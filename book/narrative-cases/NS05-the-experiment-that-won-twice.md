# NS05 — The Experiment That Won Twice

*A music-learning app celebrates a conversion win, until a data engineer asks what its dashboard is actually counting.*

The company, people, and events are fictional. The engineering decisions and statistical mechanisms reflect plausible product work; the numbers are illustrative.

## Week one — The button everybody loved

At half past nine, the growth team at TempoRoom arrived for the weekly product review. TempoRoom sold lessons and practice plans to amateur musicians. A customer could play a short demo, take a free lesson, and subscribe for ongoing coaching. Its interface looked friendly. Behind it sat a complicated collection of payments, entitlements, recommendation jobs, marketing pages, and analytics systems that few people understood end to end.

Alina, a product manager, showed a chart. The company's subscription conversion rate had been nearly flat for months. A new onboarding flow—a shorter signup form, a more prominent first lesson, and a recommendation based on the musician's instrument—appeared to improve conversions by eleven percent. The experiment had run for a week. The graph showed green.

“This could pay for the next quarter of development,” Alina said.

Basil, the senior frontend engineer, had implemented the new flow. It reduced how many questions a user answered before reaching a useful lesson. It also replaced a set of sequential API calls with a single onboarding endpoint that fetched available lessons and the user's plan together. On his laptop, the screen felt much more responsive.

Nadia, the data engineer, did not congratulate anyone immediately. She asked how conversion was defined. The room offered several answers: clicking Subscribe, beginning checkout, receiving a successful payment response, and actually acquiring an active subscription. The dashboard title said “Subscriptions.” The event definition counted `checkout_complete` events sent from the browser after a confirmation page rendered.

“What happens when the confirmation page renders twice?” Nadia asked.

Nobody knew. That was not unusual. Product analytics can begin as a harmless collection of events and gradually become a system from which people make very expensive decisions. But a client event describes what the browser believed happened, not necessarily what the payment processor or billing database committed.

Alina asked whether Nadia thought the experiment was fake. Nadia said she hoped it was real and wanted to find out. A good experiment should survive somebody asking how it was measured.

## The event that had two lives

TempoRoom's frontend used a React app for authenticated lessons and a server-rendered marketing site for public course pages. The analytics library queued client events, retried failed uploads, and occasionally replayed events when a browser came back online. A separate backend service recorded payment-provider webhooks and updated subscription entitlements.

Basil had moved analytics initialization during the onboarding redesign. The new page mounted a component that called a tracking function after the subscription state loaded. In one navigation path, the component remounted when the router replaced the temporary onboarding route with the permanent lesson route. The tracking effect fired again.

A junior developer said React must be broken because it ran the effect twice. Basil explained that remounting was a real lifecycle event; a tracking side effect tied carelessly to rendering could execute more than once. Development Strict Mode could expose effect mistakes too, but the production bug here didn't depend on Strict Mode. The important issue was that the frontend did not possess an authoritative identity for the completed business event.

A client event contained a user ID and a timestamp. If it appeared twice, the ingestion service accepted both. The dashboard counted both. Alina's green bar represented a mixture of behavior changes and duplicate observations.

Nadia recommended separating exposure, behavior, and outcome. The experiment platform should record which variant a user was assigned to; the product should record meaningful intermediate actions; the billing service should provide authoritative subscription changes. Each important event needed a stable identity, not just “some event happened around this time.”

The billing service already had a durable subscription ID and payment-provider event IDs. It could deduplicate repeated webhook deliveries, reconcile uncertain provider outcomes, and publish a state-change event after the database committed. The event stream could still deliver the same record more than once, but consumers could make processing idempotent by using the event identity and version.

The team rebuilt the conversion metric from those authoritative events. The eleven-percent increase shrank to six percent.

Alina was disappointed. Nadia said six percent might still be excellent. They had simply stopped crediting the product for rendering the same success twice.

## The identity problem disguised as a funnel

Before the experiment could be trusted, TempoRoom had to decide what a user meant. A visitor might begin on a phone, open the registration email on a laptop, and purchase a subscription hours later through a payment page hosted by another service. Anonymous browser identifiers, logged-in account IDs, and billing customer IDs didn't line up neatly. The analytics system had been treating each browser as a separate person until somebody logged in, sometimes counting one journey as two.

Nadia refused to solve this by joining everything on email address. Email could change, be mistyped, or be shared by a family account. It was also sensitive personal data that shouldn't be copied casually into every analytics pipeline. The company needed a deliberate mapping between anonymous sessions and authenticated identities, with explicit privacy and retention rules.

