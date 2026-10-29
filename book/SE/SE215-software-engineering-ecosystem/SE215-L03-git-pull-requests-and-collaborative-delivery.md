---
id: SE215-L03
course: SE215
title: "Git, Pull Requests, and Collaborative Delivery"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L02
next: SE215-L04
---

# SE215 — The Software Engineering Ecosystem

## Lecture 03: Git, Pull Requests, and Collaborative Delivery

*Five developers are working on the same application. Three features are unfinished, two branches have diverged, an urgent security fix must reach production, and the release manager has just discovered that the green CI checks were run against yesterday's code. Everybody knows Git. So why has delivering software become so complicated?*

# Part I — Intuition

## The picture to carry in your head

Imagine five engineers maintaining a hotel-booking platform.

Alice is developing a new checkout interface.

Bob is implementing discount codes.

Charlie is refactoring the reservation API.

Diana is upgrading the authentication system.

And Emma is fixing a security vulnerability that must reach production immediately.

Everybody works in Git.

Everybody knows how to create branches, commit changes, and open pull requests.

Yet the team has a problem.

Alice's feature branch is two weeks old. During those two weeks, Charlie changed the reservation API that Alice's frontend expects.

Bob's discount implementation also modifies the checkout logic, but neither developer knows what the other is doing.

Diana's authentication changes aren't ready, but someone accidentally merged part of the work into a release branch.

Meanwhile, Emma's urgent security fix is trapped behind a long queue of reviews and failing integration tests.

The problem isn't a lack of familiarity with Git commands.

It's that the team hasn't designed a reliable method of integrating changes.

**Version control preserves history. It doesn't automatically make collaborative development safe.**

Git can store competing versions of the codebase.

It can detect many textual conflicts.

It can reconstruct earlier commits.

But it cannot decide whether Alice's feature is compatible with Charlie's API, whether Bob's business rules are correct, or whether a deployment will work with the current database.

Those are engineering decisions.

## 1. A branch is a different view of the project's future

Imagine that everyone begins on the same working version of the application.

Alice creates a branch and modifies checkout.

Bob creates another branch and modifies pricing.

Their branches now represent two possible developments of the same system.

Neither has necessarily incorporated the other's work.

As time passes, the common starting point becomes older.

The longer the branches remain separate, the more opportunities arise for assumptions to diverge.

Alice may write code against an API that no longer exists on the main branch.

Bob may create a pricing abstraction that duplicates something another developer introduced.

Tests can pass on both branches independently while their combined result fails.

A branch isn't inherently dangerous.

The danger comes from allowing independent development to accumulate without integration.

## 2. A successful merge doesn't prove a successful system

Suppose Alice and Bob modify different files.

Git merges their changes without a conflict.

Excellent.

Does that mean the software works?

Not necessarily.

Alice's checkout component calls `calculateTotal()` expecting a price in euros.

Bob changed the pricing service so that it returns integer cents.

The changes occurred in different files.

Git can combine the text perfectly.

The resulting application may charge the customer one hundred times the intended amount.

This is a **semantic conflict**.

The code merges cleanly, but the assumptions don't.

Git detects overlapping changes to content.

It doesn't understand every behavioral contract connecting that content.

That's why integration tests, code review, and small increments matter.

## 3. Smaller changes are easier to understand

Imagine reviewing a pull request containing twelve thousand changed lines.

It includes a new payment feature, dependency upgrades, formatting changes, and a database migration.

The author has been working on it for three weeks.

The reviewer must understand all those changes simultaneously.

Now compare a pull request that introduces one compatible API field and its associated tests.

The second change is easier to reason about.

It has a smaller surface for unintended consequences.

And it can often be integrated earlier.

This suggests an important principle:

**The ideal unit of collaboration is usually a small, coherent change—not an entire feature hidden on a branch until everything is finished.**

A large feature can be developed through several safe increments.

Incomplete behavior can remain disabled until the product is ready to release it.

The source code can be integrated before the feature becomes visible.

That distinction will become important.

## 4. Integration and release are different decisions

Suppose we merge Alice's unfinished checkout implementation into the main branch.

Does that mean customers must immediately see it?

No.

The application can contain functionality that isn't yet enabled.

A feature flag, route restriction, or deliberate internal interface can prevent unfinished behavior from being available to users.

This separates two decisions.

