---
id: SE215-L02
course: SE215
title: "How Engineering Work Gets Planned and Delivered"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L01
next: SE215-L03
---


# SE215 — The Software Engineering Ecosystem

## Lecture 02: How Engineering Work Gets Planned and Delivered

*Six engineers are working full-time. Their calendar is packed with meetings, their Jira board contains dozens of active tickets, and everyone is reporting progress. Yet the company hasn't delivered a meaningful product improvement in six weeks. How can a team be constantly busy and still accomplish so little?*

# Part I — Intuition

## The picture to carry in your head

Imagine a restaurant with six chefs.

Every chef is working hard.

One starts preparing a steak. Another starts a soup. Someone begins decorating a dessert. Another opens three orders simultaneously because all three seem urgent.

The kitchen is full of activity.

Ingredients are being chopped, pans are heating, and everyone looks productive.

But customers aren't receiving their meals.

The steak needs a side dish. The soup is waiting for an ingredient. The desserts aren't ready to serve. Every chef is occupied, so nobody is available to help finish the orders already underway.

The restaurant's problem isn't insufficient effort.

It's the way work flows through the kitchen.

Now replace the restaurant with a software company.

Six engineers are working on a hotel-booking platform.

One is implementing reservation-date changes. Another is building a pricing API. A third is refactoring authentication. Two developers are handling unrelated frontend features. The final engineer keeps getting interrupted by production bugs.

Every task is important.

Every developer is busy.

But almost nothing reaches production.

This is the central problem of engineering work organization.

**The objective isn't to keep every engineer busy. It's to move valuable work from an idea to a useful, reliable product outcome.**

## 1. Software work is a flow, not a collection of personal tasks

A feature usually moves through several stages.

Somebody identifies a need.

The team clarifies the requirements.

Developers implement the change.

Other engineers review it.

Automated tests run.

The application is deployed.

The new behavior is verified.

Only then can customers benefit from the change.

The work passes through a sequence of dependencies, even when several activities happen in parallel.

A developer completing their implementation doesn't necessarily mean the feature is complete.

If the pull request sits unreviewed for four days, no customer benefits from it.

If the backend is complete but the frontend isn't, the full experience may remain unavailable.

If the deployment is delayed for another week, the work is still waiting to produce value.

A useful engineering organization therefore cares about the **flow of completed work**, not simply the amount of work started.

## 2. Starting more can make finishing slower

Suppose each engineer begins three tasks.

Now eighteen pieces of work are in progress.

Every task introduces context, unfinished decisions, dependencies, and potential interruptions.

When a developer switches between tasks, they must reconstruct where they left off.

When another developer needs assistance, everyone is already committed to something else.

Code reviews wait.

Integration testing waits.

Deployment decisions wait.

The number of active tasks becomes large while the number of completed features remains small.

This is why limiting work in progress can improve delivery.

Instead of encouraging every engineer to start something new whenever they're blocked, the team may benefit from helping complete work already underway.

The goal isn't inactivity.

It's reducing the distance between starting something and finishing it.

## 3. Planning exists because the future is uncertain

Imagine the product manager asks:

"How long will the date-change feature take?"

You might estimate three days.

Then discover that it requires a database migration, payment-provider integration, and new test infrastructure.

Your original estimate was based on incomplete information.

Software development frequently involves discovering the work while performing it.

That makes exact prediction difficult.

But it doesn't make planning useless.

A good plan identifies what we know, what we don't know, what matters most, and which decisions need to be made next.

It also creates opportunities to adapt when reality differs from our assumptions.

This is the useful intuition behind Agile approaches.

Agility isn't the ability to change priorities randomly every afternoon.

It's the ability to learn and adjust while maintaining a coherent direction.

## 4. Two ways to organize the same kitchen

There are many approaches to organizing software work.

Two particularly influential ones are Scrum and Kanban.

**Scrum** uses short, structured cycles called Sprints. A team works toward a Sprint Goal, inspects progress, delivers usable increments, and adapts its plans.

**Kanban** focuses on making work visible, controlling how much is in progress, managing its flow, and improving the process using evidence.

The two aren't simply competing brands.

They emphasize different coordination mechanisms, and teams can combine useful practices when the combination is coherent.

Scrum asks how a team can pursue valuable goals through repeated planning and feedback cycles.

Kanban asks how work moves through a system and what prevents it from flowing efficiently.

Neither approach can rescue a team that refuses to make priorities clear or address genuine bottlenecks.

## Three questions before the Deep Dive

1. Why might reducing the number of tasks being worked on increase the number of tasks completed?
2. Why isn't a developer's finished pull request necessarily a delivered product improvement?
3. If estimates are uncertain, what is the point of planning at all?

Keep our six-person booking team in mind as we examine how software work is actually organized.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The team that completes tickets but misses every release

Our fictional company, Mercury, operates a hotel-booking platform.

It has six software engineers, a product manager, and access to shared design, security, and infrastructure specialists.

