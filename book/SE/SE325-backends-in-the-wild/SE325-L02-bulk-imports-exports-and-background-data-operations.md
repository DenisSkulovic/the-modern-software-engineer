---
id: SE325-L02
course: SE325
title: "Bulk Imports, Exports, and Background Data Operations"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE325-L01
next: SE325-L03
---



# SE325 — Backends in the Wild: Production Field Guide
## Lecture 02: Bulk Imports, Exports, and Background Data Operations

*One customer starts a property-catalogue export. Ten minutes later the shared database pool is exhausted, interactive booking APIs stall, and nobody can say whether the export is 12% or 87% complete.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** production field-guide elective. Target spoken duration ordinarily 25–35 minutes, plus optional lab. Builds on SE320-L03 queues without repeating retry/DLQ fundamentals. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Design resumable, resource-aware bulk import/export and backfill workflows that survive partial failure, cancellation, and multitenant contention.

### Opening Problem

Operations uploads a million-row CSV of hotel rates. Row 412,883 fails validation. Should the job abort, skip, or quarantine? Can it resume after a worker crash without duplicating earlier rows? Meanwhile an export for another tenant is reading the same hot tables.

### Planned Coverage

CSV/JSON at scale; streaming; resumability; checkpoints; partial success; per-row validation; job progress; cancellation; backfills; memory and connection limits; noisy-neighbor exports; reporting progress without lying.

### Scope Boundaries

- Queue, retry, and DLQ fundamentals remain in SE320-L03 — cite them; do not reteach.
- Query planning depth stays in CS330; this lecture owns operational bulk-job design.

### Expected Understanding

Sketch a checkpointed import/export pipeline, reason about partial success and cancellation, and protect interactive traffic from bulk work.

### Suggested Exercise / Lab

Design a resumable rate-import job with per-row failure quarantine and explicit progress semantics.

### Planned Manuscript Structure

1. Narrative hook and sustained engineering case study.
2. Technical development of the underlying mechanisms.
3. Practical trade-offs and realistic failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture hook.
8. Optional Practical Lab, after the spoken lecture ends.
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card, last, inside one fenced text block.

### Cross-references (for future authorship)

SE320-L03 (workers/queues), CS330 (query/transaction cost), CS430-L03 (overload), SE325-L06 (tenant fairness).

<!-- Full manuscript to be generated later. -->
