from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.matching import TenderMatcher
from tenderpulse.domain.models import (
    ClassificationCode,
    LifecycleStatus,
    Lot,
    ProcurementRecord,
    RecordKind,
    SourceCode,
    SourceEvidence,
)
from tenderpulse.profiles import CompanyProfile, load_demo_profiles

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_CONFIG = ConfigDict(frozen=True, extra="forbid")


class ArtifactValidationError(ValueError):
    """Raised when separately frozen pilot artifacts cannot be compared safely."""


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone evidence")
    return value


def _validate_sha256(value: str) -> str:
    normalized = value.lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError("value must be a lowercase hexadecimal SHA-256")
    return normalized


class PilotCapture(BaseModel):
    model_config = _ARTIFACT_CONFIG

    run_id: UUID
    source: Literal["eis"]
    endpoint: str
    mode: Literal["live_bounded"]
    published_from: date
    published_to: date
    limit: int = Field(ge=1, le=50)
    record_count: int = Field(ge=0, le=50)
    active_count: int = Field(ge=0, le=50)
    selected_count: int = Field(ge=0, le=50)
    raw_sha256: str
    started_at: datetime
    finished_at: datetime
    observed_at: datetime

    @field_validator("raw_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("started_at", "finished_at", "observed_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @model_validator(mode="after")
    def validate_contract(self) -> PilotCapture:
        if self.endpoint != "https://zakupki.gov.ru/epz/order/extendedsearch/rss.html":
            raise ValueError("capture endpoint must be the official EIS RSS endpoint")
        if self.published_to < self.published_from:
            raise ValueError("capture published_to cannot precede published_from")
        if (self.published_to - self.published_from).days > 31:
            raise ValueError("capture window cannot exceed 31 days")
        if self.active_count > self.record_count:
            raise ValueError("capture active_count cannot exceed record_count")
        if self.selected_count > self.active_count:
            raise ValueError("capture selected_count cannot exceed active_count")
        return self


class PilotSampleItem(BaseModel):
    model_config = _ARTIFACT_CONFIG

    sample_id: str = Field(min_length=1)
    source: Literal["eis"]
    source_record_id: str = Field(pattern=r"^\d{19}$")
    source_url: str
    ingestion_run_id: UUID
    record_version_id: UUID
    record_version: int = Field(ge=1)
    raw_sha256: str
    current: Literal[True]
    title: str = Field(min_length=1)
    description: str = ""
    buyer_name: str | None = None
    region_code: str | None = None
    delivery_location: str | None = None
    delivery_mode: str = "unknown"
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    capture_run_id: UUID | None = None
    capture_raw_sha256: str | None = None
    published_at: datetime | None = None
    deadline_at: datetime | None = None
    lifecycle: Literal["active", "planned"] = "active"
    classifications: tuple[str, ...] | None = None

    @field_validator("raw_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("capture_raw_sha256")
    @classmethod
    def validate_capture_sha256(cls, value: str | None) -> str | None:
        return _validate_sha256(value) if value is not None else None

    @field_validator("published_at", "deadline_at")
    @classmethod
    def validate_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        return _require_aware(value) if value is not None else None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.netloc != "zakupki.gov.ru":
            raise ValueError("source_url must use the official EIS HTTPS host")
        return value

    @model_validator(mode="after")
    def validate_item(self) -> PilotSampleItem:
        if (self.amount is None) != (self.currency is None):
            raise ValueError("amount and currency must be known or unknown together")
        if (self.capture_run_id is None) != (self.capture_raw_sha256 is None):
            raise ValueError("capture run and raw SHA must be known or unknown together")
        return self


class PilotSampleArtifact(BaseModel):
    model_config = _ARTIFACT_CONFIG

    schema_version: Literal["pilot-sample/v1"]
    capture_id: UUID
    captured_at: datetime
    source: Literal["eis"]
    profile_slug: str | None = None
    evaluation_as_of: datetime | None = None
    sampling_method: str | None = None
    source_contract: str | None = None
    captures: tuple[PilotCapture, ...] = ()
    sample_count: int | None = Field(default=None, ge=0)
    sample_sha256: str | None = None
    items: tuple[PilotSampleItem, ...]

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @field_validator("evaluation_as_of")
    @classmethod
    def validate_evaluation_as_of(cls, value: datetime | None) -> datetime | None:
        return _require_aware(value) if value is not None else None

    @field_validator("sample_sha256")
    @classmethod
    def validate_sample_sha256(cls, value: str | None) -> str | None:
        return _validate_sha256(value) if value is not None else None

    @model_validator(mode="after")
    def validate_universe(self) -> PilotSampleArtifact:
        _require_unique_sample_ids(self.items)
        source_ids = [item.source_record_id for item in self.items]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("sample contains duplicate source record IDs")
        if self.sample_count is not None and self.sample_count != len(self.items):
            raise ValueError("sample_count does not equal items length")
        if self.sample_sha256 is not None:
            actual = _canonical_sample_items_sha256(self.items)
            if self.sample_sha256 != actual:
                raise ValueError("sample_sha256 does not match canonical items")
        if self.captures:
            capture_ids = {capture.run_id for capture in self.captures}
            if any(item.capture_run_id not in capture_ids for item in self.items):
                raise ValueError("sample item references an unknown capture run")
            if sum(capture.selected_count for capture in self.captures) != len(self.items):
                raise ValueError("capture selected_count does not equal sample size")
        return self


BlindLabelName = Literal["relevant", "not_relevant", "insufficient_evidence"]
GeographyLabel = Literal[
    "in_scope",
    "outside_direct_scope_contractor_unverified",
    "unknown",
    "conflicting",
]
BudgetLabel = Literal["in_range", "below_min", "above_max", "unknown", "invalid_or_non_rub"]
QualificationLabel = Literal[
    "unknown_below_review_trigger",
    "manual_review_required_gt_1m",
    "explicit_specialized_blocker",
    "unknown_due_missing_amount",
    "unknown_requirements",
]


class BlindPilotLabel(BaseModel):
    model_config = _ARTIFACT_CONFIG

    sample_id: str = Field(min_length=1)
    label: BlindLabelName
    primary_reason_code: str = Field(min_length=1)
    secondary_reason_codes: tuple[str, ...] = ()
    short_note: str = Field(min_length=1, max_length=1000)
    confidence: Decimal = Field(ge=0, le=1)
    confidence_band: Literal["high", "medium", "low"]
    geography: GeographyLabel
    budget: BudgetLabel
    qualification: QualificationLabel
    evidence_fields: tuple[str, ...] = Field(min_length=1)


class BlindLabelArtifact(BaseModel):
    model_config = _ARTIFACT_CONFIG

    schema_version: Literal["pilot-labels/v1"]
    sample_sha256: str
    profile_slug: str = Field(min_length=1)
    profile_version: int = Field(ge=1)
    rubric_version: str = Field(min_length=1)
    rubric_sha256: str | None = None
    labeler_kind: Literal["agent", "human"]
    frozen_at: datetime
    evaluation_as_of: datetime | None = None
    labels: tuple[BlindPilotLabel, ...]

    @field_validator("sample_sha256")
    @classmethod
    def validate_sample_sha(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("rubric_sha256")
    @classmethod
    def validate_rubric_sha(cls, value: str | None) -> str | None:
        return _validate_sha256(value) if value is not None else None

    @field_validator("frozen_at")
    @classmethod
    def validate_frozen_at(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @field_validator("evaluation_as_of")
    @classmethod
    def validate_optional_as_of(cls, value: datetime | None) -> datetime | None:
        return _require_aware(value) if value is not None else None

    @model_validator(mode="after")
    def validate_unique_labels(self) -> BlindLabelArtifact:
        _require_unique_sample_ids(self.labels)
        return self


class PilotPrediction(BaseModel):
    model_config = _ARTIFACT_CONFIG

    sample_id: str = Field(min_length=1)
    record_version_id: UUID
    record_version: int = Field(ge=1)
    decision: Literal["recommended", "review", "not_relevant", "expired"]
    score: Decimal = Field(ge=0, le=100)
    reason_codes: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


class PilotPredictionArtifact(BaseModel):
    model_config = _ARTIFACT_CONFIG

    schema_version: Literal["pilot-predictions/v1"]
    sample_sha256: str
    labels_sha256: str
    profile_slug: str = Field(min_length=1)
    profile_version: int = Field(ge=1)
    policy_version: str = Field(min_length=1)
    generated_at: datetime
    predictions: tuple[PilotPrediction, ...]

    @field_validator("sample_sha256", "labels_sha256")
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @model_validator(mode="after")
    def validate_unique_predictions(self) -> PilotPredictionArtifact:
        _require_unique_sample_ids(self.predictions)
        return self


class ConfusionCounts(BaseModel):
    model_config = _ARTIFACT_CONFIG

    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int


class PilotMetrics(BaseModel):
    model_config = _ARTIFACT_CONFIG

    sample_size: int
    confusion: ConfusionCounts
    provisional_agent_actionable_precision: float | None
    bounded_sample_recall: float | None
    agent_abstention_rate: float
    agent_label_coverage: float
    matcher_actionable_coverage: float
    hard_onsite_geography_false_admissions: int


class HumanReviewItem(BaseModel):
    model_config = _ARTIFACT_CONFIG

    sample_id: str
    source_url: str
    title: str
    agent_label: BlindLabelName
    matcher_decision: str
    confidence: Decimal
    priority_reasons: tuple[str, ...]


class PilotEvaluationReport(BaseModel):
    model_config = _ARTIFACT_CONFIG

    sample_sha256: str
    labels_sha256: str
    predictions_sha256: str
    profile_slug: str
    profile_version: int
    metrics: PilotMetrics
    human_review_shortlist: tuple[HumanReviewItem, ...]


def canonical_artifact_sha256(value: object) -> str:
    payload: object
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    elif isinstance(value, tuple) and all(isinstance(item, BaseModel) for item in value):
        payload = [item.model_dump(mode="json") for item in value]
    else:
        payload = value
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_sample_items_sha256(items: tuple[PilotSampleItem, ...]) -> str:
    payload = [item.model_dump(mode="json", exclude_unset=True) for item in items]
    return canonical_artifact_sha256(payload)


def build_prediction_artifact(
    sample: PilotSampleArtifact,
    labels: BlindLabelArtifact,
    profile: CompanyProfile,
    *,
    generated_at: datetime,
    policy_version: str,
) -> PilotPredictionArtifact:
    _require_aware(generated_at)
    sample_hash = canonical_artifact_sha256(sample)
    if labels.sample_sha256 != sample_hash:
        raise ArtifactValidationError("labels sample hash does not match the frozen sample")
    if labels.profile_slug != profile.slug or labels.profile_version != profile.version:
        raise ArtifactValidationError("label and company profile versions do not match")
    if generated_at <= labels.frozen_at:
        raise ArtifactValidationError("predictions must be generated after labels were frozen")

    matcher = TenderMatcher(now=lambda: sample.evaluation_as_of or sample.captured_at)
    predictions: list[PilotPrediction] = []
    for item in sample.items:
        recommendation = matcher.match(profile, _to_procurement_record(item, sample))
        predictions.append(
            PilotPrediction(
                sample_id=item.sample_id,
                record_version_id=item.record_version_id,
                record_version=item.record_version,
                decision=recommendation.decision.value,
                score=recommendation.score,
                reason_codes=tuple(reason.code for reason in recommendation.reasons),
                gaps=tuple(gap.value for gap in recommendation.gaps),
                blockers=tuple(blocker.value for blocker in recommendation.blockers),
            )
        )
    return PilotPredictionArtifact(
        schema_version="pilot-predictions/v1",
        sample_sha256=sample_hash,
        labels_sha256=canonical_artifact_sha256(labels),
        profile_slug=profile.slug,
        profile_version=profile.version,
        policy_version=policy_version,
        generated_at=generated_at,
        predictions=tuple(predictions),
    )


def evaluate_pilot(
    sample: PilotSampleArtifact,
    labels: BlindLabelArtifact,
    predictions: PilotPredictionArtifact,
    *,
    minimum_sample_size: int = 50,
) -> PilotEvaluationReport:
    if len(sample.items) < minimum_sample_size:
        raise ArtifactValidationError(f"minimum sample size is {minimum_sample_size}")

    sample_hash = canonical_artifact_sha256(sample)
    labels_hash = canonical_artifact_sha256(labels)
    if labels.sample_sha256 != sample_hash or predictions.sample_sha256 != sample_hash:
        raise ArtifactValidationError("sample hash mismatch across artifacts")
    if predictions.labels_sha256 != labels_hash:
        raise ArtifactValidationError("predictions labels hash does not match frozen labels hash")
    if predictions.generated_at <= labels.frozen_at:
        raise ArtifactValidationError("predictions must be generated after labels were frozen")
    if (
        predictions.profile_slug != labels.profile_slug
        or predictions.profile_version != labels.profile_version
    ):
        raise ArtifactValidationError("profile mismatch between labels and predictions")
    if sample.profile_slug is not None and sample.profile_slug != labels.profile_slug:
        raise ArtifactValidationError("profile mismatch between sample and labels")

    items = {item.sample_id: item for item in sample.items}
    label_by_id = {label.sample_id: label for label in labels.labels}
    prediction_by_id = {prediction.sample_id: prediction for prediction in predictions.predictions}
    expected_ids = set(items)
    if set(label_by_id) != expected_ids or set(prediction_by_id) != expected_ids:
        raise ArtifactValidationError("sample ID universe mismatch across artifacts")
    for sample_id, item in items.items():
        prediction = prediction_by_id[sample_id]
        if (
            prediction.record_version_id != item.record_version_id
            or prediction.record_version != item.record_version
        ):
            raise ArtifactValidationError(f"record version lineage mismatch for {sample_id}")

    tp = fp = fn = tn = abstentions = hard_geo = matcher_actionable = 0
    actionable = {"recommended", "review"}
    for sample_id in sorted(expected_ids):
        label = label_by_id[sample_id]
        prediction = prediction_by_id[sample_id]
        is_actionable = prediction.decision in actionable
        matcher_actionable += int(is_actionable)
        if label.label == "insufficient_evidence":
            abstentions += 1
        elif label.label == "relevant":
            if is_actionable:
                tp += 1
            else:
                fn += 1
        elif is_actionable:
            fp += 1
        else:
            tn += 1
        if prediction.decision == "recommended" and label.geography in {
            "outside_direct_scope_contractor_unverified",
            "conflicting",
        }:
            hard_geo += 1

    total = len(items)
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    metrics = PilotMetrics(
        sample_size=total,
        confusion=ConfusionCounts(
            true_positive=tp,
            false_positive=fp,
            false_negative=fn,
            true_negative=tn,
        ),
        provisional_agent_actionable_precision=(
            tp / precision_denominator if precision_denominator else None
        ),
        bounded_sample_recall=tp / recall_denominator if recall_denominator else None,
        agent_abstention_rate=abstentions / total,
        agent_label_coverage=(total - abstentions) / total,
        matcher_actionable_coverage=matcher_actionable / total,
        hard_onsite_geography_false_admissions=hard_geo,
    )
    shortlist = _human_review_shortlist(items, label_by_id, prediction_by_id)
    return PilotEvaluationReport(
        sample_sha256=sample_hash,
        labels_sha256=labels_hash,
        predictions_sha256=canonical_artifact_sha256(predictions),
        profile_slug=labels.profile_slug,
        profile_version=labels.profile_version,
        metrics=metrics,
        human_review_shortlist=shortlist,
    )


def render_human_review_markdown(
    sample: PilotSampleArtifact,
    report: PilotEvaluationReport,
) -> str:
    if report.sample_sha256 != canonical_artifact_sha256(sample):
        raise ArtifactValidationError("review report does not reference the supplied sample")
    items = {item.sample_id: item for item in sample.items}
    requested_ids = [item.sample_id for item in report.human_review_shortlist]
    if any(sample_id not in items for sample_id in requested_ids):
        raise ArtifactValidationError("review shortlist is outside the sample universe")

    lines = [
        "# Human review packet — «Чистая территория»",
        "",
        (
            "Проверка должна быть слепой: сначала откройте официальную карточку, выберите "
            "один label `relevant / not_relevant / insufficient_evidence` и запишите короткую "
            "причину. Только после фиксации всех ответов сравнивайте их с агентскими и "
            "системными artifacts."
        ),
        "",
        (
            "RSS не предоставил географию выполнения, deadline и классификаторы, если в "
            "таблице стоит `unknown`; эти сведения нужно проверять в официальной "
            "карточке/документации. Адрес заказчика сам по себе не считается местом работ."
        ),
        "",
        "| № | Закупка | Предмет | Сумма | RSS region/deadline | Ваш label | Причина |",
        "| ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for index, sample_id in enumerate(requested_ids, start=1):
        item = items[sample_id]
        amount = f"{item.amount} {item.currency}" if item.amount is not None else "unknown"
        region = item.region_code or "unknown"
        deadline = item.deadline_at.isoformat() if item.deadline_at is not None else "unknown"
        title = item.title.replace("|", "\\|")
        lines.append(
            f"| {index} | [{item.source_record_id}]({item.source_url}) | {title} | "
            f"{amount} | {region} / {deadline} |  |  |"
        )
    lines.extend(
        [
            "",
            (
                "Минимально проверьте: самостоятельный клининговый lot, фактическое место "
                "исполнения, окончание подачи, НМЦК каждого lot и требования к "
                "опыту/лицензиям."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _human_review_shortlist(
    items: dict[str, PilotSampleItem],
    labels: dict[str, BlindPilotLabel],
    predictions: dict[str, PilotPrediction],
) -> tuple[HumanReviewItem, ...]:
    ranked: list[tuple[tuple[int, Decimal, str], HumanReviewItem]] = []
    for sample_id, item in items.items():
        label = labels[sample_id]
        prediction = predictions[sample_id]
        reasons: list[str] = []
        priority = 6
        if prediction.decision in {"recommended", "review"} and label.label == "not_relevant":
            reasons.append("system_actionable_vs_blind_not_relevant")
            priority = min(priority, 0)
        if prediction.decision == "recommended" and label.geography in {
            "outside_direct_scope_contractor_unverified",
            "conflicting",
        }:
            reasons.append("hard_onsite_geography_false_admission")
            priority = min(priority, 0)
        if prediction.decision in {"not_relevant", "expired"} and label.label == "relevant":
            reasons.append("system_rejected_vs_blind_relevant")
            priority = min(priority, 1)
        if (
            prediction.decision in {"recommended", "not_relevant", "expired"}
            and label.label == "insufficient_evidence"
        ):
            reasons.append("system_definite_vs_blind_insufficient_evidence")
            priority = min(priority, 2)
        if label.label == "insufficient_evidence":
            reasons.append("agent_insufficient_evidence")
            priority = min(priority, 3)
        if label.confidence_band == "low":
            reasons.append("low_agent_confidence")
            priority = min(priority, 3)
        if not reasons:
            reasons.append("deterministic_control_or_boundary_sample")
        review_item = HumanReviewItem(
            sample_id=sample_id,
            source_url=item.source_url,
            title=item.title,
            agent_label=label.label,
            matcher_decision=prediction.decision,
            confidence=label.confidence,
            priority_reasons=tuple(reasons),
        )
        ranked.append(((priority, label.confidence, sample_id), review_item))
    target = min(15, len(ranked))
    if len(ranked) >= 10:
        target = max(10, target)
    ordered = sorted(ranked, key=lambda pair: pair[0])
    selected: list[HumanReviewItem] = []
    deferred: list[HumanReviewItem] = []
    title_counts: dict[str, int] = {}
    for _rank, review_candidate in ordered:
        title_key = " ".join(review_candidate.title.casefold().split())
        if title_counts.get(title_key, 0) >= 2:
            deferred.append(review_candidate)
            continue
        selected.append(review_candidate)
        title_counts[title_key] = title_counts.get(title_key, 0) + 1
        if len(selected) == target:
            break
    if len(selected) < target:
        selected.extend(deferred[: target - len(selected)])
    return tuple(selected)


def _to_procurement_record(
    item: PilotSampleItem,
    sample: PilotSampleArtifact,
) -> ProcurementRecord:
    classifications = tuple(
        _classification_from_text(value) for value in (item.classifications or ())
    )
    return ProcurementRecord(
        source=SourceCode.EIS,
        source_record_id=item.source_record_id,
        kind=RecordKind.NOTICE,
        lifecycle=LifecycleStatus(item.lifecycle),
        title=item.title,
        description=item.description,
        buyer_name=item.buyer_name,
        classifications=classifications,
        countries=("RU",),
        region_codes=(item.region_code,) if item.region_code is not None else (),
        delivery_location=item.delivery_location,
        delivery_mode=ServiceDeliveryMode(item.delivery_mode),
        published_at=item.published_at,
        observed_at=sample.evaluation_as_of or sample.captured_at,
        deadline_at=item.deadline_at,
        lots=(
            Lot(
                source_lot_id="main",
                title=item.title,
                amount=item.amount,
                currency=item.currency,
                deadline_at=item.deadline_at,
                classifications=classifications,
            ),
        ),
        evidence=SourceEvidence(
            raw_sha256=item.raw_sha256,
            ingestion_run_id=item.ingestion_run_id,
            source_url=item.source_url,
        ),
    )


def _classification_from_text(value: str) -> ClassificationCode:
    system, separator, code = value.partition(":")
    if not separator or not system or not code:
        raise ArtifactValidationError(f"invalid classification value: {value}")
    return ClassificationCode(system=system, code=code)


def _require_unique_sample_ids(values: tuple[Any, ...]) -> None:
    sample_ids = [value.sample_id for value in values]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("artifact contains duplicate sample IDs")


def _load[ArtifactModel: BaseModel](
    path: Path,
    model: type[ArtifactModel],
) -> ArtifactModel:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tenderpulse.pilot_eval")
    commands = parser.add_subparsers(dest="command", required=True)
    predict = commands.add_parser("predict")
    predict.add_argument("sample", type=Path)
    predict.add_argument("labels", type=Path)
    predict.add_argument("--policy-version", required=True)
    predict.add_argument("--output", required=True, type=Path)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("sample", type=Path)
    evaluate.add_argument("labels", type=Path)
    evaluate.add_argument("predictions", type=Path)
    evaluate.add_argument("--output", type=Path)
    review = commands.add_parser("review")
    review.add_argument("sample", type=Path)
    review.add_argument("report", type=Path)
    review.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    sample = _load(args.sample, PilotSampleArtifact)
    if args.command == "review":
        report = _load(args.report, PilotEvaluationReport)
        args.output.write_text(
            render_human_review_markdown(sample, report),
            encoding="utf-8",
        )
        return

    labels = _load(args.labels, BlindLabelArtifact)
    if args.command == "predict":
        seed = next(
            (profile for profile in load_demo_profiles() if profile.slug == labels.profile_slug),
            None,
        )
        if seed is None:
            raise ArtifactValidationError(f"profile seed not found: {labels.profile_slug}")
        artifact = build_prediction_artifact(
            sample,
            labels,
            seed.model_copy(update={"version": labels.profile_version}),
            generated_at=datetime.now(UTC),
            policy_version=args.policy_version,
        )
        _write_json(args.output, artifact)
        return

    report = evaluate_pilot(
        sample,
        labels,
        _load(args.predictions, PilotPredictionArtifact),
    )
    if args.output is None:
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        _write_json(args.output, report)


def _write_json(path: Path, artifact: BaseModel) -> None:
    output = json.dumps(artifact.model_dump(mode="json"), ensure_ascii=False, indent=2)
    path.write_text(f"{output}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
