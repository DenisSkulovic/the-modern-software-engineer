---
id: SE450-L05
course: SE450
title: "Configuration, Secrets, and Persistent State"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L04
next: SE450-L06
---




# SE450 — Kubernetes and Platform Engineering

## Lecture 05: Configuration, Secrets, and Persistent State

*The application survived. The process restarted, the Pod was replaced, and Kubernetes proudly reported everything healthy. Unfortunately, the application had forgotten its configuration, lost its local data, and started using credentials that no longer worked.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity platform running in Kubernetes.

One of its workers scans customer assets, discovers exposed services, and writes its findings to MongoDB.

The worker needs several things to do its job.

It needs a container image containing Python, scanning tools, and application code.

It needs configuration: the RabbitMQ hostname, scanning concurrency, module selection, and the location of the MongoDB cluster.

It needs credentials: perhaps a token for a commercial threat-intelligence API.

It needs temporary storage: a directory where it can unpack scanner output, generate intermediate files, and merge results.

And it needs durable storage somewhere: the database containing completed findings, unfinished scan records, and customer information.

Everything works.

Then Kubernetes replaces the worker Pod.

The new Pod starts successfully. The image is correct. The process launches. The health check passes.

But the worker cannot authenticate to an external API, and its unfinished local scan data has vanished.

What happened?

Kubernetes restored the execution environment without necessarily restoring everything the application depended upon.

The mistake was treating these dependencies as though they all belonged to the same category.

They don't.

## 1. Four different kinds of information

Picture a restaurant.

The kitchen has equipment: ovens, refrigerators, knives, and counters.

It has instructions: recipes, opening hours, and preparation procedures.

It has credentials: keys to the building, access codes for suppliers, and payment-system authorization.

And it has business records: customer orders, invoices, reservations, and financial accounts.

If the restaurant burns down and you rebuild it, those things require very different recovery strategies.

You can buy new equipment.

You can restore recipes from copies.

You must securely reissue access credentials.

But if you lose the authoritative order history, rebuilding the kitchen doesn't reconstruct what customers already paid for.

Kubernetes applications have the same distinctions.

**The image** provides executable software and packaged dependencies.

**Configuration** tells the software how to behave in its environment.

**Secrets** provide sensitive information needed to access protected systems.

**Persistent state** records facts that must survive process replacement.

There's also a fifth category: temporary scratch data that may be safely discarded.

The first architectural task is to decide which information belongs to which category.

## 2. Configuration doesn't belong in the image

Suppose you build a scanner image for production.

The image contains Python code, Nmap, various security tools, and your application dependencies.

Should it also contain the production MongoDB hostname and API credentials?

Usually not.

The same application image might be deployed in development, staging, and production.

The executable software can remain identical while environment-specific settings differ.

Kubernetes provides ConfigMaps for non-confidential configuration.

A ConfigMap might specify:

- The RabbitMQ service address.
- The maximum number of concurrent scans.
- A logging level.
- A set of enabled scanner modules.

The Pod references those values, and Kubernetes makes them available to the container.

This separates what the program *is* from how it is *configured to behave*.

It also allows configuration to evolve independently of rebuilding the application image.

But that independence comes with an important subtlety.

Changing a ConfigMap doesn't necessarily change a running application's effective configuration immediately.

We'll return to that shortly.

## 3. A Secret isn't a magic vault

The worker also needs an API token.

That information is confidential.

Kubernetes provides Secret objects for values such as passwords, tokens, keys, and certificates.

A Secret can be supplied to a Pod as an environment variable or mounted as files.

But the word *Secret* is dangerously reassuring.

A Kubernetes Secret is not automatically a complete secret-management solution.

Its values are commonly represented as base64-encoded data in API manifests.

Base64 is an encoding, not encryption.

Anyone who can decode base64 can recover the original value.

The security of a Secret depends on access control, storage encryption, delivery mechanisms, operational practices, and the application's own behavior.

If your scanner prints its API token into logs, Kubernetes cannot make those logs safe merely because the original token came from a Secret.

**A Secret is a sensitive Kubernetes API resource, not a promise that the credential can never leak.**

## 4. Temporary storage should be allowed to disappear

Now consider the scanner's working directory.

It downloads data, produces intermediate JSON files, and temporarily stores parsed results.

Perhaps those files are useful only while one scan is running.

If the process restarts inside the same Pod, we might want the files to remain available.

But if the Pod is permanently replaced, we may be comfortable starting over.

Kubernetes provides an `emptyDir` volume for this kind of storage.

The volume is created for a Pod and can be shared by its containers.

Its contents can survive ordinary container restarts within that same Pod.

But when the Pod is removed, the associated `emptyDir` data is removed.

That makes it suitable for scratch files, caches, and temporary coordination.

It is not appropriate as the sole authoritative location for irreplaceable customer findings.

The word *volume* alone does not guarantee persistence.

Some volumes are deliberately ephemeral.

## 5. Persistent storage has a life beyond the Pod

Now imagine a database Pod.

Its process is replaceable, but its data files are not disposable.

If Kubernetes replaces the Pod and gives the new instance an empty filesystem, the database may start without its previous data.

That's unacceptable.

Kubernetes provides PersistentVolumes and PersistentVolumeClaims to separate storage resources from individual Pod lifetimes.

A PersistentVolume represents a storage resource available through the cluster's storage system.

A PersistentVolumeClaim is a request for storage with particular characteristics.

A Pod can mount storage through a claim.

The volume may remain bound to that claim even when the Pod using it disappears.

A replacement Pod can potentially mount the same storage and continue using the existing files.

That is the central idea.

But there are conditions.

The volume must be available. Its storage system must be healthy. The replacement Pod must be placed where the volume can be accessed. The access mode must permit the intended attachment.

And the application must know how to recover safely from an interrupted process.

**Persistent storage preserves a storage resource across Pod replacement. It does not automatically guarantee application consistency, availability, or recoverability.**

## 6. The Pod is replaceable; the business state is not

Return to our scanner.

A good architecture might look like this:

```text
                  SCANNER POD
               +---------------+
               | Scanner image |
               |               |
ConfigMap -----> Configuration |
Secret --------> Credentials   |
               |               |
emptyDir -----> Scratch files  |
               +---------------+
                       |
             Durable operations
                       |
              +--------+--------+
              |                 |
           MongoDB          RabbitMQ
       Findings/state      Pending work
              |                 |
       Independent persistence and
          recovery mechanisms
```

The diagram makes an important point.

The scanner Pod itself doesn't need a persistent volume for every kind of information.

If scan results are already written durably to MongoDB, the worker may not need a dedicated persistent disk for those results.

If RabbitMQ retains unacknowledged work, the application may be able to retry an interrupted scan.

A temporary scanner directory can remain ephemeral.

The right solution is not to attach permanent disks to every container.

It's to place each kind of state behind the correct durability boundary.

## The minute-long mental replay

A Pod starts.

Its image supplies executable software.

ConfigMaps supply ordinary settings.

Secrets supply confidential data, subject to the cluster's security controls.

Ephemeral volumes supply temporary files whose lifetime is tied to the Pod.

PersistentVolumes supply storage that can outlive the Pod, subject to their claim and storage lifecycle.

External databases and brokers may provide durable business state without requiring the application Pod itself to manage local permanent storage.

When the Pod disappears, each resource follows its own lifecycle.

The engineering challenge is to ensure that the application's required state survives through the appropriate mechanism.

### Three questions before the Deep Dive