**Integration:** Is the code compatible with the shared codebase?

**Release:** Should users be able to exercise the new behavior?

Separating these decisions enables shorter branches and more frequent integration.

But feature flags aren't free.

They introduce conditional paths, configuration, and cleanup obligations.

We should use them deliberately rather than hide permanently unfinished code behind dozens of forgotten switches.

## 5. Git history is evidence, not a museum exhibit

A good repository history helps engineers understand what changed and why.

It supports debugging, investigation, auditing, and recovery.

But that doesn't mean every temporary commit should be preserved forever.

A developer may create several commits while exploring a solution.

Those commits might be meaningful steps.

Or they might be temporary corrections such as "fix lint," "oops," and "actually fix test."

Different teams prefer different ways of incorporating this history into the shared branch.

Some preserve individual commits.

Some squash a pull request into one coherent change.

Some maintain a strictly linear history.

The correct choice depends on the team's workflow and recovery needs.

The aim isn't the prettiest Git graph.

It's a history that makes future engineering work easier.

## Three questions before the Deep Dive

1. Why can two branches merge without textual conflicts and still produce broken software?
2. Why might frequent integration be safer than waiting until a large feature is completely finished?
3. What's the difference between merging code and releasing behavior to users?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The release that combined five individually successful branches

It's Wednesday afternoon at Mercury, our hotel-booking company.

A release is scheduled for Thursday.

Five developers have been working on different changes.

Every developer reports that their implementation works.

The pull requests are ready.

But integration produces a surprising result.

The checkout interface expects a field that Charlie removed from the reservation API.

Bob's discount code uses the new pricing service, while Alice's checkout still uses the old representation.

Diana's authentication refactor introduces a middleware change that breaks an administrative route.

And the database migration assumes every application instance has already been updated, even though production uses rolling deployments.

None of these problems necessarily existed within the individual developer's branch.

They emerged when independently developed changes were combined.

This is the problem collaborative delivery is supposed to manage.

We need a process that discovers incompatibilities early, preserves useful history, and allows production fixes to move independently of unfinished product work.

## 2. Git's underlying model: snapshots and history

Before comparing workflows, let's establish the small amount of Git machinery that matters.

Git records commits representing snapshots of a project's tracked contents, together with metadata and parent relationships.

A commit identifies a particular point in the repository's history.

Commits form a directed acyclic graph.

In ordinary terms, that means each commit links to its parent or parents, allowing Git to reconstruct how different lines of development diverged and later came together.

### A branch is a movable reference

A branch is essentially a named reference to a commit.

When you create a new commit on that branch, the branch reference advances.

Two branches can point to different commits that share an earlier ancestor.

That's how independent work develops.

A tag, by contrast, commonly marks a particular commit or release rather than automatically advancing with new development.

This distinction matters for releases.

A branch represents a moving line of development.

A release tag normally identifies a specific version.

### Your working directory isn't the repository history

Your working tree contains the files you're currently editing.

The staging area identifies changes prepared for the next commit.

The commit records a snapshot into the repository's history.

These are distinct states.

A developer may modify a file without staging it.

They may stage only part of a file.

They may commit a change without pushing it.

Understanding these boundaries is useful when debugging a confusing Git state, but our main focus is what happens when several developers share the history.

## 3. Merge versus rebase: two ways to integrate work

Suppose Alice creates a feature branch from main.

While she's working, Bob merges another change into main.

Alice's branch and main now diverge.

She needs to incorporate the newer work.

Two common approaches are merge and rebase.

### Merge

Merging combines histories.

If the branches have diverged, Git may create a merge commit with two parents.

The history preserves the fact that the work developed separately and was later integrated.

This is useful when that branching structure matters.

It also avoids rewriting existing commits simply to incorporate another branch's history.

### Rebase

Rebasing takes the changes represented by commits on one branch and replays them onto a different base.

Conceptually, Alice takes her work and reapplies it as though she had started from the latest main branch.

The result can be a linear-looking history.

But the replayed commits generally receive new identities.

This is why rebasing is considered history rewriting.

### The collaboration hazard

Suppose Alice and Bob are both basing work on a shared branch.

Alice rebases that branch and force-pushes the rewritten history.

Bob's local history still references the original commits.

Now their histories disagree about the identity and ancestry of commits that were supposedly shared.

