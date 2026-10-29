---
id: SE250-L04
course: SE250
title: "React Performance, Testing, and Debugging"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE250-L03
next: SE250-L05
---

# SE250 — React Engineering for Experienced Developers
## Lecture 04: React Performance, Testing, and Debugging

*The search box freezes on every keystroke. Someone wraps everything in `memo`. The codebase becomes twice as complicated, and the search box is still slow.*

---

# Part I — Intuition

## 1. The Hotel Search That Takes Half a Second to Type a Letter

Imagine joining the frontend team of a successful hotel-booking platform.

The application displays several hundred hotel results, including prices, ratings, availability indicators, and reservation buttons.

The backend is performing well. Search requests usually complete quickly, and the database is not overloaded.

Yet customers complain that the search interface feels sluggish.

You open the application and type "Amsterdam" into the hotel-name filter.

The first letter appears immediately.

The second is noticeably delayed.

By the fourth letter, the interface is visibly struggling.

You open Chrome DevTools and notice that the main thread is busy whenever you type.

A colleague suggests debouncing the search input. Another suggests adding `useMemo` around the filtering function. A third proposes wrapping every hotel card in `React.memo`.

The fourth suggests replacing React entirely.

The fourth colleague has apparently been waiting for this moment since the company hired them.

Before choosing a solution, we need to understand what is actually happening.

The user is not necessarily waiting for the network. They may be waiting for React to calculate the interface, for JavaScript to perform expensive computations, or for the browser to process the resulting DOM and layout work.

These are different bottlenecks.

And each requires different evidence.

## 2. React Rendering Is Work, but Not All Work Is Equal

Recall the rendering model from SE250-L01.

A state update causes React to calculate the next interface. React then determines what changes need to be committed to the DOM.

Suppose our hotel-search page maintains a state variable called `searchText`.

Every keystroke updates that state.

If the search input and the entire results list are owned by the same component, React may execute the parent component and recursively render a substantial portion of its children.

Each hotel card may calculate derived values, format prices, build element descriptions, and execute other JavaScript.

Even if React eventually determines that most DOM elements do not need changing, it may already have performed substantial rendering work.

This distinction matters.

**Avoiding DOM changes does not necessarily mean avoiding expensive JavaScript calculations.**

Imagine 500 hotel cards, each requiring a moderately expensive calculation.

A single card is harmless.

But repeating that calculation 500 times after every keystroke can produce noticeable delays.

The problem is not that React is incapable of handling 500 components.

The problem is that our update has caused work that may not have been necessary.

### Visual anchor 1 — An expensive update

```text
Customer types "A"
       |
       v
searchText changes
       |
       v
SearchPage renders
       |
       v
500 HotelCard renders
       |
       v
500 calculations
       |
       v
React commits changes
       |
       v
Browser updates screen
```

The question is not merely how to make each calculation faster.

We should first ask why all 500 cards were recalculated.

Perhaps their props actually changed.

Perhaps the parent unnecessarily recreated values.

Perhaps state is owned too high in the tree.

Or perhaps there are simply too many visible DOM elements.

Those problems require different interventions.

## 3. Rendering Is Not the Same as Committing

Suppose our colleague adds a console log inside every hotel card.

Typing one letter produces hundreds of logs.

They announce that React is repainting the page hundreds of times.

Not necessarily.

A component function executing is a render.

React applying changes to the DOM is a commit.

The browser performing layout and paint is yet another process.

A component may render without causing a corresponding DOM change.

React may also abandon rendering work before committing it, particularly when work can be interrupted or restarted.

Development Strict Mode can introduce additional component executions.

Therefore, a console log is useful evidence of function execution, but not definitive proof of expensive DOM changes.

We need measurements that distinguish these layers.

### Visual anchor 2 — Three places to investigate

```text
React render work
   Component calculations
   Child renders
   Reconciliation
          |
          v
React commit work
   DOM updates
   Ref attachments
   Layout Effects
          |
          v
Browser work
   Style calculation
   Layout
   Paint
   Compositing
```

React DevTools helps us investigate React rendering.

The browser Performance panel helps investigate the broader main-thread timeline.

Neither tool should be treated as a universal performance oracle.

## 4. Optimization Is About Avoiding Unnecessary Work

Imagine that Hotel Aurora's name, rating, and price have not changed.

The user is typing into an unrelated filter input.

Should its hotel card perform an expensive formatting or calculation routine again?

Perhaps not.

If React can establish that the relevant inputs are unchanged, it may be able to reuse previous work.

This is the idea behind memoization.

Memoization stores the result of a calculation or component rendering work so that equivalent inputs do not require repeating it.

React historically provided explicit tools for this:

`React.memo` can help skip rendering a component whose props have not changed.

`useMemo` can cache an expensive calculation result.

`useCallback` can preserve a function identity between renders.

These mechanisms are useful, but they are not interchangeable.

And adding them everywhere is not automatically an improvement.

A component that takes a tiny fraction of a millisecond to render may not justify additional dependency logic and memoization bookkeeping.

More importantly, memoization cannot rescue an architecture that performs fundamentally unnecessary operations.

If the application renders 5,000 DOM rows while only twenty are visible, reducing some calculations does not eliminate the cost of maintaining those thousands of elements.

If every keystroke triggers a blocking synchronous operation, wrapping a child in `memo` may not address it.

**The best optimization is often removing the work, not caching its result.**

## 5. React Compiler Changes the Economics

Modern React includes an optional build-time optimizer called React Compiler.

The compiler analyzes React components and hooks and can automatically apply memoization that previously required manual `memo`, `useMemo`, and `useCallback`.

This is important because a large amount of manual memoization code exists only to prevent unnecessary calculations and render cascades.

But the compiler is not a magic performance switch.

It does not make rendering 10,000 DOM elements free.

It does not automatically turn an expensive algorithm into an efficient algorithm.

It does not remove the need for correct component state, immutable data, or pure rendering.

And it cannot optimize every arbitrary piece of JavaScript.

The compiler works best when code follows React's rules.

If a component mutates its inputs or violates supported patterns, the compiler may skip optimizing it.

So the architectural principles remain valuable even in compiler-enabled applications.

The developer must still recognize where work comes from and whether that work should exist.

## 6. Sometimes the Urgent Work and Expensive Work Should Be Separated

Typing into a text field is an urgent interaction.

Updating a complicated results visualization may be less urgent.

React supports mechanisms for distinguishing urgent updates from work that can be interrupted.

For example, the input text can update immediately while an expensive results update is allowed to proceed with lower priority.

This is the purpose of transition-related APIs and deferred values.

The important idea is not that React suddenly makes expensive calculations faster.

Instead, it can improve responsiveness by allowing urgent interactions to take priority over some less urgent rendering work.

### Visual anchor 3 — Urgent versus deferred

```text
User types "Amst"
      |
      ├──► Update text input
      |       High priority
      |       Remains responsive
      |
      └──► Update large results list
              Lower priority
              Can be interrupted
              May temporarily show old results
```

But this technique has limitations.

It does not eliminate the expensive work.

It does not automatically debounce network requests.

And it does not move CPU-intensive JavaScript onto another thread.

For genuine CPU-heavy computation, a Web Worker or algorithmic redesign may be necessary.

## 7. Correctness Comes Before Performance

Now imagine our hotel-search interface has become wonderfully fast.

Unfortunately, when a customer switches from Hotel A to Hotel B, the previous hotel's availability sometimes appears under the new hotel.

This is a correctness defect.

No amount of rendering optimization makes it acceptable.

We encountered this race in SE250-L02.

Here we will add another discipline: writing a test that reproduces the problem deterministically.

Rather than waiting for random network conditions, we deliberately control response order.

We request Hotel A, then Hotel B.

We resolve B first.

We resolve A afterward.

We verify that the interface continues to show B's information.

This test describes a user-visible invariant.

