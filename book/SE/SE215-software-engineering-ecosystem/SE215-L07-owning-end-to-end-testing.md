---
id: SE215-L07
course: SE215
title: "Owning End-to-End Testing"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L06
next: SE215-L08
---

# SE215 — The Software Engineering Ecosystem

## Lecture 07: Owning End-to-End Testing

*Your application has 1,200 passing tests. Code coverage is 98 percent. CI is green, the deployment succeeded, and the monitoring dashboard looks healthy. Then a customer opens the booking page, selects a hotel, enters their dates, and clicks Reserve. Nothing happens. How did an entire engineering team fail to test the one thing the customer was trying to do?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a car factory.

The engine has been tested.

The transmission has been tested.

The brakes have been tested.

The dashboard electronics have been tested.

Each component meets its specification.

The completed vehicle leaves the assembly line.

A customer gets inside, presses the start button, shifts into drive, and discovers that the car won't move.

The engine works.

The transmission works.

But the components don't cooperate correctly.

This is the intuition behind end-to-end testing.

**A system consists not only of individual components, but also of the interactions between them.**

Let's return to Mercury, our hotel-booking platform.

The frontend has a reservation form.

The backend has an endpoint for creating reservations.

PostgreSQL stores bookings.

The authentication system identifies customers.

A payment integration handles charges.

Every component has tests.

Yet when a customer clicks Confirm Reservation, the frontend sends a request containing a field named `checkInDate`.

The backend now expects `arrivalDate`.

Each component was tested against its own assumptions.

Neither test established that the deployed frontend and backend agreed.

The browser request fails.

The customer cannot complete the booking.

An end-to-end test can expose this disagreement by exercising a meaningful journey across the relevant boundaries.

## 1. Test the behavior the customer actually experiences

Consider a test that calls a function named `calculatePrice`.

It passes.

That's useful evidence that a particular function behaves as expected.

Now consider a test that renders a reservation component with mocked data and clicks its Confirm button.

It passes.

That's useful evidence about frontend behavior.

But what if the real backend rejects the request?

What if the session cookie is missing?

What if the reverse proxy routes the request incorrectly?

What if the database schema is incompatible with the running API?

Those tests may not detect the problem.

An E2E test approaches the application from the outside.

It opens a real browser, interacts with visible controls, and checks whether a user can accomplish the intended task.

The browser executes the real JavaScript.

The application performs its normal navigation.

Requests travel through whichever backend and infrastructure components the test environment includes.

And the test observes the result.

But there's a qualification.

A browser test using a mocked API isn't automatically a full-system E2E test.

Its scope depends on which parts of the system are actually participating.

We'll return to that distinction.

## 2. Why Playwright is useful

Playwright provides browser automation and a test runner.

Instead of manually opening Chrome, clicking a button, selecting dates, and checking the result, we can describe those actions programmatically.

A test might say:

Open the reservation page.

Select new dates.

Click Confirm.

Verify that the application shows a successful confirmation.

Playwright can perform these actions in actual browser engines and inspect the resulting behavior.

It also provides facilities for isolating browser state, running tests in parallel, intercepting network requests, and recording traces.

These capabilities matter because browser testing is otherwise difficult to make reliable.

A test that works once on one developer's laptop is not yet a trustworthy automated test.

We want a test that can run repeatedly, in different environments, without accidentally depending on yesterday's cookies or another test's database records.

## 3. The hidden problem: every test needs a world to operate in

Imagine writing a test for canceling a reservation.

The test needs a customer account.

It needs an authenticated browser session.

It needs a reservation belonging to that customer.

The reservation must be eligible for cancellation.

The database must contain consistent inventory and payment information.

And afterward, the test should not leave unwanted state that breaks another test.

Where does all of that come from?

This is one of the least glamorous but most important parts of E2E engineering.

**A browser test is only as deterministic as the environment and data beneath it.**

If the test depends on a shared reservation created last week, it may stop working when somebody cancels that reservation.

If two tests use the same customer account and modify the same booking simultaneously, they may interfere.

If a test depends on the current date or an expiring promotion, it may fail tomorrow without a code change.

A reliable suite must control its starting conditions.

## 4. The three different meanings of an E2E test

Consider three tests that all use Playwright to complete a reservation.

In the first, the browser interacts with the real frontend, but the reservation API response is mocked.

This tests the frontend's behavior against a controlled response.

In the second, the browser talks to a real test backend and a test database.

This can verify that the application components actually agree.

In the third, the browser interacts with an application deployed through production-like infrastructure.

That can verify additional boundaries such as routing, deployment configuration, TLS, and runtime dependencies.

These tests have different costs and different evidential value.

The first is fast and controllable.

