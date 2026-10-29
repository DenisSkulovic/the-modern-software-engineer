---
id: SE320-L01
course: SE320
title: "The Anatomy of a Backend Service"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S01]
prev: null
next: SE320-L02
---

<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE325-L01, SE325-L02, SE325-L06
Preserve this lecture’s service-anatomy focus (layers, middleware, DI, request context).
When SE325 manuscripts exist, add concise cross-references to files/object storage,
bulk data operations, and API protection / multi-tenant fairness.
Do not expand this lecture into those operational deep-dives.
-->










# SE320 — Backend Services and Asynchronous Processing
## Lecture 01: The Anatomy of a Backend Service

*How a request travels through a production backend, why architectural boundaries exist, and how perfectly reasonable code can produce spectacularly unreasonable results.*

---

# 1. The Booking That Succeeded and Failed Simultaneously

It's 14:37 on a Tuesday. A customer is booking a hotel room through your SaaS platform. She selects her dates, enters her details, and clicks **Confirm Reservation**.

The frontend sends a request:

```http
POST /api/reservations
Content-Type: application/json
Authorization: Bearer eyJ...

{
  "hotelId": "hotel_482",
  "roomTypeId": "deluxe",
  "checkIn": "2026-11-12",
  "checkOut": "2026-11-15"
}
```

The request reaches your Node.js backend. The controller is remarkably straightforward:

```typescript
app.post("/api/reservations", async (req, res) => {
  const reservation = await reservationService.create(
    req.body
  );

  res.status(201).json(reservation);
});
```

Underneath it, the service performs three operations:

```typescript
async function create(input: CreateReservationInput) {
  const reservation = await repository.insert(input);

  await notificationService.sendConfirmation(reservation);

  return reservation;
}
```

Reasonable code. An experienced developer could write it in five minutes. But something unusual happens.

The database successfully inserts the reservation. The reservation receives ID `R-10842`. Then the notification service attempts to contact an external email provider.

The email provider accepts the message, but its response is lost because the connection times out. Your backend sees the timeout, throws an exception, and returns:

```http
HTTP/1.1 500 Internal Server Error
```

The customer sees:

> Something went wrong. Please try again.

She clicks again. The second request creates reservation `R-10843`.

The customer now has two reservations, potentially two confirmation emails, and a hotel that thinks it has sold two rooms. Meanwhile, the database is perfectly healthy.

The controller executed exactly as written. The email provider may have delivered both messages. No individual component necessarily malfunctioned.

**The system produced an incorrect business outcome because the responsibilities and guarantees of its components were poorly coordinated.**

This is the first important lesson of backend engineering:

**A backend service is not merely code that receives HTTP requests and performs database operations. It is a mechanism for preserving business rules while coordinating components that operate under different constraints and failure modes.**

Understanding that mechanism is our objective today.

We'll dissect the service from the moment a request enters the Node.js process until the moment a response leaves it. Along the way, we'll discover why routing, middleware, validation, application services, domain logic, repositories, transactions, and background workers exist.

And, more importantly, why their boundaries matter.

---

# 2. The Backend Is Not the Controller

In the web engineering courses (CS230, SE240, SE310), we followed a request across the internet: DNS, connections, TLS, HTTP, proxies, and browser behavior. Now imagine that journey has finished.

An HTTP request has reached our application. What happens? A typical production backend might contain the following logical path:

```text
                 INCOMING HTTP REQUEST
                          |
                          v
              Server / HTTP Framework
                          |
                          v
                 Request Middleware
                          |
              +-----------+-----------+
              |           |           |
         Request ID    Security    Body Parsing
              |           |           |
              +-----------+-----------+
                          |
                          v
                    API Routing
                          |
                          v
                 Authentication
                          |
                          v
              Authorization / Validation
                          |
                          v
                      Controller
                          |
                          v
                Application Service
                          |
                +---------+---------+
                |                   |
                v                   v
           Domain Logic       Dependencies
                |                   |
                +---------+---------+
                          |
                          v
                 Repository / Adapter
                          |
                          v
                  PostgreSQL / Redis
                          |
                          v
                   Service Result
                          |
                          v
                Response Serialization
                          |
                          v
                     HTTP RESPONSE
```

This diagram is illustrative, not a universal execution order. Some validation occurs before authorization, some authorization requires database access, and middleware can run before and after downstream handlers.

The important idea is that a request crosses multiple **responsibility boundaries**. These boundaries are not necessarily separate processes, servers, packages, or classes.

They represent different questions. The HTTP server asks: *How do I receive this request?* The authentication mechanism asks: *Who is making it?*

Authorization asks: *Is that actor permitted to perform this operation?* Validation asks: *Does this input conform to the expected contract?*

The application service asks: *What business operation are we attempting to complete?* The domain logic asks: *What rules govern that operation?*

The persistence layer asks: *How do we retrieve and modify durable data?* And the response layer asks: *How should the result be communicated to the caller?*

A well-designed backend keeps these questions distinguishable.

Not because software architects enjoy drawing boxes—although some very clearly do—but because each question changes for different reasons.

Consider the practical consequences: migrate Express to Fastify, and cancellation-penalty rules should stay unchanged; add a scheduled job that expires unpaid reservations, and you should not need a fake HTTP request just to reuse reservation logic.

Let's investigate how this separation works.

---

# 3. A Request Enters the Node.js Process

Suppose we're running an Express application.

```typescript
import express from "express";

const app = express();

app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.listen(3000);
```

At startup, several things happen.

Node.js initializes its runtime, loads the application modules, registers routes and middleware, and asks the operating system to listen for incoming connections on port 3000.

The operating system manages the network socket. When HTTP data arrives, Node's underlying HTTP machinery parses the message and invokes the framework's request-handling machinery.

Express doesn't personally implement TCP or allocate a dedicated thread for every request. It operates on top of Node's networking and event-driven runtime.

The distinction matters.

A Node.js service can handle many concurrent requests because it doesn't need to keep a JavaScript thread blocked while waiting for every database query or external HTTP response.

For instance:

```typescript
app.get("/users/:id", async (req, res) => {
  const user = await database.findUser(req.params.id);

  res.json(user);
});
```

While `findUser()` waits for the database, Node can continue processing other ready work. But this doesn't mean the backend has unlimited concurrency.

A request consumes resources even while waiting:

- Memory for request objects and application state.
- A place in the event-driven execution machinery.
- Potentially a database connection.
- File descriptors and network resources.
- Capacity in downstream systems.

And CPU-intensive synchronous JavaScript can still monopolize the event loop. Imagine adding this innocent-looking operation:

```typescript
const result = calculateSomethingExpensive();
```

If it takes 800 milliseconds of CPU-bound JavaScript execution, other callbacks on that event-loop thread may be delayed.

The operating system might report that the machine has plenty of unused CPU capacity, yet the application becomes unresponsive.

We encountered this distinction in the computer science foundations courses (CS110, CS220, CS320): **available hardware capacity is not the same thing as available execution capacity within a particular runtime.**

Backend engineering begins with understanding where resources are consumed, where execution waits, and where concurrency is constrained. Our request has now arrived.

Before it reaches the controller, however, it encounters a rather interesting invention. Middleware.

---

# 4. Middleware: The Assembly Line

Imagine a factory manufacturing cars. Before a car leaves the factory, it passes through stations responsible for different operations.

One station installs doors. Another checks electrical systems. Another verifies safety requirements. A backend request-processing pipeline works somewhat similarly.

Middleware functions inspect or transform the request, establish context, reject invalid operations, or pass control onward. In Express:

```typescript
app.use(requestLogger);
app.use(express.json());
app.use(authenticate);

app.post("/reservations", createReservation);
```

Order matters. A request passes through the applicable middleware in registration order, subject to how each middleware chooses to continue, respond, or raise an error.

For example:

```typescript
function requestLogger(req, res, next) {
  console.log(`${req.method} ${req.path}`);
  next();
}
```

Calling `next()` passes control onward. Calling `res.status(401).json(...)` instead terminates the request-response path. And failing to do either can leave the request hanging.

This simple pipeline model is extremely powerful. It allows shared infrastructure concerns to be separated from business-specific concerns.

Typical examples include authentication, body parsing, request identifiers, logging, rate limiting, and input-size restrictions. But there's a trap.

**Not everything that occurs on every request belongs in middleware.**

Developers sometimes build gigantic middleware chains that quietly access databases, modify business state, enforce complicated permissions, and call external services.

Eventually, understanding one request requires reconstructing the behavior of fifteen middleware functions whose interactions aren't obvious.

The backend becomes a haunted house of side effects. A reasonable principle is:

**Middleware should primarily handle transport-level and cross-cutting concerns. Business operations should remain visible in the application's use cases.**

There are exceptions, particularly around security. The distinction is conceptual rather than absolute.

### The security boundary

Suppose you implement authentication:

```typescript
app.use(async (req, res, next) => {
  const token = extractBearerToken(req);

  const identity = await verifyToken(token);

  req.user = identity;

  next();
});
```

Ignoring the omitted error handling and TypeScript request augmentation, this middleware establishes an identity. It answers:

> Who is making this request?

It does not necessarily answer:

> Is this person allowed to modify this reservation?

That second question depends on the specific operation and resource. This separation brings us to one of the most consequential backend design mistakes.

---

# 5. Authentication Is Not Authorization

Suppose your SaaS supports multiple hotels. An employee of Hotel A can manage Hotel A's reservations. An employee of Hotel B can manage Hotel B's reservations.

Your backend exposes:

```http
GET /api/reservations/R-10842
```

The route verifies that the caller has a valid authentication token. Then the controller executes:

```typescript
const reservation = await repository.findById(
  req.params.reservationId
);
```

Can you see the problem? The user is authenticated. The reservation exists.

The database query succeeds. But nothing established that the reservation belongs to a hotel the user may access.

An employee from Hotel B might retrieve Hotel A's reservation simply by changing the identifier. This is a form of broken object-level authorization.

And it's particularly nasty because the application can behave completely correctly according to its implementation. A better interface makes the authorization scope explicit:

```typescript
const reservation = await reservationService.getById({
  reservationId: req.params.reservationId,
  actorId: req.user.id,
  tenantId: req.user.tenantId,
});
```

The application service must enforce the relevant permissions, potentially with a tenant-scoped query:

```sql
SELECT *
FROM reservations
WHERE id = $1
  AND hotel_id = $2;
```

For a system where users can access multiple hotels, the permission model might involve memberships, roles, or resource-specific policies rather than a single `tenantId`.

The key principle remains the same.

**Identity alone does not confer permission over every object reachable through the API.**

Notice something else: we must not blindly accept the tenant identifier from the HTTP request body.

```typescript
// Dangerous if accepted as authoritative:
const tenantId = req.body.tenantId;
```

The client is not an authority on its own permissions.

Tenant scope should be established from trusted identity and authorization information, with explicit business rules governing any requested target tenant.

This is an example of a *trust boundary*. External input crosses into a system that holds more privileges and information than the caller.

At that boundary, the backend must establish what can be trusted.

One architectural advantage of explicit application-service inputs is that authorization doesn't disappear when the operation is invoked from somewhere other than HTTP.

If a worker, CLI tool, or administrator action invokes the same operation, the required security context should still be clear. A useful design question is:

> Could another entry point accidentally bypass the rules that this controller enforces?

If the answer is yes, your boundary deserves attention.

---

# 6. Validation: What Does This Input Actually Mean?

Our incoming booking request contains dates, hotel identifiers, and a room type. We could validate its structure using a library such as Zod.

```typescript
import { z } from "zod";

const createReservationSchema = z.object({
  hotelId: z.string().min(1),
  roomTypeId: z.string().min(1),

  checkIn: z.iso.date(),
  checkOut: z.iso.date(),
});
```

The controller parses the incoming payload:

```typescript
const input = createReservationSchema.parse(req.body);
```

Now we know that certain fields exist and follow the expected structure. But have we established that the reservation is valid? Not remotely.

The checkout date might precede check-in. The room type might not belong to the hotel. The customer might be attempting to book a room that is unavailable.

The hotel might be closed for renovations. The booking might violate a minimum-stay policy. A payment might be required before confirmation.

These are not all the same kind of validation. We should distinguish at least three concerns.

### Structural validation

Does the request have the expected shape? Are required fields present? Are identifiers strings? Are dates correctly formatted? Are values within basic representational limits?

This belongs naturally near the transport boundary.

### Business validation

Does the requested operation make sense according to domain rules? For instance:

```typescript
if (checkOut <= checkIn) {
  throw new InvalidStayDatesError();
}
```

Or:

```typescript
if (stayLength < ratePlan.minimumNights) {
  throw new MinimumStayViolationError();
}
```

These rules often belong in application or domain logic.

### State-dependent validation

Is the operation permitted given the system's current state? Is inventory actually available? Has the reservation already been cancelled?

Is the invoice already paid? This category is especially dangerous because checking a condition doesn't necessarily keep it true.

