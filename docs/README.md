---
title: TenderPulse
project: TenderPulse
type: project
status: active
updated: 2026-08-08
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

### MVP

- TED Search API: актуальные и result notices по узким временным/CPV-фильтрам.
- ЕИС: ограниченные XML/ZIP-пакеты извещений и результатов; ручная дозагрузка является
  поддерживаемым fallback, пока live-канал не подтверждён в Docker.
- USAspending: исторические федеральные contract awards, получатели и суммы. Это источник
  результатов, а не активных закупок США.
- Не более 100 записей на источник за один запуск по умолчанию и не более 500 по явному запросу.
- Неизменяемый raw-артефакт, SHA-256, параметры запроса, время получения, версии canonical-record
  и evidence каждого match.
- Два синтетических демонстрационных профиля: IT/data-интегратор и поставщик медицинского/
  лабораторного оборудования. Они не представляют реальные компании.
- Веб-интерфейс профиля, аналитики, рекомендаций и управляемой дозагрузки; idempotent in-app alerts и
  opt-in HTTPS webhook с журналом попыток. Внешняя отправка выключена по умолчанию.
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
| TED | notices и результаты ЕС | [Search API v3](https://docs.ted.europa.eu/api/latest/search.html) | anonymous POST, date/CPV filters |
| ЕИС | notices, протоколы и контракты РФ | [ЕИС](https://zakupki.gov.ru/) | XML/ZIP packages, bounded import |
| USAspending | contract awards США | [API endpoints](https://api.usaspending.gov/docs/endpoints) | anonymous award search |
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
