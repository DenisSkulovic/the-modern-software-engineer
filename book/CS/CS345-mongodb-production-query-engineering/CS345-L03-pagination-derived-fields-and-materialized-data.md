---
id: CS345-L03
course: CS345
title: "Pagination, Derived Fields, and Materialized Data"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS345-L02
next: CS345-L04
---

# CS345 — MongoDB Production Query Engineering
## Lecture 03: Pagination, Derived Fields, and Materialized Data

*The engineer stores one additional field. The expensive aggregation disappears from the read path. The page becomes fast. Three weeks later, the customer rankings are wrong.*

---

# Part I — Intuition

## 1. The Field That Saved the Database

Imagine a SaaS platform with thousands of customers and millions of historical activity events.

Its administrative interface allows account managers to browse customers, filter them, and sort them by completed revenue.

A customer's revenue isn't stored directly in the customer document.

Instead, it is calculated from historical events.

Each time an administrator opens the ranking, MongoDB must determine which customers qualify, retrieve their completed events, calculate revenue totals, sort customers by the calculated amounts, and return the requested page.

You investigated the aggregation in CS345-L02.

You found a useful index on the event collection. You reduced unnecessary intermediate arrays. You moved suitable filters earlier and verified MongoDB's optimizer behavior.

The pipeline became more efficient.

But it still had a fundamental problem.

To identify the twenty customers with the greatest completed revenue, MongoDB had to calculate revenue for all relevant candidates.

It couldn't simply retrieve the first twenty from an existing revenue index because that indexed value didn't exist.

Now imagine adding two fields to every customer document:

`completedRevenue` and `completedEventCount`.

Whenever a completed event is recorded, the customer's stored totals are updated.

The administrative query becomes almost embarrassingly simple.

Find Mercury's customers. Sort by completed revenue. Return twenty.

With a compound index matching the tenant and ranking order, MongoDB can potentially retrieve the requested records through a short index traversal.

No historical lookup is required on the normal read path.

No grouping of event histories is needed.

The ranking has become much cheaper.

It's a beautiful optimization.

Until someone changes an event.

## 2. The Price of a Stored Answer

Suppose Customer 733 has accumulated €500,000 in completed-event revenue.

The value is stored on their customer document.

Now an administrator discovers that a previously completed event worth €10,000 was recorded incorrectly.

They change the event's status to failed.

The source history is corrected.

But the customer document still reports €500,000.

The correct amount is €490,000.

The administrative ranking now contains a value that disagrees with its authoritative history.

The database is executing the query perfectly.

The index is working correctly.

The query returns exactly the stored information.

Unfortunately, the stored information is wrong.

This is the trade-off behind materialized data.

**You move computation from the read path into the write, synchronization, and maintenance paths.**

The expensive work doesn't simply disappear.

Some of it is performed when facts change. Some of it may be performed during background reconciliation or rebuilding.

And the application acquires a new responsibility: ensuring that the derived representation remains faithful to its source.

## 3. Source Facts Versus Derived Representations

Imagine an accounting ledger containing individual business events.

Each event has an identity, customer, status, amount, and timestamp.

That history represents the underlying facts used for our ranking.

The customer document's revenue total is a derived representation of those facts.

We can reconstruct the total by reading the history.

But we cannot necessarily reconstruct every historical event from the total alone.

That difference is important.

The source facts carry greater informational detail.

The derived representation trades some of that detail for convenient access.

### Visual anchor 1 — Two ways to answer the same question

```text id="md1a8x"
COMPUTE ON READ

Customer documents
        |
        v
Join historical events
        |
        v
Filter completed events
        |
        v
Calculate totals
        |
        v
Sort calculated totals
        |
        v
Return 20 customers


MATERIALIZED READ MODEL

Historical events
        |
        | maintained computation
        v
Customer.completedRevenue
        |
        v
Indexed sort
        |
        v
Return 20 customers
```

The second design improves frequent reads.

But the arrow connecting historical events to the stored total must be implemented and maintained.

If that arrow breaks, the cached truth becomes fiction.

## 4. Deep Pagination Is Another Independent Problem

Now suppose we have solved the computed-sort problem.

The customer collection contains indexed revenue totals.

Page one loads quickly.

The administrator jumps to page five thousand.

The endpoint uses a page size of twenty and an offset of almost one hundred thousand.

Even with the correct index, MongoDB must advance through the preceding ordered results before returning the requested page.

The expensive historical calculation has disappeared.

The deep offset cost remains.

These were two separate problems:

**Problem A:** Computing the sort key required expensive historical work.

**Problem B:** Locating a deep page required traversing many earlier results.

Materialization addresses the first.

Cursor-based pagination can address the second.

But neither automatically solves the other.

### Visual anchor 2 — Indexed offset versus indexed cursor

```text id="am76p1"
OFFSET PAGINATION

Indexed customer ranking
    |
    v
Walk 100,000 entries
    |
    v
Discard almost all
    |
    v
Return 20


CURSOR PAGINATION

Indexed customer ranking
    |
    v
Seek past last known
ranking position
    |
    v
Return next 20
```

The cursor approach needs an ordering contract and a known previous position.

It is excellent for sequential navigation.

It does not automatically provide cheap arbitrary jumps to page five thousand.

That's an important product trade-off.

## 5. A Cursor Describes a Position, Not a Page Number

Suppose customers are sorted by completed revenue descending.

Alice has €900.

Bob and Cara both have €800.

Dan has €700.

If the first page contains Alice and Bob, where should the next page begin?

It must begin with Cara.

Using only revenue as a cursor is insufficient.

If we request revenue strictly below €800, Cara disappears.

If we request revenue less than or equal to €800, Bob may appear again.

We need a unique tie-breaker.

For example, sort by revenue descending and customer ID ascending.

Now the ordering is complete.

The cursor contains both the last revenue value and the last customer ID.

### Visual anchor 3 — Stable cursor ordering

```text id="jv33my"
Customer    Revenue    ID
Alice       900        1
Bob         800        2   ← cursor
Cara        800        3
Dan         700        4

Next page:
Revenue < 800
OR
Revenue = 800 AND ID > 2
```

This is lexicographic pagination over the selected ordering.

The unique ID makes ties deterministic.

Without a complete order, even a perfectly indexed query can skip or repeat entities.

## 6. Materialization Creates a Consistency Policy

Let's return to Customer 733.

Their stored revenue becomes incorrect after a historical event changes.

How can we prevent this?

One strategy is to update the event and customer total together within an appropriate multi-document transaction.

Another is to publish a reliable event and let a background consumer update the summary.

A third is to rebuild the summary periodically.

A fourth is to accept bounded staleness because the ranking is informational rather than financially authoritative.

These strategies have different guarantees.

An administrative dashboard may tolerate a short delay in its ranking.

A payment settlement system may not.

The correct decision depends on the consequence of inconsistency.

The most dangerous design is one that claims the materialized value is always current while offering no mechanism to maintain or verify it.

**Every derived field needs an explicit consistency contract.**

## 7. A Tiny Comprehension Check

Suppose a customer has three completed events worth €100, €200, and €50.

