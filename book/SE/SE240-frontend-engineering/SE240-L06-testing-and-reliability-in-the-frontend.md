---
id: SE240-L06
course: SE240
title: "Testing and Reliability in the Frontend"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S11]
prev: SE240-L05
next: null
---



# SE240 — Browser and Frontend Engineering

## Lecture 06: Testing and Reliability in the Frontend

*How an application can have 1,200 passing tests, 98% code coverage, and still fall apart when an ordinary customer clicks an ordinary button.*

---

# 1. The Booking That Passed Every Test

Your hotel-booking platform has an impressive testing infrastructure. The frontend contains 1,200 automated tests. Vitest executes most of them in seconds, Vue Test Utils verifies the components, and Playwright runs end-to-end scenarios.

Your CI dashboard displays:

```text
Tests passed:       1,200 / 1,200
Statement coverage: 98%
Build:              Successful
Deployment:         Successful
```

The engineering team is reasonably pleased with itself.

Then a customer reports an extraordinary problem. She searches for a hotel in Berlin and selects November 10–13. Then she changes her mind and selects November 17–20. The displayed results update correctly.

She clicks Reserve. The booking confirmation appears.

But the reservation is for **November 10–13**: the dates she originally selected.

You investigate.

The backend created exactly the reservation it was asked to create, and the API contract was satisfied. The frontend submitted the wrong dates.

How?

An earlier availability request completed after a newer request and silently replaced part of the booking state. The interface displayed the latest search dates, while the booking workflow retained stale information from the previous search.

We encountered this kind of asynchronous race in SE240-L03. But here's the more interesting question:

**Why didn't any of the 1,200 tests catch it?**

The search component had tests.

The date picker had tests.

The booking composable had tests.

The API adapter had tests.

Every component behaved correctly under the conditions the tests provided.

The failure emerged from the timing and interaction between them.

The tests verified isolated pieces. The customer exercised the system.

And that's our subject today.

Software testing is not fundamentally about accumulating green checkmarks.

It's about developing justified confidence that a system will behave correctly under the conditions that matter. Those are two very different ambitions.

---

# 2. What Does a Test Actually Prove?

Consider this test:

```typescript
import { describe, expect, it } from "vitest";

function calculateNights(
  checkInDay: number,
  checkOutDay: number
) {
  return checkOutDay - checkInDay;
}

describe("calculateNights", () => {
  it("calculates a three-night stay", () => {
    expect(calculateNights(10, 13)).toBe(3);
  });
});
```

The test passes.

What have we established?

Only that this implementation produces `3` for those particular inputs.

We haven't established that it correctly handles:

- Different months.
- Leap years.
- Invalid date ranges.
- Daylight-saving transitions.
- The application's actual date representation.

The test isn't worthless. It's simply narrower than its reassuring green status might suggest.

A test has three essential ingredients:

1. A system or behavior under examination.
2. A particular setup and action.
3. An expectation about the result.

The third ingredient is especially important. A test needs an **oracle**: some independent basis for deciding what correct behavior means.

Imagine writing:

```typescript
expect(calculatePrice(input)).toBe(
  calculatePrice(input)
);
```

This is technically an assertion, but it proves almost nothing useful.

Both sides call the same implementation. If that implementation is wrong, they may agree perfectly.

A more subtle version of this mistake occurs when developers copy the production algorithm into the test and use it to calculate the expected result. Now the application and its test may share the same conceptual error.

The purpose of testing isn't merely to execute code.

It's to compare actual behavior against expectations derived from requirements, invariants, contracts, or independently understood examples.

## 2.1 Confidence is not certainty

Even a large and carefully designed test suite cannot establish that an arbitrary program is correct under every possible condition. There are too many possible inputs, environmental conditions, interaction sequences, network delays, and external failures.

But testing can provide meaningful evidence. A good test suite concentrates that evidence around behavior that matters.

For our hotel platform, this includes questions like:

Does selecting a new date range replace the previous search correctly?

Can an outdated network response overwrite newer state?

Can the customer submit a reservation twice? Does a failed booking produce a truthful interface state?

Can a customer using only the keyboard complete checkout?

These are much more valuable questions than whether a private helper function was called exactly three times.

---

# 3. The Four Levels of Testing

Testing strategies are often described using a pyramid.

At the bottom are numerous small tests.

Higher up are larger, more expensive tests involving more components of the system.

The model is useful, although real applications don't need to obey one universal distribution. Let's investigate the levels through our booking platform.

