---
id: CS430-L01
course: CS430
title: "Distributed Systems and Partial Failure"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S07]
prev: null
next: CS430-L02
---

<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE325-L05
Preserve timeout, retry, retry amplification, and idempotency theory here.
When SE325-L05 exists, add a concise cross-reference for ongoing vendor-integration
maintenance (contract drift, sync corruption, token refresh). Do not rewrite this
lecture as a vendor field guide.
-->










# CS430 — Distributed Systems and Reliable Workflows

## Lecture 01: Distributed Systems and Partial Failure

*Why a network timeout tells you almost nothing about whether an operation succeeded—and how to build reliable software when different computers cannot agree on what happened.*

---

# 1. The Payment That May or May Not Have Happened

It's 21:43. A customer in Berlin has just booked a hotel room in Stockholm.

Your Node.js backend creates a pending reservation and asks the payment provider to charge reservation R-10842 for 450 euros, recorded as 45000 minor units.

```typescript
const payment = await paymentProvider.charge({
  reservationId: "R-10842",
  amount: 45000,
  currency: "EUR"
});
```

The provider does the work. It validates the payment method, contacts the financial systems, and authorizes the charge. The response it tries to send back names payment `pay_82934` and status succeeded.

```json
{
  "paymentId": "pay_82934",
  "status": "succeeded"
}
```

That response never arrives. After three seconds the client gives up. The error it records is a timeout, `ETIMEDOUT`.

```text
ETIMEDOUT
```

The backend has a problem.

It doesn't know whether the customer was charged.

Perhaps the request never reached the provider. Perhaps the provider rejected it. Perhaps the charge succeeded, but the response was lost. Perhaps the provider is still processing the request.

All four possibilities can look remarkably similar from your application's perspective.

What should happen next?

If you retry with a new payment request, you might charge the customer twice. If you declare the operation failed, you might tell the customer to try again even though the payment succeeded. If you confirm the reservation, you might give away a room without receiving payment.

And if you simply wait forever, your service eventually runs out of resources.

Welcome to distributed systems engineering.

The interesting problem isn't that networks sometimes fail. Developers know that already. The problem is that **a communication failure can make the outcome of a remote operation fundamentally uncertain**.

In a local function call, exceptions and return values generally tell us what happened within the executing process, subject to the function's semantics. Once execution crosses a network, the caller and callee can experience different realities.

The callee may have completed an operation that the caller believes failed.

The caller may have abandoned a request that the callee is still processing.

A retry may arrive before the original request finishes—or long afterward.

And there is no universal mechanism that allows one computer to distinguish every slow computer from every failed computer.

This is why distributed systems aren't merely ordinary software deployed across multiple machines. They require a different model of knowledge, failure, and coordination.

---

# 2. The Difference Between a Local Call and a Remote Call

Consider two calls that look almost identical. One is an ordinary `calculatePrice(input)` in this process. The other is `await pricingService.calculatePrice(input)`. If that second call goes over HTTP, it has left the process.

```typescript
const result = calculatePrice(input);
```

```typescript
const result = await pricingService.calculatePrice(input);
```

The local calculation primarily depends on code execution, memory, and the process environment. The remote call leaves the process. Between the two machines sit the operating system, the network stack, a load balancer or proxy, the remote service, and often that service's own database. Any part of that chain may experience delay, failure, or resource exhaustion.

```text
Application Process
        |
        v
Operating System
        |
        v
Network Stack
        |
        v
Load Balancer / Proxy
        |
        v
Remote Service
        |
        v
Remote Database
```

The request itself might be lost. The response might be lost. The remote process might crash before processing, during processing, or after committing its result.

Even when both machines are functioning correctly, a network problem can prevent them from communicating.

This leads to the defining characteristic of distributed failure: **different parts of the system can fail independently**.

In an ordinary single-process program, a fatal process crash generally stops the whole program. In a distributed application, one component may continue operating while another becomes unreachable.

A database may remain healthy while its application loses connectivity.

A payment provider may successfully process payments while your HTTP client experiences timeouts.

A worker may continue executing after its queue-processing lease expires.

These are examples of *partial failure*.

The challenge is that a caller cannot always observe the true state of another component.

### Failure versus suspicion

Suppose Service A sends a request to Service B and receives no response.

Has B crashed?

Possibly.

But perhaps B is overloaded. Perhaps a packet was delayed. Perhaps the network is partitioned. Perhaps B completed the work but its response was lost.

From A's perspective, these situations can be indistinguishable.

A timeout therefore establishes something about **the caller's waiting period**, not necessarily about the remote operation's final outcome.

This is why distributed systems often need explicit states: pending, processing, succeeded, failed, and unknown.

```text
PENDING
PROCESSING
SUCCEEDED
FAILED
UNKNOWN
```

`UNKNOWN` isn't an admission of poor engineering. Sometimes it's the only truthful answer available.

The goal is to design a mechanism that eventually resolves uncertainty without incorrectly repeating business effects.

---

# 3. A Request Has More Possible Outcomes Than Success and Failure

Let's examine the payment operation as a timeline. On the happy path the client sends the payment request, the provider validates it, processes it, commits the result, and sends success back.

```text
CLIENT                              PAYMENT PROVIDER
   |                                       |
   |-------- Payment Request ------------>|
   |                                       |
   |                              Validate request
   |                                       |
   |                              Process payment
   |                                       |
   |                              Commit result
   |                                       |
   |<--------- Success response -----------|
   |                                       |
```

