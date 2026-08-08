---
title: Модель угроз
type: security
status: draft
updated: 2026-08-08
---

# Модель угроз

## Активы и границы доверия

Активы: GigaChat credentials/access token, чувствительный профиль компании, raw procurement data,
canonical history, recommendation evidence и alert destinations. Недоверенные границы: все source
payloads, пользовательские файлы/поля, LLM output и URL/текст внутри notice.

## Угрозы и обязательные контроли

| Угроза | Контроль MVP | Остаточный риск |
| --- | --- | --- |
| Secret leakage | `.env` ignored, redaction, tokens only in memory, no config endpoint | host/container admin access |
| TLS interception | checked-in public root CA, verification always on, expiry/fingerprint test | upstream chain rotation |
| SSRF | fixed adapter base URLs, validated object keys, no user-provided fetch URL | compromised official source |
| Prompt injection | source text is data, no LLM tools, structured schema and citations | semantic manipulation remains possible |
| Poisoned/changed source | raw hash, source locator, SCD2 diff, validation issues | source itself may publish wrong facts |
| Cross-company leakage | local single-tenant MVP; no public deployment | missing auth/RBAC blocks public use |
| Alert duplication | transactional outbox + idempotency key | channel-specific delivery ambiguity |
| XML entity attack | DTD/entity resolution disabled, ZIP size/member limits | parser/library vulnerabilities |

## Deployment boundary

До появления authentication, RBAC, tenant isolation, CSRF controls and recovery tests сервис доступен
только локально или в защищённом внутреннем контуре. Компания должна разрешить передачу конкретных
полей профиля и фрагментов notice внешнему GigaChat; deterministic matcher работает без LLM.

## Certificate policy

`certs/russian_trusted_root_ca_pem.crt` — публичный корневой сертификат НУЦ Минцифры, не секрет.
Ожидаемый SHA-256 fingerprint:
`D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`.
Его срок истекает 27.02.2032. Отключение TLS verification не является fallback.
