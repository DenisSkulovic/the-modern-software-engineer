---
id: CS330-L02
course: CS330
title: "SQL and Query Performance"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [BACK301-S03]
prev: CS330-L01
next: CS330-L03
---

# CS330 — Relational Databases and Transactions

## Lecture 02: SQL and Query Performance

*The same SQL query takes fifteen milliseconds in development and four seconds in production. The database is healthy. The query is correct. Yet it performs far more work than necessary. To understand why, we need to stop thinking about SQL as instructions and start thinking about the physical work behind an answer.*

# Part I — Intuition

## The picture to carry in your head

Imagine a vast archive containing fourteen million reservation records.

You're the archive manager. A colleague arrives with a question:

"Show me the twenty-five most recent confirmed reservations for Hotel 482 during October."

The request sounds simple.

Twenty-five records. One hotel. One month.

Surely finding them should be easy.

But that depends entirely on how the archive is organized.

If the records are stored in boxes according to the order they arrived, you may need to inspect an enormous number of boxes before you can identify the relevant reservations.

If you have an organized catalogue of reservations by hotel and check-in date, you can navigate directly to the relevant section and retrieve the required entries.

The question hasn't changed.

The number of records requested hasn't changed.

What changed is the **physical work required to answer it**.

This is the central idea of SQL performance.

A SQL query describes a result. PostgreSQL chooses an execution strategy for producing that result.

Sometimes the strategy is excellent.

Sometimes it is reasonable for one dataset and terrible for another.

And sometimes the database makes the wrong choice because its understanding of the data is incomplete.

## 1. SQL describes the destination, not the route

In ordinary application code, we often specify an algorithm.

Take an array.

Filter it.

Sort it.

Return the first twenty-five elements.

SQL is different.

We describe the records we want, the conditions they must satisfy, and the ordering we require.

The database has considerable freedom to decide how to retrieve them.

It might scan a table.

It might navigate an index.

It might combine several indexes.

It might join records using a nested loop, a hash table, or sorted streams.

It might avoid sorting because the required order already exists in an index.

That freedom is one of the great strengths of relational databases.

But it also creates a responsibility for engineers: **understand the physical plan chosen for an important query**.

A correct SQL statement does not guarantee an efficient execution plan.

## 2. An index is a second organization of the same data

Return to the archive.

Suppose the original reservations are stored in large boxes, roughly according to when they were inserted.

We create a separate catalogue sorted by hotel identifier and check-in date.

Each catalogue entry contains the relevant search keys and a way to locate the original record.

Now finding Hotel 482's October reservations can be dramatically faster.

That's the intuition behind a B-tree index.

It doesn't ordinarily rearrange the whole table into the desired order.

It maintains a separate searchable structure.

That structure costs space.

It also costs work to maintain whenever relevant data is inserted or modified.

An index is therefore a trade: extra storage and write maintenance in exchange for faster access to particular patterns of data.

And it only helps when the access pattern can use it effectively.

## 3. An index isn't useful merely because it exists

Imagine a reservation database where ninety-two percent of all records have status `confirmed`.

You create an index on the status column.

Then you ask for every confirmed reservation.

Should PostgreSQL use the index?

Not necessarily.

If almost every row qualifies, navigating through an index and retrieving the corresponding table data may be more expensive than scanning the table directly.

Now imagine asking for the tiny minority of reservations with status `pending_review`.

An index may be extremely useful.

The difference is **selectivity**: how much of the dataset a condition eliminates.

The best access path depends not simply on whether a column has an index, but on how many rows the query needs and how expensive retrieving them will be.

## 4. The catalogue must match the question

Suppose our archive catalogue is organized by hotel, then by check-in date.

That's excellent for questions that begin with a hotel.

But a query asking for every reservation across every hotel on one particular date may not benefit in the same way.

The leading organization is different.

This is why composite-index column order matters.

An index on hotel followed by date is not interchangeable with an index on date followed by hotel.

And an index that also supports the desired ordering can sometimes avoid an expensive sort.

A thoughtfully selected composite index can be more useful than several unrelated single-column indexes.

The right design follows the workload.

## 5. The planner must estimate the journey

How does PostgreSQL choose between scanning the table and using an index?

It estimates the cost of possible execution strategies.

To do that, it needs information about the data.

How many rows exist?

How many hotels?

What proportion of reservations are confirmed?

How are check-in dates distributed?

Do particular values occur frequently?

The planner doesn't usually execute every candidate strategy to find out which is fastest.

It makes estimates.

That means it can be wrong.

Suppose one hotel has ten thousand reservations while another has five million.

A query that works well for the first may behave very differently for the second.

And if the planner estimates one hundred matching rows when the actual result contains one hundred thousand, it may choose a poor execution strategy.

This is why understanding query plans is more valuable than applying database folklore.

## 6. One screen can hide enormous work

Our support dashboard displays twenty-five reservations.

But what if the backend retrieves twenty-five reservations and then issues one separate query to load each customer's name?

One screen now requires twenty-six database operations.

What if it retrieves a hundred reservations?

One hundred and one operations.

This is the classic N-plus-one problem.

Alternatively, the backend might construct one enormous join that multiplies reservation rows across several one-to-many relationships.

That's a different kind of waste.

And a page requested using an enormous `OFFSET` may force PostgreSQL to identify and skip many records before returning just twenty-five.

The visual simplicity of the final screen tells us almost nothing about the work performed underneath.

## Three questions before the Deep Dive

Try explaining these aloud.

1. Why can a sequential scan be faster than an index scan even when an appropriate index exists?
2. Why can two queries using the same columns benefit from different index orders?
3. Why might an endpoint returning only twenty-five records require the database to examine hundreds of thousands of rows?

