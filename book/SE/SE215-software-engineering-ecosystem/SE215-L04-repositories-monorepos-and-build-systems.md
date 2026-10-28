---
id: SE215-L04
course: SE215
title: "Repositories, Monorepos, and Build Systems"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE215-L03
next: SE215-L05
---


# SE215 — The Software Engineering Ecosystem
## Lecture 04: Repositories, Monorepos, and Build Systems

*A company has a frontend, backend API, background workers, shared TypeScript packages, and deployment tooling. Engineers disagree about whether they belong in one repository or five.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** short orientation elective. Target spoken duration ordinarily 18–25 minutes (~2,800–4,000 spoken words). Conceptual and practically informed; not a specialist qualification. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Understand the trade-offs behind repository organization and tooling in multi-application software projects.

### Opening Problem

A company has a frontend, backend API, background workers, shared TypeScript packages, and deployment tooling. Engineers disagree about whether they belong in one repository or five.

### Planned Coverage

Monorepos versus multirepos; project and package boundaries; directory organization; dependency graphs; package managers and workspaces; npm, pnpm, Yarn, Nx, Turborepo; task orchestration; incremental builds; caching; shared contracts; generated clients; code ownership; independent versioning and releases; CI implications. When a monorepo is useful and when it becomes cumbersome. Distinguish repository structure, application architecture, and deployment architecture.

### Scope Boundaries

Do not repeat Clean Architecture, DDD, or microservice fundamentals from SE330 and CS430. Refer to them when discussing dependency and deployment boundaries. A monorepo does not imply a monolith, and a multirepo does not imply microservices.

### Expected Understanding

Defend a monorepo or multirepo choice and explain how changes, builds, tests, and deployments flow through it.

### Suggested Exercise / Lab

Design a repository layout for a TypeScript frontend, Node.js API, Python worker, shared API schemas, and infrastructure code.

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
