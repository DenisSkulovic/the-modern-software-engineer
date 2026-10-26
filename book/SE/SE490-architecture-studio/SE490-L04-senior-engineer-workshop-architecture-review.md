---
id: SE490-L04
course: SE490
title: "Senior Engineer Workshop: Architecture Review"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S12]
prev: SE490-L03
next: SE490-L05
---



# SE490 — Architecture and Systems Design Studio

## Lecture 04: Senior Engineer Workshop: Architecture Review

*An application that works, a company that is growing, and an architecture that is quietly becoming a liability. Your job is to decide what actually needs fixing.*

---

## 1. Congratulations, You're Now Responsible

It's Monday morning, and you've just joined a European SaaS company as its new senior software engineer.

The company operates **Mercury**, a platform serving independent hotels and small hotel chains. Mercury provides reservation management, payment processing, guest communications, analytics, and integrations with external property-management systems.

The business is doing well.

Revenue has grown steadily, customer retention is healthy, and the platform now serves 650 hotels across fourteen countries. Management expects the customer base to double over the next eighteen months.

But the engineering organization is struggling.

Deployments have become unpredictable. Several customers have reported duplicate invoices, API latency occasionally spikes above ten seconds, and a recent PostgreSQL outage caused nearly an hour of disruption.

The chief technology officer has a plan:

> "We need to modernize. Kubernetes, microservices, event-driven architecture, proper CI/CD. The whole thing. We're growing fast, and the current system obviously can't scale."

You have been asked to conduct an architecture review and recommend what the company should do.

Your first instinct might be to inspect the source code.

That's reasonable, but insufficient.

Architecture reviews aren't coding-style inspections. They investigate how technical structures interact with business requirements, operational risks, engineering capacity, and the system's expected evolution.

Before recommending anything, you need to understand what you're dealing with.

---

## 2. The System on the Whiteboard

The engineering team provides the following architecture diagram.

```text
                         Customers
                             │
                             ▼
                          CloudFront
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
                Vue Frontend      API Gateway
                                      │
                                      ▼
                               Node.js Lambdas
                                      │
                ┌─────────────────────┼───────────────────┐
                ▼                     ▼                   ▼
             PostgreSQL             Redis            External APIs
                │                     │               ├── Payments
                │                     │               ├── Hotel PMS
                ▼                     ▼               └── Email
           RDS Multi-AZ           BullMQ Jobs
                                      │
                                      ▼
                                 EC2 Workers

                         S3: Documents and Images
```

At first glance, nothing looks outrageous.

The frontend is delivered through CloudFront. Lambda handles HTTP requests, PostgreSQL stores transactional data, Redis supports caching and background processing, and S3 stores documents.

There is no obvious reason why this architecture couldn't serve a successful SaaS.

The problem emerges when you investigate the relationships between its components.

### Application structure

The backend repository contains:

```text
src/
├── controllers/
├── services/
│   ├── BookingService.ts
│   ├── PaymentService.ts
│   ├── BillingService.ts
│   ├── CustomerService.ts
│   └── IntegrationService.ts
├── repositories/
├── entities/
├── workers/
├── utils/
└── aws/
```

The `BookingService` is approximately 2,800 lines long.

It imports repositories, payment-provider clients, billing utilities, and notification functions directly. Several workers modify booking and payment entities without going through the corresponding domain services.

The TypeORM entities are imported throughout the application, including into HTTP response construction and external integration code.

### Deployment structure

GitHub Actions builds and deploys Lambda functions whenever changes reach `main`.

The API and workers have separate workflows.

Database migrations execute during application initialization, and several Lambda functions can attempt migration checks simultaneously.

Application versions are tracked by Git commit, but there is no centralized record connecting deployed versions, migration state, worker versions, and configuration changes.

### Infrastructure

The production PostgreSQL instance is moderately provisioned, with CPU utilization usually below 35%.

Database connections occasionally approach the configured maximum.

Lambda concurrency can expand rapidly, and each warm execution environment maintains its own TypeORM connection pool.

Redis runs on a small EC2 instance without a documented recovery procedure.

Background workers share the Redis instance with application caching.

### Security

The API authenticates users through JWTs.

However, several repository methods accept only a resource ID, and tenant ownership is verified inconsistently.

The application Lambda execution role has broad S3 access.

Most third-party credentials are stored in environment variables, with rotation handled manually.

### Operations