If you understand these distinctions, you have the foundation.

**Query performance is about minimizing the cost of producing the requested result, not merely minimizing the number of rows returned.**

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The query that became 250 times slower

It's Monday morning.

The customer-support team reports that the reservation dashboard has become painfully slow.

An employee selects Hotel 482, chooses October, and waits four seconds for the latest twenty-five confirmed reservations.

You find the SQL query.

It filters by hotel identifier, confirmed status, and an October check-in range.

It orders by check-in date descending, using reservation ID as a secondary ordering key.

Then it limits the result to twenty-five rows.

On the development database, it takes approximately fifteen milliseconds.

In production, it takes four seconds.

The SQL is identical.

The query is logically correct.

The difference is the data and the physical execution path.

The production table contains fourteen million reservations.

And the current plan performs much more work than the desired twenty-five-row result suggests.

Let's investigate how PostgreSQL produces an answer.

## 2. A table isn't an array in memory

A common mental mistake is imagining a PostgreSQL table as one enormous JavaScript array.

We picture rows sitting next to one another, waiting to be filtered.

But PostgreSQL stores table data in pages—commonly eight-kibibyte pages in a standard build.

Its ordinary row storage is called the **heap**.

The word doesn't refer to a heap priority-queue data structure.

It describes the table's storage organization, which is not intrinsically ordered by hotel ID, check-in date, or some other business column.

A table page can contain multiple row versions and associated storage metadata.

PostgreSQL also uses multiversion concurrency control, or MVCC, so different row versions can exist for transactional reasons.

We'll study those details in L03.

For now, the important consequence is that asking for rows in a particular logical order does not mean the table is physically arranged that way.

### Sequential scans

A sequential scan visits table pages and evaluates the relevant predicates against the rows.

For a small table, this can be extremely efficient.

For a query that needs most of a large table, it can also be efficient.

Scanning pages in sequence can be cheaper than following many scattered index references.

But for a query matching only a tiny fraction of fourteen million rows, scanning the entire table may perform vastly more work than necessary.

The question is not whether sequential scans are good or bad.

It's whether scanning the table is a sensible way to answer this particular question.

## 3. B-tree indexes: the physical shortcut

PostgreSQL's default index type is B-tree.

A B-tree organizes search keys in a balanced, ordered structure.

Internal index pages guide navigation toward the appropriate region.

Leaf pages contain index entries associated with table locations, subject to the index's design and implementation.

This allows PostgreSQL to locate relevant entries without examining every table row.

### The two-stage lookup

Suppose an index contains hotel ID and check-in date.

The database navigates to the relevant index entries.

But our query also needs customer ID, checkout date, and other columns.

If those values aren't available in the index, PostgreSQL may need to retrieve the corresponding table rows from the heap.

This creates an important performance distinction.

Finding an index entry can be cheap.

Following a large number of index entries to scattered heap pages may be expensive.

If one hundred rows match, those lookups might be trivial.

If ten million rows match, the same access strategy might be terrible.

The index isn't a substitute for understanding selectivity and physical locality.

### The primary key is also an index

PostgreSQL normally supports primary-key uniqueness through an appropriate unique index.

That makes searching by a primary key efficient.

But it doesn't automatically help queries filtered by hotel and check-in date.

An index on reservation ID answers a different class of questions.

The existence of a primary key isn't a complete indexing strategy.

## 4. Selectivity: how much data can we avoid?

Imagine three queries against fourteen million reservations.

The first retrieves one reservation by primary key.

The second retrieves every confirmed reservation, representing perhaps seventy percent of the table.

The third retrieves confirmed reservations for Hotel 482 during October, perhaps a very small fraction of the entire dataset.

All three use filters.

But their selectivity differs dramatically.

### Highly selective predicates

A condition matching one row out of fourteen million is highly selective.

An index can often locate the matching entry with comparatively little work.

### Low-selectivity predicates

A condition matching ten million rows is not selective.

If the query also needs many columns from the table, retrieving them through an index may offer little advantage.

A sequential scan may be cheaper.

### Combined predicates

A hotel identifier may narrow the search substantially.

A date range may narrow it further.

Status might eliminate additional records.

The important thing is how the conditions combine.

An index optimized for the combined access pattern can sometimes avoid large amounts of unnecessary reading.

### The dangerous assumption about a boolean index

Consider indexing `is_active` when almost every row has `is_active = true`.

That index may offer little benefit for the majority case.

But an index targeting the rare inactive or problematic records could be valuable.

The design follows the distribution of values and the queries that actually matter.

**An index is useful when it avoids enough work to justify using it.**

## 5. Composite indexes: column order is a strategy

Now let's examine our hotel dashboard.

It filters by hotel ID and a check-in date range, requires confirmed reservations, and orders by check-in date descending with reservation ID as a tie-breaker.

A candidate B-tree index uses hotel ID first, then check-in date descending, then reservation ID descending.

Why that order?

Because the query begins with one particular hotel.

The leading equality condition narrows the relevant portion of the index.

Within that hotel, the date column can support both range filtering and the required ordering.

The ID provides a deterministic order for rows sharing the same check-in date.

A suitable index might look like this:

```sql
CREATE INDEX idx_reservations_hotel_date
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
);
```

The important part for listening is the sequence: first identify the hotel, then move through its reservations in the desired date order, breaking ties by ID.

### Equality before range: a useful starting principle

For a common B-tree query pattern, equality conditions on leading index columns followed by a range condition can be effective.

For instance, an index on hotel ID and check-in date is naturally aligned with a query for one hotel and a bounded date range.

But don't turn this into the superstition that every equality column must appear first regardless of the required ordering or workload.

Index design depends on filters, sorting, result sizes, and actual plan behavior.

