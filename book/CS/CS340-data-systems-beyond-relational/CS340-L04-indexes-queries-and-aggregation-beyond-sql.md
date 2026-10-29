---
id: CS340-L04
course: CS340
title: "Indexes, Queries, and Aggregation Beyond SQL"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L03
next: CS340-L05
---



<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / CS345
Preserve conceptual coverage of aggregation cost, deep pagination, $lookup/$unwind,
and explain literacy here. When CS345 exists, point to its diagnostic studios and
production-cases/MONGO-* for hands-on plan forensics. Do not regenerate this lecture
as a lab course.
-->







# CS340 — Data Systems Beyond Relational Databases

## Lecture 04: Indexes, Queries, and Aggregation Beyond SQL

*Why a database can have dozens of indexes and still scan millions of documents, how MongoDB decides what to read, and why the fastest query is often the one that avoids doing most of the work.*

---

# 1. The Query That Worked Perfectly Until Someone Used It

It's Monday morning at our hotel-booking company, and the product team is celebrating a new search feature.

Customers can now search hotels by city, price category, amenities, and ratings. Results can be sorted by rating, with the best hotels appearing first.

The backend uses MongoDB.

Development was straightforward. Each hotel is represented as a document containing its location, descriptions, amenities, rating, and other catalogue information.

The query is readable. It finds hotels in Prague, requires parking, filters for highly rated properties, sorts by rating, and returns the first twenty results.

In development, the request completes almost instantly.

The staging environment behaves similarly.

Then the feature reaches production.

At first, everything appears healthy. But as customers begin using the new filters, certain requests become painfully slow.

Some take three seconds. Others take eight.

A few time out completely.

The backend's CPU utilization rises. Database read activity increases dramatically. Customers begin abandoning searches.

The database contains several million hotel documents, but the query returns only twenty results.

That seems absurd.

Why would finding twenty hotels require so much work?

One engineer suggests increasing MongoDB's memory allocation.

Another proposes creating an index on every field used in the search.

A third recommends migrating the entire catalogue to Elasticsearch.

The database administrator opens the query execution plan.

The results are rather embarrassing.

For one problematic request, MongoDB examines more than a million candidate documents to return twenty results.

The application has asked for twenty hotels.

The database has inspected an enormous fraction of its collection to find them.

This isn't necessarily a database failure.

It's an **access-path failure**.

The query describes what the application wants, but the available physical structures don't let the database reach that answer efficiently.

Today we're going to investigate how databases solve that problem.

We'll examine indexes as physical access paths, why compound key order matters, how arrays complicate indexing, why the query planner sometimes makes surprising decisions, and how aggregation pipelines can accidentally transform modest questions into enormous computational workloads.

Our goal isn't to memorize MongoDB operators.

It's to develop an intuition for **how much work a query forces the database to perform**.

That intuition transfers to PostgreSQL, Elasticsearch, analytical databases, and virtually every system that retrieves structured information.

---

# 2. A Query Is a Question, Not an Execution Plan

Let's begin with the distinction between what a query means and how the database answers it.

Suppose our application requests all hotels in Prague with a rating of at least four stars.

Logically, the request is simple.

Find documents satisfying two conditions.

But physically, the database has several possible strategies.

It could read every document in the collection and evaluate both conditions.

It could use an index on the city field to find Prague hotels, then inspect those documents to check their ratings.

It could use an index on rating first, then check each candidate's city.

Or it might use a compound index that organizes both fields together.

The correct logical result is the same.

The amount of physical work can differ enormously.

## 2.1 The collection scan

Imagine the catalogue contains five million hotels.

Only twenty thousand are in Prague.

A **collection scan** examines documents in the collection and evaluates the query conditions as it encounters them.

Without a suitable index, this may be the straightforward way to obtain the answer.

For a small collection, a collection scan can be perfectly reasonable.

Sequentially examining several hundred documents may be cheaper than navigating an index and performing additional lookups.

But if the collection contains millions of documents and the query is highly selective, inspecting everything becomes expensive.

This is why an index exists.

An index helps the database eliminate large portions of the search space.

## 2.2 An index is an alternative physical organization

Think of a telephone directory organized alphabetically by surname.

If you're searching for one surname, the ordering is useful.

But if you want everyone born in July, the surname index may not help much.

The information is organized according to one access pattern.

Database indexes work through the same principle.

An index maintains additional information organized for particular searches, ranges, or sorts.

MongoDB commonly uses B-tree-family index structures for ordinary indexes.

The database can navigate that ordered structure to locate candidate documents without examining every document in the collection.

But the index is not the complete collection.

It is an additional data structure maintained alongside the stored documents.

Every index consumes storage and memory, and modifying indexed information can require additional work.

This introduces the first major trade-off.

**Indexes make selected reads cheaper by making storage and writes more expensive.**

We already encountered this in CS330, but document databases introduce several interesting complications.

---

# 3. Selectivity: The Question Behind Every Useful Index

Suppose our catalogue contains five million hotels.

Four million support Wi-Fi.

Two million offer breakfast.

Twenty thousand are in Prague.

Only two hundred satisfy a particularly restrictive combination of filters.

Which field would be most useful for narrowing a search?

Often, the highly selective condition.

**Selectivity** describes how effectively a condition reduces the candidate set.

A condition matching nearly every document has low selectivity.

A condition matching a tiny fraction has high selectivity.

An index on a highly selective condition can let the database ignore most of the collection.

But selectivity is not the entire story.

## 3.1 Why the most selective field doesn't always go first

Imagine our application runs this query:

Find hotels in Prague, with an active listing status, ordered by rating from highest to lowest, returning twenty results.

The city condition may be selective.

The active-status condition may not be.

But sorting introduces another requirement.

An index can help the database find matching documents.

It can also supply documents in an order useful to the query.

Sometimes an index that reads somewhat more candidate entries but avoids an expensive sort is faster overall.

So the best index isn't always the one that filters most aggressively at the first step.

We must consider the entire operation.

What conditions narrow the result?

What order is required?

How many results are returned?

Which fields must be retrieved?

And how many physical reads will the plan perform?

## 3.2 Cardinality

You'll also encounter the word **cardinality**.

In database discussions, this often refers to the number of distinct values in a field, although query optimizers also use cardinality to describe estimated or actual result counts.

Consider a boolean field named `isActive`.

It has very low distinct-value cardinality: true or false.

An index on that field alone may have limited value if almost every hotel is active.

Now consider a unique hotel identifier.

It has very high cardinality.

A lookup by that identifier can locate a single document efficiently.

But don't memorize a rule that high-cardinality fields always deserve indexes.

A field's usefulness depends on actual query predicates, the distribution of values, required ordering, and the cost of maintaining the index.

An index that nobody uses is not a performance feature.

It is a maintenance expense.

---

# 4. Compound Indexes: Why Field Order Matters