1. Why is an `emptyDir` volume suitable for scanner scratch files but not for the only copy of customer scan results?
2. Why doesn't changing a ConfigMap necessarily update the effective configuration of an already running application?
3. Why is a persistent volume not the same thing as a verified backup and recovery strategy?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Worker That Returned Without Its Memory

Our cybersecurity platform runs several scanner workers.

Each worker receives tasks from RabbitMQ, executes scanning modules, and records findings.

The application uses three kinds of storage:

- MongoDB for durable scan results and application records.
- An `emptyDir` for temporary scanner output.
- A shared configuration directory populated through Kubernetes resources.

One afternoon, a worker node fails.

Kubernetes detects the failure and eventually creates a replacement Pod on another node.

The new worker starts correctly.

But it cannot continue an unfinished scan because its intermediate files are gone.

Meanwhile, the application reports an authentication error when calling a threat-intelligence API.

The platform engineer discovers that the mounted credential was rotated, but one code path still expects the previous credential format.

A third issue emerges: an older configuration value remains active in some Pods even though the ConfigMap has been updated.

The team initially believes these problems have one cause.

They don't.

We've encountered three independent contracts:

**Data lifetime:** how long does stored information survive?

**Configuration propagation:** when does an application observe a configuration change?

**Credential validity:** which identity or secret value is accepted by another system?

Kubernetes provides mechanisms for all three, but each has different semantics.

Let's investigate them separately.

## 2. The Container Filesystem Is Not Your Database

A container starts from an image and receives a writable filesystem layer.

The image contains its packaged files.

The writable layer allows the running container to create and modify files.

This is convenient for temporary execution state.

But the writable layer is tied to the container's lifecycle.

When Kubernetes replaces a container instance, you shouldn't expect the new instance to inherit the previous container's writable filesystem.

When a Pod is replaced on another node, assuming that its local container files will follow it is especially dangerous.

### The hidden persistence bug

Suppose a Python worker writes results into:

`/app/results/scan-4821.json`

It then intends to upload the file to MongoDB or object storage.

But the upload hasn't happened yet.

The Pod disappears.

The replacement worker starts with the same container image, but the old file isn't there.

From Kubernetes' perspective, this may be ordinary behavior.

From the application developer's perspective, a business result has vanished.

The problem is an invalid durability assumption.

The filesystem path was treated as authoritative storage, but it belonged to a disposable execution environment.

### A useful classification

When designing a containerized application, classify each write.

Is it a temporary cache?

Is it intermediate work that can be recomputed?

Is it a checkpoint required for recovery?

Is it a completed business result?

Is it an audit record that must not be lost?

The persistence mechanism should reflect the answer.

If a file can be regenerated cheaply, ephemeral storage may be appropriate.

If the file represents irreplaceable business state, it needs a durable storage strategy.

And if it belongs to a stateful database, the database's own consistency and recovery mechanisms matter in addition to the underlying disk.

## 3. ConfigMaps: Configuration as an API Resource

A ConfigMap stores non-confidential configuration data.

It is a namespaced Kubernetes API object containing key-value pairs.

A ConfigMap can store ordinary UTF-8 text values and certain binary data.

Its purpose is to make configuration available independently of a container image.

Suppose our scanner has these settings:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: scanner-config
data:
  RABBITMQ_HOST: rabbitmq.security.svc.cluster.local
  LOG_LEVEL: info
  MAX_CONCURRENT_SCANS: "5"
