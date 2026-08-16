from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from tenderpulse.pilot_eval import (
    ArtifactValidationError,
    BlindLabelArtifact,
    HumanReviewArtifact,
    HumanReviewEvaluationReport,
    PilotEvaluationReport,
    PilotPredictionArtifact,
    PilotSampleArtifact,
    build_prediction_artifact,
    canonical_artifact_sha256,
    evaluate_human_review,
    evaluate_pilot,
    import_human_review_markdown,
    render_human_review_markdown,
)
from tenderpulse.profiles import CompanyProfile

CAPTURED_AT = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
LABELS_FROZEN_AT = CAPTURED_AT + timedelta(minutes=5)
PREDICTED_AT = LABELS_FROZEN_AT + timedelta(minutes=5)
PROFILE_SLUG = "cleaning-moscow"
PROFILE_VERSION = 2
TRACKED_EVAL_DIR = Path(__file__).parents[1] / "evals" / "cleaning_pilot_2026-08-16"


def _filled_review_markdown(
    sample: PilotSampleArtifact,
    labels: list[str] | None = None,
) -> bytes:
    review_labels = labels or ["not_relevant"] * len(sample.items)
    relevant_count = sum(label == "relevant" for label in review_labels)
    not_relevant_count = sum(label == "not_relevant" for label in review_labels)
    insufficient_count = sum(label == "insufficient_evidence" for label in review_labels)
    lines = [
        "# Human review packet — «Чистая территория»",
        "",
        "Дата ревью: **16.08.2026**.",
        "",
        (
            "**Итог:** `relevant` — "
            f"**{relevant_count} из {len(review_labels)}**; `not_relevant` — "
            f"**{not_relevant_count} из {len(review_labels)}**; "
            f"`insufficient_evidence` — **{insufficient_count} из {len(review_labels)}**."
        ),
        "",
        (
            "| № | Закупка | Предмет | НМЦК | Проверенные место исполнения / "
            "окончание подачи | Ваш label | Причина | Требования к опыту / лицензиям |"
        ),
        "| ---: | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for index, (item, label) in enumerate(zip(sample.items, review_labels, strict=True), start=1):
        amount = f"{item.amount:.2f}" if item.amount is not None else "unknown"
        currency = item.currency or ""
        lines.append(
            f"| {index} | [{item.source_record_id}]({item.source_url}) | {item.title} | "
            f"{amount} {currency} | Москва / **20.08.2026 09:00 МСК** | "
            f"`{label}` | Проверенная причина для строки {index}. | "
            "Специальная лицензия не указана. |"
        )
    return ("\n".join(lines) + "\n").encode()


def _uuid(index: int) -> str:
    return str(UUID(int=index + 1))


def _sample_item(
    index: int,
    *,
    delivery_mode: str = "onsite",
    region_code: str | None = "RU-MOW",
) -> dict[str, Any]:
    return {
        "sample_id": f"sample-{index:02d}",
        "source": "eis",
        "source_record_id": f"0123456789{index:09d}",
        "source_url": f"https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber={index}",
        "ingestion_run_id": _uuid(100 + index),
        "record_version_id": _uuid(200 + index),
        "record_version": 1,
        "raw_sha256": f"{index + 1:064x}",
        "current": True,
        "title": f"Услуги по уборке, пример {index}",
        "description": "Поддерживающая уборка помещений и прилегающей территории.",
        "buyer_name": f"Заказчик {index}",
        "region_code": region_code,
        "delivery_mode": delivery_mode,
        "amount": "750000.00",
        "currency": "RUB",
        "classifications": ["OKPD2:81.21"],
    }


def _sample_payload(count: int = 3) -> dict[str, Any]:
    return {
        "schema_version": "pilot-sample/v1",
        "capture_id": _uuid(50),
        "captured_at": CAPTURED_AT,
        "source": "eis",
        "items": [_sample_item(index) for index in range(count)],
    }


def _sample(count: int = 3) -> PilotSampleArtifact:
    return PilotSampleArtifact.model_validate(_sample_payload(count))


def _label(
    index: int,
    *,
    label: str = "relevant",
    geography: str = "in_scope",
    budget: str = "in_range",
    qualification: str = "unknown_below_review_trigger",
    confidence: float = 0.75,
    confidence_band: str = "medium",
    primary_reason_code: str = "REL_CLEANING_PREMISES",
) -> dict[str, Any]:
    return {
        "sample_id": f"sample-{index:02d}",
        "label": label,
        "primary_reason_code": primary_reason_code,
        "secondary_reason_codes": [],
        "short_note": f"Blind domain judgement for sample {index}",
        "confidence": confidence,
        "confidence_band": confidence_band,
        "geography": geography,
        "budget": budget,
        "qualification": qualification,
        "evidence_fields": ["title"],
    }


def _labels_payload(
    sample: PilotSampleArtifact,
    labels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "pilot-labels/v1",
        "sample_sha256": canonical_artifact_sha256(sample),
        "profile_slug": PROFILE_SLUG,
        "profile_version": PROFILE_VERSION,
        "rubric_version": "clean-territory-blind-v1",
        "labeler_kind": "agent",
        "frozen_at": LABELS_FROZEN_AT,
        "labels": labels
        if labels is not None
        else [_label(index) for index in range(len(sample.items))],
    }


def _labels(
    sample: PilotSampleArtifact,
    labels: list[dict[str, Any]] | None = None,
) -> BlindLabelArtifact:
    return BlindLabelArtifact.model_validate(_labels_payload(sample, labels))


def _prediction(
    sample: PilotSampleArtifact,
    index: int,
    *,
    decision: str = "recommended",
    score: int = 80,
) -> dict[str, Any]:
    item = sample.items[index]
    return {
        "sample_id": item.sample_id,
        "record_version_id": item.record_version_id,
        "record_version": item.record_version,
        "decision": decision,
        "score": score,
        "reason_codes": ["keyword_match"],
    }


def _predictions_payload(
    sample: PilotSampleArtifact,
    labels: BlindLabelArtifact,
    predictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "pilot-predictions/v1",
        "sample_sha256": canonical_artifact_sha256(sample),
        "labels_sha256": canonical_artifact_sha256(labels),
        "profile_slug": PROFILE_SLUG,
        "profile_version": PROFILE_VERSION,
        "policy_version": "deterministic-matcher/v1",
        "generated_at": PREDICTED_AT,
        "predictions": predictions
        if predictions is not None
        else [_prediction(sample, index) for index in range(len(sample.items))],
    }


def _predictions(
    sample: PilotSampleArtifact,
    labels: BlindLabelArtifact,
    predictions: list[dict[str, Any]] | None = None,
) -> PilotPredictionArtifact:
    return PilotPredictionArtifact.model_validate(_predictions_payload(sample, labels, predictions))


def test_artifact_schemas_accept_complete_typed_lineage() -> None:
    sample = _sample()
    labels = _labels(sample)
    predictions = _predictions(sample, labels)

    assert sample.schema_version == "pilot-sample/v1"
    assert sample.items[0].source == "eis"
    assert sample.items[0].record_version == 1
    assert len(sample.items[0].raw_sha256) == 64
    assert labels.profile_version == PROFILE_VERSION
    assert predictions.profile_version == PROFILE_VERSION


def test_tracked_eis_sample_is_frozen_bounded_and_matcher_blind() -> None:
    sample_path = TRACKED_EVAL_DIR / "sample.json"
    raw = sample_path.read_text(encoding="utf-8")
    sample = PilotSampleArtifact.model_validate_json(raw)

    assert len(sample.items) == sample.sample_count == 50
    assert len({item.sample_id for item in sample.items}) == 50
    assert len(sample.captures) == 2
    assert sum(capture.selected_count for capture in sample.captures) == 50
    assert all(capture.limit <= 50 for capture in sample.captures)
    assert all(item.current and item.lifecycle in {"active", "planned"} for item in sample.items)
    assert "matcher_decision" not in raw
    assert "matcher_score" not in raw
    assert "matcher_reasons" not in raw


def test_tracked_agent_eval_artifacts_join_and_reproduce_report() -> None:
    sample = PilotSampleArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "sample.json").read_text(encoding="utf-8")
    )
    labels = BlindLabelArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "labels.json").read_text(encoding="utf-8")
    )
    predictions = PilotPredictionArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "predictions.json").read_text(encoding="utf-8")
    )
    saved_report = json.loads((TRACKED_EVAL_DIR / "report.json").read_text(encoding="utf-8"))

    report = evaluate_pilot(sample, labels, predictions)

    assert report.model_dump(mode="json") == saved_report
    assert sum(label.label == "not_relevant" for label in labels.labels) == 44
    assert sum(label.label == "insufficient_evidence" for label in labels.labels) == 6
    assert sum(prediction.decision == "review" for prediction in predictions.predictions) == 1
    assert report.metrics.provisional_agent_actionable_precision is None
    assert report.metrics.bounded_sample_recall is None
    assert report.metrics.hard_onsite_geography_false_admissions == 0
    assert any(
        item.sample_id == "eis:0373200104826000065:v1" for item in report.human_review_shortlist
    )
    assert render_human_review_markdown(sample, report) == (
        TRACKED_EVAL_DIR / "HUMAN_REVIEW.md"
    ).read_text(encoding="utf-8")