Git can help recover from this situation, but it introduces unnecessary coordination complexity.

A practical rule is:

**Rebasing your own local feature branch is usually fine. Rewriting shared published history requires deliberate coordination.**

Don't treat rebase as automatically superior to merge.

They create different historical structures and have different collaborative consequences.

## 4. Three ways to merge a pull request

On GitHub, teams commonly encounter three pull-request merge methods.

### Merge commit

A merge commit preserves the branch's individual commits and introduces the integration relationship.

This keeps more of the original development history.

It can be useful when individual commits are meaningful.

But frequent merge commits can produce a more complicated graph.

### Squash merge

A squash merge combines the pull request's changes into one commit on the target branch.

This is attractive when a pull request represents one coherent change but contains several temporary development commits.

The shared branch receives a concise history.

However, the original internal commit sequence isn't preserved there as separate commits.

That can matter if the individual steps were carefully designed and independently useful.

### Rebase merge

A rebase-style integration places the pull request's commits sequentially onto the target branch without a merge commit.

This creates a linear history while preserving individual changes as separate commits in the resulting history.

The exact implementation and resulting commit identities depend on the hosting platform's behavior.

### Which would I choose?

For a conventional product team using small pull requests, squash merging is a reasonable default.

Each pull request represents one coherent change.

Its final commit message explains what changed and why.

But a team maintaining carefully structured commits may prefer rebase merging.

A project that values explicit branch ancestry may prefer merge commits.

There isn't a universal best method.

The selection should serve review, traceability, debugging, and recovery.

## 5. Trunk-based development: integrate before divergence becomes expensive

Now let's examine branching strategy.

One traditional approach keeps feature branches alive for the entire feature-development period.

A substantial feature may take weeks.

During that time, developers continue changing their own copies of the system.

Eventually, the feature branch must be integrated.

This is where expensive conflicts and outdated assumptions accumulate.

### Short-lived branches

Trunk-based development emphasizes frequent integration into a shared mainline, often called the trunk.

Developers may commit directly under suitable controls or use short-lived branches that merge frequently.

The defining principle is not that branches are forbidden.

It's that development shouldn't remain separated from the mainline long enough for integration risk to accumulate.

Suppose Alice's checkout redesign will take three weeks.

Instead of one enormous branch, she can introduce several compatible changes.

First, add a new API adapter.

Then introduce the new checkout state model.

Then add the UI components behind a disabled feature flag.

Then migrate selected flows.

Finally, enable the new experience when it is ready.

Each increment can be reviewed and integrated independently.

This makes incompatibilities visible while the relevant changes are still small.

### Trunk-based development has a requirement

The shared branch must remain in a usable state.

Frequent integration isn't helpful if every merge breaks the build.

That means the team needs reliable tests, disciplined compatibility, and a sensible release process.

A feature hidden behind a flag must still behave safely when disabled.

Database changes must remain compatible with running application versions.

Developers need to consider integration as part of daily engineering work.

Trunk-based development trades large, infrequent integration events for smaller, continuous integration work.

## 6. Long-lived branches: why they become expensive

Long-lived branches aren't automatically wrong.

Some products have unusual release schedules, certification requirements, or maintenance obligations that justify separate lines of development.

But a long-lived feature branch creates several risks.

Its dependencies become stale.

Its tests may not reflect changes merged elsewhere.

Its assumptions about database schemas and API contracts may diverge.

The eventual review grows enormous.

And the integration cost is deferred rather than eliminated.

The problem is especially severe when developers treat their branch as a private world until the last day of development.

### A useful warning sign

Suppose a pull request contains forty commits and changes twelve thousand lines.

The author asks for review after three weeks.

That isn't necessarily proof of poor engineering.

But it should trigger questions.

Could the change have been split into smaller compatible increments?

Was the team integrating assumptions during development?

Does the pull request combine unrelated refactoring and behavior changes?

Will reviewers realistically understand the entire risk surface?

The more difficult a change is to review, the more likely important defects are to go unnoticed.

## 7. Pull requests: a design conversation, not a permission slip

A pull request is often described as a request to merge code.

That's technically accurate, but its larger value is facilitating collaboration.

A good pull request provides enough context for another engineer to understand the intention and evaluate its consequences.

It should explain:

What problem is being solved?

What behavior changes?

Which important implementation decisions were made?

How was the change tested?

