---
id: CS430-L05
course: CS430
title: "Designing Reliable Business Workflows"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S11]
prev: CS430-L04
next: null
---



# CS430 — Distributed Systems and Reliable Workflows

## Lecture 05: Designing Reliable Business Workflows

*How to complete a hotel booking when the customer disappears, the payment provider times out, the inventory hold expires, and several independently functioning systems disagree about what happened.*

---

# 1. The Customer Who Paid for a Room Nobody Reserved

It's 16:42 on a Friday. A customer in Berlin wants to book a hotel in Stockholm for €450.

Your platform communicates with three systems: PostgreSQL, an external hotel inventory provider, and a payment processor.

The booking flow seems straightforward.

First, ask the hotel provider whether a Deluxe room is available. Then authorize the customer's payment, confirm the booking with the hotel, and capture the money.

Finally, return a successful response.

```text
Customer
   |
   v
Check Availability
   |
   v
Authorize Payment
   |
   v
Confirm Hotel Booking
   |
   v
Capture Payment
   |
   v
Return Confirmation
```

This works beautifully in development.

Then production introduces a rather inconvenient complication: time.

The customer submits the booking request at 16:42:00. The inventory provider confirms that the room is available, and the payment processor successfully authorizes €450.

At 16:42:03, your backend sends the final confirmation request to the hotel supplier.

The supplier processes it and successfully creates the reservation.

Then the response disappears.

Your HTTP client times out.

The application doesn't know whether the hotel booking succeeded. It leaves the reservation pending, hoping to reconcile the result later.

Meanwhile, a scheduled cleanup worker notices that the inventory hold's deadline has passed. It assumes the booking failed and releases the hold.

A second customer books the same last available room.

At 16:44, the original supplier finally returns a booking confirmation through its asynchronous status interface.

Your system now has a confirmed supplier reservation, a released local hold, an authorized payment, and a customer who received an error message.

Several questions immediately arise.

Should you capture the payment? Should you cancel the supplier booking? What if cancellation incurs a penalty? What happens if the customer retries the original booking? And what if the payment authorization expires before you resolve the supplier's status?

The problem isn't one failing function. It's an operation that spans several independently committed systems, each with its own state, deadlines, and failure behavior.

**A reliable business workflow must remember what it intended to accomplish, what it has actually established, and what remains uncertain—even after the original process disappears.**

This is where the previous ten sessions converge.

Transactions protect local invariants. Queues schedule recoverable work. Idempotency controls duplicates. Events communicate state changes. Distributed-systems reasoning tells us not to confuse timeouts with failures.

Today we'll assemble those mechanisms into a coherent booking workflow.

---

# 2. Start With Business Guarantees, Not an Architecture Diagram

Before selecting BullMQ, Redis, AWS Lambda, or a workflow engine, we need to establish what a successful reservation actually means.

Consider these possible promises:

1. The customer has submitted a booking request.
2. The platform has temporarily held suitable inventory.
3. Payment has been authorized.
4. The hotel or supplier has confirmed the reservation.
5. Payment has been captured.
6. Confirmation has been delivered to the customer.

These are not equivalent.

A customer clicking Confirm establishes intent, not a reservation. An inventory hold may expire. A card authorization isn't necessarily a completed capture, and sending an email doesn't prove that the underlying booking is valid.

For our example, we'll design a **prepaid booking workflow**.

The business considers the booking fully successful only when the supplier has confirmed the accommodation and the required payment has been captured. The confirmation email is a subsequent consequence, not part of the booking's atomic success condition.

This is a design assumption, not a universal hotel-industry rule. Some hotels collect payment at check-in, some bookings require deposits, and some suppliers confirm accommodation before the payment process begins.

The distinction matters because different commercial agreements lead to different workflow designs.

### Our central invariants

We want several guarantees:

**Inventory correctness:** The system must not confirm a booking without an appropriate allocation or supplier confirmation.

**Payment correctness:** A single intended payment must not accidentally produce multiple independent charges.

**Workflow durability:** Once accepted, a booking attempt must remain recoverable after an application crash.

**Truthful status:** The API must not report a booking as confirmed when required steps are unresolved.

**Recoverability:** Every nonterminal state must have a defined way to progress, expire safely, compensate, or escalate for investigation.

Notice that none of these guarantees mentions a particular queue library.

The architecture will serve the guarantees, not the other way around.

---

# 3. A Reservation Is a State Machine, Not a Boolean

Many applications begin with a simple database field:

```text
reservation.status = "pending" | "confirmed" | "failed"
```

That's manageable until we encounter a timeout.

The payment provider may have authorized the money, but the application doesn't know whether the supplier has confirmed the room.

Should the reservation be pending or failed?

What if inventory is held, payment authorization is confirmed, and supplier confirmation is still underway?

A single broad status may conceal information needed for recovery.

A better approach is to model the important state dimensions separately.

For example:

```text
BOOKING
  REQUESTED
  HOLDING_INVENTORY
  INVENTORY_HELD
  AWAITING_PAYMENT_AUTH
  AWAITING_SUPPLIER_CONFIRMATION
  AWAITING_CAPTURE
  CONFIRMED
  COMPENSATING
  FAILED
  MANUAL_REVIEW

PAYMENT
  NOT_STARTED
  AUTHORIZING
  AUTHORIZED
  CAPTURING
  CAPTURED
  CANCELLED
  FAILED
  UNKNOWN

INVENTORY
  NOT_HELD
  HOLDING
  HELD
  CONFIRMING
  CONFIRMED
  RELEASING
  RELEASED
  UNKNOWN
```

