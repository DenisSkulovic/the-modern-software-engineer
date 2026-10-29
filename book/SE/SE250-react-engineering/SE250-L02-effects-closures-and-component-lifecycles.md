---
id: SE250-L02
course: SE250
title: "Effects, Closures, and Component Lifecycles"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L01
next: SE250-L03
---


# SE250 — React Engineering for Experienced Developers
## Lecture 02: Effects, Closures, and Component Lifecycles

*The hotel page displays the wrong price. Every request succeeded, every component rendered, and the bug is still there.*

---

# Part I — Intuition

## 1. The €240 Room That Somehow Costs €180

Imagine a customer browsing hotels in Amsterdam.

They open Hotel A. The booking interface displays a room priced at €180 per night. They switch to Hotel B, where the price is €240.

For a moment, everything works correctly.

Then the interface changes.

The title still says Hotel B, but the price suddenly becomes €180.

The customer has not switched hotels again. The backend hasn't changed its prices. No exception appears in the console.

Your React application has successfully displayed the wrong information.

You inspect the network requests and discover something interesting.

When the customer selected Hotel A, the frontend requested its price. That request took 1.2 seconds.

A fraction of a second later, the customer selected Hotel B. Its request took only 150 milliseconds.

Hotel B's response arrived first. React displayed €240.

Then Hotel A's older response arrived. React displayed €180.

Both requests succeeded. Both responses contained correct data. The application made an incorrect decision about which response was allowed to update its state.

This is not primarily a networking problem.

It is a **lifetime and synchronization problem**.

The application has allowed work belonging to an old screen state to interfere with the current screen.

To fix it properly, we need to understand React Effects.

## 2. Rendering Is Not Permission to Change the Outside World

In the previous lecture, we established that React calls component functions to calculate an interface.

A component receives props and state, executes ordinary JavaScript, and returns a description of what should appear.

That calculation should be pure.

Given equivalent inputs, rendering should describe the same interface without modifying external systems.

But real applications must interact with the outside world. Our booking page needs to retrieve hotel prices, subscribe to availability updates, and perhaps integrate with a map or third-party reservation widget.

Those operations cannot simply happen every time React calls the component function.

Why?

Because a render might happen more than once. React might restart rendering work or abandon it without committing the result.

If our component opened a WebSocket connection while rendering, React could create connections for interface versions that never appeared on screen.

If the component submitted a reservation while rendering, even an abandoned render could have caused a real business transaction.

We need a boundary between **calculating an interface** and **synchronizing with something outside React**.

That boundary is where Effects enter.

## 3. An Effect Is a Synchronization Agreement

Many React tutorials introduce `useEffect` as a way to run code after rendering.

That description is technically related to its timing but pedagogically dangerous.

It encourages developers to put anything inconvenient into an Effect: calculating totals, responding to clicks, resetting fields, copying state, fetching data, opening connections, and logging analytics.

Soon the application contains dozens of Effects that trigger one another.

A better mental model is this:

**An Effect describes how one external system should stay synchronized with the current committed React state.**

For our hotel page, the agreement might be:

> While Hotel A is selected, retrieve information relevant to Hotel A. If the selection changes to Hotel B, the work associated with Hotel A is no longer authoritative.

For a live availability connection, the agreement might be:

> While the customer is viewing Hotel A, maintain a subscription to Hotel A's availability updates. When they switch hotels, disconnect from A and subscribe to B.

For a browser event listener:

> While this component needs to respond to keyboard shortcuts, register a listener. Remove that listener when the component no longer needs it.

These operations have something in common.

They have a beginning and potentially an ending.

The beginning is **setup**.

The ending is **cleanup**.

### Visual anchor 1 — Synchronization lifetime

```text
Selected hotel: A

Effect A:
  Start synchronization for A
            |
            | Customer selects B
            v
  Stop synchronization for A
            |
            v
Effect B:
  Start synchronization for B
            |
            | Component removed
            v
  Stop synchronization for B
```

The key observation is that the Effect for Hotel A doesn't own the application forever.

It owns a particular synchronization period.

When that period ends, its work must stop influencing the current interface.

## 4. Each Effect Belongs to a Render

Remember React's snapshot model.

When the selected hotel equals A, React renders the component with `hotelId` equal to A.

The Effect created by that render closes over A.

Later, React renders with `hotelId` equal to B and creates a different Effect closure.

The earlier Effect does not automatically forget A.

It may still have an unresolved network request, an active timer, or a registered callback.

This is ordinary JavaScript closure behavior.

The framework cannot make an old promise forget the values captured when it was created.

What React can do is provide a predictable lifecycle for the synchronization process.

When relevant dependencies change, React cleans up the previous Effect before setting up the replacement.

A cleanup function gives us the opportunity to invalidate the old work.

For example, the Effect for Hotel A can maintain a local flag called `ignore`.

When its cleanup runs, it sets `ignore` to true.

If Hotel A's response later arrives, its callback checks the flag and refuses to update the page.

Hotel B's Effect has a different flag belonging to its own execution.

This is important: we are not changing a global variable called `ignore`. Each Effect setup owns its own local closure.

### Visual anchor 2 — Two requests racing

```text
Time ─────────────────────────────────►

Hotel A request
  START ───────────────────── RESPONSE
           \
            \ selection changes
             \
Hotel B       START ─ RESPONSE
                         |
                         v
                    Display €240

Old A response arrives later.
Without protection: display €180.
With cleanup: ignore obsolete result.
```

Network arrival order does not determine business authority.

The application must establish which request still matters.

## 5. Dependencies Declare What Changes the Agreement

How does React know when to replace an Effect?

The developer specifies dependencies.

Imagine a hotel availability subscription that depends on the selected hotel ID.

When the ID changes, the old subscription no longer represents the desired state.

React can therefore stop the old synchronization and start a new one.

If the dependency remains unchanged, the subscription ordinarily does not need to be restarted.

A common misconception is that the dependency array is a list of values we would *prefer* React to watch.

That is not quite right.

The dependency list must account for the reactive values read by the Effect.

If the Effect uses `hotelId`, that value normally belongs in its dependency list.

If the Effect also reads a changing authentication token, that dependency must be accounted for too.

Otherwise, it may continue operating with obsolete credentials.

The rule is not merely about satisfying ESLint.

It is about making the synchronization contract truthful.

A missing dependency means the Effect may continue representing a previous render when it should have been replaced.

An unnecessary unstable dependency means the Effect may restart more often than necessary.

Both can create production bugs.

## 6. The Cleanup Function Is Not an Optional Courtesy

Consider a live availability connection.

Each time the selected hotel changes, the application opens a new connection.

Without cleanup, the old connections remain active.

After visiting ten hotels, the customer might have ten subscriptions delivering updates.

The screen may display contradictory availability messages, the browser may consume unnecessary resources, and the backend may maintain connections that nobody needs.

Closing the previous connection is not merely an optimization.

It is part of the correctness of the feature.

Similarly, timers should be cleared when their synchronization period ends. Event listeners should be removed when no longer needed.

For data fetching, cleanup should prevent obsolete results from altering the interface. It may also cancel underlying work when cancellation is supported.

**Correct setup and correct cleanup are two halves of the same operation.**

## 7. Strict Mode: React Deliberately Exposes Your Mistakes

