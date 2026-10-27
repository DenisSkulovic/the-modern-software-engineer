---
id: SE330-L02
course: SE330
title: "Architecture Patterns and Their Consequences"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S02]
prev: SE330-L01
next: SE330-L03
---




# SE330 — Software Architecture and Evolution

## Lecture 02: Architecture Patterns and Their Consequences

*Layered architecture, vertical slices, hexagonal architecture, Clean Architecture, domain-driven design, and the strange business of solving the same problem six different ways.*

---

## 1. The Application With Six Architectures

A software company is building a subscription management platform. Its application handles customers, subscription plans, billing cycles, payments, and account cancellations.

Initially, the backend is beautifully simple:

```text
src/
├── controllers/
├── services/
├── repositories/
└── database/
```

As the company grows, developers begin noticing problems. Business logic leaks into HTTP controllers, database entities travel through unrelated modules, and changing payment providers requires modifying several services.

An experienced engineer proposes **hexagonal architecture**, separating business logic from infrastructure through ports and adapters.

Another engineer suggests **Clean Architecture**, with domain entities, use cases, interface adapters, and frameworks arranged in concentric circles.

A third recommends **domain-driven design**, arguing that the real problem is unclear boundaries between subscriptions, billing, and payments.

Someone else proposes **vertical slices**, because adding one feature currently requires navigating half the repository.

Finally, management hires an architect who declares that the future is **event-driven microservices**.

Within six months, the team has implemented all these ideas.

The result is spectacular.

Creating a subscription now involves a controller, command handler, application service, domain service, aggregate, repository interface, repository implementation, event dispatcher, event handler, mapper, DTO, and dependency injection configuration.

The business operation still inserts approximately three rows into PostgreSQL.

What happened?

None of these architectural patterns is necessarily bad. In fact, several are genuinely powerful. The mistake was treating them as competing badges of engineering sophistication rather than understanding the particular problems each pattern addresses.

**Architectural patterns are tools for controlling complexity, not trophies for demonstrating technical maturity.**

Our task is to understand their mechanisms, identify their costs, and discover how to combine them selectively.

---

## 2. Architecture Patterns Operate on Different Dimensions

Before examining individual patterns, we need to correct a common misconception: architectural approaches are not always mutually exclusive.

Layered architecture primarily addresses the separation of technical responsibilities.

Vertical-slice architecture emphasizes organizing code around features or use cases.

Hexagonal architecture separates application behavior from external technologies.

Clean Architecture establishes dependency rules between policy and implementation details.

Domain-driven design helps engineers discover meaningful business models and boundaries.

Event-driven architecture structures communication around events, while microservices establish independently deployable service boundaries.

These approaches answer different questions.

| Pattern | Central question |
|---|---|
| Layered architecture | Which technical responsibility belongs where? |
| Vertical slices | Which code changes together for a feature? |
| Hexagonal architecture | How can business behavior avoid depending on infrastructure? |
| Clean Architecture | In which direction should source dependencies point? |
| Domain-driven design | How should software represent business concepts and boundaries? |
| Event-driven architecture | How should components communicate about changes? |
| Microservices | Which parts should be independently deployed and operated? |

A modular monolith might simultaneously use vertical slices, domain-driven boundaries, hexagonal interfaces for selected integrations, and asynchronous domain notifications.

That's perfectly reasonable.

What is not reasonable is assuming every pattern must be implemented in its most elaborate form.

The important distinction is between applying a principle and adopting all the machinery associated with a named architectural style.

---

## 3. Layered Architecture: The Classic Starting Point

Layered architecture is probably the most familiar pattern in enterprise development.

A typical backend separates responsibilities into:

```text
┌─────────────────────────────┐
│       HTTP Controllers      │
├─────────────────────────────┤
│      Application Logic      │
├─────────────────────────────┤
│       Data Access           │
├─────────────────────────────┤
│          Database           │
└─────────────────────────────┘
```

A request moves through the layers:

```text
HTTP Request
    ↓
Controller
    ↓
Service
    ↓
Repository
    ↓
PostgreSQL
```

The controller handles HTTP concerns. The service coordinates business operations. The repository encapsulates database access.

Consider a straightforward subscription endpoint:

```typescript
// controllers/subscriptionController.ts

async function createSubscription(req, res) {
  const result = await subscriptionService.create({
    customerId: req.user.id,
    planId: req.body.planId
  });

  res.status(201).json(result);
}
```

The application service implements the operation:

```typescript
// services/subscriptionService.ts

async function create(command: CreateSubscription) {
  const plan = await planRepository.findById(
    command.planId
  );

  if (!plan?.active) {
    throw new Error("Plan unavailable");
  }

  return subscriptionRepository.insert({
    customerId: command.customerId,
    planId: plan.id,
    status: "PENDING"
  });
}
```

The repository handles persistence:

```typescript
// repositories/subscriptionRepository.ts

async function insert(data: NewSubscription) {
  return database
    .getRepository(SubscriptionEntity)
    .save(data);
}
```

This structure works well because it separates different kinds of concerns. Developers can often find the HTTP boundary, business orchestration, and database interaction without much difficulty.

