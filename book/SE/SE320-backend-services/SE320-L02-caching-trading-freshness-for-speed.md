---
id: SE320-L02
course: SE320
title: "Caching: Trading Freshness for Speed"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S05]
prev: SE320-L01
next: SE320-L03
---



<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE335-L01
Preserve cache concepts (invalidation, stampedes, TTLs, keys) here.
When SE335 exists, cross-reference Redis production forensics and REDIS-01.
Do not turn this lecture into a Redis ops lab.
-->










# SE320 — Backend Services and Asynchronous Processing

## Lecture 02: Caching: Trading Freshness for Speed

*How to make an application dramatically faster by deliberately introducing copies of reality—and why those copies eventually disagree.*

---

# 1. The Hotel Room That Was Available and Unavailable at the Same Time

Your hotel-booking platform is doing rather well. Thousands of customers are searching for accommodation, examining hotel descriptions, checking room availability, and comparing prices.

The application is healthy, but PostgreSQL is working harder than necessary. A particularly popular hotel in Copenhagen receives hundreds of nearly identical search requests every minute, repeatedly asking for the same room categories, descriptions, amenities, and pricing summaries.

Some queries take 40 milliseconds. Others take 80. Individually, that's perfectly acceptable, but collectively they're consuming database connections, memory, CPU time, and network capacity.

So you introduce Redis.

The backend now checks Redis before querying PostgreSQL. When the result is cached, the application returns it in a few milliseconds rather than repeating the database operation.

Your average response latency falls dramatically. PostgreSQL has fewer queries to execute, connection-pool pressure decreases, and the platform handles more traffic without additional database hardware.

A rare moment when engineering appears to have worked exactly as advertised.

Then, on a busy Saturday afternoon, something peculiar happens.

A customer books the last available Deluxe room at Hotel Copenhagen. The reservation is committed successfully, and PostgreSQL correctly records that the room category is sold out.

Thirty seconds later, another customer searches for the same hotel.

Redis responds:

```json
{
  "hotelId": 482,
  "roomType": "deluxe",
  "availableRooms": 1,
  "nightlyPrice": 189
}
```

The frontend displays the room as available.

A third customer performs the same search, but their request happens to miss the cache and reaches PostgreSQL. That customer sees zero rooms available.

Two users are looking at the same hotel, for the same dates, through the same application, at almost the same moment. One sees an available room; the other sees a sold-out hotel.

Neither response was necessarily produced by broken infrastructure.

PostgreSQL returned its current state. Redis returned the information it had previously been given.

The problem is that we now have **two representations of the same business information, maintained through different mechanisms and updated at different times**.

This is the fundamental complication introduced by caching.

We have made reads faster by introducing another copy of data, but that copy can become stale. Now we must decide when staleness is acceptable, how information is refreshed, and which operations must bypass the cache entirely.

And there's an even more surprising possibility: the cache can resurrect old data *after* we've explicitly invalidated it.

We'll get to that.

---

# 2. Why Caching Works in the First Place

Consider how people actually use software.

A hotel platform may contain 200,000 properties, but customers don't distribute their attention evenly across all of them. Popular destinations and prominent hotels receive disproportionately many requests, while thousands of other properties receive little traffic.

Similarly, an e-commerce platform may contain millions of products, but a small fraction generates much of the browsing activity. A social network might have billions of posts, yet certain popular posts are read millions of times within hours.

This unevenness creates an opportunity.

If the same information is requested repeatedly, why reconstruct it from the underlying database on every request?

We encountered the underlying principle in the computer science foundations courses (CS110, CS220, CS320) when studying memory hierarchies and locality.

**Temporal locality** means recently accessed information is likely to be accessed again. **Spatial locality** means information near previously accessed information may also be useful.

CPU caches exploit these patterns to avoid repeatedly accessing slower memory. Operating systems use page caches to avoid unnecessary storage reads, and databases maintain buffer pools to reuse data pages already loaded into memory.

Application caching applies related principles at a different level.

Instead of caching raw memory or disk pages, we may cache meaningful application results:

```text
hotel:482:description
hotel:482:room-types
hotel:482:availability:2026-11-14
customer:10842:profile
pricing:hotel-482:2026-11-14
```

These represent information that would otherwise require database queries, calculations, or external API calls.

### The economics of a cache hit

Imagine an operation with the following illustrative costs:

| Operation | Latency |
|---|---:|
| Redis lookup | 2 ms |
| PostgreSQL query | 50 ms |
| Expensive external API | 300 ms |

Suppose 90% of requests find the result in Redis, and the remaining 10% must retrieve it from PostgreSQL.

Ignoring other application overhead, expected access time becomes:

\[
0.9(2) + 0.1(2 + 50) = 7\text{ ms}
\]

Compare that with approximately 50 milliseconds without caching.

That's a substantial improvement.

The benefit becomes even more interesting when we consider database load. At 1,000 requests per second, a 90% cache hit rate reduces database queries for this operation from approximately 1,000 per second to 100 per second.

