---
id: SE440-L03
course: SE440
title: "Testing Strategies for Complex Systems"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S10]
prev: SE440-L02
next: null
---




# SE440 — Production Reliability and Quality Engineering

## Lecture 03: Testing Strategies for Complex Systems

*Why 95% test coverage can coexist with a spectacular production failure—and how to test the things that actually matter.*

---

## 1. The Application With 95% Coverage

Your company operates a subscription billing platform serving 40,000 businesses. It handles recurring payments, invoices, account upgrades, cancellations, and webhook notifications from several payment providers.

The engineering team takes testing seriously.

Every pull request runs hundreds of unit tests. GitHub Actions reports 95% statement coverage, and the main branch rarely contains failing tests.

The codebase has extensive mocks, a collection of integration tests, and several end-to-end scenarios executed before production releases.

Management is pleased.

Then a new application version goes live.

Within twenty minutes, customers begin reporting duplicate charges.

The incident investigation reveals that a payment-provider webhook is sometimes delivered twice. The backend processes both deliveries independently, generating two payment records and triggering duplicate downstream actions.

The surprising part is that the webhook handler has 100% unit-test coverage.

Here's one of its tests:

```typescript
it("processes a successful payment", async () => {
  paymentRepository.findByExternalId.mockResolvedValue(null);
  paymentRepository.save.mockResolvedValue(savedPayment);
  eventPublisher.publish.mockResolvedValue(undefined);

  await handler.handle(paymentSucceededEvent);

  expect(paymentRepository.save).toHaveBeenCalledTimes(1);
  expect(eventPublisher.publish).toHaveBeenCalledTimes(1);
});
```

The test is green.

It proves that when the repository reports no existing payment, the handler asks it to save a payment and publishes an event.

But consider two concurrent deliveries:

```text
Webhook A                         Webhook B
    │                                 │
    ▼                                 ▼
Check existing payment           Check existing payment
    │                                 │
    ▼                                 ▼
Not found                        Not found
    │                                 │
    ▼                                 ▼
Insert payment                   Insert payment
    │                                 │
    ▼                                 ▼
Publish event                    Publish event
```

Every individual operation behaves as expected.

The combined result is wrong.

The test suite never exercised concurrent processing against a real database with meaningful constraints. Its mocks always returned precisely the responses the test author expected.

The team had tested the implementation it imagined, not the system it operated.

**Test coverage measures which code executed during tests. It does not measure whether the tests examined the failure modes that matter.**

This session will examine how different testing techniques produce different kinds of evidence, why excessive mocking can conceal architectural problems, and how experienced engineers design tests around production risks rather than coverage percentages.

---

## 2. What Does a Passing Test Actually Establish?

A test is an experiment.

It establishes that a particular implementation, executed under specified conditions, produced an outcome satisfying selected assertions.

That sounds straightforward, but the qualifiers are crucial.

Consider:

```typescript
expect(calculateTotal(100, 20)).toBe(120);
```

If the test passes, we know the function returned 120 for those inputs in that execution environment.

We do not know that it handles every possible input correctly.

We do not know that it behaves correctly under concurrent execution, that its dependencies work in production, or that its underlying business requirements were correctly understood.

A test provides evidence about a defined behavior under defined conditions.

### Four important questions

When evaluating any test, ask:

1. **What behavior is being verified?**
2. **Which components are real, and which are substituted?**
3. **Which conditions and failure modes are exercised?**
4. **What class of defect would cause this test to fail?**

The fourth question is particularly revealing.

If a test would continue passing after introducing a serious business defect, its practical value may be limited.

For example, a test that merely checks whether a mocked repository method was called does not necessarily prove that a reservation was persisted correctly.

The assertion may be useful when verifying orchestration, but it isn't evidence of database correctness.

### Correctness has several dimensions

Software can fail in different ways:

- **Functional correctness:** The operation produces the wrong business result.
- **Integration correctness:** Components disagree about protocols, schemas, or behavior.
- **Concurrency correctness:** Individually valid operations interact incorrectly.
- **Operational correctness:** Deployment, configuration, and infrastructure prevent intended operation.
- **Security correctness:** Unauthorized behavior becomes possible.
- **Performance correctness:** The system violates latency or throughput requirements.
- **Resilience correctness:** Failures cause unacceptable data loss, duplication, or cascading outages.

Different tests address different dimensions.

No single testing technique provides complete confidence across all of them.

---

## 3. Unit Tests: Fast, Focused, and Easy to Misuse

Unit tests examine relatively small portions of application behavior.

A unit might be a function, class, domain object, or cohesive collection of closely related logic.

The important characteristic is controlled scope, not a universal rule that every test must exercise exactly one method.

Suppose our subscription domain supports suspension:

```typescript
class Subscription {
  constructor(
    private status: "ACTIVE" | "SUSPENDED" | "CANCELLED"
  ) {}

  suspend(): void {
    if (this.status !== "ACTIVE") {
      throw new Error("Only active subscriptions can be suspended");
    }

    this.status = "SUSPENDED";
  }

  getStatus() {
    return this.status;
  }
}
```

A useful unit test:

```typescript
it("rejects suspension of cancelled subscriptions", () => {
  const subscription = new Subscription("CANCELLED");

  expect(() => subscription.suspend()).toThrow(
    "Only active subscriptions can be suspended"
  );

  expect(subscription.getStatus()).toBe("CANCELLED");
});
```