### Where layering begins to fail

Now imagine that the platform grows to 150 endpoints.

Its directories contain 30 controllers, 45 services, and 25 repositories. A single feature may require modifications across several large, shared files.

Worse, services begin calling other services:

```text
SubscriptionService
    ↓
BillingService
    ↓
CustomerService
    ↓
SubscriptionService
```

The technical layers still exist, but ownership of business behavior becomes increasingly unclear.

A directory named `services` doesn't tell us whether a class owns a business rule, orchestrates a workflow, or merely wraps a repository call.

This often produces *anemic services*: classes with generic CRUD methods that move data between HTTP handlers and repositories without expressing much business meaning.

It can also produce the opposite problem: enormous service classes containing dozens of unrelated operations.

Layering has separated technical responsibilities without necessarily creating cohesive business boundaries.

### The distinction between closed and relaxed layering

In a strictly layered design, a component communicates only with its immediately adjacent layer.

In a more relaxed design, some layers may be skipped when doing so is appropriate. For instance, a simple read-only endpoint might query a database through a dedicated query component without passing through an elaborate domain service.

Neither rule should become dogma.

A strict hierarchy may provide useful consistency, but forcing every operation through unnecessary layers creates additional indirection with little benefit.

**Layered architecture is an excellent default for small and moderately complex applications. Its weakness appears when technical organization substitutes for explicit business ownership.**

---

## 4. Vertical Slices: Organizing Around What the Application Does

Vertical-slice architecture approaches the same application from another direction.

Instead of organizing everything according to technical roles, it groups implementation around particular features or business operations.

Consider:

```text
src/
├── subscriptions/
│   ├── create/
│   │   ├── handler.ts
│   │   ├── schema.ts
│   │   └── tests.ts
│   ├── cancel/
│   │   ├── handler.ts
│   │   └── tests.ts
│   └── get-details/
│       └── handler.ts
├── billing/
│   ├── generate-invoice/
│   └── collect-payment/
└── customers/
    └── update-profile/
```

Each feature contains much of the implementation needed to accomplish one operation.

This can dramatically improve navigation and change locality.

A developer implementing subscription cancellation can begin in `subscriptions/cancel` rather than searching across controllers, services, repositories, validators, and miscellaneous utilities.

### The deeper idea: minimize the cost of change

Imagine two operations:

- Creating a subscription.
- Displaying subscription statistics.

Both concern subscriptions, but their technical requirements differ.

Creation involves business validation, state transitions, payment arrangements, and database consistency.

Statistics may involve an optimized SQL query returning an aggregate result.

Why should both operations use an identical stack of controllers, domain objects, repository interfaces, and service abstractions?

A vertical-slice approach allows each operation to use the structure appropriate to its complexity.

For example, the statistics endpoint might use a direct query:

```typescript
const result = await db.query(`
  SELECT plan_id, COUNT(*) AS total
  FROM subscriptions
  WHERE status = 'ACTIVE'
  GROUP BY plan_id
`);
```

Meanwhile, subscription creation may require a richer application workflow.

This resembles a lightweight form of **Command Query Responsibility Segregation**, or CQRS: operations that change state and operations that retrieve information can use different models and paths.

Importantly, CQRS does not automatically imply separate databases, message brokers, or eventual consistency. It can be as simple as distinguishing write operations from read queries inside one Node.js application.

### The danger of excessive fragmentation

Vertical slices can also be taken too far.

Suppose `create`, `renew`, `cancel`, and `suspend` each independently implement subscription lifecycle rules.

Now the system contains duplicated and potentially contradictory business logic.

The solution is to distinguish **feature orchestration** from **shared domain invariants**.

Feature handlers can remain separate while using a cohesive subscription domain model that owns the rules governing valid state transitions.

The guiding principle is simple:

**Organize independently changing behavior into focused slices, but centralize business rules that must remain consistent across those slices.**

Vertical slicing is not an excuse to duplicate the domain model forty times.

---

## 5. Hexagonal Architecture: The Application Is Not Its Database

Let's introduce a different problem.

A subscription platform currently exposes its functionality through Express HTTP endpoints. Management now wants a scheduled worker that automatically renews subscriptions every night.

The business operation already exists, but its implementation depends heavily on HTTP request objects.

Elsewhere, domain logic directly imports TypeORM entities and Stripe-specific APIs.

The team discovers that executing the same business operation from a worker requires reconstructing assumptions about HTTP, authentication middleware, and infrastructure.

This is precisely the problem hexagonal architecture was designed to address.

Alistair Cockburn introduced the architectural pattern commonly known as **Ports and Adapters** to separate application behavior from the technologies through which it is accessed or supported.

### The central design

```text
        HTTP Controller
              │
              ▼
      ┌───────────────┐
      │               │
      │  Application  │◄──── Scheduled Worker
      │               │
      └───────────────┘
         │         │
         ▼         ▼
    Repository   Payment
       Port       Port
         ▲         ▲
         │         │
    PostgreSQL   Stripe
      Adapter    Adapter
```

