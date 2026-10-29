---
id: CS345-L02
course: CS345
title: "Aggregation Pipelines Under Pressure"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS345-L01
next: CS345-L03
---

# CS345 — MongoDB Production Query Engineering
## Lecture 02: Aggregation Pipelines Under Pressure

*The endpoint returns twenty customers. The database joins two hundred thousand historical events, expands them, calculates thousands of totals, sorts everything, discards almost all the results, and finally hands the application its twenty customers. The payload is tiny. The work is not.*

---

# Part I — Intuition

## 1. The Customer Ranking That Became a Production Incident

Imagine you're working on a SaaS platform serving several thousand business customers.

The administrative interface contains a customer-ranking screen.

Administrators can sort customers by activity, revenue, risk, or other metrics calculated from historical events.

For years, the feature has worked.

The frontend requests twenty customers per page. The API returns twenty compact JSON objects containing customer names, counts, and calculated scores.

Response payloads are small. The application code is straightforward.

Then the historical event collection grows.

What used to take 150 milliseconds begins taking several seconds. Some queries eventually exceed the API timeout.

The frontend team notices that the problem gets worse when administrators sort by calculated revenue or select deep pages.

An engineer opens the MongoDB aggregation pipeline.

It begins with customers, joins historical events, expands the joined records, calculates revenue, sorts the customers, skips previous pages, and limits the result to twenty.

Every stage seems reasonable.

Nothing obviously performs a million-iteration JavaScript loop.

And yet MongoDB is doing an enormous amount of work.

The mistake is assuming that a sequence of reasonable aggregation stages necessarily produces a reasonable total workload.

**A pipeline is not expensive because it has many stages. It is expensive because of how much data each stage must process, retain, and pass onward.**

## 2. An Aggregation Pipeline Is a Data Factory

Imagine a factory processing customer records.

The factory begins with five thousand customers.

One station filters customers belonging to the selected tenant.

Another retrieves their activity history.

A third separates individual events.

A fourth calculates totals.

A fifth sorts the customers by their calculated revenue.

The final station packages twenty customers into the response.

The output contains twenty records, but the intermediate work can be enormous.

The most important question is not how many stages the pipeline contains.

It is what happens to the number of records flowing through those stages.

Some stages reduce cardinality.

Some preserve it.

Others expand it.

### Visual anchor 1 — Cardinality through the factory

```text id="86tqbp"
5,000 customer documents
          |
          | $match tenant
          v
4,000 customer documents
          |
          | $lookup history
          v
4,000 customers with history arrays
          |
          | $unwind history
          v
~164,000 event-level records
          |
          | $group by customer
          v
4,000 customer summaries
          |
          | $sort calculated revenue
          v
4,000 ordered summaries
          |
          | $skip 3,000
          v
1,000 remaining summaries
          |
          | $limit 20
          v
20 response documents
```

These numbers describe our forthcoming laboratory fixture. Actual execution may use optimizations that avoid physically materializing every conceptual intermediate object.

Still, the logical cardinalities explain the work the database must account for.

The crucial moment occurs when four thousand customers become approximately 164,000 event-level records.

That is a cardinality expansion.

Later grouping reduces the count again.

But reducing the count does not erase the work already required.

## 3. `$lookup` Can Hide an Enormous Relationship

A MongoDB `$lookup` performs a left outer join against another collection.

Suppose each customer has thirty-six activity events.

The lookup attaches a history array containing those events.

For most customers, that's modest.

But imagine one unusually active customer with twenty thousand additional events.

Now that customer's history is very large.

Even if the final customer summary contains only total revenue and event count, the original lookup may have needed to retrieve a substantial amount of historical information.

A foreign-key index can make finding the events much more efficient.

But an index doesn't make the events disappear.

If the business calculation genuinely needs every historical event, the operation still has to process the necessary facts.

### 3.1 Indexing and workload reduction are different

An index answers:

> How can I find the relevant event documents efficiently?

A different pipeline design asks:

> Do I need to retrieve and carry all those event documents into the outer pipeline?

These are separate questions.

A foreign index may reduce the cost of locating each customer's events.

A lookup subpipeline may reduce how much information flows back into the outer pipeline by filtering and aggregating related events before returning a compact result.

Both can matter.

## 4. `$unwind` Changes the Number of Records

A lookup normally adds an array field to each input document.

Suppose Alice has three completed events.

The customer document contains an array with three event objects.

An `$unwind` stage produces three logical output documents, one for each event.

The customer fields are repeated across those outputs.

This is useful when calculations need to operate on individual events.

But imagine doing that for thousands of customers.

A relatively compact customer collection becomes a large stream of event-level records.

If the pipeline then performs expensive calculations or grouping across that stream, the work grows accordingly.

### Visual anchor 2 — One customer expands into many rows

```text id="1x8rwr"
BEFORE UNWIND

Alice
  history:
    Event 101 — €40
    Event 102 — €60
    Event 103 — €20

AFTER UNWIND

Alice + Event 101 — €40
Alice + Event 102 — €60
Alice + Event 103 — €20

AFTER GROUP

Alice — 3 events — €120
```

The final result has one row.

The intermediate stream had three.

In our real fixture, those three might become tens of thousands.

## 5. Grouping Doesn't Undo Earlier Work

Suppose the pipeline groups all activity events back into one summary per customer.

The output cardinality falls dramatically.

The developer observes that `$group` produces only four thousand documents.

That sounds manageable.

But the group stage must process the relevant input events to calculate their aggregates.

If it receives 164,000 event-level records, it must account for that input.

Some aggregations can be optimized substantially.

For example, computing a simple count or sum does not require storing every event in an array.

But the operation still has to obtain and process the facts needed for the result.

This is the difference between **the number of output documents** and **the amount of work required to produce them**.

## 6. Calculated Sorting Can Prevent Indexed Ordering

Now suppose we want the twenty customers with the greatest completed-event revenue.

The total revenue isn't stored in the customer document.

It is calculated from the activity history.

The pipeline must obtain the relevant events, calculate each customer's revenue, and then rank customers.

A conventional index on customer name or creation date cannot directly provide an ordering by a value that only exists after the aggregation.

This is why computed sorting can become expensive.

The database may need to calculate thousands of customer totals before knowing which twenty belong at the top.

You cannot generally solve this by moving `$limit: 20` before the calculation.

Doing so would choose twenty customers before knowing which ones have the greatest revenue.

That changes the answer.

**An optimization is invalid if it eliminates work the database needs to determine which records qualify for the result.**

## 7. The Sort Can Be Optimized Without Making the Whole Pipeline Cheap

MongoDB supports an important optimization.

When `$sort` is followed by `$limit`, and no intervening stage changes the number of documents, the optimizer can combine them.

Instead of retaining every sorted item, MongoDB can maintain only the top number required.

That can reduce sorting memory.

But consider deep pagination.

The application requests page 151, with twenty customers per page.

The skip is three thousand.

The sort must still identify enough top-ranked customers to discard the first three thousand and return the next twenty.

MongoDB can optimize the sort to maintain the top 3,020 candidates.

That's better than retaining the entire sorted set.

But it's much more work than maintaining only twenty candidates.

And it doesn't avoid calculating revenue for all customers who might belong in the ranking.

### Visual anchor 3 — Top-K still grows with offset

```text id="9zpc2o"
PAGE 1

Sort by calculated revenue
Keep top 20
Return 20


PAGE 151

Sort by calculated revenue
Keep top 3,020
Skip 3,000
Return 20
```

The optimizer can improve the implementation without changing the fundamental cost of deep-offset pagination.

## 8. What Should We Optimize First?

Imagine looking at the pipeline.

You could add indexes.

You could move filters earlier.

You could change the lookup to aggregate events inside the foreign collection.

You could remove unnecessary document fields.

You could reconsider how the result is sorted.

You could store a derived revenue total directly on the customer document.

