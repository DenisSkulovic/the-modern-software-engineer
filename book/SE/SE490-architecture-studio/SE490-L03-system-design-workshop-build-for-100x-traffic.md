---
id: SE490-L03
course: SE490
title: "System Design Workshop: Build for 100× Traffic"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S12]
prev: SE490-L02
next: SE490-L04
---










# SE490 — Architecture and Systems Design Studio

## Lecture 03: System Design Workshop: Build for 100× Traffic

*One production SaaS. A hundredfold increase in traffic. A limited engineering budget. Which parts of the architecture would you change, which would you leave alone, and how would you know whether your decisions were correct?*

---

# 1. The Monday Morning Meeting

It's 09:15 on Monday, and the CEO has some rather exciting news.

Your hotel-booking platform has secured a partnership with a major European travel company. Starting in six weeks, the partner will begin directing customers to your booking engine.

Traffic is expected to increase dramatically.

The CEO presents a slide with one enormous number:

**100×**

One hundred times more requests than today.

The CTO looks at you.

You're the senior engineer responsible for proposing an architecture capable of handling this growth.

The existing system is a fairly ordinary Node.js SaaS application. It uses PostgreSQL for reservations, customers, payments, and hotel inventory. Redis provides caching and BullMQ processing. Static assets are delivered through a CDN, and the application runs on AWS.

Nothing particularly unusual.

In fact, the platform has been performing reasonably well.

The existing architecture looks like this:

```text id="hxwhsk"
                         INTERNET
                            |
                            v
                     CloudFront CDN
                            |
                            v
                     API Gateway / LB
                            |
                            v
                    Node.js Backend
                     (4 instances)
                            |
            +---------------+---------------+
            |               |               |
            v               v               v
        PostgreSQL        Redis          External APIs
          Primary       Cache/Jobs       Payments/Hotels
            |
            v
       Persistent Data
```

The team has six engineers.

The product is profitable, but infrastructure costs matter. Management doesn't want to triple the engineering team merely to maintain a more elaborate deployment architecture.

You have six weeks to prepare.

One developer immediately suggests Kubernetes.

Another proposes splitting the monolith into twelve microservices.

A third recommends migrating the database to DynamoDB because PostgreSQL apparently won't survive the coming apocalypse.

Someone else wants Kafka.

At this rate, the company will have seventeen distributed systems and no hotel reservations.

Before approving anything, you ask a question:

> What exactly does 100 times more traffic mean?

The meeting becomes considerably more useful.

This is where senior-level system design begins.

Not with technology selection, but with understanding the workload and the guarantees the business actually needs.

---

# 2. First, Define the Workload

Let's establish a concrete baseline.

The platform currently handles approximately 120 API requests per second during its busiest periods.

The partnership is expected to increase that peak to roughly 12,000 requests per second.

But requests aren't equally expensive.

After examining production telemetry, we develop the following approximate workload model.

| Operation | Share | Current peak | Projected peak |
|---|---:|---:|---:|
| Hotel search | 80% | 96/s | 9,600/s |
| Hotel details | 15% | 18/s | 1,800/s |
| Booking attempts | 1% | 1.2/s | 120/s |
| Other APIs | 4% | 4.8/s | 480/s |
| **Total** | **100%** | **120/s** | **12,000/s** |

These are hypothetical planning assumptions, not measured future demand.

And that's important.

The partnership may send many more customers who only browse, or it may generate a higher conversion rate. Demand could be concentrated on a handful of hotels, creating very different inventory contention from uniformly distributed traffic.

We therefore need scenarios, not merely one forecast.

A hundredfold increase in traffic doesn't necessarily imply a hundredfold increase in every resource requirement.

### The first surprising calculation

Suppose hotel searches currently require three database queries whenever they aren't served from cache.

At the projected peak:

\[
9,600\times3=28,800
\]

That's 28,800 search-related SQL statements per second without caching.

Now imagine a 90% application-cache hit rate for eligible searches.

Only 10% reach PostgreSQL:

\[
9,600\times0.10\times3=2,880
\]

We've reduced search-related database query volume by 90% without changing PostgreSQL itself.

But a 90% cache hit rate isn't guaranteed. Search keys may vary by dates, occupancy, currency, and filters. Many queries may have little reuse.

And availability-sensitive searches may require additional freshness checks.

The calculation demonstrates potential leverage, not a promise.

### Booking traffic is different

At 120 booking attempts per second, caching is far less helpful.

A booking might require inventory allocation, reservation persistence, idempotency checks, payment state transitions, and several durable workflow updates.

The system cannot simply return yesterday's reservation result.

Furthermore, every booking may involve an external hotel supplier and payment provider whose rate limits and latency we don't control.

Our architecture must therefore treat browsing and booking as different workload classes.

**Search traffic is predominantly a read-scaling problem. Booking traffic is a correctness and workflow-capacity problem.**

That distinction will guide almost every subsequent decision.

---

# 3. Establish the Success Criteria Before Changing Anything

Imagine we successfully handle 12,000 HTTP requests per second.

The monitoring dashboard looks wonderful.

Unfortunately, 20% of booking attempts time out, inventory allocations occasionally double-book rooms, and some customers are charged twice.

Have we successfully scaled?

Obviously not.

We need measurable requirements.

For our architecture exercise, let's establish illustrative targets.

| Requirement | Proposed target |
|---|---|
| Search API p95 latency | Under 300 ms |
| Hotel details p95 latency | Under 200 ms |
| Booking initiation p95 latency | Under 500 ms when durably accepted asynchronously |
| Confirmed booking correctness | No known violations of inventory invariants |
| Duplicate payment effects | Prevented under supported idempotency contracts |
| Accepted workflow recovery | Recoverable after process crashes |
| Availability | Defined separately for browsing and booking |
| Recovery | Explicit RTO and RPO agreed with the business |