Now imagine that you've implemented a connection Effect.

You open the application in development and notice that React connects, disconnects, and connects again.

You haven't changed the selected hotel.

What on earth is happening?

React's development Strict Mode can deliberately perform an additional Effect setup-and-cleanup cycle.

This is a stress test.

React is checking whether your synchronization process remains correct when it starts, stops, and starts again.

If your Effect leaks a subscription, the problem becomes more obvious.

If you forgot to clear a timer, you may suddenly see duplicated timer behavior.

Developers sometimes respond by turning off Strict Mode or adding a flag intended to prevent the Effect from running twice.

That often conceals the defect rather than fixing it.

The question should be:

> Can this synchronization safely start, stop, and start again?

If the answer is yes, Strict Mode's additional development work should not break the application.

If the answer is no, investigate why.

A component can mount and unmount during perfectly normal production navigation. Strict Mode is helping you discover assumptions that would eventually fail anyway.

### A quick comprehension check

Suppose an Effect subscribes to hotel availability updates but has no cleanup function.

The customer visits Hotel A, then B, then C.

How many subscriptions might remain active?

Three.

Now suppose we provide correct cleanup and React replaces the subscription whenever the selected hotel changes.

How many should remain active after switching to C?

One.

That is the central idea of this lecture.

**Every Effect should represent a specific synchronization process with a correctly managed lifetime.**

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. The Actual Contract of `useEffect`

Let's formalize the mechanism.

A conventional Effect has a setup function, an optional cleanup function returned by setup, and an optional dependency array.

For example, a component that subscribes to hotel availability can establish the connection when the selected hotel changes and disconnect the old subscription during cleanup.

```tsx
useEffect(() => {
  const connection = connectToHotel(hotelId);

  return () => {
    connection.disconnect();
  };
}, [hotelId]);
```

The code is short, but it describes an entire lifecycle.

When the component commits with its initial hotel ID, React runs the Effect setup.

When a later committed render has different dependencies, React invokes the previous cleanup and then runs the new setup.

When the component unmounts, React invokes the final cleanup.

React compares dependencies using `Object.is`.

Effects run on the client, not during server rendering. We will explore the consequences for SSR and hydration in SE250-L05.

### 8.1 Three dependency arrangements

There are three common arrangements worth distinguishing.

**No dependency array.** The Effect runs after every relevant commit. If it returns cleanup, React cleans up the previous setup before establishing the next one.

**Empty dependency array.** The Effect does not normally re-synchronize because of changing props or state. It still runs after the initial mount, cleans up on unmount, and participates in development Strict Mode checks.

**A dependency array containing reactive values.** The Effect re-synchronizes when one of those dependencies changes.

An empty array is not a magic instruction to "run exactly once."

A component can unmount and mount again. Development checks can repeat setup. A different component instance can be created.

Thinking in terms of a single lifetime synchronization is more accurate than thinking in terms of a one-time function call.

### 8.2 Effects are associated with committed work

React rendering and Effect execution are separate concerns.

The component function calculates an interface. React commits the resulting changes when appropriate. The Effect then participates in synchronization with external systems.

A render that is abandoned before commit must not establish an Effect's external connection.

This distinction matters because React's rendering work does not have to be a one-to-one sequence of function executions and committed interfaces.

Your render function should therefore remain pure.

Do not move external operations into rendering merely because Effects appear inconvenient.

## 9. One Effect, One Synchronization Responsibility

A common mistake is writing one enormous Effect that handles every responsibility on the page.

Our booking component might retrieve hotel prices, subscribe to availability updates, register a keyboard listener, update the document title, and submit analytics events in one Effect.

Those operations do not necessarily share a lifetime.

The price request depends on the hotel ID.

The availability connection may depend on the hotel ID and authentication credentials.

The keyboard listener might be stable for the entire lifetime of the booking component.

The document title is a separate browser synchronization concern.

An analytics event may be associated with navigation rather than arbitrary state changes.

Combining them forces unrelated processes to share the same dependency changes.

For example, a theme change could unexpectedly reconnect the availability WebSocket if the giant Effect also reads the theme.

Instead, divide the processes according to their independent synchronization requirements.

This is similar to designing small services or well-defined responsibilities in a backend system.

The benefit is not aesthetic minimalism.

It is independent lifecycle control.

**An Effect boundary should describe the lifetime of one external relationship.**

## 10. The Stale Hotel Price: Two Problems, Not One

Return to the booking application.

The selected hotel is represented by `hotelId`.

An Effect requests the selected hotel's price and updates the displayed `price` when the response arrives.

A naive implementation might look like this:

```tsx
useEffect(() => {
  fetchHotelPrice(hotelId).then(result => {
    setPrice(result.price);
  });
}, [hotelId]);
```

At first glance, the dependency is correct.

The Effect does run when the hotel ID changes.

But there are two independent problems.

### 10.1 Problem one: The old request remains authoritative

Suppose Hotel A's request is still pending when the customer selects Hotel B.

React creates the new Effect for B.

But the old JavaScript promise still exists.

Without cleanup or another validity mechanism, its callback may eventually call `setPrice`.

The old response can overwrite the new response.

The Effect's dependency array did not prevent this.

Dependencies control the synchronization lifecycle. They do not automatically cancel arbitrary asynchronous JavaScript operations.

### 10.2 Problem two: Old data may be displayed during the transition

Suppose Hotel A's price is already visible.

The customer selects Hotel B.

React renders the page with Hotel B's title, but `price` is still the previous state value until application logic replaces it.

Even with excellent request cleanup, this can temporarily produce an interface containing Hotel B's identity and Hotel A's price.

A common solution is to represent the loaded price together with the identity it belongs to.

For example, store a quote containing both `hotelId` and `price`, then display it only when the quote's ID matches the currently selected hotel.

This ensures that the interface does not mistakenly present a historical quote as current merely because the request for the new hotel has not finished.

We have two separate correctness concerns:

- **Request authority:** Which asynchronous result is still allowed to update state?
- **Display consistency:** Does the data currently being rendered actually belong to the selected entity?

Both matter.

A stale-result guard protects the first.

A well-designed state model protects the second.

## 11. Cleanup with an Ignore Flag

One straightforward approach is to create a local invalidation flag for each Effect execution.

The Effect begins with `ignore` set to false.

When a response arrives, the callback updates state only if `ignore` remains false.

When the Effect is cleaned up, `ignore` becomes true.

```tsx
useEffect(() => {
  let ignore = false;

  async function load() {
    const result = await fetchHotelPrice(hotelId);

    if (!ignore) {
      setQuote({
        hotelId,
        price: result.price,
      });
    }
  }

  void load();

  return () => {
    ignore = true;
  };
}, [hotelId]);
```

Each execution has its own `ignore` variable.

When the hotel changes, cleanup invalidates the previous execution.

The previous request may still finish, but its result is no longer accepted.

This is a practical way to establish an authority boundary.

Notice that the quote also includes the hotel ID. The rendering logic can reject a mismatched quote while waiting for new data.

A robust implementation should also handle loading and error states explicitly rather than allowing rejected promises to become unhandled failures.

We will build a fuller state model in SE250-L03.

## 12. Cancellation with `AbortController`

Ignoring an obsolete result prevents it from changing the UI.

