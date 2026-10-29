---
id: SE325-L05
course: SE325
title: "Surviving Third-Party Integrations"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE325-L04
next: SE325-L06
---

# SE325 — Backends in the Wild: Production Field Guide
## Lecture 05: Surviving Third-Party Integrations

*The supplier API returns HTTP 200. Every synchronization job completes. The monitoring dashboard is green. Three weeks later, finance discovers that thousands of hotel-night records are wrong. The external API didn't go down. Something more difficult happened: it changed while continuing to work.*

---

# Part I — Intuition

## 1. The Integration That Broke Without Failing

Imagine you're a backend engineer at Mercury, our hotel-booking platform.

Mercury works with hundreds of accommodation suppliers. Some expose modern APIs; others communicate through channel managers, legacy integration platforms, or scheduled data feeds.

One supplier, AlpineRooms, provides an API for hotel availability and pricing.

Mercury calls the API several times an hour.

It retrieves hotel identifiers, room types, dates, prices, and available inventory.

The integration has worked for eighteen months.

Then the supplier makes a change.

Previously, availability records contained dates such as `2026-11-03`.

Now some records contain timestamps such as `2026-11-03T00:30:00+02:00`.

The supplier's engineering team considers this a minor improvement. They wanted to include timezone information.

Your application continues receiving valid JSON.

Every response has HTTP status 200.

The parser doesn't throw an exception.

The synchronization job reports success.

But your importer interprets the timestamp as an instant, converts it to UTC, and takes the UTC calendar date.

For some records, November 3 becomes November 2.

The application has silently moved room availability into the previous day.

Nobody receives an error alert.

Days later, the business notices that availability reports don't match the supplier's system.

This is an important category of production failure.

**An integration can remain technically available while becoming semantically incorrect.**

## 2. An API Contract Is More Than JSON Structure

Suppose an API returns:

```json
{
  "hotelId": "H-482",
  "available": 3,
  "date": "2026-11-03"
}
```

Your application understands this response.

But what exactly does `available` mean?

Three available rooms?

Three available room categories?

Three units remaining after existing reservations?

Three units visible to Mercury under its commercial allocation?

And what does the date mean?

A hotel's local calendar date?

A UTC date?

The beginning of a nightly inventory period?

A timestamp representing when the availability was calculated?

The JSON structure alone doesn't answer these questions.

The meaning comes from the contract.

A contract includes field types, required values, units, timezones, identifier semantics, pagination behavior, error handling, and the meaning of business operations.

If the vendor changes any of those assumptions, your application can become incorrect even when every HTTP request succeeds.

This is why integration maintenance is different from merely knowing how to send requests.

## 3. The Supplier Doesn't Know Your Architecture

Imagine that Mercury relies on AlpineRooms for availability.

AlpineRooms doesn't know how you've organized your database.

It doesn't know that your importer assumes every page contains exactly one hundred records except the final page.

It doesn't know that your application interprets every date as UTC.

It doesn't know that you have a nightly reconciliation process that overwrites cached inventory.

From the vendor's perspective, its API may be working normally.

From Mercury's perspective, an undocumented assumption has broken.

The difficulty is that you don't control the external system.

You can ask for documentation, subscribe to change notices, or negotiate support commitments.

But you can't independently guarantee that the supplier will never introduce a surprising behavior.

The integration must tolerate some degree of uncertainty.

## 4. A Short Page Isn't Necessarily the Last Page

Now introduce another change.

AlpineRooms previously returned exactly one hundred records per page, except for the final page.

Your importer uses this rule:

"If the page contains fewer than one hundred records, we've reached the end."

Then the vendor changes its pagination implementation.

It starts returning variable-sized pages.

A response containing sixty records may still provide a continuation cursor pointing to more data.

Your importer stops after those sixty.

The job reports success.

The remaining records are never fetched.

### Visual anchor 1 — The successful incomplete synchronization

```text id="v5p01"
Supplier API
    |
    v
Page 1: 100 records
next_cursor = A
    |
    v
Page 2: 60 records
next_cursor = B
    |
    +---- Broken client stops here
    |
    v
Page 3: 80 records
next_cursor = null
```

The error isn't the number of records returned.

It's the importer's incorrect assumption about what indicates completion.

**Pagination must follow the provider's documented continuation contract—not a guess based on page length.**

## 5. A Webhook Isn't a Command from the Future

The supplier also sends webhooks when availability changes.

Suppose hotel H-482 has five rooms available.

A customer books a room.

The vendor sends an update saying four remain.

Another customer books several rooms.

The vendor sends a newer update saying one remains.

But network delivery isn't necessarily ordered.

The newer event arrives first.

Your application stores one available room.

Then the older event arrives.

Your application overwrites the value with four.

The system has moved backward.

Both webhooks were valid.

The bug lies in treating arrival order as business-event order.

### Visual anchor 2 — Out-of-order delivery

```text id="v5p02"
Supplier reality:

Revision 10: 4 rooms
Revision 11: 1 room

Network arrival:

Revision 11 arrives first
       |
       v
Mercury stores 1 room

Revision 10 arrives later
       |
       v
Broken importer stores 4 rooms
```

A webhook should usually be treated as evidence of an external event, not an unconditional instruction to overwrite current state.

Where the provider supplies a meaningful per-resource version or sequence number, the consumer can use it to reject stale updates.

Otherwise, the consumer may need to retrieve the latest authoritative representation from the vendor.

## 6. Why Authentication Also Becomes an Operational Problem

Suppose the supplier uses OAuth.

Your application obtains an access token and uses it to call the API.

Eventually the token expires.

The integration must refresh its authorization or obtain new credentials.

Now imagine twenty workers discovering the expiration simultaneously.

All twenty attempt to refresh the same credentials.

The vendor rotates the refresh token.

Some workers use the newly issued token.

Others attempt to reuse the invalidated one.

Suddenly the integration is failing even though the vendor's service is healthy.

Authentication is therefore not merely a configuration step performed when the integration is first installed.

Credentials have lifetimes, rotation behavior, permissions, and failure modes.

A production integration needs to manage them deliberately.

## 7. Rate Limits Are Part of the Contract

Imagine the supplier allows a limited number of API requests per minute.

Mercury usually stays within the limit.

Then somebody launches a historical backfill.

The backfill attempts to retrieve three months of availability.

Thousands of requests begin.

The supplier responds with `429 Too Many Requests`.

A naive client retries immediately.

The vendor responds with another 429.

The retry loop makes the situation worse.

Meanwhile, normal synchronization calls are also being throttled.

The emergency backfill has displaced the everyday work required to keep customer-facing availability current.

Rate limits aren't merely errors to catch.

They're constraints around how much work the integration may perform.

## 8. The External System Is a Separate Failure Domain

Let's put the pieces together.

The supplier may change its schema.

Its pagination may behave differently.

Authentication may expire.

Rate limits may interrupt a backfill.

Webhooks may be duplicated or delayed.

The API may time out after successfully completing an operation.

The supplier's sandbox may behave differently from production.

And the supplier may experience an outage while Mercury remains healthy.

### Visual anchor 3 — The integration boundary

```text id="v5p03"
       Mercury application
                |
                v
       Integration adapter
                |
       +--------+--------+
       |        |        |
    Auth     Request    Response
       |        |        |
       +--------+--------+
                |
                v
       External supplier
                |
       +--------+--------+
       |                 |
    Polling           Webhooks
       |                 |
       +--------+--------+
                |
                v
     Validation & reconciliation
                |
                v
        Mercury's data
```

The adapter is more than a convenient HTTP client.

It is the boundary where external uncertainty must be translated into internal guarantees.

## 9. The Five Questions That Matter

Whenever you encounter an unfamiliar vendor integration, ask:

**What does the vendor promise?** Not only response shapes, but field meanings, consistency, ordering, pagination, and operational limits.

**How can that promise change?** Versioning, undocumented behavior, token policies, and sandbox differences.

**What happens when communication is uncertain?** Timeouts, retries, ambiguous outcomes, and duplicate notifications.

**How do we detect incorrect data?** Validation, coverage checks, freshness measures, reconciliation, and business invariants.

**How do we repair it?** Durable checkpoints, bounded replay, authoritative resynchronization, and controlled publication.

### A tiny comprehension check

A supplier returns HTTP 200, but a date's format changes. Has the API necessarily preserved its business contract?

No.

