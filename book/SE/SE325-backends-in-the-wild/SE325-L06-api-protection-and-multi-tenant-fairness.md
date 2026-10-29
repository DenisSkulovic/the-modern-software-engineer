---
id: SE325-L06
course: SE325
title: "API Protection and Multi-Tenant Fairness"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE325-L05
next: null
---



# SE325 — Backends in the Wild: Production Field Guide
## Lecture 06: API Protection and Multi-Tenant Fairness

*One tenant launches an expensive analytics export. Per-IP rate limits look fine. The database pool is not. Critical booking APIs degrade for everyone while the “fair” limiter reports success.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** production field-guide elective. Target spoken duration ordinarily 25–35 minutes, plus optional lab and a course-level **production incident studio** (capstone exercise, not a seventh catalogue lecture). Complements CS430-L03 overload theory with an API-product / multi-tenant fairness lens. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, course-completion transition; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Distinguish request rate limits, concurrency limits, expensive-query budgets, tenant quotas, and emergency load shedding — and design controls that protect critical paths from noisy neighbors.

### Opening Problem

A multitenant hotel platform offers a “download all reservations” endpoint. One customer hammers it. Average latency rises. Redis is healthy. Connection pools are not. Should the API return `429` or `503`? Which work should be shed first?

### Planned Coverage

Request and concurrency limits; per-customer quotas; expensive-endpoint budgets; bulkhead isolation; noisy neighbors; load shedding versus rate limiting; cost allocation; graceful degradation; emergency controls / kill switches; `429` versus `503` semantics.

### Scope Boundaries

- CS430-L03 keeps capacity, pools, and overload fundamentals — add cross-references rather than regenerating that lecture.
- SE310 owns authn/authz; this lecture owns resource governance after identity is established.

### Expected Understanding

Propose a layered protection scheme for interactive vs bulk work, and defend containment choices in a senior interview.

### Suggested Exercise / Lab — Production Incident Studio (course capstone)

After finishing L01–L06 listening, run this interview-style investigation (lab worksheet, not a separate lecture ID):

A multitenant application suffers elevated latency after a release. Redis looks healthy. The database connection pool is exhausted. A background export started ten minutes earlier. A scheduled cleanup job is also running. One tenant generated most of the workload.

Reconstruct the failure, rank hypotheses, propose immediate containment, identify the underlying defect, and plan a safe fix — connecting SE320, CS430, SE440, and this elective.

### Planned Manuscript Structure

1. Narrative hook and sustained engineering case study.
2. Technical development of the underlying mechanisms.
3. Practical trade-offs and realistic failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Course-completion transition (point to incident studio lab).
8. Optional Practical Lab + Production Incident Studio, after the spoken lecture ends.
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card, last, inside one fenced text block.

### Cross-references (for future authorship)

CS430-L03 (scaling/load), SE320-L01 (request path), SE325-L02 (bulk exports), SE440-L02 (incident response).

<!-- Full manuscript to be generated later. -->
