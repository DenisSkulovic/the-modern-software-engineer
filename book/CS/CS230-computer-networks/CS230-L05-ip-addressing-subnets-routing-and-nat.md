---
id: CS230-L05
course: CS230
title: "IP Addressing, Subnets, Routing, and NAT"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS230-L04
next: CS230-L06
---

# CS230 — Computer Networks and Web Protocols

## Lecture 05: IP Addressing, Subnets, Routing, and NAT

*How a packet escapes your laptop, navigates thousands of networks, reaches a private cloud server, and somehow finds its way home.*

---

# 1. The Packet That Had Nowhere to Go

Imagine you're the backend engineer responsible for a hotel-booking platform.

The application has recently migrated to AWS. Its frontend is served through a CDN, incoming API traffic passes through a public load balancer, and the actual backend containers operate inside private subnets.

The architecture appears sensible. Customers can search hotels, inspect availability, and retrieve their existing reservations.

Then the payment flow fails.

The backend needs to contact an external payment provider. The application sends an HTTPS request, waits, and eventually times out. The payment provider reports that it hasn't received the request.

You check the obvious things. DNS resolution succeeds. The backend process is running. CPU utilization is low. The provider's API works perfectly from your laptop.

Someone suggests increasing the request timeout. Someone else wants to restart the containers. A third engineer wonders whether the TLS certificate has expired.

But the problem isn't inside the application, DNS, or TLS.

The application is trying to send a packet toward the public internet, and the network has no valid way to deliver it.

Somewhere in your cloud configuration, a route is missing.

To understand why that small configuration detail can render a perfectly functional application useless, we need to answer a question developers encounter constantly but rarely examine properly.

**How does an IP packet actually travel from one computer to another?**

In CS230-L04, we studied how DNS helps applications discover network destinations. Now we have an address, but an address is only a destination. It doesn't tell us how to reach it.

We'll begin with an ordinary laptop on Wi-Fi, follow its packets toward a cloud-hosted application, and eventually return to our broken payment integration.

Along the way, we'll investigate IP addresses, subnet masks, local networks, default gateways, routing tables, MAC addresses, network address translation, and IPv6.

These are not obscure topics reserved for network administrators. They determine whether your backend can reach a database, whether a container can access an external API, why two VPNs sometimes conflict, and why exposing a port doesn't necessarily make a service reachable.

By the end, you should be able to look at a network configuration and reason about what traffic can reach what destination, which device makes each decision, and where an apparently mysterious connection failure might originate.

---

# 2. An IP Address Is Not Quite What You Think It Is

Let's begin with a familiar address:

`192.168.1.42`

Most developers recognize it as a private IPv4 address, probably belonging to a laptop, phone, or another device on a home network.

But what does that address actually represent?

An IP address is a logical address assigned to a network interface. More precisely, it identifies an interface or endpoint within an IP addressing and routing context.

It isn't necessarily a permanent identity for a physical machine.

Your laptop might have one IPv4 address on Wi-Fi, another on a corporate VPN, and one or more IPv6 addresses. A cloud server might have multiple addresses attached to different network interfaces.

Conversely, one public IP address might represent traffic from hundreds of devices through network address translation. We will discover exactly how that works shortly.

The first misconception to eliminate is that an IP address uniquely identifies a computer in the way a passport identifies a person.

It doesn't.

It is closer to a network location that can be assigned, changed, shared through translation, or made reachable through different routing arrangements.

## 2.1 IPv4 addresses are 32-bit numbers

IPv4 addresses contain 32 bits.

The familiar dotted-decimal representation divides those bits into four groups of eight. Each group is called an octet, with values ranging from zero to 255.

So `192.168.1.42` is simply a convenient human-readable representation of one 32-bit value.

Thirty-two bits provide approximately 4.29 billion distinct numerical addresses.

That sounds like a lot until you consider the number of smartphones, laptops, servers, routers, cameras, virtual machines, and other connected devices in the world.

Furthermore, not every IPv4 address can be assigned to an ordinary public internet endpoint. Large portions of the address space have special purposes, and address allocation does not permit every address to be used interchangeably.

IPv4 address scarcity is one of the reasons private addressing, NAT, and eventually IPv6 became so important.

But before discussing public and private addresses, we need to understand something more fundamental.

An IP address is not just an arbitrary number assigned to a device. Its relationship to other addresses helps the network determine where packets should travel.

That relationship is expressed through **network prefixes**.

---

# 3. Subnets: Dividing the Address Space into Neighborhoods

Imagine a residential city with thousands of buildings.

If every piece of mail required a search through every apartment in the entire city, delivery would be extraordinarily inefficient.

Instead, addresses have structure. Streets, districts, and postal codes allow delivery systems to narrow the destination progressively.

IP networking uses a related principle.

An IP address can be understood in relation to a network prefix, which identifies a block of addresses.

That block is commonly called a **subnet** when discussing the smaller networks into which a larger address space has been divided.

A subnet allows devices and routers to distinguish destinations considered locally reachable from those requiring another network hop.

## 3.1 Understanding CIDR notation

Suppose your laptop receives this configuration:

`192.168.1.42/24`

The slash and number are called CIDR prefix notation. CIDR stands for Classless Inter-Domain Routing.

The number after the slash indicates how many leading bits belong to the network prefix.

In this example, 24 of the 32 IPv4 bits are fixed by the network prefix. The remaining eight bits distinguish addresses within that block.

The resulting network is:

`192.168.1.0/24`

Because eight bits remain variable, the block contains 256 IPv4 addresses.

These range from `192.168.1.0` through `192.168.1.255`.

In a conventional IPv4 subnet, the first address identifies the network and the last is the subnet-directed broadcast address. That leaves 254 addresses normally available for host assignment.

There are exceptions to this familiar convention, particularly for special-purpose point-to-point and host routes, and cloud providers may reserve additional addresses within their subnets.

But for ordinary small-network reasoning, the basic model is useful.

Your laptop at `192.168.1.42` belongs to the same slash-24 subnet as a printer at `192.168.1.80`.

A server at `192.168.2.20`, however, belongs to a different slash-24 subnet.

That difference determines whether your laptop normally attempts direct local delivery or sends the packet toward a router.

## 3.2 Why the subnet mask matters

You may have encountered subnet masks such as:

`255.255.255.0`

This is simply another representation of a slash-24 IPv4 prefix.

In binary, the mask contains 24 leading ones, followed by eight zeros.

The ones select the network portion. The zeros identify the bits available to vary within that network.

A device can apply the mask to an address using a bitwise AND operation to obtain the associated network prefix.

For example, applying the slash-24 mask to `192.168.1.42` produces the network address `192.168.1.0`.

Now compare two addresses:

`192.168.1.42` and `192.168.1.200`.

When both are interpreted using the same slash-24 mask, their network portions match.

The host can therefore treat the destination as belonging to its directly connected network, assuming the network's actual link topology and configuration support that relationship.

Compare that with `192.168.2.20`.

The network portions differ. The host needs some route toward another network.

This isn't merely mathematical trivia. The network prefix influences an actual forwarding decision.

## 3.3 A subnetting example with smaller networks

Suppose your office has a slash-24 network containing 256 addresses, but you want to separate employees, laboratory machines, and guest devices.

You can divide the address space into smaller prefixes.

For example, consider:

`192.168.1.128/26`

A slash-26 prefix fixes 26 bits and leaves six bits variable.

Two to the power of six equals 64, so the subnet contains 64 addresses.

Its range runs from `192.168.1.128` through `192.168.1.191`.

For conventional IPv4 host addressing, `192.168.1.129` through `192.168.1.190` are usable host addresses.

Notice something interesting. The slash notation expresses a mathematical address range, not a particular number of physical computers.

A slash-26 subnet doesn't require 62 machines to exist. It merely describes an address block capable of supporting an appropriate allocation of endpoints.

You might place only six devices in that subnet.

The subnet still defines the same address boundaries.

### The key calculation

For IPv4, the total number of addresses in a prefix is:

**Two raised to the power of 32 minus the prefix length.**

A slash-24 contains 256 addresses. A slash-26 contains 64. A slash-30 contains four.