Mika asked a statistical question: if the experiment assigned visitors anonymously before signup, what happened when they opened a new browser? A naive implementation could expose the same person to different variants. The team decided which unit they intended to randomize—account or visitor—and acknowledged the limitations for anonymous traffic. They also adopted a consistent policy for cross-device journeys, rather than quietly inventing perfect attribution after the fact.

Basil discovered that some events were sent even when the browser did not have permission to track nonessential behavior under the user's consent settings. Product analytics was not exempt from the rules governing user data simply because the events were useful to the company. The tracking client distinguished essential operational telemetry from optional analytics and respected the relevant consent configuration. The backend limited fields and retention so logs would not become a second collection of private user histories.

Alina initially worried these safeguards would make the experiment smaller and harder to interpret. Nadia said that a smaller, well-defined sample could support a more honest decision than a larger pile of events with uncertain identity and permission. The important question wasn't how many rows the warehouse contained. It was what population those rows represented.

## The graph that forgot who the users were

The next review looked better. The experiment still appeared to win overall. Then Mika, a product analyst, segmented the results by device and acquisition channel. Something strange emerged: within several major segments, the new experience performed only slightly better or sometimes worse. Yet the combined number showed a striking gain.

The explanation lay in composition. During the experiment, a marketing campaign had sent more high-intent visitors to the new variant through a campaign-tagging error. People already motivated to subscribe were unevenly distributed. The aggregated conversion rate partly reflected which users entered each group, not only what the interface did to them.

Mika explained the intuition without opening a statistics textbook. Imagine two restaurants, one serving mostly hungry commuters and another serving people who just finished dinner. You cannot reliably decide which menu is more persuasive by comparing raw dessert orders. The people arriving at each restaurant matter.

This kind of reversal or distortion in aggregated numbers can resemble Simpson's paradox. It does not mean every aggregate is wrong. It means the relationship between group composition and outcomes must be understood before interpreting a headline metric.

The experimentation service had assigned variants at first exposure, but the frontend had also allowed a marketing query parameter to force a particular variant for preview links. One campaign accidentally used a preview link in production. That bypassed random allocation for some visitors.

Basil fixed the preview mechanism to require internal authorization and ensured that public assignment came from the experiment service. Mika proposed keeping analysis restricted to valid assignments and reporting sample sizes and uncertainty, not only a heroic-looking percentage uplift.

Alina asked whether the test should run another week. Nadia asked what decision they needed to make. Was the goal to detect any statistical difference, or to decide whether a change was worth its product, support, and engineering costs? An improvement in a click metric could coexist with more refunds, lower lesson completion, or worse outcomes for users on slower devices.

They agreed on a primary subscription outcome and several guardrail metrics: refund rate, successful first-lesson start, time to usable lesson, and support contacts. They also set the intended duration and stopping rules before looking at the next round of results, rather than peeking daily and declaring victory at the first convenient green bar.

## The dashboard that needed three databases

TempoRoom collected operational events in PostgreSQL, delivered product events through a queue, and built analytics tables in a column-oriented system optimized for scanning large volumes of measurements. Someone suggested replacing the whole arrangement with a single enormous PostgreSQL database because having multiple data systems seemed complicated.

Nadia agreed that complexity was real. But the company had different questions. Billing needed strict transactional rules: a subscription should not become active twice because two webhook deliveries arrived. The product team needed large aggregations over events: cohort conversion, retention, lesson starts, and campaign performance. The recommendation service needed quick access to current user preferences. One tool could serve all three at small scale, but the performance and consistency demands were diverging.

The analytics store was a derived copy, not the authority on subscription truth. Events traveled from the transactional system through a durable publication mechanism. A temporary lag might make a dashboard a few minutes old. That was acceptable for product analysis; it was unacceptable for deciding whether someone could access a paid lesson immediately after purchase.

They had previously tried to join raw frontend events with billing records through a giant query every time somebody loaded a dashboard. It worked in testing. Once the event table grew, a filter and sort on millions of rows forced the database to do expensive work before returning a tiny chart. Adding a few indexes helped some queries, but the design still mixed a transactional workload with a large analytical scan.

Nadia's team precomputed well-defined daily aggregates with documented dimensions and retained lineage back to the source events. The dashboard became quick, while analysts could still run careful deeper queries on the analytical store. They also implemented reconciliation to detect missing or duplicated transfers between systems.