These states are illustrative. A real implementation should avoid unnecessary proliferation of nearly identical states, but it must preserve distinctions that affect recovery.

Why maintain separate dimensions?

Because payment success doesn't imply booking success. Inventory availability doesn't imply payment success, and a locally expired hold doesn't necessarily mean an external supplier has released the room.

A single `FAILED` status cannot faithfully represent every possible combination.

### Durable transitions

Instead of allowing arbitrary assignments, each state transition should have conditions.

For example:

```text
AWAITING_CAPTURE
       |
       +-- Capture confirmed --> CONFIRMED
       |
       +-- Capture rejected --> COMPENSATING
       |
       +-- Capture uncertain --> Remain unresolved
```

The workflow should also reject stale commands.

If a reservation has already been cancelled, a delayed `PaymentAuthorized` event shouldn't automatically reactivate it.

This is where optimistic versioning and conditional database updates from CS330-L03 become useful.

```sql
UPDATE booking_workflows
SET
  status = 'AWAITING_CAPTURE',
  version = version + 1
WHERE id = $1
  AND status = 'AWAITING_SUPPLIER_CONFIRMATION'
  AND version = $2
RETURNING id;
```

A successful update establishes that the transition applied to the expected current state.

Zero updated rows means the transition's assumptions are no longer true.

The caller must reload and reevaluate rather than blindly force the next state.

---

# 4. A Practical Booking Protocol

Let's design the normal success path.

We'll assume the hotel supplier supports temporary inventory holds and stable external operation identifiers. We'll also assume the chosen payment method supports separate authorization and capture.

Those capabilities must be verified for an actual provider integration.

Our simplified sequence is:

```text
Customer submits booking
           |
           v
Create durable booking intent
           |
           v
Request inventory hold
           |
           v
Inventory held
           |
           v
Authorize payment
           |
           v
Payment authorized
           |
           v
Confirm supplier reservation
           |
           v
Supplier confirmed
           |
           v
Capture payment
           |
           v
Payment captured
           |
           v
Mark booking confirmed
           |
           v
Send confirmation asynchronously
```

At first glance, we've simply expanded the original flow.

The important difference is that each step now has durable state, a stable operation identity, and a recovery policy.

We aren't relying on one Node.js process remaining alive throughout the sequence.

### Step A — Create the booking intent

The customer submits:

```http
POST /api/bookings
Idempotency-Key: booking-attempt-92831

{
  "hotelId": "hotel-482",
  "roomTypeId": "deluxe",
  "checkIn": "2026-11-12",
  "checkOut": "2026-11-15"
}
```

The backend validates the request, calculates or retrieves an authoritative quote, and creates a durable booking attempt.

It assigns an internal `bookingId` and associates the request's idempotency key with that attempt.

If the customer retries with the same key and equivalent parameters, the application retrieves the existing attempt rather than creating an unrelated booking.

A different payload using the same key should be rejected or handled according to a deliberately defined conflict policy.

### Step B — Hold inventory

The workflow requests temporary inventory allocation.

For an internally managed inventory database, this might be a transaction that atomically reserves capacity for each night.

For an external supplier, it might be an API call that creates a supplier-side hold with an expiration deadline.

Either way, the application records the hold identifier and deadline.

### Step C — Authorize payment

The platform obtains payment authorization for the agreed amount.

For eligible Stripe PaymentIntent integrations, manual capture uses `capture_method=manual`. After authorization, a PaymentIntent can enter `requires_capture`, meaning the funds have been authorized but not yet captured.

The authorization has an expiration, which depends on the payment method, network rules, and transaction characteristics. It is not indefinite.

An authorization is therefore another time-limited resource that the workflow must manage.

### Step D — Confirm the supplier booking

With inventory held and payment authorized, the application requests definitive supplier confirmation.

Only after the supplier confirms should the workflow advance toward capture under our selected prepaid model.

If supplier confirmation fails definitively, the system should release the hold and cancel the authorization where supported.

If the supplier's outcome is unknown, the workflow must reconcile it rather than assuming failure.

### Step E — Capture payment

After supplier confirmation, the platform captures the authorized amount.

This too is a remote operation and can return an ambiguous timeout.

The workflow must retain its stable provider payment identifier and reconcile the actual capture state before attempting anything that might create a second financial effect.

### Step F — Finalize the booking

Once capture is confirmed, the application can mark the booking as fully confirmed and record durable notification intent.

The email worker may fail later without invalidating the confirmed booking.

The normal path sounds straightforward. The engineering challenge is making every interruption point recoverable.

---

# 5. The Database Is the Workflow's Memory

Let's design a minimal persistence model.

```sql
CREATE TABLE booking_workflows (
  id TEXT PRIMARY KEY,

  customer_id TEXT NOT NULL,
  request_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,

  status TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0,

  amount_minor BIGINT NOT NULL,
  currency CHAR(3) NOT NULL,

  supplier_hold_id TEXT,
  supplier_booking_id TEXT,
  hold_expires_at TIMESTAMPTZ,

  payment_operation_id TEXT NOT NULL,
  provider_payment_id TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (customer_id, request_key),
  UNIQUE (payment_operation_id)
);
```

