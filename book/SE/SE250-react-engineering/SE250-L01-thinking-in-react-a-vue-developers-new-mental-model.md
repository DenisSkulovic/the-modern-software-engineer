---
id: SE250-L01
course: SE250
title: "Thinking in React: A Vue Developer's New Mental Model"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE250-L02
---


# SE250 — React Engineering for Experienced Developers
## Lecture 01: Thinking in React — A Vue Developer's New Mental Model

*Why familiar JavaScript suddenly behaves strangely when you put it inside a React component.*

---

# Part I — Intuition

## 1. The Button That Refuses to Count

Imagine joining a company that operates a hotel-booking platform.

You are comfortable with Vue. You have written substantial frontend applications, handled forms, managed API requests, debugged production issues, and implemented complicated booking flows. React shouldn't be particularly intimidating.

After all, it has components, properties, state, event handlers, and declarative rendering. These are familiar ideas.

Your first assignment looks trivial.

The booking interface has a button labeled **Add two guests**. The current reservation has two guests. Clicking the button should increase that number to four.

You open the React component and discover something like this:

```tsx
function GuestSelector() {
  const [guests, setGuests] = useState(2);

  function addTwoGuests() {
    setGuests(guests + 1);
    setGuests(guests + 1);
  }

  return (
    <button onClick={addTwoGuests}>
      Guests: {guests}
    </button>
  );
}
```

The customer clicks the button.

The number changes from two to three.

Not four.

You inspect the event handler. There are clearly two increment operations. Neither throws an error. React renders the new value correctly. Everything appears to work, except for the actual result.

Your Vue instincts might suggest that the second operation should observe the result of the first. If a reactive reference initially contains two, incrementing its value twice produces four.

Yet React behaves differently.

This is not a bug in React. It is a bug in your mental model.

And understanding this particular mistake unlocks an extraordinary amount of React.

## 2. React Does Not Give You a Live State Variable

Let's begin with the most important distinction.

In Vue, a reactive reference behaves like a container holding a current value. When you write `guests.value++`, you change what that container contains.

Code that subsequently reads `guests.value` observes the updated value.

Vue tracks reactive dependencies and schedules the corresponding component updates. The browser's DOM does not necessarily update immediately, but the reactive reference itself has already changed.

React takes another approach.

When React runs your component function, it gives that particular execution a **snapshot of state**.

Imagine React producing a photograph of the reservation at a specific moment.

The photograph says:

- Hotel: Grand Central.
- Guests: two.
- Nights: three.
- Room price: €150.
- Total: €450.

The component uses these values to describe an interface.

The event handlers created during that execution also belong to this particular snapshot.

When the customer clicks **Add two guests**, the handler still knows `guests` as two.

Calling `setGuests(guests + 1)` does not rewrite the photograph.

Instead, it asks React to prepare another version of the interface, with guests set to three.

Calling the same expression again asks for the same value: three.

The original `guests` variable has not magically become three inside that handler.

React has received two requests to set the next value to three.

**State setters request future state. They do not mutate the state snapshot currently being read.**

This is the fundamental conceptual adjustment.

### Visual anchor 1 — Two photographs

```text
RENDER A
  guests = 2
  handler captures guests = 2
          |
          | customer clicks
          v
  request guests = 3
  request guests = 3
          |
          v
RENDER B
  guests = 3
  new handler captures guests = 3
```

The important thing about this diagram is not the arithmetic. It is that each render has its own values and its own event-handler closures.

The handler associated with Render A does not become the handler associated with Render B simply because a state update was requested.

## 3. React Rebuilds a Description, Not Necessarily the Screen

A second important distinction concerns the word *render*.

In ordinary conversation, rendering means drawing something on screen.

In React, rendering primarily means **calling component functions to calculate what the interface should look like**.

Imagine our booking component receives a nightly price and the number of nights. It returns a description containing a heading, the total price, and a reservation button.

That description is not the browser's DOM.

React examines the new result, compares it against the previous committed interface, and determines what must change.

Only then does React commit the necessary updates to the DOM.

In simple terms, three phases matter:

1. Something triggers an update.
2. React renders a new description.
3. React commits changes that are actually needed.

After that, the browser performs its own rendering work to produce pixels.

These are different layers.

You already encountered the browser's rendering pipeline in SE240-L01. React operates above that pipeline, deciding which DOM changes should be made.

### Visual anchor 2 — From interaction to screen

```text
Customer clicks
       |
       v
State update requested
       |
       v
React calls components
       |
       v
New UI description
       |
       v
React compares old and new
       |
       v
DOM commit, if needed
       |
       v
Browser rendering pipeline
```

This distinction explains another common mystery: a React component may execute without producing a visible DOM change.

It also explains why putting an API call directly inside a component function is dangerous. Rendering is supposed to calculate a description, not perform irreversible work.

React may render a component more than once. Some rendering work may never be committed.

You should not interpret every function execution as a confirmed change to the page.

## 4. What Actually Persists Between Renders?

We have established something peculiar.

React executes our component function again when its state changes.

But ordinary local variables inside a JavaScript function are recreated each time the function executes.

So where does the state live?

Not inside the local variable called `guests`.

React retains the component's state outside the individual function execution. When React renders the component, it supplies the appropriate state values for that render.

The `useState` call connects the function to that stored state.

You can think of `useState` as asking React:

> What value belongs to this particular component instance, at this particular state position, in the render we are calculating?

This is why the following pattern works:

```tsx
const [guests, setGuests] = useState(2);
```

`guests` is the value for the current render.

`setGuests` requests an update to the stored state.

And the initial value, two, is used when that state is first initialized, not every time the function executes.

React must therefore keep track of component instances and the ordering of their state hooks.

This is why hooks cannot be called conditionally or inside arbitrary loops. Their ordering is part of how React correctly associates state with the component.

The precise machinery becomes more interesting later, but the mental model is already useful.

