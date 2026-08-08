---
title: ADR-002 — Organization identity boundary
type: decision
status: accepted
updated: 2026-08-08
---

# ADR-002: source-scoped identity before cross-source resolution

## Контекст

TED, ЕИС и USAspending публикуют buyer/supplier names разного качества. Совпадение очищенной строки не
доказывает, что юридические лица одинаковы; агрессивное удаление организационно-правовых форм даёт
ложные merge и делает аналитику необъяснимой. При этом повторяющиеся варианты одного имени внутри
источника полезно нормализовать и связать с исходными версиями.

## Решение

- Сравнительный key строится одним модулем через Unicode NFKC, casefold и схлопывание punctuation/
  whitespace. Юридические формы не удаляются.
- Organization key в MVP — `(source, normalized_name)`. Межисточниковый merge запрещён без отдельного
  устойчивого identifier и evidence-backed resolver.
- Каждая исходная форма сохраняется как alias. Link хранит role, ordinal, source spelling, raw SHA и
  ссылку на конкретную SCD2-версию.
- `init-db` backfill-ит links для всей сохранённой истории; повтор не создаёт дубликаты.

## Последствия

Аналитика получает устойчивых buyers/suppliers внутри source и полную прослеживаемость. Одна реальная
организация может оставаться несколькими source-scoped сущностями — это сознательный false-negative,
предпочтительный ложному факту. Будущий resolver расширит модель identifier/candidate edges отдельным
владельцем, не меняя исходные aliases и links.