The simplified schema omits foreign keys, detailed constraints, and associated child tables. It illustrates the information the workflow must preserve.

For a production system, I'd typically separate the booking, inventory allocation, payment operation, and workflow execution records rather than place every detail in one table.

But the central idea remains: the application must be able to reconstruct the workflow's position without relying on the memory of a process that may no longer exist.

### Separate payment operations

A more complete payment table might look like:

```sql
CREATE TABLE payment_operations (
  id TEXT PRIMARY KEY,
  booking_id TEXT NOT NULL,

  operation_type TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_reference TEXT,

  status TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,

  amount_minor BIGINT NOT NULL,
  currency CHAR(3) NOT NULL,

  last_attempt_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,

  UNIQUE (provider, idempotency_key)
);
```

Why use explicit operation records?

Because one booking may involve authorization, capture, cancellation, refund, and perhaps multiple failed attempts over its lifetime.

Those aren't merely status changes on one payment field.

They're distinct financial operations with independent identities and outcomes.

For example, authorization and capture should not accidentally reuse the same operation identifier merely because they belong to one booking.

The idempotency key identifies a particular intended provider operation.

### An important distinction

A workflow's durable state is not the same thing as its execution schedule.

PostgreSQL can record:

```text
Booking R-10842
Status: AWAITING_SUPPLIER_CONFIRMATION
Next action: reconcile supplier confirmation
```

BullMQ can schedule the actual reconciliation attempt.

If Redis loses the scheduled job, a recovery process can inspect PostgreSQL and recreate the work.

This gives us a useful separation:

**The database records what must happen. The queue determines when an attempt runs.**

For important business workflows, I generally prefer that arrangement over treating queue-job existence as the sole representation of workflow state.

---

# 6. The Hold Expiration Race

Now let's revisit the failure from our opening incident.

A temporary inventory hold has an expiration deadline.

At 16:45, a cleanup worker decides the hold is expired.

Simultaneously, the payment and confirmation workflow is advancing.

The cleanup worker reads:

```text
hold_expires_at = 16:45
status = HELD
```

It concludes that the hold should be released.

But another worker may have just started confirming the reservation with the supplier.

If both proceed independently, one can release the hold while the other confirms the booking.

We need a transition protocol.

### Claim the state before acting

One approach is to require the expiration worker to atomically move the local hold into a releasing state.

```sql
UPDATE inventory_holds
SET
  status = 'RELEASING',
  version = version + 1
WHERE id = $1
  AND status = 'HELD'
  AND expires_at <= now()
RETURNING id, supplier_hold_id;
```

Meanwhile, the booking worker must atomically claim its own right to begin confirmation:

```sql
UPDATE inventory_holds
SET
  status = 'CONFIRMING',
  version = version + 1
WHERE id = $1
  AND status = 'HELD'
  AND expires_at > now()
RETURNING id, supplier_hold_id;
```

Only one of these transitions can succeed against the same current row under appropriate database concurrency control.

This prevents two local workers from simultaneously treating the hold as both releasable and confirmable.

But there's a crucial limitation.

The supplier has its own clock and authoritative state.

Even if our database says the hold hasn't expired, the supplier may reject confirmation because its deadline has passed.

Similarly, a supplier confirmation request may have succeeded just as the local operation encountered a timeout.

Therefore, state transitions involving the supplier still need reconciliation.

The local atomic update establishes who may attempt the operation. It doesn't automatically guarantee the external outcome.

### Safety margins and deadlines

A robust system shouldn't normally begin confirmation one millisecond before a supplier hold expires.

It should reserve enough time for expected network latency, retries, and provider processing.

The exact margin depends on the supplier's documented hold behavior and the product's tolerance for uncertain outcomes.

And once confirmation is underway, the expiration worker must not blindly treat the original hold deadline as proof that confirmation failed.

The workflow must distinguish an expired, uncommitted hold from an external confirmation whose result remains unknown.

---

# 7. Payment Authorization Is Not Payment Capture

This distinction deserves particular attention because financial APIs often expose several states that developers mistakenly collapse into a single `paid` boolean.

**Authorization** generally means the payment method has approved an amount for potential capture, subject to network and provider rules.

**Capture** requests that the authorized funds be taken for settlement.

**Settlement** and payout to the merchant may happen later according to the provider's processes.

For supported Stripe payment methods, a manually captured PaymentIntent can enter:

```text
requires_capture
```

after successful authorization.

Capturing it successfully advances the payment toward the completed state. The exact lifecycle depends on payment method and integration.

Now imagine the supplier rejects the booking after authorization.

The preferred compensation may be cancelling the authorization rather than capturing and later refunding it.

Why?

Because capture and refund create additional financial events and potentially more customer confusion.

However, authorizations also expire. The workflow must capture within the relevant validity period, or reauthorize appropriately if the business requires a longer delay.

This matters particularly for hotel bookings scheduled months in advance. Holding a card authorization from October until a stay in February generally isn't a valid assumption for ordinary online card payments.

The payment model must match when the customer is actually charged.

### Three independent questions

When examining payment state, ask:

- Was the payment method authorized?
- Were funds captured?
- Has the provider definitively reported the current outcome?

These questions can have different answers.

And if the provider times out during capture, don't simply create another payment attempt with a new identity.

Retrieve or reconcile the existing provider operation using the stable reference.

The provider's idempotency contract matters. In Stripe API v1, for example, idempotency records have finite retention and can replay stored error responses; API v2 has different recovery semantics.

A production payment adapter should encode those specifics rather than pretending every provider offers identical guarantees.

---

# 8. Webhooks: The Provider Calls You Back

So far, we've mostly assumed that our backend initiates requests to external systems.

Payment providers also communicate asynchronously.

For example, Stripe may deliver a payment event to a configured webhook endpoint.

This is valuable when payment outcomes occur after the original HTTP request ends, or when a provider's state changes independently.

But webhooks introduce three important complications:

**They can be duplicated. They can arrive out of order. They can arrive while the application is recovering from another failure.**

Suppose the payment provider generates:

```text
Payment authorized
Payment captured
```

The corresponding webhook deliveries might arrive in the reverse order.

Or the capture event might arrive twice because the provider didn't receive an acknowledgment of the first delivery.

The handler must not assume that each business transition generates exactly one event delivered in chronological order.

### A safe webhook ingress pattern

A good design separates receiving the event from performing expensive business processing.

```text
Provider Webhook
       |
       v
Verify Signature
       |
       v
Validate Event Identity
       |
       v
Persist to Inbox
       |
       v
Return 2xx
       |
       v
Background Processor
       |
       v
Reconcile / Advance Workflow
```

The signature verification must use the provider's documented mechanism.

For Stripe, that includes the raw request body, the `Stripe-Signature` header, and the endpoint signing secret.

Parsing and reserializing JSON before verification can invalidate the signature.

### The durable inbox

A webhook inbox table might contain:

```sql
CREATE TABLE provider_webhook_inbox (
  provider TEXT NOT NULL,
  event_id TEXT NOT NULL,

  event_type TEXT NOT NULL,
  provider_object_id TEXT NOT NULL,
  payload JSONB NOT NULL,

  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ,

  PRIMARY KEY (provider, event_id)
);
```

When a verified event arrives, the endpoint attempts to insert it.

```sql
INSERT INTO provider_webhook_inbox (
  provider,
  event_id,
  event_type,
  provider_object_id,
  payload
)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT DO NOTHING;
```

Only after the inbox transaction commits should the handler acknowledge durable acceptance.

If the database is unavailable and the event cannot be recorded, returning success could cause the provider to stop retrying even though we lost the event.

The endpoint should generally fail appropriately so the provider can retry under its delivery policy.

After durable acceptance, background processing can handle the event.

A duplicate delivery of the same event ID won't create another inbox record.

### Event deduplication isn't business deduplication

Some providers can generate distinct event objects describing the same underlying transition.

Stripe specifically documents cases where deduplication may also require considering the provider object ID together with the event type.

More importantly, the booking processor should not issue another financial operation merely because it receives another notification.

The inbox deduplicates transport-level events.

The workflow's state machine and payment-operation identities protect business effects.

These are complementary guarantees.

---

# 9. A Webhook Should Be Evidence, Not an Unconditional Command

Imagine a booking has already been cancelled and refunded.

Then a delayed payment-success event arrives.

A naive handler executes:

```typescript
if (event.type === "payment_intent.succeeded") {
  await reservationRepository.update(reservationId, {
    status: "confirmed"
  });
}
```

That's dangerous.

The event may be authentic and historically correct, but the current booking state may have changed since it was generated.

An event saying that payment succeeded doesn't mean the booking should now be confirmed.

The handler needs to interpret the event within the current workflow.

A safer conceptual approach:

```typescript
async function processPaymentEvent(
  event: VerifiedPaymentEvent
) {
  const operation = await findPaymentOperation(
    event.providerObjectId
  );

  if (!operation) {
    await recordUnmatchedEvent(event);
    return;
  }

  await reconcilePaymentOperation(operation.id);
}
```

The reconciliation function retrieves or interprets authoritative provider state, then applies an allowed local transition.

For provider event formats containing current snapshots, the exact procedure may differ. But the principle is that an event should not blindly overwrite newer business state.

### The late-success problem

Suppose we cancelled a booking after payment authorization remained unresolved.

Later, reconciliation proves that the payment was captured.

We should not automatically reactivate the booking.

Perhaps the inventory has already been released or allocated elsewhere.

The correct response may be to initiate a refund and mark the booking for compensation.

This means the workflow must distinguish:

```text
Payment captured + Booking confirmed
```

from:

```text
Payment captured + Booking cancelled
```

The first is successful completion.

The second is a financial inconsistency requiring corrective action.

Both may arise from legitimate sequences of events.

---

# 10. Reconciliation: Reliability Without Trusting Notifications

Suppose Stripe sends a webhook confirming payment capture.

Your webhook endpoint is unavailable for several hours.

The provider retries according to its policy, but delivery still fails.

Eventually, the provider may stop retrying.

What happens to your booking?

If your entire workflow depends on receiving that one webhook, the payment may remain permanently unresolved in your database.

That's not acceptable for a serious financial system.

A reliable workflow needs a second recovery mechanism: **reconciliation**.