## 3.1 Unit tests: Is this piece of logic correct?

Suppose reservations may be cancelled only before a particular deadline. We can express a simplified rule:

```typescript
interface CancellationPolicy {
  status: "pending" | "confirmed" | "cancelled";
  deadline: number;
  now: number;
}

export function canCancel(
  booking: CancellationPolicy
): boolean {
  return (
    booking.status === "confirmed" &&
    booking.now < booking.deadline
  );
}
```

Now test several meaningful conditions:

```typescript
import { describe, expect, it } from "vitest";
import { canCancel } from "./cancellation";

describe("cancellation policy", () => {
  it("allows confirmed bookings before the deadline", () => {
    expect(canCancel({
      status: "confirmed",
      now: 100,
      deadline: 200
    })).toBe(true);
  });

  it("rejects cancellation at the deadline", () => {
    expect(canCancel({
      status: "confirmed",
      now: 200,
      deadline: 200
    })).toBe(false);
  });

  it("rejects already cancelled bookings", () => {
    expect(canCancel({
      status: "cancelled",
      now: 100,
      deadline: 200
    })).toBe(false);
  });
});
```

These tests are quick.

They need no browser, no database, and no Vue application. And they cover important business decisions.

This is where unit testing shines: **small, well-defined behavior with clear expected outcomes**.

However, there's a limitation. The tests prove that `canCancel()` behaves correctly for those cases.

They don't prove that the checkout page calls it correctly, or that the frontend and backend agree on cancellation rules.

And they certainly don't prove that an unauthorized customer cannot cancel someone else's reservation.

Those are different questions requiring different tests.

## 3.2 Component tests: Does the UI behave correctly?

Now consider a Vue component:

```vue
<script setup lang="ts">
defineProps<{
  price: number;
  currency: string;
  disabled: boolean;
}>();

const emit = defineEmits<{
  reserve: [];
}>();
</script>

<template>
  <div>
    <p>{{ price }} {{ currency }}</p>

    <button
      :disabled="disabled"
      @click="emit('reserve')"
    >
      Reserve
    </button>
  </div>
</template>
```

We can mount the component with Vue Test Utils and interact with it.

```typescript
import { mount } from "@vue/test-utils";
import { expect, it } from "vitest";
import HotelOffer from "./HotelOffer.vue";

it("emits reservation intent", async () => {
  const wrapper = mount(HotelOffer, {
    props: {
      price: 149,
      currency: "EUR",
      disabled: false
    }
  });

  await wrapper.get("button").trigger("click");

  expect(wrapper.emitted("reserve")).toHaveLength(1);
});

it("prevents clicking when disabled", async () => {
  const wrapper = mount(HotelOffer, {
    props: {
      price: 149,
      currency: "EUR",
      disabled: true
    }
  });

  expect(wrapper.get("button").attributes("disabled"))
    .toBeDefined();
});
```

These tests verify the component's rendered behavior and event interface. They're useful because Vue components are not merely ordinary functions: they participate in a reactive lifecycle. Props change, events fire, DOM updates are scheduled, and conditional elements appear and disappear.

Component tests allow us to examine those behaviors without launching the entire product.

### An asynchronous detail

Vue batches DOM updates. That means changing reactive data doesn't necessarily update the DOM synchronously. Vue Test Utils methods such as `trigger()` and `setValue()` can be awaited to allow Vue's corresponding update cycle to complete. For external promises, utilities such as `flushPromises()` can help settle promise continuations during tests.

But there is a distinction:

**Waiting for Vue's DOM update is not the same as waiting for every arbitrary asynchronous operation in the application.**

A test may need to control the relevant request or timer explicitly. And `flushPromises()` isn't a magical command that completes unresolved network requests or advances all future timers.

## 3.3 Integration tests: Do collaborating parts agree?

Now imagine the reservation form interacting with:

- A validation schema.
- A pricing module.
- A reservation workflow.
- An API adapter.
- A shared store.

Each part has independent tests. But do they work together?

An integration test might mount the reservation view with its real composables and store, while substituting a controlled implementation of the remote API.

The test could verify that:

1. The customer selects a room.
2. The date range is validated.
3. The reservation workflow receives the selected dates.
4. The correct request payload is constructed.
5. The confirmation state appears only after success.

Unlike a tiny unit test, this crosses several application boundaries.

That's the point.

Many bugs occur not inside modules, but where modules exchange information.

For example:

```text
DatePicker
    │
    ▼
SearchStore
    │
    ▼
BookingWorkflow
    │
    ▼
ReservationAPI
```

If the date picker emits a string but the workflow assumes a different date representation, every module could appear reasonable in isolation while the integration is wrong. An integration test can expose the disagreement.

## 3.4 End-to-end tests: Can the customer actually accomplish the task?

Finally, consider a real browser test. The customer opens the application, searches for Berlin, selects dates, chooses a hotel, confirms a reservation, and sees a confirmation. A tool such as Playwright can automate this journey.

```typescript
import { test, expect } from "@playwright/test";

test("customer can complete a reservation", async ({ page }) => {
  await page.goto("/search");

  await page.getByRole("textbox", {
    name: "Destination"
  }).fill("Berlin");

  await page.getByRole("button", {
    name: "Search hotels"
  }).click();

  await expect(
    page.getByRole("heading", {
      name: "Hotels in Berlin"
    })
  ).toBeVisible();

  await page.getByRole("button", {
    name: "View Hotel Alexander"
  }).click();

  await page.getByRole("button", {
    name: "Reserve room"
  }).click();

  await expect(
    page.getByRole("heading", {
      name: "Reservation confirmed"
    })
  ).toBeVisible();
});
```

This is an illustrative test assuming the application exposes those controls and accessible names. A complete test would also establish the intended dates, user identity, and backend test data.

But the important part is its perspective.

It doesn't directly call the reservation function. It interacts through the UI, and the browser performs routing, event handling, rendering, and network communication. This gets us substantially closer to the customer's actual experience.

There is still an important question, however.

**What exactly lies behind the browser during the test?**

---

# 4. A Fake Backend Can Give You Real Confidence—About the Wrong Thing

Suppose your Playwright test intercepts the reservation request:

```typescript
await page.route("**/api/reservations", async route => {
  await route.fulfill({
    status: 201,
    contentType: "application/json",
    body: JSON.stringify({
      reservationId: "9821",
      status: "confirmed"
    })
  });
});
```

The customer completes the reservation flow.

The test passes.

What have we proved?

We've established that the frontend can process this particular mocked response and display the expected interface. That's useful.

But have we proved that the real backend accepts the request?

No.

Have we proved that the database commits the reservation correctly?

No.

Have we proved that authentication cookies, proxy configuration, request validation, and deployed API routes work together?

Again, no.

And now we've reached one of the most important principles in testing:

**The more of the system you replace with mocks, the fewer real interactions you're verifying.**

This doesn't mean mocks are bad. They're indispensable for many situations. They make failures reproducible, allow tests to simulate rare conditions, and help isolate frontend behavior from unstable external dependencies. But their scope must be understood.

## 4.1 Three different versions of an end-to-end test

Imagine testing the same booking workflow in three environments.

| Environment | What it verifies | What it misses |
|---|---|---|
| Browser + mocked APIs | UI behavior and client-side integration | Real backend behavior |
| Browser + real test backend | Full application interaction | Some production infrastructure differences |
| Browser + production-like deployment | Browser, APIs, deployment configuration, and more infrastructure | Still cannot reproduce every real-world condition |

A browser test isn't automatically a full-system test merely because it uses Playwright.

Its actual coverage depends on which components participate.

This is why test names should be interpreted carefully. The useful question is not:

"Do we have E2E tests?"

It's:

"Which real boundaries do those tests actually cross?"

## 4.2 Mock at boundaries, not everywhere

Suppose you're testing the booking interface. One approach is to mock every internal function:

```text
Mock date picker
Mock store
Mock booking composable
Mock price calculation
Mock API adapter
```

Now the test exercises very little of the actual application.

A more useful integration approach might retain the real date picker, state management, and booking workflow while replacing only the external network boundary. That allows the modules to interact naturally, while the test still remains controlled and deterministic.

This is often a better balance.

As a practical rule:

> Preserve the real behavior you're trying to verify. Substitute dependencies that are outside the test's intended responsibility.

---

# 5. The Mocking Paradox: Testing Your Own Assumptions

Let's return to our opening production bug. The frontend submits an old date range after a newer search.

Why didn't tests catch it?

Perhaps the search component used:

```typescript
vi.mock("./hotelApi", () => ({
  fetchHotels: vi.fn().mockResolvedValue([
    { id: 4812, name: "Hotel Alexander" }
  ])
}));
```

Every API request resolves immediately. The test changes the dates, the request completes, and the UI updates. Then the test changes the dates again, the second request completes, and everything works.