A page contains fewer records than the requested limit but includes a continuation cursor. Should the importer stop?

No. It should follow the documented continuation mechanism.

A webhook is validly signed but contains an older availability revision. Should it automatically overwrite newer state?

No. Authenticity and freshness are separate properties.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 10. An Integration Is a Product You Maintain

A common engineering mistake is treating an external API integration as a small implementation task.

A developer receives credentials, writes an HTTP client, maps response fields into internal models, and declares the integration finished.

In reality, the application has acquired a dependency on an independently operated product.

That product will evolve.

Its documentation may change.

Its authentication mechanisms may be updated.

Some endpoints may be deprecated.

Its data may contain unexpected values.

And its operational behavior may vary under load.

### 10.1 The integration lifecycle

A mature integration has several responsibilities.

Onboarding credentials and tenant configuration.

Mapping vendor identifiers into internal identities.

Retrieving or receiving data.

Validating the data contract.

Persisting authoritative or derived information.

Detecting missed updates.

Recovering from failed requests.

Monitoring correctness and freshness.

Handling vendor changes.

Eventually decommissioning the integration safely.

The initial API implementation is only the beginning.

### 10.2 Operational ownership

Some companies have dedicated integration teams.

Others assign each vendor to a backend developer.

A smaller organization may expect one engineer to handle authentication, data mapping, incident investigation, and vendor communication.

The exact team structure varies.

But somebody needs to know which integrations are healthy, which are stale, and which have become untrustworthy.

A dashboard containing only HTTP success rates is insufficient.

## 11. The Adapter Boundary

Consider Mercury's internal representation of hotel availability.

It might contain a stable internal hotel ID, room type, local stay date, currency, price, available quantity, and source revision.

AlpineRooms uses its own identifiers and field names.

The integration adapter translates between these representations.

### 11.1 Don't spread vendor terminology everywhere

If every application service manipulates raw AlpineRooms response objects, vendor assumptions leak across the codebase.

A field rename may affect dozens of unrelated services.

A dedicated adapter can isolate those assumptions.

For example, one translation layer maps the vendor's `property_code` to Mercury's internal hotel identity.

Another explicitly converts vendor monetary values into the application's canonical money representation.

### 11.2 Translation must preserve meaning

A mapper that converts a field's name isn't necessarily a correct adapter.

Suppose the supplier reports prices per night while Mercury expects totals for an entire stay.

The mapping needs to account for that distinction.

Suppose the supplier reports room availability for a local accommodation date, while Mercury stores a timestamp.

The integration needs a documented interpretation.

### 11.3 Preserve raw evidence carefully

When debugging integration drift, having the original vendor payload can be valuable.

It allows the team to determine whether corruption occurred before or after translation.

But raw payloads may contain personal or commercially sensitive information.

Retain them only under an appropriate policy, with access controls and limited duration.

The goal is diagnosability, not permanent duplication of every external record.

## 12. Contract Drift: Valid Syntax, Wrong Semantics

A contract can change in several ways.

A previously required field becomes optional.

An identifier changes format.

A currency switches from major units to minor units.

A date begins including timezone information.

An enum acquires a new value.

An amount that once meant net price begins including tax.

An endpoint changes its pagination guarantees.

Some changes are easy to detect.

Others produce valid, believable, incorrect data.

### 12.1 Strict parsing versus permissive guessing

Suppose the application expects a local date formatted as `YYYY-MM-DD`.

The supplier starts sending a full timestamp.

A permissive parser might accept both.

But what should the timestamp mean?

Is it the beginning of the local stay date?

Is it a UTC instant?

Is it a timestamp describing when the record was updated?

If the meaning is unknown, converting it automatically may create silent corruption.

### 12.2 Quarantine uncertainty

For consequential fields, an unexpected representation should often fail validation or enter a controlled quarantine path.

This is preferable to inventing an interpretation.

The integration can continue processing unaffected records if the business contract permits partial success.

But the affected records should be counted and investigated.

### 12.3 Contract compatibility isn't only backward compatibility

A vendor may add an optional field without breaking your parser.

That doesn't mean the change is irrelevant.

Perhaps the new field changes how another field must be interpreted.

The contract review needs to consider semantics as well as syntax.

## 13. Dates, Timezones, and Local Business Meaning

Hotel availability is particularly sensitive to date semantics.

A guest stays from November 3 to November 6.

Those dates describe nights at a particular property.

They aren't necessarily best represented as arbitrary UTC instants.

### 13.1 A date is not a timestamp

A local date represents a calendar day.

A timestamp with an offset represents an instant.

Converting an instant into UTC may change its calendar date.

For example, `2026-11-03T00:30:00+02:00` corresponds to 22:30 UTC on November 2.

If the vendor intended the local hotel date November 3, taking the UTC date produces the wrong business value.

### 13.2 The correct conversion depends on the contract

If the vendor explicitly documents the timestamp as the beginning of the hotel's local stay date, the local calendar date may be appropriate.

If the field represents an event timestamp, converting to UTC for storage may be appropriate.

The same string can require different treatment depending on its meaning.

### 13.3 Never rely on the server's default timezone

A backend may run in UTC.

The supplier may operate in Paris.

The hotel may be in Helsinki.

A scheduled job may execute in another region.

Implicit timezone conversions can introduce errors.

Use explicit domain types and a documented timezone policy.

### 13.4 The migration problem

Suppose historical records were imported using the wrong timezone conversion.

Fixing the parser prevents future corruption.

It doesn't correct previously imported data.

The team needs to identify the affected interval, establish authoritative source values, and perform a controlled backfill.

## 14. Pagination Is a Consistency Contract

Many APIs return large datasets in pages.

The most important pagination designs include offset-based pagination, cursor pagination, and continuation-token pagination.

### 14.1 Offset pagination

A client requests page zero, page one, page two, and so on.

This can work for relatively stable datasets.

But consider what happens when records are inserted or deleted while the client traverses the list.

The relative positions of records may shift.

A client can miss or duplicate entries.

### 14.2 Cursor pagination

The server returns a continuation token representing where the next page should begin.

The client follows that token until the provider's documented completion condition is reached.

But a cursor isn't automatically a consistent snapshot.

The provider may still permit records to change during traversal.

### 14.3 A short page doesn't establish completion

The server may return fewer records than requested while still providing another cursor.

Reasons can include internal partitioning, filtering, service limits, or implementation-specific pagination behavior.

Do not infer completion from page length unless the API explicitly promises that rule.

### 14.4 The continuation token belongs to its query

A cursor may encode filters, sort order, or internal position.

Changing query parameters mid-traversal can invalidate its meaning.

An integration should bind checkpoints to the relevant tenant, endpoint, filters, source version, and cursor.

### 14.5 Watch for repeated cursors

A broken provider or client may repeatedly receive the same continuation token.

Without a guard, the synchronization can loop indefinitely.

Record cursor progress and detect cycles.

A repeated token is a reason to investigate—not automatically a valid final page.

## 15. A Complete Pagination Loop Can Still Produce an Incomplete Dataset

Suppose Mercury follows every cursor correctly.

The supplier's data changes during the scan.

At the beginning, room H-482 appears on Page 1.

Later, a record is added or removed.

Another room changes position.

The importer may still miss a record or observe inconsistent versions, depending on the vendor's pagination guarantees.

### 15.1 Request a snapshot when supported

Some vendors provide snapshot tokens or consistent export endpoints.

These establish a stable view for a traversal, subject to documented limitations.

### 15.2 Watermark-based synchronization

Another approach retrieves changes since an agreed source timestamp or revision.

But the semantics matter.

Does the watermark represent creation time, update time, or transaction commit order?

Can multiple records share the same timestamp?

Are updates delayed or backdated?

A reliable watermark strategy needs a deterministic boundary and tie-breaking policy.

### 15.3 Snapshot plus changes

A common bootstrap pattern is to obtain a baseline snapshot and then apply changes occurring afterward.

But the handoff between snapshot and incremental changes must be defined.

If you capture the change watermark only after finishing the snapshot, changes occurring during the scan may be missed unless the provider guarantees otherwise.

Prefer a vendor-supported snapshot cursor or a safe overlap-and-deduplicate protocol.

### 15.4 Coverage verification

Where the provider offers counts, checksums, revision ranges, or inventory summaries, use them.

But understand what those numbers represent.

A record count can detect missing entities.

