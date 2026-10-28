---
id: CS350-L04
course: CS350
title: "Online Migrations and the Database Incident Studio"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS350-L03
next: null
---


# CS350 — Advanced PostgreSQL Engineering
## Lecture 04: Online Migrations and the Database Incident Studio

*A logically correct migration becomes an incident: locks, WAL, backfills, and a rollback that no longer matches the schema.*

---

### Status — Planning Stub

**Pedagogical model:** migration forensics + multi-incident studio. Ties to SE340 delivery and `RELEASE-01` / `CICD-01` cases without duplicating SE340 theory.

### Learning Objective

Plan and diagnose expensive migrations, batched updates, index creation, lock contention, backfills, and replication implications — including when rollback is unsafe.

### Studio themes

- Expensive `ALTER` / index build under traffic
- Batched backfill that fights vacuum/WAL
- App deploy vs schema order (`RELEASE-01`)
- Re-measure after “obvious” fixes that worsen write amplification

### Lab contract

Diagnosis before solution; include at least one wrong-looking “easy fix.”

### Cross-references

SE340-L04; CS350-L01–L03; SE325 (bulk ops); production cases `PG-*`, `RELEASE-01`.

<!-- Full manuscript to be generated later. -->