Their stored completed revenue is €350.

Now the €200 event changes from completed to failed.

Should the stored total become €150?

Yes.

Would applying `$inc: {completedRevenue: 200}` again during a retry be safe?

No. It would double-count the contribution.

Would changing the original event status and the customer total in two independent writes provide atomic consistency?

No. One write could succeed and the other fail.

These are not indexing questions.

They're data consistency and distributed-workflow questions.

That is why materialization is an architectural decision, not merely a performance trick.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. First Separate Three Different Costs

Our original MongoDB endpoint had several expensive behaviors.

It joined historical events.

It calculated customer-level totals.

It sorted by those totals.

It skipped large numbers of results.

When optimizing, separate three costs.

**Source acquisition:** How much historical data must MongoDB examine?

**Derived computation:** How much work is required to calculate the ranking key?

**Result navigation:** How much work is required to locate the requested portion of the ordered result?

A better foreign index can improve source acquisition.

A materialized total can remove repeated derived computation from the normal read path.

Cursor pagination can reduce result-navigation cost.

But these optimizations operate at different layers.

A clear diagnosis identifies which cost dominates before redesigning the system.

## 9. Offset Pagination: Convenient but Linear in Distance

Offset pagination uses `skip()` and `limit()`.

A page size of twenty and page number 151 produce a skip of three thousand.

A page number of five thousand produces a skip of 99,980.

MongoDB documents that `skip()` must scan from the beginning of the relevant input results before returning the requested portion.

As the offset increases, it generally becomes slower.

### 9.1 A good index doesn't make skip free

Suppose our customer ranking uses:

`{tenantId: 1, completedRevenue: -1, _id: 1}`

The index supports filtering by tenant and walking the customer records in revenue order.

That's excellent.

But if the query skips three thousand matching records, it still needs to advance past them.

The index avoids an expensive sorting operation.

It doesn't eliminate the offset traversal.

### 9.2 Why offset remains useful

Offset pagination supports arbitrary page numbers.

The user can jump directly to page fifty.

A page-size change maps naturally into an offset.

It is straightforward to implement and explain.

For small datasets and shallow pages, it is often perfectly reasonable.

The correct conclusion is not that offset pagination is forbidden.

It's that its cost and consistency properties must match the product.

### 9.3 Changing data can shift pages

Imagine the user loads page one.

Then a customer receives a large new event and moves higher in the ranking.

The user requests page two.

The ordering has changed between requests.

An offset now refers to a different set of positions.

A customer might appear twice or be missed.

This isn't exclusively a MongoDB problem.

It is a consequence of navigating a changing ordered dataset through positional offsets.

## 10. Cursor Pagination: Navigate Relative to a Known Row

Cursor pagination uses the last result's ordering values.

For our ranking, the order is:

Completed revenue descending.

Customer ID ascending.

The next page requests customers appearing after the cursor in that order.

A query can express this with a compound predicate.

For a previous final row with revenue 800 and ID 2, the next page includes customers whose revenue is less than 800, or whose revenue equals 800 and whose ID is greater than 2.

This produces a deterministic continuation for a stable dataset.

### 10.1 Cursor pagination can use a compound index

The same index supporting the sort can support the range-based query.

However, the optimizer must still choose an appropriate plan.

Complex `$or` expressions, other filters, and query transformations may affect index bounds.

Don't assume every cursor implementation is equally efficient.

Inspect the execution plan.

### 10.2 Cursor encoding

A production API should not accept arbitrary MongoDB query fragments from the browser.

Instead, the server can issue an opaque cursor containing the relevant ordering values and contextual information.

The cursor may include the last score, last ID, filter identity, and a schema or ranking version.

The server validates and decodes it.

If tampering matters, the cursor can be authenticated cryptographically.

A cursor is an API contract, not just a JSON object passed through without validation.

### 10.3 Cursor limitations

A cursor doesn't guarantee a frozen view of the collection.

If a customer's revenue changes between page requests, the customer may move across the cursor boundary.

New or updated records can still cause duplicates or omissions under certain conditions.

For a strict snapshot-consistent export, a different mechanism may be required, such as snapshot reads under supported database semantics, a fixed ranking version, or a materialized export dataset.

Cursor pagination improves traversal efficiency and ordering behavior.

It does not automatically solve temporal consistency.

## 11. Why Computed Sorting Defeats Ordinary Index Ordering

In CS345-L02, we calculated customer revenue through an aggregation over activity events.

The sort key existed only after the calculation.

MongoDB couldn't use a simple index on the customer collection to retrieve documents already ordered by that value.

The query first had to establish the derived revenue values.

Only then could it sort the customers.

### 11.1 Adding an index on source fields is not equivalent

Suppose activity events have an index on customer ID and status.

That helps find completed events for a customer.

But it does not directly give us a globally ordered list of customers by the sum of those events.

An index on individual event amounts doesn't give the sum per customer either.

We are ranking by a derived aggregate over multiple source documents.

The index would need to organize the already calculated customer-level result.

### 11.2 Moving the limit earlier changes semantics

We cannot select twenty arbitrary customers and then calculate which of them has the greatest revenue.

That would rank a subset rather than the full candidate set.

A correct global ranking requires sufficient information about all potentially qualifying customers.

Materialization changes that because the ranking key is already available.

## 12. The Computed Pattern

MongoDB documents the Computed Pattern as a way to store frequently needed calculated values ahead of read time.

Imagine storing `completedRevenue` and `completedEventCount` on the customer document.

The historical event collection remains the source from which those values are derived.

But administrative queries can use the stored summaries directly.

### 12.1 The read benefit

A ranking query becomes:

Find Mercury customers.

Sort by stored revenue descending and ID ascending.

Return twenty.

With a suitable compound index, MongoDB may avoid the expensive history aggregation entirely.

The index can provide the required ordering.

The query may need to fetch only the requested customer documents.

### 12.2 The write cost

Whenever an event becomes completed, its contribution must be incorporated.

If a completed event changes amount, the stored total must be adjusted by the difference.

If a completed event is reversed, its contribution must be removed.

If an event moves between customers, both customer summaries may need correction.

If an event is deleted, the system must determine whether that deletion changes the aggregate.

The read-model maintenance rules become part of the domain model.

### 12.3 The consistency contract

A useful invariant is:

> For each customer, completed revenue equals the sum of amounts from all authoritative events currently classified as completed.

That statement is much more valuable than saying the system caches revenue.

It defines what correctness means.

It gives us something to test, rebuild, and monitor.

## 13. Incremental Maintenance Versus Full Recalculation

There are two broad approaches to maintaining derived values.

**Full recalculation:** Read the relevant source events and compute the complete current aggregate.

**Incremental maintenance:** Apply the difference caused by each source change.

Both are useful.

### 13.1 Full recalculation

Suppose Customer 733's summary is suspected to be stale.

We can aggregate that customer's completed events and calculate the authoritative total.

Then replace the stored summary.

This is straightforward to reason about.

It naturally handles corrections and reversals because the total is reconstructed from current source facts.

But it can be expensive for customers with very large histories.