Now imagine a failure occurring at different points.

The critical distinction is between *what happened* and *what the caller observed*. Walk the same payment along the path and the knowledge changes.

If the request was definitely never transmitted, the provider did not charge, and the caller sometimes knows that. If the request was lost in transit, the provider did not charge, and the caller usually cannot tell this case from the others. If the failure happens during remote processing, the provider may already have charged, and the caller does not know. If the provider committed and then failed before answering, the customer was charged, and the caller does not know. If the success response was lost on the way back, the customer was charged, and the caller does not know.

An HTTP timeout is an observation about communication. It is not a business result such as payment declined.

Likewise, a network disconnect after submitting a reservation doesn't establish that the reservation was cancelled.

### The retry ambiguity

Suppose the backend retries the operation:

```text
Attempt 1: Charge €450 -> Timeout
Attempt 2: Charge €450 -> Success
```

What actually happened? The client saw the same two lines either way: the first charge of 450 euros timed out, the second charge of 450 euros succeeded. The money is not the same.

Possibility A: the first attempt never reached the provider. Only the second charge landed. The customer paid 450 euros.

Possibility B: the first attempt charged 450 euros and the response was lost. The second attempt charged another 450. The customer paid 900 euros.

```text
Possibility A:
  Attempt 1 never reached provider
  Attempt 2 charged €450
  Total charged: €450

Possibility B:
  Attempt 1 charged €450
  Attempt 1 response was lost
  Attempt 2 charged another €450
  Total charged: €900
```

The exact same sequence of client-visible events can produce different financial outcomes.

That's the central problem.

You cannot resolve it merely by catching more exceptions, increasing the timeout, or adding another `try/catch`.

You need a protocol that lets the participants recognize the **identity of the intended operation**.

Before we design one, however, let's understand what timeouts are actually for.

---

# 4. Timeouts: Deciding How Long You're Willing to Wait

Imagine a backend waiting for a remote service.

Without a timeout, the request could remain pending indefinitely, consuming resources while providing no useful progress.

A timeout establishes an upper bound on how long the caller is willing to wait for a particular operation.

For example:

```typescript
const response = await fetch(paymentUrl, {
  method: "POST",
  signal: AbortSignal.timeout(3000)
});
```

This gives the fetch operation a three-second timeout.

But three seconds is a policy choice, not a fact about the remote system.

The provider might normally respond within 200 milliseconds but occasionally take five seconds during network disruption or heavy processing.

If your timeout is too short, you'll abandon operations that might have succeeded shortly afterward.

If it's too long, your application accumulates waiting requests and delays useful failure handling.

### Why cancellation isn't rollback

When the timeout fires, Node.js aborts the local fetch operation.

That doesn't mean the remote server stops processing.

The provider may already have committed the payment. It may continue processing after the connection disappears, or the server might not even notice the disconnect immediately.

There is no automatic distributed rollback associated with aborting an HTTP request.

This distinction matters even with services under your control. A caller's cancellation signal and a remote operation's completion are separate events unless your protocol explicitly coordinates them.

### Timeouts versus deadlines

Suppose an API request has a total response-time budget of four seconds.

It calls three downstream services:

```text
Authentication Service
        |
        v
Pricing Service
        |
        v
Payment Service
```

If each call receives an independent three-second timeout, the entire operation might wait close to nine seconds before additional application overhead.

That's inconsistent with the original four-second budget.

A **deadline** represents the latest acceptable completion time for the overall operation.

Each downstream call receives only an appropriate portion of the remaining budget.

Conceptually:

```typescript
const deadline = performance.now() + 4000;

function remainingMs(): number {
  return Math.max(0, deadline - performance.now());
}
```

Before a new operation, the application evaluates how much time remains.

This example uses a monotonic elapsed-time clock rather than the wall clock, because we're measuring duration.

A real implementation would also propagate cancellation appropriately, reserve time for response handling, and avoid starting work that cannot plausibly finish before the deadline.

### Choosing timeout values

A useful approach is to examine the dependency's actual latency distribution.

If the vast majority of calls complete within 100 milliseconds but the 99.9th percentile reaches 800 milliseconds, choosing a 150-millisecond timeout may cause many unnecessary aborts.

At the same time, extending every timeout to thirty seconds could allow slow dependencies to exhaust caller resources during incidents.

Timeout selection involves balancing false timeouts, resource consumption, and user-facing latency requirements.

For external payments, the timeout policy must also work with operation-status retrieval and idempotency. Otherwise, shortening the timeout simply creates more ambiguous payment outcomes.

---

# 5. Retries: A Reliability Feature That Can Become an Attack

Temporary failures are common.

A connection can reset, a service can briefly overload, or a load balancer can route traffic toward an unhealthy instance.

Trying again often works.

That's why retries are such a widely used reliability mechanism.

But retries consume capacity.

Suppose Service A calls Service B, which calls Service C.

Each layer retries failed calls three times in total.

If C is unavailable, one original request from A may cause up to nine attempts from B to C, depending on where retries are applied.

Now add another retrying layer above A. One user request, three attempts at the first layer, three at the next for each of those, three at the last for each of those: twenty-seven calls against a dependency that is already down.

```text
1 user request
    |
    v
3 attempts at Layer A
    |
    v
3 attempts per A attempt at Layer B
    |
    v
3 attempts per B attempt at Layer C

Potential downstream attempts: 3 × 3 × 3 = 27
```

