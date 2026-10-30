# Engineering Decision Map

A navigation layer above the catalogue — not a lecture. Revisit in 5–10 minutes when concepts feel fragmented.

**Principle for this programme:** breadth first → mechanistic intuition → selective depth when a mock, JD, or production problem demands it. AI coding agents increasingly write the code; engineers still own problem framing, architecture, trade-offs, failure modes, and verification.

The catalogue remains a **reference library**, not a completion checklist. Deeper material lives in the linked lectures.

---

## A. The complete mental picture

A modern product request rarely “hits a database.” It crosses several layers, each with its own failure modes:

```text
  User / device
       │
       ▼
  Browser / app UI  ── cache, SSR/CSR, auth cookies/tokens
       │
       ▼
  Edge / CDN / LB   ── TLS terminate, routing, rate limits
       │
       ▼
  API / BFF         ── authn/z, validation, contracts, idempotency keys
       │
       ├──────────────► Sync path: business logic ──► primary DB / search
       │                      │
       │                      └──► cache (Redis…) ──► read models
       │
       └──────────────► Async path: queue / bus ──► workers
                              │
                              ├──► side effects (email, billing, AI jobs)
                              └──► outbox / saga / workflow engine

  Infra: containers, config, secrets, CI/CD, autoscaling
  Ops:   logs, metrics, traces, alerts, runbooks
```

**Boundaries that matter**

| Layer | Owns | Typical failure that leaks upward |
| --- | --- | --- |
| UI | Interaction, optimistic UX, client validation | Shows success while the write never committed |
| Edge | Routing, TLS, coarse protection | Sends users to a dying region or sticky bad pod |
| API | Contracts, auth, orchestration of *one* request | Timeouts while a worker already charged the card |
| Data | Truth, constraints, isolation | Lost updates, dirty reads, hot partitions |
| Workers | Slow / retryable work | Duplicate side effects without idempotency |
| Observability | Evidence | You cannot tell *which* layer broke |

Failures propagate **asymmetricly**: a DB blip becomes API 500s, then UI spinners, then support tickets — unless timeouts, bulkheads, and user-visible states were designed deliberately.

---

## B. Engineering decisions and their consequences

| Decision | Problem | Prefer A when… | Prefer B when… | Primary trade-off | Easy-to-miss failure |
| --- | --- | --- | --- | --- | --- |
| **Relational vs document** | Shape of truth | Strong relations, joins, constraints, reporting | Document-shaped aggregates, flexible fields, high write locality | Query power vs modeling freedom | Document DB used as a bag of JSON with no ownership boundaries → inconsistent “entities” |
| **Sync request vs async job** | Latency vs work size | User must wait for the outcome; work is small and reliable | Long, bursty, or external-dependent work | UX simplicity vs operational complexity | Async without status/visibility → “did it work?” support load |
| **Cache vs authoritative read** | Latency / load | Hot read-mostly data; staleness is acceptable | Correctness-critical reads; low QPS | Speed vs freshness | Cache stampedes; caching user-specific or permissioned data poorly |
| **Modular monolith vs microservices** | Team/deploy boundaries | One product, one team, shared transactions help | Independent deploy/scale/failure domains truly needed | Simplicity vs isolation | Microservices for fashion → distributed monolith + ops tax |
| **SPA vs SSR vs hybrid** | First paint, SEO, auth | App-like authenticated UX (SPA); public/SEO content (SSR); both (hybrid) | — | Interactivity vs TTFB/complexity | SPA that SEO/auth/CDN were never designed for |
| **Vertical vs horizontal scale** | More capacity | Simple bottlenecks; strong single-node consistency | Elastic load; partial failure tolerance | Cost/complexity vs headroom | Horizontal scale without sticky session / shared-nothing design → random breakage |
| **Retry vs idempotency** | Transient faults | Safe read-only or naturally idempotent ops | Any side effect (pay, email, provision) | Resilience vs duplicate work | Retries *without* idempotency keys → double charges |
| **Strong vs eventual consistency** | Cross-node agreement | Inventory, money, unique constraints | Feeds, caches, analytics, multi-region UX | Correctness latency vs availability | Eventual consistency sold as “it will converge” without conflict rules |
| **Managed vs self-hosted** | Ops ownership | Undifferentiated infra; small team | Special constraints, cost at scale, regulatory control | Velocity vs control/cost | Managed defaults that hide backup/restore or connection limits until outage |
| **AI agent vs deterministic logic** | Ambiguous vs precise work | Drafting, ranking, tool routing with human/policy bounds | Money, authz, invariants, ledgers | Flexibility vs predictability | Agent “succeeds” while violating an invariant tests never encoded |

Concrete flavor: a booking funnel can use **relational** inventory + **idempotent** payment webhooks + **async** confirmation email + **SSR** product pages — each choice solves a different failure class.

---

## C. The connections that matter

Courses teach topics in silos. Interviews and production reward the **joints**:

- **Transactions ↔ concurrency ↔ business correctness** — isolation levels are product rules in disguise (double booking is a concurrency bug with a business name).
- **Queues ↔ retries ↔ idempotency ↔ distributed systems** — at-least-once delivery is the default; exactly-once is usually “idempotent + dedupe.”
- **Caching ↔ consistency ↔ latency** — every cache is a consistency policy, whether you wrote one down or not.
- **Infrastructure ↔ deployments ↔ reliability** — a perfect service still fails if releases, config, and rollbacks are unsafe.
- **API contracts ↔ versioning ↔ FE/BE compatibility** — “backward compatible” is a product promise enforced by schema and clients.
- **Observability ↔ performance ↔ incidents** — you cannot tune or repair what you cannot see across request and async paths.
- **AI tools ↔ authorization ↔ verification** — tool calling without authz and outcome checks is remote code execution with marketing.