These targets would require negotiation with product management and real performance measurements.

Also, a booking-initiation response isn't the same as completed supplier confirmation.

If the endpoint returns `202 Accepted`, the target measures how quickly the platform durably accepts the attempt. The actual booking-completion time needs a separate objective.

We should track business outcomes such as successful bookings per second, completion latency, unresolved-payment age, and supplier-confirmation failures.

This is a useful distinction in interviews:

**A service-level objective should describe a meaningful user or business outcome, not merely the speed of one internal component.**

Let's now examine the existing architecture.

---

# 4. Before Scaling, Find Out Where Time Goes

The most expensive mistake would be redesigning the system without understanding its current behavior.

We need a baseline.

I'd begin by instrumenting several representative request paths, particularly hotel search, hotel details, and booking creation.

For each path, I want to know:

- How much time is spent in Node.js?
- How much time is spent waiting for database connections?
- Which SQL queries dominate database execution?
- How often does Redis return cached results?
- How much time is spent waiting for suppliers and payment providers?
- What happens to latency and throughput as concurrency increases?

Suppose the hotel-search endpoint currently takes 180 milliseconds at p95.

A distributed trace reveals:

```text id="l2zvk8"
HOTEL SEARCH — 180 ms

Request validation           3 ms
Authentication               5 ms
Database pool waiting       35 ms
PostgreSQL queries         105 ms
Response transformation     12 ms
Serialization/network       20 ms
```

The numbers are illustrative, but the diagnosis is revealing.

More than half the time is spent executing SQL.

Another substantial portion is waiting for a database connection.

Splitting the service into microservices won't make those queries faster. In fact, additional service calls might make the request slower.

We should investigate PostgreSQL before introducing new network boundaries.

### Find the expensive queries

PostgreSQL's `pg_stat_statements` extension can aggregate execution statistics for SQL statements.

A representative query is:

```sql id="55fsoz"
SELECT
  calls,
  total_exec_time,
  mean_exec_time,
  rows,
  query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

The extension must be installed and configured appropriately.

Notice that we're ordering by total execution time rather than only average latency.

A query taking 10 milliseconds but executing a million times can consume more total database resources than a query taking two seconds once per day.

We should investigate both frequently expensive queries and unusually slow individual operations.

Then use execution plans:

```sql id="w002fa"
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...
```

As in CS330-L02, `EXPLAIN ANALYZE` actually executes the statement, so production use requires care.

We might discover missing composite indexes, N+1 queries generated by TypeORM, large offset pagination, unnecessary sorting, or queries retrieving far more columns than the frontend needs.

These are excellent optimization opportunities because they reduce the work performed on every request.

**Making one request cheaper is often more valuable than adding machines that perform the same inefficient request.**

---

# 5. Phase One: Make the Existing System Efficient

Suppose our investigation reveals that hotel searches repeatedly join several tables, filter by location and dates, and retrieve large intermediate datasets.

We can improve the queries and indexes before changing the deployment topology.

A reservation-history query might benefit from:

```sql id="cknbsg"
CREATE INDEX idx_reservations_customer_history
ON reservations (
  customer_id,
  created_at DESC,
  id DESC
);
```

A frequently used administrative query might require another composite index aligned with its tenant, status, and date filters.

But we don't index every possible combination of search parameters. Index maintenance increases write overhead, and large indexes consume memory and storage.

We choose indexes according to demonstrated access patterns.

### Pagination

Suppose the reservation history API uses:

```sql id="5fwxdz"
LIMIT 50 OFFSET 500000;
```

Large offsets can force PostgreSQL to traverse huge numbers of preceding entries.

Keyset pagination can avoid much of that work when the endpoint supports cursor-based navigation.

### ORM behavior

Suppose TypeORM retrieves 100 hotels, then separately fetches room types and amenities for each hotel.

A single API request might produce hundreds of database queries.

Batching associated data retrieval can drastically reduce round trips.

But one enormous join isn't automatically better: multiple one-to-many relationships can multiply the result rows.

We must inspect the generated SQL and the actual data volumes.

### Reduce unnecessary computation

If hotel descriptions, amenities, and property metadata rarely change, there's little reason to reconstruct them repeatedly.

That leads naturally to caching.

Notice the order of our reasoning.

We haven't introduced any new architecture yet.

We've reduced unnecessary database work and improved the existing application's efficiency.

This should happen before scaling expensive infrastructure to execute inefficient operations faster.

---

# 6. Phase Two: Separate Cheap Repeated Reads From Authoritative Decisions

Most projected traffic is browsing.

That's good news.

Hotel descriptions, photographs, amenities, destination information, and certain search results are often highly cacheable.

We can use several layers:

```text id="ftrnj6"
                       CUSTOMER
                          |
                          v
                    CloudFront CDN
                          |
                          v
                   Node.js Backend
                          |
                    Redis Cache
                          |
                       Cache Miss
                          |
                          v
                       PostgreSQL
```

Static photographs and frontend assets should generally be served through the CDN rather than application servers.

For application data, Redis can cache frequently requested hotel summaries and suitable derived search results.

But a cache should reflect the business semantics of the data.

### Different information needs different freshness

A hotel description can usually tolerate modest staleness.

A room category's amenities might be cached for several minutes.

Search availability can sometimes be cached briefly, provided booking operations revalidate inventory.

A final booking commitment cannot rely on stale cache availability.

For example:

```text id="adulvq"
SEARCH
  |
  v
Cached availability summary
  |
  v
Customer selects room
  |
  v
