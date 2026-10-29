---
id: SE325-L06
course: SE325
title: "API Protection and Multi-Tenant Fairness"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE325-L05
next: null
---

# SE325 — Backends in the Wild: Production Field Guide
## Lecture 06: API Protection and Multi-Tenant Fairness

*One enterprise customer requests a series of enormous data exports. Your rate limiter reports that every client is within its allowance. Redis is healthy, CPU utilization is moderate, and no obvious infrastructure component has crashed. Yet ordinary customers can barely complete a booking. How can a perfectly legal customer bring down an application without making an extraordinary number of requests?*

---

# Part I — Intuition

## 1. The Customer Who Used Everything They Were Allowed to Use

It's Tuesday afternoon at Mercury, our hotel-booking platform.

The application serves hundreds of accommodation suppliers and thousands of individual customers.

Most API requests are straightforward. A customer retrieves a booking, checks availability, or updates a small piece of information.

Some requests are more demanding.

Suppliers can export property catalogues, retrieve historical reservation data, and run detailed reports.

One enterprise supplier, AlpineRooms, decides to export its entire reservation history.

Its integration launches several large exports.

Each export reads hundreds of thousands of records, performs joins and sorting, and generates a downloadable CSV file.

The supplier's requests are legitimate.

Its credentials are valid.

The requests pass authorization.

The per-IP rate limiter allows them because none of the individual IP addresses exceeds its configured threshold.

Meanwhile, the database connection pool begins filling up.

Several export operations keep database connections occupied while processing large result sets.

A scheduled cleanup job also begins.

Suddenly, ordinary customer requests have to wait for database connections.

Some eventually time out.

The support dashboard shows rising booking failures.

Your application is not under a traditional denial-of-service attack.

Nobody has discovered a security vulnerability.

One customer is simply consuming an unreasonable proportion of shared capacity.

This is the **noisy-neighbor problem**.

**In a multi-tenant system, a workload can be individually authorized and still be collectively harmful.**

## 2. Why Counting Requests Isn't Enough

Suppose Mercury allows each customer one hundred API requests per minute.

Imagine two customers.

Customer A makes eighty requests to retrieve individual reservations. Each request performs one small indexed database lookup.

Customer B makes five requests to export hundreds of thousands of reservations. Each request performs a large query and occupies database resources for several minutes.

Customer A makes sixteen times as many requests.

Yet Customer B may consume vastly more database capacity.

The request counter gives the wrong impression of who is using the most resources.

A request has several dimensions of cost.

How much CPU does it consume?

How many database queries does it execute?

How long does it occupy a database connection?

How much memory does it require?

How many rows does it examine?

How much data does it transfer?

How much downstream work does it generate?

These quantities can differ by several orders of magnitude between endpoints.

A request-rate limiter primarily controls how frequently requests arrive.

It doesn't automatically control the amount of work each request performs.

## 3. Rate Is Different from Concurrency

Consider two simple operations.

The first takes ten milliseconds.

The second takes ten seconds.

Suppose each arrives at the same rate: ten requests per second.

The quick operation may require only a small amount of concurrent execution capacity.

The slow operation may accumulate approximately one hundred simultaneous requests under steady-state conditions.

This follows a useful relationship from queueing theory: average concurrency equals arrival rate multiplied by average time in the system.

You encountered the underlying mathematics in CS430-L03.

Here we care about the operational consequence.

**A modest request rate can still create enormous concurrency when each request holds resources for a long time.**

This is why a rate limit and a concurrency limit answer different questions.

A rate limit asks how often a customer may begin work.

A concurrency limit asks how much work may remain active simultaneously.

### Visual anchor 1 — The same rate, different occupancy

```text id="s32506a"
TEN REQUESTS PER SECOND

Fast operation:
  Each takes 0.01 seconds
  Approximate average concurrency: 0.1

Slow operation:
  Each takes 10 seconds
  Approximate average concurrency: 100

Same arrival rate.
Completely different resource demand.
```

Now imagine the slow requests are database exports.

Even a small number of them can occupy a connection pool for a significant period.

## 4. Shared Capacity Is Like a Small Restaurant Kitchen

Picture a restaurant with six cooking stations.

Five stations are occupied preparing an enormous catering order for one customer.

The sixth station is occupied preparing ingredients for tomorrow.

A regular customer enters and orders a simple meal.

The restaurant has enough ingredients.

The cooks are healthy.

The electricity works.

But every station is occupied.

The customer waits.

This is similar to a backend whose database connection pool is exhausted.

The request may need only a simple lookup.

But it cannot begin because the required resource is unavailable.

Now imagine that the restaurant reserves three stations for ordinary customers, two for catering, and one for preparation.

The catering work progresses more slowly.

But customers can still receive meals.

This is the intuition behind **resource isolation**, sometimes called a bulkhead.

## 5. A Bulkhead Protects One Workload from Another

Ships have compartments separated by bulkheads.

If water enters one compartment, the entire vessel should not immediately flood.

Software systems use a similar idea.

Instead of placing every workload into one undifferentiated pool, we can separate resource budgets.

Interactive bookings may receive reserved capacity.

Bulk exports may use a smaller worker pool.

Scheduled maintenance may have its own concurrency limit.

### Visual anchor 2 — Shared versus protected capacity

```text id="s32506b"
NAIVE SHARED POOL — 6 CONNECTIONS

Exports:      5 occupied
Maintenance:  1 occupied
Bookings:     0 available


PROTECTED CAPACITY — 6 CONNECTIONS

Bookings:     3 reserved
Exports:      2 maximum
Maintenance:  1 maximum
```

The exact numbers are illustrative.

Real pool design requires measurements.

The point is that one workload should not automatically consume every resource another workload needs.

But there's an important qualification.

Separating connection pools doesn't magically separate database CPU, disk I/O, locks, or memory.

A large export can still overload the shared database even if its connection count is limited.

Bulkheads reduce blast radius. They aren't unlimited capacity.

## 6. Fairness Doesn't Necessarily Mean Equality

Suppose Mercury has two tenants.

The first is a small hotel with twenty rooms.

The second is a large international supplier with ten thousand properties.

Should both receive exactly the same API allowance?

Not necessarily.

Perhaps enterprise contracts provide higher quotas.

Perhaps some operations have different business importance.

Perhaps the smaller customer should receive a minimum service guarantee even while the larger tenant generates more revenue.

Fairness is a policy.

It can mean equal treatment.

It can mean proportional allocation.

It can mean guaranteed minimum service.

Or it can mean a combination of paid entitlements and protection against monopolization.

The important question is what the system promises and whether it can enforce that promise without harming everyone else.

## 7. What Happens When Capacity Runs Out?

Imagine that all available export workers are busy.

A new export request arrives.

The application has several options.

It can reject the request because the tenant has exceeded its quota.

It can accept the request as a background job and queue it.

It can ask the client to retry later.

Or, during a broader infrastructure incident, it may temporarily refuse nonessential operations.

These choices are different.

For example, returning `202 Accepted` is appropriate when the system has genuinely accepted an asynchronous job and can track it durably.

Returning `429 Too Many Requests` is appropriate when the client has exceeded a relevant request-rate or usage policy.

Returning `503 Service Unavailable` can be appropriate when the service temporarily cannot handle requests because of overload or maintenance.

A server should not claim to have accepted a job merely because it placed something in an unbounded in-memory list that may disappear on restart.

**Admission is a promise. The system must understand the cost of that promise before making it.**

## 8. The Most Important API Isn't Always the Most Expensive

Now imagine production is under heavy load.

Which operations should Mercury protect?

Perhaps creating a confirmed booking is more important than generating an optional historical report.

Maybe checking whether an existing reservation succeeded is essential.

A supplier's full-catalogue export may be valuable but can wait.

A scheduled cleanup task may be temporarily delayed.

This suggests prioritizing operations according to business importance and their correctness requirements.

The goal isn't to make every request equally fast.

It's to preserve the most valuable and necessary behavior when capacity becomes scarce.

