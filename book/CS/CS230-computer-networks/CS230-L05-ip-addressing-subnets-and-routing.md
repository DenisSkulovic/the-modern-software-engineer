---
id: CS230-L05
course: CS230
title: "IP Addressing, Subnets, and Routing"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS230-L04
next: CS230-L06
---





# CS230 — Computer Networks and Web Protocols

## Lecture 05: IP Addressing, Subnets, and Routing

*Your VPN is connected. DNS returns the correct address. The company's internal server is running. Yet your laptop cannot reach it—and the problem is hiding in a completely ordinary routing decision.*

---

# Part I — Intuition

## The picture to carry in your head

You're working remotely on a hotel-booking platform.

The application's development database is accessible through a corporate VPN.

You connect to the VPN, open your development environment, and attempt to contact the database at `10.42.20.17`.

The connection times out.

You check the VPN client. Connected.

You check DNS. The hostname resolves to the expected address.

Your colleague can reach the database from the office.

You can access public websites without difficulty.

The obvious conclusion is that something must be wrong with the VPN.

But perhaps the VPN is working perfectly.

Perhaps your laptop is sending the database traffic in the wrong direction.

This is what today's lecture is about.

## 1. Every packet needs a next destination

Imagine traveling from Vilnius to a small village in Germany.

You know your final destination.

But knowing the address doesn't tell you which road to take out of Vilnius.

You first need to decide which road leads toward the destination.

After traveling along that road, you arrive at another junction.

There, another decision is made.

You continue through several intersections until you reach the village.

IP routing works through a sequence of forwarding decisions.

A packet contains a destination IP address.

Your computer consults its routing information and decides how to begin delivering it.

If the destination is directly reachable over a local network, the machine may send it directly.

Otherwise, it sends the packet to another device—a router—that knows something about forwarding traffic toward the destination.

That router makes its own decision.

And the next router does the same.

The sender doesn't need to know every intermediate machine along the entire journey.

It needs a suitable next hop.

**An IP address identifies the intended destination. A route determines the next forwarding decision.**

## 2. A subnet is a neighborhood of addresses

Suppose your laptop has the address:

`192.168.1.42/24`

The first part is an IPv4 address.

The `/24` describes a network prefix.

It means that the first 24 of the address's 32 bits are fixed when identifying the network block.

The remaining eight bits can vary.

That gives us the network:

`192.168.1.0/24`

It contains 256 IPv4 addresses, ranging from `192.168.1.0` through `192.168.1.255`.

In a conventional IPv4 LAN, the first address identifies the network and the last serves as the subnet-directed broadcast address, leaving 254 ordinary host addresses.

Now imagine a printer at `192.168.1.80`.

The laptop and printer are in the same `/24` block.

They can normally communicate through their local network if the actual link and security configuration permit it.

But a server at `192.168.2.20` is outside that block.

Reaching it requires an appropriate route.

The slash notation is not decorative.

It influences how machines decide whether destinations are local or must be reached through another network.

## 3. The routing table is a collection of instructions

Your laptop maintains routing information.

Imagine it contains three relevant routes:

```text
192.168.1.0/24   Directly reachable through Wi-Fi
10.42.0.0/16     Reachable through the corporate VPN
0.0.0.0/0        Everything else via the home router
```

The first route covers your local network.

The second covers the company's internal address space.

The third is the default route, used when no more specific matching route is available.

Now consider a packet addressed to `10.42.20.17`.

It matches the corporate VPN route.

It also matches the default route.

Which should the computer choose?

The more specific matching route.

This is the fundamental rule called **longest-prefix matching**.

A prefix containing more fixed leading bits identifies a narrower destination range.

A `/16` route is more specific than `/0`.

A `/24` route is more specific than `/16`.

A `/32` IPv4 host route identifies one address and is more specific than all of those.

This lets networks express broad rules with exceptions.

## 4. The mystery: two routes overlap

Now here's the twist.

You're sitting in a hotel.

The hotel's Wi-Fi network happens to use:

`10.42.20.0/24`

Your laptop receives:

`10.42.20.42/24`

The corporate VPN installs:

`10.42.0.0/16`

You attempt to reach the company database:

`10.42.20.17`

Both routes match the destination.

But the hotel's local `/24` route is more specific than the corporate VPN's `/16`.

The operating system prefers the local route.

Instead of sending the packet through the VPN, it tries to deliver the packet on the hotel's Wi-Fi network.

The database is not there.

The connection fails.

The VPN is connected.

The DNS answer is correct.

The database is healthy.

The routing decision is simply different from what you expected.

### The failure in one picture

```text
Destination: 10.42.20.17

Hotel Wi-Fi route: 10.42.20.0/24   MATCH
Corporate VPN:     10.42.0.0/16    MATCH
Default route:     0.0.0.0/0       MATCH

Winner: Hotel Wi-Fi /24
Because /24 is more specific than /16.
```

This is why a connected VPN doesn't guarantee that every corporate destination travels through it.

The operating system follows its effective routing rules, not the user's intentions.

## 5. The local network needs another kind of address

Suppose your laptop has selected the home router as its next hop.

It knows the router's IP address.

But how does it physically deliver the packet across the local network?

On an ordinary IPv4 Ethernet-style network, it uses another addressing mechanism.

Devices have link-layer addresses, commonly called MAC addresses.

The laptop needs to discover the link-layer address corresponding to the router's IPv4 address.

It can use the Address Resolution Protocol, or ARP.

Conceptually, ARP asks:

"Who has this IPv4 address on the local network?"

The router responds with the relevant link-layer address.

The laptop can now transmit a local frame addressed to that router.

Inside the frame is an IP packet whose destination remains the remote server.

Notice that there are two destinations involved.

The link-layer destination is the next local hop.

The IP destination is the final destination of the packet.

The router receives the frame, examines the IP destination, and forwards the packet using another local delivery mechanism appropriate for its next hop.

