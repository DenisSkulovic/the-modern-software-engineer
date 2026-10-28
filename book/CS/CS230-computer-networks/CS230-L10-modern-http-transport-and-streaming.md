---
id: CS230-L10
course: CS230
title: "Modern HTTP Transport and Streaming"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS230-L09
next: CS230-L11
---



# CS230 — Computer Networks and Web Protocols

## Lecture 10: Modern HTTP Transport and Streaming

*Your server sends the first result after one second. The browser receives nothing for thirty seconds, then everything appears at once. The backend is innocent, the network is technically working, and the reverse proxy has quietly defeated the entire purpose of streaming.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity platform generating an investigation report.

A customer submits a domain. The backend analyzes DNS records, discovers exposed services, inspects web technologies, and uses an AI model to summarize the findings.

The complete report takes thirty seconds to generate.

But the first finding is available almost immediately.

Wouldn't it be better to display results progressively?

The customer could see the first discovered assets after one second, the risk analysis after ten, and the final report after thirty.

Your Node.js application implements streaming.

Locally, it works beautifully.

The browser receives each update as soon as it becomes available.

Then you deploy the application behind a reverse proxy.

The customer clicks Generate.

Nothing happens.

One second passes. Five seconds. Twenty seconds.

Finally, after thirty seconds, the entire report appears.

The application logs prove that it generated updates throughout those thirty seconds.

So where were the updates hiding?

The answer requires understanding how HTTP messages travel, how modern transports multiplex work, and why intermediaries sometimes choose to buffer data instead of forwarding it immediately.

## 1. HTTP describes a conversation, not just a connection

We learned in CS230-L03 that HTTP defines methods, status codes, headers, caching semantics, and other rules for exchanging representations.

Those meanings don't fundamentally depend on whether we use HTTP/1.1, HTTP/2, or HTTP/3.

A GET request still asks for a representation.

A 404 still reports that the requested resource wasn't found.

An authorization failure doesn't become something else because the connection uses QUIC.

What changes is the machinery carrying the messages.

Imagine sending the same letter by ordinary post, courier, or a dedicated delivery network.

The meaning of the letter remains the same.

The transport affects how quickly it arrives, how deliveries share infrastructure, and what happens when something goes missing.

HTTP versions are similar.

They preserve the broad application semantics while changing how requests and responses are represented and transported.

## 2. HTTP/1.1 — reuse the connection

In HTTP/1.1, messages use a textual wire format.

A request contains a request line, headers, and an optional body. The response has corresponding elements.

HTTP/1.1 normally supports persistent connections.

That means a browser doesn't have to establish a new TCP and TLS connection for every resource.

It can reuse an existing connection for subsequent HTTP exchanges.

This avoids repeated connection-establishment costs.

But there's a limitation.

HTTP/1.1 does not provide modern multiplexing of independent requests within one connection.

It has a pipelining mechanism, but responses must be associated with requests in order.

If an earlier response is slow, a later response cannot simply leap ahead.

Browsers therefore commonly use multiple connections to enable parallel transfers with HTTP/1.1.

That approach works, but creates additional connection overhead.

## 3. HTTP/2 — several conversations on one connection

HTTP/2 introduces a binary framing system.

Multiple logical streams share one TCP connection.

Imagine a browser requesting a stylesheet, a JavaScript bundle, and an image.

Each response belongs to its own HTTP/2 stream.

Frames from those streams can be interleaved over the same connection.

The server doesn't have to finish sending the entire image before sending data belonging to the stylesheet.

This is multiplexing.

It removes an important HTTP-level ordering restriction.

But HTTP/2 still uses TCP.

TCP presents an ordered byte stream.

If some TCP data is lost, later bytes cannot simply be delivered to HTTP/2 past the missing gap.

Even if those later bytes contain frames for another HTTP request, progress can be delayed.

HTTP/2 solved one kind of head-of-line blocking while retaining another at the transport layer.

## 4. HTTP/3 — independent streams over QUIC

HTTP/3 changes the transport foundation.

Instead of HTTP/2 over TCP, it uses QUIC, generally carried over UDP.

QUIC implements reliable streams, loss recovery, congestion control, and integrated TLS 1.3 security.

The important difference is that independent QUIC streams don't require one global byte-delivery order.

If data for stream A is lost, stream B may continue progressing when its own necessary data has arrived.

This avoids TCP's connection-wide stream-delivery bottleneck.

But HTTP/3 isn't immune to packet loss.

The streams still share network capacity and connection-level congestion control.

A busy or lossy connection can still be slow.

**HTTP/3 improves the independence of stream delivery. It doesn't abolish network congestion, application bottlenecks, or bad architecture.**

## 5. Streaming is not a new HTTP version

Now return to our report generator.

The application wants to send data progressively.

That is an application behavior.

It isn't inherently an HTTP/3 feature.

HTTP/1.1 can deliver a response incrementally, including through chunked transfer coding.

HTTP/2 can deliver incremental DATA frames on a stream.

HTTP/3 can deliver progressive response data through QUIC streams.

The essential requirement is that the backend emits partial results and the relevant transport path delivers them without inappropriate delay.

A reverse proxy may choose to buffer an upstream response before sending it downstream.

For ordinary responses, buffering can improve efficiency.

For live progress updates, it can make streaming appear broken.

### The streaming path

```text id="mht901"
Report generator
  |
  | Produces update every second
  v
Node.js HTTP server
  |
  | Sends incremental response data
  v
Reverse proxy
  |
  | Buffer or forward?
  v
Browser
  |
  v
Customer sees progress
```

Every relevant intermediary must cooperate with the desired incremental delivery.

The backend emitting data is necessary, but not sufficient.

## 6. Different streaming problems need different protocols

Suppose the server needs to send progress notifications to the browser.

The client mostly listens.

Server-Sent Events, or SSE, can be a good fit.

Now imagine a collaborative editor where users continuously exchange changes in both directions.

WebSockets may be more appropriate.

Or imagine communication between internal services using typed request and response messages, including long-running streaming operations.

gRPC may be useful.

These technologies are not competing answers to one identical problem.

They represent different communication contracts.

The correct choice depends on directionality, message framing, client support, reconnection behavior, infrastructure compatibility, and operational requirements.

## 7. A stream doesn't mean eternal connectivity

Our customer begins receiving report updates.

Then their phone changes networks.

The connection disappears.