The team collects CloudWatch logs and basic infrastructure metrics.

It does not have consistent distributed tracing or structured correlation between HTTP requests and background jobs.

Alerts primarily monitor CPU, memory, Lambda errors, and application availability.

There are automated database backups, but nobody remembers the last complete restoration test.

We now have an architecture worth investigating.

But we still shouldn't start redesigning it.

---

## 3. Establish the Business Constraints

You meet the CTO, product manager, and engineering lead.

Their requirements are more useful than the architecture diagram.

**Business objectives:**

- Support approximately twice the current customer base within eighteen months.
- Reduce customer-visible incidents.
- Maintain frequent feature delivery.
- Expand corporate billing and supplier integrations.
- Avoid a prolonged migration that delays product development.

**Engineering constraints:**

- Seven backend engineers.
- Three frontend engineers.
- One engineer primarily responsible for infrastructure.
- No dedicated security or SRE team.
- Limited experience operating Kubernetes.
- Approximately six weeks available for initial reliability improvements.

**Operational requirements:**

- Core booking operations should meet a 99.9% monthly request-success objective.
- Important data must remain recoverable after infrastructure failure.
- Payment and invoice duplication must be prevented.
- Tenant data must remain isolated.
- The company cannot tolerate a multi-month feature freeze.

Notice what isn't present.

Nobody has established that Kubernetes is required.

Nobody has demonstrated that independent microservice deployment would improve delivery speed.

Nobody has shown that Lambda itself is incapable of supporting future traffic.

The business needs a more reliable, maintainable platform.

Technologies are possible ways to achieve that outcome, not the outcome itself.

### Distinguish constraints from assumptions

Management believes customer growth requires microservices.

But doubling customers doesn't necessarily double peak requests, database workload, or infrastructure cost.

A hotel may generate hundreds of API operations daily or thousands, depending on its integration model.

Before planning for growth, we need workload measurements.

Similarly, the existence of a large service class doesn't automatically prove that splitting it into another process is necessary.

It may indicate a domain-boundary problem that can be corrected within the existing deployment model.

**A senior engineer turns architectural opinions into testable hypotheses.**

---

## 4. Collect Evidence Before Proposing Solutions

You request incident reports, deployment histories, database statistics, and representative source-code changes from the previous three months.

Several findings emerge.

### Finding A — Latency spikes

The booking API's normal p95 latency is approximately 240 milliseconds.

Its p99 occasionally exceeds eight seconds.

During these incidents:

```text
PostgreSQL CPU:                  28%
Active database connections:    Near maximum
Lambda concurrency:             Elevated
Connection acquisition delay:   Several seconds
```

The most important clue is that PostgreSQL CPU remains relatively low while connection acquisition becomes slow.

This suggests connection pressure rather than necessarily insufficient query-processing capacity.

A trace from one slow request shows:

```text
GET /reservations/:id          8,740 ms
│
├── Authentication                12 ms
├── Acquire DB connection      8,490 ms
├── Execute SQL                   31 ms
└── Serialize response            14 ms
```

The missing time has an explanation.

But the next question is why connections are unavailable.

### Finding B — Worker interference

Several background workers maintain database transactions while calling external hotel suppliers.

A representative implementation:

```typescript
await dataSource.transaction(async (manager) => {
  const booking = await manager.findOneBy(
    BookingEntity,
    { id: bookingId }
  );

  const status = await supplier.getBookingStatus(
    booking.externalId
  );

  booking.supplierStatus = status;

  await manager.save(booking);
});
```

When supplier responses are slow, transactions retain their database connections longer than necessary.

This contributes to connection pressure.

The architectural failure isn't that PostgreSQL is too small. It's that application resource ownership extends across an unpredictable external operation.

### Finding C — Duplicate invoices

A BullMQ worker performs:

```typescript
const existing = await invoiceRepository.findByBookingId(
  bookingId
);

if (!existing) {
  await invoiceRepository.createInvoice(bookingId);
}
```

There is no database uniqueness constraint preventing duplicate invoices for the same logical billing obligation.

During retries or concurrent execution, both workers can observe no existing invoice.

The issue is an unenforced business invariant.

Increasing worker capacity would make this problem more likely to appear, not less.

### Finding D — Deployment incidents

Three recent incidents involved incompatible application and database versions.

In one case, new Lambda functions expected a column before the migration completed.