It cannot detect a record whose price is wrong but whose identity is still present.

Coverage checks and semantic reconciliation complement one another.

## 16. Token Lifecycles and OAuth Operations

Many vendor integrations use API keys.

Others use OAuth 2.0.

Some require client certificates or signed requests.

The authentication mechanism is not interchangeable, but several operational principles recur.

### 16.1 Access-token expiration

An access token typically has a limited lifetime.

The application should know when it expects the token to expire and refresh or reacquire credentials according to the vendor's supported mechanism.

But a 401 response isn't universally proof of expiration.

It may indicate revocation, invalid audience, configuration problems, or another authentication failure.

### 16.2 Refresh-token rotation

Some OAuth authorization servers rotate refresh tokens.

When the client refreshes, the server issues a new refresh token and invalidates the previous one.

This can detect token replay, but it creates coordination requirements.

If several workers use the old refresh token concurrently, they may interfere with one another.

### 16.3 Coordinate refresh

A production integration can maintain an authoritative credential record and coordinate refresh operations.

Depending on the system, that may involve a single token-management component, conditional database updates, or another safe ownership mechanism.

The exact solution should respect the vendor's token policies.

### 16.4 Secrets aren't logs

Never place access tokens or refresh tokens in ordinary application logs.

Redact authorization headers and sensitive query parameters.

Credentials need secure storage, scoped permissions, rotation, and incident-recovery procedures.

### 16.5 Least privilege

A vendor integration that only retrieves hotel availability shouldn't automatically receive broad permission to cancel reservations or access unrelated customer data.

Use the narrowest permissions the provider supports.

OAuth scopes and API roles are part of the integration's security contract.

## 17. Rate Limits Are Shared Resource Budgets

Suppose the vendor allows five hundred API requests per minute.

Mercury has several workers:

A frequent availability synchronizer.

A historical catalogue backfill.

A support-tool lookup service.

A scheduled reconciliation process.

If each independently believes it may issue five hundred requests per minute, the combined traffic can overwhelm the vendor's quota.

### 17.1 The quota may apply at different scopes

The provider may enforce limits per API key, tenant, account, endpoint, application, or underlying resource.

A rate-limit strategy needs to know the actual scope.

### 17.2 Coordinate budgets

If multiple workers share one vendor quota, they need an appropriate shared request budget.

An individual worker's local limiter may be insufficient.

### 17.3 Separate priorities

Normal availability synchronization may be more urgent than a historical backfill.

The integration should reserve or prioritize capacity according to business needs.

A backfill shouldn't monopolize the same quota that keeps current hotel inventory fresh.

### 17.4 Limit concurrency too

Request rate isn't the only constraint.

A provider may permit a certain number of requests per minute but perform poorly under too many simultaneous requests.

The client should consider both request rate and in-flight concurrency.

## 18. HTTP 429 and Retry-After

HTTP status 429 indicates that the client has sent too many requests within the relevant limits.

A provider may include a `Retry-After` header.

That header can express a delay in seconds or an HTTP date.

The client should respect the documented vendor retry policy and applicable server guidance.

### 18.1 Don't retry immediately

Immediate retries after a rate-limit response can amplify overload.

Use bounded retry behavior.

### 18.2 Add jitter when appropriate

If thousands of clients retry after exactly the same delay, they may create another synchronized burst.

Jitter spreads retries across time.

### 18.3 Retry budgets matter

A worker should not retry indefinitely.

The integration needs a maximum attempt or elapsed-time budget, durable status, and an escalation path for operations that remain incomplete.

### 18.4 Respect deadlines

A request serving an interactive customer may have a short deadline.

A nightly backfill may tolerate longer waits.

The retry strategy should reflect those different objectives.

### 18.5 Rate limiting can be evidence

An unexpected rise in 429 responses may indicate that Mercury changed request patterns, the vendor reduced quotas, or another workload began consuming the shared budget.

Investigate before simply increasing retry counts.

## 19. Not Every HTTP Failure Means the Same Thing

Let's distinguish common response categories.

**401 Unauthorized:** The request lacks valid authentication according to the server's requirements. Investigate token validity and authentication context.

**403 Forbidden:** The server refuses the operation. The client may lack permission, although providers can use the status for other policy decisions.

**404 Not Found:** The requested resource isn't available under the relevant endpoint semantics. It doesn't universally prove permanent deletion.

**409 Conflict:** A request conflicts with the current resource state under the provider's contract.

**429 Too Many Requests:** A rate limit or quota was exceeded.

**5xx errors:** The server or an intermediary encountered a failure. The operation's final outcome may remain uncertain.

These are starting points, not complete business semantics.

A provider may document special error codes and response bodies.

### 19.1 Classify retryability

Retry a transient read failure when appropriate.

Don't blindly retry an invalid request.

Don't automatically repeat a non-idempotent mutation after a timeout.

### 19.2 Unknown versus failed

Suppose Mercury sends a reservation cancellation request.

The connection times out.

The cancellation might have succeeded.

Repeating it without a stable operation identity or authoritative status check may create additional problems.

This is the same uncertain-outcome problem studied in CS430-L01.

The integration should use the vendor's documented idempotency or lookup mechanisms where available.

## 20. Webhook Ingress Is a Security Boundary

Webhooks reverse the direction of communication.

Instead of Mercury polling the vendor, the vendor sends events to Mercury.

A production webhook endpoint is exposed to incoming requests.

It must establish whether each request is authentic and acceptable.

### 20.1 Verify signatures over the actual bytes

Providers commonly use HMAC or another signing mechanism.

The application should verify the signature according to the vendor's specification.

If the signature is calculated over the raw request body, parsing and reserializing JSON before verification can alter the bytes and invalidate the comparison.

Use a constant-time comparison routine for MAC verification where appropriate.

### 20.2 Secrets must be managed

Webhook signing secrets should be stored securely.

Rotation may require accepting a bounded overlap of old and new secrets under a defined policy.

### 20.3 Authentication isn't authorization

A valid signature proves that the payload was authenticated according to the signing protocol.

It doesn't mean every event should modify any internal tenant or resource.

Verify event type, source identity, tenant mapping, resource ownership, and expected schema.

### 20.4 Replay protection

Some providers include unique delivery IDs, timestamps, or other replay-prevention information.

The client can use these according to the provider's contract.

A delivery ID may be reused on redelivery, so the application should not treat every repeated delivery as a distinct business event.

### 20.5 Ingest before expensive processing

A webhook endpoint should usually validate and durably record the event before acknowledging successful receipt, then process it asynchronously.

This reduces the chance of provider timeouts and separates ingress availability from business processing duration.

However, returning success before durable acceptance can create data loss if the process crashes immediately afterward.

## 21. Delivery Identity Versus Business Revision

This is a particularly important distinction.

Suppose an availability webhook arrives twice.

Both copies have the same delivery ID.

The inbox can deduplicate them.

Now suppose two distinct events arrive for the same hotel.

The first reports source revision 10.

The second reports revision 11.

These are different events.

If revision 11 arrives first, revision 10 must not overwrite its newer state.

### 21.1 Inbox deduplication

An inbox table can record unique vendor delivery identifiers.

This prevents processing the same delivery repeatedly.

### 21.2 Revision-aware projection

The inventory projection can store the latest accepted source revision.

An update is accepted only if it is newer according to the vendor's documented ordering scheme.

### 21.3 Deduplication doesn't solve ordering

A repeated event and an out-of-order event are different problems.

A unique delivery ID prevents duplicated processing of the same message.

It doesn't prevent an older *different* event from overwriting newer state.

### 21.4 If no usable version exists

Some vendors provide no reliable ordering identifier.

A safer webhook strategy may treat the event as a signal to retrieve the current authoritative resource.

The event tells Mercury that something changed.

Mercury then fetches the current state.

This creates additional API traffic but can simplify ordering when the provider's lookup semantics are trustworthy.

## 22. Webhooks and Polling Are Complementary

A common mistake is assuming that webhooks make periodic synchronization unnecessary.

Webhooks can provide low-latency change notifications.

But deliveries may be delayed, duplicated, or missed.

Polling can identify changes not observed through webhooks.

### 22.1 The hybrid model

Use webhooks for responsiveness.

Use periodic synchronization for completeness.

Use reconciliation to compare derived Mercury state with authoritative supplier state.

### 22.2 Avoid two uncontrolled writers

