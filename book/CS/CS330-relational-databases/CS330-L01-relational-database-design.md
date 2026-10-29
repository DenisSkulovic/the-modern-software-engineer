---
id: CS330-L01
course: CS330
title: "Relational Database Design"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [BACK301-S02]
prev: null
next: CS330-L02
---



# CS330 — Relational Databases and Transactions

## Lecture 01: Relational Database Design

*The database contains valid rows. The SQL executes correctly. Every test passes. Yet a customer opens an old reservation and discovers that the price has changed since checkout. The problem isn't the query. It's what the schema believes about the world.*

# Part I — Intuition

## The picture to carry in your head

Imagine a small hotel with twelve rooms, one receptionist, and a paper reservation book.

Each booking occupies one line: guest name, room number, arrival date, departure date, and nightly price.

If you were developing software for this hotel, translating the reservation book into a single database table would seem perfectly sensible.

And initially, it would work.

Then the hotel joins a travel-booking platform.

Its third floor is renovated. Several rooms receive new numbers. The *Economy Double* category becomes *Classic Double*. Prices vary by season and by night. A family books three rooms in one transaction, then cancels one of them.

Meanwhile, the accounting department asks you to reconstruct exactly what another customer agreed to pay six months ago.

Suddenly, the elegant original table becomes a liability.

The hotel has changed its current price, and old reservations now display that price.

The customer has three rooms, but the database treats each room as a separate reservation.

A room number changes, and historical references become confusing.

None of this requires corrupt data. The individual rows can all satisfy the database's technical rules.

The trouble is that **the database represents an inaccurate model of the business**.

That's the central idea of relational database design.

A schema is not merely a collection of places to store values. It expresses what things exist, which facts belong to them, how those facts relate, and which combinations are allowed.

## 1. A name is not an identity

Consider the hotel's name: *Grand Baltic*.

Suppose the property changes its branding to *Baltic Grand*.

Is it now a different hotel?

Of course not.

The name changed. The underlying entity persisted.

A useful database model distinguishes identity from mutable descriptions.

We might give the hotel a stable database identifier and store its current name as an attribute.

Reservations can refer to that stable identifier without becoming invalid when the name changes.

This principle appears everywhere.

A customer's email address is not necessarily their permanent identity.

A physical room's displayed number may change.

A product's SKU might be replaced.

A company's legal name can change without creating an entirely new organization.

The design question is: **What makes this thing the same thing over time?**

Once you've answered that, choosing a primary key becomes much easier.

## 2. Two facts that look identical may mean different things

Now consider the room price.

A Deluxe room currently costs €249 per night.

But a customer booked that room last month for €189.

Which price should appear on the old invoice?

The agreed €189.

The current room price and the historical agreed price are different business facts, even though they may originally have held the same number.

This distinction is important because database designers frequently hear that duplication is bad.

Often it is.

If every reservation repeats the hotel's current address, changing that address requires updating many rows. Copies can become inconsistent.

But preserving the agreed price in a reservation is not necessarily redundant duplication of the current price.

It records a historical agreement.

The rule isn't "never duplicate data."

It's **don't accidentally store multiple independently maintained copies of the same fact, and don't discard historical facts that must remain true.**

## 3. Relationships have shapes

Our hotel sells several room categories.

Each category may contain many physical rooms.

A customer may create many reservations.

One reservation may contain several accommodation items.

These relationships have different shapes.

A hotel has many room types.

A reservation has many reservation items.

Each item refers to a room type and may describe a quantity, agreed price, or rate plan.

Why not create three independent reservations when someone books three rooms?

Because the business may treat them as one booking with a shared confirmation, payment arrangement, and cancellation policy.

But a customer might later cancel only one room.

The intermediate reservation-item entity gives us somewhere to represent that distinction.

Cardinality isn't merely a diagramming convention.

It describes how the business behaves.

## 4. Database constraints are promises about valid reality

Suppose our API rejects a reservation when checkout is earlier than check-in.

Good.

But what happens when an administrator imports reservations through a script? Or another service writes directly to the database?

The TypeScript validation in our API doesn't run there.

A database constraint can enforce the date relationship regardless of which application writes the row.

A foreign key can prevent references to nonexistent hotels.

A uniqueness constraint can prevent duplicate room codes within the same property.

These are valuable because they enforce rules at the shared persistence boundary.

But not every business rule can be expressed through a simple constraint.

A reservation spanning five nights might require coordinating inventory across five dates.

A state transition might depend on the previous status.

Database design must distinguish rules that can be enforced locally from rules requiring transactional coordination.

## 5. Even a good schema will change

Return to our growing hotel platform.

Product management introduces a new booking channel: direct, partner, or corporate.

You need to add it to millions of existing reservations.

You could immediately introduce a mandatory database column.

But existing records lack values, and old application instances may still be writing reservations during deployment.

A technically reasonable schema change can become a production outage.

So database design has a lifecycle.

We must think not only about the correct final representation but also about how to reach it safely from the current one.

A common technique is to expand the schema in a compatible way, migrate data and application behavior gradually, enforce the new rules, and only then remove the old representation.

The model must be correct.

It must also be possible to operate and evolve.

## Three questions before the Deep Dive

