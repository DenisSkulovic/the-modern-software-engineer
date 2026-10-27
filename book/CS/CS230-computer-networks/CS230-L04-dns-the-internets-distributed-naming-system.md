---
id: CS230-L04
course: CS230
title: "DNS: The Internet's Distributed Naming System"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS230-L03
next: CS230-L05
---



# CS230 — Computer Networks and Web Protocols

## Lecture 04: DNS — The Internet's Distributed Naming System

*Why changing one DNS record can affect millions of users, why different computers disagree about the same hostname, and why the internet's naming system is considerably more sophisticated than a phone book.*

---

# Part I — Intuition

*The internet doesn't have one giant phone book. It has a hierarchy of responsibilities and a lot of cached answers.*

Look at the opening diagram for half a minute, then listen. This pass builds one mental picture. Part II develops the same picture with full technical depth.

### The picture to carry in your head

This is what can happen **on a cache miss**, not a mandatory sequence for every lookup.

```mermaid
flowchart LR
    B["Browser / OS"] --> R["Recursive resolver\nAsk on user's behalf"]
    R --> T["Root\nWhere is .com?"]
    T --> U["TLD nameservers\nWho serves example.com?"]
    U --> A["Authoritative DNS\nWhat is api.example.com?"]
    A -. "Answer" .-> R
    R -. "Cache + return" .-> B
```

The example uses the reserved documentation domain `example.com`. The hierarchy is rooted in DNS delegation, not a chain of machines transferring the website itself.

**The question:** Who is responsible for answering the question, and who is merely remembering an earlier answer?

---

### 1. A migration that worked for half the customers

Your booking API used to point at an old deployment. You switch the hostname's DNS record to the new deployment. A colleague in Vilnius reaches the new API, while someone in London still reaches the old one. The authoritative DNS provider shows the updated record, so why are customers seeing two different answers?

Because a hostname doesn't live inside one magical worldwide lookup table that updates every browser instantly. DNS involves authoritative information and cached copies held by several systems.

Start with what the browser wants. It needs one or more network addresses for a name such as `api.example.com`. It may already have a usable answer in a local cache. The operating system or another configured resolution layer may also have one. If an answer isn't available there, a recursive resolver can perform the search on the client's behalf.

Notice our first distinction. The **recursive resolver** is the helper answering clients. The **authoritative nameserver** is the source designated to answer for a DNS zone. They are different jobs, even if a particular provider runs several kinds of infrastructure.

### 2. Who knows whom?

Imagine the recursive resolver has never looked up our hostname and has no helpful cached delegation information.

It doesn't need to ask every server on the planet. It starts at the DNS hierarchy. Root nameservers can direct it toward the relevant top-level domain, such as `.com`. The TLD nameservers can direct it toward the authoritative nameservers for `example.com`. The authoritative server can answer for the requested name or supply information relevant to completing resolution.

The root doesn't store the live IP address of every website. The TLD doesn't host the website. And the authoritative DNS server isn't necessarily the machine running the API.

They divide the responsibility for **knowing where the answer should be found**.

In many real lookups, the resolver already remembers the delegation and needs fewer upstream queries. The diagram is the logic of authority, not a promise of four network trips every time.

**Checkpoint:** Does querying a DNS root server download an API response? **No.** It helps locate DNS authority; fetching the API happens later with another protocol.

### 3. A record is an answer to a particular question

DNS records have types because "What is this hostname's address?" isn't the only possible question.

An **A record** gives an IPv4 address. An **AAAA record** gives an IPv6 address. A **CNAME** makes one name an alias of another name, which the resolver may need to follow to obtain the requested address. An **MX record** helps identify mail exchangers. **TXT** records carry text used for several application and verification purposes.

A record type isn't a command to open a connection. It supplies information. For example, an A record doesn't guarantee the target server is reachable or healthy.

A DNS answer may also depend on how the provider selects responses: different users or resolvers can receive different appropriate endpoints. DNS-based traffic steering is useful but doesn't replace health, connection, TLS, or application behavior.

### 4. Why two computers can disagree

Now consider **TTL**, the time-to-live attached to cached DNS information. A resolver can cache a record for a permitted period and continue returning it until it needs to refresh, subject to its implementation and policies.

Suppose a resolver obtained the old address shortly before the migration and its cached answer has substantial lifetime remaining. Another resolver queries after the update and receives the new address. The two clients can temporarily reach different deployments while the authoritative source has already changed.

This isn't necessarily DNS malfunction. It's the consequence of caching as designed.

Changing a record doesn't erase previously distributed cached answers. Lowering TTL only at the moment of a migration also doesn't retroactively shorten TTLs already cached. That's why carefully planned migrations may lower relevant TTLs ahead of time, wait for old caches to age out, and keep the old endpoint functional during transition.

**Checkpoint:** If `dig` using an authoritative server shows the new record, does that prove every user sees it? **No.** Their resolvers and caches may still have valid earlier answers.

### 5. Sometimes absence gets cached

Suppose a client asks for a hostname that doesn't exist yet and receives a negative DNS answer, such as NXDOMAIN. That negative result can also be cached according to DNS rules.

You create the hostname a minute later. Some clients still report that it doesn't exist because their resolver remembers the earlier negative response.

The relevant mental point: DNS caching doesn't store only successful addresses. It can store knowledge that a particular question had no answer under earlier authoritative information.

### 6. DNS privacy, integrity, and identity are separate questions

If someone sees an ordinary DNS lookup, they may infer which hostname was queried. Mechanisms such as DNS over HTTPS or DNS over TLS protect the transport between client and configured resolver, under their respective trust assumptions.

**DNSSEC** addresses a different concern: cryptographic authentication of DNS data through a chain of trust for signed zones. It doesn't encrypt ordinary DNS queries. And neither DNSSEC nor encrypted DNS replaces TLS certificate validation for the eventual HTTPS connection.

That distinction fits the entire course. Finding an address, ensuring the DNS information is authentic, keeping queries private, and authenticating a remote HTTPS service are distinct responsibilities.

### 7. The minute-long replay

