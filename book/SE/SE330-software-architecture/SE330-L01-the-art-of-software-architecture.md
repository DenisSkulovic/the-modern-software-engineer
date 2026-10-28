---
id: SE330-L01
course: SE330
title: "The Art of Software Architecture"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S01]
prev: null
next: SE330-L02
---









# SE330 — Software Architecture and Evolution

## Lecture 01: The Art of Software Architecture

*Why perfectly functional software can become extraordinarily expensive to change.*

---

## 1. The Application That Became Afraid of Change

Imagine a SaaS company operating a successful hotel-booking platform. Its application handles reservations, payments, availability, customer notifications, invoices, and integrations with external hotel-management systems.

The engineering team consists of eight developers. The application has been running in production for four years, processes thousands of reservations daily, and has reasonably good automated test coverage. Customers are satisfied, revenue is growing, and the system rarely experiences outages.

Then the product manager requests a seemingly modest feature:

**Allow selected corporate customers to reserve rooms without paying immediately.**

Currently, every reservation requires immediate payment. Corporate customers should instead receive an invoice with a payment deadline.

A developer estimates three days. The feature eventually consumes four weeks.

Why?

The investigation reveals something peculiar. Payment assumptions are scattered throughout the entire application:

- The booking service assumes that a successful reservation always has a completed payment.
- The notification service checks a `paid` boolean before sending confirmations.
- The reporting system infers revenue from reservation creation.
- The cancellation workflow assumes every confirmed reservation has a refundable transaction.
- Several frontend components independently calculate whether a reservation is valid.
- A shared `BookingUtils` module contains a growing collection of payment-related conditions.
- Database entities are imported directly into unrelated business modules.

None of these decisions was particularly unreasonable when originally implemented. The first version of the product genuinely required immediate payment, and each developer solved the problem in front of them.

Yet together, these decisions created an architecture in which a change to one business rule propagated through much of the system.

The company has discovered an uncomfortable truth: **software can remain functionally correct while becoming structurally unhealthy.**

Two systems may implement exactly the same features, use the same programming language, serve the same traffic, and produce identical results. Nevertheless, one may accommodate a new requirement in two days while the other requires weeks of coordinated modifications.

Understanding why is the central concern of software architecture.

---

## 2. What Architecture Actually Is

Software architecture is frequently described through diagrams showing boxes connected by arrows. One box represents the frontend, another the backend, another PostgreSQL, and perhaps several fashionable clouds float around the edges.

Such diagrams can be useful, but they aren't architecture itself. They merely illustrate selected aspects of the system.

Architecture concerns the **important structural decisions that shape what a system can do, how it behaves, and how difficult it will be to change**.

Consider several decisions:

- Whether payment processing is embedded throughout reservation code or isolated behind a business boundary.
- Whether different modules directly access each other's database tables.
- Whether background operations execute synchronously during HTTP requests or through durable workers.
- Whether the application deploys as one unit or several independently deployed services.
- Whether business rules depend directly on AWS SDKs.
- Whether a failing external provider can exhaust the application's available connections.

These choices have consequences beyond their immediate implementation. They influence development speed, reliability, testing, operational complexity, and the kinds of future changes that will be easy or difficult.

Compare those decisions with choosing between two equivalent names for a local variable. Both are design decisions, but their consequences have radically different scope.

Architecture operates at multiple scales. A poorly designed TypeScript module can create substantial architectural coupling, while the choice between two cloud providers may be relatively inconsequential if the application uses a sufficiently portable deployment model.

This is why reducing architecture to infrastructure diagrams or technology selections is misleading.

### Architecture creates a cost structure

Suppose we model the total engineering cost of a system over its lifetime:

\[
C_{\text{lifetime}}
=
C_{\text{initial}}
+
\sum_{i=1}^{n} C_{\text{change},i}
+
C_{\text{operation}}
+
C_{\text{failure}}
\]

This isn't a financial accounting formula, but it captures the important components.

The initial implementation is only one part of the cost. Future feature development, maintenance, incidents, infrastructure operation, and architectural migrations may collectively exceed it.

An architecture optimized exclusively for rapid initial delivery may minimize the first term while increasing the others.

Conversely, an excessively sophisticated architecture may increase initial and operational costs without producing meaningful long-term benefits.

The objective is not to minimize architectural complexity at any price.

**The objective is to choose a structure whose costs and capabilities fit the system's actual requirements and plausible evolution.**

For a temporary internal application used by five employees, architectural elegance may have little economic value. For a subscription platform expected to operate for ten years with a growing engineering organization, maintainability becomes a major business concern.

A senior engineer recognizes this difference.

---

## 3. Requirements: The Architecture Begins Before the Code

Suppose two companies ask you to design a document-processing application.

Both require users to upload PDFs, extract information, and retrieve the processed results. Their functional requirements appear nearly identical.

But consider their circumstances.

**Company A** is a small startup processing 2,000 documents daily. Processing may take several minutes, customers can retry failed uploads, and two developers maintain the application.

**Company B** handles medical documents for hospitals. It processes millions of documents, requires strong access controls and auditing, and must meet demanding reliability, privacy, and recovery requirements.

Would you give them the same architecture?

Probably not, even though their product descriptions sound similar.

The difference comes from requirements that describe not merely *what* the system does, but *how well* it must perform under particular conditions.

### Functional requirements

Functional requirements describe capabilities and externally visible behavior:

- Upload a document.
- Authenticate a user.
- Process an invoice.
- Create a reservation.
- Retrieve historical transactions.

