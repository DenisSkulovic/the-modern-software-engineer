---
id: SE240-L03
course: SE240
title: "State Management and Reactive Applications"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S06]
prev: SE240-L02
next: SE240-L04
---




# SE240 — Browser and Frontend Engineering

## Lecture 03: State Management and Reactive Applications

*How an application can update everything perfectly—and still display information that is completely wrong.*

---

# 1. The Hotel Room That Was Available, Unavailable, and Booked at the Same Time

It's a busy Friday evening at your hotel-booking platform.

A customer searches for hotels in Berlin.

The application displays a particularly attractive room:

**Hotel Alexander — Deluxe Room — €149 — 1 room remaining.**

The customer clicks Reserve.

Your Vue application immediately displays a cheerful confirmation:

> Reservation successful!

Except the reservation wasn't successful.

Another customer booked the final room a fraction of a second earlier.

The backend correctly rejected the operation.

Unfortunately, your frontend already updated its local reservation state.

Now the UI needs to undo its enthusiastic announcement.

Meanwhile, something even stranger happens.

An older availability request completes after the failed reservation attempt.

Its response says:

```json
{
  "roomId": 73,
  "availableRooms": 1
}
```

The frontend obediently processes it.

The room becomes available again.

The customer clicks Reserve a second time.

Another failure.

And somewhere in the middle of all this, your application is maintaining several state variables:

```typescript
isAvailable = true
isReserved = false
isLoading = false
reservationFailed = true
```

Each variable is technically valid JavaScript.

Vue is correctly tracking and rendering every change.

There is no framework bug.

**The application is reactive, but its understanding of reality is inconsistent.**

This is the central difficulty of state management.

Reactivity answers:

> When data changes, how does the interface update?

State management must answer something much harder:

> Which data should exist, who owns it, when is it trustworthy, and what happens when multiple sources disagree?

The difference is enormous.

Let's investigate.

---

# 2. Reactivity: The Beautiful Machinery Underneath

We already explored JavaScript execution and the browser's event loop in the computer science foundations courses (CS110, CS220, CS320) and SE240 SE240-L01. Now we'll focus specifically on Vue's reactive model.

Consider:

```typescript
import { ref, computed } from "vue";

const nightlyPrice = ref(150);
const nights = ref(3);

const totalPrice = computed(
  () => nightlyPrice.value * nights.value
);
```

Initially:

```text
Nightly price: €150
Nights:        3
Total:         €450
```

Now execute:

```typescript
nights.value = 4;
```

The computed total becomes €600. You didn't manually update `totalPrice`, and you didn't call a function telling Vue to refresh the interface. Vue knows that `totalPrice` depends on `nights`.

How?

## 2.1 Dependency tracking

At a conceptual level, Vue maintains relationships between reactive data and computations that consume it. When a computed getter executes:

```typescript
() => nightlyPrice.value * nights.value
```

Vue tracks which reactive values were accessed. A simplified dependency graph might look like:

```text
nightlyPrice ──┐
               ├──► totalPrice ──► UI rendering
nights ────────┘
```

When `nights.value` changes, Vue can invalidate the computed result. The next time it's needed, the getter can recalculate its value. Computed properties cache their results until their reactive dependencies require reevaluation, which is an important distinction from calling an ordinary function on every render.

Underneath, Vue's reactivity system uses mechanisms involving tracked reads and writes. For `reactive()` objects, JavaScript proxies can intercept property access and modification. For `ref()` values, Vue manages dependency tracking around access to the `.value` property. The implementation is considerably more sophisticated, but that's the useful model: Vue maintains a graph of reactive dependencies and uses it to propagate changes.

## 2.2 `ref()` versus `reactive()`

Both are useful.

```typescript
const searchCity = ref("Berlin");
```

A `ref` wraps a value in a reactive container. For an object:

```typescript
const filters = reactive({
  city: "Berlin",
  guests: 2,
  refundableOnly: false
});
```

Vue provides reactive property access through a proxy. The choice often comes down to ergonomics, replacement behavior, and how the state is consumed. For example, directly destructuring primitive properties from a reactive object can lose the original reactive connection:

```typescript
const filters = reactive({
  city: "Berlin"
});

const { city } = filters;
```

