---
id: SE490-L01
course: SE490
title: "Putting It Together: Understanding a Running Application"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [CS101-S12]
prev: null
next: SE490-L02
---







# SE490 — Architecture and Systems Design Studio
## Lecture 01: Putting It Together: Understanding a Running Application

*How the foundations of computer science come together when an actual software system starts falling apart.*

**Estimated study time:** 85–105 minutes, including investigation, architectural reasoning, and exercises.

---

# 1. Friday, 16:42 — Everything Is on Fire

It's Friday afternoon. You're the senior developer responsible for a moderately successful SaaS platform called Meridian.

Meridian provides reservation management, customer analytics, automated reporting, and payment processing for independent hotels.

The company started with a handful of customers. Now it serves several hundred properties across Europe.

The engineering team consists of six developers.

The product has grown rapidly, but the architecture remains relatively straightforward.

A Vue frontend communicates with a Node.js backend. PostgreSQL stores the main application data. Redis supports background job processing. Workers generate reports and communicate with external services.

Most components run in Docker containers. A payment provider handles card transactions.

The system is not exceptionally sophisticated. That's part of its charm.

And until this afternoon, it was working rather well. At 14:00, the team deployed a release containing three changes.

First, a new customer analytics dashboard. Second, a report-generation improvement intended to reduce repeated work.

Third, an integration with a new hotel inventory provider. All three changes passed automated tests.

The deployment succeeded. For about fifteen minutes, everything looked normal.

Then the trouble began.

### 14:16 — The dashboard becomes painfully slow

Customer support reports that opening the analytics dashboard sometimes takes six seconds.

Previously, it took less than half a second.

The developers inspect the application servers.

CPU utilization is low.

Memory usage appears normal.

No major database outage has been reported.

### 14:27 — Two guests reserve the same room

A hotel manager calls support.

Two customers have received confirmations for the last available room on the same night.

Both payments appear to have succeeded.

The system has oversold its inventory.

### 14:39 — The reporting worker disappears

A background worker generating customer reports abruptly terminates.

The container runtime restarts it.

Several minutes later, the same thing happens.

The application logs don't contain a normal JavaScript exception.

The container reports exit code 137.

### 14:51 — A customer ID changes during processing

An external integration reports a mysterious issue.

The provider sent customer identifier:

`9007199254740993`

But the platform recorded:

`9007199254740992`

One digit changed.

The customer is furious, which is understandable. Account identifiers aren't supposed to behave like approximate weather forecasts.

Four incidents.

Four different symptoms.

And everyone is looking at you.

One developer says the new release must have introduced a memory leak.

Another blames PostgreSQL.

A third suggests doubling the number of application containers.

Someone proposes reverting the entire release.

And the product manager wants an explanation before the next customer calls.

This is where we're going to put eleven sessions of computer science to work.

Not by reciting definitions.

By investigating what actually happened.

---

# 2. The Architecture: What We're Dealing With

Before touching the code, let's establish the system's structure. Here's the simplified architecture.

```text
                       USERS
                         |
                         v
                  Vue Application
                         |
                         v
                    HTTPS / API
                         |
                         v
                  Load Balancer
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      Node API A     Node API B     Node API C
          |              |              |
          +--------------+--------------+
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
         PostgreSQL     Redis     External APIs
             |           |           |
             |           v           +── Payments
             |       Job Queue       +── Inventory
             |           |           +── Messaging
             |           v
             |     Report Workers
             |           |
             +-----------+
```

The architecture isn't automatically wrong.

A small cluster of stateless API servers backed by PostgreSQL and a job queue is a perfectly reasonable starting point for many SaaS applications.

But notice something. Each part of the system has different characteristics.

The browser has its own state and execution environment. The API servers are independent processes.

PostgreSQL maintains shared authoritative data. Redis coordinates background work.

Workers execute asynchronously. External providers operate independently and can fail without warning.

And the operating system determines the resources available to each process. These boundaries matter.

A variable in API server A isn't automatically shared with API server B.

A successful HTTP request doesn't mean every downstream operation succeeded.

A TypeScript interface doesn't validate an external JSON response.

And a Docker container doesn't have unlimited access to the host's resources. We already know all of these facts individually.

Now we'll see what happens when an application accidentally forgets them.

## The first rule of incident investigation

Before you diagnose anything, separate observations from assumptions. Consider the statement:

"The dashboard is slow because PostgreSQL is overloaded."

Is that an observation? No.

It's a hypothesis. The actual observation is:

"The dashboard's response time increased."

Perhaps PostgreSQL is overloaded. Perhaps the application performs unnecessary sequential queries.

Perhaps the connection pool is exhausted. Perhaps the server waits on an external integration.

Perhaps a synchronous JavaScript operation blocks the event loop. We don't know yet.

Similarly:

"The report worker has a memory leak."

That's not established merely because the process terminated with exit code 137. We need evidence.

Good engineering begins by resisting the urge to fall in love with the first plausible explanation. Let's examine what we know.

---

# 3. The Evidence Room

The team has collected the following diagnostic information.

The values in this case study are fictional, but chosen to illustrate realistic failure mechanisms.

Try forming your own hypotheses.

## Exhibit A — Dashboard performance

Before the release:

| Metric | Value |
|---|---:|
| Median response time | 210 ms |
| 95th percentile response time | 420 ms |
| Typical PostgreSQL queries per request | 4 |
| API CPU utilization | 20–30% |

After the release:

| Metric | Value |
|---|---:|
| Median response time | 3.9 seconds |
| 95th percentile response time | 6.2 seconds |
| Typical PostgreSQL queries per request | 101 |
| API CPU utilization | 15–25% |

