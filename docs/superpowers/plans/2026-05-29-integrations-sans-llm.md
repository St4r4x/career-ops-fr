# Intégrations sans LLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add salary normalisation (13e mois, RTT, TR, intéressement) + legitimacy penalty signals to `pre_filter.py`, ATS Unicode normalisation to the three PDF generators, and a `liveness.py` module with opt-in integration in `import_offers.py`.

**Architecture:** Three independent groups. Group 1 extends `score_offer()` in `pre_filter.py` with two new signals (salary_normalized replaces the old salary signal; legitimacy adds penalties). Group 2 adds a `_normalize_for_ats()` helper called inside `generate_pdf()`, `generate_cover_letter()`, and `generate_prep_sheet()`. Group 3 creates a new `scripts/liveness.py` module using `httpx` (already in requirements) and wires it into `import_offers.py` behind a `--check-liveness` flag.

**Tech Stack:** Python 3.11+, re (stdlib), httpx 0.28 (already installed), pytest + pytest-httpx (already installed)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/pre_filter.py` | Modify | Add `_MONTHS_13_RE`, `_RTT_RE`, `_TR_RE`, `_INTERESSEMENT_RE`; replace salary signal with `_score_salary()`; add `_score_legitimacy()` |
| `scripts/liveness.py` | Create | `check_liveness(url) -> (status, reason)` — HTTP-first, zero browser |
| `scripts/import_offers.py` | Modify | Add `--check-liveness` flag, call `check_liveness()` per offer before insert |
| `scripts/generate_pdf.py` | Modify | Add `_normalize_for_ats()`, call it in `generate_pdf()` |
| `scripts/generate_cover_letter.py` | Modify | Call `_normalize_for_ats()` before WeasyPrint render |
| `scripts/generate_prep_sheet.py` | Modify | Call `_normalize_for_ats()` before WeasyPrint render |
| `tests/test_pre_filter.py` | Modify | Add `TestSalaryNormalized` and `TestLegitimacy` classes |
| `tests/test_liveness.py` | Create | 7 tests using pytest-httpx |
| `tests/test_generate_pdf.py` | Modify | Add 4 ATS normalisation tests |

---

## Task 1: Replace salary signal with package-aware `_score_salary()`

**Files:**
- Modify: `scripts/pre_filter.py`
- Test: `tests/test_pre_filter.py`

The current salary signal (+0.3 if a value is in target range) ignores French compensation extras. This task replaces it with `_score_salary()` that reconstructs the annual package before comparing.

- [ ] **Step 1: Add failing tests — new class `TestSalaryNormalized` at bottom of `tests/test_pre_filter.py`**

```python
class TestSalaryNormalized:
    def test_13th_month_raises_package_into_range(self) -> None:
        # 3 500 × 13 = 45 500 → in range [40k-55k] → +0.5
        desc = "Salaire 3500€/mois + 13ème mois"
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(0.5, abs=0.05)
        assert any("salary:" in t for t in tags)

    def test_rtt_and_tr_added_to_package(self) -> None:
        # 38k base + 10 RTT (~1743) + TR (~1962) = ~41.7k → in range → +0.5
        desc = "Salaire 38000€ annuel, 10 RTT, titre-restaurant"
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(0.5, abs=0.05)

    def test_salary_out_of_range_penalty(self) -> None:
        # 80k clearly above target → -0.3
        desc = "Rémunération : 80k€"
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(-0.3, abs=0.05)

    def test_salary_no_info_neutral(self) -> None:
        # No salary info → 0.0 (no bonus, no penalty)
        desc = "Rejoignez notre équipe dynamique."
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(0.0, abs=0.05)

    def test_interessement_adds_to_package(self) -> None:
        # 38k + 5% intéressement = 39.9k → below range → -0.3
        # but 40k + 5% = 42k → in range → +0.5
        desc = "Salaire 40000€, intéressement selon résultats"
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(0.5, abs=0.05)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /home/missia03/Projects/career-ops-fr && source .venv/bin/activate
pytest tests/test_pre_filter.py::TestSalaryNormalized -v 2>&1 | tail -10
```

Expected: all 5 FAIL (old salary signal gives wrong values).

- [ ] **Step 3: Add new regex constants at top of `scripts/pre_filter.py`** (after `_SALARY_RE` line 68)

```python
_MONTHS_13_RE = re.compile(r"13[eè]me?\s*mois|treizi[eè]me\s*mois", re.IGNORECASE)
_RTT_RE = re.compile(r"(\d+)\s*RTT", re.IGNORECASE)
_TR_RE = re.compile(r"titre[\s-]restaurant|ticket[\s-]restaurant", re.IGNORECASE)
_INTERESSEMENT_RE = re.compile(r"int[eé]ressement|participation", re.IGNORECASE)
```

- [ ] **Step 4: Add `_score_salary()` function after `_all_target_companies()` in `scripts/pre_filter.py`**

```python
def _score_salary(desc: str, desc_lower: str, scoring_cfg: dict) -> tuple[float, str | None]:
    """Reconstruct French annual package and return (score_delta, tag_or_None)."""
    sal_min = scoring_cfg.get("target_salary_min", 0)
    sal_max = scoring_cfg.get("target_salary_max", 999_999)

    # Find first salary value
    m = _SALARY_RE.search(desc_lower)
    if not m:
        return 0.0, None

    raw = m.group(1) or m.group(2)
    if not raw:
        return 0.0, None
    base = int(raw)
    if base < 1000:
        # monthly value
        multiplier = 13 if _MONTHS_13_RE.search(desc_lower) else 12
        base_annual = base * multiplier
    else:
        base_annual = base

    # RTT
    rtt_match = _RTT_RE.search(desc_lower)
    rtt_days = int(rtt_match.group(1)) if rtt_match else (10 if "rtt" in desc_lower else 0)
    rtt_val = rtt_days * base_annual / 218 if rtt_days else 0.0

    # Titre-restaurant
    tr_val = 218 * 9.0 if _TR_RE.search(desc_lower) else 0.0

    # Intéressement / participation
    int_val = base_annual * 0.05 if _INTERESSEMENT_RE.search(desc_lower) else 0.0

    total = base_annual + rtt_val + tr_val + int_val
    tag = f"salary:{int(total)}"

    if sal_min <= total <= sal_max:
        return 0.5, tag
    return -0.3, tag
