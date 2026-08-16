---
title: Текущее состояние
type: state
status: active
updated: 2026-08-16
---

# Текущее состояние

## Active objective

Провести воспроизводимую agent-assisted blind evaluation профиля «Чистая территория» на не менее чем
50 реальных извещениях ЕИС, измерить качество matching и превратить подтверждённые классы ошибок в
test-first изменения, не выдавая агентскую разметку за человеческую приёмку закрытого пилота.

## Acceptance criteria

- [x] Sample содержит ≥50 уникальных current ЕИС notice versions из документированного набора bounded
  captures (каждый request ≤50 records и ≤31 дня); для каждой
  записи сохранены source ID/URL, capture/run metadata, canonical version и raw SHA без source bytes.
- [x] Blind-label rubric зафиксирован до раскрытия matcher output и различает `relevant`, `not_relevant`
  и `insufficient_evidence`, а также отдельно отмечает geography/budget/qualification uncertainty.
- [x] Агентская разметка покрывает все sample records и сохраняет reason/confidence; отсутствие данных
  не превращается в отрицательный или положительный факт.
- [x] Matcher results вычислены только после фиксации labels и связаны с точными profile/record versions.
- [x] Reproducible evaluator валидирует artifact schemas, запрещает duplicate/leakage и считает confusion,
  actionable precision, bounded-sample recall, abstention/coverage и hard onsite geography admissions.
- [x] Любой исправляемый повторяемый класс FP/FN сначала получает failing regression eval, затем меняется
  его owner mechanism; спорные случаи остаются explicit review/unknown.
- [x] Agent-assisted результат явно не закрывает human-labeled gate: сформирован отдельный review packet
  и список минимум 10–15 приоритетных записей для проверки владельцем продукта.
- [ ] Full test/lint/dbt, Docker health, docs/IMMUNE audit, artifact integrity и secret scan проходят;
  verified checkpoint отправлен в подтверждённую Git-ветку.

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

## Changed areas

- Affected: pilot-eval contract/artifacts, bounded ЕИС capture projection, matcher phrase scoring,
  evaluation metrics, regression evals, documentation and Git.
- Not affected: auth/session schema, source/raw/SCD2 ownership, GigaChat extraction, office account,
  notification transports, public deployment and automatic application submission.

## Decisions made

- Agent labeler is blind to matcher decisions until labels are frozen; collection, labeling and scoring
  are separate responsibilities, while exact source/profile versions make the comparison reproducible.
- Agent labels are provisional expert evidence, not `human-labeled` acceptance. Human verification of
  10–15 prioritized disagreements/uncertain records remains mandatory before claiming pilot precision.
- `insufficient_evidence` is an abstention label. It is reported separately and never coerced into a
  convenient positive/negative denominator.
- Exact multi-word service phrase is stronger thematic evidence than one stem and contributes `0.30`,
  but never proves geography, deadline, budget or qualification; sparse matches stop at `review`.
- Zero positive denominator is reported as `null`. This capture cannot honestly prove or disprove the
  human pilot target of actionable precision ≥80%.
- Профиль считается pilot candidate, а не доказанной реальной юридической компанией.
- Подрядчики расширяют географию только до `review`; они не доказывают наличие исполнителя.
- Budget range — eligibility boundary для известных сумм, а не только scoring bonus.
- Unknown amount и unknown legal requirements остаются видимыми; система не угадывает допуск.
- `review_above_amount` — общий typed owner ручной квалификационной проверки, а не hardcoded проверка
  имени cleaning-profile или парсинг свободного текста. Для pilot candidate порог равен 1 млн рублей.
- Обычный клининг не получает выдуманную лицензию. Опасные отходы и специализированные pest-control
  работы исключаются до отдельного юридического/операционного подтверждения.
- Seed-файл владеет fresh-install default; работающая БД получает следующую version через штатный API,
  чтобы не перезаписывать историю или возможные пользовательские изменения bootstrap-ом.

## Next exact step

Завершить release coherence checks, опубликовать verified checkpoint в подтверждённую Git-ветку и
передать владельцу 15-record blind packet для следующего human-labeled шага.

## Blockers

- Нет блокера для agent-assisted evaluation. Human-labeled acceptance и юридическая проверка требований
  остаются blocked до проверки владельцем продукта и документов компании.

## Non-goals

- Объявление агентской разметки человеческой или юридически достаточной.
- Изменение matching только ради достижения целевой метрики без анализа класса ошибок.
- Сохранение полных live RSS/source documents в Git; tracked artifact содержит только bounded public facts
  и lineage identifiers, необходимые для воспроизведения вывода.
- Юридическое заключение о лицензиях, допусках или соответствии 44-ФЗ/223-ФЗ.
- Начало 14-дневного reliability run или production rollout.
- Изменение office profile, auth, alerts, attachment ingestion или production deployment.
- Автоматическое привлечение подрядчика или подача заявки.

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
`GET /api/health` returns `{"status":"ok"}`. Git delivery remains the final unchecked gate.
