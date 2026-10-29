---
id: CS230-L06
course: CS230
title: "Private Networks, NAT, and Cloud Reachability"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS230-L05
next: CS230-L07
---






# CS230 — Computer Networks and Web Protocols

## Lecture 06: Private Networks, NAT, and Cloud Reachability

*Customers can reach your backend. Your backend can reach its database. Every health check passes. But when it tries to charge a customer's credit card, the connection disappears into the network. The payment provider never sees it.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine you're responsible for a hotel-booking platform hosted on AWS.

The frontend is served through a CDN. Customer requests arrive through a public application load balancer. Several Node.js backend instances run in private subnets, and PostgreSQL runs in an additional private network segment.

The architecture seems sensible. Customers can search hotels, retrieve reservations, and begin a booking.

Then the payment flow fails.

A customer chooses a hotel and clicks Pay.

Your backend attempts an HTTPS connection to the payment provider. The request times out.

The payment provider says it received nothing.

The backend's DNS lookup succeeds. PostgreSQL is healthy. The public load balancer successfully routes customer requests to the backend.

So why can traffic enter the application while the application cannot contact the outside world?

The answer lies in the difference between **being reachable from the internet, having a route to the internet, and possessing an address that the internet can reply to**.

These are three separate requirements.

## 1. Your backend lives in a private address space

Suppose one backend instance has the address `10.42.20.17`.

That's a private IPv4 address.

Another company might have a server at `10.42.20.17`.

Your home router may manage devices using addresses beginning with `10`.

Millions of private networks can reuse the same address ranges.

This is useful because IPv4 addresses are scarce.

But it creates an obvious problem.

If your backend sends a packet onto the public internet with source address `10.42.20.17`, how should the payment provider send a reply?

There may be countless devices with that address in unrelated private networks.

The public internet doesn't provide an ordinary globally unique route back to your private host.

Something needs to translate the relationship between the private network and the publicly reachable network.

That mechanism is often NAT.

## 2. NAT changes the address the outside world sees

Imagine your backend sends an HTTPS request to a payment provider.

Internally, the request begins at a private source address.

Before the traffic reaches the public internet, a NAT device can translate its source address into a publicly usable one.

From the payment provider's perspective, the request comes from the translated address.

The provider sends its reply there.

The NAT device remembers which internal connection corresponds to the external one and translates the returning traffic back toward the backend.

The backend receives the reply.

To the application, the interaction looks like an ordinary HTTPS conversation.

But the network has changed the addressing information along the way.

The essential mechanism is not mysterious:

**NAT allows one addressing context to communicate through another by translating packet addresses and maintaining the information needed for the return path.**

## 3. The return path is half the conversation

Suppose the backend successfully sends a packet toward the payment provider.

Does that prove the connection will work?

Not yet.

A communication path needs to work in both directions.

The outbound packet must reach the provider.

The provider's response must be able to return to the correct destination.

If the response reaches a NAT device that no longer has the necessary translation state, it may be discarded.

If a firewall blocks returning traffic, the connection may fail.

If the cloud network lacks an appropriate path toward the internet, the original packet may never leave the environment.

This is why troubleshooting shouldn't stop at "the route exists."

A route is a forwarding instruction.

It isn't a guarantee of completed communication.

## 4. Public and private subnets aren't defined by the names we give them

Now look at our AWS architecture.

The public load balancer uses subnets that have suitable routes toward the internet gateway.

The backend runs in private subnets.

The backend can accept traffic forwarded by the load balancer because communication within the VPC has an appropriate local path.

But a private subnet doesn't automatically have outbound internet connectivity.

For ordinary IPv4 internet access, it may need a route toward a public NAT gateway or another suitable egress mechanism.

The NAT gateway then needs its own functioning path to the internet.

### The two traffic paths

```text
INBOUND CUSTOMER REQUEST

Internet
   |
   v
Internet-facing load balancer
   |
   v
Private backend
   |
   v
Database


OUTBOUND PAYMENT REQUEST

Private backend
   |
   v
NAT gateway
   |
   v
Internet gateway
   |
   v
Payment provider
```

The two paths share some infrastructure, but they are not the same path.

Having a working inbound route through a load balancer doesn't establish the existence of a working outbound route from the backend.

## 5. NAT isn't a firewall

Here's an important security distinction.

A NAT device translates addresses.

A firewall decides which traffic is permitted.

Home routers frequently combine both functions, which makes them easy to confuse.

But translation and access control are separate responsibilities.

A server can have a private IP address and still be reachable through a public load balancer or a forwarding rule.

A server can have a public IP address and still be protected by a firewall that rejects inbound connections.

Being privately addressed isn't a complete security policy.

Being publicly addressed isn't automatically a security failure.

The security question is what traffic can reach which endpoints, under which rules, and with which application-level authorization.

## 6. IPv6 changes the need for address sharing

IPv6 provides a vastly larger address space than IPv4.

A cloud workload can have a globally unique IPv6 address without needing address-sharing NAT merely to conserve addresses.

Does that mean every IPv6 instance must accept unsolicited internet connections?

No.

Firewalls and egress-only routing arrangements can restrict incoming traffic.

This is a useful conceptual reset.

NAT is not what makes a network private.

A network's security posture depends on routing and access-control decisions.

## 7. A final mystery: small packets work, large ones don't

Imagine we fix the payment-provider route.

TCP connections now establish successfully.

Small HTTPS requests work.

But sending a large request body causes the connection to stall.

A developer suspects JSON serialization or an application timeout.

The actual problem may be somewhere else.

Network links have limits on the packet sizes they can carry.

A VPN or tunnel can add extra headers, reducing the space available for the original packet.

If oversized packets are discarded and the sender doesn't receive the necessary feedback, the connection can appear to hang.

This is a Path MTU problem.

It illustrates one more important principle:

**Successful connection establishment doesn't prove that every subsequent packet size can traverse the path.**

## The minute-long mental replay

A backend has a private IPv4 address.

The cloud network can route traffic internally, but that doesn't automatically provide a usable public internet path.

For outbound IPv4 access, a NAT gateway can translate the source address and maintain return-traffic state.

An internet gateway and correct subnet routes provide the relevant external path.

Firewalls and security rules independently determine which connections are permitted.

IPv6 can avoid address-sharing NAT while retaining strong access controls.

And packet-size constraints can break data transfer even after a connection has been established.

### Three questions before the Deep Dive

1. Why can't the payment provider ordinarily reply directly to a private source address such as `10.42.20.17`?
2. Why does successful customer access through a public load balancer not prove that the backend has outbound internet access?
3. Why are NAT, routing, and firewall rules different responsibilities?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Payment Request That Never Left the VPC

Our hotel-booking platform has recently migrated to AWS.

The engineering team built a VPC with the address range `10.42.0.0/16`.

Within that VPC, it created separate subnets for public-facing infrastructure, application containers, and databases.

An internet-facing application load balancer accepts customer requests.

The Node.js backend runs in private subnets.

PostgreSQL remains accessible through internal networking.

The migration passes its deployment checks.

Customers can browse hotels and retrieve their reservations.