You might check that one room remains available, then create a reservation. Another concurrent request may do exactly the same thing.

Both requests can observe availability before either modifies it. We will dissect that problem in CS330-L03. For now, remember:

**Validating a snapshot of state is not equivalent to enforcing an invariant against concurrent modification.**

And here's another important design consideration. Never trust client-provided calculations for authoritative business values. If the frontend sends:

```json
{
  "roomTypeId": "deluxe",
  "totalPrice": 1.00
}
```

the backend should not assume the room actually costs one euro.

It should derive authoritative pricing from trusted business data, applying appropriate pricing and promotional rules. The frontend describes what the customer wants.

The backend determines what the customer is allowed to do and what the operation means.

---

# 7. Controllers Should Be Translators, Not Brains

We've authenticated the caller, established the authorization context, and validated the incoming structure. Now we reach the controller. What should it do?

A good controller is essentially an adapter between HTTP and the application's use cases.

It translates request data into an application command, invokes the appropriate operation, and translates the result into an HTTP response. Consider:

```typescript
app.post("/reservations", async (req, res) => {
  const input = createReservationSchema.parse(req.body);

  const result = await reservationService.create({
    actorId: req.user.id,
    tenantId: req.user.tenantId,
    roomTypeId: input.roomTypeId,
    checkIn: input.checkIn,
    checkOut: input.checkOut,
  });

  res.status(201).json({
    id: result.id,
    status: result.status,
  });
});
```

This is a good direction, assuming the route and service enforce the necessary permissions and correctness rules. The controller knows about HTTP.

It knows where request data comes from. It knows which response code should represent success.

But it doesn't need to understand how inventory is reserved, how prices are calculated, or how database transactions are coordinated. Why is that useful?

Imagine a background job that imports reservations from an external booking platform—or a GraphQL resolver for the same operation. Neither should re-implement reservation logic inside its transport; both should invoke the application service. The transport interface changes. The business operation remains conceptually the same.

This gives us a useful distinction:

**A controller represents an entry point. An application service represents a use case.**

One application service might be invoked by several entry points. And the application service itself should represent a meaningful business operation.

Not merely a thin wrapper around a database table. Which brings us deeper into the system.

---

# 8. Application Services and Domain Logic

Consider a reservation operation. A customer wants to book a room. That apparently simple operation might involve:

1. Establishing the customer's permissions.
2. Retrieving the relevant hotel and room information.
3. Evaluating booking rules.
4. Calculating the authoritative price.
5. Reserving inventory.
6. Persisting the reservation.
7. Recording an event for subsequent processing.
8. Returning the reservation result.

Who coordinates these actions? Usually, an **application service**. For example:

```typescript
class CreateReservationService {
  constructor(
    private readonly inventory: InventoryRepository,
    private readonly reservations: ReservationRepository,
    private readonly pricing: PricingService,
    private readonly transactions: TransactionManager
  ) {}

  async execute(command: CreateReservationCommand) {
    // Coordinate the business operation.
  }
}
```

This is only an interface sketch, not a complete booking implementation. We still need correct authorization, concurrency control, and transactional behavior.

But its architectural purpose is clear. The application service orchestrates a use case. Now suppose the hotel has complicated cancellation rules.

Some bookings are refundable up to 48 hours before arrival. Others have tiered penalties. Some promotions prohibit refunds. Where should those rules live?

They could be embedded directly in the application service. For simple domains, that might be perfectly reasonable.

But as the rules become more complicated and reusable, they deserve their own domain concepts.

```typescript
function calculateCancellationPenalty(
  reservation: Reservation,
  policy: CancellationPolicy,
  cancelledAt: Date
): Money {
  // Domain-specific calculation.
}
```

Notice what this function doesn't require. It doesn't need Express. It doesn't need a database connection.

It doesn't need to know what an HTTP status code is. It receives meaningful domain information and calculates a result.

That's an important characteristic of domain logic: it models the rules of the business rather than the mechanics of a delivery technology.

### Application logic versus domain logic

Here's a practical distinction. The application service asks:

> What sequence of responsibilities must be coordinated to complete this operation?

The domain logic asks:

> Given these business facts, what behavior or decision is correct?

For example:

```text
CreateReservationService
    |
    +-- Authorize booking operation
    |
    +-- Load room and rate plan
    |
    +-- Evaluate booking policy
    |
    +-- Calculate price
    |
    +-- Reserve inventory atomically
    |
    +-- Persist reservation
    |
    +-- Record reservation-created event
    |
    +-- Return result
```

The diagram is the division of labor: the service coordinates; pricing, inventory, and persistence each own their part. Of course, reality is rarely this immaculate. Smaller applications often combine responsibilities without serious consequences.

You do not need a separate `CancellationPenaltyCalculationStrategyFactory` merely because somebody read a design-patterns book on a suspiciously productive weekend.

The objective is to isolate genuinely meaningful responsibilities, not maximize the number of files.

**A useful abstraction separates things that need to change independently. A useless abstraction merely relocates code.**

---

# 9. The Persistence Boundary: Why Repositories Exist

At some point, the application must retrieve or modify data. A repository provides an interface for persistence-related operations. For example:

```typescript
interface ReservationRepository {
  findById(
    id: string,
    tenantId: string
  ): Promise<Reservation | null>;

  save(reservation: Reservation): Promise<void>;
}
```

The application service can depend on this interface without knowing whether it is implemented through TypeORM, raw PostgreSQL queries, or something else. That sounds attractive.

But repositories are also frequently overengineered. Consider this generic abstraction:

```typescript
interface Repository<T> {
  create(entity: T): Promise<T>;
  update(entity: T): Promise<T>;
  delete(id: string): Promise<void>;
  findAll(): Promise<T[]>;
}
```

It looks reusable. Unfortunately, real business operations rarely fit neatly into generic CRUD methods.

A reservation system might need to retrieve overlapping bookings, lock inventory rows, fetch a paginated customer history, or atomically claim an available room.

A generic repository often fails to express those operations clearly.

Developers then add more layers, custom query specifications, and escape hatches until the abstraction becomes more complicated than the database it was designed to hide.

A better rule is:

**Design persistence interfaces around the operations the application actually needs.**

Sometimes that means a domain-oriented repository. Sometimes it means a query service returning specialized read models.

And sometimes a straightforward TypeORM repository used within a well-defined module is sufficient. The purpose isn't to pretend PostgreSQL doesn't exist.

Database capabilities influence architecture. Transactions, constraints, indexes, and concurrency semantics matter.

An abstraction should protect useful boundaries without concealing important guarantees.

