---
id: SE335-L01
course: SE335
title: "Redis in Production: Memory, Latency, and Cache Failures"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE335-L02
---

# SE335 — Queues, Caches, and Worker Production Diagnostics
## Lecture 01: Redis in Production — Memory, Latency, and Cache Failures

*Redis reports a 99% cache hit ratio. Its CPU is healthy. Memory is below the configured limit. Meanwhile, PostgreSQL has exhausted its connection pool, API latency is exploding, and everyone is wondering why the cache isn't protecting anything.*

---

# Part I — Intuition

## 1. The Beautiful Dashboard and the Burning Database

Imagine you're investigating a production incident at a hotel-booking platform.

The search API has become slow. Requests that normally finish in 150 milliseconds now take several seconds. PostgreSQL CPU utilization is high, database connections are saturated, and requests are queuing inside the backend connection pool.

Naturally, the team checks Redis.

Redis handles cached hotel descriptions, search summaries, availability previews, and a variety of frequently requested reference values.

The monitoring dashboard reports an impressive cache hit ratio: 99%.

Redis memory utilization looks healthy.

The Redis service responds quickly to ordinary `GET` commands.

One engineer concludes that caching is working correctly, so the database overload must have another explanation.

Another proposes increasing Redis memory.

A third suggests moving more data into Redis.

But the real problem may already be visible in the numbers.

Suppose the application performs ten thousand Redis lookups per second.

Nine thousand nine hundred are hits.

One hundred are misses.

That's a 99% hit ratio.

Now suppose each missed request triggers an expensive database aggregation. A hundred additional expensive queries per second might be enough to overwhelm the database.

And perhaps another five hundred requests per second bypass Redis entirely.

The database now receives six hundred operations per second from the relevant application paths, even though the cache's global hit ratio remains excellent.

The dashboard isn't lying.

**It's answering a different question from the one we actually care about.**

## 2. Hit Rate Is a Ratio, Not a Protection Guarantee

A hit ratio describes the fraction of observed cache lookups that succeed.

It doesn't describe how expensive the misses are.

It doesn't describe how many requests bypass the cache.

It doesn't describe which business operations are represented.

And it doesn't necessarily describe the database work avoided by the cache.

Imagine two categories of Redis keys.

The first category contains frequently read, inexpensive configuration values. The application requests them constantly, and almost every lookup succeeds.

The second category contains expensive customer reports. These reports are requested less frequently, but each miss requires a large MongoDB aggregation or PostgreSQL query.

If the inexpensive configuration lookups dominate the counters, the global hit ratio can remain close to 100% while report misses overload the database.

### Visual anchor 1 — A misleading global average

```text
Redis lookups during one interval

Configuration lookups:
  9,900 hits
  Almost no database work

Expensive report lookups:
  100 misses
  100 costly database operations

Additional bypass path:
  500 requests
  No Redis lookup at all

Redis hit ratio:
  9,900 / 10,000 = 99%

Database operations from these paths:
  600
```

The calculation is straightforward.

The interpretation is not.

We need to understand which cache misses occur, what they cost, and whether the cache protects the expensive part of the system.

## 3. The Hot Key That Hides Everything Else

Suppose one configuration key receives thousands of reads per second.

Nearly every read succeeds.

This key contributes an enormous number of hits to the global statistics.

Meanwhile, thousands of tenant-specific report keys are repeatedly expiring or missing.

Those report keys create expensive database work.

But their misses represent only a small fraction of total Redis lookups.

A single extremely popular key can therefore make the aggregate cache hit ratio look excellent.

This is an example of a **hot key**: one key receives a disproportionate share of traffic.

Hot keys can create two very different problems.

First, they can distort cache statistics, concealing poor caching behavior elsewhere.

Second, a sufficiently hot key can become a Redis-side throughput or latency bottleneck, particularly when commands involve large values or substantial work.

Those are separate effects.

A hot key is not automatically a problem merely because it's popular.

The problem depends on the traffic distribution, command cost, response size, and deployment architecture.

## 4. Expiration and Eviction Are Different

Imagine that hotel availability previews should remain cached for thirty seconds.

The application stores them with a time-to-live, or TTL.

After the TTL expires, Redis treats the key as expired.

The next request may encounter a cache miss and regenerate the value.

Now imagine Redis approaches its configured memory limit.

Under an eviction policy such as `allkeys-lru`, Redis can remove existing keys to make room for new data.

Those keys may have had substantial TTL remaining.

They disappear because of memory pressure, not because their freshness period ended.

### Visual anchor 2 — Two ways to lose a cached value

```text
Cached hotel availability
             |
             ├── TTL expires
             |      |
             |      v
             |   Expiration
             |
             └── Memory pressure
                    |
                    v
                 Eviction

Both may cause the next read to miss.

The underlying causes are different.
```

This distinction matters operationally.

If misses arise from deliberately short TTLs, increasing Redis memory may not help.

If misses arise from frequent eviction, increasing memory might help, but it may only postpone the problem if key cardinality continues growing without bound.

We must determine which mechanism is responsible.

## 5. The Cache Stampede

Now imagine a popular hotel-search result cached for sixty seconds.

Thousands of users access the result.

Every request is a hit.

Then its TTL expires.

Fifty requests arrive almost simultaneously.

Each checks Redis.

Each observes a miss.

Each independently queries the database.

The database executes the same expensive query fifty times.

Redis eventually receives fifty attempts to populate the same key.

The first query didn't need to happen fifty times.

The application failed to coordinate concurrent cache misses.

This is a cache stampede.

SE320-L02 introduced the concept and its general solutions. Here we're concerned with how it appears in production and how to measure it.

The central diagnostic question is:

**How many independent backend loads occur for one logically missing cache key?**

### Visual anchor 3 — Fifty requests, one missing value

```text
50 incoming requests
          |
          v
       Redis GET
          |
          v
      Cache miss
          |
          v
 50 simultaneous DB queries
          |
          v
      Database overload

With single-flight coordination:

50 incoming requests
          |
          v
      Cache miss
          |
          v
  One backend query
          |
          v
  Shared result for waiting requests
```

The second design still has a cache miss.

But it produces far less backend work.

That's why cache hit ratio alone is insufficient.

Two systems can have similar hit rates while generating radically different database loads during miss bursts.

## 6. Redis Can Be Fast and Still Make the Application Slow

Suppose Redis processes a `GET` command extremely quickly.

The application takes 300 milliseconds to receive its result.

Where did the time go?

Possibilities include network latency, connection acquisition, TLS, client scheduling, large-value transfer, or other commands blocking Redis's main command-execution path.

Redis's Slow Log measures the execution time of commands inside Redis.

It does not include the full time required for the client to send the request and receive the reply.

Therefore, an empty Slow Log doesn't prove that application-to-Redis latency is healthy.

The system may be slow outside the measured command execution.

This is another example of a metric answering a narrower question than we initially assume.

## 7. Memory Pressure Is More Complicated Than One Number

Suppose Redis is configured with a memory limit of two gigabytes.

The operating system reports that the Redis process consumes more than two gigabytes of resident memory.

Is Redis violating its configuration?

Not necessarily.

Redis's `maxmemory` controls the memory threshold relevant to its dataset and eviction behavior.

It is not an absolute ceiling on every byte of process memory.

