---
title: Аудит TenderPulse
type: audit
status: active
updated: 2026-08-15
---

# Аудит TenderPulse

## Вывод о достаточности контекста

`sufficient` для начала UX-переработки. Пользователь явно отклонил текущий MVP из-за перегруженности
и непонятности интерфейса, но подтвердил, что основная продуктовая логика выглядит рабочей. Изменение
не затрагивает data/domain/API contracts; наблюдаемый текущий UI и deterministic suite дают baseline.

## Источники и доступность контекста

| Область | Статус | Источник/evidence | Влияние неизвестного | Следующее действие |
| --- | --- | --- | --- | --- |
| Бизнес-задача и ожидаемый результат | confirmed | обратная связь 15.08.2026, `docs/STATE.md` | Субъективный вкус остаётся | Route IA + screenshots + повторная review |
| Акторы и сценарии | confirmed | `docs/README.md`, работающий UI/API | Материальных unknown нет | Сохранить company/tender/analytics/data journeys |
| Данные и интеграции | confirmed | `docs/DATA.md`, architecture, tests | UI может скрыть evidence | Не менять owners; route/context tests |
| Развёртывание и эксплуатация | confirmed | Compose, `docs/RUNBOOK.md`, healthy baseline | Новый frontend build не нужен | Оставить FastAPI/Jinja/CSS в текущем image |

Допустимые статусы: `confirmed`, `inferred`, `unknown`, `not applicable`.

## Бизнес-анализ

### Проблема и желаемый исход

Одна страница одновременно является обзором, поиском тендеров, аналитической витриной, редактором
профиля, формой создания компании и ingestion console. Browser baseline: `6800 px` при viewport
`720 px`, `57` content blocks, `5` форм и `8` заголовков h1/h2. Желаемый исход — пользователь понимает
текущую задачу и следующий шаг без изучения всей системы.

### Границы и non-goals

В scope: route-based information architecture, shared layout/navigation, focused pages, design tokens,
responsive/accessibility states и сохранение существующих действий. Не в scope: matching, procurement
schema, dbt semantics, source/LLM contracts, authentication, SPA/framework migration и branding research.

## Аудит текущего состояния

`main` и `origin/main` указывали на `5a50cf6`, worktree до начала изменения был clean. MVP 2.0 имел
`157 passed`, branch coverage `87.21%`, dbt `54/54`, healthy Docker и browser E2E. Web owner сейчас —
один `dashboard.html` с anchor navigation и route `/`; `tender_detail.html` уже отдельный. Пользовательская
приёмка отменяет прежний вывод о готовности UI, но не результаты domain/data проверок.

## Архитектурные варианты

| Вариант | Сильные стороны | Риски/стоимость | Соответствие требованиям |
| --- | --- | --- | --- |
| Только CSS/типографика | минимальный diff | не исправляет смешение задач и 6800 px flow | недостаточно |
| Accordions/tabs внутри `/` | сохраняет один route | скрывает сложность, слабые deep links/navigation state | частично |
| Отдельные server-rendered routes | один state owner, deep links, progressive enhancement | новые context/templates/tests | рекомендуется |
| SPA | богатые transitions/state | второй toolchain/state owner без MVP-выгоды | избыточно |

## Рекомендация и обоснование

Оставить Python/FastAPI/Jinja и vanilla CSS/JS: они уже владеют page/API contract, работают в Docker и
достаточны для route-based UI. Добавить shared base/partials и focused templates. Это сохраняет server
semantics, TestClient verification и отсутствие нового build/dependency boundary.

## Риски и неизвестные

| Риск/unknown | Вероятность | Влияние | Проверка или mitigation | Владелец |
| --- | --- | --- | --- | --- |
| Новый дизайн всё ещё воспринимается сложным | medium | high | page isolation + screenshots + stakeholder review | Product/UI |
| Потеря действия при split | medium | high | route capability tests + full regression + browser journeys | API/Web |
| Mobile overflow/недоступный control | medium | medium | 390×844 browser inspection, labels/focus tests | CSS/templates |
| Старые `/#anchor` ссылки | low | low | `/` остаётся overview; новые nav links документированы | API/Web |

## Ландшафт проверок

Route isolation/navigation/accessibility contracts; existing API/domain suite; TestClient journeys for
tenders, profiles and ingestion; browser screenshots and DOM metrics at desktop/mobile; console errors;
Docker rebuild/health; dbt regression; project-control/IMMUNE audits. Live ЕИС/GigaChat не нужен:
external contract не меняется, deterministic fixtures остаются владельцем release evidence.

## Открытые вопросы и блокеры

Нет блокеров. Конкретный визуальный вкус пользователя остаётся предметом финальной review, но не меняет
выбранную обратимую server-rendered архитектуру.

## Решение о начале реализации

`allowed`: intent, architecture и verification map зафиксированы; docs-phase gate должен пройти до кода.