What happens next?

The browser may reconnect.

But does it know which updates were already received?

Can it recover missed events?

Will the server repeat the last update?

Does the application still retain the generated report?

The transport doesn't automatically answer these questions.

A connection is a temporary communication channel.

The business operation needs its own stable identity and durable state.

If report `4821` continues running after the browser disconnects, the client should be able to discover its current state when it returns.

This gives us an important principle:

**Streaming improves how progress is delivered. It shouldn't become the only place where important progress exists.**

### Three questions before the Deep Dive

1. How can HTTP/2 multiplex several requests while still being affected by TCP head-of-line blocking?
2. Why doesn't HTTP/3 automatically make every website faster?
3. Why might an application emit events every second while the browser receives them all at once?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Report That Arrived Thirty Seconds Late

Our cybersecurity platform has introduced AI-generated asset reports.

A customer requests a report for their organization.

The backend gathers information from MongoDB, launches several supporting queries, and streams generated explanations as soon as they become available.

In development, a progress indicator advances smoothly.

The first update arrives after approximately one second.

Production behaves differently.

The browser displays no progress for thirty seconds.

Then every update appears together.

The API process has not crashed.

The database queries are healthy.

The application logs show that updates were emitted at regular intervals.

The frontend code uses the correct streaming interface.

What could have changed?

The production request now passes through an ingress reverse proxy and CDN.

One of those intermediaries buffers the response.

Instead of forwarding each small piece as it arrives, it accumulates the body and delivers it much later.

The transport connection is alive.

The response is technically successful.

But the user-visible behavior is wrong.

To diagnose this properly, we'll examine what each HTTP version makes possible—and what the surrounding infrastructure can still prevent.

## 2. HTTP Semantics Are Separate From HTTP Wire Format

One of the most useful conceptual distinctions in modern networking is the separation between application meaning and message transport.

HTTP defines requests, responses, methods, status codes, representations, and metadata.

Different HTTP versions carry those concepts using different framing and transport arrangements.

This is why you can deploy HTTP/3 at a CDN while keeping HTTP/1.1 between the CDN and your origin server.

The application may still receive an ordinary GET request.

The browser still expects the same broad HTTP response semantics.

The intermediary translates between protocol versions and manages separate connections.

### Why this distinction matters

Suppose the customer connects to your CDN using HTTP/3.

An engineer says, "Our backend supports HTTP/3 now."

Not necessarily.

The backend might still receive HTTP/1.1 requests from the CDN.

Likewise, enabling HTTP/2 on the origin doesn't prove the browser uses HTTP/2.

**The HTTP version is a property of a particular communication hop, not necessarily the complete end-to-end request journey.**

When investigating behavior, determine the negotiated protocol on the hop that actually matters.

## 3. HTTP/1.1: Persistence Without Multiplexing

Consider a browser loading a complicated page.

It needs HTML, JavaScript, CSS, fonts, images, and data from application APIs.

Establishing a separate connection for every resource would impose substantial overhead.

TCP handshakes, TLS handshakes, socket management, and connection state all have costs.

HTTP/1.1 normally allows persistent connections.

Once established, a connection can carry multiple successive request-response exchanges.

This can reduce repeated setup costs.

But HTTP/1.1 has no stream identifier that lets independent responses freely share one connection.

### The pipelining limitation

HTTP/1.1 defines pipelining.

A client can send multiple requests before receiving all their responses.

However, the responses must be returned in the corresponding request order.

Imagine the client asks for resource A and then resource B.

Resource A requires an expensive database query.

Resource B is ready immediately.

The server cannot send the final response for B ahead of A as though the response order were irrelevant.

The protocol relies on ordered responses to associate messages with requests.

This can cause head-of-line blocking.

The limitations and deployment difficulties of pipelining led browsers to rely largely on multiple parallel HTTP/1.1 connections instead.

### The price of multiple connections

Each connection consumes resources.

There are socket buffers, kernel structures, congestion-control state, and potentially TLS state.

Multiple connections can provide parallelism, but they aren't free.

That helps explain why HTTP/2's multiplexing model was a meaningful change.

## 4. HTTP/2: Streams and Frames

HTTP/2 introduces a binary framing layer.

Each HTTP request-response exchange belongs to a logical stream identified within the connection.

The connection carries frames.

Some frames contain request or response headers.

Others contain data.

Frames belonging to different streams can be interleaved.

Imagine three resources:

A stylesheet takes ten milliseconds to generate.

An image takes one second to transfer.

An API response takes two hundred milliseconds.

With HTTP/2, these exchanges can proceed through separate streams over one TCP connection.

The large image doesn't have to occupy the entire connection until its response finishes.

### Logical independence

An HTTP/2 stream has its own lifecycle.

It can be opened, carry data, and close.

It may also be reset independently under appropriate conditions.

The connection itself continues carrying other streams.

This is a major improvement over treating one connection as a sequence of complete HTTP/1.1 responses.

### Flow control

Multiplexing introduces a new challenge.

What if a sender produces data faster than the receiver can process it?

HTTP/2 provides flow control at both stream and connection levels.

A receiver advertises how much data it is prepared to accept.

The sender must respect those windows for flow-controlled data.

This helps bound buffering and prevents unrestricted data transmission into an overwhelmed receiver.

But flow control has its own complexity.

A stream may be blocked because its window is exhausted.

Or every stream may be affected by a connection-level flow-control limit.

Multiplexing doesn't mean unlimited concurrency.

The receiver and sender still have finite memory, processing capacity, and bandwidth.

### Header compression

HTTP/2 uses HPACK to compress header fields.

This is useful because related HTTP requests often repeat similar metadata.

Cookies, content-negotiation fields, and other headers can produce substantial repetition.

Header compression reduces some of that overhead.

It also introduces state and implementation complexity.

The important engineering model is that HTTP/2 optimizes the exchange of many related requests, not that every individual request becomes magically cheap.

## 5. The TCP Bottleneck Beneath HTTP/2

Now imagine that our HTTP/2 connection carries three streams.

Stream A downloads a large image.

Stream B loads an important stylesheet.

Stream C receives an API response.

The HTTP/2 layer allows frames from these streams to be interleaved.

But all those frames ultimately travel through one ordered TCP byte stream.

Suppose a TCP segment carrying part of stream A is lost.

Later TCP segments arrive.

Some contain frames belonging to streams B and C.

