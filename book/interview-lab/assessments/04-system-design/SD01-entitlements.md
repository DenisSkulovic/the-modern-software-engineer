# SD01 — Memberships, Workspaces and Entitlements

**Format:** 90-minute senior full-stack system-design conversation; no required code  
**Role archetype:** customer platform for B2B organizations + individual creators, React/TypeScript frontend, cloud backend  
**Evidence:** job-family-inspired simulation focused on workspace hierarchy and authorization. **Not an official company's interview design.**  
**Interviewer:** senior platform engineer; seeks clear boundaries and migration pragmatism, not arbitrary planetary scale.

## Part I — Candidate prompt

### 0–10 min — Introduction and requirement discovery

"Our product serves solo creators and enterprise organizations. Today every user is essentially the owner of their own account. We're adding organization workspaces, collaborators, and subscriptions. Design the **minimum coherent authorization/entitlement platform** that other product teams can use."

The interviewer answers reasonable clarifications:
- 2M total user accounts; 20k organizations; typical organization has 3–40 people, some have 5k.
- Users may belong to multiple organizations and have an individual workspace simultaneously.
- Products have feature entitlements (e.g., export rights, seat limits), and people have **permissions** (e.g., invite member, edit project).
- Existing auth service issues signed identity tokens; this team may not replace it.
- Business-critical: paid enterprise customer should not lose legitimate access when a billing event is delayed, but revocation after security removal must take effect promptly.

Ask candidate to clarify source of truth, scope and non-goals. Resist forcing all requirements before they ask.

### 10–30 min — Model and APIs

"Give me entities and relationships; verbal or whiteboard. What API does an application call to decide whether a particular person can export from workspace W?"

Probes:
- Distinguish authentication, organization membership, role/capability permission and purchased entitlement.
- Where do inherited workspace permissions end? Are project-specific exceptions needed for V1?
- Who can see or edit organization membership? Who can grant an owner role?
- Does changing a token immediately change authorization? What about long-lived JWT claims?
- Does frontend hide controls, and is that enough?

Expect a concise example of a permission-check interface, not a specific cloud product.

### 30–50 min — Subscription, concurrency and lifecycle

"A customer buys 30 seats; 29 are filled. Two admins invite a new member simultaneously. Later one member is removed while a download is already being initiated."

Discuss:
- What counts as a seat (invited, accepted, active)?
- Atomic seat reservation or accepting bounded oversubscription?
- Correct role update without privilege escalation; optimistic concurrency if needed.
- Revocation timing for sensitive export operation; cache invalidation and maximum staleness.
- Audit logs and access evaluations across organizations.

### 50–67 min — Legacy migration

"Existing personal accounts each have project data. Organizations launch in six weeks. Do you migrate everything, introduce a compatibility layer, or both?"

Follow-ups: old bookmarked URLs, default workspace, duplicate names, stable identifiers, staged rollouts, orphaned projects, rollback. Ask for a migration process that can be rehearsed and checked, not a risky one-shot SQL script.

### 67–81 min — Incident and future feature

> Support reports that some recently removed members can still open old projects for minutes. An engineering manager says "decrease the JWT expiry to one minute." A product manager requests nested groups and arbitrary folder permissions immediately.

Ask to triage what evidence identifies the stale boundary, explain the implications of token TTL, and choose a sensible initial scope. Discuss monitoring for authorization denials and anomalous grants.

### 81–90 min — Candidate questions and final trade-off

"What is your first production milestone? What could go wrong even if every unit test passes?" Reserve time for candidate questions.

---

# STOP — INTERVIEWER KEY / DESIGN REFERENCE

## Suggested minimal model

- Identity users exist independently of authorization scopes; user ID is stable.
- Workspace/organization with ID, type (personal or organization), lifecycle.
- Membership (userId, workspaceId, role, status) with unique membership constraint, actor and audit history.
- Role-to-permission mapping or direct capability grants within a constrained vocabulary; authorize per resource and tenant, not just on role label.
- Product entitlement (workspaceId, feature, quantity/plan/state, effective dates) sourced from billing/contracts, independent from permission; seats are a constrained entitlement, not the same as membership.
- Resource ownership (project.workspaceId) and resource-level exceptions only if requirements justify them.

Evaluation: first authenticate user identity; load authoritative membership (and any scoped overrides); check requested capability for resource; check applicable product entitlement; then return allow/deny with auditability where required. A sample API: check(actorId, action="project.export", resource={workspaceId, projectId}) → decision. **Never trust a frontend claim or cached role string as proof of access.**

## Data / concurrency reasoning

Relational constraints and transactions can coordinate seats/memberships; if purchase events are delayed, distinguish provisional commercial grace from unsafe security revocations. For the 29/30 seats race, candidate may count only accepted seats and reserve in an atomic transaction/row lock or use a seat-allocation counter with compare-and-swap. The chosen semantics must be explicit. Client retries need idempotent invitation operations.

A membership revoke should be effective at the **authorization decision boundary** even if the old identity token remains valid. Keep high-risk permissions out of long-lived self-contained token claims or use server-side freshness/version/revocation checks. Cache keys include workspace/resource/auth version; revoke invalidates or bounds stale reads. A 1-minute token TTL alone does not solve stale server caches and causes churn.

## Migration / rollout

Prefer stable workspace IDs and compatibility for legacy personal workspace semantics, backfill memberships with owner constraints, dual-read or gated rollout, audit for missing/orphaned ownership, shadow-evaluate before enforcing, and make migrations restartable. Include a path for rollback of application behavior, though destructive schema rollback might be inappropriate. Resource-level access checks and tenant isolation get integration tests.

## Reasonable alternative designs

Start with a straightforward DB service rather than microservices plus policy engine. More elaborate ReBAC graph or policy-as-code platform can be justified if shared cross-product permissions and nested groups become real requirements. No credit simply for naming Zanzibar, OPA, or Auth0. Complexity needs an operational payoff.

## Rubric

Strong: separates user identity, membership, permission and purchased entitlement; gets server-side authorization and revocation right; makes an explicit concurrency choice; plans safe migration. Weak: equates hiding a button with security; stores every permission solely in a long-lived JWT; confuses plan limits with user rights; promises immediate consistency without a defined decision boundary.

**Links to curriculum if gaps appear:** SE310-L02/L03, CS330-L03, CS430-L02, SE330-L02, SE440-L03.