These establish the essential business functionality.

### Quality attributes

Quality attributes describe properties of the system's behavior and structure.

| Attribute | Architectural concern |
|---|---|
| Performance | Latency and throughput under specified workloads |
| Availability | Ability to serve requests over time |
| Reliability | Correct operation and recovery from failures |
| Security | Protection of data, operations, and trust boundaries |
| Scalability | Ability to accommodate changing demand |
| Maintainability | Effort and risk associated with modifications |
| Testability | Ability to verify behavior efficiently |
| Deployability | Ability to release changes safely and frequently |
| Operability | Ability to diagnose and manage production behavior |
| Cost efficiency | Resources and spending required to deliver the service |

These attributes frequently conflict.

For example, maintaining several geographically separated database replicas may improve resilience or read availability, but it also introduces operational cost and replication concerns. Encrypting and auditing sensitive operations improves security while adding implementation effort and potentially measurable overhead.

A useful architecture is therefore a collection of informed compromises.

### Turn vague qualities into scenarios

A requirement stating that an application must be *fast* is nearly useless for architectural decisions.

Fast compared with what? Under which load? At what percentile? From which geographical location?

A stronger requirement might say:

> When 500 users concurrently search the catalog, 95% of requests must complete within 400 milliseconds, measured at the API boundary under the defined test workload.

Now the requirement has measurable consequences. Engineers can test candidate designs, identify bottlenecks, and determine whether caching or infrastructure changes are justified.

Similarly, *the application must be maintainable* might become:

> Adding a new payment provider should normally require changes within the payments module and its composition configuration, without modifying reservation business rules.

This requirement is harder to measure precisely, but it provides a meaningful architectural test.

The AWS Well-Architected Framework formalizes a related way of evaluating systems across operational excellence, security, reliability, performance efficiency, cost optimization, and sustainability. These categories are useful prompts, not a universal prescription for how every application should be structured.

### Constraints matter as much as qualities

Architectural decisions are also shaped by nonnegotiable constraints:

- A four-month delivery deadline.
- Three available engineers.
- An existing PostgreSQL database.
- Mandatory EU data residency.
- A contractual integration with an old SOAP service.
- A fixed infrastructure budget.
- A team experienced with Node.js but unfamiliar with Kubernetes.

A theoretically attractive design may be a terrible practical choice if the organization cannot build or operate it reliably.

Notice the distinction between a requirement and a proposed implementation.

"We must recover service within fifteen minutes after an availability-zone failure" is a requirement. "We must use Kubernetes" is a proposed technical solution that needs independent justification.

Confusing the two allows technological preferences to masquerade as business necessities.

---

## 4. Coupling: The Invisible Network of Consequences

Return to our hotel application.

Why did introducing invoice-based reservations require modifications across so many modules?

Because the modules were coupled in ways that made changes propagate.

**Coupling describes the extent to which one part of a system depends on another.**

Some coupling is unavoidable. A reservation genuinely depends on payment information in certain workflows, and invoices genuinely depend on transaction data.

The question is not whether dependencies exist, but how broadly and deeply they reach.

### Structural coupling

Consider a booking service that directly imports another module's implementation:

```typescript
import { StripePaymentService } from "../payments/stripe";
import { BookingEntity } from "../database/entities";
import { EmailSender } from "../notifications/email";

export class BookingService {
  async createBooking(request: BookingRequest) {
    // Validate, save, charge, email...
  }
}
```

This service knows several implementation details:

- Payments use Stripe.
- Persistence uses a particular entity representation.
- Notifications are delivered through email.
- The booking operation orchestrates all these responsibilities.

If those technologies or workflows change, the booking service may need modification.

Some dependencies are entirely reasonable inside a small application. But when this structure spreads across dozens of modules, the system gradually becomes difficult to modify independently.

### Data coupling

A more subtle problem occurs when unrelated modules share ownership of the same data.

Imagine:

```text
booking-service
    └── writes reservations.status

payment-service
    └── writes reservations.status

notification-worker
    └── reads reservations.status

reporting-service
    └── interprets reservations.status
```

All four components depend on the meaning of a database column.

What does `CONFIRMED` mean?

Does it indicate that inventory has been reserved? That the customer has paid? That the hotel acknowledged the booking? That the customer received confirmation?

If different modules interpret the same value differently, the coupling becomes semantic as well as structural.

Changing one status transition may unexpectedly affect reporting, billing, or notifications.

This is particularly dangerous because TypeScript cannot detect that two modules disagree about the business meaning of a perfectly valid string value.

### Temporal coupling

Dependencies also arise through execution order.

Consider a workflow that assumes:

1. Save the reservation.
2. Charge the customer.
3. Send the confirmation.
4. Commit the result.

If one step cannot complete without the preceding steps having occurred in exactly the expected order, the system has temporal coupling.

Some ordering is inherent in the business process. However, unnecessary ordering constraints reduce flexibility and complicate failure recovery.

For example, requiring an email provider to respond successfully before completing a reservation may turn a temporary notification outage into a booking outage.

The notification is important, but the business may not require it to complete synchronously.

### Behavioral coupling

Two modules can have clean interfaces and still depend heavily on each other's undocumented behavior.

A reservation service might call:

```typescript
await paymentService.charge(customerId, amount);
```

But perhaps the payment service sometimes returns success before the transaction is settled, and the caller assumes settlement has already occurred.

The function signature is simple. The behavioral contract is not.

