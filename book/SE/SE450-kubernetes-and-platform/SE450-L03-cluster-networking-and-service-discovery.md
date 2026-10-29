---
id: SE450-L03
course: SE450
title: "Cluster Networking and Service Discovery"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L02
next: SE450-L04
---

# SE450 — Kubernetes and Platform Engineering

## Lecture 03: Cluster Networking and Service Discovery

*Your application has an address. Its Service has another address. DNS provides a name. A network plugin connects the machines. A proxy redirects the traffic. A policy may block it. When the connection fails, which part of this elaborate arrangement is responsible?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a security-scanning platform running inside Kubernetes.

One application, the scanner worker, receives a domain from RabbitMQ and starts investigating it. During the scan, it needs information from another internal application: the asset inventory API.

The inventory API knows which domains belong to which customers, which assets have already been discovered, and which scan results are worth storing.

The scanner calls the inventory API over HTTP.

Yesterday, the request worked.

Today, it fails.

You open the Kubernetes dashboard. The scanner Pod is Running. The inventory API Pods are Running. Their Deployment has two available replicas.

You discover something even stranger: the scanner can reach public websites on the internet.

So the network is obviously working, isn't it?

Not necessarily.

There isn't one magical thing called *the network*. There are several independent mechanisms cooperating to deliver a request.

The scanner must discover the inventory API's address. The address must lead to a Service whose routing configuration identifies the correct backends. The packet must travel through the cluster network. Security policies must permit the connection. Finally, the actual application must be listening and capable of responding.

Any one of those steps can fail while the others remain healthy.

This lecture is about learning to distinguish them.

## 1. Why Pod IP addresses are not enough

Suppose the inventory API has two Pods.

One has the address `10.244.1.20`. The other has `10.244.2.15`.

The scanner could theoretically call one of those addresses directly.

But what happens when Kubernetes replaces the Pod?

As we learned in SE450-L02, a replacement Pod is a new object with a new identity and potentially a different IP address.

Yesterday's address might no longer identify a useful application instance.

Our scanner shouldn't need to discover every new Pod address whenever the Deployment rolls out a new version.

Instead, Kubernetes provides a Service.

A Service offers a stable logical destination for a changing group of backends.

For example, the scanner can call `http://inventory-api:8080`.

The name identifies the Service. The Service's configuration identifies the eligible inventory API endpoints.

One Pod can disappear, another can appear, and the client can continue using the same Service name.

The key insight is:

**A Pod identifies a particular execution environment. A Service identifies a logical network destination that can outlive its individual Pods.**

## 2. DNS answers the question "Where?"

When our scanner asks to connect to `inventory-api`, it first needs to turn that name into an address.

Inside a typical Kubernetes cluster, CoreDNS provides DNS resolution for Services and other supported cluster records.

A Service in the `security` namespace might have the fully qualified name:

`inventory-api.security.svc.cluster.local`

The final domain suffix depends on cluster configuration; `cluster.local` is the conventional example.

For a normal ClusterIP Service, DNS returns its virtual Service IP address.

Suppose that address is `10.96.42.17`.

The scanner can now attempt to connect to `10.96.42.17:8080`.

But here's the important part:

**DNS has not selected the inventory API Pod that will handle the request.**

DNS has identified the Service's virtual destination.

Another networking mechanism must make that destination lead to an eligible backend.

This is why a successful DNS lookup does not prove that application traffic can flow.

## 3. The Service is a stable receptionist

Imagine entering a hospital.

You know the hospital's address, but you don't know which doctor will see you today.

At reception, your request is directed to an available physician.

Tomorrow, that physician might be absent. Another doctor can see you, but the hospital's address hasn't changed.

A Kubernetes Service plays a similar role for network connections.

It represents an address and port associated with a changing set of endpoints.

The endpoints generally correspond to Pods selected by the Service's labels, although Services can also exist without selectors.

The Service does not require clients to know the current backend population.

But don't take the analogy too literally.

A Kubernetes Service is ordinarily not a receptionist process running at the Service IP. It is an API object whose behavior is implemented by networking machinery.

There may be no application process listening directly on the virtual address.

Instead, packet-processing rules or another service-routing implementation translate traffic toward a selected endpoint.

### Visual anchor — service discovery and routing

```text
Scanner Pod
    |
    | 1. Resolve inventory-api
    v
Cluster DNS
    |
    | Answer: Service virtual IP
    v
10.96.42.17:8080
    |
    | 2. Service routing selects endpoint
    v
+-----------------------------+
| Inventory Service           |
|                             |
|  Pod A       Pod B          |
|  10.244.1.20 10.244.2.15   |
+-----------------------------+
```

DNS and Service routing solve different problems.

DNS translates a name into a destination address.

Service routing connects that logical destination to actual endpoints.

## 4. But who carries the packet?

Now imagine that the scanner runs on node A and the selected inventory API Pod runs on node B.

The two Pods are on different machines.

Their traffic must cross the physical or virtual network connecting those nodes.

This is where Kubernetes' Pod network comes in.

Kubernetes expects a network model in which Pods receive unique cluster-wide IP addresses and can communicate across nodes without requiring application-level NAT between ordinary Pod addresses.

A network implementation must make that possible.

That implementation might use routes, virtual Ethernet interfaces, overlays, tunnels, eBPF programs, or integrations with cloud networking.

Different clusters implement the same broad network contract in very different ways.

The Container Network Interface, or CNI, provides a standard interface through which container runtimes and Kubernetes networking integrations can configure container networking.

The important concept isn't which particular plugin your company installed.

It's that **Kubernetes specifies the desired networking behavior, while a networking implementation makes packets actually travel**.

If cross-node routing breaks, DNS can still return the correct Service address.

The Service can have healthy endpoints.

The application can be ready.

And the packet can still fail to reach its destination.

## 5. NetworkPolicy: the door can be deliberately locked

Suppose the cluster network is functioning perfectly.

The Service resolves.

The selected inventory API endpoint is healthy.

But the scanner is not permitted to connect.

Kubernetes supports NetworkPolicy resources that describe allowed network communication.

For example, the inventory API might accept traffic only from authorized backend workloads in the `security` namespace.

This protects the API from unnecessary internal exposure.

A Pod running in another namespace might be perfectly healthy and able to access the public internet, yet be unable to contact the inventory API.

That's not a malfunction.

It's an intentional security boundary.

An important detail: **a NetworkPolicy resource only has an effect when the cluster's networking implementation supports and enforces it.**

Writing a YAML policy doesn't magically install a firewall.

We'll examine actual policy behavior in the Deep Dive.

## 6. The browser enters through another door

So far, everything has happened inside the cluster.

But what if a customer wants to reach our public API from a browser?

The customer cannot normally address the cluster's internal `inventory-api.security.svc.cluster.local` name.

That namespace belongs to the cluster's DNS environment.

External clients need an entry point.

Kubernetes can expose Services using several mechanisms, including NodePort and LoadBalancer Services.

For HTTP applications, an Ingress controller or Gateway API implementation can also route external requests based on hostnames, paths and related rules.

This creates another layer:

A public name identifies an external entry point, which selects a Service, which eventually leads to an application Pod.

For example:

```text
Customer's browser
       |
       v
api.example.com
       |
       v
External load balancer
       |
       v
Gateway / HTTP router
       |
       v
scanner-api Service
       |
       v
Eligible API Pod
```

