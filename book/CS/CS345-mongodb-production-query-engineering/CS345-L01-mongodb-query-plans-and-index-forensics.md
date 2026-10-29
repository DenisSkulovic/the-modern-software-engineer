---
id: CS345-L01
course: CS345
title: "MongoDB Query Plans and Index Forensics"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: CS345-L02
---


# CS345 — MongoDB Production Query Engineering
## Lecture 01: MongoDB Query Plans and Index Forensics

*The API returns twenty documents. The database examines eighty thousand. Both things are true, and only one of them explains why production is slow.*

---

# Part I — Intuition

## 1. The Admin Page That Got Slower Without Getting Bigger

Imagine you're responsible for a SaaS platform whose administrative interface lists customer reservations.

An administrator can filter reservations by customer, hotel, status, and date. Each page displays twenty records.

The endpoint has existed for years.

Originally, the collection contained a few thousand documents. The response was nearly instantaneous.

Today, the collection contains millions.

The administrator opens the first page.

Sometimes it loads quickly. Other times it takes several seconds.

You inspect the API response.

Twenty documents.

The payload is small.

The backend performs no obviously expensive calculations.

You inspect the MongoDB query.

It filters by tenant and status, sorts by booking date, skips the appropriate number of documents, and returns twenty results.

The code appears reasonable.

A colleague proposes increasing the MongoDB cluster size.

Another suggests adding Redis caching.

A third suggests increasing the API timeout.

Those might become relevant under certain circumstances, but none establishes why the query is slow.

You run MongoDB's `explain("executionStats")`.

The results reveal that the query examined tens of thousands of documents before returning twenty.

Suddenly, the problem looks different.

The endpoint isn't slow because it returns too much information.

It's slow because of the work required to find that information.

**A query's output size tells you almost nothing about the amount of work performed to produce it.**

This is the central problem of MongoDB query forensics.

## 2. A Query Is a Request, Not an Algorithm

Suppose the API asks MongoDB for the twenty newest confirmed reservations belonging to Tenant Mercury.

The request describes three things.

First, the documents must belong to Mercury.

Second, their status must be confirmed.

Third, they must be ordered from newest to oldest.

MongoDB has several possible ways to produce that result.

It could scan the entire collection, check every document, identify the matching reservations, sort them, and return twenty.

It could use an index on tenant ID to locate Mercury's reservations, fetch those documents, check their statuses, sort the survivors, and return twenty.

Or it could use a compound index organizing reservations by tenant, status, and booking time.

With the right index, MongoDB may be able to navigate directly to Mercury's confirmed reservations in the required order.

Then it can stop after obtaining the first twenty.

The logical result is identical.

The physical work can be radically different.

### Visual anchor 1 — Three ways to answer one query

```text id="c5h9tm"
REQUEST:
Mercury's 20 newest confirmed bookings

PATH A — Collection scan
  Examine collection
  Filter tenant and status
  Sort matching documents
  Return 20

PATH B — Tenant index
  Find Mercury's documents
  Fetch and filter by status
  Sort remaining documents
  Return 20

PATH C — Compound index
  Seek Mercury + confirmed
  Walk booking-date order
  Fetch necessary documents
  Return 20
```

An index is not a universal accelerator.

It is an alternative organization of data.

Its value depends on whether that organization matches the query's access pattern.

## 3. The Three Numbers That Expose Wasted Work

MongoDB exposes execution statistics that help answer a basic question:

How much work was required to return the result?

Three measurements deserve particular attention.

**`nReturned`** reports how many documents the winning query execution returned.

**`totalKeysExamined`** reports how many index entries were examined.

**`totalDocsExamined`** reports how many documents were examined during execution.

Imagine a query reporting:

```text id="6qylz8"
nReturned:          20
totalKeysExamined:  85,000
totalDocsExamined:  60,000
```

These numbers are illustrative, not measurements from our laboratory.

The query returned twenty documents while examining a large amount of index and document data.

That is evidence of substantial work.

It doesn't yet tell us why the work happened.

Perhaps the index doesn't include the status field.

Perhaps the index provides the wrong ordering.

Perhaps the predicate is not selective.

Perhaps the query must examine many candidates to satisfy another condition.

But now we have a measurable problem.

### Visual anchor 2 — Examined versus returned

```text id="r42ry8"
85,000 index entries examined
              |
              v
60,000 documents examined
              |
              v
       Filters and sort
              |
              v
       20 documents returned
```

Be careful with the interpretation.

`totalKeysExamined` counts index-entry examinations, not necessarily distinct documents.

Multikey indexes can produce several entries associated with one document.

`totalDocsExamined` counts document examinations, including repeated examinations when they occur.

Neither number should automatically be interpreted as the number of unique business entities processed.

And a query with many examined keys is not necessarily inefficient if the business requirement genuinely requires scanning a large range.

The relevant comparison is between necessary and unnecessary work.

## 4. The Index Can Be Used and Still Be Wrong

Here's an important production trap.

You inspect an execution plan and find `IXSCAN`.

Excellent. The query uses an index.

Does that mean it's efficient?

No.

Imagine an index containing only tenant ID.

MongoDB can use it to locate Mercury's reservations.

But Mercury is a large tenant with eighty thousand reservations.

The query also requires confirmed status and descending booking time.

The tenant index doesn't organize records by those additional requirements.

MongoDB may still have to fetch many documents, filter them, and sort them.

The index was used correctly.

It simply wasn't sufficiently useful for this query.

A common beginner mistake is treating `IXSCAN` as success and `COLLSCAN` as failure.

A better engineer asks how much work the access path avoided.

**Index usage is evidence of a strategy, not evidence that the strategy is good.**

## 5. Compound Indexes Encode a Workload

Suppose we create a compound index with three leading fields:

Tenant ID, booking status, and booking timestamp.

Conceptually, MongoDB now has an ordered catalogue.

First, records are organized by tenant.

Within each tenant, by status.

Within each tenant-status group, by booking time.

The API can seek to Mercury's confirmed reservations and traverse them in descending booking order.

This is a close match for the query.

But reverse the field order and the index might be much less useful.

An index beginning with booking timestamp is organized primarily around time, not around a particular tenant.

It may need to traverse a much larger range to find Mercury's records.

This is why compound index field order matters.

The familiar guideline is **Equality, Sort, Range**, often abbreviated ESR.

Equality predicates generally belong first.

Fields needed for sorting often follow.

Range conditions can follow those, although highly selective ranges may justify placing range fields before sort fields instead.

The guideline is a starting point, not a replacement for testing actual plans.

### Visual anchor 3 — Compound-index ordering

