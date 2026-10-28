---
id: SE240-L02
course: SE240
title: "Frontend Architecture Beyond Components"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S05]
prev: SE240-L01
next: SE240-L03
---








# SE240 — Browser and Frontend Engineering

## Lecture 02: Frontend Architecture Beyond Components

*How a beautiful little Vue application becomes an architectural nightmare—and how to prevent it without turning your frontend into a miniature government bureaucracy.*

---

# 1. The €37 That Appeared Out of Nowhere

Your hotel-booking platform has been running successfully for eighteen months.

What began as a modest Vue application now contains roughly 250 components, dozens of composables, several Pinia stores, and integrations with multiple backend services.

The application works. Customers make reservations. The business is growing.

Then someone in product management requests a seemingly trivial change.

> "We now offer a 10% loyalty discount. Please make sure customers see their discounted price everywhere."

Simple enough. You update the hotel search page. The displayed price changes from €370 to €333. Excellent. Then QA discovers that the hotel details page still displays €370.

You fix that too.

Then someone notices that the booking confirmation page displays €333, but the payment summary displays €370.

You investigate.

It turns out that four different components calculate the total price independently.

One uses a utility function. Another relies on a computed property. A third reads a value from a Pinia store. The fourth simply displays the price returned by an API.

Meanwhile, the currency selector modifies a global state variable, and one of the pricing components directly imports the authentication store to check whether the customer qualifies for loyalty discounts.

Somewhere in this mess, the loyalty rule has been implemented three times.

The actual backend still calculates the authoritative price correctly, fortunately. But the frontend presents conflicting figures.

A senior developer suggests extracting everything into a new composable:

```typescript
useHotelPricing()
```

A week later, that composable contains 600 lines of code. It imports three stores, calls two APIs, reads route parameters, handles error notifications, calculates discounts, and updates checkout state.

Congratulations.

You've moved the mess into a different file.

The underlying architectural problem remains.

**Your application has no clear answer to the question: Who is responsible for what?**

And this is where frontend architecture begins. Not with folder names. Not with choosing Pinia over another library. Not with deciding whether components should be 100 or 300 lines long. Architecture begins with responsibilities, boundaries, and dependencies.

---

# 2. Components Are Not an Architecture

Vue encourages us to decompose interfaces into components.

That's a good thing.

A hotel search interface might contain:

```text
HotelSearchPage
├── SearchFilters
│   ├── LocationSelector
│   ├── DateRangePicker
│   └── GuestSelector
│
├── SortingControls
│
└── HotelResults
    ├── HotelCard
    ├── HotelCard
    └── HotelCard
```

This is a useful decomposition of the visible interface. But it doesn't tell us where the business logic belongs. Who determines whether a hotel is refundable? Who knows how loyalty discounts work? Who decides whether search results are stale? Who communicates with the backend? Who owns the selected currency? And what happens when the same information is needed on a completely different page?

A component tree describes **visual composition**. An application architecture describes **responsibilities and dependencies**. Those are different structures. A component can be beautifully written and still participate in a terrible architecture. Consider:

```vue
<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import { useCurrencyStore } from "@/stores/currency";
import { useBookingStore } from "@/stores/booking";
import { getLoyaltyDiscount } from "@/utils/pricing";
import { fetchHotelDetails } from "@/services/hotels";

const auth = useAuthStore();
const currency = useCurrencyStore();
const booking = useBookingStore();

// Another 150 lines of application logic...
</script>
```

There's nothing inherently wrong with importing stores or services into a component.

The problem emerges when many components independently coordinate the same business process.

Each component becomes a small application inside the larger application.

And each one develops its own assumptions.

The hotel search card thinks the customer price is calculated one way.

The checkout component thinks it's calculated another way.

The payment component has a third interpretation.

The architectural problem is not code duplication alone. It's **knowledge duplication**. Several parts of the system believe they own the same rule. That becomes dangerous because business rules change.

---

# 3. Coupling and Cohesion: Two Old Ideas That Still Explain Everything

Software architecture has invented an impressive collection of terminology over the decades.

Some of it is genuinely useful.

Some of it is primarily useful for making conference presentations last forty minutes.

Two concepts, however, have survived for excellent reasons:

**Coupling** and **cohesion**.

## 3.1 Coupling: How much do modules depend on one another?

Suppose a component imports:

```typescript
import { useAuthStore } from "@/stores/auth";
import { useBookingStore } from "@/stores/booking";
import { usePaymentStore } from "@/stores/payment";
import { useSearchStore } from "@/stores/search";
```

Does that automatically mean the component is badly designed? No. But it should make you curious.

Why does this component know about so many different application concerns?

What happens when the payment architecture changes?

What happens when authentication is redesigned?

How many unrelated components will require modification?

Coupling describes how strongly different parts of a system depend on one another.

