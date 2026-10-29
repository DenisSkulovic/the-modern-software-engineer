---
id: SE250-L03
course: SE250
title: "State, Data Fetching, and Real Application Architecture"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L02
next: SE250-L04
---


# SE250 — React Engineering for Experienced Developers
## Lecture 03: State, Data Fetching, and Real Application Architecture

*Your React application has five perfectly functioning components, three copies of the same data, and absolutely no agreement about which one is telling the truth.*

---

# Part I — Intuition

## 1. The Hotel That Was Available and Sold Out Simultaneously

It's Friday evening, and your hotel-booking platform is having a peculiar incident.

A customer searches for hotels in Amsterdam. The results page displays Hotel Aurora, with one room remaining.

The customer opens its details page. One room remaining.

They proceed to the reservation form, enter their information, and successfully book the last room.

The backend processes the reservation correctly. Inventory is reduced from one available room to zero. The reservation is committed, and the customer receives confirmation.

Then they navigate back to the search results.

Hotel Aurora still says one room remaining.

They open its details page again.

Sold out.

They return to search.

One room remaining.

Your React components are disagreeing about reality.

You investigate and discover that the search page has its own `useState` holding hotel results. The details page uses a custom hook that fetches availability through an Effect. The reservation page stores a separate availability object in Context.

Each component appears perfectly reasonable when examined individually.

But the application has no coherent answer to a crucial question:

**Who owns the data, and who is responsible for making it current?**

This is where React stops being a library of components and becomes an architecture problem.

## 2. Not Everything Called State Is the Same Thing

Imagine the booking application as a hotel with several departments.

The receptionist knows which guest is currently checking in. The reservations department maintains bookings. The accounting department controls payment records. The building's public directory tells visitors where to find each department.

You wouldn't ask the receptionist to personally maintain the hotel's entire accounting database.

Nor would you store a customer's unfinished handwritten registration form in the public directory.

Software state needs similarly appropriate ownership.

Consider four pieces of information.

The first is whether a calendar dropdown is currently open.

The second is the customer's selected destination, check-in date, and number of guests.

The third is the current availability of Hotel Aurora.

The fourth is an unfinished guest-information form.

All four affect the interface. But their lifetimes, sources of truth, and sharing requirements differ.

The dropdown is temporary local interface state. The search criteria probably belong in the URL, because customers expect navigation, refresh, and shared links to preserve their search.

The hotel's availability is server-owned data. The frontend can cache a copy, but it cannot make itself authoritative over inventory.

The unfinished guest-information form is a local draft. It may need to survive navigation within the booking flow, but it should not automatically become global application state.

Putting all four into one enormous Context provider would be like storing room keys, financial ledgers, and guest passports in a single reception drawer.

Technically possible. Architecturally deranged.

## 3. State Has an Owner and a Lifetime

There are two questions worth asking whenever you encounter state.

**Who owns the truth?**

And:

**How long must this value survive?**

For a dropdown, the component owns the truth. The value may disappear when the dropdown's component unmounts.

For search filters, the URL can own the canonical selection. Different components read those parameters and derive their views from them.

For availability, the backend owns the truth. A frontend query cache stores a temporary representation of that truth.

For an unfinished form, the booking feature may own the draft until the reservation is completed or abandoned.

These differences determine the technology you should use.

React's `useState` is excellent for small local values.

Context makes a value available to descendants without manually passing it through every intermediate component.

A reducer organizes complicated state transitions.

A routing library manages navigation and URL parameters.

A server-state library manages cached results, freshness, refetching, and mutations.

None of these is the universal answer to every state problem.

The engineering task is to match the mechanism to the responsibility.

### Visual anchor 1 — The state ownership map

```text
Hotel Booking Application
│
├── URL
│   └── Destination, dates, guests, filters
│
├── React component/feature state
│   └── Dropdowns, form drafts, selection
│
├── Shared client state
│   └── Cross-feature UI preferences
│
└── Server-state cache
    ├── Search results
    ├── Hotel details
    ├── Availability
    └── Reservation status
             │
             ▼
       Backend authority
```

Notice that the server-state cache is not the database. It stores representations of data fetched from the server.

And notice that the URL is not merely a string displayed in the address bar. In a navigable application, it can be a major source of application state.

## 4. A Query Cache Is a Library, Not a Warehouse

Imagine that two different components want Hotel Aurora's availability.

One is a hotel card in the search results. The other is an availability badge in a booking sidebar.

Without coordination, both components may independently fetch the same information.

If they each store their own copies, they can disagree after the next booking.

A query cache introduces a shared registry of fetched results.

Each result has an identity, represented by a query key.

For example:

`['availability', 'hotel-aurora']`

The key identifies one particular piece of data.

Components asking for that same data can observe the corresponding cached result.

When the data becomes outdated, the application can mark the query stale and arrange for fresh data to be fetched.

This is similar to a library catalogue.

You do not locate a book by asking every visitor to remember where they last saw it. You give the book a stable identity and a shared catalogue entry.

### Visual anchor 2 — Query identity

```text
HotelCard ─────────┐
                   │
BookingSidebar ────┼──► Query Cache
                   │       │
AvailabilityBadge ─┘       │
                           ▼
                 ['availability', 'A']
                           │
                           ▼
                      GET /A
```

Now all three components can refer to the same logical query.

But the identity must be correct.

Suppose the query key is only `['availability']`, while the request actually depends on which hotel is selected.

Hotel A and Hotel B may then share a cache entry despite representing different data.

The cache is doing exactly what you instructed it to do.

The architecture is wrong.

**A cache key is a declaration of data identity. A wrong key creates a wrong notion of sameness.**

## 5. Fresh Does Not Mean True Forever

Suppose Hotel Aurora has one available room.

The application fetches its availability at 19:00.

At 19:01, another customer books that room.

Your frontend has not received that information.

Should it still display one available room?

Perhaps temporarily. A frontend cache is a representation of previously retrieved server data, not an instantaneous view of every change on the backend.

A server-state library lets you establish a freshness policy.

You might consider a result fresh for a short period, refetch when the user returns to the tab, or invalidate it after a mutation.

But no cache policy magically guarantees inventory availability.

The final reservation must still be checked and committed by the backend.

This distinction is especially important when discussing optimistic updates.

A UI may optimistically display that a hotel was added to the customer's favorites, even before the server confirms it.

That is relatively low risk.

Optimistically announcing that a €2,000 reservation has been successfully completed is a different proposition.

The consequences of being wrong are much greater.

**Frontend freshness is a user-experience policy. Backend authority is a correctness boundary.**

## 6. The Reservation Changes More Than One Screen

Our customer books Hotel Aurora's final room.

The reservation request succeeds.

Which parts of the frontend may now contain outdated information?

The hotel availability query, certainly.

The hotel details page may also include availability.

Search results may contain availability summaries.

A booking sidebar could have a cached quote.

Perhaps the customer's reservation history should also refresh.

Notice that these are not necessarily the same query.

They are different representations potentially affected by the same business event.

This is why invalidation is an architectural decision.

The application must understand which cached data a successful mutation makes obsolete.

The query library cannot infer every business consequence of creating a reservation.

It needs an explicit policy.

A simple implementation might invalidate the availability query for the booked hotel and the relevant search-result queries.

A larger application may centralize those policies inside feature-specific mutation hooks.

The key is that the operation has a known consequence beyond the component that initiated it.

### Visual anchor 3 — Mutation and invalidation

```text
Customer clicks Reserve
          │
          ▼
POST reservation
          │
          ▼
Backend commits booking
          │
          ▼
Mutation succeeds
          │
          ├──► Invalidate hotel availability
          ├──► Invalidate affected search results
          └──► Invalidate reservation history
                         │
                         ▼
                  Fetch current data
```

This does not mean invalidating every query in the application after every mutation.

That would work rather like solving a dusty-room problem by demolishing the building.

