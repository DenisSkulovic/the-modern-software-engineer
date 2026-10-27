---
id: CS330-L02
course: CS330
title: "SQL and Query Performance"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S03]
prev: CS330-L01
next: CS330-L03
---




# CS330 — Relational Databases and Transactions

## Lecture 02: SQL and Query Performance

*Why a database sometimes spends four seconds answering a question it could have answered in fifteen milliseconds—and how to investigate what it's actually doing.*

**Estimated study time:** 90–110 minutes, including the optional PostgreSQL lab.

---

### How to listen to this lecture

Written for continuous listening first, then for on-screen re-reading. Theme: **SQL describes the result you want; the planner chooses the physical work** — and **slow queries are diagnosed from plans and row estimates, not folklore**. Sticky-note callouts mark the durable trade-offs. Near the end, answer the oral challenges **out loud** before reading solutions. The PostgreSQL investigation lab lives after the spoken lecture ends — keep it for a screen session.

By the end, you should be able to say why identical SQL can be 250× slower on larger data, when a sequential scan beats an index, how composite and partial indexes align with filters and `ORDER BY`, what `EXPLAIN ANALYZE` reveals when estimates diverge from reality, why N+1 and deep `OFFSET` pages hurt, and which questions to ask before adding another index.

---

# 1. The Query That Became 250 Times Slower Without Changing

It's Monday morning, and somebody from customer support reports that the reservation management dashboard has become painfully slow.

Not completely broken. That would almost be easier. It works, eventually.

An employee selects a hotel, chooses a date range, and waits four seconds for a list of reservations to appear.

You open the backend repository and find the responsible SQL query — select reservation identity, customer, dates, and status for one hotel's confirmed check-ins in October, newest first, limited to twenty-five rows:

```sql
SELECT
    r.id,
    r.customer_id,
    r.check_in,
    r.check_out,
    r.status
FROM reservations r
WHERE r.hotel_id = 482
  AND r.status = 'confirmed'
  AND r.check_in >= DATE '2026-10-01'
  AND r.check_in < DATE '2026-11-01'
ORDER BY r.check_in DESC, r.id DESC
LIMIT 25;
```

Nothing particularly exotic. A few conditions, an ordering clause, and a limit. On your development database, the query completes in approximately 15 milliseconds.

In production, it takes four seconds. You compare the application code. Identical.

You compare the SQL. Identical. You check the database server.

CPU usage is moderate. Memory isn't exhausted. There's plenty of free disk space.

The database hasn't crashed. It hasn't lost data. It hasn't even become obviously overloaded.

And yet this perfectly ordinary query is now roughly 250 times slower. What's going on? Here's the first clue.

Your development database contains 8,000 reservations. Production contains 14 million. That seems like an obvious explanation. More data means more work.

But hold on.

If a table contains 14 million reservations, why should PostgreSQL examine all 14 million merely to retrieve 25 reservations from one hotel?

Surely there must be a smarter way. There is. In fact, PostgreSQL has several fundamentally different ways to execute this query.

It can scan the entire table. It can search an index. It can combine several indexes.

It can retrieve rows in an order that avoids sorting. It can choose to read thousands of rows or perhaps only a few dozen.

And the truly interesting part is that **PostgreSQL itself must decide which approach is most efficient**.

Your SQL describes the result you want. It doesn't normally prescribe the algorithm that must produce it.

Somewhere between your SQL statement and the returned rows, the database makes an architectural decision on your behalf.

This decision is called a *query execution plan*.

Understanding how PostgreSQL chooses and executes these plans is one of the most valuable database skills an application engineer can develop.

Let's enter the machinery.

---

# 2. SQL Is a Description, Not a Recipe

When we write ordinary application code, we're accustomed to specifying operations procedurally.

Consider this TypeScript pipeline — filter by hotel, filter confirmed status, sort by check-in descending, then take the first twenty-five:

```typescript
const result = reservations
  .filter(r => r.hotelId === 482)
  .filter(r => r.status === "confirmed")
  .sort((a, b) => b.checkIn.localeCompare(a.checkIn))
  .slice(0, 25);
```

The JavaScript code describes a particular sequence of operations. Filter the array. Filter the remaining elements.

Sort them. Take the first 25. Even if the runtime optimizes parts of this execution, we've expressed an algorithm.

SQL works differently. The same intent as a result description — hotel 482, ordered by check-in descending, limited to twenty-five — without naming the algorithm:

```sql
SELECT *
FROM reservations
WHERE hotel_id = 482
ORDER BY check_in DESC
LIMIT 25;
```

We're describing the desired result. We aren't telling PostgreSQL how to obtain it.

The database might discover that an index already contains the reservations in the required order.

In that case, explicitly sorting the records would be unnecessary. It might retrieve the first 25 matching index entries and stop. Or it might decide to read the entire table and sort the relevant rows.

The database optimizer explores possible execution strategies and estimates their costs. From SQL through parsing, rewriting, and planning, candidate paths such as sequential scan, index scan, and bitmap scan compete; one plan tree is chosen and executed to produce the result rows:

```text
                 SQL QUERY
                     |
                     v
             Parsing and Analysis
                     |
                     v
               Query Rewriting
                     |
                     v
                Query Planner
                     |
           +---------+---------+
           |         |         |
           v         v         v
       Seq Scan  Index Scan  Bitmap Scan
           |         |         |
           +---------+---------+
                     |
                     v
              Chosen Plan Tree
                     |
                     v
                Executor
                     |
                     v
                 Result Rows
```

The optimizer's job is to find a good execution strategy without spending more time optimizing the query than executing it.

This is why PostgreSQL uses estimates rather than exhaustively testing every possible plan.

For a complex query involving many tables, the number of potential join orders and algorithms becomes enormous.

The optimizer must make educated decisions.

And like any system making decisions from incomplete information, it can occasionally make the wrong one.

> **Sticky note #1**
>
> SQL names the result; the planner names the algorithm — and its choice can be wrong when estimates are wrong.

The important question is: *what information is it using?* To understand that, we need to understand how rows are physically stored and retrieved.

---

# 3. The Table Is Not an Array in Memory

Imagine our `reservations` table contains 14 million rows. It's tempting to picture them as an enormous JavaScript array. But a PostgreSQL table is stored in pages, usually 8 KiB each in a standard installation.

These pages contain row versions and associated storage information. PostgreSQL refers to the table's primary row storage as the **heap**.

The word *heap* here has nothing to do with the heap data structure we studied in the computer science foundations courses (CS110, CS220, CS320). It means the table isn't intrinsically maintained in the logical order of any particular column.

Rows occupy physical locations within storage pages. A simplified heap — pages of row versions with no guaranteed logical order by ID, date, customer, or hotel:

```text
RESERVATIONS TABLE — HEAP

Page 0
  Row: Reservation 1042
  Row: Reservation 1051
  Row: Reservation 1052
  ...

Page 1
  Row: Reservation 1053
  Row: Reservation 1068
  ...

Page 2
  Row: Reservation 1072
  Row: Reservation 1081
  ...

...

Page 120,000
  ...
```