In another, a worker continued using an old event representation after the API producer changed its payload.

These problems concern release coordination and compatibility.

They are not caused by the absence of Kubernetes.

### Finding E — Tenant isolation risk

Several endpoints retrieve records using:

```typescript
repository.findOneBy({ id });
```

The team explains that the frontend normally supplies IDs belonging to the current tenant.

This is an authorization defect.

The frontend cannot enforce a backend security boundary.

Unlike some performance improvements, this finding doesn't require additional load measurements before action.

You have identified a credible path to cross-tenant data disclosure.

It deserves immediate remediation and an investigation into whether unauthorized access has occurred.

---

## 5. Risk Ranking: What Matters Most?

The CTO wants a modernization roadmap.

You now have enough information to distinguish architectural problems by their likely consequences.

A reasonable preliminary ranking is:

| Finding | Consequence | Priority |
|---|---|---|
| Inconsistent tenant authorization | Cross-customer data exposure | Critical |
| Duplicate-invoice race | Financial correctness violations | Critical |
| Unsafe schema deployment | Customer-facing outages | High |
| Connection starvation | Severe latency and potential cascading failure | High |
| Untested database recovery | Uncertain recoverability | High |
| Poor tracing | Slower diagnosis | Medium–high |
| Shared Redis workloads | Possible resource interference | Medium |
| Large service classes | Increasing development friction | Medium |
| Lack of Kubernetes | No demonstrated harm | None |

This is not a universal severity scoring system. The priorities reflect the evidence and assumptions in this case.

Several findings deserve attention immediately because their risk is already established.

Others require further measurement.

The important distinction is between **known correctness failures**, **credible operational risks**, and **architectural preferences without demonstrated value**.

A senior engineer should be able to make that distinction without becoming emotionally attached to a preferred technology stack.

---

## 6. Immediate Priority: Protect Tenant Boundaries

The tenant authorization defect is the first issue I'd address.

Not because it is the most intellectually interesting, but because it can expose customer data during ordinary authenticated usage.

### Define an explicit authorization context

Instead of relying on arbitrary request parameters, establish a trusted application context:

```typescript
type AuthorizedContext = {
  userId: string;
  tenantId: string;
  permissions: ReadonlySet<string>;
};
```

This context is created after validating authentication and confirming the user's membership and active tenant.

The application should not accept an arbitrary `tenantId` from a frontend request as authoritative.

### Scope resource access

A reservation query becomes:

```typescript
async function getReservation(
  context: AuthorizedContext,
  reservationId: string
) {
  if (!context.permissions.has("reservation:read")) {
    throw new ForbiddenError();
  }

  return reservationRepository.findOneBy({
    id: reservationId,
    tenantId: context.tenantId
  });
}
```

This enforces both a capability check and tenant ownership.

The production design may centralize these policies or use additional database-level enforcement, but every sensitive access path must be covered.

### Audit the broader system

Fixing one endpoint isn't enough.

Review:

- Reservation APIs.
- Invoice and payment APIs.
- Document downloads.
- Administrative operations.
- Background jobs.
- Export endpoints.
- Cache keys.
- Supplier integration callbacks.

Cross-tenant isolation is a system-wide invariant.

The immediate remediation should include authorization regression tests and, where appropriate, database-level safeguards such as PostgreSQL Row-Level Security.

The team should also review access logs to determine whether suspicious cross-tenant requests occurred, recognizing that available logs may not conclusively establish historical access.

---

## 7. Second Priority: Make Financial Invariants Enforceable

The duplicate-invoice problem is another established correctness failure.

The existing code relies on application-level read-before-write logic.

That is insufficient under concurrency.

### Establish the actual business invariant

Before adding a constraint, determine what constitutes a duplicate.

A booking may legitimately produce several invoices:

- An original invoice.
- A corrected invoice.
- Additional charges.
- A separate invoice for another billing period.

Therefore, simply enforcing uniqueness on `booking_id` may be incorrect.

Suppose the business defines one invoice per booking and billing period.

Then the database could enforce:

```sql
ALTER TABLE invoices
ADD CONSTRAINT unique_booking_period_invoice
UNIQUE (booking_id, billing_period_id);
```

The exact key must match the business meaning.

The application can use a transactional insert or conflict-handling strategy to make repeated execution safe.

### Introduce durable publication

If invoice creation triggers an event, the database write and event intent should remain consistent.

A transactional outbox is a reasonable fit.

