---
title: "ADR-004: Russian source and geography boundary"
type: decision
status: accepted
updated: 2026-08-15
---

# ADR-004: Russian source and geography boundary

## Context

MVP 1.0 mixed EIS, TED and USAspending records and represented geography as country codes. MVP 2.0
must recommend only Russian procurement and distinguish remote delivery from physical regional work.
Russian electronic platforms expose public cards, but a stable public procurement API/RSS/export contract
has not yet been demonstrated for an additional adapter.

## Decision

- ЕИС RSS plus bounded official XML/ZIP packages own the initial Russian ingestion contract.
- TED/USAspending adapters and existing immutable evidence remain in the repository/history, but are not
  called by MVP 2.0 live cycles and are excluded from current product/API/analytics/alert projections.
- Platform cards remain official outbound destinations. HTML scraping is not an adapter contract.
- A new source adapter requires an official endpoint/export, documented bounds, provenance fields,
  deterministic fixtures, TLS verification and a live opt-in smoke.
- Geography is a typed policy owned by the domain: ISO 3166-2 Russian regions, service mode,
  service regions, nationwide/travel and contractor coverage. Every recommendation exposes either
  geography evidence or an explicit gap/blocker.

## Consequences

- Russia-only is enforced by one projection/source policy instead of hiding foreign rows in templates.
- Local physical work can fail geography even when country matches, while remote work can remain relevant.
- Historical evidence is preserved without claiming it belongs to the current Russian product.
- Coverage starts narrower than all Russian ETPs, but every included fact remains lawful, bounded and explainable.
