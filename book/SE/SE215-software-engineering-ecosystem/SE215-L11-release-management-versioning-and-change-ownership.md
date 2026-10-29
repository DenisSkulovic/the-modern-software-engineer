---
id: SE215-L11
course: SE215
title: "Release Management, Versioning, and Change Ownership"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE215-L10
next: SE215-L12
---

# SE215 — The Software Engineering Ecosystem
## Lecture 11: Release Management, Versioning, and Change Ownership

*Five developers have finished their features. Every pull request is merged. CI is green. Marketing has announced Friday's launch. One backend change isn't compatible with the old frontend, the database migration cannot be safely reversed, and the person coordinating the release is suddenly on vacation. Who exactly is responsible for getting this software to customers?*

---

# Part I — Intuition

## 1. The Friday Release Nobody Owns

Imagine you're a full-stack developer at Mercury, a growing hotel-booking platform.

Your team has spent two weeks implementing several improvements.

Alice has redesigned part of the booking interface. Bob has fixed a payment reconciliation problem. Clara has added a backend field for reservation modifications. David has improved search performance.

Every developer has completed their assigned ticket.

The pull requests are merged.

Automated tests pass.

The product manager announces that the release is ready for Friday.

Then someone asks a deceptively simple question:

"Which version are we releasing?"

The room goes quiet.

Alice says her frontend code was merged yesterday.

Bob says his payment fix was merged this morning.

Clara explains that her backend change depends on a database migration.

David says his search optimization is ready, but the related index hasn't been created in production.

The product manager asks whether the new checkout can be enabled for all customers immediately.

Nobody knows who is responsible for coordinating the actual deployment.

Everyone finished their own work.

Nobody established that the pieces were ready to go live together.

This is the problem release management solves.

**Release management turns a collection of completed changes into a controlled, identifiable, and supportable product change.**

## 2. Writing Code, Merging Code, Deploying Code, and Releasing Features Are Different Events

Software developers often use the word *release* loosely.

Someone says they released a bug fix when they merged a pull request.

Another engineer says the release happened when the container image was built.

The platform engineer says deployment finished when Kubernetes reported a successful rollout.

The product manager says the feature wasn't released because the feature flag is still disabled.

All four people are describing different events.

Here's a useful sequence.

First, a developer writes a change.

Second, the change is reviewed and merged into a shared branch.

Third, an artifact is built and tested.

Fourth, the artifact is deployed into production.

Fifth, the feature becomes available to the intended users.

Sixth, the team verifies that the change works and doesn't damage important business outcomes.

These events can happen on different days.

### Visual anchor 1 — The journey to customers

```text
Code written
     |
     v
Code merged
     |
     v
Artifact built
     |
     v
Artifact deployed
     |
     v
Feature enabled
     |
     v
Customers use it
     |
     v
Outcome measured
```

Not every release needs a separate step for each event. But the distinctions help engineers coordinate work.

A feature can be merged without being deployed.

It can be deployed without being enabled.

It can be enabled without being available to every customer.

And it can be available without achieving the product outcome the team intended.

## 3. A Version Is a Name for Something Specific

Suppose Mercury's production application currently reports version `2.7.0`.

The team fixes a payment bug.

It decides to call the new release `2.7.1`.

That version number helps people discuss the release.

Support can say a problem was fixed in `2.7.1`.

An engineer can investigate which customers are still running or receiving an older version.

A release manager can coordinate which changes belong in the next release.

But a version number isn't the same thing as the source code.

Nor is it automatically proof of what is running.

The Git repository contains commits.

A Git tag may mark the commit associated with a release.

The build system produces an artifact.

The container registry stores that artifact.

Production executes a particular artifact.

The version number is the human-readable identity connecting these things.

The stronger technical identity is usually the exact commit and artifact digest.

### Visual anchor 2 — One release, several identities

```text
Human release version:
  2.7.1

Git release tag:
  v2.7.1

Source commit:
  83b2c4...

Container artifact:
  sha256:7ab3...

Production:
  running that artifact
```

You don't need to memorize the exact hashes.

You need to understand why an engineer might ask for them.

**Version numbers help people communicate. Immutable identifiers help computers establish exactly what was built and deployed.**

## 4. What Does a Release Manager Actually Do?

Imagine that Mercury employs a dedicated release manager.

Does that person write the application code?

Not necessarily.

Do they personally operate Kubernetes?

Not necessarily.

Do they decide which product features the company should build?

Usually not as their primary responsibility.

Their central job is coordinating the release so that the right changes reach the right environment at the right time, with known risks and clear ownership.

They may assemble the release scope, coordinate dependencies, ensure required testing is complete, schedule deployment windows, gather approvals, communicate with stakeholders, and oversee release verification.

They also help coordinate recovery if something goes wrong.

The release manager is not supposed to replace the engineers who understand the application.

The developer still owns technical correctness.

The QA specialists contribute testing and risk expertise.

Platform engineers own or support deployment infrastructure.

Product management determines intended customer outcomes and business priorities.

The release manager coordinates the movement of these responsibilities toward a safe release.

## 5. What If There Is No Release Manager?

In a small startup, there may be no dedicated release-management role.

One of the developers might take responsibility for the release.

Perhaps the tech lead acts as release captain for the week.

Maybe the company deploys automatically whenever code reaches the main branch.

That's also a form of release management.

The process can be lightweight.

But somebody still needs to understand what is being deployed, which dependencies matter, how production will be verified, and what happens if the deployment fails.

A five-person team doesn't need an elaborate bureaucracy.

It does need a coherent way to avoid deploying incompatible changes or accidentally releasing unfinished behavior.

As companies grow, the process often becomes more specialized.

The responsibility doesn't vanish.

It becomes distributed across clearly defined roles and tools.

## 6. The Release Calendar

Suppose Mercury releases a new application version every Thursday.

Developers know that changes ready by Wednesday afternoon can be considered for that release.

QA knows when to perform final verification.

Support knows when customer-facing changes may appear.

Marketing can coordinate an announcement.

This is a release cadence.

Some organizations call regularly scheduled releases a *release train*.

The train leaves according to an established schedule.

Features that aren't ready may wait for the next train.

This can improve predictability.

But it also introduces choices.

What happens when an urgent security bug appears on Friday?

Does the team wait until next Thursday?

Probably not.

It may use a hotfix process.

What happens when a feature misses the cutoff?