But production requests don't necessarily complete in the same order they're initiated.

The mock quietly removed the condition that caused the bug.

This is a subtle danger. A test double isn't merely a replacement implementation. It defines the environment in which the tested code operates. If that environment is unrealistically simple, the test may conceal important failure modes.

## 5.1 Make the race happen deliberately

A better test can control response ordering. Imagine:

```text
Request A: November 10–13
Request B: November 17–20
```

Now force this sequence:

```text
A starts
B starts
B completes
A completes
```

The expected behavior:

**The interface must continue showing the results and booking state associated with B.**

The old response must not overwrite newer information.

This is a high-value test because it exercises a realistic failure mechanism.

We don't need to generate random network chaos. We need to identify a meaningful concurrency scenario and reproduce it deterministically.

Other valuable failure cases include:

- A request returns `401` after authentication expires.
- A reservation receives `409 Conflict`.
- A response arrives after its component has unmounted.
- A network request times out.
- An API returns malformed data.
- A user double-clicks a consequential action.
- A retry occurs after an uncertain operation outcome.

These tests are particularly useful because happy-path testing frequently overlooks them.

The broader idea is called **fault injection**. Instead of waiting for production to produce difficult conditions, we deliberately introduce failures in controlled tests.

---

# 6. Code Coverage: The Number That Looks More Important Than It Is

Let's address the elephant in the CI dashboard.

```text
Statement coverage: 98%
```

That sounds impressive.

But what does it mean?

Depending on the coverage configuration, it means that test execution reached approximately 98% of the measured statements. It doesn't mean 98% of application behavior is correct. Nor does it mean 98% of possible failure scenarios have been tested.

Let's examine a simple function:

```typescript
function canBook(
  availableRooms: number,
  requestedRooms: number
) {
  if (availableRooms >= requestedRooms) {
    return true;
  }

  return false;
}
```

Suppose the tests call:

```typescript
canBook(5, 2);
canBook(0, 1);
```

Both branches execute, and coverage might report excellent results. But what about:

```typescript
canBook(1, -100);
```

The function returns `true`.

Perhaps that shouldn't be allowed.

Coverage doesn't tell us whether meaningful boundary cases were selected.

## 6.1 Different coverage measurements

Common coverage metrics include:

**Statement coverage:** Which statements executed?

**Branch coverage:** Which branches of decisions executed?

**Function coverage:** Which functions executed?

**Line coverage:** Which source lines executed?

They answer related but different questions. Branch coverage is often more informative than simple line coverage for conditional logic.

But even 100% branch coverage doesn't establish complete behavioral correctness.

Suppose a pricing function contains the wrong discount formula. Tests might execute every line and branch while expecting the same incorrect result. The tests and implementation agree, yet the business requirement remains violated.

## 6.2 Mutation testing: A more interesting question

There's a technique called **mutation testing**. Instead of asking whether tests execute the code, mutation testing deliberately modifies the code.

For example, it might change:

```typescript
price > 100
```

to:

```typescript
price >= 100
```

Then it runs the tests.

Do they detect the change?

If the test suite still passes, perhaps it never examined the boundary value.

A mutation that changes program behavior but survives the tests can reveal a weakness. Mutation testing isn't perfect, and it can be computationally expensive. But it illustrates a deeper idea:

**A useful test should be capable of detecting an important incorrect implementation.**

That is more meaningful than simply exercising the implementation.

## 6.3 Coverage is a diagnostic, not a target to worship

A coverage report can help identify large areas of completely untested code.

That's useful. But forcing every module toward 100% coverage can create mountains of low-value tests. You may end up testing trivial getters and framework implementation details while failing to test important booking workflows.

I would much rather maintain:

- Excellent tests for pricing rules.
- Strong tests for reservation-state transitions.
- Meaningful authorization and API contract tests.
- A few reliable critical user journeys.

Than thousands of superficial tests created to satisfy a coverage threshold.

The correct goal is risk reduction. Coverage is one instrument for understanding test quality, not a complete measure of it.

---

# 7. Flaky Tests: When Your Test Suite Becomes a Slot Machine

Imagine a Playwright test that fails every tenth CI run.

You rerun it.

It passes.

You rerun the full suite.

It passes again.

Naturally, someone announces:

"It's just flaky."

And merges the pull request.

This is how test suites gradually lose credibility.

Once developers believe failures are random, they stop investigating them. Eventually, a genuinely broken application may receive the same treatment.

