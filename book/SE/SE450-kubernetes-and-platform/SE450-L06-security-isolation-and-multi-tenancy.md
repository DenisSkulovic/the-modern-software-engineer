---
id: SE450-L06
course: SE450
title: "Security, Isolation, and Multi-Tenancy"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L05
next: SE450-L07
---


# SE450 — Kubernetes and Platform Engineering

## Lecture 06: Security, Isolation, and Multi-Tenancy

*A scanner is supposed to investigate suspicious websites. One of those websites exploits the scanner instead. The attacker now controls a process inside your Kubernetes cluster. How much of your infrastructure does that actually give them?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity company operating a platform that investigates customers' internet-facing assets.

Customers submit domains. Scanner workers visit those domains, discover technologies, inspect exposed services, and collect evidence.

Some workers execute complex tools. Others interact with unknown HTTP servers. Still others process files and metadata supplied by untrusted systems.

This is inherently risky work.

Unlike a normal backend service that communicates with a small group of trusted dependencies, a scanner deliberately interacts with systems it doesn't control.

One afternoon, a scanner processes a maliciously crafted response from an external server. A vulnerability in one of its parsing dependencies allows the attacker to execute code inside the scanner container.

The attacker now controls the application process.

What happens next?

The reassuring answer would be: nothing much. The attacker is trapped inside one disposable container.

But that answer is not necessarily correct.

The scanner may have network access to internal APIs. It may possess credentials. Its Pod may have a Kubernetes ServiceAccount token. Its container may run with unnecessary Linux privileges.

And the node hosting it may also run workloads belonging to other customers.

The real question is no longer whether the scanner has been compromised. For our scenario, it has.

The question is **what authority that compromised process possesses and which boundaries constrain it**.

## 1. The building with several different locks

Imagine a large office building.

The first lock controls entry to the building.

A second lock controls which floors a person can access.

A third controls which rooms on a floor they can enter.

And a fourth determines whether they can open the filing cabinets inside those rooms.

These locks protect different things.

A visitor might be allowed into the lobby but not the executive offices.

An employee might enter the finance floor but lack permission to open the payroll database.

A maintenance technician might access the server room but not be authorized to read customer records.

Kubernetes has a similarly layered security model.

Container isolation helps restrict what a process can do to its host environment.

Kubernetes RBAC controls permitted API operations.

NetworkPolicy can restrict which network destinations a Pod may reach.

Secrets and workload identities determine which credentials the process can use.

Application authorization controls which business records it can access.

None of those protections automatically implies the others.

**Being inside a container doesn't mean the process has no network access. Being inside a namespace doesn't mean it cannot reach another namespace. Having an identity doesn't mean that identity has been granted appropriate permissions.**

The entire architecture must be considered.

## 2. A namespace is not a security force field

Suppose our scanner runs in a namespace named `scanners`.

MongoDB and several internal APIs run in a namespace named `platform`.

The developer says, "They're in separate namespaces, so they're isolated."

Not necessarily.

A Kubernetes namespace organizes API resources and provides a scope for permissions and policies.

It does not automatically establish a network firewall between Pods.

Under the basic Kubernetes networking model, Pods in different namespaces may communicate unless network policies or other controls restrict them.

Likewise, namespaces don't create separate Linux kernels.

Two Pods in different namespaces may run on the same physical or virtual node.

So namespaces are useful administrative and policy boundaries, but they are not complete security isolation.

For our compromised scanner, the question is whether its effective network permissions allow it to contact the internal MongoDB service.

The namespace names alone don't answer that.

## 3. The invisible badge inside the Pod

Now consider identity.

Our scanner may need to communicate with the Kubernetes API to inspect Job objects or report execution status.

Kubernetes supports ServiceAccounts for workload identity.

A Pod can run under a particular ServiceAccount, and a credential can be projected into the Pod to authenticate as that identity.

This is like giving the process an employee badge.

But the badge isn't the permission system itself.

Kubernetes RBAC determines which API operations that identity may perform.

One ServiceAccount might be allowed to read selected Jobs in its namespace.

Another might be able to create new Jobs.

A highly privileged controller might be authorized to manage resources across the cluster.

If the compromised scanner's ServiceAccount has broad permissions, the attacker may inherit those permissions.

The software vulnerability compromised the process.

The excessive permissions determine how far the compromise can spread.

### A particularly important distinction

A ServiceAccount identifies the workload to Kubernetes.

It doesn't automatically identify the customer whose scan is being processed.

Our scanner might serve hundreds of customers under the same ServiceAccount.

The application must still enforce customer-specific access to business data.

Otherwise, one compromised worker can abuse its legitimate backend credentials to access customer information outside the current scan.

**Infrastructure identity and application tenant identity are separate security questions.**

## 4. The scanner should not carry the keys to the kingdom

Suppose the scanner's legitimate job is simple:

Receive a scanning task, contact authorized targets, write results through an internal API, and acknowledge completed work.

Does it need permission to read every Kubernetes Secret?

No.

Does it need permission to create arbitrary privileged Pods?

No.

Does it need access to the host filesystem?

Usually not.

Does it need cluster-administrator permissions?

Absolutely not.

Yet these permissions can accumulate during development.

A tool fails with "Forbidden." A developer temporarily grants more access. The new configuration works. Nobody revisits the decision.

Over time, a small worker may receive authority far beyond its responsibilities.

This is why least privilege is not merely a security slogan.

It is a way of limiting the consequences of inevitable software failures.

If the scanner has no Kubernetes API permissions, compromising it does not automatically give the attacker administrative control of the cluster.

If its network policy permits only necessary destinations, lateral movement becomes harder.

If its credentials are scoped to a narrow operation, stolen credentials have less value.

The goal is not to pretend compromise is impossible.

It's to make compromise **local, bounded, detectable, and recoverable**.

## 5. One compromised Pod, several possible paths

Picture the attacker's options.

```text
                 COMPROMISED SCANNER
                         |
          +--------------+--------------+
          |              |              |
       Kubernetes      Network       Credentials
       API access      access          access
          |              |              |
       RBAC rules     NetworkPolicy   Secret scope
          |              |              |
       Other API      Internal       External APIs /
       resources      services       cloud resources
          |
     Pod privileges
          |
      Host / node
```

This is an attack-surface map, not a claim that every path is available.

Each branch requires some additional capability or misconfiguration.

A properly constrained scanner may have almost no useful Kubernetes API authority.

A poorly constrained scanner might be able to modify other workloads, read sensitive resources, or use broad cloud credentials.

The difference lies in the system's security design.

### Your mental checkpoint

Before the Deep Dive, answer these questions aloud.

1. Why doesn't placing scanner Pods in a separate namespace automatically block them from contacting internal databases?
2. What is the difference between a ServiceAccount and an RBAC permission?
3. Why can a compromised process be dangerous even without a container escape?
4. What would make the same scanner vulnerability less damaging in one cluster than in another?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Scanner That Became a Cluster Administrator

Our platform has six scanner workers in the `scanners` namespace.

Each runs a Python application that receives tasks from RabbitMQ, launches specialized scanning modules, and stores results through internal services.

During early development, the team created a ServiceAccount called `scanner-worker`.