### What if the query filters only by date?

An index organized first by hotel may be much less useful for an all-hotels date search.

PostgreSQL can sometimes exploit multicolumn B-tree indexes using techniques such as skip scans, depending on the distribution of leading-column values and the expected cost.

But that doesn't make column order irrelevant.

For an index with thousands of distinct hotel IDs, repeatedly searching hotel-specific regions may be more expensive than another access path.

The first principle remains: **design the index around the query patterns that matter most, and verify what the planner actually does**.

## 6. Partial indexes: index only the relevant subset

Our dashboard displays confirmed reservations.

It doesn't need pending, canceled, or expired records.

Why should its index contain every reservation?

PostgreSQL supports **partial indexes**.

A partial index contains entries only for rows satisfying a defined predicate.

For example, we can index hotel, check-in date, and reservation ID only where status equals `confirmed`.

That can make the index smaller and more targeted than a corresponding full-table index.

```sql
CREATE INDEX idx_confirmed_reservations_hotel_date
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
WHERE status = 'confirmed';
```

This index is attractive when confirmed-reservation queries are common and the reduction in index size or access work is valuable.

But partial indexes have an important limitation.

### The planner must prove the predicate applies

PostgreSQL can use a partial index only when it can establish that the query's conditions imply the index predicate.

If the query explicitly requires `status = 'confirmed'`, that relationship is straightforward.

But imagine a generic prepared plan using `status = $1`.

The parameter might later be `confirmed`, `pending`, or something else.

A generic plan cannot simply assume every possible value satisfies the partial-index predicate.

It may therefore be unable to use the index.

A custom plan generated for a particular parameter value can behave differently.

This explains why an index may look perfect in a SQL console yet not appear in the application's actual prepared-query plan.

**The query the planner sees matters—not merely the query you imagined writing.**

## 7. Covering indexes and index-only scans

Now suppose our dashboard needs customer ID in addition to the indexed hotel, date, and reservation ID.

A normal index scan may need to visit the heap to retrieve customer ID.

PostgreSQL supports included columns through `INCLUDE`.

These columns are stored as index payload rather than as ordinary search-order keys.

A covering partial index could include customer ID to make more of the selected data available directly from the index.

```sql
CREATE INDEX idx_confirmed_dashboard
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
INCLUDE (customer_id, check_out)
WHERE status = 'confirmed';
```

Now the index may contain everything needed for some dashboard queries.

That creates the possibility of an **index-only scan**.

But the name is slightly misleading.

### Why index-only doesn't guarantee zero heap visits

PostgreSQL uses MVCC to determine which row versions are visible to a transaction.

An index entry doesn't by itself contain all the information needed to establish visibility.

PostgreSQL uses a visibility map to identify heap pages whose tuples can be considered visible without checking each row version.

If the relevant heap page isn't marked appropriately, even an index-only scan may need a heap fetch.

This is why `EXPLAIN ANALYZE` can show an `Index Only Scan` with nonzero `Heap Fetches`.

Index-only scans tend to be particularly attractive for suitable queries against relatively stable data.

On frequently updated tables, visibility checks and index-maintenance costs may reduce the benefit.

And including more columns makes the index larger.

The question isn't whether an index can theoretically cover a query.

It's whether doing so improves the real workload enough to justify the storage and write costs.

## 8. `EXPLAIN`: the database tells us its plan

So far, we've reasoned about possible access paths.

But how do we learn what PostgreSQL actually intends to do?

We use `EXPLAIN`.

A plan is a tree of operations.

Its leaf nodes obtain data.

Other nodes filter, join, aggregate, sort, or limit it.

### Sequential scan

A `Seq Scan` reads table pages and evaluates conditions.

It can be entirely appropriate when many rows are needed.

### Index scan

An `Index Scan` navigates an index and typically retrieves matching table rows.

It can be useful when the index narrows the search or provides an advantageous order.

### Bitmap index and heap scans

A `Bitmap Index Scan` identifies candidate heap locations.

A `Bitmap Heap Scan` then retrieves relevant table pages.

This can reduce inefficient scattered heap access for certain result sizes.

### Index-only scan

An `Index Only Scan` attempts to obtain required data from the index while checking visibility as needed.

### Sort, join, and limit nodes

Other plan nodes arrange or combine the data.

A `Sort` may process many rows even when a parent `Limit` returns only a few.

A join node may execute a child operation repeatedly.

A limit node may be able to stop an underlying scan early—or may sit above operations that already did substantial work.

The plan tells us much more than whether an index exists.

It shows the sequence of physical operations the database expects to perform.

## 9. `EXPLAIN ANALYZE`: expectations versus actual work

Plain `EXPLAIN` tells us the chosen plan and its estimates.

`EXPLAIN ANALYZE` executes the query and reports what actually happened.

With the `BUFFERS` option, we can also inspect useful buffer-accounting information.

This is where database performance diagnosis becomes much more concrete.

### Estimated cost isn't elapsed time

A plan node has estimated startup and total costs.

These numbers are measured in PostgreSQL's internal cost units.

They are not milliseconds.

An estimated cost of 100 doesn't mean PostgreSQL predicts the query will take one hundred milliseconds.

Costs exist primarily to compare alternative plans within the planner's model.

### Estimated rows versus actual rows

Suppose the planner expects eighty rows from a particular index scan.

But the actual execution produces 3,100.

That is almost a fortyfold underestimate.

The planner may have chosen an index scan believing it would perform a small number of heap lookups.

Instead, it performed thousands.

Perhaps a different strategy would have been cheaper.

The mismatch between estimated and actual row counts is often more informative than the presence of a particular scan type.

### Loops multiply work

Imagine a nested-loop join.

