---
id: SE360-L02
course: SE360
title: "Terraform and Reproducible Infrastructure"
type: elective
manuscript: manuscript
edition: "2.1.0"
legacy_ids: []
prev: SE360-L01
next: SE360-L03
---

# SE360 — Practical Terraform and Cloud Delivery
## Lecture 02: Terraform and Reproducible Infrastructure

*The Terraform configuration says production has three application instances. The state file says three. The cloud console shows two. Terraform proposes replacing the database. Someone suggests running `apply` to fix everything.*

Before we investigate that danger, we need a surface map of what Terraform actually is—especially if you've never used it. The rest of this lecture assumes only that map, not specialist fluency.

# Terraform From Absolute Zero

*A short orientation for a software developer who has never used Terraform.*

## Imagine building a house

Suppose you've developed a web application.

You've written the frontend, the backend, and the database queries.

Everything works on your laptop.

Now you want real customers to use it.

You need somewhere to run the application.

Maybe you need three cloud servers, a PostgreSQL database, a load balancer to distribute requests, and a network that allows the servers to communicate securely.

You could open the AWS website and create everything manually.

Click here to create a server. Click there to create a database. Configure the network. Set the permissions. Repeat for staging.

It works.

But imagine having to recreate the environment next month. Or create an identical one for another customer. Or figure out what another engineer changed six months ago.

That's the problem Terraform helps solve.

## 1. Terraform is a recipe for infrastructure

Instead of clicking around the AWS console, you write configuration files describing what infrastructure you want.

Something like: I want three servers, one PostgreSQL database, and one load balancer connecting them. These resources should exist in this region and use these settings.

Terraform reads your configuration and communicates with AWS through its APIs to create or modify those resources.

This is called **Infrastructure as Code**, or IaC.

Infrastructure is described in files that can be reviewed, version-controlled, and reused, much like ordinary source code.

## 2. What does Terraform code look like?

Here is an illustrative fragment declaring an AWS storage bucket. It is only a fragment, not a complete runnable project—real configuration also needs a provider setup and credentials.

```hcl id="tf36zero"
resource "aws_s3_bucket" "reports" {
  bucket = "example-company-reports-unique-name"
}
```

The first part says what kind of resource you want: an AWS S3 bucket.

The second part gives it a name within Terraform's configuration: `reports`.

The contents tell Terraform how the resource should be configured.

The important point is that the file describes a desired resource.

It isn't a Python script that manually clicks AWS buttons.

## 3. The three commands worth recognizing

`terraform init` prepares the project and downloads the required provider plugins.

`terraform plan` compares the requested infrastructure with what Terraform understands about the existing infrastructure, then shows the changes it proposes.

`terraform apply` carries out the approved changes.

Imagine changing the configuration from three servers to five.

Terraform may propose creating two additional servers rather than rebuilding everything.

But it can also propose replacing or deleting resources when a change requires it.

That's why engineers review the plan before applying it.

## 4. What is Terraform state?

Terraform needs to remember which real infrastructure resources belong to its configuration.

It records that relationship in something called **state**.

Imagine a shopping list where you wrote "one refrigerator." You then bought a specific refrigerator and recorded its serial number.

Terraform state is somewhat like that record.

It helps associate a declaration in your configuration with the actual cloud resource Terraform manages.

State is important operational data. Teams normally store shared production state in a controlled backend rather than passing local state files between developers.

## 5. How is Terraform different from Docker and Kubernetes?

These tools do different jobs.

**Docker** packages an application and its dependencies into a container image.

**Kubernetes** manages how containerized applications run: Pods, replicas, deployments, restarts, and services.

**Terraform** typically creates or manages infrastructure such as cloud networks, databases, Kubernetes clusters, permissions, and load balancers.

They can work together.

For example, Terraform creates an AWS Kubernetes cluster. A CI/CD pipeline builds a Docker image. Kubernetes deploys and runs that image.

Terraform can also manage certain Kubernetes resources, but that doesn't make it identical to Kubernetes.

## 6. Will you personally use Terraform?

Possibly. But you don't need to become a Terraform specialist to be a strong full-stack engineer.

In a small company, developers may maintain Terraform because there is no dedicated infrastructure team.

In a larger company, platform or infrastructure engineers may own most Terraform configurations.

As an application developer, you might simply need to recognize the files in a repository, understand what a proposed infrastructure change means, and collaborate with the people responsible for applying it.

At your level, the most useful starting knowledge is understanding what Terraform manages, what a plan means, why state matters, and why applying infrastructure changes deserves care.

You can learn the detailed syntax when you actually need it.

## The zero-intro mental model

**Terraform is a version-controlled blueprint for creating and maintaining infrastructure.**

Docker packages your application.

Kubernetes can run it.

Terraform helps establish the infrastructure it runs on.

Git tracks changes to the blueprint.

CI/CD can automate applying approved changes.

You don't need to know how to build the entire house. You should know what the blueprint is and why changing it can affect the building.

That surface familiarity is enough before the rest of this lecture. For Hashicorp's own short reference, see [What is Terraform?](https://developer.hashicorp.com/terraform/intro).

*The absolute-zero orientation ends here. Part I begins the diagnostic mental model.*

---

# Part I — Intuition

## 1. The Infrastructure That Disagreed With Its Own Code

Imagine you're working on a SaaS platform deployed to AWS.

The company uses Terraform to manage cloud infrastructure: networks, security groups, databases, application services, and supporting resources.

Every infrastructure change goes through version control.

Developers submit pull requests. Terraform generates plans. Engineers review them, and an approved pipeline applies the changes.

The arrangement appears orderly.

One morning, the production application becomes unavailable.

An engineer opens the AWS console and discovers that one of the application's supporting resources differs from what the Terraform configuration declares.

The configuration says the resource should exist in one form.

The cloud provider reports something else.

The engineer runs `terraform plan`.

The output proposes several changes, including replacement of a resource that the application currently depends on.

The engineer thinks:

"Terraform knows what production should look like. Why not run `apply` and let it fix everything?"

That instinct is understandable.

It is also dangerous.

The configuration describes the infrastructure we want.

Terraform's state records what Terraform believes it manages.

The provider APIs reveal what currently exists.

And the application depends on what is actually available.

These are related perspectives, but they are not automatically identical.

A correct infrastructure investigation begins by distinguishing them.

## 2. Terraform Has Three Versions of Reality

Think about a company maintaining a fleet of delivery vehicles.

The company has a planning document describing which vehicles it should own.

It has an inventory database describing the vehicles assigned to the company.

And outside, in the parking lot, there are actual vehicles.

The planning document corresponds to Terraform configuration.

The inventory database corresponds to Terraform state.

The vehicles correspond to real infrastructure.

Suppose the planning document and inventory database both list ten vehicles, but somebody has removed one vehicle without updating either document.

The configuration is unchanged.

The state hasn't yet been reconciled.

Reality has changed.

This is infrastructure drift.

### Visual anchor 1 — The three perspectives

```text id="tf36a1"
        CONFIGURATION
       Desired resources
               |
               v
         TERRAFORM STATE
      Recorded relationships
               |
               v
       REAL INFRASTRUCTURE
       Provider-managed objects
```

The arrows are conceptual rather than a claim that Terraform only compares adjacent layers.

During normal planning, Terraform uses provider operations to refresh its understanding of real objects, then compares that refreshed information with the configuration.

The important distinction is that **configuration, state, and reality are different things**.

You cannot safely treat any one of them as complete proof of the other two.

## 3. State Is More Than a List of Resources

Imagine the configuration contains a resource called `aws_db_instance.primary`.

That is a Terraform address.

It identifies a resource instance within the configuration's logical structure.

The actual database exists under an identifier maintained by AWS.

Terraform state associates the logical address with the provider-managed object and its recorded attributes.

Without that association, Terraform may not recognize that an existing object corresponds to a resource declaration.

It could propose creating another object.

Or, if a previously managed resource disappears from configuration, it may propose destroying the real object that the old address still represents.

This is why state deserves operational protection.