The physical arrangement isn't guaranteed to correspond to reservation ID, date, customer, or hotel.

And updates can create new row versions because PostgreSQL uses Multi-Version Concurrency Control—MVCC.

We'll investigate MVCC properly next session. For now, what matters is that finding a logical row can involve reading storage pages. If the query must examine every row, PostgreSQL can perform a **sequential scan** — start at the beginning of the table, read each page, examine row versions, apply the `WHERE` conditions, and continue until finished:

```text
Start at beginning of table
         |
         v
Read page
         |
         v
Examine row versions
         |
         v
Apply WHERE conditions
         |
         v
Continue until finished
```

This sounds primitive.

But sequential scanning has a significant advantage: reading a large amount of data in sequence can be efficient.

The database can process pages systematically instead of repeatedly jumping between unrelated storage locations.

Modern storage devices and operating-system caches make sequential access particularly attractive for large scans.

Therefore, a sequential scan is not automatically evidence of poor performance.

If your query needs 80% of the table, scanning it once may be considerably cheaper than performing millions of individual index lookups.

However, if your query needs only 25 rows out of 14 million, there should usually be a better approach.

Enter the index.

---

# 4. A B-Tree: How to Find a Needle Without Inspecting Every Piece of Hay

Suppose you maintain a telephone directory containing one million names. Someone asks for the phone number of a person named Zimmerman. Would you begin with page one and read every entry?

Of course not. The directory is alphabetically organized.

You can jump toward the end, narrow the relevant region, and find Zimmerman without examining the entire directory.

A database B-tree index exploits a similar idea. Create a single-column index on hotel identity:

```sql
CREATE INDEX idx_reservations_hotel
ON reservations (hotel_id);
```

PostgreSQL constructs a separate index structure containing hotel identifiers associated with references to table rows.

Conceptually, a root splits hotel ranges, internal nodes narrow further, and leaf pages hold the ordered keys — deliberately simplified; real B-trees have more levels:

```text
                     ROOT
              +-------+-------+
              |               |
          Hotels 1–500    Hotels 501–1000
              |               |
         +----+----+      +---+----+
         |         |      |        |
       1–250    251–500 501–750 751–1000
         |         |
         v         v
       LEAF      LEAF
       PAGES     PAGES
```

This diagram is deliberately simplified. PostgreSQL B-tree indexes contain internal pages and ordered leaf pages, and real structures can have more levels.

The important mechanism is hierarchical navigation.

Instead of examining every row, PostgreSQL follows the index toward the relevant key range.

For Hotel 482, it descends through the appropriate internal pages, reaches leaf entries for that key, and retrieves references to matching table rows.

In a healthy, well-sized B-tree, this usually involves traversing relatively few index levels.

But don't overinterpret the familiar complexity notation. We often describe balanced tree lookup as approximately O of log n.

That's a useful abstract model. However, database performance isn't determined solely by algorithmic complexity. The expensive part may be fetching the matching rows from the underlying table.

### The second journey: from index to heap

Suppose the index finds 3,000 reservations belonging to Hotel 482. The index entries identify where those rows are stored. The executor might need to visit many heap pages to retrieve the actual reservation data — the same hotel key pointing at scattered heap pages:

```text
B-TREE INDEX
    |
    +-- Hotel 482 -> Heap page 918
    |
    +-- Hotel 482 -> Heap page 28,410
    |
    +-- Hotel 482 -> Heap page 7,206
    |
    +-- Hotel 482 -> Heap page 64,812
    |
    ...
```

The index search itself may be cheap. But the corresponding table access could involve thousands of scattered locations. If the pages aren't already cached, retrieving them may require substantial physical I/O.

Even cached page accesses and per-row processing have costs. This is the fundamental trade-off between sequential scanning and index scanning.

**A sequential scan reads more data in an efficient order. An index scan attempts to read less data, potentially with more scattered accesses.**

> **Sticky note #2**
>
> Sequential scan ≠ always bad; index scan ≠ always good — the winner depends on how much data you actually need.

Whether the index wins depends largely on how much data the query actually needs. And that brings us to selectivity.

---

# 5. Selectivity: Not All WHERE Clauses Are Created Equal

Consider three queries.

Query A asks for one reservation by primary key:

```sql
SELECT *
FROM reservations
WHERE id = 10842;
```

Query B asks for every confirmed reservation:

```sql
SELECT *
FROM reservations
WHERE status = 'confirmed';
```

Query C asks for one hotel's reservations in a date window:

```sql
SELECT *
FROM reservations
WHERE hotel_id = 482
  AND check_in >= DATE '2026-10-01'
  AND check_in < DATE '2026-11-01';
```

These queries might have dramatically different selectivity.

**Selectivity** describes what fraction of rows satisfy a condition.

Suppose the table contains 14 million rows. Illustrative fractions:

1. **Query A — by ID** matches about 1 row, roughly 0.000007% of the table.
2. **Query B — confirmed** matches about 10 million rows, roughly 71% of the table.
3. **Query C — hotel and dates** matches about 400 rows, roughly 0.003% of the table.

Query A is extremely selective. A primary-key index lookup is the obvious candidate.

Query B matches most of the table.

An index on `status` might not help much if the query requires returning all those records.

A sequential scan could be preferable. Query C is also highly selective, provided PostgreSQL has an appropriate access path. This is why adding an index on every column isn't a sensible optimization strategy.

An index is beneficial when it allows the executor to avoid enough expensive work.

### The deceptive boolean index

Imagine a table containing 50 million orders. You create an index on the boolean paid flag:

```sql
CREATE INDEX idx_orders_paid
ON orders (is_paid);
```

But 95% of orders have `is_paid = true`. A query asking for paid orders still potentially needs 47.5 million rows. The index doesn't make that huge result small.

On the other hand, if you frequently process the 5% of orders that remain unpaid, a partial index targeting the appropriate subset may be valuable.

> **Sticky note #3**
>
> Selectivity beats column presence — an index helps when it shrinks expensive work, not merely because a column appears in `WHERE`.

The usefulness of an index depends on the workload and distribution of values, not merely on the presence of a column in a `WHERE` clause.

Let's now return to our slow reservation query and design an index that understands what we're actually asking.

---

# 6. Composite Indexes: The Order of the Columns Matters

Our dashboard query filters by hotel, status, and dates, then orders by check-in date and reservation ID.

A simplistic approach might create separate indexes on hotel, status, and check-in:

```sql
CREATE INDEX ON reservations (hotel_id);
CREATE INDEX ON reservations (status);
CREATE INDEX ON reservations (check_in);
```

PostgreSQL can sometimes combine indexes through bitmap operations. But three separate indexes are not automatically the best design. What if we create an index that organizes the data according to the actual query pattern — hotel first, then check-in and ID descending:

```sql
CREATE INDEX idx_reservations_hotel_date
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
);
```

