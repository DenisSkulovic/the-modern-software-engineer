---
id: CS350-L02
course: CS350
title: "PostgreSQL Query Plan Forensics"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS350-L01
next: CS350-L03
---

# CS350 — Advanced PostgreSQL Engineering
## Lecture 02: PostgreSQL Query Plan Forensics

*The query returns twenty rows. PostgreSQL examines two hundred thousand. Someone adds an index, execution gets slower, and the database is behaving perfectly rationally.*

---

# Part I — Intuition

## 1. The Index That Made Everything Worse

Imagine you're responsible for the reservation-management system of a hotel-booking platform.

The administrative dashboard contains a list of reservations. Staff can filter by hotel, booking status, customer, and date.

For months, everything works.

Then the company grows.

The reservations table reaches several million rows. One particular report becomes slow, and an engineer notices that its SQL filters by booking status.

The query looks innocent:

"Find all confirmed reservations and calculate their total captured value."

The engineer checks the schema.

There's no index on `status`.

Aha! An obvious opportunity.

They create an index on the column.

The index builds successfully. PostgreSQL updates its statistics. The team tests the query.

It isn't faster.

In one experiment, forcing PostgreSQL to use an indexed access path makes the query substantially slower.

How is this possible?

Isn't the entire point of an index to make queries faster?

The answer is that an index is a method of locating data, not a guarantee that locating data through that method is cheaper.

Suppose eighty percent of all reservations are confirmed.

The report needs most of the table.

An index can identify the matching reservations, but the database may still need to retrieve their actual rows to calculate the total.

Using the index could mean traversing an additional data structure and then visiting a large number of table pages.

A sequential scan can simply read the table and evaluate the status condition as it goes.

For a query touching most of the table, this can be cheaper.

**An index is useful when it avoids enough work to justify its own cost.**

The important question is not whether PostgreSQL used an index.

It is how much work PostgreSQL had to perform to return the answer.

## 2. PostgreSQL Chooses an Execution Plan

When you write SQL, you describe the result you want.

You generally don't specify the precise sequence of physical operations needed to produce it.

PostgreSQL's planner considers possible strategies and estimates their costs.

For example, it may choose to:

- Scan the table sequentially.
- Traverse a B-tree index.
- Read matching index entries and collect table-page locations into a bitmap.
- Join two relations using nested loops.
- Build a hash table for a join.
- Sort intermediate results.
- Aggregate rows before returning the final answer.

Each strategy has trade-offs.

The planner estimates how much data each operation will process and how expensive the operation is likely to be.

It considers table statistics, available indexes, estimated row counts, storage-access costs, and other parameters.

The result is a tree of operations called an **execution plan**.

The tree tells us how PostgreSQL intends to produce the requested result.

### Visual anchor 1 — The plan is a tree

Imagine a query that retrieves bookings from one hotel and attaches customer names.

A possible execution plan might look like this:

```text id="m1pxc9"
Nested Loop
    |
    ├── Index Scan on bookings
    |       Find bookings for Hotel 42
    |
    └── Index Scan on customers
            Find customer for each booking
```

The nested loop is the parent operation.

The two scans provide its inputs.

The second scan may execute repeatedly, once for each booking returned by the first.

The tree tells us more than which indexes exist.

It shows how many times operations may run and how they combine.

## 3. The Planner Has Predictions, but Reality Has Measurements

PostgreSQL has a command called `EXPLAIN`.

It displays the proposed execution plan.

By itself, ordinary `EXPLAIN` generally estimates what will happen without executing the query.

`EXPLAIN ANALYZE` goes further.

It actually runs the query and reports execution measurements.

Now we can compare the planner's expectations with what happened.

Imagine an operation that was expected to return fifty rows.

During execution, it actually returned fifty thousand.

That is a thousandfold estimation error.

The planner may have chosen a nested-loop join because it expected a small amount of work.

But the actual input was enormous.

The algorithm wasn't necessarily implemented incorrectly.

The choice was based on an inaccurate prediction.

This is a recurring theme in query optimization.

**A bad execution plan can be the consequence of a bad estimate, not a bad SQL statement.**

### Visual anchor 2 — Prediction versus observation

```text id="7igarc"
PostgreSQL planner
        |
        v
Estimated rows: 50
        |
        v
Chooses nested-loop strategy
        |
        v
Actual rows: 50,000
        |
        v
Repeated work becomes expensive
```

The evidence we care about is the difference between estimated and actual cardinality, and what that difference caused downstream.

## 4. Loops Multiply the Work

Suppose a query returns 5,000 bookings.

For each booking, PostgreSQL performs an indexed lookup into the customer table.

One lookup might take a tiny fraction of a millisecond.

That sounds harmless.

But five thousand small operations can become substantial.

And if the lookup touches expensive storage pages, the cost can grow further.

PostgreSQL's execution plan reports a `loops` count.

For a node executed multiple times, its reported actual rows and per-node timing are ordinarily averages per execution.

So a node displaying two rows per loop and five thousand loops has returned roughly ten thousand rows across its executions.

It did not return only two rows overall.

That distinction matters enormously.

A developer who reads only the `actual rows` value and ignores `loops` can completely misunderstand the amount of work performed.

## 5. Buffers Reveal Data Access

A database query doesn't operate entirely on abstract rows.

It reads pages of data through PostgreSQL's buffer system and potentially from storage.

Execution plans can report buffer activity.

A shared buffer hit means the page was found in PostgreSQL's shared buffer cache.

A shared read means a page had to be read into that cache.

That read may come from the operating system's cache or physical storage. It doesn't automatically prove that the database waited for a physical disk operation.

This distinction is important.

We should not look at `shared read` and assume every read represents a mechanical disk access.

Still, buffer counts help us understand how much data-access work the query performed.

If two semantically equivalent plans return the same result but one touches vastly more pages, that's valuable evidence.

### Visual anchor 3 — The evidence chain

```text id="9yxim4"
Slow SQL request
      |
      v
EXPLAIN ANALYZE
      |
      ├── Estimated vs actual rows
      ├── Loops
      ├── Scan and join choices
      ├── Buffer hits and reads
      ├── Sort and hash behavior
      └── Total execution time
      |
      v
Explain where work accumulated
```

This is what we mean by *query-plan forensics*.

We reconstruct the work performed by the database.

## 6. Twenty Results Can Require Enormous Work

Imagine the reservations dashboard requests page five thousand.

Each page contains twenty bookings.

The SQL uses `LIMIT 20 OFFSET 99980`.

The final result contains only twenty rows.

But PostgreSQL must account for the preceding 99,980 rows in the requested order.

It cannot simply teleport to the hundred-thousandth matching row unless the access strategy provides another suitable way to locate that position.

An index may help avoid sorting.

But an offset still requires traversing and discarding the preceding results.

The output size can be tiny while the internal work remains large.

The same thing happens in more complicated queries.

The database might have to join, calculate, filter, or sort a huge intermediate result before returning a small final page.

This is particularly important when debugging SQL generated by ORMs.

The application developer may see twenty returned objects and assume the database processed twenty records.

That assumption is often false.

## 7. A Tiny Comprehension Check

Consider two hypothetical plans for the same query.

Plan A uses a sequential scan and completes in 40 milliseconds.

Plan B uses an index scan and completes in 110 milliseconds.

Both return exactly the same rows.

Which plan is better?

Under those measured conditions, Plan A.

The presence of an index does not make Plan B preferable.