TCP cannot deliver those later bytes to the HTTP/2 implementation as a continuous ordered stream until the missing byte range has been recovered.

So B and C may also stall.

This is transport-level head-of-line blocking.

### Why TCP does this

TCP's contract is reliable, ordered byte-stream delivery.

It does not understand HTTP/2 stream identifiers.

From TCP's perspective, the connection contains one sequence of bytes.

Its job is to reconstruct that sequence correctly.

This design is powerful and widely useful.

But it means that a missing piece affects delivery of later bytes across the shared connection.

HTTP/2's multiplexing exists above that boundary.

It cannot bypass TCP's ordered-delivery guarantee.

### Why the distinction matters

HTTP/2 eliminates the ordinary HTTP/1.1 response-order constraint at the application framing layer.

It doesn't eliminate transport-level blocking caused by missing TCP data.

Those are different problems at different layers.

Confusing them leads to exaggerated claims about what multiplexing guarantees.

## 6. HTTP/3: QUIC Changes the Underlying Contract

HTTP/3 uses QUIC rather than TCP as its transport foundation.

QUIC commonly operates over UDP.

But it's misleading to describe HTTP/3 as simply "HTTP over UDP."

UDP itself provides datagrams with comparatively minimal transport semantics.

QUIC builds a sophisticated transport on top of that foundation.

It provides reliable streams, acknowledgments, loss recovery, congestion control, connection management, flow control, and integrated TLS 1.3 security.

### Independently ordered streams

Imagine a QUIC connection carrying three HTTP/3 requests.

Each request uses a separate QUIC stream.

A packet carrying data for stream A is lost.

Data for stream B arrives successfully.

Provided B's required stream data and protocol dependencies are available, the receiver can continue processing B without waiting for A's missing bytes.

The loss recovery remains necessary for A.

But the transport doesn't impose one global byte-delivery order across all streams.

This is the architectural advantage over HTTP/2 carried on TCP.

### Loss still affects the entire connection

Don't misinterpret stream independence as unlimited performance.

QUIC streams share the connection's congestion-control system and network capacity.

Packet loss can reduce the amount of data the sender is permitted to transmit.

If the connection becomes congested, several streams may slow down.

There can also be dependencies created by header compression or application behavior.

So HTTP/3 reduces one important form of transport-level blocking.

It does not eliminate congestion or all possible dependencies between requests.

### Header compression changes too

HTTP/3 uses QPACK for header compression rather than HTTP/2's HPACK.

This matters because compression designs that rely on an ordered shared transport can introduce unwanted dependencies in a system with independent streams.

QPACK is designed for HTTP/3's stream model.

You don't need to memorize the compression algorithms to reason about normal applications.

But you should understand why the transport change required rethinking parts of the framing and compression system.

## 7. QUIC Security and Connection Establishment

HTTP/3 relies on QUIC's integration of TLS 1.3.

With conventional HTTPS over TCP, the client establishes transport connectivity and negotiates TLS.

QUIC combines transport establishment with its TLS-based cryptographic handshake.

This can reduce sequential connection-setup work under appropriate conditions.

For short connections on high-latency networks, setup costs can matter.

But don't assume HTTP/3 always wins.

If a browser already has a warm HTTP/2 connection, a fresh HTTP/3 connection may not provide any setup advantage.

Implementation quality, server performance, and network conditions still matter.

### Zero-RTT early data

QUIC supports mechanisms that can allow previously connected clients to send certain application data early during connection resumption.

This can reduce latency.

But early data can be replayable under the relevant security model.

That matters for operations with side effects.

Consider creating a paid reservation.

Blindly allowing replayable early data to trigger another reservation or payment would be dangerous.

Application semantics and replay protection remain essential.

The transport supporting early data doesn't mean every application operation should use it.

### Connection migration

QUIC also has mechanisms that can support connection migration.

For example, a mobile device may move between Wi-Fi and cellular networks.

Under suitable conditions, an established QUIC connection can survive certain network-path changes without being defined solely by the original IP-address-and-port tuple.

But migration isn't guaranteed in every environment.

Client behavior, intermediary support, transport policy, and network conditions can still terminate the connection.

This is a capability, not an eternal-connectivity promise.

## 8. How a Client Chooses HTTP/3

A user normally visits an HTTPS URL without specifying an HTTP version.

The client determines which protocol it can use with the destination.

For HTTPS over TCP, ALPN allows the client and server to negotiate an application protocol such as HTTP/2 or HTTP/1.1 during the TLS handshake.

HTTP/3 runs over QUIC, so the client needs to discover or know that an appropriate HTTP/3 endpoint is available.

One mechanism is the `Alt-Svc` response header.

Another involves DNS HTTPS resource records that can advertise supported application protocols and related connection parameters.

Client implementations may also retain previously discovered alternative-service information.

### The fallback problem

Suppose a browser learns that an origin supports HTTP/3.

It attempts a QUIC connection over UDP.

But the customer's corporate network blocks that traffic.

A well-designed client can fall back to a TCP-based HTTP version.

This is why HTTP/3 deployments commonly maintain HTTP/2 or HTTP/1.1 support.

The HTTP/3 setting on the server isn't proof that every browser successfully uses HTTP/3.

### Is HTTP/3 faster?

Sometimes.

It may provide meaningful improvements in certain lossy or mobile network conditions.

It may improve connection setup under suitable circumstances.

But on a stable network with warm connections, the difference can be modest.

An inefficient implementation can also underperform.

The correct conclusion is to measure actual user conditions, including negotiated protocol, latency, packet loss, and backend behavior.

**Protocol choice changes transport mechanisms. It doesn't eliminate the need to understand the workload.**

## 9. Streaming: Incremental Delivery Is an End-to-End Behavior

Now return to our report generator.

The first finding is ready after one second.

The application wants to send it immediately.

There are several ways to deliver an HTTP response incrementally.

With HTTP/1.1, chunked transfer coding can frame a response whose full length isn't known in advance.

With HTTP/2, the sender can transmit incremental DATA frames on the appropriate stream.

With HTTP/3, response data can be delivered incrementally through the QUIC stream.

The application doesn't need to hold the complete response before beginning delivery.

But every participant in the path has its own buffering and forwarding behavior.

### The buffering proxy

Our Node.js server emits one update every second.

The reverse proxy receives those updates from the upstream connection.

Instead of immediately forwarding each one, it buffers the response.