```text id="yl15qy"
Index:
tenantId → status → bookedAt DESC

Mercury
  |
  ├── cancelled
  ├── confirmed
  |      |
  |      ├── newest
  |      ├── next newest
  |      └── older...
  |
  └── pending

Query seeks Mercury + confirmed,
then walks the required order.
```

## 6. A Covered Query Can Avoid Fetching Documents

Imagine the admin list needs only tenant ID, booking status, and booking timestamp.

All three values are available in the compound index.

MongoDB may be able to satisfy the query entirely from index entries without retrieving the original documents.

This is called a **covered query**.

A properly covered query can have `totalDocsExamined` equal to zero.

That is useful because fetching full documents can involve additional storage access and processing.

But coverage is conditional.

Every field required by the query and projection must be available from the index, including fields MongoDB needs internally.

MongoDB includes `_id` in results by default.

If `_id` isn't in the supporting index, you may need to exclude it explicitly to obtain a covered projection.

Certain query patterns, including predicates involving null values, complicate or prevent coverage.

And a covered query is not automatically the best query if the index becomes huge or expensive to maintain.

The benefit depends on the workload.

## 7. The Deep Page Problem Is Different

Now suppose the first page becomes fast after adding the compound index.

The administrator jumps to page four thousand.

Each page contains twenty reservations.

The query uses a skip of approximately eighty thousand documents.

Even with a useful index, MongoDB may need to advance through the preceding index entries before reaching the requested page.

The response still contains twenty documents.

But the amount of work grows with the offset.

This is a different problem from filtering with the wrong index.

A compound index can support the query's order beautifully while deep pagination remains expensive.

Later in CS345, we'll examine cursor pagination, materialized fields, computed sorting, and aggregation stages that can make this problem substantially worse.

For now, recognize that the shape of the request matters as much as the index.

### A tiny comprehension check

Two queries each return twenty documents.

Query A examines twenty-five index keys and twenty documents.

Query B examines eighty thousand index keys and twenty documents.

Which one is likely doing more index-scanning work?

Query B.

But can you conclude that B is necessarily eighty thousand divided by twenty times slower?

No.

Index-key examinations are not equivalent units of time, and workload, caching, storage access, and execution strategy also matter.

The statistics provide evidence about work, not a complete latency model.

That distinction is essential.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. Query Forensics Starts with the Actual Request

Before opening an execution plan, capture the real query shape.

Suppose the backend generates this operation:

```javascript id="j0gbks"
db.bookings.find({
  tenantId: "mercury",
  status: "confirmed"
})
.sort({
  bookedAt: -1,
  _id: -1
})
.limit(20);
```

It filters by two equality conditions, sorts newest first, and returns twenty documents.

The `_id` tie-breaker makes the ordering deterministic when multiple bookings have identical timestamps.

In production, however, the request may contain additional fields.

Perhaps the selected hotel restricts results.

Perhaps the customer supplies a date range.

Perhaps the query uses `$in` across several statuses.

Perhaps a permission filter is applied.

Perhaps the query requests a specific projection.

These details can change the ideal index.

An optimization based on a simplified query may improve the simplified example while doing little for the actual endpoint.

### 8.1 Capture query shape and parameters

The query shape describes the structure of the operation: its predicates, sorting, projection, and related characteristics.

The specific parameter values matter too.

A tenant with eighty thousand documents may need a different access strategy from a tenant with fifty documents.

A query matching a common status behaves differently from one matching a rare status.

When diagnosing production behavior, capture both the operation's shape and representative values.

Do not copy only the query method name from the application code.

## 9. Reading `explain("executionStats")`

MongoDB's `explain()` can provide several levels of information.

The `queryPlanner` mode describes the selected query plan and relevant planning information.

The `executionStats` mode executes the winning plan and reports its execution statistics.

The `allPlansExecution` mode includes additional partial trial information for candidate plans considered during plan selection.

For most initial investigations, `executionStats` is a useful starting point.

The command can be invoked from a `find` cursor:

```javascript id="5nzhcs"
db.bookings.find({
  tenantId: "mercury",
  status: "confirmed"
})
.sort({ bookedAt: -1, _id: -1 })
.limit(20)
.explain("executionStats");
```

The result can be large.

Modern MongoDB uses different execution engines, including the classic query engine and the slot-based execution engine.

The structure of explain output varies by version and engine.

Do not build your entire debugging understanding around one hardcoded JSON path.

Focus on the important measurements and the logical execution stages.

### 9.1 The top-level statistics

The principal execution statistics include:

`nReturned`: documents returned by the winning plan.

`totalKeysExamined`: index entries examined.

`totalDocsExamined`: document examinations performed.

`executionTimeMillis`: reported execution time for the explain operation.

These values provide the first approximation of work.

### 9.2 Explain timing is not ordinary request latency

This deserves emphasis.

MongoDB's explain operation ignores the existing query-plan cache and performs planning for the operation being explained.

It also prevents caching the selected plan.

Therefore, its execution time may differ from normal steady-state execution, where a cached plan may be reused.

The timing also doesn't include all application network and serialization overhead.

For production latency investigation, combine explain evidence with application measurements, MongoDB profiler information, slow-query logs, or appropriate monitoring.

Use explain to understand the execution mechanism.

Use representative workload measurements to determine the actual customer impact.

## 10. `COLLSCAN`, `IXSCAN`, `FETCH`, and `SORT`

These are fundamental plan concepts.

### 10.1 Collection scan

`COLLSCAN` indicates a collection scan.

MongoDB examines documents and evaluates the query conditions.

For a highly selective lookup in a large collection, this may be expensive.

For a query that genuinely needs most of the collection, it may be reasonable.

A collection scan on a tiny collection is often harmless.

### 10.2 Index scan

`IXSCAN` indicates scanning entries in an index.

The important follow-up is identifying which index was used and what bounds were applied.

An index scan can examine only a narrow range.

Or it can scan a vast portion of the index.

The stage name alone doesn't reveal selectivity.

### 10.3 Document fetch

`FETCH` indicates retrieving documents from the collection after identifying candidate records through an index.

This may be necessary because the query needs fields not present in the index.

It may also be necessary to evaluate conditions that cannot be fully resolved from index entries.

A plan containing `IXSCAN` followed by `FETCH` isn't inherently bad.

Most ordinary application queries need actual document content.

The question is whether too many documents are fetched before being rejected.

### 10.4 Sort

If MongoDB cannot obtain the required order directly from an index, it may perform an explicit sort.

An explicit `SORT` stage can become expensive when many documents qualify.

The query may need to examine the entire relevant input before deciding which documents belong at the top.

A suitable compound index can sometimes avoid this work entirely.

### 10.5 Engine-specific representations

In a slot-based execution plan, the visible stage structure may differ from older classic-engine examples.

Some plans include a representation of the query plan alongside the lower-level slot-based execution details.

