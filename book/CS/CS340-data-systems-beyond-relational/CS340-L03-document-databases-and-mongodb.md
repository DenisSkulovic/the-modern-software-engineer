---
id: CS340-L03
course: CS340
title: "Document Databases and MongoDB"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L02
next: CS340-L04
---







# CS340 — Data Systems Beyond Relational Databases

## Lecture 03: Document Databases and MongoDB

*Why putting related information together can transform an application's performance, why some documents become architectural disasters, and how MongoDB turns data modeling into a question of ownership, atomicity, and change.*

---

# 1. The Hotel Document That Ate the Database

It's Friday afternoon, and the engineering team at our hotel-booking platform is celebrating a successful migration.

Six months earlier, the company moved its hotel catalogue from a heavily normalized relational schema into MongoDB.

The old catalogue had dozens of interconnected tables. Retrieving a hotel profile involved information about descriptions, amenities, room categories, photographs, policies, and other property characteristics.

The new model is wonderfully convenient.

A hotel is a document.

It contains the hotel's name, location, descriptions, amenities, and room information. When the application needs a hotel profile, it retrieves one document and returns the relevant information to the frontend.

The code is simpler. Developers spend less time reconstructing objects through joins. Adding new property attributes rarely requires a coordinated relational schema migration.

For months, everything works.

Then one hotel becomes extraordinarily popular.

It receives thousands of customer reviews. The product team introduces historical pricing information. Marketing begins recording visitor interactions. Someone decides to embed the hotel's entire availability calendar inside the same document because, after all, availability belongs to the hotel.

Soon the document contains an enormous amount of information.

Every time somebody requests the hotel's public profile, the application retrieves far more data than the frontend needs.

Updates become increasingly expensive. Several services modify different parts of the same growing document. A developer discovers that an operation attempting to append another review is failing because the document has reached MongoDB's size limit.

MongoDB documents have a maximum BSON size of 16 mebibytes.

The team is surprised.

Wasn't MongoDB supposed to be flexible?

Wasn't embedding information supposed to improve performance?

And wasn't the entire reason for leaving PostgreSQL to avoid complicated relationships?

Then comes the real disaster.

Two customers attempt to reserve the last available room for the same date.

The booking service reads the hotel document, sees one room available, and proceeds with the reservation.

Both operations appear individually valid.

Both bookings are created.

The hotel has sold the same room twice.

The product manager demands an explanation.

One developer blames MongoDB. Another suggests adding a distributed lock. Someone proposes moving the availability calendar into Redis.

But the central problem isn't that MongoDB is incapable of enforcing correct updates.

It's that the data model was designed around a superficial principle:

**If information belongs to the same real-world thing, put it in the same document.**

That sounds reasonable.

It's also dangerously incomplete.

The correct document boundary depends on how information is accessed, updated, owned, and kept consistent—not simply on which nouns appear together in a business description.

Today we'll investigate that boundary.

We'll examine BSON documents, collections, embedding versus referencing, atomic updates, concurrent modifications, multidocument transactions, schema evolution, and the relationship between a document model and the application's actual business rules.

MongoDB will be our concrete example, but the principles extend to document databases and aggregate-oriented modeling more broadly.

By the end, you should be able to look at a complicated domain model and reason about what belongs together, what should remain separate, and which guarantees the database can enforce.

---

# 2. What Is a Document, Really?

Let's begin with the basic abstraction.

In a relational database, application information is represented through relations, commonly encountered as tables containing rows.

In MongoDB, application information is organized into **documents**, which live inside collections.

A document resembles a structured object.

It can contain ordinary fields, nested objects, arrays, and values of different BSON types.

For example, imagine a hotel containing its name, location, amenities, and a small collection of descriptions in different languages.

The logical structure resembles the object your backend might eventually return to the frontend.

That resemblance is one of document databases' most attractive properties.

But we should distinguish three concepts.

A JavaScript object is a runtime data structure.

JSON is a textual data-interchange format.

BSON is a binary serialization format used by MongoDB to represent documents.

They are related, but they aren't interchangeable.

## 2.1 BSON has more types than JSON

JSON supports strings, numbers, booleans, null, arrays, and objects.

BSON supports additional types, including dates, binary data, ObjectIds, and various numeric representations.

Why does this matter?

Consider a booking platform storing financial information.

A JavaScript Number uses binary floating-point representation. It cannot represent every decimal fraction exactly, and large integers have precision limits.

MongoDB supports Decimal128, which can be useful for decimal quantities requiring exact decimal representation within its precision and range.

But the application must preserve that type correctly through serialization and arithmetic.

Storing Decimal128 in MongoDB doesn't magically prevent the frontend from converting it into an imprecise JavaScript Number.

Likewise, MongoDB's ObjectId is a specific BSON identifier type.

It is not simply an arbitrary string containing hexadecimal characters.

Applications frequently convert ObjectIds into string representations for APIs, but that conversion must be managed consistently.

Type fidelity across application boundaries remains an engineering responsibility.

## 2.2 The special `_id` field

MongoDB documents have a primary identifier field named `_id`.

Within an ordinary unsharded collection, the default unique `_id` index enforces uniqueness of these values.

If an application doesn't supply `_id`, MongoDB or its driver can generate an appropriate value, commonly an ObjectId.

But not every document identifier must be an ObjectId.

An application can use another supported type when its data model calls for it.

For example, a hotel might use a stable string identifier such as `HOTEL-1042`.

The important distinction is between the identity of the record and its other attributes.

A hotel can change its name, address, or description while retaining its identity.

This is the same fundamental modeling principle we encountered in CS330.

Changing from tables to documents doesn't eliminate the need to define what makes an entity the same entity over time.

## 2.3 Collections are not tables with a different name

A collection groups documents.

Documents within a collection can have different shapes, subject to any configured validation rules.

That can make evolving structures more convenient.

But it also means the application needs to understand the range of shapes it may encounter.

If half the hotel documents use a string for the property rating and the other half use a number, every consumer must deal with the inconsistency.

A flexible database does not create a coherent data model on your behalf.

**Schema flexibility is the ability to choose and evolve structure, not permission to stop understanding your data.**

---