The second crosses more genuine application boundaries.

The third includes more deployment behavior but may be slower, more expensive, and more sensitive to environmental conditions.

None is universally best.

The important thing is to know exactly **what each test proves and what it leaves untested**.

## 5. The sensible testing strategy

Mercury has hundreds of business rules.

Should every rule be tested by opening a browser and completing an entire reservation?

Probably not.

Suppose the cancellation policy has thirty combinations of date, customer status, payment state, and booking type.

Those business rules can often be tested more efficiently at the domain or service layer.

Then a smaller number of browser tests can verify that the customer-facing workflow correctly integrates the relevant components.

That gives us two complementary forms of confidence.

Detailed tests verify many important rules quickly.

End-to-end tests verify that real user journeys cross application boundaries correctly.

The objective isn't to maximize the number of browser tests.

It's to cover important risks at the most useful testing level.

### Three questions before the Deep Dive

1. Why might a Playwright test pass while the real booking API remains broken?
2. Why is a test database shared by twenty parallel tests potentially dangerous even when every browser receives a fresh session?
3. Why might five carefully selected E2E scenarios provide more value than a hundred nearly identical ones?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The checkout that passed every test

Mercury's team has a frontend developed in Vue and a backend written in Node.js.

The developers maintain unit tests for pricing, validation, and reservation eligibility.

They also have component tests covering the date picker and confirmation dialog.

Finally, they use Playwright to test checkout.

The test opens a page, selects dates, clicks Reserve, and checks for a success message.

Everything passes.

Then production breaks.

Why?

The Playwright test intercepts the reservation endpoint and always returns a successful response.

That mock was originally introduced because the shared testing environment was unreliable.

Over time, the team forgot what the test actually verified.

It verified that the frontend could display success after receiving a particular successful response.

It didn't verify that the backend could create a reservation.

It didn't verify authentication, inventory allocation, database persistence, or the real API contract.

The test wasn't necessarily useless.

It was simply being asked to support a claim it couldn't establish.

This is our first operational rule:

**Name tests according to the boundaries they genuinely exercise.**

A browser test with a mocked backend is useful.

It just shouldn't be confused with a full-stack booking test.

## 2. Start with the customer journey, not a list of components

Suppose we're designing a testing strategy for Mercury.

We could begin by listing every screen and component.

There is a search page, hotel detail page, date picker, login dialog, checkout form, and confirmation page.

Then we could write a test for every component combination.

That approach can produce an enormous suite without identifying the most consequential risks.

A better starting point is the user journey.

What does the customer need to accomplish?

For Mercury, several important journeys emerge.

A customer searches for a hotel and receives results.

A customer signs in and views their reservations.

A customer completes a new reservation.

A customer changes reservation dates.

A customer cancels an eligible reservation.

A customer encounters a failed payment or uncertain network result.

These are business capabilities.

Now ask which journeys deserve browser-level verification.

The booking confirmation path is especially important because failure can affect money, inventory, and customer trust.

A decorative preference panel may not deserve the same investment.

### Risk determines coverage

A useful test portfolio balances business impact, change frequency, technical complexity, and likelihood of failure.

The more consequential the workflow, the stronger the case for testing the complete interaction.

But the most expensive workflow doesn't automatically need the most browser tests.

The goal is to choose a few meaningful scenarios and verify the detailed business rules at more focused layers.

## 3. Locators: interact with the interface, not its implementation

Now we write a browser test.

The customer sees a button labeled Confirm Reservation.

How should the test find it?

One option is a CSS selector referring to the button's position inside several nested containers.

That might work today.

Then a designer adds another wrapper element.

The selector breaks.

The user-visible behavior hasn't changed.

Our test depended on irrelevant implementation structure.

Playwright encourages locators based on user-facing attributes.

For example, selecting a button by its role and accessible name.

This is more closely aligned with how users and assistive technologies identify interface controls.

### Accessible names are useful contracts

Suppose a button has the accessible name Confirm Reservation.

A test can locate it through that name.

If the implementation changes from one CSS framework to another, the locator can remain valid.

This encourages semantic markup and accessible controls.

It's a useful connection between testability and accessibility.

However, role-based locators aren't magic.

If a screen contains five buttons all named Edit, a locator may be ambiguous.

We may need to identify the relevant reservation card first, then locate its Edit button.

For elements without suitable user-facing semantics, a deliberate test identifier can be appropriate.

The principle is to use a stable contract, not to avoid CSS selectors as a religious rule.

## 4. Waiting: the source of countless flaky tests

Imagine our booking page loads asynchronously.

The browser opens the route.

The frontend requests reservation data.

The response arrives.

The UI renders.