## 5. React Remembers Components by Identity

Suppose our booking page contains an editable guest form.

The customer enters two guest names, selects another hotel, and suddenly finds that the previous guest names are still present.

Or perhaps the opposite happens: they change a seemingly harmless property and the entire form unexpectedly resets.

Both problems can arise from how React decides whether a component is the same component as before.

A component's state is associated with its identity in the React tree.

Its component type, position, and key are central to that identity.

Imagine a desk assigned to a particular hotel-booking form. Each time React renders, it checks whether the same occupant still belongs at that desk.

If the same component occupies the same identity position, its state can be preserved.

If React determines that this is a different component, the previous state is discarded and new state is initialized.

### Visual anchor 3 — Component identity

```text
BEFORE
BookingPage
  └── GuestForm (hotel A)
        └── draft = "Alice"

AFTER: same component identity
BookingPage
  └── GuestForm (hotel B)
        └── draft = "Alice"

AFTER: distinct key for hotel B
BookingPage
  └── GuestForm (hotel B)
        └── draft = ""
```

In the second situation, React can deliberately treat the new hotel form as a different component.

The important point is that changes to properties do not automatically create a new component identity.

React distinguishes between updating an existing component and replacing it.

And `key` is not merely a way to silence warnings about rendering lists. It is part of that identity system.

## 6. Repairing the Original Button

Return to the first mystery.

We wanted two increments, but both setter calls used the same snapshot.

React provides another form of state update.

Instead of passing the desired next value, pass a function that calculates it from the previous queued value.

```tsx
function addTwoGuests() {
  setGuests(g => g + 1);
  setGuests(g => g + 1);
}
```

Now React processes the updates sequentially.

The first updater transforms two into three.

The second updater receives three and transforms it into four.

We are no longer relying on the captured value from the old render.

We are expressing transformations of state.

This is the practical distinction:

**Use a value when you intend to replace state. Use an updater function when the next state depends on the previous state.**

Not every call to a state setter requires the functional form. But when the new value must be calculated from the existing value, the functional form is generally safer.

### A tiny comprehension check

Without running any code, consider this sequence. The current number of guests is two:

```tsx
setGuests(guests + 1);
setGuests(g => g + 1);
```

What number should the interface show after the queued updates are processed?

The answer is four.

The first operation requests the value three.

The second operation transforms that queued result into four.

If you understand why this works, you already understand something more important than memorizing the signature of `useState`.

You understand that React state updates are processed according to a model of snapshots and queued operations.

And this model will help explain stale closures, batched updates, mysterious form resets, incorrectly keyed lists, and quite a few other bugs.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 7. The React Component Is a Calculation

Let's examine the execution model more precisely.

A React function component accepts properties and returns a React element description, usually written with JSX.

Consider our hotel's booking summary.

```tsx
type BookingSummaryProps = {
  nightlyPrice: number;
  nights: number;
};

function BookingSummary({
  nightlyPrice,
  nights,
}: BookingSummaryProps) {
  const total = nightlyPrice * nights;

  return (
    <section>
      <h2>Your reservation</h2>
      <p>Total: €{total}</p>
    </section>
  );
}
```

A listener who skips the code should understand its entire purpose: React calls a function, the function multiplies the nightly price by the number of nights, and the returned JSX describes a reservation summary.

JSX is not an HTML template interpreted through Vue-style reactive bindings. It is syntax transformed into JavaScript expressions that create React elements.

Those elements are descriptions of what React should render. Creating one does not immediately insert a corresponding DOM node.

A crucial distinction is that writing `<BookingSummary />` tells React to render that component. You ordinarily do not call `BookingSummary()` yourself.

React must manage its lifecycle, state, and relationship to the surrounding tree.

### 7.1 Properties are inputs, not possessions

Our component receives `nightlyPrice` and `nights` through props.

It should treat those values as read-only inputs.

If a parent renders the component again with a new nightly price, the child receives new props and calculates a new total.

This is broadly familiar from Vue.

The important React-specific discipline is to treat each render as a fresh calculation based on the current props and state snapshot.

You should not mutate props or objects inherited from earlier renders.

For example, suppose a parent passes an array of reservation extras. The child wants to display them sorted alphabetically.

Calling `extras.sort()` directly mutates the array provided by the parent.

That violates the expectation that rendering does not modify existing inputs.

Instead, the child can create a copy and sort that copy.

```tsx
function ExtrasList({ extras }: {
  extras: string[];
}) {
  const sorted = [...extras].sort();

  return (
    <ul>
      {sorted.map(extra => (
        <li key={extra}>{extra}</li>
      ))}
    </ul>
  );
}
```

The important idea is not that sorting is forbidden. It is that the function should not modify data belonging to another component or previous snapshot.

**A render should calculate an interface, not change the world around it.**

## 8. Rendering, Reconciliation, and Commit

Let's follow the life of a React update.

Our booking page displays three nights at €150 per night, for a total of €450.

The customer clicks a button that changes the number of nights to four.

React receives a state update.

During the next render, the parent component runs with the new state. It describes the reservation summary with the number of nights equal to four.

React may then render its children as needed.

The summary calculates a total of €600.

Now React has enough information to determine how the committed interface should change.

The old interface had a paragraph displaying €450. The new description specifies €600.

React can update the relevant text in the existing DOM without recreating the entire page.

The browser then handles the resulting visual work.

### 8.1 Re-render does not mean remount

This distinction matters enormously.

A **re-render** means React executes rendering work again to calculate the UI.

A **remount** means React creates a new component instance rather than preserving the existing one.

Re-rendering an input component does not ordinarily imply destroying and recreating its DOM input.

Remounting it may discard its local state, DOM identity, focus, and other instance-specific behavior.

If someone says, "The component rerendered, therefore the input lost focus," that is not a sufficient explanation.

The question is whether the input's identity or DOM node changed.