It does not need to inspect the component's internal state setter or count how many times an Effect ran.

That is the central philosophy of React Testing Library.

**Test what the user can observe, while controlling the conditions that make the bug possible.**

### A tiny comprehension check

Suppose the React Profiler shows that a hotel list takes 70 milliseconds to render after every keystroke.

You wrap all hotel cards in `React.memo`, but each card receives a newly created callback prop during every parent render.

Will memoization necessarily prevent those cards from rendering?

No.

By default, React compares props shallowly. A newly created function has a different reference identity, so memoization may not provide the expected benefit.

Before using `useCallback`, however, ask whether the parent actually needs to re-render the list when the input changes.

Moving the input's state into a smaller component could remove the unnecessary render cascade at its source.

That is the distinction between optimizing an existing architecture and improving the architecture itself.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. Investigating an Interaction, Not a Vague Feeling

When someone reports that a React application is slow, the first task is to define the failing interaction.

"Search is slow" is not sufficiently precise.

Does typing feel delayed?

Does the input update immediately but the results appear late?

Does scrolling stutter?

Does navigating to a hotel detail page take too long?

Does the screen freeze after clicking a filter?

Each symptom suggests a different bottleneck.

For our hotel-search page, define the investigation:

The user types a character into the search field. The text appears noticeably late, and the interface becomes temporarily unresponsive.

We want to measure the work between the input interaction and the next visual response.

This naturally leads to React DevTools and the browser's Performance panel.

We already discussed general browser performance, rendering costs, and user-centric performance metrics in SE240-L05.

Here our focus is what React specifically contributes to that work.

## 9. React DevTools Profiler

React DevTools includes profiling capabilities for investigating component rendering performance.

You can record an interaction and inspect which components rendered, how much time was spent rendering, and how the work was distributed across the component tree.

Depending on the tooling version, views and labels may differ, but the core questions remain stable.

Which component updates were expensive?

Which components participated in the update?

Was the expensive work concentrated in one subtree or distributed across hundreds of children?

Did components render because their own state changed, their props changed, or their parents updated?

The useful output is not simply a colored picture of the component tree.

It is an explanation of where rendering time went.

### 9.1 Flamegraphs and rendering cost

Imagine a profile showing that `SearchPage` updated after every keystroke.

The expensive subtree is `HotelResults`, containing 500 `HotelCard` components.

Most of those cards received the same hotel data as before.

The results suggest that the search input's state update is causing a broad render cascade.

That is a concrete hypothesis.

The next step is to identify why the cards render and which calculations consume time.

Do not automatically conclude that every rendered component is a problem.

A component that renders in a fraction of a millisecond may be harmless.

A component that performs an expensive calculation hundreds of times may be worth investigating.

### 9.2 React's programmatic Profiler

React also exposes a `<Profiler>` component.

It can measure rendering activity within a selected subtree and report information through an `onRender` callback.

Two particularly useful values are `actualDuration` and `baseDuration`.

`actualDuration` describes the rendering time spent on the subtree for the measured update.

`baseDuration` estimates the cost of rendering the subtree without benefiting from relevant memoization, based on recent component render costs.

These are not the same as complete user-perceived interaction latency.

They do not include every browser layout, paint, network, and scheduling cost.

The callback also provides a phase, allowing you to distinguish initial mounting from updates.

A small profiler can help compare the behavior of a particular subtree before and after optimization.

```tsx
import { Profiler } from "react";

function onRender(
  id: string,
  phase: string,
  actualDuration: number,
  baseDuration: number
) {
  console.log({
    id,
    phase,
    actualDuration,
    baseDuration,
  });
}

function SearchPage() {
  return (
    <Profiler id="hotel-results" onRender={onRender}>
      <HotelResults />
    </Profiler>
  );
}
```

The example assumes `HotelResults` is defined elsewhere.

For controlled performance comparisons, avoid drawing conclusions from one measurement.

Warm up the application, repeat the interaction, and compare equivalent scenarios.

Development builds have additional overhead, and Strict Mode can affect observed execution patterns. For performance decisions, representative production builds and devices provide more reliable evidence.

React's production profiling support requires an appropriate profiling-enabled build rather than assuming the normal production bundle exposes the same measurements.

## 10. Render Counts Are Clues, Not Performance Metrics

A developer adds `console.count("HotelCard render")` to every card.

The console fills with hundreds of messages.

That may indicate unnecessary rendering, but it is not enough to establish user-visible slowness.

Console logging itself has overhead.

Development Strict Mode may cause additional render executions.

And a render can be cheap enough to ignore.

A stronger investigation combines several observations:

The user experiences delayed input.

The React Profiler shows a costly results subtree during that interaction.

The browser Performance panel shows substantial main-thread JavaScript work.

A controlled optimization reduces the measured work and improves the interaction.

Now we have a causal explanation rather than an assumption based on log volume.

The important habit is to build a chain of evidence from the symptom to the suspected mechanism.

## 11. `React.memo`: Skipping Child Rendering

By default, when a parent component renders, React may also render its children.

`React.memo` allows React to skip rendering a memoized component when its props have not changed, subject to React's rendering and optimization behavior.

Consider a hotel card receiving the hotel name, price, and rating.

If those props remain unchanged while an unrelated parent state value changes, memoization may prevent that card from rendering again.

The mechanism is straightforward:

```tsx
import { memo } from "react";

const HotelCard = memo(function HotelCard({
  name,
  price,
}: {
  name: string;
  price: number;
}) {
  return (
    <article>
      <h3>{name}</h3>
      <p>€{price}</p>
    </article>
  );
});
```

React normally compares the previous and next props using `Object.is` for each prop.

But `memo` is a performance optimization, not a semantic guarantee.

A memoized component still re-renders when its own state changes.

It can also re-render when a context it consumes changes.

And React may still decide to render it for other reasons.

### 11.1 The reference-identity trap

Suppose each hotel card receives an options object created inside the parent render.

```tsx
<HotelCard
  hotel={hotel}
  options={{ currency: "EUR" }}
/>
```

The options object is new on each parent render.

Even though its contents are equivalent, its reference identity changes.

For a default shallow comparison, that counts as a changed prop.

Likewise, this creates a new callback:

```tsx
<HotelCard
  hotel={hotel}
  onSelect={() => selectHotel(hotel.id)}
/>
```

If every card receives a newly created function on every update, memoization may fail to skip those cards.

But do not immediately start memoizing everything.

Consider whether the card needs those object and callback props at all.

You may simplify the component interface to accept stable primitive values, or move callback creation to a more appropriate boundary.

**A stable component interface can be more valuable than additional memoization machinery.**

## 12. `useMemo`: Caching a Calculation

Suppose filtering hotel results is expensive.

The application has a large array of hotels, and the filtering process performs substantial computation.

If unrelated state changes, recalculating the same filtered result may be unnecessary.

`useMemo` can cache the result of a calculation until its dependencies change.

```tsx
const visibleHotels = useMemo(() => {
  return filterHotels(hotels, filters);
}, [hotels, filters]);
```

React compares the dependencies using `Object.is`.

If they remain equivalent, React can reuse the cached result.

But several qualifications matter.

First, the calculation should be pure.

Second, the dependencies must represent every reactive value needed by the calculation.

Third, if `filters` is a newly created object on every render, the cached result may be invalidated unnecessarily.

Fourth, memoization does not reduce the cost of the first calculation.

And fifth, React may discard memoized values under particular circumstances. The application must remain correct if the calculation executes again.

### 12.1 Memoization is not state ownership

Do not store essential mutable state inside `useMemo`.

It is not a replacement for `useState` or `useRef`.

Use it to optimize the calculation of a value from existing inputs.

If the application requires persistent user edits, those edits need appropriate state ownership.

### 12.2 The algorithm may be the real problem

Suppose filtering 5,000 hotels requires an expensive nested comparison against another collection.