A slash-32 identifies a single address, which is useful for host-specific routes.

It is tempting to memorize a table of prefix lengths and host counts, but understanding the relationship is more valuable. You can reconstruct the answer rather than relying on memory.

## 3.4 Why subnets exist beyond address organization

Subnets aren't merely a way to avoid wasting addresses.

They establish meaningful network boundaries.

In an ordinary Ethernet-style LAN, devices within the same IP subnet can often communicate directly at the link layer. Communication to another subnet typically requires routing.

This provides opportunities for network segmentation, different routing policies, broadcast-domain organization, and security controls.

An organization might separate office workstations from database servers, for example.

The mere existence of separate subnets doesn't automatically secure the database. If a router forwards all traffic freely between them, the separation provides little access protection.

Security requires actual filtering and authorization policies.

Still, subnetting supplies a useful structural foundation for designing those boundaries.

This will become especially important when we investigate cloud VPCs, where subnets, route tables, and network-security rules work together.

---

# 4. The First Decision: Is the Destination Local?

Our laptop is connected to Wi-Fi in Vilnius.

Its IPv4 address is `192.168.1.42/24`.

The hotel's public API is available through a destination address represented by `203.0.113.80`.

For this lecture, we'll use addresses from the documentation-only ranges reserved for examples. They illustrate the mechanisms without referring to actual public services.

The browser needs to establish an HTTPS connection to the API.

Before any packet leaves the machine, the operating system must decide which network interface and next hop should receive it.

The operating system consults its **routing table**.

## 4.1 What the routing table contains

A routing table contains rules associating destination prefixes with forwarding decisions.

Some routes describe networks directly reachable through a particular interface.

Others identify a **next-hop router** that can forward packets toward the destination.

And one especially important route handles destinations that don't match a more specific rule.

This is the **default route**.

For IPv4, the default prefix is written as `0.0.0.0/0`.

A prefix length of zero means no leading destination bits are fixed. Consequently, every IPv4 destination matches that prefix.

But this doesn't mean the default route always wins.

Routing normally uses a principle called **longest-prefix matching**.

The most specific matching destination prefix takes precedence, subject to the router's forwarding policies and tie-breaking rules.

## 4.2 Longest-prefix matching

Imagine our laptop has three relevant routes.

One says that destinations in `192.168.1.0/24` are directly reachable through Wi-Fi.

Another says that destinations in `10.42.0.0/16` should go through a VPN interface.

The third is the default route, sending all otherwise unmatched IPv4 traffic toward the home router at `192.168.1.1`.

Now consider three destinations.

A packet addressed to `192.168.1.80` matches the local slash-24 route. The laptop attempts delivery within the local network.

A packet addressed to `10.42.20.17` matches the VPN slash-16 route, which is more specific than the default route.

And a packet addressed to `203.0.113.80` matches neither of those specialized routes. The default route wins.

The operating system therefore decides to send the packet to the home router at `192.168.1.1`.

Notice the subtlety.

The final destination is still `203.0.113.80`.

The gateway at `192.168.1.1` is merely the next stop.

This is the distinction between a **destination** and a **next hop**.

A router doesn't need to be the machine you ultimately want to contact. It only needs to know a useful way of forwarding the packet toward that destination.

## 4.3 Where do these routes come from?

You probably didn't enter your laptop's IP address, subnet mask, gateway, and DNS resolver manually.

In many IPv4 networks, these settings come from **DHCP**, the Dynamic Host Configuration Protocol.

When your laptop joins Wi-Fi, it can obtain an address lease and related configuration information, such as a subnet mask, default gateway, and DNS server addresses.

The details depend on the network and operating system. Addresses and routes can also be configured manually, supplied by VPN software, or installed through other mechanisms.

A familiar DHCP exchange is often summarized as Discover, Offer, Request, and Acknowledge.

For today's purposes, what matters is the outcome.

Your laptop learns not merely who it is on the local network but also where to send packets intended for destinations outside that network.

If DHCP provides an incorrect default gateway, local communication may work perfectly while internet access fails.

If DHCP supplies a correct gateway but incorrect DNS information, connecting by IP address might work while connecting by hostname fails.

These are different failures, despite producing a similar user experience: "The internet is broken."

---

# 5. ARP and MAC Addresses: Getting the Packet to the Gateway

Our laptop has decided to send the packet toward its default gateway.

But something is missing.

It knows the gateway's IP address: `192.168.1.1`.

How does it actually transmit data to that device over the local network?

This is where we encounter the distinction between IP addressing and **link-layer addressing**.

## 5.1 Two kinds of addresses with different responsibilities

An IP address helps identify a destination within a routed network.

A MAC address, in an Ethernet-style network, identifies a link-layer interface for local frame delivery.

These addresses are not interchangeable.

IP is concerned with communication across potentially many networks.

Ethernet MAC addressing is concerned with delivering frames over a local link-layer domain.

If your laptop wants to communicate with a remote web server, it generally doesn't need to discover that server's Ethernet MAC address.

In fact, that MAC address would not be meaningful for forwarding a packet across the entire internet.

Your laptop needs to know the link-layer destination for the **next local hop**.

In our example, that is the home router.

## 5.2 Address Resolution Protocol

For ordinary IPv4 Ethernet-style communication, the operating system can use **ARP**, the Address Resolution Protocol.

ARP associates an IPv4 address with a link-layer hardware address on the local network.

Conceptually, the laptop asks:

"Who has IPv4 address 192.168.1.1? Tell me your MAC address."

The appropriate device responds with the relevant link-layer address.

The laptop can cache that information in a neighbor or ARP table.

Now it can transmit a frame addressed to the gateway's MAC address, carrying an IP packet whose destination remains `203.0.113.80`.

This distinction is easy to miss but absolutely central.

The link-layer destination is the gateway.

The IP-layer destination is the remote server.

The first determines where the current local frame goes. The second is what the router uses to decide where the enclosed IP packet should travel next.

## 5.3 What changes at each router?

Imagine placing the IP packet inside a local delivery envelope.

The laptop sends the envelope to the home router.

The router receives the frame, extracts the IP packet, examines the destination address, and determines its next hop.

It then forwards the packet using the appropriate link-layer framing for the next connection.

On ordinary Ethernet links, that means a new Ethernet frame with link-layer source and destination addresses relevant to that hop.

The same process can repeat across numerous routers.

The link-layer envelope changes from hop to hop.

The IP packet retains its ultimate destination across ordinary forwarding, although routers modify certain network-layer fields and NAT devices may rewrite addresses.

This is how the internet avoids requiring every device to know every other device's hardware address.

The laptop only needs local neighbor information and a route toward its destination.

The next router performs its own forwarding decision.

And so on.

### What about Wi-Fi?

Real Wi-Fi framing has its own link-layer details, which are not identical to ordinary Ethernet framing.

But the architectural principle remains.

Local network protocols deliver information to the next reachable device, while IP provides the addressing and forwarding model for communication across multiple networks.

For application engineers, the critical separation is **local delivery versus routed delivery**.

---

# 6. Routing: How the Internet Avoids Needing One Giant Map

The packet has reached our home router.

What happens next?

The router examines the destination IP address and uses its forwarding information to select an outgoing interface or next hop.

Perhaps the next destination is an ISP router. From there, the packet may travel through several networks before reaching the infrastructure hosting our application.

Each routing device repeats a variation of this decision.

It does not normally need to understand that the packet belongs to a hotel-booking application, that the request is a payment operation, or that its payload may eventually contain JSON.

Those details belong to higher protocol layers.

## 6.1 Routers don't forward based on geography alone

Suppose our laptop is in Vilnius and the destination server is in Frankfurt.

You might expect packets to follow something resembling the shortest geographical route.

But internet routing is not simply Google Maps for packets.

The physical topology of networks matters, but so do commercial relationships, network policies, provider agreements, failures, traffic engineering, and available routes.

A provider might prefer one upstream network over another even when the preferred route is geographically longer.

Two packets sent to the same destination at different times might travel through different paths.

Indeed, even simultaneous traffic can use different paths when networks employ load balancing across multiple forwarding options.

