"""Deduplication of job offers across portals.

Two offers are considered duplicates when their normalized title+company key is
identical.  Normalization:
- Lowercase
- Unicode accent stripping (NFD decomposition + ASCII encoding)
- Punctuation removal (only alphanumeric and spaces kept)
- Collapse multiple spaces to one

URL normalization strips query params for portals where the offer ID is in the
path (APEC), so the same offer scraped from different search-result pages maps
to a single canonical URL.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse, urlunparse

from scripts.models import RawOffer

# Portals whose offer identity lives entirely in the URL path; query params
# (page index, search context, etc.) are irrelevant for deduplication.
# Portals whose offer identity lives entirely in the URL path.
# Matched against the portal field OR the URL hostname.
_PATH_ONLY_PORTALS = frozenset({"apec"})
_PATH_ONLY_HOSTNAMES = frozenset({"www.apec.fr", "apec.fr"})


def normalize_offer_url(url: str, portal: str = "") -> str:
    """Return a canonical URL for deduplication.

    For APEC the offer ID is in the path; query-string params (page index,
    selectedIndex…) are search context and must be dropped.  Detection is
    done on both the portal field and the URL hostname so that older rows
    with an empty portal column are handled correctly.
    """
    if not url:
        return url
    parsed = urlparse(url)
    if portal.lower() in _PATH_ONLY_PORTALS or parsed.hostname in _PATH_ONLY_HOSTNAMES:
        return urlunparse(parsed._replace(query="", fragment=""))
    return url


def _remove_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def normalize_key(title: str, company: str) -> str:
    """Build a normalized deduplication key from title and company.

    Args:
        title: Raw job title string.
        company: Raw company name string.

    Returns:
        A normalized key string: ``"<title>||<company>"``.
    """

    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = _remove_accents(text)
        text = re.sub(r"[^a-z0-9 ]", " ", text)
        text = re.sub(r" {2,}", " ", text).strip()
        return text

    return f"{_normalize(title)}||{_normalize(company)}"


def deduplicate(offers: list[RawOffer]) -> list[RawOffer]:
    """Remove duplicate offers, keeping the first occurrence per unique key.

    Args:
        offers: List of raw offers, potentially containing duplicates.

    Returns:
        Deduplicated list of ``RawOffer``, in original order of first occurrence.
    """
    seen: set[str] = set()
    unique: list[RawOffer] = []
    for offer in offers:
        key = normalize_key(offer.title, offer.company)
        if key not in seen:
            seen.add(key)
            unique.append(offer)
    return unique
