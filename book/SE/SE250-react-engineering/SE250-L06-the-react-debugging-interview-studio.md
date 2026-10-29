---
id: SE250-L06
course: SE250
title: "The React Debugging Interview Studio"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L05
next: null
---


# SE250 — React Engineering for Experienced Developers
## Lecture 06: The React Debugging Interview Studio

*The code compiles. The tests are mostly green. The customer reports that something is wrong. Your interviewer turns toward you and asks: "All right. How would you investigate?"*

---

# Part I — Intuition

## 1. Welcome to an Unfamiliar Codebase

Imagine you're interviewing for a full-stack position at a European product company.

The technical round is practical. There are no whiteboard algorithms, no questions about memorizing obscure JavaScript specifications, and no demand that you implement a distributed database in forty minutes.

Instead, the interviewer opens a small React application.

It's a hotel-booking interface with search results, a guest form, availability data, and a reservation button.

The interface looks ordinary.

Then the interviewer demonstrates a bug.

A customer reserves the last available room at Hotel Aurora. The backend reports that the reservation succeeded and inventory is now zero.

But the hotel card still says one room available.

The interviewer asks:

"Why?"

You examine the component.

It uses `useQuery`, displays the returned data, and calls a mutation when the user clicks Reserve.

Nothing obviously broken jumps out.

You could try changing the state, forcing a re-render, introducing a new Effect, or asking Cursor to rewrite the feature.

But the interviewer is not primarily interested in whether you can make the screen change.

They want to know whether you can explain why it was wrong in the first place.

That's what separates familiarity with React from engineering competence.

## 2. A Bug Is Evidence of a Broken Assumption

Every piece of application code contains assumptions.

A state setter assumes something about which value should come next.

An Effect assumes something about which external resource it is synchronizing.

A query key assumes something about the identity of data.

A component key assumes something about the identity of a component instance.

A Server Component assumes something about which environment can execute its code.

When the application misbehaves, one or more of those assumptions may be false.

Your task is to identify which assumption failed.

Consider the stale hotel availability.

There are several plausible explanations.

Perhaps the backend didn't actually update inventory.

Perhaps the frontend requested the wrong hotel.

Perhaps the query cache still contains an older result.

Perhaps the reservation mutation invalidated the wrong query.

Perhaps the card is rendering a different copy of availability stored in Context.

Perhaps the request completed correctly, but the component displayed a historical result.

These hypotheses are not equally likely in every situation.

But you cannot choose one merely because you remember seeing a similar bug in another project.

You need evidence.

### Visual anchor 1 — From symptom to cause

```text
Customer sees wrong availability
              |
              v
      Establish actual state
              |
              v
      Trace data provenance
              |
              v
      Identify violated invariant
              |
              v
      Form a hypothesis
              |
              v
      Test hypothesis against evidence
              |
              v
      Fix and verify
```

The purpose of debugging is not to make the visible symptom disappear by whatever means happen to work.

It is to identify the violated contract and restore it.

## 3. The Four React Questions

Across the preceding five lectures, we've examined many mechanisms.

But a remarkably large portion of React debugging can begin with four questions.

**First: Which render or state snapshot did this code belong to?**

A callback may retain state from an older render. A state setter may queue a replacement when the developer intended a transformation.

**Second: Which component identity did React preserve?**

A changing key may remount a form. An unstable list key may associate local state with a different entity.

**Third: Which synchronization or data owner produced this value?**

An Effect may have obsolete work still running. A query key may identify the wrong cache entry. Two components may own competing copies of the same server data.

**Fourth: Which environment performed the work?**

The code may execute during client rendering, server prerendering, hydration, or a subsequent browser interaction.

These four questions will not solve every possible problem.

But they cover a surprising amount of the territory where React applications become difficult.

### Visual anchor 2 — Four dimensions of a React bug

```text
React defect
    |
    ├── Time
    |     Snapshot, closure, update order
    |
    ├── Identity
    |     Position, type, key, remount
    |
    ├── Ownership
    |     Local state, Context, server cache
    |
    └── Environment
          Server, browser, hydration
```

This is a more useful debugging model than attempting to remember which hook is fashionable this year.

## 4. Reading Code Is a Prediction Exercise

Suppose you encounter an unfamiliar custom hook.

It creates an interval, updates state once per second, and logs the selected hotel.

A superficial review says:

"Okay, it starts a timer."

An engineering review asks:

Which values does the interval callback capture?

What happens when those values change?

What stops the interval?

What happens if the component unmounts?

What happens in development Strict Mode?

Can two intervals become active simultaneously?

Does changing the selected hotel reset the correct state?

You should be able to answer many of these questions before executing the code.

Then you run it.

If your prediction is wrong, investigate the difference.

This is how reading unfamiliar code becomes a trainable skill.

You're not merely learning APIs.

You're learning to simulate the execution model mentally.

## 5. Symptoms, Mechanisms, and Solutions Are Different Things

Imagine an interviewer says:

"The guest-name field loses focus while typing."

A weak answer is:

"I'd add `useMemo`."

That is a proposed intervention without a diagnosis.

A stronger answer is:

"I'd check whether the input DOM node is being replaced. If the component or one of its ancestors changes identity on every keystroke, React may remount the input and lose focus. I'd inspect keys and component definitions, then verify which DOM node survives between updates."

The second answer contains a causal hypothesis.

It identifies evidence that would confirm or reject it.

It also leaves room for other explanations.

Perhaps the input loses focus because application code explicitly focuses another element.

Perhaps the parent conditionally switches between different input components.

The key is that the investigation connects the symptom to a mechanism.

### Visual anchor 3 — A complete engineering answer

```text
Symptom
  "The field loses focus."

Mechanism
  "The input may be remounted."

Evidence
  "Its DOM identity changes on each edit."

Correction
  "Preserve component identity."

Verification
  "Typing retains focus and draft state."
```

A senior engineer should be able to explain all five.

## 6. Correctness Before Cleverness

A tempting React debugging strategy is to deploy optimization hooks until the problem disappears.

`memo`, `useMemo`, `useCallback`, refs, Effects, and transitions can all change application behavior or scheduling characteristics.

But that doesn't make them interchangeable.

If a query cache has the wrong key, memoization is irrelevant.

If a timer leaks, moving it into a ref without cleanup doesn't solve the resource-lifetime problem.

If a list uses array indexes as keys, preventing additional re-renders does not establish correct entity identity.

If server and browser output disagree during hydration, forcing a client-only state update may hide a deeper environment assumption.

The simplest correct solution is often less code than the original implementation.

Deleting an unnecessary Effect can improve correctness.

Moving state to its rightful owner can eliminate coordination logic.

Using a stable entity ID can fix a class of state-preservation problems.

And correcting a query key can remove the need for several compensating refetches.

