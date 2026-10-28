---
id: CS430-L03
course: CS430
title: "Scaling and Load Management"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S09]
prev: CS430-L02
next: CS430-L04
---








# CS430 — Distributed Systems and Reliable Workflows

## Lecture 03: Scaling and Load Management

*Why adding more servers can make an application slower, how bottlenecks migrate through a system, and why the fastest way to complete more requests sometimes involves refusing to accept them.*

---

# 1. The Deployment That Made Everything Worse

It's Monday morning, and your hotel-booking platform is experiencing a traffic surge.

The marketing team launched a successful promotion over the weekend. Reservation searches have doubled, new customers are registering, and the system is approaching the limits of its existing infrastructure.

Your production environment currently runs four Node.js application instances behind a load balancer.

The architecture is straightforward:

```text
                       INTERNET
                          |
                          v
                     LOAD BALANCER
                          |
            +-------------+-------------+
            |             |             |
            v             v             v
         Node.js       Node.js       Node.js
        Instance A    Instance B    Instance C
            |             |             |
            +-------------+-------------+
                          |
                          v
                      PostgreSQL
```

There's actually a fourth instance, but you get the idea.

CPU utilization on the application servers has been increasing, and the 95th-percentile API response time has climbed from 180 milliseconds to nearly 900 milliseconds.

The obvious solution seems to be horizontal scaling.

Instead of four application instances, let's run twelve.

You update the deployment configuration, and the orchestration system brings eight additional instances online.

For a moment, everything looks promising. The load balancer distributes traffic across more machines, and average CPU utilization per application instance falls.

Then the monitoring dashboard begins displaying something deeply unpleasant.

<escape>

```text
                         BEFORE       AFTER
Application instances       4           12
App CPU utilization        75%          32%
API p95 latency           900 ms      2,800 ms
Timeout rate                1%           9%
Database connections        68          196
Completed requests/s       820          610
```

</escape>

The numbers are illustrative, but the failure pattern is very real.

You tripled the number of application servers.

CPU utilization fell.

And the application became substantially slower.

How?

You investigate the database connection configuration.

Every Node.js instance maintains a PostgreSQL connection pool with a maximum of 20 connections.

With four instances, the theoretical maximum across their pools was:

\[
4 \times 20 = 80
\]

With twelve instances:

\[
12 \times 20 = 240
\]

The application now attempts to maintain far more concurrent database sessions.

PostgreSQL has not gained any additional CPU cores, memory bandwidth, storage throughput, or ability to resolve conflicting transactions. Instead, it faces more simultaneous queries, more memory consumption, and more opportunities for contention.

Some requests wait for locks. Others wait for I/O. Some hold connections while performing application work that doesn't need database access.

The number of concurrent operations increases, but the amount of useful completed work decreases.

We've encountered one of the most important principles in performance engineering:

**Scaling one component does not increase the capacity of a dependency it shares with every other component.**

In fact, scaling the wrong component can amplify pressure on the real bottleneck.

Today we'll investigate what scaling actually means, how load interacts with latency, why queues form, how resource saturation behaves, and how to determine which architectural change will genuinely improve a production system.

---

# 2. Scaling Is Not the Same Thing as Adding Servers

Let's begin by distinguishing three concepts that developers frequently mix together.

**Capacity** is the amount of work a system can sustain under defined performance and correctness requirements.

**Throughput** is the amount of work it actually completes per unit of time.

**Latency** is the time an individual operation takes from a specified starting point until completion.

They are related, but not interchangeable.

Suppose a backend handles 500 requests per second with a median response time of 80 milliseconds.

If traffic increases to 800 requests per second, the system might still handle everything successfully, but median latency could rise to 150 milliseconds.

At 1,000 requests per second, response times might grow dramatically and some requests may time out.

At 1,200 incoming requests per second, the system might complete only 700 requests per second because overload has made its internal execution less efficient.

That last result is especially important.

A system's completed throughput does not necessarily increase indefinitely as offered load increases.

A typical progression looks something like this:

```text
USEFUL THROUGHPUT
       ^
       |
       |                       ______
       |                   ___/      \__
       |                __/             \__
       |             __/
       |          __/
       |       __/
       |    __/
       |___/
       +--------------------------------------> OFFERED LOAD
                   Saturation      Overload
```

At low load, additional requests produce additional useful work.

As the system approaches saturation, queues form and contention increases.

Past a certain point, additional concurrency can consume resources without producing proportional throughput. Under severe overload, useful throughput may decline.

The particular shape depends on the workload and architecture. This isn't a universal mathematical curve.

But it's a useful mental model: **more incoming work does not automatically mean more completed work**.

### The distinction between throughput and goodput

Imagine your API receives 1,000 requests per second.

It successfully completes 700.

Another 200 time out, and 100 fail immediately.

Calling this a 1,000-request-per-second system is misleading.

It received 1,000 requests, but only 700 were useful completions.

The term *goodput* describes successfully completed, useful work.

For a hotel-booking system, goodput might mean confirmed reservations per second rather than HTTP requests processed per second.

An application could return 10,000 error responses per second and look spectacularly productive according to a badly chosen request counter.

Performance must be measured in terms of completed work that actually matters.

---

# 3. Vertical and Horizontal Scaling: Two Different Bets

There are two broad ways to increase capacity.

### Vertical scaling

Vertical scaling means giving an existing machine more resources.

For example:

```text
BEFORE                     AFTER

4 CPU cores                 16 CPU cores
16 GB RAM                   64 GB RAM
Moderate storage IOPS       Higher storage IOPS
```

For PostgreSQL, vertical scaling can be extremely effective.

A more powerful database server may execute queries faster, cache more data in memory, and process more concurrent operations.

Vertical scaling is often operationally simpler than distributing data across several independent database nodes.

But it has limits.

Hardware gets increasingly expensive at the high end, and not every workload benefits equally from additional cores or memory.

A single highly contended inventory row may still serialize conflicting updates regardless of how many CPU cores you purchase.

### Horizontal scaling

Horizontal scaling means adding more independent processing instances.

```text
BEFORE

        Load Balancer
              |
              v
           Node A


AFTER

        Load Balancer
              |
       +------+------+
       |      |      |
       v      v      v
     Node A Node B Node C
```

This works particularly well when requests can be distributed across instances without requiring substantial coordination between them.