This can be efficient for ordinary responses.

The proxy may reduce the overhead of many small writes and manage upstream and downstream connections more independently.

But for a progress stream, the buffering creates the exact user experience we were trying to avoid.

The browser receives everything together.

### Flush doesn't guarantee arrival

The application may flush its response stream.

That ensures progress through some local buffering boundary.

It doesn't guarantee immediate arrival at the browser.

The operating system, TLS layer, reverse proxy, CDN, compression system, and client-side buffering can all influence when data becomes visible.

Different implementations have different behaviors.

For NGINX, response buffering can be controlled through configuration, and suitable upstream responses may use `X-Accel-Buffering` when permitted by the proxy configuration.

But this isn't a universal header understood by every CDN or gateway.

The actual intermediary chain must be configured and tested.

### Streaming has an observability trap

Suppose the server sends its first byte after one second.

The browser sees the first visible update after thirty seconds.

The application logs show fast processing.

A traditional response-duration metric might not reveal exactly where the delay occurred.

You need measurements that distinguish:

- When the backend produced the first update.
- When it wrote the first response data.
- When the proxy received that data.
- When the proxy forwarded it.
- When the client actually received and processed it.

These are separate events.

The first useful byte matters as much as the final completion time when the product promises progressive output.

## 10. Server-Sent Events: One-Way Updates Over HTTP

Server-Sent Events, usually abbreviated SSE, provide a simple way for servers to send an ongoing stream of events to clients.

In browsers, the `EventSource` interface supports this pattern.

The client makes an HTTP request.

The server responds with the media type `text/event-stream`.

The connection remains open while the server emits events.

A progress event might say that DNS enumeration has completed.

Another might announce that port discovery has finished.

Another might provide the final report location.

The server doesn't need a new HTTP request for every update.

### Event framing

SSE messages use a text format.

They can include fields such as `event`, `data`, and `id`.

A blank line terminates an event.

The event ID can support reconnection and replay behavior when the server implements the corresponding recovery semantics.

For our report, each event might identify its progress position.

The client can remember the latest event it received.

After disconnection, it can reconnect and indicate the last observed event ID through the standard EventSource mechanism.

### Reconnection doesn't create durable history

This is a critical qualification.

The browser may reconnect automatically.

But the server must retain or reconstruct the relevant event history if it promises to replay missed events.

Otherwise, reconnection simply establishes a new stream.

The client may miss updates.

Or it may receive some updates again.

For a report generator, that can be handled through a durable report state and monotonically identifiable events.

The stream should communicate progress, not act as the sole authoritative record of the report.

### Heartbeats

Long-lived SSE connections can encounter idle timeouts.

An application may periodically send comment lines or other harmless heartbeat traffic to keep an otherwise quiet stream active.

But heartbeats aren't a replacement for correct timeout configuration.

They also don't guarantee that every intermediary or client will keep the connection open indefinitely.

### When SSE makes sense

SSE is attractive for server-to-browser updates:

Scan progress.

Report generation.

Notifications.

Live monitoring.

It works naturally with HTTP infrastructure and has a relatively simple client model.

But if the client needs frequent bidirectional messaging, another protocol may be more appropriate.

## 11. WebSockets: Two-Way Communication With a Different Lifecycle

WebSockets provide a bidirectional message-oriented communication channel.

A browser and server establish a WebSocket connection, commonly using an HTTP/1.1 Upgrade handshake.

Standardized establishment mechanisms also exist for HTTP/2 and HTTP/3 environments, subject to implementation support.

Once established, the channel carries WebSocket messages rather than independent ordinary HTTP request-response exchanges.

This is useful for applications where both sides need to send information frequently.

Imagine a collaborative interface where several analysts edit a security investigation simultaneously.

The server broadcasts changes.

Clients submit edits.

The application needs bidirectional communication without creating a separate HTTP request for every small interaction.

WebSockets can be a good fit.

### The connection isn't the session

Suppose a browser disconnects for twenty seconds.

During that interval, other analysts continue making changes.

When the browser reconnects, what happens?

The WebSocket protocol doesn't automatically know which application updates the client missed.

The application needs a resynchronization strategy.

Perhaps it fetches the latest authoritative document state.

Perhaps it resumes from a durable event sequence.

Perhaps it compares version numbers and requests missing changes.

The connection provides communication.

The application provides state continuity.

### Slow consumers

WebSocket systems also need to consider backpressure.

What if the server produces messages faster than a browser can process them?

The browser's traditional `WebSocket` API doesn't offer a comprehensive built-in backpressure mechanism for received messages.

An application that receives messages too quickly may accumulate memory or become unresponsive.

Server implementations also need bounded outgoing queues and slow-client policies.

A system with ten thousand open WebSockets can be perfectly healthy in terms of connection count while consuming excessive memory because some clients cannot keep up.

### Operational consequences

Long-lived connections change how load balancers and deployments behave.

Idle timeouts matter.

Connection draining matters.

Server restarts require reconnection.

Authentication may need refreshing or revalidation.

A connection can remain open while the user's permission to receive certain information has changed.

WebSockets are useful, but they require explicit lifecycle design.

They are not simply "HTTP, but faster."

## 12. gRPC: Typed Remote Calls and Streaming

gRPC provides an RPC-oriented communication model.

Service interfaces are commonly defined using Protocol Buffers.

The definitions can generate client and server code across supported languages.

gRPC commonly uses HTTP/2 as its transport.

It supports several interaction patterns.

**Unary RPC:** one request and one response.

**Server streaming:** one request followed by multiple response messages.

**Client streaming:** multiple request messages followed by one response.

**Bidirectional streaming:** both sides exchange streams of messages.

This makes gRPC useful for internal service-to-service communication with structured contracts.

### Streaming is still bounded by resources

A gRPC stream is not an infinite queue.

Receivers need to process messages.

Flow control limits how much data can be in flight.

Applications need deadlines, cancellation handling, and resource bounds.

If a client stops reading, the server shouldn't blindly accumulate unlimited response data.

### Deadlines

A gRPC client can specify a deadline for an operation.

When that deadline expires, the client may stop waiting and the RPC is cancelled according to the relevant behavior.

But the server application must cooperate with cancellation.

A handler that continues an expensive operation without checking cancellation may waste resources.

And cancellation does not guarantee reversal of external side effects already performed.

### Browser compatibility

