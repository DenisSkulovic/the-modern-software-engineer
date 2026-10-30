# NS04 — The Tuesday Cutover

*A field-service company changes one innocent-looking field, and discovers that a software release is an agreement between old code, new code, people, and time.*

The company, people, and events are fictional. Technical mechanisms and operational tensions are grounded in ordinary software engineering practice; figures are illustrative.

## Monday — An adjective becomes a database migration

At eight forty on Monday, Leena, product manager at Fieldwell, put a photograph on the conference-room screen. It showed an electrical technician outside a warehouse in Rotterdam, standing beside a service van. The caption was a customer's complaint: “Your technician was on time. Unfortunately, she was certified for the wrong equipment.”

Fieldwell sold scheduling software to companies that dispatched technicians to inspect elevators, refrigeration equipment, and industrial power systems. A customer had hundreds of service appointments each day. Some required safety certificates that expired; others required equipment-specific training. For years, Fieldwell had described a technician with a single text field called `qualification`. It contained values such as “electrician,” “senior electrician,” or occasionally “Ask Miriam.”

Miriam was a dispatcher, a real person, and an alarmingly important undocumented dependency. She knew which technician was actually qualified to work on which equipment. When she went on holiday, dispatchers quietly sent more technicians to the wrong jobs.

Leena proposed replacing the free-text field with a structured list of certifications, each with an issuer, expiry date, and permitted equipment category. The dispatch screen would highlight missing qualifications before a job was assigned. She wanted the feature in two weeks because a major customer had a contract renewal approaching.

Oskar, the backend engineer, initially called it a schema change. Jules, the frontend engineer, called it a new form. Priya, the engineering lead, called it “a change to what counts as a valid dispatch.” All three descriptions were true, but only Priya's made the scope clear.

The system could currently assign a technician to a job if they were free at the requested time. The new rule would require an appropriate, unexpired certification. That rule belonged in the authoritative operation that made the assignment, not merely in a red warning on the screen. Otherwise, two dispatchers or an older mobile client could bypass the frontend check and create an invalid assignment anyway.

Before touching code, Priya asked Leena a question no ticket had answered: “Do we prevent assignment when a certificate is expired, or do we warn and let a supervisor override?” Leena had assumed the answer was obvious. The safety team said the first option. A pilot customer's operations director said that emergencies required the second. By lunchtime, the team had discovered three different rules for different categories of work. Their first useful artifact was not a database migration. It was a decision table, signed off by the people who would be accountable if the software made the wrong decision.

## Tuesday — The old world will not disappear on command

Fieldwell had a PostgreSQL primary, a Node.js API, an administrative React application, and a mobile app that technicians sometimes used offline. Backend instances ran as containers across several nodes. Releases moved through a shared CI pipeline and a deployment process coordinated by a small platform team.

Jules suggested renaming `qualification` to `certifications` and changing the field from a string to an array. Oskar said they could migrate the existing values in a script and be done by Thursday. Priya drew four boxes on a whiteboard: old frontend, new frontend, old backend, new backend. Then she added a fifth: mobile clients that had not connected for three days.

“This,” she said, tapping the fifth box, “is why we don't get to deploy the entire world at once.”

The old API clients expected a single string. Some old backend instances might still be serving traffic when a rolling deployment began. Mobile devices might upload queued assignments hours after the new version went live. Simply changing the column type could break existing code, and merely checking the current browser version would not protect the database from requests from yesterday.

They chose an expand-and-contract migration. First, they would add new tables to represent certificates and permitted equipment categories while leaving the old field intact. The new backend would read and write the new structure, but would continue supporting old clients through a compatibility layer. New API responses would include both the old representation and the new representation during the transition. Only after every relevant client path was upgraded could they remove the old field.

It was less elegant than a clean replacement. It was also far safer. Compatibility has a cost, but the cost is visible. A broken release because half the fleet still speaks yesterday's schema has a cost too, usually visible on a Sunday evening when nobody wants to discuss it.

Oskar asked whether they should backfill certifications by interpreting the existing `qualification` values. Priya pointed to “Ask Miriam.” A migration can change data format without discovering missing business facts. They chose to migrate recognizable codes automatically, mark ambiguous records as requiring review, and give supervisors a safe way to complete the gaps. The product had previously treated messy data as an inconvenience; the new feature turned it into a correctness constraint.

The database engineer recommended uniqueness constraints on technician, certification type, and issuance identity where appropriate, foreign keys for referenced categories, and explicit validity ranges. Application validation would provide useful errors to people. Database constraints would protect invariants when the application had a bug, a race, or an unexpected writer.

