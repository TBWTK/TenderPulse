---
title: TenderPulse
project: TenderPulse
type: project
status: active
updated: 2026-08-16
---

# TenderPulse

TenderPulse превращает ограниченные, регулярно обновляемые выборки государственных закупок в
проверяемую ленту возможностей для конкретной компании. Пользователь описывает компетенции,
товары, географию и ограничения компании; система нормализует закупки и историю их изменений,
ранжирует релевантные позиции, показывает обязательные требования и сроки и объясняет каждую
рекомендацию ссылками на исходную запись и сохранённые evidence.

## Акторы и сценарии

- **Представитель компании** входит по выданному коду, уточняет свой профиль и проверяет рекомендации.
- **Тендерный специалист** фильтрует источники, сверяет требования/сроки и подписывается на alerts.
- **Аналитик** изучает покупателей, победителей, суммы, категории и географию в витринах.
- **Оператор** запускает Docker-стек, управляет bounded ingestion и контролирует freshness/errors.

## Границы

### MVP 2.0 — accepted baseline

- Пользовательский current scope содержит только закупки российских заказчиков; ЕИС является
  подтверждённым live-authority, а российские ЭТП — официальными destinations/card sources до
  появления документированного machine-readable contract.
- Четыре demo-профиля покрывают автосервис, IT-разработку, благоустройство и клининг. Это seed,
  а не лимит: пользователь может создавать и версионировать собственные компании.
- География учитывает регион выполнения и реальную delivery model (`onsite`, `remote`, `hybrid`),
  contractor coverage и unknown; совпадение страны `RU` само по себе не является преимуществом.
- Русский guided UI разделяет обзор, actionable/rejected тендеры, scoped analytics, каталог/редактор
  компаний и bounded-загрузку на самостоятельные маршруты с единым profile context.

Пользователь принял этот baseline 16.08.2026. MVP 2.1 добавляет локальную account boundary и готовит
тот же pipeline к следующему закрытому пилоту, не объявляя пилот уже проведённым.

### MVP 2.1 — локальная подготовка к пилоту

- Два invitation-style account входят по локальному коду и видят только одну связанную компанию.
- Рабочие профили: клининг и офисное снабжение; legacy versions сохраняются вне account visibility.
- Normal company navigation не содержит global profile selector и operator ingestion console.
- Existing Docker worker регулярно загружает bounded ЕИС RSS; Airflow и скрытый scraping не добавляются.
- UI использует progressive disclosure и проверяется на mobile, intermediate и desktop breakpoints.

### Выход из MVP 2.1: закрытый пилот

- Первый pilot candidate — «Чистая территория»: Москва/МО, клининг помещений и территорий,
  подрядчики допустимы, договоры 500 тыс.–25 млн рублей. Keywords и ограничения до human validation
  считаются рабочими гипотезами, а не подтверждёнными юридическими фактами. При сумме свыше 1 млн
  неизвестный опыт явно переводит тематически подходящую закупку в ручную проверку.
- Одна реальная компания проходит onboarding через тот же UI и получает текущую очередь ЕИС.
- Пользовательская разметка проверяет качество matching, географии и AI-evidence на bounded-выборке.
- Двухнедельный эксплуатационный прогон доказывает freshness, failures, alerts, persistence и recovery.
- Реальные решения `участвовать / отклонить / отложить` сохраняют основания и образуют product evidence.
- Только итоговое pilot-решение `go` открывает Production v1; полный contract находится в
  [текущем состоянии](STATE.md), а evidence map — в [качестве](QUALITY.md).

Agent-assisted pre-evaluation зафиксировал 50 real ЕИС records. Владелец продукта сначала разметил
15-record shortlist, затем оставшиеся 35: итог — 1 `relevant` и 49 `not_relevant`. Matcher оставил
единственный клининговый lot в `review` и отверг остальные (`TP=1`, `TN=49`). Point precision/recall
равны 100%, но 95% Wilson lower bound precision — только 20,65%; целевые 80% ещё не доказаны из-за
единственного positive label.

### Сохранённая foundation MVP 1.0

- ЕИС: актуальные notices 44-ФЗ из официального bounded RSS; ограниченные XML/ZIP-пакеты остаются
  поддерживаемым fallback для исторических извещений и результатов.