Now our investigation becomes more interesting.

We create an index containing multiple fields.

This is a **compound index**.

Suppose the index organizes hotels by city, then listing status, then rating.

Conceptually, it resembles a directory sorted first by city, then by whether the listing is active, and finally by rating.

Within the group of active hotels in Prague, ratings are ordered.

That arrangement can support our search efficiently.

The database can navigate to the relevant city and status range, then read entries in rating order.

It may find the first twenty matching entries without sorting thousands of documents independently.

But the order of fields in the index matters enormously.

## 4.1 The leftmost-prefix principle

Imagine an index ordered by city, status, and rating.

A query filtering by city alone can often use the leading portion of that index.

A query filtering by both city and status can also use the prefix.

But a query filtering only by rating cannot generally exploit the index's complete ordering as though rating were the first field.

Why?

Because ratings are organized within groups defined by the preceding keys.

The high-rated hotels are not all stored together globally.

They are distributed across cities and statuses.

Think of a telephone directory sorted by surname and then first name.

It is excellent for finding everyone named Smith.

It is not especially useful for finding everyone named Daniel regardless of surname.

The index contains first names, but they are ordered only within each surname group.

This is the intuition behind compound-index prefixes.

## 4.2 Equality, Sort, Range

MongoDB documentation describes a useful index-design guideline called **Equality, Sort, Range**, commonly abbreviated ESR.

Equality predicates match specific values.

Sort describes the required result ordering.

Range predicates include comparisons such as greater than, less than, or a bounded interval.

For many common queries, placing equality fields first, followed by the sort fields and then range fields, helps the engine use the index efficiently.

But ESR isn't an inviolable law.

If a range condition is extremely selective, placing it before a sort field may reduce the number of index entries examined enough to justify a separate sort.

This variation is sometimes described as Equality, Range, Sort.

The right choice depends on the workload.

Let's consider an example.

The query requires city equals Prague, active status equals true, rating at least four, and results ordered by popularity.

An index beginning with city and status makes sense because those equality conditions define the relevant subset.

Should popularity or rating come next?

If there are relatively few highly rated Prague hotels, using the rating range early might dramatically reduce candidate work.

But if the query requires the twenty most popular results and thousands of hotels satisfy the rating condition, an index ordered by popularity may avoid expensive sorting and permit early termination.

The best plan depends on the data distribution and query requirements.

This is why good engineers measure.

**Index design is not arranging field names according to aesthetic preference. It is organizing the data around how queries actually consume it.**

## 4.3 Direction and sorting

MongoDB index specifications use ascending and descending directions.

A simple single-field index can generally be traversed in either direction to support ascending or descending ordering.

For compound indexes, however, the relative direction of the indexed fields matters when satisfying multi-field sorts.

If a query sorts by rating descending and review count ascending, the index must provide a compatible ordering pattern, or the database may need additional sorting work.

Again, index definitions encode physical ordering.

They aren't merely a declaration that certain fields should become faster.

---

# 5. The Index Was Used—and the Query Was Still Slow

The engineering team creates a compound index.

The query execution plan now reports that an index scan was used.

Success?

Not necessarily.

This is one of the most important lessons in database performance.

**Using an index is not the same as using an index efficiently.**

Imagine a query that scans one million index entries, fetches eight hundred thousand documents, and returns twenty results.

Technically, it used an index.

Operationally, it still performed an enormous amount of work.

## 5.1 Index scan versus document fetch

An ordinary index contains indexed key information and references needed to locate documents.

Suppose our query filters hotels by city using an index.

The database locates candidate entries for Prague.

But the query also needs the hotel's full description, images, and other fields not stored in the index.

The engine must retrieve the corresponding documents.

This is often represented through an index scan followed by a fetch operation.

If the index narrows the candidate set to twenty documents, that's excellent.

If it produces hundreds of thousands of candidates that must each be examined, the index may not have helped enough.

## 5.2 Covered queries

Now consider a query that needs only a hotel's name and rating.

Suppose the relevant filter fields and returned fields are all available within an appropriate index.

Under suitable conditions, MongoDB can answer the query using index information without fetching full collection documents.

This is a **covered query**.

For many query shapes, the execution statistics can show zero documents examined.

That is useful because fetching documents may require additional memory access and storage I/O.

But coverage has conditions.

The query, projection, index fields, and other relevant semantics must be compatible.

For example, MongoDB includes `_id` in ordinary projections by default. If `_id` isn't part of the index and isn't needed, explicitly excluding it may be necessary for coverage.

Multikey indexes also introduce restrictions on which projections they can cover.

A covered query isn't a magical optimization that every index automatically supplies.

It is a useful consequence of having enough information in an appropriate access structure.

---

# 6. Multikey Indexes: One Document Can Produce Many Index Entries

Our hotel documents contain an array of amenities.

One hotel might have Wi-Fi, parking, breakfast, a swimming pool, and a gym.

Another might have only Wi-Fi.

How should an index on the amenities field behave?

MongoDB supports **multikey indexes** for array-valued fields.

Conceptually, one document can contribute multiple index entries, one for each distinct indexed array value.

This allows a query searching for hotels with parking to use an index rather than scanning every hotel document.

But arrays complicate the relationship between documents and index entries.

## 6.1 Index cardinality isn't document cardinality

Imagine one million hotel documents.

Each contains an average of twenty distinct amenity values.

An index on the amenity array may contain many more entries than the document count.

This can increase index storage and maintenance costs.

It also complicates the interpretation of query statistics.

A single document may contribute several relevant index entries.

The database must avoid returning the same document multiple times merely because several index entries match.

Indexes on arrays are useful, but their cost depends on array sizes and values.

## 6.2 The two-room trap

Now imagine a hotel document containing two embedded room objects.

The first room has capacity four and costs 300 euros.

The second room has capacity two and costs 120 euros.

A customer searches for rooms with capacity at least four and price below 200 euros.

Does this hotel contain a room satisfying both conditions?

No.

But a query that independently tests the nested capacity path and nested price path may match the document because different elements satisfy the two conditions.

One room satisfies the capacity requirement.

Another satisfies the price requirement.

The document contains both values, but no single room satisfies the combined requirement.

This is a query-semantics bug, not merely a performance problem.

MongoDB's **`$elemMatch`** operator allows the application to require that one array element satisfy the specified conditions together.

The difference is fundamental.

We are asking whether one room satisfies both requirements, not whether the hotel contains those values somewhere.

## 6.3 Array semantics affect index bounds

The complication reaches the index planner.

For suitable compound multikey indexes over fields from the same array of embedded documents, MongoDB can use `$elemMatch` and shared field paths to constrain the scan more precisely.

Without the appropriate element-matching semantics, combining index bounds may not be valid because conditions could apply to different array elements.

There are also restrictions on compound multikey indexes involving separate array fields.