Some scanning modules needed to inspect Kubernetes Job status. Others created short-lived Jobs for isolated investigations.

The team granted the ServiceAccount broad API permissions because it was easier than identifying exactly which operations were required.

The application worked.

Months later, a vulnerability in a scanner dependency allows an attacker to execute code inside a worker container.

During the subsequent incident investigation, the security team discovers that the worker's ServiceAccount can create Pods and read Secrets in a namespace containing sensitive credentials.

The attacker did not need to escape the container to cross that boundary.

The container already held credentials for a Kubernetes identity with excessive authority.

This illustrates an uncomfortable fact about infrastructure security:

**An attacker who controls a legitimate workload can use the workload's legitimate permissions.**

Authentication can succeed. RBAC can authorize the operation. The API server can behave exactly as designed.

The security failure lies in giving that workload authority it never needed.

Let's trace the boundaries.

## 2. Start With the Threat Model

Before choosing security controls, identify what needs protection and who might attack it.

Our scanner processes potentially hostile internet content. An attacker may control a website, HTTP response, downloadable artifact, protocol banner, or other input the scanner encounters.

We assume an exploitable vulnerability gives the attacker code execution with the privileges of the scanner process.

This is our initial foothold.

The assets at risk include customer scan data, internal credentials, the message broker, internal APIs, Kubernetes resources, cloud infrastructure, and neighboring workloads.

The attacker's possible objectives include stealing data, modifying findings, disrupting scans, consuming resources, or moving into more privileged systems.

We should distinguish three different kinds of compromise.

**Application compromise:** the attacker controls the scanner process and can act using its application privileges.

**Kubernetes control-plane compromise:** the attacker gains unauthorized authority over Kubernetes API resources or infrastructure management.

**Node compromise:** the attacker gains control over the underlying operating-system environment or another privileged host component.

These are not equivalent outcomes.

A compromised application is serious, but it doesn't automatically imply that the attacker has acquired control over the node or control plane.

The security architecture should make crossing those additional boundaries difficult.

## 3. Kubernetes Authentication, Authorization, and Admission

Consider what happens when a client makes a request to the Kubernetes API.

For example, a workload attempts to read a ConfigMap.

The API server processes the request through several distinct security stages.

### Authentication: who is making the request?

The API server determines the client's identity.

That identity might originate from a human user's authentication configuration, a ServiceAccount token, a client certificate, or another supported mechanism.

If the caller presents a valid ServiceAccount token, the API server can recognize it as a particular ServiceAccount in a particular namespace.

Authentication establishes identity.

It does not imply that the requested operation is permitted.

### Authorization: may this identity perform the operation?

After authentication, Kubernetes evaluates whether the identity is authorized to perform the requested action.

RBAC is a common authorization mechanism.

For example, a Role might permit the `get` operation on ConfigMaps within a namespace.

If the caller lacks the required authorization, the API server rejects the request.

But even an authorized request may be subject to additional checks.

### Admission: is this requested resource change acceptable?

Admission controls can validate or mutate eligible API requests.

A policy might reject a Pod that requests privileged execution.

Another might require approved resource constraints or labels.

Some admission mechanisms can modify a resource before it is persisted.

Admission is not a replacement for authorization.

It is an additional policy layer applied to supported API operations.

### Persistence and reconciliation

If the request passes the relevant stages, the API server can persist the resource change.

Controllers may then observe it and act.

The complete conceptual sequence is:

```text
          API REQUEST
               |
               v
         Authentication
          Who are you?
               |
               v
          Authorization
        May you do this?
               |
               v
       Admission controls
       Is this acceptable?
               |
               v
          API persistence
               |
               v
       Controller / runtime
          consequences
```

The stages are conceptually separate, even though the API server's implementation has more detailed ordering and processing behavior.

This distinction is extremely useful during incident analysis.

An unauthorized request may fail at RBAC.

An authorized Pod creation may fail at admission because of security policy.

An accepted Pod may still fail to start because of scheduling or runtime conditions.

## 4. ServiceAccounts: Workload Identity Is Not Permission

Every Kubernetes namespace ordinarily has a `default` ServiceAccount.

If a Pod doesn't specify another ServiceAccount, Kubernetes generally associates it with the namespace's default one.

The default ServiceAccount does not ordinarily receive powerful API permissions automatically in a properly configured RBAC cluster.

However, its token may still be mounted into Pods by default, even when the application has no reason to communicate with the Kubernetes API.

This increases unnecessary credential exposure.

### Bound and projected tokens

Modern Kubernetes commonly uses short-lived, projected ServiceAccount tokens.

These tokens can be associated with the lifetime of a Pod and have defined audiences.

The kubelet can refresh them before expiration.

This is preferable to relying on indefinitely valid legacy tokens.

But a short-lived token isn't harmless.

If an attacker controls the Pod and can access its projected credentials, they may be able to use those credentials while valid.

And a token's impact depends on what its identity is authorized to do.

### Disable unnecessary token mounting

If our scanner doesn't need the Kubernetes API, its Pod can specify:

`automountServiceAccountToken: false`

This prevents ordinary automatic mounting of that ServiceAccount credential.

The Pod can still be associated with its ServiceAccount as an identity.

But the application no longer receives an unnecessary API token through the normal automount mechanism.

This is a straightforward reduction in attack surface.

It doesn't remove credentials explicitly delivered through other mechanisms, and it doesn't restrict the application's network access or external cloud identity.

Those require separate controls.

### Dedicated identities

Instead of making unrelated workloads share one ServiceAccount, create dedicated identities for distinct functions.

Our ordinary scanner workers might use `scanner-runtime`.

A controller that creates short-lived scan Jobs might use `scan-job-controller`.

A reporting service might use `report-reader`.

The controller can receive the specific API permissions required to manage Jobs.

The ordinary scanner can remain without Kubernetes API authority.

This is significantly safer than handing every worker a single highly privileged identity.

## 5. RBAC: What an Identity Can Actually Do

Kubernetes RBAC expresses permissions through Roles, ClusterRoles, RoleBindings, and ClusterRoleBindings.

These names describe two separate dimensions: the scope of permissions and the mechanism that binds them to identities.

### Role

A Role contains permission rules intended for a particular namespace.

It can authorize actions such as reading selected ConfigMaps or managing Jobs in that namespace.

### ClusterRole

A ClusterRole defines rules that can apply to cluster-scoped resources or be reused for namespaced resources.

It is not automatically equivalent to cluster-administrator privileges.

A ClusterRole might define a narrow read-only permission that is bound within just one namespace.

### RoleBinding

A RoleBinding grants permissions from a Role or ClusterRole to specified subjects within the RoleBinding's namespace.

It doesn't generally turn the referenced permissions into global authority.

### ClusterRoleBinding

A ClusterRoleBinding grants permissions defined by a ClusterRole at cluster scope, including across applicable namespaces.

That broader scope can be dangerous when applied to application workloads without justification.

### A narrow example

Suppose a reporting component needs to read ConfigMaps in its own namespace.

A suitable Role could grant only `get` on ConfigMaps, possibly restricted to known resource names.

A RoleBinding could associate that Role with the reporting ServiceAccount.

