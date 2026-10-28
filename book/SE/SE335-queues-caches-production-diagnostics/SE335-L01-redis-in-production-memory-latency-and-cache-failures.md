---
id: SE335-L01
course: SE335
title: "Redis in Production: Memory, Latency, and Cache Failures"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE335-L02
---


# SE335 — Queues, Caches, and Worker Production Diagnostics
## Lecture 01: Redis in Production: Memory, Latency, and Cache Failures

*99% cache hit ratio — and the database is still on fire. Eviction, hot keys, and miss storms don’t care about your green dashboard.*

---

### Status — Planning Stub

**Pedagogical model:** diagnostic studio (~15–25 min spoken + lab). Deepens SE320-L02; does not reteach cache stampede theory from scratch.

### Learning Objective

Troubleshoot Redis memory, latency, eviction, expiration, hot keys, and consistency failures with evidence — including when “raise maxmemory” only delays the incident.

### Opening Problem

`REDIS-01`: high hit ratio coexists with serious DB overload (wrong keys, tiny TTLs, thundering herd, or bypass paths).

### Planned Coverage

Hot keys; eviction policies and value sizes; TTL patterns; miss storms; latency; connection behavior; cache consistency; diagnosing “Redis looks fine.”

### Scope Boundaries

SE320-L02 owns conceptual caching. SE325 owns bulk/API fairness. SE460 owns cross-layer measurement. This lecture owns Redis operational forensics.

### Lab contract

Hypothesis → evidence → mechanism → change → verify. Include a fix that appears to help but doesn’t.

### Cross-references

SE320-L02; `REDIS-01`; SE335-L03.

<!-- Full manuscript to be generated later. -->