For a deeper call chain, amplification can become extreme.

This is sometimes described as a **retry storm**.

The dependency is already struggling, so callers generate additional requests, consuming even more of its limited capacity.

The recovery mechanism becomes part of the outage.

### Retry budgets

A practical retry policy should define how many additional attempts are permitted and how much overall time they may consume.

For example, a low-latency interactive request may justify only one retry after a brief transient failure.

A background reconciliation worker might retry over hours, provided attempts are spread out and the operation remains safe.

Often it's better to concentrate retries at one deliberate architectural layer rather than allowing every component in a call chain to retry independently.

### Exponential backoff

Instead of immediately repeating failed requests, we can increase the delay between attempts. The first try goes immediately. The next waits about 200 milliseconds, then about 400, then about 800, doubling until a cap. A common cap in this sketch is five seconds: take 200 milliseconds times two to the power of the retry number, and do not exceed 5000 milliseconds.

For example:

```text
Attempt 1: immediately
Attempt 2: after ~200 ms
Attempt 3: after ~400 ms
Attempt 4: after ~800 ms
```

A typical capped backoff calculation is:

```typescript
const cap = Math.min(
  200 * 2 ** retryNumber,
  5000
);
```

But if 10,000 clients encounter the same failure simultaneously, they'll potentially retry on the same schedule.

That's where **jitter** comes in. Take that capped delay and multiply it by a random fraction between zero and one, so the clients do not wake up together.

```typescript
const delay = Math.random() * cap;
```

Randomized delay spreads requests across time rather than creating synchronized waves.

AWS's engineering literature strongly emphasizes this technique because correlated retries can overwhelm services even when each client individually behaves reasonably.

### Not every failure is retryable

An HTTP `503` from a temporarily unavailable dependency may justify retrying.

A validation error usually doesn't.

A rate-limit response may require respecting `Retry-After` or another provider-defined policy.

A network timeout after a payment submission requires particular care because the operation may already have succeeded.

Retries must be both **operationally bounded** and **semantically safe**.

The second requirement brings us to idempotency.

---

# 6. Idempotency: Giving an Operation a Durable Identity

We've already encountered idempotent workers in SE320-L03. Now let's examine the underlying distributed protocol more carefully.

Suppose a customer wants to pay €450 for Reservation R-10842.

The business intent is:

> Execute this particular payment operation once.

That intent must remain the same even if the HTTP request is transmitted several times.

One solution is to assign a stable operation identifier: an operation id such as `payop_92831`, tied to reservation R-10842, amount 45000 minor units, currency EUR. Every retry carries that same identity. On the wire it is often a header, `Idempotency-Key: payop_92831`, with the reservation, amount, and currency repeated in the body.

```text
payment-operation: payop_92831
reservation: R-10842
amount: 45000
currency: EUR
```

```http
POST /payments
Idempotency-Key: payop_92831
Content-Type: application/json

{
  "reservationId": "R-10842",
  "amountMinor": 45000,
  "currency": "EUR"
}
```

The receiving system uses the key to recognize multiple requests representing the same intended operation.

On the server, that key has a short life. Record the new identity, mark it processing, then later mark it succeeded or failed. A second request with the same key returns the existing result, or says the work is still underway. It does not start another payment.

```text
                 NEW OPERATION
                       |
                       v
                Record identity
                       |
                       v
                   PROCESSING
                  /          \
                 v            v
             SUCCEEDED      FAILED
```

When another request arrives with the same key, follow the documented idempotency contract rather than inventing a second payment.

### What must an idempotency record contain?

For a serious implementation, several pieces of information are useful.

An operation identity, scoped to the appropriate tenant or customer.

A fingerprint or canonical representation of the meaningful request parameters.

The operation's current status.

The resulting payment or reservation identifier.

Enough information to recover the result after a process crash.

And an appropriate retention policy.

The parameter fingerprint matters because the same idempotency key shouldn't silently authorize incompatible operations. Key `payop_92831` was first used for 450 euros. A later request presents the same key and 900 euros. That is not a harmless retry of the same request.

Imagine:

```text
Key: payop_92831
First request:  €450
Second request: €900
```

That is not a harmless retry of the same request.

It's a conflict in declared intent.

The service should reject the mismatch rather than treating it as a second payment or returning a misleading result.

### The concurrency problem inside idempotency

A naive implementation might look like this:

```typescript
const existing = await repository.findByKey(key);

if (!existing) {
  await createPayment();
  await repository.saveKey(key);
}
```

Two concurrent requests can both observe that the key doesn't exist.

Both may then execute the payment.

We've recreated a familiar race condition from CS330-L03.

A correct implementation must atomically claim or establish the operation identity and coordinate concurrent requests.

For local database work, uniqueness constraints and transactions are common tools.

For external effects, the service still needs an appropriate protocol with the external provider.

### Retention matters

An idempotency key is not necessarily remembered forever.

A provider may discard old keys after a retention period.

If the same request is retried after that period, the provider might treat it as a new operation.

Stripe, for example, documents a finite key-retention policy and may treat a reused key as a new request after pruning.

Its API also documents that saved results can include certain errors, so blindly repeating the key after a recorded server error isn't necessarily a way to obtain a newly executed operation.

A robust integration must understand the provider's exact contract rather than assuming all idempotency implementations behave identically.

**The useful guarantee is not that every request executes once. It's that repeated requests representing one business intent do not create unintended additional effects under the agreed protocol.**