Ordinary gRPC's HTTP/2 requirements don't map directly onto every browser networking API.

Browser applications often use gRPC-Web with a suitable intermediary or translation layer.

This is an example of why protocol choice must consider the actual clients and infrastructure.

A technology that works naturally between backend services may require additional machinery when used from a browser.

## 13. Flow Control and Backpressure: Streaming Is Not Infinite

We've now encountered streaming in several forms.

HTTP/2 streams.

QUIC streams.

SSE.

WebSockets.

gRPC streaming.

They differ, but share a fundamental problem.

What happens when the producer generates data faster than the consumer can handle it?

Imagine an AI report generator producing ten thousand tokens per second.

The client's network can receive only a fraction of that rate.

If the server keeps generating and buffering without restraint, memory consumption grows.

Eventually, the process may become unstable.

### Backpressure is a feedback mechanism

Backpressure allows downstream capacity limitations to influence upstream production.

At the transport level, flow-control windows and congestion mechanisms restrict transmission.

At the application level, a streaming implementation may pause reading from an upstream source when a downstream write buffer becomes full.

In Node.js, stream APIs expose backpressure-related signals, including the return value of `write()` and the `drain` event.

The exact implementation matters.

A correct streaming program should not assume that a successful method call means all data has already reached the client.

### Backpressure doesn't necessarily stop computation

Suppose an AI provider continues generating output while the application is unable to send it onward.

The Node.js server might correctly pause its own writes.

But unless the application also controls its upstream data consumption, it may accumulate output in another buffer.

Backpressure has to propagate far enough upstream to protect the actual limiting resource.

This is a general systems principle:

**A bounded downstream resource requires bounded upstream production or bounded buffering.**

The same idea applies to queues, databases, network sockets, and worker pools.

## 14. Timeouts: Different Clocks Along the Same Journey

Our report request passes through the browser, CDN, reverse proxy, and Node.js server.

Each participant may have timeouts.

A connection timeout determines how long to wait for transport establishment.

A response-header timeout may limit how long the caller waits for the beginning of a response.

An idle or inactivity timeout may terminate a connection if no relevant data moves for too long.

An overall deadline limits the total operation duration.

These are different policies.

### The streaming failure

Suppose an SSE connection sends an event every ten seconds.

A proxy has a five-second upstream read inactivity timeout.

The proxy may terminate the stream between events because it sees no data for longer than its configured limit.

The application may need suitable heartbeats or a more appropriate proxy timeout.

Now suppose the stream emits heartbeats every second but never completes its actual task.

The connection may remain active while the business operation makes no useful progress.

An idle timeout alone doesn't detect that failure.

The application needs an operation-level deadline or progress policy.

### Overall deadlines

Imagine a user-facing operation with a ten-second budget.

The first intermediary consumes one second.

The next consumes another.

The backend takes several more.

A downstream call then retries.

If each component independently starts a fresh ten-second timeout, the total operation can greatly exceed the user's original budget.

A coordinated system propagates appropriate remaining time budgets.

But propagating a deadline is not the same as guaranteeing cancellation of every remote action.

The operation may already have produced durable side effects.

This takes us back to distributed-systems correctness.

## 15. Retries and the Ambiguous Outcome

Suppose a customer creates a reservation.

The browser sends a POST request through a CDN and load balancer.

The backend commits the reservation.

Before the response reaches the browser, the connection fails.

The browser sees a timeout.

Did the reservation happen?

Yes, in our scenario.

But the browser doesn't know that.

If it blindly repeats the request, it may create a duplicate reservation.

Now imagine multiple intermediaries also performing retries.

One logical user action can generate several attempts.

### Retry amplification

If several layers each allow multiple attempts, the total number of backend executions can multiply.

This is particularly dangerous during overload.

A struggling backend becomes slow.

Callers retry.

Retries add more work.

The backend becomes even slower.

More callers retry.

The system enters a retry storm.

### Safe retries require more than HTTP methods

HTTP defines safe and idempotent method semantics, but a business operation must be designed to honor the relevant guarantees.

A POST used for reservation creation can be made safely repeatable through an application-level idempotency mechanism.

The client supplies a stable operation identity.

The backend records and recognizes repeated attempts for the same logical operation.

Proper implementation must also handle concurrent duplicates, persistence, and retention.

A proxy configuration alone cannot create exactly-once business effects.

### The rule for intermediaries

Retries should be bounded.

They should consider the remaining deadline and whether the operation is safe to repeat.

They should avoid amplifying overload.

And there should be a clear understanding of which layer owns the retry decision.

Blind retries at every hop are not resilience.

They're a distributed denial-of-service attack against your own system.

## 16. Gateway Errors: Who Actually Failed?

When several HTTP-aware intermediaries participate in a request, errors can originate before the application receives anything.

Three status codes are particularly useful.

**502 Bad Gateway** generally means a gateway or proxy received an invalid response from an upstream server.

**503 Service Unavailable** indicates that the responding server is currently unable to handle the request, commonly because of overload or maintenance.

**504 Gateway Timeout** means a gateway or proxy did not receive a timely response from an upstream server it needed to complete the request.

These are semantic distinctions.

Real implementations may have provider-specific error behavior, so the exact status must be interpreted with the infrastructure's documentation and logs.

### The misleading 504

Imagine the browser receives HTTP 504.

The developer assumes the Node.js handler ran too long.

But the request may never have reached Node.js.

The gateway may have failed while establishing an upstream connection.

Or a connection pool may have been exhausted.

Or another intermediary may have timed out before forwarding the request.

The most important question is:

**Which participant generated the response, and what operation was it waiting for?**

This is why a gateway error should be investigated along the actual request path.

## 17. Diagnosing the Original Streaming Incident

Let's return to the thirty-second report delay.

The Node.js backend emits events every second.

The browser receives them together after thirty seconds.

We need evidence that distinguishes application delay from intermediary buffering.

### Start with the origin

Test the backend directly from an authorized environment that bypasses the production intermediary.

Observe whether event data arrives progressively.

If direct streaming works, the application is capable of incremental output on that path.

This doesn't prove every application behavior is correct, but it narrows the hypothesis.

### Add one intermediary at a time

Next, test through the reverse proxy.

If updates become delayed, inspect buffering, compression, flush behavior, and response timeout settings.

Then test through the CDN.

Some edge products have different support or configuration for long-lived streaming responses.

The goal is to find the first hop where the observed timing changes.

