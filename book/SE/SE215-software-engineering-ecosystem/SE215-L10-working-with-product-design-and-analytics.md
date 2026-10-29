---
id: SE215-L10
course: SE215
title: "Working With Product, Design, and Analytics"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L09
next: SE215-L11
---


# SE215 — The Software Engineering Ecosystem

## Lecture 10: Working With Product, Design, and Analytics

*The new checkout is beautiful. The product manager approves it, the designer loves it, the developers implement it exactly, and QA finds no blocking defects. Three weeks after release, booking conversion has fallen. Nobody made an obvious mistake. So why did the project fail?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine Mercury, our hotel-booking company, wants to improve its checkout experience.

The existing booking form looks old-fashioned.

It has several awkward fields, a crowded summary panel, and a payment section that the design team considers visually confusing.

The product manager proposes a redesign.

The designer produces a clean, modern interface in Figma.

There is more whitespace, clearer typography, elegant cards, and a simplified progress indicator.

The frontend team implements the design.

The backend needs almost no changes.

QA confirms that the new checkout functions correctly.

The release goes to production.

Everyone believes the project is complete.

Then an analyst notices something disturbing.

Before the redesign, eight percent of customers entering checkout completed a booking.

After the redesign, the measured completion rate is seven percent.

That is a decline of one percentage point, or twelve and a half percent relative to the previous rate.

If the change genuinely caused that decline, it could represent a substantial amount of lost business.

What went wrong?

Perhaps the new design hides important cancellation information.

Perhaps a prominent button becomes less visible on small screens.

Perhaps customers no longer understand which price includes taxes.

Perhaps the new experience creates a delay while retrieving payment information.

Or perhaps the apparent decline is a measurement error, a change in customer traffic, or ordinary statistical variation.

The team doesn't know yet.

But one thing is already clear.

**Implementing a specification correctly does not guarantee that the specification solves the right problem.**

That's the central lesson of this chapter.

## 1. Software development has more than one definition of success

As developers, we often think about success in technical terms.

The code compiles.

The tests pass.

The application responds correctly.

The deployment succeeds.

There are no obvious errors.

These are important achievements.

But businesses build software to accomplish something.

Mercury wants customers to discover hotels, complete reservations, and return for future bookings.

A redesigned interface is valuable only insofar as it improves some meaningful aspect of that experience.

This distinction introduces two different questions.

**Delivery:** Did we build the intended feature correctly?

**Outcome:** Did the feature produce the intended benefit?

A team can succeed at delivery and fail at outcomes.

Conversely, a product experiment can fail to improve the target metric while still providing valuable evidence about user behavior.

Not every unsuccessful hypothesis represents poor engineering.

The goal is to learn enough to make better decisions.

## 2. Product managers work with problems and priorities

A product manager is often responsible for understanding which problems are worth solving and coordinating decisions about product direction.

That includes customer needs, business goals, constraints, trade-offs, and prioritization.

A product manager doesn't necessarily write every requirement or personally decide every pixel.

And the role varies substantially across companies.

In Mercury's case, the product manager should be able to explain why checkout needs attention.

Perhaps analytics show many customers abandon the payment step.

Perhaps customer support receives complaints about unclear cancellation terms.

Perhaps research reveals that customers don't trust the final displayed price.

Those are different problems.

And they may require different solutions.

"Make checkout more modern" is a weak problem statement because visual modernization isn't itself the customer outcome.

"Reduce abandonment caused by unclear final pricing" is more useful.

It points toward a specific user difficulty and a measurable hypothesis.

## 3. Designers investigate how people experience the product

A designer doesn't merely choose colors and arrange rectangles.

Product and UX design can involve understanding user behavior, shaping journeys, organizing information, exploring interaction patterns, and testing whether an experience makes sense.

A wireframe may illustrate the structure of a screen.

A prototype can demonstrate an intended interaction.

A high-fidelity design may specify detailed visual behavior.

But a design file isn't automatically a complete behavioral specification.

A static screen may show what happens when everything works.

It may say nothing about the case where the payment provider times out.

Or the room becomes unavailable.

Or the user's name is unusually long.

Or the application is displayed on a narrow mobile screen.

Or a keyboard-only user navigates through the form.

Developers need to help identify those missing states.

## 4. Analytics turns observations into questions

Mercury collects information about how customers use the product.

A customer opens checkout.

They enter dates.

They review the price.

They select a payment method.

They submit the booking.

The application records events describing those actions.

From these events, analysts can construct funnels and measure conversion.

But the numbers require interpretation.

Suppose many customers abandon the payment step.

That doesn't automatically mean the payment form is confusing.

Some may encounter declined cards.