Memoizing the result may reduce unnecessary repeated calculations.

But every meaningful filter change still requires running the expensive algorithm.

If the algorithm is fundamentally inefficient, memoization merely reduces how often the inefficiency is encountered.

A better data structure, a precomputed index, server-side filtering, or a changed search strategy may deliver a larger improvement.

This is the same distinction we encounter in database performance engineering.

Caching an expensive query is not automatically a substitute for fixing its execution plan.

## 13. `useCallback`: Stabilizing Function Identity

`useCallback` caches a function definition between renders while its dependencies remain unchanged.

Its main value is preserving function identity when that identity matters.

Consider a memoized hotel card receiving an `onSelect` callback.

If the parent creates a new callback every time it renders, the child receives a changed prop.

The parent can create a stable callback:

```tsx
const handleSelect = useCallback((hotelId: string) => {
  setSelectedHotelId(hotelId);
}, []);
```

The card then receives that callback and calls it with its own hotel ID.

Because React state-setter functions have stable identities, this particular callback does not need to capture a changing state value.

The dependency array can therefore remain empty.

### 13.1 Be careful with closures

Suppose a callback reads the current selected hotel and performs some operation based on it.

If you omit that changing dependency, the callback can retain an older value.

You have traded a rendering concern for a correctness bug.

One solution may be to include the dependency.

Another may be to express the operation as a functional state update, when appropriate.

The right choice depends on what the callback needs to do.

`useCallback` is not permission to ignore JavaScript closure semantics.

Those semantics remain exactly as important as they were in SE250-L01 and L02.

### 13.2 The three memoization tools answer different questions

`React.memo` asks whether a component render can be skipped when props are unchanged.

`useMemo` asks whether a calculation result can be reused.

`useCallback` asks whether a function identity can be reused.

They often appear together, but there is no requirement to use all three.

If your application does not have a measured problem that benefits from preserving those identities, ordinary code is generally clearer.

## 14. The Dangerous Custom Comparison Function

`React.memo` accepts an optional comparison function.

This can appear attractive when a component receives complicated objects.

A developer might compare only the hotel ID and price, ignoring every other prop.

That can produce subtle defects.

Suppose the component also receives an `onReserve` callback.

The parent creates a new callback when the selected booking dates change.

A custom comparison function ignores the callback because the hotel ID and price remain unchanged.

React skips rendering the component.

The component retains the older callback.

When the customer clicks Reserve, that callback may submit the previous dates.

The optimization has created a stale-closure bug.

This is especially dangerous because the interface can look entirely correct.

The displayed dates might be rendered elsewhere, while the button silently retains historical behavior.

Custom comparison functions must account for all props that can affect output or behavior, including functions.

Deep equality comparisons can also become more expensive than simply rendering the component.

**A performance optimization that changes correctness is not an optimization. It is a defect with a benchmark.**

## 15. React Compiler: What It Actually Changes

React Compiler is a build-time optimizer that can automatically memoize React components and calculations.

Unlike manual memoization, it analyzes the code and introduces suitable caching behavior during compilation.

For many ordinary applications, this reduces the need to explicitly write `React.memo`, `useMemo`, and `useCallback`.

But there are important boundaries.

### 15.1 The compiler is optional

Using a modern React version does not necessarily mean your application is configured to use React Compiler.

It must be enabled through supported build tooling.

The actual installation and configuration depend on the framework, bundler, and compiler version.

Do not assume an application is compiler-optimized merely because it uses React 19 or later.

### 15.2 The compiler depends on correct React code

React Compiler relies on assumptions about component purity, immutable props and state, and the Rules of Hooks.

If code violates these constraints, the compiler may skip optimizing the affected component or hook.

It cannot safely preserve the semantics of every arbitrary mutation while also reusing previous results.

This is a strong reason to learn the React execution model independently.

Compiler-aware development still requires understanding snapshots, identity, dependencies, and side-effect boundaries.

### 15.3 Manual memoization still has a place

React's current guidance generally encourages relying on the compiler for ordinary memoization when it is enabled, while retaining manual controls for situations requiring more precise behavior.

Existing memoization should not be removed indiscriminately.

Changing it can affect compiler output or performance characteristics.

A safe migration uses linting, compiler diagnostics, tests, and profiling.

### 15.4 What the compiler cannot solve

Imagine a component rendering 10,000 hotel cards.

The compiler may help skip unnecessary repeated calculations.

But if the user genuinely needs to render a different set of 10,000 elements, substantial work remains.

The compiler does not eliminate the cost of DOM creation, layout, or painting.

It cannot turn a fundamentally expensive sorting algorithm into a cheap one.

It does not automatically debounce external requests.

And it cannot repair a wrong server-state cache key or a stale reservation callback caused by faulty application logic.

**Automatic memoization reduces bookkeeping. It does not eliminate engineering judgment.**

## 16. State Placement Can Beat Memoization

Let's reconsider our hotel-search page.

The search input lives in the same component that renders all hotel results.

Every keystroke updates parent state.

This causes a broad rendering update.

One possibility is to apply memoization to the entire result subtree.

Another is to move the input's transient state into a smaller component and communicate only committed or appropriately scheduled search changes.

The second approach may reduce the scope of urgent updates.

For example, the input could own its immediate text value.

A separate state value could represent the query used for expensive results processing.

This separation can be achieved through deliberate component architecture or React's scheduling APIs.

But be careful not to create two sources of truth accidentally.

If the input and result query can diverge, their relationship must be intentional.

This is an instance of a broader principle:

**The component that owns a state update determines how much of the tree may be affected by that update.**

Before optimizing children, inspect the state boundary that triggers their work.

## 17. Transitions: Prioritizing Updates

React's `useTransition` and `startTransition` APIs allow certain updates to be treated as non-urgent.

Consider typing into a hotel-search field while updating an expensive result list.

The text input should remain responsive.

The result list can tolerate a short delay.

An appropriate design can update the input state urgently and schedule the result-query update as a transition.

```tsx
const [input, setInput] = useState("");
const [query, setQuery] = useState("");
const [isPending, startTransition] = useTransition();

function handleChange(value: string) {
  setInput(value);

  startTransition(() => {
    setQuery(value);
  });
}
```

The input uses `input`.

The expensive results view uses `query`.

React can prioritize the input update over interruptible transition rendering work.

The `isPending` value can help communicate that transition work is pending.

### 17.1 Transitions do not make work free

If rendering the results takes substantial CPU time, it still costs CPU time.

Transitions help React schedule rendering work so that urgent interactions can remain responsive.

They do not move arbitrary JavaScript computation to another thread.

They also cannot be used to control a text input directly.

The controlled text input should update from urgent state.

### 17.2 The synchronous work trap

Suppose an event handler performs an expensive synchronous calculation before calling `startTransition`.

The main thread is already blocked.

React cannot retroactively make that calculation interruptible.

Likewise, placing a long-running synchronous operation inside a transition callback does not automatically transform that JavaScript operation into background work.

Transition scheduling applies to React state updates and their rendering work.

It is not a general-purpose worker system.

### 17.3 Asynchronous boundaries matter

The state updates marked as transitions are subject to React's documented scheduling rules.

If code awaits an asynchronous operation and later performs another state update, that later update may need its own `startTransition` call to receive transition treatment.

Do not assume that an entire arbitrary asynchronous function automatically remains one transition.

The precise behavior should be verified against the React version being used.

## 18. `useDeferredValue`: Letting Results Lag Behind Input

React also provides `useDeferredValue`.

Suppose we have one state value representing the current search text.

We can derive a deferred version of that value.

The input renders from the immediate value.

The results view renders from the deferred value.

```tsx
const [query, setQuery] = useState("");
const deferredQuery = useDeferredValue(query);
```

If the user types rapidly, React can keep displaying results for an earlier query while preparing the new results.

