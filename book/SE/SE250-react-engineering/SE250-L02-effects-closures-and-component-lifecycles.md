---
id: SE250-L02
course: SE250
title: "Effects, Closures, and Component Lifecycles"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L01
next: SE250-L03
---


# SE250 — React Engineering for Experienced Developers
## Lecture 02: Effects, Closures, and Component Lifecycles

*Switching hotel pages sometimes shows yesterday’s prices. The fetch “worked.” The Effect “ran.” The closure remembered the wrong render — and Strict Mode made the bug louder in development.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** 25–35 minutes spoken + prediction/debug lab. Builds on L01’s snapshot model. `useEffect` is not Vue `watch`.

### Learning Objective

Decide when an Effect is appropriate, reason about stale closures and dependency arrays, use refs correctly, and diagnose request races, cleanup bugs, and Strict Mode double-invocation without treating Effects as a lifecycle dumping ground.

### Opening Problem

Navigating between hotel detail pages occasionally displays stale prices. Effects fire; responses return out of order; captured IDs belong to earlier renders. A vibecoded `useEffect` that “loads data on mount” is the wrong abstraction — and the bug looks random until you understand closures and cleanup.

### Planned Coverage

`useEffect` purpose (sync with external systems); cleanup; stale closures; dependency rules; Rules of Hooks; `useRef`; timers; subscriptions; async requests and races; infinite loops; unnecessary Effects; event-handler vs Effect placement; Strict Mode development checks.

### Scope Boundaries

- Do not reteach L01 rendering/snapshots — apply them.
- Server Components / SSR wait for L05.
- Data-fetching libraries (TanStack Query) introduced properly in L03; here focus on why raw Effects fail.

### Expected Understanding

Trace a stale-price bug to captured values and timing; fix with correct dependencies, cleanup/abort, or by moving logic out of Effects when appropriate.

### Suggested Exercise / Lab

Hotel-page switcher with stale prices: predict → reproduce → fix → verify → then AI review.  
Secondary: timer/subscription leak without cleanup.

### Critical exercise rule

Prediction → Investigation → Correction → AI review. No premature spoilers.

### Planned Manuscript Structure

1. Narrative hook and case study.
2. Technical development.
3. Trade-offs and failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture hook.
8. Optional Practical Lab.
9. Further Reading.
10. Dense Cheatsheet.

### Cross-references

SE250-L01; SE240-L03 (async/state races in general); SE240-L06 (testing races).

<!-- Full manuscript to be generated later. -->