Aggregation explain output also has version-dependent structures.

Don't conclude that a behavior is absent merely because its stage name isn't located at the path an old tutorial expects.

## 11. Why `totalDocsExamined` Can Be Much Larger Than `nReturned`

Imagine an index on tenant ID.

The query asks for Mercury's confirmed bookings.

MongoDB uses the tenant index to find Mercury's documents.

It fetches candidate documents and checks status.

Suppose Mercury has eighty thousand bookings and sixty thousand are confirmed.

If the index can't efficiently narrow by status, the executor may fetch many documents that won't appear in the final result.

Then it sorts or otherwise arranges the matches to return twenty.

The result is a high document-examination count.

The remedy might be a compound index that includes status and the relevant order.

But we should confirm this through the actual plan.

### 11.1 A useful efficiency comparison

One simple diagnostic ratio is documents examined divided by documents returned.

For example, twenty thousand examined and twenty returned produces a ratio of one thousand to one.

A large ratio deserves investigation.

However, it's not a universal quality score.

A report calculating statistics over twenty thousand documents may legitimately return one summary document.

That would produce a large examined-to-returned ratio even if every input document was necessary.

**Interpret examined counts in the context of the actual business operation.**

## 12. Understanding Index Bounds

An index scan is valuable because it can restrict the part of the index being traversed.

MongoDB explain output can expose index bounds.

Imagine a compound index on tenant ID, status, and booking timestamp.

The query uses equality conditions for Mercury and confirmed status.

The relevant index range can be restricted to that tenant-status combination.

Within that range, booking timestamps are ordered.

This allows the executor to retrieve recent bookings without scanning unrelated tenants or statuses.

### 12.1 Bounds can be broad

Suppose the query filters only by tenant ID.

The compound index may still be useful because tenant ID is the prefix.

But without a status predicate, the scan must consider multiple status ranges.

If the query sorts by booking time across all statuses, an index ordered by tenant, status, and booking time does not necessarily provide the requested global booking-time order.

Why?

Because booking time is ordered separately within each status group.

The index does not interleave all statuses according to booking time.

This is a subtle but important consequence of compound index ordering.

### 12.2 Prefixes matter

An index ordered by tenant, status, and booking time naturally supports filtering by tenant.

It can also support filtering by tenant and status.

But a query filtering only by booking time cannot generally exploit the same efficient prefix narrowing.

MongoDB has optimizations for certain index access patterns, but you should not assume a compound index is equally useful for every subset of its fields.

The index's ordering encodes a hierarchy.

## 13. Equality, Sort, Range — With Qualifications

MongoDB documents the ESR guideline for compound indexes.

Equality fields usually come first.

Sort fields follow when avoiding an in-memory sort is important.

Range fields follow when that ordering produces the better access path.

But there is an important qualification.

If a range predicate is extremely selective, placing it before the sort fields can reduce scanned data enough to justify performing an explicit sort afterward.

This alternative is sometimes described as Equality, Range, Sort.

The correct choice depends on the workload.

### 13.1 Our admin endpoint

The query filters by tenant and status, then sorts by booking timestamp and `_id` descending.

A plausible index is:

```javascript id="2z475g"
{
  tenantId: 1,
  status: 1,
  bookedAt: -1,
  _id: -1
}
```

This supports both equality predicates and the requested ordering.

### 13.2 Add a range predicate

Now the administrator filters to bookings made during the last month.

If booking timestamp is also the sort field, the index can potentially restrict the time range while providing the required order.

But suppose the query filters by a narrow amount range and sorts by booking time.

Should amount precede booking time or follow it?

That depends on whether reducing the amount range is more valuable than avoiding the sort.

The answer should come from measurements and query frequencies.

### 13.3 An index is an investment

Every index consumes storage and imposes maintenance work on writes.

A compound index with many fields may be useful for a specific read pattern but expensive to maintain.

The objective isn't creating an index for every imaginable query.

It's supporting the important workload with a defensible index budget.

## 14. Covered Queries and Projections

A covered query can return results using only index data.

Suppose the admin interface needs tenant ID, status, and booking timestamp.

If those fields are indexed and the query can be fully evaluated from the same index, MongoDB may avoid fetching documents.

A suitable projection is necessary.

```javascript id="kfph8l"
db.bookings.find(
  {
    tenantId: "mercury",
    status: "confirmed"
  },
  {
    _id: 0,
    tenantId: 1,
    status: 1,
    bookedAt: 1
  }
)
.sort({ bookedAt: -1 })
.limit(20);
```

When this query is covered by a suitable index, `totalDocsExamined` can be zero.

### 14.1 Why `_id` matters

MongoDB includes `_id` in a typical result unless it is explicitly excluded.

If the chosen index doesn't contain `_id`, an otherwise coverable query may require a document fetch to return it.

Either include `_id` in the index if justified or exclude it from the projection when the application doesn't need it.

### 14.2 Projection is not automatically coverage

Returning fewer fields can reduce data transfer and processing.

But if the query still needs a field that isn't in the index, MongoDB may need to fetch documents.

A projection can make the result smaller without eliminating the fetch stage.

That remains useful, but it is a different optimization.

### 14.3 Coverage has limitations

Multikey indexes, null predicates, and other query conditions can restrict coverage.

A query is not covered merely because most fields happen to be indexed.

Use explain to confirm the actual absence of document examinations.

## 15. Multikey Indexes: One Document, Several Keys

MongoDB arrays introduce another important complication.

Suppose a booking document contains several tags:

`["vip", "refundable", "corporate"]`

A multikey index on the tags field can represent multiple distinct array values from that one document.

Therefore, index-key examinations need not correspond one-to-one with document examinations.

This is why the two counters are separate.

### 15.1 Arrays complicate compound indexes

MongoDB has restrictions on compound multikey indexes when multiple indexed fields contain arrays.

A compound index cannot simply combine arbitrary independent array-valued fields in all circumstances.

Array matching semantics also matter.

When multiple conditions must apply to the same array element, `$elemMatch` can be necessary to express the intended relationship and potentially improve index-bound usage.

These topics were introduced in CS340-L04.

Here the operational lesson is that multikey plans require careful interpretation.

High key-examination counts may partly reflect several index entries per document.

## 16. Partial Indexes: Index Only Relevant Documents

Suppose the administrative interface frequently queries pending reservations.

Pending bookings represent a small fraction of the entire collection.

A partial index can include only documents meeting a specified condition.

For example, an index can cover pending bookings while excluding confirmed and cancelled ones.

This may reduce index size and write-maintenance costs compared with indexing every document.

But the planner cannot use the partial index for queries whose results might require documents excluded from it.

### 16.1 The eligibility rule

A query must contain conditions that imply the partial index's filter.