The link-layer envelope changes.

The packet continues its journey.

## 6. The internet is a chain of local decisions

A packet traveling across the internet may pass through many routers.

Each router uses its forwarding information to select the next step.

The routers don't need to know that the packet belongs to a hotel-booking application.

They don't need to understand the customer's reservation.

They generally don't need to inspect the HTTP message.

They forward according to network-layer information and applicable routing policies.

The route may not be geographically shortest.

Internet routing also reflects provider agreements, traffic engineering, failures, and network policy.

A packet can travel through a longer geographical route because that route is preferred or available.

This is not necessarily a malfunction.

It's how independently operated networks cooperate.

## The minute-long mental replay

An application wants to contact an IP destination.

The operating system consults routing information.

The most specific applicable destination route normally wins, subject to routing policies and tie-breaking behavior.

The chosen route identifies direct delivery or a next hop.

For local IPv4 Ethernet-style delivery, ARP may resolve the next hop's link-layer address.

The packet travels to the next device.

Routers repeat forwarding decisions until the packet reaches its destination or can no longer be forwarded.

The sender's intended path and the operating system's selected path aren't necessarily identical.

### Three questions before the Deep Dive

1. Why does `10.42.20.0/24` take precedence over `10.42.0.0/16` for destination `10.42.20.17`?
2. Why does your laptop need the router's MAC address rather than the remote web server's MAC address?
3. Why doesn't a successfully connected VPN prove that a particular request travels through it?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The VPN That Was Connected to the Wrong Road

Our engineer is trying to access a development database.

The database address is `10.42.20.17`.

The corporate VPN establishes successfully.

The hostname resolves correctly.

Yet the TCP connection never completes.

The operating system's routing table contains a directly connected hotel Wi-Fi network at `10.42.20.0/24` and a VPN route covering `10.42.0.0/16`.

The destination matches both.

The local route wins because its prefix is longer.

From the operating system's perspective, the destination appears to be on the local network.

The machine therefore attempts local delivery.

This may fail because no device owns that address on the hotel's network.

Or, in a more alarming variation, another unrelated device on the local network may happen to use it.

Now the engineer might connect to the wrong endpoint.

TLS hostname verification and other application authentication controls remain important defenses, but they don't correct the underlying routing error.

The incident illustrates a principle that experienced application developers sometimes underestimate:

**Correct naming and correct routing are independent requirements.**

DNS may correctly identify a destination that the operating system cannot reach through the intended path.

Let's build the mechanics carefully.

## 2. What an IP Address Actually Identifies

Developers often casually refer to an IP address as a computer's address.

That's useful shorthand, but the actual model is more flexible.

An IP address is a logical identifier used within the Internet Protocol addressing and routing system.

It is typically assigned to a network interface, though real implementations support additional addressing arrangements.

One machine can have multiple IP addresses.

One interface can have multiple addresses.

A laptop can have IPv4 and IPv6 addresses simultaneously.

A VPN can introduce virtual interfaces and routes.

A cloud workload may operate behind translated or virtual network identities.

And an address may move between machines as part of a high-availability design.

### Address identity versus machine identity

Suppose a server has an IPv4 address today.

Tomorrow it is replaced by another machine that receives the same address.

The IP address remained useful as a network destination, but the underlying host changed.

Conversely, the same laptop can receive different addresses when moving between networks.

Therefore, IP addressing should not be confused with permanent machine identity or application identity.

TLS certificates, application credentials, and service-discovery mechanisms address different aspects of identity.

This distinction becomes especially important in cloud environments, where infrastructure replacement is routine.

## 3. IPv4 Addressing: Thirty-Two Bits With Structure

An IPv4 address contains 32 bits.

Humans usually write those bits as four decimal numbers separated by dots.

Consider:

`192.168.10.150`

Each decimal number represents eight bits, commonly called an octet.

The address can therefore be treated as one 32-bit binary value.

A network prefix identifies a contiguous block of addresses sharing a number of leading bits.

The prefix length determines how much of the address is fixed.

### Understanding `/24`

A `/24` prefix fixes the first 24 bits.

Eight bits remain variable.

That produces two to the power of eight, or 256, possible address values.

For example:

`192.168.10.0/24`

covers:

`192.168.10.0` through `192.168.10.255`.

In a conventional IPv4 subnet, the first address denotes the network and the last is the directed broadcast address.

The remaining addresses are normally suitable for host assignment.

There are exceptions, including point-to-point addressing, and cloud providers may reserve additional addresses within a subnet.

Don't turn the familiar 254-host calculation into a universal rule for every IPv4 prefix.

### The subnet mask

You may also encounter:

`255.255.255.0`

This is the dotted-decimal subnet mask corresponding to `/24`.

Its binary form contains 24 leading one-bits followed by eight zero-bits.

Applying a bitwise AND operation between an IPv4 address and the mask produces the network address.

For example, applying the `/24` mask to `192.168.10.150` produces `192.168.10.0`.

This isn't merely an interview trick.

It explains how addresses are grouped into destination prefixes and how the operating system recognizes matching network ranges.

## 4. Subnetting: Dividing a Network Into Smaller Blocks

Suppose an organization owns an internal `/24` block.

It wants separate network segments for office devices, laboratory machines, and guest traffic.

Instead of placing everything into one large address range, it may divide the block into smaller prefixes.

Imagine dividing a `/24` into four `/26` blocks.

A `/26` fixes 26 bits.

That leaves six bits variable.

Two to the power of six equals 64.

Therefore, each `/26` block contains 64 addresses.

The four blocks are:

```text
192.168.10.0/26       .0   through .63
192.168.10.64/26      .64  through .127
192.168.10.128/26     .128 through .191
192.168.10.192/26     .192 through .255
```

The addresses after the final dot are shown in abbreviated form.

Now consider the address:

`192.168.10.150/26`

It belongs to:

`192.168.10.128/26`