A tightly coupled system often exhibits **change propagation**. You modify one feature. Unexpectedly, several other features must change too. Good architecture doesn't eliminate dependencies. That's impossible. It makes them deliberate, understandable, and reasonably stable.

## 3.2 Cohesion: Do related responsibilities live together?

Imagine a module containing:

```typescript
export function calculateHotelPrice() { /* ... */ }

export function validateEmail() { /* ... */ }

export function getBrowserWidth() { /* ... */ }

export function sendAnalyticsEvent() { /* ... */ }
```

All four functions might work perfectly.

But why do they belong together?

What is the module actually responsible for?

A cohesive module contains functionality that belongs to a meaningful common purpose. For example:

```text
booking-pricing/
├── calculate-subtotal.ts
├── apply-discount.ts
├── price-types.ts
└── pricing.test.ts
```

This is much easier to understand as a unit of responsibility. The files collectively concern pricing calculations. We can summarize the architectural ambition as:

> Keep related responsibilities together, and minimize unnecessary dependencies between unrelated responsibilities.

This sounds almost embarrassingly simple.

Yet it explains an enormous percentage of software maintainability problems.

## 3.3 The real test: What happens when requirements change?

A useful way to evaluate architecture is to imagine a future change. Suppose the business introduces a new booking cancellation policy.

In a well-structured system, you'd expect to modify a reasonably identifiable area.

In a poorly structured system, you might search through thirty components for scattered conditions such as:

```typescript
booking.isRefundable
```

or:

```typescript
hoursBeforeCheckIn > 24
```

or:

```typescript
booking.status !== "confirmed"
```

Each developer implemented a slightly different interpretation of the rule. This is where architecture begins to pay for itself. Not because the code looks prettier. Because the cost and risk of change become more predictable.

---

# 4. Four Responsibilities Worth Separating

Let's examine our hotel-booking frontend through four conceptual responsibilities.

These aren't mandatory directories or rigid layers.

They're different kinds of work that benefit from being distinguished.

## 4.1 Presentation: What should the user see?

Presentation logic concerns the visible interface and user interactions. A `HotelPrice.vue` component might receive:

```typescript
interface Props {
  amountCents: number;
  currency: string;
  discounted: boolean;
}
```

Its responsibility is to display a price appropriately.

It may format the number, display a discount badge, or choose relevant visual styling.

It shouldn't independently decide whether the customer qualifies for the discount.

Why not?

Because eligibility is a business rule.

If the component owns that decision, every other location displaying discounted prices must somehow reproduce the same logic.

A useful principle:

**Components should primarily express the interface, not independently invent the business meaning of the data they display.**

That doesn't mean components must be completely free of logic. A dropdown handling keyboard navigation obviously contains behavioral logic. A form component may validate whether a required field is empty. The distinction is between logic inherent to the interface and rules belonging to the product's business domain.

## 4.2 Application logic: What is the user trying to accomplish?

Imagine the user clicks:

```text
Confirm Reservation
```

The application must coordinate several steps.

It might:

1. Validate required form inputs.
2. Submit the reservation request.
3. Track pending or failed operation states.
4. Navigate to the confirmation page after success.

This is application orchestration. It coordinates a user-facing workflow. It doesn't necessarily need to decide how prices are calculated or how database transactions work. A composable or feature-level controller might own this behavior.

## 4.3 Domain logic: What are the business rules?

Domain logic expresses concepts specific to the problem being solved. Examples include:

- Whether a reservation can be cancelled.
- How a loyalty discount affects an estimated price.
- Which booking statuses permit modification.
- Whether a search date range is valid.
- Which room policies are compatible with a requested booking.

Some of these rules can be represented as ordinary TypeScript functions.

For example:

```typescript
interface DiscountInput {
  subtotalCents: number;
  discountPercent: number;
}

export function calculateDiscountedSubtotal({
  subtotalCents,
  discountPercent
}: DiscountInput): number {
  if (
    !Number.isSafeInteger(subtotalCents) ||
    subtotalCents < 0 ||
    !Number.isInteger(discountPercent) ||
    discountPercent < 0 ||
    discountPercent > 100
  ) {
    throw new Error("Invalid discount input");
  }

  const discountCents = Math.round(
    subtotalCents * discountPercent / 100
  );

  return subtotalCents - discountCents;
}
```

This function is deliberately independent of Vue. It doesn't import Pinia. It doesn't know which page is currently open. It doesn't make network requests. It takes inputs and produces an output. That makes it easy to understand and test.

The example assumes non-negative minor-unit amounts, integer percentage discounts, and a particular rounding policy. Real pricing systems must define currency-specific precision, rounding, taxes, fees, and other rules explicitly.

There's also a critical security distinction.

The frontend may calculate an **estimated display price**.

The backend must still determine and validate the authoritative booking price.

A malicious client can modify its JavaScript, request payloads, and local state.

Frontend domain logic is useful for consistency and user experience, not as a trusted financial enforcement boundary.

