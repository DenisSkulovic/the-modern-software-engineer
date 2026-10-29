---
id: SE215-L12
course: SE215
title: "From Vague Business Idea to Shipped Product"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE215-L11
next: null
---

# SE215 — The Software Engineering Ecosystem
## Lecture 12: From Vague Business Idea to Shipped Product

*Your manager walks into a meeting, spends ten minutes describing a half-formed idea, announces that customers need it in two weeks, and leaves. There's no specification, no design, no technical plan, and no agreement about what success means. Congratulations. You own the feature.*

---

# Part I — Intuition

## 1. The Ten-Minute Meeting

It's Monday morning at Mercury, a growing hotel-booking company.

You're a full-stack developer responsible for parts of the booking experience.

Your manager calls you into a meeting.

"Support is drowning in requests from customers who want to change their reservations. We should let customers do it themselves. It can't be that complicated. Add a button to the booking page, show a calendar, let them choose new dates, and update the reservation."

You start asking questions.

"Can customers change hotels? What about prices? Do we need to recalculate payments? What if the new dates aren't available?"

The manager waves a hand.

"Figure out the details. We need something working in two weeks. Just make it happen."

The meeting ends.

You return to your desk.

There is no design.

There is no formal specification.

There is no dedicated product manager available for the next several days.

The frontend and backend repositories are large. Reservation logic crosses several services. Some bookings originate from external suppliers. Payments are handled through another integration.

And you are supposed to deliver a working customer feature in ten business days.

What do you do?

The inexperienced response is to immediately create a feature branch and begin building a calendar component.

The stronger response is to establish **what problem you're actually being asked to solve, which part can be solved safely, and what evidence would demonstrate success**.

The difference matters because the requested interface is only the visible surface of a much larger operation.

## 2. The Manager Gave You a Solution, Not a Requirement

"Add a button and calendar" sounds like a requirement.

But it is really a proposed solution.

The actual problem is that customers contact support to change reservations.

Why?

Perhaps customers cannot find their reservation details.

Perhaps changing dates requires human assistance.

Perhaps the existing cancellation process is confusing.

Perhaps many requests are simple date changes, but others involve payment adjustments, supplier approval, and complex policies.

These are different problems.

If the goal is to reduce support workload, adding a calendar only helps if customers can successfully complete the relevant operation.

A feature that allows customers to submit a change request but still requires support to process it may simply create another support queue.

The first responsibility is to distinguish the requested implementation from the desired outcome.

### Visual anchor 1 — Work backward from the outcome

```text id="nxq2af"
Manager's suggestion:
"Add a change-dates button"
             |
             v
Underlying problem:
"Customers need support
 to modify reservations"
             |
             v
Desired outcome:
"Eligible customers can
 complete changes themselves"
             |
             v
Engineering question:
"Which changes can we
 automate safely in two weeks?"
```

The button is not the objective.

Successful self-service is the objective.

## 3. You Don't Need Fifty Questions. You Need the Right Five.

When a request is vague, engineers sometimes respond with enormous questionnaires.

They demand a complete product specification before writing any code.

That can become another failure mode.

The business may genuinely not know all the answers yet.

A better response is to identify the assumptions that determine feasibility.

For our booking feature, five questions matter immediately.

**Which customers?** Are we targeting all reservations or a narrow group of eligible bookings?

**Which changes?** Date changes only, or also hotels, room types, prices, and guests?

**What are the rules?** Which bookings can be modified, and when?

**What happens to inventory and payments?** Can we guarantee that changing one reservation doesn't create an overbooking or financial inconsistency?

**What does success mean?** Are we reducing support tickets, increasing completed self-service changes, or improving customer satisfaction?

You may need more details eventually.

But these questions expose the major uncertainty before you start implementing.

## 4. The Two-Week Deadline Is a Constraint, Not a Specification

Suppose management says the work must fit within two weeks.

You cannot simply make every possible booking modification safe and reliable because a calendar invitation says Friday.

The deadline constrains the scope.

It doesn't remove the underlying complexity.

Perhaps the complete feature would support date changes, hotel transfers, room upgrades, refunds, additional payments, cancellation policies, and external supplier reservations.

That could be a substantial project.

But perhaps the first release can support only direct bookings at the same property, with the same room type and number of nights, where the price remains unchanged and the booking is still far enough from check-in.

This is a much smaller set of business cases.

It might still solve a meaningful portion of support requests.

### Visual anchor 2 — Reduce scope, preserve the outcome

```text id="h6e2va"
ALL BOOKING CHANGES
    |
    ├── Different hotel
    ├── Room upgrade
    ├── Additional payment
    ├── Partial refund
    ├── External supplier approval
    ├── Different guests
    └── Simple eligible date change
                 |
                 v
          First release candidate
```

The point is not to arbitrarily remove features.

It's to find a useful vertical slice whose technical and business risks are manageable.

**A small complete workflow is more valuable than a large collection of partially implemented screens.**

## 5. A Vertical Slice Crosses the Entire System

Imagine implementing only the frontend calendar.

It looks excellent.

The user selects new dates.

The button says Confirm.

But the backend operation isn't ready.

The feature isn't complete.

Now imagine implementing the backend endpoint without a usable interface, authorization checks, customer communication, or production verification.

That isn't a complete customer workflow either.

A vertical slice includes the necessary components across the system.

For our booking feature:

The customer opens a reservation.

The system determines whether it can be changed.

The customer sees available alternative dates.

The customer selects a valid option.

The backend verifies eligibility and availability again.

The reservation is changed safely.

The customer receives a confirmation.

The operation is recorded for support and audit.

The application reports a meaningful success event.

Each step may be small.

Together, they form an end-to-end product capability.

## 6. You Are Also Managing Risk

Changing booking dates isn't equivalent to changing a profile nickname.

It affects scarce inventory.

Suppose the customer moves a reservation from Friday to Saturday.

You must release the original inventory and reserve the new inventory correctly.

What if another customer books the last available room at the same moment?

What if the client sends the confirmation request twice?

What if the database commits, but the browser loses the response?

What if the customer has someone else's reservation ID?

What if a confirmation email fails after the reservation has already changed?

These are not obscure theoretical concerns.

They're ordinary production failure modes.

The feature is only safe if the business invariants survive them.

You don't need to become a database or security specialist overnight.

But you must recognize which operations require stronger guarantees and which assumptions need verification.

## 7. Product Design Doesn't Begin in Figma

Your manager suggested a calendar.

But what should the customer see before clicking it?

Perhaps the reservation is nonmodifiable.

Perhaps the cutoff has passed.

Perhaps no alternative dates are available.

Perhaps the customer is eligible, but the requested dates would increase the price, which the first release doesn't support.

A useful interface must represent those states.

Product design is not merely deciding whether the calendar should be blue or green.

It is deciding what the user needs to understand and what choices the system can safely offer.

In a small company, the developer might sketch these flows without a dedicated designer.

In a larger company, a product designer might lead the interaction design.

Either way, someone must establish the behavior.

## 8. Launching Isn't the End

Suppose you complete the feature in two weeks.

It passes tests.

The release succeeds.

Customers begin using it.

Can you declare the project successful?

Not yet.

Perhaps very few customers are eligible.

Perhaps eligible customers cannot find the feature.

Perhaps the interface works on desktop but fails on mobile.

