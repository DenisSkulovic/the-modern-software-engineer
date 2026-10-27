---
id: SE460-L03
course: SE460
title: "Queues, Concurrency, and Backpressure"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE460-L02
next: SE460-L04
---






# SE460 — Performance Engineering
## Lecture 03: Queues, Concurrency, and Backpressure

*Doubling the number of application instances makes a busy service slower rather than faster.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Explain why adding concurrency can reduce throughput or increase latency, and design controls protecting shared bottlenecks.

### Opening Problem

Doubling the number of application instances makes a busy service slower rather than faster.

### Planned Coverage

Queueing effects, utilization and saturation, Little's Law in practice, concurrency limits, thread pools, connection pools, queue growth, backpressure, overload, retry amplification, and admission control.

### Scope Boundaries

CS430 teaches distributed scaling; this lecture centers on quantitative diagnosis and performance interventions.

### Expected Understanding

Apply Little's Law to a saturated service; design concurrency limits and backpressure; spot retry amplification.

### Planned Manuscript Structure

1. Narrative hook and sustained engineering case study.
2. Technical development of the underlying mechanisms.
3. Practical trade-offs and realistic failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture or course-completion transition.
8. Optional Practical Lab, after the spoken lecture ends.
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card, last, inside one fenced text block.

<!-- Full manuscript to be generated later. -->