# 3. The Aggregate: Finding the Right Boundary

Now we arrive at the most important design concept of the lecture.

Imagine a hotel containing several amenities, contact details, and localized descriptions.

Should these live inside one document?

Often, yes.

But why?

The strongest reason isn't merely that they belong to the same hotel.

It's that they may form a useful **aggregate**: a group of related information that is commonly retrieved or modified together and can reasonably share a lifecycle and consistency boundary.

Aggregate is a term also used in domain-driven design, where it describes a consistency boundary governed by an aggregate root.

MongoDB documents provide a particularly natural physical representation for some aggregates because a single-document write is atomic.

These concepts overlap, but they aren't identical.

A domain aggregate is a modeling decision about business invariants and ownership.

A database document is a storage and atomicity unit.

A good design often aligns them.

## 3.1 Model operations before choosing document boundaries

Let's examine our hotel profile.

Customers regularly request the hotel's name, location, amenities, and short descriptions together.

Those fields change relatively infrequently.

They are owned by the catalogue subsystem.

And their combined size is reasonably bounded.

Embedding them into one hotel document makes sense.

Now consider customer reviews.

Reviews belong to hotels conceptually.

But they have different properties.

They arrive continuously. They grow without a natural small upper bound. Customers may edit or delete individual reviews. The frontend often retrieves only the latest twenty, sorted by date or relevance.

Reviews therefore have an independent lifecycle and access pattern.

Embedding every review into the hotel document would couple unbounded review activity to the hotel profile.

That is usually a poor aggregate boundary.

## 3.2 Bounded versus unbounded relationships

This distinction is extraordinarily useful.

Suppose a hotel has a fixed or modest collection of supported languages.

Embedding the translated hotel name and short description may be perfectly reasonable.

Suppose the same hotel has hundreds of thousands of customer reviews.

That collection is unbounded.

Embedding every review causes the parent document to grow indefinitely and creates increasingly awkward operations.

MongoDB's 16-mebibyte document limit makes the failure explicit, but performance and architectural problems may arise long before that limit.

Large documents consume memory and bandwidth, and large arrays can complicate indexing and updates.

The relevant rule is not "never embed arrays."

It's:

**Embed related information when its size, access pattern, and lifecycle make it a coherent part of the document. Reference information that grows or changes independently.**

## 3.3 Ownership is as important as cardinality

Imagine a hotel has a primary address.

That address is owned and maintained as part of the hotel's catalogue record.

Embedding it is natural.

Now imagine several hotels belong to one corporate chain.

The chain's legal entity information is shared by many properties and maintained independently.

Copying that corporate information into every hotel document may produce synchronization problems when it changes.

A reference to a separate organization record is more attractive.

The reasoning isn't simply one-to-many versus many-to-one.

It's whether the referenced information has an independent identity and lifecycle.

A useful question is:

"If this information changes, which documents should logically need updating?"

If one independent change requires modifying thousands of unrelated aggregates, the boundary deserves scrutiny.

---

# 4. Embedding: The Beautiful Shortcut With a Hidden Cost

Let's examine embedding in more detail.

Suppose our hotel document contains an array of amenities and a nested address object.

The frontend requests the hotel profile.

MongoDB can return the requested document, or selected fields through a projection, without requiring an application-level join across separate collections.

That can make reads straightforward and efficient.

But don't oversell the mechanism.

The storage engine still has to retrieve and process appropriate data and index structures.

A large document may be expensive even if the query returns only part of it.

The exact work depends on physical storage, caching, query planning, and document structure.

Embedding reduces certain relationship-reconstruction costs.

It doesn't make arbitrary quantities of data free.

## 4.1 Locality and read patterns

Consider two designs.

In the first, every hotel amenity is stored in a separate document.

Retrieving one hotel profile requires fetching the hotel and gathering its related amenities.

In the second, amenities are embedded inside the hotel document.

The second model may make the common read substantially simpler.

The application doesn't need to coordinate multiple records to assemble a small, coherent profile.

This is particularly attractive for data that naturally belongs to one aggregate.

But now imagine that the application frequently searches for all hotels containing one particular amenity.

The embedded fields may need appropriate indexes to make those queries efficient.

Document structure and query access paths must be considered together.

We'll investigate multikey indexes and query planning in CS340-L04.

## 4.2 Updates become part of the trade-off

Now suppose the marketing team modifies the hotel's main description.

The update affects information inside the hotel document.

Meanwhile, another service updates its amenities.

Does that mean the updates necessarily conflict?

Not always.

MongoDB supports targeted field updates that can modify different fields within the same document.

But the application must use the correct update operations.

A dangerous pattern is to retrieve a document, modify one field in application memory, and then replace the entire stored document with that stale copy.

Another concurrent update might have modified a different field in the meantime.

Replacing the entire document can overwrite the other change.

The physical document boundary is atomic.

But **atomicity alone does not prevent application-level lost updates caused by stale read-modify-write logic**.

We'll examine that distinction shortly.

## 4.3 The subset pattern

Here's a useful compromise.

Suppose a hotel has thousands of reviews, but the public hotel profile displays only its rating summary and three featured reviews.

We don't need to embed every review.

We can store the reviews independently while including a bounded summary inside the hotel document.

For example, the hotel document could contain an average rating, review count, and a small selection of featured-review summaries.

The independent review collection remains authoritative for the full review history.

The embedded summary is a derived representation optimized for the common profile read.

This approach resembles MongoDB's **subset pattern**.

It improves access convenience without allowing the document to grow indefinitely.

But we have introduced another problem.

How do we keep the summary synchronized with the underlying reviews?

That brings us to the cost of duplication.

---

# 5. Referencing: When Relationships Refuse to Stay Inside One Document

Suppose we store reviews in their own collection.

Each review contains its own identity and a reference to the hotel.

A review might include the hotel ID, customer ID, rating, text, and creation timestamp.

Now the application can query reviews independently.

It can paginate them, sort by date, retrieve a customer's reviews, or moderate suspicious content without rewriting the entire hotel document.

This is a natural use of **referencing**.

## 5.1 References aren't relational foreign keys

In a relational database, a foreign key can enforce the existence of a referenced record and define certain integrity behaviors.

