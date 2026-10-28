---
id: SE250-L04
course: SE250
title: "React Performance, Testing, and Debugging"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L03
next: SE250-L05
---


# SE250 — React Engineering for Experienced Developers
## Lecture 04: React Performance, Testing, and Debugging

*The page “feels slow,” Profiler lights up half the tree on every keystroke, and someone pastes `memo` and `useMemo` everywhere — including places the React Compiler would (or wouldn’t) help.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** 25–35 minutes spoken + profiling/testing lab. Builds on L01–L03.

### Learning Objective

Investigate rerenders with evidence; apply memoization and transitions judiciously; understand what React Compiler does and does not excuse; use error boundaries and Testing Library for behavior, not implementation trivia.

### Opening Problem

A booking search UI janks while typing. Premature memoization obscures the real expensive subtree. Tests assert internal state instead of user-visible behavior. An Effect race passes in CI and fails for customers.

### Planned Coverage

React Profiler; expensive updates; memo / `useMemo` / `useCallback` judgment; React Compiler (stable but optional — does not waive Rules of Hooks); transitions; virtualization (when relevant); error boundaries; Suspense (client-facing); React Testing Library; reproducing Effect races and identity bugs; production investigation habits.

### Scope Boundaries

- SE240-L05 / L06 own general frontend performance and testing strategy — specialize to React here; do not regenerate those lectures.
- SSR/RSC production architecture is L05.

### Expected Understanding

Profile a janky interaction, name the real cost, fix without cargo-cult memoization, and write a behavior test that would catch the bug.

### Suggested Exercise / Lab

Unnecessary render cascade: predict → profile → fix → test → AI review.  
Secondary: broken custom hook under Strict Mode.

### Critical exercise rule

Prediction → Investigation → Correction → AI review.

### Planned Manuscript Structure

Standard SE250 structure (hook → deep dive → oral → lab → cheatsheet).

### Cross-references

SE240-L05, SE240-L06; SE250-L01–L03.

<!-- Full manuscript to be generated later. -->