Leena was startled when a meeting about a field on a screen turned into a conversation about historical truth. Priya explained that the software could not simply reject last year's assignments because a certificate was expired today. Assignment records needed a snapshot of the relevant qualification decision at the time it was made. Current certification state and historical evidence were different facts.

## Tuesday evening — A certificate is not just a string with a date

While Oskar sketched the new tables, Dana joined a discussion about how the system would decide whether a certificate counted. Fieldwell could not assume that two certificates with the same display name were interchangeable. A qualification issued by one authority might authorize a narrower set of equipment than another. A certificate might have been revoked before its stated expiry date. Emergency overrides might require a named supervisor and become invalid after a certain shift.

The temptation was to store `isQualified: true` on each technician and update it overnight. That would produce a convenient query, but it would hide the reason behind the decision. A technician could be qualified for one class of industrial refrigeration unit but not another. The answer was a relation among technician, equipment type, certificate, issuer, time, and sometimes emergency policy. A single boolean would be a lossy summary of a much richer rule.

They mapped the source facts separately from derived decisions. Certificate records kept issuer identity, dates, verification status, and scope. Assignment history recorded what evidence was considered and which policy version made the decision. The system could compute current eligibility for a requested job, and it could preserve a small historical explanation for an auditor without pretending the current certificate table represented the past.

This changed the frontend design. Instead of displaying a generic red warning, Jules created an explanation that said which qualification was missing or expired, and linked to the person allowed to resolve it. Fieldwell had previously optimized for reducing clicks. Now the user needed an understandable reason for a blocked action. The fastest interface wasn't necessarily the one requiring the fewest seconds; it was the one that helped dispatchers make correct decisions without calling Miriam.

That evening the QA engineer, Hassan, challenged a hidden assumption: the system clock. If a certification expired at midnight, midnight in which timezone? A dispatcher in Helsinki could assign a technician in Lisbon. A certificate might specify an issuer's local date, while the database stored timestamps in UTC. They wrote down how validity boundaries were interpreted and tested transitions around midnight and daylight-saving changes. The resulting rule was boring, specific, and important. Production bugs love phrases such as “everybody knows what midnight means.”

## Wednesday — The seemingly harmless concurrent edit

Jules built the new dispatch interface. A supervisor could see a technician's certifications, an expiry indicator, and an override flow requiring a reason. The warning looked great in the staging environment. Then two people tested it together.

One dispatcher opened an assignment at nine. A second dispatcher removed the technician's certification at nine-oh-one after receiving an updated safety document. At nine-oh-two, the first dispatcher clicked Assign using a screen that still displayed the earlier valid status.

Jules had validated the certification on the frontend. So had Oskar, in a separate read before writing the assignment. But the state could change between that read and the write. The system was making a decision based on a fact that was no longer true.

Oskar's first instinct was to wrap everything in a transaction. Priya agreed that a transaction was useful but reminded him that transactions do not automatically solve every business race. The relevant checks and writes had to be coordinated under the chosen isolation and locking strategy. In their design, the assignment transaction would lock or otherwise protect the appropriate authoritative rows and verify eligibility before committing. If the condition changed, the operation would fail with a clear conflict rather than quietly dispatch the wrong person.

Jules changed the UI to handle that conflict as a normal outcome, not an inexplicable error. It refreshed the assignment state and told the dispatcher what had changed. The frontend could optimistically show an assignment in progress, but it would not report final success until the backend confirmed the authoritative write.

A junior developer asked why they didn't cache the certification decision for an hour to avoid repeatedly querying PostgreSQL. The same hour could contain an urgent revocation. They could cache descriptive lists and read-mostly categories. But a safety-critical authorization decision depended on fresh, authoritative state or an explicitly acceptable consistency policy. “Fast” and “correct” weren't two independent checkboxes. The decision about freshness was part of the product rule.

That afternoon, the team added tests spanning the API contract, the database invariant, and the frontend response to conflicts. Unit tests covered the rules, but a realistic integration test had two assignment requests race against a revocation. Priya insisted on testing the unpleasant timing, not only the happy path where every request politely waits its turn.

## Thursday — The release has more than one owner

Fieldwell's monorepo contained the API, frontend, shared types, migrations, and worker code. Some developers viewed the shared repository as convenient; others thought it made CI painfully slow. The release team had learned not to equate a single commit with a single deployable version.

