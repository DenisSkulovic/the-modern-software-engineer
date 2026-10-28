---
id: CS230-L09
course: CS230
title: "Proxies, Load Balancers, and CDNs"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS230-L08
next: CS230-L10
---



# CS230 — Computer Networks and Web Protocols

## Lecture 09: Proxies, Load Balancers, and CDNs

*Your backend is healthy. Its authorization logic is correct. Its logs show nothing suspicious. Yet a customer has just received another customer's private reservation details. The culprit is a server that your application never directly called.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a hotel-booking platform serving customers throughout Europe.

The application has several Node.js backend instances. They communicate with PostgreSQL, handle customer reservations, and expose HTTP APIs.

A customer in Paris opens the website and requests their reservations.

You might imagine a simple conversation: the browser contacts the Node.js server, the server retrieves the reservations, and the browser displays them.

But modern production systems rarely work that way.

The browser may first contact a geographically nearby CDN server. That server may inspect the HTTP request, apply security rules, terminate TLS, and decide whether it already has a cached response.

If the request needs to reach the application, the CDN forwards it toward an origin infrastructure containing a load balancer.

The load balancer chooses one of several available Node.js instances.

That instance finally processes the request.

The customer sees one website, but the request may involve several separate network connections and several independent decisions.

### The architecture

```text
                  Customer's browser
                          |
                          v
                    CDN / Edge
                 Cache, TLS, rules
                          |
                          v
                   Load balancer
                  Backend selection
                          |
                  +-------+-------+
                  |               |
                  v               v
               Node A          Node B
                  |               |
                  +-------+-------+
                          |
                          v
                       Database
```

The important part isn't the number of servers.

It's that each intermediary has its own responsibilities and may change how the request is handled.

And one of those intermediaries may answer the request without consulting your application at all.

## 1. The server that answered without asking

Suppose the browser requests a public hotel image.

The first customer causes the CDN to retrieve the image from the origin server. The CDN stores a copy.

The second customer requests the same image.

The CDN recognizes that it already has an acceptable response and returns it immediately.

The Node.js application may never see that second request.

That's excellent.

The customer receives the image faster, and your infrastructure performs less work.

Now imagine the same behavior applied to:

`GET /api/me/reservations`

Customer Alice requests her reservations. The origin authenticates Alice correctly and returns her data.

The CDN stores the response under a cache key that identifies only the URL.

Bob then requests the same URL.

If the CDN incorrectly considers Bob's request equivalent to Alice's, it may return Alice's cached response.

The backend never receives Bob's request. Its authorization logic has no opportunity to reject anything.

The backend is correct.

The CDN configuration is wrong.

And the system has leaked private data.

**An intermediary that can answer requests is part of the application's correctness and security model.**

## 2. Forward and reverse proxies

A proxy is an intermediary that communicates with another endpoint on behalf of a client or server.

A **forward proxy** primarily represents the client side.

For example, a company may route employee internet traffic through a corporate proxy to apply access policies or logging.

A **reverse proxy** primarily represents the server side.

Clients contact the reverse proxy, which forwards requests to backend applications.

A CDN commonly acts as a geographically distributed reverse proxy.

A load balancer may also function as a reverse proxy when it terminates connections and forwards application traffic.

The distinction is about the role an intermediary plays, not about a completely different kind of computer.

## 3. Load balancing isn't the same as making work disappear

Imagine four Node.js instances.

A load balancer distributes new connections or requests among them according to its implementation.

This can improve availability and processing capacity.

But suppose every HTTP request performs the same expensive PostgreSQL query.

Adding four Node.js instances doesn't make that query cheaper.

The database may simply receive more simultaneous expensive requests.

The load balancer can distribute incoming work.

It cannot guarantee that the downstream systems can handle the resulting demand.

This is why horizontal scaling works only when the workload and dependencies support it.

## 4. One request, several security boundaries

Suppose the browser connects to the CDN using HTTPS.

The CDN terminates that TLS connection so it can inspect the HTTP request.

It then establishes another connection toward the origin infrastructure.

That connection may also use TLS, but it is a separate TLS session.

The encryption protecting the browser-to-CDN hop does not automatically protect every subsequent hop.

Meanwhile, the backend may see the load balancer's IP address instead of the customer's.

The customer's original address may be conveyed through an HTTP forwarding header.

But an HTTP header is data supplied by a participant in the request chain.

A malicious client can also send headers.

The backend must know which proxies are trusted before interpreting forwarding metadata as security-relevant information.

**Every time an intermediary terminates a connection, it becomes responsible for preserving or reconstructing some properties of the original request.**

## 5. The cache doesn't know what a customer is

A CDN is very good at comparing request characteristics.

It can recognize URLs, query parameters, selected headers, and other configured attributes.

But it doesn't automatically understand your application's business authorization rules.

Two requests to `/api/me/reservations` have the same path.

They don't necessarily have permission to receive the same response.