This test verifies a meaningful invariant.

It doesn't need PostgreSQL, HTTP, Docker, or AWS.

Its execution is fast, deterministic, and easy to understand.

### Good unit tests examine behavior

Compare the previous test with:

```typescript
expect(subscriptionRepository.save)
  .toHaveBeenCalledWith(expectedObject);
```

The latter may verify something useful, but it is more closely coupled to implementation details.

A refactoring that preserves correct business behavior while changing persistence orchestration could break the test unnecessarily.

Ideally, unit tests express business guarantees:

> A cancelled subscription cannot be suspended.

Rather than incidental implementation details:

> The third internal helper must be called exactly once before the fourth helper.

There are exceptions. Interaction testing is appropriate when invoking a dependency is itself an essential part of the contract.

But tests that mirror implementation structure too closely become expensive to maintain.

### Unit tests are not necessarily isolated from all collaborators

Some engineers insist that every dependency must be mocked.

That is unnecessary.

A pure domain model may use real value objects, validators, and helper functions without compromising the usefulness of the unit test.

The goal is to keep the tested behavior understandable and controllable, not to replace every object with a mock merely because it exists in another file.

**Unit tests are most valuable for complicated deterministic logic whose correctness can be established without recreating a production environment.**

---

## 4. Test Doubles: Fakes, Stubs, Spies, and Mocks

The vocabulary around test doubles is occasionally inconsistent across frameworks, but several distinctions are useful.

A **stub** supplies predetermined responses.

A **fake** provides a simplified working implementation, such as an in-memory repository.

A **spy** records interactions.

A **mock**, in the stricter classical sense, represents expected interactions whose occurrence is verified.

In everyday TypeScript testing, developers often use *mock* to describe all these mechanisms.

That's fine conversationally, but understanding their different roles helps prevent misuse.

### Stubbing an external payment provider

Suppose we need to test a subscription activation use case without charging a real payment method.

We can provide:

```typescript
const paymentGateway = {
  charge: async () => ({
    transactionId: "test-transaction"
  })
};
```

This allows us to exercise the application workflow under a known payment outcome.

The test can then verify that successful payment leads to the appropriate state transition.

### Testing failure behavior

We can also simulate an unavailable provider:

```typescript
const paymentGateway = {
  charge: async () => {
    throw new Error("Payment provider unavailable");
  }
};
```

Now the application should handle the failure according to its business contract.

Perhaps the subscription remains pending and the operation records a retryable state.

The double makes otherwise difficult scenarios easy to reproduce.

### The danger: substitutes can lie

Suppose our fake repository stores objects in a JavaScript `Map`.

```typescript
class FakePaymentRepository {
  private payments = new Map<string, Payment>();

  async findByExternalId(id: string) {
    return this.payments.get(id) ?? null;
  }

  async save(payment: Payment) {
    this.payments.set(payment.externalId, payment);
  }
}
```

This fake may be useful for application-level tests.

But it does not reproduce PostgreSQL's transaction isolation, unique constraints, row locking, or failure behavior.

It may not even reproduce the exact semantics of its production repository.

A test passing against the fake doesn't prove that the real persistence implementation behaves identically.

The appropriate conclusion isn't that fakes are bad.

It is that **the scope of a test's evidence is bounded by the fidelity of its dependencies**.

Use substitutes to control selected behavior, and use real dependencies where their behavior is part of what you're trying to establish.

---

## 5. Integration Tests: Testing the Boundaries Where Assumptions Meet Reality

Integration tests exercise multiple components together.

A particularly valuable category verifies interaction with infrastructure whose semantics matter.

For a PostgreSQL-backed application, that means executing real SQL against a real PostgreSQL server rather than assuming an in-memory database behaves identically.

### The duplicate-payment example

We can enforce an important invariant in PostgreSQL:

```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY,
  provider TEXT NOT NULL,
  external_payment_id TEXT NOT NULL,
  amount_cents BIGINT NOT NULL,
  status TEXT NOT NULL,

  CONSTRAINT unique_provider_payment
    UNIQUE (provider, external_payment_id)
);
```

Now duplicate inserts for the same provider payment cannot both commit successfully.

This is stronger than relying exclusively on:

```typescript
const existing = await repository.findByExternalId(id);

if (!existing) {
  await repository.save(payment);
}
```

The read-then-insert sequence is vulnerable to concurrent execution.

A database uniqueness constraint establishes a concurrency-safe invariant at the authoritative persistence boundary.

### Test the constraint directly

An integration test can execute two inserts with the same external payment identity and verify that the database preserves uniqueness.

Better still, test the actual application repository using concurrent operations.

The expected result might be:

- One insert creates the record.
- The other operation recognizes the existing record or encounters a uniqueness conflict that the application handles correctly.
- Only one logical payment is recorded.

The exact implementation may use `INSERT ... ON CONFLICT`, transactional logic, or another appropriate database mechanism.

What matters is verifying the real behavior.

### Testcontainers

Tools such as Testcontainers can start disposable infrastructure for automated tests.

A Node.js test suite might launch a PostgreSQL container, apply migrations, execute tests, and discard the environment afterward.

This provides stronger fidelity than relying on an unrelated in-memory database implementation.

