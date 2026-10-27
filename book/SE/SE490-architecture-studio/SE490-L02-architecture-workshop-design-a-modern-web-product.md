---
id: SE490-L02
course: SE490
title: "Architecture Workshop: Design a Modern Web Product"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S12]
prev: SE490-L01
next: SE490-L03
---




# SE490 — Architecture and Systems Design Studio

## Lecture 02: Architecture Workshop: Design a Modern Web Product

*Eleven sessions of engineering knowledge. One real product. Limited money, limited time, and absolutely no permission to build an architectural monstrosity.*

---

# 1. Friday, 14:07 — Three Customers, One Hotel Room, and a Very Unhappy Engineering Team

It's Friday afternoon. Your hotel-booking platform is experiencing the busiest hour in its short history.

A major travel influencer has mentioned your website. Traffic is suddenly five times higher than usual.

At 14:07, three things happen almost simultaneously.

**Customer A**, browsing from Berlin, finds the last available room at a popular hotel. She clicks Reserve.

**Customer B**, browsing from Stockholm, sees the same room and clicks Reserve a fraction of a second later.

**Customer C**, browsing from London, has already reserved a different room and is completing payment.

Customer A receives a confirmation. Customer B also receives a confirmation.

Customer C's payment succeeds, but the API request times out. Her browser displays a failure message and offers to try again. She clicks Retry.

Meanwhile, your monitoring dashboard begins showing elevated API latency. Someone suggests increasing the number of application servers.

Another developer suggests clearing Redis. A third wonders whether the CDN is returning stale availability.

And your product manager asks the most terrifying question in software engineering:

> "Can we just fix it quickly?"

Let's examine the situation. The website itself is fast.

The CDN is healthy. The Vue application is rendering smoothly.

Most requests complete in less than 100 milliseconds. And yet the product is failing at its most important responsibility: selling hotel rooms correctly.

Now imagine that, six months earlier, somebody had asked you to design this system. Would your architecture have anticipated these failures?

Would you have known which guarantees belonged to the browser, API, database, and payment provider? Would you have designed the application differently?

That's what we're going to investigate. This studio workshop brings together networking, browser, frontend, API, and delivery ideas from earlier courses into one design exercise.

But we're not going to produce a gigantic architectural diagram merely to make the system look sophisticated. We're going to make engineering decisions.

And every decision must justify its cost.

---

# 2. The Assignment: You're the Technical Lead

Imagine you're entering a senior engineering interview. The interviewer says:

> "Design a modern hotel-booking SaaS. Customers should be able to search hotels, view availability, reserve rooms, pay, and manage bookings. Hotels should be able to manage their inventory. Explain your architecture."

This is deliberately vague. A mediocre candidate immediately begins drawing microservices.

A stronger candidate asks what kind of product we're building. Because architecture depends on constraints.

Let's establish ours.

## 2.1 Product requirements

The initial product needs:

- Public hotel search and hotel details.
- Date-based room availability and pricing.
- Customer registration and authentication.
- Reservation creation and cancellation.
- Online payment through an external provider.
- An authenticated dashboard for hotel operators.
- Basic administrative tools.

The first release will serve hotels managing inventory directly in our system.

Integrations with external reservation networks and global distribution systems are postponed. That scope decision matters enormously.

Direct inventory is difficult enough. Integrating dozens of independent supplier systems introduces additional availability, consistency, and reconciliation challenges.

We won't pretend those complexities can be solved merely by adding another API adapter.

## 2.2 Operational constraints

Assume:

| Constraint | Starting assumption |
|---|---|
| Engineering team | 5 developers |
| Time to first release | 6 months |
| Initial hotels | Approximately 500 |
| Expected usage | Thousands of daily visitors |
| Potential growth | 10× within a year |
| Frontend experience | Vue 3, TypeScript, Vite |
| Backend experience | Node.js, PostgreSQL, AWS |
| Primary market | Europe |
| Availability target | Strong reliability, without enterprise-scale spending |

These figures are illustrative design assumptions, not predictions. We're not trying to build Booking.com on day one.

We're building a product that might become substantial if it succeeds. That distinction should influence almost every architectural decision.

## 2.3 What absolutely must be correct?

This is where we identify our most important invariants. An **invariant** is a property that the system must preserve through every valid operation.

For our product:

1. Two confirmed reservations must not consume the same unit of inventory.
2. A customer must not be able to access another customer's private reservation.
3. A hotel operator must not modify another hotel's inventory without authorization.
4. A network retry must not create duplicate bookings or unintended payments.
5. The frontend must not announce a confirmed booking without authoritative confirmation.
6. Public search results may be slightly stale, but actual booking decisions must use authoritative state.

Notice that these are not performance objectives. They're correctness requirements.

A system can operate slowly and still preserve them. A system that violates them is broken regardless of its benchmark scores.

**Architecture begins by distinguishing what must never happen from what we'd merely prefer to happen quickly.**

---

# 3. First Decision: Don't Build Microservices

The interviewer asks:

"How would you organize the backend?" You have five developers and six months.

One option is:

```text id="x0f5ya"
User Service
Hotel Service
Inventory Service
Pricing Service
Booking Service
Payment Service
Notification Service
API Gateway
Message Broker
Service Discovery
```

Each service has its own deployment pipeline. Perhaps its own database.

You could use Kubernetes to orchestrate everything. It would make an impressive diagram.

You would also spend a remarkable amount of your six-month deadline building infrastructure and debugging service communication.

For our initial scale and team size, this is difficult to justify. My choice would be a **modular monolith**.