### Visual anchor 3 — Protection layers

```text id="s32506c"
Incoming request
       |
       v
Authenticate and identify tenant
       |
       v
Apply request-rate policy
       |
       v
Classify operation and estimate cost
       |
       v
Check tenant quota
       |
       v
Check endpoint concurrency
       |
       v
Check shared resource capacity
       |
       +---- Reject or queue safely
       |
       v
Execute bounded work
       |
       v
Release resources and record usage
```

This is a conceptual pipeline, not a requirement to implement seven network services.

Some checks may happen in an API gateway.

Others belong in the application or job scheduler.

The important point is that several distinct limits protect different resources and promises.

## 9. A Tiny Comprehension Check

Suppose a tenant makes five requests per minute, and each request occupies a database connection for three minutes.

Would a limit of one hundred requests per minute protect the database?

Not necessarily. The tenant may still accumulate fifteen concurrent operations.

Now suppose the application separates export workers from booking API instances, but both use the same unprotected database.

Is the system completely isolated?

No. The database remains a shared dependency.

Finally, if the platform cannot generate an export immediately but can durably queue it, must it return an error?

No. It can accept a tracked asynchronous job, provided the queue and job lifecycle are genuinely reliable.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 10. Protecting an API Means Governing Resource Consumption

Traditional API protection discussions often focus on security.

Authentication determines who the caller is.

Authorization determines what they're permitted to do.

Input validation establishes whether the request is structurally and semantically acceptable.

SE310 covers those boundaries.

But a caller can pass every security check and still create excessive work.

An authenticated customer may issue thousands of expensive search requests.

A supplier may request a report that performs an enormous database aggregation.

A legitimate administrative operation may lock heavily used rows for too long.

Resource governance begins after we establish the caller's identity and intended operation.

The system must decide how much capacity that operation may consume.

### 10.1 Four distinct questions

We should separate four decisions.

**Identity:** Who is requesting work?

**Permission:** Are they allowed to perform the operation?

**Entitlement:** How much of that operation are they allowed to request?

**Admission:** Can the system safely begin the work now?

A tenant can be entitled to ten exports per day but still be unable to execute all ten concurrently.

A user can have permission to query reservation history but still be subject to limits on result size.

A service may temporarily reject work even from entitled users when its dependencies are overloaded.

## 11. Why Per-IP Rate Limiting Is Incomplete

Per-IP rate limiting is useful in some circumstances, especially near public network boundaries.

It can reduce certain forms of abuse before expensive authentication or application work occurs.

But IP addresses are not reliable representations of business tenants.

### 11.1 One tenant can use many IPs

A customer may distribute requests across servers, cloud regions, offices, or networks.

A limit of one hundred requests per IP might allow the same organization to send thousands of requests through different addresses.

### 11.2 Many legitimate users can share one IP

Employees behind a corporate network may share a public address through NAT.

Mobile network users may also appear behind shared addresses.

Aggressive per-IP limits can unfairly throttle unrelated legitimate users.

### 11.3 Proxy identity can be forged if trusted incorrectly

Applications behind reverse proxies often use forwarded-address headers.

Those headers must be interpreted according to the trusted proxy chain.

An application that blindly trusts arbitrary client-supplied forwarding headers may allow an attacker to invent apparent source addresses.

### 11.4 Use authoritative tenant identity

After authentication, quotas can be associated with the resolved tenant or customer account.

The tenant identity should come from trusted server-side authorization context, not from a freely editable request header.

Per-IP controls remain useful as one layer.

They are not a replacement for tenant-level governance.

## 12. Request-Rate Limiting

A rate limiter restricts how frequently an operation may occur over time.

Several mechanisms are common.

### 12.1 Fixed window

Suppose a tenant is allowed one hundred requests per minute.

The application counts requests within each calendar minute.

This is simple.

But consider the boundary between two windows.

A client might submit one hundred requests just before the minute changes and another hundred immediately afterward.

The short burst is significantly larger than the nominal rate suggests.

### 12.2 Sliding window

A sliding-window limiter considers activity over a moving time interval.

It can provide smoother enforcement than a simple fixed window.

But accurate implementations may require more bookkeeping.

### 12.3 Token bucket

Imagine each tenant has a bucket of tokens.

Tokens accumulate at a configured rate, up to a maximum capacity.

Each admitted request consumes tokens.

If insufficient tokens remain, the operation is delayed or rejected.

The bucket capacity permits controlled bursts.

The refill rate controls sustained traffic.

### 12.4 Leaky bucket and paced admission

Another family of limiters controls the rate at which work leaves a queue or enters execution.

This can smooth bursts.

But adding a queue creates waiting time and memory obligations.

A rate limiter shouldn't silently accumulate an unbounded backlog.

### 12.5 Distributed counters

If Mercury has ten API instances, a counter maintained only in each instance allows the effective global allowance to scale with replica count.

Shared limits may need a coordinated store, distributed rate-limit service, or carefully designed quota allocation.

The correct architecture depends on how strict the limit must be.

For a rough abuse-control mechanism, small inaccuracies may be acceptable.

For a contractual paid quota, more precise accounting may matter.

## 13. Concurrency Limiting

Request rate controls arrivals.

Concurrency controls how many operations remain active.

Suppose an export occupies a database connection for twenty seconds.

Allowing a tenant to start twenty exports simultaneously may create significant resource pressure even if the tenant makes only twenty requests in one minute.

A concurrency limiter can allow two active exports and reject or queue additional ones.

### 13.1 Semaphore model

A semaphore represents a finite number of permits.

Before beginning expensive work, the operation acquires a permit.

When the work finishes or fails, it releases the permit.

The permit should be released through reliable cleanup logic, including exceptions and cancellations.

### 13.2 Permits must correspond to real work

A common mistake is releasing the concurrency permit when the HTTP request returns `202 Accepted`.

If the expensive export continues in the background, the permit must belong to the background execution, not merely the initial API request.

The admission of a job and the execution of a job are different resource lifetimes.

### 13.3 Queued is not running

A durable export queue can contain one hundred jobs while only two export workers are active.

That may be perfectly healthy if the waiting time is acceptable and the queue is bounded.

But a hundred queued jobs shouldn't be confused with a hundred active database operations.

### 13.4 Tenant and global limits

A tenant might be allowed two active exports.

The system might allow twenty active exports across all tenants.

Both limits matter.

The tenant cap prevents monopolization.

The global cap protects total capacity.

## 14. Expensive-Operation Budgets

Even concurrency limits can be too crude.

Two exports may have radically different costs.

One retrieves ten thousand rows through a suitable index.

Another performs several aggregations across tens of millions of records.

Both count as one active export.

But their resource consumption may differ enormously.

### 14.1 Weighted costs

An API can assign estimated cost units to operations.

For example:

Retrieve one reservation: one unit.

Search a small property catalogue: three units.

Generate a large report: fifty units.

Run a historical export: one hundred units.

These are illustrative policy weights, not universal performance measurements.

The system can enforce a weighted admission budget instead of treating every request as equivalent.

### 14.2 Estimate before execution

For some endpoints, expected cost can be approximated using request parameters.

Date range.

Requested record count.

Number of properties.

Requested aggregation dimensions.

Sort complexity.

Requested export format.

But estimates can be wrong.

An API accepting arbitrary query shapes may need stronger restrictions because the actual execution cost depends on indexes, data distribution, and database planning.

### 14.3 Bound the shape of requests

Instead of allowing an unlimited report query, require a maximum date range or result size.

For extremely expensive operations, require asynchronous execution.

The goal is to prevent unbounded user-controlled computation.

### 14.4 Measure actual cost

Estimates should be refined using production evidence.

Track actual query time, rows examined, database waits, CPU consumption, and output size where available.

A billing-style cost model that never reflects actual resource consumption can become both unfair and ineffective.

## 15. Database Connections Are Scarce Resources

Return to the original incident.

Mercury's API uses PostgreSQL.

Each application instance maintains a connection pool.

Suppose the application runs eight replicas, each configured with twenty database connections.

