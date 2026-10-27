---
id: SE460-L02
course: SE460
title: "CPU, Memory, and Runtime Performance"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE460-L01
next: SE460-L03
---






# SE460 — Performance Engineering
## Lecture 02: CPU, Memory, and Runtime Performance

*A service becomes slow even though average CPU utilization appears low, and several micro-optimizations accomplish nothing.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Distinguish CPU-bound, allocation-bound, scheduling-related, and waiting-related performance problems.

### Opening Problem

A service becomes slow even though its average CPU utilization appears low, and several attempted micro-optimizations accomplish nothing.

### Planned Coverage

CPU time versus wall-clock time, per-core bottlenecks, profilers, flame graphs, allocation profiles, garbage-collection pressure, memory locality, blocking work, JIT warmup, and interpreting runtime metrics.

### Scope Boundaries

CS220/CS320 teach the underlying machinery. This lecture teaches how to measure and optimize it.

### Expected Understanding

Read a profiler/flame graph usefully; classify a slowdown as CPU, allocation, scheduling, or waiting.

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

