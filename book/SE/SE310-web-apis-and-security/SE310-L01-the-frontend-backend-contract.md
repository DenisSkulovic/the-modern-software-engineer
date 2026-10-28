---
id: SE310-L01
course: SE310
title: "The Frontend–Backend Contract"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S07]
prev: null
next: SE310-L02
---










# SE310 — Web APIs, Identity, and Security

## Lecture 01: The Frontend–Backend Contract

*How two perfectly correct pieces of software can combine into a completely broken application—and why API design is fundamentally about managing promises.*

---

# 1. The Deployment That Broke Nothing—and Everything

It's Tuesday afternoon at your hotel-booking company. The backend team has finished an important improvement.

Previously, hotel prices were represented as ordinary numbers:

```json
{
  "hotelId": 4812,
  "price": 149.99,
  "currency": "EUR"
}
```

The new implementation uses monetary amounts expressed in minor units:

```json
{
  "hotelId": 4812,
  "price": {
    "amountMinor": 14999,
    "currency": "EUR"
  }
}
```

This is a sensible improvement. Representing monetary values using floating-point numbers can produce precision problems, and explicit monetary structures make currencies and rounding policies easier to manage.

The backend developers update their TypeScript interfaces. They update their controllers. They update their tests. Everything passes.

The frontend team updates the Vue application to consume the new structure. Everything passes there too.

The backend deploys at 14:00. The frontend deploys at 14:05. By 14:10, customers are reporting broken price displays.

The frontend team investigates. The newest version of the application works.

But some customers are still running the previous JavaScript bundle.

One customer opened the booking page an hour earlier and never refreshed it. Another has an older cached application shell. A third is using a mobile client that hasn't been updated.

All three still expect:

```typescript
price: number
```

But the backend now returns:

```typescript
price: {
  amountMinor: number;
  currency: string;
}
```

The resulting frontend behavior ranges from ugly to catastrophic. One component displays:

```text
€[object Object]
```

Another produces `NaN`.

A third throws a runtime exception.

And all the tests are still green.

This is our first important discovery:

**Two independently correct implementations can be incompatible with one another.**

The problem isn't necessarily inside either implementation.

It's in the contract between them.

And unlike a function signature inside one TypeScript project, a network contract connects programs that may be deployed, updated, cached, restarted, and rolled back independently. That changes the engineering problem considerably.

---

# 2. An API Is a Promise, Not Just an Endpoint

Consider this endpoint:

```http
GET /api/hotels/4812
```

What does it promise? A junior developer might answer: "It returns hotel information." That's true, but insufficient.

A useful API contract must establish considerably more. For example:

- What input is accepted?
- What response structure is returned?
- Which fields are optional?
- What do their values mean?
- Which errors are possible?
- What authentication is required?
- Can responses be cached?
- Can requests be retried?
- Does the endpoint return current or potentially stale information?
- What happens when the contract evolves?

These details determine whether the client can use the API correctly. Imagine a response containing:

```json
{
  "availableRooms": 1
}
```

What does that mean?

Does it mean one room is available right now?

One room was available when the database query began?

One room was available when the cache was last refreshed?

Does the number include rooms temporarily held for other customers?

Is availability guaranteed until the customer finishes checkout?

The JSON structure cannot answer these questions.

Yet they are arguably more important than whether the property is called `availableRooms` or `roomsAvailable`.

This is the difference between a **data schema** and a **behavioral contract**. The schema defines the structure of messages. The behavioral contract defines what those messages mean and how the system behaves. A robust API requires both.

---

# 3. REST: Resources Instead of Remote Function Calls

Most web developers encounter REST long before studying what it actually means. They write:

```http
GET /api/hotels
POST /api/reservations
PUT /api/users/42
DELETE /api/favorites/18
```

And call the result a REST API. That's a reasonable everyday convention, although technically REST is a broader architectural style with constraints beyond mapping HTTP methods to CRUD operations. Let's focus on the ideas useful to application engineers.

## 3.1 Model resources, not database tables

Suppose a hotel-booking system contains:

```text
Hotels
Rooms
Reservations
Customers
Payments
```

A resource-oriented API might expose:

```http
GET /hotels/4812
GET /hotels/4812/rooms
GET /reservations/9821
POST /reservations
```

These identify meaningful entities or collections. The server decides how those resources are represented and maintained, and a resource doesn't need to correspond directly to one database table. For example:

```http
GET /reservations/9821
```

might assemble information from reservations, payments, customer profiles, and external hotel integrations. From the client's perspective, the reservation is one resource. The database's internal organization remains the backend's concern.

That's useful because it separates the API contract from the persistence implementation.

## 3.2 Not everything is CRUD

Now suppose the customer wants to cancel a reservation. Should we use:

```http
DELETE /reservations/9821
```

Maybe. But cancellation isn't necessarily deletion. The booking must remain available for auditing, refunds, accounting, and customer support. A domain-specific operation may be clearer:

```http
POST /reservations/9821/cancel
```