### 8.2 React can calculate without committing

There is another important qualification.

React's modern rendering model can prepare work, interrupt work, restart work, or abandon work that never becomes the committed interface.

You should not assume a component execution corresponds one-to-one with a DOM commit.

Neither should you assume every state update necessarily produces a visible change.

For example, setting a state variable to a value React considers equal to the existing value may allow React to skip further work. React uses `Object.is` for its state equality comparison, although internal scheduling can still result in some rendering work before a bailout.

And when a parent renders, child components may also render even if their props appear unchanged, unless React can skip the work through its optimization mechanisms.

This is why render-count debugging requires care.

A component function executing twice is not proof that the browser repainted twice, and a component re-rendering is not necessarily evidence of a performance problem.

### 8.3 Strict Mode is deliberately inconvenient

In development, React Strict Mode may invoke component rendering logic an extra time to expose code that is not pure.

It can also perform additional development-only checks involving effects and refs.

This can confuse an engineer who puts `console.log()` inside the component function and expects one log per visible update.

The correct response is not automatically to disable Strict Mode.

Instead, distinguish render executions from committed changes, and investigate whether the component is doing work that should never happen during rendering.

We will examine effects and cleanup in SE250-L02.

For now, remember that **rendering must be safe to repeat**.

## 9. State Snapshots and JavaScript Closures

The original counter bug is not an exotic React edge case.

It is ordinary JavaScript closure behavior interacting with React's rendering model.

Every time React executes a component, its local variables belong to that particular invocation.

Every function created during the invocation closes over variables from that invocation.

Our booking component creates an event handler while `guests` equals two.

That handler retains access to the value two.

When React later renders the component with guests equal to three, it creates a new handler associated with the new render.

The previous handler does not become a different function with different captured values.

### 9.1 The misleading console log

Consider an event handler that changes the guests value and immediately logs it.

```tsx
function handleClick() {
  setGuests(guests + 1);
  console.log(guests);
}
```

If `guests` was two for that render, the log prints two.

This is expected.

The setter has requested a future state update. It has not reassigned the local constant.

Adding `await Promise.resolve()` inside the same handler does not magically make the captured `guests` variable live or reactive.

The closure still belongs to its original render.

This is a useful distinction for asynchronous code.

An `async` function may continue executing after other updates have occurred, while retaining values captured when that function began.

### 9.2 A delayed confirmation bug

Imagine a reservation interface that delays a confirmation message.

The customer initially selects two guests, clicks **Check availability**, and then changes the number of guests to four.

A delayed callback created by the original click still has access to the guest count that existed when the callback was created.

That might be correct. Perhaps the availability request was explicitly made for two guests.

Or it might be a bug. Perhaps the callback is supposed to report the current selection.

There is no universally correct answer until you establish the intended semantics.

**Captured historical values and current values are different things.**

React forces you to be clear about which one you mean.

Later, effects introduce additional places where stale closures matter. For now, the essential rule is simple: each render creates a new lexical environment.

## 10. State Updates Form a Queue

We can now examine how React processes several updates.

Suppose `guests` starts at two.

Consider three operations:

```tsx
setGuests(g => g + 1);
setGuests(10);
setGuests(g => g + 1);
```

These are not three identical kinds of instruction.

The first says: transform the previous value by adding one.

The second says: replace the value with ten.

The third says: transform the previous value by adding one.

React processes the queue in order.

Starting at two, the first updater produces three. The direct replacement produces ten. The last updater produces eleven.

The resulting state is eleven.

The sequence is conceptually similar to applying operations to a value in a small state machine.

The distinction between replacement and transformation is what makes the result predictable.

### 10.1 Batching is not the cause of every state bug

React batches many state updates so that it does not unnecessarily commit a separate interface update for every setter call.

Modern React includes automatic batching in common asynchronous contexts when using the modern root API.

But batching is not the fundamental reason our original button only incremented once.

Even before discussing scheduling, both expressions calculated the exact same replacement value from the same captured snapshot.

The essential problem was this:

`setGuests(guests + 1)` was executed twice while `guests` referred to two.

Both requested three.

Batching determines how updates are grouped for processing and rendering. Snapshot semantics determine what values the event handler reads.

Those are related but separate mechanisms.

React also ordinarily handles separate intentional user interactions, such as separate clicks, distinctly rather than indiscriminately merging them into a single batch.

Avoid the simplified folklore that every setter always causes a render, or that React waits until some arbitrary future moment for every update.

The reliable model is that setters enqueue update requests, React schedules and processes them, and the next render receives the resulting state.

### 10.2 A practical rule for update expressions

If you are setting a known value, such as changing the selected currency to euros, passing the value directly is reasonable.

If you are transforming existing state, such as incrementing a counter, appending to a list, removing an item, or toggling a boolean, an updater function is often the clearest form.

For example, adding a hotel to a collection can be expressed as transforming the previous array into a new array containing the additional hotel.

This avoids depending on a possibly outdated array captured by an earlier render.

It also makes the intended transition explicit.

## 11. React State Is Treated as Immutable

Here is where Vue experience can become actively misleading.

In Vue, mutating a property of a reactive object is a normal way to trigger reactive behavior.

In React, state objects should be treated as immutable snapshots.

Suppose a component stores the following reservation object:

```tsx
const [booking, setBooking] = useState({
  guests: 2,
  nights: 3,
  refundable: false,
});
```

Now an engineer writes:

```tsx
booking.guests = 4;
setBooking(booking);
```

This is wrong.

The object reference has not changed. React may regard the requested state value as unchanged.

Moreover, the engineer has modified an object that belonged to an earlier state snapshot.

That can produce confusing behavior when other parts of the application retain references to the same object.

The correct approach is to create a new state object.

```tsx
setBooking(previous => ({
  ...previous,
  guests: 4,
}));
```

The updater receives the relevant prior state value and returns a new object.