Memory can also be consumed by allocator overhead, fragmentation, client buffers, replication buffers, persistence-related activity, and other structures.

The relationship between Redis's accounting and operating-system resident memory requires investigation.

Likewise, a low amount of free memory doesn't automatically mean Redis is malfunctioning.

For a cache with an appropriate eviction policy, using available capacity can be desirable.

The question is whether memory pressure produces excessive eviction, rejected writes, latency, or operating-system instability.

## 8. The Four Questions Behind a Redis Incident

A useful operational investigation begins with four questions.

**First: Is the cache protecting the expensive workload?**

Look beyond global hit rate to per-operation misses, backend calls, and database cost.

**Second: Why are cached values disappearing?**

Investigate TTL expiration, eviction, invalidation, and key construction.

**Third: Is Redis itself introducing latency?**

Separate Redis command execution from network, connection, and client-side delays.

**Fourth: Is the cached data correct and safely scoped?**

A fast cache can still return stale prices, wrong tenant data, or incorrectly cached failures.

### A tiny comprehension check

Suppose Redis reports a 99% hit ratio.

The database is overloaded.

A developer proposes doubling `maxmemory`.

What would you ask first?

Whether eviction is causing the misses.

If the misses are caused by short TTLs, high-cardinality keys, application bypass paths, or synchronized expiration, increasing memory may do little.

And if the global hit ratio is dominated by inexpensive hot-key reads, we need more specific workload metrics before interpreting it.

That is the mindset of production Redis forensics.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Redis Is an Operational System, Not a Magic Hash Map

We already studied caching architectures, freshness, invalidation, stampedes, and cache keys in SE320-L02.

This lecture assumes that foundation.

Our focus is operational evidence.

Redis manages keyspace data, memory allocation, expiration, eviction, client connections, command processing, persistence, and replication.

A problem in any of those areas can affect application behavior.

The central mistake is treating Redis as a box that either answers `GET` quickly or doesn't.

Production diagnosis requires understanding the actual path from application request to cached result and, when necessary, to the authoritative backend.

### 9.1 The complete request path

Imagine an availability-preview request.

The API receives the request.

The application constructs a tenant-scoped cache key.

It obtains a Redis connection.

It executes `GET`.

On a hit, it deserializes the cached value and returns it.

On a miss, it queries the authoritative backend.

It serializes the result.

It writes the new cache entry.

Then it returns the response.

Every step can introduce latency or failure.

Some requests never enter this path because they bypass caching entirely.

A Redis dashboard sees only the operations reaching Redis.

That's an important observability limitation.

## 10. The Global Hit Ratio Can Be Accurate and Useless

Redis exposes `keyspace_hits` and `keyspace_misses` through `INFO stats`.

A conventional hit-ratio calculation is successful key lookups divided by all successful and unsuccessful key lookups.

But those counters describe Redis keyspace lookup activity.

They don't necessarily correspond one-to-one with application HTTP requests.

Commands other than `GET`, including existence checks, can influence the counters.

Different services and business operations share them.

They are cumulative counters, so you should compare changes over a measurement interval rather than interpreting lifetime totals as current behavior.

### 10.1 A numerical incident

Suppose ten thousand relevant Redis lookups occur during a ten-second interval.

Nine thousand nine hundred are hits.

One hundred are misses.

The ratio is 99%.

Now suppose those hundred misses each trigger a query that consumes 200 milliseconds of database execution work.

That's twenty seconds of aggregate database execution demand over the ten-second interval, before considering concurrency, locks, or other workloads.

Additionally, a bypass route may send several hundred requests directly to the database.

The cache is successful at serving most lookups.

Yet it may be failing to protect the expensive query class.

### 10.2 Better measurements

For each important application operation, measure cache attempts, hits, misses, and bypasses.

Measure the backend calls triggered by misses.

Measure the backend's cost, not just call count.

A cheap primary-key lookup and a complex aggregation shouldn't automatically carry equal operational weight.

Also measure the number of concurrent backend loads for the same cache key.

These application-level metrics often explain database pressure better than the global Redis hit ratio.

### 10.3 The hit ratio can improve while protection worsens

Suppose traffic to a frequently cached configuration key doubles.

Redis records many additional hits.

The global hit ratio rises.

Meanwhile, expensive report misses remain unchanged.

Database pressure is no better.

The dashboard looks healthier because the workload mix changed.

This is a classic aggregate-metric problem.

Always interpret ratios alongside absolute rates and workload segmentation.

## 11. Redis `INFO`: Useful Counters, Dangerous Assumptions

Redis's `INFO` command exposes several sections.

`INFO stats` contains counters such as keyspace hits, misses, evictions, and expirations.

`INFO memory` describes Redis memory usage.

`INFO clients` reports connection-related information.

`INFO commandstats` provides cumulative command execution statistics.

`INFO latencystats` provides latency percentile information for commands.

These views help establish whether Redis is itself under pressure.

But they require careful interpretation.

### 11.1 Hits and misses

The counters are cumulative since their relevant reset point.

Calculate deltas over the same observation window.

Do not compare a five-minute database CPU spike with Redis hit statistics accumulated over months.

### 11.2 Expired keys

`expired_keys` counts keys removed through expiration processing.

It does not mean every cache miss was caused by expiration.

A key might never have existed, have been invalidated explicitly, or have been evicted.

Nor does every expired key necessarily produce an immediate application miss.

### 11.3 Evicted keys

`evicted_keys` counts keys removed because of maxmemory pressure.

A rising eviction rate suggests that memory policy and working-set size deserve investigation.

But eviction itself isn't necessarily a failure.

For a cache, evicting cold entries may be the correct behavior.

The important question is whether evictions are removing valuable data and increasing expensive misses.

### 11.4 Rejected writes

Under `noeviction`, Redis doesn't automatically discard existing keys to admit new data when the memory limit is reached.

Commands requiring additional memory can fail.

If application code treats Redis as optional, it may bypass caching and query the backend directly.

The database load can increase precisely when Redis reaches its limit.

The Redis service may remain reachable and answer reads while cache writes fail.

That is a subtle operational failure.

## 12. Expiration Versus Eviction

Expiration is governed by TTL.

Eviction is governed by memory pressure and eviction policy.

A key can expire without Redis being close to its memory limit.

A key can be evicted while it still has a long TTL.

These mechanisms can produce similar application symptoms but demand different remedies.

### 12.1 TTL behavior

Redis's `TTL` command reports the remaining lifetime of a key in seconds.

A positive result indicates remaining TTL.

`-1` indicates an existing key without an expiration.

`-2` indicates that the key doesn't exist.

The difference between absent and non-expiring matters when investigating cache behavior.

### 12.2 Passive and active expiration

Redis can discover expiration when a key is accessed.

It also performs background expiration work.

An expired key may remain physically allocated briefly until Redis removes it.

Therefore, expiration events and memory reclamation don't necessarily occur at the exact millisecond a TTL reaches zero.

### 12.3 Why synchronized TTLs are dangerous

Suppose the application warms ten thousand hotel-search keys during startup.

Every key receives the same sixty-second TTL.

A minute later, many keys expire around the same time.

Requests begin missing in a burst.

The backend receives a large amount of regeneration work.

TTL jitter can distribute expirations over time.

