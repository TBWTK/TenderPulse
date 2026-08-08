---
title: Этапы проекта
type: roadmap
status: draft
updated: 2026-08-08
---

# Этапы проекта

| Этап | Проверяемый результат | Критерий завершения | Статус |
| --- | --- | --- | --- |
| Foundation | Fixture → raw evidence → versioned canonical → recommendation API | Domain/source/history/matching tests, Docker config, docs check | done |
| TED | Регулярная bounded-загрузка актуальных notices ЕС | Live smoke + idempotency + freshness/lineage UI | done |
| ЕИС | XML/ZIP notices РФ с ручным fallback | Safe package parser/upload done; live TLS/layout still unresolved | blocked |
| USA outcomes | Awards, winners and buyers enrich analytics | Award API smoke, provenance tests, marts | done |
| AI evidence | Требования/сроки и объяснение с GigaChat | Structured-output eval, citations, unknown handling, cached evidence | done |
| Product | Профиль, recommendations, analytics, load controls и alerts | HTML/API integration and alert idempotency | done |
| Quality & handoff | Документация совпадает с работающим Docker MVP | Full regression, dbt, live smoke, audit, Git checkpoint | active |

Допустимые статусы: `planned`, `active`, `blocked`, `done`.