In MongoDB, an ordinary field containing another document's identifier does not automatically create an enforced foreign-key relationship.

Suppose a review contains `hotelId: "HOTEL-1042"`.

What happens if the hotel is deleted?

MongoDB doesn't automatically guarantee that every referencing review disappears or that deletion is prevented.

The application needs an explicit policy.

It might retain reviews for audit purposes, remove them through a controlled workflow, or prevent hotel deletion while certain data exists.

The database supports the operations needed to implement that policy.

But the reference field alone doesn't enforce relational integrity.

This is one of the responsibilities developers must recognize when moving away from an explicitly constrained relational schema.

## 5.2 MongoDB can perform joins

A common claim is that document databases don't support joins.

That is false for modern MongoDB.

MongoDB's aggregation framework includes `$lookup`, which can combine information from another collection under supported join conditions.

That can be useful for certain read patterns.

But having a join capability does not mean that every relationship should be normalized into separate collections.

Nor does it mean that joins become costless.

They still require processing, suitable indexes, and attention to data volume and query shape.

We should model the data according to common access patterns and ownership, then use query mechanisms appropriate to the resulting design.

The question isn't whether MongoDB allows a join.

It's whether the data boundaries make sense for the workload.

## 5.3 The duplication dilemma

Let's return to our review summary.

When a new review arrives, the application writes a review document.

It also needs to update the hotel's review count and rating summary.

Those changes now span multiple documents.

What happens if the review insert succeeds but the summary update fails?

The review exists, but the summary is stale.

Depending on the product, that might be acceptable temporarily.

If the summary is explicitly derived data, we can repair it through a reliable event-driven update mechanism or periodic reconciliation.

But what if the duplicated information represents money or inventory rather than a review count?

Temporary disagreement may be unacceptable.

That distinction determines whether we need a strongly coordinated operation, a derived view, or a different data boundary.

**Duplication can make reads cheaper while making writes and consistency more complicated.**

Denormalization isn't free performance.

It's a deliberate exchange of write-side complexity for read-side convenience.

---

# 6. The Historical Snapshot: When Duplication Is Actually Correct

Let's investigate a particularly important exception.

A customer books a hotel room for 150 euros per night.

At booking time, the property is named "Old Town Suites."

Three months later, the hotel changes its name to "Grand Old Town Residence" and raises its nightly price.

What should the customer's historical reservation display?

If the reservation simply references the current hotel name and price, the past may appear to change whenever the catalogue changes.

That's undesirable.

A reservation is not merely a pointer to the current product catalogue.

It is also a historical business record of what was agreed.

Therefore, the reservation may need to embed an immutable or appropriately controlled snapshot of relevant booking information.

That might include the hotel name as presented at booking, selected room details, dates, currency, agreed price, cancellation terms, and other contractual facts.

Now duplication is not an accidental inconsistency.

It is the correct representation of two different kinds of truth.

The catalogue describes the hotel's current offer.

The reservation describes a historical agreement.

Their values may differ legitimately.

This is a deeply useful modeling principle.

**Before eliminating duplicated data, ask whether the copies are supposed to represent the same fact at the same point in time.**

Sometimes normalization removes accidental redundancy.

Sometimes it destroys information that the business must preserve.

The correct answer comes from semantics, not from database ideology.

---

# 7. Atomic Updates: The Power of One Document

Now we reach MongoDB's transactional boundary.

A write operation affecting one document is atomic at the document level.

That means the database doesn't expose a partially applied version of that single-document write as its completed result.

Suppose a hotel document contains a room type's availability count and associated update metadata.

A single update can modify related fields atomically.

This is particularly powerful when the document itself represents a coherent consistency boundary.

But let's investigate what can still go wrong.

## 7.1 The classic read-modify-write race

Imagine a document representing inventory for one hotel, room type, and date.

Its available count is one.

Two booking requests arrive concurrently.

Request A reads the document and sees one available room.

Request B reads the same document and also sees one.

Both requests decide that booking is possible.

If both then perform unconditional writes setting availability to zero, both might report success unless the application checks the relevant conditions correctly.

The individual writes are atomic.

But the complete sequence of reading, deciding, and writing was not one atomic operation.

We made a classic mistake: a decision was based on state that might change before the update.

## 7.2 Put the condition into the update

Instead of checking availability separately and then writing, we can issue a conditional atomic update.

The update should match the intended inventory document only when availability is greater than zero.

Then it decrements availability by one.

Conceptually:

"Find this inventory document, but only if at least one unit remains; decrement the count atomically."

If two requests compete for the last available unit, only one can successfully apply that conditional decrement.

The other finds that the condition no longer matches.

The application can interpret the operation's matched or modified result to determine whether inventory was successfully claimed.

This is a powerful pattern because the condition and modification are evaluated as part of the same single-document write operation.

MongoDB supports update filters and operators such as `$inc` for this purpose.

The practical lesson is:

**When an invariant depends on the current value of a document, express the condition in the atomic operation—not merely in application code before it.**

## 7.3 Why `$inc` is different from `$set`

Suppose a document contains a counter with value ten.

Two concurrent requests each want to increment it.

If they both read ten and later execute `$set` with eleven, one increment can be lost.

But MongoDB's `$inc` operator performs an increment within the update operation.

Two successful increments of one can result in twelve without requiring the application to calculate the new value from a previously read snapshot.

This doesn't mean `$inc` solves every concurrency problem.

It solves a particular class of relative updates.

If the operation also requires checking business conditions, those conditions must be part of the atomic update or another appropriate coordination mechanism.

Atomic operators are useful precisely because they let the database perform changes relative to its current state.

---

# 8. When One Document Isn't Enough

Let's complicate the booking scenario.

A customer wants to reserve a room for five consecutive nights.

Our inventory model stores one document per hotel, room type, and date.

That seems sensible.

Each daily inventory document is small, has a clear identity, and supports atomic conditional updates.

But the reservation now needs to claim inventory across five separate documents.

What if four updates succeed and the fifth fails?

The customer can't book only four of the five nights.

The business operation must behave coherently across all five dates.

One-document atomicity is not enough.

## 8.1 Multidocument transactions exist