The team should evaluate whether delaying the whole release is justified or whether the incomplete feature should wait.

Release management is partly the discipline of making these decisions without allowing every deadline to turn into a crisis.

## 7. A Hotfix Is Not Just Another Feature

Now imagine that Mercury's payment service has a production bug.

Some customers are charged correctly, but their bookings aren't always marked confirmed.

The problem cannot safely wait until the next normal release.

The team needs a hotfix.

But main contains several unfinished features.

Should the developer simply deploy everything currently on main to deliver the payment fix?

That may be unnecessarily risky.

Depending on the team's branching and delivery strategy, the engineer might create a patch against the current production release, cherry-pick the fix, test it, and deploy only that correction.

The same fix must also be integrated into future development if it isn't there already.

Otherwise the next normal release could accidentally reintroduce the bug.

This is one reason release branches, version tags, and hotfix procedures exist.

Their purpose isn't to make Git complicated.

It's to give the team control over exactly which changes customers receive.

## 8. Release Success Is a Business Observation

Suppose Mercury deploys the new checkout successfully.

All Pods become ready.

The API is responding.

No exceptions appear in the logs.

But booking conversion falls substantially after the rollout.

Was the release successful?

Technically, the deployment may have succeeded.

The product outcome may not have.

Or perhaps payment failure rates increased, creating a serious regression despite healthy infrastructure metrics.

A complete release process monitors both technical health and relevant business outcomes.

For a payment change, the team might watch payment failures, confirmed bookings, refunds, and reconciliation discrepancies.

For a new checkout, it may watch conversion and customer-reported problems.

For a search optimization, it may watch latency, error rates, and database load.

The correct measurements depend on the change.

### A tiny comprehension check

A feature has been merged into main, deployed to production, but is disabled behind a feature flag.

Has the code been deployed?

Yes.

Has the feature been released to customers?

Not necessarily.

Now imagine version `2.7.1` was tagged and published, but production still runs `2.7.0`.

Does the existence of the tag prove that customers received the fix?

No.

Finally, if a company has no dedicated release manager, does release management cease to exist?

No. The responsibilities still need ownership, whether through developers, automation, or a rotating release captain.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Release Management Is a Coordination Discipline

We already covered Git and collaborative delivery in SE215-L03, and the technical mechanics of CI/CD in SE340 and SE360.

Here our concern is different.

We want to understand how an organization decides what to release, when to release it, who participates, and how to establish that it succeeded.

A release manager or release captain coordinates the entire change.

They don't necessarily perform every technical action.

This is important because successful release management requires specialist knowledge from several parts of the organization.

Developers understand the code and its dependencies.

QA understands testing risks and gaps.

Platform engineers understand deployment infrastructure.

Database engineers understand migration consequences.

Security specialists may need to review high-risk changes.

Support and product teams understand customer impact.

The coordination responsibility ensures that these perspectives lead to one executable plan.

### 9.1 Ownership versus execution

A release captain can be responsible for confirming that a database migration has been reviewed without personally designing that migration.

A developer can own deployment verification without personally maintaining the Kubernetes cluster.

An engineering manager can approve the business risk of delaying a release without becoming responsible for the deployment commands.

The point is clear accountability—not forcing one person to become an expert in every adjacent discipline.

## 10. Six Terms That Should Never Be Confused

Let's establish the vocabulary.

**Commit:** A particular snapshot in Git history, connected to its ancestry.

**Branch:** A movable reference used to organize work and development history.

**Tag:** A named reference typically used to mark an important commit, such as a release.

**Build:** The process of transforming source and dependencies into a runnable or distributable output.

**Deployment:** Installing or activating an application artifact in an environment.

**Feature release:** Making functionality available to its intended users.

Now add a seventh term.

**Release version:** The human-readable identifier assigned according to the product's versioning policy.

A release version may correspond to a Git tag and a particular artifact.

But these identities should not be assumed interchangeable without evidence.

### 10.1 Why the distinction matters

Imagine a team merges ten commits into main during one day.

The CI system produces ten application images.

Production deploys three of them.

The product enables only one feature flag.

How many releases happened?

That depends on what we're measuring.

There were ten source integrations.

Ten builds.

Three production deployments.

And one feature exposure event.

An organization may call the three deployments releases, or it may reserve a customer-facing release name for a coordinated product launch.

There's no universal vocabulary that eliminates the need to define the event being measured.

## 11. Git Tags and Release Records

A Git tag identifies a specific point in repository history.

An annotated tag contains additional metadata such as a tagger, message, and date.

It can also be signed.

For example, a team may create an annotated release tag for version `2.7.1`.

A tag is useful because it gives engineers a stable human-readable reference to the relevant source revision.

But ordinary Git references can technically be moved or deleted.

Teams often protect release tags through policies and permissions.

The intended convention is that published release identities should not be silently rewritten.

### 11.1 A GitHub Release is more than a Git tag

GitHub supports release records associated with tags.

These records can include release notes, downloadable assets, and other release information.

Creating a GitHub Release doesn't automatically mean a SaaS service has been deployed to production.

It's a publication mechanism.

A release record is particularly useful for libraries, command-line tools, downloadable applications, and other products where consumers install versions.

### 11.2 Internal SaaS releases look different

A SaaS company may deploy several times a day without publishing a public GitHub Release each time.

The release identity can instead be recorded through deployment metadata, internal release dashboards, changelogs, and artifact digests.

For an internal service, the critical operational questions are:

Which version is running?

Which changes does it contain?

When was it deployed?

What other services are compatible with it?

Where can the team find the relevant release evidence?

## 12. Semantic Versioning

Semantic Versioning, commonly abbreviated SemVer, provides a structured naming convention.

Its normal form is:

**MAJOR.MINOR.PATCH**

For example, `2.7.1`.

The meaning is based on compatibility with a declared public API.

A major version increase indicates a backward-incompatible API change.

A minor version increase indicates backward-compatible functionality.

A patch version increase indicates backward-compatible bug fixes.

### 12.1 Patch releases

Suppose Mercury publishes a library version `2.7.0`.

It fixes a bug without intentionally changing the existing public API contract.

Under SemVer, a patch release could be `2.7.1`.

This helps consumers understand that the change is intended to preserve compatibility.

But the number isn't proof.

The implementation still needs testing.

### 12.2 Minor releases

Suppose the library adds a new optional function without breaking existing consumers.

A minor release could be `2.8.0`.

The change is backward compatible under the declared public API.