Now consider another situation.

Plan A returns fifty rows and examines fifty rows.

Plan B returns fifty rows but examines a million candidate rows.

What should you investigate?

Why Plan B examined so many rows, whether its estimates were accurate, and whether a different access path or query structure could avoid that work.

You don't need to memorize every PostgreSQL plan node to begin an investigation.

You need to ask how much work was done, why it was done, and whether that work was necessary.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. The Three Views of a Database Query

Let's establish three different perspectives.

**The SQL statement** describes the result required by the application.

**The estimated execution plan** describes how PostgreSQL expects to obtain that result.

**The measured execution plan** describes what happened when the statement actually ran.

These are not interchangeable.

The SQL can be logically correct while inefficient.

The estimated plan can be reasonable based on incomplete statistics.

The measured execution can reveal unexpected cardinalities, repeated work, or expensive data access.

A useful investigation compares all three.

### 8.1 The essential commands

Ordinary `EXPLAIN` shows an estimated plan:

```sql id="40gmg1"
EXPLAIN
SELECT *
FROM bookings
WHERE hotel_id = 42;
```

To execute the query and collect runtime measurements, use:

```sql id="m7du76"
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM bookings
WHERE hotel_id = 42;
```

For this lecture, the latter is our primary diagnostic instrument.

`ANALYZE` causes the statement to execute.

`BUFFERS` adds buffer-usage information.

This is not the same as the standalone SQL `ANALYZE` command that gathers table statistics.

The names are similar, but their purposes differ.

### 8.2 A critical safety rule

`EXPLAIN ANALYZE` actually executes the SQL statement.

If you use it on an `UPDATE`, `DELETE`, or `INSERT`, those modifications occur.

In a disposable lab, you can run such experiments inside a transaction and roll them back.

In production, you must consider triggers, locks, external side effects, and the operational consequences of executing the statement.

A transaction rollback does not necessarily undo every possible effect outside the database.

For ordinary investigation, begin with read-only queries and use safe environments whenever possible.

## 9. How to Read an EXPLAIN Node

A PostgreSQL text plan contains several important fields.

A simplified, illustrative scan might look like this:

```text id="h4mi9p"
Index Scan using bookings_hotel_idx on bookings
  (cost=0.42..120.00 rows=50 width=80)
  (actual time=0.030..2.100 rows=5000 loops=1)
  Index Cond: (hotel_id = 42)
  Buffers: shared hit=180 read=35
```

These figures are invented solely to demonstrate how the fields are interpreted. They are not measurements from our lab.

Let's decode them.

### 9.1 Cost

The estimated cost has two values.

The first represents startup cost.

The second represents total estimated cost if the node's output is consumed.

These values are expressed in PostgreSQL's internal cost units.

They are not milliseconds.

A plan with estimated cost 100 does not mean PostgreSQL predicts 100 milliseconds.

The numbers are used to compare candidate plans under the planner's cost model.

### 9.2 Estimated rows

The planner predicts that the scan will return fifty rows.

That estimate influences decisions elsewhere in the tree.

If those fifty rows are used as the outer input to a nested loop, PostgreSQL may expect roughly fifty executions of the inner lookup.

### 9.3 Width

The estimated width represents the average number of bytes per output row.

It matters for memory, sorting, hashing, and data movement.

A query returning wide text columns may have substantially different costs from one returning only integer identifiers.

This is one reason `SELECT *` can make an otherwise ordinary query more expensive.

### 9.4 Actual time

The actual timing reports observed execution timing for the node.

The first value is the time until its first output.

The second is the time until the node finishes producing its output.

For nodes executed repeatedly, these are generally averages per execution.

They are not independent durations to be added blindly across the plan tree.

Parent node timings include time spent obtaining results from children.

Summing all node times double-counts work.

### 9.5 Actual rows and loops

The scan actually returned approximately five thousand rows per execution and ran once.

That is radically different from the estimated fifty.

The planner underestimated the result cardinality by about a factor of one hundred.

The more important question is what this error caused elsewhere in the plan.

### 9.6 Buffers

The node reports 180 shared buffer hits and 35 shared reads.

These counts help describe the data-access workload.

They are not a direct measurement of user-perceived latency.

A query may be CPU-bound while producing many buffer hits.

A query may also suffer from expensive storage reads.

We must interpret the buffer information alongside timing and the plan structure.

## 10. Read the Tree from the Leaves Upward

SQL is written in one order.

Execution plans are interpreted differently.

A useful habit is to begin with the leaf operations that read source data.

Identify their access methods.

Then move upward through joins, sorts, aggregates, and final output nodes.

For example, consider a query joining bookings to customers.

PostgreSQL might scan a subset of bookings using an index and then retrieve customers through primary-key lookups.

The parent join node receives those inputs.

An aggregate above the join might group the results.

A sort above the aggregate might order the groups by revenue.

A limit node at the top returns the requested number of rows.

### 10.1 Actual execution isn't always a simple sequential walk

The plan tree is a useful model of dependencies, but execution is not necessarily equivalent to executing every node completely from bottom to top.

Many PostgreSQL plan nodes operate through a demand-driven iterator model.

A parent requests rows from its children.

A `LIMIT` node may stop requesting rows after obtaining enough output.

A nested loop may alternate between its outer and inner inputs.

A sort generally needs to consume its input before producing correctly ordered results.

Parallel plans can execute work concurrently.

So the tree explains data flow and dependencies, not a universal chronological script.

## 11. Scan Types: What PostgreSQL Is Actually Reading

Let's compare the main access methods.

### 11.1 Sequential Scan

A sequential scan reads the table's heap pages and evaluates the relevant conditions.

It can be efficient when many rows qualify.

It may also be chosen for small tables because navigating an index would add overhead.

A sequential scan is not automatically a failure.

### 11.2 Index Scan

An index scan uses an index to locate candidate table rows.

For each candidate, PostgreSQL may need to visit the heap to retrieve additional columns or verify visibility.

This can be excellent for selective lookups.

But if a large percentage of the table qualifies, the repeated index and heap access can be expensive.

### 11.3 Bitmap Index Scan and Bitmap Heap Scan

A bitmap plan separates the process of finding candidate row locations from retrieving their heap pages.

A Bitmap Index Scan identifies candidate locations.

A Bitmap Heap Scan visits relevant heap pages, allowing PostgreSQL to organize access more efficiently than repeated independent heap lookups in some situations.

This is often attractive for queries returning a moderate portion of a table.

Bitmap plans can also combine multiple indexes.

The plan may show whether bitmap pages were exact or lossy.

Lossy pages require additional filtering during heap access.

### 11.4 Index-Only Scan

An index-only scan can satisfy the required data columns from the index.

But the name can be misleading.

PostgreSQL uses MVCC, and an index entry alone does not always establish whether the corresponding row is visible to the current transaction.

The executor may still need heap access.

The plan reports `Heap Fetches` when those occur.

A covering index is therefore necessary for many index-only strategies, but not sufficient to guarantee zero heap access.

The visibility map and table modification history matter.

We will explore the physical consequences of MVCC in CS350-L03.

## 12. Why an Index Can Be Slower Than a Sequential Scan

Return to our opening incident.

Suppose eighty percent of bookings are confirmed.

The query calculates the sum of captured amounts for confirmed bookings.

A simple index on status can identify those rows.

But the query needs the `amount` column from the heap.

If the index doesn't contain that value, PostgreSQL may need extensive heap access.