def test_tracked_baseline_snapshot_reproduces_pre_fix_report() -> None:
    sample = PilotSampleArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "sample.json").read_text(encoding="utf-8")
    )
    labels = BlindLabelArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "labels.json").read_text(encoding="utf-8")
    )
    predictions = PilotPredictionArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "predictions-baseline.json").read_text(encoding="utf-8")
    )
    saved_report = json.loads(
        (TRACKED_EVAL_DIR / "report-baseline.json").read_text(encoding="utf-8")
    )

    report = evaluate_pilot(sample, labels, predictions)

    assert report.model_dump(mode="json") == saved_report
    assert {prediction.decision for prediction in predictions.predictions} == {"not_relevant"}
    assert report.metrics.matcher_actionable_coverage == 0


@pytest.mark.parametrize(
    "missing_field",
    [
        "source_record_id",
        "source_url",
        "ingestion_run_id",
        "record_version_id",
        "record_version",
        "raw_sha256",
    ],
)
def test_sample_schema_rejects_missing_lineage(missing_field: str) -> None:
    payload = _sample_payload(1)
    del payload["items"][0][missing_field]

    with pytest.raises(ValidationError, match=missing_field):
        PilotSampleArtifact.model_validate(payload)


def test_artifact_schema_rejects_unknown_schema_version() -> None:
    payload = _sample_payload()
    payload["schema_version"] = "pilot-sample/v999"

    with pytest.raises(ValidationError, match="schema_version"):
        PilotSampleArtifact.model_validate(payload)