Of course, those remaining queries don't necessarily arrive evenly. A sudden burst of cache misses can still overwhelm the database, and average latency doesn't tell us what happens to the slowest requests.

Nevertheless, caching can provide three benefits simultaneously: reduced latency, reduced work in the underlying system, and greater capacity for repeated reads.

Notice that the greatest benefit often comes not from Redis being extraordinarily fast, but from **avoiding work that didn't need to happen again**.

---

# 3. Where Should the Cache Live?

We've already encountered caching in the web engineering courses (CS230, SE240, SE310): browsers, CDNs, HTTP directives, and static asset delivery. Backend systems introduce additional caching locations, each with different sharing and consistency properties.

Consider this architecture:

```text
                       CLIENT
                         |
                         v
                    CDN / EDGE
                         |
                         v
                    API GATEWAY
                         |
                         v
              NODE.JS APPLICATIONS
                 |             |
                 v             v
           Local Cache    Shared Redis
                 |             |
                 +------+------+
                        |
                        v
                    PostgreSQL
```

These aren't necessarily all active on one request. The diagram illustrates possible storage layers.

### In-process memory

A Node.js application can cache data using a simple `Map`, a bounded LRU implementation, or another local structure.

```typescript
const hotelCache = new Map<string, HotelSummary>();
```

Access can be extremely fast because no network call is required. But the cache exists only within that particular process.

Suppose your service has six application instances behind a load balancer. Each instance maintains its own cache, so updating or invalidating one instance doesn't automatically update the others.

Local caches are attractive for small, frequently accessed, relatively stable information. They're less convenient when strong coordination across instances is required.

And an unbounded `Map` can become a memory leak disguised as a performance optimization.

### Shared Redis cache

Redis provides a shared in-memory data store that multiple application instances can access.

```text
Node Instance A ────┐
                    |
Node Instance B ────+──── Redis
                    |
Node Instance C ────┘
```

Now all three instances can read the same cached object.

This removes much of the inconsistency caused by independently populated local caches, but it doesn't automatically solve consistency between Redis and PostgreSQL.

It also introduces network communication and another service that may become unavailable.

### CDN and HTTP caches

These are excellent for public or appropriately shareable resources, especially static content and responses whose freshness requirements can be expressed through HTTP caching rules.

They aren't automatically suitable for authenticated, tenant-specific business data.

We won't revisit the detailed HTTP cache directives from the web engineering courses (CS230, SE240, SE310). For this course, our attention stays on the backend's coordination of application state.

A practical recommendation: **start by identifying which repeated work is actually expensive, then choose the smallest caching layer that solves that problem**.

Adding Redis to a system with no meaningful repeated-read bottleneck is an excellent way to create another monthly infrastructure bill.

---

# 4. Cache-Aside: The Simplest Useful Pattern

The most common application-level caching pattern is called **cache-aside**, also known as lazy loading.

The application treats the database as its authoritative source and uses the cache opportunistically.

The read path looks like this:

```text
             GET HOTEL DETAILS
                     |
                     v
                 Redis GET
                     |
              +------+------+
              |             |
           CACHE HIT     CACHE MISS
              |             |
              v             v
         Return data    Query database
                            |
                            v
                       Cache result
                            |
                            v
                       Return data
```

In TypeScript, using the Node Redis client:

```typescript
async function getHotelSummary(
  hotelId: number
): Promise<HotelSummary | null> {
  const key = `hotel:${hotelId}:summary`;

  const cached = await redis.get(key);

  if (cached !== null) {
    return JSON.parse(cached);
  }

  const hotel = await hotelRepository.findSummary(hotelId);

  if (hotel !== null) {
    await redis.set(key, JSON.stringify(hotel), {
      EX: 300
    });
  }

  return hotel;
}
```

The first request misses Redis, fetches from PostgreSQL, and stores the result for up to five minutes.

Subsequent requests can reuse it.

The pattern has several attractive properties. It caches only information that is actually requested, doesn't require preloading every database record, and allows the application to retrieve data from PostgreSQL when a cached entry is missing.

But the implementation above hides several decisions.

What if Redis is unavailable? What if PostgreSQL returns no hotel? What if the hotel changes during those five minutes? And what happens if a thousand requests encounter the same cache miss simultaneously?

Let's tackle the consistency problem first.

---

# 5. Cache Invalidation: The Apparently Simple Solution

Suppose a hotel changes its name from *Baltic Grand Hotel* to *Baltic Grand Copenhagen*.

PostgreSQL is updated successfully.

Redis still contains the old name.

We have several possible strategies.

### Expiration through TTL

We could rely on the cached object expiring naturally.

```redis
SET hotel:482:summary "{...}" EX 300
```

The `EX 300` option gives the key a time-to-live of 300 seconds.

Redis makes expired keys unavailable to ordinary reads and removes them through passive and active expiration mechanisms.

This establishes a useful freshness mechanism: an uninterrupted cached entry cannot remain readable indefinitely once its TTL expires.

However, it isn't a universal guarantee that business data is at most five minutes stale. A slow loader might publish an old snapshot after a newer update, and repeated re-population races can extend the age of incorrect information.