A webhook consumer and a polling synchronizer may both update the same inventory record.

Without shared version rules, one can overwrite the other with stale data.

Both should participate in the same authority and ordering contract.

### 22.3 Reconciliation is not another blind overwrite

Suppose the latest webhook reports revision 11.

A slow polling request returns an older snapshot from revision 10.

The polling result should not automatically replace the newer state.

The reconciliation system needs to understand the source's version and snapshot semantics.

## 23. Backfills and Replays Must Be Bounded

Suppose an integration bug affected thirty days of supplier data.

The team repairs the parser.

Now it needs to correct historical records.

A naive recovery would launch a massive backfill with unlimited concurrency.

That can exhaust the vendor quota and Mercury's own database capacity.

### 23.1 Define the affected population

Which suppliers?

Which markets?

Which date ranges?

Which field interpretations?

Which source revisions?

The correction should target a justified population.

### 23.2 Preserve the source identity

A reprocessing job should identify the source data and transformation version.

If the vendor's current API no longer exposes the historical values, simply querying today's endpoint may not reconstruct yesterday's truth.

### 23.3 Process in controlled chunks

Use bounded request concurrency, rate budgets, checkpoints, and retries.

Record accepted, rejected, and corrected records.

### 23.4 Make repair idempotent

A backfill should be safe to resume.

Repeated processing of one chunk shouldn't create duplicate business records or stale overwrites.

### 23.5 Separate preparation from publication

For high-risk availability or pricing data, staging and controlled publication may prevent partially repaired data from becoming customer-visible.

The exact choice depends on the business requirements.

## 24. Sandbox Versus Production

Vendors often provide sandbox environments.

They can be useful for initial integration testing.

But their behavior may differ from production.

A sandbox might contain a tiny dataset.

Production may contain millions of records.

A sandbox may rarely trigger rate limits.

Production may impose strict quotas.

A sandbox may send predictable webhooks.

Production may deliver events under real network delays and retries.

A sandbox may not reproduce every supported date format or historical edge case.

### 24.1 Sandbox success is necessary but insufficient

A passing sandbox test proves something about the sandbox behavior exercised.

It doesn't prove the integration is robust under production scale and data diversity.

### 24.2 Contract fixtures

Maintain representative vendor payloads in tests.

Include normal responses, optional fields, unknown enums, date boundaries, partial pages, errors, and webhook variants.

These fixtures help detect regressions when Mercury changes its adapter.

### 24.3 Production canaries

Where the integration permits it, use carefully scoped production verification.

For example, fetch a known harmless resource and validate its shape and semantics.

Don't execute dangerous business operations merely to test connectivity.

### 24.4 Vendor change monitoring

Subscribe to vendor changelogs, deprecation notices, and support announcements.

Maintain ownership for reviewing relevant changes.

But don't rely exclusively on vendor communication.

Your own validation should detect surprising behavior.

## 25. What Does a Healthy Integration Dashboard Show?

Let's return to the opening incident.

The HTTP success rate is 100%.

The synchronization job reports success.

Yet inventory is wrong.

Clearly, the dashboard measures the wrong things.

### 25.1 Transport metrics

Request count.

Latency.

HTTP status categories.

Timeouts.

Rate-limit responses.

Authentication failures.

These indicate communication health.

### 25.2 Processing metrics

Records received.

Records accepted.

Records rejected.

Unknown schema values.

Pagination cursors traversed.

Import duration.

These indicate processing behavior.

### 25.3 Freshness metrics

Age of the latest authoritative update.

Lag between vendor changes and Mercury's accepted state.

Time since the last complete synchronization.

These indicate how current the data is.

### 25.4 Completeness metrics

Expected versus observed record coverage.

Missing identifiers.

Incomplete page traversals.

Unreconciled resource counts.

These indicate whether the expected data arrived.

### 25.5 Correctness metrics

Invalid price distributions.

Impossible availability values.

Unexpected date shifts.

Revision regressions.

Disagreements with authoritative supplier reports.

These indicate whether the data means what it should.

### 25.6 Operational workload metrics

Quota consumption.

Requests waiting for rate budget.

Backfill queue depth.

Outstanding webhook inbox records.

Repeated failures by tenant or endpoint.

These indicate whether the integration can sustain its workload.

## 26. The Silent Corruption Incident

Now reconstruct the AlpineRooms failure.

The nightly sync reports success.

But a vendor pagination change creates shorter intermediate pages.

The importer stops early.

Some properties never receive updates.

Separately, a date field changes from a local calendar date to an offset timestamp.

Mercury converts it to UTC and extracts the UTC date.

Some availability shifts into the previous day.

Finally, a delayed older webhook overwrites a newer availability revision.

Three independent defects exist.

### 26.1 Why the monitoring remained green

Every HTTP request returned success.

The parser accepted every payload.

The job had no expected-coverage check.

The date transformation didn't validate the field's semantic contract.

The webhook consumer ignored source revisions.

The dashboard measured request execution instead of data integrity.

### 26.2 Why this is difficult to detect

The resulting data often looks plausible.

A hotel with three rooms available is believable.

A date one day earlier is believable.

A catalogue missing several records may still contain thousands of valid properties.

Silent corruption can survive ordinary smoke tests.

### 26.3 The first response should be containment

Identify which markets and suppliers are affected.

Stop the defective synchronization path from overwriting additional correct data.

Preserve raw evidence according to the retention policy.

Avoid blindly republishing uncertain prices or availability.

If necessary, temporarily mark affected records as stale or unavailable to customer-facing booking flows.

### 26.4 Correct the interpretation

Establish the vendor's actual date and pagination contracts.

Update the adapter.

Add validation for unexpected representations.

Make the cursor traversal obey the documented continuation behavior.

### 26.5 Repair historical state

Determine the affected period.

Retrieve authoritative source information through a safe backfill or vendor-supported export.

Apply version-aware corrections.

Reconcile counts, dates, prices, and availability.

### 26.6 Verify before resuming normal operation

Run the corrected integration on controlled data.

Compare against independent vendor evidence.

Re-enable synchronization gradually if appropriate.

Monitor contract-validation errors and freshness.

## 27. Vendor Communication Is an Engineering Capability

At some point, the integration team may need to contact AlpineRooms.

An effective support request is specific.

It identifies the affected endpoint, tenant or account, request time, correlation ID, expected contract, actual behavior, and business impact.

It avoids sharing raw credentials or unnecessary customer data.

### 27.1 A useful escalation

Instead of saying:

"Your API is broken."

Explain that a continuation cursor was returned after a short page and ask whether page size has ceased to be a completion guarantee.

Or provide the exact date representation change and ask for the documented semantic interpretation.

### 27.2 Incident evidence

Preserve request identifiers and safely redacted response examples.

Record whether the behavior differs between sandbox and production.

Track vendor responses as part of the incident timeline.

### 27.3 Design for independent recovery

A vendor may take days to respond.

Mercury needs bounded containment and a defensible fallback strategy.

But fallback should never invent authoritative booking availability.

If correctness can't be established, refusing an uncertain operation may be safer than presenting stale information as guaranteed.

## 28. Choosing an Integration Architecture

Not every vendor needs the same level of machinery.

A small, read-only weather lookup may use a straightforward HTTP client with timeouts and caching.

A hotel-inventory integration affecting customer bookings deserves stronger data validation and freshness checks.

A payment provider requires even more careful operation identity and reconciliation.

The design should reflect the consequences of incorrect or missing data.

### 28.1 Start with contracts

What is the source's authority?

What are its identifier and version semantics?

What are its authentication and quota constraints?

What does completion mean?

### 28.2 Then choose mechanisms

HTTP client.

Token management.

Pagination.

Webhook inbox.

Durable sync checkpoints.

Data staging.

Version-aware writes.

Reconciliation.

Monitoring.

Each mechanism should address a specific requirement.

### 28.3 Avoid universal adapters

A generic abstraction that hides every vendor difference may appear elegant.

But if it erases important semantic differences—such as whether a date is local or UTC—it can make the system less correct.

Share infrastructure where useful.

Keep vendor-specific business meaning explicit.

## 29. What an Experienced Backend Engineer Should Be Able to Do

You don't need to memorize every OAuth grant or every vendor's pagination syntax.

But you should recognize the dangerous assumptions.

A successful HTTP response doesn't establish data completeness.

A valid JSON payload doesn't establish business meaning.