MongoDB supports transactions spanning multiple documents, including across collections and, with the appropriate deployment support, across shards.

Within a transaction, the application can perform the coordinated updates and commit them together according to the database's transaction semantics.

For our example, a transaction might conditionally claim availability for every requested night, insert the reservation record, and commit only if all necessary operations succeed.

If a required inventory update fails, the transaction can be aborted.

This is a legitimate use of multidocument transactions.

The old claim that MongoDB cannot perform transactions is outdated.

## 8.2 Why not wrap everything in a transaction?

Transactions have costs.

The database must maintain appropriate transactional state and coordinate visibility, conflict detection, durability, and commit processing.

Long-running or highly contended transactions can create resource pressure and operational complications.

Distributed transactions spanning shards may introduce additional coordination overhead.

So the presence of multidocument transactions does not eliminate the value of choosing sensible document boundaries.

If a common operation can be performed safely as one conditional single-document update, that may be preferable to coordinating several unrelated documents.

But we should not distort the entire data model merely to avoid every transaction.

The correct rule is not "never use transactions."

It's:

**Choose transaction boundaries according to business invariants, then model data to make the common invariants practical to enforce.**

## 8.3 A transaction doesn't complete an external payment

Now imagine the inventory transaction succeeds.

The application then contacts a payment provider.

The payment provider approves the charge.

Before the backend records that result, its process crashes.

Can the MongoDB transaction undo the payment?

No.

The database transaction covers operations within its supported transactional system.

It doesn't automatically control an external payment provider.

We've crossed a distributed-system boundary.

Correctness now requires additional business workflow design: durable operation identities, state machines, idempotency, and reconciliation.

We examined those ideas in CS430.

The important distinction is that database transactions can protect database invariants, but they don't make independently operated external systems participate in one effortless atomic operation.

---

# 9. Optimistic Concurrency: Protecting Against Stale Updates

Let's investigate another common concurrency problem.

An administrator opens a hotel document for editing.

The hotel currently has version 17.

The administrator changes the cancellation policy but leaves the form open.

Meanwhile, another administrator updates the hotel's description and saves version 18.

The first administrator finally clicks Save.

If their application replaces the entire document using the stale copy, it may overwrite the second administrator's changes.

How can we prevent that?

## 9.1 Version-based conditional updates

One approach is **optimistic concurrency control**.

The document contains a version number.

When a client retrieves the document, it also receives that version.

When submitting an update, the client includes the expected version in the database update filter.

The database performs the change only if the stored version still matches.

The update also increments the version.

If the document changed in the meantime, the filter no longer matches.

The application can report a conflict, reload the current document, and ask the user to reconcile their changes.

The check and update must occur atomically.

Otherwise, we simply recreate the check-then-write race.

## 9.2 Why optimistic concurrency can be attractive

In many administrative applications, concurrent edits to the same document are relatively rare.

Holding a database lock for the entire time a human edits a form would be impractical.

The administrator might leave the browser open for an hour.

Optimistic concurrency avoids reserving exclusive access during that interval.

Instead, it allows concurrent reading and detects conflicts at update time.

That trade-off makes sense when conflicts are relatively uncommon and can be handled gracefully.

## 9.3 Different fields can sometimes be updated safely without a version conflict

But be careful not to over-apply document versioning.

If one operation independently increments a review counter while another changes the hotel's description, a properly targeted update may allow both changes to succeed without overwriting each other.

A coarse document-wide version check might reject one update unnecessarily.

The right concurrency strategy depends on the invariant.

Sometimes the entire aggregate must change coherently.

Sometimes two independent fields can safely evolve without treating every simultaneous update as a business conflict.

This is one reason targeted MongoDB update operators are preferable to blindly replacing whole documents in many workloads.

---

# 10. Nested Arrays: Convenience Can Become a Trap

Document databases make nested arrays convenient.

Imagine a hotel document containing room categories, each with its own facilities and pricing information.

At first glance, this looks elegant.

But how do we update one room category without replacing the entire array?

MongoDB provides positional update mechanisms and array filters that allow applications to target matching array elements.

For example, an update can select a room element by its identifier and change one field within that element.

This can avoid unnecessarily rewriting an entire logical structure at the application level.

But the choice of data model still matters.

## 10.1 Large arrays have independent costs

Suppose a hotel contains fifty room categories.

An embedded array might be perfectly reasonable.

Now imagine a hotel containing fifty thousand individually bookable units, each generating frequent updates.

One gigantic hotel document is no longer an attractive aggregate.

Even if the database provides efficient update operators, the document remains a large unit of logical atomicity and contention.

Frequent independent updates targeting the same large document can compete with one another.

And eventually the document may exceed the size limit.

This is not a problem solved by learning more update syntax.

It's a modeling problem.

## 10.2 The danger of treating arrays as independent collections

An array inside a document is not automatically equivalent to a separate collection.

The contained elements share the parent document's identity and lifecycle.

They don't automatically have independent indexes and storage behavior identical to standalone documents.

MongoDB does provide multikey indexes that can index array values, but query planning and update behavior have their own rules.

We'll examine those in CS340-L04.

For now, remember the architectural distinction.

A bounded array is useful when the elements naturally belong to one aggregate.

An unbounded collection of independently managed entities usually deserves a separate data boundary.

---

# 11. Schema Evolution Without an `ALTER TABLE` Moment

Let's return to our hotel's catalogue.

The original document contains a cancellation policy expressed as a simple string.

Later, the product team introduces a richer policy model.

It needs a cancellation deadline, fee rules, timezone information, and exceptional conditions.

In a relational database, this might involve an explicit schema migration.

MongoDB can allow old and new document shapes to coexist in the same collection.

That flexibility is valuable.

But it creates a new challenge.

Which shapes can application code safely expect?

## 11.1 The old document never received the memo

Suppose the original document stores:

`cancellationPolicy: "flexible"`

The new application expects a nested object with fields describing deadlines and fees.

It reads an old document.

What happens?

If the code blindly accesses nested fields, it may fail or produce incorrect results.

A TypeScript interface declaring the new shape doesn't transform old stored documents into that shape.

Types do not rewrite persistent data.

