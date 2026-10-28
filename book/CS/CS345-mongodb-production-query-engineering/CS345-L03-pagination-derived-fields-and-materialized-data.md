---
id: CS345-L03
course: CS345
title: "Pagination, Derived Fields, and Materialized Data"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS345-L02
next: CS345-L04
---


# CS345 — MongoDB Production Query Engineering
## Lecture 03: Pagination, Derived Fields, and Materialized Data

*Storing the derived score as a field fixed the aggregation headache — and created a synchronization problem the next release had to own.*

---

### Status — Planning Stub

**Pedagogical model:** spoken trade-off case + lab comparing offset vs cursor pagination and live computation vs maintained fields.

### Learning Objective

Choose offset vs cursor pagination deliberately; decide when to denormalize or materialize derived values; design sync/backfill strategies and prove they stay correct when inputs change.

### Opening Problem

Computing `score` after `$lookup` prevents useful indexed ordering. Precomputing `score` makes deep pages fast — until stats change and the stored field lies.

### Planned Coverage

Offset vs cursor pagination; indexed ordering; expensive computed sorts; denormalization; on-demand materialized views / precomputed summaries; invalidation and sync; backfills; `$facet` total-count traps; correctness vs latency trade-offs.

### Scope Boundaries

SE325 owns bulk import/export ops; this lecture owns query-path materialization for read models. CS340 theory stays cited, not regenerated.

### Lab contract

Implement/compare: compute-on-read pipeline vs maintained field + index; break sync on purpose; verify with plans and assertions.

### Cross-references

CS345-L02; CS340; SE325-L02 (bulk/backfill adjacent); `MONGO-01`.

<!-- Full manuscript to be generated later. -->
