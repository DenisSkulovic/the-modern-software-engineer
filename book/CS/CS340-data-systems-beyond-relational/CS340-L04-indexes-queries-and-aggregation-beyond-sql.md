---
id: CS340-L04
course: CS340
title: "Indexes, Queries, and Aggregation Beyond SQL"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS340-L03
next: CS340-L05
---




# CS340 — Data Systems Beyond Relational Databases
## Lecture 04: Indexes, Queries, and Aggregation Beyond SQL

*How modern databases organize information, choose their trade-offs, and behave when real applications put them under pressure.*

**Estimated study time:** TBD once the spoken manuscript exists (target roughly 60–90 minutes including lab).

---

### Status — stub outline

This file is a writing scaffold. Full voice-first manuscript still to be authored.

**Learning objective:** Compound and multikey indexes, query planning, aggregation pipelines, query selectivity, and diagnosing unexpectedly expensive queries.

**Complements:** CS330 (relational modeling, SQL performance, transactions). This course covers other data models, storage-engine trade-offs, and specialized systems — not a MongoDB certification track.

**Voice-first target when written:** spoken narrative first; diagrams and dense samples as screen aids with spoken captions; oral examination; mental model; optional lab only after *The spoken lecture ends here…*

### Planned spoken path

1. Hook — the aggregation that worked in staging and timed out in production
2. Indexes as access paths — equality, ranges, compound key order
3. Multikey / array indexes and their cardinality surprises
4. Query planners — what 'using an index' does and does not promise
5. Selectivity, covered queries, and collection scans that look innocent
6. Aggregation pipelines — stages, memory limits, and early filtering
7. Reading explain plans without drowning in operator names
8. Diagnosing expensive queries — evidence before adding another index
9. Oral examination · Mental model · Next lecture · Optional lab

<!-- Expand into full manuscript below; delete this stub scaffold when the lecture lands. -->
