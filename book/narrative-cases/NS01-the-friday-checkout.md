# NS01 — The Friday Checkout

*A reservation platform, a deceptively fast release, and the strange business of deciding when a booking is actually real.*

The company and events in this story are fictional. The engineering mechanisms are realistic; details such as traffic and timings are illustrative.

## Monday — A promise on the home page

At nine on Monday morning, AlderStay's product manager, Mira, opened the weekly meeting with a screenshot. The screenshot showed a hotel in Lisbon, a bright green button, and the words “Book now. Instant confirmation.” Below it sat a second screenshot: a customer support ticket from a family whose reservation had not been confirmed until seventeen minutes after payment.

Mira had been at the company long enough to know that these two screenshots contradicted each other. She also knew the marketing team had already paid for a campaign around instant booking. “What does instant actually mean?” she asked, turning toward the engineers. “Because the customers have one definition, and I have a feeling our software has another.”

Jonas, the backend engineer, explained their booking workflow. AlderStay did not own hotel rooms. It operated a storefront connected to several suppliers, each of which maintained its own inventory and reservation API. The customer's browser could see a room and a price, but the supplier ultimately decided whether that room was still available. AlderStay could reserve an internal slot in its own system, yet it could not force a remote hotel inventory system to agree.

Their current checkout performed too much work while the browser waited. It validated the selected room, asked the supplier whether it was available, authorized the payment, attempted to create the supplier booking, and wrote the result to PostgreSQL. Only then did it return a definitive response. A single slow supplier could stretch the operation beyond the patience of a browser, a load balancer, or a human.

The frontend engineer, Nika, proposed a cleaner experience. The user would press Book. The backend would validate the request, create a durable booking attempt, and return immediately with a tracking identifier. The page could then show a progress state while the rest happened asynchronously. “We can make it feel quick without lying,” Nika said. The last three words turned out to be more important than the first five.

Mira wanted to know whether the architecture could support the campaign. Jonas answered with an uncomfortable distinction. “We can return quickly. We cannot guarantee the supplier will confirm quickly. So we can promise fast acknowledgment, not guaranteed instant confirmation.” They changed the wording for the release from “Instant confirmation” to “Booking in progress, usually confirmed shortly.” Marketing complained, but the lawyer attending the meeting looked relieved.

There was a second issue. The team measured backend handler time because it was easy to measure, and page-loading time because the browser provided it. Neither metric described the business outcome: the time between a customer submitting a booking and receiving a supplier-confirmed reservation. Mira asked analytics to add that interval as a product metric. It was the first architectural decision of the week, although nobody had drawn a box or chosen a technology.

## Tuesday — The hotel page is not the booking

Nika started by tracing the journey of a hotel page. A visitor in Sweden entered a URL. DNS located an address for AlderStay's CDN. The browser established or reused a connection, negotiated HTTPS when necessary, and requested the document. The CDN could deliver cached images, styles, and JavaScript without touching the origin application. The hotel page itself contained a mixture of public descriptions, prices, and live inventory hints.

The distinction mattered. A hotel description changed perhaps twice a year. A room's availability could change between the moment somebody saw it and the moment they pressed Book. Caching those two things with the same policy would either make the website painfully slow or mislead customers. Nika kept public photographs and versioned JavaScript aggressively cacheable. For prices and availability, the frontend used a short-lived API response as a hint, not as a promise.

A colleague asked whether they could simply disable all caches. Nika said they could, in the same way they could improve traffic safety by banning every car. It would solve one problem by creating several others. The right question was not “cache or no cache” but “which facts may be stale, for how long, and what must be revalidated before money changes hands?”

The new checkout would use one browser request rather than a chain of dependent calls. Previously the frontend requested a quote, then a coupon adjustment, then a shipping-like fee calculation, then payment setup. Each call could be quick in isolation while the browser paid a network round trip for each dependency. The new backend endpoint could coordinate work close to the databases and partner services, returning one coherent checkout proposal.

Nika was careful not to pretend that combining requests made all work disappear. If the backend still had to call a distant supplier four times in sequence, those four calls remained. But moving orchestration away from the browser made it easier to parallelize independent reads, cache stable inputs, enforce a single authorization decision, and present a response the page could understand as one object.

