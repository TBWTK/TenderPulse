---
title: Аудит TenderPulse
type: audit
status: active
updated: 2026-08-16
---

# Аудит TenderPulse

## Вывод о достаточности контекста

`sufficient` для импорта и оценки full-50 human relevance diagnostic. Полученный PDF содержит
оставшиеся 35 заполненных строк; exact bytes, пять страниц и embedded official links доступны.
Профиль/source/matching contracts и frozen predictions версионированы. Контекста недостаточно только
для утверждения ≥80% precision: в полной human-разметке найден ровно один positive label.

## Источники и доступность контекста

| Область | Статус | Источник/evidence | Влияние неизвестного | Следующее действие |
| --- | --- | --- | --- | --- |
| Business outcome | confirmed | user audit response + `docs/STATE.md` | нет | closed-pilot validation |
| Auth model | confirmed | tests + ADR-005 + HTTP journeys | public identity не входит | pilot access review |
| Company catalog | confirmed | cleaning + office supply evals | real fit ещё не измерен | label real-company sample |
| Current data | confirmed | PostgreSQL inspection 16.08.2026 | legacy history сохранена | retain shared lineage |
| Scheduled ingestion | confirmed | Docker worker + live run log | 14-day reliability неизвестна | pilot run ledger |
| Procurement attachments | unknown | `docs/DATA.md`, no source adapter/code | unsafe scraping/format expansion | official contract review before adapter |
| UI defect | confirmed | browser 390/768/1024/1280 | subjective pilot feedback ещё нет | pilot observation |
| Cleaning profile facts | confirmed | user message + local DB v2 16.08.2026 | нет | collect missing operational evidence |
| Keywords/exclusions | inferred | synthetic eval + full-50 human diagnostic | positive coverage insufficient | collect relevant cases |
| Licences/experience | unknown | user explicitly supplied no facts | legal/eligibility error | keep unknown; verify per tender |
| Budget semantics | confirmed | typed matcher tests + v2 500k–25m profile | нет для deterministic contract | validate on labeled sample |
| Real relevance sample | confirmed | frozen 50-record ЕИС sample + full human labels | один positive denominator | расширить positive-case evidence |
| Profile discovery | confirmed | official form parameters + six-query live worker run | RSS detail fields sparse | retain bounded query/run lineage |
| Human review document | confirmed | 15-row Markdown + 35-row PDF typed imports 16.08.2026 | один positive label | collect additional relevant cases |

Допустимые статусы: `confirmed`, `inferred`, `unknown`, `not applicable`.

## Бизнес-анализ

### Проблема и желаемый исход

MVP 2.0 технически позволяет выбрать любой DB profile, но не знает пользователя или владельца компании.
Рабочая БД показывает семь test/legacy профилей. Analytics смешивает семь областей, а company user видит
operator controls. Желаемый исход: пользователь вводит local access code, сразу попадает в одну свою
компанию и видит короткий decision workflow; source data обновляется независимо от browser session.

### Acceptance и non-goals

Acceptance принадлежит `docs/STATE.md`, evidence map — `docs/QUALITY.md`. Не в scope: public sign-up,
password recovery, social OAuth, GigaChat BYOK, Telegram/email, public deployment, physical history deletion,
Airflow и attachment scraping без official contract.

## Аудит реализованного состояния

- Cleaning pilot candidate записан как immutable v2: Москва/МО, подрядчики допустимы, договоры
  500 тыс.–25 млн рублей. Seed и local DB согласованы, v1/history сохранены после restart.
- Matcher fail-closed блокирует полностью известные суммы вне диапазона, сохраняет неизвестную сумму
  как `review` и требует ручной проверки квалификации выше 1 млн рублей. Последнее — product trigger,
  а не юридическое заключение.
- Пять positive/actionable и пять explicit negative scenarios, contractor geography и mixed/unknown
  budgets закреплены deterministic tests. На текущих 30 live records нет выдуманной рекомендации:
  1 `review`, 29 `not_relevant`.
