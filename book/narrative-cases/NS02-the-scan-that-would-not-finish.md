# NS02 — The Scan That Would Not Finish

*A security platform with plenty of servers, an unreliable progress bar, and a database query that got slower after every successful day.*

The company and events are fictional. Systems and engineering trade-offs are representative, not an account of any real employer.

## Monday — The customer sees eighty-nine percent

The latest customer complaint arrived in three parts. First, a screenshot of a security dashboard stuck at eighty-nine percent. Second, a CSV export containing only a fraction of the findings shown on the screen. Third, a short message from the customer's security director: “If I cannot tell when your scan is finished, I cannot tell my board what is exposed.”

Northlight Security sold an external-asset monitoring platform to midsize enterprises. Customers added domains and public IP ranges. An engine explored what was reachable, a parser interpreted technical findings, a database stored the results, and a web application turned those results into dashboards and reports. The product sounded like one operation—run a scan—but internally it was a chain of independent systems, teams, and promises.

Sofia led the application team. Her backend was mostly TypeScript running on Node.js. Ethan ran the scanning engine, written in Python because the engine depended on a collection of mature command-line scanners and analysis libraries. Farah owned the data platform, including a large MongoDB cluster. Priya was responsible for reliability and the Kubernetes deployment. On Monday morning, all four were staring at the same progress bar and seeing four different problems.

Sofia suspected the frontend. The UI showed a scan as unfinished even though many findings were available. Ethan suspected the engine scheduler. The engine pods had been disappearing after long scans. Farah suspected a heavy aggregation used to calculate dashboard counts. Priya suspected they were confusing routine container termination with application failure. They agreed to meet, but not to decide which team was at fault before reconstructing one scan end to end.

The scan director's phrase—“when your scan is finished”—was the first puzzle. Did finished mean all network probes had run? That every engine report had been uploaded? That every report had been parsed? That old findings had been marked absent? That the UI's search index had caught up? That the CSV export was ready? Each was a real milestone, and none was automatically equivalent to the others.

Sofia wrote the distinction on the incident board. A scan was an operation with a history, not a boolean with two values. The customer needed a truthful stage indicator, and the engineering teams needed to decide which stage owned the word completed.

## Tuesday — The path from internet to database

They traced one scan from the user's click. The React frontend sent a request to an API behind a load balancer. The API authenticated the user, checked whether the organization owned the requested environment, validated the scan configuration, and wrote a scan request to MongoDB. A scheduling service published work into RabbitMQ. The engine manager created Kubernetes Jobs for different scanner families. Python processes discovered assets and vulnerabilities, emitted reports, and stopped.

The parser then consumed engine reports, normalized findings, resolved duplicates, compared them with previous runs, and wrote new and updated documents. The last phase calculated summaries and marked a report ready. The browser periodically fetched the status, so a refreshing page could reconstruct progress without relying on a long-lived connection. Under ordinary conditions, the entire journey looked smooth.

Nothing about the architecture was inherently unreasonable. Queues were useful because security scans could take minutes or hours, and customer HTTP requests should not stay open that long. Kubernetes was useful because some scanners were CPU hungry and others mostly waited on network responses. MongoDB was useful for heterogenous findings that evolved as detection plugins changed. But choosing plausible components did not make the boundaries between them safe.

The engineers checked the exact scan that had stalled. RabbitMQ showed the parser had acknowledged work. MongoDB contained a main engine report marked finished. Kubernetes, however, showed that the corresponding Job had failed. This had triggered a rule in the scheduling service: if the pod is failed, mark the scan failed. It was a simple rule that had once seemed protective.

Priya asked when the pod had failed. The container log showed the scanner had successfully written its final report. A cleanup process then exceeded its memory limit, and Kubernetes recorded the container's unsuccessful exit. From the infrastructure's perspective, the Job was failed. From the engine report's perspective, the scan data had already been produced correctly. These were not contradictory observations; they described different contracts.

Ethan wanted to change every Kubernetes failure into a success if a report existed. Sofia objected. A half-written report might exist before a crash. They needed a more precise rule: a validated, finalized main engine report was authoritative about completion of the scanning work; missing or incomplete reports still required investigation. A pod's exit state could indicate operational trouble but should not overwrite a completed business milestone after the fact.