Picture the index as a sorted catalogue. First by hotel. Then, within each hotel's entries, by check-in date in descending order.

Finally, by reservation ID in descending order. Conceptually, hotels nest their newest check-ins first:

```text
Hotel 481
    Oct 31 — Reservation 9012
    Oct 30 — Reservation 9011
    ...

Hotel 482
    Oct 31 — Reservation 10842
    Oct 31 — Reservation 10792
    Oct 30 — Reservation 10741
    Oct 29 — Reservation 10693
    ...

Hotel 483
    ...
```

Now consider a selective hotel-and-date query that also orders the way the index is sorted:

```sql
SELECT id, check_in
FROM reservations
WHERE hotel_id = 482
  AND check_in >= DATE '2026-10-01'
  AND check_in < DATE '2026-11-01'
ORDER BY check_in DESC, id DESC
LIMIT 25;
```

PostgreSQL may navigate directly to the relevant hotel's date range.

Because the index already maintains the required ordering, it may not need a separate sorting step.

It can potentially retrieve 25 qualifying records and stop.

That's a much more powerful optimization than merely indexing each filter column independently.

### Why the column order matters

Suppose we instead create an index that leads with check-in, then hotel:

```sql
CREATE INDEX idx_date_hotel
ON reservations (check_in, hotel_id);
```

This organizes the entries primarily by date.

For a query selecting one particular hotel across a date range, PostgreSQL may need to examine entries for many hotels within that range.

An index beginning with `hotel_id` is often better for a workload where hotel equality comes first.

A traditional practical guideline for multicolumn B-tree indexes is:

**Put highly useful equality conditions first, then consider range conditions and required ordering.**

But this is a heuristic, not a mathematical law.

Column distribution, query patterns, ordering, and PostgreSQL's planner capabilities all matter.

Recent PostgreSQL versions also support B-tree skip-scan strategies for some queries that lack restrictions on leading columns.

So the rule isn't that an index becomes completely unusable when the leftmost column isn't specified.

It's that leading-column restrictions often make the index substantially more efficient.

### An overlooked detail: tie-breaking

Why include `id DESC`? Because multiple reservations can share the same check-in date. If we sort only by date, their relative order isn't fully specified.

A stable unique tie-breaker gives us deterministic ordering. That's essential for reliable pagination, which we'll investigate shortly.

---

# 7. Partial and Covering Indexes: Designing for a Particular Workload

Let's make the query even more interesting. The dashboard only displays confirmed reservations. Do we really need an index entry for every cancelled, expired, and pending reservation?

Not necessarily. PostgreSQL supports **partial indexes** — same hotel and date ordering keys, but only where status is confirmed:

```sql
CREATE INDEX idx_confirmed_reservations_hotel_date
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
WHERE status = 'confirmed';
```

This index contains entries only for confirmed reservations. It can be smaller than a corresponding full-table index.

And it is particularly relevant to queries whose conditions establish that `status = 'confirmed'`.

Our dashboard query qualifies. But there's a subtle restriction.

The planner must be able to establish that the query's predicate implies the partial index predicate.

For example, a prepared statement using a generic plan with an unrestricted parameter `WHERE status = $1` cannot assume `$1` always equals `'confirmed'`. Such a generic plan may therefore be unable to use our partial index.

This is one reason SQL behavior can differ between literal examples and parameterized production queries.

### Covering indexes

Suppose the dashboard needs identity, hotel, check-in, and customer — and our index has the first three keys but not customer:

```sql
SELECT id, hotel_id, check_in, customer_id
FROM reservations
WHERE hotel_id = 482
  AND status = 'confirmed'
ORDER BY check_in DESC, id DESC
LIMIT 25;
```

Our index contains `hotel_id`, `check_in`, and `id`, but not `customer_id`. PostgreSQL may need to visit the heap to retrieve that final field. One option is a covering partial index that includes customer as payload:

```sql
CREATE INDEX idx_confirmed_dashboard
ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
INCLUDE (customer_id)
WHERE status = 'confirmed';
```

The `INCLUDE` column is stored as payload. It isn't an additional search key. Now the index contains all the selected fields.

Could PostgreSQL answer the query without visiting the table? Potentially. This is called an **index-only scan**.

But there's a catch. PostgreSQL must still verify MVCC visibility.

An index entry doesn't, by itself, establish that its row version is visible to the current transaction.

PostgreSQL uses a visibility map to determine whether a heap page can safely be skipped. For recently modified pages, it may still need heap access. Therefore, *index-only* does not always mean literally zero heap fetches.

An execution plan can show an `Index Only Scan` together with a nonzero `Heap Fetches` count.

Covering indexes are especially useful for relatively stable data and frequently executed queries with a predictable set of required columns.

They are less attractive when they become enormous or when indexed payload values change frequently.

And that brings us to a cost many developers overlook. Every index is another structure that must be maintained when data changes. We'll return to that shortly.

---

# 8. EXPLAIN: Looking Inside the Optimizer's Decision

We've discussed several possible execution strategies. But how do you determine which one PostgreSQL actually chose? You ask it — plain `EXPLAIN` on a hotel-and-status filter:

```sql
EXPLAIN
SELECT *
FROM reservations
WHERE hotel_id = 482
  AND status = 'confirmed';
```

PostgreSQL returns an execution plan. One possibility is a sequential scan with both predicates as filters:

```text
Seq Scan on reservations
  Filter: ((hotel_id = 482) AND (status = 'confirmed'))
```

Another is an index scan that applies the hotel as an index condition and status as a residual filter:

```text
Index Scan using idx_reservations_hotel_date
  Index Cond: (hotel_id = 482)
  Filter: (status = 'confirmed')
```

Or a bitmap index scan feeding a bitmap heap scan on the same hotel condition:

```text
Bitmap Heap Scan on reservations
  Recheck Cond: (hotel_id = 482)
  -> Bitmap Index Scan on idx_reservations_hotel_date
       Index Cond: (hotel_id = 482)
```

These are simplified illustrations, not output from a measured database. Each plan represents a different method of retrieving the result.

### Sequential scan

Read table pages and evaluate the filter against rows. Useful when much of the table needs examination.

### Index scan

Navigate through the index and retrieve matching table rows.

Useful when the index provides an efficient way to find a relatively small or conveniently ordered result.

### Bitmap index and heap scan

First use index information to identify qualifying heap locations. Then retrieve matching heap pages in a more efficient order.

This can be advantageous when the query matches enough rows that repeated individual heap lookups would be expensive, but not so many that a full sequential scan is preferable.

### Index-only scan

Attempt to satisfy the query using information stored in the index, consulting heap visibility where necessary.

The optimizer chooses between these approaches based on its estimates. But `EXPLAIN` alone reveals what PostgreSQL *expects* to happen. What if those expectations are wrong?

That's where `EXPLAIN ANALYZE` enters the story.

---

# 9. EXPLAIN ANALYZE: The Database Gives Its Testimony