That subnet runs from `.128` through `.191`.

For a conventional IPv4 subnet, `.128` is the network address and `.191` is the broadcast address.

Ordinary host addresses run from `.129` through `.190`.

A host at `.200` belongs to a different `/26` block.

### The formula

For an IPv4 prefix of length \(p\), the total number of addresses is:

\[
2^{32-p}
\]

A `/24` contains 256 addresses.

A `/26` contains 64.

A `/30` contains four.

A `/32` identifies one address.

### The `/31` exception

In conventional small IPv4 subnets, engineers often subtract two addresses for network and broadcast.

But `/31` prefixes have standardized use on point-to-point links where both addresses can be used.

This is a reminder that address-block mathematics and host-assignment conventions are related but not identical.

The formula calculates the size of the block.

The actual usable assignments depend on the network design and addressing conventions.

### Why CIDR matters beyond arithmetic

Classless Inter-Domain Routing, or CIDR, allows networks to represent address blocks using arbitrary prefix lengths rather than being limited to old classful boundaries.

This permits flexible subnet design and route aggregation.

For example, a provider can advertise a larger aggregate prefix instead of requiring every external router to maintain separate entries for every small internal subdivision.

This helps make internet-scale routing manageable.

The deeper significance of CIDR is not merely saving addresses.

It is giving routers a compact language for describing destination ranges.

## 5. The Routing Table: The Operating System's Forwarding Instructions

A host uses routing information to determine where outgoing packets should go.

A simplified route contains a destination prefix and forwarding instructions.

Those instructions may identify an outgoing interface, a next-hop gateway, or other attributes.

Some routes describe directly connected networks.

Others describe networks reachable through routers.

A default route handles destinations that don't match more specific routes.

For IPv4, the default route is:

`0.0.0.0/0`

Since zero leading bits are fixed, every IPv4 destination matches.

That sounds universal.

But a default route is the least specific possible route.

Any matching `/8`, `/16`, `/24`, or `/32` route is more specific.

### Longest-prefix matching

Consider this simplified routing table.

```text
Destination         Forwarding path
192.168.1.0/24      Wi-Fi
10.42.0.0/16        Corporate VPN
10.42.20.0/24       Separate tunnel
0.0.0.0/0           Home router
```

Now determine the route to:

`10.42.20.17`

The destination matches `/16`, `/24`, and `/0`.

The `/24` route wins because it is the most specific.

For:

`10.42.30.17`

the `/24` no longer matches.

The `/16` route wins.

For:

`203.0.113.80`

neither corporate route matches.

The default route applies.

### Prefix length before route metrics

You may have encountered routing metrics or administrative preferences.

They matter, but don't confuse them with prefix specificity.

In ordinary destination routing, the longest matching prefix is selected before comparing preferences among otherwise competing routes.

A `/24` can therefore take precedence over a `/16` even if the `/16` is associated with a preferred VPN connection.

Real operating systems may also use policy routing, multiple tables, source-address rules, and other controls.

But the core destination-prefix principle remains fundamental.

### The next hop is not the final destination

Suppose the packet's final destination is `203.0.113.80`.

The host's selected next hop is the local router at `192.168.1.1`.

The host sends the packet toward that router.

The packet's IP destination remains `203.0.113.80` during ordinary routing.

The next-hop address tells the local machine how to begin forwarding.

The final destination tells routers where the packet is ultimately intended to go.

Confusing these two addresses leads to many misunderstandings about network behavior.

## 6. Where Do Routes Come From?

Most users don't manually configure their laptop's routing table.

The operating system receives configuration from the network and from installed software.

### DHCP

In typical IPv4 networks, DHCP can provide an IP address lease, subnet information, default gateway, and DNS resolver addresses.

When a laptop joins Wi-Fi, it may receive this information automatically.

That allows the machine to determine which network addresses belong to its local segment and where to send other traffic.

A DHCP server supplying the wrong gateway can break external connectivity while local communication continues working.

A DHCP server supplying incorrect DNS resolvers can break hostname-based connections even though routing by address still works.

The symptoms may sound identical to users.

The failure mechanisms are different.

### VPN software

A VPN client commonly creates a virtual network interface and installs routes.

Some VPNs direct nearly all traffic through the tunnel.

Others use split tunneling, sending only selected destinations through the VPN.

For example, the VPN may install routes for corporate prefixes while leaving public internet traffic on the normal connection.

This is convenient because ordinary browsing doesn't have to traverse the company network.

But split tunneling also creates opportunities for route overlap.

The hotel Wi-Fi incident is one example.

### Manual and dynamic routes

Administrators can install routes manually.

Routers may learn routes through routing protocols.

Cloud networking systems can configure virtual routes through provider infrastructure.

The source of a route matters when troubleshooting.

A route installed by DHCP may reappear after a lease renewal.

A route installed by VPN software may reappear on reconnection.

A manually deleted route may therefore return because the system controlling it is still active.

This is a familiar reconciliation problem at the networking level.

## 7. ARP: Finding the Local Recipient

We know how the operating system selects a route.

But suppose the route says to send traffic toward gateway `192.168.1.1`.

The network interface still needs to deliver the data over the local link.

On an ordinary IPv4 Ethernet-style network, that involves a link-layer address.

The Ethernet frame has a source and destination MAC address.

The IP packet inside the frame has its own source and destination IP addresses.

These are not interchangeable.

### Address Resolution Protocol

ARP allows a host to discover the link-layer address associated with an IPv4 address on the local network.

The host may broadcast an ARP request asking which device owns a particular IPv4 address.

The appropriate device responds with its link-layer address.

The host caches the result in a neighbor table.

Now it can send frames toward the selected next hop.

### Why ARP doesn't find the remote server

Suppose your laptop wants to contact a public server in another country.

It does not attempt to discover the remote server's Ethernet MAC address.

That address is not meaningful across the entire routed internet.

Instead, the laptop determines its next local hop.