If an index contains only pending bookings, a query for all bookings cannot rely on it to produce complete results.

Likewise, a query for confirmed bookings cannot use it as though it covered those documents.

A partial index is valuable precisely because it represents a restricted subset.

Its correctness depends on the query's relationship to that subset.

### 16.2 The index may still not win

Even if a query is eligible to use a partial index, the planner might choose another strategy.

Eligibility and optimality are different questions.

Inspect the plan and workload before concluding that the index is being ignored incorrectly.

## 17. The Query Planner Chooses a Candidate

MongoDB's query planner considers available candidate plans.

It evaluates them according to its planning mechanisms and selects a winner.

The selection is informed by observed work during the planning process.

The selected plan may later be cached for reuse with queries of the same relevant shape.

This improves performance by avoiding repeated planning work.

But the plan that is best during a trial isn't guaranteed to be best for every parameter distribution or future data size.

### 17.1 Explain ignores the plan cache

This is a critical diagnostic caveat.

`explain()` doesn't simply report the cached plan that the ordinary application request would necessarily use.

It ignores existing plan cache entries and doesn't create a new cached winning plan.

Therefore, it is possible for explain and normal application execution to behave differently.

### 17.2 Query shape and plan cache identity

Modern MongoDB exposes identifiers such as `planCacheShapeHash` and `planCacheKey`.

The query shape identifies structurally related requests.

The plan cache key also depends on the index environment relevant to that shape.

Adding or removing indexes can change the plan cache key.

Exact fields and formats vary by MongoDB version.

These identifiers are useful when correlating slow-query logs and plan-cache behavior.

But don't mistake a shared shape for identical selectivity.

Two requests with the same structural form can target tenants with dramatically different amounts of data.

### 17.3 Replanning and changing workloads

A plan can become less appropriate as data distributions or available indexes change.

MongoDB has mechanisms for plan-cache management and plan reconsideration.

The details vary by version.

The correct investigation combines plan information with actual workload evidence rather than assuming the planner will always select the ideal strategy.

## 18. Why `hint()` Is Useful but Dangerous

MongoDB supports `hint()` to request a specific index.

This is valuable during experiments.

Suppose a query has two candidate indexes.

You can force each one in turn and compare examined keys, examined documents, sorting work, and latency.

This helps determine why one strategy behaves differently.

But a forced index is not automatically appropriate for production.

The forced strategy may be beneficial for one tenant and disastrous for another.

If the index is removed or changed, the hint may become invalid.

And a hint can constrain future planner decisions as the dataset evolves.

Use hints to establish evidence.

Don't use them as a substitute for understanding the workload.

## 19. Why a Collection Scan Can Be Rational

A query asks for every confirmed booking.

Confirmed bookings represent eighty percent of the collection.

MongoDB may prefer scanning the collection instead of navigating through a low-selectivity status index and fetching most documents anyway.

This resembles the PostgreSQL index-versus-sequential-scan problem from CS350-L02.

The underlying cost trade-off is similar.

An index saves work when it avoids enough irrelevant data.

If nearly everything qualifies, it may add overhead without saving much.

### 19.1 Compare the complete operation

An indexed strategy may be faster if the index also supports sorting or covers the projection.

A collection scan may be competitive if the query reads most documents.

Do not evaluate the status index in isolation from sorting, projection, and result limits.

The best access path depends on the full query.

## 20. Query Plans Versus Application Latency

Suppose explain reports a query execution time of forty milliseconds.

The application endpoint takes six hundred milliseconds.

Is MongoDB innocent?

Not necessarily.

The query might be executed repeatedly.

The application might perform additional aggregation operations.

Connection-pool waiting can add delay.

Network transfer and BSON decoding may contribute.

The Node.js process may perform expensive transformations after receiving the documents.

The API may invoke several MongoDB queries sequentially.

MongoDB explain doesn't automatically reveal the entire endpoint's behavior.

A complete investigation requires tracing the application request across its boundaries.

### 20.1 The MongoDB equivalent of N+1

Suppose the application retrieves twenty bookings.

Then it issues a separate query for each booking's customer information.

Each individual query may be efficient.

But the endpoint performs twenty-one database operations.

A single explain result won't show the cumulative application-level pattern.

Inspect driver calls and request traces.

### 20.2 The opposite failure: one giant aggregation

A developer may combine everything into one enormous pipeline with `$lookup`, `$unwind`, `$group`, computed fields, and sorting.

This eliminates round trips but may create large intermediate results.

One query isn't automatically better than several.

CS345-L02 will investigate that problem in depth.

## 21. A Production Investigation Procedure

Let's return to the original administrative endpoint.

The customer reports that the reservations list has become slow.

### Step 1 — Establish the exact symptom

Which endpoint is slow?

Which tenant?

Which filters?

Which page?

Does the problem occur on the first page, deep pages, or both?

Is the latency consistent or intermittent?

### Step 2 — Capture the real MongoDB operation

Record the complete filter, projection, sort, skip, limit, and relevant collation.

Include representative parameter values.

Don't rely on a simplified reconstruction.

### Step 3 — Inspect `explain("executionStats")`

Record `nReturned`, `totalKeysExamined`, `totalDocsExamined`, and the winning plan.

Identify collection scans, index scans, document fetches, and sorting stages.

### Step 4 — Examine index definitions

Use `getIndexes()`.

Determine whether an existing index matches the query shape.

Consider equality predicates, ordering, and ranges.

Inspect whether the projection could be covered.

### Step 5 — Explain the wasted work

Don't stop at saying "the index is bad."

Explain why the index requires scanning or fetching more data than necessary.

### Step 6 — Test a focused alternative

Create a candidate index in the isolated lab or appropriate testing environment.

Use hints diagnostically if useful.

Measure before and after.

### Step 7 — Verify correctness

Ensure the same filters, projection, ordering, and result semantics remain intact.

A faster query that silently drops records is not an optimization.

### Step 8 — Evaluate index maintenance

An additional index increases storage and write-maintenance costs.

Determine whether the improvement justifies that cost.

### Step 9 — Measure normal workload behavior

Explain bypasses the plan cache.

Verify representative application latency and query behavior separately.

### Step 10 — Consider the larger architecture

If the query requires expensive computation or very deep pagination, another index may not be sufficient.

The data model, precomputation strategy, or pagination contract may need to change.

Those are the subjects of the next lectures.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — The Twenty-Document Illusion

A query returns twenty documents but examines 100,000.

What does that tell you?

What does it not tell you?

### Question 2 — `IXSCAN` Without Improvement

A query uses a tenant index but still takes several seconds.

The tenant has hundreds of thousands of bookings.

The query also filters by status and sorts by booking date.

What would you investigate?

### Question 3 — Compound Index Order