But a disposable PostgreSQL instance is still not identical to production.

Production may have different data volume, configuration, extensions, replication behavior, permissions, or concurrent workloads.

Integration testing narrows uncertainty. It does not eliminate it.

---

## 6. Testing External Integrations Without Calling the Real World Every Time

Payment systems, hotel suppliers, email providers, and external APIs introduce a different kind of uncertainty.

A test that calls a real supplier may be slow, expensive, nondeterministic, or capable of producing unwanted side effects.

But a test that replaces every supplier interaction with a perfect stub may never detect protocol incompatibilities.

A useful strategy separates several concerns.

### Test your own translation logic

Suppose a supplier returns:

```json
{
  "booking_state": "confirmed",
  "confirmation_reference": "HOTEL-19384"
}
```

Your adapter maps that response into an internal reservation status.

This translation can be unit-tested with representative supplier payloads.

Include missing fields, unexpected enum values, malformed responses, and known provider-specific quirks.

### Test HTTP behavior against a controlled server

A local HTTP test server can simulate real request and response behavior.

This verifies concerns such as:

- HTTP methods and paths.
- Headers and authentication formatting.
- Serialization and parsing.
- Timeouts.
- Non-2xx responses.
- Malformed bodies.
- Retryable versus nonretryable failures.

For TypeScript applications, libraries such as MSW, Nock, or a dedicated local test server can help, depending on the required level of fidelity.

### Test selected scenarios against provider sandboxes

A provider's sandbox environment can expose differences your local substitutes don't reproduce.

But sandboxes may behave differently from production in important ways.

They can have simplified data, simulated settlement, different limits, or incomplete failure scenarios.

Therefore, tests against provider sandboxes should supplement, rather than replace, local tests and production monitoring.

### Protect live systems

Never run destructive automated tests against real payment accounts or customer reservations without appropriate isolation and explicit safeguards.

Tests should use designated environments, credentials, accounts, and fixtures.

A testing system that occasionally charges customers or cancels legitimate reservations is not a successful quality-control system.

It's a new production incident generator.

---

## 7. Contract Testing: Discovering Disagreement Before Deployment

Consider two independently maintained services.

The booking API calls a customer service:

```http
GET /customers/123
```

The expected response is:

```json
{
  "id": "123",
  "name": "Alice",
  "billingEmail": "alice@example.com"
}
```

The customer service team changes the field to:

```json
{
  "id": "123",
  "name": "Alice",
  "contactEmail": "alice@example.com"
}
```

Their own tests pass.

The booking API's tests also pass because its mock still returns `billingEmail`.

Production fails when the new service version is deployed.

The problem is a broken **consumer-provider contract**.

### What contract tests establish

Contract tests verify compatibility between the expectations of a consumer and the behavior of a provider.

For example, the booking service may specify that it requires:

- A customer ID.
- A billing email field.
- Defined response behavior for missing customers.

The provider can verify that its implementation satisfies those expectations.

This is useful when services are independently deployed or maintained by separate teams.

### Consumer-driven contracts

In consumer-driven contract testing, consumers express the interactions they depend on.

A provider verifies those contracts as part of its build or release process.

Tools such as Pact support this workflow.

But contract testing doesn't prove complete business correctness.

A provider might return the expected JSON fields while containing incorrect customer data.

Similarly, a contract test may not detect a performance regression, authorization defect, or database failure.

A contract establishes compatibility of defined interactions—not that every possible operation behaves correctly.

### Contracts are broader than HTTP

A message published to SQS or EventBridge also has a contract.

Suppose the old event is:

```json
{
  "eventType": "ReservationConfirmed",
  "reservationId": "123"
}
```

A new producer changes `reservationId` to `bookingId` without coordinating with consumers.

Background workers may begin failing or silently ignore the event.

Event schemas, optional fields, versioning rules, and consumer tolerance are therefore part of integration testing.

Compatibility must be considered across deployment windows where different versions coexist.

---

## 8. End-to-End Tests: Verifying the Complete Journey

An end-to-end test exercises a realistic operation across several application boundaries.

For a hotel-booking SaaS:

```text
Browser
   │
   ▼
Search Hotel
   │
   ▼
Select Room
   │
   ▼
Enter Guest Details
   │
   ▼
Confirm Reservation
   │
   ▼
Backend Workflow
   │
   ▼
Database / Payment Integration
   │
   ▼
Confirmation Screen
```

This can reveal failures invisible to unit tests.

Perhaps a frontend field is serialized incorrectly. Perhaps authentication cookies aren't sent under the expected domain. Perhaps a backend API returns a value the Vue application cannot render.

A full workflow test can detect these integration failures.

### Why E2E tests are expensive

End-to-end tests have several disadvantages.

They are slower than focused tests, require more infrastructure, and can fail for reasons unrelated to the behavior under investigation.

A test may fail because:

- A browser animation delayed an element.
- Test data was modified by another test.
- A shared staging environment was temporarily unavailable.
- An external provider responded slowly.
- A selector depended on fragile DOM structure.

These are not necessarily application defects.

They may represent **test flakiness**: nondeterministic outcomes caused by timing, environment state, or unreliable test design.

### Don't test every permutation through the browser

Suppose reservation cancellation has twenty business-rule scenarios.

Do all twenty need to be exercised through the complete browser workflow?

Probably not.