A stateless Node.js API is often an excellent candidate.

One instance handles a reservation search while another handles a customer profile request.

But the application may still depend on shared resources:

```text
         Node A      Node B      Node C
            \          |          /
             \         |         /
              +--------+--------+
                       |
                       v
                    PostgreSQL
                       |
                       v
                   Storage I/O
```

If all three instances perform expensive queries against the same saturated database, adding Node D might make little difference.

### What about serverless?

AWS Lambda provides another form of horizontally scaled execution. More concurrent requests can lead to more concurrent function environments, subject to platform limits and configuration.

But database connections remain a potential bottleneck.

If hundreds of Lambda environments independently establish PostgreSQL connections, the database can experience a sudden connection surge.

Connection proxies and carefully managed concurrency can help, but serverless scaling doesn't repeal the capacity limits of the services downstream.

**The relevant question is never merely whether a component can scale. It's whether the complete request path can accommodate the additional work.**

---

# 4. The Bottleneck Determines the System

Imagine a hotel reservation request requiring four operations:

```text
1. Authenticate user
2. Read hotel configuration
3. Allocate inventory
4. Record reservation
```

Suppose each operation has a different capacity.

| Component | Sustainable capacity |
|---|---:|
| Authentication service | 5,000 requests/s |
| Hotel configuration cache | 20,000 requests/s |
| Inventory allocation | 700 requests/s |
| Reservation persistence | 1,500 requests/s |

These figures are hypothetical and assume one unit of each operation per request.

Which component limits the reservation workflow?

Inventory allocation.

Even if every other component can handle thousands of requests per second, a workflow requiring one inventory allocation per reservation cannot sustain more than the inventory subsystem permits.

Under these simplified assumptions, the maximum end-to-end rate is bounded by approximately 700 reservations per second.

Adding more authentication servers doesn't change that.

Making the cache twice as fast doesn't change that.

The slowest or most capacity-constrained required stage limits throughput.

### But bottlenecks move

Suppose you optimize inventory allocation and increase its capacity from 700 to 2,000 operations per second.

Now reservation persistence, at 1,500 per second, becomes the bottleneck.

You haven't removed bottlenecks from the system. You've moved the limiting constraint.

This is a normal part of performance engineering.

As one stage improves, another becomes more significant.

The same phenomenon occurs inside a computer: improving CPU execution may expose memory bandwidth limitations, while faster storage may reveal inefficient query execution.

A mature scaling strategy repeatedly identifies the current bottleneck instead of assuming the same component will always matter most.

### Amdahl's law makes an appearance

Recall Amdahl's law from our computer-science foundations.

If 20% of an operation's total execution time cannot benefit from a proposed parallelization, even infinitely accelerating the remaining 80% produces a maximum theoretical speedup of:

\[
S_{\max}=\frac{1}{0.2}=5
\]

With a finite parallelization factor \(N\), the idealized speedup is:

\[
S(N)=\frac{1}{0.2+\frac{0.8}{N}}
\]

This is not a direct formula for sizing arbitrary distributed services. But the intuition transfers.

The portion of a workflow that cannot scale proportionally eventually dominates the result.

In distributed systems, those limitations often appear as shared databases, coordinated transactions, central locks, rate-limited providers, or sequential business operations.

---

# 5. Why Queues Appear Before Servers Collapse

Let's introduce a small amount of queueing theory.

Suppose your backend receives requests at an average rate of 100 per second.

Each request spends an average of 200 milliseconds inside the system, including waiting and processing.

How many requests are in the system on average?

There's a beautiful relationship called **Little's Law**:

\[
L=\lambda W
\]

Where:

- \(L\) is the average number of requests in the system.
- \(\lambda\) is the average completed throughput.
- \(W\) is the average time each request spends in the system.

For a stable system, with consistent measurement boundaries and no long-term accumulation of work:

\[
L=100\times0.2=20
\]

Approximately twenty requests are present in the system on average.

They might be actively executing JavaScript, waiting for PostgreSQL, waiting for an external API, or sitting in an internal queue.

Now imagine average response time rises to two seconds while sustainable throughput remains 100 requests per second.

\[
L=100\times2=200
\]

The system now contains approximately 200 concurrent in-flight requests on average.

Nothing necessarily became more computationally expensive.

Many requests may simply be waiting.

Nevertheless, they consume memory, connection state, bookkeeping resources, and potentially downstream capacity.

### The hidden consequence of latency

Higher latency increases the amount of concurrent work required to sustain a given throughput.

That additional concurrency can create more contention, which increases latency further.

This feedback loop helps explain why overloaded services sometimes deteriorate rapidly rather than gracefully.

Little's Law doesn't tell us exactly why the waiting time increased. It provides a relationship between throughput, time, and concurrency.

Also, it is a steady-state relationship. If requests are accumulating indefinitely because arrival rate exceeds service capacity, the system is not in a stable equilibrium.

In that case, the backlog grows.

For example, if 300 requests per second arrive but only 250 can finish, approximately 50 additional requests accumulate every second until some mechanism limits the queue, rejects work, or changes the arrival or completion rates.

The queue has not solved the capacity mismatch.

It has merely made the mismatch visible over time.

---

# 6. Why Latency Explodes Near Saturation

Consider a simplified processing resource capable of completing one request every 10 milliseconds.

Its nominal service rate is:

\[
\mu=100 \text{ requests/second}
\]

Requests arrive at average rate \(\lambda\).

In a simple M/M/1 queueing model—Poisson arrivals, exponentially distributed service times, and one server—the average total time in the system is:

\[
W=\frac{1}{\mu-\lambda}
\]

This is an idealized model, not a direct prediction for a real Node.js application.

But it demonstrates something important.

| Arrival rate | Utilization | Average response time |
|---|---:|---:|
| 20 requests/s | 20% | 12.5 ms |
| 50 requests/s | 50% | 20 ms |
| 80 requests/s | 80% | 50 ms |
| 90 requests/s | 90% | 100 ms |
| 95 requests/s | 95% | 200 ms |
| 99 requests/s | 99% | 1,000 ms |

The underlying service time remains 10 milliseconds on average.

Yet near full utilization, waiting dominates.

At 99% utilization, average response time reaches approximately one second in this model.

Why?

Because almost no spare capacity remains to absorb random bursts.