It is not merely a cache of API responses.

It is part of Terraform's management contract with the infrastructure.

### Visual anchor 2 — Address versus physical identity

```text id="tf78bo"
Terraform address:
aws_db_instance.primary
          |
          | state association
          v
Provider resource ID:
my-production-database
          |
          v
Actual database instance
```

The specific provider resource ID depends on the resource type.

The essential idea is the association between the address Terraform manages and the real infrastructure object.

## 4. The Dangerous Rename

Suppose your Terraform configuration contains a production database resource named `primary`.

The team decides to rename its Terraform label to `database`.

A developer changes the configuration from `aws_db_instance.primary` to `aws_db_instance.database`.

To a human reader, this looks like a harmless naming improvement.

But Terraform resource addresses are significant.

If the configuration simply removes one address and introduces another, Terraform may interpret the change as removing one managed object and creating another.

The plan could contain a database destruction and creation, even though nobody intended to replace the database.

Terraform supports `moved` blocks to express this sort of refactoring.

A moved block tells Terraform that the existing state association should move from one resource address to another.

The physical resource can remain the same.

The configuration change now carries the migration of identity explicitly.

That's a surprisingly important lesson:

**Renaming a Terraform resource is not necessarily equivalent to renaming a variable in application code.**

## 5. A Plan Is a Proposed Operation, Not a Safety Certificate

Terraform's plan output may report that three resources will be added, one changed, and one destroyed.

Those numbers are helpful.

But they don't describe business impact.

One destroyed resource might be a disposable test file.

Another might be a production database containing years of customer data.

The plan's significance depends on the resources involved and the consequences of their changes.

The symbols also matter.

An update in place is different from a replacement.

Replacement may involve destroying an existing object and creating a new one, or creating the replacement first when the resource and lifecycle configuration permit it.

Some provider attributes cannot be changed without replacement.

Changing one seemingly minor argument may therefore trigger a substantial infrastructure operation.

### Visual anchor 3 — Small configuration edit, large impact

```text id="tfn8kp"
Configuration change:
Modify one resource argument
             |
             v
Provider says:
Argument requires replacement
             |
             v
Terraform plan:
Destroy and create resource
             |
             v
Possible application downtime,
new endpoint, or data loss
```

The correct response is to inspect *why* replacement is proposed.

Don't judge a plan solely by the number of changed resources or lines of configuration.

## 6. State Locking Prevents Competing Writers

Now imagine two engineers working on production infrastructure.

Engineer A reviews a plan and begins applying it.

Engineer B independently begins another Terraform operation against the same state.

Without coordination, both operations could make decisions based on conflicting assumptions.

Each might modify the underlying infrastructure and attempt to update state.

The result could be inconsistent or corrupted management records.

Terraform backends that support state locking prevent competing operations from modifying the same state simultaneously.

A lock is a coordination mechanism.

It doesn't make the proposed infrastructure changes correct.

It helps ensure that concurrent Terraform operations don't race over the same state.

### The force-unlock trap

Sometimes a lock appears stuck.

An engineer proposes forcibly removing it.

But what if another operation is still legitimately running?

Removing its lock could allow two writers to modify the same state concurrently.

The appropriate response is to establish who owns the lock and whether that operation has actually ended.

Force-unlocking without that evidence can turn a temporary operational delay into a state-consistency incident.

## 7. Production and Staging Aren't Just Variable Values

Suppose one Terraform configuration can create both staging and production infrastructure.

It accepts an environment variable.

The developer supplies `environment=staging` for one run and `environment=production` for another.

Is that enough to separate the environments safely?

No.

The state backend matters.

The cloud account matters.

The provider credentials matter.

The selected workspace or state key matters.

If the application uses the production backend state while passing a variable named staging, Terraform can still operate on resources associated with production state.

A descriptive variable doesn't override the actual identities of the backend and provider.

For infrastructure operations, an environment is not merely a string.

It is a collection of resource, credential, and state boundaries.

## 8. The Four Questions Before Any Apply

When a Terraform plan surprises you, ask:

**What configuration am I applying?**

Which Git commit, root module, variables, and provider versions are in use?

**Which state am I operating on?**

Which backend, workspace, and state key identify the managed resources?

**Which actual environment will the provider modify?**

Which cloud account, region, subscription, or project do the credentials reach?

**What will the plan physically do?**

Which resources will be created, updated, replaced, destroyed, or merely refreshed?

### A tiny comprehension check

You rename a Terraform resource address, and the plan proposes destroying one resource and creating another.

Should you approve the plan because the configuration change was just a rename?

No. You should investigate the state association and consider an explicit resource move.

Now suppose a remote state lock blocks your apply.

Would `-lock=false` be a harmless shortcut?

No. It can allow unsafe concurrent state operations.

Terraform is powerful precisely because it can modify real infrastructure. That power makes state identity and plan review first-class engineering responsibilities.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Terraform Is a Reconciliation System

SE340-L04 introduced infrastructure as code and the basic Terraform workflow.

Here we focus on what happens when the workflow encounters real-world inconsistencies.

Terraform configuration expresses a desired infrastructure model.

Providers communicate with external systems.

State records managed resource associations and attributes.

The dependency graph determines how operations are related.

When Terraform plans, it evaluates the difference between the current managed objects and the configuration's desired result.

### 9.1 The normal lifecycle

A typical workflow involves:

`terraform init`

`terraform validate`

`terraform plan`

`terraform apply`

The initialization step prepares the working directory, initializes the backend, and installs required provider dependencies.

Validation checks configuration syntax and internal consistency.

Planning proposes changes.

Applying attempts to perform those changes.

The commands are familiar.

The operational sophistication comes from understanding what each command establishes—and what it doesn't.

### 9.2 `validate` does not prove infrastructure safety

A valid Terraform configuration can still delete a database.

It can target the wrong cloud account.

It can apply unsafe firewall rules.

It can create resources with excessive permissions.

Syntax validation is necessary, but it's not a substitute for plan review, policy checks, or environment verification.

### 9.3 Provider behavior matters

Terraform delegates real resource operations to providers.

The provider defines supported arguments, observed attributes, and which changes require replacement.

A cloud API may reject an operation or report intermediate state.

A provider may encounter eventual consistency or timeouts.

The proposed plan is therefore a model of expected operations, not a guarantee that every external step will succeed.

## 10. The Three Layers of Infrastructure Reality

Let's formalize the earlier intuition.

### 10.1 Configuration

Configuration is the declared desired state.

It includes resource blocks, modules, variables, data sources, outputs, and provider configuration.

It can be reviewed and version-controlled.

But configuration alone doesn't tell you which real resources Terraform currently manages.

### 10.2 State

State provides Terraform's recorded associations between resource addresses and provider-managed objects.

It also records relevant attributes, dependencies, and metadata required for future operations.

State has its own lifecycle.

It needs secure storage, appropriate access controls, and suitable coordination.

### 10.3 Real infrastructure

The cloud provider or external system has the actual resources.

Those resources can change independently of Terraform.

An operator may alter a security group through the console.

An autoscaling mechanism may adjust instance counts.

A resource may fail or be deleted.

Another automation system may change settings.

Terraform must account for these realities.

### 10.4 A crucial distinction: stale state versus drift

Drift generally means that the real resource differs from the declared or expected managed configuration.

The state may temporarily contain stale information about that resource.

During normal planning, Terraform refreshes managed objects and evaluates those differences.

A problem involving incorrect state associations is related but different.

For example, importing the wrong physical resource under a Terraform address is a management-identity problem.

It may not resemble an ordinary manually edited cloud attribute.

The corrective procedure depends on which relationship is wrong.

## 11. What `terraform plan` Actually Does

A normal Terraform plan uses configuration, state, and provider observations to propose operations.

It ordinarily refreshes information about existing managed resources before comparing the result with desired configuration.

The plan can propose creation, update, replacement, or destruction.

### 11.1 The plan is evidence about intent and expected change

Suppose a resource's configured instance type changes.

Terraform may propose an update or replacement depending on the provider's rules.