def test_every_artifact_rejects_duplicate_sample_ids() -> None:
    sample_payload = _sample_payload(2)
    sample_payload["items"][1]["sample_id"] = sample_payload["items"][0]["sample_id"]
    with pytest.raises(ValidationError, match="duplicate sample IDs"):
        PilotSampleArtifact.model_validate(sample_payload)

    sample = _sample(2)
    label_payload = _labels_payload(sample)
    label_payload["labels"][1]["sample_id"] = label_payload["labels"][0]["sample_id"]
    with pytest.raises(ValidationError, match="duplicate sample IDs"):
        BlindLabelArtifact.model_validate(label_payload)

    labels = _labels(sample)
    prediction_payload = _predictions_payload(sample, labels)
    prediction_payload["predictions"][1]["sample_id"] = prediction_payload["predictions"][0][
        "sample_id"
    ]
    with pytest.raises(ValidationError, match="duplicate sample IDs"):
        PilotPredictionArtifact.model_validate(prediction_payload)


@pytest.mark.parametrize("leaked_field", ["matcher_decision", "matcher_score", "matcher_reasons"])
def test_blind_label_schema_rejects_matcher_leakage(leaked_field: str) -> None:
    sample = _sample(1)
    payload = _labels_payload(sample)
    payload["labels"][0][leaked_field] = "leaked"

    with pytest.raises(ValidationError, match=leaked_field):
        BlindLabelArtifact.model_validate(payload)