There was a security wrinkle. A customer could edit the price displayed in a browser request, because anything on the client side was ultimately under the customer's control. The backend had to recalculate the amount from authoritative pricing rules. The same principle applied to hotel identifiers, discounts, and customer ownership. Frontend validation was helpful feedback. It was not the boundary that protected the business.

They also reviewed their CORS configuration after a development build failed when the frontend ran on another port. The backend returned valid JSON, and `curl` could read it, but the browser refused JavaScript access because the server had not granted that origin permission. Jonas fixed the explicit development-origin policy rather than disabling browser protections or enabling a wildcard across every environment. The episode lasted twenty minutes and left no exciting postmortem. That was what a correctly scoped fix looked like.

By evening, the page was noticeably faster in the test environment. Its network waterfall had fewer dependent calls. Yet the most consequential line of code was not in the frontend. It was the line that decided which state to write before telling the user anything.

## Wednesday — The state nobody wanted to name

The developers met with a whiteboard full of booking states. The first version said “new, success, failed.” Jonas erased it. Their real workflow could be accepted locally but not yet accepted by the supplier. Payment could be authorized but not captured. Inventory could be held, then released. A supplier might succeed after AlderStay had already stopped waiting. A timeout did not reveal whether the remote operation happened.

After an hour, the model had named transitions: requested, inventory held, payment authorized, supplier pending, supplier confirmed, capture pending, confirmed, cancellation required, and failed. Not every state appeared on the customer's screen. Some existed so a worker could recover from an interrupted attempt. Others existed so support could tell whether a payment needed reconciliation rather than a blind retry.

PostgreSQL carried the booking's authoritative state. The team considered a document database because supplier payloads were flexible, but this was not primarily a flexible-document problem. Booking identities, inventory constraints, payment attempts, and customer ownership had relationships and invariants. They were already comfortable with relational transactions and unique constraints. They kept the essential booking ledger there and stored raw partner payloads separately where they were useful for diagnosis.

An important design decision emerged from a race. Two customers could see the last available room, click at nearly the same moment, and both try to reserve it. If the application read a remaining count of one, checked that it was positive, and then independently updated the row, both requests might believe they succeeded. A database transaction did not automatically make that application logic safe under every isolation arrangement.

Jonas proposed an atomic conditional update: reserve a unit only if the inventory counter was still positive, and check whether the database actually changed a row. A unique constraint would prevent the same business attempt from being recorded twice. Where inventory came directly from suppliers rather than AlderStay, the internal hold was still only a local guardrail. The supplier's final confirmation remained authoritative for the external reservation.

The queue was the next decision. Long supplier calls would move to a worker process. The API would create the booking attempt and enqueue work. That sounded easy until Tomas, the platform engineer, asked what happened if the database commit succeeded and the process crashed before publishing the queue message. The booking would exist, but no worker would ever hear about it.

Someone suggested publishing first. Tomas asked what happened if the queue accepted the message and the database transaction later failed. The worker might operate on a booking that did not exist. This was the dual-write problem: one logical event had to affect two independent systems that could fail at different moments.

They chose a transactional outbox. In one PostgreSQL transaction, the API inserted the booking attempt and an outbox row describing the work to publish. A separate publisher delivered those rows to the queue, retrying when necessary. The publisher was allowed to send the same event more than once. That meant the consumer needed to recognize repeated work by business identity rather than assume one message equaled one business operation.

The supplier API was less accommodating. It supported booking references but did not offer a universal idempotency-key contract for every reservation action. AlderStay would persist an external reference and query the supplier for its state before reissuing ambiguous requests. This did not create mathematical certainty when the supplier's own API was inconsistent. It created a careful, auditable strategy for reducing uncertainty.

At the end of Wednesday, the architecture was more complicated than Monday's fast checkout mockup. But the complexity was not decorative. Each piece represented a specific failure they had decided not to hide from the customer.

## Thursday — A release is a coordinated change

The merge request looked smaller than the discussion. A handful of frontend files, a new backend endpoint, a migration adding booking-attempt states, a worker handler, and some infrastructure configuration. Yet the change crossed four deployable units and a database schema. Its true size was measured in coordination, not line count.