```

- [ ] **Step 5: Replace old salary block in `score_offer()` with call to `_score_salary()`**

Find and remove this block in `score_offer()` (lines 142–154):

```python
    if desc_lower:
        sal_min = scoring_cfg.get("target_salary_min", 0)
        sal_max = scoring_cfg.get("target_salary_max", 999_999)
        for m in _SALARY_RE.finditer(desc_lower):
            raw = m.group(1) or m.group(2)
            if raw:
                val = int(raw)
                if val < 1000:
                    val *= 1000
                if sal_min <= val <= sal_max:
                    score += 0.3
                    tags.append(f"salary:{val}")
                    break
```

Replace with:

```python
    if desc_lower:
        sal_delta, sal_tag = _score_salary(offer.description or "", desc_lower, scoring_cfg)
        if sal_delta != 0.0:
            score += sal_delta
            if sal_tag:
                tags.append(sal_tag)
```

- [ ] **Step 6: Run new salary tests**

```bash
pytest tests/test_pre_filter.py::TestSalaryNormalized -v 2>&1 | tail -10
```

Expected: all 5 PASS.

- [ ] **Step 7: Run full pre_filter suite**

```bash
pytest tests/test_pre_filter.py -v 2>&1 | tail -15
```

Expected: all pass. If `test_salary_in_range` from `TestNewSignals` fails (it tested the old +0.3 logic), update it:

```python
    def test_salary_in_range(self) -> None:
        desc = "Salaire proposé : 45k€ selon profil."
        offer = _offer_with_desc(description=desc)
        score, _ = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(0.5, abs=0.05)  # new signal gives +0.5