For a high-selectivity query, that can be worthwhile.

For a query touching most of the table, sequential scanning may be more efficient.

### 12.1 Selectivity is the missing concept

Selectivity describes how much of the data satisfies a condition.

If only a tiny fraction qualifies, an index can dramatically reduce the search space.

If most rows qualify, avoiding the remaining rows may not justify the index traversal and heap access.

The exact crossover depends on table size, row width, caching, storage characteristics, parallelism, and the planner's cost model.

There is no universal percentage at which indexes become useless.

### 12.2 Why forcing an index is a diagnostic experiment

PostgreSQL allows certain planner methods to be discouraged through configuration settings.

For example, disabling sequential scans discourages the planner from choosing that access method when alternatives exist.

This can help compare different candidate strategies.

But it is a diagnostic technique.

It does not prove that the forced alternative should become the production default.

And the setting cannot eliminate sequential scans in every possible case.

A strong investigation compares the actual plans and measured work, not merely their labels.

## 13. Join Algorithms: Different Shapes of Work

We covered relational joins in CS330 and SQL composition in CS350-L01.

Now we're interested in their execution strategies.

### 13.1 Nested Loop Join

A nested loop reads rows from an outer input.

For each outer row, it searches or scans the inner input for matches.

This can be extremely efficient when the outer input is small and the inner lookup uses a selective index.

For example, twenty bookings joined to customers by primary key may be inexpensive.

But if the outer input unexpectedly contains a million rows, the inner lookup can execute a million times.

This is where the `loops` field becomes important.

### 13.2 Hash Join

A hash join generally builds a hash table from one input and probes it with rows from the other.

This can be effective for equality joins involving substantial inputs.

The cost includes building the hash table and processing the probing input.

The plan may report hash buckets, batches, and memory usage.

If the hash table cannot fit within its available memory budget, PostgreSQL may need multiple batches and temporary storage.

A hash join is not automatically superior to a nested loop.

It is appropriate when its startup and processing costs compare favorably with alternatives.

### 13.3 Merge Join

A merge join combines inputs ordered by their join keys.

It can be efficient when the inputs are already sorted or can be sorted economically.

Indexes may provide the required ordering.

Otherwise, explicit sort operations may be necessary.

The planner considers whether preparing the sorted inputs is worth the benefit.

### 13.4 The important question

Do not memorize:

"Nested loops are bad, hash joins are good."

That is incorrect.

Ask instead:

How many rows enter each side?

How many times does the inner operation execute?

Are the join keys indexed?

What is the cost of building a hash table or sorting the inputs?

Are the planner's cardinality estimates accurate?

Those questions determine whether the join strategy makes sense.

## 14. Rows Multiplied by Loops

Let's make the arithmetic explicit.

Suppose a plan node shows:

`actual rows=2 loops=5000`

That means the node returned approximately two rows per execution across five thousand executions.

Total returned rows are approximately ten thousand.

Now suppose the node's average actual completion time is 0.04 milliseconds.

Five thousand executions represent roughly two hundred milliseconds of accumulated time for that node.

But don't add that number mechanically to the parent node's time.

Parent timing already includes child work, and actual parallel execution can complicate interpretation further.

The useful idea is identifying repetition.

A tiny operation performed a vast number of times can dominate a query.

### 14.1 Rows removed by filter

A plan may also report rows removed by a filter.

This tells us that PostgreSQL examined candidate rows but rejected some after applying a condition.

The location of the filter matters.

An `Index Cond` restricts index access.

A `Filter` may be applied after retrieving candidate rows.

If a query uses one index condition but discards most retrieved rows through another filter, an alternative composite or partial index may reduce work.

However, PostgreSQL may also choose the existing strategy because the overall cost remains reasonable.

Again, measure rather than assume.

## 15. Cardinality Estimation: Where Plans Go Wrong

PostgreSQL relies heavily on statistics when estimating result sizes.

Ordinary table statistics describe individual columns, including value distributions and common values.

But multiple predicates can be correlated.

Imagine a hotel platform where nearly all confirmed bookings belong to Hotel A, while cancelled bookings are concentrated in several smaller hotels.

A query filters by both hotel ID and status.

If PostgreSQL treats those conditions as statistically independent, it may estimate a number of matching rows that differs substantially from reality.

That estimate influences scan choice, join strategy, memory expectations, and other plan decisions.

### 15.1 Statistics can be stale

If the table changes significantly after the last statistics collection, the planner may operate with outdated information.

Running the standalone `ANALYZE` command updates statistical estimates.

This can improve plans without changing SQL or indexes.

But `ANALYZE` is not a guaranteed performance fix.

It collects statistics, not magical knowledge of every possible query.

### 15.2 Extended statistics

PostgreSQL supports multivariate statistics through `CREATE STATISTICS`.

These can describe relationships among columns.

Examples include most-common-value combinations, functional dependencies, and distinct-value relationships.

For correlated equality conditions, such statistics may improve row estimates.

But they are not a universal solution.

They do not automatically fix every complex join-estimation problem, and their effectiveness depends on the query shape and statistics collected.

The correct workflow is to identify the estimation error first.

Then determine whether the missing information can be represented through appropriate statistics.

## 16. Sorting and Memory

Our reservations dashboard allows sorting by amount.

Suppose the query retrieves hundreds of thousands of rows and sorts them by booking value.

If no suitable index provides the requested order, PostgreSQL may perform an explicit sort.

The plan can reveal the sort method and memory or disk usage.

For small sorts, PostgreSQL may keep the operation in memory.

For larger sorts, it may use temporary disk space.

A top-N query may use a bounded sorting strategy when only a small number of results are needed.

But a small final result does not guarantee a cheap sort.

The database may still need to examine all qualifying rows to determine which ones belong in the top-N result.

### 16.1 `work_mem` isn't a global query limit

PostgreSQL's `work_mem` setting influences memory available to certain operations, including sorts and hashes.

It is not a simple total-memory limit for a query.

A query may contain several memory-consuming nodes.

Parallel workers can multiply memory usage.

Increasing `work_mem` globally to fix one slow sort can increase memory pressure elsewhere.

A safer investigation first identifies the actual spilling operation and its workload.

Then any memory adjustment should be evaluated in context.

### 16.2 Temporary buffer activity

A plan showing temporary blocks read or written suggests that intermediate work used temporary storage.

This may come from sorting, hashing, or other operations.

But temporary I/O is not automatically the sole bottleneck.

Compare total timing, row counts, and the relevant plan nodes before declaring that increasing memory will solve the problem.

## 17. Pagination: LIMIT Is Not a Performance Guarantee

Suppose a query returns twenty bookings with an offset of 150,000.

The database may use an index that already provides the correct order.

That avoids a full explicit sort.

But the index still needs to provide enough ordered rows for PostgreSQL to skip the first 150,000 and return the next twenty.

The index is useful, yet the query may remain expensive.

### 17.1 Offset pagination

Offset pagination is convenient for arbitrary page navigation.

But deep offsets require progressively more skipped work.

Concurrent changes to the dataset may also shift row positions between page requests.

### 17.2 Keyset pagination

Keyset pagination uses the ordering values of the last row from the previous page.

For example, if bookings are ordered by timestamp and booking ID descending, the next page can request rows whose `(booked_at, booking_id)` tuple is smaller than the cursor tuple.

An appropriate composite index can help PostgreSQL seek directly to the relevant portion of the ordered data.

This is often much more efficient for sequential page navigation.