So an IP route is fundamentally a forwarding decision, not a promise about geographical distance.

## 6.2 Routing within networks and between networks

Large networks are often divided into administrative domains called **autonomous systems**, or ASes.

An internet service provider may operate an autonomous system. A major cloud provider may operate one or more. Large enterprises may also have their own autonomous systems.

Within an autonomous system, routing can use internal routing protocols and network-specific policies.

Between autonomous systems, the internet relies heavily on **BGP**, the Border Gateway Protocol.

BGP allows participating networks to exchange reachability information about IP prefixes under defined policies.

For example, a network may advertise that it can provide a path toward a particular public IP prefix.

Other networks can use these announcements, together with their own routing policies, to determine how to forward traffic toward that prefix.

BGP is not simply a protocol that calculates the geographically shortest path.

It is a policy-driven mechanism for exchanging reachability information between networks.

### Control plane versus data plane

Here is a particularly valuable distinction.

The **control plane** is responsible for discovering, calculating, and maintaining information about available routes.

The **data plane** is responsible for forwarding actual packets according to the resulting forwarding information.

BGP and other routing protocols help build that knowledge.

Once appropriate forwarding entries exist, routers can process large volumes of packets without conducting an entire route-discovery conversation for each one.

In practical terms, when a packet arrives, the router performs a forwarding lookup. It doesn't call neighboring routers to ask for directions every time.

That separation is one of the reasons large-scale packet forwarding can operate at extraordinary speeds.

## 6.3 The TTL: Preventing packets from wandering forever

What if routers contain a mistake?

Imagine two routers that each believe the other provides the correct route to a destination.

A packet could bounce between them indefinitely.

IP has a mechanism that limits this possibility.

IPv4 packets contain a **Time to Live**, or TTL, field.

Despite the name, modern routers ordinarily treat it as a hop limit. Each forwarding router decreases the value by at least one.

If the value reaches zero, the packet is discarded.

A router may send an ICMP Time Exceeded message to the original sender.

IPv6 uses an explicitly named Hop Limit field for the corresponding purpose.

This is the mechanism behind classic traceroute-style investigations: send packets with deliberately limited hop counts and observe which devices report that the limit was exceeded.

But remember that not every router responds to diagnostic traffic, and receiving a response from an intermediate router doesn't necessarily reveal how quickly it forwards ordinary application packets.

Traceroute provides evidence about paths, not a perfect movie of every packet's journey.

---

# 7. Private IP Addresses: The Internet's Shared Interior Spaces

Our packet is moving toward the public internet, but something seems strange.

The laptop's source address is `192.168.1.42`.

Millions of other devices around the world might have exactly the same address.

How could an internet server distinguish them?

The answer begins with the difference between **private** and **public** IPv4 addressing.

## 7.1 The three private IPv4 ranges

RFC 1918 defines three important ranges for private use.

The first is `10.0.0.0/8`, covering addresses beginning with 10.

The second is `172.16.0.0/12`, covering addresses from `172.16.0.0` through `172.31.255.255`.

The third is `192.168.0.0/16`, covering addresses from `192.168.0.0` through `192.168.255.255`.

Private IPv4 addresses can be reused independently by different organizations.

Your home router may use `192.168.1.1`.

Your neighbor's router may use the same address.

A café in Berlin may use it, too.

That is perfectly acceptable because these addresses are meaningful within their respective private routing environments.

They are not globally unique destination identities on the public internet.

Ordinary internet routers don't provide global routing to those private address ranges.

There is an important subtlety here.

Private addresses are not inherently unable to participate in routing. They can be routed perfectly well inside organizations, VPNs, cloud networks, and other controlled environments.

What they lack is ordinary globally coordinated reachability on the public internet.

That is why a backend at `10.42.20.17` can communicate with another backend inside its VPC while being inaccessible directly from a random laptop elsewhere on the internet.

## 7.2 Why private addressing exists

Private addresses serve two major purposes.

They allow organizations to build internal networks without obtaining globally unique IPv4 addresses for every device.

And they support administrative separation between internal addressing and external internet connectivity.

Imagine a company with five thousand laptops, servers, printers, and virtual machines.

It doesn't necessarily want or need a separate publicly reachable IPv4 address for every device.

Private address ranges let the organization construct its own internal topology and control how that topology connects to external networks.

But this creates a problem.

When a private device needs to contact a public server, the public internet cannot simply route replies back to its private address.

Something has to bridge those two addressing worlds.

That something is frequently NAT.

---

# 8. NAT: How Hundreds of Devices Share One Public Address

Return to our laptop.

Its local address is `192.168.1.42`.

Its browser opens a TCP connection toward the remote API at `203.0.113.80`, port 443.

The operating system selects a temporary local source port. For illustration, let's call it port 53124.

The connection therefore begins with a source endpoint of `192.168.1.42:53124` and a destination endpoint of `203.0.113.80:443`.

This is a perfectly meaningful connection inside the laptop's private network.

But that private source address cannot be used as the return destination through the public internet.

The home router intervenes.

## 8.1 Source Network Address Translation

Assume the router has a public IPv4 address represented by `198.51.100.24`.

As our packet passes through the router, the router performs source address translation.

Instead of forwarding a packet whose source is `192.168.1.42`, it forwards a packet whose source is the router's public address.

In many home and enterprise configurations, the router also changes the source port.

For example, it might translate:

`192.168.1.42:53124`

into:

`198.51.100.24:62001`

The destination remains `203.0.113.80:443`.

This combination of address and transport-port translation is commonly called **Network Address and Port Translation**, or NAPT. Many engineers also call it Port Address Translation, or PAT.

In everyday conversation, the entire mechanism is usually called NAT.

The external API sees a connection originating from the translated public endpoint.

It generally has no knowledge that the real browser is running on a laptop at `192.168.1.42`.

## 8.2 The translation table

Here's the fascinating part.

The router has to remember what it did.

It maintains translation state associating the external connection with the appropriate internal endpoint.

When the API sends its response toward `198.51.100.24:62001`, the router consults that state.

It determines that this traffic belongs to the connection originating from `192.168.1.42:53124`.

The router then translates the destination information and forwards the response toward the laptop.

From the laptop's perspective, it has a conversation with the remote API.

From the API's perspective, it has a conversation with the router's public-facing address and port.

The NAT device maintains the mapping that makes the two perspectives compatible.

### Why source ports matter

Suppose another laptop on the same Wi-Fi network opens a connection to the same API.

Its local source might be `192.168.1.57:53124`.

Notice that both laptops can use the same local source port because they have different private IP addresses.

The router can allocate a distinct translated endpoint for the second connection.

For example, it might map the second laptop's traffic to public port 62002.

Now the remote API can send responses to different external ports, and the router can deliver them to the correct internal clients.

This is how thousands of simultaneous connections can share a relatively small pool of public IPv4 addresses.

The precise mapping behavior varies between NAT implementations. Some mappings depend on the remote destination as well as the local endpoint, and routers must manage port availability and protocol-specific connection state.

But the essential principle remains: the device maintains enough translation information to associate returning traffic with the original communication.

## 8.3 NAT is stateful—and that creates limitations

A NAT device cannot maintain an unlimited number of mappings.

Its tables consume memory, translated ports are finite, and mappings must eventually expire.

Busy gateways can run into port exhaustion or other state-management limits. This matters for cloud applications that open huge numbers of outbound connections to a small set of external destinations.

The translation device also needs suitable state when replies arrive.

For TCP, NAT implementations can use connection-related events and timers to manage mappings.

For UDP, where no equivalent connection handshake exists, translation state typically relies more heavily on traffic observations and idle timeouts.

This explains an otherwise puzzling class of bugs: a UDP application works for a while, remains idle, and then finds that traffic sent to an old mapped endpoint no longer reaches the original client.

The NAT mapping may have expired.

Protocol designers and application engineers sometimes need keepalives, connection establishment techniques, or relay services to cope with these realities.

We will explore TCP and UDP behavior more deeply in CS230-L06.

---

# 9. NAT Is Not a Firewall, and a Firewall Is Not a Route