BOOKING
  |
  v
Authoritative inventory allocation
```

The search result is advisory.

The booking operation must obtain the actual resource.

This distinction allows aggressive read optimization without sacrificing reservation correctness.

### Cache stampedes

At 12,000 requests per second, cache expiration behavior becomes important.

If thousands of requests simultaneously miss a popular key, they may create a burst of expensive database work.

Useful mitigations include bounded cache regeneration, single-flight coordination, randomized TTLs, and stale-while-revalidate where staleness is acceptable.

We also need a Redis failure plan.

If Redis becomes unavailable, allowing all 9,600 search requests per second to fall straight through to PostgreSQL could overwhelm the database.

Fallback traffic must be bounded.

Some search requests may need to fail quickly or use degraded results rather than destroying the availability of the booking workflow.

This is the moment when caching and backpressure become inseparable.

---

# 7. Phase Three: Protect the Booking Path

Search optimization improves capacity.

But the company earns money when customers complete bookings.

That path deserves stronger guarantees than ordinary browsing.

Let's assume the platform manages inventory through PostgreSQL.

For each room type and night, it maintains authoritative capacity:

```text id="teme7l"
room_type_id
night
total_capacity
remaining_capacity
```

A booking for three nights must allocate inventory for all three nights atomically.

A conditional database update can prevent a counter from dropping below zero:

```sql id="cyui89"
UPDATE room_inventory
SET remaining_capacity = remaining_capacity - 1
WHERE room_type_id = $1
  AND night = $2
  AND remaining_capacity > 0
RETURNING remaining_capacity;
```

For a multi-night booking, the application executes the necessary allocations inside one transaction, verifies that every required night was successfully claimed, and creates the reservation record.

If any allocation fails, the transaction rolls back.

Competing transactions should acquire inventory rows in a consistent order to reduce deadlocks.

This isn't the only valid implementation. PostgreSQL exclusion constraints may be appropriate for individually assigned rooms, while externally supplied inventory requires a different protocol.

The key point is that inventory correctness must survive concurrent booking requests.

### Idempotency under increased traffic

At 120 booking attempts per second, retries are no longer unusual events.

Customers double-click buttons. Mobile networks disconnect. Clients encounter timeouts. Load balancers terminate connections.

Every booking attempt should have a stable identity.

A unique constraint such as:

```sql id="sh4b70"
UNIQUE (tenant_id, idempotency_key)
```

can help prevent independently creating the same accepted operation twice.

The implementation must also validate that repeated use of the key refers to the same request parameters and coordinate concurrent attempts.

For payment processing, a stable provider operation identity must be preserved across retries.

**Scaling cannot come at the cost of allowing one customer action to produce multiple reservations or charges.**

### Keep transactions short

A database transaction should not hold inventory locks while waiting several seconds for a hotel supplier or payment provider.

Commit the local state required to represent the next workflow step, then perform the external operation under a durable workflow protocol.

If the provider times out, preserve the uncertain state and reconcile it.

That's what CS430-L05 prepared us for.

---

# 8. A Hidden Bottleneck: The External Supplier

Let's return to our workload estimate.

We expect 120 booking attempts per second at peak.

Suppose the hotel supplier supports only 80 booking requests per second under the commercial agreement.

We can scale our application to a hundred instances.

We can buy an enormous PostgreSQL server.

We can add Redis clusters.

None of those changes increases the supplier's limit.

If all 120 booking attempts require that supplier, incoming demand exceeds its permitted throughput.

This is a hard external constraint.

### What are our choices?

We could negotiate a higher limit with the supplier.

We could distribute bookings among multiple suppliers if the business model supports it.

We could queue requests briefly, but only if the customer-facing contract and inventory-hold deadlines permit delayed processing.

Or we could reject excess booking attempts transparently.

What we should not do is quietly accept commitments that the platform has no reasonable capacity to fulfill.

### Admission control

A sensible design may distinguish:

```text id="mm8lgc"
Incoming booking attempt
          |
          v
Check admission capacity
          |
       +--+--+
       |     |
       v     v
     Admit  Reject/Defer
       |
       v
Persist booking intent
       |
       v
Durable workflow
```

For accepted asynchronous operations, the platform can return a stable booking-operation ID and `202 Accepted`.

But accepting work durably is a commitment to process it according to an explicit contract.

If the supplier can't complete requests before their holds expire, filling a queue with thousands of booking attempts doesn't solve the problem.

It creates a delayed failure factory.

We need realistic processing deadlines and capacity limits.

---

# 9. Phase Four: Scale the Application Without Overwhelming PostgreSQL

Now suppose we've optimized queries and protected critical workflows.

Application CPU becomes the next bottleneck.

This is where horizontal scaling becomes attractive.

We increase the number of stateless Node.js instances behind the load balancer.

```text id="xev8cu"
                    LOAD BALANCER
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
      Node A           Node B           Node C
        |                |                |
        +----------------+----------------+
                         |
                    Pooling Layer
                         |
                         v
                    PostgreSQL