Recomputing every customer after every event would defeat the original optimization.

### 13.2 Incremental maintenance

Suppose an event worth €120 changes from pending to completed.

The customer's total increases by €120.

MongoDB's `$inc` operator can atomically modify a numeric field within one document.

The same update can increment the completed event count.

This is efficient.

But the update must happen exactly once for the logical transition.

If a retry applies the same increment twice, the summary becomes wrong.

### 13.3 Corrections require deltas

Consider these transitions:

A new completed event worth €100 contributes plus €100 and plus one completed event.

A completed event changes to failed: minus €100 and minus one completed event.

A completed event's amount changes from €100 to €150: plus €50, with no count change.

A pending event changes amount: zero change to completed revenue.

An event moves from Customer A to Customer B: remove its contribution from A and add it to B.

A correct incremental system must understand the old and new contribution of each event.

A naive implementation that always increments by the new amount is incorrect.

## 14. Single-Document Atomicity Is Not Cross-Document Atomicity

MongoDB provides atomic updates at the single-document level.

An update using `$inc` is atomic for the customer document being modified.

But our authoritative event is stored in another collection.

Changing the event and changing the customer summary are two document modifications.

If they're executed independently, one can succeed while the other fails.

### 14.1 The partial-success problem

Imagine the service changes an event from pending to completed.

The event update succeeds.

Then the process crashes before updating the customer summary.

The source says completed.

The summary hasn't changed.

A retry needs to recover.

But if the retry blindly increments the summary, it may be correct this time—or it may double-count if the first attempt had already applied the increment before losing its response.

The system needs an explicit idempotency and reconciliation design.

### 14.2 Multi-document transactions

MongoDB supports multi-document transactions on replica sets and sharded clusters.

A suitable transaction can update the source event and its customer summary atomically.

If the transaction aborts, neither modification should become committed.

That is valuable for strict consistency requirements.

But transactions have costs and require correct handling of write conflicts, retries, and uncertain commit outcomes.

A standalone MongoDB server does not support multi-document transactions.

Our basic laboratory can demonstrate atomic single-document updates and deliberate drift, but a transactional integration experiment requires a replica-set deployment.

### 14.3 Atomicity isn't the entire problem

Even with a transaction, the application must correctly determine the source transition.

The update should establish whether the event actually changed from its expected previous state.

Only if the transition occurs should the associated delta be applied.

Otherwise, a repeated command could apply the same business transition again.

A transaction coordinates changes.

It doesn't automatically understand their business meaning.

## 15. Asynchronous Read Models and Eventual Consistency

Not every ranking requires strict synchronous consistency.

Suppose the customer ranking is an administrative analytical view.

A delay of several seconds between source changes and the displayed ranking may be acceptable.

The application could update the source event first, then publish a reliable notification or use a change stream to maintain the summary asynchronously.

### 15.1 Change streams

MongoDB change streams allow applications to observe database changes on replica sets and sharded clusters.

A worker can react to event inserts, updates, and deletes.

But change streams do not automatically provide a perfect exactly-once business processing guarantee.

A consumer can restart, resume, retry, or process events again depending on its recovery behavior.

The projection-maintenance logic must be idempotent or otherwise protected against duplicate application.

### 15.2 Old and new contributions

A change stream update event does not always contain all the information needed to calculate a delta.

If an amount changes from €100 to €150, the worker needs to know both values or otherwise reconstruct the prior contribution.

MongoDB supports pre- and post-images for change streams when configured appropriately.

Those facilities have availability, retention, and operational requirements.

Alternatively, the application can publish explicit domain events containing the required before-and-after information.

### 15.3 An event ledger

One possible robust design maintains a ledger of projection updates identified by stable event or transition IDs.

The consumer records which logical updates have already been applied.

Duplicate delivery can then be recognized.

But recording the deduplication marker and changing the aggregate must itself be coordinated appropriately.

Otherwise the system can mark work as processed without applying it, or apply it without recording completion.

The design must make recovery safe.

### 15.4 Eventual consistency needs observability

If the ranking is eventually consistent, the system should know how far behind it is.

Useful measurements include projection lag, pending updates, last processed source position, reconciliation discrepancies, and rebuild status.

"Eventually consistent" should not mean "sometimes wrong and nobody knows why."

## 16. Backfilling a Derived Field

Suppose we decide to introduce `completedRevenue` on existing customer documents.

The collection contains millions of customers.

We must calculate historical totals and populate the new fields.

This is a backfill.

### 16.1 The initial population

A backfill can aggregate authoritative events by customer ID and write summary fields into customer documents.

MongoDB's `$merge` stage supports incorporating aggregation results into another collection.

This can be useful for building materialized views.

But `$merge` is not a universal atomic snapshot-replacement mechanism.

Writes may be applied incrementally, and a failure can leave partial output.

### 16.2 Zero-activity customers

A grouping aggregation over completed events produces no group for a customer with zero completed events.

If the application expects every customer to contain explicit zero-valued summary fields, the backfill must handle those customers separately.

One approach is to initialize summary fields to zero before populating computed values.

Another is to build a complete customer-level read model beginning from customers and joining source data.

The correct choice depends on the data structure and operational constraints.

### 16.3 The race during a live backfill

A particularly dangerous scenario occurs when the application continues updating summaries while a historical backfill runs.

Imagine:

The backfill begins reading historical events.

A new completed event arrives.

The live application increments the customer summary.

Then the backfill writes an older calculated total over the updated summary.

The new event's contribution disappears from the materialized value.

The source history is correct.

The projection is stale.

This is a deployment-consistency problem, similar to the schema migration issues from CS350-L04.

### 16.4 Safe migration strategies

A robust production approach needs a defined cutover strategy.

Possible designs include:

- Temporarily controlling relevant writes while rebuilding.
- Computing a new projection in a separate collection, then catching up with subsequent source changes.
- Using source event sequence numbers or watermarks to determine which changes are already reflected.
- Reconciling and validating before switching readers.
- Maintaining a versioned projection and retiring the old one only after successful cutover.

There is no universal one-line `$merge` command that solves every concurrency problem.

The backfill must be designed around the consistency guarantees required by the application.

## 17. Reconciliation: How Do We Detect a Lying Field?

Suppose our materialized revenue has been maintained for several months.

How do we know it remains correct?

We need a way to reconstruct expected values from source events and compare them with the stored summaries.

### 17.1 Full reconciliation

A full reconciliation calculates totals for every customer and compares them with the materialized values.

This is conceptually straightforward.

It may be expensive for a large dataset.

### 17.2 Sampled reconciliation

The system can periodically select customers and compare their totals.

This reduces cost.

But sampling doesn't guarantee every discrepancy will be detected.

### 17.3 Targeted reconciliation

Customers associated with failed projection updates, unusual activity, or recently corrected events can be prioritized.

This can detect important defects efficiently.

### 17.4 Rebuild from source

A derived representation should ideally be reconstructible from authoritative facts.

That provides a recovery mechanism when projection logic contains a bug.

But a rebuild must still handle concurrent changes and safe cutover.

A reconstruction that produces correct historical values and then overwrites newer live updates is not sufficient.