This is one of the most useful distinctions in practical networking.

Imagine a company places an application server behind a NAT device.

An engineer announces that the server is secure because it uses a private IP address.

That's not a sufficient security argument.

NAT translates addressing information. A firewall enforces traffic-permission rules.

The two functions are frequently combined in home routers, but they solve different problems.

## 9.1 Why unsolicited inbound traffic usually fails

In the ordinary home-router scenario, outbound connections establish translation state.

A response matching an existing mapping can be forwarded back to the originating device.

But what if a stranger on the internet tries to initiate a new connection to the router's public IP address?

Without a suitable configured mapping or forwarding rule, the NAT device generally has no translation instructing it to deliver that connection to a particular private host.

The traffic may be discarded.

This behavior resembles a firewall in its visible effect, but NAT and firewall policy should not be treated as interchangeable security controls.

A network can use publicly routed addresses and still enforce strict stateful firewall policies.

And a NAT device can be deliberately configured to forward inbound connections to private hosts.

Translation alone doesn't express your complete security policy.

## 9.2 Destination NAT and port forwarding

Suppose you run a development server at `192.168.1.50`, listening on port 8080.

You want to make it accessible through a public port on your home router.

A port-forwarding rule can instruct the router to translate an incoming connection for a particular external port into a connection directed toward the internal server.

This is a form of **destination NAT**, commonly abbreviated DNAT.

The destination address and possibly the destination port are rewritten.

But several conditions still need to be satisfied.

The router must actually possess or have access to an externally reachable address. The upstream network must deliver inbound traffic to it. The forwarding rule must be correct. The server must be listening on the appropriate interface and port, and any applicable firewalls must permit the connection.

Opening a port in your application is only one piece of the chain.

### The `localhost` trap

Imagine your Node.js server listens on `127.0.0.1:8080`.

You configure a perfect router forwarding rule to the machine's LAN address.

The connection still fails.

Why?

Because `127.0.0.1` is a loopback address. A process listening only on that address is not automatically accepting connections arriving at the machine's Wi-Fi interface.

To accept remote connections, the server must listen on an appropriate reachable address, potentially including a wildcard bind such as `0.0.0.0`, and network policy must allow the traffic.

Of course, binding to all interfaces can broaden exposure. It should be an intentional engineering decision, not a universal fix.

## 9.3 Carrier-grade NAT: When your router isn't really public

There's another complication, increasingly relevant for residential and mobile internet.

Your home router may not actually possess a globally reachable public IPv4 address.

The ISP might place it behind another NAT system.

This is called **carrier-grade NAT**, often abbreviated CGNAT.

In such an arrangement, your household and many others may share public IPv4 addressing through a provider-operated translation layer.

The address assigned to your router's external interface might belong to the shared address range `100.64.0.0/10`, which was reserved specifically for this kind of use.

Or the provider might use another private addressing arrangement internally.

Why does this matter?

Because configuring port forwarding on your home router doesn't give you control over the ISP's translation device.

An unsolicited inbound packet must traverse every relevant translation and filtering boundary.

If the ISP doesn't provide an appropriate public mapping, your local forwarding rule cannot solve the problem by itself.

This is why some self-hosting enthusiasts discover that their home servers are inaccessible from the public internet even though every router setting appears correct.

Possible solutions include obtaining public addressing from the ISP, using IPv6 when available, establishing an outbound tunnel to a reachable relay, or using another suitable remote-access architecture.

The right solution depends on the network environment and security requirements.

---

# 10. Into the Cloud: Public Front Door, Private Application

Our original hotel-booking API is hosted on AWS.

Let's inspect a simplified architecture.

The company operates a VPC with an address range of `10.42.0.0/16`.

Within it, there are several smaller subnets.

The public-facing load balancer uses subnets with suitable internet routing.

Application containers reside in private subnets, perhaps within `10.42.20.0/24`.

Database instances occupy additional private subnets.

This arrangement allows the company to expose a controlled entry point while keeping most application infrastructure unreachable directly from the public internet.

## 10.1 Public and private subnet terminology

A common misunderstanding is that a subnet becomes public because its IP addresses somehow look public.

That's not how AWS uses the term.

For ordinary IPv4 VPC configurations, a subnet is considered public when its associated route table includes an appropriate route to an internet gateway.

A private subnet lacks that direct IPv4 route to an internet gateway.

The address assignment and resource configuration also matter.

A resource doesn't automatically become publicly accessible simply because its subnet has an internet-gateway route. It still needs appropriate public addressing and security permissions.

Similarly, a resource in a private subnet can communicate with other VPC resources or with external destinations through different routing mechanisms.

The distinction is about actual network reachability, not the psychological comfort of the labels.

## 10.2 The internet gateway and the load balancer

When a customer connects to the public API, their packets can reach an internet-facing load balancer through AWS's networking infrastructure.

The load balancer terminates or forwards traffic according to its configuration.

For an application load balancer performing HTTP and HTTPS proxying, the connection toward the backend is conceptually a separate connection from the customer's connection.

The load balancer selects an appropriate application target and sends traffic toward its private address.

For example, the backend container might be reachable at `10.42.20.17:3000`.

Notice that the public client doesn't need a direct route to the container's private address.

It communicates with the public front door.

The load balancer communicates with the private application.

The resulting architecture is more than simple address translation. A layer-seven reverse proxy understands application-level concepts such as HTTP hostnames, paths, request headers, and health checks.

That enables behaviors that ordinary IP forwarding and NAT do not provide.

## 10.3 Where did the customer's IP address go?

There is an interesting consequence of introducing a reverse proxy.

When the application receives the backend connection, the network-level source address may belong to the load balancer rather than the original customer.

Yet the application might need to know the customer's IP address for logging, security decisions, or rate limiting.

HTTP-aware proxies commonly forward client-address information through headers such as `X-Forwarded-For`.

But this introduces a trust problem.

An application must not blindly accept arbitrary forwarded-client headers from untrusted callers. Otherwise, a client might claim to originate from whichever address it prefers.

A robust system defines which reverse proxies are trusted and how the original client identity should be derived.

The larger lesson is that **each intermediary can change what the next system sees**.

A packet received by your backend is not necessarily the same packet sent by the customer's browser.

There may have been several independent connections, address translations, TLS terminations, and application-level forwarding decisions along the way.

That is why network architecture diagrams should distinguish routers, NAT gateways, load balancers, and reverse proxies.

They are not interchangeable boxes connected by arrows.

---

# 11. The Other Direction: Why Our Backend Cannot Reach the Payment Provider

Now return to the failure that opened the lecture.

The customer can reach the public load balancer.

The load balancer can reach the backend.

The backend can query its database.

But when the backend tries to contact the external payment provider, the request times out.

Why?

The application container lives in a private subnet. Its private IPv4 address is meaningful within the VPC but is not directly routable across the public internet.

It needs an appropriate outbound path.

## 11.1 The route table decides the next hop

Suppose the private subnet's route table contains only a route for the VPC's local address range.

That route permits appropriate local communication within the VPC.

So the backend can reach internal databases and other services.

But the payment provider has a public IPv4 address outside the VPC.

What route matches that destination?

If there is no suitable default or more specific route toward an external gateway, the traffic has no valid forwarding path.

The application may generate the request correctly, but correct application code cannot compensate for missing network routing.

This is the first lesson of our incident.

**A process can be healthy while its network environment makes a required operation impossible.**

## 11.2 Adding a NAT gateway for outbound IPv4

One common AWS solution is to configure an appropriate NAT gateway and route outbound IPv4 traffic from the private subnet through it.

For a regional deployment using a public NAT gateway, the architecture typically involves the private application's route toward the NAT gateway, followed by the NAT gateway's route through an internet gateway.

The NAT gateway translates the source addressing so the external payment provider can return traffic through the established mapping.

This allows the private application to initiate outbound connections without requiring a directly public IPv4 address for the application container.

But the NAT gateway is not simply a checkbox labeled "internet."

It must be provisioned correctly. The relevant routes must exist. Subnet associations must be correct. Security policies must permit the required traffic. Return traffic must be able to travel back through the configured networking path.