TTL bounds the lifetime of a particular cache entry, not automatically the age of the underlying facts.

### Explicit invalidation

A stronger common approach is to delete the cache entry after changing the authoritative data.

```typescript
await hotelRepository.rename(hotelId, newName);

await redis.del(`hotel:${hotelId}:summary`);
```

The next read misses Redis and loads the new value from PostgreSQL.

This seems excellent.

But let's inspect the order of operations.

Why update PostgreSQL first and invalidate Redis afterward?

If we invalidate first, another request could immediately miss the cache, retrieve the old database value before the update commits, and populate Redis with that old value.

Then our database update completes, leaving Redis stale.

Updating first and invalidating second usually reduces this particular problem.

Unfortunately, it doesn't eliminate every race.

### The delayed-reader problem

Consider three participants:

- Reader A requests the hotel summary.
- Writer B renames the hotel.
- Redis contains no cached summary initially.

The following sequence is possible:

```text
TIME     READER A               WRITER B

T1       Redis miss

T2       Reads old hotel name
         from PostgreSQL

T3                              Updates hotel name
                                 in PostgreSQL

T4                              Commits

T5                              Deletes Redis key

T6       Writes OLD hotel
         name into Redis

T7       Another request reads
         OLD value from Redis
```

At T5, Writer B did exactly what our invalidation strategy required.

But Reader A had already retrieved the old value and hadn't yet written it to Redis.

At T6, that delayed read repopulates the cache with obsolete data.

**An invalidation does not automatically prevent an earlier read from publishing stale information afterward.**

This is one of those bugs that can survive months of testing because the timing window is usually tiny.

Under high concurrency, slow database queries, or network delays, the window becomes more realistic.

### How do serious systems address it?

The right solution depends on the freshness guarantee required.

For ordinary hotel descriptions, the simplest acceptable answer may be a short TTL plus invalidation, accepting rare stale reads.

For data requiring stronger coordination, approaches include versioned cache keys, generation identifiers, compare-and-set publication, and protocols in which cache fills verify that the version they loaded is still current.

For example, a cache entry might contain:

```json
{
  "version": 18,
  "hotelName": "Baltic Grand Copenhagen"
}
```

The cache population process can be designed to avoid replacing a newer version with an older version.

But checking the version and writing the cache value must be appropriately coordinated; a non-atomic check followed by a separate write can itself race.

And database commits and Redis operations still don't share a transaction.

If you require immediate, strict correctness following a committed database update, the simplest robust architecture is often to perform the authoritative operation against the database rather than claiming an ordinary cache-aside scheme provides strong consistency.

---

# 6. The Most Important Boundary: Search Results Are Not Inventory Commitments

Let's return to hotel availability.

Customers frequently request availability summaries, so caching them seems attractive.

But room inventory is a business-critical resource.

What happens if a customer sees one available room in Redis, clicks Book, and another customer has already taken it?

The system must be able to reject the booking.

That's not necessarily a failure of architecture.

A search result describes availability at some moment. A confirmed reservation establishes a business commitment.

Those are different kinds of promises.

Consider:

```text
SEARCH REQUEST
      |
      v
Read cached availability
      |
      v
Display "1 room remaining"


BOOKING REQUEST
      |
      v
Authoritative inventory allocation
      |
      v
PostgreSQL transaction
      |
      +-- Success -> Reservation confirmed
      |
      +-- Failure -> Room no longer available
```

The search layer may tolerate a short period of stale information, provided the interface and business rules acknowledge that availability can change.

The booking operation cannot rely on cached availability as proof that inventory remains.

It must enforce the actual inventory invariant using the transactional mechanisms from CS330-L03.

Similarly, a cached price can be useful for preliminary search results, but the final purchase must operate against an authoritative quote or valid price commitment.

This distinction generalizes to many systems.

An e-commerce catalogue may display approximate stock levels while order placement performs authoritative allocation. A ticket platform may show seats as available until a transactional hold is secured.

**A cache is appropriate for information that may be temporarily inaccurate. It is not automatically appropriate as the authority for an operation that must remain correct.**

The practical engineering question is not simply whether data can be cached.

It's what the system promises when that cached data is used.

---

# 7. Three Write Strategies, Three Different Failure Models

Cache-aside is one way to coordinate reads and writes. Two other patterns are worth understanding because they appear frequently in system-design discussions.

## Write-through

In a write-through design, writes update the authoritative store and the cache as part of the write path.

```text
Application Write
       |
       v
Update PostgreSQL
       |
       v
Update Redis
       |
       v
Return
```

This can keep the cache warm after successful updates, avoiding the cache miss caused by invalidation.

But PostgreSQL and Redis are independent systems.

What happens if the database update succeeds but the Redis update fails?

Or if two concurrent writers update the same database record and their cache writes arrive in the opposite order?

A naive write-through implementation still has consistency problems.

The term describes an update strategy, not a distributed atomicity guarantee.

## Write-behind

In write-behind caching, the application first records data in the cache and persists it to the database asynchronously.

```text
Application Write
       |
       v
Write Cache
       |
       v
Return Success
       |
       v
Persist to Database Later
```