The company wants to introduce self-service reservation changes.

Customers should be able to modify their booking dates without contacting support.

The team estimates that the feature will take roughly two weeks.

At the beginning of the first week, everyone starts working.

One developer builds the new frontend.

Another develops the reservation-modification endpoint.

A third works on payment handling.

A fourth starts a database migration.

The remaining engineers are assigned technical improvements and existing bugs.

By Friday, almost every ticket shows activity.

But nothing can be released.

The frontend expects an API response shape that the backend doesn't provide.

The payment workflow depends on a design decision that hasn't been made.

The database migration introduces a compatibility problem.

Several pull requests are waiting for review.

Then a production incident interrupts the second week.

The product manager asks for an updated delivery date.

Nobody can give a defensible answer.

Everyone knows how busy they've been.

Nobody knows how much coherent, releasable functionality remains.

The problem isn't necessarily poor developers.

It's an ineffective delivery system.

Let's examine the concepts that would help the team understand and improve it.

## 2. Agile: a philosophy, not a calendar of meetings

The word *Agile* appears constantly in software companies.

Job descriptions ask for Agile experience.

Recruiters ask about Scrum.

Managers discuss story points and sprint velocity.

Developers sometimes respond with a weary sigh.

Part of the problem is that Agile is often confused with a particular collection of ceremonies.

But Agile software development is fundamentally concerned with delivering useful software, collaborating with customers and colleagues, learning through feedback, and responding intelligently to change.

The idea isn't that planning and documentation are worthless.

It's that a plan can become inaccurate as knowledge evolves, and the organization must be capable of responding.

### The dangerous interpretation of flexibility

Suppose Mercury's product manager changes the team's highest priority every morning.

Monday: reservation changes.

Tuesday: a new loyalty programme.

Wednesday: an administrative dashboard.

Thursday: an urgent redesign.

Friday: return to reservation changes.

Someone might describe this as being highly Agile.

It isn't necessarily.

The team may have no stable opportunity to complete anything.

Useful adaptability depends on purposeful prioritization.

A good team can respond to genuinely important new information without treating every interruption as equally valuable.

**Agility means adapting to reality, not abandoning direction.**

## 3. Scrum: short cycles around a meaningful goal

Scrum is a framework for developing complex products.

Its official definition includes accountabilities, events, artifacts, and commitments.

The terminology matters because many companies claim to practice Scrum while implementing something quite different.

The three accountabilities are Product Owner, Scrum Master, and Developers.

These are not necessarily three job titles occupied by three separate departments.

They're responsibilities within the Scrum Team.

### The Product Owner

The Product Owner is accountable for maximizing product value and effectively managing the Product Backlog.

At Mercury, that includes making the priorities surrounding reservation changes clear.

Perhaps the first release should support date changes that don't require additional payment.

That smaller scope could provide substantial customer value without introducing every complication immediately.

The Product Owner doesn't necessarily decide the implementation architecture.

But the team needs a clear view of which outcomes matter most.

### The Scrum Master

The Scrum Master is accountable for establishing Scrum and helping the team improve its effectiveness.

This isn't simply someone who schedules meetings and asks people for status updates.

A useful Scrum Master helps identify obstacles, improve collaboration, and make the framework serve its intended purpose.

### Developers

The Developers are accountable for creating usable increments and planning how to achieve the work.

This includes quality, collaboration, and adapting their technical plan as necessary.

They're not merely recipients of tasks assigned from outside.

### The Sprint

Scrum organizes work into Sprints of one month or less.

Each Sprint creates a short period for pursuing a goal, inspecting the result, and adapting.

A Sprint isn't merely a container for random tickets.

It should have a coherent **Sprint Goal**.

For Mercury, the goal might be:

"Enable customers to preview an eligible reservation-date change and receive a reliable confirmation without involving customer support."

That's more useful than a list of unrelated tasks because it expresses a meaningful result.

## 4. Scrum events: why these meetings exist

Let's inspect the events without treating them as a ceremonial religion.

### Sprint Planning

The team considers why the Sprint is valuable, what can be done, and how the selected work will be approached.

It develops a Sprint Goal and a plan.

Developers participate in selecting and organizing work based on what they understand about their capacity and the technical problem.

The goal is not to make an infallible prediction.

It's to establish a reasonable, shared direction.

### Daily Scrum

The Daily Scrum is a short opportunity for Developers to inspect progress toward the Sprint Goal and adapt their plan.

In the official framework, it's a fifteen-minute event.

It isn't fundamentally a meeting where every developer reports activity to a manager.

A useful discussion might reveal that the frontend and backend teams have incompatible assumptions about the booking API.

Then the team can resolve that issue while it is still manageable.

### Sprint Review

At the Sprint Review, the team and relevant stakeholders inspect the outcome of the Sprint and discuss what to do next.

A demonstration may be useful, but the event is more than a performance showing how many tickets were closed.