Two requests for hotel prices may differ by currency, language, dates, customer eligibility, or other dimensions.

A safe cache design must distinguish which responses are equivalent for reuse.

If it cannot confidently establish equivalence, it should not reuse sensitive content.

## The minute-long replay

A browser contacts the CDN.

The CDN may return a cached response or contact the origin.

The origin load balancer chooses a backend destination.

Each connection has its own protocol, TLS boundary, timeout behavior, and observability.

The backend may see forwarded metadata rather than the original network peer.

The CDN can improve latency and availability, but incorrect caching or trust configuration can introduce failures that the backend code never sees.

### Three questions before the Deep Dive

1. Why can a backend with correct authorization still participate in a customer-data leak?
2. What is the difference between distributing requests and increasing useful system throughput?
3. Why shouldn't an application blindly trust the `X-Forwarded-For` header?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Reservation That Belonged to Someone Else

It's Monday morning at a hotel-booking company.

The infrastructure team has recently introduced a CDN in front of the application.

Static resources load faster. Origin traffic has fallen. Several pages are noticeably more responsive.

The engineering team is pleased.

Then customer support receives an alarming report.

A customer has opened their reservations page and seen another person's hotel booking.

The screenshot contains the other customer's name, travel dates, and reservation details.

An engineer immediately searches the backend logs.

There's nothing obviously suspicious.

The database query is correctly scoped to the authenticated user.

The authorization middleware works.

The customer-specific endpoint has thorough automated tests.

Yet the exposure happened.

The team starts by asking the wrong question:

"How did Bob's request pass Alice's authorization checks?"

Eventually, someone asks a better one:

"Did Bob's request ever reach the backend?"

That question changes the investigation.

The CDN reports that Bob's request was answered from its cache.

Alice's earlier response had been stored under a cache key that did not distinguish the two authenticated sessions.

Bob received a response that was originally generated for Alice.

The application wasn't bypassed through a sophisticated SQL injection or a broken JWT.

It was bypassed because the intermediary reused data under an invalid assumption of equivalence.

Our mission is to understand how a system acquires that kind of power—and how to use it safely.

## 2. An HTTP Request May Cross Several Independent Connections

A browser can communicate with a CDN over one TLS-protected connection.

The CDN can communicate with an application load balancer over another.

The load balancer can communicate with a Node.js instance over a third.

Those connections aren't necessarily using the same HTTP version or transport.

The CDN may speak HTTP/3 to the browser and HTTP/2 or HTTP/1.1 toward the origin.

The load balancer may maintain a pool of persistent connections to backend instances.

A single browser request therefore doesn't necessarily correspond to one continuous end-to-end network connection.

The intermediary receives a request, interprets its protocol-level meaning, and constructs or forwards an appropriate request toward the next participant.

Some intermediaries operate at lower network layers and don't inspect HTTP at all.

Others understand HTTP methods, headers, paths, cookies, and responses.

That distinction determines what they can do.

### A hop isn't always transparent

An intermediary may modify headers, normalize URLs, compress responses, enforce size limits, reject requests, or apply timeouts.

It may retry an upstream request.

It may terminate TLS and establish a new protected connection.

It may return a cached result.

It may even generate an error response without contacting the intended backend.

The user experiences one request, but the infrastructure contains multiple independently operating participants.

That's why debugging modern web infrastructure requires understanding the actual request path rather than assuming the application server handles everything.

## 3. Layer Four and Layer Seven Load Balancers

Load balancers can operate using different layers of protocol information.

A **Layer Four load balancer** makes forwarding decisions primarily from transport-level information such as IP addresses, ports, and connection characteristics.

It can distribute TCP connections without necessarily understanding the HTTP requests carried inside them.

This is useful when the application protocol should remain opaque to the load balancer or when relatively simple connection forwarding is sufficient.

A **Layer Seven load balancer** understands an application protocol such as HTTP.

It can make decisions using hostnames, paths, request methods, headers, or other HTTP properties available to it.

For example, one application load balancer might route:

`/api/` toward the backend API,

`/images/` toward an image-processing service,

and `/admin/` toward an administration application.

But an HTTPS-aware Layer Seven intermediary generally needs to terminate TLS to inspect encrypted HTTP contents.

By contrast, an intermediary forwarding encrypted TCP traffic without terminating TLS cannot simply inspect arbitrary HTTP paths.

The distinction is about what information the intermediary can observe and act upon.

### Connection distribution versus request distribution

Suppose our application uses HTTP/2 over a long-lived connection.

A Layer Four balancer may choose one backend for that connection.

Hundreds of individual HTTP requests can then travel over the same selected connection.

Adding another backend instance doesn't necessarily redistribute those existing requests.

An HTTP-aware proxy can potentially make routing decisions per request, subject to its own connection-management behavior.

This matters when interpreting load-balancer statistics.