The application needs an evolution strategy.

## 11.2 Schema versioning

One useful approach is to store a schema-version identifier.

For example, older documents might carry version 1, while newly written documents carry version 2.

The application can interpret or normalize documents according to the appropriate version.

During a transition, readers may support both shapes while writers produce the new representation.

A background migration can gradually update older documents.

Eventually, the organization may remove compatibility code when it has verified that the old representation is no longer needed.

This is closely related to the expand-and-contract approach to schema evolution discussed in CS330.

The difference is that document stores may permit multiple shapes to coexist without a single immediate schema alteration.

That is operational flexibility, not the elimination of migration work.

## 11.3 Schema validation

MongoDB supports collection-level schema validation, including rules expressed through a MongoDB-supported subset of JSON Schema.

The database can reject writes that fail configured validation requirements.

For example, a hotel document might require a name, a valid location structure, and a particular schema version.

But validation behavior depends on its configuration.

MongoDB supports validation levels and actions that determine how invalid writes and existing documents are treated.

A stricter write-validation policy doesn't necessarily mean every old document was retrospectively cleaned up.

Applications must still account for legacy data and migration state.

And database-level structural validation does not automatically enforce every business rule.

A field may have the correct BSON type while containing a semantically invalid price or an impossible booking interval.

## 11.4 The three validation boundaries

For practical application engineering, it helps to recognize three layers.

At the API boundary, validate untrusted incoming data.

At the domain layer, enforce business rules and relationships.

At the database boundary, enforce appropriate storage constraints and invariants.

These layers overlap intentionally.

They protect against different failure modes.

API validation gives clients useful errors and prevents malformed data from entering normal workflows.

Domain validation establishes business meaning.

Database constraints help protect persistent state even if an application path contains a mistake.

A flexible document database can participate in all three, but the responsibilities must be designed explicitly.

---

# 12. MongoDB Indexes and Queries: Just Enough to Understand the Model

We shouldn't finish this lecture without connecting document design to query performance.

Suppose we store each hotel as a document.

The application needs to find hotels by city, available amenities, price category, and various property attributes.

MongoDB supports indexes over fields, including fields nested within documents.

It also supports multikey indexes for appropriate array-valued fields.

That allows documents to remain hierarchical while still supporting indexed access to selected nested values.

But the existence of an index doesn't make every query efficient.

## 12.1 An access pattern is a workload requirement

Imagine two queries.

The first retrieves one hotel by `_id`.

The second searches hotels in Prague that contain certain amenities and sorts them by a rating field.

These operations have different needs.

The first benefits from the document identifier index.

The second may require additional indexes and careful consideration of selectivity, sorting, and query planning.

If you never design or test those access paths, a flexible schema can become a flexible way to create slow queries.

The database must still locate the relevant documents.

## 12.2 Arrays complicate query semantics

Suppose a document contains an array of room objects.

Each room has a capacity and price.

The application wants rooms with capacity at least four and price below 200 euros.

A careless query over separate array-field predicates may match conditions satisfied by different elements of the same array.

That can produce a logically incorrect result.

MongoDB's `$elemMatch` operator helps require that specified conditions apply to the same matching array element.

This is a wonderful example of how nested data modeling influences query correctness.

The issue isn't merely index performance.

It's the meaning of the query.

## 12.3 The aggregation pipeline

MongoDB also provides an aggregation pipeline.

Conceptually, documents pass through a sequence of transformations.

A pipeline might filter records, select fields, group results, calculate values, sort them, or combine information from another collection.

Stages such as `$match`, `$project`, `$group`, and `$lookup` express these operations.

This is useful because applications often need more than simple document retrieval.

But aggregation pipelines are not automatically efficient.

Moving a selective filter earlier may reduce downstream work.

Suitable indexes may avoid scanning large collections.

Grouping enormous datasets can consume substantial resources.

And joining collections still introduces processing costs.

We'll examine these mechanisms in CS340-L04.

For now, the important message is:

**A document model changes how data is represented. It does not eliminate query planning or computational complexity.**

---

# 13. Returning to the Hotel That Ate the Database

Let's revisit our original incident.

The company created one enormous hotel document containing virtually every related entity.

At first, that seemed convenient.

But the model ignored several different lifecycles.

Hotel descriptions changed occasionally.

Reviews arrived continuously.

Availability changed constantly under concurrent booking activity.

Historical pricing grew over time.

Customer interactions belonged to an analytics workload.

These responsibilities should never have been forced into one giant document simply because they shared a hotel identifier.

## 13.1 Redesign the boundaries

The public hotel profile becomes one bounded document containing catalogue information.

Reviews become independently stored documents with references to the hotel.

The hotel may retain a small derived rating summary and selected featured-review information.

Inventory becomes its own set of carefully modeled records, organized according to the business's availability and concurrency requirements.

Reservations become independent business aggregates containing appropriate historical snapshots.

Analytics events enter a separate ingestion and analytical pipeline.

This doesn't necessarily require five different database products.

Several collections can coexist inside MongoDB, and some responsibilities may remain better suited to PostgreSQL or another authoritative system.

The important change is conceptual.

We have separated information according to ownership, lifecycle, access pattern, and consistency requirements.

## 13.2 Fix the double-booking bug

For inventory represented as one document per date and room type, a conditional atomic decrement can prevent two requests from independently claiming the last available unit in that document.

But a multi-night booking spans several inventory records.

That requires appropriate coordination, possibly through a multidocument transaction or a carefully designed reservation-hold workflow.

The application must also handle transaction conflicts, uncertain outcomes, and retries without duplicating reservations.

If payments are involved, database transaction boundaries alone are insufficient.

We need a durable business workflow.

This is where the material from CS330 and CS430 becomes essential.

MongoDB is not being asked to magically solve business correctness.

It's being used according to explicit guarantees.

## 13.3 Would we still choose MongoDB?

Possibly.

The hotel catalogue remains a plausible document-oriented workload.

Flexible hierarchical attributes and profile-oriented access patterns can fit MongoDB well.

But PostgreSQL with JSONB might also satisfy the same requirements.

If the company already operates PostgreSQL successfully, introducing MongoDB creates additional infrastructure and data-synchronization costs.