1. Why should a reservation reference a stable hotel identifier rather than use the hotel's current name as its identity?
2. Why is duplicating a hotel's current address across reservations different from preserving an agreed historical price?
3. Why might introducing a new mandatory column cause an outage even if the SQL migration looks correct?

If you can answer those, you already understand the most important intuition: **the schema models facts, their meanings, and their lifecycles—not merely the shape of convenient application objects.**

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The reservation that changed after checkout

It's October 2026.

Our booking platform has been running successfully for eighteen months.

A customer contacts support.

Six months ago, she booked three nights at €189 per night.

Now the reservation page displays €249.

Nobody modified her reservation directly.

The application simply joins the reservation to the room type's current pricing information.

The hotel's revenue manager recently increased that price.

The query is working exactly as written.

The database is returning perfectly valid data.

Yet the result is wrong.

The mistake occurred earlier, when the schema assumed a room type's price and a reservation's agreed price represented the same information.

They don't.

This is the first important distinction of database modeling:

**A correct query against an incorrect model can produce a confidently incorrect business answer.**

Before designing tables, we need to discover what facts actually exist in the domain.

## 2. Model the business before choosing tables

Consider the word *room*.

Our hotel has one hundred physical rooms divided into five categories: Standard, Deluxe, Suite, Family, and Accessible.

When a customer books a Deluxe room for next weekend, what have they purchased?

They may have purchased a right to occupy a suitable Deluxe room rather than one particular numbered room.

The hotel might assign the actual physical room during check-in.

That gives us at least four distinct concepts.

A **room type** describes the accommodation category being sold.

A **physical room** represents an individual unit in the building.

**Inventory** describes which accommodation capacity is available for particular dates.

A **reservation** records the customer's booking commitment.

These concepts have different identities and lifecycles.

A physical room might be renovated without changing the room category it belongs to.

A room category may be renamed without replacing its physical rooms.

Inventory availability changes every time a qualifying reservation is made or canceled.

And the reservation must retain the terms agreed with the customer, even when the hotel's current offering changes.

Now imagine Deluxe capacity is ten rooms.

For a proposed three-night stay, eight rooms are already reserved on the first night, nine on the second, and all ten on the third.

Can we sell another Deluxe room for the whole stay?

No.

Availability must hold for every required night.

That conclusion follows from the business model, not from a particular database query.

The question we must answer before designing persistence is:

**Which facts can exist, change, or disappear independently?**

This is how we discover entity boundaries.

## 3. Entities, relationships, and cardinality

A relational database represents information through relations, commonly implemented as tables.

For our platform, a reasonable starting point includes hotels, room types, customers, reservations, and reservation items.

A hotel offers many room types.

Each room type belongs to one hotel.

A customer may make many reservations.

Each reservation belongs to a customer under the particular account model we've chosen.

These are one-to-many relationships.

### Why reservation items matter

Suppose reservation R-1042 contains two Deluxe rooms and one Standard room.

We could represent these as three independent reservations.

But that might be wrong.

The customer made one booking, received one confirmation, and perhaps paid one deposit.

Within that booking, individual accommodation commitments might still be canceled or changed separately.

A useful model is:

One reservation has many reservation items.

Each reservation item identifies a room type, quantity, agreed price, and potentially separate fulfillment state.

This effectively resolves a many-to-many relationship between reservations and room types.

The intermediate table also gives us somewhere to store facts belonging to the relationship itself.

This is a key modeling insight.

Sometimes a relationship is important enough to become an entity with its own attributes and lifecycle.

### What about one-to-one relationships?

One-to-one relationships can be useful when separating information with a distinct security boundary, optional lifecycle, or access pattern.

For example, a customer might have an optional billing profile.

But splitting every large table into several one-to-one tables merely for aesthetic reasons adds joins and operational complexity.

Use the relationship that expresses the actual domain.

Not the one that looks most elegant on a diagram.

## 4. Identity and business uniqueness

Let's discuss keys.

A primary key identifies a row.

But what should count as an identity?

Consider physical room 204 in the Grand Baltic hotel.

The number 204 isn't globally unique.

Another hotel may have its own room 204.

The combination of hotel and room number may be unique within the current business rules.

But even that combination can change if the property renumbers its rooms.

A stable surrogate primary key gives the physical room a persistent technical identity.

We can separately enforce uniqueness of room number within the hotel.

For example, the database can require that the combination of hotel ID and room number be unique.

These are different guarantees.

**Primary key:** Which record is this?

**Business uniqueness:** Which combinations must not coexist?

### Natural versus surrogate keys

A natural key comes from meaningful domain data.

A surrogate key is created primarily to identify the record, such as a generated integer or UUID.

Natural keys are attractive when their meaning, uniqueness, and stability genuinely hold.

But business identifiers often change.

Email addresses change. Products are recoded. Rooms are renumbered.

For many SaaS systems, stable surrogate identities plus separately enforced business uniqueness are a practical default.

That doesn't mean UUIDs are universally better than integers.

Generated integers are compact and can have good index locality.

UUIDs offer different generation and distribution properties, with storage and indexing trade-offs that depend on their version and generation scheme.

The important design decision is separating technical identity from mutable business descriptions.