Four healthy servers do not guarantee that each handles exactly one-quarter of the traffic.

The actual distribution depends on connection lifetimes, routing strategy, traffic characteristics, and implementation.

## 4. How a Load Balancer Chooses a Backend

Let's say our booking API has four healthy instances.

The load balancer needs a selection policy.

### Round robin

A simple strategy distributes successive eligible connections or requests among backend instances in sequence.

It's easy to understand and can work well for roughly similar workloads.

But one request might take five milliseconds while another performs an expensive operation for several seconds.

Equal request counts aren't necessarily equal amounts of work.

### Least connections or least outstanding requests

Another strategy prefers instances with fewer active connections or requests.

This may respond better to uneven work, but connection count isn't a universal measure of CPU load.

An idle WebSocket connection can remain open for hours.

One CPU-intensive request may consume substantial capacity.

So the selection metric needs to match the actual workload.

### Weighted balancing

Backends may have different capacities.

A larger instance might receive a higher share of traffic.

Weights are also useful during migrations or controlled traffic shifts.

But weights don't replace application-level measurements.

A server with twice the CPU doesn't necessarily have twice the throughput if the bottleneck lies elsewhere.

### Consistent hashing and affinity

Some systems try to route related traffic to the same backend, using a stable key.

This can improve cache locality or support specialized stateful routing.

But the chosen key, backend changes, and failure behavior all matter.

Hashing isn't a promise that the selected backend will remain alive forever.

### Sticky sessions

Imagine customer sessions are stored only in the memory of Node.js instance A.

The first request reaches A and succeeds.

The next reaches B.

B doesn't recognize the session.

Sticky routing can make repeated requests more likely to return to A.

But what if A crashes?

The session state is still gone.

Sticky sessions can be useful, but they are a routing strategy, not a durable session-storage strategy.

For ordinary horizontally scaled applications, shared or externally persisted session state is often more robust.

## 5. Health Checks: A Server Can Be Alive but Useless

Suppose the load balancer has four backend targets.

Three are healthy.

The fourth has lost its ability to serve reservations because of an internal application problem.

Its operating-system process remains alive. Its HTTP server still responds to simple requests.

If the health check merely asks whether the process accepts connections, the backend may continue receiving traffic.

Now the load balancer distributes customers toward an application instance that cannot fulfill the service.

A more meaningful readiness check can improve the decision.

But making health checks increasingly comprehensive introduces a different danger.

### The shared-dependency trap

Imagine the database becomes unavailable for twenty seconds.

Every API instance depends on that database.

If each backend's health check treats any brief database failure as proof that the entire process must be removed from service, the load balancer may conclude that all backends are unhealthy.

Different load balancers react differently when every target fails health checks. Some return errors; some may fail open under particular configurations.

Either outcome requires deliberate design.

The correct check depends on what the service must guarantee.

An API that cannot perform its essential operation may need to report unready.

But restarting or withdrawing every backend during a recoverable dependency interruption can amplify the outage.

Health checks should represent useful serving capability without creating unnecessary cascading failures.

### Connection draining

Now suppose a backend is being replaced during a deployment.

The load balancer should stop choosing it for appropriate new traffic while allowing existing work to finish according to its drain settings and deadlines.

But stopping new routing doesn't make existing connections disappear instantaneously.

The backend process must cooperate with graceful shutdown.

This is why deployment safety involves both intermediary behavior and application lifecycle.

A load balancer can decide where traffic goes.

It cannot guarantee that a backend finishes every in-flight business operation before the process disappears.

## 6. The Client IP Address That Wasn't the Client's

Our booking application's backend receives a request.

The network-level peer address belongs to the load balancer.

That's expected if the load balancer terminates the client-facing connection and establishes another connection toward the application.

But the backend may need information about the original client for logging, rate limiting, security analysis, or geographic decisions.

HTTP proxies often communicate this information using headers such as `X-Forwarded-For` or the standardized `Forwarded` header.

Additional forwarding headers may describe the original scheme or host.

These values are useful—but they require a trust model.

### The spoofing problem

A client may send its own `X-Forwarded-For` header.

If the backend accepts that value as authoritative without establishing which intermediaries are trusted, an attacker may manipulate the apparent client address.

That can undermine rate limits, access controls, security logs, or abuse investigations.

The correct approach is to define trusted proxy boundaries.

The edge proxy should handle untrusted forwarding input according to a deliberate policy.

The application should identify trusted intermediary addresses or use another well-defined trusted forwarding mechanism.

When interpreting a chain of forwarded addresses, it must account for which entries were added by trusted proxies rather than assuming the first reported address is always authentic.

The backend should also be protected against unauthorized direct access that bypasses the expected proxy chain.

### Original scheme and host

Suppose HTTPS terminates at the CDN.

The request from the CDN to the backend might use a different scheme.

If the application determines whether the original request was secure merely from its immediate connection, it may reach the wrong conclusion.

