---
id: CS340-L01
course: CS340
title: "The Database That Didn't Fit Into Tables"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: null
next: CS340-L02
---






# CS340 — Data Systems Beyond Relational Databases

## Lecture 01: The Database That Didn't Fit Into Tables

*Why intelligent engineers keep inventing different kinds of databases, why none of them has replaced SQL, and how to recognize the right data architecture before choosing the technology.*

**Estimated study time:** 70–90 minutes, including the optional lab.

---

### How to listen to this lecture

Written for continuous listening first, then for on-screen re-reading. Theme: **choose data models by the questions and invariants you must protect**, not by collecting logos. Bold takeaways mark where a fashionable product would still be the wrong answer for the workload and guarantees you actually need.

Near the end, answer the oral challenges **out loud** before reading the solutions. The practical lab lives after the spoken lecture ends — keep it for a screen-and-terminal session.

---

# 1. The Company That Needed Six Databases

It's Monday morning, and you're the newly appointed technical lead of a rapidly growing travel platform.

Three years ago, the company was a small startup offering hotel reservations in a handful of European cities. Its architecture was refreshingly boring: a Node.js backend, a PostgreSQL database, and a Vue frontend.

Customers could search hotels, select rooms, create reservations, and pay.

The database contained tables for hotels, customers, room types, reservations, and payments. Foreign keys protected relationships. Transactions prevented double bookings. A few carefully chosen indexes made the important queries fast.

The system was simple, understandable, and remarkably reliable.

Then the company became successful.

Today, the platform lists hundreds of thousands of properties. Each property has its own characteristics. A small city apartment might have Wi-Fi, a kitchenette, and self-check-in instructions. A luxury resort might offer dozens of restaurants, swimming pools, spa services, complicated cancellation policies, and hundreds of room configurations.

The product team wants every property to expose its unique features without requiring a database migration whenever a new attribute appears.

Meanwhile, customers demand sophisticated search.

They want to find *a quiet hotel near the old town with a balcony, free parking, good breakfast, and a flexible cancellation policy*.

The existing search feature relies on SQL filters and a few text comparisons. It works, but the product team wants typo tolerance, relevance ranking, synonyms, multilingual search, and perhaps eventually semantic search.

Then marketing introduces another requirement.

The company needs to understand user behavior across millions of browsing sessions. Which search filters produce bookings? Which destinations attract attention but rarely convert? Which suppliers experience declining conversion rates? Which campaigns generate revenue?

The operational database is already busy processing reservations. Large analytical queries are beginning to compete with customer-facing transactions.

Security introduces a fourth problem.

The company wants to detect suspicious relationships between accounts, payment methods, devices, and reservations. Fraudulent customers sometimes create multiple identities while reusing the same devices or payment details.

The investigations involve traversing networks of relationships, sometimes several connections deep.

Finally, the infrastructure team wants reliable session storage, distributed rate limiting, and extremely fast access to frequently requested data.

At the next architecture meeting, six engineers make six proposals.

One wants to keep everything in PostgreSQL.

Another proposes MongoDB because the hotel attributes are flexible.

A third wants Elasticsearch for search.

Someone suggests Redis for performance.

Another recommends a graph database for fraud detection.

The analytics engineer wants a column-oriented database.

The CTO looks at the whiteboard, sees six database logos, and asks a reasonable question.

"Are we building a hotel-booking platform or collecting databases?"

You have to make the architectural decision.

The naive solution is to choose the database with the most impressive benchmarks.

The slightly more sophisticated solution is to choose whatever technology currently dominates engineering conference presentations.

The correct solution begins somewhere else entirely.

**What kinds of work does our data system actually need to perform, and which guarantees must survive when things go wrong?**

That's the question driving this course.

---

# 2. A Database Is More Than a Place to Store Information

Let's begin with a deceptively simple definition.

A database stores information and allows applications to retrieve or modify it.

Technically correct. Educationally almost useless.

A text file can store information.

A JavaScript object can store information.

A folder full of JSON documents can store information.

Why do we need database systems?

Because storing information is the easy part. Maintaining useful, correct, efficiently accessible information while many operations happen concurrently is considerably harder.

Imagine our travel platform accepts a reservation.

It must record the customer's identity, the selected property, the room, the dates, the agreed price, and the current status.

Later, the customer might change the reservation.

A payment provider might send a confirmation.

An administrator might issue a refund.

Another service might need to generate an invoice.

The information must survive process restarts and hardware failures. Concurrent updates must not violate important business rules. Queries must remain acceptably fast as data grows.

These are distinct problems.

A database system makes engineering choices about how to solve them.

## 2.1 The responsibilities competing inside every database

Consider five fundamental concerns.

**Data modeling** determines how information is represented and related. Are we storing rows, documents, key-value pairs, graph relationships, or something else?

**Access** determines how efficiently we can answer questions. Finding one customer by ID is fundamentally different from scanning a billion events to calculate conversion rates.

**Consistency and transactions** determine which observations and updates are allowed when operations happen concurrently or data is replicated.

**Durability and recovery** determine what survives crashes, restarts, corruption, and infrastructure failures.

**Scalability and operation** determine how the system behaves as data, traffic, and infrastructure complexity grow.

Every mature database must address these concerns in some form.

But databases prioritize them differently.

Some are optimized for small, frequent transactions.

Some are designed around predictable key-based access.

Some invest heavily in full-text indexing and relevance ranking.

Others reorganize enormous datasets so analytical calculations can scan only the information they need.

The resulting systems may all call themselves databases, yet expose dramatically different abstractions.

## 2.2 There is no universal winner

Imagine asking which vehicle is best.

A bicycle, a cargo ship, a high-speed train, and a helicopter all transport things.

Comparing them without specifying the journey is absurd.

Database comparisons can suffer from the same problem.