## 5. Normalization: preventing the three anomalies

Return to our original flat reservation table.

It repeats the hotel name, hotel address, customer information, room description, and current room characteristics on every booking.

This design may make one reservation easy to display.

But maintaining it becomes dangerous.

### The update anomaly

The hotel's address changes.

Thousands of reservation rows contain the old address.

Updating every copy is expensive, and an incomplete update leaves conflicting information.

One current fact now exists in several inconsistent forms.

### The insertion anomaly

We want to register a hotel before it receives its first reservation.

But hotel information exists only inside reservation rows.

We cannot represent the new hotel without inventing a booking or introducing special cases.

The model wrongly requires two independent facts to exist together.

### The deletion anomaly

Suppose the last reservation for a hotel is deleted.

If that reservation also contains the only stored record of the hotel's identity and address, deleting one fact destroys another.

These are the classic motivations for relational normalization.

### Functional dependencies

There's a formal idea beneath the examples.

Suppose a hotel ID identifies one hotel with one current address.

Then, within our model, the hotel ID determines the current address.

We describe this as a **functional dependency**.

Now suppose reservation ID determines hotel ID, and hotel ID determines the hotel's current address.

If we repeatedly store the current hotel address in every reservation, we're maintaining an attribute whose real dependency belongs elsewhere.

Separating hotels from reservations reflects that dependency.

### The normal forms without turning them into a ritual

First Normal Form is concerned with representing data as relational attributes rather than smuggling independently meaningful collections into a single value.

For example, storing room IDs as the string `"101,102,108"` and repeatedly parsing that string is a poor substitute for representing the relationship explicitly.

Second Normal Form addresses dependencies on only part of a composite candidate key.

Suppose a reservation item is identified by reservation ID and room-type ID, while room-type name depends only on room-type ID. That name belongs to the room-type entity rather than being independently maintained on each reservation item.

Third Normal Form addresses further undesirable dependencies that allow non-key facts to determine other non-key facts, subject to its precise formal definition.

The hotel-address example captures the intuition.

For interviews, understanding the anomalies and functional dependencies is more valuable than chanting normal-form definitions without being able to apply them.

The goal is to store facts according to the dependencies that actually define them.

## 6. Historical snapshots are not necessarily bad normalization

Now return to the customer whose reservation price changed.

Didn't we just argue against repeating information?

Yes—but only when the repeated values represent the same independently maintained fact.

The hotel's current nightly rate and the price agreed for an existing reservation are not the same fact.

Their meanings differ.

One describes today's offering.

The other describes the historical transaction.

A reservation item may therefore preserve the agreed price, rate plan, currency, and relevant commercial terms.

Depending on the business, it may also preserve nightly price breakdowns, tax treatment, and other contractual details.

The reservation must remain interpretable after the hotel updates its current pricing.

The same principle applies to product descriptions on invoices, tax rates on past transactions, and exchange rates used in completed financial operations.

Historical facts shouldn't silently change when current reference data changes.

### Two forms of deliberate duplication

We should distinguish two situations.

**Historical snapshots** preserve information whose meaning is tied to a past event or agreement.

**Derived summaries** duplicate information that can be recalculated from authoritative source records, usually to improve query performance or support reporting.

Both can be legitimate.

But they have different correctness requirements.

A historical agreed price is part of the transaction's authoritative record.

A monthly reservation count might be a derived value that must be updated or rebuilt when underlying reservations change.

The question isn't whether a column is duplicated.

It's what the duplicate represents and how its correctness is maintained.

## 7. Building a useful hotel schema

Let's design a small relational structure.

The hotel table holds a stable identity, current name, and property timezone.

Room types belong to hotels and define categories such as Deluxe or Standard.

Customers have stable identifiers.

Reservations connect customers to hotels and define stay dates, booking status, and creation time.

Reservation items connect reservations to room types, describe quantities, and preserve agreed commercial information.

Physical room assignments can be modeled separately when necessary.

The detailed SQL implementation appears in the practical lab.

For listening, the important challenge is understanding the relationships the schema must enforce.

### Cross-hotel integrity

Suppose reservation R-1042 belongs to Hotel A.

Room type Deluxe-7 belongs to Hotel B.

Our reservation-item table references both records.

If it has one foreign key checking that R-1042 exists and another checking that Deluxe-7 exists, both checks can succeed.

Yet the combination is invalid.

The reservation item links a booking at Hotel A to a room type offered by Hotel B.

This is a subtle but important failure.

Independent foreign keys prove independent existence.

They don't automatically prove that two referenced records belong to the same hotel.

### Composite foreign keys

One solution is to carry the hotel ID into the reservation item and enforce consistency with both parent records.

The item references the combination of reservation ID and hotel ID.

It also references the combination of room-type ID and hotel ID.

Now PostgreSQL can reject a reservation item whose room type belongs to a different hotel.

This requires appropriate unique or primary-key constraints on the referenced combinations.

It also introduces some redundancy and indexing cost.

But that redundancy exists for a reason: it enables the database to enforce a cross-entity business invariant.

An alternative schema could encode ownership differently.

The general principle is that **relational constraints can enforce relationships among facts, not merely the existence of individual rows**.

## 8. Constraints: useful guarantees and their boundaries