The database itself isn't reporting major system-wide CPU saturation.

However, the dashboard endpoint now performs many more SQL statements. The new implementation contains this code:

```typescript
const customers = await customerRepository.find({
  take: 100
});

for (const customer of customers) {
  customer.lastInvoice =
    await invoiceRepository.findOne({
      where: {
        customerId: customer.id
      },
      order: {
        createdAt: "DESC"
      }
    });
}
```

## Exhibit B — The double booking

The booking endpoint contains:

```typescript
async function bookRoom(
  hotelId: string,
  stayDate: string
) {
  const inventory = await getInventory(
    hotelId,
    stayDate
  );

  if (inventory.available <= 0) {
    throw new Error("Sold out");
  }

  const reservation = await createReservation(
    hotelId,
    stayDate
  );

  await decreaseInventory(
    hotelId,
    stayDate
  );

  return reservation;
}
```

The application runs on three independent Node.js processes. The authoritative inventory count is stored in PostgreSQL.

The database has a unique constraint on reservation IDs, but no constraint that directly prevents inventory from becoming negative.

## Exhibit C — The disappearing worker

The report worker runs inside a container with a 512 MiB memory limit. Recent measurements:

| Metric | Before workload | Shortly before termination |
|---|---:|---:|
| V8 heap used | 84 MiB | 105 MiB |
| External memory | 92 MiB | 310 MiB |
| Process RSS | 240 MiB | 460 MiB |

The worker processes PDF documents using Node.js Buffers. The new implementation performs:

```typescript
const results = await Promise.all(
  reportJobs.map(async job => {
    const source = await downloadReportSource(job);
    const pdf = await generatePdf(source);

    return {
      reportId: job.id,
      pdf
    };
  })
);
```

Some generated PDF Buffers are several megabytes. One batch can contain sixty reports.

The container runtime reports that the process was OOM-killed.

## Exhibit D — The corrupted identifier

The external provider returns:

```json
{
  "customerId": 9007199254740993,
  "status": "active"
}
```

The Node.js integration parses the response:

```typescript
const data = await response.json();

const customerId = data.customerId;
```

Later, it serializes the value back into JSON. The recorded identifier is:

`9007199254740992`

---

# 4. A Short Investigation Before the Answers

Before reading the next sections, try answering these questions.

**Question one:** Which incident appears primarily related to algorithmic structure or unnecessary work?

**Question two:** Which incident involves concurrent access to shared state?

**Question three:** Which incident demonstrates the difference between JavaScript heap memory and total process memory?

**Question four:** Which incident is caused by the inability of a particular representation to preserve information exactly?

You can probably identify all four. But let's make things slightly harder.

Suppose someone proposes these remedies:

1. Add more Node.js API instances.
2. Rewrite the reporting worker in Rust.
3. Change the customer identifier's TypeScript type to `bigint`.
4. Add a mutex around the booking function.
5. Wrap the report batch in `Promise.allSettled()`.
6. Add another PostgreSQL index.

Which remedies might help? Which would fail to address the actual issue?

Which require more evidence? And which could create new problems?

Keep those questions in mind. We'll now investigate each incident properly.

---

# 5. Investigation One: The Dashboard That Did Almost Nothing, Very Slowly

Let's begin with the dashboard. The application CPU is mostly idle.

PostgreSQL isn't globally overwhelmed. Yet the endpoint takes several seconds.

Here's the suspicious code again:

```typescript
const customers = await customerRepository.find({
  take: 100
});

for (const customer of customers) {
  customer.lastInvoice =
    await invoiceRepository.findOne({
      where: {
        customerId: customer.id
      },
      order: {
        createdAt: "DESC"
      }
    });
}
```

What happens?

First, one database query loads 100 customers. Then the application executes one additional query for every customer.

That's 101 queries. And there's something particularly important about the loop.

Each query is awaited before the next query starts. The database operations are sequential.

Imagine each invoice query requires an average of 40 milliseconds, including its round trip and execution.

One hundred queries could consume approximately four seconds.

Meanwhile, the Node.js process spends much of that period waiting for results. The CPU doesn't need to be busy.

It's repeatedly waiting for a remote dependency. We've rediscovered the **N+1 query problem**.

## Why this is an algorithmic problem

At first glance, you might classify the problem as a database issue. And it certainly involves a database.

But the deeper cause is the structure of the work. We have `n` customers.

For every customer, we perform an independent database operation.

The number of round trips grows linearly with the number of customers.

More importantly, the latency of those round trips accumulates because they're performed sequentially.

This is a perfect example of why Big O alone doesn't tell the whole story. The loop is O(n) in the number of database operations.

But each operation has a substantial constant cost: network latency, query planning, index access, locks, and result transmission, not merely an arithmetic instruction.

One hundred small remote operations can be far slower than one appropriately designed operation that processes the same data in the database.

## The tempting fix: `Promise.all()`

A developer proposes:

```typescript
const invoices = await Promise.all(
  customers.map(customer =>
    invoiceRepository.findOne({
      where: {
        customerId: customer.id
      },
      order: {
        createdAt: "DESC"
      }
    })
  )
);
```

Would this improve latency? Possibly.

Instead of waiting sequentially, the application initiates the invoice queries concurrently.

But what has actually changed?

We still execute one hundred database queries. We've reduced serial waiting, subject to connection-pool and database capacity.

Worse, if dozens of dashboard requests arrive simultaneously, the application may create an enormous number of pending database operations.

Suppose fifty users open the dashboard, each request initiating one hundred invoice queries: that's potentially five thousand database operations competing for connections and execution capacity.