```

- [ ] **Step 8: Commit**

```bash
git add scripts/pre_filter.py tests/test_pre_filter.py
git commit -m "feat(scoring): add French salary normalisation (13e mois, RTT, TR, intéressement)"
```

---

## Task 2: Add legitimacy penalty signal

**Files:**
- Modify: `scripts/pre_filter.py`
- Test: `tests/test_pre_filter.py`

- [ ] **Step 1: Add failing tests — new class `TestLegitimacy` at bottom of `tests/test_pre_filter.py`**

```python
class TestLegitimacy:
    def test_thin_description_penalty(self) -> None:
        # desc < 300 chars → -0.5 cap
        desc = "Poste à pourvoir. Envoyez votre CV."
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(-0.5, abs=0.05)
        assert "legitimacy:suspicious" in tags

    def test_no_tech_skills_penalty(self) -> None:
        # long desc but 0 tech skills → -0.3
        desc = "Nous recherchons un profil dynamique et motivé. " * 20
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert score == pytest.approx(-0.3, abs=0.05)
        assert "legitimacy:suspicious" in tags

    def test_no_salary_penalty(self) -> None:
        # long desc with tech skills but no salary → -0.2 (below suspicious threshold)
        desc = ("python pytorch mlops docker fastapi " * 10) + (" lorem ipsum " * 30)
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        # skills give +1.0, legitimacy:no_salary gives -0.2, no "suspicious" tag
        assert "legitimacy:suspicious" not in tags
        assert any("legitimacy:no_salary" in t for t in tags)

    def test_good_offer_no_penalty(self) -> None:
        # rich desc with tech skills and salary → no legitimacy penalty
        desc = "python pytorch mlops docker. CDI 45k€. " + ("lorem ipsum " * 20)
        offer = _offer_with_desc(description=desc)
        score, tags = score_offer(offer, MOCK_SETTINGS_V2)
        assert not any("legitimacy:" in t for t in tags)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_pre_filter.py::TestLegitimacy -v 2>&1 | tail -10
```

Expected: all 4 FAIL.

- [ ] **Step 3: Add `_score_legitimacy()` function in `scripts/pre_filter.py`** (after `_score_salary()`)

```python
def _score_legitimacy(desc: str, desc_lower: str) -> tuple[float, list[str]]:
    """Return (penalty, tags) based on offer quality signals. Penalty capped at -0.5."""
    penalty = 0.0
    tags: list[str] = []

    if len(desc) < 300:
        penalty -= 0.5
        tags.append("legitimacy:thin_desc")

    if not any(skill in desc_lower for skill in _TECH_SKILLS):
        penalty -= 0.3
        tags.append("legitimacy:no_tech")

    if not _SALARY_RE.search(desc_lower):
        penalty -= 0.2
        tags.append("legitimacy:no_salary")

    capped = max(penalty, -0.5)
    if capped <= -0.3:
        tags.append("legitimacy:suspicious")

    return capped, tags
```

- [ ] **Step 4: Add call to `_score_legitimacy()` in `score_offer()`** — after the ATS portal block (end of the function, before `return`):

```python
    if desc_lower:
        leg_delta, leg_tags = _score_legitimacy(offer.description or "", desc_lower)
        if leg_delta != 0.0:
            score += leg_delta
            tags.extend(leg_tags)
```

- [ ] **Step 5: Run legitimacy tests**

```bash
pytest tests/test_pre_filter.py::TestLegitimacy -v 2>&1 | tail -10
```

Expected: all 4 PASS.

- [ ] **Step 6: Run full pre_filter suite**

```bash
pytest tests/test_pre_filter.py -v 2>&1 | tail -15
```

Expected: all pass. Note: some `TestNewSignals` tests may now fail because the legitimacy penalty kicks in on empty descriptions. Fix by adding `description="python"` to offers in failing tests (the existing `_offer_with_desc` helper has `description=""` by default). For `test_experience_no_match`, `test_portal_apec_no_bonus`, `test_ats_portal_bonus`: these all use empty descriptions which will now trigger legitimacy penalties. Update them to use a minimal valid description:

For any test in `TestNewSignals` that uses `_offer_with_desc()` with empty `description=""` and asserts `score == pytest.approx(0.0, ...)` — add a rich enough description to avoid legitimacy penalties, e.g.:

```python
description="python pytorch docker mlops fastapi aws CDI 45k€ " + "lorem ipsum " * 20
```

Then adjust the expected score by adding the salary/skill bonuses that description triggers.

**Alternative (simpler):** isolate legitimacy tests by using a dedicated settings without legitimacy (use `MOCK_SETTINGS_V2` with a description that satisfies all legitimacy checks). The safest fix: for tests that specifically test ONE signal (portal, CDI, etc.), use a description that is >300 chars, has tech skills, and has salary, so legitimacy = 0.

Update the affected `TestNewSignals` tests:

```python
_RICH_DESC_NO_EXTRAS = (
    "python pytorch docker mlops aws postgresql fastapi nlp llm rag embedding "
    "retrieval transformer sklearn redis kubernetes airflow spark gcp azure CDI "
    "45k€ selon profil 2 ans d'expérience " + "lorem ipsum dolor sit amet " * 10
)

    def test_ats_portal_bonus(self) -> None:
        offer = _offer_with_desc(portal="lever", description=_RICH_DESC_NO_EXTRAS)
        score, _ = score_offer(offer, MOCK_SETTINGS_V2)
        # rich desc: skills ~1.0 + exp 0.5 + CDI 0.3 + salary 0.5 + portal 0.3 = ~2.6
        assert score > 2.0  # portal bonus is included

    def test_portal_apec_no_bonus(self) -> None:
        offer = _offer_with_desc(portal="apec", description=_RICH_DESC_NO_EXTRAS)
        score_apec, _ = score_offer(offer, MOCK_SETTINGS_V2)
        offer_lever = _offer_with_desc(portal="lever", description=_RICH_DESC_NO_EXTRAS)
        score_lever, _ = score_offer(offer_lever, MOCK_SETTINGS_V2)
        assert score_lever > score_apec  # lever gets +0.3, apec does not