Perhaps the feature reduces support tickets but increases booking errors.

Perhaps it saves agents time but causes more refund disputes.

The business goal requires measurement.

We need to know whether customers actually complete modifications and whether the operation creates unacceptable side effects.

### Visual anchor 3 — The complete engineering loop

```text id="m44x5a"
Business problem
      |
      v
Clarify and constrain
      |
      v
Design a safe workflow
      |
      v
Build a vertical slice
      |
      v
Test and verify
      |
      v
Deploy and expose
      |
      v
Measure outcomes
      |
      v
Learn and improve
```

This is the job of delivering software.

Writing code is one essential activity inside it.

### A tiny comprehension check

Your manager asks for a calendar, but the real business goal is reducing support workload. What should you optimize for?

Successful eligible self-service changes, with appropriate business and safety guardrails—not merely calendar completion.

You discover that payment-changing reservations would double the project scope. Should you silently ignore them?

No. You should make the limitation explicit, propose a useful smaller release, and obtain an informed scope decision.

And if all technical tests pass, but customers still call support because they cannot find the feature?

The implementation may be technically correct while the product outcome remains unsuccessful.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Begin with the Uncertainty, Not the Code

Let's reconstruct the first two hours after the manager leaves.

You have a vague request and ten business days.

What information would materially affect the implementation?

First, identify the business objective.

Suppose support receives a significant number of date-change requests every week. The manager wants to reduce manual work.

Now identify what constitutes a completed outcome.

A customer must be able to change an eligible reservation without an agent performing the modification.

Simply submitting a form doesn't necessarily meet that objective.

Next, inspect the existing system.

Can the backend already modify a reservation?

Is that capability used internally by support agents?

Does the inventory system expose an operation that can atomically move reserved capacity between dates?

How are booking policies represented?

Do direct and supplier-managed bookings follow different rules?

Is the current payment amount stored in a way that lets us verify a no-price-change restriction?

These questions establish whether the two-week scope is feasible.

### 9.1 Investigate before designing

One of the most valuable things an experienced developer can do is discover existing capabilities.

Perhaps the support team's internal tool already calls an API that changes booking dates safely.

If so, the project may primarily involve building a customer-facing interface, authorization, eligibility checks, and operational safeguards.

If not, the feature may require new core reservation logic.

Those are very different estimates.

A responsible engineer doesn't estimate solely from the visible frontend work.

### 9.2 Distinguish known, assumed, and unknown

You might produce a short engineering note.

**Known:** The customer portal can authenticate users and retrieve their reservations.

**Known:** Support agents can modify some reservations through an internal tool.

**Assumed:** A subset of direct bookings can be changed without payment adjustment.

**Unknown:** Whether the existing inventory operation handles concurrent date changes atomically.

**Unknown:** Whether supplier-managed bookings can be changed through the same API.

The important part is making consequential uncertainty visible.

The note doesn't need to be long.

It needs to identify what could invalidate the plan.

## 10. Discover the Real Business Workflow

Suppose you spend thirty minutes with a support specialist.

They explain that booking-change requests fall into several categories.

Some customers want to move their stay by one or two days.

Others want to change hotels.

Some need additional payments.

Some request partial refunds.

A portion of reservations are controlled by external suppliers.

Now you understand why support involvement exists.

The complexity isn't merely a missing calendar.

It's the business rules surrounding the operation.

### 10.1 Identify the valuable subset

You ask which category consumes the most predictable manual effort.

The support specialist says simple same-property changes are relatively common, provided the booking is still well ahead of check-in.

You verify whether those cases have a stable business policy.

If the existing backend can safely perform them, they become a candidate for the first release.

### 10.2 A numerical example

Imagine the support team handles 400 change-related contacts per month.

After examining a sample, the team estimates that 120 concern simple date modifications.

Suppose only half of those satisfy the proposed first-release eligibility rules.

That gives roughly 60 eligible cases per month.

These are hypothetical planning numbers, not measured facts about Mercury.

If the feature achieves an eighty-percent successful self-service completion rate among those eligible cases, it could deflect approximately 48 contacts per month.

That's a useful estimate.

But it may or may not justify the implementation cost.

The team should compare the expected benefit with the operational risks and maintenance burden.

### 10.3 Avoid confusing eligibility with adoption

Even if 60 customers are eligible, not all will discover or use the feature.

The outcome depends on discoverability, usability, and trust.

A technically eligible workflow is not automatically a successfully adopted product.

## 11. Write a One-Page Product Brief

You don't necessarily need a formal product requirements document.

For a small feature, a one-page brief may be sufficient.

But it should establish the key decisions.

### 11.1 Problem

Customers contact support for simple reservation-date changes that could potentially be completed through self-service.

### 11.2 Objective

Reduce avoidable support work while allowing eligible customers to safely modify their own reservations.

### 11.3 Target users

Authenticated customers with qualifying direct bookings.

### 11.4 First-release scope

Only same-property, same-room-type date changes with unchanged stay duration and total price, sufficiently far ahead of check-in.

No external supplier bookings.

No additional payments or refunds.

No hotel changes.

### 11.5 Success criterion

Customers can complete eligible changes without support intervention.

The team also measures completion rate, technical failures, support-contact changes, and reservation correctness.

### 11.6 Open questions

Can the existing inventory operation guarantee safe reservation movement?

Do all eligibility rules exist in authoritative backend data?

Can the two-week schedule accommodate the required integration testing?

This brief is not the final implementation plan.

It's a compact agreement about what problem the team is solving and which constraints apply.

## 12. Define the Business Invariants

Before designing the interface, establish what must always remain true.

For our first release, consider several invariants.

A customer may modify only a reservation they are authorized to manage.

A reservation cannot be moved outside its allowed policy window.

The new dates must be available at the moment the modification commits.

The inventory change must not create overbooking.

The reservation must not be charged twice or silently change price.

The operation must not leave inventory partially transferred if it fails.

Repeated confirmation attempts must not create multiple modifications.

The final reservation state must be auditable.

These constraints are more important than the precise appearance of the calendar.

### 12.1 Frontend validation isn't authoritative

The frontend can hide the Change Dates button for ineligible bookings.

That's useful.

But a client can send arbitrary HTTP requests.

The backend must enforce authorization and eligibility independently.

The system should not trust a reservation ID merely because the user obtained it through the interface.

### 12.2 The availability race

Suppose the frontend checks that a room is available for the requested dates.

The customer waits thirty seconds before confirming.

Another customer books the last room.

The original availability response is now stale.

The backend must revalidate availability as part of a safe commit operation.

A preliminary availability check improves user experience.

It is not a reservation guarantee.

### 12.3 The transactional boundary

If the original and new inventory allocations are managed within one transactional data system, the operation may be able to reserve the new capacity, release the old capacity, and update the booking atomically.

But if an external supplier or independent service owns part of the inventory, that guarantee may not be available through one database transaction.

This is why excluding unsupported supplier-managed bookings can materially reduce first-release complexity.

The two-week estimate depends on that boundary.

## 13. Model the User Journey

Now design the experience.

A simple flow might begin on the booking-details page.

The customer sees their reservation dates.

If eligible, the interface presents Change Dates.

Selecting it opens a calendar showing potential new dates.

The customer chooses an alternative.

The application verifies availability and price compatibility.

The user sees a confirmation summary.