Are there migration, compatibility, security, or rollout risks?

For a simple change, this explanation may be short.

For a database migration or payment-flow modification, more detail is appropriate.

### Review the behavior, not just the style

Imagine Bob's pull request introduces a new discount calculation.

A reviewer comments on variable naming and formatting.

But nobody asks whether discounts should apply before or after tax, whether refunds preserve the original discount, or whether currency rounding occurs at the correct stage.

The review has focused on superficial details while ignoring the business risk.

Formatting should generally be automated where practical.

Human review is most valuable when examining correctness, clarity, architecture, security, maintainability, and operational consequences.

### Code review isn't a substitute for testing

A reviewer can notice suspicious behavior.

But they cannot manually simulate every relevant input or concurrent execution by reading code.

Automated tests provide different evidence.

Static analysis provides different evidence.

Production monitoring provides different evidence.

A mature delivery process combines these mechanisms rather than expecting one reviewer to guarantee everything.

## 8. The hidden cost of review queues

Remember the previous SE215 lecture on work in progress.

Pull requests provide an excellent example.

Suppose five developers finish implementation work and open five pull requests.

Nobody reviews them promptly because everyone is busy writing their own code.

After several days, the original authors move to other tasks.

Review comments arrive.

Now the authors must reconstruct their earlier context, make changes, rerun tests, and perhaps resolve new conflicts with main.

The delay has increased the cost of finishing the work.

### Review latency is part of delivery latency

A code change isn't delivered when the developer finishes typing.

It still needs integration and whatever release steps the organization requires.

If code review regularly takes several days, review becomes a significant part of cycle time.

A team might improve this by limiting active work, prioritizing reviews, assigning ownership clearly, or reviewing smaller pull requests.

The goal isn't to review everything instantly.

It's to prevent unfinished work from accumulating unnecessarily.

**Helping another engineer finish a useful change can be more valuable than starting another change yourself.**

## 9. A green CI check can become stale

Now for one of the most important production gotchas.

Alice opens a pull request.

Her CI tests pass.

Bob opens another pull request.

His CI tests also pass.

Both checks are green.

Bob merges first.

Then Alice merges.

Is the shared branch guaranteed to pass?

No.

Alice's checks may have run against a different version of main from the one that includes Bob's changes.

Each feature was validated independently.

Their combined behavior may be broken.

This is an integration problem that branch protections and merge queues are intended to help manage.

### Required status checks

A protected branch may require successful automated checks before changes can be merged.

That can include builds, tests, type checking, security checks, or other validations.

Branch protection can also require reviews and restrict direct pushes.

These controls help establish a consistent process.

But the checks only verify what they actually test.

A passing type checker won't necessarily detect an incorrect payment workflow.

### Merge queues

For repositories with frequent concurrent pull requests, a merge queue can validate changes against a candidate integrated state that includes other queued changes.

This helps reduce situations where individually green pull requests produce a broken mainline.

It also reduces repeated manual updating of pull-request branches merely to keep them current.

A merge queue doesn't magically prove business correctness.

It improves confidence that the combined changes satisfy the configured automated checks.

That distinction matters.

## 10. A merge conflict isn't the most dangerous conflict

Let's return to Alice's checkout and Bob's pricing changes.

A textual conflict occurs when Git cannot automatically reconcile competing changes to overlapping content.

Git asks a developer to resolve it.

That's inconvenient, but at least the conflict is visible.

A semantic conflict is subtler.

Alice changes a frontend model to interpret `price` as euros.

Bob changes the backend contract to represent monetary amounts in minor currency units.

Their commits touch different files.

Git merges them cleanly.

The application now displays incorrect amounts.

No merge-conflict marker appears.

The problem may only surface during integration testing or production use.

### Why small integration increments help

When changes are integrated frequently, the distance between assumptions and reality is smaller.

API contract tests can catch incompatible representations.

Integration tests can verify frontend/backend collaboration.

Feature flags can prevent incomplete functionality from becoming visible.

And reviewers can assess the changes while their context is fresh.

This is the practical value of continuous integration.

Not merely running tests after every commit.

It's discovering disagreements among collaborating parts early.

## 11. The production hotfix: don't merge the whole unfinished world

Now Emma discovers a critical authorization vulnerability.

An API endpoint allows a customer to retrieve another customer's reservation by manipulating an identifier.