The component would not automatically receive permission to list Secrets, create Pods, or delete Deployments.

For the scanner's limited operational role, that's exactly the kind of precision we want.

### Why verbs matter

Kubernetes RBAC permissions are defined by API groups, resources and verbs, optionally with further restrictions.

Common verbs include `get`, `list`, `watch`, `create`, `update`, `patch`, and `delete`.

These operations have different security implications.

Granting permission to read one named resource is different from permitting a caller to list every resource of that type in the namespace.

For Secrets, broad `list` and `watch` permissions are particularly sensitive because they can expose Secret data.

When reviewing permissions, don't treat every read operation as harmless merely because it cannot modify infrastructure.

## 6. The Surprising Privilege of Creating Pods

Now we reach one of the most important Kubernetes-specific security traps.

Suppose the scanner ServiceAccount cannot directly read a particular Secret through the Kubernetes API.

A developer concludes that the Secret is protected.

But the scanner ServiceAccount can create arbitrary Pods in the namespace containing that Secret.

Why might that still be dangerous?

Because a Pod can reference a Secret from its own namespace and consume it through a mounted volume or environment variable.

Kubernetes' standard Secret consumption model doesn't require the Pod's ServiceAccount to possess direct Secret `get` permission merely to reference an existing Secret.

Consequently, an identity authorized to create arbitrary Pods in a namespace can potentially arrange for a workload to consume Secrets available in that namespace.

This is an indirect privilege.

Similarly, permission to create Pods may allow a caller to choose powerful ServiceAccounts already present in that namespace.

The newly created Pod can then run using the selected ServiceAccount's credentials.

Depending on the cluster's admission controls and other restrictions, the effective authority of Pod creation may therefore exceed the obvious meaning of the `create pods` permission.

### Why this changes RBAC design

A security reviewer cannot simply inspect whether a workload has permission to read Secrets.

They must examine whether that workload can create or modify other resources that themselves consume sensitive data or identities.

This includes permissions over Pods and workload controllers such as Deployments or Jobs.

An identity capable of changing a Deployment's Pod template may be able to affect the process and credentials used by that Deployment.

The impact depends on namespace boundaries, policies, available identities, and admission restrictions.

**Authorization must be evaluated through the capabilities it enables, not merely through the names of the API verbs.**

### Dedicated namespaces reduce this risk

Suppose the controller responsible for creating scanner Jobs operates in a namespace containing no powerful unrelated credentials.

Even if its permission to create Pods is misused, the available resources and identities are more limited.

Compare that with a controller operating in a namespace that also contains cloud-administrator credentials and highly privileged ServiceAccounts.

The second design creates a much larger potential blast radius.

This is why namespace organization and RBAC design must be considered together.

## 7. Namespaces: Useful Boundaries, Not Complete Isolation

Namespaces provide a powerful organizational and security-policy scope.

Different namespaces can use different Roles, RoleBindings, NetworkPolicies, resource quotas and Pod Security Admission settings.

But namespaces don't automatically isolate every resource or execution pathway.

### Control-plane separation

An application identity can be restricted to resources in its own namespace.

This helps prevent one team from modifying another team's resources.

However, cluster-scoped resources such as Nodes, PersistentVolumes, ClusterRoles, and CustomResourceDefinitions don't belong to an ordinary namespace.

Overly broad cluster-level permissions can undermine namespaced separation.

### Network separation

Pods in distinct namespaces can often communicate over the Pod network unless policies restrict the path.

The DNS system may resolve Services across namespaces.

So separate namespace names do not imply separate networking environments.

### Node separation

Pods from multiple namespaces may run on the same node.

They share an underlying kernel and host infrastructure, subject to container isolation mechanisms.

A compromised application does not automatically control the kernel, but sharing the node creates a security boundary that must be evaluated.

### Storage separation

PVCs are namespaced, while PersistentVolumes are cluster-scoped objects.

Storage access, provisioning, reclaim behavior and backend authorization need their own protections.

Namespace membership alone doesn't establish every storage security property.

### A practical decision

For trusted internal engineering teams, namespaces combined with suitable policies can provide an efficient shared-cluster architecture.

For mutually distrustful customers running arbitrary code, the threat model may justify dedicated node pools, sandboxed runtimes, virtualized control planes or entirely separate clusters.

The right choice depends on the required strength of isolation, not on a belief that all namespaces are equally secure.

## 8. Container Isolation: A Process Is Not a Virtual Machine

Our scanner process runs inside a Linux container.

Containers rely on operating-system isolation mechanisms such as namespaces, cgroups, capabilities, seccomp and other kernel security controls.

The container sees a restricted environment, but it generally shares the host's Linux kernel.

A container is not inherently a separate virtual machine with its own independent kernel.

This means the security properties of the underlying node matter.

### Root inside a container

A process may run as user ID zero inside its container.

That does not automatically mean it has unrestricted authority over the host.

Namespaces and capability restrictions can constrain it.

However, running as root increases risk when combined with other misconfigurations or vulnerabilities.

It can also make certain filesystem or privilege-related attacks easier.

For application workloads that don't require root privileges, running as a non-root user is a sensible defense.

### Linux capabilities

Linux capabilities divide some traditionally root-associated powers into more specific privileges.

For example, different capabilities govern particular network, process or system operations.

A container should generally retain only the capabilities it requires.

The `NET_ADMIN` capability, for example, can enable powerful network-configuration operations within the relevant namespace.

Whether such a capability creates broader danger depends on the surrounding configuration and isolation model.

For our scanner, we should determine whether each scanning module genuinely requires unusual capabilities.

A DNS resolver or HTTP technology detector usually doesn't need the same privileges as a low-level packet inspection tool.

### Privileged containers

A container configured with `privileged: true` receives broad privileges and substantially weakens normal container isolation.

This can be necessary for certain trusted infrastructure components, but it's generally inappropriate for arbitrary application workloads.

A compromised privileged scanner can present a much larger risk than a compromised, tightly constrained unprivileged scanner.

### Host namespaces and mounts

Using `hostNetwork`, `hostPID`, or broad host filesystem mounts can expose additional node-level capabilities or information.

A `hostPath` mount may reveal files belonging to the host, depending on the mounted path and permissions.

In a multitenant environment, these settings deserve particularly strong scrutiny.

The default engineering posture should be to avoid them unless a concrete requirement justifies them.

## 9. Hardening the Scanner's Security Context

Kubernetes provides `securityContext` fields at Pod and container levels.

These settings describe important aspects of process identity and operating-system privilege.

For an ordinary scanner component that doesn't require root or special capabilities, a hardened configuration might include:

- Run as a non-root user.
- Prevent privilege escalation.
- Drop unnecessary Linux capabilities.
- Use the runtime's default seccomp profile.
- Make the root filesystem read-only where compatible.
- Mount explicit writable volumes only where needed.

A compact example:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: scanner
      image: registry.example.com/scanner@sha256:EXAMPLE_DIGEST
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
      volumeMounts:
        - name: scratch
          mountPath: /tmp
  volumes:
    - name: scratch
      emptyDir: {}