The core domain rules can be tested quickly through focused tests.

A smaller set of E2E tests can verify that the browser, API, authentication, and persistence layers cooperate correctly.

This produces stronger confidence at lower maintenance cost.

### Test behavior, not pixels of implementation

A brittle browser test might locate a button through a long CSS selector:

```text
div:nth-child(3) > section > div > button.primary
```

A minor layout refactor can break it.

A better test uses accessible roles, labels, or deliberate stable test identifiers.

For example, with Playwright:

```typescript
await page.getByRole("button", {
  name: "Confirm reservation"
}).click();
```

This more closely reflects the interface behavior the user experiences.

The goal is to detect meaningful product regressions, not punish developers for rearranging harmless markup.

---

## 9. The Testing Pyramid—and Why It Isn't a Law

The traditional testing pyramid recommends many fast unit tests, fewer integration tests, and a relatively small collection of expensive end-to-end tests.

```text
             /\
            /  \
           / E2E\
          /------\
         /Integration\
        /-------------\
       /  Unit Tests   \
      /_________________\
```

The underlying principle is sensible.

Fast, focused tests should handle the large number of deterministic behavior combinations, while broader tests verify selected interactions across boundaries.

But the exact shape should depend on the application.

A library implementing mathematical algorithms may benefit from extensive unit and property-based testing.

A database-heavy CRUD application may gain greater confidence from integration tests against PostgreSQL than from mocking every repository method.

A payment system needs strong workflow and integration testing because many risks occur between components.

### The testing trophy

For applications with significant infrastructure integration, some engineers advocate a shape emphasizing integration tests alongside unit tests.

The precise diagram matters less than the engineering reasoning.

Ask:

> Where does this system's meaningful complexity actually live?

If your important defects involve concurrency, database constraints, and provider behavior, a test suite containing thousands of mocked service tests but almost no real integration tests is poorly aligned with risk.

If your application implements a complex pricing algorithm, focused deterministic unit tests may provide exceptional value.

**Test-layer proportions should follow failure modes, not an architectural illustration.**

---

## 10. Concurrency Testing: Correct Operations, Incorrect Interleavings

Concurrency bugs are difficult because they depend on timing and interaction between operations.

A function may behave correctly in isolation while producing invalid results when executed simultaneously with itself.

Consider a limited-inventory product with one remaining item.

Two customers attempt to purchase it.

A naive implementation:

```typescript
async function purchase(productId: string) {
  const inventory = await repository.getInventory(productId);

  if (inventory.available <= 0) {
    throw new Error("Out of stock");
  }

  await repository.updateInventory(
    productId,
    inventory.available - 1
  );
}
```

Sequential tests pass.

Concurrent requests may both observe one available item and both proceed.

The system oversells.

### Testing the invariant

The important guarantee is:

> Two concurrent purchase attempts must not produce two successful sales when only one unit is available.

A concurrency test might issue multiple purchase requests simultaneously against a real database.

But there's a complication.

A test using `Promise.all()` does not guarantee that the critical race occurs.

The database may serialize the operations by chance, making the test pass even though the implementation is unsafe.

### Make the race reproducible

A stronger test can coordinate execution at the critical point.

For example, test instrumentation can arrange for two transactions to read the inventory value before either performs the update.

Then allow both to continue.

This deliberately exercises the dangerous interleaving.

Alternatively, a correct implementation may rely on an atomic conditional update:

```sql
UPDATE inventory
SET available = available - 1
WHERE product_id = $1
  AND available > 0
RETURNING available;
```

The test verifies that only one operation succeeds when the initial inventory is one.

This is stronger because the database enforces the invariant atomically.

### Concurrency tests and nondeterminism

A concurrency test that passes one hundred times has still not mathematically proven the absence of every possible race.

Different scheduling, load, database state, and network timing may expose additional interleavings.

The goal is to test known dangerous scenarios deliberately and establish correctness through both implementation mechanisms and executable evidence.

For critical invariants, database constraints and atomic operations often provide stronger foundations than hoping the application happens to execute operations in a safe order.

---

## 11. Testing Asynchronous Workflows

Background jobs introduce additional failure modes because operations may execute later, retry, or overlap.

Imagine a BullMQ worker processing invoice generation.

```text
Reservation Confirmed
         │
         ▼
      Job Queue
         │
         ▼
   Invoice Worker
         │
         ▼
      PostgreSQL
         │
         ▼
     Email Provider
```

What should happen if the worker crashes after saving the invoice but before acknowledging the job?

The queue may deliver the job again.

If the handler isn't idempotent, the retry may create a duplicate invoice.

### Design tests around delivery semantics

Useful scenarios include:

**Duplicate delivery:** Process the same logical job twice and verify that only one invoice is created.

**Crash after persistence:** Simulate failure after the invoice is committed but before the job is acknowledged.

**Temporary provider failure:** Verify that an appropriate retry occurs without duplicating durable business state.

**Permanent invalid payload:** Verify that the job doesn't retry indefinitely without useful diagnostics.

**Concurrent workers:** Verify that two workers cannot violate the same business invariant.

**Out-of-order events:** Verify that delayed messages don't incorrectly regress state.

These tests should reflect the actual guarantees of the queue and application workflow.

BullMQ and Redis provide useful delivery and processing mechanisms, but durable business idempotency often requires coordination with authoritative persistence.