The aim is to invalidate the data whose meaning may have changed.

## 7. A Tiny Comprehension Check

Imagine these three values:

- The selected destination is Amsterdam.
- The favorite button for Hotel Aurora is currently showing a loading spinner.
- Hotel Aurora has one remaining room according to the latest fetched response.

Where should each value live?

The destination is a strong candidate for URL state because it describes a shareable, navigable search.

The spinner is temporary interface state, often directly represented by the mutation's pending status.

The room count belongs to server data, accessed through an appropriately identified query cache.

Now imagine the favorite mutation completes successfully.

Should the application invalidate every search query, every user preference, and every hotel detail?

Not necessarily.

It should update or invalidate the representations affected by that particular mutation.

This is the core architectural skill we're developing.

Before reaching for a state-management library, identify the state's owner, identity, lifetime, and consistency requirements.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. Five Questions Before Choosing State Management

A useful React architecture begins with a state inventory rather than a library comparison.

For every important value, ask five questions.

**First: Who is authoritative?** The browser, a component, the URL, a server, or an external service?

**Second: What identifies the value?** Is it associated with a booking draft, hotel ID, tenant, user, search filter set, or route?

**Third: Who needs it?** One component, one feature subtree, several unrelated screens, or multiple sessions?

**Fourth: How long must it survive?** A render, a component lifetime, route navigation, a browser refresh, or an authenticated session?

**Fifth: What makes it obsolete?** A user interaction, a server mutation, time passing, navigation, logout, or another user's action?

These questions are more valuable than asking whether React Context, Redux, Zustand, or TanStack Query is the best state-management library.

Each tool has a different operating model.

Let's apply the questions to the booking application.

The guest-form draft is owned by the booking feature. Its identity is the current booking attempt. It must survive movement between relevant steps, but may be discarded after completion.

Search filters are associated with a route and its query parameters. Their identity is the normalized search criteria. They must survive refresh and support browser history.

Hotel availability is authoritative on the backend. Its cache identity includes the hotel and possibly dates, room category, occupancy, tenant, and other request-dependent variables.

A theme preference is client-owned or account-owned depending on the product. It may need to survive sessions, and changing it should not invalidate hotel availability.

These are different storage and synchronization problems.

Treating them as one undifferentiated category called *global state* hides the important distinctions.

## 9. Local State and Lifting State

React's `useState` is the natural starting point for local interaction.

A date-picker component might own whether its calendar is open.

A guest-name input might own its temporary draft while the form is active.

If two sibling components need to coordinate around a value, the nearest shared ancestor can own it and pass the necessary data and callbacks downward.

This is commonly called *lifting state up*.

But there is a trade-off.

Move state too low, and components that must agree acquire independent copies.

Move it too high, and unrelated parts of the tree may become coupled to changes they do not care about.

Suppose the booking sidebar and guest editor both need to access the same draft.

The booking feature can own the draft and pass relevant values into its children.

That does not mean the entire application root must own the draft.

An important design criterion is the **smallest boundary that contains all legitimate consumers and survives for the required lifetime**.

There is no benefit in making a value global simply because more than one component needs it.

### 9.1 Local state is not inferior state

Developers sometimes treat global stores as the mature solution and `useState` as something appropriate only for toy projects.

That is backwards.

A component that owns its state locally has a narrow interface and fewer accidental dependencies.

If a modal's visibility has no relevance outside its feature, putting it in a global store creates unnecessary responsibility.

Global accessibility should be justified by global consumption or persistence requirements.

The default should be local ownership until a concrete need argues otherwise.

## 10. Context: Distribution, Not Automatic State Management

React Context allows a component to provide a value to descendants without manually forwarding it through every intermediate component.

This is particularly useful for information needed deep in a component tree.

Examples include a theme, locale, feature-level service, or state and dispatch functions belonging to a complex screen.

But Context is often misunderstood.

**Context is a mechanism for distributing values. It is not automatically an efficient global state store, a query cache, or a replacement for domain modeling.**

Consider a `BookingContext` containing the selected hotel, guest names, payment state, search filters, availability data, theme, and several setter functions.

If the provider produces a new context value, components consuming that context can re-render even when the specific field they care about has not changed.

React compares context values using `Object.is`.

A consumer does not automatically subscribe to only one property of a large object merely because it reads that property.

### 10.1 The expensive shared object

Suppose the context value is assembled from state values and functions:

```tsx
const value = {
  bookingDraft,
  theme,
  searchFilters,
  setBookingDraft,
  setTheme,
  setSearchFilters,
};
```

Every consumer of this context is tied to the identity of the provided value.

A theme change can cause a booking-form consumer to render again even when its booking draft is unchanged.

This does not necessarily mean the component remounts or that the DOM is recreated. It means React may perform additional rendering work.

Those are different phenomena, as established in SE250-L01.

A reasonable improvement is to separate independently changing contexts.

For example, a theme context should not be bundled with rapidly changing guest-form input state merely for organizational convenience.

### 10.2 Context is not always a performance disaster

The opposite mistake is declaring Context unusable in large applications.

A stable theme value or service configuration may change infrequently.

A feature-scoped context containing a reducer's state and dispatch can be entirely appropriate.

Context also works well alongside component composition.

Passing a component as `children` can sometimes avoid the need to thread values through many intermediate layers.

The practical question is whether Context expresses a legitimate shared responsibility and whether its update characteristics match the consumers.

If large numbers of components need independent subscriptions to different slices of frequently changing client state, a selector-capable external store may be more suitable.

That is a measurable architectural requirement, not a reason to install a new library automatically.

## 11. `useReducer`: Managing Transitions, Not Just Values

A booking flow has more complicated behavior than opening a dropdown.

The user selects dates, enters guest information, requests a quote, confirms details, and submits the reservation.

Certain transitions must be coordinated.

For example, the application should not enter its completed state before the backend confirms success.

One way to organize the client-side flow is a reducer.

A reducer is a function that receives the current state and an action, then returns the next state.

Imagine a booking draft with three states: editing, reviewing, and submitting.

A reducer might accept actions such as `guestChanged`, `reviewRequested`, `editRequested`, and `submissionStarted`.

```tsx
type DraftState = {
  phase: "editing" | "reviewing" | "submitting";
  guestName: string;
};

type DraftAction =
  | { type: "guestChanged"; name: string }
  | { type: "reviewRequested" }
  | { type: "editRequested" }
  | { type: "submissionStarted" };

function draftReducer(
  state: DraftState,
  action: DraftAction
): DraftState {
  switch (action.type) {
    case "guestChanged":
      return { ...state, guestName: action.name };

    case "reviewRequested":
      return { ...state, phase: "reviewing" };

    case "editRequested":
      return { ...state, phase: "editing" };

    case "submissionStarted":
      return { ...state, phase: "submitting" };
  }
}
```

This is intentionally simple.

A production reducer might validate whether a transition is allowed or represent more specific states. Invalid transitions should be handled deliberately rather than blindly accepted.

The point is that update logic becomes explicit.

Instead of several unrelated handlers each modifying overlapping state fields, actions describe meaningful changes.

### 11.1 Reducers should remain pure

A reducer is not the place to submit a payment or perform an HTTP request.

Its responsibility is to calculate the next state from the previous state and an action.

External operations belong outside the reducer.

For a reservation, the mutation function performs the server request, and the resulting success or failure can lead to an appropriate state transition.

A reducer can describe the application's understanding of the operation.

It should not secretly perform the operation itself.

### 11.2 Reducers and state machines

A reducer with a well-designed action model resembles a state machine.

For more complex workflows, discriminated unions can make impossible combinations harder to represent.

Instead of several booleans such as `isLoading`, `isSuccessful`, `hasError`, and `isEditing`, the application might use a single phase describing the current workflow state.

This prevents combinations like successful, failed, and loading simultaneously.

However, a reducer alone does not guarantee valid transitions. That depends on how it is written.