Let's examine the most important constraints through the hotel example.

### `NOT NULL`

A reservation must refer to a hotel.

Therefore, its hotel ID should not be null.

But an assigned physical room might legitimately be unknown until check-in.

An optional room assignment may therefore permit null.

Nullability should express domain meaning.

Making everything optional creates ambiguous records.

Making everything mandatory prevents the representation of legitimate intermediate states.

### `UNIQUE`

A hotel may have only one room type with code `DELUXE`.

Another hotel may use the same code.

So a composite uniqueness rule on hotel ID and code expresses the business requirement.

In PostgreSQL, ordinary unique constraints generally treat nulls as distinct, permitting multiple null values under the relevant rules.

PostgreSQL also provides `NULLS NOT DISTINCT` when a different null-uniqueness policy is needed.

This is why a uniqueness rule must be designed together with nullability.

### `FOREIGN KEY`

A room type should not reference a nonexistent hotel.

A reservation item should not reference a nonexistent reservation.

Foreign keys enforce these relationships across different application writers.

They also introduce lifecycle decisions.

Should deleting a hotel delete every historical reservation?

Probably not.

Reservations may carry financial, legal, and operational significance long after a property becomes inactive.

An `ON DELETE CASCADE` rule can be appropriate for child records whose existence has no independent meaning.

It can be disastrous when historical business records should survive the deletion of their parent entity.

### `CHECK`

A reservation item must have positive quantity.

A reservation must have checkout after check-in.

A booked amount must not be negative in the relevant representation.

These are good candidates for row-local checks.

But a simple `CHECK` constraint isn't a general-purpose mechanism for coordinating arbitrary data across multiple rows or tables.

There are also semantic limitations.

A status constraint can ensure that the status is one of `pending`, `confirmed`, or `cancelled`.

It doesn't automatically enforce valid transitions.

A cancelled reservation becoming confirmed again may require an explicit workflow.

A permitted value isn't necessarily a permitted transition.

And a syntactically valid reservation isn't necessarily backed by available inventory.

### Why application validation still matters

Database constraints protect shared persistence.

Application validation protects user experience and catches problems earlier.

A customer's incorrect date range should normally receive a useful explanation rather than an unexplained database error.

But the database must still protect the invariant from imports, scripts, alternate services, and unexpected code paths.

Use both layers for their respective purposes.

## 9. Temporal modeling: dates are not timestamps

Now consider a guest checking in on November 12 and checking out on November 15.

Which nights are reserved?

November 12, 13, and 14.

The checkout date is excluded.

This is naturally represented as a **half-open interval**: November 12 inclusive, November 15 exclusive.

Half-open intervals are useful because adjacent stays can meet at the same boundary without overlapping.

A guest departing November 15 can be followed by another guest arriving November 15.

The first stay ends exactly where the next begins.

### Why SQL `DATE` is often appropriate

A hotel night is primarily a local calendar concept.

The business is selling accommodation for particular dates in the property's timezone.

Using UTC timestamps as the primary representation can complicate ordinary stay rules.

For check-in and checkout dates, SQL `DATE` is often the natural choice.

For events such as reservation creation or payment authorization, `TIMESTAMPTZ` is appropriate because these describe instants in time.

The hotel's IANA timezone, such as `Europe/Vilnius`, remains important for interpreting local business rules.

A fixed UTC offset isn't a complete timezone definition.

And a hotel night doesn't always correspond to exactly twenty-four elapsed hours across daylight-saving transitions.

Choose temporal types according to what the time means.

## 10. Two kinds of double booking

Can the database prevent a room from being sold twice?

Yes—but first we must define what kind of inventory we're selling.

### An assigned physical room

Suppose physical room 204 is booked from November 12 through the morning of November 15.

Another confirmed reservation for the same room from November 14 to November 17 would overlap.

PostgreSQL provides range types and exclusion constraints that can express this rule.

A GiST exclusion constraint can forbid two relevant records from having the same room identifier and overlapping date ranges.

The `&&` range operator represents overlap.

The `btree_gist` extension provides suitable GiST operator support for ordinary scalar equality comparisons.

We can apply the constraint only to reservation statuses that actually block inventory, such as held or confirmed.

This gives us a database-enforced invariant.

Concurrent application requests cannot simply bypass it by making their checks at inconvenient times.

### A pool of interchangeable rooms

Now imagine the hotel sells ten Deluxe rooms as one shared category.

Customers book the category rather than choosing physical rooms.

A single physical-room exclusion constraint doesn't express that inventory model.

We need to ensure that reservations never exceed available category capacity on any night of the stay.

A three-night reservation may affect three nightly inventory records.

Two transactions can compete for the last available unit on one of those nights.

Reading availability and then updating it in separate operations is not sufficient.

We need appropriate transactional coordination.

That may involve conditional updates, row locking, isolation levels, or another carefully designed inventory mechanism.

CS330-L03 will examine these mechanisms in depth.

For now, the durable distinction is:

**An exclusion constraint can protect non-overlapping occupancy of one identified resource. Pooled inventory needs a capacity invariant across a collection of resources and dates.**

Those are different data models.

## 11. Money and status: precision matters

A schema can be structurally sound and still misrepresent business values.

