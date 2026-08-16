---
title: Текущее состояние
type: state
status: active
updated: 2026-08-16
---

# Текущее состояние

## Active objective

Импортировать полученный 5-page PDF с оценками оставшихся 35 закупок как неизменяемое внешнее
human evidence, точно связать его с ранее размеченными 15 и frozen sample/predictions, затем выпустить
полный 50-record human report. Полная разметка не должна автоматически означать прохождение pilot gate:
вывод обязан учитывать размер positive denominator и явно показывать статистическую неопределённость.

## Acceptance criteria

- [x] Exact PDF bytes сохранены с SHA-256 `3e27c7b2…bc0b`; adapter проверяет PDF magic/encryption,
  дату `16.08.2026`, 35 contiguous rows, declared counts `0/35/0` и 35 official ЕИС hyperlinks.
- [x] Каждая PDF-строка fail-loud связывается по source ID/order с exact remainder packet и проверяет
  amount/currency, допустимый label, непустые place/deadline, reason и requirements/licenses.
- [x] Typed remainder artifact хранит source/blank/completed/report hashes и exact record/raw lineage;
  PDF enrichment остаётся reviewer evidence и не мутирует canonical procurement facts или DB reviews.
- [x] Merge требует непересекающиеся 15 + 35 и ровно всю frozen 50; duplicate/missing/stale profile,
  sample, prediction или source-document state отклоняется.
- [x] Full report показывает `TP=1, TN=49, FP=FN=0`, point precision/recall отдельно от 95% Wilson lower
  bound; `eligible_for_full_pilot_gate=false`, пока lower bound не доказывает целевые 80%.
- [ ] Failing tests предшествуют implementation; tracked artifacts воспроизводятся byte-for-byte,
  focused/full tests, lint/mypy, docs/IMMUNE audits, secret scan и Git checkpoint проходят.

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
- Remainder generator проверяет sample/completed-review/shortlist hashes, exact profile и lineage,
  затем строит 35 unique IDs как непересекающееся дополнение к первым 15; union равен frozen 50.
- `HUMAN_REVIEW_REMAINING_35.md` содержит только official URL, title и amount из sample, а 35 наборов
  reviewer fields пусты. SHA-256 `6cde292f…05dff` воспроизводится byte-for-byte через CLI.
- Fail-first remainder suite остановился на `ImportError: HumanReviewRemainderPacket`; после реализации
  focused suite проходит `42` tests. Full suite — `250` tests, `84.99%` branch coverage;
  Ruff/format/strict mypy, project-control/IMMUNE audits, diff и secret scan проходят.
- Verified remainder checkpoint `b8b170c21c277e30381f6967d7b62d2058f750de` опубликован в
  `origin/codex/ui-redesign`; direct remote-ref check вернул тот же hash.
- Полученный PDF сохранён byte-for-byte с SHA-256 `3e27c7b2…bc0b`; `pdfinfo`, text extraction и render
  всех пяти страниц подтвердили readable table, 35 rows, 35 official links и labels `0/35/0`.
- Offline typed import проверил PDF bounds/encryption, date/counts, exact IDs/order/links/amounts,
  profile/record/raw lineage. Reviewer place/deadline/reason/requirements сохранены только в eval artifact.
- Full merge содержит exact 50 sample IDs в sample order: 1 `relevant`, 49 `not_relevant`, 0 abstention.
  Frozen matcher: `TP=1`, `TN=49`, `FP=FN=0`, actionable coverage 2%, disagreements 0.
- Point precision/recall равны 100%, но 95% Wilson lower bound precision — `0.206543`; report фиксирует
  `precision_confidence_below_target` и `eligible_for_full_pilot_gate=false` при target 80%.
- Fail-first PDF/full-50 suite остановился на `ImportError: FullHumanReviewArtifact`; после реализации
  focused suite проходит `46` tests. Full suite — `254` tests, `84.01%` branch coverage; lint/mypy проходят.
- Rebuilt Compose установил `pypdf 6.16.1`; API/worker/PostgreSQL/MinIO healthy, init завершён с `0`,
  `GET /api/health` вернул `{"status":"ok"}`. dbt skipped: schema/marts/data contract не менялись.

## Changed areas

- Affected: PDF review adapter/dependency, typed remainder/full artifacts, confidence-aware eval/CLI,
  immutable pilot evidence, security/runbook/data/quality/state docs and tests.
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
- Remainder определяется set difference frozen sample и exact imported reviews, а не новым поиском или
  ранжированием. Рендерер получает только sample и typed packet, поэтому не имеет доступа к labels и
  predictions; полная coverage сама по себе не доказывает качество без достаточных positive labels.
- PDF является внешним human evidence, не procurement attachment: parser работает offline, bounded
  `2 MiB/20 pages`, проверяет embedded official links/layout и не выполняет embedded content.
- Gate использует pre-existing matcher snapshot и 95% Wilson lower bound precision. При текущих данных
  point estimate описателен; даже 1/1 success не удовлетворяет target 80% с confidence 95%.

## Next exact step

Не меняя matcher policy, собирать следующие последовательные bounded ЕИС windows и независимо размечать
все matcher-actionable records до достаточного denominator. При отсутствии FP минимум 16/16 TP нужен,
чтобы 95% Wilson lower bound превысил 80%; любой FP увеличит требуемую выборку.

## Blockers

- Импорт и full-50 coverage закрыты; blocker качества — positive/actionable denominator `1`.
- Закрытый пилот также всё ещё требует 14-day reliability, extraction/alert/recovery evidence,
  company eligibility facts и реальные participate/reject/defer outcomes.

## Non-goals

- Выдумывать, дополнять или исправлять human review за пользователя.
- Переносить географию, deadlines и requirements из reviewer document в canonical source data.
- Менять matcher по одному 15-row shortlist без доказанного повторяемого класса ошибок.
- Предзаполнять новые human labels, reasons, geography, deadlines или requirements.
- Считать создание blank packet закрытием 50-record human pilot gate.
- Подтверждать юридическую корректность reviewer assertions или считать адрес заказчика canonical местом работ.
- Менять matcher под этот документ до доказательства повторяемого класса FP/FN.
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

Remaining-35 fail-first 16.08.2026 остановил collection с
`ImportError: HumanReviewRemainderPacket`. Current `tests/test_pilot_eval.py` проходит `42` tests;
tracked Markdown SHA-256 `6cde292f5cd43a6d26c6502681bb4ac48a2a2190c522431e4e3991a2f7e05dff`
воспроизводится byte-for-byte. Full suite — `250` tests, `84.99%` branch coverage;
Ruff/format/strict mypy, project-control/IMMUNE audits, `git diff --check` и secret scan проходят.
Implementation checkpoint `b8b170c21c277e30381f6967d7b62d2058f750de` подтверждён на remote branch.

Full-50 PDF fail-first 16.08.2026 остановил collection с
`ImportError: FullHumanReviewArtifact`. Current `tests/test_pilot_eval.py` проходит `46` tests; three
tracked JSON artifacts воспроизводятся byte-for-byte из exact PDF/sample/parents/predictions. Full suite —
`254` tests, `84.01%` branch coverage; Ruff/format/strict mypy проходят. Rebuilt Docker runtime содержит
`pypdf 6.16.1`, все long-running services healthy, init — `0`, API health — `ok`. dbt skipped because
DB schema/marts не затронуты; `uv lock --check` проходит.