The system performs the modification.

The user receives a final confirmation.

### 13.1 Design the states

The happy path isn't enough.

What happens when the booking is ineligible?

What happens when no equivalent-price dates are available?

What happens if the customer loses network connectivity?

What happens if the server completes the change but the response is lost?

What happens when the user retries?

What happens if the booking changes in another session during the workflow?

What happens if the confirmation email is delayed?

These states define much of the actual product.

### 13.2 Avoid misleading success messages

Suppose the customer confirms the change.

The server begins processing.

The frontend immediately displays:

"Your reservation has been updated."

But the operation hasn't committed yet.

That is misleading.

The interface should distinguish an operation in progress from one confirmed by the authoritative system.

If the outcome is uncertain because of a network interruption, the application may need to retrieve the current booking state before telling the user whether the modification succeeded.

### 13.3 Accessibility and mobile use

A date-picker must support keyboard access and clear interaction states.

Dates need accessible labels.

Unavailable dates should be understandable without relying only on color.

The confirmation screen should remain usable on narrow mobile displays.

Error messages should explain what the customer can do next.

These are functional aspects of the experience, not optional decorative improvements.

## 14. Write Acceptance Criteria Before Implementation

A good acceptance criterion describes observable behavior.

For example:

**Eligible booking:** Given an authenticated owner of an eligible direct booking, when valid available dates are selected and confirmed, the system changes the booking exactly once and returns the authoritative updated reservation.

**Ineligible booking:** Given a booking outside the modification policy, the customer cannot complete the operation, even if they call the API directly.

**Unavailable dates:** Given dates that become unavailable before confirmation, the modification fails without releasing the original inventory.

**Retry:** Given a confirmation request that succeeded but whose response was lost, repeating the same operation with the same idempotency identity must not perform the change again.

**Authorization:** Given a reservation owned by another customer, the operation must not disclose or modify that reservation.

**Audit:** Given a successful modification, an authorized support agent can identify the old and new dates and the relevant operation identity.

These criteria provide a contract between implementation, testing, product expectations, and release verification.

## 15. Find the Minimum Technical Architecture

Now examine the system.

Perhaps the frontend uses Vue or React.

The backend provides REST endpoints.

PostgreSQL stores reservations and inventory.

A background worker sends confirmation emails through an external service.

How much new architecture does the feature need?

Probably less than an enthusiastic engineer might initially propose.

### 15.1 Reuse appropriate capabilities

If the backend already exposes a safe booking-modification operation to internal tools, reuse its domain logic.

Don't implement a second version of inventory management in the customer-facing API.

The customer route may need stronger authorization, policy restrictions, and narrower supported behavior.

But the underlying invariant-preserving operation should have one authoritative implementation where practical.

### 15.2 Avoid an unnecessary microservice

A new feature doesn't automatically require a new service.

Creating a separate booking-modification microservice introduces deployment, networking, observability, configuration, and distributed transaction concerns.

Those costs may be justified at scale.

For a two-week vertical slice, existing service boundaries may be more appropriate.

### 15.3 Separate core changes from side effects

The booking modification is the authoritative business operation.

The confirmation email is a consequence of that operation.

If the email provider is unavailable, the booking shouldn't necessarily be rolled back after it has successfully committed.

Instead, a reliable notification workflow can process the event afterward.

That workflow must be able to retry safely.

The exact implementation may use an existing outbox, queue, or notification service.

The important distinction is between completing the reservation modification and delivering a secondary notification.

## 16. Design an API Contract

The customer needs a way to determine eligibility, explore valid alternatives, and confirm a change.

An API might expose an eligibility response, an availability query, and a modification command.

The exact URL design depends on the existing application.

### 16.1 Eligibility

The booking-details response might include whether the reservation is currently eligible for date changes.

It may provide a reason code when modification is unavailable.

But the backend must recheck eligibility when the customer actually confirms.

### 16.2 Availability

The frontend requests alternative dates.

The backend returns candidate options with the necessary price and availability information.

These options are provisional unless the architecture explicitly reserves inventory.

### 16.3 Confirmation

The final modification request includes the chosen dates and an idempotency key.

The backend validates the authenticated customer, current booking state, policy, price, and availability.

It performs the modification through the authoritative domain operation.

The response returns the updated booking or an appropriate failure.

### 16.4 Idempotency

Suppose the operation succeeds in the database, but the HTTP response is lost.

The browser retries.

Without idempotency, the backend might attempt the operation again.

The application can use a stable operation identity to recognize a repeated confirmation request.

But idempotency isn't merely storing an arbitrary key.

The system needs to bind that identity to the relevant customer, booking, and requested operation, and handle conflicting reuse safely.

## 17. Security Is Part of the Feature

This is a customer-facing endpoint modifying valuable business state.

The most immediate security risk is unauthorized access to another customer's booking.

A developer might implement:

"Find the booking by ID and update its dates."

But the endpoint must verify that the authenticated principal is authorized to modify that specific reservation.

This is an object-level authorization problem.

### 17.1 Never trust client-supplied ownership

The request may contain a booking ID.

It shouldn't be able to choose the owner.

The owner relationship comes from authoritative server-side data and the authenticated identity.

### 17.2 Avoid leaking booking details

A failed request for another customer's booking shouldn't reveal private reservation information.

Error semantics should follow the application's security policy.

### 17.3 Prevent abusive workloads

An attacker might repeatedly request expensive availability calculations or submit many modification attempts.

Rate limiting, request validation, and appropriate backend capacity controls can reduce abuse.

But arbitrary throttling shouldn't accidentally prevent legitimate users from completing an important operation.

### 17.4 Audit responsibly

Audit records should identify relevant operations without storing unnecessary sensitive information.

They should support legitimate operational investigation and access controls.

The goal is accountability, not indiscriminate data collection.

## 18. Testing the Vertical Slice

A two-week deadline does not justify skipping important tests.

It requires prioritizing the tests that protect the highest risks.

### 18.1 Unit tests

Test eligibility rules, date cutoffs, policy interpretation, and allowed price comparisons.

These are useful because they can run quickly and cover edge cases.

### 18.2 Integration tests

Test the actual interaction between booking state and inventory modifications.

Verify that the operation commits correctly and that failure leaves the original reservation valid.

Test concurrency where possible.

### 18.3 API tests

Verify authorization, validation, idempotency, and error responses.

An endpoint must not become secure only when called through the official frontend.

### 18.4 End-to-end tests

Exercise the customer journey from booking details to successful modification.

Include an unavailable-date scenario and a network failure.

Verify that the UI doesn't claim success before the backend confirms it.

### 18.5 Manual exploratory testing

A human tester can examine usability, confusing states, mobile behavior, and interactions that scripted tests may overlook.

This work can be performed by the developer in a small team.

In a larger organization, QA specialists may contribute more extensive expertise.

### 18.6 The test portfolio follows risk

Don't create hundreds of superficial tests merely to increase coverage numbers.

Prioritize the operations whose failure could create overbooking, unauthorized changes, incorrect payments, or misleading customer confirmations.

## 19. Plan the Work as a Two-Week Delivery

Let's establish an illustrative schedule.

The exact feasibility depends on existing infrastructure and team support.

### Day 1 — Problem and feasibility

Meet the relevant business owner.

Inspect support request categories.