The test clicks the Confirm button.

Sometimes it works.

Sometimes the request takes longer.

The developer adds a two-second sleep.

The test becomes more reliable.

Then CI runs on a slower machine.

The test fails again.

The developer increases the sleep to five seconds.

Now the test suite is slower and still unreliable.

What's wrong?

The test is waiting for time to pass rather than for the required condition to become true.

### Condition-based synchronization

Playwright locators and assertions provide automatic waiting and retry behavior for many ordinary UI operations.

Instead of sleeping for an arbitrary duration, we can wait until the expected button is visible and enabled, then interact with it.

After submitting the form, we can wait until the appropriate confirmation appears.

This makes the test responsive to actual application behavior.

If the operation completes quickly, the test doesn't waste five seconds.

If it takes longer within the configured timeout, the test can still succeed.

### Don't wait for everything to become idle

Some applications maintain long-running connections, polling, analytics requests, or other background activity.

Waiting for the entire network to become idle can be an unreliable signal of whether the user-facing operation is complete.

A better test usually waits for the specific state that matters.

For example:

"Reservation confirmed" appears.

Or the application shows a known validation error.

Or a particular API response has completed and the relevant UI state has updated.

The test should synchronize with the behavior it's verifying.

**Waiting is part of the test's correctness model, not an arbitrary delay between actions.**

## 5. Browser isolation isn't enough when the backend is shared

Playwright creates isolated browser contexts for ordinary tests.

Each context has its own browser state, including cookies and local storage.

This helps prevent one test's browser session from contaminating another.

But consider two tests using different browser contexts while both access the same database.

Test A changes a customer's reservation.

Test B expects that reservation to remain unchanged.

The browsers are isolated.

The backend state isn't.

The tests may still interfere.

### Test-data isolation

A reliable suite needs a deliberate strategy for test data.

One approach gives each test its own customer and reservation.

Another gives each parallel worker an isolated account or tenant.

Some systems can provision a database per test worker.

Others use dedicated schemas, namespaces, or deterministic cleanup.

Each option has costs.

Creating an entire database for every browser test may be excessive.

But sharing mutable business records across dozens of tests is often a source of nondeterminism.

The correct choice depends on the application's architecture and the parallelism of the suite.

### Cleanup isn't always enough

Imagine a test creates a reservation and promises to delete it afterward.

The test process crashes.

Cleanup never runs.

The record remains.

If future tests assume the database is empty, they may fail.

Therefore, test isolation shouldn't depend entirely on successful teardown.

Unique identifiers, bounded test namespaces, and periodic cleanup can provide additional protection.

This is the same kind of defensive reasoning we use for production background jobs.

## 6. Authentication without repeating login everywhere

Mercury's tests require authenticated customers.

Should every test open the login page, type a username and password, complete authentication, and then navigate to its actual task?

That would waste time and make unrelated tests depend on the login workflow.

Playwright supports saving authenticated browser state and reusing it in subsequent tests.

A setup step can authenticate a suitable test account, save its state, and allow test contexts to begin already signed in.

This is useful for tests whose objective isn't authentication itself.

Authentication should still have dedicated tests.

### The parallel-account trap

Suppose every test reuses the same authenticated account.

If the tests only read data, that may be perfectly acceptable.

But if multiple tests edit the account's settings or reservations, they can conflict.

A better strategy may use separate accounts for different workers or tests.

The state-reuse mechanism isn't the problem.

The shared mutable server state is.

### Security matters even in test infrastructure

Saved authentication state may contain session cookies or other sensitive information.

It should be treated as credentials.

Don't commit it into the repository.

Don't casually upload it into public build artifacts.

Don't use production customer accounts for destructive E2E testing.

Testing infrastructure has access to powerful systems and therefore deserves proper security boundaries.

## 7. Fixtures: make the test environment explicit

Let's introduce another Playwright concept.

A **fixture** prepares a resource required by a test and can clean it up afterward.

Playwright provides built-in fixtures for the page, browser context, and API request capabilities.

Teams can create additional fixtures for their own application.

For example, Mercury might have a fixture that creates a valid reservation.

A test declares that it needs a reservation.

The fixture creates one before the test proceeds.

Afterward, it attempts cleanup.

This separates test setup from the behavior under examination.

The test can focus on what matters:

Given a valid reservation, when the customer changes dates, the system confirms the new booking state.

### Fixtures shouldn't become an invisible universe

There's a danger in excessive abstraction.

Suppose a test imports a fixture called `fullyPreparedBookingScenario`.

Nobody knows which account it uses, which API requests it makes, or which database state it establishes.

When the test fails, the setup machinery is harder to understand than the feature.

