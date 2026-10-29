---
id: SE325-L03
course: SE325
title: "Scheduled Jobs, Time, and Distributed Execution"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE325-L02
next: SE325-L04
---



# SE325 — Backends in the Wild: Production Field Guide
## Lecture 03: Scheduled Jobs, Time, and Distributed Execution

*A nightly billing job worked for months — until a failover launched it twice, a DST boundary shifted “midnight,” and a lost completion acknowledgment left finance wondering whether invoices had already been sent.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** production field-guide elective. Target spoken duration ordinarily 25–35 minutes, plus optional lab. Complements SE320-L03 async workers; focuses on periodic scheduling failure modes Google SRE-style distributed cron problems expose. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Reason about distributed periodic work: missed runs, duplicate launches, leases, catch-up policy, calendar-time semantics, and idempotent business effects.

### Opening Problem

A daily “settle unpaid invoices at midnight” job runs in a multi-replica scheduler. At failover, two replicas believe they own the run. Separately, the scheduler was down at midnight — should it catch up at 03:17? What does “midnight” mean across DST?

### Planned Coverage

Cron and calendar semantics; DST and timezone changes; missed executions; duplicate launches; distributed scheduling; job leases / leader election; idempotency of scheduled side effects; catch-up policies; long-running scheduled work overlapping the next window; completion acknowledgment loss.

### Scope Boundaries

- Do not repeat SE320-L03 queue fundamentals or CS430-L05 payment-state machines — link for durable business effects.
- This lecture owns *when* work runs and *who* may run it, not the full payment workflow.

### Expected Understanding

Design a scheduled job that is safe under failover, clock weirdness, and delayed catch-up — and explain which business effects must be idempotent.

### Suggested Exercise / Lab

Specify lease + catch-up policy for a daily billing job across two scheduler replicas and a DST transition.

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

SE320-L03 (async execution), CS430-L01 (partial failure / idempotency), CS430-L05 (durable business workflows).

<!-- Full manuscript to be generated later. -->