A benchmark showing one system handling enormous numbers of simple key-value lookups tells us little about its suitability for complex financial transactions.

A database performing exceptionally well at full-text search might be an awkward choice for enforcing relational integrity across reservations and payments.

And a powerful analytical engine might be terribly inefficient for thousands of small concurrent updates.

The question isn't which database is fastest.

It's **fastest at what, under which constraints, while preserving which guarantees?**

This is the first mental model worth carrying through the course.

---

# 3. The Relational Model: Why PostgreSQL Isn't Going Anywhere

Before investigating alternatives, we should resist a popular temptation.

The title of this course is *Data Systems Beyond Relational Databases*.

That does not mean relational databases are obsolete.

Quite the opposite.

A mature relational database remains one of the strongest general-purpose foundations available for application development.

And PostgreSQL, in particular, can handle a much wider variety of workloads than developers sometimes assume.

Let's recall why relational databases became so successful.

## 3.1 Data has relationships, whether we acknowledge them or not

Imagine the booking platform's central business model.

A customer creates a reservation.

The reservation concerns a property and a room type.

It contains a price agreement.

A payment may be authorized, captured, or refunded.

These entities are related.

The relationships carry important rules.

A payment must belong to a valid business operation. A reservation must not reference a nonexistent property. A room cannot be sold beyond the available inventory according to the system's booking rules.

The relational model gives us a disciplined way to represent data through relations, keys, constraints, and operations over those relations.

SQL lets us express queries declaratively.

The database query planner decides how to execute them.

Transactions provide a mechanism for grouping operations while enforcing appropriate consistency requirements.

That combination is extremely powerful.

A relational database doesn't simply store records. It helps enforce a coherent model of the world.

## 3.2 The relational model is not inherently inflexible

Consider our hotel's flexible amenities.

One developer argues that PostgreSQL cannot store varying attributes without adding columns constantly.

But PostgreSQL supports structured JSON data, including the `jsonb` type.

We might store stable hotel identity and relationships relationally while keeping certain variable property attributes inside a JSONB column.

PostgreSQL can query and index JSONB content.

That doesn't make every document-oriented design automatically equivalent to a dedicated document database, but it invalidates the simplistic claim that relational databases cannot handle flexible data.

Likewise, PostgreSQL supports full-text search, arrays, specialized indexes, and extensions that expand its capabilities.

Graph relationships can be represented through tables and traversed using recursive queries.

Analytical queries can be written in SQL.

The real question isn't whether PostgreSQL can express an operation.

It's whether it can support the required workload efficiently, correctly, and economically at the scale and complexity we actually face.

## 3.3 PostgreSQL as a default, not a religion

Suppose our startup currently has ten developers and a modest amount of traffic.

Introducing five specialized databases would create five systems to deploy, secure, monitor, back up, upgrade, and understand.

The company would also need to synchronize information between them.

That's a serious engineering cost.

If PostgreSQL can meet the requirements comfortably, keeping the architecture simple is often the stronger decision.

But imagine that product search eventually demands sophisticated multilingual relevance ranking across millions of descriptions.

Or analytics begins scanning enormous volumes of events continuously.

At that point, specialized systems may provide advantages significant enough to justify their complexity.

The mature position is neither "PostgreSQL for everything" nor "use the best specialized database for every feature."

It's this:

**Start with a coherent system of record. Introduce specialization when a measured workload or clear requirement justifies it.**

Now let's meet the alternatives.

---

# 4. Document Databases: When an Entity Is More Naturally a Document

Our first candidate is MongoDB.

Imagine the hotel's product catalogue.

One property has three amenities.

Another has thirty.

Some properties expose detailed accessibility information. Others provide complex dining options, multilingual descriptions, room layouts, or seasonal services.

The data is naturally hierarchical.

A hotel contains descriptive attributes, and some of those attributes contain nested structures.

We could model everything relationally.

But what if the most common operation is simply fetching a complete hotel description?

A document-oriented model becomes attractive.

## 4.1 The document as a unit of organization

A document database such as MongoDB stores records as documents.

MongoDB uses BSON, a binary representation supporting structured values such as strings, numbers, arrays, and nested documents.

Imagine one property document containing its name, location, descriptions, amenities, and room-summary information.

When the application requests that property, much of the relevant information may already live together.

This is the intuition behind **document-oriented modeling**.

Data frequently accessed together can often be represented together.

Instead of reconstructing a complex object through several relational joins, an application may retrieve one document containing the desired structure.

That can make certain reads convenient and efficient.

But don't jump to the conclusion that documents are universally superior to joins.

The convenience creates trade-offs.

## 4.2 Embedding versus referencing

Suppose a hotel has several restaurant facilities.

Should their details be embedded inside the hotel document?

Perhaps.

If these restaurants are always displayed as part of the hotel's profile, rarely updated independently, and bounded in number, embedding may be sensible.

Now consider customer reviews.

A hotel might eventually receive hundreds of thousands of reviews.

Should all reviews be stored inside one enormous hotel document?

Probably not.

The collection grows independently, different queries need different subsets, and many operations concern individual reviews.

References or separate documents are likely more appropriate.

Similarly, imagine embedding the current customer profile inside every reservation.

If the customer updates their phone number, do we update thousands of historical reservation documents?

Perhaps the reservation actually needs a historical snapshot of contact information at booking time.

Or perhaps it should reference the customer's current profile.

Those are different business semantics.

The correct modeling decision depends on ownership, update behavior, growth, and the queries that matter.

**Embedding and referencing aren't formatting preferences. They decide which information shares a lifecycle.**

## 4.3 The atomicity boundary

Here's where document modeling becomes especially interesting.

MongoDB supports atomic updates to individual documents.

If several related fields reside inside one document, an appropriate update operation can change them together atomically.

This can be extremely useful when those fields form one coherent business unit.

But what if an operation must modify several independent documents?

