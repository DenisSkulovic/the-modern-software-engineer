---
id: CS430-L04
course: CS430
title: "Microservices, Events, and Service Boundaries"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S10]
prev: CS430-L03
next: CS430-L05
---







# CS430 — Distributed Systems and Reliable Workflows

## Lecture 04: Microservices, Events, and Service Boundaries

*How splitting a straightforward application into independent services can transform one database transaction into a distributed coordination problem—and when that trade is actually worth making.*

---

# 1. The Refactoring That Broke Reservations

Your hotel-booking SaaS has been growing for three years.

The original application was a fairly conventional Node.js backend. It contained modules for reservations, inventory, payments, notifications, pricing, and hotel management. All modules shared one PostgreSQL database, and everything deployed together.

The codebase wasn't perfect. Some modules were tightly coupled, deployments were becoming increasingly complicated, and occasionally one team's changes disrupted another team's work.

The engineering director proposes an architectural modernization.

*Let's split the application into microservices.*

The idea sounds excellent. Billing can deploy independently of reservations. Inventory can scale according to its own workload. The notification service can fail without bringing down the booking API.

Three months later, the architecture looks considerably more sophisticated:

```text
                       API GATEWAY
                            |
           +----------------+----------------+
           |                |                |
           v                v                v
     Reservation         Inventory         Billing
       Service            Service          Service
           |                |                |
           v                v                v
       Database         Database         Database
           |                |                |
           +----------------+----------------+
                            |
                       EVENT BROKER
                            |
                            v
                     Notification
                        Service
```

The system now contains several independently deployable services, separate databases, asynchronous event communication, and dedicated deployment pipelines.

The architecture diagrams are beautiful.

Unfortunately, customers have started experiencing something strange.

A customer successfully reserves the final available hotel room. The Inventory Service records the allocation and returns success.

The Reservation Service then requests payment authorization from Billing.

Billing successfully authorizes the payment but suffers a network interruption before returning its response.

The Reservation Service times out.

It doesn't know whether payment succeeded, so the booking remains pending.

Meanwhile, an inventory-hold expiration worker releases the room because the reservation wasn't confirmed within its allotted time.

Another customer books that room.

Several minutes later, the payment provider sends a webhook confirming the original authorization.

The first customer has now authorized payment for a room the system no longer holds.

Every service behaved more or less according to its local implementation. Yet the combined system failed to preserve the business workflow.

Here's the important part: before the microservices migration, much of the reservation and inventory logic could be coordinated inside one PostgreSQL transaction.

Now the same business operation spans several independently committed databases and an external payment provider.

We've gained independent deployment and scaling. But we've lost a convenient shared transactional boundary.

**The cost of distributing a system isn't merely network latency. It's the loss of simple, local coordination over operations that previously shared one authority.**

Today we'll investigate how to draw useful service boundaries, distinguish events from commands, coordinate cross-service workflows, and decide whether microservices are actually justified.

---

# 2. What Makes Something a Microservice?

Suppose your application contains these modules:

```text
src/
  reservations/
  inventory/
  billing/
  hotels/
  notifications/
```

Each module has its own controllers, services, and persistence code.

Is this a microservices architecture?

No. It's a modular application, potentially a modular monolith.

Now imagine packaging each module into a separate Docker container.

Are they microservices?

Not automatically.

What if all containers access the same tables, deploy together, and depend on one another's internal implementation details?

You've distributed the runtime without meaningfully separating the responsibilities.

A useful microservice has several characteristics:

- It owns a meaningful business capability.
- It exposes an intentional interface.
- It can generally evolve and deploy independently.
- It controls its own persistent business state.
- Other services interact with it through contracts rather than manipulating its internal data.

The word *micro* is slightly misleading. The objective isn't to make every service tiny.

A service containing 30,000 lines of cohesive billing logic may be a better architectural boundary than five services containing 6,000 lines each and constantly calling one another.

The more useful unit is the **business capability**.

Reservation management is a capability. Payment processing is another. Hotel catalogue management may be another.

But `DatabaseService`, `ValidationService`, and `UtilityService` aren't automatically meaningful microservices merely because they contain reusable functionality.

Splitting by technical layer can produce an architecture in which every ordinary business operation requires communication across several services.

```text
HTTP Service
     |
     v
Validation Service
     |
     v
Business Logic Service
     |
     v
Database Service
```

That's often just a traditional layered application with network calls inserted between its layers.

Congratulations: you've converted function calls into distributed failure opportunities.

A meaningful service boundary should correspond to a reason for independent ownership, change, scaling, deployment, or operational isolation.

---

# 3. Why the Modular Monolith Is Such a Strong Starting Point

Let's revisit the modular monolith from the web engineering courses (CS230, SE240, SE310).

```text
               NODE.JS APPLICATION
                        |
       +----------------+----------------+
       |                |                |
       v                v                v
  Reservations       Inventory         Billing
       |                |                |
       +----------------+----------------+
                        |
                        v
                    PostgreSQL
```

The modules remain conceptually separate, but they execute in one application and can participate in shared database transactions where the architecture permits it.

Suppose confirming a reservation requires an inventory allocation and a reservation record.

An application service can coordinate both:

```typescript
await dataSource.transaction(async manager => {
  await inventoryService.allocate(manager, booking);
  await reservationService.confirm(manager, booking);
});
```

If either operation fails, the transaction rolls back.

We don't need a network protocol between reservations and inventory. We don't need to reconcile independently committed states. We can use PostgreSQL constraints, locks, and transactional guarantees directly.

That's a genuine architectural advantage.

Of course, sharing a database can also encourage bad coupling. If every module freely modifies every table, dependencies become difficult to understand.

But that's a problem of modular discipline, not an inherent consequence of monolithic deployment.

