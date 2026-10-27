---
id: CS320-L06
course: CS320
title: "From System Calls to Asynchronous I/O"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS320-L05
next: CS320-L07
---




# CS320 — Operating Systems, Concurrency, and Runtimes
## Lecture 06: From System Calls to Asynchronous I/O

*Why a Node.js server that handles thousands of connections on one thread can suffer severe latency spikes from one seemingly harmless file operation.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Explain how event-driven servers interact with the kernel and why asynchronous APIs don't all rely on the same low-level execution mechanism.

### Opening Problem

A Node.js server handles thousands of connections on one main JavaScript thread, yet introducing one seemingly harmless file operation causes severe latency spikes.

### Planned Coverage

File descriptors, sockets, pipes, blocking and nonblocking I/O, readiness versus completion models, select/poll, epoll, kqueue, IOCP, io_uring as a modern Linux interface, libuv, and the distinction between operating-system I/O and application scheduling.

### Scope Boundaries

CS230 teaches network protocols. CS320-L06 teaches how the runtime and kernel manage I/O operations.

### Expected Understanding

Trace an async API call to kernel I/O mechanisms; distinguish readiness from completion models; explain why some 'async' work still blocks the event loop.

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