Some options preserve the same data model.

Others introduce new architectural responsibilities.

The correct order is to understand where the work is happening.

First, measure cardinality through the pipeline.

Then inspect which operations use indexes.

Determine whether the lookup retrieves more data than the calculation needs.

Inspect whether sorting requires all computed summaries.

Check whether any stage uses excessive memory or spills to disk.

Only then decide which intervention is appropriate.

### A tiny comprehension check

A pipeline takes 4,000 customer documents, joins their histories, and unwinds them into 160,000 event-level records.

Then it groups them back into 4,000 customer summaries and returns twenty.

Would moving `$limit: 20` immediately after the initial customer match produce the same highest-revenue customers?

No.

It would select twenty customers before calculating the ranking.

Could aggregating history inside the lookup reduce the size of the intermediate outer stream?

Yes.

But it would still need to process the underlying events required to calculate the totals.

That distinction is the heart of this lecture.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Diagnose the Pipeline You Actually Execute

In CS345-L01, we learned to inspect MongoDB execution plans.

Now we're investigating aggregation pipelines.

A common mistake is to look at the source pipeline and assume MongoDB literally executes every stage in exactly that written form.

MongoDB has an aggregation optimizer.

It can move certain filters, combine adjacent operations, and transform specific stage combinations into more efficient execution structures.

The pipeline you wrote is a description of the requested transformation.

The optimized physical execution may differ.

### 9.1 Why this matters

Consider the following conceptual sequence:

First calculate a new field.

Then filter documents using an unrelated original field.

MongoDB may be able to move that filter before the calculation, because the filter doesn't depend on the calculated field.

Similarly, certain `$lookup`, `$unwind`, and `$match` combinations can be coalesced.

Therefore, the correct question is not merely:

"Could I move this `$match` earlier in the source code?"

It is:

"Did MongoDB already move it, and would changing the source pipeline materially alter the execution?"

### 9.2 The investigation tools

For aggregation queries, use:

`db.collection.explain("executionStats").aggregate(pipeline)`

The explain result can reveal the optimized plan and relevant stage execution information.

The exact structure depends on MongoDB version and execution engine.

Some operations appear in a top-level `stages` array.

Others may be represented inside a query-plan tree, including slot-based execution stages.

Do not assume every version reports the same nested JSON structure.

For production latency, complement explain with normal application measurements.

Explain ignores existing plan-cache entries and is not a complete measurement of application-observed latency.

## 10. Cardinality Is the First Performance Budget

For every aggregation stage, ask three questions.

How many documents enter?

How many documents leave?

How much work is required per input document?

Consider common stages.

**`$match`** usually reduces or preserves the number of documents.

**`$project`** and **`$set`** generally preserve document count while changing fields or calculating values.

**`$unwind`** may increase the count dramatically, reduce it, or preserve empty arrays depending on its configuration.

**`$group`** reduces documents into groups, often producing far fewer outputs than inputs.

**`$sort`** preserves count but may need to process and retain substantial input before yielding results.

**`$limit`** reduces output count.

**`$skip`** discards earlier results in the stream.

**`$lookup`** ordinarily preserves the number of outer documents while attaching arrays of matched foreign documents, although subsequent unwind stages or optimizer transformations may change the effective stream.

### 10.1 A stage can be expensive without increasing document count

Suppose `$lookup` outputs four thousand customer documents.

The count hasn't changed.

But each document now contains historical activity data.

A customer with twenty thousand events may produce an enormous joined array.

Therefore, measuring only document count isn't sufficient.

You must also consider document size, foreign-document examinations, memory, and how much data is transported between stages.

### 10.2 Work before cardinality reduction still matters

Suppose an expensive calculation processes one million records.

Then `$group` produces one summary.

The final result has one document.

That doesn't mean the calculation was cheap.

Likewise, a `$limit` placed after a blocking or expansive operation may not reduce much of the work performed earlier.

## 11. `$lookup`: Finding Related Data Versus Processing Related Data

MongoDB supports equality joins using `localField` and `foreignField`.

Imagine customers containing `_id`, and activity events containing `customerId`.

A lookup can attach each customer's events to their customer document.

The foreign collection should ordinarily have a suitable index on `customerId` for this kind of equality lookup.

Without that index, repeated foreign collection scans can become extremely expensive.

### 11.1 The indexed lookup is only the beginning

Suppose the event collection contains two hundred thousand records.

A customer has thirty-six events.

An index can locate those events efficiently.

But if the query needs only the count and sum of completed events, retrieving all thirty-six complete event objects into the outer pipeline may be unnecessary.

The event documents may contain descriptions, metadata, payloads, and other fields irrelevant to the calculation.

The system is paying to carry information it doesn't need.

### 11.2 Lookup subpipelines

MongoDB allows a `$lookup` stage to contain a pipeline executed against the foreign collection.

For example, the lookup can filter for completed events and group them into a summary.

Instead of returning dozens or thousands of event objects, it may return one summary object.

This changes the shape of the intermediate result.

The outer customer pipeline can then calculate the ranking using compact per-customer summaries.

### 11.3 The work hasn't disappeared

There's an important qualification.

The foreign aggregation still has to inspect the relevant events.

A lookup subpipeline isn't automatically faster than a simple equality lookup followed by an optimized unwind and group.

It may involve different execution-engine capabilities or repeated subpipeline execution for many outer documents.

The correct comparison is empirical.

We should inspect foreign index usage, documents examined, intermediate cardinality, and overall latency.

**Reducing intermediate data volume is useful. Reducing necessary underlying work is a separate achievement.**

## 12. Indexed Versus Unindexed Lookup

Suppose we join four thousand customers to an events collection containing two hundred thousand documents.

If MongoDB can efficiently locate events by customer ID, the lookup can be reasonably selective.

Without a suitable foreign index, the database may repeatedly search a large part of the events collection.

The total potential work becomes enormous.

For this reason, checking foreign index availability is one of the first steps in `$lookup` diagnosis.

### 12.1 What explain can reveal

Modern MongoDB explain output may expose lookup-specific statistics such as:

- `totalDocsExamined`
- `totalKeysExamined`
- `collectionScans`
- `indexesUsed`
- `executionTimeMillisEstimate`

These fields help identify whether the foreign collection was accessed through an index and how much work occurred.

Not every query plan exposes them at the same JSON path.

Some lookup operations may use optimized slot-based execution representations.

Use the actual explain output from the running MongoDB version.

### 12.2 Why a foreign index may not be enough

An indexed lookup can still be expensive if each customer has huge history.

Consider one customer with twenty thousand events.

An efficient index identifies those events.

But the calculation may still need to examine twenty thousand records.

An index helps locate data.

It doesn't change the fact that the business question requires processing historical activity.

At some point, the architecture may need a maintained summary.

That is a different decision, explored in CS345-L03.

## 13. `$lookup` and `$unwind` Coalescence

This is a particularly important optimizer behavior.

Suppose a pipeline performs `$lookup`, immediately unwinds the lookup result, and then filters the joined records.

MongoDB may combine these operations internally.

For example, it can coalesce `$unwind` into `$lookup`.

If a following `$match` filters a subfield of the joined array, MongoDB may coalesce that filter as well.

This can avoid materializing a large joined array only to immediately expand and filter it.

### 13.1 Why the written pipeline can mislead

A developer sees:

`$lookup → $unwind → $match`

They assume MongoDB first builds every full history array, then expands it, then filters individual events.

But the optimized execution may not literally do that.

The source code describes logical operations.

The optimizer may implement them in a more efficient combined form.

### 13.2 What this means for diagnosis

Do not claim that moving a `$match` before or inside a lookup is necessarily an optimization without inspecting the actual plan.

MongoDB may already perform an equivalent transformation.

Conversely, some transformations cannot be pushed down because they depend on values calculated later or would change semantics.

The correct investigation distinguishes:

- Logical stage order.
- Optimizer transformations.
- Physical execution behavior.

This is one of the reasons production query tuning requires explain evidence rather than stylistic opinions about pipeline formatting.

## 14. Filtering Early, but Correctly

Filtering irrelevant source documents early is often beneficial.

Suppose our ranking concerns Mercury's customers only.

Filtering the customer collection by `tenantId: "mercury"` before joining history can reduce the number of customers requiring lookup work.

But the optimizer may already be able to move that independent filter earlier.

Use explain to confirm.

### 14.1 A predicate may depend on joined data

Suppose we want customers whose total completed revenue exceeds €500.

That value doesn't exist until we've processed their activity history.

We cannot simply apply the revenue filter before computing revenue.

Likewise, filtering the underlying events before grouping can change the aggregate.

If the requirement is total historical revenue, excluding older events is wrong.

If the requirement is revenue from the last ninety days, filtering older events is correct.

### 14.2 Don't optimize away business meaning

A pipeline optimization is valid only if it preserves the intended result.

This sounds obvious.

But in production, developers frequently move `$limit` or `$match` earlier without proving that the resulting query remains equivalent.

A dramatically faster query returning the wrong ranking is not an improvement.

## 15. `$unwind`: How Fanout Becomes Expensive

Suppose each customer has thirty-six events.

Unwinding produces roughly thirty-six event-level records for each customer.

For four thousand customers, that is more than a hundred thousand intermediate records.

Then our unusually active customer contributes another twenty thousand.

The result is a large stream.

### 15.1 Repeated parent fields

Each unwound output conceptually carries the customer document's other fields alongside one event.

If the customer record contains large descriptions or metadata fields, the repeated logical structure can become costly.

Projecting or removing irrelevant fields may reduce the amount of data carried through subsequent processing.

But MongoDB can already perform some projection optimizations.

Again, inspect the executed plan before attributing improvements to manually moving every `$project`.

### 15.2 Preserve-null semantics

Suppose the business report must include customers with no completed activity.

An inner-style unwind or a later match requiring completed events can eliminate those customers.

Using `preserveNullAndEmptyArrays` can preserve customers without joined history.

But a subsequent filter on event fields may remove them again.

A correct summary must deliberately represent zero-activity customers.

The alternative is to aggregate inside the lookup and default missing summaries to zero.

This is often easier to reason about.

The important point is that performance changes must preserve zero-activity semantics.

## 16. `$group`: Aggregate State and Memory

A `$group` stage collects input documents into groups.

The amount of memory required depends on the number of groups, the accumulators, and the values retained.

A group calculating a numeric sum and count per customer has a different memory profile from one collecting every event into an array.

### 16.1 Sum and count

For a simple count and total, the group needs to maintain aggregate state.

It doesn't need to retain every individual event.

This is generally more efficient than collecting all events and calculating the total later in application code.

### 16.2 The danger of `$push`

Suppose we use `$push` to collect every event into a customer history array.

For an ordinary customer, that may be acceptable.

For a customer with twenty thousand events, the array becomes large.

The resulting document can approach MongoDB's BSON document-size limit.

Even if the final API only needs a total, carrying the whole history is wasteful.

### 16.3 Group cardinality

A group by customer produces approximately one output per distinct customer.

A group by customer and event date may produce many more outputs.

A group by a nearly unique event identifier may preserve almost the original cardinality.

Therefore, the number of output groups is an important memory consideration.

## 17. Blocking Stages and Memory Pressure

Some pipeline stages can produce output incrementally.

Others must process substantial input before producing results.

A sort by a computed revenue field is a classic blocking operation.

The database needs to establish the ordering before returning the correct ranked rows.

A group may also require substantial intermediate state.

### 17.1 Memory and spilling

MongoDB aggregation stages such as `$sort` and `$group` can be subject to memory limits.

In MongoDB 8.0, the `allowDiskUseByDefault` setting controls whether eligible operations exceeding the relevant 100 MB per-stage memory threshold may spill to temporary disk files by default.

Individual aggregate operations can override this behavior with `allowDiskUse`.

Spilling can prevent a query from failing because of memory pressure.

But temporary disk I/O may be expensive.

It can also create storage pressure.

### 17.2 Allowing disk use doesn't fix an inefficient pipeline

If a query unnecessarily processes millions of documents, enabling disk spilling doesn't eliminate those documents.

It merely allows certain stages to use disk-backed temporary storage when necessary.

This can be appropriate for unavoidable analytical workloads.

It is not a substitute for reducing unnecessary cardinality or improving the data model.

### 17.3 Not every stage can spill

`$facet` has particularly important limitations.

Its output document is subject to a 100 MB stage-specific restriction that `allowDiskUse` cannot bypass.

The final output document is also subject to MongoDB's 16 MiB BSON document limit.

Therefore, enabling disk use is not a universal response to aggregation memory failures.

## 18. Sorting by Derived Fields

Return to our ranking.

The customer's total revenue is calculated from completed activity events.

The customer collection doesn't contain that total.

Consequently, an ordinary index on customer creation date or name cannot provide the desired order by calculated revenue.

The pipeline needs to compute revenue before correctly ranking the customers.

### 18.1 Why an early limit changes the answer

Suppose we have four thousand Mercury customers.

We want the twenty highest-revenue customers.

If we apply `$limit: 20` before the lookup, we examine only twenty arbitrary or previously ordered customers.

We then calculate their revenue.

That returns the highest-revenue customers among those twenty.

It does not return the twenty highest-revenue customers across the entire tenant.

The query is faster because it answers a smaller, different question.

### 18.2 A sort may remain necessary after optimization

Even if we aggregate activity inside the lookup, the revenue total still doesn't exist as an indexed field in the customer collection.

The outer pipeline must calculate a total for each candidate customer and determine the ranking.

Reducing intermediate event arrays is helpful.

It does not automatically remove the expensive global ranking problem.

### 18.3 The architectural escape hatch

If the application needs this ranking frequently, the system could maintain a derived revenue field on each customer document.

Then a compound index might support tenant filtering and revenue sorting.

But now the application must keep the stored revenue correct when activity events change.

That introduces synchronization, backfill, and consistency responsibilities.

We will investigate that trade-off in CS345-L03.

## 19. `$sort`, `$skip`, and `$limit`

MongoDB can coalesce `$sort` and `$limit` when no intervening cardinality-changing operation prevents the optimization.

This allows a top-K sort rather than retaining the full sorted set.

### 19.1 Deep offsets increase K

For:

`$sort → $skip: 3000 → $limit: 20`

MongoDB can optimize the sorting requirement to keep the top 3,020 values.

Then it discards the first three thousand.

This reduces sort memory compared with retaining every sorted result, but it does not make the skip free.

### 19.2 Input processing remains

Even if the sort only retains a bounded number of candidates, it may still need to examine every eligible customer summary.

And those summaries may each require aggregating historical events.

The optimization reduces sorting-state size.

It doesn't necessarily reduce upstream computation.

### 19.3 Deep pagination and computed sorting are a nasty combination

A deep page requires a large K.

A computed sort key requires processing all candidate entities.

A join-derived key may require substantial historical-event work per entity.

These costs multiply into a workload that can become much more expensive than the final response size suggests.

This is precisely why storing frequently queried derived values can become attractive.

But before accepting that trade-off, verify that the computed value is genuinely the bottleneck.

## 20. `$facet`: Convenience with Hidden Costs

The administrative interface often needs two things:

The twenty customers for the selected page.

The total number of matching customers, so the UI can display pagination controls.

A developer may use `$facet` to compute both in one aggregation.

For example, one branch sorts, skips, and limits the results.

Another counts them.

This can be convenient.

But `$facet` doesn't make the count free.

### 20.1 The count branch still needs its input

Suppose the pipeline calculates completed revenue for four thousand customers and filters to those above a threshold.