But the underlying request may continue consuming bandwidth, server capacity, and browser resources.

When using `fetch`, we can often cancel the request through `AbortController`.

The Effect creates an AbortController, passes its signal to `fetch`, and calls `abort()` during cleanup.

```tsx
useEffect(() => {
  const controller = new AbortController();

  async function load() {
    try {
      const response = await fetch(
        `/api/hotels/${hotelId}/price`,
        { signal: controller.signal }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const quote = await response.json();

      if (!controller.signal.aborted) {
        setQuote({ hotelId, price: quote.price });
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setError(error);
      }
    }
  }

  void load();

  return () => controller.abort();
}, [hotelId]);
```

This version attempts to cancel obsolete fetch work and prevents updates after cancellation.

The distinction between cancellation and invalidation is important.

An aborted request might already have reached the server.

Aborting a client request does not guarantee that the server undoes its work.

It certainly should not be treated as a transaction rollback.

If the operation creates a reservation or charges a payment method, cancellation on the client is not sufficient to establish business correctness.

Such mutations need appropriate server-side controls, including idempotency and authoritative transaction handling.

That is also why submitting a reservation should ordinarily be driven by the user's explicit submit event, not by an Effect that runs whenever certain state values happen to change.

**Cancellation controls client-side work. It is not a substitute for business transaction semantics.**

## 13. A Dependency Array Is Not a Wish List

Let's examine one of React's most frequently misunderstood concepts.

Suppose our availability subscription uses both `hotelId` and `authToken`.

An engineer specifies only `hotelId` as a dependency.

When the authentication token changes, the Effect does not necessarily reconnect.

The old connection may continue using obsolete credentials.

The missing dependency has made the synchronization contract inaccurate.

React's exhaustive-dependencies lint rule exists to help detect this class of mistake.

It examines reactive values used by Effects and checks whether the declared dependencies reflect them.

Reactive values include props, state, and values or functions declared within the component body.

The dependency array is not an optimization knob to manipulate until the linter stops complaining.

If an Effect reads a reactive value, changing that value may require resynchronization.

### 13.1 Functions and objects can cause unnecessary restarts

Suppose our component creates a new configuration object during each render:

```tsx
const options = {
  hotelId,
  includeAvailability: true,
};

useEffect(() => {
  const connection = connect(options);

  return () => connection.disconnect();
}, [options]);
```

The configuration object is newly created whenever the component renders.

Even if the hotel ID remains unchanged, the object identity differs.

React compares dependencies using `Object.is`, so the Effect may disconnect and reconnect unnecessarily.

A developer might respond by removing `options` from the dependency array.

That hides the cause rather than resolving it.

Instead, create the configuration inside the Effect and depend on the primitive values it genuinely needs.

```tsx
useEffect(() => {
  const connection = connect({
    hotelId,
    includeAvailability: true,
  });

  return () => connection.disconnect();
}, [hotelId]);
```

Now an unrelated change to the component's theme does not require a new availability connection.

This is not simply a memoization trick.

It clarifies the synchronization dependency.

### 13.2 Infinite loops from unstable dependencies

A particularly unpleasant variation appears when an Effect updates state and that state update causes a new dependency value to be created.

The sequence becomes:

The Effect runs, sets state, triggers a render, receives a newly created object or function dependency, runs again, sets state again, and repeats.

React may eventually report excessive update depth.

Adding an empty dependency array can silence the loop, but it may also introduce stale data.

The correct investigation is to identify what external synchronization is required, what reactive values determine it, and whether the state update belongs in an Effect at all.

## 14. Most State Calculations Do Not Need Effects

This may be the most practically valuable section of the lecture.

React codebases frequently contain Effects that exist only because the developer did not know where else to put an operation.

Consider a booking form with nightly price and number of nights.

An engineer writes an Effect that calculates the total and stores it in another state variable.

The component now has three values to maintain: price, nights, and total.

Changing either input causes a render with the old total. After commit, the Effect updates the total, causing another render.

The application has introduced synchronization work where none was required.

The total could simply have been calculated during rendering.

```tsx
const total = nightlyPrice * nights;
```

The broader principle was introduced in SE250-L01 and SE240-L03.

Here, the important observation is that **Effects are not a general-purpose mechanism for keeping React state synchronized with other React state**.

Often, the correct fix for an Effect bug is deleting the Effect.

### 14.1 Resetting state when an entity changes

Another common example is resetting a form whenever `hotelId` changes.

A developer adds an Effect that notices the new hotel ID and clears the guest draft.

But if the product considers each hotel's form a separate component identity, a hotel-specific key may express that requirement more directly.

Alternatively, the parent might own separate drafts for each hotel.

An Effect that repeatedly copies props into local state often creates an unnecessary second source of truth.

State ownership and component identity should be considered before adding synchronization code.

### 14.2 Calculating filtered results

Suppose our booking page stores all available rooms and a price filter.

An Effect calculates `visibleRooms` whenever either changes.

But the filtered list is derived from existing React state.

It can ordinarily be calculated during rendering.

If the calculation is expensive, memoization may be appropriate.

That is a separate performance decision.

An Effect should not become the default substitute for ordinary expressions.

## 15. Events and Effects Answer Different Questions

The distinction between an event handler and an Effect is semantic.

An event handler answers:

> What should happen because this particular interaction occurred?

An Effect answers:

> What external system must remain synchronized with the current committed state?

Consider three hotel-booking operations.

The customer clicks **Reserve now**. That should trigger a reservation submission associated with the explicit interaction.

The customer navigates to a hotel detail page. The application needs to load or maintain data relevant to that page.

The customer changes the number of nights. The total price needs to be recalculated from the current values.

These operations belong to different categories.

Reservation submission belongs to an event-driven mutation path.

Synchronizing the visible hotel with an external data source can belong to an Effect, although production data-fetching infrastructure may offer a better abstraction.

Calculating the total belongs to rendering.

Putting all three into Effects produces a fragile application.

### 15.1 The dangerous `shouldSubmit` flag

Imagine an engineer handles a submit button by setting `shouldSubmit` to true.

An Effect observes this state and sends a reservation request.

Now a business mutation depends on the lifecycle of an Effect.

What happens during remounting, development Strict Mode checks, retries, or unexpected state restoration?

The design has created unnecessary opportunities for repeated submissions.

A direct event handler is generally a better place to initiate an explicit user-requested operation.

Server-side idempotency is still necessary for important financial operations, because duplicate requests can arise for many reasons unrelated to React.

But React should not introduce additional ambiguity about whether the user actually requested an operation.

## 16. Stale Closures in Timers

We have already seen stale values in asynchronous network requests.

Timers provide another useful example.

Suppose a component displays elapsed seconds.

The engineer initializes `seconds` to zero and creates an interval inside an Effect with an empty dependency array.

Every second, the interval calls `setSeconds(seconds + 1)`.

The first tick changes the display from zero to one.

Then the timer appears stuck.

Why?

The interval callback belongs to the render in which `seconds` was zero.

It repeatedly requests the replacement value one.

The value captured by the closure does not automatically update when React renders again.

### 16.1 The functional updater solution

If the interval's purpose is simply to increment the counter, the callback does not need to read the captured `seconds` value.

It can use a functional state update.