Architectural judgment is largely pattern recognition across these joints: seeing that a “frontend bug” is actually an idempotency gap, or that a “slow API” is a missing index plus an N+1 across a service boundary.

---

## D. Thinking like an architect

When facing an unfamiliar problem, run a short checklist before drawing boxes:

1. **What is the actual business outcome?** (Not “add Kafka.”)
2. **What must remain correct even when the system is wrong?** Money, authz, uniqueness, privacy.
3. **What are the hard constraints?** Latency SLO, consistency, compliance, team size, existing stack.
4. **What fails, and how does the user experience failure?** Timeouts, partial writes, poison messages.
5. **Where does load concentrate?** Hot keys, thundering herds, fan-out.
6. **How is it operated?** Deploy, migrate, observe, roll back, on-call.
7. **How do we verify?** Invariants, acceptance tests, load/failure drills — not only happy-path demos.

**Overengineering smell:** new moving parts that do not buy a clearer failure domain, a real scale need, or a team boundary. Prefer the simplest design that preserves the invariants you named in step 2.

---

## E. Engineering with AI coding agents

Useful workflow:

**Problem → constraints & invariants → delegate implementation → review → test → operational verify.**

Make acceptance criteria explicit: “charging must be idempotent on `idempotency_key`”; “worker may run twice”; “UI must not claim success before commit.”

Agents excel at producing plausible code and tests for the cases you stated. They under-detect the cases you omitted.

**Example flaw:** an agent implements “export user data” as a synchronous API with a unit test that exports 10 rows. Tests pass. In production, multi-GB tenants timeout, double-click retries create overlapping exports, and the endpoint holds a DB read lock while writing to object storage. The missing architecture was: async job, cursor/pagination, idempotent enqueues, progress resource, and backpressure — none of which the happy-path tests required.

You still need enough mechanistic intuition to spot that class of mistake in review.

---

## F. Navigate to deeper material

Use the map to choose a lecture — then listen/read. Do not treat this list as homework.

| Theme | Start here |
| --- | --- |
| End-to-end request path | [`CS230-L01`](CS/CS230-computer-networks/CS230-L01-the-journey-of-a-web-request.md) · [`SE320-L01`](SE/SE320-backend-services/SE320-L01-the-anatomy-of-a-backend-service.md) |
| Relational modeling & SQL | [`CS330-L01`](CS/CS330-relational-databases/CS330-L01-relational-database-design.md) · [`CS330-L02`](CS/CS330-relational-databases/CS330-L02-sql-and-query-performance.md) |
| Transactions & correctness | [`CS330-L03`](CS/CS330-relational-databases/CS330-L03-transactions-and-isolation.md) |
| Beyond tables / data choice | [`CS340-L01`](CS/CS340-data-systems-beyond-relational/CS340-L01-the-database-that-didnt-fit-into-tables.md) · [`CS340-L07`](CS/CS340-data-systems-beyond-relational/CS340-L07-the-data-architecture-workshop.md) |
| Queues & async | [`SE320-L03`](SE/SE320-backend-services/SE320-L03-queues-workers-and-asynchronous-workflows.md) |
| Caching | [`SE320-L02`](SE/SE320-backend-services/SE320-L02-caching-trading-freshness-for-speed.md) |
| Distributed failure | [`CS430-L01`](CS/CS430-distributed-systems/CS430-L01-distributed-systems-and-partial-failure.md) · [`CS430-L02`](CS/CS430-distributed-systems/CS430-L02-consistency-replication-and-availability.md) |
| Concurrency / event loops | [`CS320-L06`](CS/CS320-operating-systems-and-concurrency/CS320-L06-concurrency-event-loops-and-cancellation.md) |
| Auth & browser security | [`SE310-L02`](SE/SE310-web-apis-and-security/SE310-L02-authentication-and-browser-security.md) · [`SE310-L01`](SE/SE310-web-apis-and-security/SE310-L01-the-frontend-backend-contract.md) |
| Architecture judgment | [`SE330-L01`](SE/SE330-software-architecture/SE330-L01-the-art-of-software-architecture.md) · [`SE330-L02`](SE/SE330-software-architecture/SE330-L02-architecture-patterns-and-their-consequences.md) |
| Frontend architecture | [`SE240-L02`](SE/SE240-frontend-engineering/SE240-L02-frontend-architecture-beyond-components.md) · [`SE250-L01`](SE/SE250-react-engineering/SE250-L01-thinking-in-react-a-vue-developers-new-mental-model.md) |
| Observability | [`SE440-L01`](SE/SE440-production-reliability/SE440-L01-observability-understanding-production-systems.md) |
| Releases & change | [`SE215-L11`](SE/SE215-software-engineering-ecosystem/SE215-L11-release-management-versioning-and-change-ownership.md) |
| Evidence / experiments | [`CS120-L04`](CS/CS120-mathematical-and-statistical-thinking/CS120-L04-experiments-evidence-and-causality.md) |
| AI tools & agents | [`AI410-L01`](AI/AI410-agentic-ai-systems/AI410-L01-tool-calling-and-connecting-ai-to-software.md) · [`AI410-L02`](AI/AI410-agentic-ai-systems/AI410-L02-agents-from-model-calls-to-autonomous-workflows.md) |
| System design studio | [`SE490-L03`](SE/SE490-architecture-studio/SE490-L03-system-design-workshop-build-for-100x-traffic.md) |

Topic index: [`technology-atlas.md`](technology-atlas.md). Study priorities: [`STUDY-INTENT.md`](STUDY-INTENT.md). Practice: [`interview-lab/`](interview-lab/).