### Fake queues versus real queues

A unit test can directly invoke a worker handler with a sample payload.

That is useful for business logic.

But it does not establish actual queue retry behavior, lock renewal, job acknowledgment, or stalled-job recovery.

Selected integration tests should exercise the real queue infrastructure when those mechanisms matter.

Again, different test layers establish different guarantees.

---

## 12. Property-Based Testing: Finding Cases You Didn't Think Of

Traditional tests use developer-selected examples.

For instance:

```typescript
expect(calculateCancellationFee(100, 20)).toBe(20);
```

This verifies one case.

But perhaps the underlying function has dozens of unusual edge cases involving dates, rounding, or combinations of discounts.

**Property-based testing** takes a different approach.

Instead of enumerating every input manually, define general properties and generate many inputs automatically.

For example, a cancellation fee might need to satisfy:

\[
0 \leq \text{fee} \leq \text{booking total}
\]

A property-based test can generate many booking amounts and cancellation conditions, then verify the invariant.

With a TypeScript library such as fast-check:

```typescript
import fc from "fast-check";

it("never charges more than the booking total", () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 0, max: 1_000_000 }),
      fc.integer({ min: 0, max: 100 }),
      (amount, percentage) => {
        const fee = calculateFee(amount, percentage);

        return fee >= 0 && fee <= amount;
      }
    )
  );
});
```

Property-based testing can discover inputs the developer didn't anticipate.

Many tools also attempt to **shrink** a failing input into a simpler counterexample.

For example, instead of reporting a defect involving an enormous transaction amount and complicated parameters, the tool may reduce it to the smallest input that still fails.

### Properties must be meaningful

A weak property such as "the function returns a number" may pass even when the business result is wrong.

A stronger property captures an invariant.

For money calculations, useful properties may include:

- Results use the expected integer currency unit.
- Discounts never produce a negative charge unless explicitly permitted.
- Applying a zero discount preserves the original amount.
- Reordering independent line items doesn't change the total.

Property-based testing is especially valuable for parsers, serializers, validation logic, financial calculations, and algorithms with many input combinations.

It complements example-based tests rather than replacing them.

---

## 13. Performance Testing: Correctness Under Load

A system may behave correctly for one request while failing under realistic traffic.

Performance testing investigates behavior as demand changes.

Several distinct approaches are useful.

### Load testing

A load test examines the application under expected or planned workload.

For example:

> Can the reservation API sustain 300 requests per second while maintaining p95 latency below 400 milliseconds?

The test needs a representative mixture of operations, data sizes, authentication behavior, and downstream dependencies.

Testing one lightweight health endpoint tells us very little about database-heavy reservation creation.

### Stress testing

Stress testing pushes the system beyond expected capacity.

The objective is to discover saturation behavior, failure modes, and recovery characteristics.

For example, increase traffic until:

- Request latency grows sharply.
- Connection pools saturate.
- Queues accumulate.
- Error rates rise.
- Autoscaling reaches limits.

The important question isn't merely the maximum requests per second.

It's how the system behaves when overloaded.

Does it reject requests cleanly, or does it accept work indefinitely until everything times out?

### Soak testing

A soak test runs sustained workload over a longer period.

It may reveal resource leaks, unbounded caches, connection accumulation, or gradual performance deterioration.

A system can survive a five-minute test while failing after twelve hours.

### Spike testing

Spike testing examines sudden demand changes.

For example, a travel promotion causes traffic to increase from 50 to 1,000 requests per second within seconds.

Does the infrastructure scale quickly enough? Does the database tolerate the connection surge? Do clients retry and amplify overload?

This is where cloud architecture, capacity planning, and reliability engineering intersect.

### Measure the correct quantities

A useful performance test records:

- Offered request rate.
- Completed throughput.
- Error rate.
- Latency distribution.
- Resource utilization and saturation.
- Queue length and processing delay.
- Recovery time after load decreases.

Be careful about coordinated omission: some load generators slow down the rate of new requests when the system becomes slow, accidentally understating customer-facing latency.

A workload model should make clear whether arrival rate is independent of response completion or driven by a fixed number of clients waiting between operations.

Tools such as k6 can support realistic HTTP load testing, but interpreting the results matters more than producing an impressive graph.

---

## 14. Resilience Testing: Making Dependencies Fail on Purpose

Reliability engineering taught us that systems fail through partial outages, timeouts, retry storms, and resource saturation.

Testing should deliberately exercise these conditions.

Consider a booking workflow involving PostgreSQL and an external payment provider.

What happens if:

- PostgreSQL becomes unavailable during checkout?
- The payment provider returns HTTP 503?
- The provider times out after successfully charging the customer?
- Redis disappears while background jobs are active?
- A worker is terminated during invoice creation?
- One API instance fails during peak traffic?

These scenarios are difficult to verify with ordinary unit tests.

### Fault injection

A controlled environment can simulate:

- Network timeouts.
- Connection resets.
- Delayed responses.
- Dependency unavailability.
- Process termination.
- Resource exhaustion.
- Invalid or partial responses.

A proxy such as Toxiproxy can introduce selected network failures between services during integration tests.

For example, an application test might deliberately delay PostgreSQL connections or disconnect Redis during job processing.

The goal is not random destruction.

It's to verify specific recovery guarantees.