```text
PostgreSQL Transaction
    │
    ├── Insert Invoice
    ├── Insert Outbox Event
    └── Commit
              │
              ▼
       Outbox Dispatcher
              │
              ▼
          Job Queue
```

The dispatcher may retry publication, and consumers must tolerate duplicate delivery.

This doesn't create magical exactly-once behavior across independent systems.

It establishes durable local consistency and provides a manageable way to recover from partial failure.

### Test the actual race

The team should add integration tests using real PostgreSQL.

Execute concurrent attempts to create the same logical invoice, then verify that the database contains one authoritative record and the downstream workflow produces one logical billing effect.

Also test failure after transaction commit but before job acknowledgment.

This improvement addresses a proven business defect. It should take precedence over reorganizing service directories.

---

## 8. Third Priority: Make Deployments Compatible

The next major risk is deployment safety.

The current system treats application releases, worker releases, and database migrations as loosely coordinated operations.

That is dangerous because persistent state is shared across concurrently running versions.

### Remove migration ownership from application startup

Database migrations should execute through a controlled release step or dedicated migration job.

Multiple Lambda execution environments should not independently decide to mutate production schema during initialization.

The release process needs a clear owner for schema evolution.

### Adopt expand-and-contract migrations

For a column rename, avoid immediately deleting the old representation.

Instead:

```text
Release A
    Expand schema with compatible new structures

Release B
    Deploy code capable of handling both representations

Migration
    Backfill and verify historical data

Release C
    Move authoritative reads and writes

Release D
    Remove obsolete structures after consumers migrate
```

Intermediate states must remain compatible with active API and worker versions.

This requirement is particularly important for queues, where delayed messages may remain in circulation after a producer changes its schema.

### Promote identifiable artifacts

The team should record which immutable application artifacts are deployed.

A release record should connect:

```text
Release ID
    ├── API image or Lambda artifact
    ├── Worker artifact
    ├── Database schema version
    ├── Configuration revision
    └── Feature flags
```

This makes rollback decisions more informed.

Restoring an older application artifact is safe only if that artifact remains compatible with the current persistent state.

### Add production verification

A successful deployment should be followed by meaningful checks:

- Core booking endpoint health.
- Database error rate.
- Reservation creation success.
- Invoice-processing failures.
- Queue backlog age.
- Application latency distributions.

A release pipeline that reports success while customers cannot create bookings is measuring the wrong outcome.

---

## 9. Fourth Priority: Contain Connection Pressure

Now we can address the performance problem.

The system currently combines rapidly scaling Lambda execution environments with a finite PostgreSQL connection budget.

Some background workers also retain connections during slow external calls.

These behaviors create a dangerous resource relationship.

### First, fix unnecessary connection ownership

Remove external supplier calls from database transactions where business correctness allows it.

For example:

```typescript
const booking = await bookingRepository.findById(bookingId);

const supplierStatus = await supplier.getBookingStatus(
  booking.externalId
);

await bookingRepository.updateStatusConditionally({
  bookingId,
  expectedVersion: booking.version,
  supplierStatus
});
```

The conditional update protects against overwriting state that changed while the supplier call was in progress.

The exact implementation should reflect the domain's state-transition rules.

This reduces the time database connections remain occupied.

### Then control aggregate concurrency

Investigate:

- Lambda concurrency.
- Per-environment connection-pool sizing.
- Database connection limits.
- Worker concurrency.
- Connection acquisition latency.
- Database CPU and I/O saturation.

RDS Proxy may help manage connection pressure from Lambda execution environments.

But proxying doesn't increase PostgreSQL's fundamental query-processing capacity, and transaction/session behavior can limit connection multiplexing.

A smaller aggregate connection budget, improved connection reuse, and controlled concurrency may provide more immediate benefit.

### Why not simply upgrade PostgreSQL?

Increasing database capacity might provide headroom.

But if the application holds connections while waiting for ten-second supplier responses, upgrading the database doesn't correct that misuse.

The right sequence is to eliminate avoidable resource occupation, establish admission control, measure the remaining bottleneck, and only then purchase additional capacity where justified.

Cloud resources are not a substitute for understanding resource lifetimes.

---

## 10. Fifth Priority: Make Recovery Credible

The platform uses RDS Multi-AZ and automated backups.

That's useful, but the company has no recent evidence that it can recover its complete application state within an acceptable time.