## 7. What the Interviewer Is Actually Evaluating

A practical debugging interview is rarely just a test of whether the candidate knows the correct hook.

The interviewer can observe how you approach an unfamiliar problem.

Do you establish the expected behavior?

Can you reproduce the failure?

Do you distinguish facts from guesses?

Can you read unfamiliar code without panicking?

Do you investigate the relevant runtime evidence?

Do you make a minimal, defensible change?

Can you write a test that would have caught the regression?

And when the interviewer challenges your solution, can you explain its trade-offs?

You do not need to pretend that you have operated every React feature in production.

A strong response can acknowledge unfamiliarity while demonstrating a credible verification plan.

For example:

"I haven't worked extensively with that Next.js caching mechanism, so I wouldn't assume its behavior. I'd first establish which cache owns the result, check the framework version and configuration, and reproduce the invalidation behavior in a small test."

That is considerably stronger than confidently inventing the behavior of an API.

### A tiny comprehension check

Suppose a React component appears to render twice in development.

Should you immediately disable Strict Mode?

No.

First establish what actually happened.

Were there two component-function executions, two Effect setups, two DOM commits, or two network requests?

Those observations have different explanations.

The interviewer wants you to distinguish them.

This studio is designed to train exactly that skill.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. The Studio Contract

This course concludes with four practical investigations.

Each scenario contains a defective implementation and a customer-visible symptom.

You must work through it without reading the solution notes first.

The intended approach is:

**Predict → Reproduce → Investigate → Explain → Correct → Test → Defend.**

These stages are distinct.

Predicting means explaining what you expect the existing code to do.

Reproducing means observing the failure under known conditions.

Investigating means collecting evidence about the mechanism.

Explaining means identifying the specific violated invariant.

Correcting means changing the implementation.

Testing means verifying expected behavior and relevant edge cases.

Defending means explaining why your solution is appropriate and what alternatives you considered.

Only after completing the first independent attempt should AI review your explanation.

## 9. Four Scenarios, Four Engineering Dimensions

The studio is built around four production-like incidents.

### Scenario A — Availability That Lies

A booking application shows inconsistent availability after navigation and reservation.

The investigation requires understanding server-state caching, query identity, mutation invalidation, and backend authority.

### Scenario B — The Guest Who Inherited Someone Else's Notes

A dynamic guest list attaches local input state to the wrong person.

A separate performance complaint involves unnecessary rendering when unrelated state changes.

The investigation requires distinguishing component identity, state ownership, Context propagation, and actual render cost.

### Scenario C — The Custom Hook That Refuses to Die

A timer-based feature behaves incorrectly after changing hotels.

Development Strict Mode makes the defect more visible.

The investigation requires understanding closures, dependencies, cleanup, and state lifetime.

### Scenario D — The Page That Disagrees with Its Own HTML

A Next.js hotel page produces hydration problems and sends unnecessary internal data to a Client Component.

The investigation requires understanding server prerendering, Client Component boundaries, serialization, and safe data exposure.

The scenarios deliberately cover different failure mechanisms.

In practice, a real incident may involve several of them simultaneously.

## 10. Investigation Discipline

Before modifying code, write a short incident note.

A useful format is:

**Observed:** What does the application actually do?

**Expected:** What should the user or system observe?

**Hypothesis:** Which mechanism could explain the discrepancy?

**Evidence:** What did you inspect, and what supports the hypothesis?

**Change:** Which specific code change should restore the invariant?

**Verification:** What test or experiment would fail before the change and pass afterward?

This should be concise.

You are not writing a thesis every time a button misbehaves.

But the structure prevents a common failure mode: making multiple speculative changes without knowing which one solved the problem.

## 11. Test Behavior, Not Hook Arrangement

A regression test should survive reasonable refactoring.

If a guest note must remain associated with Bob after Alice is removed, test that user-visible behavior.

Do not require a particular `useState` call or reducer structure.

If an old hotel request must not overwrite the current selection, test the displayed hotel and quote.

Do not require the component to use a particular ignore flag.

If a timer must stop after unmount, verify the absence of active work.

Do not assert arbitrary implementation details unless they are directly relevant to the resource contract being tested.

This principle allows multiple valid implementations.

A candidate can solve a stale-data problem with correctly managed Effects, cancellation, or a suitable server-state library.

The interviewer should assess correctness and trade-offs, not personal attachment to one library.

## 12. Performance Claims Require Measurements

For the performance scenario, use React DevTools Profiler and the browser Performance panel.

A render log is useful evidence that a component function executed.

It is not proof that the browser repainted the entire page.

A component may render without significant DOM changes.

An unrelated Context update may legitimately cause consumers to re-render.

And memoization may be unnecessary if rendering is already cheap.

Before optimizing, establish which work is expensive and why it happens.

Then change one relevant factor and measure again.

The objective is not to maximize the number of memoized components.

It is to improve the specific interaction without introducing correctness defects.

## 13. Constraints of a Realistic Interview

A typical technical interview offers limited time.

You cannot redesign an entire frontend architecture from scratch.

When a defect is isolated, prefer a focused correction.

When the defect reveals a broader ownership problem, explain the larger architectural concern, but distinguish the immediate fix from a longer-term improvement.

For example, correcting an incorrect TanStack Query key may be sufficient for the immediate bug.

Centralizing query-key conventions may be a reasonable follow-up.

Migrating the entire application to a different state-management system would be difficult to justify without additional evidence.

A good engineer can distinguish an urgent repair from a strategic refactor.

## 14. Communication Under Scrutiny

A practical interviewer may ask:

"How do you know that's the cause?"

"What would happen if two requests complete in the opposite order?"

"Why not simply force a refetch?"

"Would your fix behave correctly in Strict Mode?"

"Did you verify that the component was remounted rather than re-rendered?"

"Does your solution still work when the hotel changes?"

These are not necessarily hostile questions.

They are opportunities to demonstrate that you understand the mechanism.

A strong response states the relevant invariant, explains the evidence, and describes a verification step.

If the interviewer exposes a weakness in your proposed fix, adapt.

Do not defend a broken solution merely because it was your first idea.

## 15. The Completion Standard

Completing the manuscripts of SE250 does not mean mastering React.

Even listening carefully to all six lectures establishes understanding, not necessarily independent proficiency.

This studio provides stronger evidence.

You should be able to read unfamiliar React code, predict its behavior, identify the cause of an observed defect, implement a correction, and verify it.

Ideally, you can do this without AI generating the diagnosis.

The goal is not to reject AI assistance permanently.

It is to ensure that you understand the application well enough to judge whether an AI-generated suggestion is correct.

Once you can independently investigate a React problem, AI becomes a useful collaborator rather than an invisible source of truth.

---

# The Oral Examination

