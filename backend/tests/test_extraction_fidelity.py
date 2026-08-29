from pathlib import Path

from app.agents.extraction import (
    _keep_optional_source_value,
    _keep_verbatim,
    _normalize_for_source_check,
)
from app.models.extraction import Necessity, Requirement


SAMPLE_POSTING = Path(__file__).parents[1].joinpath("data", "sample_posting.txt").read_text(
    encoding="utf-8"
)


def requirement(text: str) -> Requirement:
    return Requirement(text=text, necessity=Necessity.REQUIRED)


def test_normalization_covers_only_representation_changes():
    assert _normalize_for_source_check("  •  Build\nPython services. ") == "build python services"
    assert _normalize_for_source_check("‘e–commerce’") == "'e-commerce'"
    assert _normalize_for_source_check("e-\n  commerce") == "e-commerce"
    assert _normalize_for_source_check("3—5 years!!!") == "3-5 years"
    assert _normalize_for_source_check("co-op") == "co-op"


def test_keep_verbatim_accepts_normalized_spans_and_counts_drops():
    kept, dropped_count = _keep_verbatim(
        [
            requirement("• 3-5 years of experience building production APIs with Python."),
            requirement("Experience with e-commerce platforms."),
            requirement("Experience with AWS (Lambda, RDS, S3)"),
        ],
        SAMPLE_POSTING,
    )

    assert [item.text for item in kept] == [
        "• 3-5 years of experience building production APIs with Python.",
        "Experience with e-commerce platforms.",
        "Experience with AWS (Lambda, RDS, S3)",
    ]
    assert dropped_count == 0


def test_keep_verbatim_rejects_fabricated_or_fuzzy_spans():
    kept, dropped_count = _keep_verbatim(
        [
            requirement("Build production Python services with FastAPI"),
            requirement("Build highly scalable Python microservices with FastAPI"),
            requirement("Experience with AWS Lambda, RDS, and S3"),
        ],
        SAMPLE_POSTING,
    )

    assert [item.text for item in kept] == [
        "Build production Python services with FastAPI",
    ]
    assert dropped_count == 2


def test_keep_verbatim_drops_empty_normalized_spans():
    kept, dropped_count = _keep_verbatim([requirement("...")], SAMPLE_POSTING)

    assert kept == []
    assert dropped_count == 1


def test_optional_metadata_is_removed_when_not_source_checked():
    assert _keep_optional_source_value("Senior Backend Engineer", SAMPLE_POSTING) == (
        "Senior Backend Engineer"
    )
    assert _keep_optional_source_value("A Principal Data Scientist", SAMPLE_POSTING) is None
    assert _keep_optional_source_value(None, SAMPLE_POSTING) is None


def test_sample_posting_is_long_enough_and_contains_required_fixture_features():
    assert len(SAMPLE_POSTING) >= 50
    assert "e-\n  commerce" in SAMPLE_POSTING
    assert "3–5" in SAMPLE_POSTING
    assert "•" in SAMPLE_POSTING
    assert "◦" in SAMPLE_POSTING
    assert "▪" in SAMPLE_POSTING