### Dependency direction

Consider two possible designs.

**Design A:**

```text
HTTP Controller
      |
      v
TypeORM Repository
      |
      v
PostgreSQL
```

Business rules may end up scattered between the controller and persistence calls.

**Design B:**

```text
HTTP Controller
      |
      v
Application Service
      |
      +----> Domain Rules
      |
      v
Persistence Interface
      ^
      |
PostgreSQL Implementation
```

In Design B, the application defines what persistence behavior it requires. Infrastructure provides an implementation. This is a form of dependency inversion.

It is particularly valuable when you want business logic to remain independently testable, or when several entry points reuse the same application behavior.

But it's not an obligation to build a framework inside your framework.

For a modest SaaS backend, I would generally prefer a modular monolith with explicit feature boundaries, relatively simple application services, and selective persistence abstractions.

That produces most of the architectural benefits without unnecessary ceremony.

---

# 10. Transactions: Where Does an Operation Begin and End?

Now we arrive at the problem that opened this lecture. Suppose creating a reservation requires three database changes:

- Insert the reservation.
- Decrease available inventory.
- Insert an audit record.

We don't want to persist the reservation if updating inventory fails. Nor do we want to decrement inventory without recording the reservation. These changes belong together.

A database transaction allows us to define an atomic unit of database work. Using PostgreSQL through `node-postgres`, the basic pattern looks like this:

```typescript
const client = await pool.connect();

try {
  await client.query("BEGIN");

  await client.query(
    `INSERT INTO reservations (...) VALUES (...)`
  );

  await client.query(
    `UPDATE inventory SET ... WHERE ...`
  );

  await client.query(
    `INSERT INTO audit_log (...) VALUES (...)`
  );

  await client.query("COMMIT");
} catch (error) {
  await client.query("ROLLBACK");
  throw error;
} finally {
  client.release();
}
```

The SQL statements here are schematic; actual inventory updates must enforce concurrency-safe business conditions.

An important detail: every statement participating in this PostgreSQL transaction must use the **same database client connection**.

Calling `pool.query()` independently for each statement does not preserve a shared transaction. And the acquired client must be returned to the pool when finished.

But notice something subtle. What happens if we add this inside the transaction?

```typescript
await emailProvider.sendConfirmation(reservation);
```

Now our database transaction contains an external side effect.

If the email is successfully delivered and then the database transaction rolls back, we've sent confirmation of a reservation that doesn't exist.

Alternatively, if the database commits successfully and the email operation times out afterward, we may return an error even though the reservation exists.

A PostgreSQL transaction cannot roll back a message already delivered by an email provider.

**A database transaction establishes guarantees within the database. It does not magically make external systems participate in those guarantees.**

This is why the transaction boundary and the application-service boundary are related but not identical.

An application use case may coordinate a business workflow larger than any individual database transaction.

Later in this course, we'll examine the transactional outbox pattern, durable workflows, idempotency, and reconciliation.

For now, one practical improvement is to record a durable notification intent alongside the reservation.

```text
DATABASE TRANSACTION
    |
    +-- Insert reservation
    |
    +-- Update inventory
    |
    +-- Insert notification-outbox record
    |
    +-- COMMIT
```

A separate worker later processes the outbox record and sends the email.

This does not automatically guarantee that the email will be delivered exactly once. The worker can still crash after sending but before recording completion.

What it does provide is a durable record of work that must be attempted and recovered. We've separated **committing the reservation** from **delivering its confirmation**—different failure modes that should not share one synchronous success condition.

---

# 11. Background Work: Not Everything Belongs in the Request

A reservation succeeds. Now the system wants to:

- Send confirmation emails.
- Update analytical reports.
- Notify a channel manager.
- Generate an invoice PDF.
- Synchronize a CRM.
- Run a fraud-detection process.

Should the user wait for all six operations? Usually not.

Some operations are necessary before the reservation can be considered accepted. Others are consequences of an already accepted reservation.

This introduces an architectural distinction between **synchronous requirements** and **asynchronous consequences**.

A synchronous requirement must complete before the backend can truthfully promise the requested result.

An asynchronous consequence can happen afterward under a separate reliability contract. For instance:

```text
            Create Reservation Request
                        |
                        v
                 Application Service
                        |
                        v
               Commit Reservation
                        |
                        v
                  HTTP 201 Created

                        |
                 Durable Outbox
                        |
                        v
                  Background Worker
                        |
              +---------+---------+
              |                   |
              v                   v
         Send Email        Update External CRM
```

The worker might use BullMQ and Redis, a cloud queue, or another processing mechanism. But be careful with a tempting shortcut:

```typescript
await reservationRepository.save(reservation);

await queue.add("send-email", {
  reservationId: reservation.id,
});
```

What happens if the database save succeeds but the queue operation fails? We have a reservation without the expected notification job. The inverse ordering has its own problems.

This is the **dual-write problem**: two independent systems must be updated, but there's no shared atomic transaction.

A transactional outbox helps when the application database can durably record the intended work in the same transaction as the business change.

We'll study queues deeply in SE320-L03, where the innocent-looking phrase *process this job once* becomes considerably more complicated than it sounds.

For now, the larger architectural lesson is that background processing isn't simply a performance trick. It establishes a different execution and recovery model.

And the location of that boundary determines what your HTTP endpoint can honestly promise.

---

# 12. Dependency Injection: Who Builds the Machine?

We've introduced controllers, application services, repositories, pricing policies, and external adapters. How do these objects obtain their dependencies?

One approach is to instantiate everything wherever it's needed.

```typescript
class ReservationService {
  private repository = new PostgresReservationRepository();
  private payments = new StripePaymentService();
}
```

Simple. But the class now decides both what work to perform and which concrete infrastructure implementations to use.

Testing becomes harder. Configuration becomes scattered. Replacing dependencies requires modifying the class. Another approach is constructor injection:

```typescript
class ReservationService {
  constructor(
    private readonly repository: ReservationRepository,
    private readonly payments: PaymentGateway
  ) {}
}
```

The service receives dependencies rather than constructing them. Somewhere near application startup, we assemble the actual system.

```typescript
const repository = new PostgresReservationRepository(pool);

const paymentGateway = new StripePaymentGateway(config);

const reservationService = new ReservationService(
  repository,
  paymentGateway
);
```

This assembly location is sometimes called the **composition root**. It's an important architectural concept.

The application is a network of collaborating objects and services. Something must construct that network. Dependency injection makes those connections explicit.

Frameworks such as Spring and NestJS provide dependency-injection containers that automate much of this work. But dependency injection itself doesn't require a framework.