For example, MongoDB doesn't permit a compound multikey index where more than one indexed field is an array in the same indexed document.

The full rules are implementation-specific, but the motivation is understandable.

Combining multiple independent arrays can create ambiguous or explosively large combinations of index entries.

This reinforces an idea from CS340-L03.

Nested data is convenient only when we understand the semantics of the relationships it represents.

The document model and query model must agree.

---

# 7. Specialized Indexes: One Size Doesn't Fit Every Query

We've concentrated on ordinary ordered indexes.

But modern document databases provide several other indexing strategies.

Each exists because different query shapes need different access paths.

## 7.1 Partial indexes

Suppose our catalogue contains active and archived hotels.

Most customer-facing queries need only active hotels.

Maintaining one large index covering every historical listing may be unnecessarily expensive.

A **partial index** includes only documents satisfying a specified filter expression.

For example, an index might cover only active properties.

That can reduce index size and maintenance work for documents outside the indexed subset.

But there's a correctness requirement.

The query planner cannot use a partial index to answer a query if doing so would omit records the query is allowed to return.

Therefore, the query must include conditions that make the partial index's subset appropriate.

A partial index isn't simply a smaller index that every query can use interchangeably.

It encodes a restriction on which documents are represented.

## 7.2 TTL indexes

Some data has a natural expiration time.

Imagine temporary session records, diagnostic events, or short-lived operational data.

MongoDB supports **TTL indexes**, which can help remove documents after an expiration condition.

But expiration is not a guaranteed exact-time deletion event.

MongoDB's background TTL process removes eligible documents according to its operational behavior.

A document may remain for some time after becoming eligible for expiration.

This distinction matters for business correctness.

A TTL index can be useful for storage lifecycle management.

It should not be the only mechanism enforcing a critical deadline such as whether a reservation hold remains valid.

The application must check the relevant expiration rule directly when correctness depends on it.

## 7.3 Text, geographical, and search-specific indexes

MongoDB also supports indexing approaches for textual and geospatial queries.

For example, geospatial indexes can help answer location-oriented questions such as finding properties near a coordinate.

Traditional text indexes support certain full-text search capabilities.

More sophisticated search workloads may benefit from dedicated search functionality, including MongoDB Search or a separate search engine.

These systems address different needs.

An ordinary B-tree index on a hotel description is not equivalent to a linguistic search index capable of tokenization and relevance ranking.

An index designed for geographical proximity isn't interchangeable with an ordinary numeric range index.

The key principle is the same.

**Choose the access structure according to the mathematical and semantic operation the application needs.**

We'll examine specialized systems more broadly in CS340-L06.

---

# 8. The Query Planner: The Database Makes a Bet

Suppose MongoDB has several possible indexes for our hotel search.

How does it choose?

The database's query-planning machinery considers available access paths and develops candidate execution strategies.

The details vary by MongoDB version and query engine.

But the general responsibility is to identify an efficient way to execute the requested operation.

This is an optimization problem.

And like other optimizers, a query planner works with imperfect information and practical constraints.

## 8.1 The winner isn't always globally optimal

Imagine two possible plans.

Plan A uses an index on city and then filters ratings.

Plan B uses a compound index that also supports sorting by rating.

The better choice depends on how many candidate documents each plan must examine, their distribution, and the cost of sorting and fetching.

A planner may evaluate candidate plans and select one according to its mechanisms.

Some plans can be cached for reuse with similar query shapes.

But a plan that performs well for one set of parameter values may behave less impressively for another.

Suppose a search for hotels in a small city returns fifty candidates.

The same query structure for London might return fifty thousand.

A plan suitable for the small city isn't automatically ideal for the large city.

The physical workload has changed even though the query structure looks similar.

## 8.2 Data distributions change over time

Imagine an index created when almost every hotel was active.

Several years later, most historical listings are archived.

The selectivity of the active-status field has changed.

A query optimizer must make decisions using the information and mechanisms available to it.

Real data distributions can change, and those changes can alter which plans are effective.

This is one reason query performance can deteriorate even when application code hasn't changed.

The data grew or changed shape.

The old access pattern now costs something different.

## 8.3 Don't blame the planner before examining the query

It is tempting to treat the query planner as an unpredictable black box.

Sometimes an optimizer genuinely makes a poor choice.

But often the problem is that the application has not provided a suitable index for the query's requirements.

Or the query itself requests expensive work.

Or the available index serves filters but not sorting.

Before forcing a particular plan with a hint, understand why the chosen plan is expensive.

A hint can be useful during diagnosis or in a carefully controlled workload.

But forcing one plan forever can become another source of technical debt when data distribution or query behavior changes.

---

# 9. Reading `explain`: The Database Testifies

We now return to our production incident.

Our hotel search is slow.

How do we move from speculation to evidence?

MongoDB provides `explain`, which exposes information about query planning and, in appropriate modes, execution statistics.

The exact output format can vary between server versions and query engines.

But several concepts remain especially useful.

## 9.1 The three numbers worth understanding first

Imagine an execution report containing these illustrative values.

Documents returned: 20.

Index keys examined: 850,000.

Documents examined: 620,000.

This tells us that the query returned very little relative to the amount of work performed.

The planner used some index information, but the path wasn't selective enough or didn't align sufficiently with the complete query.

Now imagine an improved plan.

Documents returned: 20.

Index keys examined: 24.

Documents examined: 20.

That's a dramatically different access pattern.

The same logical query produced the same twenty results.

But the database performed far less candidate examination.

These statistics aren't the complete story.

Wall-clock time, caching, storage activity, contention, and other factors still matter.

But they provide strong evidence about the amount of work the query performs.

## 9.2 Important plan concepts

A **COLLSCAN** indicates collection-scanning work.

An **IXSCAN** indicates scanning an index.

A **FETCH** indicates retrieving documents as part of the execution plan.

A **SORT** stage can indicate explicit sorting work not fully supplied by an appropriate index ordering.

The exact plan representation depends on the server and query engine, and some operators may appear differently in newer execution formats.

Don't memorize every possible stage name.

Instead, ask:

Where is the engine finding candidates?

How many candidates is it examining?

Which conditions are applied through indexes?

Which conditions require fetching documents?

Where is sorting occurring?

How many results survive each stage?

Those questions provide a transferable mental model.

## 9.3 Explain isn't a normal production request

There's a subtle operational detail.

MongoDB's `explain` can evaluate candidate plans separately from ordinary plan-cache reuse.

Consequently, an explained query may not behave identically to a normal execution using an already cached plan.

`executionStats` provides valuable information about the winning plan's measured work, but the execution also has its own environmental conditions.

A representative production investigation should therefore combine explain information with actual query latency, profiler evidence, query shape, workload conditions, and index usage.

**An execution plan explains the work a query performs. It is not a substitute for measuring the application experience.**