Consider `EXPLAIN` with `ANALYZE` and `BUFFERS` so PostgreSQL actually runs the query and reports measured work:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM reservations
WHERE hotel_id = 482
  AND status = 'confirmed';
```

Unlike plain `EXPLAIN`, this actually executes the query and reports what happened.

It includes estimated costs and row counts, actual execution times, actual row counts, loop counts, and information about buffer activity.

A plan node might report something like: index scan on `idx_reservations_hotel_date`, estimated cost from 0.43 to 125.60 expecting about 80 rows, but actual time from 0.050 to 4.200 milliseconds with 3,100 rows in one loop:

```text
Index Scan using idx_reservations_hotel_date
  (cost=0.43..125.60 rows=80 width=64)
  (actual time=0.050..4.200 rows=3100 loops=1)
```

These numbers are illustrative. Look at the discrepancy. The planner expected approximately 80 rows.

The query actually returned 3,100. That's almost a fortyfold underestimate. Why does this matter?

Because the optimizer may have chosen an index scan believing it would perform a few dozen row lookups.

Instead, it performed thousands. Perhaps a different plan would have been cheaper.

### Understanding the important fields

**Estimated cost.** The values after `cost=` are PostgreSQL's internal estimates of startup and total execution cost. They are not milliseconds. You cannot interpret `cost=100` as a prediction of 100 ms.

**Estimated rows.** The planner's estimate of the number of rows produced by that plan node.

**Actual time.** Measured execution time, in milliseconds, for the node.

**Actual rows.** The average number of rows produced per execution of that node.

**Loops.** How many times the node was executed. This last field matters enormously for joins.

If an inner index scan runs 10,000 times and reports an average of one row per loop, it may have produced approximately 10,000 rows overall.

A seemingly cheap operation repeated thousands of times can become expensive.

### Buffers: did we actually read from storage?

You may see buffer activity such as `Buffers: shared hit=1200 read=85`.

A shared buffer hit means PostgreSQL found the required block in its shared buffer cache.

A read means the block was brought into PostgreSQL's shared buffers, but it does not necessarily mean a physical disk access occurred; the operating system's filesystem cache may have supplied it.

Buffer counts are block accesses, not necessarily counts of distinct pages. They tell you useful things about the amount and nature of database work. You may also see temporary blocks used for sorting or hashing.

Those often reveal that an operation exceeded its available memory budget and required temporary storage.

### Read plans from the bottom upward

Execution plans are trees. Leaf nodes generally obtain raw data. Parent nodes transform, join, sort, or aggregate that data.

A useful debugging technique is to start with the data-access nodes and work upward. Ask:

What data did PostgreSQL read? How many rows survived filtering? How did it combine them?

Did it sort them? How often did it repeat each operation? Where did the estimates diverge from reality?

> **Sticky note #4**
>
> `EXPLAIN` is expectation; `EXPLAIN ANALYZE` is testimony — chase large estimated-versus-actual gaps before guessing indexes.

A vital caution: `EXPLAIN ANALYZE` actually executes statements. Running it on an `UPDATE`, `DELETE`, or `INSERT` can modify data—use a controlled environment, and understand transaction and side-effect behavior before experimenting with writes. Even an expensive read-only query can consume significant production resources; treat the tool as an instrument, not a harmless observer.

---

# 10. Why the Planner Sometimes Gets It Wrong

Let's investigate that dramatic difference between estimated and actual row counts. How does PostgreSQL estimate result sizes in the first place? It collects statistics about table contents.

These include approximate table sizes, value distributions, common values, and histograms. For example, the planner might know that:

- Approximately 70% of reservations are confirmed.
- There are roughly 1,000 distinct hotel identifiers.
- Certain check-in dates are unusually common.
- A particular column contains many null values.

This helps estimate selectivity. But statistics are imperfect. They're generally based on samples and approximations.

And the planner cannot know every possible relationship among columns.

### The correlation trap

Imagine a multinational hotel platform. Nearly every reservation for Hotel 482 belongs to Lithuania. Your query asks for that hotel and country code `LT`:

```sql
WHERE hotel_id = 482
  AND country_code = 'LT'
```

Suppose Hotel 482 accounts for 1% of reservations, and Lithuania accounts for 5%. If the planner naively treats these conditions as independent, it might estimate one percent times five percent — five hundredths of one percent of the table, or 0.0005 as a fraction.

That's 0.05% of the table.

But if nearly all Hotel 482 reservations are Lithuanian, the true fraction could be close to 1%.

The estimate could be wrong by a factor approaching twenty. Why? Because `hotel_id` and `country_code` are correlated.

PostgreSQL supports **extended statistics** to improve certain estimates involving related columns — dependencies and most-common-value combinations on hotel and country, then refresh with `ANALYZE`:

```sql
CREATE STATISTICS reservations_hotel_country_stats
  (dependencies, mcv)
ON hotel_id, country_code
FROM reservations;

ANALYZE reservations;
```

The `dependencies` statistic captures certain functional relationships, while `mcv` captures common combinations of values.

These statistics can help the optimizer with supported combinations of predicates.

They are not a universal cure for all correlation problems, particularly those involving arbitrary joins, ranges, or complex expressions.

### Stale statistics

Suppose your table grows from 100,000 reservations to ten million. Or a major marketing campaign suddenly concentrates traffic on a handful of hotels.

If the statistics haven't been refreshed adequately, PostgreSQL may be optimizing using an outdated picture of reality.

Running `ANALYZE reservations;` refreshes planner statistics.

Autovacuum normally handles automatic analysis, but unusual workloads or substantial changes may justify manual investigation.

However, don't develop the habit of responding to every slow query with `ANALYZE` and a prayer.

If the query lacks a useful index, fresher statistics won't conjure one into existence.

And if the database is blocked on locks or exhausted connection pools, the planner may not be your problem at all.

The fundamental principle is:

**The optimizer makes decisions from its model of the data. Better information can improve those decisions, but it cannot replace an appropriate physical access path.**

---

# 11. Joins: Three Different Ways to Combine Relationships

In CS330-L01, we normalized our schema. Hotels live in one table. Reservations live in another.

Customers live in a third. Now the dashboard needs reservation and customer information — join customers on identity for hotel 482:

```sql
SELECT
  r.id,
  r.check_in,
  c.display_name
FROM reservations r
JOIN customers c
  ON c.id = r.customer_id
WHERE r.hotel_id = 482;
```

How should PostgreSQL execute this? Several algorithms are possible.

### Nested-loop join

Imagine PostgreSQL finds 25 reservations. For each reservation, it looks up the associated customer by primary key — find a reservation, look up its customer, find the next reservation, look up again:

```text
Find reservation
      |
      v
Look up its customer
      |
      v
Find next reservation
      |
      v
Look up its customer
      |
      ...
```

This can be highly efficient when the outer result is small and the inner lookup uses an index.

Twenty-five indexed customer lookups may be extremely cheap. But imagine the outer input contains one million reservations. Now the inner lookup might execute one million times.

That's potentially expensive. A nested-loop join isn't inherently bad.

Its cost depends on how many iterations it performs and how expensive each inner operation is.

### Hash join

PostgreSQL can read one input and build an in-memory hash table keyed by the join column. Then it scans the other input and probes that hash table — build from customers by ID, then probe with reservations:

```text
CUSTOMERS
    |
    v
