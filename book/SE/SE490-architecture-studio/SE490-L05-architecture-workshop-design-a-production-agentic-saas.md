---
id: SE490-L05
course: SE490
title: "Architecture Workshop: Design a Production Agentic SaaS"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [AI501-S12]
prev: SE490-L04
next: null
---



# SE490 — Architecture and Systems Design Studio
## Lecture 05: Architecture Workshop: Design a Production Agentic SaaS

### The €320 Refund That Should Never Have Happened

It's Monday morning. You've just joined a European SaaS company as its new principal engineer.

The company operates a customer-service platform for hotel groups. Its product integrates with hotel reservation systems, payment providers, booking channels, and customer communication services.

Six months ago, the team added AI.

Initially, the assistant answered frequently asked questions. Then it gained access to reservation records. Eventually, developers introduced tool calling, allowing it to prepare modifications, retrieve payment information, and occasionally issue refunds.

Customers loved the conversational interface. Support managers appreciated the reduced workload.

Then an incident occurred.

A customer contacted the assistant:

> I booked a room for €320, but the hotel says it never received the reservation. My bank shows the payment. Can you sort this out?

The assistant queried the reservation system and found no confirmed booking. It queried the payment provider and found an authorization for €320.

It concluded that the customer had been charged without receiving a reservation.

Reasonable so far.

The assistant then requested a refund.

Unfortunately, the payment was merely authorized, not captured. The payment provider's workflow required canceling the authorization rather than issuing a refund.

The assistant's tool execution failed with a timeout. It retried using a new operation identifier.

Meanwhile, an asynchronous booking-confirmation event arrived from the hotel.

The reservation was now confirmed.

The assistant didn't know.

It continued working from its earlier observations, eventually causing a €320 refund against a subsequently captured payment.

The customer now had a valid reservation and had received their money back.

The company lost €320, generated inconsistent accounting records, and spent several hours investigating the incident.

The CTO asks you a question:

> How do we make sure this never happens again?

You could propose a better model.

You could rewrite the prompts.

You could introduce a dedicated refund agent, a supervisor agent, a memory framework, and an elaborate multi-agent architecture.

Or you could recognize that the incident exposes a deeper problem.

**The system has allowed a probabilistic component to coordinate business operations without sufficient authoritative state, execution guarantees, or control boundaries.**

The correct solution isn't necessarily more AI.

It's better architecture.

Today, we'll design that architecture from first principles.

This is the final workshop of **SE490 — Architecture and Systems Design Studio**, and the last lecture of the sixty-lecture core curriculum.

---

## 1. The Assignment: Build Something a Company Could Actually Operate

Let's establish a realistic business scenario.

Our fictional product is called **Harbor**, a multi-tenant customer-service SaaS for hotel operators.

It supports hotel groups in Europe and integrates with their property-management systems, reservation providers, and payment services.

Harbor currently serves:

| Dimension | Planning assumption |
|---|---:|
| Hotel properties | 180 |
| Enterprise tenants | 24 |
| Customer conversations | 120,000/month |
| Peak conversation traffic | 10× average |
| Historical reservation records | 4 million |
| Supported languages | 8 |
| Active customer-support agents | 350 |

These are architectural assumptions for the exercise, not observed industry statistics.

The company has a team of eight engineers and a modest infrastructure budget.

Its backend is primarily TypeScript and Node.js, deployed on AWS. PostgreSQL stores transactional data, Redis supports some caching and background processing, and several external integrations communicate through REST APIs and webhooks.

The frontend uses Vue 3.

This is an established SaaS product, not a greenfield demonstration.

### The business objectives

Management wants Harbor's AI assistant to:

1. Answer hotel-policy and reservation questions.
2. Interpret modification and cancellation requests.
3. Retrieve current booking and payment information.
4. Prepare modification quotes and possible remedies.
5. Handle uncomplicated support interactions without human intervention.
6. Escalate uncertain or high-risk situations.
7. Assist support agents investigating complicated cases.

The company also wants to reduce support costs without sacrificing customer trust.

### The nonfunctional requirements

We establish several initial targets:

**Security:** No customer may access another customer's or tenant's private data.

**Correctness:** Financial and reservation mutations must obey authoritative business rules.

**Reliability:** An interrupted workflow must recover without blindly duplicating external actions.

**Latency:** Routine conversational interactions should remain comfortably interactive, with an initial p95 target of five seconds for simple questions.

**Availability:** Core reservation access must remain functional when the AI provider is unavailable.

**Cost:** AI inference should initially remain below an average of €0.05 per customer conversation, excluding human-support costs.

**Auditability:** Important actions must be traceable to a user request, authorization event, operation identifier, and external outcome.

These are proposed acceptance criteria. We would validate them with stakeholders before treating them as contractual SLOs.

The architecture must also comply with applicable privacy, payment, and contractual requirements.

### The deliberate constraint

We are not permitted to solve the problem by hiring forty engineers and rebuilding the entire product.

Our design must be maintainable by the existing team.

This matters.

An architecture that is technically sophisticated but economically impossible to maintain is not a successful architecture.

---

## 2. The First Decision: Where Does AI Belong?

Before choosing a model or agent framework, we should classify the product's responsibilities.

Some require natural-language interpretation.

Others require precise business operations.