Not because microservices are inherently bad. Because the benefits of independent service deployment don't yet outweigh the operational and consistency costs.

## 3.1 The modular monolith

Conceptually:

```text id="j1p3uk"
              Node.js Application
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
   Identity        Hotels        Reservations
       │              │              │
       └──────────────┼──────────────┘
                      │
               Payments Module
                      │
                      ▼
                  PostgreSQL
```

The application runs as one deployable backend service. Internally, its business capabilities have recognizable boundaries.

For example:

```text id="sy8es5"
src/
├── modules/
│   ├── identity/
│   ├── hotels/
│   ├── inventory/
│   ├── reservations/
│   ├── payments/
│   └── notifications/
│
├── infrastructure/
│   ├── database/
│   ├── payment-provider/
│   └── email/
│
└── app.ts
```

We can still enforce good separation. The reservation module shouldn't directly manipulate arbitrary payment database tables.

The payment module shouldn't independently implement hotel inventory rules. But they can communicate through ordinary in-process interfaces.

This avoids introducing network calls between components that don't yet need independent deployment.

## 3.2 Why this matters for correctness

Imagine the reservation operation needs to:

1. Check inventory.
2. Reserve a unit.
3. Create a booking record.

If all relevant authoritative data lives in the same PostgreSQL database, these changes can participate in one database transaction.

Now imagine inventory and reservations are owned by separate independently deployed services with separate databases.

Coordinating that operation becomes a distributed workflow.

We need to consider partial failures, message delivery, compensation, and consistency between independently committed states. Those problems are solvable.

But why introduce them before the product requires such separation? A modular monolith keeps many critical business operations simpler.

The important qualification is that *modular* must mean something.

A giant collection of controllers importing one another's repositories freely isn't good architecture merely because it deploys as one service.

**We're choosing one deployment unit, not abandoning architectural boundaries.**

---

# 4. The Big Picture: Our Initial Architecture

Let's assemble the complete web system.

```text id="lzmyx5"
                   CUSTOMER BROWSER
                    Vue 3 + Router
                            │
                            │ HTTPS
                            ▼
                    CLOUDFRONT / EDGE
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
           STATIC ASSETS            /api requests
             S3 Origin                  │
                │                       ▼
                │                API Entry Point
                │                       │
                │                       ▼
                │                 Node.js Backend
                │                       │
                │            ┌──────────┼──────────┐
                │            │          │          │
                │            ▼          ▼          ▼
                │        PostgreSQL   Session     Background
                │                     Storage      Worker
                │                                   │
                │                                   ▼
                │                              Email Provider
                │
                └────────────────────────────────────────
                       
                       External Payment Provider
                                  ▲
                                  │
                          Backend Integration
```

The payment provider is connected to our backend, not directly trusted as a result of arbitrary browser input.

A real deployment would have additional network and security details. This diagram concentrates on application responsibilities rather than every AWS component.

Let's walk through the choices.

## 4.1 Frontend

Vue 3 with TypeScript and Vite. We already have experience with the stack.

Changing to React or introducing an entirely new framework would consume time without a demonstrated benefit.

For the authenticated application, I'd initially choose client-side rendering.

It's a stateful product where users navigate through searches, forms, reservations, and administrative interfaces. CSR is a reasonable fit.

Public marketing pages can be statically generated.

If search-engine visibility and initial rendering performance become important for public hotel details, we can later consider SSR or pre-rendering for those routes.

That doesn't require committing the entire product to server-side rendering from day one.

## 4.2 Delivery infrastructure

The Vite build generates static assets. S3 stores them.

CloudFront serves them through HTTPS. A suitable routing configuration forwards `/api` requests to the backend origin.

This can allow the browser to use one public origin:

```text id="d9p6cj"
https://stays.example.com
https://stays.example.com/api/...
```

rather than requiring every frontend request to cross between separate browser origins. This simplifies some cookie and CORS concerns.

But sharing an origin doesn't eliminate authentication, authorization, CSRF, or caching requirements.

CloudFront must not accidentally cache personalized API responses.

## 4.3 Backend

A Node.js modular monolith. It can run using a suitable managed AWS compute platform.

Whether we choose containers, a managed application service, or a serverless arrangement depends on team familiarity, workload behavior, and operational needs.

I wouldn't choose Kubernetes merely because the application might eventually grow.

## 4.4 Database

PostgreSQL. It handles the primary transactional business data:

- Customers.
- Hotel organizations.
- Rooms and inventory.
- Quotes.
- Reservations.
- Payment records.

Relational constraints and transactions are particularly valuable for reservations.

## 4.5 Redis and background work

Redis may serve session storage, certain caches, or a queue backend. But I would resist making Redis a second unofficial source of truth for inventory.

If PostgreSQL is authoritative, a Redis cache must not be able to decide that a room can be sold when the database says otherwise.

Background workers handle operations such as email delivery and certain asynchronous maintenance tasks.

They are useful because confirming a booking should not require waiting synchronously for an email provider to accept a message.

For durable business events, though, we must ensure work isn't lost between committing the booking and publishing its notification. We'll return to that shortly.

---

# 5. The User's Journey Through the System

Now let's trace a customer opening the application. They navigate to:

```text id="d9vayx"
https://stays.example.com/search?city=Berlin
```

What happens? The browser may resolve the hostname, establish or reuse a secure connection, and request the document.

CloudFront serves the HTML from an appropriate origin or cache. The HTML references versioned JavaScript and CSS assets.

The browser loads the required resources and initializes Vue. Vue Router interprets the path and query parameters.

The search feature requests hotel data. The frontend renders the results.