These questions concern investigation judgment. The scenario-specific diagnoses remain deliberately undisclosed until the practical exercises.

### Question 1 — The Wrong Value

A component displays an incorrect server-derived value.

What evidence would you collect before changing its state-management implementation?

### Question 2 — The Rendering Complaint

A developer reports that a component re-renders fifty times.

Does that establish a performance defect?

How would you investigate?

### Question 3 — The Intermittent Bug

A problem occurs only when the user navigates rapidly between two pages.

How would you make the problem reproducible?

### Question 4 — The Code Review

A colleague proposes adding a `useEffect` that copies a changing prop into local state.

What questions would you ask before accepting the change?

### Question 5 — The Interview Defense

You've implemented a fix that passes the original reproduction.

The interviewer asks whether it handles unmounting, repeated interactions, and unusual response ordering.

How do you respond?

---

# Solutions and Discussion

### Question 1

Establish the backend's authoritative result, the request parameters, the cache identity, the current component state, and the sequence of relevant updates.

Trace the value from its original source to the rendered interface.

### Question 2

No.

Rendering frequency alone does not establish user-visible cost.

Measure the component's rendering work and correlate it with an actual slow interaction.

Investigate whether rendering was necessary and whether the work is expensive enough to matter.

### Question 3

Control the timing of relevant asynchronous operations.

Use delayed or manually resolved promises to reproduce specific completion orders.

Avoid relying on random network latency or arbitrary sleeps.

### Question 4

Ask who should own the value, whether it is truly independent state, whether the component should preserve user edits, and whether a derived expression or component identity change would express the requirement more directly.

### Question 5

Treat those questions as legitimate verification requirements.

Describe additional tests and execute them when possible.

A fix that handles only the original happy path may not be sufficient.

---

# The Mental Model Worth Keeping

A React bug is usually not mysterious once you identify the failed contract.

State snapshots explain which values callbacks read.

Component identity explains which local state React preserves.

Effects explain the lifetime of external synchronization.

Query keys and invalidation explain the identity and freshness of cached server data.

Rendering and profiling explain where work is performed.

Server/client boundaries explain where code executes and what data is exposed.

The practical debugging loop is:

**Establish the invariant. Reproduce the violation. Trace the mechanism. Make the smallest defensible correction. Verify the behavior under conditions that previously failed.**

---

# Next Step — From React Education to Interview Competence

This concludes the six-lecture SE250 elective.

The course has provided the conceptual foundation for independent React work. The studio now tests whether that understanding can be applied to unfamiliar code.

A successful studio run can become a focused React debugging session in the repository's Interview Lab.

Use its practical European product-company profile unless a real job description or interview invitation provides more specific evidence.

The result should be an assessment of demonstrated reasoning, correctness, communication, and trade-off judgment.

Do not automatically mark the course as mastered because its manuscript exists.

*The spoken lecture ends here. The following material contains the practical studio packets and must be completed independently before consulting the answer key.*

---

# Practical Studio — Four Debugging Incidents

## Studio Rules

Work through the cases in order or select one according to a current weakness.

For each case, save a short investigation note containing the symptom, prediction, evidence, root cause, fix, and verification results.

Do not ask Cursor to diagnose the issue before your first attempt.

Cursor may scaffold the project, install dependencies, and apply code you've decided to write.

When you finish a case, ask AI to review your explanation and challenge any unsupported assumptions.

Each case has a specific acceptance contract.

A passing application is necessary, but not sufficient: you must explain why the correction works.

---

# Case A — The Availability Cache That Lies

## Business Context

The booking platform displays two hotels.

Hotel Aurora has one available room.

Canal House has three available rooms.

Customers can reserve a room from either hotel card.

The backend maintains the authoritative inventory.

The frontend uses TanStack Query to load availability and submit reservations.

## Starting Symptom

The two hotel cards sometimes display information belonging to the wrong hotel.

After reserving a room, the displayed inventory may remain unchanged.

The backend's inventory updates correctly.

The interviewer asks:

"Can you investigate why the frontend disagrees with the server?"

## Environment

Create a Vite React and TypeScript application with TanStack Query v5.

```bash
npm create vite@latest react-studio -- --template react-ts
cd react-studio
npm install
npm install @tanstack/react-query
npm install -D vitest jsdom \
  @testing-library/react \
  @testing-library/dom \
  @testing-library/user-event \
  @testing-library/jest-dom
```

Use each case as a separate component module. For Case A, render `AvailabilityStudio` inside a QueryClientProvider.

## Source File — AvailabilityStudio.tsx

The application uses a small in-memory inventory service. It intentionally avoids a real backend so that the investigation remains focused on frontend data ownership.

```tsx
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

export type HotelId = "aurora" | "canal";

type Availability = {
  hotelId: HotelId;
  remaining: number;
};

const initialStock = {
  aurora: 1,
  canal: 3,
};

const stock: Record<HotelId, number> = {
  ...initialStock,
};

export function resetStock() {
  Object.assign(stock, initialStock);
}

const sleep = (ms: number) =>
  new Promise<void>(resolve => setTimeout(resolve, ms));

async function fetchAvailability(
  hotelId: HotelId
): Promise<Availability> {
  await sleep(60);

  console.log("FETCH", hotelId);

  return {
    hotelId,
    remaining: stock[hotelId],
  };
}

async function reserve(
  hotelId: HotelId
): Promise<{ hotelId: HotelId }> {
  await sleep(60);

  if (stock[hotelId] === 0) {
    throw new Error("Sold out");
  }

  stock[hotelId] -= 1;

  console.log("RESERVED", hotelId, stock[hotelId]);

  return { hotelId };
}

function HotelCard({
  hotelId,
  name,
}: {
  hotelId: HotelId;
  name: string;
}) {
  const queryClient = useQueryClient();

  const availability = useQuery({
    queryKey: ["availability"],
    queryFn: () => fetchAvailability(hotelId),
    staleTime: Infinity,
  });

  const booking = useMutation({
    mutationFn: () => reserve(hotelId),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["availability", hotelId],
      });
    },
  });

  return (
    <section aria-label={name}>
      <h2>{name}</h2>

      <p>
        Rooms left:{" "}
        {availability.data?.remaining ?? "Loading"}
      </p>

      <p>
        Data source:{" "}
        {availability.data?.hotelId ?? "None"}
      </p>

      <button
        disabled={booking.isPending}
        onClick={() => booking.mutate()}
      >
        Reserve {name}
      </button>

      {booking.isError && (
        <p role="alert">{booking.error.message}</p>
      )}

      {booking.isSuccess && (
        <p role="status">Reservation succeeded</p>
      )}
    </section>
  );
}

export function AvailabilityStudio() {
  return (
    <main>
      <h1>Hotel Availability</h1>

      <HotelCard hotelId="aurora" name="Hotel Aurora" />
      <HotelCard hotelId="canal" name="Canal House" />
    </main>
  );
}
```