It resolves the link-layer address of that next hop.

The local frame reaches the router.

The router performs another forwarding decision and constructs the appropriate link-layer framing for the next segment.

This continues through the network.

The local frame changes from hop to hop.

The IP destination generally remains the final destination, aside from deliberate translation mechanisms that we'll study next.

### ARP failure is not route failure

Suppose the routing table correctly identifies a next-hop gateway.

But ARP cannot resolve the gateway's link-layer address.

The host knows where the packet should go at the IP layer.

It cannot complete local delivery.

This distinction matters when diagnosing failures.

A correct route is not proof that the next hop is physically or virtually reachable.

### The security consequence

ARP was not designed as a strongly authenticated identity system.

On networks without appropriate protections, malicious or faulty devices can create misleading address-to-hardware mappings.

That is one reason local network trust matters.

Application authentication—particularly proper TLS validation—remains important even when the underlying network appears familiar.

## 8. Routers: Small Decisions at Internet Scale

Once the packet reaches a router, the router examines the destination address and selects a forwarding path.

It may have several possible routes.

It may also apply policy, filtering, or traffic-engineering decisions.

But the fundamental operation is still selecting where the packet should go next.

A router doesn't normally ask the original sender for a complete end-to-end itinerary.

Each router makes a decision based on information available to it.

### Control plane versus data plane

The **control plane** establishes and maintains routing knowledge.

The **data plane** forwards actual packets using that knowledge.

This distinction is extremely useful.

A routing protocol may discover that a particular network is reachable through a neighboring router.

That information becomes part of the forwarding system.

Packets can then be processed at high speed using the resulting route information.

The router doesn't need to renegotiate the destination path with every packet.

### Routing inside an organization

An enterprise or provider network may use internal routing protocols to distribute reachability information.

Examples include OSPF and IS-IS.

These protocols help routers maintain knowledge of reachable prefixes within their routing domain.

The choice of protocol and design belongs largely to network engineering, but application engineers benefit from understanding the separation between route discovery and packet forwarding.

### Routing between organizations

The internet consists of many independently operated networks.

These are commonly organized into autonomous systems.

Between autonomous systems, BGP is a central protocol for exchanging information about reachable IP prefixes.

BGP's decisions reflect network policy, available paths, and administrative relationships.

It is not a globally coordinated algorithm that simply chooses the physically shortest distance.

A network may prefer one upstream provider over another because of policy or commercial arrangements.

A route may change after an outage or a routing update.

The resulting packet path may look strange from a geographical perspective while remaining consistent with the network's operating rules.

### Route aggregation

Suppose an organization operates many small internal subnets.

It can sometimes summarize their reachability with one larger aggregate prefix when that summary accurately represents the available path.

This reduces the amount of routing information other networks need to maintain.

But aggregation has consequences.

An overly broad route may direct traffic toward destinations that aren't actually reachable through the expected path.

More specific routes or appropriate internal forwarding must complete the picture.

Again, the routing system is a language of destination ranges and forwarding decisions.

## 9. The Hop Limit: Packets Must Not Wander Forever

Imagine a network configuration error that creates a routing loop.

Router A forwards a packet to router B.

Router B forwards it back to A.

Without a limiting mechanism, the packet could circulate indefinitely.

IP includes a way to prevent that.

In IPv4, packets contain a Time To Live field, commonly called TTL.

In IPv6, the corresponding field is called Hop Limit.

In ordinary routing, each forwarding router decrements the relevant field.

When the limit is exhausted, the packet is discarded.

This prevents persistent routing loops from circulating packets forever.

### Traceroute exploits this behavior

Tools such as traceroute can probe the forwarding path by sending packets with progressively increasing hop limits.

Routers that discard packets because the hop limit expires may return ICMP diagnostic messages.

The tool can use these replies to reveal intermediate hops.

But traceroute doesn't guarantee a complete or perfectly accurate route diagram.

Some routers don't respond.

Some rate-limit ICMP diagnostics.

Some paths are asymmetric.

Load balancing may cause different probes to follow different forwarding paths.

And some networks hide internal topology.

So traceroute is a diagnostic instrument, not an omniscient map of the internet.

A useful result should be interpreted as evidence about observed probes, not necessarily an exhaustive account of every packet's journey.

## 10. IPv6: Same Routing Ideas, Different Addressing Machinery

We've spent most of the lecture using IPv4 addresses.

Now let's extend the mental model.

IPv6 uses 128-bit addresses rather than IPv4's 32-bit addresses.

This creates a vastly larger address space.

Addresses are usually written in hexadecimal groups separated by colons.

For example:

`2001:db8:42:20::17`

This address belongs to a range reserved for documentation examples.

IPv6 also uses prefix notation.

A `/64` fixes the first 64 bits, leaving 64 bits for the remaining address portion.

For example:

`2001:db8:42:20::/64`

Ordinary IPv6 local networks commonly use `/64` prefixes.

### The key difference in address planning

IPv4 administrators frequently divide address space into small subnets because public IPv4 addresses are scarce.

IPv6 provides a substantially larger allocation space.

Its design usually emphasizes scalable hierarchical allocation, routing aggregation, and stable addressing conventions rather than squeezing every possible host into a tiny subnet.

But address abundance doesn't remove routing.

An IPv6 host still needs to determine whether a destination is on-link or must be reached through a router.

It still uses routing information.

It still needs local delivery mechanisms.

And the network still requires security policies.

### IPv6 address categories

**Global unicast addresses** can provide globally unique network addressing, subject to actual routing configuration.

**Link-local addresses**, generally within `fe80::/10`, are used for communication on a local link.

**Unique Local Addresses**, within `fc00::/7`, support private-network-style addressing; locally assigned ULAs commonly begin with `fd`.

The IPv6 loopback address is `::1`.

These categories illustrate that not every address is intended to be publicly routed.

Address scope remains an important part of the architecture.