The total possible application-side connection demand may reach one hundred sixty connections, even before considering background workers and administrative tools.

Increasing the number of application replicas can therefore increase pressure on PostgreSQL.

### 15.1 A connection pool isn't a free capacity generator

The pool limits how many requests can hold database connections simultaneously.

When all connections are occupied, other requests wait.

Increasing the pool may reduce waiting if the database has unused execution capacity.

But once the database is saturated, additional connections can increase contention and reduce useful throughput.

### 15.2 Connection ownership matters

An export should not hold a database connection while performing unrelated slow network operations if the application can safely release it.

For example, streaming a large dataset directly from a cursor may keep a database connection occupied for a long time.

An alternative may fetch bounded chunks and release the connection between chunks.

But that introduces snapshot-consistency questions.

The correct design must balance resource lifetime and data correctness.

### 15.3 Separate pools are only partial isolation

Suppose Mercury creates one pool for bookings and another for exports.

This can prevent the export path from occupying every connection allocated to booking requests.

But PostgreSQL still has finite CPU, memory, storage I/O, and lock capacity.

A query running through the export pool can consume the same database resources used by the booking pool.

Logical connection isolation doesn't automatically create physical database isolation.

## 16. Protecting Critical Operations

An application needs a deliberate view of business priority.

For Mercury, relevant categories might include:

**Critical interactive work:** Creating bookings, confirming important payment outcomes, retrieving authoritative booking status.

**Ordinary interactive work:** Browsing hotels, viewing reservation history, modifying account preferences.

**Background business work:** Supplier synchronization, report generation, scheduled reconciliation.

**Deferrable maintenance:** Nonurgent cleanup, disposable cache refreshes, optional analytical exports.

These categories aren't immutable.

A financial reconciliation may become urgent near a reporting deadline.

A supplier synchronization job may be essential for preventing stale inventory.

The business determines importance.

### 16.1 Protect the path, not merely the endpoint

A booking operation might depend on authentication, inventory, payment, and database services.

Protecting only the booking API's own worker pool won't help if a noisy workload saturates a shared dependency.

The protection strategy must understand the full resource path.

### 16.2 Reserve capacity carefully

Some capacity may be reserved for essential operations.

But rigid reservations can waste resources if one lane is idle while another has an enormous backlog.

A mature system may allow controlled borrowing while preserving minimum guarantees.

That introduces additional complexity.

Begin with understandable limits, measure utilization, and refine them when justified.

### 16.3 Priority inversion

Imagine a low-priority export holds a database lock needed by a high-priority booking operation.

The booking's API priority cannot make the lock disappear.

This is a priority-inversion problem at a shared resource.

Preventing it may require reducing transaction duration, redesigning queries, or isolating conflicting workloads.

Admission priority alone isn't enough.

## 17. Fairness Between Tenants

Tenant fairness can be implemented in several ways.

### 17.1 Equal quotas

Every tenant receives the same request allowance.

This is simple, but may not reflect the business model or usage patterns.

### 17.2 Tiered quotas

Enterprise customers may receive larger allowances.

Small customers receive smaller limits with guaranteed minimum service.

The policy should be explicit and enforceable.

### 17.3 Proportional sharing

Capacity can be distributed according to configured weights.

For example, a tenant with a higher entitlement may receive a larger share of export throughput.

### 17.4 Fair scheduling

A background-job scheduler can process work across tenants in a way that prevents one large backlog from monopolizing the worker fleet.

One simple strategy is round-robin selection among tenants with waiting jobs.

More advanced algorithms, such as deficit round robin or weighted fair queuing, can account for unequal job costs and entitlement weights.

### 17.5 Avoid starvation

A fairness policy should consider whether low-priority jobs can wait forever.

Some systems use aging or minimum service guarantees to ensure eventual progress.

The appropriate guarantee depends on the product.

## 18. Tenant Quotas Versus Global Capacity

A tenant quota is a policy about permitted usage.

Global capacity is a statement about current system resources.

These may disagree.

Suppose AlpineRooms is entitled to ten active export requests.

But Mercury's export workers can safely run only six exports across all tenants.

The tenant's entitlement does not create physical capacity.

Similarly, a tenant may be below its quota while the database is temporarily degraded.

The service may still need to postpone work.

### 18.1 Two independent rejection reasons

**Policy denial:** The tenant has exceeded its allowed usage.

**Capacity denial:** The system cannot safely accept additional work now.

These should not be collapsed into one vague "something went wrong" response.

### 18.2 Make waiting visible

For asynchronous exports, a durable queue can accept a job without beginning execution immediately.

The response should expose a job ID and a way to inspect status.

It may provide an approximate waiting-time estimate when the system can calculate one responsibly.

### 18.3 Queues need admission too

If every customer can enqueue unlimited jobs, the application can accumulate an enormous backlog.

Even a queue with only two workers can become operationally unmanageable.

Limit queued jobs, storage obligations, retention, and per-tenant pending work.

## 19. `429` Versus `503`

HTTP status codes communicate different failure categories.

### 19.1 `429 Too Many Requests`

This indicates that the client has exceeded a rate-limiting policy.

It can be appropriate for per-user, per-tenant, per-key, or per-resource request limits.

A `Retry-After` header may indicate when the client should try again.

The response should explain the limit sufficiently for the client to behave appropriately, without exposing unnecessary internal details.

### 19.2 `503 Service Unavailable`

This indicates that the server is temporarily unable to handle the request, commonly because of overload or maintenance.

It can also include `Retry-After`.

A tenant can be entirely within its normal quota and still receive a 503 when shared infrastructure is unavailable.

### 19.3 `202 Accepted`

This can be appropriate when the application has durably accepted an asynchronous operation for later processing.

It does not mean the operation has already completed successfully.

The client should receive a suitable way to track progress and outcome.

### 19.4 `413 Content Too Large`

If the client attempts an upload or request body exceeding the permitted size, 413 may be the appropriate response.

This is distinct from rate limiting or temporary capacity overload.

### 19.5 Don't pretend the distinction is always clean

An organization's API may define usage policies involving concurrent operations, not only request counts.

Those policies can lead to application-specific response choices.

But the documented contract should distinguish exhausted customer entitlements from temporary system overload.

The code shouldn't randomly return 429 or 503 based on which exception happened to be caught.

## 20. Load Shedding: Refusing Work to Preserve the Service

Load shedding means deliberately declining some work when accepting it would threaten the system's ability to provide useful service.

This can feel counterintuitive.

Engineers naturally want every request to succeed.

But consider a system that can safely process one thousand requests per second.

Two thousand requests per second arrive.

If the application accepts all two thousand and queues them indefinitely, latency grows.

Clients time out.

They retry.

The system receives even more requests.

Eventually, nearly everything fails.

### 20.1 Reject early

An overloaded application should ideally reject unsuitable work before it acquires expensive downstream resources.

Rejecting after a request has already consumed substantial database capacity defeats much of the purpose.

### 20.2 Protect useful work

Low-priority exports may be deferred before critical booking confirmation.

Optional enrichment may be disabled before core application behavior.

### 20.3 Shed before collapse

Good load shedding can preserve partial availability.

A system that rejects some nonessential work early may serve more critical operations successfully than one that accepts everything.

### 20.4 Beware retry amplification

Clients may retry rejected requests.

If every client retries immediately, load shedding can produce another surge.

Use appropriate response semantics, retry guidance, and client-side backoff.

## 21. Graceful Degradation

Load shedding and graceful degradation are related but different.

Load shedding refuses work.

Graceful degradation provides a reduced service when full functionality isn't available.

Suppose Mercury's recommendation engine becomes overloaded.

The booking page could still display the core hotel information without personalized recommendations.

Suppose an analytics dashboard is unavailable.

The customer might still retrieve their reservations.

The architecture should classify optional and essential dependencies.

### 21.1 Fail open or fail closed?

For a recommendation feature, omitting the recommendation may be acceptable.

For payment authorization, inventory correctness, or tenant isolation, silently bypassing validation could be dangerous.