This can improve perceived responsiveness because the input does not have to wait for the expensive results update.

### 18.1 Deferred does not mean debounced

Debouncing waits for a period of inactivity before performing an operation.

Deferred rendering is a scheduling mechanism.

`useDeferredValue` does not introduce a fixed delay and does not itself prevent additional network requests.

If your concern is that every keystroke triggers an expensive API call, you still need an appropriate request policy, such as debouncing, caching, cancellation, or server-side search behavior.

These mechanisms solve different problems.

### 18.2 Old results should look old

If the visible list is based on a deferred query, it may temporarily describe an earlier search.

That can be acceptable, but the UI should avoid presenting historical results as unquestionably current.

For example, the application can visually indicate that the result list is updating.

This is not merely aesthetic polish.

It communicates an intentional difference between the current input and the data presently being displayed.

## 19. Virtualization: Don't Render What Nobody Can See

Suppose the hotel search returns 5,000 results.

Even after memoization, the page contains thousands of DOM elements.

The browser must maintain their structure, calculate layout, and potentially handle significant memory and styling work.

Virtualization changes the problem.

Instead of rendering all 5,000 rows, the application renders only the rows currently visible in the viewport, usually with a small overscan region.

As the user scrolls, the rendered window changes.

The user can still navigate through the full logical list.

But the DOM contains far fewer active row elements.

This approach is useful for large tables, lists, logs, and other repetitive collections.

### 19.1 Virtualization has costs

Virtualized lists need careful handling of row heights, scroll position, keys, keyboard navigation, focus, and accessibility.

Variable-height content can complicate measurement.

Automated tests may need to account for the fact that off-screen rows do not exist in the DOM.

And virtualizing a list does not solve an expensive filtering algorithm that still processes every item synchronously.

The correct strategy may combine efficient filtering with virtualization.

But do not install a virtualization library because a list contains fifty inexpensive rows.

The added complexity should be justified by measured behavior.

## 20. Suspense: Coordinating Loading Boundaries

React Suspense allows a part of the interface to display fallback content while a descendant is not yet ready to render.

One straightforward use case is lazy-loading component code.

Suppose the hotel-details page includes a large interactive map that is not needed on the search page.

React's `lazy` can defer loading that component until it is required.

Suspense can display an appropriate fallback while the component code is loading.

```tsx
import { lazy, Suspense } from "react";

const HotelMap = lazy(() => import("./HotelMap"));

function HotelDetails() {
  return (
    <Suspense fallback={<p>Loading map…</p>}>
      <HotelMap />
    </Suspense>
  );
}
```

The example assumes `HotelMap` is a default export.

### 20.1 Suspense is not a generic loading detector

A common misconception is that wrapping a component in Suspense automatically detects every asynchronous operation inside it.

It does not.

A fetch started inside an ordinary `useEffect` does not automatically activate the nearest Suspense boundary.

Suspense works with mechanisms that explicitly suspend rendering, such as lazy component loading or supported Suspense-enabled data sources.

Framework-integrated data loading and compatible query-library APIs can participate in Suspense.

But the relationship must be designed.

### 20.2 Loading boundaries are UX boundaries

A Suspense boundary determines which part of the interface may temporarily display fallback content.

If the entire booking page sits under one enormous boundary, a small delayed dependency may replace the whole page with a spinner.

More carefully placed boundaries can preserve useful content while one section loads.

For example, the hotel title and reservation summary might remain visible while an interactive map loads separately.

The choice is not purely technical.

It defines what the user sees while different parts of the interface become available.

## 21. Error Boundaries: Containing Rendering Failures

Now imagine a hotel details widget that crashes while rendering malformed data.

Without an appropriate error boundary, the failure may cause a much larger part of the React interface to disappear.

An error boundary allows a subtree to display fallback UI when a descendant throws during rendering.

This can preserve the rest of the application.

For example, a recommendations widget might fail while the booking controls remain usable.

### 21.1 Error boundaries are not universal exception handlers

An error boundary does not automatically catch errors from ordinary event handlers, unrelated asynchronous callbacks, or every failed network request.

It also has specific limitations around server rendering and errors thrown by the boundary itself.

A network request that rejects inside an Effect does not magically become a rendering error handled by the nearest boundary.

The application must represent asynchronous failures through the appropriate state or error-handling mechanisms.

### 21.2 Boundary placement follows failure isolation

A single root error boundary can prevent a complete blank page in some situations.

But it may still replace too much of the interface.

Smaller boundaries around independently recoverable features can improve resilience.

Consider a hotel booking page containing a map, reviews, recommendations, and reservation controls.

A broken recommendations widget should not necessarily destroy the reservation interface.

This is similar to fault isolation in backend systems.

We cannot guarantee that every component will always work.

We can design boundaries so that one failure does not unnecessarily take down the whole experience.

## 22. React Testing Library: Test the Interface Contract

Let's change focus from performance to correctness.

In SE240-L06, we discussed testing confidence and the danger of testing isolated implementation details.

React Testing Library applies that philosophy to React components.

Instead of inspecting component instances or private state variables, tests interact with rendered DOM elements.

They look for buttons, inputs, headings, alerts, and other user-visible structures.

A test might type into the hotel search field and verify that appropriate results appear.

Or it might click Reserve and verify that a confirmed reservation is displayed only after the backend operation succeeds.

### 22.1 Prefer queries reflecting user interaction

Testing Library encourages queries such as `getByRole` and `getByLabelText`.

These often align with accessible interfaces.

For example, querying a button by its accessible name tests something closer to what a user or assistive technology encounters.

A test that locates an element through an internal class name or implementation-specific component structure is often more brittle.

That doesn't make `data-testid` forbidden.

It remains useful when semantic queries are impractical.

But implementation details should not be the default testing interface.

### 22.2 `userEvent` versus low-level events

The `user-event` library simulates interactions through a sequence of DOM events resembling user actions.

Typing into a field involves more than dispatching one arbitrary change event.

The browser may focus the element, update its value, and dispatch keyboard and input events.

`userEvent` models these interactions more comprehensively than directly triggering one event with `fireEvent`.

This can expose bugs related to focus, disabled controls, and event ordering.

It is still a simulation, not a substitute for testing in a real browser.

For full browser behavior, use tools such as Playwright, as discussed in SE240-L06 and SE215-L07.

## 23. Asynchronous Testing Without Arbitrary Sleeps

Consider our stale hotel-price race.

A test that waits exactly 500 milliseconds and then checks the interface is fragile.

It assumes a particular timing relationship.

That relationship can change under CI load, slower hardware, or implementation changes.

Testing Library provides asynchronous queries and utilities such as `findBy` and `waitFor`.

These allow tests to wait for expected conditions rather than an arbitrary delay.

But there is an even better approach for testing races.

Control the asynchronous operations directly.

Instead of waiting for real network requests, create promises whose completion the test can trigger.

Start request A.

Start request B.

Resolve B.

Assert that B appears.

Resolve A.

Assert that B remains visible.

Now the test reproduces the actual failure condition deterministically.

### 23.1 Test the invariant, not the implementation

A weak race test might assert that an Effect ran twice.

But perhaps the implementation later changes to TanStack Query.

The number and structure of Effects may change without altering correct behavior.

A stronger test asserts:

> After selecting Hotel B, an obsolete Hotel A response must not replace B's displayed quote.

That requirement survives architectural refactoring.

The best tests describe externally meaningful behavior.

## 24. Testing Component Identity Bugs

React component identity creates another distinctive class of test failures.

Suppose a list of guests uses array indexes as keys.

The user edits Bob's note and removes Alice.

The note may now appear under the wrong guest because component identity followed position rather than the guest ID.

A test can reproduce this directly.

Render the list.

Enter a note for Bob.

Remove Alice.

Assert that Bob still has the note and Charlie does not.

The test doesn't need to inspect React's reconciliation algorithm.