A flaky test produces inconsistent results under conditions that are intended to be equivalent. Several mechanisms commonly cause this.

## 7.1 Fixed delays

Consider:

```typescript
await page.getByRole("button", {
  name: "Search"
}).click();

await page.waitForTimeout(1000);

expect(
  await page.getByText("Hotel Alexander").isVisible()
).toBe(true);
```

The developer waits one second.

Why one second?

Because it worked on their laptop.

But perhaps CI is slower. Perhaps the response takes 1.2 seconds.

Perhaps it takes only 100 milliseconds, in which case the test wastes 900 milliseconds.

A better approach uses a condition:

```typescript
await page.getByRole("button", {
  name: "Search"
}).click();

await expect(
  page.getByText("Hotel Alexander")
).toBeVisible();
```

Playwright's web-first assertions can retry until the expected condition becomes true or the configured timeout expires. This is much more robust than choosing arbitrary sleep durations.

The difference is philosophical. The fixed delay asks:

"Has enough time probably passed?"

The condition-based assertion asks:

"Has the required behavior actually occurred?"

## 7.2 Fragile selectors

Consider:

```typescript
await page.locator(
  "div:nth-child(4) > div > button.primary"
).click();
```

This selector depends on implementation structure. A designer adds another wrapper element, and the test breaks, even though the application's user-visible behavior may be completely unchanged.

A more resilient test uses meaningful interface semantics:

```typescript
await page.getByRole("button", {
  name: "Reserve room"
}).click();
```

This locates the control according to its accessible role and name. It's closer to how a user understands the interface. Explicit test identifiers are also appropriate when no reliable user-facing locator is available.

The principle is to prefer stable contracts over incidental DOM structure.

## 7.3 Shared test state

Suppose Test A creates a reservation.

Test B assumes no reservations exist.

Test C changes the authenticated user's account settings. Now the result depends on execution order. Run individually, every test passes.

Run in parallel, failures appear.

This is test contamination.

Tests should be isolated as much as practical. For browser testing, that commonly means separate browser contexts or sessions. For integration testing, it may mean dedicated test data, transactional cleanup, unique identifiers, or isolated databases.

The correct isolation strategy depends on cost and infrastructure. But tests should not secretly depend on one another's leftovers.

## 7.4 Real race conditions

Not every intermittent test failure is a broken test. Sometimes the application itself contains an asynchronous race. For example, a stale API response occasionally overwrites newer state. The test fails inconsistently because it has discovered a real timing-dependent bug.

Adding a longer sleep might make the failure disappear.

It doesn't make the application correct.

A useful debugging rule:

**Before calling a test flaky, determine whether the nondeterminism belongs to the test infrastructure or the product itself.**

Those require different solutions.

---

# 8. Accessibility: A Dimension Ordinary Tests Often Miss

Imagine our booking application works beautifully with a mouse.

Every button responds.

Every form submits.

Every end-to-end test passes.

Then someone tries using only a keyboard.

They cannot reach the date picker.

Or the reservation dialog opens, but keyboard focus remains behind it.

Or the booking button is represented by a clickable `<div>` that has no appropriate keyboard behavior.

The interface works under the assumptions the team tested.

It fails for other legitimate users.

Accessibility isn't simply a matter of adding alternative text to images. It concerns whether people using different input methods, assistive technologies, and sensory capabilities can understand and operate the interface.

## 8.1 Semantic HTML does useful work for you

Consider:

```html
<div onclick="reserve()">
  Reserve Room
</div>
```

This looks like a button if CSS makes it look like one. But it doesn't automatically acquire all the behavior of a native button.

Compare:

```html
<button type="button">
  Reserve Room
</button>
```

A native button provides browser-supported semantics and keyboard behavior.

It participates in the accessibility tree appropriately, and it has conventional focus and activation behavior.

This is one reason semantic HTML is valuable even in sophisticated component frameworks.

Using native elements correctly can eliminate entire categories of interaction bugs.

## 8.2 Test with roles and accessible names

Playwright supports queries such as:

```typescript
page.getByRole("button", {
  name: "Reserve Room"
});
```

This is useful for test stability. But it also encourages an interface whose controls have meaningful accessible semantics. If your important button is impossible to locate by an appropriate role and name, that may reveal an accessibility issue worth investigating.

However, role-based locators alone do not establish full accessibility.

A button can have a correct role and still be unusable in a particular interaction sequence.

## 8.3 Automated accessibility checks have limits

