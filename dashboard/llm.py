"""LLM client and phase functions for server-side candidature prep.

Groq (llama-3.3-70b-versatile) is the primary provider. On any Groq failure
(timeout, 5xx, quota) this falls back transparently to Gemini Flash.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import google.generativeai as genai
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)

_GROQ_MODEL = "llama-3.3-70b-versatile"
_GEMINI_MODEL = "gemini-2.0-flash"


class LLMError(Exception):
    """Raised when both Groq and Gemini fail to answer."""


class GroundingError(Exception):
    """Raised when a cover letter still cites an unknown experience_id after retry."""


def _call_groq(system_prompt: str, user_prompt: str, json_mode: bool) -> str:
    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )
    kwargs: dict[str, Any] = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs,
    )
    return response.choices[0].message.content or ""


def _call_gemini(system_prompt: str, user_prompt: str, json_mode: bool) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    generation_config = {"response_mime_type": "application/json"} if json_mode else {}
    model = genai.GenerativeModel(
        _GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config=generation_config,
    )
    response = model.generate_content(user_prompt)
    return response.text or ""


def call_llm(
    system_prompt: str, user_prompt: str, *, json_schema: dict | None = None
) -> str:
    """Call Groq first; fall back to Gemini on any failure. Logs which provider answered."""
    json_mode = json_schema is not None
    if json_mode:
        user_prompt = (
            f"{user_prompt}\n\nRespond with a JSON object matching this shape: "
            f"{json.dumps(json_schema)}"
        )
    try:
        result = _call_groq(system_prompt, user_prompt, json_mode)
        logger.info("llm: answered by groq")
        return result
    except OpenAIError as exc:
        logger.warning("llm: groq failed (%s), falling back to gemini", exc)
    try:
        result = _call_gemini(system_prompt, user_prompt, json_mode)
        logger.info("llm: answered by gemini")
        return result
    except Exception as exc:
        # Any Gemini SDK failure here means both providers are down.
        raise LLMError(f"Both Groq and Gemini failed: {exc}") from exc