Identify eligibility and policy rules.

Investigate whether the existing backend can safely move inventory.

Produce a short scope and feasibility decision.

### Day 2 — Contracts and user flow

Agree on the first-release scope.

Define acceptance criteria.

Sketch the key interaction states.

Establish the API contract and important failure cases.

### Days 3–4 — Backend vertical slice

Implement the narrow modification path.

Reuse existing domain logic.

Enforce authorization, eligibility, availability, and idempotency.

Add initial integration tests.

### Days 5–6 — Frontend journey

Build the booking-details entry point, calendar, confirmation, and failure states.

Connect to the backend.

Verify mobile and accessible interaction.

### Day 7 — End-to-end integration

Test representative eligible and ineligible bookings.

Exercise concurrency and retry behavior.

Investigate unexpected integration issues.

### Day 8 — Quality and operational readiness

Complete high-risk tests.

Review monitoring and audit behavior.

Prepare feature flags and release checks.

Resolve important defects.

### Day 9 — Controlled release

Deploy the approved artifact.

Verify backend compatibility.

Enable the feature for internal users or a small eligible cohort.

Observe errors and business outcomes.

### Day 10 — Stabilization and handoff

Review early results.

Fix critical issues.

Document known limitations.

Agree on monitoring and next steps.

This schedule is not a promise.

It's a planning hypothesis.

If Day 1 reveals that safe inventory modification requires redesigning a supplier integration, the plan must change.

## 20. The Midweek Surprise

Now introduce reality.

It's Wednesday afternoon.

You've built the backend eligibility check.

The frontend calendar is underway.

Then a support specialist reveals that some direct bookings use promotional inventory rules not represented by the ordinary availability endpoint.

Your original assumption is incomplete.

What do you do?

The weak response is to ignore the issue until testing.

Another weak response is to abandon the entire project immediately.

The stronger response is to identify which bookings are affected and whether the first release can exclude them safely.

Perhaps the feature supports only bookings with a well-defined standard-rate inventory path.

That exclusion should be enforced by the backend and communicated in the UI.

It should also be recorded as a product limitation.

### 20.1 Change the scope deliberately

An unexpected discovery may alter the feasible subset.

That isn't automatically a project failure.

It is part of engineering under uncertainty.

The key is to update the plan, acceptance criteria, and stakeholder expectations before the hidden assumption becomes a production defect.

### 20.2 Avoid silent scope reduction

If you exclude every difficult case without informing the business, the result may solve almost none of the intended support workload.

The trade-off must be visible.

A smaller safe feature is useful only if its remaining scope has meaningful value.

## 21. The Manager Wants More

On Thursday, the manager returns.

"Looks great. Can we also let customers switch hotels?"

The developer knows that changing hotels introduces different availability, prices, inventory ownership, cancellation policies, and perhaps supplier integrations.

Should you say yes?

Not automatically.

Should you simply say no?

Not necessarily.

A useful response explains the additional complexity and offers choices.

You might say that the first release supports eligible date changes within the same property, and hotel transfers require separate discovery and technical planning.

If switching hotels is more commercially valuable than date changes, the business can choose to revise the priority.

But it should make that choice with a realistic understanding of the cost.

### 21.1 Scope negotiation isn't resistance

An experienced engineer helps management understand trade-offs.

They don't treat every new request as an obligation to work unlimited overtime.

They also don't hide behind technical jargon.

The conversation should connect additional work to customer value, schedule, dependencies, and risk.

### 21.2 Make the cost of alternatives visible

One option is to ship the narrow first release on time.

Another is to delay the release and expand functionality.

A third is to build only a booking-change request workflow, with an explicit warning that support still processes the request manually.

These options produce different business outcomes.

The product owner should understand them.

## 22. Release Management Belongs in the Plan

The developer finishes implementation.

Now the feature must reach production safely.

SE215-L11 covered release management as a professional responsibility.

Here we apply it to one concrete product change.

### 22.1 Identify the release artifact

Which source revision contains the feature?

Which image or bundle was built and tested?

Which other changes are included?

### 22.2 Verify the target

Which environment receives the release?

Are the required configuration values and feature flags present?

### 22.3 Confirm compatibility

Can old and new application instances coexist during rollout?

Does the backend API remain compatible with the deployed frontend?

Are database changes safe for the running versions?

### 22.4 Establish recovery

Can the feature be disabled independently?

What happens to reservations already modified?

Can the application roll back without reversing persistent business operations?

### 22.5 Assign release responsibility

In a small company, you may serve as release captain.

In a larger one, coordinate with platform engineers and an existing release process.

The ownership interface changes.

The need for release evidence remains.

## 23. Feature Flags, Gradual Exposure, and Experimentation

A date-change feature is a good candidate for controlled exposure.

The team might deploy it behind a feature flag.

Initially, only internal users can access it.

Then a small percentage of eligible bookings.

If errors and operational signals remain healthy, exposure can increase.

### 23.1 Use stable eligibility

A feature rollout should not randomly enable and disable the action every time the user refreshes the page.

The assignment or eligibility mechanism should be stable according to the product's intended behavior.

### 23.2 Feature flags don't replace backend authorization

A disabled button isn't a security control.

The backend must still validate authorization and business eligibility.

### 23.3 Rollout versus A/B test

The initial rollout may be intended mainly to reduce operational risk.

It isn't automatically a valid randomized experiment measuring support deflection.

A meaningful A/B test needs clear assignment, exposure measurement, a primary outcome, appropriate sample size, and analysis rules.

A two-week implementation schedule doesn't necessarily include enough time to measure a reliable business effect.

The launch is the beginning of observation, not proof that the product hypothesis succeeded.

## 24. Instrumentation: Define What Counts

Suppose the application records an event called `booking_change_success`.

When should it fire?

When the customer clicks Confirm?

When the API receives the request?

When the booking modification commits?

When the confirmation email is sent?

Those are different events.

For a meaningful successful-change metric, the authoritative business commit is the important boundary.

### 24.1 Useful events

The product may distinguish:

Booking change entry viewed.

Eligibility checked.

Date-change flow started.

Valid alternative selected.

Confirmation attempted.

Modification committed.

Modification rejected, with an appropriate category.

The events should be defined consistently.

### 24.2 Identity and duplication

If a confirmation response is retried, the system should not count one successful modification as multiple completed changes.

An operation identity can support deduplication.

### 24.3 Avoid unnecessary personal information

Analytics doesn't need raw payment data or excessive customer details to measure the feature.

Collect only what is necessary for the intended analysis and legitimate operational purposes.

### 24.4 Operational and analytical data differ

The booking database is authoritative for the reservation state.

Analytics events help explain user behavior.

If they disagree, the team should investigate instrumentation and event delivery before trusting the dashboard blindly.

## 25. Measuring the Actual Product Outcome

The manager's objective was reducing support work.

What should we measure?

A reasonable primary operational measure is the number of eligible booking modifications successfully completed through self-service.

But that doesn't tell the whole story.

### 25.1 The denominator matters

Suppose the interface reports fifty successful changes.

Is that good?

It depends.

How many customers were eligible?

How many started?

How many encountered errors?

How many still contacted support afterward?

A successful-change count without context can be misleading.

### 25.2 Support deflection

The company may want to know whether relevant support contacts decreased.

But comparing this week's count with last week's count doesn't automatically establish causality.