The fix is relatively small.

But several unrelated features are unfinished.

How should Emma deliver the correction?

The answer depends on how production releases are managed.

### Case A: main is always releasable

In a disciplined trunk-based workflow, main should contain compatible, tested code.

Unfinished features are safely disabled or isolated.

Emma can create a small fix branch from current main.

The team reviews and validates the change.

Then it merges and deploys the corrected version.

This is straightforward because the mainline is maintained as a releasable system.

### Case B: production runs an older supported release

Suppose production currently runs version 2.7 while main contains work intended for version 2.8.

Emma may need to apply the fix to the production release line.

One option is to create a hotfix branch from the relevant production commit or maintained release branch.

Then implement the correction, validate it, and deploy the patched release.

The same fix should also be incorporated into main if it isn't already there.

Otherwise, the next release may reintroduce the vulnerability.

### Cherry-pick

Git's `cherry-pick` operation can reapply the change introduced by a selected commit onto another branch.

This can be useful when a small fix needs to be applied to a maintained release line without merging unrelated development work.

But a cherry-pick isn't guaranteed to be conflict-free.

The selected change may depend on code absent from the older release.

It must be reviewed and tested in that context.

### The important principle

A hotfix should carry the necessary correction and its dependencies—not every unrelated feature that happens to share a development branch.

This is one reason release boundaries matter.

## 12. Revert, reset, and rollback are different operations

Imagine Emma's fix has been deployed, but the release introduces another problem.

Someone says:

"Just reset the branch."

That phrase hides several very different operations.

### Git revert

A revert creates a new commit that attempts to undo the changes introduced by an earlier commit.

This is often useful for undoing an already shared change while preserving a clear public history.

The revert itself is another change that can be reviewed and tested.

### Git reset

Reset moves a branch or current reference to another commit, with options that also affect the staging area and working tree.

It can be useful for local history management.

But using reset to rewrite shared published history can disrupt collaborators.

The distinction isn't that reset is bad.

It's that it changes references and possibly local state rather than recording a new inverse change in the same way as revert.

### Deployment rollback

A deployment rollback changes what software is running.

It may involve deploying an earlier build artifact or switching traffic to another version.

That's different from changing Git history.

And there's a further complication.

If the new release changed the database schema or transformed stored data, returning to older application code may not be safe.

The old code may be incompatible with the new database state.

**Git rollback, application rollback, and database recovery are three different problems.**

Our SE340 and CS330 courses examine deployment and schema compatibility in depth.

## 13. Feature flags: integrate safely, release deliberately

Suppose Alice's checkout redesign will require several weeks.

Rather than keep a huge feature branch open, the team merges small compatible pieces behind a disabled feature flag.

The new code exists in the shared repository.

But ordinary customers still use the previous checkout flow.

Once the new implementation is tested, the team enables it for internal users.

Then perhaps a small percentage of customers.

Finally, after observing satisfactory behavior, it enables the new flow more broadly.

This can separate deployment from product release.

### A flag is operational state

But flags have costs.

Now the system may have two implementations.

Both may need testing.

The flag configuration becomes part of runtime behavior.

A flag may be enabled in production but disabled in staging, making reproduction harder.

And an old flag left permanently in the code can accumulate complexity.

A good flag should have an owner, purpose, and intended cleanup plan.

Feature flags are useful when they reduce the risk of integration and rollout.

They aren't a substitute for compatible architecture or reliable testing.

## 14. Protecting the shared branch without creating bureaucracy

A sensible repository workflow balances two concerns.

We want changes integrated frequently.

We also want to prevent obvious defects and unauthorized changes from entering critical branches.

Depending on repository size and risk, controls may include required pull-request reviews, passing status checks, restricted pushes, CODEOWNERS rules, signed commits, and merge queues.

But controls can also introduce delay.

If every tiny change requires approval from three people who are rarely available, the workflow may become a bottleneck.

### Risk-based rigor

A documentation correction doesn't necessarily need the same review process as a payment authorization change.

A database migration deserves attention to compatibility, locking, and recovery.

A security-sensitive change may require specialist review.

A low-risk code cleanup can often receive a simpler review.

Some of this differentiation can be enforced through repository configuration and code ownership rules.

Other parts depend on engineering judgment.

The best process provides enough protection without making safe change unnecessarily difficult.