The browser needs an address. It checks whether it or another local layer already knows. A recursive resolver may answer from cache or follow DNS delegations through the hierarchy to an authoritative source. It returns records with applicable caching information. Different resolvers may temporarily report different still-cached answers after a change. The browser then uses the resulting address as input to the next stage of communication; DNS itself hasn't opened the API connection.

#### Three questions before L04

1. Recursive resolver versus authoritative server? **One searches/caches for clients; the other answers for its zone.**
2. Why did London reach the old deployment? **A usable old record may still have been cached.**
3. Does a valid A record prove the API is healthy? **No.** It answers an address question, not a reachability or application-health question.


### Pocket map — screen reference

```text
CLIENT         wants address for hostname
RECURSIVE      answers for client, uses cache or queries hierarchy
ROOT           directs toward TLD authority
TLD            directs toward domain's authoritative nameservers
AUTHORITATIVE  provides records for zone
A              IPv4 address
AAAA           IPv6 address
CNAME          alias to another DNS name
TTL            cached answer lifetime under caching rules
NEGATIVE CACHE failed/nonexistent-name answer may be retained
DNSSEC         authenticated DNS data; not query confidentiality
DoH / DoT      encrypted transport client ↔ resolver
TLS            separate later authentication of HTTPS server

DNS works ≠ route works ≠ TCP works ≠ TLS works ≠ API works
```

*The intuition pass ends here.*

---

# Part II — Deep Dive

# 1. The Deployment That Worked for Only Half the Internet

It's nine in the morning. Your company operates a successful hotel-booking platform, and today you're migrating its public API to a new infrastructure provider.

The new servers are running. Health checks pass. Database connectivity is verified. TLS certificates are installed. You've even tested several complete booking workflows against the new environment.

Everything looks ready.

The final step appears almost insultingly simple. The existing API hostname points to the old infrastructure, and you need it to point to the new infrastructure. Your DevOps colleague opens the DNS dashboard, changes the record, clicks Save, and announces that the migration is complete.

At nine fifteen, things get interesting.

Some customers can search hotels, select rooms, and complete reservations. Others cannot even log in. Your colleague in Frankfurt reports that everything works, while another colleague in London is still hitting the old API servers.

A customer in Vilnius can access the website through mobile internet but not through their home Wi-Fi. Meanwhile, the authoritative DNS provider's dashboard clearly displays the new address.

The engineering team starts arguing.

One developer blames the CDN. Another thinks the ISP has a broken cache. Someone suggests restarting the API containers, which is a creative solution considering that the requests aren't reaching those containers in the first place.

Finally, somebody declares that DNS is still propagating.

That phrase is not entirely meaningless, but it often substitutes for an explanation rather than providing one. What exactly is propagating? Between which machines? Who decides when the old information expires? And why can a perfectly healthy application remain inaccessible long after its DNS configuration has been corrected?

To answer those questions, we need to stop treating DNS as a function that converts a name into an address and examine it as a distributed system with its own authority model, caches, protocols, and failure modes.

By the end of this lecture, you should be able to explain not merely what DNS does, but how resolution works, why results differ, what happens during a migration, and how to distinguish a genuine DNS problem from a broken network connection.

---

# 2. A Domain Name Is an Identity, Not a Machine

Begin with a deceptively simple question.

What does `api.stays.example` actually identify?

A beginner might say that it identifies a server. An experienced developer might say it resolves to an IP address. Both answers are useful approximations, but neither captures the complete relationship.

The hostname is a name within a globally organized namespace. Applications use it as a relatively stable identity for reaching a service. DNS supplies information that helps clients locate that service, without requiring its physical or network location to remain fixed.

Imagine that our API originally runs on one virtual machine. Later, we place it behind a load balancer. Eventually, we migrate it to a CDN-connected architecture spanning several regions.

The hostname can remain unchanged throughout these transformations. What changes is the infrastructure associated with it.

This distinction is an example of **indirection**: separating a stable reference from an implementation that may change.

Indirection is everywhere in software engineering. A function name hides its implementation, a database index hides physical storage organization, and a service interface hides the machines performing the work. DNS applies a related idea across the internet.

Now consider the reverse relationship.

Could multiple hostnames resolve to the same IP address?

Absolutely. One machine, load balancer, or CDN endpoint may serve hundreds or thousands of hostnames. The IP address gets packets to an endpoint, while protocols such as TLS and HTTP help identify the intended service.

Could one hostname resolve to several IP addresses?

Certainly. It might have multiple IPv4 addresses, multiple IPv6 addresses, or different answers depending on the resolver and infrastructure configuration.

So the relationship is not one name equals one machine. It is a naming system that provides records associated with names. What clients subsequently do with those records depends on the record type, application, and network configuration.

That brings us to the first essential mental distinction:

**DNS resolution is not the same operation as establishing a network connection.**

The DNS system may supply an address. It does not thereby establish a TCP connection, authenticate an HTTPS server, confirm that the application is healthy, or guarantee that packets can reach the destination.

Those are separate responsibilities belonging to other layers of the system.

---

# 3. Who Actually Answers a DNS Question?

Suppose your browser needs to connect to `api.stays.example`.

Where does it obtain the address?

You might imagine it asking one DNS server somewhere on the internet. But even before a DNS packet is transmitted, several other possibilities exist.

Your application may reuse an existing connection. The browser might have cached the necessary information. The operating system may have a local DNS cache, or there may be a hosts-file override that maps the name directly to an address.

Only when an appropriate answer isn't already available does a resolver need to obtain additional naming information.

Here, we encounter several participants that developers often lump together under the phrase "DNS server."

## 3.1 The stub resolver

An application generally doesn't implement the entire DNS protocol hierarchy itself. It asks a resolution facility to obtain information about a hostname.

The operating system commonly provides this interface through resolver libraries. Applications can request address information and receive candidate addresses without individually contacting the root, top-level-domain, and authoritative DNS servers.

The relatively small component making such requests is commonly called a **stub resolver**.

A stub resolver is a client of DNS resolution services. It typically delegates the difficult work rather than walking the global hierarchy itself.

There are complications, of course. Modern browsers may maintain their own DNS caches or use DNS over HTTPS, sometimes bypassing the operating system's configured DNS server. Corporate networking software and VPNs can also change how names are resolved.