Now we're dealing with a wider transaction boundary.

Modern MongoDB supports multidocument transactions under appropriate deployment configurations, so the statement "MongoDB has no transactions" is false.

However, transaction capabilities don't eliminate the importance of data-model boundaries.

If every routine business operation requires coordinating many independently stored documents, we should examine whether our model reflects how the application actually works.

The same architectural question exists in relational databases, but document systems encourage us to think particularly carefully about aggregation boundaries.

## 4.4 Flexible schema does not mean optional correctness

A document database can allow documents in the same collection to have different fields and structures.

This is useful for evolving products.

But there's a trap.

If one document stores `price` as a number, another as a string, and a third omits the field entirely, the application still has to interpret those differences.

Schema flexibility moves some responsibilities away from rigid table definitions.

It doesn't abolish schema requirements.

MongoDB supports schema validation, and applications should still define and enforce meaningful contracts.

Otherwise, the database becomes a collection of historical accidents that every reader must accommodate.

The valuable property isn't the absence of structure.

It's the ability to choose appropriate structure and evolve it deliberately.

We'll examine this entire subject in CS340-L03.

---

# 5. Key-Value Systems: What If We Already Know What We're Looking For?

Now imagine a different problem.

Every incoming API request carries a session identifier.

The backend must retrieve a small amount of session information quickly.

It already knows the exact key.

There is no complicated query.

No search ranking.

No need to join seven entities.

We want to associate a key with a value and retrieve that value efficiently.

This is the natural territory of **key-value systems**.

## 5.1 The beauty of an intentionally narrow interface

A simple key-value store provides an abstraction resembling a dictionary.

Store a value under a key.

Retrieve the value for a key.

Update or remove it.

A real implementation may provide many more capabilities, but the central access pattern remains direct key-based access.

This narrower interface can be valuable.

When the system is optimized around known lookup keys, it can avoid much of the complexity associated with supporting arbitrary relational queries.

But that specialization cuts both ways.

Suppose we store bookings under keys derived from reservation IDs.

Finding one reservation by ID may be straightforward.

Now ask for every reservation made by customers in Lithuania last month where the amount exceeded 500 euros.

Unless our data model includes suitable secondary access paths or another query mechanism, this request may become expensive or awkward.

The database hasn't failed.

We asked it to perform work that its chosen access structure wasn't designed to support efficiently.

## 5.2 Redis: More than a cache, less than a universal database

Redis is often introduced as an in-memory key-value cache.

That's a useful starting point, but Redis supports a variety of data structures, including strings, hashes, sets, sorted sets, lists, and streams, along with additional capabilities depending on its version and deployed components.

A simple cache might store a serialized hotel summary under a key.

A sorted set might support a leaderboard or priority-like access pattern.

A counter might help implement one component of a rate-limiting mechanism.

These structures are useful because the operations match familiar application needs.

But using Redis introduces architectural questions.

Is it storing authoritative business data or a disposable derived copy?

What happens when an entry expires?

What happens if the Redis instance becomes unavailable?

Does the chosen persistence and replication configuration satisfy the required durability guarantees?

If we use Redis for sessions, how will authentication behave during a Redis outage?

The word *fast* answers none of these questions.

## 5.3 DynamoDB: Key-value thinking at distributed scale

Now consider Amazon DynamoDB.

DynamoDB is a managed NoSQL system supporting item-based storage and primary-key access.

Its data model is heavily influenced by access patterns and key design.

A primary key can consist of a partition key alone or a partition key combined with a sort key.

The partition key helps determine how data is distributed.

The sort key provides ordering and range-query capabilities among items sharing a partition-key value.

This can make certain queries efficient and predictable.

But a poor partition-key choice can concentrate traffic on a limited portion of the available infrastructure.

Imagine assigning all reservations made on the current day to one partition-key value.

That value may receive enormous traffic while other partition-key values remain nearly idle.

The application has unintentionally created a hotspot.

Distributed infrastructure cannot automatically rescue every badly chosen data-access pattern.

DynamoDB supports secondary indexes and additional query capabilities, but effective modeling begins by understanding which lookups and ranges the application actually requires.

This is a crucial contrast with the broad ad hoc querying flexibility of relational databases.

**Some systems reward you for deciding how data will be queried before you decide how to store it.**

We'll return to partition keys, indexes, and hotspots later in the course.

---

# 6. Search Engines: Finding Information Isn't the Same as Looking Up Records

Now return to the product team's request.

Customers want to search for hotels using natural descriptions.

A user types:

"Quiet apartment near old town with parking."

The database contains thousands of properties with descriptions in several languages.

What should the system return?

Perhaps the user doesn't know the exact words used in the listings.

Perhaps the spelling is imperfect.

Perhaps one property uses the phrase "historic center" instead of "old town."

Perhaps a listing contains every requested word but is otherwise a poor match.

This is not simply an equality lookup.

It is an **information retrieval problem**.

## 6.1 From exact matching to relevance

Ordinary database queries often ask whether records satisfy particular conditions.

Hotel price below 150 euros.

City equals Prague.

Parking available.

These are structured predicates.

Full-text search introduces another dimension: relevance.

We want to identify documents containing useful information related to a query and rank them according to some scoring model.

The result isn't always a simple yes-or-no answer.

Two hotels might both match, but one is clearly more relevant.

Search systems invest considerable engineering effort in indexing text, analyzing language, retrieving candidates, and ranking results.

## 6.2 The inverted index

A central search-engine data structure is the **inverted index**.

Imagine three hotel descriptions.

The first contains "quiet apartment with balcony."

The second contains "luxury hotel with balcony."

The third contains "quiet countryside retreat."

Instead of storing only documents and searching every description from beginning to end, the system builds mappings from terms to the documents containing them.

The term *quiet* points toward the first and third documents.