That tells you what Terraform intends to do.

It doesn't establish that the application tolerates the change.

You still need to understand capacity, availability, endpoint behavior, and dependencies.

### 11.2 A speculative plan versus a saved plan

Running `terraform plan` without saving the plan produces a speculative proposal.

You can inspect it.

It doesn't commit Terraform to applying those exact changes later.

Running `terraform plan -out=tfplan` saves a particular execution plan.

Passing that file to `terraform apply` asks Terraform to execute the saved operations.

This is valuable in automation because the approval step can review a specific plan artifact.

However, the plan can become stale if state changes in the meantime.

A saved plan isn't an unlimited future authorization independent of changing infrastructure.

### 11.3 Saved plans contain sensitive information

A saved plan can contain the full configuration, input variables, and planned values.

Values marked sensitive may be hidden in terminal output while still being present in the saved plan file.

Backend configuration can also be captured.

Therefore, saved plan files deserve secure handling.

Do not upload them as publicly accessible CI artifacts merely because they are useful for review.

This is particularly important when a plan contains database credentials, tokens, or other privileged configuration.

## 12. Why a Small Plan Can Be Dangerous

Terraform displays a concise summary of resource changes.

But risk isn't proportional to the number of planned operations.

Replacing a disposable test instance is different from replacing a production database.

Deleting a security-group rule may isolate an application.

Changing a network route may affect multiple services.

Replacing a storage resource may threaten persistent data.

### 12.1 Replacement is the critical signal

A plan that includes replacement deserves special attention.

Terraform may replace a resource when an argument cannot be updated in place or when replacement is explicitly requested.

The replacement may affect resource identity, addresses, availability, or stored data.

The exact consequences depend on the provider and resource type.

### 12.2 `create_before_destroy`

Terraform supports a lifecycle setting that can request creation of the replacement before destruction of the original.

This may reduce downtime.

But it isn't universally possible.

Some resources require globally unique names.

Others cannot coexist with a replacement.

Dependencies may propagate create-before-destroy behavior.

A successful plan still requires real-world capacity and compatibility.

### 12.3 `prevent_destroy`

Terraform supports `prevent_destroy` to reject plans that would destroy certain managed resources while the lifecycle rule remains in their configuration.

This can help protect critical objects.

But it is not an absolute infrastructure safety boundary.

Removing the resource configuration removes the lifecycle protection from that configuration.

A resource can also be deleted outside Terraform.

Use it as one defense, not the entire protection strategy.

## 13. State Is Operational Data

Terraform state is often stored as JSON through a backend.

It includes resource identities and values needed to manage infrastructure.

State isn't simply an implementation detail that engineers can casually replace.

### 13.1 Why committing local state is dangerous

Local state can contain sensitive values.

It also changes as infrastructure is modified.

Committing state to source control creates access, versioning, and coordination problems.

Two engineers may each have a different state snapshot.

A Git merge is not an appropriate mechanism for reconciling concurrent infrastructure modifications.

For shared environments, use a suitable remote state backend with access controls and locking where supported.

### 13.2 State lineage and serial numbers

Terraform state includes metadata such as lineage and serial information.

These help protect against certain unsafe manual state operations.

For example, attempting to push state from an unrelated lineage or overwrite a newer state version can be rejected.

These checks are valuable.

But Terraform provides force options that can bypass protections.

Such operations should not be used casually.

### 13.3 `terraform state pull`

This command retrieves the current state snapshot from the configured backend.

It can be useful for diagnostic inspection or creating a controlled backup before a risky state operation.

But the output may contain sensitive infrastructure information.

Do not casually paste raw state into tickets, logs, or public channels.

### 13.4 `terraform state push`

Manually pushing state can overwrite the backend's current state.

This is a dangerous recovery operation.

It should be reserved for carefully controlled cases where ordinary configuration-driven mechanisms are insufficient.

Before any manual state repair, establish the exact backend and state identity, verify no competing writers exist, and preserve a recoverable backup.

## 14. Remote Backends and State Locking

A backend determines how Terraform stores state and, where supported, coordinates access.

A local backend stores state on the filesystem.

Remote backends store state in shared infrastructure or a managed service.

Different backends provide different capabilities.

### 14.1 Why teams use remote state

A shared environment requires one authoritative state location.

Engineers and CI systems need to refer to the same managed resources.

A remote backend can provide controlled access, durable storage, and locking.

Some backends also provide versioning and recovery facilities through their underlying storage systems.

### 14.2 State locking

If the backend supports locking, Terraform automatically attempts to lock state for operations that could write it.

This prevents competing writers from using the same state simultaneously.

A failed lock acquisition should normally stop the operation rather than proceed unsafely.

### 14.3 `-lock=false` is not a troubleshooting default

Disabling locking removes a critical coordination mechanism.

If another Terraform operation is active, both may manipulate infrastructure and state based on conflicting assumptions.

The fact that a pipeline is blocked doesn't establish that the lock is stale.

### 14.4 Force-unlocking

Terraform supports `force-unlock` for situations where automatic unlocking failed.

The command requires a lock identifier.

Before using it, establish that the owner is no longer performing the protected operation.

Never force-unlock an active legitimate operation simply because your own deployment is waiting.

## 15. The Saved-Plan and Backend Trap

An engineer generates a plan while targeting one backend.

Later, the environment changes.

Someone attempts to apply the saved plan.

A subtle detail matters: saved plan files contain backend configuration captured when the plan was created.

Terraform uses the backend configuration recorded in the saved plan during application.

That helps preserve the association between a plan and its intended state.

But it also means plan files can contain sensitive backend details, and temporary credentials captured through inappropriate configuration methods can create problems.

### 15.1 Backend credentials should not be casually embedded

Supplying secrets directly inside backend configuration can place them in local Terraform initialization metadata and saved plan files.

Use supported environment-based or other appropriate credential mechanisms rather than putting long-lived secrets into configuration files.

### 15.2 A plan belongs to a specific context

A meaningful infrastructure approval identifies the configuration revision, input variables, provider versions, backend/state identity, and target environment.

Approving an unlabeled plan file called `tfplan` without that context is weak release discipline.

### 15.3 Compare this with SE360-L01

In the previous lecture, we learned to trace the source commit and artifact digest.

Terraform adds another identity: the state and external environment against which the plan was produced.

An infrastructure plan is effectively an artifact tied to a particular configuration and observed state.

Treat it with corresponding care.

## 16. Drift: The Console Change That Came Back

Suppose Terraform configures an application service with three instances.

An operator responds to an incident by manually increasing it to five through the cloud console.

The immediate incident stabilizes.

The configuration still declares three.

The next normal Terraform plan refreshes the actual resource and identifies the difference.

Unless other configuration or lifecycle behavior changes the outcome, Terraform may propose restoring the configured value of three.

That could undo the emergency scaling intervention.

### 16.1 Terraform isn't confused

Terraform is reconciling the managed object toward the declared configuration.

The manual change created an inconsistency.

The operational problem is that the emergency intervention wasn't incorporated into the desired-state workflow.

### 16.2 Decide which reality should win

There are three broad choices.

Restore the infrastructure to the original configuration.

Update configuration to preserve the intentional external change.

Or establish a deliberate ownership boundary where another controller is allowed to manage that attribute.

The choice depends on the business intent.

### 16.3 `ignore_changes`

Terraform's `ignore_changes` lifecycle mechanism can tell Terraform not to reconcile specified attributes during updates.

This can be useful when another controller legitimately owns those attributes.

For example, an autoscaling controller may manage a desired replica count.

But ignoring changes can also conceal unwanted drift.

If an attribute is security-critical, silently ignoring external modifications may create serious risk.

The correct question is who is authorized to manage that field.

## 17. Refresh-Only Mode

Terraform provides refresh-only planning and application modes.

A refresh-only plan evaluates changes in real infrastructure and proposes updating Terraform's state and outputs to reflect them without modifying the managed infrastructure itself.

This is useful for investigating external changes.

### 17.1 Refresh-only is not reconciliation