The database may become the next bottleneck.

We've converted a slow sequential workload into a potentially aggressive concurrent workload.

## A better question

Instead of asking:

"How can we execute these one hundred queries faster?"

Ask:

"Why do we need one hundred separate queries at all?"

The database already understands collections, relationships, sorting, and aggregation. We should exploit that.

One possibility is a set-based query retrieving the latest invoice for each selected customer.

For PostgreSQL, an approach using `DISTINCT ON` might look like this:

```sql
SELECT DISTINCT ON (customer_id)
       customer_id,
       id,
       created_at,
       total_amount
FROM invoices
WHERE customer_id = ANY($1)
ORDER BY customer_id,
         created_at DESC,
         id DESC;
```

Here, `$1` represents the selected customer IDs.

The query retrieves at most one invoice per customer, choosing the latest according to the specified ordering.

The `id` provides a deterministic tie-breaker if multiple invoices share the same timestamp.

This is only one possible SQL approach.

Window functions, lateral joins, or a differently structured query might perform better depending on the schema and workload.

We should examine an actual query plan before declaring a winner.

A suitable index might support lookup and ordering by customer and creation time. For example:

```sql
CREATE INDEX invoices_customer_latest_idx
ON invoices (
  customer_id,
  created_at DESC,
  id DESC
);
```

Whether that index is useful depends on query frequency, table characteristics, existing indexes, and the database optimizer.

## The principle we've recovered

CS110-L03 taught us to distinguish computational work from waiting.

CS110-L04 taught us that indexes organize information for efficient retrieval.

CS110-L05 taught us to avoid unnecessary repeated work. CS220-L03 taught us to investigate where execution time is actually spent.

CS320-L01 taught us that more concurrency isn't automatically better. All those ideas converge here.

**The best optimization is often not making a bad operation faster. It's eliminating the need for the operation.**

---

# 6. Investigation Two: The Room That Belonged to Two People

Now for the more serious incident. Two customers booked the same last room.

This isn't merely a performance problem. It's a violation of a business invariant.

Let's define that invariant carefully. For the simplified inventory model:

**Confirmed reservations must never exceed the available capacity for the corresponding hotel, room type, and stay date.**

The existing code checks availability. Then it creates a reservation.

Then it decreases inventory. But each step is a separate asynchronous operation.

Consider two requests running on different API instances.

```text
Initial availability: 1

API A                              API B
  |                                  |
  |── Read availability: 1            |
  |                                  |
  |                         Read availability: 1
  |                                  |
  |── Create reservation A            |
  |                                  |
  |                         Create reservation B
  |                                  |
  |── Decrease inventory              |
  |                                  |
  |                         Decrease inventory
  |                                  |
  v                                  v

Two reservations confirmed.
Only one room existed.
```

Every individual query may execute correctly, and neither PostgreSQL nor Node.js is necessarily malfunctioning.

The problem is that the application hasn't made the complete decision atomic.

## Why a local mutex is insufficient

Suppose someone proposes adding a mutex to the Node.js booking service.

That might prevent two requests inside one process from entering the protected section simultaneously.

But we have three API instances. Each has its own memory.

Each has its own mutex. Request A can acquire the mutex in process A.

Request B can simultaneously acquire the mutex in process B. Both believe they have exclusive access.

The locks don't coordinate across the shared inventory state.

A mutex protects only the scope within which it is actually shared and enforced. The authoritative inventory lives in PostgreSQL.

So the database needs to participate in enforcing the booking invariant.

## An atomic conditional update

Imagine a table:

```text
room_inventory
--------------
hotel_id
room_type
stay_date
available
```

For a simple one-date reservation, we could perform:

```sql
UPDATE room_inventory
SET available = available - 1
WHERE hotel_id = $1
  AND room_type = $2
  AND stay_date = $3
  AND available > 0
RETURNING available;
```

If the update affects no rows, the booking must not proceed as confirmed.

If it affects one row, capacity has been successfully claimed for that inventory record.

PostgreSQL coordinates conflicting updates to the same row through its transaction and locking machinery.

With an appropriate transaction, the inventory update and reservation creation can be committed together.

The conceptual workflow becomes:

```text
BEGIN TRANSACTION
       |
       v
Conditionally claim capacity
       |
       +── No capacity? → ROLLBACK
       |
       v
Create reservation record
       |
       v
COMMIT
```

But we're not finished.

## What about multi-night reservations?

Suppose a guest wants to stay three nights. The application must reserve inventory for November 10, 11, and 12.

What happens if capacity is available on the first two nights but not the third?

We can't leave the first two nights decremented while rejecting the booking.

A database transaction can coordinate changes across the relevant rows.

We should also consider acquiring conflicting locks in a consistent order to reduce deadlock risk.

And we need to ensure the relevant rows actually exist and represent the inventory model correctly.

A counter-based design is only one possible approach.

A system assigning specific physical rooms may use a different allocation and constraint strategy.

What matters is that the representation and transaction design enforce the business rule.

## Now add payment processing

Here's where the problem becomes substantially more interesting. A customer books the last room.

The inventory operation succeeds. The payment provider fails.

What happens to the reserved capacity?

Or perhaps the payment provider succeeds, but the database transaction fails.

Now what?

We cannot simply put an external payment API call inside a database transaction and pretend everything is atomic.

PostgreSQL cannot automatically roll back a charge made by an independent payment provider.

This is a distributed workflow problem. A practical design might involve:

1. Creating a temporary inventory hold with an expiration policy.
2. Recording a durable booking state.
3. Performing a payment authorization using an idempotency key where supported.
4. Finalizing the reservation after the payment outcome is established.
5. Releasing or expiring the hold when the booking cannot complete.
6. Reconciling uncertain payment outcomes.

The exact sequence depends on the payment provider and business requirements.

But the important idea is that we need explicit states and recovery behavior. For example:

```text
PENDING
   |
   v
INVENTORY_HELD
   |
   v
PAYMENT_AUTHORIZED
   |
   v
CONFIRMED
```

With alternative transitions for failure, cancellation, and expiration.

We need to define which guarantees can be enforced locally and how to recover when external steps fail.

## The principle we've recovered

CS110-L01 taught us to define the problem correctly. CS110-L04 taught us about state and representation.

CS220-L01 taught us that abstractions have limits. CS320-L01 taught us about races, concurrency, and atomicity.

Now those ideas combine into a real architectural decision.

**Correctness under concurrency must be enforced at the level where the shared state and business invariant actually live.**

---

# 7. Investigation Three: The Worker That Disappeared Without an Exception

Now let's investigate the reporting worker. The application occasionally terminates with exit code 137.

The container runtime reports an OOM kill. The worker's memory usage increased sharply before termination.

But look carefully at the metrics. The V8 managed heap grew only from 84 MiB to 105 MiB.

External memory increased from 92 MiB to 310 MiB. RSS increased from 240 MiB to 460 MiB.

What does this suggest?

It suggests that much of the growth is occurring outside the ordinary V8 managed heap.

And we know the worker handles PDFs using Node.js Buffers.

## The suspicious code

```typescript
const results = await Promise.all(
  reportJobs.map(async job => {
    const source = await downloadReportSource(job);
    const pdf = await generatePdf(source);

    return {
      reportId: job.id,
      pdf
    };
  })
);
```

Imagine sixty report jobs. Each produces a PDF occupying approximately eight MiB.

If all sixty results remain in memory simultaneously, the PDF payloads alone could require roughly:

`60 × 8 MiB = 480 MiB`

That's before accounting for:

- The Node.js runtime.
- Other application objects.
- Temporary generation buffers.
- Downloaded source data.
- Native allocations.
- Thread stacks.
- Other process memory.

Our container has a 512 MiB memory limit. But there's another detail.

`Promise.all()` doesn't impose a concurrency limit.

It initiates all the asynchronous operations immediately.

Depending on their implementation, many may allocate large buffers at overlapping times.

And the final `results` array retains every completed PDF until the combined operation finishes and the results are subsequently released.

## Why the V8 heap measurement misled the team

Node.js Buffers commonly use externally accounted backing memory.

Therefore, large Buffer allocations may be reflected more clearly in the `external`, `arrayBuffers`, and RSS measurements than in `heapUsed`.

Someone watching only the ordinary JavaScript heap might conclude that memory usage is fine.

But the operating system cares about the process's broader memory footprint.

And the container's cgroup enforces its memory allowance. The host might have gigabytes of free RAM.

That doesn't mean the container is allowed to use them.

## Is this a memory leak?

Not necessarily. This is an important distinction.

The worker may be retaining large amounts of memory only while processing a legitimate batch.

After processing finishes, the objects might become unreachable and eventually be collected.

But the process never reaches that point. Its peak memory usage exceeds the available limit first.

This is a **peak-memory and concurrency-design problem**.

It may also involve long-lived retention if results are cached or stored in global collections.

## A better design

We could impose bounded concurrency. For example, process at most a few reports simultaneously.

We could also avoid retaining every generated PDF in an array.

Instead, each report could be uploaded to persistent object storage as it completes.

Then the worker retains only a small amount of metadata. Conceptually:

```typescript
async function processReport(job: ReportJob) {
  const source = await downloadReportSource(job);

  const pdf = await generatePdf(source);

  await uploadReport(job.id, pdf);

  return {
    reportId: job.id,
    status: "completed"
  };
}
```

This still holds one complete PDF in memory.

For very large reports, streaming or incremental generation may reduce peak memory further, if the underlying libraries support it.

But the retention model has changed: not all sixty PDFs need to stay alive together.

With bounded concurrency, the maximum number of simultaneously processed reports becomes a deliberate engineering choice.

## What about increasing container memory?

It may be reasonable: perhaps report generation legitimately requires several hundred megabytes and a 512 MiB container is simply undersized.

But increasing memory isn't a substitute for understanding the workload.

If the next customer submits 600 reports instead of 60, an unbounded design could fail again.

We need both appropriate resource allocation and bounded resource consumption.

## The principle we've recovered

CS110-L02 taught us that representation has consequences. CS110-L03 taught us about resource complexity.

CS220-L02 taught us about memory retention and external allocations.

CS320-L01 taught us that unlimited concurrency can overwhelm dependencies.

CS320-L02 taught us how container memory limits are enforced. Here, all five ideas converge.

**A workload can be logically correct and still be operationally impossible because its peak resource requirements exceed the execution environment's limits.**

---

# 8. Investigation Four: The Identifier That Changed by One

Now for the strangest incident. The integration provider sends:

`9007199254740993`

Your application records:

`9007199254740992`

There is no arithmetic in the application. No explicit rounding.

No transformation intended to change the ID. And yet the value is different.

Let's examine the representation. The provider sent the identifier as a JSON number.

The Node.js application parsed it into an ordinary JavaScript `number`. JavaScript numbers use IEEE 754 binary64 representation.

As we learned in CS110-L02, this representation cannot preserve every sufficiently large integer exactly.

The largest safe integer is:

```javascript
Number.MAX_SAFE_INTEGER
// 9007199254740991
```

Our identifier is larger. So the parsed numerical value cannot preserve the original integer exactly.

Try:

```javascript
JSON.parse(
  '{"customerId":9007199254740993}'
).customerId;
```

The result is:

`9007199254740992`

The information was lost during parsing into the numerical representation. Now imagine that the TypeScript interface declares:

```typescript
interface CustomerResponse {
  customerId: number;
}
```

Does that help? No.

It merely tells the type checker that the value is a number.

The type says nothing about whether that number preserves the original identifier exactly.

What if we change the TypeScript type to `bigint`? Still not enough.

If the JSON value has already been parsed into an inaccurate JavaScript number, converting that number into BigInt doesn't reconstruct the missing digit.

## The proper fix

The integration contract should represent large identifiers in a form that preserves their exact value.

A decimal string is a common solution:

```json
{
  "customerId": "9007199254740993",
  "status": "active"
}
```

Now JavaScript can preserve the complete identifier as text.

If the application needs arbitrary-precision integer arithmetic, it can parse the string into BigInt.

But many identifiers don't require arithmetic at all. They are labels, not quantities.

A string may be the more appropriate domain representation.

## The more interesting lesson

This isn't merely a JavaScript quirk. It's an information-preservation problem.

The provider had an exact identifier; the application translated it into a representation incapable of preserving that value, and no later algorithm can reliably reconstruct information that was lost.

This is exactly the principle we encountered in our very first SE490 lecture.

Remember the daily unique-user counts?

Once individual user identities were discarded, the exact multi-day distinct count couldn't be recovered from daily totals alone.

The mechanism was different, but the underlying reasoning was the same.

**A representation must preserve the distinctions required by the problem.**

---

# 9. The Dangerous Temptation: Fix Everything With More Infrastructure

We have diagnosed four incidents. Now imagine the company holds an emergency architecture meeting where someone proposes a sweeping solution:

"We've outgrown the monolith. Let's split the system into microservices, add Kubernetes, move everything to event-driven architecture, and rewrite the performance-critical components in a faster language."

It sounds ambitious, modern, and expensive. Would it fix our problems? Let's examine them.

## The dashboard

The endpoint makes one hundred unnecessary sequential database queries. Splitting the backend into microservices doesn't eliminate them and may add network boundaries and operational complexity; the immediate solution is to improve the data-access pattern.

## The double booking

The booking workflow doesn't enforce the inventory invariant atomically. Moving it into a dedicated reservation microservice doesn't solve that: the same race can occur inside a microservice, or between several instances of it. The invariant still needs a properly enforced authoritative boundary.

## The report worker

The worker initiates too many memory-heavy operations and retains large intermediate results. Kubernetes might restart it after failure, but a restart doesn't solve the resource-consumption problem; it may simply repeat the same failing workload.

## The corrupted identifier

The API contract represents a large identifier as an unsafe numerical value. No amount of infrastructure solves that; the contract must preserve the identifier exactly.

## The bigger engineering mistake

We're confusing architectural sophistication with problem-solving: a more complicated architecture isn't inherently a better one. The relevant question is:

**Which change addresses the actual failure mechanism with acceptable cost and risk?**

Sometimes a large architectural transformation is justified: the system may have genuine independent scaling requirements, different teams may need clear service ownership, deployment coupling may have become a major organizational bottleneck, or workload isolation may require stronger boundaries. Those are valid reasons for architectural change. But four bugs do not automatically justify rebuilding the entire system, especially when targeted improvements can address them.

A strong engineer resists the temptation to turn every production incident into a platform migration.

---

# 10. A Practical Recovery Plan

We now understand the failure mechanisms. But knowing the causes isn't the same as safely restoring the system.

Imagine you're responsible for coordinating the response.

What should happen first?

We need to consider customer impact, immediate containment, permanent correction, and verification.

## Priority one: Protect financial and booking correctness

Double bookings can cause direct financial and reputational harm. We need to prevent additional overselling.

Depending on the system and risk, that might mean temporarily disabling affected booking operations or routing them through an already safe path.

Then we need to reconcile existing reservations and payments.

Which customers received confirmations? Which inventory records were affected?

Were payments authorized or captured? Which operations need cancellation, refunding, or manual intervention?

We shouldn't deploy a fix and pretend previous incorrect state no longer exists.

Correctness incidents often require both preventing future failures and repairing existing data.

## Priority two: Stop the report-worker crash loop

We have evidence of memory exhaustion. A temporary concurrency reduction could help contain the problem.

We may also need to pause unusually large batches.

Then investigate which report jobs were completed, which were partially processed, and which require retrying.

The job system must not treat a process crash as proof that all its external actions failed.

For example, perhaps a PDF was successfully uploaded before the worker died.

Retrying should not produce unsafe duplicate side effects.

## Priority three: Repair the data contract

The large identifier issue needs an exact representation.

Changing the external API contract may require coordination with the integration provider.

Until then, the application should avoid silently accepting unsafe numerical IDs.

A defensive boundary can reject identifiers that cannot be represented safely.

But remember that validation after ordinary JSON parsing cannot recover the original integer's exact digits.

If the source continues sending oversized integer literals, a parsing strategy capable of preserving the original numerical token may be required, or the provider must change its contract.

The important thing is not to silently persist corrupted identifiers.

## Priority four: Repair dashboard performance

The dashboard is unpleasantly slow, but the immediate business consequences may be less severe than corrupted reservations or payments.

The team can investigate the query pattern, build a set-based replacement, compare execution plans, and verify performance under representative load.

