"""Check if a job posting URL is still active.

HTTP-first, zero browser, zero LLM.
Uses httpx (already in requirements).
"""

from __future__ import annotations

import logging
import re

import httpx

_APEC_OFFRE_RE = re.compile(r"/detail-offre/(\d+[A-Z]?)", re.IGNORECASE)
_APEC_API = "https://www.apec.fr/cms/webservices/offre/public?numeroOffre={}"
_APEC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

logger = logging.getLogger(__name__)

_EXPIRED_URL_RE = re.compile(
    r"[?&/](expired|not[-_]found|error|closed|removed|unavailable)",
    re.IGNORECASE,
)

_EXPIRED_BODY_PATTERNS: list[str] = [
    # APEC
    "n'est plus en ligne",
    "cette offre n'est plus en ligne",
    "offre expirée",
    "offre pourvue",
    "cette offre a expiré",
    "offre clôturée",
    "découvrez d'autres offres similaires",
    # Generic French
    "poste pourvu",
    "ce poste n'est plus disponible",
    "cette offre n'est plus disponible",
    "offre non disponible",
    "annonce expirée",
    "cette annonce a expiré",
    # WTTJ / Lever / Greenhouse
    "this job is no longer available",
    "this position is no longer available",
    "this role is no longer available",
    # English
    "job no longer available",
    "position has been filled",
    "this job has expired",
    "job has been removed",
    "no longer accepting applications",
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

    if _EXPIRED_URL_RE.search(url):
        return "expired", "url_pattern"

    # APEC SPA pages don't expose expiry via HTTP — use the internal REST API instead
    if "apec.fr" in url:
        m = _APEC_OFFRE_RE.search(url)
        if m:
            try:
                api_url = _APEC_API.format(m.group(1))
                with httpx.Client(follow_redirects=True, timeout=timeout) as client:
                    r = client.get(api_url, headers=_APEC_HEADERS)
                    if r.status_code == 404:
                        return "expired", "apec_api_404"
                    if r.status_code == 200:
                        try:
                            data = r.json()
                            # All content fields empty = offer expired/removed
                            content = " ".join(
                                str(data.get(k) or "")
                                for k in (
                                    "texteHtml",
                                    "texteHtmlProfil",
                                    "texteHtmlEntreprise",
                                )
                            ).strip()
                            if not content:
                                return "expired", "apec_api_empty"
                            return "active", "ok"
                        except Exception:
                            pass
            except (httpx.ConnectError, httpx.TimeoutException, httpx.InvalidURL):
                return "uncertain", "network_error:apec"
        return "uncertain", "apec_no_id"

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return "expired", "http_404"
            if resp.status_code == 410:
                return "expired", "http_410"

            body = resp.text[:_MAX_BODY_BYTES].lower()

            for pattern in _EXPIRED_BODY_PATTERNS:
                if pattern in body:
                    return "expired", f"body_pattern:{pattern[:30]}"

            return "active", "ok"

    except (
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.ConnectTimeout,
        httpx.TooManyRedirects,
        httpx.InvalidURL,
    ) as exc:
        logger.debug("Liveness check uncertain for %s: %s", url, exc)
        return "uncertain", f"network_error:{type(exc).__name__}"