That is already one reason why typing a DNS query into a terminal doesn't always reproduce the exact resolution behavior of a browser.

## 3.2 The recursive resolver

The stub resolver commonly sends its query to a **recursive resolver**.

This might be operated by your internet service provider, a company, a public DNS service, or a local caching service that forwards queries elsewhere.

A recursive resolver has a more demanding responsibility: given a name and a requested record type, it attempts to obtain an answer on behalf of its client.

If the answer is cached, the resolver can return it immediately. Otherwise, it may need to contact several DNS servers to discover which organization is authoritative for the name.

The word *recursive* describes the service offered to the client: the client asks for a result and expects the resolver to pursue the necessary resolution work.

Interestingly, the resolver usually performs that work through **iterative queries**. It contacts one server, receives information about where to ask next, and continues until it can return an answer or a failure.

This is the crucial distinction between a recursive resolver and an authoritative DNS server.

## 3.3 The authoritative server

An authoritative DNS server publishes DNS information for a zone under its responsibility.

It doesn't generally need to ask the rest of the internet what records its own zone contains. Its configured data is the source of authority for those records.

Think of it this way.

The recursive resolver is the researcher trying to answer a question. The authoritative server is an institution responsible for publishing the answer for a particular part of the namespace.

An authoritative server does not necessarily know where your application actually runs. It only knows the records it has been configured to serve. If somebody enters an obsolete IP address into those records, the server can faithfully provide the wrong operational destination.

This matters because DNS authority is about responsibility for naming information, not proof of application health.

---

# 4. Following a DNS Query Through the Hierarchy

Let's reconstruct a cold DNS lookup, assuming our recursive resolver has no useful cached information.

We want address records for `api.stays.example.com`.

The DNS namespace is hierarchical, with labels separated by dots. Conceptually, the fully qualified name ends at a root represented by a trailing dot, although ordinary applications usually omit that final dot.

The resolver needs to find the appropriate authority for the name.

## 4.1 Start at the root

The recursive resolver has information about the DNS root server system, including root-server addresses distributed through its configuration.

It asks a root server where to find the information needed for `api.stays.example.com`.

The root server does not need to know the IP address of our API.

Instead, it can direct the resolver toward the nameservers responsible for the `.com` top-level domain.

This is a **referral**.

The root server has supplied information about the next authority to consult, rather than the final application address.

Notice how elegantly this scales. Root servers don't need to store the address records for every website on Earth. They primarily participate in organizing the next level of delegation.

## 4.2 Ask the top-level domain

The recursive resolver contacts an appropriate `.com` nameserver.

Once again, the nameserver does not necessarily know the address of our API. But it knows about delegations beneath `.com`.

It directs the resolver toward the authoritative nameservers responsible for `example.com`.

Those nameservers may belong to the company, a managed DNS provider, or an infrastructure platform.

The recursive resolver now knows which authority is responsible for answering questions about records in that zone, subject to any further delegations.

## 4.3 Ask the authoritative server

The resolver asks the appropriate authoritative server for the requested address record.

Perhaps the server responds with an IPv4 address. Perhaps it responds with an alias to another hostname, requiring additional resolution.

For example, the company might configure `api.stays.example.com` as an alias pointing to an endpoint controlled by a CDN provider.

The resolver must then obtain the relevant address information for that target name. Depending on its cache and the response it has already received, this may require further queries.

Eventually, the recursive resolver returns the resulting information to the original client.

The browser now has candidate addresses with which it can attempt a connection.

## 4.4 Why the entire hierarchy isn't queried constantly

That description sounds expensive.

Imagine millions of browsers repeatedly asking recursive resolvers to begin at the DNS root every time they load a webpage. The system would be terribly inefficient.

Fortunately, caching applies not only to final address records but also to other useful DNS information, including delegations.

A resolver that recently learned which nameservers handle `.com` can reuse that information while it remains valid. Likewise, it may already know the authoritative nameservers for `example.com`.

In practice, a routine lookup may require no external query at all. Another lookup might need only one query to an authoritative server. A truly cold lookup may involve several steps.

DNS therefore achieves global scalability through a combination of hierarchical authority, distributed operation, and aggressive reuse of information.

### The delegated-zone complication

Suppose our company wants a separate team to administer `internal.example.com`.

It can delegate that subdomain to a different set of authoritative nameservers using NS records at the appropriate parent zone.

The namespace remains one tree, but administrative responsibility has been divided.

There is an interesting bootstrapping problem here. What if the nameserver for a domain is itself named inside that same domain? How can the resolver discover its address without first resolving a name that depends on the delegation?

This is one reason DNS has the concept of **glue records**. Address information supplied with a referral can help a resolver reach nameservers whose names would otherwise create a circular dependency.

You do not need to memorize every DNS delegation rule to work as a backend developer. You should, however, understand the deeper principle: the system is not a centralized catalogue. It is a tree of delegated authority, and resolution works by following that authority.

---

# 5. DNS Records: Questions Have Types

We've repeatedly spoken about resolving a name into an address. But DNS is not fundamentally limited to addresses.

Its data model contains **resource records**, each associated with a name, a record type, a class, a time-to-live value, and type-specific data.

The internet class, represented by IN, is the usual one encountered in everyday DNS work.

A query therefore doesn't simply ask, "What is this domain?"

It asks a more precise question, such as, "What IPv4 address records exist for this hostname?" or "Which nameservers are responsible for this domain?"

Let's examine the record types that matter most to application engineers.

## 5.1 A and AAAA: Address information

An **A record** associates a name with an IPv4 address.

An **AAAA record** associates a name with an IPv6 address.

A name can have multiple address records. Clients may receive several candidate addresses and attempt to connect using one or more of them.

For example, a company may operate a service accessible through both IPv4 and IPv6. Its DNS records allow clients to discover both possibilities, while the client and network environment determine which connection attempts succeed.

Do not assume that returning multiple addresses automatically creates a sophisticated load balancer.

DNS can distribute or advertise address choices, but it does not inherently measure application health, preserve user sessions, or guarantee that every client distributes its requests evenly.

