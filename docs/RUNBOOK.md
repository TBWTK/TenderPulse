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
- `/reviews` — отдельная blind-очередь ручной оценки current notice versions без matcher score/decision;
  каждая правка создаёт новую immutable revision с exact profile/record/raw identity.
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
`searchString` + `morphology=on` строятся из первых трёх уникальных service phrases каждого current
профиля; keywords используются только при пустом services. Каждый profile/query создаёт отдельный run
с profile slug/version, strategy version и raw SHA. Общий hard cap — 30 queries/cycle. Полный профиль,
budget/geography/constraints во внешний источник не отправляются. Пустой валидный RSS — `0 records`; foreign source, limit 51,
битая schema или transport error видны как отказ, а не как правдоподобный пустой результат.

`GET /api/reviews` возвращает только revisions текущего account. `POST /api/reviews/{source}/{id}` требует
CSRF и exact `profile_version`, `record_version`, `raw_sha256`, `expected_latest_revision`, label/reason/note.
Изменившаяся версия или параллельная оценка получает `409`; чужие оценки не выдаются. Экран является
процедурно blind: обычная tender detail page доступна отдельно, поэтому reviewer не должен открывать её
до фиксации оценки. Будущий документ ревью нельзя считать импортированным до проверки его universe/schema.

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
.venv/bin/python -m tenderpulse.pilot_eval review-remainder \
  evals/cleaning_pilot_2026-08-16/sample.json \
  evals/cleaning_pilot_2026-08-16/human-reviews.json \
  evals/cleaning_pilot_2026-08-16/report.json \
  --output /tmp/HUMAN_REVIEW_REMAINING_35.md
.venv/bin/python -m tenderpulse.pilot_eval import-human \
  evals/cleaning_pilot_2026-08-16/sample.json \
  evals/cleaning_pilot_2026-08-16/report.json \
  evals/cleaning_pilot_2026-08-16/HUMAN_REVIEW.md \
  /path/to/HUMAN_REVIEW_filled.md --output /tmp/human-reviews.json
.venv/bin/python -m tenderpulse.pilot_eval evaluate-human \
  evals/cleaning_pilot_2026-08-16/sample.json \
  /tmp/human-reviews.json \
  evals/cleaning_pilot_2026-08-16/predictions.json \
  evals/cleaning_pilot_2026-08-16/report.json --output /tmp/human-report.json
```

Сравнивайте `/tmp` с tracked current artifacts. `null` precision/recall означает отсутствие
положительных labels/denominator в этой bounded выборке, а не нулевое качество. Human gate
требует независимой выборки минимум 50 notices; заполненный 15-row `HUMAN_REVIEW.md`
закрывает shortlist handoff, но не заменяет full-pilot evidence.
Файл `HUMAN_REVIEW_REMAINING_35.md` нужно заполнять без просмотра `labels.json`,
`predictions*.json` и `report*.json`. Он даёт полную 50-record coverage вместе с первыми 15,
но не гарантирует достаточный positive denominator.
Импорт fail-loud при лишней/пустой строке, дубле, неизвестном label, amount/URL/universe
расхождении или prediction snapshot, созданном после review. `shortlist_*` метрики нельзя
использовать как full-pilot или market-quality claim. CLI создаёт file evidence; он не пишет
reviewer enrichment в canonical records и не создаёт account DB revisions.

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