But keyset pagination has trade-offs.

It doesn't naturally support arbitrary jumps to page 5,000.

It requires a stable ordering contract.

And it does not automatically provide snapshot consistency across separate requests.

### 17.3 The compound-index connection

A query filtered by hotel and ordered by booking timestamp and ID can benefit from an index beginning with the hotel ID and continuing with the ordering columns.

For example, an index on:

`(hotel_id, booked_at DESC, booking_id DESC)`

This can allow PostgreSQL to locate one hotel's bookings in the desired order.

However, adding an index must still be justified by actual workload patterns and maintenance costs.

## 18. Prepared Statements and Parameter-Sensitive Plans

Imagine an application that retrieves bookings by hotel ID.

Hotel Aurora accounts for most bookings.

Hotel Pines accounts for a tiny fraction.

The same parameterized query runs for both hotels.

Should PostgreSQL always use the same execution plan?

Not necessarily.

For a large hotel, a sequential scan may be attractive.

For a small hotel, an index scan may be much more efficient.

PostgreSQL prepared statements can use custom or generic execution plans.

A custom plan can consider the specific parameter values for that execution.

A generic plan can be reused without depending on the particular values.

### 18.1 The trade-off

Custom planning may produce a better strategy for highly skewed parameters.

But planning itself costs time.

A generic plan can avoid repeated planning overhead.

PostgreSQL normally decides between these approaches using its prepared-statement planning rules.

The `plan_cache_mode` setting allows diagnostic control over the choice.

This is related to what engineers sometimes broadly call *parameter sniffing*, but PostgreSQL's generic/custom plan behavior should be understood on its own terms rather than assumed identical to another database engine.

### 18.2 Why the same SQL can be fast or slow

If the ideal plan varies dramatically with the parameter value, a reused generic plan may be poor for some values.

The correct investigation compares the actual execution plans for representative parameters.

Don't simply turn off prepared statements or force custom plans globally.

Establish whether parameter-sensitive planning is responsible for the observed problem.

## 19. ORM-Generated SQL: The Plan Doesn't Know It Came from an ORM

An ORM generates SQL.

PostgreSQL executes SQL.

The database doesn't care whether the statement was handwritten, produced by Prisma, generated through Hibernate, or assembled by another query builder.

The query planner operates on the statement and available statistics.

### 19.1 The N+1 problem

Suppose the application retrieves one hundred bookings.

Then, for each booking, it performs a separate query to fetch customer information.

The problem may not be visible in a single execution plan.

Each individual customer lookup could be extremely fast.

The application nevertheless performs 101 database round trips.

`EXPLAIN ANALYZE` on one query will not reveal the cumulative latency of the whole request.

You must inspect the sequence of statements executed by the application.

Tools such as query logging, tracing, and `pg_stat_statements` can help identify repeated query patterns.

The latter requires appropriate server configuration and is not necessarily enabled by default.

### 19.2 One enormous ORM query can be worse

The opposite problem also exists.

An ORM eagerly joins several one-to-many relationships.

The resulting SQL produces a huge intermediate rowset with duplicated parent data.

The database may spend substantial time joining, sorting, or transmitting rows that the ORM later deduplicates into objects.

Reducing round trips is useful, but one enormous query is not automatically optimal.

Sometimes carefully batching several queries is more efficient.

The correct choice follows cardinality, data volume, and observed latency.

### 19.3 Capture actual SQL and parameters

Never diagnose an ORM performance issue solely from the application-level method name.

Capture the actual SQL statement.

Capture representative parameter values.

Inspect the execution plan.

Determine whether the application performs one statement or hundreds.

Then explain the cost.

## 20. A Practical Plan-Reading Checklist

When an unfamiliar execution plan appears, follow a consistent process.

### Step 1 — Confirm the measured problem

Is the database query actually responsible for the slow endpoint?

The request may spend time in application processing, network transport, connection-pool waiting, serialization, or other systems.

Separate those costs.

### Step 2 — Capture the real SQL

Include representative parameter values and relevant session settings.

A query with a rare hotel ID may have a different plan from one with a very common ID.

### Step 3 — Read the total timing

Note planning time and execution time.

Remember that `EXPLAIN ANALYZE` adds measurement overhead and does not include every aspect of application-observed latency.

### Step 4 — Find cardinality mismatches

Compare estimated and actual rows at important nodes.

Large estimation errors can explain surprising join or scan choices.

### Step 5 — Examine repeated work

Inspect `loops`.

A cheap-looking inner scan executed thousands of times may account for substantial work.

### Step 6 — Examine data access

Inspect buffer hits, reads, heap fetches, and filter behavior.

Determine whether the query accesses far more data than necessary.

### Step 7 — Identify blocking operations

Look for sorts, hashes, aggregations, and materialization.

Inspect temporary storage activity and memory constraints where relevant.

### Step 8 — Form a hypothesis

Explain why the plan performs excessive work.

Do not immediately create an index.

Possible causes include missing indexes, poor predicate selectivity, stale statistics, correlated conditions, excessive join cardinality, deep offsets, or parameter-sensitive plans.

### Step 9 — Test one correction

Change the smallest relevant factor.

Examples include correcting a predicate, adding a suitable composite index, updating statistics, rewriting an unnecessary join, or using keyset pagination.

### Step 10 — Verify correctness and performance

Confirm the query still returns the correct results.

Compare plans and measured work under representative conditions.

Consider index maintenance, write costs, deployment safety, and other affected queries.

## 21. The Three Levels of Database Performance Reasoning

It is useful to distinguish three levels of competence.

**Level one: Recognize plan operators.**

You can identify sequential scans, index scans, nested loops, hash joins, sorts, and aggregates.

This is basic plan literacy.

**Level two: Explain the cost mechanism.**

You can describe why an operator is expensive in a particular plan.

For example, a nested loop executes an inner lookup fifty thousand times because the outer input is much larger than expected.

This is real diagnostic competence.

**Level three: Predict and verify an improvement.**

You can propose a change, explain why it should reduce work, and validate the result without changing correctness.

This is production engineering judgment.

The aim of CS350-L02 is the third level.

Memorizing plan-node names is not enough.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — The Index Trap

A query retrieves eighty percent of a table's rows.

PostgreSQL chooses a sequential scan even though an index exists on the filtered column.

Is this necessarily wrong?

Explain the cost trade-off.

### Question 2 — Estimated Versus Actual Rows

A scan is estimated to return 100 rows.

It actually returns 100,000.

Why might this lead to a poor join strategy?

### Question 3 — Loops

An inner index scan shows:

`actual rows=3 loops=4000`

Approximately how many rows did it return across all executions?

Why is looking at the three-row figure alone misleading?

### Question 4 — Buffers

A plan reports thousands of shared buffer hits and very few shared reads.

Does this prove the query is fast?

Does a shared read necessarily mean a physical disk read?

### Question 5 — Index-Only Scans

A query uses an Index Only Scan but reports many heap fetches.

Why?

What database mechanism determines whether heap visibility checks can be avoided?

### Question 6 — Sorting

A query has `LIMIT 20` but still spends substantial time sorting.

How can this happen?

What would you inspect?

### Question 7 — Deep Pagination

An admin endpoint uses `LIMIT 20 OFFSET 150000`.

Why can it remain expensive even with a suitable ordering index?

What alternative would you consider?

### Question 8 — Prepared Statements

A parameterized query is fast for a small hotel but slow for a very large hotel.