Trusted forwarding metadata can communicate the original request scheme.

But again, the application should not blindly trust arbitrary client-supplied claims.

Incorrect forwarding configuration can produce redirect loops, insecure URL generation, or incorrect cookie behavior.

The underlying principle is simple:

**Original-client information becomes asserted metadata when an intermediary terminates the connection. That metadata is trustworthy only within a correctly defined proxy boundary.**

## 7. TLS Termination Changes the Trust Boundary

In CS230-L08, we examined how TLS authenticates endpoints and protects communication.

Now apply that knowledge to our architecture.

The browser establishes a TLS connection with the CDN.

The CDN presents an appropriate certificate for the requested hostname.

The browser verifies the certificate and establishes an encrypted, authenticated connection to the CDN endpoint.

The CDN can now inspect the HTTP request because it terminates that TLS session.

It may then establish another TLS connection to the origin.

That's commonly called TLS re-encryption.

There are now two separate protected hops.

### Hop-by-hop encryption isn't one continuous tunnel

The first connection protects browser-to-CDN communication.

The second protects CDN-to-origin communication.

The CDN sits inside the trust boundary of both connections because it can access the HTTP content.

That may be entirely intentional.

A CDN needs to inspect requests to provide caching, HTTP routing, or application-layer security services.

But the architecture must recognize that the intermediary is trusted with the data.

### Origin authentication still matters

An origin connection using HTTPS isn't automatically secure merely because it is encrypted.

The connecting intermediary must validate the intended origin identity according to an appropriate trust policy.

If it accepts arbitrary certificates or disables verification, an attacker who can interfere with the origin connection may gain opportunities that proper authentication would have prevented.

The browser's successful TLS validation at the CDN does not prove that the CDN's origin connection was authenticated correctly.

### TLS passthrough

Some intermediaries forward encrypted traffic without terminating TLS.

That can preserve the endpoint's role in authenticating and decrypting the connection.

But it also limits the intermediary's ability to inspect HTTP content.

A system cannot simultaneously require complete HTTP inspection at an intermediary and keep that intermediary unable to decrypt the HTTP messages.

Architecture involves choosing where trust is placed.

## 8. The CDN: A Geographically Distributed Reverse Proxy

A CDN is often introduced as a way to serve static files close to users.

That's one of its most familiar purposes.

But modern CDNs can also terminate TLS, implement caching policies, enforce application-layer security rules, and route requests toward origin infrastructure.

Consider a browser in Stockholm accessing a booking application hosted in a European cloud region.

A nearby CDN point of presence can answer requests for already cached static assets without contacting the origin.

The browser experiences lower network latency and fewer origin round trips.

The origin serves fewer repeated requests.

This is especially effective for resources such as versioned JavaScript bundles, stylesheets, fonts, and public images.

But not every response should be cached.

### Static assets

Suppose a JavaScript file has a content-derived filename such as `app.a18f2c.js`.

When its contents change, the filename changes.

That makes long-lived caching attractive because the old URL continues to identify the old content.

A CDN can reuse the response without risking a mismatch between the same URL and newly modified bytes, assuming the deployment strategy preserves the relevant assets.

### Public search results

A hotel-search response may be cacheable for a limited period if the business allows temporary staleness.

But what defines the response?

Dates, destination, currency, language, filters, and possibly customer-specific eligibility may all change the result.

A safe cache design must consider these dimensions.

### Authenticated reservation data

A customer's private reservations belong to a different category.

They should not be reused across unrelated customers.

For sensitive personalized responses, a conservative policy is to prohibit storage in shared caches, often using `Cache-Control: private, no-store` or simply `no-store`, together with appropriate CDN bypass rules.

In standard HTTP semantics, `private` prevents shared-cache storage of an unqualified private response, while `no-store` instructs caches not to store the response.

The CDN's actual configuration must also be verified.

An explicit caching override can create behavior very different from the application's intended HTTP policy.

## 9. Cache Keys: The Most Dangerous Equality Test in the Architecture

A cache has to answer a deceptively difficult question:

"May I reuse this stored response for the current request?"

To do that, it calculates or selects a cache key.

The key may include the request method, target URI, and additional configured dimensions.

For example, a public search response might depend on:

- Destination.
- Travel dates.
- Currency.
- Language.
- Search filters.

If two requests differ in a dimension that changes the response, they may not be equivalent for caching.

Now return to our incident.

Alice requests:

`GET /api/me/reservations`

Her session cookie identifies her to the origin.

The origin correctly returns Alice's reservations.

A dangerous CDN configuration stores the response using a key based only on the URL.

Bob requests the same URL.

Bob's cookie identifies a different user, but the cache key fails to distinguish that identity.

The CDN considers the requests equivalent.

It returns Alice's response.

### Why the cookie doesn't automatically save us

It is unsafe to assume that the presence of a Cookie header makes an HTTP response uncacheable under every circumstance.