```

Also update `test_experience_no_match`, `test_experience_over_threshold` to use descriptions that are long enough and have tech skills to avoid legitimacy penalty — adjust expected scores accordingly.

- [ ] **Step 7: Run full suite**

```bash
pytest tests/test_pre_filter.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/pre_filter.py tests/test_pre_filter.py
git commit -m "feat(scoring): add legitimacy penalty signal (thin desc, no tech, no salary)"
```

---

## Task 3: ATS Unicode normalisation in PDF generators

**Files:**
- Modify: `scripts/generate_pdf.py`
- Modify: `scripts/generate_cover_letter.py`
- Modify: `scripts/generate_prep_sheet.py`
- Test: `tests/test_generate_pdf.py`

- [ ] **Step 1: Add failing tests at bottom of `tests/test_generate_pdf.py`**

```python
from scripts.generate_pdf import _normalize_for_ats


class TestNormalizeForAts:
    def test_em_dash_replaced(self) -> None:
        assert _normalize_for_ats("foo—bar") == "foo--bar"

    def test_en_dash_replaced(self) -> None:
        assert _normalize_for_ats("foo–bar") == "foo-bar"

    def test_smart_quotes_replaced(self) -> None:
        result = _normalize_for_ats("“foo”")
        assert result == '"foo"'

    def test_zero_width_removed(self) -> None:
        assert _normalize_for_ats("foo​bar") == "foobar"

    def test_style_block_preserved(self) -> None:
        html = "<style>.em—dash { color: red; }</style>normal—text"
        result = _normalize_for_ats(html)
        assert "—" in result  # dash inside style preserved
        assert result.endswith("normal--text")

    def test_plain_text_unchanged(self) -> None:
        assert _normalize_for_ats("Hello world") == "Hello world"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_generate_pdf.py::TestNormalizeForAts -v 2>&1 | tail -10
```

Expected: all 6 FAIL with `ImportError: cannot import name '_normalize_for_ats'`.

- [ ] **Step 3: Add `_normalize_for_ats()` to `scripts/generate_pdf.py`** — after the imports, before `TEMPLATE_DIR`:

```python
import re as _re

_ATS_REPLACEMENTS: list[tuple[str, str]] = [
    ("—", "--"),   # em-dash
    ("–", "-"),    # en-dash
    ("‘", "'"),    # left single quote
    ("’", "'"),    # right single quote
    ("“", '"'),    # left double quote
    ("”", '"'),    # right double quote
    (" ", " "),    # non-breaking space
    ("​", ""),     # zero-width space
    ("‌", ""),     # zero-width non-joiner
    ("﻿", ""),     # BOM
]

_STYLE_SCRIPT_RE = _re.compile(
    r"(<(?:style|script)[^>]*>)(.*?)(</(?:style|script)>)",
    _re.DOTALL | _re.IGNORECASE,
)


def _normalize_for_ats(html: str) -> str:
    """Replace typographic characters that break ATS parsers, preserving style/script blocks."""
    protected: list[str] = []

    def _protect(m: _re.Match) -> str:
        protected.append(m.group(0))
        return f"\x00PROTECTED{len(protected) - 1}\x00"

    masked = _STYLE_SCRIPT_RE.sub(_protect, html)
    for old, new in _ATS_REPLACEMENTS:
        masked = masked.replace(old, new)
    for i, block in enumerate(protected):
        masked = masked.replace(f"\x00PROTECTED{i}\x00", block)
    return masked