The count branch needs to know how many customers qualify.

The page branch needs the correct ranked slice.

Both depend on the upstream calculation.

The pipeline may still need to process all relevant customer histories.

A single network round trip does not mean a single cheap operation.

### 20.2 Facet placement matters

If `$facet` is the first stage, it cannot rely on an earlier `$match` to narrow the collection.

Placing a suitable indexed match before the facet can reduce its input.

But if that match depends on calculated values, it cannot be moved ahead of the calculation without changing the meaning.

### 20.3 The memory trap

Each `$facet` output document must remain within its stage-specific memory limit.

`allowDiskUse` doesn't make the facet output arbitrarily large.

And the final output document must still fit within the BSON document size limit.

A facet branch returning enormous arrays can fail even when other aggregation stages are allowed to spill.

### 20.4 Separate queries are sometimes better

One query for the current page and another for the count can be reasonable.

That doesn't automatically make the system more expensive.

The two operations may have different optimal access paths.

The count may be cached, delayed, approximated, or omitted if the product doesn't genuinely require an exact total.

But if both operations must reflect the same snapshot, executing separate queries introduces consistency considerations.

The decision follows product requirements and measured execution costs.

## 21. Stage Order Versus Optimizer Rewriting

Let's examine a common misconception.

A developer sees a `$match` after `$project` and declares the pipeline inefficient.

But if the match doesn't depend on the projected values, MongoDB may move it earlier automatically.

Similarly, `$lookup` followed by `$unwind` can be coalesced.

This means the visible source pipeline may look inefficient while the optimized execution avoids some obvious waste.

### 21.1 Don't fight the optimizer blindly

The right approach is:

First understand the logical semantics.

Then inspect the optimized plan.

Identify which transformations MongoDB already performed.

Finally, focus on work that remains expensive.

Rearranging source stages may improve readability without changing runtime behavior.

That's still useful, but it isn't necessarily a performance improvement.

### 21.2 Sometimes optimizer transformations are constrained

A `$match` that depends on a field calculated by `$addFields` cannot simply move before that calculation.

A `$limit` cannot cross a grouping operation if doing so would change which groups are considered.

A sort by a computed value cannot generally use an index on a different stored field.

These are semantic limitations, not planner failures.

## 22. Large Customer Histories and Document Limits

Our laboratory includes one unusually active customer with more than twenty thousand historical events.

That customer is intended to expose skew.

Most customers have a few dozen events.

One has an enormous history.

### 22.1 Average cardinality hides tail behavior

Suppose the average customer has forty events.

That sounds manageable.

But an extreme customer can produce substantially more work and much larger intermediate objects.

This is similar to database query performance problems involving a few unusually large tenants.

Averages can hide the expensive tail.

### 22.2 A lookup array can become too large

A standard lookup adds an array of matching foreign documents.

If that array and the surrounding document become too large, MongoDB's document-size restrictions may become relevant.

Coalescing lookup with unwind can avoid materializing some large intermediate structures.

Using a lookup subpipeline that returns an aggregate can also reduce result size.

But the correct design depends on the actual required output.

If the API really needs the entire history, it may require pagination or a separate history endpoint rather than embedding everything into one customer response.

### 22.3 Unbounded relationships are architectural signals

A history collection that grows indefinitely often deserves separate access patterns.

The customer profile may need a compact summary.

The history page may need paginated events.

The analytical system may need historical aggregates.

Trying to serve all three needs through one universal lookup can become expensive and difficult to maintain.

This is a data-modeling issue, not merely a pipeline syntax problem.

## 23. Production Investigation: MONGO-02

Let's assemble the diagnostic process around the growing customer history.

The endpoint used to load quickly.

Now latency grows as activity history accumulates.

The response still contains a compact customer summary.

### Step 1 — Identify the exact output contract

Does the API need every historical event?

Or only a count, sum, and latest event?

Does it include customers with zero activity?

What date and status restrictions apply?

You cannot optimize safely without those semantics.

### Step 2 — Capture the complete pipeline

Record the actual stages, parameters, collation, pagination settings, and relevant tenant.

Don't rely on a simplified reconstruction.

### Step 3 — Measure cardinality

Count documents entering and leaving important conceptual stages.

Pay particular attention to lookup fanout and unwind expansion.

Use a controlled dataset or staging environment to avoid burdening production.

### Step 4 — Inspect foreign index usage

Check indexes on the activity collection.

Review lookup execution statistics when available.

A missing foreign-key index can cause enormous repeated scan work.

### Step 5 — Identify blocking operations

Examine group and sort behavior.

Look for memory usage and disk-spill evidence.

Determine whether the final sort key is computed from history.

### Step 6 — Inspect optimizer transformations

Check whether MongoDB has moved filters or coalesced lookup-related stages.

Don't optimize a textual stage ordering that the engine has already transformed.

### Step 7 — Compare alternatives

Try filtering earlier where semantics permit.

Try aggregating inside the lookup.

Try a different query direction if the result contract allows it.

Avoid returning unnecessary historical arrays.

### Step 8 — Verify results

Compare the complete logical output of the original and improved pipelines.

Check counts, amounts, customers with zero activity, ties, and deep pages.

### Step 9 — Measure representative workload

Explain output helps identify work.

Application latency, CPU, memory, disk activity, and query behavior under realistic conditions establish operational impact.

### Step 10 — Decide whether the data model needs to change

If every request still recomputes large historical aggregates, further pipeline optimization may have diminishing returns.

That is when a maintained derived field or summary collection becomes worth considering.

But materialization introduces correctness obligations.

That decision belongs in the next lecture.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — Cardinality Expansion

A pipeline starts with 2,000 customers.

Each customer has an average of 50 activity events.

The pipeline performs a lookup and unwinds the event arrays.

Roughly how many event-level records may flow into the next stage?

What qualifications apply to that estimate?

## Question 2 — The Indexed Lookup

A lookup uses an index on `customerId`.

The query is still slow for a customer with 30,000 historical events.

Why doesn't the index solve the entire problem?

## Question 3 — The Early Limit

A pipeline must return the twenty customers with the greatest revenue calculated from their histories.

Someone proposes limiting the customer collection to twenty before joining history.

Why is that generally incorrect?

## Question 4 — Optimizer Coalescence

A pipeline contains `$lookup`, `$unwind`, and `$match` on a joined field.

Does the source pipeline prove MongoDB materializes the entire joined array before filtering?

How would you verify?

## Question 5 — Grouping and Memory

Two group stages each process 100,000 events.

One calculates a count and numeric sum per customer.

The other pushes every event into a customer-history array.

Why might their memory requirements differ dramatically?

## Question 6 — Deep Pagination

A pipeline sorts customers by computed revenue, skips 5,000, and returns twenty.

What top-K optimization can MongoDB perform?

Why does the deep page remain expensive?

## Question 7 — Facet Counts

A `$facet` produces a page of twenty results and an exact total count.

The UI receives only a small response.

Does that prove the count branch was cheap?

What memory restriction applies to `$facet`?

## Question 8 — `allowDiskUse`

An aggregation exceeds an eligible stage's memory limit.

An engineer enables disk spilling.

Does that fix inefficient join cardinality?

Can `$facet` spill its output beyond its stage-specific limit?

## Question 9 — Zero-Activity Customers

A revenue report must include customers with no completed events.

An engineer moves `$match: {"history.status": "completed"}` after `$unwind`.

What correctness problem could this introduce?

## Question 10 — The Production Diagnosis

A customer ranking endpoint becomes slower as historical events accumulate.

Describe the evidence you'd collect before recommending that revenue totals be stored directly on customer documents.

---

# Solutions and Discussion

## Solution 1 — Cardinality Expansion

Approximately 100,000 event-level records if each customer contributes fifty events.

The actual count depends on distribution, empty arrays, filtering, and unwind options.

The average also hides high-cardinality outliers.