Here, `city` is an ordinary string value, not a reactive reference to `filters.city`. Utilities such as `toRefs()` can preserve reactivity when destructuring is needed.

But the more interesting issue isn't which API you choose. It's deciding what information should be stored as state in the first place.

---

# 3. Derived State: Don't Store What You Can Calculate

Suppose your reservation form stores:

```typescript
const nightlyPrice = ref(150);
const nights = ref(3);
const totalPrice = ref(450);
```

Every time `nights` changes, you manually update `totalPrice`. Perhaps you use a watcher:

```typescript
watch(nights, () => {
  totalPrice.value =
    nightlyPrice.value * nights.value;
});
```

Now imagine the nightly price changes. Oops. The watcher only reacts to changes in `nights`, so you add another watcher. Later, a loyalty discount appears: another watcher. Then taxes: another one.

Soon the application contains a network of synchronization rules attempting to keep several redundant values consistent. This is a familiar failure mode.

**You've stored information that could have been derived from other information.**

A better approach:

```typescript
const nightlyPrice = ref(150);
const nights = ref(3);
const discountPercent = ref(10);

const subtotal = computed(
  () => nightlyPrice.value * nights.value
);

const discountedTotal = computed(
  () => subtotal.value * (1 - discountPercent.value / 100)
);
```

Now the dependency graph explains the relationships.

```text
nightlyPrice ──┐
               ├──► subtotal ──┐
nights ────────┘               ├──► discountedTotal
discountPercent ───────────────┘
```

There's no need to manually synchronize the result. This is a powerful general rule:

> Store the smallest useful set of independent facts. Derive the rest whenever practical.

There are exceptions. Expensive calculations may need memoization or other optimization. Sometimes a user is editing a provisional copy of a value that differs from its committed value. And real financial calculations require explicit rounding and currency rules. But unnecessary duplication of mutable state is one of the easiest ways to manufacture bugs.

## 3.1 Computed properties are for calculations, not orchestration

Consider this questionable code:

```typescript
const hotels = computed(async () => {
  return await fetchHotels(filters.value);
});
```

Now `hotels` contains a computed promise rather than automatically becoming a properly managed asynchronous resource. You still need to handle loading, errors, request races, and lifecycle behavior.

Computed getters are best used for synchronous derived values. For external side effects, Vue provides watchers and related APIs. And for substantial server-data management, specialized query libraries may be preferable. That brings us to an important distinction.

---

# 4. Not All State Is the Same Kind of State

Imagine opening the hotel search page. It contains:

- The currently selected city.
- Whether the filter dropdown is open.
- The hotel search results.
- The currently authenticated user.
- The selected currency.
- The search results sorted by price.
- A reservation request currently awaiting confirmation.

All of these are state. But treating them as one homogeneous collection of values is a mistake, because they have different owners, lifetimes, and consistency requirements.

A useful classification:

| Kind of state | Example | Natural owner |
|---|---|---|
| Local UI state | Dropdown open/closed | Component |
| Navigation state | City, dates, filters | Often URL/router |
| Shared client state | Selected currency | Shared store |
| Derived state | Sorted hotel results | Computed value |
| Server state | Room availability | Backend, locally cached |
| Workflow state | Booking pending/failed/confirmed | Feature-level operation |

The table isn't a rigid architectural specification. It's a way of asking better questions.

## 4.1 Local state

Consider:

```typescript
const isFilterPanelOpen = ref(false);
```

Only the filter panel needs this value. Putting it in a global Pinia store would usually be unnecessary. The component owns the interaction, and its state can disappear when the component is destroyed. That's perfectly fine.

## 4.2 Navigation state

Suppose the user searches:

```text
City: Berlin
Guests: 2
Check-in: November 10
Check-out: November 13
```

Wouldn't it be useful if the URL preserved those choices? For example:

```text
/search?city=Berlin&guests=2&checkIn=2026-11-10&checkOut=2026-11-13
```

Now the customer can bookmark the search or share it. The Back button can restore a previous search. Reloading doesn't necessarily discard the context.

This suggests that the URL is often a natural home for shareable navigation state. Not every temporary input needs to be synchronized to the URL. But if a value defines which resource or view the user is looking at, putting it exclusively inside an ephemeral store may be a poor decision.