Formal state-machine libraries can be worthwhile for genuinely complicated workflows. They are not necessary for every form.

The goal is to make transitions understandable and enforce the important invariants.

## 12. Custom Hooks: Reuse Behavior Without Inventing New Truth

React custom hooks allow reusable logic to be expressed using other hooks.

A feature might expose `useHotelAvailability`, `useBookingDraft`, or `useReservationMutation`.

This makes consuming components easier to read.

But there is a significant trap.

Suppose the custom hook internally calls `useState` and performs a fetch through `useEffect`.

Two components call that hook.

Do they automatically share the same state?

No.

Each hook invocation belongs to its own component instance.

Unless the hook accesses a genuinely shared store, context, or query cache, each invocation maintains independent state.

This is one reason a custom hook alone does not solve the duplicated-availability problem.

### 12.1 A custom hook is not a singleton

Consider a simplified hook:

```tsx
function useSelectedHotel() {
  const [hotelId, setHotelId] = useState("A");
  return { hotelId, setHotelId };
}
```

If the search page calls `useSelectedHotel()` and the booking sidebar calls it independently, they receive separate state instances.

Changing one does not automatically update the other.

The name of the hook does not confer shared ownership.

To share the selected hotel, the state must live in a common owner or an appropriate shared state system.

### 12.2 A hook can expose an existing shared cache

A custom hook wrapping TanStack Query behaves differently because the query library maintains a shared cache through its QueryClient.

Two invocations of `useHotelAvailability("A")` can observe the same cached query.

The hook is a convenient feature interface; the QueryClient supplies the shared cache.

Understanding this distinction prevents architectural confusion.

**Custom hooks organize access and behavior. They do not automatically create shared state.**

## 13. URL State: The Application's Public Address

Our customer searches for hotels in Amsterdam from November 12 to November 16, for two adults.

They copy the URL and send it to a friend.

What should happen when the friend opens it?

Ideally, the application reconstructs the same search.

If all search criteria exist only in component state, this may not work.

The browser URL is a natural home for shareable navigation state.

A search route might resemble:

`/hotels?city=amsterdam&checkin=2026-11-12&checkout=2026-11-16&guests=2`

The application parses the parameters, validates them, and constructs a normalized search model.

That model then determines which data should be requested.

### 13.1 The URL is an input, not a trusted database

Users can modify URL parameters manually.

Dates can be invalid. Guest counts can be negative. Unexpected values may appear.

The application must validate and normalize them.

The URL should not be trusted to establish permissions, prices, or reservation authority.

Nor should every internal detail be placed there.

Guest passport information, payment credentials, or sensitive private form data do not belong in shareable URLs.

The URL is appropriate for navigable state, not arbitrary persistence.

### 13.2 Avoid two competing sources of truth

A common mistake is copying URL search parameters into local component state on mount and then allowing the copies to diverge.

The browser address bar says Amsterdam while a local state variable says Berlin.

Now which one should determine the search?

For committed search criteria, it is often cleaner to treat the URL as canonical.

If the user is editing filters before applying them, a separate temporary draft may be appropriate.

When they click Apply, the application updates the URL.

This distinction between **draft criteria** and **committed criteria** is especially useful for search interfaces.

## 14. Server State Is Not Ordinary Client State

We now reach the central technical mechanism.

Server state differs from local React state because it exists independently of the component.

The backend can change it without the frontend knowing.

Another customer can book the final room. An administrator can update the hotel's price. A scheduled process can alter availability.

A frontend representation of this data is therefore a cache.

It has an identity, an age, a fetching status, and a relationship to the authoritative server.

Using `useState` and an Effect for every request means implementing these concerns repeatedly.

You need to decide when to fetch, what to do when a request fails, whether to reuse old data, and how to handle overlapping requests.

You also need to manage cancellation, loading states, cache invalidation, and potentially retry behavior.

This is precisely the class of responsibility addressed by TanStack Query and similar systems.

We'll use TanStack Query v5 as our concrete example.

## 15. The QueryClient and `useQuery`

TanStack Query maintains cached queries through a QueryClient.

Components use `useQuery` to declare which data they need and how to obtain it.

Imagine a hook requesting Hotel Aurora's current availability.

```tsx
function useHotelAvailability(hotelId: string) {
  return useQuery({
    queryKey: ["availability", hotelId],
    queryFn: ({ signal }) =>
      fetchAvailability(hotelId, signal),
    staleTime: 15_000,
  });
}
```

The query key identifies the data.

The query function retrieves it.

The stale time establishes how long the fetched result is considered fresh under this policy.

The supplied AbortSignal can be passed into the underlying fetch implementation to support cancellation.

Notice that the component does not need to manually create a separate Effect, set loading flags, catch every request, and coordinate duplicated cache entries.

The query system manages the query lifecycle.

### 15.1 Query identity must include relevant variables

Suppose availability depends on hotel ID, dates, and number of guests.

Then the query key must distinguish requests with different values for those parameters.

A reasonable key might be:

```tsx
[
  "availability",
  {
    hotelId,
    checkIn,
    checkOut,
    guests,
  },
]
```

If the query function depends on a variable that can change the returned data, that variable generally belongs in the query's identity.

For example, the same hotel may have different availability for different dates.

Leaving dates out of the key may cause a result for November to be reused for December.

This is not a React rendering problem.

It is a cache identity defect.

### 15.2 Query keys should be serializable and predictable

TanStack Query v5 uses array-based query keys with deterministic hashing.

An object inside a key can contain several named parameters. Object property ordering does not ordinarily change the identity, while array element ordering does matter.

But be careful with arbitrary values.

Functions, unstable class instances, or non-serializable objects are poor choices for query identity.

Normalize filters into a predictable data structure.

A useful query-key factory can centralize this convention:

```tsx
const hotelKeys = {
  all: ["hotels"] as const,

  detail: (id: string) =>
    ["hotels", "detail", id] as const,

  availability: (
    id: string,
    checkIn: string,
    checkOut: string
  ) =>
    [
      "hotels",
      "availability",
      id,
      { checkIn, checkOut },
    ] as const,
};
```

The purpose is not to build elaborate abstraction for its own sake.

It is to ensure that fetching and invalidation agree about the identity of cached data.

## 16. Freshness, Cache Lifetime, and Refetching

One of the most common TanStack Query misunderstandings is confusing `staleTime` with cache retention.

They answer different questions.

**Stale time:** How long should fetched data be considered fresh?

**Garbage-collection time:** How long can an inactive query remain cached before it is eligible for removal?

In TanStack Query v5, query data is considered stale immediately by default, unless configured otherwise.

Inactive queries are ordinarily retained for five minutes by default.

This means a query can remain cached even while considered stale.

When a component subscribes to that query again, cached data may be shown while a background refetch occurs.

The library can also refetch stale queries under conditions such as component mounting, window focus, and network reconnection.

These defaults are useful, but they can surprise developers.

### 16.1 Why a page sometimes refetches when you return to it

Imagine the customer switches to another browser tab and returns ten minutes later.

The availability query is stale.

TanStack Query may refetch it when focus returns.

This is sensible for changing server data.

But imagine the data represents a list of countries or a static reference table.

Repeatedly refetching it may provide little benefit.

You can assign a longer freshness interval to relatively stable data.

The point is to choose freshness according to the nature of the data rather than using one global policy for everything.

### 16.2 Freshness is not an absolute correctness guarantee

Suppose a query has a stale time of one minute.

That does not mean the hotel's inventory cannot change during that minute.

It means the client is willing to treat that representation as sufficiently fresh under its chosen policy.

For informational browsing, some delay may be acceptable.

For final booking confirmation, the server must verify actual availability.

A long stale time should never be mistaken for a business guarantee.

### 16.3 Request deduplication

When multiple components request the same query key concurrently, TanStack Query can share the in-flight query promise rather than issuing separate equivalent requests.