## 11. Neighbor Discovery: IPv6 Doesn't Use ARP

IPv6 doesn't use ARP.

Instead, it uses Neighbor Discovery, which relies on ICMPv6.

Neighbor Discovery performs several related tasks.

It can discover nearby routers.

It can resolve link-layer addresses.

It can determine whether a neighbor remains reachable.

It can help detect duplicate addresses.

It also supports important aspects of local IPv6 configuration.

### Neighbor Solicitation and Advertisement

To discover the link-layer address associated with an IPv6 neighbor, a host can send a Neighbor Solicitation message.

The relevant neighbor can respond with a Neighbor Advertisement.

Conceptually, this plays a role similar to ARP address resolution in IPv4.

But Neighbor Discovery is a broader protocol suite.

### Router Advertisements

IPv6 routers may send Router Advertisement messages containing information about the local network.

Hosts can use this information to identify routers, learn prefixes, and support automatic address configuration.

Stateless Address Autoconfiguration, commonly called SLAAC, is one mechanism for obtaining IPv6 addresses from advertised information.

Networks can also use DHCPv6 or manual addressing, depending on their requirements.

### Why ICMPv6 matters

A surprisingly common mistake is treating all ICMP traffic as optional diagnostic noise.

In IPv6, ICMPv6 participates in essential network functions.

Indiscriminately blocking Neighbor Discovery messages or other required ICMPv6 control traffic can break normal connectivity.

This is not simply a question of whether the host answers ping.

ICMPv6 is part of how the network operates.

Security controls should distinguish legitimate protocol requirements from unnecessary exposure.

## 12. Dual Stack: The Same Name Can Lead to Different Networks

Many environments support IPv4 and IPv6 simultaneously.

A hostname may have both A and AAAA records.

The A record provides IPv4 address information.

The AAAA record provides IPv6 address information.

We covered the DNS aspects in CS230-L04.

Now consider what happens afterward.

The client may attempt an IPv6 connection, an IPv4 connection, or a coordinated strategy using both address families.

Happy Eyeballs-style behavior can reduce delays when one family is unavailable or slow.

But the exact selection depends on the client implementation and environment.

### The misleading success

Suppose your API is reachable over IPv4.

Its IPv6 destination is incorrectly routed.

A developer tests the IPv4 address and reports that networking works.

Meanwhile, users whose clients attempt IPv6 may experience failures or delays.

Both observations can be correct.

They describe different network paths.

### Diagnose the address families separately

If a problem appears only for some networks or clients, establish which destination addresses were selected and which protocols were attempted.

Compare the IPv4 and IPv6 routes.

Check transport connectivity and TLS behavior independently.

A successful IPv4 connection does not prove IPv6 connectivity.

Likewise, a correct AAAA record does not prove the corresponding IPv6 route and service are operational.

This is particularly important when a service has recently introduced IPv6 support.

The additional address family creates another possible path to the application, with its own configuration and failure modes.

## 13. The Real Routing Table May Be More Complicated

So far, we've used a simple model:

Find the longest matching destination prefix.

Follow the selected route.

That's the right foundation.

But real systems may apply more elaborate rules.

### Multiple routing tables

Linux supports policy routing with multiple routing tables.

Routing rules can select different tables based on properties such as source address, packet marking, or other configuration.

A container networking plugin, VPN, or cloud networking component may create policy-based routes.

This means a simple glance at one table isn't always enough to explain the actual path.

### Source address selection

A host with multiple interfaces may have several possible source addresses.

The selected outgoing route and operating-system address-selection rules influence which source address is used.

This matters because return traffic must be able to reach the chosen source address.

A packet might leave through the intended interface but carry an inappropriate source address.

The destination may receive it, yet the reply may not return through a usable path.

### Asymmetric routing

The forward and return paths don't necessarily traverse the same routers.

Routing decisions are made independently in different parts of the network.

Asymmetric routes are not automatically wrong.

But they can interact badly with stateful firewalls, NAT devices, and network diagnostics.

A device that expects to observe both directions of a connection may reject traffic when the return path bypasses it.

We'll explore those consequences more fully in the next lecture.

### Virtualized and cloud networks

Inside a cloud environment, the routing logic may be implemented through virtual networking infrastructure rather than devices that resemble traditional physical routers.

A route table can still express destination-prefix forwarding decisions.

But there may be additional layers involving virtual interfaces, provider-managed gateways, and network security controls.

The conceptual model survives.

The implementation changes.

That is why learning routing as a set of decisions is more durable than memorizing the interface of one cloud provider.

## 14. Diagnose the VPN Incident Without Guessing

Let's return to our developer.

The VPN reports Connected.

The database hostname resolves to `10.42.20.17`.

The connection times out.

We need to determine where the packet actually goes.

### Step one: verify the selected destination

Confirm the IP address the client intends to contact.

If a hostname is used, compare its DNS resolution with the expected address.

This establishes the naming part of the journey.

It doesn't prove connectivity.

### Step two: inspect the route

Ask the operating system which route it selects for destination `10.42.20.17`.

The answer shows that the destination is treated as directly reachable through the hotel Wi-Fi interface.

The VPN's broader `/16` route doesn't win.

This is decisive evidence.

### Step three: explain why

The Wi-Fi network has a directly connected `/24` route.

The VPN installed a `/16`.

Both match the destination.

The `/24` is more specific.

The operating system follows that route.

There is no need to speculate about database connection limits, PostgreSQL authentication, or HTTP proxies yet.

The packet isn't reaching the intended corporate network path.

### Step four: identify the actual collision

The hotel uses `10.42.20.0/24`.

The company also assigns internal addresses within that range.

Two independent networks have overlapping address spaces.

Private IPv4 address ranges can be reused by different organizations.

That is normally convenient.

But it creates ambiguity when a machine participates in multiple private networks simultaneously.

This is a fundamental design problem, not merely a bad VPN client.

### Step five: choose a safe remedy