This is an action-oriented endpoint inside a broadly resource-oriented API. Perfectly pragmatic. The important issue isn't achieving ideological purity; it's communicating the intended operation accurately.

HTTP methods still matter, especially their safety and idempotency semantics from CS230-L03.

## 3.3 The benefit and limitation of REST

REST-style APIs work well because HTTP already provides useful concepts:

- Resource identifiers.
- Methods.
- Status codes.
- Headers.
- Caching.
- Conditional requests.

You can build upon those conventions rather than inventing everything yourself. But REST doesn't automatically determine the correct granularity of your resources. Suppose a hotel details page needs:

```text
Hotel details
Room availability
Customer loyalty benefits
Guest reviews
Pricing rules
```

A highly granular API might require five separate calls. That's not necessarily bad if they can execute concurrently and have useful independent caching policies. But if the frontend must perform them sequentially, latency accumulates.

A backend-for-frontend endpoint could instead aggregate the data needed for that particular interface. For example:

```http
GET /hotel-pages/4812?checkIn=2026-11-10
```

The architectural choice depends on the product's needs.

**Resource-oriented design should help clients accomplish useful work, not force them to reconstruct the backend's internal domain model through dozens of network calls.**

---

# 4. GraphQL: Let the Client Describe What It Needs

Now imagine our hotel platform has three different clients. A desktop application displays:

- Hotel description.
- Photos.
- Amenities.
- Room availability.
- Reviews.
- Nearby attractions.

A mobile application displays only:

- Name.
- Main photograph.
- Starting price.

An internal administration dashboard needs:

- Hotel identifiers.
- Inventory configuration.
- Supplier information.
- Operational status.

With conventional REST endpoints, you might build several specialized representations. GraphQL approaches the problem differently. Rather than having the server return one predefined resource representation, the client submits a query specifying which fields it wants. For example:

```graphql
query HotelDetails($id: ID!) {
  hotel(id: $id) {
    id
    name
    location {
      city
      country
    }
    rooms {
      id
      price {
        amountMinor
        currency
      }
    }
  }
}
```

The response follows the requested structure:

```json
{
  "data": {
    "hotel": {
      "id": "4812",
      "name": "Hotel Alexander",
      "location": {
        "city": "Berlin",
        "country": "Germany"
      },
      "rooms": [
        {
          "id": "73",
          "price": {
            "amountMinor": 14999,
            "currency": "EUR"
          }
        }
      ]
    }
  }
}
```

This gives the client greater control over the fields it retrieves.

## 4.1 The schema becomes central

A GraphQL server defines a type system describing what clients can query. For example:

```graphql
type Money {
  amountMinor: Int!
  currency: String!
}

type Room {
  id: ID!
  price: Money!
}

type Hotel {
  id: ID!
  name: String!
  rooms: [Room!]!
}

type Query {
  hotel(id: ID!): Hotel
}
```

This schema is an explicit contract. A client knows which fields exist and what types they return. GraphQL also has mechanisms for mutations and subscriptions, although subscriptions require additional implementation and transport considerations.

But here's where the attractive simplicity starts becoming complicated.

## 4.2 GraphQL doesn't make backend work disappear

Suppose the client requests:

```graphql
query {
  hotels {
    id
    name
    rooms {
      price {
        amountMinor
      }
    }
  }
}
```

The backend might resolve the query by:

1. Fetching 100 hotels.
2. Fetching rooms separately for each hotel.

That's potentially 101 database queries.

Sound familiar?

It's the classic **N+1 query problem**.

GraphQL didn't cause the underlying data-access inefficiency, but nested field resolution can make it easy to introduce. Techniques such as batching and request-scoped loaders can help.

There's another issue: query complexity. If clients can request deeply nested data and large collections without limits, a single operation may generate enormous backend work. GraphQL servers therefore need deliberate limits and authorization rules. The client choosing fields does not mean the client is authorized to access every field.

## 4.3 GraphQL errors deserve special attention

A GraphQL operation can produce both data and errors.

For example:

```json
{
  "data": {
    "hotel": {
      "id": "4812",
      "name": "Hotel Alexander"
    }
  },
  "errors": [
    {
      "message": "Reviews service unavailable"
    }
  ]
}
```

The exact shape depends on the schema, nullability, and execution result. Importantly, an HTTP `200 OK` response can contain GraphQL execution errors. This differs from the simple convention often used in REST-style JSON APIs, where HTTP status codes directly express the overall operation's success or failure. A GraphQL client must inspect the GraphQL response contract, not merely `response.ok`.

GraphQL is powerful, but it doesn't eliminate the need for thoughtful API semantics. It moves some complexity into schema design, execution, caching, authorization, and query-cost control.

---

# 5. RPC: When the Operation Matters More Than the Resource

There's another approach. Instead of modeling resources, explicitly model operations. This is the idea behind **Remote Procedure Call**, or RPC. Consider:

```text
CreateReservation
CancelReservation
CalculateQuote
ConfirmPayment
```

These are operations with meaningful inputs and outputs. An RPC API might define:

```protobuf
service ReservationService {
  rpc CreateReservation(CreateReservationRequest)
      returns (CreateReservationResponse);

  rpc CancelReservation(CancelReservationRequest)
      returns (CancelReservationResponse);
}
```

This resembles calling a function, except the function executes in another process, potentially on another machine. One popular RPC technology is gRPC, which commonly uses Protocol Buffers to define messages and services. For example:

```protobuf
message CreateReservationRequest {
  string hotel_id = 1;
  string room_id = 2;
  string idempotency_key = 3;
}

message CreateReservationResponse {
  string reservation_id = 1;
  string status = 2;
}
```

The numbered fields form part of Protocol Buffers' wire format. Those numbers cannot casually be changed or reused when evolving an established binary contract.

## 5.1 Why RPC can be attractive

RPC-style interfaces work especially well when:

- Operations are naturally command-oriented.
- Services communicate within a controlled environment.
- Strong interface definitions are desirable.
- Generated clients improve development efficiency.
- Efficient binary serialization is useful.

Imagine several backend services:

```text
Booking Service
      │
      ├──► Pricing Service
      │
      ├──► Inventory Service
      │
      └──► Payment Service
```

An RPC protocol might be perfectly suitable for some of these interactions. But don't mistake RPC syntax for local function-call semantics. A remote operation can fail because of network problems.

It can time out after the server successfully executes it.

It has serialization overhead, latency, and partial-failure behavior.

A function call inside one process and an RPC invocation may look similar in code, but they have fundamentally different failure models. This is one of the most important traps in distributed systems.

## 5.2 So which approach should you choose?

| Approach | Particularly useful when | Main trade-off |
|---|---|---|
| REST-style HTTP | Resource-oriented public APIs, browser integrations, conventional CRUD workflows | Endpoint granularity and response shapes require care |
| GraphQL | Clients need different projections of interconnected data | More sophisticated execution, caching, and complexity control |
| RPC / gRPC | Explicit service operations, strongly defined internal interfaces | Greater tooling and transport coupling; remote-failure semantics remain |

These are not mutually exclusive. A product might expose REST-style HTTP to browsers, use GraphQL for a complex internal dashboard, and use gRPC between selected backend services.

And technology selection is not the same as architecture quality.

A badly designed GraphQL schema is still a bad API. A badly designed gRPC service is still a bad service.

A well-designed conventional HTTP API can support sophisticated products for many years.

---

# 6. TypeScript Types Are Not Runtime Contracts

Let's return to our broken pricing deployment. The frontend expects:

```typescript
interface HotelResponse {
  id: number;
  price: number;
}
```

And executes:

```typescript
const response = await fetch("/api/hotels/4812");

const hotel: HotelResponse = await response.json();
```

This code might compile without complaint. Does that guarantee that `hotel.price` is a number? Absolutely not.

TypeScript's type system operates primarily at compile time. The JSON response comes from outside the TypeScript type system. At runtime, it could contain:

```json
{
  "id": 4812,
  "price": {
    "amountMinor": 14999
  }
}
```

Or:

```json
{
  "id": "definitely-not-a-number",
  "price": null
}
```

Or even:

```json
{
  "message": "Database unavailable"
}
```

A type annotation doesn't validate remote data. This is a critical distinction between **static expectations** and **runtime evidence**.

## 6.1 The trust boundary

A more accurate type for arbitrary incoming JSON is conceptually:

```typescript
const data: unknown = await response.json();
```

Now the application must establish that the data matches the expected contract before relying on it. You could write manual validation, or use a runtime schema library such as Zod. For example:

```typescript
import { z } from "zod";

const HotelSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  price: z.object({
    amountMinor: z.number().int().nonnegative(),
    currency: z.string().length(3)
  })
});

type Hotel = z.infer<typeof HotelSchema>;

async function fetchHotel(id: number): Promise<Hotel> {
  const response = await fetch(`/api/hotels/${id}`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const json: unknown = await response.json();

  return HotelSchema.parse(json);
}
```

Now the frontend has a runtime check at the external data boundary. It still doesn't prove that the price is commercially correct, that the currency is supported, or that the room is available. But it verifies important structural assumptions. That distinction matters.

**Schema validation verifies the shape and some constraints of data. Business validation determines whether the data represents an acceptable business operation.**

## 6.2 Validate on both sides

The backend should also validate incoming requests. Suppose a customer submits:

```json
{
  "hotelId": 4812,
  "guests": -500,
  "checkIn": "banana"
}
```

The server shouldn't trust the frontend merely because the official Vue application normally submits valid data. Anyone can construct an HTTP request without using your UI.

But validation involves several layers.

**Structural validation**

Are the required fields present? Are their types valid?

**Semantic validation**

Is checkout after check-in? Is the guest count within an acceptable range?

**Authorization**

Is this customer permitted to modify the requested reservation?

**Business consistency**

Is the room still available? Is the quoted price still valid? Can the booking transition to the requested state?

The last two cannot be solved by a JSON schema alone. They require access to authoritative application state and properly enforced business rules.

