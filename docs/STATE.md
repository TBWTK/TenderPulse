---
title: Текущее состояние
type: state
status: active
updated: 2026-08-16
---

# Текущее состояние

## Active objective

Реализовать закрытый пилотный контур: bounded профильный поиск по официальному ЕИС RSS и
версионированное ручное ревью точных procurement/profile versions. Подготовить систему к будущему
документу владельца продукта, не подменяя его оценки агентской разметкой и не объявляя метрики качества
до импорта реальных human labels.

## Acceptance criteria

- [x] `EisRssQuery` передаёт проверенную bounded `searchString` и `morphology=on` только на фиксированный
  официальный RSS URL; пустые/control/слишком длинные строки отклоняются до HTTP.
- [x] Один versioned discovery-owner детерминированно выбирает не более трёх service phrases на профиль,
  дедуплицирует их и fail-loud при нарушении глобального лимита.
- [x] Live ingestion создаёт отдельный auditable run для каждой profile/query pair и сохраняет exact
  profile slug/version, strategy version, date/limit/search parameters и raw SHA; ошибка одного запроса
  видима и не скрывает результаты независимых запросов.
- [x] Human review append-only хранит account, exact profile/record versions, raw SHA, label, reason,
  note, revision и timestamps; stale/cross-company mutations fail closed.
- [x] Отдельная company-страница `/reviews` показывает только исходные факты и official link, но не
  matcher decision/score/reasons до фиксации оценки; форма доступна и адаптивна.
- [x] Human labels и pilot precision не сгенерированы системой. Будущий документ импортируется только
  после получения и проверки его schema/universe; отсутствие документа остаётся явным gap.
- [x] Failing tests предшествуют production code; full pytest/coverage, lint/mypy, migrations, dbt,
  rebuilt Docker, responsive browser inspection, bounded live ЕИС smoke, audits и Git checkpoint проходят.

## Current verified state

- MVP 2.1 закрыт checkpoint `36a6eb6`: два local account, tenant isolation, спокойный responsive UI и
  automatic bounded ЕИС RSS прошли `172` tests, `86.07%` branch coverage и `54` dbt tests.
- Пользователь подтвердил название, город, услуги, service regions, contractor policy и budget range
  16.08.2026; keywords, exclusions и requirements поручено сформировать системе.
- Seed и current DB v2 теперь совпадают с подтверждёнными фактами; DB history сохраняет v1 и v2, а
  restart API/worker не откатывает active version bootstrap-ом.
- Fail-first suite подтверждает gap: `12 failed` по параметрам профиля, дворовой уборке, пяти exclusions,
  contractor geography, двум out-of-range суммам, unknown amount и отсутствующему UI label.
- Независимый domain audit выявил риск широкого `OKPD2 81.29`, одиночных stems и неизвестного опыта;
  второй fail-first gate дал `7 failed` до появления typed review threshold.
- Реализация использует узкие фразы/`81.29.12`, budget blocker и `review_above_amount=1 000 000`;
  focused suite проходит `45` tests, full suite — `191` tests с `86.14%` branch coverage.
- Ruff, форматирование и strict mypy проходят; dbt завершил `PASS=54 WARN=0 ERROR=0`. Rebuilt Compose
  показывает healthy API/worker/PostgreSQL/MinIO, immediate worker cycle получил 25 записей ЕИС.
- Browser inspection формы v2 на 1280/768/390 px подтвердил доступность всех трёх budget controls,
  сохранённые значения, отсутствие обрезания и доступную историю из двух версий.
- Текущая bounded live-очередь честно содержит `1 review` и `29 not_relevant`, без искусственно
  сгенерированных `recommended`; качество на реальном рынке ещё не измерено.
- Checkpoint `99c9a18` опубликован в `origin/codex/ui-redesign`; `git ls-remote` подтвердил тот же
  полный remote hash `99c9a1833b12f465ac67cd9f97571edc73379b73`.
- Реальные подходящие/неподходящие закупки и подтверждённые лицензии пользователем не предоставлены.
- Frozen sample содержит 50 unique current active ЕИС versions из двух неперекрывающихся однодневных
  captures (`40 + 10`); все record/run/raw identifiers сверены с PostgreSQL lineage. В RSS известны
  buyer/amount, но region/deadline/classification отсутствуют у всех 50 и сохранены как unknown.
- Blind agent labels: `44 not_relevant`, `6 insufficient_evidence`, `0 relevant`; labels frozen
  16.08.2026 до predictions и не содержат matcher decision/score/reasons.
- Baseline matcher отвергал все 50 records. Реальный кейс ЕИС `0373200104826000065` с точной фразой
  «санитарное содержание и уборка помещений» стал fail-first regression; общий phrase owner теперь
  переводит sparse record в `review`, не обходя budget/geography/deadline/qualification gates.
- Current matcher: `1 review`, `49 not_relevant`; confusion на 44 определённых negative labels —
  `TN=44`, `TP=FP=FN=0`, abstention `12%`, actionable coverage `2%`, hard geo false admissions `0`.
  Precision/recall равны `null`, потому что в bounded sample нет agent-positive denominator.
