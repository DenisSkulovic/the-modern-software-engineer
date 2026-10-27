---
id: CS230-L02
course: CS230
title: "Networking for Software Engineers"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S02]
prev: CS230-L01
next: CS230-L03
---




# CS230 — Computer Networks and Web Protocols

## Lecture 02: Networking for Software Engineers

*Why a connection capable of transferring a gigabyte in seconds can still make a tiny API request feel painfully slow.*

---

# 1. The Mystery of the Gigabit Connection

Imagine you've deployed two identical Node.js services. Same code.

Same database schema.

Same hardware specifications. Same application configuration.

One runs in Frankfurt.

The other runs in Singapore. You're sitting in Berlin, investigating their performance.

Both servers have access to excellent network infrastructure, with gigabit connections and negligible CPU utilization.

You run a large file transfer test against each, and both demonstrate impressive throughput.

Then you make a tiny API request:

```http
GET /api/user/4812
```

The response contains barely 800 bytes.

Frankfurt responds in 35 milliseconds. Singapore responds in 230 milliseconds.

You investigate the application logs. Both servers executed the request in approximately 8 milliseconds.

Where did the remaining time go? More importantly, why doesn't that magnificent gigabit network connection make the difference disappear?

Now consider an even stranger observation. You download a large file from Singapore.

After a brief startup period, the transfer runs at hundreds of megabits per second. The network is clearly fast.

Yet a sequence of small, dependent API requests against the same server feels sluggish.

**The network can transfer enormous quantities of information while remaining frustratingly slow at completing conversations.**

This apparent contradiction sits at the heart of network engineering. To understand it, we need to separate several properties that everyday language tends to lump together under the word *speed*.

By the end of this lecture, you should be able to explain bandwidth versus latency, why TCP reliability and congestion control cost time, how windows and RTT limit throughput, and why application dependency graphs turn network physics into product pain.

---

# 2. Bandwidth and Latency: Two Different Kinds of Speed

Let's begin with an analogy. Imagine two transportation systems.

The first is a small courier van that travels between two neighboring buildings. It can carry only 100 kilograms per trip, but completes each journey in two minutes.

The second is an enormous freight train traveling across Europe. It can transport 2,000 tonnes at once, but takes twelve hours to arrive.

Which is faster? That question is incomplete.

If you're delivering a single envelope, the van is dramatically better. If you're transporting a thousand tonnes of steel, the train is vastly more efficient.

Computer networks have a similar distinction.

**Bandwidth** describes how much data a connection or path can transmit per unit of time.

**Latency** describes the delay involved in delivering information.

They are related, but not interchangeable.

## 2.1 Bandwidth

Network bandwidth is typically expressed in bits per second. A connection advertised as:

```text
1 Gbps
```

has a nominal data rate of one billion bits per second. Since eight bits make one byte, the theoretical conversion is approximately:

```text
1 Gbps = 125 MB/s
```

Actual application throughput will generally be lower because of protocol overhead, competing traffic, network limitations, and other factors. But the rough capacity is substantial.

Now consider a 1 KB API response. Even on a much slower 100 Mbps link, transmitting 1 KB takes roughly:

```text
1,000 bytes × 8 / 100,000,000 bits/s

≈ 0.08 milliseconds
```

In other words, the actual transmission time for this tiny payload is nearly irrelevant.

If the response takes 200 milliseconds, upgrading the bandwidth from 100 Mbps to 1 Gbps will not make the request ten times faster. The problem almost certainly lies elsewhere.

## 2.2 Latency

A network exchange experiences several different forms of delay.

**Propagation delay** comes from signals traveling through physical distance.

**Transmission delay** is the time spent putting the packet's bits onto the link.

**Processing delay** is network equipment examining and forwarding packets.

**Queueing delay** is packets waiting because a link or device is busy.

Propagation is especially interesting.

Electrical and optical signals travel extremely quickly, but not instantaneously. Light traveling through optical fiber moves at roughly 200,000 kilometers per second.

A 4,000-kilometer fiber path therefore has a propagation delay of approximately 20 milliseconds in one direction. A round trip requires at least twice that, before accounting for other delays.

This gives us an uncomfortable engineering reality:

**Some latency cannot be optimized away with better application code. It is a consequence of geography.**

A well-designed application acknowledges this limitation and minimizes the number of sequential exchanges that must cross those distances.

## 2.3 Round-trip time

We encountered RTT in CS230-L01.

Let's make it more concrete. Imagine a client sends a request and waits for a response:

```text
Client                          Server
  │                                │
  │────────── Request ────────────►│
  │                                │
  │◄───────── Response ────────────│
  │                                │
```

If the network's round-trip time is 100 milliseconds, even an almost instantaneous server-side operation can require approximately 100 milliseconds for the request and response to travel.

Now suppose the client needs to perform five dependent operations:

```text
Fetch user
    ↓
Fetch user's organization
    ↓
Fetch organization's permissions
    ↓
Fetch available products
    ↓
Fetch product pricing
```

Each request depends on information returned by the previous one. With a 100-millisecond RTT, the network alone can introduce approximately:

```text
5 × 100 ms = 500 ms
```

That's before meaningful server-side processing. If the operations were independent and could run concurrently, the situation would be quite different.

The key principle is:

**Latency accumulates along sequential dependencies. Bandwidth does not eliminate those dependencies.**

This is why API design, request batching, connection reuse, and geographical placement matter so much.

---

# 3. Packets: What Actually Travels Across the Network?

Suppose your application needs to transmit a 5 MB JSON document.

You might imagine the operating system sending five million bytes as one continuous object. But network transmission doesn't work quite that way.

Data is divided into smaller units. At the internet layer, these are IP packets.

When using TCP, application bytes are organized into TCP segments, which are carried inside IP packets. On an Ethernet network, those IP packets are typically carried inside Ethernet frames.

Conceptually:

```text
Ethernet Frame
┌───────────────────────────────────────┐
│ Ethernet header                       │
│ ┌───────────────────────────────────┐ │
│ │ IP header                         │ │
│ │ ┌───────────────────────────────┐ │ │
│ │ │ TCP header                    │ │ │
│ │ │ ┌───────────────────────────┐ │ │ │
│ │ │ │ Application data          │ │ │ │
│ │ │ └───────────────────────────┘ │ │ │
│ │ └───────────────────────────────┘ │ │
│ └───────────────────────────────────┘ │
└───────────────────────────────────────┘
```

Each layer adds information needed for its responsibilities. Ethernet helps deliver traffic over a local link.

IP provides addressing and forwarding across networks.

TCP provides a reliable, ordered byte stream between endpoints. HTTP gives the application data its meaning.

## 3.1 Why not send enormous packets?

Imagine a packet carrying 50 MB. What happens if a transmission error corrupts it?

What happens if a router needs to share a link among thousands of users? What happens if the next network segment cannot carry packets anywhere near that size?

Networks need manageable transmission units. A common Ethernet Maximum Transmission Unit, or **MTU**, is 1,500 bytes.

That number refers to the maximum payload carried by the Ethernet frame, typically an IP packet. It doesn't mean all 1,500 bytes are available for application data.

For a common IPv4/TCP configuration without additional options, headers consume at least 40 bytes, leaving roughly 1,460 bytes of TCP payload. Actual values depend on the network path, IP version, headers, and encapsulation.

Consequently, transmitting a 5 MB response requires many packets. The sender and transport machinery handle that division rather than forcing application developers to manually split every HTTP response.

## 3.2 IP addresses versus ports

Let's imagine your browser connects to:

```text
203.0.113.42:443
```

The IP address identifies the network destination.

The port identifies a transport endpoint at that destination. This lets one server expose multiple services:

```text
203.0.113.42:443    HTTPS
203.0.113.42:22     SSH
203.0.113.42:5432   PostgreSQL
```

These are conventional example assignments, not a recommendation to expose PostgreSQL publicly.

For a TCP connection, the combination of source and destination addresses and ports distinguishes the conversation. That allows thousands of simultaneous connections to coexist.

## 3.3 What is a socket?

A socket is an operating-system abstraction through which applications perform network communication. When a Node.js server executes:

```typescript
server.listen(3000);
```

it asks the runtime and operating system to establish a listening endpoint.

When a client connects, the operating system manages transport-level connection state, and the application receives events and data through that interface.

A listening socket is not the same as an established TCP connection. The server can accept many established connections through its listening endpoint.

This distinction matters when reasoning about connection limits, file descriptors, memory consumption, and server capacity. Thousands of active connections consume resources even if most are currently idle.

---

# 4. TCP: Reliability Is Not Free

IP provides packet delivery on a best-effort basis.

Packets may be delayed, dropped, duplicated, or reordered. TCP's purpose is to provide applications with a reliable, ordered byte stream despite those underlying uncertainties.

That sounds wonderful.

But reliability requires machinery. And machinery has costs.

## 4.1 Sequence numbers and acknowledgments