Those capabilities belong to more specialized infrastructure.

## 5.2 CNAME: Following an alias

A **CNAME record** declares that one DNS name is an alias of another name.

Imagine that our company owns `api.stays.example.com`, but the public endpoint is managed by a CDN provider.

Instead of maintaining the provider's changing IP addresses, we can point our hostname to the provider's assigned hostname.

The DNS resolution process then follows the alias and obtains the necessary records associated with the target.

This creates another layer of indirection. The company controls its public identity, while the provider manages the underlying endpoint addresses.

However, a CNAME is not a magical HTTP redirect. The browser does not navigate to a new URL merely because DNS resolution encounters an alias.

The requested HTTPS hostname remains the application's intended identity.

There is also a technical restriction worth knowing. A conventional CNAME cannot coexist with ordinary records at the same owner name, which makes it unsuitable at the apex of a DNS zone that must contain records such as SOA and NS.

Managed DNS providers sometimes offer features called ALIAS, ANAME, or CNAME flattening to provide similar operational convenience. These are provider-side mechanisms rather than the ordinary CNAME record type.

Modern HTTPS and SVCB records also introduce standardized service-binding capabilities, including aliasing arrangements, although client and infrastructure support must still be considered.

## 5.3 Records beyond web addressing

Other DNS records serve different purposes.

**NS records** identify authoritative nameservers and participate in delegation.

**SOA records**, short for Start of Authority, contain administrative information about a zone and play an important role in negative caching.

**MX records** identify mail exchangers for a domain, while **TXT records** carry textual information used by mechanisms such as domain ownership verification and email authentication.

**CAA records** let a domain owner express which certificate authorities are authorized to issue certificates for that domain, under the applicable certificate-issuance policies.

**SRV records** can advertise service endpoints, including ports, for applications designed to use them.

The important insight is not that you should memorize a catalogue of record names.

It is that DNS forms a general-purpose naming database with typed information. Different applications can ask different questions about the same name.

A hostname with no A record is not necessarily nonexistent. It might have other record types, or its configuration might deliberately contain no IPv4 address.

That distinction will become particularly important when we investigate failed lookups.

---

# 6. DNS Caching: Why Two Computers Can Disagree

Return to our migration incident.

At nine in the morning, the authoritative DNS record changes from the old infrastructure to the new infrastructure.

Yet some clients continue receiving the old address.

To understand why, we need to examine the **time to live**, commonly abbreviated TTL.

## 6.1 What the TTL actually controls

DNS records carry TTL values expressed in seconds.

For a caching resolver, a TTL describes how long the associated data may ordinarily be reused before it must be refreshed or otherwise handled according to the resolver's applicable caching policies.

Suppose the authoritative A record for our API has a TTL of one hour.

At 8:59, a recursive resolver obtains the old address and caches it with a remaining lifetime of one hour.

At 9:00, we update the authoritative record to the new address.

What does the recursive resolver do at 9:01?

It doesn't necessarily contact the authoritative server. It still possesses a cached record that has not expired.

From its perspective, the cached information is still usable.

It may continue supplying the old address until approximately 9:59, even though the authoritative configuration was changed almost an hour earlier.

Meanwhile, another recursive resolver might have no cached copy at all. Its first query after nine o'clock retrieves the new address immediately.

Both resolvers can be behaving correctly according to the protocol's caching model.

This explains the apparently contradictory observations from our colleagues in Frankfurt, London, and Vilnius.

They are not necessarily consulting the same recursive resolver, and even if they are, their applications may have different local caches or existing connections.

**There is no single global DNS cache that must synchronously update before a change becomes real.**

The process is better understood as independent caches expiring and obtaining updated information.

## 6.2 Why reducing the TTL at deployment time doesn't solve the problem

Here is a classic operational mistake.

At nine o'clock, the engineer changes the address and simultaneously reduces its TTL from one hour to sixty seconds.

They expect the entire internet to begin using the new address within one minute.

But consider the resolver that cached the old answer at 8:59.

Its existing cached data came with a one-hour lifetime. Changing the authoritative TTL afterward does not retroactively rewrite that cached copy.

The resolver may continue using the old answer for almost another hour.

The correct strategy is to lower the TTL sufficiently **before** the planned migration.

If the old TTL is one hour, you might lower it to sixty seconds more than an hour before changing the address, allowing previously cached longer-lived answers to expire.

After that preparation period, compliant resolvers obtaining the record should receive the shorter TTL.

When the actual cutover happens, cached old answers should ordinarily expire much sooner.

Even then, avoid treating the TTL as a perfect worldwide deadline. Resolver implementations, client caches, connection reuse, provider configuration, and operational anomalies can complicate the transition.

The practical migration plan should tolerate overlap.

## 6.3 A safer migration sequence

Suppose our company needs a low-risk DNS migration.

First, prepare and test the new environment independently. Confirm that the application works with the intended hostname, not merely when contacted through an IP address.

Next, reduce the relevant TTL sufficiently in advance and allow previously cached records to age out.

Then change the DNS records and monitor responses from authoritative and recursive resolvers. Verify the actual application behavior from multiple networks.

Most importantly, keep the old infrastructure able to serve valid requests during the transition. Do not immediately destroy a working destination merely because the DNS dashboard displays a new one.

Finally, retire the old environment only after observing that traffic has drained and the remaining risks are acceptable.

This is a blue-green deployment principle expressed through network naming.

The old and new systems may need to coexist, particularly when they cannot be switched atomically.

### A subtle but important architectural lesson

DNS is often the wrong tool for decisions requiring immediate, per-request control.

Suppose you need to redirect five percent of requests to a new service version, monitor errors, and roll back within seconds.

A load balancer, reverse proxy, service mesh, or application-level routing system may be more appropriate than changing DNS records.

DNS-based traffic steering can be useful, but caching makes it a relatively coarse control mechanism.

Choose the control mechanism according to the required speed and granularity of the decision.

---

# 7. DNS Can Cache Failure, Too

So far, we've investigated caching successful answers. But what happens when the requested name does not exist?