Use fixtures for meaningful, reusable resources.

Keep their contracts explicit.

Avoid building an elaborate test framework before the application actually needs one.

## 8. Mocking: useful control, limited evidence

Let's return to network interception.

Playwright can intercept a request and supply a controlled response.

For example, we can make the reservation API return an HTTP error.

That allows us to test whether the frontend displays the correct failure state.

We can also simulate slow responses and out-of-order completion.

These are valuable tests.

But they prove frontend behavior against the simulated responses.

They don't prove the real backend produces those responses correctly.

### A balanced strategy

For our booking application, I would maintain both kinds of browser tests.

A small full-stack smoke suite uses the real test backend and verifies crucial business journeys.

Focused browser tests use controlled network responses to exercise unusual UI states.

The full-stack tests verify integration.

The mocked tests make difficult failure scenarios reproducible.

Neither replaces the other.

### The uncertain-payment example

Suppose the browser sends a booking request and the connection fails.

The user doesn't know whether the server committed the reservation.

A frontend test can simulate a network failure and verify that the interface doesn't display an unjustified success message.

But merely aborting the browser request does not prove that a booking was committed before the response disappeared.

To test that ambiguity properly, we need a controlled backend or integration fixture that performs the business operation while withholding or losing the response.

The test must model the actual failure being claimed.

That's an important senior-level distinction.

## 9. Parallel execution: speed with hidden costs

Playwright can execute tests using multiple workers.

This can substantially reduce total execution time.

But parallelism exposes shared-state problems.

Two tests might use the same customer.

One test might delete records required by another.

Several browser instances might overwhelm a small test database.

A shared external provider sandbox might enforce rate limits.

A fixed port might already be occupied.

A test may pass with one worker and fail with eight.

### Parallelism is a design constraint

A well-designed test should not depend on the execution order of unrelated tests.

It should not assume another test has already created the required data.

It should not rely on a globally shared mutable account unless that access is intentionally coordinated.

If adding more workers causes failures, investigate the isolation problem before simply reducing parallelism.

Sometimes lower concurrency is still appropriate because the test environment has genuine capacity limits.

But the team should understand the trade-off.

The objective is reliable, reasonably fast feedback.

Not the maximum possible number of concurrent browsers.

## 10. Debugging a flaky test like a production incident

Imagine one of Mercury's checkout tests fails every tenth CI run.

A developer reruns it.

It passes.

The team declares it flaky and moves on.

This is dangerous.

Eventually, developers stop trusting test failures.

A genuinely broken release may receive the same treatment.

### What could cause intermittent failure?

The test might rely on a fixed timeout.

Another test might modify shared data.

An element might be temporarily covered by an animation.

An asynchronous request might complete in an unexpected order.

The test environment might be overloaded.

The application itself might contain a real race condition.

These are different root causes.

Increasing timeouts doesn't resolve most of them.

### Traces and artifacts

Playwright can record traces containing actions, snapshots, and relevant debugging information.

A trace can help show what the browser saw, which action failed, and what happened around the failure.

Screenshots and videos can also provide evidence.

But these artifacts aren't free.

Recording everything can slow the suite and generate large storage volumes.

Teams often retain traces for failed executions or particular retries.

They should also consider whether artifacts contain sensitive test data.

### Retries are diagnostic, not a cure

A retry can distinguish an intermittent failure from a consistently reproducible one.

But a test passing on retry doesn't mean the underlying problem has disappeared.

A useful investigation asks why the first attempt failed.

Was the fixture wrong?

Was the environment overloaded?

Was there an actual application race?

If a test has become unreliable, fix its assumptions or the relevant application behavior.

Don't simply allow unlimited retries until it turns green.

## 11. Deciding what belongs in CI

Mercury has hundreds of automated tests.

Running the entire browser suite on every small commit takes forty minutes.

Developers begin ignoring the results because feedback arrives too late.

We need a sensible portfolio.

### Pull-request checks

For ordinary pull requests, run fast checks such as type checking, linting, unit tests, and relevant integration tests.

Include a small number of critical browser smoke tests when they provide worthwhile confidence within the feedback budget.

A public booking flow may deserve such coverage.

A rarely used administrative report may not need a complete browser journey on every pull request.

### Deployment verification

After deployment to a suitable environment, execute checks that verify the deployed application can perform its critical operations.

A backend may be healthy while the public routes, credentials, or application configuration are wrong.

The deployment process should verify something meaningful beyond process readiness.

### Broader regression testing

More comprehensive E2E suites may run before major releases, on a schedule, or when relevant areas change.

These can include additional browsers, user roles, and less common business scenarios.

The precise distribution depends on the company's risk and delivery process.

The key is to make the suites purposeful.