```

The image digest shown here is illustrative and must be replaced with a real digest before deployment.

The example expresses a relatively constrained execution environment. It doesn't claim that every scanning tool can run under these settings without modification.

### The practical difficulty

Some security tools genuinely need unusual capabilities or filesystem behavior.

For instance, a tool performing raw-packet operations may require capabilities not needed by a simple HTTP scanner.

The wrong response is to grant the entire scanner platform privileged execution.

A better architecture separates capability classes.

Most scanning modules can run in ordinary restricted workers.

Specialized modules requiring elevated privileges can execute through a narrower, more carefully controlled system.

Those jobs might run on dedicated nodes, under tightly scoped identities, with specific runtime settings and additional monitoring.

The architecture then limits exposure to elevated privileges instead of making them the default for every scan.

## 10. Pod Security Standards and Admission

Manually reviewing every workload manifest is not enough.

Applications evolve. Teams change. Dependencies introduce new requirements. A developer may accidentally add `privileged: true` or enable host networking.

Kubernetes provides Pod Security Standards to define broad security profiles.

The three profiles are **Privileged**, **Baseline**, and **Restricted**.

### Privileged

This profile is intentionally permissive.

It is generally appropriate only where elevated infrastructure capabilities are explicitly required and separately controlled.

### Baseline

Baseline prevents several known dangerous configurations while preserving compatibility with many ordinary applications.

It is useful as a minimum security standard for many shared environments.

### Restricted

Restricted applies stronger hardening requirements.

It includes rules concerning non-root execution, privilege escalation, seccomp, Linux capabilities, and permitted volume types, among other restrictions.

Not every existing workload can satisfy Restricted without adjustment.

But it provides a valuable target for ordinary application workloads.

### Pod Security Admission

Pod Security Admission can enforce these profiles through namespace labels.

It supports three modes:

**Enforce:** reject Pod configurations that violate the selected standard.

**Audit:** record policy violations in audit information.

**Warn:** report violations to the API client without necessarily rejecting the resource.

A namespace may use different profiles for these modes.

For example, a team can enforce Baseline while warning and auditing against Restricted.

That allows gradual improvement without immediately breaking every workload.

### What admission does not do

Pod Security Admission doesn't automatically establish network isolation, protect application database rows, or verify that a container image is free from vulnerabilities.

Nor is it a universal replacement for carefully designed RBAC.

Admission controls the acceptance of certain API resource configurations.

Runtime security and application authorization remain independent concerns.

## 11. Policy as Code: Preventing Bad Infrastructure Before It Runs

Pod Security Admission covers a useful standardized baseline.

But organizations often need additional policies.

For example:

Every production Deployment must use an approved container registry.

Every Pod must declare a responsible team.

Workloads in a particular namespace must specify resource requests.

Privileged execution must be restricted to approved platform components.

Kubernetes supports admission mechanisms that can validate resource changes against such requirements.

### ValidatingAdmissionPolicy

Modern Kubernetes provides ValidatingAdmissionPolicy, which can express validation rules using the Common Expression Language, or CEL.

A policy defines validation logic, and a binding determines where and how that policy applies.

This can enforce useful constraints without requiring a custom external webhook for every rule.

### Admission webhooks

Organizations can also deploy validating and mutating admission webhooks.

A validating webhook can reject an unacceptable resource.

A mutating webhook can alter eligible resource definitions, for example by injecting standardized configuration.

But these systems become part of the control-plane request path.

A failing admission webhook can block deployments or introduce unexpected behavior, depending on its failure policy.

Security policy therefore has an operational availability cost.

The platform team needs to decide when a policy failure should reject changes and when a more permissive failure mode is acceptable.

### Prevention versus visibility

A useful policy rollout often begins in a visibility-oriented mode.

The organization discovers which workloads violate the proposed requirement.

It repairs legitimate exceptions.

Then it enables enforcement where appropriate.

Blindly enabling the strictest policy across an existing production cluster can break essential infrastructure.

Security controls must be introduced with the same rollout discipline as other production changes.

## 12. NetworkPolicy: Containing Lateral Movement

Suppose our scanner is compromised.

It needs internet access to inspect external hosts.

But does it need network access to the internal billing API?

No.

Does it need direct access to every database?

No.

Does it need to connect to Kubernetes control-plane endpoints?

Only if its legitimate responsibilities require that access.

The networking architecture should reflect these distinctions.

### The default-connectivity problem

Kubernetes' basic Pod networking model allows broad connectivity unless additional controls restrict it.

A scanner in one namespace may be able to connect to Services in another namespace.

A compromised process can attempt to use that network position.

NetworkPolicy can restrict allowed Pod traffic at supported network layers.

A sensible design might permit scanner workers to communicate with RabbitMQ and a specific result-ingestion API while restricting unnecessary access to internal services.

### The scanner exception

A normal business API may have a small set of known outbound dependencies.

A scanning worker deliberately contacts many external destinations.

That makes its egress requirements unusual.

A simplistic policy allowing only a few static IP addresses may prevent it from performing its legitimate job.

The architecture may need to separate internal control traffic from arbitrary target scanning.

For example, scanner workers might run in a dedicated network environment with controlled external egress, while their access to sensitive internal services remains narrow.

The correct solution depends on the scanner's functionality and organizational risk tolerance.

### NetworkPolicy limitations

Standard NetworkPolicy primarily governs IP- and port-level connectivity.

It is not an HTTP authorization engine.

And it only provides protection when the cluster networking implementation actually enforces the policies.

A NetworkPolicy YAML resource accepted by the API is not proof of effective network isolation.

As in SE450-L03, verify actual behavior.

### Don't confuse reachability with authority

Suppose a scanner can connect to the billing API's TCP port.

That does not mean the billing API should authorize the scanner to perform arbitrary financial operations.

The API must still authenticate callers and enforce business permissions.

Network isolation narrows attack paths.

Application authorization protects the operations behind those paths.

Both matter.

## 13. Cloud Workload Identity: The Cluster Is Not the Final Boundary

Many Kubernetes applications use cloud-provider services.

Our scanner may need access to object storage, cloud queues, or security-related APIs.

A naive solution is to place a long-lived cloud access key inside a Kubernetes Secret and mount it into every worker.

That creates a valuable credential for attackers.

If the process is compromised, the credential may be stolen.

### Federated workload identity

Cloud platforms offer mechanisms that associate Kubernetes workloads with cloud identities.

The exact implementation differs among providers.

A Kubernetes ServiceAccount identity may participate in an OIDC-based federation or a provider-specific workload identity mechanism.

The application can then obtain appropriately scoped cloud credentials without embedding a permanent access key in its image.

This is useful, but it introduces another security boundary.

Kubernetes RBAC controls Kubernetes API permissions.

Cloud IAM controls cloud-resource permissions.

A workload may have no Kubernetes API permissions while still holding powerful cloud authority.

For example, it may be allowed to access an object-storage bucket.

A compromised process could attempt operations permitted by that cloud identity.

### The permissions must be scoped on both sides

The workload identity association should be narrow.

The cloud role should grant only the required actions on appropriate resources.

Trust policies should restrict which Kubernetes identities may assume the role.

And the organization should avoid allowing unrelated workloads to impersonate the authorized identity through overly broad deployment permissions.

An identity federation system does not automatically solve least privilege.

It provides better credential mechanics when configured correctly.

## 14. Software Supply Chain: Trusted Deployment of Untrusted Dependencies

Our scanner contains many third-party tools.

Some are installed through package managers.

Others come from container images or downloaded binaries.

The application may be carefully hardened at runtime while still containing a compromised dependency.

This creates a different attack path.

Instead of exploiting the scanner through a malicious website, an attacker compromises the software artifact before deployment.

### Image tags versus digests

A container image tag is a human-readable reference.

Tags can be changed in registries, depending on registry settings and permissions.

An image digest identifies particular image content.

Pinning an image by digest makes the selected artifact more reproducible.

But a digest doesn't prove that the artifact is safe.

It only helps establish which artifact is being used.

### Image provenance

Production systems benefit from knowing where images came from, how they were built, and which changes were included.

Useful controls include build-system isolation, image scanning, dependency review, software bills of materials, and signature or provenance verification.

Some organizations use admission policies to restrict deployment to approved or verified images.

The exact verification mechanism depends on the chosen tooling and trust infrastructure.

### The CI/CD identity problem

A build pipeline may have permission to publish images and update Kubernetes workloads.

If that pipeline is compromised, an attacker may be able to deploy malicious software without exploiting the running application.

The pipeline is part of the trusted system.

Its credentials should be scoped and protected accordingly.

A separate deployment identity with limited namespace permissions is often preferable to unrestricted cluster-administrator credentials in CI.

### Avoid the false conclusion

A signed image can still contain vulnerable code.

A scanned image can still contain undiscovered vulnerabilities.

A reproducible image can still be malicious if the source or build environment is compromised.

Supply-chain security provides evidence and controls over artifact origin and construction.

It doesn't eliminate runtime security requirements.

## 15. Multi-Tenancy: What Exactly Is a Tenant?

The word *tenant* is overloaded.

In a SaaS product, a tenant may be a customer organization whose data must be isolated from other customers.

In a Kubernetes cluster, a tenant may be an engineering team with permission to deploy workloads.

In a security-scanning platform, a tenant might even represent an isolated execution environment for customer-supplied scanning configurations.

These are not necessarily the same boundary.

### SaaS data isolation

Suppose the application serves two customers through the same API Deployment.

Both requests use the same Kubernetes ServiceAccount.

Kubernetes cannot automatically determine which MongoDB documents belong to each customer.

That requires application-level authorization and data-isolation design.

Putting the application in a namespace named `production` doesn't solve tenant-specific database access.

### Team isolation

Suppose two engineering teams share a cluster.

They may need separate namespaces, Roles, resource quotas and network policies.

The objective is to prevent one team from accidentally modifying or exhausting another team's infrastructure.

This is a more natural fit for namespace-scoped Kubernetes controls.

### Untrusted-workload isolation

Now suppose customers can submit arbitrary code or configuration to be executed.

The threat model becomes much stronger.

A malicious workload may deliberately attempt to escape its sandbox or attack nearby workloads.

Namespaces alone may be insufficient.

Dedicated nodes, sandboxed container runtimes, virtualized environments or separate clusters may be justified.

The appropriate isolation level depends on how much the tenants trust one another and what failures are acceptable.

## 16. Shared Nodes, Dedicated Nodes, and Dedicated Clusters

Let's examine the isolation spectrum.

### Shared namespace and shared nodes

This offers limited segmentation and can be convenient for tightly coupled, mutually trusted components.

But it creates a broad shared policy and resource environment.

For unrelated teams or sensitive workloads, it may be unnecessarily permissive.

### Separate namespaces on shared nodes

This provides stronger API organization and policy boundaries.

RBAC and NetworkPolicy can limit interactions.

However, the workloads still share underlying nodes and infrastructure.

A node-level compromise may affect workloads beyond the compromised namespace.

### Dedicated node pools

Sensitive scanner workloads can be scheduled onto dedicated nodes.

Taints, tolerations, node affinity and admission policy can help enforce placement.

This reduces co-location with unrelated workloads.

But node pools still share some cluster-level control-plane services.

And a scheduling convention is not itself a complete isolation guarantee unless workload authors cannot bypass its intended constraints.

### Sandboxed runtimes

Some environments use sandboxed container runtimes to add stronger separation between workloads and the host kernel.

These can involve additional virtualization or user-space kernel isolation.

They may reduce the consequences of some container escape vulnerabilities.

But they can introduce overhead, compatibility limitations and operational complexity.

### Separate clusters

For sufficiently sensitive or mutually distrustful workloads, separate clusters can provide stronger infrastructure separation.

That comes at a cost.

More clusters require more lifecycle management, networking, policies, observability and upgrades.

Managed Kubernetes can reduce some operational burden, but it doesn't eliminate the architecture.

### The decision principle

Choose isolation based on the consequences of compromise.

A low-risk internal batch processor and a scanner executing potentially hostile inputs shouldn't automatically receive identical isolation.

Likewise, not every application needs its own dedicated cluster.

The objective is proportional security, not maximal infrastructure ceremony.

## 17. Resource Quotas and Denial-of-Service Isolation

Security isn't only about confidentiality.

Availability also matters.

Suppose an application team can create unlimited Pods.

A mistake or malicious automation could generate thousands of workloads and consume shared cluster capacity.

Other teams might then be unable to deploy their services.

Kubernetes ResourceQuotas can limit resource consumption and certain object counts within namespaces.

LimitRanges can provide or constrain resource requests and limits.

Pod priorities, scheduling policies and separate node pools can provide additional protections.

But quotas don't eliminate every noisy-neighbor problem.

For example, network bandwidth, storage performance, shared databases and API-server traffic may become bottlenecks.

The threat model must include the resources that tenants actually share.

A system isn't securely isolated if one tenant cannot steal another tenant's data but can routinely make the other's service unavailable.

## 18. Detection: What Would a Compromise Look Like?

Preventive controls are essential, but they will never catch every problem.

Suppose our scanner has been compromised.

What evidence might reveal it?

Perhaps its process begins making unexpected network connections.

Perhaps its ServiceAccount attempts Kubernetes API operations that were never part of its normal behavior.

Perhaps new Pods appear under an unusual identity.

Perhaps a workload suddenly requests privileged execution.

Perhaps the scanner starts contacting internal services unrelated to scanning.

Each observation points to a different layer.

### API audit logs

Kubernetes audit logging can record API activity according to configured audit policies.

These logs can help reconstruct who attempted which Kubernetes API operations.

They may reveal unauthorized requests, unexpected resource creation or modifications to sensitive resources.

But audit logging must be configured appropriately.

And audit events don't automatically include every action performed inside a container.

### Workload logs

Application logs reveal the scanner's business and runtime behavior.

Unexpected scan destinations, abnormal job transitions or authentication failures may indicate misuse.

However, application logs can be incomplete or manipulated after process compromise.

They should not be treated as the sole authoritative evidence source.

### Network telemetry

Network monitoring can reveal connections to unexpected internal services or external destinations.

For a scanner, interpretation is difficult because unusual outbound traffic is part of the legitimate workload.

The system needs context.

A scan targeting an authorized external domain is different from a scanner attempting to contact the cluster's administrative endpoints.

### Runtime signals

Container and node-level monitoring may detect unusual processes, filesystem operations, privilege changes or other suspicious execution behavior.

The available mechanisms depend on runtime security tooling.

Again, the goal isn't to record every system call forever.

It's to collect useful evidence aligned with the actual threat model.

## 19. Incident Response: Don't Destroy the Evidence

Suppose the security team confirms that a scanner process was compromised.

The first instinct might be to delete the Pod.

That may reduce immediate exposure, but it may also destroy useful evidence.

Container filesystems and `emptyDir` data can disappear with the Pod.

Application memory and process state may vanish when the container exits.

The appropriate response depends on severity, available forensic capabilities and organizational incident procedures.

### Containment

Limit the attacker's ability to continue operating.

Possible measures include revoking affected credentials, restricting network access, preventing further scheduling of compromised workloads, and isolating relevant execution environments.

These actions must be performed carefully.

An emergency NetworkPolicy applied incorrectly could also disrupt critical recovery services.

### Identity and credential review

Determine which Kubernetes and cloud identities were available to the compromised workload.

Inspect their effective permissions and associated resources.

Rotate or revoke exposed credentials as appropriate.

Don't assume that deleting the Pod immediately invalidates every external credential the process may have obtained.

### Scope investigation

Determine which APIs, databases, storage systems and other workloads were reachable or affected.

Review available audit logs, network telemetry and application records.

An attacker may have used legitimate permissions in ways that leave no obvious application crash.

### Recovery

Rebuild workloads from trusted artifacts, correct the exploited vulnerability and reduce excessive permissions.

Verify the integrity of affected business state.

Then test whether the security boundaries actually prevent the same chain from recurring.

### The important distinction

Recovering a running Pod is not the same as recovering trust.

Kubernetes may replace the compromised process immediately.

But if the new Pod uses the same vulnerable image and excessive identity, it recreates the same security exposure.

**Reconciliation restores declared state. Security recovery must establish that the declared state is trustworthy.**

## 20. Designing a Defensible Scanner Platform

Let's bring everything together.

We have a platform that must execute complex scanning tools against potentially hostile external systems.

We want strong engineering without creating an absurdly expensive infrastructure.

What would a reasonable design look like?

### Separate the control plane from scanning execution

A trusted orchestration component receives requests, validates authorization and schedules scanning work.

Scanner workers execute the actual investigations.

Ordinary workers shouldn't automatically receive the permissions required to create or modify arbitrary Kubernetes resources.

If Jobs are used for isolated scans, a dedicated controller can own the relevant Kubernetes API operations.

### Use narrow ServiceAccounts

Each workload gets an identity corresponding to its actual responsibilities.

Workers that don't call the Kubernetes API should avoid mounting an unnecessary API token.

Controllers that need API permissions should receive narrow Roles rather than broad cluster access.

### Restrict internal network access

Scanner workers need controlled access to the broker, result-ingestion service and legitimate scanning destinations.

They generally don't need direct access to billing databases, administrative APIs or unrelated tenant services.

NetworkPolicy and broader network architecture should limit lateral movement.

### Separate privilege classes

Ordinary scanning modules run with non-root execution, restricted capabilities and appropriate seccomp settings.

Specialized scanning tools requiring elevated privileges are isolated into a narrower execution environment.

The entire platform shouldn't run privileged merely because one module needs a specialized capability.

### Protect credentials

External API tokens are scoped appropriately.

Cloud identities use narrow permissions and short-lived credential mechanisms where practical.

Credentials are distributed through controlled mechanisms and rotated deliberately.

### Preserve tenant authorization

Even when workers share a Kubernetes identity, the platform must enforce which customer data and scan tasks they can access.

A trusted result-ingestion API can validate tenant ownership and operation identity.

Kubernetes namespace isolation doesn't replace those checks.

### Monitor security-relevant behavior

Collect appropriate Kubernetes audit records, workload telemetry and network signals.

Pay particular attention to unexpected API permissions, sensitive resource access, unusual Pod creation and unauthorized cross-boundary traffic.

### Apply proportional isolation

A trusted metadata parser and a tool executing complex operations against hostile network targets may deserve different runtime environments.

Use dedicated nodes, stronger sandboxes or separate clusters when the threat model justifies the cost.

This architecture accepts a realistic premise: some scanner component may eventually be compromised.

The goal is to prevent that event from becoming a compromise of the entire business.

## 21. The Oral Examination

Answer each scenario aloud. Try to identify both the immediate weakness and the missing security boundary.

### Challenge 1 — The Namespace Illusion

A development team deploys the scanner in `scanners` and MongoDB in `platform`.

They conclude that the scanner cannot connect to MongoDB because the two applications belong to different namespaces.

What is wrong with that assumption?

### Challenge 2 — The ServiceAccount That Cannot Read Secrets

A ServiceAccount cannot directly read Secrets through RBAC.

However, it can create arbitrary Pods in the namespace containing those Secrets.

Why might this still create a serious exposure?

### Challenge 3 — The Innocent Default Identity

A scanner doesn't call the Kubernetes API.

It uses the namespace's default ServiceAccount, and its token is automatically mounted.

What would you change, and what protection would that provide?

### Challenge 4 — The Privileged Network Scanner

One scanning module requires low-level network capabilities.

The team responds by running every scanner container with `privileged: true`.

What is the architectural mistake, and what alternative would you propose?

### Challenge 5 — The Cloud Identity Surprise

A worker's Kubernetes ServiceAccount has almost no RBAC permissions.

The security team therefore considers it low-risk.

But the workload can obtain cloud credentials allowing broad object-storage access.

What have they overlooked?

### Challenge 6 — Restricted Pods, Exposed Data

Every Pod satisfies the Restricted Pod Security Standard.

Nevertheless, a scanner successfully retrieves another customer's scan results through an internal API.

Why didn't Kubernetes Pod hardening prevent this?

### Challenge 7 — The Shared Cluster Decision

Two internal engineering teams share a Kubernetes cluster.

A third tenant wants to execute arbitrary customer-supplied code.

Should it automatically use the same isolation model?

Explain the factors that would determine your decision.

### Challenge 8 — The Perfectly Rebuilt Vulnerability

A compromised scanner Pod is deleted.

Kubernetes starts a replacement with the same image and credentials.

The platform team announces that the incident has been resolved.

What is missing from that conclusion?

## 22. Solutions and Discussion

### Solution 1 — Namespaces aren't automatic firewalls

Namespaces organize API resources and scope many policies, but they don't automatically block Pod-to-Pod network communication.

The cluster's network model may permit cross-namespace connections unless appropriate policies or other controls restrict them.

The team must inspect and test actual network isolation.

### Solution 2 — Pod creation can provide indirect Secret access

A newly created Pod can reference Secrets available within its namespace.

Therefore, an identity capable of creating arbitrary Pods may be able to arrange for Secret consumption without possessing direct Secret `get` permission.

It may also be able to select more privileged ServiceAccounts.

Permission to create workloads must be treated as security-sensitive.

### Solution 3 — Remove unnecessary API credentials

Use a dedicated or appropriately controlled ServiceAccount and set `automountServiceAccountToken: false` when Kubernetes API credentials are unnecessary.

This removes one credential exposure path.

It does not automatically restrict internal network access or other application credentials.

### Solution 4 — One specialized capability shouldn't weaken every workload

The team has expanded the privileges of the entire scanning fleet to accommodate one specialized tool.

Instead, separate workloads by capability requirements.

Most scanning modules can run under restrictive security contexts.

Specialized jobs can receive narrower additional capabilities and stronger execution isolation.

The design should minimize both the number of privileged workloads and the duration and scope of their authority.

### Solution 5 — Cloud IAM and Kubernetes RBAC are separate

The workload may have narrow Kubernetes permissions but broad external cloud authority.

Its federated identity or cloud credentials can still permit damaging operations.

The security review must inspect Kubernetes RBAC, cloud IAM, trust relationships and the resources accessible through each identity.

### Solution 6 — Pod hardening doesn't enforce customer ownership

Restricted Pod Security Standards constrain certain operating-system and Pod configuration risks.

They don't automatically authenticate business requests or enforce tenant-specific database access.

The internal API must validate the caller's application identity and its authorization to access the requested customer data.

### Solution 7 — Untrusted execution requires a stronger threat model

Internal teams may be sufficiently trusted for namespace-based separation combined with appropriate policies.

Arbitrary customer-supplied code introduces deliberate adversarial behavior.

The organization should evaluate sandboxed runtimes, dedicated nodes, virtualized environments or separate clusters based on the required isolation level, performance overhead and operational cost.

### Solution 8 — Replacement is not remediation

The new Pod may contain the same vulnerability and excessive permissions.

The incident response must establish the exploit's scope, contain affected identities, correct the vulnerability, rebuild from trusted artifacts, and verify data integrity.

Only then can the team claim meaningful security recovery.

## 23. The Mental Model Worth Keeping

Kubernetes security isn't one wall. It's several independent boundaries.

When a workload is compromised, ask:

1. **Process:** What operating-system privileges does it possess?
2. **Identity:** Which ServiceAccount and external credentials can it use?
3. **Authorization:** What Kubernetes and cloud operations are permitted?
4. **Network:** Which systems can it reach?
5. **Data:** Which business records can it read or modify?
6. **Isolation:** What other workloads share its infrastructure?
7. **Recovery:** What evidence establishes that the system is trustworthy again?

These questions expose the difference between a contained application compromise and a cluster-wide security incident.

A hardened container with excessive API permissions is dangerous.

A Pod with no API permissions but unrestricted internal network access may still be dangerous.

A strongly isolated workload using an overly privileged cloud identity can still expose critical resources.

The correct objective is to minimize authority across every relevant boundary.

**Assume a process can fail or be compromised. Design the infrastructure so that its failure doesn't automatically become everyone else's failure.**

## 24. Next Lecture — SE450-L07: Releases, GitOps, and Platform Observability

We've learned how to deploy applications, connect them, allocate resources, preserve state and constrain their privileges.

But how do we safely change a running production system?

A Deployment can report successful rollout while customers experience broken requests.

A Helm upgrade can apply valid manifests that create an incompatible application release.

A GitOps controller can faithfully restore configuration that operators are desperately trying to change during an incident.

And observability tools can report healthy Pods while business transactions continue failing.

In the next lecture, we'll examine how release automation, reconciliation, deployment verification and production observability should cooperate.

The central question is:

**How do we know that a new version is actually better, rather than merely successfully deployed?**

*The spoken lecture ends here. The remainder is for hands-on practice and screen-based revision.*

---

## Optional Practical Lab — Prove What a Kubernetes Identity Can and Cannot Do

**Goal:** Create an isolated practice namespace, define a narrowly scoped ServiceAccount, verify its effective RBAC permissions, and test a restrictive Pod security policy without deploying a privileged workload.

This lab doesn't require actual exploits, real credentials, or access to sensitive Secrets. It is a defensive configuration experiment.

Use a disposable local Kubernetes cluster with permission to create namespaces and namespaced RBAC resources.

### Lab A — Verify the cluster

Check which cluster you're about to modify.

```bash
kubectl config current-context
kubectl get nodes
```

Create a dedicated namespace.

```bash
kubectl create namespace se450-l06
```

Confirm that the namespace is empty apart from ordinary automatically created objects.

```bash
kubectl get all -n se450-l06
```

### Lab B — Create a dedicated ServiceAccount and Role

Create `rbac-demo.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: scanner-observer
  namespace: se450-l06
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: config-reader
  namespace: se450-l06
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: scanner-config-reader
  namespace: se450-l06