Existing consumers should continue working according to that promise.

### 12.3 Major releases

Suppose a public API removes a previously supported operation or changes behavior in a backward-incompatible way.

A new major version may be appropriate.

For example, `3.0.0`.

This signals that consumers may need code changes.

### 12.4 Version zero

Under SemVer, versions beginning with `0.` represent initial development.

The public API should not be considered stable.

A project using `0.7.3` isn't necessarily making the same stability commitment as one using `2.7.3`.

### 12.5 Prerelease versions

A version such as `2.8.0-rc.1` indicates a release candidate.

It is intended to represent a prerelease version rather than the normal final release.

An organization may use release candidates to test a proposed release before approving the final version.

The suffix follows the project's convention.

### 12.6 Build metadata

SemVer supports build metadata such as `2.8.0+build.104`.

That metadata doesn't affect SemVer version precedence.

It can help identify a particular build, but an actual artifact digest remains important for exact artifact identity.

## 13. SemVer Is Not Universal

A crucial qualification: SemVer is a compatibility scheme for a declared public API.

Not every application is a public library.

A privately operated SaaS backend may use version numbers mainly for operational traceability.

A team might call each monthly release `2026.10`.

Another might assign monotonically increasing build numbers.

Another might use Git commit hashes and container digests without presenting a conventional product version to customers.

These are legitimate approaches when they fit the product.

### 13.1 Calendar Versioning

Calendar Versioning, or CalVer, uses date-based identifiers.

For example, a team might label a release `2026.10`.

The exact format is a convention.

This can be useful when release timing is more meaningful than API compatibility.

But a date doesn't tell consumers whether an interface changed incompatibly.

### 13.2 Internal services

A company operating dozens of internal services may deploy each independently.

Requiring every internal service to share one version number can create unnecessary coordination.

Instead, each service can have its own artifact identity and release history.

The system's overall compatibility depends on API and event contracts, not merely matching version numbers.

### 13.3 Public libraries

For a library consumed by many external applications, SemVer can be especially valuable.

Consumers need to understand compatibility expectations when updating dependencies.

An incompatible change may require a major version, migration instructions, and a period of deprecation.

### 13.4 Mobile and desktop applications

Distributed applications introduce another complication.

Users may remain on older versions for weeks or months.

The backend may need to support several client versions simultaneously.

Publishing a new version does not immediately replace every installed copy.

A release policy must account for backward compatibility and support windows.

## 14. Release Branches Versus Trunk-Based Delivery

SE215-L03 covered the Git mechanics.

Here the question is why an organization chooses a particular release process.

### 14.1 Trunk-based development

In trunk-based development, engineers integrate small changes frequently into a shared mainline.

The main branch should remain healthy and releasable.

Feature flags or compatible incremental changes can separate integration from customer exposure.

This approach can support frequent automated deployments.

It reduces the duration of code divergence.

But it requires disciplined testing, compatibility management, and recovery.

### 14.2 Release branches

Some organizations maintain a release branch corresponding to a supported version.

For example, `release/2.7`.

New development continues on main.

The release branch receives selected bug fixes and maintenance changes.

This can be useful when the organization supports a stable production release while preparing a future version.

But long-lived branches create merge and backport obligations.

### 14.3 The hotfix problem

Suppose production runs `2.7.0`.

Main contains development intended for `2.8.0`.

An urgent payment fix is required.

A team might apply the fix to the production release branch and publish `2.7.1`.

The fix should also be integrated into main.

Otherwise the next release could omit it.

### 14.4 Cherry-picking has limitations

Cherry-picking copies the change introduced by a commit onto another branch.

It doesn't automatically guarantee semantic compatibility.

The target branch may lack supporting code or have different assumptions.

The cherry-picked change must be built and tested against the actual release line.

## 15. Release Trains and Continuous Delivery

There are several common ways to schedule releases.

**Continuous deployment:** Qualified changes automatically reach production under the organization's deployment rules.

**Frequent controlled releases:** Deployments occur regularly, perhaps daily, but may require approval.

**Release trains:** Changes are grouped around planned release times.

**Event-driven or emergency releases:** Critical fixes may be released outside the normal schedule.

These are not mutually exclusive.

A company can have a weekly customer-facing release train while deploying infrastructure fixes or internal services more frequently.

### 15.1 Why release trains exist

A predictable cadence helps coordinate testing, documentation, customer communication, and operational staffing.

It can be useful when multiple teams must release compatible changes together.

But if every team must wait for one large monthly deployment, integration and recovery risks may accumulate.

### 15.2 Release trains need a cutoff policy

Suppose one feature misses the planned testing deadline.

Does the entire release wait?

The answer should depend on the feature's importance and coupling to other changes.

If it's independent, moving it to the next release may be sensible.

If the release contains a database migration required by several services, the coordination problem is more complicated.

The release scope should be intentionally controlled rather than determined by whoever finished last.

## 16. What Goes into a Release?

A release isn't necessarily every change merged since the previous release.

The organization needs to know which changes are included and which features will actually be exposed.

A practical release inventory might identify:

Application fixes.

New functionality.

Database migrations.

Configuration changes.

Infrastructure dependencies.

Feature flags.

External integrations.

Known limitations.

Support implications.

### 16.1 Dependency relationships

Suppose the frontend calls a new API field.

The backend must support it before the frontend begins relying on it.

Suppose a backend migration requires historical data to be populated.

The migration must complete or provide a compatible transitional behavior before the new read path is enabled.

Suppose a new feature flag controls a workflow.

Its configuration must be ready in the intended environment.

The release manager needs visibility into these dependencies.

The specialists responsible for them need to verify their technical correctness.

### 16.2 Release scope isn't a dumping ground

The product manager wants a checkout redesign.

A developer suggests including an unrelated authentication refactor because it's already merged.

The refactor may be valid.

But adding unrelated high-risk changes to a coordinated release increases uncertainty.

A release should have a deliberate scope and understandable risk profile.

For continuous deployment, the equivalent discipline is keeping changes small, compatible, and independently verifiable.

## 17. Go/No-Go Decisions

A release approaches its scheduled deployment window.

Some tests have passed.

One issue remains unresolved.

The team must decide whether to proceed.

This is a go/no-go decision.

A good decision isn't based solely on whether a checklist contains all green indicators.

It considers the significance of unresolved risks.

### 17.1 What deserves attention?

Are critical user journeys working?