In reality, several operations may overlap or be skipped because of caching. But the system is conceptually:

```text id="8tmrwr"
URL
 │
 ▼
Browser + CDN
 │
 ▼
Vue Application
 │
 ▼
Hotel Search API
 │
 ▼
PostgreSQL / suitable cache
 │
 ▼
JSON Response
 │
 ▼
Reactive State
 │
 ▼
Rendered Hotel Results
```

Here's the important architectural question:

**Which parts of this journey should be allowed to become stale?**

The JavaScript bundle can be cached for a long time if its URL is content-versioned. Hotel photographs can be cached aggressively.

A user's selected filters can remain in the URL. Search results might tolerate short-lived caching.

But the final decision to reserve a room must not depend on whatever happened to be in the browser cache. This gives us two distinct paths.

A **discovery path**, optimized for responsiveness and efficient reads. A **commit path**, optimized for correctness.

They may use similar APIs and the same backend, but they have different consistency requirements. That's a fundamental architectural distinction.

---

# 6. Frontend Architecture: Who Owns the Information?

We now need to organize the Vue application. Suppose the customer searches for Berlin, selects dates, opens a hotel, and begins checkout.

Several kinds of state are involved. Let's assign ownership deliberately.

| Information | Primary location |
|---|---|
| Search city, dates, guest count | URL/router |
| Open filter panel | Local component state |
| Search results | Server-state query cache |
| Selected currency | Shared preferences store |
| Hotel pricing rules | Backend authority; frontend display model |
| Reservation attempt status | Reservation workflow |
| Authenticated session | Backend, represented through protected browser credentials |
| Confirmed reservation | Backend authoritative data |

Notice that we're not putting everything into Pinia. Nor are we creating a separate global store for every component.

Different information has different lifetimes and owners.

## 6.1 The search feature

A reasonable structure:

```text id="s4m0zo"
features/
└── hotel-search/
    ├── components/
    │   ├── SearchFilters.vue
    │   ├── HotelCard.vue
    │   └── SearchResults.vue
    ├── composables/
    │   └── useHotelSearch.ts
    ├── api/
    │   └── hotelSearchApi.ts
    └── model/
        └── searchTypes.ts
```

The search feature owns its interface and application behavior. It doesn't need to import the payment store.

The payment feature doesn't need to understand how search filtering works. Checkout can receive a selected hotel and quote through an intentional interface.

## 6.2 Handling an asynchronous search

Suppose the user changes their destination from Berlin to Hamburg. The Berlin request might finish later.

We already know this race from SE240-L03. The search architecture must ensure an obsolete response doesn't overwrite the current results.

A query library can associate data with a key such as:

```typescript id="ndqe13"
[
  "hotel-search",
  city,
  checkIn,
  checkOut,
  guests
]
```

Each distinct search has a distinct cache identity.

The frontend should also prevent a booking from being initiated using stale form inputs or a quote associated with a different date range.

The design principle isn't merely "use TanStack Query." It's:

**The identity of a result must include the inputs that determine its meaning.**

## 6.3 The checkout state machine

We should avoid representing checkout with six independent booleans. Instead, model meaningful workflow states.

```typescript id="7xnnzg"
type CheckoutState =
  | { status: "editing" }
  | { status: "creating-hold"; attemptId: string }
  | { status: "awaiting-payment"; reservationId: string }
  | { status: "processing"; reservationId: string }
  | { status: "confirmed"; reservationId: string }
  | { status: "rejected"; reason: string }
  | { status: "unknown"; attemptId: string };
```

Why an `unknown` state? Because a network timeout cannot prove that a consequential backend operation failed.

If the server created a reservation but the response disappeared, the frontend needs a way to reconcile the outcome.

A state machine makes that uncertainty explicit. A collection of booleans tends to conceal it.

---

# 7. API Design: What Does the Frontend Actually Need?

Let's create a small, deliberate HTTP contract.

| Purpose | Method | Endpoint |
|---|---|---|
| Search hotels | GET | `/api/hotels` |
| Retrieve hotel | GET | `/api/hotels/{id}` |
| Obtain a price quote | POST | `/api/quotes` |
| Create inventory hold | POST | `/api/reservation-holds` |
| Retrieve reservation status | GET | `/api/reservations/{id}` |
| Cancel reservation | POST | `/api/reservations/{id}/cancel` |

These are examples, not a universal booking API standard. I would use conventional HTTP/JSON here.

GraphQL could be justified later if diverse clients need sophisticated projections of hotel data.

But at our current scale, it isn't solving a demonstrated problem.

## 7.1 Why separate quotes from reservations?

Imagine a customer sees:

```text id="o7fefd"
€149 per night
```

That's a search result. Not necessarily a binding offer.

A quote is more specific. It might include:

```json id="yr4tbp"
{
  "quoteId": "quote-481",
  "roomId": "73",
  "checkIn": "2026-11-10",
  "checkOut": "2026-11-13",
  "guests": 2,
  "total": {
    "amountMinor": 44700,
    "currency": "EUR"
  },
  "expiresAt": "2026-11-10T14:15:00Z"
}
```

The example deliberately simplifies taxes and fees. The important thing is that the quote has an identity, explicit inputs, an amount, and an expiration.

The backend owns the authoritative interpretation. The frontend doesn't submit:

```json id="r5za7r"
{
  "price": 1
}
```

and expect the server to accept it because the value is a positive number. The backend verifies the quote and applies the actual business rules.

But here's an important point:

**A valid price quote doesn't necessarily guarantee that inventory is reserved.**