A modular monolith can establish explicit public interfaces, restrict cross-module imports, and assign clear ownership of tables and business rules.

It can also use domain events internally when that makes the design clearer, without immediately introducing distributed message delivery.

### The deployment disadvantage

A monolith normally deploys as one application.

If Billing changes, you may need to redeploy the entire process. If a shared runtime crashes, multiple capabilities may be affected.

Different modules also share application-level scaling and runtime resources.

These costs become more important as the product and engineering organization grow.

However, don't assume they automatically outweigh the advantages of local coordination.

For a small team maintaining one cohesive SaaS product, a well-structured modular monolith is frequently a more efficient architecture than a fleet of microservices.

The relevant question is not whether microservices are modern.

It's whether the benefits of independent operation exceed the new coordination costs.

---

# 4. Finding Boundaries Through Business Invariants

Suppose we need to decide whether reservations and inventory belong in separate services.

We could begin by counting lines of code, comparing database table sizes, or examining team ownership.

Those are useful signals, but I'd start somewhere else.

**Which business rules require these components to change state together?**

Consider the invariant:

> A confirmed reservation must have successfully allocated the required inventory.

If reservation confirmation and inventory allocation live in one database, we can often enforce the relationship using a local transaction.

If they live in separate services, the guarantee becomes more complicated.

The Reservation Service cannot simply roll back the Inventory Service's committed transaction.

Instead, the system needs an explicit protocol for intermediate states, success, failure, and recovery.

This suggests an architectural principle:

**Operations that must maintain strong invariants together are candidates for sharing a consistency boundary.**

A *consistency boundary* identifies the state that must be coordinated under a particular correctness guarantee.

It doesn't necessarily correspond to one table or one class.

In domain-driven design terminology, an aggregate often provides a related concept: a cluster of domain state whose invariants are enforced through a defined transactional boundary.

But aggregates and microservices aren't synonyms. One service may own many aggregates, and a single business workflow may span several.

### A useful boundary investigation

Imagine three capabilities:

**Reservations** manages booking requests, lifecycle states, amendments, and cancellations.

**Inventory** manages capacity, allocations, holds, and room availability.

**Notifications** sends confirmation emails and other messages.

Which relationships are tightly coupled?

Reservations and inventory interact during important transactional decisions. Whether a booking can become confirmed depends on inventory.

Notifications are different.

An email failure should normally not invalidate an otherwise successful reservation.

Notification delivery has different scaling requirements, failure modes, and operational priorities.

That makes notifications a natural candidate for asynchronous separation.

Reservations and inventory require more careful consideration.

They can absolutely become separate services, especially when inventory is a substantial independent product capability serving multiple booking channels.

But the separation creates a coordination protocol that must be designed explicitly.

This is why drawing service boundaries from organizational charts or noun lists can be misleading.

A domain relationship that looks simple on a diagram may hide a strong transactional dependency.

---

# 5. Data Ownership: The Rule That Makes Service Boundaries Real

Imagine the Inventory Service owns the `room_inventory` table.

The Reservation Service needs availability data.

The easiest implementation is obvious:

```sql
SELECT remaining
FROM inventory.room_inventory
WHERE room_type_id = 42;
```

Why bother calling Inventory through an API when the table is right there?

Because if Reservation directly depends on Inventory's internal schema, the supposed boundary begins to disappear.

Inventory can no longer change its database representation independently.

Perhaps it wants to replace one inventory row per day with a more sophisticated allocation model. Perhaps it wants to introduce Redis-backed read projections or a different persistence technology.

If other services directly query its internal tables, every such change becomes a coordinated migration.

A more meaningful boundary looks like:

```text
Reservation Service
        |
        v
Inventory API / Commands
        |
        v
Inventory Service
        |
        v
Inventory-Owned Tables
```

The Inventory Service owns the rules for modifying its data.

Other services request operations through its public contract.

### Database per service doesn't necessarily mean server per service

There's an important practical nuance.

Service data ownership doesn't require provisioning a separate physical PostgreSQL server for every microservice.

Two services might use different PostgreSQL databases or schemas on shared infrastructure.

For example:

```text
PostgreSQL Server
    |
    +-- reservations schema
    |
    +-- billing schema
    |
    +-- inventory schema
```

Different credentials and permissions can help enforce ownership.

The important rule is that each service controls its own data and transactional boundaries.

However, sharing one physical database server still creates infrastructure coupling. An outage or resource bottleneck in that server may affect several services.

Logical independence and physical independence are different dimensions.

### The reporting problem

Here's the downside.

The administration dashboard wants a report combining reservations, payment statuses, hotel names, and inventory information.

In a monolith, perhaps one SQL query joins four tables.

With separately owned databases, that direct join may no longer be appropriate.

Now we need another strategy.

And this is where service boundaries begin affecting not only writes, but reads.

---

# 6. Reading Data Across Service Boundaries

Suppose the frontend requests a reservation summary containing:

```json
{
  "reservationId": "R-10842",
  "hotelName": "Baltic Grand",
  "paymentStatus": "authorized",
  "roomType": "Deluxe"
}
```

Those fields belong to several capabilities.

How do we assemble the response?

### Option A — API composition

An application-facing service calls the relevant owners and combines their results.

```text
Reservation Details API
          |
          +-- Reservation Service
          |
          +-- Hotel Service
          |
          +-- Billing Service
          |
          v
     Combined Response
```

This is relatively straightforward and keeps ownership clear.

But it introduces runtime dependencies.

If Billing takes three seconds to respond, the entire reservation-details request may become slow.

If Billing is unavailable, we must decide whether to return a partial response, cached status, or error.

And if the calls occur sequentially, their latencies accumulate.