If an operator changes a cloud setting manually, a refresh-only apply can update Terraform's recorded state to reflect the new external value.

It doesn't necessarily change the configuration.

A subsequent normal plan may still propose restoring the declared configuration.

This distinction matters.

### 17.2 Why automatic refresh isn't enough

A normal plan also refreshes state information by default.

But the normal plan then proposes configuration-driven infrastructure changes.

Refresh-only mode is useful when the immediate goal is explicitly to review and record observations about external changes rather than reconcile the real infrastructure toward configuration.

### 17.3 Avoid the deprecated `terraform refresh` shortcut

The older `terraform refresh` command effectively performs an automatically approved refresh-only state update.

HashiCorp recommends using refresh-only plan and apply workflows that allow review.

Updating state based on incorrect provider credentials or environment assumptions can cause significant damage to state records.

Always establish the target environment before accepting a refresh-only state modification.

## 18. Why `-refresh=false` Can Mislead You

Terraform normally refreshes managed resource information when planning.

The `-refresh=false` option disables that behavior.

This can reduce provider API calls.

But it can also make Terraform operate on outdated assumptions.

Suppose a resource was modified manually.

A plan without refresh may not notice.

The resulting proposal can be incomplete or misleading.

### 18.1 Faster isn't automatically safer

A plan that completes faster by omitting external-state observation may be useful in certain controlled workflows.

It should not be treated as authoritative evidence that production matches the configuration.

### 18.2 Incident investigations need current observations

If you suspect drift, deliberately disabling refresh works against the investigation.

Use current provider observations wherever possible.

## 19. Resource Addresses, Refactoring, and `moved` Blocks

Resource addresses are how Terraform identifies managed resource instances within configuration.

Renaming an address changes Terraform's logical model.

Without guidance, that may look like one resource disappearing and another appearing.

### 19.1 The wrong approach

A developer changes:

`aws_db_instance.primary`

to:

`aws_db_instance.database`

Terraform may propose removing the old resource and creating a new one.

The exact plan depends on state and configuration.

For a production database, the consequences could be severe.

### 19.2 The correct refactoring mechanism

A `moved` block declares that the old address corresponds to the new address.

Terraform updates the state association during the planned change.

The physical resource doesn't need to be recreated merely because its Terraform address changed.

### 19.3 Keep migration history when appropriate

For reusable modules, moved blocks also document how resource addresses evolved.

Removing historical moved blocks too early can break upgrade paths for consumers starting from older module versions.

This resembles database schema compatibility.

A source-code refactor may require explicit migration metadata to preserve existing infrastructure identity.

## 20. Importing Existing Infrastructure

Suppose an administrator manually created an AWS security group.

The team now wants Terraform to manage it.

Writing a resource block isn't enough to tell Terraform that the existing security group corresponds to the new declaration.

Terraform may plan to create another resource.

An import operation establishes the association between a Terraform resource address and an existing provider-managed object.

### 20.1 Declarative import blocks

Terraform supports `import` blocks in configuration.

An import block identifies the target resource address and the existing object to import.

The corresponding resource configuration should describe the intended managed settings.

Terraform can then plan the import and the subsequent configuration relationship.

### 20.2 Import doesn't prove configuration matches reality

After import, Terraform may propose additional changes because the declared arguments differ from the object's actual settings.

Review those changes carefully.

A successful import is not proof that the imported resource is safe to reconcile immediately.

### 20.3 Avoid double management

One physical resource should not casually be managed under multiple independent Terraform states or resource addresses.

Competing controllers can make conflicting changes.

Before importing, establish whether the object is already managed elsewhere.

The infrastructure ownership boundary matters as much as the syntax.

## 21. The Dependency Graph

Terraform builds a dependency graph to determine how operations relate.

Some dependencies are inferred through references.

For example, if an application resource references a database endpoint, Terraform can infer a relationship.

Other dependencies may need explicit declaration.

### 21.1 Dependency ordering

Terraform can create independent resources concurrently.

It orders dependent operations according to the graph.

The default parallelism setting affects how many graph operations may run concurrently.

But a dependency graph isn't merely an optimization.

It reflects relationships necessary for correct resource operations.

### 21.2 Explicit `depends_on`

Terraform provides `depends_on` for dependencies that cannot be inferred through ordinary references.

This can be necessary when one resource relies on another's operational side effects.

But adding broad explicit dependencies everywhere can make plans more conservative, reduce parallelism, and cause additional values to remain unknown until apply.

Use explicit dependencies where the relationship is real.

### 21.3 Infrastructure order is not application readiness

Suppose Terraform creates a database resource and then an application service referencing its endpoint.

Terraform may establish the resource dependency correctly.

That doesn't automatically mean the database is fully initialized, schema migrations have completed, or the application is ready to serve requests.

Infrastructure existence and application readiness are different contracts.

The delivery pipeline must verify the relevant runtime state.

## 22. Modules and Blast Radius

Terraform modules organize reusable infrastructure definitions.

A module may create several resources, such as a network, service, IAM role, and monitoring configuration.

This is useful for consistency.

But a small change to a shared module can affect many environments that use it.

### 22.1 Module versions matter

A team updates a shared module version.

The source code change appears small.

But the module may alter resource arguments that require replacement.

A production review must inspect the resulting plan, not simply the module diff.

### 22.2 Root modules define operational boundaries

A root module and its backend determine a set of managed resources.

Separate root configurations can help limit blast radius.

For example, networking infrastructure and application deployments may deserve different state boundaries.

That can reduce the scope of an individual apply.

But it introduces dependencies between states and additional coordination requirements.

### 22.3 Large state files aren't automatically wrong

A large Terraform state can make planning slower and changes harder to reason about.

But splitting state merely to reduce file size can create complex cross-state dependencies.

Choose boundaries based on ownership, lifecycle, security, and acceptable blast radius.

## 23. Terraform Workspaces and Environments

Terraform CLI workspaces allow multiple state instances to be associated with one working configuration under a suitable backend.

This can be convenient.

But a workspace name does not automatically create an isolated cloud account, separate credentials, or a complete security boundary.

### 23.1 The environment identity problem

Suppose the selected workspace is `staging`.

But the AWS credentials point to production.

The word staging doesn't prevent provider operations from reaching production.

Likewise, an environment variable named production doesn't prove that the selected backend state is production.

### 23.2 Prefer strong boundaries for critical environments

For important environments, teams often use clearly separated state backends or state keys, cloud accounts or projects, protected deployment controls, and scoped credentials.

The exact design depends on the organization.

The principle is that environment isolation must be enforced by actual identities and permissions, not merely naming conventions.

### 23.3 Inspect the full target tuple

Before applying, establish:

Configuration revision.

Root module.

Selected backend and state.

Workspace.

Provider account or project.

Region.

Environment-specific variables.

These together determine what the operation may affect.

## 24. Secrets and Terraform State

Terraform often manages resources requiring credentials or sensitive values.

A developer may mark a variable as `sensitive = true`.

Terraform then redacts the value in many ordinary CLI displays.

But sensitivity marking does not automatically prevent storage of that value in state or saved plans.

This distinction is critical.

### 24.1 Redaction isn't encryption

Hiding a secret from terminal output is useful.

It is not equivalent to ensuring the secret never enters a persistent artifact.

### 24.2 Ephemeral values and write-only arguments

Modern Terraform supports ephemeral values in appropriate contexts.

Ephemeral inputs can be omitted from state and plan files.

Some providers also support write-only resource arguments.

These features can reduce secret persistence.

However, they are subject to context restrictions and provider support.

They don't retroactively remove secrets already written into older state versions.

### 24.3 Protect state storage

A production state backend should have restricted access, encryption where appropriate, backup or versioning, and auditability.

Access to state can expose sensitive infrastructure information.

A user who cannot read application secrets directly may still gain access to them through poorly protected state.

Treat state access as a privileged capability.

## 25. Lifecycle Rules: Guardrails With Consequences

Terraform's lifecycle features can influence how resource changes are planned.