Seasonality, booking volume, marketing campaigns, and support policy changes can affect contact rates.

A controlled experiment may provide stronger evidence when appropriate.

At minimum, normalize relevant support contacts against the population of bookings or customers that could generate those contacts.

### 25.3 Guardrails

A feature that reduces support tickets but creates reservation errors is not a success.

Relevant guardrails include:

Unexpected inventory discrepancies.

Payment anomalies.

Modification failures.

Repeated requests.

Customer complaints.

Support escalations.

The primary outcome and safety metrics need to be interpreted together.

## 26. The Feature Is Live. Something Goes Wrong.

Imagine that the controlled rollout begins.

Most eligible customers can modify dates successfully.

But a subset encounters a conflict when two concurrent actions target the same inventory.

The backend rejects the modification safely.

The frontend displays an unclear generic error.

Customers retry repeatedly and then call support.

Technically, the database is protecting its invariant.

The product experience is still poor.

This is an important distinction.

The safe rejection is correct.

The interface needs to explain what happened and allow the customer to select another option.

### 26.1 Observe at the right boundary

The team should distinguish:

Successful modifications.

Expected business rejections.

Unexpected technical failures.

Client-side errors.

Uncertain outcomes.

These shouldn't all appear as one generic failure count.

### 26.2 Respond proportionately

If the feature creates incorrect inventory, disable exposure and investigate immediately.

If it safely rejects unavailable dates but the message is confusing, a targeted UX correction may be appropriate.

Different failures deserve different responses.

### 26.3 Correctness before conversion

The company should not optimize conversion at the expense of booking correctness.

A customer completing an invalid reservation isn't a successful product outcome.

## 27. Documentation and Operational Handoff

Suppose Friday arrives.

The feature is deployed.

You're relieved.

But what happens on Monday when you're unavailable?

Support needs to understand which bookings are eligible.

On-call engineers need to know how to disable the feature.

Product management needs access to relevant measurements.

Developers need to understand the known limitations.

A useful handoff might include:

The supported booking types.

The eligibility rules.

Known excluded cases.

The operation's consistency guarantees.

Relevant monitoring dashboards.

The feature flag.

Common failure reasons.

Recovery and reconciliation procedures.

The owner of follow-up work.

This doesn't require writing a hundred-page operations manual.

It requires making the system understandable to the people who will operate it.

## 28. What Changes with Company Size?

The same two-week assignment looks different in different organizations.

### 28.1 A five-person startup

You might meet the manager, inspect support data, sketch the interface, write frontend and backend code, test it, deploy it, and monitor the release yourself.

You may also maintain the cloud environment.

The work is broad.

The danger is that important decisions have no independent reviewer.

You should seek lightweight validation where the risks are significant.

### 28.2 A fifty-person product company

A product manager may define the objective and eligibility scope.

A designer may work on the journey.

A backend engineer may own the booking operation.

A frontend engineer may implement the interface.

QA may contribute exploratory and automated testing.

A platform engineer may support deployment.

An analyst may evaluate adoption.

You still need to understand how their work connects.

The main challenge becomes coordination and avoiding assumptions between teams.

### 28.3 A large enterprise

The feature may require security review, architectural approval, release management, compliance checks, and coordination with external integration teams.

The implementation may be narrower.

But the number of organizational dependencies can be greater.

A technically small change may take longer because several systems and responsibilities must align.

### 28.4 Specialization doesn't eliminate judgment

An experienced developer shouldn't expect to personally master every adjacent profession.

But they should recognize the questions each profession helps answer.

If a company lacks a designer, you still need to consider usability.

If it lacks QA specialists, you still need to test.

If it lacks a release manager, somebody still owns the release.

If it lacks an analyst, somebody still needs to define what success means.

The responsibilities exist whether or not the organization has a dedicated job title for them.

## 29. The Senior Engineer's Most Valuable Contribution

Think about what changed between Monday and Friday.

On Monday, the manager had an idea.

By Friday, the engineer had transformed it into an explicit product scope, a set of business invariants, an API contract, a customer journey, a tested implementation, a release plan, and a measurement strategy.

Some of that involved code.

Much of it involved identifying uncertainty and making decisions.

The most valuable contribution wasn't knowing how to implement a calendar.

It was preventing the team from spending two weeks building the wrong or unsafe operation.

### 29.1 Technical leadership without authority

You don't need to be the engineering manager to demonstrate leadership.

You can identify dependencies.

You can surface risk.

You can propose smaller deliverable slices.

You can coordinate with QA, product, support, and platform engineers.

You can explain trade-offs.

You can establish verification criteria.

These are practical engineering contributions, not merely management activities.

### 29.2 The limits of ownership

Ownership doesn't mean accepting unlimited responsibility or claiming authority you don't have.

If the business hasn't decided which customer segment matters, you can propose options and ask for a decision.

If a critical database invariant cannot be guaranteed within the schedule, you should state that constraint.

If the company lacks a necessary specialist, you should identify the risk rather than pretending expertise you don't possess.

Professional ownership is making the work and its consequences clear.

It isn't silently absorbing every uncertainty.

## 30. The Two-Week Assignment Revisited

Let's return to the manager's original instruction.

"Add a button, show a calendar, let customers change reservations. Two weeks."

At the beginning, you could have started coding immediately.

You might have produced a beautiful interface.

But you might also have built a feature that changes prices incorrectly, permits unauthorized modifications, creates inventory conflicts, or solves almost none of the support workload.

Instead, you investigated the business problem.

You identified a meaningful subset of reservations.

You defined the safety constraints.

You reused existing domain logic where appropriate.

You built an end-to-end customer journey.

You tested the important failure modes.

You deployed gradually.

You measured whether customers could successfully complete the operation.

And you documented the limitations and next steps.

The first release doesn't solve every booking-modification problem.

That's fine.

It solves a defined problem safely, provides evidence about its value, and creates a foundation for future iterations.

**The goal of an experienced software engineer isn't to implement the biggest possible interpretation of a vague request. It is to deliver a useful, correct, maintainable outcome under real constraints.**

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Vague Request

A manager says, "Customers need to modify reservations. Add a calendar. You have two weeks."

What are the first five questions you would investigate?

## Question 2 — The Missing Requirement

Why is "add a calendar" not a sufficient product requirement?

What is the underlying outcome we should establish?

## Question 3 — Scope Negotiation

The complete feature requires hotel changes, refunds, additional payments, and supplier approvals.

What would you do with a fixed two-week deadline?

## Question 4 — The Availability Race

The frontend shows available dates.

The customer waits thirty seconds before confirming.

Another customer books the final available room.

What must happen when confirmation is submitted?

## Question 5 — Authorization

The frontend hides reservations that don't belong to the authenticated user.

Is this sufficient to secure the booking-modification endpoint?

## Question 6 — The Lost Response

The backend successfully changes the booking, but the HTTP response is lost.

The browser retries.

What design requirement prevents a duplicate operation?

## Question 7 — The Business Metric

The new feature records fifty completed self-service modifications.

Can you conclude it successfully reduced support workload?

What other evidence would you request?

## Question 8 — The Product Manager's Surprise

The manager asks on Thursday to add hotel transfers to the Friday release.

How would you respond constructively?

## Question 9 — Release Versus Exposure

The code is merged and deployed, but the feature flag is disabled.

