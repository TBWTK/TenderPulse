---
title: Текущее состояние
type: state
status: active
updated: 2026-08-08
---

# Текущее состояние

## Active objective

Завершить и зафиксировать live ЕИС slice: официальный bounded RSS 44-ФЗ с проверенной TLS-цепочкой,
raw/SCD2 lineage, scheduler/API/UI и сохранённым manual XML/ZIP fallback; затем передать готовый Git
checkpoint без несанкционированной внешней отправки.

## Acceptance criteria

- [x] ЕИС RSS использует только фиксированный официальный HTTPS endpoint, 44-ФЗ, одну страницу,
  интервал не более 31 дня и не более 50 records; пустой валидный канал даёт явные 0 records.
- [x] Серверный TLS проверяется pinned root + issuing CA Минцифры; DTD/ENTITY, чужие item links,
  неожиданный media type/schema и ответы более 2 MiB отклоняются явно.
- [x] Live ЕИС проходит через общий raw/run/canonical/SCD2/organization pipeline, доступен scheduler,
  ручному API и dashboard; bounded XML/ZIP upload остаётся независимым fallback для истории.
- [x] Два последовательных live-запуска доказали одинаковый raw SHA и отсутствие лишней SCD2-версии;
  pytest/coverage, Ruff, mypy, dbt, Compose health и project-control gates проходят.
- [x] Локальный Git checkpoint готовится с secret scan; push в `origin/main` остаётся только после
  отдельного явного разрешения пользователя.

## Current verified state

- Foundation vertical slice реализован: immutable content-addressed raw, ingestion runs, canonical records,
  SCD2 versions, два профиля, matcher, lineage/recommendations API, Alembic, dbt и Docker Compose.
- `pytest`: 100 passed, branch coverage 86.23%; Ruff format/lint и strict mypy прошли 08.08.2026.
- Docker health подтверждён для API, worker, PostgreSQL/pgvector и MinIO; init migration/seed завершился с 0.
- dbt 1.12: 5 models + 48 data tests, `PASS=53 WARN=0 ERROR=0` на PostgreSQL Docker.
- GigaChat evidence v2 реализован через forced function call и явные coverage statuses; все claims требуют
  verbatim citation из canonical evidence fields. Validated/rejected/failed attempts сохраняются отдельно.
- 08.08.2026 live GigaChat smoke на TED `497954-2026` прошёл с TLS verification: модель
  `GigaChat-2:2.0.30.01` подтвердила deadline; requirements остались явно `unknown`.
- TED/ЕИС/USAspending live transport связан с scheduler и ручным allowlisted API. Два одинаковых TED
  запуска дали один raw hash и оставили `records=6/current_versions=6/total_versions=6`.
- USAspending bounded live cycle сохранил 2 awards; TED bounded cycle сохранил 2 notices.
- Официальный ЕИС RSS 44-ФЗ в Docker вернул 10 извещений за `01.08.2026..08.08.2026`; run
  `2886986a-fb71-4f4c-8110-3bf6b02c057e` сохранил raw SHA
  `ee3681351f9bbd81d67c0150ae35b1bf167faea0b1d066b2564049c708cce290` в MinIO.
- Немедленный replay ЕИС создал новый auditable run с тем же raw SHA, но оставил `11 current / 11 total`
  ЕИС-версий и `max_version=1`; organization projection содержит 8 ЕИС-покупателей и 11 role links.
- Server-rendered dashboard на `127.0.0.1:8010` вернул HTTP 200 (22 461 bytes), показывает два профиля,
  recommendations, freshness, buyer/outcome analytics, controls, AI evidence и in-app alerts.
- ЕИС live connector читает официальный RSS одной страницы (44-ФЗ, ≤50 records, ≤31 days) через
  проверенную root + issuing CA цепочку. Manual fallback принимает XML/ZIP до 10 MiB, ограничивает
  members/uncompressed bytes/records и связывает records с hash всего package.
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
- Проверенный normalization/outcomes/alerts slice сохранён локальным commit `74b36e8`; staged secret scan
  не нашёл credentials/private keys, `.env` остаётся ignored.
- 08.08.2026 официальный TED v3 smoke вернул актуальные records с provenance links; endpoint
  anonymous и поддерживает bounded pagination/iteration.
- 08.08.2026 официальный USAspending smoke вернул contract awards; источник не содержит активные notices.
- 08.08.2026 issuing CA из AIA цепочки `*.zakupki.gov.ru` проверен root CA; официальный RSS smoke прошёл
  без отключения verification. Решение и границы зафиксированы в ADR-003.
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
- ЕИС projection: официальный RSS query/parser/client, bounded filters, API/UI/scheduler config,
  live replay evidence, certificate tests и ADR-003; manual package path сохранён.
- `certs/russian_trusted_root_ca_pem.crt` и `certs/russian_trusted_sub_ca_pem.crt`: проверенная локальная
  TLS chain для GigaChat/ЕИС без `verify=false`.

## Decisions made

- USAspending используется как outcome/history enrichment, не как источник активных notices.
- MVP использует hybrid lakehouse: immutable S3 raw + PostgreSQL/pgvector canonical/serving + dbt marts.
- Source-specific payloads не протекают в matching/API; downstream читает canonical model.
- Межисточниковая organization identity не выводится из совпадения имени; решение закреплено в ADR-002.
- Live ЕИС MVP читает официальный RSS подписки 44-ФЗ; full export/HTML scraping запрещены, XML/ZIP upload
  служит контролируемым historical fallback. Решение закреплено в ADR-003.

## Next exact step

Создать локальный EIS checkpoint после финального secret scan. После отдельного явного разрешения
пользователя выполнить `git push -u origin main`, проверить remote ref и зафиксировать опубликованный
checkpoint. До такого разрешения никаких внешних Git writes не выполнять.

## Blockers

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