Some may discover additional fees.

Some may simply be comparing prices.

Others may experience technical errors.

A funnel reveals where users stop progressing.

It doesn't, by itself, explain why.

Analytics is useful for detecting patterns and testing hypotheses.

User research, technical investigation, and domain knowledge help explain those patterns.

## 5. Engineering belongs in the conversation before implementation

Now imagine the product manager, designer, analyst, and developer discuss Mercury's checkout problem.

The analyst identifies unusually high abandonment after final pricing appears.

The designer suspects that the price breakdown is difficult to understand.

The developer notices that the frontend initially displays a preliminary price, then updates it after an additional API request.

That creates a short interval where customers see one amount followed by another.

Suddenly the discussion changes.

The issue may not be purely visual.

It may involve how the application obtains and presents authoritative prices.

Perhaps the API contract should expose a complete pricing breakdown earlier.

Perhaps the UI should explicitly distinguish estimates from final totals.

Perhaps the product should avoid showing a price as confirmed before its relevant conditions have been established.

This is what cross-functional collaboration should accomplish.

Different disciplines provide different evidence.

The team develops a better understanding of the problem.

**A good developer doesn't wait until every important decision has already been made to contribute engineering judgment.**

### Three questions before the Deep Dive

1. How can a feature be technically correct but unsuccessful from a product perspective?
2. What important information might be missing from a polished Figma screen?
3. Why does observing that customers abandon checkout not prove that the checkout design caused the abandonment?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Discovery and delivery: two different kinds of uncertainty

Mercury's product team is preparing the next checkout improvement.

Before writing code, it needs to decide what to build.

This is commonly called **product discovery**.

Discovery investigates user problems, opportunities, assumptions, and possible solutions.

It can involve customer interviews, usability testing, product analytics, prototypes, technical exploration, and experiments.

Once a direction has been selected, the team must implement and release it.

That is **product delivery**.

The two activities overlap.

A developer may create a prototype during discovery.

A production release may reveal new information that changes the product hypothesis.

But they answer different questions.

Discovery asks whether we're pursuing a useful solution.

Delivery asks how to implement that solution safely and effectively.

### The dangerous handoff

A weak organization treats these phases as a rigid sequence.

Product writes requirements.

Design produces screens.

Engineering implements them.

QA tests the implementation.

Then everyone discovers that the original assumptions were wrong.

A healthier approach involves engineering earlier.

A developer can identify technical constraints, propose simpler alternatives, estimate risks, and expose hidden interactions.

The goal isn't to have developers overrule every product decision.

It's to prevent important engineering knowledge from arriving after the design is considered finished.

## 2. Turning an objective into requirements

Suppose Mercury states:

"We want customers to feel more confident about the final booking price."

That is a useful objective, but it isn't yet an implementable specification.

We need to understand which behavior should change.

Perhaps the application must display all mandatory fees before the customer reaches payment.

Perhaps taxes must be represented consistently across currencies.

Perhaps cancellation conditions must be visible before confirmation.

Perhaps the displayed total must remain consistent with the amount eventually charged.

Now we can define requirements.

### Functional requirements

Functional requirements describe what the system must do.

For example:

The checkout displays a final price breakdown.

The customer can inspect cancellation terms.

The amount submitted for payment matches the authoritative booking total.

The system handles inventory or price changes before confirmation.

### Nonfunctional requirements

Nonfunctional requirements describe important qualities or constraints.

For example:

The interface must work on narrow mobile screens.

Interactive controls must be keyboard accessible.

The price breakdown must remain understandable when translated into longer languages.

The final checkout step must meet appropriate responsiveness requirements.

Sensitive payment details must not leak into analytics.

### Acceptance criteria

Acceptance criteria make the expected behavior testable.

Consider:

"When a customer confirms a reservation, the displayed total must match the amount recorded for the corresponding payment operation, subject to explicitly defined currency and rounding rules."

That's stronger than:

"The new checkout should look like the Figma mockup."

It identifies an invariant connecting frontend, backend, and payment behavior.

The team can now test it.

## 3. User journeys reveal missing states

A single screenshot usually represents one moment.

A user journey represents a sequence of interactions and decisions.

Let's map Mercury's checkout.

The customer selects a room.

The application calculates the applicable price.

The customer enters personal information.

The customer reviews the reservation terms.

The customer selects a payment method.

The system attempts to confirm the booking.

Finally, the customer receives an authoritative outcome.

Now add failure paths.

What happens if the room is no longer available?

What happens if the payment is declined?

What happens if the server commits the booking but the response is lost?

What happens if the customer navigates backward?

What happens if the price changes before final confirmation?