Confusing those responsibilities is how the opening incident happened.

| Responsibility | Recommended mechanism |
|---|---|
| Interpret customer intent | LLM |
| Understand ambiguous language | LLM |
| Explain hotel policies | Retrieval + LLM |
| Retrieve reservation status | Authoritative API |
| Check room availability | Reservation provider |
| Calculate price differences | Deterministic business logic |
| Decide refund eligibility | Authoritative policy rules and workflow |
| Execute payment operations | Controlled backend service |
| Select investigative next steps | Bounded agent, where justified |
| Persist conversation history | Database |
| Maintain operation state | Durable workflow store |
| Enforce permissions | Trusted application code |

The distinction isn't that language models are incapable of arithmetic or logical reasoning.

They can perform both.

The distinction is that we already possess deterministic systems better suited to enforcing business invariants.

Consider a customer saying:

> Move my arrival to Friday, but only if the extra charge stays below €100.

The model can extract:

```json id="n782me"
{
  "intent": "modify_reservation",
  "requestedArrival": "Friday",
  "maximumAdditionalCostMinorUnits": 10000,
  "currency": "EUR"
}
```

The application resolves the date using trusted calendar context, retrieves the authenticated reservation, checks availability, and calculates the price difference.

If the difference exceeds €100, the operation must not proceed.

That final constraint shouldn't depend on whether the model correctly remembers the customer's condition during a later reasoning step.

**Interpretation belongs to the model. Enforcement belongs to the application.**

This division becomes our first architectural decision record.

---

## 3. Architecture Decision Record 001: A Modular Monolith With an AI Subsystem

The company already operates a reasonably functional backend.

Should we introduce a separate microservice for each AI capability?

A reservation agent service, a memory service, a RAG service, a tool service, a supervisor service, and perhaps a dedicated orchestration platform?

No.

Not initially.

Most of these components will share authentication, tenant context, domain models, database transactions, and operational infrastructure.

Splitting them prematurely would increase deployment complexity without delivering a clear business benefit.

We'll start with a **modular backend**, separating AI-specific responsibilities from authoritative domain services.

```text id="j3q5v8"
                 Vue 3 Application
                         |
                         v
                 API Gateway / BFF
                         |
                         v
               Application Backend
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
  Conversation       AI Application     Domain Services
    Service             Layer                |
       |                 |                   |
       |       +---------+---------+         |
       |       |         |         |         |
       |       v         v         v         |
       |    Context    Model     Tool        |
       |    Builder   Gateway   Registry     |
       |       |         |         |         |
       |       |         |         +---------+
       |       |         |
       |       |         v
       |       |     Model Provider
       |       |
       |       v
       |    Retrieval Service
       |       |
       +-------+-------------------+
               |
               v
          PostgreSQL / S3

Background execution:
SQS / Workers / Durable Operation Store

External systems:
PMS / Booking Providers / Payment Providers
```

This is a logical architecture.

It doesn't require every box to become an independently deployed service.

### Why this structure?

The AI application layer handles model-specific concerns: prompt construction, model selection, structured outputs, tool discovery, token budgets, and evaluation metadata.

Domain services continue to own reservation and payment operations.

The tool registry exposes selected domain capabilities through validated interfaces.

This prevents the AI subsystem from developing a parallel set of business rules.

For example, the reservation service already knows how to check cancellation eligibility.

We should not implement another cancellation-policy engine inside an agent prompt.

### Deployment choices

Given the team's AWS experience, we can retain the existing API Gateway and Lambda infrastructure for suitable request handlers.

PostgreSQL remains the transactional source of truth.

S3 stores documents and larger evidence artifacts.

Background operations use a queue and dedicated workers.

We don't need Kubernetes merely because LLM inference is involved.

Most inference happens on the model provider's infrastructure.

Our primary responsibilities are orchestration, data access, security, and reliability.

If long-running workloads eventually require containerized workers, ECS or another managed compute platform may be appropriate.

But introducing an entire Kubernetes control plane would currently solve no identified problem.

---

## 4. The Conversational Request Lifecycle

Let's follow an ordinary request.

A customer writes:

> I booked a room for next Thursday. Can I move it to Saturday?

The frontend sends the message to Harbor.

### Step 1: Authenticate and establish context

The backend identifies the authenticated customer and tenant.

It retrieves relevant conversation state and determines whether a specific reservation is already associated with the interaction.

The model must not invent identity or ownership.

If multiple reservations match, the assistant should ask for clarification rather than selecting one arbitrarily.

### Step 2: Interpret the request

The AI layer uses a structured-output operation to classify intent and extract relevant information.

A smaller, fast model may be sufficient.

Possible output:

```json id="bbi0kb"
{
  "intent": "modify_reservation",
  "targetArrivalText": "Saturday",
  "reservationReference": null,
  "needsClarification": false
}
```

The backend resolves relative dates using the current date and relevant hotel timezone.

A missing explicit reservation reference is not necessarily a problem if the authenticated conversation is already bound to one reservation.

### Step 3: Execute authoritative reads

The application retrieves the reservation and obtains live availability from the hotel integration.

These are deterministic application operations.

The model doesn't need to decide the sequence if the workflow is already known.

### Step 4: Calculate the modification quote

The backend calculates:

- Proposed new dates.
- Availability.
- Additional cost or refund.
- Applicable modification restrictions.
- Quote expiration.

