import re
from collections.abc import Sequence

from app.models.extraction import Requirement


_QUOTE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u00ab": '"',
        "\u00bb": '"',
    }
)

_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\u2043": "-",
        "\u2e17": "-",
        "\u2e1a": "-",
        "\u2e3a": "-",
        "\u2e3b": "-",
        "\ufe58": "-",
        "\ufe63": "-",
        "\uff0d": "-",
    }
)

_LEADING_BULLET = re.compile(r"(?m)^[ \t]*[-*+•◦▪▫‣⁃·](?=[ \t]+)")
_HARD_WRAP_DASH = re.compile(r"-\r?\n[ \t]*")
_TRAILING_PUNCTUATION = re.compile(r"[.,;:!?،؛：！？]+$")


def _normalize_for_source_check(value: str) -> str:
    """Normalize representation without changing the words being compared."""

    normalized = value.translate(_QUOTE_TRANSLATION).translate(_DASH_TRANSLATION)
    normalized = _LEADING_BULLET.sub("", normalized)
    normalized = _HARD_WRAP_DASH.sub("-", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = _TRAILING_PUNCTUATION.sub("", normalized).rstrip()
    return normalized.casefold()


def _keep_verbatim(
    requirements: Sequence[Requirement], posting: str
) -> tuple[list[Requirement], int]:
    """Keep only Requirements whose normalized text occurs in the posting."""

    normalized_posting = _normalize_for_source_check(posting)
    kept: list[Requirement] = []
    dropped_count = 0

    for requirement in requirements:
        normalized_text = _normalize_for_source_check(requirement.text)
        if normalized_text and normalized_text in normalized_posting:
            kept.append(requirement)
        else:
            dropped_count += 1

    return kept, dropped_count


def _keep_optional_source_value(value: str | None, posting: str) -> str | None:
    """Keep optional metadata only when it is verifiable in the posting."""

    if value is None:
        return None
    normalized_value = _normalize_for_source_check(value)
    if normalized_value and normalized_value in _normalize_for_source_check(posting):
        return value
    return None
