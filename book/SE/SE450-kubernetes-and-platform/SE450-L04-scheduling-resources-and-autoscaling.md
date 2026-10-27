---
id: SE450-L04
course: SE450
title: "Scheduling, Resources, and Autoscaling"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE450-L03
next: SE450-L05
---






# SE450 — Kubernetes and Platform Engineering
## Lecture 04: Scheduling, Resources, and Autoscaling

*A cluster reports spare overall CPU capacity, yet several pods remain Pending while others suffer CPU throttling.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Explain why available cluster resources do not automatically imply schedulable capacity or healthy performance.

### Opening Problem

A cluster reports spare overall CPU capacity, yet several pods remain Pending while others suffer CPU throttling.

### Planned Coverage

Resource requests and limits, scheduler placement, node constraints, taints and tolerations, affinity, topology spread, QoS, eviction, Horizontal Pod Autoscaler, node autoscaling, and capacity planning.

### Scope Boundaries

Operating-system resource mechanics belong to CS320; this lecture explains Kubernetes policy and control loops.

### Expected Understanding

Diagnose Pending vs throttling; reason about requests/limits, QoS, and autoscaling feedback loops.

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