The term *balcony* points toward the first and second.

The query engine can use these mappings to identify candidates efficiently.

Real search engines do much more.

They may tokenize text, normalize case, handle linguistic forms, maintain positional information, calculate relevance scores, and apply additional filters.

Elasticsearch and OpenSearch are examples of systems designed for these kinds of workloads.

But search indexes introduce another challenge.

## 6.3 The search index is usually not the authority on reality

Suppose a hotel changes its description.

The application updates the operational database.

An indexing pipeline then updates the search engine.

For some period, the search index might contain the previous representation.

This is a synchronization problem.

Now imagine a much more dangerous version.

The search index indicates that a room is available.

The customer attempts to book it.

Meanwhile, another customer has reserved the last room.

Should the search engine decide whether the new reservation succeeds?

No.

Search results can help users discover candidate products.

The authoritative booking operation must enforce inventory correctness through an appropriate transactional system.

This distinction is essential.

Search is often a **derived view** optimized for discovery.

The operational database remains responsible for the relevant business invariants.

And the derived view needs a reliable update mechanism, monitoring, and reconciliation strategy.

We'll investigate these relationships in detail later.

---

# 7. Graph Databases: When Relationships Become the Main Question

The security team now approaches us with an unusual request.

Several customer accounts appear unrelated.

They use different names and email addresses.

But the fraud team suspects that the accounts belong to one coordinated operation.

Some share payment instruments.

Others share devices.

Still others booked hotels using referral links associated with the same group of accounts.

The question isn't simply which records match a filter.

It's how records connect through networks of relationships.

That brings us to **graph databases**.

## 7.1 Nodes and edges

A graph represents entities as nodes and relationships as edges.

For example, a customer can be connected to a device through a relationship meaning "used this device."

A device may be associated with several customers.

A customer may be connected to a payment instrument.

That payment instrument may be shared with another customer.

Now imagine asking:

"Find all accounts connected to this suspicious account through at most three relationships involving devices or payment instruments."

The relationships themselves have become central to the query.

A graph database such as Neo4j provides a model and query language designed around traversing these relationships.

Instead of thinking only about tables and joins, we express patterns through connected entities.

## 7.2 Why not just use SQL?

We absolutely can represent graphs in relational databases.

A table of entities and a table of relationships can describe a graph.

SQL supports joins and recursive queries.

For many applications, that's more than sufficient.

A dedicated graph database becomes attractive when graph traversal is central to the workload and its model, query capabilities, and performance characteristics provide meaningful advantages.

But don't assume graph queries are automatically cheap.

A highly connected node can produce enormous numbers of candidate paths.

The cost depends on graph topology, traversal depth, constraints, indexes, and the specific implementation.

Graph databases make relationship-oriented modeling and querying natural.

They do not make combinatorial complexity disappear.

## 7.3 Is fraud detection automatically a graph-database problem?

Not necessarily.

If fraud detection only requires finding accounts that share a payment token, a conventional indexed database query might be sufficient.

But if investigators repeatedly explore multi-hop relationships, shared devices, referral networks, and unusual connection patterns, the graph model may become increasingly valuable.

Once again, the technology should follow the dominant access patterns.

Not the other way around.

---

# 8. Analytical Databases: Asking Questions About Millions of Events

Our final major requirement comes from the analytics team.

They want to examine user behavior across hundreds of millions of events.

Every search, filter selection, property view, booking attempt, and completed reservation contributes information.

The team wants to calculate conversion rates by country, marketing channel, device type, time period, and product category.

Some queries scan enormous datasets.

This differs fundamentally from retrieving one reservation by ID.

## 8.1 Transactional versus analytical workloads

Operational databases are often optimized for **online transaction processing**, or OLTP.

These systems handle many relatively small operations, including point lookups, inserts, updates, and transactions.

Analytical systems focus on **online analytical processing**, or OLAP.

Their workloads often involve scanning large datasets, filtering records, grouping results, and calculating aggregates.

Imagine a table containing one hundred million events.

Each event includes dozens of attributes.

An analyst asks:

"What was the conversion rate by country and device type during the last thirty days?"

The query may need only a few columns: timestamp, country, device type, and event category.

Yet a traditional row-oriented storage layout organizes much of each record's data together.

That can be excellent for retrieving complete individual records, but less convenient when processing a small subset of columns across millions of rows.

## 8.2 Column-oriented storage

A column-oriented database stores values by column or column-oriented blocks rather than simply keeping whole rows together.

That can allow queries to read only the columns they require.

It also creates opportunities for efficient compression, because values within one column often have similar types and distributions.

For example, a country column might contain a relatively small set of repeated country codes.

An analytical engine can exploit that structure.

Systems such as ClickHouse are designed around column-oriented analytical processing.

Other analytical platforms use related techniques, although their execution models, storage formats, and architectures differ.

The advantage is not that columns are universally better than rows.

It is that the physical data layout and execution strategy match analytical queries.

## 8.3 Why not run analytics directly on PostgreSQL?

Sometimes you should.

For modest datasets, a few well-designed SQL queries, indexes, and perhaps materialized views may provide everything a company needs.

Introducing a separate analytical system can be unnecessary.

But suppose the event volume grows enormously.

Heavy analytical queries now compete with reservation transactions for CPU, memory, storage I/O, and other database resources.

The company may benefit from separating operational workloads from analytical workloads.

This might involve replication, data pipelines, event ingestion, or a dedicated analytical store.

However, the second system introduces another source of uncertainty.

When the operational database changes, how quickly does the analytical system learn about it?

What happens if the ingestion pipeline stops?

How are duplicates handled?

Can historical data be corrected?

What happens when event schemas evolve?

Analytics frequently tolerates some delay that a payment system cannot.

That difference makes the separation feasible.

But the company must define how fresh the analytical results need to be and how their correctness is established.

---