A retry doesn't establish that the original operation failed.

A signed webhook doesn't establish that its information is current.

A sandbox test doesn't establish production behavior.

And a completed sync job doesn't establish that all relevant records agree with the vendor.

The senior-level skill is treating external integrations as long-lived contracts with independent failure modes.

The objective isn't merely to make communication succeed.

It's to keep the data trustworthy as both organizations evolve.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Green Synchronization

A nightly sync reports 100% successful API requests, but supplier inventory is missing.

What evidence would you inspect before concluding the API is healthy?

## Question 2 — The Short Page

A client requests one hundred records.

The supplier returns sixty and includes a continuation cursor.

Should the client stop?

Why?

## Question 3 — The Date Change

The vendor previously returned `2026-11-03`.

It now returns `2026-11-03T00:30:00+02:00`.

What must you establish before deciding how to store that value?

## Question 4 — OAuth Rotation

Twenty workers try to refresh the same rotating OAuth refresh token simultaneously.

What can go wrong?

How would you coordinate credential renewal?

## Question 5 — The Rate Limit

A historical backfill receives repeated 429 responses.

Should it retry immediately?

How should the integration preserve normal synchronization capacity?

## Question 6 — Valid Webhook, Stale Data

A validly signed webhook reports source revision 10.

The database already contains revision 11.

What should happen?

Does signature verification resolve the ordering problem?

## Question 7 — The Lost Response

A vendor mutation request times out.

Can you conclude that the external operation failed?

How should you recover?

## Question 8 — Sandbox Success

An integration passes every sandbox test.

Production synchronization begins losing records.

What environmental differences might explain the failure?

## Question 9 — Snapshot and Incremental Sync

An importer takes a full snapshot, then starts processing changes.

What must be true about the handoff between those two phases to avoid missing updates?

## Question 10 — The Data Contract

A vendor changes an amount from major currency units to minor currency units while preserving its JSON numeric type.

Why is a schema validator potentially insufficient?

## Question 11 — Observability

What metrics would distinguish a transport outage from silent data corruption?

## Question 12 — Senior Incident Design

Design an integration for a hotel supplier whose API uses OAuth, cursor pagination, webhooks, and strict quotas.

Explain how it handles retries, missed updates, delayed events, backfills, and data-correctness verification.

---

# Solutions and Discussion

## Solution 1 — Data Completeness

Inspect expected record coverage, cursor traversal, freshness, rejection counts, semantic validation, and reconciliation against authoritative supplier data.

HTTP success is necessary but insufficient.

## Solution 2 — Follow the Cursor

A short page isn't necessarily the final page.

The client should use the vendor's documented continuation semantics.

## Solution 3 — Date Meaning

Determine whether the field represents a local calendar date, an absolute instant, or another domain concept.

Do not silently convert it to UTC and take the UTC date unless that matches the contract.

## Solution 4 — Token Coordination

Concurrent refresh attempts may invalidate shared credentials or race while persisting rotated tokens.

Use a coordinated credential owner or safe conditional update mechanism, respecting the provider's OAuth policy.

## Solution 5 — Bounded Retry

Respect documented retry guidance, including `Retry-After` when applicable.

Use bounded retries and jitter.

Coordinate shared vendor quotas and reserve capacity for more important traffic.

## Solution 6 — Ordering

The older revision should not overwrite newer authoritative state.

A valid signature establishes authenticity and integrity under the signing protocol, not freshness.

## Solution 7 — Ambiguous Outcome

A timeout doesn't prove failure.

Use a stable operation identity, vendor idempotency features, or authoritative status lookup where available.

Avoid blind non-idempotent retries.

## Solution 8 — Production Differences

Production may differ in data volume, pagination, rate limits, token handling, webhook timing, or schema diversity.

Maintain representative contract tests and controlled production verification.

## Solution 9 — Snapshot Handoff

The baseline snapshot and incremental change stream need a defined overlap or shared source watermark.

Otherwise, changes during snapshot collection can be lost.

## Solution 10 — Semantic Drift

The JSON type remains numeric while the business unit changes.

Structural validation alone may accept values that are off by a factor of one hundred.

Validate units and business meaning.

## Solution 11 — Layered Observability

Transport metrics identify request failures.

Processing metrics identify rejected or malformed records.

Freshness, completeness, and reconciliation metrics identify missing or semantically incorrect data.

## Solution 12 — Reliable Integration

Use a vendor-specific adapter, secure token lifecycle, cursor traversal, coordinated quotas, signed webhook inbox, source-version-aware updates, durable checkpoints, bounded backfills, and periodic reconciliation.

The design should detect both communication failure and data-correctness failure.

---

# The Mental Model Worth Keeping

A third-party integration is an operational boundary between two organizations.

You control one side.

The other side has independent deployments, data models, authentication, quotas, and failure modes.

A successful request proves only that a particular request succeeded under the provider's response semantics.

It doesn't establish that the dataset is complete, fresh, correctly interpreted, or safe to publish.

The durable questions are:

**What exactly does the vendor's data mean?**

**How do we know we've received all relevant records?**

**How do we handle delayed, repeated, or uncertain operations?**

**What happens when credentials or quotas change?**

**How do we detect and repair disagreement with authoritative source data?**

A robust integration assumes that change is inevitable and makes incorrect assumptions observable before they become business incidents.

---

# Next Lecture — SE325-L06: API Protection and Multi-Tenant Fairness

We've investigated how to behave responsibly when an external vendor imposes limits on our application.

The next lecture turns the situation around.

Now Mercury is the platform serving API clients.

One enterprise tenant launches several expensive exports.

Another customer repeatedly executes complex searches.

A third starts an enormous synchronization backfill.

Per-IP rate limits look healthy.

The database connection pool is exhausted.

Ordinary booking requests begin timing out.

SE325-L06 will investigate request-rate limits, concurrency limits, tenant quotas, expensive-query budgets, bulkheads, load shedding, and how to protect critical business operations from noisy neighbors.

*The spoken lecture ends here. The remaining material is a practical integration investigation for screen-based work rather than continuous audio listening.*

---

# Optional Practical Lab — The Green Synchronization That Corrupted Inventory

## Lab Contract

This laboratory uses Python's standard library and SQLite.

It requires no vendor account, external API credentials, network access, or cloud infrastructure.

The local vendor fixture contains four hotel-inventory records.

It deliberately introduces three defects:

1. A short page that still has a continuation cursor.
2. A date representation that the broken importer converts to the wrong calendar day.
3. A newer webhook followed by a duplicate delivery and then an older revision.

The script provides commands to initialize the fixture, run the broken importer, deliver broken webhooks, audit the result, and execute a corrected reconciliation path.

The correction assumes a **fixture-specific, explicitly confirmed vendor contract**: offset timestamps in the sample represent the supplier-local calendar date. That interpretation must not be generalized to real APIs without documentation.

Webhook signatures are simulated using HMAC-SHA256 with a local demonstration key.

The simulator does not implement a real HTTP webhook server, OAuth, replay windows, distributed worker locking, or an actual vendor quota.

**Predict → Observe → Diagnose → Repair → Reconcile.**

## Lab 1 — Create the Workspace

Create a disposable directory named `se325-vendor-lab`.

Save the following script as `studio.py`.

The simulator creates a local SQLite database named `vendor_studio.sqlite3`.

Initialization refuses to overwrite an existing database.

### The vendor-integration simulator

