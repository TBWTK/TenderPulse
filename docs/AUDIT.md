---
title: Аудит TenderPulse
type: audit
status: active
updated: 2026-08-16
---

# Аудит TenderPulse

## Вывод о достаточности контекста

`sufficient` для synthetic onboarding cleaning pilot candidate. Пользователь подтвердил название,
Москву, услуги, service regions Москва/МО, допустимость подрядчиков и бюджет 500 тыс.–25 млн рублей;
системе поручено сформировать рабочие keywords/exclusions и осторожные требования. Юридические лицензии
и реальные labeled notices неизвестны, поэтому legal claims и pilot precision остаются отдельными gates.

## Источники и доступность контекста

| Область | Статус | Источник/evidence | Влияние неизвестного | Следующее действие |
| --- | --- | --- | --- | --- |
| Business outcome | confirmed | user audit response + `docs/STATE.md` | нет | closed-pilot validation |
| Auth model | confirmed | tests + ADR-005 + HTTP journeys | public identity не входит | pilot access review |
| Company catalog | confirmed | cleaning + office supply evals | real fit ещё не измерен | label real-company sample |
| Current data | confirmed | PostgreSQL inspection 16.08.2026 | legacy history сохранена | retain shared lineage |
| Scheduled ingestion | confirmed | Docker worker + live run log | 14-day reliability неизвестна | pilot run ledger |
| Attachments | unknown | `docs/DATA.md`, no adapter/code | unsafe scraping/format expansion | official contract review before adapter |
| UI defect | confirmed | browser 390/768/1024/1280 | subjective pilot feedback ещё нет | pilot observation |
| Cleaning profile facts | confirmed | user message + local DB v2 16.08.2026 | нет | collect missing operational evidence |
| Keywords/exclusions | inferred | business eval + narrow classifier contract | real false positives неизвестны | human-label ≥50 notices |
| Licences/experience | unknown | user explicitly supplied no facts | legal/eligibility error | keep unknown; verify per tender |
| Budget semantics | confirmed | typed matcher tests + v2 500k–25m profile | нет для deterministic contract | validate on labeled sample |
| Real relevance sample | unknown | examples not supplied | precision unmeasured | collect/label ≥50 ЕИС notices |

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

## Ландшафт проверок

Auth unit/integration, cookie/CSRF security, tenant adversarial API/page journeys, Alembic upgrade from
current schema, legacy-data bootstrap, business matching evals, worker failure/recovery, static DOM safety,
browser intermediate breakpoints, full regression/coverage, dbt, Docker rebuild/health/restart, local
credential secret scan and opt-in bounded live ЕИС smoke.

## Открытые вопросы и блокеры

Synthetic onboarding не заблокирован. Для закрытого пилота нужны документы компании и human-labeled выборка. Official
attachment contract остаётся explicit unknown; adapter запрещён без bounded machine-readable semantics.

## Решение о поставке

`accepted for local pre-pilot`: профиль и matching contract имеют local evidence; Git push проверяется
отдельным release gate. Это не `production-ready` и не
подтверждение ≥80% precision на реальной компании; эти gates принадлежат следующему этапу.

## Решение о начале

Историческое решение — `allowed`: business intent, ADR-005, acceptance и fail-first evidence были
зафиксированы до production implementation. Итоговое решение о поставке приведено выше.