## Solution 2 — Indexed Lookup

The index reduces the cost of locating the customer's events.

It doesn't remove the need to process thirty thousand events if the calculation requires them.

Filtering, aggregation, or maintaining a derived summary may reduce higher-level work.

## Solution 3 — Early Limit

The operation would choose twenty customers before calculating the global revenue ranking.

It would return the best customers among that arbitrary subset rather than the best customers overall.

The result contract would change.

## Solution 4 — Optimizer Coalescence

No.

MongoDB can coalesce lookup and unwind, and sometimes the following match.

Inspect the optimized execution plan to determine what transformations occurred.

## Solution 5 — Group Memory

Numeric count and sum accumulators require compact aggregate state.

Pushing every event into arrays retains much more data and can approach document-size limits.

The number of groups and retained values determine memory pressure.

## Solution 6 — Deep Pagination

MongoDB can combine the sort and limit to retain the top 5,020 values.

But it may still need to calculate revenue for all candidate customers.

The large skip also increases the top-K requirement.

## Solution 7 — Facet Counts

No.

The count branch may require processing the entire qualifying input.

`$facet` has a stage-specific 100 MB output-document limit that cannot be bypassed with `allowDiskUse`.

The final result is also subject to the BSON document-size limit.

## Solution 8 — Disk Spilling

Disk spilling allows certain stages to exceed memory thresholds by writing temporary files.

It doesn't reduce unnecessary processing.

`$facet` cannot use disk spilling to bypass its output limit.

## Solution 9 — Zero-Activity Customers

Filtering joined events after unwind can remove customers without completed events.

A correct report must deliberately preserve and represent zero-activity customers.

A lookup subpipeline returning summaries and applying zero defaults can simplify this.

## Solution 10 — Production Diagnosis

Capture the actual pipeline and output contract.

Measure intermediate cardinalities.

Inspect foreign index usage, lookup work, grouping, sorting, memory, and spills.

Compare semantically equivalent pipeline strategies.

Verify results.

Then determine whether recomputing historical aggregates on every request remains too expensive.

Only after that evidence should you consider maintaining derived values.

---

# The Mental Model Worth Keeping

An aggregation pipeline is a data-processing system.

Every stage has an input cardinality, output cardinality, and cost per input.

Lookup can attach enormous histories.

Unwind can expand the stream.

Group can reduce output count without erasing earlier work.

Sort can require global knowledge of calculated values.

Skip can make deep pages increasingly expensive.

Facet can duplicate analytical work and introduce memory constraints.

**Measure the data flowing through the pipeline, not merely the documents returned to the application.**

The correct optimization preserves business semantics while reducing unnecessary work.

---

# Next Lecture — CS345-L03: Pagination, Derived Fields, and Materialized Data

Our investigation has exposed a difficult architectural problem.

The customer ranking depends on revenue calculated from historical events.

Every time an administrator sorts by revenue, MongoDB must obtain enough historical information to calculate the ranking.

We can improve indexing and aggregation structure.

But the derived revenue value still isn't stored in an indexable form on the customer document.

What if we maintained the total directly?

Then the ranking could use an ordinary compound index.

A twenty-result page might become dramatically cheaper.

But every event update, refund, correction, or backfill could change the stored total.

The database would now contain a derived value that must remain synchronized with its source facts.

In CS345-L03, we'll investigate that trade-off.

We'll compare offset and cursor pagination, computed and materialized sorts, and the operational consequences of keeping derived data correct.

*The spoken lecture ends here. The following investigations require a disposable MongoDB environment and should be performed independently before reviewing the diagnostic notes.*

---

# Optional Practical Lab — Aggregation Pipeline Forensics

## Lab Contract

The workshop uses a synthetic MongoDB database with:

- 5,000 customers.
- 200,000 activity events.
- Two tenants.
- One unusually active customer.
- Completed, pending, and failed events.
- Some customers with no completed events.

The fixture is designed to expose both ordinary and highly skewed history distributions.

The comparison is not guaranteed to produce one particular latency ratio on every machine.

MongoDB version, available memory, indexes, execution engine, and cache state can affect timing.

The required outcome is a defensible explanation supported by actual execution evidence.

**Prediction → Evidence → Diagnosis → Change → Verification → AI Review.**

Do not read the solution notes before your first independent attempt.

## 1. Start MongoDB

Reuse the disposable MongoDB 8.0 container from CS345-L01 if it exists.

Otherwise:

```bash id="xcxvm2"
docker run --name cs345-mongo \
  -p 27028:27017 \
  -d mongo:8.0
```

Connect with:

```bash id="lae8zm"
docker exec -it cs345-mongo mongosh cs345
```

Use only the disposable `cs345` database.

This lab creates separate `pipeline_customers` and `pipeline_events` collections, leaving the previous lecture's booking collection untouched.

## 2. Create the Dataset

Reset the dedicated collections.

```javascript id="mk26cq"
const lab = db.getSiblingDB("cs345");

lab.pipeline_customers.drop();
lab.pipeline_events.drop();

const customers = lab.pipeline_customers;
const events = lab.pipeline_events;
```

### Generate customers

Customer IDs one through four thousand belong to Mercury.

The remaining one thousand belong to Nimbus.

```javascript id="clte5m"
const customerDocs = [];

for (let id = 1; id <= 5000; id++) {
  customerDocs.push({
    _id: id,
    tenantId: id <= 4000 ? "mercury" : "nimbus",
    name: `Customer ${id}`,
    tier: id % 10 === 0 ? "enterprise" : "standard",
    createdAt: new Date(
      Date.UTC(2024, 0, 1) + id * 86_400_000
    )
  });
}

customers.insertMany(customerDocs);

print("Customers:", customers.countDocuments({}));
```

Expected count: 5,000.

### Generate historical events

Every customer receives thirty-six normal events.

Customer 733 receives an additional twenty thousand events.

The final collection contains exactly 200,000 events.

A subset of customers deliberately has no completed events.

```javascript id="e14ce9"
const totalEvents = 200000;
const eventBatchSize = 1000;

for (
  let start = 1;
  start <= totalEvents;
  start += eventBatchSize
) {
  const batch = [];

  for (
    let eventId = start;
    eventId < start + eventBatchSize &&
    eventId <= totalEvents;
    eventId++
  ) {
    const customerId =
      eventId <= 180000
        ? ((eventId - 1) % 5000) + 1
        : 733;

    const status =
      customerId % 17 === 0
        ? "failed"
        : eventId % 10 < 7
          ? "completed"
          : eventId % 10 < 9
            ? "pending"
            : "failed";

    batch.push({
      _id: eventId,
      customerId,
      tenantId:
        customerId <= 4000 ? "mercury" : "nimbus",

      status,
      amountEur: 25 + (eventId % 120),

      occurredAt: new Date(
        Date.UTC(2025, 0, 1) + eventId * 1000
      ),

      payload: `Event-${eventId}-` + "x".repeat(60)
    });
  }

  events.insertMany(batch, { ordered: false });
}

print("Events:", events.countDocuments({}));
```

### Verify the fixture

Run:

```javascript id="8s6pvh"
printjson({
  customers: customers.countDocuments({}),
  events: events.countDocuments({}),
  mercuryCustomers:
    customers.countDocuments({ tenantId: "mercury" }),
  whaleEvents:
    events.countDocuments({ customerId: 733 })
});
```

Expected values:

| Measurement | Expected |
|---|---:|
| Customers | 5,000 |
| Events | 200,000 |
| Mercury customers | 4,000 |
| Customer 733 events | 20,036 |

Also check a customer with no completed events:

```javascript id="x2v45t"
printjson({
  customer17Completed:
    events.countDocuments({
      customerId: 17,
      status: "completed"
    })
});
```

Expected result: zero.

### Create the initial foreign index

```javascript id="37ntrh"
events.createIndex(
  { customerId: 1 },
  { name: "events_customer" }
);
```