This distinction explains why replacing a dependency can be difficult even when its interface remains unchanged.

### Measuring the practical impact

Coupling is often discussed qualitatively, but change history provides evidence.

Investigate ten recent features or bug fixes and ask:

- How many modules changed together?
- Which modules repeatedly appear in unrelated modifications?
- How many teams had to coordinate?
- How frequently did changes produce regressions elsewhere?
- Were changes concentrated around one responsibility or scattered unpredictably?

A module that changes every time *anything* changes may be an architectural bottleneck.

However, co-changing files aren't automatically evidence of bad coupling. Updating an API contract alongside its client may be a legitimate coordinated change.

The meaningful question is whether the coordination reflects a genuine business dependency or an avoidable implementation dependency.

---

## 5. Cohesion: What Belongs Together?

Coupling concerns relationships *between* modules.

**Cohesion concerns how closely the responsibilities *within* a module belong together.**

Imagine a module named `CommonUtils` containing:

```typescript
export function formatDate(...) { /* ... */ }
export function calculateCancellationFee(...) { /* ... */ }
export function generateInvoiceNumber(...) { /* ... */ }
export function validateHotelAvailability(...) { /* ... */ }
export function normalizeEmail(...) { /* ... */ }
```

These functions may each be useful, but they do not collectively express a coherent responsibility.

The module exists because its contents are convenient to share, not because they form a meaningful unit.

Now compare a `CancellationPolicy` module containing:

```typescript
export function calculateCancellationFee(...) { /* ... */ }
export function isCancellationAllowed(...) { /* ... */ }
export function determineRefundEligibility(...) { /* ... */ }
```

These functions operate on closely related business concepts and are likely to evolve together.

That is higher cohesion.

### The surprising importance of boundaries

A good module boundary is often found by asking:

**Which pieces of the system tend to change for the same reasons?**

If cancellation rules frequently evolve together, they likely deserve a shared home. If notification templates change independently from payment processing, they probably should not be tightly integrated.

This is more useful than blindly organizing everything according to technical categories.

Consider:

```text
src/
├── controllers/
├── services/
├── repositories/
├── validators/
└── utils/
```

This structure organizes code by its technical role. It can work well, particularly in small applications.

However, a reservation feature may require navigating all five directories, and developers may struggle to identify which components belong to the reservation domain.

An alternative:

```text
src/
├── reservations/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── persistence/
├── payments/
├── notifications/
└── identity/
```

Now the system emphasizes business responsibilities, while each responsibility may retain internal technical layers.

Neither folder structure guarantees good architecture. A feature-organized codebase can still have chaotic dependencies, and a layered codebase can maintain excellent boundaries.

The useful principle is that **module organization should help developers understand ownership, dependencies, and expected change patterns**.

This also raises a question that developers frequently underestimate: who owns the meaning of a concept?

If payment and reservation modules both believe they own the `paymentStatus` field, extracting them into separate directories accomplishes very little.

Ownership must exist in behavior, not merely filenames.

---

## 6. Dependency Direction: Who Is Allowed to Know What?

One of the most powerful architectural ideas is that dependencies should follow deliberate directions.

Suppose the reservation business logic directly imports Stripe, PostgreSQL, and AWS:

```text
ReservationService
    ├── Stripe SDK
    ├── TypeORM
    ├── AWS SDK
    └── Express
```

This may be convenient, but it means that business logic is entangled with external implementation choices.

Why should the rule determining whether a reservation may be confirmed depend on which payment SDK the company uses?

It shouldn't, unless the rule genuinely relies on a provider-specific capability.

### Separating policy from mechanism

Consider a slightly more deliberate design:

```typescript
type Reservation = {
  id: string;
  customerId: string;
  totalCents: number;
};

interface ReservationRepository {
  save(reservation: Reservation): Promise<void>;
}

interface PaymentGateway {
  charge(
    customerId: string,
    amountCents: number
  ): Promise<{ transactionId: string }>;
}
```

The business operation depends on capabilities rather than concrete technologies:

```typescript
class ReservationCheckout {
  constructor(
    private readonly reservations: ReservationRepository,
    private readonly payments: PaymentGateway
  ) {}

  async execute(reservation: Reservation): Promise<void> {
    const payment = await this.payments.charge(
      reservation.customerId,
      reservation.totalCents
    );

    await this.reservations.save(reservation);

    console.log(`Charged ${payment.transactionId}`);
  }
}
```

The real implementations are supplied from outside:

```typescript
const checkout = new ReservationCheckout(
  new PostgresReservationRepository(),
  new StripePaymentGateway()
);
```

We have introduced a meaningful distinction:

```text
           Application policy
          ReservationCheckout
            /            \
           v              v
   ReservationRepository  PaymentGateway
           ^              ^
           |              |
    PostgreSQL Adapter  Stripe Adapter
```

At runtime, the application calls the adapters. But at the source-code level, the application layer owns the interfaces and does not import those adapters.

The concrete infrastructure implementations depend on the contracts required by the application, reversing the source dependency compared with directly importing infrastructure into business logic.

This is the **Dependency Inversion Principle** in practical form.

TypeScript's structural typing makes these interfaces lightweight: no special framework or inheritance hierarchy is required. Since interfaces disappear at runtime, the application still needs a composition mechanism to provide concrete implementations.

### What did we actually gain?

We gained the ability to change or test external mechanisms while preserving much of the application policy.

For example, we could provide a test implementation:

```typescript
class FakePaymentGateway implements PaymentGateway {
  async charge() {
    return { transactionId: "test-123" };
  }
}
```

Or introduce a second production payment provider behind the same capability.

However, there is an important limitation: **an interface cannot magically erase real semantic differences between providers**.

If one provider supports immediate capture while another uses asynchronous settlement, the application may genuinely need different workflow behavior. Pretending that both providers are interchangeable through a simplistic `charge()` method could conceal important business distinctions.

Also, our example is intentionally incomplete: charging before saving introduces partial-failure risks, including a successful charge followed by a failed database write. A production workflow must address durable state, idempotency, and reconciliation using the techniques developed in SE320–SE490.

Architecture doesn't disappear because we introduced three interfaces.

It merely provides a clearer location for dealing with those difficulties.

### The correct level of abstraction

Should every database call, helper function, and external library receive an interface?

No.

An abstraction has a maintenance cost:

- More symbols to understand.
- More navigation between files.
- Additional indirection during debugging.
- More interfaces to evolve.
- Potentially misleading promises of interchangeability.

Create a boundary when it protects an important policy, isolates volatility, enables necessary testing, or clarifies ownership.

Do not automatically create `IHotelService`, `HotelServiceImpl`, `AbstractHotelFactory`, and `DefaultHotelFactoryProvider` just because you once saw a diagram involving arrows.

Java developers have survived enough of that already.

---

## 7. Modularity Is About Containing Change

Let's revisit the corporate booking feature.

The original system scattered payment assumptions across reservation creation, customer communications, financial reports, and cancellation workflows.

A more modular design might establish these responsibilities:

```text
Reservation
    Owns reservation lifecycle and confirmation rules

Payments
    Owns charges, payment attempts, refunds, and settlement state

Billing
    Owns invoices, deadlines, and outstanding balances

Notifications
    Owns delivery of customer communications

Reporting
    Builds financial and operational views from authoritative data
```

The reservation module should understand whether payment obligations allow a booking to proceed. But it need not know how Stripe captures a card charge or how billing generates an invoice PDF.

The billing module should know how much money is owed. It need not independently decide whether a hotel room remains reserved.

These boundaries create opportunities for local reasoning.

Suppose invoice formatting changes. Ideally, engineers modify billing without touching reservation lifecycle logic.

Suppose a hotel introduces a new cancellation policy. The reservation or cancellation domain should own the decision, while payment execution handles the resulting refund instruction.

### Boundaries are not walls

Real workflows cross business boundaries. A reservation may need to interact with inventory, payments, billing, and notifications.

The goal isn't to eliminate cross-module communication; it's to make those interactions explicit and governed by meaningful contracts.

A good contract communicates business intent:

```typescript
paymentService.requestRefund({
  paymentId,
  amountCents,
  reason: "CUSTOMER_CANCELLATION"
});
```

A weaker boundary might expose another module's persistence details:

```typescript
paymentRepository.updatePaymentEntity({
  // Internal fields the reservation module should not own
});
```

The second version allows external modules to manipulate internal state, making the payment boundary largely ceremonial.

A powerful test of modularity is to imagine replacing the internal implementation of a module.

How much of the rest of the codebase would need to know?

If the answer is "nearly everything," the boundary probably isn't protecting much.

### Modular monoliths and microservices

As explored in SE320–SE490, modularity does not require independent deployment.

A modular monolith can enforce meaningful ownership boundaries while sharing one process and deployment pipeline. A microservice architecture distributes components across network boundaries, introducing independent deployment and scaling opportunities alongside latency, consistency, and operational costs.

The useful distinction is between **logical boundaries** and **deployment boundaries**.

You may need the former long before you need the latter.

Indeed, extracting a badly coupled module into another service often produces a badly coupled distributed system. The dependencies haven't disappeared; they've become network calls, synchronized releases, and cross-service incidents.

Good architecture is not measured by how many processes exist.

---

## 8. Quality Attributes Are Architectural Trade-offs

We now understand how structure influences maintainability. But architecture also shapes runtime characteristics.

Consider three goals for an online retail platform:

1. Provide very fast product searches.
2. Keep product availability accurate.
3. Remain functional during temporary database failures.

Each goal suggests different technical mechanisms.

For fast searches, we might introduce caching, optimized indexes, or dedicated search infrastructure.

For accurate availability, we might need authoritative inventory updates, transactional controls, and careful handling of stale data.

For resilience, we might serve limited cached information during outages while temporarily disabling checkout.

These mechanisms interact.

A cache improves response time but may expose stale inventory. A strict consistency requirement can increase latency or reduce availability during failures. Serving cached product descriptions is relatively harmless; accepting purchases based on stale inventory can be much more consequential.

Architecture therefore requires understanding which properties matter at which points in the system.

### Architectural tactics

A *tactic* is a concrete design mechanism intended to improve a quality attribute.

| Quality | Possible tactic | Typical cost or limitation |
|---|---|---|
| Availability | Redundant application instances | More infrastructure and coordination |
| Performance | Caching | Staleness and invalidation complexity |
| Reliability | Durable job queue | Asynchronous behavior and operational overhead |
| Security | Least-privilege permissions | More configuration and maintenance |
| Modifiability | Explicit module interfaces | Indirection and contract management |
| Deployability | Backward-compatible migrations | More release-planning complexity |
| Scalability | Horizontal workers | Downstream bottlenecks remain |

The important lesson is not to memorize this table. It is to recognize that architectural features exist to address particular problems, and every feature has costs.