### Define the expected outcome first

Suppose a payment provider times out.

A meaningful test hypothesis is:

> The application records the payment outcome as uncertain, does not issue a second non-idempotent charge, and eventually reconciles the result.

Now the test can inject the timeout and inspect durable state.

Without an expected invariant, a fault-injection experiment may produce interesting logs but little evidence of correctness.

---

## 15. Test Data and Environments: The Hidden Source of Flakiness

A test suite may contain excellent assertions and still be unreliable because its environment is poorly controlled.

Suppose two integration tests share the same customer record.

Test A changes the customer's billing status.

Test B assumes the customer remains active.

Depending on execution order, one or both tests may fail.

The implementation may be correct. The test environment is not isolated.

### Isolation strategies

Common approaches include:

- Creating unique test data per test.
- Resetting databases between test groups.
- Using transaction rollback where suitable.
- Launching disposable service containers.
- Avoiding uncontrolled shared staging state.
- Separating tests that require exclusive resources.

No strategy works universally.

Transaction rollback can be effective for some database tests, but it may not isolate behavior involving independently committed worker transactions or external processes.

A disposable database provides strong isolation, but initializing a large environment for every test can be expensive.

The trade-off is between fidelity, speed, and independence.

### Deterministic time

Time-dependent tests deserve special attention.

Consider:

```typescript
if (new Date() > subscription.expiresAt) {
  expireSubscription();
}
```

A test executed near a time boundary may behave differently from one executed several minutes later.

Rather than relying on actual wall-clock time, inject a clock abstraction or use controlled test-time facilities.

For example:

```typescript
interface Clock {
  now(): Date;
}
```

A test implementation can return a fixed instant.

This makes boundary conditions reproducible.

The same principle applies to random identifiers, external responses, and asynchronous scheduling where deterministic control is possible.

### Production-like doesn't mean identical

A staging environment may use smaller databases, synthetic records, and simplified third-party integrations.

That's often reasonable.

But the differences should be understood.

If production failures regularly arise from data volume, tenant complexity, or integration behavior absent from staging, the environment isn't exercising the relevant risks.

A good test strategy identifies which production characteristics must be reproduced and which can safely be simplified.

---

## 16. Coverage, Mutation Testing, and False Confidence

Let's return to our 95% coverage figure.

Coverage tools commonly report measurements such as:

- Statement coverage.
- Branch coverage.
- Function coverage.
- Line coverage.

These measurements show which code locations or control-flow paths were exercised.

They don't establish whether the assertions were meaningful.

### A high-coverage but weak test

Consider:

```typescript
function applyDiscount(amount: number, percent: number) {
  return amount * (1 - percent / 100);
}
```

A test calls the function:

```typescript
it("calculates discount", () => {
  applyDiscount(100, 20);
});
```

The function executed.

Coverage may count its statements as covered.

But the test makes no assertion.

The implementation could return `NaN`, zero, or an incorrect value and the test might still pass.

### Mutation testing

Mutation testing evaluates whether tests detect deliberately introduced code changes.

A mutation tool might change:

```typescript
amount * (1 - percent / 100)
```

to:

```typescript
amount * (1 + percent / 100)
```

If the test suite still passes, the mutation survives.

That suggests the tests failed to detect an important behavioral change.

Mutation testing isn't a complete correctness proof. Some mutations are equivalent to the original behavior or irrelevant to requirements.

But it can reveal weak assertions and untested logic more effectively than raw coverage percentages.

### What coverage is actually good for

Coverage is useful as a diagnostic tool.

If a critical payment module has almost no test execution, that's worth investigating.

If a complex branch is never exercised, a targeted test may be valuable.

But setting an organization-wide target such as "every repository must achieve 95%" can encourage meaningless tests written primarily to satisfy the metric.

A better question is:

> Which important behavior remains insufficiently verified?

Coverage helps locate gaps. It cannot determine their business importance.

---

## 17. Designing a Practical Test Portfolio

Suppose you're responsible for testing a production hotel-booking SaaS.

Its architecture includes Vue, Node.js, PostgreSQL, Redis/BullMQ, Stripe, and several hotel suppliers.

A reasonable test portfolio might look like this:

| Layer | Primary target | Example |
|---|---|---|
| Unit | Domain logic | Cancellation fee calculation |
| Application-level | Use-case orchestration | Failed payment leaves booking pending |
| Database integration | Persistence guarantees | Duplicate provider payment rejected |
| HTTP integration | API contracts | Unauthorized tenant access denied |
| External adapter | Provider translation | Malformed supplier response handled |
| Contract | Cross-service compatibility | Reservation event schema accepted |
| E2E | Critical user journey | Create and confirm a booking |
| Concurrency | Shared-state invariants | Two customers cannot oversell inventory |
| Performance | Capacity and latency | Search API meets workload objective |
| Resilience | Failure recovery | Payment timeout reconciles safely |

The objective is not to implement every category for every feature.

A simple static content endpoint may need very little testing.

A financial workflow involving external providers and durable state requires much stronger evidence.

### Where Karate fits

Karate, which you may recognize from API automation work, is useful for HTTP-level integration and functional API tests.

It can express request sequences, authentication, response assertions, and data-driven scenarios in a relatively concise form.

For example, a Karate scenario can verify that an authenticated user from Tenant A cannot retrieve a Tenant B reservation.