## 4.4 Infrastructure: How does the application communicate with the outside world?

Infrastructure concerns implementation mechanisms. For example:

```typescript
export async function fetchHotels(
  city: string
): Promise<HotelDto[]> {
  const response = await fetch(
    `/api/hotels?city=${encodeURIComponent(city)}`
  );

  if (!response.ok) {
    throw new Error("Hotel request failed");
  }

  return response.json();
}
```

This function knows about HTTP and the API.

But it doesn't need to know how the hotel card is styled.

Nor should the pricing calculation need to know whether hotel data came from REST, GraphQL, or a mock fixture.

A healthy architecture prevents unnecessary knowledge from leaking across these responsibilities.

Conceptually:

```text
Vue Components
      │
      ▼
Application / Feature Logic
      │
      ├────────► Domain Rules
      │
      ▼
API / Infrastructure Adapters
      │
      ▼
Backend Services
```

This is a useful mental model, not a requirement to construct four folders and a factory class for every button. The amount of architectural separation should be proportional to the complexity of the product.

---

# 5. Organizing by Technical Type Versus Organizing by Feature

One of the most common frontend structures looks like this:

```text
src/
├── components/
├── composables/
├── stores/
├── services/
├── utils/
├── types/
├── views/
└── router/
```

There's nothing inherently wrong with it.

For a small application, it's perfectly reasonable.

But imagine 250 components and fifty composables.

What happens when a developer wants to understand the reservation feature?

They may need to open files scattered across every directory.

The code is organized according to **what kind of file it is**, rather than **what business capability it belongs to**.

That's a meaningful difference.

## 5.1 Feature-based organization

An alternative is to organize substantial functionality around business features. For example:

```text
src/
├── app/
│   ├── router/
│   └── main.ts
│
├── features/
│   ├── hotel-search/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── api/
│   │   ├── model/
│   │   └── index.ts
│   │
│   ├── reservations/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── api/
│   │   ├── model/
│   │   └── index.ts
│   │
│   └── payments/
│       ├── components/
│       ├── api/
│       └── index.ts
│
└── shared/
    ├── ui/
    ├── formatting/
    └── http/
```

Now the hotel-search feature has a recognizable home. A developer investigating search behavior can find most relevant implementation details nearby. This is sometimes called **vertical slicing**. Instead of separating every technical concern across the entire application, we group code around a coherent capability.

## 5.2 Why feature boundaries matter more than folders

Here's the catch.

You can reorganize files into feature directories and accomplish almost nothing architecturally.

Suppose:

```typescript
// features/hotel-search/components/HotelCard.vue
import { usePaymentStore } from
  "@/features/payments/model/paymentStore";
```

And:

```typescript
// features/payments/components/PaymentForm.vue
import { useSearchStore } from
  "@/features/hotel-search/model/searchStore";
```

The files are neatly organized. But the features remain tightly coupled. The real issue is dependency direction. A folder structure is only useful if it reflects meaningful boundaries. That requires deciding which parts of a feature are public and which are internal implementation details.

---

# 6. Public Interfaces: Stop Reaching into Everyone Else's Drawers

Imagine the reservations feature provides a capability:

```typescript
export async function startReservation(
  hotelId: string
): Promise<void> {
  // Coordinate reservation creation.
}
```

Another feature needs to initiate a reservation.

It should ideally depend on a stable, intentional interface.

For example:

```typescript
import {
  startReservation
} from "@/features/reservations";
```

The reservations feature can expose that function through its public entry point:

```typescript
// features/reservations/index.ts

export { startReservation } from
  "./application/startReservation";
```

Now compare an alternative:

```typescript
import {
  useReservationInternalStore
} from "@/features/reservations/model/internalStore";
```

The second approach reaches directly into another feature's implementation. Sometimes that's expedient. But if it becomes the normal pattern, the boundary loses its meaning.

Other features start depending on internal store shapes, helper functions, and incidental data structures.

A future refactor becomes difficult because every implementation detail has effectively become public.

This is the same principle behind encapsulation in object-oriented programming.

The internal implementation should be changeable without forcing unrelated consumers to change.

## 6.1 Dependency direction

Consider three features:

```text
Hotel Search
Reservations
Payments
```

A tempting design allows all three to import one another freely. That can produce cycles:

```text
Hotel Search ───► Reservations
      ▲                │
      │                ▼
      └──────────── Payments
```

Now the modules become difficult to understand independently.

Initialization order can become troublesome.

Testing requires constructing large portions of the application.

And business changes propagate through unexpected paths.

A cleaner approach might introduce an explicit checkout workflow that coordinates the relevant capabilities:

```text
        Checkout Workflow
         /      |       \
        ▼       ▼        ▼
     Search  Reservation  Payment
     Data     Capability  Capability
```