An incorrect route table can make a perfectly configured NAT gateway useless.

## 11.3 Route tables and firewalls answer different questions

Consider an outbound HTTPS request from our backend.

The route table answers: **where should this packet go next?**

A security group or firewall answers: **is this traffic permitted?**

Those are different decisions.

In AWS, security groups provide stateful filtering for supported resources. Network ACLs provide another layer of subnet-associated filtering and are stateless in their rule behavior.

A route might correctly direct traffic toward the NAT gateway, while a security policy blocks the application from sending it.

Alternatively, every firewall rule might allow the traffic, but no route exists to deliver the packet.

Neither failure can be solved by changing application request headers.

This is why engineers should investigate routing and filtering separately rather than treating all connection failures as generic firewall issues.

## 11.4 The return path matters, too

Suppose an outbound request successfully leaves the VPC.

That doesn't automatically prove the response can return.

The receiving system sends a response toward the source endpoint it observed. NAT devices must maintain suitable translation state, and the intervening routing and filtering systems must support the return path.

More complex networks may also experience **asymmetric routing**, where outbound and inbound packets use different network paths.

Asymmetry isn't inherently incorrect. But stateful devices may reject traffic that arrives through an unexpected path without the connection state they require.

This is particularly relevant when an organization introduces multiple firewalls, VPN gateways, transit gateways, or alternative egress paths.

You cannot establish connectivity by examining only the outbound half of a conversation.

A working exchange requires both directions.

---

# 12. IPv6: What Happens When We Stop Treating Addresses as Scarce?

We've spent much of this lecture discussing private IPv4 addresses and translation because IPv4 has a fundamental limitation: its address space is relatively small.

IPv6 addresses contain 128 bits rather than 32.

The resulting address space is enormously larger—large enough to transform how addresses can be allocated and routed.

IPv6 isn't merely IPv4 with longer numbers, however.

It also changes important details of local discovery, packet handling, and network configuration.

## 12.1 IPv6 addresses and prefixes

IPv6 addresses are normally written in hexadecimal, with groups separated by colons.

An example from the documentation range is:

`2001:db8:42:20::17`

IPv6 also uses CIDR prefix notation.

For example, a slash-64 prefix fixes the first 64 bits, leaving another 64 bits available for the interface-address portion.

Slash-64 subnets are extremely common in ordinary IPv6 local networks.

Unlike traditional IPv4 subnet sizing, where administrators might carefully divide a small range into slash-27 or slash-28 networks to conserve host addresses, typical IPv6 address planning can allocate tremendously large subnets.

The principal design problem shifts away from squeezing as many hosts as possible into scarce address space.

Instead, administrators focus more on scalable allocation, routing structure, aggregation, and operational policies.

## 12.2 Global, local, and loopback addressing

IPv6 contains several important address categories.

**Global unicast addresses** can provide globally unique addressing suitable for internet routing, subject to the actual routing and security configuration.

**Link-local addresses**, commonly beginning with `fe80`, are intended for communication on a local link. Routers do not forward packets with link-local source or destination addresses to other links.

**Unique Local Addresses**, or ULAs, occupy `fc00::/7` and serve private-network-style purposes without ordinary public internet routing. In practice, locally assigned ULA prefixes commonly begin with `fd`.

The IPv6 loopback address is `::1`, serving a role analogous to IPv4's `127.0.0.1`.

These categories remind us that a large address space doesn't eliminate the need for scope and routing rules.

Not every IPv6 address is intended to be globally reachable.

## 12.3 IPv6 can often avoid NAT

Here's one of the biggest architectural differences.

With sufficiently allocated global IPv6 addressing, devices and services can possess their own globally unique IP addresses without relying on address-sharing NAT for conservation.

That doesn't mean every device should accept unsolicited internet connections.

A firewall can still enforce strict inbound policies.

This is another reason NAT should not be confused with network security.

IPv6 allows an architecture where an endpoint has global addressing but remains protected by stateful firewall rules.

The network can be reachable in principle without every connection being permitted.

This distinction often makes protocol design and end-to-end connectivity simpler, although real networks still contain firewalls, proxies, tunnels, and other intermediary systems.

## 12.4 Neighbor Discovery replaces ARP

IPv6 does not use ARP.

Instead, it uses **Neighbor Discovery**, built on ICMPv6.

Neighbor Discovery supports several responsibilities, including discovering nearby routers, learning link-layer addresses, determining whether neighbors remain reachable, and detecting duplicate addresses.

Routers can advertise information about the network through Router Advertisement messages.

Hosts may use this information for automatic address configuration, including **Stateless Address Autoconfiguration**, or SLAAC.

Other configurations use DHCPv6 or manual assignment.

The precise behavior depends on the environment, but the conceptual purpose is familiar.

The host needs to know its addresses, which destinations are considered local, and which routers can forward traffic toward other networks.

Neighbor Discovery supplies part of that machinery for IPv6.

A particularly important operational consequence is that blocking ICMPv6 indiscriminately can break essential network functions.

ICMPv6 is not merely a diagnostic convenience equivalent to allowing ping.

It participates in normal IPv6 operation.

## 12.5 Dual-stack systems and surprising failures

During the long transition from IPv4 to IPv6, many systems support both protocols.

A hostname may have both A and AAAA DNS records.

The client may attempt connectivity using IPv6, IPv4, or a strategy that coordinates connection attempts across the available address families.

Techniques inspired by Happy Eyeballs aim to avoid excessive delays when one family performs poorly.

Suppose your public API works from some networks but fails or feels slow from others.

One possibility is that its IPv4 route works correctly while its IPv6 destination is broken or unreachable.

A client with working IPv6 connectivity may expose this defect, while an IPv4-only client never encounters it.

The appropriate investigation separates the address families.

Check DNS answers, routing, connection attempts, TLS behavior, and application responses for IPv4 and IPv6 independently.

A successful IPv4 test does not prove the IPv6 path is healthy.

And a correct AAAA record does not guarantee that the advertised IPv6 destination is operational.

---

# 13. MTU: The Network Failure That Waits for Larger Packets

Let's investigate one final networking mechanism before returning to our incident.

Imagine an API connection with strange behavior.

The TCP handshake succeeds. Small HTTPS requests work. A simple health check returns immediately.

But when the client sends a larger request body, the connection stalls.

The application's logs reveal nothing useful. The developer concludes that the backend must be blocking on JSON parsing.

Yet the request body may not have arrived intact.

The problem could involve the **Maximum Transmission Unit**, or MTU.

## 13.1 Packets cannot be arbitrarily large

Every network link has limits on the size of the packets or frames it can transmit.

An ordinary Ethernet network commonly supports a 1,500-byte IP MTU.

However, the complete path between two endpoints may contain links or tunnels with smaller effective limits.

Suppose a VPN adds additional headers around an original IP packet.

Those headers consume space.

A packet that fits comfortably on the original Ethernet network might become too large once encapsulated inside the VPN tunnel.

The sender and network need a way to accommodate the path's actual size restrictions.

## 13.2 Path MTU Discovery

The **Path MTU** is the largest packet size that can traverse the path without requiring fragmentation beyond the packetization assumptions in use.

Systems can employ Path MTU Discovery to determine an appropriate size.

In IPv4, fragmentation rules and the Don't Fragment flag influence what happens when a router encounters an oversized packet.

In IPv6, routers do not fragment packets in transit. When a packet exceeds the next link's MTU, an appropriate router can discard it and send an ICMPv6 Packet Too Big message.

The sending endpoint can then adjust its packetization behavior.

Modern transports may also use packetization-layer discovery techniques rather than relying exclusively on traditional ICMP-based behavior.

The essential principle is that the endpoints need to avoid repeatedly sending packets that the intervening path cannot carry.

## 13.3 The black-hole problem

Now imagine that an intervening firewall blocks the diagnostic messages needed to communicate that a packet is too large.

Small packets travel successfully.

Larger packets are dropped.

But the sender doesn't receive the expected feedback explaining why.

It may keep retransmitting data that cannot traverse the path in its current form.