Consider money.

Storing a financial amount in binary floating-point can introduce representational error because many decimal fractions cannot be represented exactly.

For many financial applications, integer minor units or PostgreSQL `NUMERIC` provide more appropriate representations.

For example, €189.00 may be represented as 18,900 cents.

But not every currency uses two decimal places, and some calculations require greater precision than ordinary settlement units.

A complete monetary model defines currency, precision, rounding rules, and historical interpretation.

A three-character currency field is not automatically a validated currency code.

### State needs more than a list of labels

Now consider reservation status.

We can enforce membership in an allowed set.

But whether a transition from `cancelled` to `confirmed` is permitted depends on the business workflow.

A status transition may require additional authorization, inventory checks, or payment reconciliation.

The database can help enforce these rules, but a row-local status check doesn't express the entire workflow.

**Valid values, valid relationships, and valid state transitions are different guarantees.**

## 12. Denormalization with an explicit maintenance contract

Suppose our platform has millions of reservations.

The administration dashboard repeatedly asks how many confirmed bookings each hotel received this month.

Calculating the aggregate from authoritative reservations may initially be inexpensive.

At scale, repeatedly executing the same expensive aggregation might become costly.

We could maintain a summary table containing hotel ID, month, confirmed booking count, and gross booking value.

That is a derived representation.

It may improve reporting performance.

But now we have another correctness obligation.

What happens when a reservation is cancelled?

What happens when a historical booking is corrected?

What happens when a refund changes the financial interpretation?

Who updates the summary?

How fresh must it be?

Can it be rebuilt from authoritative data?

If the summary supports quarterly analytics, a short delay may be acceptable.

If it determines whether the final available room may be sold, stale data could cause an overselling bug.

The practical default is to normalize authoritative operational data first, then introduce derived representations when there is a measured reason and a defined maintenance policy.

Denormalization is a trade-off, not a moral failure.

## 13. The migration that took production down

Our schema has become more mature.

Now product management wants every reservation to record its booking channel: direct, partner, or corporate.

We have five million existing reservations and several running application versions.

The naïve migration introduces `booking_channel` as a mandatory column immediately.

But historical rows contain no value.

And older application instances may still insert reservations without the new field.

Even a migration with a default can introduce unintended historical semantics or operational locking costs.

A schema change is therefore not just a SQL statement.

It is a coordinated transition across application versions, stored data, database constraints, and live traffic.

### Expand

Introduce the column in a backward-compatible, initially nullable form.

Old application versions continue operating.

New versions can begin populating it.

The temporary flexibility is intentional.

### Migrate application behavior

Deploy compatible code to all relevant write paths.

That includes HTTP handlers, workers, importers, administration scripts, and scheduled jobs.

If we use a default value, it must have defensible business meaning.

Don't label historical partner bookings as direct merely because that's an easy default.

### Backfill existing data

Populate missing values.

On a large table, avoid assuming one enormous update is operationally harmless.

A production backfill may need batches, progress tracking, idempotent execution, and attention to WAL generation, replication lag, and locks.

### Enforce the new invariant

Once compatible writers are deployed and historical data is corrected, add the required constraint.

PostgreSQL supports introducing some constraints as `NOT VALID`, enforcing them for new or modified rows without immediately scanning the entire existing table.

Validation can occur separately.

For a non-null requirement, a validated check constraint may help prepare for a later `SET NOT NULL`, subject to PostgreSQL version and locking details.

The exact deployment sequence should be tested against the actual database.

### Contract

Only after incompatible old application versions are gone should obsolete compatibility paths or old schema representations be removed.

This overall pattern is commonly called **expand–migrate–contract**.

It often requires several deployments.

That's not overengineering.

It's recognizing that production databases have history, traffic, and independently deployed consumers.

### The operational cost of constraints and indexes

Foreign keys, uniqueness constraints, and indexes have benefits, but they aren't free.

Indexes consume storage and increase write-maintenance work.

Large schema changes can acquire locks or require substantial scans.

PostgreSQL's `CREATE INDEX CONCURRENTLY` can allow ordinary writes to continue during an index build, though it has additional operational requirements and may leave an invalid index after failure.

It also cannot run inside an ordinary transaction block.

These details matter because a logically correct design can still be deployed incorrectly.

Relational design has three dimensions:

**Logical correctness:** Are we representing the right facts?

**Integrity:** Are invalid values and relationships rejected?

**Operational behavior:** Can queries, writes, and migrations work safely at production scale?

A schema needs all three.

---

# The Oral Examination

Answer aloud before reading the solutions. For each question, explain the reasoning rather than naming a fashionable database pattern.

**Question 1 — The historical invoice**

A developer proposes removing the price and description from order items and always joining the product table for current information. They argue that normalization forbids duplication. What's wrong with this reasoning?

**Question 2 — The three-room reservation**

A customer books two Deluxe rooms and one Standard room, then cancels one Deluxe room. How would you model the booking and its individual accommodation commitments?

**Question 3 — The cross-hotel reference**

A reservation belongs to Hotel A, while its item references a room type belonging to Hotel B. Both foreign keys are individually valid. How could the database prevent this combination?

**Question 4 — The dangerous cascade**