But the first production payment attempt fails.

The backend attempts to connect to the payment provider over HTTPS and eventually times out.

The payment provider confirms that no corresponding request arrived.

DNS resolution produces the expected public IP address.

The backend's application logs show the outbound operation beginning but never completing.

The engineering team initially investigates TLS certificates, HTTP client configuration, and payment-provider availability.

All reasonable suspects.

But the first useful infrastructure discovery is simpler.

The backend's private subnet has no default IPv4 route toward a suitable external egress path.

The application can communicate within the VPC because its route table contains the local VPC route.

It cannot contact an arbitrary public destination because the routing configuration doesn't provide the necessary next hop.

The application isn't failing at payment processing.

Its packet never completes the intended network journey.

Let's reconstruct that journey.

## 2. The Three Private IPv4 Ranges

RFC 1918 reserves three IPv4 address blocks for private use.

They are:

- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

These blocks can be reused inside independently operated private networks.

An office in Vilnius might use `10.0.0.0/8`.

A hotel in Berlin might use a subnet from the same range.

An AWS VPC might use `10.42.0.0/16`.

The fact that these networks reuse address space isn't inherently a problem.

Their internal routing contexts are separate.

The difficulty appears when private networks need to communicate with one another or with the public internet.

### Private addresses aren't globally unique

Suppose your backend uses `10.42.20.17`.

Another company uses exactly the same address.

A public payment provider cannot distinguish the two solely from that private source address.

Nor does the global internet ordinarily advertise routes allowing it to reach arbitrary RFC 1918 destinations.

Private addressing works because these networks maintain their own internal address contexts.

At the boundary, a system needs an appropriate mechanism for communicating outside that context.

For ordinary IPv4 internet access, source NAT is common.

### What about `100.64.0.0/10`?

You may encounter addresses in the range `100.64.0.0/10`.

This is Shared Address Space defined by RFC 6598, often associated with carrier-grade NAT.

It isn't one of the three RFC 1918 private ranges.

Internet service providers may use it between customer equipment and carrier NAT infrastructure.

This creates situations where your home router has an address that isn't globally reachable even though it also isn't a familiar `192.168` or `10` address.

When debugging internet reachability, don't assume every non-public addressing arrangement uses RFC 1918.

The relevant address category and network topology matter.

## 3. NAT: Following One Connection Through Translation

Consider a laptop on a private network.

Its IPv4 address is `192.168.1.42`.

It opens an HTTPS connection toward a public server at `203.0.113.80`, port 443.

For illustration, the laptop chooses local source port 53124.

The connection begins with these endpoints:

Source: `192.168.1.42:53124`

Destination: `203.0.113.80:443`

These addresses and ports describe a valid connection within the laptop's networking context.

But the private source address isn't appropriate as an ordinary return destination across the public internet.

The NAT device translates it.

Suppose the device has public IPv4 address `198.51.100.24`.

It may translate the source to:

`198.51.100.24:62001`

The destination remains `203.0.113.80:443`.

The server sees the translated source endpoint.

### What the translator remembers

The NAT device keeps connection-mapping information.

Conceptually, it remembers that a flow arriving from a particular private endpoint has been assigned a particular external representation.

When the response arrives at `198.51.100.24:62001`, the NAT device recognizes the relevant mapping.

It rewrites the destination information and forwards the response toward `192.168.1.42:53124`.

The laptop receives the data through its original local socket.

Here's the simplified transformation:

```text
BEFORE OUTBOUND TRANSLATION

192.168.1.42:53124
       |
       v
203.0.113.80:443


AFTER OUTBOUND TRANSLATION

198.51.100.24:62001
       |
       v
203.0.113.80:443


RETURN TRAFFIC

203.0.113.80:443
       |
       v
198.51.100.24:62001
       |
       v
NAT restores destination:
192.168.1.42:53124
```

Notice that the laptop doesn't need to know the NAT device's chosen external port.

It continues using its original local endpoint.

The device manages the translation state.

### NAT isn't necessarily address-only translation

Many common IPv4 NAT arrangements also translate transport-layer ports.

This is often called Network Address and Port Translation, or NAPT, and sometimes Port Address Translation, or PAT.

Port translation allows multiple internal connections to share one public address while remaining distinguishable.

Without port-level differentiation, sharing one public address among large numbers of simultaneous connections would be far more restrictive.

The mapping details vary across NAT implementations.

Some reuse ports where possible.

Others choose different external ports.

The essential requirement is that the device can identify the correct internal destination for permitted return traffic.

## 4. Why NAT Is Stateful

Imagine the NAT device receives a returning packet.

It must determine where that packet belongs.

In an ordinary connection-sharing configuration, the external destination address alone may be insufficient.

Many internal clients share the same public address.

The translated port and additional flow information help identify the correct mapping.

This requires state.

### State has a lifetime

NAT mappings do not usually exist forever.

The device must manage memory and port resources.

For TCP, it can observe connection-related information.

For UDP, which doesn't have TCP's connection lifecycle, the device typically relies more heavily on timers and observed traffic.

The precise mapping and timeout policies depend on the implementation.

This matters for long-lived but idle connections.

Suppose an application keeps a connection-like UDP association idle for a long time.

The NAT device may eventually discard the mapping.

A later packet from the remote peer might no longer match an active translation entry.

The application sees a connectivity failure even though its own local state still suggests the session exists.

This is one reason networking protocols and applications use suitable keepalive, reconnection, or recovery mechanisms.

### Port mappings are finite

A NAT device has limited address and port resources.

Suppose thousands of scanner workers connect simultaneously to the same external service.

Each outbound flow may require translation state and an available external port mapping.

At sufficient scale, the device may become unable to allocate additional mappings under its operating constraints.

New connections fail even though CPU, RAM, and application replicas appear healthy.

This is not an application-thread limit or database connection-pool problem.

It is a shared egress-resource limit.

We'll revisit this when we examine cloud NAT gateways.

## 5. Incoming Connections: Why NAT Doesn't Automatically Expose Your Server

Now reverse the situation.

A public client wants to initiate a connection toward an internal server.

The internal server has address `192.168.1.42`.

The NAT device has public address `198.51.100.24`.

The external client sends a packet toward the public address on some port.

What happens?

In an ordinary outbound-connection-sharing NAT configuration, there may be no translation entry telling the device which internal host should receive the new inbound connection.

The packet cannot be mapped to a specific internal destination merely from the public address alone.

It may be discarded.

### Destination NAT and port forwarding

A device can be configured to translate incoming destinations.

For example:

`198.51.100.24:8443`

might be forwarded toward:

`192.168.1.42:443`

This is destination NAT, commonly abbreviated DNAT.

Home routers often describe such configurations as port forwarding.

Cloud networking systems may provide equivalent or more sophisticated public entry mechanisms.

### But NAT still isn't a firewall

Here is the subtle distinction.

The absence of a translation mapping may prevent an ordinary incoming connection from reaching an internal host.

That behavior can resemble a firewall.

But NAT's primary role is address translation.

A firewall's role is traffic authorization.