## 4.3 Shared client state

The selected display currency might be relevant across many features. A Pinia store is a reasonable owner:

```typescript
export const usePreferencesStore = defineStore(
  "preferences",
  () => {
    const currency = ref("EUR");

    function selectCurrency(value: string) {
      currency.value = value;
    }

    return { currency, selectCurrency };
  }
);
```

This is state controlled by the client. The application can make a local change immediately. Whether it also persists that preference to a backend is a separate concern.

## 4.4 Server state

Now consider:

```typescript
const availableRooms = ref(1);
```

Where does the true value live? Not in the Vue application. The actual availability depends on reservations, cancellations, inventory rules, and potentially external hotel systems. The backend is responsible for determining the authoritative state, and the frontend possesses only a **snapshot** of that state.

And snapshots become outdated.

This is the fundamental difference between ordinary client state and server state. Client state is often something your application can directly control. Server state is information your application has obtained from a remote system that may change independently.

That distinction changes everything.

---

# 5. Server State: Your Frontend Is Living in the Past

Let's examine the availability problem. At 12:00:00, the backend reports:

```text
Available rooms: 1
```

Your frontend receives the response at 12:00:00.100. At 12:00:01, another customer books the room, and the backend now reports:

```text
Available rooms: 0
```

But your frontend still displays:

```text
Available rooms: 1
```

Has Vue failed? No. The local state accurately reflects the last information the application received. The problem is that the world changed after that information was obtained.

This is unavoidable in distributed systems. Unless the frontend has a suitable communication mechanism, it cannot instantly know about arbitrary changes occurring elsewhere. Even with WebSockets, there are propagation delays, network failures, and reconnection scenarios. The frontend's local view of server state is always subject to some freshness limitation.

## 5.1 Freshness is a policy decision

Different kinds of data tolerate different levels of staleness. Consider:

**Country names** rarely change, so caching for a long period is usually reasonable.

**Hotel photographs** change occasionally, so moderately long caching can be useful.

**Hotel search results** have prices and availability that may change frequently, so shorter freshness windows may be appropriate.

**Final reservation availability** needs authoritative validation when the booking is committed.

The last case is especially important. Even a response fetched 100 milliseconds ago cannot guarantee that inventory remains available now, because another customer could book the room immediately afterward. Therefore, no amount of frontend refetching replaces correct backend concurrency control.

This leads to a useful separation:

**The frontend optimizes how accurately and conveniently information is presented.**

**The backend enforces which state transitions are actually permitted.**

An availability badge helps the customer decide what to attempt. A transactional reservation workflow determines whether the booking actually succeeds.

---

# 6. The Race Condition: When Yesterday's Answer Arrives Tomorrow

Now let's investigate a different problem.

A customer types into a city search field.

The application sends a request for every completed search term.

At first:

```text
Search: Berlin
```

Then the customer changes it to:

```text
Search: Hamburg
```

Two requests are in flight.

The Berlin request starts first.

The Hamburg request starts second.

Naturally, you'd expect Berlin to finish first.

Except networks don't guarantee that.

Imagine:

```text
Time       Request A: Berlin        Request B: Hamburg

0 ms       Starts
50 ms                               Starts
100 ms                              Completes
110 ms                              UI shows Hamburg
350 ms     Completes
360 ms     UI shows Berlin
```

The customer selected Hamburg.

The frontend displays Berlin.

No server malfunctioned.

No response was invalid.

The requests simply completed in a different order from the order in which they were initiated.

This is an **asynchronous race condition**.

## 6.1 The naive implementation

Consider:

```typescript
watch(searchCity, async city => {
  hotels.value = await fetchHotels(city);
});
```

It looks perfectly reasonable.

Whenever the city changes, fetch hotels.

But each invocation runs independently.

An older request can finish after a newer one and overwrite the latest results.

The watcher responds correctly to changes.

The overall system is incorrect because it doesn't account for concurrent operations.

## 6.2 One solution: Ignore outdated responses

We can associate requests with a monotonically increasing generation number.

```typescript
let latestRequest = 0;

watch(searchCity, async city => {
  const requestId = ++latestRequest;

  const result = await fetchHotels(city);

  if (requestId !== latestRequest) {
    return;
  }

  hotels.value = result;
});
```