```

The example contains strings.

Even though the concurrency setting represents a number, its ConfigMap value is stored as text.

The application is responsible for parsing the value and validating that it has a sensible meaning.

### Configuration is not automatically valid

A ConfigMap could declare:

`MAX_CONCURRENT_SCANS: "five thousand bananas"`

Kubernetes doesn't inherently understand the scanner application's concurrency semantics.

The API may accept the ConfigMap because it's valid configuration data from Kubernetes' perspective.

But the application may reject it or behave incorrectly.

This resembles L01's distinction between accepted intent and application correctness.

Kubernetes stores and distributes configuration.

The application owns the interpretation of that configuration.

### Missing configuration

A Pod can reference individual ConfigMap keys.

If a required reference cannot be resolved, the container may fail to start.

That is often preferable to silently starting an application with an unintended fallback value.

However, the failure can be confusing if engineers investigate only the application logs.

The process may never have started far enough to emit meaningful logs.

Pod events and container waiting reasons can reveal missing configuration references.

This illustrates another recurring diagnostic principle:

**When the process doesn't start, first determine whether Kubernetes successfully constructed its environment.**

## 4. Environment Variables Versus Mounted Configuration Files

Kubernetes can deliver ConfigMap values through environment variables or mounted files.

These approaches have different update behavior.

Consider a worker reading a configuration value from the environment at process startup.

It begins with:

`MAX_CONCURRENT_SCANS=5`

A developer changes the ConfigMap value to 10.

Will the running Python process immediately see 10?

No.

Environment variables are established when the container process starts.

Updating the ConfigMap doesn't rewrite the environment of an already running process.

The Pod must be replaced or the relevant container restarted with an updated environment to pick up the new value.

### Mounted configuration files behave differently

Suppose the ConfigMap is mounted as a directory containing configuration files.

Kubernetes can update the projected files when the source ConfigMap changes.

That propagation is not necessarily instantaneous.

It depends on kubelet synchronization and cache/watch behavior.

The running application must also notice the file change and reload it.

If the Python worker reads the file only once during startup, the updated file may exist without changing the effective application configuration.

This is the distinction between **delivery** and **adoption**.

Kubernetes can deliver a new configuration file.

The application decides whether and when to adopt its contents.

### The subPath exception

A particularly easy trap involves `subPath` mounts.

If a container mounts an individual ConfigMap file through `subPath`, that mount does not receive normal automatic ConfigMap updates.

A developer may assume that all mounted ConfigMap files update dynamically.

They don't.

The mounting mechanism matters.

This is worth remembering because `subPath` is frequently used to place one configuration file into an existing directory without masking the entire directory.

### Why replacing Pods is often simpler

Dynamic configuration reload can be useful.

But it introduces complexity.

What happens if one process reloads the new configuration while another still uses the old value?

What if the configuration contains several related fields that must change together?

What if the application reads the file halfway through a reload procedure?

For many ordinary services, a simpler and more predictable strategy is to create a new configuration version and roll out new Pods using it.

The new Pods start with a coherent configuration.

Readiness checks determine when they can receive traffic.

Old Pods are then retired.

This makes configuration deployment resemble application deployment.

The approach is particularly attractive when correctness and reproducibility matter more than instantaneous configuration changes.

## 5. Immutable Configuration and Versioned Deployments

Kubernetes supports immutable ConfigMaps.

Once a ConfigMap is marked immutable, its data cannot be modified in place.

This can improve consistency and reduce unnecessary change tracking.

But it requires a different update strategy.

Instead of modifying an existing ConfigMap, create another one with a new name.

For example:

`scanner-config-v12`

Then update the Deployment to reference the new ConfigMap.

Kubernetes creates replacement Pods whose specifications point at the new configuration object.

### Why versioned configuration is attractive

Imagine debugging a production incident.

The application image is pinned to a specific version.

But the ConfigMap was edited repeatedly throughout the day without any clear connection to the Deployment revisions.

Which configuration was active when the failure happened?

Which Pods loaded which version?

A versioned configuration name, or another reliable mechanism connecting a rollout to a configuration revision, makes the deployment easier to reconstruct.

This is especially useful when using GitOps.

The Git repository describes a specific desired application configuration.

The deployment process applies a known configuration version.

The workload is updated to consume that version.

The resulting release becomes easier to reason about and roll back.

### A subtle rollback problem

Suppose version two of an application requires configuration format two.

You deploy both together.

Then you roll back only the application image to version one, leaving configuration format two active.

The old application may not understand the new settings.

A rollback is not necessarily safe unless compatible versions of software and configuration are restored together.

**Configuration is part of the deployed software contract, even when it lives outside the image.**

## 6. Secrets: Sensitive Information With an API Lifecycle

Now consider the scanner's commercial API token.

Unlike ordinary concurrency settings, the token should not appear in a public configuration repository.

Kubernetes provides Secret resources for confidential values.

A Secret can contain passwords, authentication tokens, TLS credentials and other sensitive data.

But security depends on the entire lifecycle.

How is the credential created?

Where is it stored?

Who can read it?

How is it delivered?

How does the application consume it?

How is it rotated?

How is it revoked?

And how can operators determine whether it was exposed?

A Secret resource is only one component of that system.

### Base64 is not encryption

A Secret's `data` field uses base64-encoded values.

That representation allows arbitrary bytes to be transmitted through the Kubernetes API.

It does not provide confidentiality.

A person who can read the encoded value can decode it.

The API also supports `stringData` for convenient cleartext input, which is transformed into stored Secret data.

Neither representation makes it safe to commit actual production credentials into Git.

### Storage encryption matters

Kubernetes Secrets are not necessarily encrypted at rest in etcd by default.

Clusters should configure appropriate encryption at rest for sensitive resources.

Managed Kubernetes providers may offer their own encryption arrangements, so the actual configuration must be verified.

Encryption at rest helps protect stored data against certain threats.

It doesn't prevent an authorized API client from retrieving a Secret.

And it doesn't prevent an application from disclosing a credential after it has read it.

### RBAC matters

Kubernetes role-based access control determines which identities can perform operations on resources.

Granting broad read access to Secrets is dangerous.

But there is a subtler issue.

An identity with permission to create Pods in a namespace may be able to create a Pod that mounts a Secret from that namespace and exfiltrates its value, even without direct permission to read the Secret API object.

Therefore, protecting Secrets requires considering both direct Secret access and the ability to create workloads that consume them.

This is one reason namespace boundaries and workload-admission permissions matter.

We'll examine this more deeply in SE450-L06.

## 7. Secret Delivery: Environment Variables or Files?

A Secret can be referenced through environment variables.

For example, a container might receive an `API_TOKEN` environment variable.

This is convenient because many libraries already support environment-based configuration.

But environment variables have operational risks.

They can be exposed through careless diagnostic output, process-environment inspection by sufficiently privileged actors, crash reports or application logging.

And, like ConfigMap-backed environment variables, they don't automatically change inside an already running process when the Secret is updated.

### Mounted Secret files

A Secret can also be mounted as files.

On Linux, Kubernetes normally uses memory-backed storage for Secret volumes rather than writing those projected values into ordinary persistent node storage.

The application reads the credential from a known file path.

This can be preferable for applications that support file-based credentials, particularly when dynamic rotation is required.

However, the application must still handle file updates correctly.

The fact that the file changes doesn't guarantee that an HTTP client, database driver or authentication library reloads the new value.

### Which approach is safer?

There is no universal winner.

Environment variables may be simple and compatible with the application's configuration system.

Mounted files can avoid embedding the credential in the process environment and may support refresh without replacing the Pod.

But they require appropriate filesystem permissions, careful consumption and rotation handling.

In either case, restrict access to the containers that genuinely need the credential.

A logging sidecar should not automatically receive every Secret used by the application container.

### ServiceAccount tokens

If a Pod needs to authenticate to the Kubernetes API, it may use a ServiceAccount identity.

Modern Kubernetes supports short-lived, bound ServiceAccount tokens projected into Pods.

This is generally preferable to relying on legacy long-lived ServiceAccount token Secrets.

But not every application needs Kubernetes API access.

For a scanner worker that communicates only with RabbitMQ, MongoDB and external scanning targets, an automatically mounted Kubernetes API credential may be unnecessary.

Disabling unnecessary ServiceAccount token mounting reduces exposure.

That is a straightforward application of least privilege.

## 8. Credential Rotation Is a Protocol, Not a File Update

Suppose our scanner uses token A to access an external API.

The provider issues token B.

The platform updates the Kubernetes Secret.

Have we successfully rotated credentials?

Not necessarily.

Some workers may have token A in their environment.

Others may read token B from updated files.

Some may hold an authenticated connection or client object created with token A.

The provider might revoke token A immediately.

Now the cluster contains Pods at different stages of adopting the new credential.

### A safer rotation sequence

When the external system supports overlapping credentials, a practical rotation often looks like this:

First, create and authorize token B while token A remains valid.

Second, distribute token B to the intended consumers.

Third, trigger or verify adoption by every relevant application instance.

Fourth, confirm successful authentication using token B.

Finally, revoke token A after the transition is complete.

The precise order depends on the provider's API and credential model.

Some systems don't support overlapping credentials. Others use short-lived dynamically issued tokens.

The architecture must adapt to those constraints.

### Why immediate revocation is dangerous

Imagine changing the Secret and immediately revoking the old token.

The Secret object now contains B.

But a running Pod still uses environment variable A.

That Pod will continue attempting to authenticate with A until it restarts.

Its Secret reference is correctly configured, yet the process is still using the old value.

The failure is not in the Secret object.

It's in the rotation procedure.

### External secret stores

For complex organizations, an external secret-management system can become the authoritative source of credentials.

Kubernetes workloads may retrieve credentials directly or use an integration that projects them into Pods.

The Secrets Store CSI Driver is one example of an ecosystem mechanism for mounting external secret data, subject to its provider and configuration.

Other controllers synchronize values into Kubernetes Secret objects.

These approaches introduce additional dependencies and failure modes, but they can centralize rotation, auditing and credential governance.

The correct choice depends on scale, security requirements and operational maturity.

**Moving a secret into an external vault doesn't eliminate the need to design how applications receive, refresh and revoke credentials.**

## 9. Volumes: A Mount Is Not a Durability Guarantee

We now move from configuration and credentials to storage.

Kubernetes supports many kinds of volumes.

Some are temporary.

Some project API data.

Some expose storage managed by an external system.

Some are tied to a specific node.

Some survive Pod replacement.

The word *volume* describes a mounting abstraction, not one universal durability contract.

### The `emptyDir` volume

An `emptyDir` is created when a Pod is assigned to a node.

Its contents can survive container restarts within that Pod.

The data is removed when the Pod is removed.

It is useful for scratch files, temporary downloads and shared data between containers in the same Pod.

For example, a scanner might use `emptyDir` to hold intermediate output while multiple helper processes execute.

If the Pod disappears, those files disappear with it.

### Memory-backed `emptyDir`

An `emptyDir` can use memory-backed storage through `medium: Memory`.

This can be useful for certain temporary workloads requiring fast access.

But memory-backed storage consumes memory resources.

Writing large files into it isn't a way to avoid memory limits.

It can contribute to container or Pod memory pressure and eventually trigger resource-related failures.

### Disk-backed `emptyDir`

Ordinary disk-backed `emptyDir` uses node-local ephemeral storage.

That storage competes with other node-level temporary storage needs, such as container logs and writable layers.

A scanner that generates hundreds of gigabytes of temporary output can place severe pressure on the node.

This may trigger ephemeral-storage eviction even if CPU and memory remain healthy.

Resource planning must consider local ephemeral storage, not just RAM and processor capacity.

### `hostPath`

A `hostPath` volume exposes a path from the node's filesystem to a Pod.

It can be useful for certain privileged node-level agents.

But it is dangerous for ordinary application storage.

The contents belong to a specific node.

Moving the Pod to another node doesn't automatically move those files.

The mount can also expose sensitive host files or create serious security risks if permissions are too broad.

For a normal application, `hostPath` is usually not the right solution to persistence.

### The central distinction

A Pod volume and a persistent volume are not synonyms.

Some Pod volumes are explicitly tied to one Pod lifetime.

PersistentVolumes are separate cluster storage resources with their own lifecycle.

That separation is what enables durable storage across Pod replacement.

## 10. PersistentVolumes and PersistentVolumeClaims

Imagine our platform needs a stateful service with 100 GiB of durable storage.

The application shouldn't necessarily know whether the underlying storage is a cloud block disk, network filesystem, or another supported storage system.

It needs to express requirements.

A PersistentVolumeClaim, or PVC, provides that request.

The PVC can specify required capacity, access modes and a storage class.

The Kubernetes storage system then finds or provisions a suitable PersistentVolume, or PV.

### The relationship

```text
                 APPLICATION POD
                       |
                       v
               Volume mount
                       |
                       v
           PersistentVolumeClaim
                "I need storage"
                       |
                       v
               PersistentVolume
             "Storage resource"
                       |
                       v
              Storage backend
        Cloud disk / network storage /
           other supported system