This is useful for our hotel card and booking sidebar.

But deduplication depends on correct query identity.

Two genuinely different requests must not be given the same key just to reduce network traffic.

Otherwise, optimization has destroyed correctness.

A single incorrect cached answer shared by five components is not better than five independently incorrect answers.

## 17. Query Results Have More Than Loading and Success

Real data loading involves more than a boolean called `isLoading`.

A query may have no data yet, hold data while refetching, fail after previously succeeding, or be disabled while waiting for required inputs.

TanStack Query distinguishes query status from fetching status.

For example, a query can already have successful cached data while `isFetching` indicates that a background request is in progress.

This allows the interface to display existing information without replacing the entire page with a loading spinner.

That distinction is important for usability.

A search result list should not necessarily disappear every time a background freshness check occurs.

On the other hand, showing historical information without indicating that a critical value is being refreshed can be misleading.

The interface must make a product-level decision about which data is safe to display during revalidation.

For hotel browsing, displaying a previously fetched price with an appropriate freshness policy may be acceptable.

For the final confirmation step, the application should obtain an authoritative quote or reservation response and avoid implying certainty before the server provides it.

### 17.1 Error handling should reflect the operation

Not all errors deserve the same interface.

A failure to refresh a hotel description is different from a failure to submit a reservation.

For a background refetch error, the application may continue displaying cached data while indicating the refresh failed.

For a reservation mutation, the user needs a clear outcome or recovery path.

For an uncertain network failure after submitting a reservation, blindly retrying without idempotency controls may cause duplicate operations.

React architecture should preserve these domain distinctions instead of reducing every failure to a generic red toast.

## 18. Query Invalidation After Mutations

Now return to the original incident.

The customer successfully reserves Hotel Aurora's final room.

The backend availability changes.

The frontend's cached availability must be reconsidered.

TanStack Query exposes `invalidateQueries` for this purpose.

For example, after a reservation succeeds, the application can invalidate the availability query for the affected hotel.

```tsx
queryClient.invalidateQueries({
  queryKey: ["availability", hotelId],
});
```

Invalidation marks matching queries stale.

Active matching queries are ordinarily refetched in the background under the default behavior.

This is a crucial distinction.

**Invalidation does not itself mean replacing the cached value with the correct new value.**

It says that the cached representation should no longer be trusted as fresh.

The query system then arranges appropriate refetching.

### 18.1 Mutation ownership

A mutation changes server-owned state.

In TanStack Query, `useMutation` provides a mechanism for initiating and observing such operations.

A feature-level reservation mutation hook might submit the reservation, then invalidate relevant cached queries after successful completion.

```tsx
function useReserveHotel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reserveHotel,

    onSuccess: async (_result, variables) => {
      await queryClient.invalidateQueries({
        queryKey: [
          "availability",
          variables.hotelId,
        ],
      });
    },
  });
}
```

Here the mutation variables identify which hotel was affected.

The example assumes this is the query-key convention used by the feature.

If availability depends on date and room type, the invalidation policy may need to cover more than one matching query.

The key design must support that decision.

### 18.2 Invalidate narrowly, but not incorrectly

Suppose availability has separate entries for different dates.

A reservation affects one specific room on a specific date range.

Invalidating only one exact query might leave overlapping date-range queries stale.

Invalidating every query in the application would be excessive.

A reasonable policy may invalidate the availability family for the affected hotel.

Likewise, hotel search-result queries might embed availability summaries, requiring their own invalidation.

The appropriate scope follows business dependencies.

This is why query-key organization is an architectural responsibility rather than merely an API detail.

## 19. Updating the Cache Directly

Sometimes the server mutation returns enough information to update cached data immediately.

Imagine changing a hotel's display name in an administrative dashboard.

The server responds with the updated hotel object.

The application may use that response to update a corresponding cached detail query.

TanStack Query provides `setQueryData` for writing cached data directly.

This can avoid unnecessary refetching when the response is sufficiently authoritative and complete.

But this approach introduces responsibility.

You must preserve immutability, update the correct query, and consider other cached representations containing the same information.

An updated hotel name might appear in detail views, search results, favorite lists, and reservation summaries.

Updating one cache entry does not automatically update every representation.

TanStack Query is primarily a query-key-based cache, not a magical normalized entity database that understands all relationships between your API responses.

That is one reason targeted invalidation is often simpler than manually synchronizing many representations.

The trade-off is additional network work.

Choose according to the amount of duplicated data, the API's consistency guarantees, and the complexity of maintaining correct cache updates.

## 20. Optimistic Updates: Fast Interfaces, Temporary Fiction

Optimistic updates deliberately display an expected result before the server confirms it.

For example, clicking Add to Favorites can immediately change the button to Favorited.

If the mutation fails, the interface can restore the previous value or otherwise reconcile with the server.

This can make an interface feel responsive.

But the application is temporarily presenting an assumption.

### 20.1 Two approaches

One approach is to display pending mutation variables directly in the relevant component.

For a favorite button, the UI can show a pending state without changing a shared cache entry.

This is relatively simple when only one part of the interface needs to reflect the optimistic result.

Another approach is to update cached data optimistically.

That can propagate the temporary result to multiple components observing the same query.

But now the application must handle rollback or revalidation if the mutation fails.

A typical cache-based optimistic workflow is:

1. Cancel relevant in-flight refetches that could overwrite the optimistic state.
2. Snapshot the previous cached value.
3. Apply an optimistic update.
4. Perform the mutation.
5. Restore or reconcile the cache on failure.
6. Invalidate affected queries to obtain authoritative data.

The library provides mechanisms for this workflow, but business correctness remains the developer's responsibility.

### 20.2 Concurrent optimistic updates are harder

Suppose the user rapidly toggles a favorite twice.

Two mutations are in flight.

The first fails, and its rollback restores an older snapshot.

But the second may already have succeeded.

A naive rollback can overwrite a newer valid state.

Concurrency turns optimistic updates into a state-coordination problem.

This is why optimistic logic deserves tests involving overlapping mutations, out-of-order responses, and failures.

### 20.3 Do not optimistically invent a confirmed booking

A reservation request may fail because inventory disappeared, the payment was rejected, or the backend refused the operation.

Showing a temporary pending reservation state is reasonable.

Showing an authoritative confirmation before the transaction is committed is not.

A high-value mutation may also require idempotency keys and a way to retrieve the authoritative outcome after a network failure.

The UI must distinguish:

- The customer requested a reservation.
- The request is pending.
- The backend confirmed the reservation.
- The result is rejected or uncertain.

This is domain modeling, not merely animation polish.

## 21. Forms: Draft State Is Not Server State

Our booking form has guest names, contact information, selected extras, and possibly payment-related inputs.

While the customer edits these values, they are drafts.

The backend does not necessarily need to know about every keystroke.

The form can own local state, perhaps using a form library if validation and field coordination become complicated.

On submission, the application transforms the validated draft into an API request.

This is a useful boundary.

The editable form draft should not be casually stored as though it were an authoritative server response.

Similarly, fetched customer profile information may be used to initialize a form, but the user should not lose their unsaved edits whenever the profile query refetches.

### 21.1 Initial values versus ongoing synchronization

Suppose the backend profile contains a guest name.

The form initializes its draft from that name.

A background profile refetch occurs.

Should the form automatically replace the current draft?

Usually not.

The customer may have edited the name.

Blindly synchronizing every server response into form state would destroy legitimate user input.

The application needs an explicit policy for initialization, resetting, and preserving dirty fields.

For a new booking attempt, changing the booking identity may justify resetting the form.

For an existing draft, preserving edits is usually more important.

The underlying question is ownership.

Once the user begins editing, the draft is not merely a direct reflection of the server profile.

## 22. Global Client State: When Context Is Not Enough

Some values legitimately need to be shared across unrelated application branches.

Examples might include global UI preferences, a cross-feature selection, or a complex client-side workflow.