A request arriving while the server is occupied must wait. When utilization is high, those waiting periods become more frequent and harder to clear.

Real systems have multiple workers, variable request costs, priority rules, locks, and changing service rates. Their exact behavior differs.

Still, the practical lesson survives:

**High utilization is not always high efficiency. Near saturation, small fluctuations can cause disproportionately large latency increases.**

This is why maintaining spare capacity can be an economically sensible reliability decision rather than waste.

A server sitting at 100% utilization might look efficient on a dashboard.

To a customer, it may look like a very expensive loading spinner.

---

# 7. The Connection Pool: A Small Queue Hiding in Plain Sight

Let's return to our production incident.

Every Node.js instance uses PostgreSQL through a connection pool.

A simplified configuration using `node-postgres` might be:

```typescript
import pg from "pg";

const { Pool } = pg;

const pool = new Pool({
  max: 20,
  connectionTimeoutMillis: 2000,
  idleTimeoutMillis: 30000
});
```

The pool maintains reusable PostgreSQL connections.

Instead of establishing a new database connection for every query, the application checks out an existing one when available.

That avoids repeated connection-establishment overhead.

But a pool also limits concurrency.

If the pool contains twenty connections and all are occupied, another query must wait until a connection becomes available—or fail when its configured acquisition deadline is exceeded.

```text
                 REQUESTS
                    |
          +---------+---------+
          |         |         |
          v         v         v
        Query A   Query B   Query C
          |         |         |
          +---------+---------+
                    |
                    v
              CONNECTION POOL
              [20 connections]
                    |
             +------+------+
             |             |
          Available       All busy
             |             |
             v             v
          Execute       Wait in queue
```

A connection pool is therefore both a resource-reuse mechanism and a concurrency-control mechanism.

### Why bigger pools aren't automatically faster

Suppose PostgreSQL can efficiently process 30 concurrent queries for your particular workload.

A pool of ten may underutilize the server.

Increasing the pool to twenty could improve throughput.

Increasing it to thirty might improve throughput further.

But increasing active database concurrency to 200 may cause more memory pressure, lock contention, I/O competition, and scheduling overhead.

Throughput might plateau or decline.

This is why PostgreSQL connection count isn't a straightforward performance knob.

There is no universal optimum such as "four connections per CPU core" that applies to every workload.

The right pool size depends on query durations, transaction behavior, database resources, concurrency requirements, and the number of application instances.

### Pool size is multiplied by deployment size

Imagine twelve Node.js instances, each with a maximum pool size of twenty.

The potential connection count is:

\[
12\times20=240
\]

Now add six BullMQ worker processes, each with its own pool of ten.

\[
240+(6\times10)=300
\]

And perhaps there are administrative applications, migration jobs, and monitoring clients.

The total can grow significantly beyond what any one application's configuration suggests.

Actual connections depend on pool behavior and demand; `max` is a ceiling, not a promise that every instance immediately opens all its connections.

But the capacity budget must account for every client category.

### Pool waiting versus query execution

Suppose an API takes 1,200 milliseconds.

Its actual SQL query takes only 20 milliseconds.

Where did the rest go?

Perhaps the request waited 1,100 milliseconds for a pool connection.

Optimizing the SQL query may offer little benefit if the dominant problem is waiting for access to the database.

Measure the two phases separately:

```text
Request received
       |
       v
Wait for pool connection     1,100 ms
       |
       v
Execute SQL                    20 ms
       |
       v
Serialize response             5 ms
       |
       v
HTTP response
```

This is one reason application-level latency measurements must be decomposed into meaningful stages.

A healthy database query plan doesn't establish that database access is healthy from the application's perspective.

---

# 8. PostgreSQL Has More Bottlenecks Than CPU

Let's imagine PostgreSQL CPU utilization is only 35%, yet requests are slow.

Does that mean the database has plenty of unused capacity?

Not necessarily.

A database can be waiting for resources other than CPU.

### Lock contention

Two transactions may need to modify the same inventory row.

The first transaction acquires the row lock.

The second waits.

If the first transaction holds its lock for several seconds, the second experiences corresponding delay even if PostgreSQL has many idle CPU cores.

Increasing the number of connections may simply create more waiting transactions.

### Storage I/O

A query may need pages that aren't already available in PostgreSQL shared buffers or the operating-system cache.

If the storage system is saturated or experiencing high latency, database processes can spend substantial time waiting for I/O.

CPU utilization may remain modest.

### Memory pressure

Sorting, hashing, and joining large datasets can require significant working memory.

PostgreSQL's `work_mem` influences memory available to individual operations, but it isn't a fixed memory allocation per database connection.

A query can execute multiple memory-consuming operations, and many queries can run concurrently.

Excessive concurrency can therefore multiply memory demand.

### Idle transactions

A transaction may be open without currently executing SQL.

PostgreSQL reports this as `idle in transaction`.

Such transactions can continue holding locks and snapshots, potentially interfering with concurrent work and MVCC cleanup.

This is particularly problematic when application code holds a transaction open while waiting for an external service.

### Connection overhead

PostgreSQL traditionally uses a separate backend process for each client connection.

Connections consume server-side resources even when they're idle.

Increasing `max_connections` also affects internal resource allocation.

Allowing thousands of connections doesn't mean PostgreSQL can efficiently execute thousands of expensive queries simultaneously.

The distinction is crucial:

**A resource can be saturated even when other resources are underutilized.**

A CPU dashboard alone cannot diagnose database capacity.

---

# 9. Investigating PostgreSQL Under Load

PostgreSQL exposes information about active sessions through `pg_stat_activity`.

A useful investigation might begin with:

```sql
SELECT
  pid,
  application_name,
  state,
  wait_event_type,
  wait_event,
  now() - query_start AS query_age
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_age DESC NULLS LAST;
```

This can reveal whether sessions are actively executing, idle, waiting, or sitting inside open transactions.

For example:

```text
state                  wait_event_type
-------------------------------------
active                 IO
active                 Lock
idle in transaction    Client
idle                   Client
```

These categories give us clues.

An active query with an I/O wait may be waiting for storage-related work.

An active query waiting on a lock suggests contention.

A session idle inside a transaction may be holding resources while waiting for application activity.

But `pg_stat_activity` is a snapshot, not a complete performance history. Some waits may be short-lived, and access to detailed information about other sessions depends on permissions.