For example, instead of using exactly sixty seconds, the application might choose a TTL within a safe range around that value.

But jitter must respect the business freshness requirement.

Adding random time to a strict maximum freshness deadline can violate that deadline.

A safe design often jitters downward from the maximum permitted TTL.

## 13. Eviction Policies: What Happens Under Memory Pressure?

Redis supports several eviction policies.

For a cache-only Redis instance, `allkeys-lru` is a common starting point.

It considers all keys eligible for eviction and approximates least-recently-used behavior.

`allkeys-lfu` instead considers approximate access frequency.

`allkeys-random` selects keys randomly.

`volatile-lru` and related volatile policies consider only keys with expiration.

`volatile-ttl` favors keys with shorter remaining lifetimes.

`noeviction` rejects certain memory-growing operations rather than evicting existing keys.

### 13.1 Approximate LRU is not perfect LRU

Redis's LRU implementation uses sampling rather than maintaining a perfect global ordering of every access.

This reduces memory and computational overhead.

The resulting policy approximates recency well enough for many workloads.

Do not assume that the key with the mathematically oldest access timestamp will always be evicted first.

### 13.2 LFU has its own assumptions

LFU favors keys accessed frequently.

This can be attractive when a small set of keys accounts for a large fraction of traffic.

Redis's LFU behavior also uses approximate frequency tracking and decay.

An LFU policy isn't automatically superior to LRU.

Workloads change.

A key that was popular last week may no longer deserve memory today.

The correct policy should be evaluated against the application's access distribution.

### 13.3 The volatile-policy trap

Imagine a Redis instance containing two kinds of data.

Temporary cached search results have TTLs.

Other keys have no expiration.

The instance uses `volatile-lru`.

Redis can evict only the keys with expiration.

If most memory is occupied by non-expiring keys, the cacheable subset may churn heavily or writes may fail when no eligible candidates remain.

Changing the policy to `allkeys-lru` might solve the immediate pressure but now makes the non-expiring keys eligible for eviction.

If those keys hold durable job state or critical coordination information, this could be disastrous.

The architectural problem is mixing data with incompatible durability and eviction requirements.

A dedicated cache instance is often safer.

## 14. Redis Memory: Allocated Memory Is Not Resident Memory

Redis exposes several memory measurements.

`used_memory` represents memory allocated through Redis's allocator.

`used_memory_rss` represents the process's resident memory reported by the operating system.

`maxmemory` controls the configured memory threshold used for eviction behavior.

These numbers need not match.

### 14.1 Fragmentation and allocator overhead

Memory allocators manage memory in blocks and arenas.

After many allocations and frees, resident memory may remain larger than the amount currently used for live Redis data.

Fragmentation can contribute to this difference.

But a high fragmentation ratio isn't automatically evidence of one specific problem.

Small instances and allocator overhead can distort the ratio.

Use absolute byte measurements and the broader memory breakdown.

### 14.2 Replication and persistence buffers

Redis may retain buffers for replication or persistence-related operations.

Some memory isn't counted toward eviction in the same way as ordinary cache data.

The `mem_not_counted_for_evict` metric can help explain part of this.

If the instance performs replication or persistence, leaving adequate RAM headroom above the configured maxmemory can be essential.

### 14.3 `maxmemory` isn't an operating-system safety guarantee

A Redis instance configured with a two-gigabyte maxmemory limit can still consume more than two gigabytes of process memory.

Likewise, command execution can temporarily exceed the configured threshold before eviction restores the intended dataset limit.

For a containerized deployment, distinguish Redis's maxmemory configuration from the container's actual memory limit.

A container OOM kill is not equivalent to Redis evicting cold keys.

The former terminates the process.

The latter is controlled cache replacement.

## 15. Why Increasing `maxmemory` May Be the Wrong Fix

Suppose a cache repeatedly loses useful keys.

Increasing memory can be reasonable if the working set simply doesn't fit and additional capacity is available.

But the same symptom can arise from other causes.

Keys may expire after only a few seconds.

Cache keys may include unnecessary volatile parameters, producing a unique key for almost every request.

The application may write enormous values that provide little benefit.

One tenant may generate disproportionate cardinality.

A background process may populate the cache with data nobody requests.

Increasing memory doesn't correct those problems.

### 15.1 Key cardinality is part of the workload

Imagine a cache key constructed from tenant ID, hotel ID, date range, occupancy, currency, language, and every optional filter.

Some of those dimensions are necessary.

Others may be included accidentally.

If a timestamp or unique request ID becomes part of the key, nearly every request might generate a new entry.

The cache can consume substantial memory while providing very few useful hits.

A larger Redis instance merely stores more one-time values.

### 15.2 Value sizes matter too

A cache containing ten million tiny entries behaves differently from one containing a few thousand enormous serialized JSON objects.

Large values cost memory, network transfer, serialization, and deserialization.

Even when a large value is fetched from memory, moving several megabytes over the network may dominate application latency.

Consider caching a smaller representation when appropriate.

But don't strip fields required for correctness merely to make payloads smaller.

## 16. Finding Large Keys Without Blocking Production

A useful Redis investigation often begins by identifying which key patterns consume memory.

But careless keyspace inspection can create additional operational problems.

The `KEYS` command searches the entire keyspace synchronously.

Against a large production dataset, broad `KEYS *` operations can block the server long enough to cause visible latency.

Redis provides cursor-based scanning through `SCAN`.

This lets clients iterate through the keyspace incrementally.

### 16.1 `SCAN` is incremental, not free

A full scan still performs work.

The `COUNT` argument is a hint, not a guarantee of exact returned batch size.

Keys may appear more than once during an iteration.

And a changing keyspace can affect which keys appear.

Applications using `SCAN` must handle those semantics.

### 16.2 Measuring values

`MEMORY USAGE` estimates the memory consumed by a particular key and its value.

This is useful for identifying unexpectedly large entries.

But measuring memory usage across millions of keys can itself create substantial diagnostic traffic.

Use bounded sampling or controlled scans.

Avoid turning the investigation into another load generator.

### 16.3 Big keys versus hot keys

A large key consumes memory and may create expensive transfer or processing work.

A hot key receives disproportionate request traffic.

These are different properties.

A tiny counter can be extremely hot.

A huge cached report may be accessed only once per day.

The appropriate remedy depends on which property causes the problem.

## 17. Redis Latency: Separate Server Execution from the Round Trip

Redis is optimized for low-latency command execution, but application-observed latency includes more than server-side processing.

Consider four categories.

**Command execution:** How long Redis spends processing the command.

**Network:** Time to send the request and receive the result.

**Connection management:** Time spent establishing or acquiring a usable connection.

**Client work:** Scheduling, serialization, deserialization, and other application processing.

A request can be slow even when Redis's command execution is fast.

### 17.1 The Slow Log

Redis's Slow Log records commands whose execution time exceeds a configured threshold.

It measures Redis command execution, excluding client communication and related I/O.

Therefore, an empty Slow Log doesn't prove the application-to-Redis path is fast.

It only tells us that the configured threshold didn't capture slow command executions during the observed period.

### 17.2 Latency monitoring

Redis has a latency-monitoring subsystem.

It can record events exceeding a configured threshold.

Commands such as `LATENCY LATEST`, `LATENCY HISTORY`, and `LATENCY DOCTOR` help investigate spikes.