You could configure an inbound translation rule that forwards traffic toward a sensitive internal service.

If no suitable filtering or application authorization exists, the service may be exposed.

Conversely, a publicly addressed server can have a firewall that blocks almost all inbound traffic.

Address translation and traffic policy must be assessed separately.

**A network boundary is secure because unwanted traffic is controlled, not because its addressing happens to be private.**

## 6. A Public Subnet Doesn't Give Every Instance a Public Identity

Let's move into AWS.

Our hotel-booking platform uses a VPC with CIDR block:

`10.42.0.0/16`

The VPC contains several subnets.

One subnet hosts an internet-facing application load balancer.

Another hosts Node.js backend instances.

A third hosts database infrastructure.

The public-facing subnet has an IPv4 default route toward an internet gateway.

The backend subnet doesn't.

What makes the first subnet public?

In the ordinary AWS IPv4 model, a subnet is considered public when its associated route table has a route for internet-bound traffic toward an internet gateway.

The label *public* describes that routing arrangement.

It doesn't mean that every instance in the subnet is automatically reachable from the public internet.

### Public routing isn't enough

Consider an EC2 instance in a public subnet.

Its route table sends `0.0.0.0/0` toward an internet gateway.

But the instance has only a private IPv4 address.

Can an arbitrary internet client directly initiate an IPv4 connection to it?

Not through the standard public-IPv4 mechanism.

The instance generally needs a suitable public IPv4 address or Elastic IP association for direct public IPv4 connectivity.

It also needs appropriate security rules and a listening application.

The internet gateway performs the relevant public/private IPv4 address mapping for publicly addressed instances.

Having a route toward the gateway alone doesn't assign a public address.

### The full direct-connectivity requirements

For ordinary direct public IPv4 connectivity, several conditions need to align.

The resource must have the appropriate public addressing arrangement.

Its subnet routing must support the internet gateway path.

Network security controls must permit the intended traffic.

And the destination application must listen and respond correctly.

Failure at any one boundary can prevent successful communication.

### A public load balancer changes the design

Our backend doesn't need direct public IPv4 addresses merely because customers access it.

The internet-facing load balancer provides the public entry point.

It receives requests through its public-facing infrastructure and forwards them toward private backend targets.

The targets communicate using internal VPC connectivity.

This allows the application instances to avoid unnecessary direct internet exposure.

The public load balancer is the designated ingress boundary.

The backend remains privately addressed.

## 7. The Missing Outbound Path

Now return to the payment-provider failure.

A customer reaches the load balancer.

The load balancer reaches the Node.js backend.

The backend accesses PostgreSQL.

Everything internal works.

Then the backend attempts an HTTPS connection to the external payment provider.

DNS resolves the provider's hostname to a public IPv4 destination.

The backend needs a route outside its VPC.

### The private subnet's route table

Suppose the backend subnet has only the local VPC route.

Conceptually:

```text
Destination      Target
10.42.0.0/16     local
```

That route permits forwarding within the VPC's configured address range.

It doesn't tell the VPC how to deliver packets toward arbitrary public IPv4 destinations.

A public payment-provider address doesn't match the local route.

There is no suitable default route.

The connection fails.

### The NAT gateway architecture

For ordinary private-subnet outbound IPv4 internet access, an AWS public NAT gateway is a common solution.

The private subnet gets a route directing internet-bound IPv4 traffic toward the NAT gateway.

The public NAT gateway resides in an appropriate public subnet with a path to an internet gateway and uses an associated public addressing arrangement.

A simplified architecture looks like this:

```text
VPC: 10.42.0.0/16

PUBLIC SUBNET
  Internet-facing load balancer
  Public NAT gateway
         |
         v
  Internet gateway
         |
         v
      Internet


PRIVATE APP SUBNET
  Node.js backend
  Private IP: 10.42.20.17
         |
         v
  Route 0.0.0.0/0 -> NAT gateway


PRIVATE DATABASE SUBNET
  PostgreSQL
  Internal connectivity only,
  unless explicitly designed otherwise
```

The essential private-subnet route is:

`0.0.0.0/0 → NAT gateway`

The NAT gateway's public-subnet route toward the internet gateway completes the intended external path.

### The AWS translation detail

There is a useful implementation detail here.

For a public AWS NAT gateway, AWS documents the NAT gateway translating the originating private address to the gateway's private address.

When that traffic passes through the internet gateway, the public NAT gateway's private address is mapped to its associated Elastic IP.

The external payment provider sees the resulting public egress identity.

Return traffic is translated back through the relevant infrastructure and delivered to the original private workload.

You don't generally need to manage every step manually.

But understanding the distinction prevents confusion when inspecting AWS addressing and traffic flows.

## 8. Security Groups, Network ACLs, and Routes

The outbound route is now correct.

Does that guarantee the payment connection succeeds?

No.

AWS provides multiple traffic-control mechanisms.

They have different responsibilities.

### Route tables

A route table decides where matching traffic should be directed.

For example, traffic toward the VPC's local address range stays within the VPC routing system.

Other IPv4 traffic may be directed toward a NAT gateway.

The route table expresses forwarding choices.

It isn't an application authorization system.

### Security groups

Security groups provide stateful traffic filtering associated with supported resources, commonly network interfaces.

Rules determine permitted traffic according to addresses, security-group references, ports, protocols, and related settings.

Because security groups are stateful, permitted connections can receive corresponding return traffic without requiring a separately mirrored response rule.

For example, if a backend's security group permits an outbound HTTPS connection, return packets belonging to that tracked flow are ordinarily allowed under the stateful behavior.

### Network ACLs

Network ACLs operate at the subnet boundary and are stateless.

They use ordered rules with allow and deny actions.

Because they're stateless, allowing traffic in one direction doesn't automatically permit the corresponding return traffic.

This creates a familiar trap.

Suppose a network ACL allows outbound TCP connections to destination port 443.

But it fails to permit the necessary inbound response traffic toward the client's ephemeral port.

The initial traffic may leave, yet the return path is blocked.

The application experiences a timeout.

### Why ephemeral ports matter

A TCP client connecting to remote port 443 generally chooses a local ephemeral source port.

The remote server's response travels back toward that client-side port.

In a stateless filtering system, rules must account for the actual direction and port relationships of the connection.

The required port ranges depend on the environment and addressing or translation path.

Don't mechanically copy a giant permissive rule without understanding the traffic it is intended to support.

### The three independent questions

At this point, we should be able to separate:

**Routing:** Which gateway or interface handles the packet?

**Translation:** Which address and port mappings permit communication across address contexts?

**Filtering:** Which packets are permitted to cross the relevant boundaries?

All three may be needed.

A correct route can lead to a NAT gateway while a security group blocks the outbound connection.

A security group can permit the connection while the route table lacks an internet path.

And a working outbound route and filter can still fail if the NAT device cannot allocate translation state.

## 9. The Payment Provider's Allowlist

Suppose we fix the subnet route.

The backend now reaches the internet through a public NAT gateway.

But the payment provider rejects the request.

Why?

The provider allows connections only from a set of approved public IPv4 addresses.