```

The PVC is the consumer-facing storage request.

The PV represents the provisioned storage resource.

The storage backend implements the actual persistence.

A PVC doesn't contain the application's data in the same sense that a file does.

It is a Kubernetes API object representing a claim to storage.

### Static provisioning

An administrator can create a PersistentVolume that represents existing storage.

A PVC can bind to a suitable PV.

This is static provisioning.

It is useful when storage must be prepared independently or when the underlying infrastructure has special requirements.

### Dynamic provisioning

With dynamic provisioning, creating a PVC can trigger the creation of an appropriate storage resource through a configured storage provisioner.

This is common in managed Kubernetes environments.

The developer requests storage without manually creating a cloud disk.

But the requested storage must still be supported by the cluster.

If no suitable StorageClass or provisioner exists, the PVC may remain Pending.

The API accepting the PVC is not proof that actual storage has been created.

That should sound familiar by now.

Kubernetes is still a reconciliation system.

## 11. StorageClasses: Choosing the Storage Contract

A StorageClass describes how a class of storage should be provisioned and managed.

A cluster might provide different classes for different requirements.

One class might use fast block storage.

Another might use network-accessible storage.

Another might emphasize lower cost or a particular availability arrangement.

A PVC specifies the desired StorageClass.

The storage provisioner then attempts to satisfy the request using that class's configuration.

### Storage performance matters

Two persistent volumes with the same capacity can behave very differently.

One might deliver high random I/O performance but only attach to one node at a time.

Another might support access from multiple nodes but have different latency characteristics.

A third might be tied to a particular availability zone.

Capacity isn't the entire storage requirement.

Applications also care about latency, throughput, consistency, sharing and failure behavior.

### The StorageClass isn't a database design

Suppose we choose very fast cloud block storage for MongoDB.

Does that guarantee correct replication?

No.

Does it guarantee transaction durability across an entire database cluster?

No.

Does it guarantee that an accidental deletion can be recovered?

No.

The StorageClass determines important storage infrastructure characteristics.

Database correctness still depends on the database's write semantics, replication configuration, recovery design and operational practices.

## 12. Access Modes: Who May Mount the Volume?

Persistent volumes support access modes describing how storage may be mounted.

The familiar modes are:

**ReadWriteOnce**, abbreviated RWO.

**ReadOnlyMany**, abbreviated ROX.

**ReadWriteMany**, abbreviated RWX.

And **ReadWriteOncePod**, abbreviated RWOP, for supported CSI-backed storage.

These names are easy to memorize and easy to misunderstand.

### ReadWriteOnce

RWO permits read-write mounting by a single node.

It does not universally mean that only one Pod can mount the volume.

Multiple Pods on the same node may be able to access an RWO volume, depending on the storage implementation and circumstances.

This distinction matters when reasoning about exclusivity.

If you need Kubernetes to enforce single-Pod access to suitable CSI storage, RWOP may better express the requirement.

### ReadOnlyMany

ROX permits the volume to be mounted read-only by multiple nodes, subject to storage support.

That can be useful for shared datasets that should not be modified by consumers.

### ReadWriteMany

RWX permits read-write mounting by multiple nodes.

This is useful for certain shared-filesystem workloads.

But an RWX volume is not automatically a database transaction coordinator.

If two application instances write conflicting updates to the same files, the application still needs appropriate coordination.

Storage sharing and application consistency are different properties.

### ReadWriteOncePod

RWOP is designed for single-Pod read-write access with supported CSI storage.

It provides a stronger Kubernetes-level exclusivity constraint than ordinary RWO.

But even here, one should not leap from exclusive mounting to universal data correctness.

The application can still corrupt its own data.

A node can still crash.

A storage system can still fail.

Access modes describe supported access patterns, not complete application guarantees.

## 13. Storage Topology: Why the Pod Cannot Move

Now we reach the central production trap.

Our stateful service runs in availability zone A.

Its persistent volume is backed by a cloud block disk provisioned in zone A.

The node fails.

Kubernetes needs a replacement Pod.

A suitable node exists in zone B.

CPU and memory are available.

The scheduler would ordinarily be happy to place the Pod there.

But the disk is tied to zone A.

The storage backend cannot attach it to the node in zone B.

The replacement Pod may remain Pending or encounter volume attachment and mounting failures, depending on the scheduling and storage configuration.

The persistent data exists.

The replacement process is ready.

Yet the two cannot be brought together.

This is a storage-topology constraint.

### Persistent does not mean globally accessible

A persistent volume can preserve data while remaining tied to a particular location or storage domain.

It may be available to other nodes in the same zone.

It may not be available across zones.

The exact behavior depends on the storage backend.

This is why storage topology must participate in scheduling.

### `Immediate` versus `WaitForFirstConsumer`

StorageClasses support volume binding modes.

With `Immediate` binding, provisioning or binding can occur as soon as the PVC is created.

This may happen before Kubernetes knows which Pod will consume the storage and where that Pod is allowed to run.

For topology-constrained storage, the resulting volume might be placed in a location incompatible with the consumer's scheduling requirements.

`WaitForFirstConsumer` delays binding or provisioning until a Pod using the claim exists.

This allows the scheduler and storage provisioning process to consider the Pod's placement requirements together.

It's particularly useful when storage cannot be accessed from every node.

### An important scheduling pitfall

A Pod using a PVC with `WaitForFirstConsumer` can behave incorrectly if the Pod bypasses the scheduler through an explicit `nodeName` assignment.

The storage binding process may be unable to use the expected scheduling coordination.

A node selector or other scheduler-aware placement mechanism is generally more appropriate.

The larger lesson is that CPU, memory and storage topology are not independent scheduling problems.

The scheduler must find a placement satisfying all relevant constraints.

## 14. CSI: The Bridge to Real Storage Systems

How does Kubernetes actually create and mount cloud disks?

It generally relies on storage integrations.

The Container Storage Interface, or CSI, provides a standard mechanism for storage providers to integrate with container orchestration systems.

CSI drivers implement operations needed to provision, attach, stage, mount, expand and manage volumes, according to their capabilities.

Kubernetes communicates with those drivers through appropriate controllers and node-side components.

### The logical sequence

Imagine a Pod requiring a dynamically provisioned persistent volume.

A PVC describes the storage request.

A StorageClass identifies the provisioner.

A CSI provisioner may create the storage resource.

The PVC binds to the resulting PV.

The scheduler chooses a compatible node.

If the storage requires attachment, the relevant storage components arrange for attachment to that node.

Node-level CSI operations prepare and mount the volume.

The kubelet then makes the mounted storage available to the container.

The application finally sees a filesystem path.

Each stage can fail.

### Why CSI troubleshooting is different from application troubleshooting

Suppose MongoDB logs don't appear because the container never starts.

The Pod is stuck in `ContainerCreating`.

Events report a volume attachment failure.

This is not necessarily a MongoDB configuration bug.

The database process may never have executed.

You need to inspect the PVC, PV, StorageClass, selected node, CSI driver and storage backend.

A cloud permission problem could prevent disk attachment.

A stale attachment could block moving the volume to another node.

A storage topology mismatch could make the placement invalid.

A missing CSI component could prevent mounting altogether.

**When a volume cannot be mounted, investigate the storage control path before debugging application code that hasn't started.**

## 15. The StatefulSet Storage Relationship

Recall SE450-L02.

A StatefulSet provides stable logical identities for stateful Pods.

It can also define `volumeClaimTemplates`.

These templates cause PersistentVolumeClaims to be created for individual StatefulSet members.

For example, a three-member database StatefulSet might have stable members:

`mongo-0`

`mongo-1`

`mongo-2`

Each member can have its own PVC.

The claims remain associated with the corresponding logical identities.

If `mongo-1` is replaced, the new Pod can reference the same claim.

This is much more appropriate for ordinary database member storage than attaching one shared writable directory to every database instance.

### Stable identity isn't guaranteed availability

Suppose the volume for `mongo-1` cannot attach.

The StatefulSet can recreate the logical Pod identity, but the Pod may remain unable to start.

Suppose the volume contains corrupted database files.

Reattaching it preserves the corruption.

Suppose the database cluster loses quorum.

The presence of stable Pod names doesn't restore safe write availability.

Again, the Kubernetes storage model and database replication model solve different problems.

### PVC retention

StatefulSet PVCs are normally retained across certain StatefulSet deletion or scale-down operations under the default retention behavior.

Kubernetes also supports configurable PVC retention policies for StatefulSets.

That means deleting a StatefulSet doesn't always delete its data claims.

This is often desirable because accidental workload deletion shouldn't automatically erase the database.

But it can surprise developers expecting cleanup to remove every resource.

Conversely, explicitly configuring deletion policies may make scale-down or StatefulSet deletion destructive to storage.

The retention behavior must be known before running potentially destructive commands.

## 16. Reclaim Policies: What Happens When the Claim Disappears?

A PersistentVolume has a reclaim policy describing what happens when its claim is released.

Two important values are `Retain` and `Delete`.

### Retain

With Retain, releasing the PVC does not automatically destroy the underlying storage.

The PV and its data require an appropriate administrator-managed reclamation process.

This can protect valuable data from accidental deletion.

But it can also leave storage resources consuming money after applications are removed.

### Delete

With Delete, releasing the claim can cause the PV and its backing storage resource to be deleted through the provisioner.

Dynamically provisioned volumes commonly use Delete by default, unless configured otherwise.

This is convenient for disposable environments.

It can be dangerous for valuable state.

### The destructive cleanup trap

Imagine a developer removing a namespace containing a stateful application and its PVCs.

The PVs use a Delete reclaim policy.

The storage provisioner processes the released claims.

The underlying disks may be deleted.

The developer thought they were deleting Kubernetes configuration.

In reality, the operation also triggered the storage lifecycle.

This is why persistent storage requires ownership and deletion policies that match the value of the data.

A command that looks like infrastructure cleanup can become a data-destruction operation.

For valuable storage, inspect PVCs, PVs, reclaim policies, snapshots and backups before deleting resources.

## 17. Persistent Storage Is Not Backup

This distinction deserves its own section because confusing the two can destroy a business.

A persistent disk survives ordinary Pod replacement.

That's useful.

But imagine the application accidentally deletes a collection of important records.

The deletion is written to the persistent disk.

The disk faithfully preserves the deletion.

Or imagine an application bug corrupting an index.

The storage system durably stores the corrupted bytes.

Persistence is working.

Your data is still damaged.

### What backup solves

A backup provides an independent recoverable copy of data from an earlier state.

A recovery strategy defines how that copy can be restored and how much data loss or downtime is acceptable.

Those requirements belong to the application's operational design.

### Volume snapshots

Kubernetes supports the VolumeSnapshot API through compatible storage integrations and snapshot controllers.

A snapshot can capture a point-in-time storage representation.

But snapshot availability depends on the storage driver and installed components.

And a storage snapshot is not automatically an application-consistent database backup.

Imagine a database writing several related files.

A crash-consistent snapshot may capture storage as though the machine stopped abruptly at that moment.

The database may be able to recover using its transaction log.

But that depends on the database's recovery design and the snapshot's consistency guarantees.

For some workloads, application coordination or database-native backup mechanisms are required.

### Backups must survive the relevant failure domain

A backup stored only in the same failing storage environment may not provide meaningful protection.

A production recovery plan should consider independence, retention, access control, corruption, accidental deletion and regional failure.

It must also include restore testing.

A backup that has never been restored is evidence of an attempt to create a backup.

It is not yet strong evidence of recoverability.

### RPO and RTO

Two useful concepts from reliability engineering apply here.

The **Recovery Point Objective**, or RPO, describes the maximum acceptable data loss measured in time.

The **Recovery Time Objective**, or RTO, describes the target time for restoring service after disruption.

For temporary scanner scratch files, the requirements may be relaxed.

For customer account records or completed financial transactions, the requirements may be much stricter.

The storage architecture should follow the business guarantees.

It should not be selected merely because a particular StorageClass is the default.

## 18. Should Databases Run Inside Kubernetes?

We've learned how Kubernetes can provide persistent storage to Pods.

Does that mean every database should run inside the cluster?

No.

Kubernetes can run stateful systems effectively, but the operational responsibility is substantial.

A production database needs storage management, backups, replication, failover, upgrades, monitoring and disaster recovery.

Kubernetes provides useful building blocks.

A database operator can automate some application-specific operations.

But someone still has to understand and own the complete recovery design.

### Managed external databases

For many application teams, a managed database service is a strong choice.

The Kubernetes application connects over the network.

The database provider handles some portion of infrastructure provisioning, backup automation, maintenance and failover.

That doesn't eliminate application responsibilities.

The team must still design transactions, indexes, access control, query performance, connection management and recovery requirements.

But it can reduce the number of infrastructure systems the application team operates directly.

### Databases inside Kubernetes

Running a database inside Kubernetes can be reasonable when the organization has suitable expertise, automation and operational requirements.

It may provide consistent deployment infrastructure and integration with platform tooling.

But it also introduces dependencies on cluster control-plane health, CSI drivers, storage topology and workload scheduling.

A database operator can help coordinate upgrades and failover, but only if its behavior is understood and tested.

### The architectural principle

The question isn't whether Kubernetes is capable of running MongoDB.

It is.

The question is whether operating MongoDB inside Kubernetes improves the organization's overall reliability, cost and control compared with available alternatives.

There is no badge of engineering sophistication awarded for placing every stateful service inside the cluster.

Sometimes the most sophisticated architecture is the one that responsibly delegates an operational burden.

## 19. Designing the Scanner's State Boundaries

Let's return to the cybersecurity platform and make deliberate decisions.

### Application image

The scanner image contains the executable code and pinned dependencies.

It should be reproducible, tested and replaceable.

The image should not contain production credentials or mutable customer data.

### Ordinary configuration

The scanner's module settings, concurrency limits and service addresses can come from ConfigMaps or another appropriate configuration mechanism.

Configuration changes should follow a defined rollout or reload policy.

The team should be able to determine which configuration revision a running Pod has adopted.

### Credentials

Tokens and passwords should come from a controlled secret-management process.

Access should be limited to workloads that need them.

Rotation should be coordinated with the applications and external providers.

Credentials should not appear in logs, repositories or debug output.

### Scratch files

Intermediate scanner data can use `emptyDir` when it can be safely discarded or recomputed.

The worker should have explicit disk and memory budgets for temporary data.

A single huge scan should not be allowed to exhaust the node's local storage.

### Durable scan progress

The application should record important progress checkpoints in a durable system when the business requires resumability.

A replacement worker must be able to determine whether a scan should resume, restart or be reconciled.

This belongs to the application workflow and queue-processing design.

### Completed findings

Customer findings should be stored in the authoritative data system.

If that system is MongoDB, its own durability, replication and backup policies must be appropriate.

A scanner Pod's local files should not be the only copy of completed results.

### Large artifacts

Large scan artifacts that need independent retention may be better stored in object storage rather than on a dedicated disk attached to each worker.

The database can store metadata and references.

This can allow workers to remain replaceable while artifacts remain accessible across the fleet.

Object storage also has its own access-control, retention and consistency considerations.

The point is to give each data category a persistence mechanism matching its actual lifecycle.

## 20. Troubleshooting the Original Failure

Our worker was replaced after a node failure.

Now configuration is inconsistent, authentication fails, and unfinished work is missing.

How should we investigate?

### Step 1 — Identify what disappeared

Was it a temporary file?

An environment variable?

A mounted Secret?

A persistent filesystem?

A database record?

Do not assume that all missing information represents a storage failure.

First identify the owning mechanism.

### Step 2 — Inspect the effective Pod specification

Determine which ConfigMaps, Secrets and volumes the Pod references.

Check whether the required objects exist in the correct namespace.

Inspect relevant Pod events.

A missing required key can prevent container startup.

An invalid mount can block container creation.

A working container with stale environment values indicates a different problem.

### Step 3 — Separate configuration delivery from adoption

If a ConfigMap changed, determine how the application consumes it.

Environment variable?

Mounted file?

`subPath`?

Did the Pod restart?

Does the application reload the file dynamically?

A Kubernetes update can succeed while an application continues using old configuration.

### Step 4 — Investigate credential validity

Verify which credential version the application is actually using without exposing its value.

Check when the external provider issued or revoked the credential.

Look for failed authentication in sanitized application logs.

Determine whether the rotation sequence allowed old and new application instances to coexist safely.

### Step 5 — Inspect storage claims

If persistent data is missing or a volume cannot mount, inspect the PVC and PV.

Check binding state, StorageClass, access modes and topology constraints.

Review Pod events for provisioning, attachment and mount failures.

Then inspect the storage backend and relevant CSI components.

### Step 6 — Determine whether the data was ever durable

If a worker wrote a result only to `emptyDir`, it may have been lost with the Pod.

If the result was acknowledged to the queue before durable persistence, the system may have lost the opportunity to retry safely.

That is an application workflow issue.

If the result reached a database but later disappeared, investigate database durability, consistency and recovery separately.

### Step 7 — Reconstruct the intended failure behavior

A robust system should answer:

What happens if the worker dies before writing anything?

What happens after partial output?

What happens after writing findings but before acknowledging the queue message?

What happens if storage becomes unavailable?

What happens if credentials rotate halfway through an operation?

The design should have defensible answers before production failures force the team to invent them.

## 21. The Oral Examination

Answer these aloud before reading the solutions.

### Challenge 1 — The ConfigMap That Refuses to Update

A developer changes `MAX_CONCURRENT_SCANS` from 5 to 10 in a ConfigMap.

The Deployment references the value as an environment variable.

All existing Pods remain healthy, but the workers continue using 5.

Why?

### Challenge 2 — The Mounted File Mystery

A ConfigMap is mounted into a container.

The developer updates the ConfigMap and expects a running process to reload it.

What conditions must be satisfied for the new configuration to affect the application?

What changes if the file is mounted through `subPath`?

### Challenge 3 — The Secret That Wasn't Secret

A team commits a YAML file containing a production API key under a Secret's base64-encoded `data` field.

They argue that the key is safe because it isn't visible as plain text.

Explain the security failure.

### Challenge 4 — The Failed Credential Rotation

The team updates a Kubernetes Secret from token A to token B and immediately revokes A.

Half the Pods continue failing authentication.

What likely happened, and how should credential rotation be designed?

### Challenge 5 — The Lost Scanner Output

A worker writes intermediate scan results into an `emptyDir`.

The Pod is replaced on another node.

The files disappear.

Is Kubernetes malfunctioning? What architecture would preserve necessary progress?

### Challenge 6 — The Persistent Disk That Cannot Move

A database Pod runs in zone A with a zone-bound persistent volume.

The node fails.

Kubernetes attempts to run the replacement in zone B, but the volume cannot attach.

Why isn't persistence enough to guarantee recovery?

### Challenge 7 — ReadWriteOnce Isn't One Pod

Two Pods on the same node both attempt to mount an RWO volume.

A developer insists that RWO guarantees exclusive access by one Pod.

Is that correct? What access mode better expresses single-Pod exclusivity on supported CSI storage?

### Challenge 8 — The Successful Backup That Failed Recovery

A database uses persistent volumes and daily snapshots.

After a major failure, the team discovers that its snapshots cannot produce a usable recovery within the required time.

What did the architecture overlook?

## 22. Solutions and Discussion

### Solution 1 — Environment variables are established at container start

The existing worker processes already received their environment variables.

Changing the ConfigMap doesn't modify those running process environments.

The Pods need to be restarted or replaced so that the new value is injected.

A controlled Deployment rollout is a common approach.

### Solution 2 — Delivery and application adoption are separate

For ordinary ConfigMap volume projection, Kubernetes can eventually update mounted files.

But the application must reload them to change its behavior.

The change isn't necessarily instantaneous.

A `subPath` ConfigMap mount does not receive normal automatic updates.

For predictable configuration transitions, versioned configuration and controlled Pod replacement may be preferable.

### Solution 3 — Base64 provides no confidentiality

Base64 is reversible encoding.

Anyone with access to the committed manifest can decode the credential.

The key should be treated as compromised according to the organization's threat model, rotated or revoked, and removed from active distribution paths.

Secret management requires access controls, appropriate encryption and secure delivery.

### Solution 4 — Existing processes may still use token A

Pods consuming the Secret through environment variables don't automatically receive B.

Some applications using mounted files may also fail to reload the credential.

A safer rotation supports overlapping credentials when possible, distributes B, verifies adoption, and only then revokes A.

The precise procedure depends on the credential provider.

### Solution 5 — `emptyDir` belongs to the Pod lifetime

The volume was intended for temporary Pod data.

Deleting or replacing the Pod removes that data.

If progress must survive, the application should store durable checkpoints or results in an appropriate external system or persistent storage mechanism.

The queue-processing workflow must also support safe retries.

### Solution 6 — Storage has topology constraints

The persistent volume survives Pod replacement but may only be attachable within its permitted storage topology.

The replacement Pod must run on a compatible node, or the recovery system must provide a supported replication or restoration mechanism.

Storage location and scheduler placement are coupled.

### Solution 7 — RWO is node-oriented, not universal Pod exclusivity

ReadWriteOnce permits read-write mounting on one node.

It doesn't universally prohibit multiple Pods on that same node from accessing the volume.

ReadWriteOncePod better expresses single-Pod access for supported CSI storage.

Neither access mode replaces application-level consistency controls.

### Solution 8 — Snapshots aren't a complete recovery plan

The team may have overlooked application consistency, independent backup retention, restore procedures, failure-domain protection or recovery objectives.

It should define acceptable RPO and RTO, use suitable database-aware backup techniques where necessary, and regularly test restoration.

A snapshot existing is not equivalent to proving that useful service can be restored.

## 23. The Mental Model Worth Keeping

Kubernetes can restore execution without restoring meaning.

An image restores software.

A ConfigMap supplies ordinary configuration.

A Secret supplies sensitive data under an access-control and credential-lifecycle model.

An ephemeral volume supports temporary execution state.

A PersistentVolume provides storage beyond a Pod's lifetime.

An external data system may preserve durable business records independently of the application Pod.

But none of these mechanisms individually guarantees complete business recovery.

Whenever an application writes or consumes information, ask:

1. **Who owns it?** The process, Pod, Kubernetes API, storage backend or external system?
2. **How long must it survive?** A function call, container restart, Pod replacement, node failure or regional disaster?
3. **How is it delivered?** Environment, file mount, API, network connection or persistent disk?
4. **How does it change?** Reload, rollout, rotation, migration or restoration?
5. **What proves recovery works?** Not merely that a resource exists, but that the application can resume correctly.

These questions matter more than memorizing every Kubernetes volume type.

## 24. Next Lecture — SE450-L06: Security, Isolation, and Multi-Tenancy

Our workloads now have configuration, credentials and durable storage.

But who is allowed to access them?

A compromised scanner Pod may attempt to read Kubernetes Secrets, contact internal services, mount host resources or interfere with another tenant's workload.

A ServiceAccount may have more API permissions than necessary. A privileged container may escape assumptions about isolation. A developer may have permission to create Pods that indirectly expose credentials.

In the next lecture, we'll explore Kubernetes security through actual trust boundaries: RBAC, ServiceAccounts, Pod Security Standards, admission controls, network isolation and workload identity.

The central question becomes:

**What can a compromised workload do beyond the task it was supposed to perform?**

*The spoken lecture ends here. The remainder is for hands-on practice and screen-based revision.*

---

## Optional Practical Lab — Prove What Survives a Container Restart and a Pod Replacement

**Objective:** Observe ConfigMap propagation, environment-variable immutability, `emptyDir` persistence across container restart, and storage behavior across Pod replacement.

Use a disposable Kubernetes cluster such as Minikube or kind.

Do not use real credentials. Do not delete or modify existing production PVCs or PVs.

### Lab A — Verify the cluster

```bash
kubectl config current-context
kubectl get nodes
```

Create a dedicated namespace:

```bash
kubectl create namespace se450-l05
```

### Lab B — Create a ConfigMap

Create `config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: scanner-config
data:
  MESSAGE: "version-one"