This can reduce perceived write latency and combine frequent updates before persistence.

But it introduces a potentially serious durability problem.

If the cache acknowledges a write and then loses the data before the database receives it, the acknowledged operation can disappear.

Write-behind can be reasonable for workloads that tolerate loss or implement durable recovery mechanisms. It's much harder to justify for confirmed hotel reservations, financial transactions, or customer payments.

## Cache-aside with invalidation

The application writes to PostgreSQL, invalidates relevant cached data, and allows later reads to repopulate the cache.

This is often my default recommendation for ordinary business applications because the database remains clearly authoritative and cache entries are disposable.

Still, we must explicitly accept its consistency characteristics and failure windows.

| Strategy | Main benefit | Main difficulty |
|---|---|---|
| Cache-aside | Simple, loads data on demand | Stale entries and cache misses |
| Write-through | Keeps frequently updated cache entries warm | Coordinating two writes |
| Write-behind | Lower immediate write latency | Durability and recovery |

For a typical Node.js/PostgreSQL SaaS, I'd start with cache-aside for read-heavy, noncritical views. More elaborate strategies should solve a demonstrated requirement rather than satisfy an architectural aesthetic.

---

# 8. The Cache Stampede: When Faster Infrastructure Causes an Outage

Our hotel platform has a particularly popular search result: Copenhagen hotels for New Year's Eve.

The result is expensive to calculate. It joins pricing rules, property information, room categories, and availability summaries.

Redis caches the result for sixty seconds.

Everything works beautifully until the key expires.

At the exact moment it disappears, 600 concurrent requests arrive.

They all execute:

```typescript
const cached = await redis.get(key);
```

They all receive `null`.

And they all begin reconstructing the same expensive database result.

```text
                  Popular cache key expires
                            |
          +-----------------+-----------------+
          |                 |                 |
       Request A         Request B         Request C
          |                 |                 |
       Cache miss        Cache miss        Cache miss
          |                 |                 |
          +-----------------+-----------------+
                            |
                            v
                   Massive database load
```

Instead of 600 requests sharing one cached result, we may execute hundreds of expensive queries simultaneously.

This is a **cache stampede**, sometimes called a thundering-herd or dogpile problem.

And it illustrates an important operational irony: the cache can concentrate work into sudden bursts even while reducing average database load.

### Single-flight within one process

A simple mitigation is to ensure that concurrent requests for the same key within one Node.js process share a single pending computation.

```typescript
const inFlight = new Map<string, Promise<HotelSummary>>();

async function loadOnce(
  key: string,
  loader: () => Promise<HotelSummary>
): Promise<HotelSummary> {
  const existing = inFlight.get(key);

  if (existing) return existing;

  const task = loader();
  inFlight.set(key, task);

  try {
    return await task;
  } finally {
    if (inFlight.get(key) === task) {
      inFlight.delete(key);
    }
  }
}
```

If ten requests arrive together, the first starts the operation and the others await the same promise.

But this only coordinates requests within one process.

If you have twenty Node.js instances, you could still initiate twenty database queries.

And this simple implementation assumes the calling code handles errors and cache publication appropriately.

### Distributed coordination

Redis can support a short-lived loading lease:

```redis
SET cache-load:hotel-482 <unique-token> NX PX 5000
```

`NX` means the key is set only if it doesn't exist.

`PX 5000` makes the lease expire after five seconds.

The successful caller attempts to load the data while other callers wait briefly, retry the cache, or use an acceptable stale result.

A proper implementation must release the lease only if it still owns it, account for lease expiration, and handle a loader that stalls.

Importantly, a loading lease is a performance-coordination mechanism, not proof that stale data can never be published.

If the loader continues after its lease expires, another loader may have started. Strong publication guarantees require additional coordination, such as version checks or fencing.

### TTL jitter

Another inexpensive technique is adding randomized variation to expiration times.

Instead of expiring every cached hotel summary exactly at five minutes, we might use:

```typescript
const ttlSeconds =
  270 + Math.floor(Math.random() * 61);
```

Now different keys expire between 270 and 330 seconds.

This reduces synchronized expiration across many keys, although it doesn't by itself stop a stampede on one exceptionally popular key.

### Stale-while-revalidate

Sometimes the best response to an expired cache entry is to continue serving slightly stale information while one background operation refreshes it.

This can be excellent for hotel descriptions, public rankings, or noncritical statistics.

But it requires a deliberate stale-serving window, refresh coordination, and a policy for what happens if refresh repeatedly fails.

For inventory allocations or financial commitments, serving stale state as authoritative would be inappropriate.

---

# 9. Redis Memory: Expiration Is Not Eviction

Developers sometimes treat Redis as though every cache entry is guaranteed to remain until its TTL expires.

That's not necessarily true.

Redis stores data in memory, and that memory is finite.

If configured with a maximum dataset memory limit, Redis can evict keys according to an eviction policy.

For example:

```text
maxmemory 1gb
maxmemory-policy allkeys-lru
```

When Redis needs to reclaim memory, it may remove entries before their TTL expires.