Latency monitoring is normally disabled until configured.

A diagnostic threshold should reflect the application's actual latency requirements.

### 17.3 Command statistics

`INFO commandstats` exposes cumulative execution statistics by command.

This can help identify expensive command categories.

`INFO latencystats` provides percentile information for command execution.

These metrics complement Slow Log and latency monitoring.

They don't replace application-level end-to-end latency measurements.

## 18. The Slow Command That Blocks Other Clients

Redis processes command execution primarily through a main execution thread, although modern Redis versions can use additional threads for certain I/O and background activities.

This architecture makes many ordinary operations efficient.

But expensive commands can delay other clients.

Suppose an application executes a computationally heavy operation against a very large collection.

While Redis performs that work on the main command-execution path, unrelated requests can experience additional latency.

### 18.1 Avoid unbounded operations

Commands such as broad `KEYS` scans or expensive operations on enormous collections can create latency spikes.

Evaluate command complexity and the size of the affected data structure.

A command that is fast for ten elements may be expensive for ten million.

### 18.2 Slow commands versus slow network

If command execution statistics remain low but client latency is high, investigate network, payload size, connection pool behavior, and application scheduling.

If Redis itself records expensive command execution, investigate the commands and data structures involved.

These are different investigations.

## 19. Pipelining and Round-Trip Costs

Suppose an application needs fifty independent cached values.

It issues fifty sequential `GET` requests.

Even if Redis executes each command rapidly, the client pays repeated network round-trip latency.

Pipelining lets the client send several commands without waiting for a response after every individual request.

Commands such as `MGET` can also retrieve multiple values in one operation.

### 19.1 Pipelining isn't unlimited parallelism

A very large pipeline can consume substantial buffers and create bursts of server work.

It can also complicate error handling.

The goal is reducing unnecessary round trips, not placing millions of commands into one unbounded request.

### 19.2 Pipeline execution isn't a transaction

Pipelining does not automatically provide all-or-nothing semantics.

Commands can be executed individually.

If the application requires atomic behavior, Redis transactions or scripts may be relevant, subject to their own limitations.

Performance batching and atomicity are separate concerns.

## 20. Hot Keys and Skewed Traffic

A hot key receives disproportionately high traffic.

Imagine one global configuration key requested thousands of times per second.

Redis may serve it quickly.

But its traffic can dominate hit counters and network activity.

If the value is large, repeated transfers can consume substantial bandwidth.

In clustered Redis deployments, one key belongs to one hash slot and therefore one shard at a time.

An extremely hot key can create an uneven load distribution.

### 20.1 Hot-key detection

Potential evidence includes application-level key-pattern metrics, sampled access logs, command statistics, and carefully controlled Redis diagnostic tools.

Redis provides keyspace-analysis facilities, but some require particular eviction-policy configurations or can impose scanning costs.

Avoid running intrusive diagnostics against a saturated production instance without considering their impact.

### 20.2 Possible remedies

If a hot value is stable and safe to cache in process, local caching can reduce repeated Redis requests.

If the value is large, a smaller representation may help.

If application traffic is unnecessarily repetitive, request coalescing or batching may reduce load.

If the key is used for mutable coordination state, replicating or locally caching it can break correctness.

Again, the data's semantics determine which optimizations are valid.

## 21. The Cache Stampede: Diagnose Concurrency, Not Just Misses

Suppose a popular report expires.

Fifty concurrent requests observe the same missing key.

All fifty query the database.

Redis sees fifty misses.

But the database sees fifty expensive loads.

One miss is not necessarily one backend operation, and many misses can be concentrated on one logical key.

### 21.1 Local single-flight

Within one application process, requests for the same missing key can share one in-progress loader operation.

The first request begins the backend query.

Other requests wait for the same result.

After completion, the cache is populated.

This reduces duplicate loads within that process.

But if ten application replicas experience the same miss, each may still perform its own backend load.

### 21.2 Distributed coordination

Redis can coordinate loaders through a short-lived ownership key using `SET` with `NX` and an expiration.

One worker becomes the loader.

Others wait, retry, or serve a permitted stale value.

The ownership token and release operation must be handled safely.

A simple unconditional `DEL` can accidentally remove another worker's newer lock after the original lease expires.

A compare-and-delete operation avoids that particular mistake.

But a Redis lease isn't a universal distributed correctness guarantee.

If the loader stalls past its lease and another worker starts, duplicate loading can still occur.

For read-only cache regeneration, occasional duplicate work may be acceptable.

For payments or other irreversible operations, the architecture needs stronger business-level idempotency and concurrency controls.

### 21.3 Stale-while-revalidate

For data that tolerates bounded staleness, the application can return an existing stale value while one background operation refreshes it.

This can preserve availability during regeneration.

But it is not appropriate for every kind of data.

A stale hotel description may be harmless.

A stale inventory preview must not be treated as a binding reservation guarantee.

A stale authorization decision can be dangerous.

The freshness contract must be explicit.

## 22. Negative Caching and Failure Classification

Suppose a request asks for a hotel ID that doesn't exist.

Without negative caching, repeated requests for that identifier may query the authoritative database every time.

A short-lived negative cache entry can represent the known absence.

This reduces repeated expensive lookups.

But there is a crucial distinction.

**Not found** is not the same as **temporarily unavailable**.

If the backend times out or returns an error, caching that failure as though the hotel doesn't exist can create a long-lived incorrect result.

Likewise, caching a negative result too aggressively can hide newly created data.

### 22.1 Cache failures according to meaning

A confirmed absence can sometimes be cached briefly.

A transient database outage usually requires a different failure policy.

A permission denial may depend on user identity and authorization context.

A missing tenant-scoped object must not be cached under a key shared across tenants.

Correct negative caching requires carefully defined semantics.

## 23. Cache Keys Are Security and Correctness Boundaries

A hotel availability preview may depend on tenant, hotel, dates, occupancy, currency, and other dimensions.

If the key omits a relevant dimension, the application can return a cached value created for another request context.

That can produce stale or incorrect business results.

More seriously, omitting tenant or authorization scope can create cross-tenant data exposure.

### 23.1 Key design is not merely performance tuning

A key identifies the logical value being cached.

It must encode all dimensions needed to distinguish values safely.

But adding unnecessary dimensions creates excessive key cardinality and reduces reuse.

The design is a balance.

Too few dimensions can cause incorrect sharing.

Too many can eliminate useful hits.

### 23.2 Versioned keys and invalidation

Some systems use a version in the cache key.

When underlying data changes, a new version causes readers to use a different key.

This can avoid certain stale-publication races.

But versioning introduces storage growth and cleanup considerations.

The application must know which version is current.

As always, the maintenance contract matters.

## 24. Redis Availability and Cache Failure Modes

What happens if Redis becomes unavailable?

A cache-aside application may fall back to the authoritative database.

That seems sensible.

But if Redis fails for a high-traffic endpoint, the database may suddenly receive the entire workload that Redis normally absorbs.

The fallback can create a second outage.

### 24.1 Failure behavior needs capacity limits

A robust application considers how many fallback requests the database can safely handle.

Possible controls include bounded concurrent loads, request coalescing, circuit breakers, admission limits, stale-value policies, and degraded responses.

Not every endpoint should simply hammer the database until Redis recovers.