If the regression is severe enough to affect availability or overwhelm the database, its urgency increases.

Incident priority depends on impact, not merely technical elegance.

## A useful prioritization principle

**Correctness and customer harm generally outrank cosmetic performance improvements.**

A six-second dashboard is bad. Charging two customers for one room is worse.

Of course, performance failures can also become availability failures.

The key is to assess actual consequences rather than prioritizing whichever bug looks most interesting to fix.

---

# 11. Verification: How Do We Know We've Actually Fixed Anything?

This is where weak engineering processes often stumble: a developer identifies a plausible cause, writes a patch, runs a few tests, deploys, and announces success. But what evidence do we actually have? Let's take each fix from §10 in turn.

## Dashboard verification

We should verify that the returned data is correct, the SQL query count has decreased, query plans are appropriate, latency improves under representative workloads with acceptable database consumption, and performance doesn't deteriorate as the customer count grows.

A successful optimization isn't simply a lower number in one local benchmark.

It's a demonstrable improvement in the relevant production behavior without violating correctness.

## Booking verification

We need more than one ordinary successful booking test.

We should deliberately create concurrent attempts against the same limited inventory. For example:

1. Initialize inventory with one available room.
2. Start two independent booking operations.
3. Coordinate them to exercise competing access.
4. Allow both to finish.
5. Verify that no more than one booking is confirmed.
6. Verify that the final inventory state is valid.

We should also test transaction failures, payment failures, and recovery paths. The crucial thing to verify is the invariant.

**Confirmed reservations must not exceed capacity.**

The test should challenge that guarantee directly.

## Worker verification

We should process batches of different sizes and document characteristics, measuring peak RSS, heap usage, external memory, active report jobs, throughput, job completion and failure rates, and retry behavior.

We should verify that the worker remains within its memory budget under the expected workload.

And we should deliberately terminate a worker mid-processing to exercise the recovery behavior from Priority two.

A reliable background system must expect processes to disappear. Not because they are badly implemented.

Because processes can fail.

## Identifier verification

Test values near and beyond JavaScript's safe integer boundary. For example:

```text
9007199254740990
9007199254740991
9007199254740992
9007199254740993
```

Verify that the value received from the provider is preserved exactly throughout parsing, transport, storage, and later retrieval.

Test the actual API boundary, not merely a TypeScript function.

If the provider sends identifiers as strings, verify that the application doesn't accidentally convert them into unsafe numbers later.

## The principle

**A fix isn't proven by looking reasonable. It's supported by evidence that the original failure mechanism has been eliminated or appropriately controlled.**

That requires tests designed around actual failure modes. Not just tests that demonstrate the happy path.

---

# 12. The Hidden Fifth Problem: A System That Cannot Explain Itself

Let's imagine the team successfully fixes all four incidents. Two weeks later, another slowdown occurs.

The application logs say:

`Request failed`

That's it. No request identifier.

No dependency timings. No query-count information.

No clear separation between application errors and external service failures.

The team spends hours trying to determine which component is responsible. This reveals another kind of engineering deficiency.

Not a bug in one algorithm. Not a TypeScript mistake.

Not a memory leak. A lack of **observability**.

We will study observability properly in the production-engineering course, but it belongs in this discussion because the ability to investigate a system is itself an important design concern.

## A system should provide evidence about its behavior

Consider a request that travels through:

```text
Browser
   |
   v
API server
   |
   v
Database
   |
   v
External provider
   |
   v
Background worker
```

If something fails, we want to know where. A useful production system typically provides several kinds of evidence.

**Logs** describe relevant events.

**Metrics** quantify behavior over time.

**Traces** help reconstruct how one operation moves through components and where time is spent.

Together, they can help answer questions such as:

- Which endpoint became slow?
- Which database query dominated its latency?
- Did the application spend time executing JavaScript or waiting?
- Which external service failed?
- How many requests were affected?
- Did retries increase the load?
- Did a worker process a job twice?
- Did memory usage increase with batch size?

Observability doesn't automatically prevent failures. But it can dramatically reduce the time required to understand them.

And that's a form of engineering leverage. A well-designed system doesn't merely try to work correctly.

It helps its operators understand what happened when it doesn't.

---

# 13. The Architecture Review: What Would We Improve Long-Term?

Now that the immediate incident is under control, let's imagine an architecture review.

The objective isn't to redesign everything.

It's to identify improvements that reduce the likelihood and impact of similar incidents. I would focus on five areas.

## A. Stronger boundaries around external data

External APIs should not be assumed correct merely because their documentation describes a schema.

Incoming information should be validated against runtime constraints. Identifiers should preserve exactness.

Dates should retain their intended semantics. Monetary values should have explicit units and rounding rules.

Errors should distinguish missing information from unavailable systems.

The goal is to avoid allowing ambiguous or invalid external data to propagate into trusted application logic.

## B. Explicit ownership of business invariants

Critical rules need clearly identified enforcement points. For example:

- Inventory must not become oversold.
- A payment must not be charged twice for the same logical operation.
- A refund must be authorized.
- A subscription must not grant entitlements after its effective expiration.
- A reservation must satisfy the relevant date and capacity constraints.

These rules should be enforced by appropriate combinations of domain logic, database constraints, transactions, idempotency, and workflow state.

They shouldn't depend on every caller remembering to perform a sequence of checks in the correct order.

## C. Bounded resource consumption

Every expensive operation should have an understood resource model.

How much memory might it allocate? How many concurrent operations can run?

How many database connections can it consume? What happens when the workload grows?

Can the queue accumulate indefinitely? Does the system apply backpressure?

