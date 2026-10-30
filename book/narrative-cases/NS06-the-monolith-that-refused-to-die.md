# NS06 — The Monolith That Refused to Die

*A growing B2B company is told it needs microservices. Its engineers ask what problem the new architecture would actually solve.*

This is a fictional company and a fictional sequence of events. Technical choices are plausible examples, not a prescription for every team.

## Monday — The architecture diagram at the board meeting

Waymark sold software to industrial distributors. Customers ordered replacement parts, tracked warehouse inventory, managed warranties, and arranged deliveries through a browser and a collection of APIs. The business grew steadily, which was good. Its engineering organization had grown less steadily, which was becoming a problem.

At an investor meeting, a consultant displayed a slide showing a large rectangle labeled “Monolith” with a red cross over it. Beside it sat an elegant cloud of tiny service boxes: orders, inventory, customers, catalog, billing, analytics, and notifications. Arrows connected everything. The title read “Architecture for Scale.”

Adrian, Waymark's CTO, returned to the office with a question for his engineering lead, Simone: “Are we behind because we're still a monolith?”

Simone refused to answer immediately. Their system was a substantial Node.js application with PostgreSQL, Redis for a few caches, RabbitMQ for background jobs, and a React frontend. Most code lived in one repository. They deployed the backend as one unit, but its code had boundaries of varying quality. Some modules were clean. Others had grown into sprawling services that knew how to modify orders, read inventory, email customers, and generate reports.

“The architecture is behind where we need to be,” Simone said, “but that doesn't tell us whether microservices are the fix.”

Adrian pointed to the slide. An investor had asked whether separate teams could release independently. They could not, at least not safely every time. A change to warehouse allocation frequently required coordination with orders and billing. CI took forty minutes. A harmless change in customer preferences occasionally blocked a critical release because a flaky integration test failed in an unrelated module.

Simone agreed these were real costs. She wanted to measure them before making them worse in three different ways.

## The first measurement was not CPU

Simone organized two weeks of engineering archaeology. Theo, a backend developer, reviewed the repository's dependency graph. Mara, a platform engineer, examined deployment and CI history. Clara, the product lead, described where projects stalled while waiting for other teams.

The repository's worst problem was not size. It was direction. A module called `shared` had become the place where nobody needed permission to put code. Inventory imported an order helper. Orders imported inventory models. Reporting imported half the database layer and occasionally wrote back into transactional tables because somebody needed to fix a derived status quickly.

The organization appeared to have seven domains. The code effectively had one large domain named “everything.”

Theo proposed a simple first step: make each business capability own a small public interface, with internal models private to that module. Instead of reaching into another module's tables, a caller would request a business operation. They didn't need a network call to enforce a boundary. A plain in-process function or module API could work, provided the team controlled dependencies and tests.

They mapped business invariants. Orders and inventory were tightly connected because an accepted order needed a credible inventory reservation. Billing and notifications could often proceed asynchronously after a durable order transition. Analytics was a reader of business events, not an owner of order status. Customers and permissions cut across many capabilities but did not justify copying authorization rules into every controller.

The big surprise was that the expensive change collisions clustered around three files and two tables, not around the whole monolith. A report aggregating pull-request history showed that most of the repo was rarely modified. The hotspot modules changed daily and were touched by three teams.

Simone took the report to Adrian. “Breaking every module into a service would move the hotspot into the network. It wouldn't necessarily make the hotspot disappear.”

## The Friday incident nobody wanted to reproduce

Before the architecture review, Simone asked the team to reconstruct a failed release from the previous month. The release had improved warehouse inventory reconciliation. Unit tests passed and the API initially looked healthy, but some customers received duplicate shipping confirmations.

Theo followed the path. The order service wrote the shipping transition to PostgreSQL and called a notification helper that immediately sent an email. If the mail provider accepted the message but the local request timed out, the service raised an error. A job retried the entire workflow. The second attempt found the shipment already marked ready, but the notification helper ran again because its own state had not been recorded durably.

The bug wasn't caused by the monolith. Extracting notification to a separate service without defining the side-effect contract could have made it even harder to diagnose. The issue was an ambiguous outcome across a remote boundary and a retry policy that confused “I didn't hear success” with “nothing happened.”

They moved notifications to a durable work record keyed by the business action, designed the worker to tolerate duplicate delivery, and introduced reconciliation where the provider could not guarantee exactly-once notification. Customer support could now see whether confirmation was pending, attempted, or confirmed under the available provider contract.

Simone also changed the incident review format. It named the failed assumption, the evidence supporting the diagnosis, and why the previous tests missed it. Nobody was scored for having guessed the bug first. The goal was to make invisible boundaries visible before an incident, not to reward the loudest person during one.

