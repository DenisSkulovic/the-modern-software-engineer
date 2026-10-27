---
id: CS220-L04
course: CS220
title: "Type Systems, Ownership, and Language Design"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS220-L03
next: CS220-L05
---




# CS220 — Programming Languages, Memory, and Execution
## Lecture 04: Type Systems, Ownership, and Language Design

*Why TypeScript, Java, Go, Python, and Rust can all be “typed” and still make radically different promises about what a program is allowed to do.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Compare how languages encode correctness in their type systems and memory models — static versus dynamic typing, structural versus nominal types, inference, generics, mutability, ownership, and borrowing — and explain what each design can and cannot enforce at compile time.

### Opening Problem

Two services implement the same booking invariant. One relies on TypeScript interfaces and runtime validation; another is rewritten in a language with ownership rules. Both compile. Only one class of bugs becomes structurally impossible — and the team needs to know which, and why.

### Planned Coverage

Static and dynamic typing revisited comparatively; structural versus nominal typing; type inference; generics and parametric polymorphism; mutability and aliasing; ownership, borrowing, and lifetimes as a contrasting design; what compilers can prove versus what remains a runtime or protocol concern. Sustained cross-language comparison, not language tutorials.

### Scope Boundaries

CS220-L01 already covers TypeScript erasure, validation boundaries, and local type-system habits. This lecture widens the design space across languages. CS220-L05 covers runtimes, bytecode, GIL, and concurrency trade-offs. CS320 covers OS threads and scheduling in depth.

### Expected Understanding

State what a given language’s type or ownership model guarantees; name a bug class that model cannot catch; choose a language feature (nominal types, ownership, runtime checks) for a concrete invariant without treating any one language as universally superior.

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