A VPN administrator may be able to install more specific routes for particular corporate destinations.

For example, a host-specific `/32` route can override a conflicting `/24` destination match, assuming the tunnel and forwarding configuration support the intended path.

But that may be a tactical workaround.

If multiple internal resources overlap with local networks, individually managing exceptions may become cumbersome.

A more durable solution may involve address planning, VPN policy, or network architecture changes that avoid ambiguous overlapping prefixes.

Don't casually change production routing without understanding the effect on other traffic.

### Step six: verify the fix

After the intended routing change, inspect the selected route again.

Confirm that the packet is directed through the expected VPN path.

Then test transport connectivity to the intended service.

Finally, establish application-level success through appropriate authentication and a legitimate database operation.

A correct route is necessary, but not sufficient.

The service must still be listening, network policies must permit traffic, and authentication must succeed.

## 15. The Boundary Between Routing and Security

One more distinction matters before we finish.

Suppose two departments occupy separate IP subnets.

The engineering team says:

"The finance database is secure because it is in another subnet."

That is not enough.

Subnet separation describes address organization and routing topology.

A router may forward traffic freely between the subnets.

If that is allowed, any host with a usable route may be able to attempt connections to the finance database.

Security depends on actual access controls.

Those may include firewalls, security groups, network policies, and application-level authentication and authorization.

### Route, permission, and application

Think of three separate questions.

**Route:** Is there a forwarding path toward the destination?

**Permission:** Do applicable network controls allow the traffic?

**Application:** Is the service listening, and does it authorize the requested operation?

A packet can have a valid route and still be blocked.

A TCP connection can succeed while TLS authentication fails.

An authenticated connection can succeed while the application rejects the requested business operation.

These are different boundaries.

When diagnosing a connectivity problem, identify the first one that fails.

## 16. The Oral Examination

Answer each question aloud before reading the solutions. Explain the mechanism rather than merely naming it.

### Challenge 1 — Calculate a Subnet

A machine has address `192.168.10.150/26`.

What is its network prefix?

What is the complete range of the subnet?

Which addresses are normally assignable to hosts in a conventional IPv4 subnet?

Would `192.168.10.200` belong to the same subnet?

### Challenge 2 — Which Route Wins?

A laptop has these routes:

- `192.168.1.0/24` through Wi-Fi.
- `10.42.0.0/16` through a VPN.
- `0.0.0.0/0` through its default gateway.

Which route is selected for `10.42.20.17`?

Now add a directly connected route for `10.42.20.0/24`.

Which route wins, and why?

### Challenge 3 — The Next-Hop Confusion

Your laptop wants to connect to `203.0.113.80`.

Its next hop is the router at `192.168.1.1`.

Which address appears as the IP packet's destination?

Which device's MAC address does the laptop normally need for local delivery?

### Challenge 4 — The Overlapping VPN

A developer connects to the company VPN while using a hotel network.

The hotel and company address spaces overlap.

DNS is correct, but the connection to an internal service fails.

How would you prove that a route collision is responsible?

### Challenge 5 — The Invisible Router

The routing table contains a valid-looking route toward a gateway.

But packets still cannot leave the local network.

Why might the route be correct while delivery fails?

### Challenge 6 — The IPv6 Mystery

An API works over IPv4 but is intermittently unreachable for users with IPv6 connectivity.

The service has both A and AAAA DNS records.

What would you investigate?

### Challenge 7 — The Traceroute Trap

Traceroute shows several unanswered hops.

An engineer concludes that the packet must have been dropped permanently at the first unanswered hop.

Why is that conclusion unsafe?

### Challenge 8 — The Security Illusion

A database runs in a different subnet from the API.

An engineer says this makes it unreachable to unauthorized clients.

What additional evidence would be required to support that security claim?

## 17. Solutions and Discussion

### Solution 1 — A `/26` block contains 64 addresses

A `/26` fixes 26 bits and leaves six bits variable.

Two to the power of six equals 64.

The address `192.168.10.150` falls within:

`192.168.10.128/26`

The block runs from `.128` through `.191`.

In a conventional IPv4 subnet, `.129` through `.190` are normally assignable host addresses.

The address `.200` belongs to the next `/26` block beginning at `.192`.

The important skill is deriving the block from the prefix length rather than memorizing the result.

### Solution 2 — The most specific matching destination route wins

Initially, the `/16` VPN route is more specific than the default `/0` route, so traffic toward `10.42.20.17` uses the VPN.

After adding the `10.42.20.0/24` route, that route becomes more specific than the VPN's `/16`.

It therefore takes precedence under ordinary longest-prefix matching.

This remains true even if the engineer personally wants the traffic to use the VPN.

### Solution 3 — IP and link-layer destinations are different

The IP packet's final destination is `203.0.113.80`.

For ordinary Ethernet-style local delivery, the laptop needs the link-layer address of its selected next-hop router at `192.168.1.1`.

The local frame goes to the router.

The IP packet remains addressed to the remote destination.

### Solution 4 — Inspect the actual selected route

Determine the resolved destination address and ask the operating system which route it selects.

Compare the local network prefix with the corporate VPN routes.

If the local route is more specific and points toward the wrong network, that explains the behavior.

A successful VPN connection alone doesn't establish correct per-destination routing.

### Solution 5 — Local delivery may be broken

A valid route may identify a next hop whose link-layer address cannot be resolved.

The interface may be down.

The gateway may be unavailable.

A virtual network may have a misconfigured link or policy.

Route selection and successful local delivery are separate requirements.

### Solution 6 — Separate the address families

Inspect both A and AAAA DNS answers.

Determine which address the affected client actually attempts.

Check IPv6 route selection, Neighbor Discovery behavior, network filtering, transport connectivity, and service configuration.

Compare the results with IPv4.

A successful IPv4 test is not proof that the IPv6 path works.

### Solution 7 — A missing ICMP response isn't proof of forwarding failure