The inner index scan executes ten thousand times.

Its plan output reports one row per loop and an average time of a few microseconds.

That sounds cheap.

But the operation was repeated ten thousand times.

The cumulative work can be significant.

When reading `EXPLAIN ANALYZE`, always inspect `loops`.

The reported actual row counts and timings for a node are generally averages per execution. Repeated execution changes their meaning.

### Buffer hits and reads

A plan may report shared-buffer hits and reads.

A shared hit means PostgreSQL found a required page in its own shared buffer cache.

A shared read means a block was brought into those buffers.

It doesn't automatically prove that the block came from physical disk; the operating system's page cache may have supplied it.

This matters when someone interprets a buffer-read count as a literal disk-operation count.

Buffer statistics reveal important patterns of database work, but they must be interpreted according to their actual semantics.

### Why `ANALYZE` isn't a harmless prefix

`EXPLAIN ANALYZE` really executes the statement.

For an `UPDATE` or `DELETE`, that can modify data.

Even a `SELECT` can consume significant resources, invoke functions with side effects, or produce heavy load under certain conditions.

Use a controlled environment or a carefully planned production-safe investigation.

And remember that the executor's reported time isn't necessarily the entire application-observed latency.

Connection-pool waiting, network transport, serialization, and application processing can add time outside the measured executor interval.

## 10. Why the planner sometimes chooses badly

PostgreSQL's optimizer estimates result sizes from collected statistics.

These include row counts, distinct-value estimates, histograms, and common-value information.

The estimates are useful but imperfect.

They may become stale as data changes.

They may also miss important relationships between columns.

### The correlation trap

Suppose Hotel 482 accounts for one percent of all reservations.

And five percent of reservations belong to Lithuania.

If the planner treats hotel ID and country as independent, it may estimate that a query filtering on both selects approximately one percent multiplied by five percent of the table.

That's only 0.05 percent.

But if nearly every reservation for Hotel 482 is in Lithuania, the actual result could be close to one percent.

The estimate is wrong by roughly a factor of twenty.

That's a substantial difference for a cost-based optimizer.

PostgreSQL can use **extended statistics** to learn certain cross-column relationships, including functional dependencies and frequent combinations of values.

Creating suitable extended statistics can improve particular cardinality estimates.

But it's not a universal cure for arbitrary join correlations or every range-predicate problem.

### Stale statistics

Suppose our production table has grown from one hundred thousand rows to fourteen million.

Or reservations become concentrated among a small number of unusually large hotels.

If statistics no longer reflect the relevant distribution, the planner can make poor choices.

Autovacuum and auto-analyze normally maintain statistics, but exceptional workloads sometimes require targeted investigation.

Refreshing statistics is useful when they are stale.

It will not magically create an index that doesn't exist.

And it won't fix an API waiting four seconds for a database connection when the SQL itself executes in ten milliseconds.

**A planner can only optimize using the information and access paths available to it.**

## 11. Joins: different ways to combine relationships

In CS330-L01, we normalized the hotel schema.

Reservations reference customers.

Reservation items reference room types.

That means producing a complete dashboard may require joins.

A join specifies a logical relationship.

PostgreSQL still must choose how to execute it.

Three algorithms are particularly useful to recognize.

### Nested-loop join

Imagine retrieving twenty-five reservations, then looking up each customer through the customer's primary-key index.

That's a nested-loop pattern.

For every reservation, retrieve the matching customer.

With a small outer result and cheap indexed lookups, this can be extremely efficient.

But suppose the outer input contains one million reservations.

Now the inner operation may execute one million times.

The same algorithm may become expensive.

The important evidence is the number of outer rows and inner-loop executions.

A nested-loop join is not inherently bad.

A nested loop with a huge unexpected outer input often is.

### Hash join

PostgreSQL can build an in-memory hash table from one input, using the join key.

Then it scans the other input and probes the hash table.

This is often useful for joining substantial datasets on equality conditions.

But building the hash table consumes memory.

If it cannot fit within the relevant memory budget, the operation may need batching and temporary storage.

The best join algorithm depends on input size, filtering, memory, and other costs.

### Merge join

If both inputs are sorted on the join key, PostgreSQL can advance through them together.

This can be efficient for large sorted inputs.

But obtaining the sorted order may itself require work.

An index might already provide a suitable order.

Alternatively, PostgreSQL may need to sort an input before merging.

### Join order matters too

With several tables, the optimizer must decide which relationships to combine first.

Imagine joining five tables before applying a highly selective hotel filter.

That could create a large intermediate result.

A plan that narrows relevant rows earlier may be much cheaper.

But the planner's ability to choose that strategy depends on estimated cardinalities and supported transformations.

When row estimates are wrong, join plans can go wrong in surprisingly expensive ways.

## 12. The ORM trap: one page, 101 queries

Now let's move back to the Node.js application.

The dashboard retrieves one hundred reservations.

For each reservation, the application separately looks up the customer's name.

The result is correct.

But the application performs one query for reservations and another hundred queries for customers.

This is the **N-plus-one query problem**.

Each lookup may be cheap in isolation.

Together, they can incur substantial network round trips, database scheduling, and execution overhead.

### Two common solutions

One option is a join that retrieves reservation and customer information together.

Another is to retrieve the page of reservations, then fetch all relevant customers in one batched query.

Which is better?

It depends on the data shape and query requirements.

A join is often excellent for a straightforward many-to-one relationship.

But when a query joins several one-to-many relationships, result rows may multiply.

Suppose one reservation has five items and three related events.

Joining both child collections carelessly can produce fifteen combinations for that reservation.

The ORM might reconstruct the desired objects.

But the database still produced and transferred the multiplied rows.