---

# 10. Aggregation Pipelines: Programming a Data Factory

Our company now wants a business dashboard.

For each city, the product team wants to know how many active hotels meet certain quality requirements and what their average rating is.

The operation involves filtering, grouping, calculating aggregate values, sorting, and returning the results.

MongoDB's **aggregation pipeline** provides a way to express such transformations.

Think of a pipeline as a series of stages.

Each stage receives documents or intermediate results, performs an operation, and passes its output to the next stage.

The final result might contain records that look nothing like the original documents.

A hotel document might contain dozens of fields.

An aggregate result might contain only a city and its average rating.

## 10.1 The core stages

The most useful stages to recognize are straightforward.

**`$match`** filters documents according to conditions.

**`$project`** selects, reshapes, or computes fields.

**`$group`** groups documents by a key and calculates aggregate values.

**`$sort`** orders the results.

**`$limit`** restricts the number of results.

**`$unwind`** expands array elements into separate pipeline documents.

**`$lookup`** combines data with information from another collection.

These stages form a powerful language for transforming document collections.

But their convenience makes it easy to hide enormous computational work inside a compact pipeline.

A four-stage aggregation can be far more expensive than a lengthy-looking ordinary query.

The important question remains the same.

How many documents enter each stage, and what work must the stage perform?

---

# 11. Filter Early: The Most Important Pipeline Optimization

Imagine our analytics query concerns only active hotels in Prague.

The collection contains five million hotels.

Prague has twenty thousand.

Of those, perhaps fifteen thousand are active.

We eventually want the average rating of those active Prague hotels.

Now consider two possible approaches.

One pipeline begins by grouping all five million hotels into city summaries, then filters for Prague.

Another filters for active Prague hotels first, then performs the grouping.

The second approach can process dramatically fewer documents during grouping.

The principle is simple.

**Do the most useful reduction before expensive work, whenever the semantics permit it.**

## 11.1 Filtering changes the cost of everything downstream

Suppose a pipeline performs a costly join-like operation for every hotel.

If we reduce the input from five million to fifteen thousand first, we can avoid millions of unnecessary downstream operations.

The same idea applies to sorting, grouping, and expensive projections.

But there is an important qualification.

MongoDB has its own aggregation optimizer.

The engine can reorder certain stages and push filters into earlier execution stages when it can prove that doing so preserves the meaning of the query.

This means the pipeline as written is not always the pipeline as physically executed.

For example, filtering conditions that do not depend on computed fields can sometimes be moved before projections or other transformations.

The optimizer may also combine or rewrite certain stage sequences.

So "put `$match` early" is a valuable design principle, not a demand to manually reproduce work the optimizer already performs.

The right process is to express clear semantics, inspect the optimized plan, and measure the result.

## 11.2 Don't project everything just because you can

Developers sometimes place a large `$project` stage at the beginning of every pipeline, believing that manually removing unused fields must always improve performance.

But MongoDB's optimizer can often identify which fields are required and avoid carrying unnecessary data through parts of execution.

A manual projection may improve clarity or support a necessary transformation.

It isn't automatically a performance improvement.

Worse, a transformation can interfere with access to an efficient index or prevent certain optimizations.

Optimize based on actual execution behavior.

Not on the visual appearance of the pipeline.

---

# 12. Blocking Stages: Why a Query Suddenly Needs a Lot of Memory

Some pipeline operations can emit results progressively.

Others need to accumulate substantial information before producing useful output.

This distinction matters.

Imagine reading hotels one at a time and filtering out those not in Prague.

Each document can be accepted or rejected independently.

Now imagine sorting every hotel in Europe by a computed popularity score.

If the engine cannot obtain the required ordering from an index, it may need to collect and organize a large set of results.

Sorting becomes a potentially memory-intensive operation.

Grouping can have similar consequences when the database needs to maintain aggregate state for many distinct groups.

Such operations are often called **blocking stages**.

## 12.1 Sorting five million documents to return twenty

Consider the original hotel search.

The frontend requests only twenty hotels.

But the database may need to examine many candidate hotels before it knows which twenty have the highest rating.

If an index provides the required order, the database may be able to stop after finding enough suitable results.

Without such an ordering, the engine may need to process a far larger candidate set.

The result limit is small.

The work needed to discover the top results may not be.

This is why `limit(20)` is not automatically proof of an efficient query.

## 12.2 Top-k optimization

There is a useful middle ground.

If a pipeline sorts a large collection but returns only the top twenty results, a query engine may be able to maintain a limited set of top candidates rather than materializing a complete ordering of all input documents.

MongoDB can optimize suitable `$sort` followed by `$limit` sequences in this way.

But the engine still needs to evaluate enough candidates to determine which belong in the top results.

The optimization reduces memory and sorting work.

It doesn't necessarily eliminate scanning.

## 12.3 Memory limits and disk spilling

MongoDB imposes memory limits on relevant aggregation operations.

Under supported configurations, stages requiring more memory than the applicable threshold may write temporary data to disk when disk use is allowed.

For example, modern MongoDB versions support `allowDiskUse` behavior for appropriate aggregation stages.

The familiar 100-megabyte stage threshold is an important reference, but exact behavior depends on server version, configuration, and the stage. Newer versions may also impose additional per-operation limits.

Enabling disk spilling can allow a query to complete rather than fail because of an in-memory limit.

But spilling to disk isn't a performance optimization.

It is a way to handle larger intermediate workloads.

The query may become substantially slower and consume significant temporary storage I/O.

The better question is why the query needs so much intermediate data in the first place.

Could a selective filter run earlier?

Could an index provide the ordering?

Could the system maintain a precomputed aggregate?

Should the workload run in a specialized analytical system instead of the operational database?

Those are architectural questions.

Increasing a memory limit is merely one possible operational response.

---

# 13. `$unwind`: One Document Becomes Many

Now let's investigate a subtle source of workload amplification.

Our hotel documents contain arrays of amenities.

The analytics team wants to calculate how frequently each amenity appears in active hotel listings.

An aggregation might use `$unwind` to turn each amenity array element into a separate pipeline record.

Conceptually, a hotel containing twenty amenities becomes twenty intermediate documents.

That makes grouping by amenity straightforward.

But it also increases the number of records passing through subsequent stages.

## 13.1 Cardinality explosion

Suppose we begin with one million hotels.

Each contains an average of twenty amenity entries.

After unwinding the amenity arrays, the pipeline may process around twenty million intermediate records.

The original collection contains one million documents.

The aggregation now has twenty million units of work at that stage.

If we then perform an expensive lookup for each unwound record, the workload may become enormous.

This is **cardinality expansion**.

It is one reason apparently simple pipelines can produce surprising costs.

The query may begin with a manageable collection.

A transformation multiplies the number of intermediate records.

Every later stage inherits that increased workload.