To the application developer, the connection appears mysterious.

The server is reachable. The handshake works. Some requests succeed. Others stall.

This is a classic **Path MTU black-hole** failure pattern.

It is a reminder that ICMP is not merely something network engineers use for ping.

Parts of IP networking depend on receiving appropriate control and error messages.

Blindly blocking all ICMP traffic can create failures that are extraordinarily unpleasant to diagnose.

The deeper lesson is that successful connection establishment does not prove that every subsequent packet size will be deliverable.

---

# 14. A Framework for Diagnosing Network Reachability

We've now encountered enough mechanisms to investigate real problems systematically.

When an application cannot reach a destination, begin by asking what the failure actually tells you.

Don't immediately blame the backend, and don't immediately blame the network either.

A useful investigation proceeds through several distinct questions.

## 14.1 Do we have the intended destination?

For hostname-based connections, establish whether the name resolves to the expected addresses.

We investigated this in CS230-L04.

But remember that DNS resolution can succeed while everything afterward fails.

Obtaining an IP address only means the naming step produced information.

## 14.2 Does the operating system have a route?

Next, determine which route and interface the operating system would use.

Does the destination match a directly connected network?

Does a VPN install a more specific route?

Is there an appropriate default route?

If no usable route exists, the system may report a network-unreachable error without even attempting to deliver the packet through the expected external path.

An important practical insight is that different destinations can match different routes on the same machine.

The fact that one API works tells you relatively little about the routing path toward another API.

## 14.3 Can the next hop be reached?

Even if the route table points to the correct gateway, local delivery can still fail.

Is the network interface functioning?

Can the system resolve the next hop's link-layer address where required?

Is the expected router present?

Are link-layer security policies or network isolation preventing communication?

In a cloud environment, the analogous questions involve virtual interfaces, subnet associations, route targets, and provider networking configuration.

A route pointing toward a nonexistent or unavailable next hop isn't useful merely because it appears in a table.

## 14.4 Do intermediary policies and translations permit the traffic?

Next, examine firewalls, security groups, network ACLs, NAT mappings, and other middleboxes.

Is the destination port allowed?

Does the return path traverse the expected stateful devices?

Does the source address change through NAT?

Is the application expecting connections from a source address that differs from what the network actually supplies?

Does a private subnet have the appropriate outbound gateway?

These questions are especially important when traffic passes through cloud networks, corporate VPNs, container networking, or several layers of address translation.

## 14.5 Is the destination service actually listening?

Finally, distinguish network reachability from application availability.

A TCP connection can be refused because no appropriate process is listening, or because a network device deliberately rejects it.

A connection timeout may indicate packet loss, filtering, unreachable destinations, or other failures that prevent the connection from completing.

A successful TCP connection only establishes transport-level communication. TLS negotiation can still fail.

And successful TLS negotiation doesn't prove that an HTTP endpoint will return a correct response.

These stages are related, but they provide different evidence.

**The best debugging question is not "Why does the network fail?" It is "At which boundary does expected communication stop?"**

---

# 15. Solving the Payment Integration Incident

Let's reconstruct our original production failure.

The backend runs at a private IPv4 address inside an AWS VPC.

It can accept connections from the application load balancer. It can query its database. Its health checks pass.

The payment provider's DNS name resolves correctly to a public address.

But an outbound HTTPS connection never completes.

We examine the private subnet's route table.

It contains a local route for the VPC address space. It does not contain the intended default route toward the NAT gateway or another suitable outbound path.

That explains why internal connectivity succeeds while external connectivity fails.

The application has no usable route from its private subnet toward the payment provider's public destination.

The team configures the appropriate outbound route and verifies that the NAT gateway and its upstream connectivity are operational.

They also confirm that security group rules permit the required outbound traffic and that the payment provider allows connections from the resulting public egress address.

After restoring the intended network path, the payment request succeeds.

No backend code change was required.

### What the team should have learned

The immediate mistake was an incorrect route configuration.

But the architectural mistake was deeper.

The deployment checklist validated application health and internal dependencies without validating a required outbound business dependency.

A backend that serves health-check requests may still be incapable of completing its most important workflow.

The team should therefore include external dependency connectivity in appropriate deployment checks and runtime monitoring, without making every liveness probe depend directly on an external payment provider.

It should also document egress architecture explicitly, rather than leaving it as an invisible assumption in infrastructure configuration.

Finally, the infrastructure should be represented in code and reviewed like application code.

A single route-table change can have just as much business impact as a broken payment implementation.

The network is part of the software system, whether or not application developers enjoy thinking about it.

---

# 16. The Oral Examination

We now have enough knowledge to examine IP networking like an engineer rather than merely recognize its terminology.

Before reading the solutions, try answering these questions out loud. Imagine that a senior engineer is interviewing you and will challenge any hand-waving.

Explain mechanisms, not just conclusions. If you can defend the explanation when an interviewer changes one condition, you understand the subject.

### Challenge 1 — The subnet calculation

A machine has address `192.168.10.150/26`.

What network prefix contains this address?

What is the complete address range of that subnet?

Which addresses would normally be available for host assignment in a conventional IPv4 subnet?

And would `192.168.10.200` belong to the same slash-26 subnet?

### Challenge 2 — The VPN routing mystery

Your laptop has the following routes:

- `192.168.1.0/24` through Wi-Fi.
- `10.42.0.0/16` through a VPN.
- `0.0.0.0/0` through the home router.

You attempt to connect to `10.42.20.17`.

Which route wins, and why?

Now suppose your home network itself uses `10.42.20.0/24`.

Which of these overlapping routes is more specific, and what practical problem might appear?

### Challenge 3 — Following a NAT connection

A laptop at `192.168.1.42` opens a TCP connection from local port 53000 to `203.0.113.80`, port 443.

Its router has the public address `198.51.100.24` and translates the source to port 61000.

Describe the source and destination endpoints before and after translation.

Then explain how the router knows where to deliver the response.

Finally, explain why an unrelated inbound connection to the router's public port 62000 does not automatically reach the laptop.

### Challenge 4 — The cloud networking trap

You create an EC2 instance in a subnet with a default route to an internet gateway.

The instance has only a private IPv4 address.

A colleague says: "The subnet is public, so the instance must be reachable from the internet."

What is wrong with that conclusion?

What additional conditions would normally be required for direct inbound IPv4 connectivity?

### Challenge 5 — The invisible backend

Your application load balancer accepts HTTPS traffic from customers.

The application containers have private IPv4 addresses and no direct public inbound route.

Yet customers can successfully use the application.

Explain why this is possible.

Would the backend necessarily observe the customer's original IP address as the source address of its TCP connection?

How might the application obtain reliable client-address information?

### Challenge 6 — The dual-stack failure

An API hostname has valid-looking A and AAAA records.

Some clients connect successfully. Others experience long delays or failures.

The backend team tests IPv4 and finds no problems.

Explain at least two plausible IPv6-related causes and how you would distinguish them from application-layer defects.

### Challenge 7 — The suspiciously small request

A service successfully establishes a TCP connection through a VPN.

Small requests work, but larger HTTP requests sometimes hang.

Backend CPU and memory metrics look normal.

Explain how MTU problems could cause this behavior.

What role might ICMP messages play, and why could an overzealous firewall make the incident worse?

### Challenge 8 — The architectural judgment

Your company is designing a new SaaS platform.

Someone argues that every backend instance should have its own public IPv4 address because NAT gateways add cost and complexity.

Another engineer insists that no application server should ever have a public address, under any circumstances.

Evaluate both claims.

What factors should determine the architecture?

---

# 17. Solutions and Discussion

### Solution 1 — Subnet calculation

A slash-26 prefix leaves six variable IPv4 bits, producing blocks of 64 addresses.

The address 150 falls within the range 128 through 191 in the final octet.

Therefore, the network is `192.168.10.128/26`.

Its complete address range is `192.168.10.128` through `192.168.10.191`.

In a conventional IPv4 subnet, the normally assignable host range is `192.168.10.129` through `192.168.10.190`.

The address `192.168.10.200` belongs to a different slash-26 block, beginning at 192.