### Define recovery objectives

Suppose management agrees on:

```text
Core booking RTO:       60 minutes
Booking database RPO:    5 minutes
```

These are illustrative targets requiring validation against the business's actual tolerance.

The engineering team should test whether its recovery mechanisms can meet them.

### Perform a restoration drill

In an isolated environment:

1. Restore a recent database backup or available recovery point.
2. Verify critical schemas and records.
3. Launch compatible application code.
4. Reconnect essential infrastructure.
5. Execute representative booking operations.
6. Measure elapsed restoration time.
7. Identify data requiring reconciliation.

A critical detail is external state.

If a customer paid through a payment provider shortly before a failure, the system must reconcile that financial outcome with the restored booking records.

Database restoration alone cannot reconstruct every external side effect.

### Investigate Redis recovery separately

Redis currently supports both caching and BullMQ background jobs.

Those workloads have different durability requirements.

Losing cached data may merely reduce performance temporarily.

Losing important job state can affect business processing.

The team should determine whether current persistence and recovery arrangements satisfy the queue's actual reliability requirements.

If important jobs must survive specific failure scenarios, the architecture needs tested recovery guarantees—not just a Redis process that normally stays running.

---

## 11. Observability: Fix the Blind Spots, Not Every Dashboard

The team currently monitors CPU, memory, basic Lambda errors, and overall availability.

Those measurements are useful but insufficient.

The recent latency incident demonstrated that healthy-looking CPU graphs can coexist with severe connection starvation.

A targeted observability improvement should instrument the critical request and job paths.

### Trace one reservation end to end

```text
HTTP Request
     │
     ▼
Booking API
     │
     ├── Authentication
     ├── Database Connection Acquisition
     ├── PostgreSQL Query
     ├── Supplier Request
     └── Response
```

For asynchronous work, propagate suitable trace or business correlation context into BullMQ jobs.

The objective is to connect a customer-visible operation to the background work and dependencies it triggers.

### Track meaningful metrics

A useful initial set might include:

| Measurement | Why it matters |
|---|---|
| Booking request success rate | Customer impact |
| Booking latency p95/p99 | Tail performance |
| Database pool wait duration | Connection starvation |
| PostgreSQL active connections | Capacity pressure |
| Supplier request latency | External dependency behavior |
| Invoice duplicate/conflict events | Financial correctness |
| Queue oldest-job age | Processing delay |
| Worker retry rate | Background failure patterns |

Not every metric belongs in a paging alert.

Alerts should focus on meaningful user impact, rapidly deteriorating reliability, and actionable resource exhaustion.

### Avoid observability overengineering

The team doesn't need twenty dashboards and a self-hosted telemetry platform merely to prove engineering sophistication.

Managed monitoring services or a modest OpenTelemetry-based deployment may be sufficient.

Start with measurements that make known incidents easier to detect and diagnose.

Expand instrumentation when questions emerge that existing evidence cannot answer.

---

## 12. Architectural Modularity: Improve the Code Without Distributing It

So far, our most urgent improvements have addressed security, financial correctness, deployment safety, performance, and recovery.

Now we can discuss the maintainability problem.

The backend contains oversized services, unclear ownership, and cross-module persistence access.

Should it become microservices?

Not yet.

### Establish domain ownership

A reasonable modular structure might be:

```text
src/
├── modules/
│   ├── reservations/
│   │   ├── application/
│   │   ├── domain/
│   │   ├── persistence/
│   │   └── index.ts
│   ├── payments/
│   ├── billing/
│   ├── customers/
│   └── integrations/
├── shared/
└── composition/
```

The objective isn't to replace every file at once.

Instead, identify the most frequently modified workflows and clarify which module owns each important state transition.

For example:

- Reservations own reservation lifecycle rules.
- Payments own payment attempts and provider outcomes.
- Billing owns invoices and financial obligations.
- Integrations translate external supplier protocols.
- Notifications own communication delivery.

Cross-module operations should use explicit application capabilities.

### Don't create a universal abstraction framework

The team currently has two payment providers and four hotel supplier integrations.

It may benefit from stable interfaces around those external systems.

But constructing a generic plugin framework for every future supplier would be speculative.

A small, well-defined adapter boundary is more valuable than an elaborate framework designed for imaginary integrations.

### Enforce important dependencies

Architecture tests or static analysis can prevent modules from importing one another's internal persistence implementation.