A useful design discussion should be able to complete the following sentence:

> We are introducing **this mechanism** because **this measurable requirement or identified risk** justifies **these additional costs**.

If the team cannot complete that sentence convincingly, the design may be driven more by fashion than necessity.

### Architecture is often about deciding where *not* to optimize

Suppose customers spend six seconds waiting for an external hotel supplier to return room availability.

Engineers propose rewriting the internal Node.js service in Go because its handlers sometimes consume 20 milliseconds.

Even if the rewrite halves internal processing time, overall latency would improve only marginally.

The architectural bottleneck is the external dependency, not JavaScript execution.

A stronger investigation might examine supplier timeouts, parallel queries, cached results, incremental rendering, or a product design that communicates progress.

The senior engineer's advantage is not knowing more optimization techniques.

It is knowing which constraint actually matters.

---

## 9. Reversibility: Designing for an Uncertain Future

There is one problem no architecture can eliminate: the future is unknown.

A startup may expect ten thousand customers and attract ten million. A payment provider may increase prices, a regulatory requirement may change, or a seemingly stable product line may disappear.

Trying to predict every possibility produces elaborate abstractions for imaginary requirements.

Ignoring foreseeable change produces expensive migrations.

Good architecture must operate between these extremes.

### Not every decision deserves the same commitment

Consider three decisions.

**Decision A: Which structured logging library should we use?**

If logging calls are reasonably centralized and the application relies on standard concepts, changing libraries may be manageable.

**Decision B: Should every module directly access the database tables owned by every other module?**

Undoing this later may require substantial restructuring of business logic and data ownership.

**Decision C: Should customer identifiers be globally unique across tenants or only unique within each tenant?**

This choice may influence schema constraints, API contracts, authorization, caching, imports, and integrations. Changing it after years of production data could be expensive.

These decisions differ in their *reversibility* and blast radius.

A practical assessment might classify choices as:

| Decision characteristic | Typical approach |
|---|---|
| Cheap to change, limited consequences | Decide quickly |
| Expensive but well understood | Analyze deliberately |
| Expensive and highly uncertain | Prototype, measure, or preserve options |
| Easy to postpone without accumulating major risk | Delay commitment |

This isn't permission to avoid decisions indefinitely. Some uncertainty must be accepted so development can proceed.

Instead, it suggests allocating engineering attention according to the consequences of being wrong.

### The value of preserving options

Suppose your SaaS platform currently supports one payment provider, but expansion into several European markets is a credible business objective.

It may be reasonable to define a payment capability boundary today because payment-provider changes could be expensive.

It probably isn't reasonable to implement adapters for seven hypothetical providers, build a universal payment-routing engine, and introduce dynamic failover before the first international customer exists.

The first choice preserves an option.

The second purchases speculative flexibility at a substantial upfront cost.

This distinction is central to evolutionary architecture.

**Prepare for plausible changes without implementing imaginary features.**

Martin Fowler's discussion of YAGNI makes an important distinction here: avoiding speculative functionality does not mean avoiding refactoring or neglecting code quality. The ability to evolve incrementally depends on keeping the existing design malleable.

---

## 10. Abstraction Can Become Its Own Technical Debt

Abstraction is usually presented as something unquestionably desirable. Developers are encouraged to remove duplication, create reusable components, and hide implementation details.

But abstraction is a trade.

It exchanges some immediate simplicity for potential future flexibility.

Imagine an application supporting two hotel suppliers with substantially different APIs.

A developer creates:

```typescript
interface HotelProvider {
  search(): Promise<Hotel[]>;
  reserve(): Promise<Reservation>;
  cancel(): Promise<void>;
}
```

This initially appears elegant.

However, Supplier A requires a short-lived reservation hold before payment. Supplier B confirms reservations immediately but sometimes returns asynchronous status updates. Supplier C, added later, permits partial cancellations.

Soon the supposedly universal interface acquires numerous flags:

```typescript
reserve({
  requiresHold,
  supportsAsyncConfirmation,
  allowPartialCancellation,
  useLegacyPricing,
  confirmationMode,
  ...
});
```

The abstraction no longer expresses a coherent common model. It attempts to conceal meaningful differences, and every new provider makes the interface less understandable.

A better solution might retain a small shared contract for genuinely common capabilities while modeling supplier-specific workflows explicitly.

### Three common abstraction mistakes

**Abstraction before understanding.** Developers introduce generalized frameworks before observing enough real examples to understand what should be generalized.

**Abstraction around the wrong similarity.** Two functions look syntactically similar but serve different business responsibilities, so forcing them together creates conditional complexity.

**Abstraction that leaks.** Consumers must still understand the hidden implementation's constraints, failures, or internal representations, defeating the purpose of the boundary.

The famous temptation is to eliminate duplication at all costs.

Yet two similar pieces of code may be better than one abstraction that forces unrelated concepts to evolve together.

Duplication has a cost; incorrect unification has a different cost. Engineers must compare them.

A useful guideline is to tolerate limited duplication until the underlying commonality becomes clear, especially in business domains where apparently similar workflows may diverge later.

---

## 11. Architecture Is Also an Organizational System

Software doesn't evolve independently of the people maintaining it.

Imagine a platform with three engineering teams:

- Reservations
- Payments
- Customer experience

But the codebase contains one enormous shared service responsible for most business operations.

Every feature requires several teams to modify the same files. Merge conflicts become frequent, reviews cross ownership boundaries, and releases demand extensive coordination.

The architecture undermines the organization.