Price validity and inventory ownership are different guarantees. We should define them separately.

---

# 8. The Most Important Operation: Reserving the Last Room

Now we reach the heart of the architecture. Customer A and Customer B both want the last available room.

Both browsers previously received:

```json id="rmkdjd"
{
  "availableRooms": 1
}
```

Both click Reserve. How do we prevent duplicate allocation?

The first thing to recognize is that frontend validation is irrelevant to enforcing this invariant. Disabling the button after clicking is good UX.

It reduces accidental duplicate requests. But two customers are using different browsers.

Neither frontend controls the other's state. The backend must enforce correctness.

## 8.1 The naive implementation

Imagine:

```typescript id="ifhvhz"
const inventory = await getInventory(roomId);

if (inventory.availableRooms > 0) {
  await createReservation(customerId, roomId);
  await decreaseInventory(roomId);
}
```

Looks reasonable. But consider concurrent execution.

```text id="4m42wk"
Customer A                    Customer B
    │                             │
    ▼                             ▼
Reads available = 1         Reads available = 1
    │                             │
    ▼                             ▼
Creates reservation         Creates reservation
    │                             │
    ▼                             ▼
Decreases inventory         Decreases inventory
```

Both operations passed the availability check. This is a classic check-then-act race.

The database must coordinate competing modifications.

## 8.2 A transactionally safe approach

Assume inventory is modeled as a count of interchangeable room units for a given room category and stay date.

For a simplified single inventory record, a conditional SQL update might look like:

```sql id="tpss5z"
UPDATE room_inventory
SET available = available - 1
WHERE id = $1
  AND available > 0
RETURNING available;
```

When executed correctly within the database's concurrency model, the update can atomically claim one available unit.

If no row is returned, there was no unit available to claim.

The reservation record and associated inventory change must then be committed together in a suitable transaction.

For a multi-night hotel stay, the inventory model becomes more complicated because availability may need to be reserved consistently across every requested date.

The backend must avoid partially reserving some nights and not others.

That can require locking or conditionally updating multiple inventory records within one transaction, with a consistent strategy for concurrent requests.

And the operation must be associated with an idempotency key so network retries don't create additional independent reservations. Conceptually:

```text id="mwdcvn"
POST /api/reservation-holds
          │
          ▼
Validate identity + quote + request
          │
          ▼
Begin database transaction
          │
          ├── Establish idempotency identity
          │
          ├── Claim required inventory
          │
          ├── Create provisional reservation
          │
          └── Commit atomically
          │
          ▼
Return authoritative result
```

The actual implementation needs to protect the idempotency record against concurrent duplicate requests, using appropriate uniqueness constraints and transaction behavior.

An in-memory JavaScript variable is not sufficient. Neither is a frontend loading indicator.

## 8.3 Why Redis isn't the ultimate authority

Someone suggests:

"Let's just create a Redis lock around room booking." Redis may help with coordination in some designs.

But if PostgreSQL owns the authoritative inventory and reservations, correctness should ultimately be enforced through durable database constraints and transactional operations.

A separate lock can fail, expire, or become unavailable.

The architecture should not permit overselling merely because a cache or distributed coordination mechanism behaves unexpectedly.

Redis can improve performance and support particular workflows. It should not accidentally replace the system's actual consistency guarantees.

---

# 9. Payment: The Moment Everything Becomes Distributed

We've safely claimed the room.

Problem solved?

Not yet. Now we need payment.

And payment involves an external system. Suppose we create a temporary inventory hold for ten minutes.

The customer begins payment through a trusted payment provider. A possible workflow:

```text id="qbvkap"
Room available
      │
      ▼
Inventory hold created
      │
      ▼
Payment initiated
      │
      ▼
Customer completes payment
      │
      ▼
Provider reports outcome
      │
      ▼
Backend finalizes booking
      │
      ▼
Reservation confirmed
```

Simple enough in the happy case. But external systems create partial failures.

## 9.1 The payment succeeded, but our API timed out

The customer completes payment. The payment provider processes it successfully.

Our backend receives a timeout while waiting for confirmation. What should the frontend display?

Certainly not:

```text id="ngpvae"
Payment failed. Please pay again.
```

We don't know that payment failed. It may have succeeded.

A safer state is:

```text id="5jfqb9"
Payment status being verified.
```

The frontend can query the backend using the known reservation or operation identifier. The backend reconciles the status with the payment provider.

## 9.2 Webhooks and authoritative status

Payment providers often send server-to-server events reporting changes. A webhook might indicate that a payment completed.

But the application must validate the webhook's authenticity using the provider's documented mechanism, typically involving a signature or equivalent trusted verification.

It must also handle duplicate deliveries. A webhook may be delivered more than once.

And related events may not arrive in the order the application expects.

Therefore, the backend should maintain durable payment state and process repeated events idempotently.

A browser redirect to a "success" page is not sufficient proof that the payment succeeded. The frontend can display the latest authoritative backend status.

The payment provider and backend records determine the actual result.

## 9.3 The inventory hold expires while payment is processing

Now for an unpleasant edge case. The reservation hold is valid for ten minutes.

The customer starts payment at minute nine. A delayed authentication step takes longer than expected.

The hold expires. The room becomes available to another customer.

Then the original payment succeeds. What happens?

We have a successful payment but no guaranteed inventory. This is why payment integration and reservation finalization require an explicit workflow.

Depending on the business requirements and provider capabilities, strategies might include:

- Extending holds while an authorized payment operation remains active.
- Authorizing payment before capturing funds.
- Finalizing the booking only after a suitable payment and inventory decision.
- Automatically refunding or voiding payment when fulfillment becomes impossible.
- Escalating exceptional states for reconciliation.

