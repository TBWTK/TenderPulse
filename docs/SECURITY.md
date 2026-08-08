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
| TLS interception | checked-in public root + issuing CA, verification always on, fingerprint tests and documented expiry | upstream chain rotation |
| SSRF | fixed adapter base URLs, validated object keys, no user-provided fetch URL | compromised official source |
| Prompt injection | source text is data, no LLM tools, structured schema and citations | semantic manipulation remains possible |
| Poisoned/changed source | raw hash, source locator, SCD2 diff, validation issues | source itself may publish wrong facts |
| Cross-company leakage | local single-tenant MVP; no public deployment | missing auth/RBAC blocks public use |
| Alert duplication | transactional outbox + stable webhook `Idempotency-Key` + attempt history | receiver must implement deduplication |
| Webhook secret/SSRF | opt-in config only, HTTPS validation, destination stored only as SHA-256, no response body | host operator controls egress target; query-token rotation is external |
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

`certs/russian_trusted_sub_ca_pem.crt` — публичный issuing CA `Russian Trusted Sub CA` для текущей
цепочки `*.zakupki.gov.ru`. Ожидаемый SHA-256 fingerprint:
`21:55:78:50:36:C9:00:DB:B5:F1:BB:2A:15:69:C8:0C:55:59:5B:D6:BF:94:86:7A:29:BB:DD:BC:7D:88:A3:F2`;
срок действия — до 19.07.2029. Сертификат получен из AIA leaf-сертификата ЕИС и проверен указанным
root. Любая замена требует проверки chain, fingerprint/expiry tests и live smoke.