### Find blocking relationships

PostgreSQL also provides `pg_blocking_pids()`.

For example:

```sql
SELECT
  pid,
  state,
  wait_event_type,
  pg_blocking_pids(pid) AS blocking_pids,
  query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

This helps identify sessions whose lock acquisition is blocked by others.

In a live production environment, inspect such information carefully. It can reveal sensitive SQL text, and cancelling or terminating sessions has operational consequences.

The goal is to understand the dependency chain before taking action.

### What about connection pool metrics?

On the Node.js side, `pg.Pool` exposes useful information:

```typescript
console.log({
  total: pool.totalCount,
  idle: pool.idleCount,
  waiting: pool.waitingCount
});
```

If `waitingCount` remains high, requests are accumulating while waiting for available connections.

But interpret this alongside database metrics.

If the pool waits because a few connections are occupied by slow transactions, increasing the pool size may worsen the situation.

If the database is underutilized and the pool is unnecessarily small, increasing pool capacity could be appropriate.

The same symptom—requests waiting for connections—can have different causes.

Diagnosis requires examining both sides of the boundary.

---

# 10. Connection Pooling Doesn't Have to Live Inside Node.js

For applications with many processes or highly variable concurrency, external connection pooling can help.

One well-known tool is PgBouncer.

Conceptually:

```text
             MANY APPLICATION CLIENTS
                       |
                       v
                    PgBouncer
                       |
                  SMALLER POOL
                       |
                       v
                    PostgreSQL
```

PgBouncer can multiplex client connections onto a smaller number of PostgreSQL server connections, depending on its pooling mode.

This is particularly attractive when application instances are numerous, short-lived, or rapidly scaled.

### Session pooling versus transaction pooling

In session pooling, a server connection remains associated with a client session for its duration.

In transaction pooling, a server connection can be returned to the pool at the end of each transaction and reused by another client.

Transaction pooling often enables greater connection reuse.

But it changes the semantics of connection ownership.

Applications cannot assume that session-local database state persists across transactions on the same underlying PostgreSQL connection.

Features involving session state, temporary tables, certain prepared-statement behaviors, session-level advisory locks, or other connection-specific mechanisms require careful compatibility analysis.

Modern PgBouncer versions can support some protocol-level prepared-statement behavior under appropriate configuration, but blanket assumptions about all prepared statements are unsafe.

The lesson is straightforward: external pooling is not merely an invisible performance upgrade.

It changes how application sessions map onto database sessions.

Still, for a large fleet of stateless application instances, it can be one of the most useful tools for controlling connection pressure.

---

# 11. The Node.js Event Loop: Low CPU Doesn't Mean Low Contention

Let's shift attention from PostgreSQL back to Node.js.

Suppose your server runs on a machine with eight logical CPU cores.

The monitoring dashboard reports approximately 13% total CPU utilization.

Yet the API is slow and event-loop latency is high.

How is that possible?

A single Node.js event-loop thread can be saturating one logical core while the other cores remain mostly idle.

Approximately one-eighth of the machine's total CPU capacity is being consumed.

A system-wide average can therefore hide a fully saturated execution thread.

Consider:

```typescript
app.get("/calculate", (req, res) => {
  const result = performExpensiveSynchronousCalculation();

  res.json(result);
});
```

If the calculation blocks the event loop for 500 milliseconds, unrelated requests handled by the same event-loop thread may be delayed.

Node.js can efficiently manage many concurrent I/O operations, but CPU-bound synchronous JavaScript still monopolizes the executing thread.

### Event-loop delay

Node.js provides `monitorEventLoopDelay()` through `node:perf_hooks`.

A simplified measurement:

```typescript
import { monitorEventLoopDelay } from "node:perf_hooks";

const histogram = monitorEventLoopDelay({
  resolution: 20
});

histogram.enable();

setInterval(() => {
  const p99Milliseconds =
    histogram.percentile(99) / 1e6;

  console.log({
    eventLoopDelayP99Ms: p99Milliseconds
  });

  histogram.reset();
}, 10000);
```

The histogram reports delay in nanoseconds, hence the conversion to milliseconds.

This doesn't directly tell you which function caused the delay.

It tells you that the event loop was unable to service scheduled work as promptly as expected.

Profiling and tracing can then help identify the responsible computation.

### Should you add more Node.js instances?

If your bottleneck is CPU-bound JavaScript execution on individual event loops, adding processes across available CPU cores may improve throughput.

Worker threads can also help with suitable CPU-intensive operations.

But if your application spends most of its time awaiting an overloaded database, adding more event loops isn't likely to solve the underlying problem.

Again, the bottleneck determines the appropriate scaling mechanism.

---

# 12. Backpressure: The Art of Not Accepting Everything

Now consider a system receiving 1,000 reservation search requests per second.

Its downstream database can safely support only 700 of those requests per second under the current workload.

What's the application supposed to do with the remaining 300?

A naive design accepts every request and lets them wait.

```text
Incoming requests: 1,000/s
        |
        v
Unlimited internal waiting
        |
        v
Database capacity: 700/s
```

The queue grows.

Latency increases.

Clients begin timing out.

Some clients retry, creating even more requests.

Now the system is performing work for requests whose callers may no longer be waiting.

A more deliberate design limits how much work is admitted.

```text
Incoming requests
        |
        v
Admission Control
        |
        +-- Capacity available -> Process
        |
        +-- Short queue available -> Wait briefly
        |
        +-- Overloaded -> Reject quickly