## Initial Investigation

Before executing the code, answer:

1. What cached queries should exist after the page loads?
2. Can the cache distinguish Aurora from Canal House?
3. What do you expect the two `Data source` fields to display?
4. What should happen after a successful reservation?
5. Which part of the implementation communicates that the cached data has become outdated?

Write your prediction.

Then run the application.

Observe both cards.

Reserve Aurora's final room.

Compare the displayed inventory with the backend's in-memory stock, visible through the console logs.

## Evidence Packet A1 — Query Inspection

If the behavior remains unclear, inspect the QueryClient cache with TanStack Query Devtools or log the query cache entries.

Identify the stored query keys and their data.

Do not modify the application yet.

Explain whether two logically different pieces of server data have been assigned one identity.

## Evidence Packet A2 — Mutation Inspection

Inspect the mutation's `onSuccess` callback.

Determine which query keys it attempts to invalidate.

Compare those keys with the keys actually registered by the queries.

Explain whether the invalidation matches the intended cached data.

## Required Correction

Implement a correction that satisfies all of the following:

- Hotel Aurora and Canal House have independent cached availability.
- A successful reservation causes the affected availability to refresh.
- A failed reservation is not displayed as successful.
- The UI does not claim that cached availability guarantees a room can still be booked.
- The correction does not require copying availability into a second global store.

## Regression Test

Configure Vitest with jsdom and Testing Library.

The following test is intentionally designed to fail against the broken implementation.

```tsx
import {
  beforeEach,
  expect,
  it,
} from "vitest";

import {
  render,
  screen,
  within,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import {
  AvailabilityStudio,
  resetStock,
} from "./AvailabilityStudio";

beforeEach(() => {
  resetStock();
});

function renderStudio() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <AvailabilityStudio />
    </QueryClientProvider>
  );
}

it("keeps availability independent by hotel", async () => {
  renderStudio();

  const aurora = within(
    screen.getByRole("region", {
      name: "Hotel Aurora",
    })
  );

  const canal = within(
    screen.getByRole("region", {
      name: "Canal House",
    })
  );

  expect(
    await aurora.findByText("Rooms left: 1")
  ).toBeInTheDocument();

  expect(
    await canal.findByText("Rooms left: 3")
  ).toBeInTheDocument();
});

it("refreshes availability after reservation", async () => {
  const user = userEvent.setup();

  renderStudio();

  const aurora = within(
    screen.getByRole("region", {
      name: "Hotel Aurora",
    })
  );

  await aurora.findByText("Rooms left: 1");

  await user.click(
    aurora.getByRole("button", {
      name: "Reserve Hotel Aurora",
    })
  );

  expect(
    await aurora.findByText("Rooms left: 0")
  ).toBeInTheDocument();
});
```

The test setup should import `@testing-library/jest-dom/vitest` through a Vitest setup file.

## Interviewer Follow-Ups

After implementing your fix, answer:

**"Why not call `refetch()` manually from the button handler?"**

**"What if availability depends on dates and occupancy, not only hotel ID?"**

**"What if a reservation affects several search-result queries?"**

**"What if another customer books the last room while our cached value is still positive?"**

**"What changes when this becomes a multi-tenant application?"**

Your answers should distinguish cache identity, freshness, business authority, and security boundaries.

---

# Case B — The Guest Who Inherited Alice's Notes

## Business Context

A booking form maintains a list of guests.

Each guest can have an editable note.

The user can remove guests and reorder them.

The application also has global display settings.

## Starting Symptom

A customer writes a note for Alice.

They remove Alice from the booking.

The note unexpectedly appears under Bob.

Separately, the engineering team complains that changing an unrelated display setting causes the guest rows to render again.

The interviewer asks:

"Are these two symptoms caused by the same mechanism?"

## Source File — GuestStudio.tsx

This application intentionally combines dynamic list state with a broad Context provider.

```tsx
import {
  createContext,
  useContext,
  useState,
} from "react";

type Guest = {
  id: string;
  name: string;
};

const initialGuests: Guest[] = [
  { id: "a", name: "Alice" },
  { id: "b", name: "Bob" },
  { id: "c", name: "Charlie" },
];

type Settings = {
  currency: string;
  theme: string;
};

const SettingsContext = createContext<Settings>({
  currency: "EUR",
  theme: "light",
});

function GuestRow({ guest }: { guest: Guest }) {
  const settings = useContext(SettingsContext);
  const [note, setNote] = useState("");

  console.count(`GuestRow rendered: ${guest.name}`);

  return (
    <li>
      <strong>{guest.name}</strong>

      <span> — {settings.currency}</span>

      <label>
        Note for {guest.name}
        <input
          value={note}
          onChange={event => setNote(event.target.value)}
        />
      </label>
    </li>
  );
}

export function GuestStudio() {
  const [guests, setGuests] =
    useState(initialGuests);

  const [theme, setTheme] = useState("light");

  const settings = {
    currency: "EUR",
    theme,
  };

  function removeFirst() {
    setGuests(current => current.slice(1));
  }

  function reverseGuests() {
    setGuests(current => [...current].reverse());
  }

  return (
    <SettingsContext.Provider value={settings}>
      <main>
        <h1>Booking Guests</h1>

        <button onClick={removeFirst}>
          Remove first guest
        </button>

        <button onClick={reverseGuests}>
          Reverse order
        </button>

        <button
          onClick={() =>
            setTheme(current =>
              current === "light" ? "dark" : "light"
            )
          }
        >
          Toggle theme
        </button>

        <p>Current theme: {theme}</p>

        <ul>
          {guests.map((guest, index) => (
            <GuestRow
              key={index}
              guest={guest}
            />
          ))}
        </ul>
      </main>
    </SettingsContext.Provider>
  );
}
```

## Initial Investigation

Start by predicting what happens to guest notes after removing Alice.

Does React preserve the state belonging to Bob, or the state associated with a particular position in the list?

Then predict what happens when the theme changes.

Which components consume the Context?

Does the relevant currency value actually change?

Does this necessarily imply a DOM remount?

Run the application.

Enter different notes for Alice, Bob, and Charlie.

Remove Alice.

Observe the result.

Next, reload the page and toggle the theme while watching render logs or React DevTools.

## Evidence Packet B1 — Component Identity

Inspect the keys passed to `GuestRow`.

Consider what happens to the first element's key when Alice is removed.

Compare the identity of the React component with the identity of the underlying guest.

## Evidence Packet B2 — Context Propagation

Inspect which components consume `SettingsContext`.

Determine whether changing the provided value can cause consumers to re-render, even if they only use the currency field.

