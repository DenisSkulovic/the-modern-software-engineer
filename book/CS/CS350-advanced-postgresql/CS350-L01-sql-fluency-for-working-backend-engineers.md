---
id: CS350-L01
course: CS350
title: "SQL Fluency for Working Backend Engineers"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: CS350-L02
---


# CS350 — Advanced PostgreSQL Engineering
## Lecture 01: SQL Fluency for Working Backend Engineers

*Not `SELECT * FROM users`. Write the revenue ranking query unaided — then defend joins, filters, and edge cases.*

---

### Status — Planning Stub

**Pedagogical model:** fluency-first studio. Spoken framing ~15–25 min; heavy unaided writing lab. Prerequisite conceptual CS330; this closes the vibecode gap.

### Learning Objective

Independently write and validate joins, aggregations, CTEs, window functions, conditional aggregates, updates, and pagination queries for realistic booking-domain questions.

### Opening Problem

“Find the five customers with the greatest confirmed booking revenue over the last ninety days, excluding refunded bookings, including customers with no activity where appropriate.” No ORM. No AI until after the first attempt.

### Planned Coverage

Joins; `GROUP BY` / `HAVING`; CTEs; window functions; `FILTER` / conditional aggregates; upserts and careful updates; keyset vs offset pagination in SQL; null/edge-case discipline; comparing alternative formulations.

### Scope Boundaries

CS330 owns relational theory and isolation concepts. L01 establishes hand SQL before L02 throws plans. Do not start with vacuum/bloat.

### Lab contract

Write → explain → compare alternatives → validate results → then AI review.

### Cross-references

CS330-L01/L02; later `PG-01`.

<!-- Full manuscript to be generated later. -->
