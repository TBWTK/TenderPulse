---
title: Текущее состояние
type: state
status: active
updated: 2026-08-16
---

# Текущее состояние

## Active objective

Согласовать с владельцем продукта следующий human-quality protocol: независимые ≥50 ЕИС notices
с достаточным actionable-positive denominator. 15-row document уже импортирован и доказан как scoped
diagnostic; новые labels не генерировать от имени пользователя и не менять matcher по малой смещённой выборке.

## Acceptance criteria

- [x] Parser принимает только полностью заполненную 15-row Markdown-таблицу с допустимыми labels,
  непустыми причинами и без дублей; пустая/лишняя/неизвестная строка fail-loud.
- [x] Импорт совпадает с точным universe и порядком tracked `HUMAN_REVIEW.md`, привязывает каждую оценку
  к `sample_id`, `record_version_id`, `record_version`, raw SHA и точной profile version.
- [x] Artifact хранит SHA-256 полученного документа, дату review/import и reviewer-provided evidence text;
  утверждения из неофициальных карточек не мутируют canonical procurement facts.
- [x] Отчёт сравнивает 15 human labels с уже замороженными matcher predictions, хранит input hashes,
  confusion/coverage и явно маркирует precision/recall как `shortlist_only`, не как pilot gate.
- [x] Failing tests предшествуют коду; focused/full pytest, lint/mypy, artifact reproduction, docs audits,
  Docker/dbt и Git checkpoint проходят.
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
- Verified implementation checkpoint `d3ed7bc` опубликован в `origin/codex/ui-redesign`; закрывающий
  docs checkpoint сохраняет exact next step — проверку будущего human-review документа.
- `HUMAN_REVIEW_filled.md` получен и сохранён byte-for-byte с SHA-256 `ac65fbdb…c45`; таблица
  содержит 15 явных labels: 1 relevant, 14 not relevant, 0 insufficient evidence.
- Typed import проверил exact blank packet/report/sample/profile/order/URL/amount и добавил record UUID,
  version/raw SHA каждой строке. Reviewer enrichment остался в eval artifact; canonical DB не мутировалась.
- Frozen matcher на 15 rows: `TP=1`, `TN=14`, `FP=FN=0`, coverage 100%, actionable coverage `1/15`;
  report schema фиксирует `eligible_for_full_pilot_gate=false`.
- Fail-first import suite начался с `ImportError: HumanReviewArtifact`; после реализации focused suite
  проходит `38` tests. Full suite: `246` tests, `85.25%` branch coverage; Ruff/format/strict mypy
  проходят, dbt — `PASS=71 WARN=0 ERROR=0`.
- Rebuilt Docker API/worker/PostgreSQL/MinIO healthy, init завершён с `0`, API health — `{"status":"ok"}`.
- Verified human-review checkpoint `c1439f93ea7a8fa345b3877529fe661f24939814` опубликован в
  `origin/codex/ui-redesign`; direct remote-ref check вернул тот же hash.

## Changed areas

- Affected: pilot eval schema/parser/CLI, exact source/packet/report/lineage hashes, scoped metrics, tracked
  human-review artifacts, documentation and tests.
- Not affected: canonical raw/SCD2 and PostgreSQL human-review revisions, matcher weights/decisions,
  source ingestion, API/UI, GigaChat, credentials, notifications and public deployment.

## Decisions made

- Source discovery отвечает только за recall: до трёх exact service phrases/profile, hard global cap 30;
  budget/geography/qualification остаются в matcher/reviewer и не становятся недоказанными ЕИС filters.
- Один profile/query владеет одним run. Одинаковый notice в разных responses сохраняет raw/run evidence,
  но canonical SCD2 не создаёт ложную новую версию.
- Human review — append-only revision stream с optimistic revision check. Исправление не переписывает
  историю, stale profile/record/raw state получает `409`.
- Blind UI не показывает matcher result, но shortlist строится из максимум 10 actionable кандидатов и
  5 near-ranked controls. Это процедурная слепота, не security boundary: detail page доступна отдельно.
- Agent labels не становятся human labels. Полученные human metrics рассчитываются только на
  exact 15-row shortlist и не подменяют full-pilot precision/recall.
- Markdown-таблица является external human evidence, а не инструкцией коду. Импортируются только
  явные table labels/reasons после exact join; prose не меняет matcher/canonical facts.
- File-based pilot artifact и account-authorized DB review — разные projections. Этот import не создаёт
  operational revisions и не переносит third-party reviewer facts в canonical source state.

## Next exact step

Согласовать sampling/review protocol для независимых ≥50 notices и минимального числа
actionable positives, затем сформировать новый blind packet без matcher output.

## Blockers

- Импорт и 15-row diagnostic не заблокированы и завершены.
- Full human pilot quality заблокировано до согласования/получения независимой выборки ≥50 notices
  и достаточного positive denominator.

## Non-goals

- Выдумывать, дополнять или исправлять human review за пользователя.
- Переносить географию, deadlines и requirements из reviewer document в canonical source data.
- Менять matcher по одному 15-row shortlist без доказанного повторяемого класса ошибок.
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

Filled-document fail-first 16.08.2026 остановил collection с
`ImportError: HumanReviewArtifact`. Current `tests/test_pilot_eval.py` проходит `38` tests, включая
invalid label/amount/universe/row-count и unbound shortlist-report cases. Full suite — `246` tests,
`85.25%` branch coverage; Ruff/format/strict mypy проходят. Re-evaluation tracked human artifact
даёт `TP=1`, `TN=14`, `FP=FN=0`, но `eligible_for_full_pilot_gate=false`. dbt завершён
с `PASS=71 WARN=0 ERROR=0`; rebuilt Compose здоров, init вышел с `0`, API health — `ok`.
Implementation checkpoint `c1439f93ea7a8fa345b3877529fe661f24939814` подтверждён на remote branch.