Reconciliation compares local state with the authoritative state of external systems.

For example, a scheduled worker retrieves payment operations that have remained unresolved beyond an expected interval.

```sql
SELECT *
FROM payment_operations
WHERE status IN ('AUTHORIZING', 'CAPTURING', 'UNKNOWN')
  AND updated_at < now() - INTERVAL '2 minutes';
```

The two-minute threshold is illustrative. Actual thresholds depend on provider behavior and the operation's expected duration.

For each operation, the worker queries the provider using its stable reference.

Possible results:

```text
LOCAL UNKNOWN
      |
      +-- Provider says captured --> Record captured
      |
      +-- Provider says declined --> Record failed
      |
      +-- Provider says pending --> Schedule later check
      |
      +-- Provider unavailable ---> Keep unresolved
```

A provider lookup that times out doesn't establish that the payment failed.

It merely means the reconciliation attempt couldn't resolve the state.

### Reconciliation isn't just a fallback

In mature systems, reconciliation can become a first-class operational capability.

You may compare:

- Local booking records against supplier reservations.
- Authorized payments against pending bookings.
- Captured payments against confirmed bookings.
- Refund requests against provider refund records.
- Internal ledger entries against provider settlement reports.

These comparisons can detect inconsistencies even when every individual service reports normal operation.

For example, an event-handling bug may silently fail to update one payment record. Reconciliation can detect that the provider captured money while the local operation remains unresolved.

A good system doesn't merely retry failed requests.

It periodically asks whether its recorded business state still agrees with external reality.

---

# 11. Compensation: Correcting the World After Partial Success

Let's examine a few failure cases.

### Case A — Inventory held, payment declined

The customer has a temporary room hold, but the card authorization is definitively rejected.

The workflow should release the hold and mark the booking unsuccessful.

If releasing the hold fails temporarily, the workflow remains in a compensating state until the release is confirmed, the hold expires according to the supplier's authoritative rules, or another recovery action is taken.

### Case B — Payment authorized, supplier booking rejected

The customer has authorized funds, but the supplier definitively rejects confirmation.

We should cancel the payment authorization where supported, not capture it.

The booking can become terminally failed only once the necessary compensation obligations are resolved or explicitly tracked.

### Case C — Supplier confirmed, capture failed

This is more serious.

The hotel expects the customer, but the payment hasn't been captured.

Possible responses depend on the supplier contract and commercial policy.

The platform might retry capture if safe, request another payment method, or cancel the supplier reservation.

Cancellation may carry fees or may no longer be possible.

This case cannot be solved through a generic rollback command.

### Case D — Capture succeeded, booking confirmation uncertain

This is among the most dangerous situations.

Money has been captured, but the platform cannot establish whether the supplier confirmed accommodation.

The workflow must reconcile supplier state before deciding whether to finalize or compensate.

If the supplier confirms, proceed.

If the supplier definitively rejects the reservation, initiate refund handling.

If the supplier remains unreachable, preserve the unresolved state and escalate according to an operational policy.

### Compensation can itself fail

Suppose a refund request times out.

Did the refund succeed?

We're back to the uncertainty problem from CS430-L01.

The compensation operation needs its own durable identity and reconciliation mechanism.

This is why reliable sagas are not simply sequences of `try/catch` blocks.

A compensation is another business operation with its own lifecycle.

---

# 12. The Orchestrator: Making Progress Without Trusting Process Memory

We need a component responsible for advancing the booking workflow.

Let's call it the Booking Orchestrator.

It doesn't necessarily need to be a separate microservice.

For a modular Node.js backend, it can be an application-level component backed by PostgreSQL.

Its central function is to inspect durable state and determine the next valid action.

Conceptually:

```typescript
async function advanceBooking(bookingId: string) {
  const booking = await repository.getForProcessing(
    bookingId
  );

  switch (booking.status) {
    case "REQUESTED":
      return initiateInventoryHold(booking);

    case "INVENTORY_HELD":
      return initiatePaymentAuthorization(booking);

    case "AWAITING_SUPPLIER_CONFIRMATION":
      return reconcileOrConfirmSupplier(booking);

    case "AWAITING_CAPTURE":
      return reconcileOrCapturePayment(booking);

    case "COMPENSATING":
      return continueCompensation(booking);

    default:
      return;
  }
}
```

This is an architectural sketch rather than a complete implementation.

A real orchestrator also needs worker claiming, version checks, deadlines, provider operation identities, recovery from partial attempts, and durable scheduling.

But the basic structure is useful.

The worker doesn't assume it owns the entire workflow forever. It performs one recoverable step and records progress.

Another worker can continue later.

### The claim-execute-record pattern

For each external action, a robust sequence often resembles:

1. Atomically claim the next permitted transition.
2. Record the intended external operation and its stable ID.
3. Commit the local state.
4. Execute the external request.
5. Record the observed outcome in a new transaction.
6. Schedule reconciliation if the outcome is uncertain.

The external call should generally not be performed while holding an unnecessary long-running PostgreSQL transaction open.

However, step 4 may succeed immediately before the worker crashes.

Therefore, step 5 might never happen.

The stable operation ID and reconciliation policy exist precisely to recover that case.

### What about two orchestrator workers?

Suppose BullMQ delivers the same job twice.