How might generic versus custom planning contribute?

### Question 9 — ORM N+1

An endpoint takes two seconds, but each individual SQL query completes in five milliseconds.

What should you investigate?

Why might one `EXPLAIN ANALYZE` be insufficient?

### Question 10 — The Senior Diagnosis

You receive a slow production query and an execution plan.

Describe the sequence of evidence you would collect before recommending an index.

---

# Solutions and Discussion

## Solution 1 — The Index Trap

A sequential scan can be the cheaper strategy when most rows qualify.

An index may add traversal overhead and require many heap accesses.

Compare actual execution and buffer work before judging the choice.

## Solution 2 — Cardinality Error

The planner may choose a strategy appropriate for a small input, such as repeated indexed lookups.

If the actual input is much larger, that repeated work may become expensive.

Investigate why the estimate was inaccurate and what the error caused downstream.

## Solution 3 — Loops

Approximately twelve thousand rows.

The displayed actual row count is ordinarily an average per execution.

Multiplying by the loop count reveals the approximate total.

## Solution 4 — Buffers

No.

Buffer hits can be numerous in a CPU-heavy query, and many cached-page accesses still require work.

A shared read means a page was brought into PostgreSQL's shared buffers, potentially from the operating system cache rather than physical storage.

## Solution 5 — Heap Fetches

PostgreSQL must verify MVCC visibility.

If the relevant heap page isn't marked all-visible, an index-only scan may still need to inspect the heap.

The visibility map helps determine when heap access can be avoided.

## Solution 6 — Sorting

The database may need to examine all qualifying rows before identifying the top twenty.

Inspect the sort input cardinality, sort method, memory usage, temporary I/O, and whether an appropriate index could provide the required order.

## Solution 7 — Deep Pagination

The database must account for the skipped ordered rows.

An index can avoid sorting but does not eliminate the offset traversal.

Keyset pagination can use a cursor to locate the next portion of the ordered data more directly.

## Solution 8 — Prepared Plans

A generic plan does not depend on specific parameter values.

It may be inappropriate for a highly skewed value.

A custom plan can incorporate the parameter and choose a more suitable strategy.

Compare plans under representative parameters before changing configuration.

## Solution 9 — N+1

The endpoint may execute hundreds of individually fast queries.

The cumulative network, execution, and application-processing cost can become large.

Inspect the full query sequence, statement counts, and application tracing.

## Solution 10 — Production Investigation

Confirm the database is responsible for the latency.

Capture the actual SQL and parameters.

Read the measured plan.

Compare estimated and actual rows.

Inspect loops, scan methods, buffers, sorts, and temporary storage.

Form a causal hypothesis.

Test a focused change and verify correctness and performance.

---

# The Mental Model Worth Keeping

A query plan is an explanation of the physical work needed to produce a relational result.

The planner predicts row counts and costs.

The executor performs the operations.

`EXPLAIN ANALYZE` lets us compare prediction with reality.

The strongest diagnostic questions are:

**How many rows were processed? How many times was the operation repeated? How much data was accessed? Which assumptions caused PostgreSQL to choose this strategy?**

An index is not automatically a fix.

A sequential scan is not automatically a problem.

A small result does not imply a small workload.

And a correct query can still be catastrophically inefficient.

---

# Next Lecture — CS350-L03: PostgreSQL Under Production Pressure

We now understand how to inspect an individual query's execution strategy.

But PostgreSQL is not merely a query executor.

It is a continuously operating database system.

Transactions create row versions. Vacuum must reclaim dead tuples. Indexes grow. WAL accumulates. Connections consume resources. Locks can block otherwise inexpensive operations.

A query can have an excellent execution plan and still perform badly because the surrounding system is under pressure.

In CS350-L03, we'll investigate those operational mechanisms.

We'll reproduce dead tuples, inspect autovacuum behavior, examine lock and connection contention, and understand why deleting millions of records does not necessarily shrink a database file.

*The spoken lecture ends here. The following material is for independent experiments and plan investigation rather than continuous audio listening.*

---

# Optional Practical Lab — PostgreSQL Query Plan Forensics

## Lab Contract

The purpose of this lab is to collect actual PostgreSQL evidence.

No execution plans have been precomputed for your machine.

The planner's choices and measured timings can differ depending on PostgreSQL version, hardware, memory, cache state, and configuration.

For each exercise:

1. Predict the likely plan.
2. Run the query.
3. Record the actual plan.
4. Explain the expensive operations.
5. Change one factor.
6. Run the query again.
7. Compare results and measured work.
8. Ask AI to review your reasoning only afterward.

Do not treat an expected plan shape as a guaranteed outcome.

The important result is understanding the plan PostgreSQL actually chooses.

## 1. Create a Larger Database

The six-customer fixture from CS350-L01 is useful for verifying SQL correctness, but too small for meaningful performance experiments.

A tiny table often makes sequential scanning the rational choice regardless of indexes.

We'll create a separate schema containing 300,000 bookings and 30,000 customers.

The fixture deliberately includes skewed hotel distribution, correlated statuses, and wide rows.

Use a disposable local PostgreSQL instance.

If you already started the PostgreSQL container for CS350-L01, reuse it.

Otherwise create a local PostgreSQL 18 container.

```bash id="wj0psy"
docker run --name cs350-postgres \
  -e POSTGRES_PASSWORD=labpass \
  -e POSTGRES_DB=cs350 \
  -p 5433:5432 \
  -d postgres:18

docker exec -it cs350-postgres \
  psql -U postgres -d cs350
```

If the container already exists but is stopped, use `docker start cs350-postgres`.

### Create the schema

The following setup intentionally drops only the dedicated `cs350_plans` schema.

```sql id="d9d2zt"
DROP SCHEMA IF EXISTS cs350_plans CASCADE;
CREATE SCHEMA cs350_plans;

CREATE TABLE cs350_plans.customers (
    customer_id integer PRIMARY KEY,
    name text NOT NULL,
    segment text NOT NULL
);

CREATE TABLE cs350_plans.bookings (
    booking_id bigint PRIMARY KEY,
    customer_id integer NOT NULL
        REFERENCES cs350_plans.customers(customer_id),
    hotel_id integer NOT NULL,
    status text NOT NULL,
    booked_at timestamptz NOT NULL,
    amount_eur numeric(12,2) NOT NULL,
    note text NOT NULL
);
```

### Seed customers

Create 30,000 customers.

Five percent will belong to the business segment.

```sql id="7wb6u6"
INSERT INTO cs350_plans.customers (
    customer_id, name, segment
)
SELECT
    g,
    'Customer ' || g,
    CASE
        WHEN g % 20 = 0 THEN 'business'
        ELSE 'consumer'
    END
FROM generate_series(1, 30000) AS s(g);
```

### Seed bookings

Create 300,000 bookings.

Hotel 1 deliberately receives most of the records.

Booking status is correlated with hotel distribution.

The note column makes each row wider, increasing the potential cost of heap access.

```sql id="w7u2up"
INSERT INTO cs350_plans.bookings (
    booking_id,
    customer_id,
    hotel_id,
    status,
    booked_at,
    amount_eur,
    note
)
SELECT
    g,
    ((g - 1) % 30000) + 1,

    CASE
        WHEN g % 100 < 85 THEN 1
        ELSE (g % 15) + 2
    END,

    CASE
        WHEN g % 100 < 80 THEN 'confirmed'
        WHEN g % 100 < 90 THEN 'pending'
        ELSE 'cancelled'
    END,

    TIMESTAMPTZ '2026-01-01 00:00:00+00'
        + g * INTERVAL '10 seconds',

    (50 + (g % 900))::numeric(12,2),

    repeat(md5(g::text), 6)

FROM generate_series(1, 300000) AS s(g);
```