A senior engineer should be able to distinguish these layers rather than treating "we validate requests" as one mysterious checkbox.

---

# 7. Serialization: Where Good Data Quietly Changes Meaning

Even when both sides agree on field names, serialization can create subtle problems. JSON looks simple, but JavaScript, databases, and other programming languages do not all represent values identically.

## 7.1 Missing versus null

Consider:

```json
{
  "middleName": null
}
```

Now compare:

```json
{}
```

Are these equivalent?

Not necessarily.

The first explicitly supplies `null`.

The second omits the field entirely.

For a partial update, that difference may be essential.

For example, suppose a profile update accepts:

```json
{
  "phoneNumber": null
}
```

Does that mean: "Remove the existing phone number"? Meanwhile:

```json
{}
```

might mean: "Leave the phone number unchanged."

If the API doesn't define the difference, frontend and backend developers may implement contradictory behavior. This becomes particularly important for PATCH requests and partial updates.

## 7.2 The large-integer problem

JavaScript's ordinary `number` type represents integers exactly only within its safe integer range. The maximum safe integer is:

```typescript
Number.MAX_SAFE_INTEGER
// 9007199254740991
```

Now suppose a backend sends an identifier larger than that as a JSON number.

A JavaScript client may lose precision when parsing it.

Two distinct database identifiers can become indistinguishable in application code.

This is one reason large identifiers are frequently represented as strings in browser-facing API contracts. For example:

```json
{
  "reservationId": "9223372036854775807"
}
```

The identifier is not something the frontend needs to perform arithmetic on. Treating it as a string is often safer.

## 7.3 Time is another trap

Consider:

```json
{
  "checkIn": "2026-11-10"
}
```

This looks straightforward.

But is it a calendar date or an instant in time?

Those are different concepts.

A hotel check-in date often represents a local calendar date associated with the property's location.

Meanwhile:

```json
{
  "createdAt": "2026-11-10T14:30:00Z"
}
```

represents a specific UTC instant. Conflating these concepts can cause off-by-one-day problems and timezone confusion.

For timestamps, define a consistent representation and timezone semantics. For dates that are genuinely calendar dates, don't accidentally reinterpret them as UTC instants merely because the frontend uses JavaScript's `Date` class.

## 7.4 Money needs its own contract

Our opening incident involved monetary representation. Minor-unit integers are useful, but they aren't sufficient without clear rules. For example:

```json
{
  "amountMinor": 14999,
  "currency": "EUR"
}
```

means €149.99 if the currency uses two decimal places. But not every currency uses the same number of minor units, and some financial systems require intermediate precision beyond the currency's conventional display precision.

A robust monetary contract must establish:

- Which currency is represented.
- What the numeric unit means.
- Where rounding occurs.
- How taxes and fees are represented.
- Whether the amount is estimated, quoted, or final.

The field type is only part of the contract. Its meaning matters just as much.

---

# 8. Pagination: Why Returning Everything Is Not an API Strategy

Imagine your hotel search endpoint:

```http
GET /api/hotels?city=Berlin
```

Initially, it returns 100 hotels. Fine. Then the platform expands, and a search can return 50,000 listings.

Now the backend performs an enormous query, constructs a giant JSON response, and sends data the frontend may never display.

Pagination solves the immediate problem by dividing large collections into manageable pieces. But pagination has its own correctness questions.

## 8.1 Offset pagination

A familiar approach:

```http
GET /api/hotels?limit=20&offset=40
```

This asks for twenty records starting at offset forty in a defined ordering. It's simple, and it works well for many applications. But consider a changing dataset.

Suppose the ordering is newest first.

Page one returns records 100 through 81.

Before the user fetches page two, a new record is inserted at the beginning.

Now an offset of twenty may cause a record from the previous page to appear again.

Deletions can create the opposite problem: records may be skipped.

There's also a performance issue.

Large offsets can become expensive because the database may need to traverse or otherwise process many earlier rows before returning the requested slice. The exact cost depends on the database and query plan.

## 8.2 Cursor-based pagination

An alternative is to use a cursor identifying a position in a stable ordering. Suppose hotels are sorted by creation time and a unique ID:

```sql
SELECT id, name, created_at
FROM hotels
WHERE (created_at, id) < ($1, $2)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

The cursor represents the final `(created_at, id)` pair from the previous page. The next query retrieves records after that position in the chosen ordering. The unique ID acts as a tie-breaker when multiple records have the same creation timestamp.

A response might look like:

```json
{
  "items": [
    { "id": "4812", "name": "Hotel Alexander" }
  ],
  "nextCursor": "opaque-token",
  "hasMore": true
}
```

The client doesn't need to understand the cursor's internal format; it simply supplies it when requesting the next page. Cursor-based pagination can be more stable under insertions and more efficient for deep traversal when supported by suitable indexes.

But it isn't magic. If records are modified in ways that affect their sort position, duplicates or omissions may still be possible. And if your product requires a perfectly consistent snapshot across many page requests, you need additional design considerations.

## 8.3 Filtering and sorting are part of the contract

Suppose your API supports:

```http
GET /api/hotels?city=Berlin&sort=price&limit=20
```

What does `sort=price` mean?

Ascending or descending?

Does it include taxes?

Does it use the customer's selected currency?

How are equal prices ordered?

What happens if a filter is changed while paginating?

All of these choices affect consistency.

A good API defines stable defaults, deterministic ordering, sensible page-size limits, and predictable handling of invalid filters.

Most importantly, **pagination should happen at an appropriate backend data layer**, not by loading 50,000 records into Node.js and slicing the array afterward. The database should usually do the expensive selection work.

---

# 9. Errors Are Part of the Contract

Suppose the frontend submits a reservation:

```http
POST /api/reservations
```

The backend responds:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "Something went wrong"
}
```

