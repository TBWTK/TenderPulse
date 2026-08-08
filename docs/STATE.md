---
title: Текущее состояние
type: state
status: active
updated: 2026-08-08
---

# Текущее состояние

## Active objective

Закрыть product-input/evidence slice: дать компании полноценно описывать оба MVP-профиля через UI,
сохранять каждое изменение новой версией и показывать извлечённые GigaChat requirements/deadlines с
coverage status, gaps и citations непосредственно в рекомендации.

## Acceptance criteria

- [x] Dashboard редактирует name, capabilities, keywords, CPV/OKPD2/PSC prefixes, countries и budget
  bounds для каждого из ровно двух профилей; PUT создаёт следующую immutable version.
- [x] Company-profile contract нормализует whitespace/case, удаляет дубликаты и явно отклоняет пустые
  capabilities/keywords, неизвестные classification systems, неверные country codes и budget range.
- [x] Изменённый профиль немедленно влияет на deterministic recommendations и создаёт отдельный alert
  snapshot только для новой profile version.
- [x] Последний AI extraction attempt для current record version отображается в dashboard: status,
  requirements/deadlines coverage, claims, gaps и verbatim citations; reload не теряет evidence.
- [x] UI обновляет evidence безопасными DOM text nodes; full regression/dbt/Compose и server-rendered/API
  QA проходят, документация согласована. In-app browser не открыл loopback из-за client policy, поэтому
  его визуальный smoke заменён проверяемыми HTML/API/asset-контрактами и не считается product evidence.

## Current verified state

- Foundation vertical slice реализован: immutable content-addressed raw, ingestion runs, canonical records,
  SCD2 versions, два профиля, matcher, lineage/recommendations API, Alembic, dbt и Docker Compose.
- `pytest`: 115 passed, branch coverage 86.49%; Ruff format/lint и strict mypy прошли 08.08.2026.
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
- Runtime profile smoke создал нормализованный `it-data-integrator` v2, получил 10/10 `not_relevant`
  после изменения matching input, пережил повторный `init`, затем восстановил demo content как auditable
  v3; второй `init` также сохранил v3 вместо реактивации seed v1.
- Dashboard runtime smoke после schema upgrade показал TED `497954-2026` с сохранёнными coverage
  `requirements: unknown` и `deadlines: found`, без server error и потери citations при reload.
- ЕИС live connector читает официальный RSS одной страницы (44-ФЗ, ≤50 records, ≤31 days) через
  проверенную root + issuing CA цепочку. Manual fallback принимает XML/ZIP до 10 MiB, ограничивает
  members/uncompressed bytes/records и связывает records с hash всего package.
- Alembic migrations `0001..0006` создают lineage, AI attempts, organization identity, in-app outbox,
  webhook delivery attempts и explicit legacy AI coverage. Текущий Docker revision —
  `0006_ai_evidence_coverage`; 2/2 исторических payloads имеют явные coverage statuses.
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
- Проверенный live ЕИС slice сохранён локальным commit `04509ec`; staged secret scan не нашёл
  credentials/private keys, публичный issuing CA не содержит private key.
- Проверенный product-input/evidence slice сохранён локальным commit `e6934e0`: полный versioned profile
  editor, seed preservation, current-record AI evidence, migration `0006` и dbt port contract. Staged
  secret scan прошёл, `.env` остался ignored.
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
- Product-input/evidence projection: полный versioned profile editor, нормализация/валидация matching
  input, seed-preservation invariant, current-record evidence cards, safe DOM rendering и миграция `0006`.
- Analytics config projection: dbt default port contract-tested against Docker Compose (`5433`).
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

После явного разрешения пользователя отправить накопленные commits в `origin/main`, проверить remote
SHA и закрыть Quality & handoff stage.

## Blockers

- GitHub push остановлен approval policy как внешний data egress; локальный commit готов, обход не допускается.

## Non-goals

- Полная историческая выгрузка или более 500 records за один запуск.
- Production auth/RBAC, автоматическая подача заявки и юридическая гарантия требований.
- SAM.gov, прогноз вероятности победы и обучение собственной модели.
- Создание третьего MVP-профиля и ingest произвольных офисных документов компании.

## Verification

Свежий MVP checkpoint:

```bash
.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q
.venv/bin/ruff check src tests migrations
.venv/bin/ruff format --check src tests migrations
.venv/bin/mypy src/tenderpulse
make dbt-test
docker compose config --quiet
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py check .
```
