---
id: CS320-L07
course: CS320
title: "Threads, Atomics, and Memory Ordering"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS320-L06
next: CS320-L08
---




# CS320 — Operating Systems, Concurrency, and Runtimes
## Lecture 07: Threads, Atomics, and Memory Ordering

*Why two threads updating shared state with code that looks logically correct can still observe inconsistent results across processors.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Understand why code order isn't necessarily sufficient to reason about shared-memory correctness and when synchronization establishes the necessary guarantees.

### Opening Problem

Two threads update shared state using code that appears logically correct, yet different processors observe inconsistent results.

### Planned Coverage

Shared memory, data races, atomic operations, synchronization, happens-before relationships, memory visibility, mutexes, contention, deadlocks, lock-free intuition, and why compiler/CPU reordering complicates concurrency.

### Scope Boundaries

L01 teaches concurrency as an application concept. L07 examines lower-level shared-memory correctness. Keep the discussion conceptual rather than turning the course into C++ concurrency specialization.

### Expected Understanding

Explain data races versus synchronization; describe happens-before and visibility; recognize when reordering makes 'correct-looking' shared-memory code unsafe.

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