When a request completes, it checks whether it's still the latest one.

If a newer request has started, the old result is discarded.

This implements a **latest-request-wins** policy.

It doesn't cancel the earlier network request.

It merely prevents that request from overwriting newer state.

The example also omits loading and error handling for clarity; those need the same stale-request protection.

## 6.3 Another solution: Cancel obsolete work

Vue supports watcher cleanup.

We can use `AbortController` to cancel a previous fetch when the search value changes.

```typescript
const hotels = ref<Hotel[]>([]);
const searchCity = ref("Berlin");
const status = ref<"idle" | "loading" | "success" | "error">("idle");

watch(
  searchCity,
  async (city, _oldCity, onCleanup) => {
    const controller = new AbortController();
    let active = true;

    onCleanup(() => {
      active = false;
      controller.abort();
    });

    status.value = "loading";
    hotels.value = [];

    try {
      const response = await fetch(
        `/api/hotels?city=${encodeURIComponent(city)}`,
        { signal: controller.signal }
      );

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const result = await response.json();

      if (!active) return;

      hotels.value = result.hotels;
      status.value = "success";
    } catch {
      if (!active) return;

      status.value = "error";
    }
  },
  { immediate: true }
);
```

When Vue invalidates the watcher because `searchCity` changes, the cleanup runs.

The earlier fetch is aborted if possible.

The `active` flag also prevents obsolete executions from updating the interface after invalidation.

Vue 3.5 introduced a separate `onWatcherCleanup()` API. The callback-based `onCleanup` approach shown above is broadly useful and avoids some of that newer API's synchronous-registration restrictions.

### An important qualification

Aborting a client request doesn't guarantee that the server stopped processing it.

Perhaps the server already executed a database query.

Perhaps it already committed a reservation.

Cancellation is useful for managing client resources and preventing obsolete responses from updating the UI.

It's not a business-level rollback mechanism.

That distinction becomes crucial when working with payments, reservations, and other consequential operations.

---

# 7. Loading, Error, and Success Are States—Not Random Booleans

Let's return to our reservation interface. Suppose we represent its workflow using:

```typescript
const isLoading = ref(false);
const isSuccessful = ref(false);
const hasError = ref(false);
```

Three booleans create eight possible combinations. Some are sensible. Others are contradictory. For example:

```text
isLoading:    true
isSuccessful: true
hasError:     true
```

What does that mean? Is the operation loading? Did it succeed? Did it fail? Technically, all three values can be true. But perhaps the actual workflow should allow only one of several distinct states.

A better model:

```typescript
type BookingStatus =
  | "idle"
  | "submitting"
  | "confirmed"
  | "failed";

const bookingStatus = ref<BookingStatus>("idle");
```

Now the application has a clearer vocabulary.

```text
idle
  │
  ▼
submitting
  │
  ├────────► confirmed
  │
  └────────► failed
                │
                └────────► submitting (retry)
```

This is the beginning of a **state machine**. A state machine defines valid states and transitions between them. The advantage isn't merely fewer variables; it's that the model excludes impossible combinations.

## 7.1 Make state transitions explicit

Imagine a reservation workflow:

```typescript
type BookingState =
  | { status: "idle" }
  | { status: "submitting"; attemptId: string }
  | { status: "confirmed"; reservationId: string }
  | { status: "failed"; message: string };
```

This uses a discriminated union, where the different variants carry different information. A confirmed state necessarily includes a reservation identifier. A failed state includes an error message. An idle state doesn't pretend to have either. TypeScript can help ensure the UI handles the possibilities.

For example:

```typescript
function getStatusText(state: BookingState): string {
  switch (state.status) {
    case "idle":
      return "Ready to book";

    case "submitting":
      return "Submitting reservation...";

    case "confirmed":
      return `Confirmed: ${state.reservationId}`;

    case "failed":
      return state.message;
  }
}
```

This kind of modeling becomes increasingly valuable as workflows gain more states. A payment flow might distinguish:

```text
idle
creating-payment
awaiting-customer-action
processing
succeeded
failed
```

A hotel reservation might distinguish a temporary hold from a fully confirmed booking. The correct states depend on the business domain. The principle is that the application should explicitly represent meaningful workflow conditions instead of reconstructing them from loosely related booleans.