Are database migrations compatible with running applications?

Are infrastructure dependencies ready?

Is the intended artifact built and verified?

Are known defects acceptable?

Can the team observe production behavior?

Is there a credible recovery plan?

Are relevant people available to respond if something fails?

### 17.2 Who makes the decision?

The answer depends on organizational structure.

A release captain may coordinate the decision.

A technical owner may accept or reject a specific engineering risk.

A product owner may decide whether a missing feature justifies postponement.

A security or compliance requirement may mandate particular approval.

The decision should have clear accountability.

### 17.3 Avoid fake certainty

A deployment with no identified risks is not necessarily risk-free.

A release checklist helps reveal known failure modes.

It does not guarantee that unknown problems cannot occur.

The objective is informed, proportionate risk management.

## 18. Release Windows, Change Freezes, and Operational Context

Why do some companies avoid deploying immediately before a holiday?

Because recovery requires people and operational capacity.

A release may be technically safe under ordinary conditions but unnecessarily risky when the relevant engineers are unavailable.

Some organizations establish release windows, maintenance periods, or change freezes.

### 18.1 Change freezes

A change freeze temporarily restricts some deployments, often during high-risk business periods.

For example, an e-commerce company may restrict nonessential changes during a major sales event.

The freeze can reduce change-related risk.

But freezes also delay fixes and encourage larger batches afterward.

They should be used deliberately rather than as a universal substitute for release safety.

### 18.2 High-risk versus low-risk changes

A documentation update isn't equivalent to a payment database migration.

A configuration change affecting one internal tenant isn't equivalent to replacing a production database.

Release rigor should reflect potential blast radius and reversibility.

An organization that treats every change as equally dangerous may create unnecessary delivery friction.

An organization that treats every change as harmless will eventually discover why that was unwise.

## 19. Release Notes, Changelogs, and Communication

A developer may think release notes are an administrative inconvenience.

In reality, they help other people understand what changed.

But different audiences need different information.

### 19.1 Customer-facing release notes

Customers care about new capabilities, improved workflows, fixed problems, and changes requiring action.

They usually don't need a list of internal commit hashes.

A useful release note explains what changed and why it matters.

For example:

"Reservations can now be modified online without contacting support, provided no additional payment is required."

That's more meaningful than:

"Implemented reservation modification endpoint."

### 19.2 Internal release notes

Engineers, support teams, and operators may need more detail.

An internal release record can identify:

The version and artifact.

Deployment time.

Included changes.

Database migrations.

New feature flags.

Known issues.

Monitoring requirements.

Rollback or recovery conditions.

### 19.3 Changelog versus release notes

A changelog maintains a history of changes between versions.

Release notes communicate a specific release to its intended audience.

The distinction can be subtle, and teams use the terminology differently.

The important requirement is providing useful change information.

### 19.4 Breaking changes require communication

If an API removes a field or changes request semantics, consumers may need to update.

A version number alone may not provide enough information.

The team should explain the migration path, deprecation period, compatibility window, and relevant deadlines.

## 20. Releasing Versus Exposing a Feature

Imagine Mercury deploys the new checkout behind a disabled feature flag.

The code is present in production.

Customers still use the old checkout.

The product team enables the new version for internal users.

Then five percent of eligible customers.

Then twenty-five percent.

Eventually, the feature is enabled for everyone.

These are exposure decisions.

They are related to deployment but separate from it.

### 20.1 Progressive rollout

A gradual rollout limits how many users initially experience a change.

It gives engineers an opportunity to observe behavior before expanding exposure.

For a risky checkout change, the team might monitor payment failures, booking completion, client errors, and support reports.

### 20.2 Rollout isn't automatically an experiment

An A/B test is designed to estimate the effect of a change using an appropriate assignment and analysis method.

A progressive rollout may simply aim to reduce operational risk.

The two can use similar feature-flag infrastructure, but they have different goals.

A rollout percentage isn't automatically evidence of experimental causality.

### 20.3 Kill switches

Some features can be disabled quickly through configuration.

This can be useful during an incident.

But a feature flag can't reverse every effect.

It may not undo database migrations, already sent notifications, completed payments, or previously written data.

A release rollback strategy must distinguish reversible exposure from persistent side effects.

## 21. Post-Release Verification

A successful deployment isn't the end of release management.

The team should verify that the intended change works in the actual environment.

### 21.1 Technical verification

Depending on the system, relevant checks may include:

Deployment health.

Application error rates.

Latency.

Database errors.

Queue backlogs.

Resource saturation.

Unexpected changes in logs.

### 21.2 Business verification

For Mercury's booking platform, the release may need checks for:

Successful booking creation.

Payment authorization and capture.

Reservation confirmation.

Cancellation and refund behavior.

Search results.

Conversion and customer impact.

The exact signals depend on what changed.

### 21.3 Define the observation window

A release may look healthy in the first thirty seconds but fail under peak traffic.

The team should consider how much observation is needed.

A background job change might need enough time for representative jobs to execute.

A scheduled billing change might need verification at the next billing cycle.

Not every release can be fully validated immediately.

The release plan should identify delayed verification obligations.

## 22. Rollback, Revert, Disable, and Roll Forward

These terms describe different interventions.

**Revert:** Create a new source-control change that undoes an earlier code change.

**Deployment rollback:** Restore an earlier deployed application artifact.

**Feature disablement:** Stop exposing a feature, often through configuration.

**Infrastructure rollback:** Restore or reconfigure infrastructure, subject to the actual resource semantics.

**Database reversal:** Attempt to undo a schema or data migration.

**Roll forward:** Deploy a corrective change compatible with the current state.

These actions aren't interchangeable.

### 22.1 The database compatibility trap

Suppose a release renames `guest_email` to `contact_email`.

The new application works.

A later defect causes the team to restore the old application image.

But the old application expects the removed field.

The image rollback succeeds.

The application fails.

The release manager must therefore ensure that recovery plans account for schema and data compatibility.

### 22.2 Choose recovery before the incident

For important changes, identify the likely recovery path before deployment.

A reversible configuration change may support a straightforward rollback.

A destructive migration may require forward recovery.

A partial data backfill may need resumable processing.

A payment workflow may require reconciliation rather than replaying operations blindly.

The plan should reflect the actual failure modes.

## 23. Hotfixes and Supported Release Lines

Let's return to the payment bug.

Production runs `2.7.0`.

Main contains work planned for `2.8.0`.