This supports equality lookup by customer ID.

Do not add the compound status index yet.

---

# Experiment A — The Expensive Ranking

## Starting Symptom

The administrator requests page 151 of Mercury's customers, ranked by completed-event revenue.

The page size is twenty.

The query must include customers with zero completed events.

### The initial pipeline

The following pipeline joins full event histories, unwinds them, calculates totals, sorts, and paginates.

It is deliberately written in a way that invites investigation.

```javascript id="xvo32a"
const badPipeline = [
  {
    $lookup: {
      from: "pipeline_events",
      localField: "_id",
      foreignField: "customerId",
      as: "history"
    }
  },
  {
    $unwind: {
      path: "$history",
      preserveNullAndEmptyArrays: true
    }
  },
  {
    $match: {
      tenantId: "mercury"
    }
  },
  {
    $group: {
      _id: "$_id",
      name: { $first: "$name" },

      completedCount: {
        $sum: {
          $cond: [
            { $eq: ["$history.status", "completed"] },
            1,
            0
          ]
        }
      },

      totalRevenue: {
        $sum: {
          $cond: [
            { $eq: ["$history.status", "completed"] },
            "$history.amountEur",
            0
          ]
        }
      }
    }
  },
  {
    $sort: {
      totalRevenue: -1,
      _id: 1
    }
  },
  { $skip: 3000 },
  { $limit: 20 }
];
```

### Task A1 — Predict

Before executing the pipeline, answer:

How many customers enter the lookup?

How many belong to Mercury?

Roughly how many event-level records will the unwind produce before grouping?

What happens to customers who have only failed events?

Can the final sort use the existing customer ID index to order by `totalRevenue`?

Can an early `$limit: 20` preserve the correct ranking?

### Task A2 — Run the pipeline

```javascript id="camvq3"
const badResults = customers.aggregate(
  badPipeline,
  {
    allowDiskUse: true,
    maxTimeMS: 120000
  }
).toArray();

printjson(badResults);
```

Record the returned customer IDs and calculated totals.

Don't assume the runtime will match a particular time estimate.

### Task A3 — Inspect execution statistics

```javascript id="v6wt73"
const badExplain = customers
  .explain("executionStats")
  .aggregate(badPipeline, {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

printjson(badExplain);
```

Inspect the optimized pipeline and available execution statistics.

Look for:

- Initial collection access.
- Lookup index usage.
- Document and key examinations.
- Lookup and unwind optimization.
- Grouping.
- Sorting.
- Any spill-related information.

Do not assume every stage appears as an independent top-level JSON object.

### Acceptance criteria

You can explain the physical workload behind the twenty-document result.

You can identify which parts are necessary and which may be excessive.

---

# Experiment B — Measure Intermediate Cardinality

## Objective

Reconstruct the logical number of records at major pipeline boundaries.

Instead of relying only on the final response, run controlled counts for pipeline prefixes.

### Initial customer count

```javascript id="5l9wl6"
printjson(
  customers.aggregate([
    { $count: "customers" }
  ]).toArray()
);
```

### Mercury customer count

```javascript id="bkf4z4"
printjson(
  customers.aggregate([
    { $match: { tenantId: "mercury" } },
    { $count: "customers" }
  ]).toArray()
);
```

### Event-level cardinality after lookup and unwind

Run a pipeline that limits the source to Mercury before joining, then counts the unwound event stream.

```javascript id="e87f3a"
const expandedCount = customers.aggregate([
  { $match: { tenantId: "mercury" } },

  {
    $lookup: {
      from: "pipeline_events",
      localField: "_id",
      foreignField: "customerId",
      as: "history"
    }
  },

  { $unwind: "$history" },

  { $count: "eventLevelRows" }
], {
  allowDiskUse: true,
  maxTimeMS: 120000
}).toArray();

printjson(expandedCount);
```

### Task B1 — Verify the expected count

Mercury has 4,000 customers.

Each has thirty-six normal events.

Customer 733 has twenty thousand additional events.

The conceptual unwound event count should be 164,000.

Verify the actual result.

### Task B2 — Understand the optimizer

Inspect explain for this prefix.

Did MongoDB combine `$lookup` and `$unwind`?

If so, explain why the logical count remains meaningful even when the intermediate arrays are not physically materialized in the naive way.

### Acceptance criteria

You can distinguish logical pipeline cardinality from physical materialization.

You understand why the optimizer may reduce some intermediate allocation without eliminating the need to process relevant events.

---

# Experiment C — Aggregate Inside the Lookup

## Objective

Return compact customer-level summaries rather than full histories into the outer pipeline.

The optimized candidate begins by filtering Mercury customers.

For each customer, the lookup retrieves completed events and aggregates them into a summary.

The outer pipeline then sorts the customer summaries.

### Candidate pipeline

```javascript id="3rouui"
const improvedPipeline = [
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
            totalRevenue: { $sum: "$amountEur" }
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

      totalRevenue: {
        $ifNull: [
          { $arrayElemAt: ["$summary.totalRevenue", 0] },
          0
        ]
      }
    }
  },

  {
    $project: {
      name: 1,
      completedCount: 1,
      totalRevenue: 1
    }
  },

  {
    $sort: {
      totalRevenue: -1,
      _id: 1
    }
  },

  { $skip: 3000 },
  { $limit: 20 }
];
```

### Task C1 — Predict the improvement

What is the grain of the foreign lookup result?

How many outer customer summaries should exist before sorting?

Does the new pipeline still process historical events?

Does it preserve customers with zero completed events?

Can its final computed revenue sort use an ordinary customer index?

### Task C2 — Run and compare

```javascript id="r55a3o"
const improvedResults = customers.aggregate(
  improvedPipeline,
  {
    allowDiskUse: true,
    maxTimeMS: 120000
  }
).toArray();

printjson(improvedResults);
```

Compare customer IDs and totals with `badResults`.

### Task C3 — Verify semantic equivalence

```javascript id="iwiw8w"
function normalizeResults(rows) {
  return rows.map(row => ({
    id: row._id,
    completedCount: row.completedCount,
    totalRevenue: row.totalRevenue
  }));
}

const sameResults =
  JSON.stringify(normalizeResults(badResults)) ===
  JSON.stringify(normalizeResults(improvedResults));

print("Equivalent result page:", sameResults);
```

Expected result: `true`.

If the result is false, investigate before continuing.

### Task C4 — Compare explain

```javascript id="b7et33"
const improvedExplain = customers
  .explain("executionStats")
  .aggregate(improvedPipeline, {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

printjson(improvedExplain);
```

Compare the available lookup and stage statistics.

### Important qualification

The lookup subpipeline may reduce intermediate data volume without necessarily outperforming the original pipeline on every machine.

Different execution strategies and the cost of repeated foreign aggregation can affect runtime.

Your report must explain measured behavior rather than assuming the word "improved" guarantees lower latency.

---

# Experiment D — Add a Compound Foreign Index

## Objective

Improve the lookup's ability to find completed events for a given customer.

Create:

```javascript id="bc30vx"
events.createIndex(
  {
    customerId: 1,
    status: 1
  },
  {
    name: "events_customer_status"
  }
);
```

### Tasks

Run the improved pipeline again.

Inspect whether the compound index is used by the lookup.

Compare examined keys and documents with the earlier plan.

Explain why filtering by customer and status may benefit from this index.

### Acceptance criteria

You can identify the relevant foreign index.

You can explain the difference between reducing index search work and reducing outer pipeline cardinality.

---

# Experiment E — Demonstrate Unindexed Lookup Cost Safely

## Objective

Understand the risk of unindexed foreign joins without accidentally executing an enormous full-collection workload.

Do **not** remove the foreign index and run the full four-thousand-customer lookup.

That could require an extremely large amount of repeated scanning.

Instead, use only ten customers.