### 24.2 Timeouts and connection pools

The Redis client should use appropriate connection and command timeouts.

An application pool can become exhausted if requests wait too long for Redis connections or responses.

A short command execution time doesn't rule out long client-side queueing.

Measure pool acquisition latency separately when relevant.

### 24.3 Cache failure must not turn into data corruption

Cached data should not become authoritative merely because the database is slow.

For a hotel booking, the backend must still confirm availability and enforce the reservation transaction.

Redis can accelerate previews.

It cannot automatically replace the database's business invariants.

## 25. The Production Forensics Procedure

Let's return to the opening incident.

Redis reports 99% hits.

PostgreSQL is overloaded.

The team wants to increase Redis memory.

What should a senior engineer do?

### Step 1 — Establish the affected operation

Which API endpoints are slow?

Which database queries are expensive?

Are they triggered by cache misses, bypasses, or unrelated workflows?

### Step 2 — Compare rates, not lifetime counters

Measure Redis hit and miss deltas during the incident interval.

Measure database calls during the same interval.

Break the workload down by endpoint and key family.

### Step 3 — Identify whether misses are expensive

A hundred cheap misses may be harmless.

Ten misses triggering enormous reports may be significant.

Determine the cost of each miss class.

### Step 4 — Inspect TTL and eviction behavior

Are useful keys expiring?

Are keys being evicted under memory pressure?

Are writes rejected?

What eviction policy is configured?

### Step 5 — Check concurrency amplification

Do multiple requests regenerate the same missing value simultaneously?

Count backend loads per cache key.

### Step 6 — Inspect key design

Are keys too specific, creating low reuse?

Are required dimensions missing, threatening correctness?

Are some endpoints bypassing caching entirely?

### Step 7 — Investigate Redis latency separately

Inspect Slow Log, latency events, command statistics, client connections, and application-observed round trips.

Don't assume all latency originates inside Redis.

### Step 8 — Form a causal hypothesis

For example:

"The global hit ratio is dominated by a frequently requested configuration key. The expensive report family has short TTLs, and concurrent misses trigger duplicate MongoDB aggregations. Redis memory is not under eviction pressure, so increasing `maxmemory` will not address the main problem."

That is a diagnosis.

### Step 9 — Make a focused correction

Possible changes include workload-specific cache metrics, longer safe TTLs, TTL jitter, single-flight, appropriately scoped negative caching, better key normalization, or bounded fallback concurrency.

The correction must preserve freshness and isolation requirements.

### Step 10 — Verify the result

Measure database query rate, query cost, API latency, cache miss rate for the relevant key family, Redis memory, and error behavior.

A higher global hit ratio is not sufficient evidence of success.

The meaningful outcome is reduced expensive backend work without introducing stale or unsafe data.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The 99% Hit Rate

Redis performs 10,000 lookups per second and reports a 99% hit ratio.

The database is overloaded.

Give three plausible explanations that are consistent with those metrics.

## Question 2 — Expiration Versus Eviction

A cached report disappears before its configured TTL ends.

What Redis mechanism might explain this?

Which statistics and configuration would you inspect?

## Question 3 — The Memory Fix

Redis memory pressure causes frequent eviction.

A developer proposes doubling `maxmemory`.

What additional questions must you answer before accepting the proposal?

## Question 4 — Hot Keys

One key receives half of all Redis reads.

The global hit ratio is excellent.

Why might that hide poor caching behavior in an expensive report endpoint?

## Question 5 — Slow Log

Application requests experience 200-millisecond Redis round trips.

The Slow Log contains no entries.

Does that prove Redis isn't involved?

What should you investigate next?

## Question 6 — Noeviction

Redis uses `noeviction` and reaches its maxmemory limit.

What happens to memory-growing writes?

How could that indirectly overload the database?

## Question 7 — The Stampede

Fifty application requests miss the same report key simultaneously.

How many database queries might a naive cache-aside implementation execute?

How could single-flight change that?

What limitation does process-local single-flight have?

## Question 8 — Negative Caching

The authoritative database times out when looking up a hotel.

Should the application cache a "hotel not found" result?

Why or why not?

## Question 9 — Tenant Isolation

A cache key contains hotel ID and dates but omits tenant ID.

What correctness or security problem could this create?

## Question 10 — Operational Judgment

The team wants to mix cached search results with non-expiring job-coordination keys in one Redis instance using `allkeys-lru`.

What would you challenge about that design?

---

# Solutions and Discussion

## Solution 1 — The 99% Hit Rate

The remaining one percent can still represent substantial absolute miss traffic.

The misses may trigger disproportionately expensive database operations.

Other requests may bypass Redis entirely.

Hot, inexpensive cached keys can dominate global hit statistics.

Concurrent misses can also amplify backend work.

## Solution 2 — Expiration Versus Eviction

Memory-pressure eviction can remove a key before its TTL expires.

Inspect `evicted_keys`, memory usage, `maxmemory`, the eviction policy, and relevant key-access patterns.

Also rule out explicit invalidation or overwriting.

## Solution 3 — The Memory Fix

Determine whether evictions are causing the expensive misses.

Inspect key cardinality, value sizes, TTLs, working-set behavior, and available RAM.

Consider allocator overhead and container limits.

Additional memory may help, but it may also postpone unbounded growth.

## Solution 4 — Hot Keys

The hot key contributes a large number of hits.

Expensive report misses may represent only a small fraction of total lookups while generating most database cost.

Measure hit and miss rates by business operation or key family.

## Solution 5 — Slow Log

No.

Slow Log records command execution exceeding its configured threshold, not end-to-end client round-trip latency.

Investigate network transfer, large values, connection acquisition, client scheduling, server latency events, and the threshold configuration.

## Solution 6 — Noeviction

Memory-growing writes can fail once the configured memory threshold is reached.

If the application responds by bypassing caching, more traffic may reach the authoritative database.

The failure needs to be monitored and handled deliberately.

## Solution 7 — The Stampede

A naive implementation might execute fifty independent database queries.

Single-flight can reduce that to one backend load within a process.

But separate application replicas may still load the same key independently.

Distributed coordination or another bounded regeneration strategy may be necessary.

## Solution 8 — Negative Caching

No.

A timeout doesn't establish that the hotel doesn't exist.

Caching it as absence would turn a transient failure into incorrect data.

Use a failure policy appropriate to transient unavailability.

## Solution 9 — Tenant Isolation

Two tenants could receive data through the same cache key despite different authorization or business contexts.

This can create incorrect responses or cross-tenant information exposure.

The key must encode the relevant isolation dimensions.

## Solution 10 — Mixed Eviction Semantics

`allkeys-lru` can evict any key, including non-expiring coordination keys.

If those keys must be preserved, the architecture is unsafe.

Use separate instances or another design with appropriately distinct durability and eviction guarantees.

---

# The Mental Model Worth Keeping

Redis performance isn't one hit-ratio number.

A production cache is a system with memory limits, key lifetimes, eviction policies, command execution costs, connections, and a downstream database dependency.

The essential questions are:

**Which requests are protected? Why do misses happen? How much backend work does each miss create? Is Redis itself slow? What happens when the cache fails?**

A healthy cache dashboard is not proof of a healthy application.

Measure the protected workload, not merely the cache.

---