Technically, you've returned an error.

But what can the frontend do with it?

Almost nothing.

Should it tell the user to change their dates?

Should it refresh availability?

Should it retry?

Should it send the user to login?

Should it contact customer support?

The error message doesn't explain the failure in a machine-readable way.

## 9.1 Stable error codes

Consider a more useful response:

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json
```

```json
{
  "type": "https://api.example.com/problems/room-unavailable",
  "title": "Room no longer available",
  "status": 409,
  "code": "ROOM_UNAVAILABLE",
  "detail": "The requested room is no longer available.",
  "requestId": "req-9281"
}
```

Here the status and problem details express a meaningful failure. The custom `code` field can provide a stable application-level identifier. The frontend can implement behavior such as:

```typescript
if (error.code === "ROOM_UNAVAILABLE") {
  await refreshAvailability();
  showAlternativeRooms();
}
```

This is considerably safer than inspecting human-readable messages. For example:

```typescript
if (error.message.includes("room")) {
  // ...
}
```

That approach is fragile. Error messages change. They get translated. Developers reword them.

Machine-readable codes should have stable documented meanings.

## 9.2 Errors should suggest appropriate actions

Different failures require different handling.

| Failure | Likely frontend behavior |
|---|---|
| Invalid date range | Highlight relevant fields |
| Authentication expired | Start an appropriate authentication flow |
| Room unavailable | Refresh alternatives |
| Request rate limited | Respect documented retry guidance |
| Temporary server failure | Offer retry where safe |
| Reservation outcome uncertain | Reconcile using operation identity |

This connects directly to Sessions 3 and 6. An HTTP status code doesn't automatically tell you whether retrying is safe, and a network timeout doesn't prove the business operation failed.

A good contract defines how clients should recover, not merely what they should display when everything succeeds.

---

# 10. API Versioning: The Art of Changing a Contract Without Breaking Its Consumers

Now we return to our original pricing incident. The backend replaced:

```json
{
  "price": 149.99
}
```

with:

```json
{
  "price": {
    "amountMinor": 14999,
    "currency": "EUR"
  }
}
```

The change is sensible.

But it breaks existing clients.

Why?

Because the contract associated with the field changed.

The old client expects a number. The new server returns an object.

A compatible evolution strategy must account for clients that haven't updated yet.

## 10.1 Additive evolution

One approach is to introduce the new field while retaining the old one temporarily:

```json
{
  "price": 149.99,
  "priceDetails": {
    "amountMinor": 14999,
    "currency": "EUR"
  }
}
```

New clients use `priceDetails`.

Old clients continue using `price`.

The backend supports both for a transition period.

Eventually, after the old field is no longer needed, the organization can plan its removal.

This is often called an **expand–migrate–contract** strategy.

```text
Expand
  │
  ├── Support old and new representations
  ▼
Migrate
  │
  ├── Update clients gradually
  ▼
Contract
  │
  └── Remove obsolete representation when safe
```

The elegance of this approach is that client and server deployments don't need to happen at exactly the same instant. That's vital for web applications.

A customer may keep a browser tab open for hours. A mobile client may remain outdated for months. An external API consumer may deploy on an entirely different schedule.

## 10.2 What counts as a breaking change?

Some changes are obviously breaking. For example:

- Removing a required field.
- Renaming an existing field.
- Changing a number into an object.
- Changing the meaning of a value.
- Making a previously optional request field mandatory.
- Changing response status behavior relied upon by clients.

But even apparently additive changes can sometimes cause problems. Suppose a response uses:

```typescript
type BookingStatus =
  | "pending"
  | "confirmed"
  | "cancelled";