No design can simply assume that two independent organizations will commit their changes atomically. The workflow needs to handle partial completion.

We'll explore those patterns much more deeply in SE320–SE490. For our architecture workshop, the essential rule is:

**The user sees one booking operation, but the backend may be coordinating several independently failing systems.**

That coordination deserves an explicit owner and durable state.

---

# 10. Caching: Make Search Fast Without Selling Imaginary Rooms

Our product has a read-heavy workload. Many customers browse hotels.

Relatively few complete reservations. That's important because reads and writes have different scalability characteristics.

## 10.1 What should we cache?

| Resource | Initial strategy |
|---|---|
| Versioned JS/CSS | Long-lived browser/CDN caching |
| Hotel photographs | CDN caching |
| Public hotel descriptions | Cache with sensible invalidation |
| Search results | Short-lived caching where safe |
| Personal reservations | No shared caching |
| Final inventory claim | Authoritative database operation |

Hotel search is an interesting middle ground. Suppose 500 customers search:

```text id="8y32og"
Berlin, November 10–13, 2 guests
```

The results might be reused briefly, provided the cache key includes every relevant parameter and the response isn't personalized in an incompatible way.

That could reduce redundant backend work. But the cached results must not become a commitment of availability.

Imagine:

```text id="ge8o0f"
Search result:
1 room remaining
        │
        ▼
Customer clicks Reserve
        │
        ▼
Backend rechecks / claims inventory atomically
        │
        ├── Success
        │
        └── No longer available
```

This is acceptable product behavior when communicated properly. Availability may change between search and booking.

The frontend can show alternatives when the final reservation cannot proceed.

The alternative—attempting to guarantee that every visible search result remains bookable—would require expensive and complicated resource reservation semantics.

We don't need that guarantee for casual browsing. We need it for actual reservation commitments.

This is how requirements lead to simpler architecture.

---

# 11. Security: A Booking Platform Is a Multi-Tenant System

Our backend serves two broad user groups. Customers manage their own reservations.

Hotel operators manage their organization's listings, inventory, and bookings. That creates important authorization boundaries.

Imagine:

```text id="i6fu8u"
Hotel Group A
  ├── Hotel 1
  └── Hotel 2

Hotel Group B
  └── Hotel 3
```

An operator from Hotel Group A must not modify Hotel Group B's inventory. A customer must not access another customer's private booking.

These restrictions must be enforced in backend application logic and relevant data-access operations. They must not depend on hidden buttons in Vue.

## 11.1 Authentication choice

For our browser-first application, I'd seriously consider a server-managed session with a protected cookie. For example:

```http id="xakown"
Set-Cookie: __Host-session=...; Path=/; Secure; HttpOnly; SameSite=Lax
```

The backend validates the session and establishes the authenticated principal.

Sensitive cookie-authenticated operations must also have appropriate CSRF defenses.

Because we've arranged the browser-facing API under the application's own origin, we can avoid unnecessary cross-origin complexity for ordinary browser requests.

But that doesn't make our API private. Anyone can still send HTTP requests directly.

The backend must enforce authorization independently.

## 11.2 The broken object-level authorization test

Imagine:

```http id="u66aqk"
GET /api/reservations/9821
```

The backend recognizes Customer A. But reservation 9821 belongs to Customer B.

The correct result is denial of access, potentially represented as `404` or another appropriate response according to the API's disclosure policy.

The key is that identifying the user isn't enough. The request must be checked against the specific resource.

For hotel operators, the same applies to organization and hotel ownership.

This should be a high-priority test because it protects customer data and tenant boundaries.

## 11.3 Don't expose payment secrets to the frontend

The Vue application may use public identifiers or client-side payment SDK configuration supplied by the provider.

But private payment credentials belong in the backend environment. Vite build variables exposed to client code are not secret.

Everything shipped to the browser must be considered inspectable. This is not a subtle security principle.

It's a fundamental consequence of delivering executable code to an untrusted client.

---

# 12. Performance: Optimize the Experience, Not the Server Dashboard

Now suppose the product launches successfully. The backend responds quickly.

Yet the hotel search page feels slow on ordinary mobile phones. What would we measure?

First, remember our three Core Web Vitals.

| Metric | Good target |
|---|---|
| Largest Contentful Paint | ≤ 2.5 seconds |
| Interaction to Next Paint | ≤ 200 ms |
| Cumulative Layout Shift | ≤ 0.1 |

These targets refer to the 75th percentile of real-user visits, segmented appropriately. For our hotel application, likely performance risks include:

**Large hotel photographs.** We should serve appropriately sized images and prioritize important above-the-fold content.

**Too much initial JavaScript.** We should use route-level code splitting and avoid importing administrative features into customer search routes.

**Large result lists.** Virtualization or pagination may reduce browser rendering work.

**Late data dependencies.** The interface shouldn't wait for reviews and recommendations before showing useful hotel details.

**Unexpected layout shifts.** Image dimensions and loading placeholders should reserve stable space.

## 12.1 Would I add SSR immediately?

Not necessarily. For a five-person team building a strongly interactive SaaS, an ordinary Vue SPA may be a better starting point.

SSR adds infrastructure and complexity. It also creates server/client state synchronization and hydration concerns.

If public hotel pages eventually require stronger search-engine discoverability or significantly better initial content delivery, SSR may become attractive.

We can make that decision based on measurements and business requirements. The general principle:

**Choose the simplest rendering strategy that meets the actual user experience requirements.**