The hexagon is conceptual. There aren't necessarily six interfaces, and no geometric properties make the architecture work.

The essential distinction is between application behavior and external mechanisms.

A **port** defines an interaction the application supports or requires.

An **adapter** translates between that port and some external technology.

### Driving and driven adapters

Driving adapters initiate application behavior.

Examples include:

- HTTP controllers.
- Queue consumers.
- Scheduled jobs.
- Command-line applications.
- Automated test harnesses.

Driven adapters fulfill requirements expressed by the application.

Examples include:

- PostgreSQL repositories.
- Stripe integration clients.
- Email providers.
- Object-storage implementations.

Let's construct a small example.

```typescript
// subscriptions/application/ports.ts

export interface SubscriptionStore {
  find(id: string): Promise<Subscription | null>;
  save(subscription: Subscription): Promise<void>;
}

export interface PaymentProcessor {
  charge(
    customerId: string,
    amountCents: number,
    idempotencyKey: string
  ): Promise<PaymentResult>;
}
```

Our application use case depends on these capabilities:

```typescript
// subscriptions/application/renewSubscription.ts

export class RenewSubscription {
  constructor(
    private readonly store: SubscriptionStore,
    private readonly payments: PaymentProcessor
  ) {}

  async execute(subscriptionId: string) {
    const subscription = await this.store.find(
      subscriptionId
    );

    if (!subscription) {
      throw new Error("Subscription not found");
    }

    if (!subscription.canRenew()) {
      throw new Error("Renewal not permitted");
    }

    // Coordinate payment and a durable renewal workflow.
    // Persistence, retries and reconciliation are omitted.
  }
}
```

The use case doesn't need to know whether it was initiated by HTTP, a scheduled worker, or a queue consumer.

Similarly, it doesn't directly know which payment provider or database implements its dependencies.

At runtime, the application still performs concrete database and payment operations. Hexagonal architecture doesn't eliminate infrastructure; it makes the dependency between business behavior and infrastructure explicit.

### Why dependency direction matters

Without a port, an application service might import `StripePaymentClient` directly.

With a port, the Stripe adapter implements an application-defined contract:

```typescript
export class StripePaymentAdapter
  implements PaymentProcessor {

  async charge(
    customerId: string,
    amountCents: number,
    idempotencyKey: string
  ): Promise<PaymentResult> {
    // Translate to Stripe's API.
  }
}
```

The application owns the interface; infrastructure conforms to it.

This reverses the source-code dependency without reversing runtime execution. The application still calls the adapter, but its source code no longer imports Stripe-specific classes.

That distinction is central to dependency inversion.

### When hexagonal architecture earns its cost

It is especially useful when business logic must survive changes in delivery mechanisms or integrations.

A payment platform supporting several providers is a strong candidate. So is a document-processing system that can be triggered through HTTP, background jobs, and scheduled batch imports.

However, wrapping every library call in a custom interface is not automatically beneficial.

If a small service performs three uncomplicated SQL queries, introducing twelve repository interfaces may create more code without protecting any meaningful business policy.

The right question is not, "Are we perfectly hexagonal?"

It is, "Which infrastructure dependencies are making our important business logic harder to test, reuse, or evolve?"

---

## 6. Clean Architecture: Dependency Rules as a Design Philosophy

Clean Architecture, associated with Robert C. Martin, overlaps substantially with hexagonal architecture.

Its familiar diagrams show concentric circles representing different responsibilities:

```text
┌────────────────────────────────────┐
│     Frameworks and Infrastructure  │
│  ┌──────────────────────────────┐  │
│  │      Interface Adapters      │  │
│  │  ┌────────────────────────┐  │  │
│  │  │    Application Use     │  │  │
│  │  │         Cases          │  │  │
│  │  │  ┌──────────────────┐  │  │  │
│  │  │  │  Domain Policy   │  │  │  │
│  │  │  └──────────────────┘  │  │  │
│  │  └────────────────────────┘  │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

The central rule is that **source-code dependencies should point inward, toward more fundamental policies**.

Business rules should not depend on HTTP frameworks, database drivers, or particular user interfaces.

Outer components may depend on inner contracts, while inner components remain unaware of those outer implementations.

### The difference from hexagonal architecture

Hexagonal architecture emphasizes the application's boundary with external actors and technologies through ports and adapters.

Clean Architecture offers a more explicit conceptual separation between domain policy, use-case orchestration, adapters, and infrastructure.

They share the same fundamental aim: protect important application logic from unnecessary dependency on implementation details.

In an ordinary TypeScript project, their resulting code structures may look remarkably similar.

You should not feel obligated to implement both as separate architectural frameworks.

### The dependency injection misconception

Developers sometimes mistake dependency injection for Clean Architecture itself.

Consider:

```typescript
class SubscriptionService {
  constructor(
    private readonly database: DataSource
  ) {}
}
```

A dependency was injected, but the service still depends directly on TypeORM's `DataSource`.

Dependency injection helps supply dependencies from outside. Dependency inversion concerns **which abstractions the business logic depends on**.

These are related ideas, not synonyms.

Similarly, adopting NestJS or another dependency-injection framework does not automatically produce clean architectural boundaries. A neatly injected dependency can still be the wrong dependency.

### The cost of architectural purity

Imagine a simple internal application where employees update contact information.

A developer implements every operation through:

```text
Controller
    ↓