The product may behave differently from what stakeholders expected.

New information may change priorities.

The purpose is feedback and adaptation.

### Sprint Retrospective

The Retrospective examines how the team's way of working could improve.

Perhaps pull requests spent too long waiting for review.

Perhaps requirements were repeatedly discovered after implementation began.

Perhaps the team accepted too many parallel commitments.

The Retrospective should produce actionable improvements, not a collection of complaints that nobody revisits.

### A technical detail worth knowing

Scrum includes the Product Backlog, Sprint Backlog, and Increment as artifacts.

They are associated respectively with the Product Goal, Sprint Goal, and Definition of Done.

The distinction is important: Scrum isn't simply sprint planning plus daily status meetings. It connects objectives, current work, and a shared standard for usable results.

## 5. What does "done" actually mean?

Return to Mercury's frontend developer.

Their component is implemented.

The TypeScript compiler passes.

The pull request is open.

Is the feature done?

Almost certainly not.

Now suppose the pull request has been approved and merged.

Is it done?

Still not necessarily.

The backend integration may not work.

The feature may not have been deployed.

Its acceptance criteria may remain unverified.

### Definition of Done

A Definition of Done establishes the quality and completeness conditions required for an Increment to count as done.

It may involve integration, testing, security, documentation, or other relevant quality measures.

The exact requirements depend on the product and organization.

But one important distinction is universal:

**Implementation progress and usable, completed work are not the same thing.**

### Definition of Done versus acceptance criteria

The Definition of Done concerns the shared standard of quality for the product Increment.

Acceptance criteria concern what a particular feature or backlog item must accomplish.

For our date-change feature, acceptance criteria might state:

A customer may choose new dates only when their booking policy permits changes.

The system must not confirm new dates when inventory cannot be allocated.

A successful change must have a stable operation identifier.

An uncertain payment outcome must not be presented as a definite failure.

These describe behavior specific to the feature.

The Definition of Done may additionally require tests, review, integration, and other quality expectations.

A ticket can satisfy its functional acceptance criteria while still failing the team's broader completion standard.

## 6. Splitting work vertically instead of horizontally

Our Mercury team originally divided the project into frontend, backend, database, and payment tickets.

That can be useful for organizing engineering work.

But it creates an important risk.

Each ticket may be completed independently without delivering anything the customer can use.

This is called a horizontal decomposition.

The work is divided by technical layer.

A **vertical slice** instead delivers a small, coherent behavior across the necessary layers.

For example, the first slice might let the customer view their existing reservation and see whether date changes are permitted.

The second slice might let them select alternative dates and receive a quote.

The third might support confirmation when no additional payment is required.

The fourth might introduce payment adjustments.

Each slice requires some frontend, backend, and persistence work.

But each can produce an independently testable capability.

### Why vertical slices help planning

They expose integration problems earlier.

They produce useful feedback sooner.

And they give the team opportunities to reduce scope without ending with four disconnected technical components.

Not every vertical slice must be immediately visible to end users.

Some infrastructure or architectural changes are necessary foundations.

But if a product team repeatedly finishes technical components without completing useful behaviors, it should question its decomposition.

The objective is to minimize the distance between work and validated value.

## 7. Estimation: useful uncertainty versus fake precision

Now the product manager asks the difficult question.

"When will the date-change feature be ready?"

The honest answer depends on what has been clarified.

Some work may be familiar.

Other work may contain significant uncertainty.

The payment provider's behavior might be poorly documented.

The inventory schema may require changes.

The test environment may not support reliable concurrent-booking tests.

A good estimate should reflect those uncertainties.

### Hours and days

An engineer may estimate the effort required for a relatively familiar task.

For example, updating a simple validation rule might take a few hours.

But effort isn't necessarily elapsed delivery time.

A two-hour code change can take four days to reach production if it waits for review, integration testing, and deployment approval.

Distinguish the time spent actively working from the time spent moving through the delivery system.

### Story points

Some teams use story points to express relative size, effort, complexity, or uncertainty.

The intended interpretation differs between organizations.

A team might consider one task roughly comparable to another and estimate it at three points rather than eight.

But story points are not standardized hours.

Five points in one team do not necessarily mean the same thing as five points in another.

And story points are not a required element of Scrum.

They are an optional estimation technique.

### Why velocity becomes dangerous

Velocity usually refers to the quantity of estimated work completed during a Sprint.

A team may use its historical velocity for forecasting.

But problems arise when management treats it as a productivity score.

Suppose Mercury's engineers previously completed thirty points per Sprint.

Now they're told to complete forty.

The team can increase its numerical velocity by assigning more points to the same work.

Nothing useful has improved.

Worse, developers may feel pressure to prioritize point completion over product outcomes.

**A measurement that is useful for forecasting can become harmful when treated as an individual performance target.**

### Forecasting instead of promising

A more useful approach expresses uncertainty explicitly.

Given similar past work and current capacity, the team might expect to deliver a particular scope within a range of dates.