---

# 8. Optimistic Updates: Making the UI Faster Than Reality

Now comes one of the most interesting frontend design choices.

Suppose a customer clicks a button to add a hotel to their favorites.

The API request takes 180 milliseconds.

We have two choices.

**Pessimistic update:**

Wait for the server to confirm the action, then update the UI.

**Optimistic update:**

Update the UI immediately, assuming the operation will succeed.

If it fails, undo the local change.

For something like favoriting a hotel, optimistic behavior can feel excellent.

The heart icon fills instantly.

The server request proceeds in the background.

Most of the time, everything works.

But there's a hidden contract.

**The frontend is temporarily displaying a state that the backend has not yet confirmed.**

That's acceptable for some interactions and dangerous for others.

## 8.1 A simple optimistic interaction

Imagine:

```typescript
async function addFavorite(hotelId: string) {
  const wasFavorite = favorites.value.includes(hotelId);

  if (!wasFavorite) {
    favorites.value = [...favorites.value, hotelId];
  }

  try {
    await favoriteApi.add(hotelId);
  } catch {
    if (!wasFavorite) {
      favorites.value = favorites.value.filter(
        id => id !== hotelId
      );
    }
  }
}
```

This illustrates the basic pattern.

Update locally.

Perform the operation.

Restore the previous state if the operation fails.

However, the implementation has a limitation.

What if the user rapidly adds and removes the same hotel while requests overlap?

A rollback from one failed request might overwrite a newer successful interaction.

Real optimistic updates must account for concurrent mutations, overlapping requests, and the authoritative final state.

## 8.2 Not every operation should appear successful immediately

Let's compare two interactions.

**Adding a hotel to favorites**

Low consequence.

Often reversible.

Optimistic feedback is reasonable.

**Confirming a €2,000 hotel reservation**

High consequence.

Potentially involves external availability, payments, cancellation policies, and legally meaningful commitments.

The UI should not announce a confirmed reservation before receiving an authoritative confirmation.

It can immediately respond:

```text
Submitting reservation...
```

That provides fast feedback without making a false claim.

Then, after success:

```text
Reservation confirmed!
```

If the request times out, the outcome may be uncertain.

In that case, the client may need to check the booking status using an operation identifier rather than simply displaying failure or creating another booking.

This leads to a particularly useful distinction:

**Optimistic feedback is not the same as optimistic business truth.**

You can make an interface feel responsive without lying about whether a consequential operation succeeded.

---

# 9. Server-State Libraries: Why Pinia Alone May Not Be Enough

Suppose your application contains twenty different API queries.

For each query, you manually maintain:

```typescript
const data = ref(null);
const loading = ref(false);
const error = ref(null);
```

Then you implement:

- Fetching.
- Retries.
- Refetching.
- Caching.
- Cache expiration.
- Request deduplication.
- Stale response handling.
- Loading and error states.
- Refreshing after mutations.

Soon you've built a homemade server-state management library.

Possibly an unreliable one.

This is where tools such as **TanStack Query for Vue** become interesting.

The idea is to distinguish two fundamentally different responsibilities.

Pinia is well suited to managing client-owned application state.

A server-state library specializes in managing remotely sourced data and its lifecycle.

They can coexist.

## 9.1 Queries are identified by keys

Imagine fetching hotels:

```typescript
import { useQuery } from "@tanstack/vue-query";

const city = ref("Berlin");

const hotelQuery = useQuery({
  queryKey: ["hotels", city],
  queryFn: () => fetchHotels(city.value),
  staleTime: 30_000
});
```

The query key identifies the requested dataset.

Conceptually:

```text
["hotels", "Berlin"]
```

is different from:

```text
["hotels", "Hamburg"]
```

The library can cache them separately.

When the reactive `city` reference changes, the query key changes, allowing the library to manage the corresponding query.

For a real application, every parameter affecting the result must be reflected in the cache identity, including relevant filters, dates, or currency when those alter the returned data.

Otherwise, distinct requests can incorrectly share cached results.

## 9.2 Fresh versus stale

The `staleTime` option specifies how long fetched query data should be considered fresh.

In our example:

```typescript
staleTime: 30_000
```

means 30 seconds.