Each stage has its own configuration and possible failures.

A public DNS record can be correct while the Gateway route is wrong.

The Gateway route can be correct while the Service has no endpoints.

The Service can have endpoints while the application rejects the HTTP request.

The network isn't one mechanism. It's a sequence of distinct responsibilities.

## The minute-long mental replay

The scanner wants to call `inventory-api`.

First, its resolver discovers the Service's address through DNS.

Then the scanner opens a connection to that address and port.

Service-routing machinery selects an eligible backend endpoint.

The Pod network carries the packet, potentially across multiple nodes.

Network policies and underlying networking controls determine whether communication is permitted.

The destination application receives the connection and processes the request.

A successful response travels back through the relevant connection path.

If any step fails, we identify that step rather than vaguely blaming Kubernetes networking.

### Three questions before the Deep Dive

1. Why does a ClusterIP Service have a different IP address from its Pods?
2. Why does successful DNS resolution not prove that a connection will succeed?
3. What can block communication even when the source and destination Pods are healthy?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Scanner That Could Reach Google but Not MongoDB

At 09:15, a scanner worker starts failing.

Its application logs report connection timeouts when contacting the internal inventory API.

A developer enters the scanner container and performs three tests.

The first test resolves the inventory API's DNS name successfully.

The second test connects to a public website successfully.

The third test attempts an HTTP request to the inventory API and times out.

"That makes no sense," says the developer. "DNS is healthy. Internet access works. The inventory Pods are running."

It actually makes perfect sense.

DNS, internet egress, and internal Pod-to-Pod communication may use different paths, addresses, policies and infrastructure.

We need to reconstruct the exact connection.

Let's begin where the network actually begins: inside a Pod.

## 2. The Pod Network Namespace

A Pod is a Kubernetes execution unit containing one or more containers.

One of the resources shared by ordinary containers within a Pod is its network namespace.

A Linux network namespace has its own view of network interfaces, addresses, routing tables and related network state.

For example, a Pod may have an interface with an IP address such as `10.244.1.30`.

Two containers inside that Pod can generally communicate through localhost because they share the network namespace.

But two different Pods normally have separate network namespaces.

If one Pod connects to `127.0.0.1`, it is contacting its own loopback interface—not another Pod's loopback interface.

### The localhost trap

Suppose the inventory API listens only on `127.0.0.1:8080`.

Inside its own Pod, a request to localhost succeeds.

The application appears healthy when tested from the same network namespace.

But another Pod connecting to the inventory Pod's IP address cannot necessarily reach that listener.

The process is not listening on the destination address used by remote clients.

For an ordinary API that should accept Pod-network connections, the application commonly binds to `0.0.0.0` for IPv4, or the appropriately configured IPv6/wildcard address.

The precise listener configuration depends on protocol and security requirements.

This distinction is fundamental:

**The Pod having an IP address does not imply that every process inside it listens on that address.**

### What about containerPort?

A Kubernetes container specification can declare `containerPort: 8080`.

This is useful metadata for tools, named ports and other resource configuration.

It does not itself force the application to listen on that port.

Nor is it a firewall rule that opens an otherwise closed socket.

If your Node.js application listens on 3000 while your Pod specification documents 8080, Kubernetes doesn't magically translate the application's port.

The operating system still needs a real listening socket.

## 3. The Kubernetes Network Model

Kubernetes defines broad expectations for Pod networking.

Every ordinary Pod receives a unique address within the cluster's Pod network.

Pods should be able to communicate directly across nodes, except where policy or other intentional restrictions interfere.

For ordinary Pod-to-Pod traffic, the model does not require applications to translate between individual Pod IP addresses.

This makes distributed applications easier to reason about.

An application on node A can target a Pod IP on node B without knowing how those two physical machines are connected.

But this abstract model requires an implementation.

### Node addressing versus Pod addressing

A node has its own address or addresses on the infrastructure network.

A Pod receives an address within the Pod network.

These are different identities.

Suppose node A has infrastructure address `192.168.10.11`, while one of its Pods has `10.244.1.30`.

Node B has infrastructure address `192.168.10.12`, while an inventory Pod has `10.244.2.15`.

The scanner Pod sends a packet to `10.244.2.15`.

Some networking implementation must arrange for that packet to reach node B and its destination Pod.

The application does not ordinarily care whether the implementation uses an overlay tunnel or native routing.

The networking infrastructure cares very much.

### Cross-node paths

A common overlay-network design encapsulates the original Pod packet inside another packet addressed between nodes.

The infrastructure transports the outer packet.

At the destination node, the overlay implementation removes the encapsulation and forwards the original packet toward the destination Pod.

Another design might advertise Pod routes directly through the underlying network, avoiding overlay encapsulation.

Cloud-integrated implementations may allocate Pod addresses from virtual network ranges that are directly routable through the cloud infrastructure.

All are attempts to satisfy the Pod networking model.

The trade-offs include operational complexity, MTU overhead, performance, address management and integration with network policy.

### The MTU surprise

Imagine that ordinary packets fit within a 1500-byte Ethernet MTU.

An overlay encapsulates those packets inside additional headers.

The encapsulation consumes space.

If the network configuration doesn't account for that overhead, some packet sizes may require fragmentation or fail to traverse the path properly.

Under certain circumstances, small requests succeed while larger transfers stall.

This is a classic example of why "ping works" does not prove every transport operation will work.

And, as we learned in CS230, an ICMP echo test does not establish that a TCP connection to a specific port is possible.

## 4. CNI: The Networking Implementation Boundary

Kubernetes uses the Container Network Interface as an integration mechanism for configuring container networking.

CNI is an interface and specification, not one universal network topology.

A CNI implementation is responsible for creating or configuring the networking environment needed by Pods, often including interfaces, addresses and routes.

Different networking projects provide varying additional capabilities.

Examples include Calico, Cilium and Flannel, although their architectures and capabilities differ substantially.

Some solutions focus heavily on connectivity; others add advanced network policy enforcement, observability, eBPF-based routing, or integrations with cloud infrastructure.

A Kubernetes cluster's actual networking behavior therefore depends partly on the chosen implementation.

### The important distinction: CNI versus Service routing

People sometimes speak as though CNI and kube-proxy are interchangeable components.

They aren't.

Pod networking makes Pod addresses reachable.

Service routing makes a Service's logical IP and port lead to the appropriate endpoints.

A conventional cluster may use a CNI plugin for Pod connectivity and kube-proxy for Service routing.

Another cluster may use an eBPF-based networking system that also replaces kube-proxy functionality.

The architectural responsibilities remain distinguishable even when one product implements both.

This gives us our first useful diagnostic separation:

**Can I reach the target Pod IP directly? Can I reach the target through its Service?**

If direct Pod connectivity works but Service connectivity fails, the likely investigation shifts toward the Service definition, endpoints and Service-routing implementation.

If both paths fail, the problem may be at the Pod listener, network-policy or Pod-network layer.

These are hypotheses, not universal diagnostic proofs, because policies and traffic paths may differ between direct and Service connections.

## 5. Services: Stable Identity for an Unstable Population

A Kubernetes Service exposes a logical network endpoint.

The most common internal Service type is ClusterIP.

A ClusterIP Service receives a virtual IP address from the cluster's configured Service address range.

That address is distinct from the Pod address range.

Consider an inventory API Deployment with two ready Pods:

- `10.244.1.20:8080`
- `10.244.2.15:8080`

Its Service might use:

- `10.96.42.17:80`

A client connects to the Service IP on port 80.

Service-routing machinery forwards that connection toward an eligible endpoint on port 8080.

This separation of ports is deliberate.

### Service port versus targetPort

Consider:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: inventory-api
spec:
  selector:
    app: inventory-api
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

The Service accepts connections through port 80.

The selected Pods are expected to accept traffic on port 8080.

The `targetPort` can also refer to a named port declared on the target containers, allowing backend port definitions to evolve behind a stable Service contract.

The `port` is the Service-facing port.

The `targetPort` describes the endpoint-facing port.

Neither field starts the actual application server.

If the container process listens only on 3000, the Service configuration above cannot make its port 8080 respond.

### Why not use the Pod IPs directly?

Pod IP addresses are tied to Pod lifetimes.

Deployment updates, rescheduling and failure recovery produce replacement Pods.

Clients would need to discover and track the changing addresses.

The Service abstraction decouples client configuration from backend lifecycle.

It also lets Kubernetes choose among multiple eligible endpoints.

This makes Services a foundational part of ordinary application architecture inside a cluster.

### Selectors: a Service can point to nobody

A Service commonly uses labels to select backing Pods.

Suppose the Deployment template labels Pods with:

`app: inventory-api`

But somebody accidentally changes the Service selector to:

`app: inventory-service`

The Service itself remains a valid API object.

It still has a name and a ClusterIP.

DNS may still resolve it correctly.

But the selector no longer identifies the intended Pods.

The Service may have no eligible endpoints.

Our scanner now calls a destination that exists logically but has nobody available to answer.

This produces one of the most useful Kubernetes troubleshooting questions:

**Does the Service have ready endpoints, not merely an address?**

## 6. EndpointSlices: The Actual Backend Membership

Kubernetes uses EndpointSlice resources to represent groups of network endpoints backing Services.

For ordinary selector-based Services, the EndpointSlice controller observes the relevant Pods and manages endpoint information.

The endpoint data includes addresses, ports and readiness-related conditions.

Why a separate API object?

Because backend populations can be large and dynamic.

A Service might have hundreds or thousands of endpoints. Every deployment and autoscaling event changes that population.

EndpointSlices allow the system to represent these endpoints in manageable pieces rather than forcing all endpoint information into one giant legacy object.

The modern EndpointSlice API also provides richer endpoint conditions and dual-stack support.

### An illustrative EndpointSlice

```yaml
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: inventory-api-example
  labels:
    kubernetes.io/service-name: inventory-api
addressType: IPv4
ports:
  - name: http
    protocol: TCP
    port: 8080
endpoints:
  - addresses: ["10.244.1.20"]
    conditions:
      ready: true
  - addresses: ["10.244.2.15"]
    conditions:
      ready: true
```

This simplified example demonstrates the information, not a resource you should manually create for an ordinary selector-based Service.

The controller normally manages those EndpointSlices for you.

### Endpoint readiness and termination

EndpointSlices support important conditions:

**ready** indicates whether the endpoint is ordinarily eligible to receive traffic.

**serving** indicates whether an endpoint can serve traffic, including the meaningful distinction for an endpoint that is terminating.

**terminating** reports whether the endpoint is being terminated.

Normally, terminating endpoints are excluded from ordinary ready endpoint selection. Some implementations can consider serving-but-terminating endpoints during special cases, such as when all available endpoints are terminating.

There is also a relevant exception for Services configured with `publishNotReadyAddresses`, which changes readiness reporting semantics.

These details matter during rolling deployments.

A Pod may begin termination while existing connections remain active.

Its endpoint information changes, but updates and networking decisions propagate asynchronously.

This is why graceful shutdown remains necessary even when Services and readiness probes are configured.

### EndpointSlice versus the old Endpoints API

The older Endpoints API is deprecated in modern Kubernetes.

For new diagnostics and tooling, inspect EndpointSlices.

A useful command is:

`kubectl get endpointslices -l kubernetes.io/service-name=inventory-api`

The command reports the endpoint objects associated with that Service in the selected namespace.

If you find no eligible endpoints, investigate the Service selector, Pod labels and Pod readiness before blaming packet routing.

## 7. Service Virtual IPs: The Address That Doesn't Belong to a Pod

Here's the weird part.

The Service's ClusterIP usually isn't assigned to a conventional application network interface in the same way that a Pod IP is.

Instead, Kubernetes networking uses a virtual-IP implementation.

In many conventional clusters, kube-proxy configures packet-processing rules on each node.

These rules recognize traffic addressed to a Service IP and port and redirect it to an eligible endpoint.

### What kube-proxy actually does

Despite the name, kube-proxy is not necessarily a user-space reverse proxy accepting every HTTP request.

Common Linux kube-proxy modes program kernel networking mechanisms such as iptables or nftables.

The packet can be redirected through kernel packet-processing rules.

Conceptually:

```text
Client Pod
  source:      10.244.3.12
  destination: 10.96.42.17:80
                    |
                    v
        Service-routing decision
                    |
                    v
  destination: 10.244.2.15:8080
                    |
                    v
             Inventory Pod
```

This is a simplified representation of destination translation; the real path depends on the proxy mode, network implementation and connection state.

### Why connection tracking matters

The first packets of a TCP connection establish the forwarding decision.

Linux connection tracking, or an equivalent mechanism, helps maintain consistent translation for subsequent packets belonging to that flow.

Consequently, a Service does not necessarily distribute individual HTTP requests independently among all Pods.

With ordinary L4 Service forwarding, a long-lived TCP connection generally remains associated with a selected backend.

If a client sends many HTTP requests over that connection, they may all reach the same Pod.

This has an important consequence for load distribution.

Imagine two API Pods and one client maintaining a long-lived HTTP/2 connection.

The client sends a thousand requests over that connection.

Kubernetes' ordinary Service routing does not automatically guarantee that 500 requests reach each Pod.

The selected connection can concentrate traffic on one backend.

For request-aware balancing, connection pooling or application-level proxying, additional L7 mechanisms may be needed.

### kube-proxy is not mandatory

Some networking implementations provide Service routing without kube-proxy.

For example, an eBPF-based datapath may implement Service translation and load balancing directly.

Therefore, finding no kube-proxy Pods is not automatically evidence that the cluster is broken.

First establish which networking architecture the cluster actually uses.

A useful senior-engineering habit is to separate the logical requirement from its implementation.

The Service abstraction is part of Kubernetes.

The precise packet-forwarding implementation is cluster-dependent.

## 8. DNS: Turning Logical Names Into Addresses

We've covered the actual Service routing. Now return to discovery.

Kubernetes ordinarily deploys a cluster DNS service, commonly implemented by CoreDNS.

For a normal ClusterIP Service, DNS provides records associating the Service's domain name with its cluster IP.

For example:

`inventory-api.security.svc.cluster.local`

A Pod in the `security` namespace may be able to resolve the shorter name `inventory-api` because its resolver configuration contains appropriate search domains.

A Pod in a different namespace generally needs to specify the namespace explicitly, such as:

`inventory-api.security`

Or use the fully qualified service name.

### How the name is structured

The conventional fully qualified name consists of:

- Service name: `inventory-api`
- Namespace: `security`
- Service domain component: `svc`
- Cluster DNS domain: commonly `cluster.local`