Alina asked whether they could simply cache the old chart forever, since weekly conversion didn't change quickly. Nadia said cache freshness had to match the business question. A dashboard for last quarter could be cached aggressively. A live launch guardrail needed recent data and a visible “last updated” time. A faster old answer is not automatically a better answer.

## The argument over what to change next

The experiment review turned into an argument about causality. Alina believed fewer signup fields had improved conversion. Basil thought the real benefit came from avoiding an eight-request frontend waterfall. The design researcher suspected the new lesson preview did most of the work. The experiment had changed all three at once. It could show whether the package worked under its conditions, but it couldn't precisely attribute the improvement to each component.

They could run smaller follow-up experiments, but doing so had a cost. Each variant needed design work, engineering support, enough eligible traffic, and enough time to observe meaningful outcomes. A low-traffic category might need weeks before the team could distinguish signal from noise. Some individual effects could also interact, so separating changes wasn't guaranteed to give a tidy additive explanation.

Mika suggested inspecting latency by device and connection type. If reducing dependent calls made the biggest difference on high-latency mobile connections, that would support Basil's theory. The team found that the performance improvement was indeed larger on slow connections. But they didn't confuse a plausible mechanism with a complete causal proof; the new content might also have helped those users.

Basil added network timing and web-vitals measurements around the onboarding flow, while avoiding instrumentation so heavy that it would itself slow the page. They measured client-observed time, not only server handler duration. One dashboard had proudly shown that the API completed in forty milliseconds. Users on weaker devices sometimes waited several seconds before the lesson could be used. Both numbers were accurate because they measured different boundaries.

The team also checked that the experiment did not simply move friction to a later stage. Making signup effortless could increase registrations while reducing the share of people who completed a lesson or retained a subscription. Their product story needed to extend from first click to sustained value, with no invented certainty about what a single short test proved.

## The Friday deployment that passed every test

While the analysts investigated, Basil's team shipped a separate improvement: a player that preloaded the first lesson and reduced the delay between signup and useful content. The code review looked routine. Unit tests passed, type checks passed, and the CI pipeline produced the right artifacts.

The canary deployment told another story. On desktop, first-lesson starts improved. On older phones, JavaScript execution time increased, the loading screen stayed visible longer, and some users abandoned the page. The interface downloaded a large recommendation package before it could make the player interactive. The old flow had been slower for people with good connections, but the new one was worse on devices with limited CPU and memory.

Basil inspected real-user monitoring rather than extrapolating from his development laptop. The backend's response time remained excellent. The delay occurred after data arrived, as the browser parsed and executed code and constructed the player. The team moved noncritical work out of the initial interaction path, split code where it actually reduced necessary work, and displayed playable content before optional recommendations finished.

The canary also uncovered a segment-specific API error. A new client sent a field the older backend instances didn't understand during a rolling release. The contract had not been backward compatible across overlapping versions. The team deployed the tolerant backend first, then the frontend, and added a compatibility check to the release pipeline.

A product feature can be statistically promising and operationally harmful at the same time. Alina approved the corrected release only after seeing that the guardrails were stable in the devices and markets where TempoRoom actually had customers.

## The strange case of the corrected number

Once the reporting pipeline was rebuilt, Alina asked to compare the new results with the historical dashboard. That sounded straightforward until Nadia looked at prior releases. The meaning of `checkout_complete` had changed three times. In one period it meant the browser reached a success page. In another it meant the payment provider returned an authorization. Later it meant the subscription was recorded as active. A time series with the same event name did not necessarily represent the same thing across time.

The data team added metric definitions with versioned logic, owners, and links to the source systems. They wrote down what counted as a conversion, how refunds affected reporting, which customers were included, and how late-arriving events were handled. When definitions changed, they made that visible instead of silently backfilling a chart to tell a nicer story.

An engineer suggested that the team solve the whole problem with a bigger analytics vendor. Nadia said new software could make queries easier, but it couldn't decide what “subscribed” meant, who owned the authoritative event, or which data was collected with permission. Buying a platform didn't buy agreement on business definitions.

The corrected six-percent uplift survived the stricter measurement and a cleaner rerun. Alina stopped describing it as “eleven percent more customers.” She described it as evidence that the redesigned onboarding improved the specified paid-conversion outcome under the tested conditions, while remaining compatible with the other product guardrails. It was less catchy, but everyone in the room knew what it meant.

## Monday morning — The system that can answer the wrong question perfectly