Which lifecycle stages have occurred?

What remains?

## Question 10 — The Small Company

You're the only developer available.

There is no QA engineer, designer, or release manager.

Does that eliminate the need for testing, UX decisions, and release planning?

## Question 11 — The Large Company

A dedicated release manager coordinates deployment.

Can the developer stop caring about schema compatibility and runtime behavior?

## Question 12 — Senior Engineering Judgment

Describe how you would turn an underspecified business idea into an end-to-end feature while maintaining a credible delivery commitment.

---

# Solutions and Discussion

## Solution 1 — The First Questions

Establish the desired outcome, target users, supported changes, eligibility policies, inventory and payment implications, and technical feasibility.

Prioritize questions that determine scope and correctness.

## Solution 2 — Outcome Versus Implementation

A calendar is a proposed interface.

The underlying objective is enabling eligible customers to complete reservation modifications without support intervention.

The UI is only one component of that workflow.

## Solution 3 — Controlled Scope

Identify a useful subset that can be implemented safely.

For example, same-property, same-room-type, unchanged-price date changes for qualifying direct bookings.

Make exclusions explicit and validate that the subset has meaningful business value.

## Solution 4 — Availability

The backend must revalidate availability at confirmation and preserve inventory invariants through the authoritative modification operation.

The earlier frontend availability response is not a guarantee.

## Solution 5 — Authorization

No.

The backend must verify that the authenticated principal is authorized to modify the specific reservation.

Frontend hiding is a usability mechanism, not an authorization boundary.

## Solution 6 — Idempotency

Use a stable operation identity and appropriate server-side deduplication and state checks.

A repeated request must not perform the business change again.

The response should reflect the authoritative operation outcome.

## Solution 7 — Business Measurement

Fifty completions alone is insufficient.

Consider eligible population, discovery, flow starts, success rate, support-contact changes, technical failures, and guardrail metrics.

Account for other factors affecting support demand.

## Solution 8 — Scope Negotiation

Explain that hotel transfers introduce additional availability, pricing, payment, and supplier dependencies.

Offer alternatives: ship the narrow feature, replan for expanded scope, or postpone the risky functionality.

Seek an informed priority decision.

## Solution 9 — Deployment Versus Exposure

The code has been integrated and deployed.

It hasn't necessarily been exposed to customers.

The team still needs an appropriate rollout and verification process.

## Solution 10 — Missing Specialists

No.

The responsibilities remain even when no dedicated specialist exists.

The developer should address the necessary concerns proportionately and seek review where the risks warrant it.

## Solution 11 — Shared Technical Ownership

No.

A release manager coordinates delivery.

Developers remain responsible for understanding the assumptions, dependencies, and risks of their code and its runtime behavior.

## Solution 12 — End-to-End Ownership

Clarify the problem and desired outcome.

Investigate feasibility.

Define a safe scope.

Establish invariants and acceptance criteria.

Build a complete vertical slice.

Test high-risk paths.

Plan and verify release.

Measure technical and business outcomes.

Communicate limitations and next steps.

Replan explicitly when consequential assumptions change.

---

# The Mental Model Worth Keeping

A vague business request is not a specification.

A specification is not an implementation.

An implementation is not a working product.

A working product is not necessarily a successful business outcome.

The engineer's responsibility is to help connect these stages.

Start with the problem.

Reduce uncertainty.

Define a safe and useful scope.

Preserve business invariants.

Build an end-to-end workflow.

Verify technical correctness.

Release deliberately.

Measure the outcome.

Learn from what actually happens.

**Software engineering is the discipline of turning uncertain intentions into dependable behavior.**

---

# Closing — The Software Engineering Ecosystem

This completes SE215.

Across twelve lectures, we've examined the people, processes, tools, and adjacent disciplines that surround software development.

We've studied how teams divide responsibility, how work is planned, how code is integrated, how repositories and cloud environments are organized, how testing and operations fit into delivery, how data and analytics support decisions, how releases are managed, and how developers collaborate with product and design.

The final lesson brings those subjects together.

An experienced developer doesn't need to be a product manager, designer, QA engineer, platform specialist, data engineer, security engineer, and release manager simultaneously.

But they need enough awareness to recognize when those responsibilities affect their work.

They need to know when they can make a decision independently, when they should collaborate, and when an unresolved risk deserves escalation.

In a small company, that awareness allows one developer to own broad features responsibly.

In a larger organization, it makes collaboration across specialized teams much more effective.

The organizing principle of the course is simple:

**Your job is not merely to produce source code. Your job is to help turn business problems into reliable software that people can actually use.**

*The spoken lecture ends here. The following capstone workshop is intended for independent practice and screen-based revision.*

---

# Optional Practical Workshop — The Two-Week Product Assignment

## Workshop Contract

You are the assigned full-stack developer.

Mercury's manager has given you the following request:

> "Let customers change their booking dates without calling support. We need it in two weeks. Figure out the details."

There is no finished specification.

No Figma design is provided.

The manager is available for one fifteen-minute follow-up meeting.

Support and platform engineers can answer specific questions but cannot dedicate their entire week to the project.

Your objective is to produce a credible, executable engineering plan.

Do not write implementation code immediately.

Work through the problem, scope, contracts, architecture, testing, and release strategy first.

Only then begin a minimal vertical slice.

## Lab A — Convert the Idea into a Product Brief

Create a one-page brief.

It must contain:

**Problem:** What difficulty exists for customers or the business?

**Target user:** Who should be able to use the feature?

**Desired outcome:** What meaningful result should the feature produce?

**First-release scope:** Which cases will be supported?

**Exclusions:** Which cases will deliberately remain unsupported?

**Success metrics:** How will the team evaluate whether the feature worked?

**Risks and assumptions:** Which unknowns could invalidate the plan?

### Challenge

The manager replies:

"Just support all bookings. Why complicate things?"

Write a concise explanation of why eligibility restrictions may be necessary for a safe first release.

---

# Lab B — Investigate Existing Capabilities

Assume Mercury has the following systems:

- Customer portal frontend.
- Booking API.
- PostgreSQL reservation database.
- Inventory service.
- Payment integration.
- Email notification worker.
- Internal support administration tool.
- Third-party supplier connectors.

### Your task

Determine which existing capabilities must be inspected before estimating the feature.

For each system, write:

- What you need to know.
- Why it matters.
- What would change the project scope.
- Which person or team could provide the information.

### Critical decision

The internal support tool can modify direct bookings.

But the supplier connectors require separate approval workflows.

How does this affect your first-release scope?

---

# Lab C — Define Eligibility Rules

Your proposed first release supports:

- Authenticated reservation owners.
- Direct bookings managed by Mercury.
- Same property and room type.
- Same number of nights.
- No change in total price.
- Modifications at least forty-eight hours before check-in.
- Available alternative inventory.
- No already-cancelled or otherwise locked reservations.

These are hypothetical business rules for the exercise, not universal booking policies.

### Your task

Write eligibility tests for the following scenarios.

| Booking | Requested change | Expected decision |
|---|---|---|
| Direct confirmed booking, 10 days before check-in | Same-price alternative dates | Potentially eligible |
| External supplier booking | Same-price alternative dates | Ineligible |
| Direct booking, 12 hours before check-in | Alternative dates | Ineligible |
| Booking owned by another user | Any change | Unauthorized |
| Direct booking with price increase | Alternative dates | Outside MVP |
| Cancelled booking | Alternative dates | Ineligible |
| Direct booking with unavailable inventory | Alternative dates | Reject |