The resulting name is:

`inventory-api.security.svc.cluster.local`

This is not a public internet DNS name.

It is intended for resolution within the cluster's DNS environment, or another environment deliberately configured to resolve that zone.

### DNS search domains

A Pod's resolver configuration may include search domains resembling:

```text
search security.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

The exact configuration depends on cluster settings.

The search path allows applications to use short Service names conveniently.

But it also introduces behavior that can be surprising.

With a high `ndots` value, the resolver may try search-domain expansions before an absolute lookup, depending on the name and resolver implementation.

This can produce additional DNS queries, especially for names outside the cluster.

For critical external lookups, understanding the resolver's search behavior and caching policy can matter for latency and query volume.

Do not assume every libc resolver, language runtime and application library behaves identically.

### DNS caching

A client may cache DNS answers.

A node may have a DNS cache.

CoreDNS itself may cache relevant answers.

This is useful for performance, but it also means DNS observations can be affected by TTL and application-level caching behavior.

For ordinary ClusterIP Services, the virtual Service IP offers stability even as Pod endpoints change.

This reduces the need for clients to repeatedly rediscover individual Pod addresses.

A headless Service deliberately changes that relationship.

## 9. Headless Services: Sometimes You Want the Individual Members

A normal ClusterIP Service hides the changing endpoint population behind a virtual IP.

But some applications need to discover the individual members of a distributed system.

Consider a database replica set.

A database driver may need to connect to specific replicas, discover the current primary, or address a particular member.

A load-balanced virtual IP that sends connections to arbitrary database members may not provide the desired semantics.

Kubernetes supports headless Services by setting:

`clusterIP: None`

A headless Service does not receive the usual virtual ClusterIP.

Instead, DNS can publish records associated with the backing endpoints.

For selector-based headless Services, DNS commonly returns the addresses of the relevant Pods.

This allows clients to discover individual members.

### Why StatefulSets often use headless Services

Recall the StatefulSet from SE450-L02.

A stateful application might have Pods with stable names such as `mongo-0`, `mongo-1` and `mongo-2`.

A headless Service can help provide the DNS naming structure that makes those members discoverable under predictable names.

For instance, a Pod might be addressable through a name resembling:

`mongo-0.mongo-headless.database.svc.cluster.local`

The exact names depend on the StatefulSet, Service and cluster configuration.

This gives us another crucial distinction:

**A ClusterIP Service generally hides backend identity; a headless Service can expose backend identity for applications that need it.**

Neither automatically supplies application-level leader election, quorum or data consistency.

Those remain the database's responsibilities.

## 10. NetworkPolicy: Turning a Flat Network Into Security Boundaries

Kubernetes' basic networking model makes Pod communication broadly possible.

That's convenient, but it may not be an acceptable security posture.

Imagine a multitenant cybersecurity platform.

One namespace contains internal asset data.

Another contains externally facing APIs.

Another contains scanning workers that process untrusted input and interact with internet hosts.

Should every scanning process have unrestricted access to every internal database?

Probably not.

The scanner workers may need to call a limited internal API while having no direct reason to connect to unrelated application storage.

NetworkPolicy provides a mechanism for expressing permitted network connections.

### Ingress and egress are separate directions

A NetworkPolicy can control incoming traffic to selected Pods, called ingress.

It can also control outgoing traffic from selected Pods, called egress.

The distinction matters because a connection can be blocked from either side.

Suppose the scanner is allowed to send traffic to the inventory API.

But the inventory API's ingress policy does not permit the scanner.

The connection is blocked.

Alternatively, the inventory API may accept the scanner, but the scanner's egress policy may forbid connecting to the inventory API.

The result is again a blocked connection.

The relevant source egress and destination ingress permissions must both allow the traffic where those Pods are isolated for their respective directions.

### Network policies are additive

Kubernetes NetworkPolicy does not work like a firewall rule list where one rule can explicitly override another with a higher-priority deny statement.

The standard model is additive.

Policies select Pods and define allowed communication for particular directions.

For Pods isolated in a direction, the effective allowed traffic is the union of the applicable allow rules.

Creating an additional policy cannot negate an already applicable allowance in the standard NetworkPolicy model.

This is important when debugging unexpected access.

You must inspect all policies selecting the relevant Pods, not just the policy you most recently edited.

### Default-deny policy

A namespace can adopt a default-deny ingress posture.

For example:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

The empty Pod selector selects all Pods in the namespace.

The policy establishes ingress isolation without declaring any incoming connections as allowed.

Other policies can then permit particular sources and ports.

A default-deny egress policy works similarly for outgoing traffic.

But this comes with an obvious operational trap.

### The DNS trap

Suppose you deploy a default-deny egress policy to protect scanner workers.

Immediately afterward, applications begin reporting that internal names cannot be resolved.

Why?

DNS itself requires network communication.

The Pod needs to send queries to the appropriate DNS service or resolver endpoint.

If egress policy blocks those packets, DNS resolution fails even though CoreDNS may be perfectly healthy.

A secure egress design therefore usually needs an explicit allowance for the required DNS traffic, commonly UDP and TCP port 53 to the intended cluster DNS endpoints.

The exact policy selectors and path depend on the cluster's DNS deployment, NodeLocal DNSCache usage, and network implementation.

**Security isolation is not achieved by blindly denying everything and hoping applications still work.**

A good security policy expresses legitimate dependencies explicitly.

## 11. NetworkPolicy Is Not a Complete Firewall

The standard Kubernetes NetworkPolicy API is primarily about L3/L4 connectivity between selected Pods and peers, using IP-related selectors and transport ports.

It does not universally express every security property an application might need.

For example, ordinary NetworkPolicy does not natively enforce rules such as:

"Allow GET requests to `/assets` but deny POST requests to `/assets/delete`."

That is an application-layer authorization requirement.

A service mesh, API gateway or specialized networking policy system might provide additional L7 enforcement, but standard Kubernetes NetworkPolicy is not an HTTP authorization engine.

### Policies require enforcement support

This bears repeating because it is an important operational hazard.

The Kubernetes API server may accept a NetworkPolicy resource even if the installed networking stack does not enforce it.

In that case, the policy exists as an API object but does not necessarily restrict traffic.

You must verify implementation support and test actual enforcement.

### There are tricky network-address cases

Traffic from a node, host-network processes or external load balancers may not behave exactly like ordinary Pod-to-Pod traffic.

NAT can complicate which source or destination addresses a policy implementation sees.

IP-based policy semantics may differ depending on where translation occurs in the packet path.

NetworkPolicy changes may also affect established connections differently across implementations.

For highly sensitive isolation requirements, verify the real packet path and the selected networking plugin's documented behavior.

Do not extrapolate from one successful test to every possible traffic path.

## 12. Service Types: ClusterIP, NodePort, LoadBalancer, and ExternalName

We've focused on internal ClusterIP Services, but Kubernetes offers several Service types.

Each answers a slightly different exposure requirement.

### ClusterIP — internal logical endpoint

ClusterIP is the default type.

It provides a cluster-internal virtual IP and Service routing toward endpoints.

It is appropriate for most internal API-to-API communication.

A scanner worker calling an inventory API is a typical example.

### NodePort — expose a port on nodes

A NodePort Service exposes a port on eligible node addresses, with the precise behavior depending on the Service configuration, routing implementation and infrastructure networking.

Conceptually, traffic arriving at a node's NodePort is directed toward the Service's eligible backends.

This can provide an externally reachable entry point if the surrounding network permits access.

But NodePort alone doesn't automatically create a useful public DNS name, install a TLS certificate or configure a public firewall correctly.

It is a networking primitive, not a complete public API platform.

### LoadBalancer — ask infrastructure for an external entry point

A LoadBalancer Service integrates with an appropriate load-balancer implementation.

In a cloud environment, that may provision or configure a cloud load balancer.

In a local cluster, an implementation such as a local load-balancer controller may be needed.

Merely creating a Service of type LoadBalancer does not guarantee that an external IP appears.

The infrastructure must support the request.

Many implementations build on Service and NodePort mechanisms internally, but the exact path is provider-dependent.

### ExternalName — a DNS alias, not a backend pool

An ExternalName Service maps a Service name to an external DNS name.

It does not use ordinary selector-based endpoint routing.

This can be useful for certain naming arrangements, but it does not automatically solve TLS hostname verification or HTTP Host header semantics.

If a client connects using one hostname while the remote application expects another, protocol-level mismatches are possible.

ExternalName is not a transparent application gateway.

## 13. Ingress: HTTP Routing Enters the Cluster

An internal Service is not enough when customers need to reach an HTTP application from outside.

An Ingress resource describes rules for routing HTTP or HTTPS traffic to Services.

A rule might say:

Requests for `api.example.com` with a path beginning `/scans` should reach the scanner API Service.

Requests for `app.example.com` should reach the frontend Service.

An Ingress controller implements those rules using an actual proxy or load-balancing system.

The Ingress object alone doesn't perform packet forwarding.

Without an appropriate controller, it is merely configuration.

### An illustrative Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: security-platform
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /scans
            pathType: Prefix
            backend:
              service:
                name: scanner-api
                port:
                  number: 80
```

