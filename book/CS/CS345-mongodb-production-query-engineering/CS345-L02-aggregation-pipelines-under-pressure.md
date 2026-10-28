---
id: CS345-L02
course: CS345
title: "Aggregation Pipelines Under Pressure"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS345-L01
next: CS345-L03
---


# CS345 — MongoDB Production Query Engineering
## Lecture 02: Aggregation Pipelines Under Pressure

*`$lookup` then compute then `$sort` then `$skip: 100000` then `$limit: 20` looks elegant in the API response and brutal in the execution engine.*

---

### Status — Planning Stub

**Pedagogical model:** spoken case ~15–25 min + measurable lab. Builds on L01 plan literacy.

### Learning Objective

Trace intermediate cardinality through `$match`, `$lookup`, `$unwind`, `$group`, `$facet`, sorts, and spilling — and inspect what the engine actually did, not what the pipeline text suggests.

### Opening Problem

A pipeline returns twenty customers for a deep page. The frontend sees efficiency. MongoDB may still evaluate a huge candidate set, especially when the sort key is computed after a `$lookup`.

### Planned Coverage

Stage semantics under load; early `$match`; `$lookup` / `$unwind` explosions; `$group` / `$facet` cost; sort + skip + limit behavior; stage reordering/optimizer surprises; memory limits and disk spill; reading stage-level stats.

### Scope Boundaries

Do not rewrite CS340-L04 prose — practice diagnosing with fixtures and plans. Materialized/denormalized fixes deepen in L03.

### Lab contract

Compare a bad pipeline vs an improved one with measured `executionStats` (e.g. synthetic ~200k docs). Diagnosis before the “store the score” redesign.

### Cross-references

CS340-L04; CS345-L01; `MONGO-01`, `MONGO-02`.

<!-- Full manuscript to be generated later. -->
