---
id: SE335-L02
course: SE335
title: "RabbitMQ and Worker Failure Forensics"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE335-L01
next: SE335-L03
---


# SE335 — Queues, Caches, and Worker Production Diagnostics
## Lecture 02: RabbitMQ and Worker Failure Forensics

*Adding consumers made it slower. Prefetch, nacks, and requeue loops can turn a poison message into an outage amplifier.*

---

### Status — Planning Stub

**Pedagogical model:** broker/worker forensics. SE320-L03 teaches BullMQ-centric concepts; this lecture trains RabbitMQ-class investigation without regenerating retry/idempotency theory.

### Learning Objective

Diagnose acknowledgments, `nack`/requeue loops, prefetch, stuck consumers, poison messages, DLQs, and throughput-vs-concurrency trade-offs on a realistic broker setup.

### Opening Problem

`QUEUE-01`: more consumers → worse latency/throughput; or a single poison message flaps forever via requeue.

### Planned Coverage

Ack semantics; prefetch limits; consumer concurrency; poison / DLQ paths; broker health signals; backpressure; destructive retry patterns; relating worker crashes to in-flight messages.

### Scope Boundaries

Do not rewrite SE320-L03. SE325 scheduling/bulk jobs stay separate. Cross-service pileups live in L03.

### Lab contract

Reproduce → diagnose → tune/fix → verify; challenge “just add concurrency.”

### Cross-references

SE320-L03; `QUEUE-01`; SE335-L03.

<!-- Full manuscript to be generated later. -->