That forecast should be revisited as uncertainty decreases.

If the business has a fixed deadline, scope may need to vary.

If scope is fixed, timing and capacity constraints become more important.

Planning is a process of choosing trade-offs, not eliminating uncertainty through confident language.

## 8. Kanban: control the flow of work

Now suppose Mercury's engineering team handles a constant stream of work.

Production defects arrive unpredictably.

Small improvements compete with feature development.

Urgent customer issues interrupt planned tasks.

A continuous-flow approach may be attractive.

This is where Kanban becomes useful.

Kanban is a strategy for optimizing the flow of value through a process.

Its practices include defining and visualizing the workflow, actively managing work items, and improving the workflow.

Simply creating columns labeled To Do, In Progress, and Done is not sufficient to implement the full approach.

The team needs explicit working policies.

### Visualizing the workflow

Imagine Mercury uses the following states:

Ready.

Development.

Code Review.

Verification.

Ready for Release.

Done.

Every work item moves through the relevant states.

This makes waiting visible.

If twelve items pile up in Code Review, the problem becomes difficult to ignore.

### Limiting work in progress

Now introduce a limit on active development work.

Instead of starting another task whenever a developer has a spare hour, the team checks whether existing work can be completed.

Perhaps the best next action is reviewing another developer's pull request.

Perhaps it's helping resolve a test failure.

Perhaps it's unblocking a deployment.

This creates a **pull-oriented workflow**.

New work is started when the system has capacity, rather than simply pushed into every available person's task list.

The purpose isn't to keep arbitrary columns numerically below a threshold.

It's to improve the flow of work and expose constraints.

## 9. The four flow metrics worth understanding

Kanban's current guide emphasizes four core flow metrics.

These are particularly useful because they describe what actually happens to work.

### Work in Progress

WIP is the number of work items that have started but not finished.

If Mercury has eighteen active tickets and finishes only a few each week, its work is accumulating.

That may indicate too much parallelism, blocked work, or a mismatch between demand and capacity.

### Throughput

Throughput is the count of work items completed per unit of time.

For example, the team might finish six items in a week.

This number needs context.

A tiny documentation change and a complex payment integration aren't equivalent in business value or effort.

Still, historical throughput can help forecast delivery when work-item definitions and distributions are reasonably stable.

### Work Item Age

Work Item Age is the elapsed time since a currently active item started.

Suppose most tasks finish within several days, but one reservation item has been open for three weeks.

Its age is a warning signal.

The team should investigate why it hasn't progressed.

Perhaps it is blocked by an unresolved decision.

Perhaps it is too large.

Perhaps nobody owns its completion.

### Cycle Time

Cycle Time measures elapsed time from when an item started to when it finished, according to the team's explicit workflow definition.

This includes waiting within that defined interval.

A developer may spend only four hours coding a change, while its cycle time is five days because of reviews, tests, and release queues.

That difference is important.

**The customer experiences elapsed delivery time, not just the developer's active coding time.**

### Service Level Expectation

Kanban also uses a Service Level Expectation, or SLE, as a forecast about how long work should take.

For example, based on historical data, a team might expect eighty-five percent of comparable items to finish within eight days.

That's a probabilistic expectation, not a guarantee that every item will be done in eight days.

It creates a useful reference for identifying aging work and communicating uncertainty.

## 10. Why more parallel work often means more waiting

Let's connect these metrics.

Suppose Mercury starts many tasks because management believes this keeps everyone maximally productive.

But the team has limited review capacity.

Every new task eventually enters the review queue.

As the queue grows, work spends more time waiting.

Developers begin switching to other tasks while their earlier work remains unfinished.

That creates more active work, more context switching, and more waiting.

The cycle reinforces itself.

This is a familiar phenomenon in queueing systems.

Increasing work entering a system beyond its ability to complete work produces growing queues.

Little's Law describes a relationship between average work in progress, throughput, and average time in the system under suitable long-run stability conditions.

The intuition is useful even without treating the formula as a magic prediction tool.

If throughput stays roughly the same while average WIP grows, average time in the system tends to grow too.

That is why controlling WIP can improve predictability and reduce elapsed delivery time.

But limiting WIP alone doesn't solve every bottleneck.

If a crucial reviewer is unavailable for two weeks, the team may need to improve review ownership or capacity.

The goal is to understand the actual constraint and improve it.

## 11. Scrum versus Kanban: choose according to the work

The common interview question is:

"What's the difference between Scrum and Kanban?"

A superficial answer is that Scrum has Sprints and Kanban has a board.

That distinction is incomplete.

Scrum provides a defined framework for pursuing goals through short cycles, explicit accountabilities, inspection, and adaptation.

Kanban emphasizes managing and improving the flow of value through an explicitly defined workflow.

### When Scrum may fit well

Imagine Mercury's product team is developing a new booking experience with a clear product direction.

It benefits from repeated opportunities to establish a goal, deliver increments, and receive stakeholder feedback.