What happens if the customer attempts to submit twice?

These aren't merely technical edge cases.

They are product experiences.

A customer doesn't care whether the underlying failure originated in Vue, PostgreSQL, or a payment provider.

They care whether the application explains the situation and preserves their trust.

A mature user journey includes loading, empty, error, recovery, and success states where relevant.

## 4. Wireframes, prototypes, and Figma handoff

Let's examine how the design reaches engineering.

A designer might begin with low-fidelity wireframes describing information structure.

Next comes an interactive prototype exploring how screens connect.

Eventually, the team may create high-fidelity designs with actual spacing, typography, colors, icons, and component states.

Figma is one common tool for this process.

Its developer-oriented features can help engineers inspect properties, variables, assets, annotations, and design changes.

But the workflow depends on how the organization uses the tool.

### The difference between design and implementation

Suppose Figma shows a price summary panel with four rows.

The developer can inspect dimensions and typography.

But several questions remain.

Does the panel become sticky on desktop?

What happens on mobile?

How are missing optional fees represented?

What if a long translated label wraps?

Is a discount displayed as a negative number or as a separate informational line?

What should happen while the authoritative price is being refreshed?

The design file may answer some of these questions.

Others require discussion.

A practical developer should identify ambiguities rather than silently invent behavior.

### Design handoff is a conversation

Good handoff material can include:

A description of the intended user behavior.

Relevant responsive states.

Interaction states.

Accessibility expectations.

Links to shared design components.

Known constraints and unresolved questions.

A developer should be able to explain what the implementation will do, not merely reproduce one static image.

## 5. Design systems and design tokens

Mercury has two frontends: a public booking site and an administrative application.

Both use the same brand and many similar interface components.

Without coordination, each team gradually creates its own buttons, spacing conventions, form styles, and error messages.

The applications become visually inconsistent.

Changes become expensive because the same design decision must be implemented repeatedly.

A **design system** provides reusable guidance, patterns, and components.

It may include typography, color, spacing, interaction rules, accessibility conventions, and component behavior.

A **design token** represents a reusable design decision in a technology-neutral or implementation-friendly form.

For example, the semantic token `color-feedback-error` might map to a particular color value.

The implementation can use that token instead of embedding arbitrary colors throughout the application.

### Tokens are not a substitute for component semantics

A button isn't merely a rectangle with a certain background color.

It has states.

Normal.

Hovered.

Focused.

Disabled.

Loading.

It may represent a primary action, destructive action, or secondary navigation.

A design system should account for those behaviors.

And a shared component library should implement them consistently.

But there's a limit to reuse.

A universal component with fifty props may be harder to maintain than a few well-defined components.

The goal is coherent shared behavior, not the elimination of every duplicated line of frontend code.

## 6. Responsive design and accessibility are requirements

Mercury's checkout looks excellent on a designer's large desktop monitor.

But a substantial portion of customers use phones.

The screen is smaller.

The virtual keyboard occupies space.

The network may be slower.

Touch targets matter.

Payment-provider interfaces may appear in embedded or redirected flows.

A responsive implementation must consider what happens to information hierarchy and interaction, not simply scale everything down.

### Accessibility is not optional polish

Suppose the customer submits an invalid form.

The application highlights the problematic field with a red border.

But it doesn't explain the error in text.

A customer with impaired color vision or using a screen reader may not understand what happened.

WCAG's error-identification guidance requires detected input errors to be identified and described in text.

A developer should also consider proper labels, keyboard navigation, focus management, and accessible names.

These decisions affect real usability.

They often improve automated testing as well, because semantically meaningful controls are easier to locate reliably.

### An expensive late discovery

Imagine QA finds the mobile layout unusable one day before release.

The team says:

"But the design file only showed desktop."

That isn't a useful defense.

The right time to discuss supported devices and responsive states was before implementation.

Engineering requirements should reflect actual product usage, not only the screens that happened to be available.

## 7. Instrumentation: what does a conversion event mean?

Now let's examine the redesigned checkout's reported conversion decline.

Mercury's analytics team tracks a funnel.

A customer views checkout.

They begin entering payment information.

They submit the booking.

They receive confirmation.

At each stage, the application emits events.

But what exactly should count as a conversion?

A click on Confirm?

An HTTP request sent to the API?

A successful API response?

A committed reservation?

A captured payment?

These are different events.

### The authoritative success boundary

Suppose Mercury tracks booking success by firing a browser analytics event immediately when the customer clicks Confirm.

A customer clicks the button.

The network request fails.

The application displays an error.

Yet analytics records a successful booking.

The dashboard overstates conversions.

A better approach distinguishes user intent from confirmed business success.