The exact boundaries depend on the product. Perhaps checkout belongs inside the reservations feature. Perhaps it's a separate substantial capability. The important point is that **cross-feature workflows should have an understandable owner**. They shouldn't emerge accidentally from a web of circular imports.

## 6.2 Don't extract everything into `shared`

Here's another common failure mode.

Developers begin with proper feature boundaries.

Then they encounter a function used by two features.

They move it into:

```text
shared/utils/
```

Another function follows. Then another. Eventually, `shared` contains half the business logic. This is not architectural improvement. It's the creation of a new miscellaneous dumping ground.

Shared infrastructure should generally contain concepts that are genuinely reusable without becoming coupled to one specific feature. Examples might include:

- General-purpose date formatting.
- HTTP client setup.
- Reusable accessible UI primitives.
- Generic validation helpers.

But `calculateReservationRefund()` is probably not a generic utility merely because two different pages call it.

It belongs to the business domain that owns the refund rule.

**Code reuse does not automatically justify moving business knowledge into a globally shared module.**

---

# 7. Composables, Stores, Services, and Utilities: Who Should Own What?

Vue's Composition API provides tremendous flexibility. Unfortunately, flexibility also makes it possible to place almost anything almost anywhere. Let's develop a practical distinction.

## 7.1 Composables: Reusable reactive behavior

A composable is a function that leverages Vue's Composition API to encapsulate reusable stateful behavior.

Consider:

```typescript
import { ref } from "vue";

export function useHotelSearch() {
  const hotels = ref<Hotel[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function search(city: string) {
    loading.value = true;
    error.value = null;

    try {
      hotels.value = await fetchHotels(city);
    } catch {
      error.value = "Search failed";
    } finally {
      loading.value = false;
    }
  }

  return {
    hotels,
    loading,
    error,
    search
  };
}
```

This is a reasonable composable for a modest search interface. It owns reactive behavior associated with a particular use case. But notice an important detail.

Every invocation of `useHotelSearch()` creates new refs.

That means two components calling it independently don't automatically share the same search state.

A composable is not inherently a global store.

Its state ownership depends on where the state is created.

If state is created inside the function, each invocation normally receives its own instance.

If reactive state is created in module scope, that state may be shared.

And sharing module-level mutable state introduces considerations for lifecycle, testing, and server-side rendering.

## 7.2 Pinia: State shared across application boundaries

Suppose many unrelated components need the selected display currency. The navigation bar displays it. Search results use it. The hotel details page uses it. The checkout page uses it. A Pinia store may be appropriate:

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";

export const useCurrencyStore = defineStore(
  "currency",
  () => {
    const selectedCurrency = ref("EUR");

    function setCurrency(currency: string) {
      selectedCurrency.value = currency;
    }

    return {
      selectedCurrency,
      setCurrency
    };
  }
);
```

Now components can access shared application state through a defined interface.

But there's a danger.

Once developers discover that Pinia makes sharing state convenient, they may put everything into global stores.

Every modal visibility flag. Every form input. Every temporary dropdown selection. Every loading spinner. The application develops an enormous collection of globally accessible mutable state. That's often unnecessary.

A good default principle is:

**Keep state as local as practical, and share it only as broadly as necessary.**

We'll examine state ownership and synchronization much more deeply in SE240-L03.

## 7.3 Services: Operations and external boundaries

The term *service* is overloaded. In frontend applications, it often refers to modules that perform operations such as:

```typescript
export const hotelApi = {
  async getById(id: string) {
    // HTTP request
  },

  async search(criteria: SearchCriteria) {
    // HTTP request
  }
};
```

This is an API service or adapter.

It provides a recognizable boundary around communication with another system.

Other services might coordinate application workflows without being directly responsible for HTTP.

But naming something `HotelService` doesn't automatically give it architectural meaning.

A 2,000-line class called `HotelService` can still be an architectural disaster.

Responsibilities matter more than suffixes.

## 7.4 Plain TypeScript functions: Often the best answer

Not everything needs to be reactive. Not everything needs a store. Not everything needs a composable. Consider:

```typescript
export function calculateNights(
  checkIn: string,
  checkOut: string
): number {
  // Pure date calculation.
}
```

If a function doesn't depend on Vue's lifecycle or reactivity, there may be no benefit to wrapping it in `useSomething()`.

Plain functions are easy to test, reuse, and reason about.

This is an underrated architectural advantage.

The less code depends directly on a framework, the easier it is to understand independently of that framework.

For a useful rule of thumb:

| Concern | Likely home |
|---|---|
| Dropdown open/closed state | Component |
| Reusable reactive behavior | Composable |
| State shared across unrelated views | Store |
| Hotel cancellation rule | Domain module |
| HTTP call to hotel API | API adapter |
| Formatting a currency value | Formatting utility |
| Multi-step booking interaction | Feature-level application logic |

These are starting points, not absolute laws.

Architecture requires judgment.

---

# 8. The Boundary Between Frontend Models and Backend Data

Suppose the backend returns:

```json
{
  "hotel_id": 4812,
  "nightly_price_minor": 14900,
  "currency_code": "EUR",
  "is_refundable": true
}
```

Your Vue components might prefer:

```typescript
interface Hotel {
  id: number;
  nightlyPrice: {
    amountCents: number;
    currency: string;
  };
  refundable: boolean;
}
```

Should every component understand the raw backend response format? Usually not. If backend serialization details leak across the entire frontend, changing those details becomes expensive. One approach is to define a mapping function:

```typescript
interface HotelDto {
  hotel_id: number;
  nightly_price_minor: number;
  currency_code: string;
  is_refundable: boolean;
}

