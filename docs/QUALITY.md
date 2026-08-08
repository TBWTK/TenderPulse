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
- [x] Manual EIS XML/ZIP import and bounded TED/USA queries share the same canonical downstream contract.
- [x] GigaChat malformed output/unsupported citations fail validation and known transport failures remain visible.
- [x] Empty requirement/deadline categories carry explicit `found`/`not_present`/`unknown` coverage status.
- [x] A validated AI result is cached by record/input/prompt/model and reconstructable from stored hashes.

## Regression gates

- [x] pytest unit/contract suite with branch coverage ≥80%.
- [x] PostgreSQL integration proves migrations, one-current constraint and live replay idempotency.
- [x] dbt source/not-null/unique/relationships/accepted-values tests pass for all marts.
- [x] Ruff formatting/lint and strict mypy pass.
- [x] Docker Compose config and container health checks pass.
- [x] Server-rendered dashboard and API product flows pass integration tests; browser visual QA was not requested.
- [x] Live TED/USA/GigaChat smokes are bounded and record no secret values; live EIS remains blocked.
- [x] In-app alert replay is idempotent and new record/profile versions produce distinct events.

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