Request DTO
    ↓
Input Mapper
    ↓
Command
    ↓
Use Case
    ↓
Domain Entity
    ↓
Repository Port
    ↓
Repository Adapter
    ↓
ORM Entity
    ↓
Response Mapper
    ↓
Response DTO
```

There may be valid reasons for some of these transformations, particularly when external contracts differ from internal models.

But creating all of them mechanically can turn straightforward functionality into a navigation exercise.

The principle worth preserving is separation of important policies from volatile mechanisms.

The ceremony is optional.

---

## 7. Domain-Driven Design: Discovering the Right Boundaries

So far, we've focused primarily on how code is organized and how dependencies flow.

But consider a more fundamental problem: **what if the application's understanding of the business is wrong?**

Imagine a hotel-booking platform in which the word *reservation* means different things to different teams.

For the customer-facing product, a reservation means the customer has requested a room.

For the inventory team, it means a room allocation has been held.

For finance, it means an obligation that may generate revenue.

For the hotel integration team, it means a booking acknowledged by an external property-management system.

These definitions overlap, but they are not identical.

Trying to represent every meaning through one enormous `ReservationEntity` can lead to fields such as:

```typescript
interface ReservationEntity {
  status: string;
  paymentStatus: string;
  supplierStatus: string;
  inventoryStatus: string;
  invoiceStatus: string;
  confirmationStatus: string;
}
```

The entity becomes a collection of states belonging to several different business processes.

Domain-driven design, or **DDD**, begins with the observation that good software models require understanding the business domain and its language.

It provides both strategic techniques for discovering boundaries and tactical techniques for implementing domain behavior.

### Ubiquitous language

DDD encourages developers and domain experts to establish precise terminology within a particular business context.

For example:

- *Reservation* means the customer's booking agreement.
- *Inventory hold* means temporary allocation of room capacity.
- *Payment authorization* means permission to capture funds, not completed settlement.
- *Invoice* means a financial document representing an obligation to pay.

The vocabulary should appear consistently in discussions, code, tests, and relevant documentation.

This is more than a naming convention. Ambiguous language often reveals ambiguous business ownership.

If developers cannot agree on what `CONFIRMED` means, there may be a missing distinction in the domain model.

### Bounded contexts

A **bounded context** establishes a boundary within which a particular domain model and vocabulary are internally consistent.

Consider:

```text
┌─────────────────────┐
│ Reservation Context │
│                     │
│ Booking lifecycle   │
│ Cancellation rules  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Billing Context   │
│                     │
│ Invoices            │
│ Outstanding balances│
└─────────────────────┘
```

The reservation context and billing context may both discuss a customer, but they need not use the same complete customer model.

Billing might care about legal billing details, currency, and tax identifiers. Reservations might care about the guest, dates, room preferences, and booking permissions.

Forcing both contexts to share one universal `CustomerEntity` creates coupling through a supposedly reusable data structure.

A bounded context allows different representations where the business meanings genuinely differ.

This does not require microservices. Several bounded contexts may coexist in a single application and database.

### Aggregates: protecting business invariants

DDD also introduces the concept of an **aggregate**.

An aggregate groups domain entities and value objects behind a consistency boundary. Its root controls operations that must preserve the aggregate's invariants.

Consider subscription management.

A subscription might have rules such as:

- A cancelled subscription cannot be renewed without reactivation.
- A billing period cannot overlap an existing billing period.
- Suspension must not silently convert an expired subscription into an active one.

Instead of permitting arbitrary updates to the subscription's fields, the domain model exposes meaningful operations:

```typescript
type SubscriptionStatus =
  | "ACTIVE"
  | "SUSPENDED"
  | "CANCELLED";

class Subscription {
  constructor(
    readonly id: string,
    private status: SubscriptionStatus
  ) {}

  suspend(): void {
    if (this.status !== "ACTIVE") {
      throw new Error(
        "Only active subscriptions can be suspended"
      );
    }

    this.status = "SUSPENDED";
  }