Parallel calls can reduce the critical path, but they also generate simultaneous downstream load.

### Option B — Materialized read model

Instead of repeatedly assembling information through live service calls, the system can maintain a dedicated projection.

For example:

```text
Reservation Confirmed Event ----+
                                |
Payment Authorized Event -------+--> Reservation Read Model
                                |
Hotel Renamed Event ------------+
```

The read model might contain the information needed by a particular dashboard:

```text
reservation_id
hotel_name
room_type
payment_status
reservation_status
```

Now one query can retrieve the response.

This resembles the read-model side of **Command Query Responsibility Segregation**, or CQRS.

CQRS broadly separates models used to change authoritative state from models optimized for reading it.

The read model may be denormalized and updated asynchronously.

That creates excellent query performance for suitable workloads, but it also creates replication and consistency concerns.

The dashboard might briefly show an older payment status.

Once again, the correct choice depends on the business contract.

For operational decisions such as issuing a refund, the application should consult authoritative state rather than blindly trusting an asynchronous projection.

For a general dashboard, modest projection lag may be acceptable.

**Separating data ownership usually makes cross-domain queries more expensive architecturally, even when it makes individual services easier to evolve.**

---

# 7. Synchronous Communication: The Distributed Function Call

The simplest way for one service to use another is usually a synchronous request.

```typescript
const allocation = await inventoryClient.allocate({
  reservationId,
  roomTypeId,
  checkIn,
  checkOut
});
```

The Reservation Service waits for Inventory to return a result.

This is convenient because the code resembles an ordinary function call.

But CS430-L01 taught us why that resemblance is dangerous.

The call can time out after Inventory has committed the allocation.

The caller cannot necessarily determine whether the operation succeeded.

Retries can duplicate effects unless the protocol supports idempotency.

And the Reservation Service now depends on Inventory's availability during the request.

### Cascading dependencies

Imagine:

```text
Reservation
    |
    v
Inventory
    |
    v
Pricing
    |
    v
Hotel Configuration
```

A reservation requires a successful response from each service.

Even if every dependency is individually reliable, the complete operation may be more fragile because it requires all of them to function within the request's deadline.

Latency also accumulates, especially when calls are sequential.

This is sometimes called a *chatty* service architecture: an ordinary business operation involves many fine-grained network interactions.

The cure isn't necessarily to make every communication asynchronous.

Synchronous requests are appropriate when the caller genuinely needs an immediate answer.

The goal is to avoid distributing operations across service boundaries without understanding the availability and latency consequences.

---

# 8. Events: Communicating What Happened

An alternative is event-driven communication.

Instead of directly instructing every downstream service to perform work, a service can publish a fact about something that happened.

For example:

```json
{
  "eventId": "evt-92831",
  "eventType": "ReservationConfirmed",
  "reservationId": "R-10842",
  "version": 7,
  "occurredAt": "2026-10-25T18:42:00Z"
}
```

The event communicates that Reservation R-10842 became confirmed.

Other services can react:

```text
                Reservation Service
                         |
                         v
                ReservationConfirmed
                         |
               +---------+---------+
               |                   |
               v                   v
         Notification          Analytics
           Service              Service
```

The Reservation Service doesn't need to know how Analytics updates its reports or which email provider Notifications uses.

That can be a useful form of decoupling.

### Events versus commands

These concepts are often confused.

A **command** requests an action:

```text
AuthorizePayment
ReserveInventory
SendConfirmationEmail
```

An **event** reports a fact:

```text
PaymentAuthorized
InventoryReserved
ReservationConfirmed
```

The difference is semantic.

A command has an intended recipient or responsible capability.

An event can have multiple interested consumers.

For example, `PaymentAuthorized` may be consumed by Reservations, Accounting, and Analytics.

But an event name doesn't guarantee that the described fact is durable or that consumers receive it exactly once.

A well-designed event should represent something the publishing service can truthfully assert.

Publishing `ReservationConfirmed` before inventory is actually secured would be a serious contract mistake.

### Event contracts are APIs

Events need stable schemas, versioning policies, and meaningful identifiers.

A consumer must know what each field means.

Does `amount` represent cents, euros, or a decimal currency amount?

Does `status = confirmed` mean inventory is allocated, payment is authorized, or merely that the user clicked Confirm?

A schema can be syntactically valid while conveying ambiguous business semantics.

Events are shared contracts just as HTTP APIs are.

They should be designed and evolved with similar care.

---

# 9. The Dual-Write Problem: Why Publishing Events Isn't Simple

Suppose the Reservation Service creates a reservation and publishes an event.

A naive implementation might look like:

```typescript
await reservationRepository.confirm(reservationId);

await eventBroker.publish({
  type: "ReservationConfirmed",
  reservationId
});
```

What happens if the database write succeeds but event publication fails?

The reservation is confirmed, but downstream services never learn about it.

Notifications may never send confirmation.

Analytics may never include the booking.

Now reverse the order.

```typescript
await eventBroker.publish(event);

await reservationRepository.confirm(reservationId);
```

What happens if publication succeeds but the database transaction fails?

Consumers receive an event describing a reservation that wasn't actually confirmed.

Neither order is sufficient.

This is the **dual-write problem**, which we briefly encountered in Sessions 1 and 6.

The difficulty is that PostgreSQL and the message broker are independent systems.

An ordinary PostgreSQL transaction cannot atomically commit a separate Redis, Kafka, or cloud messaging operation.

### The transactional outbox

One widely used solution is to write the event into PostgreSQL alongside the business change.

```sql
BEGIN;

UPDATE reservations
SET status = 'confirmed'
WHERE id = 'R-10842';

INSERT INTO outbox_events (
  event_id,
  aggregate_id,
  event_type,
  payload
)
VALUES (
  'evt-92831',
  'R-10842',
  'ReservationConfirmed',
  '{"reservationId":"R-10842"}'
);

COMMIT;
```