Build hash table by customer ID
    |
    v
RESERVATIONS
    |
    v
Probe customer hash table
    |
    v
Joined rows
```

Hash joins are often attractive for joining substantial datasets when the join is based on equality.

But building the hash table consumes memory.

If the operation exceeds its memory budget, it may need to process data in batches involving temporary disk storage.

### Merge join

If both inputs are sorted by their join keys, PostgreSQL can advance through them together — sorted reservations and sorted customers feeding a merge:

```text
Sorted reservations ------+
                          |
                          v
                       Merge Join
                          ^
                          |
Sorted customers ---------+
```

Merge joins can be effective when large sorted inputs are available or when the required ordering is useful elsewhere in the plan.

The database may exploit existing indexes or explicitly sort inputs.

### Join order matters too

Now imagine five related tables: reservations, customers, hotels, reservation items, and room types.

PostgreSQL must decide not just which join algorithms to use, but which relationships to combine first.

Joining large unfiltered tables before applying a highly selective condition might create an enormous intermediate result.

Applying useful filters early can dramatically reduce subsequent work. The planner searches for efficient alternatives. And again, its choices depend on estimated cardinality.

If it expects 100 intermediate rows but actually produces five million, a plan that seemed excellent can become disastrous.

That is why row-estimation errors often propagate into join-performance problems.

---

# 12. The ORM Trap: One Page, 101 Queries

Let's switch perspectives. You're working in Node.js with TypeORM. The frontend requests 100 reservations with customer information.

You write a repository find limited to one hundred rows:

```typescript
const reservations = await reservationRepository.find({
  take: 100,
});
```

Then, for each reservation, a separate customer lookup by ID:

```typescript
for (const reservation of reservations) {
  reservation.customer = await customerRepository.findOneBy({
    id: reservation.customerId,
  });
}
```

What's wrong? Nothing functionally. Every reservation receives the correct customer.

But the backend executes one query to retrieve reservations, followed by 100 customer queries.

That's the classic **N+1 query problem** — one query for the page, then one hundred for each customer, totaling 101 round trips:

```text
1 query  -> Fetch reservations

100 queries -> Fetch each customer separately

Total: 101 queries
```

If each query incurs network, database scheduling, and execution overhead, the accumulated cost becomes substantial.

Even worse, the database might be fast enough that individual queries look harmless. The problem is their multiplicity.

### The obvious repair

We could retrieve the related customers in one query with an `IN` list of IDs:

```sql
SELECT *
FROM customers
WHERE id IN (...);
```

Then associate customers with reservations in application memory. Or we could use a join that returns reservation and customer fields together for the hotel page:

```sql
SELECT
  r.id,
  r.check_in,
  c.id AS customer_id,
  c.display_name
FROM reservations r
JOIN customers c
  ON c.id = r.customer_id
WHERE r.hotel_id = 482
ORDER BY r.check_in DESC, r.id DESC
LIMIT 100;
```

In TypeORM, relationship loading and query-builder features can help, depending on mapping and loading strategy.

But there's a second trap.

### The giant join problem

Suppose each reservation has five items and each item has three associated records.

A careless join across several one-to-many relationships can multiply the number of result rows.

One reservation may appear repeatedly in the SQL result because of combinations of its child relationships.

Even if the ORM reconstructs the correct entity graph, it may need to transfer and process far more rows than expected.

This isn't strictly N+1 anymore. It's *row explosion*. The lesson is not that joins are bad or that ORMs are inefficient.

The lesson is that **an ORM doesn't repeal relational algebra or the physical cost of fetching data**.

You still need to understand the generated SQL. For a complex reservation dashboard, a good strategy might be:

1. Query the specific page of reservation IDs.
2. Fetch associated customers and items in a small number of batched queries.
3. Assemble the response.

In many systems this is simpler and more predictable than constructing one enormous join spanning every relationship.

A useful senior-engineering skill is recognizing when the ORM's convenience is hiding an expensive access pattern.

---

# 13. Sorting: The Hidden Cost of ORDER BY

Let's revisit our original query — hotel filter, newest check-ins first, limit twenty-five:

```sql
SELECT *
FROM reservations
WHERE hotel_id = 482
ORDER BY check_in DESC
LIMIT 25;
```

The `LIMIT 25` looks comforting. We're requesting only 25 rows. Surely PostgreSQL only needs to process 25 rows?

Not necessarily.

Without an appropriate index, PostgreSQL may need to examine every reservation belonging to Hotel 482 before determining which 25 are the latest.

It might then perform a bounded top-N sort, keeping only the best candidates in memory.

That's better than necessarily sorting the entire matching set in full, but it still must consider the candidate rows.

An index aligned with both the filter and the ordering can change the situation dramatically — hotel, then check-in and ID descending:

```sql
CREATE INDEX idx_hotel_latest
ON reservations (hotel_id, check_in DESC, id DESC);
```

Now PostgreSQL may be able to navigate to the hotel's records in the desired order and stop after retrieving the first 25.

Instead of reading tens of thousands of rows, evaluating candidates, and finding the latest twenty-five, we may get: find the hotel's ordered index range, read the first twenty-five suitable entries, and return:

```text
Find hotel's ordered index range
      |
      v
Read first 25 suitable entries
      |
      v
Return
```

That's a substantial reduction in work.

But it depends on whether the index and query conditions genuinely permit early termination.

A residual filter not represented effectively by the index may force PostgreSQL to scan many additional entries to find 25 matches.

### Sorting large datasets

Execution plans can report sort methods and memory usage. If an operation spills to disk, it may be constrained by the memory available for sorting.

PostgreSQL's `work_mem` setting influences memory available to individual sort and hash operations.

But setting `work_mem` to an enormous value globally is not automatically wise.

A complex query can contain multiple memory-consuming operations, and many queries may run concurrently.

An innocent-looking global increase can multiply memory consumption across the system. Again, the appropriate response is diagnosis rather than guesswork. Sometimes an index eliminates the sort.

Sometimes a query rewrite reduces input size. Sometimes a memory adjustment is justified.

And sometimes sorting is simply the right operation, with a cost that the application must accommodate.

---

# 14. Pagination: Why Page 10,000 Is Not Like Page 1

Consider a reservation listing API. The frontend requests page 1 — hotel 482, newest first, twenty-five rows from offset zero:

```sql
SELECT id, check_in
FROM reservations
WHERE hotel_id = 482
ORDER BY check_in DESC, id DESC
LIMIT 25 OFFSET 0;
```

Fine. Page 2 uses `LIMIT 25 OFFSET 25`. Also fine. Now imagine the user jumps to page 10,000 with `LIMIT 25 OFFSET 249975`.

What does PostgreSQL do?

It cannot simply teleport to the 249,976th logical result in an arbitrary filtered ordering without doing work to identify the skipped entries.

Even with a suitable ordered index, it generally must traverse the preceding qualifying entries to reach the requested offset.

The rows skipped by `OFFSET` are still computed. As the offset grows, the amount of work often grows too.

### Cursor-based pagination

Suppose the first page ends with check-in `2026-10-17` and ID `10842`.

Instead of requesting page 2 through an offset, we can ask for records after that position in our descending order — keyset comparison on the sort columns:

```sql
SELECT id, check_in
FROM reservations
WHERE hotel_id = 482
  AND (
    check_in,
    id
  ) < (
    DATE '2026-10-17',
    10842
  )