Distinguish:

- Component-function execution.
- Re-rendering.
- Remounting.
- Actual DOM mutation.

These are not interchangeable.

## Required Correction

The application must satisfy three separate requirements.

First, guest notes remain associated with their proper guests through removal and reordering.

Second, changing the theme does not unnecessarily cause guest rows that depend only on currency to perform expensive rendering work.

Third, the solution must not rely on suppressing legitimate React updates through an incorrect custom comparison function.

You may restructure Context, component ownership, or component props.

Explain why you chose your approach.

## Required Behavior Test

Write a React Testing Library test that:

1. Renders the three guests.
2. Types `"Window seat requested"` into Bob's note field.
3. Removes Alice.
4. Confirms Bob still has the note.
5. Reverses the list.
6. Confirms Bob still has the note.

Prefer accessible labels such as `Note for Bob`.

Do not inspect internal `useState` values.

## Performance Investigation

Use React DevTools Profiler to compare guest-row render activity before and after your changes.

Do not declare the optimization successful merely because you added `memo`.

Demonstrate whether unrelated theme updates still cause the guest rows to render.

If the rows are cheap, explain why their re-rendering may not be a meaningful production concern even if the architecture is unnecessarily coupled.

## Interviewer Follow-Ups

**"Why are array-index keys sometimes acceptable?"**

**"Would wrapping `GuestRow` in `React.memo` fix every Context-related re-render?"**

**"What if guest notes must survive unmounting the entire booking form?"**

**"What if the user switches between two separate reservations?"**

**"How would you decide whether this deserves a global store?"**

---

# Case C — The Custom Hook That Refuses to Die

## Business Context

The hotel dashboard displays a live counter representing how long a hotel-monitoring session has been active.

When the selected hotel changes, a new monitoring session begins.

When the component is removed, the monitoring process must stop.

## Starting Symptom

The counter reaches one and stops.

After switching hotels, the log messages still mention the previous hotel.

In development, several timers appear to remain active.

The interviewer asks:

"Is React Strict Mode creating the bug, or exposing it?"

## Source File — MonitoringStudio.tsx

The code below contains a custom hook managing a timer.

It intentionally includes lifecycle and closure defects.

```tsx
import {
  useEffect,
  useState,
} from "react";

type HotelId = "A" | "B";

const activeTimers = new Set<
  ReturnType<typeof setInterval>
>();

export function activeTimerCount() {
  return activeTimers.size;
}

function useHotelMonitor(hotelId: HotelId) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(
        `Monitoring Hotel ${hotelId}`,
        `Seconds: ${seconds}`
      );

      setSeconds(seconds + 1);
    }, 1000);

    activeTimers.add(id);

    // No cleanup
  }, []);

  return seconds;
}

function HotelMonitor({
  hotelId,
}: {
  hotelId: HotelId;
}) {
  const seconds = useHotelMonitor(hotelId);

  return (
    <section>
      <h2>Hotel {hotelId}</h2>
      <p>Monitoring seconds: {seconds}</p>
    </section>
  );
}

export function MonitoringStudio() {
  const [hotelId, setHotelId] =
    useState<HotelId>("A");

  const [visible, setVisible] = useState(true);

  return (
    <main>
      <button
        onClick={() =>
          setHotelId(current =>
            current === "A" ? "B" : "A"
          )
        }
      >
        Switch hotel
      </button>

      <button
        onClick={() => setVisible(current => !current)}
      >
        Toggle monitor
      </button>

      {visible && (
        <HotelMonitor hotelId={hotelId} />
      )}

      <p>Selected hotel: {hotelId}</p>
    </main>
  );
}
```

Render the studio under React Strict Mode in development.

## Initial Investigation

Before executing the code, predict:

1. The displayed counter after one second.
2. The displayed counter after three seconds.
3. Which hotel ID appears in logs after switching hotels.
4. What happens to the interval after unmounting.
5. What additional behavior Strict Mode may expose.

Then run the application.

Observe the counter, console logs, and timer activity.

## Evidence Packet C1 — The Closure

Identify the render in which the interval callback was created.

Which values did it capture?

Does updating React state modify those captured local values?

## Evidence Packet C2 — Dependencies

Examine the Effect's dependency array.

Which changing values influence the synchronization process?

Does the Effect correctly represent a monitoring session associated with the selected hotel?

## Evidence Packet C3 — Cleanup

Inspect what happens when the component unmounts.

Does the timer stop?

Does switching hotels establish the correct monitoring lifetime?

Would removing Strict Mode make the production behavior correct?

## Required Correction

The monitor must satisfy these requirements:

- It increments once per second while active.
- Its current hotel identity is correct.
- Switching hotels begins a new monitoring session.
- The displayed elapsed time resets appropriately for the new session.
- Unmounting stops all associated timers.
- Development Strict Mode does not leave leaked timers.
- The solution does not rely on an arbitrary ref guard that merely hides duplicate Effect setup.

You may use component identity, functional state updates, correct dependencies, and cleanup.

Explain how these mechanisms interact.

## Verification

Create a test or controlled experiment using fake timers.

Advance time and verify that the counter progresses.

Switch hotels and verify the appropriate reset.

Unmount the monitor and confirm that its timer is no longer active.

Use `activeTimerCount()` or another suitable instrumentation mechanism to inspect resource lifetime.

Make sure your instrumentation itself is updated correctly when timers are removed.

For automated tests, clear fake timers between tests to avoid cross-test contamination.

## Interviewer Follow-Ups

**"Why does the counter become stuck at one?"**

**"Why not simply add `seconds` to the dependency array?"**

**"What does Strict Mode actually do to Effects?"**

**"Should changing hotel identity reset state through an Effect or by remounting a keyed component?"**

**"What changes if the callback receives updates through a WebSocket rather than an interval?"**

---

# Case D — The Page That Disagrees with Its Own HTML

## Business Context

The hotel catalogue has recently adopted Next.js App Router.

The page displays public hotel information and an interactive booking offer.

The server has access to additional supplier information that the browser does not need.

## Starting Symptom

A user with a previously saved currency preference sees a hydration warning on the first page load.

The initial server response displays the default currency, but the browser expects another value.

A security reviewer also reports that the application sends more hotel data to the browser than the booking widget requires.

The interviewer asks:

"Can you explain both problems without treating Server Components and Client Components as separate applications?"

## Environment

Use a Next.js App Router project with TypeScript.

```bash
npx create-next-app@latest next-boundary-studio \
  --typescript --eslint --app --src-dir --use-npm

cd next-boundary-studio
npm run dev
```

## Source File — app/page.tsx

The page is a Server Component.

It retrieves a hotel record containing public and internal fields.

The internal token is deliberately fake. Never use real credentials for this exercise.