Now the reservation update and event record succeed or fail together.

A separate process publishes committed outbox records to the message broker.

```text
               Reservation Service
                       |
                       v
              PostgreSQL Transaction
                       |
                 +-----+-----+
                 |           |
                 v           v
             Reservation   Outbox Event
                 |           |
                 +-----+-----+
                       |
                     COMMIT
                       |
                       v
                 Outbox Relay
                       |
                       v
                  Message Broker
                       |
                       v
                  Consumers
```

This solves the problem of losing the event intent when the database commit succeeds.

But it doesn't guarantee that the broker receives every event exactly once.

Suppose the relay publishes an event successfully, then crashes before marking the outbox record as delivered.

On restart, it may publish the same event again.

Therefore, consumers must tolerate duplicate delivery.

We developed that principle thoroughly in SE320-L03.

### Polling versus change-data capture

The relay can periodically query the outbox table for unpublished events.

Alternatively, change-data-capture technology can observe committed database changes through PostgreSQL's logical decoding mechanisms and publish them downstream.

Tools such as Debezium are commonly used for this style of integration.

The approaches have different operational characteristics.

Polling is conceptually simple but requires careful handling of concurrency, polling intervals, database load, and event ordering.

Log-based capture can avoid repeated polling queries and integrate naturally with streaming infrastructure, but it introduces connector management, replication slots, schema evolution, and recovery requirements.

Neither eliminates the possibility of duplicate delivery.

And neither guarantees application-level ordering without an explicit ordering strategy.

---

# 10. Ordering: A Subtle Problem Hidden in Event Streams

Imagine a reservation undergoes three transitions:

```text
Version 7: Pending
Version 8: Confirmed
Version 9: Cancelled
```

The Reservation Service publishes:

```text
ReservationConfirmed
ReservationCancelled
```

A downstream projection processes events concurrently.

The cancellation event finishes first.

Then the delayed confirmation event arrives.

If the consumer simply overwrites its local status, it may end up showing:

```text
status = confirmed
```

even though the authoritative reservation is cancelled.

Every event was valid when published.

The problem was their application order.

### Version-aware processing

One defense is attaching a monotonically increasing aggregate version.

```json
{
  "eventId": "evt-92832",
  "reservationId": "R-10842",
  "version": 9,
  "eventType": "ReservationCancelled"
}
```

A consumer can compare the event version with its last applied version.

For a projection representing the latest complete state, older versions can be ignored after a newer authoritative snapshot has been safely applied.

For consumers applying incremental deltas, merely accepting the highest version may be insufficient. Missing intermediate events may need to be fetched or processed in order.

The right strategy depends on whether events describe complete state or state transitions.

Other approaches include partitioning events by aggregate ID, enforcing ordered processing, or using an event log with explicit sequence guarantees.

A message broker may preserve order within a partition or queue under defined assumptions, but concurrent consumers, failures, and retries can still complicate processing.

**Event ordering must be designed around the state transitions consumers perform—not assumed from the fact that messages were originally published in order.**

---

# 11. Sagas: A Business Operation Without One Global Transaction

We now reach the main architectural problem from our opening incident.

Suppose booking a hotel requires:

1. Securing inventory.
2. Authorizing payment.
3. Confirming the reservation.
4. Sending confirmation.

Inventory, Billing, and Reservations each own their database.

We cannot simply wrap all three services in one ordinary PostgreSQL transaction.

One approach is a **saga**.

A saga coordinates a sequence of local transactions, allowing the overall business workflow to progress through multiple services.

Each participating service commits its own changes.

When a later operation cannot complete, the workflow may invoke compensating actions for earlier successful steps.

Consider:

```text
Create Pending Reservation
            |
            v
      Hold Inventory
            |
            v
     Authorize Payment
            |
            v
    Confirm Reservation
            |
            v
     Send Notification
```

If payment authorization fails definitively, we may release the inventory hold and mark the reservation as rejected.

```text
Create Pending Reservation
            |
            v
      Hold Inventory
            |
            v
     Payment Declined
            |
            v
    Release Inventory Hold
            |
            v
      Mark Rejected
```

That resembles a rollback, but there's an important difference.

A database rollback makes uncommitted changes disappear.

A saga compensation is a **new business operation that attempts to counteract the consequences of an earlier committed operation**.

Releasing inventory is not the same thing as rolling back the original inventory transaction.

The hold may have been visible to other services.

A customer may have received a notification.

Another workflow may have reacted to the intermediate state.

And some actions cannot be fully undone.

### Compensation is not time travel

Suppose you captured a payment.

Later, the reservation fails.

You issue a refund.

Financially, the customer may eventually receive the money back.

But the original charge still happened.

The refund is a separate financial event, possibly with processing delays, fees, exchange-rate effects, and accounting consequences.

Similarly, sending an email cannot be reversed by deleting an event.

You can send a correction, but the customer may already have read the original message.

A saga therefore needs business-specific compensation rules rather than pretending distributed operations provide ordinary ACID rollback.

---

# 12. Choreography Versus Orchestration

There are two common ways to coordinate sagas.

### Choreography: Services react to events

In a choreography-based saga, services publish events and other services react.

```text
ReservationCreated
        |
        v
Inventory Service
        |
        v
InventoryHeld
        |
        v
Billing Service
        |
        v
PaymentAuthorized
        |
        v
Reservation Service
        |
        v
ReservationConfirmed
```

This can work well when the flow is relatively straightforward and event relationships are well understood.

Services remain loosely coupled to one another's internal implementations.