## 18. The `$facet` Exact-Count Trap

Now consider the pagination interface.

The product manager wants a message:

"Showing 20 of 4,000 customers."

The backend uses `$facet` to return both the current page and the exact total count.

That can be convenient.

But a single aggregation request does not imply cheap work.

### 18.1 Computed filter versus stored filter

Suppose the user asks for customers whose completed revenue exceeds €10,000.

If revenue is calculated dynamically from historical events, obtaining the exact count may require calculating revenue for every qualifying customer.

The page branch and count branch depend on that computation.

If revenue is stored and indexed, the count can potentially use a much cheaper indexed predicate.

Materialization improves more than sorting.

It can also improve filtering and counting on derived values.

### 18.2 Counts remain a product decision

Does the interface genuinely require an exact total on every interaction?

Perhaps it does.

Perhaps the administrator only needs Next and Previous controls.

Perhaps a cached count updated periodically is acceptable.

Perhaps the product can display "more results available" without calculating the entire total immediately.

These are legitimate product decisions with engineering consequences.

The right answer isn't always another index.

Sometimes the right answer is changing the interface contract.

## 19. Materialized Field Versus Separate Summary Collection

We have discussed storing `completedRevenue` directly on each customer document.

That's not the only option.

We could create a separate collection containing customer ranking summaries.

Each summary document might contain customer ID, tenant ID, completed revenue, event count, and an update version.

### 19.1 Embedded derived field

Advantages include simple reads and straightforward filtering with customer attributes.

But frequently updated summary fields may create write contention on customer documents or affect their indexes.

The summary's lifecycle becomes coupled to the customer document.

### 19.2 Separate read model

A separate summary collection can isolate ranking-specific indexes and write patterns.

It can support versioned rebuilds and more explicit projection ownership.

But queries may require additional data access to obtain customer names or other attributes.

That can introduce new joins, duplication, or synchronization concerns.

### 19.3 Which is better?

The choice depends on the workload.

If the customer document is relatively stable and the ranking changes infrequently, a stored field may be simple.

If rankings change constantly or need independent rebuilds, a dedicated read-model collection may be cleaner.

Don't create a separate collection merely because microservices architecture diagrams look impressive with more boxes.

Use the boundary that reflects actual operational needs.

## 20. Materialization Can Become a Write Bottleneck

Suppose one customer generates thousands of completed events per second.

Every event updates the same customer revenue document.

Now the materialized summary becomes a hot document.

MongoDB must coordinate concurrent updates to that document.

Even though `$inc` is atomic at the document level, repeatedly updating one document can become a throughput bottleneck.

### 20.1 The read optimization moved contention elsewhere

The original application performed expensive reads.

The redesigned application performs cheap indexed reads.

But now high-volume writes contend on shared summary documents.

This is a classic trade-off.

The optimization moved work from read time to update time.

### 20.2 Alternative aggregation strategies

The system might aggregate events into time buckets or partitioned counters, then combine a small number of summaries.

A background process might periodically consolidate partial totals.

For extremely high write rates, the read model may deliberately accept a consistency delay.

These designs increase complexity.

They should be justified by actual write pressure.

### 20.3 Index maintenance also matters

An index on `completedRevenue` must be updated when the value changes.

If revenue changes frequently, that index receives substantial maintenance traffic.

The index is still valuable for ranking reads.

But its write cost belongs in the architecture decision.

**A materialized indexed field is not free storage. It is an ongoing maintenance contract.**

## 21. When Not to Materialize

Materialization is not automatically appropriate.

Consider a small collection with a few hundred customers.

The historical aggregation takes ten milliseconds.

The ranking runs a handful of times per day.

Maintaining derived revenue might introduce more complexity than it saves.

Likewise, some metrics are difficult to update incrementally.

A simple count or sum is often manageable.

An exact median, percentile, or complex distinct count may require more sophisticated state or periodic recomputation.

Some metrics also depend on changing time windows.

A rolling ninety-day revenue total changes when old events leave the window, even if no new events arrive.

A naive increment-on-insert strategy would fail to remove expired contributions.

Materialization is attractive when the read cost is meaningful, the metric has a clear definition, and the maintenance strategy is operationally reasonable.

## 22. The Decision Framework

Before materializing a derived field, answer six questions.

**How expensive is computing it on demand?**

Measure actual query work and latency.

**How frequently is it requested?**

A costly calculation executed once a month may be acceptable.

**How often do its inputs change?**

A summary updated once daily has a different maintenance cost from one updated thousands of times per second.

**How fresh must the result be?**

A dashboard ranking may tolerate bounded staleness. A financial settlement calculation may not.

**Can the value be reconstructed?**

A clear source-of-truth relationship supports reconciliation and recovery.

**What happens if maintenance fails?**

Design retries, idempotency, monitoring, and rebuilding before treating the derived field as dependable.

These answers determine whether materialization is a good trade.

## 23. Returning to the Original Production Incident

Let's reconstruct our admin ranking problem.

The original endpoint joined historical activity, calculated per-customer revenue, sorted the computed values, skipped thousands of results, and returned twenty customers.

The proposed redesign stores completed revenue on the customer documents.

A compound index supports tenant filtering and revenue ordering.

The normal read path no longer joins histories.

This can dramatically reduce query work.

But the design is incomplete until we answer:

Who updates revenue when an event completes?

What happens when an event is reversed?

How are partial corrections handled?

Can repeated messages double-count a contribution?

How are existing customers backfilled?

How does the application detect drift?

Can an old backfill overwrite newer updates?

What consistency does the UI promise?

How does the system recover after a consumer outage?

These questions are not peripheral complications.

They are the cost of the optimization.

The correct engineering judgment balances the reduced read cost against the new write and maintenance responsibilities.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Two Bottlenecks

A query computes revenue through `$lookup`, sorts customers by that value, skips 100,000 results, and returns twenty.

Which problems can storing an indexed revenue field solve?

Which problem remains?

## Question 2 — Cursor Ties

Customers are sorted by revenue descending.

Two customers have the same revenue.

Why is revenue alone insufficient as a cursor?

What additional field would you use?

## Question 3 — Event Correction

An event changes from completed at €100 to completed at €150.

How should the materialized revenue change?

What happens to the completed-event count?

## Question 4 — Duplicate Delivery

A consumer processes an event that adds €200 to customer revenue.

The consumer restarts and processes the same logical event again.

What happens with a naive `$inc`?

How could the architecture prevent this?

## Question 5 — Partial Success

An application updates the source event successfully, then crashes before updating the summary.

What invariant is violated?

What mechanisms could prevent or repair the inconsistency?

## Question 6 — Backfill Race

A historical backfill calculates €500 for a customer.

Before it writes the value, a new completed event increases the live summary to €600.

The backfill then writes €500.

What went wrong?

How could a production migration avoid this?

## Question 7 — Changing Rankings

A customer moves from page two to page one because their revenue increases between pagination requests.

Can cursor pagination guarantee that the user sees every customer exactly once across the entire browsing session?

Why not?

## Question 8 — Exact Counts

