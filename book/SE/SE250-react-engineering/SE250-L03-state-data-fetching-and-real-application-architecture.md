---
id: SE250-L03
course: SE250
title: "State, Data Fetching, and Real Application Architecture"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L02
next: SE250-L04
---


# SE250 — React Engineering for Experienced Developers
## Lecture 03: State, Data Fetching, and Real Application Architecture

*Local `useState`, a giant Context, and three ad-hoc fetches later, the booking form and the search results disagree about availability — and nobody owns the cache key.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** 25–35 minutes spoken + architecture/debug exercises. Assumes L01–L02 mental model.

### Learning Objective

Choose local vs shared vs server state deliberately; structure Context, reducers, and custom hooks without god-providers; use a data library (TanStack Query–class) for cache keys, invalidation, optimistic updates, and stale responses.

### Opening Problem

A production-like hotel SPA mixes UI state, server cache, and URL params without clear ownership. Availability flickers after a reservation. Context re-renders the world. A custom hook hides a race. Interviews ask you to defend boundaries — not list hook names.

### Planned Coverage

Local vs shared vs server state; Context pitfalls; reducers; custom hooks; forms; router/URL state; state machines (light touch); TanStack Query (or equivalent): cache keys, invalidation, optimistic updates, deduplication, stale responses; feature boundaries and large-application ownership.

### Scope Boundaries

- SE240 owns generic architecture vocabulary — apply it in React; do not rewrite SE240-L02.
- Performance profiling deep-dive is L04; RSC/Next is L05.

### Expected Understanding

Sketch a defensible state/data map for a booking feature and fix a stale-cache / wrong-owner bug without dumping everything into Context.

### Suggested Exercise / Lab

Broken availability after booking: predict cache behavior → investigate keys/invalidation → fix → verify → AI review.  
Secondary: Context provider that remounts children unnecessarily.

### Critical exercise rule

Prediction → Investigation → Correction → AI review.

### Planned Manuscript Structure

1. Narrative hook.
2. Technical development.
3. Trade-offs.
4. Oral examination.
5. Solutions.
6. Mental Model.
7. Next Lecture.
8. Lab.
9. Further Reading.
10. Dense Cheatsheet.

### Cross-references

SE240-L02, SE240-L03; SE250-L02; SE310-L01 (API contracts).

<!-- Full manuscript to be generated later. -->