Failing open isn't universally graceful.

It depends on the business invariant.

### 21.2 Degradation needs testing

A fallback that has never been exercised may itself be broken.

Test the application when optional dependencies are unavailable.

Make sure degraded behavior doesn't accidentally create more work than the original operation.

## 22. Circuit Breakers, Bulkheads, and Limits Are Different

These concepts often appear together, but solve different problems.

**Rate limiter:** Restricts how frequently work is admitted.

**Concurrency limiter:** Restricts how many operations are active.

**Bulkhead:** Isolates capacity among workloads or dependencies.

**Circuit breaker:** Stops or limits calls to a dependency exhibiting problematic failure behavior.

**Load shedding:** Rejects work under overload to preserve system health.

**Queue:** Holds accepted work for later execution, subject to limits.

A circuit breaker doesn't automatically provide fair tenant quotas.

A rate limiter doesn't guarantee downstream capacity.

A bulkhead doesn't automatically prevent expensive queries from consuming CPU.

And a queue doesn't create processing capacity.

The mechanisms are complementary.

## 23. Emergency Controls and Kill Switches

Imagine Mercury experiences a sudden database overload.

Engineering identifies expensive historical exports as the major contributor.

What can be done immediately?

Possible interventions include temporarily disabling new export admission, reducing export-worker concurrency, pausing nonessential backfills, and lowering query budgets.

The choice depends on the system's actual failure mode.

### 23.1 A kill switch should be narrow

An emergency flag that disables only optional exports is preferable to shutting down the entire API when the export path is the problem.

### 23.2 Disabling new work doesn't stop active work

If five long-running exports already occupy database connections, preventing new exports may not free capacity quickly enough.

The team may need a controlled cancellation or termination procedure.

### 23.3 Cancel safely

Terminating a database query can free resources, but the application must understand any transactional and business consequences.

An already committed export or import side effect isn't automatically undone.

### 23.4 Operational safeguards

Kill switches should have clear ownership, scope, observability, and restoration procedures.

An emergency mitigation shouldn't silently remain enabled for months without review.

## 24. Cost Attribution and Product Economics

Fairness also has an economic dimension.

A tenant performing enormous exports consumes infrastructure resources.

Even if the platform remains technically available, the cost may be substantial.

The business may need to understand usage by tenant.

### 24.1 Useful measurements

Requests by endpoint.

Estimated and actual cost units.

Database execution time.

Storage consumed by exports.

Object-storage egress.

Background processing duration.

Queue occupancy.

### 24.2 Chargeback and quotas

Some SaaS businesses include usage quotas in subscription plans.

Others bill for additional export capacity.

Still others use resource accounting only to identify abusive or inefficient workloads.

The billing model is a product decision.

The measurement and enforcement mechanisms are engineering responsibilities.

### 24.3 Avoid false precision

A query-cost estimate isn't automatically an accurate monetary cost.

Database resource usage depends on load, caching, and shared infrastructure.

Use a defensible model.

Don't present arbitrary internal weights as objective physical measurements.

## 25. Observability for Resource Governance

A healthy API-protection dashboard needs more than total request count.

Start with traffic.

Requests per tenant.

Requests per endpoint.

Accepted and rejected operations.

But add resource measurements.

### 25.1 Pool occupancy

How many database connections are active?

How many requests are waiting for a connection?

How long do they wait?

### 25.2 Concurrency

How many exports are running?

How many are queued?

How many belong to each tenant?

### 25.3 Cost and duration

Which endpoints consume the greatest database time?

Which operations scan the most records?

Which background jobs run unusually long?

### 25.4 Tail latency

Average latency can conceal customer pain.

Track appropriate latency distributions for critical operations.

A small proportion of requests waiting tens of seconds may be a serious problem even if the mean remains moderate.

### 25.5 Goodput

How many useful, successful business operations complete?

For Mercury, that might include confirmed bookings and completed authorized exports.

Raw HTTP throughput isn't a sufficient business-health metric.

### 25.6 Rejection reasons

Distinguish tenant quota, global overload, authentication failure, authorization denial, invalid request, and downstream failure.

These aren't interchangeable.

## 26. Diagnosing the Noisy-Neighbor Incident

Return to the opening problem.

AlpineRooms starts several exports.

Booking latency rises.

The rate limiter reports healthy request rates.

Redis looks normal.

The database connection pool is exhausted.

How do we investigate?

### 26.1 Establish the timeline

When did latency begin rising?

Which deployment or workload changes happened around that time?

Did the exports start before or after the degradation?

### 26.2 Examine resource occupancy

Are requests waiting to acquire database connections?

How many connections are held by exports?

How long do those operations remain active?

Are queries themselves slow, or is most time spent waiting for a connection?

### 26.3 Segment by tenant and operation

Which tenants account for active database work?

Which endpoints consume the most resources?

Are background jobs competing with interactive requests?

### 26.4 Check query and transaction behavior

Are exports holding transactions open unnecessarily?

Are they performing expensive sorts or large scans?

Are they waiting on locks?

Has a query plan changed?

### 26.5 Verify the rate-limiter model

Is the limiter keyed by IP address rather than tenant?

Does it count requests without accounting for long-running work?

Is it applied per application instance instead of globally?

### 26.6 Avoid premature scaling

Adding API instances may multiply database connection demand.

Increasing connection-pool sizes may worsen contention.

Adding export workers may increase the very workload causing the incident.

Scale only when evidence identifies available capacity or a genuine bottleneck that scaling can address.

## 27. Immediate Containment

Suppose the investigation confirms that five expensive exports are holding most of the shared database pool.

The first objective is restoring critical booking operations.

A reasonable containment plan might include pausing new exports, reducing export concurrency, and selectively cancelling safe-to-restart work.

But cancellation must be deliberate.

An import job that has already modified data may require a resumable checkpoint.

An export that writes to a temporary object may be safe to cancel and restart.

A financial reconciliation might require more caution.

### 27.1 Coordinate with product and support

Enterprise customers may notice delayed exports.

The team should communicate the limitation and preserve job state where possible.

### 27.2 Verify recovery

Database connection wait time should decline.

Critical booking latency should recover.

Error rates should improve.

The system should continue making progress on important background obligations.

### 27.3 Don't declare victory too early

A temporary kill switch may restore service.

But the underlying design remains vulnerable until workload isolation and admission policy are corrected.

## 28. The Permanent Protection Design

Let's construct a practical layered architecture.

First, public-edge controls protect against excessive anonymous traffic and malformed requests.

Second, authentication establishes the trusted user and tenant identity.

Third, a request-rate policy limits ordinary API traffic.

Fourth, endpoints are classified by expected resource cost.

Fifth, tenant-level quotas limit active and pending expensive work.

Sixth, global worker and connection budgets protect shared infrastructure.

Seventh, critical operations receive suitable capacity protection.

Eighth, queues allow deferrable operations to wait without occupying scarce execution resources.

Ninth, monitoring and emergency controls provide operational feedback.

### 28.1 Don't build everything at once

A small company may need only a few straightforward controls.

For example, a rate limiter, a maximum of two exports per tenant, a global export-worker limit, and a separate database connection budget may solve most of the immediate risk.

More sophisticated weighted scheduling should be justified by actual workload diversity.

### 28.2 The limits belong near the cost

A global API gateway may know the tenant and endpoint.

But it may not know the database execution cost of a particular query.

Some governance belongs inside the application or background scheduler.

The most useful limit is often enforced immediately before acquiring the resource it protects.

### 28.3 Protection should follow real bottlenecks

If the database CPU is saturated, merely splitting connection pools may not help.

If memory is exhausted by exports, cap memory-intensive processing.

If object-storage egress dominates cost, apply suitable export and bandwidth policies.

Resource governance should be evidence-driven.

## 29. The Senior Interview Answer

Imagine an interviewer asks:

"Your multi-tenant SaaS has an API rate limiter, but one customer can still make the product unusable for everyone. What would you do?"

A weak answer is:

"Lower the rate limit."

A somewhat better answer is:

"Use rate limiting by tenant instead of IP."

A strong answer begins by identifying what resource is being exhausted.

Is the problem request rate, concurrency, database connections, expensive queries, memory, external API quota, or network throughput?

Then it separates policy from capacity.

Which tenant or endpoint is consuming the resource?

What is the contractual allowance?

What work is essential?

Which operations can be queued or deferred?

What limit can be enforced before expensive work begins?

And how will the team verify that the protection improves useful throughput without creating unfair starvation?

This demonstrates a more mature understanding of API protection.

The objective isn't to prevent customers from using the product.

It's to ensure that one workload cannot unintentionally prevent everyone else from using it.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Healthy Rate Limiter

A tenant sends five export requests per minute.

Each export occupies a database connection for three minutes.

The tenant's rate limit allows one hundred requests per minute.

Why can this still overload the system?

## Question 2 — Rate Versus Concurrency

Explain the difference between a token-bucket rate limiter and a semaphore-based concurrency limiter.

What does each protect?

## Question 3 — The IP Address

Why is per-IP rate limiting inadequate as the only fairness mechanism in a multi-tenant SaaS?

## Question 4 — The Database Pool

A service runs eight replicas, each configured with twenty PostgreSQL connections.

What is the potential combined connection demand?

Why might increasing application replicas worsen database contention?

## Question 5 — Bulkhead Limitations

Bookings and exports use separate connection pools.

Exports still cause PostgreSQL CPU saturation.

Has the system achieved complete resource isolation?

## Question 6 — Tenant Entitlement

A tenant is entitled to ten exports per day.

It has already requested only two.

The export system is temporarily overloaded.

Must the application execute the third export immediately?

## Question 7 — `429` Versus `503`

A tenant exceeds a documented request-rate limit.

Another tenant is below quota, but the service is temporarily overloaded.

Which status codes would ordinarily distinguish these situations?

## Question 8 — The Async Export

The API responds with `202 Accepted` for a large export.

What must the system actually do to justify that response?

Does the request need to hold a database connection while the job waits?

## Question 9 — Load Shedding

Why might rejecting optional exports improve overall system reliability?

What risks arise if clients immediately retry every rejection?

## Question 10 — The Query Budget

A reporting endpoint allows arbitrary date ranges and sort parameters.

Why might request count and concurrency limits still be insufficient?

## Question 11 — Fairness

One enterprise tenant pays for higher quotas.

A small customer expects reliable booking operations.

How would you balance entitlement, resource allocation, and minimum service guarantees?

## Question 12 — Senior Incident Response

A release is followed by high booking latency.

Redis is healthy.

Database connections are exhausted.

A large export and scheduled cleanup began shortly before the incident.

How would you investigate, contain, correct, and verify the problem?

---

# Solutions and Discussion

## Solution 1 — Occupancy

Even a modest arrival rate can create substantial concurrency when each operation holds resources for a long time.

The limiter controls arrivals, not resource occupancy.

## Solution 2 — Different Limits

A token bucket regulates request frequency and permitted bursts.

A semaphore limits simultaneous active operations.

Both may be necessary.

## Solution 3 — Incorrect Identity

One tenant can use many IP addresses, while many legitimate users can share one IP.

Use trusted tenant or account identity for business quotas, alongside appropriate edge-level controls.

## Solution 4 — Connection Multiplication

Eight replicas multiplied by twenty connections creates a potential demand of 160 connections, before considering other services and workers.

More replicas can increase contention when PostgreSQL is already saturated.

## Solution 5 — Shared Database Resources

No.

Separate pools help control connection occupancy, but the underlying database CPU, I/O, locks, and memory remain shared.

## Solution 6 — Policy Versus Capacity

No.

Entitlement doesn't guarantee immediate execution under overload.

A durable queue, appropriate delay, or temporary capacity response may be necessary.

## Solution 7 — HTTP Semantics

`429 Too Many Requests` ordinarily communicates a rate-limiting policy violation.

`503 Service Unavailable` communicates temporary server unavailability, including overload.

The documented API contract should make these distinctions clear.

## Solution 8 — Durable Acceptance

The system must genuinely accept and track the asynchronous operation.

The job can wait in a bounded durable queue without consuming its eventual execution resources.

## Solution 9 — Protect Useful Work

Early rejection prevents low-priority requests from consuming resources needed by critical operations.

Uncontrolled immediate retries can create a retry storm.

## Solution 10 — Variable Cost

One request can perform vastly more work than another.

Use query-shape restrictions, cost estimates, execution budgets, and appropriate asynchronous processing.

## Solution 11 — Weighted Fairness

Higher-tier tenants may receive larger quotas, but the architecture should preserve critical service for other customers.

Use explicit entitlements, tenant caps, resource protection, and fair scheduling.

## Solution 12 — Incident Method

Correlate latency with workload changes.

Inspect connection occupancy, wait time, query behavior, and tenant activity.

Contain expensive optional work.

Restore critical capacity.

Introduce bounded admission and isolation.

Verify recovery through booking latency, goodput, pool waits, and fair progress of background jobs.

---

# The Mental Model Worth Keeping

An API request isn't merely a line in a request counter.

It's a claim on finite computational resources.

**Rate limits govern arrival frequency.**

**Concurrency limits govern active work.**

**Cost budgets govern expensive operations.**

**Tenant quotas govern entitlement and fairness.**

**Bulkheads limit shared-resource interference.**

**Load shedding protects the system when capacity is insufficient.**

No single mechanism solves every overload problem.

The durable questions are:

**Who is requesting the work?**

**How expensive is the operation?**

**Which resource will it occupy, and for how long?**

**How much capacity may this tenant consume?**

**What must remain available when the system is overloaded?**

A reliable multi-tenant platform doesn't merely process requests.

It decides which work it can responsibly accept.

---

# Closing — Backends in the Wild: Production Field Guide

This completes SE325.

Across six lectures, we've examined backend responsibilities that often appear after the clean architecture diagrams have already been drawn.

We started with large files, where transferring bytes introduced memory, storage, authorization, and cleanup problems.

We moved to bulk processing, where one million records became a sequence of durable, bounded operations.

We investigated scheduled jobs, where clocks, failover, and repeated execution complicated apparently simple recurring tasks.

We studied production data repairs and lifecycle obligations, where changing one row could conflict with caches, indexes, backups, and reconciliation systems.

We examined third-party integrations, where external systems could silently change their behavior while continuing to return successful responses.

Finally, we investigated multi-tenant resource fairness, where authorized work could exhaust shared infrastructure and interfere with critical application behavior.

These subjects share one idea.

**Correct software must remain correct when operations become large, slow, repeated, interrupted, concurrent, or partially successful.**

A backend is not production-ready merely because its endpoints return the right JSON under ordinary conditions.

It must also have defensible behavior when the world stops cooperating.

The final practical studio combines the entire elective into one incident investigation.

*The spoken lecture ends here. The remaining material is a screen-based practical laboratory and integrated production incident studio.*

---

# Optional Practical Lab — The Noisy Tenant and the Exhausted Pool

## Lab Contract

This laboratory uses only Python's standard library.

It runs a deterministic simulation of a shared database connection pool.

No real database, cloud account, external API, or load-testing infrastructure is required.

The simulation compares two admission policies.

**Naive policy:** Every operation competes for one shared pool of six permits.

**Protected policy:** Bookings receive three permits, exports receive two, and maintenance receives one. A single tenant is also limited to two active exports.

A permit represents one simplified resource slot occupied for the duration of the simulated operation.

The simulation does not model real SQL execution, CPU contention, network timing, or database lock behavior.

It demonstrates admission and occupancy decisions, not performance predictions for a real deployment.

## Lab A — Build the Simulator

Create a directory named `se325-fairness-lab`.

Save the following code as `studio.py`.

The simulator uses a logical clock.

Operations are introduced at specified times, hold capacity for a defined duration, and then release it.