But the complete workflow becomes distributed across many consumers.

When a booking is stuck, determining what should happen next may require reconstructing event dependencies across several services.

As the process grows, event chains can become difficult to reason about.

Who owns the overall booking state?

Which service decides that a timeout requires compensation?

How does the system know when the workflow is permanently complete?

Without clear answers, choreography can become an elaborate game of distributed telephone.

### Orchestration: One component coordinates the workflow

An orchestrated saga has an explicit coordinator.

```text
                 Booking Orchestrator
                         |
                +--------+--------+
                |                 |
                v                 v
          Inventory Service   Billing Service
                |                 |
                +--------+--------+
                         |
                         v
                 Booking State
```

The orchestrator knows the workflow's current state and determines the next operation.

For example:

```text
PENDING
   |
   v
HOLDING_INVENTORY
   |
   v
INVENTORY_HELD
   |
   v
AUTHORIZING_PAYMENT
   |
   +-- Authorized --> CONFIRMING
   |
   +-- Declined ----> RELEASING_HOLD
```

This makes the business process more explicit.

It's often easier to inspect, test, recover, and evolve when the workflow contains many steps, deadlines, retries, and compensation rules.

The trade-off is that the orchestrator becomes a central source of workflow coordination.

That's not automatically a problem. It may be precisely the responsibility we want one component to own.

### Which would I choose?

For simple, loosely coupled reactions—updating analytics after a reservation is confirmed, for example—event choreography is attractive.

For a payment-and-inventory workflow with multiple intermediate states, external timeouts, compensation, and reconciliation, I'd generally prefer explicit orchestration.

Not necessarily a dedicated workflow product. A carefully designed application service backed by durable workflow state may suffice.

The important thing is that the sequence of responsibilities is visible and recoverable.

---

# 13. Why Two-Phase Commit Usually Isn't the Escape Hatch

At this point, someone may ask:

> Why not use a distributed transaction and make all the services commit together?

Distributed transactions are a real technology.

PostgreSQL supports two-phase commit through commands such as:

```sql
PREPARE TRANSACTION 'booking-92831';
COMMIT PREPARED 'booking-92831';
ROLLBACK PREPARED 'booking-92831';
```

In a coordinated two-phase commit protocol, participants first prepare their transactions, then a coordinator decides whether to commit or abort them.

Conceptually:

```text
             COORDINATOR
                  |
         Phase 1: Prepare
           /             \
          v               v
      Database A       Database B
          |               |
          +-------+-------+
                  |
         Phase 2: Commit
           /             \
          v               v
      Database A       Database B
```

This can provide atomic commit coordination when participants support the protocol and the system correctly manages coordinator state and recovery.

So why don't microservice architectures use it everywhere?

Because it couples the participants' transactional progress to a distributed coordinator and introduces difficult failure-handling and operational requirements.

Prepared transactions can retain locks and resources while waiting for resolution.

If the coordinator becomes unavailable, participants may remain in an uncertain prepared state until the decision can be recovered.

Many message brokers, external APIs, payment providers, and SaaS integrations don't participate in the required protocol at all.

Even where two-phase commit is supported, it does not magically encompass every side effect in a business workflow.

Therefore, the blanket claim that distributed transactions are impossible is wrong.

A better statement is:

**Distributed atomic commit is possible under particular protocols and assumptions, but it often introduces unacceptable coupling or is unsupported by the services a modern business workflow depends upon.**

For ordinary microservice workflows involving payment providers, inventory services, and asynchronous messaging, durable state machines, idempotency, and compensation are usually more practical.

---

# 14. When Microservices Actually Earn Their Cost

We've spent much of this chapter criticizing the complexity introduced by microservices.

That shouldn't be mistaken for a blanket rejection.

There are real situations where they provide substantial advantages.

### Independent engineering teams

Suppose a company has twelve product teams working on different business capabilities.

Coordinating every release through one application may become a significant organizational bottleneck.

Clear service ownership can let teams evolve and deploy capabilities independently.

But that independence only exists if service contracts remain stable enough to avoid constant coordinated changes.

### Distinct scaling requirements

Imagine that hotel search handles 20,000 requests per second while payment reconciliation processes only a few hundred operations per minute.

Search is CPU- and query-intensive.

Payment reconciliation is constrained by external providers and requires strict auditability.

Deploying and scaling these workloads independently can be very useful.

Though it's worth remembering that different worker deployments or process groups can sometimes provide similar benefits without splitting the entire domain into microservices.

### Operational isolation

If PDF generation occasionally exhausts memory, separating it into a distinct service can prevent that failure from directly crashing reservation processing.

Dedicated resource limits and deployment policies can improve fault containment.

### Independent technology requirements

A particular capability may genuinely benefit from a different runtime or persistence technology.

For instance, an analytics pipeline may be better served by a columnar warehouse than by the operational PostgreSQL database.

That can justify an independently operated subsystem.

But using a different programming language merely because one team prefers it isn't automatically an architectural benefit.

### External product boundaries

Sometimes one capability becomes a product used by several other applications.

A central identity service, pricing engine, or inventory system may have multiple independent consumers.

That can justify a clear service interface and separate operational ownership.

The pattern is consistent:

**Microservices are attractive when independent ownership produces tangible value—not when the organization simply wants more deployable units.**

---

# 15. The Distributed Monolith: The Worst of Both Worlds

There's a particularly unfortunate architecture worth recognizing.

Imagine a company that splits its monolith into fifteen services.

Each service deploys separately.

But every significant feature requires simultaneous changes to six services, shared database schemas, and coordinated releases.

Services communicate through long chains of synchronous calls.

One deployment frequently breaks another.

The result is a **distributed monolith**.