The decision should depend on measured requirements and operational trade-offs.

What we definitely shouldn't do is assume that moving to MongoDB fixes poor modeling automatically.

A bad relational model can become a bad document model.

It may simply become a bad model with curly braces.

---

# 14. The Oral Examination

Before reading the solutions, answer the following questions aloud.

A strong answer should identify the relevant invariants, access patterns, and failure modes—not merely repeat which product features exist.

## Challenge 1 — The enormous hotel document

A developer embeds every customer review, every reservation, and every availability record inside one hotel document.

What problems will eventually appear?

Which information would you separate, and why?

## Challenge 2 — Embedding versus referencing

A hotel has three official contact addresses, fifty amenities, and two hundred thousand reviews.

Which data would you consider embedding?

Which would you reference?

What information would you need before deciding?

## Challenge 3 — The disappearing increment

Two requests read a counter with value ten.

Both then update the document to set the counter to eleven.

The final value is eleven.

Why didn't single-document atomicity prevent the lost increment?

How would you fix it?

## Challenge 4 — The last room

Two customers attempt to reserve the last available room for one date.

Describe a safe single-document inventory update.

Now explain why booking five consecutive nights may require a different coordination mechanism.

## Challenge 5 — The stale administrator

Two administrators edit the same hotel profile.

The second saves a new description.

The first later submits an old full-document copy with an updated cancellation policy.

How can the application avoid overwriting the second administrator's changes?

## Challenge 6 — The historical reservation

A hotel changes its name and nightly price after a customer books.

Should historical reservations automatically display the latest catalogue values?

Which information would you snapshot?

## Challenge 7 — The schema migration

A collection contains one million documents using an old cancellation-policy format.

A new application release expects a different nested structure.

MongoDB allows both document shapes to exist.

What deployment and migration strategy would you use?

## Challenge 8 — The MongoDB transaction question

An interviewer says:

"MongoDB is NoSQL, so you can't use ACID transactions. That's why it isn't suitable for serious business applications."

Evaluate the claim.

What would you still need to understand before choosing MongoDB for a booking system?

---

# 15. Solutions and Discussion

## Solution 1 — Oversized aggregate

The document contains unrelated lifecycles and unbounded collections.

It may become excessively large, hit BSON size limits, increase update contention, and require expensive reads or modifications.

Reviews, reservations, availability, and analytics events should generally be modeled independently.

The hotel profile should remain a bounded catalogue aggregate.

The exact boundaries depend on ownership, access patterns, and consistency requirements.

## Solution 2 — Embedding decision

A small bounded collection of hotel-owned contact information is a reasonable embedding candidate.

Fifty amenities may also be appropriate if they are retrieved with the hotel and share its lifecycle.

Two hundred thousand reviews are better represented independently.

But cardinality alone isn't the complete answer.

We should also examine update frequency, query patterns, ownership, duplication, and whether the child entities need independent identities.

## Solution 3 — Lost increment

The read and subsequent write are separate operations.

Each write may be atomic, but both clients calculated the replacement value from the same stale state.

Using `$inc` allows the database to increment the current value as part of the atomic update.

For more complicated invariants, include relevant conditions in the update filter or use another suitable coordination mechanism.

## Solution 4 — Inventory correctness

Store an inventory record for the relevant hotel, room type, and date.

Use a conditional atomic update requiring available inventory greater than zero, then decrement it.

Only a successful conditional update claims the unit.

For a multi-night booking, several inventory documents must be updated consistently.

A suitable multidocument transaction or a carefully designed hold-and-confirm workflow may be required.

The final solution must also handle failures and retries safely.

## Solution 5 — Optimistic concurrency

Use targeted updates when independent fields can be modified safely.

For operations requiring protection against stale state, include an expected document version or relevant expected field value in the atomic update filter.

If the condition no longer matches, report a conflict and allow reconciliation rather than overwriting newer information.

## Solution 6 — Historical facts

A reservation should preserve the business facts agreed at booking time.

These can include hotel name, room description, dates, price, currency, and applicable cancellation terms.

The current catalogue may evolve independently.

This is intentional historical denormalization, not necessarily inconsistent data.

## Solution 7 — Schema evolution

Introduce readers capable of handling the old and new representations.

Write new records in the chosen new format.

Use explicit schema versions or normalization logic where useful.

Backfill older documents through a controlled migration, monitor progress, and enforce appropriate validation rules.

Remove compatibility code only after verifying that old representations are no longer required.

The lack of an immediate ALTER TABLE operation does not eliminate migration work.

## Solution 8 — Transactions

The claim is false.

MongoDB supports multidocument ACID transactions in supported deployment configurations.

Single-document writes are atomic, and multidocument transactions can coordinate wider changes.

However, correctness still depends on data modeling, transaction boundaries, deployment configuration, durability and consistency settings, and business workflow design.

A database transaction also cannot automatically roll back an independently completed external payment.

The correct choice depends on the actual workload and guarantees.

---

# 16. The Mental Model Worth Keeping

A document database organizes information into structured documents that can naturally represent hierarchical application data.

The most important decision isn't the syntax of those documents.

It's **where one document should end and another should begin**.

Five questions provide a durable framework.

**What is retrieved together?** Information frequently read as one coherent object may benefit from embedding.

**What changes together?** Fields forming one invariant may benefit from sharing an atomic document boundary.

**What grows independently?** Unbounded or independently managed entities usually deserve separate documents.

**What owns the information?** Independent identities and lifecycles often favor referencing rather than uncontrolled duplication.

**What must remain correct under concurrency?** Atomic updates, conditional filters, optimistic concurrency, and transactions must reflect real business invariants.

MongoDB provides useful tools for all these responsibilities, but it doesn't choose the boundaries for you.

The central principle is:

**Design documents around access patterns, ownership, and consistency boundaries—not merely around real-world nouns.**

A good document model makes common operations natural and correctness practical to enforce.

A bad document model merely relocates relational complexity into application code, unbounded arrays, and difficult synchronization problems.

---

# 17. Next Lecture — Indexes, Queries, and Aggregation Beyond SQL

We've designed document boundaries and investigated how MongoDB maintains atomicity and supports evolving structures.