  getStatus(): SubscriptionStatus {
    return this.status;
  }
}
```

This example is intentionally simple, but its direction matters.

Consumers request a valid business operation rather than directly setting arbitrary database fields.

An aggregate is not merely an ORM entity, and it need not be represented by an elaborate class hierarchy. It is primarily a design boundary for consistent business state changes.

### Aggregates and transactions

Suppose a subscription renewal requires changing subscription state and recording a payment attempt.

The appropriate consistency strategy depends on the business guarantees.

Some state changes belong within one atomic database transaction. Others involve external systems and cannot be protected by a local database transaction, requiring durable workflows and reconciliation.

DDD encourages carefully identifying consistency boundaries rather than treating every related entity as one giant object.

A common design mistake is creating enormous aggregates that load and lock large collections of data for every operation.

The opposite mistake is splitting genuinely inseparable invariants across independently updated components without an explicit consistency strategy.

Both errors come from treating modeling rules as formulas rather than reasoning about actual business constraints.

### Context maps and integration

Bounded contexts must still communicate.

A context map describes relationships between them: which context owns a concept, which depends on another, and where translation is necessary.

An **anti-corruption layer** can protect one context from another context's terminology or data representation.

For example, a hotel supplier might call something a `BookingConfirmation`, but the internal application may distinguish inventory acceptance from final customer confirmation.

An adapter can translate the supplier's model into the application's own vocabulary.

This prevents external terminology from gradually rewriting the internal domain model.

DDD is most valuable where business rules are genuinely complicated. Applying elaborate aggregates and ubiquitous-language workshops to a trivial CRUD administration screen may offer little benefit.

**The strength of DDD is not sophisticated object-oriented code. It is making the software's representation of the business more accurate.**

---

## 8. Modular Monoliths: Strong Boundaries Without Distributed Operations

We've now encountered several patterns that can strengthen internal structure.

But how should the resulting application be deployed?

For many teams, the best answer remains surprisingly straightforward: **as one application**.

A modular monolith organizes code into meaningful internal modules while preserving a unified deployment.

For our subscription platform:

```text
src/
├── modules/
│   ├── subscriptions/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── index.ts
│   ├── billing/
│   ├── payments/
│   └── identity/
├── composition/
└── server.ts
```

Each module exposes a deliberate public API.

Other modules should not import arbitrary internal implementations.

For example:

```typescript
// Good: use the module's published capability
import { suspendSubscription }
  from "../subscriptions";

// Suspicious: reach into another module's persistence
import { SubscriptionEntity }
  from "../subscriptions/infrastructure/entities";
```

The difference is not purely cosmetic.

The first form preserves the opportunity to change subscription persistence without modifying every consumer.

The second distributes knowledge of internal implementation details across the application.

### How do we enforce boundaries?

TypeScript folder structure alone does not prevent inappropriate imports.

A team can use lint rules, dependency analysis, package boundaries, and architecture tests to establish restrictions.

A simple rule might be:

```text
billing/
    may import:
        subscriptions/public-api

    must not import:
        subscriptions/infrastructure
        subscriptions/internal-domain
```

More importantly, code reviews must reinforce the underlying ownership model.

A boundary that exists in diagrams but is routinely bypassed in production code is not a reliable boundary.

### Why not deploy each module independently?

Independent deployment can be useful, but it changes the cost structure.

A microservice introduces operational responsibilities:

- Network communication and partial failures.
- Independent versioning and deployment.
- Authentication and authorization across service boundaries.
- Distributed tracing.
- Data ownership and consistency.
- Service discovery and configuration.
- Additional testing and incident-response complexity.

A modular monolith avoids many of these distributed-systems costs while retaining logical separation.

Its limitations remain significant: modules typically share deployment timing and process-level resources, and scaling one module independently may require architectural changes.

Nevertheless, many businesses do not need independently deployed services for every domain boundary.

A strong modular monolith is often a better foundation than a premature constellation of microservices.

---

## 9. Event-Driven Architecture: Communication Through Facts

Let's examine another architectural choice.

A customer successfully activates a subscription. Several other operations should follow:

- Send a confirmation email.
- Update analytics.
- Start a customer onboarding workflow.
- Record an audit entry.

One design uses synchronous calls:

```text
Activate Subscription
    ↓
Send Email
    ↓
Update Analytics
    ↓
Start Onboarding
    ↓
Write Audit Log
```

This creates temporal coupling. A slow analytics provider or unavailable email service might delay the original operation.

An event-driven design changes the interaction:

```text
                Subscription Activated
                         │
                         ▼
                 Event Publication
                         │
           ┌─────────────┼──────────────┐
           ▼             ▼              ▼
       Email Worker   Analytics      Onboarding