---

# 7. What If the Provider Doesn't Support Idempotency?

Now suppose your payment provider has no idempotency-key mechanism.

You submit a payment request and encounter a timeout.

What should happen?

One possibility is to query the provider for payments associated with the reservation or merchant reference.

If the provider supports reliable lookup by a stable reference, the backend can investigate whether the operation succeeded before deciding what to do next.

A durable local record keeps the operation id `payop_92831`, reservation R-10842, a provider reference such as `merchant-92831`, and status unknown.

```text
payment_operation_id = payop_92831
reservation_id       = R-10842
provider_reference   = merchant-92831
status               = UNKNOWN
```

A reconciliation process then tries to move the local record out of unknown. If the provider confirms the charge, mark succeeded. If the provider confirms a rejection, mark failed. If the provider is still processing, or cannot be reached, leave the record unknown. A failed lookup is not evidence that the payment failed.

```text
UNKNOWN
   |
   +-- Provider confirms charge ------> SUCCEEDED
   |
   +-- Provider confirms rejection ---> FAILED
   |
   +-- Provider still processing -----> UNKNOWN
   |
   +-- Provider unreachable ---------> UNKNOWN
```

It's another communication failure.

And absence from a provider's search results is only meaningful if the provider's lookup contract guarantees that completed operations would already be visible.

This is why reconciliation can be surprisingly difficult.

### The impossibility of perfect certainty without cooperation

Suppose the provider exposes only one operation:

```text
charge(amount)
```

It provides no idempotency keys, no operation lookup, no status queries, and no reliable reconciliation interface.

If the response is lost after charging, the caller cannot know whether the effect happened.

It cannot both guarantee eventual execution and guarantee no duplication through retries under arbitrary failures.

Those two goals conflict with the available information.

You must choose a business policy: risk duplicates, risk missed operations, require manual intervention, or change providers.

Sometimes the correct architectural answer is that an external API doesn't provide sufficient guarantees for a business-critical workflow.

That's not a programming failure. It's an integration-contract limitation.

---

# 8. Circuit Breakers: Stop Calling Something That Is Clearly Struggling

Imagine your booking API depends on an external pricing service.

Under ordinary conditions, pricing requests complete within 100 milliseconds.

Then the service begins timing out.

Every booking request waits three seconds, retries, and waits another three seconds.

Soon the application has hundreds of requests stuck waiting for the pricing service.

Connection pools fill.

Memory consumption increases.

Unrelated endpoints begin slowing down.

One struggling dependency has now degraded the entire application.

A **circuit breaker** is a mechanism for preventing this kind of failure propagation.

It tracks failures and temporarily refuses new calls when a dependency appears unhealthy.

A common state model has three names. **Closed** means requests are allowed. **Open** means requests are rejected immediately because recent failures say the dependency is unhealthy. **Half-open** means a few probe calls are allowed, and their results move the circuit back to closed or to open.

```text
                  CLOSED
             Requests allowed
                       |
              Too many failures
                       |
                       v
                    OPEN
             Requests rejected
                       |
               Recovery interval
                       |
                       v
                  HALF-OPEN
             Limited probe calls
                  /        \
             Success      Failure
                |            |
                v            v
             CLOSED         OPEN
```

When the circuit is closed, requests flow normally.

When it's open, calls fail fast rather than consuming resources waiting for a dependency that is likely unavailable.

After an interval, the circuit allows a limited number of probe requests. If the dependency appears healthy, normal traffic resumes.

### What a circuit breaker does not solve

It doesn't repair the dependency.

It doesn't establish whether an earlier payment succeeded.

It doesn't automatically make a retry safe.

And it doesn't necessarily belong in front of every remote call.

A circuit breaker changes the caller's behavior in response to observed dependency health.

For a hotel-description enrichment service, an open circuit might trigger a fallback to basic property information.

For a payment provider, an open circuit may require putting the payment operation into a pending state rather than declaring the payment declined.

The fallback must preserve business semantics.

### Circuit breakers and retries work together

A common strategy is to combine limited retries, bounded timeouts, and a circuit breaker.

But configuration matters.

A circuit that opens after one isolated network error may reject perfectly healthy traffic.

A circuit that waits for thousands of failures may react too slowly.

Rolling error rates, latency thresholds, minimum request volumes, and recovery behavior should be informed by real traffic patterns.

And if dozens of application instances independently reopen their circuits at the same moment, the recovering dependency may receive a sudden burst of probes.

Jitter and controlled recovery traffic can help.

---

# 9. Bulkheads: Preventing One Dependency From Consuming Everything

Circuit breakers respond to unhealthy dependencies. Another useful pattern limits how much capacity a dependency can consume even before it fails.

This is sometimes called a **bulkhead**, borrowing the idea from compartmentalized ships.

A ship divided into watertight compartments can survive flooding in one area without losing the entire vessel.

A backend can similarly divide its execution capacity.

Suppose an application supports:

- Reservation creation.
- Hotel search.
- Analytics queries.
- External CRM synchronization.

If all four workloads use one unbounded collection of outbound operations, a slow CRM integration could consume connections or memory that reservations need.

Instead, you might allocate separate concurrency limits.

```text
                  NODE.JS SERVICE
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
     Reservations     CRM Sync       Analytics
       Limit: 40      Limit: 10      Limit: 15
          |              |              |
          v              v              v
       Database      External API    Database
```

These numbers are illustrative.