But the rules should reflect actual ownership.

A directory reorganization that merely moves the 2,800-line `BookingService` into `reservations/application` hasn't solved anything.

The success criterion is whether future changes become more local and easier to reason about.

---

## 13. The Kubernetes Question

The CTO returns to the original proposal.

> "Fine, but surely we'll need Kubernetes when we double our customer base?"

Maybe.

But nothing in the investigation currently establishes that requirement.

The system already uses Lambda for HTTP execution and EC2 for workers.

Its observed failures involve:

- Database connection management.
- Incorrect business concurrency.
- Weak authorization.
- Unsafe deployments.
- Missing recovery verification.

Kubernetes would not automatically fix any of these.

It could introduce additional responsibilities involving cluster administration, workloads, networking, security policies, observability, and upgrades.

With one engineer primarily responsible for infrastructure, those responsibilities are not trivial.

### Could ECS/Fargate be useful?

Potentially.

The EC2 workers may benefit from a managed container execution platform that simplifies deployment, isolation, and scaling.

If the worker fleet has operational problems caused by host management, ECS/Fargate is worth evaluating.

But even that migration should be justified by measurable operational benefits.

The HTTP API might also eventually move from Lambda to persistent containers if workload characteristics favor stable connection pools, long-lived processes, or different cost economics.

That's a separate compute decision.

### A deliberately postponed technology list

For the initial roadmap, I would not recommend:

- Kubernetes.
- A service mesh.
- Splitting every module into microservices.
- A new database engine.
- A complete backend rewrite.
- Multi-region active-active deployment.
- An elaborate event-sourcing platform.
- A universal dependency-injection or plugin framework.

These technologies are not inherently bad.

They simply don't address the strongest evidence we currently have.

**Mature architecture is often defined as much by the complexity you refuse to introduce as by the technology you adopt.**

---

## 14. The Six-Week Improvement Roadmap

We have limited engineering capacity.

A useful roadmap needs a defensible order, clear ownership, and explicit success criteria.

The highest-risk findings should begin immediately, while longer-term design improvements can proceed incrementally.

| Period | Primary work | Expected outcome |
|---|---|---|
| Week 1 | Tenant authorization audit and urgent fixes; financial duplicate prevention | Close known data-exposure and billing correctness risks |
| Week 2 | Concurrency integration tests; controlled migration ownership | Prevent recurrent financial races and deployment conflicts |
| Week 3 | Fix long-lived transactions; introduce connection-pool measurements and concurrency limits | Reduce database connection starvation |
| Week 4 | Compatible release workflow; API and worker version tracking; smoke tests | Safer, more diagnosable deployments |
| Week 5 | Database restoration drill; Redis recovery assessment; incident runbooks | Establish credible recovery evidence |
| Week 6 | Targeted module refactoring; dependency rules; review remaining risks | Reduce change friction without a rewrite |

This is a planning framework, not a guarantee that every item will finish within six weeks.

Several activities should proceed in parallel where ownership and capacity allow.

For example, the immediate authorization fix need not wait for the deployment improvements.

Likewise, basic tracing around database connection acquisition can be introduced while investigating connection starvation.

### What does success look like?

The team should measure results rather than declaring success because the codebase looks cleaner.

Useful outcomes include:

- Unauthorized cross-tenant access tests consistently reject requests.
- Duplicate financial operations are prevented by database-enforced invariants.
- Critical releases support safe coexistence of application and schema versions.
- Connection acquisition latency remains acceptable under representative load.
- Recovery drills demonstrate actual RTO/RPO performance.
- Engineers can reconstruct important request and worker paths.
- Frequently changed modules require fewer unrelated modifications.

Some improvements reduce risk rather than producing an immediately visible performance gain.

That's fine.

But the team should know what risk it reduced and what evidence supports that conclusion.

---

## 15. Communicating the Review to Management

A senior engineer's responsibilities don't end with finding problems.

The recommendations must be understandable to people who don't want to discuss PostgreSQL connection pools for forty minutes.

Imagine you're presenting to the CTO and product manager.

A useful summary might be:

> Mercury's architecture remains viable for its current scale and likely near-term growth. The most serious problems are not insufficient orchestration or a lack of microservices; they are weaknesses in tenant authorization, financial invariants, release compatibility, resource management, and tested recovery.
>
> We recommend six weeks of targeted engineering improvements focused on reducing these risks. A complete rewrite or Kubernetes migration would consume substantial capacity without directly addressing the demonstrated failure modes.
>
> After these improvements, we'll reassess scaling and deployment needs using actual workload measurements and incident evidence.

