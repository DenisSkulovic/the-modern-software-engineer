---
id: SE250-L05
course: SE250
title: "React in Production: SPAs, Next.js, and Server Rendering"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L04
next: SE250-L06
---


# SE250 — React Engineering for Experienced Developers
## Lecture 05: React in Production: SPAs, Next.js, and Server Rendering

*Vite + React SPA ships fine until SEO and first paint demand a server. Next.js App Router arrives with Server Components and Client Components — and suddenly “just React” is an architectural boundary problem.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** 25–35 minutes spoken + architecture decision lab. Core React model from L01–L04 is prerequisite; this lecture adds production delivery layers.

### Learning Objective

Choose SPA vs SSR frameworks with eyes open; explain hydration, Suspense, and Server vs Client Components as an extra architectural layer — not “React running twice.”

### Opening Problem

A hotel catalogue must be crawlable and fast on first visit. A team copies client-only data fetching into a Server Component world (or the reverse) and gets hydration mismatches, waterfalls, or secrets leaked to the client.

### Planned Coverage

Vite SPA vs Next.js (and similar); routing; SSR; hydration; Suspense; Server Components vs Client Components; caching boundaries; deployment considerations; when a plain SPA is enough; keeping React fundamentals distinct from any one meta-framework.

### Scope Boundaries

- Do not confuse React itself with Next.js.
- Do not regenerate SE240-L04 delivery/SEO depth — cross-reference and specialize.
- SE215-L08 may own broader SEO orientation; keep React/Next mechanics here.

### Expected Understanding

Defend SPA vs App Router for a concrete product constraint, and diagnose a hydration or server/client boundary mistake.

### Suggested Exercise / Lab

Server/client boundary bug (or hydration mismatch): predict → investigate → fix → AI review.  
Decision memo: when *not* to adopt Next.js.

### Critical exercise rule

Prediction → Investigation → Correction → AI review.

### Planned Manuscript Structure

Standard SE250 structure; Next Lecture → L06 studio.

### Cross-references

SE240-L04; SE250-L01–L04; SE215-L08 (SEO orientation).

<!-- Full manuscript to be generated later. -->