```python id="s32506lab"
from collections import Counter
from dataclasses import dataclass


CAPACITY = 6

LANE_LIMITS = {
    "booking": 3,
    "export": 2,
    "maintenance": 1,
}

DURATION = {
    "booking": 2,
    "export": 12,
    "maintenance": 8,
}

TENANT_EXPORT_LIMIT = 2


@dataclass(frozen=True)
class Work:
    at: int
    lane: str
    tenant: str
    ip: str
    label: str


ARRIVALS = (
    [
        Work(
            0,
            "export",
            "alpha",
            f"198.51.100.{i}",
            f"alpha-export-{i}",
        )
        for i in range(1, 6)
    ]

    + [
        Work(
            1,
            "maintenance",
            "system",
            "local",
            "cleanup",
        )
    ]

    + [
        Work(
            2,
            "booking",
            "beta",
            "203.0.113.7",
            f"beta-booking-{i}",
        )
        for i in range(1, 5)
    ]

    + [
        Work(
            3,
            "export",
            "alpha",
            "198.51.100.40",
            "alpha-export-6",
        ),
        Work(
            3,
            "export",
            "alpha",
            "198.51.100.41",
            "alpha-export-7",
        ),
    ]

    + [
        Work(
            4,
            "booking",
            "gamma",
            "203.0.113.18",
            "gamma-booking",
        )
    ]

    + [
        Work(
            13,
            "booking",
            "beta",
            "203.0.113.7",
            "beta-booking-later",
        )
    ]
)


def simulate(mode):

    # Each item:
    # (logical release time, work)

    active = []

    outcome = Counter()

    print(f"\n--- {mode.upper()} ---")

    for req in sorted(
        ARRIVALS,
        key=lambda r: r.at,
    ):

        # Release completed operations.
        active = [
            (end, old)
            for end, old in active
            if end > req.at
        ]

        lane_count = sum(
            old.lane == req.lane
            for _, old in active
        )

        tenant_export_count = sum(
            old.lane == "export"
            and old.tenant == req.tenant
            for _, old in active
        )

        if (
            mode == "protected"
            and req.lane == "export"
            and tenant_export_count
                >= TENANT_EXPORT_LIMIT
        ):

            result = "TENANT_QUOTA"

        elif (
            mode == "protected"
            and lane_count
                >= LANE_LIMITS[req.lane]
        ):

            result = "LANE_FULL"

        elif len(active) >= CAPACITY:

            result = "POOL_FULL"

        else:

            result = "ADMITTED"

            active.append((
                req.at + DURATION[req.lane],
                req,
            ))

        outcome[(req.lane, result)] += 1

        print(
            f"t={req.at:02d} "
            f"{req.label:21s} "
            f"{result:13s} "
            f"in_flight={len(active)}"
        )

    print(
        "SUMMARY",
        sorted(outcome.items()),
    )

    return outcome


if __name__ == "__main__":
    simulate("naive")
    simulate("protected")
```

The IP addresses in this simulation are documentation-only example addresses.

The code records them to illustrate that one business tenant can use several source IPs, but it doesn't implement an actual IP rate limiter.

The results `TENANT_QUOTA`, `LANE_FULL`, and `POOL_FULL` are simulator decisions, not HTTP status codes.

In a production API, the response semantics would depend on the documented policy and whether the operation was rejected, deferred, or durably queued.

---

# Lab B — Predict the Naive Outcome

Before running the script, inspect the arrival schedule.

At logical time zero, tenant Alpha begins five exports.

Each export occupies one simulated resource slot for twelve time units.

At time one, a maintenance job begins.

At time two, tenant Beta submits four booking requests.

### Questions

How many resource slots are occupied at time two?

How many booking requests can begin immediately?

Does the number of HTTP requests from Alpha necessarily violate a reasonable per-IP rate limit?

Why is the identity of the tenant more informative than the source IP for this scenario?

Write down your predictions before executing the script.

---

# Lab C — Run the Simulation

Execute:

```bash id="s32506run"
python studio.py
```

The first section shows the naive shared-pool behavior.

Five exports occupy five slots.

The maintenance task occupies the sixth.

The four booking requests arriving at time two cannot acquire capacity.

Another booking arriving at time four is also rejected.

Only the later booking at time thirteen is admitted, after the long-running exports finish.

### Investigation

Why are ordinary bookings affected even though their individual cost is small?

Would increasing the request-rate allowance improve the situation?

Would adding additional export workers necessarily help?

### Acceptance criteria

You can explain why the bottleneck is concurrent resource occupancy, not request arrival frequency.

---

# Lab D — Inspect the Protected Outcome

The second simulation applies lane-specific capacity limits.

Exports may occupy at most two slots.

Maintenance may occupy one slot.

Bookings have a reserved budget of three slots.

Tenant Alpha is also limited to two active exports.

### Observe

Three of the first four booking requests are admitted.

The fourth exceeds the booking lane's limit at that moment.

The booking from tenant Gamma is admitted later.

The final booking is also admitted.

In total, five booking operations are admitted and one is refused immediate admission.

### Questions

What improved?

Which workloads lost immediate execution capacity?

Why is the result better for critical customer-facing operations?

Does the protected configuration guarantee that a real PostgreSQL server cannot become saturated?

### Important qualification

This is a fixed-reservation model.

In a real system, the team might allow controlled borrowing of unused capacity.

But borrowing must preserve the intended minimum protection when critical demand returns.

---

# Lab E — Turn Admission Decisions into an API Contract

The simulation gives internal reasons.

A real API needs external behavior.

Consider these situations.

### Situation 1

A tenant exceeds its documented request-rate quota.

What response is appropriate?

### Situation 2

The system has a durable job queue.

An export cannot begin immediately but can safely be accepted for later processing.

What response is appropriate?

### Situation 3

A tenant is within quota, but the service is temporarily overloaded and cannot accept the request or durably queue it.

What response is appropriate?

### Situation 4

A requested file exceeds the maximum upload size.

What response is appropriate?

### Situation 5

The customer repeatedly requests a non-idempotent operation after an uncertain timeout.

What additional correctness issues arise before the system decides whether to retry?

### Acceptance criteria

Your design distinguishes customer-policy limits, temporary system overload, durable asynchronous acceptance, request validation, and uncertain business outcomes.

---

# Lab F — Add a Weighted Cost Budget

The existing simulator treats each active operation as one resource slot.

Now imagine the following cost model.

| Operation | Estimated cost units |
|---|---:|
| Retrieve one booking | 1 |
| Search a modest hotel catalogue | 3 |
| Generate a weekly report | 20 |
| Export all historical reservations | 80 |

These values are hypothetical.

### Your task

Design a token-bucket policy using cost units.

A tenant receives a defined refill rate and maximum burst allowance.

Each operation consumes its estimated cost.

### Investigate

How does this differ from counting requests?

What happens when an export turns out to be much more expensive than predicted?

What is the relationship between a weighted admission policy and a concurrency limit?

### Challenge

A tenant repeatedly submits queries that appear cheap but generate expensive database plans.

How would you prevent the tenant from bypassing the intended budget?

Consider parameter restrictions, measured execution cost, query timeouts, and asynchronous processing.

---

# Lab G — Multi-Tenant Fair Scheduling

Mercury has three tenants waiting for export workers.

Tenant Alpha has one hundred queued exports.

Tenant Beta has five.

Tenant Gamma has two.

The scheduler processes jobs in one global FIFO queue.

Alpha submitted its jobs first.

### Your task

Design a scheduling policy that prevents Alpha from monopolizing every worker for a long time.

Consider round-robin scheduling across tenants.

Then consider weighted allocation if Alpha has a larger contractual allowance.

### Questions

What prevents a tenant from enqueueing unlimited work?

How do you protect normal synchronization while allowing historical backfills?

What should happen if one tenant's job is much more expensive than another's?

How would you prevent a low-priority job from waiting forever?

---

# Lab H — Database Connection Pool Investigation

## Scenario

Mercury runs six API instances.

Each instance has a database connection pool of twenty.