The decision restored some stalled scans, but not all. A few reports were marked finished yet lacked parsed findings, which meant the downstream parser had not completed. They split the UI state into scanning, parsing, reconciling, ready, and failed. The frontend no longer displayed a single percentage assembled from uncorrelated counters. It displayed the latest authoritative milestone and a short explanation of what remained.

The customer appreciated the new wording, although the CSV was still too slow. Solving one truthful-state problem had exposed a second, independent problem: whether the data could be retrieved at useful speed.

## Wednesday — The query that ate the afternoon

The affected customer had accumulated years of scan history. Their latest scan contained roughly one hundred and sixty thousand findings, including repeated detections across assets and reports. The dashboard requested the highest-severity findings, twenty at a time. Page one loaded quickly. Pages near the end could take more than ten seconds. The CSV export exhausted its timeout.

One engineer said the API returned only twenty documents, so the database could not be doing that much work. Farah opened the MongoDB explain plan and laughed without much amusement. “Twenty is how many we keep,” she said. “It isn't how many we look at.”

The query began with a filter for the current tenant and scan. It joined findings against historical findings to determine their latest status, computed display fields, sorted by severity and timestamp, skipped thousands of rows for deep pagination, and finally returned twenty. Some of the expensive work occurred before the limit. On a large tenant, intermediate results grew dramatically. The backend had asked MongoDB to complete a long investigation and then hand over a tiny receipt.

A second issue was the compound index. The collection contained tens of millions of documents across tenants. An index that began with tenant identity but did not align well with scan filtering and sort order helped less than its existence suggested. Indexes are not badges of database maturity. They are alternate physical organizations of data, and their usefulness depends on the query's predicates, ordering, and data distribution.

Farah first removed unnecessary fields from the aggregation, moved selective filtering ahead of expensive transformations where semantics permitted it, and inspected how many keys and documents were examined. She resisted the easy suggestion to add every field to one gigantic index. Large indexes cost memory, storage, and write work; a bad index can simply make the wrong operation faster at consuming resources.

They also changed the data model. The API was repeatedly calculating a status that the parser already knew at the end of each scan. Why perform a historical self-join on every page view if most of that state could be maintained during processing? The parser began materializing stable summary fields on the current finding record, with clear rules for updates and backfills. That did not eliminate the need for history. It separated the read model used by customers from the history used for auditing and reconciliation.

The next argument concerned pagination. Deep offsets required MongoDB to walk past a potentially huge number of records before returning the next page. Cursor-based pagination could continue after a stable sort key and avoid rescanning the entire prefix. But the product team had built a page-number input because customers liked jumping to page four hundred and eighty-seven. Cursor pagination would change that experience.

They made a pragmatic distinction. Interactive browsing would use cursors and stable tie-breakers, because most people advanced through a list or refined filters. Exports would become asynchronous jobs that streamed results in batches to object storage, rather than pretending a browser request should return a six-figure dataset instantly. The exact count and arbitrary-page navigation remained available only where the cost was justified and clearly understood.

Sofia asked whether a PostgreSQL migration would solve the performance problem. Farah said perhaps some query patterns would be easier in a relational model, but a database brand change was not an optimization plan. The current system's main problems were an expensive access path, repeatedly derived fields, and a product interface that encouraged pathological pagination. Rebuilding those mistakes in SQL would still leave expensive queries.

By Wednesday evening, page one and page fifty both felt normal in the test environment, although the team had not yet proven every production workload. There was still a larger problem waiting in the background: the parser sometimes did the same work twice.

## Wednesday afternoon — The report that belonged to somebody else

The slow report had one more oddity. The CSV export endpoint accepted a scan identifier and returned findings for the current organization. During manual testing, a quality engineer pasted a scan identifier from another tenant into the request. The API rejected it, which was reassuring. But the export worker used a different helper to resolve the tenant and, in one test environment, queried findings by scan identifier alone.

