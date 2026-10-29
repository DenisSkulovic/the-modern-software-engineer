---
id: SE325-L05
course: SE325
title: "Surviving Third-Party Integrations"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE325-L04
next: SE325-L06
---



# SE325 — Backends in the Wild: Production Field Guide
## Lecture 05: Surviving Third-Party Integrations

*A channel-manager API starts returning a subtly different date format. The nightly synchronization still “succeeds.” By morning, occupancy reports are wrong for three markets and nobody got an alert.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** production field-guide elective. Target spoken duration ordinarily 25–35 minutes, plus optional lab. Preserves CS430-L01 retry/idempotency and CS430-L05 payment/webhook depth; owns ongoing vendor-integration maintenance. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Operate long-lived third-party integrations under drift, partial sync failure, ambiguous outcomes, quotas, and sandbox/production mismatch.

### Opening Problem

Your booking platform syncs inventory with an external partner. Tokens expire. Pagination changes. Rate limits appear mid-backfill. A webhook arrives twice, then late. Sandbox behavior never matched production. Finance notices corruption weeks later.

### Planned Coverage

Vendor API drift; OAuth / token refresh; quotas and `429` handling; paginated synchronization; webhooks and signatures; ambiguous failures; replay and backfills; sandbox differences; integration observability; partial synchronization and consumer-side reconciliation.

### Scope Boundaries

- CS430-L01 keeps timeout/retry/idempotency theory — link, don’t rewrite.
- CS430-L05 remains the primary payment and durable workflow lecture — avoid duplicating authorization/capture/reconciliation depth; generalize to non-payment vendors here.

### Expected Understanding

Diagnose silent sync corruption, design detection and replay, and explain how to live with a vendor you do not control.

### Suggested Exercise / Lab

Given a partner pagination change and a late duplicate webhook, propose detection, containment, and a safe backfill.

### Planned Manuscript Structure

1. Narrative hook and sustained engineering case study.
2. Technical development of the underlying mechanisms.
3. Practical trade-offs and realistic failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture hook.
8. Optional Practical Lab, after the spoken lecture ends.
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card, last, inside one fenced text block.

### Cross-references (for future authorship)

CS430-L01 (retries/idempotency), CS430-L05 (webhooks/payments), SE310-L01 (contracts), SE440-L01 (observability).

<!-- Full manuscript to be generated later. -->