@pytest.mark.parametrize("artifact_name", ["labels", "predictions"])
def test_evaluator_rejects_label_or_prediction_universe_mismatch(artifact_name: str) -> None:
    sample = _sample(3)
    labels_payload = _labels_payload(sample)
    if artifact_name == "labels":
        labels_payload["labels"][2]["sample_id"] = "sample-outside-capture"
    labels = BlindLabelArtifact.model_validate(labels_payload)

    prediction_payload = _predictions_payload(sample, labels)
    if artifact_name == "predictions":
        prediction_payload["predictions"][2]["sample_id"] = "sample-outside-capture"
    predictions = PilotPredictionArtifact.model_validate(prediction_payload)

    with pytest.raises(ArtifactValidationError, match="sample ID universe"):
        evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)


@pytest.mark.parametrize(
    ("mismatch_field", "mismatch_value"),
    [("profile_slug", "another-company"), ("profile_version", 3)],
)
def test_evaluator_rejects_profile_mismatch(
    mismatch_field: str,
    mismatch_value: str | int,
) -> None:
    sample = _sample()
    labels = _labels(sample)
    prediction_payload = _predictions_payload(sample, labels)
    prediction_payload[mismatch_field] = mismatch_value
    predictions = PilotPredictionArtifact.model_validate(prediction_payload)

    with pytest.raises(ArtifactValidationError, match="profile"):
        evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)


def test_evaluator_rejects_record_version_lineage_mismatch() -> None:
    sample = _sample()
    labels = _labels(sample)
    prediction_payload = _predictions_payload(sample, labels)
    prediction_payload["predictions"][0]["record_version_id"] = _uuid(999)
    predictions = PilotPredictionArtifact.model_validate(prediction_payload)

    with pytest.raises(ArtifactValidationError, match="record version lineage"):
        evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)


def test_predictions_link_exact_frozen_labels_and_are_generated_after_them() -> None:
    sample = _sample()
    labels = _labels(sample)

    wrong_hash_payload = _predictions_payload(sample, labels)
    wrong_hash_payload["labels_sha256"] = "f" * 64
    wrong_hash_predictions = PilotPredictionArtifact.model_validate(wrong_hash_payload)
    with pytest.raises(ArtifactValidationError, match="labels hash"):
        evaluate_pilot(sample, labels, wrong_hash_predictions, minimum_sample_size=1)

    early_payload = _predictions_payload(sample, labels)
    early_payload["generated_at"] = labels.frozen_at
    early_predictions = PilotPredictionArtifact.model_validate(early_payload)
    with pytest.raises(ArtifactValidationError, match="after labels were frozen"):
        evaluate_pilot(sample, labels, early_predictions, minimum_sample_size=1)


def test_evaluator_default_gate_requires_fifty_records() -> None:
    sample = _sample(3)
    labels = _labels(sample)
    predictions = _predictions(sample, labels)

    with pytest.raises(ArtifactValidationError, match="minimum sample size is 50"):
        evaluate_pilot(sample, labels, predictions)