There are four background worker instances, each with a pool of ten.

The PostgreSQL server has finite connection and execution capacity.

### Your assignment

Calculate the potential combined application-side connection demand.

Then explain why the configured maximum isn't necessarily the same as the number of currently active connections.

### Investigation

Your dashboard reports:

- Low Node.js CPU.
- High database connection occupancy.
- Increasing connection acquisition wait time.
- Moderate database CPU.
- Long-running export transactions.

Which hypotheses become more plausible?

Would increasing the API instance count be your first response?

What additional database metrics would you inspect?

---

# Lab I — Emergency Load Shedding

## Incident

The platform is degraded.

Bookings are timing out.

A historical export is running.

A scheduled cleanup job is also active.

You have access to the following operational controls:

Disable new exports.

Pause scheduled cleanup.

Reduce export concurrency.

Cancel selected running exports.

Increase application replicas.

Increase database pool sizes.

### Your task

Rank these interventions.

Explain which you would attempt first and why.

Identify which require additional evidence.

### Safety challenge

What if the scheduled cleanup job is responsible for deleting expired sensitive files?

Can it be postponed indefinitely?

Explain how temporary containment should differ from a permanent fix.

---

# Course-Level Production Incident Studio

## The Incident: Everyone's API Is Slow Except the Dashboard

This studio integrates all six SE325 lectures.

It is not a separate catalogue lecture.

### Scenario

Mercury operates a multi-tenant booking platform.

The system includes:

- A Node.js API.
- PostgreSQL.
- Redis.
- Background workers.
- Object storage.
- Supplier integrations.
- Scheduled cleanup and synchronization jobs.
- Historical reservation exports.

The company deployed a new release at 13:50.

At 14:00, tenant Alpha started a large reservation export.

At 14:05, the scheduled cleanup job began.

At 14:10, booking latency started increasing.

At 14:12, connection-pool acquisition wait time rose sharply.

At 14:15, customer support reported booking timeouts.

At 14:20, the incident team began investigating.

### Evidence packet A — Application metrics

```text id="s32506e1"
API CPU utilization:          32%
API memory utilization:       41%

HTTP average latency:        420 ms
HTTP p99 latency:             9.2 s

HTTP 5xx error rate:          4.8%

Redis cache hit ratio:        98.7%
Redis ordinary GET latency:   low
```

### Evidence packet B — Database metrics

```text id="s32506e2"
Database CPU utilization:     46%

Connection pool limit:        30
Connections occupied:         30

Requests waiting for pool:    84
Connection wait p99:          8.1 s

Long-running export queries:  5
Active cleanup transactions:  1
```

### Evidence packet C — Tenant activity

```text id="s32506e3"
Tenant Alpha:
  5 historical exports
  Multiple source IP addresses
  Low request frequency

Tenant Beta:
  Ordinary booking traffic
  No active exports

Tenant Gamma:
  Ordinary booking traffic
  No active exports
```

### Evidence packet D — Release changes

The new release introduced a larger export date range and increased the maximum number of concurrent exports per tenant.

It also changed how exports hold database cursors while generating output.

The cleanup job itself was unchanged.

### Evidence packet E — Operational behavior

The export workers use the same database connection pool as some interactive API requests.

An export can hold a connection while streaming large amounts of output.

The API rate limiter counts requests by IP address.

There is no per-tenant export-concurrency limit.

---

## Studio Assignment 1 — Reconstruct the Timeline

Explain which events preceded the latency increase.

Separate correlation from demonstrated causation.

Identify the evidence suggesting a shared database resource bottleneck.

Which information would you need to confirm that exports caused the connection exhaustion?

---

## Studio Assignment 2 — Rank the Hypotheses

Consider these explanations.

1. Redis caching stopped working.
2. PostgreSQL CPU reached its execution limit.
3. Export workers exhausted shared connection capacity.
4. The new deployment introduced a database query regression.
5. The cleanup job created lock contention.
6. A supplier API outage slowed booking requests.

Rank the hypotheses using the evidence.

Identify what would confirm or weaken each explanation.

Don't infer root cause merely from the order in which events happened.

---

## Studio Assignment 3 — Containment

The business is losing bookings.

What would you do during the first fifteen minutes?

Specify:

- Which workloads to pause.
- Which metrics to inspect.
- Which actions might restore capacity.
- What customer communication is necessary.
- How to preserve evidence.
- What recovery conditions you would monitor.

Explain why indiscriminately increasing pool sizes may worsen the incident.

---

## Studio Assignment 4 — The Export That Cannot Be Cancelled Cleanly

One export has been running for fifteen minutes.

Its worker has generated part of a CSV file.

The application has not yet published the final download artifact.

The user clicks Cancel.

### Your task

Design safe cancellation.

Address database cursor cleanup, temporary object cleanup, durable job status, retries, and the possibility that the worker crashes during cancellation.

Connect your answer to SE325-L01 and SE325-L02.

---

## Studio Assignment 5 — The Scheduled Cleanup Job

The cleanup job started shortly before the outage.

It removes abandoned multipart uploads and old temporary export objects.

### Your task

Determine whether the cleanup job is a contributing factor.

Inspect whether it holds unnecessary database resources.

Explain how it should behave when the scheduler launches duplicate occurrences or when the previous run remains active.

Connect your answer to SE325-L03.

---

## Studio Assignment 6 — The Data Repair After the Incident

During recovery, support discovers several export records marked completed even though their downloadable files were never fully generated.

An engineer proposes an SQL update changing every such record to failed.

### Your task

Design a safe repair.

Establish which artifacts exist.

Use guarded updates.

Record audit evidence.

Coordinate with object-storage cleanup.

Ensure that later retries or scheduled reconciliation cannot overwrite the repair incorrectly.

Connect your answer to SE325-L04.

---

## Studio Assignment 7 — The External Supplier Backfill

The incident delayed a supplier synchronization job.

The backlog now contains several hours of updates.

The team proposes increasing supplier API concurrency to catch up.

### Your task

Explain why this may create additional pressure on Mercury's database and the vendor's quota.

Design bounded catch-up.

Include vendor rate limits, source revisions, checkpoints, and reconciliation.

Connect your answer to SE325-L05.

---

## Studio Assignment 8 — Permanent Remediation

Design a long-term architecture.

Your proposal should address:

- Tenant-aware admission.
- Request-rate quotas.
- Export-concurrency limits.
- Expensive-query budgets.
- Dedicated background-worker capacity.
- Database connection-pool isolation.
- Underlying database resource limits.
- Durable export queues.
- Safe cancellation.
- Scheduled-job coordination.
- External integration quota management.
- Monitoring and emergency controls.

### Interviewer challenge

"We could solve this by buying a much larger PostgreSQL instance. Why complicate the software?"

Explain when additional capacity would help and why capacity alone doesn't establish tenant fairness or prevent unbounded future workload growth.

---

# STOP — Independent Studio Ends Here

Do not read the following diagnostic notes until you've completed the investigation.

The objective is to demonstrate that you can diagnose a complex production incident without immediately guessing at a fashionable infrastructure fix.

---

# Lab and Studio Diagnostic Notes

## Naive Pool

Five exports and one maintenance task occupy all six simulated permits.

Booking requests cannot acquire capacity.

The workload is legal under a simple request-rate policy but harmful to shared resource availability.

## Protected Pool

Two exports and one maintenance task occupy three permits.

The remaining capacity protects booking work.

The tenant quota prevents AlpineRooms from immediately monopolizing export execution.

The model is simplified; real PostgreSQL CPU, memory, locks, and I/O remain shared.

## Rate Versus Concurrency

Rate limits regulate arrival frequency.

Concurrency limits regulate simultaneous active work.

Weighted budgets add a rough model of operation cost.

All three can be useful.

## Incident Diagnosis

The strongest initial hypothesis is shared database connection exhaustion caused by long-running export work.

The release's increased export concurrency and longer connection holding are relevant evidence.

But the team should still inspect actual query and connection ownership before treating that hypothesis as proven.

## Redis