The browser can record that the customer attempted to submit.

But successful booking confirmation should be associated with an authoritative business outcome.

Depending on the analytics platform, the system may deliver that fact through an appropriately controlled client or server-side event mechanism.

### Event identity

Repeated rendering, retries, navigation, and duplicate deliveries can produce repeated analytics events.

So meaningful conversion events need an appropriate identity and deduplication strategy.

For ecommerce tracking, Google Analytics recommends purchase events containing transaction identifiers and other relevant fields.

Its deduplication behavior has specific limitations and should not be treated as a replacement for an authoritative booking or payment ledger.

The principle is broader than GA4:

**An analytics event must have a clear meaning, trigger, identity, and ownership.**

Otherwise, the dashboard can be confidently wrong.

## 8. Funnels: choosing the correct denominator

Let's inspect Mercury's checkout funnel.

Suppose ten thousand unique eligible customers enter checkout.

Eight hundred complete a booking.

The completion rate is eight percent.

But what if the analyst divides completed bookings by total checkout-page views instead?

One customer may open the page three times.

Another may navigate backward and forward.

A third may refresh after a payment error.

The number of page views exceeds the number of unique customers.

The measured rate changes.

Neither calculation is automatically meaningless.

But they answer different questions.

A meaningful metric definition needs a specified unit.

For example:

"Unique customers who complete a confirmed booking within the observation window, divided by unique customers who became eligible and entered checkout during that window."

Other products may use sessions or checkout attempts instead of customers.

The important requirement is consistency.

### Segments reveal different experiences

Suppose total conversion falls after the redesign.

Is the decline uniform?

Perhaps desktop conversion improves while mobile conversion deteriorates.

Perhaps existing customers perform better while first-time customers struggle.

Perhaps one payment method has a new technical problem.

Perhaps translated labels cause a layout failure in French.

Segmenting the data can reveal useful patterns.

But slicing the data into dozens of tiny segments also increases the risk of finding random patterns.

Use segments to investigate plausible mechanisms, not to manufacture a positive result somewhere.

## 9. A/B testing: separating change from coincidence

Mercury wants to know whether the redesign actually improves checkout completion.

A straightforward before-and-after comparison isn't enough.

Traffic composition may change.

Seasonality may affect purchase behavior.

Marketing campaigns may bring different customers.

External events may influence travel demand.

A controlled A/B experiment can provide stronger evidence.

One eligible group sees the original checkout.

Another sees the redesigned checkout.

Assignment should be randomized according to a defined unit, such as a customer, and remain stable where the experiment requires it.

Both variants operate during the same general period.

Now the team can compare outcomes under more comparable conditions.

### Assignment and exposure are not identical

Suppose a customer is assigned to variant B but never actually visits checkout.

Should they count as exposed to the new checkout?

That depends on the experiment design and estimand.

The team must distinguish assignment from actual exposure and define its analysis accordingly.

A common approach records exposure when the user becomes eligible to encounter the tested experience.

But exposure logging itself can introduce bugs.

If the new checkout crashes before emitting exposure, affected variant-B users might disappear from the analysis.

That can make the surviving group look artificially successful.

### Sample-ratio mismatch

Suppose Mercury expects a fifty-fifty allocation.

But the experiment reports substantially more observed users in one variant than randomness would reasonably explain.

This is called sample-ratio mismatch, or SRM.

It may indicate problems with assignment, eligibility, logging, filtering, or technical failures that disproportionately affect one variant.

A persistent unexplained SRM undermines trust in the experiment.

The correct response is to investigate the data before declaring a winner.

### Don't peek until something looks good

Another failure occurs when a team repeatedly checks results and stops as soon as a desirable difference appears.

Ordinary statistical tests generally require a suitable analysis plan.

Stopping opportunistically or comparing many metrics without appropriate methods can produce misleading conclusions.

We don't need to reproduce an advanced statistics course here.

The engineering lesson is to agree on the primary outcome, decision framework, and analysis procedure before the experiment.

CS120 provides the deeper statistical foundation.

## 10. Primary metrics and guardrails

Let's design Mercury's experiment properly.

The primary goal is to improve confirmed booking conversion among eligible checkout entrants.

That becomes the primary metric.

But what if the redesign improves the number of bookings while increasing payment errors?

Or customers complete more bookings but later cancel at a higher rate?

Or the checkout becomes less accessible?

This is why experiments need **guardrail metrics**.

Guardrails monitor important outcomes we don't want to harm.

For Mercury, they might include payment failures, application errors, mobile performance, customer support complaints, and cancellation patterns.

Not every guardrail needs a complex statistical model.

Some represent operational thresholds that should trigger immediate investigation.