subjects:
  - kind: ServiceAccount
    name: scanner-observer
    namespace: se450-l06
roleRef:
  kind: Role
  name: config-reader
  apiGroup: rbac.authorization.k8s.io
```

Apply it:

```bash
kubectl apply -f rbac-demo.yaml
```

Inspect the objects:

```bash
kubectl get serviceaccounts,roles,rolebindings -n se450-l06
kubectl describe role config-reader -n se450-l06
```

Notice that the Role grants access only to ConfigMaps, and the binding applies within the namespace.

### Lab C — Verify effective permissions

With a local administrator identity that is authorized to impersonate ServiceAccounts for authorization checks, test the following:

```bash
kubectl auth can-i get configmaps \
  --as=system:serviceaccount:se450-l06:scanner-observer \
  -n se450-l06

kubectl auth can-i list secrets \
  --as=system:serviceaccount:se450-l06:scanner-observer \
  -n se450-l06

kubectl auth can-i create pods \
  --as=system:serviceaccount:se450-l06:scanner-observer \
  -n se450-l06
```

Expected results are:

- `get configmaps`: yes.
- `list secrets`: no.
- `create pods`: no.

If the API rejects the impersonation request, the current user lacks the necessary permission to perform the check. Don't interpret that as a result for the ServiceAccount itself.

**Explain:** Why does the first result not imply the other two?

### Lab D — Disable unnecessary token mounting

Create `secure-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: scanner-demo
  namespace: se450-l06