```

The subscription module reports that something happened. Interested consumers react according to their responsibilities.

### Events describe facts, not requests

An event might be:

```typescript
type SubscriptionActivated = {
  eventId: string;
  subscriptionId: string;
  customerId: string;
  occurredAt: string;
};
```

This event describes an occurrence in the domain.

Compare it with a command:

```typescript
type SendActivationEmail = {
  customerId: string;
  templateId: string;
};
```

The command requests an action from a particular responsibility.

The event announces a fact that may interest multiple consumers.

Confusing the two can create architectural ambiguity. If a producer emits `SubscriptionActivated` specifically to force another service to perform a required operation, the system may be hiding a command behind event terminology.

### The benefits

Event notifications can reduce direct dependencies between producers and consumers.

The subscription module need not know every analytics dashboard or notification workflow that depends on activation events.

New consumers can potentially be added without modifying the subscription module.

Events can also support asynchronous execution and independent scaling of consumer workloads.

### The hidden costs

Event-driven communication introduces its own failure modes.

What happens if the subscription database commits successfully but event publication fails?

What happens if a consumer processes the same event twice?

What if two events arrive out of order?

What if a consumer cannot understand a newer event schema?

Production designs must address these questions through mechanisms such as durable publication, the transactional outbox pattern, idempotent consumers, retries, versioned contracts, and dead-letter handling where appropriate.

These aren't optional details if the event controls important business behavior.

### Domain events are not necessarily integration events

Within a monolith, a domain event might simply represent an internal occurrence that triggers another application handler.

It need not travel through Kafka, RabbitMQ, or any external broker.

An integration event, by contrast, crosses a system or independently governed component boundary and usually requires stronger durability and compatibility considerations.

Similarly, event-driven architecture should not be confused with **event sourcing**, where recorded events form the authoritative history from which application state can be reconstructed.

An application can publish events while storing its authoritative state in ordinary PostgreSQL tables.

### When events are the wrong solution

Suppose activating a subscription is legally forbidden unless payment authorization succeeds.

It would be dangerous to treat payment authorization as a casual asynchronous side effect if the workflow allows activation before the required decision is known.

The system needs an explicit process guaranteeing the correct outcome, whether through a synchronous operation or a durable state machine.

Event-driven architecture is especially attractive for independent consequences of a completed business action.

It is less attractive when used to conceal mandatory coordination behind a collection of loosely specified messages.

---

## 10. Combining the Patterns Without Creating a Monster

Let's design a practical subscription SaaS serving 30,000 customers with six backend developers.

The platform uses Node.js, TypeScript, PostgreSQL, Stripe, Redis, and a background job system. Product management expects new pricing plans, occasional payment-provider changes, and additional billing functionality.

Here is a reasonable starting architecture:

```text
                 HTTP API
                    │
                    ▼
           ┌───────────────────┐
           │  Modular Monolith │
           │                   │
           │  Subscriptions    │
           │  Billing          │
           │  Payments         │
           │  Customers        │
           │                   │
           └─────────┬─────────┘
                     │
          ┌──────────┴───────────┐
          ▼                      ▼
      PostgreSQL            Job Queue
                                 │
                                 ▼
                          Background Workers

Payments module ───────► Payment Provider
```

Inside this design, we can selectively apply several patterns.

**Modular monolith:** Each major business responsibility has a defined boundary, but deployment remains unified.

**Vertical slices:** Individual operations such as subscription activation, suspension, and cancellation have focused application handlers.

**Domain-driven design:** Subscription lifecycle rules live in a coherent model, while billing and payments own their respective concepts.

**Hexagonal architecture:** Payment-provider and other volatile infrastructure dependencies use appropriate ports and adapters.

**Event-driven communication:** Noncritical downstream reactions, such as analytics and notifications, can be triggered asynchronously.

**Layering:** Each sufficiently complex module may internally distinguish transport, application logic, domain behavior, and persistence.

**Clean Architecture principles:** Core business policy avoids depending directly on volatile infrastructure implementations.

Notice that this architecture does not require seven independent architectural frameworks.

It needs a small set of understandable design rules.

### A concrete execution path

A customer requests cancellation:

```text
HTTP DELETE /subscriptions/:id
              │
              ▼
      Cancellation Handler
              │
              ▼
      Subscription Domain
      validates cancellation
              │
              ▼
       Transactional Update
       - subscription status
       - required local records
       - durable event/outbox record
              │
              ▼
          Commit
              │
              ▼
      Background Dispatcher
              │
       ┌──────┴────────┐
       ▼               ▼
  Notifications    Analytics