Alina opened the weekly dashboard and noticed that refund rate had dropped during the experiment. The team almost celebrated again, until customer support pointed out that refunds were processed several days after a purchase. The new customers had simply not been around long enough to request them. A measurement made at different stages in a customer's lifecycle can give the impression of improvement merely because one group has had less time to experience a bad outcome.

Nadia defined observation windows for the metrics and separated early indicators from mature outcomes. They could measure immediate lesson starts after signup, but thirty-day retention required thirty days or an explicitly modeled estimate with known limitations. The temptation to label every fast indicator a final outcome was strong because business decisions rarely waited for perfect data. Still, the dashboard needed to say whether a number was preliminary.

The payment provider also changed how it delivered settlement notifications during the test. Some events arrived later than before. The ingestion pipeline processed them correctly, but the daily conversion chart shifted as late events appeared. Nadia designed reports around event time and processing time separately. A purchase occurring on Monday might be recorded in the analytical system on Tuesday, and that shouldn't silently redefine which day the purchase belonged to.

Basil asked if the team should make every metric real-time. Nadia said no. Real-time analytics demanded additional pipelines, operational complexity, and careful correction when delayed data arrived. A practical dashboard could show rapidly updating operational indicators while marking final business metrics as reconciled only after an appropriate delay. The engineering task was to provide the right certainty at the right time, not to make every number move constantly.

The product review became shorter once those meanings were agreed. People stopped arguing over which screenshot was true and began discussing which business decision the evidence could support. That was less exciting than a green conversion chart, but it saved the team from spending another month optimizing a misleading proxy for success.

## The question of what a win costs

By week three, the onboarding redesign produced a smaller but more credible improvement in paid subscriptions. The lesson-start metric improved as well. Yet the revenue team asked whether the difference was large enough to justify keeping the experiment's extra infrastructure and maintaining two onboarding implementations.

Priya, the staff engineer, said an experiment flag was meant to support a decision, not become a permanent museum piece. Keeping both paths forever multiplied testing, made analytics harder to interpret, and increased the chance of old code breaking during unrelated changes. Once the decision was stable, the winning path should become the ordinary path and the unused branch should be removed deliberately.

The team documented what it knew and what remained uncertain. They could estimate the subscription uplift within a range, but no experiment could prove future behavior would remain identical after market conditions changed. They could claim the redesigned flow had improved a particular measured outcome under the tested conditions, not that it universally made users happier.

Support noticed fewer tickets asking why the first lesson wasn't available immediately after payment. That was not the metric the experiment originally targeted, but it mattered to the customer experience. The backend now treated completed payment, subscription entitlement, and browser navigation as separate states, each with explicit transitions. A successful payment wasn't assumed merely because the user saw a success screen; the billing record was authoritative. If the customer refreshed during an uncertain provider response, the UI could recover from durable status rather than inventing a second purchase.

At the retrospective, Alina admitted that she initially wanted the biggest green number. Nadia admitted she sometimes treated data quality as a reason to delay any decision. Basil said the product had finally forced the teams to understand one another's boundaries. They had all been partly right about the risks they cared about.

TempoRoom did not emerge with a perfect metric. It emerged with a stronger chain from an actual business event, through a durable identity, into an analytics model, through a statistical comparison, and finally into an engineering release that worked on real devices.

The original result had been an eleven-percent win. The corrected result was less dramatic. It was also something they could reasonably act on.

That distinction is the reason experiments belong in software engineering rather than in a separate room labeled “marketing numbers.” The meaning of a measurement depends on how a browser emits it, how an API records it, how queues deliver it, how databases preserve it, how analysts group it, and how product teams translate it into a decision.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Connections:** CS120-L02/L03/L04 (probability, sampling, experiments and causality); SE215-L10 (product, design, analytics); SE240-L03/L05 (frontend state and performance); SE250-L02/L03 (effects and server state); SE310-L01 (API contract); CS330-L01/L02/L03 (relational modeling, queries, transactions); CS340-L01/L06 (data-system selection, analytical workloads); SE320-L03 (durable events, duplicate delivery); CS430-L01 (idempotency and uncertainty); SE340-L04 (CI/CD); SE440-L01 (observability).

**Technical caveats:** A conversion event is not necessarily authoritative business truth. Nonrandom allocation can bias a comparison; segmentation alone does not repair an invalid experiment. Statistical significance, practical impact, and causal validity are distinct. The fictional data architecture is one reasonable design, not a universal requirement.

**Optional reflections:** Which event should define “became a subscriber”? How would you prevent experiment preview links from corrupting allocation? Why does a faster backend not guarantee a better onboarding experience?
