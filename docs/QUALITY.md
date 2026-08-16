---
title: Качество
type: quality
status: active
updated: 2026-08-16
---

# Качество

## Profile discovery and human-review contour — active evidence plan

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Official query contract | unit + bounded live smoke | fixture HTTP / ЕИС RSS | query validation and captured request | fixed URL, search phrase + morphology, ≤50/≤31 days | passing |
| Deterministic discovery | business contract eval | two exact profile versions | plan snapshot, dedupe and cap cases | ≤3 useful phrases/profile; overflow fails before fetch | passing |
| Run traceability | component integration | fixture RSS/raw/repository | profile/query success + one-query failure | one run per pair; exact metadata/raw SHA/failure visible | passing |
| Immutable review | migration + repository eval | SQLite/PostgreSQL | append revision and list history | exact account/profile/record/raw identity retained | passing |
| Tenant/stale safety | adversarial API eval | two accounts + changed record/profile | foreign and stale submissions | fail closed with 404/409; no hidden fallback | passing |
| Blind review UI | route/static/browser | 390/768/1280 px | inspect content, form, nav and overflow | raw facts/official link visible; matcher output absent | passing |
| Honest pilot boundary | docs/artifact audit | supplied 15-row document | exact import + scope assertions | human labels preserved; shortlist metric is not pilot claim | passing |
| Release coherence | full regression | local/Compose/dbt/Git | release commands | tests/coverage/lint/dbt/health/audits pass | passing |

Fail-first order: query/plan/run tests → discovery implementation → review schema/repository/API/UI tests →
implementation → full verification. Live source proves current compatibility only; deterministic fixtures
own CI. Supplied human evidence remains a separate immutable artifact and is never fabricated or completed by code.

Fail-first signatures: missing `tenderpulse.discovery`, then missing `tenderpulse.human_reviews`;
browser acceptance separately exposed 179-card overload and `396 > 390` mobile width. Final evidence:
`238` tests, `85.94%` branch coverage, Ruff/format/strict mypy, Alembic `0009`, dbt `71/71`, healthy
rebuilt Compose, six successful official profile queries, API health, 15-card 1280/768/390 browser
inspection with no overflow/matcher output/console errors, and `0` persisted human reviews.

## MVP 2.1 — complete evidence

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Login/session lifecycle | unit + integration | fixture PostgreSQL/SQLite + TestClient | `tests/test_auth.py` | generic failure, session expiry/revocation, secure cookie contract | pass |
| Cross-company isolation | adversarial API/page eval | two accounts/two profiles | foreign slug/query/API mutations | own profile succeeds; чужой profile `404/403`, no fallback | pass |
| Secret/CSRF safety | security contract | app config + HTTP | hash inspection, cookie flags, unsafe requests | no plaintext code; missing/mismatch CSRF rejected | pass |
| Two-company catalog | migration/bootstrap E2E | legacy DB + reseed | upgrade → seed → restart | exactly two account-visible profiles; legacy history preserved | pass |
| Office relevance | business eval | Russian fixtures | furniture/stationery/MFP/software cases | office supply ranks; software development rejects | pass |
| Role-based IA | route/HTML/browser | authenticated company session | nav + direct `/data`/creation attempts | no selector/operator controls; own company editor works | pass |
| Calm analytics | content + browser | seeded analytics | section budget + progressive disclosure | primary metrics limited; history/outcomes secondary; no SCD2 label | pass |
| Responsive UI | browser visual/DOM | 390/768/1024/1280 | overflow/overlap/action bounds | width equal, controls usable, no cramped 3-column history | pass |
| Automatic ЕИС RSS | worker/component + Docker | fixture and live ЕИС | immediate cycle, failed cycle, next cycle | bounded EIS-only run evidence; worker continues; failures visible | pass |
| Document boundary | contract review + negative tests | official locator/manual files | unsupported automatic attachment request | no hidden scraping; manual XML/ZIP and `unknown` explicit | pass |
| Regression/release | full suite + dbt + Docker | local and rebuilt Compose | documented verification chain | coverage ≥85%, all gates healthy, restart preserves auth/profile | pass |