Explain why an index on tenant ID, status, and descending booking time may help a query filtering by tenant and status and sorting by booking time.

Why might the same index be less suitable for sorting all statuses together?

### Question 4 — Covered Query

A query projects only indexed fields.

Why might MongoDB still fetch documents?

What should you verify in explain?

### Question 5 — Low Selectivity

A query matches eighty percent of the collection.

MongoDB chooses `COLLSCAN` despite an index on the filtered field.

Is this necessarily a poor plan?

### Question 6 — Partial Index

A partial index contains only pending reservations.

Can it safely satisfy a query returning all reservations?

Why not?

### Question 7 — Plan Cache

Why might `explain("executionStats")` differ from ordinary application execution?

Can its timing be treated as an exact prediction of endpoint latency?

### Question 8 — Multikey Index

Why might `totalKeysExamined` exceed the number of distinct documents examined?

What kind of data structure commonly causes this?

### Question 9 — Deep Pagination

An indexed query sorts correctly but uses `skip(80000).limit(20)`.

Why can it remain expensive?

What would you consider changing?

### Question 10 — Production Judgment

Your team proposes adding five compound indexes to support every variation of an admin search screen.

What evidence would you request before approving them?

---

# Solutions and Discussion

## Solution 1 — Examined Versus Returned

The query performed substantial examination work relative to its output.

That may suggest inefficient filtering, ordering, or pagination.

But a high ratio isn't inherently bad for operations that legitimately aggregate large input sets.

Inspect the query's purpose and execution stages.

## Solution 2 — Tenant Index

The tenant index may narrow the collection to a still-large subset.

Status filtering and sorting can require additional work.

Consider a compound index reflecting the equality predicates and sort order.

Verify the resulting examined counts and plan structure.

## Solution 3 — Compound Ordering

The index groups keys by tenant, then status, then booking time.

Equality conditions on the first two fields allow efficient traversal in booking-time order.

Without a status equality, booking time is ordered within separate status groups rather than globally across them.

## Solution 4 — Covered Query

Coverage requires all query and projection fields to be available from a suitable index.

The default `_id` projection may require a fetch when `_id` isn't included.

Null predicates, multikey restrictions, or other conditions can also prevent coverage.

Check `totalDocsExamined` and relevant execution stages.

## Solution 5 — Collection Scan

A collection scan may be cheaper when most documents qualify.

An index may add traversal and fetch overhead.

Compare actual workload measurements rather than judging the stage name.

## Solution 6 — Partial Index

No.

The index excludes documents outside its filter.

A query requiring all reservations cannot rely on an index containing only pending reservations.

The query predicate must imply the partial filter for the index to provide a complete result.

## Solution 7 — Plan Cache

Explain ignores existing cached plans and performs its own planning.

Its reported time doesn't include all application costs.

Use explain to investigate execution work, then verify real workload latency separately.

## Solution 8 — Multikey

Array-valued fields can create multiple index entries associated with one document.

Therefore, keys examined and unique documents examined need not match.

## Solution 9 — Deep Pagination

Skip requires advancing past the preceding results.

An index can support ordering without eliminating the offset traversal.

Cursor pagination may help when sequential navigation is acceptable.

## Solution 10 — Index Budget

Request representative query shapes, frequency, selectivity, current execution plans, latency evidence, and write workload information.

Evaluate whether fewer well-designed indexes can support several important access patterns.

Consider storage and write-maintenance costs.

---

# The Mental Model Worth Keeping

A MongoDB query plan describes the physical work required to produce a result.

The essential questions are:

**How many keys were examined? How many documents were fetched or examined? Which index bounds restricted the search? Was sorting avoided? How much work was necessary?**

An index being present doesn't establish that it is useful.

An index being used doesn't establish that the query is efficient.

A small result doesn't establish that the query is cheap.

A collection scan doesn't automatically indicate a defect.

The objective is to explain the work and demonstrate that a proposed change reduces unnecessary work without changing correctness.

---

# Next Lecture — CS345-L02: Aggregation Pipelines Under Pressure

Our first lecture focused on query access paths and index forensics.

But real MongoDB production problems often involve more than `find()`.

An administrative report may join customer records through `$lookup`, expand nested arrays with `$unwind`, calculate derived fields, group historical events, and sort the final results.

The individual operations are reasonable.

Together, they can create enormous intermediate datasets.

A query returning twenty records may process hundreds of thousands of records along the way.

In CS345-L02, we'll investigate how aggregation pipelines amplify work, which optimizations MongoDB can perform automatically, and when pipeline structure must change.

*The spoken lecture ends here. The following material is intended for independent investigation in a disposable MongoDB environment.*

---

# Optional Practical Lab — MongoDB Query Plan Forensics

## Lab Contract

This workshop is designed to produce actual execution evidence.

You must predict the likely behavior before running each query.

Then inspect the results and explain discrepancies.

Do not assume MongoDB will choose a specific plan on every machine.

Version, data distribution, available indexes, cache state, and planner behavior can affect the results.

The objective is not to make the plan match a screenshot.

The objective is to explain the plan you observe.

Use only an isolated local database.

## 1. Start MongoDB

Start a disposable MongoDB 8.0 container.

```bash id="hyo0ap"
docker run --name cs345-mongo \
  -p 27028:27017 \
  -d mongo:8.0
```

If the container already exists but is stopped:

```bash id="fuzbea"
docker start cs345-mongo
```

Connect through `mongosh`:

```bash id="2p7ozt"
docker exec -it cs345-mongo mongosh cs345
```

All subsequent JavaScript snippets are intended for `mongosh`.

They use the disposable `cs345` database.

## 2. Create the Fixture

The fixture contains 120,000 bookings.

A dominant tenant called Mercury owns seventy percent of them.

The remaining documents belong to smaller tenants.

Booking timestamps increase monotonically with the sequence number.

The dataset deliberately includes skewed distributions and a relatively large note field.

### Reset the collection

```javascript id="li2a4z"
const lab = db.getSiblingDB("cs345");

lab.bookings.drop();
```

### Insert the bookings

Use batches to avoid creating an unnecessarily large client-side array.

```javascript id="dewe3e"
const collection = lab.bookings;

const batchSize = 1000;
const total = 120000;

for (let start = 1; start <= total; start += batchSize) {
  const batch = [];

  for (
    let g = start;
    g < start + batchSize && g <= total;
    g++
  ) {
    const tenantId =
      g % 100 < 70
        ? "mercury"
        : `tenant-${g % 30}`;

    const status =
      g % 13 === 0
        ? "cancelled"
        : g % 5 === 0
          ? "pending"
          : "confirmed";

    batch.push({
      seq: g,
      tenantId,
      status,
      hotelId: g % 500,
      customerId: g % 10000,

      bookedAt: new Date(
        Date.UTC(2026, 0, 1) + g * 60_000
      ),

      amountEur: 75 + (g % 900),

      tags: [
        g % 4 === 0 ? "vip" : "standard",
        g % 5 === 0 ? "email" : "web"
      ],

      note: `Booking-${g}-` + "x".repeat(120)
    });
  }

  collection.insertMany(batch, {
    ordered: false
  });
}

print("Documents inserted:", collection.countDocuments({}));
```