interface Hotel {
  id: number;
  nightlyPrice: {
    amountCents: number;
    currency: string;
  };
  refundable: boolean;
}

function toHotel(dto: HotelDto): Hotel {
  return {
    id: dto.hotel_id,
    nightlyPrice: {
      amountCents: dto.nightly_price_minor,
      currency: dto.currency_code
    },
    refundable: dto.is_refundable
  };
}
```

Now most of the frontend works with its own model.

The API adapter understands the external representation.

This is an example of an **anti-corruption boundary**: translating an external system's concepts into the vocabulary used internally.

However, there's a trade-off. If your frontend and backend are developed together, use compatible models, and have straightforward contracts, creating an elaborate mapping layer for every DTO may add more bureaucracy than value. The purpose isn't to mechanically transform every property. The purpose is to avoid unnecessary dependence on unstable or unsuitable external representations. A good boundary earns its existence by insulating meaningful change.

---

# 9. Testability Is an Architectural Property

Consider a component that:

- Retrieves hotel details.
- Calculates discounts.
- Reads authentication state.
- Makes a reservation.
- Navigates to checkout.
- Displays errors.

How do you test its booking logic?

You might need to mount the Vue component, initialize Pinia, mock HTTP, configure a router, and reproduce a particular authentication state.

Even if the test passes, understanding why it passes can be difficult.

Now imagine the booking policy is represented by a pure function.

```typescript
interface BookingPolicy {
  cancellationDeadline: number;
  now: number;
  status: "pending" | "confirmed" | "cancelled";
}

export function canCancel(
  booking: BookingPolicy
): boolean {
  return (
    booking.status === "confirmed" &&
    booking.now < booking.cancellationDeadline
  );
}
```

Testing is straightforward:

```typescript
import { describe, expect, it } from "vitest";

describe("canCancel", () => {
  it("allows cancellation before deadline", () => {
    expect(
      canCancel({
        status: "confirmed",
        now: 100,
        cancellationDeadline: 200
      })
    ).toBe(true);
  });

  it("rejects cancelled bookings", () => {
    expect(
      canCancel({
        status: "cancelled",
        now: 100,
        cancellationDeadline: 200
      })
    ).toBe(false);
  });
});
```

The simplified policy assumes numeric timestamps and deliberately excludes other business constraints. In a real reservation system, a backend must remain authoritative. But the architectural point is that isolated business logic is easy to verify. This is not because the developer added tests afterward. It's because the design separates the rule from unrelated infrastructure.

## 9.1 Dependencies can be passed rather than imported

Suppose an application operation depends on an API.

You could import a global singleton directly.

Or you could make the dependency explicit:

```typescript
interface ReservationApi {
  create(input: ReservationInput):
    Promise<Reservation>;
}