The model may explain the result, but the quote itself must come from trusted systems.

### Step 5: Prepare the next action

The assistant responds:

> Saturday is available. Moving your arrival would cost an additional €35. Would you like to confirm the change?

The application also creates a structured pending operation.

If the user confirms, the backend proceeds through the controlled modification workflow.

This request required natural-language interpretation and generation.

It did not require an autonomous agent planning every step.

That is intentional.

---

## 5. Architecture Decision Record 002: Use Agents Selectively

We need to decide which workflows justify autonomy.

Let's divide Harbor into three categories.

### Category A — Simple language operations

Examples include intent extraction, summarization, language detection, and producing customer-facing explanations.

These should generally use a single model call.

They don't need agent loops.

### Category B — Known business workflows

Reservation modification, cancellation, payment reconciliation, and refund preparation have established business steps.

The application should coordinate these deterministically.

LLMs can assist with interpretation and communication, but shouldn't control mandatory transactional sequences.

### Category C — Open-ended investigations

Some tasks don't have a predictable sequence.

For example:

> Investigate why this customer's reservation failed and determine the likely root cause.

The relevant evidence might reside in booking events, payment records, provider errors, or infrastructure logs.

A bounded investigative agent can decide which read-only tools to invoke based on intermediate findings.

This is our strongest initial use case for autonomy.

### The resulting design

```text id="5tm7wg"
Incoming support request
          |
          v
Structured intent extraction
          |
          +--> Routine question
          |         |
          |         v
          |    Retrieval + answer
          |
          +--> Booking operation
          |         |
          |         v
          |    Deterministic workflow
          |
          +--> Complex investigation
                    |
                    v
              Bounded agent loop
                    |
                    v
              Findings / proposal
                    |
                    v
              Human or workflow review
```

The investigative agent begins with read-only permissions.

It may propose remedies, but it does not execute refunds or cancellations.

This greatly reduces the consequences of incorrect reasoning.

### What about multiple agents?

We have no demonstrated requirement for them yet.

A single investigative agent with a carefully selected tool set is simpler to debug and operate.

If evaluations later reveal that payment investigations and infrastructure investigations require substantially different contexts or expertise, we can introduce specialist workers.

But we won't add a supervisor agent merely to make the architecture diagram look like a corporate organization chart.

---

## 6. The Knowledge Architecture: RAG Where It Adds Value

Harbor needs to answer questions about hotel policies.

These documents are private, occasionally updated, and specific to each hotel or tenant.

RAG is appropriate.

But what exactly belongs in the retrieval system?

### Good RAG candidates

- Cancellation-policy documents.
- Hotel amenities and service descriptions.
- Support procedures.
- Contractual explanations.
- Internal troubleshooting documentation.
- Historical incident reports.

### Poor RAG candidates

- Current reservation status.
- Live room availability.
- Payment capture status.
- Customer balances.
- Whether a refund has already been issued.

Those belong in authoritative operational systems.

### Ingestion

Hotel-policy documents arrive through uploads or integrations.

A background pipeline parses them, preserves structural information, generates chunks, creates embeddings, and indexes the content.

Each chunk retains:

```text id="i80m09"
document_id
document_version
tenant_id
property_id
section
effective_from
effective_to
content
embedding_model_version
source_location
```

For an initial implementation, PostgreSQL with pgvector and full-text search may be sufficient.

We can combine lexical and vector retrieval, optionally adding reranking when evaluation demonstrates a benefit.

### Source authority

Suppose a customer asks about cancellation eligibility.

The search system finds:

1. A 2024 cancellation FAQ.
2. A 2026 official policy.
3. A support note describing an old exception.

The semantically closest result isn't necessarily the authoritative one.

Retrieval must account for document scope, effective dates, and source authority.

The application should also distinguish policy documents from current business facts.

### Citations

Generated answers should reference identifiable source passages.

The model may cite source IDs, but the application should verify that those sources were actually retrieved and authorized.

Citation existence alone doesn't establish that the claim is supported.

For important policy decisions, an authoritative rule evaluator may still be necessary.

RAG provides explanations and reference material.

It does not become the transactional policy engine.

---

## 7. Tool Design: Business Capabilities, Not Database Access

Our investigative agent needs access to real systems.

We should expose meaningful operations rather than unrestricted implementation primitives.

An initial tool catalog might look like:

| Tool | Purpose | Permission |
|---|---|---|
| `get_reservation_summary` | Retrieve booking status and dates | Read |
| `get_booking_events` | Inspect reservation lifecycle | Read |
| `get_payment_state` | Retrieve authorization/capture status | Read |
| `get_modification_quote` | Calculate a proposed modification | Read/computation |
| `search_hotel_policies` | Retrieve relevant documentation | Read |
| `prepare_cancellation` | Create a pending operation | Controlled write |
| `prepare_refund_review` | Create a refund-review proposal | Controlled write |

Notice that there is no generic `execute_sql` tool.

There is also no unrestricted `issue_refund` tool exposed to the investigative agent.

### Execution boundary

Every tool invocation follows:

```text id="3d501u"
Model-generated request
          |
          v
Tool allowlist
          |
          v
Schema validation
          |
          v
Authenticated principal
          |
          v
Authorization check
          |
          v
Business preconditions
          |
          v
Domain service
          |
          v
Normalized result
```