Tomas worked with the release manager, Elena, to establish a safe deployment order. They expanded the database schema first, adding new columns and values without removing what the old application still needed. The old and new backend versions could coexist during rollout. The new code learned to read old records. Only after traffic moved and the new behavior stabilized would they consider removing obsolete columns or states.

Why bother? Because a rollback of application containers is not automatically a rollback of the database. If new code writes records that old code cannot understand, redeploying yesterday's image may replace one incident with another. The team used an expand-and-contract migration, delaying destructive cleanup until compatibility had been proven.

Continuous integration ran tests, type checks, and a contract test ensuring the frontend could interpret every booking state the API might expose. A deployment pipeline built immutable images and promoted them between environments. Elena asked for a feature flag around the new checkout path. It would let the team disable the new behavior without inventing an emergency rebuild while customers waited.

The tests were not perfect. One happy-path integration test mocked a supplier that always responded promptly. Another covered an immediate supplier failure. Nika added a test for a delayed response, in which the user refreshes the page and the UI reconstructs the correct booking state from the server rather than from stale in-memory state. That test caught a bug where a green success banner appeared whenever the HTTP request returned successfully, even though the body said the booking was still pending.

The frontend bug illustrated a subtle contract error. HTTP 202 meant the request had been accepted for processing. It did not mean the supplier booking was confirmed. The UI had treated transport-level success as business-level success. Nika changed the page to show a clear pending state, a booking-reference link, and a status update mechanism. A simple polling endpoint was sufficient; there was no need to deploy WebSockets merely because progress could change.

Elena arranged a limited rollout for Friday morning. Five percent of bookings would use the new flow. Support had the escalation procedure, payments had a reconciliation report, and engineering had a dashboard showing pending-state duration, queue age, supplier errors, and confirmed bookings. They were not measuring just server health. They were measuring whether customers got what they thought they bought.

At five Thursday evening, Mira asked whether they were ready. Jonas said yes, with one caveat: “We are ready to observe the system honestly. That's not the same as being guaranteed a quiet Friday.”

## Friday, 09:12 — The first small lie

The first half-hour looked good. The 95th-percentile latency of the new checkout endpoint fell sharply because it no longer waited for every supplier operation. The frontend showed progress promptly. Support reported fewer customers refreshing the payment page in panic. The business metric—time to actual confirmation—improved modestly, not dramatically. That difference was expected.

At 09:12, a supplier in southern Europe began responding slowly to reservation requests. The reason was outside AlderStay's control. Some requests took two seconds, others twenty, and a few timed out after the supplier had already created a booking. The queue accumulated work. The new system's ability to accept requests quickly was suddenly working against the assumption that suppliers would keep pace.

A dashboard showed green API latency, yellow queue age, and rising pending bookings. A customer-facing metric lagged behind by a minute. Mira noticed first that the support queue had started climbing. “If our API is fast,” she asked, “why are customers calling?” The answer was that the API was doing a different job than the customer expected. It was accepting work, not finishing it.

At 09:18, the first serious incident appeared. A worker was handling booking B-3184. It called the supplier, received no response before its timeout, and attempted a reconciliation lookup. Before the lookup finished, its container was terminated during a rollout-related restart. The queue eventually redelivered the job. A new worker began processing the same logical booking.

This was normal for an at-least-once delivery system. The surprising part was that the worker implementation used a fresh generated operation identifier on every attempt. It had treated the message delivery as the identity of the business action. The same booking could therefore produce more than one outward request if the first outcome was uncertain.

A second supplier booking appeared. No second payment had yet been captured, but the company had reserved two rooms at the supplier for one customer. The unique constraint in PostgreSQL prevented two local booking records. It did nothing to prevent two external side effects. A local database guarantee could not reach across the network and enforce the behavior of a separate organization.

Jonas was tempted to retry harder, assuming the reconciliation query was merely slow. Elena asked the team to stop changing timeouts until they knew whether the first reservation succeeded. That intervention mattered. Making every timeout longer might tie up workers and keep the queue from draining; making every retry more aggressive might create more duplicates.