- Форма профиля проверена browser inspection на 1280/768/390 px; порог опыта, бюджет и история версий
  доступны без обрезания.
- Agent-assisted pre-evaluation сохранил 50 current ЕИС versions из двух bounded captures, blind rubric,
  50 separate labels, baseline/current predictions и воспроизводимый report. Agent labels содержат
  44 отрицательных и 6 abstention, поэтому precision/recall честно остаются `null`.
- Sparse RSS case `0373200104826000065` доказал ошибку тематического threshold: точная многословная
  клининговая фраза отвергалась. После fail-first regression общий matcher даёт ей `review`; неизвестные
  region/deadline/qualification не превращаются в рекомендацию.
- `discovery` детерминированно строит максимум три service queries на exact profile version и общий
  hard cap 30. Live Docker worker получил шесть successful responses (`25/0/0 + 25/25/9`), сохранив
  отдельные run parameters/raw SHA; source search не объявляется решением matcher.
- `0009_human_reviews` добавляет append-only revisions с account/profile/record/raw identity и
  optimistic concurrency. API требует CSRF, foreign history скрыта, stale identity получает `409`.
- Полученный `HUMAN_REVIEW_filled.md` совпал с exact 15-row packet/order/amount/URL и был
  обогащён frozen `sample_id`, record UUID/version/raw SHA. Исходный SHA — `ac65fbdb…c45`;
  таблица содержит 1 `relevant`, 14 `not_relevant`, 0 abstention.
- Полученный 5-page PDF SHA `3e27c7b2…bc0b` содержит exact complement 35/35, 35 official ЕИС links
  и labels `0 relevant / 35 not_relevant / 0 insufficient_evidence`. Merge даёт frozen 50 без дублей.
- Full comparison с pre-existing matcher snapshot: `TP=1`, `TN=49`, `FP=FN=0`; point precision/recall
  100%, но 95% Wilson lower bound precision `20,65%`, поэтому 80%-gate остаётся failed.
- Pre-existing matcher snapshot даёт на этих 15 строках `TP=1`, `TN=14`, `FP=FN=0`; код жёстко
  маркирует отчёт `eligible_for_full_pilot_gate=false`. Reviewer сверял часть facts по
  сторонним открытым карточкам из-за нестабильной ЕИС; это evidence не мутирует canonical data.
- Первый browser render честно выявил перегрузку 179 cards и overflow 396/390. Owner-policy shortlist
  теперь фиксирует 15 версий (до 10 actionable + 5 blind controls); 1280/768/390 проверки не показывают
  matcher output, horizontal overflow или console errors.

- Миграция `0008_local_accounts` вводит отдельные authority для account, access credential и server
  session. Company context выводится из session binding, а не из query selector.
- Два account видят только `cleaning-moscow` и `office-supply-moscow`; запрос чужого profile/API
  отклоняется. Legacy profiles/raw/history не удалены и не подменяют tenant visibility.
- Access code хранится только как keyed HMAC hash; browser получает revocable HttpOnly session и CSRF
  cookie. Реальные demo secrets остаются в ignored `.env`, не в tracked artifacts.
- Analytics использует progressive disclosure; ближайшие сроки фильтруются до actionable решений.
  Проверены 390/768/1024/1280 px без overflow и offscreen controls.
- Worker по умолчанию выполняет immediate и hourly bounded ЕИС RSS. Штатный Docker run получил 25
  записей по TLS; component test доказывает продолжение после failed cycle.
- Full release evidence: `172` tests, `86.07%` branch coverage, Ruff/format/strict mypy, dbt `54/54`,
  rebuilt Compose health/restart, authenticated HTTP journeys и browser inspection.