```python
import argparse
import hashlib
import hmac
import json
import sqlite3

from datetime import (
    date,
    datetime,
    timezone,
)

from pathlib import Path


DB = Path("vendor_studio.sqlite3")

SECRET = (
    b"local-fixture-secret-"
    b"do-not-use-in-production"
)


RECORDS = [
    (
        "H-A",
        "2026-11-03",
        4,
        1,
    ),
    (
        "H-B",
        "2026-11-04",
        3,
        1,
    ),
    (
        "H-C",
        "2026-11-03T00:30:00+02:00",
        1,
        1,
    ),
    (
        "H-D",
        "2026-11-05",
        2,
        1,
    ),
]


# Note that Page 2 is short but
# still contains a continuation cursor.

PAGES = {
    None: (
        [RECORDS[0], RECORDS[1]],
        "p2",
    ),

    "p2": (
        [RECORDS[2]],
        "p3",
    ),

    "p3": (
        [RECORDS[3]],
        None,
    ),
}


# A new event, its redelivery,
# then a different older event.

EVENTS = [
    {
        "id": "evt-new",
        "record": "H-A",
        "version": 3,
        "available": 0,
    },
    {
        "id": "evt-new",
        "record": "H-A",
        "version": 3,
        "available": 0,
    },
    {
        "id": "evt-old",
        "record": "H-A",
        "version": 2,
        "available": 5,
    },
]


def connect():
    if not DB.exists():
        raise SystemExit(
            "Run init first in "
            "a disposable directory"
        )

    connection = sqlite3.connect(DB)

    connection.row_factory = sqlite3.Row

    return connection


def init():
    if DB.exists():
        raise SystemExit(
            "Database exists; "
            "delete it manually to reset"
        )

    with sqlite3.connect(DB) as connection:
        connection.executescript("""
            CREATE TABLE inventory (
                record_id TEXT PRIMARY KEY,
                business_day TEXT NOT NULL,
                available INTEGER NOT NULL,
                source_version INTEGER NOT NULL
            );

            CREATE TABLE inbox (
                event_id TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                source_version INTEGER NOT NULL
            );

            CREATE TABLE sync_runs (
                id INTEGER PRIMARY KEY
                    AUTOINCREMENT,
                mode TEXT NOT NULL,
                pages_seen INTEGER NOT NULL,
                rows_seen INTEGER NOT NULL,
                declared_success INTEGER NOT NULL
            );

            CREATE TABLE notes (
                id INTEGER PRIMARY KEY
                    AUTOINCREMENT,
                note TEXT NOT NULL
            );
        """)

    print(
        "Initialized local "
        "vendor-integration fixture"
    )


def page(cursor):
    if cursor not in PAGES:
        raise ValueError(
            "Invalid continuation cursor"
        )

    return PAGES[cursor]


def broken_day(value):
    if len(value) == 10:
        return date.fromisoformat(
            value
        ).isoformat()

    # BROKEN: Treats a supplier-local
    # business date as UTC date.

    return (
        datetime.fromisoformat(value)
        .astimezone(timezone.utc)
        .date()
        .isoformat()
    )


def expected_day(value):
    if len(value) == 10:
        return date.fromisoformat(
            value
        ).isoformat()

    # Fixture-specific confirmed rule:
    # timestamp represents the supplier's
    # local hotel calendar date.

    return (
        datetime.fromisoformat(value)
        .date()
        .isoformat()
    )


def upsert(
    connection,
    record_id,
    day,
    available,
    version,
    guard,
):
    if guard:

        connection.execute("""
            INSERT INTO inventory
            VALUES (?,?,?,?)

            ON CONFLICT(record_id)
            DO UPDATE SET
                business_day =
                    excluded.business_day,
                available =
                    excluded.available,
                source_version =
                    excluded.source_version

            WHERE
                excluded.source_version
                >= inventory.source_version
        """, (
            record_id,
            day,
            available,
            version,
        ))

    else:

        connection.execute("""
            INSERT INTO inventory
            VALUES (?,?,?,?)

            ON CONFLICT(record_id)
            DO UPDATE SET
                business_day =
                    excluded.business_day,
                available =
                    excluded.available,
                source_version =
                    excluded.source_version
        """, (
            record_id,
            day,
            available,
            version,
        ))


def broken_sync():
    cursor = None

    pages = 0
    rows = 0

    with connect() as connection:

        while True:
            entries, next_cursor = page(
                cursor
            )

            pages += 1

            for (
                record_id,
                when,
                available,
                version,
            ) in entries:

                upsert(
                    connection,
                    record_id,
                    broken_day(when),
                    available,
                    version,
                    False,
                )

                rows += 1

            # BROKEN:
            # A short page is NOT necessarily
            # the final page.

            if len(entries) < 2:
                break

            cursor = next_cursor

            if cursor is None:
                break

        connection.execute("""
            INSERT INTO sync_runs (
                mode,
                pages_seen,
                rows_seen,
                declared_success
            )
            VALUES (?,?,?,1)
        """, (
            "broken",
            pages,
            rows,
        ))

    print(
        f"Green sync: pages={pages} "
        f"rows={rows}"
    )


def signed(event):
    body = json.dumps(
        event,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()

    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256,
    ).hexdigest()

    return body, signature


def accept(event, safe):
    body, signature = signed(event)

    expected = hmac.new(
        SECRET,
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        signature,
        expected,
    ):
        raise ValueError(
            "Invalid webhook signature"
        )

    with connect() as connection:

        if safe:
            result = connection.execute("""
                INSERT OR IGNORE
                INTO inbox
                VALUES (?,?,?)
            """, (
                event["id"],
                event["record"],
                event["version"],
            ))

            if result.rowcount == 0:
                return (
                    "duplicate delivery ignored"
                )

            result = connection.execute("""
                UPDATE inventory
                SET
                    available = ?,
                    source_version = ?
                WHERE record_id = ?
                  AND source_version < ?
            """, (
                event["available"],
                event["version"],
                event["record"],
                event["version"],
            ))

            if result.rowcount == 0:
                return (
                    "stale event ignored"
                )

            return "applied"

        # BROKEN:
        # No deduplication or revision check.

        connection.execute("""
            UPDATE inventory
            SET
                available = ?,
                source_version = ?
            WHERE record_id = ?
        """, (
            event["available"],
            event["version"],
            event["record"],
        ))

        connection.execute("""
            INSERT INTO notes(note)
            VALUES (?)
        """, (
            "processed delivery "
            + event["id"],
        ))

        return (
            "applied without deduplication "
            "or version guard"
        )


def webhooks_broken():
    for event in EVENTS:
        print(
            event["id"],
            accept(event, False),
        )


def repair():
    cursor = None

    pages = 0
    rows = 0

    seen = set()

    with connect() as connection:

        while True:
            entries, next_cursor = page(
                cursor
            )

            pages += 1

            for (
                record_id,
                when,
                available,
                version,
            ) in entries:

                if record_id in seen:
                    raise RuntimeError(
                        "Duplicate snapshot ID; "
                        "investigate"
                    )

                seen.add(record_id)

                upsert(
                    connection,
                    record_id,
                    expected_day(when),
                    available,
                    version,
                    True,
                )

                rows += 1

            if next_cursor is None:
                break

            cursor = next_cursor

        # This is a simulated independent
        # provider coverage reference.

        expected_ids = {
            record[0]
            for record in RECORDS
        }

        if seen != expected_ids:
            raise RuntimeError(
                "Snapshot incomplete"
            )

        connection.execute("""
            INSERT INTO sync_runs (
                mode,
                pages_seen,
                rows_seen,
                declared_success
            )
            VALUES (?,?,?,1)
        """, (
            "repaired",
            pages,
            rows,
        ))

    print(
        f"Repaired snapshot "
        f"pages={pages} rows={rows}"
    )

    for event in EVENTS:
        print(
            "event",
            event["id"],
            accept(event, True),
        )


def audit():
    with connect() as connection:
        actual = {
            row["record_id"]: dict(row)
            for row in connection.execute(
                "SELECT * FROM inventory"
            )
        }

        runs = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM sync_runs "
                "ORDER BY id"
            )
        ]

        inbox = connection.execute(
            "SELECT COUNT(*) FROM inbox"
        ).fetchone()[0]

    expected = {
        record[0]: {
            "business_day":
                expected_day(record[1]),
            "available": record[2],
            "source_version": record[3],
        }
        for record in RECORDS
    }

    expected["H-A"]["available"] = 0
    expected["H-A"]["source_version"] = 3

    issues = []

    for key, value in expected.items():

        if key not in actual:
            issues.append(
                f"{key}: MISSING"
            )
            continue

        for field in (
            "business_day",
            "available",
            "source_version",
        ):

            if actual[key][field] != value[field]:
                issues.append(
                    f"{key}.{field}: "
                    f"actual={actual[key][field]!r} "
                    f"expected={value[field]!r}"
                )

    print("Sync runs:", runs)
    print("Inbox events:", inbox)
    print("Actual records:", actual)

    print(
        "AUDIT:",
        "PASS" if not issues else "FAIL",
    )

    for issue in issues:
        print(" -", issue)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=[
            "init",
            "broken-sync",
            "webhooks-broken",
            "audit",
            "repair",
        ],
    )

    args = parser.parse_args()

    commands = {
        "init": init,
        "broken-sync": broken_sync,
        "webhooks-broken": webhooks_broken,
        "audit": audit,
        "repair": repair,
    }

    commands[args.command]()
```

