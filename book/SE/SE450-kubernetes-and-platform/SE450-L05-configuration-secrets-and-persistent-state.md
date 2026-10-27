---
id: SE450-L05
course: SE450
title: "Configuration, Secrets, and Persistent State"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE450-L04
next: SE450-L06
---






# SE450 — Kubernetes and Platform Engineering
## Lecture 05: Configuration, Secrets, and Persistent State

*A stateful service works until its pod moves to a different node, where its data or configuration disappears.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Understand the distinction between a replaceable process and persistent application state.

### Opening Problem

A stateful service works until its pod moves to a different node, where its data or configuration disappears.

### Planned Coverage

ConfigMaps, Secrets, projected configuration, environment-variable risks, storage volumes, PVs, PVCs, StorageClasses, CSI, StatefulSet storage identity, backup and recovery concerns, and external stateful services.

### Scope Boundaries

Do not duplicate database durability material from CS330 or CS340.

### Expected Understanding

Explain what survives a pod move; choose ConfigMap/Secret/volume patterns; reason about PVC identity and external stateful dependencies.

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

