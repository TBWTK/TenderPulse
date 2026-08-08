---
title: Текущее состояние
type: state
status: idle
updated: 2026-08-08
---

# Текущее состояние

## Active objective

Активного инженерного инкремента нет: проверенный TenderPulse MVP опубликован в `origin/main` и
передан пользователю. Следующая работа начинается только с нового согласованного продуктового результата.

## Acceptance criteria

- [x] Все заявленные MVP-capabilities сопоставлены с code/test/runtime/data evidence.
- [x] Product, architecture, data, UI, tests и docs описывают одинаковые границы MVP.
- [x] В tracked-файлах нет `.env`, private keys или заполненных GigaChat/token credentials.
- [x] Clean-ветка `main` опубликована в `origin/main`; local и remote SHA проверены на совпадение.

## Current verified state

- Реализованы bounded adapters TED Search API, официальный ЕИС RSS + безопасный XML/ZIP fallback и
  USAspending awards; downstream использует единый versioned canonical procurement model.
- Immutable raw artifacts, SHA-256, ingestion provenance, SCD2 history, source-scoped organizations,
  lots/classifications/geography и match evidence позволяют восстановить каждую рекомендацию.
- Два версионируемых профиля управляют TED CPV и USA keyword scope; UI показывает рекомендации,
  requirements/deadlines coverage, AI citations/gaps, аналитику, загрузку и alerts.
- Свежий regression checkpoint 08.08.2026: `121 passed`, branch coverage `86.57%`; Ruff lint/format и
  strict mypy прошли; dbt `PASS=53 WARN=0 ERROR=0`; Docker API/worker/PostgreSQL/MinIO healthy;
  dashboard вернул HTTP 200.
- Bounded live smokes TED, ЕИС, USAspending и GigaChat ранее прошли с TLS verification и сохранённым
  raw/run evidence; live external calls остаются opt-in и не принадлежат deterministic CI.
- `origin/main` создан обычным push без переписывания истории; upstream настроен, SHA сверяется через
  `git rev-parse HEAD` и `git ls-remote --heads origin main`.

## Changed areas

- MVP: adapters, canonical/history/identity, raw storage, API/worker, matching/AI evidence, profiles,
  alerts, analytics/dbt, migrations, Docker, UI, fixtures, tests и project documentation.
- Handoff checkpoint меняет только `docs/STATE.md` и `docs/ROADMAP.md`; production code/data не менялись.

## Decisions made

- USAspending остаётся outcome/history enrichment, не источником активных notices.
- Lakehouse boundary: S3-compatible immutable raw + PostgreSQL/pgvector canonical/serving + dbt marts.
- Межисточниковая organization identity не выводится из совпадения имени.
- ЕИС MVP использует официальный bounded RSS; full export/HTML scraping запрещены.
- Неизвестные значения остаются явными `unknown`; AI claims допустимы только с проверяемыми citations.

## Next exact step

Дождаться нового запроса пользователя и до изменения кода зафиксировать один проверяемый objective с
acceptance criteria и non-goals.

## Blockers

- Нет.

## Non-goals

- Полная историческая выгрузка или более 500 records за один запуск.
- Production auth/RBAC, tenant isolation, автоматическая подача заявки и юридическая гарантия требований.
- SAM.gov, прогноз вероятности победы, обучение собственной модели и третий MVP-профиль.
- Произвольные source URLs или неограниченный ad-hoc query вне allowlisted adapters.

## Verification

```bash
.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q
make lint
make dbt-test
docker compose config --quiet
docker compose ps
curl -sS -o /dev/null -w "%{http_code} %{size_download}\n" http://127.0.0.1:8010/
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py audit .
git rev-parse HEAD
git ls-remote --heads origin main
```