The simulator deliberately simplifies vendor API semantics.

It does not use a real network service or multiple concurrent consumers.

The fixture's source revisions are assumed to be monotonically increasing for each hotel record, and the final audit uses a separate simulated authoritative snapshot.

In production, those guarantees must be established through the vendor's documented protocol.

---

# Lab 2 — Reproduce the Broken Synchronization

Initialize the database.

```bash
python studio.py init
```

Run the defective importer.

```bash
python studio.py broken-sync
```

The importer reports success.

It processed two pages and three records.

### Before auditing

Inspect the `PAGES` fixture.

How many pages exist?

How many total records should be imported?

Why did the importer stop early?

### Investigate the date

Record H-C contains:

`2026-11-03T00:30:00+02:00`

Under the fixture's confirmed contract, the correct hotel business date is November 3.

What date does the broken conversion produce?

Why?

### Acceptance criteria

Identify both the pagination defect and the date-interpretation defect without relying on the audit output.

---

# Lab 3 — The Duplicate and Late Webhooks

Deliver the deliberately problematic webhook sequence.

```bash
python studio.py webhooks-broken
```

The sequence contains:

A newer event reporting zero available rooms.

The same delivery repeated.

An older event reporting five available rooms.

### Prediction

What availability will the broken consumer store?

What revision will it retain?

How many delivery-processing notes will exist?

### Required explanation

Why is a validly signed event still capable of corrupting state?

Why is delivery deduplication a different problem from source-revision ordering?

---

# Lab 4 — Audit the Integration

Run:

```bash
python studio.py audit
```

The audit should identify four mismatches.

One hotel has the wrong availability.

That hotel also has a regressed source revision.

Another hotel's date is wrong.

One hotel is completely missing.

### Investigation

What evidence proves the sync isn't complete?

Which failure was caused by pagination?

Which was caused by field interpretation?

Which was caused by event ordering?

### Interviewer challenge

"The synchronization job was green. Why are you saying it failed?"

Explain the difference between HTTP-level execution success and a complete, correct data projection.

---

# Lab 5 — Repair the Integration

Run the corrected reconciliation flow.

```bash
python studio.py repair
```

The repair follows all continuation cursors.

It interprets the fixture's date field according to the explicitly confirmed supplier-local business-date contract.

It verifies the expected snapshot coverage.

It applies source-version guards.

It deduplicates webhook deliveries.

And it refuses to let an older distinct event overwrite newer state.

### Verify

```bash
python studio.py audit
```

The audit should pass.

### Required explanation

What changed in the pagination loop?

Why is H-C's date now correct?

Why doesn't the older webhook replace the newer availability?

What would you do if the supplier provided no source revision number at all?

---

# Lab 6 — OAuth Token Rotation Review

## Scenario

Mercury has ten worker processes sharing one vendor integration.

All ten use an access token that expires at midnight.

At midnight, several workers receive authentication failures.

They simultaneously refresh the token.

The vendor uses refresh-token rotation.

### Your task

Design a safe credential-refresh strategy.

Address:

- Secure token storage.
- Token expiry.
- Coordination among workers.
- Atomic replacement of rotated credentials.
- Handling revocation.
- Distinguishing expired tokens from permission errors.
- Avoiding secret leakage in logs.
- Recovering if refresh succeeds remotely but credential persistence fails locally.

### Challenge

The vendor responds with HTTP 403.

Would you automatically refresh the token and retry the same operation?

Explain why that may be inappropriate.

---

# Lab 7 — Pagination Under Concurrent Updates

## Scenario

A vendor endpoint supports cursor pagination.

The client begins traversing a large dataset.

While the scan runs, the supplier creates new records and modifies existing ones.

The vendor doesn't guarantee that one cursor traversal represents a stable snapshot.

### Your task

Design a synchronization protocol that avoids gaps.

Investigate whether the vendor supports:

- Snapshot tokens.
- Stable continuation cursors.
- Change sequence numbers.
- Updated-since filters.
- Export snapshots.
- Webhook history.
- Independent record counts or checksums.

### Critical question

If you capture a change watermark only after completing the snapshot, what updates might be lost?

### Acceptance criteria

You identify the need for an overlap or vendor-supported snapshot-to-change-stream handoff.

---

# Lab 8 — The Rate-Limited Backfill

## Scenario

The vendor allows a limited number of requests per minute across Mercury's shared account.

Normal availability synchronization consumes part of that quota.

An engineer starts a thirty-day historical backfill.

The backfill generates repeated 429 responses.

### Your task

Design a shared vendor-request budget.

Explain how normal synchronization can retain priority over historical work.

Define:

- Request admission.
- Concurrency limits.
- Retry handling.
- `Retry-After` interpretation.
- Bounded exponential backoff.
- Jitter.
- Retry budgets.
- Checkpoints.
- Operator visibility.

### Interviewer challenge

"Why not just add more workers and retry faster?"

Explain how increasing request concurrency can worsen throttling and delay important synchronization.

---

# Lab 9 — Webhook Security Review

## Scenario

Mercury receives webhooks from a supplier.

The existing implementation parses JSON, then checks a signature calculated over the reserialized object.

It immediately updates the database before storing the delivery ID.

### Your task

Identify the problems.

Propose a safe ingress process that:

1. Receives the request through HTTPS.
2. Enforces an appropriate body-size limit.
3. Verifies the signature according to the vendor's raw-body contract.
4. Validates supported event types.
5. Resolves the authorized tenant and resource.
6. Durably records a unique delivery identity.
7. Acknowledges receipt according to the provider's timing requirements.
8. Processes the event asynchronously.
9. Rejects stale business revisions.
10. Supports redelivery and reconciliation.

### Additional challenge

The provider retries an event using the same delivery ID.

Should your inbox process it again?

What if the original delivery was recorded but its business processing never completed?

---

# Lab 10 — Sandbox Versus Production

## Scenario

The supplier's sandbox returns a hundred records.

Its production system returns several million.

The sandbox never rate-limits requests.

It always sends webhooks in order.

All dates are in one format.

### Your assignment

Create a contract-test and operational-verification plan.

Include:

- Short intermediate pages.
- Repeated cursors.
- Unknown enum values.
- Optional or missing fields.
- Date and timezone variations.
- Unexpected numeric units.
- Duplicate webhooks.
- Out-of-order webhooks.
- Token expiration.
- Throttling.
- Uncertain mutations.
- Large datasets.
- Partial synchronization.

### Acceptance criteria

You distinguish tests of the application adapter from evidence about real vendor production behavior.

---

# Final Incident — The AlpineRooms Synchronization Failure

## Business context

Mercury imports hotel availability from AlpineRooms.

The integration uses OAuth, cursor pagination, and webhooks.

A nightly synchronization job runs successfully.

Several markets show incorrect occupancy.

Some availability records are missing.

Others appear under the wrong date.

A delayed webhook has overwritten newer inventory.

### Required incident report

**Impact:** Which booking operations and markets are affected?

**Authority:** Which external data represents current supplier truth?

**Transport:** Were requests failing or succeeding?

**Pagination:** Did the importer retrieve every page?

**Semantics:** Did the parser preserve local business-date meaning?

**Ordering:** Did older webhook events overwrite newer state?

**Authentication:** Were token failures involved?

**Quotas:** Did backfills interfere with normal synchronization?

**Containment:** How would you prevent further incorrect publication?

**Recovery:** How would you rebuild the affected data safely?

**Verification:** What independent evidence proves the repaired data is complete, fresh, and correct?

### Senior-level challenge

Your interviewer says:

"The vendor API changed without warning. There's nothing we could have done."

Explain which vendor changes are outside Mercury's control and which failures could have been detected or contained through better contract validation, coverage checks, revision-aware updates, and reconciliation.

---

# STOP — Independent Investigation Ends Here

Do not read the following notes until you've attempted the exercises.

The objective is to distinguish transport success from data correctness and design a recovery that survives future vendor changes.

---

# Lab Diagnostic Notes

## Pagination

The broken importer stops when it receives a page shorter than its requested limit.

But that page still contains a continuation cursor.

The corrected importer follows the cursor until the documented completion condition.

## Date Semantics

The broken importer converts the timestamp to UTC and extracts the UTC date.