The worker was not intentionally bypassing security. Its author had assumed that a scan ID was an unguessable secret. That assumption was wrong. Identifiers are useful handles, not proof that the caller may access the resource. If a backend takes an ID from a browser, it must connect the resource to the authenticated tenant, and that obligation cannot disappear merely because work moves into a background queue.

Sofia corrected the export path so tenant identity came from the authenticated request context, was recorded in the durable job, and was checked when data was actually fetched. The download link had its own time-limited access controls. The worker used scoped database filters, not a global query followed by hopeful application filtering. When it resumed after a crash, it revalidated the durable job context rather than accepting arbitrary tenant input attached to a redelivered message.

The exercise exposed why seemingly minor API changes could have disproportionate consequences. A broken pagination endpoint annoyed users; an incorrect tenant boundary could disclose customer vulnerabilities to the wrong company. They also learned why small QA cases mattered. Testing a request with a wrong ID found a kind of mistake that millions of correct requests would never reveal.

Farah added a constraint to the next data migration review: every new summary table or derived collection needed an explicit ownership key and a tested access path. If faster reads required dropping tenant filters, the optimization was not acceptable. Product correctness included who was allowed to learn the answer.

## Wednesday evening — How to investigate a large system without breaking it

Farah still had a practical problem. The expensive production query needed investigation, but running it repeatedly against the largest tenant could make the incident worse. A junior engineer suggested copying the whole collection into a local laptop. Another suggested turning on detailed profiling for every database operation. Neither was proportionate to the question they were trying to answer.

The team first measured what the query actually did in the production-like environment: examined index keys, examined documents, intermediate pipeline behavior, and returned rows. They compared those measurements with representative tenant sizes rather than with an empty test database. They inspected the execution plan carefully and set limits around diagnostic work. A query plan was evidence about a particular query and data distribution, not a universal promise for all future customers.

They created a bounded sample with deliberate coverage of small and large tenants. For certain questions they used targeted filters and known identifiers rather than asking the server to select arbitrary random documents from a massive collection. They tracked index sizes and write costs as well as read latency. The target was to understand whether the change improved the system's real workload, not to produce one impressive benchmark number.

Sofia asked why database performance had become a company-wide issue. Farah answered that query design was an interface contract in disguise. The frontend's sorting and pagination options dictated which database paths had to be efficient. The parser's document shape dictated what the query could avoid. The release pipeline determined when an index could be built safely. The product's promises determined whether approximate counts were acceptable. None of those questions belonged to the database team alone.

By the time Farah closed her laptop, there was no dramatic fix left to discover. There was a measurable hypothesis, a safe way to test it, and a plan that didn't require the production cluster to serve as an uncontrolled laboratory.

## Thursday — The duplicate message that was nobody's bug

RabbitMQ was delivering work again after a deployment. Some parsing jobs appeared twice. Ethan called it a queue problem. Priya asked whether the worker acknowledged messages before or after completing the database writes. The answer was after. That meant a worker could successfully write findings and crash before acknowledging the message. RabbitMQ would then be entitled to redeliver it.

The queue was doing what it promised: favoring delivery over silently losing work. The application had mistakenly interpreted a delivery attempt as proof of a unique business operation. A scan could be processed more than once, especially around crashes, reconnects, and deployment rollouts.

Sofia checked the parser. It used upserts for some findings but plain inserts for a few derived action records. It also sent a completion notification when a worker finished, regardless of whether another worker had already recorded completion. A duplicate message could therefore create duplicated secondary records and two emails, even when the primary finding documents were deduplicated.

The team established stable identities for the logical operations, unique database constraints where appropriate, and processing transitions that could recognize already completed work. A notification was not sent merely because code reached the last line of a function. It had a durable event identity and was recorded before delivery; sending it more than once should not create multiple customer-visible outcomes.

They also discussed concurrency. Adding parser replicas had made the queue drain faster for small customers but increased pressure on MongoDB during large scans. Each worker could run several operations concurrently, and the same compound index the UI needed was also being updated by ingestion. More workers meant more writes, more index maintenance, more memory usage, and occasionally less useful throughput.