spec:
  serviceAccountName: scanner-observer
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: scanner
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
      resources:
        requests:
          cpu: "20m"
          memory: "32Mi"
        limits:
          cpu: "100m"
          memory: "64Mi"
```

Apply the Pod:

```bash
kubectl apply -f secure-pod.yaml
kubectl wait -n se450-l06 --for=condition=Ready pod/scanner-demo --timeout=120s
```

Inspect its security configuration and mounts:

```bash
kubectl get pod scanner-demo -n se450-l06 -o yaml
```

Within this Pod, the ordinary automatic ServiceAccount token mount is disabled.

**Explain:** Why does the Pod still have a ServiceAccount identity even though its token isn't automatically mounted?

### Lab E — Enforce Restricted Pod Security

Apply the Restricted Pod Security Standard to the isolated practice namespace:

```bash
kubectl label namespace se450-l06 \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted \
  --overwrite
```

Inspect the labels:

```bash
kubectl get namespace se450-l06 --show-labels
```

Now create an intentionally invalid manifest called `invalid-pod.yaml`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: invalid-privileged-pod
  namespace: se450-l06
spec:
  containers:
    - name: demo
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      securityContext:
        privileged: true
```

Do not create the privileged Pod.

Instead, use server-side dry-run validation:

```bash
kubectl apply --dry-run=server -f invalid-pod.yaml
```