A strong interview answer should show how the range was derived rather than merely stating the result.

### Solution 2 — VPN routes

The destination `10.42.20.17` matches both the VPN slash-16 route and the default slash-zero route.

The VPN route wins because it has the longer matching prefix.

If the home network also uses `10.42.20.0/24`, that connected slash-24 route is more specific than the VPN slash-16 route.

Consequently, traffic intended for an internal corporate host may be treated as locally reachable on the home network instead.

This is a classic overlapping-address-space problem.

Potential solutions include avoiding overlapping network allocations, changing the relevant routing or VPN configuration, or using more specialized translation or tunneling arrangements when renumbering isn't practical.

The key principle is that a VPN connection does not automatically override every other route.

### Solution 3 — NAT

Before translation, the source is `192.168.1.42:53000` and the destination is `203.0.113.80:443`.

After translation, the source becomes `198.51.100.24:61000`, while the destination remains the remote API endpoint.

The router maintains state associating the translated endpoint and connection with the internal laptop.

When the response arrives for the translated connection, the router performs the reverse translation and forwards it internally.

An unrelated inbound connection to port 62000 has no automatic relationship to the existing translation mapping.

Without suitable explicit forwarding, mapping, or other configuration, the router generally has no reason to deliver that connection to the laptop.

### Solution 4 — Public subnet

A subnet with an appropriate route to an internet gateway is not sufficient to make every resource directly reachable from the internet.

For ordinary IPv4 internet connectivity, the instance also needs appropriate public IPv4 addressing and relevant network permissions.

The instance must accept traffic on the intended interface and port, its security group and applicable network ACL rules must permit the connection, and the routing path must support communication in both directions.

A public subnet is a networking capability, not an automatic exposure guarantee.

### Solution 5 — Private backend

The public load balancer is reachable from internet clients.

It forwards or proxies appropriate requests to the private application targets through the VPC network.

The clients do not need direct connectivity to the targets' private IP addresses.

For an application load balancer acting as a reverse proxy, the backend normally observes the load balancer side of the connection at the network layer.

Original client information may be communicated through trusted forwarding headers.

The application should process these headers according to its trusted proxy configuration rather than blindly accepting client-supplied values.

### Solution 6 — IPv6

An AAAA record may point to an IPv6 address that is not correctly routed, filtered, or served.

Alternatively, the server may accept IPv4 connections but fail to listen on the expected IPv6 interface.

Firewall rules for IPv6 may differ from IPv4 rules.

Test name resolution and connectivity independently for both address families.

Verify whether the IPv6 destination can establish a transport connection, complete TLS negotiation, and return the expected HTTP response.

The pattern of failures across those stages helps distinguish routing, security, and application problems.

### Solution 7 — MTU

A VPN adds encapsulation overhead, reducing the effective payload size that can fit through parts of the path.

Small packets may traverse the tunnel normally while larger packets exceed the actual Path MTU.

Path MTU Discovery and appropriate packetization behavior should help the sender adjust.

If necessary ICMP messages are filtered or lost, the sender may not learn why oversized packets fail.

This can produce a situation where the initial connection works but larger data transfers stall.

The investigation should examine the tunnel's MTU, observed packet behavior, applicable ICMP handling, and the transport's packet-size negotiation.

### Solution 8 — Architectural judgment

Neither absolute claim is justified.

Public addressing is not inherently insecure, and NAT is not inherently mandatory.

A publicly addressed server with carefully designed security controls can be appropriate in some environments.

Conversely, putting application servers in private subnets behind a controlled public ingress layer is often attractive because it reduces direct exposure, centralizes access policies, and supports more deliberate network architecture.

The decision should consider threat models, operational complexity, connection patterns, IPv4 address availability, IPv6 support, gateway costs, availability requirements, external dependencies, and deployment design.

NAT gateways introduce costs and potential bottlenecks or failure domains. But giving every server a public IPv4 address can introduce other operational, security, and addressing costs.

A senior engineer should evaluate those trade-offs rather than promoting a universal rule.

---

# 18. The Mental Model Worth Keeping

IP networking can be understood as a sequence of forwarding decisions made across multiple independently managed networks.

Start with the destination.

**The IP address identifies where the packet is intended to go.**

The network prefix determines which address ranges belong together for routing purposes.

The host's routing table selects a directly connected destination or an appropriate next hop.

Local link-layer mechanisms deliver the packet to that next hop.

Routers repeat the process, forwarding according to their own routing information.

NAT devices may translate addressing information and maintain state connecting internal and external conversations.

Firewalls and security policies determine which traffic is permitted, independently of whether routes exist.

And the destination's networking stack must deliver the arriving information to the appropriate transport endpoint and application.

There is one especially useful principle to remember:

**A reachable destination requires a valid forwarding path, appropriate permissions, and a working return path.**

DNS can be correct while routing is broken. Routing can be correct while a firewall blocks traffic. A TCP connection can succeed while TLS fails. A healthy application can remain completely unreachable because of infrastructure configuration.

Once you separate those responsibilities, network failures stop looking like mysterious acts of nature.

They become engineering problems with identifiable boundaries.

---

# 19. Next Lecture — The Life of a Network Connection

We've discovered how packets move between networks and how NAT allows private devices to communicate through public addressing.

But what happens when two applications actually begin communicating?

What does it mean for a TCP connection to be established? How can the operating system distinguish thousands of simultaneous conversations? What happens when packets arrive out of order, or when one endpoint disappears without closing its connection?

And why do some applications choose UDP instead of TCP, while modern protocols such as QUIC build sophisticated transport behavior on top of UDP?

In **CS230-L06 — The Life of a Network Connection**, we'll investigate the operating-system and transport machinery that turns routed packets into application communication.

The packets have found their destination.

Now they need to have a conversation.

---

## Optional Practical Lab — Exploring Your Own Network

*The spoken lecture ends here. The remainder is a screen-first investigation worksheet, intended for hands-on study or rapid revision.*

### Experiment A — Inspect addresses, interfaces, and routes

On Linux, inspect addresses and routes with `ip addr`, `ip route`, and `ip -6 route`:

```bash
ip addr
ip route
ip -6 route
```

On macOS, try `ifconfig`, `netstat -rn`, and `route -n get 1.1.1.1`:

```bash
ifconfig
netstat -rn
route -n get 1.1.1.1
```

On Windows PowerShell, use `Get-NetIPConfiguration` plus `Get-NetRoute` for IPv4 and IPv6:

```powershell
Get-NetIPConfiguration
Get-NetRoute -AddressFamily IPv4
Get-NetRoute -AddressFamily IPv6
```

Investigate which addresses belong to your Wi-Fi interface, whether any VPN interfaces exist, and which routes provide access to external networks.

Find the default gateway.

### Experiment B — Ask the OS which route it will use

On Linux, ask which route would be used toward `1.1.1.1` and toward a local address such as `192.168.1.1`:

```bash
ip route get 1.1.1.1
ip route get 192.168.1.1
```

Replace the private destination with a relevant address from your own network.

Compare the selected interfaces and next hops.

On Windows, inspect the route table using: `route print`

Try to predict the longest-prefix match before checking the result.

### Experiment C — Inspect local neighbor discovery

On Linux: `ip neigh`

On macOS: `arp -a`

On Windows: `Get-NetNeighbor`

Identify which local IP addresses have corresponding link-layer neighbor information.

Why shouldn't you expect the MAC address of a public web server on another continent to appear in your local ARP table?

### Experiment D — Trace a route

On Linux: `traceroute example.com`

On Windows: `tracert example.com`

On macOS: `traceroute example.com`

Some commands may need to be installed separately.

Examine the route toward the destination, noting that intermediate routers may suppress, rate-limit, or deprioritize diagnostic responses.

Do not interpret every missing hop as packet loss affecting the real application.

### Experiment E — Inspect public versus private addressing

Find the IPv4 address assigned to your local network interface.

Then check the public source address observed by a service you trust.

If the addresses differ, consider whether your traffic passes through NAT.

Inspect your router's WAN configuration if available. An address in `100.64.0.0/10`, or an RFC 1918 private address on the WAN interface, can indicate another upstream address-translation layer.

