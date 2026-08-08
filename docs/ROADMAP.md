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
| ЕИС | Актуальные 44-ФЗ notices + XML/ZIP historical fallback | Official RSS live replay, TLS chain, bounds, raw/SCD2 lineage | done |
| USA outcomes | Awards, winners, amounts and buyers enrich analytics | Award API/UI smoke, provenance tests, dbt outcome mart | done |
| AI evidence | Требования/сроки и объяснение с GigaChat | Structured-output eval, citations, unknown handling, cached evidence | done |
| Product | Полный profile input, recommendations, visible AI evidence, analytics, controls и alerts | Versioned profile/evidence HTML/API integration, in-app/webhook idempotency | done |
| Identity | Source-scoped buyers/suppliers and aliases | Backfill all SCD2 versions, dbt relationships, no guessed cross-source merge | done |
| Quality & handoff | Документация совпадает с работающим Docker MVP | Full regression, dbt, live smoke, audit, Git checkpoint/push approval | active |

Допустимые статусы: `planned`, `active`, `blocked`, `done`.