For example, a model may request:

```json id="ptzb2g"
{
  "reservationId": "res_84721"
}
```

The backend must verify that the requesting principal can access this reservation.

The identifier itself is not an authorization credential.

### Should we use MCP?

Not necessarily.

Harbor currently has one application integrating with its own domain services.

Direct TypeScript interfaces are simpler.

If the company later exposes these capabilities to several independent AI hosts—such as an internal engineering assistant, customer-support application, and external partner agents—an MCP server could become useful.

The decision is about interoperability.

MCP would standardize tool discovery and invocation, but it wouldn't eliminate authorization or business correctness requirements.

---

## 8. The Critical Workflow: Preparing and Executing a Refund

Now let's return to our opening incident.

A customer appears to have paid €320 for an unconfirmed reservation.

What should happen?

First, the assistant must distinguish:

- Payment authorization.
- Payment capture.
- Reservation confirmation.
- Refund eligibility.
- Actual refund execution.

These are separate states and events.

A payment authorization isn't equivalent to a captured payment.

A missing reservation confirmation doesn't necessarily mean the booking failed permanently.

And a refund is not necessarily the correct remedy.

### Step 1: Investigate

The read-only agent gathers evidence.

```text id="lvgltd"
Reservation:
confirmation_pending

Payment:
authorization_succeeded

Capture:
not_confirmed

Provider booking:
status_unknown
```

The agent produces a finding:

> The customer has a successful payment authorization, but the reservation-confirmation outcome remains uncertain. Reconciliation is required before proposing a financial remedy.

This is more useful than blindly issuing a refund.

### Step 2: Reconcile authoritative state

A deterministic service queries the reservation provider and payment provider.

If the booking succeeded, the application can update its local records and notify the customer.

If the booking definitively failed and the payment remains authorized but uncaptured, the appropriate operation may be authorization cancellation.

If payment was captured and the service cannot be provided, a refund may be appropriate under applicable rules.

These branches depend on authoritative systems and business policy.

### Step 3: Prepare the remedy

Suppose reconciliation confirms:

- No reservation exists.
- €320 was captured.
- The customer qualifies for reimbursement.

The backend prepares:

```json id="zj6d6p"
{
  "operationId": "refund-op-92817",
  "reservationId": "res_84721",
  "paymentId": "pay_442",
  "amountMinorUnits": 32000,
  "currency": "EUR",
  "status": "awaiting_approval"
}
```

The operation is persisted.

No money has moved yet.

### Step 4: Obtain approval

For the initial release, financial mutations require approval through a trusted application workflow.

The approver sees the specific payment, amount, reason, and verified state.

Approval is associated with this operation, not with a vague conversational statement.

### Step 5: Execute and reconcile

A worker claims the approved operation and invokes the payment provider.

It uses a stable idempotency identity supported by the provider.

The worker then records the authoritative outcome.

If the provider times out, the operation enters an uncertain state pending reconciliation.

The agent cannot invent a new refund operation merely because it received an error.

### The state machine

```text id="6cpgco"
PROPOSED
    |
    v
VALIDATED
    |
    v
AWAITING_APPROVAL
    |
    v
APPROVED
    |
    v
SUBMITTED
    |
    +------> SUCCEEDED
    |
    +------> FAILED
    |
    +------> UNKNOWN
                 |
                 v
            RECONCILING
                 |
          +------+------+
          |             |
          v             v
       SUCCEEDED      FAILED
```

This is ordinary business-workflow engineering.

The AI system participates by interpreting requests, gathering evidence, and explaining outcomes.

But authoritative state transitions remain controlled by trusted services.

---

## 9. Durable Execution: Surviving the Worst Possible Moment

Suppose the refund worker sends the payment-provider request.

The provider succeeds.

The worker crashes before recording success.

This is the most important recovery scenario in the design.

A naïve implementation would retry the refund.

A reliable implementation preserves a stable logical operation identity and reconciles the outcome.

### The transactional outbox

One useful mechanism is the transactional outbox.

When an approved operation is recorded, the application can create a corresponding outbox event in the same database transaction.

```text id="az3scw"
PostgreSQL transaction
       |
       +--> Update refund operation
       |
       +--> Insert outbox event
       |
       v
Commit
```

A separate dispatcher publishes the event to the worker queue.

This prevents a common failure in which the database transaction commits but the application crashes before scheduling background work.

The dispatcher itself can publish duplicates.

Therefore, consumers must handle duplicate messages.

### At-least-once delivery

AWS SQS standard queues provide at-least-once delivery and don't guarantee strict ordering. Visibility timeouts temporarily hide messages being processed, but duplicates remain possible.

Our operation handler must therefore be idempotent. <Cite ref="turn723002search11"/>

A simplified sequence might be:

```text id="pju4v6"
Receive queue message
        |
        v
Load operation from PostgreSQL
        |
        v
Claim operation safely
        |
        v
Check terminal state
        |
        +--> Already complete: acknowledge
        |
        v
Reconcile existing external attempt
        |
        v
Execute if appropriate
        |
        v
Persist authoritative result
        |
        v
Acknowledge queue message
```

The application must use transactional state transitions or equivalent concurrency controls so competing workers don't both submit the same operation.