## 15. A practical workflow for Mercury

Let's design one coherent approach for our six-engineer team.

First, use a shared main branch as the central integration point.

Developers create small, short-lived branches for coherent changes.

They open pull requests early enough that reviewers can provide feedback before the work becomes enormous.

CI checks builds, tests, types, and other relevant requirements.

Branch protection prevents bypassing essential checks.

Main is kept in a deployable state.

Large unfinished features are introduced through compatible increments, with controlled flags when necessary.

Release artifacts are identifiable and traceable to source commits.

Production hotfixes follow the actual release strategy, and corrections are incorporated into all relevant supported lines.

Finally, the team monitors review time, failed integrations, and deployment problems as signals about the effectiveness of its workflow.

This doesn't require a complicated Git branching methodology with seven permanent branch types.

For many product teams, a relatively simple approach is more maintainable.

### When might we choose differently?

A mobile application with a long app-store release cycle might maintain additional release branches.

A library supporting several major versions may need multiple maintenance lines.

An enterprise with strict certification requirements may have additional approval steps.

An open-source project with many external contributors may place particular emphasis on pull-request review and contributor boundaries.

A small internal service with continuous deployment may be comfortable with a much simpler workflow.

The right Git strategy follows the product's release constraints and the organization's collaboration needs.

## 16. The senior engineer's contribution

An experienced engineer doesn't merely know more Git commands.

They recognize how source-control choices affect the entire delivery process.

They know when a pull request has become too large to review responsibly.

They know why a green CI result may no longer be relevant after another change merges.

They distinguish textual conflicts from behavioral incompatibilities.

They avoid casually rewriting shared history.

They understand why code integration and feature release should be separated when useful.

And they can explain how to fix production safely without dragging unfinished work into the release.

Most importantly, they help the team make changes **small enough to understand, early enough to integrate, and safe enough to release**.

That's the real purpose of collaborative delivery.

---

# The Oral Examination

Answer each question aloud before reading the solutions.

### Question 1 — The clean merge that broke production

Two pull requests pass their individual tests and merge without textual conflicts. The combined application fails. How is that possible?

### Question 2 — Merge versus rebase

What does rebasing change about commit history? Why can rebasing shared published branches create problems for collaborators?

### Question 3 — The enormous feature branch

A developer maintains a feature branch for four weeks. What risks accumulate, and how might you restructure the work?

### Question 4 — The green checks

Two pull requests have green CI checks, but each was tested against an earlier version of main. What mechanism can improve confidence in their combined integration?

### Question 5 — The hotfix

Production runs an older release. Main contains unfinished changes. How would you safely deliver a small security fix without deploying unrelated work?

### Question 6 — Undoing an incorrect release

Explain the difference between reverting a commit, resetting a branch, and rolling back a deployed application.

### Question 7 — The feature flag

Why might merging unfinished code into main be safer than keeping it on a branch for several weeks? What risks does the feature flag introduce?

### Question 8 — The review bottleneck

Developers finish implementation rapidly, but pull requests spend four days awaiting review. Is this a code-review problem, an engineering-process problem, or both?

---

# Solutions and Discussion

## Solution 1 — Integration is more than textual merging

Git can combine changes to separate files without understanding their semantic assumptions.

An API contract, database schema, or shared business rule may have changed.

Integration and contract tests, small changes, and appropriate review help detect these incompatibilities.

## Solution 2 — Rebase rewrites commit ancestry

Rebase replays changes onto another base, generally creating new commit identities.

If collaborators have already based work on the original published commits, replacing that history can create disagreement between local and remote histories.

Use care when rewriting shared branches.

## Solution 3 — Shorten integration distance

Long branches accumulate stale dependencies, divergent assumptions, large reviews, and difficult merges.

Split the feature into compatible increments, merge them regularly, and use a controlled flag when the new behavior should not yet be exposed.

## Solution 4 — Validate the integrated candidate

Required current-branch checks or a merge queue can help ensure that the candidate integrated state passes the relevant checks.

The checks still need to test meaningful behavior; no CI configuration guarantees complete correctness.

## Solution 5 — Patch the release line

Create the hotfix from the relevant production release or maintained branch.

Apply and test the correction in that context, perhaps by cherry-picking a focused commit.

Deploy the patched release, then ensure the fix is also present in main and other supported release lines.