# Next Lecture — SE335-L02: RabbitMQ and Worker Failure Forensics

We've investigated Redis as a shared caching system.

But many backend architectures also rely on asynchronous queues and workers.

A worker might process external-asset scans, import files, generate reports, or execute long-running tasks.

The message broker allows work to be buffered and processed outside the original HTTP request.

That sounds straightforward.

Then the queue begins growing.

Someone increases the number of consumers.

Throughput gets worse.

A poison message is rejected and immediately requeued, producing an endless loop.

Or a worker acknowledges a message before committing its database result, then crashes.

The next lecture investigates RabbitMQ's actual delivery and acknowledgment mechanisms, prefetch, retries, dead-letter routing, and worker concurrency.

*The spoken lecture ends here. The following practical exercises require a disposable local Redis instance and are intended for hands-on investigation.*

---

# Optional Practical Lab — Redis Production Forensics

## Lab Contract

This laboratory creates a deliberately misleading cache hit ratio, a cache stampede, memory-pressure eviction, and a write failure under `noeviction`.

All experiments use a disposable Redis instance.

Do not run `FLUSHDB`, `CONFIG SET maxmemory`, or eviction-policy experiments against shared or production Redis.

For each exercise:

**Predict → Measure → Diagnose → Correct → Verify.**

The solution notes are below the exercises.

## Lab 1 — Start a Disposable Redis Instance

Run Redis 8.0 with persistence disabled and a cache-only eviction policy.

```bash
docker run --name se335-redis \
  -p 6387:6379 \
  -d redis:8.0 \
  redis-server \
  --save "" \
  --appendonly no \
  --maxmemory 32mb \
  --maxmemory-policy allkeys-lru
```

If the container already exists but is stopped:

```bash
docker start se335-redis
```

Check connectivity:

```bash
docker exec se335-redis redis-cli PING
```

Expected response: `PONG`.

Inspect memory configuration:

```bash
docker exec se335-redis redis-cli CONFIG GET maxmemory
docker exec se335-redis redis-cli CONFIG GET maxmemory-policy
```

This instance is explicitly disposable. It must not contain durable application or coordination state.

---

# Lab 2 — The 99% Hit Ratio Incident

## Objective

Create a Redis workload with a 99% hit ratio while demonstrating that expensive database traffic can remain substantial.

We'll simulate authoritative database work rather than installing PostgreSQL or MongoDB for this experiment.

The Redis operations are real. The database calls are counted by the application.

### Install the Python client

Use a local Python environment:

```bash
python -m pip install "redis>=5,<8"
```

Create `redis_hit_ratio.py`.

The script clears only the disposable database, populates one hot key, performs 9,900 successful lookups and 100 misses, then accounts for 500 requests that bypass Redis.

```python
import asyncio
from redis.asyncio import Redis

REDIS_URL = "redis://localhost:6387/0"

async def main():
    redis = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    await redis.flushdb()
    await redis.set(
        "lab:config:global",
        "configured",
        ex=600,
    )

    before = await redis.info("stats")

    backend_calls = 0
    expensive_work_units = 0

    # Hot, inexpensive key: 9,900 hits.
    for _ in range(9900):
        result = await redis.get("lab:config:global")
        assert result == "configured"

    # Unique expensive report keys: 100 misses.
    for n in range(100):
        result = await redis.get(f"lab:report:{n}")

        if result is None:
            backend_calls += 1
            expensive_work_units += 200

    # Requests bypassing the cache completely.
    for _ in range(500):
        backend_calls += 1
        expensive_work_units += 200

    after = await redis.info("stats")

    hits = (
        after["keyspace_hits"]
        - before["keyspace_hits"]
    )

    misses = (
        after["keyspace_misses"]
        - before["keyspace_misses"]
    )

    ratio = hits / (hits + misses)

    print("Redis hits:", hits)
    print("Redis misses:", misses)
    print(f"Hit ratio: {ratio:.2%}")
    print("Backend calls:", backend_calls)
    print(
        "Synthetic DB work units:",
        expensive_work_units,
    )

    await redis.aclose()

asyncio.run(main())
```

Run:

```bash
python redis_hit_ratio.py
```

### Expected observation

The script generates a 99% Redis hit ratio over its explicit lookup operations.

It also records 600 simulated backend calls.

The synthetic work-unit counter is not actual database CPU time. It represents deliberately different operation costs.

### Investigation questions

Why can the hit ratio remain excellent?

Which requests dominate the hit counter?

Which requests generate backend work?

Would increasing Redis maxmemory change the results of this script?

What application metrics would reveal the problem before the database becomes overloaded?

### Acceptance criteria

You can explain why global Redis counters do not describe the complete application's backend cost.

You can propose workload-specific metrics for cache attempts, misses, bypasses, and backend loads.

---

# Lab 3 — A Reproducible Cache Stampede

## Objective

Demonstrate that fifty simultaneous requests for one missing key can trigger fifty duplicate backend loads.

Then introduce process-local single-flight.

Create `redis_stampede.py`.

The fake backend sleeps for eighty milliseconds to make concurrent overlap visible.

```python
import asyncio
from redis.asyncio import Redis

REDIS_URL = "redis://localhost:6387/0"
KEY = "lab:report:shared"

async def main():
    redis = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    db_calls = 0

    async def load_from_database():
        nonlocal db_calls

        db_calls += 1
        await asyncio.sleep(0.08)

        return "report-value"

    async def naive_get():
        cached = await redis.get(KEY)

        if cached is not None:
            return cached

        value = await load_from_database()

        await redis.set(KEY, value, ex=30)

        return value

    await redis.delete(KEY)

    results = await asyncio.gather(
        *(naive_get() for _ in range(50))
    )

    print("Naive result count:", len(results))
    print("Naive DB calls:", db_calls)

    # Reset for single-flight experiment.
    await redis.delete(KEY)
    db_calls = 0

    lock = asyncio.Lock()

    async def singleflight_get():
        cached = await redis.get(KEY)

        if cached is not None:
            return cached

        async with lock:
            # Double-check after waiting.
            cached = await redis.get(KEY)

            if cached is not None:
                return cached

            value = await load_from_database()

            await redis.set(KEY, value, ex=30)

            return value

    results = await asyncio.gather(
        *(singleflight_get() for _ in range(50))
    )

    print("Single-flight result count:", len(results))
    print("Single-flight DB calls:", db_calls)

    await redis.aclose()

asyncio.run(main())
```

### Predictions

How many backend calls will the naive implementation make?

Why might the count depend on timing in a real network environment?

How many should the single-flight implementation make in this controlled experiment?

Why does the second cache check matter?

### Acceptance criteria

The naive case demonstrates concurrent duplicate backend work.

The corrected case performs one backend load within the process.

You can explain why the same local lock doesn't coordinate multiple application replicas.

---

# Lab 4 — Expiration Versus Eviction

## Objective

Observe both key expiration and memory-pressure eviction.

Begin with a clean disposable database.

```bash
docker exec se335-redis redis-cli FLUSHDB
```

### Part A — TTL

Create a short-lived key:

```bash
docker exec se335-redis redis-cli SET lab:ttl "value" EX 3
docker exec se335-redis redis-cli TTL lab:ttl
```

Wait a few seconds and check again.

```bash
docker exec se335-redis redis-cli TTL lab:ttl
```