The request should be rejected by the Restricted Pod Security Admission policy.

It violates multiple requirements, including privileged execution and other missing restrictive settings.

Now test the ordinary hardened Pod specification without changing the running Pod:

```bash
kubectl apply --dry-run=server -f secure-pod.yaml
```

The hardened configuration should pass the relevant security requirements in a compatible Linux cluster, assuming no additional policies reject it.

**Explain:** What is the difference between the API accepting a resource definition and the runtime enforcing the resulting process restrictions?

### Lab F — Examine the permission boundaries

Consider the ServiceAccount you created.

It can read ordinary ConfigMaps in the practice namespace.

It cannot list Secrets.

It cannot create Pods.

Its Pod does not automatically receive a Kubernetes API token.

And the namespace has an enforced Restricted Pod Security Standard.

Now imagine compromising the application process.

Which Kubernetes API operations are available through its ordinary configuration?

Which network destinations might still be reachable?

Does the Pod security standard prevent the process from making an authorized HTTP request to another service?

Does any of this establish which customer data the application may access?

The answers should reveal the difference between identity, authorization, process restrictions and network controls.

### Lab G — Cleanup

Verify that this is still your isolated practice namespace:

```bash
kubectl get all,serviceaccounts,roles,rolebindings -n se450-l06
```