HTTP's special shared-cache restrictions for requests containing an `Authorization` header are not the same thing as a general prohibition on caching requests with cookies.

Similarly, a `Set-Cookie` response header does not automatically prohibit caching.

The origin must communicate appropriate caching semantics, and the intermediary must implement them correctly.

The distinction between Cookie and Authorization matters because many web applications use cookies for authentication.

### Could we include the cookie in the cache key?

Technically, a cache can vary responses based on selected request headers, and HTTP provides mechanisms such as `Vary` for representing some of these distinctions.

But building a shared cache of sensitive personalized reservations is often unnecessary and fragile.

Session cookies change.

Authorization rules may depend on more than one identifier.

User-specific representations can have complicated invalidation requirements.

A safer design is frequently to bypass the shared cache entirely for these responses.

The correct optimization is not necessarily to invent a more elaborate cache key.

Sometimes the correct optimization is to refuse caching where the correctness burden exceeds the benefit.

**A cache key is a claim about which requests are equivalent. If the claim is wrong, the cached response can be wrong—or dangerous.**

## 10. The Cache Stampede: When a Fast System Overloads Its Origin

Caching has another failure mode that doesn't involve private-data exposure.

Imagine a popular public hotel-search result.

The CDN stores the response for thirty seconds.

Thousands of customers request it during that interval.

Almost every request is answered at the edge.

Then the cached response becomes stale.

A large number of requests arrive before the cache has been refreshed.

If the CDN independently forwards all those requests to the origin, the application may experience a sudden surge.

The system that normally protects the origin has created a synchronized burst of origin traffic.

This is a cache stampede.

### Request collapsing

One mitigation is to coalesce equivalent outstanding cache misses.

The CDN or another caching layer allows one origin request to fetch the response while other matching requests wait for that result.

Instead of sending hundreds of duplicate origin requests, the cache performs fewer origin fetches.

The exact mechanism and guarantees depend on the implementation.

### Stale-while-revalidate

For suitable responses, a cache may serve a stale representation while it refreshes the data in the background.

This can maintain low latency and reduce synchronized origin load.

But the approach depends on the freshness requirements.

It may be appropriate for relatively stable public hotel descriptions.

It would be dangerous to treat stale search results as authoritative proof that the final room is still bookable.

The booking transaction must revalidate inventory and enforce its business invariants.

### Origin shielding

A CDN may use an additional caching layer or designated shield location to reduce repeated origin traffic from many edge locations.

This improves origin protection, but adds another cache whose behavior needs to be understood.

Every caching layer creates another place where response identity, freshness, and invalidation matter.

The general rule is:

**Cache data according to its acceptable staleness and equivalence requirements, not simply according to how expensive the origin request is.**

## 11. The Incident Investigation: Finding the Missing Request

Let's return to Bob, who saw Alice's reservations.

The backend team searches its logs for Bob's request and cannot find it.

That absence is the first valuable clue.

It doesn't prove the request was cached. Logs may be incomplete, sampling may exclude relevant requests, or the request may have reached a different backend.

But it suggests that the team should examine earlier participants in the request chain.

### Step one: establish who answered

The browser's network tools may expose response headers and timing information.

The CDN may provide request logs with cache status or a correlation identifier.

Those records can establish whether the edge answered the request from its cache or contacted the origin.

Different CDN providers use different headers and logging conventions.

A header name alone is not universal evidence. Interpret it according to the actual provider.

### Step two: reconstruct the cache key

Determine which request characteristics participated in cache lookup.

Was the key only the URL path?

Did it include query parameters?

Were relevant headers considered?

Was authenticated traffic supposed to bypass caching?

Did a global rule override origin cache directives?

The objective is to identify why two non-equivalent requests were treated as interchangeable.

### Step three: inspect the origin response

Check which cache-control directives the application sent for the sensitive endpoint.

Was there a clear `no-store` directive?

Was an intermediary-specific caching rule overriding the intended behavior?

Was the route accidentally included in a generic "cache all GET responses" rule?

The key is to find the boundary where the incorrect policy entered the system.

### Step four: contain the leak

Disable inappropriate shared caching for the affected route.

Purge affected cached responses where necessary.

Verify the corrected behavior using controlled test identities and synthetic data.

Then investigate the potential exposure window using available logs and records.

The incident may require security and privacy response procedures beyond the infrastructure fix.

### Step five: prevent recurrence

Add release tests that verify cache behavior for authenticated endpoints.

Review CDN rules as part of the application's security configuration.

Document which routes may be cached and under what conditions.

Ensure that a change to application authentication, response shape, or cache policy triggers appropriate review.

The most valuable lesson isn't "remember to add a header."

It's that CDN configuration is executable application behavior and deserves the same engineering scrutiny as code.

## 12. Designing a Defensible Production Edge

Imagine we are designing the platform again.

We have four broad traffic categories.

### Static, versioned assets

