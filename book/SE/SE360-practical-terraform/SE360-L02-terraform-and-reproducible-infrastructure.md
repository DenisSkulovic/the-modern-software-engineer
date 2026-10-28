---
id: SE360-L02
course: SE360
title: "Terraform and Reproducible Infrastructure"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE360-L01
next: SE360-L03
---


# SE360 — Practical Terraform and Cloud Delivery
## Lecture 02: Terraform and Reproducible Infrastructure

*The plan looks harmless. State, drift, and a dependency you didn’t see promote the wrong reality.*

---

### Status — Planning Stub

**Pedagogical model:** Terraform operations studio. Builds on SE340 IaC introduction.

### Learning Objective

Operate plans, state, remote backends, drift, dependencies, environments, and secrets carefully enough to diagnose unsafe applies and environment skew.

### Opening Problem

Infrastructure “matches code” in one environment and silently drifts in another; or an apply changes a dependency the app release assumed was stable.

### Planned Coverage

Plan/apply; state and locking; remote backends; drift; module/dependency graphs; workspaces/environments; secrets handling; blast radius of seemingly small changes.

### Scope Boundaries

Do not move all of SE340-L04 Terraform content here — deepen investigation. Kubernetes GitOps stays SE450.

### Lab contract

Reproduce drift or unsafe plan → diagnose → remediate → verify state.

### Cross-references

SE340-L04; SE360-L01; SE360-L03.

<!-- Full manuscript to be generated later. -->
