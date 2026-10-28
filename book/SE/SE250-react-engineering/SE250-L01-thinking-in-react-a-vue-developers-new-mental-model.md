---
id: SE250-L01
course: SE250
title: "Thinking in React: A Vue Developer's New Mental Model"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE250-L02
---


# SE250 — React Engineering for Experienced Developers
## Lecture 01: Thinking in React: A Vue Developer's New Mental Model

*You know Vue. You can ship UI with Cursor writing React. Then someone asks why clicking “increment twice” only adds one — and the gap between vibecoding and a mental model becomes obvious.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** practical React elective for experienced engineers. Target spoken duration ordinarily 25–35 minutes, plus mandatory prediction/debug exercises. Assumes JS/TS, DOM, APIs, and frontend architecture from SE240 — not React hook mastery. Explicit Vue comparisons where they clarify. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Explain what React actually does on a state update: render vs commit, state as a snapshot, batching, reconciliation, keys, and component identity — without treating React as “Vue with different syntax.”

### Opening Problem

A hotel booking UI has a counter that should jump by two on one click. Both `setCount(count + 1)` calls use the same captured `count`. The engineer who only knows shallow `useState` tutorials cannot predict or defend the behavior.

### Planned Coverage

Components as functions; JSX; props; rendering and committing; state snapshots; batching; reconciliation; keys; component identity/position; controlled updates; functional updates (`setCount(c => c + 1)`); explicit Vue `ref` / `computed` contrasts.

### Scope Boundaries

- Do not regenerate browser fundamentals or generic frontend architecture from SE240.
- Do not assume prior mastery of hooks beyond what this lecture introduces for state.
- Next.js / Server Components wait until L05.

### Expected Understanding

Given a small React component, predict output after interactions, explain *why*, and correct snapshot/identity mistakes without AI doing the reasoning first.

### Suggested Exercise / Lab — Prediction → Investigation → Correction → AI review

1. **Predict** what `incrementTwice` does with two `setCount(count + 1)` calls.
2. **Run** and compare.
3. **Fix** with updater functions; explain the difference.
4. Only then ask Cursor to review the explanation.

Additional: a form that resets because a changing `key` remounts the component — predict before fixing.

### Critical exercise rule

Present the unfamiliar behavior first. Require prediction, explanation, independent debugging, implementation, and verification **before** hints or solutions. AI prepares the broken app; it must not replace the first reasoning attempt.

### Planned Manuscript Structure

1. Narrative hook and sustained case study (Vue contrast).
2. Technical development of the React execution model.
3. Practical trade-offs and failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture hook.
8. Optional Practical Lab (after spoken end).
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card.

### Cross-references (for future authorship)

SE240-L01 (browser), SE240-L02 (architecture), SE240-L03 (state ideas — Vue-flavored).

<!-- Full manuscript to be generated later. -->