### Step E1 — Small indexed lookup

```javascript id="l7jblm"
const smallLookup = [
  {
    $match: {
      _id: { $gte: 1, $lte: 10 }
    }
  },
  {
    $lookup: {
      from: "pipeline_events",
      localField: "_id",
      foreignField: "customerId",
      as: "history"
    }
  },
  {
    $project: {
      historyCount: { $size: "$history" }
    }
  }
];

const indexedExplain = customers
  .explain("executionStats")
  .aggregate(smallLookup);

printjson(indexedExplain);
```

### Step E2 — Remove only the relevant foreign indexes

```javascript id="mf6xzp"
events.dropIndex("events_customer");
events.dropIndex("events_customer_status");
```

### Step E3 — Re-run the ten-customer investigation

```javascript id="h4j6r8"
const unindexedExplain = customers
  .explain("executionStats")
  .aggregate(smallLookup, {
    maxTimeMS: 30000
  });

printjson(unindexedExplain);
```

### Step E4 — Restore the indexes

```javascript id="w06b1q"
events.createIndex(
  { customerId: 1 },
  { name: "events_customer" }
);

events.createIndex(
  { customerId: 1, status: 1 },
  { name: "events_customer_status" }
);
```

### Tasks

Compare foreign collection access.

Does the unindexed lookup perform more collection scanning?

Why would expanding the same query to thousands of customers be dangerous?

### Acceptance criteria

You understand why foreign-key indexing is essential for many large lookup workloads.

You have restored the indexes before continuing.

---

# Experiment F — The Wrong Early Limit

## Objective

Demonstrate that a superficially faster pipeline can return the wrong business answer.

Create a version of the improved pipeline that limits customers before computing revenue.

```javascript id="rjcngu"
const wrongEarlyLimit = [
  {
    $match: {
      tenantId: "mercury"
    }
  },

  {
    $sort: {
      _id: 1
    }
  },

  {
    $limit: 20
  },

  ...improvedPipeline.slice(1, -3),

  {
    $sort: {
      totalRevenue: -1,
      _id: 1
    }
  },

  { $limit: 20 }
];
```

### Task F1 — Compare with the true top twenty

Run the correct improved pipeline with skip set to zero.

Then run the early-limit version.

Compare customer IDs.

### Task F2 — Explain the defect

Why is the early-limit version faster?

Why does it no longer answer the original ranking question?

### Acceptance criteria

You can distinguish valid workload reduction from a semantics-changing shortcut.

---

# Experiment G — `$facet` and Exact Counts

## Objective

Understand the cost of returning both a ranked page and the exact number of qualifying customers.

### Candidate pipeline

Take the improved pipeline before its final sort, skip, and limit.

Use `$facet` to calculate the page and total count.

```javascript id="5hcfag"
const summaryPrefix = improvedPipeline.slice(0, -3);

const facetPipeline = [
  ...summaryPrefix,

  {
    $facet: {
      page: [
        {
          $sort: {
            totalRevenue: -1,
            _id: 1
          }
        },
        { $skip: 3000 },
        { $limit: 20 }
      ],

      count: [
        { $count: "total" }
      ]
    }
  }
];
```

### Task G1 — Predict

Does the count branch avoid the earlier customer-history calculations?

How many customer summaries enter the facet?

What result shape does `$facet` produce?

### Task G2 — Run

```javascript id="885gu9"
const faceted = customers.aggregate(
  facetPipeline,
  {
    allowDiskUse: true,
    maxTimeMS: 120000
  }
).toArray();

printjson({
  pageLength: faceted[0].page.length,
  count: faceted[0].count
});
```

### Expected output shape

The result is one document containing:

- A `page` array.
- A `count` array.

The count should report 4,000 Mercury customers.

### Task G3 — Explain the cost

Why does returning one compact result document not prove the aggregation was cheap?

What would happen if a facet branch attempted to create an enormous result array?

Could `allowDiskUse` bypass the facet output-size restriction?

### Acceptance criteria

You can explain the distinction between one network round trip and a low-cost query.

You understand `$facet` memory limitations.

---

# Experiment H — Sort, Skip, and Top-K

## Objective

Inspect the optimization of a computed sort followed by skip and limit.

Take the improved pipeline.

Create two versions:

- Page one: skip zero, limit twenty.
- Page 151: skip three thousand, limit twenty.

### Task H1 — Run explain for both

```javascript id="w5a4fo"
const firstPage = [
  ...summaryPrefix,
  {
    $sort: {
      totalRevenue: -1,
      _id: 1
    }
  },
  { $skip: 0 },
  { $limit: 20 }
];

const deepPage = [
  ...summaryPrefix,
  {
    $sort: {
      totalRevenue: -1,
      _id: 1
    }
  },
  { $skip: 3000 },
  { $limit: 20 }
];

const firstExplain = customers
  .explain("executionStats")
  .aggregate(firstPage, {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

const deepExplain = customers
  .explain("executionStats")
  .aggregate(deepPage, {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

printjson(firstExplain);
printjson(deepExplain);
```

### Task H2 — Investigate

Look for sort-limit coalescence in the optimized plan.

Explain why the deep page may require retaining more top-ranked candidates.

Does either pipeline avoid calculating revenue for the candidate customers?

### Acceptance criteria

You understand why deep pagination remains expensive even when MongoDB optimizes sorting memory.

---

# Experiment I — The Unusually Active Customer

## Objective

Investigate why average history size is a poor predictor of the worst-case lookup cost.

### Compare history counts

```javascript id="rua7y5"
printjson({
  ordinaryCustomer:
    events.countDocuments({ customerId: 734 }),

  unusuallyActiveCustomer:
    events.countDocuments({ customerId: 733 })
});
```

Expected values:

- Customer 734: 36 events.
- Customer 733: 20,036 events.

### Compare lookups

Inspect an equality lookup for each customer.

Record the returned history size and relevant execution statistics.

### Tasks

Why can a lookup be acceptable for most customers but costly for one unusual customer?

What happens if the activity array approaches the BSON document-size limit?

Would a per-customer summary be more appropriate for an endpoint that only needs counts and totals?

### Acceptance criteria

You can explain tail-cardinality risk.

You understand why a compact customer response can conceal expensive historical work.

---

# Final Incident — MONGO-02

## Starting Symptom

A customer-details endpoint becomes steadily slower as history accumulates.

The response still contains the same small fields:

- Customer ID.
- Customer name.
- Completed-event count.
- Completed-event revenue.

The application currently uses lookup, unwind, group, and projection.

### Required Incident Report

Prepare a short technical report with the following sections.

**Business requirement:** What does the endpoint actually need?

**Observed workload:** How many customers and historical events are processed?

**Execution evidence:** Which indexes and aggregation stages dominate work?

**Cardinality:** Where does the stream expand or become large?

**Optimization candidates:** What can be reduced without changing the output?

**Correctness checks:** Are customers with no completed events preserved?

**Residual cost:** What work remains even after the better pipeline?

**Architectural decision:** At what point would maintained customer summaries be justified?

### Interviewer challenge

Your interviewer says:

"The new lookup pipeline is cleaner, but it still examines historical events. Why not just store the revenue total on the customer document?"

Explain the trade-off.

Do not immediately declare materialization universally superior.

Discuss update frequency, read frequency, consistency requirements, backfills, correction handling, and maintenance ownership.

---

# STOP — Independent Investigation Ends Here

Do not read the following diagnostic notes until you've attempted the exercises.

The objective is to interpret real execution behavior, not memorize a pipeline rewrite.

---

# Lab Diagnostic Notes

## Experiment A — The Expensive Ranking

The initial pipeline attaches histories, expands event-level records, calculates per-customer totals, and sorts by those totals.

The final result is small, but the computation must consider the qualifying candidate customers and their histories.

The optimizer may move the tenant filter earlier and coalesce lookup/unwind operations.