The example omits production TLS and controller-specific configuration.

An Ingress controller must be installed, and external DNS must be configured appropriately.

A resource successfully accepted by the API does not mean that traffic can already reach it.

### Ingress is stable, but no longer expanding

The Kubernetes Ingress API is stable and widely used.

However, it is frozen for new feature development.

The Kubernetes project recommends Gateway API for newer routing capabilities.

This does not mean existing Ingress deployments must be immediately rewritten.

It means that Gateway API is the intended direction for more expressive routing architecture.

## 14. Gateway API: Separation of Infrastructure and Routing Ownership

Gateway API introduces resources with more explicit responsibility boundaries.

A **GatewayClass** identifies a class of Gateway implementation.

A **Gateway** describes an instance of traffic-handling infrastructure, including listeners.

An **HTTPRoute** describes HTTP routing rules and how they attach to Gateways.

This matters because large organizations rarely want every application team to administer the entire public networking infrastructure.

A platform team might own Gateway infrastructure and TLS policies.

An application team might own the HTTPRoute that publishes its service through an approved Gateway.

This creates a cleaner division of responsibilities.

### A simplified architecture

```text
Platform team
    |
    v
GatewayClass
    |
    v
Gateway
    |
    | accepts attached HTTPRoutes
    v
Application team's HTTPRoute
    |
    v
scanner-api Service
    |
    v
Ready scanner-api Pods
```

The actual routing is performed by a Gateway API implementation.

The API resources express the intended relationships.

Gateway API uses custom resource definitions and an appropriate implementation rather than being universally operational in every cluster by default.

### Why this matters for system design

A senior engineer should think about ingress architecture in terms of trust boundaries.

Where does TLS terminate?

Which team owns public routes?

Which requests require authentication?

Which backends may be exposed?

How are timeouts and request sizes enforced?

Where are rate limits configured?

How are routes observed and audited?

Those are architectural questions, not simply Kubernetes syntax questions.

The public entry point is one of the highest-risk components in a production system.

## 15. Following an External Request End to End

Let's trace a customer's request to start a scan.

The customer sends:

`POST https://api.example.com/scans`

Public DNS resolves `api.example.com` to an address associated with the external entry infrastructure.

The request reaches a cloud load balancer or another externally reachable frontend.

A Gateway or Ingress implementation selects the route corresponding to the hostname and path.

The route points to the `scanner-api` Service.

Service-routing machinery or the gateway's backend integration selects an eligible scanner API endpoint.

The Pod network carries traffic to that backend.

The API process receives the HTTP request and performs authentication, authorization and validation.

It records the scan request and arranges downstream work.

The response returns along the relevant connection path.

Every arrow in this sequence can introduce latency, failure, security enforcement or observability requirements.

### Where TLS terminates changes the architecture

TLS might terminate at the external load balancer.

It might terminate at the Gateway.

It might be reestablished between the Gateway and the backend.

A service mesh could provide further workload-to-workload encryption.

The actual design determines which component can inspect HTTP headers and paths, and where plaintext is exposed.

Not all clusters use the same pattern.

If an application depends on headers such as `X-Forwarded-For` or `Forwarded`, it must also define which intermediary is trusted to supply them.

Blindly trusting client-provided forwarding headers can create security problems.

The correct client-IP and identity model depends on the full proxy chain.

## 16. Egress: Leaving the Cluster Is a Different Journey

Our security scanners spend much of their time communicating with external hosts.

That traffic has different requirements from internal API communication.

A scanner Pod may connect to a public domain over HTTPS.

Its packets must reach a destination outside the Pod network.

Depending on the cluster and cloud infrastructure, the source address may be translated through a node, NAT gateway or specialized egress gateway.

The external server may see a public egress IP shared by many Pods.

It will not normally see the Pod's private address.

### Why this matters for security scanning

Suppose a target organization allows scans only from a small list of approved source IP addresses.

If the cluster uses several NAT gateways or nodes with different public addresses, scans may originate from multiple egress identities.

Autoscaling or node replacement can change those addresses unless the architecture deliberately stabilizes them.

This is operationally significant.

A security-scanning platform may need predictable outbound identity, explicit source allowlists, rate limits and tenant isolation.

These requirements aren't solved merely by running the scanner inside Kubernetes.

### The connection-pool trap

Consider thousands of scanner Pods establishing outbound connections.

The egress infrastructure may experience high connection-tracking pressure, NAT port usage or external rate-limit pressure.

Scaling Pods doesn't automatically scale every downstream network resource.

A cluster can have plenty of CPU while its shared egress path becomes the bottleneck.

That connects this lecture to SE460, where we'll study performance and capacity more systematically.

### NetworkPolicy and egress

Standard NetworkPolicy can restrict outgoing connections by selected peers, IP blocks and ports, subject to its API model and implementation.

But enforcing an allowlist of arbitrary external DNS names isn't generally a native standard NetworkPolicy capability.

Some advanced networking products provide FQDN-aware policy extensions.

Those are implementation-specific features, not promises made by the core NetworkPolicy API.

## 17. Traffic Distribution, Locality, and Connection Semantics

A Service with multiple eligible endpoints often distributes connections among them.

But the exact algorithm depends on the implementation.

Ordinary Service routing is not necessarily a sophisticated application-aware load balancer.

### Session affinity

Services can use client-IP-based session affinity.

This can help preserve a relationship between a client source address and a selected backend for a period of time.

But it's not a substitute for correct state management.

A Pod can still disappear. Source IPs may be shared through NAT. Traffic distribution can become uneven.

