# SD02 — Durable Commerce Integrations Without a Distributed Fantasy

**Format:** 90-minute backend-leaning senior full-stack system design  
**Role archetype:** headless commerce frontend, third-party platforms and ERP, durable jobs, cloud  
**Evidence:** role-relevant fictional architecture prompt; **not an actual company's interview**.  
**Interviewer:** engineering lead for integrations; focuses on correctness, integration ownership, incident recoverability.

## Part I — Candidate and interviewer packet

### 0–10 min — What is the business problem?

"A retailer operates a React/Next.js storefront and uses an external commerce provider for checkout, an ERP for invoices/inventory, and a warehouse partner for fulfillment. Orders sometimes disappear between systems, inventory goes negative, and support cannot explain what happened. We're replacing fragile low-code flows with owned services. How do you approach a minimal durable integration layer?"

Offer on clarification:
- About 12k orders/day with bursts around promotions; an order includes lines and payment status.
- Commerce webhooks are at-least-once and may be delayed or reordered; an event may have a provider event ID.
- ERP API has a 100 requests/minute cap and sometimes times out after accepting a write.
- Warehouse partner imports shipment requests via HTTPS and can report asynchronous status.
- Storefront cannot block checkout for several minutes waiting for external systems.
- All counts here are **fictional exercise constraints**, not employer facts.

### 10–30 min — Source of truth and state transitions

Ask the candidate to define precisely what "order accepted" means. Distinguish checkout/payment capture, canonical order state, invoice, inventory allocation, and shipment.

"Tell me which business transitions can be safely eventual and which should block a user interaction. What would the user see if the ERP is unavailable?"

Encourage one vertical slice: paid order → accepted integration job → invoice & fulfillment updates → visible progress. Clarify cancellation/refund scope and avoid assuming all providers can participate in an atomic transaction.

### 30–50 min — Architecture and durable work

"Follow an OrderPaid event from arrival to a successful warehouse handoff. Include the failure path."

Ask for idempotent webhook ingest, authentication/signature check, raw event retention, dedup scope, database durable work state, broker/job runner, retry/backoff, downstream idempotency and correlation IDs. Offer a counterexample:

> ERP accepts invoice creation, but the HTTP response times out. The worker restarts and replays. What must happen to avoid duplicate invoices?

Explore provider idempotency key support versus reconciliation/search by external reference. Ask for a retry budget and manual exception queue.

### 50–66 min — Data mismatch incident

> At 14:05 warehouse dispatch count falls; checkout succeeds. The queue has 1,800 jobs pending. ERP responses include intermittent 429s; warehouse API reports healthy. Support sees "payment captured, status unknown" for 40 orders.

"What do you do in the next 15 minutes? What customer-facing promise can you make?"

Prompts: isolate ERP rate limiter, reduce request rate with shared quota, delayed retry and jitter, maintain ordering only per order where necessary, avoid poison retries, quantify affected orders. Discuss why blindly increasing worker concurrency may worsen 429s.

### 66–81 min — Extend and migrate carefully

"We need to migrate off the old low-code workflow without processing the same order through both systems."

Ask for shadow reads, flags/routing by order cohort, replay semantics, idempotency across old/new systems, backfill/reconciliation, observability and rollback. Introduce one late cancellation/refund event if time permits.

### 81–90 min — Stakeholder conversation and questions

"Marketing needs a weekend sale. What minimal safeguards must be present before launch, and what work can wait?" Reserve candidate questions.

---

# STOP — INTERVIEWER KEY / REASONABLE ANSWERS

## Architecture reference

Provider-signed webhook → validate, persist original event with unique provider/event key and correlation IDs → durable integration intent in transaction → worker/outbox → provider-specific adapters with rate limiting, retries and reconciliation → append-only transition/audit history → user and support read model. The order's canonical commercial state remains sourced from commerce/payment systems (depending on contract), while integration jobs track *delivery progress*, not invented payment facts.

Idempotency needs **more than duplicate webhook suppression**. For ambiguous downstream writes, persist an external reference or stable idempotency key. If provider lacks idempotency API, query for existing invoice/shipment before attempting another creation; if no safe recovery API exists, route to manual resolution rather than blindly repeating an irreversible call. A 202 / timeout from an external system does not prove failure. A generic "exactly once" claim is not enough.

**Correctness versus freshness:** A storefront may show "Order received; fulfillment pending" while ERP is down, provided payment state is actually known. Do not promise shipment before confirmed warehouse acceptance. Reconciliation compares commercial source, integration intents, ERP docs and warehouse records periodically, with traceable exceptions. Data drift is inevitable; silent data drift is optional.

**Operational incident:** 429 indicates rate limits, not necessarily API unavailability. Compare permitted vs requested rate, retry-After signals, shared token bucket / worker concurrency and job age; reduce pressure and spread backoff. Maintain fair ordering per order, not global serial processing. Alert on stuck state, age percentiles, dead-letter/error counts and reconciliation discrepancies. Support tooling needs a per-order timeline.

**Migration:** Define single live owner for each order/cohort, maintain dedup across old and new workers, shadow-only new logic initially, backfill in controlled batches and reconcile before cutover. Use explicit routing and a rollback that does not duplicate completed side effects.

**V1 simplicity:** Durable DB-backed job/outbox plus a small worker fleet may be sufficient at 12k orders/day. Kafka/microservices/Temporal are alternatives, not immediate mandatory artifacts. A queue helps throughput; it does not automatically resolve business consistency.

## Rubric

Strong: defines authoritative business events, handles timeouts honestly, chooses testable idempotency, explains operator recovery and prioritizes customer trust. Weak: global distributed transaction fantasy, infinite retries on invoice creation, treats queue ACK as ERP success, cannot explain the customer's experience during partial failure.

**Targeted refresher:** CS430-L01/L05, SE320-L03, SE325-L05 (if later authored), SE440-L01, CS330-L03.
