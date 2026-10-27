---
id: SE450-L03
course: SE450
title: "Cluster Networking and Service Discovery"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE450-L02
next: SE450-L04
---






# SE450 — Kubernetes and Platform Engineering
## Lecture 03: Cluster Networking and Service Discovery

*Two pods can reach the internet but cannot communicate with a service inside the same cluster.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

### Learning Objective

Trace an application request through Kubernetes networking and distinguish DNS, routing, policy, and application failures.

### Opening Problem

Two pods can reach the internet but cannot communicate with a service inside the same cluster.

### Planned Coverage

Pod addressing, CNI fundamentals, Services, EndpointSlices, cluster DNS, kube-proxy or equivalent service-routing implementations, load balancing, Ingress and Gateway API, egress routing, and NetworkPolicy.

### Scope Boundaries

Builds on CS230 instead of reteaching TCP, TLS, DNS, or routing from scratch.

### Expected Understanding

Trace pod-to-service traffic; separate DNS, CNI, Service, and NetworkPolicy failure modes.

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