Are temporary results released? Can large data be streamed?

These aren't premature optimization questions when the system already has resource-related failures.

They're operational correctness questions.

## D. Data access designed around actual queries

Instead of relying blindly on convenient ORM calls, understand the generated database operations. Look for repeated queries.

Understand indexes. Measure query plans.

Avoid unnecessary data transfer. Pay attention to how workload growth affects query cost.

The point isn't to abandon ORMs. It's to stop assuming that elegant application code necessarily produces efficient data access.

## E. Recovery as a normal part of execution

External services fail. Containers restart.

Networks time out. Databases can reject transactions.

Queues may redeliver work. A mature application needs explicit recovery behavior for business-critical operations.

This includes durable state where appropriate, retries with clear semantics, idempotency, reconciliation, and operational visibility.

Reliable systems are not systems in which nothing ever fails.

They're systems designed so that anticipated failures do not automatically destroy correctness.

---

# 14. Your Capstone Challenge: You Are the Senior Engineer

Now it's your turn.

Imagine the company has given you ninety minutes to investigate the system and propose a plan.

You don't have to write an entire application.

You do need to reason clearly.

Spend approximately 25–35 minutes on this section if you want the full exercise.

## Task A — Diagnose Before Acting

You receive four reports:

1. Dashboard latency increased from 400 ms to 6 seconds.
2. Two concurrent bookings succeeded against the last room.
3. A report worker was OOM-killed under large batches.
4. A large customer identifier changed after JSON parsing.

For each incident, explain:

- The primary failure mechanism.
- What evidence supports that mechanism.
- What additional evidence you would seek.
- The immediate containment action.
- The permanent correction.
- How you would verify the correction.

Don't begin with a technology recommendation.

Begin with a causal explanation.

## Task B — Defend Your Architecture

A colleague proposes migrating the entire system to microservices.

Another proposes rewriting the backend in Go.

A third proposes replacing PostgreSQL with a distributed NoSQL database.

Would any of those changes directly solve the observed problems?

Which might be justified for other reasons?

What evidence would you demand before approving a major architectural change?

Describe the trade-offs rather than merely declaring one technology superior.

## Task C — Design a Safe Booking Operation

Sketch a reliable booking workflow for a room type with limited inventory.

Requirements:

- Several independent API instances.
- PostgreSQL as the authoritative inventory store.
- Multi-night reservations.
- External payment provider.
- Retries after network timeouts.
- Recovery from process crashes.
- No confirmed overselling.

Identify:

- The states of a booking.
- Where inventory is claimed.
- Where atomicity is required.
- Which external operations need idempotency.
- How failed bookings release capacity.
- What happens when the payment outcome is unknown.
- How the system detects and repairs inconsistent outcomes.

You don't need a perfect production design.

You need a coherent one.

## Task D — Explain the System to an Interviewer

Imagine this question in a senior full-stack interview:

> "A production API has become slow, sometimes oversells inventory, and occasionally runs out of memory. How would you investigate?"

You have three minutes to answer.

A strong response should demonstrate:

- Systematic diagnosis.
- Understanding of resource constraints.
- Knowledge of concurrency and database correctness.
- Awareness of operational trade-offs.
- Ability to prioritize customer impact.
- Confidence without pretending to know facts not yet established.

Try speaking your answer aloud.

If you can explain it naturally, you've probably understood more than if you merely recognize all the terminology.

---

# 15. An Example of a Strong Interview Answer

Here's how I might answer that question.

Not as a memorized script, but as an example of the reasoning and communication style worth developing.

> "I'd treat those as three potentially independent failure mechanisms rather than assuming there's one root cause.
>
> For latency, I'd begin by examining request-level timings and dependency traces. I'd want to distinguish CPU execution from database or network waiting. If the regression correlates with a sharp increase in query count, I'd investigate N+1 patterns, batching, and query plans before adding infrastructure.
>
> For overselling, I'd focus on the inventory invariant and how it's enforced under concurrent requests. An application-level availability check isn't sufficient if multiple requests can act on stale information. I'd inspect the transaction boundaries and ensure the authoritative data store enforces the required atomicity.
>
> For memory exhaustion, I'd compare V8 heap usage with RSS and externally allocated memory, particularly if the service handles buffers or large files. I'd also look at concurrency, caching, and retained object references. A container memory limit can be exceeded even when the host has spare RAM.
>
> I'd prioritize customer-impacting correctness problems, contain active failures, then reproduce and verify each issue with targeted tests. I wouldn't begin by migrating databases, rewriting the backend, or increasing resources until the evidence supported those changes."

Notice what this answer accomplishes. It doesn't pretend to have diagnosed a system without seeing evidence.

It identifies plausible mechanisms. It explains what evidence would distinguish them.

It proposes a sensible order of investigation. And it resists premature architectural conclusions.

That's exactly the sort of reasoning you want to demonstrate in a senior engineering interview.

---

# 16. One More Surprise: The Problems Are More Connected Than They Look

The four incidents look separate. They actually reveal four general constraints that appear throughout computing.

### Constraint one: Information

What information exists, and what can be inferred from it?

If a representation loses necessary information, no later computation can guarantee recovery.

### Constraint two: Work

How much computation, communication, and resource consumption does an operation require?

An inefficient workload can become impossible to execute at scale.

### Constraint three: Time and ordering

Which operations can overlap? Which actions depend on earlier results?

What happens when shared state changes between reading it and modifying it?

### Constraint four: Environment

What resources and guarantees does the execution environment provide? How much memory is available?

What happens when a process crashes? What is shared between instances?

What survives deployment?