Now comes another question.

How does the database actually find the information?

What happens when a query filters nested objects or arrays?

Why can an index dramatically accelerate one query but do almost nothing for another?

How do compound and multikey indexes behave?

And how can an aggregation pipeline transform millions of documents without accidentally performing enormous unnecessary work?

In **CS340-L04 — Indexes, Queries, and Aggregation Beyond SQL**, we'll examine the physical and logical machinery that makes document queries efficient—or surprisingly expensive.

We've designed the data.

Next, we'll make the database find it.

---

# Optional Practical Lab — Modeling MongoDB Correctly

*The spoken lecture ends here. The remaining material is intended for screen-based experimentation and revision.*

## Lab A — Create a bounded hotel document

Using `mongosh` against a local development database, create a hotel document containing bounded catalogue data.

```javascript
use cs340_lab

db.hotels.insertOne({
  _id: "HOTEL-1042",
  schemaVersion: 1,
  name: "Old Town House",
  location: {
    city: "Vilnius",
    country: "LT"
  },
  amenities: ["wifi", "parking", "breakfast"],
  descriptions: {
    en: "A quiet hotel near the old town."
  },
  ratingSummary: {
    count: 0,
    average: null
  }
})
```

Discuss which fields form one catalogue aggregate and which business facts should remain elsewhere.

## Lab B — Separate reviews from the hotel

Create an independently managed review document.

```javascript
db.reviews.insertOne({
  _id: "REVIEW-001",
  hotelId: "HOTEL-1042",
  customerId: "CUSTOMER-73",
  rating: 5,
  text: "Excellent location.",
  createdAt: new Date()
})
```

Retrieve reviews for the hotel:

```javascript
db.reviews.find({
  hotelId: "HOTEL-1042"
})
```

Create an index on `hotelId` and `createdAt`, then consider how it supports retrieving recent reviews.

Why shouldn't a review's `hotelId` field be treated as an automatically enforced foreign key?

## Lab C — Reproduce and repair the inventory race

Create a test inventory document:

```javascript
db.inventory.insertOne({
  _id: "HOTEL-1042:standard:2026-12-15",
  hotelId: "HOTEL-1042",
  roomTypeId: "standard",
  date: "2026-12-15",
  available: 1
})
```

The safe inventory decrement uses one conditional write:

```javascript
db.inventory.updateOne(
  {
    _id: "HOTEL-1042:standard:2026-12-15",
    available: { $gt: 0 }
  },
  {
    $inc: { available: -1 }
  }
)
```

Repeat the update.

Inspect `matchedCount` and `modifiedCount`.

Explain why only one decrement can succeed when availability begins at one.

Then consider how you'd claim inventory across several dates atomically.

## Lab D — Practice optimistic concurrency

Create a hotel-profile version field.

```javascript
db.hotels.updateOne(
  { _id: "HOTEL-1042" },
  { $set: { version: 1 } }
)
```

Attempt an update requiring the expected version:

```javascript
db.hotels.updateOne(
  {
    _id: "HOTEL-1042",
    version: 1
  },
  {
    $set: { name: "Grand Old Town House" },
    $inc: { version: 1 }
  }
)
```

Repeat with the stale expected version.

Explain why the second operation no longer matches.

Discuss when a document-wide version check is desirable and when independent targeted field updates may be sufficient.

## Lab E — Enforce schema validation

Create a separate test collection with MongoDB JSON Schema validation.

```javascript
db.createCollection("validatedHotels", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "schemaVersion"],
      properties: {
        name: { bsonType: "string" },
        schemaVersion: { bsonType: "int" }
      }
    }
  }
})
```

Insert valid and invalid documents.

Observe how validation behaves.

Then investigate how changing validation rules affects existing documents.

Pay particular attention to validation levels and the distinction between validating new writes and retroactively cleaning up old data.

## Lab F — Update an embedded array element

Create a document containing a small array of room categories.

```javascript
db.roomCatalog.insertOne({
  _id: "HOTEL-1042",
  rooms: [
    { id: "standard", capacity: 2, active: true },
    { id: "family", capacity: 4, active: true }
  ]
})
```

Update only the matching category:

```javascript
db.roomCatalog.updateOne(
  { _id: "HOTEL-1042" },
  {
    $set: {
      "rooms.$[room].active": false
    }
  },
  {
    arrayFilters: [
      { "room.id": "family" }
    ]
  }
)
```

Explain why a targeted update can be safer than replacing an entire stale document.

Then ask whether embedding ten thousand frequently updated rooms would still be a sensible design.

## Lab G — Design a real booking model

Design collections or aggregates for:

- Hotels and bounded public descriptions.
- Room types.
- Reviews.
- Per-date availability.
- Customer reservations.
- Historical price snapshots.
- Payment-operation state.

Identify which information is authoritative and which is derived.

Specify the atomicity requirements for one-night and multi-night bookings.

Explain what happens when reservation creation succeeds but payment processing becomes uncertain.

The goal is to connect MongoDB modeling to actual business correctness rather than merely produce convenient JSON objects.

---

## Further Reading — Optional Technical References