But be careful.

**Fresh does not mean guaranteed correct.**

It means the client-side caching policy considers the data sufficiently recent.

The backend might change its state one millisecond after the fetch.

The client can still consider the cached data fresh for the configured period.

That's a policy decision, not a distributed consistency guarantee.

By default, TanStack Query generally considers cached query data stale immediately unless a different freshness policy is configured.

Stale data can still be displayed while a background refetch obtains newer information.

That is often desirable.

A user may prefer seeing slightly outdated search results rather than a blank screen every time a page regains focus.

But for certain operations, the application must explicitly require authoritative validation.

## 9.3 Invalidation after a mutation

Suppose a customer successfully adds a hotel to their favorites.

Other components displaying favorite hotels may now have outdated cached data.

A mutation handler can invalidate the relevant query:

```typescript
await queryClient.invalidateQueries({
  queryKey: ["favorites"]
});
```

This marks matching cached queries as stale and can trigger refetching of active queries.

The application doesn't need to manually locate every component displaying favorites and tell it to reload.

That reduces synchronization work.

However, invalidation is not instant global consistency.

It initiates or schedules the process of obtaining updated information according to the library's behavior.

Other tabs, devices, and clients have their own state.

And any display updated optimistically before confirmation still needs careful failure handling.

## 9.4 Should every application use a server-state library?

No.

A small Vue application with a handful of simple API requests may not need one.

But as fetching, caching, and synchronization requirements grow, manually managing all those concerns through general-purpose stores can become expensive.

A useful division might be:

```text
Vue component state
    └── Local UI interactions

Pinia
    └── Shared client-owned preferences and workflows

TanStack Query
    └── Cached server data, fetching, invalidation

Backend
    └── Authoritative business state
```

These aren't perfectly isolated categories.

For example, a workflow may coordinate both a Pinia store and query mutations.

But the distinction helps prevent the accidental creation of several conflicting sources of truth.

---

# 10. The Multiple-Tab Problem

Let's complicate matters. The same customer opens your application in two browser tabs. In Tab A, they update their profile name. In Tab B, they still see the old name.

Why?

Because each tab may have its own JavaScript runtime and in-memory application state. Updating a Pinia store in one tab doesn't automatically update every other tab. Even if both tabs use the same server-state library, ordinary in-memory query caches are not necessarily shared. The backend can now contain the correct profile name while one browser tab displays an older snapshot.

## 10.1 Strategies for synchronization

Several mechanisms can help, depending on the requirements.

**Refetching on focus.** When the user returns to a tab, the application may refresh stale data. This is simple and often sufficient.

**Polling.** The application periodically requests newer state. For example, an operations dashboard might refresh every 15 seconds. Polling is straightforward but creates repeated requests, even when nothing has changed.

**WebSockets or Server-Sent Events.** The backend can push updates to connected clients. Useful for chat, operational dashboards, and certain live applications. But connections can fail, clients can disconnect, and events can be missed unless the system provides appropriate recovery mechanisms.

**BroadcastChannel.** Browser tabs from the same origin can communicate through the `BroadcastChannel` API. This is useful for propagating events such as preference changes or logout notifications between tabs. However, it doesn't make remote backend state automatically consistent.

Each mechanism solves a different part of the synchronization problem. Real-time systems are rarely solved by merely introducing WebSockets. They also need to consider ordering, reconnection, missed updates, and how clients recover the current authoritative state.

---

# 11. Putting It Together: A Safer Booking Interface

Let's redesign the interface from our opening mystery. The user is viewing a room with one unit apparently available, and our system needs to distinguish several things.

First, the displayed availability is a snapshot. Second, the customer initiating a booking is not equivalent to a successful reservation. Third, concurrent requests must not overwrite newer state. Fourth, failure and uncertainty need explicit representation.

A possible state model:

```typescript
type ReservationState =
  | { status: "idle" }
  | { status: "submitting"; attemptId: string }
  | { status: "confirmed"; reservationId: string }
  | { status: "rejected"; reason: string }
  | { status: "unknown"; attemptId: string };
```

Why introduce `unknown`? Because distributed operations can have uncertain outcomes. If a reservation request times out after the server may have committed it, the frontend should not automatically assume that nothing happened. It can use the original attempt identifier to retrieve or reconcile the operation's authoritative status.