# 9. The Labels Are Messier Than the Marketing Suggests

We've now examined relational, document, key-value, search, graph, and analytical systems.

At this point, somebody usually asks:

"So which ones are NoSQL?"

It's a reasonable question, but we should be careful.

The term **NoSQL** historically grouped many systems that did not fit the conventional relational database model.

Today, it is often interpreted as "not only SQL."

That definition is broad enough to include technologies with radically different data models, interfaces, and consistency behavior.

But the distinction is increasingly blurry.

PostgreSQL supports JSON documents and full-text search.

MongoDB supports complex aggregations and multidocument transactions.

DynamoDB supports more than simple key-value reads.

Redis supports multiple structured data types.

Some search engines support vector search.

Analytical databases may use SQL while maintaining very different physical storage designs from traditional operational databases.

The product categories overlap.

And the SQL language itself is not synonymous with one physical storage architecture.

## 9.1 Two independent questions

It helps to separate two dimensions.

The first is the **logical data model and interface**.

What entities does the system expose? Which operations can applications express? How are relationships represented?

The second is the **physical and distributed architecture**.

How is information stored and indexed? How are writes made durable? How is data replicated or partitioned? How does the system recover from failure?

Two databases might expose similar document interfaces while using different storage engines.

Two systems might both support SQL while making very different decisions about physical data organization.

And one database might provide multiple indexing and querying mechanisms within the same product.

The simple labels are useful for orientation.

They aren't sufficient for architecture decisions.

## 9.2 Consistency is not determined by the database category

There's another misconception worth eliminating.

Relational databases are often described as strongly consistent, while NoSQL databases are described as eventually consistent.

That is too crude to be reliable.

Actual guarantees depend on the database, the operation, the replication architecture, transaction isolation, and chosen read and write settings.

A relational system using asynchronous replicas can expose stale reads from those replicas.

A non-relational system may support strongly consistent reads or transactional operations within specified boundaries.

Different deployments of the same database can expose different behaviors.

If correctness matters, don't ask merely whether the product is SQL or NoSQL.

Ask which guarantee the specific operation needs and which configuration actually provides it.

---

# 10. The Real Architectural Question: What Must Never Be Wrong?

We're almost ready to make decisions about our travel platform.

But there's one dimension that deserves special attention.

Some information can tolerate approximation or temporary staleness.

Other information cannot.

Imagine a search page displaying a hotel that was available thirty seconds ago.

Perhaps that's acceptable, provided the final booking operation checks authoritative inventory.

Now imagine the database permanently recording two successful sales of the same last room.

That is a different class of failure.

Imagine an analytics dashboard whose figures are ten minutes behind real time.

Depending on the product, that might be perfectly fine.

Now imagine a payment ledger losing the record of a captured transaction.

That's unacceptable.

These scenarios reveal that data systems should be chosen according to more than query speed.

They must satisfy the business's correctness requirements.

## 10.1 Identify the source of truth

For every important business fact, determine which system is authoritative.

Where is a reservation created?

Which system determines whether a room can be sold?

Where is a payment's final recorded state maintained?

Which system owns the current customer profile?

A cache can contain copies.

A search index can contain derived representations.

An analytical database can contain historical or replicated data.

But the architecture must define which system makes authoritative decisions when copies disagree.

Without clear ownership, the company can develop contradictory versions of reality.

## 10.2 Derived data creates synchronization obligations

Suppose our operational database stores the authoritative hotel record.

A search engine maintains an indexed representation.

An analytical system stores events and aggregated measurements.

A cache stores frequently requested summaries.

Now one hotel changes its name.

Which systems need updating?

How are updates delivered?

What happens if the search-index update fails?

What happens if a consumer receives the same update twice?

What happens if an old update arrives after a newer one?

These are distributed-systems questions, not merely database questions.

A common strategy is to publish changes through a reliable mechanism, sometimes using a transactional outbox or change-data-capture system.

But those mechanisms introduce their own operational responsibilities.

Every additional data representation creates synchronization and recovery work.

This is why adopting a new database has a cost much larger than its hosting bill.

## 10.3 The hidden price of multiple databases

A specialized system might make one feature dramatically faster.

But operating it requires monitoring, backups or recovery mechanisms appropriate to its role, access controls, upgrades, capacity planning, incident response, and developer expertise.

The team must also maintain data pipelines and establish failure-handling behavior when systems disagree.

An architectural improvement is real only when its benefits outweigh those costs.

At small scale, one versatile database is often a better solution than a collection of specialized systems.

At larger scale, specialization may become justified.

The transition should be driven by requirements, evidence, and measured trade-offs.

Not fashion.

---

# 11. The Architecture Meeting: Our Decision

Let's return to the whiteboard.

The CTO wants to know how many databases we're actually going to introduce.

Our answer should begin with the existing system.

PostgreSQL already handles reservations, customers, payments, and other authoritative business records.

It supports the transactional requirements the platform depends on.

There is no compelling reason to replace it merely because new database technologies exist.

So PostgreSQL remains our primary system of record.

Next, we examine hotel metadata.

Its structure is flexible and hierarchical.

MongoDB might be a natural fit, especially if the catalogue is operated as a separate bounded subsystem with suitable document ownership and query patterns.

But PostgreSQL JSONB might also handle the requirement effectively.

We should compare the actual document sizes, queries, update patterns, indexing requirements, and operational costs before introducing another system.

For full-text search, we initially assess PostgreSQL's capabilities.

If the product requires more sophisticated linguistic analysis, relevance ranking, typo tolerance, and high-scale search features, a specialized search engine becomes a stronger candidate.

But the search index should remain a derived view, not the ultimate authority for booking inventory.

For sessions and selected high-frequency lookups, Redis may offer useful data structures and low-latency access.

Yet we should define whether those values are disposable, reconstructable, or business-critical.

