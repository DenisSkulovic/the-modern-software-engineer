# NS07 — The City That Woke Up Offline

*A transit platform loses a cloud region before the morning commute, and discovers that availability means different things to riders, operators, and databases.*

All organizations, services, and incidents are fictional. Technical details illustrate plausible distributed-system behavior.

## 04:51 — The first alert nobody believed

On a wet Tuesday morning, Iris was asleep when her phone began buzzing. She was the on-call engineer for Metroline, a mobility platform that supplied live transit arrival predictions to several cities. Riders checked the app before leaving home. Dispatchers used a different console to view vehicle locations and publish service disruptions. Public displays at bus stops called a simplified API to show the next arrival.

Metroline processed positioning reports from buses, scheduled timetables, disruption notices, and user subscription preferences. Its primary application region hosted the APIs, PostgreSQL, a message broker, and a collection of workers that converted vehicle positions into estimated arrival times. Redis held short-lived arrival predictions, which were valuable precisely because they were fresh.

The alert said the arrival API's success rate had fallen sharply. Another reported that a worker queue was growing. A third said a health check was failing in one availability zone. Iris opened the dashboard on her phone. It showed the API instances at low CPU usage. That was either reassuring or deeply unhelpful.

At 04:57, the cloud provider's status page reported an issue affecting the region's network and managed storage. Some workloads continued functioning; others could not reach dependencies. It wasn't a neat all-or-nothing outage. Requests failed differently depending on which path they used.

Iris called Mateo, platform lead, and Noor, the backend engineer responsible for arrival predictions. She also paged Elin from customer operations because someone needed to communicate with the transit agencies, not just restart containers.

At 05:08, the first agency asked why the public display said a bus was arriving in three minutes when the vehicle had not moved for half an hour.

## 05:12 — The apparently healthy cache

Noor inspected the response path. The mobile app called an edge endpoint, which reached Metroline's API. The API read a cached arrival estimate, then fell back to recent vehicle positions when necessary. The cache was healthy enough to answer requests, but its inputs were stale because the processing workers could not consume new events consistently.

The engineering dashboard had two different greens. HTTP availability was partly green: clients received `200 OK`. Data freshness was red: the answer was no longer trustworthy. A system can be responsive and still be wrong.

Noor proposed showing the last known position with an explicit age and suppressing precise predicted arrival times after a freshness threshold. The product manager worried users would interpret “Unknown arrival” as service failure. Elin said users would interpret a confidently incorrect three-minute estimate as something worse, especially if it caused them to miss a connection.

They changed the response contract to distinguish current predictions, stale last-known positions, and timetable-only fallback. For public displays, a static schedule was still useful when live telemetry was unavailable, provided it was labeled as scheduled rather than real-time. The team could degrade functionality without inventing certainty.

This had implications for frontend state. A cached `200` response wasn't enough for the app to show a bright green “Live” label. The UI needed to consider the timestamp and freshness status attached to each prediction. The same principle applied to push notifications: “Bus approaching” could not be sent from a data stream that had stopped updating.

Meanwhile, Redis remained useful for short-lived data, but its expiration policy wasn't a substitute for semantic validity. A cache entry with a five-minute TTL could still be misleading after a thirty-second telemetry interruption on a busy route. The appropriate freshness rule depended on what the information meant to a rider.

## 05:19 — A map that could not admit uncertainty

The customer-facing map used colored dots to show every bus on the network. When telemetry stopped, the dots stayed where they were. The frontend component retained the last successful query result because replacing the map with a blank screen felt worse. Over several minutes, the interface gradually became a convincing picture of a city that no longer existed.

Noor asked how the UI should represent incomplete observations. Elin argued that older positions were still useful when labeled as last seen. The product designer suggested a faded icon, a visible timestamp, and a switch from predicted arrival to scheduled arrival after an explicit freshness limit. Riders wouldn't need to understand stream processing. They needed to know when the system was making a prediction versus quoting a timetable.

The backend added an observation timestamp and a quality state to its API response. The frontend no longer inferred freshness from the fact that the request returned successfully. The distinction mattered in other places too. A service disruption published by an operator carried an authoritative validity window. A vehicle position was only a measurement from a possibly delayed source. The application had previously presented both as equally live because they arrived through the same API.

The mobile app had its own caching policy. If a rider went underground and lost connectivity, it could still show route maps and scheduled stops offline. It should not keep showing a stale live countdown as though it were updating. Metroline decided that offline usefulness was good; offline certainty was dangerous. A network outage could degrade the experience without requiring every screen to disappear.

## 05:26 — The second region isn't a second opinion