### Metrics have different roles

A primary metric helps answer whether the experiment achieved its main objective.

Secondary metrics help explain behavior.

Guardrails identify potentially unacceptable consequences.

For example, reducing checkout time may be a useful secondary result.

But faster checkout isn't a victory if customers unknowingly accept conditions they don't understand.

The team should choose measurements based on the actual product objective and risks.

## 11. Feature flags and gradual rollout

Mercury implements the redesigned checkout behind a feature flag.

The code is deployed to production, but the new experience is initially disabled.

The team enables it for internal users.

Then it performs a controlled rollout or experiment.

This separates deployment from exposure.

It provides opportunities to detect errors before the entire customer base encounters the new behavior.

But there's a distinction between a **gradual rollout** and a **controlled experiment**.

A gradual rollout primarily manages operational and product risk by exposing the feature to progressively more users.

An experiment aims to estimate the effect of a change through a suitable comparison.

A rollout isn't automatically a valid experiment.

### Stable assignment matters

If a customer sees the new checkout on one page load and the old checkout on the next, the experience becomes confusing.

It may also contaminate the experiment.

Assignment should follow a stable, appropriately scoped rule.

But stable assignment introduces further questions.

What happens when the user signs in after beginning as anonymous?

What if the same person uses two devices?

What if experiment eligibility changes?

These aren't reasons to avoid experimentation.

They're implementation details that affect the validity of the results.

The analytics and engineering teams need to agree on them.

## 12. The investigation: why did conversion fall?

Let's return to our opening incident.

Mercury observes that checkout completion fell after the new design was released.

The team begins with four hypotheses.

First, the design is less understandable.

Second, the new frontend introduced a technical failure.

Third, the analytics implementation changed.

Fourth, the measured decline reflects other changes in the population or measurement period.

### Step one: verify the measurement

Was the success event defined consistently before and after release?

Did the new implementation move the event trigger?

Are duplicate events handled correctly?

Did the population entering checkout change?

If the metrics aren't comparable, the reported decline may not represent a genuine behavioral change.

### Step two: inspect technical signals

Did JavaScript errors increase?

Did checkout requests fail more often?

Did response times change?

Was the payment integration affected?

Did the new layout perform poorly on mobile devices?

A technically caused conversion decline can masquerade as a design problem.

### Step three: inspect the funnel

Where does the largest drop occur?

Before reviewing the price?

During payment entry?

After final submission?

Which devices, languages, and customer segments are affected?

This helps narrow the candidate explanations.

### Step four: examine user behavior

Usability research may reveal that customers cannot find the cancellation policy.

Session recordings or similar behavioral tools, where lawfully and appropriately configured, may reveal interaction difficulties.

Customer support may identify confusing wording.

These observations can suggest mechanisms, though they don't by themselves prove causality.

### Step five: test a correction

Suppose the evidence suggests customers don't understand whether taxes are included.

The team changes how the total price is presented.

It instruments the relevant behavior and runs an appropriately designed experiment.

Now it can evaluate whether the change improves the chosen outcome without harming guardrails.

The important point is that Mercury didn't immediately redesign the entire checkout again.

It investigated the specific failure.

## 13. What the senior engineer contributes

An experienced engineer is not merely the person who converts Figma into React or Vue components.

They can help the team discover hidden requirements.

They know which product behaviors are difficult to implement reliably.

They recognize when analytics events don't represent authoritative business facts.

They can identify missing error states and accessibility concerns.

They understand that a visually simple change may affect API contracts, performance, caching, or payment workflows.

They can build features that are observable, testable, and safely reversible.

And they can participate intelligently when metrics contradict expectations.

A strong engineering contribution isn't just:

"I implemented the screen exactly."

It's:

"We identified the underlying problem, agreed on the relevant behavior, implemented it safely, measured the outcome, and learned whether our assumptions were correct."

This is not about turning every developer into a product manager or analyst.

It's about recognizing that software engineering sits inside a larger system of product decisions and customer outcomes.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — Delivery versus outcome

The redesigned checkout matches Figma perfectly, passes tests, and deploys successfully. Conversion falls. Did engineering succeed?

### Question 2 — The incomplete design

A designer provides a polished desktop checkout screenshot. What questions should the developer ask before implementation?

### Question 3 — The wrong conversion event

A frontend emits `booking_completed` when the customer clicks Confirm. Why might that be misleading?

### Question 4 — The metric denominator

Mercury reports eight hundred bookings from ten thousand checkout entrants. Another analyst divides those bookings by fourteen thousand checkout-page views. Are they measuring the same thing?

### Question 5 — An experiment with uneven groups