### Measure both first and last bytes

Time to First Byte, or TTFB, helps describe when the client begins receiving a response under the chosen measurement definition.

But a streaming application also needs to measure inter-event latency.

A fast TTFB followed by a long silence can still produce a terrible user experience.

Likewise, a slow first event may reflect actual backend work rather than proxy buffering.

### Correlate observations

Use request IDs and distributed tracing where supported.

Record when the backend generates an event and when the client receives it.

Proxy logs may expose upstream timing measurements.

But no single metric automatically describes every hop.

And a CDN may terminate one protocol and establish another toward the origin.

Always determine which participant measured which interval.

### The resolution

In our scenario, the reverse proxy is buffering responses.

The team configures the relevant route to forward streaming data appropriately, with suitable timeout and compression settings.

They verify that events arrive progressively through the complete production path.

The fix is not merely changing a configuration flag.

The fix is establishing that the user's intended incremental experience survives the actual architecture.

## 18. Choosing the Right Communication Model

Let's finish with a practical design decision.

Our cybersecurity platform has several kinds of communication.

### Normal API operations

Creating a scan, retrieving a report, and managing configuration fit naturally into ordinary HTTP request-response APIs.

Use clear resource semantics and appropriate deadlines.

For asynchronous work, return a durable operation identifier rather than keeping an ordinary request open indefinitely.

### Progress notifications

SSE is a strong option when the browser primarily needs server-originated updates.

The application can stream progress events and reconnect using durable operation state.

The server should support appropriate replay or state refresh.

### Collaborative interfaces

WebSockets can be appropriate when clients and servers exchange frequent bidirectional updates.

The application must handle disconnections, slow consumers, reconnection, and state synchronization.

### Internal streaming RPCs

gRPC can provide typed contracts and streaming communication between supported services.

Its deadlines and flow-control behavior must be understood.

For browser clients, account for gRPC-Web or another compatible interface where necessary.

### Large progressive responses

Ordinary HTTP streaming may be sufficient for generated reports or downloads.

But the entire intermediary path must preserve the intended response behavior.

Do not introduce WebSockets merely because the application wants to deliver a response progressively.

### The actual decision

Choose based on the communication contract.

Is the exchange finite or long-lived?

One-way or bidirectional?

Byte-oriented or message-oriented?

Does the client need replay after disconnection?

What are the maximum message rates?

Which protocols do browsers, proxies, CDNs, and backends actually support?

What happens when the connection disappears halfway through an operation?

Those questions matter more than choosing whichever protocol sounds most modern.

## 19. The Oral Examination

Answer these aloud before reading the solutions.

### Challenge 1 — The Multiplexing Misconception

HTTP/2 can carry several requests through one TCP connection.

Why can packet loss still delay otherwise independent HTTP/2 requests?

How does HTTP/3 change that behavior?

### Challenge 2 — The Misleading HTTP/3 Deployment

A CDN advertises HTTP/3 support, but the origin server supports only HTTP/1.1.

Is the architecture necessarily broken?

Which connection uses which protocol?

### Challenge 3 — The Buffered Stream

A backend sends SSE updates every second.

Direct connections receive updates immediately.

Connections through a reverse proxy receive all updates after twenty seconds.

Which mechanisms would you investigate?

### Challenge 4 — The Lost Progress Updates

A browser consumes SSE events for a long-running report.

The connection drops for fifteen seconds.

When it reconnects, several progress updates are missing.

What must the application provide if it promises reliable recovery?

### Challenge 5 — The Slow WebSocket Client

A real-time dashboard generates updates faster than a particular browser can process them.

What can go wrong, and how should the server respond?

### Challenge 6 — The Endless gRPC Request

A client cancels a gRPC operation after its deadline expires.

The server continues an expensive downstream computation.

Why can that happen?

What should the application implement?

### Challenge 7 — The Duplicate Reservation

A reservation POST reaches the backend and commits successfully.

The response is lost.

An intermediary retries the request.

What guarantees are needed to prevent duplicate business effects?

### Challenge 8 — The 504 That Never Reached Node.js

A browser receives HTTP 504.

No matching application log exists.

What evidence would you collect before increasing backend timeouts?

## 20. Solutions and Discussion

### Solution 1 — HTTP/2 multiplexes above an ordered TCP stream

HTTP/2 frames from independent streams share one TCP byte sequence.

A missing TCP segment prevents later bytes from becoming available to HTTP/2 until the gap is recovered.

HTTP/3 uses QUIC streams with independent ordered delivery, so loss affecting one stream need not block delivery of data belonging to another stream.

Congestion control and other shared constraints still exist.

### Solution 2 — Protocol versions are negotiated per hop

The browser can communicate with the CDN over HTTP/3.

The CDN can establish a separate HTTP/1.1 connection to the origin.

The intermediary translates the relevant HTTP messages between the protocols.

That architecture is valid when correctly implemented.

A client-facing HTTP/3 setting doesn't prove the origin itself uses HTTP/3.

### Solution 3 — Inspect buffering and the actual response path

Compare direct-origin and proxied timing.

Inspect proxy response buffering, compression, flush behavior, streaming support, and timeout configuration.

For NGINX, route-level buffering controls and supported upstream response headers may be relevant.

Verify behavior through the entire path rather than assuming one setting solves every intermediary.

### Solution 4 — Reconnection requires durable application state

EventSource may reconnect and carry a last-event identifier.

But the server must retain or reconstruct the relevant events if replay is promised.

Alternatively, the client can fetch the authoritative current report state and continue from there.

The SSE connection itself is not durable storage.

### Solution 5 — Bound queues and define slow-consumer behavior

A slow WebSocket consumer can cause buffers to grow and memory consumption to rise.

The server should enforce bounded output queues, appropriate backpressure or dropping policies where acceptable, and connection termination or resynchronization when necessary.

The policy depends on whether each message is critical or replaceable.

### Solution 6 — Cancellation doesn't automatically stop application code

The gRPC framework can signal cancellation, but a running handler may need to check that signal and propagate it to downstream work.

Application code must cooperate.

Cancellation also doesn't reverse external side effects already committed.

### Solution 7 — Preserve the logical operation identity

The repeated request must be recognized as another attempt to perform the same reservation operation.

A durable idempotency mechanism, correct concurrency handling, and appropriate transaction boundaries are required.

The intermediary should not blindly retry unsafe operations.