Mateo had been preparing a standby environment in a second cloud region. The application containers were deployed there, and a PostgreSQL replica followed the primary asynchronously. Some engineering presentations called it “active-passive disaster recovery.” The slide was reassuring. The actual situation was more complicated.

The standby database was a few seconds behind when regional communication became unstable. Its most recent record was older than the primary's last acknowledged writes. Promoting it might allow the service to recover quickly, but potentially lose recently committed user preferences, disruption updates, or operational actions. The team didn't know exactly which changes had reached the replica.

Iris asked which data truly required zero loss. Arrival predictions could be recomputed from incoming telemetry and timetables. Some support annotations could be restored later. Operational disruption orders, authorization changes, and audit records needed more careful treatment. They couldn't treat every table as equally critical merely because the database stored them together.

Mateo proposed shifting all reads to the standby region while keeping writes disabled. Noor pointed out that an application configured for the old primary might still try writes, and clients could retry state-changing requests after timeouts. If one region believed it owned writes while another did too, they could create conflicting truths. The team needed a controlled promotion and fencing plan, not a hopeful DNS change.

Fencing meant preventing the old primary, if it reappeared, from accepting writes as though it still had authority. Without that guard, a temporary network partition could produce two competing primaries and contradictory records. Some managed systems automate parts of this, but the application's expectations, write routing, and recovery procedures still matter.

At 05:34, Mateo confirmed that the old primary was no longer accepting application writes under their failover procedure, promoted the standby database, and directed write traffic to the recovered system. They recorded the replication gap and began reconciling potentially missing state using durable event IDs and external sources where possible.

## The routing test from the wrong laptop

A well-meaning developer reported that the new region was reachable because `curl` worked from the office. Iris asked whether the failing clients were in the office. They weren't. Some were public displays running through cellular networks, others were mobile apps on unreliable Wi-Fi, and several were transit-agency systems with explicit outbound allowlists.

They compared resolution and connection behavior from representative networks. One agency had allowlisted the previous region's public egress or endpoint addresses and rejected the newly promoted path. Another display software version attempted IPv6 and delayed fallback when the new IPv6 listener wasn't configured as expected. A successful request from one environment did not prove every other environment could traverse the same network path.

The team distinguished the stages carefully. DNS could return an address while the TCP connection failed. TCP could establish while TLS certificate validation failed because the new endpoint presented an unexpected chain or hostname. TLS could succeed while the HTTP proxy returned a gateway timeout because its upstream was unhealthy. Each result narrowed the search; none identified the whole root cause by itself.

Mateo corrected the IPv6 listener and coordinated the agency allowlist change rather than disabling certificate checks or assuming all failures were DNS propagation. They documented which partner networks depended on fixed endpoint properties. The cloud was programmable, but some customer contracts still treated an IP address as part of the interface.


## 05:41 — DNS is not a global switch

The team had a second-region endpoint ready. Mateo updated edge routing so new traffic would prefer the healthy region. But clients didn't all switch immediately. Some had connections to an old load balancer. Others had cached DNS answers. A few transit displays used network stacks that recovered slowly after the first address stopped responding.

Noor reminded the room that changing an authoritative DNS record did not invalidate existing recursive resolver caches or established connections. A short TTL helps during planned changes, but it is not a command that reaches every client instantly. IPv4 and IPv6 endpoints could also have different reachability problems. The team compared the actual route used by affected devices rather than assuming they all behaved like the office laptops.

The new region was technically healthy yet unexpectedly slow for some riders. The edge network was delivering requests, but the standby's read model was cold. Its cache had little recent data, and many requests fell back to database queries. The database connection pool queued waiting operations. Request duration climbed even though individual SQL queries remained moderately fast.

Adding more API instances made the symptom worse. Each instance opened another pool of database connections, multiplying pressure on the same bottleneck. The team reduced unnecessary request fan-out, constrained pool sizes, prioritized critical routes, and warmed frequently used read models gradually. Horizontal scaling could not create more database capacity merely by placing more applications in front of it.

One endpoint generated a disproportionately large load because it returned detailed vehicle history for every bus on the map. The mobile UI needed only the latest positions for the current viewport. Noor added a compact query path, and the frontend requested only the necessary subset. Sometimes the most effective reliability intervention is to stop asking an expensive question so often.

## 05:49 — The alarm that measured the wrong thing

As traffic shifted, Iris inspected an alert claiming the API's error rate had recovered. She was suspicious. The metric counted requests reaching application instances, but many failed requests were being answered by the CDN before they ever reached the API. The numerator had improved partly because a portion of the failures wasn't in the measurement anymore.