```

- [ ] **Step 4: Call `_normalize_for_ats()` inside `generate_pdf()`**

Replace lines 67–72 in `generate_pdf.py`:

```python
    html_content = render_html(context)
    css_path = TEMPLATE_DIR / "cv.css"
    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(
        str(output_path),
        stylesheets=[str(css_path)],
    )
```

With:

```python
    html_content = _normalize_for_ats(render_html(context))
    css_path = TEMPLATE_DIR / "cv.css"
    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(
        str(output_path),
        stylesheets=[str(css_path)],
    )
```

- [ ] **Step 5: Run ATS normalisation tests**

```bash
pytest tests/test_generate_pdf.py::TestNormalizeForAts -v 2>&1 | tail -10
```

Expected: all 6 PASS.

- [ ] **Step 6: Read `scripts/generate_cover_letter.py` and add the same normalisation**

Read the file to find its `render_html()` / `generate_pdf()` equivalent call, then apply `_normalize_for_ats()` the same way. Import `_normalize_for_ats` from `scripts.generate_pdf`:

```python
from scripts.generate_pdf import _normalize_for_ats
```

Apply before WeasyPrint in whichever function renders HTML to PDF.

- [ ] **Step 7: Read `scripts/generate_prep_sheet.py` and apply same normalisation**

Same pattern as Step 6.

- [ ] **Step 8: Run full test suite**

```bash
pytest --tb=short 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add scripts/generate_pdf.py scripts/generate_cover_letter.py scripts/generate_prep_sheet.py tests/test_generate_pdf.py
git commit -m "feat: add ATS Unicode normalisation to PDF generators (em-dash, smart quotes, ZWS)"
```

---

## Task 4: Create `scripts/liveness.py`

**Files:**
- Create: `scripts/liveness.py`
- Create: `tests/test_liveness.py`

- [ ] **Step 1: Create `tests/test_liveness.py`**

```python
"""Tests for scripts/liveness.py — uses pytest-httpx for HTTP mocking."""

from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock


class TestCheckLiveness:
    def test_404_returns_expired(self, httpx_mock: HTTPXMock) -> None:
        from scripts.liveness import check_liveness
        httpx_mock.add_response(url="https://example.com/job/123", status_code=404)
        status, reason = check_liveness("https://example.com/job/123")
        assert status == "expired"
        assert "404" in reason

    def test_410_returns_expired(self, httpx_mock: HTTPXMock) -> None:
        from scripts.liveness import check_liveness
        httpx_mock.add_response(url="https://example.com/job/123", status_code=410)
        status, reason = check_liveness("https://example.com/job/123")
        assert status == "expired"
        assert "410" in reason

    def test_body_pattern_fr_expired(self, httpx_mock: HTTPXMock) -> None:
        from scripts.liveness import check_liveness
        httpx_mock.add_response(
            url="https://example.com/job/123",
            status_code=200,
            text="Désolé, cette offre a expiré.",
        )
        status, reason = check_liveness("https://example.com/job/123")
        assert status == "expired"
        assert "body_pattern" in reason

    def test_body_pattern_en_expired(self, httpx_mock: HTTPXMock) -> None:
        from scripts.liveness import check_liveness
        httpx_mock.add_response(
            url="https://example.com/job/123",
            status_code=200,
            text="This job is no longer available.",
        )
        status, reason = check_liveness("https://example.com/job/123")
        assert status == "expired"

    def test_200_clean_body_active(self, httpx_mock: HTTPXMock) -> None:
        from scripts.liveness import check_liveness
        httpx_mock.add_response(
            url="https://example.com/job/123",
            status_code=200,
            text="<html><body><h1>Senior ML Engineer</h1><p>Apply now!</p></body></html>",
        )
        status, reason = check_liveness("https://example.com/job/123")
        assert status == "active"
        assert reason == "ok"

    def test_network_error_uncertain(self, httpx_mock: HTTPXMock) -> None:
        from scripts.liveness import check_liveness
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        status, reason = check_liveness("https://example.com/job/123")
        assert status == "uncertain"
        assert "network_error" in reason

    def test_empty_url_uncertain(self) -> None:
        from scripts.liveness import check_liveness
        status, reason = check_liveness("")
        assert status == "uncertain"
        assert reason == "no_url"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_liveness.py -v 2>&1 | tail -10