It simply verifies that data remains associated with the correct user-visible entity.

This is an excellent example of how understanding React internals improves testing.

You know which failure conditions are worth reproducing because you understand the mechanism.

## 25. Testing Error Boundaries and Failure States

An application can render correctly under normal data but crash when a particular API field is missing.

A useful test deliberately supplies malformed or unexpected data.

Does the component handle the condition gracefully?

If a descendant throws during rendering, does the appropriate error boundary display a meaningful fallback?

Does the rest of the booking page remain usable?

For asynchronous data, tests should distinguish loading, success, failure, and retry behavior.

A query failure should not silently present an old price as though it were a current confirmed quote.

A failed reservation should not display success.

A retry button should actually attempt recovery.

These are meaningful product contracts.

They are considerably more valuable than tests asserting that a component contains a particular internal state variable.

## 26. Testing Performance: What Unit Tests Cannot Prove

Should we write a test that asserts rendering takes less than twenty milliseconds?

Usually, not in an ordinary component-test environment.

Timing measurements depend heavily on hardware, runtime, instrumentation, background activity, and environment.

A threshold that passes on a fast developer machine may fail unpredictably in CI.

Likewise, jsdom does not implement the browser's complete layout and rendering pipeline.

It cannot faithfully measure layout, paint, or actual visual smoothness.

React Testing Library can verify behavioral correctness.

The React Profiler can help investigate rendering work.

The browser Performance panel can expose main-thread activity and rendering costs.

A representative browser performance test can measure user-facing interactions under controlled conditions.

These approaches complement one another.

Do not confuse them.

### 26.1 Performance regression protection

For an expensive interaction, you can establish a repeatable browser-level benchmark with a representative dataset and environment.

Measure the baseline.

Implement a targeted change.

Repeat the measurement.

Compare distributions rather than relying on one run.

If the improvement matters, preserve the scenario as an appropriate regression benchmark.

But avoid building a giant benchmark suite for every trivial component.

Performance testing should concentrate on interactions where regressions meaningfully affect users.

## 27. A Production Investigation Procedure

Let's return to the hotel-search incident.

The user experiences a delay after typing each character.

The team suspects React rendering.

What should the investigation look like?

### Step 1 — Reproduce under representative conditions

Use a realistic hotel dataset.

Record the input interaction with the React Profiler and browser Performance panel.

Consider testing on hardware closer to ordinary customer devices rather than relying exclusively on a powerful development laptop.

### Step 2 — Separate the time

Determine whether the delay is caused primarily by React render calculations, commit work, browser layout and paint, or unrelated JavaScript.

Do not assume React is responsible for the entire interaction.

### Step 3 — Identify the expensive subtree

Look for a large component subtree rendering after every input update.

Determine whether its props and data actually change.

Inspect expensive calculations and object identities.

### Step 4 — Form a minimal hypothesis

For example:

> Search input state is owned by the results-page parent, causing hundreds of hotel cards to recalculate unchanged values after each keystroke.

This is a claim we can test.

### Step 5 — Change one meaningful factor

Perhaps move transient input state into a smaller component.

Perhaps memoize an expensive derived result.

Perhaps stabilize props to a memoized child.

Perhaps virtualize the list.

Do not combine ten optimizations before measuring.

Otherwise, you lose the ability to identify which change mattered.

### Step 6 — Verify correctness

The search results must remain accurate.

Selections must still work.

Guest data must remain associated with the correct entities.

Async requests must still obey current selection.

Optimization should not introduce stale closures or incorrect cache behavior.

### Step 7 — Compare performance

Repeat the same interaction under similar conditions.

Compare rendering work and browser responsiveness.

If the change is negligible, reconsider whether the additional complexity is justified.

### Step 8 — Preserve useful tests

Add behavioral tests for the failure modes most likely to regress.

If the optimization changed rendering architecture, test interactions that depend on state preservation and callback correctness.

The conclusion should be evidence-based:

> We identified repeated expensive hotel-card rendering triggered by input state updates. We reduced unnecessary work and verified that the interaction improved without breaking search behavior.

That is a much stronger engineering explanation than:

> We added `useMemo` because React was slow.

---

# The Oral Examination

Answer every question aloud before proceeding to the solutions.

## Question 1 — The Expensive List

A search component renders 800 hotel cards.

Typing into an input causes every card's render function to execute.

Most cards receive unchanged hotel data.

Does this prove the browser recreated 800 DOM nodes?

What would you measure next?

## Question 2 — Memoization Failure

A parent wraps `HotelCard` in `React.memo`.

Each card receives `onSelect={() => selectHotel(hotel.id)}`.

The cards still re-render during unrelated parent updates.

Explain why.

Give two reasonable architectural corrections.

## Question 3 — The Comparator Bug

A memoized reservation button uses a custom comparison function that checks only hotel ID and price.

The parent changes booking dates and passes a new `onReserve` callback.

The button retains the previous callback.

Explain why this can cause a stale-date reservation.

## Question 4 — `useMemo` Versus `useCallback`

Explain the distinct purposes of `React.memo`, `useMemo`, and `useCallback`.

Would you add all three to a simple static heading component?

Why or why not?

## Question 5 — React Compiler

Does enabling React Compiler remove the need to understand render purity, state identity, and dependencies?

Can it solve an inefficient algorithm or a 10,000-row DOM problem?

What should you verify before relying on compiler optimizations?

## Question 6 — Transitions

A developer places an expensive synchronous calculation inside a `startTransition` callback.

The application still freezes.

Why?

What does transition scheduling actually affect?

## Question 7 — Deferred Search

A search input uses `useDeferredValue` for the results list.

Will this automatically reduce the number of network requests?

What is the difference between deferred rendering and debouncing?

## Question 8 — Suspense and Errors

A component fetches data inside `useEffect`.

A developer wraps it in `<Suspense fallback={<Spinner />}>`.

Will Suspense automatically show the fallback while the Effect's fetch is pending?

Would an Error Boundary automatically catch a rejected promise from an unrelated event handler?

## Question 9 — Testing the Race

A customer selects Hotel A and then Hotel B.

Hotel B's response arrives first, followed by A's.

Design a deterministic React Testing Library test that catches the stale-result bug.

What should the test assert?

## Question 10 — The Production Incident

Your team reports that a hotel-search input has 400 milliseconds of perceived delay.

React DevTools shows substantial rendering work, but browser DevTools also shows a long layout phase.

How would you investigate without prematurely deciding that `React.memo` is the solution?

---

# Solutions and Discussion

## Solution 1 — The Expensive List

No. Component rendering does not imply equivalent DOM mutation.

React may calculate new element descriptions while ultimately committing only a small number of DOM changes.

Measure the React rendering cost, inspect which components and calculations are expensive, and correlate this with browser main-thread activity.

## Solution 2 — Memoization Failure

The parent creates a new function object during each render.

That changes the callback prop's reference identity, defeating the default shallow comparison used by `memo`.

Possible corrections include providing a stable callback that receives a hotel ID or restructuring the state boundary so unrelated updates do not render the list.

Do not automatically introduce `useCallback` if a simpler component design removes the problem.

## Solution 3 — The Comparator Bug

The custom comparison function ignores a behaviorally important prop.

React skips rendering the child even though its callback changed.

The child may continue using the callback from an earlier render, which captured previous booking dates.

The comparator is incorrect because it treats behaviorally different props as equivalent.

## Solution 4 — Memoization Tools

`React.memo` can skip component rendering when props are unchanged.

`useMemo` caches calculation results.

`useCallback` preserves function identity.

A simple static heading generally needs none of these unless profiling demonstrates an unusual problem.

With React Compiler enabled, many routine memoization opportunities can be handled automatically.

## Solution 5 — React Compiler

No.

The compiler depends on correct React semantics and can skip code it cannot safely optimize.

It does not eliminate DOM costs, inefficient algorithms, or invalid state architecture.

