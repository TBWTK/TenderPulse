---
title: Запуск и эксплуатация
type: runbook
status: active
updated: 2026-08-10
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
идемпотентно восстанавливает organization links для всех ранее сохранённых SCD2-версий. Seed создаёт
только отсутствующий профиль: сохранённая пользователем версия никогда не откатывается к demo v1.

## Управление данными

- Dashboard: `GET /`.
- Ограниченная live-загрузка: `POST /api/ingestion/run`; источники `ted`, `eis`, `usaspending`, общий
  limit `1..500`, URL нельзя передать снаружи. ЕИС независимо ограничивает ответ первыми 50 records.
- Manual ЕИС: `POST /api/ingestion/eis-upload`, `.xml`/`.zip`, максимум 10 MiB. ZIP ограничен 50
  members, 20 MiB uncompressed и 500 records; DTD/ENTITY и unsafe paths запрещены.
- Runs/freshness: `GET /api/ingestion/runs`, `GET /api/analytics/source-freshness`.
- Результаты контрактов: `GET /api/analytics/award-outcomes`; winner/amount имеют явный coverage status.
- Product analytics: `GET /api/analytics/product/{profile_slug}`. `decisions`, `coverage`, `sources`,
  `categories`, `geographies` и `buyers` относятся только к current active/planned notices; `history`
  читает все SCD2 versions, `outcomes` — current award lots.
- Lineage: `GET /api/records/{source}/{source_record_id}/lineage`.
- Профили: dashboard редактирует name, capabilities, keywords, CPV/OKPD2/PSC, countries и budget bounds;
  `PUT /api/profiles/{slug}` обязан передавать следующую version. В MVP остаётся ровно два slug-а.

Следующий manual или scheduled cycle перечитывает current versions без рестарта. Union CPV prefixes
обоих профилей ограничивает TED, union keywords — USAspending; ЕИС RSS использует свой фиксированный
bounded query. `GET /api/ingestion/runs` возвращает фактические filters и `profile_versions`. Если active
profiles не ровно два или slug-и дублируются, цикл завершается ошибкой до обращения к источнику.

Dashboard по умолчанию показывает только `recommended`/`review`. Отклонённые matcher-ом records
раскрываются отдельно под «Рассмотрено и отклонено» и не имеют кнопок AI extraction. Кнопка
«Проверить требования в доступных данных» проверяет только поля уже сохранённой current record version;
после validated attempt карточка показывает coverage/claims/gaps вместо повторного действия. Timeline
«История» содержит raw SHA, ingestion run и официальный source URL каждой версии.

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
После ответа и после reload карточка показывает последний attempt текущей record version, включая
coverage statuses, gaps и verbatim citations. `unknown` означает недостаток evidence, а не отсутствие
требования или срока.

## Проверка и остановка

```bash
make verify
make dbt-test
docker compose down
```

`make dbt-test` по умолчанию использует Compose-порт `127.0.0.1:5433`; переменные `DBT_*` нужны только
для явно переопределённого подключения.

`docker compose down` сохраняет named volumes. Удаление volumes не входит в обычную остановку и
является destructive operation. До public deployment обязательны auth/RBAC, CSRF, tenant isolation,
durable command queue и backup/restore test. Для публичного webhook дополнительно нужны egress allowlist,
destination rotation procedure и receiver authentication policy.