A developer adds `ON DELETE CASCADE` from hotels to reservations. A hotel is removed from the platform, and its historical bookings disappear. What was the modeling mistake?

**Question 5 — Two kinds of inventory**

Why can an exclusion constraint prevent overlapping stays in a particular physical room but not automatically prevent overselling a category with ten interchangeable rooms?

**Question 6 — The million-row migration**

You need to introduce a mandatory booking-channel field into a live reservations table while multiple application versions may coexist. Describe a safe migration strategy.

**Question 7 — The deceptively valid value**

A reservation status is one of the allowed values, yet the transition into that status was illegal. Why doesn't a simple `CHECK` constraint solve this?

**Question 8 — The senior design question**

Your team wants to duplicate monthly reservation statistics for performance. Under what conditions is this reasonable, and what guarantees must accompany the design?

---

# Solutions and Discussion

## Solution 1 — Current and historical facts

The developer is confusing a product's current catalogue information with the terms of a completed transaction.

An order item should preserve the commercial details relevant to the historical agreement.

Those fields are not merely redundant copies of the current product record; they have a distinct temporal meaning.

The exact snapshot requirements depend on business and legal rules.

## Solution 2 — One booking, several items

A reservation can represent the overall booking, with reservation items representing individual accommodation commitments.

Each item can reference a room type, quantity, price, and relevant state.

Partial cancellation can affect an item without necessarily cancelling the entire booking.

If the business treats every room as an independent agreement, a different grouping model may be justified.

The choice follows the domain lifecycle.

## Solution 3 — Composite relationship integrity

Independent foreign keys establish existence, not shared hotel ownership.

One approach carries `hotel_id` in the item and uses composite foreign keys referencing the reservation's and room type's corresponding hotel-scoped identifiers.

The referenced combinations require suitable uniqueness constraints.

Other schema designs may express the same ownership invariant differently.

## Solution 4 — Deleting the parent shouldn't erase history

The schema confused an inactive hotel with a hotel whose historical existence should be erased.

Reservations may have independent financial, legal, and operational meaning.

A lifecycle status or carefully governed deletion policy may be more appropriate.

Cascading deletion is suitable when child records genuinely have no independent reason to survive their parent.

## Solution 5 — Different resource models

A physical-room exclusion constraint prevents overlapping date ranges for one identified room.

Category inventory involves capacity shared by interchangeable units over several nights.

It requires coordinating allocations across the relevant inventory records and concurrent transactions.

A simple physical-room overlap rule cannot enforce pooled capacity.

## Solution 6 — Expand, migrate, enforce, contract

Add the column compatibly, deploy all writers to populate it, backfill historical records in manageable batches, validate the new invariant, then remove obsolete compatibility behavior.

Consider application-version coexistence, locks, write amplification, replication, and the exact PostgreSQL version.

Avoid treating a large production migration as one atomic code deployment.

## Solution 7 — Values aren't transitions

A `CHECK` constraint can restrict the set of values a row may contain.

A state transition depends on previous state, current state, and potentially other records.

Application logic and transactional database mechanisms must enforce the transition contract.

## Solution 8 — Derived data requires maintenance rules

A summary can be useful when it materially improves read performance or supports analytical workloads.

But its authoritative source, freshness requirement, update mechanism, recovery strategy, and rebuildability must be explicit.

A dashboard may tolerate eventual consistency where an inventory commitment cannot.

---

# The Mental Model Worth Keeping

When designing a relational schema, ask five questions:

**Identity:** What makes this entity the same entity over time?

**Meaning:** Which facts belong to it, and which apparently similar facts actually mean different things?

**Relationships:** How do the entities depend on one another, and what cardinalities and lifecycles follow?

**Invariants:** Which invalid states can the database itself prevent, and which require coordinated transactions?

**Evolution:** Can the representation change safely while old data and application versions still exist?

A good schema doesn't merely make today's queries convenient.

**It represents the business accurately, protects important invariants, preserves necessary history, and remains possible to evolve.**

# Next Lecture — CS330-L02: SQL and Query Performance

We've designed a schema that expresses meaningful business facts.

But what happens when those tables contain tens of millions of rows?

Why does one SQL query finish in milliseconds while another takes seconds?

Why can adding an index sometimes make performance worse?

And why does PostgreSQL choose a query plan that looks obviously wrong to a human?

In the next lecture, we'll study how relational databases physically find, combine, and return information: B-tree indexes, selectivity, query planning, joins, execution plans, and performance diagnosis.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Let PostgreSQL Protect the Business

The following experiments are intended for a disposable PostgreSQL database. Do not run destructive schema changes against a production database.

## Experiment A — A small but meaningful hotel schema

Start with hotels and room types:

```sql
CREATE TABLE hotels (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL,
  timezone TEXT NOT NULL
);

CREATE TABLE room_types (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  hotel_id BIGINT NOT NULL REFERENCES hotels(id),
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  max_guests INTEGER NOT NULL CHECK (max_guests > 0),

  UNIQUE (hotel_id, code),
  UNIQUE (id, hotel_id)
);
```

The second unique constraint supplies a composite referenced key for hotel-scoped relationships. It is intentionally redundant with the single-column primary key from a pure uniqueness perspective.