```

If cancellation also requires a refund, the design needs a durable refund workflow with explicit state and failure handling. We cannot assume that a database transaction atomically includes an external payment-provider request.

This workflow illustrates how architecture patterns complement one another.

The domain model enforces cancellation rules. The application handler coordinates the operation. Persistence and external integrations are isolated where useful. Durable asynchronous processing handles consequences that do not need to complete in the original HTTP request.

Nothing here requires independent microservice deployment.

### What would justify changing the architecture later?

Perhaps billing processing becomes computationally expensive and needs separate scaling.

Perhaps a dedicated payments team emerges with strict operational ownership.

Perhaps regulatory requirements demand stronger isolation of sensitive financial operations.

These are credible reasons to reconsider service boundaries.

By contrast, reaching 100,000 customers is not automatically a reason to introduce Kubernetes or split every module into a separate service.

The number of customers says little about the actual request rate, workload characteristics, operational constraints, or organizational requirements.

Architecture should respond to evidence.

---

## 11. Choosing a Pattern: A Practical Decision Framework

Instead of asking which architectural pattern is best, begin with the dominant source of complexity.

| Problem observed | First architectural idea to investigate |
|---|---|
| Business logic scattered across HTTP and persistence code | Layer separation and dependency inversion |
| Each feature requires changes across many unrelated files | Feature ownership and vertical slices |
| Business rules depend heavily on external SDKs | Ports and adapters |
| Unclear business terms and conflicting state rules | DDD and bounded contexts |
| Modules frequently modify one another's internals | Modular boundaries and explicit contracts |
| Slow secondary operations delay critical requests | Asynchronous processing and events |
| Different workloads genuinely need independent scaling | Separate processes or services |
| Multiple teams are blocked by synchronized deployments | Service boundaries and ownership review |

This table provides starting hypotheses, not guaranteed answers.

For example, if reports are slow, separating report generation into a worker may be enough. Introducing an independently deployed reporting microservice is a larger step requiring additional justification.

Likewise, if a payment SDK is imported throughout the codebase, a focused adapter may solve most of the problem without adopting an elaborate Clean Architecture template.

### Watch for architectural warning signs

Several symptoms deserve investigation:

**Every operation passes through many trivial abstractions.** The architecture may contain indirection without meaningful separation.

**Shared utility modules continually grow.** Business responsibilities may be leaking into generic code.

**One database entity appears throughout unrelated modules.** Internal data models may have become unofficial cross-module contracts.

**Developers frequently coordinate changes across many teams.** Boundaries may not match ownership or change patterns.

**Simple operations require publishing and consuming several events.** Asynchronous communication may be hiding unnecessary complexity.

**A repository contains dozens of interfaces with one implementation each.** Some interfaces may protect real dependencies, but others may be ceremonial.

**Every new feature requires modifying a central orchestrator.** The design may have concentrated too much knowledge in one component.

None of these symptoms proves an architecture is defective.

They identify places where investigation is more valuable than aesthetic judgment.

---

## 12. Practical Lab — Refactoring a Subscription Backend

Consider an existing service:

```typescript
class SubscriptionService {
  async activate(customerId: string, planId: string) {
    const plan = await dataSource
      .getRepository(PlanEntity)
      .findOneBy({ id: planId });

    if (!plan || !plan.active) {
      throw new Error("Invalid plan");
    }

    const stripe = new StripeClient(process.env.STRIPE_KEY!);

    await stripe.charge(customerId, plan.priceCents);

    const subscription = await dataSource
      .getRepository(SubscriptionEntity)
      .save({
        customerId,
        planId,
        status: "ACTIVE"
      });

    await emailService.sendActivation(customerId);

    return subscription;
  }
}
```

This implementation has several problems, but don't assume each one requires a new architectural pattern.

### Investigation A — Identify responsibilities

Separate the operation into conceptual responsibilities:

- Retrieving plan information.
- Validating subscription eligibility.
- Processing payment.
- Persisting subscription state.
- Coordinating partial failures.
- Sending customer notifications.

Which of these are business decisions, and which are infrastructure mechanisms?

Which steps must be coordinated durably?

What happens if payment succeeds but persistence fails?

### Investigation B — Introduce minimal boundaries

Propose a module organization:

```text
subscriptions/
├── domain/
│   └── subscription.ts
├── application/
│   └── activateSubscription.ts
├── infrastructure/
│   └── postgresSubscriptionStore.ts
└── index.ts

payments/
├── application/
│   └── paymentPort.ts
└── infrastructure/
    └── stripeAdapter.ts

notifications/
└── application/
    └── sendActivation.ts
