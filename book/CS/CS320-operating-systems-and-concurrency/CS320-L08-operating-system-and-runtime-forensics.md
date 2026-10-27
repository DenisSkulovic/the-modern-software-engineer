---
id: CS320-L08
course: CS320
title: "Operating-System and Runtime Forensics"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS320-L07
next: null
---




# CS320 — Operating Systems, Concurrency, and Runtimes
## Lecture 08: Operating-System and Runtime Forensics

*A production backend shows intermittent latency, memory growth, disappearing workers, and exhausted file descriptors — and several plausible explanations compete.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Diagnose resource and runtime failures by forming hypotheses and selecting evidence, rather than blindly changing limits or restarting services.

### Opening Problem

A production backend experiences intermittent latency, memory growth, disappearing worker processes, and exhausted file descriptors. Several plausible explanations compete.

### Planned Coverage

Integrated investigations using process state, CPU profiles, scheduling metrics, RSS, page faults, open descriptors, socket state, blocking I/O, cgroup limits, and relevant Linux tools.

### Scope Boundaries

This is a capstone investigation, not another lecture introducing operating-system vocabulary.

### Expected Understanding

Form ranked hypotheses for a multi-symptom incident; choose evidence from OS/runtime tools; defend a diagnosis without cargo-cult restarts or limit bumps.

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