The important idea is limiting the damage caused by one workload.

In Node.js, bulkheading may involve semaphores, bounded work queues, separate connection pools, dedicated worker processes, or distinct deployment units.

The details depend on where the actual resource constraint exists.

But don't confuse bulkheading with simply increasing every concurrency limit.

If PostgreSQL can safely process only 100 expensive queries concurrently, allowing 1,000 application-level operations to hit it simultaneously is unlikely to help.

A bounded system can reject excess work or queue it deliberately rather than allowing unlimited resource consumption.

**Reliability sometimes requires doing less work, not adding more attempts.**

---

# 10. The Tail-Latency Problem

Let's examine another reason distributed applications can feel slow even when their components appear healthy.

Suppose your backend calls five independent services sequentially.

Each service normally responds quickly, and each has a 99% probability of completing within its latency target.

Assuming independence for this simple illustration, the probability that all five meet their target is:

\[
0.99^5 \approx 95.1\%
\]

That means approximately 4.9% of complete requests encounter at least one service exceeding its individual latency target.

Now suppose the application calls ten services.

\[
0.99^{10} \approx 90.4\%
\]

Almost one in ten complete operations experiences at least one slow dependency under those assumptions.

Real dependencies are often correlated, so the actual behavior may be better or worse.

The lesson is that end-to-end latency can deteriorate as the number of required remote operations increases.

### Sequential versus parallel dependencies

Some operations genuinely depend on earlier results.

For example, a payment request may require an already calculated authoritative amount.

But many independent calls can execute concurrently. Here, hotel details, amenities, and the review summary are requested together, and the handler waits until all three settle or one of them rejects.

```typescript
const [hotel, amenities, reviews] = await Promise.all([
  hotelService.getDetails(id),
  amenityService.getForHotel(id),
  reviewService.getSummary(id)
]);
```

Parallel execution can reduce critical-path latency compared with calling the three services sequentially.

However, it also creates simultaneous load and potentially more complex failure handling.

If one call rejects, `Promise.all` rejects, but the other operations aren't automatically cancelled.

They may continue consuming resources.

For optional dependencies, `Promise.allSettled()` or carefully designed separate fallbacks can be appropriate.

Again, concurrency is an architectural choice with resource and correctness consequences—not merely a syntax optimization.

---

# 11. Clocks, Leases, and the Trouble With Time

Distributed systems often need to answer questions involving time.

Has a lease expired?

Is an operation too old?

Did Event A happen before Event B?

Which update is newer?

It may seem reasonable to compare timestamps.

But different computers don't necessarily agree on the current time.

One server's clock might be 200 milliseconds ahead of another. Network time synchronization reduces clock drift, but it doesn't make physically separate clocks perfectly identical.

Clock adjustments, virtualization, operating-system behavior, and network disturbances introduce additional complications.

### Wall clocks versus monotonic clocks

A wall clock answers:

> What time is it?

A monotonic clock helps answer:

> How much time has elapsed?

For measuring local operation durations, monotonic clocks are preferable because wall-clock corrections can cause timestamps to jump forward or backward.

In Node.js, `performance.now()` is suitable for elapsed-duration measurements within a process.

But a monotonic timestamp from Server A cannot simply be compared numerically with a timestamp from Server B as though they share the same origin.

### The expired-lock problem

Imagine Worker A acquires a distributed lock with a ten-second lease.

Then Worker A pauses for fifteen seconds because of a long garbage-collection pause, host suspension, or scheduling delay.

The lease expires.

Worker B acquires the lock and begins work.

Worker A resumes.

Now both workers may be capable of modifying the same resource.

The lock once belonged to A, but that no longer establishes that A is the current owner.

One protection is a **fencing token**: an increasing number associated with successive lock ownership.

```text
Worker A acquires lock -> token 41
Worker B acquires lock -> token 42
```

The protected resource rejects operations carrying a token older than the highest token it has accepted.

Worker A can resume, but its old token 41 cannot override operations associated with token 42, provided the authoritative resource actually enforces the rule correctly.

This matters because a lease alone cannot stop a process that has paused and later resumed.

We will explore clocks, consistency, and replicated state more deeply in CS430-L02.

For now, the practical rule is to avoid treating timestamps or expiring leases as infallible proof of global ordering or ownership.

---

# 12. Correlation: How Do You Reconstruct What Happened?

Imagine the payment timeout from our opening incident.

Customer support asks:

> Did Reservation R-10842 actually get charged?

Your logs show a payment request starting at 21:43:02 and a timeout at 21:43:05. That pair of lines is not enough to say whether reservation R-10842 was charged.

```text
21:43:02 Payment request started
21:43:05 Payment timeout
```

You need to identify the exact operation across systems.

A useful architecture distinguishes several identifiers, and they are not interchangeable.

A **request id** names one incoming HTTP request. A **trace id** names one distributed execution path. An **operation id** names one intended business effect, such as this payment. A **reservation id** names the business entity. A **provider reference** names the external system's own operation.

A retry normally creates a new network attempt. It may have a new request id while preserving the same business operation id. In the example, reservation R-10842 and operation `payop_92831` stay put. Attempt one has request `req_a91` and times out. Attempt two has request `req_b52` and succeeds. Two requests, one intended payment.

```text
reservationId = R-10842
operationId   = payop_92831

Attempt 1:
  requestId = req_a91
  result    = timeout

Attempt 2:
  requestId = req_b52
  result    = success
```