That's meaningful API security testing.

But Karate does not replace focused unit tests for domain logic or database concurrency tests against PostgreSQL.

Similarly, Karate's UI capabilities can support browser testing, but a full UI journey shouldn't be the only place complex backend invariants are verified.

The tool should serve the testing layer, not dictate the entire testing strategy.

### Organize tests around risk

For a critical payment workflow, I'd prioritize:

1. Correct financial and state-transition invariants.
2. Real database uniqueness and transactional behavior.
3. Duplicate webhooks and retries.
4. External-provider protocol compatibility.
5. Authorization and tenant isolation.
6. The essential end-to-end checkout journey.
7. Relevant performance and failure-recovery behavior.

This ordering isn't universal.

But it reflects the fact that a duplicate payment is generally more consequential than a minor formatting defect in an administrative dashboard.

---

## 18. Practical Lab — Proving Idempotency Under Concurrency

Let's design a test for the incident that opened this lecture.

The application receives payment-provider webhook events.

Each event contains a stable provider payment identifier.

The required invariant is:

> Processing the same logical payment event multiple times, including concurrently, must not create duplicate payment records or duplicate downstream financial actions.

### Part A — Examine the unsafe implementation

```typescript
async function handlePaymentSucceeded(
  event: PaymentSucceededEvent
) {
  const existing = await repository.findByExternalId(
    event.paymentId
  );

  if (existing) {
    return;
  }

  await repository.save({
    externalPaymentId: event.paymentId,
    amountCents: event.amountCents,
    status: "SUCCEEDED"
  });

  await eventPublisher.publish({
    type: "PaymentRecorded",
    paymentId: event.paymentId
  });
}
```

Identify two distinct risks.

First, concurrent handlers can both observe that the payment doesn't exist.

Second, publishing an event after saving the payment introduces a failure window. The database write may succeed while event publication fails.

### Part B — Establish a database invariant

Create a real PostgreSQL table with an appropriate unique constraint.

```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY,
  external_payment_id TEXT NOT NULL UNIQUE,
  amount_cents BIGINT NOT NULL,
  status TEXT NOT NULL
);
```

In a multi-provider system, uniqueness might instead use the combination of provider identity and external payment ID.

The exact schema should reflect the provider's identifier guarantees.

### Part C — Make persistence idempotent

A possible SQL pattern is:

```sql
INSERT INTO payments (
  id,
  external_payment_id,
  amount_cents,
  status
)
VALUES ($1, $2, $3, 'SUCCEEDED')
ON CONFLICT (external_payment_id)
DO NOTHING
RETURNING id;
```

If the insert returns a row, this operation created the record.

If no row is returned, a record with that external identity already exists.

The application should then determine whether the existing record is consistent with the incoming event, rather than blindly treating every duplicate identifier as harmless.

### Part D — Test concurrent delivery

Your integration test should launch many attempts using the same logical event.

Conceptually:

```typescript
await Promise.all(
  Array.from({ length: 20 }, () =>
    handlePaymentSucceeded(event)
  )
);
```

Then query PostgreSQL:

```sql
SELECT COUNT(*)
FROM payments
WHERE external_payment_id = $1;
```

The result must be exactly one.

However, also verify that the relevant downstream business effect occurs once.

A uniqueness constraint on the payments table alone does not automatically prevent duplicate event publishing if the application publishes regardless of whether it inserted a new record.

### Part E — Add a transactional outbox

A robust design may insert the payment record and an outbox event in the same database transaction.

The transaction either commits both records or neither.

A separate dispatcher publishes committed outbox events and marks them as delivered according to its own retry-safe protocol.

This still permits duplicate delivery to downstream consumers, so those consumers need appropriate idempotency.

The test suite should verify:

- One logical payment record exists.
- One logical outbox event exists for that transition.
- Duplicate webhook deliveries don't create duplicate financial effects.
- A dispatcher failure can be retried safely.
- The application tolerates uncertainty about whether external event publication succeeded.

This is a much stronger test of payment correctness than asserting that a repository mock was called once.

### Part F — Inject a crash

Simulate a failure immediately after the database transaction commits but before the webhook handler acknowledges success.

The webhook provider retries the event.

Does the application preserve the invariant?

If so, the test has demonstrated meaningful resilience against a realistic distributed failure.

---

## 19. Engineering and Interview Challenges

### Challenge 1 — The 95% coverage problem

A backend has 95% unit-test coverage, but production frequently fails because of PostgreSQL constraints, API compatibility, and deployment configuration.

What changes would you recommend to the test strategy? Would increasing coverage to 99% help?

### Challenge 2 — The integration-test disagreement

A developer argues that all database access should be mocked because running PostgreSQL in CI is slow and inconvenient.

Another argues that every test must use PostgreSQL.

Which position is more defensible, and how would you balance speed with correctness?

### Challenge 3 — The flaky E2E suite

A Vue application's browser tests fail approximately 10% of the time.

Most failures disappear when the tests are rerun.

The team begins rerunning failed tests automatically until they pass.

What's wrong with this strategy? How would you investigate the actual causes?

### Challenge 4 — The queue correctness problem

A worker reads a BullMQ job, sends an invoice email, and marks the job complete.

It crashes after sending the email but before acknowledging completion.

The job is retried, and the customer receives the same email twice.