### Create initial indexes

Create one deliberately low-selectivity index and several useful supporting indexes.

```sql id="evfzfe"
CREATE INDEX bookings_status_idx
ON cs350_plans.bookings (status);

CREATE INDEX bookings_hotel_time_idx
ON cs350_plans.bookings (
    hotel_id,
    booked_at DESC,
    booking_id DESC
);

CREATE INDEX bookings_customer_idx
ON cs350_plans.bookings (customer_id);

ANALYZE cs350_plans.customers;
ANALYZE cs350_plans.bookings;
```

## 2. Verify Data Distribution

Before investigating performance, inspect the dataset.

```sql id="25h03j"
SELECT COUNT(*)
FROM cs350_plans.bookings;

SELECT status, COUNT(*)
FROM cs350_plans.bookings
GROUP BY status
ORDER BY status;

SELECT hotel_id, COUNT(*)
FROM cs350_plans.bookings
GROUP BY hotel_id
ORDER BY COUNT(*) DESC, hotel_id;
```

### Expected distribution

There are exactly 300,000 bookings.

The status distribution is:

| Status | Rows |
|---|---:|
| confirmed | 240,000 |
| pending | 30,000 |
| cancelled | 30,000 |

Hotel 1 contains 255,000 bookings.

The remaining 45,000 bookings are distributed across other hotels.

These values establish why different predicates have very different selectivity.

---

# Experiment A — PG-01: The Index That Loses

## Starting Symptom

A report sums captured amounts for all confirmed bookings.

A developer insists that PostgreSQL should use the status index.

But confirmed bookings represent eighty percent of the table.

### Step A1 — Predict

Before running the query, answer:

Would you expect a sequential scan or an index-based strategy to be cheaper?

What physical work would each plan perform?

What columns are required?

Does the status index contain everything needed to calculate the sum?

### Step A2 — Measure the normal plan

Run the report with PostgreSQL's normal planner choices.

```sql id="0tfbv4"
EXPLAIN (ANALYZE, BUFFERS)
SELECT SUM(amount_eur)
FROM cs350_plans.bookings
WHERE status = 'confirmed';
```

Record:

- Scan method.
- Estimated rows.
- Actual rows.
- Buffer hits and reads.
- Execution time.

If the planner chooses a parallel plan, record that too.

### Step A3 — Compare an alternative access strategy

For a controlled comparison, temporarily discourage sequential scans.

Also disable parallel workers in both measurements to simplify the comparison.

```sql id="op2vt7"
BEGIN;

SET LOCAL max_parallel_workers_per_gather = 0;

EXPLAIN (ANALYZE, BUFFERS)
SELECT SUM(amount_eur)
FROM cs350_plans.bookings
WHERE status = 'confirmed';

SET LOCAL enable_seqscan = off;

EXPLAIN (ANALYZE, BUFFERS)
SELECT SUM(amount_eur)
FROM cs350_plans.bookings
WHERE status = 'confirmed';

ROLLBACK;
```

This setting discourages sequential scans but does not absolutely prohibit them.

PostgreSQL may choose an index scan or a bitmap-based plan.

The result depends on its available alternatives.

### Step A4 — Explain the difference

Compare the two plans.

Does the indexed strategy perform additional heap accesses?

Does it touch more or fewer buffers?

Is the sequential scan faster?

If the indexed plan is not slower on your machine, explain why that might happen rather than inventing a result.

Possible factors include caching, table size, storage characteristics, and the selected index strategy.

### Acceptance criteria

You can explain why using an index isn't automatically better.

You can distinguish plan cost estimates from measured execution time.

You can defend PostgreSQL's normal choice using evidence.

You have not changed global planner settings.

---

# Experiment B — The Rare Hotel

## Starting Symptom

Hotel 12 has a small fraction of the total bookings.

The admin interface wants its twenty newest reservations.

### Step B1 — Run the query

```sql id="qm12ys"
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    booking_id,
    booked_at,
    amount_eur
FROM cs350_plans.bookings
WHERE hotel_id = 12
ORDER BY booked_at DESC, booking_id DESC
LIMIT 20;
```

### Step B2 — Investigate

Which index can support both the hotel filter and the requested order?

Does PostgreSQL need an explicit sort?

How many rows does it actually retrieve?

What happens if you use a different hotel ID?

Try Hotel 1 and Hotel 12.

### Step B3 — Disable index scans temporarily

Inside a transaction, compare plans with relevant index strategies discouraged.

Do not treat the altered settings as a production recommendation.

### Acceptance criteria

You can explain why the composite index is useful.

You understand that an index can support filtering and ordering simultaneously.

You can explain why the same query shape may have different costs for different parameter values.

---

# Experiment C — The Cardinality Estimate That Doesn't Understand Correlation

## Starting Symptom

The planner estimates rows for a combination of hotel and status values that cannot actually occur in this fixture.

### Step C1 — Inspect the data

Determine whether Hotel 12 has any confirmed bookings.

Run a direct count first.

```sql id="vce9gt"
SELECT COUNT(*)
FROM cs350_plans.bookings
WHERE hotel_id = 12
  AND status = 'confirmed';
```

### Step C2 — Inspect the estimate

```sql id="n7wx9m"
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM cs350_plans.bookings
WHERE hotel_id = 12
  AND status = 'confirmed';
```

Compare the estimated and actual row counts.

What assumptions might explain the difference?

### Step C3 — Add multivariate statistics

Create a statistics object describing the relationship between hotel ID and status.

```sql id="8lk6rj"
CREATE STATISTICS bookings_hotel_status_stats
    (mcv, dependencies)
ON hotel_id, status
FROM cs350_plans.bookings;

ANALYZE cs350_plans.bookings;
```

### Step C4 — Measure again

Run the same `EXPLAIN ANALYZE`.

Did the estimated cardinality change?

Did PostgreSQL choose a different plan?

Did execution time improve?

These outcomes are not guaranteed.

The useful result is understanding whether the statistics improved the planner's knowledge of this particular data distribution.

### Acceptance criteria

You can explain why ordinary single-column statistics may misestimate correlated predicates.

You understand what the extended statistics object describes.

You have compared estimates before and after collecting it.

---

# Experiment D — Loops and Repeated Index Lookups

## Starting Symptom

A query retrieves bookings for a relatively small hotel and joins them to customer information.

One plan may perform repeated customer lookups.

### Step D1 — Inspect the normal plan

```sql id="txsb4b"
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    b.booking_id,
    c.name,
    c.segment
FROM cs350_plans.bookings b
JOIN cs350_plans.customers c
    ON c.customer_id = b.customer_id
WHERE b.hotel_id = 12;
```

### Step D2 — Examine the join algorithm

Does PostgreSQL choose a nested loop, hash join, or another strategy?

If it chooses a nested loop, inspect the inner lookup's `loops` count.

How many times does the lookup run?

### Step D3 — Compare another join strategy

For a diagnostic comparison, discourage hash and merge joins within a transaction.

