---
title: Текущее состояние
type: state
status: complete
updated: 2026-08-15
---

# Текущее состояние

## Active objective

Реализовать TenderPulse MVP 2.0 как русскоязычный продукт для российских закупок: четыре
редактируемых demo-компании и любая созданная пользователем компания получают объяснимую очередь
тендеров с адекватной географией, требованиями, официальным переходом, аналитикой и полной lineage.

## Acceptance criteria

- [x] Все active opportunities, recommendations, analytics и alerts относятся только к российским
  закупкам; TED/USAspending не попадают в пользовательские current projections или новые live cycles.
- [x] Seed содержит четыре различимых versioned-профиля: автосервис, IT, благоустройство и клининг;
  пользователь может выбрать и изменить каждый без сброса при повторном bootstrap.
- [x] Пользователь может создать пятую и последующие компании, видеть историю профиля и после restart
  получать тот же matching/ingestion/alert pipeline без ограничения «ровно два профиля».
- [x] Профиль хранит описание, услуги, positive/negative keywords, классификаторы, типы заказчиков,
  бюджет, base/service regions, delivery mode, travel и contractor policy с русскими подсказками UI.
- [x] Explainable geography использует российские region codes и service mode: московский onsite
  автосервис отклоняет Камчатку без подрядчиков, contractor coverage меняет решение с evidence,
  remote IT остаётся допустимым для Владивостока, unknown location остаётся явным gap/blocker.
- [x] Русский UI предоставляет список/создание/редактирование компаний, поиск/фильтры/сортировку
  тендеров, отдельный rejected audit и карточку закупки с reasons, blockers и официальным source link.
- [x] AI requirements/deadlines работают только по сохранённой record version, имеют citations либо
  честный `unknown`; карточка сохраняет raw SHA/run/source и SCD2 timeline.
- [x] Scoped analytics показывает decision funnel, coverage, категории/ОКПД2, регионы, заказчиков,
  freshness, ближайшие deadlines, динамику, geography rejects, gaps/blockers, outcomes и profile quality.
- [x] Alerts создаются только для actionable российских закупок, содержат region/deadline/source и
  остаются идемпотентными по версиям профиля/record/policy.
- [x] Все 15 обязательных E2E-сценариев из цели доказаны deterministic tests и browser inspection;
  полный pytest/coverage, Ruff/format/mypy, dbt, Docker health и project-control audit проходят.

## Current verified state

- Финальный regression 15.08.2026: `157` deterministic tests проходят с branch coverage `87.21%`;
  Ruff, format и strict mypy проходят, dbt — `54/54`, Docker Compose — healthy.
- Browser E2E подтвердил четыре отраслевые очереди, Москва/Камчатка, remote IT во Владивостоке,
  фильтры, detail/official ЕИС link, rejected audit, аналитику и русские подсказки профиля.
- Пользовательский `mvp2-restart-proof` изменён через UI с v1 на v2; после restart api/worker история
  `[1, 2]` и мебельная рекомендация `recommended` сохранились в PostgreSQL.
- Current API/UI/analytics/alerts и журнал загрузок показывают только ЕИС/RU; legacy foreign raw/history
  сохранены для аудита, но не попадают в пользовательский current-контур.

## Changed areas

- Intent checkpoint: цель MVP 2.0, source boundary, capability evals и этапы разработки.
- Profile/source checkpoint: расширенный profile contract, four-profile seed, create/history API,
  single-active-version DB invariant и ЕИС-only current/live source policy.
- Geography/data/product checkpoint: canonical regions/delivery mode, blockers, ЕИС notice/contract
  parser, Russian-only dbt staging, six-notice demo, award outcome, filters/sort/detail/create UI,
  deadline/budget/diagnostic/profile-quality analytics и enriched alerts.
- Handoff checkpoint: русские analytics/status labels, current-source run history, сброс фильтров при
  смене компании, браузерные сценарии и Docker restart persistence.

## Decisions made

- ЕИС — единственный подтверждённый live source-authority MVP 2.0. Российские ЭТП не парсятся скрыто:
  новый adapter допустим только после фиксации официального API/RSS/export contract, limits и tests.
- Имеющиеся foreign raw/history не удаляются, но исключаются из current product projections; новые
  live cycles не вызывают TED/USAspending.
- География использует один typed owner: ISO 3166-2 Russian region codes, `onsite|remote|hybrid`,
  service regions, nationwide/travel/contractor policy. UI и matcher не дублируют это решение.
- Четыре профиля — обязательный seed, а не runtime limit. Любое число active user profiles допустимо;
  ingestion остаётся bounded и сохраняет использованные profile versions.
- Вероятность победы и анализ конкурентов не вычисляются; historical winners/amounts остаются facts.

## Next exact step

Активного шага разработки нет; следующая продуктовая стадия начинается только с новой проверяемой цели.

## Blockers

- Нет.

## Non-goals

- Анализ конкурентов, гарантированный прогноз победы и объяснение решения комиссии.
- Автоматическая подача заявки или юридическое заключение о допуске.
- Неограниченная выгрузка, скрытый scraping и user-provided source URLs.
- Production multi-tenancy, auth/RBAC и публичное deployment.

## Verification

```bash
.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q
make lint
make dbt-test
docker compose config --quiet
docker compose ps
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py audit .
```