Remember that VPNs and proxies can change the public address observed by external services.

### Experiment F — Test IPv4 and IPv6 separately

Using curl, force IPv4 with `-4` and IPv6 with `-6` while fetching only headers (`-I`):

```bash
curl -4 -I https://example.com
curl -6 -I https://example.com
```

Compare the results.

A failed IPv6 attempt may indicate that your local network lacks usable IPv6 connectivity, not that the website itself is broken.

Use the comparison as diagnostic evidence, not an automatic verdict.

### Experiment G — Design a cloud network

Imagine an AWS VPC `10.42.0.0/16` with a public load-balancer subnet `10.42.10.0/24`, a private application subnet `10.42.20.0/24`, and a private database subnet `10.42.30.0/24`:

```text
VPC:
  10.42.0.0/16

Public load balancer:
  10.42.10.0/24

Private application:
  10.42.20.0/24

Private database:
  10.42.30.0/24
```

Design routing and security controls for the following requirements:

1. Internet clients can reach the load balancer on HTTPS port 443.
2. The load balancer can reach application containers on port 3000.
3. Application containers can reach PostgreSQL on port 5432.
4. Application containers can initiate outbound HTTPS connections to an external payment provider.
5. The database cannot accept direct inbound internet connections.

Explain the role of each subnet, route table, internet gateway, NAT gateway, and security group.

The goal is not to memorize AWS resource names. It is to derive a working network architecture from explicit communication requirements.

---

## Further Reading — Optional Technical References

1. [RFC 791 — Internet Protocol](https://www.rfc-editor.org/rfc/rfc791) — Original IPv4 packet architecture and forwarding fundamentals.
2. [RFC 1918 — Address Allocation for Private Internets](https://www.rfc-editor.org/rfc/rfc1918) — Private IPv4 addressing.
3. [RFC 4632 — Classless Inter-Domain Routing](https://www.rfc-editor.org/rfc/rfc4632) — Prefix-based addressing, aggregation, and longest-prefix forwarding.
4. [RFC 3022 — Traditional IP Network Address Translator](https://www.rfc-editor.org/rfc/rfc3022) — Address translation, port translation, and their limitations.
5. [RFC 6598 — Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598) — Addressing used for carrier-grade NAT deployments.
6. [RFC 4271 — Border Gateway Protocol 4](https://www.rfc-editor.org/rfc/rfc4271) — Interdomain routing and BGP.
7. [RFC 4291 — IPv6 Addressing Architecture](https://www.rfc-editor.org/rfc/rfc4291) — IPv6 address structure and address categories.
8. [RFC 4861 — Neighbor Discovery for IPv6](https://www.rfc-editor.org/rfc/rfc4861) — Router discovery, neighbor resolution, and local IPv6 operation.
9. [RFC 8201 — Path MTU Discovery for IPv6](https://www.rfc-editor.org/rfc/rfc8201) — Discovering usable packet sizes across IPv6 paths.
10. [AWS — VPC Route Tables](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html) — Practical cloud routing configuration.
11. [AWS — Example Routing Options](https://docs.aws.amazon.com/vpc/latest/userguide/route-table-options.html) — Internet gateways, NAT gateways, and route targets.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS230-L05  IP / SUBNETS / ROUTING / NAT — INTERVIEW GLANCE CARD

CORE MODEL
  IP address = logical address of an interface/endpoint — not a passport ID
  Address → destination; routing → how to get there
  Reachability needs: forwarding path + permissions + working RETURN path

IPv4 BASICS
  32-bit; dotted octets 0–255; ~4.29B numerical space (specials + scarcity)
  Private + NAT + IPv6 exist largely because of that scarcity

SUBNETS & CIDR
  prefix/N = N leading network bits; host bits = 32−N
  Addresses in prefix = 2^(32−N)   /24→256  /26→64  /30→4  /32→1 host
  Mask 255.255.255.0 ≡ /24; AND address with mask → network prefix
  Same prefix → often direct local delivery; else → router/next hop
  Conventional /24: network + broadcast reserved → 254 usable hosts
  Subnets = boundaries for routing/segmentation — NOT automatic security

ROUTING TABLE
  Connected prefixes, next-hop routes, default 0.0.0.0/0 (matches all)
  Longest-prefix match wins (more specific > default)
  Destination vs next hop: gateway forwards toward ultimate IP
  DHCP often supplies address, mask, gateway, DNS (wrong GW vs wrong DNS
  = different failures with same "internet broken" UX)

LINK LAYER vs IP
  MAC: local frame delivery to NEXT hop — not remote server's MAC across net
  ARP (IPv4): "who has IP X?" → MAC; cache in neighbor/ARP table
  Each hop: new L2 framing; IP destination usually retained (NAT rewrites)

INTERNET ROUTING
  Not Google Maps — policy, peering, failures, traffic engineering
  AS = administrative domain; BGP exchanges prefix reachability + policy
  Control plane: learn/maintain routes
  Data plane: forward packets from installed entries
  IPv4 TTL / IPv6 Hop Limit: decrement; 0 → drop (+ ICMP Time Exceeded)
  Traceroute uses hop limits — evidence about path, not perfect timing movie

PRIVATE IPv4 (RFC 1918)
  10.0.0.0/8
  172.16.0.0/12  (172.16–172.31)
  192.168.0.0/16
  Reusable inside orgs; no ordinary global public routing
  Routable inside VPC/VPN — not "unroutable physics"

NAT / NAPT (PAT)
  Private src rewritten to public IP (+ often src port)
  Translation STATE maps return traffic to internal endpoint
  Many clients share few public IPv4s via distinct mapped ports
  Stateful limits: table size, port exhaustion, UDP idle expiry
  Unsolicited inbound usually fails without mapping — effect ≠ full firewall
  DNAT / port forward: rewrite dest to internal host — still need public
  reachability, correct listen bind, firewalls both ways
  localhost trap: listen 127.0.0.1 ≠ accept LAN/Wi-Fi arrivals
  CGNAT: ISP NAT above you; WAN may be 100.64.0.0/10 — home forward insufficient

NAT ≠ FIREWALL ≠ ROUTE
  Route:     where next?
  Firewall:  is it permitted? (SG stateful; NACL often subnet + stateless)
  NAT:       rewrite addresses/ports + keep mapping

CLOUD SKETCH (AWS-STYLE)
  "Public subnet" ≈ route to Internet Gateway — not "addresses look public"
  Private subnet: no direct IGW IPv4 route; egress via NAT GW (+ IGW upstream)
  Public LB → private targets; clients need no route to 10.x containers
  L7 LB ≠ NAT: host/path/headers/health; backend sees LB as TCP peer
  Client IP: X-Forwarded-For only if you TRUST the proxy chain
  Incident pattern: healthy app + missing private→NAT default = payment timeout

IPv6
  128-bit; hex groups; /64 common for LANs
  Global unicast | link-local fe80:: (not forwarded) | ULA fc00::/7 (fd…)
  Loopback ::1  (≈ 127.0.0.1)
  Global addr + firewall can replace conservation NAT — NAT ≠ security
  Neighbor Discovery (ICMPv6) replaces ARP; RA / SLAAC / DHCPv6
  Blocking ICMPv6 can break IPv6 operation (not "just ping")
  Dual-stack: test A and AAAA paths independently

MTU / PMTUD
  Link MTU limits (Ethernet often 1500); tunnels shrink effective payload
  Path MTU Discovery; IPv6 routers don't fragment in transit → Packet Too Big
  Black hole: oversized drops + ICMP filtered → handshake OK, large body stalls

DIAGNOSIS LADDER
  1. Intended destination? (DNS)
  2. Usable route / interface?
  3. Next hop reachable (L2 / cloud target)?
  4. Middleboxes: SG/NACL/NAT/return path / asymmetry?
  5. Service listening + TLS + HTTP semantics?
  Ask: at which BOUNDARY did expected communication stop?

SENIOR LINE: reachable = path + permission + return. DNS OK while routing
             broken; route OK while filter blocks; TCP OK while TLS fails.
```
