---
id: SE360-L01
course: SE360
title: "CI/CD in the Real World: Jenkins, GitHub Actions, and GitLab CI"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE360-L02
---


# SE360 — Practical Terraform and Cloud Delivery
## Lecture 01: CI/CD in the Real World: Jenkins, GitHub Actions, and GitLab CI

*Green build, wrong artifact. Controllers, agents, workspaces, credentials, and what “deployed” actually meant.*

---

### Status — Planning Stub

**Pedagogical model:** pipeline literacy studio. Complements SE340-L04; adds Jenkins/Actions/GitLab investigation depth without plugin tourism.

### Learning Objective

Explain pipeline architecture (controller vs agent/runner, stages, workspaces, credentials, caching, artifacts, gates) well enough to investigate “works locally, fails in CI” and successful-but-wrong deploys.

### Opening Problem

`CICD-01`: Jenkins (or peer) reports successful deployment; production runs an unexpected application version.

### Planned Coverage

Declarative pipeline model; agents/runners; workspaces; credentials; caching; artifacts; triggers; approval gates; shared libraries (recognition-level); mapping the same ideas across Jenkins / GitHub Actions / GitLab CI.

### Scope Boundaries

SE340 owns progressive delivery and IaC concepts at programme level. This lecture owns practical pipeline forensics. Not every Jenkins plugin.

### Lab contract

Trace artifact provenance from commit → build → deploy target; find the mismatch.

### Cross-references

SE340-L04; SE215-L06; `CICD-01`.

<!-- Full manuscript to be generated later. -->