```

Apply it:

```bash
kubectl apply -n se450-l05 -f config.yaml
```

### Lab C — Create a Pod consuming the ConfigMap in two ways

Create `pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-demo
spec:
  restartPolicy: Always
  containers:
    - name: worker
      image: busybox:1.36
      command:
        - sh
        - -c
        - |
          echo "Container started"
          while true; do sleep 30; done
      env:
        - name: MESSAGE_FROM_ENV
          valueFrom:
            configMapKeyRef:
              name: scanner-config
              key: MESSAGE
      volumeMounts:
        - name: config-files
          mountPath: /etc/scanner
          readOnly: true
        - name: scratch
          mountPath: /scratch
  volumes:
    - name: config-files
      configMap:
        name: scanner-config
    - name: scratch
      emptyDir: {}
```

Apply it:

```bash
kubectl apply -n se450-l05 -f pod.yaml
kubectl wait -n se450-l05 --for=condition=Ready pod/config-demo --timeout=120s
```

Inspect both configuration paths:

```bash
kubectl exec -n se450-l05 config-demo -- printenv MESSAGE_FROM_ENV

kubectl exec -n se450-l05 config-demo -- cat /etc/scanner/MESSAGE
```

Both should initially report `version-one`.

### Lab D — Change the ConfigMap

Update the ConfigMap:

```bash
kubectl patch configmap scanner-config -n se450-l05 \
  --type=merge \
  -p '{"data":{"MESSAGE":"version-two"}}'
