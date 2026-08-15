---
title: Этапы проекта
type: roadmap
status: active
updated: 2026-08-15
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
| MVP 2.0 intent | Российский source boundary и полный acceptance contract | Source matrix, baseline audit, 15 E2E scenarios и non-goals зафиксированы до кода | done |
| MVP 2.0 profiles | 4 demo + произвольные versioned user companies | Create/edit/history/reseed tests; source scope не зависит от числа профилей | done |
| MVP 2.0 geography | Explainable region/service-mode policy | Москва/Камчатка, contractor, remote Владивосток и unknown-location evals | done |
| MVP 2.0 Russian data | Только bounded российские active notices/outcomes | ЕИС current/details/results fixtures, foreign exclusion, official links and lineage | done |
| MVP 2.0 product UI | Понятный русский company/tender workflow | Guided profile, filters/sort/detail, four-profile + create-company deterministic E2E | done |
| MVP 2.0 analytics | География, deadlines, dynamics, blockers и quality | Typed API/UI scopes, deterministic projection tests и dbt coherence | done |
| MVP 2.0 handoff | Воспроизводимый Docker MVP и Git checkpoint | Full regression/dbt/health/browser/audit, restart persistence и verified push | done |
| MVP 2.0 UX acceptance | Раздельный, доступный и визуально цельный рабочий интерфейс | Route isolation, design system, responsive browser journeys, stakeholder re-review | ready for review |

Допустимые статусы: `planned`, `active`, `blocked`, `done`.