def test_metrics_report_confusion_precision_recall_abstention_and_geography_safety() -> None:
    sample = _sample(6)
    label_values = [
        _label(0, label="relevant"),
        _label(1, label="relevant"),
        _label(
            2,
            label="not_relevant",
            budget="below_min",
            primary_reason_code="NR_BUDGET_BELOW_MIN",
        ),
        _label(
            3,
            label="insufficient_evidence",
            geography="unknown",
            confidence=0.55,
            confidence_band="low",
            primary_reason_code="IE_GEO_MISSING_OR_AMBIGUOUS",
        ),
        _label(
            4,
            label="insufficient_evidence",
            geography="outside_direct_scope_contractor_unverified",
            primary_reason_code="IE_GEO_OUTSIDE_CONTRACTOR_UNVERIFIED",
        ),
        _label(
            5,
            label="not_relevant",
            qualification="explicit_specialized_blocker",
            primary_reason_code="NR_SCOPE_PEST_CONTROL",
        ),
    ]
    labels = _labels(sample, label_values)
    prediction_values = [
        _prediction(sample, 0, decision="recommended"),
        _prediction(sample, 1, decision="not_relevant", score=15),
        _prediction(sample, 2, decision="review", score=55),
        _prediction(sample, 3, decision="review", score=45),
        _prediction(sample, 4, decision="recommended"),
        _prediction(sample, 5, decision="not_relevant", score=10),
    ]
    predictions = _predictions(sample, labels, prediction_values)

    report = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)

    assert report.metrics.confusion.true_positive == 1
    assert report.metrics.confusion.false_positive == 1
    assert report.metrics.confusion.false_negative == 1
    assert report.metrics.confusion.true_negative == 1
    assert report.metrics.provisional_agent_actionable_precision == pytest.approx(1 / 2)
    assert report.metrics.bounded_sample_recall == pytest.approx(1 / 2)
    assert report.metrics.agent_abstention_rate == pytest.approx(2 / 6)
    assert report.metrics.agent_label_coverage == pytest.approx(4 / 6)
    assert report.metrics.matcher_actionable_coverage == pytest.approx(4 / 6)
    assert report.metrics.hard_onsite_geography_false_admissions == 1


def test_zero_denominators_are_explicit_unknown_not_zero_or_one() -> None:
    sample = _sample(2)
    labels = _labels(
        sample,
        [
            _label(
                0,
                label="not_relevant",
                budget="below_min",
                primary_reason_code="NR_BUDGET_BELOW_MIN",
            ),
            _label(
                1,
                label="not_relevant",
                qualification="explicit_specialized_blocker",
                primary_reason_code="NR_SCOPE_PEST_CONTROL",
            ),
        ],
    )
    predictions = _predictions(
        sample,
        labels,
        [
            _prediction(sample, 0, decision="not_relevant", score=5),
            _prediction(sample, 1, decision="not_relevant", score=10),
        ],
    )

    report = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)

    assert report.metrics.provisional_agent_actionable_precision is None
    assert report.metrics.bounded_sample_recall is None


def test_canonical_artifact_hash_is_deterministic_and_content_sensitive() -> None:
    content = {"z": 3, "nested": {"b": [2, 1], "a": "value"}}
    reordered = {"nested": {"a": "value", "b": [2, 1]}, "z": 3}
    changed = deepcopy(content)
    changed["nested"]["a"] = "different"

    assert canonical_artifact_sha256(content) == canonical_artifact_sha256(reordered)
    assert canonical_artifact_sha256(content) != canonical_artifact_sha256(changed)
    assert len(canonical_artifact_sha256(content)) == 64


def test_report_preserves_exact_input_hashes() -> None:
    sample = _sample()
    labels = _labels(sample)
    predictions = _predictions(sample, labels)

    report = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)

    assert report.sample_sha256 == canonical_artifact_sha256(sample)
    assert report.labels_sha256 == canonical_artifact_sha256(labels)
    assert report.predictions_sha256 == canonical_artifact_sha256(predictions)


def test_prediction_snapshot_is_built_from_frozen_sample_after_labels() -> None:
    sample = _sample(1)
    labels = _labels(sample)
    profile = CompanyProfile(
        slug=PROFILE_SLUG,
        version=PROFILE_VERSION,
        name="Чистая территория",
        capabilities=("уборка помещений",),
        positive_keywords=("уборка помещений",),
        classification_prefixes={"OKPD2": ("81.21",)},
        countries=("RU",),
        base_region="RU-MOW",
        service_regions=("RU-MOW", "RU-MOS"),
        delivery_mode="onsite",
        min_amount="500000",
        max_amount="25000000",
        review_above_amount="1000000",
    )

    predictions = build_prediction_artifact(
        sample,
        labels,
        profile,
        generated_at=PREDICTED_AT,
        policy_version="deterministic-matcher/v1",
    )

    assert predictions.sample_sha256 == canonical_artifact_sha256(sample)
    assert predictions.labels_sha256 == canonical_artifact_sha256(labels)
    assert predictions.profile_version == PROFILE_VERSION
    assert predictions.predictions[0].decision == "recommended"
    assert predictions.predictions[0].reason_codes == (
        "classification",
        "keywords",
        "geography_service_region",
        "budget",
    )