The company needs an urgent correction.

A patch release `2.7.1` can be created from the supported production release line.

The fix is reviewed and tested against that line.

A release tag identifies the source.

The corresponding artifact is built and deployed.

Then the same correction must be incorporated into main.

### 23.1 Why a separate patch may be necessary

The latest development branch might contain unfinished features, migrations, or incompatible changes.

Deploying all of it merely to fix one production defect can increase risk.

A supported release line provides a controlled alternative.

### 23.2 The backport obligation

If the hotfix exists only on the production branch, future development may not contain it.

The next release can accidentally reintroduce the bug.

The team needs an explicit backport or forward-merge policy.

### 23.3 The compatibility check

A cherry-picked commit might depend on code introduced after the production branch diverged.

The change may not apply cleanly or may compile but behave incorrectly.

The patched release needs its own verification.

Git operations are not substitutes for testing.

## 24. Version Management Across Multiple Services

Suppose Mercury has separate services for authentication, bookings, payments, and notifications.

Each can deploy independently.

Should every service share version `2.7.1`?

Not necessarily.

A single global version may be useful for a tightly coordinated product release.

But independent service versioning can improve clarity and reduce unnecessary coupling.

The important question is compatibility.

### 24.1 API contracts

A new booking service may introduce an optional response field.

Old clients can often continue working.

Removing a field or changing its meaning may break consumers.

The release plan needs to address contract evolution.

### 24.2 Events and messages

A notification worker may consume `BookingConfirmed` events.

If the producer changes the event schema, old consumers may fail.

The compatibility contract exists independently of the service version numbers.

### 24.3 Client support windows

A mobile application may remain installed for months.

The backend cannot assume every user upgrades immediately.

The team must decide which client versions are supported and for how long.

### 24.4 Database migrations

Several services may depend on the same database schema.

A migration affecting one service may also affect background workers or analytical consumers.

The release inventory must include these dependencies.

## 25. Release Management Across Company Sizes

In a five-person startup, one engineer might prepare the release, run the migration, deploy the application, verify the checkout, and notify the team.

This can be reasonable when the system is small and the engineer has sufficient knowledge.

In a growing SaaS company, the product team may own application changes while a platform team maintains deployment infrastructure.

A rotating release captain may coordinate verification and communication.

In a large enterprise, dedicated release managers or change-management specialists may coordinate releases involving many teams, compliance requirements, external customers, or strict maintenance windows.

### 25.1 More specialization creates more interfaces

A dedicated release manager can improve coordination.

But it can also create an additional handoff.

If every developer assumes the release manager owns all technical risks, important knowledge can be lost.

A good process preserves technical ownership while clarifying coordination responsibility.

### 25.2 Developers still matter

Even in a large organization, developers may need to explain:

Which code changes are included.

Which configurations are required.

Whether a migration is compatible.

What the release could break.

How to verify the new behavior.

Which failures require immediate recovery.

Release management isn't a reason for developers to stop understanding production.

## 26. Measuring Release Performance

How do we know whether a team's release process is healthy?

A team might count the number of deployments.

More deployments can indicate shorter feedback cycles.

But if every deployment causes an outage, that number is misleading.

DORA's current delivery-performance model includes five metrics.

**Deployment frequency:** How often application changes are deployed.

**Change lead time:** Time from code commit to successful production deployment.

**Failed deployment recovery time:** How long it takes to recover from a failed deployment.

**Change fail rate:** The proportion of deployments causing failures in production.

**Deployment rework rate:** The proportion of deployments involving unplanned work to repair defects.

These provide complementary perspectives.

### 26.1 Speed and stability belong together

A team shipping once a day with frequent severe incidents isn't necessarily performing better than a team shipping several times a week with high stability.

Likewise, a team avoiding all deployments for months may look stable while accumulating integration risk and delaying customer value.

The goal is a sustainable delivery system.

### 26.2 Metrics shouldn't become individual rankings

Deployment metrics describe system behavior.

They shouldn't be used as simplistic scores for comparing individual developers.

A security-sensitive service and a low-risk internal dashboard may have different appropriate release patterns.

Interpret metrics in context.

## 27. A Practical Release Playbook

Imagine Mercury is preparing version `2.8.0`.

A reasonable lightweight process might look like this.

### Before the release

Establish the exact scope.

Identify the approved source revision and artifact.

Confirm that required tests have passed.

Review migrations, dependencies, configuration, and feature flags.

Confirm that the deployment target is correct.

Identify the person coordinating the release and the people responsible for relevant systems.

Agree on rollback or forward-recovery conditions.

### During the release

Deploy the approved artifact.

Observe deployment progress.

Verify the intended version is running.

Run relevant smoke tests.

Enable features according to the planned exposure strategy.

Monitor errors and critical business metrics.

### After the release

Confirm the expected business behavior.

Record the release identity and time.

Publish appropriate notes.

Track delayed verification obligations.

Resolve or document known issues.

Clean up obsolete release flags and temporary workarounds when safe.

### 27.1 The process should be proportional

A low-risk internal service update may need a few automated checks.

A payment migration may need a more deliberate release plan, approval, and operational staffing.

A release playbook should make appropriate action easier, not turn every deployment into an administrative ceremony.

## 28. The Release Manager's Most Important Skill

Suppose the product manager says:

"We promised this feature for Friday. Everything needs to ship."

QA reports a serious unresolved payment failure.

The developer knows the release contains a database migration.

The platform engineer says the deployment pipeline is ready.

What should the release captain do?

Not simply announce that Friday is cancelled.

Not blindly approve deployment.

And not personally attempt to solve every technical problem.

They should establish the actual dependencies and options.

Can the safe parts ship independently?

Can the risky feature remain disabled?

Can the payment change be isolated?

Can the migration be postponed without breaking compatibility?

What is the customer impact of delay?

Which risks are unacceptable?

Then coordinate an explicit decision with the responsible people.

The purpose of release management isn't to protect a date on a calendar.

It is to make delivery predictable, controlled, and recoverable while preserving business value.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — What Was Released?

A feature is merged into main and deployed to production, but its feature flag remains disabled.

Has the code been integrated? Deployed? Released to customers?

Explain the distinctions.

## Question 2 — Tag Versus Artifact

A Git tag `v2.7.1` exists.

Production runs a container image built from another commit.

Which evidence establishes the actual running version?

Why isn't the tag sufficient?

## Question 3 — Semantic Versioning