Nor does every application benefit from a sophisticated container. For a small or medium Node.js backend, explicit construction can be refreshingly understandable.

For a larger application with many lifecycle-managed dependencies, a container may reduce repetitive wiring. The interesting principle is not the technology.

It's that the business operation should not unnecessarily control the construction of the infrastructure it depends upon.

### Beware the opposite extreme

Dependency injection can also become a source of needless complexity.

If a codebase contains interfaces, factories, providers, decorators, adapters, registries, and configuration wrappers for every two-line helper function, something has gone wrong.

A good boundary exists because it protects a meaningful design decision. Not because every class is legally required to have an interface.

---

# 13. Organizing a Backend: Layers Versus Features

Imagine a growing SaaS application. It contains reservations, hotels, billing, users, notifications, and integrations. One possible directory structure is:

```text
src/
  controllers/
    reservation.controller.ts
    hotel.controller.ts
    billing.controller.ts

  services/
    reservation.service.ts
    hotel.service.ts
    billing.service.ts

  repositories/
    reservation.repository.ts
    hotel.repository.ts
    billing.repository.ts

  models/
  validators/
  utils/
```

This groups files by technical responsibility. It works reasonably well when the application is small.

But as it grows, implementing one reservation feature may require editing files scattered across six directories. Another structure groups code by business capability:

```text
src/
  modules/
    reservations/
      api/
        reservation.routes.ts
        reservation.controller.ts

      application/
        create-reservation.ts
        cancel-reservation.ts

      domain/
        reservation.ts
        cancellation-policy.ts

      infrastructure/
        postgres-reservation-repository.ts

    billing/
    hotels/
    users/
    notifications/

  shared/
    database/
    logging/
    errors/

  bootstrap/
    app.ts
```

Now the reservation module contains much of what is needed to understand reservations. Within the module, we can still separate technical responsibilities.

This is often called **feature-oriented** or **vertical-slice organization**. The benefits become noticeable when the codebase grows:

A developer can investigate a feature without touring the entire repository. Modules can establish clearer ownership of domain rules. Changes are more likely to remain localized.

Dependencies between business capabilities become easier to identify. But directories alone do not establish architectural boundaries.

If every module imports every other module's internal services and directly modifies every database table, the folder structure is mostly decorative.

A meaningful module boundary controls what other modules are permitted to depend upon. For example, the billing module might expose:

```typescript
billingService.createInvoiceForReservation(...)
```

It should not require reservation code to know the details of billing's internal invoice tables. This is precisely where the modular monolith from the web engineering courses (CS230, SE240, SE310) becomes interesting.

**A modular monolith provides meaningful internal boundaries while retaining a single deployable application.**

You gain the ability to reason about independently evolving capabilities without immediately paying the operational and consistency costs of distributed microservices.

For many business applications, that's a very attractive bargain.

---

# 14. Request Context: Following One Request Through the Maze

Let's return to production. Your logs contain these messages:

```text
14:37:12 Query started
14:37:12 Customer loaded
14:37:12 Reservation validation failed
14:37:12 Query completed
14:37:12 External API timeout
14:37:12 Response 500
```

Which messages belong to the same request? With dozens of concurrent requests, timestamps alone aren't sufficient. A useful technique is to assign each request a unique identifier.

```text
requestId = req_82fa91
```

Then logs become:

```text
[req_82fa91] Reservation creation started
[req_82fa91] Inventory checked
[req_82fa91] Database committed
[req_82fa91] Notification timeout
[req_82fa91] Response 500
```

Now we have a coherent story. This becomes more useful when the request crosses modules and external services.

But how does a function deep inside the repository obtain the request identifier? We could pass it explicitly through every method.

```typescript
await reservationService.create(input, context);
```

That's clear and often appropriate. Alternatively, Node.js provides `AsyncLocalStorage`, which can associate context with an asynchronous execution chain. A simplified example:

```typescript
import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";

type RequestContext = {
  requestId: string;
};

const requestContext =
  new AsyncLocalStorage<RequestContext>();

app.use((req, res, next) => {
  requestContext.run(
    { requestId: randomUUID() },
    () => next()
  );
});
```

Later:

```typescript
function log(message: string) {
  const requestId =
    requestContext.getStore()?.requestId ?? "unknown";

  console.log(`[${requestId}] ${message}`);
}
```

The logging function doesn't need an explicit context argument. Node maintains the association through supported asynchronous execution paths.

This is useful for logging, tracing, and request-local metadata. But it shouldn't become an excuse to hide essential business inputs.

A reservation service that secretly reads the current tenant from ambient context is harder to reason about than one whose authorization scope is explicit. I would generally favor:

- Ambient context for diagnostic information such as request IDs.
- Explicit parameters for business-critical information such as actor identity, tenant scope, and transaction ownership.

Also, asynchronous request context is not durable workflow state.

When a background worker processes a job tomorrow, it needs appropriate identifiers and business context recorded in the job or persistent state. It cannot simply inherit the HTTP request's memory.

That distinction will become increasingly important as our systems grow more distributed.

---

# 15. Error Handling Is Part of the API Contract

Consider these failures:

1. The customer submits malformed dates.
2. The user isn't authenticated.
3. The user attempts to access another hotel's reservation.
4. The reservation has already been cancelled.
5. PostgreSQL is temporarily unavailable.
6. The external payment service times out.

Should all six return HTTP 500? Definitely not. They represent fundamentally different outcomes.

An API should communicate failures in a form that allows callers to make appropriate decisions. A practical mapping might look like this:

| Situation | Typical HTTP response |
|---|---|
| Malformed request | `400 Bad Request` |
| Authentication required or invalid | `401 Unauthorized` |
| Authenticated but not permitted | `403 Forbidden` |
| Resource doesn't exist or isn't disclosed | `404 Not Found` |
| Conflict with current state | `409 Conflict` |
| Semantically invalid input | `422 Unprocessable Content` |
| Rate limit exceeded | `429 Too Many Requests` |
| Unexpected server failure | `500 Internal Server Error` |
| Temporarily unavailable dependency/service | `503 Service Unavailable` |

These mappings are conventions, not substitutes for understanding the semantics of an actual failure.

For example, some systems deliberately return 404 instead of 403 to avoid revealing the existence of protected resources.

The internal application might define meaningful error types:

```typescript
class ReservationConflictError extends Error {}

class PermissionDeniedError extends Error {}

class InventoryUnavailableError extends Error {}
```

Then the HTTP adapter maps them into appropriate responses.