```

But CS430-L03 exposed a dangerous trap.

Every instance may maintain its own PostgreSQL connection pool.

Suppose we scale to forty application instances, each configured with a maximum pool size of twenty.

Potential application connections:

\[
40\times20=800
\]

That's before accounting for workers, administration tools, and other services.

PostgreSQL doesn't necessarily benefit from hundreds of simultaneously active connections.

We need an explicit connection budget.

### External connection pooling

PgBouncer or an appropriate managed database proxy may help multiplex many application clients onto a smaller number of PostgreSQL connections.

AWS RDS Proxy is particularly relevant when using RDS and dynamic application or Lambda concurrency.

But proxies aren't magic.

Long transactions occupy server connections.

Session-local features can prevent effective connection reuse. In RDS Proxy, certain PostgreSQL session operations can cause connection pinning.

A database proxy reduces connection-management overhead; it doesn't make expensive queries disappear.

### Horizontal scaling needs shared-state discipline

Application instances should not rely on important mutable business state stored only in local memory.

Sessions, idempotency records, inventory holds, and workflow progress need appropriate shared or durable storage.

Otherwise, a request routed to a different instance may see a different state.

Local in-process caches are still useful for suitably stable data, but they shouldn't quietly become authoritative business databases.

The goal is that any healthy application instance can process an eligible request using well-defined shared state.

---

# 10. Phase Five: Separate Background Work From Interactive Traffic

At the new scale, booking events will produce substantial background activity.

Every successful reservation might require:

- A customer confirmation email.
- A hotel notification.
- An invoice.
- CRM synchronization.
- Analytics updates.
- Reconciliation scheduling.

These tasks don't all require the same latency, resources, or reliability strategy.

Instead of one general-purpose worker pool, we can separate them by workload.

```text id="cya5ww"
                 PostgreSQL Outbox
                        |
                        v
                   Job Publisher
                        |
                        v
                       Redis
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
     Notifications   Documents    Reconciliation
        Workers       Workers        Workers
```

The reservation transaction records durable event intent through an outbox.

The publisher transfers work into queues.

Workers process jobs with appropriate concurrency limits and retry policies.

But delivery may be repeated after crashes.

Consumers must be idempotent where their business effects require it.

### Scale the workers independently

Email delivery may be constrained by the provider's rate limits.

PDF generation may be CPU-intensive.

Reconciliation may require expensive external lookups.

There's little reason to scale all three identically.

We can give each workload independent capacity, concurrency, retry, and backlog policies.

This reduces contention and makes failures easier to contain.

### Don't forget the queue's own capacity

Redis must be configured appropriately for its role.

Disposable cache entries and important BullMQ job state should not casually share an eviction policy that can remove essential queue data.

We should monitor queue depth, processing latency, oldest waiting job, retry volume, and failure rates.

A queue that grows indefinitely isn't a scalability solution.

It's an increasingly large record of work the system cannot finish.

---

# 11. Should We Add Read Replicas?

Now imagine that PostgreSQL's primary still spends substantial resources serving read-heavy operational reports and customer-history queries.

We might introduce a read replica.

```text id="e2y4lg"
                       APPLICATION
                            |
                 +----------+----------+
                 |                     |
            Critical Reads          Reports
                 |                     |
                 v                     v
               PRIMARY  ----------> REPLICA
                         Replication
```

This can move some read workload away from the primary.

But remember CS430-L02.

Asynchronous replicas may lag.

A customer who creates a reservation and immediately reads from a replica could receive a stale result.

Therefore, we should route consistency-sensitive reads appropriately.

For example:

- Recently created reservations: primary.
- Authoritative payment and inventory decisions: primary or relevant owner.
- Historical reporting: replica, if lag is acceptable.
- General catalogue reads: replica or cache, depending on freshness requirements.

Read replicas are useful when actual read demand justifies them.

They are not an automatic prerequisite for 100× scale.

If most search requests are handled by Redis and the remaining SQL queries are efficient, the primary might remain sufficient for longer than expected.

Also, read replicas don't solve primary write saturation.

If booking transactions are exhausting write capacity, we need to investigate write behavior, contention, schema design, or hardware—not merely add read replicas.

---

# 12. What About Partitioning and Sharding?

Suppose our reservations table eventually grows to several hundred million rows.

Should we partition it?

Perhaps.

PostgreSQL supports declarative table partitioning, including range and hash partitioning.

A reservation table might be partitioned by a suitable date column:

```text id="ag65d5"
reservations
    |
    +-- reservations_2026_10
    +-- reservations_2026_11
    +-- reservations_2026_12
    +-- ...