The application must enforce the business invariant.

### Solution 8 — Identify where the timeout originated

Inspect CDN and gateway logs, upstream connection timing, request correlation IDs, connection-pool state, routing, and target health.

A 504 can originate before the application receives the request.

Increasing a backend timeout without identifying the failing boundary may have no effect.

## 21. The Mental Model Worth Keeping

Modern HTTP transport is about managing multiple conversations over finite, unreliable, and shared resources.

HTTP/1.1 provides persistent request-response communication without modern multiplexing.

HTTP/2 multiplexes streams over TCP.

HTTP/3 uses QUIC to provide independently delivered streams without TCP's connection-wide ordered-byte-stream constraint.

SSE, WebSockets, and gRPC define different application communication contracts on top of transport mechanisms.

Streaming requires cooperation among the producer, network stack, intermediaries, and consumer.

And no transport version eliminates timeouts, resource limits, business uncertainty, or the possibility of disconnection.

Whenever you design a long-lived or incremental communication path, ask:

**What is the message contract? Where is data buffered? How does backpressure propagate? What happens when the connection ends? Which state must survive?**

Those questions are more durable than memorizing which HTTP version happens to be fastest in a particular benchmark.

## 22. Next Lecture — CS230-L11: Network Forensics for Software Engineers

We now understand the individual networking mechanisms covered throughout CS230.

DNS establishes names.

IP routing moves packets.

TCP and QUIC provide transport capabilities.

TLS establishes protected communication.

HTTP defines request-response semantics.

Proxies, CDNs, and load balancers create intermediary decisions.

Streaming and persistent connections introduce lifecycle and buffering concerns.

But real production incidents rarely tell us which layer failed.

They present symptoms.

An API works from your laptop but fails from Kubernetes.

An HTTPS connection succeeds in Chrome but fails in Node.js.

A CDN returns a response the backend never generated.

A stream buffers for thirty seconds.

A gateway reports 504 while the application logs nothing.

In CS230-L11, we'll enter the network incident room and practice distinguishing these failures through evidence rather than guesswork.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — Streaming Through Real HTTP Infrastructure

**Goal:** Observe incremental HTTP responses, protocol negotiation, client disconnects, and the difference between application writes and client-visible delivery.

The exercises use a local Node.js server and HTTP tools. No cloud account or production infrastructure is required.

### Lab A — Inspect available HTTP protocols

First inspect your installed curl version:

```bash
curl --version
```

The output lists supported features and protocols.

Some curl builds support HTTP/2 or HTTP/3; others do not.

Use an HTTPS endpoint you control or are authorized to test.

If your curl supports HTTP/2:

```bash
curl --http2 -sS -o /dev/null \
  -w 'HTTP version: %{http_version}\n' \
  https://YOUR-TEST-HOST/
```

If your curl supports HTTP/3:

```bash
curl --http3 -sS -o /dev/null \
  -w 'HTTP version: %{http_version}\n' \
  https://YOUR-TEST-HOST/
```

The `--http3` option can permit fallback, depending on curl behavior and version. An explicit HTTP/3-only test can be performed with `--http3-only` in supporting builds.

**Investigate:** Did the client actually negotiate the protocol you expected, or did it use a fallback?

### Lab B — Create a local SSE server

Create `stream-server.mjs`:

```javascript
import http from "node:http";

const server = http.createServer((req, res) => {
  if (req.url !== "/events") {
    res.writeHead(404).end("Not found");
    return;
  }

  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no"
  });

  res.flushHeaders();

  let sequence = 0;

  const timer = setInterval(() => {
    sequence += 1;

    const event =
      `id: ${sequence}\n` +
      `event: progress\n` +
      `data: ${JSON.stringify({
        step: sequence,
        timestamp: Date.now()
      })}\n\n`;

    console.log("Producing event", sequence);

    const accepted = res.write(event);

    if (!accepted) {
      console.log("Backpressure: output buffer is full");
      clearInterval(timer);
      res.once("drain", () => {
        if (!res.destroyed) {
          res.end();
        }
      });
      return;
    }

    if (sequence >= 10) {
      clearInterval(timer);
      res.end();
    }
  }, 1000);

  res.on("close", () => {
    clearInterval(timer);
    console.log("Connection closed");
  });
});

server.listen(8088, "127.0.0.1", () => {
  console.log("SSE server: http://127.0.0.1:8088/events");
});
```

Run:

```bash
node stream-server.mjs
```

The server emits ten events, one per second.

It uses HTTP/1.1 and ordinary Node.js HTTP streaming.

Notice that modern streaming behavior does not require HTTP/3.

This is a teaching example: a production stream should implement a robust backpressure strategy rather than simply ending the response when its write buffer fills.

### Lab C — Observe incremental delivery

In another terminal:

```bash
curl -N http://127.0.0.1:8088/events
```

The `-N` option disables curl's output buffering.

You should see events arrive progressively rather than all at once.

Compare the terminal output timing with the timestamps printed by the Node.js server.

**Questions:**

1. Which timestamp represents event generation?
2. Does the server's `res.write()` guarantee that the browser has received the event?
3. Which additional intermediaries would exist in a real production deployment?

### Lab D — Disconnect the client

Start the stream again.

After several events, interrupt curl with Ctrl+C.

Observe the Node.js server output.

The response's `close` handler should run when the connection closes.

Now imagine the endpoint starts an expensive background report instead of merely sending timer events.

Should closing the SSE connection necessarily cancel the report?

Not always.

A durable background report may need to continue even if the customer closes the browser.

The application should separate report execution state from the lifetime of its streaming connection.

### Lab E — Put a reverse proxy in front

If you already have NGINX in a local development environment, configure a disposable proxy route toward the Node.js server.

An illustrative location configuration is:

```nginx
location /events {
    proxy_pass http://127.0.0.1:8088;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 60s;
}
```

Use this only in a local configuration you control.

With proxy buffering disabled for the route, incremental data should be forwarded without being accumulated as a normal complete response.

Then compare behavior with buffering enabled.

Small test streams may still appear incremental under some configurations, so don't assume every proxy will demonstrate a dramatic delay without a sufficiently realistic buffering scenario.

The goal is to understand the mechanism, not force a particular result.

### Lab F — Choose a communication model

For each application, choose between ordinary HTTP, SSE, WebSockets, and gRPC.