Several policies are available:

| Policy | Behavior |
|---|---|
| `allkeys-lru` | Preferentially evicts less recently used keys |
| `allkeys-lfu` | Preferentially evicts less frequently used keys |
| `volatile-ttl` | Evicts expiring keys with shorter remaining TTL |
| `allkeys-random` | Random eviction across keys |
| `noeviction` | Refuses certain memory-growing writes rather than evicting |

Redis uses approximate algorithms for LRU and LFU rather than maintaining perfect global rankings.

A key distinction:

**Expiration is a freshness/lifetime mechanism. Eviction is a memory-management mechanism.**

The TTL tells Redis when an entry is no longer valid for retrieval.

The eviction policy decides which entries may disappear because memory is constrained.

These mechanisms solve different problems.

### A particularly dangerous deployment choice

Imagine using the same Redis instance for two purposes:

1. Disposable cached hotel search results.
2. BullMQ jobs representing business work that must be processed.

You configure `allkeys-lru` because it works nicely for the cache.

Now Redis is permitted to evict keys from the queue's internal state as well.

That would be a serious architectural mistake.

Queue metadata and durable workflow state cannot be treated like disposable cache entries. Redis-backed queues such as BullMQ require appropriate persistence, memory policy, and operational configuration.

For important business processing, separating the cache and queue into appropriately configured Redis instances is often the safer design.

The same technology can serve different roles, but those roles demand different guarantees.

---

# 10. Cache Keys Are Part of the Data Model

A cache entry isn't simply a value.

It's a mapping from a key to a representation of some underlying information.

Consider:

```text
hotel:482:availability
```

What does this actually represent?

Availability on which dates?

For how many guests?

In which currency?

Under which rate plan?

For which distribution channel?

A search result might depend on:

```text
hotelId
checkIn
checkOut
guestCount
currency
ratePlan
salesChannel
```

If two requests differ in any dimension that materially changes the result, their cached representation may also need to differ.

For instance:

```text
availability:v2:482:2026-11-12:2026-11-15:2:EUR:public
```

The `v2` prefix is a schema-version marker. It allows new application code to use a different cache representation without accidentally interpreting older serialized entries.

But a complete key containing every possible query parameter can create another problem: **cache-key explosion**.

If customers can select arbitrary combinations of dates, occupancy, currencies, filters, and sort orders, the number of distinct cache entries may become enormous.

Many entries may be requested only once.

A cache full of low-reuse entries offers little benefit.

In some systems, it's better to cache reusable components—hotel descriptions, room-type details, pricing rules—and assemble personalized results from those components.

### Tenant isolation and security

Now imagine a multi-tenant SaaS.

Hotel A and Hotel B each have a reservation with ID `10842` in separate identifier namespaces.

If the cache key is simply:

```text
reservation:10842
```

one tenant might receive another tenant's reservation.

That's not merely stale data. It's a security failure.

Cache keys and authorization boundaries must agree.

Sensitive information also needs suitable handling regarding access controls, logging, encryption, retention, and cache invalidation.

And even when a result is cached, the application must still enforce the relevant authorization rules.

**A cache hit must never become a shortcut around permission checks.**

---

# 11. Negative Caching: Remembering That Nothing Exists

So far, we've cached successful database results.

But what if the database returns nothing?

Imagine an API endpoint:

```http
GET /api/products/does-not-exist
```

A request arrives. PostgreSQL finds no matching product.

One second later, another request asks for the same nonexistent product.

Then another.

Perhaps a crawler is probing millions of identifiers, or a client has a bug that repeatedly requests an obsolete resource.

Without negative caching, every request reaches the database.

One solution is to cache the *absence* of the resource for a short period.

```typescript
const NOT_FOUND = "__NOT_FOUND__";

async function getProduct(id: string) {
  const key = `product:${id}`;
  const cached = await redis.get(key);

  if (cached === NOT_FOUND) return null;
  if (cached !== null) return JSON.parse(cached);

  const product = await repository.findById(id);

  if (!product) {
    await redis.set(key, NOT_FOUND, { EX: 15 });
    return null;
  }

  await redis.set(key, JSON.stringify(product), {
    EX: 300
  });

  return product;
}
```

Now repeated requests for a missing product can avoid database work.

But negative caching has an interesting freshness problem.

What if the product is created five seconds later?

The cache may continue reporting that it doesn't exist until the negative entry is invalidated or expires.

This is why negative entries often receive shorter TTLs.

For rapidly changing resources, or identifiers that can be created immediately after a failed lookup, the invalidation policy deserves special attention.

And remember that `null` can represent different things: a missing cache entry, a cached missing resource, or a legitimate null-valued field.

The representation must distinguish these states explicitly.

---

# 12. The Architecture of a Sensible Production Cache

Let's combine what we've learned into a practical approach for a hotel SaaS.

Not every part of the system needs the same caching policy.