They paused new traffic through the feature flag, preserving already accepted attempts. Support received a clear instruction not to tell customers that pending reservations had failed. Payment operations were checked for duplicates, and the supplier was contacted about the conflicting reference. The company would rather spend an hour reconciling facts than spend a week refunding avoidable charges.

## Friday, 10:04 — Follow the booking, not the dashboard

At ten, the incident channel contained screenshots, logs, and several contradictory explanations. One engineer blamed Redis because the availability cache still showed the room. Another blamed the queue because it had redelivered work. Another wanted to scale worker replicas. Each explanation contained an observation but skipped the question of what behavior was actually wrong.

Tomas drew a timeline around one business identifier. At 09:17:55, PostgreSQL committed booking B-3184 and its outbox event. At 09:17:56, the publisher sent the event. At 09:18:01, a worker contacted the supplier. At 09:18:16, its request timed out. At 09:18:19, the worker process died before the reconciliation result was recorded. At 09:18:27, the queue redelivered the job. At 09:18:29, another supplier request was issued with a new external operation reference.

That timeline was more valuable than a thousand general CPU metrics. It revealed precisely which assumption had failed: a queue attempt was being treated as a unique business operation. The correct identity had to be stable across retries. When supplier status was ambiguous, the system needed a durable intermediate state and a controlled reconciliation path, not another casual create call.

Nika asked whether the cache had contributed. Not to the duplicate supplier reservations. Redis had made availability hints stale during the slowdown, but checkout revalidated before committing a local hold. The cache could mislead a visitor about what looked available; it did not own the business invariant. They added a freshness indicator for the UI, but they did not call that a fix for the duplicate side effect.

The team then looked at scaling. The queue had twenty thousand pending jobs; adding workers would increase throughput only if the supplier could accept the extra requests. In fact, more concurrency against an already struggling supplier could amplify the incident. Tomas limited outbound concurrency for that supplier, applied jittered backoff to safe retries, and protected capacity for reconciliation work. The goal was not maximum requests per second. It was maximum successful, correctly resolved bookings per minute.

There was another operational subtlety. The queue metrics measured message age and attempts, but the business dashboard measured bookings by customer-visible state. A high count of retried messages did not necessarily mean a high count of customers harmed. Conversely, an empty queue did not prove every customer had a valid reservation. The team needed both infrastructure and domain metrics, connected by stable identifiers.

At 10:45, they deployed a narrow fix. The worker now persisted and reused a stable business operation reference. An ambiguous timeout moved the attempt into a reconciliation state; the processor first looked up any prior supplier outcome and escalated to a manual workflow when the supplier could not provide certainty. Additional tests deliberately killed workers between external success and local persistence. The tests could not create an absolutely failure-proof supplier, but they exposed the precise crash window that had been missed.

The company resumed the five-percent rollout after confirming the repaired path on a small batch. Elena did not expand it to fifty percent merely because the new deployment passed CI. The business metric, supplier-confirmation time, error rates, and reconciled duplicates needed time to settle.

## Friday afternoon — Support is part of the architecture

By two o'clock, the finance team had identified the handful of customers whose supplier records required reconciliation. Some had one local booking but two supplier confirmations. A few had an authorization that remained open despite a canceled booking. The operations team needed to distinguish authorizing a payment from capturing it; an authorization was not yet settled money. They worked through the provider's records instead of treating every duplicate-looking line in a log as a double charge.

Leila from support asked why she had to copy booking identifiers between three administration screens. One showed the customer's request, another showed the supplier reservation, and a third showed the payment state. The screens had been designed around the teams that owned them, not around a customer who wanted one answer. Leila could not promise a refund, rebooking, or confirmation without calling somebody in engineering.

Elena was tied up in the rollout call, so Jonas and Nika built a modest incident view using existing APIs: one business identifier, a timeline of state transitions, and links to authorized payment and supplier records. It was not a heroic new dashboard. It was a way to expose the same state machine to people who had to explain it to customers. Sensitive payment details stayed behind role-based authorization; support did not need unrestricted access to internal logs.

The support view revealed a final problem with the company's metrics. Engineering had counted the number of failed HTTP requests. Customer support had counted the number of conversations. Neither exactly counted affected bookings: one customer might retry ten times, while another might receive a successful HTTP response for a booking that stayed pending. The teams agreed to group incidents by stable business identity and outcome. Only then could they tell whether the release was actually improving customer experience.