The exact implementation depends on provider guarantees and whether an operation is already in progress.

### Provider idempotency limitations

Stripe, for example, supports idempotency keys for eligible POST requests and documents its retention and parameter-consistency behavior. Reusing a key after it has been pruned may create a new operation, so internal durable records remain necessary. <Cite ref="turn723002search9"/>

An idempotency key isn't a substitute for an operation ledger.

Likewise, a queue isn't a transaction manager.

The architecture should never claim exactly-once external effects unless the complete system genuinely establishes those guarantees.

---

## 10. Conversation Memory Versus Operational State

Harbor also needs to remember customer interactions.

But we should be selective.

### Conversation history

Store recent messages and relevant tool observations in a conversation repository.

For model inference, construct context using the recent history plus any relevant summaries.

Avoid indefinitely appending every tool response.

### Customer preferences

Explicit durable preferences belong in structured customer records.

For example:

```json id="hd7y82"
{
  "preferredLanguage": "de",
  "notificationChannel": "email",
  "preferredRoomLocation": "quiet"
}
```

There's no need for a vector-memory system to retrieve a known notification preference.

### Investigation history

Long-running investigations need durable event records, evidence references, and checkpoints.

The model may receive a compact summary when work resumes.

However, critical operation IDs, approvals, and external outcomes remain in structured application state.

### The stale-memory problem

Suppose yesterday's investigation found a reservation pending.

Today, the customer asks whether it's confirmed.

The assistant may use historical memory to understand the context, but it must retrieve current authoritative status before answering.

Memory helps explain history.

It doesn't override present reality.

### Do we need semantic long-term memory?

Possibly later.

For the initial release, conversation history, structured customer preferences, and durable workflow records may be sufficient.

A semantic memory system should be introduced only after observing use cases that benefit from recalling unstructured historical information.

Avoid adding persistent AI memory merely because the framework has a memory module.

---

## 11. Security Architecture: Assume the Model Can Be Manipulated

Harbor processes customer messages, uploaded documents, hotel policies, and external API responses.

Some content is untrusted.

An attacker may insert malicious instructions into a document retrieved by RAG or a message processed by the agent.

The model might attempt to follow them.

Our architecture should contain the consequences.

### Tenant isolation

Every business data request includes trusted tenant context.

A reservation lookup must enforce the authenticated customer's permissions.

A retrieval query must filter documents before exposing them to the model.

An agent memory store must prevent cross-tenant information access.

PostgreSQL row-level security can provide defense in depth where appropriately configured, but it doesn't replace correct application authorization.

### Tool permissions

The investigative agent receives read-only tools.

Prepared business operations go through separate services.

Payment execution requires authorization and, under our initial policy, explicit approval.

### Data minimization

The model receives the fields needed for the current task.

For example, answering a booking-status question doesn't require sending full payment details or identity documents.

Production logs should avoid indiscriminately storing raw conversations and sensitive tool responses.

### Prompt injection

A retrieved document might instruct the assistant to export customer records.

The model may attempt to comply.

But it shouldn't possess an unrestricted export tool, and any available data operations should enforce authorization independently.

The OWASP Agentic Applications guidance provides a useful threat-modeling reference for these risks. <Cite ref="turn723002search3"/>

The design principle is simple:

**The system should remain secure even when the model makes an unsafe decision.**

---

## 12. Evaluation Architecture: How Do We Know This Works?

A production system requires more than successful demonstrations.

We need evidence across several layers.

### Intent extraction

Create a dataset of realistic customer messages.

Evaluate whether the model distinguishes:

> Can I cancel my booking?

from:

> Cancel my booking.

Also test conditional instructions, relative dates, missing information, and multilingual requests.

### Retrieval

Measure whether the correct policy passages are found.

Test ordinary rules, exceptions, obsolete versions, and tenant-specific documents.

Use known evidence to separate retrieval failures from generation failures.

### Tool selection

Evaluate whether the agent chooses appropriate read-only operations.

A question about payment status should not trigger a cancellation-preparation tool.

### Workflow correctness

Use isolated test databases and simulated payment providers.

Inject timeouts, duplicate queue messages, stale reservation data, and delayed webhooks.

Verify authoritative final state rather than trusting the agent's description.

### Agent trajectories

Inspect complete action sequences.

An investigation that reaches the correct conclusion after attempting unauthorized operations is not a successful run.

Current evaluation tooling supports examining model and tool trajectories, but a portable code-first harness should preserve our own test cases and acceptance criteria. <Cite ref="turn723002search1"/>

### Initial acceptance criteria

For the first controlled release, we might propose:

| Metric | Initial requirement |
|---|---|
| Cross-tenant access | Zero successful violations in security tests |
| Unauthorized mutation | Prevented by deterministic authorization |
| Duplicate refund under replay | Zero in fault-injection tests |
| Intent accuracy | ≥95% on the representative evaluation set |
| Policy answer correctness | ≥95% on supported policy scenarios |
| Unresolved cases | Explicitly escalated or identified |
| Routine conversational p95 | ≤5 seconds |
| Average AI inference cost | ≤€0.05/conversation |

These are illustrative engineering targets, not guarantees established by the architecture.

In particular, observing zero violations in tests doesn't prove their absolute impossibility. Security properties require strong enforcement mechanisms and continuing review.

### The release process