| Data | Suggested strategy | Correctness requirement |
|---|---|---|
| Hotel descriptions | Cache-aside, longer TTL | Modest staleness acceptable |
| Room amenities | Cache-aside with invalidation | Usually tolerant of brief staleness |
| Search availability | Short-lived cache or derived view | Revalidate during booking |
| Search price estimates | Carefully keyed, short-lived cache | Final quote must be authoritative |
| Confirmed reservation state | Database-first, selective caching | Authoritative checks for critical actions |
| Inventory allocation | Transactional database operation | Strong concurrency correctness |
| Analytical summaries | Cached/precomputed | Defined reporting freshness |
| Notification jobs | Durable queue/workflow state | Must not be treated as disposable cache |

The point isn't to prescribe exact TTL values. Those depend on how frequently the information changes, how expensive it is to reconstruct, and how much staleness the product can tolerate.

### Cache failure behavior

Suppose Redis becomes unavailable.

What should happen?

For a nonessential hotel-description cache, the service may fall back to PostgreSQL.

But the fallback must be bounded.

If every application instance suddenly sends all traffic to PostgreSQL, the database can become overloaded precisely when Redis fails.

You may need request concurrency limits, backpressure, bounded database access, and graceful degradation.

For an operation that relies on Redis as authoritative workflow state, falling back to PostgreSQL may not even be meaningful.

This is another reason to keep cache responsibilities separate from essential state-management responsibilities.

### Operational metrics

Cache hit rate is useful, but insufficient.

Suppose the hit rate rises from 90% to 99%. That sounds excellent.

But what if a small number of very expensive queries account for most remaining misses?

Or what if cached responses are fast while the misses become extremely slow?

Useful measurements include cache hit/miss rates, hit and miss latency distributions, Redis memory utilization, evictions, expiration rates, database query load, hot-key concentration, and refresh failures.

You should also track the business correctness of cached data where it matters.

For example, how often does search availability disagree with the final inventory-allocation decision?

That metric can reveal the customer-facing cost of stale information more clearly than Redis's hit rate alone.

A cache is successful when it improves the system's actual performance and cost without violating its agreed behavior—not when the Redis dashboard looks impressively green.

---

# 13. Practical Lab: Reproducing a Cache Invalidation Race

This experiment reproduces the stale-repopulation problem from Section 5.

You'll need Node.js and Redis. Start a disposable Redis instance, for example:

```bash
docker run --rm -p 6379:6379 redis:7
```

In another terminal:

```bash
npm init -y
npm install redis
```

Create `cache-race.mjs`:

```javascript
import { createClient } from "redis";

const redis = createClient();

redis.on("error", err => {
  console.error("Redis error:", err);
});

await redis.connect();

const key = "lab:hotel:482";
await redis.del(key);

// Simulated authoritative database state.
let database = {
  hotelId: 482,
  name: "Old Hotel Name"
};

// A gate lets us deliberately pause a reader.
let releaseReader;
const readerGate = new Promise(resolve => {
  releaseReader = resolve;
});

let signalRead;
const readStarted = new Promise(resolve => {
  signalRead = resolve;
});

async function delayedReader() {
  const cached = await redis.get(key);

  if (cached !== null) {
    return JSON.parse(cached);
  }

  // Simulate the database returning a snapshot.
  const snapshot = { ...database };

  console.log("Reader loaded:", snapshot.name);

  signalRead();

  // Pause before populating the cache.
  await readerGate;

  await redis.set(key, JSON.stringify(snapshot), {
    EX: 60
  });

  console.log("Reader populated cache");

  return snapshot;
}

async function writer() {
  database.name = "New Hotel Name";

  console.log("Database updated:", database.name);

  await redis.del(key);

  console.log("Writer invalidated cache");
}

try {
  const pendingRead = delayedReader();

  // Ensure reader has loaded the OLD value.
  await readStarted;

  // Writer commits and invalidates Redis.
  await writer();

  // Allow old reader to publish afterward.
  releaseReader();

  await pendingRead;

  const cached = JSON.parse(await redis.get(key));

  console.log("Database says:", database.name);
  console.log("Redis says:", cached.name);
} finally {
  await redis.del(key);
  await redis.quit();
}
```

Run:

```bash
node cache-race.mjs
```

The important output is:

```text
Reader loaded: Old Hotel Name
Database updated: New Hotel Name
Writer invalidated cache
Reader populated cache
Database says: New Hotel Name
Redis says: Old Hotel Name
```

We deliberately synchronized the operations to make the race reproducible.

A real production system wouldn't contain our artificial gate, of course. But network delays, database latency, and process scheduling can produce the same ordering.

### Investigation A — Does a shorter TTL solve it?

Change the Redis TTL from sixty seconds to five seconds.

The stale value will disappear sooner.

But the race still occurs.

TTL limits the lifetime of the stale entry rather than preventing its creation.

### Investigation B — Add local single-flight

Modify the read path so concurrent requests in the same Node.js process share one pending database operation.

This reduces redundant cache fills.

Does it prevent our original race?

No. The reader can still load an old snapshot while a writer commits a newer value.

Single-flight addresses duplicate work, not database/cache consistency.

### Investigation C — Design version-aware publication

Now imagine that every authoritative hotel update increments a version number.

