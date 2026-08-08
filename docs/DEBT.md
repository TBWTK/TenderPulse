---
title: Технический долг
type: debt
status: active
updated: 2026-08-08
---

# Технический долг

| ID | Проблема и доказательство | Влияние | Причина отсрочки | Условие решения | Статус |
| --- | --- | --- | --- | --- | --- |
| D-001 | Pytest сообщает `ResourceWarning` от короткоживущих SQLite `StaticPool` fixtures | Шум в локальном test output; production PostgreSQL не затронут | Требуется единый managed DB fixture вместо локальных helper-ов | Все engine/session закрываются fixture teardown; `ResourceWarning` отсутствует без фильтра | open |
| D-002 | Starlette предупреждает о deprecation `httpx` TestClient и предлагает `httpx2` | Будущий upgrade может сломать API tests | Экосистема ещё сохраняет совместимый TestClient | Перейти на поддержанный transport после стабилизации FastAPI/Starlette dependency | open |
| D-003 | Manual ingestion выполняется синхронно в API process | Запрос до 500 records может быть долгим | Для локального bounded MVP durable queue избыточна | Добавить persisted command queue/claim/retry и 202 progress API до публичного deployment | open |

Невыполненный acceptance criterion является незавершённой работой, а не техдолгом.

Live ЕИС и public deployment controls — незавершённые capability, а не техдолг; они остаются в
`STATE.md`, `ROADMAP.md` и `SECURITY.md`.