A public library introduces a backward-compatible function.

Which SemVer component should change?

What happens if the library removes a supported public API operation?

## Question 4 — Internal SaaS Versioning

Does every independently deployed backend service need to share one global SemVer number?

What matters more than matching version numbers?

## Question 5 — The Hotfix

Production runs `2.7.0`.

Main contains unfinished work for `2.8.0`.

An urgent bug must be fixed.

Describe a safe release-line strategy.

What happens after publishing the hotfix?

## Question 6 — The Release Captain

What does a release manager coordinate?

Which technical responsibilities remain with developers and specialists?

## Question 7 — The Missed Deadline

One feature fails final testing before the weekly release.

Should the entire release necessarily be delayed?

What would influence the decision?

## Question 8 — A/B Testing Versus Rollout

A feature is enabled for ten percent of customers.

Does this automatically constitute a valid A/B experiment?

Why not?

## Question 9 — The Failed Rollback

The deployment system restores an old application image.

The database has undergone a forward-only migration.

What can go wrong?

## Question 10 — Release Notes

What information belongs in customer-facing release notes?

What additional information might an internal release record require?

## Question 11 — Metrics

A team doubles its deployment frequency, but production incidents also increase.

Has delivery performance necessarily improved?

Which additional metrics would you inspect?

## Question 12 — Professional Judgment

A product manager insists that a payment-related feature must ship Friday.

QA identifies a serious failure mode.

The release manager asks you, as the backend developer, for your recommendation.

What do you say?

---

# Solutions and Discussion

## Solution 1 — Integration, Deployment, Exposure

The code has been integrated and deployed.

The feature isn't necessarily available to customers because exposure remains disabled.

These are separate lifecycle events.

## Solution 2 — Exact Runtime Identity

Compare the intended source revision, build artifact, deployed image digest, and observed running artifact.

The Git tag identifies source history.

It doesn't prove which artifact production currently executes.

## Solution 3 — SemVer

A backward-compatible public API addition ordinarily increments the minor version.

A backward-incompatible public API removal requires a major version change under the stable SemVer contract.

Version-zero rules differ.

## Solution 4 — Independent Services

No.

Services can have independent release identities.

Their API, event, schema, and operational compatibility contracts matter more than matching human-readable version numbers.

## Solution 5 — Production Hotfix

Apply the fix to a supported production release line.

Test and publish an appropriate patch release.

Deploy the verified artifact.

Then ensure the correction is incorporated into future development, using cherry-pick, merge, or another appropriate strategy.

## Solution 6 — Release Manager

The release manager coordinates scope, dependencies, approvals, scheduling, communication, verification, and recovery readiness.

Developers and specialists retain responsibility for the technical correctness of the systems they understand.

## Solution 7 — Release Scope

The decision depends on feature coupling, risk, business impact, and whether other changes can ship independently.

An incomplete feature can sometimes wait for the next release or remain disabled.

A tightly coupled migration may require postponing the coordinated change.

## Solution 8 — Progressive Rollout

No.

A gradual rollout controls exposure.

A valid A/B experiment requires an appropriate hypothesis, assignment, measurement, and analysis design.

## Solution 9 — Database Compatibility

The old application may no longer understand the current schema or data.

An image rollback doesn't automatically reverse persistent state.

Recovery must restore a compatible application/database combination.

## Solution 10 — Release Communication

Customer-facing notes should explain meaningful new capabilities, fixes, and required actions.

Internal records may include artifact identity, deployment time, migrations, feature flags, monitoring, known risks, and recovery procedures.

## Solution 11 — Delivery Metrics

No.

Inspect change fail rate, failed deployment recovery time, change lead time, and deployment rework, alongside deployment frequency.

Consider the quality and risk of the changes.

## Solution 12 — Engineering Judgment

Explain the failure mechanism and its possible business impact.

Offer safe alternatives: isolate the feature, delay the risky portion, ship independent changes, or change the rollout plan.

Participate in the decision with product, QA, and release ownership.

Don't conceal technical risk merely to meet the date.

---

# The Mental Model Worth Keeping

Release management is the discipline of turning completed engineering work into a controlled change that customers can safely use.

Source integration is not deployment.

Deployment is not feature exposure.

Feature exposure is not product success.

Version numbers help people communicate.

Immutable artifact identities help establish exactly what was delivered.

Release managers coordinate the process.

Developers remain responsible for understanding the technical behavior and risks of their changes.

A reliable release answers:

**What is changing? Why is it ready? Which exact artifact will run? Who owns the dependencies? How will we know it worked? What happens if it doesn't?**

---

# Next Lecture — SE215-L12: From Vague Business Idea to Shipped Product

We've now surveyed the people, tools, processes, and adjacent disciplines involved in professional software engineering.

The final lecture will combine them into one realistic assignment.

A manager enters a meeting with an idea.

The explanation is vague.

The deadline is two weeks.

There's no complete design, no clear specification, no agreed analytics, and several dependencies nobody has investigated.

You're the developer expected to make it happen.

SE215-L12 will follow the work from initial discovery and scope negotiation through product design, implementation, testing, release planning, rollout, instrumentation, and post-release evaluation.

The objective isn't to become every specialist in the organization.

It's to develop the judgment needed to turn an uncertain business request into a responsible engineering outcome.

*The spoken lecture ends here. The following practical workshop should be attempted independently before reading the solutions.*

---

# Optional Practical Workshop — Own a Realistic Release

## Workshop Contract

This workshop assumes you've already studied the Git collaboration material in SE215-L03.

It focuses on release decisions rather than repeating basic Git instruction.

The exercises use a disposable local Git repository.

No GitHub connection or production infrastructure is required.

**Decide → Prepare → Verify → Release → Recover → Communicate.**

Don't read the answer key until after attempting the exercises.

## Lab A — Create a Local Release Line

Create a disposable directory.

```bash
mkdir se215-release-lab
cd se215-release-lab

git init -b main

git config user.name "Release Lab"
git config user.email "release-lab@example.test"
```

Create the initial application file.

```bash
printf 'Booking API version 2.7.0\n' > app.txt

git add app.txt
git commit -m "Establish booking API 2.7.0"
```

Create an annotated release tag.

```bash
git tag -a v2.7.0 -m "Booking API 2.7.0"
```

Create a maintained production release branch.

```bash
git branch release/2.7
```

### Investigation

What does the tag identify?