A Sprint-based cadence may be useful.

### When Kanban may fit well

Imagine Mercury's platform-support team receives unpredictable incidents, access requests, infrastructure changes, and small operational tasks.

It may benefit from continuous prioritization, explicit work policies, aging-item monitoring, and WIP controls.

Fixed Sprint commitments may be less useful for this particular workload.

### Can teams combine them?

Yes, provided they understand what they're combining.

A Scrum Team may use Kanban practices to improve its workflow.

The team may retain its Scrum events and goals while limiting WIP and measuring flow.

But combining frameworks shouldn't mean accumulating every possible meeting, chart, and metric.

The test is whether the approach improves delivery and learning.

An organization is not successful because it performs Scrum correctly according to a checklist.

It is successful when its way of working helps people deliver valuable, reliable products.

## 12. Prioritization: important isn't the same as urgent

Now Mercury faces a difficult week.

The product manager wants the reservation-date feature.

Customer support reports a confusing refund message.

Security discovers a serious authorization flaw.

A major customer requests a reporting enhancement.

Meanwhile, the database migration needs careful preparation.

Everything has an advocate.

How should the team choose?

### Value, urgency, risk, and dependencies

A useful prioritization discussion considers the value of an item, the consequence of delaying it, its risks, and the work it depends on.

The security flaw may deserve immediate attention because of the potential harm it creates.

A confusing refund message may be a small change with a substantial effect on support volume.

The major customer's reporting request may be commercially important, but its urgency should be examined rather than assumed.

The database migration may not produce visible value by itself, but it may be necessary to deliver another capability safely.

### Prioritization is a decision, not a score generator

Teams sometimes use scoring frameworks such as RICE or weighted shortest job first.

These can help structure discussions.

But a numerical score doesn't automatically capture business reality.

Estimates of impact and effort are uncertain.

Some risks cannot responsibly be traded away for higher feature throughput.

A useful prioritization technique makes assumptions visible and supports informed decisions.

It should not replace judgment.

### What should a developer do?

A developer may not own final product prioritization.

But they should contribute information about technical risk, dependencies, hidden work, and cheaper alternatives.

For example:

"We can deliver the no-additional-payment date-change flow first. That would provide meaningful customer value while we complete the more complex payment reconciliation design."

That's a technical insight translated into a product option.

It helps decision-makers choose intelligently.

## 13. Measuring delivery without corrupting the behavior

We've discussed story points and flow metrics.

What about software delivery performance itself?

DORA's research identifies useful measures of how reliably and efficiently software changes reach production.

Its current framework includes five metrics grouped around delivery throughput and instability.

For orientation, the key measures are:

**Change lead time:** How long it takes a code change to move from commit to successful production deployment.

**Deployment frequency:** How often changes are deployed.

**Failed deployment recovery time:** How long it takes to recover from a failed deployment.

**Change fail rate:** How frequently deployments cause failures requiring intervention.

**Deployment rework rate:** The share of deployments devoted to unplanned correction of previous deployment problems.

These are different from Kanban's work-item metrics.

A story's cycle time might begin when development starts and end when the feature is considered finished.

Change lead time measures a narrower delivery interval starting at a code commit.

The definitions and boundaries matter.

### Why one metric can mislead

Imagine Mercury deploys ten times per day.

That sounds impressive.

But half those deployments are emergency fixes for broken releases.

High deployment frequency alone doesn't establish effective delivery.

Now imagine a team with almost no failed deployments.

That also sounds impressive.

But perhaps the organization deploys only twice a year and avoids change through extreme caution.

The measurement needs context.

DORA's distinction between delivery throughput and instability is useful because teams should improve speed without creating unacceptable reliability problems.

### Metrics are instruments, not employee rankings

Measuring one developer by the number of commits, tickets, or story points they produce creates obvious incentives to manipulate the metric.

A senior engineer who prevents an incident through a careful architecture review may close fewer tickets than a colleague implementing small UI changes.

That doesn't make the senior engineer less productive.

Measure system performance and outcomes rather than pretending every contribution can be reduced to an individual count.

## 14. When the plan breaks: handle change deliberately

Let's return to Mercury's reservation-date feature.

It's the middle of the Sprint.

The team discovers that the payment provider sometimes returns an ambiguous timeout.

The original plan assumed every payment attempt returned a definite success or failure.

That assumption was wrong.

What happens now?

A poor organization may demand that the team preserve the original deadline and scope without discussing the new complexity.

Another poor organization may abandon the entire plan immediately.

A better approach is to assess the implications.

Does the new information threaten the Sprint Goal?

Can the team adjust the scope while preserving the desired outcome?

Should the payment-dependent portion be postponed?

Is a different implementation viable?

In Scrum, scope may be clarified and renegotiated with the Product Owner as more is learned, provided the Sprint Goal isn't endangered.

The goal creates stability.

The implementation plan can adapt.