Now imagine the booking flow:

```text
Customer clicks Reserve
           │
           ▼
     SUBMITTING
           │
           ├── Server confirms
           │        │
           │        ▼
           │     CONFIRMED
           │
           ├── Server rejects
           │        │
           │        ▼
           │      REJECTED
           │
           └── Network outcome uncertain
                    │
                    ▼
                  UNKNOWN
                    │
                    ▼
          Query authoritative status
                    │
              Resolve outcome
```

The frontend should also ensure that stale search or availability responses don't overwrite the active reservation workflow. A previous availability response saying "one room remaining" is not proof that the customer can still book it. The final decision belongs to backend business logic protected by appropriate concurrency guarantees.

The frontend can display:

> Availability may have changed. Checking your reservation...

That's less theatrically satisfying than immediately announcing success. But it's accurate. And accuracy is considerably more attractive than charging someone twice for a hotel room.

---

# 12. Practical Investigation

Let's perform two small experiments.

## Experiment A — Reproduce an asynchronous race

Open your browser console and execute:

```javascript
function fakeSearch(city, delay) {
  return new Promise(resolve => {
    setTimeout(() => resolve(city), delay);
  });
}

async function search(city, delay) {
  const result = await fakeSearch(city, delay);
  console.log("Displaying:", result);
}

search("Berlin", 500);
search("Hamburg", 100);
```

The Hamburg result appears first. Then Berlin appears. Imagine replacing `console.log()` with:

```javascript
hotels.value = result;
```

You've recreated the race condition. Now introduce a generation counter:

```javascript
let latest = 0;

async function safeSearch(city, delay) {
  const id = ++latest;
  const result = await fakeSearch(city, delay);

  if (id !== latest) return;

  console.log("Displaying:", result);
}

safeSearch("Berlin", 500);
safeSearch("Hamburg", 100);
```

Only the latest requested search is displayed. It's a tiny experiment that demonstrates an extremely common production problem.

## Experiment B — Inspect reactive dependencies

In a small Vue component, create:

```typescript
const price = ref(100);
const nights = ref(2);

const total = computed(() => {
  console.log("Recalculating total");
  return price.value * nights.value;
});
```

Read `total.value` several times. Notice that Vue doesn't need to recalculate it every time when its dependencies are unchanged. Then modify `nights.value` and read the total again. The computed getter reevaluates because a dependency changed. Now consider how much unnecessary synchronization code this mechanism eliminates.

### Optional extension

Create a component that fetches data whenever a search term changes. Use a delayed mock fetch to force responses to arrive out of order. Then fix the implementation using watcher cleanup or a request-generation counter. This is a worthwhile exercise because it resembles problems you'll eventually encounter in real applications.

---

# 13. Engineering and Interview Challenges

### Challenge 1 — The Stale Search

A user searches for Berlin, then Hamburg. The Berlin request finishes last and replaces the Hamburg results.

What caused the bug?

What two different mechanisms could prevent it?

### Challenge 2 — The Global State Temptation

A developer proposes putting the following into one Pinia store:

- Search filters.
- Dropdown visibility.
- Current user.
- Hotel API results.
- Selected currency.
- Booking request status.

Is this necessarily incorrect?

How would you improve the ownership model?

### Challenge 3 — The Optimistic Payment

A team wants to display "Payment successful!" immediately after the customer clicks Pay, before receiving any response. Their argument is that optimistic UIs improve perceived performance.

Is the design reasonable?

What could the UI display instead?

### Challenge 4 — The Freshness Guarantee

Your frontend fetches room availability every five seconds.

Can you now guarantee that a room displayed as available can be booked successfully?

Why or why not?

### Challenge 5 — The Timeout Mystery

A customer submits a reservation request. The connection times out. The frontend doesn't know whether the backend committed the reservation.

Which state should the application represent?

What mechanisms help resolve the uncertainty?

---

# 14. Solutions and Discussion

**Challenge 1**

The bug results from overlapping asynchronous operations completing out of order. One solution is to use a request-generation identifier and ignore results from older requests. Another is to cancel obsolete requests using `AbortController` and watcher cleanup, while guarding against stale continuations. For a larger application, a server-state library can manage much of the query lifecycle.