Tools such as axe-core can detect many common accessibility violations. These include certain problems involving labels, roles, contrast, and document structure. But automated tools cannot fully determine whether an interface is understandable or usable.

For example, they may not establish that:

- The keyboard navigation sequence is sensible.
- A custom date picker is comfortable to operate.
- A modal restores focus appropriately.
- Error messages provide sufficient guidance.
- Screen-reader announcements make sense throughout a workflow.

These require additional testing. A practical accessibility strategy combines automated checks with keyboard interaction testing and targeted manual evaluation, potentially including screen-reader testing.

The broader lesson:

**Testing must include the ways real people interact with the application, not merely the ways developers happen to interact with it.**

---

# 9. Browser Compatibility: There Is No Single Browser

Your Vue application works in Chrome.

Excellent.

Does it work in Firefox?

What about Safari?

What about a phone with a different viewport, touch interactions, and mobile browser behavior?

Modern browsers implement largely shared web standards, but differences still exist.

Potential issues include:

- CSS layout and rendering behavior.
- Browser API support.
- Focus management.
- Input controls.
- Touch interactions.
- File uploads.
- Storage and privacy policies.
- Browser-specific security behavior.

Playwright can run tests against Chromium, Firefox, and WebKit browser engines.

That's useful for identifying cross-engine differences.

But testing Playwright's WebKit isn't identical to testing every actual version of Safari on every Apple device. Likewise, emulating a mobile viewport doesn't perfectly reproduce physical-device performance, touch behavior, and operating-system integration.

## 9.1 Don't test every combination equally

Imagine supporting:

```text
3 browser engines
× 5 viewport sizes
× 4 operating systems
× 20 major workflows
```

That's already 1,200 combinations. And we haven't introduced languages, authentication states, feature flags, or network conditions. Exhaustively testing every combination becomes expensive.

A practical strategy selects combinations based on user distribution, risk, and known compatibility differences.

For example:

- Run fast core tests on every pull request.
- Test important browser engines on critical workflows.
- Run broader compatibility checks periodically.
- Investigate specific regressions on the platforms affected.
- Use real devices for behavior that emulation doesn't reproduce well.

The objective is meaningful coverage of supported environments, not combinatorial perfection.

---

# 10. Test Architecture: What Should Run in CI?

We've now collected several testing approaches. How should they fit together? Consider a conventional Vue/Node.js SaaS team.

A practical pipeline could look like this:

```text
Pull Request
     │
     ├── Type checking
     │
     ├── Linting
     │
     ├── Unit tests
     │
     ├── Component tests
     │
     ├── Focused integration tests
     │
     └── Critical browser smoke tests
                 │
                 ▼
          Merge / Deployment
                 │
                 ├── Post-deployment smoke checks
                 │
                 └── Broader scheduled test suites
```

The exact pipeline depends on product size and risk. For example, a large payment-oriented SaaS may justify more extensive pre-deployment verification than a small internal dashboard. But the underlying idea is to balance two competing needs.

**Fast feedback** lets developers discover failures quickly.

**Realistic verification** gives confidence that components and infrastructure work together.

An enormous browser suite that takes two hours and fails randomly may be less useful than a smaller suite that reliably detects consequential regressions.

## 10.1 Prioritize by risk

Not every behavior deserves equal testing effort. Consider these examples.

**Formatting the color of a minor decorative badge**

Low business consequence.

A component test may be enough.

**Calculating booking totals**

High consequence.

Unit tests should thoroughly cover relevant arithmetic and rounding rules. Integration tests should verify authoritative backend behavior.

**Preventing duplicate reservations**

High consequence.

Requires tests at the backend transaction or idempotency boundary, not merely disabling a Vue button.

**Completing checkout**

High consequence and crosses many systems.

A carefully designed end-to-end workflow is justified.

**Changing a dropdown's animation**

Mostly presentation behavior.

A focused component or browser test may be appropriate.

The testing strategy should follow the consequences of failure. That's a more useful organizing principle than insisting that every function must have its own test.

## 10.2 The best test is not necessarily the largest

A full browser test can be expensive. It requires application startup, a browser environment, network interactions, test data, and appropriate cleanup.

If a bug concerns a pure pricing function, a unit test may establish the behavior much more quickly and precisely. On the other hand, a test that checks only a mocked booking composable cannot prove that the deployed checkout flow actually works.

The goal is to use the **smallest test scope that provides convincing evidence for the behavior being examined**. And then complement it with a limited number of larger tests that verify important boundaries.

---