- Live ЕИС загружает не более 25 записей по умолчанию и никогда не принимает более 50 за запуск;
  окно публикации ограничено 31 днём, ответ — 2 MiB.
- Неизменяемый raw-артефакт, SHA-256, параметры запроса, время получения, версии canonical-record
  и evidence каждого match.
- Веб-интерфейс сохраняет каждое изменение профиля новой версией и не перезаписывает его bootstrap-ом.
- Карточка рекомендации показывает последний AI attempt для текущей версии notice: coverage
  requirements/deadlines, claims, gaps и verbatim citations. Idempotent in-app alerts и opt-in HTTPS
  webhook ведут журнал попыток; внешняя отправка выключена по умолчанию.
- Основная очередь содержит только `recommended`/`review`. `not_relevant`/`expired` остаются доступными
  в отдельном audit-разделе без AI- или alert-действий; оба представления строятся из одного результата matcher.
- Аналитика профиля явно разделяет текущие решения/actionable deadlines и вторичные history/
  current award outcomes: decision funnel, полноту полей, источники, категории, географию, покупателей,
  сохранённые версии, победителей и суммы. Это наблюдаемые данные, а не прогноз вероятности победы.
- Каждая карточка открывает timeline всех сохранённых версий с raw SHA, ingestion run и официальным URL.
- Source-scoped identity покупателей/поставщиков: исходные aliases и SCD2/raw evidence сохраняются;
  одинаковое имя из разных источников не считается доказанным merge.

### Явно не входит в MVP

- Полная выгрузка источников, скрытый web scraping и обещание полноты всех юрисдикций.
- Автоматическая подача заявки, юридическая проверка допуска и предсказание победы как факта.
- Активные закупки США из USAspending; для этого позже нужен отдельный SAM.gov connector.
- Публичное multi-tenant развёртывание: local code/session не заменяет production identity, perimeter,
  rate limiting, RBAC/RLS и tenant-isolation audit.

## Источники и проверенные границы

| Источник | Роль | Официальный контракт | MVP-режим |
| --- | --- | --- | --- |
| ЕИС RSS | notices 44-ФЗ | [RSS расширенного поиска](https://zakupki.gov.ru/epz/order/extendedsearch/rss.html) | active: HTTPS, 31 дней, ≤50 records, ≤2 MiB |
| ЕИС XML/ZIP | details/history/results | [ЕИС](https://zakupki.gov.ru/) | active bounded manual/import fallback; immutable raw |
| Росэлторг | 44-ФЗ, 223-ФЗ, commercial cards | [Публичный поиск](https://www.roseltorg.ru/torgi) | destination/candidate; public procurement API не доказан |
| Другие российские ЭТП | platform-specific cards | official pages из ЕИС | candidate; adapter только после API/RSS/export contract review |
| TED / USAspending | legacy foreign history | сохранённые adapters MVP 1.0 | исключаются из current UI/analytics/alerts и новых live cycles |
| GigaChat | structured extraction/explanation | [REST API](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api) | optional, cached evidence, no CI calls |

## Навигация

- [Текущее состояние](STATE.md)
- [Этапы](ROADMAP.md)
- [Архитектура](ARCHITECTURE.md)
- [Качество](QUALITY.md)
- [Технический долг](DEBT.md)
- [Данные](DATA.md)
- [Модель угроз](SECURITY.md)
- [Запуск и эксплуатация](RUNBOOK.md)
- [ADR-001: platform and data boundaries](decisions/ADR-001-platform-and-data-boundaries.md)
- [ADR-002: organization identity boundary](decisions/ADR-002-organization-identity-boundary.md)
- [ADR-003: official ЕИС RSS and TLS boundary](decisions/ADR-003-eis-rss-and-tls-boundary.md)
- [ADR-004: Russian source and geography boundary](decisions/ADR-004-russian-source-and-geography-boundary.md)
- [ADR-005: local account and tenant boundary](decisions/ADR-005-local-account-and-tenant-boundary.md)

<!-- immune-project-engineering:docs:start -->
- [Аудит и достаточность контекста](AUDIT.md)
- [Инженерные принципы IMMUNE](IMMUNE.md)
<!-- immune-project-engineering:docs:end -->