```tsx
import HotelOffer from "./hotel-offer";

export default async function Page() {
  const hotel = {
    id: "aurora",
    name: "Hotel Aurora",
    nightlyPriceEur: 180,
    description: "A hotel near the canal.",

    internalSupplierCommission: 0.17,
    supplierApiToken: "DEMO_ONLY_NOT_A_REAL_SECRET",
  };

  return (
    <main>
      <h1>{hotel.name}</h1>
      <p>{hotel.description}</p>

      <HotelOffer hotel={hotel} />
    </main>
  );
}
```

## Source File — app/hotel-offer.tsx

The interactive component uses a browser preference to decide how to display currency.

```tsx
"use client";

import { useState } from "react";

type Hotel = {
  id: string;
  name: string;
  nightlyPriceEur: number;
  description: string;
  internalSupplierCommission: number;
  supplierApiToken: string;
};

export default function HotelOffer({
  hotel,
}: {
  hotel: Hotel;
}) {
  const [guests, setGuests] = useState(2);

  const currency =
    typeof window === "undefined"
      ? "EUR"
      : window.localStorage.getItem("currency") ?? "EUR";

  return (
    <section>
      <h2>Booking Offer</h2>

      <p>Currency: {currency}</p>

      <p>
        Nightly price: {hotel.nightlyPriceEur}
      </p>

      <p>Guests: {guests}</p>

      <button
        onClick={() => setGuests(current => current + 1)}
      >
        Add guest
      </button>
    </section>
  );
}
```

## Initial Investigation

Open the application in a browser.

Set a currency preference using DevTools:

```js
localStorage.setItem("currency", "GBP");
```

Reload the page.

Inspect the terminal and browser console.

Compare the server-rendered HTML with the browser's initial render expectation.

Why can a Client Component participate in server prerendering?

Why is checking whether `window` exists not sufficient to guarantee a hydration match?

## Evidence Packet D1 — Execution Environment

Identify which code runs in the server environment.

Identify which code must also execute in the browser.

Explain the meaning of the `"use client"` directive.

Does it universally prevent initial server-side HTML generation?

## Evidence Packet D2 — The Serialized Boundary

Inspect what the Server Component passes into `HotelOffer`.

Which fields does the Client Component actually use?

Which fields are unnecessary?

Inspect the initial document and relevant Next.js response payloads using developer tools.

Consider whether data passed through the server/client boundary should be treated as private merely because it originated in a Server Component.

## Required Correction

The page must satisfy these requirements:

- The server-produced HTML and initial browser render agree.
- The saved browser currency preference can still appear after hydration.
- The interactive guest selector continues working.
- The Client Component receives only the public data it requires.
- The solution does not use `suppressHydrationWarning` as a blanket workaround.
- The solution does not move server-only supplier credentials into public environment variables.

## Interviewer Follow-Ups

**"Why is the component called a Client Component if it can be prerendered on the server?"**

**"What happens if the customer's theme must be correct before the first paint?"**

**"Does marking a function with `'use server'` automatically make it secure?"**

**"How would you keep private user-specific data out of a shared server cache?"**

**"Would this internal dashboard necessarily benefit from migrating to Next.js?"**

---

# Integrated Interview Round

After completing the individual cases, perform a simulated debugging interview using one scenario chosen without advance notice.

The recommended default profile is a practical European product-company full-stack position.

The interviewer should act as a collaborative but technically demanding senior engineer.

The session should focus on the candidate's investigation rather than framework trivia.

A useful format is:

**Opening:** The interviewer demonstrates the bug and provides the relevant code.

**Investigation:** The candidate predicts the behavior, asks for relevant evidence, and traces the mechanism.

**Implementation:** The candidate proposes and implements a focused correction.

**Verification:** The candidate writes or explains a regression test.

**Review:** The interviewer asks about edge cases, trade-offs, and what the fix does not address.

A realistic simulation should not reveal the answer key, scoring rubric, or planned follow-up questions before the attempt.

The interviewer may provide reasonable clarifications.

If the candidate requests a hint, that assistance should be recorded for the eventual debrief.

---

# Evaluation Rubric

Use the repository's Interview Lab scale from zero to four for each category.

| Competency | Strong performance |
|---|---|
| Problem framing | Establishes expected behavior and relevant invariants |
| React execution model | Correctly reasons about renders, closures, and identity |
| Data ownership | Distinguishes local state, Context, and server caches |
| Investigation | Uses evidence instead of speculative changes |
| Implementation | Produces a focused, correct correction |
| Verification | Tests failure conditions and meaningful edge cases |
| Trade-off judgment | Recognizes simpler and alternative solutions |
| Communication | Explains reasoning clearly without invented certainty |

The scores mean:

- **0 — Not demonstrated:** Absent or substantially incorrect.
- **1 — Weak:** Major gaps or unsupported reasoning.
- **2 — Functional:** Reasonable but incomplete.
- **3 — Strong:** Correct, specific, and well-reasoned.
- **4 — Exceptional:** Particularly rigorous, insightful, and adaptable.

A strong practical performance does not require solving everything instantly.

It does require identifying the relevant mechanisms and establishing evidence for the correction.

Do not convert the score into a fabricated probability of receiving a job offer.

---

# STOP — End of Candidate-Facing Studio

**Do not continue into the diagnostic notes until you have completed at least one independent attempt.**

The following material is for reviewing the work afterward.

Reading it before attempting the cases defeats the central purpose of the studio.

---

# Diagnostic Notes and Reference Solutions

## Case A — Query Identity and Invalidation

The critical defect is that both availability queries use the same key.

The query function depends on `hotelId`, but the key does not include that variable.

TanStack Query therefore treats the two requests as belonging to the same cached query identity.

The correct key must distinguish hotels.

```tsx
const availability = useQuery({
  queryKey: ["availability", hotelId],
  queryFn: () => fetchAvailability(hotelId),
  staleTime: Infinity,
});
```

The second defect concerns invalidation.

The mutation invalidates `["availability", hotelId]`, but the original query was registered under `["availability"]`.

The invalidation therefore does not match that query.

After correcting the query key, the intended invalidation can target the appropriate cached entry.

```tsx
onSuccess: async () => {
  await queryClient.invalidateQueries({
    queryKey: ["availability", hotelId],
  });
}
```

A successful reservation must not be confused with a guarantee that a previously cached availability value remains correct.

The backend remains authoritative.

For a real hotel platform, query identity may include hotel ID, dates, occupancy, room category, and relevant authorization context.

A reservation mutation may also need to invalidate search-result queries containing availability summaries.

### Alternative solutions

A different caching library or an explicitly managed store could solve the problem, but neither is necessary for this exercise.

The smallest correction is to establish correct data identity and invalidation.

