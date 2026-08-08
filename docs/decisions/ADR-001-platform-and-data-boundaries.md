---
title: ADR-001 — Platform and data boundaries
type: decision
status: accepted
updated: 2026-08-08
---

# ADR-001: hybrid lakehouse на Python, S3 и PostgreSQL

## Контекст

MVP должен одновременно хранить исходные доказательства, историю изменений, реляционные связи,
аналитические витрины и объяснимый поиск, но намеренно не выгружает весь мировой procurement corpus.
Полноценный distributed Iceberg/Spark stack увеличит операционную поверхность до появления измеренного
объёма, а один PostgreSQL без raw lake не обеспечит независимое восстановление source evidence.

## Решение

- Python 3.12+, FastAPI, Pydantic and SQLAlchemy/Alembic own application contracts.
- S3-compatible MinIO owns immutable content-addressed raw payloads.
- PostgreSQL 16 + pgvector owns canonical entities, SCD2 history, jobs, match evidence and serving queries.
- dbt-postgres owns analytics marts/tests; it does not duplicate ingestion or canonical rules.
- One application image runs API and worker commands; Docker Compose adds PostgreSQL and MinIO.
- Source adapters and LLM adapters are ports. Tests use deterministic fixtures/fakes.

Это hybrid lakehouse: lake хранит первичные доказательства, warehouse обеспечивает constrained canonical
и serving projections. Термин не означает, что MVP уже использует distributed table format.

## Последствия

Плюсы: простое локальное развёртывание, сильные транзакционные инварианты, дешёвое хранение raw,
воспроизводимый lineage. Минусы: аналитическое масштабирование ограничено одним PostgreSQL, Parquet/Iceberg
curated layer пока отсутствует. Пересмотр обязателен, если один bounded-run перестанет укладываться в 500
records, corpus превысит 10 млн canonical versions, либо появится независимый distributed analytics workload.

Object keys, canonical contracts and adapter ports сохраняются при будущей миграции, поэтому отдельные
MinIO/PostgreSQL instances заменяемы и не являются незаменимыми носителями продуктового знания.