def test_human_review_shortlist_is_prioritized_deterministic_and_bounded() -> None:
    sample = _sample(16)
    labels_values = [_label(index) for index in range(16)]
    labels_values[0] = _label(
        0,
        label="insufficient_evidence",
        geography="outside_direct_scope_contractor_unverified",
        primary_reason_code="IE_GEO_OUTSIDE_CONTRACTOR_UNVERIFIED",
    )
    labels_values[1] = _label(1, label="relevant")
    labels_values[2] = _label(
        2,
        label="insufficient_evidence",
        geography="unknown",
        confidence=0.55,
        confidence_band="low",
        primary_reason_code="IE_GEO_MISSING_OR_AMBIGUOUS",
    )
    labels_values[3] = _label(3, confidence=0.55, confidence_band="low")
    labels_values[4] = _label(
        4,
        label="insufficient_evidence",
        geography="unknown",
        primary_reason_code="IE_DEADLINE_MISSING_OR_AMBIGUOUS",
    )
    labels = _labels(sample, labels_values)

    predictions_values = [_prediction(sample, index) for index in range(16)]
    predictions_values[0] = _prediction(sample, 0, decision="recommended", score=80)
    predictions_values[1] = _prediction(sample, 1, decision="not_relevant", score=20)
    predictions_values[4] = _prediction(sample, 4, decision="review", score=35)
    predictions = _predictions(sample, labels, predictions_values)

    report = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)
    repeated = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)

    shortlist = report.human_review_shortlist
    assert 10 <= len(shortlist) <= 15
    assert len({item.sample_id for item in shortlist}) == len(shortlist)
    assert shortlist[0].sample_id == "sample-00"
    assert "hard_onsite_geography_false_admission" in shortlist[0].priority_reasons
    review_by_id = {item.sample_id: item for item in shortlist}
    assert "agent_insufficient_evidence" in review_by_id["sample-04"].priority_reasons
    assert shortlist == repeated.human_review_shortlist


def test_human_review_shortlist_limits_duplicate_titles_when_alternatives_exist() -> None:
    payload = _sample_payload(20)
    for item in payload["items"][:5]:
        item["title"] = "Одинаковое содержание автомобильных дорог"
    sample = PilotSampleArtifact.model_validate(payload)
    label_values = [_label(index) for index in range(20)]
    prediction_values = [_prediction(sample, index) for index in range(20)]
    for index in range(5):
        label_values[index] = _label(
            index,
            label="insufficient_evidence",
            geography="unknown",
            primary_reason_code="IE_SCOPE_MIXED_OR_LOT_UNKNOWN",
        )
        prediction_values[index] = _prediction(
            sample,
            index,
            decision="not_relevant",
            score=5,
        )
    labels = _labels(sample, label_values)
    predictions = _predictions(sample, labels, prediction_values)

    report = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)

    duplicate_count = sum(
        item.title == "Одинаковое содержание автомобильных дорог"
        for item in report.human_review_shortlist
    )
    assert duplicate_count <= 2
    assert len(report.human_review_shortlist) == 15


def test_human_review_markdown_is_derived_from_sample_without_prediction_leakage() -> None:
    sample = _sample(12)
    labels = _labels(sample)
    predictions = _predictions(sample, labels)
    report = evaluate_pilot(sample, labels, predictions, minimum_sample_size=1)

    markdown = render_human_review_markdown(sample, report)

    assert "0123456789000000000" in markdown
    assert "750000.00 RUB" in markdown
    assert sample.items[0].source_url in markdown
    assert "recommended" not in markdown
    assert "Blind domain judgement" not in markdown