- Reproducible CLI и 15-record blind human packet находятся в
  `evals/cleaning_pilot_2026-08-16/`; agent labels не закрывают human pilot gate.
- Verified implementation checkpoint `79f22e2a0fce39ce90a427b27d333994145ff625` опубликован в
  `origin/codex/ui-redesign`; direct remote-ref check вернул тот же hash.
- Profile-aware worker выполнил 6 отдельных official ЕИС queries: `25/0/0` cleaning и `25/25/9`
  office records; каждый successful run содержит query/profile/version/strategy/raw evidence.
- Миграция `0009_human_reviews` применена к PostgreSQL. Review API сохраняет immutable revision и
  отклоняет stale/concurrent identity; два account не видят оценки друг друга.
- Browser baseline выявил перегрузку `179` cards и mobile overflow `396 > 390`. Fail-first shortlist
  policy ограничил экран 15 версиями (до 10 actionable + 5 blind controls); итоговые 1280/768/390
  inspections дают `scrollWidth == viewport`, 15 official links/forms и no matcher output/console errors.

## Changed areas

- Affected: ЕИС query/discovery plan, one-run-per-profile/query metadata, human-review domain/schema/API/UI,
  Alembic/dbt integrity, responsive navigation, documentation and tests.
- Not affected: canonical raw/SCD2 ownership, matcher weights/decisions, GigaChat extraction, account
  credentials, notification transports, public deployment and automatic application submission.

## Decisions made

- Source discovery отвечает только за recall: до трёх exact service phrases/profile, hard global cap 30;
  budget/geography/qualification остаются в matcher/reviewer и не становятся недоказанными ЕИС filters.
- Один profile/query владеет одним run. Одинаковый notice в разных responses сохраняет raw/run evidence,
  но canonical SCD2 не создаёт ложную новую версию.
- Human review — append-only revision stream с optimistic revision check. Исправление не переписывает
  историю, stale profile/record/raw state получает `409`.
- Blind UI не показывает matcher result, но shortlist строится из максимум 10 actionable кандидатов и
  5 near-ranked controls. Это процедурная слепота, не security boundary: detail page доступна отдельно.
- Agent labels не становятся human labels. Precision/recall не пересчитываются до получения и проверки
  будущего документа пользователя.

## Next exact step

После получения документа ревью проверить его schema/universe и точные source/profile versions, импортировать
только подтверждённые human labels и пересчитать scoped pilot metrics. До получения документа ничего не
догенерировать от имени reviewer.

## Blockers

- Нет блокера для discovery/review infrastructure.
- Импорт human labels и измерение human pilot quality заблокированы до получения документа пользователя.

## Non-goals

- Выдумывать, дополнять или исправлять human review за пользователя.
- Автоматически scraping-ить HTML карточки/вложения ЕИС без нового machine-readable source contract.
- Считать source search рекомендацией, менять matcher под желаемую метрику или скрывать unknown.
- Начинать 14-дневный reliability run, public deployment, production auth/RLS, alerts channels или
  автоматическую подачу заявки.

## Verification

```bash
.venv/bin/pytest tests/test_mvp21_profiles.py tests/test_matching.py -q
.venv/bin/pytest tests/test_pilot_eval.py -q
.venv/bin/python -m tenderpulse.pilot_eval evaluate \
  evals/cleaning_pilot_2026-08-16/sample.json \
  evals/cleaning_pilot_2026-08-16/labels.json \
  evals/cleaning_pilot_2026-08-16/predictions.json --output /tmp/tenderpulse-pilot-report.json
make test
make lint
make dbt-test
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
git diff --check
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py audit .
python3 /Users/tbwtk/.codex/skills/immune-project-engineering/scripts/immune_project.py audit . --phase implementation
```

Pilot eval evidence: fail-first evaluator import ended with `ModuleNotFoundError`; real sparse-cleaning
regression first returned `not_relevant`. Current tracked report reproduces byte-for-byte, focused
pilot/profile/matching suites pass, full suite passes at `85.85%` branch coverage, Ruff/format/strict
mypy pass, dbt reports `PASS=54 WARN=0 ERROR=0`, rebuilt API/worker/PostgreSQL/MinIO are healthy and
`GET /api/health` returns `{"status":"ok"}`. Artifact/secret scans pass; implementation checkpoint
`79f22e2a0fce39ce90a427b27d333994145ff625` is verified on the remote branch.

Discovery fail-first остановился на `ModuleNotFoundError: tenderpulse.discovery`. После реализации
`.venv/bin/pytest tests/test_discovery.py tests/test_source_http.py tests/test_live_ingestion.py -q`
проходит: `23 passed`.

Human-review fail-first остановился на `ModuleNotFoundError: tenderpulse.human_reviews`; browser baseline
показал 179 cards и mobile overflow. Current full suite проходит с `85.94%` branch coverage; migration
`0009`, dbt `PASS=71`, live six-query worker cycle и responsive 1280/768/390 browser inspection проходят.
Release audit: `238` tests, Ruff/format/strict mypy, Compose health, API health, `git diff --check`,
project-control и IMMUNE audits проходят. PostgreSQL подтверждает `0009_human_reviews`, `0` созданных
human labels и шесть последних discovery runs с raw SHA.