# 11. Production Reliability Extends Beyond the Test Suite

Here's one final uncomfortable truth.

Even a well-tested application can fail in production.

Perhaps a CDN serves stale HTML. Perhaps a third-party payment provider changes behavior. Perhaps a browser update introduces a compatibility issue. Perhaps a particular mobile device struggles with JavaScript execution. Or perhaps customers discover an interaction sequence no test author anticipated.

Testing reduces the probability of failures.

It doesn't eliminate the need to detect and recover from them. That's why mature frontend reliability includes production observation.

Useful signals include:

**JavaScript errors**

Which exceptions occur, on which routes, and in which release versions?

**Failed network requests**

Which endpoints fail? Are failures concentrated in certain regions or browsers?

**Performance telemetry**

Are LCP, INP, and CLS deteriorating for particular user groups?

**Business workflow metrics**

Are reservations actually completing?

Are customers abandoning checkout?

Are error rates increasing after deployment?

A release can have zero JavaScript exceptions and still be broken if the Reserve button no longer initiates the correct business operation.

## 11.1 Release monitoring and rollback

Imagine deploying version B.

The browser error rate increases sharply, and booking completion drops. A release-aware observability system helps identify that the regression began with version B.

The team rolls back to version A.

But remember SE240-L04. Frontend rollback isn't necessarily instantaneous. Some customers may still be running version B, and CDN and browser caches may retain assets. The backend must remain compatible with client versions still active.

Operational reliability therefore connects directly to deployment architecture. A frontend isn't reliable merely because its test suite passes before deployment. It must remain observable and recoverable afterward.

---

# 12. Practical Lab — Break Your Tests on Purpose

Let's perform two small investigations.

## Experiment A — A test that passes for the wrong reason

Consider:

```typescript
function applyDiscount(
  price: number,
  discountPercent: number
) {
  return price - discountPercent;
}
```

This implementation is wrong if the business requirement says `discountPercent` represents a percentage.

Now imagine testing:

```typescript
expect(applyDiscount(100, 10)).toBe(90);
```

The test passes! Why?

Because the selected input disguises the mistake. Subtracting €10 and applying a 10% discount to €100 happen to produce the same result.

Now test:

```typescript
expect(applyDiscount(200, 10)).toBe(180);
```

The implementation returns 190.

The bug becomes visible.

This simple example illustrates a crucial testing principle.

**The quality of test cases matters more than the number of times the test runner executes the function.**

Choose examples that distinguish correct behavior from plausible incorrect implementations.

## Experiment B — Reproduce the stale-response bug

Create a simple asynchronous search function.

```typescript
function fakeSearch(
  city: string,
  delay: number
): Promise<string> {
  return new Promise(resolve => {
    setTimeout(() => resolve(city), delay);
  });
}
```

Now execute:

```typescript
async function search(city: string, delay: number) {
  const result = await fakeSearch(city, delay);

  console.log("Displaying:", result);
}

search("Berlin", 500);
search("Hamburg", 100);
```

Hamburg appears first.

Berlin appears afterward.

That's the same class of failure that broke our booking workflow.

Now introduce request identity:

```typescript
let latestRequest = 0;

async function safeSearch(
  city: string,
  delay: number
) {
  const requestId = ++latestRequest;
  const result = await fakeSearch(city, delay);

  if (requestId !== latestRequest) {
    return;
  }

  console.log("Displaying:", result);
}
```

Repeat the experiment.

Only the latest requested result should be accepted.

The next challenge is more interesting.

Write a Vitest test that controls two unresolved promises explicitly and settles them in reverse order. Assert that an obsolete response cannot overwrite current state.

Such a test should not depend on sleeping for an arbitrary number of milliseconds. It should control the sequence deliberately. That's how you turn a timing-sensitive production bug into a deterministic regression test.

---

# 13. Engineering and Interview Challenges

### Challenge 1 — The 98% Coverage Trap

Your frontend has 98% statement coverage. Customers frequently encounter incorrect reservation totals.

What does this tell you about the limitations of coverage? What tests would you add?

### Challenge 2 — The Mocked Checkout

A Playwright test mocks every API request and successfully completes checkout. The production checkout fails because the backend rejects the request payload.

Which boundary wasn't actually tested? How would you improve the testing strategy?

### Challenge 3 — The Flaky Test

A browser test fails in CI approximately once every twenty runs.

It uses:

```typescript
await page.waitForTimeout(500);
```

A developer proposes increasing the delay to 2,000 milliseconds.