Now reverse the problem.

Suppose management insists that every small feature team own an independently deployed microservice, complete with its own CI/CD pipeline, database, monitoring, security configuration, and on-call responsibilities.

The organization may acquire more operational systems than it can competently maintain.

Here the organization undermines the architecture.

Conway's Law describes the relationship between system structure and organizational communication. In practice, teams and architectures influence one another: responsibilities shape software boundaries, and software boundaries shape collaboration.

### Architecture determines coordination costs

Imagine a feature requiring five engineers to modify five tightly coupled components.

If every change requires coordinated reviews, synchronized deployments, and shared release windows, the team's effective productivity can decline even when the individual engineers are excellent.

Clear boundaries can allow developers to work more independently.

But independence is not absolute. Shared product behavior, contracts, security, and operational policies still require coordination.

The objective is to align coordination with genuine business dependencies instead of accidental code dependencies.

### Architecture decisions need institutional memory

Suppose you discover a strange limitation:

> The billing worker must not access the reservations database directly.

Without context, this may appear unnecessarily restrictive.

Perhaps the team previously suffered incidents because billing processes updated reservation states without enforcing reservation invariants. The restriction may protect an important business boundary.

This is where Architecture Decision Records, or ADRs, become valuable.

An ADR is a short document recording:

- **Context:** What problem or constraints motivated the decision?
- **Decision:** What did we choose?
- **Consequences:** What improves, what becomes harder, and what risks remain?
- **Status:** Is the decision proposed, accepted, or superseded?

An ADR should explain *why*, not merely repeat the implementation.

For example:

> **ADR-014: Billing will not modify reservation state directly.**
>
> **Context:** Direct database updates have caused inconsistent reservation and payment lifecycles.
>
> **Decision:** Billing will request reservation changes through a defined application interface.
>
> **Consequences:** Reservation invariants remain centrally enforced, but some operations require additional orchestration and explicit failure handling.

This modest document may save future engineers days of rediscovering the original reasoning.

Architecture diagrams similarly serve communication. The C4 model, for example, describes systems at several useful zoom levels: context, containers, components, and code.

Not every project needs every diagram. A useful architecture document should help someone understand or change the system, not merely demonstrate that the team owns diagramming software.

---

## 12. Architecture as a Continuous Engineering Activity

There's a persistent misconception that architecture happens at the beginning of a project.

An architect draws diagrams, developers implement them, and eventually the application goes into production.

In reality, important architectural decisions continue throughout the software's lifetime.

The first release reveals which assumptions were incorrect. Production traffic exposes bottlenecks. Business requirements introduce previously unknown constraints. Engineering teams discover which boundaries actually support independent development.

A good architecture must adapt to these discoveries.

### Architectural erosion

Imagine a well-organized payments module with clearly defined interfaces.

A developer needs to fix a production issue quickly and directly imports a payment repository into the reporting module. The change works, tests pass, and nobody objects.

Months later, several other modules begin using the same shortcut.

Eventually, payment persistence details become shared dependencies, and the original boundary has little practical value.

This gradual degradation is called architectural erosion.

It rarely begins with a grand decision to destroy the architecture. It arises from individually convenient choices accumulating into system-wide complexity.

### Protecting important boundaries

Some architectural rules can be made executable.

For example, a TypeScript project might establish that:

```text
reservations/domain
    must not import:
        payments/infrastructure
        database/typeorm
        aws-sdk
```

Static analysis, ESLint rules, dependency graph tools, or dedicated architecture tests can enforce such restrictions.

This turns part of architecture from documentation into a continuously checked property.

A team may similarly test that database schemas remain backward compatible during rolling deployments, or that particular API endpoints meet performance budgets.

These checks are sometimes called *architecture fitness functions*: mechanisms for verifying that important structural or behavioral characteristics remain within acceptable bounds as the system evolves.

Not every architectural property can be automated, but important boundaries should not depend entirely on developers remembering a design document from three years ago.

### Architecture reviews should focus on risks

A senior engineer reviewing an unfamiliar application should avoid beginning with a list of preferred technologies.

A more effective investigation asks:

1. Which business operations are most important?
2. Which failures would cause serious damage?
3. Which parts of the system change most frequently?
4. Where are responsibilities ambiguous?
5. Which dependencies create operational or development bottlenecks?
6. Which architectural decisions are becoming expensive?
7. What evidence supports the proposed improvements?

This turns architecture review into structured engineering analysis rather than aesthetic criticism.

A codebase does not need to look fashionable.

It needs to serve its users, satisfy its constraints, and remain economically viable to maintain.

---

## 13. Practical Lab — Investigating Architectural Coupling

Let's perform a manageable architecture investigation using a hypothetical TypeScript backend.

Consider this project:

```text
src/
├── api/
│   └── bookingController.ts
├── booking/
│   ├── bookingService.ts
│   └── cancellationService.ts
├── payment/
│   ├── stripeService.ts
│   └── refundService.ts
├── notification/
│   └── emailService.ts
├── database/
│   ├── bookingRepository.ts
│   └── paymentRepository.ts
└── shared/
    ├── bookingUtils.ts
    └── statusHelpers.ts
```

Suppose inspection reveals:

```text
bookingService
    → stripeService
    → bookingRepository
    → emailService
    → bookingUtils

cancellationService
    → refundService
    → paymentRepository
    → bookingUtils

refundService
    → bookingRepository
    → statusHelpers

emailService
    → bookingRepository
    → statusHelpers
```