```tsx
useEffect(() => {
  const id = setInterval(() => {
    setSeconds(previous => previous + 1);
  }, 1000);

  return () => clearInterval(id);
}, []);
```

The interval is established for the component's relevant lifetime.

Its callback transforms the latest queued state without reading stale captured state.

Cleanup prevents the interval from continuing after unmount.

This is both simpler and more reliable than recreating the interval every time the counter increments.

### 16.2 What if the timer needs changing data?

Suppose the callback also reads the current hotel name or a changing playback speed.

Now the correct design depends on the intended behavior.

If changing the playback speed should recreate the timer with a different interval, the speed belongs in the Effect's dependencies.

If the callback merely needs to read a current informational value without restarting the timer, a different mechanism may be appropriate.

The key is to distinguish values that determine the synchronization lifetime from values that should merely be observed when a callback runs.

## 17. `useRef`: Persistent Mutable Data Without Rendering

React provides another tool called `useRef`.

A ref is an object containing a mutable `.current` property.

The ref object persists between renders of the same component instance.

Changing its `.current` value does not trigger a React render.

This makes it useful for information that must survive between renders but does not itself determine the displayed interface.

Examples include timer IDs, DOM element references, third-party library instances, and certain coordination values.

### 17.1 A ref is not Vue's `ref`

The shared name is unfortunate.

Vue's `ref()` creates a reactive value. Reading its `.value` participates in Vue's dependency-tracking system.

React's `useRef()` creates a persistent mutable container that does not participate in rendering updates when its `.current` changes.

They solve different problems.

In React, if the value determines what should appear on screen, state is usually the appropriate choice.

If it represents an external resource handle or mutable information not used for rendering, a ref may be appropriate.

### 17.2 Refs and DOM access

Suppose a guest-name input must receive focus after a particular operation.

React can associate a ref with the input DOM element.

The ref gives code a way to call browser APIs such as `focus()` when appropriate.

But accessing DOM refs during rendering is generally incorrect.

During the first render, the element may not exist yet. During later renders, React may not have committed the latest DOM changes.

Read or write refs in event handlers or Effects, where the relevant lifecycle expectations are clearer.

### 17.3 Refs are not an excuse to bypass state

Some developers use refs to avoid dependency warnings or prevent renders.

They place business data into mutable containers and then wonder why the UI does not update.

A ref deliberately does not notify React that its contents changed.

If the booking total is stored only in a ref and the component reads it during rendering, changing the ref won't automatically refresh the screen.

Refs are useful precisely because they are not ordinary reactive state.

Use them for the responsibilities they are designed to hold.

## 18. Reading Current Values Without Reconnecting

Modern React also provides `useEffectEvent` for a more specific problem.

Imagine our booking application maintains a live availability connection for the selected hotel.

Whenever the connection succeeds, the application shows a notification using the current theme.

The selected hotel determines which connection should exist.

The theme determines how the notification should appear.

Changing the theme should not disconnect and reconnect the availability subscription.

Yet if the Effect directly reads `theme`, it becomes a reactive dependency.

How do we express the difference?

We can separate the reactive synchronization process from the non-reactive callback that needs to read the latest committed values.

An Effect Event created with `useEffectEvent` can read current props and state when called from Effect-related logic, without making those values dependencies of the surrounding Effect.

```tsx
const onConnected = useEffectEvent(() => {
  showNotification("Availability connected", theme);
});

useEffect(() => {
  const connection = connectToHotel(hotelId);

  connection.on("connected", onConnected);
  connection.connect();

  return () => connection.disconnect();
}, [hotelId]);
```

The connection's lifetime depends on `hotelId`.

The notification callback can read the current `theme` without making theme changes restart the connection.

This solves a real dependency-design problem.

But `useEffectEvent` is not a general escape hatch for suppressing dependency warnings.

It should be used for genuinely non-reactive logic invoked from Effects.

Effect Events must follow their documented calling restrictions, and they should not be passed around as arbitrary callbacks or used as a universal alternative to ordinary event handlers.

They are available in modern React versions, including the React 19.2-and-later API line.

For older React projects, you need to work within the APIs supported by the installed version and choose an appropriate synchronization design.

The important underlying idea remains the same:

**Some values determine when synchronization must restart. Other values are merely needed when an event from that synchronization occurs.**

Those are different responsibilities.

## 19. `useEffect` Versus `useLayoutEffect`

Most external synchronization belongs in ordinary Effects.

But some operations must happen in a narrower timing window.

Suppose a tooltip must measure its rendered dimensions and adjust its position before the user sees it.

If React commits the initial tooltip position, the browser paints it, and an ordinary Effect later measures and moves it, the user might see a visible jump.

React provides `useLayoutEffect` for cases where work needs to happen after DOM mutation but before the browser repaints.

This can be useful for layout measurement and immediate positioning.

However, layout Effects can block painting.

Overusing them can make an application feel slower.

They are not a superior version of `useEffect`.

They serve a different timing requirement.

Use ordinary Effects unless the user-visible problem genuinely requires pre-paint measurement or adjustment.

This distinction connects to the browser rendering pipeline discussed in SE240-L01.

React controls its own render and commit work, but the browser still has to perform layout, paint, and compositing.

Choosing the correct synchronization timing matters because it affects when the user can see the result.

## 20. Strict Mode: Diagnosing the Extra Setup

Let's return to development Strict Mode with more precision.

When Strict Mode applies, React can intentionally perform an extra setup-and-cleanup cycle for Effects during development.

Suppose our availability Effect calls `connect()` and returns a cleanup that calls `disconnect()`.

The observed development sequence may resemble:

```text
Connect A
Disconnect A
Connect A
```

This is expected when the relevant Strict Mode development checks apply.

The important invariant is that only the intended active connection remains.

Now imagine the cleanup does nothing.

The sequence becomes two connections with no corresponding removal of the first.

Strict Mode has exposed a resource leak.

### 20.1 Why a `useRef` guard is often the wrong fix

A developer might introduce a ref called `hasConnected`.

The first setup changes it to true. Subsequent setups skip connection creation.

This may suppress duplicate setup in development.

But consider what happens after cleanup.

The connection has been disconnected, while the ref still says the connection was established.

The replacement setup may then skip reconnecting.

The application ends up disconnected.

The guard has concealed the lifecycle rather than implementing it.

Refs can be appropriate for genuine one-time coordination requirements, but they should not be the default response to Strict Mode's setup-and-cleanup checks.

### 20.2 Duplicate network requests are not automatically a bug

An Effect that fetches data may produce additional development requests under Strict Mode.

Correct cleanup can ensure that obsolete responses are ignored or aborted.

Production request behavior depends on the actual mounting and navigation lifecycle.

The objective is correctness, not an absolute promise that a request will occur only once.

If duplicate requests are expensive, data-loading architecture, caching, deduplication, and framework-level loading can address the broader problem.

We will explore those mechanisms in the next lecture.

### 20.3 Effects and irreversible operations

Some operations cannot meaningfully be undone.

Charging a credit card is the obvious example.

An Effect's setup-and-cleanup lifecycle is a poor fit for a transaction whose initiation must correspond to an explicit user action.

Do not attempt to solve such a mismatch by making the Effect run only once.

Put the operation behind an appropriate event or application command, and give the backend the controls necessary to make retries safe.