**A test suite that provides fast, trustworthy evidence is more useful than a giant suite that developers no longer believe.**

## 12. Who should own E2E testing?

Now we arrive at the organizational question.

Should developers write and maintain these tests?

Or should a dedicated QA automation team handle everything?

There isn't one universally correct organization chart.

But application developers benefit from owning much of the automated verification associated with their features.

They understand the implementation.

They can create appropriate test data.

They can investigate failures across frontend and backend boundaries.

They can update tests alongside behavior changes.

And they can prevent defects earlier rather than treating QA as a final handoff.

### What specialists contribute

Dedicated QA and test engineers can provide substantial expertise in risk analysis, exploratory testing, accessibility, test strategy, infrastructure, and hard-to-reproduce scenarios.

Their role need not be reduced to manually checking work developers consider finished.

A strong team treats quality as shared responsibility while making ownership of particular test suites and infrastructure explicit.

### The senior engineer's perspective

Suppose an interviewer asks:

"How would you introduce E2E testing to a full-stack application?"

A useful answer isn't merely:

"I'd install Playwright and write some tests."

You should discuss what workflows carry the most risk.

Which components must be real.

How test data will be created.

How authentication will work.

How tests will remain isolated.

What runs in CI.

How failures will be investigated.

And who maintains the suite after the original author leaves.

That's the difference between knowing a browser-automation library and designing a testing capability.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — The mocked checkout

A Playwright test intercepts every booking API request and returns a successful reservation. It passes. What has the test established, and what has it not established?

### Question 2 — Test isolation

Each Playwright test receives a fresh browser context. Why can two parallel tests still interfere?

### Question 3 — Synchronization

Why is waiting five seconds before clicking a button generally worse than waiting for the button to become visible and enabled?

### Question 4 — Authentication

When is reusing authenticated browser state appropriate? When might separate accounts be required?

### Question 5 — Uncertain outcomes

You abort a booking request from the browser and verify that the UI displays a network error. Have you tested the case where the backend committed the reservation but the response was lost?

### Question 6 — Flaky tests

A test fails occasionally but succeeds when retried. What evidence should you collect before deciding whether the problem is in the test or the application?

### Question 7 — Testing strategy

A payment-oriented SaaS has thirty cancellation-policy combinations. Should all thirty be tested through the browser?

### Question 8 — Team ownership

Why might developer-owned E2E tests improve product quality even when a company employs experienced QA automation engineers?

---

# Solutions and Discussion

## Solution 1 — Frontend behavior against a controlled response

The test establishes that the frontend can complete its UI interaction when given that mocked response.

It doesn't prove the real API accepts the request, authenticates correctly, commits the booking, or integrates with persistence.

Those boundaries require separate verification.

## Solution 2 — Browser isolation doesn't isolate backend state

The tests may use different browser sessions while sharing customers, reservations, databases, queues, or external sandbox resources.

Isolation must account for those shared dependencies.

## Solution 3 — Conditions describe the required behavior

A fixed delay waits even when the application is ready and may still be too short when execution is slow.

A condition-based wait synchronizes with the meaningful state and is generally more reliable.

## Solution 4 — Reuse safe, nonconflicting state

Stored authentication state is useful when tests can reuse the session without corrupting shared server-side data.

Tests that mutate account-level state may require separate accounts or other isolation.

Stored authentication state must be treated as sensitive.

## Solution 5 — Not necessarily

Aborting a browser request doesn't automatically simulate a server commit followed by response loss.

That scenario needs a test setup capable of producing the actual ambiguous outcome.

The test must establish which business operation happened and which response the client observed.

## Solution 6 — Investigate the execution

Collect traces, relevant logs, screenshots, request timing, environment status, and test-data evidence.

Look for races, unstable locators, shared state, arbitrary waits, resource limits, and genuine application failures.

A passing retry doesn't prove the test is harmless.

## Solution 7 — Use the right testing layers

The thirty business-rule combinations can often be tested more efficiently through unit or integration tests.

Use a smaller collection of browser tests to verify the critical journeys and relevant cross-component integration.

## Solution 8 — Quality becomes part of implementation

Developers can create and maintain tests alongside feature changes and investigate failures across the stack.

QA specialists still contribute valuable expertise in testing strategy and difficult scenarios.

The objective is shared quality ownership rather than transferring all verification to one department.

---

# The Mental Model Worth Keeping

A trustworthy E2E suite is not simply a collection of browser scripts.

It is a controlled environment for verifying important user journeys across selected system boundaries.

Ask five questions:

**Behavior:** Which customer outcome are we verifying?

**Boundaries:** Which components are real, and which are simulated?

