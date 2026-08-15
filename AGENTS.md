<!-- project-control:start -->
## Project continuity

- Before planning or editing, read `docs/README.md`, `docs/STATE.md`, and documents directly relevant to the task.
- Reconstruct current state from repository files, Git diff/status, and fresh verification; do not rely on chat history alone.
- Define acceptance criteria and non-goals before implementation.
- Work in independently verifiable checkpoints and update `docs/STATE.md` after each verified checkpoint or before handoff.
- Keep `docs/STATE.md` compact: one active objective and one exact next step.
- Do not mark work complete without recorded test, eval, or inspection evidence.
- Do not convert unfinished acceptance criteria into technical debt.
- Create new project documents only when the project-control contract defines a trigger.
<!-- project-control:end -->

## Engineering constitution: IMMUNE

These rules are acceptance constraints, not style preferences.

- **I — Intent before implementation.** Requirements outrank architecture; architecture outranks code. Record observable intent and tests before implementation.
- **M — Mutations preserve coherence.** A change is complete only when code, schema, API, documentation, tests, and data contracts tell the same story.
- **M — Meta over patch.** Fix the mechanism that produces a class of defects when the repeated-error evidence justifies it; do not build frameworks for isolated typos.
- **U — Unexpected states fail loud.** Preserve `unknown` explicitly. Invalid source data, unverifiable assumptions, and failed external calls must not become plausible defaults. Avoid broad exception handling.
- **N — No duplicated authority, no indispensable parts.** Every decision and fact has one owner. Other projections reference or are generated from it. Extend through new owners/adapters instead of editing unrelated ones.
- **E — Every state is explainable.** Important state must be reconstructable from raw artifacts, hashes, run metadata, version history, match evidence, and verification results.

## Delivery rules

- Write or update a failing test/eval before production code for every behavioral change.
- A failing required test or a missed business acceptance criterion is a release blocker.
- Live-source and live-LLM calls are opt-in smoke tests; deterministic fixtures own CI behavior.
- Never disable TLS verification. Keep `.env`, access tokens, and company-confidential data out of Git and logs.
- Keep source-specific parsing behind adapters. The canonical procurement model is the only authority for downstream analytics and matching.

<!-- immune-project-engineering:start -->
## IMMUNE engineering contract

- Treat `docs/IMMUNE.md` as the authority for engineering principles and precedence.
- Work in this order: verified business intent → architecture → tests/evals → implementation.
- Before editing, read `docs/README.md`, `docs/STATE.md`, `docs/AUDIT.md`, `docs/IMMUNE.md`, and the directly relevant owner documents.
- Change concepts coherently across requirements, code, schemas/data, APIs/events, config, Docker/operations, docs, tests/evals, migrations, security, and observability.
- Expose unexpected and unknown states; do not silently guess or hide failures behind broad exception handling.
- Keep one owner per truth. Keep this file concise and link to durable docs instead of copying product rules.
- Treat Docker and Git as product contracts. Keep the actual default branch releasable and preserve unrelated user changes.
- Update agent instructions when repository commands, layout, invariants, ownership, or verification gates change.
<!-- immune-project-engineering:end -->