This is **join-induced row explosion**, a different failure from N-plus-one.

A useful strategy for complex API responses is:

First, retrieve the appropriate page of primary entities.

Then fetch related collections through a small number of batched queries.

Finally, assemble the response.

This may be easier to reason about than one enormous join.

The point isn't that ORMs are bad.

It's that they cannot eliminate the physical consequences of the SQL they generate.

A senior engineer should know how to inspect that SQL.

## 13. Sorting: why `LIMIT 25` can still be expensive

Our query asks for the newest twenty-five reservations.

It uses an `ORDER BY` clause and a `LIMIT`.

Surely PostgreSQL only needs to examine twenty-five rows?

Not necessarily.

Without a suitable ordered access path, it may need to examine every matching reservation before identifying the newest twenty-five.

PostgreSQL may use a bounded top-N sorting strategy rather than fully sorting every row in the conventional sense.

That's an optimization.

But it still needs to consider the candidate rows.

### Index order can avoid the sort

A B-tree index aligned with the filter and requested ordering can allow PostgreSQL to retrieve rows already in the desired order.

It may then stop once enough qualifying rows have been found.

This can be dramatically faster than scanning and sorting a large matching set.

But the index must match the actual query requirements.

A residual filter may cause PostgreSQL to examine additional index entries before it finds twenty-five qualifying rows.

The difference between twenty-five rows returned and twenty-five entries examined still matters.

### Sorting can use temporary storage

Large sorts can exceed the memory made available to the operation.

PostgreSQL may then use temporary files.

That creates additional I/O.

In an execution plan, sort methods and temporary-block activity can help reveal this behavior.

Increasing a memory setting might help a particular operation, but it also increases potential memory consumption across concurrently executing operations.

Again, more memory isn't a universal substitute for an appropriate access path.

## 14. Pagination: page 10,000 isn't like page 1

The dashboard displays reservations in pages of twenty-five.

Page one uses an offset of zero.

Page two skips twenty-five rows.

Now imagine a user navigating to page ten thousand.

The query requests twenty-five rows after skipping 249,975 earlier results.

Even with an appropriately ordered index, PostgreSQL generally must traverse the relevant earlier entries to reach that position.

Those skipped rows aren't free.

Large offsets can make late pages increasingly expensive.

### Keyset pagination

Instead of saying "skip the first 249,975 rows," we can describe where the next page begins.

Suppose the last row of the previous page had check-in date October 17, 2026, and reservation ID 10,842.

Our ordering is by check-in date descending and ID descending.

The next-page predicate asks for rows whose pair of values is less than that final pair.

This is **keyset pagination**, sometimes exposed through an opaque cursor.

A suitable composite index can navigate to the continuation point efficiently.

The database no longer needs to walk through every earlier page merely to skip it.

### Why the ID matters

Many reservations can share the same check-in date.

If we use only the date, pagination may skip records sharing that date or repeat them incorrectly.

Including a unique tie-breaker establishes a stable total ordering for the query.

### The limits of cursors

Keyset pagination is especially useful for sequential navigation through large result sets.

But it makes arbitrary jumps to numbered pages more difficult.

Cursors also need to match the original filters and sorting definition.

And they don't automatically provide a consistent database snapshot across several HTTP requests.

If records are inserted or updated between pages, the results can change.

The correct pagination strategy depends on product behavior and consistency requirements.

The broader insight is that pagination changes the physical query workload.

It's not merely a frontend presentation decision.

## 15. Every index has an ongoing cost

We've spent most of this lecture investigating the value of indexes.

Now consider a table with fifteen indexes.

Every inserted row may require updates to several index structures.

Changes to indexed values can require additional maintenance.

Indexes consume storage and cache capacity.

They contribute to write amplification, WAL generation, and maintenance work.

Not every index affects every update identically. PostgreSQL's storage and update mechanisms introduce important nuances, including cases where certain updates can avoid index modifications.

But the general trade-off remains: indexes speed particular reads at a cost to other operations.

### The wrong index can be an expensive decoration

Suppose we add an index on a column rarely used for filtering or ordering.

The planner hardly ever selects it.

Yet the database must continue maintaining it where relevant.

The index provides little value while consuming resources.

A better approach is workload-driven index design.

Identify important queries.

Examine their filters, ordering, joins, and actual plans.

Choose indexes that reduce substantial work.

Then measure the effect on reads and writes.

### Indexes should be treated as an investment

A useful index has an expected return.

That return may be lower response latency, improved throughput, reduced I/O, or more predictable tail performance.

Its costs include storage, maintenance, write overhead, and migration complexity.

This is why adding five indexes to fix one slow query is not automatically a good engineering decision.

Find the smallest set that materially improves the important workload.

## 16. Reconstructing the four-second query

We now have enough knowledge to investigate our original incident.

The support dashboard takes four seconds.

The SQL is correct.

The production table contains fourteen million rows.

What should we do?

### First, verify that the database query is actually slow

The API might spend time waiting for a database connection, performing authorization checks, serializing large responses, or calling another service.

Measure the actual SQL execution interval separately from the HTTP request duration.

If the query finishes in twenty milliseconds, optimizing its index probably won't resolve a four-second endpoint.

### Second, capture the real SQL and parameters

If the application uses an ORM, inspect the generated statement.

Include the actual parameter values or representative parameter distributions.

A query may behave well for most hotels and poorly for one extremely large tenant.

Prepared-statement plan behavior may also matter.

We need to investigate what production actually executes.

### Third, inspect the execution plan

Use `EXPLAIN`, and where safe, `EXPLAIN (ANALYZE, BUFFERS)`.

Look for scans reading far more data than needed.

Look for large sort operations.

Look for repeated nested-loop executions.

Compare estimated and actual row counts.