### Verify the fixture

```javascript id="u0e81f"
printjson(
  collection.aggregate([
    {
      $group: {
        _id: "$tenantId",
        count: { $sum: 1 }
      }
    },
    { $sort: { count: -1 } },
    { $limit: 5 }
  ]).toArray()
);
```

Mercury should own 84,000 bookings.

The total collection should contain 120,000 documents.

## 3. Create a Deliberately Incomplete Index

Begin with only a tenant index.

```javascript id="ledw2d"
collection.createIndex(
  { tenantId: 1 },
  { name: "tenant_only" }
);
```

This index can locate one tenant's documents.

It does not directly organize those documents by status and booking timestamp.

---

# Experiment A — The Twenty-Document Illusion

## Starting Symptom

The administrative endpoint requests Mercury's twenty newest confirmed bookings.

The result is small.

The workload may not be.

### Query

```javascript id="6el4gu"
const query = {
  tenantId: "mercury",
  status: "confirmed"
};

const sort = {
  bookedAt: -1,
  _id: -1
};

const initialExplain = collection
  .find(query)
  .sort(sort)
  .limit(20)
  .explain("executionStats");

printjson({
  nReturned: initialExplain.executionStats.nReturned,
  keysExamined:
    initialExplain.executionStats.totalKeysExamined,
  docsExamined:
    initialExplain.executionStats.totalDocsExamined,
  executionTimeMillis:
    initialExplain.executionStats.executionTimeMillis
});
```

### Tasks

Before running, predict whether MongoDB can use the tenant index.

Can the tenant index avoid examining unrelated statuses?

Can it provide the required booking-time order?

Run the query.

Record the actual examined counts.

Inspect the full winning plan separately.

Identify whether it uses `COLLSCAN`, `IXSCAN`, `FETCH`, or an explicit sorting operation.

### Acceptance criteria

You can explain why returning twenty documents may require substantial work.

You understand which parts of the query the tenant-only index supports.

You do not assume index usage means efficient execution.

---

# Experiment B — Build a Workload-Matched Compound Index

## Objective

Create an index reflecting the actual equality predicates and sort order.

### Candidate index

Before creating it, predict how it should change the execution plan.

Then execute:

```javascript id="4myuag"
collection.createIndex(
  {
    tenantId: 1,
    status: 1,
    bookedAt: -1,
    _id: -1
  },
  {
    name: "tenant_status_time"
  }
);
```

Run the original query again.

```javascript id="7yrxxi"
const improvedExplain = collection
  .find(query)
  .sort(sort)
  .limit(20)
  .explain("executionStats");

printjson({
  nReturned: improvedExplain.executionStats.nReturned,
  keysExamined:
    improvedExplain.executionStats.totalKeysExamined,
  docsExamined:
    improvedExplain.executionStats.totalDocsExamined,
  executionTimeMillis:
    improvedExplain.executionStats.executionTimeMillis
});
```

### Tasks

Compare the examined counts.

Did the winning plan change?

Does the compound index support the required order?

Is an explicit sort still present?

Does the query still return the same twenty documents?

### Verification

Use a deterministic projection and compare the identifiers returned before and after the index was created.

The order should remain consistent because the query includes the `_id` tie-breaker.

### Acceptance criteria

You can explain why the compound index matches the query shape.

You can demonstrate whether it reduced examination work.

You have not relied solely on timing differences.

---

# Experiment C — Force a Poor Candidate Index

## Objective

Compare competing access strategies.

Create a status-only index.

```javascript id="5qfow8"
collection.createIndex(
  { status: 1 },
  { name: "status_only" }
);
```

Now run the admin query while forcing the status-only index.

```javascript id="xx3zyz"
const forced = collection
  .find(query)
  .sort(sort)
  .hint("status_only")
  .limit(20)
  .explain("executionStats");

printjson({
  nReturned: forced.executionStats.nReturned,
  keysExamined:
    forced.executionStats.totalKeysExamined,
  docsExamined:
    forced.executionStats.totalDocsExamined,
  executionTimeMillis:
    forced.executionStats.executionTimeMillis
});
```

### Tasks

Compare the forced plan with the compound-index plan.

Does the status index restrict the search to Mercury?

Does it support the requested order?

How many index entries and documents are examined?

Why might an index that is useful for one query be poor for another?

### Acceptance criteria

You understand that `hint()` is a diagnostic tool.

You do not recommend forcing an index in production merely because one local experiment produced a favorable result.

---

# Experiment D — Covered Query Versus Document Fetch

## Objective

Observe when MongoDB can satisfy a query entirely from index entries.

The existing compound index contains tenant ID, status, booking timestamp, and `_id`.

### Covered projection

```javascript id="iz8olv"
const covered = collection
  .find(
    {
      tenantId: "mercury",
      status: "confirmed"
    },
    {
      _id: 0,
      tenantId: 1,
      status: 1,
      bookedAt: 1
    }
  )
  .sort({ bookedAt: -1 })
  .limit(20)
  .explain("executionStats");

printjson({
  nReturned: covered.executionStats.nReturned,
  keysExamined:
    covered.executionStats.totalKeysExamined,
  docsExamined:
    covered.executionStats.totalDocsExamined
});
```

### Prediction

Should MongoDB need to fetch the original booking documents?

Why or why not?

### Uncovered projection

Now request the note field as well.

```javascript id="xc6t3y"
const uncovered = collection
  .find(
    {
      tenantId: "mercury",
      status: "confirmed"
    },
    {
      _id: 0,
      tenantId: 1,
      status: 1,
      bookedAt: 1,
      note: 1
    }
  )
  .sort({ bookedAt: -1 })
  .limit(20)
  .explain("executionStats");

printjson({
  nReturned: uncovered.executionStats.nReturned,
  keysExamined:
    uncovered.executionStats.totalKeysExamined,
  docsExamined:
    uncovered.executionStats.totalDocsExamined
});
```

### Tasks

Compare document-examination counts.

Why does requesting an additional field change the access requirements?

What happens if you omit `_id: 0` from the first projection?

### Acceptance criteria

You understand the difference between a small projection and a genuinely covered query.

You can explain why coverage may eliminate document fetches.

---

# Experiment E — Compound Index Prefixes

## Objective

Demonstrate that a compound index doesn't support every subset of its fields equally.

Run three queries.