At the next sprint planning meeting, Clara asked whether every customer workflow should now be asynchronous. Theo said no. That would introduce extra states, queues, delayed feedback, and operational complexity where a straightforward synchronous request would do. The useful decision was to isolate work whose latency, retry behavior, or failure tolerance differed from the core transaction.

## Tuesday — One order, four truths

To test the proposed boundaries, the team followed a single order. A customer selected a spare motor, placed an order, and received an ETA. Inventory recorded a reservation. Billing created an invoice. A warehouse worker printed a pick list. Analytics recorded a sale. Each step was connected, but not every step needed to happen atomically.

Theo drew a timeline: accepting an order required checking inventory and committing a reservation without overselling. Sending an email could fail without making the accepted order nonexistent. Analytics could lag. A shipping estimate could be updated later. The system needed to state which facts were authoritative and when they became true.

The monolith's PostgreSQL transaction currently updated order and inventory rows together. That was convenient and strong. Splitting orders and inventory into separate databases would make the operation a distributed workflow, with retries, uncertainty, and compensation. It might eventually be justified. But it would not be free.

A developer suggested publishing an `OrderCreated` event and letting inventory reserve stock afterward. Simone asked what the customer should see between the event and the reservation. Would the website say an order was accepted when stock might be unavailable? The room had no agreed answer. Changing architecture would change the business contract.

Clara explained that Waymark sold emergency parts for factories where a machine stopped working until the part arrived. Customer support would rather say “we are checking availability” than promise a component that did not exist. The team kept stock reservation inside one authoritative transactional boundary for now. It decoupled notifications and reporting from the synchronous path.

That was their first architectural decision: **don't distribute a business invariant casually just because a box on a slide looks too large.**

## Wednesday — The monorepo wasn't the enemy either

The platform team had a different frustration. CI ran nearly every test after nearly every change. Developers complained that the monorepo made builds slow, but Mara discovered the build system lacked dependency-aware caching. A change to a frontend icon triggered backend integration tests. A change to a documentation file rebuilt container images.

They introduced a better build graph and isolated test suites by package while preserving a smaller end-to-end set for cross-module behavior. Shared contracts still triggered the tests that depended on them. A nightly broader suite caught integration changes that escaped narrower checks.

The first attempt made CI faster but less trustworthy. A test for order reservation was excluded because it sat under the reporting module, where someone had placed it years earlier. Mara caught the mistake after inspecting which tests had run. They adjusted the ownership map and made test selection observable, not an opaque optimization.

A junior engineer asked whether splitting into microservices would make the pipeline faster. Mara laughed. It would create several pipelines, each with deployment, versioning, security, observability, and integration concerns. Parallel builds could help, but the company already had ways to reduce unnecessary work without deploying twenty separate systems.

On Thursday, Adrian asked about independent team ownership. Simone proposed module ownership first: clear maintainers, APIs, dependency rules, code review responsibilities, and an architectural decision record for exceptional cross-boundary access. A modular monolith could give the company meaningful ownership boundaries without imposing network and data-consistency boundaries prematurely.

That would not satisfy investors who treated microservices as a sign of maturity. It might satisfy customers who cared whether orders worked.

## The disagreement about team autonomy

Adrian arranged a workshop with the heads of orders, warehouse, and customer operations. Each wanted the ability to ship independently. The orders team complained that a change to billing often blocked their deployment. The warehouse team complained that shared entities changed without notice. Customer operations complained that every release introduced an unfamiliar error message it had to explain to buyers.

Simone gave the groups a concrete exercise. Suppose the warehouse team wanted to replace the algorithm used to allocate stock across depots. Which other teams needed to care? It depended on the promise exposed by the inventory interface. If that interface still guaranteed that a reservation either succeeded or failed with a stable reason, the allocation algorithm could change internally. If it changed when an order was considered accepted, then it was a business contract change requiring coordination.

They wrote boundaries in terms of responsibilities and invariants, not just folders. An inventory module owned reservations and available-to-promise quantities. An order module owned customer-facing order lifecycle. A billing module owned invoicing and payment reconciliation. No module could modify another's tables without an explicit architectural exception and review. That sounded bureaucratic until it reduced accidental coupling in the very next pull request.

Adrian asked whether separate teams could really be autonomous in a shared deployment. Simone admitted the limitation. They still had coordinated release timing and shared runtime risk. But autonomy was not binary. Teams could gain independent design authority, clearer contracts, targeted tests, and fewer accidental dependencies before paying for the full cost of separately deployed services.