Routers may decline to generate diagnostic responses, rate-limit them, or respond through unexpected paths.

Load balancing can also affect traceroute results.

An unanswered intermediate hop doesn't necessarily mean packets cannot continue beyond it.

Interpret the complete set of observations and test actual destination connectivity.

### Solution 8 — Subnets are not automatically access controls

Separate subnets establish routing boundaries, but a router may forward traffic between them.

Verify the actual routing and network-permission rules.

Then verify application authentication and authorization.

Security requires enforceable policies, not merely address organization.

## 18. The Mental Model Worth Keeping

IP networking becomes easier to understand when you treat it as a series of forwarding decisions.

An IP address identifies a destination.

A prefix identifies an address range.

The routing system selects a matching forwarding rule, ordinarily preferring the longest matching destination prefix.

A next hop determines where the packet goes locally.

ARP or IPv6 Neighbor Discovery can help map a local network-layer address to link-layer delivery information.

Routers repeat forwarding decisions across networks.

Routing protocols and control-plane systems maintain the information used by those decisions.

And the existence of a route doesn't prove that traffic is permitted or that the destination application is available.

Whenever a connection fails, begin with three questions:

**Which destination did the application choose? Which route did the operating system select? Could the packet actually reach the selected next hop?**

Those questions will eliminate a surprising amount of network guesswork.

## 19. Next Lecture — CS230-L06: Private Networks, NAT, and Cloud Reachability

We now understand how a packet obtains its destination and moves through a routed network.

But a new problem appears when networks use private IPv4 addresses.

Your laptop might use `192.168.1.42`.

Millions of other devices might use the same address.

How can they all communicate with the public internet?

And why can a customer reach an application through a public cloud load balancer while the application's own private backend cannot reach an external payment provider?

The next lecture will investigate private address spaces, NAT and port translation, public and private cloud subnets, internet and NAT gateways, stateful security controls, and the return path.

We'll also encounter a particularly unpleasant network failure: small packets succeed, but larger HTTPS requests disappear because the path cannot carry them.

We know how the router chooses the road.

Next, we'll examine what happens when the packet crosses the boundary between private and public networks.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — Your Computer's Routing Decisions

**Goal:** Inspect the actual addresses and routes on your computer, calculate prefixes, and explain which route would carry a packet.

You don't need a cloud account or special infrastructure. The exercises are read-only unless explicitly described otherwise.

### Lab A — Inspect local interfaces

On Linux:

```bash
ip -br address
ip -4 route
ip -6 route
```

On macOS:

```bash
ifconfig
netstat -rn
```

On Windows PowerShell:

```powershell
Get-NetIPConfiguration
Get-NetIPAddress
Get-NetRoute
```

Identify your active interface, its IPv4 and IPv6 addresses, and the available default routes.

### Lab B — Ask the system to select a route

On Linux:

```bash
ip route get 203.0.113.80
```

On macOS:

```bash
route -n get 203.0.113.80
```

On Windows, inspect the destination against the routes shown by:

```powershell
route print
```

The address `203.0.113.80` is reserved for documentation. We are using it only as an example for route selection.

Do not attempt to connect to it.

**Question:** Which interface and gateway would be selected for an otherwise unmatched public IPv4 destination?

### Lab C — Calculate subnets with Python

Python's standard library contains `ipaddress`.

Create `subnets.py`:

```python
import ipaddress

addresses = [
    "192.168.10.150/26",
    "192.168.1.42/24",
    "10.42.20.17/16",
    "2001:db8:42:20::17/64",
]

for address in addresses:
    interface = ipaddress.ip_interface(address)
    network = interface.network

    print(f"Address: {interface.ip}")
    print(f"Network: {network}")
    print(f"Addresses in block: {network.num_addresses}")
    print()
```

Run it:

```bash
python subnets.py
```

Before viewing each result, calculate the network prefix manually.

Then compare your reasoning with Python's output.

### Lab D — Simulate longest-prefix matching

Consider the following routes.

```text
192.168.1.0/24    Wi-Fi
10.42.0.0/16      VPN
10.42.20.0/24     Local
0.0.0.0/0         Default
```

Use Python to identify matching prefixes:

```python
import ipaddress

destination = ipaddress.ip_address("10.42.20.17")

routes = [
    ("192.168.1.0/24", "Wi-Fi"),
    ("10.42.0.0/16", "VPN"),
    ("10.42.20.0/24", "Local"),
    ("0.0.0.0/0", "Default"),
]

matches = []

for prefix, interface in routes:
    network = ipaddress.ip_network(prefix)

    if destination in network:
        matches.append((network.prefixlen, prefix, interface))

for item in sorted(matches, reverse=True):
    print(item)

print("Selected:", max(matches))
```

**Explain:** Why does the selected route not necessarily match the connection you intended to use?

### Lab E — Inspect the neighbor table

On Linux:

```bash
ip neigh
```

On macOS:

```bash
arp -a
```

On Windows:

```powershell
Get-NetNeighbor
```

Inspect the relationships between local IP addresses and link-layer addresses.

These entries may be incomplete or empty if the host hasn't recently communicated with relevant neighbors.

**Question:** Why doesn't the table need to contain the MAC addresses of every remote website you've visited?

### Lab F — Trace a route

Use a legitimate reachable destination you control or a public service that permits diagnostic probes.

On Linux:

```bash
traceroute YOUR_DESTINATION
```

On macOS:

```bash
traceroute YOUR_DESTINATION
```

On Windows:

```powershell
tracert YOUR_DESTINATION
```

Observe the intermediate hops that respond.

Some may remain unanswered.

**Question:** Does an unanswered hop prove that the destination is unreachable?

Explain why not.

### Lab G — The VPN overlap investigation

Assume a developer has the following configuration.

```text
Wi-Fi address:         10.42.20.42/24
Corporate VPN route:   10.42.0.0/16
Database address:      10.42.20.17
```