Fail-first order: auth/tenant contracts → schema migration/bootstrap → UI authorization → worker/responsive.
Runtime presence is not evidence until the dedicated row is `passing` with recorded output.
Initial fail-first run 16.08.2026: selected MVP 2.1 suite stopped during collection with
`ModuleNotFoundError: tenderpulse.auth`; this proves the accepted auth owner does not yet exist before code.

Final evidence 16.08.2026: `172` tests pass with `86.07%` branch coverage; Ruff, format and strict mypy
pass; dbt reports `PASS=54 WARN=0 ERROR=0`. Rebuilt Compose services are healthy; a live official ЕИС
RSS cycle ingested `25` bounded records. Authenticated cleaning/office HTTP journeys deny foreign profile
access. Browser DOM inspection at 390/768/1024/1280 px reports no overflow/offscreen controls, and nearest
deadlines contain only actionable decisions.

## Cleaning pilot-candidate onboarding — active evidence plan

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Confirmed profile facts | profile contract | `mvp21_profiles.json` | `tests/test_mvp21_profiles.py` | Москва/МО, contractors, 500k–25m совпадают с вводом пользователя | passing |
| Cleaning relevance breadth | parameterized business eval | synthetic ЕИС notices | ≥5 cleaning scenarios | premises/territory/seasonal scopes classify as expected | passing |
| False-positive boundaries | adversarial business eval | product-only/specialized fixtures | ≥5 negative/review scenarios | unrelated/special scopes blocked; uncertainty reviewed | passing |
| Budget eligibility | unit + API contract | in/out/unknown/mixed amount fixtures | matcher/blocker serialization | out of range blocks; unknown remains gap/review | passing |
| Geography via contractors | business eval | Москва/МО/другой регион | matcher evidence | direct region recommended; contractor region review | passing |
| Legal unknown honesty | content/contract review | profile constraints + typed threshold | source audit + matcher/UI label | no invented licence; >1m unknown experience requires review | passing |
| Versioned local onboarding | authenticated E2E + restart | Docker PostgreSQL | GET v1 → PUT v2 → restart → history | v1 retained, v2 active and account-bound | passing |
| Regression and Git delivery | full release chain | local + Compose + GitHub | test/lint/dbt/health/audit/push | gates green, secrets absent, remote checkpoint visible | passing |

Fail-first order: business scenarios/profile facts → budget state machine/API label → implementation →
authorized profile-version journey → full regression/Docker/Git. Synthetic fixtures prove the contract,
not real-market precision; the ≥50 human-labeled pilot gate remains separate below.

Fail-first evidence 16.08.2026: `.venv/bin/pytest tests/test_mvp21_profiles.py tests/test_matching.py -q`
reports `12 failed`. Failures independently expose the old contractor/budget/profile facts, missing `9061`
yard classification, absent stop phrases, absent typed amount blocker/UI label and guessed recommendation
for unknown amount. Existing unrelated tests still pass; production code was unchanged for this run.