Both workers try to advance Booking R-10842.

They must not independently initiate two supplier bookings.

A database version check or lease-based claim can coordinate which worker is authorized to initiate the next action.

But a time-limited lease by itself is insufficient if an old worker resumes after the lease expires.

The external provider must recognize repeated requests through stable operation references, or the workflow needs another appropriate enforcement mechanism.

The correct design must tolerate stale workers, not merely normal concurrent execution.

---

# 13. The Customer Closes the Browser

This is a surprisingly revealing scenario.

Suppose the customer submits a booking and immediately closes the tab.

Should the booking stop?

Not necessarily.

If the server has durably accepted the booking attempt, the workflow should continue independently of the browser connection.

The customer's disappearance doesn't cancel a payment request already sent to the provider.

Nor does an HTTP connection closing automatically reverse an inventory hold.

A reasonable API might return:

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "bookingId": "R-10842",
  "status": "processing"
}
```

The frontend can subsequently retrieve:

```http
GET /api/bookings/R-10842
```

And receive:

```json
{
  "bookingId": "R-10842",
  "status": "awaiting_payment_confirmation"
}
```

If the customer reconnects from another device, they should be able to recover the same booking attempt.

If the client retries the original creation request with the same idempotency key, the server should return the existing operation rather than create another booking.

### Cancellation is a business operation

What if the customer clicks Cancel while the booking is processing?

That request cannot simply terminate a worker thread and assume the external world returns to its previous state.

Cancellation must follow the workflow's current durable state.

Before supplier confirmation, cancellation might release a temporary hold and cancel payment authorization.

After supplier confirmation and capture, cancellation may require the hotel's contractual cancellation policy and potentially a refund.

During an uncertain supplier operation, cancellation may need to enter a pending state until the supplier outcome is known.

The distinction is important:

**Disconnecting, cancelling a request, and cancelling a booking are three different operations.**

The user interface should reflect that rather than offering misleading guarantees.

---

# 14. Time Limits: Inventory Holds, Card Authorizations, and Workflow Deadlines

A booking workflow contains several clocks.

The supplier inventory hold may expire in ten minutes.

The customer may need to complete payment authentication within a shorter period.

The card authorization may expire after a provider- and network-specific interval.

The API request itself may have a four-second timeout.

And a reconciliation worker may run every few minutes.

These clocks govern different things.

A timeout on one doesn't automatically invalidate the others.

### Deadline-aware orchestration

Instead of recording only a generic `expires_at`, useful workflow state might include:

```text
booking_created_at
supplier_hold_expires_at
payment_authorization_expires_at
next_reconciliation_at
workflow_deadline
```

These values influence which actions remain safe.

For example, suppose supplier confirmation typically takes several seconds, but the inventory hold expires in one second.

It may be unwise to start a new confirmation attempt.

Alternatively, if confirmation is already in progress, the system may need to reconcile rather than immediately release inventory.

### Don't trust local wall-clock time as global authority

The supplier determines whether its hold remains valid.

The payment provider determines whether its authorization can still be captured.

Our timestamps are useful scheduling information, but the actual remote operation's validity depends on the provider's rules and state.

This is a practical consequence of the clock and lease problems from CS430-L01.

For deadlines and cleanup, use conservative margins and authoritative status checks where required.

---

# 15. Reconciliation and Observability as Operational Requirements

A workflow can be technically sophisticated and still operationally unusable.

Imagine customer support receives:

> I paid €450, but I never received a booking confirmation.

What should the engineer investigate?

Without explicit workflow records, they might search through disconnected logs from the API, workers, Redis, PostgreSQL, payment provider, and supplier integration.

With a durable workflow, the system can expose something like:

```text
Booking: R-10842
Customer: C-928

16:42:00  Booking requested
16:42:01  Inventory hold confirmed
16:42:02  Payment authorization succeeded
16:42:03  Supplier confirmation submitted
16:42:06  Supplier request timed out
16:42:06  Workflow awaiting reconciliation
16:43:00  Supplier lookup failed
16:44:00  Supplier confirmation discovered
16:44:02  Payment capture initiated
16:44:03  Capture confirmed
16:44:03  Booking confirmed
16:44:04  Notification queued
```

This is much more useful than six unrelated log lines saying `request failed`.

A strong workflow records meaningful transitions with identifiers that allow the corresponding external operations to be found.

### Important operational metrics

For this booking system, I'd monitor unresolved bookings by state and age, inventory holds nearing expiration, payment authorizations approaching capture deadlines, ambiguous provider outcomes, failed compensation attempts, and reconciliation success rates.

A particularly useful metric is the age of the oldest unresolved booking.

A thousand bookings pending for two seconds may be entirely normal.

One booking pending for six hours with captured payment and uncertain supplier status deserves immediate attention.

Not all failures should trigger the same urgency.

A failed confirmation email is inconvenient.

A captured payment with no valid accommodation is a much more serious business incident.

Monitoring priorities should reflect that distinction.

---

# 16. Practical Lab: A Workflow That Survives Duplicate and Late Events

Let's construct a compact PostgreSQL experiment.

The goal is to reproduce a workflow where an expired booking receives a late payment-success event, and demonstrate why that event must not simply reactivate the booking.

We'll use a single database for convenience and simulate the payment provider through inserted events.

### Step 1 — Create the tables

```sql
DROP TABLE IF EXISTS workflow_events;
DROP TABLE IF EXISTS workflow_actions;
DROP TABLE IF EXISTS booking_workflows;