1. A user starts a long-running domain scan and later retrieves its final result.
2. A browser displays incremental progress updates for the scan.
3. Several analysts collaboratively edit one investigation document.
4. Two backend services exchange typed streaming messages.
5. A browser downloads a large generated report.

Explain which properties matter:

Directionality, lifecycle, message framing, reconnection, replay, and infrastructure support.

There may be more than one defensible answer.

### Lab G — The retry amplification experiment

Imagine a request passes through three retrying components.

Each component permits up to three total attempts, including the original attempt.

In a pathological arrangement, the layers can multiply attempts.

A rough upper-bound example is three multiplied by three multiplied by three, or 27 downstream attempts for one logical operation.

Actual behavior depends on when retries are triggered and whether requests reach each layer.

**Investigate:** Why is this dangerous during overload, and how would you redesign retry ownership?

### Lab H — The streaming failure report

Write a short incident explanation for this scenario:

The backend emits an SSE event every second.

Direct connections receive the events promptly.

Production clients receive updates in thirty-second batches.

The application remains healthy.

Your report should identify:

- The established observations.
- The leading hypothesis.
- A test that distinguishes the proxy from the application.
- A safe configuration change.
- The evidence required to confirm recovery.

---

## Further Reading

1. [RFC 9112 — HTTP/1.1](https://www.rfc-editor.org/rfc/rfc9112.html) — Persistence, pipelining, message framing.
2. [RFC 9113 — HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html) — Streams, framing, multiplexing, flow control.
3. [RFC 9114 — HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html) — HTTP semantics over QUIC.
4. [RFC 9000 — QUIC Transport](https://www.rfc-editor.org/rfc/rfc9000.html) — QUIC connections, streams, loss recovery, migration.
5. [MDN — Using Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) — EventSource and SSE event format.
6. [MDN — WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) — Bidirectional browser communication and backpressure limitations.
7. [gRPC Core Concepts](https://grpc.io/docs/what-is-grpc/core-concepts/) — Unary and streaming RPCs.
8. [gRPC Deadlines](https://grpc.io/docs/guides/deadlines/) — Time budgets and cancellation behavior.
9. [NGINX Proxy Module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) — Proxy buffering and upstream configuration.
10. [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — Methods, status codes, and retry semantics.

---

## Dense Cheatsheet — Interview Glance Card

*The final reference is fenced for screen revision rather than continuous voice playback.*

```text
CS230-L10 — MODERN HTTP TRANSPORT AND STREAMING

HTTP SEMANTICS VS TRANSPORT

  Semantics:
    Methods, statuses, representations, headers

  Transport:
    How messages are framed and carried

  HTTP version is negotiated per hop.

HTTP/1.1

  Textual wire format
  Persistent TCP connections
  No modern multiplexing
  Pipelining responses must remain ordered
  Browsers commonly use multiple parallel connections
  Chunked transfer coding supports unknown-length bodies

HTTP/2

  Binary framing
  Multiple logical streams per TCP connection
  Interleaved HEADERS and DATA frames
  HPACK header compression
  Stream and connection flow control

  Solves HTTP-level response ordering limitations
  Does NOT eliminate TCP connection-wide HOL blocking

HTTP/3

  HTTP semantics over QUIC
  QUIC typically over UDP
  TLS 1.3 integrated into transport
  Reliable, independently ordered QUIC streams
  QPACK header compression

  Stream A loss need not block Stream B delivery
  Shared congestion control still limits capacity
  Not immune to packet loss
  Not universally faster

HTTP/3 DISCOVERY

  Alt-Svc
  DNS HTTPS records
  Previously discovered server support

  ALPN negotiates protocol
  UDP blocked -> TCP-based HTTP fallback

QUIC

  Streams
  Acknowledgments
  Loss recovery
  Congestion control
  Flow control
  Connection migration support
  TLS-integrated handshake

  Zero-RTT can carry replay risks

STREAMING

  Incremental delivery of response data
  Supported by HTTP/1.1, HTTP/2, HTTP/3
  Requires cooperation from intermediaries
  Proxy buffering can defeat progressive output
  Flush != confirmed client receipt

SSE

  Server -> client event stream
  Content-Type: text/event-stream
  Browser EventSource
  Fields: event, data, id, retry
  Automatic reconnection behavior
  Server must implement replay/state recovery
  Heartbeats may help avoid idle timeout

WEBSOCKETS

  Bidirectional message-oriented channel
  Long-lived connection
  Requires reconnection/state synchronization
  Slow consumers need bounded buffering
  Traditional browser WebSocket API lacks
  comprehensive receive-side backpressure

gRPC

  Commonly HTTP/2
  Typed service contracts, often Protobuf
  Unary, server-streaming, client-streaming,
  bidirectional-streaming RPCs
  Deadlines and cancellation
  Browser commonly requires gRPC-Web

BACKPRESSURE

  Producer rate > consumer capacity
    -> buffering grows
    -> latency/memory pressure

  Respond by:
    pausing upstream consumption
    enforcing bounded queues
    applying flow control
    defining slow-consumer policy

TIMEOUT TYPES

  Connect timeout       Establish transport
  Response timeout      Wait for response phase
  Idle timeout          No traffic/progress interval
  Overall deadline      Total operation time budget

  Idle heartbeat != useful business progress
  Cancellation != rollback

GATEWAY ERRORS

  502  Invalid upstream response
  503  Service temporarily unavailable
  504  Upstream response not received in time

  Identify which hop generated the error.

RETRIES

  Bound attempts
  Use backoff and jitter where appropriate
  Respect end-to-end deadlines
  Avoid layered retry amplification
  Preserve business operation identity
  Do not blindly retry non-idempotent effects

OBSERVABILITY

  Measure backend generation time
  Measure first response write
  Measure proxy forward timing
  Measure client-visible arrival
  Correlate request IDs across hops

  TTFB != full response duration
  Full response duration != first useful event latency

SENIOR QUESTIONS

  Which protocol on each hop?
  Which streams share transport state?
  Where is the data buffered?
  What happens when receiver slows?
  What happens when connection closes?
  Who owns retries and deadlines?
  Which business state must survive disconnect?

SENIOR LINE

  "HTTP versions change framing and transport behavior,
   but streaming correctness depends on the complete path.
   I separate protocol negotiation, buffering, backpressure,
   deadlines, retries, and durable application state rather
   than assuming a newer protocol guarantees better behavior."
```
