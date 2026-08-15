---
title: "ADR-005: local account and tenant boundary"
type: decision
status: accepted
updated: 2026-08-16
---

# ADR-005: local account and tenant boundary

## Контекст

MVP 2.0 выбирает любой active company profile через query parameter и global selector; session,
authentication и authorization отсутствуют. MVP 2.1 должен дать два локальных входа, каждый к одной
компании, не превращая общий lakehouse ЕИС в две копии и не заявляя public multi-tenancy.

`company_profiles.active` уже владеет понятием current immutable profile version. Использовать тот же
flag для tenant visibility означало бы две authority и разрушило бы version invariant.

## Решение

- `accounts` владеют локальной identity, role/status и binding к одному profile slug.
- `access_credentials` хранят только keyed hash высокоэнтропийного access code и его безопасный prefix.
- Успешный login создаёт opaque server-side `web_sessions`; browser получает только session cookie и
  отдельный CSRF token. Logout отзывает session.
- Company endpoints всегда получают разрешённый profile slug из authenticated account. Запрошенный
  чужой slug fail-closed; fallback к первому профилю запрещён в authenticated context.
- Procurement raw/canonical/history остаются shared source facts. Profile versions, recommendations,
  analytics, alerts и user actions проецируются только через account binding.
- Bootstrap создаёт bindings для двух canonical demo profiles, но не удаляет legacy profile history.
- Company navigation не показывает operator ingestion controls. Role `operator` предусмотрен contract,
  но local MVP 2.1 не обязан выдавать третий credential.

## Рассмотренные варианты

| Вариант | Причина отклонения/выбора |
| --- | --- |
| Query profile selector | отсутствует identity и cross-company isolation; отклонён |
| Raw API key на каждом browser request | секрет живёт в browser storage и смешивает human/API auth; отклонён |
| Access code → signed stateless cookie | нет server-side revocation/audit; отклонён |
| Access code → server-side session | отзыв, expiry, audit и минимальный UI; выбран |
| Отдельная БД на компанию | дублирует shared ЕИС lakehouse и усложняет local operations; отклонён |
| Self-registration | расширяет abuse, verification и recovery surface до pilot evidence; отложен |

## Инварианты безопасности

- Access code и pepper никогда не хранятся в Git, URL, logs или database plaintext.
- Hash использует secret pepper; пустой/дефолтный production-like pepper fail-closed.
- Authentication failure не раскрывает существование account.
- Session имеет expiry/revocation; cookie — `HttpOnly` и `SameSite=Lax`, `Secure` обязателен вне localhost.
- Unsafe authenticated API request требует совпадающий CSRF token.
- Authorization проверяется server-side для HTML и API; скрытая navigation не является контролем.

## Последствия

Нужны Alembic migration, auth repository/service, middleware/dependencies, login/logout UI, bootstrap
credentials из local env, tenant-aware API/page queries, security tests и обновлённый runbook. Public
multi-tenancy всё ещё требует TLS termination, production secret manager, account lifecycle, recovery,
rate limiting, RLS decision и отдельного threat review.