```text
Service A ---> Service B ---> Service C
    |              |             |
    v              v             v
Service D <--- Service E <--- Service F
```

The system pays the operational price of microservices without achieving meaningful independence.

It has network failures, deployment complexity, distributed tracing requirements, eventual consistency, and multiple pipelines.

But it still behaves as one tightly coupled application.

A useful diagnostic question is:

> Can this service change its internal implementation and deploy without requiring coordinated changes across unrelated services?

If the answer is consistently no, the boundaries may be poorly chosen.

Another indicator is that one ordinary business operation requires a dozen synchronous service calls.

Or that every service reads the same tables.

Or that teams cannot explain which component owns a particular business invariant.

The problem usually isn't insufficient infrastructure sophistication.

It's weak responsibility boundaries.

Adding Kubernetes, service meshes, and more message brokers won't automatically fix that.

---

# 16. Evolving a Monolith Without a Big-Bang Rewrite

Suppose your SaaS is genuinely outgrowing its modular monolith.

How should you migrate?

I'd strongly discourage rewriting the entire application as microservices in one enormous project.

Instead, extract capabilities incrementally.

A common approach resembles the **strangler pattern**: new or extracted functionality gradually takes responsibility for selected operations while the old system continues serving the remainder.

Imagine Notifications is our first candidate.

Initially:

```text
Monolith
   |
   +-- Reservations
   +-- Billing
   +-- Inventory
   +-- Notifications
```

First, establish a clear internal notification interface.

Then introduce a durable outbox for notification intents.

Next, implement a separate notification worker or service that consumes those intents.

Finally, remove the old in-process notification behavior once the new execution path has demonstrated correctness.

```text
Monolith
   |
   +-- Reservations
   +-- Billing
   +-- Inventory
   |
   +-- Durable Outbox
           |
           v
    Notification Service
```

Notice that we didn't need to extract all modules simultaneously.

The migration produced a useful independent capability while preserving the rest of the system.

### What should be extracted first?

I'd generally favor a capability with:

- Clear responsibility and data ownership.
- Limited synchronous dependencies.
- Distinct scaling or operational requirements.
- Relatively simple failure semantics.
- A measurable benefit from independent deployment.

Notifications, reporting, document processing, and certain integrations often make reasonable early candidates.

Inventory and payment workflows are usually more demanding because they participate in critical business invariants.

That doesn't mean they should never be separated.

It means the migration should begin with a clearly designed consistency protocol, not a Dockerfile.

---

# 17. Practical Lab: A Transactional Outbox and an Idempotent Consumer

Let's implement the core coordination mechanism using PostgreSQL.

We'll simulate two service-owned data domains within one disposable database.

In a real microservice architecture, Reservations and Billing would typically own separate databases or access boundaries. The experiment uses one PostgreSQL instance for convenience, but we'll perform separate local transactions to model independent service commits.

The goal is to demonstrate three properties:

1. A reservation and its event intent commit atomically.
2. An event can be delivered more than once.
3. Repeated delivery doesn't have to create duplicate billing records.

## Step 1 — Create the tables

```sql
DROP TABLE IF EXISTS billing_consumed_events;
DROP TABLE IF EXISTS billing_invoices;
DROP TABLE IF EXISTS reservation_outbox;
DROP TABLE IF EXISTS reservations;

CREATE TABLE reservations (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  amount_minor BIGINT NOT NULL
);

CREATE TABLE reservation_outbox (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  published_at TIMESTAMPTZ
);

CREATE TABLE billing_consumed_events (
  event_id TEXT PRIMARY KEY,
  consumed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE billing_invoices (
  id TEXT PRIMARY KEY,
  reservation_id TEXT NOT NULL UNIQUE,
  amount_minor BIGINT NOT NULL
);
```

The outbox belongs to the reservation domain.

The consumed-event table and invoices belong to the simulated billing domain.

We won't use cross-domain foreign keys because those would obscure the intended ownership boundary.

## Step 2 — Commit a reservation and event together

```sql
BEGIN;

INSERT INTO reservations (
  id,
  status,
  amount_minor
)
VALUES (
  'R-101',
  'confirmed',
  45000
);

INSERT INTO reservation_outbox (
  event_id,
  event_type,
  aggregate_id,
  payload
)
VALUES (
  'evt-101',
  'ReservationConfirmed',
  'R-101',
  '{
    "reservationId": "R-101",
    "amountMinor": 45000
  }'
);

COMMIT;
```

Both records now exist.

Inspect them:

```sql
SELECT * FROM reservations;
SELECT * FROM reservation_outbox;
```

Now repeat the experiment with another reservation, but issue `ROLLBACK` instead of `COMMIT`.

Neither the reservation nor its event intent should remain.

That is the guarantee provided by the local transaction.

## Step 3 — Simulate an outbox publisher

A relay would retrieve unpublished events:

```sql
SELECT
  event_id,
  event_type,
  aggregate_id,
  payload
FROM reservation_outbox
WHERE published_at IS NULL;
```

Imagine the publisher successfully sends `evt-101` to a message broker.

It then crashes before recording publication.

The outbox row remains unpublished.

When the relay restarts, it retrieves the same event again.

The event may be published twice.

This is an expected recovery scenario.

A production relay would need bounded batch selection, concurrency control, retry behavior, and potentially claim leases or database-log capture. We don't need that infrastructure to demonstrate consumer idempotency.

## Step 4 — Consume the event once

The Billing Service receives `evt-101`.

We'll use the event identity to claim processing and create the invoice within one Billing-owned transaction.

```sql
BEGIN;

WITH first_processing AS (
  INSERT INTO billing_consumed_events (event_id)
  VALUES ('evt-101')
  ON CONFLICT DO NOTHING
  RETURNING event_id
)
INSERT INTO billing_invoices (
  id,
  reservation_id,
  amount_minor
)
SELECT
  'INV-101',
  'R-101',
  45000
FROM first_processing;

COMMIT;
```

