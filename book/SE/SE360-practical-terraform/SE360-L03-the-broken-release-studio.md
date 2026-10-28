---
id: SE360-L03
course: SE360
title: "The Broken Release Studio"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE360-L02
next: null
---


# SE360 — Practical Terraform and Cloud Delivery
## Lecture 03: The Broken Release Studio

*Pipeline green. Wrong artifact, bad credentials, or schema already migrated — rollback makes it worse.*

---

### Status — Planning Stub

**Pedagogical model:** end-to-end release incident studio. Ties CI/CD + infra + app compatibility.

### Learning Objective

Diagnose releases that build correctly but deploy incompatible apps, misuse credentials, promote the wrong artifact, or break rollback because schema moved first.

### Studio scenarios

- `CICD-01` wrong artifact / tag / cache
- Credential or environment mix-up
- `RELEASE-01` app rollback after forward-only migration

### Lab contract

Evidence trail from pipeline logs → artifact identity → runtime version → schema compatibility. Containment before cleverness.

### Cross-references

SE360-L01/L02; SE340-L04; CS350-L04; production cases `CICD-01`, `RELEASE-01`.

<!-- Full manuscript to be generated later. -->