Before the migration, payments originated from a known public address.

Now they originate from the NAT gateway's public egress address.

The provider sees a different source identity.

Its allowlist doesn't include that address.

This is a different failure from the missing route.

The packet may reach the provider successfully.

The provider's network security controls may then reject it.

### Egress identity becomes part of the contract

For applications integrating with external payment systems, banking infrastructure, enterprise APIs, or other restricted services, public egress addresses can be operationally important.

The team may need predictable outbound addresses.

A public NAT gateway with appropriate Elastic IP configuration can help provide that identity.

But the architecture must account for every active egress path.

If different private subnets or availability zones use different NAT gateways, requests may originate from different public addresses.

The provider's allowlist must reflect the actual architecture.

### The availability-zone trade-off

AWS recommends considering a NAT gateway in each availability zone that contains workloads requiring internet access, improving zone independence.

This can also reduce cross-zone networking dependencies.

But it may increase infrastructure cost and introduce multiple egress public addresses to manage.

A single NAT gateway can simplify some aspects of administration and allowlisting, but can create an unnecessary cross-zone dependency.

The correct design depends on availability requirements, traffic volumes, provider allowlisting constraints, and cost.

There is no free lunch.

**Predictable egress is an architectural requirement when external systems use source addresses as an access-control input.**

## 10. NAT Gateways Can Become a Shared Bottleneck

Now imagine the hotel platform has expanded.

It operates hundreds of application instances, asynchronous workers, and third-party integration services.

Many of them send traffic through the same NAT gateway.

Some maintain connection pools.

Others frequently open and close connections.

A batch operation suddenly creates thousands of outbound connections to one external API.

The application instances have spare CPU.

The database is healthy.

But new outbound connections intermittently fail.

### Translation resources are finite

A NAT gateway must maintain state for active connections.

It also needs usable external source ports or other mapping resources to distinguish flows.

In AWS, NAT gateways have documented connection-capacity constraints per public or private IPv4 address and destination combination.

The exact capacity and scaling options depend on the gateway configuration.

A particularly useful CloudWatch metric is `ErrorPortAllocation`.

An increase indicates that the NAT gateway failed to allocate a source port for a connection.

This is direct evidence of a translation-capacity problem.

### Why one destination is special

Imagine thousands of clients behind NAT all connecting to the same destination IP, destination port, and protocol.

Those flows compete for the NAT gateway's available mappings for that destination combination.

A distributed workload can therefore concentrate pressure on one egress resource even when its individual application instances appear lightly loaded.

This is similar to a database connection pool shared across many replicas.

Adding more application instances may worsen the pressure.

### Mitigation choices

The correct intervention depends on the failure.

Reduce unnecessary connection churn.

Reuse connections where appropriate.

Limit aggregate concurrency.

Distribute workloads across suitable egress infrastructure.

Consider supported additional NAT gateway addresses or separate gateways when justified.

And monitor actual egress capacity rather than assuming a managed gateway is unlimited.

For a high-volume cybersecurity scanning platform, this is particularly relevant.

Thousands of scanners can generate substantial outbound connection pressure even when the scanning computations themselves are not CPU-intensive.

## 11. NAT and Asymmetric Return Paths

A stateful translator must associate returning traffic with the correct connection.

Now imagine a network with multiple gateways or routes.

The outbound packet travels through NAT device A.

But the return packet arrives through device B.

Device B may not have the translation state created by A.

The connection fails.

This is a stateful-path problem.

### Asymmetric routing isn't universally wrong

Network routes don't have to be geographically or topologically identical in both directions.

Asymmetric paths are common.

Many networks function perfectly well with asymmetric routing.

But stateful intermediaries introduce additional requirements.

If a firewall or NAT device needs to observe both directions of a flow, path asymmetry can break its stateful processing.

The topology must ensure that return traffic reaches the appropriate stateful boundary or use infrastructure designed to share or preserve the necessary state.

### Why this matters in cloud architecture

Multi-homed workloads, transit gateways, VPNs, network appliances, and complex inter-VPC routing can create non-obvious return paths.

A team may inspect the outbound route and declare it correct.

But the return route may traverse a different security or translation path.

When connection establishment behaves inconsistently, inspect both directions.

The question isn't merely whether packets can leave.

It is whether the complete conversation has a usable, policy-compliant path.

## 12. NAT, Proxies, and Load Balancers Are Different Things

At this point, several networking technologies may appear to overlap.

A NAT gateway translates addressing information.

A reverse proxy can terminate a connection and forward an application request.

A load balancer chooses among backend destinations.

A firewall controls permitted traffic.

A single product or managed service may perform more than one of these functions.

But the conceptual responsibilities remain distinct.

### NAT operates on addressing

NAT can rewrite source or destination address information, often including transport ports.

It doesn't inherently need to understand HTTP methods, reservation IDs, or cookies.

### An HTTP proxy understands messages

An HTTP reverse proxy can inspect request paths, hostnames, methods, and headers.

It can cache responses, change headers, enforce application-layer policies, or generate its own errors.

We will study those behaviors in CS230-L09.

### A load balancer chooses targets

A load balancer may use transport-level information or inspect application messages, depending on its design.

Some load balancers perform NAT-like forwarding.

Others terminate connections and establish new ones.

The name describes a role, not one fixed implementation.

### Why the distinction matters

Suppose a payment provider sees the NAT gateway's public source address.

That doesn't mean your Node.js application can trust the source-IP information it receives through the public load balancer.

Those are different paths with different intermediaries.

Likewise, adding an outbound HTTP proxy may affect which application protocols are supported and how traffic is authenticated.

It isn't simply interchangeable with a NAT gateway.

Choosing the correct infrastructure requires understanding which responsibility needs to be fulfilled.

## 13. IPv6: Global Addresses Without Mandatory Address Sharing

IPv6 changes the addressing assumptions.

With suitable global IPv6 allocation, individual workloads can have globally unique addresses.

There is no general need to share one public IPv4 address among thousands of internal endpoints merely because addresses are scarce.

This doesn't imply that IPv6 hosts should be exposed indiscriminately.

### Globally addressed does not mean publicly accessible

An IPv6 workload may have a globally unique address.

But the network can still use firewall rules to block unsolicited inbound connections.

It may use routing arrangements that permit outbound communication without allowing external clients to initiate connections.

Security remains an explicit design concern.

### The AWS egress-only internet gateway

AWS supports egress-only internet gateways for IPv6.

An egress-only internet gateway permits outbound IPv6 communication and corresponding return traffic while preventing ordinary unsolicited inbound IPv6 connections through that gateway.

A subnet route may direct `::/0` toward the egress-only internet gateway.

This is a different mechanism from address-sharing NAT.

The workload can retain its own global IPv6 address.

The gateway provides a stateful outbound-only reachability boundary.

### IPv6 doesn't forbid translation

It would be incorrect to claim that IPv6 never uses NAT or translation.

For example, NAT64 can allow IPv6-only clients to communicate with IPv4 services under appropriate configurations.

AWS NAT gateways support certain IPv6-to-IPv4 translation scenarios using DNS64/NAT64.