```

Wait for the kubelet to propagate the change to the mounted file.

Then inspect the file again:

```bash
kubectl exec -n se450-l05 config-demo -- cat /etc/scanner/MESSAGE
```

It should eventually show `version-two`.

Now inspect the environment variable:

```bash
kubectl exec -n se450-l05 config-demo -- printenv MESSAGE_FROM_ENV
```

It should still report `version-one`.

**Question:** Why do the mounted file and environment variable disagree?

Remember that the update to the file is not guaranteed to be instantaneous.

### Lab E — Test `emptyDir` across a container restart

Write a temporary file into the Pod's `emptyDir`:

```bash
kubectl exec -n se450-l05 config-demo -- \
  sh -c 'echo "important scratch file" > /scratch/test.txt'
```

Verify it:

```bash
kubectl exec -n se450-l05 config-demo -- cat /scratch/test.txt
```

Now terminate the main process inside the container:

```bash
kubectl exec -n se450-l05 config-demo -- kill 1
```

The kubelet should restart the container according to the Pod's restart policy.

Wait for the container to become ready again:

```bash
kubectl wait -n se450-l05 --for=condition=Ready pod/config-demo --timeout=120s
```

Inspect the file:

```bash
kubectl exec -n se450-l05 config-demo -- cat /scratch/test.txt
```

The file should still exist because the Pod and its `emptyDir` volume survived the container restart.

Also check the environment variable after restart. It should now reflect the current ConfigMap value.

**Question:** Which parts of the execution environment were recreated, and which persisted?

### Lab F — Replace the Pod

Delete the Pod:

```bash
kubectl delete pod config-demo -n se450-l05
```

Then recreate it from the same manifest:

```bash
kubectl apply -n se450-l05 -f pod.yaml
kubectl wait -n se450-l05 --for=condition=Ready pod/config-demo --timeout=120s
```

Inspect the scratch directory:

```bash
kubectl exec -n se450-l05 config-demo -- ls -la /scratch
```

The previous scratch file should be gone.

The new Pod has a new `emptyDir` volume.

**Question:** Why did the file survive a container restart but not a Pod replacement?

### Lab G — Inspect cluster storage capabilities

Check whether your local cluster has a default StorageClass:

```bash
kubectl get storageclasses
```

Inspect available PVs and PVCs:

```bash
kubectl get pv
kubectl get pvc -A
```

Do not modify existing claims.

If your local cluster has a functioning default dynamic provisioner, create a disposable PVC using `claim.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 256Mi
```

Apply it:

```bash
kubectl apply -n se450-l05 -f claim.yaml
```

Inspect:

```bash
kubectl get pvc demo-data -n se450-l05
kubectl describe pvc demo-data -n se450-l05
```

The PVC may bind immediately or wait until a consumer Pod exists, depending on the StorageClass binding mode.

If the cluster lacks a working provisioner, stop this optional section here and inspect the PVC events rather than trying to install unfamiliar storage infrastructure.

### Lab H — Prove PVC persistence across Pod replacement

If your PVC is supported and can be provisioned, create `persistent-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: persistent-demo
spec:
  restartPolicy: Never
  containers:
    - name: worker
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: durable
          mountPath: /data
  volumes:
    - name: durable
      persistentVolumeClaim:
        claimName: demo-data