Verify that the compiler is configured, inspect relevant diagnostics, preserve correctness tests, and profile representative interactions.

## Solution 6 — Transitions

React transitions schedule state updates and related rendering with non-urgent priority.

They do not automatically interrupt an arbitrary synchronous JavaScript calculation already blocking the main thread.

The calculation may need algorithmic optimization, chunking, a worker, or another architectural change.

## Solution 7 — Deferred Search

No.

`useDeferredValue` can allow rendering work to lag behind urgent updates.

It does not itself debounce or eliminate network requests.

Debouncing delays an operation according to an explicit timing policy.

These mechanisms may be combined, but they solve different problems.

## Solution 8 — Suspense and Errors

No.

Ordinary fetch requests started in Effects do not automatically activate Suspense.

A supported suspending resource is required.

Error Boundaries do not automatically catch errors thrown by ordinary event handlers or unrelated asynchronous callbacks.

Those failures require appropriate handling.

## Solution 9 — Testing the Race

Inject or mock a controllable data-loading function.

Render Hotel A, switch to Hotel B, resolve B's request, and verify B's information appears.

Then resolve A's request and verify that B's information remains visible.

The test should assert the user-visible invariant rather than the number of Effect calls.

## Solution 10 — The Production Incident

Record the interaction with both React DevTools and the browser Performance panel.

Identify the rendering calculations, DOM mutations, layout work, and any synchronous operations contributing to the delay.

Form separate hypotheses for each meaningful cost.

Apply targeted changes and measure them independently.

Memoization may reduce render calculations but will not necessarily solve layout costs or excessive DOM size.

---

# The Mental Model Worth Keeping

When a React interface feels slow, separate three questions:

**What work is happening? Why is that work happening? Can the work be eliminated, reduced, deferred, or performed elsewhere?**

Profiling identifies where time goes.

Component architecture determines which updates affect which subtrees.

Memoization avoids repeated calculations when inputs are unchanged.

Transitions help prioritize urgent interactions.

Virtualization reduces the number of rendered elements.

Testing verifies that these changes preserve correctness.

React Compiler can automate many memoization decisions, but it does not remove the need to understand the application.

**Measure first. Change the mechanism responsible. Verify both performance and behavior.**

---

# Next Lecture — SE250-L05: React in Production — SPAs, Next.js, and Server Rendering

We now understand React's component execution model, Effects, state architecture, and performance diagnostics.

But so far, most of our discussion has assumed an application rendered primarily in the browser.

Production React applications can use several different rendering and delivery architectures.

A conventional single-page application loads JavaScript and renders much of its interface on the client.

A server-rendered application can deliver HTML before the browser executes the full client application.

Hydration then connects server-produced markup to client-side interactivity.

Modern React frameworks also support Server Components, streaming, and more sophisticated boundaries between server and client execution.

These mechanisms introduce new architectural questions.

Where should data be fetched?

Which code runs on the server?

Which components require client-side JavaScript?

What causes hydration mismatches?

And when is the additional complexity worthwhile?

SE250-L05 investigates these production deployment and rendering models, with Next.js as a major concrete example.

*The spoken lecture ends here. The following exercises are intended for on-screen investigation rather than continuous audio listening.*

---

# Optional Practical Lab — React Performance and Debugging Studio

## Working Protocol

For each experiment, follow this sequence:

**Predict → Measure → Investigate → Correct → Verify → AI Review.**

Do not optimize a component before identifying the work that matters.

Do not replace correctness tests with performance measurements.

Do not interpret development render logs as authoritative production performance data.

The lab contains deliberately inefficient React code and a deterministic asynchronous race.

## Experiment A — The Expensive Hotel List

### Objective

Create a React application with hundreds of hotel cards.

Every keystroke causes expensive rendering work.

You must identify the expensive subtree and reduce unnecessary work without breaking search functionality.

### Setup

Create a Vite React and TypeScript application.

```bash
npm create vite@latest react-performance-lab -- --template react-ts
cd react-performance-lab
npm install
npm run dev
```

For the initial investigation, use React DevTools Profiler and the browser Performance panel.

### Broken implementation

The application creates 300 stable hotel objects.

Each hotel card performs a deliberately expensive deterministic calculation. The calculation is artificial, so the experiment isolates React's rendering behavior rather than depending on network or browser layout costs.

The work factor can be adjusted to suit the development machine.

```tsx
import { useState } from "react";

type Hotel = {
  id: number;
  name: string;
  price: number;
};

const hotels: Hotel[] = Array.from(
  { length: 300 },
  (_, index) => ({
    id: index + 1,
    name: `Hotel ${index + 1}`,
    price: 100 + (index % 90),
  })
);

function calculateScore(hotel: Hotel) {
  let value = hotel.id;

  for (let i = 0; i < 20_000; i++) {
    value = (value * 33 + i) % 100_003;
  }

  return value % 100;
}

function HotelCard({
  hotel,
  onSelect,
}: {
  hotel: Hotel;
  onSelect: () => void;
}) {
  const score = calculateScore(hotel);

  console.count(`Render hotel ${hotel.id}`);

  return (
    <article>
      <strong>{hotel.name}</strong>
      <span> — €{hotel.price}</span>
      <span> — Score: {score}</span>

      <button onClick={onSelect}>
        Select
      </button>
    </article>
  );
}

export default function App() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] =
    useState<number | null>(null);

  const [dark, setDark] = useState(false);

  const visible = hotels.filter(hotel =>
    hotel.name
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <main
      style={{
        background: dark ? "#222" : "#fff",
        color: dark ? "#fff" : "#222",
      }}
    >
      <h1>Hotel Search</h1>

      <label>
        Search hotels
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </label>

      <button
        onClick={() => setDark(previous => !previous)}
      >
        Toggle theme
      </button>

      <p>Selected: {selected ?? "None"}</p>

      {visible.map(hotel => (
        <HotelCard
          key={hotel.id}
          hotel={hotel}
          onSelect={() => setSelected(hotel.id)}
        />
      ))}
    </main>
  );
}
```

### Task 1 — Predict

Before running the app, explain what happens when the customer types one character.

Which component owns the input state?

Which components are likely to render?

Does the expensive score calculation execute again?

Will the same thing happen when only the theme changes?

### Task 2 — Profile

Record these interactions:

1. Initial rendering of the 300 hotels.
2. Typing a character into the search field.
3. Changing the theme.
4. Selecting a hotel.

For each interaction, inspect the React rendering work.

Record the relative cost of the results subtree.

Do not focus on exact milliseconds across different machines.

### Task 3 — Try `React.memo`

Wrap `HotelCard` in `React.memo`.

Repeat the measurements.

Explain why memoization may be ineffective when the parent creates a new `onSelect` callback for every hotel on each render.

### Task 4 — Stabilize callback identity

Refactor `HotelCard` to accept a stable callback that takes the hotel ID as an argument.

The parent should pass the same function identity between renders when possible.

Use `useCallback` if necessary.

Verify that the card remains functionally correct.

Compare the rendering behavior again.

### Task 5 — Investigate state placement

Move the theme toggle into a component with its own local state, or restructure theme ownership so that unrelated updates do not unnecessarily recalculate the hotel list.

Be careful: if the hotel cards themselves consume a changing theme context, they may legitimately need to update.

Your goal is to distinguish unnecessary rendering from rendering required by actual changes.

### Task 6 — Consider alternative strategies

Experiment with deferred search rendering.

Consider whether the filtering calculation itself is expensive enough to justify memoization.

Ask whether rendering all 300 cards is necessary.

If you extend the dataset to several thousand rows, investigate virtualization.

### Acceptance criteria

The application remains correct after optimization.

The selected hotel ID is accurate.

Search results correspond to the entered query.

You can explain which specific optimization reduced which category of work.

You can distinguish first-render cost from subsequent update cost.