The spread operator preserves the other properties at the top level.

For nested objects, the same principle applies at each level being modified. A shallow spread does not automatically clone nested objects.

### 11.1 Why immutability matters

Immutability supports several useful properties.

First, React can use reference identity to determine whether state has changed and to support optimizations.

Second, previous render snapshots remain conceptually stable.

Third, debugging becomes easier because updates describe transitions between values instead of silently modifying shared objects.

Fourth, state updates are easier to reason about when multiple operations occur.

The cost is additional care when modifying arrays and deeply nested structures.

React is not demanding that every variable in your JavaScript application be immutable. It is asking you to treat the props and state used by rendering as immutable inputs.

Local temporary objects created and modified entirely within a render are a different matter.

The important boundary is ownership and observation.

## 12. Derived Values Should Usually Not Be State

Our hotel reservation has a nightly price and a number of nights.

The total price is their product.

Should the total be stored in its own state variable?

Usually not.

The component can calculate it directly during rendering.

```tsx
const total = nightlyPrice * nights;
```

Whenever the component renders with a new price or number of nights, it calculates the corresponding total.

There is no need for a separate state setter or synchronization mechanism.

If you store all three values independently, you create the possibility of inconsistency.

For example, the number of nights might change while the stored total remains stale.

This is exactly the kind of redundant state problem already discussed generally in SE240-L03.

Here we are applying the principle to React's render model.

### 12.1 But where is React's `computed`?

A Vue developer may naturally ask where React's equivalent of a computed property is.

For a cheap calculation, it is often just an ordinary JavaScript expression in the component function.

Vue's `computed` automatically tracks reactive dependencies and caches its result until those dependencies change.

React does not implicitly track arbitrary reads of state in the same fashion.

Instead, the component recalculates expressions when it renders.

For expensive calculations, React provides tools such as `useMemo`, but memoization has its own behavior and trade-offs.

We will explore those tools in SE250-L04 rather than treating every ordinary arithmetic expression as something that needs caching.

The practical message is that React components are calculations. Calculating derived values during rendering is not a workaround.

It is a normal part of the model.

## 13. Component Identity: Where State Actually Belongs

Let's turn to a class of bugs that can survive code review because the JSX looks perfectly reasonable.

Our booking page has a component called `GuestForm`.

It owns the guest names and contact information entered into a reservation.

A parent component displays one hotel's reservation form at a time.

Initially, it renders the form for Hotel A.

The customer types "Alice" into the guest-name field.

Then the customer selects Hotel B.

The parent passes a different `hotelId` property to `GuestForm`.

What should happen to the text field?

That depends on the product requirement.

But the React behavior may surprise you.

If React preserves the same component identity in the same tree position, the form's local state is ordinarily preserved.

Changing `hotelId` does not automatically reset `useState`.

### 13.1 Initial state is not reactive to new props

Suppose the form initializes its draft from a property.

```tsx
function GuestForm({ initialName }: {
  initialName: string;
}) {
  const [name, setName] = useState(initialName);

  return (
    <input
      value={name}
      onChange={e => setName(e.target.value)}
    />
  );
}
```

The initial value is used when this component's state is initialized.

If the parent later passes a different `initialName`, that does not mean React should discard the current draft and initialize the state again.

The component might contain important unsaved user input.

Automatically resetting that input whenever a property changes would be equally dangerous.

This is why `initialName` is an appropriate name: it describes the initial value, not a continuously synchronized source.

If the application needs a new form when the hotel changes, it must express that identity change.

### 13.2 Keys can deliberately reset state

One option is to give the form a key derived from the hotel identity.

```tsx
<GuestForm
  key={hotel.id}
  initialName={hotel.guestName}
/>
```

When the key changes, React treats the form at that position as a different component identity.

The previous form state is discarded and the new form initializes its state.

This can be exactly what the product needs.

But it can also destroy unsaved input.

A changing key is not automatically a fix. It is an explicit decision about component identity.

If the user should be able to switch between hotels and preserve separate drafts for each, simply forcing remounts is insufficient. Those drafts need an appropriate owner, such as state maintained by the parent and indexed by hotel ID.

The right implementation follows the intended data lifetime.

**Ask whose state it is, and how long it must survive.**

## 14. Keys in Lists: The Wrong Guest Gets the Right Name

Component identity becomes particularly important when rendering collections.

Imagine a booking screen with three guest rows.

Each row contains a name, an editable note, and perhaps an additional checkbox.

The application renders the rows using array indexes as keys.

Initially:

```text
0  Alice
1  Bob
2  Charlie
```

Each row owns some local input state.

The user edits Bob's note.

Then Alice is removed.

The new array is:

```text
0  Bob
1  Charlie
```

If the keys are the array indexes, React can associate the component previously occupying key zero with the new row at key zero.

But key zero previously represented Alice.

The component identity follows the index, not the guest.

This can cause local state to appear attached to the wrong guest.

A note originally entered for Alice may now appear under Bob.

### 14.1 Stable keys represent real identity

If each guest has a stable ID, use it.

```tsx
{guests.map(guest => (
  <GuestRow
    key={guest.id}
    guest={guest}
  />
))}
```

When items are inserted, deleted, or reordered, React can match the elements by their stable identities.

The rule is not that indexes are always forbidden.

An index key may be acceptable for a truly static list whose order and membership never change and whose rows do not depend on persistent local identity.

The problem is using a position as if it were an identity.

Also avoid generating a new random key on every render.

That communicates to React that the old component no longer exists and a new one has appeared.

The result may be repeated remounts, lost focus, reset input, and discarded local state.

**Keys are identity declarations, not decorative metadata.**

### 14.2 Type matters too

Keys are not the only factor.

React also distinguishes component types.

If an element at a position changes from one component type to another, React will generally replace the corresponding component subtree.

A related mistake is defining a component function inside another component's render function.