1. [MongoDB — Data Modeling](https://www.mongodb.com/docs/manual/data-modeling/) — Access-pattern-driven document design.
2. [MongoDB — Embedding Versus References](https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/) — Choosing data boundaries and relationships.
3. [MongoDB — Avoid Unbounded Arrays](https://www.mongodb.com/docs/manual/data-modeling/design-antipatterns/unbounded-arrays/) — Document growth and high-cardinality relationships.
4. [MongoDB — Atomicity and Transactions](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/) — Single-document guarantees and transaction boundaries.
5. [MongoDB — Model Data for Atomic Operations](https://www.mongodb.com/docs/manual/tutorial/model-data-for-atomic-operations/) — Aligning data models with atomic updates.
6. [MongoDB — Schema Validation](https://www.mongodb.com/docs/manual/core/schema-validation/) — Enforcing structural requirements.
7. [MongoDB — Schema Design Patterns](https://www.mongodb.com/docs/manual/data-modeling/design-patterns/) — Subsets, computed values, versioning, and other modeling techniques.
8. [MongoDB — BSON Documents](https://www.mongodb.com/docs/manual/core/document/) — Document types and size limits.
9. [MongoDB — Update Array Elements](https://www.mongodb.com/docs/manual/reference/operator/update/positional-filtered/) — Filtered positional updates.
10. [MongoDB — Unique Indexes](https://www.mongodb.com/docs/manual/core/index-unique/) — Database-enforced uniqueness and its constraints.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers can skip it. This is the rapid visual review: scan the card, identify anything you can't explain, and revisit only that section.*

```text
CS340-L03  DOCUMENT DATABASES & MONGODB — INTERVIEW GLANCE CARD

CORE MODEL
  Document      Structured BSON record; nested fields and arrays
  Collection    Group of documents; shapes may differ
  _id           Document identity; indexed and normally unique in collection
  BSON          Binary data model: ObjectId, Date, Decimal128, arrays, objects...
  Limit         16 MiB maximum BSON document size
  Schema        Flexible ≠ absent; explicit contracts still required

DOCUMENT BOUNDARIES — THE FIVE QUESTIONS
  1. Read together?     → consider EMBEDDING
  2. Change together?   → consider EMBEDDING / shared atomic boundary
  3. Grow without bound?→ prefer REFERENCES / separate collection
  4. Own lifecycle?     → usually separate entity
  5. One invariant?     → align document or transaction boundary

EMBED vs REFERENCE
  Embed when:
    bounded child data, read together, common lifecycle,
    shared ownership, useful one-document atomicity
  Reference when:
    unbounded arrays, independently queried/updated children,
    many-to-many, independent identity/lifecycle, high cardinality

  HOTEL PROFILE: name/address/amenities/small translations → EMBED
  REVIEWS:       many, grow forever, page/sort/moderate      → REFERENCE
  AVAILABILITY:  frequent concurrent date-specific updates → SEPARATE
  RESERVATION:   historical agreement/snapshots              → OWN AGGREGATE
  CATALOGUE:     current hotel offer ≠ historical booking truth

  ANTI-PATTERN: one giant hotel document with 100k reviews and
  all bookings/inventory. Eventually growth, contention, size limits.

ATOMICITY & CONCURRENCY
  Single-document write = atomic.
  updateMany across documents ≠ one atomic all-or-nothing operation.
  Read → decide → unconditional write = RACE.

  Unsafe:
    A reads 1 room; B reads 1 room;
    A writes remaining=0; B writes remaining=0; BOTH claim success.

  Safe single-day decrement:
    filter: {_id: dayKey, available: {$gt: 0}}
    update: {$inc: {available: -1}}
    matchedCount=1 → claimed; 0 → no claim.
  $inc counter: avoids stale read + $set lost increment.
  Multi-night inventory across multiple docs → transaction or coherent
    hold/state-machine design; handle failures + retries.
  A database transaction ≠ atomic control of an external payment API.

LOST UPDATE / OPTIMISTIC CONCURRENCY
  Whole-document replacement from stale copy can clobber fresh fields.
  Prefer $set of targeted field(s) for independent updates.
  For aggregate-wide conflict detection:
    filter: {_id, version: expected}
    update: {$set: changes, $inc: {version: 1}}
    no match → stale version/conflict.
  Version check must happen ATOMICALLY with write.
  Don't reject harmless independent updates unnecessarily.

ARRAYS
  Small bounded list → useful embedded structure.
  Unbounded array → size/performance/index problems.
  $push append, $pull remove, $addToSet conditionally add,
  $set targeted update, $[name] + arrayFilters select nested elements.
  $elemMatch → predicates must hold in SAME array element.
  Multikey indexes support array contents, with specific restrictions.

REFERENCES & DUPLICATION
  {hotelId: "..."} does NOT enforce foreign-key integrity automatically.
  $lookup can combine collections; document DBs CAN perform joins.
  Duplicating derived reviewCount/rating → faster reads;
    must maintain/reconcile data.
  Historical price/name snapshot → intentional immutable business fact.
  Catalogue NOW and reservation THEN may legitimately disagree.

SCHEMA EVOLUTION
  No ALTER TABLE requirement does NOT imply no migration.
  Old version: cancellationPolicy = "flexible"
  New version: cancellationPolicy = {deadline, fees, timezone}
  Plan: dual-shape readers → new-shape writers → backfill → verify
        → tighten validation → retire compatibility code.
  schemaVersion can make migrations explicit.
  $jsonSchema validation available; levels/actions matter.
  Existing invalid docs may survive changed validator rules.
  TypeScript runtime types alone do not validate database documents.

BSON / TYPE TRAPS
  ObjectId != arbitrary string; convert deliberately across APIs.
  Date != date-only business value; timezone semantics matter.
  Decimal128 can preserve decimal precision; JavaScript Number may not.
  Missing field != explicit null in every query/serialization situation.
  _id identity should survive changes in descriptive fields.

QUERY DESIGN (PREVIEW OF L04)
  Index common filters/sorts; don't index every field blindly.
  Dot notation queries nested values.
  Multikey index for arrays.
  $match → filter; $project → select; $group → aggregate;
  $lookup → join-like combination.
  Queries still need plans, indexes, selectivity, and cost measurement.

TRANSACTIONS / DISTRIBUTED GUARANTEES
  MongoDB supports multi-document ACID transactions.
  Available on supported replica set and sharded deployments.
  Transactions have coordination/conflict/resource costs.
  Single-doc atomicity ≠ automatically durable on every failure:
    write concern/journaling/replication configuration matters (L05).
  NoSQL ≠ no consistency; NoSQL ≠ no transactions.

DESIGN DECISION — SENIOR CHECKLIST
  Dominant queries?   Read vs write frequency?   Growth bounded?
  Who owns record?    What changes independently?
  One business invariant across what records?
  What can be stale?   What must never be inconsistent?
  Which copies are derived?   How are they repaired?
  Can PostgreSQL JSONB meet requirements without another datastore?

INTERVIEW IN ONE LINE
  "I design document boundaries around data accessed and changed together,
   keep unbounded independent entities separate, and enforce business
   invariants with atomic conditional writes or transactions where needed."
```