Use long-lived caching for content-hashed static resources.

Serve them efficiently from the CDN.

Ensure deployment procedures don't remove older assets while active browser sessions still reference them.

### Public catalogue information

Use bounded caching where acceptable.

Include the dimensions that genuinely affect representation identity.

Measure cache hit rate and origin load.

Protect the origin against stampedes.

Make clear that cached information is not necessarily a final transactional commitment.

### Authenticated customer data

Default to avoiding shared caching unless there is a thoroughly justified and tested design.

Use appropriate response directives and CDN bypass configuration.

Never assume URL equality means customer-data equality.

### Transactions and sensitive operations

Treat payment, reservation creation, cancellation, and similar operations as authoritative business workflows.

Use correct HTTP semantics and application-level idempotency where necessary.

An intermediary must not turn retries into duplicate business effects.

We will examine the detailed behavior of intermediary timeouts, streaming, and retries in CS230-L10.

For now, remember that every additional network participant can introduce another timeout or retry decision.

### The architecture's real responsibilities

The CDN improves geographic delivery and may apply edge security or caching.

The load balancer distributes traffic to eligible backends.

The backend enforces business authorization and operations.

The database preserves authoritative business state.

But none of these responsibilities is completely isolated.

The CDN can accidentally leak data.

The load balancer can route to unhealthy instances.

Forwarded headers can become a security vulnerability.

TLS configuration can expose an unprotected origin hop.

And excessive caching can hide the very application behavior the team is trying to observe.

A production edge should be treated as part of the software architecture, not as decorative infrastructure placed in front of it.

## 13. The Oral Examination

Answer these questions aloud before reading the solutions. Each answer should explain the mechanism and identify what evidence would confirm it.

### Challenge 1 — The Missing Backend Request

A customer receives HTTP 200 containing incorrect account data.

The backend logs show no corresponding request.

Name three plausible explanations and explain how you would distinguish them.

### Challenge 2 — Four Servers, One Bottleneck

A team increases its Node.js instances from two to eight.

HTTP latency becomes worse.

Database CPU and connection counts increase sharply.

Why didn't load balancing help?

### Challenge 3 — The Forged Client Address

A backend uses `X-Forwarded-For` for rate limiting.

Clients can reach the backend directly, and the application trusts the first IP in the header.

What is dangerous about this design?

### Challenge 4 — The HTTPS Assumption

A browser successfully establishes HTTPS with a CDN.

The CDN contacts the origin through another connection.

Does the browser's successful TLS handshake prove that the origin connection is authenticated and encrypted?

### Challenge 5 — The Cache That Was Too Helpful

Two customers request `/api/me/reservations`.

They have different authenticated sessions.

The CDN returns the same stored response to both.

Explain the likely error and propose a safer design.

### Challenge 6 — The Cache Stampede

An edge cache serves a popular public search response.

Whenever the response expires, origin load spikes.

Explain the mechanism and propose two mitigations.

### Challenge 7 — Sticky Sessions

A customer logs in through backend A.

A load balancer uses session affinity.

Backend A fails.

Why might the customer lose their session, and what architectural improvement would reduce that risk?

## 14. Solutions and Discussion

### Solution 1 — Identify the participant that answered

The response may have come from a CDN cache, a browser or service-worker cache, or another intermediary rather than the expected backend.

Incomplete logging or routing to an unexpected application instance is also possible.

Inspect browser request details, edge request logs, cache status, routing decisions, and correlation identifiers.

A missing application log is a clue, not proof of caching.

### Solution 2 — The bottleneck moved downstream

Adding application instances increased concurrent database demand.

If database queries, locks, connections, or I/O were already limiting throughput, additional Node.js capacity could amplify contention rather than improve useful work.

Measure where request time is spent and optimize the limiting dependency or control aggregate concurrency before adding more replicas.

### Solution 3 — Forwarding metadata is untrusted without a boundary

A client can forge forwarding headers.

If the backend accepts direct connections and interprets arbitrary headers as trustworthy client identity, attackers may evade IP-based controls or corrupt audit information.

Restrict direct backend access and configure a trusted proxy chain whose forwarding metadata is interpreted correctly.

### Solution 4 — TLS protection is per connection

The browser authenticated the CDN endpoint.

That doesn't prove the CDN's origin connection is protected or correctly authenticated.

The origin connection requires its own TLS configuration and appropriate certificate or identity verification.

A TLS-terminating CDN is a trusted participant with access to HTTP contents.

### Solution 5 — The cache key ignored authorization context

The CDN treated requests with different authorized response identities as equivalent.

The backend may have authenticated correctly for the original response, but the later cache hit bypassed origin authorization.

The safer default for sensitive personalized data is to disable shared caching through explicit application semantics and verified CDN rules.

### Solution 6 — Expiration synchronized origin misses

Many equivalent requests reached the cache after the stored response became stale.