Not the most fashionable one.

---

# 13. Deployment: The Old Browser Must Survive the New Release

Now we need to deploy safely. Our Vue application is built with Vite.

The build produces files such as:

```text id="lz3ing"
index.html
assets/index.a92fd1.js
assets/SearchView.f81d72.js
assets/ReservationsView.e491ac.js
```

On the next release, the filenames change. We studied the danger in SE240-L04.

A customer might keep an old application tab open while the new deployment occurs.

If we delete the old lazy-loaded chunks immediately, that customer may encounter broken navigation. So our release strategy should:

1. Build and test the complete application.
2. Publish new versioned assets before switching the HTML entry point.
3. Retain previous assets for an appropriate compatibility window.
4. Use long-lived caching for immutable, content-versioned resources.
5. Use suitable revalidation for the HTML entry document.
6. Preserve API compatibility with browser clients still running previous releases.

The sixth point is particularly important. The browser may run version A while the backend runs version B.

They must still agree on the contract. This is why frontend deployment is not an atomic replacement of every user's application.

It's the introduction of a new version into an environment containing older versions.

## 13.1 Database migrations complicate deployment further

Suppose the new backend needs a renamed database column. If we rename it immediately, old backend instances might fail during rolling deployment.

A safer strategy can use the same expand–migrate–contract principle we applied to API contracts. First support the new representation.

Then migrate consumers. Then remove the obsolete representation when the transition is complete.

This is especially useful when frontend, backend, and database changes cannot all be activated simultaneously.

A reliable deployment strategy considers which software versions may coexist at each stage.

---

# 14. Testing: Protect the Important Invariants

We have limited engineering resources. We can't write comprehensive tests for every imaginable combination of browser, network, and business state.

So we prioritize. What would I test most seriously?

## 14.1 Inventory correctness

Create two concurrent booking attempts against the same final inventory unit. Verify that no more than one succeeds.

This must exercise the authoritative backend and database behavior. Mocking the database transaction would miss the most important part of the test.

## 14.2 Idempotency

Submit the same logical booking attempt multiple times using the same idempotency key. Verify that the backend does not create duplicate reservations.

Also verify that concurrent duplicate submissions behave correctly.

## 14.3 Authorization

Authenticate as Customer A. Attempt to retrieve Customer B's reservation.

The operation must be denied. Repeat equivalent checks for hotel organizations and privileged operations.

## 14.4 Critical frontend workflow

Use Playwright to test:

```text id="jkdxxk"
Search
   ↓
Select hotel
   ↓
Obtain quote
   ↓
Create hold
   ↓
Complete test payment
   ↓
Verify confirmation
```

At least one critical test should exercise a real test backend rather than only mocked responses.

## 14.5 Failure conditions

Inject controlled failures:

- An availability response arrives out of order.
- The booking request times out after successful server processing.
- The payment provider sends a duplicate event.
- A hotel becomes unavailable during checkout.
- The frontend is still running an older release.
- A background notification fails and requires retry.

We shouldn't measure testing success exclusively through coverage percentage. The question is whether meaningful failures are difficult to introduce unnoticed.

A good testing strategy follows the architecture's important risks.

---

# 15. Observability: How Will We Know Which Part Is Broken?

Imagine the product is now in production. Customer support reports:

"Bookings are failing." What does that actually mean?

Perhaps:

- The Reserve button isn't responding.
- The frontend sends invalid dates.
- The API rejects a stale quote.
- PostgreSQL is overloaded.
- The payment provider is unavailable.
- The reservation succeeds but the confirmation page fails.
- An email doesn't arrive.

Those are completely different incidents. A useful observability system must distinguish them.

## 15.1 Correlate operations across layers

Suppose a booking attempt has a request identifier:

```text id="47f6sb"
requestId = req-8f219
```

The browser may attach or receive a correlation identifier. The backend records it in relevant structured logs.

Database timing and external-service operations can be associated with the same trace or transaction context. Conceptually:

```text id="6b3r9d"
Browser booking attempt
        │
        ▼
API request req-8f219
        │
        ├── Authorization: 4 ms
        ├── Quote validation: 9 ms
        ├── Inventory transaction: 24 ms
        └── Payment operation: 820 ms
```

Now the performance bottleneck becomes visible. We know that the expensive portion is the payment operation, not the inventory transaction.

For asynchronous workflows, correlation identifiers can connect API requests, background jobs, and provider events.

But we must avoid storing sensitive card information or unnecessary personal data in logs. Observability itself must respect privacy and security boundaries.

## 15.2 Technical metrics and business metrics

Technical monitoring might track:

- Request latency.
- Error rates.
- Database connection pool usage.
- Queue depth.
- Failed background jobs.
- Browser JavaScript errors.
- Core Web Vitals.

Business monitoring should also track:

- Quote creation success.
- Inventory hold success.
- Reservation confirmation rate.
- Payment reconciliation failures.
- Reservations stuck in intermediate states.

The distinction matters. The API can return HTTP 200 for every request while the business workflow remains broken.

A senior engineer should monitor whether the product is accomplishing its purpose, not merely whether servers remain online.

---

# 16. The Architecture Review: Five Questions from a Skeptical Interviewer

We have a proposed architecture. Now let's challenge it.

This is the part of a senior interview where the interviewer changes the constraints and watches how you reason.

The objective isn't to defend every earlier decision as sacred. It's to demonstrate that you understand why the decisions were made and when they should change.

## Question 1 — "Traffic increases by 100×. What breaks first?"

The correct response is not:

"We move to microservices." We don't know what breaks first.