**State:** Can the test establish its starting conditions independently?

**Synchronization:** Does it wait for meaningful behavior rather than arbitrary time?

**Evidence:** When it fails, can we explain why?

A senior engineer should be able to defend the answers.

**The purpose of E2E testing is not to make the CI dashboard greener. It's to establish trustworthy evidence that the product can do what its users need it to do.**

# Next Lecture — SE215-L08: Technical SEO and Web Discoverability

We've learned how to verify that a customer can use a working website.

But what happens when the customer never discovers the website in the first place?

Imagine Mercury rebuilds its public hotel catalogue with a modern JavaScript application.

The pages look beautiful.

The API is fast.

The browser tests pass.

Yet organic search traffic begins falling.

Perhaps crawlers cannot discover important pages.

Perhaps canonical URLs are incorrect.

Perhaps the sitemap contains invalid destinations.

Perhaps the application depends too heavily on client-side rendering for its discoverability requirements.

Next we'll examine the engineering mechanisms behind crawling, indexing, structured data, canonicalization, and search visibility.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Build a Reliable Playwright Suite

The following examples assume a fictional local Mercury application.

They are **illustrative test contracts**, not claims about endpoints or UI elements that already exist in a repository. Adapt the routes, controls, and helper APIs to your actual application.

The lab uses TypeScript and Playwright Test.

## Lab 1 — Establish the environment

Create a dedicated testing environment containing:

- A running frontend application.
- A real test backend.
- An isolated or namespaced test database.
- A mechanism for creating and cleaning up test customers and reservations.
- A predictable authentication strategy.

Do not point destructive tests at production customer records.

Install Playwright in the application project and install the browser binaries using the official setup workflow.

```bash
npm install --save-dev @playwright/test
npx playwright install
```

A minimal project structure might look like this:

```text id="72wkea"
mercury/
├── apps/
│   ├── web/
│   └── api/
├── tests/
│   └── e2e/
│       ├── fixtures.ts
│       ├── booking.spec.ts
│       └── auth.setup.ts
├── playwright.config.ts
└── playwright/
    └── .auth/
```

The `.auth` directory should be ignored by Git if used to store authentication state.

## Lab 2 — Configure Playwright

A basic configuration defines the browser project, local application URL, retries, trace behavior, and test-server startup.

```typescript
// playwright.config.ts

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",

  retries: process.env.CI ? 1 : 0,

  workers: process.env.CI ? 2 : undefined,

  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],

  webServer: {
    command: "npm run start:test",
    url: "http://127.0.0.1:4173/",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
```

The fictional `start:test` script must actually start the application and backend dependencies required for these tests.

The web-server configuration checks whether the specified frontend endpoint is available; it does not automatically provision PostgreSQL or establish that the complete backend is ready.

In a real project, the team may use Docker Compose, Testcontainers, dedicated setup scripts, or CI-managed services.

## Lab 3 — Create isolated reservation data

We'll assume Mercury exposes an authenticated test-only API for creating fixtures.

For example, a protected endpoint in the isolated test environment can create a customer-owned reservation and return its identifier.

Such an endpoint must never become an unauthenticated production backdoor.

A reusable Playwright fixture could create one reservation for each test and attempt cleanup afterward:

```typescript
// tests/e2e/fixtures.ts

import {
  test as base,
  expect,
} from "@playwright/test";

type BookingFixtures = {
  reservationId: string;
};

export const test = base.extend<BookingFixtures>({
  reservationId: async ({ request }, use) => {
    const response = await request.post(
      "/__test__/reservations",
      {
        data: {
          customer: "e2e-customer",
          checkIn: "2027-02-10",
          checkOut: "2027-02-12",
          status: "confirmed",
        },
      }
    );

    expect(response.ok()).toBeTruthy();

    const { id } = await response.json();

    try {
      await use(id);
    } finally {
      await request.delete(
        `/__test__/reservations/${id}`
      );
    }
  },
});

export { expect };
```

This assumes test-only endpoints, suitable test credentials or permissions, and a server implementation that creates unique isolated records.

The fixture provides useful structure, but it doesn't guarantee perfect cleanup after a process crash.

For larger suites, add unique test namespaces or worker-specific accounts and periodic cleanup of abandoned records.

## Lab 4 — Test a successful reservation-date change

The first browser test should exercise a real application workflow.

In this example, the customer opens an existing reservation, selects new dates, confirms the change, and receives a successful result.