Add customers and reservations:

```sql
CREATE TABLE customers (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email TEXT NOT NULL,
  display_name TEXT NOT NULL
);

CREATE TABLE reservations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  hotel_id BIGINT NOT NULL REFERENCES hotels(id),
  customer_id BIGINT NOT NULL REFERENCES customers(id),

  check_in DATE NOT NULL,
  check_out DATE NOT NULL,

  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'confirmed', 'cancelled')),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CHECK (check_out > check_in),
  UNIQUE (id, hotel_id)
);
```

We deliberately haven't made customer email unique. Whether email identifies a login account, booking contact, or person is a business decision.

Finally, add reservation items that must belong to the same hotel as both their parent reservation and referenced room type:

```sql
CREATE TABLE reservation_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

  reservation_id BIGINT NOT NULL,
  hotel_id BIGINT NOT NULL,
  room_type_id BIGINT NOT NULL,

  quantity INTEGER NOT NULL CHECK (quantity > 0),

  quoted_total_minor BIGINT NOT NULL
    CHECK (quoted_total_minor >= 0),

  currency CHAR(3) NOT NULL,

  FOREIGN KEY (reservation_id, hotel_id)
    REFERENCES reservations(id, hotel_id),

  FOREIGN KEY (room_type_id, hotel_id)
    REFERENCES room_types(id, hotel_id)
);
```

**Challenge:** Create two hotels, one room type at each hotel, and one reservation belonging to Hotel A. Attempt to attach a room type from Hotel B to that reservation.

Explain which constraint rejects the combination.

## Experiment B — Uniqueness has scope

Insert a `DELUXE` room type into Hotel A.

Try inserting another `DELUXE` room type into the same hotel.

Then insert `DELUXE` into Hotel B.

The first duplicate should fail under the hotel-scoped uniqueness rule. The second hotel's code should be allowed.

**Challenge:** Explain why a global `UNIQUE(code)` constraint would encode the wrong business rule.

## Experiment C — Valid dates are not enough

Insert a reservation with check-in on November 15 and checkout on November 12.

The row-local date constraint should reject it.

Now insert two reservations for the same room type covering overlapping dates.

Those rows may both be valid under the current schema.

Why?

Because our schema hasn't yet established an inventory-capacity constraint.

**Challenge:** Explain the difference between a valid date interval and a valid allocation of scarce accommodation.

## Experiment D — Prevent overlapping physical-room assignments

PostgreSQL can enforce non-overlapping occupancy for a specific assigned room using a range exclusion constraint.

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE assigned_stays (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

  room_id BIGINT NOT NULL,
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,

  status TEXT NOT NULL
    CHECK (status IN ('held', 'confirmed', 'cancelled')),

  CHECK (check_out > check_in),

  EXCLUDE USING gist (
    room_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
  )
  WHERE (status IN ('held', 'confirmed'))
);
```

For a self-contained experiment, this table uses only the room identifier without declaring the full physical-room table. A production schema should establish the appropriate referential relationships.

Try inserting two confirmed stays for the same room with overlapping dates.

Then try two adjacent stays where the first checkout date equals the second check-in date.

Finally, create an overlapping canceled reservation.

**Challenge:** Why is the half-open interval important? Why does the status condition change which rows participate in the exclusion rule?

## Experiment E — The historical-price distinction

Create a conceptual pricing model containing current room-type rates and agreed reservation-item prices.

Change the current room rate after a reservation has been confirmed.

Verify that the reservation item's agreed price does not change.

**Challenge:** Explain why this is not simply accidental duplicate data.

## Experiment F — A safe mandatory-column migration

Start with an existing reservations table.

Add an optional booking-channel column:

```sql
ALTER TABLE reservations
ADD COLUMN booking_channel TEXT;
```

Update the application so every relevant writer populates the field.

For a small test dataset, backfill nulls:

```sql
UPDATE reservations
SET booking_channel = 'legacy'
WHERE booking_channel IS NULL;
```

Now introduce a constraint without immediately validating historical rows:

```sql
ALTER TABLE reservations
ADD CONSTRAINT booking_channel_present
CHECK (booking_channel IS NOT NULL) NOT VALID;
```

Validate it separately:

```sql
ALTER TABLE reservations
VALIDATE CONSTRAINT booking_channel_present;
```

Where justified by the supported PostgreSQL version and tested locking behavior, the column can subsequently be made formally `NOT NULL`.

The example demonstrates the stages. A real five-million-row migration should use controlled batching and deployment coordination rather than blindly copying these commands into production.

**Challenge:** Why should compatible application writers be deployed before the new constraint starts rejecting missing values?

## Experiment G — Index creation under live traffic

Consider an index supporting common hotel/date lookups:

```sql
CREATE INDEX CONCURRENTLY
idx_reservations_hotel_date
ON reservations (hotel_id, check_in);
```

PostgreSQL supports concurrent index creation to avoid blocking ordinary table writes for the entire build, but the process has important operational trade-offs and cannot run inside a regular transaction block.

A failed concurrent index build can leave an invalid index requiring attention.

**Challenge:** Why does an index improve some reads while increasing storage and write-maintenance costs?

---

# Further Reading

Official PostgreSQL references:

- **Constraints:** https://www.postgresql.org/docs/current/ddl-constraints.html
- **Range Types and Exclusion Constraints:** https://www.postgresql.org/docs/current/rangetypes.html
- **Numeric Types:** https://www.postgresql.org/docs/current/datatype-numeric.html
- **Date and Time Types:** https://www.postgresql.org/docs/current/datatype-datetime.html
- **ALTER TABLE and Constraint Validation:** https://www.postgresql.org/docs/current/sql-altertable.html
- **CREATE INDEX and Concurrent Index Builds:** https://www.postgresql.org/docs/current/sql-createindex.html

Related chapters:

- CS330-L02 — SQL and Query Performance
- CS330-L03 — Transactions: When Correct Operations Produce Incorrect Results
- CS340-L03 — Document Databases and MongoDB

---

## Dense Cheatsheet — Interview Glance Card

```text
CS330-L01 — RELATIONAL DATABASE DESIGN