Your final explanation must include measurements rather than merely claiming that `memo` made the application faster.

---

# Experiment B — A Deterministic Stale-Response Test

## Objective

Write a test that catches an old hotel-price response overwriting the current selection.

Unlike the performance experiment, this is a correctness investigation.

The response order must be controlled directly rather than depending on arbitrary delays.

### Test dependencies

Install Vitest, React Testing Library, user-event, jest-dom, and jsdom.

```bash
npm install -D vitest jsdom \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom
```

Configure Vitest to use jsdom and a setup file.

The following `vite.config.ts` provides a minimal setup.

```tsx
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/setupTests.ts"],
  },
});
```

The setup file imports the jest-dom matchers.

```ts
import "@testing-library/jest-dom/vitest";
```

Save this as `src/setupTests.ts`.

### Broken component

Create `src/HotelQuoteView.tsx`.

This component does not protect itself from obsolete asynchronous responses.

```tsx
import { useEffect, useState } from "react";

export type HotelId = "A" | "B";

export type Quote = {
  hotelId: HotelId;
  price: number;
};

type Props = {
  loadQuote: (hotelId: HotelId) => Promise<Quote>;
};

export function HotelQuoteView({
  loadQuote,
}: Props) {
  const [hotelId, setHotelId] =
    useState<HotelId>("A");

  const [quote, setQuote] =
    useState<Quote | null>(null);

  useEffect(() => {
    loadQuote(hotelId).then(setQuote);
  }, [hotelId, loadQuote]);

  return (
    <main>
      <h1>Hotel {hotelId}</h1>

      <button onClick={() => setHotelId("A")}>
        Hotel A
      </button>

      <button onClick={() => setHotelId("B")}>
        Hotel B
      </button>

      <p>
        Price: {quote ? `€${quote.price}` : "Loading"}
      </p>

      <p>
        Quote belongs to:{" "}
        {quote?.hotelId ?? "None"}
      </p>
    </main>
  );
}
```

### Controlled-promise helper

Create `src/deferred.ts`.

The helper creates a promise whose resolution is controlled by the test.

```ts
export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;

  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}
```

### Test implementation

Create `src/HotelQuoteView.test.tsx`.

The test starts with Hotel A, switches to Hotel B, resolves B first, and then resolves A.

The expected invariant is that Hotel B remains displayed after the obsolete response arrives.

```tsx
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import {
  HotelQuoteView,
  type HotelId,
  type Quote,
} from "./HotelQuoteView";

import { deferred } from "./deferred";

it("never shows an obsolete hotel's quote", async () => {
  const user = userEvent.setup();

  const requestA = deferred<Quote>();
  const requestB = deferred<Quote>();

  const loadQuote = (hotelId: HotelId) => {
    return hotelId === "A"
      ? requestA.promise
      : requestB.promise;
  };

  render(<HotelQuoteView loadQuote={loadQuote} />);

  await user.click(
    screen.getByRole("button", { name: "Hotel B" })
  );

  await act(async () => {
    requestB.resolve({
      hotelId: "B",
      price: 240,
    });
  });

  expect(
    screen.getByText("Price: €240")
  ).toBeInTheDocument();

  await act(async () => {
    requestA.resolve({
      hotelId: "A",
      price: 180,
    });
  });

  expect(
    screen.getByRole("heading", { name: "Hotel B" })
  ).toBeInTheDocument();

  expect(
    screen.getByText("Price: €240")
  ).toBeInTheDocument();

  expect(
    screen.getByText("Quote belongs to: B")
  ).toBeInTheDocument();
});
```

### Tasks

First, predict whether the test passes with the broken implementation.

Then run it:

```bash
npx vitest run
```

Inspect the failure.

Explain why the test is deterministic even though the component is asynchronous.

Fix the component using Effect cleanup and an appropriate stale-response guard.

Also ensure that a quote belonging to Hotel A cannot temporarily appear as Hotel B's current quote while B is loading.

Run the test again.

Then extend it with an additional scenario in which the user switches A to B to A and the requests complete in an unexpected order.

### Acceptance criteria

The test fails against the broken implementation.

It passes after the correction.

No arbitrary `setTimeout` sleeps are used to establish request order.

The test asserts visible behavior rather than the number of Effect executions.

The corrected component remains safe when obsolete responses complete after newer ones.

---

# Experiment C — Identity Regression Test

## Objective

Write a test for a keyed guest list.

The user types a note for Bob, removes Alice, and expects Bob's note to remain associated with Bob.

Use the guest-list implementation from SE250-L01 or create a small equivalent component.

Initially use array indexes as keys.

Then write a React Testing Library test that:

1. Renders Alice, Bob, and Charlie.
2. Types a unique note into Bob's field.
3. Removes Alice.
4. Asserts that Bob still owns his note.
5. Reorders the remaining guests.
6. Asserts that the note still belongs to Bob.

Your test should fail with index keys when component-local state becomes associated with the wrong row.

Then replace index keys with stable guest IDs.

Verify that the test passes.

### Acceptance criteria

The test uses accessible labels or roles to locate the fields.

It does not inspect internal React state.

It verifies the user-visible association between a guest and their note.

You can explain why stable keys correct the identity mapping.

---

# Experiment D — Error Boundary Investigation

## Objective

Contain a rendering failure without destroying the entire booking page.

Create a hotel recommendations component that throws during rendering when it receives deliberately malformed data.

Place it next to a reservation summary.

First, render both without an error boundary.

Observe the failure.

Next, implement an error boundary around only the recommendations subtree.

A native React error boundary can be implemented with a class component using `getDerivedStateFromError`.

Alternatively, a suitable error-boundary library can provide a reusable abstraction.

### Tasks

Verify that malformed recommendations cause the recommendations area to display fallback UI.

The reservation summary should remain available.

Add a retry or reset mechanism appropriate for the component's behavior.

Then deliberately reject a promise from an ordinary event handler.

Explain why the rendering error boundary is not automatically a universal handler for that asynchronous failure.

### Acceptance criteria

The recommendations failure is isolated.

The reservation summary remains usable.

The fallback is meaningful to the user.

The test distinguishes rendering failures from event-handler and asynchronous errors.

---

# Lab Solutions and Diagnostic Notes

**Do not read this section until you have completed your own investigation.**

## Experiment A — Performance Diagnosis

The baseline application places the search state above the entire hotel list.

Every search update causes the parent to render and may cause many hotel cards to execute their expensive calculations again.

Wrapping the cards in `React.memo` may initially have little benefit because the inline `onSelect` callback has a new reference identity on every parent render.

A better callback interface allows the card to receive a stable function and call it with its own hotel ID.

For example, the card can accept:

```tsx
onSelect: (hotelId: number) => void;
```

The parent can define:

```tsx
const handleSelect = useCallback((id: number) => {
  setSelected(id);
}, []);
```

And render:

```tsx
<HotelCard
  key={hotel.id}
  hotel={hotel}
  onSelect={handleSelect}
/>
```

Inside the card, the click handler can call `onSelect(hotel.id)`.

With stable hotel objects and a stable callback, memoization can skip unnecessary card rendering when parent updates do not change relevant props.

However, the filtering operation still determines which cards should be present.

A changed search query may legitimately add or remove cards.

For a large list, virtualization can reduce DOM work further.

For expensive calculations, `useMemo` may help avoid repeated work when inputs are unchanged.

For urgent typing, deferred rendering or transitions may improve responsiveness.

The correct conclusion depends on profiling results.

## Experiment B — Stale Response Correction

The Effect must invalidate the previous request when its dependencies change.

A local ignore flag is sufficient for this controlled exercise.

The quote must also be associated with the current hotel identity when rendered.

```tsx
useEffect(() => {
  let ignore = false;

  loadQuote(hotelId).then(result => {
    if (!ignore) {
      setQuote(result);
    }
  });

  return () => {
    ignore = true;
  };
}, [hotelId, loadQuote]);

const visibleQuote =
  quote?.hotelId === hotelId ? quote : null;
```