### Make uncertainty visible early

A developer should not conceal uncertainty until the day before release.

Suppose the payment integration is blocked because a required provider capability is undocumented.

That should become visible when discovered.

The team can investigate, seek help, change scope, or adjust the forecast.

Waiting quietly for several days rarely improves the situation.

### Protect the meaning of "done"

A deadline doesn't make a defect disappear.

If a critical authorization check or inventory invariant is missing, declaring the feature complete is not a solution.

The team may reduce the feature's scope.

It may delay the release.

It may disable unfinished behavior behind a controlled feature flag.

But it should not quietly redefine correctness to make a chart look better.

## 15. The senior engineer's contribution

Suppose you're the senior full-stack engineer on the Mercury team.

You aren't necessarily the Product Owner.

You don't necessarily run Sprint Planning.

You may not be responsible for choosing Scrum or Kanban.

So what can you contribute?

First, you can identify technical uncertainty before it becomes a delivery surprise.

Second, you can help split large features into coherent, testable increments.

Third, you can make dependencies explicit.

Fourth, you can improve review, testing, and deployment workflows that delay completed work.

Fifth, you can resist pressure to substitute activity metrics for genuine outcomes.

And when priorities change, you can explain consequences without treating the new request as a personal insult.

### A practical example

The product manager says:

"We need reservation changes ready by Friday."

A weak engineering response is:

"That's impossible."

Another weak response is:

"Sure, we'll make it happen."

A stronger response might be:

"We can deliver self-service date changes that require no payment adjustment by Friday, assuming the inventory API is available tomorrow. Payment-changing reservations involve an unresolved provider failure case and need additional design and testing. We can either narrow Friday's scope or accept a later release for the complete feature."

That's useful because it gives the organization a decision.

It explains constraints.

It separates known work from uncertainty.

And it offers a viable path to value.

The senior engineer's role isn't to sound confident about impossible estimates.

It's to make technical reality legible to the people deciding what to do.

---

# The Oral Examination

Answer each question aloud before reading the solutions.

### Question 1 — Busy but not delivering

A team has ten active pull requests and five developers, but deploys almost nothing. What would you investigate before concluding that developers are working too slowly?

### Question 2 — Scrum responsibilities

What are the three Scrum accountabilities, and why is the Daily Scrum not merely a manager's status-report meeting?

### Question 3 — The wrong definition of done

A backend engineer marks a feature complete because the API implementation is merged. The frontend still cannot use it. What's wrong with the completion claim?

### Question 4 — The estimation trap

A manager asks why one team completes forty story points per Sprint while another completes twenty. Can those numbers be compared directly?

### Question 5 — Kanban flow

A team's WIP continues increasing while throughput remains relatively stable. What is likely happening to elapsed delivery time, and what might the team investigate?

### Question 6 — Scrum versus Kanban

Would you use the same work-management approach for a product feature team and an operational support team receiving unpredictable incidents? Explain the trade-offs.

### Question 7 — The late discovery

Halfway through a Sprint, engineers discover a payment-provider limitation that invalidates part of the original plan. What should happen next?

### Question 8 — Measuring delivery

Why is deployment frequency alone insufficient to determine whether a team is performing well?

---

# Solutions and Discussion

## Solution 1 — Investigate flow, not apparent effort

Look at waiting time, review queues, blocked work, integration dependencies, testing failures, deployment restrictions, and excessive context switching.

Developers may be busy while work accumulates between stages.

Reducing WIP, improving review capacity, or completing existing work may be more valuable than starting additional tasks.

## Solution 2 — Accountabilities and collaboration

The three accountabilities are Product Owner, Scrum Master, and Developers.

The Daily Scrum allows Developers to inspect progress toward the Sprint Goal and adapt their plan.

It isn't inherently a management reporting ceremony.

## Solution 3 — Implementation isn't completed product behavior

The backend code may be implemented, but the feature isn't necessarily usable.

Its acceptance criteria and the relevant Definition of Done must be satisfied.

This may require frontend integration, testing, and other work before the item genuinely counts as complete.

## Solution 4 — Story points are local estimates

Story points have no universal conversion between teams.

Different teams may use different reference tasks and estimation conventions.

Comparing their numerical velocity as an individual or team productivity ranking is unreliable and may create harmful incentives.

## Solution 5 — Work is accumulating

If work enters the system faster than it leaves, queues and waiting times tend to grow.

Investigate bottlenecks, aging items, excessive parallelism, blocked dependencies, and whether the team's workflow policies are effective.

Control WIP where appropriate, but also address the underlying constraint.

## Solution 6 — Match the coordination style to the work

A product team pursuing coherent goals may benefit from Scrum's repeated planning and feedback cycles.

An operations team with unpredictable demand may benefit from Kanban's flow management and explicit WIP controls.

The approaches can be combined thoughtfully, but neither should be applied mechanically.

## Solution 7 — Replan around the goal

Make the new constraint visible.