Distributed tracing can connect the execution path across services. Structured logs can record the operation identity and relevant status transitions.

But observability doesn't itself guarantee correctness.

It makes uncertainty investigable.

If a payment remains unresolved, the application needs durable state and reconciliation—not merely a beautiful trace showing where communication stopped.

---

# 13. Designing the Original Payment Workflow Properly

We now have enough concepts to redesign the opening scenario.

Suppose a customer submits a booking request.

Rather than treating a payment timeout as a definitive failure, the system establishes a durable payment operation. It records a booking intent and a payment operation, then submits to the provider. A definite success or a definite rejection is stored as such. A timeout leaves the operation pending, and a later workflow reconciles or retries under that same identity.

```text
POST /reservations
        |
        v
Create booking intent
        |
        v
Record payment operation
        |
        v
Submit request to provider
        |
        +-- Definitive success
        |        |
        |        v
        |   Mark payment succeeded
        |
        +-- Definitive rejection
        |        |
        |        v
        |   Mark payment failed
        |
        +-- Timeout / Unknown
                 |
                 v
          Preserve pending state
                 |
                 v
          Reconcile / Retry Safely
```

The payment operation has one stable identity.

Every attempt to submit it uses the same provider-supported idempotency key where available.

If the provider returns a definite result, the application records it.

If communication fails ambiguously, the operation remains unresolved rather than being misclassified as a decline.

A background workflow can query the provider or retry safely under the provider's contract.

### What should the customer see?

That depends on the product.

For a short-lived checkout flow, the frontend might display:

> Your payment is being confirmed. Please don't submit another booking.

The system should provide a way to retrieve the booking's status using a stable identifier.

A `202 Accepted` response may be appropriate when the application has durably accepted work but hasn't completed the requested outcome.

If the booking is already confirmed and only secondary work remains, `201 Created` may be appropriate instead.

The response must describe what the backend can actually guarantee.

For hotel bookings, additional complications arise around inventory holds, payment authorization expiry, supplier confirmation, and compensation if payment succeeds but inventory allocation fails.

Those belong to the durable business workflow we'll design in CS430-L05.

The architectural foundation, however, is already clear.

**A remote operation's state belongs in durable business records, not solely in the success or failure of one HTTP call.**

---

*The spoken lecture ends here. What follows is a practical lab for the screen, then interview prompts and a glance card. You can stop the voice reader.*

# 14. Practical Lab: Reproduce an Unknown Payment Outcome

Let's construct a tiny distributed system using only Node.js.

We'll simulate a payment provider that commits a charge immediately, then delays its response long enough for the client's request to time out.

We'll compare two endpoints:

- `/charge-naive`, which creates a new charge for every request.
- `/charge-safe`, which uses an idempotency key to recognize repeated attempts.

This experiment deliberately uses in-memory storage. It demonstrates the protocol but doesn't provide cross-process or restart durability.

### Step 1 — Create the simulated provider

Create `server.mjs`:

```javascript
import http from "node:http";

const charges = [];
const operations = new Map();

const sleep = ms =>
  new Promise(resolve => setTimeout(resolve, ms));

function sendJson(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json"
  });

  res.end(JSON.stringify(body));
}

async function readBody(req) {
  let text = "";

  for await (const chunk of req) {
    text += chunk;
  }

  return JSON.parse(text);
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/state") {
    return sendJson(res, 200, { charges });
  }

  if (
    req.method !== "POST" ||
    !["/charge-naive", "/charge-safe"].includes(req.url)
  ) {
    return sendJson(res, 404, { error: "Not found" });
  }

  try {
    const input = await readBody(req);

    const amount = input.amount;
    const key = req.headers["idempotency-key"];

    if (!Number.isInteger(amount) || amount <= 0) {
      return sendJson(res, 400, {
        error: "Invalid amount"
      });
    }

    let charge;

    if (req.url === "/charge-safe") {
      if (typeof key !== "string" || !key) {
        return sendJson(res, 400, {
          error: "Idempotency key required"
        });
      }

      const existing = operations.get(key);

      if (existing) {
        if (existing.amount !== amount) {
          return sendJson(res, 409, {
            error: "Key reused with different amount"
          });
        }

        return sendJson(res, 200, existing);
      }
    }

    charge = {
      id: `charge-${charges.length + 1}`,
      amount,
      status: "succeeded"
    };

    // The business effect happens NOW.
    charges.push(charge);

    if (req.url === "/charge-safe") {
      operations.set(key, charge);
    }

    console.log("CHARGE COMMITTED:", charge.id);

    // But the response arrives much later.
    await sleep(250);

    sendJson(res, 200, charge);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) {
      sendJson(res, 500, {
        error: "Server failure"
      });
    }
  }
});

server.listen(3000, () => {
  console.log("Payment provider on port 3000");
});
```

Run:

```bash
node server.mjs
```

### Step 2 — Create the client

Create `client.mjs`:

```javascript
const sleep = ms =>
  new Promise(resolve => setTimeout(resolve, ms));

async function attempt(path, key, timeoutMs) {
  try {
    const response = await fetch(
      `http://localhost:3000${path}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(key ? { "Idempotency-Key": key } : {})
        },
        body: JSON.stringify({ amount: 45000 }),
        signal: AbortSignal.timeout(timeoutMs)
      }
    );

    return await response.json();
  } catch (error) {
    return { error: error.name };
  }
}

console.log("NAIVE FIRST ATTEMPT:");
console.log(await attempt("/charge-naive", null, 60));