def test_filled_human_review_import_preserves_exact_lineage_and_document_provenance() -> None:
    sample = _sample(3)
    agent_labels = _labels(sample)
    predictions = _predictions(sample, agent_labels)
    agent_report = evaluate_pilot(sample, agent_labels, predictions, minimum_sample_size=1)
    blank_packet = render_human_review_markdown(sample, agent_report).encode()
    document = _filled_review_markdown(
        sample,
        ["not_relevant", "relevant", "insufficient_evidence"],
    )

    artifact = import_human_review_markdown(
        sample,
        agent_report,
        blank_packet=blank_packet,
        document=document,
        source_document_name="HUMAN_REVIEW_filled.md",
        imported_at=PREDICTED_AT + timedelta(minutes=10),
    )

    assert artifact.schema_version == "pilot-human-reviews/v1"
    assert artifact.labeler_kind == "human"
    assert artifact.profile_slug == PROFILE_SLUG
    assert artifact.profile_version == PROFILE_VERSION
    assert artifact.sample_sha256 == canonical_artifact_sha256(sample)
    assert artifact.blank_packet_sha256 == canonical_artifact_sha256(blank_packet)
    assert artifact.shortlist_report_sha256 == canonical_artifact_sha256(agent_report)
    assert artifact.source_document_sha256 == canonical_artifact_sha256(document)
    assert [review.label for review in artifact.reviews] == [
        "not_relevant",
        "relevant",
        "insufficient_evidence",
    ]
    assert [review.sample_id for review in artifact.reviews] == [
        item.sample_id for item in sample.items
    ]
    assert artifact.reviews[1].record_version_id == sample.items[1].record_version_id
    assert artifact.reviews[1].raw_sha256 == sample.items[1].raw_sha256
    assert artifact.reviews[1].checked_execution_and_deadline.startswith("Москва")


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (lambda value: value.replace(b"`not_relevant`", b"`unknown_label`", 1), "label"),
        (lambda value: value.replace(b"750000.00", b"750001.00", 1), "amount"),
        (
            lambda value: value.replace(b"0123456789000000000", b"0999999999999999999", 1),
            "shortlist universe",
        ),
        (lambda value: b"\n".join(value.splitlines()[:-1]) + b"\n", "row count"),
    ],
)
def test_filled_human_review_import_fails_loud_on_unverifiable_rows(
    mutation: Any,
    expected_error: str,
) -> None:
    sample = _sample(3)
    agent_labels = _labels(sample)
    predictions = _predictions(sample, agent_labels)
    agent_report = evaluate_pilot(sample, agent_labels, predictions, minimum_sample_size=1)
    document = mutation(_filled_review_markdown(sample))

    with pytest.raises(ArtifactValidationError, match=expected_error):
        import_human_review_markdown(
            sample,
            agent_report,
            blank_packet=render_human_review_markdown(sample, agent_report).encode(),
            document=document,
            source_document_name="HUMAN_REVIEW_filled.md",
            imported_at=PREDICTED_AT + timedelta(minutes=10),
        )