A `$facet` returns twenty customers and an exact count after calculating revenue through historical lookups.

Does the small response imply low query cost?

What changes if revenue is stored and indexed?

## Question 9 — Write Amplification

A materialized revenue field is updated thousands of times per second for one customer.

What new performance problem might appear?

## Question 10 — Architectural Judgment

A ranking runs twice daily and takes 80 milliseconds.

Would you immediately introduce materialized revenue with transactions, event consumers, reconciliation, and backfills?

Defend your decision.

---

# Solutions and Discussion

## Solution 1 — The Two Bottlenecks

A stored, indexed revenue field can eliminate repeated historical revenue computation and allow MongoDB to retrieve customers in revenue order.

Deep offset traversal remains expensive.

Cursor pagination can address sequential traversal, but arbitrary deep page jumps remain a distinct product requirement.

## Solution 2 — Cursor Ties

Revenue alone doesn't uniquely identify a position.

Use a stable unique tie-breaker such as customer ID.

For descending revenue and ascending ID, the cursor predicate must reflect both ordering directions.

## Solution 3 — Event Correction

Increase completed revenue by €50.

The completed-event count remains unchanged because the event stays completed.

The update should be based on the difference between old and new contributions.

## Solution 4 — Duplicate Delivery

A repeated `$inc` would double-count the event.

The system needs idempotent processing, such as a durable transition identifier and appropriately coordinated deduplication state, or another design that makes repeated processing safe.

## Solution 5 — Partial Success

The materialized total no longer equals the authoritative completed-event sum.

A multi-document transaction can coordinate the two writes on a supported deployment.

Alternatively, a reliable asynchronous projection with idempotent processing and reconciliation can restore consistency.

## Solution 6 — Backfill Race

An older calculated snapshot overwrote a newer projection value.

A safe strategy needs explicit source positioning, controlled writes, a catch-up process, versioned cutover, or another way to prevent stale results from replacing newer state.

## Solution 7 — Changing Rankings

No.

Cursor pagination doesn't freeze the dataset.

Records whose ranking values change can move across the cursor boundary.

Strictly consistent pagination requires additional snapshot or versioning semantics.

## Solution 8 — Exact Counts

No.

The count branch can still depend on expensive upstream computation.

Stored and indexed revenue can allow filtering and counting without recomputing the complete historical aggregate.

## Solution 9 — Write Amplification

The customer summary may become a hot document.

Frequent updates can create contention and index-maintenance overhead.

Possible alternatives include batched updates, bucketed summaries, or eventually consistent consolidation.

## Solution 10 — Architectural Judgment

Probably not.

An 80-millisecond query executed twice daily may not justify a substantial consistency and maintenance subsystem.

First establish that the existing query creates meaningful business or operational problems.

Materialization should solve a measured problem, not merely demonstrate architectural sophistication.

---

# The Mental Model Worth Keeping

Materialization changes the location of work.

Computing on read keeps the answer close to its authoritative source but may repeat expensive operations.

Maintaining a derived field makes reads cheap but creates write, synchronization, and recovery responsibilities.

Cursor pagination changes how the application navigates an ordered result.

It reduces deep-offset traversal but doesn't freeze a changing dataset.

The most important questions are:

**What is authoritative? What is derived? What maintains the derived value? How can it become wrong? How will we detect and repair that?**

A fast stored answer is useful only if its correctness is understood.

---

# Next Lecture — CS345-L04: The MongoDB Performance Incident Studio

We have now covered query-plan forensics, aggregation cardinality, deep pagination, indexed sorting, and materialized read models.

The final lecture combines these mechanisms.

You'll inherit several deliberately problematic MongoDB endpoints.

One has catastrophic deep-offset pagination.

Another grows slower as customer history accumulates.

A third uses a convenient `$facet` whose exact count forces expensive computation.

You'll be expected to inspect execution evidence, identify causes, implement corrections, preserve business semantics, and defend the trade-offs.

The capstone will also challenge apparently obvious fixes that improve reads while making writes or consistency significantly worse.

*The spoken lecture ends here. The remaining material is a practical investigation and should be performed independently before consulting the solutions.*

---

# Optional Practical Lab — Materialized Rankings and Pagination

## Working Contract

This lab continues the MongoDB 8.0 fixture from CS345-L02.

It requires:

- `pipeline_customers`: 5,000 customers.
- `pipeline_events`: 200,000 events.
- 4,000 Mercury customers.
- Customer 733 with 20,036 historical events.

If those collections do not exist, run the fixture setup from CS345-L02 first.

The lab deliberately introduces incorrect materialized values.

Run it only in the disposable `cs345` database.

The workflow is:

**Predict → Measure → Implement → Break → Diagnose → Repair → Verify.**

Do not read the answer key before attempting the exercises.

## Lab 1 — Verify the Starting Dataset

Connect to the local MongoDB container.

```bash
docker exec -it cs345-mongo mongosh cs345
```

Use the lab database.

```javascript
const lab = db.getSiblingDB("cs345");

const customers = lab.pipeline_customers;
const events = lab.pipeline_events;

printjson({
  customers: customers.countDocuments({}),
  events: events.countDocuments({}),
  mercury: customers.countDocuments({
    tenantId: "mercury"
  }),
  whaleHistory: events.countDocuments({
    customerId: 733
  })
});
```

The expected values are 5,000, 200,000, 4,000, and 20,036.

Stop and repair the fixture if they differ.

---

# Lab 2 — Establish the Compute-on-Read Baseline

The first pipeline calculates revenue from completed activity events.

It starts with Mercury customers, aggregates their completed events through `$lookup`, and sorts by the computed revenue.

The result is logically one customer summary per customer, including customers with zero completed events.

```javascript
const computedPrefix = [
  {
    $match: {
      tenantId: "mercury"
    }
  },
  {
    $lookup: {
      from: "pipeline_events",
      localField: "_id",
      foreignField: "customerId",
      pipeline: [
        {
          $match: {
            status: "completed"
          }
        },
        {
          $group: {
            _id: null,
            completedCount: { $sum: 1 },
            completedRevenue: { $sum: "$amountEur" }
          }
        }
      ],
      as: "summary"
    }
  },
  {
    $set: {
      completedCount: {
        $ifNull: [
          { $arrayElemAt: ["$summary.completedCount", 0] },
          0
        ]
      },
      completedRevenue: {
        $ifNull: [
          { $arrayElemAt: ["$summary.completedRevenue", 0] },
          0
        ]
      }
    }
  },
  {
    $project: {
      name: 1,
      completedCount: 1,
      completedRevenue: 1
    }
  }
];

const ranking = [
  { $sort: { completedRevenue: -1, _id: 1 } },
  { $limit: 20 }
];

const computedTop20 = customers.aggregate(
  [...computedPrefix, ...ranking],
  { maxTimeMS: 120000, allowDiskUse: true }
).toArray();

printjson(computedTop20);
```

### Task A — Measure

Inspect the execution plan.

```javascript
const baselineExplain = customers
  .explain("executionStats")
  .aggregate(
    [...computedPrefix, ...ranking],
    { maxTimeMS: 120000, allowDiskUse: true }
  );

printjson(baselineExplain);
```