export function createReservationWorkflow(
  api: ReservationApi
) {
  return {
    async submit(input: ReservationInput) {
      return api.create(input);
    }
  };
}
```

A production composition root can provide the real API implementation. A test can provide a fake. This is dependency injection in its simplest form. No decorator framework. No service container. No fifteen abstractions. Just a function receiving an object that provides the operations it needs.

Explicit dependencies make modules easier to test and understand. That doesn't mean every imported function should be injected. Injecting a deterministic date-formatting utility merely to satisfy an architectural ideology is usually pointless. Use dependency injection where substituting the implementation actually matters.

---

# 10. How Much Architecture Is Too Much?

We've spent much of the lecture discussing boundaries.

Now comes the necessary counterargument.

**Architecture can become its own source of complexity.**

Imagine a tiny Vue application with three pages. A developer introduces:

```text
presentation/
application/
domain/
infrastructure/
repositories/
factories/
interfaces/
adapters/
dependency-injection/
```

Every button click travels through four layers of indirection.

A simple HTTP request requires six files.

The system is technically organized but exhausting to navigate.

This isn't sophistication.

It's overengineering.

A healthy architecture should reduce cognitive load, not increase it.

## 10.1 The right amount of structure changes over time

Consider three stages of a product.

**Stage A — Small prototype**

A few pages, limited business logic, one or two developers. A simple `components`, `views`, `composables`, and `services` structure may be entirely sufficient.

**Stage B — Growing application**

Several substantial business capabilities, increasingly complex workflows, multiple developers.

Feature-based organization, clear state ownership, and separation of business rules begin providing meaningful value.

**Stage C — Mature SaaS product**

Dozens of developers, long-lived product areas, extensive integrations, complicated domain rules. More explicit module boundaries, public feature interfaces, contract testing, and architectural rules may be justified.

The mistake is assuming that every project should begin at Stage C.

Or that a Stage C application can remain maintainable forever using the accidental structure of Stage A.

Architecture should evolve with actual complexity.

## 10.2 A useful criterion: Cost of change

Rather than asking whether an architecture follows a particular pattern, ask:

> How difficult is it to implement a predictable business change without accidentally breaking unrelated behavior?

That's a much more practical measure of architecture quality. A few useful signals include:

- Changes frequently require editing unrelated features.
- Business rules are duplicated across multiple components.
- Internal implementation details are imported everywhere.
- Tests require initializing half the application.
- Circular dependencies keep appearing.
- Developers struggle to identify who owns particular behavior.

These are signs that clearer boundaries may be worth introducing. Conversely, if the application is small and understandable, adding more layers may create complexity without solving a real problem. The best architecture isn't the one with the most abstractions. It's the one whose abstractions correspond to genuine responsibilities.

---

# 11. Refactoring a Mess Without Rewriting the Application

Let's return to our hotel-booking application.

The pricing logic is scattered everywhere.

The components are tightly coupled.

The team is understandably tempted to announce: "We need to rewrite the frontend properly."

Be careful.

Large rewrites often exchange known problems for unknown problems while consuming enormous development capacity.

A more practical strategy is incremental.

## Step 1 — Identify the actual source of truth

Start with the pricing domain. Determine which system owns authoritative pricing. For hotel reservations, that's generally backend-side business logic, potentially incorporating supplier quotes, taxes, policies, and transactional validation. The frontend should not invent its own final booking price. Clarify which values are estimates, which are quoted, and which are confirmed. This gives the team a consistent conceptual model.

## Step 2 — Locate duplicated business knowledge

Search for pricing calculations across the frontend.

Identify which components independently apply discounts, taxes, or currency conversions.

Separate genuinely different calculations from accidental duplication.

Don't immediately extract everything into a giant pricing module.

First understand what the existing code is doing.

## Step 3 — Create a coherent feature boundary

Move the relevant pricing presentation and application logic into a recognizable area. For example:

```text
features/
└── pricing/
    ├── api/
    ├── model/
    ├── components/
    └── index.ts