```

This is **backpressure**: communicating or enforcing the fact that a downstream component cannot safely accept unlimited work.

### Load shedding

One form of backpressure is load shedding.

Instead of allowing every request to time out eventually, the service rejects excess requests early.

For example:

```http
HTTP/1.1 503 Service Unavailable
Retry-After: 2
```

A fast, honest rejection may be better than waiting ten seconds and returning an error anyway.

But there's an important condition.

Clients must not interpret every 503 as permission to retry immediately and indefinitely.

Retries need budgets, backoff, jitter, and respect for the overall request deadline.

Otherwise, load shedding simply creates another source of repeated traffic.

### Prioritizing useful work

Not all requests have equal business value.

A system might prioritize completing already-authorized reservations over refreshing nonessential analytics.

It might degrade hotel recommendation quality while preserving search and booking.

It might stop accepting large reporting jobs during a database incident.

This isn't necessarily about assigning monetary value to users.

It's about preserving critical operations and preventing secondary workloads from consuming resources needed for core functionality.

### Beware overloaded queues

A bounded queue should have limits not only on its number of entries but also on waiting time.

A request that has waited ten seconds for a connection may already have exceeded the client's deadline.

Executing it now could waste resources.

Discarding expired work before it reaches an expensive dependency can improve goodput.

The principle is counterintuitive but important:

**A system can complete more useful work by refusing some work early instead of attempting everything and failing late.**

---

# 13. Scaling Background Workers Has the Same Problem

Remember BullMQ from SE320-L03.

A queue of pending jobs starts growing.

Your first instinct might be to increase worker concurrency:

```typescript
const worker = new Worker(
  "notifications",
  processJob,
  {
    connection,
    concurrency: 100
  }
);
```

But what if every job calls an external API limited to 50 requests per second?

Increasing worker concurrency may simply increase the number of simultaneous calls and rate-limit errors.

Those failures trigger retries.

Retries increase queue traffic.

The system may become less efficient.

### Queue depth isn't enough

Suppose two queues each contain 10,000 pending jobs.

Queue A processes 5,000 jobs per second.

Queue B processes 20 jobs per second.

The same queue depth has radically different operational meaning.

Useful metrics include job arrival rate, completion rate, processing duration, retry frequency, and age of the oldest waiting job.

The last metric is often particularly revealing.

A backlog that drains in two seconds is very different from one that requires eight minutes.

### Separate capacity domains

You might run separate workers for:

```text
Email Notifications
Payment Reconciliation
PDF Generation
Analytics Exports
```

Each workload has different resource requirements.

Email workers may be constrained by provider rate limits.

PDF workers may be CPU- or memory-intensive.

Payment reconciliation may depend on a tightly controlled external API.

Analytics jobs may place significant load on PostgreSQL.

Scaling them independently prevents one workload from monopolizing resources intended for another.

And for business-critical operations, concurrency settings should respect correctness constraints as well as performance limits.

---

# 14. Capacity Planning: How Much Traffic Can We Actually Handle?

Let's imagine you're preparing the platform for a large seasonal promotion.

Marketing expects peak traffic to reach 2,000 API requests per second.

Should you simply provision enough machines to handle that number?

Not yet.

You need to understand the request mix.

Suppose peak traffic consists of:

| Request type | Percentage | Rate |
|---|---:|---:|
| Hotel searches | 60% | 1,200/s |
| Hotel details | 25% | 500/s |
| Reservation creation | 5% | 100/s |
| Other APIs | 10% | 200/s |

These operations have very different costs.

A cached hotel-details request may use almost no database capacity.

A search may involve several database queries, external pricing integrations, or complex filtering.

A reservation creation request might perform a transaction involving inventory locks, payment state, and persistence.

Therefore, 2,000 requests per second doesn't define the resource requirement by itself.

The workload mix matters.

### Convert API traffic into dependency demand

Suppose each uncached search performs three PostgreSQL queries, while cache hit rate is 80%.

Search-related database demand is approximately:

\[
1200 \times 0.2 \times 3=720
\]

That's 720 queries per second from search misses, under these assumptions.

Add reservation writes and other API traffic, and the database demand becomes larger.

But this still doesn't tell us whether PostgreSQL can handle the workload. Queries differ in CPU time, I/O, memory, and lock behavior.

For capacity planning, measure representative resource consumption.

### Account for headroom

Suppose your measured sustainable capacity is 2,500 requests per second at acceptable p95 latency under the expected request mix.

Would you deliberately operate at 2,450 requests per second during the promotion?

Probably not.

Traffic is variable. Instances fail. Cache hit rates change. Dependencies slow down. New deployments sometimes increase resource consumption.

Capacity planning should preserve enough headroom for realistic disturbances.

The exact reserve depends on the system's reliability requirements, autoscaling speed, and failure model.

There's no universal rule that every service must run below a particular CPU percentage.

But planning for the median load while ignoring peak behavior and component failures is asking for trouble.

---

# 15. Load Testing: The Difference Between a Benchmark and an Investigation

A meaningful load test doesn't merely determine the largest number of requests a server can receive.

It investigates how behavior changes as demand increases.

A useful test gradually raises offered load while measuring throughput, latency, errors, and resource saturation.

For example:

```text
Stage 1:  200 requests/s
Stage 2:  400 requests/s
Stage 3:  600 requests/s
Stage 4:  800 requests/s
Stage 5: 1000 requests/s
```

At each stage, allow enough time to observe representative behavior rather than measuring only a transient burst.

The goal is to identify where latency begins increasing disproportionately, where queues accumulate, and where useful throughput plateaus.

### Open-loop versus closed-loop testing

This distinction is especially important.

A **closed-loop load generator** might maintain 100 concurrent clients, each sending a new request only after its previous request finishes.

If the server slows down, clients send fewer requests per second.

The offered load decreases automatically.

That can hide overload.

An **open-loop generator** attempts to submit requests according to a target arrival rate, independently of how long earlier requests take.

If the service slows down, concurrent requests accumulate.

This more directly exposes what happens when external traffic continues arriving despite increasing latency.

Both test models have legitimate uses.

Closed-loop testing is useful for understanding fixed-concurrency workloads.

Open-loop testing is useful for modeling independently arriving requests and identifying saturation behavior.

### Coordinated omission

Suppose a benchmark sends another request only after the previous one completes.

During a five-second stall, the generator sends no additional requests.

The measurements record one very slow request, but not the delays that real users arriving during those five seconds might have experienced.

This is a form of **coordinated omission**.

It can make latency distributions appear healthier than the real service would be under a continuing arrival stream.

A good performance test should be explicit about what workload it simulates and what latency it measures.

### Measure the tail

Average latency is not enough.

Imagine these response times:

```text
50% of requests:   50 ms
45% of requests:  100 ms
 4% of requests:  800 ms
 1% of requests: 5000 ms