An experiment was configured for equal allocation, but substantially more users appear in one variant than expected. What should the team investigate before trusting the result?

### Question 6 — Faster but worse

The redesigned checkout reduces time to submit by twenty percent but increases payment failures. Should the experiment be declared successful?

### Question 7 — Engineering involvement

Why should developers participate in discussions about product requirements and design before implementation begins?

### Question 8 — Post-release investigation

Conversion drops after a release. What would you inspect before deciding to roll back the design?

---

# Solutions and Discussion

## Solution 1 — Technical success, uncertain product success

The implementation may satisfy its technical requirements while failing to achieve the product objective.

Engineering should still investigate whether technical defects, measurement changes, or product assumptions explain the result.

A valid experiment producing a negative result can still provide useful learning.

## Solution 2 — Discover missing behavior

Clarify responsive layouts, accessibility, keyboard interaction, loading and error states, validation, translations, data dependencies, payment failures, and business-rule edge cases.

A static image isn't a complete interaction contract.

## Solution 3 — Attempted action versus authoritative completion

A click establishes intent, not necessarily a successful reservation.

The API might reject the request, the payment might fail, or the business operation might remain uncertain.

Track attempts separately from confirmed business outcomes.

## Solution 4 — Different units of analysis

Unique checkout entrants and page views are different denominators.

The resulting rates answer different questions.

Define the eligible population and unit consistently before comparing variants or time periods.

## Solution 5 — Check experiment integrity

Investigate assignment, eligibility, exposure logging, variant-specific crashes, filtering, and identity consistency.

An unexplained sample-ratio mismatch can invalidate the comparison.

## Solution 6 — Consider guardrails and the actual objective

Faster submission is not sufficient if payment reliability deteriorates.

Evaluate the primary metric alongside important guardrails and the overall customer outcome.

## Solution 7 — Prevent expensive late discoveries

Engineers can identify hidden dependencies, missing states, feasibility issues, simpler solutions, measurement problems, and operational risks before implementation becomes costly.

## Solution 8 — Verify, segment, and diagnose

Check metric definitions and instrumentation, exposure patterns, traffic composition, technical errors, performance, funnel stages, and customer segments.

If serious customer harm or a technical defect is established, mitigate promptly. Otherwise, investigate sufficiently before attributing the change to the design.

---

# The Mental Model Worth Keeping

A product feature moves through five connected questions.

**Problem:** Which customer or business difficulty are we trying to address?

**Behavior:** What must the application actually do, including edge cases?

**Delivery:** Can we implement and release that behavior safely?

**Measurement:** What evidence would show whether the intended outcome occurred?

**Learning:** What should we change after observing the result?

Product management, design, analytics, and engineering contribute different kinds of knowledge to these questions.

Their responsibilities differ, but their work must connect.

**A senior engineer doesn't merely build what was requested. They help ensure the team understands what it's building, why it matters, and whether it actually worked.**

# Next Lecture — SE215-L11: Release Management, Versioning, and Change Ownership

Mercury's redesigned booking flow is ready in principle.

The product brief is clear. Design and analytics are aligned. The implementation is reviewed.

Then someone asks the practical question every shipping team eventually faces:

Which version is this?

Is it tagged? Built? Deployed to staging? Visible to customers?

Who approves Thursday's window—and what do we undo if conversion collapses after the announcement?

Git, CI, and feature flags are parts of the answer, but release management is the discipline that connects them.

In the next lecture, we'll examine versioning, release ownership, staged rollouts, and rollback decisions from the perspective of a developer who may have to own the release themselves.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — The Checkout Redesign That Went Wrong

## Lab A — Write a product brief

Mercury's product manager gives you this request:

> Redesign checkout to reduce abandonment. The new layout should be cleaner, with fewer fields, clearer pricing, and a more modern payment section.

Before writing code, produce a one-page product brief containing:

1. The observed customer problem and the evidence supporting it.
2. A testable hypothesis about the cause.
3. The intended behavior change.
4. Critical functional and nonfunctional requirements.
5. Dependencies on backend, payments, design, and analytics.
6. What success would mean.
7. Important risks and unresolved questions.

Avoid treating "make it modern" as a testable requirement.

## Lab B — Review the design handoff

Assume the designer supplies a Figma file showing three desktop screens:

- Customer information.
- Payment details.
- Reservation confirmation.

The screens look polished, but no additional information is provided.

Create a design-review checklist.

At minimum, examine:

- Mobile and tablet layouts.
- Keyboard and screen-reader behavior.
- Field validation and descriptive errors.
- Loading indicators and unavailable states.
- Payment failures and uncertain outcomes.
- Long translated strings.
- Price and currency formatting.
- Cancellation-policy visibility.
- Back navigation and loss of form state.
- Interaction with existing design-system components.