We've already discussed `create_before_destroy`, `prevent_destroy`, and `ignore_changes`.

They are useful, but each has limitations.

### 25.1 `create_before_destroy`

This can reduce downtime by creating a replacement before deleting the original.

But capacity, naming constraints, and dependencies may prevent safe coexistence.

### 25.2 `prevent_destroy`

This can reject accidental destruction while the configured rule applies.

It doesn't protect against out-of-band deletion or every possible state-management operation.

### 25.3 `ignore_changes`

This can support shared ownership of selected resource attributes.

But careless use can conceal configuration drift.

### 25.4 The real lesson

Lifecycle settings are not magic safety switches.

They encode assumptions about resource ownership, update behavior, and acceptable replacement.

Those assumptions must match the real infrastructure.

## 26. The Temptation of `-target`

Terraform supports targeted planning and application.

This focuses operations on selected resource addresses and their dependencies.

It can be useful during exceptional recovery situations.

But routine targeting can leave the wider configuration partially reconciled.

The resulting state may not reflect the full desired infrastructure relationship.

### 26.1 Why engineers reach for it

A full plan proposes many changes.

The engineer only wants to fix one resource.

Targeting appears to simplify the problem.

Sometimes it is appropriate.

But if the other proposed changes matter to the dependency graph or reflect drift, repeatedly ignoring them can create confusion.

### 26.2 Better long-term response

If engineers constantly need to target isolated portions of a huge configuration, consider whether the infrastructure should be divided into more appropriate operational boundaries.

Don't turn targeted applies into an undocumented substitute for architecture.

## 27. Failed Applies and Partial Reality

A Terraform apply isn't a universal transaction across all infrastructure providers and resources.

Suppose a plan contains five changes.

Terraform successfully creates three resources.

The fourth operation fails.

The fifth never runs.

The apply reports failure.

But some infrastructure changes have already happened.

### 27.1 Rollback isn't automatic

Terraform cannot generally reverse every successful cloud API operation as one atomic transaction.

A failed apply may leave partially changed infrastructure.

The state should record successfully completed operations as accurately as possible, but recovery may still require investigation.

### 27.2 The correct recovery pattern

First identify which operations succeeded.

Inspect the current state and real resources.

Determine whether the remaining desired changes are still safe.

Generate a new plan using the actual current configuration and state.

Do not blindly repeat a stale saved plan or manually edit state until you understand the failure.

### 27.3 External side effects complicate recovery

A resource creation may trigger external actions, billing, network changes, or application behavior.

Destroying the resource afterward doesn't necessarily undo those effects.

Infrastructure changes should be treated as operational procedures with partial-failure possibilities.

## 28. Drift Versus Intentional Operations

Not all drift is a mistake.

A cloud autoscaler may intentionally modify capacity.

An emergency operator may temporarily change a security rule.

A separate controller may manage a runtime field.

But those external changes need an ownership policy.

### 28.1 Single ownership where practical

If Terraform and another controller both attempt to manage the same attribute, they can repeatedly overwrite each other's changes.

For example, Terraform may declare a desired replica count while an autoscaler changes it according to demand.

Without a suitable ownership decision, the systems can fight.

### 28.2 Document exceptions

An emergency change should be recorded.

The team should decide whether to preserve it in configuration or restore the original desired state.

Leaving unexplained drift in production is a future incident waiting to happen.

### 28.3 Reconciliation should be intentional

Terraform is not a passive observer.

A normal apply can change real infrastructure.

Before running it after an incident, determine whether the configured desired state is still the correct desired state.

## 29. Terraform in a CI/CD Pipeline

Return to SE360-L01.

A software release has source identity, artifact identity, deployment target identity, and runtime identity.

An infrastructure release has analogous concerns.

Which Terraform configuration revision was approved?

Which provider and module versions were selected?

Which state and backend were used?

Which plan was reviewed?

Which account or project will be modified?

What did the apply actually change?

### 29.1 Review the specific plan

A production pipeline can generate a saved plan artifact.

An authorized reviewer examines it.

The apply stage executes that approved plan.

This is stronger than reviewing a speculative plan and later executing a completely new plan without checking whether its changes differ.

### 29.2 Secure the plan artifact

Because a saved plan may contain sensitive values and backend details, it should not be published through an unprotected artifact store.

The artifact needs appropriate access controls and retention.

### 29.3 Verify environment identity before planning

A plan targeting the wrong state or provider account is not made safe by approval.

The pipeline should check backend identity and authenticated provider context before performing changes.

### 29.4 Verify after apply

An apply success establishes that Terraform completed its planned operations according to the provider interactions.

It doesn't prove the application is healthy.

Infrastructure checks should be followed by appropriate runtime and service verification.

## 30. The Production Incident: A Plan That Would Undo Recovery

Let's reconstruct a complete incident.

A service experiences high latency.

An operator manually increases its capacity from three instances to five.

The service recovers.

The infrastructure configuration still declares three.

A scheduled Terraform pipeline runs.

Its normal plan discovers that actual capacity differs from configuration.

It proposes restoring three instances.

The plan is approved automatically because the change appears small.

The apply reduces capacity.

The original performance problem returns.

### 30.1 Terraform did what it was configured to do

The problem isn't that Terraform randomly modified infrastructure.

The system had competing sources of desired state.

The emergency operator intended five instances.

The configuration still intended three.

The deployment process treated the older configuration as authoritative.

### 30.2 The durable fix

Establish who owns the capacity setting.

If Terraform should manage it, update the configuration to reflect the intended value.

If another controller should manage it, define that ownership appropriately.

Require review of plans that reverse emergency changes.

Record incident-driven infrastructure adjustments and their intended lifetime.

### 30.3 The second failure

Now imagine the engineer notices the plan also proposes replacing a database due to a resource-address rename.

The engineer shouldn't approve the replacement because the change appears cosmetic.

They should use an appropriate moved block to preserve the association between the Terraform address and the existing database.

The plan should be reviewed again to confirm that no unintended physical replacement remains.

### 30.4 The third failure

A separate engineer tries applying while the production state is locked.

They consider disabling locking.

That would introduce an unnecessary concurrency risk.

The correct response is to identify the lock owner and wait or recover it safely.

These failures share one principle:

**Terraform operates on configuration and state relationships. Those relationships must be understood before using Terraform to modify production reality.**

## 31. The Senior Infrastructure Investigation

A credible investigation begins with evidence.

First, identify the intended infrastructure change.

Then establish configuration revision, root module, variables, provider versions, and module versions.

Confirm the backend, workspace, and provider account.

Inspect the normal plan and any drift observations.

Identify replacement and destruction operations.

Examine resource dependencies and lifecycle settings.

Determine whether the declared desired state is still appropriate.

Only then select a recovery path.

After applying, verify both infrastructure state and application behavior.

The engineer's task is not simply making Terraform report no changes.

It is ensuring that the intended infrastructure exists, remains safely managed, and supports the application's actual requirements.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — Three Realities

Explain the difference between Terraform configuration, Terraform state, and actual cloud infrastructure.

How can they disagree?

## Question 2 — The Dangerous Rename

A developer renames `aws_db_instance.primary` to `aws_db_instance.database`.

The plan proposes a replacement.

What should you investigate?

## Question 3 — The Lock

A production apply is blocked by a Terraform state lock.

Someone suggests `-lock=false`.

Why is that dangerous?

## Question 4 — Drift

An operator manually scales a service from three instances to five during an incident.

The Terraform configuration still declares three.

What might the next normal plan propose?

How should the team decide what to do?

## Question 5 — Refresh-Only

What does `terraform plan -refresh-only` help investigate?

How does it differ from a normal reconciliation plan?

## Question 6 — Saved Plans

Why is a saved Terraform plan useful in CI/CD?

Why should it be treated as a potentially sensitive artifact?

## Question 7 — Environment Identity

A job selects the Terraform workspace named `staging`, but AWS credentials point to production.

Does the workspace name protect production?

What should the pipeline verify?

## Question 8 — Partial Apply