She opened edge logs and compared them with application traces. Some clients received gateway timeouts while others got cached timetable responses. A few repeated an idempotent read rapidly enough to strain the recovering edge configuration. The service-level objective had been framed as “percentage of successful API handler calls.” That was a poor measure of whether a rider could obtain useful transit information.

Elin helped define an end-user-oriented availability measure: what share of representative requests from real client environments produced a valid, sufficiently fresh answer within an acceptable delay? That metric couldn't completely replace infrastructure measurements; it needed them to explain why experience changed. But it anchored the incident around the outcome customers actually cared about.

The team also stopped treating all routes as equal. During the incident, timetables and disruption notices were more important than a decorative map animation. They prioritized essential endpoints and temporarily reduced polling frequency for expensive noncritical detail views. Under overload, serving fewer features well was preferable to allowing every feature to fail together.

## 06:03 — More retries, less availability

The message broker began recovering, and thousands of delayed vehicle reports arrived. Workers tried to process them, while API clients retried failed calls, and a third-party notification service retried its own callbacks. The system was getting busier because it was recovering.

Iris watched queue depth rise and worker throughput fluctuate. The instinct was to add more consumers. Noor pointed out that workers used a shared database and sometimes called the external notification service. Raising concurrency indiscriminately would overload dependencies and create yet more timeouts. They needed to bound in-flight work, prioritize the newest relevant vehicle positions, and ensure replayed data could not overwrite later state.

Vehicle reports carried a source identity, sequence number, and observation timestamp. A late report about a bus's position at 05:15 should not replace a newer 05:55 observation merely because it was processed later. A consumer checking only arrival order would manufacture movement backward through the city.

The team used version-aware updates and idempotent event processing. Duplicate report deliveries were expected during recovery; they should not lead to duplicate rider alerts or corrupted state. For notifications with external side effects, they recorded durable delivery intent and reconciled outcomes rather than claiming that retrying a webhook was automatically safe.

By 06:17, API availability had improved. The timetables were readable, live predictions gradually resumed, and customer operations could see freshness warnings for routes with delayed telemetry.

Elin drafted an agency update in plain language. It distinguished services that were functioning, features operating in degraded mode, and areas where data remained delayed. She included the next planned update time and avoided promising that the entire region was fixed merely because the primary website loaded again.

## 06:40 — One decision, several departments

At the incident bridge, the transit-agency liaison asked for a one-sentence explanation. Mateo began describing the cloud region and replica lag. Elin stopped him. “They need to know whether they can trust arrival displays for the next hour.” The engineering explanation was useful internally, but customers needed an operational decision.

They issued a status notice distinguishing three capabilities: scheduled routes still worked, live predictions were degraded on affected lines, and disruption publishing had recovered with some recent updates under reconciliation. Support teams received a short checklist for identifying stale displays and a path for escalating reports of missing notices. This prevented dozens of separate support conversations from consuming engineers needed for recovery.

The agency's public-relations team wanted to say the incident had been “resolved” once most buses were reporting again. Iris preferred “recovering,” because several consumers were still catching up and one important class of notification hadn't been fully reconciled. Their status vocabulary had to correspond to observable conditions. Otherwise the public status page became another cache of optimistic misinformation.

A new engineer asked why they didn't invoke a global failover button and leave the details to infrastructure automation. Mateo explained that automation could move traffic, promote known-safe resources, and enforce guardrails. It could not decide whether a lost operational notice was acceptable, whether an old report should overwrite a new vehicle location, or how to explain degraded arrivals to riders. Those were product and engineering contracts, not merely cloud settings.

## 06:56 — The replay that almost sent yesterday's warning

As workers caught up, Elin noticed a test rider receiving a notification about an earlier road closure that had already ended. The notification system consumed disruption events, but one handler interpreted arrival order as the order in which events happened. A delayed “closure started” record had been processed after the “closure ended” record.

Noor paused the notification publisher long enough to compare sequence numbers, effective times, and authoritative disruption state. A simple queue did not guarantee the chronological meaning of independent business events, especially when retries and parallel consumers were involved. They changed the consumer to check whether an event was newer than the state it would affect and whether the alert was still valid at publication time.

They also considered the harder case where an external notification provider had already accepted a message before Metroline's connection timed out. Blindly sending the message again could annoy riders. The application attached a stable identity to each notification intent, used provider-supported deduplication where available, and recorded uncertain outcomes for reconciliation. It couldn't guarantee that every phone would display the message exactly once; that depended on systems outside its control. It could prevent avoidable duplicate submissions and make uncertainty visible.