Every meaningful prompt, model, tool-schema, or retrieval change should run through a relevant evaluation suite.

High-risk mutations receive deterministic integration and fault-injection tests.

Model changes are compared against a pinned baseline using the same representative scenarios.

Canary rollout provides additional production evidence.

The goal isn't to maximize one aggregate quality score.

It's to prevent important regressions while improving business outcomes.

---

## 13. Operating the System: SLOs, Traces, and Costs

Our architecture should be observable from the beginning.

Every conversation receives a correlation identifier.

Agent runs receive stable execution IDs.

Mutating operations receive business operation IDs.

These identifiers allow an engineer to trace a customer complaint from the original message to the resulting database and provider records.

### Example trace

```text id="fy06mu"
conversation: conv_928

  intent_extraction
    model: fast-model-v3
    result: refund_inquiry

  reservation_lookup
    reservation: res_84721
    result: confirmation_pending

  payment_lookup
    payment: pay_442
    result: authorized

  investigation_agent
    tool_calls: 3
    result: reconciliation_required

  reconciliation
    status: awaiting_provider_confirmation

  customer_response
    outcome: unresolved
    escalation: support_queue
```

The trace should also include duration, resource usage, and relevant error categories.

Sensitive content needs appropriate handling.

### Business metrics

Measure:

- Verified conversation resolution rate.
- Human escalation rate.
- Wrong-intent classification rate.
- Unsupported policy claims.
- Unresolved financial operations.
- Duplicate-operation attempts.
- Cost per verified resolution.

The system may be technically available while delivering poor advice.

Therefore, infrastructure availability and semantic task quality must be monitored separately.

### Economics

Let's calculate an illustrative monthly inference budget.

Assume:

- 120,000 conversations.
- Average four model calls per conversation.
- Average 2,500 input tokens per call.
- Average 350 output tokens per call.

Suppose our hypothetical blended prices are:

- €0.70 per million input tokens.
- €2.80 per million output tokens.

Each call costs approximately:

**Input:** €0.00175

**Output:** €0.00098

**Total:** €0.00273

Four calls per conversation cost approximately €0.01092.

At 120,000 conversations, that is about **€1,310 per month in base inference usage**.

Real spending would be higher after accounting for complex investigations, retries, embeddings, reranking, infrastructure, and other services.

Still, the calculation suggests that model inference may be economically manageable.

### Where the real money is

Suppose a human-handled support conversation costs the business several euros in staff time.

Reducing unnecessary escalations can save considerably more than shaving a fraction of a cent from token costs.

But incorrect automation can create refunds, compensation claims, chargebacks, and reputational damage.

Therefore, we should optimize **cost per correct, completed customer outcome**, not merely cost per model request.

A more expensive model may be justified for complicated disputes.

A cheap model may be ideal for routine intent extraction.

And no model at all is preferable for exact database lookups and arithmetic.

---

## 14. The First Production Roadmap

We have an architecture, but we shouldn't implement everything simultaneously.

The company has eight engineers.

We need a sequence that delivers value while controlling risk.

### Phase 1 — Reliable read-only assistance

Implement:

- Structured intent extraction.
- Authorized reservation lookups.
- Hotel-policy retrieval.
- Source-backed answers.
- Basic escalation.
- Tracing and evaluation infrastructure.

No autonomous mutations.

This phase establishes whether AI can reliably reduce information-retrieval workload.

### Phase 2 — Prepared business operations

Add modification quotes, cancellation proposals, and refund-review requests.

The model interprets the user's request.

Trusted services validate and prepare operations.

Users or authorized support staff approve consequential actions.

### Phase 3 — Durable execution

Introduce persistent operation state, queue-backed execution, outbox publishing where necessary, idempotency, reconciliation, and fault-injection testing.

Only after these mechanisms are trustworthy should the system execute additional business operations.

### Phase 4 — Bounded investigations

Introduce an agent capable of investigating complicated reservation and payment issues using read-only tools.

Limit model calls, tool calls, duration, and cost.

Evaluate complete trajectories.

### Phase 5 — Optimize using evidence

Measure real outcomes.

Potential improvements might include:

- Better retrieval.
- More selective model routing.
- More effective context compaction.
- Specialized investigative tools.
- A dedicated MCP interface for external AI clients.
- Parallel specialist investigations.

Each should have a measurable justification.

The roadmap deliberately postpones several fashionable technologies.

That isn't conservatism for its own sake.

It's reducing complexity until we have evidence that additional complexity is worth paying for.

---

## 15. Architecture Review: The Principal Engineer's Interrogation

Our design is now on the table.

Imagine presenting it to a skeptical architecture review committee.

They ask several uncomfortable questions.

### Question 1: Why PostgreSQL instead of a dedicated vector database?

Because the expected policy-document volume is modest relative to the company's transactional workload.

PostgreSQL already exists, and pgvector can provide the initial retrieval capability.

This reduces operational complexity.

If retrieval scale, recall requirements, or latency eventually exceed what the design can provide economically, we can evaluate a dedicated search system.

The decision is reversible because retrieval is accessed through an application-level interface.

### Question 2: Why not fine-tune a model on every hotel's policies?

Because policy knowledge changes and requires provenance.

Fine-tuning is generally less convenient for rapidly changing factual documents, and it doesn't automatically provide source attribution.