Terraform successfully creates three resources, then fails while creating a fourth.

Has nothing changed because the apply failed?

What should the engineer do next?

## Question 9 — Lifecycle Rules

Explain the benefits and limitations of `prevent_destroy`, `create_before_destroy`, and `ignore_changes`.

## Question 10 — Import

An AWS security group already exists.

The team adds a corresponding Terraform resource block.

Does Terraform automatically know that the existing object belongs to the new address?

What mechanism establishes that association?

## Question 11 — Secrets

A variable is marked `sensitive = true`.

Does that guarantee the value cannot appear in state or saved plan files?

What additional mechanisms may be appropriate?

## Question 12 — Production Judgment

Terraform proposes replacing one production database and updating three small resources.

The total plan contains only four changes.

How would you evaluate the risk before approval?

---

# Solutions and Discussion

## Solution 1 — Three Realities

Configuration declares desired infrastructure.

State records managed resource associations and attributes.

Real infrastructure exists in external systems and may change independently.

Terraform normally refreshes managed objects when planning and compares observed reality with configuration.

## Solution 2 — The Rename

Inspect whether Terraform lost the association between the old and new resource addresses.

Use a suitable `moved` block for an intended refactor.

Verify the new plan doesn't physically replace the resource merely because its Terraform label changed.

## Solution 3 — The Lock

Disabling locking can allow concurrent operations against the same state.

This risks conflicting changes and state inconsistency.

Identify the lock owner and determine whether the protected operation is still active.

## Solution 4 — Drift

Terraform may propose restoring the configured capacity of three.

The team should determine whether five is now the intended desired state, whether the emergency change should be temporary, or whether another controller owns that attribute.

Update configuration or ownership policy accordingly.

## Solution 5 — Refresh-Only

Refresh-only mode evaluates external changes and proposes updating state and outputs without changing managed infrastructure.

A normal plan refreshes observations and then proposes configuration-driven infrastructure reconciliation.

## Solution 6 — Saved Plans

Saved plans let automation apply a specific reviewed proposal.

They may contain configuration, input variables, backend information, and sensitive values.

They require appropriate security controls.

## Solution 7 — Environment Identity

No.

Workspace names don't enforce cloud-account isolation.

Verify state backend, workspace, authenticated account or project, region, and target resources.

## Solution 8 — Partial Apply

Some resources may already have changed.

Inspect the actual infrastructure and current state.

Generate a fresh plan based on the post-failure situation.

Do not assume automatic rollback.

## Solution 9 — Lifecycle Rules

`prevent_destroy` can block planned destruction while the rule is present.

`create_before_destroy` can reduce downtime when replacement resources can coexist.

`ignore_changes` can support shared ownership but may conceal drift.

All require correct assumptions and do not guarantee safety by themselves.

## Solution 10 — Import

No.

An import establishes the association between an existing provider-managed object and a Terraform resource address.

The corresponding configuration must then be reviewed for unintended reconciliation changes.

## Solution 11 — Secrets

No.

Sensitive marking redacts display but does not inherently prevent persistence.

Appropriate remote state security, ephemeral values, write-only provider arguments, and external secret-management mechanisms may be necessary.

## Solution 12 — Production Judgment

Evaluate resource identity, replacement consequences, data persistence, downtime, dependencies, backup and recovery, target environment, and application impact.

Plan size is not a meaningful proxy for business risk.

---

# The Mental Model Worth Keeping

Terraform manages real infrastructure through declared configuration and recorded state.

Configuration describes what should exist.

State records what Terraform manages.

Providers reveal what actually exists.

A plan proposes how to reconcile those perspectives.

But Terraform cannot determine whether a configuration change is operationally desirable merely because the syntax is valid.

The engineer must establish:

**Which configuration? Which state? Which environment? Which physical operations? Which business consequences?**

Infrastructure reproducibility requires more than version-controlled code.

It requires reliable state identity, controlled change execution, explicit ownership, and verification of real-world results.

---

# Next Lecture — SE360-L03: The Broken Release Studio

We've now investigated application artifact provenance and Terraform state management.

The final lecture combines them.

A pipeline builds the correct application but deploys the wrong image.

A Terraform operation targets the wrong environment.

A database migration changes schema compatibility before the old application has disappeared.

The release pipeline reports success.

Production becomes unavailable.

And the first rollback attempt makes things worse.

In SE360-L03, you'll investigate these interacting release failures through an end-to-end incident studio.

The objective is to trace evidence from source revision to artifact, infrastructure state, deployment target, and application compatibility—then design a safe recovery.

*The spoken lecture ends here. The following exercises require a disposable local environment and are intended for independent investigation rather than continuous audio listening.*

---

# Optional Practical Lab — Terraform State, Drift, and Unsafe Plans

## Lab Contract

This workshop uses Terraform to manage files on your own computer through HashiCorp's Local provider.

It requires no AWS account, cloud credentials, or billable infrastructure.

The local files represent provider-managed resources.

The exercises reproduce:

- Configuration versus state.
- Out-of-band changes.
- Drift detection.
- Refresh-only behavior.
- Resource-address refactoring.
- Saved-plan handling.
- Environment separation.
- Plan review.
- Recovery after unintended changes.

The local-file provider deliberately models only a subset of real cloud behavior.

It doesn't reproduce AWS networking, database replacements, or distributed state locking.

Do not interpret it as a substitute for testing cloud-provider-specific operations.

The required method is:

**Predict → Plan → Inspect → Apply → Modify Reality → Diagnose → Repair → Verify.**

Only use the dedicated lab directory.

## Lab 1 — Install and Verify Terraform

Install Terraform CLI using HashiCorp's official instructions for your operating system.

Verify it is available:

```bash id="tfv001"
terraform version
```

This lab expects Terraform 1.5 or later.

The Local provider must be downloaded during initialization, so an internet connection is needed for the initial provider installation.

Create a dedicated directory:

```bash id="tfv002"
mkdir se360-terraform-lab
cd se360-terraform-lab
```

Create a `.gitignore` file:

```gitignore id="tfv003"
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
tfplan
crash.log
crash.*.log
runtime-manifest.json
```

State files and saved plans may contain sensitive information in real projects.

This lab uses only nonsensitive sample data, but the same handling discipline is appropriate.

## Lab 2 — Create Your First Managed Resource

Create `main.tf`.

The configuration manages one JSON file representing an application runtime manifest.

```hcl id="tfv004"
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition = contains(
      ["dev", "staging", "production"],
      var.environment
    )

    error_message = "Unsupported environment."
  }
}

variable "release_version" {
  type    = string
  default = "1.0.0"
}

resource "local_file" "manifest" {
  filename = "${path.module}/runtime-manifest.json"

  content = jsonencode({
    environment = var.environment
    release     = var.release_version
    replicas    = 3
  })

  file_permission = "0644"
}

output "manifest_path" {
  value = local_file.manifest.filename
}
```

### Predict

What resource address does Terraform manage?

What real object will it create?

Where will state be stored?

What does the desired configuration say about release version and replica count?

### Initialize

```bash id="tfv005"
terraform init
terraform validate
```

### Plan

```bash id="tfv006"
terraform plan
```

Inspect the proposed creation.

No file should be created merely by running a speculative plan.

### Save and apply a plan

```bash id="tfv007"
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan
```

Inspect `runtime-manifest.json`.

It should contain an object with environment `dev`, release `1.0.0`, and three replicas.

### Inspect state

```bash id="tfv008"
terraform state list
terraform state show local_file.manifest
```

The resource address should appear in state.

### Acceptance criteria

You can explain the relationship between the HCL resource block, the local state association, and the managed file.

---

# Lab 3 — Reproduce Infrastructure Drift

## Starting Symptom

An operator modifies the managed file outside Terraform.

The configuration remains unchanged.

The state initially reflects the last successful Terraform operation.

### Step 1 — Modify reality manually

Open `runtime-manifest.json` in a text editor.

Change the replica count from three to five.

Save the file.

Do not modify `main.tf`.

### Predict

What does the configuration declare?