Imagine our application sends 4,000 bytes over TCP. For illustration, divide the data into four segments:

```text
Segment A: bytes    0–999
Segment B: bytes 1000–1999
Segment C: bytes 2000–2999
Segment D: bytes 3000–3999
```

These are relative byte positions for the example, not literal TCP initial sequence numbers.

Now suppose segment B disappears. The receiver obtains:

```text
A → C → D
```

TCP needs to reconstruct the original byte stream. It knows which byte ranges have arrived because data is tracked using sequence numbers.

The receiver can acknowledge the contiguous data it has received and indicate what comes next.

With TCP selective acknowledgment support, it can also inform the sender about later byte ranges received out of order.

The sender can then retransmit the missing information. Eventually, the receiving application sees:

```text
A → B → C → D
```

in the correct order.

This is powerful because the application does not ordinarily need to implement packet retransmission itself.

But consider what happened to latency. The missing segment couldn't be ignored, and recovery required additional network activity and time.

## 4.2 Detecting loss

TCP cannot simply assume a packet was lost because an acknowledgment hasn't arrived immediately. Perhaps the network is slow.

Perhaps the receiver delayed its acknowledgment. Perhaps packets took different routes.

TCP uses mechanisms including acknowledgment patterns and retransmission timers to infer loss.

Modern implementations can use sophisticated loss-detection methods rather than relying exclusively on a simple fixed timeout.

The distinction matters because different loss-recovery paths have very different latency costs.

If later data arrives and acknowledgment information reveals a gap, the sender may recover relatively quickly.

But if an isolated packet disappears and little subsequent traffic exists to reveal the problem, recovery may require waiting for a timer.

This explains a frustrating phenomenon: a tiny network loss can occasionally produce a disproportionately large delay.

## 4.3 Head-of-line blocking

TCP guarantees ordered delivery of application bytes. Suppose your HTTP/2 connection carries data for several independent requests.

If an earlier TCP byte range is missing, later bytes may be available inside the operating system but cannot yet be delivered in order to the HTTP/2 implementation. This holds even if some later bytes belong to a different HTTP/2 stream.

That is transport-level **head-of-line blocking**.

HTTP/3 addresses this particular limitation by using QUIC's independently ordered streams.

However, QUIC is still reliable for data that requires reliable delivery. Packet loss remains expensive, and congestion remains a problem.

HTTP/3 removes one particular form of blocking; it does not make unreliable networks reliable for free.

---

# 5. Flow Control: What If the Receiver Can't Keep Up?

Imagine a server capable of sending data at 800 Mbps.

Its client is a small device with limited memory and processing capacity. What happens if the server sends data much faster than the client can consume it?

Buffers fill. Without some form of regulation, data could be discarded or the receiver overwhelmed.

TCP solves this through **flow control**.

The receiver advertises how much additional data it is prepared to accept, represented through the TCP receive window. Suppose the receiver effectively tells the sender:

```text
I currently have room for another 64 KB.
```

The sender must respect that constraint. As the receiving application consumes data, buffer space becomes available, and the advertised window may grow.

The essential relationship is:

```text
Sender ─────────► Receiver
          Data

Sender ◄──────── Receiver
       ACK + available window
```

A slow application can therefore limit the rate at which its peer sends data.

This is important because performance bottlenecks do not always originate inside the network itself. Sometimes the receiving process simply isn't consuming incoming data quickly enough.

But there's another limitation, even when the receiver is extremely fast.

What if the network path itself cannot cope with the sender's transmission rate? That's a different problem.

---

# 6. Congestion Control: The Network Has No Infinite Waiting Room

Imagine a motorway with a capacity of 2,000 vehicles per hour.

If 1,500 vehicles arrive each hour, traffic flows comfortably. If 4,000 arrive, congestion develops.

Adding more cars doesn't make the motorway process them faster. It creates queues.

Computer networks face the same problem. A router might receive packets through several high-capacity links but need to forward them through a slower outgoing link.

Packets begin accumulating in its buffers.

If the queues fill, packets may be dropped. If queues become very long, latency increases.

TCP must avoid transmitting recklessly into congested network paths.

## 6.1 The congestion window

TCP's sender maintains a **congestion window**, usually abbreviated `cwnd`.

This limits how much data the sender may have in flight without acknowledgment, according to its congestion-control algorithm.

Importantly, the sender must respect both:

- The receiver's flow-control window.
- The congestion-control window.

A simplified model is:

```text
Allowed outstanding data
    ≈ min(receive window, congestion window)
```