RAG is better suited to retrieving applicable policy versions.

Fine-tuning might later improve specialized classification behavior or domain-specific output patterns.

### Question 3: Why aren't we using multiple agents?

Because the initial workflows don't demonstrate a need for independent specialist autonomy.

Most business operations follow known sequences.

A single bounded investigative agent is sufficient for our first open-ended use case.

We'll consider specialist workers if evaluations reveal measurable benefits from context isolation or parallel investigation.

### Question 4: Why not make the assistant fully autonomous?

Because the business requires strong guarantees around reservation and financial mutations.

Model autonomy is useful for interpreting language and investigating uncertainty.

It isn't a substitute for authorization, transactional correctness, approval, or reconciliation.

The system may eventually automate additional low-risk operations, but that expansion should be based on measured reliability and explicit business acceptance.

### Question 5: What happens if the model provider becomes unavailable?

Read-only reservation access and ordinary customer-service features remain available.

The application can temporarily disable AI-assisted interpretation, queue nonurgent work, or escalate to human support.

The core business shouldn't become unavailable merely because model inference is unavailable.

### Question 6: What happens when a payment refund succeeds but the worker crashes?

The operation remains durably recorded with a stable business identity.

Recovery reconciles the provider state before deciding whether any retry is appropriate.

Queue redelivery cannot simply create a new refund.

This is enforced by the application workflow, not by the model.

### Question 7: What is the biggest architectural risk?

Not model hallucination in isolation.

The greatest risk is allowing model-generated conclusions to acquire business authority without independent verification.

That can manifest as unauthorized tool execution, stale-state decisions, incorrect policy application, or duplicated external mutations.

Our architecture should therefore preserve a clear boundary between probabilistic interpretation and authoritative execution.

---

## 16. Final Workshop: Defend the Design Under Changing Requirements

Let's challenge the architecture with five new requirements.

### Challenge A — Tenfold growth

Harbor signs a major European hotel group.

Conversation volume rises from 120,000 to 1.2 million per month.

What should scale first?

Would you introduce microservices, Kubernetes, a dedicated vector database, or something else?

### Challenge B — Fully automated refunds

Management wants the assistant to refund customers automatically when eligibility is obvious.

What additional guarantees and operational controls would you require?

### Challenge C — External AI clients

Several hotel partners want to connect their own AI assistants to Harbor's reservation and policy capabilities.

Should we introduce MCP?

What would its security architecture look like?

### Challenge D — Complicated incidents

The single investigative agent performs poorly on incidents requiring simultaneous analysis of payments, bookings, and infrastructure.

Would a multi-agent architecture help?

How would you decide?

### Challenge E — The model upgrade

A new model performs better on public benchmarks but costs twice as much and generates more tool calls.

Would you migrate?

What evidence should determine the decision?

---

## 17. Workshop Solutions and Discussion

### Solution A — Find the bottleneck before changing architecture

A tenfold traffic increase doesn't automatically require microservices or Kubernetes.

First, measure the actual bottlenecks.

Model-provider quotas, PostgreSQL connection limits, external reservation APIs, queue throughput, or worker concurrency may constrain the system before the application compute layer does.

Scale independently where necessary.

For example, background workers can scale separately from request handlers.

Introduce caching for genuinely cacheable data, enforce provider-aware rate limits, and examine database query plans and connection pooling.

A dedicated search service may become justified if retrieval requirements demand it.

But architectural changes should follow measured constraints, not a ceremonial traffic threshold.

### Solution B — Automate only under explicit business conditions

For autonomous refunds, define a narrowly permitted category of operations.

For example, perhaps refunds below a certain threshold can execute automatically when the reservation is definitively canceled, payment capture is confirmed, the applicable policy is unambiguous, and no previous refund exists.

Those conditions must be enforced deterministically.

The system also needs stable operation identities, audit records, reconciliation, fraud and abuse controls, rate limits, and a mechanism to disable automation rapidly.

Human review should remain available for ambiguous or exceptional cases.

The model can recommend a refund.

The backend must prove that the specific refund satisfies the automatic-execution policy.

### Solution C — MCP becomes appropriate for reusable integration

With several independent external AI hosts, a standardized integration surface becomes valuable.

We could expose selected reservation, policy, and quote capabilities through an MCP server.

Each client would authenticate through a supported authorization mechanism.

The server would enforce tenant scope, user permissions, resource ownership, rate limits, and output minimization.

Sensitive mutations would remain behind the same approval and workflow controls.

MCP standardizes discovery and invocation.

It doesn't grant permission merely because a model can see a tool.

### Solution D — Evaluate specialization before adopting it

First, examine why the single agent fails.

Is its context too large? Does it confuse payment and reservation evidence? Does it fail to inspect necessary sources?

If the incident naturally decomposes into independent investigations, specialist agents may help.

We could run payment, reservation, and infrastructure investigators concurrently, then combine structured findings.

But compare this approach against deterministic parallel retrieval and a single strong synthesis model.

Measure correctness, latency, token consumption, and coordination errors.

A multi-agent system is justified only if its benefits exceed its additional complexity.

### Solution E — Application evaluations outweigh generalized benchmarks

Public benchmarks can identify promising models, but Harbor should evaluate the candidate on its own tasks.