Check whether an index can supply the requested ordering.

### Fourth, inspect the data distribution

How many reservations belong to Hotel 482?

How many are confirmed?

How many fall within October?

Is this hotel's data distribution unusual?

Are statistics stale?

Does the planner understand important correlations?

The development database's small and uniform data may be a poor model of production.

### Fifth, test the smallest plausible fix

Suppose we discover that PostgreSQL scans and sorts a large number of matching reservations.

A targeted partial composite index on confirmed reservations, organized by hotel and descending check-in date and ID, becomes a reasonable candidate.

We create and test the index in an appropriate environment.

Then repeat the query under representative data.

We inspect the new plan.

Does the database use the index?

Does it avoid the costly sort?

How many rows and pages does it examine?

Does it actually reduce execution time?

### Sixth, evaluate the wider consequences

Our improvement might accelerate dashboard reads.

But does it significantly increase write costs?

Does it create additional storage pressure?

Does it help other hotels and date ranges?

Will the index remain useful as distributions change?

We should measure the relevant workload, not merely celebrate one faster test query.

A good optimization reduces real production cost without introducing unacceptable new costs elsewhere.

---

# The Oral Examination

Answer each question aloud before reading its solution. Explain the likely mechanism and what evidence you'd seek.

**Question 1 — The unused index**

A table has ten million rows, and ninety-two percent of them have status `completed`. PostgreSQL chooses a sequential scan despite an index on status. Is the optimizer necessarily wrong?

**Question 2 — Index ordering**

You frequently query reservations by one hotel, within a check-in date range, ordered by check-in date descending and ID descending. What composite-index design would you consider, and why?

**Question 3 — The partial-index surprise**

You create a partial index for confirmed reservations. A literal query uses it, but a generic prepared query with `status = $1` doesn't. Why?

**Question 4 — The bad row estimate**

A plan expects eighty rows and actually returns 3,100. Why can this cause a poor access-path or join decision?

**Question 5 — The join debate**

A nested-loop join executes twenty-five indexed lookups. Another nested-loop join executes one million. Is the join type itself sufficient to determine which query is efficient?

**Question 6 — The slow LIMIT**

A query returns only twenty-five rows but performs a costly sort. Why doesn't `LIMIT 25` automatically make the query cheap?

**Question 7 — The N-plus-one trap**

An ORM loads one hundred reservations and then separately retrieves each customer's name. What are two reasonable alternatives, and what danger can arise from joining several one-to-many relationships?

**Question 8 — The production diagnosis**

The API takes four seconds, but `EXPLAIN ANALYZE` reports only thirty milliseconds of query execution. What would you investigate before adding an index?

---

# Solutions and Discussion

## Solution 1 — A scan can be cheaper

When most rows satisfy the condition, the index may eliminate little work. Retrieving almost the entire table through many index references can be more expensive than scanning it directly.

Inspect row selectivity, required columns, actual plan behavior, and relevant statistics. An index isn't an obligation to use it.

## Solution 2 — Match equality, range, and order

A candidate B-tree index uses hotel ID first, then check-in date descending, then reservation ID descending.

The hotel equality narrows the search, and the remaining keys align with the date range and requested ordering.

Verify the plan and consider a partial index if confirmed-reservation queries dominate.

## Solution 3 — Predicate implication matters

The partial index includes only rows satisfying its predicate.

A generic plan with an unrestricted status parameter cannot assume the parameter always means confirmed.

The planner must establish that the query predicate implies the index predicate for the relevant plan.

A custom parameter-specific plan may behave differently.

## Solution 4 — The cost estimate was based on the wrong cardinality

The planner may choose many individual index lookups or a particular join strategy because it expects a small result.

If the actual result is much larger, the chosen plan may perform far more work than expected.

Investigate statistics, correlations, and the access paths available.

## Solution 5 — The amount of repeated work matters

A nested loop with twenty-five cheap indexed lookups may be excellent.

One million repeated lookups may be very expensive.

Inspect outer-row count, inner-loop cost, and total execution behavior before judging the algorithm.

## Solution 6 — The database may still need to examine many candidates

Without an ordered access path, PostgreSQL may need to inspect all qualifying rows before selecting the newest twenty-five.

A top-N sort can reduce sorting work but doesn't eliminate the need to consider the candidates.

A matching ordered index may allow earlier termination.

## Solution 7 — Batch or join deliberately

A join can retrieve the customers with reservations.

Alternatively, fetch the page of reservations, then retrieve customers in one batched query.

Several one-to-many joins can multiply result rows, so a page-plus-batched-relations approach may be preferable for complex responses.

## Solution 8 — Separate database time from request time

The four seconds may come from connection-pool waiting, network delays, application processing, serialization, locks, or other work outside the measured executor interval.

Trace the request and identify where elapsed time accumulates.

Don't optimize a thirty-millisecond query merely because the endpoint is slow.

---

# The Mental Model Worth Keeping

When a SQL query is slow, ask five questions:

**Access:** How does PostgreSQL find the relevant rows?

**Volume:** How many rows and pages must it examine compared with how many it returns?

**Estimation:** Did the planner correctly predict the data volume and distribution?

**Composition:** How do joins, sorting, and pagination multiply the work?

**Trade-off:** Will the proposed index or query change improve the real workload without imposing unacceptable write and maintenance costs?

**SQL describes the answer. The execution plan describes the work. Performance engineering means understanding and improving that work.**

# Next Lecture — CS330-L03: Transactions and Isolation

We've learned how to retrieve relational data efficiently.

Now imagine two customers trying to reserve the final Deluxe room for the same night.

Both queries execute quickly.

Both transactions contain individually valid statements.

Both eventually commit.