```

Expected: all 7 FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `scripts/liveness.py`**

```python
"""Check if a job posting URL is still active.

HTTP-first, zero browser, zero LLM.
Uses httpx (already in requirements).
"""

from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger(__name__)

_EXPIRED_URL_RE = re.compile(
    r"[?&/](expired|not[-_]found|error|closed|removed|unavailable)",
    re.IGNORECASE,
)

_EXPIRED_BODY_PATTERNS: list[str] = [
    # French
    "offre expirée",
    "offre pourvue",
    "poste pourvu",
    "ce poste n'est plus disponible",
    "cette offre a expiré",
    "offre clôturée",
    # English
    "job no longer available",
    "position has been filled",
    "this job has expired",
    "job has been removed",
    "no longer accepting",
    "this job is no longer available",
    "this position has been filled",
]

_HEAD_TIMEOUT = 8
_GET_TIMEOUT = 15
_MAX_BODY_BYTES = 50_000


def check_liveness(url: str, *, timeout: int = _GET_TIMEOUT) -> tuple[str, str]:
    """Return (status, reason).

    status: "active" | "expired" | "uncertain"
    reason: short string explaining the decision
    """
    if not url or not url.startswith(("http://", "https://")):
        return "uncertain", "no_url"

    # Check URL patterns before any HTTP request
    if _EXPIRED_URL_RE.search(url):
        return "expired", "url_pattern"

    try:
        # HEAD request first (fast, no body)
        with httpx.Client(follow_redirects=True, timeout=_HEAD_TIMEOUT) as client:
            try:
                head = client.head(url)
                if head.status_code == 404:
                    return "expired", "http_404"
                if head.status_code == 410:
                    return "expired", "http_410"
            except httpx.TimeoutException:
                pass  # fall through to GET

        # GET request with body inspection
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            with client.stream("GET", url) as resp:
                if resp.status_code == 404:
                    return "expired", "http_404"
                if resp.status_code == 410:
                    return "expired", "http_410"

                body = resp.read(_MAX_BODY_BYTES).decode("utf-8", errors="replace").lower()

                for pattern in _EXPIRED_BODY_PATTERNS:
                    if pattern in body:
                        return "expired", f"body_pattern:{pattern[:30]}"

                return "active", "ok"

    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout,
            httpx.TooManyRedirects, httpx.InvalidURL) as exc:
        logger.debug("Liveness check uncertain for %s: %s", url, exc)
        return "uncertain", f"network_error:{type(exc).__name__}"
```

- [ ] **Step 4: Run liveness tests**

```bash
pytest tests/test_liveness.py -v 2>&1 | tail -15
```

Expected: all 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/liveness.py tests/test_liveness.py
git commit -m "feat: add liveness.py — HTTP-first job URL liveness checker"
```

---

## Task 5: Wire liveness check into `import_offers.py`

**Files:**
- Modify: `scripts/import_offers.py`
- Test: `tests/test_import_offers.py`

- [ ] **Step 1: Add failing test at bottom of `tests/test_import_offers.py`**

```python
class TestLivenessIntegration:
    def test_expired_offer_skipped_with_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts import import_offers as io

        monkeypatch.setattr(
            "scripts.import_offers.check_liveness",
            lambda url, **kw: ("expired", "http_404"),
        )
        conn = _make_conn()
        offer = RawOffer(
            title="ML Engineer",
            company="Acme",
            url="https://jobs.example.com/1",
            portal="apec",
        )
        inserted, skipped, expired = io.import_offers_with_liveness(
            [offer], Path(":memory:"), conn=conn
        )
        assert inserted == 0
        assert expired == 1

    def test_uncertain_offer_imported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts import import_offers as io

        monkeypatch.setattr(
            "scripts.import_offers.check_liveness",
            lambda url, **kw: ("uncertain", "timeout"),
        )
        conn = _make_conn()
        offer = RawOffer(
            title="ML Engineer",
            company="Acme",
            url="https://jobs.example.com/2",
            portal="apec",
        )
        inserted, skipped, expired = io.import_offers_with_liveness(
            [offer], Path(":memory:"), conn=conn
        )
        assert inserted == 1
        assert expired == 0
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_import_offers.py::TestLivenessIntegration -v 2>&1 | tail -10
```

Expected: FAIL with `ImportError` or `AttributeError`.

- [ ] **Step 3: Add import and `import_offers_with_liveness()` to `scripts/import_offers.py`**