Other constraints, including connection state and implementation behavior, also matter.

The distinction is fundamental.

**Flow control protects the receiver.**

**Congestion control protects the network path.**

An application developer who understands this difference is already thinking beyond the simplistic idea that network performance is determined exclusively by bandwidth.

## 6.2 Slow start: Learning how much the network can handle

When a TCP connection begins, the sender doesn't necessarily know the available network capacity. Sending a gigantic burst immediately would be dangerous.

So common congestion-control behavior begins with a relatively limited amount of data in flight.

As acknowledgments return successfully, the sender increases the amount of data it can transmit.

During classical TCP slow start, the congestion window can grow approximately exponentially across round trips.

A simplified illustration:

```text
Round trip 1:  10 segments
Round trip 2:  20 segments
Round trip 3:  40 segments
Round trip 4:  80 segments
```

These numbers are illustrative, not a universal initial-window requirement or exact prediction.

Despite the name, *slow start* can increase the sending rate quite rapidly.

But its growth is constrained by the need to receive acknowledgments, so a connection with high RTT requires more wall-clock time to complete the same number of growth rounds.

This is one reason short transfers can behave differently from long transfers.

A large download can eventually reach a high sustained rate. A tiny API request may finish before the connection ever approaches the available network capacity.

## 6.3 What happens when congestion appears?

A congestion controller needs signals that the network is becoming overloaded.

Historically, packet loss has been a primary signal. Modern systems may also use explicit congestion notification, delay measurements, or other signals depending on the algorithm.

A classical approach increases the sending window when transmission proceeds successfully and reduces it after congestion is detected. The algorithms have evolved considerably.

**CUBIC**, widely deployed in operating-system TCP stacks, uses a cubic growth function intended to perform well on high-bandwidth, long-distance networks.

**BBR**, developed by Google, takes a different modeling approach focused on estimating bottleneck bandwidth and round-trip propagation time.

Neither approach eliminates the fundamental need to share finite network resources.

They make different assumptions and trade-offs about throughput, delay, fairness, and congestion response.

For application developers, the critical lesson isn't memorizing the equations behind CUBIC.

It's realizing that **the transport dynamically controls how much data can be in flight, based on its understanding of the path**.

A fast network link doesn't guarantee the sender will immediately use all of its capacity.

---

# 7. The Bandwidth–Delay Product: A Beautiful Little Equation

We can now connect bandwidth, latency, and in-flight data. Imagine a water pipe.

The pipe has a certain capacity, but water takes time to travel from one end to the other. To keep the pipe fully utilized, some quantity of water must already be moving through it.

The same principle applies to networks. The **bandwidth–delay product**, or BDP, describes how much data can be in flight across a path at a given data rate and round-trip time.

The equation is:

\[
BDP = Bandwidth \times RTT
\]

Suppose we have:

```text
Bandwidth: 100 Mbps
RTT:       100 ms
```

Convert the bandwidth:

```text
100 Mbps = 12.5 MB/s
```

Multiply by the RTT:

```text
12.5 MB/s × 0.1 s = 1.25 MB
```

The result:

**Approximately 1.25 MB of data must be in flight to fully utilize that bandwidth under this simplified model.**

Now imagine the sender can keep only 64 KiB of unacknowledged data in flight.

Even if the physical link could deliver 100 Mbps, the effective transfer rate may be bounded approximately by:

\[
Throughput \lesssim \frac{Window}{RTT}
\]

Using our figures:

```text
65,536 bytes / 0.1 seconds

≈ 655,360 bytes/s

≈ 5.24 Mbps
```

That's a startling difference. We have a network capable of 100 Mbps, but the in-flight-data limitation yields an approximate ceiling near 5 Mbps.

The link isn't necessarily defective.

The server isn't necessarily overloaded. The relationship between the permitted in-flight data and the RTT is preventing full utilization.

Modern TCP implementations use window scaling and other mechanisms to avoid such severe limitations in ordinary configurations. But the general principle remains essential.

**High-bandwidth, high-latency paths require substantial data in flight to achieve high throughput.**

This helps explain why congestion-control behavior, buffer sizes, and RTT matter so much for long-distance transfers.

It also clarifies why a bandwidth upgrade may accomplish little when the true limitation lies elsewhere.

---

# 8. Bufferbloat: When More Buffering Makes the Internet Worse

Let's investigate one of the strangest network problems.

You have a decent home internet connection. When the network is idle:

```text
Ping: 15 ms
```

You start uploading a huge file to cloud storage.

Now your video call begins stuttering. You measure again:

```text
Ping: 450 ms
```

Yet the upload is transferring data successfully at a respectable rate.

What happened? One possible explanation is **bufferbloat**.

## 8.1 Why buffers exist

Network equipment needs buffers because packets do not always arrive at perfectly convenient times.

Suppose packets enter your router faster than your internet uplink can transmit them. The router can temporarily queue those packets rather than immediately discarding them.

Some buffering is useful. But imagine the buffer holds several seconds' worth of traffic.

A small interactive packet arriving behind a substantial queue must wait its turn. The link may be operating at its maximum throughput, but latency becomes terrible.

This illustrates a particularly important distinction:

**A fully utilized network link can deliver excellent throughput and terrible responsiveness simultaneously.**

The remedy isn't necessarily buying more bandwidth. Better queue management, fair scheduling, traffic shaping, or properly configured Smart Queue Management mechanisms such as FQ-CoDel or CAKE may be more directly relevant.

And application architecture matters too. A service that behaves well when RTT is 20 milliseconds may feel significantly worse when congestion pushes RTT above 400 milliseconds.

## 8.2 Jitter: Latency that refuses to behave consistently

Another important property is **jitter**, or variation in packet delay. Suppose network RTT measurements are:

```text
20 ms
21 ms
19 ms
24 ms
22 ms
```

That's relatively stable. Now consider:

```text
20 ms
380 ms
31 ms
170 ms
22 ms
```

The average isn't the most interesting feature. The variability is.

Real-time applications, including voice calls, video conferencing, multiplayer games, and interactive remote-control systems, can be especially sensitive to this.

But ordinary web applications are affected too. A sequence of requests may usually complete quickly and occasionally experience enormous delays.

From the user's perspective, the product becomes unpredictable. This is why measuring only average latency can conceal significant performance problems.

---

# 9. Packet Loss and the Long Tail

Suppose a network drops only 0.5% of packets. That sounds tiny.

Surely a 99.5% success rate should be excellent? Not necessarily.

First, a large transfer involves many packets. If a transfer sends 10,000 packets and losses were independent with a probability of 0.5%, the expected number of lost packets would be:

```text
10,000 × 0.005 = 50
```

Real packet losses are not necessarily independent; congestion can cause correlated bursts of loss.

But the example illustrates how small percentages become significant across many transmission opportunities.

Second, the real damage often comes from recovery behavior.

A lost packet might require retransmission, and congestion control may reduce the sending rate.

A small request that lacks enough subsequent traffic to reveal loss quickly might experience a noticeable timeout-related delay.

Consequently, occasional network loss can create large latency outliers. This leads to an important production-engineering concept.

## 9.1 Average latency isn't enough

Imagine your API reports:

```text
Average:  80 ms
p50:      45 ms
p95:     180 ms
p99:    1200 ms
```

The median user experience is excellent.

But one in every hundred requests takes roughly 1.2 seconds or longer. For a sufficiently popular service, that's a lot of unhappy interactions.

The situation becomes more serious when a single user action depends on many network operations.

Suppose a dashboard performs twenty independent requests and requires all twenty responses before it is considered ready.

Even if each request has only a 1% probability of being unusually slow, the probability that at least one of twenty requests experiences that slow outcome is approximately:

\[
1 - 0.99^{20} \approx 18.2\%
\]

This assumes independent events, which is a simplifying assumption. But the architectural lesson is real.

A user-facing operation that depends on many components can encounter a poor tail-latency experience even when each component looks reasonably healthy in isolation. This is why engineers examine p95, p99, dependency fan-out, timeouts, and critical paths.

It is also why indiscriminately splitting an application into dozens of synchronous microservices can create performance and reliability problems.

A distributed call may look cheap when viewed individually. An entire dependency graph can be expensive.

---

# 10. Diagnosing Networks Without Becoming a Network Engineer

We now have enough theory to conduct useful investigations.

There is no need to memorize every network protocol or become a router administrator.

For application engineering, the valuable skill is being able to narrow down the likely source of a delay.

Let's examine a few tools.

## 10.1 Ping: Is there a measurable round trip?

On Windows:

```powershell
ping -n 20 example.com
```

On Linux:

```bash
ping -c 20 example.com
```

Ping typically sends ICMP echo requests and measures the time until replies arrive. Useful observations include:

- Average RTT.
- Minimum and maximum RTT.
- Variation across samples.
- Reported packet loss.

But there is a trap. An ICMP ping isn't the same thing as an HTTPS request.

Some servers block ICMP entirely. Others rate-limit or deprioritize ICMP responses.

