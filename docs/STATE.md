---
title: Текущее состояние
type: state
status: complete
updated: 2026-08-10
---

# Текущее состояние

## Active objective

Довести TenderPulse от проверенного инженерного прототипа до принимаемого продуктового MVP: пользователь
должен видеть отделённые рекомендации, честный AI evidence state, согласованную навигацию, достоверную
аналитику текущего среза и видимую историю без ложных обещаний полноты или вероятности победы.

## Acceptance criteria

- [x] Очередь по умолчанию содержит только `recommended` и `review`; `not_relevant`/`expired` доступны
  отдельно как рассмотренные записи, а counts и заголовки не смешивают эти понятия.
- [x] AI-action доступен только для actionable records, явно ограничен сохранёнными evidence fields и
  после validated attempt показывает coverage/result вместо бессмысленного повторного запуска.
- [x] Порядок sidebar совпадает с DOM, active section обновляется при переходе/scroll и проверяется тестом.
- [x] Аналитика выбранного профиля показывает decision funnel, current-data coverage, категории,
  географию, покупателей, outcomes и history/version counts; каждый показатель имеет точный scope label.
- [x] Карточка показывает число версий и даёт открыть version timeline с raw SHA/run/source evidence.
- [x] Оба demo-профиля проходят end-to-end product eval; unknown остаётся явным, а нерелевантные записи
  не выглядят рекомендациями и не создают AI/alert actions.
- [x] Полный pytest/coverage, Ruff, format, strict mypy, dbt, Docker health, browser inspection и
  project-control audit проходят; docs/API/UI/data contracts согласованы.

## Current verified state

- Data/platform foundation сохранён: bounded TED/ЕИС/USA adapters, immutable raw, SCD2 canonical,
  source-scoped identity, два versioned profiles, matcher, GigaChat evidence, alerts, dbt и Docker.
- Product acceptance checkpoint 10.08.2026: 131 deterministic tests pass; branch coverage 86.97%; Ruff,
  format и strict mypy pass; dbt `PASS=53`; rebuilt API/worker/db/minio containers healthy.
- Browser inspection двух профилей подтверждает разделённые actionable/rejected views, отсутствие
  AI-action у rejected, cached evidence state, sidebar scroll-spy, scoped analytics и version timeline;
  browser console errors: 0.
- Реальный Docker snapshot: IT profile — 2 actionable / 8 rejected из 10; MedLab — 3 actionable
  (`2 recommended + 1 review`) / 7 rejected. Analytics показывает coverage, distributions, 19 current
  records / 19 versions и 3 award outcomes без заявления о win probability.

## Changed areas

- Product queue projection: API группирует единый ranked result, template macro рендерит actionable и
  rejected audit views, JavaScript управляет AI-action/scroll-spy, CSS показывает audit/action states;
  tests фиксируют наблюдаемую семантику.
- Product analytics projection: typed API/UI contract объединяет decision funnel, data coverage,
  distributions, SCD2 history и award outcomes с явными scope labels; repository предоставляет полный lineage.
- Matching scope: `current_opportunities` является единым владельцем active/planned notice selection для
  recommendation API, dashboard и alerts. Workspace date использует московский business day.

## Decisions made

- Product MVP показывает ranked candidates, но default recommendation queue и rejected audit trail —
  разные представления одной matcher-authority, а не два независимых расчёта.
- Analytics для UI строится из canonical records/versions и matcher results с явным scope (`current` или
  `history`); декоративные labels не могут расширять фактический scope.
- `validated` означает проверенный structured output, а не полноту source evidence; `unknown` не скрывается.
- Предсказание победы, автоматическая заявка и полнотекстовое скачивание произвольных вложений не входят
  в этот MVP и не будут имитироваться эвристикой или LLM.

## Next exact step

Провести пользовательскую приёмку текущего Docker MVP по сохранённым экранам и зафиксировать только
новые бизнес-требования отдельным следующим этапом.

## Blockers

- Нет.

## Non-goals

- Полная выгрузка источников, скрытый scraping или гарантия полноты всех юрисдикций.
- Прогноз вероятности победы, объяснение решения закупочной комиссии и автоматическая подача заявки.
- Production auth/RBAC/tenant isolation и публичное deployment.
- Третий профиль, SAM.gov и произвольные user-provided source URLs.

## Verification

```bash
.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q
make lint
make dbt-test
docker compose config --quiet
docker compose ps
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py audit .
```