## Solution 6 — Different layers of recovery

Revert creates a new commit undoing earlier changes.

Reset moves a reference and can affect the staging area and working tree.

Deployment rollback changes the running application version.

Database migrations and persisted state may make an application rollback unsafe even when an older artifact is available.

## Solution 7 — Continuous integration with operational obligations

Integrating small compatible pieces reveals conflicts earlier.

A flag can keep unfinished behavior unavailable to users.

But flags introduce alternate runtime paths, configuration differences, and cleanup obligations.

They must be governed and eventually removed when no longer needed.

## Solution 8 — Flow and review ownership

Review latency is part of delivery latency.

The team may need smaller pull requests, explicit review ownership, better WIP management, and prioritized assistance with completing already-started work.

The objective is improving completion flow without weakening important review quality.

---

# The Mental Model Worth Keeping

When evaluating a Git workflow, ask four questions.

**Integration:** How quickly do independent changes meet the shared codebase?

**Verification:** What evidence tells us the combined system still works?

**Release:** Can we deploy or enable one change without accidentally including unrelated unfinished work?

**Recovery:** Can we identify, undo, patch, and redeploy changes safely?

Git provides the history and tools.

Pull requests provide a collaboration boundary.

CI provides automated evidence.

Release processes control what users receive.

And engineering judgment connects them.

**The best workflow isn't the one with the most elaborate branching diagram. It's the one that lets a team make small, understandable, verifiable changes without making production a gamble.**

# Next Lecture — SE215-L04: Repositories, Monorepos, and Build Systems

We've learned how engineers collaborate on changes.

But consider another question.

Our hotel company operates a Vue frontend, a Node.js API, several Python workers, shared TypeScript schemas, infrastructure configuration, and deployment tooling.

Should all of these live in one repository?

Should they use separate repositories?

Who owns shared libraries?

How can the build system avoid rebuilding everything after every small change?

And why do technologies such as pnpm workspaces, Nx, and Turborepo exist?

In SE215-L04, we'll explore the relationship between repository structure, dependency management, builds, ownership, and deployment independence.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Repair a Git Delivery Workflow

## Experiment A — Merge and rebase in a disposable repository

Create a temporary Git repository with a main branch and a feature branch.

Make one commit on the feature branch.

Make a different commit on main.

Now inspect the divergent history.

Using a disposable branch copy, try integrating through a merge.

Then reset the experiment to the same starting point and integrate through a rebase.

Compare the resulting commit graph and identities.

Useful commands include:

```bash
git log --oneline --graph --decorate --all
git merge <branch-name>
git rebase main
```

The objective is to understand the history transformation, not memorize command sequences.

**Question:** Which approach records an explicit merge relationship, and which replays commits onto a new base?

## Experiment B — A semantic conflict

Create a small TypeScript service with two modules.

One module provides a price.

Another consumes it.

On one branch, change the producer to represent money in integer minor units.

On another branch, modify the consumer while retaining the assumption that values are major currency units.

Make the branches modify different files.

Merge them.

Observe that Git may report no textual conflict.

Then create an integration test checking the monetary interpretation.

**Question:** Why did source-control integration succeed while application correctness failed?

## Experiment C — A production hotfix

Simulate three branches:

- `main` — ongoing development.
- `release/2.7` — currently deployed version.
- `feature/new-checkout` — unfinished work.

Introduce a small security defect in the released code and implement a correction.

Practice applying the correction to the appropriate release line and incorporating it into main.

You may use `git cherry-pick` where appropriate.

Do not assume the same patch applies cleanly across divergent branches.

**Question:** What validation is required before declaring the hotfix ready?

## Experiment D — Revert versus reset

In a disposable repository, create several commits.

Introduce a defective change.

Use `git revert` to create an inverse commit.

Inspect the history.

Separately experiment with `git reset` to understand how moving a branch reference affects the repository and working tree.

**Safety rule:** Do not experiment with history-rewriting commands on important shared branches. Use a disposable repository and inspect the command effects first.

## Experiment E — Design a team workflow

Your team has six engineers and deploys its backend several times per week.

It uses GitHub Actions for testing.

You need a workflow that supports:

- Small feature development.
- Pull-request review.
- Protected production code.
- Frequent integration.
- Urgent hotfixes.
- Unfinished product features.
- Database migrations.
- Reproducible release artifacts.

