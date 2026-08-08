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
alerts, но сохраняет новый ingestion run как свидетельство повтора.

## Управление данными

- Dashboard: `GET /`.
- Ограниченная live-загрузка: `POST /api/ingestion/run`; источники только `ted` и `usaspending`, limit
  `1..500`, URL нельзя передать снаружи.
- Manual ЕИС: `POST /api/ingestion/eis-upload`, `.xml`/`.zip`, максимум 10 MiB. ZIP ограничен 50
  members, 20 MiB uncompressed и 500 records; DTD/ENTITY и unsafe paths запрещены.
- Runs/freshness: `GET /api/ingestion/runs`, `GET /api/analytics/source-freshness`.
- Lineage: `GET /api/records/{source}/{source_record_id}/lineage`.

Для регулярного TED/USA цикла:

```dotenv
LIVE_INGESTION_ENABLED=true
INGESTION_INTERVAL_SECONDS=3600
SOURCE_RECORD_LIMIT=100
TED_LOOKBACK_DAYS=14
USA_LOOKBACK_DAYS=365
```

Worker выполняет первый цикл сразу после старта, затем ждёт interval. При `false` внешних source
вызовов нет. Live ЕИС scheduler отсутствует: официальный transport/layout не подтверждён.

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
durable command queue, backup/restore test и внешний alert channel.
