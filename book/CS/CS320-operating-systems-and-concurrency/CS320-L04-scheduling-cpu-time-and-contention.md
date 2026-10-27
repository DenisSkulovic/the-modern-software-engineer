---
id: CS320-L04
course: CS320
title: "Scheduling, CPU Time, and Contention"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS320-L03
next: CS320-L05
---




# CS320 — Operating Systems, Concurrency, and Runtimes
## Lecture 04: Scheduling, CPU Time, and Contention

*Why a sixteen-core server with low average CPU usage can still leave one worker experiencing severe response delays.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Explain why a runnable task might not execute immediately and distinguish insufficient CPU capacity from contention, scheduling, or application-level blocking.

### Opening Problem

An application is running on a sixteen-core server and reports low average CPU usage, yet one worker experiences severe response delays.

### Planned Coverage

Process and thread states, scheduling queues, fairness, preemption, context switching, CPU affinity, CPU time versus wall-clock time, scheduler latency, CPU quotas and throttling, priority inversion, and the effects of oversubscription.

### Scope Boundaries

L02 introduces scheduling. L04 explains its deeper mechanics and performance consequences.

### Expected Understanding

Separate CPU capacity from contention and blocking; interpret scheduler-related symptoms; explain quotas, throttling, and oversubscription effects.

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