## 21. Why Raw Effect-Based Fetching Becomes Painful

Our hotel-price example is intentionally simple.

It uses one selected hotel and one request.

Real applications need more.

Imagine a search page showing forty hotels.

Each hotel needs a price, availability, a cancellation policy, and perhaps a recommendation score.

The customer changes filters and navigates between pages.

The same hotel may appear in several searches.

The user may return to a previously viewed hotel.

Now our application must answer questions such as:

Should previously fetched data be reused?

How long is a cached price considered fresh?

Can concurrent components share one pending request?

What happens when the customer changes filters while the old request is pending?

How are loading, error, and retry states represented?

How do we prevent request waterfalls?

How does server rendering interact with data loading?

A raw Effect does not provide a complete solution to these questions.

You can build caching, request deduplication, freshness rules, and invalidation yourself.

But doing so repeatedly across components becomes an application infrastructure project.

Libraries such as TanStack Query and framework-level data-loading mechanisms exist because server state is more complicated than calling `fetch()` after rendering.

That does not make understanding Effects irrelevant.

An engineer still needs to know why an old request can update the wrong screen, how cancellation works, and what an Effect's lifetime means.

Otherwise, the library merely hides a problem the engineer cannot diagnose when things go wrong.

**First understand the mechanism. Then choose an abstraction that removes repetitive complexity.**

## 22. A Production Debugging Procedure

Let's assemble everything into a practical investigation.

The customer reports:

> Sometimes Hotel B shows Hotel A's price. It happens more often when I navigate quickly. In development I also see duplicate network requests.

Do not immediately rewrite the component.

Begin by reconstructing the evidence.

### Step 1 — Identify the intended authority

At every moment, which hotel is selected?

Which response is allowed to supply the displayed quote?

If the selected hotel is B, a response produced for A must not be presented as B's current price.

This is the business invariant.

### Step 2 — Trace the asynchronous operations

Record the selected hotel ID, request start, request completion, and whether the result was accepted.

Use a distinct request identifier to correlate events.

Do not infer arrival order from the order in which requests started.

A slow earlier request can finish after a faster later request.

### Step 3 — Examine Effect dependencies

Does the Effect depend on the correct hotel ID?

Does it read credentials, filters, or other reactive values that are missing from the dependency array?

Does an unstable object or function cause unnecessary restarts?

### Step 4 — Examine cleanup

When the hotel changes, what happens to the previous Effect?

Is its work cancelled, invalidated, or allowed to continue?

Does cleanup remove listeners, clear timers, and disconnect subscriptions?

A missing cleanup may explain both duplicate resource usage and incorrect state updates.

### Step 5 — Examine state representation

Even if an obsolete request is ignored, can an old quote remain visible temporarily under the new hotel's title?

Does the state retain enough information to establish which hotel the quote belongs to?

Would a discriminated loading-and-success state better represent the interface?

### Step 6 — Reproduce deterministically

Do not rely on random network timing.

Artificially delay Hotel A's response and make Hotel B's response fast.

Start A, switch to B, and verify that A finishes last.

This turns an intermittent production symptom into a controlled test.

### Step 7 — Validate the actual fix

A successful fix should preserve the business invariant across request completion orders.

Test rapid navigation, repeated navigation, unmounting, failed requests, and development Strict Mode.

A fix that merely makes the bug less frequent is not sufficient.

The same investigation strategy applies to timers, subscriptions, authentication state changes, and third-party widgets.

In every case, ask which external process still has permission to affect the current application.

---

# The Oral Examination

Answer these questions aloud before reading the solutions. Explain the causal mechanism rather than merely identifying a Hook.

## Question 1 — The Missing Dependency

A hotel availability Effect uses `hotelId` and `authToken`, but declares only `[hotelId]` as dependencies.

The authentication token changes while the customer remains on the same hotel.

What could go wrong?

Why is suppressing the exhaustive-dependencies warning not a reliable fix?

## Question 2 — The Race

The customer selects Hotel A and then immediately Hotel B.

A's request takes 1,200 milliseconds. B's takes 150 milliseconds.

Both callbacks call `setPrice()` without checking whether the result still belongs to the selected hotel.

Predict the likely sequence and describe two independent safeguards.

## Question 3 — The Stuck Timer

An Effect creates an interval with an empty dependency array.

The callback calls `setSeconds(seconds + 1)` once per second.

The initial value of `seconds` is zero.

Why does the displayed value become stuck at one?

How would you fix it without recreating the interval every second?

## Question 4 — The Reconnecting Widget

A component creates an `options` object during every render.

An Effect depends on that object and opens a WebSocket connection.

Changing an unrelated theme value causes the connection to restart.

Explain why.

Give a correction that does not involve disabling the dependency linter.

## Question 5 — Strict Mode

In development, an Effect logs:

```text
connect
disconnect
connect
```

Is this necessarily a bug?

What would you investigate if the logs instead showed two connections with no disconnection?

## Question 6 — The Ref

A developer stores a visible booking total in `useRef`.

They update `totalRef.current` after changing the number of nights.

The screen does not update.

Explain why.

When would a ref be preferable to state?

## Question 7 — Should This Be an Effect?

Classify these operations:

- Calculating the reservation total from price and nights.
- Opening a WebSocket subscription for the selected hotel.
- Submitting a reservation after the customer clicks Confirm.
- Registering and removing a browser resize listener.
- Resetting a form because the selected hotel represents a different component identity.

Explain why each belongs where you place it.

## Question 8 — The Current Theme

An availability connection should remain open when the theme changes.

When the connection emits an event, a notification should use the latest theme.

How would you separate the reactive connection lifetime from the non-reactive notification behavior?

## Question 9 — The Cleanup Limit

A customer clicks Reserve, and the frontend sends a request to create a reservation.

The customer navigates away, and an AbortController aborts the fetch.

Does that guarantee that the reservation was not created?

Explain the difference between transport cancellation and business transaction correctness.

## Question 10 — The Real Incident

A component shows the correct hotel title but occasionally displays a quote belonging to a previously selected hotel.

The Effect already uses `[hotelId]` correctly.

Describe an investigation that distinguishes missing cleanup, asynchronous response ordering, and the temporary display of old state.

What would you test before declaring the bug fixed?

---

# Solutions and Discussion

## Solution 1 — The Missing Dependency

The Effect can continue using obsolete authentication credentials because changing `authToken` does not cause it to resynchronize.

The dependency list does not accurately describe the reactive values used by the Effect.

Include the relevant dependency or restructure the synchronization so that the credentials are handled through an appropriate, explicit mechanism.

Suppressing the warning can conceal stale closure behavior.

## Solution 2 — The Race

B's response arrives first and updates the displayed price.

A's response arrives later and overwrites it.

The first safeguard is invalidating or cancelling work associated with the previous hotel, so obsolete responses cannot update current state.

The second is representing the quote together with the hotel identity and refusing to display it when it does not match the selected hotel.

These safeguards address request authority and display consistency.

## Solution 3 — The Stuck Timer

The interval callback captures the initial value of `seconds`, which is zero.

Each tick requests the replacement value one.

A functional updater such as `setSeconds(previous => previous + 1)` transforms the current queued value without relying on the stale closure.

The interval should also be cleared during cleanup.