Without request coalescing or appropriate stale serving, they produced repeated origin fetches.

Request collapsing, stale-while-revalidate where safe, and origin shielding can reduce the load.

The freshness policy must still match business correctness requirements.

### Solution 7 — Affinity doesn't preserve process memory

Sticky routing may direct future requests to backend A, but it cannot preserve A's memory after failure.

If session state exists only in A's process, the session can disappear with it.

Shared or durable session storage, or another appropriately designed session strategy, makes backend instances more replaceable.

## 15. The Mental Model Worth Keeping

An intermediary is not necessarily a transparent pipe.

It may select destinations, terminate connections, inspect messages, modify metadata, cache responses, enforce policies, and generate its own errors.

Its configuration can therefore affect performance, correctness, security, and availability.

Whenever a proxy, load balancer, or CDN becomes part of an architecture, ask:

**What information can it see? What decisions can it make? What state does it retain? Which claims about the original client can it trust? What happens when it is wrong?**

Those questions reveal more than memorizing a particular cloud provider's load-balancer product names.

## 16. Next Lecture — CS230-L10: Modern HTTP Transport and Streaming

We've examined the intermediaries that stand between clients and applications.

But we haven't yet explored how modern HTTP transports change communication through those intermediaries.

HTTP/1.1, HTTP/2, and HTTP/3 differ in connection behavior, multiplexing, and transport mechanisms.

Streaming responses create new challenges for proxies that buffer content.

WebSockets and gRPC introduce long-lived connections, framing, and lifecycle decisions.

Timeouts and retries can behave differently at every hop.

In CS230-L10, we'll follow one application conversation through these modern transport mechanisms and investigate the failures that appear when intermediaries disagree about how long a request should live.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — The Intermediary Investigation

The objective is to investigate proxy behavior, routing, and caching using systems you control or are authorized to test. Avoid experimenting with other users' authenticated data.

### Lab A — Identify who answered an HTTP request

Choose a website or API you control that uses a CDN or reverse proxy.

Inspect its headers:

```bash
curl -sS -D - -o /dev/null https://YOUR-TEST-HOST/
```

Look for documented cache-status or intermediary-related headers.

Repeat the request and compare the results.

Do not assume a particular header is universal across CDN providers.

Determine whether the response was served from a cache or fetched from the origin, using the actual provider's semantics.

### Lab B — Compare cache policies

Consider three responses:

**Version A**

```http
HTTP/1.1 200 OK
Cache-Control: public, max-age=31536000, immutable
Content-Type: application/javascript
```

**Version B**

```http
HTTP/1.1 200 OK
Cache-Control: public, s-maxage=30
Content-Type: application/json
```

**Version C**

```http
HTTP/1.1 200 OK
Cache-Control: private, no-store
Content-Type: application/json
```

Decide which policy is appropriate for:

1. A content-hashed JavaScript bundle.
2. A public hotel-search result that may be stale for thirty seconds.
3. An authenticated customer's private reservations.

Explain why the choice is based on response semantics, not merely response size or computational cost.

### Lab C — Design the cache key

Consider a public endpoint:

`GET /api/hotels?city=Paris&currency=EUR&lang=en`

The response depends on the city, currency, and language.

Design a cache key that distinguishes relevant representations.

Now introduce a logged-in customer with a negotiated loyalty price.

Would you extend the cache key, bypass caching, or create a separate public representation?

Explain your decision and its security implications.

### Lab D — Reproduce a header-trust mistake conceptually

Imagine an application's Express configuration enables trust of every proxy without restricting direct access.

The application uses `req.ip` for security-sensitive rate limiting.

A client can send an arbitrary `X-Forwarded-For` header directly to the backend.

Explain why this design is unsafe.

Then propose a corrected architecture that:

1. Restricts direct backend reachability.
2. Defines which intermediary addresses are trusted.
3. Handles forwarding headers at the trust boundary.
4. Tests client-IP interpretation with known proxy hops.

Do not test spoofing against a public system you don't own.

### Lab E — Review a load-balancing design

A service has four backend instances.

Each instance has a maximum safe application concurrency of fifty requests.

All instances share PostgreSQL.

The database can sustain only one hundred concurrent expensive queries before latency deteriorates significantly.

The team proposes increasing the application pool to eight replicas.

Explain why this may not increase throughput.

Design an admission-control or concurrency-management strategy that respects the shared database bottleneck.

### Lab F — Investigate a private-response caching incident

Use the fictional reservation leak from the lecture.

Prepare an incident report answering:

1. Which request was served from cache?
2. Which cache-key assumption was invalid?
3. Why didn't backend authorization prevent the leak?
4. What immediate containment is necessary?
5. What evidence would establish the exposure window?
6. What test should prevent recurrence?

The strongest answer should identify the interaction between origin response policy, intermediary configuration, and authenticated request identity.

---

## Further Reading