### Query 1 — Tenant only

```javascript id="ic8r5y"
collection
  .find({ tenantId: "mercury" })
  .limit(20)
  .explain("executionStats");
```

### Query 2 — Tenant and status

```javascript id="8w8ir6"
collection
  .find({
    tenantId: "mercury",
    status: "confirmed"
  })
  .limit(20)
  .explain("executionStats");
```

### Query 3 — Status and booking time without tenant

```javascript id="aaif1m"
collection
  .find({
    status: "confirmed"
  })
  .sort({ bookedAt: -1 })
  .limit(20)
  .explain("executionStats");
```

### Tasks

Inspect which indexes MongoDB chooses.

Explain why the prefix fields matter.

Explain why the compound index organized by tenant and status does not automatically provide one global booking-time order across all tenants.

Compare the number of examined keys and documents.

### Acceptance criteria

You can predict which queries align with the compound index's leading fields.

You understand the limits of prefix-based access.

---

# Experiment F — Partial Index Eligibility

## Objective

Create an index containing only pending bookings.

### Partial index

```javascript id="r2sewf"
collection.createIndex(
  {
    tenantId: 1,
    bookedAt: -1
  },
  {
    name: "pending_by_tenant_time",
    partialFilterExpression: {
      status: "pending"
    }
  }
);
```

### Query eligible for the partial index

```javascript id="afmd4v"
collection
  .find({
    tenantId: "mercury",
    status: "pending"
  })
  .sort({ bookedAt: -1 })
  .limit(20)
  .explain("executionStats");
```

### Query not eligible for the same partial index

```javascript id="zj31jt"
collection
  .find({
    tenantId: "mercury",
    status: "confirmed"
  })
  .sort({ bookedAt: -1 })
  .limit(20)
  .explain("executionStats");
```

### Tasks

Explain why the partial index cannot provide complete results for the confirmed query.

Inspect whether MongoDB chooses the partial index for the pending query.

If it chooses another eligible index, explain why that is not automatically a correctness or planner defect.

### Acceptance criteria

You understand the eligibility rule for partial indexes.

You can distinguish index eligibility from the planner's selection of the winning strategy.

---

# Experiment G — Multikey Index Evidence

## Objective

Observe how array-valued fields affect index-entry counts.

The fixture contains a `tags` array.

Create an index:

```javascript id="rf2x4q"
collection.createIndex(
  { tags: 1 },
  { name: "tags_multikey" }
);
```

Run a tag query:

```javascript id="3q6am6"
const tagExplain = collection
  .find({ tags: "vip" })
  .hint("tags_multikey")
  .limit(100)
  .explain("executionStats");

printjson({
  nReturned: tagExplain.executionStats.nReturned,
  keysExamined:
    tagExplain.executionStats.totalKeysExamined,
  docsExamined:
    tagExplain.executionStats.totalDocsExamined
});
```

### Tasks

Inspect the multikey index metadata in explain.

Why can one document contribute multiple index entries?

Why shouldn't index keys examined be interpreted as unique documents examined?

### Acceptance criteria

You can explain multikey index cardinality.

You understand why array queries may need additional attention when designing compound indexes.

---

# Experiment H — A Glimpse of Deep Pagination

## Objective

Observe the cost of skipping a large number of matching index entries.

Use the compound-index-supported query.

### Shallow page

```javascript id="pavvxr"
const shallow = collection
  .find(query)
  .sort(sort)
  .skip(0)
  .limit(20)
  .explain("executionStats");
```

### Deep page

```javascript id="5klqsa"
const deep = collection
  .find(query)
  .sort(sort)
  .skip(40000)
  .limit(20)
  .explain("executionStats");
```

### Compare

```javascript id="3kxboi"
printjson({
  shallow: {
    returned: shallow.executionStats.nReturned,
    keys: shallow.executionStats.totalKeysExamined,
    docs: shallow.executionStats.totalDocsExamined,
    ms: shallow.executionStats.executionTimeMillis
  },
  deep: {
    returned: deep.executionStats.nReturned,
    keys: deep.executionStats.totalKeysExamined,
    docs: deep.executionStats.totalDocsExamined,
    ms: deep.executionStats.executionTimeMillis
  }
});
```

### Questions

Do both queries return twenty documents?

Does the deeper query examine more index entries?

Why doesn't the compound index completely eliminate offset cost?

Would cursor pagination change the access pattern?

### Acceptance criteria

You can explain why an index-supported sort may still require substantial work for deep offsets.

Do not attempt to fully redesign pagination yet.

That will be the focus of CS345-L03.

---

# Final Investigation — The Slow Admin Endpoint

## Starting Symptom

The Mercury administrative endpoint has become slow.

It displays twenty confirmed bookings, sorted newest first.

The initial implementation uses only a tenant index.

You have now collected several execution plans.

### Required Incident Report

Prepare a short technical report containing:

**Business requirement:** Which documents does the endpoint need?

**Observed behavior:** What were the measured examined counts and execution characteristics?

**Root cause:** Which work was unnecessarily performed?

**Index decision:** Which index best matches the important query shape?

**Correctness:** Does the corrected query return the same results in the required order?

**Trade-offs:** What storage and write costs does the new index introduce?

**Verification:** How would you verify actual production performance beyond explain?

### Interviewer Challenge

Your interviewer says:

"The compound index is faster. Why don't we create compound indexes for every combination of filters in the admin UI?"

Explain why that is usually a poor indexing strategy.

Discuss query frequency, index overlap, write costs, storage, and the importance of prioritizing actual access patterns.

---

# STOP — End of Independent Lab

Do not read the following diagnostic notes until after attempting the experiments.

The goal is to interpret your own execution evidence rather than reproduce a memorized answer.

---

# Lab Diagnostic Notes

## Experiment A — The Incomplete Tenant Index

The tenant-only index can identify Mercury's documents but doesn't directly support the status filter and booking-time ordering.

MongoDB may need to examine many candidate documents and perform additional sorting work.

The selected plan depends on collection size and planner choices.

The underlying issue is the mismatch between the index organization and the complete query shape.

## Experiment B — Compound Index

The compound index aligns with the tenant and status equality predicates followed by booking-time ordering.

MongoDB can potentially restrict the index scan to the relevant range and return the first twenty entries without a broad sort.

The expected improvement is a substantial reduction in examined work.

Verify the actual plan rather than assuming the optimizer will always select it.

## Experiment C — Forced Status Index

The status-only index cannot efficiently narrow the query to one tenant.

It also doesn't provide the requested booking-time order.

Using it may require examining many unrelated documents.

The result demonstrates why the mere presence of `IXSCAN` doesn't establish efficiency.

## Experiment D — Covered Query

The initial projection requests only fields available from the compound index.