## Solution 4 — The Reconnecting Widget

The configuration object is created again on each render.

React compares dependency references using `Object.is`, so the new object is considered different.

The Effect therefore resynchronizes unnecessarily.

Creating the configuration inside the Effect and depending on the stable primitive values it actually needs is often the simplest solution.

## Solution 5 — Strict Mode

The extra setup-and-cleanup cycle is expected in development when Strict Mode checks apply.

It tests whether the synchronization process can be stopped and restarted correctly.

If connections accumulate, investigate missing or ineffective cleanup.

Do not automatically disable Strict Mode or introduce a guard that prevents necessary reconnection.

## Solution 6 — The Ref

Updating `.current` does not schedule a React render.

Refs are appropriate for persistent mutable values that do not determine the displayed interface, such as timer handles, DOM references, or external object instances.

If the value determines what the UI displays, React state is ordinarily the correct choice.

## Solution 7 — Should This Be an Effect?

The reservation total should be calculated during rendering because it is derived from existing data.

The WebSocket subscription belongs in an Effect or an appropriate abstraction managing external synchronization.

Reservation submission belongs to the explicit event-driven mutation path.

The resize listener can be managed by an Effect with correct cleanup.

If selecting a different hotel intentionally creates a new form identity, using a hotel-specific key may express the reset more directly than an Effect.

## Solution 8 — The Current Theme

The connection Effect should depend on values determining the connection, such as the selected hotel ID.

A suitable Effect Event can read the latest committed theme when a connection-related callback occurs, without making theme changes restart the connection.

This is a legitimate use of `useEffectEvent` in supported React versions.

It should not be used to hide dependencies that genuinely determine synchronization.

## Solution 9 — The Cleanup Limit

No.

Aborting a client-side request does not guarantee that the server stopped processing it or rolled back a completed transaction.

The reservation may already have been created.

Important mutations require server-side correctness mechanisms, including appropriate idempotency behavior, transactional controls, and ways to determine the outcome after an uncertain response.

## Solution 10 — The Real Incident

First, identify the quote's hotel ID and the currently selected hotel ID.

Then trace request creation, completion, cleanup, cancellation, and accepted state updates.

A correct dependency array does not automatically prevent an old promise from completing.

Separately, a previously loaded quote may remain in state while a new hotel is being selected.

Reproduce both conditions with controlled delays.

Verify that obsolete responses cannot override current data and that mismatched quotes are never displayed as belonging to the selected hotel.

Test fast navigation, slow responses, errors, unmounting, and development Strict Mode.

---

# The Mental Model Worth Keeping

React Effects are not lifecycle dumping grounds.

They are **synchronization processes** between committed React state and external systems.

Each Effect has a setup, a set of reactive dependencies, and possibly a cleanup. Its callbacks capture values from the render that created them.

The four questions worth retaining are:

**What external system am I synchronizing? Which values determine that synchronization? What invalidates the previous work? Does an obsolete result still have permission to change the interface?**

If an Effect merely transforms React state into more React state, reconsider whether it is needed.

If it manages an external resource, give that resource an explicit lifetime.

If it performs asynchronous work, establish who owns the result.

And if development Strict Mode exposes duplicate subscriptions, fix the cleanup rather than hiding the evidence.

---

# Next Lecture — SE250-L03: State, Data Fetching, and Real Application Architecture

We now understand the mechanics of Effects, asynchronous closures, cleanup, and request races.

But a production application needs more than individually correct Effects.

Consider a hotel-booking platform with dozens of screens, shared search filters, authentication, availability data, cached prices, user preferences, and optimistic updates.

Who owns each piece of state?

Which values belong in component state, URL parameters, context, a client-side store, or a server-state cache?

How do we avoid duplicated requests and stale data without implementing a miniature database inside every React component?

SE250-L03 moves from individual synchronization mechanisms to the architecture of a real React application.

The goal is to build systems in which state ownership, freshness, and data flow remain comprehensible as the product grows.

*The spoken lecture ends here. The following practical investigations are designed for on-screen work rather than continuous voice listening.*

---

# Optional Practical Lab — React Effect Failure Forensics

## Working Protocol

The purpose of these investigations is to develop independent debugging ability.

For each experiment:

1. Predict the failure before running the code.
2. Explain the expected sequence of renders, Effects, and callbacks.
3. Reproduce the problem with controlled conditions.
4. Inspect evidence before changing code.
5. Implement a correction without AI-generated diagnosis.
6. Verify the fix against multiple execution orders.
7. Ask AI to review your reasoning only after completing your own investigation.

A Vite React and TypeScript project is sufficient.

```bash
npm create vite@latest react-effects-lab -- --template react-ts
cd react-effects-lab
npm install
npm run dev
```

Keep React Strict Mode enabled in development.

## Experiment A — The Stale Hotel Price

### Objective

Reproduce a deterministic race condition involving two hotel requests.

Hotel A takes 1,200 milliseconds to respond.

Hotel B takes 150 milliseconds.

The customer selects A and quickly switches to B.

The application must never display Hotel A's price as Hotel B's current price.

### Broken implementation

Replace `src/App.tsx` with the following component.

```tsx
import { useEffect, useState } from "react";

type Hotel = "A" | "B";

type Quote = {
  hotelId: Hotel;
  price: number;
};

function fakeFetchQuote(
  hotelId: Hotel
): Promise<Quote> {
  const delay = hotelId === "A" ? 1200 : 150;
  const price = hotelId === "A" ? 180 : 240;

  return new Promise(resolve => {
    setTimeout(() => {
      console.log(`Response: ${hotelId}`);
      resolve({ hotelId, price });
    }, delay);
  });
}

export default function App() {
  const [hotelId, setHotelId] =
    useState<Hotel>("A");

  const [price, setPrice] =
    useState<number | null>(null);

  useEffect(() => {
    console.log(`Request started: ${hotelId}`);

    fakeFetchQuote(hotelId).then(quote => {
      console.log(`Accepting: ${quote.hotelId}`);
      setPrice(quote.price);
    });
  }, [hotelId]);

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
        Price: {price === null ? "Loading" : `€${price}`}
      </p>
    </main>
  );
}
```

### Tasks

**Task 1 — Predict**

Before executing the program, describe what happens when the customer switches from A to B within the first 200 milliseconds.

Write the order in which requests start and finish.

Predict the final displayed hotel and price.

**Task 2 — Observe**

Run the application.

Switch to Hotel B immediately.

Record the actual console messages and the final interface.

Remember that development Strict Mode may cause additional setup work. Explain what part of the behavior comes from Strict Mode and what part comes from the missing authority check.

**Task 3 — Correct request authority**

Implement an Effect-local ignore flag.

Ensure that a response from a cleaned-up Effect cannot update the active quote.

**Task 4 — Correct display consistency**

Replace the independent price state with a quote containing both the hotel identity and price.

Render a quote only when its hotel ID matches the currently selected hotel.

While the selected hotel's quote is unavailable, render an explicit loading state.

**Task 5 — Validate**

Test these navigation sequences:

- A to B.
- A to B to A.
- B to A.
- Multiple rapid changes.
- Switching hotels after an existing quote is already visible.

The application must never present one hotel's price under another hotel's title.

### Stretch investigation

