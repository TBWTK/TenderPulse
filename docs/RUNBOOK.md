---
title: Запуск и эксплуатация
type: runbook
status: active
updated: 2026-08-16
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

До первого запуска заполните три независимых значения длиной не менее 32 символов:
`AUTH_TOKEN_PEPPER`, `CLEANING_ACCESS_CODE`, `OFFICE_ACCESS_CODE`. Pepper не передаётся пользователю;
коды выдаются соответствующим компаниям вне Git/log/URL. `AUTH_COOKIE_SECURE=false` допустим только
для `http://127.0.0.1`; любое TLS-развёртывание обязано включить secure cookie.

Web/API: `http://127.0.0.1:8010`; PostgreSQL: `127.0.0.1:5433`; MinIO console:
`127.0.0.1:9001`. Порты задаются `TENDERPULSE_*_PORT`.

Init применяет Alembic, идемпотентно загружает один российский ЕИС demo-export из 6 notices и 1
award, создаёт два рабочих профиля и два local account binding. Повторный init сохраняет новый
ingestion run, но не создаёт canonical version без изменения и не сбрасывает пользовательскую active
profile version. Legacy profile/history физически сохраняются, но не доступны company account.

## Пользовательский workflow

- `/login` принимает локальный код и создаёт revocable server-side session; `/logout` отзывает её.
- `/` — короткий рабочий обзор авторизованной компании без mutation-форм и длинных списков.
- `/tenders` — actionable-очередь, фильтры и отдельный свёрнутый rejected audit.
- `/analytics` — решения и actionable deadlines; data quality/history/outcomes раскрываются вторично.
- `/company` — подсказки, редактирование собственного профиля и immutable version history.
- `/tenders/{source}/{source_record_id}` — карточка с requirements, geography, lineage, результатами и
  отдельным официальным переходом.
- `GET /api/profiles` возвращает один разрешённый профиль; `PUT /api/profiles/{own_slug}` создаёт
  следующую immutable version. Чужой slug отвечает `404`, создание профиля company role запрещено.
- `GET /api/recommendations/{own_slug}` — current ЕИС/RU active/planned notices.
- `GET /api/analytics/product/{slug}` — полный current scope, даже если UI-очередь отфильтрована.
- `GET /api/analytics/award-outcomes` — только текущие российские award facts.
- `GET /api/records/{source}/{id}/lineage` — все сохранённые версии, включая legacy history.

Company navigation не содержит selector, `/companies/new` и `/data`; прямой запрос к operator surface
получает `403`. В MVP 2.1 operator UI не имеет отдельного выданного account и schedule принадлежит
worker. API кроме `/api/health` требует session; unsafe запросы дополнительно требуют CSRF header/cookie.

Budget bounds в профиле являются eligibility boundary. Полностью известная сумма вне диапазона получает
`not_relevant`; неизвестная сумма — `review`. Необязательный `review_above_amount` задаёт сумму, выше
которой неизвестный опыт/квалификация требуют ручной проверки. Он не подтверждает и не отменяет
юридические требования конкретной закупки.

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
и версии только account-visible профилей сохраняются в run. Пустой валидный RSS — `0 records`; foreign source, limit 51,
битая schema или transport error видны как отказ, а не как правдоподобный пустой результат.

`POST /api/ingestion/eis-upload` принимает `.xml`/`.zip` ≤10 MiB; ZIP ≤50 members и ≤20 MiB
uncompressed. DTD/ENTITY, unsafe path и unsupported schema отклоняются. Parser сохраняет official
zakupki.gov.ru URL, region/delivery mode, deadline, CPV/ОКПД2 и award winner/amount, когда они есть.

## GigaChat

Задайте `GIGACHAT_API_KEY`, `GIGACHAT_SCOPE` и CA bundle. Токены живут только в HTTP-клиенте и не
попадают в raw/log. Кнопка «Извлечь требования и сроки» вызывает
`POST /api/records/{source}/{id}/evidence/extract` и анализирует только доступные поля сохранённой
версии; это не замена проверки полной документации.
Attempt привязан к current record version и содержит prompt/model/input/output hashes, validation
status и verbatim citations. `unknown` означает недостаток evidence, не отсутствие требования.

## Воспроизведение agent-assisted pilot eval

Frozen artifacts лежат в `evals/cleaning_pilot_2026-08-16/`. Predictions разрешено строить только после
фиксации labels; CLI проверяет hashes, timestamps, profile/version и полное равенство sample universe.

```bash
.venv/bin/python -m tenderpulse.pilot_eval predict \
  evals/cleaning_pilot_2026-08-16/sample.json \
  evals/cleaning_pilot_2026-08-16/labels.json \
  --policy-version tender-matcher/exact-phrase-review-v1 \
  --output /tmp/predictions.json
.venv/bin/python -m tenderpulse.pilot_eval evaluate \
  evals/cleaning_pilot_2026-08-16/sample.json \
  evals/cleaning_pilot_2026-08-16/labels.json \
  /tmp/predictions.json --output /tmp/report.json
.venv/bin/python -m tenderpulse.pilot_eval review \
  evals/cleaning_pilot_2026-08-16/sample.json \
  /tmp/report.json --output /tmp/HUMAN_REVIEW.md
```

Сравнивайте `/tmp` с tracked current artifacts. `null` precision/recall означает отсутствие
положительных labels/denominator в этой bounded выборке, а не нулевое качество. Human gate закрывается
только после заполнения `HUMAN_REVIEW.md` без предварительного просмотра agent/matcher outcomes.

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

После restart войдите обоими кодами, проверьте один разрешённый slug через `/api/profiles`, `/company`
и последний `ingestion_run`. `docker compose down`
сохраняет named volumes. Удаление volumes — отдельная destructive operation и не входит в штатную
остановку. До public deployment нужны production identity/RBAC, rate limiting, RLS/изоляция,
backup/restore и durable queue; local access-code boundary не является public-ready authentication.