Record the winning access path, lookup work, index use, and relevant stage statistics.

### Task B — Reason

Why must this pipeline calculate totals for every candidate customer before determining the top twenty?

Would adding an index on `pipeline_events.amountEur` directly provide the customer-level revenue ranking?

Explain.

---

# Lab 3 — Materialize the Customer Totals

We will store completed revenue and event count directly in the customer documents.

This is a controlled, offline laboratory backfill.

**Do not treat this script as a concurrency-safe production migration.** It assumes no other process is updating these fields or changing source events during the rebuild.

### Step A — Initialize every customer

```javascript
customers.updateMany(
  {},
  {
    $set: {
      completedRevenue: 0,
      completedCount: 0
    }
  }
);
```

This ensures customers with no completed events receive explicit zero values.

### Step B — Aggregate source events

The following aggregation calculates totals and writes them into the matching customer documents.

The `$merge` stage uses the customer ID as its match key.

It updates only the derived fields, preserving customer names and other fields.

```javascript
events.aggregate([
  {
    $match: {
      status: "completed"
    }
  },
  {
    $group: {
      _id: "$customerId",
      completedRevenue: { $sum: "$amountEur" },
      completedCount: { $sum: 1 }
    }
  },
  {
    $merge: {
      into: "pipeline_customers",
      on: "_id",
      whenMatched: [
        {
          $set: {
            completedRevenue:
              "$$new.completedRevenue",
            completedCount:
              "$$new.completedCount"
          }
        }
      ],
      whenNotMatched: "discard"
    }
  }
], {
  allowDiskUse: true,
  maxTimeMS: 120000
}).toArray();
```

`$merge` is a write stage. The operation has side effects, and its writes are not necessarily rolled back as a group if it fails partway through.

### Task C — Verify

Read a sample customer:

```javascript
printjson(
  customers.findOne(
    { _id: 733 },
    {
      name: 1,
      completedRevenue: 1,
      completedCount: 1
    }
  )
);
```

Then inspect customers with no completed events.

Do their stored totals equal zero?

---

# Lab 4 — Build the Ranking Index

Create a compound index supporting tenant filtering and revenue sorting.

```javascript
customers.createIndex(
  {
    tenantId: 1,
    completedRevenue: -1,
    _id: 1
  },
  {
    name: "tenant_revenue_ranking"
  }
);
```

The new ranking query is simple:

```javascript
const materializedQuery = {
  tenantId: "mercury"
};

const materializedSort = {
  completedRevenue: -1,
  _id: 1
};

const materializedTop20 = customers
  .find(
    materializedQuery,
    {
      name: 1,
      completedCount: 1,
      completedRevenue: 1
    }
  )
  .sort(materializedSort)
  .limit(20)
  .toArray();

printjson(materializedTop20);
```

### Task A — Compare results

Compare the materialized ranking with the compute-on-read baseline.

```javascript
function comparable(rows) {
  return rows.map(row => ({
    id: row._id,
    revenue: row.completedRevenue,
    count: row.completedCount
  }));
}

print(
  "Equivalent:",
  JSON.stringify(comparable(computedTop20)) ===
  JSON.stringify(comparable(materializedTop20))
);
```

Expected: `true`.

### Task B — Explain the plan

```javascript
const materializedExplain = customers
  .find(materializedQuery)
  .sort(materializedSort)
  .limit(20)
  .explain("executionStats");

printjson({
  returned: materializedExplain.executionStats.nReturned,
  keys: materializedExplain.executionStats.totalKeysExamined,
  docs: materializedExplain.executionStats.totalDocsExamined,
  ms: materializedExplain.executionStats.executionTimeMillis
});
```

Inspect the winning plan.

### Required explanation

Why does this query no longer need `$lookup` or `$group`?

How does the compound index provide ordering?

What work remains?

Why does explain timing alone not establish normal production latency?

---

# Lab 5 — Offset Pagination Versus Cursor Pagination

## Part A — Deep offset

Request page 151, using a page size of twenty.

```javascript
const deepOffsetExplain = customers
  .find(
    { tenantId: "mercury" }
  )
  .sort({
    completedRevenue: -1,
    _id: 1
  })
  .skip(3000)
  .limit(20)
  .explain("executionStats");

printjson({
  returned: deepOffsetExplain.executionStats.nReturned,
  keys: deepOffsetExplain.executionStats.totalKeysExamined,
  docs: deepOffsetExplain.executionStats.totalDocsExamined
});
```

Predict the number of index entries the query may need to traverse.

Then inspect the actual result.

## Part B — Obtain a cursor

For the laboratory, retrieve the last row preceding the target page.

This one-time cursor lookup is itself offset-based and therefore has the corresponding cost.

```javascript
const previous = customers
  .find({ tenantId: "mercury" })
  .sort({
    completedRevenue: -1,
    _id: 1
  })
  .skip(2999)
  .limit(1)
  .next();

printjson(previous);
```

In a normal cursor API, the client obtains the cursor from the previous page instead of performing this costly arbitrary jump.

## Part C — Cursor query

Use the revenue and ID from the previous result.

```javascript
const cursorFilter = {
  tenantId: "mercury",
  $or: [
    {
      completedRevenue: {
        $lt: previous.completedRevenue
      }
    },
    {
      completedRevenue: previous.completedRevenue,
      _id: { $gt: previous._id }
    }
  ]
};

const cursorResults = customers
  .find(cursorFilter)
  .sort({
    completedRevenue: -1,
    _id: 1
  })
  .limit(20)
  .toArray();

printjson(cursorResults);
```

### Task A — Verify correctness

Compare `cursorResults` with the corresponding offset page.

The rows should match if the dataset hasn't changed.

### Task B — Inspect explain

Run `explain("executionStats")` for the cursor query.

Does MongoDB use the ranking index?

Does the plan avoid a large offset traversal?

Does the `$or` predicate introduce additional execution stages?

Don't assume every MongoDB version or index configuration produces the same exact plan.

### Task C — Explain the API trade-off

Why is cursor pagination well suited to Next and Previous navigation?

Why doesn't it automatically make jumping to page 5,000 cheap?

What happens when a customer's revenue changes between requests?

---

# Lab 6 — Break Synchronization Deliberately

Now we introduce the most important defect.

The historical event collection is authoritative.

The customer document contains a materialized representation.

We will change one without updating the other.

### Step A — Record the current values

```javascript
const target = 733;

const beforeCustomer = customers.findOne(
  { _id: target },
  {
    completedRevenue: 1,
    completedCount: 1
  }
);

const sourceEvent = events.findOne({
  customerId: target,
  status: "completed"
});

printjson({
  customer: beforeCustomer,
  event: sourceEvent
});
```

### Step B — Modify the source

Change one completed event to failed.

```javascript
const changed = events.updateOne(
  {
    _id: sourceEvent._id,
    status: "completed"
  },
  {
    $set: {
      status: "failed"
    }
  }
);

printjson(changed);
```

The event update should match one document.

### Step C — Observe the drift

