---
title: Качество
type: quality
status: draft
updated: 2026-08-08
---

# Качество

## Capability evals

- [x] `IT Integrator` ranks a software/data notice above unrelated medical/construction fixtures and lists feature evidence.
- [x] `MedLab Supplier` ranks a medical/lab notice above unrelated IT/construction fixtures and lists feature evidence.
- [x] A changed source payload creates version 2 and preserves version 1; an identical replay is a no-op.
- [x] A recommendation can be reconstructed from profile version, record version, raw SHA and match evidence.
- [x] Missing deadline/amount/winner appears as `unknown`/gap and never as zero, epoch or inferred organization.
- [x] Live ЕИС RSS, manual ЕИС XML/ZIP and bounded TED/USA queries share the same canonical downstream contract.
- [x] GigaChat malformed output/unsupported citations fail validation and known transport failures remain visible.
- [x] Empty requirement/deadline categories carry explicit `found`/`not_present`/`unknown` coverage status.
- [x] A validated AI result is cached by record/input/prompt/model and reconstructable from stored hashes.
- [x] Buyer/supplier normalization is source-scoped, preserves aliases/raw/version links and backfills all
  existing SCD2 versions without guessing cross-source identity.
- [x] Award outcome projection exposes buyer, winner, amount/currency and raw evidence; partial or
  mixed-currency lots do not become a false total.
- [x] Opt-in webhook uses a stable idempotency key, retries only retryable failures and stores attempts
  without destination URL or response body.

## Regression gates

- [x] pytest unit/contract suite with branch coverage ≥80%.
- [x] PostgreSQL integration proves migrations, one-current constraint and live replay idempotency.
- [x] dbt source/not-null/unique/relationships/accepted-values tests pass for all marts.
- [x] Ruff formatting/lint and strict mypy pass.
- [x] Docker Compose config and container health checks pass.
- [x] Server-rendered dashboard and API product flows pass integration tests; browser visual QA was not requested.
- [x] Live TED/ЕИС/USA/GigaChat smokes are bounded and record no secret values; ЕИС replay preserves one
  canonical version while recording each run and raw hash.
- [x] In-app alert replay is idempotent and new record/profile versions produce distinct events.
- [x] Alembic `0004..0005`, organization/outcome marts and 48 dbt data tests pass on Docker PostgreSQL.

## Verification commands

```bash
uv sync --all-extras --dev
make test
make lint
make dbt-test
docker compose config --quiet
make verify
LIVE_SOURCE_TESTS=1 uv run pytest -q -m live_source
LIVE_LLM_TESTS=1 uv run pytest -q -m live_llm
```

## Нефункциональные требования

- Default ingestion limit: 100 records/source/run; hard application limit: 500.
- Live ЕИС limit: 50 records/one RSS page and at most 31 days per run; response body limit: 2 MiB.
- External HTTP connect/read timeout: 10/30 seconds; retries only for idempotent reads and 429/5xx.
- No live external call in default CI and no TLS verification bypass in any environment.
- Raw object is committed before canonical row; canonical transaction rolls back on invalid state.
- Structured logs include correlation/run IDs and redact configured secret field names.
- No latency SLO is claimed before Docker measurements; UI must show job freshness and failure state.

## Test-first evidence protocol

For a behavioral change, commit order within the diff is conceptual: acceptance/eval → observed failure
signature → implementation → regression. `docs/STATE.md` records only fresh command evidence; documentation
alone cannot close a criterion. A source fixture is evidence of a parser contract, not proof that the live
source is available today.