```

Apply and wait for readiness:

```bash
kubectl apply -n se450-l05 -f persistent-pod.yaml
kubectl wait -n se450-l05 --for=condition=Ready pod/persistent-demo --timeout=120s
```

Write a file:

```bash
kubectl exec -n se450-l05 persistent-demo -- \
  sh -c 'echo "persistent marker" > /data/marker.txt'
```

Delete only the Pod:

```bash
kubectl delete pod persistent-demo -n se450-l05
```

Recreate it:

```bash
kubectl apply -n se450-l05 -f persistent-pod.yaml
kubectl wait -n se450-l05 --for=condition=Ready pod/persistent-demo --timeout=120s
```

Read the file:

```bash
kubectl exec -n se450-l05 persistent-demo -- cat /data/marker.txt
```

It should still contain `persistent marker`.

This demonstrates persistence across Pod replacement through the same claim.

It does not prove that the storage would survive every node or cloud-provider failure.

### Lab I — Inspect the reclaim policy before cleanup

Check which PV backs the claim:

```bash
kubectl get pvc demo-data -n se450-l05 -o wide
```

Inspect the PV's reclaim policy:

```bash
kubectl get pv
```

Use `kubectl describe pv PV_NAME` to inspect the specific volume.

Do not delete or modify unrelated PVs.

Understand whether the provisioned volume uses Retain or Delete.

Only then proceed with cleanup of the disposable lab resources.

### Lab J — Cleanup

Verify the contents of the namespace:

```bash
kubectl get all,pvc,configmap -n se450-l05
```

If the resources belong exclusively to this exercise, delete the namespace:

```bash
kubectl delete namespace se450-l05
```

Depending on the PVC's reclaim policy and storage provisioner, deletion may also trigger deletion of the underlying storage resource.

This is precisely why reclaim policies deserve attention.

---

## Further Reading

1. [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/) — Configuration delivery and update semantics.
2. [Updating Configuration via a ConfigMap](https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/) — Environment variables, mounted files and immutability.
3. [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) — Sensitive data in Kubernetes.
4. [Good Practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/) — Access control, encryption and operational risks.
5. [Volumes](https://kubernetes.io/docs/concepts/storage/volumes/) — Volume types and mounts.
6. [Ephemeral Volumes](https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/) — Storage tied to Pod lifetimes.
7. [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) — PVs, PVCs, binding, access modes and reclaim policies.
8. [Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/) — Dynamic provisioning and topology-aware binding.
9. [Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/) — Snapshot resources and driver requirements.
10. [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) — Storage identity and claim retention.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is deliberately fenced for quick screen-based revision.*

```text
SE450-L05 — CONFIGURATION, SECRETS, AND PERSISTENT STATE