For simple shared state, Context and a reducer can be sufficient.

For frequently changing shared state with many independent consumers, a dedicated external store may be more appropriate.

Libraries such as Zustand and Redux Toolkit offer mechanisms for organizing shared client state and allowing consumers to select relevant values.

The important advantage is not that they make state global.

Context can already distribute values globally.

The advantage may be the subscription model, development tooling, middleware, and explicit update organization.

### 22.1 Avoid making server data a second global truth

A common mistake is fetching hotel availability with TanStack Query and then copying it into a global store.

Now the query cache has one value, while the global store has another.

Which one is current?

Every refetch becomes a synchronization problem.

Every mutation must update two independent representations.

Unless the duplicated data serves a clearly justified purpose, this is unnecessary complexity.

Let the server-state cache own fetched server data.

Let the client store own genuinely client-owned state.

Do not use a general-purpose global store as an accidental second query cache.

## 23. Architecture by Feature, Not by Hook Name

Let's make the structure concrete.

A growing React application might contain hundreds of components.

A common organizational approach is to create large directories called `components`, `hooks`, `services`, `types`, and `utils`.

This works initially.

Eventually, every feature's code is distributed across the entire repository.

Changing hotel availability requires searching through several unrelated directories.

A feature-oriented structure can make ownership clearer.

```text
src/
  app/
    providers/
    router/
  features/
    hotel-search/
      components/
      hooks/
      api/
      query-keys.ts
    hotel-details/
      components/
      hooks/
      api/
    booking/
      components/
      hooks/
      api/
      booking-reducer.ts
  shared/
    ui/
    http/
```

This is an illustrative structure, not a mandatory template.

The relevant point is that hotel search, hotel details, and booking have recognizable homes.

Their public interfaces can expose useful hooks and components without requiring unrelated features to import internal implementation details.

### 23.1 Shared code requires a reason

A `shared` directory can become a dumping ground.

A helper used by only one feature does not automatically become a global utility because it is technically reusable.

Conversely, a genuinely shared HTTP client, date-normalization function, or UI primitive may belong in a common layer.

The decision should reflect stable responsibility and actual reuse.

This is the same architectural principle discussed in SE240-L02.

Here we are applying it to React-specific mechanisms and query ownership.

### 23.2 A custom query hook can be the feature interface

Instead of allowing every component to invent its own API request and query key, the hotel feature can expose `useHotelAvailability`.

The hook uses a centralized key convention and an appropriate API function.

Consumers then depend on the feature's public behavior.

When caching policy or endpoint details change, the implementation can be updated behind that interface.

Do not hide every trivial one-line expression behind a custom hook.

But reusable data-access behavior with an established contract is a strong candidate.

## 24. Authentication and Multi-Tenant Cache Boundaries

There is one production concern that deserves explicit attention.

Imagine a multi-tenant application.

A user belongs to Tenant A and views private customer data.

They log out and another user logs into Tenant B without fully reloading the application.

If the query cache retains private Tenant A data under generic query keys, the new session may accidentally reuse it.

This is not merely a cosmetic stale-data bug.

It can become a confidentiality problem.

### 24.1 Query identity must reflect authorization scope

When the returned representation depends on tenant or user identity, the cache design must account for that scope.

One approach is to include the relevant tenant or user identity in query keys.

Another is to isolate QueryClient instances by authenticated session or clear sensitive cached data when authentication changes.

Applications may use both approaches.

The correct design depends on how authentication and tenancy work.

### 24.2 A cache key is not an authorization mechanism

Including a tenant ID in the query key does not authorize access.

The backend must independently enforce permissions.

A malicious user can modify client-side code and query parameters.

The query cache is a convenience and consistency mechanism, not a security boundary.

### 24.3 Logout is a state transition with consequences

Logout may require clearing private cached data, resetting sensitive local drafts, closing authenticated subscriptions, and redirecting the user.

Merely changing a boolean called `isLoggedIn` may leave private representations in memory.

Persistent caches, if enabled, need particular care.

Authentication transitions must be designed across all relevant state owners.

This is one of the clearest examples of why frontend architecture is more than choosing hooks.

## 25. The React Production State Map

Let's assemble a defensible architecture for the hotel-booking application.

**Search route:** The URL owns committed destination, dates, guest count, sorting, and filters.

**Search feature:** TanStack Query owns cached hotel-search responses, identified by the normalized search criteria and appropriate authorization scope.

**Hotel details:** A hotel-specific query provides descriptive data. Availability uses a separate query whose key includes all availability-relevant parameters.

**Booking draft:** The booking feature owns editable guest information and the current booking step, perhaps through a reducer.

**Reservation mutation:** A mutation function submits the booking request. The backend validates and commits the reservation.

**Post-success synchronization:** Relevant availability, search, and reservation-history queries are invalidated or updated according to explicit policies.

**Theme and locale:** Small shared contexts provide relatively stable presentation preferences.

**API layer:** Typed functions convert requests and responses between frontend models and backend contracts.

The critical property is that each important value has one clear ownership model.

There can be multiple representations of the same real-world entity, but their relationships must be deliberate.

A search result summary and a hotel-details response may both include the hotel's name.

That duplication is sometimes unavoidable.

The architecture must nevertheless know which cache entries become invalid after relevant mutations.

## 26. Diagnosing the Original Incident

Return to the Friday-evening booking bug.

The customer reserves the final room.

The details page correctly shows sold out.

The search results still show one room remaining.

A weak diagnosis is:

> React didn't re-render the search page.

Perhaps it did. Perhaps it rendered the exact stale data it was given.

Another weak diagnosis is:

> We need Redux so every component shares availability.

That merely changes where the stale copy is stored.

A more useful investigation follows the data.

### Step 1 — Identify the authoritative result

Did the backend actually commit the reservation and reduce availability?

Verify the API response and authoritative inventory state.

Do not assume the UI's confirmation means the transaction succeeded.

### Step 2 — Inventory cached representations

Which queries contain availability information?

Does the search response embed remaining-room counts?

Does the details page use a separate availability endpoint?

Are they associated with different query keys?

### Step 3 — Inspect mutation consequences

After successful reservation, which queries are invalidated or updated?

Does the mutation invalidate only the details query while leaving search results unchanged?

Does it invalidate the wrong key prefix?

### Step 4 — Inspect query identity

Could two hotels or two date ranges share the same key accidentally?

Are tenant and user scopes handled correctly?

### Step 5 — Inspect freshness behavior

Is the search query considered fresh because of a long stale time?

Was it invalidated at all?

Did a background refetch fail?

Is cached data being displayed while revalidation occurs?

### Step 6 — Reproduce deterministically

Start with one available room.

Fetch search and details data.

Complete a reservation.

Inspect the backend inventory and both query-cache entries.

Navigate back to search.

Verify that the application eventually reflects zero availability, and that the UI does not assert an invalid booking guarantee while waiting for authoritative data.

### Step 7 — Validate related cases

Test overlapping date ranges, different hotels, failed reservations, repeated navigation, background refetches, authentication changes, and concurrent bookings.

The goal is not merely to make one screen appear correct.

It is to establish a reliable consistency policy.

This is what a senior engineer should be able to explain in an interview.

Not merely which hook they would import.

---

# The Oral Examination

Answer aloud before reading the solutions. Explain the trade-offs and underlying ownership model.

### Question 1 — State Ownership

Classify the following values and explain where they should live:

A calendar dropdown's visibility; committed hotel-search criteria; an unfinished guest form; current hotel availability; and a global theme preference.

Explain which values must survive navigation or refresh.

### Question 2 — The Custom Hook Trap

Two components independently call a custom hook that internally uses `useState` and `useEffect` to load availability.

Do they automatically share state?

How would the answer differ if the hook used TanStack Query with the same query key?

### Question 3 — The Broken Query Key

A query fetches availability based on hotel ID and check-in date.