The changes arrived in a sequence: database expansion, compatible API, admin interface, mobile API compatibility, backfill process, enforcement flag, and eventually cleanup. A feature flag controlled whether the new safety rule was enforced for a customer, but a feature flag could not roll a database schema backward. That distinction mattered when Leena asked whether they could “just turn it off” if the release went badly.

Dana from platform engineering reviewed the deployment plan. “What happens,” she asked, “if new code writes certifications but we roll the API back to a version that knows only about the old string?”

They discovered the compatibility layer could read old data but would ignore newly created certificate records in one edge case. Rolling back the application would not delete those records, yet an older writer might overwrite the legacy field and create a disagreement between the representations. The solution was to make the transition explicitly version-tolerant, monitor both representations, and prevent irreversible cleanup until no supported writer depended on the old schema.

A deployment is not a magic replacement of every process at once. During a rolling update, old and new instances can handle requests concurrently. Background workers might still be running an earlier image. A customer might have a browser tab open from yesterday. Dana's release checklist asked about those overlapping lives, not just whether the Docker image built.

The first CI run failed on a test that had passed locally. One service stub used an old API response fixture that omitted the new field. The contract test was doing its job: warning that the team had changed assumptions shared between components. Another test failed because a database migration was executed inside an application transaction even though the deployment migration mechanism expected its own transaction boundaries. The team fixed the test and deployment flow rather than weakening the checks until the pipeline turned green.

Leena wanted to know why the first deployment only added invisible database tables. Priya answered that the safest feature sometimes had a boring first release. If the new tables caused unexpected performance or migration trouble, they could address that before customers depended on them. Delivery was a sequence of reversible decisions wherever possible.

## Thursday night — A rollback rehearsal nobody wanted

Dana assembled a miniature production environment with three application versions: yesterday's worker, today's compatible API, and tomorrow's frontend. She asked the team to rehearse a rollback while a migration backfill was halfway through. That sounded unnecessarily cruel until they tried it.

The old worker read `qualification` but did not recognize the new certificate records. It could still send notifications about a technician whose current certificate had been revoked. The new API knew the updated rule, but the older worker had cached assignment details in a job payload. Even if a database transaction correctly rejected a new assignment, an old job could still carry stale data into an email or a report.

They decided that notification workers should refer to an authoritative assignment identity and read the committed current status when performing consequential actions, rather than treat arbitrary snapshots in the queue as a permanent command. Messages still carried enough context for observability and replay, but the business rule had a clear owner. For historical notifications, the worker could use the immutable decision snapshot recorded at the time of assignment.

Hassan created a regression scenario in which the new frontend submitted an assignment while one API instance was still old. They verified that the request couldn't bypass the safety rule because traffic was routed only to compatible instances once enforcement began. They also tested a client with no knowledge of certificates. The server accepted requests using the old representation when the business rule permitted it and rejected unsafe assignments with a precise error. Compatibility didn't mean silently allowing a safety violation.

The rehearsal caught an environment problem as well. A configuration variable enabling certificate enforcement had been set in the API deployment but not in the background worker. The code was identical in source control; behavior differed because its environment differed. Dana added checks that verified actual deployed configuration and recorded the image digest alongside feature-flag state during rollout. A green build was proof of a build, not proof that all running processes had the same understanding of the world.

## Friday — The dashboard says green

At eleven fifteen, the first pilot tenant received the new interface. The deployment dashboard was green. API error rates were stable. Response times looked reasonable. Leena invited the customer to a live demonstration.

The supervisor opened a job and selected a certified technician. The interface showed a warning about a certificate that had expired yesterday. Excellent. The supervisor chose a different technician, clicked Assign, and received confirmation. Then the customer's coordinator refreshed the list. The new assignment had disappeared.

Nobody had lost the database row. The assignment write had committed. The list page was served from a cached read model updated asynchronously by a worker. That worker consumed a change event, projected assignment details into a search-friendly representation, and updated a Redis-backed view. Its message schema did not include the new certification decision metadata. An error handler had treated the unknown value as a failed projection and queued the event for retry.

The team initially saw no API errors because the request path was healthy. The bug lived in the asynchronous path after the response. The user had correctly been told that the assignment existed, but the list was showing a stale version of reality. These were different promises, and the product hadn't clearly expressed them.

Dana compared request traces with worker metrics. The queue depth had begun growing after the pilot rollout. The error wasn't a time-out at the browser, nor a failed database transaction. A contract change had crossed a boundary between teams, and no integration test covered the actual event consumed by the projection worker.