A reader records the version associated with its database snapshot.

Before publishing, it must establish that the snapshot is still current.

A robust cross-process approach needs coordinated version state and an atomic publication condition. One possible design uses a Redis generation marker updated by the writer and a Redis script that only publishes the result if the generation still matches the reader's original value.

But this still requires careful handling of the interval between the PostgreSQL commit and the Redis generation update.

Think through these questions:

- What happens if PostgreSQL commits but Redis is unavailable?
- What if the reader checks the generation just before the writer changes it?
- Can the writer's invalidation and generation change be coordinated atomically within Redis?
- What guarantees survive a process crash?

You should notice that enforcing strict cache consistency is starting to resemble a distributed-systems problem.

That's because it is one.

The practical conclusion isn't that you should always build a complicated version protocol. It's that you should avoid promising stronger cache consistency than the architecture actually provides.

---

# 14. Engineering and Interview Challenges

### Question 1 — The cache that becomes stale after invalidation

A read request misses Redis and begins fetching a product from PostgreSQL. Another request updates the product and invalidates Redis. The first request finishes afterward and caches its older snapshot.

What happened? Would reducing TTL prevent the race?

### Question 2 — The midnight stampede

At midnight, thousands of popular cache keys expire simultaneously. Database CPU spikes, query latency increases, and the application starts timing out.

What caused the problem? Suggest three complementary mitigations and explain what each addresses.

### Question 3 — The dangerous Redis configuration

Your SaaS uses the same Redis instance for cached search results, BullMQ jobs, and business-critical rate-limit counters.

A colleague configures `allkeys-lru` eviction.

What risks does this introduce, and how would you restructure the system?

### Question 4 — The 99% hit rate

The team's dashboard proudly reports a 99% cache hit rate. Unfortunately, users still complain about slow search requests.

How can both observations be true? Which metrics would you investigate?

### Question 5 — Caching room inventory

A developer proposes storing remaining room counts in Redis and decrementing them with `DECR` during booking. PostgreSQL would receive updates asynchronously.

Is Redis capable of performing atomic decrements? Does that automatically make the entire reservation workflow correct?

### Question 6 — Cache keys and tenants

Two tenants use the same human-readable product identifier. Your cache stores products under `product:{id}`.

What could go wrong, and what should the cache-key design account for?

---

# 15. Solutions and Discussion

### 1. Stale repopulation after invalidation

The reader obtained an older database snapshot before the writer committed, then published it after the invalidation.

Deleting the cache key didn't coordinate with the already-running read.

A shorter TTL reduces how long the resulting stale entry survives but doesn't eliminate the race. Stronger prevention requires coordinated publication, version-aware mechanisms, or avoiding the cache for operations requiring strict current-state guarantees.

### 2. Synchronized cache misses overwhelm the database

The system experienced a cache stampede.

TTL jitter can spread different keys' expiration times and reduce synchronization. Single-flight or short-lived loading leases can reduce duplicate regeneration for individual keys. Stale-while-revalidate can continue serving acceptable old data while a bounded number of workers refresh it.

The system should also limit fallback concurrency so a cache outage doesn't simply become a database outage.

### 3. Disposable and durable state need different guarantees

LRU eviction can remove cache keys before their TTL expires, which is fine for reconstructible search results.

It is dangerous when Redis also contains queue state or correctness-critical counters whose disappearance changes business behavior.

I'd separate disposable caching from durable or semantically essential Redis workloads, using independent memory limits, eviction policies, persistence settings, and monitoring appropriate to each responsibility.

BullMQ in particular should not share an arbitrarily evicting cache environment.

### 4. Hit rate doesn't tell the entire performance story

The remaining 1% of misses may involve very expensive database queries, hot keys, or high-latency external dependencies.

The cache may also store mostly cheap results while costly endpoints remain uncached.

I'd investigate per-endpoint hit rates, cache-hit and cache-miss latency distributions, backend query counts, hot-key behavior, stampedes, and end-to-end request traces.

A global percentage can conceal the workload that actually matters.

### 5. Redis atomic operations aren't distributed transactions

Redis can execute individual commands such as `DECR` atomically.

But that doesn't automatically coordinate the resulting inventory change with a PostgreSQL reservation insert, payment state, or external supplier.

If Redis decrements successfully and PostgreSQL fails, the systems disagree. If Redis loses authoritative state before persistence, inventory information may be lost.

Redis can be the authoritative store for appropriately designed workloads, but making it authoritative requires deliberate durability, recovery, and cross-system coordination.

For a conventional PostgreSQL-backed reservation system, I would generally keep inventory allocation in the database transaction and treat Redis availability as advisory.

### 6. The cache must encode the relevant identity and scope

If different tenants share the same product identifier, `product:{id}` may collide.

The cache could return one tenant's data to another tenant, creating a serious security failure.

The key should include the trusted tenant scope when identifiers are tenant-local. It should also distinguish other relevant dimensions such as locale, currency, schema version, and authorization-dependent representation when those dimensions change the result.

And cached content must never bypass authorization.

---

