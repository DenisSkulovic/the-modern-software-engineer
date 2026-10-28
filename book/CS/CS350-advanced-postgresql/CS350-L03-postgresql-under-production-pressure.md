---
id: CS350-L03
course: CS350
title: "PostgreSQL Under Production Pressure"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS350-L02
next: CS350-L04
---


# CS350 — Advanced PostgreSQL Engineering
## Lecture 03: PostgreSQL Under Production Pressure

*Disk climbs after deleting millions of rows. Connections saturate. A long transaction quietly blocks vacuum.*

---

### Status — Planning Stub

**Pedagogical model:** operational diagnosis studio. Complements CS330 isolation theory with physical consequences.

### Learning Objective

Connect MVCC, autovacuum, dead tuples, bloat, WAL, long transactions, connection pressure, and locks to observable production symptoms.

### Opening Problem

`PG-02`: PostgreSQL disk usage climbs despite large deletes — or latency spikes correlate with vacuum/lock/connection pressure.

### Planned Coverage

MVCC visibility and dead tuples; autovacuum; table/index bloat; WAL growth drivers; long-running transactions; connection pools; lock diagnosis; “delete didn’t shrink the file” realities.

### Scope Boundaries

Migration studio is L04. SE325 data repair is adjacent, not duplicated.

### Lab contract

Reproduce a pressure symptom with fixtures → diagnose → remediate carefully → verify.

### Cross-references

CS330-L03; CS350-L02; `PG-02`.

<!-- Full manuscript to be generated later. -->