Forcing an unrelated state update or adding an arbitrary `key` to remount the card would be a workaround rather than a principled solution.

### What a strong interviewer answer sounds like

"The cache key doesn't include the hotel ID even though the query function depends on it. Both cards therefore refer to one logical query. The mutation also invalidates a key that doesn't match the original entry. I'd align query identity and invalidation, then test both independent hotel data and the post-reservation refresh."

---

## Case B — Identity and Context Are Separate Problems

The guest-note bug comes from using the array index as a component key.

When Alice is removed, Bob moves from index one to index zero.

React may preserve the component state associated with the old index-zero position.

That state previously belonged to Alice.

The correct key is the stable guest ID.

```tsx
{guests.map(guest => (
  <GuestRow
    key={guest.id}
    guest={guest}
  />
))}
```

Now component identity follows the guest rather than the list position.

The Context issue is separate.

The provider creates a combined settings value containing currency and theme.

Changing the theme changes the provided context value.

Components consuming that context may re-render even if they only use the currency.

A solution can separate the currency and theme responsibilities.

For example, use an independent currency context for components that only need currency.

Alternatively, pass the currency through props if the component structure is small and direct.

For more complicated shared state, selector-based subscriptions may become appropriate.

### Important qualification

Removing the broad Context dependency does not automatically guarantee that guest rows never render again.

Their parent can still re-render and pass props.

`React.memo` may be useful if their props remain stable and rendering cost is meaningful.

The correct optimization should be verified with profiling.

### What a strong interviewer answer sounds like

"These are two different mechanisms. The note corruption is a reconciliation identity problem caused by index keys. The rendering complaint comes from broad Context propagation and possibly parent rendering. I'd correct stable identity first, then profile the theme interaction before deciding whether to split Context or memoize the rows."

---

## Case C — Stale Closures, Dependencies, and Cleanup

The interval callback captures `seconds` and `hotelId` from the render in which the Effect was created.

Because the Effect has an empty dependency array, changing the selected hotel does not establish a new monitoring process.

The callback repeatedly requests `setSeconds(seconds + 1)` using the captured value.

If `seconds` was initially zero, the displayed counter may become stuck at one.

The missing cleanup allows intervals to continue running after the component's relevant lifetime has ended.

Strict Mode exposes this problem through additional development setup-and-cleanup checks.

It is not the fundamental cause.

A corrected hook can use a functional state updater and proper cleanup.

```tsx
function useHotelMonitor(hotelId: HotelId) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(`Monitoring Hotel ${hotelId}`);

      setSeconds(previous => previous + 1);
    }, 1000);

    activeTimers.add(id);

    return () => {
      clearInterval(id);
      activeTimers.delete(id);
    };
  }, [hotelId]);

  return seconds;
}
```

This corrects the timer's closure and lifetime behavior.

However, it does not automatically reset local elapsed state when the hotel changes.

One reasonable approach is to give the monitored component a hotel-specific identity.

```tsx
{visible && (
  <HotelMonitor
    key={hotelId}
    hotelId={hotelId}
  />
)}
```

Changing the key remounts the component and initializes a new monitoring session.

Other designs are possible if state must survive switching, but they require an explicit ownership model.

### What a strong interviewer answer sounds like

"The interval captures the initial counter and hotel ID. It never resynchronizes and never cleans up. I'd use a functional updater, include the actual synchronization dependency, and return cleanup. Since the requirement says each hotel starts a new monitoring session, I'd also make that session identity explicit, probably by keying the monitor by hotel ID."

---

## Case D — Hydration and Data Exposure

The hydration problem comes from producing different initial output on the server and browser.

During server prerendering, the currency is `"EUR"`.

During the initial browser render, local storage may provide `"GBP"`.

The two outputs do not match.

The Client Component directive does not prevent server prerendering of its initial HTML.

A straightforward correction is to initialize the currency deterministically and read browser storage after mount.

```tsx
"use client";

import { useEffect, useState } from "react";

type PublicHotel = {
  id: string;
  name: string;
  nightlyPriceEur: number;
};

export default function HotelOffer({
  hotel,
}: {
  hotel: PublicHotel;
}) {
  const [guests, setGuests] = useState(2);

  const [currency, setCurrency] =
    useState<string | null>(null);

  useEffect(() => {
    setCurrency(
      window.localStorage.getItem("currency") ?? "EUR"
    );
  }, []);

  return (
    <section>
      <h2>Booking Offer</h2>

      <p>
        Currency: {currency ?? "Loading preference"}
      </p>

      <p>Nightly price: {hotel.nightlyPriceEur}</p>

      <p>Guests: {guests}</p>

      <button
        onClick={() =>
          setGuests(current => current + 1)
        }
      >
        Add guest
      </button>
    </section>
  );
}
```

The initial server and browser renders now agree on a placeholder.

After hydration, the client updates the displayed preference.

For a preference that must be correct before the first paint, a server-readable cookie and consistent initial rendering may be preferable.

The data-exposure issue is separate.

The Server Component passes the entire hotel object to the Client Component.

That object includes internal fields that the Client Component does not require.

Values crossing the server/client serialization boundary must be treated as client-visible.

The server should pass an explicitly limited public representation.

```tsx
const publicHotel = {
  id: hotel.id,
  name: hotel.name,
  nightlyPriceEur: hotel.nightlyPriceEur,
};

return <HotelOffer hotel={publicHotel} />;
```

Private supplier credentials should remain in server-only data-access code.

A server-side function must also enforce authentication and authorization when appropriate.

Server execution does not make a network-exposed operation automatically secure.

### What a strong interviewer answer sounds like

"The component is marked for client interactivity, but its initial HTML can still be generated on the server. Its initial render must agree with hydration. Here, local storage changes the browser's initial output. I'd make the initial output deterministic and read the preference after mount, or use a server-readable preference if first-paint accuracy matters. Separately, I'd stop passing internal supplier fields through the client boundary."

---

# Course-Level Debrief

## What This Studio Actually Demonstrates

The four cases exercise different parts of React engineering.

Case A tests server-state identity and invalidation.

Case B tests reconciliation identity and rendering ownership.

Case C tests closure semantics and Effect lifetimes.

Case D tests server/client execution boundaries and hydration.

Together they provide a practical measure of whether the candidate can reason about React beyond familiar component syntax.

However, passing these cases does not establish mastery of every React ecosystem technology.

It does not prove expertise in advanced Next.js caching, React Compiler internals, accessibility engineering, or large-scale frontend performance.

Those capabilities require additional practical experience and appropriate focused study.

The important achievement is establishing a reliable mental model for unfamiliar code.

## What to Practice After the Studio

Review only the areas where actual evidence reveals weakness.

If stale closures remain confusing, return to SE250-L01 and L02.

If server-state caching is difficult, review SE250-L03.