### Investigation A: Draw the dependency graph

Identify which modules depend directly on persistence implementations, which modules contain business rules, and which supposedly independent features depend on shared utilities.

Pay particular attention to `bookingRepository`.

Why are payment and notification modules accessing booking persistence directly? Are they retrieving legitimate read-only information, or do they depend on internal reservation representations?

The import graph alone cannot answer this. You need to investigate actual behavior and ownership.

### Investigation B: Simulate a feature change

Product management introduces a new rule:

> Customers with approved corporate billing accounts may confirm reservations before completing payment.

Trace the likely impact through the modules.

Which dependencies reflect unavoidable business coordination? Which exist because payment state and reservation state were incorrectly merged?

Can the payment module express an outstanding financial obligation without requiring the reservation module to pretend the transaction has already completed?

### Investigation C: Propose a smaller improvement

Do not rewrite the application into microservices.

Instead, attempt three targeted improvements:

1. Make reservation state transitions owned by the reservation module.
2. Move provider-specific payment behavior behind an appropriate payment capability.
3. Prevent notification code from modifying or interpreting internal reservation state directly.

Draw the revised dependency graph.

Then explain what remains coupled and why that coupling is legitimate.

### Optional real-codebase experiment

In a TypeScript repository you own, inspect import dependencies using an appropriate dependency-analysis tool such as [dependency-cruiser](https://github.com/sverweij/dependency-cruiser).

Look for circular dependencies, heavily imported modules, and imports that cross intended feature boundaries.

Don't assume a circular dependency automatically means the architecture is broken. Investigate whether the cycle represents a meaningful design problem, a harmless type-level dependency, or an artifact of module organization.

For additional evidence, inspect Git history to discover which files frequently change together. Combining dependency structure with change history provides a stronger picture than either analysis alone.

---

## 14. Engineering and Interview Challenges

Try reasoning through these before reading the discussion.

**Challenge 1 — The framework abstraction**

Your team operates a TypeScript SaaS with one database, one payment provider, and six backend developers. A senior engineer proposes building a universal plugin framework for payments, databases, and messaging because the company might eventually migrate to other technologies.

Is this good architectural foresight or overengineering? Which parts might be justified?

**Challenge 2 — The shared database**

Two teams maintain reservation and billing modules within one application. Both directly update the same `reservations` table, but automated tests pass and production incidents are rare.

Would you change this architecture? What information would determine the priority?

**Challenge 3 — The microservice proposal**

A backend application handles 50,000 requests daily and is occasionally slow during report generation. Management proposes breaking it into six microservices to improve performance and scalability.

What would you investigate before approving the proposal?

**Challenge 4 — The expensive boundary**

A critical business operation requires coordination between inventory and payments. Developers propose making the modules entirely independent, with no direct calls or shared transactions, because low coupling is considered desirable.

Can this objective be pursued too far? What business guarantees must influence the decision?

**Challenge 5 — Architecture under uncertainty**

Your company must release a customer-facing product in three months. Requirements are unstable, the engineering team is small, and management expects significant growth if the product succeeds.

Which architectural decisions deserve early attention, and which should probably be postponed?

---

## 15. Solutions and Discussion

### Challenge 1 — Abstractions must earn their existence

The universal plugin framework is almost certainly premature.

One payment provider and one database do not establish enough evidence about the variations that future integrations will require. A framework designed around imagined differences may introduce complexity while preserving little useful flexibility.

However, separating essential business logic from payment-provider SDK calls is sensible. Payments are an external integration boundary with meaningful business risk, and isolating that dependency may be inexpensive.

The key distinction is between establishing a useful boundary and building a generalized platform before its requirements exist.

I would implement the smallest credible payment abstraction, keep database access appropriately encapsulated, and postpone speculative plugin infrastructure.

### Challenge 2 — Clarify ownership before changing deployment

Shared database access is not necessarily an immediate crisis, especially inside a small monolith.

The important concern is whether both modules independently enforce or modify the same business invariants.

If billing can directly change reservation status, the system risks inconsistent transitions and ambiguous responsibility. I'd investigate write paths, transaction boundaries, incident history, and upcoming requirements before choosing a migration strategy.

If the design creates real risks or repeated coordination costs, I would centralize ownership incrementally. A new microservice or separate database is not automatically required.

### Challenge 3 — Microservices do not fix unknown bottlenecks

First measure report-generation behavior.

Is the application CPU-bound? Does reporting execute expensive database queries? Are large result sets blocking the Node.js event loop? Is the database saturated? Does the report consume excessive memory?

The appropriate solution could be query optimization, asynchronous report generation, a dedicated worker process, better indexing, or separate read capacity.

At 50,000 daily requests, the average rate is less than one request per second, though bursts and individual request costs may still be substantial.

The traffic figure alone provides almost no justification for six microservices.

Independent services may be appropriate if reporting genuinely requires separate operational scaling or ownership, but the problem must be demonstrated first.

### Challenge 4 — Business integrity outranks architectural purity

Low coupling is a means, not a business objective.

Inventory and payment operations may require coordinated failure handling to avoid selling unavailable inventory or charging customers for reservations that cannot be fulfilled.

Making components independent does not eliminate these requirements. It moves coordination into explicit workflows involving state transitions, retries, compensation, and reconciliation.

A direct application call may be perfectly reasonable within a modular monolith. In a distributed architecture, a durable workflow may be necessary.

The correct design should satisfy the business guarantees with the least unnecessary complexity.

### Challenge 5 — Protect expensive decisions and defer speculative complexity

I would prioritize several foundational concerns:

- Clear ownership of core business rules and sensitive data.
- An understandable modular structure with manageable dependencies.
- A database model capable of enforcing important invariants.
- Authentication, authorization, and essential security boundaries.
- Basic automated tests, reproducible deployment, and operational visibility.
- Isolation of external integrations where failures or provider changes are credible risks.

I would probably postpone Kubernetes, multi-region deployments, complex event-driven orchestration, generalized frameworks, and microservice extraction unless specific requirements justify them.

The objective is neither to build a disposable prototype nor to engineer an imaginary future corporation.

It is to deliver a maintainable product whose most expensive decisions have been considered carefully, while preserving the ability to learn from actual usage.

---

## Mental Model

When evaluating an architecture, ask:

1. **Purpose:** Which functional requirements and quality attributes matter most?
2. **Constraints:** What limitations shape the available options?
3. **Boundaries:** Who owns each responsibility, rule, and piece of data?
4. **Dependencies:** Which changes and failures propagate across those boundaries?
5. **Trade-offs:** What complexity does each architectural mechanism introduce?
6. **Evolution:** Which decisions are expensive to reverse, and what evidence would justify changing them?

**The central principle: Good architecture makes important changes and failures easier to contain, without imposing more complexity than the problem requires.**


---

## Next Lecture — SE330-L02: Architecture Patterns and Their Consequences

Continue in **SE330 — Software Architecture and Evolution**.

## Further Reading

1. **Martin Fowler — [Software Architecture Guide](https://martinfowler.com/architecture/)**. A thoughtful exploration of architecture as important design decisions, shared understanding, and the capacity of software to evolve.

2. **Martin Fowler — [YAGNI](https://martinfowler.com/bliki/Yagni.html)**. Why speculative flexibility is often expensive, and why avoiding unnecessary features must not become an excuse for poor design.

3. **Simon Brown — [The C4 Model](https://c4model.com/)**. A practical way to communicate architecture at different levels of detail without drowning people in diagrams.

4. **Michael Nygard — [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)**. The foundational explanation of lightweight Architecture Decision Records.

5. **AWS — [Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/)**. A structured reference for evaluating cloud workloads across operational, security, reliability, performance, cost, and sustainability concerns.

6. **Mark Richards and Neal Ford — *Fundamentals of Software Architecture***. A substantial book on architectural characteristics, styles, components, and engineering trade-offs.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE330-L01  SOFTWARE ARCHITECTURE — INTERVIEW GLANCE CARD

CORE MODEL
  Functionally correct ≠ structurally healthy
  Architecture = important structural decisions shaping capability,
  behavior, and cost of change — not just box diagrams
  Lifetime cost ≈ initial + Σ changes + operate + failure
  Fit structure to requirements & plausible evolution

REQUIREMENTS BEFORE CODE
  Functional: what the system does
  Quality attributes: performance, availability, reliability, security,
  scalability, maintainability, testability, deployability, operability, cost
  Attributes conflict → informed compromises
  Vague “fast/maintainable” → measurable scenarios
  Constraints (deadline, team, residency, budget, skills) bind options
  Requirement ≠ preferred implementation (“must use K8s”)

COUPLING
  Extent one part depends on another; some unavoidable
  Structural: direct imports of Stripe/entities/email
  Data: shared ownership of same column meaning (CONFIRMED?)
  Temporal: forced execution order (email before booking commit)
  Behavioral: clean interface, undocumented semantics
  Evidence: co-change history — genuine vs accidental dependency

COHESION
  Do responsibilities inside a module belong together?
  CommonUtils grab-bag vs CancellationPolicy cluster
  Organize by change reasons / ownership, not only tech layers
  Ownership in behavior, not filenames

DEPENDENCY DIRECTION
  Policy shouldn't import Stripe/TypeORM/AWS/Express by default
  Depend on ports (ReservationRepository, PaymentGateway);
  adapters implement → Dependency Inversion
  Interface ≠ erase real provider semantic differences
  Abstraction cost: files, indirection, false interchangeability
  Boundary when it protects policy / volatility / tests / ownership

MODULARITY
  Contain change: reservations / payments / billing / notifications
  Boundaries ≠ walls; contracts express business intent
  Don't expose other modules' persistence internals
  Logical boundaries vs deployment boundaries
  Modular monolith before premature microservices
  Extracting coupled module → distributed coupled system

QUALITY TACTICS
  Mechanism for a measurable requirement, with costs
  (cache→staleness; queue→async ops; replicas→coord cost…)
  Optimize where the bottleneck is (supplier 6s ≠ rewrite Go for 20ms)

REVERSIBILITY
  Cheap/limited → decide fast; expensive+uncertain → prototype/options
  Preserve options ≠ implement imaginary providers
  YAGNI: skip speculative features; keep design malleable

ABSTRACTION DEBT
  Premature / wrong similarity / leaky interfaces
  Limited duplication may beat forced unification

ORGANIZATION
  Conway: teams ↔ structure; architecture sets coordination cost
  ADRs: context / decision / consequences / status
  C4 for communication zoom levels

CONTINUOUS ARCHITECTURE
  Erosion: convenient shortcuts accumulate
  Fitness functions: enforceable import rules / budgets
  Review risks: ops, failures, change hotspots, ambiguous ownership

SENIOR LINE: Good architecture contains important changes and failures
             without more complexity than the problem requires.
```

---


