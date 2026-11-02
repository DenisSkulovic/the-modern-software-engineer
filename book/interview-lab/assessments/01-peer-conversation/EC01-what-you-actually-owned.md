# EC01 — What You Actually Owned

**Format:** peer technical conversation (60 minutes, not a forced 90)  
**Role archetype:** backend-leaning senior full-stack product engineer; TypeScript/Node, integrations, production operations  
**Evidence basis:** inspired by published senior-engineer conversation formats in European product teams; exact questions below are fictional.  
**Permitted materials:** conversation, optional whiteboard or notes; no code execution required.  
**Interviewer:** curious senior engineer who is technically precise but not performatively difficult.

## Part I — Candidate and interviewer script

### Opening — 0–8 min

**Interviewer:** "Tell me about a system you have worked on recently. Which parts did you actually own, and which parts were inherited or built with teammates?"

Choose **one real experience**, not a polished generic architecture. The interviewer should accept a recon pipeline, event-driven service, feature delivery, SaaS backend, production incident, or other relevant real example. If the candidate claims a metric, ask for measurement and attribution, not rhetorical confidence.

**Natural follow-ups (pick 2):**
- What did the system do for its users? What was its most important correctness requirement?
- Which technical decisions were **yours**, and which were inherited or consensus decisions?
- What changed after you worked on it? How do you know?
- What was the least glamorous but most important failure mode?
- If the system were rebuilt today, which part would you deliberately simplify?

### Follow the actual architecture — 8–30 min

Ask for a verbal request / event journey through the chosen system: entry point → authorization → persistence → processing → user-visible completion. Do not demand a predetermined microservices picture.

Once the candidate names a background workflow, present the **fictional adjacent scenario**:

> "We have an API that accepts a report generation request. It stores a job in PostgreSQL, then enqueues work. Workers can be restarted or run the same job twice. Some reports take four minutes. Customers sometimes retry after a gateway timeout. Design a safe request and worker contract; keep the first version small."

**Probing in natural order:**
1. When do you return to the client? What identifies the job? Is the API retry safe?
2. What if the database commit succeeds and queue publishing fails? Can the work get stuck?
3. What if the worker completes the report but crashes before acknowledging delivery?
4. What is the **source of truth** for job state, and what is a duplicate side effect?
5. Where would a team investigate a backlog that grows only for one tenant?

The candidate may challenge the initial "stores then enqueues" design. Reward that.

### Evidence-driven incident — 30–43 min

Provide **only when needed**:

> On Monday 10:04, job creation success rate stays at 99.9%. Queue age climbs from 8 seconds to 17 minutes. Worker CPU is low, but DB connection wait grows to 3 seconds. One enterprise tenant accounts for 70% of new jobs. The database shows a long-running query used by a "progress" endpoint.

Ask: "What would you investigate in the next ten minutes, and what **wouldn't** you change yet?"

Possible follow-ups:
- Is the large tenant itself the root cause?
- Would increasing worker count help?
- Is a single 17-minute queue age metric enough to prove all tenants are failing?
- How do you contain impact without silently losing jobs?

### Senior judgment / collaboration — 43–53 min

"Your PM wants the feature tomorrow. Your first design takes three days and includes deduplication, one safe retry path, minimal status reporting and tests. What's your proposal?"

If an answer is abstract, ask for one actual trade-off they would put in a short note and one test that gates launch. If candidate is very strong, ask how they'd roll back schema changes or reconcile reports after outage.

### Candidate questions — 53–60 min

"Any questions about the role, our engineering culture or how we work?" Accept thoughtful practical questions. Don't require artificial enthusiasm.

---

# STOP — INTERVIEWER KEY / DEBRIEF ONLY

## Evaluation focus

| Competency | Good evidence | Weak evidence |
| --- | --- | --- |
| Ownership | Specific boundaries and individual contribution, candid uncertainties | "We built microservices" without who/why |
| Architecture | Correct request/job contract; coherent data/queue boundary | Queue mistaken for durable business truth |
| Failure reasoning | Duplicate/unknown outcomes, outbox or recoverable dispatch, ack semantics | Assumes exactly-once magic |
| Incident response | Checks DB wait, progress query, tenant fairness, queue stages | Randomly adds workers / increases timeout |
| Product judgment | Slices delivery while protecting irreversible work | "Ship now, fix all correctness later" |

## Reference reasoning (not a required design)

Accept an API that validates/authenticates the requester, chooses a client-scoped idempotency key, persists a job in a durable store, and returns 202 with a stable job/status resource. If creation and dispatch are separated, ensure recovery: e.g., transactional outbox written with the job and a relay, or a reconciler that enqueues jobs still pending. Do not accept a hand-wave that two independent DB/broker writes are atomic.

A worker claims/executes work with a retry policy, deadline, observable attempts, and deduplication. Acknowledgment occurs only after durable outcome recording; duplicate delivery must not cause a second irreversible side effect. Report creation may use unique job IDs and replaceable object-store artifacts. Business process idempotency is different from broker delivery guarantees.

The incident's low worker CPU plus high DB connection wait suggests blocked query/connection-pool pressure rather than simple CPU starvation. Investigate query plan, concurrent progress-poll rate, pool size, database locks, and per-tenant breakdown, including whether the long-running progress query causes contention. The 70% tenant share is a **clue** about fairness but not proof of root cause. Consider throttling expensive polling, isolating read workloads, tenant quotas, and progressive shedding; protect job durability.

Product answer: offer a thin correct first release with reliable idempotency/status and limited throughput, defer bells-and-whistles and speculative autoscaling. Speak with PM about impact and risks; don't demand three days purely from authority. The appropriate first version depends on irreversibility and financial/business harm.

## Suggested targeted refresh after an actual weak answer

SE320-L01/L03 (service, queues), CS430-L01/L05 (partial failure, durable workflows), CS330-L03 (transactions), SE440-L01 (observability). No automatic lecture completion or interview score.

**Interviewer guardrail:** The most important part is what the candidate actually did in a real project. Do not replace half the session with a fictional whiteboard game if their real experience yields useful depth.