Recalculate the customer's authoritative completed revenue.

```javascript
const authoritative = events.aggregate([
  {
    $match: {
      customerId: target,
      status: "completed"
    }
  },
  {
    $group: {
      _id: "$customerId",
      completedRevenue: { $sum: "$amountEur" },
      completedCount: { $sum: 1 }
    }
  }
]).toArray();

const stored = customers.findOne(
  { _id: target },
  {
    completedRevenue: 1,
    completedCount: 1
  }
);

printjson({
  authoritative: authoritative[0],
  stored
});
```

### Investigation

What is the difference?

Why is the stored value wrong?

Does the MongoDB ranking index know that the stored value is incorrect?

Could the ranking query return the wrong order even though its execution plan is efficient?

---

# Lab 7 — Repair the Derived Value

Use the authoritative source aggregation to reconstruct Customer 733's summary.

The following correction is a controlled lab repair, not a concurrency-safe production transaction.

```javascript
const corrected = authoritative[0] ?? {
  completedRevenue: 0,
  completedCount: 0
};

customers.updateOne(
  { _id: target },
  {
    $set: {
      completedRevenue: corrected.completedRevenue,
      completedCount: corrected.completedCount
    }
  }
);
```

Verify that the stored values now match the authoritative aggregation.

### Task A — Explain the limitation

What if another completed event arrives between the authoritative aggregation and the update?

Could the repaired value immediately become stale?

### Task B — Design a production correction

Describe how you would coordinate source modifications with summary updates.

Your design must account for retries, status changes, amount corrections, and duplicate processing.

---

# Lab 8 — Transactional Projection Design

This experiment is conceptual unless you explicitly configure a MongoDB replica set.

The standalone MongoDB container from CS345-L01 and L02 does not support multi-document transactions.

### Scenario

An event transitions from pending to completed.

Its amount is €120.

The source event and customer summary must change atomically.

### Task

Design a MongoDB transaction that:

1. Checks the event's current status.
2. Changes it from pending to completed only when the expected status matches.
3. Increments the customer's completed revenue by €120.
4. Increments the completed-event count by one.
5. Commits both modifications atomically.
6. Handles write conflicts, retries, and uncertain commit outcomes appropriately.

### Important questions

What happens if the event was already completed?

Should the summary increment again?

What if the customer update fails?

What if the transaction commits but the application loses the commit response?

Why is the transaction insufficient without a meaningful business transition guard?

---

# Lab 9 — The Backfill Race

## Starting Symptom

A production migration is populating materialized revenue.

The application continues accepting completed events.

The backfill reads a customer's history and calculates €500.

Before it writes, a live event adds €100 and updates the stored summary to €600.

The backfill then writes €500.

### Task A — Explain

Why did the backfill overwrite newer information?

Why doesn't simply rerunning the backfill always solve the underlying race?

### Task B — Design a safe migration

Propose a production strategy using a new versioned read model.

Explain how it would:

- Establish a source position or snapshot boundary.
- Build historical summaries.
- Capture changes occurring during the build.
- Catch up to an acceptable consistency point.
- Verify source and derived values.
- Switch readers.
- Retire the old representation.

No one-line `$merge` shortcut is sufficient without considering concurrency.

### Acceptance criteria

The proposed design has an explicit source-of-truth contract and recovery mechanism.

It accounts for failures during the backfill and cutover.

It does not silently lose new events.

---

# Lab 10 — Exact Counts and the Product Contract

## Starting Symptom

The administrative UI displays an exact total count alongside every page.

The product manager insists that the count must update immediately after every event.

### Task A — Compare two approaches

Approach one computes completed revenue through historical aggregation and uses `$facet` to obtain both the page and exact count.

Approach two filters and sorts the stored revenue field through an index.

Explain which work each approach requires.

### Task B — Challenge the requirement

Could the interface function with a cached count?

Could it display "more results available" rather than an exact total?

Could it restrict arbitrary page jumping and use cursor navigation?

### Task C — State the trade-off

Write a short recommendation balancing UI requirements, query cost, data freshness, and maintenance complexity.

---

# Final Investigation — The Materialized Ranking Incident

## Business Context

A SaaS platform stores customer activity events in MongoDB.

An administrative ranking endpoint originally calculated revenue dynamically.

The endpoint became slow as historical events accumulated.

The team introduced `completedRevenue` on customer documents and indexed it.

Read latency improved.

Several weeks later, an administrator reports that a customer's ranking is inconsistent with their event history.

## Required Incident Report

Prepare a concise production investigation containing:

**Observed symptom:** What value is wrong, and where?

**Authoritative source:** Which documents define the correct revenue?

**Projection ownership:** Which component maintains the stored total?

**Likely failure modes:** Duplicate processing, missed updates, status transitions, amount corrections, or backfill races.

**Evidence:** How would you identify the source of drift?

**Immediate repair:** How would you restore the affected customer's correct total?

**Long-term correction:** What consistency mechanism would you implement?

**Verification:** How would you detect future divergence?

**Performance trade-off:** What additional write and operational costs does materialization introduce?

## Interviewer Challenge

Your interviewer says:

"We used to have a slow query. Now we have a fast query and incorrect data. Was materialization a mistake?"

Your answer should distinguish the architectural trade-off from the quality of the implementation.

Materialization can be appropriate.

But it requires a reliable maintenance contract.

A performance improvement that creates unmonitored correctness failures is not a successful production outcome.

---

# STOP — Independent Investigation Ends Here

Do not read the following notes until you've attempted the laboratory.

The point is to reason about correctness, not merely recognize the expected answer.

---

# Lab Diagnostic Notes

## Compute-on-Read Versus Materialized Ranking

The compute-on-read pipeline must aggregate relevant histories before sorting by derived revenue.

The materialized query can use a compound index on tenant, revenue, and customer ID.

The expensive historical lookup disappears from the normal read path.

However, the stored values now require maintenance whenever source facts change.

## Offset Versus Cursor

Offset pagination traverses the preceding ordered results.

Cursor pagination seeks relative to the last known ordering tuple.

The cursor must include the unique tie-breaker to handle equal revenue values correctly.

Neither strategy guarantees snapshot consistency across a changing dataset.

## Synchronization Defect

Changing an event from completed to failed reduces authoritative completed revenue and event count.

If the customer document is not updated, the stored projection becomes stale.

MongoDB's index faithfully orders the stale values.

It does not know what the values should be.

## Controlled Repair

A full recomputation from authoritative events can repair a customer's stored total.

But the read-and-write sequence must account for concurrent changes.

A repair performed without concurrency coordination can overwrite newer updates.

## Transactional Design

On a supported replica-set or sharded deployment, a multi-document transaction can coordinate an event status transition with a customer summary update.

The operation must check that the expected source transition actually occurred.

If the event was already completed, a repeated request must not increment revenue again.

Transaction retries and uncertain commit responses require appropriate handling.

## Asynchronous Projection Design

A change-stream or event-driven projector must handle duplicate processing and missed work.

It should maintain durable progress and support reconciliation.

A materialized field is eventually consistent only under a defined and monitored consistency policy.