**Challenge 2**

The design isn't automatically incorrect, but it combines concerns with very different ownership and lifecycle requirements. Dropdown visibility probably belongs in a component. Shareable search parameters may belong in the URL. Selected currency is a reasonable candidate for shared client state. Server-fetched hotel results may be better managed by a query cache. Booking workflow status should have a clear feature-level owner.

The objective isn't to create the maximum number of stores. It's to avoid giving unrelated state one accidental global owner.

**Challenge 3**

Not for a consequential payment confirmation. The operation might fail, require additional customer authentication, remain pending, or succeed while its response is lost. The UI can respond immediately with "Processing payment..." while waiting for the authoritative result.

Optimistic interaction feedback is useful. False confirmation of financial outcomes is not.

**Challenge 4**

No. The backend state may change between polls. Even a response received immediately before the customer's action can become outdated because another customer performs a competing operation. The backend must enforce inventory correctness at the moment of reservation through appropriate transactional and concurrency mechanisms. Polling improves the freshness of the displayed information but cannot guarantee future availability.

**Challenge 5**

An explicit uncertain or `unknown` state is appropriate if the operation may have completed despite the timeout. The frontend should avoid blindly submitting a new independent booking attempt. An idempotency key, durable operation identifier, and authoritative status endpoint can help determine the outcome.

This is a distributed-systems problem appearing inside an ordinary web application.

---

# 15. The Mental Model Worth Keeping

Reactivity is an elegant mechanism for propagating changes through an application. But it doesn't determine whether the changes are correct.

A well-designed reactive application distinguishes between:

**Independent state**, which must be stored.

**Derived state**, which should generally be calculated from its dependencies.

**Local UI state**, which belongs near the interface that controls it.

**Shared client state**, which may require an application-wide owner.

**Server state**, which represents potentially stale information obtained from a remote authority.

**Workflow state**, which describes the progress and outcome of operations.

Once asynchronous requests enter the picture, you must also reason about races, cancellation, request identity, and out-of-order completion. Once remote business operations enter the picture, you must reason about authoritative outcomes, retries, idempotency, and uncertainty. And once several clients interact with the same backend, the frontend's local data becomes just one temporary perspective on a changing system.

The most important principle is:

**Reactivity keeps the interface synchronized with its local state. Architecture and protocols determine whether that local state remains meaningfully synchronized with reality.**

---

# 16. Next Session — The Frontend–Backend Contract

We've now investigated how a frontend maintains and synchronizes state. But that state often arrives through an API, and APIs introduce their own subtle problems. Imagine that the frontend expects:

```json
{
  "price": 149,
  "currency": "EUR"
}
```

The backend team introduces a new representation:

```json
{
  "price": {
    "amount": 14900,
    "currency": "EUR"
  }
}
```

Both formats are perfectly reasonable. The new backend implementation passes all its tests, and the frontend also passes its own tests. Yet the deployed application breaks.

What went wrong? The two sides no longer agree on the contract connecting them.

In **SE310-L01 — The Frontend–Backend Contract**, we'll investigate REST, GraphQL, RPC, serialization, validation, schema evolution, pagination, error models, and backward compatibility. We'll focus on how independently developed components can communicate reliably without becoming permanently locked to each other's implementation details.

---


---

## Next Lecture — SE240-L04: Delivering Modern Web Applications

Continue in **SE240 — Browser and Frontend Engineering**.

## Further Reading — Optional References

1. [Vue — Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals.html) — Refs, reactive objects, and dependency tracking.
2. [Vue — Computed Properties](https://vuejs.org/guide/essentials/computed.html) — Derived state and caching.
3. [Vue — Watchers](https://vuejs.org/guide/essentials/watchers.html) — Side effects, cleanup, and asynchronous requests.
4. [Pinia — Core Concepts](https://pinia.vuejs.org/core-concepts/) — Shared client state and store design.
5. [TanStack Query — Vue Query Keys](https://tanstack.com/query/latest/docs/framework/vue/guides/query-keys) — Identifying and caching remote data.
6. [TanStack Query — Optimistic Updates](https://tanstack.com/query/latest/docs/framework/vue/guides/optimistic-updates) — Updating UI before server confirmation.

---


---