But ordinary IPv6-to-IPv6 internet access does not require IPv4-style address-sharing NAT for address conservation.

The distinction is about why translation is used.

IPv4 NAT commonly addresses public-address scarcity and network-boundary requirements.

IPv6 translation may address protocol interoperability or specific architectural needs.

### Security still needs correct routing

If a workload has a global IPv6 address but no suitable IPv6 route, it cannot magically reach the internet.

If the route exists but filtering blocks traffic, the connection may fail.

If the provider offers only an IPv4 endpoint and the environment is IPv6-only, some compatibility or translation mechanism may be necessary.

The basic diagnostic separation survives:

Address, route, policy, transport, application.

## 14. MTU: Why a Connection Can Work Until It Sends Real Data

We have solved the private-subnet payment problem.

The route works.

NAT works.

The provider accepts the source address.

TCP connects successfully.

TLS may even begin successfully.

But certain larger requests stall.

The most suspicious feature is the relationship between failure and packet size.

### Maximum Transmission Unit

A network link has a maximum packet size it can carry at the relevant layer.

For ordinary Ethernet networks, an IP MTU of 1,500 bytes is common.

But an end-to-end path can traverse links with different MTUs.

The effective Path MTU is constrained by the smallest relevant link limit along the path.

### Tunnels add overhead

Imagine an application packet traveling through a VPN.

The original packet is encapsulated inside another packet.

The outer headers consume additional space.

A packet that fits the original network may no longer fit the tunnel's effective packet-size budget.

If the sender continues transmitting packets larger than the path can support, something has to happen.

The packet may be fragmented where allowed, rejected with appropriate feedback, or dropped under problematic conditions.

### Path MTU Discovery

Path MTU Discovery helps endpoints determine a packet size that can traverse the path.

For IPv4, traditional discovery uses the Don't Fragment flag and ICMP messages indicating that fragmentation would be required.

For IPv6, forwarding routers do not fragment packets. An oversized packet can trigger an ICMPv6 Packet Too Big message so the sender can adapt.

Modern transport implementations may also use packetization-layer discovery techniques.

The important principle is that the sender must learn or infer a usable packet size.

### The black-hole failure

Imagine an intervening firewall blocks the relevant ICMP feedback.

Small packets traverse the path successfully.

Larger packets are dropped because they exceed an actual MTU limit.

The sender doesn't receive the feedback necessary to reduce its packet size through the expected discovery mechanism.

It retransmits.

The application waits.

The connection appears to hang.

This is a Path MTU black-hole pattern.

### Why TCP handshake success is misleading

A TCP handshake uses relatively small packets.

Those may fit through the path.

A subsequent HTTPS request or response may involve larger packets.

Those may fail.

Therefore, a successful connection handshake doesn't prove that normal payload transmission will work.

### TCP MSS

TCP endpoints advertise a Maximum Segment Size, or MSS.

MSS describes the maximum TCP payload size a peer is prepared to receive in a segment under the relevant conditions.

It relates to—but is not identical to—the IP MTU because IP and TCP headers also consume space.

Some network devices adjust advertised MSS values, often called MSS clamping, to help avoid packets that exceed an underlying path limit.

But MSS clamping isn't a universal cure for every protocol or MTU problem.

A correct diagnosis still matters.

## 15. Diagnosing the Payment Failure Systematically

Now let's imagine we know nothing about the cause.

We only know that the backend cannot contact the payment provider.

How should we investigate?

The most effective approach is to separate the connection into stages.

### Stage one: identify the destination

Which hostname does the application contact?

Which IP addresses does the resolver return?

Does the application prefer IPv4 or IPv6?

Is the selected destination the one we intended?

A DNS success doesn't establish routing, but it tells us which address the application is trying to reach.

### Stage two: identify the outbound route

Which route table applies to the backend subnet?

For the selected public IPv4 destination, is there a matching route toward a suitable egress mechanism?

If the private subnet only has its local VPC route, we've found a likely cause.

If it has a NAT gateway route, continue.

### Stage three: follow the gateway path

Is the NAT gateway healthy and configured appropriately?

For a public NAT gateway, does its public-subnet routing support internet access through the internet gateway?

Are its public addresses correctly configured?

Does the architecture introduce unexpected cross-zone dependencies?

A route to a broken or unavailable gateway is not useful merely because the route exists.

### Stage four: inspect filtering

Does the application's security group allow the outbound traffic?

Do subnet network ACL rules permit the required forward and return traffic?

Are there other firewalls, proxies, or inspection devices along the path?

Remember that security groups are stateful while network ACLs are stateless.

Their return-traffic behavior differs.

### Stage five: inspect translation and egress identity

Which public address does the payment provider see?

Does the provider allow that address?

Is NAT translation state being created?

Are NAT capacity metrics reporting port allocation failures or packet drops?

This is particularly important when failures appear only under concurrency.

### Stage six: inspect transport and application behavior

Does the TCP connection establish?

Does TLS negotiation succeed?

Does the provider return an HTTP response?

Does the application interpret that response correctly?

A payment-provider 403 response is different from a TCP timeout.

A TLS certificate failure is different from a missing route.

A correct diagnosis preserves these distinctions.

### Stage seven: verify the return path

If the outbound traffic appears to reach the provider but no response arrives, investigate return routing, NAT state, firewall behavior, and any asymmetric path.

The conversation is not complete merely because its first packet departed successfully.

## 16. The Observability Problem: What Each Tool Can Prove

A networking investigation becomes much stronger when each tool is used for a precise question.

### Route tables

Route tables show forwarding intent.

They tell you which next hop should handle a destination under the relevant routing rules.

They don't prove that the next hop works or that the application receives a response.

### VPC Flow Logs

AWS VPC Flow Logs can provide information about observed traffic flows associated with supported network interfaces or other configured scopes.

They can help answer questions about addresses, ports, traffic volume, and whether traffic was accepted or rejected by relevant controls according to their logging semantics.

But Flow Logs are not complete packet captures.

They don't contain the HTTP request body.

And the meaning of their records depends on where logging is enabled and which aggregation or metadata options are used.

### NAT gateway metrics

NAT gateway metrics can reveal connection-establishment activity, port allocation failures, packet drops, and other operational behavior.

An increase in `ErrorPortAllocation` is especially relevant when investigating connection-capacity pressure.

But a healthy NAT gateway doesn't prove that the payment provider accepted the application request.

### Packet captures

A packet capture can reveal transport-level behavior where capture access is available and authorized.

For example, it may show TCP SYN retransmissions or ICMP feedback.

But encryption prevents an ordinary passive capture from revealing protected HTTPS contents.

And packet-capture observations are specific to the point where traffic is captured.

A capture from inside a container may show private source addresses, while a capture outside a NAT boundary sees translated ones.

### Application logs

Application logs can show DNS resolution, connection attempts, TLS errors, HTTP status codes, and business operation identifiers.

But they may not reveal every intermediate network event.

A timeout log generally tells you that the application didn't receive an expected result within a time budget.

It doesn't automatically prove where the packet was lost.