CORE MODEL
  Schema = representation of business facts and relationships
  Valid SQL + valid rows can still encode the wrong business model
  Design identity, meaning, integrity, and evolution together

DOMAIN DISTINCTIONS
  Room type != physical room
  Reservation != reservation item
  Inventory per night != current room-rate listing
  Current rate != historically agreed price
  Current name/address != entity identity

ENTITY BOUNDARIES
  What can exist independently?
  What can change independently?
  What can be deleted independently?
  What owns the relationship's attributes?

RELATIONSHIPS
  1:N — hotel -> room types
  1:N — reservation -> reservation items
  M:N — resolved through intermediate entity
  Reservation item stores quantity, price, rate plan, state
  1:1 useful for true lifecycle/security/ownership boundaries

IDENTITY
  Primary key = stable row identity
  Business UNIQUE = real-world uniqueness constraint
  Natural key = meaningful business-derived key
  Surrogate key = generated technical identifier
  Stable surrogate PK + separate business UNIQUE often practical
  Room number unique within hotel, not globally

NORMALIZATION
  Update anomaly — multiple copies of one current fact
  Insertion anomaly — cannot store one fact without another
  Deletion anomaly — removing one fact destroys another
  Functional dependency — key determines attributes
  1NF — relational values, not comma-separated lists
  2NF — no improper dependency on part of composite key
  3NF — address relevant transitive/non-key dependencies
  Normalize independently maintained operational facts

HISTORY
  Historical agreed price is a distinct fact from current rate
  Preserve snapshots needed for invoices / contracts / audits
  Historical duplication != automatically normalization defect

CONSTRAINTS
  NOT NULL — required value
  UNIQUE — prohibited duplicates within defined scope
  FOREIGN KEY — referenced existence / relationship
  CHECK — row-local valid-value or relationship rule
  Composite FKs can enforce same-hotel ownership
  CHECK value membership != legal state transition
  Application validation improves UX
  DB constraints protect all writers

TENANT / HOTEL INTEGRITY
  Reservation belongs to Hotel A
  Room type belongs to Hotel B
  Independent FKs may both pass
  Composite FK using hotel_id can prevent mismatch
  Cross-entity invariant needs appropriate schema structure

TEMPORAL MODELING
  Hotel stay = half-open [check_in, check_out)
  Checkout date excluded
  Adjacent stays can meet without overlap
  DATE for property-local calendar nights
  TIMESTAMPTZ for event instants
  IANA timezone for property-local rules
  A hotel night need not be exactly 24 elapsed hours

INVENTORY
  Assigned room:
    EXCLUDE USING gist (room_id WITH =,
      daterange(check_in, check_out, '[)') WITH &&)
    Conditional on blocking status
  Room-type pool:
    Multiple interchangeable units per night
    Capacity may span multiple date rows
    Needs transactional capacity enforcement
  Physical-room overlap != pooled inventory model

MONEY / STATUS
  Prefer exact NUMERIC or defined integer minor units
  Floating point can be unsuitable for financial amounts
  Currency precision/rounding must be explicit
  CHAR(3) != valid currency-code guarantee
  Allowed status != allowed transition

DENORMALIZATION
  Derived summaries can improve reporting
  Define source of truth and freshness
  Define update, repair, and rebuild mechanisms
  Do not drive scarce inventory from stale reports
  Govern duplicated operational data

MIGRATIONS
  EXPAND — compatible schema change
  MIGRATE — deploy writers + backfill data
  ENFORCE — validate constraints after compatibility
  CONTRACT — remove old representation last
  Batch large backfills; mind WAL, locks, replication
  NOT VALID + VALIDATE can separate enforcement/scan phases
  CREATE INDEX CONCURRENTLY reduces write blocking
  Indexes have write/storage costs and operational risks

THREE DIMENSIONS
  Logical correctness — represent right facts
  Integrity — reject invalid combinations
  Operations — perform and evolve safely under load

SENIOR INTERVIEW LINE
  "I'd identify stable domain identities and independent facts,
   model cardinalities and historical meaning, enforce as much
   integrity as appropriate at the persistence boundary, and
   ensure schema changes are compatible with live deployments."

MENTAL MODEL
  Identity -> Meaning -> Relationships -> Invariants -> Evolution
```