CREATE TABLE booking_workflows (
  id TEXT PRIMARY KEY,

  status TEXT NOT NULL,
  inventory_status TEXT NOT NULL,
  payment_status TEXT NOT NULL,

  version INTEGER NOT NULL DEFAULT 0,

  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workflow_events (
  provider TEXT NOT NULL,
  event_id TEXT NOT NULL,
  booking_id TEXT NOT NULL,
  event_type TEXT NOT NULL,

  PRIMARY KEY (provider, event_id)
);

CREATE TABLE workflow_actions (
  id TEXT PRIMARY KEY,
  booking_id TEXT NOT NULL,
  action_type TEXT NOT NULL,
  status TEXT NOT NULL,

  UNIQUE (booking_id, action_type)
);
```

The `workflow_actions` table records durable follow-up obligations.

For the lab, assume at most one refund action is necessary per booking. A real system supporting several independent refunds would need a more precise operation identity.

### Step 2 — Create a pending booking

```sql
INSERT INTO booking_workflows (
  id,
  status,
  inventory_status,
  payment_status
)
VALUES (
  'R-101',
  'AWAITING_PAYMENT',
  'HELD',
  'AUTHORIZING'
);
```

Now imagine the workflow deadline passes, and the platform determines that no new booking confirmation should be initiated.

```sql
UPDATE booking_workflows
SET
  status = 'COMPENSATING',
  inventory_status = 'RELEASING',
  version = version + 1
WHERE id = 'R-101'
  AND status = 'AWAITING_PAYMENT';
```

The booking has entered compensation.

Suppose inventory release eventually succeeds:

```sql
UPDATE booking_workflows
SET
  inventory_status = 'RELEASED',
  version = version + 1
WHERE id = 'R-101'
  AND status = 'COMPENSATING'
  AND inventory_status = 'RELEASING';
```

Notice that the payment remains unresolved.

The workflow should not pretend everything is finished.

### Step 3 — A late payment-captured event arrives

Now simulate a provider event:

```text
eventId = evt-payment-101
booking = R-101
payment captured = true
```

First, the event is inserted into the inbox:

```sql
INSERT INTO workflow_events (
  provider,
  event_id,
  booking_id,
  event_type
)
VALUES (
  'payment-provider',
  'evt-payment-101',
  'R-101',
  'PaymentCaptured'
)
ON CONFLICT DO NOTHING;
```

The event is authentic within our simulated scenario.

But the booking is already compensating, and its inventory has been released.

Should this event confirm the booking?

Absolutely not.

### Step 4 — Process it according to current workflow state

We can record the payment fact and create a refund obligation within one database transaction:

```sql
BEGIN;

SELECT status, inventory_status, payment_status
FROM booking_workflows
WHERE id = 'R-101'
FOR UPDATE;
```

The application checks that the event refers to the correct provider payment operation and that its authoritative outcome is captured. Our lab assumes those checks have already succeeded.

Then:

```sql
UPDATE booking_workflows
SET
  payment_status = 'CAPTURED',
  version = version + 1
WHERE id = 'R-101'
  AND status = 'COMPENSATING'
  AND payment_status <> 'CAPTURED';
```

And:

```sql
INSERT INTO workflow_actions (
  id,
  booking_id,
  action_type,
  status
)
VALUES (
  'refund-R-101',
  'R-101',
  'REFUND_PAYMENT',
  'PENDING'
)
ON CONFLICT (booking_id, action_type)
DO NOTHING;

COMMIT;
```

The booking remains compensating.

Payment is now recorded as captured.

And the system has a durable refund obligation.

The refund worker can later issue or reconcile the refund through the provider, using its own stable operation identity.

### Step 5 — Deliver the webhook again

Run the same event insertion and processing operations again.

The inbox's composite primary key prevents a duplicate event record.

The refund action's unique constraint prevents another refund obligation for the same booking and action type.

The workflow doesn't become confirmed merely because a duplicate or delayed payment event arrived.

This demonstrates the relationship between transport deduplication and business state enforcement.

### Step 6 — Think through the missing cases

Our lab is intentionally incomplete. It doesn't prove supplier cancellation, execute actual provider refunds, or handle all possible payment transitions.

Consider how you'd extend it to handle:

- A payment authorization that succeeded but wasn't captured.
- A supplier confirmation that arrives after local inventory release.
- A refund request whose response is lost.
- Two workers processing different provider events concurrently.
- A customer cancellation submitted while capture is underway.

The answer should not be a growing collection of arbitrary status assignments.

You want explicit business transitions, durable operation records, and a reconciliation path for every uncertain external effect.

---

# 17. Engineering and Interview Challenges

### Question 1 — Payment succeeded, booking failed

A hotel supplier definitively rejects a booking after your payment provider has captured the customer's money.

What should the system do? Is marking the reservation `failed` sufficient?

### Question 2 — Duplicate webhook delivery

A payment provider sends the same payment-success webhook three times.

Your webhook endpoint successfully acknowledges all deliveries.

How do you ensure the business operation isn't applied three times?

### Question 3 — The dangerous expired hold

A cleanup worker sees that an inventory hold deadline has passed, while another worker is attempting supplier confirmation.

What coordination mechanism would you use, and why isn't the timestamp alone sufficient?

### Question 4 — Browser disconnected

The customer closes the browser immediately after submitting a booking. Payment authorization and supplier confirmation are still in progress.

Should the backend cancel the booking automatically?

### Question 5 — The invisible capture

A payment capture request times out, but the provider later reports that the money was captured.

Your application already started releasing the inventory hold.

How should the workflow respond?

### Question 6 — The missing webhook

A payment provider successfully captures funds, but its webhook never reaches your application.

What prevents the workflow from remaining unresolved forever?

---

# 18. Solutions and Discussion

### 1. Create a durable compensation workflow

The supplier rejection is definitive, but the payment capture already occurred.

The application should preserve both facts, initiate the appropriate refund operation, and track it to a resolved outcome.

Marking the reservation `failed` doesn't refund money or establish that the customer is financially whole.

The compensation itself may fail or return an uncertain result, requiring idempotency and reconciliation.

### 2. Deduplicate events and enforce business idempotency

The webhook inbox should reject duplicate event IDs.

However, the workflow must also identify the actual payment operation and prevent duplicate business transitions.

For local database effects, unique constraints and atomic transactions can help.

For provider-side effects, stable operation identifiers and provider-supported idempotency are necessary where available.

Event deduplication and business idempotency solve related but distinct problems.

### 3. Coordinate through conditional state transitions

Both workers must compete through an authoritative state transition rather than independently acting on the hold.

A transaction or conditional update can ensure that only one local operation claims the hold for confirmation or release.

But the supplier controls the external hold and confirmation state, so an ambiguous remote operation still requires reconciliation.

The local deadline alone doesn't prove that the supplier has rejected or cancelled the booking.

### 4. Disconnecting isn't cancellation

If the booking request has been durably accepted, the workflow should normally continue independently of the browser connection.

The customer should be able to retrieve the existing booking attempt later.

If the user explicitly requests cancellation, that should become a business operation whose behavior depends on the current workflow state.

Network cancellation and booking cancellation aren't interchangeable.

### 5. Preserve captured-payment reality and compensate appropriately

The system must not pretend capture failed because the response timed out.

Once capture is confirmed, the workflow should evaluate whether the supplier reservation remains valid.

If it does, the booking may continue toward confirmation.

If inventory has been definitively lost and the booking cannot be fulfilled, the application must initiate refund or other contractually appropriate compensation.

If supplier state is still uncertain, preserve the unresolved state and continue reconciliation.

### 6. Reconciliation provides an independent recovery path

A scheduled process should inspect payment operations that remain unresolved beyond expected processing times.

It queries the provider using stable references and advances the workflow according to authoritative state.

Webhook delivery is useful for timely updates, but it shouldn't be the only mechanism capable of establishing the final outcome of a business-critical financial operation.

---

# 19. Mental Model

A reliable multi-step business workflow is a **durable state machine coordinating local transactions and external effects that cannot be rolled back together**.

When designing one, ask:

- **What does success actually promise?** Distinguish requested, held, authorized, confirmed, captured, and delivered outcomes.
- **What state must survive a crash?** Persist operation identities, deadlines, transitions, and unresolved obligations.
- **Where are the local atomic boundaries?** Use database transactions for changes that truly belong together.
- **Which effects are external?** Assume timeouts and retries can leave their outcomes uncertain.
- **What happens after partial success?** Define continuation, compensation, and reconciliation.
- **Can delayed or duplicate work cause harm?** Enforce versioned transitions, idempotency, and authoritative state checks.
- **How does the operation eventually finish?** Every nonterminal state needs a recovery or escalation path.

The central principle:

**A business workflow is reliable when it can recover the correct next action from durable state—not when every step happens to succeed during the original request.**

That is the difference between a backend that works under normal conditions and one that remains trustworthy when the real world refuses to cooperate.

---

# Next Session — System Design Workshop: Build for 100× Traffic

We now understand database design, query performance, transactions, caching, queues, partial failures, replication, scaling, service boundaries, and durable workflows.

In **SE490-L03 — System Design Workshop: Build for 100× Traffic**, we'll bring the entire course together: take a realistic production hotel-booking backend, increase its traffic by two orders of magnitude, and decide which architectural changes are actually justified, which should happen first, and which fashionable technologies we'd deliberately avoid.

---


---

## End of CS430

**CS430 — Distributed Systems and Reliable Workflows** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

- **Stripe — Place a Hold on a Payment Method:** https://docs.stripe.com/payments/place-a-hold-on-a-payment-method
- **Stripe — PaymentIntent Lifecycle:** https://docs.stripe.com/payments/paymentintents/lifecycle
- **Stripe — Webhooks:** https://docs.stripe.com/webhooks
- **Stripe — Idempotent Requests:** https://docs.stripe.com/api/idempotent_requests
- **AWS — Saga Orchestration Pattern:** https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html
- **AWS — Transactional Outbox Pattern:** https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- **PostgreSQL — Explicit Locking:** https://www.postgresql.org/docs/current/explicit-locking.html
- **PostgreSQL — SELECT and Row Locking:** https://www.postgresql.org/docs/current/sql-select.html


---