await sleep(300);

console.log("NAIVE RETRY:");
console.log(await attempt("/charge-naive", null, 1000));

console.log("SAFE FIRST ATTEMPT:");
console.log(
  await attempt("/charge-safe", "payment-92831", 60)
);

await sleep(300);

console.log("SAFE RETRY:");
console.log(
  await attempt("/charge-safe", "payment-92831", 1000)
);

console.log("FINAL PROVIDER STATE:");

const state = await fetch("http://localhost:3000/state");
console.log(await state.json());
```

Run in another terminal:

```bash
node client.mjs
```

### Step 3 — Inspect the result

The first naive request should time out from the client's perspective.

But the server committed the charge before delaying its response.

The naive retry therefore creates a second charge.

The safe endpoint also times out on its first attempt, but the retry carries the same idempotency key and retrieves the previously stored result.

You should observe three total charges:

```text
Naive attempt 1 -> charge-1
Naive attempt 2 -> charge-2
Safe attempt 1  -> charge-3
Safe attempt 2  -> returns charge-3
```

The exact client timeout error name can depend on the Node.js version, but the important observation is the distinction between the caller's outcome and the provider's state.

### Step 4 — Investigate the remaining weaknesses

Our safe implementation is still not production-grade.

The operation records exist only in one process's memory. Restarting the server loses them.

Multiple provider instances would maintain separate maps unless they shared authoritative storage.

A real implementation also needs durable atomic claiming, a proper state machine for operations that complete asynchronously, retention policies, and careful treatment of errors after the operation begins.

Notice that the in-memory example inserts the operation record synchronously before any subsequent `await`, so two requests handled by this one event loop cannot interleave between its lookup and insertion. That property disappears if the real implementation performs separate asynchronous read and write operations without coordination.

For an actual financial system, provider-side durable idempotency and reconciliation are essential.

The lab demonstrates the core idea: **the same client-visible timeout can coexist with a successfully committed remote business effect**.

---

# 15. Engineering and Interview Challenges

### Question 1 — The ambiguous timeout

Your backend sends a payment request and times out after three seconds. The payment provider exposes an operation-status endpoint.

Should you immediately retry the payment? What information would you record before doing anything else?

### Question 2 — Retry amplification

A request passes through three services. Each retries failed downstream calls three times in total.

What failure pattern could result? How would you redesign retry ownership?

### Question 3 — Cancellation semantics

An HTTP client aborts a request after one second. The server completes a database transaction two seconds later.

Has either component violated a guarantee? What should the API contract say about cancellation?

### Question 4 — The circuit breaker

Your recommendation engine becomes unavailable. It is used only to personalize hotel search results.

What should happen when the circuit breaker opens? Would your answer change if the dependency were the authoritative payment processor?

### Question 5 — The lease-holder returns

Worker A acquires a ten-second distributed lock, pauses for fifteen seconds, then resumes. During the pause, Worker B acquired the expired lock.

Why might both workers now perform work? How do fencing tokens help?

### Question 6 — Unknown versus failed

A background workflow stores payment states as `pending`, `succeeded`, and `failed`.

A developer proposes marking every timeout as `failed` to simplify the model.

What's wrong with that? What additional state or mechanism is necessary?

---

# 16. Solutions and Discussion

### 1. Preserve the operation identity and reconcile

The timeout doesn't establish whether the payment succeeded.

The backend should preserve a stable payment operation ID, the provider request reference, the amount, the associated reservation, and the current uncertain status.

It can then query the provider or retry under a documented idempotency contract.

Creating a new payment operation merely because the previous HTTP attempt timed out risks duplicate charges.

### 2. Retries can multiply downstream load

If each layer retries independently, one user request can generate many downstream attempts during an outage.

This increases pressure on the failing service and may delay recovery.

A better design typically places retries at a deliberate layer, uses a shared overall deadline, applies exponential backoff with jitter, and limits total attempts.

Retries should target errors likely to be transient and operations that are safe to repeat.

### 3. Aborting communication doesn't necessarily abort remote execution

The client stopped waiting. The server continued and committed.

Neither necessarily violated its local contract.

The API must distinguish request cancellation from guaranteed cancellation of the underlying operation.

For operations with durable effects, clients need a stable way to determine the eventual outcome.

An explicit cancellation operation may be appropriate, but even then the server must define when cancellation is still possible.

### 4. Fallback depends on business semantics

If recommendations are optional, the application can return ordinary hotel search results without personalization.

A circuit breaker can protect the system from repeated calls to the unavailable recommendation service.

For an authoritative payment processor, bypassing the dependency doesn't justify confirming unpaid transactions.

The system may need to pause payment processing, preserve pending state, use an explicitly supported alternative provider, or report temporary unavailability.

Failure-handling policy must preserve the meaning of the operation.

### 5. Lease expiration doesn't stop an old worker

Worker A may continue executing after its lease expires. Worker B may legitimately acquire the lock, creating overlapping work.

Fencing tokens give each ownership generation an increasing identifier.

If the authoritative resource rejects operations from older generations, Worker A's stale token cannot override Worker B's newer ownership.

The protected resource must enforce the token; merely generating it is insufficient.

### 6. A timeout is not a definitive business failure

Marking every timeout as failed invents information the system does not possess.

The payment may already have succeeded.

The workflow needs a representation of unresolved or uncertain outcomes, plus reconciliation or safe retry behavior.

That may be an explicit `unknown` state or a `pending` state with an associated reason and recovery process.

What's essential is preserving uncertainty rather than falsely converting it into rejection.

---

# 17. Mental Model

A distributed system is a collection of independently operating components whose communication can fail without revealing the true state of the remote participant.

When designing a remote operation, ask:

- **What can fail?** The request, the response, the remote process, the network, or a dependency.
- **What can the caller actually know?** Distinguish observations from confirmed business outcomes.
- **What happens after a timeout?** The remote operation may still be running or may already have completed.
- **Can the operation be retried safely?** Use stable operation identities and idempotency where needed.
- **How is overload contained?** Apply deadlines, bounded retries, backoff, jitter, circuit breakers, and resource isolation.
- **How is uncertainty eventually resolved?** Preserve durable state, expose operation status, and reconcile ambiguous outcomes.

The principle worth carrying forward is:

**A remote call is not a local function call with higher latency. It's communication between independent systems that may disagree about what happened.**

Reliable distributed software makes that uncertainty explicit and designs recovery around it.

---

# Next Session — Consistency, Replication, and Availability

Our payment workflow now survives ambiguous timeouts and repeated requests. But another problem emerges when we introduce a PostgreSQL read replica: the primary commits a successful reservation, while the replica briefly continues reporting that it doesn't exist.

Both database servers are functioning correctly, yet they return different answers.

In **CS430-L02 — Consistency, Replication, and Availability**, we'll investigate replication lag, read-after-write guarantees, failover, network partitions, and the real meaning of consistency models and the CAP theorem.

---


---

## Next Lecture — CS430-L02: Consistency, Replication, and Availability

Continue in **CS430 — Distributed Systems and Reliable Workflows**.

## Further Reading

- **AWS Builders' Library — Timeouts, Retries, and Backoff with Jitter:** https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- **AWS Builders' Library — Making Retries Safe with Idempotent APIs:** https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- **AWS Prescriptive Guidance — Circuit Breaker Pattern:** https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html
- **Stripe — Idempotent Requests:** https://docs.stripe.com/api/idempotent_requests
- **MDN — AbortSignal:** https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal
- **Martin Kleppmann — Designing Data-Intensive Applications, 2nd Edition:** Chapters on distributed systems, consistency, and coordination.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS430-L01  DISTRIBUTED SYSTEMS & PARTIAL FAILURE — INTERVIEW GLANCE CARD

CORE MODEL
  Remote call ≠ local function with latency
  Partial failure: components fail independently; caller may not observe truth
  Timeout = caller's waiting bound — NOT remote outcome
  UNKNOWN is sometimes the only honest state
  Observation ≠ business result (ETIMEDOUT ≠ payment declined)

REQUEST OUTCOMES
  Fail before send / lost request / during process / after commit / lost response
  Same client timeout sequence can mean €450 charged once OR twice

TIMEOUTS & DEADLINES
  Bound wait; abort local fetch ≠ remote rollback / stop
  Deadline = overall budget; each hop gets remaining time (monotonic clock)
  Too short → false aborts; too long → resource pileup
  Payment timeouts need status lookup + idempotency, not just shorter waits

RETRIES
  Useful for transients; amplify load (retry storms: 3×3×3 = 27)
  Concentrate retries at one deliberate layer; shared deadline
  Exponential backoff + jitter (avoid synchronized waves)
  Retry only when operationally bounded AND semantically safe
  503 maybe; validation no; payment timeout = special care

IDEMPOTENCY
  Stable operation identity (Idempotency-Key) for one business intent
  Server: claim identity → PROCESSING → SUCCEEDED/FAILED; replay result
  Fingerprint params — same key + different amount = conflict (409)
  Concurrent claim needs atomic uniqueness/tx (race = double charge)
  Finite key retention (e.g. Stripe) — know provider contract
  Guarantee: repeated same intent ≠ unintended extra effects under protocol
  No provider idempotency → lookup/reconcile by stable reference; else policy

CIRCUIT BREAKER
  CLOSED → too many failures → OPEN (fail fast) → HALF-OPEN probes → …
  Doesn't repair dependency / prove payment status / make retries safe
  Fallback must preserve semantics (optional enrich vs payment authority)
  Combine with bounded retries; avoid synchronized half-open stampedes

BULKHEADS
  Isolate concurrency/pools per workload so one slow dependency can't eat all
  Bounded reject/queue > unlimited acceptance
  Reliability sometimes = do less work

TAIL LATENCY
  Many serial deps: end-to-end p99 suffers even if each is "99% OK"
  Parallelize independent calls; cancel/fallback carefully (Promise.all traps)

CLOCKS & LEASES
  Wall clock ≠ global order; monotonic for local elapsed only
  Lease expiry doesn't stop a paused worker → dual owners
  Fencing token: resource rejects older ownership generation

CORRELATION IDS
  Request ID ≠ Trace ID ≠ Operation ID ≠ Reservation ID ≠ Provider ref
  Retry: new request ID, SAME operation ID
  Observability helps investigate; durable state + reconcile = correctness

PAYMENT WORKFLOW PATTERN
  Durable payment operation → submit with stable key → success/fail/UNKNOWN
  Preserve pending on ambiguity; reconcile/retry safely
  Customer messaging must match what backend can guarantee (e.g. 202)
  Remote op state lives in durable records — not one HTTP success/fail

SENIOR LINE: make uncertainty explicit; design recovery around it.
```