Expected after expiration: `-2`.

Create a key without a TTL:

```bash
docker exec se335-redis redis-cli SET lab:persistent "value"
docker exec se335-redis redis-cli TTL lab:persistent
```

Expected: `-1`.

### Part B — Memory pressure

Lower the disposable instance's memory limit.

```bash
docker exec se335-redis redis-cli CONFIG SET maxmemory 8mb
docker exec se335-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

Create `redis_pressure.py`.

It writes many medium-sized values, all with long TTLs.

```python
import asyncio
from redis.asyncio import Redis

async def main():
    redis = Redis.from_url(
        "redis://localhost:6387/0"
    )

    before = await redis.info("stats")

    payload = b"x" * 2048

    for n in range(6000):
        await redis.set(
            f"lab:pressure:{n}",
            payload,
            ex=600,
        )

    after = await redis.info("stats")

    print(
        "Evictions during test:",
        after["evicted_keys"]
        - before["evicted_keys"],
    )

    print(
        "Expired during test:",
        after["expired_keys"]
        - before["expired_keys"],
    )

    print(
        "Existing pressure keys:",
        await redis.dbsize(),
    )

    await redis.aclose()

asyncio.run(main())
```

Run:

```bash
python redis_pressure.py
```

### Investigation

Did the eviction counter increase?

Why could keys disappear even though their TTLs hadn't expired?

Why might the exact eviction count vary?

Would increasing `maxmemory` permanently solve a workload with unbounded key creation?

### Acceptance criteria

You can distinguish expiry-driven removal from memory-pressure eviction.

You understand that the eviction policy controls which keys may be removed.

---

# Lab 5 — The Noeviction Failure

## Objective

Observe how Redis can remain reachable while memory-growing writes fail.

On the disposable instance, change the eviction policy:

```bash
docker exec se335-redis redis-cli CONFIG SET maxmemory-policy noeviction
```

With memory still near the configured limit, attempt to write a new large value.

Use a small Python experiment:

```python
import asyncio
from redis.asyncio import Redis
from redis.exceptions import ResponseError

async def main():
    redis = Redis.from_url(
        "redis://localhost:6387/0"
    )

    try:
        await redis.set(
            "lab:noeviction:new",
            b"z" * 200_000,
        )

        print("Write succeeded.")
    except ResponseError as error:
        print("Write rejected:", error)

    await redis.aclose()