ORDER BY check_in DESC, id DESC
LIMIT 25;
```

This is **keyset pagination**, often exposed to clients through opaque cursors. The query directly describes where the next page begins. A matching composite index can navigate efficiently to that position.

This is especially attractive for large, frequently accessed datasets.

### Why include both date and ID?

Multiple reservations may have the same check-in date. If the cursor contained only the date, we could skip records sharing that date. Including the unique ID establishes a total ordering.

In this example, both sort columns are descending and non-null, which makes the tuple comparison appropriate.

Mixed sort directions or null semantics require more careful cursor predicates.

### Cursor pagination isn't magic

It introduces trade-offs. Jumping directly to arbitrary numbered pages becomes harder. The cursor must remain associated with the original filters and sort order.

If records are inserted, deleted, or modified between requests, subsequent pages can reflect those changes.

A cursor doesn't automatically produce a transactionally consistent snapshot across multiple HTTP requests.

But for activity feeds, event histories, large reservation lists, and infinite scrolling, cursor pagination is often preferable to enormous offsets.

The interesting principle is:

**Pagination is not merely a frontend UI choice. It determines the access pattern the database must support.**

---

# 15. Why More Indexes Can Make the Database Slower

We've spent much of this lecture celebrating indexes. Let's ruin the party slightly. Imagine a table with twelve indexes.

Every time the application inserts a reservation, PostgreSQL may need to update multiple index structures.

When indexed values change, the corresponding index maintenance may also be required. Indexes consume storage. They generate additional write activity.

They contribute to WAL volume, maintenance work, and cache pressure. And their existence doesn't guarantee that the planner will use them. Suppose the table receives 20,000 writes per second.

Adding an index to accelerate a rare administrative report might impose continuous write overhead on a critical transactional workload.

That could be a poor trade.

### Updates and index maintenance

PostgreSQL's MVCC implementation creates new row versions during updates.

Some updates can use a HOT—Heap-Only Tuple—optimization, avoiding new index entries when the necessary conditions are satisfied.

Updating indexed columns generally prevents that optimization.

A database with many indexes on frequently modified fields may therefore incur substantial maintenance overhead.

### Indexes should follow query patterns

A sensible design process begins with actual queries. Which queries are frequent? Which are expensive?

Which business operations have strict latency requirements? What rows do they filter? How do they sort?

How much data do they return? Only then should you consider an index. For example, a customer-history index leading with customer, then created-at and ID descending:

```sql
CREATE INDEX idx_reservation_customer_history
ON reservations (customer_id, created_at DESC, id DESC);
```

This might be useful for retrieving a customer's recent reservation history. But it won't automatically solve every hotel-administration query. Indexes are specialized data structures serving particular access patterns.

They're not general-purpose speed buttons.

> **Sticky note #5**
>
> Indexes follow workloads — every extra structure is write, WAL, and cache cost you pay whether the planner uses it or not.

---

# 16. Diagnosing a Slow Production Query Systematically

Let's return to the original production incident. The reservation dashboard takes four seconds. What should a competent engineer do?

Not immediately add an index. Not immediately double the database instance size.

And definitely not start adjusting obscure PostgreSQL configuration parameters like somebody trying to tune a piano with a hammer.

Start by identifying where the time is spent.

### First: Is the database actually slow?

The API takes four seconds. But perhaps the SQL query finishes in 30 milliseconds.

The delay could come from connection-pool contention, authorization lookups, external APIs, serialization, or application-level processing.

Measure the database call separately from the total request duration. If the query itself is slow, continue.

### Second: Capture the real query

Inspect the SQL actually executed by the application. Include relevant parameter values.

An ORM query that looks simple in TypeScript may generate complicated SQL involving joins and nested conditions.

Make sure you're investigating the actual workload.

### Third: Obtain the execution plan

Use `EXPLAIN`, and where operationally safe, `EXPLAIN (ANALYZE, BUFFERS)`. Investigate row estimates, access methods, joins, loops, sorting, and buffer activity. Look for mismatches between estimated and actual rows.

### Fourth: Understand the data distribution

How large are the relevant tables? How selective are the filters? Are certain tenants disproportionately large?

Have data volumes or distributions changed? Are the planner statistics reasonably current?

A query that performs well for a hotel with 200 reservations may behave very differently for a hotel with five million.

### Fifth: Design the smallest useful improvement

Potential interventions include:

1. Adding a workload-aligned index.
2. Changing an inefficient query.
3. Avoiding unnecessary columns.
4. Eliminating N+1 behavior.
5. Reducing join multiplication.
6. Switching to keyset pagination.
7. Updating stale statistics.
8. Batching work.
9. Using an appropriate reporting or pre-aggregation strategy.

Choose the improvement supported by evidence.

### Sixth: Verify the effect under realistic conditions

A faster local query isn't automatically a production success. Measure representative data volumes and parameters. Check write overhead, concurrency, memory consumption, and regressions in related queries.

Finally, monitor the change after deployment.

A query optimization that improves one dashboard while significantly slowing critical writes is not necessarily a win.

Production performance is a system-level concern.

---

# 17. The Oral Examination

Pause the lecture for each one.

Answer **out loud** — as if an interviewer were across the table — before you listen to or read the solutions.

They're designed to reinforce practical judgment rather than obscure planner trivia.

### Challenge A — The Unused Index

**Suggested time: 8 minutes**

A table contains ten million rows. You create an index on `status`. The query selects every order where `status = 'completed'`. About 92% of rows have this status. PostgreSQL chooses a sequential scan.

Is the optimizer malfunctioning?

What would you investigate?

### Challenge B — Composite Index Order

**Suggested time: 8 minutes**

You frequently execute a parameterized hotel-and-date query ordered by check-in and ID descending, limited to fifty rows:

```sql
SELECT *
FROM reservations
WHERE hotel_id = $1
  AND check_in >= $2
  AND check_in < $3