```typescript
if (error instanceof ReservationConflictError) {
  return res.status(409).json({
    code: "RESERVATION_CONFLICT",
    message: "Reservation conflicts with current state",
  });
}
```

The application service shouldn't need to throw an HTTP-specific exception merely to express that inventory is unavailable.

And the frontend shouldn't have to parse arbitrary English error messages to determine what happened. A stable machine-readable code is considerably better.

### Unexpected errors

Unexpected failures require a different treatment. Log enough information internally to investigate them, including a correlation identifier and relevant safe context.

Return a controlled response to the client. Don't expose database credentials, SQL queries, internal stack traces, or secret values. For example:

```json
{
  "code": "INTERNAL_ERROR",
  "message": "The operation could not be completed",
  "requestId": "req_82fa91"
}
```

One more technical detail: Express 5 automatically forwards rejected promises returned from asynchronous route handlers to its error-handling pipeline.

That convenience does not extend to arbitrary detached promises or background work that a handler launches without returning or awaiting.

Error handling must cover the actual execution path.

### The genuinely difficult part

Sometimes the server cannot determine whether a business operation succeeded. Imagine a client disconnecting immediately after the database commits.

The backend has created the reservation, but the client never receives the response. From the client's perspective, the outcome is uncertain.

This is why a production API needs more than good error messages. It needs a strategy for retrying operations safely and retrieving their eventual status.

That takes us directly into distributed-systems territory.

---

# 16. Resource Lifecycles: The Invisible Limits

Suppose your application behaves correctly at ten requests per second. At two hundred requests per second, latency becomes catastrophic. You inspect the database.

It isn't consuming much CPU. You inspect the application. Its CPU usage also looks reasonable.

What's happening? Consider database connection pooling. A PostgreSQL pool might permit ten active connections from a particular application instance.

If all ten are busy, additional operations must wait for a connection. Suppose each database operation takes 50 milliseconds.

Under idealized conditions, ten continuously occupied connections could complete roughly 200 such operations per second.

But actual performance depends on transaction durations, query mixes, database contention, scheduling, and many other factors.

Now imagine a developer accidentally leaves a transaction open while waiting for an external API.

Instead of holding a database connection for 50 milliseconds, the request holds it for three seconds. Ten concurrent requests may exhaust the entire pool.

Incoming requests accumulate while waiting for connections. CPU usage remains relatively low. The service appears mysteriously slow.

This is a resource-management failure, not necessarily a computational performance failure. The solution isn't automatically to increase the pool size.

That might simply transfer more pressure to PostgreSQL. First investigate why connections are occupied and for how long.

Other constrained resources include outbound HTTP connection pools, memory, worker capacity, open file descriptors, external API rate limits, and the event loop itself.

### Startup and shutdown matter too

A backend has a lifecycle beyond handling requests. At startup, it may need to load configuration, initialize dependencies, and establish whether it can serve traffic.

At shutdown, it should stop accepting new work, allow appropriate in-flight operations to finish within a bounded grace period, and close resources. A useful distinction is:

**Liveness:** Is the process alive and able to make progress?

**Readiness:** Is it currently able to serve the traffic it is supposed to receive?

A backend might be alive but unable to acquire any database connections. Returning `200 OK` from a hardcoded `/health` endpoint doesn't prove that the service is ready.

At the same time, readiness checks should be designed carefully. If every instance performs expensive dependency queries every second, your health-check mechanism becomes its own source of load.

Production engineering repeatedly teaches the same lesson:

**A system must manage its own resources and lifecycle, not merely implement correct business functions.**

---

# 17. Returning to the Original Incident

We can finally reconstruct the booking failure. Our original implementation was:

```typescript
async function create(input: CreateReservationInput) {
  const reservation = await repository.insert(input);

  await notificationService.sendConfirmation(reservation);

  return reservation;
}
```

Three responsibilities were mixed together:

**First:** Persist the reservation.

**Second:** Deliver an external notification.

**Third:** Define whether the HTTP operation should be considered successful.

The first operation succeeded. The second operation produced an ambiguous timeout. The third operation incorrectly treated that timeout as evidence that the booking failed.

The customer retried. Because the operation lacked a durable idempotency mechanism, the retry created a second reservation. How should we redesign it?

For a reasonably serious booking system, I would establish the following boundaries. The controller validates incoming data and identifies the authenticated actor.

The application service authorizes the booking operation and coordinates the use case. The domain logic evaluates relevant booking rules.

The database transaction atomically enforces inventory and reservation invariants while recording the resulting business event.

The system returns a truthful response describing the committed reservation. A separate worker handles notification delivery from durable work records.

And the booking operation supports a retry strategy that avoids creating duplicate business effects. A possible internal flow:

```text
POST /reservations
        |
        v
Authenticate + Validate
        |
        v
CreateReservation Use Case
        |
        +-- Authorize actor and tenant
        |
        +-- Check existing idempotency operation
        |
        +-- Determine authoritative pricing
        |
        v
DATABASE TRANSACTION
        |
        +-- Enforce inventory invariant
        |
        +-- Persist reservation
        |
        +-- Persist operation result / idempotency state
        |
        +-- Insert outbox event
        |
        +-- COMMIT
        |
        v
Return successful operation result
        |
        |
        +------ Asynchronous processing ----+
                                            |
                                            v
                                       Outbox Worker
                                            |
                                            v
                                     Notification Provider
```

There are still important complexities. How exactly does the database prevent concurrent double bookings? How does the idempotency mechanism handle simultaneous retries?

What if the worker sends an email but crashes before acknowledging it? What happens if inventory is managed by an external hotel supplier rather than our database?

Those are real problems, and we'll investigate them in subsequent sessions. But notice what the architecture has accomplished. It has made the responsibilities visible.

We know which component establishes identity, which enforces business rules, which guarantees atomic local persistence, and which performs recoverable asynchronous work.

When something fails, we have a much clearer idea of which guarantees should still hold. That is the practical value of backend architecture. Not elegance for its own sake.

**Clarity about responsibility, ownership, and failure behavior.**

---

# 18. Practical Investigation: The Successful Operation That Returns 500

Let's reproduce the original problem.

This experiment intentionally uses a small in-memory application rather than PostgreSQL. The goal is to isolate the backend's control flow and the difference between business success and HTTP success.

You'll need Node.js and Express. Create a small project:

```bash
npm init -y
npm install express@5
```

Create `server.mjs`:

```javascript
import express from "express";

const app = express();

app.use(express.json());

const reservations = [];

let emailAttempts = 0;

async function sendConfirmation(reservation) {
  emailAttempts++;

  // Simulate an external service that accepted
  // the operation but whose response timed out.
  throw new Error("Email provider timeout");
}

app.post("/reservations", async (req, res) => {
  const reservation = {
    id: crypto.randomUUID(),
    customer: req.body.customer,
    status: "confirmed",
  };

  reservations.push(reservation);

  await sendConfirmation(reservation);

  res.status(201).json(reservation);
});

app.get("/debug", (_req, res) => {
  res.json({
    reservations,
    emailAttempts,
  });
});

app.use((error, _req, res, _next) => {
  console.error(error.message);

  res.status(500).json({
    error: "Reservation creation failed",
  });
});

app.listen(3000, () => {
  console.log("Server listening on port 3000");
});
```

For clarity, add this import at the top:

```javascript
import crypto from "node:crypto";
```

Run:

```bash
node server.mjs
```

Create a reservation:

```bash
curl -i -X POST http://localhost:3000/reservations \
  -H "Content-Type: application/json" \
  -d '{"customer":"Alice"}'
```

The server returns HTTP 500. Try the request again. Then inspect the state:

```bash
curl http://localhost:3000/debug
```

You'll find two confirmed reservations. The API claimed failure twice. The internal business state changed twice.

The simulation doesn't actually deliver email. It deliberately models the situation where the external call's outcome is not known to the caller.

### Investigation A

Move the notification call after `res.status(201).json(reservation)`. Does that solve the problem?

It prevents the email timeout from changing the already-sent HTTP success response. But new issues appear. The notification still fails.

The detached asynchronous operation needs its own error handling. The process could crash before attempting it.

And there is no durable record requiring the notification to be retried. We've improved one failure mode without establishing reliable delivery.

### Investigation B

Introduce an `Idempotency-Key` header. Store a mapping from the key to the created reservation.

When the same key is received again, return the original reservation instead of creating another.

This basic experiment demonstrates the idea, but a production implementation needs more. The idempotency record should survive process restarts.

It must handle concurrent requests with the same key. It should be scoped appropriately to the tenant and operation.

It should reject incompatible reuse of the same key with a different request payload.

And the idempotency state must be coordinated atomically with the business outcome, or it can disagree with the reservation database.

A `Map` in memory is a teaching demonstration, not a reliable production solution.

### Investigation C

Ask yourself which part of the implementation truly represents the business operation. Is it `res.status(201).json(...)`? Is it `reservations.push(...)`?

Is it the successful email delivery? This question forces you to define the application's success boundary.

And until that boundary is defined, writing correct retry behavior is largely guesswork.

---

# 19. Engineering and Interview Challenges

Try reasoning through these before reading the discussion.

### Question 1 — Where should authorization live?

A controller verifies that the caller has permission to cancel a reservation.

The underlying `CancelReservationService` assumes authorization has already happened.

Later, a scheduled worker calls the service directly.

What architectural risk does this introduce, and how would you address it?

### Question 2 — Is a repository always necessary?

You're building a relatively small Node.js SaaS backend using TypeORM.

A colleague insists that every entity must have its own repository interface, implementation, generic base repository, and factory.

Is that genuinely good architecture?

What factors should influence your decision?

### Question 3 — The mysterious production slowdown

Your Node.js service suddenly becomes slow.

CPU utilization is 25%.

PostgreSQL CPU utilization is 18%.

The average API response time has increased from 120 milliseconds to eight seconds.

What would you investigate before scaling the service?

### Question 4 — When is the operation complete?

A customer submits an order.

The database commits the order successfully.

A CRM synchronization call fails.

Should the API return success or failure?

What conditions determine the answer?

### Question 5 — The modular monolith

Your application has reservation, billing, and notification modules.

All modules live in one Node.js deployment and share one PostgreSQL database.

Does this mean the application has no meaningful modular boundaries?

What makes those boundaries real rather than cosmetic?

---

# 20. Solutions and Discussion

### 1. Authorization should survive alternative entry points

The design assumes that all callers enter through a controller with the correct authorization checks. The worker violates that assumption.

One solution is to require a meaningful authorization or execution context at the application-service boundary.

For example, an interactive operation might require an authenticated actor with permission over the target reservation.

A scheduled operation might execute under a narrowly defined system identity with explicitly permitted capabilities.

Some authorization checks can still occur in controllers or middleware, but security-critical business permissions should not accidentally disappear when the same use case is invoked elsewhere.

The guiding principle is to establish authorization at a boundary that every relevant execution path respects.

### 2. Repository abstractions should earn their existence

No, every database entity does not automatically need several layers of abstraction.

A repository is useful when it expresses meaningful persistence operations, protects domain boundaries, provides a useful testing seam, or isolates infrastructure details that genuinely need independent evolution.

For straightforward CRUD operations, direct use of TypeORM within a well-contained application module might be entirely acceptable.

A generic abstraction that simply mirrors every ORM method adds little value. The correct question is not whether the code conforms to a preferred architectural pattern.

It's whether the abstraction makes the system easier to understand, change, and test.

### 3. Investigate waiting, not just computation

Low CPU utilization doesn't prove that the system has spare effective capacity.

Possible explanations include exhausted database connection pools, long-running transactions, slow external services, outbound connection limits, lock contention, event-loop blocking, and resource queues.

I would begin with latency breakdowns, dependency timing, connection-pool metrics, event-loop delay, and traces from representative slow requests.

If requests spend seven seconds waiting for database connections and 15 milliseconds executing SQL, scaling application instances may actually worsen database connection pressure.

Identify the bottleneck before adding capacity.

### 4. Success depends on the business contract

If CRM synchronization is an asynchronous consequence of accepting the order, the API should generally return success after the authoritative order state is committed.

The failed synchronization must be recorded and retried separately.

If the external service is genuinely part of the operation's required acceptance criteria, things become more complex.

We must decide whether to represent the order as pending, rejected, or requiring reconciliation. The service must communicate a state it can actually justify.

A remote timeout alone cannot prove that the remote operation failed.

### 5. A shared database doesn't eliminate modular boundaries

A modular monolith can absolutely have meaningful boundaries while sharing deployment and infrastructure.

What matters is whether modules own their business responsibilities, expose deliberate interfaces, avoid unauthorized manipulation of one another's internals, and maintain understandable dependency directions.

A billing module that owns invoice creation and exposes appropriate operations is meaningfully separated from reservations.

A billing folder whose tables are freely modified by every other module is not.

A single deployment makes certain kinds of coordination easier, but it doesn't automatically establish or destroy architectural discipline.

---

# 21. The Mental Model to Keep