The team reduced concurrency for the heaviest tenants and separated parsing from high-priority interactive reads where possible. It was not a perfect partition of all resources, but it stopped the largest background jobs from routinely making ordinary customers wait for dashboard pages. Priya insisted on measuring queue age, successful findings per second, database write latency, and customer-facing page latency together. A declining queue could be good news or simply evidence that the system had become better at discarding work.

A product manager asked if the platform could promise that every finding would be written exactly once. A backend engineer from an adjacent team replied that they could promise not to expose duplicate logical findings under the chosen identity rules. That was a product guarantee enforced by application semantics. It was not the same thing as promising that the queue or database would never observe a repeated attempt.

The distinction was not philosophical hair-splitting. It determined whether the application was robust to the kinds of crashes that actually happen in production.

## Friday — The infrastructure is telling the truth, but not the whole truth

When the new parser went into a limited rollout, Kubernetes reported several pods being terminated for out-of-memory errors. One dashboard showed node CPU only around thirty percent. A director asked why the cluster was failing while most of its capacity sat idle. Priya pulled up the container memory limits and the allocation of resources per pod.

Low overall CPU did not guarantee that individual containers had sufficient memory. Each pod ran under limits and requests of its own. A Python scanner could exceed its memory limit even while neighboring nodes were mostly idle. Likewise, a Node.js parser could appear lightly loaded on aggregate CPU while its event loop was blocked by large synchronous transformations. Percentages depended on what denominator was being measured and which resource was actually scarce.

They found a batch processor that loaded an entire large report into memory, expanded nested finding structures, and built an enormous array of pending writes before flushing it. It had passed tests on reports with a few hundred entries. In production, some reports contained hundreds of thousands. The program's complexity was not hidden in the algorithm's Big O notation; it was visible in the shape and lifetime of the data it held.

Ethan proposed raising the memory limit. Priya said that might be a useful emergency measure, but it would not change the fact that the processor's memory grew with report size. Sofia changed the parser to iterate through input incrementally and write bounded batches. That imposed a bit more state management, but the memory footprint stopped growing without limit as the report grew.

They had to handle partial batches carefully. Suppose the worker wrote the first forty thousand findings and then died. On restart it had to resume or replay safely. A checkpoint could help avoid unnecessary work, but the checkpoint and the writes had to follow a coherent consistency rule. Reprocessing a bounded chunk was acceptable if writes were idempotent. Claiming exactly-once execution because a checkpoint existed was not.

The team also discovered that their monitoring dashboard counted failed pod exits under one global metric. It did not distinguish between scanning work that had successfully produced a finalized report and parsing work that still needed recovery. A red Kubernetes indicator was a useful infrastructure fact. It was not the customer's final scan status.

They added separate evidence: engine report completion, parser checkpoint, findings persisted, summary computation finished, and report ready. Trace and log correlation carried stable scan and tenant identifiers, with care not to leak sensitive customer asset data into broad-access operational logs. Support could now investigate a scan without asking every engineer which container it had once run inside.

On Friday afternoon the platform still had a few slow customers, but nobody pretended the new design had solved all scaling problems. The team had instead located the work, bounded the dangerous resource consumption, and made the status model correspond more closely to reality.

## The other Friday problem — Which version is actually running?

At four in the afternoon, a seemingly unrelated customer still saw the old eighty-nine-percent progress state. Their API responses came from one cluster while the new frontend was already deployed at the CDN edge. The team had completed a successful CI pipeline, but the dashboard for that tenant had not changed. Somebody suggested clearing the browser cache. Priya checked the running deployment version first.

The repository contained several applications in a shared monorepo. They shared types and helper packages, yet they were built into separate images and released by distinct pipelines. A green build at the repository level did not guarantee that every dependent service had been promoted to the same environment. The deployment manifest for the processing API still referenced an earlier image digest because an approval step had not completed.

This was neither Kubernetes inventing a bug nor a browser failing to refresh. It was a release-coordination gap. Some running services understood the new scan states and some still spoke the old contract. The team could either deploy all pieces in lockstep forever or design a compatibility window in which old and new versions safely coexisted. They chose the latter, with explicit version labels in traces and a check that the frontend could interpret both response shapes during rollout.