## Backfill Race

A historical rebuild can overwrite newer live updates if it writes an outdated snapshot.

A robust migration uses source-position tracking, catch-up processing, versioned projection state, or another explicit concurrency strategy.

The cutover must occur only after correctness has been established.

## Exact Counts

A single `$facet` request does not make the count free.

Materialized and indexed fields can reduce the work required for ranking and filtering.

But exact counts may still have nontrivial costs, particularly under changing data and strong consistency requirements.

The product should justify the requirement.

## Final Incident — Expected Judgment

A strong engineer distinguishes the materialization decision from the defective synchronization implementation.

The read-path optimization may be valuable.

The correctness problem is that the application failed to maintain the invariant linking source events to stored totals.

The durable solution needs explicit ownership, safe update handling, idempotency, reconciliation, monitoring, and recovery.

---

# Further Reading

1. **MongoDB — Handle Computed Values**  
   https://www.mongodb.com/docs/v8.0/data-modeling/design-patterns/handle-computed-values/

2. **MongoDB — Compound Indexes**  
   https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-compound/

3. **MongoDB — ESR Guideline**  
   https://www.mongodb.com/docs/v8.0/tutorial/equality-sort-range-guideline/

4. **MongoDB — cursor.skip()**  
   https://www.mongodb.com/docs/v8.0/reference/method/cursor.skip/

5. **MongoDB — `$merge`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/merge/

6. **MongoDB — `$inc`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/update/inc/

7. **MongoDB — Transactions**  
   https://www.mongodb.com/docs/v8.0/core/transactions/

8. **MongoDB — Production Considerations for Transactions**  
   https://www.mongodb.com/docs/v8.0/core/transactions-production-consideration/

9. **MongoDB — Change Streams**  
   https://www.mongodb.com/docs/v8.0/changeStreams/

10. **MongoDB — Change Stream Pre- and Post-Images**  
    https://www.mongodb.com/docs/v8.0/changeStreams/#change-streams-with-document-pre--and-post-images

11. **MongoDB — `$facet`**  
    https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/facet/

12. **MongoDB — Aggregation Pipeline Optimization**  
    https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-optimization/

Cross-reference CS340-L03/L04 for document modeling and indexing foundations, CS345-L01 for query-plan analysis, CS345-L02 for aggregation cardinality, and `production-cases/MONGO-01.md` for the deep-pagination incident.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text id="lsy4u9"
CS345-L03 — PAGINATION & MATERIALIZED DATA
================================================

THREE COSTS
-----------
1. Source acquisition
2. Derived computation
3. Result navigation

Optimize the actual bottleneck.

OFFSET PAGINATION
-----------------
skip(N).limit(20)

Benefits:
  simple page numbers
  arbitrary page jumps

Costs:
  traverses skipped results
  deeper offsets become expensive
  changing data can shift positions

CURSOR PAGINATION
-----------------
Sort:
  completedRevenue DESC
  _id ASC

Cursor:
  lastRevenue
  lastId

Next page:
  revenue < lastRevenue
  OR
  revenue == lastRevenue AND id > lastId

Needs complete deterministic ordering.

Cursor does not freeze dataset.
Changing rank values may move records.

INDEXED RANKING
---------------
{ tenantId: 1,
  completedRevenue: -1,
  _id: 1 }

Supports tenant filter and ranking order.

Deep skip still traverses offset.
Cursor can seek into ordered range.

COMPUTED SORT
-------------
Revenue from $lookup + $group.

MongoDB must calculate candidate totals
before ranking them.

An index on individual event amounts
does not directly index customer totals.

MATERIALIZED FIELD
------------------
Store completedRevenue on customer.

Read:
  simple indexed find/sort.

Write:
  update derived total on source change.

Trade:
  read-time work
  for update/maintenance responsibility.

CORE INVARIANT
--------------
customer.completedRevenue
==
SUM(amountEur for authoritative
    completed customer events)

INCREMENTAL UPDATES
-------------------
Pending -> completed €100:
  revenue +100
  count +1

Completed -> failed €100:
  revenue -100
  count -1

Completed €100 -> €150:
  revenue +50
  count unchanged

Pending €100 -> €150:
  completed revenue unchanged

IDEMPOTENCY
-----------
$inc is atomic for one document.
Blind duplicate $inc is NOT idempotent.

Need:
- transition identity
- expected-state guard
- durable deduplication
- coordinated update semantics

TRANSACTIONS
------------
Source event + customer summary
are two documents.

Multi-document transaction can
coordinate both atomically.

Requires replica set / sharded cluster.
Standalone MongoDB lacks this support.

Transaction does not invent
business idempotency.

ASYNC READ MODEL
----------------
Source events authoritative.

Projection consumer updates summary.

Possible:
  change streams
  durable domain events
  background aggregation

Must handle:
  duplicate delivery
  lag
  restart/recovery
  corrections
  reconciliation

BACKFILL
--------
1. Define source-of-truth boundary.
2. Compute historical summaries.
3. Capture concurrent changes.
4. Catch up safely.
5. Validate.
6. Switch readers.
7. Monitor divergence.

Naive $merge during live writes
can overwrite newer values.

$MERGE
------
Writes aggregation results.
Useful for materialized views.

Not a single atomic
whole-collection cutover.

Failures can leave partial output.

RECONCILIATION
--------------
Recompute authoritative totals.
Compare against stored values.
Repair discrepancies safely.

Approaches:
  full
  sampled
  targeted
  versioned rebuild

HOT DOCUMENT
------------
Frequent updates to one customer
may cause contention.

Indexed revenue updates also
have index-maintenance cost.

Consider buckets/consolidation
when measured write pressure
justifies complexity.

EXACT COUNT
-----------
$facet total count isn't free.

Could use:
  indexed predicate
  cached count
  delayed count
  next-page detection

Product contract matters.

WHEN TO MATERIALIZE
-------------------
Frequent expensive reads.
Repeated historical computation.
Computed sort/filter needed.
Stable aggregate definition.
Manageable update requirements.
Clear consistency contract.

WHEN NOT TO
-----------
Rare inexpensive queries.
Highly complex changing metrics.
Unclear source-of-truth ownership.
Unacceptable maintenance complexity.

DIAGNOSTIC QUESTIONS
--------------------
What is authoritative?
Which values are derived?
Who maintains them?
Can updates be duplicated?
Can updates be missed?
Can a backfill overwrite live data?
How is drift detected?
How is the projection rebuilt?
What staleness is acceptable?
What happens under write contention?

RED FLAGS
---------
"Store the field; problem solved."
"An index makes offset pagination free."
"Cursor pagination gives a snapshot."
"$inc is automatically idempotent."
"Change streams guarantee exactly once."
"Backfills don't race with live writes."
"$merge is a universal atomic rebuild."
"Exact total counts are free."
"Materialized data is always faster overall."

MENTAL MODEL
------------
Materialization moves computation
from reads to maintenance.

The indexed answer is valuable only
if its relationship to authoritative
facts remains trustworthy.

NEXT
----
CS345-L04
The MongoDB Performance Incident Studio
```
