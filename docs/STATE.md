---
title: Текущее состояние
type: state
status: active
updated: 2026-08-16
---

# Текущее состояние

## Active objective

Подготовить закрытый пилот TenderPulse на одной реальной российской компании: согласовать профиль,
разметить bounded-выборку ЕИС и измерить практическую точность actionable-рекомендаций.

## Acceptance criteria

MVP 2.1 — verified:

- [x] Неавторизованный HTML-запрос перенаправляется на `/login`, API отвечает `401`; валидный local
  access code создаёт server-side session, неверный код не раскрывает account, logout отзывает session.
- [x] Access codes хешируются с обязательным secret pepper, не сохраняются в Git/log/URL/browser
  storage; cookie имеет `HttpOnly`, `SameSite`, ограниченный lifetime, а unsafe API защищены CSRF.
- [x] Два account привязаны каждый к одной компании; чужой profile slug не переключает контекст и
  отвечает `404`/`403`. Shared procurement data не становится tenant-owned.
- [x] В account-контуре доступны только `Чистая территория` и `Офисное снабжение`; второй профиль
  покрывает мебель, канцелярию, принтеры/МФУ и расходники и исключает разработку ПО.
- [x] Company user видит обзор, тендеры, аналитику, свой профиль и logout; глобальный selector,
  создание чужих компаний и операторский раздел данных отсутствуют.
- [x] Обзор ограничен первичными KPI и следующим шагом; history/data-quality/outcomes аналитики
  раскрываются вторично и не используют пользовательский жаргон SCD2.
- [x] На viewport 390, 768, 1024 и 1280 px нет horizontal overflow, offscreen controls и тесной
  трёхколоночной history card на промежуточной ширине.
- [x] Docker worker выполняет bounded ЕИС RSS cycle сразу и затем каждый час, сохраняет run evidence,
  продолжает работу после failed cycle и не вызывает TED/USAspending.
- [x] Automatic attachment adapter не заявлен без официального безопасного contract; manual XML/ZIP,
  official link и явный `unknown` сохранены.
- [x] Telegram/email/webhook expansion и public deployment остаются planned; существующие in-app и
  webhook contracts не деградировали.
- [x] Изменение реализовано test-first; `172` tests и branch coverage `86.07%`, Ruff/format/strict mypy,
  `54` dbt tests, rebuilt Docker, live ЕИС cycle, restart и browser acceptance прошли.
- [x] Два local-demo code подготовлены вне Git для передачи пользователю; реализация оформляется
  восстановимым Git checkpoint без ложного заявления об обновлении remote/default branch.

## Current verified state

- Миграция `0008_local_accounts` владеет accounts, keyed-hash credentials и revocable sessions;
  CSRF и account/profile authorization применяются на сервере.
- Account visibility принадлежит bindings: `cleaning-moscow` и `office-supply-moscow`. Legacy profile
  versions и procurement lineage сохранены, но не доступны company accounts.
- Ближайшие сроки аналитики включают только `recommended`/`review`, а rejected records не создают
  ложный actionable backlog.
- Штатные Compose-образы собраны; API, worker, PostgreSQL и MinIO healthy. Worker получил `25` записей
  из официального ЕИС RSS с TLS verification и повторил цикл после restart.
- Browser acceptance прошёл на 390/768/1024/1280 px; реальные cleaning/office login и cross-company
  denial проверены через HTTP journey.

## Changed areas

- Auth/session schema, profile visibility, API/page authorization, analytics projection, UI/navigation,
  worker defaults/resilience, Docker/env, documentation and test/eval evidence changed coherently.
- Canonical procurement, raw/history lineage, organization/outcome authority and source adapters were
  preserved; only their authorized product projection changed.

## Decisions made

- MVP 2.1 — local pre-pilot hardening, а не доказательство ценности на реальной компании.
- Один company account владеет одной profile lineage; notices/raw/history общие, рекомендации и alerts
  вычисляются только в разрешённом profile context.
- Self-registration, password recovery, social login, public deployment и PostgreSQL RLS не входят в этап.
- Airflow не добавляется: schedule принадлежит одному наблюдаемому Docker worker.
- Telegram/email и автоматические attachments отложены до выбора канала и подтверждения source contract.
- Физическое удаление legacy evidence, полная выгрузка ЕИС и автоматическая подача заявок запрещены.

## Non-goals

- Self-registration, password recovery, social login, public deployment и PostgreSQL RLS.
- Telegram/email delivery, Airflow, automatic attachment scraping и автоматическая подача заявок.
- Доказательство pilot precision, 14-дневной надёжности или production readiness.

## Next exact step

Получить от владельца продукта одну реальную компанию и её ограничения, затем составить и вслепую
разметить первые 50 notices ЕИС для pilot precision gate.

## Blockers

- Реальная компания и human labels ещё не предоставлены; это блокирует пилотную валидацию, но не MVP 2.1.

## Verification

```bash
make test
make lint
make dbt-test
docker compose config --quiet
docker compose ps -a
git diff --check
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py audit .
python3 /Users/tbwtk/.codex/skills/immune-project-engineering/scripts/immune_project.py audit . --phase implementation
```
