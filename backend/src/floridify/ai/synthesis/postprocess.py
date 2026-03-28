"""Definition text post-processing: cleanup after AI synthesis.

Strips trailing domain labels from definition text, normalizes whitespace,
and extracts domain hints. The domain label set is derived programmatically
from the domain classifier — no hardcoded list.
"""

from __future__ import annotations

import re

from ...utils.logging import get_logger

logger = get_logger(__name__)


def _get_known_domain_labels() -> set[str]:
    """Derive domain label set from the domain classifier module.

    Returns a set like {"finance", "geography", "aviation", "medicine", ...}.
    Avoids maintaining a separate hardcoded list.
    """
    from ..assessment.domain import get_all_known_domains

    return get_all_known_domains()


def _build_trailing_domain_pattern() -> re.Pattern[str]:
    """Build a regex that matches trailing domain labels in definition text.

    Matches patterns like:
      "...about its longitudinal axis. Aviation."
      "...in a turn; aviation usage."
      "...from the horizontal, aviation"
    """
    domains = _get_known_domain_labels()
    # Escape and sort by length (longest first) for regex alternation
    escaped = sorted((re.escape(d) for d in domains), key=len, reverse=True)
    alternation = "|".join(escaped)

    # Match: optional punctuation/whitespace + domain label + optional period at end of string
    return re.compile(
        rf"[.\s;,]*\b({alternation})\b[.\s]*$",
        re.IGNORECASE,
    )


# Lazily compiled pattern (on first use)
_TRAILING_DOMAIN_RE: re.Pattern[str] | None = None


def _get_trailing_domain_re() -> re.Pattern[str]:
    global _TRAILING_DOMAIN_RE
    if _TRAILING_DOMAIN_RE is None:
        _TRAILING_DOMAIN_RE = _build_trailing_domain_pattern()
    return _TRAILING_DOMAIN_RE


def strip_trailing_domain_label(text: str) -> tuple[str, str | None]:
    """Remove trailing domain labels from definition text.

    Returns:
        (cleaned_text, extracted_domain_or_None)

    Examples:
        "The tilting of an aircraft. Aviation." → ("The tilting of an aircraft.", "aviation")
        "A financial institution" → ("A financial institution", None)
    """
    pattern = _get_trailing_domain_re()
    match = pattern.search(text)

    if match:
        domain = match.group(1).lower()
        cleaned = text[: match.start()].rstrip()
        # Ensure it still ends with punctuation
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        logger.debug(f"Stripped trailing domain '{domain}' from definition text")
        return cleaned, domain

    return text, None


def clean_definition_text(text: str) -> str:
    """Full post-processing cleanup for synthesized definition text.

    Applies:
      1. Strip trailing domain labels
      2. Normalize whitespace
      3. Fix double periods
      4. Ensure sentence ends with period
    """
    # Strip trailing domain label
    text, _ = strip_trailing_domain_label(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Fix double/triple periods
    text = re.sub(r"\.{2,}", ".", text)

    # Fix space before period
    text = re.sub(r"\s+\.", ".", text)

    # Ensure ends with period
    if text and text[-1] not in ".!?":
        text += "."

    return text