```

The backend introduces:

```text
payment_review
```

A frontend may use an exhaustive switch that assumes the original three values are the only possibilities. The additional status can break its assumptions.

Or imagine introducing a new required field in a response schema, only to discover that older backend instances can't provide it during a rolling deployment.

Compatibility depends on the expectations of actual consumers.

Not merely whether the change looks additive in isolation.

## 10.3 Should you create `/v2`?

Sometimes a new major API version is appropriate:

```http
GET /api/v1/hotels/4812
GET /api/v2/hotels/4812
```

This provides explicit separation between contracts. But versioning has costs. You may need to maintain both versions for a substantial period, and documentation, tests, infrastructure, and bug fixes become more complex. And maintaining `/v2` doesn't automatically make incompatible changes safe within that version.

A good default is to evolve existing contracts compatibly wherever practical. Introduce explicit versions when the benefits of separating incompatible behavior justify the operational cost.

## 10.4 Rollbacks are part of compatibility planning

Consider this deployment order:

1. Backend expands the response.
2. Frontend begins consuming the new field.
3. The backend deployment encounters an unrelated issue.
4. Operations rolls it back.

Does the new frontend still work? Only if the rollback target supports the fields the new frontend requires—or if the frontend tolerates their absence. This is why compatibility should often be considered in both directions across the intended deployment and rollback window.

A successful rollout plan isn't merely: "Deploy the backend first." It's: "Ensure the combinations of client and server versions likely to coexist can communicate correctly." That includes old browser tabs, rolling deployments, mobile applications, CDN behavior, and rollback scenarios.

---

# 11. OpenAPI, Contract Tests, and the Limits of Documentation

How can teams reduce the risk of incompatible changes? One approach is to define the API contract explicitly. For conventional HTTP APIs, **OpenAPI** provides a standardized way to describe endpoints, parameters, responses, schemas, and other characteristics. A simplified specification might contain:

```yaml
openapi: 3.1.0

info:
  title: Hotel API
  version: 1.0.0

paths:
  /hotels/{id}:
    get:
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string

      responses:
        "200":
          description: Hotel details
          content:
            application/json:
              schema:
                type: object
                required:
                  - id
                  - name
                properties:
                  id:
                    type: string
                  name:
                    type: string
```

This gives tools and developers a machine-readable description of the interface. OpenAPI can support:

- Documentation generation.
- Typed client generation.
- Schema validation.
- Mock-server creation.
- Compatibility checks.
- Contract-oriented testing.

The specification above is intentionally minimal; a production API description would cover more response cases and reuse schemas where appropriate.

## 11.1 Generated types don't guarantee runtime correctness

Suppose you generate TypeScript interfaces from OpenAPI. That's useful, because it reduces manual duplication. But what if the deployed backend doesn't actually follow the specification? Your generated types are still only expectations. Therefore, teams often combine generated contracts with runtime validation or tests that exercise the real API implementation.

The distinction is important:

**A contract document describes the agreement. A contract test checks whether an implementation honors it.**

## 11.2 Consumer-driven contract testing

Imagine a frontend depends on:

```json
{
  "reservationId": "9821",
  "status": "confirmed"
}
```

A consumer-driven contract test can describe that expectation. The backend provider can verify that its implementation satisfies the consumer's required interaction. This can identify incompatibilities before deployment. Tools such as Pact support this style of testing.

But contract tests don't establish everything. They may verify response structure while failing to capture important business behavior. For example, a contract test might confirm that a reservation response includes:

```json
{
  "status": "confirmed"
}
```

It doesn't automatically prove that inventory was correctly decremented, payment was handled safely, or duplicate reservations are impossible. Those require additional integration, business, and concurrency tests.

Contract testing is one layer of verification—not a replacement for all other forms of testing.

---

# 12. A Practical Design Exercise: Build a Reservation API Contract

Let's assemble a reasonable contract for creating a reservation. We want the frontend to submit a booking attempt. The backend must validate the request, check authoritative availability, and create a reservation safely.

A request could look like:

```http
POST /api/reservations
Content-Type: application/json
Idempotency-Key: 5a92b6...
```

```json
{
  "roomId": "73",
  "checkIn": "2026-11-10",
  "checkOut": "2026-11-13",
  "guests": 2,
  "quoteId": "quote-481"
}
```

Why include `quoteId`? Because the quoted price and conditions may have been determined earlier. Rather than trusting a price supplied by the browser, the backend can retrieve or validate the relevant quote.

A successful response:

```http
HTTP/1.1 201 Created
Location: /api/reservations/9821
Content-Type: application/json
```

```json
{
  "reservationId": "9821",
  "status": "confirmed",
  "total": {
    "amountMinor": 44997,
    "currency": "EUR"
  }
}
```

A failed availability check might return:

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json
```

```json
{
  "type": "https://api.example.com/problems/room-unavailable",
  "title": "Room unavailable",
  "status": 409,
  "code": "ROOM_UNAVAILABLE"
}
```

If the request times out, the client must not blindly create a new booking with a different idempotency key. It should retry according to the documented idempotency contract or query the operation's authoritative status.

Now notice how many concepts we've brought together. The HTTP method communicates the operation's nature.

The schema defines the request and response shape.

Validation protects the backend from malformed inputs.

Authorization determines whether the caller may act.

Business rules determine whether the booking is permitted.

Idempotency protects against duplicate execution. The response status and error model guide frontend behavior. Version compatibility ensures the interaction survives deployments.

That's what a complete frontend–backend contract looks like. Not merely a JSON interface.

---

# 13. Practical Investigation

Here are two worthwhile exercises that don't require a large project.

## Experiment A — Break a contract deliberately

Create a simple TypeScript interface:

```typescript
interface Hotel {
  id: string;
  price: number;
}
```

Then parse this JSON:

```typescript
const raw = JSON.parse(`
{
  "id": "4812",
  "price": {
    "amountMinor": 14999,
    "currency": "EUR"
  }
}
`);

const hotel = raw as Hotel;

console.log(hotel.price.toFixed(2));
```

The code may compile.

At runtime, it fails.

Why?

Because the type assertion doesn't transform the actual object.

Now implement runtime validation using your preferred schema library. Observe the difference between discovering a contract mismatch at a controlled validation boundary and encountering an exception deep inside a UI component.

## Experiment B — Observe pagination instability

Imagine a collection ordered by descending ID:

```text
100, 99, 98, 97, 96, 95
```

Your API returns three records per page. Page one:

```text
100, 99, 98
```

Before page two is requested, another record is inserted:

```text
101, 100, 99, 98, 97, 96, 95
```

What does `offset=3` return now?

```text
98, 97, 96
```

Record 98 appears twice.

Now try cursor-based pagination using the final ID from the first page:

```text
cursor = 98
```

The next query retrieves:

```text
97, 96, 95
```

This demonstrates one advantage of continuing from a stable position rather than a numeric offset. It doesn't eliminate every possible consistency issue, but it shows why pagination design matters for changing datasets.

---

# 14. Engineering and Interview Challenges

### Challenge 1 — The Harmless Field

A backend engineer adds a new status:

```text
payment_review
```

to an existing reservation status enum. The engineer argues that no fields were removed, so the change is backward compatible.

Do you agree?

### Challenge 2 — REST versus GraphQL

You have a mobile app and a desktop app that need substantially different subsets of hotel information.

Would GraphQL necessarily be the better choice? What factors would influence your decision?

### Challenge 3 — The TypeScript Illusion

A team generates frontend TypeScript types from the backend's OpenAPI specification.

Can the frontend now safely assume every response follows those types? What additional protections might be worthwhile?

### Challenge 4 — The Broken Rollback

The backend adds a new required response field. The frontend is updated to depend on it. Then the backend is rolled back to an older version that doesn't return the field.

What went wrong in the deployment strategy?

### Challenge 5 — The Booking Contract

A reservation endpoint accepts the room ID, date range, and a price supplied by the frontend. The backend validates that the price is a positive number.

Is the validation sufficient? What should the backend do instead?

---

# 15. Solutions and Discussion

**Challenge 1**

Not necessarily.

Adding a new enum value may break clients that assume the original set is exhaustive. For example, a frontend might have a switch statement with no fallback behavior. Compatibility requires examining actual consumer expectations.

Possible mitigations include supporting unknown values gracefully, documenting extensible enums, and coordinating changes that alter business workflows.

**Challenge 2**

No. GraphQL may reduce overfetching and allow clients to select different representations. But it introduces schema, execution, caching, authorization, and query-complexity considerations.

A few thoughtfully designed REST-style endpoints might satisfy both clients with less operational complexity. The decision should reflect actual client requirements, team experience, performance needs, and expected schema evolution.

**Challenge 3**

No. Generated types express the documented contract, not guaranteed runtime behavior. The server may deploy an incompatible implementation or return unexpected data.

Runtime schema validation, provider contract tests, integration tests, and careful deployment compatibility policies can reduce those risks.

**Challenge 4**

The rollout didn't preserve compatibility across the expected rollback window. The team needed to ensure that the new frontend could coexist with an older backend or that rollback procedures maintained the required contract.

An expand–migrate–contract strategy could have provided a safer transition.

**Challenge 5**

No. A positive price can still be incorrect or malicious. The frontend is an untrusted participant.

The backend should determine the authoritative price or validate a server-issued quote, including applicable conditions, currency, expiration, availability, and pricing rules. Structural validation is necessary, but it doesn't establish business correctness.

---

# 16. The Mental Model Worth Keeping

An API is not merely a collection of endpoints. It's an agreement between independently executing programs.

The most important principles are:

**Contracts include meaning, not just structure.** A field can have the correct type and still be interpreted incorrectly.

**Remote data must be validated.** TypeScript interfaces don't enforce runtime behavior across network boundaries.

**Choose communication styles deliberately.** REST, GraphQL, and RPC solve different problems and introduce different trade-offs.

**Design collections for scale.** Pagination, filtering, stable ordering, and bounded queries are part of the API's usability and performance.

**Errors must be actionable.** Stable machine-readable error codes let clients recover intelligently.

**Compatibility is an operational concern.** Real clients and servers are not updated atomically. Old versions, cached applications, rolling deployments, and rollbacks will coexist.

**Business correctness belongs to authoritative systems.** A frontend can display, estimate, and request operations, but cannot enforce trustworthy financial or inventory rules.

And the single most important lesson:

**A reliable API contract allows implementations to evolve independently without forcing every participant to change at precisely the same moment.**

That's the difference between software components that happen to communicate today and a system that can continue evolving for years.

---

# 17. Next Session — Authentication and Browser Security