Imagine that your team is preparing a new service at `api-v2.stays.example.com`.

A developer tries to access it before the DNS record has been created.

The resolver asks the appropriate authoritative server and receives an answer indicating that the requested DNS name does not exist.

This response is commonly called **NXDOMAIN**.

The developer creates the missing DNS record one minute later, but their next attempt still fails.

What's going on?

The previous negative response may have been cached.

DNS supports **negative caching**, which prevents resolvers from repeatedly asking authoritative servers about names that are known not to exist.

Without negative caching, a typo in a frequently requested hostname could generate a continual stream of identical failed lookups.

The downside is that an accidentally queried nonexistent name can remain unavailable to some clients for a period after its record is created.

The duration of ordinary NXDOMAIN or NODATA negative caching is governed by information associated with the zone's SOA record, together with resolver behavior and applicable limits.

## 7.1 Three failures that are not the same

Engineers should distinguish several DNS outcomes.

**NXDOMAIN** means the queried DNS name does not exist.

**NODATA** means the requested record type has no answer at an existing name, typically represented by a successful DNS response code with an empty answer for that type.

For example, a hostname might have an AAAA record but no A record. Asking for its A record is not necessarily the same as asking for a nonexistent hostname.

**SERVFAIL** indicates that the DNS server could not successfully process or complete the query. Causes may include failures contacting other nameservers, misconfiguration, or DNSSEC validation problems.

A timeout is different again: the client did not receive a usable DNS response within the expected time.

These distinctions matter because their remedies are different.

Creating an A record is not the appropriate response to every SERVFAIL. Restarting an application won't repair a DNSSEC validation failure. Flushing a local cache may not fix an error returned by an authoritative server.

And a completely correct authoritative answer doesn't immediately erase negative responses already retained by caching resolvers.

The recurring principle is simple:

**A failed lookup has a mechanism and a location, just like any other distributed-system failure.**

---

# 8. DNS as a Traffic-Steering System

We have concentrated on correctness, but DNS also plays a major role in performance and geographical distribution.

Consider a company serving customers from Europe, Asia, and North America.

Sending every customer to one physical server in Frankfurt would create unnecessary latency for many users. Instead, the company may use DNS responses to advertise different regional or CDN endpoints.

How might this work?

A DNS provider can consider information about where a query appears to originate. Often, the visible source is a recursive resolver rather than the actual end user.

Some DNS ecosystems support EDNS Client Subnet, which can provide partial client-network information to help select geographically appropriate responses, subject to resolver and provider behavior.

This is why geographical DNS steering is imperfect.

Two people in the same city might use different recursive resolvers and receive different answers. A user employing a remote DNS resolver might receive an endpoint chosen using incomplete location information.

The application then connects to the selected IP address through the ordinary networking system.

### Anycast complicates the picture

Another technique frequently used by DNS providers and CDNs is **anycast**.

With anycast, multiple geographically distributed network locations advertise reachability for the same IP address. Internet routing determines which location receives a particular flow.

That means two users can connect to the same IP address while reaching different physical facilities.

Notice the distinction.

DNS-based steering may give different addresses to different users.

Anycast can route users toward different facilities even when they use the same destination address.

These techniques can be combined, and CDNs frequently have additional internal routing mechanisms behind their public endpoints.

An IP address in a DNS response is therefore not a reliable diagram of the physical architecture.

### One more complication: IPv4 and IPv6

A hostname may advertise both IPv4 and IPv6 addresses.

Modern clients can use connection-selection strategies, including forms of the Happy Eyeballs approach, to avoid unnecessarily delaying connectivity when one address family works better than another.

This creates an interesting diagnostic possibility.

A service may have perfectly functional IPv4 connectivity but broken IPv6 connectivity. Some clients might successfully reach it through IPv4 while others experience delays or failures associated with IPv6 attempts.

The DNS records might all be syntactically correct. The underlying network paths might not be.

We will explore addressing and routing in much greater depth in CS230-L05.

For now, remember that **DNS supplies possible destinations; network routing determines how packets actually travel to them**.

---

# 9. DNS Security: Three Different Problems, Three Different Defenses

It is tempting to imagine that using HTTPS makes DNS security irrelevant.

After all, if the application communicates securely with the website, does it matter how the browser found the website's IP address?

It matters, but we need to distinguish three different security properties.

## 9.1 Protecting the integrity of DNS information

Traditional DNS does not inherently provide cryptographic proof that every answer has originated from the appropriate zone authority.

An attacker capable of interfering with DNS resolution may attempt to supply fraudulent information, redirecting clients toward infrastructure they control.

**DNSSEC**, or DNS Security Extensions, introduces cryptographic signatures and chains of trust that allow validating resolvers to authenticate appropriate DNS data.

A validating resolver can detect certain forms of tampering with signed DNS information.

But DNSSEC does not encrypt ordinary DNS queries. It also does not guarantee that the published address points to a healthy application or that an administrator entered the intended configuration.

It authenticates DNS information under its trust model; it does not audit the business correctness of that information.

## 9.2 Protecting DNS queries in transit

Traditional DNS queries and responses have often traveled without transport encryption.

Protocols such as **DNS over HTTPS**, or DoH, and **DNS over TLS**, or DoT, can protect communication between a DNS client and its chosen resolver.

That makes passive observation or modification of that particular communication path more difficult.

But encrypted DNS doesn't magically make the resolver trustworthy. The selected resolver still processes the queries and may observe the names being requested.

Nor does DoH automatically encrypt every subsequent exchange between recursive and authoritative nameservers.

It protects a particular communication relationship, not the entire internet's naming system.

## 9.3 Authenticating the application endpoint

Now consider HTTPS itself.

Suppose an attacker persuades a client to connect to a malicious IP address when requesting `api.stays.example.com`.

If the attacker cannot present a certificate and complete the TLS handshake in a manner valid for the requested hostname under the client's trust policy, the HTTPS connection should fail authentication.

This is a separate defense from DNSSEC or encrypted DNS.

TLS authentication is tied to the intended service identity, not simply to whichever IP address DNS happened to return.

That's also why manually directing a hostname to a different IP address does not automatically defeat HTTPS identity verification.