## 13.2 The order of operations matters

Imagine we need amenities only for active hotels in Prague.

Filtering to Prague before unwinding reduces how many hotel documents generate expanded records.

Unwinding all hotels first creates a much larger intermediate stream.

The optimizer may be able to perform some reordering, but not every transformation can be moved freely without changing semantics.

We should design the pipeline around the intended relationships.

The lesson is broader than MongoDB.

SQL joins can multiply rows.

Graph traversals can expand candidate paths.

Event-processing pipelines can amplify messages.

Whenever one input can produce many outputs, ask how large the intermediate result might become.

---

# 14. `$lookup`: When Documents Need Relationships Again

In CS340-L03, we discussed embedding versus referencing.

Suppose hotel reviews live in a separate collection.

Now the product team wants a query returning hotels together with selected review information.

MongoDB's `$lookup` stage can combine data from another collection.

This demonstrates why the statement "document databases have no joins" is misleading.

But the ability to join doesn't eliminate its cost.

## 14.1 The indexed lookup

Imagine a query selecting one hundred hotels.

For each hotel, the pipeline retrieves related review records.

If the foreign collection has an appropriate index on the hotel identifier, the lookup can locate related records efficiently.

Without a suitable index, the system may need substantially more work.

The cost depends on the lookup form, available indexes, query planner, and number of input documents.

A lookup performed after filtering to one hundred hotels can be much cheaper than one performed for millions of hotels.

## 14.2 The join that creates enormous arrays

Suppose one popular hotel has two hundred thousand reviews.

A naïve lookup might attach a massive array of matching reviews to that hotel.

The intermediate result becomes large, expensive, and potentially subject to document-size or memory constraints.

Perhaps the application only needs the average rating and three recent reviews.

Then retrieving the entire review history is unnecessary.

A better design may calculate the required summary, perform a constrained lookup, or maintain suitable derived data.

This returns us to the data-modeling lesson.

A query that repeatedly reconstructs enormous nested aggregates may indicate that the document boundaries or access patterns deserve reconsideration.

## 14.3 Relationships always have a cost somewhere

Embedding makes some reads easy but can complicate writes and growth.

Referencing makes independent entity lifecycles easier but can require joins or multiple queries.

A derived summary can make reads cheap but requires synchronization.

There isn't a free option.

The engineering task is to pay the cost in the place where the workload can tolerate it.

---

# 15. Pagination: Why Page Ten Thousand Is Different From Page One

Our search API supports pagination.

The frontend requests twenty hotels per page.

The first page is fast.

The ten-thousandth page is slow.

Why?

The application uses offset-based pagination.

It sorts hotels by rating, skips the preceding results, and returns twenty.

A database generally cannot jump to the ten-thousandth result merely because the application specifies a skip count.

It may need to traverse or process the preceding results before producing the requested page.

An appropriate index can help maintain order, but skipping a large number of entries still has a cost.

## 15.1 Cursor-based pagination

An alternative is to remember the position of the last item from the previous page.

Suppose hotels are ordered by rating descending.

The next request can ask for hotels below the last rating already returned.

But ratings are not necessarily unique.

Several hotels might have exactly the same rating.

Without a deterministic tie-breaker, pagination can skip or repeat results.

A robust cursor may therefore include the rating and a stable unique identifier.

The query uses those values to continue from the previous position in the specified ordering.

This is often called **keyset pagination** or cursor-based pagination.

It can avoid the growing cost of skipping enormous offsets.

But it has trade-offs.

It is less convenient for jumping to an arbitrary numbered page.

And concurrent data changes may still affect how records appear between page requests unless the application requires and provides stronger snapshot semantics.

The appropriate choice depends on the product.

For infinite scrolling or sequential result browsing, cursor pagination is often attractive.

For certain administrative interfaces requiring arbitrary page navigation, offsets may remain acceptable.

Again, the data access pattern determines the strategy.

---

# 16. The Index That Made Writes Worse

Our team is now enthusiastic about indexes.

Every slow query receives another index.

One developer proposes indexing every frequently mentioned field.

The read dashboards improve.

Then the ingestion service begins slowing down.

Why?

Because indexes require maintenance.

Every inserted document may generate entries in several indexes.

Updates can require changing index entries when indexed values change.

Deletes require corresponding index maintenance.

MongoDB also needs to store and cache these additional structures.

## 16.1 The index budget

Imagine a collection with fifteen indexes.

A single insert must account for the collection data and the applicable entries in all fifteen index structures.

The exact physical work varies.

But the overhead is real.

More indexes consume storage, memory, CPU, and write I/O.

Indexes can also increase the cost of backups, maintenance, and schema evolution.

So a mature team doesn't simply count slow queries and create one index for each.

It examines the most important access patterns, identifies useful shared prefixes or compound indexes, and removes redundant structures where appropriate.

## 16.2 Why too many similar indexes are suspicious

Suppose a collection contains indexes beginning with the same two fields.

Some may be genuinely necessary because their later fields, directions, uniqueness, partial filters, or query roles differ.

Others may offer little additional value.

A compound index can sometimes support queries that use its leading prefix, making a shorter index partly redundant.

But don't automatically delete the shorter index.

It may still be smaller, cheaper to scan for certain workloads, or useful under particular planning conditions.

The correct decision requires examining actual index usage and query plans.

The principle is straightforward.

**Every index should justify the cost of keeping it up to date.**

---

# 17. Solving the Original Production Incident

Let's return to the hotel search that examined more than a million documents to return twenty results.

The query filters by city, active status, amenities, and minimum rating, then sorts by rating.

The collection has several indexes, but none aligns particularly well with the complete access pattern.

One index helps locate hotels in the selected city.

Another indexes ratings.

Another indexes amenities.

But the chosen plan still examines far too many candidates and performs substantial filtering and sorting work.

The problem isn't a lack of indexes in general.

It's a lack of appropriate access paths for the actual important queries.

## 17.1 First, identify representative query shapes

We examine production query patterns.

Which filters are usually supplied?

Which combinations are common?

Which sort orders matter?

How many results are requested?

Do some cities or property categories have dramatically different selectivity?

We avoid designing solely for one unusual query.

Instead, we identify the small number of high-value query shapes accounting for most customer traffic and resource consumption.

## 17.2 Build an index deliberately

For a common query filtering by city and active status, then sorting by rating, a compound index organized around those requirements is a strong candidate.

We evaluate how additional amenity or price conditions affect selectivity and whether they justify a different compound index.

If arrays are involved, we consider multikey semantics and restrictions carefully.

We don't assume that one giant index containing every possible filter will efficiently support every search combination.

And we remember that optional filters can produce many different query shapes.

The search feature may require several carefully chosen indexes rather than one universal access path.

## 17.3 Measure before and after

We compare explain statistics under representative data volumes and parameter values.