Therefore, the source pipeline doesn't prove that MongoDB physically materializes every conceptual intermediate array.

## Experiment B — Cardinality

The fixture contains 4,000 Mercury customers with thirty-six ordinary events each, plus twenty thousand additional events for Customer 733.

That gives 164,000 event-level records for Mercury.

The count represents logical expansion, regardless of whether the execution engine applies optimized lookup/unwind handling.

## Experiment C — Lookup Subpipeline

The alternative pipeline aggregates completed events inside the foreign lookup.

The outer stream receives compact customer summaries rather than full event arrays.

This can reduce intermediate data volume and simplify zero-activity handling.

It doesn't eliminate the need to process historical events.

Performance must be measured rather than assumed.

## Experiment D — Foreign Compound Index

The compound index on customer ID and status can support equality lookup and completed-status filtering.

Inspect whether the lookup uses the index and whether examined work changes.

## Experiment E — Missing Foreign Index

Removing the customer ID indexes can force significantly more expensive foreign collection access.

For thousands of outer customers, repeated scans could become extremely costly.

That is why the experiment restricts itself to ten customers.

## Experiment F — Wrong Early Limit

The early limit selects customers before calculating their true rank.

It changes the business question.

A faster result is irrelevant if it is not the requested global ranking.

## Experiment G — Facet

The count branch still depends on the upstream summary computation.

A compact result doesn't mean the count was cheap.

The facet output has its own memory and BSON-size limitations.

## Experiment H — Deep Pagination

The optimizer may retain the top skip-plus-limit candidates during sorting.

For page 151, that means 3,020 rather than twenty.

All eligible customer summaries may still need to be calculated to establish the correct ranking.

## Experiment I — Tail Cardinality

Customer 733 has 20,036 historical events.

An equality index can locate them efficiently but doesn't eliminate the need to process them when calculating historical totals.

A compact summary may better serve an endpoint that doesn't need the full event history.

## Final Incident — Expected Judgment

A strong investigation identifies foreign index usage, lookup cardinality, group and sort costs, and optimizer transformations.

It verifies semantic equivalence between candidate pipelines.

It measures actual work and normal request latency.

It recognizes that recomputing historical aggregates may remain expensive even after pipeline optimization.

A maintained summary can improve the read path, but it creates correctness and synchronization responsibilities.

That is the architectural decision developed in CS345-L03.

---

# Further Reading

1. **MongoDB — Aggregation Pipeline Optimization**  
   https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-optimization/

2. **MongoDB — Aggregation Pipeline Limits**  
   https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-limits/

3. **MongoDB — `$lookup`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/lookup/

4. **MongoDB — `$unwind`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/unwind/

5. **MongoDB — `$group`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/group/

6. **MongoDB — `$sort`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/sort/

7. **MongoDB — `$facet`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/facet/

8. **MongoDB — Explain Results**  
   https://www.mongodb.com/docs/v8.0/reference/explain-results/

9. **MongoDB — Aggregation Pipeline Stages**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation-pipeline/

10. **MongoDB — Schema Design and Data Modeling**  
    https://www.mongodb.com/docs/v8.0/data-modeling/

Cross-reference CS340-L04 for aggregation fundamentals, CS345-L01 for query-plan and index forensics, `production-cases/MONGO-01.md` and `MONGO-02.md` for related production incidents, and CS345-L03 for derived fields and materialized query models.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text id="qqzlr5"
CS345-L02 — AGGREGATION PIPELINES UNDER PRESSURE
================================================

CORE PRINCIPLE
--------------
Small output != small workload.

Measure:
- Input cardinality
- Output cardinality
- Intermediate size
- Foreign index work
- Blocking stages
- Memory/spill behavior
- Actual latency

STAGE CARDINALITY
-----------------
$match:
  reduces or preserves count

$project / $set:
  usually preserves count

$lookup:
  adds matching foreign data

$unwind:
  can multiply rows

$group:
  combines into groups

$sort:
  preserves count, may block

$skip:
  discards preceding results

$limit:
  caps following output

$facet:
  processes several subpipelines

LOOKUP
------
Indexed equality lookup:
  can locate matching foreign docs

But:
  index doesn't eliminate required
  historical-event processing.

Check:
indexesUsed
totalKeysExamined
totalDocsExamined
collectionScans

LOOKUP SUBPIPELINE
------------------
Filter/aggregate foreign data
before returning to outer pipeline.

Can reduce:
- joined array size
- outer cardinality
- downstream data volume

May still process the same events.
Benchmark actual execution.

LOOKUP + UNWIND
---------------
MongoDB can coalesce adjacent:
$lookup + $unwind

And sometimes following:
$match on joined subfields

Don't assume literal materialization
from source stage order.

UNWIND FANOUT
-------------
4,000 customers × 36 events
+ 20,000 exceptional events
= 164,000 logical event-level rows.

Average cardinality hides outliers.

GROUP
-----
$sum / count:
  compact aggregate state

$push:
  can retain enormous arrays

Output count doesn't measure
all preceding input work.

SORT
----
Sorting computed revenue requires
calculating candidate revenue first.

An index on unrelated stored fields
can't provide derived revenue order.

SORT + LIMIT
------------
MongoDB can coalesce compatible
sort/limit sequences into top-K.

SORT + SKIP + LIMIT
-------------------
K = skip + limit

skip 3000, limit 20
=> top 3020 candidates.

Still may process all eligible inputs.

EARLY LIMIT TRAP
----------------
Limit before revenue computation
does NOT preserve global top revenue.

Faster wrong answers are still wrong.

FACET
-----
Several branches share input.

Exact count is not free.
Upstream expensive calculation remains.

Facet output:
  100 MB stage limit,
  cannot spill beyond that via allowDiskUse.

Final document:
  16 MiB BSON size limit.

MEMORY & SPILL
--------------
MongoDB 8.0 eligible stages:
  100 MB stage memory behavior

allowDiskUse can permit temp files.

Spill:
  prevents certain memory failures
  does not remove unnecessary work
  may add storage/I/O pressure

OPTIMIZER
---------
Can reorder independent matches.
Can coalesce lookup/unwind/match.
Can optimize sort/limit.

Inspect optimized explain,
not only source pipeline text.

EXPLAIN
-------
db.collection
  .explain("executionStats")
  .aggregate(pipeline)

Output structure varies by engine/version.
Explain ignores existing plan cache.

CORRECTNESS
-----------
Preserve:
- zero-activity customers
- exact status filtering
- date-range semantics
- counts and sums
- deterministic sorting
- pagination meaning

PRODUCTION FORENSICS
--------------------
1. Capture real pipeline.
2. Define output contract.
3. Measure stage cardinality.
4. Inspect foreign index usage.
5. Inspect optimized plan.
6. Identify blocking work.
7. Look for spill evidence.
8. Compare equivalent designs.
9. Verify same results.
10. Measure normal latency.

MATERIALIZATION SIGNALS
-----------------------
Frequent reads.
Expensive repeated history scans.
Sort key computed after lookup.
Deep pagination.
Stable, maintainable aggregate contract.

But materialization creates:
- update synchronization
- retry/idempotency concerns
- backfill requirements
- drift detection
- consistency trade-offs

ANTI-PATTERNS
-------------
"It returns only 20 docs."
"Just put $limit first."
"$lookup uses an index, so it's cheap."
"$group reduced rows, so no work happened."
"allowDiskUse makes the pipeline efficient."
"$facet gives a free total count."
"The optimizer follows my code literally."
"An early $match always changes performance."
"One query is always better than two."
"Store the derived field, problem solved."

MENTAL MODEL
------------
Track the quantity and shape of data
through every operation.

Ask what work is necessary,
what work is duplicated,
what work can be avoided,
and what business meaning must survive.

NEXT
----
CS345-L03
Pagination, Derived Fields,
and Materialized Data
```