Extend `fakeFetchQuote` to accept an `AbortSignal`.

Use the signal to cancel the timeout and reject the pending promise when aborted.

Then replace the ignore flag with an AbortController-based implementation.

Handle cancellation separately from genuine request failures.

Explain why invalidating an obsolete result and actually cancelling work are different operations.

## Experiment B — The Timer That Never Reaches Two

### Objective

Diagnose stale closure behavior and timer cleanup.

The timer should increment once per second while mounted.

### Broken implementation

This component creates an interval that repeatedly reads the initial `seconds` value.

```tsx
import { useEffect, useState } from "react";

export default function App() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setSeconds(seconds + 1);
    }, 1000);

    return () => clearInterval(id);
  }, []);

  return <h1>Seconds: {seconds}</h1>;
}
```

### Tasks

Predict the displayed value after one, two, and five seconds.

Run the implementation.

Explain why the interval callback retains the initial value.

Correct the problem using a functional state update.

Next, introduce a parent component with a button that mounts and unmounts the timer.

Verify that no interval continues after the timer component is removed.

### Acceptance criteria

The timer increments correctly while mounted.

The timer stops after unmount.

No unnecessary interval recreation occurs on every second.

## Experiment C — The Subscription Leak

### Objective

Understand why setup without cleanup creates accumulated external resources.

The mock subscription system below tracks active subscriptions in a module-level Set.

### Broken implementation

```tsx
import { useEffect, useState } from "react";

const subscriptions = new Set<number>();
let nextSubscriptionId = 1;

function subscribe(hotelId: string) {
  const id = nextSubscriptionId++;

  subscriptions.add(id);

  console.log(
    `Subscribed to ${hotelId}`,
    `Active: ${subscriptions.size}`
  );

  return () => {
    subscriptions.delete(id);

    console.log(
      `Unsubscribed from ${hotelId}`,
      `Active: ${subscriptions.size}`
    );
  };
}

export default function App() {
  const [hotelId, setHotelId] = useState("A");

  useEffect(() => {
    subscribe(hotelId);
  }, [hotelId]);

  return (
    <main>
      <h1>Hotel {hotelId}</h1>

      <button onClick={() => setHotelId("A")}>
        A
      </button>

      <button onClick={() => setHotelId("B")}>
        B
      </button>
    </main>
  );
}
```

### Tasks

Run the application in development Strict Mode.

Switch between A and B several times.

Observe the active-subscription count.

Identify what the `subscribe()` function returns.

Modify the Effect so that React receives a cleanup function.

Verify that after development checks and hotel changes settle, exactly one subscription remains active while the component is mounted.

Then add a parent that can unmount the subscriber and verify that the active count returns to zero.

Do not implement a ref guard to suppress the extra Strict Mode setup.

### Acceptance criteria

No subscriptions remain after unmount.

The active count does not grow indefinitely after repeated hotel switches.

The implementation behaves correctly when setup is followed by cleanup and another setup.

## Experiment D — An Effect That Runs for the Wrong Reason

### Objective

Investigate unstable object dependencies.

The application has a hotel connection and a theme toggle.

Changing the theme must not reconnect the hotel subscription.

### Broken implementation

```tsx
import { useEffect, useState } from "react";

export default function App() {
  const [hotelId, setHotelId] = useState("A");
  const [dark, setDark] = useState(false);

  const options = {
    hotelId,
    receiveAvailability: true,
  };

  useEffect(() => {
    console.log("CONNECT", options);

    return () => {
      console.log("DISCONNECT", options);
    };
  }, [options]);

  return (
    <main>
      <h1>Hotel {hotelId}</h1>

      <button
        onClick={() => setDark(previous => !previous)}
      >
        Theme: {dark ? "Dark" : "Light"}
      </button>

      <button
        onClick={() =>
          setHotelId(previous =>
            previous === "A" ? "B" : "A"
          )
        }
      >
        Switch hotel
      </button>
    </main>
  );
}
```

### Tasks

Predict what happens when changing only the theme.

Run the application.

Explain why the Effect sees a changed dependency.

Refactor the code so that the configuration object is created inside the Effect.

Make the Effect depend only on the values that actually determine the subscription.

Verify that changing the theme does not cause a new connection while changing the hotel still does.

### Acceptance criteria

The exhaustive-dependencies linter must remain enabled.

No dependency warning should be suppressed.

The subscription must resynchronize for actual hotel changes.

It must not resynchronize for unrelated theme changes.

## Experiment E — Classify Before You Code

Consider the following proposed features.

For each, decide whether it belongs in rendering, an event handler, an Effect, or a higher-level abstraction.

1. Calculate a reservation total.
2. Automatically synchronize the document title with the selected hotel.
3. Send a payment request after the customer clicks Pay.
4. Keep a browser resize listener registered.
5. Fetch a list of 2,000 hotels with caching, background refetching, retries, and request deduplication.
6. Reset an editable form when the user starts a completely new booking.
7. Read the latest theme when an established subscription emits a notification.
8. Focus an input after a user clicks an Edit button.

Your explanation must consider what triggers the operation, who owns the relevant state, whether synchronization is needed, and what cleanup or lifetime requirements exist.

---

# Practical Lab — Solutions and Diagnostic Notes

**Do not read this section before completing your own investigations.**

## Experiment A — Correct Request Authority

A local ignore flag allows each Effect execution to invalidate its own pending result.

A quote containing both `hotelId` and `price` allows the rendering logic to reject stale data even while the next Effect is waiting to run.

A minimal corrected implementation can follow this pattern:

```tsx
const [quote, setQuote] =
  useState<Quote | null>(null);

useEffect(() => {
  let ignore = false;

  fakeFetchQuote(hotelId).then(result => {
    if (!ignore) {
      setQuote(result);
    }
  });

  return () => {
    ignore = true;
  };
}, [hotelId]);

const visibleQuote =
  quote?.hotelId === hotelId ? quote : null;
```

The JSX should display `visibleQuote.price` only when `visibleQuote` exists.

Otherwise it should display a loading state.

The ignore flag prevents an obsolete Effect from committing its late result. The identity check prevents a previously loaded quote from being presented as belonging to a newly selected hotel.

For the AbortController variation, cancellation should stop the pending timer in the mock implementation and reject the promise with an appropriate cancellation error.

The application must distinguish cancellation from a genuine failure.

## Experiment B — Correct Timer

Use a functional updater to avoid depending on the captured `seconds` value.

```tsx
useEffect(() => {
  const id = setInterval(() => {
    setSeconds(previous => previous + 1);
  }, 1000);

  return () => clearInterval(id);
}, []);
```

The interval itself does not need to be recreated when the counter increments.

Cleanup prevents it from surviving the component's lifetime.

## Experiment C — Correct Subscription

Return the unsubscribe function provided by the subscription API.

```tsx
useEffect(() => {
  return subscribe(hotelId);
}, [hotelId]);
```

React now has the mechanism necessary to stop the previous subscription before starting the next one.

Development Strict Mode may create extra setup-and-cleanup activity, but it should not leave leaked subscriptions.

## Experiment D — Correct Dependencies

The configuration object should be created inside the Effect.

```tsx
useEffect(() => {
  const options = {
    hotelId,
    receiveAvailability: true,
  };

  console.log("CONNECT", options);

  return () => {
    console.log("DISCONNECT", options);
  };
}, [hotelId]);
```