This wasn't an argument against microservices. It was an argument for earning them. The organization could separate a domain when its operational and organizational needs justified the new network boundaries, not when a consultancy diagram needed another box.

## The service that really did want independence

Not every proposed service boundary was bad. Waymark's catalog search was becoming computationally expensive. Product data came from thousands of suppliers, each sending spreadsheets, API updates, or nightly feeds. Cleaning descriptions, matching part numbers, and building search indexes took hours. In the monolith, the import jobs shared process memory and deployment cadence with customer APIs.

One afternoon a supplier uploaded a badly formatted file containing millions of duplicated rows. The import worker exhausted its memory allowance. The container was killed. The application had to restart, briefly affecting order placement even though nobody was placing an import order.

Mara inspected the metrics. The container had hit its cgroup memory limit while average CPU remained modest. The operating system could kill a process for exceeding a memory constraint even if the host had unused resources elsewhere. Adding more backend instances would reduce some blast radius, but not the fundamental coupling between long-running imports and interactive requests.

This was a better extraction candidate. Search-index building had different scaling needs and different failure tolerance. Its outputs were derived from authoritative catalog records. Rebuilding them could be retried. A failed import should not take the order API with it.

Theo designed a separate worker deployment that consumed durable jobs from a queue, wrote cleaned records to staging storage, and published a versioned catalog index only after validation. The queue allowed the import rate to be controlled. Backpressure prevented one supplier from monopolizing the system. Work could be retried, but the idempotency key was the supplier feed and import version, not an arbitrary message-delivery identifier.

The worker still lived in the monorepo initially. It shared some libraries and contracts but deployed independently. The lesson was subtle: a separate deployable process is useful when there is a concrete reason; it does not require the organization to immediately convert everything into a network of mutually suspicious microservices.

## The false simplicity of events

As the new catalog pipeline took shape, a developer added a database write and then published a queue event saying the import was available. In testing, both operations worked. Mara asked what would happen if the process committed the database write and crashed before sending the event.

The event would be missing. Downstream search would never learn that the new version existed. If the order were reversed—send the event first, then commit—the consumer could react to a change that never became authoritative.

They adopted a transactional outbox for relevant state changes: the business update and an event record were written in one database transaction. A publisher later delivered the outbox record, possibly more than once, and consumers processed it idempotently. The approach did not make networks perfectly reliable. It made failure recoverable without losing the distinction between committed truth and attempted notification.

Clara wanted to know why a message could arrive twice if it was “reliable.” Theo explained that delivery systems often prefer redelivery over silently losing work. A consumer can crash after doing the action but before acknowledging the message. The queue sees no acknowledgment and may send it again. Reliability requires designing what repetition means, not pretending it never happens.

They added an import status resource so the frontend could show queued, processing, validating, published, or failed states. A user's browser did not need a live connection for the full import. It could reconnect and retrieve the latest durable status, and the team chose simple polling at first instead of implementing an elaborate real-time system merely because the feature ran asynchronously.

## A review of the code no human wrote

Theo had begun using an AI coding assistant to refactor the catalog importer. It quickly produced an attractive set of modules, interfaces, and unit tests. It also changed an internal helper so that two concurrent imports could publish the same catalog version. The tests passed because the assistant had mocked the publisher and never modeled the race between two workers.

Simone liked the speed, but asked a different question from “does the generated code look tidy?” The feature needed a stable import identity, an authoritative publication transition, a bound on concurrent work, and a way to recover after a worker died. They wrote those as acceptance criteria before asking the coding tool for another revision.

The revised implementation used a conditional database update to claim a publishable version and declined competing claims that no longer met the expected state. Its integration test created two concurrent workers and verified that only the valid version became visible. It also tested restart after a crash between preparation and publication.

Theo learned to use AI as a fast implementer within a carefully defined engineering decision, not as an architect whose confidence proved correctness. The code assistant knew dozens of patterns. It did not know which product promise Waymark intended to preserve unless someone explained it and wrote tests around it.

This turned out to be a useful leadership lesson for the entire team. Engineers were valuable not only because they remembered syntax, but because they could identify the invariant, anticipate realistic failure paths, and evaluate whether the implementation respected the system's actual responsibilities.

## An API contract is an organizational agreement

To make the modular boundaries real, Simone had the teams publish simple contracts for the most important operations. An inventory reservation returned a stable identifier and an explicit result. An order acceptance operation had clear preconditions. A reporting module could read published projections but could not quietly update order rows. Each contract named an owner and described the behavior other modules could depend on.

Theo noticed the same language appearing in customer support documentation. When an order remained pending, support needed to know whether stock had been reserved, billing had failed, or shipping was awaiting confirmation. The internal state machine was not merely a coding pattern. It determined which explanations the business could truthfully give customers.