```sql id="evnm9s"
BEGIN;

SET LOCAL enable_hashjoin = off;
SET LOCAL enable_mergejoin = off;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    b.booking_id,
    c.name,
    c.segment
FROM cs350_plans.bookings b
JOIN cs350_plans.customers c
    ON c.customer_id = b.customer_id
WHERE b.hotel_id = 12;

ROLLBACK;
```

### Step D4 — Explain the actual work

Identify the outer input.

Identify the inner input.

Record the inner node's loop count.

Multiply average rows per execution by loops to estimate the total rows returned by that node.

Explain why the strategy can be reasonable for a small input but expensive for a large one.

### Acceptance criteria

You can read `loops` correctly.

You do not sum parent and child timings as independent costs.

You can explain the conditions under which nested loops are appropriate.

---

# Experiment E — Sorting Under Memory Pressure

## Starting Symptom

An administrative export sorts a large collection of bookings by amount.

The query performs a substantial sort.

### Step E1 — Measure the normal sort

```sql id="b57i1r"
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    booking_id,
    amount_eur
FROM cs350_plans.bookings
ORDER BY amount_eur DESC, booking_id ASC;
```

Look for the Sort node.

Record its method and memory usage.

### Step E2 — Constrain the sort memory

Run a diagnostic transaction with a small `work_mem` value.

```sql id="g9b26h"
BEGIN;

SET LOCAL work_mem = '64kB';

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    booking_id,
    amount_eur
FROM cs350_plans.bookings
ORDER BY amount_eur DESC, booking_id ASC;

ROLLBACK;
```

### Step E3 — Investigate

Does the sort use temporary disk space?

Are temporary buffers reported?

What changes when memory is less constrained?

Why would increasing `work_mem` globally be dangerous?

### Acceptance criteria

You can recognize an in-memory versus disk-based sort.

You understand that `work_mem` applies to individual operations rather than representing a global query memory cap.

You can explain why changing memory settings is not a substitute for understanding the query.

---

# Experiment F — Deep Pagination Versus Keyset Pagination

## Starting Symptom

The reservations dashboard is fast on page one and much slower on deep pages.

### Step F1 — Measure a deep offset

```sql id="e6u2y2"
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    booking_id,
    booked_at
FROM cs350_plans.bookings
WHERE hotel_id = 1
ORDER BY booked_at DESC, booking_id DESC
LIMIT 20 OFFSET 150000;
```

### Step F2 — Examine the plan

Does the index support the ordering?

How many rows flow into the Limit node?

How much work occurs despite returning twenty rows?

### Step F3 — Obtain a cursor

Find the row immediately preceding the desired page.

This one-time query establishes the cursor for the experiment.

```sql id="tctopm"
SELECT
    booked_at,
    booking_id
FROM cs350_plans.bookings
WHERE hotel_id = 1
ORDER BY booked_at DESC, booking_id DESC
OFFSET 149999
LIMIT 1;
```

Record its timestamp and booking ID.

### Step F4 — Use keyset pagination

Replace the placeholders with the cursor values you retrieved.

```sql id="q7ijqj"
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    booking_id,
    booked_at
FROM cs350_plans.bookings
WHERE hotel_id = 1
  AND (booked_at, booking_id) <
      (
        TIMESTAMPTZ 'REPLACE_WITH_CURSOR_TIMESTAMP',
        REPLACE_WITH_CURSOR_ID
      )
ORDER BY booked_at DESC, booking_id DESC
LIMIT 20;
```

### Step F5 — Compare

Do the two queries return the same page?

Does the keyset query avoid traversing the large offset?

How do their execution plans differ?

### Acceptance criteria

The returned rows match.

You can explain the keyset predicate.

You can explain why the composite index supports this access pattern.

You understand the trade-off between sequential cursor navigation and arbitrary page jumps.

---

# Experiment G — Generic Versus Custom Plans

## Starting Symptom

The same prepared query performs differently depending on the hotel ID.

### Step G1 — Prepare the query

```sql id="7o1pl7"
PREPARE hotel_total(integer) AS
SELECT SUM(amount_eur)
FROM cs350_plans.bookings
WHERE hotel_id = $1;
```

### Step G2 — Compare custom plans

```sql id="x28axg"
BEGIN;

SET LOCAL plan_cache_mode = force_custom_plan;

EXPLAIN (ANALYZE, BUFFERS)
EXECUTE hotel_total(1);

EXPLAIN (ANALYZE, BUFFERS)
EXECUTE hotel_total(12);

ROLLBACK;
```

### Step G3 — Compare generic plans

```sql id="r8jcgu"
BEGIN;

SET LOCAL plan_cache_mode = force_generic_plan;

EXPLAIN (ANALYZE, BUFFERS)
EXECUTE hotel_total(1);

EXPLAIN (ANALYZE, BUFFERS)
EXECUTE hotel_total(12);

ROLLBACK;
```

### Step G4 — Investigate

Compare the chosen scan methods.

Does the generic plan use the same broad strategy for both parameter values?

Do custom plans account for the different hotel distributions?

Are the execution times meaningfully different?

### Acceptance criteria

You can explain the custom/generic planning trade-off.

You do not recommend globally forcing custom plans without evidence.

You understand why highly skewed parameter values matter.

After the exercise, release the prepared statement:

```sql id="l75xsk"
DEALLOCATE hotel_total;
```

---

# Final Incident — PG-01

## Starting Symptom

A production report uses an index but remains slow.

A colleague proposes forcing indexed access across the application.

You have the SQL query and an `EXPLAIN (ANALYZE, BUFFERS)` result.

Your task is to determine whether the index is actually helping.

### Investigation Packet

Use the plans gathered in Experiment A as your evidence.

Prepare a short written diagnosis containing:

**Business requirement:** What result does the report calculate?

**Observed performance:** What did the measured execution show?

**Execution mechanism:** Which access path did PostgreSQL use?

**Alternative plan:** What happened when another strategy was encouraged?

**Root cause:** Why was one approach cheaper or more expensive?

**Recommendation:** Should the production system change its index strategy, query, statistics, or nothing at all?

**Verification:** How would you validate the recommendation under representative workload conditions?

### Required Defense

Your interviewer asks:

"Why not force PostgreSQL to use the index? We created the index for a reason."

Your answer should explain why an index can be an unsuitable access path for a large matching fraction of the table.

It should also acknowledge that indexes cost storage and write-maintenance work even when they do not improve important queries.

---

# Lab Solutions and Diagnostic Notes

**Do not read this section until you've attempted the investigations.**

## Experiment A — Indexed Access Isn't Automatically Faster

The confirmed status qualifies eighty percent of the table.

An indexed strategy may need to traverse the status index and retrieve a large number of heap rows to access the amount column.

A sequential scan can read the table more directly.

Depending on hardware and cache behavior, the measured difference may vary.

The important diagnosis is the actual work performed by both plans, not a universal claim that sequential scans always win at eighty percent selectivity.

## Experiment B — Composite Index and Ordering

The index on hotel ID, booking timestamp descending, and booking ID descending can support a query filtered by one hotel and ordered by those two fields.

It can potentially avoid a separate sort and stop after producing the required twenty rows.

The actual plan depends on PostgreSQL's cost estimates and the data distribution.

## Experiment C — Correlated Predicates

In the fixture, confirmed bookings occur only within the dominant hotel group.

A query combining a small-hotel ID with confirmed status therefore returns no rows.

Ordinary statistics may estimate positive cardinality because they don't fully represent the relationship between the two columns.

Multivariate statistics can improve estimates for suitable correlated predicates.