We've examined a backend service from the inside. The most useful mental model is not a particular folder structure or architecture diagram. It's a sequence of responsibilities:

**Transport receives the request.**

**Authentication establishes identity.**

**Authorization establishes permission.**

**Validation establishes acceptable input.**

**Application services coordinate business operations.**

**Domain logic defines business rules.**

**Persistence components interact with durable state.**

**Transactions define atomic database boundaries.**

**Background processing handles work under separate execution and recovery guarantees.**

**Error handling communicates outcomes without misrepresenting what happened.**

**Observability and resource management make the system operable in production.**

In a small application, some of these responsibilities may share the same function or class. That's fine.

Architectural boundaries do not need to become physical boundaries everywhere.

But as a system becomes more complex, distinguishing these responsibilities becomes increasingly valuable.

It allows you to identify where a guarantee must be enforced, where a failure can occur, and which component should own the response.

The senior-engineering skill is not memorizing a fashionable arrangement of controllers, services, and repositories. It's looking at an unfamiliar backend and being able to ask:

**What is this component responsible for? What does it assume? What does it guarantee? What happens when that assumption is violated?**

Those questions are considerably more powerful than knowing which decorator to place above a controller method.

---

# Coming Next — CS330-L01: Relational Database Design

Today, we've treated PostgreSQL as a persistence mechanism behind an application boundary. But a database is not merely a place where objects go to sleep between HTTP requests.

Its structure determines which relationships can be represented, which inconsistencies can be prevented, and how painful future changes become.

Imagine launching a hotel-booking product with a perfectly reasonable database schema.

One year later, the business introduces shared inventory, multi-room bookings, changing room assignments, flexible pricing, and partial refunds.

Suddenly, a schema that worked beautifully for the original application becomes an obstacle to everything the business wants to do. Why?

Because database design is not simply the act of turning TypeScript classes into SQL tables.

It's the act of modeling a world whose rules, relationships, and invariants must survive change.

In our next session, we'll investigate **relational modeling, normalization, constraints, and schema evolution**, beginning with the surprisingly difficult question:

*What exactly is a hotel room reservation?*

A room? A room type? A promise of capacity? A financial commitment? A relationship between a guest and a changing inventory system?

As we'll discover, the answer has architectural consequences long before anyone writes their first SQL query.

---


---

## Next Lecture — SE320-L02: Caching: Trading Freshness for Speed

Continue in **SE320 — Backend Services and Asynchronous Processing**.

## Further Reading

These references complement the lecture without being prerequisites:

- **Express — Using Middleware:** https://expressjs.com/en/guide/using-middleware/
- **Express 5 — Error Handling:** https://expressjs.com/en/5x/guide/error-handling/
- **Node.js — AsyncLocalStorage:** https://nodejs.org/api/async_context.html
- **node-postgres — Transactions:** https://node-postgres.com/features/transactions
- **node-postgres — Connection Pooling:** https://node-postgres.com/features/pooling
- **OWASP — Authorization Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html


---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE320-L01  BACKEND ANATOMY — INTERVIEW GLANCE CARD

CORE MODEL
  Backend ≠ controller + DB call
  Preserve business rules while coordinating components with
  different constraints / failure modes
  Request crosses responsibility boundaries (questions), not
  necessarily separate processes

REQUEST PATH (illustrative)
  HTTP server → middleware → routing → authN → authZ/validation
  → controller → application service → domain + deps
  → repository/adapter → DB → serialize → response

RESPONSIBILITY QUESTIONS
  Transport     How receive?
  AuthN         Who?
  AuthZ         Permitted for THIS operation/resource?
  Validation    Input contract?
  App service   What business operation?
  Domain        What rules?
  Persistence   How retrieve/modify durable data?
  Response      How communicate outcome?

MIDDLEWARE
  Cross-cutting / transport: logging, body parse, request ID,
  rate limit, authN identity
  Call next() OR respond OR hang
  Trap: giant chains with DB writes / business side effects
  Business ops stay visible in use cases

AUTHN ≠ AUTHZ
  Valid token ≠ may access every ID (BOLA / object-level authZ)
  Scope from trusted identity, not client body.tenantId
  Trust boundary: external input → privileged system
  AuthZ must survive workers/CLI — not only HTTP controller

VALIDATION LAYERS
  Structural   shape near transport (e.g. Zod)
  Business     domain rules (dates, min stay…)
  State-dep.   inventory/paid/cancelled — snapshot ≠ concurrent invariant
  Never trust client totals/prices as authoritative

CONTROLLER vs APPLICATION SERVICE
  Controller = HTTP adapter (parse, status, shape)
  App service = use case (reusable from jobs/GraphQL)
  Domain = rules without Express/HTTP/DB

PERSISTENCE
  Design interfaces around needed ops, not generic CRUD
  Dependency inversion: app owns ports; infra implements
  Modular monolith: feature modules + deliberate public APIs
  Folders ≠ boundaries if every module mutates every table

TRANSACTIONS & SIDE EFFECTS
  Same client for BEGIN…COMMIT; pool.query() ≠ shared txn
  DB txn ≠ external email/payment atomicity
  Dual-write: DB + queue.add() not atomic
  Prefer outbox intent in same txn; worker delivers later

SYNC vs ASYNC
  Sync: must complete before truthful promise
  Async: consequence under separate recovery contract
  Background work ≠ mere performance trick

DI / COMPOSITION
  Composition root assembles deps; business shouldn't own infra construction
  DI ≠ need a heavy container for every helper

REQUEST CONTEXT
  requestId for log correlation; AsyncLocalStorage OK for diagnostics
  Explicit params for actor/tenant/txn ownership
  Ambient context ≠ durable worker state tomorrow

ERRORS (typical mapping)
  400 malformed · 401 authN · 403 forbidden · 404 missing/undisclosed
  409 conflict · 422 semantic · 429 rate · 500 unexpected · 503 unavailable
  App errors → HTTP adapter maps; machine-readable codes
  Don't leak stacks/SQL/secrets; uncertain outcome ≠ proven failure

RESOURCES / LIFECYCLE
  Hardware free ≠ runtime capacity (pool, event loop, FDs)
  Hold DB conn while awaiting HTTP → pool exhaustion, low CPU
  Liveness vs readiness; /health ≠ ready if DB unreachable
  Manage resources + lifecycle, not only correct functions

INCIDENT PATTERN
  Persist OK + notify timeout → 500 → retry → duplicates
  Fix: truthful commit boundary + outbox + idempotency

SENIOR LINE: What responsible? Assume? Guarantee? When assumption breaks?
```

---