```typescript
// tests/e2e/booking.spec.ts

import { test, expect } from "./fixtures";

test("customer changes reservation dates", async ({
  page,
  reservationId,
}) => {
  await page.goto(
    `/reservations/${reservationId}/change`
  );

  await page.getByLabel("New check-in").fill(
    "2027-02-15"
  );

  await page.getByLabel("New check-out").fill(
    "2027-02-18"
  );

  await page.getByRole("button", {
    name: "Confirm change",
  }).click();

  await expect(
    page.getByRole("status")
  ).toContainText("Reservation updated");
});
```

This example assumes the browser is already authenticated for the fixture customer and that the application exposes those controls with accessible names.

For a stronger full-stack test, add an API or database assertion establishing that the reservation was actually updated, rather than relying entirely on the displayed success message.

The key point is that no booking API response is mocked.

The test must cross the real frontend/backend boundary in the designated testing environment.

## Lab 5 — Test validation failure

Now create a test where the selected checkout date precedes the check-in date.

```typescript
test("invalid date range cannot be confirmed", async ({
  page,
  reservationId,
}) => {
  await page.goto(
    `/reservations/${reservationId}/change`
  );

  await page.getByLabel("New check-in").fill(
    "2027-02-18"
  );

  await page.getByLabel("New check-out").fill(
    "2027-02-15"
  );

  await expect(
    page.getByText(
      "Check-out must be after check-in"
    )
  ).toBeVisible();

  await expect(
    page.getByRole("button", {
      name: "Confirm change",
    })
  ).toBeDisabled();
});
```

This checks the frontend's validation behavior.

You should still maintain backend tests verifying that invalid date ranges are rejected even when requests bypass the browser interface.

Browser validation is not an authorization or business-integrity boundary.

## Lab 6 — Test a network failure

Now use Playwright's request interception to deliberately prevent the reservation-change request from succeeding.

```typescript
test("network failure does not claim success", async ({
  page,
  reservationId,
}) => {
  await page.route(
    "**/api/reservations/*/change",
    async route => {
      await route.abort("failed");
    }
  );

  await page.goto(
    `/reservations/${reservationId}/change`
  );

  await page.getByLabel("New check-in").fill(
    "2027-02-15"
  );

  await page.getByLabel("New check-out").fill(
    "2027-02-18"
  );

  await page.getByRole("button", {
    name: "Confirm change",
  }).click();

  await expect(
    page.getByRole("alert")
  ).toContainText("Could not confirm");
});
```

This is a controlled frontend failure test. It assumes the application's URL patterns and error copy match the example.

It does **not** prove that the backend committed a change and lost the response.

That more difficult scenario requires an appropriate controlled backend fault, such as committing an operation and deliberately withholding a response.

For the network-failure test, the important requirement is that the UI doesn't confidently claim success when it lacks authoritative confirmation.

## Lab 7 — Make a flaky test reproducible

Deliberately create an asynchronous race in a small component.

The customer types one destination, then rapidly changes it.

The first request takes longer than the second.

If the frontend accepts responses without verifying that they correspond to the current search, stale results may overwrite newer ones.

Use controlled response delays to reproduce the race.

Then fix the application using a strategy such as request cancellation or generation identifiers.

Verify that the test passes consistently with the correction.

Avoid fixing it by simply waiting longer.

## Lab 8 — Run and investigate

Useful Playwright commands include:

```bash
# Run the test suite
npx playwright test

# Run one named test
npx playwright test -g "network failure"

# Open Playwright's interactive UI
npx playwright test --ui

# Show the latest HTML report
npx playwright show-report

# Record traces during a diagnostic run
npx playwright test --trace on
```

Now introduce a deliberate failure and inspect the trace.

Ask:

What action was the browser performing?

What element was actually present?

Which request failed?

Did the expected response arrive?

Did another test modify shared state?

Was the application wrong, or did the test make an invalid assumption?

The goal is to practice investigation, not merely learn Playwright commands.

## Lab 9 — Design the CI portfolio

Propose three levels of verification.

**Pull-request smoke:** A small, fast subset of critical user journeys, plus unit and integration tests.

**Deployment verification:** Real application checks against the deployed environment, including authentication and an appropriate non-destructive business journey.

**Broader regression:** Additional browsers, user roles, edge cases, and less common workflows, scheduled or executed according to release risk.

For each level, specify:

- Which components are real.
- Which external systems are mocked or sandboxed.
- Which test data is used.
- How authentication is established.
- Whether tests run in parallel.
- Which artifacts are retained after failures.
- Who investigates and owns failing tests.

A useful success condition is not merely that the tests pass once.

It's that the team trusts them enough to act when they fail.

---

# Further Reading

Official Playwright references:

- **Best Practices:** https://playwright.dev/docs/best-practices
- **Locators:** https://playwright.dev/docs/locators
- **Auto-Waiting:** https://playwright.dev/docs/actionability
- **Fixtures:** https://playwright.dev/docs/test-fixtures
- **Authentication:** https://playwright.dev/docs/auth
- **Network Interception and Mocking:** https://playwright.dev/docs/network
- **Parallelism:** https://playwright.dev/docs/test-parallel
- **Retries:** https://playwright.dev/docs/test-retries
- **Trace Viewer:** https://playwright.dev/docs/trace-viewer
- **Continuous Integration:** https://playwright.dev/docs/ci

Related programme chapters:

- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE215-L08 — Technical SEO and Web Discoverability
- SE240-L06 — Testing and Reliability in the Frontend
- SE310-L01 — The Frontend–Backend Contract
- SE440-L03 — Testing Strategies for Complex Systems
- CS430-L05 — Designing Reliable Business Workflows

---

## Dense Cheatsheet — Interview Glance Card

*The following reference is fenced for convenient TTS skipping.*

```text
SE215-L07 — OWNING END-TO-END TESTING

CORE QUESTION
  Can the customer complete a meaningful journey
  through the system boundaries actually under test?

THREE TEST SCOPES
  Browser + mocked API:
    Tests frontend behavior against controlled responses

  Browser + real test backend:
    Tests genuine frontend/backend integration

  Browser + production-like deployment:
    Includes more infrastructure and deployment boundaries

  Playwright alone does not define the scope of an E2E test.

WHAT TO TEST
  Prioritize critical user journeys
  Choose by business risk, change frequency, complexity
  Test detailed permutations at lower levels where appropriate
  E2E suite should be small enough to remain trustworthy

PLAYWRIGHT
  Real browser automation
  Chromium, Firefox, WebKit
  Locators and auto-waiting
  Browser contexts for test isolation
  Fixtures and API request capabilities
  Network interception
  Parallel execution
  Trace viewer and CI integration

LOCATORS
  Prefer roles and accessible names
  Prefer stable user-facing contracts
  Use test IDs when appropriate
  Avoid brittle DOM-position selectors
  Semantic markup improves accessibility and testability

WAITING
  Wait for meaningful conditions
  Avoid arbitrary sleep delays
  Auto-waiting handles many actionability conditions
  Assertions can retry until expected state appears
  Network idle != business operation complete

STATE ISOLATION
  Browser contexts isolate client-side state
  They do NOT isolate shared backend state
  Use unique customers/reservations as appropriate
  Test-worker isolation may be necessary
  Cleanup may fail after crashes
  Design test namespaces and periodic cleanup

AUTHENTICATION
  Storage state can avoid repeated UI login
  Keep saved auth state out of Git
  Treat session artifacts as credentials
  Shared accounts okay only when tests won't conflict
  Distinct accounts/tenants for mutating parallel tests
  Keep dedicated authentication tests

FIXTURES
  Explicit reusable test setup and teardown
  Prepare meaningful domain resources
  Avoid hidden giant fixture frameworks
  Test-only seeding must be appropriately protected
  Prefer deterministic starting conditions

MOCKING
  Great for rare frontend failure cases
  Great for controlled timing and error responses
  Does not prove real backend behavior
  Know which requests are intercepted
  Do not mistake transport failure for confirmed server rollback

FLAKINESS
  Common causes:
    Arbitrary waits
    Shared database state
    Timing races
    Fragile selectors
    Animations
    Overloaded CI resources
    Expiring data / current-date assumptions
  Retry success does not prove correctness
  Investigate traces, logs, network, data, environment

CI PORTFOLIO
  PR:
    Fast checks + critical browser smoke tests

  Post-deploy:
    Verify meaningful deployed workflows

  Broad regression:
    Additional browsers, roles, failure cases
    Scheduled or risk-based

OWNERSHIP
  Developers own feature verification and relevant tests
  QA specialists contribute strategy and risk expertise
  Platform supplies test infrastructure
  Team acts on failing tests rather than ignoring them

SENIOR INTERVIEW ANSWER
  1. Identify critical customer journeys
  2. Define real versus mocked boundaries
  3. Establish isolated and deterministic test data
  4. Choose authentication strategy
  5. Use resilient locators and condition-based waits
  6. Control parallelism and shared state
  7. Capture diagnostic artifacts
  8. Integrate fast smoke tests into CI
  9. Add deeper deployment/regression verification
 10. Establish clear ownership of failures

MENTAL MODEL
  Behavior — what customer outcome?
  Boundaries — what is real?
  State — can we reproduce the start?
  Synchronization — what are we waiting for?
  Evidence — can we explain the failure?

FINAL PRINCIPLE
  A trustworthy E2E suite is not an impressive collection
  of browser scripts. It's reliable evidence that important
  customer workflows actually function.
```