For fraud investigations, we begin by evaluating the actual relationship queries.

If simple indexed joins are enough, introducing a graph database adds little value.

If complex multi-hop traversals become central to the investigation workload, a graph-oriented system may be justified.

For analytics, we separate analytical requirements from operational requirements.

At modest volume, PostgreSQL may still be sufficient.

As event volume and query intensity grow, a column-oriented analytical system could provide substantial benefits while reducing interference with transactional workloads.

Finally, we define data ownership, synchronization mechanisms, failure behavior, and monitoring before declaring the architecture complete.

## 11.1 The recommendation is deliberately boring

For the immediate future, I'd keep PostgreSQL as the authoritative operational store.

I'd introduce Redis only where a concrete access pattern benefits from it.

I'd evaluate specialized search and analytics systems against actual requirements and measurements.

And I'd resist adding separate document or graph databases until their advantages clearly justify another operational boundary.

This isn't an argument against specialized databases.

It is an argument for **earning complexity**.

We shouldn't optimize architecture for the possibility that every fashionable product might become useful.

We should design for actual responsibilities, known constraints, and changes that are reasonably likely.

The company needs a coherent data architecture.

It doesn't need a database zoo.

---

# 12. A Practical Framework for Choosing Data Systems

Now let's extract a reusable method from the case.

When evaluating a data system, start with five questions.

**First: What are the dominant access patterns?**

Are we retrieving individual records by key? Traversing relationships? Searching text? Scanning enormous event histories? Performing small transactional updates?

**Second: What must be correct together?**

Which information forms one business invariant? What requires atomic changes? Which observations must reflect committed writes immediately, and which can tolerate staleness?

**Third: What are the growth and performance constraints?**

How much data exists? How quickly does it grow? What are the read/write ratios? What latency and throughput objectives matter? Are there hotspots or unusually expensive queries?

**Fourth: What happens when something fails?**

Can we reconstruct the data? Are backups sufficient? Is replication available? What happens if a node disappears or a pipeline falls behind? Which failures are acceptable, and which violate the business contract?

**Fifth: What does operating this system cost?**

Consider infrastructure, complexity, team familiarity, migrations, observability, backups, security, and the possibility of eventually replacing it.

These questions transfer across vendors.

They also give you a useful way to discuss unfamiliar products in interviews.

If someone asks whether DynamoDB would be a good choice for a particular workload, you don't need to remember every AWS API method.

You can ask about access patterns, partition-key distribution, transaction requirements, consistency, and scaling expectations.

That tells the interviewer you understand the problem the technology is designed to solve.

And if you don't know the exact provider guarantees, saying which ones you would verify is a strong engineering answer.

---

# 13. The Oral Examination

Before reading the solutions, answer these questions aloud.

Try explaining the reasoning as though you were interviewing for a senior engineering position.

### Challenge 1 — The MongoDB proposal

Your team stores hotel metadata in PostgreSQL.

One developer proposes moving it to MongoDB because different hotels have different attributes.

Would you approve the migration?

What information would you need before deciding?

### Challenge 2 — The document that grew forever

A developer stores each hotel and all of its customer reviews inside one MongoDB document.

The application works initially.

A popular hotel eventually accumulates hundreds of thousands of reviews.

What problems might appear?

How would you reconsider the data model?

### Challenge 3 — The DynamoDB hotspot

An application stores millions of events in DynamoDB.

Every event created on the same day receives the same partition-key value.

The system experiences throttling despite having substantial overall capacity.

What mechanism could explain this?

How might key design improve the situation?

### Challenge 4 — The search index disagreement

A customer sees an available room in a search result.

They select it, but the booking API reports that it is sold out.

Is this necessarily a bug?

Which system should make the final inventory decision?

### Challenge 5 — The analytical query

A business analyst regularly scans 500 million events to calculate conversion rates by country, device type, and campaign.

These queries interfere with the application's operational database.

What architectural options would you consider?

Why might a column-oriented system help?

### Challenge 6 — The graph-database temptation

A team wants to detect accounts sharing payment instruments.

Someone recommends Neo4j.

Would you immediately approve?

What kinds of queries would make a graph database significantly more attractive?

### Challenge 7 — The consistency misconception

An interviewer says:

"Relational databases are strongly consistent, while NoSQL databases are eventually consistent."

How would you respond?

What would you investigate before relying on a particular database's guarantees?

---

# 14. Solutions and Discussion

*Read this section after answering out loud. The practical lab appears after the spoken lecture ends.*

### Solution 1 — MongoDB migration

The presence of variable attributes is not sufficient reason to migrate.

PostgreSQL supports JSONB and other flexible modeling techniques.

We should examine document structure, query patterns, write behavior, indexing, growth, transactional requirements, and operational complexity.

MongoDB becomes attractive if its document model and related capabilities provide meaningful advantages for the actual workload.

The decision should compare concrete alternatives rather than assume flexibility requires one particular product.

### Solution 2 — Unbounded embedded reviews

An unbounded review collection can make the parent document grow excessively large.

MongoDB documents have size limits, and repeatedly modifying or retrieving a huge embedded collection can create performance and modeling problems.

Reviews also have their own lifecycle and query requirements.

A separate review collection referencing the hotel is likely more appropriate.

The hotel document might embed a bounded summary, such as review counts or selected recent reviews, if those values can be maintained correctly.

### Solution 3 — Hot partition

A partition key with extremely concentrated activity can create a hotspot.

Even if total table capacity is substantial, access concentrated on particular partition-key values can encounter local throughput constraints.

A better design distributes workload more effectively, perhaps using more granular or appropriately sharded keys while preserving the queries the application needs.

The correct approach depends on the actual access patterns, consistency requirements, and key distribution.

### Solution 4 — Stale search result

A search index may contain a slightly stale representation of inventory.