Elin asked whether to send a correction to riders who had received the stale closure notice. That was an operations decision informed by technical evidence: which users were affected, which notification had been delivered, and whether a new message would clarify the situation or create additional confusion. Reliable software needed a path from event processing to human communication.

The incident reinforced a pattern Iris recognized from earlier debugging. A component doing its narrow job correctly did not guarantee the total system made sense. The broker delivered a record. The worker processed it. The notification provider sent it. The user still received bad advice because the system had failed to preserve the event's business meaning across those steps.

## The hidden dependency on human operators

The new region had enough computing capacity to answer requests, but it did not have a complete local copy of the city's latest manual detours. Dispatchers entered those changes through an operations console, and the underlying workflow stored some attachments in a region-specific object-storage bucket. The database replica preserved references to the files, but not the files themselves.

Mateo had rehearsed database promotion, yet the product's complete recovery also depended on object storage, scheduled imports, secrets, and the permissions granted to standby workers. A running container wasn't sufficient if it couldn't read a route map. The team identified which dependencies required independent replication and which could safely be reconstructed from authoritative agency data. It also documented the limits of its recovery point and recovery time objectives so customers knew what a regional failure might mean.

Iris added the missing storage dependency to the next drill. She also resisted copying every possible system into the standby region without understanding its value. Replication cost money and could replicate corrupt data or configuration mistakes just as efficiently as healthy data. A good recovery strategy needed backups, restoration tests, dependency maps, and explicit decisions about what information had to survive.

## 07:10 — The incident isn't finished when the graph is green

The regional outage stabilized before the peak commute ended. Iris had slept less than two hours and still had twenty-seven unread messages. One came from a city operator: “Can you tell us if any disruption messages were lost during failover?”

The honest answer was that the team had not yet established that. They compared authoritative records, application logs, queued changes, and agency-provided submissions. A timeout while publishing a disruption notice did not prove the notice failed. Some agency clients had retried the same request, and idempotency keys prevented duplicate notices from appearing. But one legacy client hadn't supplied keys, so its two nearly identical submissions required reconciliation rather than blind deletion.

The incident review reconstructed the outage by tracing data and decisions across layers. A regional dependency failure reduced database availability. Worker ingestion lag made predictions stale. The cache continued answering, hiding the fact that its inputs had aged. A recovery region improved availability but exposed cold-cache and connection-pool bottlenecks. Excess retries then strained the dependencies the team was trying to restore.

No single dashboard captured all of that. Metrics revealed rates and saturation. Logs supplied individual errors. Distributed traces connected request boundaries. Domain-specific freshness indicators explained why a technically successful response could be wrong. Support tickets supplied something the metrics couldn't: the human consequence of showing bad arrival information.

The next week, the team ran a controlled failover drill. They discovered the runbook assumed a database administrator would be online within five minutes, a condition not guaranteed at four in the morning. They automated safe parts of the procedure and recorded the judgment calls that should remain human. They also tested the UI with explicitly stale data rather than only testing whether an API returned a success status.

At the retrospective, Mateo said the goal was not to eliminate every outage. That would require unlimited money and still fail. The goal was to choose which failures could be tolerated, which correctness rules could never be violated, and what graceful behavior the product should provide when assumptions broke.

Metroline had begun the morning believing disaster recovery was mainly about switching traffic to another region. It ended with a more complete model: there were multiple kinds of truth, multiple notions of being available, and many independent clocks—database replication, cached estimates, connection timeouts, queue lag, and the rider's actual wait at the stop.

At 08:45, the first bus display again showed a reliable live arrival estimate. It was an ordinary little number in a glass box. That number required an extraordinary amount of coordinated software to mean what people thought it meant.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Connections:** CS230-L04/L07/L09/L11 (DNS, connections, intermediaries, forensics); CS340-L05 (replication, consistency); CS430-L01/L02/L03/L05 (partial failure, availability, overload, workflows); SE320-L02/L03 (cache and queues); CS330-L02 (query and connections); SE240-L03/L05 (UI state and performance); SE340-L03 (regions and cloud); SE440-L01/L02 (observability and response); SE215-L01/L11 (operational roles and release ownership).

**Technical caveats:** DNS alone cannot guarantee immediate failover. Replica lag changes the write-loss risk. A business-level freshness rule is not the same as cache TTL. A successful HTTP response may be semantically stale. Real regional recovery requires provider-specific procedures and an explicit write-authority plan.

**Optional reflections:** What should the rider see if live telemetry is unavailable? Why did the standby region slow down after traffic moved? Which operations require stricter consistency than arrival prediction?