We now have three distinct ideas:

DNSSEC authenticates DNS information when properly validated.

Encrypted DNS protects communication with the chosen resolver.

TLS authenticates and protects communication with the intended application endpoint.

They solve related but different problems. Confusing them is how otherwise intelligent teams end up making rather unfortunate security assumptions.

---

# 10. How to Investigate a DNS Incident Without Guessing

Let's return to our troubled hotel-booking platform.

At nine fifteen, users are still reaching the old infrastructure, but the authoritative DNS dashboard displays the new address.

What should an engineer investigate?

A poor approach is to randomly flush caches, restart servers, and hope for improvement.

A stronger approach is to identify the observations that distinguish competing explanations.

We can organize the investigation around four questions.

## 10.1 Which resolution path is the client actually using?

First, determine how the affected application obtains DNS information.

Does it use the operating system resolver? A browser-managed DNS-over-HTTPS configuration? A VPN-provided resolver? An internal company DNS service?

Could a hosts-file entry override the public domain?

And is a new lookup even taking place?

An application may already have an open connection to the old endpoint. Connection reuse can preserve that relationship without requiring fresh DNS resolution for every request.

If a browser continues reaching an old IP address, that observation alone does not prove its current DNS lookup is returning the old address.

## 10.2 What does the configured resolver believe?

Next, inspect the response from the resolver actually used by the affected client, where it can be identified.

Look at the returned address records, aliases, status codes, and remaining TTL values.

Then compare that information with another resolver.

If one resolver returns the old address and another returns the new one, caching or resolution-path differences become plausible explanations.

But do not jump straight to blaming the first resolver. It may still possess an unexpired cached answer published by your own infrastructure.

## 10.3 What are the authoritative servers publishing?

Now identify the nameservers authoritative for the relevant zone and query them directly.

If the authoritative servers disagree, the problem may lie in the DNS provider's configuration, synchronization, or delegation arrangement.

If the authoritative servers agree on the new value, but a recursive resolver returns an old value with a decreasing TTL, ordinary caching becomes a likely explanation.

A tool such as `dig +trace` can help investigate delegation and iterative resolution. However, it does not reproduce every cache, resolver policy, browser setting, or local override used by an actual affected application.

Tools answer specific questions. They do not automatically reproduce the entire system.

## 10.4 What happens when the client connects?

Finally, separate name resolution from network connectivity and application behavior.

Suppose DNS returns the intended IP address, yet HTTPS fails.

The problem might involve a firewall, a routing issue, an unreachable listening port, a TLS certificate problem, a virtual-host configuration, or the application itself.

One particularly useful diagnostic technique is to connect to a chosen IP address while preserving the original HTTPS hostname for the request and certificate validation.

Curl supports this through its `--resolve` option.

This allows you to ask a powerful question:

"If I bypass ordinary DNS address selection and contact this particular destination, does the intended HTTPS service work?"

If the new endpoint works when its address is explicitly selected, but the ordinary request continues reaching the old endpoint, DNS or connection selection deserves further investigation.

If both fail in the same way, your evidence points elsewhere.

Good network debugging is an exercise in separating layers until the location of failure becomes unambiguous.

---

# 11. Completing the Production Incident

We can now reconstruct the migration failure.

At eight fifty-nine, a recursive resolver serving some customers cached the old API address with a one-hour TTL.

At nine, the company changed the authoritative address record.

Other resolvers, which did not retain a valid cached copy, quickly obtained the new address.

At nine five, the infrastructure team shut down the old API environment.

This was the critical mistake.

The company had changed its authoritative naming information but had not accounted for the lifetime of information already distributed through recursive resolvers and client caches.

As a result, customers whose resolution paths still selected the old endpoint began experiencing failures.

The reason the incident appeared geographically inconsistent was not that a magical wave of new DNS information was slowly moving across Europe.

Different resolvers and clients had different cached states and network configurations.

The engineers compared the affected resolver responses against the authoritative answers. They confirmed that some resolvers retained the old address with decreasing TTLs.

Restoring the old environment temporarily reduced the failures. The team kept both environments operational, monitored traffic against the old endpoints, and retired them only after the migration had safely settled.

The postmortem contained several actionable findings.

The team had not reduced the TTL sufficiently in advance. Its migration checklist did not require overlap between old and new environments. Its monitoring focused on application health rather than the endpoints real clients were still using.

Most importantly, the team had mistaken a configuration change for a globally completed transition.

That mistake is not unique to DNS.

It resembles deploying a new database schema before every service understands it, changing an API contract while old clients remain active, or removing a message consumer before the queue is drained.

Distributed systems rarely change state everywhere at exactly the same moment.

**The safe architecture tolerates multiple generations of state during transitions.**

---

# 12. The Oral Examination

We now have enough knowledge to examine DNS like an engineer rather than merely recognize its terminology.

Before reading the solutions, try answering these questions out loud. Imagine that a senior engineer is interviewing you and will challenge any hand-waving.

### Challenge 1 — Explain DNS resolution

A user types `https://api.example.com` into their browser. Explain the major DNS resolution steps and distinguish the roles of the stub resolver, recursive resolver, and authoritative server.

Do not assume every request reaches the root nameservers.

### Challenge 2 — The five-minute migration

A DNS record previously had a TTL of one hour. At noon, your team changes the IP address and lowers its TTL to thirty seconds.

At twelve fifteen, some customers are still connecting to the old IP address.

Is this necessarily evidence of a malfunction? Explain the timeline and the correct preventative strategy.

### Challenge 3 — The nonexistent hostname

A developer attempts to access a new subdomain before its DNS record is created and receives NXDOMAIN.

The record is created shortly afterward, but the developer continues receiving NXDOMAIN for several minutes.

What mechanism might explain the problem, and how would you investigate it?

### Challenge 4 — The certificate mismatch

A browser resolves the intended hostname and establishes a TCP connection to the returned IP address.

The HTTPS handshake fails with a certificate-name mismatch.

What has succeeded, what has failed, and why won't changing the DNS TTL necessarily help?

### Challenge 5 — The mysterious IPv6 incident