When covered, MongoDB can avoid fetching original documents.

Requesting `note` introduces a field not present in the index.

Document fetches become necessary.

This demonstrates why query shape and projection both affect the physical plan.

## Experiment E — Index Prefixes

The compound index's leading fields determine how efficiently MongoDB can restrict the search.

A query using tenant and status aligns well with its prefix.

A query requiring a global booking-time order across all tenants does not automatically benefit from that same ordering.

## Experiment F — Partial Index

The pending-only partial index can support eligible pending queries.

It cannot provide complete results for confirmed queries.

MongoDB may choose another eligible index if its planner considers that strategy preferable.

## Experiment G — Multikey Index

The tags array creates a multikey index.

One document can contribute multiple index entries.

Index-entry examinations and document examinations therefore measure different things.

## Experiment H — Deep Pagination

The shallow query can stop after finding the first twenty relevant results.

The deep query must account for the preceding offset.

Even with a suitable compound index, the skip requires traversing earlier entries.

Cursor pagination can often avoid this repeated traversal when sequential navigation is acceptable.

## Final Investigation — Expected Judgment

A strong diagnosis identifies the query's actual filter and sort requirements, demonstrates unnecessary work in the initial plan, and verifies improvement through a workload-matched compound index.

The recommendation should not be based only on `executionTimeMillis` from explain.

Use representative application performance measurements and inspect the normal plan-cache environment.

A good index policy supports important query shapes without creating unnecessary maintenance overhead for every possible filter combination.

---

# Further Reading

1. **MongoDB — Explain Results**  
   https://www.mongodb.com/docs/manual/reference/explain-results/

2. **MongoDB — Interpret Explain Plan Results**  
   https://www.mongodb.com/docs/manual/tutorial/analyze-query-plan/

3. **MongoDB — Query Optimization**  
   https://www.mongodb.com/docs/manual/core/query-optimization/

4. **MongoDB — ESR Guideline**  
   https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/

5. **MongoDB — Compound Indexes**  
   https://www.mongodb.com/docs/manual/core/indexes/index-types/index-compound/

6. **MongoDB — Partial Indexes**  
   https://www.mongodb.com/docs/manual/core/index-partial/

7. **MongoDB — Multikey Indexes**  
   https://www.mongodb.com/docs/manual/core/indexes/index-types/index-multikey/

8. **MongoDB — Query Plans and Plan Cache**  
   https://www.mongodb.com/docs/manual/core/query-plans/

9. **MongoDB — cursor.explain()**  
   https://www.mongodb.com/docs/manual/reference/method/cursor.explain/

10. **MongoDB — Aggregation `$sort`**  
    https://www.mongodb.com/docs/manual/reference/operator/aggregation/sort/

Cross-reference CS340-L03 and CS340-L04 for foundational MongoDB modeling and index theory, CS350-L02 for the relational-database comparison, and `production-cases/MONGO-01.md` for deep pagination.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text id="0kic4r"
CS345-L01 — MONGODB QUERY PLAN FORENSICS
================================================

THE CORE QUESTION
-----------------
How much work produced the result?

QUERY SHAPE
-----------
Filter
Projection
Sort
Skip
Limit
Collation
Relevant parameter values

EXPLAIN
-------
db.collection.find(...).explain("executionStats")

queryPlanner:
  selected plan information

executionStats:
  completed winning-plan statistics

allPlansExecution:
  additional partial candidate-plan data

EXPLAIN CAVEAT
--------------
Explain ignores existing plan cache.
It does not populate a new cached plan.

Explain timing != guaranteed steady-state
application latency.

CORE METRICS
------------
nReturned:
  documents returned

totalKeysExamined:
  index-entry examinations

totalDocsExamined:
  document examinations

executionTimeMillis:
  explain execution timing

Examinations are not necessarily
unique documents or exact latency units.

STAGES
------
COLLSCAN:
  collection scan

IXSCAN:
  index scan

FETCH:
  retrieve documents

SORT:
  explicit sort operation

Engine/version can change plan structure.

INDEX BOUNDS
------------
Narrow bounds reduce scanned keys.

Compound index ordering defines
which ranges are contiguous.

INDEX PREFIX
------------
{ tenant: 1, status: 1, date: -1 }

Good:
  tenant equality
  tenant + status equality
  tenant + status + date sort

Not equivalent to:
  global date ordering across tenants

ESR
---
Equality
Sort
Range

Equality fields usually first.
Sort next when avoiding sort matters.
Highly selective range may justify ERS.

Measure actual workload.

COVERED QUERY
-------------
All needed fields available in index.
No document fetch required.

totalDocsExamined can be 0.

Remember default _id projection.
Coverage has query-specific limitations.

MULTIKEY
--------
Array values may create multiple
index entries per document.

keysExamined != unique docs examined.

PARTIAL INDEX
-------------
Contains only documents matching
partialFilterExpression.

Query must imply partial filter
to use it without incomplete results.

Eligible != automatically selected.

LOW SELECTIVITY
---------------
Index may be worse than COLLSCAN
when most documents qualify.

Do not worship IXSCAN.

HINT
----
Forces an index strategy.

Useful for controlled comparison.
Not automatically a production fix.

PLAN CACHE
----------
Query shape identifies related requests.
planCacheShapeHash reflects shape.
planCacheKey also depends on
relevant index availability.

Exact fields vary by MongoDB version.

DEEP PAGINATION
---------------
skip(40000).limit(20)

Can traverse large offset even with
correct index order.

Cursor pagination often changes
the problem from skip to seek.

INDEX BUDGET
------------
Indexes cost:
- storage
- build resources
- write maintenance
- operational complexity

Optimize actual access patterns,
not hypothetical every-filter combinations.

DIAGNOSTIC PROCEDURE
--------------------
1. Capture real query and parameters.
2. Record current latency.
3. Run explain executionStats.
4. Inspect examined/returned counts.
5. Identify scan/fetch/sort stages.
6. Inspect bounds and index inventory.
7. Form a causal hypothesis.
8. Test focused index/query change.
9. Verify identical results.
10. Measure normal workload behavior.

RED FLAGS
---------
"Only 20 docs, so the query is cheap."
"IXSCAN proves performance is good."
"COLLSCAN always means missing index."
"Every indexed query is covered."
"Indexes always avoid sorting."
"Keys examined equals distinct docs."
"Explain timing equals API latency."
"Hint the index and ship immediately."
"One compound index supports every subset."
"Deep skip is cheap with any index."

MENTAL MODEL
------------
An index is an ordered access path.

Ask:
What was searched?
What was skipped?
What was fetched?
What was sorted?
What was returned?

Explain the physical work.
Verify the correction.

NEXT
----
CS345-L02
Aggregation Pipelines Under Pressure
```