- Current profile-discovery/review release evidence: `238` tests, `85.94%` branch coverage,
  Ruff/format/strict mypy, Alembic `0009`, dbt `71/71`, healthy Compose/API, six successful bounded
  live queries and 1280/768/390 browser inspection. PostgreSQL содержит `0` human reviews: система
  не выдала свою оценку за будущий документ пользователя.

## Архитектурные варианты

| Решение | Сильные стороны | Риск/стоимость | Вывод |
| --- | --- | --- | --- |
| Оставить query selector | без migration | нет identity/isolation | отклонено |
| Raw token на каждом request | мало server state | утечка browser secret, слабый logout | отклонено |
| Access code → server session | revoke/expiry/audit, простой UX | schema + CSRF | выбрано |
| Удалить legacy profiles | визуально просто | потеря lineage/evidence | отклонено |
| Account binding | чистая visibility authority | authorization mutation | выбрано |
| Airflow | DAG/backfill UI | лишние services/metadata/ops | отложено |
| Existing worker + run evidence | минимальная topology, уже протестирован | нужен resilience gate | выбрано |
| CSS-only analytics fix | малый diff | не исправляет information hierarchy | недостаточно |
| Progressive disclosure + breakpoint repair | меньше cognitive load, facts сохранены | template/journey changes | выбрано |
| Один общий ЕИС RSS без профиля | один request | почти нет thematic recall | отклонено |
| До 3 service queries/profile | bounded, объяснимо, exact version lineage | больше requests/overlap | выбрано |
| Mutable review status | простая таблица | теряется причина изменения | отклонено |
| Append-only review revisions | полная прослеживаемость, stale check | migration/API complexity | выбрано |
| Показывать все current notices | полный охват UI | 179 cards, unusable | отклонено browser evidence |
| Bounded 10+5 blind shortlist | рабочая очередь + controls | procedural selection bias | выбрано |

## Риски и mitigation

| Риск | Влияние | Проверка/mitigation |
| --- | --- | --- |
| Cross-company API leakage | critical | adversarial every-route tests; server profile owner |
| Plaintext access code | high | keyed hashes, ignored env, secret/log scan |
| CSRF/session fixation | high | rotate session, POST logout, CSRF mismatch tests |
| Seed hides/deletes history | high | upgrade legacy fixture; row/history counts unchanged |
| Broad office profile false positives | high | furniture/stationery/MFP positive + software negative eval |
| Worker dies after parser/storage error | high | failed-cycle then successful-cycle component test + Docker restart |
| Responsive fix passes only endpoints | medium | 390/768/1024/1280 browser DOM metrics/screenshots |
| Attachment source is not machine-readable | high | fail-closed contract gate; no guessed scraper |
| Review label contaminated matcher output | high | separate `/reviews`; matcher fields absent; procedural instruction |
| Stale/concurrent review | high | exact version/raw + expected revision; immutable append or 409 |

## Ландшафт проверок

Auth unit/integration, cookie/CSRF security, tenant adversarial API/page journeys, Alembic upgrade from
current schema, legacy-data bootstrap, business matching evals, worker failure/recovery, static DOM safety,
browser intermediate breakpoints, full regression/coverage, dbt, Docker rebuild/health/restart, local
credential secret scan and opt-in bounded live ЕИС smoke.

## Открытые вопросы и блокеры

Full-50 human handoff закрыт, но quality заблокировано до выборки с достаточным positive denominator:
единственный positive не доказывает целевые 80% precision. Также нужны документы/факты опыта
компании для eligibility. Official attachment contract остаётся explicit unknown; adapter запрещён
без bounded machine-readable semantics.

## Решение о поставке

`accepted for local pre-pilot`: профиль, matching contract и full-50 human diagnostic имеют exact local
evidence. Это не `production-ready` и не подтверждение ≥80% precision: positive denominator равен одному,
а confidence lower bound явно ниже target.

## Решение о начале

Историческое решение — `allowed`: business intent, ADR-005, acceptance и fail-first evidence были
зафиксированы до production implementation. Итоговое решение о поставке приведено выше.
