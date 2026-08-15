---
title: Текущее состояние
type: state
status: active
updated: 2026-08-15
---

# Текущее состояние

## Active objective

Добиться пользовательской приёмки MVP 2.0 через новый понятный веб-интерфейс: разделить перегруженную
страницу на самостоятельные рабочие разделы, ввести единый дизайн-код и сохранить все доказанные
сценарии тендеров, компаний, аналитики, загрузки и прослеживаемости.

## Acceptance criteria

- [x] Глобальная навигация ведёт на самостоятельные маршруты: обзор, тендеры, аналитика, компании и
  загрузка данных; активный раздел, выбранная компания и назначение страницы понятны без прокрутки.
- [x] Обзор показывает только следующий полезный шаг: actionable-счётчики, ближайшие сроки,
  свежесть данных, последние alerts и короткие переходы; на нём нет редакторов и длинных аудитов.
- [x] Тендеры имеют компактные фильтры, ясную иерархию карточки и отдельное представление отклонённых;
  detail сохраняет официальную ссылку, географическое объяснение, requirements и lineage.
- [x] Компании разделены на каталог, отдельный редактор и отдельное создание; сложные поля сгруппированы,
  снабжены подсказками, а история версий не конкурирует с основным действием.
- [x] Аналитика и загрузка данных находятся на отдельных страницах и не содержат несвязанных форм;
  аналитические scope/unknown и bounded ЕИС-контракт остаются явными.
- [x] Единый дизайн-код определяет типографику, цвет, отступы, состояния, карточки, кнопки, формы и
  responsive-поведение; при ширине 390 px нет горизонтального переполнения и потери действий.
- [x] Семантические landmarks, видимый keyboard focus, labels, skip-link и понятные статусы обеспечивают
  базовую доступность; критичный сценарий не зависит только от цвета или hover.
- [x] Все существующие business/API/evidence/matching тесты остаются зелёными; новые route-isolation,
  navigation, responsive и browser journey проверки доказывают отсутствие прежней перегрузки.

## Current verified state

- UX-релиз 15.08.2026: `/`, `/tenders`, `/analytics`, `/companies`, `/companies/new`,
  `/companies/{slug}` и `/data` имеют отдельные назначения и общий route navigation/profile context.
- Главная уменьшена с `6800` до `1095 px` при viewport `1280×720`, с `57` до `10` content blocks и
  с `5` до `0` форм; это меньше двух viewport вместо прежних 9,4.
- Browser inspection всех семи journeys: правильный active state, `0` unlabeled controls, skip-link,
  отсутствие horizontal overflow. На `390×844` все пять nav-действий видимы в пределах `10..380 px`.
- Очередь показывает `recommended/review`; `10` отклонённых записей свёрнуты отдельно и имеют `0`
  AI-actions. Кнопка объясняет, что извлекает требования/сроки только из сохранённой версии.
- Финальный regression: `160` tests, branch coverage `87.43%`; Ruff/format/strict mypy — pass;
  dbt `PASS=54 WARN=0 ERROR=0`; `git diff --check` — pass; пересобранные api/worker/db/minio — healthy.
- Финальный regression 15.08.2026: `157` deterministic tests проходят с branch coverage `87.21%`;
  Ruff, format и strict mypy проходят, dbt — `54/54`, Docker Compose — healthy.
- Browser E2E подтвердил четыре отраслевые очереди, Москва/Камчатка, remote IT во Владивостоке,
  фильтры, detail/official ЕИС link, rejected audit, аналитику и русские подсказки профиля.
- Пользовательский `mvp2-restart-proof` изменён через UI с v1 на v2; после restart api/worker история
  `[1, 2]` и мебельная рекомендация `recommended` сохранились в PostgreSQL.
- Current API/UI/analytics/alerts и журнал загрузок показывают только ЕИС/RU; legacy foreign raw/history
  сохранены для аудита, но не попадают в пользовательский current-контур.
- UX-аудит 15.08.2026: технически зелёная главная имеет `6800 px` scroll height при viewport `720 px`,
  `57` section/article blocks, `5` форм и восемь разных h1/h2-задач; пользователь MVP не принял.

## Changed areas

- Delivered UX mutation: server-rendered page routes/templates, shared navigation/layout/design tokens,
  focused tender/company/analytics/data pages, responsive and accessibility contracts.
- Not affected: canonical procurement model, matching/geography, persistence/schema, ingestion bounds,
  AI evidence, alert policy, dbt marts and external source adapters.

## Decisions made

- ЕИС — единственный подтверждённый live source-authority MVP 2.0. Российские ЭТП не парсятся скрыто:
  новый adapter допустим только после фиксации официального API/RSS/export contract, limits и tests.
- Имеющиеся foreign raw/history не удаляются, но исключаются из current product projections; новые
  live cycles не вызывают TED/USAspending.
- География использует один typed owner: ISO 3166-2 Russian region codes, `onsite|remote|hybrid`,
  service regions, nationwide/travel/contractor policy. UI и matcher не дублируют это решение.
- Четыре профиля — обязательный seed, а не runtime limit. Любое число active user profiles допустимо;
  ingestion остаётся bounded и сохраняет использованные profile versions.
- Вероятность победы и анализ конкурентов не вычисляются; historical winners/amounts остаются facts.
- Один длинный dashboard больше не является владельцем всего UI. FastAPI page routes владеют задачами,
  общий layout — навигацией/design tokens, а API/domain contracts остаются без изменений.

## Next exact step

Провести повторную пользовательскую приёмку в локальном приложении `http://127.0.0.1:8010`;
до явного подтверждения пользователя проект остаётся технически готовым к review, но MVP не объявляется принятым.

## Blockers

- Нет.

## Non-goals

- Анализ конкурентов, гарантированный прогноз победы и объяснение решения комиссии.
- Автоматическая подача заявки или юридическое заключение о допуске.
- Неограниченная выгрузка, скрытый scraping и user-provided source URLs.
- Production multi-tenancy, auth/RBAC и публичное deployment.
- Изменение matching, procurement schema, dbt-метрик или live-source контрактов.
- SPA-фреймворк, визуальный page builder и внешняя дизайн-система.

## Verification

```bash
.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q
make lint
make dbt-test
docker compose config --quiet
docker compose ps
git diff --check
python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py audit .
```