Application session state generally deserves a deliberate persistence or sharing strategy rather than dependence on one particular Pod surviving.

### Internal traffic policy

A Service can use `internalTrafficPolicy: Local`, requesting that internal Service traffic be restricted to suitable endpoints on the source node.

This can reduce cross-node traffic.

But it has a sharp consequence.

If the source node has no eligible local endpoint, traffic may fail even when healthy endpoints exist elsewhere in the cluster.

This is an intentional locality trade-off.

It illustrates why a Service having endpoints is not always enough: routing policy may limit which endpoints are eligible for a particular client.

### Topology-aware distribution

Modern Kubernetes also supports traffic distribution preferences that can favor topologically closer endpoints.

Such preferences can help reduce cross-zone traffic and associated cost or latency.

Their actual behavior depends on Kubernetes version, implementation and available endpoint topology data.

You should distinguish a strict policy from a routing preference.

A preference may be relaxed when necessary. A strict locality requirement may exclude otherwise healthy endpoints.

### Long-lived connections

Suppose a gRPC client opens a persistent HTTP/2 connection to a Service.

Ordinary L4 Service routing may select a backend once for that connection.

Subsequent RPCs can continue using the same selected Pod.

Adding more Pods does not automatically rebalance existing connections across the newly available replicas.

The application or client may need an appropriate connection-management strategy, or an L7 proxy may handle request-aware balancing.

This is a classic example of infrastructure appearing horizontally scalable while an application's connection pattern prevents effective distribution.

## 18. Debugging the Original Incident Properly

Return to our scanner worker.

DNS works.

Public internet access works.

The inventory API Service exists.

But an internal HTTP request times out.

How do we investigate?

We should move through the connection path in a deliberate order.

### Step 1 — Confirm the exact failing destination

What hostname is the scanner using?

What namespace?

Which port?

Which protocol?

Is it using HTTP, HTTPS, gRPC or a direct TCP connection?

Does it use a short name that resolves differently in another namespace?

Don't investigate a guessed destination.

Start with the actual one.

### Step 2 — Test name resolution

From an appropriate debug environment sharing the relevant network policies and DNS configuration, test the Service name.

For example:

`nslookup inventory-api.security.svc.cluster.local`

If resolution fails, inspect the resolver configuration, cluster DNS components, DNS Service endpoints and relevant egress restrictions.

If resolution succeeds, record the returned address.

But don't stop there.

The answer establishes name resolution, not successful communication.

### Step 3 — Inspect the Service definition

Use:

`kubectl get service inventory-api -n security -o yaml`

Confirm the Service type, virtual IP, ports and selectors.

The Service's `port` should match the port requested by clients.

Its `targetPort` should match the actual endpoint port.

Be especially suspicious of selectors that no longer match the deployed Pods.

### Step 4 — Inspect EndpointSlices

Use:

`kubectl get endpointslices -n security -l kubernetes.io/service-name=inventory-api`

Inspect the listed endpoint addresses and readiness conditions.

If there are no eligible endpoints, investigate labels and Pod readiness.

A Service with no usable backends cannot successfully deliver requests to an application merely because it has a ClusterIP.

### Step 5 — Test direct Pod connectivity

From a suitable debug Pod, attempt a connection to a known inventory API Pod IP and its actual listener port.

Compare this with the Service connection.

If direct connectivity works but the Service connection fails, examine Service routing, port translation and traffic policies.

If direct connectivity also fails, inspect the application listener, Pod networking and relevant security policies.

Remember that different traffic paths may encounter different policy behavior, so this comparison is diagnostic evidence rather than a mathematical proof.

### Step 6 — Inspect NetworkPolicies

List policies in the source and destination namespaces.

Determine which policies select the scanner Pod for egress and which select the inventory API Pod for ingress.

Check selectors, namespace labels, ports and protocols.

Remember that allowed traffic is additive across applicable standard NetworkPolicies.

Also verify that the installed networking implementation actually enforces NetworkPolicy.

### Step 7 — Investigate the network datapath

If the configuration looks correct but packets still fail, investigate the CNI implementation and its operational health.

Check the involved nodes, routes, networking-agent status and relevant logs.

Determine whether the failure occurs only across nodes or also between Pods on the same node.

This distinction can reveal routing, overlay, tunneling or node-specific issues.

### Step 8 — Return to the application

If TCP connections succeed but HTTP requests fail, shift toward application diagnostics.

A connection refused result is different from a timeout.

An HTTP 401 indicates an authorization-related application outcome, not generic packet loss.

An HTTP 503 may originate from a Gateway, proxy or application; its actual origin must be identified.

A TLS handshake failure can occur even when TCP connectivity works perfectly.

The diagnostic process should preserve these distinctions instead of collapsing every symptom into "the network is broken."

## 19. The Network Is a Chain of Independent Contracts

Let's summarize the full journey.

A client wishes to communicate with a named application.

DNS maps the name to an address.

A Service abstraction provides a logical destination.

EndpointSlices describe the current backend membership.

Service-routing machinery chooses an eligible endpoint and implements forwarding.

The Pod network transports packets to the destination.

Security policies and infrastructure controls determine whether the traffic is permitted.

The destination process must actually listen and respond according to the protocol.

For external traffic, additional entry or egress infrastructure participates.

Each mechanism has a contract.

Each contract can be satisfied while another fails.

This is what makes networking confusing to engineers who approach it as one monolithic feature.

And this is what makes it manageable to engineers who separate the responsibilities.

## 20. The Oral Examination

Try answering each question aloud before reading the solutions.

### Challenge 1 — DNS Works, the API Doesn't

The scanner resolves `inventory-api.security.svc.cluster.local` to the correct Service IP.

The inventory Deployment reports two healthy replicas.

The request still times out.

Identify at least four distinct causes that remain possible.

### Challenge 2 — The Vanishing Backends

The inventory API is deployed successfully, and all Pods are Running.

The Service has a ClusterIP but its EndpointSlices contain no eligible endpoints.

What would you inspect, and why?

### Challenge 3 — Direct Pod IP Works

The scanner successfully connects to `10.244.2.15:8080`, but connecting through `inventory-api:80` fails.

Which layers become more suspicious?

### Challenge 4 — The Database Discovery Problem

A three-member database cluster needs clients to discover individual replica identities.

Would an ordinary ClusterIP Service always be the best abstraction?

Explain when a headless Service may be more appropriate.

### Challenge 5 — The Security Policy Incident

An engineer creates a default-deny egress NetworkPolicy.

Immediately, Pods can no longer resolve internal Service names.

Why might that happen? What should be done without reopening all outbound traffic?

### Challenge 6 — The Uneven Load Balancer

A gRPC client sends thousands of requests through one long-lived HTTP/2 connection.

There are four healthy application Pods, but most work reaches only one.

Why might ordinary Service routing behave that way?

### Challenge 7 — The Internet-Facing API

A team creates an Ingress resource and expects the application to become publicly reachable.

The Ingress exists, but external requests fail.

Which pieces might still be missing or misconfigured?

## 21. Solutions and Discussion

### Solution 1 — Name resolution is only one step

Possible causes include an incorrect Service selector, no eligible endpoints despite healthy-looking Pods, a Service-to-backend port mismatch, a network policy denying the connection, a broken Service-routing datapath, or a cross-node CNI problem.

The destination application might also bind only to localhost or fail to accept connections despite its readiness status.