### The practical rule

Use each observation to narrow the possible failure mechanisms.

Don't pretend that any one tool reveals the entire path.

**A useful diagnostic instrument answers one specific question. A good investigation combines those answers into a coherent explanation.**

## 17. Solving the Original Production Incident

We now have the necessary mental model to explain the hotel-booking outage.

The backend runs in a private subnet.

Its IPv4 address is `10.42.20.17`.

The payment provider resolves to a public IPv4 destination.

The backend has internal VPC connectivity, but its subnet route table lacks the intended outbound route toward a public NAT gateway or another suitable egress path.

Therefore, packets addressed to the payment provider cannot follow the expected route.

The application times out.

No payment-provider request arrives.

The team corrects the private subnet's route table to direct appropriate internet-bound IPv4 traffic toward the NAT gateway.

It verifies that the gateway is available and has a working path through the internet gateway.

It checks the relevant security group and network ACL behavior.

It confirms that the payment provider allows the platform's actual public egress address.

Then it performs an authorized payment-integration test and verifies the expected application-level response.

The network path works.

No change to the Node.js payment client was necessary.

### The deeper failure

The immediate cause was an incomplete outbound routing configuration.

But the organizational failure was broader.

The release checklist validated inbound API health and internal database connectivity.

It did not verify a critical outbound business dependency.

The team treated public ingress and private egress as though they were one property called "networking."

They aren't.

### The architectural improvement

The platform should document its required outbound dependencies.

Infrastructure configuration should be version-controlled and reviewed.

Deployment verification should include representative external connectivity and business checks without turning every liveness probe into a call to a third-party provider.

NAT gateway capacity and egress identity should be observable.

And important external integrations should have clear timeout, retry, and idempotency behavior.

A route-table change can be as consequential as a broken payment algorithm.

The infrastructure is part of the application.

## 18. The Oral Examination

Answer each scenario aloud before reading the solutions.

### Challenge 1 — The NAT Translation

A laptop at `192.168.1.42:53124` connects to `203.0.113.80:443`.

Its router translates the source to `198.51.100.24:62001`.

Describe the packet endpoints before translation, after translation, and after the response is translated back.

What information must the NAT device maintain?

### Challenge 2 — The Public Subnet Misconception

An EC2 instance is in a public subnet with a default route toward an internet gateway.

It has only a private IPv4 address.

A developer insists that anyone on the internet can connect directly to it.

What's wrong with that conclusion?

### Challenge 3 — The Private Backend

Customers can reach an application through a public load balancer.

The private backend can reach PostgreSQL.

But it cannot contact an external payment provider.

Name at least four distinct networking conditions that might explain the failure.

### Challenge 4 — The Stateless Firewall

A network ACL allows outbound TCP connections to destination port 443.

The backend still experiences connection timeouts.

Why might the return traffic fail?

### Challenge 5 — The New Public Address

Payment processing stops working immediately after a migration to a new NAT gateway.

The payment provider reports rejected connections from an unfamiliar public address.

What changed, and how should the platform manage that dependency?

### Challenge 6 — The NAT Saturation Incident

A security-scanning platform launches thousands of concurrent outbound connections.

Application CPU remains low, but new connections fail intermittently.

NAT gateway metrics show increasing port allocation errors.

What's happening, and what remedies would you consider?

### Challenge 7 — IPv6 Without NAT

A cloud instance has a globally unique IPv6 address.

Does that mean every internet host should be able to initiate a connection to it?

Explain how routing and security can provide outbound access without broad inbound exposure.

### Challenge 8 — The Large-Packet Mystery

TCP connections establish successfully.

Small HTTPS requests succeed.

Large transfers stall, particularly through a VPN.

What failure mechanism should you investigate, and why might ICMP handling matter?

## 19. Solutions and Discussion

### Solution 1 — NAT preserves a return mapping

Before translation, the source is `192.168.1.42:53124` and the destination is `203.0.113.80:443`.

After translation, the source is `198.51.100.24:62001`, while the destination remains the payment server.

The payment server replies to the translated public endpoint.

The NAT device uses its mapping state to restore the destination to `192.168.1.42:53124`.

The implementation must retain enough flow information to distinguish the connection from other translated traffic.

### Solution 2 — Public routing doesn't assign a public address

A subnet's route toward an internet gateway doesn't automatically give every EC2 instance direct public IPv4 reachability.

The instance also needs an appropriate public IPv4 addressing arrangement and permitted traffic under applicable security controls.

The application must be listening on the intended port.

A public load balancer can provide a public entry point for privately addressed backend instances without exposing those instances directly.

### Solution 3 — Multiple independent failures remain possible

The private subnet may lack a default route toward an egress gateway.

The NAT gateway may be unavailable or incorrectly routed.

A security group may deny outbound traffic.

A network ACL may block the forward or return path.

The provider may reject the public egress address.

NAT translation resources may be exhausted.

Or the problem may occur later at TCP, TLS, or HTTP layers.

Inspect the actual path rather than assuming that working internal connectivity proves working internet egress.

### Solution 4 — NACLs are stateless

A network ACL doesn't automatically allow return traffic for previously permitted outbound connections.

The response travels toward the client's appropriate return port, often an ephemeral port or a translated endpoint depending on the path.

The relevant inbound rules must permit that traffic.

This differs from ordinary security-group behavior, which is stateful.

### Solution 5 — Egress identity changed

The new NAT gateway may use a different public egress address.

An external allowlist may reject it.

The platform should identify and document every legitimate public egress address, coordinate changes with the provider, and verify access after infrastructure migrations.

For high-availability designs, account for multiple gateways and their public identities.

### Solution 6 — NAT mapping capacity is constrained

Large numbers of concurrent connections can exhaust usable translation resources for particular destination combinations.

Port allocation failures are direct evidence of that problem.

Possible remedies include reducing connection churn, using connection pooling appropriately, bounding concurrency, distributing load across suitable gateways, or increasing supported NAT address capacity.

Adding application replicas without examining egress resources may make the incident worse.

### Solution 7 — Global addresses don't imply unrestricted inbound access

The instance may have a globally unique IPv6 address while being protected by security-group rules, network ACLs, and appropriate routing arrangements.

An AWS egress-only internet gateway can provide outbound IPv6 connectivity with corresponding return traffic while preventing unsolicited inbound connections through that gateway.

The security boundary is expressed by routing and policy, not by requiring address-sharing NAT.

### Solution 8 — Investigate Path MTU Discovery

A tunnel can reduce the effective packet-size budget.

Large packets may be discarded when they exceed a link's MTU.

If the sender doesn't receive the appropriate ICMP feedback, it may continue transmitting oversized packets.

This can produce a Path MTU black hole.

Small connection-establishment packets still succeed, while larger application transfers stall.

Inspect MTU, MSS, tunnel encapsulation, ICMP feedback, and relevant transport behavior.

## 20. The Mental Model Worth Keeping

Cloud networking becomes much easier to reason about when you separate five responsibilities.

**Addressing** determines which source and destination identities packets use.

**Routing** determines where packets are forwarded.

