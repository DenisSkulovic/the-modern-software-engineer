---
id: SE215-L07
course: SE215
title: "Owning End-to-End Testing"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE215-L06
next: SE215-L08
---


# SE215 — The Software Engineering Ecosystem
## Lecture 07: Owning End-to-End Testing

*An application has excellent unit-test coverage, yet customers cannot complete checkout after a deployment. The team has E2E tests, but they either rely on mocked APIs or fail unpredictably.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** short orientation elective. Target spoken duration ordinarily 18–25 minutes (~2,800–4,000 spoken words). Conceptual and practically informed; not a specialist qualification. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Understand how to design and maintain an E2E suite that verifies meaningful user workflows without becoming unreliable or excessively slow.

### Opening Problem

An application has excellent unit-test coverage, yet customers cannot complete checkout after a deployment. The team has E2E tests, but they either rely on mocked APIs or fail unpredictably.

### Planned Coverage

Browser E2E testing in practice using Playwright as the principal example; test-suite architecture; fixtures; test data; authentication setup; browser contexts; stable selectors; accessibility-oriented locators; synchronization; retries; parallel execution; test isolation; mocked versus real backends; local and CI environments; trace artifacts; screenshots; flakiness investigation; smoke suites; regression suites; and ownership of failures. Distinguish browser-component testing, browser-based integration testing, and full-system E2E testing.

### Scope Boundaries

SE240-L06 and SE440-L03 already cover the testing philosophy and test layers. This lecture emphasizes practical ownership and implementation.

### Expected Understanding

Design a Playwright test strategy for a full-stack application, choose what to mock, prepare test data, and diagnose flaky tests.

### Suggested Exercise / Lab

Build a small Playwright suite for a booking flow, including deterministic test data, successful checkout, validation failure, and one network-failure scenario. The practical lab may be substantially longer than the spoken lecture.

### Planned Manuscript Structure

1. Narrative hook and sustained engineering case study.
2. Technical development of the underlying mechanisms.
3. Practical trade-offs and realistic failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture or course-completion transition.
8. Optional Practical Lab, after the spoken lecture ends.
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card, last, inside one fenced text block.

### Cross-references (for future authorship)

Refer to deeper curriculum coverage by lecture ID rather than duplicating technical depth. SE215 is a gateway into the existing library, not a replacement for it.

<!-- Full manuscript to be generated later. -->