```

Don't create interfaces for everything. Introduce them where they isolate important dependencies or enforce ownership.

Ensure the application use case can be tested without making real Stripe calls.

### Investigation C — Design the failure behavior

Suppose Stripe reports payment success, but saving the active subscription fails.

Simply retrying the entire operation might charge the customer twice.

Design an activation workflow that uses a durable operation identifier, payment idempotency, recorded intermediate state, and reconciliation when the payment outcome is uncertain.

The purpose of the lab isn't to recreate all of SE320–SE490's workflow machinery. It is to recognize where architectural boundaries support reliable workflow implementation rather than merely rearranging files.

### Investigation D — Evaluate the result

Ask:

1. Can subscription eligibility rules be tested without HTTP or Stripe?
2. Can payment-provider integration change without rewriting domain policy?
3. Does one module own subscription lifecycle transitions?
4. Can a failed activation be diagnosed and reconciled?
5. Did the refactoring reduce meaningful coupling, or merely increase the number of files?

A successful architecture refactoring should improve at least one important system characteristic.

A larger directory tree is not itself an achievement.

---

## 13. Engineering and Interview Challenges

### Challenge 1 — Layered versus vertical slices

A backend has 200 endpoints, and developers frequently modify controllers, services, repositories, and validators to implement a single feature.

Would you reorganize the entire codebase into vertical slices? What evidence would influence your decision?

### Challenge 2 — Hexagonal architecture and testing

A developer argues that every repository must have an interface and an in-memory fake so that all tests can run without PostgreSQL.

Is this a good interpretation of hexagonal architecture? What correctness risks might the testing strategy introduce?

### Challenge 3 — Bounded contexts and databases

An e-commerce application separates Orders, Inventory, and Payments into bounded contexts.

Does this mean each context must have its own database, deployment pipeline, and independent microservice?

### Challenge 4 — Event-driven workflows

A team wants to activate a subscription by publishing `SubscriptionActivationRequested` and letting several independent consumers update payment, subscription, billing, and customer state.

What additional design decisions are necessary before this becomes a reliable workflow?

### Challenge 5 — Architectural recommendations

You join a seven-person engineering team operating a mature but reasonably reliable Node.js monolith. Its main problems are increasingly complicated business rules, occasional circular imports, and unclear ownership of shared database entities.

Management asks whether the team should migrate to microservices, Clean Architecture, or DDD.

What would you recommend, and in what order?

---

## 14. Solutions and Discussion

### Challenge 1 — Optimize for real change patterns

I would not begin with a complete repository reorganization.

First, investigate which features repeatedly require scattered modifications and whether their underlying responsibilities are genuinely coupled.

Then I would introduce vertical-slice organization incrementally, beginning with an area experiencing frequent change. If the new structure improves navigation, ownership, and testability, the team can adopt it as existing code is touched.

Moving 200 endpoints into new folders without improving the underlying boundaries is expensive housekeeping.

### Challenge 2 — Fakes do not reproduce database behavior

Hexagonal architecture allows application behavior to be tested independently of specific infrastructure implementations, but it does not imply that all testing should avoid real infrastructure.

An in-memory repository may behave differently from PostgreSQL regarding transactions, unique constraints, concurrent updates, ordering, collation, and isolation.

I would use lightweight fakes for focused application tests and real PostgreSQL integration tests where database behavior affects correctness.

An interface helps isolate dependencies. It does not make substitute implementations semantically equivalent.

### Challenge 3 — Logical boundaries do not dictate deployment boundaries

Bounded contexts represent meaningful modeling boundaries, not mandatory microservice boundaries.

Orders, Inventory, and Payments can coexist within one modular monolith and share one PostgreSQL instance while maintaining disciplined ownership.

Even within one database, modules can have separate schemas, restricted access patterns, or clearly defined repository ownership where justified.

Independent databases and deployments should be introduced for operational or organizational reasons, not because a DDD diagram contains three rectangles.

### Challenge 4 — Events require explicit workflow guarantees

The team must determine which operations are mandatory, which can be asynchronous, and which states are permissible during partial failure.

The design also needs durable publication, consumer idempotency, retry policies, ordering assumptions, observability, and a clear owner for overall activation progress.

If payment succeeds but subscription activation fails, who reconciles the operation?

If the system cannot answer that question, it doesn't yet have a reliable workflow. It merely has several consumers hoping to cooperate.

A durable orchestrated process may be preferable to loosely coordinated events when the business operation requires tightly controlled progression.

### Challenge 5 — Repair boundaries before distributing them

I would begin with the actual problems: unclear business ownership, complex domain rules, and undesirable dependencies.

First, identify the main business contexts and clarify ownership of important state transitions. Next, establish module boundaries and gradually remove problematic cross-module imports.

Where business complexity warrants it, use DDD concepts such as explicit domain operations and bounded contexts. Apply dependency inversion selectively where external infrastructure contaminates important business logic.

Only after understanding operational bottlenecks and team coordination costs would I consider extracting independent services.

For seven engineers operating a reasonably reliable application, a stronger modular monolith is the likely first recommendation.

A microservice migration before clarifying domain ownership risks converting one confusing codebase into several confusing systems that now communicate over HTTP.

---

## Mental Model

Architectural patterns are best understood as answers to different kinds of complexity:

- **Layering** separates technical responsibilities.
- **Vertical slices** localize feature implementation.
- **Hexagonal architecture** separates application capabilities from external mechanisms.
- **Clean Architecture** directs dependencies toward fundamental policies.
- **DDD** creates accurate domain models and meaningful business boundaries.
- **Modular monoliths** preserve logical separation without distributed deployment costs.
- **Events** decouple reactions to business occurrences where asynchronous behavior is appropriate.
- **Microservices** introduce independent operational boundaries when their benefits justify the additional complexity.

**The central principle: Choose architectural patterns according to the problems they solve, and adopt only as much of each pattern as the system actually needs.**


---

## Next Lecture — SE330-L03: Maintaining and Evolving Real Software

Continue in **SE330 — Software Architecture and Evolution**.

## Further Reading

1. **Alistair Cockburn — [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)**. The original Ports and Adapters explanation, including the motivation for separating an application from its interfaces and external technologies.

2. **Robert C. Martin — [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)**. The dependency rule and the distinction between business policies and infrastructure mechanisms.

3. **Martin Fowler — [Bounded Context](https://martinfowler.com/bliki/BoundedContext.html)**. Why large business systems need multiple internally consistent domain models rather than one universal representation.

4. **Martin Fowler — [What Do You Mean by Event-Driven?](https://martinfowler.com/articles/201701-event-driven.html)**. An important distinction between event notification, event-carried state transfer, event sourcing, and related approaches.

5. **Microsoft Azure Architecture Center — [Tactical Domain-Driven Design](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/tactical-domain-driven-design)**. A practical explanation of entities, value objects, aggregates, and consistency boundaries.

6. **Eric Evans — *Domain-Driven Design: Tackling Complexity in the Heart of Software***. The foundational book on domain models, ubiquitous language, aggregates, and bounded contexts.

7. **Vaughn Vernon — *Implementing Domain-Driven Design***. A detailed treatment of strategic and tactical DDD, particularly useful for understanding boundaries and aggregate design.

---