**Translation** changes addressing information when traffic crosses particular network boundaries.

**Filtering** determines which traffic is permitted.

**Transport and application protocols** determine whether the endpoints successfully establish and complete the intended conversation.

An internet gateway isn't a NAT gateway.

A public subnet doesn't automatically make every instance public.

A security group isn't a route table.

A NAT gateway doesn't replace application authentication.

And a successful TCP handshake doesn't prove that large payloads will traverse the network.

Whenever an outbound connection fails, ask:

**Which address was selected? Which route applies? Which translation occurs? Which policies permit the traffic? Can the response return?**

Those five questions are far more useful than memorizing cloud-console screenshots.

## 21. Next Lecture — CS230-L07: The Life of a Network Connection

We've now followed packets through private and public networks.

We understand why NAT translates addresses, how stateful gateways preserve return traffic, and why cloud routes and security controls must align.

But what actually happens when two application processes begin communicating?

How does a TCP connection become established?

How can one server handle thousands of simultaneous connections on port 443?

What happens when a peer disappears without closing its socket?

Why can an apparently healthy connection fail only after a long idle period?

And why does retrying an operation after a connection failure sometimes create duplicate business effects?

In the next lecture, **The Life of a Network Connection**, we'll examine sockets, TCP connection establishment, reliable byte streams, buffering, connection termination, timeouts, and the uncertainty that arises when one participant stops hearing from another.

We've built the network path.

Now the applications need to have a conversation.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — The Private Network and NAT Workbench

These exercises focus on observation and simulation. They do not require an AWS account, production credentials, or changes to cloud routing.

Do not modify shared VPC route tables, NAT gateways, security groups, or firewalls merely to reproduce a failure.

### Lab A — Inspect your computer's route toward the internet

On Linux, inspect the selected IPv4 route:

```bash
ip -4 route
ip route get 1.1.1.1
```

On macOS:

```bash
netstat -rn -f inet
route -n get 1.1.1.1
```

On Windows PowerShell:

```powershell
Get-NetRoute -AddressFamily IPv4
Find-NetRoute -RemoteIPAddress 1.1.1.1
```

The address is used only as a route-selection example.

Identify the selected interface and next hop.

**Question:** Does the route reveal whether a NAT device exists farther along the path?

Not necessarily. Your operating system may see only the next local gateway.

### Lab B — Compare private and public addressing

Inspect your local addresses.

On Linux:

```bash
ip -br address
```

On macOS:

```bash
ifconfig
```

On Windows:

```powershell
Get-NetIPAddress
```

Identify whether the assigned addresses belong to RFC 1918 ranges, IPv6 link-local space, globally unique IPv6 space, or other special-use categories.

If you use a public IP-discovery service you trust, compare the address reported by that service with your local interface addresses.

**Question:** Why might they differ?

### Lab C — Simulate a NAT translation table

Create `nat_simulation.py`.

This is a conceptual simulation, not an implementation of a real NAT device. It demonstrates how multiple private clients can share one public address through distinct translated ports.

```python
public_ip = "198.51.100.24"
next_public_port = 62000

translations = {}

def translate_outbound(private_ip, private_port, destination_ip, destination_port):
    global next_public_port

    public_port = next_public_port
    next_public_port += 1

    translations[(public_ip, public_port)] = {
        "private": (private_ip, private_port),
        "destination": (destination_ip, destination_port),
    }

    print(
        f"{private_ip}:{private_port} -> "
        f"{public_ip}:{public_port} -> "
        f"{destination_ip}:{destination_port}"
    )

    return public_port

def translate_return(public_port):
    mapping = translations.get((public_ip, public_port))

    if mapping is None:
        print("No matching translation")
        return

    print("Return destination:", mapping["private"])

first = translate_outbound(
    "192.168.1.42", 53124,
    "203.0.113.80", 443
)

second = translate_outbound(
    "192.168.1.43", 53124,
    "203.0.113.80", 443
)

translate_return(first)
translate_return(second)
translate_return(63000)
```

Run:

```bash
python nat_simulation.py
```

Explain why two internal clients can use the same local source port without confusing the public-side mapping.

Then answer:

What happens if the NAT device loses the translation table?

What would happen if the simulated external port pool were exhausted?

### Lab D — Design an AWS VPC

Consider this fictional application:

VPC: `10.42.0.0/16`

Public subnet A: `10.42.0.0/24`

Private application subnet A: `10.42.20.0/24`

Private database subnet A: `10.42.40.0/24`

The application needs an internet-facing load balancer, private backend instances, a database, and outbound HTTPS access to a payment provider.

Design the required IPv4 routes.

A useful starting point is:

```text
PUBLIC SUBNET ROUTE TABLE

Destination     Target
10.42.0.0/16    local
0.0.0.0/0       internet gateway


PRIVATE APPLICATION ROUTE TABLE

Destination     Target
10.42.0.0/16    local
0.0.0.0/0       public NAT gateway


PRIVATE DATABASE ROUTE TABLE

Destination     Target
10.42.0.0/16    local
```

Explain why this design allows the backend to reach the payment provider without making the backend itself directly publicly addressed.

Then describe which security-group rules would be appropriate between the load balancer, backend, and database.

### Lab E — Investigate five networking failures

For each scenario, state the first two or three observations you would collect.

**Scenario A:** A private backend resolves an external hostname but cannot establish a connection.

**Scenario B:** The backend reaches the payment provider, but the provider rejects requests from an unfamiliar public IP.

**Scenario C:** Outbound connections work at low concurrency but fail under a large burst. NAT port allocation errors rise.

**Scenario D:** A security-group rule allows outbound HTTPS, but a restrictive network ACL prevents successful return traffic.

**Scenario E:** Small requests work through a VPN, but larger transfers hang.

Identify the different mechanisms involved. Don't answer all five with "check the firewall."

### Lab F — Compare IPv4 and IPv6 connectivity

On a machine with both address families available, and against an endpoint you are authorized to test, compare:

```bash
curl -4 -I https://YOUR-TEST-HOST/
curl -6 -I https://YOUR-TEST-HOST/
```

If one family is unavailable locally, record that limitation rather than assuming the server is broken.

**Question:** Why doesn't success over IPv4 prove that IPv6 routing or firewall configuration is correct?

### Lab G — Diagnose the MTU problem on paper

Consider this fictional network path.

```text
Laptop Ethernet IP MTU:       1500 bytes
VPN encapsulation overhead:     80 bytes
Effective inner-packet budget: 1420 bytes
```

Suppose the application sends packets that were constructed assuming a 1500-byte usable path.

Some exceed the tunnel's effective packet-size budget.

Explain:

1. Why small packets might work.
2. Why the sender needs an appropriate packet-size adaptation mechanism.
3. What can happen if oversized-packet feedback is blocked.
4. Why disabling all ICMP traffic is dangerous.
5. Why TCP MSS adjustment may help certain flows without solving every possible MTU problem.

### Lab H — Write the payment incident report

Prepare a short engineering incident report.

Include:

- Customer impact.
- The first failed network boundary.
- Why inbound requests and internal database access continued working.
- The missing egress configuration.
- How translation and public egress identity should operate.
- The security checks needed after repairing the route.
- How the team verified recovery.
- Which deployment check should prevent the same failure.

Do not claim the problem is solved merely because the NAT gateway exists.

Establish the complete path and the application's successful interaction with the external provider.

---

## Further Reading

1. [RFC 1918 — Address Allocation for Private Internets](https://www.rfc-editor.org/rfc/rfc1918.html) — Private IPv4 address ranges.
2. [RFC 6598 — Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598.html) — Carrier-grade NAT addressing.
3. [RFC 4787 — NAT Behavioral Requirements](https://www.rfc-editor.org/rfc/rfc4787.html) — Mapping and filtering behaviors for UDP NAT.
4. [AWS — Subnet Route Tables](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html) — Forwarding and route associations.
5. [AWS — NAT Gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) — NAT gateway architecture and public/private variants.
6. [AWS — NAT Gateway Metrics](https://docs.aws.amazon.com/vpc/latest/userguide/metrics-dimensions-nat-gateway.html) — Port allocation, traffic, and error metrics.
7. [AWS — Network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html) — Stateless subnet filtering.
8. [AWS — Egress-Only Internet Gateways](https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html) — Outbound-only IPv6 access.
9. [RFC 1191 — Path MTU Discovery](https://www.rfc-editor.org/rfc/rfc1191.html) — IPv4 Path MTU mechanisms.
10. [RFC 8201 — Path MTU Discovery for IPv6](https://www.rfc-editor.org/rfc/rfc8201.html) — IPv6 Packet Too Big behavior and discovery.

---

## Dense Cheatsheet — Interview Glance Card

*The final reference is fenced for rapid screen-based revision.*

```text
CS230-L06 — PRIVATE NETWORKS, NAT, AND CLOUD REACHABILITY

RFC 1918 PRIVATE IPv4

10.0.0.0/8
172.16.0.0/12
192.168.0.0/16

Shared address space:
100.64.0.0/10 (RFC 6598, often CGNAT)

Private IPs can be reused by independent networks.
Ordinary public internet routing does not reach arbitrary RFC 1918 hosts.

SOURCE NAT

Before:
  192.168.1.42:53124 -> 203.0.113.80:443

After:
  198.51.100.24:62001 -> 203.0.113.80:443

Return:
  203.0.113.80:443 -> 198.51.100.24:62001
  NAT maps back to 192.168.1.42:53124

NAPT / PAT
  Translates address + transport port
  Allows many private flows to share public IPv4

NAT STATE

Tracks mappings / connection context
Has finite resources and timeouts
Mapping expiry can break long-idle traffic
Port exhaustion can prevent new flows

DNAT

Rewrites destination information
Used for inbound port forwarding
Not inherently a firewall policy

DISTINCT FUNCTIONS

Routing:
  Where does traffic go?

NAT:
  How is addressing translated?

Firewall:
  Is traffic permitted?

Proxy:
  How is application or connection traffic mediated?

Load balancer:
  Which destination receives traffic?

AWS VPC

VPC:
  Virtual network with configured address range

Public subnet:
  Route table has appropriate internet-gateway route

Private subnet:
  No ordinary direct IGW IPv4 route

Public subnet != every instance publicly reachable

DIRECT PUBLIC EC2 IPv4 ACCESS

Requires:
  Suitable public IPv4 association
  Internet-gateway routing
  Permissive relevant security rules
  Listening service

PUBLIC INGRESS ARCHITECTURE

Internet
  -> Internet-facing load balancer
  -> Private backend
  -> Private database

Private backend does not need direct public IPv4.

PRIVATE IPV4 EGRESS

Backend
  -> Private subnet default route
  -> Public NAT gateway
  -> Internet gateway
  -> External service

Private route:
  0.0.0.0/0 -> NAT gateway

Public NAT subnet route:
  0.0.0.0/0 -> Internet gateway

AWS PUBLIC NAT GATEWAY

Uses private address within VPC
Public egress via associated Elastic IP / IGW mapping
Stateful translation of return traffic

NAT GATEWAY OBSERVABILITY

ErrorPortAllocation
  Failed source-port allocation

PacketsDropCount
  Dropped packets

Connection/idle metrics
  Useful for egress-capacity investigations

More application replicas can increase NAT pressure.

EGRESS IDENTITY

Payment providers may allowlist public source IPs.
New NAT gateway can change public egress address.
Multiple AZ NAT gateways can mean multiple addresses.
Predictable egress may be business-critical.

SECURITY GROUPS

Stateful
Associated with supported resource interfaces
Tracks permitted connection return traffic
No explicit mirrored return rule normally needed

NETWORK ACLS

Stateless
Subnet boundary
Ordered allow/deny rules
Return traffic must be permitted separately
Ephemeral ports matter

ASYMMETRIC ROUTING

Forward and return paths may differ.
Stateful devices must receive relevant flow traffic
or support appropriate state coordination.

IPv6

128-bit addressing
Global unicast can avoid IPv4 address-sharing NAT
Global address != unrestricted inbound access
Firewall and routing policies still apply

AWS IPv6 egress-only internet gateway:
  ::/0 -> egress-only IGW
  Permits outbound + return traffic
  Blocks ordinary unsolicited inbound via gateway

NAT64 / DNS64:
  Can support IPv6-only clients reaching IPv4 services
  Different from normal IPv6-to-IPv6 communication

MTU

Maximum Transmission Unit:
  Maximum packet size for relevant link/layer

Path MTU:
  Limited by smallest path segment

VPN / tunnels add encapsulation overhead.

PATH MTU DISCOVERY

IPv4:
  DF flag + ICMP fragmentation-needed feedback

IPv6:
  Routers don't fragment
  ICMPv6 Packet Too Big feedback

Blocked feedback can create MTU black holes.

SYMPTOM

Small requests work
Large transfers hang
TCP handshake succeeds

Investigate:
  MTU
  MSS
  Encapsulation
  ICMP feedback
  Packet-size adaptation

CONNECTIVITY INVESTIGATION

1. Which destination IP was selected?
2. Which subnet route applies?
3. Is the gateway path usable?
4. Does NAT translation exist?
5. Which filtering rules apply?
6. Can the provider accept the public egress IP?
7. Can return traffic reach the correct mapping?
8. Does TCP/TLS/HTTP complete?

TOOLS AND EVIDENCE

Route tables:
  Forwarding intent

VPC Flow Logs:
  Observed traffic metadata / accept-reject indicators

NAT metrics:
  Translation capacity and traffic issues

Packet capture:
  Transport packets at one observation point

Application logs:
  Connection, TLS, HTTP and business results

No one tool proves end-to-end success.

SENIOR MENTAL MODEL

Address -> Route -> Translation -> Permission
        -> Transport -> Application -> Return path

SENIOR LINE

  "Private addressing, internet routing, NAT, and firewall
   policy are independent parts of reachability. I trace
   the actual forward and return paths, verify egress identity
   and stateful translation, and use application-level evidence
   to confirm that connectivity is genuinely restored."
```
