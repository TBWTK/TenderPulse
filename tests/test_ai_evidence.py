from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tenderpulse.ai.evidence import (
    EvidenceValidationError,
    build_evidence_input,
    upgrade_legacy_extraction_payload,
    validate_extraction_arguments,
)


def test_structured_extraction_requires_verbatim_citations(it_notice) -> None:
    evidence_input = build_evidence_input(it_notice)
    arguments = {
        "requirements_status": "found",
        "requirements": [
            {
                "text": "The supplier must deliver data engineering services.",
                "mandatory": True,
                "citation": {
                    "field": "description",
                    "quote": "Data engineering, analytics and machine learning",
                },
            }
        ],
        "deadlines_status": "found",
        "deadlines": [
            {
                "label": "submission",
                "value": "2026-09-30T12:00:00+00:00",
                "normalized_at": "2026-09-30T12:00:00Z",
                "citation": {
                    "field": "deadline_at",
                    "quote": "2026-09-30T12:00:00Z",
                },
            }
        ],
        "gaps": ["No explicit qualification threshold is present."],
    }

    extraction = validate_extraction_arguments(evidence_input, arguments)

    assert extraction.requirements[0].citation.quote in evidence_input.fields["description"]
    assert extraction.deadlines[0].normalized_at == datetime(2026, 9, 30, 12, tzinfo=UTC)
    assert extraction.gaps == ("No explicit qualification threshold is present.",)
    assert len(evidence_input.input_sha256) == 64


def test_structured_extraction_rejects_claim_without_supported_quote(it_notice) -> None:
    evidence_input = build_evidence_input(it_notice)

    with pytest.raises(EvidenceValidationError, match="citation quote is not present"):
        validate_extraction_arguments(
            evidence_input,
            {
                "requirements_status": "found",
                "requirements": [
                    {
                        "text": "ISO 27001 certification is mandatory.",
                        "mandatory": True,
                        "citation": {
                            "field": "description",
                            "quote": "ISO 27001 certification",
                        },
                    }
                ],
                "deadlines_status": "unknown",
                "deadlines": [],
                "gaps": [],
            },
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "requirements_status": "found",
            "requirements": [{"text": "No citation"}],
            "deadlines_status": "unknown",
            "deadlines": [],
            "gaps": [],
        },
        {
            "requirements_status": "unknown",
            "requirements": [],
            "deadlines_status": "unknown",
            "deadlines": "not-a-list",
            "gaps": [],
        },
        {
            "requirements_status": "unknown",
            "requirements": [],
            "deadlines_status": "unknown",
            "deadlines": [],
            "gaps": [""],
        },
    ],
)
def test_structured_extraction_rejects_malformed_arguments(it_notice, arguments) -> None:
    with pytest.raises(EvidenceValidationError, match="structured extraction is invalid"):
        validate_extraction_arguments(build_evidence_input(it_notice), arguments)


def test_missing_source_values_remain_explicit_unknown(medical_notice) -> None:
    evidence_input = build_evidence_input(medical_notice)

    assert evidence_input.fields["deadline_at"] == "unknown"
    result = validate_extraction_arguments(
        evidence_input,
        {
            "requirements_status": "unknown",
            "requirements": [],
            "deadlines_status": "unknown",
            "deadlines": [],
            "gaps": ["Submission deadline is unknown."],
        },
    )
    assert result.deadlines == ()


def test_empty_claim_category_requires_explicit_coverage_status(it_notice) -> None:
    evidence_input = build_evidence_input(it_notice)

    with pytest.raises(EvidenceValidationError, match="structured extraction is invalid"):
        validate_extraction_arguments(
            evidence_input,
            {
                "requirements_status": "found",
                "requirements": [],
                "deadlines_status": "unknown",
                "deadlines": [],
                "gaps": [],
            },
        )


def test_legacy_extraction_payload_upgrades_empty_categories_to_explicit_unknown() -> None:
    upgraded = upgrade_legacy_extraction_payload(
        {
            "requirements": [],
            "deadlines": [
                {
                    "label": "submission",
                    "value": "2026-09-30T12:00:00Z",
                    "normalized_at": "2026-09-30T12:00:00Z",
                    "citation": {
                        "field": "deadline_at",
                        "quote": "2026-09-30T12:00:00Z",
                    },
                }
            ],
            "gaps": [],
        }
    )

    assert upgraded["requirements_status"] == "unknown"
    assert upgraded["deadlines_status"] == "found"