One version of the order API returned a generic `500` when stock allocation failed. Simone said the error code hid a meaningful business outcome. A failure to reserve stock was not necessarily an infrastructure crash; it could be a valid conflict. The team refined the response contract to distinguish invalid input, unavailable inventory, and unexpected server failures. That helped the frontend display useful actions and helped operations triage genuine outages.

They also changed how they evaluated proposed abstractions. Every new interface had to buy something: isolating a dependency, expressing an invariant, reducing coupling, or protecting tests. A generic base repository for every entity wasn't automatically architecture. Neither was a framework that made developers write six files before they could express a single business rule. The architecture review began asking what complexity each abstraction removed and what complexity it introduced.

Clara appreciated this less glamorous design discipline. It meant a feature request could begin with a user outcome and become a precise responsibility without turning into a contest over whose favorite technology deserved another deployment.

## The migration nobody could finish in a weekend

The modular boundary work exposed a problem in customer data. Two product modules shared a table that mixed customer identity with warehouse-specific delivery preferences. Both wrote different columns, and a scheduled job periodically normalized addresses. The table wasn't huge, but the assumptions around it had become impossible to state clearly.

Theo proposed splitting delivery preferences into a module-owned table with a stable customer reference. Instead of rewriting every caller at once, they introduced the new representation alongside the old one, backfilled existing data, and added a compatibility path. They measured which callers still depended on the original columns before planning removal.

A migration script wasn't the whole change. Old workers might run during the transition. Reporting jobs could read stale formats. A rollback needed to preserve newly written information. Simone required a dry-run on representative data, checks of counts and invariants, and a way to pause without losing the ability to serve customers.

During the review, an engineer asked why they didn't perform the split as one large transaction and lock the table until it finished. On a busy production system, that could create long waits and block ordinary writes. They used smaller controlled steps where possible, with explicit handling for concurrent changes and reconciliation afterward. A clean code architecture was useful only if the database could reach it without stopping the business.

The team finally understood why architectural evolution often looks slower than a rewrite on a slide. Real systems carry users, data, old clients, and operational obligations along with their code. You can refactor a function in an afternoon; you cannot demand that yesterday's stored business facts disappear on the same schedule.

## The architecture review that included accounting

Six weeks later, Adrian asked for a cost comparison. The microservice diagram had promised unlimited scale, but Waymark's actual problems had concentrated in developer coordination and batch-job isolation.

Mara brought numbers. Their cloud bill included container compute, PostgreSQL capacity, storage, queue operations, observability ingestion, and network transfer. Splitting every domain into a standalone service would add idle capacity, more deployments, more cross-service calls, and a larger on-call surface. Some costs could fall if services scaled independently, but only when the workloads truly differed and the organization operated them well.

Simone presented a decision record. They had strengthened internal boundaries, reduced CI time, extracted catalog processing, and left the core order/inventory transaction together. They would revisit separation when independent scaling or team ownership produced evidence strong enough to justify the operational and consistency costs.

Clara made a different observation. Product delivery had improved even before the catalog worker shipped. Teams had clearer contracts and stopped modifying one another's data silently. Fewer cross-module surprises meant less time debugging changes that were supposedly unrelated.

Adrian asked whether he could call this a microservices migration in the board report. Simone said he could call it an architecture modernization, which was both less fashionable and more accurate.

The investor deck eventually showed fewer boxes, not more. It described the system as a modular core with independently deployed workloads where needed. This was not an ideological victory for monoliths. It was an engineering decision based on explicit invariants, observed bottlenecks, team boundaries, and the cost of failure.

The monolith had refused to die because nobody had established that killing it would help. Once the team understood which parts genuinely needed independence, the architecture evolved without a funeral.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Connections:** SE330-L01/L02/L03 (architecture, patterns, evolution); CS430-L01/L04/L05 (partial failure, boundaries, workflows); CS330-L01/L03 (data ownership and transactions); CS340-L01/L06 (search/derived systems); SE320-L01/L03 (backend architecture, queue); CS320-L04 (memory limits); SE215-L01/L02/L03/L04 (teams, delivery, monorepos); SE340-L02/L04 (containers and CI); SE440-L01/L03 (metrics and tests); SE240-L02 (frontend architecture).

**Technical caveats:** A modular monolith needs enforced boundaries, not just folder names. An outbox addresses the local dual-write gap but still demands idempotent publication and consumption. Extracting a worker deployment can improve failure isolation without implying every module needs its own database.

**Optional reflections:** Which invariant makes orders and inventory hard to split? What observation justified extracting catalog imports? How would you know when a modular boundary has become worth turning into a network boundary?
