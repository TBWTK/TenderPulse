---
title: Текущее состояние
type: state
status: active
updated: 2026-08-16
---

# Текущее состояние

## Active objective

Онбордить предоставленный владельцем продукта pilot-candidate профиль «Чистая территория» и доказать
на deterministic scenarios, что бюджет, география, подрядчики, стоп-направления и unknown-требования
дают объяснимые решения до начала разметки реальных закупок ЕИС.

## Acceptance criteria

- [x] Профиль сохраняет подтверждённые пользователем факты: Москва, работа в Москве и Московской
  области, подрядчики допустимы, бюджет договора от 500 000 до 25 000 000 RUB.
- [x] Рабочие positive keywords/classifications покрывают уборку помещений, офисов, дворов и территорий,
  ежедневный/генеральный клининг, санитарное содержание, мойку окон и сезонную/снежную уборку.
- [x] Stop-направления блокируют отдельные поставки товаров, ремонт/строительство, озеленение, охрану,
  обращение с опасными/медицинскими/радиоактивными отходами и специализированный pest control.
- [x] Неизвестные лицензии не превращаются в правовой факт: профиль явно требует проверки документации,
  а специальные допуски/опыт/персонал считаются tender-specific до подтверждения.
- [x] Москва/МО в диапазоне до 1 млн рублей рекомендуются по предмету; свыше порога неизвестный опыт
  переводит решение в `review`. Иной регион получает `review` с contractor evidence.
- [x] Все известные суммы вне диапазона создают typed budget blocker и `not_relevant`; неизвестная сумма
  при заданном budget range остаётся explicit gap и `review`.
- [x] Минимум пять positive и пять negative/uncertain synthetic scenarios покрыты business evals;
  fixtures не объявляются доказательством реальной precision.
- [x] Текущая local DB получает новую immutable version cleaning-profile через authorized API, старая
  версия сохраняется, а restart не откатывает пользовательский профиль seed-ом.
- [x] Full test/lint/dbt, Docker health/restart, authenticated browser/HTTP smoke, docs audit и secret
  scan проходят; checkpoint отправлен в GitHub по подтверждённой пользователем Git-authority.

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

## Changed areas

- Affected: business profile authority, matching budget contract, blocker API/UI labels, synthetic
  capability evals, local versioned profile state, analytics diagnostics, docs, Docker smoke and Git.
- Not affected: auth/session schema, procurement/raw/SCD2 models, source adapters, GigaChat extraction,
  office account, notification transports and public deployment.

## Decisions made

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

Собрать и вслепую разметить не менее 50 реальных извещений ЕИС для «Чистой территории», затем измерить
actionable precision и разобрать false positive/false negative до решения о 14-дневном закрытом пилоте.

## Blockers

- Нет блокера для synthetic onboarding. Human-labeled 50-notice precision gate и юридическая проверка
  требований остаются blocked до реальной выборки и документов компании.

## Non-goals

- Юридическое заключение о лицензиях, допусках или соответствии 44-ФЗ/223-ФЗ.
- Заявление о precision/recall на реальных закупках или начало 14-дневного reliability run.
- Изменение office profile, auth, alerts, attachment ingestion или production deployment.
- Автоматическое привлечение подрядчика или подача заявки.

## Verification

```bash
.venv/bin/pytest tests/test_mvp21_profiles.py tests/test_matching.py -q
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