Users on certain networks experience slow or unsuccessful connections to a website. IPv4-only tests succeed, but clients that attempt IPv6 encounter problems.

How could the DNS records and network paths contribute? What would you test before modifying the application?

### Challenge 6 — The dangerous DNS load balancer

A colleague proposes publishing three A records for three application servers and argues that DNS will automatically distribute users evenly and stop directing them to a failed server.

What assumptions are hidden in that proposal?

---

# 13. Solutions and Discussion

### Solution 1 — Resolution

First, determine whether a lookup is needed at all. The application may reuse an existing connection or obtain suitable information from a local cache or override.

Otherwise, a stub resolver or browser-specific resolution mechanism typically requests information from a recursive resolver.

If the recursive resolver cannot answer from its cache, it follows referrals through the DNS hierarchy, potentially contacting root, top-level-domain, and authoritative nameservers.

The authoritative server provides the appropriate DNS data for its zone. The recursive resolver can cache usable information and return the result to the client.

Address resolution is separate from establishing a network connection. The client must still reach the destination through the network and satisfy the relevant transport and security requirements.

### Solution 2 — Migration

No malfunction is required.

A resolver that cached the old record just before noon may retain it for close to another hour under its original TTL.

Lowering the authoritative TTL at noon does not modify copies already cached elsewhere.

The safer process is to reduce TTL sufficiently in advance, wait for older cached information to expire, perform the cutover, and maintain the old destination during the transition.

Even after DNS caches expire, existing application connections and other resolution paths may require attention.

### Solution 3 — Negative caching

The initial NXDOMAIN response may have been retained by a caching resolver.

The lifetime of the negative response is governed by relevant SOA-based negative-caching information and resolver behavior, not simply by the TTL of an A record created afterward.

Compare the authoritative response against the configured recursive resolver's response. Inspect response codes, authority information, and remaining TTL where available.

Also verify that the intended record was created in the correct authoritative zone.

### Solution 4 — Certificate mismatch

DNS resolution returned address information, and TCP connectivity succeeded.

The failure occurred during TLS identity verification.

Possible causes include reaching the wrong endpoint, missing or incorrect certificate configuration, or a server presenting a certificate for another hostname.

The appropriate investigation examines the certificate, requested hostname, SNI behavior, and destination configuration. DNS might have selected the wrong endpoint, but a TTL change does not repair TLS certificate configuration by itself.

### Solution 5 — IPv6

The hostname may advertise AAAA records that lead to an IPv6 destination with broken routing, filtering, or service configuration.

Test A and AAAA responses independently. Examine connection behavior over IPv4 and IPv6, not just the apparent correctness of the DNS records.

Check whether the relevant address family can reach the intended service port and complete TLS and HTTP exchanges.

Client connection-selection behavior can affect the severity of the issue, so results may vary by operating system, browser, and network.

### Solution 6 — Multiple A records

Returning several addresses is not equivalent to operating a fully managed load balancer.

Clients and resolvers may select or reorder addresses differently, cache results, or continue using existing connections.

DNS does not inherently perform continuous application health checks or guarantee equal distribution of connections and requests.

A robust design needs to consider health detection, endpoint withdrawal, caching delays, session behavior, and recovery mechanisms.

Depending on the requirements, a dedicated load balancer or another traffic-management system may be more appropriate.

---

# 14. The Mental Model Worth Keeping

DNS is a **distributed, hierarchical database of typed naming information**.

Its major responsibilities can be remembered through five questions:

- **Who knows?** Authoritative DNS servers publish information for their zones.
- **Who finds out?** Recursive resolvers follow delegations and retrieve answers.
- **Who remembers?** Recursive resolvers, applications, and local systems may cache information.
- **Who decides when information expires?** TTL values and applicable caching policies govern reuse.
- **Who actually connects?** The application and networking stack use the information to establish communication.

The mistake to avoid is treating DNS as a live global registry that instantly informs every client of a configuration change.

It is closer to a system of delegated authorities and independently maintained caches.

Once you understand that architecture, DNS migrations, inconsistent client behavior, geographical differences, and seemingly mysterious resolution failures become problems you can reason about rather than rituals you can only hope will work.

---

# 15. Next Lecture — IP Addressing, Subnets, Routing, and NAT

We've discovered how a hostname can lead a client toward an IP address.

But how does the client actually reach that address?

Why can your laptop communicate with a public server even though its own address might be something like `192.168.1.42`? What does a subnet mask actually mean? How do routers determine the next hop, and why can a firewall allow one connection while rejecting another?

In **CS230-L05**, we'll follow packets through local networks, routers, NAT devices, and the wider internet.

This time, the challenge won't be discovering the destination.

It will be getting there.

---

## Optional Practical Lab — Investigating DNS From the Terminal

*The spoken lecture ends here. The remaining material is a screen-first investigation worksheet and technical references.*

### Lab A — Inspect address records

On Linux or macOS, use `dig` to ask for A and AAAA records for `example.com`:

```bash
dig example.com A
dig example.com AAAA
```

On Windows PowerShell, the same idea with `Resolve-DnsName` and `-Type A` / `-Type AAAA`:

```powershell
Resolve-DnsName example.com -Type A
Resolve-DnsName example.com -Type AAAA
```

Examine the response type, returned addresses, TTL values, and DNS response status. Does the domain support both address families?

### Lab B — Explore delegation

Query NS and SOA records, then run `dig +trace` to walk delegation toward the name.

```bash
dig example.com NS
dig example.com SOA
dig +trace example.com
```

Identify the authoritative nameservers and trace how DNS delegation can lead toward the requested domain.

Remember that `dig +trace` performs its own resolution investigation. It does not reproduce all the caches or policies of your browser's configured resolver, and some networks may restrict the direct DNS traffic it uses.

### Lab C — Compare recursive resolvers

Ask the same A question of two public resolvers — for example `1.1.1.1` and `8.8.8.8` — and compare answers and remaining TTLs.

```bash
dig @1.1.1.1 example.com A
dig @8.8.8.8 example.com A
```

Compare the answers and remaining TTLs. Different results do not automatically indicate an error, particularly for geographically distributed services.