1. [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) — Shared and private caches, storage conditions, directives, and cache keys.
2. [MDN — HTTP Caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching) — Practical caching behavior.
3. [MDN — X-Forwarded-For](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For) — Forwarding chains and security.
4. [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — HTTP message semantics and intermediaries.
5. [NGINX — HTTP Load Balancing](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/) — Backend selection strategies.
6. [Cloudflare — Understanding Cache](https://developers.cloudflare.com/cache/) — An example of modern CDN caching controls.
7. [AWS — Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html) — An example of managed Layer Seven load balancing.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is intentionally fenced for fast visual revision rather than voice playback.*

```text
CS230-L09 — PROXIES, LOAD BALANCERS, AND CDNs

REQUEST JOURNEY

  Browser
    -> CDN / edge reverse proxy
    -> Load balancer
    -> Backend application
    -> Database

  Each intermediary can have its own connection,
  TLS boundary, routing decision, and timeout.

PROXY TYPES

  Forward proxy
    Represents client-side traffic
    E.g. corporate internet gateway

  Reverse proxy
    Represents origin-side infrastructure
    E.g. CDN, API gateway, HTTP load balancer

L4 VS L7

  L4
    IP, port, transport/connection information
    Can forward encrypted traffic without HTTP awareness

  L7
    HTTP host/path/method/headers
    Can route per HTTP request
    Requires visibility into HTTP contents

LOAD-BALANCING STRATEGIES

  Round robin       Distribute eligible traffic in sequence
  Least connections Prefer fewer active connections
  Least requests    Prefer fewer outstanding requests
  Weighted          Different backend traffic proportions
  Consistent hash   Stable affinity based on key

  Equal request counts != equal work
  More backend replicas != more useful throughput

STICKY SESSIONS

  Routing affinity to backend
  Does NOT preserve session memory after backend failure
  Shared/durable state improves replaceability

HEALTH CHECKS

  Liveness:
    Is the process functioning?

  Readiness:
    Should this instance receive traffic?

  Drain:
    Stop new routing while handling existing work

  Shared dependency failures can invalidate
  simplistic all-or-nothing health checks

FORWARDED IDENTITY

  X-Forwarded-For
  Forwarded
  X-Forwarded-Proto
  X-Forwarded-Host

  Header value != authenticated client identity
  Define trusted proxy hops and backend access restrictions
  Never trust arbitrary client-supplied forwarding metadata

TLS

  Browser -> CDN:
    One TLS session

  CDN -> origin:
    Another TLS session (or another configured transport)

  TLS termination grants intermediary HTTP visibility
  Re-encryption requires its own origin authentication
  Browser TLS success != origin TLS correctness

CDN

  Geographically distributed reverse proxy
  Can cache, terminate TLS, route, filter, and enforce policies
  Cache hit may produce no backend request

CACHE EQUIVALENCE

  Cache key defines which requests can reuse a response
  Must include all relevant representation dimensions
  URL equality != authorization equality

PRIVATE-DATA INCIDENT

  Alice GET /api/me/reservations
  Origin correctly authenticates Alice
  CDN incorrectly caches under URL-only key
  Bob requests same URL
  CDN returns Alice's response
  Origin never evaluates Bob's authorization

  Fix:
    Stop unsafe shared caching
    Appropriate Cache-Control
    Verify CDN overrides and bypass rules
    Purge affected entries
    Investigate exposure

HTTP CACHE DIRECTIVES

  private:
    Shared caches must not store unqualified private response

  no-store:
    Caches must not store the response

  public:
    Enables shared caching subject to HTTP requirements

  s-maxage:
    Shared-cache freshness lifetime

  Vary:
    Declares additional request-header dimensions

  Cookie does not automatically prohibit caching
  Set-Cookie does not automatically prohibit caching
  Authorization has special shared-cache rules

CACHE STAMPEDE

  Popular entry expires
    -> Many concurrent misses
    -> Origin traffic spikes

  Mitigations:
    Request collapsing
    Stale-while-revalidate when safe
    Origin shielding
    Appropriate freshness and TTL design

OBSERVABILITY

  Browser success != origin processing
  Missing backend log != definitive proof of cache hit
  Inspect CDN cache status, routing, trace IDs, timing,
  origin logs, and actual request path

TRAFFIC POLICIES

  Static hashed assets:
    Long-lived caching

  Public search:
    Bounded caching with correct variant key

  Authenticated private data:
    Avoid shared caching by default

  Transactional operations:
    Authoritative business decisions, safe retry semantics

FIVE SENIOR QUESTIONS

  What can the intermediary inspect?
  What decisions can it make?
  What state does it retain?
  Which forwarded claims can it trust?
  What breaks when its assumptions are wrong?

SENIOR LINE

  "An intermediary is part of the application architecture,
   not a transparent network pipe. I design its cache identity,
   routing, health, TLS, and forwarding trust boundaries
   according to business correctness and security requirements."
```