They paused the rollout and deployed a compatible projection reader. It accepted both old and new event schemas. Crucially, the handler did not discard older events merely because a new event arrived later; updates carried a version, so replayed or delayed events could not overwrite fresher state. The worker was designed to process messages more than once safely because redelivery after crashes was possible.

Jules added a small indication when the list was updating and a direct way to refresh authoritative assignment status. Priya resisted the suggestion to block every assignment response until every projection and cache had been updated. That would couple the critical write to downstream services with different availability characteristics. Instead they documented what the response guaranteed and ensured that customer-visible state would converge predictably.

The pilot resumed after a fix, replayed events, and a targeted test proved the projection eventually matched the authoritative assignment table.

## The customer who asked for an exception

During the pilot, a factory reported that its only available refrigeration technician had completed renewal training but the issuing authority's website had not yet published the updated certificate. A supervisor wanted to send the technician immediately because a cold-storage warehouse had stopped working. Leena called it an edge case; Hassan called it the sort of thing the product would face every week.

The team could not invent safety policy. They asked the customer's compliance officer to define the exception process. For certain equipment classes, a supervisor could submit temporary evidence and authorize a bounded override with an explicit reason and expiry. For high-risk work, no override was permitted. The UI displayed the difference clearly; the backend enforced it regardless of the client making the request.

Auditing the override created another distributed responsibility. An external notification service might be unavailable while the authorization itself succeeded. Fieldwell chose to commit the override decision and a durable notification intent together, then send the notice asynchronously. If the provider timed out, the worker might not know whether the notification was delivered. The system recorded attempts and reconciled delivery state instead of claiming exactly-once side effects merely because a queue existed.

Leena saw how a business exception could connect permissions, database constraints, temporal logic, asynchronous work, and user communication. None of those topics appeared in the original ticket. Yet all of them determined whether the customer would trust the feature during an urgent event. The team treated the exception pathway as a first-class part of the design, not a secret administrator button whose behavior nobody wanted to test.

## Monday again — The work no ticket described

A week later, Fieldwell's safety team and customer support reviewed the rollout. The new feature reduced unqualified assignments in the pilot. It also generated a surprising number of warnings for ambiguous legacy data. Support needed an explanation for supervisors, not a screenshot of a SQL schema.

Miriam finally took her holiday. For the first time, the product did not require her private mental database to operate. That was the real achievement, though nobody had written it in the sprint goal.

Leena asked Priya whether this had been a frontend feature, a backend feature, or a database project. Priya said it was a business-rule change that happened to cross several technical and organizational boundaries. The browser expressed the decision. The API enforced it. The database protected it. Workers communicated its consequences. Release engineering made the transition safe for old and new clients. Product and support made the rule usable by real people.

She opened the team's incident note. It did not end with “add more tests.” It named which contract had failed, why the existing observability missed the async path, what was changed, and how they would verify a future rollout. The goal was to make the next unknown problem less surprising, not to write a ceremonial document that nobody read.

Oskar had wanted to delete the old column immediately because it offended his sense of cleanliness. He still wanted to delete it, but now knew the right time was after compatible clients had been observed in production long enough and the legacy data had been reconciled. An extra column was temporary technical debt. A broken rollback path would have been an operational liability.

On the following Tuesday, the final pilot tenant came online. There was no dramatic celebration, just a customer message that said the certification check had caught a dangerous assignment before it was made.

Fieldwell had shipped the same feature Leena originally requested. Yet almost none of the most consequential engineering work had been about rendering the new field. It had been about turning a vague adjective—qualified—into a reliable rule that held across users, processes, databases, old clients, deployments, and time.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Connections:** SE215-L02/L03/L04/L07/L11 (roles, repo, collaborative delivery, QA, releases); SE240-L02/L03 (frontend architecture and state); SE310-L01 (API contract); SE320-L01/L03 (service boundaries and workers); CS330-L01/L03 (data modeling and transactions); CS430-L01/L04 (partial failure, event contracts); SE330-L01/L03 (architecture and evolution); SE340-L04 (CI/CD); SE440-L01/L03 (observability and tests).

**Technical caveats:** A database transaction alone doesn't guarantee a particular business invariant; the check and write must be designed for the chosen isolation and concurrency strategy. A feature flag does not reverse an incompatible schema change. Stale projections are not necessarily failed writes. The fictional organization chose to keep an authoritative assignment write separate from derived list updates.

**Optional reflections:** What contract would you test first if a worker consumed changes from a different team? How would you roll back while supporting old mobile clients? Which part of this change actually carried the business risk?