Prioritize the most important missing information.

Not every ambiguity deserves a week-long meeting, but consequential behavior shouldn't be guessed.

## Lab C — Design an analytics event contract

Mercury wants to measure the checkout funnel.

Consider these events:

```text id="6d2nx2"
checkout_viewed
payment_step_viewed
booking_submit_attempted
booking_confirmed
booking_failed
```

For each event, specify:

- The event's exact meaning.
- Where it is emitted.
- What identifier links it to a customer, session, attempt, or reservation.
- What timestamp it represents.
- Whether repeat emission is valid.
- Which potentially sensitive fields must be excluded.

Decide whether `booking_confirmed` should be produced directly from a frontend click or tied to an authoritative backend outcome.

Then design a reconciliation method that compares analytics conversions with real bookings in the operational database.

### Example event

An illustrative event might look like this:

```json id="8v7yhf"
{
  "event_name": "booking_submit_attempted",
  "schema_version": 1,
  "checkout_attempt_id": "attempt-10482",
  "reservation_id": null,
  "experiment_variant": "B",
  "event_time": "2026-10-28T14:32:00Z"
}
```

The event describes an attempt, not a successful booking.

Avoid including raw payment details, unnecessary personal information, or credentials.

This is a conceptual application-event schema, not a prescribed GA4 payload.

## Lab D — Analyze the conversion decline

Mercury's fictional A/B experiment reports:

| Metric | Original checkout A | Redesigned checkout B |
|---|---:|---:|
| Eligible unique checkout entrants | 10,000 | 10,000 |
| Confirmed bookings | 800 | 700 |
| Checkout completion rate | 8.0% | 7.0% |
| Payment API failure rate | 1.2% | 2.0% |
| Median checkout duration | 4m 10s | 3m 30s |

Answer:

1. Which variant has the higher observed conversion rate?
2. What is the absolute and relative difference?
3. Does faster checkout establish a better product outcome?
4. Which technical metric deserves investigation?
5. Can we conclude the redesign caused the difference solely from these summary numbers?
6. What additional statistical and experiment-integrity information would you request?

The raw results do not establish a statistically defensible causal conclusion by themselves. Verify randomization, consistent metrics, exposure logging, and the experiment's analysis plan.

## Lab E — Find the broken experiment

Now imagine the experiment is configured for a fifty-fifty allocation.

However, the collected exposure events show:

```text id="pw9na3"
Variant A: 10,000 exposed users
Variant B:  8,100 exposed users
```

The new checkout has a JavaScript error that occurs before exposure is logged on a subset of mobile devices.

Explain how that could bias the observed comparison.

Then design a corrective instrumentation and assignment strategy.

Investigate the sample-ratio mismatch rather than merely renormalizing the numbers and declaring a winner.

## Lab F — Plan a safe feature rollout

Create a release plan for the redesigned checkout.

It should include:

- Automated tests for the user journey.
- Compatibility with backend contracts.
- Internal verification.
- Stable experiment assignment.
- An appropriate primary metric and guardrails.
- Deployment versus exposure controls.
- Monitoring for technical errors and payment failures.
- A clear decision about when to expand, pause, or revert exposure.
- Cleanup of temporary feature flags after the experiment concludes.

Distinguish operational rollback from experiment analysis.

An urgent production defect may justify disabling a variant before the planned experiment ends.

That does not mean the resulting incomplete experiment automatically provides a valid estimate of product impact.

## Lab G — Senior interview rehearsal

The interviewer says:

"A product manager asks you to implement a Figma checkout redesign. You notice that the design doesn't account for payment failures, mobile layout, or analytics instrumentation. What do you do?"

A strong answer should demonstrate collaboration rather than confrontation.

Explain which ambiguities you'd identify, which questions you'd prioritize, what implementation contracts you'd clarify, and how you'd work with product, design, QA, and analytics.

Then describe how you'd verify both technical behavior and product outcomes after release.

The aim is to show pragmatic engineering ownership—not to claim that developers should make every product decision themselves.

---

# Further Reading

Primary references:

- **Figma — Guide to Dev Mode:** https://help.figma.com/hc/en-us/articles/15023124644247-Guide-to-Dev-Mode-in-Figma
- **Figma — Variables in Dev Mode:** https://help.figma.com/hc/en-us/articles/27882809912471-Variables-in-Dev-Mode
- **W3C — WCAG 2.2 Error Identification:** https://www.w3.org/WAI/WCAG22/Understanding/error-identification
- **Google Analytics — Recommended Events:** https://support.google.com/analytics/answer/9267735
- **Google Analytics — Ecommerce Events:** https://support.google.com/analytics/answer/12200568
- **Google Analytics — Transaction ID Deduplication:** https://support.google.com/analytics/answer/12313109
- **Statsig — Managing Sample Ratio Mismatch:** https://docs.statsig.com/experiments/monitoring/srm
- **Optimizely — Primary and Guardrail Metrics:** https://docs.optimizely.com/experimentation-strategy/docs/primary-metrics-secondary-metrics-and-monitoring-goals
- **DORA — DevOps Capabilities:** https://dora.dev/capabilities/

Related programme chapters:

- SE215-L01 — The People and Teams Behind Software
- SE215-L02 — How Engineering Work Gets Planned and Delivered
- SE215-L07 — Owning End-to-End Testing
- SE215-L09 — Data Engineering for Application Developers
- SE240-L02 — Frontend Architecture Beyond Components
- SE240-L03 — State Management and Reactive Applications
- SE310-L01 — The Frontend–Backend Contract
- CS120 — Mathematics and Statistics
- SE440-L03 — Testing Strategies for Complex Systems

---

## Dense Cheatsheet — Interview Glance Card

```text id="2vffqe"
SE215-L10 — PRODUCT, DESIGN, ANALYTICS

CORE DISTINCTION
  Delivery success != product outcome success
  Correct implementation != correct product hypothesis

PRODUCT DISCOVERY
  Understand customer problems and business opportunities
  Research assumptions and possible solutions
  Define what should change and why

PRODUCT DELIVERY
  Implement requirements safely
  Test and deploy
  Verify both technical behavior and release constraints

PRODUCT MANAGEMENT
  Problems, outcomes, priorities, trade-offs
  Requirements and stakeholder alignment
  Role varies by company

DESIGN / UX
  User journeys, wireframes, prototypes
  Interaction states, information hierarchy
  Accessibility, responsive behavior, usability
  Static Figma screen != complete behavior specification

FIGMA HANDOFF
  Inspect components, variables, assets, properties
  Clarify responsive states and behavior
  Identify loading, empty, error, success states
  Ask about long text, mobile, keyboard, accessibility
  Resolve consequential ambiguity before implementation

DESIGN SYSTEM
  Shared visual and interaction conventions
  Components, patterns, design tokens
  Semantic tokens rather than scattered magic values
  Reuse should reduce inconsistency, not create complexity

REQUIREMENTS
  Functional = what the application does
  Nonfunctional = important quality and constraints
  Acceptance criteria = verifiable behavior
  Include failure/recovery states and domain invariants

PRODUCT ANALYTICS
  Events must have defined triggers and meaning
  Attempted action != successful business operation
  Identity and deduplication matter
  Analytics conversion should reconcile with operational truth
  Avoid unnecessary PII and sensitive details

FUNNELS
  Track meaningful journey stages
  Define numerator and denominator
  Users != sessions != page views != attempts
  Drop-off identifies where, not necessarily why

A/B EXPERIMENT
  Define hypothesis and primary metric before starting
  Randomize using appropriate assignment unit
  Keep assignment stable as required
  Distinguish assignment from exposure
  Monitor experiment health
  Don't infer causality from simple before/after results
  Don't stop opportunistically at a pleasing result

SAMPLE RATIO MISMATCH (SRM)
  Observed split inconsistent with intended allocation
  May signal logging, eligibility, crash or assignment defect
  Investigate before trusting apparent metric lift

METRICS
  Primary: desired outcome
  Secondary: explanatory evidence
  Guardrails: unacceptable harms to prevent
  Conversion improvement must not mask payment failures

ROLLOUT
  Deployment != customer exposure
  Feature flags enable progressive exposure
  Gradual rollout != automatically valid A/B experiment
  Define monitoring and rollback conditions
  Remove obsolete flags and variant-specific code

PRODUCTION INVESTIGATION
  1. Confirm metric definitions
  2. Verify instrumentation
  3. Inspect technical errors and performance
  4. Segment funnel by device, language, customer type
  5. Compare support and usability evidence
  6. Identify plausible root causes
  7. Test correction with appropriate methodology
  8. Monitor outcome and guardrails

SENIOR ENGINEER'S ROLE
  Participate before design is finalized
  Surface edge cases and technical dependencies
  Translate intentions into testable behaviors
  Protect business invariants and accessibility
  Instrument meaningful events
  Design safe release and verification
  Help distinguish product problems from technical bugs

MENTAL MODEL
  Problem -> Behavior -> Delivery -> Measurement -> Learning

FINAL PRINCIPLE
  Building a feature correctly is only one part
  of building a successful product.
```