Elena, the release coordinator, added a small verification step: after promotion, inspect the running image digests, exercise a representative scan, and confirm the intended contract version in the actual environment. The step sounded mundane compared with designing a resilient queue. It was also how the team avoided spending another Friday debugging code that had never been deployed.

That afternoon taught a useful organizational distinction. CI established that a particular candidate artifact passed a defined set of checks. Deployment established that a particular environment ran an artifact. Release established that customers could safely use a capability. Those were related events, but they were not interchangeable.

## Two weeks later — The release meeting nobody skipped

The follow-up began with a familiar request from sales. A large prospect wanted scans ten times faster. Someone suggested ten times as many Kubernetes workers. This time, nobody accepted the proposal as a complete answer.

Ethan explained that some scanning tasks were network-bound and could parallelize, while others hit supplier rate limits or shared infrastructure. Farah showed how write throughput could saturate long before CPU. Priya described cloud cost and pod scheduling. Sofia explained that reports also had to be parsed, stored, queried, and made comprehensible. The bottleneck could move as soon as one stage improved.

They treated the platform as a pipeline with several queues and different limits, not as one number called speed. For each stage they would measure how much arrived, how much completed, how long work waited, and how many resources each completed unit consumed. They would protect interactive workloads from bulk processing and choose capacity changes based on measured bottlenecks.

The team briefly considered extracting every stage into its own microservice with a separate database. Sofia resisted. Their existing modules already had clear conceptual responsibilities: scheduling, scanning, parsing, persistence, and presentation. More deployable services might allow independent scaling, but they would also introduce new network failures, ownership questions, contracts, and operational work. The company needed cleaner state transitions before it needed more service boundaries.

The next release was deliberately boring. The migration added indexes in a controlled way and measured the load they imposed. The parser wrote a new summary field alongside old data during a transition. The API could read both old and new records. A backfill progressed in bounded chunks rather than locking up production. The feature flag allowed the read path to switch once enough data was ready.

Quality assurance did not merely confirm that the dashboard loaded on a fresh environment. It simulated a worker dying after half a batch, duplicate queue deliveries, a slow database, and an engine report that completed just before the Kubernetes Job failed. Those tests were less cinematic than a full cluster outage. They were also much closer to the failures the team had actually experienced.

At the end of the review, the security director's original question came back: “Can I trust the scan status?” The answer was not a promise that containers would never crash. It was a promise that a customer-visible state meant something precise, supported by durable evidence, and recoverable after the ordinary chaos of machines communicating over networks.

As the meeting ended, Ethan pointed out that the system had never been one thing called a scan. It had been a contract between discovery tools, a message broker, containers, databases, APIs, browsers, support teams, and customers. When the contracts between those pieces were vague, the platform could perform a great deal of correct technical work and still tell a customer the wrong story.

They hadn't replaced the technology stack. They had replaced several assumptions. That turned out to be the more useful modernization.

*The spoken story ends here.*

---

## Behind the story — optional screen reference

**Interdisciplinary touchpoints:** SE320-L01 (services), SE320-L03 (queues and workers), CS340-L03 (MongoDB document models), CS340-L04 (query plans, aggregation, pagination), CS340-L05 (consistency), CS320-L04 (memory pressure), CS320-L06 (event loops), CS430-L01 (partial failure), CS430-L03 (capacity and bottlenecks), SE330-L01 (architecture boundaries), SE340-L02 (containers), SE340-L03 (cloud), SE340-L04 (deployment), SE440-L01 (observability), SE440-L02 (incidents), SE440-L03 (testing), SE240-L03 (frontend state), SE215-L06 (operational ownership).

**Important distinctions:** A failed pod is not necessarily a failed business operation; a finalized engine report is not a fully parsed customer result. Returning twenty records does not imply inspecting twenty records. At-least-once message delivery can be correct behavior. More workers can reduce throughput when a shared downstream resource becomes saturated. The specific status semantics and indices depend on the application and actual query plans.

**Optional reflection:** Which statuses should the user see, and which are internal stages? What observation would prove that a slow page is caused by aggregation rather than rendering? Which pipeline stage becomes the bottleneck if scanning speed triples?
