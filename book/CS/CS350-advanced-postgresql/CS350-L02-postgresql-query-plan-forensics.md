---
id: CS350-L02
course: CS350
title: "PostgreSQL Query Plan Forensics"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS350-L01
next: CS350-L03
---


# CS350 — Advanced PostgreSQL Engineering
## Lecture 02: PostgreSQL Query Plan Forensics

*`EXPLAIN (ANALYZE, BUFFERS)`: estimates lie, `loops` multiply, and an index can still lose to a sequential scan for good reasons.*

---

### Status — Planning Stub

**Pedagogical model:** spoken plan literacy + lab on ORM-ish and hand SQL. Requires L01 fluency.

### Learning Objective

Interpret actual plans: estimates vs actual rows, join types, `loops`, buffer activity, sorts, index use, and expensive generated SQL.

### Opening Problem

Case `PG-01`: a query uses an index but is still slower than a sequential scan — until you read the plan correctly.

### Planned Coverage

`EXPLAIN` / `ANALYZE` / `BUFFERS`; nested loop / hash / merge; rows × loops; work_mem and sorts; index-only / bitmap; parameter sniffing / plan stability (light); spotting ORM N+1 and bad predicates in plans.

### Scope Boundaries

MVCC physical consequences deepen in L03. SE460 owns cross-service latency; this is Postgres-specific.

### Lab contract

Hypothesis → plan evidence → mechanism → change → re-measure.

### Cross-references

CS330-L02; CS350-L01; `PG-01`.

<!-- Full manuscript to be generated later. -->