```

The average hides the experience of users caught in the slowest portion.

Percentiles such as p50, p95, and p99 provide a clearer picture of the distribution.

But percentile values must be interpreted together with the sample size, workload, time window, and error rate.

An application can report a beautiful p99 among successful requests while silently timing out a large fraction of its traffic.

Always examine latency and failures together.

---

# 16. A Practical Lab: Watch a Saturated Resource Reject Work

Let's reproduce an important part of the opening incident without requiring a database.

We'll build a small Node.js HTTP server that simulates a shared resource with limited processing capacity.

The server accepts only a fixed number of concurrent operations. Additional requests may enter a bounded waiting queue. Once that queue is full, new requests receive HTTP 503.

This is a controlled demonstration of admission control and backlog growth—not an attempt to faithfully simulate PostgreSQL's internal execution engine.

### Step 1 — Build the server

Create `server.mjs`:

```javascript
import http from "node:http";

const CAPACITY = Number(process.env.CAPACITY ?? 8);
const MAX_WAITING = Number(process.env.MAX_WAITING ?? 32);
const SERVICE_MS = Number(process.env.SERVICE_MS ?? 100);

let active = 0;
let waiting = [];

let completed = 0;
let rejected = 0;

const sleep = ms =>
  new Promise(resolve => setTimeout(resolve, ms));

function acquire() {
  if (active < CAPACITY) {
    active++;
    return Promise.resolve();
  }

  if (waiting.length >= MAX_WAITING) {
    return Promise.reject(new Error("OVERLOADED"));
  }

  return new Promise(resolve => {
    waiting.push(resolve);
  });
}

function release() {
  const next = waiting.shift();

  if (next) {
    // Transfer the existing slot to the next waiter.
    next();
  } else {
    active--;
  }
}

const server = http.createServer(async (req, res) => {
  if (req.url === "/metrics") {
    res.writeHead(200, {
      "Content-Type": "application/json"
    });

    return res.end(JSON.stringify({
      active,
      waiting: waiting.length,
      completed,
      rejected
    }));
  }

  if (req.url !== "/work") {
    res.writeHead(404);
    return res.end();
  }

  const started = performance.now();
  let acquired = false;

  try {
    await acquire();
    acquired = true;

    // Simulated downstream processing.
    await sleep(SERVICE_MS);

    completed++;

    const duration = performance.now() - started;

    res.writeHead(200, {
      "Content-Type": "application/json"
    });

    res.end(JSON.stringify({
      durationMs: Math.round(duration)
    }));
  } catch {
    rejected++;

    res.writeHead(503, {
      "Retry-After": "1"
    });

    res.end("Overloaded");
  } finally {
    if (acquired) release();
  }
});

server.listen(3000, () => {
  console.log({
    port: 3000,
    CAPACITY,
    MAX_WAITING,
    SERVICE_MS
  });
});
```

The important part is the admission-control mechanism.

At most eight operations may occupy the simulated resource.

Additional requests can wait, but only 32 waiting requests are permitted.

Once both the active and waiting capacities are exhausted, the server rejects new requests.

For simplicity, this implementation doesn't cancel waiting operations when clients disconnect. That is one of the limitations we'll investigate.

### Step 2 — Calculate the theoretical capacity

Each operation occupies one resource slot for approximately 100 milliseconds.

With eight independent slots, an ideal upper bound for the simulated service is approximately:

\[
\frac{8}{0.1}=80
\]

So we expect roughly 80 completed operations per second under sustained demand, ignoring scheduling overhead.

This is a property of our deliberately simple artificial server.

A real database doesn't necessarily behave as eight independent slots with fixed processing times.

### Step 3 — Generate increasing load

Create `load.mjs`:

```javascript
const rate = Number(process.argv[2] ?? 50);
const durationSeconds = 8;

const results = [];
const pending = new Set();

const start = performance.now();
let nextRequest = start;
let sent = 0;

async function sendRequest() {
  const started = performance.now();

  try {
    const response = await fetch(
      "http://localhost:3000/work"
    );

    await response.arrayBuffer();

    results.push({
      status: response.status,
      ms: performance.now() - started
    });
  } catch {
    results.push({
      status: 0,
      ms: performance.now() - started
    });
  }
}

while (
  performance.now() - start <
  durationSeconds * 1000
) {
  const now = performance.now();

  if (now >= nextRequest) {
    const task = sendRequest();
    pending.add(task);

    task.finally(() => pending.delete(task));

    sent++;
    nextRequest = start + sent * (1000 / rate);
  } else {
    await new Promise(resolve => {
      setTimeout(resolve, Math.min(nextRequest - now, 5));
    });
  }
}

await Promise.allSettled([...pending]);

const successes = results.filter(r => r.status === 200);
const failures = results.filter(r => r.status !== 200);

const sorted = successes
  .map(r => r.ms)
  .sort((a, b) => a - b);

function percentile(p) {
  if (!sorted.length) return null;

  const index = Math.min(
    sorted.length - 1,
    Math.ceil(p * sorted.length) - 1
  );

  return Math.round(sorted[index]);
}

console.log({
  targetRate: rate,
  sent,
  successes: successes.length,
  failures: failures.length,
  p50SuccessMs: percentile(0.50),
  p95SuccessMs: percentile(0.95),
  p99SuccessMs: percentile(0.99)
});
```

This is a lightweight open-loop-style generator: it attempts to follow a target arrival schedule instead of waiting for each previous request to finish.

It isn't a production-grade benchmarking tool. Node.js timer precision, event-loop scheduling, and running the client on the same machine can affect the achieved arrival rate.

Still, it's adequate for investigating our small simulation.

### Step 4 — Run three load levels

Start the server:

```bash
node server.mjs
```

In another terminal:

```bash
node load.mjs 20
```

Then:

```bash
node load.mjs 60
```

Finally:

```bash
node load.mjs 120
```

At 20 requests per second, the simulated resource has ample spare capacity.

At 60, utilization is higher, but the server should generally keep pace under the assumed fixed service time.

At 120, incoming work exceeds the nominal 80-per-second service capacity.

The waiting queue grows, and the bounded admission mechanism eventually rejects excess requests.

Inspect:

```bash
curl http://localhost:3000/metrics
```

The interesting measurements are successful completions, rejected requests, and latency among accepted requests.

Notice that the server may remain operational under excess offered load because it refuses to accumulate unlimited work.

### Step 5 — Change the capacity

Restart the server with:

```bash
CAPACITY=16 node server.mjs
```

Repeat the experiment.

Because our simulated operations merely wait on timers, increasing concurrency to sixteen should increase nominal capacity.

This is what happens when independent operations genuinely benefit from more concurrency.

But that assumption is doing important work.

### Step 6 — Simulate contention

Replace:

```javascript
await sleep(SERVICE_MS);
```

with:

```javascript
const overload = Math.max(0, active - 8);

