---
title: Запуск и эксплуатация
type: runbook
status: active
updated: 2026-08-08
---

# Запуск и эксплуатация

## Быстрый старт

Требования: Docker Compose и заполненный локальный `.env`. Реальные секреты не копируются в
`.env.example` и не коммитятся.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps -a
```

Web/API доступен только на `http://127.0.0.1:8010`; PostgreSQL — `127.0.0.1:5433`, MinIO console —
`127.0.0.1:9001`. Порты переопределяются переменными `TENDERPULSE_*_PORT`.

Init container применяет все Alembic migrations, загружает три небольших demo fixtures, два
синтетических профиля и создаёт in-app alerts. Повторный init идемпотентен для canonical versions и
alerts, но сохраняет новый ingestion run как свидетельство повтора. После migrations он также
идемпотентно восстанавливает organization links для всех ранее сохранённых SCD2-версий.

## Управление данными

- Dashboard: `GET /`.
- Ограниченная live-загрузка: `POST /api/ingestion/run`; источники `ted`, `eis`, `usaspending`, общий
  limit `1..500`, URL нельзя передать снаружи. ЕИС независимо ограничивает ответ первыми 50 records.
- Manual ЕИС: `POST /api/ingestion/eis-upload`, `.xml`/`.zip`, максимум 10 MiB. ZIP ограничен 50
  members, 20 MiB uncompressed и 500 records; DTD/ENTITY и unsafe paths запрещены.
- Runs/freshness: `GET /api/ingestion/runs`, `GET /api/analytics/source-freshness`.
- Результаты контрактов: `GET /api/analytics/award-outcomes`; winner/amount имеют явный coverage status.
- Lineage: `GET /api/records/{source}/{source_record_id}/lineage`.

Для регулярного TED/ЕИС/USA цикла:

```dotenv
LIVE_INGESTION_ENABLED=true
INGESTION_INTERVAL_SECONDS=3600
SOURCE_RECORD_LIMIT=100
TED_LOOKBACK_DAYS=14
EIS_LOOKBACK_DAYS=7
USA_LOOKBACK_DAYS=365
GIGACHAT_CA_BUNDLE_FILE=/app/certs/russian_trusted_root_ca_pem.crt
EIS_ROOT_CA_FILE=/app/certs/russian_trusted_root_ca_pem.crt
EIS_SUB_CA_FILE=/app/certs/russian_trusted_sub_ca_pem.crt
```

Worker выполняет первый цикл сразу после старта, затем ждёт interval. При `false` внешних source
вызовов нет. Live ЕИС использует только `https://zakupki.gov.ru/epz/order/extendedsearch/rss.html`,
44-ФЗ, первую страницу, интервал `1..31` день и максимум 50 records; `Referer`/URL извне не принимаются.
RSS не содержит полного набора CPV/deadline/result details, поэтому эти поля остаются `unknown`, пока
они не подтверждены отдельным evidence. При ротации upstream certificate обновите issuing CA только
после проверки issuer/expiry/fingerprint и повторите certificate tests; `verify=false` запрещён.

## Alerts

In-app outbox работает всегда и не вызывает внешние системы. Для opt-in доставки задайте:

```dotenv
ALERT_WEBHOOK_URL=https://internal.example/tenderpulse
ALERT_WEBHOOK_TIMEOUT_SECONDS=10
ALERT_WEBHOOK_MAX_ATTEMPTS=5
```

Разрешён только HTTPS URL без embedded credentials и fragment. При заданном URL worker запускается
даже если live ingestion выключен, отправляет pending alerts со стабильным `Idempotency-Key` и повторяет
только transport/429/5xx failures. БД хранит destination SHA-256, HTTP status и error class; URL,
response body и возможный token из query string в audit/log не записываются. Получатель обязан уважать
`Idempotency-Key`, потому что сбой между HTTP 2xx и DB commit может привести к повторной попытке.

## GigaChat

Нужны `GIGACHAT_API_KEY`, `GIGACHAT_SCOPE` и доступный внутри контейнера CA bundle. Authorization key
и access token существуют только в memory HTTP-клиента. `GIGACHAT_CLIENT_ID` допускается в `.env` для
операционного учёта, но REST OAuth использует готовый Authorization key.

AI extraction вызывается явно через dashboard или `POST
/api/records/{source}/{source_record_id}/evidence/extract`. Результат не меняет canonical facts:
validated/rejected/failed attempt хранится отдельно с model/prompt/input/output hashes и citations.

## Проверка и остановка

```bash
make verify
DBT_HOST=127.0.0.1 DBT_PORT=5433 DBT_USER=tenderpulse \
  DBT_PASSWORD=tenderpulse-local-only DBT_DBNAME=tenderpulse make dbt-test
docker compose down
```

`docker compose down` сохраняет named volumes. Удаление volumes не входит в обычную остановку и
является destructive operation. До public deployment обязательны auth/RBAC, CSRF, tenant isolation,
durable command queue и backup/restore test. Для публичного webhook дополнительно нужны egress allowlist,
destination rotation procedure и receiver authentication policy.