# 16. The Mental Model to Keep

Caching is best understood as **maintaining a faster, potentially stale representation of information held elsewhere**.

When designing a cache, ask:

- **What work are we avoiding?** Identify the expensive repeated query, calculation, or remote operation.
- **What is authoritative?** Be explicit about which system makes final business decisions.
- **How stale may the result become?** Define acceptable freshness according to business consequences.
- **How is the entry refreshed or invalidated?** Account for expiration, writes, and concurrent cache population.
- **What happens on a miss or outage?** Prevent fallback traffic from overwhelming the underlying system.
- **What does maintaining the cache cost?** Consider memory, evictions, serialization, operational complexity, and consistency failures.

The governing principle is:

**Cache information according to its tolerance for staleness; enforce business commitments at the authoritative state boundary.**

An excellent cache makes repeated work disappear from the critical path. A poorly designed cache makes correctness disappear with it.

---

# Coming Next — SE320-L03: Queues, Workers, and Asynchronous Workflows

A reservation succeeds, and a BullMQ worker sends the confirmation email. Immediately afterward, the worker process crashes—before it acknowledges that the job has completed. Redis still considers the job unfinished, so another worker eventually executes it again.

The customer receives two emails, even though the queue is behaving exactly as designed.

In **SE320-L03**, we'll investigate why background jobs are often delivered more than once, what acknowledgments and retries actually guarantee, and how to build asynchronous workflows that survive crashes without duplicating business effects.

---


---

## Next Lecture — SE320-L03: Queues, Workers, and Asynchronous Workflows

Continue in **SE320 — Backend Services and Asynchronous Processing**.

## Further Reading

- **Redis — Cache-Aside Pattern:** https://redis.io/docs/latest/develop/use-cases/cache-aside/
- **Redis — Key Eviction Policies:** https://redis.io/docs/latest/develop/reference/eviction/
- **Redis — SET Command:** https://redis.io/docs/latest/commands/set/
- **Redis — EXPIRE Command:** https://redis.io/docs/latest/commands/expire/
- **Redis — Node.js Client:** https://redis.io/docs/latest/develop/clients/nodejs/
- **Redis — Cache Invalidation:** https://redis.io/glossary/cache-invalidation/


---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE320-L02  CACHING — INTERVIEW GLANCE CARD

CORE MODEL
  Faster copy of data held elsewhere → can be stale
  Two representations (Redis vs PostgreSQL) can disagree
  Cache ≠ authority for commitments (book / pay / allocate)

WHY IT WORKS
  Temporal + spatial locality; uneven request popularity
  Benefit often = avoid repeated work, not Redis magic
  Hit rate cuts DB load; stampedes still possible on miss bursts

WHERE TO CACHE
  In-process Map/LRU   fastest; per-instance; unbounded Map = leak
  Shared Redis         multi-instance share; still ≠ DB consistency
  CDN/HTTP             shareable public; not auto for tenant APIs
  Start: expensive repeated work → smallest layer that helps

CACHE-ASIDE (lazy)
  GET cache → hit return / miss DB → SET with TTL → return
  DB authoritative; cache opportunistic

INVALIDATION / FRESHNESS
  TTL (EX N): bounds entry lifetime ≠ “facts ≤ N old”
  Update DB then DEL usually better than invalidate-first
  Delayed-reader race: miss → load OLD → writer updates+DEL
                     → reader SETs OLD after invalidation
  Stronger: versioned keys / CAS / verify generation; or skip cache
  for strict current-state ops

WRITE STRATEGIES
  Cache-aside + invalidate  simple; stale + misses   [default SaaS]
  Write-through          warm cache; dual-write races
  Write-behind           low write latency; durability risk
  Term = update strategy, not distributed atomicity

SEARCH ≠ INVENTORY
  Cached availability OK for display if booking revalidates
  Authoritative allocation in transactional DB
  Cached price for browse; final quote authoritative

STAMPEDE / DOGPILE
  Popular key expires → many concurrent rebuilds → DB spike
  Mitigations: in-process single-flight; Redis NX lease;
               TTL jitter; stale-while-revalidate (noncritical)
  Lease = coordination, not proof against stale publish

REDIS MEMORY
  Expiration = freshness; eviction = memory (allkeys-lru etc.)
  NEVER share allkeys-lru Redis for cache + BullMQ durable jobs
  Separate instances/policies for disposable vs essential state

KEYS = DATA MODEL
  Encode all result dimensions (dates, guests, currency, channel…)
  Schema version prefix (v2:…); watch key explosion
  Tenant scope in key; cache hit NEVER bypasses authZ

NEGATIVE CACHING
  Cache absence briefly; shorter TTL; distinguish miss vs cached-null
  Create-after-negative → stale “not found” until expire/invalidate

OPS
  Redis down: bounded fallback (don't stampede DB)
  Metrics: hit/miss, latency dists, memory, evictions, hot keys,
           business disagreement rate (search vs book)
  Hit rate alone can hide expensive misses

SENIOR LINE: Cache by staleness tolerance; enforce commitments
             at the authoritative state boundary.
```

---