```

Partitioning can improve maintenance and certain queries when their predicates allow effective partition pruning.

It can also make retention operations easier, such as dropping old partitions in systems whose retention rules permit it.

But partitioning isn't automatically a speed upgrade.

Poor partition keys can make queries more complicated or force access to many partitions.

Unique constraints and foreign keys also require attention to partition-key restrictions.

### Sharding is a much bigger step

Sharding distributes data across independently operating database partitions or servers.

For example:

```text id="8nye2s"
Tenant Group A ---> Database Shard 1
Tenant Group B ---> Database Shard 2
Tenant Group C ---> Database Shard 3
```

This can provide independent write capacity when workloads are appropriately partitioned.

But now cross-shard transactions, joins, migrations, balancing, and routing become more complicated.

Choosing a shard key is a major architectural decision.

If one hotel generates 40% of booking traffic, sharding by hotel ID might still create a very hot shard.

If one customer books across multiple hotels, some cross-hotel operations may become distributed workflows.

Sharding doesn't eliminate contention within a hot inventory key.

I'd strongly resist sharding until the evidence showed that vertical scaling, query improvements, appropriate partitioning, and workload separation were insufficient.

A PostgreSQL database that handles the workload reliably is not a problem demanding a distributed database.

---

# 13. Should We Split the Monolith Into Microservices?

At this point, we've scaled the application horizontally, introduced better caching, established durable workflows, and separated background processing.

Do we actually need microservices?

Not necessarily.

A modular monolith can still support substantial traffic.

Independent Node.js application instances can process requests concurrently while sharing PostgreSQL and appropriate supporting infrastructure.

The important constraints are workload, resource capacity, data correctness, and organizational development—not the number of services on the architecture diagram.

### A better question

Which components would genuinely benefit from independent deployment and ownership?

Perhaps search becomes a substantial independent subsystem with its own query indexes and scaling requirements.

Perhaps document generation deserves separate deployment because of CPU and memory consumption.

Perhaps supplier integrations become a major capability maintained by a dedicated team.

Those are legitimate candidates.

But extracting Inventory purely because it's busy may be a mistake if it introduces expensive distributed consistency problems without improving the actual contention point.

A separate Inventory Service backed by the same hot PostgreSQL row does not make that row less contested.

Likewise, moving Billing into a separate microservice doesn't increase the payment provider's rate limit.

### The architecture I'd defend

For a six-engineer team facing a six-week deadline, I'd retain the modular monolith as the core transactional application unless specific evidence justified extraction.

I'd deploy stateless API instances horizontally, separate background workers by resource profile, and isolate additional capabilities where there is clear operational value.

This architecture is less fashionable than a dozen microservices.

It's also easier to understand, deploy, debug, and recover.

And crucially, it leaves us with a feasible migration path should the organization grow.

---

# 14. The Proposed 100× Architecture

Let's assemble our candidate design.

```text id="bquihd"
                         CUSTOMERS
                            |
                            v
                       CloudFront
                            |
                            v
                    API Gateway / LB
                            |
                +-----------+-----------+
                |                       |
                v                       v
          Stateless APIs          Admission Control
                |                       |
                +-----------+-----------+
                            |
              +-------------+--------------+
              |             |              |
              v             v              v
          Redis Cache    DB Pooler      External Suppliers
                            |              |
                            v              v
                       PostgreSQL      Payment/Hotel APIs
                         Primary
                            |
               +------------+------------+
               |                         |
               v                         v
          Read Replica              Durable Outbox
               |                         |
               v                         v
         Reporting Reads             Job Publisher
                                         |
                                         v
                                   Worker Queues
                                         |
                     +-------------------+----------------+
                     |                   |                |
                     v                   v                v
                Notifications         Documents       Reconciliation
```

This is a logical architecture, not a requirement to deploy each box as a separate managed service.

Some components might be combined or omitted depending on measured demand.

Notice what's absent.

No mandatory Kubernetes cluster.

No twelve-service microservice fleet.

No distributed SQL database.

No Kafka requirement.

No globally replicated multi-primary inventory system.

Those technologies can be excellent in systems that need them.

But nothing in the stated requirements has yet demonstrated that they're necessary.

Our candidate architecture concentrates complexity where the business demands it: inventory correctness, payment recovery, high-volume reads, resource isolation, and bounded load.

---

# 15. Cost: The Architecture Has to Make Economic Sense

Let's imagine two proposals.

**Proposal A:** Introduce Kubernetes, multiple independent databases, a message-streaming platform, a service mesh, and dedicated observability infrastructure.

**Proposal B:** Optimize SQL, introduce targeted caching, increase stateless application capacity, use a managed database proxy if needed, and isolate background workloads.

Both might theoretically support the required traffic.

But one may require significantly more engineering time, on-call expertise, and operational maintenance.

Infrastructure cost isn't merely the monthly cloud bill.

There's also engineering complexity.

More services produce more deployments, configuration, monitoring, networking, permissions, and failure scenarios.

A six-person team has limited operational attention.

That is a finite resource too.

### Measure cost per useful operation

A useful economic metric is:

\[
\text{Cost per successful booking}
=
\frac{\text{Relevant operating cost}}
{\text{Successful bookings}}
\]

The exact accounting scope must be defined.

The numerator might include cloud infrastructure, payment and supplier API fees, messaging, storage, and observability costs. Engineering labor may be considered separately or included in a fuller economic assessment.

The denominator should count genuine completed bookings rather than attempted API requests.

A new architecture that doubles infrastructure cost but increases useful throughput tenfold may be a fantastic investment.

One that triples infrastructure cost while mostly improving already-fast endpoints may not be.

### Watch the less obvious costs

At high traffic, expenses can accumulate in unexpected places.

Log and trace ingestion can become expensive if every request generates large payloads.

Cross-region data transfer can become substantial.

Repeated external API calls can incur commercial charges.

Cache misses can drive database I/O.

Retries can multiply both infrastructure work and provider requests.

Therefore, performance optimization and cost optimization frequently overlap.

Reducing unnecessary work benefits both.

---

# 16. Failure Scenarios: Test the Architecture's Behavior, Not Just Its Speed

Before declaring the design successful, we should examine what happens when components fail.

| Failure | Intended behavior |
|---|---|
| One API instance crashes | Load balancer routes to healthy instances |
| Redis cache unavailable | Bounded fallback or degraded search; critical booking protected |
| PostgreSQL connection pool saturated | Backpressure rather than unlimited accumulation |
| Notification worker crashes | Job retried; duplicate side effects handled |
| Payment provider times out | Preserve uncertain state; reconcile |
| Hotel supplier unavailable | Reject, defer, or preserve pending operations according to contract |
| Read replica lags | Critical reads use primary or wait for sufficient replay |
| Primary database fails | Controlled recovery/failover under agreed RPO and RTO |
| Traffic exceeds capacity | Load shedding prioritizes useful work |

We should test these behaviors deliberately.

For example, terminate an API instance during a load test.

Disconnect Redis in a staging environment.

Simulate payment timeouts after the provider has committed the operation.

Delay worker acknowledgments and verify that repeated execution doesn't create duplicate effects.

Introduce artificial latency into supplier integrations.

These aren't exotic academic exercises. They're rehearsals for ordinary production failures.

### Beware the recovery storm

One particularly dangerous failure pattern occurs when a dependency returns after an outage.

Imagine 100,000 delayed jobs waiting to retry.

The dependency becomes healthy.

Every worker immediately begins sending requests.

The recovering system is overwhelmed and fails again.

A good recovery design uses bounded concurrency, backoff, jitter, and controlled backlog draining.

The system must remain stable during recovery, not merely during normal operation.

---

# 17. Rollout Strategy: We Have Six Weeks, Not Six Months

We need a practical plan.

I'd prioritize the work in roughly this order.

| Priority | Work | Why it comes here |
|---|---|---|
| 1 | Establish telemetry and production baseline | Avoid blind optimization |
| 2 | Validate booking correctness and idempotency | Prevent growth from amplifying financial errors |
| 3 | Optimize expensive SQL and ORM access | Reduce underlying work |
| 4 | Introduce targeted caching and stampede protection | Address dominant read traffic |
| 5 | Define connection budgets and admission limits | Protect shared dependencies |
| 6 | Scale stateless APIs and separated worker workloads | Add capacity where useful |
| 7 | Load-test realistic traffic and failures | Verify actual behavior |
| 8 | Add replicas or stronger infrastructure only if needed | Avoid premature complexity |

Some work can happen concurrently.

For example, one engineer can investigate search-query performance while another verifies idempotency and payment recovery.

But the architectural dependencies matter.

We shouldn't load-test booking correctness solely by measuring successful HTTP responses.

Nor should we deploy aggressive caching before defining which data is authoritative.

### Progressive rollout

Rather than immediately exposing the system to all partner traffic, I'd negotiate a staged introduction.

Perhaps:

```text id="hp04eg"
Stage 1:  2× current traffic
Stage 2:  5×
Stage 3: 10×
Stage 4: 25×
Stage 5: 50×
Stage 6: 100×
```

The stages are illustrative; actual progression should depend on measured outcomes.

At each stage, compare latency, error rates, completed booking throughput, database contention, queue age, and external-provider behavior against the defined thresholds.

If a stage violates the agreed limits, stop increasing traffic and investigate.

The purpose of progressive rollout isn't bureaucratic caution.

It helps reveal which constraint becomes limiting as the workload grows.

---

# 18. Practical Lab: Build a 100× Capacity Model

Let's perform a small planning experiment using JavaScript.

We won't pretend that a spreadsheet or script can accurately predict production performance. Instead, we'll use it to identify which assumptions drive resource demand and which bottlenecks can't be solved through ordinary horizontal scaling.

Create `capacity-model.mjs`:

```javascript id="q07dwe"
const baselineRps = 120;