A failed ping does not necessarily indicate that the website is unreachable. And an excellent ping doesn't prove that the application is healthy.

Ping measures one particular kind of network exchange. Use it as evidence, not as a verdict.

## 10.2 Traceroute: Which path are packets taking?

On Windows:

```powershell
tracert -d example.com
```

On Linux, if installed:

```bash
traceroute example.com
```

Traceroute-style tools exploit the IP packet hop limit to discover intermediate network devices.

They can reveal a sequence of routers between your machine and the destination. You might see something like:

```text
1    1 ms     Home router
2    8 ms     ISP router
3   15 ms     Transit router
4   38 ms     Another network
5   41 ms     Destination
```

This is illustrative output.

The intriguing part is that the network route may be very different from what a geographical map suggests.

Traffic between two cities doesn't necessarily follow the shortest physical path.

Routing decisions depend on network topology, commercial relationships, availability, and routing policies.

### Don't misread intermediate hops

Suppose hop 7 reports:

```text
250 ms
```

but hop 8 reports:

```text
30 ms
```

It would be premature to conclude that hop 7 introduces 220 milliseconds of forwarding delay.

Routers may prioritize forwarding ordinary traffic over generating diagnostic ICMP responses.

Traceroute measures responses from individual devices, not the time each hop adds to a single traveling packet.

Likewise, missing replies can reflect filtering rather than actual packet loss affecting your application.

Traceroute is useful for investigating reachability and possible routing anomalies. It is not an automatic bottleneck detector.

## 10.3 Test the actual application connection

If you suspect HTTPS connectivity, test TCP port 443 directly. On Windows PowerShell:

```powershell
Test-NetConnection example.com -Port 443
```

This can help distinguish a basic TCP connection failure from higher-level application problems.

For HTTP-level information, curl is useful:

```bash
curl -v https://example.com
```

On Windows, `curl.exe` invokes the executable directly. To inspect timing on Windows:

```powershell
curl.exe -sS -o NUL -w "DNS=%{time_namelookup}s Connect=%{time_connect}s TLS=%{time_appconnect}s TTFB=%{time_starttransfer}s Total=%{time_total}s`n" https://example.com
```

The timing values are cumulative from the beginning of the transfer.

Comparing them can help identify where time is being spent. For example:

```text
DNS:      0.020 s
Connect:  0.110 s
TLS:      0.200 s
TTFB:     0.550 s
Total:    0.560 s
```

The initial DNS phase took approximately 20 milliseconds.

The TCP connection was established around 110 milliseconds from the beginning, and TLS setup completed around 200 milliseconds.

The first response byte arrived at 550 milliseconds, and the response finished at 560 milliseconds.

The large interval between TLS setup and TTFB deserves investigation.

But don't immediately blame application code. That interval includes the request traveling to the server, processing by intervening infrastructure, backend work, and the response traveling back.

## 10.4 A practical diagnostic sequence

When an API is unexpectedly slow, investigate in this order:

1. **Establish scope.** Is the problem specific to certain users, regions, operations, or time periods?
2. **Inspect client timing.** Separate DNS, connection, TLS, TTFB, and transfer phases where possible.
3. **Compare with server-side traces.** Determine how much time elapsed before the application began processing and after it completed.
4. **Check network behavior.** Look for elevated RTT, packet loss, unusual routing, or congestion under load.
5. **Investigate dependencies.** Identify sequential calls, external services, connection pool waits, and expensive fan-out.

These steps are not a rigid workflow.

They're a strategy for narrowing uncertainty. The crucial principle is to measure from multiple perspectives.

A browser knows when it sent and received data.

An application server knows when it began and completed its own work. Neither observer automatically knows everything that happened between them.

---

# 11. Practical Engineering Decisions

Let's turn the theory into architectural judgment.

## 11.1 Should you deploy closer to users?

Suppose a European SaaS product serves most of its customers from Frankfurt.

If your user base expands substantially into East Asia, latency may become noticeable. Deploying some infrastructure closer to those users could help.

But what would you actually move? Static assets are natural CDN candidates.

Read-heavy content may benefit from geographically distributed caches.

Application servers can sometimes be replicated across regions. Databases are more difficult because writes, consistency guarantees, and replication introduce their own constraints.

Moving a Node.js instance closer to the user may accomplish little if that instance must synchronously query a database thousands of kilometers away. You may merely relocate the long-distance network dependency.

**The location of the critical state matters as much as the location of the application process.**

## 11.2 Should you batch API requests?

Suppose a frontend needs twenty independent pieces of information.

One design makes twenty sequential requests. Another design provides an aggregate endpoint returning the necessary data in one response.

The aggregate endpoint may substantially reduce latency caused by repeated round trips.

But aggregation has costs. It can increase response size, reduce reuse of separately cacheable resources, couple unrelated features, and create overly broad API contracts.

Sometimes parallel requests are preferable.

Sometimes server-side aggregation is preferable. The engineering question isn't simply "how many requests are made?"

It's:

**Which requests are sequential, which can overlap, and what does the user actually need before the interface becomes useful?**

## 11.3 Should you add retries?

Retries are an important reliability mechanism. But they deserve caution.

Suppose the network is congested. Requests time out.

Every client immediately retries three times.

Now the overloaded system receives even more traffic. The recovery mechanism makes the failure worse.

Retries should account for failure type, timeouts, idempotency, request deadlines, backoff, jitter, and retry budgets.

A network timeout does not prove that the server failed to perform the operation.

For a payment or reservation API, blindly repeating a request can be dangerous unless the server provides appropriate idempotency guarantees. This subject will become especially important in our backend and distributed-systems course.

For now, keep the principle:

**A failed network conversation does not necessarily mean the remote operation never happened.**

---

# 12. The Oral Examination

We now have enough knowledge to examine networking like an engineer rather than merely recognize its vocabulary.

Before reading the solutions, try answering these questions out loud. Imagine that a senior engineer is interviewing you and will challenge any hand-waving.

### Challenge 1 — The 100 Mbps Trap

A service delivers a 1 KB JSON response over a 100 Mbps connection.

Users experience 180 ms latency. Your manager proposes upgrading the connection to 1 Gbps.

Would this plausibly deliver a tenfold improvement? Explain what you'd measure first.

### Challenge 2 — The Window Limitation

A TCP sender has an effective maximum of 128 KiB of outstanding data. The RTT is 80 milliseconds.

Ignoring other bottlenecks, what approximate throughput ceiling does that imply? Would a 1 Gbps link necessarily be fully utilized?

### Challenge 3 — The Mysterious Upload

A household has a fast fiber connection.

Video calls work perfectly until someone uploads a large file. The upload itself runs quickly, but video-call latency becomes terrible.

Identify a plausible network mechanism and an appropriate class of remedies.

### Challenge 4 — The Distributed Dashboard

A dashboard loads information from eight services sequentially.

Each service needs 10 ms of processing. The network RTT to each service is 70 ms.

Estimate the end-to-end time, ignoring connection establishment and other overhead. How would the answer change if the calls were independent and could run concurrently?

### Challenge 5 — The Payment Timeout

A client sends a payment request.

After two seconds, the request times out. The client receives no response.

Can it safely assume the payment failed? What must the architecture do to handle this correctly?

---

# 13. Solutions and Discussion

### Solution 1 — The 100 Mbps trap

No.

The serialization time of a 1 KB response is already extremely small at 100 Mbps. The observed 180 ms probably comes predominantly from RTT, connection establishment, backend processing, queues, or dependencies rather than the response's raw transmission time.

I would inspect browser or curl timings and compare them with server-side measurements before purchasing additional bandwidth.

### Solution 2 — The window limitation

Using:

```text
Throughput ≈ Window / RTT
```

we obtain:

```text
131,072 bytes / 0.08 seconds
= 1,638,400 bytes/second
≈ 13.1 Mbps
```

The sender would be limited to approximately 13.1 Mbps under this simplified window-bound model, even if the network could support far more. Additional bandwidth alone would not resolve that limitation.

### Solution 3 — The mysterious upload

Bufferbloat or excessive queueing on a saturated link is a plausible explanation. The large upload fills queues, delaying latency-sensitive traffic.

Appropriate remedies could include Smart Queue Management, fair queueing, traffic shaping, or reducing sustained uplink saturation. Merely adding larger buffers could make latency worse.

### Solution 4 — The distributed dashboard

Each sequential operation costs approximately:

```text
70 ms network RTT + 10 ms processing = 80 ms
```

Eight operations require:

```text
8 × 80 ms = 640 ms
```

If the requests are independent and can run concurrently, the elapsed time may approach the duration of the slowest individual operation:

```text
≈ 80 ms
```

Actual results depend on resource contention, scheduling, service behavior, and network conditions. This illustrates why the shape of a dependency graph can be more important than the performance of an individual service.

### Solution 5 — The payment timeout

No.

The server might have processed the payment successfully while the response was lost or delayed. The client cannot infer the business outcome solely from a network timeout.

A reliable payment workflow needs mechanisms such as idempotency keys, durable transaction state, and a way to retrieve or reconcile the authoritative payment status. The same principle applies to reservations, orders, and other consequential business operations.

---

# 14. The Mental Model Worth Keeping

There are five ideas that should fundamentally change how you think about networks.

**First:** Bandwidth and latency are different properties. A connection can transfer enormous quantities of data while remaining slow at individual round trips.

**Second:** Reliable transport requires acknowledgments, recovery, flow control, and congestion control. Those mechanisms affect performance.

**Third:** A network is a shared system with finite capacity. Queueing and congestion can create huge delays even while throughput remains high.

**Fourth:** The amount of data permitted in flight matters. Bandwidth, RTT, and transport windows interact in ways that can dramatically restrict throughput.

**Fifth:** Application architecture determines how much the underlying network characteristics hurt. Sequential dependencies, distant services, uncontrolled fan-out, and careless retries can turn ordinary network latency into a severe product problem.

For a senior software engineer, understanding networking isn't about configuring BGP routers. It's about recognizing when your application is fighting the physical and behavioral properties of the network—and designing systems that avoid unnecessary fights.

---

# 15. Next Lecture — HTTP: The Protocol That Runs the Web

Now that we understand the machinery transporting application data, it's time to investigate the protocol that gives those bytes meaning. Consider a simple request:

```http
GET /api/hotels/4812
```

It looks innocent. But why can that response be cached while another cannot?

Why does a browser sometimes receive `304 Not Modified` instead of the resource itself?

Why does a `POST` retry carry risks that a conventional `GET` retry generally doesn't? How can a server return `200 OK` while the application has actually failed?

And why do cookies, caching rules, content negotiation, and conditional requests make HTTP much more sophisticated than a simple request-response convention?

In **CS230-L03**, we'll investigate HTTP as an engineering protocol rather than merely the syntax used by REST APIs.

---

## Optional Practical Lab — An Evening with Your Own Network

*The spoken lecture ends here. The remaining material is a screen-first investigation worksheet and technical references.*

Here's a compact experiment you can perform on your PC. It requires no infrastructure setup.

### Lab A — Measure idle latency

Open a terminal and run a series of pings to a reachable destination. On Windows:

```powershell
ping -n 30 1.1.1.1
```

Record the minimum, average, and maximum RTT.

This is a connectivity test to a public resolver address, not a guarantee of comparable performance to your application server.

### Lab B — Measure latency under load

Start a substantial upload or an upload-capable speed test. While the upload is running, repeat the ping test and compare the results.

If latency increases dramatically, you may be observing queueing delay somewhere along the active path. The experiment alone doesn't prove bufferbloat or identify which device is responsible, but it gives you a useful clue.

Avoid performing this test while someone else depends on your connection for an important call.

### Lab C — Compare distant destinations

Choose a few reachable public destinations in different regions. Use ping, curl, or application-level timing tools as appropriate, and look for the relationship between geography and RTT.

Remember that CDN services may route you to nearby infrastructure even when a company's headquarters are far away.

### Lab D — Inspect a real web application

Open Chrome DevTools.

Find a page that initiates several API requests. Determine whether those requests execute sequentially or overlap.

Ask yourself:

If the RTT doubled, which operations would become slower?

Would the application suffer approximately one additional RTT? Or would several dependent requests compound the delay?

That question connects this networking lecture directly to frontend architecture.

### Lab E — Explain your observations

Write or speak a short diagnosis covering:

1. Idle RTT versus RTT under upload load.
2. How geography related to measured delay.
3. Whether the web app's API calls were sequential or concurrent.
4. What would happen if RTT doubled for that dependency graph.
5. Whether bandwidth alone would have fixed the pain you observed.

The objective is to practice separating throughput from conversation latency, and network physics from application shape.

---

## Further Reading — Optional Technical References

1. [RFC 9293 — Transmission Control Protocol](https://www.rfc-editor.org/rfc/rfc9293.html) — TCP fundamentals, sequencing, acknowledgments, and flow control.
2. [RFC 9438 — CUBIC](https://www.rfc-editor.org/rfc/rfc9438.html) — Modern TCP congestion control on high-speed networks.
3. [RFC 9002 — QUIC Loss Detection and Congestion Control](https://www.rfc-editor.org/rfc/rfc9002.html) — How QUIC handles loss and congestion.
4. [Microsoft — Tracert](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tracert) — Practical network-path investigation.