Every parent render creates a new nested function object. React can interpret that as a new component type, causing child state to reset.

This is one reason component definitions normally belong at module scope.

It is not merely a code-style preference.

It protects component identity.

## 15. Controlled Inputs Are a Contract

Our guest form contains a text input.

In React, one common approach is a controlled input.

The rendered value comes from React state, and the change handler updates that state.

For example, the form renders an input whose `value` is `name`, and whose `onChange` handler calls `setName` with the newly entered text.

The browser reports the input change. The handler requests the new state. React renders the corresponding value.

This creates a clear relationship between application state and the displayed field.

The important invariant is that the input's `value` and its state update mechanism agree about what the current text should be.

If you provide a controlled `value` but fail to update it properly, the field may appear read-only or repeatedly snap back to an old value.

If you supply a changing key to the input or its parent, the field may remount unexpectedly.

If you derive its value from an inappropriate source of truth, user edits may be overwritten.

And if you put the same input state in several different owners, those owners can disagree about what should be displayed.

Controlled inputs therefore make state ownership especially visible.

Uncontrolled inputs also exist, using browser-managed DOM state and APIs such as `defaultValue`. They can be appropriate in some situations.

But regardless of which style you choose, be deliberate about who owns the value and what should happen when the component is updated or replaced.

## 16. Predicting React Instead of Guessing

We have now developed enough knowledge to investigate a typical production bug.

The customer reports:

> When I change the number of guests, the price updates correctly. But when I switch hotels, my guest names sometimes disappear. Occasionally they appear under another hotel.

A weak debugging strategy is to add state setters until the behavior stops appearing.

Another weak strategy is to blame React's asynchronous rendering without establishing which state was actually changed.

A stronger investigation starts with four questions.

**First: What triggered the update?**

Was it a click, a prop change, a parent render, a state setter, or a change in the rendered component tree?

**Second: Which snapshot did the relevant code read?**

Was an event handler using the state captured during an earlier render? Was an updater function transforming the queued value?

**Third: What identity did React preserve?**

Was the same component type at the same position with the same key? Was an item moved or removed from a keyed list? Was a component unexpectedly remounted?

**Fourth: What work actually committed?**

Did React merely execute a render? Did a DOM node get replaced? Did the input lose focus because of a remount, or because application code deliberately focused something else?

These questions turn an apparently mysterious framework bug into a testable hypothesis.

For example, if guest names move between rows after deleting a guest, inspect the list keys and local state ownership.

If the same guest form retains old names after selecting another hotel, inspect whether the component identity was preserved and whether the draft is supposed to reset.

If clicking an increment button twice produces only one increment, inspect the captured snapshot and the update queue.

The goal is not to memorize every React API.

The goal is to predict the consequences of state and identity decisions before the browser proves you wrong.

## 17. Vue and React: Similar Goals, Different Execution Models

We should finish the technical discussion by being precise about the comparison.

Vue and React both support declarative component interfaces. Both manage updates rather than requiring developers to manipulate every DOM element manually.

Both have mechanisms for local and shared state, derived values, component composition, and lifecycle-related behavior.

Neither framework fundamentally changes how JavaScript closures work.

The important difference is how their programming models expose reactivity.

### 17.1 Vue emphasizes reactive data relationships

In Vue, a reactive reference exposes a current value, while computed properties and rendering effects track dependencies.

Mutating a reactive reference can cause dependent computations to become invalid and trigger scheduled updates.

The developer often reasons about an existing reactive object whose properties change over time.

### 17.2 React emphasizes render snapshots

In conventional React state management, setters request state transitions.

React re-executes component functions with new snapshots and uses the resulting descriptions to update the interface.

The developer reasons about a sequence of renders, each with its own values and closures.

React does not automatically track arbitrary property reads in a component and establish fine-grained reactive dependencies in the same way Vue does.

### 17.3 Neither approach eliminates difficult decisions

Vue's reactive dependency tracking does not solve incorrect server-state ownership, race conditions, or bad domain modeling.

React's snapshots do not automatically solve those problems either.

Both can produce subtle bugs involving state lifetime, stale asynchronous work, component identity, and inconsistent data.

And both can produce excellent applications.

React is not simply Vue with JSX and different naming conventions.

But it is also not an alien universe.

Your existing knowledge of component architecture, state ownership, browser behavior, and JavaScript remains valuable.

What changes is the model used to connect state updates to component execution.

Once that model becomes intuitive, much of React stops feeling arbitrary.

---

# The Oral Examination

Answer each question aloud before reading the solutions. A strong answer should explain the mechanism, not merely name an API.

### Question 1 — The counter

A component's `count` state equals five.

Its click handler calls `setCount(count + 1)` three times.

What value should appear after clicking, and why?

How would you make it increase by three?

### Question 2 — The queue

A component's `count` state equals two.

A single handler performs these updates in order:

```tsx
setCount(n => n * 2);
setCount(10);
setCount(n => n + 3);
```

Predict the final state.

Explain the processing of all three updates.

### Question 3 — The console mystery

An event handler calls `setName("Alice")` and then immediately logs `name`.

The old value was `"Bob"`.

Why might the console still print `"Bob"`?

Would putting `await Promise.resolve()` before the log guarantee that it prints `"Alice"`?

### Question 4 — The hotel form

A parent renders `<GuestForm hotelId={selectedHotelId} />`.

The customer types a name and then selects another hotel. The form retains the old name.

Is this necessarily a React bug?

Explain why the state was preserved and give two different design solutions for two different product requirements.

### Question 5 — The list

A list of editable guests uses array indexes as keys.

Deleting the first guest causes notes to appear under the wrong names.

Explain the likely cause.

Why does replacing indexes with random keys not solve the problem correctly?

### Question 6 — The render counter

A developer adds a console log to the body of a component and notices multiple executions for one apparent interface update.