What does the actual file contain?

What does Terraform's prior state record?

What should a normal plan detect?

### Step 2 — Run a normal plan

```bash id="tfv009"
terraform plan
```

The Local provider detects that the file content no longer matches the tracked resource content.

Depending on provider behavior, the plan may describe the file as changed or removed outside Terraform and propose recreating it.

Inspect the actual output rather than relying on one expected label.

### Step 3 — Compare with disabled refresh

Run:

```bash id="tfv010"
terraform plan -refresh=false
```

Compare the result with the normal plan.

### Required explanation

Why can disabling refresh hide an external modification?

Why would such a plan be unsuitable as authoritative drift evidence?

### Step 4 — Do not apply yet

The manual modification might represent an emergency capacity change.

Before letting Terraform restore the file, decide whether the desired replica count should remain three or become five.

This is the critical decision.

The tool can reconcile the configuration.

It cannot decide the business intent.

---

# Lab 4 — Refresh-Only Versus Normal Reconciliation

Run a refresh-only plan:

```bash id="tfv011"
terraform plan -refresh-only
```

### Tasks

Describe what the command proposes.

Does it intend to restore the original managed file?

Or does it focus on updating Terraform's recorded state and outputs to reflect observations?

### Important distinction

For the Local provider, changing file content may cause the provider to consider the tracked resource no longer valid.

The exact refresh-only plan may therefore show a state-record change rather than a simple attribute update.

That is provider-specific behavior.

The general lesson remains:

**Refresh-only changes Terraform's recorded understanding, not the external resource itself.**

Do not apply a refresh-only plan merely to make drift warnings disappear.

### Repair intentionally

For this lab, choose to restore the desired configuration of three replicas.

Run:

```bash id="tfv012"
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan
```

Inspect the file again.

The normal reconciliation should restore the declared content.

### Acceptance criteria

You distinguish an observation-only state update from configuration-driven resource reconciliation.

You can explain why the engineer must decide which desired state is appropriate.

---

# Lab 5 — The Dangerous Resource Rename

## Starting Symptom

A developer renames a Terraform resource label.

The underlying managed file should remain the same.

### Step 1 — Make the naive rename

Edit `main.tf`.

Change:

```hcl id="tfv013"
resource "local_file" "manifest" {
```

to:

```hcl id="tfv014"
resource "local_file" "release_manifest" {
```

Also update the output reference:

```hcl id="tfv015"
output "manifest_path" {
  value = local_file.release_manifest.filename
}
```

Do not change the filename or content.

### Step 2 — Inspect the plan

```bash id="tfv016"
terraform plan
```

### Prediction

Does Terraform recognize this as a harmless variable rename?

Or does it see the old managed address disappearing and a new address appearing?

What would this mean if the resource represented a production database rather than a local file?

### Step 3 — Do not apply the naive plan

Instead, add this block to the configuration:

```hcl id="tfv017"
moved {
  from = local_file.manifest
  to   = local_file.release_manifest
}
```

### Step 4 — Re-plan

```bash id="tfv018"
terraform plan
```

Inspect how the plan changes.

Terraform should recognize the intended state-address move without requiring physical replacement merely because the Terraform label changed.

### Step 5 — Apply the reviewed change

```bash id="tfv019"
terraform apply
```

Confirm that the resource now appears under the new state address:

```bash id="tfv020"
terraform state list
```

### Acceptance criteria

You understand why Terraform resource labels participate in managed resource identity.

You can use a moved block to express an intended refactor.

You recognize the potentially severe consequences of failing to preserve resource identity for stateful cloud objects.

---

# Lab 6 — A Configuration Change That Requires Review

## Starting Symptom

A developer modifies one variable.

The resulting plan may change the managed resource.

Change the release version in `main.tf` from `1.0.0` to `2.0.0`.

### Step 1 — Plan

```bash id="tfv021"
terraform plan
```

Inspect the action Terraform proposes.

For `local_file`, changing content can require replacing the file resource.

### Step 2 — Explain the operation

Does the plan represent an in-place update or replacement?

What does the provider say must happen?

Would the same action be equally safe for a production database?

### Step 3 — Evaluate a hypothetical cloud consequence

Imagine the change concerned a database attribute that required replacement.

Your interviewer asks:

"The plan only shows one resource changing. What's the problem?"

Explain why resource count is not a useful measure of release risk.

### Step 4 — Apply only the local lab change

```bash id="tfv022"
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan
```

Verify that the resulting file contains the new release version.

---

# Lab 7 — Saved Plans and Artifact Security

## Objective

Understand what a saved plan represents.

Create a fresh plan:

```bash id="tfv023"
terraform plan -out=tfplan
```

Inspect it:

```bash id="tfv024"
terraform show tfplan
```

Export the human-readable representation of the current plan:

```bash id="tfv025"
terraform show -json tfplan > tfplan.json
```

The JSON representation contains detailed configuration and planned-value information.

### Tasks

Why shouldn't a production plan be automatically published to a public CI artifact store?

What sensitive information might be present?

What configuration and backend identity is the plan associated with?

Why is applying a reviewed saved plan generally preferable to silently generating an unrelated plan later in the deployment process?

### Important qualification

The lab contains no actual secrets.

Do not insert real credentials merely to demonstrate the security risk.

---

# Lab 8 — Environment Isolation Review

## Scenario

The company has two Terraform environments.

Development uses one state backend and one cloud account.

Production uses another.

An engineer accidentally selects the production state while passing a variable called `environment=dev`.

### Task A — Explain the danger

Does the variable prevent Terraform from modifying production-managed resources?

Why not?

### Task B — Design the preflight check

Your proposed pipeline should verify:

- Configuration revision.
- Root module.
- Backend and state identity.
- Workspace.
- Provider account or project.
- Region.
- Intended environment.
- Approved plan identity.

### Task C — Fail closed

Describe the behavior when any identity differs from the approved deployment target.

### Acceptance criteria

You can explain why environment isolation requires actual credentials and state boundaries rather than descriptive variable names.

---

# Lab 9 — The Lock Incident

## Scenario

A production apply is running.

A second engineer starts another apply and receives a state-lock error.

They propose disabling locking.

### Investigation

What does the lock protect?

What evidence is needed to establish whether the first operation remains active?

When, if ever, is force-unlocking appropriate?

Why is it safer to wait for an active operation than to remove its lock?

### Design exercise

Describe a CI/CD mechanism that ensures only one approved production infrastructure operation can run against a particular state at a time.

Explain why this serialization complements, but doesn't replace, backend state locking.

---

# Lab 10 — The Partial Apply

## Scenario

A Terraform plan contains five changes.

Three resources are created successfully.

The fourth operation fails because the cloud provider rejects its configuration.

The fifth operation never starts.

The pipeline reports failure.

### Task A — Explain state and reality

What has changed?

Can the engineer assume Terraform rolled back the first three operations?

### Task B — Investigate

What evidence would you gather from apply logs, Terraform state, and provider APIs?

### Task C — Recover

Would you rerun the old saved plan immediately?

Or generate a fresh plan after inspecting the partially modified environment?

Explain.

### Acceptance criteria

You understand that Terraform apply is not one atomic transaction across all provider resources.

You can reason about partial success and safe recovery.

---

# Final Incident — The Plan That Would Undo Production Recovery

## Business context

A SaaS application runs on infrastructure managed through Terraform.

During an incident, an operator manually increases application capacity from three instances to five.

The service recovers.

The Terraform configuration still declares three instances.

A scheduled infrastructure pipeline runs.

The plan proposes restoring the declared value.

At the same time, a Terraform resource was renamed, and the plan appears to replace a critical database.

A second pipeline is blocked by a state lock.

### Required incident report

Prepare a short diagnosis including:

**Observed problem:** What changed in real infrastructure?

**Configuration intent:** What does Terraform declare?

**State relationship:** Which resources and addresses are associated in state?

**Drift:** What external modification occurred?

**Refactoring issue:** Why does the database replacement appear?

**Locking:** Why must competing state operations be prevented?