The planner may or may not change its physical plan after collecting those statistics.

## Experiment D — Nested Loops

The inner lookup can execute once per outer row.

When PostgreSQL reports average actual rows per execution and a large loop count, the total work is the product of those values.

A nested loop is efficient when the outer input is small and inner lookups are cheap.

It can become expensive when the outer input is unexpectedly large.

## Experiment E — Sort Spilling

A sufficiently large sort with a small memory allowance may spill to temporary disk storage.

The plan reports the sort method and relevant temporary data activity.

Increasing memory may improve the operation, but doing so globally can increase total memory pressure across sessions and parallel workers.

## Experiment F — Deep Pagination

Offset pagination must account for the skipped ordered rows.

Keyset pagination uses the cursor values to seek into the relevant ordering range.

With a suitable composite index, it can avoid traversing the large preceding offset.

The two approaches have different usability and consistency trade-offs.

## Experiment G — Prepared Plans

Custom plans can use actual parameter values.

Generic plans do not depend on those values.

For skewed data, different parameter values may favor different access paths.

The experiment determines whether generic planning creates a meaningful problem for this particular query.

## PG-01 — Final Diagnosis

There is no universal rule that an index scan is superior to a sequential scan.

The planner attempts to minimize estimated total execution cost.

The correct recommendation follows measured evidence.

If the sequential scan consistently performs less work and has better execution time for this report, forcing index access would be counterproductive.

If a particular index provides little benefit across the actual workload while imposing storage and write costs, its usefulness should be reviewed.

But dropping an index requires examining other queries that may rely on it.

A local experiment does not establish the index's system-wide value.

---

# Further Reading

1. **PostgreSQL — Using EXPLAIN**  
   https://www.postgresql.org/docs/current/using-explain.html

2. **PostgreSQL — EXPLAIN Command**  
   https://www.postgresql.org/docs/current/sql-explain.html

3. **PostgreSQL — Planner Statistics**  
   https://www.postgresql.org/docs/current/planner-stats.html

4. **PostgreSQL — CREATE STATISTICS**  
   https://www.postgresql.org/docs/current/sql-createstatistics.html

5. **PostgreSQL — Planner Method Configuration**  
   https://www.postgresql.org/docs/current/runtime-config-query.html

6. **PostgreSQL — Index-Only Scans and Covering Indexes**  
   https://www.postgresql.org/docs/current/indexes-index-only-scans.html

7. **PostgreSQL — PREPARE**  
   https://www.postgresql.org/docs/current/sql-prepare.html

8. **PostgreSQL — pg_stat_statements**  
   https://www.postgresql.org/docs/current/pgstatstatements.html

9. **PostgreSQL — Routine Vacuuming**  
   https://www.postgresql.org/docs/current/routine-vacuuming.html

10. **PostgreSQL — Monitoring Statistics**  
    https://www.postgresql.org/docs/current/monitoring-stats.html

Cross-reference CS330-L02 for foundational planning and index theory, CS350-L01 for SQL composition, and `production-cases/PG-01.md` for the associated incident.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text id="u9c8pv"
CS350-L02 — POSTGRESQL PLAN FORENSICS
================================================

THE CORE QUESTION
-----------------
What physical work produced the result?

THREE PERSPECTIVES
------------------
SQL:
  logical result required

EXPLAIN:
  estimated execution strategy

EXPLAIN ANALYZE:
  measured execution behavior

ESSENTIAL COMMAND
-----------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;

ANALYZE executes the statement.
Beware writes and side effects.

READING A PLAN
--------------
cost=startup..total
rows=estimated output rows
width=estimated average row bytes

actual time=start..finish milliseconds
actual rows=average per execution
loops=number of executions

Total actual rows approximately:
actual rows × loops

Costs are not milliseconds.

Do not sum parent + child timings
as independent durations.

SCANS
-----
Seq Scan:
  read table pages and filter

Index Scan:
  find candidates through index
  may fetch heap rows

Bitmap Index Scan:
  identify candidate locations

Bitmap Heap Scan:
  retrieve relevant heap pages

Index Only Scan:
  can use index-contained data
  may still require heap fetches

INDEX SELECTIVITY
-----------------
Rare predicate:
  index may avoid substantial work

Common predicate:
  sequential scan may be cheaper

Index exists != index should be used.

BUFFERS
-------
shared hit:
  PostgreSQL shared buffer cache hit

shared read:
  page brought into shared buffers
  not necessarily physical disk I/O

temp read/written:
  temporary intermediate storage

Buffer counts describe work,
not guaranteed latency.

FILTERS
-------
Index Cond:
  predicate applied through index access

Filter:
  predicate evaluated after candidate rows

Rows Removed by Filter:
  evidence of rejected candidates

JOINS
-----
Nested Loop:
  outer rows drive repeated inner work

Hash Join:
  build hash table, probe matches

Merge Join:
  combine ordered inputs

No join algorithm is always best.

CARDINALITY
-----------
Estimated rows vs actual rows.

Large mismatch can cause:
- wrong join strategy
- unexpected repeated work
- poor memory assumptions
- unsuitable scan choice

STATISTICS
----------
ANALYZE table:
  refresh planner statistics

CREATE STATISTICS:
  multivariate relationships

Kinds:
- dependencies
- mcv
- ndistinct

Correlated predicates may defeat
single-column independence estimates.

SORTS
-----
Inspect:
  Sort Method
  Memory
  Disk
  temp buffers

LIMIT does not guarantee little work.
Top-N still may scan all candidates.

work_mem is per relevant operation,
not a total query-memory cap.

PAGINATION
----------
LIMIT 20 OFFSET 150000
may process 150020 ordered rows.

Keyset:
WHERE (created_at, id) < (:time, :id)
ORDER BY created_at DESC, id DESC
LIMIT 20

Needs stable ordering and suitable index.

PREPARED PLANS
--------------
Custom plan:
  parameter-specific planning

Generic plan:
  parameter-independent reuse

Skewed values can favor
different physical strategies.

plan_cache_mode:
  auto
  force_custom_plan
  force_generic_plan

Use overrides diagnostically.

ORM FORENSICS
-------------
Capture actual SQL.
Capture parameter values.
Inspect query count.
Inspect execution plan.

N+1:
  many fast queries can produce
  slow application request.

One huge join:
  row multiplication can be expensive.

PG_STAT_STATEMENTS
------------------
Useful for aggregate statement-level
activity and workload identification.

Requires appropriate configuration.

DIAGNOSTIC SEQUENCE
-------------------
1. Confirm DB latency.
2. Capture real SQL/parameters.
3. Inspect measured plan.
4. Compare estimated vs actual rows.
5. Inspect loops.
6. Inspect buffers and heap fetches.
7. Inspect sorts and hashes.
8. Identify root cause.
9. Test smallest plausible fix.
10. Verify correctness and performance.

RED FLAGS
---------
"An index scan must be faster."
"Sequential scan means missing index."
"LIMIT 20 means 20 rows processed."
"cost=100 means 100 milliseconds."
"Actual rows ignore loops."
"Shared read equals physical disk read."
"Every CTE is materialized."
"EXPLAIN ANALYZE is harmless for writes."
"Increase work_mem globally."
"Force the planner to use my index."

MENTAL MODEL
------------
Estimate → Plan → Execute → Measure.

Explain the work.
Explain the cost.
Explain the correction.
Verify with evidence.

NEXT
----
CS350-L03 — PostgreSQL Under Production Pressure
```