Does this prove that React committed multiple DOM changes?

What additional evidence would you need?

### Question 7 — The Vue comparison

Explain the difference between updating `ref.value` in Vue and calling a React state setter.

Your explanation must distinguish the JavaScript state value, the framework's update mechanism, and the DOM.

### Question 8 — The mutable reservation

A React component stores a reservation object in state.

Its handler modifies `booking.guests` directly and then calls `setBooking(booking)`.

Why might the interface fail to update?

Explain a safer approach and why it is preferable.

---

# Solutions and Discussion

### Solution 1 — The counter

The final value is six.

All three setter calls calculate the same replacement value from the same captured `count` value of five.

To increment three times, use three functional updates, each transforming the previous queued state by adding one.

The essential distinction is replacement versus transformation.

### Solution 2 — The queue

The final value is thirteen.

The first updater doubles two to four. The direct setter replaces four with ten. The final updater adds three to ten.

The queue is processed in order.

An updater receives the result of the previous queued operation, not necessarily the state captured by the original event handler.

### Solution 3 — The console mystery

The event handler belongs to a render whose `name` value was `"Bob"`.

Calling the setter does not reassign the `name` variable captured by that handler.

The log therefore observes the historical snapshot.

Awaiting an already resolved promise does not turn that captured variable into a live state reference.

To use the new known value inside the same operation, store it in a local variable or otherwise design the operation around the intended state transition.

### Solution 4 — The hotel form

The form is probably the same component identity receiving new props.

Its local state is preserved because React does not automatically recreate state when props change.

If switching hotels should reset the form, using a hotel-specific key can deliberately create a new component identity.

If switching hotels should preserve independent unsaved drafts, the drafts need an owner that survives switching, with data associated with the correct hotel IDs.

The correct choice depends on the product requirement.

### Solution 5 — The list

Index keys associate component identity with list positions rather than guest identities.

When an earlier item is removed, later items shift positions and React can reuse component instances that previously represented different guests.

Stable guest IDs allow React to preserve the appropriate component identity through insertions, removals, and reordering.

Random keys are worse because they create unstable identities across renders, leading to unnecessary remounting and lost local state.

### Solution 6 — The render counter

No.

Rendering is component execution and UI calculation. Committing is applying the necessary changes.

A render can occur without a corresponding visible DOM change.

Development Strict Mode may also cause additional render executions.

Investigate the React Profiler, component identity, actual committed DOM updates, and relevant scheduling behavior before concluding that repeated logging represents repeated screen changes.

### Solution 7 — The Vue comparison

A Vue reactive reference behaves as a container with a current value. Assigning to `ref.value` changes the value directly and causes Vue to propagate the reactive change through its dependency system.

A React state setter requests a state update. The variable belonging to the current render remains its existing snapshot value.

Both frameworks may schedule DOM updates rather than applying them immediately.

The difference is not that Vue always synchronously updates the screen while React does not. The difference is how state and reactivity are exposed to application code.

### Solution 8 — The mutable reservation

The developer modified the existing object rather than producing a new state value.

React may regard the state as unchanged because the object identity remains the same.

The mutation also damages the conceptual stability of earlier snapshots.

Use a functional setter returning a new object, preserving unchanged fields and replacing the relevant guest count.

This provides a clear transition and avoids modifying existing state.

---

# The Mental Model Worth Keeping

When debugging a React application, imagine a sequence of snapshots rather than a continuously changing collection of local component variables.

Each render receives props and state, executes component functions, and produces a description of the desired interface.

Event handlers belong to the render that created them. State setters enqueue future values or transformations.

React preserves state according to component identity, especially type, position, and key. It calculates what changed and commits necessary DOM updates.

The most useful diagnostic questions are:

**Which snapshot did this code read? Which update did it request? Which component identity did React preserve? What actually committed?**

If you can answer those four questions, many apparently mysterious React bugs become ordinary engineering problems.

---

# Next Lecture — SE250-L02: Effects, Closures, and Component Lifecycles

Our first lecture deliberately focused on the relationship between state, rendering, and identity.

But real applications interact with systems outside React.

They fetch data, subscribe to events, open WebSocket connections, register browser listeners, start timers, and integrate with third-party libraries.

This introduces a new problem.

What happens when an asynchronous callback belongs to an old render, but the application has already moved on?

And when should React synchronize with an external system rather than merely calculate a new interface?

In SE250-L02, we investigate effects, dependency arrays, cleanup, stale closures, and Strict Mode's development checks.

The objective will be to understand why so many React applications accumulate fragile effects—and how to reason about them without trial-and-error dependency changes.

*The spoken lecture ends here. The following practical material is intended for on-screen investigation rather than continuous audio listening.*

---

# Optional Practical Lab — The React Snapshot and Identity Investigation

## Working rules

This laboratory is not a passive demonstration.

For every experiment:

1. Predict the behavior before executing the code.
2. Explain the mechanism in writing.
3. Run the application and observe the result.
4. Investigate any discrepancy between prediction and observation.
5. Correct the implementation without AI-generated fixes.
6. Verify the corrected behavior.
7. Ask Cursor or another AI assistant to critique the reasoning only afterward.

You may use AI to generate the initial project scaffolding. Do not use it to diagnose the deliberate bugs before your first attempt.

A small Vite React and TypeScript project is sufficient.

```bash
npm create vite@latest react-lab -- --template react-ts
cd react-lab
npm install
npm run dev
```

Replace `src/App.tsx` with each experiment.

## Experiment A — The State Update Queue

### Initial implementation

This experiment contains three buttons. One uses direct replacement updates, another uses functional updates, and the third mixes both kinds.

Predict the displayed value after clicking each button once, starting from zero. Reset the component between experiments.