Yet the hotel has confirmed two bookings for one remaining room.

How can successful database operations combine into an invalid business outcome?

In CS330-L03, we'll investigate transaction isolation, MVCC, locks, lost updates, serialization anomalies, and the mechanisms that make concurrent database operations correct rather than merely fast.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Watch PostgreSQL Change Its Mind

Use a disposable local PostgreSQL database. None of these experiments should be applied blindly to a production table.

## Experiment A — Build representative reservations

Create a simplified reservations table:

```sql
CREATE TABLE reservations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  hotel_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  check_in DATE NOT NULL,
  check_out DATE NOT NULL
);
```

Generate an illustrative dataset using `generate_series`:

```sql
INSERT INTO reservations (
  hotel_id, customer_id, status, check_in, check_out
)
SELECT
  1 + (g % 1000),
  1 + (g % 50000),
  CASE WHEN g % 10 < 7
    THEN 'confirmed'
    ELSE 'cancelled'
  END,
  DATE '2026-01-01' + (g % 365),
  DATE '2026-01-02' + (g % 365)
FROM generate_series(1, 500000) AS g;

ANALYZE reservations;
```

This is a synthetic dataset with deliberately simple distributions. It is not intended to replicate real production skew.

**Question:** Why might a query's plan differ significantly when the dataset contains only five hundred rows rather than five hundred thousand?

## Experiment B — Inspect the unindexed access path

Our dashboard query filters by hotel, confirmed status, and October check-in dates, then returns twenty-five rows in descending date and ID order.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT
  id,
  customer_id,
  check_in,
  check_out,
  status
FROM reservations
WHERE hotel_id = 482
  AND status = 'confirmed'
  AND check_in >= DATE '2026-10-01'
  AND check_in < DATE '2026-11-01'
ORDER BY check_in DESC, id DESC
LIMIT 25;
```

Inspect the plan.

Does it use a sequential scan? Is a sort present? How many rows are filtered out? What does the buffer activity indicate?

Avoid assuming a particular plan will always appear. PostgreSQL selects a plan based on the actual table size, statistics, and environment.

## Experiment C — Add the targeted partial index

Create an index aligned with the dashboard's filter and order:

```sql
CREATE INDEX idx_confirmed_dashboard
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
WHERE status = 'confirmed';
```

Repeat the query from Experiment B.

Compare execution time, row counts, buffer activity, and whether PostgreSQL uses the index.

**Question:** Did the index reduce actual work? If so, which operation became cheaper or disappeared?

## Experiment D — Test covering-index behavior

Create a variant that includes additional selected columns:

```sql
CREATE INDEX idx_confirmed_dashboard_cover
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
INCLUDE (customer_id, check_out)
WHERE status = 'confirmed';
```

Repeat the query.

Inspect whether PostgreSQL selects an index-only scan and whether heap fetches remain.

**Question:** Why might an index-only scan still consult heap pages? What trade-off did the included columns introduce?

## Experiment E — Explore planner estimates

Introduce a deliberately skewed dataset or query pattern.

For example, insert substantially more reservations for one particular hotel than for others.

Refresh statistics:

```sql
ANALYZE reservations;
```

Compare plans and estimated-versus-actual rows for a large hotel and a small hotel.

If you explore prepared statements, compare parameter-specific plans with generic plan behavior in a controlled environment.

**Question:** Why might identical SQL produce different sensible plans for different hotels?

## Experiment F — Inspect a correlated predicate

If your experiment table includes suitable correlated columns, create extended statistics:

```sql
CREATE STATISTICS reservations_hotel_status_stats
  (dependencies, mcv)
ON hotel_id, status
FROM reservations;

ANALYZE reservations;
```

Compare cardinality estimates where the query's predicates and data distribution can benefit from those statistics.

Do not expect extended statistics to solve every estimation problem.

**Question:** What assumption about independent predicates can become incorrect in a real multitenant database?

## Experiment G — Investigate pagination

Compare an offset query with a keyset continuation.

The offset version skips a large number of rows:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, check_in
FROM reservations
WHERE hotel_id = 482
ORDER BY check_in DESC, id DESC
LIMIT 25 OFFSET 10000;
```

Depending on the number of rows matching the hotel, this offset may exceed the available result set; choose a hotel with sufficient data or adjust the value accordingly.

The keyset version uses the final tuple from a previous page:

```sql
SELECT id, check_in
FROM reservations
WHERE hotel_id = 482
  AND (check_in, id) < (DATE '2026-10-17', 10842)
ORDER BY check_in DESC, id DESC
LIMIT 25;
```

The cursor values are illustrative. For a meaningful comparison, obtain them from a real preceding page of the same filtered and ordered result.

**Question:** Which query is likely to avoid traversing a large number of earlier entries, assuming an appropriate ordered index?

## Experiment H — Diagnose the ORM response pattern

Imagine a backend that loads one hundred reservations and separately queries the customer for each one.

Compare three approaches:

1. One reservation query plus one hundred customer queries.
2. A join that retrieves customer information together with reservations.
3. One reservation-page query followed by a batched customer lookup.

Then add a one-to-many reservation-items relationship and inspect how joining multiple child collections can multiply rows.

**Question:** Why might two or three predictable queries outperform one giant join or one hundred tiny queries?

## Experiment I — Your final query investigation

You receive a report:

> "After moving from development to production, the reservation dashboard became 250 times slower. The SQL hasn't changed."

Write a concise engineering investigation with:

- Three competing explanations.
- The first measurement you would gather.
- The most important fields in an `EXPLAIN ANALYZE` plan.
- A candidate index, if supported by the query pattern.
- One potential downside of that index.
- A before-and-after validation plan.