How many index keys were examined?

How many documents were fetched?

Was an explicit sort necessary?

How much memory did the operation consume?

What happened to high-percentile latency under concurrent load?

And what cost did the new indexes impose on writes?

The optimized query now returns the same twenty hotels after examining dramatically fewer candidates.

Its performance is better not because MongoDB acquired a new magical capability.

It's better because the physical data organization now matches the application's dominant question.

## 17.4 But what about full-text search?

The product team still wants sophisticated natural-language search.

We should not force ordinary B-tree indexes to solve problems they weren't designed for.

If relevance ranking, stemming, typo tolerance, and advanced linguistic search become central requirements, we should consider specialized search functionality.

The optimal architecture may use MongoDB for authoritative catalogue documents and a dedicated search index for discovery.

But that introduces synchronization and freshness requirements.

The result of our investigation isn't a universal recommendation to keep everything inside one database.

It's a framework for recognizing when an ordinary index is appropriate and when the workload requires a different access model.

---

# 18. The Oral Examination

Before reading the solutions, try answering these questions aloud.

For each one, explain the mechanism, the likely physical work, and what evidence you would collect.

## Challenge 1 — The index that didn't help

A query returns twenty documents.

MongoDB reports an IXSCAN, 700,000 index keys examined, and 500,000 documents examined.

A developer argues that the query is already optimized because it uses an index.

What's wrong with this conclusion?

What would you investigate next?

## Challenge 2 — Compound index order

A hotel search filters by city and active status, sorts by rating descending, and returns twenty results.

How would you begin designing a compound index?

Why might an index ordered primarily by rating be less useful for some versions of the query?

## Challenge 3 — The array query

A hotel has two room entries.

One has capacity four and price 300 euros.

The other has capacity two and price 120 euros.

A query independently tests whether any room has capacity at least four and whether any room costs below 200.

Why might the hotel match incorrectly?

How would `$elemMatch` change the semantics?

## Challenge 4 — The enormous aggregation

An aggregation groups five million hotels by city and then filters for Prague.

The product only needs Prague's result.

What optimization would you consider?

Why might the aggregation optimizer complicate your interpretation of the written pipeline?

## Challenge 5 — The slow `$lookup`

A pipeline performs a lookup against a review collection containing millions of documents.

The foreign collection has no index on the relationship key.

What work might the database perform?

How would you investigate and redesign the operation?

## Challenge 6 — The twenty-result illusion

An application sorts millions of documents by a computed field and returns twenty.

Why can the query remain expensive despite the small limit?

What are the differences between an index-supported sort, a top-k optimization, and an unrestricted full sort?

## Challenge 7 — Indexes versus writes

The team adds ten indexes to accelerate rarely used reporting queries.

Customer-facing writes become slower.

How would you decide which indexes to retain?

What alternatives might separate reporting costs from operational transactions?

## Challenge 8 — The deep pagination problem

The API sorts hotels by rating and uses a large skip value to retrieve page ten thousand.

Why is this expensive?

How would cursor-based pagination work, and why should the ordering include a unique tie-breaker?

---

# 19. Solutions and Discussion

## Solution 1 — Index efficiency

The query used an index but examined enormous numbers of index entries and documents to return twenty results.

The access path is inefficient relative to the result size.

Investigate the filter predicates, index bounds, selectivity, sort requirements, and why documents must be fetched.

Consider an index better aligned with the common query shape.

Measure actual performance as well as explain statistics.

## Solution 2 — Compound index

Begin with equality conditions such as city and active status.

Then consider rating order and any range predicates.

An index beginning with those equality fields may allow the database to navigate directly into the relevant subset and obtain results in useful order.

An index primarily ordered by rating may require examining hotels from many irrelevant cities or statuses.

The exact best ordering depends on selectivity, sorting requirements, and data distribution.

## Solution 3 — `$elemMatch`

Independent predicates on nested array fields may be satisfied by different array elements.

That doesn't establish that one room satisfies both requirements.

`$elemMatch` requires the conditions to hold for the same array element.

It can also allow more appropriate multikey index-bound behavior under suitable index structures.

## Solution 4 — Filter before grouping

If the query needs only Prague, filtering the input before grouping can dramatically reduce the aggregation work.

However, MongoDB may automatically push suitable filters earlier in the optimized pipeline.

Inspect the execution plan rather than assuming the written stage order is identical to physical execution.

## Solution 5 — Lookup costs

Without a suitable foreign index, the lookup can require much more work locating related documents.

Inspect the aggregation explain statistics, including relevant lookup execution information when available.

Consider indexing the foreign relationship key, restricting the input set before the lookup, limiting the related information retrieved, or maintaining an appropriate derived summary.

## Solution 6 — Sorting

A limit restricts the output count, not necessarily the number of candidates evaluated.

An index-supported sort can read entries in the required order and may stop once enough qualifying results are found.

A top-k optimization can reduce memory required to maintain the best candidates but may still need to inspect a large input.

A full sort may require retaining or spilling a much larger intermediate result.

The correct performance depends on the available ordering and query semantics.

## Solution 7 — Index maintenance

Indexes add costs to inserts, deletes, and updates affecting indexed fields.

Review query frequency, index usage, storage, write costs, and whether compound indexes already cover important prefixes.

Remove genuinely unused or redundant indexes carefully.

Reporting workloads may benefit from precomputed aggregates, a separate analytical store, or other architecture that doesn't impose unnecessary index-maintenance costs on operational writes.

## Solution 8 — Cursor pagination

A large offset requires skipping many preceding results, often increasing work as page numbers grow.

Cursor pagination uses the last returned ordering values to request the next range.

A unique tie-breaker makes ordering deterministic when several records share the same rating.

The trade-off is that sequential navigation becomes efficient, while arbitrary numbered page jumps are less convenient.

---

# 20. The Mental Model Worth Keeping

A database query describes the information an application wants.

The query engine must choose a physical strategy for producing that information.

**Indexes are access paths**, not universal accelerators.

Their usefulness depends on selectivity, key order, sorting requirements, projections, and the shape of the stored data.

**Compound indexes** organize information according to ordered combinations of fields.

**Multikey indexes** support arrays but introduce additional entries, restrictions, and semantic complications.

**Query planners** select execution strategies, but their decisions depend on the available structures and data distributions.

**Aggregation pipelines** transform documents, sometimes expanding or reducing enormous intermediate datasets.

**Blocking stages** such as sorting and grouping can consume substantial memory and storage resources.

And **every index carries a write and storage cost**.

The three most useful questions are:

1. How many candidates must the database examine?
2. Which physical access path lets it avoid unnecessary work?
3. Where does the query expand, sort, group, or fetch data beyond what the result actually requires?

The deepest principle is this:

**Query optimization is the art of avoiding work, not merely making individual operations faster.**

Once you understand that, execution plans stop being mysterious collections of operator names.