Evaluate whether the Sprint Goal remains achievable.

Clarify or renegotiate scope with the Product Owner, involve relevant specialists, and revise the forecast.

Do not conceal the problem or quietly relax essential correctness conditions.

## Solution 8 — Speed without stability is incomplete

Frequent deployments may be accompanied by high change-failure rates and substantial rework.

Evaluate throughput alongside instability and recovery.

Also consider product outcomes and the nature of the team's work.

---

# The Mental Model Worth Keeping

A software team's performance is not the sum of its members' apparent busyness.

It is the ability to **select valuable work, complete it reliably, learn from the result, and improve the delivery system**.

Remember four questions:

**Direction:** Are we working on the most valuable problem?

**Flow:** How quickly does work move from started to genuinely finished?

**Quality:** Does completed work satisfy the necessary product and engineering standards?

**Adaptation:** Can we respond to new information without losing coherence?

Scrum provides one structured way of pursuing goals and learning through short cycles.

Kanban provides a way of understanding and improving continuous work flow.

Metrics help reveal problems, but they don't replace judgment.

**The purpose of engineering process is to help people deliver useful software—not to create more evidence that everyone was busy.**

# Next Lecture — SE215-L03: Git, Pull Requests, and Collaborative Delivery

We've learned how teams choose and organize work.

Now imagine Mercury's developers have agreed on priorities, reduced WIP, and begun delivering small, coherent improvements.

But one urgent production fix must ship immediately.

Three other features are unfinished.

Two developers changed the same files.

A pull request has accumulated hundreds of commits.

And the release branch contains code that shouldn't reach customers yet.

How should engineers collaborate through Git without turning every merge and release into an emergency?

In SE215-L03, we'll examine the practical choices behind branching strategies, pull requests, rebasing, merge policies, trunk-based development, code review, and release coordination.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Repair Mercury's Delivery Process

## Exercise A — Diagnose the bottleneck

The Mercury team has six engineers.

Its board contains:

| Workflow state | Work items |
|---|---:|
| Ready | 12 |
| Development | 9 |
| Code Review | 7 |
| Verification | 5 |
| Ready for Release | 4 |

The team completes approximately five or six work items per week, but many new items are started before older work finishes.

Discuss:

1. What does the distribution suggest?
2. Which items would you inspect first?
3. How might you reduce excessive parallelism?
4. What information is missing before deciding that code review is the bottleneck?
5. How would you measure whether your intervention helped?

Do not automatically assume that every large column represents a bottleneck. Inspect item ages, arrival and departure rates, policies, and dependencies.

## Exercise B — Split a feature vertically

The original product request is:

"Customers should be able to change reservation dates."

The proposed work breakdown is:

- Build complete frontend.
- Build complete backend.
- Create database migration.
- Implement payment integration.
- Write all E2E tests.
- Release feature.

Redesign it as a series of small, independently testable behavioral increments.

A possible sequence:

1. Show whether a reservation is eligible for date modification.
2. Let the customer preview alternative dates and pricing.
3. Support confirmation when no additional payment is required.
4. Introduce additional-payment flows.
5. Introduce partial refunds or more complex booking policies.

For each increment, identify the frontend, backend, testing, and deployment work required.

Explain why this approach may reduce integration risk.

## Exercise C — Write acceptance criteria

Choose the first date-change increment.

Write specific acceptance criteria.

For example:

**Given** a confirmed reservation that permits changes,  
**when** the customer requests an alternative valid date range,  
**then** the application displays a valid quote without changing the existing reservation.

Now add cases covering:

- Invalid date ranges.
- Unavailable inventory.
- Expired or canceled reservations.
- Unauthorized customers.
- Network failure.
- An expired quote.

Distinguish feature-specific acceptance criteria from the team's general Definition of Done.

## Exercise D — Design a Kanban policy

Create a small workflow with:

- Ready
- Development
- Review
- Verification
- Done

Specify when an item is considered started and finished.

Choose illustrative WIP controls.

Define who may pull new work and what should happen when a pull request is blocked.

Create an initial Service Level Expectation, explicitly identifying whether it is based on historical data or merely a provisional assumption.

Then decide which metrics to inspect weekly.

## Exercise E — Interview rehearsal

Prepare a two-minute answer to:

"Tell me about a time your team missed a deadline or encountered changing requirements. How did you handle it?"

Your response should include the original objective, the newly discovered uncertainty, your personal contribution, the trade-offs discussed, and the eventual outcome.

Avoid vague claims such as "we followed Agile" or "we communicated well."

Explain what changed in the team's decisions or delivery behavior.

---

# Further Reading

Primary references:

- **The Scrum Guide (official, November 2020):** https://scrumguides.org/scrum-guide.html
- **The Kanban Guide (May 2025):** https://kanbanguides.org/the-kanban-guide/
- **Agile Manifesto:** https://agilemanifesto.org/
- **DORA — Software Delivery Performance Metrics:** https://dora.dev/guides/dora-metrics/
- **DORA — Continuous Delivery:** https://dora.dev/capabilities/continuous-delivery/