These constraints are present in almost every nontrivial software system. And they interact.

A poorly represented data model can force expensive queries.

An inefficient query can increase response latency and concurrency pressure. Higher concurrency can increase memory usage.

Memory pressure can cause process termination. Process termination can trigger retries.

Retries can expose non-idempotent operations. And those retries can create duplicate payments or reservations.

Suddenly, the system is not a collection of independent functions. It's a network of interacting constraints.

This is why understanding isolated programming concepts is necessary but insufficient.

You also need to understand how those concepts interact when software becomes a real operating system.

---

# 17. What SE490 Was Really About

The foundations began with daily user counts that couldn't answer "unique across days" — not because the algorithm was slow, but because the information had been discarded. From there, the early lectures asked one foundational question each:

1. **Computation** — What are we computing, and do we have enough information?
2. **Representation** — Does encoding preserve the properties we need?
3. **Algorithms** — How much work, and how does it grow?
4. **Data structures** — How should information be organized for the operations we need?
5. **Algorithm design** — What structure lets us avoid unnecessary search?
6. **Languages** — What does the program mean, and what does the language guarantee?
7. **Memory** — What stays alive, why reachable, at what cost?
8. **Execution** — What is the machine actually spending time on?
9. **Concurrency** — What happens when operations share state?
10. **Operating systems** — What resources, isolation, and guarantees does the environment provide?
11. **JS/TS** — Does the code behave the way its author believes?
12. **This session** — Can evidence and reasoning improve an unfamiliar system without making it worse?

---

# 18. The Final Lesson: Software Engineering Is the Management of Assumptions

The four Friday incidents weren't usefully summarized as "programming mistakes." Each was an assumption that didn't hold:

The dashboard assumed one query per customer would remain inexpensive.

The booking endpoint assumed availability wouldn't change between check and consume.

The report worker assumed it could start an entire batch within its resource budget.

The integration assumed a JavaScript number could preserve every provider identifier.

Those assumptions weren't written down. They were embedded in the design — in code, or in the runtime environment — and failed when reality left their comfort zone.

Every system makes assumptions about data, timing, resources, failures, security, user behavior, and the outside world. Some are extremely reliable; others are merely convenient. The engineer's job is to identify the important ones and determine what happens when they stop being true.

A database transaction exists partly because we cannot assume concurrent operations arrive in a convenient order. Runtime validation exists partly because we cannot assume external data matches its declared schema. Idempotency, bounded concurrency, monitoring, and durable storage answer the same family of questions for retries, capacity, observability, and process death.

They're different answers to one engineering question:

**Which assumptions are unsafe, and what mechanisms do we need to preserve correctness when reality violates them?**

Tools, languages, frameworks, platforms, and AI assistants evolve. Software still manipulates information under resource constraints, changing state, and failing networks. The details change; the fundamental problems remain recognizable.

That is the purpose of SE490: a clearer mental model of the machinery beneath everyday work — so you can recognize problems earlier, ask better questions, choose abstractions, investigate failures, and defend decisions. Whether you write TypeScript by hand or supervise an agent that just generated thirty files:

**Being able to produce code and being able to understand a system are not the same thing.**

The second skill is what allows the first to become reliable engineering.

---

## Next Lecture — SE490-L02: Architecture Workshop: Design a Modern Web Product

Continue in **SE490 — Architecture and Systems Design Studio**.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE490-L01  RUNNING APPLICATION — INTERVIEW GLANCE CARD

CORE MODEL
  Separate observations from hypotheses ("dashboard slow" ≠ "Postgres overloaded")
  Four Friday incidents = four constraint classes interacting under load/change
  Fix mechanism first; infrastructure sophistication ≠ problem-solving

INCIDENT → MECHANISM → FIX
  Dashboard N+1     1 + n sequential invoice queries; CPU idle, waiting on DB
                    Promise.all still n queries → can stampede pool
                    Fix: set-based SQL (DISTINCT ON / window / join) + index
  Double booking    check-then-act race across API instances; local mutex ≠ shared
                    Fix: conditional UPDATE … AND available > 0 RETURNING in txn;
                    multi-night all-or-nothing; payment OUTSIDE DB txn
  Worker OOM 137    V8 heapUsed OK; external/RSS grow (Buffers); Promise.all unbounded
                    Peak memory ≠ leak; bound concurrency; upload then drop PDF
  Corrupted ID      JSON number > MAX_SAFE_INTEGER → IEEE754 loss on parse
                    TS number / bigint after parse cannot recover digits
                    Fix: string IDs (or safe parse); reject unsafe numerics

BOOKING WORKFLOW (distributed)
  PENDING → INVENTORY_HELD → PAYMENT_AUTHORIZED → CONFIRMED
  Hold + expire; Idempotency-Key; reconcile UNKNOWN payment outcomes
  Enforce invariant where shared state lives (Postgres), not in process memory

INVESTIGATION / PRIORITY
  Correctness & customer harm > cosmetic latency
  Contain → repair data → permanent fix → verify with failure-mode tests
  Concurrent booking test; peak RSS; ID boundary values; not happy-path only

OBSERVABILITY (5th problem)
  Logs / metrics / traces; request IDs; dependency timings; query counts
  System that can't explain itself prolongs every incident

LONG-TERM BOUNDARIES
  Validate external data; own invariants; bound resources; design for queries;
  recovery as normal (idempotency, retries, reconciliation)

FOUR CONSTRAINTS
  Information | Work | Time/ordering | Environment — they interact (retries amplify)

SENIOR LINE: manage unsafe assumptions; produce code ≠ understand a system.
```