FIVE INFORMATION CATEGORIES

Image:
  Executable software, packaged dependencies
  Replaceable

ConfigMap:
  Non-confidential environment configuration
  Separate from image

Secret:
  Sensitive tokens, passwords, keys
  Requires real security controls

Ephemeral volume:
  Temporary Pod execution data
  Disposable

Persistent / external state:
  Business records, important artifacts, database data
  Requires durability and recovery design

CONFIGMAP

  Namespaced API resource
  data = UTF-8 string values
  binaryData = binary content
  NOT for credentials

  env injection:
    Value fixed for running process
    Pod/container restart required to adopt update

  mounted volume:
    Projected files can update eventually
    Application must reload

  subPath:
    ConfigMap mount does NOT receive normal updates

  immutable: true
    Data cannot change in place
    Create new version/name for new configuration

SECRET

  Sensitive Kubernetes API resource
  data uses base64 encoding
  base64 != encryption

  Protect through:
    etcd encryption at rest
    RBAC least privilege
    workload-admission permissions
    appropriate secret distribution
    rotation procedures
    logging discipline

  Secret env:
    Convenient, but existing process does not update automatically

  Secret volume:
    File-based consumption
    Can support eventual refresh
    Application must adopt new value

  ServiceAccount tokens:
    Prefer short-lived projected tokens
    Avoid unnecessary API credentials in Pods

ROTATION

  Issue new credential
  Distribute
  Verify adoption
  Revoke old credential
  Handle non-overlapping provider limitations

  Changing Secret != complete credential rotation

VOLUME TYPES

  Container writable layer:
    Disposable container execution state

  emptyDir:
    Pod-lifetime scratch storage
    Survives container restarts within same Pod
    Deleted when Pod disappears

  emptyDir medium Memory:
    Memory-backed temporary storage
    Counts toward memory consumption

  hostPath:
    Node-local filesystem path
    Node affinity and security risks
    Usually wrong for application persistence

  configMap / secret / downwardAPI:
    Projected API/configuration data

  PVC-backed:
    Storage lifecycle separate from individual Pod

PERSISTENT STORAGE CHAIN

  Pod
    -> PVC
    -> PV
    -> StorageClass / provisioner
    -> CSI / storage backend

PVC
  Namespaced request for storage
  Capacity, access mode, class

PV
  Cluster storage resource
  Can be statically or dynamically provisioned

StorageClass
  Provisioning characteristics
  Reclaim policy
  Volume binding mode
  Backend parameters

CSI
  Storage integration interface
  Provision, attach, stage, mount, expand, etc.
  Actual capabilities depend on driver

ACCESS MODES

  RWO:
    Read-write by one node
    NOT necessarily exclusive to one Pod

  ROX:
    Read-only access from multiple nodes

  RWX:
    Read-write access from multiple nodes

  RWOP:
    Single-Pod read-write access
    Supported CSI storage required

BINDING

  Immediate:
    Provision/bind before considering consumer Pod placement

  WaitForFirstConsumer:
    Coordinate binding/provisioning with Pod scheduling
    Useful for topology-constrained volumes

STORAGE TOPOLOGY

  Persistent != accessible from every node
  Cloud block disks may be zone-bound
  CPU/memory fit != volume attachment possible

STATEFULSET

  Stable member names / ordinals
  volumeClaimTemplates associate storage with members
  Default claim retention normally preserves PVCs
  Retention policies can alter deletion behavior

  NOT automatic database consensus, durability or failover

RECLAIM

  Retain:
    Preserve underlying volume for manual reclamation

  Delete:
    Delete PV/backing storage on claim release via provisioner

  Always inspect policy before deleting important PVCs

PERSISTENCE VS BACKUP

  Persistence:
    Data survives ordinary process/Pod replacement

  Backup:
    Independent recoverable previous copy

  Snapshot:
    Point-in-time storage capture
    Not always application-consistent

  RPO:
    Maximum acceptable data loss

  RTO:
    Target restoration time

  Verify restoration, not merely backup creation

TROUBLESHOOTING

  Missing env:
    ConfigMap/Secret key, namespace, references

  Stale config:
    env vs volume, subPath, app reload, rollout

  Authentication failure:
    Credential version, rotation, revocation, app adoption

  Missing scratch:
    Pod replaced, emptyDir deleted

  PVC Pending:
    StorageClass, provisioner, binding, capacity, topology

  Mount failure:
    CSI, attachment, node/zone, permissions, backend

  Data corrupted:
    Application/database recovery, not just disk attachment

  Unexpected data deletion:
    PVC lifecycle and PV reclaim policy

FIVE SENIOR QUESTIONS

  1. Who owns the information?
  2. What failure must it survive?
  3. How does the application receive it?
  4. How is it updated or rotated?
  5. What proves recovery actually works?

SENIOR LINE

  "Kubernetes can replace execution, but application state
   follows independent lifecycles. I separate code, configuration,
   credentials, scratch data and durable business records,
   then design their delivery, persistence, rotation and recovery
   according to their actual requirements."
``` 