The Common Table Expression attempts to record the event identity.

If the event hasn't been processed before, the insertion succeeds and returns one row.

That row drives the invoice insertion.

The consumer therefore records the event and creates the invoice in one local transaction.

Inspect:

```sql
SELECT * FROM billing_consumed_events;
SELECT * FROM billing_invoices;
```

You should see one consumed event and one invoice.

## Step 5 — Deliver the same event again

Run the same consumer transaction again.

The unique constraint on `billing_consumed_events.event_id` prevents another successful claim.

`ON CONFLICT DO NOTHING` returns no row.

Therefore, the subsequent invoice insertion receives no input rows.

Inspect the tables again.

There is still one invoice.

We've made the local database effect idempotent under repeated event delivery.

### What the lab doesn't solve

This mechanism doesn't automatically make an external payment capture exactly once.

If the consumer calls a payment provider, the provider-side effect sits outside the local PostgreSQL transaction.

We still need stable operation IDs, provider-supported idempotency, and reconciliation.

The example also assumes the event payload is trusted and valid. Real consumers should validate event contracts and enforce relevant business rules.

And a production event-processing system must think about what happens if a consumer crashes, messages arrive out of order, or a subscription falls behind.

Nevertheless, we've demonstrated a useful architectural combination:

**Transactional outbox for durable publication intent; at-least-once delivery; idempotent local consumers.**

That combination underpins many reliable event-driven systems.

---

# 18. Engineering and Interview Challenges

## Question 1 — The attractive service split

A team proposes splitting Reservations and Inventory into independent services because the modules contain a large amount of code.

Both currently participate in the same PostgreSQL transaction when confirming a booking.

Would you approve the split? What would you investigate first?

## Question 2 — The missing event

A service updates PostgreSQL, then publishes an event to Kafka.

The database commit succeeds, but Kafka is unavailable.

How would you prevent the business event from being permanently lost?

## Question 3 — The duplicate invoice

An outbox relay publishes an event successfully but crashes before recording publication.

After restarting, it publishes the event again.

Billing consumes both copies.

Where should duplicate invoice creation be prevented?

## Question 4 — The confusing compensation

A payment has been captured, but inventory confirmation fails.

A developer proposes rolling back the payment by issuing a refund.

Is that equivalent to rolling back a database transaction? What additional states and failures must be considered?

## Question 5 — The distributed dashboard

Your reservation dashboard needs reservation state, payment status, customer details, and hotel names from four independently owned services.

Would you use live API composition or an event-maintained read model?

What determines the choice?

## Question 6 — Microservices for a small team

A company has five developers and one SaaS product. Its modular monolith is reasonably maintainable, and the database handles current load comfortably.

Management proposes migrating to Kubernetes and fifteen microservices to prepare for future growth.

How would you respond?

---

# 19. Solutions and Discussion

### 1. Code size is insufficient justification

I'd first examine the consistency boundary.

If Reservations and Inventory must coordinate atomically, splitting them creates a new distributed workflow with intermediate states, retries, and compensation.

The split may still be justified if Inventory has independent consumers, scaling requirements, or organizational ownership.

But the team must design how inventory holds, reservation confirmation, timeouts, and recovery will work before extracting the capability.

A large cohesive module isn't automatically a bad service boundary.

### 2. Use a transactional outbox

Write the business change and event intent in the same PostgreSQL transaction.

A relay can publish the committed event later and retry after broker failures.

This prevents a committed database change from silently losing its associated publication intent.

But the relay can publish duplicates, so consumers must be idempotent.

### 3. Enforce idempotency at the consumer's business boundary

Billing should identify the event or intended invoice operation through a stable identifier.

It can use uniqueness constraints and a local transaction to ensure duplicate delivery doesn't create duplicate invoice records.

Queue-level deduplication can reduce redundant work, but the authoritative billing database should enforce the relevant invariant.

If the event triggers external financial operations, those require additional provider-level coordination.

### 4. Compensation is another business operation

A refund doesn't erase the original payment capture.

It creates a separate financial transaction with its own execution, timing, and failure possibilities.

The workflow needs states such as capture succeeded, refund requested, refund pending, refunded, and refund failed or unresolved.

It must also reconcile uncertain provider outcomes and avoid duplicate refunds.

A saga compensation is a corrective business action, not a magical distributed rollback.

### 5. Choose according to freshness, latency, and workload

Live API composition is attractive for relatively infrequent queries that require current information and involve a manageable number of dependencies.

An event-maintained read model is attractive for high-volume dashboards or complex joins across service-owned data, especially when some lag is acceptable.

If an operation requires authoritative payment state before issuing a refund, an eventually consistent projection may be insufficient.

Often both approaches coexist: projections for display, authoritative service calls for business-critical decisions.

### 6. Keep the modular monolith until independence has measurable value

I'd challenge the proposed migration.

Fifteen services introduce deployment, monitoring, networking, distributed consistency, and operational responsibilities that five developers must maintain.

If the current application is modular and handles its workload, that expense needs a compelling justification.

Instead, strengthen module boundaries, improve deployment automation and observability, and extract individual capabilities when a real scaling or organizational need emerges.

Microservices should solve demonstrated problems, not anticipated architectural embarrassment.

---

# 20. Mental Model

A microservice boundary is a trade: **less internal coupling and greater operational independence in exchange for network communication, distributed state, and more complicated failure recovery**.

When evaluating a service split, ask:

- **Who owns the business capability?** Boundaries should reflect meaningful responsibility.
- **Which invariants cross the boundary?** Strong shared rules become distributed coordination problems.
- **Who owns the data?** Other services should depend on contracts rather than internal tables.
- **How do services communicate?** Choose synchronous calls, commands, and events according to their semantics.
- **How are business changes and events coordinated?** Use durable publication patterns such as the transactional outbox where appropriate.
- **What happens halfway through a workflow?** Model intermediate states, retries, compensation, and reconciliation.
- **What independence do we actually gain?** Deployment, scaling, team ownership, technology choice, or fault isolation should justify the cost.

**The best architecture isn't the one with the most independent services. It's the one that places boundaries where independence is valuable and coordination remains manageable.**

For many SaaS products, that means a modular monolith for the core domain and selective extraction of capabilities with genuinely different operational requirements.

---

# Next Session — Designing Reliable Business Workflows

We've learned how services communicate and why distributed business operations need explicit coordination. Now it's time to put those mechanisms under real pressure.

In **CS430-L05 — Designing Reliable Business Workflows**, we'll design a complete hotel-booking and payment process involving inventory holds, payment authorization, external webhooks, retries, compensation, durable state, and reconciliation—including what happens when the customer closes the browser halfway through checkout.

---


---

## Next Lecture — CS430-L05: Designing Reliable Business Workflows

Continue in **CS430 — Distributed Systems and Reliable Workflows**.

## Further Reading

- **Martin Fowler — Microservices:** https://martinfowler.com/articles/microservices.html
- **Martin Fowler — Monolith First:** https://martinfowler.com/bliki/MonolithFirst.html
- **Microservices.io — Database per Service:** https://microservices.io/patterns/data/database-per-service.html
- **Microservices.io — Saga:** https://microservices.io/patterns/data/saga.html
- **Microservices.io — Transactional Outbox:** https://microservices.io/patterns/data/transactional-outbox.html
- **AWS — Transactional Outbox Pattern:** https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- **AWS — Saga Choreography Pattern:** https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html
- **PostgreSQL — Two-Phase Transactions:** https://www.postgresql.org/docs/current/two-phase.html

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS430-L04  MICROSERVICES, EVENTS & BOUNDARIES — INTERVIEW GLANCE CARD

CORE TRADE
  Split services → lose one local transactional boundary
  Cost of distribution ≠ only latency — loss of simple shared authority
  Opening failure: inventory held, payment auth unknown, hold expires,
    another books room, late webhook — each local step "worked"

WHAT IS A MICROSERVICE?
  Owns a business capability; intentional interface; independent deploy;
  owns its persistent state; others use contracts — not internals
  Micro ≠ tiny; ValidationService/DatabaseService ≠ good boundaries
  Layered split + network = distributed function-call tax

MODULAR MONOLITH FIRST
  Modules + one DB → local txs for shared invariants (allocate+confirm)
  Discipline: public interfaces, owned tables — not free-for-all joins
  Deploy/scale/fault isolation costs grow with org — justify vs coordination

BOUNDARIES FROM INVARIANTS
  What must change state together? → consistency boundary candidates
  Reservations↔inventory: strong transactional coupling
  Notifications: async candidate (email fail ≠ undo booking)
  Aggregate ≠ microservice synonym

DATA OWNERSHIP
  Don't SELECT another service's tables — breaks independent evolution
  DB-per-service ≠ server-per-service (schemas/DBs on shared PG OK-ish)
  Logical ownership ≠ physical isolation
  Cross-domain reports harder → composition or read models

READS ACROSS BOUNDARIES
  A API composition: clear ownership; latency/availability coupling
  B Materialized read model / CQRS projection: fast; async lag;
    don't refund from stale projection — consult authority

SYNC CALLS
  Look like functions; timeouts after remote commit; need idempotency
  Chatty chains amplify latency/fragility; use sync when answer needed now

EVENTS VS COMMANDS
  Command: request action (AuthorizePayment) — intended recipient
  Event: report fact (PaymentAuthorized) — many consumers
  Publish only what publisher can truthfully assert
  Event schemas are APIs (units, status meaning, versioning)

DUAL-WRITE PROBLEM
  DB commit then publish OR publish then DB — either can diverge
  Transactional outbox: business change + outbox row in ONE DB tx
  Relay publishes; crash → duplicate delivery → consumers must be idempotent
  Polling outbox vs CDC/Debezium — different ops; neither = exactly-once

ORDERING
  Concurrent consumers can apply Cancel then Confirm → wrong projection
  Aggregate version / ordered partition / fetch missing deltas
  Design for consumer state transitions — don't assume publish order = apply

SAGAS
  Sequence of local commits + compensations — not one global rollback
  Compensation = new business op (refund ≠ time travel; email irreversible)
  Choreography: react to events — loose; hard to own overall state
  Orchestration: explicit coordinator + durable workflow state — clearer for
    multi-step payment/inventory with timeouts/compensation

2PC
  PREPARE / COMMIT PREPARED exists — not impossible
  Couples participants; holds resources; coordinator failure; many APIs
    (payments, brokers) don't participate
  Prefer durable state machines + idempotency + compensation for typical SaaS

WHEN MICROSERVICES EARN COST
  Independent teams with stable contracts
  Distinct scale / isolation / technology / external product boundary
  NOT "more deployable units" fashion

DISTRIBUTED MONOLITH
  Many services + coordinated releases + shared schemas + sync call chains
  Pays microservices tax without independence — fix boundaries, not mesh

EVOLUTION
  Strangler: extract one capability (e.g. notifications via outbox) first
  Prefer clear ownership, weak sync deps, distinct ops needs early
  Inventory/payments later — with designed consistency protocol

SENIOR LINE: place boundaries where independence is valuable and
             coordination remains manageable.
```