We need measurements. Perhaps the database is handling expensive search queries.

Perhaps the application servers are CPU-bound. Perhaps the payment provider imposes rate limits.

Perhaps the browser struggles with enormous result sets. Different bottlenecks require different solutions.

A sensible investigation would examine latency, throughput, CPU, memory, database query plans, connection pools, cache hit rates, and downstream dependencies.

If search queries dominate, we might introduce better indexes, caching, query optimization, or a dedicated search system.

If application CPU is the bottleneck, horizontal scaling may help if the application is designed appropriately.

If payment-provider limits dominate, adding more Node.js instances may make the problem worse by increasing request pressure.

**Scaling is the process of removing measured bottlenecks—not adding infrastructure until the architecture diagram looks expensive.**

## Question 2 — "Why not deploy the backend in three regions?"

Perhaps we eventually should. But multi-region architecture introduces difficult questions.

Where is authoritative inventory stored? Can two regions accept concurrent bookings for the same unit?

How are writes coordinated? What happens during a network partition?

What latency can we tolerate for cross-region consistency? Replicating stateless application servers is relatively straightforward.

Replicating authoritative transactional state while preserving strong guarantees is harder.

For our initial European market, one well-chosen primary region with suitable backups and recovery planning may be sufficient.

Global distribution should be justified by actual requirements.

## Question 3 — "Why not cache availability for five minutes?"

We can cache search availability for five minutes if the product tolerates that level of staleness and clearly treats it as informational.

But we cannot use that cached answer as the authority for final reservation decisions.

The backend must revalidate and claim inventory under correct transactional controls. Caching is a performance tool.

It doesn't replace correctness.

## Question 4 — "Why did you choose REST instead of GraphQL?"

Because our initial clients have straightforward needs, the team knows HTTP/JSON well, and the extra execution and operational complexity of GraphQL hasn't been justified.

If we later develop several clients with significantly different data requirements, or encounter substantial overfetching and endpoint proliferation, we can revisit the decision.

The important thing is that our API contracts remain intentional and well documented. REST is not inherently more scalable than GraphQL.

GraphQL is not inherently more modern or sophisticated. They're different tools.

## Question 5 — "What would you deliberately not build?"

This may be the most revealing question of the entire exercise. I would avoid, at least initially:

- Kubernetes without a demonstrated operational need.
- A microservice for every business capability.
- Multi-region writable inventory.
- A custom authentication protocol.
- A homemade payment-processing system.
- An elaborate event-driven architecture for operations that can remain local transactions.
- SSR for every page without a clear reason.
- A large caching layer before identifying actual bottlenecks.
- Abstract repository and service interfaces for every trivial function.

None of these technologies is inherently wrong. But every added component increases the system's operational and cognitive surface area.

For a small team, that cost matters.

**Architecture is partly the discipline of deciding which complexities you're willing to introduce—and which ones you can afford to postpone.**

---

# 17. Your Architecture Exercise

Now it's your turn. Imagine you've inherited the system we designed.

It has been running successfully for eighteen months. Traffic has increased substantially.

There are now 8,000 hotels. The application uses:

- Vue 3 and Vite.
- CloudFront and S3.
- Node.js modular monolith.
- PostgreSQL.
- Redis for selected caching and sessions.
- Background workers.
- An external payment provider.

Three new problems appear.

### Problem A — Search becomes slow

Search queries now take between 800 milliseconds and two seconds. The API servers have low CPU utilization.

PostgreSQL shows substantial query activity. What do you investigate?

Would you immediately introduce Elasticsearch or OpenSearch? Would you scale the Node.js service?

Or would you first examine database behavior?

### Problem B — Hotel operators want live inventory

A hotel operator updates available rooms. Another employee, using a different browser tab, should see the change quickly.

Customers should also receive reasonably fresh availability information. Would you introduce WebSockets?

Polling? Server-Sent Events?

Some combination? Where would authoritative state remain?

### Problem C — Payment incidents increase

The payment provider occasionally times out. Some payment events arrive more than once.

A small number of reservations remain stuck in an intermediate state. Would you add automatic retries?

How would you prevent duplicate effects? How would you detect and reconcile stuck operations?

Try sketching a proposed solution before reading the discussion. You don't need perfect answers.

The goal is to reason through the trade-offs.

---

# 18. Exercise Discussion

## Problem A — Slow search

Start with database evidence. Inspect query plans.

Check indexes. Look for expensive joins, unnecessary sorting, poor selectivity, N+1 behavior, and excessive data transfer.

Determine whether the same expensive searches are repeatedly executed. Short-lived caching might help.

Better indexes or query structure might solve the problem entirely.

If search requirements become sophisticated—full-text relevance, geographical filtering, complex ranking, high query volume—a dedicated search engine may eventually make sense.

But introducing one immediately adds synchronization and operational complexity.

We should first establish that PostgreSQL cannot satisfy the requirements reasonably with a simpler design.

## Problem B — Live inventory

Authoritative state remains in the backend database. A straightforward first implementation might use polling with an appropriate interval.

For example, an operator dashboard could refresh relevant inventory data every several seconds.

If the product needs low-latency updates across many active clients, server-push mechanisms such as WebSockets or Server-Sent Events become attractive.

But pushing events doesn't eliminate state synchronization issues. Clients can disconnect.

Messages can be missed. Updates can arrive out of order.

The frontend needs a way to recover authoritative state.

One practical architecture might push an event indicating that inventory changed, then invalidate or refresh the relevant query.

This avoids making every event carry the complete authoritative inventory representation.