A correctly designed reservation API can still leak another customer's booking if a valid, well-formed authenticated request is answered without checking whether that caller may access that resource. Authentication proves who the caller is; authorization decides what they're allowed to do.

In **SE310-L02 — Authentication and Browser Security**, we'll investigate authentication versus authorization, sessions, cookies, bearer tokens, OAuth 2.0, OpenID Connect, same-origin policy, CORS, CSRF, and XSS—and why securing a modern web application means defending several different trust boundaries.

---


---

## Next Lecture — SE310-L02: Authentication and Browser Security

Continue in **SE310 — Web APIs, Identity, and Security**.

## Further Reading — Optional References

1. [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — Resources, methods, response semantics, and conditional requests.
2. [OpenAPI Specification](https://spec.openapis.org/oas/) — Machine-readable HTTP API contracts.
3. [GraphQL — Learn](https://graphql.org/learn/) — Schemas, queries, mutations, execution, and errors.
4. [Microsoft — Web API Design Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design) — Practical resource modeling, pagination, versioning, and compatibility.
5. [Protocol Buffers — Best Practices](https://protobuf.dev/best-practices/dos-donts/) — Evolving binary message contracts safely.
6. [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html) — Structured, standardized error descriptions.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE310-L01  THE FRONTEND–BACKEND CONTRACT — INTERVIEW GLANCE CARD

OPENING INCIDENT
  price: number → { amountMinor, currency }  Backend & FE tests green; old tabs/caches break
  Lesson         Independently correct implementations can be incompatible
  Contract       Lives across independently deployed/cached/rolled-back programs

API = PROMISE
  Beyond “returns hotel”  Inputs, shape, optionality, meaning, errors, auth, cache, retry, staleness, evolution
  Schema vs behavior      Structure of messages ≠ what they mean / how system behaves
  availableRooms=1        Now? Query start? Cache? Holds? Guaranteed through checkout?

REST-STYLE
  Resources ≠ tables      GET /reservations/9821 may join many stores
  Not all CRUD            Cancel may be POST …/cancel (audit/refunds) ≠ DELETE
  Methods matter          Safety / idempotency (CS230-L03)
  Granularity             Many fine calls vs BFF aggregate for a page — product choice

GRAPHQL
  Client selects fields   Schema = explicit type contract; mutations/subscriptions exist
  N+1 risk                Nested resolvers can explode queries; batching/loaders
  Complexity / authz      Field choice ≠ permission; need limits
  Errors                  HTTP 200 can still carry GraphQL errors — inspect response, not only ok

RPC / gRPC
  Operations              CreateReservation, Cancel…; Protobuf field numbers are wire contract
  Attractive for          Command-oriented internal services; codegen; binary
  Trap                    Looks like a local call — network failures, timeouts after success, partial failure
  Mix OK                  Browser REST · dashboard GraphQL · internal gRPC — design quality > fashion

TYPES ≠ RUNTIME
  TS annotation           Does not validate JSON from the network
  Trust boundary          unknown + Zod/schema parse at edge
  Schema vs business      Shape OK ≠ commercially acceptable / bookable
  Validate both sides     Structural · semantic · authorization · business consistency
  Client untrusted        Anyone can craft HTTP without your Vue UI

SERIALIZATION TRAPS
  null vs omitted         PATCH: clear field vs leave unchanged — define it
  Large IDs               Beyond MAX_SAFE_INTEGER → prefer string IDs in browser APIs
  Date vs instant         "2026-11-10" calendar ≠ "…Z" UTC instant
  Money                   amountMinor + currency + rounding/tax/estimate|quote|final meaning

PAGINATION
  Offset                  Simple; inserts/deletes → dupes/skips; large offsets costly
  Cursor                  Stable position + tie-breaker; opaque nextCursor; still not perfect snapshots
  Filters/sort            Part of contract; paginate in DB — don't load 50k into Node then slice

ERRORS
  Useless                 400 + "Something went wrong"
  Useful                  problem+json + stable code (ROOM_UNAVAILABLE) → actionable UI
  Don't parse             Human message strings
  Guide recovery          Field fix / reauth / refresh / retry-if-safe / reconcile unknown

VERSIONING
  Expand–migrate–contract Add new field · migrate clients · remove old when safe
  Breaking                Remove/rename/type change/meaning change/new required request field…
  Subtle break            New enum value breaks exhaustive switches
  /v2                     Costly dual maintenance; prefer compatible evolution when practical
  Rollbacks               New FE must tolerate older BE (or reverse) across coexistence window

OPENAPI / CONTRACT TESTS
  Spec                    Documents agreement; codegen helps
  Contract test           Checks implementation honors consumer expectations (e.g. Pact)
  Limit                   Structure ≠ inventory/payment correctness

RESERVATION CONTRACT SKETCH
  POST + Idempotency-Key; quoteId not client price; 201 + Location; 409 ROOM_UNAVAILABLE
  Timeout                 Don't new-key blind retry — status / idempotent retry

SENIOR LINE: Reliable contracts let sides evolve without everyone changing at the same instant.
```