This communicates three important things.

First, the platform isn't being dismissed as a hopeless legacy system.

Second, the risks are real and concrete.

Third, the proposed work serves business objectives rather than technological fashion.

### Make uncertainty explicit

Some decisions require additional evidence.

For example:

- Whether Lambda remains the most economical API compute model.
- Whether the PostgreSQL instance needs more capacity.
- Whether Redis workloads should be separated.
- Whether reporting deserves independent scaling.
- Whether certain modules should eventually become services.

These are legitimate open questions.

A senior engineer should distinguish what is known, what is inferred, and what needs measurement.

Confidence is not the same as pretending uncertainty doesn't exist.

---

## 16. Architecture Review as a Repeatable Method

Let's extract the reasoning method we've just used.

When reviewing an unfamiliar system, begin with the business.

What does the system accomplish? Which operations are essential? What consequences follow if they fail?

Next, examine structure.

Which modules own business rules and data? Where do dependencies cross boundaries? Which components can fail together?

Then inspect production evidence.

What incidents have occurred? Where is time spent? Which resources saturate? What repeatedly breaks during deployment?

Only after that should you propose changes.

### A practical sequence

```text
1. Establish business objectives and constraints
                  │
                  ▼
2. Map system components and ownership
                  │
                  ▼
3. Identify critical workflows and trust boundaries
                  │
                  ▼
4. Examine incidents, metrics, and change history
                  │
                  ▼
5. Rank risks by consequence and likelihood
                  │
                  ▼
6. Propose the smallest effective improvements
                  │
                  ▼
7. Define measurements and recovery options
                  │
                  ▼
8. Reassess after obtaining new evidence
```

This sequence doesn't imply that urgent known vulnerabilities should wait until a full review finishes.

Critical issues may require immediate containment while investigation continues.

The deeper principle is that architecture should be treated as a process of evidence-based decisions under constraints.

It isn't a static blueprint drawn once by somebody with an impressive job title.

---

## 17. Workshop — Your Own Architecture Review

Before reading the discussion, consider five additional scenarios involving Mercury.

### Challenge 1 — The Database Upgrade

After the initial improvements, PostgreSQL CPU reaches 75% during peak hours.

The CTO proposes doubling the instance size.

What additional evidence would you collect before approving the upgrade? Under what circumstances would scaling the database be the correct decision?

### Challenge 2 — The Microservice Extraction

The reporting module now consumes substantial CPU and occasionally delays API responses.

One engineer proposes extracting reporting into an independent microservice with its own database.

Would you approve the proposal? What smaller alternatives should be evaluated first?

### Challenge 3 — The Security Versus Velocity Conflict

A product manager wants to launch a new document-sharing feature within two weeks.

The proposed implementation uses presigned S3 URLs, but the team has not completed object-level authorization testing.

How would you respond?

### Challenge 4 — The Rollback Decision

A new booking API version is deployed.

It introduces a new reservation status and begins writing records using that value. A serious bug appears, and the previous API image is available for immediate rollback.

What should the incident team verify before restoring the older image?

### Challenge 5 — The Architecture Review Interview

An interviewer presents you with a diagram showing an API Gateway, six microservices, PostgreSQL, Redis, Kafka, Kubernetes, and a CDN.

They ask:

> "What do you think of this architecture?"

How should you respond without falling into either automatic praise or automatic criticism?

---

## 18. Workshop Solutions and Discussion

### Challenge 1 — CPU utilization isn't enough

A database operating at 75% CPU may be approaching a performance bottleneck, but that figure alone doesn't establish whether a larger instance is necessary.

I'd inspect query latency, wait events, I/O pressure, connection utilization, lock contention, throughput, and the relationship between load and customer-facing latency.

I'd also investigate expensive queries and missing indexes before purchasing capacity.

If the workload is genuinely CPU-bound after appropriate query optimization, increasing database capacity may be entirely reasonable.

The objective isn't to avoid cloud spending at all costs.

It's to spend money where capacity actually improves the required service behavior.

### Challenge 2 — Separate workload isolation from service decomposition

Reporting may need independent resource allocation.

But that does not automatically require its own authoritative database and microservice boundary.