```tsx
import { useState } from "react";

export default function App() {
  const [count, setCount] = useState(0);

  function direct() {
    setCount(count + 1);
    setCount(count + 1);
    setCount(count + 1);
  }

  function functional() {
    setCount(n => n + 1);
    setCount(n => n + 1);
    setCount(n => n + 1);
  }

  function mixed() {
    setCount(count + 1);
    setCount(n => n * 2);
    setCount(7);
    setCount(n => n + 1);
  }

  return (
    <main>
      <h1>Count: {count}</h1>
      <button onClick={direct}>Direct</button>
      <button onClick={functional}>Functional</button>
      <button onClick={mixed}>Mixed</button>
      <button onClick={() => setCount(0)}>
        Reset
      </button>
    </main>
  );
}
```

### Tasks

Before running the application, write a prediction for all three buttons.

For the mixed sequence, write the exact intermediate values after every queued operation.

Next, add a `console.log(count)` before and after every setter call inside the `direct` handler.

Explain why those logs do not necessarily show the new state, even though the visible number eventually changes.

Finally, add a fourth button that increments the count by five using only one updater function.

### Acceptance criteria

You should be able to explain the behavior without referencing the documentation.

Your fourth button must work correctly when the starting count is zero, five, or a hundred.

Your explanation must distinguish closure values, state-update requests, batching, and the next render.

## Experiment B — The Vanishing Reservation Draft

### Initial implementation

This application has two hotels and a simple reservation form.

The form maintains a local draft initialized from its props.

Predict what happens when you edit a guest name and switch hotels.

```tsx
import { useState } from "react";

const hotels = [
  { id: "A", name: "Hotel A", guest: "Alice" },
  { id: "B", name: "Hotel B", guest: "Bob" },
];

function GuestForm({
  initialGuest,
}: {
  initialGuest: string;
}) {
  const [guest, setGuest] = useState(initialGuest);

  return (
    <label>
      Guest name:
      <input
        value={guest}
        onChange={e => setGuest(e.target.value)}
      />
    </label>
  );
}

export default function App() {
  const [hotelId, setHotelId] = useState("A");
  const hotel = hotels.find(h => h.id === hotelId)!;

  return (
    <main>
      <h1>{hotel.name}</h1>
      <button onClick={() => setHotelId("A")}>
        Hotel A
      </button>
      <button onClick={() => setHotelId("B")}>
        Hotel B
      </button>

      <GuestForm initialGuest={hotel.guest} />
    </main>
  );
}
```

### Tasks

First, determine why switching hotels does not automatically initialize a new draft.

Then implement two separate versions.

**Version 1 — Reset per hotel**

Switching to a different hotel should show that hotel's initial guest name.

Use component identity to implement the behavior.

**Version 2 — Preserve independent drafts**

Each hotel should maintain its own edited guest name.

The user can switch between hotels repeatedly without losing either draft.

Implement this without introducing an unnecessary effect.

Think carefully about where the draft state should live.

### Acceptance criteria

Version 1 must reset state when switching to another hotel.

Version 2 must preserve independent drafts and must not mix the two hotels' data.

For both versions, explain the role of component identity and state ownership.

## Experiment C — Guest Notes Attached to the Wrong People

### Initial implementation

This example displays three editable guest notes.

It deliberately uses array indexes as keys.

```tsx
import { useState } from "react";

type Guest = {
  id: string;
  name: string;
};

const initialGuests: Guest[] = [
  { id: "a", name: "Alice" },
  { id: "b", name: "Bob" },
  { id: "c", name: "Charlie" },
];

function GuestRow({ guest }: { guest: Guest }) {
  const [note, setNote] = useState("");

  return (
    <div>
      <strong>{guest.name}</strong>
      <input
        placeholder="Guest note"
        value={note}
        onChange={e => setNote(e.target.value)}
      />
    </div>
  );
}

export default function App() {
  const [guests, setGuests] =
    useState(initialGuests);

  function removeFirst() {
    setGuests(previous => previous.slice(1));
  }

  return (
    <main>
      <button onClick={removeFirst}>
        Remove first guest
      </button>

      {guests.map((guest, index) => (
        <GuestRow
          key={index}
          guest={guest}
        />
      ))}
    </main>
  );
}
```

### Tasks

Enter different notes for Alice, Bob, and Charlie.

Predict which notes will appear after removing Alice.

Then remove Alice and observe.

Explain why React preserved some component state while associating it with different guest data.

Fix the implementation using stable identity.

Extend the experiment by adding a button that reverses the remaining guests.

Verify that notes follow the correct guest after reordering.

### Acceptance criteria

Each guest's note must remain associated with the correct guest through deletion and reordering.

You must be able to explain why random keys would not be an acceptable fix.

## Experiment D — The Invisible Mutation

### Initial implementation

This component stores a reservation in state, but its update handler mutates the existing object.

```tsx
import { useState } from "react";

export default function App() {
  const [booking, setBooking] = useState({
    guests: 2,
    nights: 3,
  });

  function addGuest() {
    booking.guests += 1;
    setBooking(booking);
  }

  return (
    <main>
      <p>Guests: {booking.guests}</p>
      <p>Nights: {booking.nights}</p>
      <button onClick={addGuest}>
        Add guest
      </button>
    </main>
  );
}
```

### Tasks

Predict the behavior when pressing the button.

Do not assume that calling a setter necessarily forces a visible update.

Inspect the object identity before and after the setter.

Correct the implementation using an immutable state transition.

Next, change the reservation shape to contain nested contact information.

Add a button that updates the contact email without mutating the existing state object or nested contact object.

### Acceptance criteria

Updates must render correctly.

Previous state objects must not be mutated.

Explain why shallow object copying is insufficient for nested modifications unless the nested level is also copied.

---

# Lab Solutions and Diagnostic Notes

**Do not read this section until you have completed your own investigations.**

### Experiment A

Starting from zero, the direct-update button produces one, the functional-update button produces three, and the mixed button produces eight.