Then remove it:

```bash
kubectl delete namespace se450-l06
```

Do not delete namespaces you did not create for the experiment.

---

## Further Reading

1. [Kubernetes Security Checklist](https://kubernetes.io/docs/concepts/security/security-checklist/) — Practical workload and cluster hardening.
2. [RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) — Least privilege and indirect privilege escalation.
3. [ServiceAccounts](https://kubernetes.io/docs/concepts/security/service-accounts/) — Workload identity and projected tokens.
4. [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) — Privileged, Baseline, and Restricted profiles.
5. [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/) — Enforcement, auditing and warnings.
6. [Security Contexts](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) — Process identity, privileges, capabilities and filesystem restrictions.
7. [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) — Network-level access control.
8. [Multi-Tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/) — Isolation across teams and untrusted workloads.
9. [Validating Admission Policy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/) — Declarative admission rules.
10. [Linux Kernel Security Constraints](https://kubernetes.io/docs/concepts/security/linux-kernel-security-constraints/) — Seccomp, capabilities, and kernel-level restrictions.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is intentionally fenced for quick visual revision.*

```text
SE450-L06 — SECURITY, ISOLATION, AND MULTI-TENANCY

CENTRAL PRINCIPLE
  Assume a workload can be compromised.
  Limit what that compromise can reach or change.

THREAT BOUNDARIES
  Process        Linux identity, capabilities, seccomp, filesystem
  Kubernetes     ServiceAccount + RBAC + admission
  Network        NetworkPolicy / infrastructure controls
  Cloud          Cloud IAM / federated identity
  Application    Business authorization / tenant ownership
  Infrastructure Node/runtime/control-plane isolation

API SECURITY
  Authentication -> Who is calling?
  Authorization  -> Is this API action permitted?
  Admission      -> Is this resource change acceptable?
  Persistence    -> Store accepted resource state
  Reconciliation -> Controllers act on desired state

SERVICEACCOUNTS
  Workload identity
  Default ServiceAccount exists in namespace
  Token may be mounted automatically
  Modern projected tokens are bound/short-lived
  automountServiceAccountToken: false if unnecessary

RBAC
  Role               Namespaced permission rules
  ClusterRole        Reusable/cluster-scope permission rules
  RoleBinding        Grants permissions in one namespace
  ClusterRoleBinding Cluster-wide binding

  Rules describe:
    API groups
    Resources
    Verbs
    Optional restrictions

DANGEROUS PERMISSIONS
  list/watch secrets    Can expose sensitive Secret data
  create pods           May indirectly consume namespace Secrets
                        or assume existing ServiceAccount identities
  modify deployments   May alter workload code/identity
  broad cluster roles  Can cross namespace boundaries
  privileged pods      Can greatly increase node-level risk

NAMESPACES
  API organization and security-policy scope
  NOT automatic network firewalls
  NOT separate kernels
  NOT complete tenant isolation

CONTAINER HARDENING
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  capabilities.drop: [ALL]
  seccompProfile: RuntimeDefault
  readOnlyRootFilesystem: true where feasible
  Avoid privileged / hostPath / hostPID / hostNetwork

POD SECURITY STANDARDS
  Privileged  Permissive
  Baseline    Prevents common privilege escalations
  Restricted  Stronger workload hardening requirements

POD SECURITY ADMISSION
  enforce -> reject violations
  audit   -> audit annotations
  warn    -> client-facing warnings
  Namespace labels select policy level/mode

ADMISSION POLICY
  Pod Security Admission -> standardized profiles
  ValidatingAdmissionPolicy -> CEL-based validation
  Webhooks -> external mutation/validation
  Policies can affect deployment availability

NETWORK
  Default connectivity may be broad
  NetworkPolicy restricts supported L3/L4 traffic
  Requires enforcing network implementation
  Network reachability != application authorization
  Untrusted scanners need carefully designed egress

CLOUD IDENTITY
  Kubernetes RBAC != cloud IAM
  Federated workload identity can avoid long-lived keys
  Cloud role must be narrowly scoped
  Trust relationship must restrict who can assume identity

SUPPLY CHAIN
  Pin image digest for reproducibility
  Digest != image safety
  Verify build provenance/signatures where appropriate
  Scan dependencies and images
  Protect build and deployment identities
  CI/CD is part of trusted infrastructure

MULTI-TENANCY
  Shared namespace       Weakest segmentation
  Separate namespaces    Namespaced policies and RBAC
  Dedicated nodes        Reduce workload co-location
  Sandboxed runtimes     Stronger process/kernel isolation
  Separate clusters      Stronger infrastructure separation

  Isolation strength should follow the threat model.

RESOURCE ISOLATION
  ResourceQuota  Namespace resource/object budgets
  LimitRange     Resource defaults and constraints
  Priority       Scheduling importance
  Node isolation Reduce noisy-neighbor and escape exposure
  Not all shared bottlenecks are covered by quotas

INCIDENT RESPONSE
  Contain affected workload/credentials
  Preserve useful evidence
  Inspect API audit logs
  Inspect cloud identity use
  Review network and application telemetry
  Determine blast radius
  Rebuild from trusted artifacts
  Verify data integrity and remediation

SEVEN SECURITY QUESTIONS
  1. What process privileges exist?
  2. Which identities/credentials are available?
  3. Which API and cloud actions are allowed?
  4. Which networks can be reached?
  5. Which business records can be accessed?
  6. What infrastructure is shared?
  7. How is trust recovered after compromise?

SENIOR LINE
  "I assume a workload may be compromised and design
   layered boundaries around process privileges, identities,
   API permissions, network reachability and tenant data.
   A namespace or hardened container alone is insufficient;
   the goal is a limited blast radius and defensible recovery."
```