The subscription depends on the hotel ID, not on an object whose identity changes whenever the component renders.

Changing the theme no longer forces reconnection.

## Experiment E — Classification

The reservation total belongs in rendering.

The document title can be synchronized through an Effect, with the desired document-title policy made explicit.

The payment request belongs in the deliberate user-interaction path, with server-side transaction safeguards.

The resize listener can be managed through an Effect with correct cleanup, or through an appropriate reusable abstraction.

Complex hotel data fetching is a strong candidate for a server-state library or framework-level data-loading solution.

Resetting a new booking form can be expressed through component identity or appropriate state ownership.

Reading the latest theme from an Effect-originated callback is a legitimate use case for an Effect Event in supported React versions.

Focusing an input because the user clicked Edit can often be handled directly from that interaction, provided the required DOM element exists when focus is attempted. If the input is only mounted after the state update, an appropriate ref and post-commit mechanism may be necessary.

---

# Further Reading

The following official documentation supports the mechanics discussed in this lecture.

1. **React — Synchronizing with Effects**  
   https://react.dev/learn/synchronizing-with-effects

2. **React — Lifecycle of Reactive Effects**  
   https://react.dev/learn/lifecycle-of-reactive-effects

3. **React — Removing Effect Dependencies**  
   https://react.dev/learn/removing-effect-dependencies

4. **React — Separating Events from Effects**  
   https://react.dev/learn/separating-events-from-effects

5. **React — You Might Not Need an Effect**  
   https://react.dev/learn/you-might-not-need-an-effect

6. **React — `useEffect` API Reference**  
   https://react.dev/reference/react/useEffect

7. **React — `useEffectEvent` API Reference**  
   https://react.dev/reference/react/useEffectEvent

8. **React — `useRef` API Reference**  
   https://react.dev/reference/react/useRef

9. **React — `useLayoutEffect` API Reference**  
   https://react.dev/reference/react/useLayoutEffect

10. **React — Strict Mode**  
    https://react.dev/reference/react/StrictMode

11. **React — Exhaustive Dependencies Lint Rule**  
    https://react.dev/reference/eslint-plugin-react-hooks/lints/exhaustive-deps

12. **Vue — Watchers**  
    https://vuejs.org/guide/essentials/watchers.html

Cross-reference SE250-L01 for render snapshots and closures, SE240-L03 for general asynchronous state races and server-state ownership, and SE240-L06 for frontend testing strategies.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE250-L02 — EFFECTS, CLOSURES, LIFECYCLES
================================================

THE CORE IDEA
-------------
Effect = synchronize committed React state
         with an external system.

Not:
- a generic "after render" callback
- a substitute for calculated state
- a dumping ground for event handlers
- a guarantee of exactly-once execution

EFFECT LIFECYCLE
----------------
Initial commit:
  setup

Dependencies change:
  previous cleanup
  new setup

Unmount:
  final cleanup

Development Strict Mode may add:
  setup → cleanup → setup

DEPENDENCIES
------------
useEffect(fn)
  Runs after every relevant commit.

useEffect(fn, [])
  Does not re-sync for changed props/state.
  Still has mount/unmount lifetime.
  Strict Mode may repeat setup in dev.

useEffect(fn, [hotelId])
  Re-syncs when hotelId changes.

Comparison: Object.is

Reactive dependencies include:
- props
- state
- values/functions declared in component

Missing dependency -> stale synchronization
Unstable dependency -> unnecessary restart

Do not suppress exhaustive-deps to hide bugs.

STALE CLOSURES
--------------
An Effect callback belongs to its render.

Changing state does not rewrite
previously created JavaScript closures.

Timer bug:
setSeconds(seconds + 1)
inside Effect with []

Fix:
setSeconds(prev => prev + 1)

ASYNC REQUEST RACE
------------------
Start A, then B.
B finishes first.
A finishes later.

Without authority checks:
A may overwrite B.

Protection:
1. Invalidate obsolete Effect results
2. Abort cancellable work when appropriate
3. Associate returned data with request identity
4. Render data only for matching entity

IGNORE PATTERN
--------------
useEffect(() => {
  let ignore = false;

  load(id).then(data => {
    if (!ignore) setData(data);
  });

  return () => {
    ignore = true;
  };
}, [id]);

ABORT PATTERN
-------------
const controller = new AbortController()

fetch(url, { signal: controller.signal })

cleanup:
controller.abort()

Abort does NOT guarantee server rollback.

RESOURCE CLEANUP
----------------
connect       -> disconnect
subscribe     -> unsubscribe
setInterval   -> clearInterval
setTimeout    -> clearTimeout
addListener   -> removeListener

Setup and cleanup must mirror each other.

EVENT VS EFFECT
---------------
Event handler:
Specific interaction causes action.

Effect:
Committed state requires external sync.

Render:
Calculate derived values.

Submit booking -> event
Connect availability -> Effect
Calculate total -> render

UNNECESSARY EFFECTS
-------------------
Avoid using Effects to:
- calculate totals
- filter existing arrays
- copy props into redundant state
- react to explicit button clicks
- synchronize state that can be derived

Often the best Effect is no Effect.

OBJECT DEPENDENCY TRAP
----------------------
const options = { hotelId }

Each render creates new object identity.

Effect depending on [options]:
may restart every render.

Better:
create options inside Effect
depend on [hotelId]

USE REF
-------
useRef(initial) -> { current }

Persists across renders.
Mutable.
Does not trigger rendering.

Good:
- timer IDs
- DOM references
- external instance handles
- nonvisual coordination values

Not a replacement for visible React state.
Not equivalent to Vue ref().

USE EFFECT EVENT
----------------
Modern React API.

Reads latest committed values in
Effect-related non-reactive callbacks.

Useful when:
- connection depends on hotelId
- notification uses latest theme
- theme should not reconnect socket

Not a dependency-linter escape hatch.
Not a general event-handler replacement.
Follow Effect Event calling restrictions.

USE LAYOUT EFFECT
-----------------
Runs in timing suitable for
DOM measurement before repaint.

Can block paint.
Use only for genuine pre-paint needs.

STRICT MODE
-----------
Extra dev setup/cleanup reveals:
- leaked listeners
- leaked timers
- leaked subscriptions
- broken remount assumptions

Do not "fix" by blindly disabling it.

DATA FETCHING IN PRODUCTION
---------------------------
Raw Effects require manual:
- race handling
- error states
- caching
- deduplication
- freshness
- invalidation
- request coordination

Consider TanStack Query or framework
data-loading mechanisms for real apps.

FOUR DEBUGGING QUESTIONS
------------------------
1. What external process is synchronized?
2. Which values determine its lifetime?
3. What invalidates the old work?
4. Can an obsolete callback still alter state?

INTERVIEW RED FLAGS
-------------------
"An empty dependency array means exactly once."
"Effects are the place for all async code."
"The dependency list is optional optimization."
"AbortController rolls back a backend request."
"Strict Mode is causing the production bug."
"A ref update should refresh the UI."
"Every prop change must restart the Effect."
"All state resets require useEffect."

NEXT:
SE250-L03 — State, Data Fetching,
and Real Application Architecture
```