def test_human_review_metrics_are_explicitly_shortlist_only() -> None:
    sample = _sample(3)
    agent_labels = _labels(sample)
    predictions = _predictions(
        sample,
        agent_labels,
        [
            _prediction(sample, 0, decision="review", score=45),
            _prediction(sample, 1, decision="review", score=45),
            _prediction(sample, 2, decision="not_relevant", score=5),
        ],
    )
    agent_report = evaluate_pilot(sample, agent_labels, predictions, minimum_sample_size=1)
    item_by_id = {item.sample_id: item for item in sample.items}
    shortlist_sample = sample.model_copy(
        update={
            "items": tuple(
                item_by_id[item.sample_id] for item in agent_report.human_review_shortlist
            )
        }
    )
    label_by_id = {
        "sample-00": "not_relevant",
        "sample-01": "relevant",
        "sample-02": "insufficient_evidence",
    }
    reviews = import_human_review_markdown(
        sample,
        agent_report,
        blank_packet=render_human_review_markdown(sample, agent_report).encode(),
        document=_filled_review_markdown(
            shortlist_sample,
            [label_by_id[item.sample_id] for item in shortlist_sample.items],
        ),
        source_document_name="HUMAN_REVIEW_filled.md",
        imported_at=PREDICTED_AT + timedelta(minutes=10),
    )

    report = evaluate_human_review(sample, reviews, predictions, agent_report)

    assert report.schema_version == "pilot-human-review-report/v1"
    assert report.selection_scope == "agent_matcher_prioritized_shortlist"
    assert report.eligible_for_full_pilot_gate is False
    assert report.metrics.sample_size == 3
    assert report.metrics.confusion.model_dump() == {
        "true_positive": 1,
        "false_positive": 1,
        "false_negative": 0,
        "true_negative": 0,
    }
    assert report.metrics.shortlist_actionable_precision == pytest.approx(0.5)
    assert report.metrics.shortlist_recall == pytest.approx(1.0)
    assert report.metrics.human_abstention_rate == pytest.approx(1 / 3)
    assert report.metrics.human_label_coverage == pytest.approx(2 / 3)
    assert report.metrics.matcher_actionable_coverage == pytest.approx(2 / 3)
    assert report.human_reviews_sha256 == canonical_artifact_sha256(reviews)
    assert report.predictions_sha256 == canonical_artifact_sha256(predictions)


def test_tracked_human_review_artifacts_reproduce_scoped_report() -> None:
    human_reviews = HumanReviewArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "human-reviews.json").read_text(encoding="utf-8")
    )
    saved_report = HumanReviewEvaluationReport.model_validate_json(
        (TRACKED_EVAL_DIR / "human-report.json").read_text(encoding="utf-8")
    )
    sample = PilotSampleArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "sample.json").read_text(encoding="utf-8")
    )
    predictions = PilotPredictionArtifact.model_validate_json(
        (TRACKED_EVAL_DIR / "predictions.json").read_text(encoding="utf-8")
    )
    shortlist_report = PilotEvaluationReport.model_validate_json(
        (TRACKED_EVAL_DIR / "report.json").read_text(encoding="utf-8")
    )

    reproduced = evaluate_human_review(sample, human_reviews, predictions, shortlist_report)

    assert reproduced == saved_report
    assert human_reviews.source_document_sha256 == (
        "ac65fbdbf8b8623f55385c13990efa39265ba32741fcffa6898c0243f1d18c45"
    )
    assert len(human_reviews.reviews) == 15
    assert sum(review.label == "relevant" for review in human_reviews.reviews) == 1
    assert reproduced.metrics.confusion.model_dump() == {
        "true_positive": 1,
        "false_positive": 0,
        "false_negative": 0,
        "true_negative": 14,
    }
    assert reproduced.metrics.shortlist_actionable_precision == 1.0
    assert reproduced.metrics.shortlist_recall == 1.0
    assert reproduced.eligible_for_full_pilot_gate is False


def test_human_review_evaluation_rejects_unbound_shortlist_report() -> None:
    sample = _sample(3)
    agent_labels = _labels(sample)
    predictions = _predictions(sample, agent_labels)
    shortlist_report = evaluate_pilot(sample, agent_labels, predictions, minimum_sample_size=1)
    reviews = import_human_review_markdown(
        sample,
        shortlist_report,
        blank_packet=render_human_review_markdown(sample, shortlist_report).encode(),
        document=_filled_review_markdown(sample),
        source_document_name="HUMAN_REVIEW_filled.md",
        imported_at=PREDICTED_AT + timedelta(minutes=10),
    )
    tampered = reviews.model_copy(update={"shortlist_report_sha256": "f" * 64})

    with pytest.raises(ArtifactValidationError, match="shortlist report"):
        evaluate_human_review(sample, tampered, predictions, shortlist_report)