Second fail-first evidence: after independent domain review, `7 failed` prove absence of the structured
`review_above_amount`, qualification gap/label, UI round-trip and bounds validation. Final focused suite:
`45 passed`. Full suite: `191 passed`, branch coverage `86.14%`; Ruff/format/strict mypy pass. Legal source
review used [ПП РФ №2571](https://government.ru/docs/all/138738/) as a manual-review trigger only; the
product does not claim a legal eligibility decision.

Local Docker evidence: authorized `PUT` created cleaning profile v2 with budget `500000..25000000`,
contractors enabled and threshold `1000000`; history returns v1/v2 and restart preserves v2. Rebuilt
services are healthy, dbt reports `PASS=54 WARN=0 ERROR=0`, and the immediate ЕИС cycle ingested 25
bounded records. Browser inspection at 1280/768/390 px shows all budget controls, readable help text and
the two-version history without clipping. The current 30-record queue yields 1 `review`, 29
`not_relevant` and 0 fabricated recommendations; real precision remains unclaimed.
Git checkpoint `99c9a18` was pushed to `origin/codex/ui-redesign`; a direct `git ls-remote` returned
`99c9a1833b12f465ac67cd9f97571edc73379b73` for that branch before the closing docs-only checkpoint.

## Закрытый пилот — evidence plan

### Agent-assisted 50-notice pre-evaluation — complete

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Live sample integrity | bounded data eval | official ЕИС RSS + PostgreSQL lineage | capture validator | ≥50 unique current notice versions from bounded request set; URL/version/raw SHA present | pass |
| Blindness/no leakage | process + artifact contract | separate collector/labeler outputs | timestamps + schema checks | labels frozen without matcher decision/score/reasons | pass |
| Honest expert labels | complete agent review | 50 public notice snapshots | rubric validation | every label has reason/confidence; unknown is explicit | pass |
| Reproducible metrics | unit + artifact eval | frozen labels + matcher snapshot | evaluator CLI/tests | confusion, precision, sample recall, abstention and geo safety | pass |
| Error mechanism | fail-first regression | prioritized FP/FN classes | focused tests before owner mutation | repeated defect fixed at owner or retained as explicit unknown | pass |
| Human handoff | review packet | disagreements + low-confidence cases | 10–15 record shortlist | user can approve/correct without reviewing all implementation | pass |
| Release coherence | full regression + Docker + docs + Git | local/Compose/GitHub | release commands | gates green; artifacts contain no secret/source bytes | pass |

`actionable precision ≥80%` remains a human pilot gate. Agent-assisted metrics are reported with the
prefix `provisional_agent_`; zero denominator is `unknown`, not 0% or 100%. `Recall` is scoped only to
the frozen 50-record capture and is not a claim about the complete ЕИС market.

Evidence 16.08.2026: two bounded captures produced 50 unique current records with verified lineage.
Blind labels are `44 not_relevant / 6 insufficient_evidence / 0 relevant`; current matcher is
`49 not_relevant / 1 review`. Metrics are `TN=44`, `TP=FP=FN=0`, abstention `12%`, matcher actionable
coverage `2%`, hard onsite geography false admissions `0`. Precision and recall are `null` because no
agent-positive denominator exists. Baseline rejected all 50; fail-first real-record regression moved
the exact cleaning phrase case to review. The generated packet contains 15 diverse records.
Full suite: `222 passed`, branch coverage `85.85%`; Ruff/format/strict mypy pass; dbt `54/54`; rebuilt
Compose is healthy. Artifact integrity/leakage/secret scans and both documentation audits pass.
Checkpoint `79f22e2a0fce39ce90a427b27d333994145ff625` is present in `origin/codex/ui-redesign`.

### Human-reviewed 15-record diagnostic — complete

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Document integrity | raw SHA + tracked bytes | supplied Markdown | byte/hash comparison | exact SHA `ac65fbdb…c45` | passing |
| Exact universe | contract eval | sample/report/blank packet | ID/order/URL/amount join | 15/15 rows map to exact record lineage | passing |
| Fail-loud parsing | negative unit tests | malformed Markdown | label/amount/ID/row mutations | every unverifiable mutation rejected | passing |
| Frozen comparison | typed eval | pre-existing predictions | hash/time/profile/version checks | snapshot predates import; no label leakage | passing |
| Honest scope | schema + docs audit | 15 prioritized rows | report fields/assertions | `eligible_for_full_pilot_gate=false` | passing |
| Reproducibility | tracked artifact test + CLI | local deterministic files | re-evaluate saved inputs | byte-equivalent typed report | passing |

Evidence 16.08.2026: user-supplied table contains 1 `relevant`, 14 `not_relevant`, 0 abstentions.
Existing matcher yields `TP=1`, `TN=14`, `FP=FN=0`, human label coverage `100%` and matcher actionable
coverage `1/15`. `shortlist_actionable_precision=1.0` and `shortlist_recall=1.0` apply only to these
15 selected records. The selection used agent/matcher priorities and does not satisfy the independent
≥50-notice human pilot gate; the report encodes that prohibition instead of relying on prose.

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Реальный company fit | Human-labeled eval | ≥1 реальная компания, ≥50 ЕИС notices | blind label → matcher comparison | actionable precision ≥80%; hard onsite geo false admission = 0 | blocked |
| Live freshness/reliability | Run ledger + raw lineage | защищённый pilot Docker | 14-дневный scheduled run audit | ≥95% циклов успешны; freshness ≤24 h; failure явный | planned |
| Извлечение без выдумывания | Human audit + citations | ≥30 размеченных notice versions | claims/coverage/citation comparison | 100% claims grounded; ≥90% `found` подтверждены; gaps = `unknown` | blocked |
| Полезный alert | Delivery/replay integration | выбранный pilot channel | new version → deliver → unchanged replay | доставка до следующего цикла, без дубля | blocked |
| Решение пользователя | Product outcome log | ≥10 real recommendations | `participate/reject/defer` journey | решение и причина восстанавливаются из versions/evidence | planned |
| Защита и recovery | Security/operations rehearsal | непубличный pilot contour | access review + backup/restore + restart/retry | доступ ограничен; PostgreSQL/MinIO восстановлены; failures видимы | planned |
| Выход в Production v1 | Stakeholder decision record | результаты всех pilot gates | product review | только `go`, `extend` с gap или `stop`; скрытых failed gates нет | planned |

Blocked rows требуют independent ≥50-notice пользовательскую разметку, документы компании,
решение о document scope и выбор канала alerts. 15-row diagnostic закрывает handoff,
но не подменяет эти gates.
`Recall` и полнота российского рынка не являются честной метрикой, пока не задана ограниченная вселенная
источника. Live-source/LLM проверки дополняют, но не заменяют сохранённую пилотную разметку.

## MVP 2.0 UX acceptance — complete

| Требование / риск | Evidence | Среда | Проверка | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| Раздельные рабочие задачи | Route/HTML contract | TestClient fixtures | `tests/test_api.py` | `/`, `/tenders`, `/analytics`, `/companies`, `/data` имеют один dominant purpose | pass |
| Понятная глобальная навигация | Semantic/static contract | templates + Browser | `tests/test_web_assets.py` + DOM inspection | реальный route nav, active state, profile context, skip-link | pass |
| Неперегруженный обзор | Browser measurement | Docker, 1280×720 | DOM metrics + screenshot | нет форм/длинных каталогов; высота не более 3 viewport | pass |
| Тендерный workflow | Integration + browser journey | seeded PostgreSQL | filters → detail → official href | очередь, rejected audit и evidence не потеряны | pass |
| Управление компаниями | Integration + browser journey | seeded + user profile | catalog → editor/new → version history | создание/редактирование разделены и сохраняют pipeline | pass |
| Аналитика и ingestion isolation | Route contract | TestClient fixtures | page content assertions | метрики и bounded ЕИС controls не смешаны с профилями | pass |
| Responsive/accessibility | Static + browser inspection | 390×844 viewport | overflow, landmarks, focus, labels | `scrollWidth == clientWidth`, действия доступны с клавиатуры | pass |
| Регрессия бизнеса | Full suite | local + Docker PostgreSQL | `make verify`, `make dbt-test` | прежние capability evals и data tests зелёные | pass |

Baseline evidence: текущая `/` имеет `6800 px` высоты при viewport `720 px`, `57` content blocks,
`5` форм и `8` h1/h2-задач. Техническая корректность не закрывает пользовательскую приёмку.
Fail-first evidence: выборочный запуск новых route/template/accessibility tests — `9 failed, 3 passed`;
сигнатуры ошибок подтверждают отсутствие focused routes/base layout, route-preserving profile switch и design tokens.
Stakeholder acceptance: пользователь принял новый интерфейс и MVP 2.0 16.08.2026.

## MVP 2.0 UX final evidence — 2026-08-15

- `160` tests pass; branch coverage `87.43%`; Ruff/format/strict mypy pass.
- dbt: `PASS=54 WARN=0 ERROR=0`; rebuilt Docker services are healthy.
- `git diff --check` passes before delivery; no schema migration or external dependency was added.
- Overview: `1095 px` at `1280×720`, `10` content blocks, `0` forms versus baseline
  `6800 px`, `57` blocks and `5` forms.
- Browser route audit covers overview, tenders, analytics, company catalog/editor/new, data and detail;
  every route has active navigation, skip-link, labels and no horizontal overflow.
- Mobile `390×844`: `scrollWidth == clientWidth == 390`; all five nav items fit within the viewport.
- Tender audit keeps rejected records collapsed with no AI action; detail retains official transition,
  requirements/deadlines, raw SHA, ingestion run, history and outcomes.

## MVP 2.0 capability evals — complete

- [x] Four seeded Russian profiles are distinct, editable and preserved by replayed bootstrap.
- [x] A fifth user profile can be created, versioned, listed after reseed and used by matching/alerts.
- [x] Moscow onsite automotive service rejects Kamchatka without contractor coverage.
- [x] Enabling contractor coverage changes the same record with traceable geography evidence.
- [x] Remote IT in Moscow can recommend a Vladivostok software tender without a false distance penalty.
- [x] Landscaping and cleaning profiles rank their Russian sector fixtures only in supported geography.
- [x] Unknown region is an explicit geography gap/blocker and never an assumed match.
- [x] Current product/API/analytics/alerts contain no TED/USAspending opportunities.
- [x] Russian UI supports guided create/edit, filters/sort, tender detail and official source navigation.
- [x] Requirements/deadlines, lineage, outcomes and new geography/deadline/blocker analytics retain exact scopes.
- [x] All 15 goal E2E scenarios pass deterministic and browser verification, including Docker restart persistence.

## Capability evals

- [x] `IT Integrator` ranks a software/data notice above unrelated medical/construction fixtures and lists feature evidence.
- [x] `MedLab Supplier` ranks a medical/lab notice above unrelated IT/construction fixtures and lists feature evidence.
- [x] A changed source payload creates version 2 and preserves version 1; an identical replay is a no-op.
- [x] A canonically unchanged record inside a different raw response keeps the original immutable
  version/organization-link SHA while the new ingestion run retains its own raw evidence.
- [x] A recommendation can be reconstructed from profile version, record version, raw SHA and match evidence.
- [x] Missing deadline/amount/winner appears as `unknown`/gap and never as zero, epoch or inferred organization.
- [x] Live ЕИС RSS, manual ЕИС XML/ZIP and bounded TED/USA queries share the same canonical downstream contract.
- [x] GigaChat malformed output/unsupported citations fail validation and known transport failures remain visible.
- [x] Empty requirement/deadline categories carry explicit `found`/`not_present`/`unknown` coverage status.
- [x] A validated AI result is cached by record/input/prompt/model and reconstructable from stored hashes.
- [x] Buyer/supplier normalization is source-scoped, preserves aliases/raw/version links and backfills all
  existing SCD2 versions without guessing cross-source identity.
- [x] Award outcome projection exposes buyer, winner, amount/currency and raw evidence; partial or
  mixed-currency lots do not become a false total.
- [x] Opt-in webhook uses a stable idempotency key, retries only retryable failures and stores attempts
  without destination URL or response body.
- [x] Full company-profile input is normalized and versioned; invalid classification/country/budget
  states fail validation, changed versions alter ranking and create a version-specific alert snapshot.
- [x] Replaying bootstrap preserves the current user profile version instead of reactivating demo v1.
- [x] Tender pages project the latest current-record AI attempt with coverage, claims, gaps and
  citations; client updates use DOM text nodes and never inject source/LLM text through `innerHTML`.
- [x] Each new live cycle reads all current DB profile versions, persists versions/date/limit and fails
  before fetch on empty/duplicate profiles, foreign sources or an ЕИС limit above 50.
- [x] Default UI queue contains only `recommended`/`review`; rejected/expired records remain in a separate
  audit view and cannot trigger AI extraction.
- [x] Current validated AI evidence replaces the extraction action with an explicit coverage/result state.
- [x] Global route navigation has a semantic active state and keeps the selected company context.
- [x] Typed product analytics exposes exact current notice, SCD2 history and award outcome scopes through
  both API and `/analytics`; missing fields remain visible in coverage denominators.
- [x] Four demo profiles produce distinct actionable/rejected queues end-to-end, and every card exposes
  an internal detail, official transition and raw SHA/run/source timeline.

## Regression gates

- [x] pytest unit/contract suite with branch coverage ≥80%.
- [x] PostgreSQL integration proves migrations, one-current constraint and live replay idempotency.
- [x] dbt source/not-null/unique/relationships/accepted-values tests pass for all marts.
- [x] Ruff formatting/lint and strict mypy pass.
- [x] Docker Compose config and container health checks pass.
- [x] Server-rendered focused pages, API product flows and static DOM-safety contracts pass integration tests.
- [x] Live TED/ЕИС/USA/GigaChat smokes are bounded and record no secret values; ЕИС replay preserves one
  canonical version while recording each run and raw hash.
- [x] In-app alert replay is idempotent and new record/profile versions produce distinct events.
- [x] Alembic `0004..0006`, legacy AI coverage migration, organization/outcome marts and 48 dbt data
  tests pass on Docker PostgreSQL.
- [x] dbt's default local port is contract-tested against the Docker Compose published port.
- [x] Runtime wiring reopens a DB session on every profile-provider call, so API/worker need no restart
  after a profile update.
- [x] MVP 2.0 final regression evidence is recorded after rebuilt Docker/dbt/browser/restart checks.

## MVP 2.0 final evidence — 2026-08-15

- `157 passed`; branch coverage `87.21%` against the `85%` release gate.
- Ruff lint/format and strict mypy pass through `make lint`.
- dbt reports `PASS=54 WARN=0 ERROR=0`; Docker services are healthy after rebuilt images.
- Browser E2E covers the four seeded sectors, rejected Kamchatka audit, remote Vladivostok IT,
  filters, company switching, tender detail, official ЕИС link, profile guidance and analytics.
- A user-created profile was changed through the UI to v2; Docker restart retained versions `[1, 2]`
  and its `recommended` furniture tender.
- Live-source and live-LLM calls remain opt-in; deterministic fixtures own the release decision.

## Verification commands

```bash
uv sync --all-extras --dev
make test
make lint
make dbt-test
docker compose config --quiet
make verify
LIVE_SOURCE_TESTS=1 uv run pytest -q -m live_source
LIVE_LLM_TESTS=1 uv run pytest -q -m live_llm
```

## Нефункциональные требования

- Default live ingestion limit: 25 ЕИС records/run; hard application/source limit: 50.
- Live ЕИС window: one RSS page and at most 31 days per run; response body limit: 2 MiB.
- External HTTP connect/read timeout: 10/30 seconds; retries only for idempotent reads and 429/5xx.
- No live external call in default CI and no TLS verification bypass in any environment.
- Raw object is committed before canonical row; canonical transaction rolls back on invalid state.
- Structured logs include correlation/run IDs and redact configured secret field names.
- No latency SLO is claimed before Docker measurements; UI must show job freshness and failure state.

## Test-first evidence protocol

For a behavioral change, commit order within the diff is conceptual: acceptance/eval → observed failure
signature → implementation → regression. `docs/STATE.md` records only fresh command evidence; documentation
alone cannot close a criterion. A source fixture is evidence of a parser contract, not proof that the live
source is available today.

<!-- immune-project-engineering:quality:start -->
## Карта acceptance и evidence

| Требование/риск | Тип evidence | Fixture/среда | Команда или inspection | Ожидаемый результат | Статус |
| --- | --- | --- | --- | --- | --- |
| UX-IA | contract + E2E | fixtures + Docker browser | route tests + screenshots | focused routes и отдельные company forms | pass |
| UX-A11Y | static + E2E | templates + 390/1280 viewport | semantic/focus/overflow checks | landmarks и controls без overflow | pass |
| UX-REG | regression + data | local + Docker PostgreSQL | `make verify`, `make dbt-test` | business/data gates не деградируют | pass |

## Портфель проверок

Выбраны business journeys, static semantics, route/API contracts, integration/regression, browser desktop
и mobile accessibility, Docker health/restart и dbt coherence. Security проверяет отсутствие новых
external inputs/dependencies и DOM text safety. Property/fuzz, concurrency и load не добавляют новой
уверенности для template/IA mutation; существующие domain suites покрывают их по своим рискам.
Live source/LLM smoke не запускается, потому что внешний contract не меняется.
<!-- immune-project-engineering:quality:end -->