For the mixed sequence, the transformations are zero to one, one to two, replacement with seven, and finally seven to eight.

The additional button can use `setCount(n => n + 5)`.

Logs reading `count` inside the same handler observe the captured value from that render.

### Experiment B

In Version 1, give `GuestForm` a key derived from the selected hotel's ID. Changing the key instructs React to treat the form as a new component identity.

In Version 2, the state must survive switching between hotel forms. A straightforward solution is to maintain a mapping of hotel IDs to draft names in the parent and provide the appropriate value and update callback to a controlled child form.

The important distinction is between destroying a draft intentionally and preserving multiple independent drafts.

### Experiment C

Index keys associate local state with positions.

When Alice is removed, the old component associated with the first position may now be used for Bob. Its local note state is therefore attached to the wrong guest.

Use `guest.id` as the key.

For the reversal task, update the array immutably, for example by returning a reversed copy. The stable guest IDs allow React to maintain correct component identities.

### Experiment D

The initial handler mutates the existing state object and passes the same object reference back to React.

The correct guest update is:

```tsx
setBooking(previous => ({
  ...previous,
  guests: previous.guests + 1,
}));
```

For nested contact data, create a new outer object and a new nested contact object:

```tsx
setBooking(previous => ({
  ...previous,
  contact: {
    ...previous.contact,
    email: "new@example.com",
  },
}));
```

The nested example assumes the reservation state has been extended to include a `contact` object.

The principle is to preserve untouched values while replacing the objects along the path being changed.

---

# Further Reading

These references provide official explanations and runnable examples that reinforce the lecture.

1. **React — Render and Commit**  
   https://react.dev/learn/render-and-commit

2. **React — State as a Snapshot**  
   https://react.dev/learn/state-as-a-snapshot

3. **React — Queueing a Series of State Updates**  
   https://react.dev/learn/queueing-a-series-of-state-updates

4. **React — Preserving and Resetting State**  
   https://react.dev/learn/preserving-and-resetting-state

5. **React — Keeping Components Pure**  
   https://react.dev/learn/keeping-components-pure

6. **React — Updating Objects in State**  
   https://react.dev/learn/updating-objects-in-state

7. **React — Rendering Lists**  
   https://react.dev/learn/rendering-lists

8. **React — Choosing the State Structure**  
   https://react.dev/learn/choosing-the-state-structure

9. **Vue — Reactivity in Depth**  
   https://vuejs.org/guide/extras/reactivity-in-depth

10. **Vue — Computed Properties**  
    https://vuejs.org/guide/essentials/computed

Cross-reference SE240-L01 for the browser rendering pipeline, SE240-L02 for frontend architecture and state ownership, and SE240-L03 for Vue reactivity and general state-management principles.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE250-L01 — THINKING IN REACT
============================================

CORE EXECUTION MODEL
--------------------
Event / state update
    → React schedules work
    → component functions render
    → new UI description
    → reconciliation
    → commit necessary DOM changes
    → browser renders pixels

Render  = calculate UI description
Commit  = apply DOM changes
Remount = replace component identity
Rerender != remount
Rerender != guaranteed DOM mutation

STATE SNAPSHOTS
---------------
Each render has its own:
- props
- state values
- local variables
- event-handler closures

setState(next) does not modify the
state variable captured by the current render.

STATE UPDATE QUEUE
------------------
setCount(count + 1)    replace with calculated value
setCount(n => n + 1)   transform previous queued value

Starting at 2:
setCount(count + 1)
setCount(count + 1)
=> 3

Starting at 2:
setCount(n => n + 1)
setCount(n => n + 1)
=> 4

Starting at 2:
setCount(n => n * 2)
setCount(10)
setCount(n => n + 3)
=> 13

BATCHING
--------
Multiple updates may be grouped.
Batching concerns scheduling/rendering.
Snapshot semantics concern captured values.
They are related, not interchangeable.

IMMUTABILITY
------------
WRONG:
booking.guests++
setBooking(booking)

RIGHT:
setBooking(prev => ({
  ...prev,
  guests: prev.guests + 1
}))

Nested updates require copying nested
objects along the modified path.

DERIVED STATE
-------------
const total = price * nights

Prefer calculation during rendering
over duplicated stored state.

Vue computed:
- tracked reactive dependencies
- cached until invalidated

React ordinary expression:
- recalculated when component renders
- no automatic read-level dependency tracking

COMPONENT IDENTITY
------------------
State is associated with component identity:
- component type
- tree position
- key when applicable

Same identity -> preserve state
Different identity -> reset/remount

Changing props alone does not reset useState.
useState(initial) uses initial on initialization.

KEYS
----
Stable entity IDs -> correct identity
Array indexes -> position-based identity
Random keys -> repeated remounting

Use key intentionally:
- preserve identity for moving list items
- reset identity for a genuinely new form

INPUTS
------
Controlled:
value={name}
onChange={e => setName(e.target.value)}

Input bugs:
- stale value source
- missing state update
- wrong owner
- changing key
- unintended remount

PURITY
------
Rendering should not:
- mutate props
- mutate existing state
- perform external side effects

Strict Mode may repeat render logic in dev.
Render logging != committed DOM changes.

VUE VS REACT
------------
Vue:
reactive current-value containers
dependency tracking
scheduled DOM updates

React:
immutable render snapshots
state update requests
component re-execution
reconciliation and commit

FOUR DIAGNOSTIC QUESTIONS
-------------------------
1. What triggered the render?
2. Which snapshot was read?
3. Which identity was preserved?
4. What actually committed?

INTERVIEW RED FLAGS
-------------------
"setState immediately changes the variable."
"Every render recreates the DOM."
"Changing props resets component state."
"Keys only silence warnings."
"Index keys are always harmless."
"React state objects can be mutated freely."
"Multiple logs prove multiple DOM commits."

NEXT: SE250-L02
Effects, Closures, and Component Lifecycles
```