ORDER BY check_in DESC, id DESC
LIMIT 50;
```

Which index would you consider first, and why? Would an index on `(check_in, hotel_id)` be equivalent?

### Challenge C — The Misleading Execution Plan

**Suggested time: 8 minutes**

An `EXPLAIN ANALYZE` result shows estimated rows of 100 and actual rows of 850,000.

What does this tell you? What might cause the mismatch? Why could it affect join algorithms?

### Challenge D — The ORM Dilemma

**Suggested time: 8 minutes**

An endpoint retrieves 100 orders. For every order, it separately fetches the customer, payment, and delivery records. The SQL queries themselves are individually fast.

The endpoint is slow. How would you investigate and redesign this access pattern?

### Challenge E — The Surprisingly Slow LIMIT

**Suggested time: 8 minutes**

A developer selects from `events` ordered by `created_at` descending with `LIMIT 10`. The table contains 100 million rows. The query is slow. The developer argues that retrieving ten rows should never be expensive.

What's wrong with that reasoning?

### Challenge F — Adding Five Indexes

**Suggested time: 8 minutes**

A colleague proposes adding indexes on every frequently used column to improve read performance.

The system already processes thousands of writes per second. What consequences would you consider before approving the change?

---

# 18. Solutions and Discussion

*Listen or read only after you have answered each challenge out loud.*

### Solution A — Unused index

If 92% of rows match the filter, an index may provide little benefit. The executor would still need to retrieve almost the entire table. Using the index could add substantial heap-access overhead.

A sequential scan may be cheaper.

I would examine the execution plan, actual data distribution, requested columns, and query frequency before making any change.

If the business frequently needs the minority of orders that are not completed, a targeted index for those operations might be much more valuable.

The existence of an index doesn't create an obligation to use it.

### Solution B — Composite index order

A strong candidate is an index on hotel, then check-in and ID descending:

```sql
CREATE INDEX ON reservations (
  hotel_id,
  check_in DESC,
  id DESC
);
```

The hotel equality condition identifies the relevant group. The date range narrows the search. The ordering aligns with the index's structure.

The limit may allow early termination.

An index beginning with `check_in` is not necessarily equivalent because it organizes rows by date before hotel.

It may be less effective for retrieving one hotel's ordered reservations. The optimal choice still depends on real workload characteristics.

### Solution C — Misleading execution plan

PostgreSQL expected roughly 100 rows but produced 850,000.

This suggests that its statistical model, predicate assumptions, or estimates derived from the query structure were substantially wrong.

Possible causes include stale statistics, correlated columns, skewed data, or difficult expressions.

The planner may have chosen a nested-loop join expecting a small outer result. With 850,000 rows, the inner operation might execute hundreds of thousands of times. A hash join or another strategy could potentially be cheaper.

The correct investigation is to identify where the first large estimation error occurs and why.

### Solution D — ORM dilemma

The endpoint may execute hundreds of queries despite each query being individually fast. I would inspect the generated SQL and count database calls per request.

Potential solutions include batching related data retrieval, using appropriate joins, or fetching IDs first and loading associations in a controlled number of queries.

But one giant join isn't automatically optimal. Multiple one-to-many relationships can multiply result rows.

The goal is a predictable, efficient access pattern with acceptable result size and round-trip count.

### Solution E — Surprisingly slow LIMIT

Without an appropriate index, PostgreSQL may need to examine a huge number of rows to identify the ten most recent events.

It can potentially use a bounded top-N sort, but it still needs to process the candidates. An index on an appropriate ordering key, such as created-at and ID descending, can support efficient retrieval of the latest records:

```sql
CREATE INDEX ON events (created_at DESC, id DESC);
```

The ordering must match the query's actual requirements, and the unique tie-breaker helps deterministic pagination.

The important difference is between *returning ten rows* and *finding which ten rows should be returned*.

### Solution F — Adding five indexes

Every additional index consumes storage and may increase insertion, update, deletion, WAL, and maintenance overhead.

Indexes can also interfere with HOT-update opportunities and place additional pressure on memory and storage caches.

I would require concrete query patterns and performance evidence before adding several indexes.

Then I would assess their overlap, size, selectivity, read benefit, and write overhead.

Sometimes one carefully designed composite index replaces several less useful single-column indexes.

More indexes are not automatically better.

---

# 19. The Mental Model Worth Keeping

Back to the Monday dashboard: identical SQL, healthy CPU, and a query that is 250 times slower in production — not because the statement changed, but because fourteen million rows and the wrong physical access path made the planner's choice expensive.

That's what makes SQL performance different from ordinary application profiling.

**SQL performance is determined not only by what you ask the database to return, but by the physical work required to find and produce that result.**

Several important consequences follow. A sequential scan isn't automatically bad. An index scan isn't automatically good.

Indexes help when they reduce expensive work enough to justify their own access and maintenance costs.

Composite indexes are particularly valuable when they align with real filters and ordering requirements.

The query planner decides how to execute SQL using estimates derived from available statistics.

Those estimates can be wrong, especially when data distributions are skewed or columns are correlated.

`EXPLAIN ANALYZE` allows us to compare the planner's assumptions with observed execution.

Joins are algorithms with different performance characteristics, not merely SQL syntax connecting tables.

ORMs make database access convenient but cannot eliminate query multiplicity, join multiplication, or expensive access patterns.

Pagination choices determine how much data must be traversed to retrieve a page. And the entire optimization process should begin with evidence rather than folklore.

Remember these durable distinctions:

- **SQL ≠ recipe** — you describe the result; the planner chooses the algorithm.
- **Seq scan ≠ failure; index ≠ win** — cost depends on how much data you need and how you access it.
- **Selectivity ≠ column presence** — indexes help when they shrink expensive work.
- **Composite order ≠ interchangeable** — equality, range, and `ORDER BY` alignment matter.
- **`EXPLAIN` ≠ reality; `ANALYZE` ≠ free** — estimates can lie; measured plans still execute the statement.
- **N+1 ≠ fast queries** — multiplicity and row explosion hide behind convenient ORMs.
- **`LIMIT` ≠ limited work; deep `OFFSET` ≠ teleport** — pagination is an access pattern.
- **More indexes ≠ faster system** — every index is write, WAL, and maintenance cost.

> **The master sticky note**
>
> When a query becomes slow, investigate the work PostgreSQL is performing before changing the code or adding infrastructure.

The most useful question isn't "Why is PostgreSQL slow?" It's: **What work did PostgreSQL decide was necessary, and was that decision appropriate for the actual data?**

Once you can answer that question, database performance stops looking like mysterious machinery and becomes an engineering problem you can reason about.

---

# 20. Next Lecture — CS330-L03: Transactions — When Correct Operations Produce Incorrect Results

We've spent an entire lecture making databases faster. Now we're going to make them correct.

Or rather, investigate why apparently correct database operations can combine to produce catastrophically incorrect outcomes.

Imagine a hotel with one Deluxe room left for tomorrow night. Two customers attempt to reserve it simultaneously. Both requests check availability.

Both see one room remaining. Both begin database transactions. Both create reservations.

Both commit successfully. And somehow, the hotel has sold its final room twice.

The disturbing part is that neither individual request necessarily contains an obvious programming mistake.

Even placing every operation inside a database transaction doesn't automatically solve every concurrency problem.

Why? What exactly does a transaction guarantee? What is isolation?

How does PostgreSQL let different transactions read and modify data simultaneously? What are MVCC snapshots, row locks, lost updates, write skew, and serialization failures?

And why can two transactions each observe a perfectly reasonable world while collectively creating an impossible one?

In **CS330-L03**, we'll examine **ACID, transaction isolation, MVCC, locking, concurrency anomalies, and optimistic concurrency control**.

We'll construct the double-booking problem, reproduce it, and explore several ways to prevent it.

This will be one of the most important sessions in the course. Because a slow booking system is inconvenient.

A fast booking system that confidently sells rooms it doesn't have is a considerably more expensive form of entertainment.

---

## Optional Practical Lab — Watch PostgreSQL Change Its Mind

*The spoken lecture ends here. The remaining material is a screen-first investigation worksheet and technical references.*

Build a small dataset and watch how query planning changes.

The experiment deliberately creates hundreds of thousands of reservations, but it doesn't need a production-scale database.

Use a local PostgreSQL instance or a disposable test database.

**Suggested time: 25–35 minutes.**

> **Gym rules:** predict the plan shape before you run each `EXPLAIN`. Challenge spoilers are in Solutions and Discussion above; lab answers follow the experiments.

### Experiment A — Create the table

Drop any prior demo table and create `demo_reservations` with identity primary key, hotel, customer, check-in, status, and total:

```sql
DROP TABLE IF EXISTS demo_reservations;