The objective is not to guess the fastest index from memory. It is to establish a defensible relationship between the query, the data distribution, the chosen plan, and the observed work.

---

# Further Reading

Official PostgreSQL references:

- **Using EXPLAIN:** https://www.postgresql.org/docs/current/using-explain.html
- **Introduction to Indexes:** https://www.postgresql.org/docs/current/indexes.html
- **Multicolumn Indexes:** https://www.postgresql.org/docs/current/indexes-multicolumn.html
- **Partial Indexes:** https://www.postgresql.org/docs/current/indexes-partial.html
- **Index-Only Scans:** https://www.postgresql.org/docs/current/indexes-index-only-scans.html
- **Planner Statistics:** https://www.postgresql.org/docs/current/planner-stats.html
- **Query Planning:** https://www.postgresql.org/docs/current/planner-optimizer.html
- **LIMIT and OFFSET:** https://www.postgresql.org/docs/current/queries-limit.html

Related programme chapters:

- CS330-L01 — Relational Database Design
- CS330-L03 — Transactions: When Correct Operations Produce Incorrect Results
- CS340-L02 — Inside a Storage Engine
- CS340-L04 — Indexes, Queries, and Aggregation Beyond SQL

---

## Dense Cheatsheet — Interview Glance Card

```text
CS330-L02 — SQL AND QUERY PERFORMANCE

CORE MODEL
  SQL = declarative result specification
  Planner = physical execution strategy
  Fast query = inexpensive physical work, not merely few returned rows

STORAGE
  PostgreSQL heap = table row/version storage
  Default page size commonly 8 KiB
  Heap not intrinsically ordered by business columns
  Index = separate searchable data structure
  Index entries may require heap retrieval

SELECTIVITY
  High selectivity = small fraction of rows match
  Low selectivity = large fraction match
  Index helpful when it avoids enough expensive work
  Seq Scan is not inherently bad
  Index Scan is not inherently good

B-TREE
  Balanced ordered index
  Supports point/range and suitable ordering queries
  Index column order matters
  Leading equality + following range often effective
  Sort direction and tie-breaker can matter
  Modern PostgreSQL may use B-tree skip scan in some cases

COMPOSITE INDEX EXAMPLE
  Hotel equality, date range, newest first:
  (hotel_id, check_in DESC, id DESC)

PARTIAL INDEX
  WHERE status = 'confirmed'
  Smaller/more targeted when workload supports it
  Query predicate must imply partial-index predicate
  Generic parameterized status may prevent index eligibility

COVERING INDEX
  INCLUDE non-key payload columns
  Potential Index Only Scan
  Visibility map controls many heap-skip decisions
  Index Only Scan may still show Heap Fetches
  Bigger index creates storage/write costs

EXPLAIN
  Shows planned execution strategy and estimates
  Seq Scan       examine table pages
  Index Scan     navigate index + retrieve rows
  Bitmap Scan    collect heap locations then visit pages
  Index Only     attempt answer from index + visibility info
  Sort / Join / Limit nodes compose the plan

EXPLAIN ANALYZE
  Actually executes query!
  cost = planner units, NOT milliseconds
  rows = estimated vs actual cardinality
  actual time = observed executor timing
  loops = repeated executions of node
  Node actual rows/times generally average per loop
  BUFFERS shared hit = PostgreSQL buffer cache hit
  BUFFERS shared read != guaranteed physical disk read
  Temp blocks may indicate sort/hash spill
  Executor timing != complete API response latency

PLANNER ESTIMATES
  Row counts, distinct values, histograms, MCVs
  Data skew and stale statistics affect estimates
  Correlated predicates may break independence assumptions
  CREATE STATISTICS supports certain multivariate estimates
  ANALYZE refreshes statistics; doesn't create missing indexes

JOINS
  Nested Loop = repeated inner lookup; good when small/cheap
  Hash Join = hash one input, probe with the other
  Merge Join = advance through ordered join inputs
  Join choice depends on cardinality, access paths, memory
  Join order can greatly affect intermediate result size

ORM TRAPS
  N+1 = one primary query + N related lookups
  Repair via join or batched secondary query
  Several 1:N joins may multiply result rows
  Inspect generated SQL, not just ORM method calls

ORDER BY / LIMIT
  LIMIT 25 doesn't imply only 25 rows inspected
  Sort may process all qualifying candidates
  Top-N sorting helps but isn't free
  Aligned index can avoid sort and enable early stop
  Sorting may spill to temporary files

PAGINATION
  OFFSET large => traverse/skip many prior entries
  Keyset cursor resumes after last ordered tuple
  DESC(check_in, id) -> tuple comparison for next page
  Unique tie-breaker prevents ambiguous ordering
  Cursors don't automatically freeze multi-request snapshots
  Deep numbered-page jumps are less convenient with keyset

INDEX COSTS
  Additional storage
  Insert/update maintenance
  WAL and cache overhead
  Index creation/migration costs
  More indexes != always better performance
  Select indexes based on important real queries

DIAGNOSIS
  1. Measure database time separately from API time
  2. Capture actual SQL and parameters
  3. Inspect EXPLAIN / ANALYZE safely
  4. Compare estimates with actual rows
  5. Understand real data distribution
  6. Select the smallest justified change
  7. Verify reads, writes, resource use and regressions

SENIOR INTERVIEW ANSWER
  "I'd first establish whether database execution owns the latency.
   Then I'd capture the actual SQL and parameters, inspect its
   execution plan and row estimates, relate the chosen access path
   to the data distribution, and benchmark the smallest justified
   index or query change under representative workload."

MENTAL MODEL
  What was requested?
  Which data was examined?
  Why did the planner choose that route?
  Where was the expensive work?
  What trade-off does the proposed fix introduce?
```