Its key is always `['availability']`.

What could happen when navigating between hotels or dates?

How should the key change?

### Question 4 — Context and Rendering

A large Context provider contains theme, booking draft, search filters, and authentication information.

Typing into the booking form causes unrelated consumers to render.

Explain why.

Would wrapping every consumer in `React.memo` necessarily solve the problem?

### Question 5 — The Reducer

A booking flow has editing, reviewing, submitting, successful, and failed states.

Why might a reducer or explicit state machine be preferable to several unrelated booleans?

Should the reducer perform the HTTP reservation request itself?

### Question 6 — Freshness

A query has a stale time of thirty seconds.

A room is booked by another customer five seconds after the frontend fetches availability.

Does the stale-time policy guarantee the frontend knows the new availability?

What must happen during final reservation confirmation?

### Question 7 — Invalidation

A successful reservation invalidates the hotel details query but not search results.

The search results include availability summaries.

What additional action might be necessary?

Why is invalidating the entire cache not always the best solution?

### Question 8 — Optimistic Updates

A favorite mutation updates the cached favorite list before server confirmation.

Two favorite mutations overlap, and the first fails after the second succeeds.

Why can naive rollback corrupt the displayed state?

What safeguards would you consider?

### Question 9 — URL Versus Local State

A search page stores destination and dates in local state.

The user refreshes the browser and loses their search.

What architectural change would you recommend?

How would you distinguish committed filters from temporary editing state?

### Question 10 — Tenant Isolation

A user logs out of Tenant A and logs into Tenant B.

Some queries have generic keys such as `['customers']`.

What is the risk?

What safeguards belong in the query-cache design, authentication transition, and backend?

### Question 11 — Architecture Interview

You are asked to design a React frontend for hotel search and reservation.

Explain which state belongs in React local state, Context, a query cache, and the URL.

Describe the reservation mutation flow and how the application recovers from stale availability.

Your answer should make trade-offs explicit rather than merely listing libraries.

---

# Solutions and Discussion

### Solution 1 — State Ownership

The dropdown is local interface state. Search criteria are strong candidates for URL state because they should survive navigation and refresh.

The unfinished guest form belongs to a booking-feature draft whose lifetime should match the booking process.

Availability is server-owned data accessed through a cache. The theme may be provided through Context and persisted according to product requirements.

### Solution 2 — The Custom Hook Trap

A custom hook using its own `useState` creates separate state for each invocation.

The hook name does not create a singleton.

When the hook wraps TanStack Query using the same QueryClient and query key, consumers can observe the same cached query.

The shared ownership comes from the query cache, not from custom-hook syntax.

### Solution 3 — The Broken Query Key

Different hotels and dates can incorrectly share a cache entry.

The key must include all variables that distinguish the requested result, such as hotel ID, dates, occupancy, and any relevant authorization scope.

A normalized parameter object can make identity explicit.

### Solution 4 — Context and Rendering

All consumers of a context can re-render when its provided value changes.

A large frequently changing context therefore couples unrelated consumers.

`React.memo` does not block updates caused by a changing context that the component consumes.

Split responsibilities, keep state appropriately local, or use a store with suitable selector-based subscriptions when justified.

### Solution 5 — The Reducer

A reducer makes transitions explicit and can reduce contradictory state combinations.

Discriminated states can help represent valid workflow phases.

The reducer should remain pure.

The HTTP request belongs to the mutation or application-operation layer. Its result can drive a subsequent state transition.

### Solution 6 — Freshness

No.

Stale time is a client freshness policy, not a guarantee that the backend cannot change.

The final reservation must be validated and committed by the authoritative backend, using appropriate concurrency and transactional controls.

### Solution 7 — Invalidation

The mutation may need to invalidate the affected search queries as well as hotel details and availability.

The correct scope depends on which cached representations can become outdated.

Invalidating everything can create excessive network activity and unnecessary disruption.

### Solution 8 — Optimistic Updates

A rollback based on an older snapshot can overwrite the result of a newer successful mutation.

Possible safeguards include careful mutation ordering, version-aware reconciliation, targeted invalidation, delaying optimistic changes, or deriving pending UI from mutation state without modifying the shared cache.

The correct approach depends on concurrency and product requirements.

### Solution 9 — URL Versus Local State

Committed search criteria should generally be represented in the URL.

The application should parse and validate them, then derive the query parameters used to fetch results.

Temporary edits may remain in a local draft until the user applies them.

### Solution 10 — Tenant Isolation

Generic cache keys may allow one authenticated session's private data to be reused by another.

Use appropriate user or tenant scoping, clear or isolate sensitive caches across authentication transitions, and reset relevant private client state.

The backend must enforce tenant authorization independently.

Cache isolation is not a substitute for server-side access control.

### Solution 11 — Architecture Interview

A defensible design uses the URL for committed search criteria, component or feature state for drafts and UI interactions, a server-state cache for fetched hotel and availability data, and narrowly scoped Context or external stores for genuinely shared client-owned values.

Reservation submission is an explicit mutation with authoritative backend validation.

Successful mutations invalidate or reconcile affected queries.

The UI distinguishes pending state from confirmed success and handles stale or uncertain results without claiming business guarantees it does not possess.

---

# The Mental Model Worth Keeping

Before choosing a React state-management tool, identify four things:

**Ownership:** Who holds the authoritative truth?

**Identity:** What distinguishes this value from another value?

**Lifetime:** How long must it survive, and who needs access?

**Invalidation:** What makes the current representation obsolete?

React state, Context, reducers, URL parameters, and query caches solve different parts of these problems.

A well-designed frontend does not eliminate all duplicated representations of data. It establishes clear rules for where those representations come from, when they remain valid, and how they are updated.

The strongest React architecture is not the one with the most sophisticated state-management library.

It is the one in which a developer can trace a wrong value back to its owner and explain how the application restores consistency.

---

# Next Lecture — SE250-L04: React Performance, Testing, and Debugging

We now have a plausible state architecture.

But imagine the search page displaying 2,000 hotels.

Changing a small preference causes hundreds of components to re-render. A large table becomes sluggish. A Context provider updates too frequently. An expensive filtering operation runs repeatedly.

Should we add `useMemo` everywhere?

Should we wrap every component in `React.memo`?

Would React Compiler solve the problem automatically?

And how do we distinguish genuine rendering bottlenecks from network latency, browser layout work, or inaccurate profiling assumptions?

SE250-L04 introduces the performance and debugging discipline needed to answer those questions.

The goal is not to decorate code with optimization hooks.

It is to measure the real problem, understand why React performs particular work, and verify that a correction improves the application.

*The spoken lecture ends here. The following practical investigations are intended for on-screen work.*

---

# Optional Practical Lab — The Broken Booking Cache

## Working Protocol

The lab contains deliberate architectural defects.

Do not read the solutions before attempting the investigation.

For each experiment:

1. Predict what should happen.
2. Explain what you expect the cache or component state to contain.
3. Run the application and reproduce the defect.
4. Identify the incorrect ownership or identity decision.
5. Implement the correction independently.
6. Verify the behavior under more than one execution sequence.
7. Only then ask AI to review your reasoning.

## Experiment A — Two Hotels, One Cache Entry

### Objective

Diagnose a query-key collision and missing invalidation after a reservation.

The application has two hotels, each starting with two available rooms.

The backend is represented by a small in-memory service.

The interface displays both hotel cards and allows the user to reserve a room.

### Setup

Create a Vite React and TypeScript project with TanStack Query.

```bash
npm create vite@latest booking-cache-lab -- --template react-ts
cd booking-cache-lab
npm install
npm install @tanstack/react-query
npm run dev
```

Replace `src/App.tsx` with the following deliberately broken implementation.

### Broken implementation

The code contains two bugs.

First, the two hotel cards share the same query key even though they request different data.

Second, completing a reservation does not invalidate the affected availability query.