Write a diagnosis answering:

1. Which routes match the database destination?
2. Which route is most specific?
3. What will the operating system attempt to do?
4. Which observation would confirm the hypothesis?
5. What temporary and permanent remedies could be considered?
6. Why should an engineer avoid modifying production routes without understanding the consequences?

### Lab H — Design a small address plan

An office has the private IPv4 block:

`10.60.0.0/16`

It needs separate network ranges for employee devices, laboratory machines, application servers, and databases.

Propose four non-overlapping subnet prefixes.

For each prefix, calculate the total number of IPv4 addresses.

Then explain which network traffic should be permitted between the subnets.

Remember that address separation and security policy are distinct concerns.

---

## Further Reading

1. [RFC 4632 — Classless Inter-Domain Routing](https://www.rfc-editor.org/rfc/rfc4632.html) — Prefix notation, aggregation, and longest-prefix forwarding.
2. [RFC 826 — Address Resolution Protocol](https://www.rfc-editor.org/rfc/rfc826.html) — IPv4 local address resolution.
3. [RFC 1812 — Requirements for IPv4 Routers](https://www.rfc-editor.org/rfc/rfc1812.html) — Router forwarding behavior.
4. [RFC 4271 — Border Gateway Protocol 4](https://www.rfc-editor.org/rfc/rfc4271.html) — Inter-domain routing.
5. [RFC 4861 — IPv6 Neighbor Discovery](https://www.rfc-editor.org/rfc/rfc4861.html) — Router and neighbor discovery.
6. [RFC 4862 — IPv6 Stateless Address Autoconfiguration](https://www.rfc-editor.org/rfc/rfc4862.html) — IPv6 address configuration.
7. [RFC 4291 — IPv6 Addressing Architecture](https://www.rfc-editor.org/rfc/rfc4291.html) — IPv6 address types and structure.
8. [RFC 8305 — Happy Eyeballs Version 2](https://www.rfc-editor.org/rfc/rfc8305.html) — Connection establishment across IPv4 and IPv6.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is deliberately fenced for visual revision.*

```text
CS230-L05 — IP ADDRESSING, SUBNETS, AND ROUTING

CORE PATH

  Destination IP
      -> Route selection
      -> Next-hop selection
      -> Local link delivery
      -> Router forwarding
      -> Destination network

IP ADDRESS

  Logical network-layer address
  Not necessarily permanent host identity
  Multiple interfaces/addresses per host possible

IPv4
  32 bits
  Dotted decimal: 192.168.10.150

IPv6
  128 bits
  Hexadecimal: 2001:db8:42:20::17

CIDR

  /p = first p address bits form prefix

  IPv4 address count:
    2^(32-p)

  /24 = 256 addresses
  /26 = 64 addresses
  /30 = 4 addresses
  /32 = single address

SUBNET CALCULATION

  192.168.10.150/26

  Network: 192.168.10.128/26
  Range:   192.168.10.128 - .191
  Hosts:   .129 - .190 (conventional IPv4)
  .200 is outside this /26

  /31 has special point-to-point use

ROUTING TABLE

  Destination prefix + forwarding instructions
  Directly connected routes
  Gateway / next-hop routes
  Default route

  IPv4 default: 0.0.0.0/0
  IPv6 default: ::/0

LONGEST-PREFIX MATCH

  /24 outranks /16 for destinations matching both
  /16 outranks /0

  More specific matching route generally wins
  Route metrics resolve other competing choices
  Policy routing can introduce additional rules/tables

NEXT HOP VS DESTINATION

  Destination:
    Final IP address

  Next hop:
    Local forwarding target

  IP destination generally remains the same
  Link-layer delivery changes hop by hop
  NAT can deliberately translate IP addresses

ARP (IPv4)

  Resolves local IPv4 -> link-layer address
  Used for ordinary Ethernet-style local delivery
  Not used to discover distant server MAC addresses

IPv6 NEIGHBOR DISCOVERY

  Uses ICMPv6, not ARP
  Neighbor Solicitation / Advertisement
  Router Solicitation / Advertisement
  Reachability and duplicate-address detection
  Supports SLAAC

  Do not blindly block essential ICMPv6

ROUTER

  Selects next forwarding path for packet
  Control plane builds route knowledge
  Data plane forwards packets

BGP

  Inter-domain prefix reachability
  Policy-driven routing
  Not geographic shortest-path calculation

TTL / HOP LIMIT

  Prevents endless routing loops
  Decremented by forwarding routers
  Traceroute uses expiry-related diagnostics

  Missing traceroute hop != definite packet loss

IPv6

  Global unicast
  Link-local: fe80::/10
  ULA: fc00::/7
  Loopback: ::1
  /64 common for ordinary local networks

DUAL STACK

  DNS A -> IPv4
  DNS AAAA -> IPv6
  Paths may differ
  Happy Eyeballs can coordinate attempts
  IPv4 success != IPv6 success

COMMON FAILURES

  Correct DNS, wrong route
  Overlapping VPN/local prefixes
  Missing default route
  Next hop unreachable
  ARP/Neighbor Discovery failure
  Wrong source address
  Policy routing mismatch
  IPv4 works, IPv6 fails
  Return path differs from forward path

THREE SEPARATE CONTRACTS

  Route:
    Is there a forwarding path?

  Permission:
    Are network controls allowing traffic?

  Application:
    Is the service listening and authorized?

DIAGNOSTIC QUESTIONS

  Which IP did the client select?
  Which route actually wins?
  Which interface/next hop is selected?
  Can local delivery succeed?
  Does the return path work?
  Which policy or application boundary follows?

SENIOR LINE

  "IP communication is a chain of forwarding decisions.
   I distinguish destination addresses, network prefixes,
   selected routes, next-hop delivery, and application
   connectivity, and I inspect the actual route rather
   than assuming a connected VPN or healthy DNS implies
   reachability."
```