Is that a good solution? What should be investigated first?

### Challenge 4 — The Accessible Button

A Vue component renders a clickable `<div>` styled as a button. Mouse-based E2E tests pass.

What problems might remain? How would you test them?

### Challenge 5 — The Testing Budget

Your team has limited CI resources.

Would you prioritize 500 additional trivial unit tests or ten carefully chosen integration and browser tests covering critical booking workflows?

What determines the correct choice?

---

# 14. Solutions and Discussion

**Challenge 1**

Coverage tells us which code was executed during testing, not whether the tests used meaningful expected results or covered important failure scenarios.

I would investigate the pricing contract, rounding rules, currency handling, taxes, discounts, and frontend/backend agreement. Tests should include independently determined examples and boundary conditions. Integration tests should also verify that the value shown to the customer matches the authoritative booking quote.

**Challenge 2**

The actual frontend–backend contract wasn't verified. Mocked responses demonstrated that the frontend could process expected behavior, but not that the real backend accepted the request.

A useful improvement would be integration or contract tests against the real API implementation, complemented by a limited number of browser workflows using a real test backend.

**Challenge 3**

Increasing the delay may conceal the problem while slowing down the suite. The test should wait for a meaningful condition rather than an arbitrary duration.

Investigate whether the failure comes from network timing, missing awaits, shared state, unstable selectors, or an actual application race. If the application is buggy, the fix belongs in the application—not merely the test.

**Challenge 4**

The element may lack appropriate keyboard interaction, focus behavior, and accessible semantics. A native `<button>` would often solve several of these issues directly.

Tests should include keyboard navigation, focus behavior, accessible roles and names, and relevant automated accessibility checks. Passing mouse-based tests isn't sufficient.

**Challenge 5**

Assuming the critical workflows are insufficiently tested, the ten carefully chosen integration and browser tests would likely provide more useful risk reduction. But the decision depends on the existing suite and the actual business risks.

Trivial unit tests are rarely worth prioritizing merely to increase test counts. The correct testing investment targets consequential failures and poorly verified boundaries.

---

# 15. The Mental Model Worth Keeping

Testing isn't about demonstrating that your code works when everything behaves exactly as expected. It's about discovering where your understanding of the system is incomplete.

**Unit tests** examine focused logic.

**Component tests** verify isolated UI behavior.

**Integration tests** examine collaboration between modules and services.

**End-to-end tests** exercise larger user journeys—but their realism depends on which dependencies are genuine.

**Mocks** provide control and repeatability, but may conceal important system behavior.

**Coverage** reveals executed code, not guaranteed correctness.

**Flaky tests** undermine confidence and may expose either test defects or real application races.

**Accessibility testing** investigates interaction paths ordinary mouse-based tests can miss.

**Cross-browser testing** checks assumptions about the execution environment.

**Production monitoring** detects failures that escaped the testing process.

And here's the most important principle:

**A test suite is valuable when it makes important bugs difficult to introduce—not when it makes the engineering dashboard look impressive.**

A thousand tests of isolated implementation details may be less valuable than a dozen that protect critical business workflows.

---

# 16. Next Session — Architecture Workshop: Design a Modern Web Product

We've studied the major pieces of modern web engineering in isolation. The real challenge is making them work together under real constraints—limited time, limited money, and a product that must stay correct as it grows.

In **SE490-L02 — Architecture Workshop: Design a Modern Web Product**, we'll design a realistic hotel-booking SaaS and defend its architecture as though we were in a senior engineering interview. The objective won't be the most sophisticated diagram possible—it will be the simplest architecture that convincingly meets the product's actual requirements.

---


---

## End of SE240

**SE240 — Browser and Frontend Engineering** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading — Optional References

1. [Vue — Testing Guide](https://vuejs.org/guide/scaling-up/testing.html) — Unit, component, and end-to-end testing recommendations.
2. [Vue Test Utils — Asynchronous Behavior](https://test-utils.vuejs.org/guide/advanced/async-suspense) — Vue updates, promises, and testing asynchronous components.
3. [Vitest — Coverage](https://vitest.dev/guide/coverage.html) — Coverage providers, reports, and configuration.
4. [Playwright — Best Practices](https://playwright.dev/docs/best-practices) — User-visible assertions, stable locators, and isolation.
5. [Playwright — Auto-waiting](https://playwright.dev/docs/actionability) — Actionability checks and timing behavior.
6. [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/) — Accessibility requirements and evaluation criteria.

---


---