Investigate the path in order rather than assuming the successful DNS answer validates the entire request.

### Solution 2 — Inspect endpoint selection

Compare the Service selector with actual Pod labels.

Inspect the Pods' readiness conditions and the Service's target port.

Then inspect the EndpointSlices and their reported conditions.

A Pod being Running does not guarantee that it is Ready.

A selector mismatch can leave a Service with no backing Pods even when the Deployment is healthy.

### Solution 3 — Service-specific mechanisms become suspicious

Direct Pod IP connectivity provides evidence that the application listener and at least one Pod-network path are functioning.

Investigate the Service definition, port mapping, EndpointSlices, Service-routing implementation and applicable traffic policies.

Do not treat the result as absolute proof that all underlying networking is healthy, because direct and Service traffic may traverse different policy and translation paths.

### Solution 4 — Discovering individual members requires identity

An ordinary ClusterIP Service hides backend identity behind a virtual address.

A headless Service can expose endpoint addresses through DNS, which is useful when clients need to discover individual members.

StatefulSets and headless Services often cooperate to provide stable per-member identities.

The database still manages replica membership, leader election and consistency.

### Solution 5 — DNS queries are outbound traffic

The default-deny egress policy may block the Pod's DNS queries.

An explicit egress rule should permit DNS traffic to the intended cluster DNS endpoints, with appropriate port and protocol restrictions.

The exact implementation depends on the cluster's DNS and networking architecture.

Allowing DNS is not equivalent to allowing arbitrary outbound connections.

### Solution 6 — Service routing is commonly connection-oriented

An L4 Service implementation often selects a backend for a connection and maintains that association through connection tracking.

Many gRPC calls can share one HTTP/2 connection.

The requests therefore need not be independently balanced across all healthy Pods.

Solutions may involve different client connection strategies or appropriate L7 load balancing, depending on the application.

### Solution 7 — An Ingress object is not infrastructure

An Ingress controller must exist and implement the requested rules.

The external entry point and DNS records must be configured.

The controller must have a valid route to the backend Service, which must have eligible endpoints.

TLS configuration, firewall rules, load balancer health and namespace restrictions may also matter.

A Kubernetes resource existing does not prove that its real-world infrastructure is ready.

## 22. The Mental Model Worth Keeping

When Kubernetes networking fails, follow five questions in order:

**Name:** What address did the client discover?

**Destination:** What Service and port does that address represent?

**Backends:** Which endpoints are eligible to receive the connection?

**Path:** What networking implementation carries and redirects the packets?

**Permission and application:** Is traffic allowed, and is the destination process actually capable of responding?

This framework converts an intimidating networking incident into a sequence of testable hypotheses.

A Service is not a Pod. DNS is not routing. CNI is not necessarily Service proxying. NetworkPolicy is not authentication. An HTTP response is not proof that every network hop was healthy.

Distinguish the contracts and the investigation becomes manageable.

## 23. Next Lecture — SE450-L04: Scheduling, Resources, and Autoscaling

We've learned how network communication reaches a Pod.

But what determines where that Pod runs in the first place?

Suppose the cluster reports plenty of unused CPU, yet a Pod remains Pending.

Another Pod runs but experiences severe CPU throttling.

A third is killed under memory pressure even though the node's overall memory usage seems reasonable.

And the Horizontal Pod Autoscaler keeps adding replicas, making the problem worse.

In the next lecture, we'll explore how Kubernetes schedules workloads, interprets resource requests and limits, applies placement constraints, and scales capacity through multiple interacting control loops.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — Break Service Discovery Without Breaking the Cluster

**Objective:** Reproduce the difference between successful DNS resolution, endpoint selection, Pod connectivity and policy enforcement.

**Environment:** A disposable local Kubernetes cluster such as Minikube or kind. The lab uses a dedicated namespace and ordinary test resources.

Do not run the destructive portions against an unfamiliar shared or production cluster.

### Lab A — Verify the target cluster

```bash
kubectl config current-context
kubectl get nodes
```

Create an isolated namespace:

```bash
kubectl create namespace se450-l03
```

### Lab B — Create a backend and its Service

Create `backend.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inventory-api
  template:
    metadata:
      labels:
        app: inventory-api
    spec:
      containers:
        - name: web
          image: nginx:stable-alpine
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: inventory-api
spec:
  type: ClusterIP
  selector:
    app: inventory-api
  ports:
    - name: http
      port: 8080
      targetPort: 80
```

Apply the resources:

```bash
kubectl apply -n se450-l03 -f backend.yaml
kubectl rollout status -n se450-l03 deployment/inventory-api
kubectl get pods,svc -n se450-l03 -o wide
```

Observe the difference between the Service IP and Pod IPs.

Inspect the backing EndpointSlices:

```bash
kubectl get endpointslices -n se450-l03 \
  -l kubernetes.io/service-name=inventory-api -o wide
```

### Lab C — Create a client Pod

Create a client with tools for basic DNS and HTTP testing:

```bash
kubectl run scanner-client -n se450-l03 \
  --image=busybox:1.36 \
  --restart=Never \
  --labels=app=scanner-client \
  --command -- sleep 3600
```

Wait until it is running:

```bash
kubectl wait -n se450-l03 \
  --for=jsonpath='{.status.phase}'=Running \
  pod/scanner-client --timeout=120s
```

Resolve the backend name from inside the client:

```bash
kubectl exec -n se450-l03 scanner-client -- \
  nslookup inventory-api
```

Then make an HTTP request:

```bash
kubectl exec -n se450-l03 scanner-client -- \
  wget -T 5 -qO- http://inventory-api:8080/
```

You should receive the standard Nginx response.

**Investigate:** Which address did DNS return? Did it return a Pod IP or the Service ClusterIP?

### Lab D — Break endpoint selection

Change the Service selector so that it no longer matches the Deployment's labels:

```bash
kubectl patch service inventory-api -n se450-l03 \
  --type=merge \
  -p '{"spec":{"selector":{"app":"nonexistent-backend"}}}'
```

Inspect the Service:

```bash
kubectl get svc inventory-api -n se450-l03
kubectl get endpointslices -n se450-l03 \
  -l kubernetes.io/service-name=inventory-api -o wide
```

Repeat the DNS lookup and HTTP request from the client.

**Expected lesson:** The Service can retain its ClusterIP and DNS record while having no eligible backends.

DNS and application routing are independent layers.

Restore the selector:

```bash
kubectl patch service inventory-api -n se450-l03 \
  --type=merge \
  -p '{"spec":{"selector":{"app":"inventory-api"}}}'
```

Wait for EndpointSlices to reflect the eligible Pods and verify that HTTP works again.

### Lab E — Test direct Pod connectivity

List the backend Pods and their IP addresses:

```bash
kubectl get pods -n se450-l03 -l app=inventory-api -o wide
```

From the client Pod, request the backend's Pod IP directly, using its real container port, 80.

```bash
kubectl exec -n se450-l03 scanner-client -- \
  wget -T 5 -qO- http://POD_IP:80/
```

Replace `POD_IP` with an actual IP from the preceding command.

**Investigate:** What changes between connecting to the Pod IP directly and connecting to `inventory-api:8080`?

### Lab F — Optional NetworkPolicy experiment

Only perform this section after verifying that your local cluster uses a networking implementation that enforces standard Kubernetes NetworkPolicy.