Compare intent accuracy, policy interpretation, tool-selection correctness, end-to-end task success, latency, and cost.

Use paired cases and repeated trials where necessary.

Inspect whether the extra tool calls reflect useful investigation or unnecessary wandering.

A model costing twice as much might still be economical if it meaningfully reduces expensive support failures.

But if the improvement is mostly stylistic, we should probably retain the existing model.

**The best model is the one that satisfies the product's requirements at an acceptable total cost—not the one with the most impressive benchmark score.**

---

## 18. The Final Architecture

Let's bring everything together.

Our production design is not one enormous autonomous agent.

It is a conventional SaaS application with carefully bounded AI capabilities.

```text id="76ayiu"
                      CUSTOMERS
                         |
                         v
                  Vue 3 Frontend
                         |
                         v
                API Gateway / BFF
                         |
                         v
               Application Backend
                         |
        +----------------+-----------------+
        |                |                 |
        v                v                 v
   Authentication   Conversation       Domain Services
                    Management              |
                         |                  |
                         v                  |
                  AI Application            |
                         |                  |
             +-----------+----------+       |
             |           |          |       |
             v           v          v       |
          Context      Model      Tool      |
          Builder     Gateway    Registry   |
             |           |          |       |
             |           |          +-------+
             |           |
             |           v
             |      Model Provider
             |
        +----+----------------------+
        |                           |
        v                           v
   Retrieval Service          Structured State
        |                           |
        v                           v
   PostgreSQL/pgvector          PostgreSQL
        |
        v
   Document Storage / S3


              DURABLE EXECUTION LAYER

        Operation Store / Outbox
                    |
                    v
                  Queue
                    |
                    v
                 Workers
                    |
         +----------+----------+
         |                     |
         v                     v
   Reservation APIs       Payment APIs
         |                     |
         +----------+----------+
                    |
                    v
            Reconciliation
                    |
                    v
          Authoritative Outcome


             CROSS-CUTTING CONTROLS

     Authorization / Tenant Isolation
     Structured Validation / Approvals
     Rate Limits / Execution Budgets
     Logs / Metrics / Traces
     Evaluation / CI/CD / Rollback
```

Every component has a clear reason to exist.

The model gateway provides flexibility across model configurations.

The retrieval system supplies relevant reference knowledge.

The tool registry exposes carefully selected business capabilities.

Domain services enforce invariants.

Persistent operation state makes long-running workflows recoverable.

Queues separate background execution from interactive requests.

Evaluation provides evidence of semantic quality.

Observability explains what happened.

And authorization remains independent of the language model.

### What we deliberately did not build

We did not introduce a multi-agent hierarchy, dedicated vector database, Kubernetes cluster, universal MCP gateway, fine-tuned foundation model, or elaborate semantic-memory platform.

None is inherently bad.

None is currently necessary.

Each can be introduced when a concrete requirement justifies it.

The architecture is intentionally evolutionary.

It provides a useful initial product while preserving room for future specialization.

---

## Mental Model

A production agentic SaaS is not an LLM surrounded by API calls.

It is a conventional distributed application that delegates selected interpretation and decision-making tasks to probabilistic models while preserving authoritative business state, execution controls, and operational guarantees.

The most important architectural decision is determining **which responsibilities benefit from model-driven flexibility and which must remain deterministic**.

Build around verified state, explicit boundaries, durable operations, meaningful evaluations, and measurable business outcomes.

**Senior AI engineering is not about giving agents maximum autonomy. It is about giving software the minimum uncertainty necessary to solve problems that deterministic systems alone cannot handle effectively.**


---

## Next Steps — Beyond the Core Curriculum

The core catalogue is complete. Continue with planned electives (see `curriculum.yaml` / `curriculum.md`), revisit studio workshops, or apply the material in interviews and production work.

## Further Reading

1. **Anthropic — Building Effective Agents**  
   A practical explanation of agent and workflow architectures, emphasizing justified complexity, composable patterns, and selective autonomy.  
   https://www.anthropic.com/engineering/building-effective-agents

2. **OpenAI — A Practical Guide to Building Agents**  
   Guidance on agent design, tools, guardrails, orchestration, and selecting appropriate levels of autonomy.  
   https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/

3. **OpenAI — Evaluating Agent Workflows**  
   Current reference for evaluating agent behavior, execution traces, tool usage, and quality regressions.  
   https://developers.openai.com/api/docs/guides/agent-evals

4. **AWS — Amazon SQS Standard Queues**  
   Official documentation on at-least-once delivery, duplicate messages, throughput, and background-workload design.  
   https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html

5. **Stripe — Idempotent Requests**  
   A concrete reference for understanding safe retries and the limitations of external payment-operation idempotency.  
   https://docs.stripe.com/api/idempotent_requests

6. **OWASP — Top 10 for Agentic Applications 2026**  
   A security framework addressing the risks of autonomous systems, tool access, memory, privilege boundaries, and cross-system operations.  
   https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

7. **LangGraph — Thinking in LangGraph**  
   Useful guidance for modeling durable workflows, state transitions, model-powered decisions, and human-intervention points.  
   https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph

8. **Microsoft Azure — Retrieval-Augmented Generation Overview**  
   A practical reference for document ingestion, retrieval architecture, ranking, and grounding generated answers in external information.  
   https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview

---