const penalty = overload * overload * 15;

await sleep(SERVICE_MS + penalty);
```

Now the simulated service becomes slower when more than eight operations run concurrently.

This deliberately models a resource whose effective processing time deteriorates under contention.

Repeat the experiment with capacities of eight and sixteen.

Increasing admitted concurrency may now reduce useful throughput or sharply increase latency.

The precise observed numbers depend on timing and load, but the conceptual result is the important part.

**Concurrency improves throughput only when the additional simultaneous work can actually make progress efficiently.**

### Step 7 — Consider real-world limitations

Our simulation has several simplifications.

It doesn't implement request deadlines or cancellation-aware queue removal.

It doesn't prioritize different workloads.

It assumes identical job costs.

It doesn't model network throughput, memory pressure, real database locks, or PostgreSQL scheduling.

For serious performance evaluation, use tools such as k6, Artillery, or another suitable load generator and test against representative infrastructure.

But the simulation illustrates the core mechanisms behind many production incidents: bounded concurrency, waiting, saturation, rejection, and contention.

---

# 17. A Senior Engineer's Production Investigation

Let's return to the original incident.

After scaling from four application instances to twelve, latency increased while app CPU decreased.

How should we investigate?

First, establish what changed besides instance count.

Did each instance open its own database pool? Did deployment alter connection limits? Did background workers scale too? Did cache hit rate change? Did traffic increase during the rollout?

Next, decompose request latency.

Measure time spent waiting for a database connection, executing SQL, waiting on external APIs, and performing application work.

Then inspect PostgreSQL.

Look at active sessions, waiting events, lock contention, long-running transactions, query duration, and resource utilization. Determine whether throughput is limited by CPU, storage, locks, connection pressure, or another resource.

Finally, change one capacity constraint at a time and measure the result under representative load.

A plausible solution might involve reducing per-instance pool size, adding an external connection pooler, shortening transactions, optimizing expensive queries, or imposing application-level concurrency limits.

Perhaps the database genuinely needs more hardware.

But buying a larger database before investigating a badly behaved transaction is an expensive way to avoid learning what happened.

### What would I change first?

Given the specific incident described at the beginning, I'd initially suspect database connection pressure and excessive concurrent query execution.

I would not immediately increase PostgreSQL's `max_connections`.

I'd inspect whether the existing connections are actively useful, waiting, or sitting idle inside transactions.

If the database is already saturated, I would reduce the amount of simultaneous work admitted to it while identifying the dominant queries and wait conditions.

Only after establishing the bottleneck would I decide whether to change pool sizes, query behavior, database resources, or application scaling.

That approach is less glamorous than adding Kubernetes nodes.

It's also considerably more likely to work.

---

# 18. Engineering and Interview Challenges

## Question 1 — More instances, worse performance

Your application scales from five instances to twenty. CPU utilization per instance decreases, but database latency triples.

Every instance maintains a connection pool of twenty.

What is your leading hypothesis, and how would you verify it?

## Question 2 — The low-CPU database

PostgreSQL CPU utilization is 25%, but reservation writes are slow.

`pg_stat_activity` shows many sessions waiting on locks.

Why would adding CPU cores or application instances fail to solve the problem?

## Question 3 — Little's Law

A stable API completes 200 requests per second, and average end-to-end latency is 300 milliseconds.

Approximately how many requests are in the system on average?

What happens to average concurrency if latency doubles while throughput stays unchanged?

## Question 4 — The misleading load test

Your benchmark maintains 100 concurrent clients. As the service becomes slower, the measured requests per second decrease automatically.

Why might this hide overload behavior? What alternative load-generation strategy would you consider?

## Question 5 — The saturated worker fleet

BullMQ workers process external API requests. The provider allows 100 requests per second.

Your queue backlog grows, so a developer increases worker concurrency from 50 to 500.

What could happen, and how would you redesign the processing limit?

## Question 6 — The unpleasant admission-control decision

Your service can reliably process 800 requests per second but receives 1,200.

Would you prefer accepting all requests and allowing them to wait, or rejecting some immediately?

Under what conditions might each approach make sense?

---

# 19. Solutions and Discussion

### 1. Connection pressure multiplied with deployment size

The potential total number of pooled connections increased from 100 to 400.

PostgreSQL may now face excessive active concurrency, memory use, and contention.

I'd compare connection-pool metrics with `pg_stat_activity`, query latency, wait events, and completed throughput.

The solution might involve smaller per-instance pools or an external pooler, but only after identifying whether the existing database connections are genuinely overloaded.

### 2. The bottleneck is coordination, not CPU capacity

Transactions waiting for locks aren't necessarily consuming much CPU.

If many operations compete for the same inventory rows, adding application instances can create more simultaneous contenders without increasing progress.

The appropriate investigation focuses on lock ownership, transaction duration, access ordering, and whether the application is holding locks longer than necessary.

Optimizing the transaction protocol can be more effective than increasing hardware capacity.

### 3. Average concurrency is sixty

Using Little's Law:

\[
L=200\times0.3=60
\]

Approximately sixty requests are in the system on average.

If average latency doubles to 600 milliseconds while completed throughput remains 200 requests per second:

\[
L=200\times0.6=120
\]

Average in-flight concurrency doubles.

This assumes a stable system and consistent measurement boundaries.

### 4. Closed-loop clients reduce offered load when the service slows

A fixed-concurrency benchmark whose clients wait for completion naturally generates fewer requests per second as response times increase.

That can hide the behavior of real traffic that continues arriving independently.

An open-loop arrival-rate test is useful for exposing queue growth and overload, provided the load generator can sustain the target rate and records errors and latency correctly.

Both models answer useful but different questions.

### 5. More workers may create more rate-limit failures

Increasing concurrency doesn't increase the external provider's permitted throughput.

The application may receive more 429 responses, trigger retries, and generate unnecessary work.

A better approach uses a shared rate limit appropriate to the provider's contract, bounded concurrency, retry policies, and monitoring of job waiting time.

If throughput cannot increase, the system must reduce, defer, prioritize, or combine incoming work.

### 6. Bounded admission usually protects useful throughput

If the offered load persistently exceeds capacity, accepting everything creates an ever-growing queue.

Latency increases, clients time out, and retries may amplify the problem.

Rejecting excess requests early can preserve acceptable latency for admitted work.

However, short bursts may be safely absorbed through a bounded queue when processing capacity is expected to catch up.

The choice depends on waiting-time deadlines, request importance, workload variability, and whether the operation can be deferred durably.

---

# 20. Mental Model

Scaling is fundamentally about increasing useful completed work while preserving acceptable latency, correctness, and operational cost.

When evaluating a production system, ask:

- **What is the current bottleneck?** CPU, I/O, locks, connections, memory, network, or an external dependency?
- **Where are requests waiting?** Distinguish actual execution time from time spent in queues.
- **How does concurrency affect service time?** More simultaneous work may increase contention rather than throughput.
- **What happens beyond sustainable capacity?** Identify the saturation point and overload behavior.
- **Can the system reject or defer work safely?** Use bounded queues, admission control, backpressure, and deadlines.
- **Which measurement represents success?** Prioritize goodput, latency distributions, error rates, and business outcomes over raw request counts.

The central principle:

**Scale the bottleneck, not merely the component that's easiest to replicate.**

A well-engineered system doesn't attempt infinite concurrency. It makes deliberate decisions about how much work can proceed, where work should wait, and when additional work should be rejected.

---

# Next Session — Microservices, Events, and Service Boundaries

Your growing SaaS is becoming difficult to maintain, so the team proposes splitting reservations, billing, notifications, and inventory into independently deployable microservices.

The new architecture looks cleaner—until creating a reservation requires coordinating database changes across several services, and one of them crashes halfway through.

In **CS430-L04 — Microservices, Events, and Service Boundaries**, we'll investigate how architectural boundaries become network boundaries, why distributed transactions are difficult, and when microservices genuinely justify their considerable complexity.

---


---

## Next Lecture — CS430-L04: Microservices, Events, and Service Boundaries

Continue in **CS430 — Distributed Systems and Reliable Workflows**.

## Further Reading

- **PostgreSQL — Number of Database Connections:** https://wiki.postgresql.org/wiki/Number_Of_Database_Connections
- **PostgreSQL — Connections and Authentication:** https://www.postgresql.org/docs/current/runtime-config-connection.html
- **PostgreSQL — Monitoring Statistics:** https://www.postgresql.org/docs/current/monitoring-stats.html
- **node-postgres — Connection Pooling:** https://node-postgres.com/features/pooling
- **node-postgres — Pool Sizing:** https://node-postgres.com/guides/pool-sizing
- **Node.js — Don't Block the Event Loop:** https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- **Node.js — Performance Hooks:** https://nodejs.org/api/perf_hooks.html
- **AWS Builders' Library — Using Load Shedding to Avoid Overload:** https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS430-L03  SCALING AND LOAD MANAGEMENT — INTERVIEW GLANCE CARD

OPENING INCIDENT
  4 → 12 app instances: app CPU down, p95/timeouts UP, DB connections explode
  Scaling one tier amplifies pressure on shared bottleneck (PostgreSQL)
  Scale the bottleneck — not the easiest-to-replicate component

CAPACITY VS THROUGHPUT VS LATENCY
  Capacity   sustainable work under defined SLOs/correctness
  Throughput completed work / time
  Latency    time per operation
  Offered load ↑ can ↓ useful completed work under overload
  Goodput = useful successful work (confirmed bookings ≠ error floods)

VERTICAL VS HORIZONTAL
  Vertical: bigger machine — simpler; contended row still serializes
  Horizontal: more instances — great if mostly independent; shared deps remain
  Serverless concurrency can stampede DB connections — proxies/limits matter
  Question: can the COMPLETE request path absorb more work?

BOTTLENECKS MOVE
  End-to-end rate ≤ slowest required stage
  Fix inventory → next limiter appears (Amdahl intuition: unscalable fraction wins)

QUEUES & LITTLE'S LAW
  L = λ W  (avg in-system = throughput × time-in-system) when stable
  Higher latency → more concurrency for same throughput → more contention
  Arrival > service → backlog grows; queue doesn't invent capacity
  Near saturation (M/M/1 intuition): tiny spare capacity → latency explodes
  High utilization ≠ high efficiency for customers

CONNECTION POOLS
  Reuse + concurrency limit; wait or timeout when exhausted
  Bigger pool ≠ faster if DB already contended
  Pool size × instance count × workers = total connection budget
  Separate pool wait vs SQL time in diagnostics
  PgBouncer: multiplex many clients → fewer server connections
    session vs transaction pooling — session state semantics change

POSTGRESQL BOTTLENECKS BEYOND CPU
  Lock waits, storage I/O, work_mem / memory pressure, idle-in-transaction
  Connections consume resources even idle; max_connections ≠ executable QPS
  Investigate: pg_stat_activity, wait_event, pg_blocking_pids
  App: pool.totalCount / idleCount / waitingCount — interpret with DB side

NODE.JS
  Low machine CPU can hide one saturated event-loop thread
  Sync CPU work blocks unrelated requests; measure event-loop delay
  More processes help CPU-bound JS; useless if waiting on saturated DB

BACKPRESSURE / LOAD SHEDDING
  Admit only what can finish; short queue; else fast 503 + Retry-After
  Clients need retry budgets/backoff — else shedding fuels storms
  Prioritize critical work; drop expired waiters before expensive deps
  Completing more useful work often means refusing some work early

BACKGROUND WORKERS
  Higher concurrency vs rate-limited APIs → retries → worse efficiency
  Queue depth alone insufficient — age of oldest job, arrival vs completion
  Separate capacity domains (email / reconcile / PDF / analytics)

CAPACITY PLANNING & LOAD TESTS
  Request mix matters more than raw RPS; convert to dependency demand
  Preserve headroom for bursts, failures, cache misses, deployments
  Ramp stages; observe where latency/queues/goodput break
  Closed-loop (fixed concurrency) can hide overload; open-loop keeps arrival rate
  Coordinated omission understates latency during stalls
  Measure p50/p95/p99 WITH error/timeout rates — not averages alone

SENIOR LINE: more concurrency can reduce completed useful work.
```