Add at the top with other imports:
```python
from scripts.liveness import check_liveness
```

Add new function after `import_offers()`:

```python
def import_offers_with_liveness(
    offers: list[RawOffer],
    db_path: Path,
    *,
    conn: sqlite3.Connection | None = None,
) -> tuple[int, int, int]:
    """Insert new offers, skipping expired ones. Returns (inserted, skipped, expired)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _conn = conn or sqlite3.connect(str(db_path))
    try:
        _conn.execute(_CREATE_TABLE_SQL)
        urls = existing_urls(_conn)
        inserted = 0
        skipped = 0
        expired_count = 0
        for offer in offers:
            if offer.url and offer.url in urls:
                skipped += 1
                continue
            if offer.url:
                status, reason = check_liveness(offer.url)
                if status == "expired":
                    logger.info("Skip (expired %s): %s @ %s", reason, offer.title, offer.company)
                    expired_count += 1
                    continue
            insert_offer(_conn, offer)
            if offer.url:
                urls.add(offer.url)
            inserted += 1
        _conn.commit()
    finally:
        if conn is None:
            _conn.close()
    return inserted, skipped, expired_count
```

- [ ] **Step 4: Add `--check-liveness` flag to `main()` in `scripts/import_offers.py`**

In `main()`, add the argument:
```python
    parser.add_argument(
        "--check-liveness",
        action="store_true",
        help="Skip offers whose URL returns 404/expired before inserting",
    )
```

And in the import call:
```python
    if args.check_liveness:
        inserted, skipped, expired = import_offers_with_liveness(offers, Path(args.db))
        print(f"Imported {inserted} new offers, skipped {skipped} existing, {expired} expired")
    else:
        inserted, skipped = import_offers(offers, Path(args.db))
        print(f"Imported {inserted} new offers, skipped {skipped} already present")
```

- [ ] **Step 5: Run liveness integration tests**

```bash
pytest tests/test_import_offers.py::TestLivenessIntegration -v 2>&1 | tail -10
```

Expected: both PASS.

- [ ] **Step 6: Run full test suite**

```bash
pytest --tb=short 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/import_offers.py tests/test_import_offers.py
git commit -m "feat: wire liveness check into import_offers with --check-liveness flag"
```

---

## Task 6: Update CHANGELOG, rescore DB, push

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run rescore on the real DB** (salary signal changed, scores will shift)

```bash
cd /home/missia03/Projects/career-ops-fr && source .venv/bin/activate
python -m scripts.rescore --dry-run 2>&1 | tail -5
python -m scripts.rescore
```

- [ ] **Step 2: Add CHANGELOG entry** in the `## [Unreleased]` section:

```markdown
## 2026-05-29

### Added
- `scripts/liveness.py` — HTTP-first liveness checker: HEAD → URL patterns → GET body patterns (FR+EN); returns `active|expired|uncertain`; zero browser, zero LLM; uses httpx
- `tests/test_liveness.py` — 7 tests covering 404, 410, FR/EN body patterns, active, network error, empty URL
- `scripts/pre_filter.py` — `_score_salary()`: reconstructs French annual package (13e mois, RTT, titre-restaurant, intéressement) before comparing to target range; +0.5 if in range, -0.3 if out of range, 0 if absent
- `scripts/pre_filter.py` — `_score_legitimacy()`: penalties for thin description (<300 chars, -0.5), no tech skills (-0.3), no salary (-0.2); `legitimacy:suspicious` tag if penalty ≥ 0.3; capped at -0.5
- `scripts/generate_pdf.py` — `_normalize_for_ats()`: replaces em-dash, smart quotes, zero-width chars before WeasyPrint render; preserves `<style>`/`<script>` blocks
- `tests/test_generate_pdf.py` — `TestNormalizeForAts` (6 tests)
- `tests/test_pre_filter.py` — `TestSalaryNormalized` (5 tests) and `TestLegitimacy` (4 tests)

### Changed
- `scripts/generate_cover_letter.py` — ATS Unicode normalisation applied before render
- `scripts/generate_prep_sheet.py` — ATS Unicode normalisation applied before render
- `scripts/import_offers.py` — added `--check-liveness` flag and `import_offers_with_liveness()` function
- `dashboard/data/applications.db` — rescored with updated salary + legitimacy signals
```

- [ ] **Step 3: Commit and push**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for no-LLM integrations [skip ci]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin master
```