If rendering performance reasoning is weak, revisit SE250-L04.

If server/client execution boundaries remain unclear, revisit SE250-L05.

Then repeat a debugging exercise with a different implementation.

Avoid memorizing the exact solutions to these four cases.

The objective is to recognize mechanisms in unfamiliar problems, not remember which line was wrong in a previously solved exercise.

---

# Further Reading

1. **React — State as a Snapshot**  
   https://react.dev/learn/state-as-a-snapshot

2. **React — Preserving and Resetting State**  
   https://react.dev/learn/preserving-and-resetting-state

3. **React — Synchronizing with Effects**  
   https://react.dev/learn/synchronizing-with-effects

4. **React — Lifecycle of Reactive Effects**  
   https://react.dev/learn/lifecycle-of-reactive-effects

5. **React — Strict Mode**  
   https://react.dev/reference/react/StrictMode

6. **React — Profiler**  
   https://react.dev/reference/react/Profiler

7. **React — React Compiler**  
   https://react.dev/learn/react-compiler/introduction

8. **TanStack Query — Query Keys**  
   https://tanstack.com/query/latest/docs/framework/react/guides/query-keys

9. **TanStack Query — Query Invalidation**  
   https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation

10. **TanStack Query — Mutations**  
    https://tanstack.com/query/latest/docs/framework/react/guides/mutations

11. **React Testing Library**  
    https://testing-library.com/docs/react-testing-library/intro/

12. **Next.js — Server and Client Components**  
    https://nextjs.org/docs/app/getting-started/server-and-client-components

13. **React — hydrateRoot**  
    https://react.dev/reference/react-dom/client/hydrateRoot

14. **Next.js — Data Security**  
    https://nextjs.org/docs/app/guides/data-security

15. **The Modern Software Engineer — Interview Lab Protocol**  
    `book/interview-lab/PROTOCOL.md`

Cross-reference SE250-L01 through SE250-L05 for the underlying mechanisms, SE240-L06 for broader testing strategy, and the Interview Lab for realistic technical-interview simulations.

---

# Dense Cheatsheet — React Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE250 — REACT ENGINEERING INTERVIEW CARD
==================================================

THE DEBUGGING LOOP
------------------
1. Establish expected behavior.
2. Reproduce the defect.
3. Identify the violated invariant.
4. Trace relevant execution/data.
5. Form a testable hypothesis.
6. Make a focused correction.
7. Verify edge cases.
8. Explain trade-offs.

RENDER SNAPSHOTS
----------------
Each render has its own:
- props
- state values
- local variables
- callbacks and closures

setState does not mutate
the current render's variable.

Use functional updaters when
new state depends on previous state.

RENDERING
---------
Render = calculate UI.
Commit = apply DOM changes.
Paint = browser visual work.

Re-render != remount.
Render logs != DOM commit count.

COMPONENT IDENTITY
------------------
State follows component identity.

Important:
- component type
- tree position
- key

Stable entity ID -> stable list identity.
Index key -> position identity.
Changing key -> reset/remount.

EFFECTS
-------
Effect = external synchronization process.

Setup -> cleanup -> replacement setup.

Dependencies describe reactive values
read by the Effect.

Missing dependency -> stale synchronization.
Missing cleanup -> leaked external work.

Strict Mode exposes lifecycle mistakes.

CLOSURES
--------
Old callback retains old render values.

Timer:
setCount(count + 1)
may repeatedly request same value.

Prefer functional updater:
setCount(c => c + 1)

ASYNC RACES
-----------
Request A starts.
Request B starts.
B finishes first.
A finishes last.

Prevent obsolete A from replacing B:
- invalidate old Effect work
- cancel when appropriate
- associate data with request identity
- render only matching data

SERVER STATE
------------
Backend owns authoritative result.

Query cache stores representations.

Query key must identify
the actual requested data.

Missing query parameters in key
can cause cache collisions.

MUTATIONS
---------
A mutation does not automatically
update every affected query.

Invalidate/reconcile deliberately.

Backend remains authoritative.

OPTIMISTIC UPDATES
------------------
Temporary client assumption.
Requires failure reconciliation.

Do not claim payment or reservation
success before backend confirmation.

CONTEXT
-------
Distributes values.
Not automatically a selective store.

Changing context value can re-render
consumers, even with React.memo.

Split ownership when appropriate.

PERFORMANCE
-----------
Measure before optimizing.

React.memo:
skip suitable child renders.

useMemo:
cache calculation result.

useCallback:
cache function identity.

React Compiler:
automatic memoization where supported.

None replaces correct architecture.

TRANSITIONS
-----------
Prioritize suitable non-urgent updates.
Do not move arbitrary CPU work
to another thread.

VIRTUALIZATION
--------------
Reduce active DOM rows for large lists.

SUSPENSE
--------
Coordinates suspending boundaries.
Ordinary Effect fetch doesn't
automatically activate Suspense.

ERROR BOUNDARIES
----------------
Contain descendant rendering errors.
Not universal async exception handlers.

SERVER / CLIENT
---------------
Server Component implementation
does not hydrate in browser.

Client Component can still have
initial HTML prerendered on server.

"use client" != browser-only execution.

Hydration needs matching
server and initial client output.

Serialized client props may be visible.
Never send unnecessary secrets.

TESTING
-------
Assert user-visible invariants.

Race:
resolve B before A,
then verify B remains displayed.

Identity:
edit Bob, remove Alice,
verify Bob retains his note.

Lifecycle:
mount, advance, switch, unmount,
verify no external resource leak.

PERFORMANCE EVIDENCE
--------------------
React Profiler:
rendering work.

Browser Performance:
main-thread and rendering behavior.

Testing Library:
user-visible correctness.

Do not confuse the three.

PRODUCTION QUESTIONS
--------------------
Which state snapshot?
Which component identity?
Which external process?
Which query/cache owner?
Which execution environment?
What actually committed?
What makes old work obsolete?
What evidence proves the fix?

INTERVIEW RED FLAGS
--------------------
"It re-rendered, so React rebuilt the DOM."
"I'll just add another useEffect."
"I'll force a refetch on every update."
"Strict Mode is the production bug."
"Every shared value belongs in Context."
"Custom hooks automatically share state."
"Memoization fixes correctness bugs."
"Server Components make data private."
"The test passed once, so it's fixed."

SE250 COMPLETION
----------------
L01 — Render snapshots and identity
L02 — Effects, closures, lifecycles
L03 — State ownership and server caching
L04 — Performance, testing, debugging
L05 — SSR, RSC, hydration, deployment
L06 — Integrated debugging studio

FINAL PRINCIPLE
---------------
Understand.
Predict.
Investigate.
Implement.
Verify.
Explain.

Then let AI critique your reasoning.
```