That can be acceptable if the product explicitly tolerates preliminary availability information that must be validated before booking.

The authoritative booking system should enforce inventory correctness.

The product should handle stale results gracefully rather than assuming a search hit guarantees reservation success.

### Solution 5 — Analytical workload

Options include optimizing existing queries, using materialized views or precomputed aggregates, moving heavy reads to suitable replicas, or introducing a dedicated analytical system.

Column-oriented storage can reduce unnecessary data reads for queries examining a few columns across enormous datasets.

A separate analytical system also introduces ingestion, freshness, duplication, correction, and operational concerns.

The architecture should balance workload isolation against those costs.

### Solution 6 — Graph database

Finding accounts that share payment instruments may be straightforward with indexed relational queries.

A graph system becomes more attractive if the dominant workload involves repeated, complex, variable-depth traversal through networks of related entities.

The decision depends on graph structure, query frequency, traversal complexity, volume, and operational requirements.

A graph-shaped problem does not automatically require a graph database.

### Solution 7 — Consistency

The claim is an oversimplification.

Different relational and non-relational systems provide different guarantees.

Replication configuration, transaction isolation, read preferences, and write acknowledgment policies can change observable behavior.

We should specify the exact operation and required guarantee, then verify the database's documented behavior under the intended configuration.

A product category is not a consistency contract.

---

# 15. The Mental Model Worth Keeping

Different data systems exist because different workloads reward different abstractions and physical designs.

A **relational database** provides a powerful general-purpose model for structured relationships, constraints, and transactions.

A **document database** emphasizes grouped, often hierarchical records whose structure can evolve according to application needs.

A **key-value system** makes known-key access and selected data-structure operations particularly natural.

A **search engine** organizes information for retrieval and relevance rather than merely exact record lookup.

A **graph database** treats relationships and traversals as central elements of its model.

An **analytical database** optimizes large-scale aggregation and scanning workloads, frequently through column-oriented storage.

These categories overlap, and the technology labels are less important than the underlying mechanisms.

The central principle is:

**Choose data systems according to access patterns, correctness requirements, failure behavior, and operational costs—not according to what happens to be fashionable.**

Start with a coherent source of truth.

Allow specialized representations when they earn their complexity.

And remember that every additional database creates another system whose state, availability, and synchronization you must understand.

The goal is not to collect technologies.

It is to know which engineering problems they solve.

---

# 16. Next Lecture — Inside a Storage Engine

We've examined databases from the application's perspective.

We now understand why different data models and workloads encourage different technologies.

But what actually happens when an application writes a record?

Does the database immediately place the information into its final location on disk?

How can a system acknowledge a write before every data page has been rewritten?

Why do some storage engines use B-trees while others favor log-structured merge trees?

What is a write-ahead log, and why can a database recover committed operations after a crash?

In **CS340-L02 — Inside a Storage Engine**, we'll open the machinery beneath the database interface.

The application sees records, documents, and queries.

We're going to investigate pages, logs, indexes, caches, compaction, and the engineering trade-offs that make some databases fast at one kind of work and painfully inefficient at another.

The database is no longer a black box.

---

## Optional Practical Lab — Compare the Data Models

*The spoken lecture ends here. The remaining exercises are intended for visual study, hands-on experimentation, and later revision.*

## Lab A — Model one hotel in PostgreSQL and MongoDB

Consider a property with these attributes:

```json
{
  "hotelId": "H-1042",
  "name": "The Old Town House",
  "city": "Vilnius",
  "amenities": ["wifi", "parking", "breakfast"],
  "rooms": [
    {
      "type": "standard",
      "beds": 2,
      "capacity": 2
    },
    {
      "type": "family",
      "beds": 3,
      "capacity": 4
    }
  ]
}
```

Design two representations.

In PostgreSQL, use a combination of relational tables and JSONB where appropriate.

In MongoDB, decide which data belongs in the hotel document and which should be represented through references.

Then answer:

1. How would you retrieve one hotel's full public profile?
2. How would you update a single room type?
3. What changes if a hotel has ten thousand rooms?
4. Which information must remain historically accurate after a reservation is made?

Do not judge the designs merely by which one requires fewer lines of code.

Evaluate lifecycle, correctness, query behavior, and growth.

## Lab B — Design DynamoDB access patterns

Imagine you need to support these operations:

- Retrieve a reservation by ID.
- Retrieve a customer's reservations ordered by creation time.
- Retrieve all reservations for a particular property during a date range.
- Update a reservation status.
- Find recently failed payments.

List possible partition and sort keys.

Identify which operations your primary key supports efficiently and which might require a secondary index or another access path.

Consider how traffic would be distributed if a large proportion of writes targeted one customer, property, or date.

The objective is to discover why key design is part of distributed-system architecture.

## Lab C — Compare full-text and structured search

Consider a hotel description:

"The property is located in the historic center, with a peaceful courtyard and secure parking."

A customer searches for:

"Quiet hotel near old town with parking."

Discuss why simple substring matching may perform poorly.

How might tokenization, linguistic normalization, relevance ranking, synonyms, and semantic representations improve retrieval?

Which structured filters should still be applied separately?

What happens if a search result refers to a hotel that has been removed from the authoritative catalogue?

## Lab D — Build a data-system decision matrix

For the following workloads, propose a starting architecture and explain when you might introduce specialization.

| Workload | Dominant concern |
|---|---|
| Reservation creation | Transactional correctness |
| Customer session retrieval | Low-latency key lookup |
| Hotel-description search | Relevance and linguistic matching |
| Fraud-network investigation | Relationship traversal |
| Conversion reporting | Large-scale aggregation |
| Flexible property attributes | Evolving structured data |

A single database may be the best initial answer for several rows.

That's not a failure of imagination.

It's often a sign that you understand operational complexity.

## Lab E — Review a polyglot persistence design

A colleague proposes:

```text
PostgreSQL  → Reservations and payments
MongoDB     → Hotels and room metadata
Redis       → Sessions and cache
Elasticsearch → Search
Neo4j       → Fraud analysis
ClickHouse  → Analytics
```

Assume the company currently has ten developers and moderate traffic.

Prepare an architectural review.

Which systems are genuinely necessary now?

Which might be valuable later?

What synchronization pipelines would exist?

Which system owns each business fact?

How would failures affect customer-facing behavior?

How would you monitor stale or contradictory copies?

Finally, propose a simpler first version and explain what evidence would justify introducing each additional system.

---

## Further Reading — Optional Technical References

1. [PostgreSQL — JSON Types](https://www.postgresql.org/docs/current/datatype-json.html) — Structured and flexible data inside a relational system.
2. [MongoDB — Data Modeling](https://www.mongodb.com/docs/manual/data-modeling/) — Documents, relationships, embedding, referencing, and access patterns.
3. [MongoDB — Embedded Data](https://www.mongodb.com/docs/manual/data-modeling/embedding/) — Benefits and limitations of embedding related information.
4. [AWS — DynamoDB Data Modeling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/data-modeling.html) — Partition keys, sort keys, and access-pattern-driven design.
5. [Redis — Data Types](https://redis.io/docs/latest/develop/data-types/) — Key-value operations and specialized data structures.
6. [Elastic — How Full-Text Search Works](https://www.elastic.co/docs/solutions/search/full-text/how-full-text-works) — Text analysis, inverted indexes, and relevance.
7. [Neo4j — Cypher Patterns](https://neo4j.com/docs/cypher-manual/current/patterns/) — Graph modeling and relationship traversal.
8. [ClickHouse — What Is a Columnar Database?](https://clickhouse.com/resources/engineering/what-is-columnar-database) — Analytical workloads and column-oriented storage.
9. Martin Kleppmann, *Designing Data-Intensive Applications* — A broader perspective on storage, replication, consistency, and distributed data systems.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS340-L01  DATA SYSTEMS BEYOND RELATIONAL — INTERVIEW GLANCE CARD

CORE QUESTION
  What work must the data system do, and which guarantees must survive failure?
  Fastest at WHAT, under WHICH constraints, preserving WHICH guarantees?
  Earn complexity — don't collect databases like souvenirs

FIVE COMPETING RESPONSIBILITIES (every DB prioritizes differently)
  1 Data modeling     rows / docs / KV / graph / …
  2 Access            point lookup vs scan vs search vs traverse
  3 Consistency/tx    concurrency + replication visibility
  4 Durability/recovery crash / corruption / infra failure
  5 Scalability/ops   growth, traffic, operational cost

RELATIONAL (PostgreSQL default foundation)
  Relationships, keys, constraints, declarative SQL, planner, transactions
  Not obsolete: jsonb, FTS, arrays, recursive/graph-ish SQL, analytics in SQL
  Flexible attrs ≠ automatic Mongo migration — compare real workload
  Start with coherent system of record; specialize when measured need

DOCUMENT (MongoDB)
  Document = unit often accessed together (BSON: nested / arrays)
  Embed when co-lifecycle, bounded, rarely independent updates
  Reference when unbounded growth, own lifecycle, subset queries (reviews!)
  Atomicity strong within a document; multi-doc tx exist but model still matters
  Flexible schema ≠ optional correctness — validate contracts

KEY-VALUE
  Known-key access; narrow interface; awkward ad-hoc queries without paths
  Redis: structures (string/hash/set/zset/list/stream) — authoritative vs cache?
    expiry, outage, persistence/replication config matter
  DynamoDB: partition key (+ sort key); design for access patterns FIRST
    bad PK → hotspots (e.g. all today's events on one key)

SEARCH
  Information retrieval + relevance — not equality lookup
  Inverted index: term → document IDs (+ analysis, ranking, filters)
  Search index usually DERIVED view; booking inventory authority stays elsewhere
  Stale search hit → OK if booking API revalidates; sync/reconcile required

GRAPH
  Nodes + edges; multi-hop relationship queries natural
  Graphs representable in SQL too; dedicated DB when traversal dominates
  Highly connected nodes → combinatorial cost remains
  Share-payment-token ≠ automatic Neo4j — depth/complexity decide

ANALYTICAL (OLAP)
  OLTP: many small txs / point ops
  OLAP: scan, filter, group, aggregate large histories
  Column-oriented: read needed columns; compression on similar values
  Separate analytics when heavy scans fight customer-facing txs
  Freshness, duplicates, schema evolution, pipeline failure = new obligations

LABELS ARE MESSY
  "NoSQL" / "not only SQL" spans wildly different systems
  Logical model/interface ≠ physical/distributed architecture
  SQL ≠ one storage layout; categories overlap
  Consistency ≠ SQL vs NoSQL slogan — depends on product, op, replication,
    isolation, read/write settings

ARCHITECTURE RULES
  Per-fact source of truth; caches/search/analytics are copies
  Every derived store → sync, monitoring, reconciliation cost
  Decide per operation: stale search OK; double-sold room not; lost payment not
  Polyglot only when benefits outweigh ops + pipeline costs

FIVE DECISION QUESTIONS
  1 Dominant access patterns?
  2 What must be correct together (atomicity / freshness)?
  3 Growth, latency, throughput, hotspots?
  4 Failure: reconstruct? rebuild? lag? which failures violate contract?
  5 Operating cost (team, backups, security, replaceability)?

LECTURE RECOMMENDATION (travel platform case)
  Keep PostgreSQL as authoritative operational store
  Redis only for concrete low-latency patterns
  Evaluate search/analytics vs measurements
  Resist extra document/graph DBs until advantages justify a boundary

SENIOR LINE: choose by access patterns + correctness + failure + ops cost —
             not fashion.
```