**Containment:** What should happen before approving any plan?

**Correction:** Which configuration, state-refactoring, or ownership changes are necessary?

**Verification:** How would you prove the intended infrastructure remains operational?

### Interviewer challenge

Your interviewer says:

"The plan is green, it only changes four resources, and Terraform knows the desired state. Why not apply it?"

Explain why none of those facts establishes that the change is operationally safe.

---

# STOP — End of Independent Lab

Do not read the following diagnostic notes until after attempting the exercises.

The goal is to interpret Terraform evidence and defend operational decisions without being supplied the answer in advance.

---

# Lab Diagnostic Notes

## State and Configuration

The configuration declares the desired file.

The state associates the Terraform resource address with the managed object and recorded attributes.

The Local provider observes the actual file during normal refresh.

These perspectives can disagree after out-of-band modifications.

## Drift

Editing the managed file outside Terraform changes reality without changing configuration.

A normal plan should detect the resulting inconsistency.

A plan with refresh disabled may miss it.

The engineer must decide whether the external change should be preserved or reversed.

## Refresh-Only

Refresh-only mode updates Terraform's recorded understanding without deliberately reconciling external infrastructure toward configuration.

It is useful for reviewing drift.

Applying refreshed state doesn't automatically change the configuration's intended values.

## Resource Rename

Changing a resource address without a moved block can cause Terraform to interpret the change as removing one managed resource and creating another.

A moved block preserves the association under the new address.

## Saved Plans

A saved plan represents a particular proposed execution and captures relevant configuration and backend details.

It can contain sensitive information.

A production pipeline should protect it and associate it with the approved configuration and target environment.

## Environment Identity

An environment variable named `dev` doesn't enforce isolation.

Backend, state, workspace, provider account, region, and credentials determine the real operational context.

## Locking

State locks prevent concurrent operations from conflicting over the same state.

Disabling locking or force-unlocking an active operation can create unsafe concurrent writers.

## Partial Apply

Terraform may successfully create several resources before another operation fails.

Those changes are not automatically rolled back as one transaction.

Inspect current state and actual infrastructure before generating a new recovery plan.

## Final Incident — Expected Diagnosis

The manual capacity increase created intentional drift.

The infrastructure configuration still declares the old capacity.

The resource rename created an address-management problem that may lead to unnecessary replacement.

The state lock protects against conflicting operations.

A safe response pauses the automatic apply, establishes the intended infrastructure state, uses an appropriate moved block, preserves the correct capacity policy, reviews the resulting plan, and verifies the running application.

The appropriate goal is not simply making Terraform report no changes.

It is establishing that the correct infrastructure is managed safely.

---

# Further Reading

1. **Terraform — Plan Command**  
   https://developer.hashicorp.com/terraform/cli/commands/plan

2. **Terraform — Apply Command**  
   https://developer.hashicorp.com/terraform/cli/commands/apply

3. **Terraform — State Locking**  
   https://developer.hashicorp.com/terraform/language/state/locking

4. **Terraform — Backends**  
   https://developer.hashicorp.com/terraform/language/state/backends

5. **Terraform — Backend Configuration**  
   https://developer.hashicorp.com/terraform/language/backend

6. **Terraform — Refresh-Only Mode**  
   https://developer.hashicorp.com/terraform/tutorials/state/refresh

7. **Terraform — Refactoring with Moved Blocks**  
   https://developer.hashicorp.com/terraform/language/modules/develop/refactoring

8. **Terraform — Importing Resources**  
   https://developer.hashicorp.com/terraform/language/import

9. **Terraform — Lifecycle Rules**  
   https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle

10. **Terraform — Managing Sensitive Data**  
    https://developer.hashicorp.com/terraform/language/manage-sensitive-data

11. **Terraform — Local Provider**  
    https://registry.terraform.io/providers/hashicorp/local/latest/docs

12. **Terraform — Resource Targeting**  
    https://developer.hashicorp.com/terraform/cli/commands/plan#resource-targeting

Cross-reference SE340-L04 for IaC and deployment foundations, SE360-L01 for artifact provenance, CS350-L04 for migration safety, and SE360-L03 for the integrated broken-release investigation.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text id="tfcard"
SE360-L02 — TERRAFORM AND REPRODUCIBLE INFRASTRUCTURE
=====================================================

THREE REALITIES
---------------
CONFIGURATION:
  Desired infrastructure

STATE:
  Terraform resource associations
  and recorded attributes

REALITY:
  Actual provider-managed objects

They can disagree.

BASIC WORKFLOW
--------------
terraform init
terraform validate
terraform plan
terraform apply

VALIDATE:
  syntax and configuration consistency
  NOT operational safety

PLAN:
  proposed operations
  NOT guarantee of successful outcome

APPLY:
  executes operations
  NOT one atomic cloud transaction

SAVED PLAN
----------
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan

Saved plans may contain secrets.
Treat as sensitive artifacts.

Plan identity includes:
- configuration revision
- variable values
- provider versions
- backend/state context

STATE
-----
Resource address != physical ID.

State associates logical addresses
with real provider-managed objects.

terraform state list
terraform state show
terraform state pull

State may contain sensitive values.

Avoid manual state push unless
carefully controlled and necessary.

BACKENDS
--------
Determine state storage.

Remote backends can provide:
- shared state
- access control
- locking
- recovery/versioning where supported

Not every backend supports
the same locking capabilities.

LOCKING
-------
Prevents competing state writers.

Do not disable locks casually.
Do not force-unlock active operations.

DRIFT
-----
Actual resource differs from
declared/recorded expectations.

Normal plan refreshes observations.

-refresh=false:
  may conceal external changes

-refresh-only:
  reviews state/output updates
  without reconciling real resources

RESOURCE MOVES
--------------
Naive address rename may appear:
  destroy old
  create new

moved block:
  preserve managed association
  under new Terraform address

IMPORT
------
Connect existing real object
to Terraform resource address.

Review post-import changes.
Avoid duplicate state ownership.

LIFECYCLE
---------
prevent_destroy:
  helps reject planned destruction

create_before_destroy:
  replacement ordering,
  not universally feasible

ignore_changes:
  allows external attribute ownership,
  but may conceal unwanted drift

DEPENDENCY GRAPH
----------------
References imply relationships.

depends_on for dependencies
that cannot be inferred.

Graph order != application readiness.

MODULES
-------
Reusable infrastructure packages.

Review plans after module upgrades.
Small source diff may have
large physical blast radius.

ENVIRONMENTS
------------
Workspace name != security boundary.

Check:
- root module
- backend/state key
- workspace
- provider account/project
- region
- variables
- credentials

SECRETS
-------
sensitive=true:
  redacts display

Does NOT necessarily exclude
values from state or plan files.

Ephemeral values and write-only
arguments can reduce persistence
where supported.

PARTIAL APPLY
-------------
Some operations may succeed
before another fails.

No universal automatic rollback.

Inspect real resources and state.
Generate fresh recovery plan.

-TARGET
-------
Exceptional recovery tool,
not routine deployment strategy.

Repeated targeting can conceal
incomplete reconciliation.

PRODUCTION REVIEW
-----------------
What config is approved?
What state is selected?
What account is authenticated?
What resources are replaced?
What dependencies change?
Can objects coexist?
What data may be lost?
What happens after partial failure?
How is runtime health verified?

ANTI-PATTERNS
-------------
"The config is correct, so apply."
"The plan is small, so it's safe."
"Terraform state is just a cache."
"Use -lock=false to unblock."
"Force unlock; it's probably stale."
"Rename the resource like a variable."
"Disable refresh to hide drift."
"Workspace staging guarantees staging."
"Sensitive means never stored."
"Failed apply means nothing changed."
"Use -target for every deployment."
"Terraform apply success means app healthy."

MENTAL MODEL
------------
Configuration declares intent.
State preserves identity.
Providers expose reality.
Plan proposes reconciliation.

Engineer decides whether
the proposed change is safe.

NEXT
----
SE360-L03 — The Broken Release Studio
```