### Additional challenge

What happens if an initially eligible booking becomes ineligible between displaying the calendar and confirming the change?

---

# Lab D — Define the API Contract

Design an API contract for the feature.

You may choose REST endpoints consistent with the existing application architecture.

The contract must support:

1. Checking eligibility.
2. Retrieving alternative dates.
3. Confirming the modification.
4. Reading the authoritative result after an uncertain response.

### Example confirmation request

The following is illustrative JSON, not an implementation of the actual endpoint.

```json id="tg4ebp"
{
  "bookingId": "bk_482",
  "newCheckIn": "2026-11-20",
  "newCheckOut": "2026-11-23",
  "idempotencyKey": "change-op-8f21"
}
```

### Required behavior

Describe how the backend validates ownership, policy, dates, price, and availability.

Explain what happens when the same idempotency key is retried.

Define suitable responses for:

- Successful modification.
- Ineligible booking.
- Unavailable inventory.
- Unauthorized request.
- Duplicate confirmation.
- Uncertain operation outcome.

### Challenge

Should the frontend be trusted to provide the authoritative new price?

Explain why or why not.

---

# Lab E — Design the Inventory Transaction

## Starting state

A reservation occupies one room for three nights.

The customer wants to move the stay to another three-night period.

The new period has limited inventory.

Two customers may request the final available room concurrently.

### Your task

Describe a safe modification operation.

Your explanation must address:

- Authorization.
- Eligibility.
- Current booking version.
- Inventory availability.
- Reserving the new dates.
- Releasing the old dates.
- Updating reservation state.
- Idempotency.
- Failure recovery.
- Audit records.

### Challenge

The new inventory reservation succeeds, but releasing the old inventory fails.

What should the system do?

How does the answer depend on whether both operations share one transaction boundary?

---

# Lab F — Sketch the User Journey

Create a simple flow containing:

- Booking details.
- Eligibility state.
- Change Dates action.
- Calendar.
- Alternative-date selection.
- Confirmation summary.
- Processing state.
- Success.
- Failure and retry handling.

For each screen or state, describe what information the customer needs.

### Required edge cases

Include:

- No available alternatives.
- Booking became ineligible.
- Network interruption.
- Operation outcome uncertain.
- Duplicate confirmation.
- Mobile interaction.
- Accessibility.

### Challenge

The backend commits the change, but the browser loses the response.

What should the interface display?

How can it establish the final state safely?

---

# Lab G — Write the Testing Strategy

Build a test plan for the first release.

Include unit, integration, API, end-to-end, and exploratory tests.

### Required scenarios

- Eligibility policy cutoff.
- Unauthorized booking modification.
- Concurrent inventory conflict.
- Same-price restriction.
- Repeated confirmation.
- Database failure.
- Email delivery failure.
- Booking modified in another session.
- Mobile calendar interaction.
- Successful customer journey.

### Task

Rank the tests according to risk.

Explain which you would prioritize if the project has only two days remaining before the planned release.

### Interviewer challenge

"We have a deadline. Can't we just test the happy path manually?"

Respond with concrete consequences rather than generic testing principles.

---

# Lab H — Write a Two-Week Plan

Create a ten-business-day schedule.

Your plan must distinguish:

- Discovery.
- Scope agreement.
- Backend implementation.
- Frontend implementation.
- Integration testing.
- High-risk verification.
- Release preparation.
- Controlled rollout.
- Monitoring and stabilization.

### Midweek change

On Day 4, you discover that one direct-booking category uses inventory rules your new operation doesn't support.

Update the plan.

Explain whether to exclude that category, redesign the operation, or revise the deadline.

Do not silently ignore the discovery.

---

# Lab I — Prepare the Release

Your implementation passes local tests.

The feature is behind a disabled feature flag.

### Your task

Create a release checklist covering:

- Approved source revision.
- Verified artifact.
- Environment identity.
- Backend and frontend compatibility.
- Database changes.
- Feature-flag configuration.
- Technical smoke tests.
- Business-flow smoke tests.
- Monitoring.
- Rollback or feature-disablement procedures.
- Responsible release owner.

### Challenge

A platform engineer says:

"Kubernetes rollout is green. We're done."

Explain which additional evidence you need before declaring customer-facing success.

---

# Lab J — Design the Analytics

Define the following measurements:

- Eligible bookings exposed to the feature.
- Customers who start the flow.
- Customers who select an alternative.
- Confirmation attempts.
- Successfully committed changes.
- Expected business rejections.
- Unexpected technical failures.
- Relevant support contacts after rollout.

### Your task

For each metric, specify its unit of analysis and authoritative measurement boundary.

Avoid double-counting retries.

Do not assume that one customer clicking Confirm is equivalent to a successful booking modification.

### Product question

The feature completes fifty modifications in its first month.

Does that establish success?

What denominator, historical context, and guardrail evidence would you request?

---

# Lab K — The Vague Manager Returns

It's Thursday afternoon.

Your manager says:

> "This is great. Let's add hotel transfers too. It's basically the same calendar, isn't it?"

Prepare a short response explaining the additional scope.

Your response should be practical and collaborative.

It should identify the new dependencies and offer alternatives.

### Required decision

Choose one:

- Ship the existing narrow feature.
- Delay and expand the scope.
- Replace the release with a different smaller business outcome.

Defend your choice.

---

# Final Studio — The Two-Week Engineering Review

You now have:

- A product brief.
- Eligibility rules.
- A user journey.
- An API contract.
- A backend transaction design.
- A test strategy.
- A delivery plan.
- A release checklist.
- An analytics contract.
- A list of unresolved limitations.

### Interview simulation

The interviewer acts as an engineering manager at a European product company.

They ask you to explain the feature.

You have fifteen minutes to present your approach.

The interviewer then challenges your assumptions.

Potential questions include:

"Why didn't you build all the requested functionality?"

"How do you know the first release is valuable?"

"What happens if your inventory check is stale?"

"Why isn't the frontend enough to enforce eligibility?"

"How do you handle a double click?"

"What happens when the confirmation email fails?"

"How do you know the feature actually reduced support work?"

"What would you change if the company had a dedicated product and platform team?"

"What if the manager refuses to change the deadline?"

### Evaluation rubric

Evaluate the response across these dimensions:

| Competency | Strong performance |
|---|---|
| Problem framing | Separates requested solution from business outcome |
| Scope judgment | Defines a useful, feasible vertical slice |
| Technical correctness | Preserves authorization, inventory, and payment invariants |
| Product design | Includes meaningful states and failure behavior |
| Collaboration | Identifies decisions and appropriate specialist involvement |
| Testing | Prioritizes high-risk scenarios |
| Delivery | Plans a safe, verifiable release |
| Measurement | Defines useful outcomes and guardrails |
| Communication | Explains assumptions, risks, and alternatives clearly |

A strong candidate doesn't need to produce a perfect design during the interview.

They should demonstrate that they know how to investigate uncertainty, make justified decisions, and protect important system behavior.

---

# STOP — End of Independent Workshop

Do not read the following notes until you've attempted the exercises.