Prepare a short proposal explaining:

1. Your primary branch strategy.
2. Expected branch lifetime.
3. Pull-request expectations.
4. Required CI checks.
5. Preferred merge method.
6. Feature-flag policy.
7. Release tagging or artifact identification.
8. Hotfix handling.
9. Rollback limitations.

The best answer is not necessarily the most complex.

Evaluate whether the workflow fits the team's scale and release requirements.

---

# Further Reading

Primary references:

- **Pro Git — Branching and Merging:** https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging
- **Pro Git — Rebasing:** https://git-scm.com/book/en/v2/Git-Branching-Rebasing
- **GitHub — About Protected Branches:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- **GitHub — Managing a Merge Queue:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- **Trunk-Based Development:** https://trunkbaseddevelopment.com/
- **DORA — Continuous Integration:** https://dora.dev/capabilities/continuous-integration/

Related programme chapters:

- SE215-L02 — How Engineering Work Gets Planned and Delivered
- SE215-L04 — Repositories, Monorepos, and Build Systems
- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE330-L03 — Maintaining and Evolving Real Software
- SE340-L04 — CI/CD and Infrastructure as Code

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for voice readers; use as a screen-based revision aid.*

```text
SE215-L03 — GIT, PULL REQUESTS, COLLABORATIVE DELIVERY

CORE PROBLEM
  Different developers evolve the same system independently.
  Git merges content; it doesn't prove behavioral compatibility.

GIT MODEL
  Commit = snapshot + metadata + parent links
  History = directed acyclic graph
  Branch = movable reference to a commit
  Tag = reference commonly used to identify releases
  Working tree != index/staging area != committed history

MERGE
  Combines histories; divergent histories may produce merge commit
  Preserves explicit branch ancestry

REBASE
  Replays changes onto a new base
  Generally creates new commit identities
  Makes linear-looking history
  Avoid casually rewriting shared published branches

PR MERGE METHODS
  Merge commit = preserve individual branch history and integration
  Squash = one coherent commit for the PR
  Rebase merge = linear individual commits
  Choose for team traceability/recovery requirements

TRUNK-BASED DEVELOPMENT
  Integrate frequently into shared mainline
  Short-lived branches allowed
  Keep trunk usable/releasable
  Large features through compatible increments
  Use controlled flags where appropriate

LONG-LIVED BRANCH RISKS
  Stale assumptions
  Outdated dependencies
  Large review surface
  Late integration failures
  Expensive conflict resolution
  Delayed feedback

PULL REQUESTS
  Explain intent, behavior, tests, risks, rollout
  Small coherent changes easier to review
  Review domain correctness, not just naming/style
  Automated checks complement human review

CI
  Green PR alone may be stale after another PR merges
  Required checks protect shared branches
  Merge queue can test candidate integrated state
  CI checks only the behavior they actually cover

CONFLICTS
  Textual conflict = Git detects competing changes
  Semantic conflict = code merges but assumptions disagree
  Contract/integration tests catch more than merge mechanics

HOTFIX
  Identify actual deployed release
  Patch relevant release line
  Test in that release context
  Cherry-pick focused changes when suitable
  Incorporate fix into main/other supported versions
  Avoid deploying unrelated unfinished work

RECOVERY
  git revert = new inverse commit
  git reset = move reference, optionally change local state
  Deployment rollback = change running artifact
  DB recovery/schema compatibility = separate concern

FEATURE FLAGS
  Separate code integration from user-visible release
  Enable phased rollout/internal testing
  Flags require ownership, testing, cleanup
  Disabled functionality must remain safe

BRANCH PROTECTION
  Reviews, required checks, restricted pushes, CODEOWNERS,
  merge queues where justified
  Protect critical code without creating review paralysis

SENIOR ENGINEER
  Reduce integration distance
  Keep changes coherent and reviewable
  Surface contract changes early
  Preserve safe production release paths
  Understand rollback and compatibility limits
  Optimize delivery flow, not Git-graph aesthetics

INTERVIEW FRAMEWORK
  Branch strategy -> integration frequency -> tests/reviews ->
  release controls -> hotfix plan -> rollback/recovery

MENTAL MODEL
  How quickly do changes integrate?
  How do we verify the combination?
  Can release be independent from integration?
  Can we recover from a bad change safely?
```