```

This structure is illustrative.

The crucial result should be a stable interface other features can use.

## Step 4 — Migrate consumers gradually

Update one consumer at a time. Perhaps start with hotel details. Then search results. Then checkout. Each migration should preserve behavior and add useful tests. Avoid converting a small pricing refactor into a simultaneous redesign of authentication, routing, and payments. That's how supposedly modest architectural improvements become six-month adventures.

## Step 5 — Prevent the old coupling from returning

Once the feature has a clear public interface, discourage direct imports of its internal modules.

Tools such as ESLint import restrictions or module-boundary rules can help enforce architectural conventions.

But enforcement should reflect meaningful boundaries.

A rule that makes legitimate work miserable will eventually be bypassed.

The goal is to make the desired dependency structure the easiest structure to follow.

---

# 12. Practical Architecture Workshop

Let's design the frontend of a growing hotel-booking SaaS. It has these capabilities:

- Hotel search and filtering.
- Hotel details.
- Reservation creation and management.
- Payments.
- Authentication.
- Currency and localization preferences.
- Account settings.

There are four developers today, but the team may expand. The product is complex enough to justify some modularity, but not large enough to demand an elaborate enterprise architecture. A reasonable starting point:

```text
src/
├── app/
│   ├── main.ts
│   ├── router/
│   └── providers/
│
├── features/
│   ├── hotel-search/
│   ├── hotel-details/
│   ├── reservations/
│   ├── checkout/
│   ├── payments/
│   └── account/
│
├── shared/
│   ├── ui/
│   ├── http/
│   ├── formatting/
│   └── validation/
│
└── assets/
```

Authentication and preferences could be modeled as substantial features, shared application capabilities, or a combination, depending on how they're used.

The exact choice matters less than defining ownership clearly.

Now imagine a customer completes a booking. The checkout feature coordinates the process. It obtains the relevant reservation information through a defined interface. It interacts with the payment capability through an appropriate abstraction. It navigates to the confirmation view after receiving a successful authoritative outcome.

The payment component doesn't need to know how hotel searching works.

The hotel-search component doesn't need to know how payment processing is implemented.

The reservation domain doesn't need to import Vue components.

And the generic button component certainly doesn't need to import the authentication store.

That would be like teaching a kitchen spoon about international banking regulations.

There's no reason for the dependency to exist.

### One important architectural decision

Would you create a separate `pricing` feature? Maybe. If pricing is a substantial independent capability used across search, reservations, and checkout, a distinct module may be justified. But if pricing rules are inseparable from reservations and managed by one business domain, creating a separate feature could introduce unnecessary cross-feature dependencies. This is exactly why software architecture cannot be reduced to copying a fashionable directory tree from GitHub.

**The boundaries should reflect the product's actual responsibilities and patterns of change.**

---

# 13. Engineering and Interview Challenges

Try answering these before reading the discussion.

### Challenge 1 — The Universal Composable

A developer creates:

```typescript
useApplication()
```

It returns authentication state, current user information, selected currency, active booking, loading indicators, and API methods.

The developer argues:

"It's convenient. Every component can access everything from one place."

What's the architectural problem?

### Challenge 2 — The Feature Boundary

The hotel-search feature needs to display whether a customer qualifies for a loyalty discount.

Should it import the authentication store, inspect the user's subscription tier, and independently calculate eligibility?

What alternative would you consider?

### Challenge 3 — The Store Explosion

A team stores every modal's open/closed state in Pinia. There are eighty modals. Is this necessarily wrong? What factors determine whether such state should be local or shared?

### Challenge 4 — The Framework Rewrite

A mature Vue application has become difficult to maintain.

A developer proposes migrating everything to React because React has better architecture.

Evaluate the argument.

### Challenge 5 — The Dependency Puzzle

Two features import each other's internal stores. A third feature also imports both stores and modifies their state directly. What risks does this create? How might you restructure the interaction?

---

# 14. Solutions and Discussion

**Challenge 1**

The composable has become a global access point for unrelated application responsibilities. It hides dependencies, increases coupling, and makes every consumer potentially dependent on the entire application state model. A better approach would expose smaller, cohesive capabilities with clear ownership. Convenience is useful, but unrestricted access to everything becomes expensive as the application grows.

**Challenge 2**

Not necessarily.

If loyalty eligibility is a business rule, scattering that calculation across presentation components risks inconsistent behavior.

A pricing or loyalty capability could expose the appropriate eligibility information or estimated display price.

The exact interface depends on how the domain is organized.

The frontend must still defer to the backend's authoritative pricing and eligibility checks when performing consequential operations.

**Challenge 3**

Not automatically wrong, but probably unnecessary for many modals. A modal used entirely within one component can often own its visibility state locally. A globally accessible modal opened by unrelated parts of the application may justify shared state or a centralized modal service. The correct scope depends on who needs to read or modify the state and how long it must persist.

**Challenge 4**

React doesn't inherently solve coupling, unclear ownership, duplicated business rules, or poor dependency direction.

Those problems can exist in any frontend framework.

A rewrite might be justified for substantial independent reasons, but the architectural deficiencies should first be diagnosed directly.

Often the same improvements can be implemented incrementally in the existing Vue application at much lower cost and risk.

**Challenge 5**

The design creates hidden coupling, unclear ownership, and potentially circular dependencies. Changes to one feature may affect unrelated behavior. Testing becomes more difficult because modules depend on one another's internal state. A better design identifies which feature or application workflow owns the coordination. Other features interact through intentional public capabilities rather than modifying each other's internal stores. The goal is not to eliminate communication between features, but to make it explicit and controlled.

---

# 15. The Mental Model Worth Keeping

Frontend architecture isn't fundamentally about components, folders, or state-management libraries.

It's about controlling complexity as the application changes.

The most important principles are:

**Cohesion:** Related responsibilities should have a recognizable home.

**Coupling:** Unrelated modules should not depend unnecessarily on each other's implementation details.

**Ownership:** Important business rules and mutable state should have clear owners.

**Boundaries:** Features should expose intentional interfaces rather than their entire internal structure.

**Dependency direction:** High-level product logic should not become unnecessarily entangled with incidental implementation mechanisms.

**Proportionality:** Architectural structure should solve real complexity, not manufacture additional complexity.

And perhaps the most useful practical principle:

**A good architecture makes reasonable future changes reasonably easy.**

Not every change. Not every possible future. But the changes the product is likely to experience. If adding a 10% loyalty discount requires modifying twelve unrelated components and five global stores, the architecture is telling you something. Listen to it.

---

# 16. Next Session — State Management and Reactive Applications

We've discussed where responsibilities should live.

But there's a particularly difficult category of responsibility we haven't explored in depth.

**State.**

Imagine a customer opening a hotel-booking page. The frontend displays:

```text
Available rooms: 1
```

The customer clicks Reserve.

The button becomes disabled, and the application optimistically displays:

```text
Reservation confirmed!
```

But the server rejects the operation because another customer booked the room moments earlier. Meanwhile, an earlier availability request finishes and updates the interface with outdated information. The UI now displays three mutually contradictory states. The application is technically reactive. Every component updates correctly when its dependencies change. Yet the overall system is wrong.

How can reactive code produce inconsistent user experiences? When should data live in a component, a composable, a Pinia store, or a server-state cache? How do you deal with stale requests, race conditions, optimistic updates, and state that changes independently on the backend?

In **SE240-L03 — State Management and Reactive Applications**, we'll investigate these problems and discover why keeping the UI synchronized with reality is much harder than making values reactive.

---


---

## Next Lecture — SE240-L03: State Management and Reactive Applications

Continue in **SE240 — Browser and Frontend Engineering**.

## Further Reading — Optional References

1. [Vue — State Management](https://vuejs.org/guide/scaling-up/state-management.html) — State ownership, shared state, and Pinia.
2. [Vue — Composables](https://vuejs.org/guide/reusability/composables.html) — Encapsulating reusable stateful behavior.
3. [Vue — Component Props](https://vuejs.org/guide/components/props.html) — One-way data flow and component contracts.
4. [Vue — Provide / Inject](https://vuejs.org/guide/components/provide-inject.html) — Passing dependencies through component trees.
5. [Pinia — Core Concepts](https://pinia.vuejs.org/core-concepts/) — Store definitions and application-wide state.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE240-L02  FRONTEND ARCHITECTURE BEYOND COMPONENTS — INTERVIEW GLANCE CARD

OPENING FAILURE
  Loyalty 10%         Same price calculated in many places → conflicting €370 / €333
  Knowledge dup       Several modules believe they own the same rule
  Bad “fix”         Giant useHotelPricing() still mixes stores, APIs, routes, notifications
  Root question       Who is responsible for what?

COMPONENTS ≠ ARCHITECTURE
  Component tree      Visual composition
  Architecture        Responsibilities + dependencies
  Trap                Many components each coordinate the same business process independently

COUPLING & COHESION
  Coupling            How strongly modules depend; change propagation is the smell
  Cohesion            Related work shares a meaningful purpose (e.g. booking-pricing/)
  Change test         New cancellation policy → one identifiable area vs 30 scattered conditions

FOUR RESPONSIBILITIES (not mandatory folders)
  Presentation        What user sees; format/display — don't invent business meaning of data
  Application         Orchestrate workflows (validate → submit → navigate)
  Domain              Business rules as plain TS when possible; independent of Vue/Pinia/HTTP
  Infrastructure      HTTP/API adapters; don't leak into pricing or card styling
  Security note       Frontend domain = estimated UX; backend owns authoritative price

FEATURE vs TECHNICAL FOLDERS
  By type             components/, stores/, utils/ — hard to find a capability
  By feature          features/hotel-search|reservations|payments + shared/
  Vertical slice      Group by business capability
  Folders alone fail  Cross-feature imports of each other's stores = still tightly coupled

PUBLIC INTERFACES
  Depend on           features/reservations public API (index.ts), not internalStore
  Encapsulation       Internals changeable without forcing every consumer to change
  Dependency direction  Avoid cycles Search↔Reservations↔Payments
  Workflow owner      Explicit checkout (or similar) coordinates capabilities
  shared/ trap        Don't dump business rules into shared/utils because two pages call them
  Rule                Code reuse ≠ move business knowledge into a global dumping ground

WHO OWNS WHAT
  Composable          Reusable reactive behavior; new refs per call unless module-scoped share
  Pinia               Shared client state across unrelated views (e.g. currency)
  Default             Keep state as local as practical; share only as broadly as needed
  Service / adapter   External operations (HTTP); suffix ≠ architecture
  Plain functions     Best for non-reactive pure logic (nights, canCancel, discount math)

FRONTEND MODEL vs BACKEND DTO
  Anti-corruption     toHotel(dto) maps snake_case / external shape → internal Hotel
  Trade-off           Elaborate mapping only when it insulates real change

TESTABILITY
  Fat component       Hard: mount + Pinia + HTTP + router + auth
  Pure domain fn      Easy unit tests; design separates rule from infrastructure
  DI light            Pass ReservationApi into workflow; inject where substitution matters

HOW MUCH ARCHITECTURE?
  Overengineering     Four layers per button click for a tiny app
  Evolve              Prototype → growing features → mature SaaS boundaries
  Quality metric      Cost of a predictable business change without collateral damage
  Smell signals       Unrelated edits, duplicated rules, internal imports everywhere,
                      half-app tests, cycles, unclear ownership

INCREMENTAL REFACTOR
  1 Source of truth   Backend authoritative pricing; clarify estimate vs quote vs confirmed
  2 Find duplication  Don't extract blindly
  3 Feature boundary  Stable public interface
  4 Migrate gradually One consumer at a time
  5 Enforce           Lint/import rules for meaningful boundaries only

MENTAL MODEL
  Cohesion · Coupling · Ownership · Boundaries · Dependency direction · Proportionality
  Good architecture makes likely future changes reasonably easy.

SENIOR LINE: Architecture starts with responsibilities—not folder names or Pinia vs X.
```

