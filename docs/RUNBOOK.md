---
title: Запуск и эксплуатация
type: runbook
status: active
updated: 2026-08-15
---

# Запуск и эксплуатация

## Быстрый старт

Требования: Docker Compose и локальный `.env`. Реальные секреты не переносятся в `.env.example` и
не коммитятся.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps -a
```

Web/API: `http://127.0.0.1:8010`; PostgreSQL: `127.0.0.1:5433`; MinIO console:
`127.0.0.1:9001`. Порты задаются `TENDERPULSE_*_PORT`.

Init применяет Alembic, идемпотентно загружает один российский ЕИС demo-export из 6 notices и 1
award, создаёт четыре отсутствующих demo-профиля и alerts. Повторный init сохраняет новый ingestion
run, но не создаёт canonical version без изменения. Пользовательская active version и созданные
пользователем slug-и не сбрасываются.

## Пользовательский workflow

- `/` — русская очередь, filters/sort, аналитика, компании и bounded ingestion.
- `/tenders/{source}/{source_record_id}?profile={slug}` — внутренняя карточка с requirements,
  geography, lineage, результатами и отдельным официальным переходом.
- `GET/POST /api/profiles`, `PUT /api/profiles/{slug}`, `GET /api/profiles/{slug}/history` — создание,
  следующая immutable version и история. Любое число distinct active slug допустимо.
- `GET /api/recommendations/{slug}` — current ЕИС/RU active/planned notices.
- `GET /api/analytics/product/{slug}` — полный current scope, даже если UI-очередь отфильтрована.
- `GET /api/analytics/award-outcomes` — только текущие российские award facts.
- `GET /api/records/{source}/{id}/lineage` — все сохранённые версии, включая legacy history.

Основная очередь содержит `recommended` и `review`; `not_relevant`/`expired` находятся в audit и не
получают AI/alert actions. Alert создаётся только для `recommended` и сохраняет profile/record version,
score/reasons, region, deadline, official URL и raw SHA.

## Bounded ЕИС ingestion

```dotenv
LIVE_INGESTION_ENABLED=true
INGESTION_INTERVAL_SECONDS=3600
SOURCE_RECORD_LIMIT=25
EIS_LOOKBACK_DAYS=7
EIS_ROOT_CA_FILE=/app/certs/russian_trusted_root_ca_pem.crt
EIS_SUB_CA_FILE=/app/certs/russian_trusted_sub_ca_pem.crt
```

`POST /api/ingestion/run` принимает только `sources=["eis"]`, limit `1..50` и окно `1..31` день.
URL фиксирован: `https://zakupki.gov.ru/epz/order/extendedsearch/rss.html`; response ≤2 MiB. Параметры
и версии всех профилей сохраняются в run. Пустой валидный RSS — `0 records`; foreign source, limit 51,
битая schema или transport error видны как отказ, а не как правдоподобный пустой результат.

`POST /api/ingestion/eis-upload` принимает `.xml`/`.zip` ≤10 MiB; ZIP ≤50 members и ≤20 MiB
uncompressed. DTD/ENTITY, unsafe path и unsupported schema отклоняются. Parser сохраняет official
zakupki.gov.ru URL, region/delivery mode, deadline, CPV/ОКПД2 и award winner/amount, когда они есть.

## GigaChat

Задайте `GIGACHAT_API_KEY`, `GIGACHAT_SCOPE` и CA bundle. Токены живут только в HTTP-клиенте и не
попадают в raw/log. Кнопка requirements вызывает `POST /api/records/{source}/{id}/evidence/extract`.
Attempt привязан к current record version и содержит prompt/model/input/output hashes, validation
status и verbatim citations. `unknown` означает недостаток evidence, не отсутствие требования.

## Alerts и webhook

In-app outbox работает локально. Для opt-in HTTPS webhook задайте `ALERT_WEBHOOK_URL`, timeout и
bounded max attempts. Receiver обязан уважать `Idempotency-Key`; БД хранит destination hash/status/error,
но не URL и response body. Retry разрешён только для transport/429/5xx.

## Проверка, перезапуск и остановка

```bash
make verify
make dbt-test
docker compose restart api worker
docker compose ps -a
docker compose down
```

После restart проверьте созданный slug через `/api/profiles` и его history. `docker compose down`
сохраняет named volumes. Удаление volumes — отдельная destructive operation и не входит в штатную
остановку. До public deployment нужны auth/RBAC, CSRF, tenant isolation, backup/restore и durable queue.