CREATE TABLE demo_reservations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

  hotel_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,

  check_in DATE NOT NULL,
  status TEXT NOT NULL,

  total_minor INTEGER NOT NULL
);
```

### Experiment B — Generate sample data

Insert roughly 300,000 random reservations across about 100 hotels and 50,000 customers, with check-ins over three years and about 70% confirmed:

```sql
INSERT INTO demo_reservations (
  hotel_id,
  customer_id,
  check_in,
  status,
  total_minor
)
SELECT
  1 + floor(random() * 100)::INTEGER,

  1 + floor(random() * 50000)::INTEGER,

  DATE '2025-01-01'
    + floor(random() * 1095)::INTEGER,

  CASE
    WHEN random() < 0.7 THEN 'confirmed'
    ELSE 'cancelled'
  END,

  10000 + floor(random() * 90000)::INTEGER

FROM generate_series(1, 300000);
```

Because the data is random, the exact distribution varies from run to run. Refresh planner statistics with `ANALYZE demo_reservations;`.

### Experiment C — Investigate the unindexed query

Run `EXPLAIN (ANALYZE, BUFFERS)` on a selective hotel-and-date dashboard-style query with limit 25:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT
  id,
  customer_id,
  check_in,
  total_minor
FROM demo_reservations
WHERE hotel_id = 42
  AND status = 'confirmed'
  AND check_in >= DATE '2026-10-01'
  AND check_in < DATE '2026-11-01'
ORDER BY check_in DESC, id DESC
LIMIT 25;
```

Inspect the plan. You may see a sequential scan followed by a sort and limit.

The precise choice and timings depend on the PostgreSQL version, machine, data distribution, and cache state.

Don't assume a particular execution plan is guaranteed. Notice how many rows are examined relative to the final 25.

### Experiment D — Introduce a partial composite index

Create a partial index for confirmed rows keyed by hotel, then check-in and ID descending; refresh statistics; re-run the same `EXPLAIN (ANALYZE, BUFFERS)`:

```sql
CREATE INDEX idx_demo_confirmed_hotel_date
ON demo_reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
WHERE status = 'confirmed';
```

Then `ANALYZE demo_reservations;` and compare plans. Questions to investigate:

Did PostgreSQL choose an index scan? Did the explicit sort disappear? How many rows were retrieved?

How much buffer activity occurred? Was the result materially faster?

Don't worry if it isn't dramatically faster. This dataset is relatively small, and much of it may already be cached.

The useful observation is the change in access strategy.

### Experiment E — Ask a different question

Try `EXPLAIN (ANALYZE, BUFFERS)` selecting every confirmed reservation with `SELECT *`.

Will the partial index from Experiment D necessarily help? No. This query retrieves a large fraction of the table.

A sequential scan may be cheaper. Furthermore, the index contains only some of the columns needed by `SELECT *`. The query is fundamentally different from the selective dashboard lookup.

### Experiment F — Explore pagination

Compare a large offset against the first page — same filters and ordering, `LIMIT 25 OFFSET 1000` versus `OFFSET 0` — with `EXPLAIN (ANALYZE, BUFFERS)`.

Look at how much work the executor performs.

Then retrieve the last `(check_in, id)` pair from the first page and experiment with keyset pagination.

If the dataset doesn't contain enough matching rows for a large offset, reduce it.

The objective is to understand how the access pattern changes—not to produce impressive benchmark figures.

### Experiment G — Optional: Explore index-only scans

Create a covering partial index that includes customer and total as payload:

```sql
CREATE INDEX idx_demo_covering
ON demo_reservations (
  hotel_id,
  check_in DESC,
  id DESC
)
INCLUDE (customer_id, total_minor)
WHERE status = 'confirmed';
```

In this disposable test database, you can run `VACUUM (ANALYZE) demo_reservations;`.

Then inspect the selective query again. Look for an `Index Only Scan`, if the planner chooses one, and examine `Heap Fetches`.

The `VACUUM` operation can help establish all-visible heap pages, making index-only scans more attractive.

But the planner still chooses according to estimated cost.

**The experiment's real achievement is learning to read the database's reasoning rather than merely measuring one number.**

### Lab solutions

**Experiment C.** An unindexed selective query often shows a sequential scan (or other whole-table-ish path) plus sort/limit; rows examined dwarf the final 25.

**Experiment D.** A matching partial composite index frequently shifts the plan toward an index (or bitmap) path and may remove an explicit sort when ordering aligns; buffer and timing gains depend on cache and scale.

**Experiment E.** A low-selectivity `status = 'confirmed'` scan of most of the table often prefers a sequential scan; the partial index is not obligated to win.

**Experiment F.** Large `OFFSET` still walks preceding qualifying rows; keyset predicates with a matching ordered index navigate nearer the resume point.

**Experiment G.** Covering indexes enable index-only scans when visibility allows; nonzero `Heap Fetches` means some heap checks remain.

---

## Further Reading

These official PostgreSQL references provide authoritative explanations and examples:

- **Using EXPLAIN:** https://www.postgresql.org/docs/current/using-explain.html
- **Multicolumn Indexes:** https://www.postgresql.org/docs/current/indexes-multicolumn.html
- **Partial Indexes:** https://www.postgresql.org/docs/current/indexes-partial.html
- **Index-Only Scans:** https://www.postgresql.org/docs/current/indexes-index-only-scans.html
- **Indexes and ORDER BY:** https://www.postgresql.org/docs/current/indexes-ordering.html
- **Planner Statistics:** https://www.postgresql.org/docs/current/planner-stats.html
- **LIMIT and OFFSET:** https://www.postgresql.org/docs/current/queries-limit.html