AlderStay's architecture had gained one more boundary: the point at which engineering facts became an explanation another human could act on. That boundary, too, needed a contract.

## Monday again — What the company actually learned

The following Monday, the postmortem was not titled “RabbitMQ failure,” “Redis bug,” or “Frontend incident.” It was titled “Ambiguous supplier outcomes during asynchronous checkout.” That title described the business reality without pretending a single technology had caused the entire problem.

Mira began with the customer journey. The faster interface had genuinely improved the feeling of responsiveness. It had not shortened the supplier's slowest operations, and it had accidentally made an incomplete state more visible. The team revised help text so “pending” sounded like an honest status rather than a euphemism for failure. Support got an internal view of each transition and its evidence, not just a green or red badge.

Jonas explained the transaction boundary. PostgreSQL could enforce a unique booking attempt and atomically record an outbox event. It could not make the payment provider, supplier, queue, and browser participate in one perfect database transaction. Reliability had to come from durable state transitions, stable business identities, bounded retries, reconciliation, and explicit uncertainty.

Nika explained the frontend boundary. The browser was free to display a useful pending view, retry a safe status read, or reconstruct progress after refresh. It was not free to invent a confirmed reservation because an HTTP handler returned quickly. They had changed the interface from an optimistic declaration to a truthful account of current knowledge.

Tomas explained the platform boundary. Containers could restart; messages could be redelivered; networks could time out without revealing whether remote work completed. The infrastructure was not obligated to behave like a local function call, even if the application code made it look like one. Scaling a struggling dependency was not necessarily helping it. Health checks and dashboards needed business-specific meaning.

Elena explained the release boundary. The feature flag had contained the blast radius, backward-compatible schema changes had made rollback possible, and staged rollout had bought the team time to notice the mismatch between technical and business success. CI had done its job within the assumptions encoded by the tests. The job of engineering leadership was to question which assumptions had not been encoded.

Nobody recommended rewriting the platform as microservices. The application already had enough independently failing components. The team planned to strengthen the existing modular boundaries, keep booking truth in a transactional store, cache only appropriate read models, and automate reconciliation where the supplier interfaces allowed it. A new architecture diagram would not have made an uncertain external outcome certain.

Later that afternoon, Mira showed the same hotel page from the previous Monday. The button now said “Request booking.” The next screen said “We're confirming your room,” followed by a reference number and an honest status. The page was a little less magical and a great deal more trustworthy.

The technical story had begun with an apparent frontend performance problem. It had traveled through DNS, CDNs, API design, caches, database transactions, queues, cloud deployments, external payment and inventory services, observability, and the responsibilities of several teams. No single component was especially mysterious. The challenge was remembering that they all participated in one customer's attempt to buy one room.

That, more than shaving another forty milliseconds from a handler, was what the company had finally learned to optimize.

*The spoken story ends here.*

---

## Behind the story — optional screen reference

**Interdisciplinary touchpoints:** CS230-L01 (web request), CS230-L09 (CDNs and load balancers), SE240-L02 (frontend architecture), SE240-L03 (state), SE310-L01 (contracts), SE310-L02 (browser security), SE320-L01 (backend anatomy), SE320-L02 (caching), SE320-L03 (queues and outbox), CS330-L01 (relational modeling), CS330-L03 (transactions), CS430-L01 (partial failure), CS430-L05 (business workflows), SE330-L01 (architectural trade-offs), SE340-L04 (CI/CD), SE440-L01 (observability), SE440-L02 (incidents), SE215-L11 (release management). These links identify **connections**, not a prerequisite list.

**Important distinctions:** An HTTP 202 is not a confirmed booking. Queue redelivery is expected under at-least-once semantics. Idempotency must cover the business side effect, not just the local record. Supplier reconciliation is necessary when a remote outcome is uncertain. A staged rollout and a feature flag limit impact but do not replace correctness.

**Optional reflection:** Which state transitions must never be ambiguous? Which measurements described the user's experience rather than the API's? If the supplier never provides reliable lookup or idempotency, what guarantees can AlderStay honestly offer?
