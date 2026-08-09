---
title: Этапы проекта
type: roadmap
status: complete
updated: 2026-08-10
---

# Этапы проекта

| Этап | Проверяемый результат | Критерий завершения | Статус |
| --- | --- | --- | --- |
| Foundation | Fixture → raw evidence → versioned canonical → recommendation API | Domain/source/history/matching tests, Docker config, docs check | done |
| TED | Регулярная bounded-загрузка актуальных notices ЕС | Live smoke + idempotency + freshness/lineage UI | done |
| ЕИС | Актуальные 44-ФЗ notices + XML/ZIP historical fallback | Official RSS live replay, TLS chain, bounds, raw/SCD2 lineage | done |
| USA outcomes | Awards, winners, amounts and buyers enrich analytics | Award API/UI smoke, provenance tests, dbt outcome mart | done |
| AI evidence | Требования/сроки и объяснение с GigaChat | Structured-output eval, citations, unknown handling, cached evidence | done |
| Product | Полный profile input, profile-driven source scope, recommendations, visible AI evidence, analytics, controls и alerts | Current DB profile versions drive versioned HTML/API/matching/ingestion; in-app/webhook idempotency | done |
| Identity | Source-scoped buyers/suppliers and aliases | Backfill all SCD2 versions, dbt relationships, no guessed cross-source merge | done |
| Quality & handoff | Документация совпадает с работающим Docker MVP | Full regression, dbt, live smoke, audit, Git checkpoint и проверенный push | done |
| Product acceptance | Рекомендации, AI-state, navigation, analytics и history образуют честный usable MVP | Two-profile E2E eval, semantic UI tests, browser inspection, full regression | done |

Допустимые статусы: `planned`, `active`, `blocked`, `done`.