What does the release branch identify?

How are they different?

What happens to the tag when main advances?

What happens to the branch when new commits are added to it?

### Acceptance criteria

You understand the distinction between a fixed release point and an evolving maintained release line.

---

# Lab B — Develop the Next Version

On main, add a new feature.

```bash
printf 'Experimental booking-change feature\n' \
  >> app.txt

git add app.txt

git commit -m \
  "Add experimental booking-change feature"
```

Imagine that this change is intended for version `2.8.0`.

It isn't approved for production yet.

### Scenario

A critical payment timeout bug is discovered in production version `2.7.0`.

The bug must be fixed without deploying the experimental feature.

### Task

Explain why publishing the current main branch may be unnecessarily risky.

Determine which release line should receive the hotfix first.

---

# Lab C — Create a Production Hotfix

Switch to the maintained production release branch.

```bash
git switch release/2.7
```

Add the hotfix marker.

```bash
printf 'Payment timeout recovery fix\n' \
  >> app.txt

git add app.txt

git commit -m \
  "Fix payment timeout recovery"
```

Inspect the history.

```bash
git log --oneline --decorate --graph --all
```

### Task C1 — Version decision

What version would you assign this backward-compatible bug-fix release?

Explain why.

### Task C2 — Release tag

Create an annotated tag for the patch release.

Do this yourself before checking the solution.

### Task C3 — The missing fix

Switch back to main.

Inspect `app.txt`.

Does it contain the payment fix?

Why not?

### Task C4 — Preserve the correction

Bring the hotfix into main without losing the experimental feature.

Choose an appropriate Git operation and explain its implications.

### Acceptance criteria

The production release line contains the hotfix without the experimental feature.

Main contains both the experimental feature and the hotfix.

The patch release has a unique version tag.

---

# Lab D — Write Release Notes

Mercury's patch release includes:

- A fix for payment timeouts that occasionally leave bookings awaiting confirmation.
- Improved recovery when the payment provider responds slowly.
- No intended public API breaking changes.

### Task

Write two versions of release communication.

**Customer-facing note:** Two or three sentences explaining the meaningful change.

**Internal release record:** Include version, source commit, artifact identity placeholder, deployment target, affected services, verification checks, known risks, and recovery conditions.

Do not present the internal Git commit message as the entire customer-facing release note.

### Acceptance criteria

Both documents explain the change to their intended audiences.

The internal record includes enough information to support troubleshooting.

---

# Lab E — Release Scope and Go/No-Go

## Scenario

Mercury plans its Thursday release.

The proposed scope contains:

| Change | Status | Risk |
|---|---|---|
| Payment timeout fix | Tested | High business importance |
| Checkout redesign | Tested on desktop only | Mobile behavior unresolved |
| Search optimization | Tested | Requires production index |
| Minor copy improvements | Tested | Low |
| Contact-email migration | Implemented | Old worker compatibility unknown |

### Task

Decide which changes can be released.

Identify which need additional evidence or coordination.

Describe the dependencies.

Determine whether any change could be disabled independently.

Choose a release captain and identify which specialists need to be consulted.

### Interviewer challenge

"The release is already announced. Can't we just ship it and fix problems tomorrow?"

Respond with a practical assessment rather than a generic refusal.

---

# Lab F — Versioning Across Products

Classify each scenario.

### Scenario 1

A public library fixes a backward-compatible parsing bug.

### Scenario 2

The same library introduces a new optional public API method.

### Scenario 3

The library removes a previously supported public API method.

### Scenario 4

An internal SaaS backend deploys a performance fix, but its API contract doesn't change.

### Scenario 5

A mobile application adds a new feature, but the backend must continue supporting older installed clients.

### Task

For each scenario, recommend an appropriate versioning or compatibility policy.

Explain whether SemVer is useful and what additional release coordination is necessary.

---

# Lab G — Design a Progressive Rollout

Mercury wants to release a new checkout.

The feature has already been deployed behind a disabled flag.

The product team proposes enabling it for everyone immediately.

### Task

Create a rollout plan with:

- Internal verification.
- Limited initial exposure.
- Defined technical and business guardrails.
- Criteria for expanding exposure.
- Criteria for pausing or disabling the feature.
- Monitoring responsibilities.
- A rollback or forward-recovery path.
- Feature-flag cleanup after successful adoption.

### Important distinction

Explain whether your plan is an operational rollout or a scientifically designed A/B experiment.

If it is both, identify the additional experimental requirements.

---

# Lab H — The Release Manager for a Day

## Starting situation

You're the most experienced developer available.

The team has no dedicated release manager.

A product manager wants a feature released by Friday.

One database migration is unreviewed.

QA reports an unresolved mobile issue.

The platform team is available only until Thursday evening.

Marketing has already prepared an announcement.

### Your assignment

Prepare a release plan.

It must establish:

1. Exact release scope.
2. Responsible owners.
3. Dependencies and blockers.
4. Required verification.
5. Deployment window.
6. Feature exposure strategy.
7. Recovery options.
8. Stakeholder communication.
9. Post-release monitoring.
10. Criteria for calling the release successful.

Then decide whether you would ship the entire feature, ship a safe subset, or postpone.

Defend your decision using concrete risks and business consequences.

---

# STOP — Independent Workshop Ends Here

Do not read the solutions before attempting the exercises.

The purpose is to practice release ownership without receiving every operational decision in advance.

---

# Solutions and Discussion

## Lab A — Release Identity

The annotated Git tag marks a particular release point.

The branch can advance with subsequent commits.

The tag doesn't automatically follow main.

This allows the organization to preserve a known release point while continuing development and maintenance.

## Lab B — Isolation

Main contains unfinished functionality intended for a future release.

The maintained production release line provides a way to patch the current supported version without including unrelated work.

This is useful when the delivery strategy doesn't guarantee that main is immediately safe to deploy.

## Lab C — Patch Release

A suitable patch version is `2.7.1`.

The tag can be created using:

```bash
git tag -a v2.7.1 -m "Booking API 2.7.1"
```

The hotfix exists on `release/2.7`, not automatically on main.

A suitable approach is to cherry-pick the hotfix commit into main.

For example:

```bash
PATCH_COMMIT=$(git rev-parse release/2.7)

git switch main
git cherry-pick "$PATCH_COMMIT"
```

Inspect the history and contents afterward.

The actual project should run relevant tests on both release lines.

## Lab D — Release Notes