const scale = Number(process.argv[2] ?? 100);

const workloads = [
  {
    name: "search",
    share: 0.80,
    dbOperations: 3,
    cacheHitRate: 0.90
  },
  {
    name: "hotel-details",
    share: 0.15,
    dbOperations: 1,
    cacheHitRate: 0.95
  },
  {
    name: "booking",
    share: 0.01,
    dbOperations: 8,
    cacheHitRate: 0
  },
  {
    name: "other",
    share: 0.04,
    dbOperations: 1,
    cacheHitRate: 0
  }
];

const totalRps = baselineRps * scale;

const results = workloads.map(workload => {
  const requests = totalRps * workload.share;

  const databaseOperations =
    requests *
    (1 - workload.cacheHitRate) *
    workload.dbOperations;

  return {
    workload: workload.name,
    requestsPerSecond: Math.round(requests),
    databaseOpsPerSecond: Math.round(databaseOperations)
  };
});

console.table(results);

const totalDatabaseOps = results.reduce(
  (sum, row) => sum + row.databaseOpsPerSecond,
  0
);

const bookingRps =
  totalRps *
  workloads.find(w => w.name === "booking").share;

const supplierLimit = 80;

console.log({
  scale,
  totalRps,
  totalDatabaseOps,
  bookingRps,
  supplierLimit,
  supplierOverCapacity: bookingRps > supplierLimit
});
```

Run:

```bash id="kd2c1v"
node capacity-model.mjs 1
node capacity-model.mjs 10
node capacity-model.mjs 100
```

At 100×, the model produces approximately:

| Workload | Requests/s | Database operations/s |
|---|---:|---:|
| Search | 9,600 | 2,880 |
| Hotel details | 1,800 | 90 |
| Booking | 120 | 960 |
| Other | 480 | 480 |
| **Total** | **12,000** | **4,410** |

Remember that these are counts of hypothetical database operations, not measured PostgreSQL capacity requirements.

One complicated query can consume more resources than dozens of simple indexed lookups.

Nevertheless, the model reveals useful relationships.

### Investigation A — Cache effectiveness

Change search cache hit rate from 90% to 50%.

How much does database demand increase?

The search workload now produces:

\[
9,600\times0.5\times3=14,400
\]

database operations per second.

Compared with 2,880, that's five times more search-related database work.

This shows why cache-key design, reuse patterns, and stampede behavior matter so much.

### Investigation B — Query optimization

Return cache hit rate to 90%.

Now reduce uncached search-query cost from three database operations to one.

Search-related database operations fall from 2,880 to 960 per second.

The actual performance benefit depends on the cost of the old and new queries, but the demand reduction is substantial.

### Investigation C — The supplier bottleneck

Our booking workload requires 120 attempts per second.

The supplier limit is 80.

Even with unlimited application and database capacity, we cannot sustain 120 supplier-dependent booking attempts per second if the provider allows only 80.

The model correctly flags the mismatch.

This is a reason to negotiate provider capacity, redesign workload distribution, or control admission—not add more Node.js instances.

### Investigation D — Change the workload mix

Suppose the partner sends fewer browsers but more customers who reach checkout.

Increase booking share from 1% to 3%, adjusting another workload share so the total remains 100%.

Now booking attempts reach 360 per second at the same total request volume.

That's a completely different scaling problem.

### What the model cannot tell us

It doesn't measure latency, contention, storage I/O, network delays, query complexity, replication overhead, or provider failure behavior.

It assumes stable request proportions and cache hit rates.

It treats every database operation as equal.

A real capacity plan requires representative load testing and production telemetry.

But the script has accomplished something useful: it makes assumptions visible.

And visible assumptions can be challenged, measured, and corrected.

That's considerably better than designing an architecture around an unexplained estimate of 12,000 requests per second.

---

# 19. Final Architecture Review: Defend the Design

Imagine you're presenting your proposal to a group of senior engineers.

One asks:

> Why haven't you introduced microservices?

A strong answer would explain that the existing modular monolith preserves useful transactional boundaries, and the immediate constraints are read throughput, connection pressure, booking correctness, and supplier capacity.

Independent services may become valuable later, but extracting them now would introduce coordination risks without necessarily improving those bottlenecks.

Another asks:

> Why are you still using PostgreSQL?

Because the measured workload hasn't demonstrated that PostgreSQL is insufficient.

We have substantial opportunities in query optimization, caching, connection management, vertical scaling, read replicas, and workload separation.

A distributed database migration would be a major correctness and operational project requiring much stronger justification.

Another asks:

> What happens if Redis fails during the promotion?

We use bounded fallback and admission control.

The platform may temporarily degrade or reject some noncritical search traffic rather than allowing cache misses to overwhelm PostgreSQL and threaten bookings.

Another asks:

> How do you prevent double bookings at 120 attempts per second?

By enforcing inventory invariants at an authoritative transactional boundary, using appropriate conditional updates, locks, constraints, or supplier-side allocation protocols.

Increasing concurrency doesn't weaken those invariants.

Another asks:

> How do you know the architecture can handle 100× traffic?

And this is perhaps the most important question.

You don't know yet.

You've produced a reasoned architecture hypothesis.

You know how its components are expected to behave and which constraints are likely to matter.

But the proposed capacity must be verified through representative load testing, failure testing, and progressive production rollout.

**Senior engineering isn't pretending to possess perfect foresight. It's making explicit assumptions, choosing defensible trade-offs, and establishing a process for correcting the design when evidence disagrees.**

---

# 20. Engineering and Interview Challenges

## Question 1 — The surprisingly effective optimization

A system receives 10,000 search requests per second.

Each uncached request performs four database queries.

A Redis cache achieves a 95% hit rate.

Approximately how many database queries per second remain from this workload, ignoring cache-management overhead?

What assumptions might make the estimate misleading?

## Question 2 — The hot inventory record

You add twenty Node.js instances, but throughput for one popular hotel's final room barely improves.

The database shows heavy row-lock contention.

Why doesn't horizontal scaling solve this problem?

What kinds of design changes might help?

## Question 3 — The premature microservice proposal

Your team wants to separate Inventory into its own service to improve scalability.

But Inventory will continue using the same PostgreSQL tables and the same contested capacity rows.

What performance benefit should you expect?

What new risks might the separation introduce?

## Question 4 — The cache outage

During peak traffic, Redis becomes unavailable.

The application immediately routes every cache miss to PostgreSQL.

Within seconds, the database is overloaded.

How should the system have been designed differently?

## Question 5 — The successful booking with a failed email

A booking commits successfully.

The email worker crashes after sending the confirmation but before acknowledging the job.

BullMQ retries.

What must the system guarantee, and what may it reasonably tolerate?

## Question 6 — The final recommendation

You have six weeks, six engineers, and a projected 100× traffic increase.

Would you prioritize Kubernetes, database sharding, Redis caching, SQL optimization, or microservice extraction?

Explain how you'd determine the actual order rather than simply naming your favorite technology.

---

# 21. Solutions and Discussion

### 1. Approximately 2,000 database queries per second

Five percent of 10,000 requests miss the cache:

\[
10,000\times0.05=500
\]

At four queries per miss:

\[
500\times4=2,000
\]

The estimate assumes independent repeated reads, a stable hit rate, and four database queries for every miss.

It ignores query-cost variation, cache invalidation, stampedes, and the possibility that hot keys dominate the workload.

### 2. The bottleneck is serialized access to shared state

All application instances compete for the same inventory row.

More instances create more contenders, not more inventory-update capacity.

Potential improvements include shortening transactions, removing unnecessary work while locks are held, reducing redundant allocation attempts, and investigating whether the inventory model creates avoidable hot spots.

But if every successful operation must modify one authoritative contested resource, some serialization may be inherent to the business invariant.

### 3. The split may provide little throughput improvement

If the same database rows remain the bottleneck, putting an HTTP service in front of them doesn't eliminate contention.

It may add network latency, timeout ambiguity, retries, and a new deployment dependency.

The separation could still provide independent ownership or resource isolation, but those benefits need to justify the additional complexity.

### 4. Cache failure requires bounded degradation

The backend should limit the number of fallback queries reaching PostgreSQL.

Possible measures include admission control, short request queues, load shedding, carefully designed stale-data serving for noncritical information, and dedicated capacity protection for booking operations.

The objective is to prevent one dependency failure from creating a second, more damaging failure.

### 5. Preserve booking correctness and handle duplicate notification attempts

The confirmed booking must remain valid regardless of email-delivery problems.

The notification workflow should be recoverable and should use available mechanisms to avoid harmful duplicates.

If the email provider cannot guarantee exactly-once delivery under ambiguous failures, an occasional duplicate email may be an acceptable trade-off.

That is very different from allowing duplicate payments or reservations.

The business guarantees should reflect the relative consequences.

### 6. Begin with evidence and the highest-leverage constraints

I'd first instrument the critical workloads and validate booking correctness.

Then optimize expensive SQL, introduce targeted caching where repeated reads justify it, establish resource budgets and backpressure, and scale stateless instances or workers as required.

More elaborate architecture should follow demonstrated limitations.

Kubernetes may be useful for deployment operations, but it doesn't inherently increase database throughput.

Sharding and microservice extraction should be postponed until the organization and workload genuinely require them.

The order is driven by measured bottlenecks and business risks, not technology fashion.

---

# 22. Mental Model — The Backend Engineer's Decision Framework

Across the backend, database, and distributed-systems courses, we've moved from the internals of one backend request to the behavior of an entire production system under concurrency, failures, and growth.

The most useful consolidated model is this:

```text id="3okc7g"
                    BUSINESS OPERATION
                            |
                            v
                   DEFINE CORRECTNESS
                            |
                            v
                    MODEL THE DATA
                            |
                            v
                  ENFORCE INVARIANTS
                            |
                            v
                  MEASURE ACTUAL WORK
                            |
                            v
                  IDENTIFY BOTTLENECKS
                            |
                            v
                 OPTIMIZE / ADD CAPACITY
                            |
                            v
                 DESIGN FAILURE RECOVERY
                            |
                            v
                 TEST UNDER REALISTIC LOAD
                            |
                            v
                   EVOLVE THE SYSTEM