The exact choice depends on latency requirements, client counts, and infrastructure.

## Problem C — Payment incidents

First, establish durable operation identity. Every payment attempt should have a stable identifier and appropriate idempotency guarantees.

Provider events should be authenticated and deduplicated. The system should record workflow states durably.

Retries should use controlled backoff, respect provider limits, and avoid repeating non-idempotent operations without appropriate protection.

A reconciliation process should identify reservations stuck in states such as:

```text id="fso1p8"
payment_pending
payment_unknown
confirmation_pending
```

It can query the payment provider or perform other authoritative recovery operations.

If the result cannot be resolved automatically, the system should surface it for investigation.

The critical lesson is that unreliable communication is expected in distributed workflows.

The architecture should make uncertain outcomes visible and recoverable rather than hiding them behind a generic error message.

---

# 19. The Final Architecture: Why This Is a Senior-Level Design

Return to Friday's incident with the architecture we've designed: transactional inventory lets only one of the competing reserves succeed; an uncertain payment enters a recoverable state instead of a false failure; CDN, search caching, Vue state boundaries, and observability each do their job without pretending to own the others.

What's interesting is what we didn't need. Not twelve microservices, Kubernetes, three writable database regions, or every communication mechanism under the sun—clear responsibilities and carefully selected guarantees. Some belong to HTTP, some to the browser, some to application code, some to PostgreSQL, some to external providers, and some require coordination between independently failing systems.

The architecture works because those responsibilities are explicit. Not because the diagram is complicated.

---

# 20. Final Consolidation — The Entire SE490 Course in One Mental Model

Let's connect the web stack one final time. A customer opens your application.

**Networking** determines how information reaches the service.

**HTTP** defines the semantics of requests, responses, methods, headers, caching, and status codes.

**The browser** parses, executes, lays out, paints, and composites the application.

**Frontend architecture** determines where responsibilities and dependencies belong.

**Reactive state management** keeps the interface synchronized with local values and manages potentially stale server data.

**API contracts** establish what independently deployed programs promise one another.

**Authentication and authorization** establish identities and permissions across trust boundaries.

**Build and deployment infrastructure** transforms source code into delivered assets while allowing different application versions to coexist.

**Performance engineering** examines how quickly real users can see and interact with useful content.

**Testing** establishes evidence that important behavior works under meaningful conditions.

And **system architecture** brings all of those concerns into one coherent product. The useful mental model is not:

```text id="nu5315"
Frontend → Backend → Database
```

That is only the skeleton. A more complete model is:

```text id="fd9iqp"
User Intent
    │
    ▼
Browser Runtime
    │
    ├── Rendering and Interaction
    ├── Local and Remote State
    ├── Security Restrictions
    └── Network Communication
    │
    ▼
HTTP / Edge Infrastructure
    │
    ├── Routing
    ├── Caching
    ├── Security
    └── Application Delivery
    │
    ▼
Backend Application
    │
    ├── Authentication
    ├── Authorization
    ├── API Contracts
    ├── Business Logic
    └── Workflow Coordination
    │
    ▼
Authoritative Data and External Systems
    │
    ├── Database
    ├── Payments
    ├── Background Processing
    └── Third-Party Integrations
```

Every arrow is a boundary, and every boundary carries assumptions—about format, identity, timing, reliability, or consistency. The most interesting engineering failures occur when two sides disagree about those assumptions: a provisional price treated as final, a timeout treated as failure, authentication mistaken for authorization, a cached response treated as fresh.

That is arguably the central lesson of modern web engineering.

---

# 21. What Makes Someone a Senior Engineer?

Senior engineering isn't knowing more protocol names or architectural patterns. It's judgment: asking what is slow and whether caching preserves freshness before proposing Redis; asking which module needs independent scaling before splitting a monolith; asking which state is authoritative before blaming Vue.

The difference is the ability to construct a causal model—to separate symptoms from causes, identify assumptions, evaluate trade-offs, and propose solutions proportional to the actual problem. A strong senior engineer doesn't need to know everything. They need to reason when several things interact and the correct answer isn't obvious.

That's what we've been practicing throughout this course.

---


---

## Next Lecture — SE490-L03: System Design Workshop: Build for 100× Traffic

Continue in **SE490 — Architecture and Systems Design Studio**.

## Further Reading — Optional References

1. [Vue — Scaling Up](https://vuejs.org/guide/scaling-up/state-management.html) — State architecture and application structure.
2. [Vue — Server-Side Rendering](https://vuejs.org/guide/scaling-up/ssr) — Rendering strategy, hydration, and server-state isolation.
3. [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — Method semantics, idempotency, and network interaction contracts.
4. [OWASP — API Security Top 10](https://api-security.owasp.org/editions/2023/en/0x11-t10/) — API authorization and other common security failures.
5. [AWS — CloudFront File Versioning](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/UpdatingExistingObjects.html) — Versioned asset delivery and deployment safety.
6. [web.dev — Core Web Vitals](https://web.dev/articles/vitals) — Measuring actual browser experience.
7. [PostgreSQL — Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) — A starting point for understanding concurrent database operations.
8. [Stripe — Idempotent Requests](https://docs.stripe.com/api/idempotent_requests) — A practical example of retry-safe payment API design.

---


*From entering a URL to architecting an entire production web application.*

The objective was never to memorize technologies—it was to understand why they exist, how they interact, where their guarantees end, and how to decide when those boundaries matter.

**The most valuable architecture isn't the one that anticipates every imaginable future. It's the one that solves today's real problems while leaving tomorrow's engineers room to make good decisions.**

---