They become evidence about what the database is actually doing.

---

# 21. Next Lecture — Replication, Consistency, and Sharding in Practice

We've learned how document databases represent information and how their indexes and query engines retrieve it efficiently.

But so far, we've mostly imagined one logical database processing requests.

What happens when the database must survive a server failure?

Why can a write succeed on one node while another node still returns an older value?

What does it mean to acknowledge a write after a majority of replicas have accepted it?

And how do we distribute enormous collections across several machines without creating hotspots or losing the ability to reason about consistency?

In **CS340-L05 — Replication, Consistency, and Sharding in Practice**, we'll investigate those questions using MongoDB replica sets and sharded deployments as concrete examples.

We've made individual queries efficient.

Next, we'll make the data system survive the loss of machines—and discover why distributing data introduces an entirely new class of correctness problems.

---

# Optional Practical Lab — Investigating Query Execution

*The spoken lecture ends here. The remaining material is intended for terminal experiments, visual analysis, and interview preparation.*

## Lab A — Create a realistic sample collection

Use `mongosh` against a local development database.

This creates a small illustrative hotel dataset with varied cities, ratings, amenities, and room configurations.

```javascript
use cs340_lab

db.hotelSearch.drop()

const cities = ["Prague", "Vilnius", "Berlin", "Paris", "Warsaw"];
const amenities = ["wifi", "parking", "breakfast", "pool", "gym"];

const hotels = Array.from({ length: 20000 }, (_, i) => ({
  hotelId: `H-${i}`,
  city: cities[i % cities.length],
  active: i % 10 !== 0,
  rating: Math.round((2.5 + (i % 25) / 10) * 10) / 10,
  name: `Hotel ${i}`,
  amenities: amenities.filter((_, k) => (i + k) % 3 !== 0),
  rooms: [
    { capacity: 2, price: 120 + (i % 100) },
    { capacity: 4, price: 180 + (i % 200) }
  ]
}));

db.hotelSearch.insertMany(hotels);
```

This synthetic distribution is not representative of real hotel data. Its purpose is to make indexing behavior visible and reproducible.

## Lab B — Observe a collection scan

Run a query before creating an index on the relevant filter and sort fields.

```javascript
db.hotelSearch.find({
  city: "Prague",
  active: true,
  rating: { $gte: 4 }
})
.sort({ rating: -1 })
.limit(20)
.explain("executionStats")
```

Inspect `nReturned`, `totalKeysExamined`, and `totalDocsExamined`, along with the reported execution stages.

Record what work occurred before indexing.

## Lab C — Create a compound index

Create an index suitable for a common city-and-status search ordered by rating.

```javascript
db.hotelSearch.createIndex({
  city: 1,
  active: 1,
  rating: -1
})
```

Repeat the query from Lab B.

Compare examined keys, examined documents, returned results, and execution plan.

Does the index support the requested sort order?

Is the result as efficient as you expected?

## Lab D — Test index prefixes

Compare queries filtering by city, by active status, and by rating.

Inspect how the compound index is used for each query.

Then create a different index order in your development environment.

```javascript
db.hotelSearch.createIndex({
  rating: -1,
  city: 1,
  active: 1
})
```

Compare query plans using `hint()` where appropriate for controlled experiments.

Do not assume that the alternative index is automatically better merely because it includes the same fields.

Measure the work for representative query shapes.

## Lab E — Reproduce the array semantics trap

Create a small collection containing one hotel with two rooms:

```javascript
db.roomSearch.drop()

db.roomSearch.insertOne({
  _id: "HOTEL-A",
  rooms: [
    { capacity: 4, price: 300 },
    { capacity: 2, price: 120 }
  ]
})
```

The following query checks whether both conditions occur somewhere among the array values, not necessarily in the same room:

```javascript
db.roomSearch.find({
  "rooms.capacity": { $gte: 4 },
  "rooms.price": { $lt: 200 }
})
```

Compare with the correct same-element query:

```javascript
db.roomSearch.find({
  rooms: {
    $elemMatch: {
      capacity: { $gte: 4 },
      price: { $lt: 200 }
    }
  }
})
```

Explain why the results differ.

Then investigate how a suitable compound multikey index can support same-element queries.

## Lab F — Build an aggregation pipeline

Calculate the average rating for active hotels grouped by city.

```javascript
db.hotelSearch.aggregate([
  { $match: { active: true } },
  {
    $group: {
      _id: "$city",
      hotelCount: { $sum: 1 },
      averageRating: { $avg: "$rating" }
    }
  },
  { $sort: { averageRating: -1 } }
])
```

Now change the operation to concern only Prague.

Compare placing `$match` early with writing a logically equivalent pipeline that filters later.

Use aggregation `explain` to investigate what the optimizer actually executes.

## Lab G — Observe cardinality expansion

Unwind hotel amenities and count how frequently each occurs.

```javascript
db.hotelSearch.aggregate([
  { $match: { active: true } },
  { $unwind: "$amenities" },
  {
    $group: {
      _id: "$amenities",
      hotelCount: { $sum: 1 }
    }
  },
  { $sort: { hotelCount: -1 } }
])
```

Explain why the number of records processed after `$unwind` may exceed the number of original hotel documents.

How would limiting the source to one city change the workload?

## Lab H — Investigate covered queries and partial indexes

Create a compound index containing the filter fields and projected output fields.

Experiment with projections that include and exclude `_id`.

Use `explain("executionStats")` to determine whether documents must be fetched.

Then create a partial index covering active hotels:

```javascript
db.hotelSearch.createIndex(
  { city: 1, rating: -1 },
  { partialFilterExpression: { active: true } }
)
```

Compare queries that explicitly require `active: true` with queries that do not.

Explain why a query cannot safely use a partial index if doing so would omit permitted results.

## Lab I — Design a production investigation

Your MongoDB collection contains five million documents.

A query returns twenty results but examines hundreds of thousands of keys and documents.

Prepare a diagnosis covering:

1. Actual query shape and input parameters.
2. Available indexes.
3. Equality predicates, range predicates, and sort order.
4. Multikey behavior and array conditions.
5. Explain statistics and physical execution stages.
6. Expected write cost of adding an index.
7. Representative performance tests under concurrency.
8. Whether the workload belongs in MongoDB or a specialized search system.

The exercise is complete when you can explain why your proposed access path should reduce work—not merely when you have created another index.

---

## Further Reading — Optional Technical References

