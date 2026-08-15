---
title: TenderPulse
project: TenderPulse
type: project
status: active
updated: 2026-08-15
---

# TenderPulse

TenderPulse превращает ограниченные, регулярно обновляемые выборки государственных закупок в
проверяемую ленту возможностей для конкретной компании. Пользователь описывает компетенции,
товары, географию и ограничения компании; система нормализует закупки и историю их изменений,
ранжирует релевантные позиции, показывает обязательные требования и сроки и объясняет каждую
рекомендацию ссылками на исходную запись и сохранённые evidence.

## Акторы и сценарии

- **Представитель компании** создаёт профиль, проверяет рекомендации и отмечает полезность.
- **Тендерный специалист** фильтрует источники, сверяет требования/сроки и подписывается на alerts.
- **Аналитик** изучает покупателей, победителей, суммы, категории и географию в витринах.
- **Оператор** запускает Docker-стек, управляет bounded ingestion и контролирует freshness/errors.

## Границы

### MVP 2.0 — active scope

- Пользовательский current scope содержит только закупки российских заказчиков; ЕИС является
  подтверждённым live-authority, а российские ЭТП — официальными destinations/card sources до
  появления документированного machine-readable contract.
- Четыре demo-профиля покрывают автосервис, IT-разработку, благоустройство и клининг. Это seed,
  а не лимит: пользователь может создавать и версионировать собственные компании.
- География учитывает регион выполнения и реальную delivery model (`onsite`, `remote`, `hybrid`),
  contractor coverage и unknown; совпадение страны `RU` само по себе не является преимуществом.
- Русский guided UI объединяет управление компаниями, actionable/rejected тендеры, detail/evidence,
  официальный переход, scoped analytics и alerts.

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
- Аналитика выбранного профиля явно разделяет текущий срез active/planned notices, SCD2 history и
  current award outcomes: decision funnel, полноту полей, источники, категории, географию, покупателей,
  сохранённые версии, победителей и суммы. Это наблюдаемые данные, а не прогноз вероятности победы.
- Каждая карточка открывает timeline всех сохранённых версий с raw SHA, ingestion run и официальным URL.
- Source-scoped identity покупателей/поставщиков: исходные aliases и SCD2/raw evidence сохраняются;
  одинаковое имя из разных источников не считается доказанным merge.

### Явно не входит в MVP

- Полная выгрузка источников, скрытый web scraping и обещание полноты всех юрисдикций.
- Автоматическая подача заявки, юридическая проверка допуска и предсказание победы как факта.
- Активные закупки США из USAspending; для этого позже нужен отдельный SAM.gov connector.
- Публичное multi-tenant развёртывание до появления аутентификации, RBAC и tenant isolation.

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
