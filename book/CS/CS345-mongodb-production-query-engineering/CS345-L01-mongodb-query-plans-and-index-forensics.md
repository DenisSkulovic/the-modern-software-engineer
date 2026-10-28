---
id: CS345-L01
course: CS345
title: "MongoDB Query Plans and Index Forensics"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: CS345-L02
---


# CS345 — MongoDB Production Query Engineering
## Lecture 01: MongoDB Query Plans and Index Forensics

*The query returns the right twenty documents. `explain` shows why the database examined a small city’s worth of work to get them.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** diagnostic studio elective. Spoken case study ~15–25 minutes; production lab 30–60 minutes. Complements CS340 — does not regenerate document modeling or aggregation theory. Diagnosis before solution.

### Learning Objective

Read MongoDB `explain("executionStats")` with intent: docs/keys examined, index bounds, covered queries, compound indexes, and planner decisions that matter under load.

### Opening Problem

An admin list endpoint is “fine” on page 1 and catastrophic on deep pages — or even on page 1 when filters defeat indexes. Logs show correct results; latency and examined counts tell another story.

### Planned Coverage

Query shapes; `explain` / `executionStats`; `totalDocsExamined` vs `totalKeysExamined`; index bounds; covered queries; compound index order; planner choices; when an index exists but is not used.

### Scope Boundaries

CS340 owns modeling and aggregation concepts. This lecture owns plan literacy and index forensics with runnable evidence.

### Lab contract

Hypothesis → evidence → mechanism → change → verification. Hints only after a first attempt.

### Cross-references

CS340-L03/L04; production case `MONGO-01` / `MONGO-02`.

<!-- Full manuscript to be generated later. -->