A healthy cache hit ratio doesn't exclude database connection exhaustion.

It also doesn't prove every important request is adequately cached.

## Cleanup

The cleanup job may contribute resource pressure.

It should be investigated, but the evidence doesn't establish it as the sole root cause.

## Immediate Containment

Pause or restrict optional expensive work, preserve critical booking capacity, and verify recovery.

Don't blindly scale API replicas or connection pools.

Coordinate cancellation with durable job state and resource cleanup.

## Permanent Design

A layered admission strategy should combine tenant quotas, endpoint and job concurrency limits, bounded queues, expensive-operation budgets, protected resource lanes, and overload monitoring.

## End-to-End Lesson

A backend can fail because every component is doing work it was individually permitted to do.

Reliability requires coordinating those individually legitimate operations against shared resource limits.

---

# Further Reading

Primary references:

- **RFC 6585 — HTTP 429 Too Many Requests:** https://www.rfc-editor.org/rfc/rfc6585.html
- **RFC 9110 — HTTP Semantics, 202 and 503:** https://www.rfc-editor.org/rfc/rfc9110.html
- **RFC 9110 — Retry-After:** https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3
- **PostgreSQL Wiki — Number of Database Connections:** https://wiki.postgresql.org/wiki/Number_Of_Database_Connections
- **Envoy — Circuit Breaking:** https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking
- **Envoy — Overload Manager:** https://www.envoyproxy.io/docs/envoy/latest/configuration/operations/overload_manager/overload_manager
- **Google SRE — Handling Overload:** https://sre.google/sre-book/handling-overload/
- **Google SRE — Addressing Cascading Failures:** https://sre.google/sre-book/addressing-cascading-failures/
- **AWS Builders' Library — Using Load Shedding to Avoid Overload:** https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/
- **AWS Builders' Library — Timeouts, Retries, and Backoff with Jitter:** https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- **Kubernetes — Resource Management for Pods and Containers:** https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
- **OWASP — API4:2023 Unrestricted Resource Consumption:** https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/

Related programme chapters:

- SE310-L01 — The Frontend–Backend Contract
- SE310-L03 — Application and Infrastructure Security
- SE320-L01 — The Anatomy of a Backend Service
- SE320-L03 — Queues, Workers, and Asynchronous Workflows
- CS430-L03 — Scaling and Load Management
- SE440-L01 — Observability: Understanding Production Systems
- SE440-L02 — Reliability Engineering and Incident Response
- SE325-L01 — Files, Uploads, and Object Storage
- SE325-L02 — Bulk Imports, Exports, and Background Data Operations
- SE325-L03 — Scheduled Jobs, Time, and Distributed Execution
- SE325-L04 — Production Data Repair, Audit, and Lifecycle
- SE325-L05 — Surviving Third-Party Integrations

---

# Dense Cheatsheet — Interview Glance Card

*The entire card is fenced so voice readers can skip it during the spoken lecture.*

```text id="s32506card"
SE325-L06 — API PROTECTION & MULTI-TENANT FAIRNESS
==================================================

CORE PRINCIPLE
--------------
Authorized work can still be harmful.

Request count != resource cost.

One noisy tenant can exhaust
shared capacity without violating
an ordinary per-IP rate limit.

FOUR QUESTIONS
--------------
Identity:
  Who is requesting work?

Permission:
  Can they perform it?

Entitlement:
  How much are they allowed?

Admission:
  Can we safely begin now?

RATE
----
Requests per time interval.

Fixed window:
  simple, boundary bursts

Sliding window:
  smoother moving-window limit

Token bucket:
  refill rate + burst capacity

Rate limits control ARRIVALS.

CONCURRENCY
-----------
Maximum simultaneously active work.

Semaphore / permits.

Concurrency limits control
RESOURCE OCCUPANCY.

LONG REQUEST
------------
Even low request rate can produce
high concurrency if duration is long.

Little's Law:
  average concurrency
  = arrival rate * average time

COST BUDGET
-----------
Not all requests cost the same.

Cheap lookup != huge export.

Weighted operations can reflect:
  query cost
  rows examined
  memory
  duration
  egress

Estimates need measurement.

IP LIMITS
---------
Useful at public edge.

But:
  one tenant may use many IPs
  many users may share one IP
  forwarded headers can be spoofed

Business quotas should use
trusted tenant identity.

DISTRIBUTED LIMITING
--------------------
Per-instance counters may
multiply allowance by replicas.

Use suitable shared control
or distributed quota allocation.

TENANT FAIRNESS
---------------
Equal quotas
Tiered quotas
Weighted sharing
Round robin
Weighted fair scheduling

Preserve minimum service.
Prevent starvation.
Bound queued work.

GLOBAL CAPACITY
---------------
Tenant entitlement does not
create physical capacity.

Need both:
  tenant limits
  global resource limits

DATABASE POOLS
--------------
Replica count * pool max
= potential aggregate demand.

More connections may worsen
an already saturated database.

Pool waiting != SQL execution.

BULKHEADS
---------
Separate capacity domains:
  booking
  background exports
  maintenance

Connection isolation helps,
but database CPU/I/O/locks
may remain shared.

PRIORITY
--------
Protect critical operations.

Examples:
  booking confirmation
  payment outcome inquiry
  authoritative booking status

Defer when possible:
  historical exports
  nonurgent analytics
  optional enrichment

QUEUING
-------
Accept durable asynchronous work.

202 Accepted:
  job accepted, not completed

Queues require:
  size limits
  job identity
  fairness
  retry policy
  cancellation
  status visibility

UNBOUNDED QUEUE != SOLUTION.

HTTP CODES
----------
429:
  client exceeded rate policy

503:
  temporary service overload
  or maintenance

202:
  asynchronously accepted

413:
  request content too large

Retry-After:
  optional wait guidance

LOAD SHEDDING
-------------
Reject work before consuming
scarce downstream resources.

Preserve useful operations.

Avoid retry storms.

GRACEFUL DEGRADATION
--------------------
Offer reduced functionality
when optional dependencies fail.

Don't bypass safety invariants.

CIRCUIT BREAKER
---------------
Protect against problematic
dependency failure behavior.

Not a substitute for
tenant fairness.

EMERGENCY CONTROLS
------------------
Pause exports
Reduce bulk concurrency
Suspend nonessential jobs
Cancel safe-to-restart work
Protect booking capacity

Monitor mitigation effects.
Avoid permanent forgotten flags.

OBSERVABILITY
-------------
Per-tenant request counts
Per-endpoint latency
Active concurrency
Pool occupancy
Pool wait p95/p99
Query time
Queue wait
Job count
Rejection reasons
Goodput
Critical business outcomes

INCIDENT SIGNALS
----------------
Redis healthy
CPU moderate
Pool completely occupied
Pool wait rising
Slow export started recently

Likely shared resource problem,
not necessarily CPU shortage.

INCIDENT PROCEDURE
------------------
1. Establish timeline
2. Identify critical impact
3. Inspect constrained resource
4. Segment by tenant/operation
5. Confirm actual ownership
6. Contain optional work
7. Protect critical paths
8. Verify recovery
9. Fix admission/isolation
10. Test under representative load

ANTI-PATTERNS
-------------
"Lower the IP rate limit."
"All requests cost the same."
"Increase workers when queue grows."
"Increase connection pools blindly."
"Streaming means cheap SQL."
"202 means the export completed."
"Separate pools isolate CPU."
"Every tenant deserves unlimited
 use because it is authenticated."
"Never reject legitimate requests."
"Retry every 503 immediately."

SE325 COURSE RECAP
------------------
L01 Files and object storage
L02 Bulk imports and exports
L03 Scheduled jobs
L04 Data repair and lifecycle
L05 Third-party integrations
L06 API fairness and overload

SENIOR MENTAL MODEL
-------------------
Every operation consumes
finite shared resources.

The system must control
admission, execution,
fairness and recovery.

A reliable backend prevents
legitimate work from becoming
a production-wide incident.

COURSE COMPLETE
```