The customer-facing note should describe improved booking confirmation reliability.

The internal record should identify the release, dependencies, verification, and recovery information.

Neither should claim functionality or compatibility guarantees the team hasn't established.

## Lab E — Go/No-Go

The payment fix may justify an urgent controlled release.

The copy improvements are likely low risk.

The search optimization needs its infrastructure dependency.

The checkout redesign has unresolved mobile risk.

The migration requires worker compatibility verification.

A reasonable decision may release independent safe changes while postponing or disabling the uncertain work.

## Lab F — Versions

For a stable public SemVer library:

Backward-compatible fix: patch.

Backward-compatible addition: minor.

Breaking API removal: major.

Internal services may use a different versioning convention but still need exact artifact identity and compatibility checks.

Mobile products need explicit support for older clients.

## Lab G — Rollout

A strong plan deploys verified code, enables limited exposure, monitors defined guardrails, and expands only when evidence supports doing so.

A gradual rollout isn't automatically a valid randomized experiment.

An A/B test needs additional assignment, measurement, and analysis design.

## Lab H — Release Ownership

A strong release captain establishes scope, verifies dependencies, identifies unacceptable risks, and coordinates an explicit go/no-go decision.

They don't need to personally perform every specialist task.

They should prevent the release deadline from obscuring technical risks and should offer viable alternatives rather than merely saying no.

---

# Further Reading

Primary references:

- **Semantic Versioning 2.0.0:** https://semver.org/
- **Git — Tagging:** https://git-scm.com/book/en/v2/Git-Basics-Tagging
- **GitHub — Managing Releases:** https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
- **GitLab — Releases:** https://docs.gitlab.com/user/project/releases/
- **GitLab — Release Evidence:** https://docs.gitlab.com/user/project/releases/release_evidence/
- **Keep a Changelog:** https://keepachangelog.com/en/1.1.0/
- **Calendar Versioning:** https://calver.org/
- **Trunk-Based Development:** https://trunkbaseddevelopment.com/
- **DORA — History of Software Delivery Metrics:** https://dora.dev/insights/dora-metrics-history/
- **GitHub Actions — Deployments and Environments:** https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- **Kubernetes — Deployments:** https://kubernetes.io/docs/concepts/workloads/controllers/deployment/

Related programme chapters:

- SE215-L01 — The People and Teams Behind Software
- SE215-L02 — How Engineering Work Gets Planned and Delivered
- SE215-L03 — Git, Pull Requests, and Collaborative Delivery
- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE215-L10 — Working With Product, Design, and Analytics
- SE340-L04 — CI/CD and Infrastructure as Code
- SE360-L01 — CI/CD in the Real World
- SE360-L03 — The Broken Release Studio
- CS350-L04 — Online Migrations and the Database Incident Studio

---

# Dense Cheatsheet — Interview Glance Card

*The following reference is fenced so voice readers can skip it.*

```text
SE215-L11 — RELEASE MANAGEMENT AND VERSIONING
================================================

CORE DISTINCTIONS

Commit:
  Git history snapshot

Branch:
  Moving reference

Tag:
  Named release point

Build:
  Source transformed into artifact

Artifact:
  Produced executable/package/image

Deployment:
  Artifact installed or activated

Feature release:
  Functionality available to users

Product outcome:
  Intended business effect achieved

VERSION IDENTITIES

Human version:
  2.7.1

Git tag:
  v2.7.1

Commit SHA:
  Exact source revision

Artifact digest:
  Exact built content

Running version:
  Observed production artifact

Version label != proof of deployment.

SEMVER

MAJOR.MINOR.PATCH

Major:
  Backward-incompatible public API change

Minor:
  Backward-compatible functionality

Patch:
  Backward-compatible bug fix

Prerelease:
  2.8.0-rc.1

Build metadata:
  2.8.0+build.104

Version zero:
  Initial development; public API unstable

SemVer is a compatibility convention,
not a universal SaaS release requirement.

CALVER

Date-oriented version identifiers.

Useful when release chronology matters
more than encoded API compatibility.

RELEASE MANAGEMENT

Coordinate:
  Scope
  Dependencies
  Readiness
  Approvals
  Schedule
  Artifacts
  Environments
  Communication
  Verification
  Recovery

Release manager coordinates.
Developers retain technical ownership.

RELEASE CADENCE

Continuous deployment:
  Qualified changes deploy automatically

Controlled frequent delivery:
  Frequent deployment with gates

Release train:
  Scheduled coordinated releases

Hotfix:
  Urgent release outside ordinary schedule

BRANCHING

Trunk-based:
  Frequent small integrations

Release branch:
  Maintained supported version

Hotfix:
  Patch production release line
  Verify
  Tag
  Deploy
  Backport into future development

RELEASE NOTES

Customer:
  Meaningful capabilities and fixes

Internal:
  Artifact, migrations, flags,
  dependencies, known risks,
  deployment time, recovery

GO/NO-GO

Check:
  Business importance
  Critical tests
  Compatibility
  Database migrations
  Infrastructure dependencies
  Feature flags
  Monitoring
  Recovery readiness
  Responsible people

DEPLOYMENT VS EXPOSURE

Deployed code may remain disabled.

Gradual rollout controls exposure.
A/B experiment estimates causal effect.

A rollout isn't automatically
a valid randomized experiment.

RECOVERY

Git revert != deployment rollback

Feature disablement != data reversal

Image rollback != schema rollback

Forward fix may be safer after
irreversible data changes.

MULTI-SERVICE RELEASES

Independent service versions are fine.

Compatibility contracts matter:
  APIs
  Events
  Data schemas
  Client support windows

DORA METRICS

Deployment frequency
Change lead time
Failed deployment recovery time
Change fail rate
Deployment rework rate

Measure throughput and instability.

COMPANY SIZE

Small company:
  Developer may own entire release

Growing company:
  Shared ownership, rotating captain

Large organization:
  Dedicated release/change roles possible

Specialization does not remove
technical ownership from developers.

FINAL RELEASE QUESTIONS

What is included?
What version is it?
Which artifact was built?
Who approved it?
Where will it go?
Are dependencies compatible?
How will users receive it?
How do we verify it?
What happens if it fails?
Who coordinates recovery?

MENTAL MODEL

Completed code is not delivered value.

Release management turns
engineering changes into
controlled, supportable product changes.

NEXT

SE215-L12 —
From Vague Business Idea to Shipped Product
```