Additional reading:

- **Accelerate**, Nicole Forsgren, Jez Humble, and Gene Kim
- **The Principles of Product Development Flow**, Donald G. Reinertsen
- **Actionable Agile Metrics for Predictability**, Daniel S. Vacanti

Related programme chapters:

- SE215-L01 — The People and Teams Behind Software
- SE215-L03 — Git, Pull Requests, and Collaborative Delivery
- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE330-L03 — Maintaining and Evolving Real Software
- SE340-L04 — CI/CD and Infrastructure as Code
- SE440-L02 — Reliability Engineering and Incident Response

---

## Dense Cheatsheet — Interview Glance Card

```text
SE215-L02 — ENGINEERING WORK PLANNING AND DELIVERY

CORE PRINCIPLE
  Busy developers != valuable completed work
  Optimize flow from idea to reliable product outcome
  More WIP can increase queues, switching, and waiting

AGILE
  Collaborate, deliver usable software, learn, adapt
  Agility != changing priorities randomly
  Planning is useful despite uncertainty

SCRUM
  Framework for complex product development
  Sprint <= 1 month
  Scrum Team accountabilities:
    Product Owner — product value / Product Backlog
    Scrum Master — framework and team effectiveness
    Developers — create usable Increment

SCRUM EVENTS
  Sprint Planning — why, what, how
  Daily Scrum — inspect and adapt toward Sprint Goal
  Sprint Review — inspect product outcome with stakeholders
  Sprint Retrospective — improve team effectiveness
  Sprint itself is the containing event

SCRUM ARTIFACTS / COMMITMENTS
  Product Backlog -> Product Goal
  Sprint Backlog -> Sprint Goal
  Increment -> Definition of Done

DONE VS ACCEPTED
  Acceptance criteria = behavior of specific item
  Definition of Done = shared quality/completeness standard
  Code merged != feature delivered
  Implementation progress != usable product increment

VERTICAL SLICES
  Horizontal: frontend, backend, database, testing as
              separate deliverables
  Vertical: small coherent behavior across required layers
  Enables earlier integration, testing, and feedback
  Some foundational technical work may still be necessary

ESTIMATION
  Effort != elapsed delivery time
  Estimate with known constraints and explicit uncertainty
  Story points = optional relative estimates, not hours
  Scrum does not require story points
  Velocity is team-local, not a universal productivity score
  Forecast using evidence; avoid fake certainty

KANBAN
  Optimize flow of value
  Define and visualize workflow
  Actively manage work items
  Improve workflow
  Board alone != complete Kanban approach
  Define start, finish, states, policies, WIP controls, SLE
  Pull new work when capacity exists

KANBAN FLOW METRICS
  WIP = started but unfinished items
  Throughput = items finished per unit of time
  Work Item Age = elapsed time of currently active item
  Cycle Time = elapsed time from start to finish
  SLE = probabilistic forecast for finishing work

FLOW
  Queues form when arrival exceeds completion capacity
  Excessive WIP increases waiting and context switching
  Little's Law relates WIP, throughput, and flow time
  under suitable stability conditions
  Reduce WIP and address real bottlenecks

SCRUM VS KANBAN
  Scrum: goal-focused short cycles, defined accountabilities
  Kanban: explicit workflow and continuous flow optimization
  They can complement one another
  Choose based on work pattern and feedback needs

PRIORITIZATION
  Consider value, urgency, risk, dependencies, cost of delay
  Important != urgent
  Scoring frameworks are aids, not substitutes for judgment
  Technical risks and hidden dependencies must be surfaced

DORA DELIVERY METRICS
  Change lead time
  Deployment frequency
  Failed deployment recovery time
  Change fail rate
  Deployment rework rate
  Measure throughput and instability together
  Deployment metrics != Kanban work-item cycle time

COMMON FAILURES
  Too many active tasks
  No coherent product goal
  Horizontal tickets never integrate
  Reviews and testing form queues
  Estimates treated as commitments
  Velocity used as employee ranking
  Scope changes without explicit trade-offs
  "Done" redefined to meet a deadline

SENIOR ENGINEER CONTRIBUTION
  Expose uncertainty early
  Split work into coherent increments
  Clarify dependencies and acceptance criteria
  Help finish work, not merely start more
  Explain risks and delivery options to stakeholders
  Defend correctness and quality while adapting scope

INTERVIEW ANSWER PATTERN
  Goal -> constraints -> uncertainty -> delivery options ->
  trade-off -> decision -> observed result

MENTAL MODEL
  Direction: are we doing the right work?
  Flow: does work actually get finished?
  Quality: is completed work usable and correct?
  Adaptation: can the team learn and change responsibly?

FINAL PRINCIPLE
  Engineering process exists to enable delivery,
  not to maximize ceremonies, tickets, or busyness.
```
