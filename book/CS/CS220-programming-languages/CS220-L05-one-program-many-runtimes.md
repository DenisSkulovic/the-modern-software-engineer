---
id: CS220-L05
course: CS220
title: "One Program, Many Runtimes"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS220-L04
next: null
---




# CS220 — Programming Languages, Memory, and Execution
## Lecture 05: One Program, Many Runtimes

*The same CPU-heavy booking calculation in Node.js, CPython, the JVM, Go, and native code — why wall time, concurrency, and failure modes diverge even when the algorithm is identical.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Compare major runtime and compilation strategies — interpreters, bytecode VMs, JIT and AOT compilation, garbage collection versus reference counting, GILs, threads, and schedulers — and explain how those choices change performance and concurrency for the same logical program.

### Opening Problem

A team ports a CPU-bound pricing routine from Node.js to Python “for data science,” then to Go “for parallelism,” and is surprised that none of the speedups or slowdowns match folklore. The algorithm is the same; the runtimes are not.

### Planned Coverage

JavaScript/V8 revisited briefly; CPython and the GIL; JVM bytecode and JIT; Go’s compilation model and goroutine scheduler at a conceptual level; native/AOT compilation; garbage collection versus reference counting; when threads help CPU work and when they do not. Prefer one sustained comparative experiment over separate language tutorials.

### Scope Boundaries

CS220-L02–L03 already cover memory and V8/CPU execution in depth for the JavaScript ecosystem. CS220-L04 covers type and ownership design. CS320 covers OS scheduling, virtual memory, and concurrency primitives. SE460 covers systematic performance engineering. This lecture builds comparative runtime literacy, not production fluency in four languages.

### Expected Understanding

Given a workload (CPU-bound, I/O-bound, mixed), predict which runtime constraints matter; explain why “add more threads” fails under a GIL; contrast bytecode+JIT with AOT/native trade-offs; name what to measure before blaming the language.

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