The goal is to develop end-to-end engineering judgment rather than recognize a prewritten plan.

---

# Workshop Diagnostic Notes

## The Product Brief

The first priority is establishing the business outcome.

For Mercury, that means enabling customers to complete eligible reservation-date changes without support intervention.

A calendar is a possible interface, not the entire requirement.

## Scope

A narrow same-property, unchanged-price workflow may be feasible if the existing inventory and reservation systems provide safe modification operations.

The two-week schedule is conditional on that capability.

Unsupported supplier or payment scenarios should not be included merely because they sound similar at the UI level.

## Technical Invariants

The backend must enforce authorization and eligibility.

Availability must be validated at confirmation.

Inventory changes must preserve scarce-capacity correctness.

Repeated requests must not duplicate the business operation.

An uncertain response must not be treated automatically as a failed operation.

## User Experience

The interface must represent eligibility, availability, confirmation, processing, success, and failure.

The customer shouldn't receive a misleading success message before the authoritative operation completes.

The UI should help users recover from expected conflicts.

## Testing

Prioritize inventory correctness, authorization, idempotency, and consistency under failure.

Visual and exploratory testing remain important, especially for mobile and accessibility.

High-risk business operations deserve stronger verification than cosmetic changes.

## Delivery

A controlled release should preserve frontend/backend compatibility, verify the intended artifact and environment, and include business-level smoke tests.

Feature flags can limit exposure but do not replace backend enforcement.

## Analytics

Successful modification should correspond to an authoritative committed operation.

Support deflection requires more evidence than raw feature usage.

Relevant denominators and guardrail metrics are necessary.

## Stakeholder Management

The developer should communicate the additional cost of expanded scope and offer options.

Professional ownership doesn't mean unconditionally accepting every request.

It means turning constraints into explicit decisions.

---

# Further Reading

Primary references:

- **Scrum Guide — Product Goal and Increment:** https://scrumguides.org/scrum-guide.html
- **Atlassian — User Stories:** https://www.atlassian.com/agile/project-management/user-stories
- **Atlassian — Acceptance Criteria:** https://www.atlassian.com/work-management/project-management/acceptance-criteria
- **Martin Fowler — Feature Toggles:** https://martinfowler.com/articles/feature-toggles.html
- **W3C — WCAG 2.2:** https://www.w3.org/TR/WCAG22/
- **OWASP — API Security Top 10:** https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- **Stripe — Idempotent Requests:** https://docs.stripe.com/api/idempotent_requests
- **DORA — Software Delivery Performance:** https://dora.dev/
- **Google SRE — Release Engineering:** https://sre.google/sre-book/release-engineering/
- **Statsig — Experimentation:** https://docs.statsig.com/experiments/overview

Related programme chapters:

- SE215-L01 — The People and Teams Behind Software
- SE215-L02 — How Engineering Work Gets Planned and Delivered
- SE215-L03 — Git, Pull Requests, and Collaborative Delivery
- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE215-L07 — Owning End-to-End Testing
- SE215-L09 — Data Engineering for Application Developers
- SE215-L10 — Working With Product, Design, and Analytics
- SE215-L11 — Release Management, Versioning, and Change Ownership
- SE310 — Web APIs, Identity, and Security
- SE320 — Backend Services and Asynchronous Processing
- CS330 — Relational Databases and Transactions
- CS430 — Distributed Systems and Reliable Workflows
- SE440 — Production Reliability and Quality Engineering

---

# Dense Cheatsheet — Interview Glance Card

*The following card is fenced for voice-reader skipping and screen-based revision.*

```text id="y7o1mp"
SE215-L12 — FROM VAGUE IDEA TO SHIPPED PRODUCT
================================================

THE CENTRAL PROBLEM
-------------------
Manager gives:
  Vague idea
  Proposed UI
  Short deadline

Developer must establish:
  Business problem
  Target users
  Safe scope
  Correctness requirements
  Delivery path
  Success evidence

PROBLEM VS SOLUTION
-------------------
"Add a calendar"
is a proposed implementation.

"Reduce support-assisted date changes"
is a business objective.

Ask which customer outcome matters.

FIRST QUESTIONS
---------------
Who needs it?
What must they accomplish?
Which cases are supported?
Which rules apply?
What systems already exist?
What makes it safe?
How will success be measured?

SCOPE
-----
Find smallest USEFUL vertical slice.

Do not deliver disconnected layers
and call the product complete.

Explicitly state exclusions.

TWO-WEEK DELIVERY
-----------------
Discovery and feasibility
Scope/contract
Backend vertical slice
Frontend journey
Integration
High-risk testing
Release preparation
Controlled rollout
Monitoring/handoff

Plan is conditional on assumptions.

BUSINESS INVARIANTS
-------------------
Authorized customer only.
Eligible booking only.
Valid available inventory.
No overbooking.
No unintended payment change.
No partial modification.
Idempotent confirmation.
Auditable state transition.

AVAILABILITY
------------
Frontend result is provisional.

Revalidate at confirmation.

Use authoritative domain logic
and suitable transaction guarantees.

IDEMPOTENCY
-----------
Repeated confirmation should not
perform the logical operation twice.

Account for lost responses and retries.

UX STATES
---------
Eligible
Ineligible
No availability
Selection
Confirmation
Processing
Success
Expected rejection
Technical failure
Uncertain outcome

API DESIGN
----------
Eligibility query
Availability query
Modification command
Authoritative result retrieval

Backend validates everything.

TESTING
-------
Unit:
  policy and eligibility

Integration:
  inventory and state change

API:
  authorization/idempotency

E2E:
  customer journey

Exploratory:
  usability/mobile/accessibility

Prioritize high-consequence risks.

RELEASE
-------
Identify artifact.
Verify target.
Check compatibility.
Enable controlled exposure.
Run business smoke tests.
Monitor guardrails.
Plan recovery.

Deployment != exposure != success.

METRICS
-------
Eligible population
Flow starts
Completed modifications
Failure categories
Support contacts
Inventory/payment guardrails

Attempted action != committed success.

Business improvement needs context.

COLLABORATION
-------------
Small startup:
  developer may own most disciplines

Growing product company:
  share work with PM/design/QA/platform

Enterprise:
  specialized roles, more dependencies

Developer retains responsibility
for understanding relevant contracts.

SCOPE NEGOTIATION
-----------------
Don't silently accept everything.
Don't refuse without alternatives.

Explain:
  Additional behavior
  Dependencies
  Risk
  Time
  Product value

Offer actionable choices.

OWNERSHIP
---------
Own the outcome responsibly.

Do not claim expertise you lack.
Surface consequential unknowns.
Seek review when risks require it.

END-TO-END FLOW
---------------
Problem
  ↓
Discovery
  ↓
Scope
  ↓
Requirements
  ↓
Architecture
  ↓
Implementation
  ↓
Testing
  ↓
Release
  ↓
Measurement
  ↓
Learning

SE215 COURSE COMPLETE
---------------------
People and teams
Planning and delivery
Git and collaboration
Repositories and builds
Cloud service models
DevOps and platform ownership
Testing
SEO
Data engineering
Product/design/analytics
Release management
End-to-end feature ownership

FINAL MENTAL MODEL
------------------
Software engineering turns
uncertain business intentions
into reliable, useful behavior.

Writing code is essential,
but it is only one part of
owning the result.
```
