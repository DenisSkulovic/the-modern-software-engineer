---
id: CS345-L04
course: CS345
title: "The MongoDB Performance Incident Studio"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS345-L03
next: null
---


# CS345 — MongoDB Production Query Engineering
## Lecture 04: The MongoDB Performance Incident Studio

*Three deliberately bad production queries. Plans, symptoms, competing fixes — including “fixes” that make writes worse.*

---

### Status — Planning Stub

**Pedagogical model:** predominantly hands-on studio. Short briefing, then multi-incident lab. Interview Lab may reuse these scenarios.

### Learning Objective

Diagnose, remediate, and verify MongoDB performance incidents end-to-end — and reject naive fixes when evidence says they trade one failure for another.

### Studio scenarios (minimum three)

1. Deep offset pagination after `$lookup` + computed sort (opening CS345 case).
2. `$lookup` / history growth making an endpoint progressively slower.
3. `$facet` (or similar) forcing expensive exact counts / dual work for “total + page.”

For each: hypothesis → evidence → mechanism → change → verification. Include at least one case where adding an index helps reads but hurts write path enough to matter.

### Scope Boundaries

Not a MongoDB beginner course. Not SE460 cross-layer performance theory — database-specific investigation.

### Cross-references

CS345-L01–L03; `book/production-cases/`; Interview Lab protocol.

<!-- Full manuscript to be generated later. -->