asyncio.run(main())
```

Depending on how much memory is currently in use, the write may or may not fail immediately.

If necessary, add more pressure keys until the configured threshold is reached.

### Questions

Does Redis still answer `PING`?

Can existing cached values still be read?

What happens if application code silently treats every failed `SET` as permission to query the database on every request?

### Cleanup

Restore the disposable cache configuration:

```bash
docker exec se335-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
docker exec se335-redis redis-cli CONFIG SET maxmemory 32mb
docker exec se335-redis redis-cli FLUSHDB
```

### Acceptance criteria

You understand the difference between a reachable Redis service and a cache that can successfully accept new data.

You can explain how write failures can indirectly increase backend load.

---

# Lab 6 — Redis Memory Forensics

## Objective

Inspect Redis's memory accounting without assuming that one number explains everything.

Run:

```bash
docker exec se335-redis redis-cli INFO memory
docker exec se335-redis redis-cli MEMORY STATS
```

Identify:

- `used_memory`
- `used_memory_rss`
- `used_memory_peak`
- `maxmemory`
- `mem_fragmentation_ratio`
- `mem_not_counted_for_evict`, where reported

### Investigation

Why can RSS exceed allocator-reported memory?

Why is maxmemory not identical to the container's memory limit?

Why should replicated or persistent Redis deployments leave headroom for additional buffers?

### Large-key investigation

Create a sample value:

```bash
docker exec se335-redis redis-cli SET lab:large "example"
docker exec se335-redis redis-cli MEMORY USAGE lab:large
```

Then examine the difference between key count and memory consumed.

Use controlled scans rather than broad production `KEYS *` operations.

### Acceptance criteria

You can describe the different memory measurements and avoid treating fragmentation ratio alone as a diagnosis.

---

# Lab 7 — Latency and Slow Log

## Objective

Understand what Redis's latency tools measure.

Enable a low threshold on the disposable instance.

```bash
docker exec se335-redis redis-cli CONFIG SET latency-monitor-threshold 1
docker exec se335-redis redis-cli CONFIG SET slowlog-log-slower-than 1000
```

The Slow Log threshold is measured in microseconds.

The latency monitor threshold is measured in milliseconds.

Inspect:

```bash
docker exec se335-redis redis-cli SLOWLOG GET 10
docker exec se335-redis redis-cli LATENCY LATEST
docker exec se335-redis redis-cli LATENCY DOCTOR
docker exec se335-redis redis-cli INFO commandstats
docker exec se335-redis redis-cli INFO latencystats
```

The laboratory may not generate any sufficiently slow commands.

That is not a failure.

Do not intentionally execute massive blocking commands merely to manufacture a Slow Log entry.

### Questions

What does the Slow Log exclude?

What does a latency-monitor event represent?

Why must application round-trip latency be measured separately?

Why would Redis processing a large value create latency even if the underlying lookup is efficient?

### Cleanup

Restore diagnostic thresholds:

```bash
docker exec se335-redis redis-cli CONFIG SET latency-monitor-threshold 0
docker exec se335-redis redis-cli CONFIG SET slowlog-log-slower-than 10000
```

The Slow Log threshold is now ten milliseconds, a conventional diagnostic value rather than a universal production recommendation.

---

# Lab 8 — REDIS-01 Incident Report

## Starting symptom

Redis reports approximately 99% hits.

PostgreSQL or MongoDB is overloaded.

The application experiences high API latency.

The team proposes doubling Redis memory.

### Your investigation

Use the evidence from the earlier experiments.

Prepare a report containing:

**Observed symptoms:** What happened to API latency, database workload, and Redis metrics?

**Hit-ratio analysis:** Which workload dominates the global hit counter?

**Cache miss analysis:** Which operations miss, and what backend work do they trigger?

**Bypass analysis:** Which operations never consult Redis?

**TTL and eviction:** Are expensive values disappearing because of expiration, eviction, or invalidation?

**Concurrency:** Do multiple misses trigger duplicate backend loads?

**Memory:** Is the instance actually under memory pressure?

**Recommendation:** Which change would most directly reduce unnecessary backend work?

**Verification:** How would you know the correction worked?

### Interviewer challenge

Your interviewer says:

"Redis is below its memory limit and reports 99% hits. Surely it isn't the problem."

Explain why those measurements do not establish that the cache protects the expensive workload.

Then defend a targeted correction.

---

# STOP — End of Independent Lab

Do not read the following notes until you've attempted the investigations.

The goal is to diagnose the system, not memorize a proposed configuration.

---

# Lab Diagnostic Notes

## The Hit-Ratio Incident

The global hit ratio is dominated by a frequently accessed configuration key.

Expensive report misses and bypass requests still generate backend work.

Increasing memory won't change the simulation because memory pressure isn't responsible for those misses.

The improvement is to instrument cache behavior by workload and reduce unnecessary expensive backend loads.

## The Stampede

The naive implementation allows several concurrent requests to observe the same missing key before any loader writes the result.

Each can begin its own database operation.

Process-local single-flight coalesces those loads.

The double-check inside the lock prevents later waiting requests from loading again after the first request populates the cache.

This implementation coordinates only one process.

## Eviction and Expiration

The TTL experiment demonstrates time-driven expiration.

The memory-pressure experiment demonstrates eviction under an allkeys policy.

Both can cause subsequent misses, but they have different causes and remedies.

## Noeviction

Redis can remain reachable while memory-growing writes fail.

An application that handles those failures poorly can shift more work onto the authoritative database.

A healthy `PING` response doesn't prove the cache is functioning as intended.

## Memory Measurements

`used_memory`, RSS, allocator fragmentation, and configured maxmemory describe different aspects of memory usage.

The configured dataset threshold does not guarantee a hard process-memory ceiling.

## Latency

Slow Log measures command execution time.

Latency monitoring records configured server-side latency events.

Application-observed latency also includes network and client-side work.

No single Redis metric describes all of them.

## REDIS-01 — Expected Judgment

A strong diagnosis identifies which business operations produce expensive cache misses, whether Redis memory pressure is actually involved, and whether concurrent requests multiply backend work.

The correction might involve workload-specific metrics, better TTLs, single-flight, bounded regeneration, or fixing bypass paths.

The final success criterion is reduced expensive database work while preserving correct cache freshness and isolation—not merely an improved global hit ratio.

---

# Further Reading

1. **Redis — Key Eviction**  
   https://redis.io/docs/latest/develop/reference/eviction/

2. **Redis — INFO**  
   https://redis.io/docs/latest/commands/info/

3. **Redis — MEMORY STATS**  
   https://redis.io/docs/latest/commands/memory-stats/

4. **Redis — MEMORY USAGE**  
   https://redis.io/docs/latest/commands/memory-usage/

5. **Redis — TTL**  
   https://redis.io/docs/latest/commands/ttl/

6. **Redis — SCAN**  
   https://redis.io/docs/latest/commands/scan/

7. **Redis — Slow Log**  
   https://redis.io/docs/latest/commands/slowlog/

8. **Redis — Latency Monitoring**  
   https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency-monitor/

9. **Redis — Diagnosing Latency Issues**  
   https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/

10. **Redis — Pipelining**  
    https://redis.io/docs/latest/develop/using-commands/pipelining/

11. **Redis — SET**  
    https://redis.io/docs/latest/commands/set/

12. **Redis — Transactions**  
    https://redis.io/docs/latest/develop/using-commands/transactions/

Cross-reference SE320-L02 for cache-aside, invalidation, and stampede fundamentals; `production-cases/REDIS-01.md` for the corresponding incident; and SE335-L03 for the cross-service asynchronous-system studio.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE335-L01 — REDIS PRODUCTION FORENSICS
================================================

CORE PRINCIPLE
--------------
A high cache hit ratio does not prove
the expensive backend workload is protected.

HIT RATIO
---------
keyspace_hits /
(keyspace_hits + keyspace_misses)

Global Redis lookup statistic.
Not the same as:
- HTTP cache hit rate
- backend calls avoided
- database CPU saved
- latency improvement

Compare deltas over the same interval.

BETTER METRICS
--------------
Per endpoint / key family:
- cache attempts
- hits and misses
- bypasses
- backend loads
- concurrent loads per key
- backend cost
- cache latency
- DB latency

EXPIRATION VS EVICTION
----------------------
Expiration:
  TTL reached

Eviction:
  maxmemory pressure + policy

INFO stats:
  expired_keys
  evicted_keys
  keyspace_hits
  keyspace_misses

TTL
---
Positive: remaining seconds
-1: key exists, no expiration
-2: key absent

TTL jitter:
  spread expiration bursts
  respect max freshness

EVICTION POLICIES
-----------------
noeviction:
  reject memory-growing writes

allkeys-lru:
  approximate recency over all keys

allkeys-lfu:
  approximate frequency over all keys

volatile-lru:
  only keys with expiry eligible

volatile-ttl:
  prefer shorter remaining TTL

Do not mix disposable cache state
with keys requiring durable retention
under an unrestricted eviction policy.

MEMORY
------
used_memory:
  Redis allocator allocation

used_memory_rss:
  resident process memory

maxmemory:
  eviction threshold, not total RSS cap

mem_fragmentation_ratio:
  interpret with absolute bytes

mem_not_counted_for_evict:
  some memory outside eviction accounting

MEMORY STATS:
  broader memory breakdown

HOT KEYS
--------
Popular key can:
- dominate hit statistics
- consume network throughput
- overload one shard
- create large repeated transfers

Hot != large.

KEY INSPECTION
--------------
Avoid broad KEYS * in production.

Use bounded SCAN:
  incremental cursor traversal
  COUNT is a hint
  duplicates possible

MEMORY USAGE:
  inspect individual key memory

LATENCY
-------
Slow Log:
  server command execution time
  excludes network round trips

LATENCY LATEST / DOCTOR:
  configured server events

INFO commandstats:
  cumulative command work

INFO latencystats:
  command execution percentiles

End-to-end client latency must
be measured separately.

STAMPEDE
--------
Many concurrent misses
can trigger duplicate DB loads.

Local single-flight:
  one loader per key per process

Distributed coordination:
  lease / ownership / careful release

TTL jitter:
  spread predictable expiry bursts

Stale-while-revalidate:
  bounded staleness where safe

CACHE FAILURE
-------------
Redis unavailable or rejecting writes
may shift traffic to database.

Bound fallback concurrency.
Consider degraded behavior.

Cache outage can become DB outage.

NEGATIVE CACHING
----------------
Confirmed absence:
  may cache briefly

Timeout/transient error:
  not equivalent to absence

Tenant-specific authorization:
  scoped key required

KEY DESIGN
----------
Include identity dimensions:
tenant, entity, dates, occupancy,
currency, version where relevant.

Too few dimensions:
  incorrect shared values

Too many dimensions:
  cardinality explosion and poor reuse

MAXMEMORY TRAP
--------------
Increasing maxmemory may help
an undersized working set.

It does not fix:
- short TTLs
- bypass paths
- unbounded key cardinality
- stampedes
- expensive misses
- incorrect keys

PRODUCTION INVESTIGATION
------------------------
1. Identify expensive backend operations.
2. Capture cache hit/miss deltas.
3. Segment by endpoint/key family.
4. Find bypasses.
5. Inspect TTL and eviction.
6. Check same-key concurrent loads.
7. Investigate memory and value sizes.
8. Separate Redis execution from RTT.
9. Form causal hypothesis.
10. Verify reduced backend work.

RED FLAGS
---------
"Redis has 99% hits, so it's fine."
"Just double maxmemory."
"TTL expiration and eviction are same."
"PING means cache works."
"Empty SLOWLOG means no Redis latency."
"KEYS * is safe for diagnostics."
"Noeviction makes cache durable."
"Single-flight works across all replicas."
"Cache a timeout as not-found."
"A Redis lock makes payments exactly-once."

MENTAL MODEL
------------
Protect the expensive workload.

Track:
Which keys?
Which misses?
Which backend loads?
Which resource pressure?
Which failure behavior?

NEXT
----
SE335-L02
RabbitMQ and Worker Failure Forensics
```