Read the code and predict the result before running it.

```tsx
import { useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

type HotelId = "A" | "B";

type Availability = {
  hotelId: HotelId;
  remaining: number;
};

const inventory: Record<HotelId, number> = {
  A: 2,
  B: 2,
};

const delay = (ms: number) =>
  new Promise<void>(resolve =>
    setTimeout(resolve, ms)
  );

async function fetchAvailability(
  hotelId: HotelId
): Promise<Availability> {
  await delay(250);

  console.log("FETCH", hotelId);

  return {
    hotelId,
    remaining: inventory[hotelId],
  };
}

async function reserveHotel(
  hotelId: HotelId
): Promise<void> {
  await delay(150);

  if (inventory[hotelId] <= 0) {
    throw new Error("Hotel is sold out");
  }

  inventory[hotelId] -= 1;

  console.log(
    "RESERVED",
    hotelId,
    "Remaining:",
    inventory[hotelId]
  );
}

function HotelCard({
  hotelId,
}: {
  hotelId: HotelId;
}) {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");

  const availability = useQuery({
    queryKey: ["availability"], // BUG
    queryFn: () => fetchAvailability(hotelId),
    staleTime: Infinity,
  });

  const reservation = useMutation({
    mutationFn: () => reserveHotel(hotelId),

    onSuccess: () => {
      setMessage("Reservation succeeded");

      // BUG: no cache invalidation
    },

    onError: (error: Error) => {
      setMessage(error.message);
    },
  });

  const data = availability.data;

  return (
    <section>
      <h2>Hotel {hotelId}</h2>

      <p>
        Data belongs to:{" "}
        {data?.hotelId ?? "Loading"}
      </p>

      <p>
        Rooms remaining:{" "}
        {data?.remaining ?? "Loading"}
      </p>

      <button
        disabled={reservation.isPending}
        onClick={() => reservation.mutate()}
      >
        Reserve room
      </button>

      <p>{message}</p>
    </section>
  );
}

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <h1>Hotel Availability Lab</h1>

      <HotelCard hotelId="A" />
      <HotelCard hotelId="B" />
    </QueryClientProvider>
  );
}
```

The `queryClient` variable inside `HotelCard` is intentionally unused at first. The missing invalidation is part of the exercise.

### Task 1 — Predict query identity

Both cards request availability using the same key.

What will the query cache contain?

Can it correctly distinguish Hotel A from Hotel B?

What do you expect the `Data belongs to` fields to display?

### Task 2 — Observe

Run the application.

Inspect the browser console.

Compare the displayed data for both hotels.

Explain why two independent component instances can nevertheless observe the same cached query.

### Task 3 — Fix query identity

Change the query key so that each hotel has its own cache entry.

Verify that Hotel A's card displays data belonging to A and Hotel B's card displays data belonging to B.

### Task 4 — Investigate reservation invalidation

Reserve a room at Hotel A.

Inspect the console.

The in-memory inventory decreases, but the cached value remains unchanged.

Explain why the mutation's success does not automatically update the query cache.

### Task 5 — Fix invalidation

Use `queryClient.invalidateQueries()` to invalidate the affected hotel's availability query after successful reservation.

Ensure that the invalidation key matches the query-key convention.

Reserve a room again.

Verify that the displayed availability reflects the updated backend inventory after refetching.

### Task 6 — Test the sold-out state

Reserve until Hotel A has no rooms remaining.

Attempt another reservation.

Confirm that the backend rejects the operation.

Improve the UI so it disables reservation when authoritative cached availability indicates zero rooms, while still handling the possibility that another client books the final room before submission.

The backend remains authoritative.

### Acceptance criteria

Hotel A and Hotel B have independent cache entries.

A reservation invalidates the correct query.

The UI eventually reflects updated availability.

A failed reservation is not reported as successful.

The frontend does not assume that disabling a button guarantees inventory correctness.

---

# Experiment B — Context Re-renders Versus Remounts

## Objective

Distinguish a context-driven re-render from a component remount.

These are different behaviors with different consequences.

### Starting implementation

This example intentionally places theme and counter state in one Context.

```tsx
import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

type AppContextValue = {
  theme: string;
  count: number;
  setTheme: (value: string) => void;
  increment: () => void;
};

const AppContext =
  createContext<AppContextValue | null>(null);

function useAppContext() {
  const value = useContext(AppContext);

  if (!value) {
    throw new Error("Missing AppContext");
  }

  return value;
}

function Counter() {
  const { count, increment } = useAppContext();

  console.log("Counter rendered");

  useEffect(() => {
    console.log("Counter mounted");

    return () => {
      console.log("Counter unmounted");
    };
  }, []);

  return (
    <button onClick={increment}>
      Count: {count}
    </button>
  );
}

function ThemeControl() {
  const { theme, setTheme } = useAppContext();

  return (
    <button
      onClick={() =>
        setTheme(theme === "dark" ? "light" : "dark")
      }
    >
      Theme: {theme}
    </button>
  );
}

export default function App() {
  const [theme, setTheme] = useState("light");
  const [count, setCount] = useState(0);

  const value = {
    theme,
    count,
    setTheme,
    increment: () => setCount(n => n + 1),
  };

  return (
    <AppContext.Provider value={value}>
      <ThemeControl />
      <Counter />
    </AppContext.Provider>
  );
}
```

### Tasks

First, predict what happens when changing the theme.

Does the Counter component re-render?

Does it necessarily unmount?

Does its count reset?

Run the program and distinguish render logs from mount and unmount logs. Remember that Strict Mode can add development-only lifecycle checks.

Next, refactor the application into separate contexts for theme and counter state.

Arrange the providers so that theme changes no longer cause Counter to re-render solely because of a shared context value.

Finally, deliberately add a changing key to the Counter component's identity.

Observe the difference between re-rendering and remounting.

### Acceptance criteria

You can explain why changing a context value causes its consumers to re-render.

You can distinguish render activity from actual remounts.

You understand why a changing key can discard local component state.

You can justify when splitting contexts is preferable to one large shared provider.

---

# Experiment C — Design the Booking State Map

## Objective

Develop an architecture without immediately writing code.

You are given these requirements:

A customer can search hotels by city and dates, sort results, open hotel details, edit guest information, add a hotel to favorites, reserve a room, and revisit reservation history.

Search criteria must survive refresh and support shareable links.

An unfinished booking draft must survive movement between the booking steps.

Availability can change because of other customers.

Favorite updates should feel responsive.

Reservations must never be declared successful before backend confirmation.

The application supports multiple authenticated tenants.

### Deliverable

Produce a short architecture note explaining:

- Which state belongs in the URL.
- Which state belongs locally to components.
- Which state belongs to the booking feature.
- Which data belongs in TanStack Query.
- Whether Context or an external client store is justified.
- What query keys are needed.
- Which queries reservation and favorite mutations should invalidate.
- How private cached data is isolated across tenants and logout.
- How the booking flow distinguishes editing, pending, confirmed, failed, and uncertain outcomes.

Do not start by choosing Redux or Zustand.

Start by drawing ownership boundaries.

### Evaluation criteria

A good design has identifiable sources of truth, appropriately scoped state, consistent query identity, explicit mutation consequences, and no unnecessary duplicated server data.

It should be possible to explain the data flow without resorting to framework jargon.

---

# Lab Solutions and Diagnostic Notes

**Read only after attempting the investigations.**

## Experiment A — Query-Key and Invalidation Fix

The original key `["availability"]` does not distinguish hotels.

Both components observe the same logical query.

The corrected query should include the hotel ID:

```tsx
const availability = useQuery({
  queryKey: ["availability", hotelId],
  queryFn: () => fetchAvailability(hotelId),
  staleTime: Infinity,
});
```

After a successful reservation, invalidate the matching hotel query:

```tsx
const reservation = useMutation({
  mutationFn: () => reserveHotel(hotelId),

  onSuccess: async () => {
    await queryClient.invalidateQueries({
      queryKey: ["availability", hotelId],
    });

    setMessage("Reservation succeeded");
  },

  onError: (error: Error) => {
    setMessage(error.message);
  },
});
```

The `staleTime: Infinity` setting makes the missing invalidation particularly visible. The query remains fresh indefinitely under the normal freshness policy until explicitly invalidated.

That is useful for the exercise, not necessarily a suitable production policy for hotel inventory.

In a real booking system, the query key would need to include all relevant availability parameters, and the mutation might affect several cached representations.

## Experiment B — Context and Identity

The initial Counter component consumes the same Context as the theme.

Changing the theme changes the provider's value, causing context consumers to re-render.

This is not automatically a remount.

The Counter's local state remains associated with the same component identity unless the tree structure, type, or key changes in a way that resets it.

Splitting theme and counter state into independent contexts reduces unnecessary coupling.

A changing key can force React to treat Counter as a different component instance and reset its local state.

The distinction is architectural as well as operational: re-rendering means recalculating a component, while remounting means replacing its identity.

## Experiment C — Suggested Ownership

A reasonable architecture puts committed search criteria in the URL, temporary form and UI state in local or booking-feature state, and fetched hotel data in the query cache.

The booking flow can use a reducer with explicit phases.

The favorite mutation can use a limited optimistic update with appropriate reconciliation.

The reservation mutation must wait for authoritative backend confirmation before declaring success.

Query identity must account for hotel IDs, relevant search parameters, and appropriate authorization scope.

Logout must clear or isolate sensitive cached information.

Other implementations are possible, but these invariants must be preserved.

---

# Further Reading

1. **React — Sharing State Between Components**  
   https://react.dev/learn/sharing-state-between-components

2. **React — Passing Data Deeply with Context**  
   https://react.dev/learn/passing-data-deeply-with-context

3. **React — Scaling Up with Reducer and Context**  
   https://react.dev/learn/scaling-up-with-reducer-and-context

4. **React — Choosing the State Structure**  
   https://react.dev/learn/choosing-the-state-structure

5. **TanStack Query — Important Defaults**  
   https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults

6. **TanStack Query — Query Keys**  
   https://tanstack.com/query/latest/docs/framework/react/guides/query-keys

7. **TanStack Query — Query Invalidation**  
   https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation

8. **TanStack Query — Mutations**  
   https://tanstack.com/query/latest/docs/framework/react/guides/mutations

9. **TanStack Query — Optimistic Updates**  
   https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates

10. **TanStack Query — Query Cancellation**  
    https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation

11. **TanStack Query — QueryClient**  
    https://tanstack.com/query/latest/docs/reference/QueryClient

12. **React — useSyncExternalStore**  
    https://react.dev/reference/react/useSyncExternalStore

Cross-reference SE240-L02 for general frontend architecture, SE240-L03 for state ownership and server-state concepts, SE250-L01 for rendering and identity, and SE250-L02 for Effects and asynchronous request races.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE250-L03 — STATE AND DATA ARCHITECTURE
================================================

FIRST QUESTIONS
---------------
1. Who owns the authoritative value?
2. What identifies it?
3. Who needs access?
4. How long must it survive?
5. What makes it obsolete?

STATE CATEGORIES
----------------
Local UI:
  dropdowns, modal visibility, temporary selection
  -> useState

Feature workflow:
  booking draft, step transitions
  -> useState / useReducer / scoped Context

URL:
  committed filters, search terms, pagination
  -> router / search params

Server state:
  hotels, availability, reservations
  -> query cache

Shared client:
  cross-feature preferences, workflows
  -> Context / external store when justified

CONTEXT
-------
Distributes values through component tree.
Does not automatically provide:
- efficient field-level subscriptions
- server caching
- request deduplication
- automatic data freshness

Context consumer re-renders when
provided context value changes.

memo does not block context updates
for a component consuming that context.

REDUCER
-------
(state, action) -> nextState

Good:
- complex local transitions
- explicit workflows
- coordinated state changes

Not for:
- HTTP side effects inside reducer
- arbitrary globalizing of local state

CUSTOM HOOKS
------------
Reusable hook != shared state.

Two calls to useState-based custom hook
have independent state instances.

Two calls to TanStack useQuery with
same key and QueryClient can share cache.

URL STATE
---------
Shareable search criteria belong in URL.
Parse + validate + normalize.
Draft filters can be local until Apply.

Never trust URL for authorization.
Avoid private sensitive data in URLs.

TANSTACK QUERY v5
-----------------
QueryClient:
  shared query and mutation infrastructure

useQuery:
  queryKey -> identity
  queryFn  -> data retrieval
  staleTime -> freshness policy

useMutation:
  performs server-changing operation

queryClient.invalidateQueries:
  mark matching cached queries stale
  active matches usually refetch

QUERY KEYS
----------
GOOD:
["availability", hotelId, { dates, guests }]

BAD:
["availability"] when query depends on hotel

All relevant changing request variables
must be represented in query identity.

Object key order is normalized for
query-key hashing.
Array element order matters.

FRESHNESS
---------
Default staleTime: 0
Queries stale immediately by default.

Default inactive gcTime: 5 minutes.

stale != absent
cached != guaranteed current
fresh != guaranteed business truth

Refetch triggers can include:
- mounting an observer
- window focus
- network reconnection
- explicit invalidation

Request deduplication works for
appropriately identical query keys.

QUERY STATES
------------
Initial pending:
  no result yet

Success:
  cached data available

Error:
  query attempt failed

isFetching can be true while
successful cached data is displayed.

MUTATION CONSEQUENCES
---------------------
Reservation succeeds:
  invalidate affected availability
  invalidate affected search results
  invalidate relevant reservation history

Scope invalidation by business impact.
Avoid blind invalidate-everything policies.

OPTIMISTIC UPDATES
------------------
1. Identify safe operation
2. Cancel conflicting refetches
3. Snapshot previous cache
4. Apply temporary update
5. Mutation executes
6. Roll back/reconcile on failure
7. Revalidate authoritative data

Concurrent optimistic mutations
require additional coordination.

Favorite toggle:
  reasonable optimistic candidate

Payment/reservation confirmation:
  backend confirmation required

STATE DUPLICATION
-----------------
Avoid:
TanStack Query -> copy data -> global store
-> independently update both forever

Separate:
server cache ownership
from client-owned draft/workflow state.

FORMS
-----
Editable draft is client-owned.
Fetched profile is input, not a mandate
to overwrite dirty fields.

Initialize intentionally.
Reset intentionally.
Preserve user edits intentionally.

MULTI-TENANCY
-------------
Cache keys may need tenant/user scope.
Clear/isolate sensitive data at logout.
Reset relevant authenticated resources.

Client cache is NOT an authorization layer.
Backend enforces access independently.

FEATURE ARCHITECTURE
--------------------
app/
features/hotel-search/
features/hotel-details/
features/booking/
shared/

Prefer identifiable feature owners.
Centralize query-key conventions.
Expose meaningful feature hooks.
Avoid giant god-providers.

DEBUGGING A STALE VALUE
-----------------------
1. Verify backend truth.
2. Identify cached representations.
3. Inspect query keys.
4. Inspect mutation invalidation.
5. Inspect freshness/refetch policy.
6. Reproduce with controlled timing.
7. Verify all affected screens.

INTERVIEW RED FLAGS
-------------------
"Everything belongs in global state."
"Context is automatically an efficient store."
"Custom hooks always share state."
"staleTime guarantees data is correct."
"Mutations update every related query."
"Query invalidation deletes the data."
"Optimistic success equals committed booking."
"Cache keys don't need all request params."
"Tenant IDs in keys enforce authorization."
"React didn't re-render" without evidence.

NEXT:
SE250-L04 — React Performance,
Testing, and Debugging
```
