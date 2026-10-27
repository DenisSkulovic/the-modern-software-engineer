---
id: CS320-L05
course: CS320
title: "Virtual Memory, Paging, and Memory Pressure"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS320-L04
next: CS320-L06
---




# CS320 — Operating Systems, Concurrency, and Runtimes
## Lecture 05: Virtual Memory, Paging, and Memory Pressure

*Why a container can crash from memory exhaustion even though its JavaScript heap looks modest and the host reports free memory.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Interpret memory metrics and reason about memory pressure beyond simple heap allocation.

### Opening Problem

A container crashes from memory exhaustion even though its JavaScript heap appears modest and the host reports free memory.

### Planned Coverage

Virtual address spaces, page tables, TLBs, page faults, copy-on-write, memory mapping, heap versus resident memory, page cache, swapping, reclaim, cgroup memory accounting, and OOM behavior.

### Scope Boundaries

CS220 explains application objects, garbage collection, and memory leaks. This lecture focuses on operating-system memory machinery.

### Expected Understanding

Distinguish heap size from RSS and cgroup limits; explain page faults, reclaim, and OOM; diagnose memory pressure beyond application-level allocation.

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