```

At every stage, ask three questions.

**What must remain true?** These are the business invariants and correctness guarantees that no optimization may casually violate.

**What limits useful progress?** These are the actual resource, concurrency, latency, and coordination bottlenecks—not merely whichever component has the highest CPU percentage.

**What happens when something fails halfway through?** These are the durability, idempotency, recovery, and reconciliation requirements that distinguish reliable production software from code that only works on the happy path.

The final engineering judgment I'd carry from this course is simple:

**Build the simplest architecture that preserves the required guarantees at the measured workload, and evolve it when evidence justifies additional complexity.**

That's not an argument for avoiding sophisticated systems. It's an argument for knowing exactly why you're introducing one.

And that is what makes a strong senior backend engineer: the ability to reason from constraints and consequences rather than reciting architectural patterns.

---


---

## Next Lecture — SE490-L04: Senior Engineer Workshop: Architecture Review

Continue in **SE490 — Architecture and Systems Design Studio**.

## Further Reading

- **PostgreSQL — Using EXPLAIN:** https://www.postgresql.org/docs/current/using-explain.html
- **PostgreSQL — pg_stat_statements:** https://www.postgresql.org/docs/current/pgstatstatements.html
- **PostgreSQL — Transaction Isolation:** https://www.postgresql.org/docs/current/transaction-iso.html
- **node-postgres — Pool Sizing:** https://node-postgres.com/guides/pool-sizing
- **AWS RDS Proxy — Connection Pooling:** https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.howitworks.html
- **Redis — Cache-Aside:** https://redis.io/docs/latest/develop/use-cases/cache-aside/
- **AWS — Transactional Outbox:** https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- **AWS Builders' Library — Using Load Shedding to Avoid Overload:** https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE490-L03  BUILD FOR 100× TRAFFIC — INTERVIEW GLANCE CARD

DEFINE WORKLOAD FIRST
  120 → 12,000 RPS example: ~80% search, ~1% booking — not uniform cost
  Search = read-scaling; booking = correctness + workflow capacity
  Cache hit math: 9600×3 uncached vs 10% miss → leverage, not a promise
  External supplier rate limit can be hard ceiling (e.g. 80 vs 120 booking/s)

SUCCESS ≠ RPS
  SLOs for latency + inventory invariants + no duplicate payment + recovery
  202 Accepted ≠ completed booking; track business outcomes

PHASE ORDER (6 weeks)
  1 Telemetry baseline  2 Booking correctness/idempotency
  3 Cheap SQL/ORM       4 Targeted cache + stampede protection
  5 Connection budgets / admission  6 Scale APIs/workers
  7 Load+failure tests  8 Replicas/infra only if measured need
  Progressive traffic stages; stop when thresholds break

EFFICIENCY BEFORE TOPOLOGY
  pg_stat_statements by total_exec_time; EXPLAIN ANALYZE carefully
  Indexes for access patterns; keyset pagination; fix N+1/ORM; then cache
  Making one request cheaper > more machines doing inefficient work

CACHE LAYERS
  CDN assets; Redis for summaries/search; advisory search ≠ booking claim
  Stampede mitigations; Redis fail → bounded fallback (protect booking path)

BOOKING PATH
  Conditional capacity UPDATE; multi-night txn; short locks (no external wait)
  UNIQUE (tenant, idempotency_key); durable workflow; reconcile UNKNOWN

HORIZONTAL SCALE TRAPS
  Instances × pool size → connection storm; PgBouncer/RDS Proxy budget
  Shared durable state for sessions/idempotency/holds; local cache ≠ authority
  Hot inventory row: more Nodes ≠ more update capacity (serialization)

WORKERS / REPLICAS / SHARD
  Outbox → queues; separate worker pools; idempotent consumers; watch depth
  Replica lag: consistency-sensitive reads → primary
  Partition maybe; shard last (hot keys, cross-shard pain)
  Modular monolith OK; extract only with evidence

FAILURE / COST
  Bounded recovery (jitter/backoff); avoid recovery storms
  Cost per successful booking; log/trace/API/retry costs accumulate
  Decision framework: correctness → model data → invariants → measure →
  bottleneck → capacity → failure recovery → test → evolve

SENIOR LINE: simplest architecture that preserves guarantees at measured load.
```
