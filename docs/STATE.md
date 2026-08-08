---
title: Текущее состояние
type: state
status: active
updated: 2026-08-08
---

# Текущее состояние

## Active objective

Закрыть сквозной normalization/outcomes/alerts slice: сделать source-scoped SSOT покупателей и
поставщиков, показать прослеживаемые результаты контрактов и подготовить opt-in внешний alert delivery,
не ослабляя bounded ingestion и правило explicit unknown.

## Acceptance criteria

- [x] Buyer/supplier aliases нормализуются одним модулем, сохраняют source/raw/version evidence и не
  объединяются между источниками без устойчивого identifier.
- [x] Current award outcomes доступны через API, dbt mart и dashboard с winner, amount/currency, buyer и
  raw SHA; отсутствующие или конфликтующие суммы остаются явно unknown/conflicting.
- [x] Внешний webhook alert выключен по умолчанию, использует idempotency key и сохраняет отдельные
  delivered/failed attempts без response body или secret destination.
- [x] Full pytest/coverage, Ruff, mypy, dbt, Compose health и project-control gates проходят после новых
  миграций; документация совпадает с реализацией.
- [ ] Локальный Git checkpoint создан; отправка в `origin/main` выполнена только после явного разрешения.

## Current verified state

- Foundation vertical slice реализован: immutable content-addressed raw, ingestion runs, canonical records,
  SCD2 versions, два профиля, matcher, lineage/recommendations API, Alembic, dbt и Docker Compose.
- `pytest`: 89 passed, branch coverage 86.79%; Ruff format/lint и strict mypy прошли 08.08.2026.
- Docker health подтверждён для API, worker, PostgreSQL/pgvector и MinIO; init migration/seed завершился с 0.
- dbt 1.12: 5 models + 48 data tests, `PASS=53 WARN=0 ERROR=0` на PostgreSQL Docker.
- GigaChat evidence v2 реализован через forced function call и явные coverage statuses; все claims требуют
  verbatim citation из canonical evidence fields. Validated/rejected/failed attempts сохраняются отдельно.
- 08.08.2026 live GigaChat smoke на TED `497954-2026` прошёл с TLS verification: модель
  `GigaChat-2:2.0.30.01` подтвердила deadline; requirements остались явно `unknown`.
- TED/USAspending live transport связан с scheduler и ручным allowlisted API. Два одинаковых TED
  запуска дали один raw hash и оставили `records=6/current_versions=6/total_versions=6`.
- USAspending bounded live cycle сохранил 2 awards; TED bounded cycle сохранил 2 notices.
- Server-rendered dashboard на `127.0.0.1:8010` вернул HTTP 200 (22 461 bytes), показывает два профиля,
  recommendations, freshness, buyer/outcome analytics, controls, AI evidence и in-app alerts.
- ЕИС manual fallback принимает XML/ZIP до 10 MiB, ограничивает members/uncompressed bytes/records,
  отклоняет DTD/ENTITY/path traversal и связывает records с hash всего загруженного package.
- Alembic migrations `0001..0005` создают lineage, AI attempts, organization identity, in-app outbox и
  webhook delivery attempts. Текущий Docker revision — `0005_webhook_alert_delivery`.
- Organization backfill на существующем PostgreSQL создал 10 source-scoped entities и 11 links по всем
  сохранённым версиям; повторный запуск идемпотентен.
- `GET /api/analytics/award-outcomes` вернул три реальных USAspending awards с buyer, winner,
  amount/currency, source URL и raw SHA; dashboard показывает тот же current projection.
- Webhook dispatcher проверен через HTTP mock: `2xx`, retryable `503`, replay и URL validation; реальная
  внешняя отправка не выполнялась, `ALERT_WEBHOOK_URL` по умолчанию не задан.
- Project-control data profile создан; локальный root commit `2e6f1df` создан на `main` после staged secret
  audit. Push в `origin/main` ожидает отдельного явного разрешения на внешний data egress.
- 08.08.2026 официальный TED v3 smoke вернул актуальные records с provenance links; endpoint
  anonymous и поддерживает bounded pagination/iteration.
- 08.08.2026 официальный USAspending smoke вернул contract awards; источник не содержит активные notices.
- HTTPS страницы ЕИС из текущего окружения не прошли TLS chain verification даже с одним
  предоставленным root CA; отключение verification запрещено, live connector пока не подтверждён.
- Предоставленная `.env` содержит имена GigaChat-переменных и исключена из Git; значения не читались.

## Changed areas

- Foundation projection целиком: domain/source adapters, persistence/migration, API, raw storage, dbt,
  Docker, fixtures, tests и документация.
- AI evidence projection: schema/evals, GigaChat OAuth/chat adapter, migration `0002`, cache/audit repository,
  service, API endpoints, settings и Docker live verification.
- Product projection: profile version API, responsive dashboard, analytics/freshness, live/manual loading,
  safe EIS upload, alert outbox/read state, migration `0003` и integration tests.
- Identity/outcome projection: единый Unicode normalizer, aliases/version links, historical backfill,
  award API/UI и dbt marts, миграция `0004` и ADR-002.
- Delivery projection: opt-in HTTPS webhook, stable idempotency key, bounded retry/audit, настройки,
  runbook/security projection и миграция `0005`.
- `certs/russian_trusted_root_ca_pem.crt`: проверенный локальный CA bundle для opt-in интеграций.

## Decisions made

- USAspending используется как outcome/history enrichment, не как источник активных notices.
- MVP использует hybrid lakehouse: immutable S3 raw + PostgreSQL/pgvector canonical/serving + dbt marts.
- Source-specific payloads не протекают в matching/API; downstream читает canonical model.
- Межисточниковая organization identity не выводится из совпадения имени; решение закреплено в ADR-002.

## Next exact step

Создать локальный Git checkpoint после staged secret audit. Push в `origin/main` остаётся отдельным
внешним действием и выполняется только после явного разрешения пользователя.

## Blockers

- Live-канал ЕИС требует проверенного TLS bundle и подтверждения актуального XML/ZIP layout; это не
  блокирует manual XML/ZIP fallback, но не позволяет заявлять регулярную live-загрузку ЕИС.
- GitHub push остановлен approval policy как внешний data egress; локальный commit готов, обход не допускается.

## Non-goals

- Полная историческая выгрузка или более 500 records за один запуск.
- Production auth/RBAC, автоматическая подача заявки и юридическая гарантия требований.
- SAM.gov, прогноз вероятности победы и обучение собственной модели.

## Verification

Свежий MVP checkpoint:

```bash
.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q
.venv/bin/ruff check src tests migrations
.venv/bin/ruff format --check src tests migrations
.venv/bin/mypy src/tenderpulse
DBT_HOST=127.0.0.1 DBT_PORT=5433 DBT_USER=tenderpulse \
  DBT_PASSWORD=tenderpulse-local-only DBT_DBNAME=tenderpulse \
  .venv/bin/dbt build --project-dir analytics --profiles-dir analytics
docker compose config --quiet
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py check .
```