### Lab D — Separate DNS from HTTPS connectivity

Curl's `--resolve` option lets you supply a particular address for a hostname and port while retaining the requested hostname for HTTPS processing.

Example syntax: `curl -v --resolve example.com:443:YOUR_IP_ADDRESS https://example.com/`

Replace `YOUR_IP_ADDRESS` with an appropriate address obtained from your investigation. Test only an endpoint you are authorized to access.

This technique is particularly useful during a migration when you need to verify a new destination before changing public DNS.

### Lab E — Explain your observations

Write or speak a short diagnosis covering:

1. Which DNS answers were obtained.
2. Which resolver supplied each answer.
3. Whether the authoritative information agreed.
4. Whether the selected destination was reachable.
5. Whether HTTPS succeeded after the connection was established.

The objective is to practice separating DNS resolution from the behavior of the network and application.

---

## Further Reading — Optional Technical References

1. [RFC 1034 — Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034.html) — DNS architecture, delegation, authoritative servers, resolvers, and caching.
2. [RFC 1035 — Domain Names: Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035.html) — DNS record formats, messages, and protocol fundamentals.
3. [RFC 2308 — Negative Caching of DNS Queries](https://www.rfc-editor.org/rfc/rfc2308.html) — NXDOMAIN, NODATA, and SOA-based negative caching.
4. [RFC 9520 — Negative Caching of DNS Resolution Failures](https://www.rfc-editor.org/rfc/rfc9520.html) — Updated requirements for caching resolution failures.
5. [RFC 4033 — DNS Security Introduction and Requirements](https://www.rfc-editor.org/rfc/rfc4033.html) — DNSSEC architecture and security goals.
6. [RFC 8484 — DNS Queries over HTTPS](https://www.rfc-editor.org/rfc/rfc8484.html) — Encrypted DNS transport over HTTPS.
7. [RFC 9460 — Service Binding and HTTPS Records](https://www.rfc-editor.org/rfc/rfc9460.html) — Modern DNS service binding and HTTPS connection information.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS230-L04  DNS — INTERVIEW GLANCE CARD

CORE MODEL
  Hostname = stable identity in a global namespace — not "a machine"
  Indirection: name stays; infrastructure (IP, LB, CDN, regions) changes
  Many names → one IP; one name → many IPs / families / geo answers
  DNS resolution ≠ TCP connect ≠ TLS auth ≠ app health ≠ reachability

WHO ANSWERS?
  Stub resolver     app/OS client; usually delegates hard work
  Recursive resolver  "get me an answer" — may use ITERATIVE queries
  Authoritative     publishes zone data; authority ≠ proof of healthy app
  Also: browser DoH/cache, hosts file, VPN — dig ≠ always browser path
  Connection reuse can skip a new lookup entirely

HIERARCHY (COLD LOOKUP)
  Recursive → Root (referral) → TLD (referral) → Authoritative (answer)
  Referral = next authority, not final A/AAAA
  Caching of answers AND delegations → most lookups aren't cold
  NS delegation + glue: avoid circular "NS name inside own zone" bootstrap
  Tree of delegated authority — not one global catalogue

RECORD TYPES (TYPED QUESTIONS)
  A / AAAA   IPv4 / IPv6 addresses (multi OK; ≠ managed LB + health)
  CNAME      alias to another NAME — not an HTTP redirect; apex conflict
             (SOA/NS); ALIAS/ANAME/flattening = provider mechanisms
  NS / SOA   nameservers; zone admin + negative-caching role
  MX / TXT   mail; verification / email auth text
  CAA        authorized CAs for issuance (policy-dependent)
  SRV        service endpoints (+ ports) when apps use them
  No A ≠ nonexistent name — other types or deliberate no IPv4

CACHING & MIGRATION ("PROPAGATION")
  TTL = how long a caching resolver may reuse the answer
  Lower TTL AT cutover does NOT rewrite already-cached copies
  Prep: lower TTL early → wait for old caches to expire → cut over
  Keep old destination up during overlap (blue-green via naming)
  No single global DNS cache; independent expiries explain geo disagreement
  DNS is coarse for instant % canary / second-scale rollback → use LB/proxy

NEGATIVE CACHING
  NXDOMAIN   name does not exist
  NODATA     name exists; requested TYPE empty (e.g. AAAA yes, A no)
  SERVFAIL   resolver/server couldn't complete (misc./DNSSEC/…)
  Timeout    no usable response in time
  Negative TTL from SOA-related rules + resolver policy — creating A later
  doesn't erase already-cached NXDOMAIN

TRAFFIC STEERING
  Geo DNS may key off recursive (or ECS) — imperfect user location
  Anycast: same IP → different facilities via routing
  Happy Eyeballs–style dual-stack selection; broken AAAA path ≠ bad A records
  DNS supplies candidates; routing decides the actual path

SECURITY — THREE DIFFERENT DEFENSES
  DNSSEC   authenticate DNS data (signatures/trust) — not encrypt queries;
           not "admin entered right IP"
  DoH/DoT  encrypt client↔chosen resolver — resolver still sees names;
           not whole recursive↔authoritative path
  TLS      authenticate intended hostname at endpoint — bad IP still fails
           without valid cert for that name

INCIDENT QUESTIONS
  1. Which resolution path? (OS / DoH / VPN / hosts / reuse?)
  2. What does THAT recursive return? (addrs, CNAME, RCODE, remaining TTL)
  3. What do authoritatives publish? (dig +trace ≠ full client reproduction)
  4. Connect separately: curl --resolve host:443:IP → isolate DNS vs HTTPS

MULTI-A "LOAD BALANCER" MYTH
  Multiple A ≠ health checks, even distribution, or instant withdrawal
  Clients/resolvers cache, reorder, reuse connections

FIVE QUESTIONS THAT RECOVER THE LECTURE
  Who knows?     authoritative
  Who finds out? recursive (iterative walk)
  Who remembers? caches (resolver / OS / app)
  Who expires?   TTL + policy
  Who connects?  transport + TLS + app after the answer

SENIOR LINE: DNS is delegated authorities + independent caches — tolerate
             multiple generations of naming state during transitions.
```