The UI should use `visibleQuote`, not the unqualified cached quote.

If it is null, the component should display an appropriate loading state.

This protects against both an obsolete response arriving late and previously loaded data appearing under a newly selected hotel.

## Experiment C — Stable Identity

Array indexes describe positions, not guest identities.

Removing the first guest shifts later guests into different positions and can cause React to reuse component state for the wrong entity.

Stable guest IDs allow the component state to follow the correct guest through removal and reordering.

The regression test should verify this behavior through rendered form fields.

## Experiment D — Error Isolation

A boundary surrounding only the recommendations subtree can render fallback UI when that subtree throws during rendering.

The reservation summary remains outside the failed boundary.

The implementation must still handle ordinary asynchronous and event-handler errors through appropriate mechanisms.

An error boundary is a rendering fault-isolation tool, not a universal exception handler.

---

# Further Reading

1. **React — Profiler API**  
   https://react.dev/reference/react/Profiler

2. **React — `memo`**  
   https://react.dev/reference/react/memo

3. **React — `useMemo`**  
   https://react.dev/reference/react/useMemo

4. **React — `useCallback`**  
   https://react.dev/reference/react/useCallback

5. **React — React Compiler Introduction**  
   https://react.dev/learn/react-compiler/introduction

6. **React — React Compiler Debugging**  
   https://react.dev/learn/react-compiler/debugging

7. **React — Rules of React**  
   https://react.dev/reference/rules

8. **React — `useTransition`**  
   https://react.dev/reference/react/useTransition

9. **React — `useDeferredValue`**  
   https://react.dev/reference/react/useDeferredValue

10. **React — Suspense**  
    https://react.dev/reference/react/Suspense

11. **React — `lazy`**  
    https://react.dev/reference/react/lazy

12. **React — Error Boundaries**  
    https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary

13. **React Testing Library — Introduction**  
    https://testing-library.com/docs/react-testing-library/intro/

14. **Testing Library — user-event**  
    https://testing-library.com/docs/user-event/intro/

15. **Testing Library — Async Methods**  
    https://testing-library.com/docs/dom-testing-library/api-async/

16. **Vitest — Documentation**  
    https://vitest.dev/

Cross-reference SE240-L05 for the browser performance pipeline, SE240-L06 for general testing strategy, SE250-L01 for render and identity semantics, SE250-L02 for asynchronous Effects and stale closures, and SE250-L03 for server-state ownership.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE250-L04 — REACT PERFORMANCE & DEBUGGING
================================================

PERFORMANCE INVESTIGATION
-------------------------
1. Define the slow interaction.
2. Reproduce with realistic data.
3. Profile React rendering.
4. Inspect browser main-thread work.
5. Identify the actual bottleneck.
6. Form a causal hypothesis.
7. Change one meaningful factor.
8. Re-measure.
9. Verify correctness.

THREE DISTINCT LAYERS
---------------------
React render:
  Component execution, calculation,
  reconciliation work.

React commit:
  Apply necessary DOM changes.

Browser rendering:
  Style, layout, paint, compositing.

Render != remount.
Render != DOM mutation.
Render count != performance cost.

REACT PROFILER
--------------
actualDuration:
  Time spent rendering profiled subtree
  for a measured update.

baseDuration:
  Estimated cost without memoization
  benefits based on recent render costs.

phase:
  mount / update / nested-update

Profiler timing != full interaction latency.

REACT.MEMO
----------
Can skip child render when props unchanged.
Default prop comparison uses Object.is.

Defeated by:
- freshly created object props
- freshly created callback props
- relevant prop changes

Does not block:
- child's own state updates
- consumed Context changes

Memoization is not correctness semantics.

USEMEMO
-------
Caches calculation result.

Good:
  expensive pure calculation
  stable dependencies
  demonstrated repeated work

Not:
  state ownership
  general-purpose correctness cache
  automatic first-render acceleration

USECALLBACK
-----------
Caches function identity.

Useful:
  stable callback props
  memoized children
  dependency-sensitive APIs

Dependencies must be correct.
Stale closures remain possible.

CUSTOM MEMO COMPARATORS
-----------------------
Must account for all behaviorally
important props, including functions.

Ignoring callback changes can retain
stale handlers and historical values.

Deep comparison may cost more than render.

REACT COMPILER
--------------
Optional build-time optimizer.
Automatically memoizes many values,
functions, and component updates.

Requires supported configuration.
Benefits from pure React code.
May skip incompatible code.

Does NOT:
- fix wrong state ownership
- repair stale async data
- optimize arbitrary bad algorithms
- eliminate DOM/layout costs
- waive Rules of Hooks

Prefer measured architecture improvements.

STATE PLACEMENT
---------------
Update ownership determines affected tree.

Localize rapidly changing state when useful.
Avoid unnecessary broad render cascades.
Do not duplicate sources of truth casually.

TRANSITIONS
-----------
startTransition:
  Mark suitable state updates non-urgent.

Urgent input update remains urgent.
Expensive result rendering can be deferred.

Transition != Web Worker.
Transition != debounce.
Transition != free computation.

Cannot control text inputs directly
through transition updates.

USEDEFERREDVALUE
----------------
Results may lag behind urgent input.
Background rendering can be interrupted.

No fixed delay.
Does not automatically reduce requests.
Not equivalent to debounce.

VIRTUALIZATION
--------------
Render visible window + overscan.

Useful for:
  large tables
  thousands of list rows
  logs and repetitive collections

Trade-offs:
  variable heights
  focus / keyboard navigation
  accessibility
  scroll stability
  test complexity

SUSPENSE
--------
Coordinates rendering fallbacks for
resources that suspend.

Supports:
  lazy component loading
  Suspense-enabled data sources

Ordinary useEffect fetch does not
automatically activate Suspense.

Boundary placement defines UX.

ERROR BOUNDARIES
----------------
Catch descendant rendering failures.
Show fallback UI for failed subtree.

Do not automatically catch:
  ordinary event-handler errors
  unrelated async callback errors
  all rejected network requests
  server-rendering errors

Place according to fault isolation.

REACT TESTING LIBRARY
---------------------
Test user-observable behavior.

Prefer:
  getByRole
  getByLabelText
  findBy*
  userEvent
  waitFor for expected conditions

Avoid unnecessary:
  internal state assertions
  implementation-specific selectors
  arbitrary sleep-based async tests

DETERMINISTIC RACE TEST
-----------------------
Start request A.
Select B.
Resolve B first.
Assert B visible.
Resolve A afterward.
Assert B remains visible.

Tests behavior, not Effect count.

IDENTITY REGRESSION TEST
------------------------
Edit Bob's note.
Remove Alice.
Reorder remaining guests.
Verify Bob still owns his note.

Stable keys represent actual identity.

PERFORMANCE TEST LIMITS
-----------------------
jsdom does not measure real layout/paint.
CI render timing is environment-sensitive.
Use controlled browser benchmarks for UX.

Correctness tests and performance
measurements are complementary.

INTERVIEW RED FLAGS
-------------------
"Every re-render recreates the DOM."
"React.memo fixes all slow interfaces."
"useMemo makes algorithms faster."
"useCallback eliminates stale closures."
"React Compiler removes need to profile."
"startTransition creates a background thread."
"useDeferredValue debounces API requests."
"Suspense handles every loading state."
"Error boundaries catch every JS exception."
"Passing unit tests proves good INP."

MENTAL MODEL
------------
What work?
Why now?
Which subtree?
Can it be removed?
Can it be reused?
Can it be deferred?
Can it be done elsewhere?
Did the fix measurably help?
Did correctness survive?

NEXT
----
SE250-L05
React in Production:
SPAs, Next.js, and Server Rendering
```