That changes the local November 3 hotel date into November 2.

Under the lab's confirmed fixture contract, the intended value is the supplier-local calendar date.

Real integrations must verify this interpretation before implementing it.

## Webhook Ordering

A newer event sets availability to zero at revision 3.

An older event later sets it to five at revision 2.

The broken consumer allows the older event to overwrite the newer state.

The corrected consumer stores delivery identity and source revision separately.

## Authentication

Rotating refresh tokens require coordinated credential management.

An authentication failure doesn't automatically establish token expiry.

Token refresh should not become an uncontrolled retry loop.

## Rate Limits

A shared integration quota needs shared admission control.

Backfills should not consume all capacity needed by normal synchronization.

Retry behavior should respect provider guidance and remain bounded.

## Snapshot Consistency

A complete cursor traversal may still observe data changing during the scan.

Use vendor-supported snapshots or a carefully designed baseline-plus-incremental protocol.

A naive watermark captured after the snapshot can create a gap.

## Webhook Security

Verify provider signatures according to the actual raw-body contract.

Store delivery identity durably before acknowledging acceptance.

Keep business processing separately retryable.

A valid signature doesn't establish that the payload is new, authorized for the target tenant, or semantically correct.

## Final Diagnosis

The simulated incident contains three independent failures.

Incomplete pagination.

Incorrect interpretation of a vendor-local date.

Stale webhook overwrite.

The original job's green status measured request execution rather than the integrity of the resulting dataset.

The corrected workflow verifies completeness, preserves business semantics, and rejects stale or repeated event effects.

---

# Further Reading

Primary references:

- **RFC 9110 — HTTP Semantics, including Retry-After:** https://www.rfc-editor.org/rfc/rfc9110.html
- **RFC 6585 — Additional HTTP Status Codes, including 429:** https://www.rfc-editor.org/rfc/rfc6585.html
- **RFC 9700 — Best Current Practice for OAuth 2.0 Security:** https://www.rfc-editor.org/rfc/rfc9700.html
- **GitHub — Webhook Best Practices:** https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks
- **GitHub — Validating Webhook Deliveries:** https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- **GitHub — Troubleshooting Webhook Delivery:** https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/troubleshooting-webhooks
- **AWS — Retry Behavior in SDKs:** https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html
- **AWS Builders' Library — Timeouts, Retries, and Backoff with Jitter:** https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- **OWASP — REST Security Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- **OpenAPI Specification:** https://spec.openapis.org/oas/latest.html
- **Python — `datetime`: Dates, Times, and Timezones:** https://docs.python.org/3/library/datetime.html
- **Python — HMAC:** https://docs.python.org/3/library/hmac.html

Related programme chapters:

- SE310-L01 — The Frontend–Backend Contract
- SE310-L03 — Application and Infrastructure Security
- SE320-L03 — Queues, Workers, and Asynchronous Workflows
- CS430-L01 — Distributed Systems and Partial Failure
- CS430-L05 — Designing Reliable Business Workflows
- SE325-L02 — Bulk Imports, Exports, and Background Data Operations
- SE325-L03 — Scheduled Jobs, Time, and Distributed Execution
- SE325-L04 — Production Data Repair, Audit, and Lifecycle
- SE325-L06 — API Protection and Multi-Tenant Fairness
- SE440-L01 — Observability: Understanding Production Systems

---

# Dense Cheatsheet — Interview Glance Card

*The following card is fenced for voice-reader skipping and screen-based revision.*

```text
SE325-L05 — SURVIVING THIRD-PARTY INTEGRATIONS
================================================

CENTRAL PRINCIPLE
-----------------
HTTP success != correct integration.

A vendor can stay available
while changing data semantics.

INTEGRATION RESPONSIBILITIES
----------------------------
Authentication
Authorization
Contract translation
Pagination
Rate limiting
Webhooks
Checkpoints
Validation
Reconciliation
Monitoring
Backfills
Vendor-change management

CONTRACT DRIFT
--------------
Field type changed
Field meaning changed
New enum value
Different currency units
Local date -> offset timestamp
Pagination behavior changed
Optional field removed
Identifier format changed

Valid JSON != valid business meaning.

ADAPTER
-------
Translate vendor representations
into internal domain concepts.

Keep vendor assumptions localized.

Avoid leaking raw vendor schemas
throughout application code.

DATES
-----
Local date != UTC instant.

Timestamp conversion may change
calendar date.

Interpret according to
documented business meaning.

PAGINATION
----------
Offset:
  positions may shift during scan

Cursor:
  follow documented continuation

Short page != final page.

Check:
  continuation token
  cursor cycles
  filters
  source revision
  snapshot guarantees

SNAPSHOT + CHANGES
------------------
Need a reliable handoff.

Capture consistent snapshot/watermark
or overlap and deduplicate safely.

Watermark after snapshot alone
may miss intermediate updates.

OAUTH
-----
Access token:
  typically short-lived

Refresh token:
  more privileged lifecycle

Refresh-token rotation:
  requires coordination

Do not log tokens.
Use least-privilege scopes.
Handle expiry and revocation.

HTTP FAILURES
-------------
401:
  authentication problem

403:
  permission/policy problem

404:
  resource unavailable by contract

409:
  state conflict

429:
  throttling/quota

5xx:
  server/intermediary failure

Timeout:
  outcome may be unknown

RETRY
-----
Bound attempts and elapsed time.
Respect Retry-After when applicable.
Use backoff and jitter.
Classify retryability.
Don't blindly repeat mutations.

RATE BUDGET
-----------
Per-key/tenant/account/endpoint
Shared budget for shared quota
Concurrency cap
Priority for live sync
Bounded backfill throughput

More workers can worsen throttling.

WEBHOOK INGRESS
---------------
HTTPS
Raw-body signature verification
Constant-time MAC comparison
Supported event/type validation
Tenant/resource authorization
Durable inbox
Quick acknowledgment
Async processing
Replay/deduplication protection

AUTHENTICITY != FRESHNESS.

DELIVERY VS BUSINESS IDENTITY
-----------------------------
Delivery ID:
  deduplicate same delivery

Source revision:
  reject stale state changes

Separate mechanisms.

LATE WEBHOOK
------------
New revision arrives first.
Old revision arrives later.

Never trust arrival order.

Use source revision or
retrieve current authoritative state.

POLLING + WEBHOOKS
------------------
Webhooks improve responsiveness.
Polling/reconciliation improve
completeness and recovery.

Both must obey same ordering rules.

BACKFILL
--------
Identify affected period.
Preserve source identity.
Use bounded requests.
Checkpoint durable progress.
Make corrections idempotent.
Respect quotas.
Verify resulting data.

SANDBOX
-------
Useful but not proof of
production behavior.

Test:
  volume
  schemas
  pagination
  token lifecycle
  rate limits
  duplicate events
  late events
  unusual dates

OBSERVABILITY
-------------
Transport:
  errors, latency, timeouts

Processing:
  received, accepted, rejected

Freshness:
  age of latest accepted source data

Completeness:
  coverage, missing IDs, page counts

Correctness:
  invalid values, revision regression,
  authoritative mismatch

Operations:
  quota usage, queue lag,
  retry rate, backfill backlog

SILENT CORRUPTION
-----------------
Green job
+ missing page
+ wrong date interpretation
+ stale webhook
= incorrect inventory.

INCIDENT RESPONSE
-----------------
1. Establish affected scope.
2. Stop defective overwrites.
3. Preserve safe evidence.
4. Confirm vendor contract.
5. Repair parser/pagination.
6. Reconcile source versions.
7. Backfill affected records.
8. Verify coverage and semantics.
9. Resume safely.
10. Monitor for recurrence.

ANTI-PATTERNS
-------------
"200 means correct."
"Short page means final page."
"Date strings are interchangeable."
"UTC date always equals hotel date."
"Signed webhook means newest state."
"Unique delivery ID solves ordering."
"401 always means refresh token."
"Retry every error immediately."
"Sandbox matches production."
"More requests improve backfill."
"Last sync completed means fresh."
"One generic adapter fits every vendor."

SENIOR MENTAL MODEL
-------------------
An integration is a maintained
contract across organizations.

Transport success is only one layer.

Completeness, meaning, freshness,
ordering and recovery determine
whether the data is trustworthy.

NEXT
----
SE325-L06
API Protection and Multi-Tenant Fairness
```