A smaller first step could move expensive report generation into dedicated background workers with controlled concurrency.

The application might use asynchronous report requests, database read replicas where appropriate, or optimized reporting queries.

If reporting later requires independent ownership, deployments, scaling, and data models, service extraction may become justified.

The important distinction is between isolating a resource-intensive workload and creating a distributed business boundary.

### Challenge 3 — Authorization is a release requirement

Presigned S3 URLs are a useful mechanism for granting time-limited access to specific objects.

But the application must verify that the requesting user is entitled to receive the URL.

Without that check, the backend may generate valid download URLs for unauthorized users.

I'd require object-level authorization tests before enabling the feature for customers.

If the deadline is immovable, the team could reduce scope or deliver the implementation behind a disabled feature flag until the necessary controls are verified.

Security is not an optional enhancement to be added after customer data becomes exposed.

### Challenge 4 — Confirm backward compatibility

The previous application version may not understand the newly introduced reservation status.

Rolling back could cause it to reject records, misinterpret business state, or overwrite newer information incorrectly.

The incident team should establish whether the old version can safely read and write the current data representation.

If compatibility is uncertain, a forward fix or targeted compatibility patch may be safer than immediate rollback.

The team must also account for active workers, delayed messages, and external operations already completed by the new version.

Application rollback cannot automatically reverse persistent data changes.

### Challenge 5 — Ask what problem the architecture solves

I'd begin by asking about functional requirements, traffic patterns, reliability objectives, data consistency, team organization, and operational constraints.

Then I'd examine why the system has six microservices and Kafka.

Perhaps the architecture supports independent teams with substantial asynchronous workloads.

Perhaps it is an unnecessarily complicated implementation of a small CRUD application.

Both are plausible.

The diagram alone cannot establish which interpretation is correct.

A strong review identifies potential risks and asks targeted questions before making recommendations.

For example:

> "I'd investigate service boundaries, ownership of transactional data, consistency guarantees, deployment coupling, and the operational cost of the infrastructure. Whether this architecture is appropriate depends on the constraints it was designed to satisfy."

That's not evasive neutrality.

It's disciplined engineering judgment.

---

## Mental Model

A senior architecture review should establish:

1. **Business reality:** Which outcomes and constraints actually matter?
2. **System structure:** Where are the important responsibilities, dependencies, and failure domains?
3. **Evidence:** Which incidents, measurements, and development patterns reveal real problems?
4. **Risk:** What could cause the greatest harm, and how likely is it?
5. **Intervention:** What's the smallest effective improvement?
6. **Economics:** Does the benefit justify engineering effort, migration risk, and operational cost?
7. **Verification:** How will we know the improvement worked?

The most important principle of SE490 is this:

**Senior engineering isn't the ability to design the most sophisticated system. It's the ability to make the right technical decisions for the system, organization, and constraints that actually exist.**


---

## Next Lecture — SE490-L05: Architecture Workshop: Design a Production Agentic SaaS

Continue in **SE490 — Architecture and Systems Design Studio**.

## Further Reading

1. **AWS — [Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/)**. A systematic approach to evaluating operational excellence, security, reliability, performance, cost, and sustainability.

2. **Martin Fowler — [Architecture](https://martinfowler.com/architecture/)**. Articles exploring software architecture, modularity, architectural decisions, and evolutionary design.

3. **Simon Brown — [The C4 Model](https://c4model.com/)**. A practical approach to communicating system architecture at different levels of detail.

4. **Google — [Site Reliability Engineering](https://sre.google/sre-book/table-of-contents/)**. Production operations, reliability objectives, monitoring, incident response, and capacity management.

5. **Michael Nygard — *Release It!, Second Edition***. Production stability patterns, failure containment, and the practical consequences of architectural decisions.

6. **Mark Richards and Neal Ford — *Fundamentals of Software Architecture***. Architectural characteristics, structural patterns, trade-offs, and the skills involved in architecture evaluation.

7. **Neal Ford, Rebecca Parsons, and Patrick Kua — *Building Evolutionary Architectures***. Approaches to maintaining architectural fitness while systems and requirements evolve.

8. **John Ousterhout — *A Philosophy of Software Design***. Complexity management, abstraction, interfaces, and long-term maintainability.

9. **Martin Kleppmann — *Designing Data-Intensive Applications***. Distributed data systems, storage, consistency, replication, and the trade-offs behind dependable production architectures.

---