Create `deny-backend.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-inventory-ingress
spec:
  podSelector:
    matchLabels:
      app: inventory-api
  policyTypes:
    - Ingress
  ingress: []
```

Apply it:

```bash
kubectl apply -n se450-l03 -f deny-backend.yaml
```

Test the HTTP request from the client again.

Depending on networking implementation and timing, the connection should be blocked once the policy is enforced. A timeout is one possible symptom.

DNS may still resolve successfully because this policy isolates ingress to the backend, not egress from the client.

Now create `allow-scanner.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-scanner-to-inventory
spec:
  podSelector:
    matchLabels:
      app: inventory-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: scanner-client
      ports:
        - protocol: TCP
          port: 80
```

Apply the allowance:

```bash
kubectl apply -n se450-l03 -f allow-scanner.yaml
```

Test HTTP communication again.

The scanner client should be permitted to reach the backend on TCP port 80 when policy enforcement is working as expected.

Notice that the NetworkPolicy refers to the backend's transport port, not merely the Service's frontend port 8080.

**Questions:**

1. Why did the first policy block a connection even though the Service and Pods were healthy?
2. Why did the second policy restore access?
3. Why didn't the new policy need to remove the default-deny policy?
4. What would it mean if neither policy changed observed connectivity?

### Lab G — Cleanup

Verify that the practice namespace is the one created for this lab, then remove it:

```bash
kubectl delete namespace se450-l03
```

### Lab reflection

Explain the following sequence without looking at the notes:

1. A scanner resolves an internal Service name.
2. The Service virtual IP is translated toward an eligible backend.
3. The Pod network carries traffic to the endpoint.
4. Network policy permits or blocks the connection.
5. The application receives the request and responds.

Then identify which of those steps you deliberately broke during the lab.

---

## Further Reading

1. [Kubernetes Services, Load Balancing, and Networking](https://kubernetes.io/docs/concepts/services-networking/) — The overall network model.
2. [Services](https://kubernetes.io/docs/concepts/services-networking/service/) — ClusterIP, NodePort, LoadBalancer, ExternalName and headless Services.
3. [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/) — Endpoint membership and readiness.
4. [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/) — Internal names and DNS records.
5. [Virtual IPs and Service Proxies](https://kubernetes.io/docs/reference/networking/virtual-ips/) — Kernel-level Service routing.
6. [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) — Ingress, egress and isolation semantics.
7. [Gateway API](https://kubernetes.io/docs/concepts/services-networking/gateway/) — Modern external traffic-routing abstractions.
8. [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/) — An operational investigation sequence.

---

## Dense Cheatsheet — Interview Glance Card

*This reference is fenced for visual revision rather than continuous voice playback.*

```text
SE450-L03 — CLUSTER NETWORKING AND SERVICE DISCOVERY

FULL CONNECTION PATH

  Client application
    -> DNS resolution
    -> Service IP:port
    -> Endpoint selection / Service proxy
    -> Pod networking
    -> Network policy / infrastructure controls
    -> Destination Pod IP:port
    -> Application listener

  External traffic adds:
    Public DNS -> External LB -> Ingress/Gateway -> Service

NETWORKING IDENTITIES

  Node IP:
    Infrastructure address of a Kubernetes node

  Pod IP:
    Address of a particular Pod execution environment
    May change when the Pod is replaced

  ClusterIP:
    Stable virtual Service address
    Not normally an application listener IP
    Redirected toward eligible backend endpoints

POD NETWORK MODEL

  Unique cluster-wide Pod IPs
  Pod-to-Pod connectivity across nodes
  Ordinary Pod traffic without app-level NAT
  Actual implementation depends on networking plugin

CNI
  Configures Pod networking
  Often handles IP allocation, interfaces, routes
  Plugin may also provide policy, eBPF, observability
  NOT synonymous with kube-proxy

SERVICE
  Stable logical network destination
  Selector commonly matches Pod labels
  port = client-facing Service port
  targetPort = backend endpoint port
  Service existence != healthy endpoints

ENDPOINTSLICE
  Backend addresses and ports
  Conditions: ready, serving, terminating
  Modern replacement for legacy Endpoints API
  inspect using:
    kubectl get endpointslices -l kubernetes.io/service-name=...

SERVICE ROUTING
  kube-proxy may program iptables/nftables/IPVS
  Alternative implementations may use eBPF
  VIP traffic redirected to eligible endpoints
  Often connection-oriented via conntrack
  One HTTP/2 connection may concentrate many requests

DNS
  inventory-api.security.svc.cluster.local
  Short names can use namespace search domains
  CoreDNS commonly resolves cluster Service names
  ClusterIP Service DNS -> Service virtual IP
  Headless Service DNS -> endpoint records
  DNS success != connectivity success

HEADLESS SERVICE
  clusterIP: None
  Exposes backend endpoint addresses
  Useful for StatefulSet/member discovery
  Does not provide database consensus or failover

NETWORKPOLICY
  Selects Pods
  Controls ingress and/or egress
  Standard policies are additive allow rules
  Source egress AND destination ingress must allow
  Default-deny possible
  Requires supporting network implementation
  DNS egress must be allowed when needed
  Not an HTTP authorization engine

SERVICE TYPES
  ClusterIP       Cluster-internal virtual endpoint
  NodePort        Service accessible via eligible node ports
  LoadBalancer    External LB via supporting implementation
  ExternalName    DNS alias to another hostname

INGRESS
  HTTP/HTTPS host/path routing to Services
  Requires controller
  Stable API, frozen for new feature development

GATEWAY API
  GatewayClass    Implementation class
  Gateway         Traffic infrastructure / listeners
  HTTPRoute       HTTP routing rules
  Requires CRDs + implementation
  Better responsibility separation for platform teams

EGRESS
  External traffic may traverse node/NAT/egress gateway
  Public source IP may differ from Pod IP
  Shared NAT can introduce capacity and identity issues
  FQDN egress rules are not standard NetworkPolicy

DIAGNOSTIC SEQUENCE
  1. Correct hostname/namespace/port?
  2. DNS resolved correctly?
  3. Service exists and has expected selector?
  4. EndpointSlices contain ready endpoints?
  5. targetPort matches real application listener?
  6. Direct Pod-IP connectivity?
  7. Service VIP connectivity?
  8. Source egress and destination ingress policies?
  9. CNI/cross-node routes/Service datapath?
 10. Application/TLS/HTTP-level errors?

SYMPTOMS — INITIAL HYPOTHESES
  NXDOMAIN           Wrong name, namespace, missing DNS record
  DNS timeout        Resolver reachability, DNS policy/health
  No endpoints       Selector/readiness/controller issue
  Connection refused No listener, rejected connection, routing issue
  Timeout            Policy, packet path, firewall, unreachable endpoint
  HTTP 401/403       App/gateway authorization or access policy
  HTTP 503           Gateway/app unavailable; identify origin
  TLS failure        Certificate, SNI, protocol, trust mismatch

  Symptoms are clues, not exclusive diagnoses.

FIVE RECOVERY QUESTIONS
  What name?
  What destination?
  Which eligible backends?
  Which datapath?
  Which permission/application boundary?

SENIOR LINE
  "DNS identifies a logical destination, Services abstract
   changing endpoint populations, networking implementations
   carry and redirect packets, and policies constrain access.
   Diagnose each responsibility independently rather than
   treating every failed request as one generic network issue."
```