1. [MongoDB — Indexes](https://www.mongodb.com/docs/manual/indexes/) — Index structures and strategies.
2. [MongoDB — Equality, Sort, Range Guideline](https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/) — Compound-index key ordering.
3. [MongoDB — Multikey Indexes](https://www.mongodb.com/docs/manual/core/indexes/index-types/index-multikey/) — Array indexing and restrictions.
4. [MongoDB — Multikey Index Bounds](https://www.mongodb.com/docs/manual/core/indexes/index-types/index-multikey/multikey-index-bounds/) — Bounds and `$elemMatch`.
5. [MongoDB — Explain Results](https://www.mongodb.com/docs/manual/reference/explain-results/) — Execution plans and statistics.
6. [MongoDB — Aggregation Pipeline Optimization](https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/) — Optimizer transformations and index usage.
7. [MongoDB — Aggregation Pipeline Limits](https://www.mongodb.com/docs/manual/core/aggregation-pipeline-limits/) — Memory limits and disk spilling.
8. [MongoDB — Partial Indexes](https://www.mongodb.com/docs/manual/core/index-partial/) — Restricting index contents to selected documents.
9. [MongoDB — `$elemMatch`](https://www.mongodb.com/docs/manual/reference/operator/query/elemmatch/) — Matching conditions within the same array element.
10. [MongoDB — Write Performance](https://www.mongodb.com/docs/manual/core/write-performance/) — The cost of maintaining indexes.
11. [MongoDB — Query Optimization](https://www.mongodb.com/docs/manual/core/query-optimization/) — Query performance and access-path design.
12. Martin Kleppmann, *Designing Data-Intensive Applications* — Broader principles of indexing, storage, and physical query work.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for voice-reader skipping. Skim when revising; return to the full lecture only when a concept fails to spark recognition.*

```text
CS340-L04  INDEXES, QUERIES & AGGREGATION — INTERVIEW GLANCE CARD

CORE MODEL
  Query semantics   WHAT data the application wants
  Access path       HOW the engine locates candidates
  Optimizer         Chooses physical execution strategy
  Index             Additional sorted/searchable structure; not free
  Goal              MINIMIZE unnecessary work, not merely operator time

SELECTIVITY / CARDINALITY
  High selectivity  matches tiny fraction → useful for narrowing
  Low selectivity   matches most docs → may not justify index lookup
  Cardinality       distinct values (or estimated result count in planner talk)
  Important: actual value distribution > abstract field cardinality
  Collection scan can win for small / broad scans.

INDEXES
  Single-field     one ordered field
  Compound         ordered tuple of fields; ORDER MATTERS
  Prefix           {city, active, rating} useful for city;
                   city+active; city+active+rating
                   NOT equivalent to a rating-first index
  Asc/desc         sort compatibility matters for multi-field indexes
  Covered query    all required info available from index, avoids FETCH
                   often totalDocsExamined=0; _id projection can matter

ESR (EQUALITY / SORT / RANGE)
  Equality fields first.
  Sort next if avoiding sort is valuable (ESR).
  Highly selective range may precede sort (ERS) when that wins.
  Use EXPLAIN; no universal field-order recipe.

  Query: city="Prague", active=true, rating>=4
         ORDER BY popularity DESC, LIMIT 20
  Candidate:
    {city:1, active:1, popularity:-1, rating:1}
  Alternative:
    {city:1, active:1, rating:1, popularity:-1}
  Trade-off: ordered early termination vs narrowing by rating.

MULTIKEY / ARRAYS
  Index array field → multiple index entries per document.
  More array elements → potentially more index storage/work.
  Independent dotted predicates may match DIFFERENT elements.
  $elemMatch → SAME array element must satisfy all conditions.

  rooms=[{capacity:4,price:300},{capacity:2,price:120}]
  "rooms.capacity">=4 AND "rooms.price"<200
    may match document although NO room satisfies both.
  rooms:{$elemMatch:{capacity:{$gte:4},price:{$lt:200}}}
    correct same-room semantics.

  Compound multikey: no parallel indexed array fields
    within the same indexed document.
  Index-bound intersection/compounding may depend on $elemMatch.

INDEX TYPES
  B-tree-family   equality + ranges + ordered scans
  Partial         indexes only matching documents; query MUST imply filter
  TTL             background expiration; NOT precise business deadline
  Geospatial      spatial queries and proximity
  Text/Search     token relevance != ordinary B-tree string lookup

EXPLAIN — READ THESE FIRST
  nReturned          number of results
  totalKeysExamined  index entries examined
  totalDocsExamined  document examinations
  COLLSCAN           collection scan
  IXSCAN             index scan
  FETCH              read docs beyond index
  SORT               explicit sorting work
  20 returned + 800k examined = warning EVEN with IXSCAN.
  Explain may select plans without ordinary plan-cache reuse.
  Test actual latency, cache, concurrency, and parameter distribution.

AGGREGATION PIPELINE
  $match       filter
  $project     reshape/select/computed fields
  $group       aggregate by key
  $sort        order
  $limit       restrict output
  $unwind      array -> multiple intermediate documents
  $lookup      join-like cross-collection access
  $facet       multiple subpipelines on same input

  Rule: reduce input before expensive stages WHEN SEMANTICALLY SAFE.
  MongoDB optimizer can push/reorder stages; inspect real plan.
  Manual early $project is NOT universally faster.

BLOCKING / EXPANSION
  $group/$sort may require materializing large state.
  Top-k sort with limit may reduce memory, not candidate count.
  $unwind: 1M hotels * 20 amenities = ~20M intermediate records.
  $lookup without suitable foreign index can become extremely costly.
  Large $lookup arrays can violate document/memory constraints.

MEMORY & SPILLING
  Blocking stages may hit memory restrictions.
  allowDiskUse can enable temporary disk spill for supported stages.
  100 MB familiar stage threshold; exact behavior version/config-specific.
  Newer versions may impose additional per-operation limits.
  Spill = allows work to finish, NOT a free speed optimization.

PAGINATION
  skip(200000) + limit(20): may traverse huge prefix.
  Cursor/keyset: continue from last ordered key values.
  Include unique tie-breaker (_id) for deterministic order.
  Cursor efficient for sequential pages, less for arbitrary jumps.

INDEX COST / HYGIENE
  Inserts/deletes/update indexed fields require index maintenance.
  Indexes consume RAM, disk, I/O, build and operational cost.
  Review unused/redundant indexes; compound prefixes may overlap.
  Don't delete a shorter index blindly: size/workload may justify it.
  Reporting queries may belong in derived aggregates or analytics store.

PRODUCTION DIAGNOSIS
  1. Capture real query SHAPE + parameters + expected results.
  2. Inspect indexes; is filtering/sorting aligned?
  3. Explain: keys examined, docs examined, returned count.
  4. Look for SORT, FETCH, $unwind, $lookup, spill.
  5. Compare before/after on representative distributions.
  6. Measure read gain AND write/index maintenance penalty.
  7. Consider data model or specialized search if mismatch persists.

SENIOR LINE
  "An index is an access path, not a magic speed switch. I optimize
   for the actual query shape and distribution, inspect work performed
   with explain, and account for the costs on writes and operations."
```