How would you design and test the workflow to reduce duplicate delivery?

### Challenge 5 — The performance illusion

A load test reports that an API successfully handles 5,000 requests per second.

The test uses a mocked database, disables authentication, and calls a lightweight endpoint with no meaningful business logic.

What does the result establish? What would a more useful performance test look like?

---

## 20. Solutions and Discussion

### Challenge 1 — Test the boundaries that actually fail

Increasing unit-test coverage from 95% to 99% is unlikely to address the main problem.

The observed failures occur at integration and deployment boundaries.

I'd introduce real PostgreSQL integration tests for important persistence behavior, contract tests for independently deployed APIs, and deployment verification for configuration and schema compatibility.

Critical workflows should also receive targeted concurrency and resilience tests.

Coverage remains useful for identifying untested code, but the testing portfolio should follow observed risks rather than pursue a larger percentage.

### Challenge 2 — Neither extreme is appropriate

Mocking every database interaction is fast but conceals important persistence behavior.

Using PostgreSQL for every trivial domain calculation increases test cost without necessarily improving confidence.

I'd keep deterministic domain tests lightweight and use real PostgreSQL for repository behavior, transaction semantics, constraints, and queries whose correctness matters.

Disposable database environments can make integration testing manageable.

The goal is to test each concern at the least expensive level that still reproduces the relevant behavior faithfully.

### Challenge 3 — Retries conceal test unreliability

Automatic retries may be useful as a temporary diagnostic aid, but treating a test as successful merely because one attempt eventually passes hides nondeterminism.

I'd collect failure artifacts such as screenshots, traces, browser logs, and timing information.

Then I'd investigate shared test data, brittle selectors, uncontrolled animations, asynchronous waits, external dependencies, and environment contention.

A flaky test suite damages engineering confidence because developers cannot distinguish real regressions from test infrastructure noise.

The correct response is to remove the sources of nondeterminism where feasible and isolate unavoidable environmental uncertainty.

### Challenge 4 — External side effects need their own idempotency strategy

Sending an email and acknowledging a job are not one atomic operation.

If the worker crashes between them, the queue may retry the job.

The application can record notification intent and delivery attempts durably, use stable logical notification identifiers, and avoid initiating duplicate sends when its recorded state establishes that the notification was already completed.

However, there is still a fundamental uncertainty if the email provider accepted the message but the application failed before recording success.

Provider-supported idempotency, where available, can reduce this ambiguity. Otherwise, exact once-only delivery may not be achievable across the boundary.

The test should model that uncertainty and verify the chosen duplicate-handling policy rather than claim a guarantee the system cannot provide.

### Challenge 5 — The test measured a synthetic endpoint

The result establishes that the particular test environment handled 5,000 requests per second for the lightweight operation under the chosen workload model.

It says little about real reservation creation, database contention, authentication, external integrations, or background processing.

A meaningful test would use representative traffic patterns, realistic data volumes, production-like infrastructure limits, and appropriate dependency behavior.

I'd measure response-time distributions, completed throughput, errors, resource saturation, and recovery after overload.

A benchmark is only useful when its workload resembles the question the engineers need answered.

---

## Mental Model

When designing a test strategy, ask:

1. **Invariant:** What must remain true for this operation to be correct?
2. **Failure mode:** How could that invariant be violated in production?
3. **Boundary:** Which real components or behaviors are necessary to reproduce the risk?
4. **Test layer:** What's the cheapest useful experiment that preserves those behaviors?
5. **Determinism:** Can the failure be reproduced reliably rather than accidentally?
6. **Evidence:** What does a passing test establish—and what does it leave unverified?
7. **Maintenance:** Will the test remain valuable as the implementation evolves?

**The central principle: A strong test suite is not the one that executes the most code. It's the one that most effectively reduces uncertainty about important production behavior.**


---

## End of SE440

**SE440 — Production Reliability and Quality Engineering** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

1. **Martin Fowler — [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)**. A thoughtful examination of unit, integration, and end-to-end testing, including trade-offs and common misunderstandings.

2. **Martin Fowler — [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html)**. The distinctions between test doubles and the implications of interaction-focused testing.

3. **Testcontainers — [Node.js Documentation](https://node.testcontainers.org/)**. Running disposable real infrastructure, including PostgreSQL, for automated integration tests.

4. **Pact — [Contract Testing Documentation](https://docs.pact.io/)**. Consumer-driven contract testing and cross-service compatibility verification.

5. **fast-check — [Property-Based Testing for JavaScript and TypeScript](https://fast-check.dev/)**. Generating input cases, expressing invariants, and shrinking failures into useful counterexamples.

6. **Grafana — [k6 Documentation](https://grafana.com/docs/k6/latest/)**. Load and performance testing, workload modeling, thresholds, and practical test execution.

7. **Karate — [Official Documentation](https://docs.karatelabs.io/)**. API automation, assertions, data-driven testing, and integration-level verification.

8. **PostgreSQL — [INSERT and ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)**. Database-enforced uniqueness and concurrency-safe insert behavior.

9. **Kent Beck — *Test-Driven Development: By Example***. A foundational exploration of incremental development and executable behavioral feedback.

10. **Gerard Meszaros — *xUnit Test Patterns***. A detailed reference on test design, fixtures, doubles, isolation, and maintainability.

---


