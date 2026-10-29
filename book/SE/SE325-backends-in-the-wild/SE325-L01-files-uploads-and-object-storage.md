---
id: SE325-L01
course: SE325
title: "Files, Uploads, and Object Storage"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE325-L02
---

# SE325 — Backends in the Wild: Production Field Guide
## Lecture 01: Files, Uploads, and Object Storage

*Your API has accepted JSON requests for years. Then a supplier uploads a four-gigabyte archive. The request times out, the container runs out of temporary storage, and the customer tries again. Six hours later, the storage bill is growing, but nobody knows whether the upload succeeded.*

---

# Part I — Intuition

## 1. The File That Was Bigger Than the Application Expected

Imagine you're working on Mercury, a hotel-booking platform.

Your backend handles reservation requests, customer profiles, payments, and hotel information.

Most requests are small.

A customer updates their telephone number. The browser sends a few hundred bytes of JSON.

A reservation service receives a booking request. The payload contains a few identifiers, dates, and customer details.

Your Node.js application reads these requests, validates them, performs the appropriate operation, and returns a response.

Everything is reasonably predictable.

Now a supplier asks for a feature.

They maintain thousands of properties and want to upload an archive containing photographs, documents, and hotel metadata.

The archive is four gigabytes.

One developer suggests adding an upload endpoint and saving the file.

That sounds straightforward.

After all, the application already receives HTTP requests.

What's special about receiving a larger request body?

Quite a lot, as it turns out.

A four-gigabyte file isn't simply a bigger version of a one-kilobyte JSON document.

The file may arrive over several minutes.

The connection may disappear halfway through.

The client may retry after an uncertain failure.

The server may run out of memory or temporary disk space.

The reverse proxy may impose a request-size limit.

The file may contain malicious content.

The upload may finish successfully even though the client never receives the acknowledgment.

And the company needs a policy for how long to retain the uploaded material.

**Large files turn request handling into a resource-management and lifecycle problem.**

## 2. The First Mistake: Treating the File as One Giant Value

Suppose the developer writes an endpoint that reads the entire request body into memory.

For small JSON requests, this is ordinary behavior.

But a four-gigabyte upload is different.

If the application attempts to hold the entire file in RAM, one request may consume more memory than the container has available.

Now imagine five suppliers uploading large archives simultaneously.

Even a server with substantial memory may become overloaded.

The important distinction is between *buffering* and *streaming*.

Buffering means accumulating data before processing it.

Streaming means processing data incrementally as it arrives.

Imagine filling a swimming pool.

You wouldn't normally collect all the water in a giant bucket before pouring it into the pool.

You would connect a hose.

The water moves through a bounded channel.

For files, that channel might transfer data in small chunks from the incoming HTTP connection to storage.

### Visual anchor 1 — Buffering versus streaming

```text id="ulv4p2"
BUFFERING

4 GB request
     |
     v
Application memory: 4 GB
     |
     v
Storage


STREAMING

4 GB request
     |
     v
Small bounded buffer
     |
     v
Storage

Repeat until complete.
```

Streaming doesn't make the four gigabytes disappear.

The system still transfers and stores the data.

But it avoids holding the entire object in memory simultaneously.

That's a fundamental improvement.

## 3. The Second Mistake: Sending Everything Through the API

Now consider the network path.

The supplier's browser sends four gigabytes to your API.

Your API then uploads those same four gigabytes to cloud storage.

The application server has become an intermediary for an enormous amount of data.

It receives every byte.

Then it sends every byte elsewhere.

Sometimes that's appropriate.

Perhaps the backend must process the data as it arrives.

Perhaps the security architecture requires all uploads to pass through a controlled gateway.

But often, the backend doesn't need to handle the bytes directly.

It needs to decide whether the supplier is authorized to upload a file and where the file should be stored.

Those are control decisions.

The actual transfer can follow a different path.

## 4. Presigned URLs: Let the Browser Talk to Storage

Imagine the following workflow.

The supplier asks Mercury's API for permission to upload an archive.

The backend authenticates the supplier, checks their tenant, validates the requested file size and type against policy, and creates an upload record.

Then it generates a temporary upload URL for object storage.

The supplier uses that URL to send the file directly to storage.

The API doesn't carry the entire payload.

It handles authorization and the upload's business lifecycle.

### Visual anchor 2 — Control path versus data path

```text id="ld72py"
Supplier's browser
        |
        | Request upload permission
        v
   Mercury API
        |
        | Return temporary upload capability
        v
Supplier's browser
        |
        | Transfer file bytes
        v
   Object storage
        |
        | Completion verification
        v
   Mercury API
```

With Amazon S3, this temporary capability is commonly a **presigned URL**.

The URL authorizes a particular storage operation under the permissions of the identity that generated it.

The browser doesn't need AWS credentials.

But the URL itself is sensitive.

Anyone possessing a valid upload URL may be able to use it within its permitted scope and lifetime.

A presigned URL is not automatically single-use.

Nor does it automatically enforce every application-level rule you might want.

Your backend still needs an upload lifecycle and authoritative verification.

## 5. Object Storage Is Not a Remote Folder

We should clarify something.

What exactly is object storage?

Imagine storing a hotel photograph.

In a traditional filesystem, you think about directories and files.

In S3, you work primarily with buckets and objects.

An object has a key, content, and associated metadata.

For example, the application might store an object under a key resembling:

`properties/482/images/cover-2026.jpg`

That key looks like a filesystem path.

But S3 is an object-storage API, not a conventional shared POSIX filesystem.

Objects are retrieved and managed through storage operations.

You don't normally open an S3 object as though it were an ordinary file on your application's local disk and append a few bytes to it.

For large files, you use the storage system's upload mechanisms.

This difference explains why cloud object storage is particularly useful for photographs, documents, archives, and generated exports.

Those objects can remain available independently of the application containers that created them.

## 6. Uploading Is Not the Same as Publishing

Suppose a supplier uploads an archive successfully.

Should Mercury immediately make its contents available to customers?

Not necessarily.

The archive might contain unexpected file types, malicious content, incorrect metadata, or images that require processing.

The upload has completed.

But the object hasn't yet been approved for use.

This suggests several states:

The upload was requested.

The file is being transferred.

The bytes have arrived.

The object is awaiting verification.

The object has been accepted.

The object has been rejected.

Or the upload has expired or been abandoned.

### Visual anchor 3 — A file has a lifecycle

```text id="tfaq9k"
REQUESTED
    |
    v
UPLOADING
    |
    v
QUARANTINED
    |
    +----> REJECTED
    |
    v
AVAILABLE
    |
    v
DELETED / RETAINED
```

The states matter because other parts of the application must not confuse them.

For example, a customer's identity document should not be treated as accepted merely because an HTTP upload returned success.

A hotel photograph shouldn't become publicly accessible before the required checks are complete.

**Receiving bytes is a transport success. Accepting the file is a business decision.**

## 7. The Third Mistake: Forgetting Incomplete Uploads

Now imagine that the supplier begins transferring the four-gigabyte archive.

The first three gigabytes arrive.

Then the laptop loses connectivity.

The browser reports an error.

The supplier tries again the next morning.

What happened to the original three gigabytes?

That depends on the upload architecture.

In Amazon S3 multipart upload, the uploaded parts can remain stored even though the complete object was never created.

Those incomplete parts can consume billable storage until the multipart upload is completed or aborted.

The supplier may never see a completed file.

The application database may contain only a pending upload record.

Yet the storage system may still be retaining gigabytes of unfinished data.

This isn't merely a failed request.

It's an abandoned resource.

A reliable file subsystem needs cleanup.

## 8. A File Upload Has Several Meanings of Success

Imagine a browser reporting that an upload failed.

There are several possibilities.

The server may not have received the file.

The object storage service may have received all the bytes but failed during finalization.

The object may have been finalized, but the network connection may have disappeared before the acknowledgment reached the browser.

The application may have finalized the object but failed to update its database record.

The object may be stored correctly but awaiting security validation.

These are different outcomes.

A well-designed upload process gives each logical upload an identity.

The client can ask:

"What happened to upload 482?"

The backend checks the authoritative upload record and relevant storage state.

That is better than treating every lost HTTP response as proof that the upload failed.

## 9. Why Files Deserve Their Own Engineering Discipline

We've identified several distinct problems.

Large payloads require bounded memory and suitable transfer paths.

Uploads can be interrupted.

Temporary storage must be cleaned up.

Files need validation.

Authorization must apply to both uploads and downloads.

Storage objects and database records can disagree.

And successful transfer isn't necessarily successful acceptance.

This is why file handling deserves more attention than a simple `POST /upload` tutorial.

The individual operations may be straightforward.

The lifecycle connecting them is where production systems become complicated.

### A tiny comprehension check

A four-gigabyte request reaches a Node.js server configured to buffer the entire body. What is the first architectural concern?

Memory and resource exhaustion.

Now suppose the browser uploads directly to S3 using a presigned URL. Does that eliminate the application's need to authenticate the supplier?

No. The application must decide whether to issue the upload capability and what it authorizes.

Finally, a multipart upload has stored three gigabytes of parts but has never been completed. Is there necessarily a three-gigabyte object available for download?

No. Incomplete multipart parts are not the same thing as a completed object.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 10. Files Have Different Performance Characteristics from Ordinary API Data

An ordinary JSON endpoint often receives a small payload and completes in milliseconds.

A file-transfer endpoint may operate for minutes, consume substantial bandwidth, and depend on the client's network stability.

That changes its failure characteristics.

### 10.1 Large requests occupy resources for longer

A lengthy upload may hold a network connection, file descriptor, request-handling context, and some application resources for its duration.

If the application writes to temporary storage, it also consumes disk space.

Even when memory usage is bounded, large transfers can place pressure on connection limits, network throughput, and storage I/O.

### 10.2 Reverse proxies and gateways matter

The request may pass through a CDN, load balancer, API gateway, reverse proxy, and application server.

Any of these components may enforce body-size limits or timeouts.

A backend capable of accepting a large file is not sufficient if an upstream gateway rejects it first.

When diagnosing a failed upload, identify the complete request path.

### 10.3 The client is part of the failure model

Browsers, mobile devices, and supplier systems may lose connectivity.

A laptop can sleep.

A user can close a tab.

A corporate network can terminate a long connection.

Large-transfer protocols should expect interruption rather than treat it as an exceptional impossibility.

## 11. Streaming: Keep Memory Bounded

Streaming is a way to process data incrementally rather than accumulating the entire input.

In Node.js, an incoming HTTP request exposes a readable stream.

A storage destination can expose a writable stream.

The application can connect them through an appropriate pipeline.

### 11.1 Backpressure

Suppose the client sends data faster than storage can write it.

Without flow control, the application may accumulate data in memory.

Backpressure allows the slower destination to regulate how quickly the upstream source supplies more data.

Node.js stream pipelines provide useful mechanisms for propagating backpressure and handling errors.

### 11.2 Streaming doesn't eliminate every temporary buffer

A streaming implementation still uses buffers.

It may also use temporary files, multipart parsers, network buffers, and storage SDK internals.

The relevant guarantee is bounded memory consumption under the expected workload—not literal zero buffering.

### 11.3 Beware accidental buffering

A common mistake is to begin with a streaming request and then call a helper that accumulates every chunk into one buffer.

The application appears to use streams.

But the memory behavior is still proportional to the entire file size.

Inspect the actual data path.

If a framework's upload middleware stores files in memory, that configuration may be inappropriate for multi-gigabyte uploads.

### 11.4 Enforce size limits while reading

A client-provided `Content-Length` can be useful for rejecting obviously oversized requests early.

But it is not a sufficient security boundary.

The application must enforce byte limits according to the actual received data and supported transfer semantics.

A malicious or malfunctioning client should not be able to bypass the application policy by lying about a header.

## 12. Three Upload Architectures

There are three broadly useful patterns.

### 12.1 Backend-proxied upload

The client uploads to the application server.

The backend authenticates, validates, and streams the bytes to storage.

This centralizes control.

It may simplify some security and processing requirements.

But the application fleet carries the full data-transfer workload.

For very large objects, this can become expensive.

### 12.2 Direct-to-object-storage upload

The client requests an upload capability from the backend.

The backend validates the request and generates a constrained presigned URL or equivalent mechanism.

The client uploads directly to object storage.

The backend later verifies completion and finalizes the business record.

This can significantly reduce application-server bandwidth and long-running request pressure.

But it introduces a multi-step lifecycle.

### 12.3 Multipart or resumable upload

A large file is divided into parts.

Parts can be uploaded independently.

Failed parts can be retried without retransmitting the entire file, subject to the protocol and session state.

The storage service combines or finalizes the parts after all required pieces are present.

This is particularly useful for large files and unreliable networks.

### Choosing deliberately

A small profile image may not need an elaborate resumable-upload protocol.

A multi-gigabyte supplier archive often does.

The architecture should match the file size, expected concurrency, security requirements, and client environment.

## 13. Presigned URLs Are Capabilities

An S3 presigned URL gives its holder permission to perform a particular storage operation under the authority of the principal that created it.

It can authorize an upload or download without distributing AWS credentials to the client.

But several subtleties matter.

### 13.1 A URL isn't necessarily single-use

An ordinary presigned PUT URL can be used more than once while valid.

If the key already exists, another successful PUT may replace the object unless additional protections prevent it.

Therefore, don't treat an ordinary presigned URL as a one-time business transaction token.

### 13.2 Use server-generated object keys

Do not allow customers to choose arbitrary bucket keys that might overwrite other tenants' objects.

A safer design assigns an opaque, unpredictable object key to each upload.

The key can contain a tenant-specific namespace, but the authoritative tenant identity must come from authenticated server-side context.

### 13.3 Limit the scope

The generated capability should target only the intended operation and storage location.

Use short expirations appropriate for the transfer.

Where needed, sign relevant request headers and use supported policy conditions to constrain uploads.

A presigned POST policy can enforce conditions such as content-length ranges; ordinary presigned PUT arrangements require their own carefully designed enforcement.

### 13.4 URL expiry and credential expiry differ

The URL's usable lifetime depends on its configured expiration and the underlying credentials.

Temporary credentials may expire before the nominal URL expiration.

For long-running multipart uploads, individual part URLs may need renewal.

A new URL should not require restarting the whole logical upload when the session remains valid.

### 13.5 Browser CORS is another requirement

A browser directly uploading to S3 may need suitable CORS configuration.

CORS controls which cross-origin browser operations are allowed.

It is not a substitute for storage authorization.

A correctly configured CORS policy doesn't make an unauthorized upload legitimate.

### 13.6 A signed URL is sensitive

A valid presigned URL is a bearer capability.

Avoid exposing it in unnecessary logs, analytics, support tickets, or browser-accessible third-party instrumentation.

Someone who obtains the URL may be able to exercise its permitted operation until it expires or the underlying authorization ceases to apply.

## 14. The Upload Record: Your Application's Source of Workflow Truth

Suppose Mercury generates a presigned upload URL.

What should it store in PostgreSQL?

Not the file bytes.

It should store the metadata necessary to manage the upload.

A conceptual record might contain:

Upload ID.

Tenant ID.

Authenticated owner.

Object key.

Expected size.

Expected content type.

Expected checksum, if provided.

Creation and expiration timestamps.

Current lifecycle status.

Storage upload ID for multipart transfers.

Final object identity or version.

Validation result.

### 14.1 Separate intent from observation

A client declares that it intends to upload a six-gigabyte file.

That declaration isn't proof that six gigabytes arrived.

A successful storage operation establishes something different.

The backend should compare the received object's size and integrity information against the agreed upload requirements.

### 14.2 Use explicit states

A useful model might include:

`REQUESTED`

`UPLOADING`

`QUARANTINED`

`AVAILABLE`

`REJECTED`

`ABORTED`

`EXPIRED`

The exact state names are less important than their meaning.

For example, `QUARANTINED` means the bytes exist but are not yet available for ordinary use.

### 14.3 Make transitions controlled

An upload shouldn't jump directly from `REQUESTED` to `AVAILABLE` merely because a client says it finished.

The server should verify the object and required checks.

State transitions should also be safe under repeated requests and concurrent callbacks.

## 15. S3 Multipart Upload: What Actually Happens

Amazon S3 has a multipart-upload API for large objects.

The important operations are initiation, part upload, completion, and abort.

### 15.1 Initiation

The application initiates a multipart upload for a particular bucket and object key.

S3 returns an upload ID.

That ID identifies the unfinished upload session.

The application must retain it for future part operations and cleanup.

### 15.2 Uploading parts

The client uploads numbered parts.

Each part can be transferred separately.

S3 associates the uploaded data with the upload ID and part number.

The client records the necessary part information, including ETags and any required checksum values.

### 15.3 Completion

Once all required parts have arrived, the application or authorized client sends the completion request.

S3 assembles the parts into the final object.

Only then is the multipart upload completed.

A partially uploaded session is not a normal downloadable object.

### 15.4 Aborting

If the upload is abandoned, an abort operation tells S3 to stop the multipart upload and free its stored parts.

Aborting while part requests remain in flight can require additional verification or repeated cleanup.

### 15.5 Part-size constraints

S3 imposes multipart-upload limits, including a maximum of ten thousand parts per upload.

For ordinary S3 multipart uploads, parts other than the final part must generally be at least five mebibytes.

An application must choose an appropriate part size for the expected object size.

For example, a four-gigabyte file divided into sixty-four-mebibyte parts requires approximately sixty-four parts.

Those parts can potentially be uploaded in parallel, within reasonable resource and service limits.

## 16. Resumability Is a State-Management Problem

Splitting a file into parts is only the beginning.

Suppose the client uploads forty of sixty-four parts and disconnects.

The next morning it resumes.

How does it know which parts succeeded?

The client may have its own local checkpoint.

The server may maintain upload-session metadata.

The storage service may provide a list of uploaded parts.

These records must be reconciled.

### 16.1 A timeout doesn't prove failure

A client may time out after S3 stored a part successfully.

Blindly assuming the part failed can cause unnecessary retransmission.

Re-uploading the same S3 part number replaces that part within the multipart session.

This can support recovery, but the application must still ensure the uploaded data and checksums correspond to the intended file.

### 16.2 A stable upload identity matters

The upload ID should identify one logical transfer.

A client retrying a failed HTTP call shouldn't automatically initiate a completely new multipart upload.

Otherwise one interrupted file can create several abandoned upload sessions.

### 16.3 Don't let two clients finalize differently

Suppose the user opens two browser tabs and resumes the same upload.

Both attempt to finalize it.

The application should coordinate the logical upload state and avoid conflicting outcomes.

For example, a database conditional update can help ensure one finalization decision becomes authoritative.

### 16.4 Completion isn't always the end

After S3 completes the multipart upload, the application may still need to update its database record and run validation.

A reliable process must handle the gap between storage completion and application finalization.

## 17. Integrity: Did We Receive the Intended Bytes?

A file can have the expected size but contain incorrect data.

A client might upload the wrong file.

A transfer might fail in an unexpected way.

A malicious client may misrepresent the content.

Checksums provide useful evidence about the bytes.

### 17.1 SHA-256 as a content identity

The client can calculate a SHA-256 digest of the intended file.

The backend can compare it with a verified digest of the stored object.

For large files, hashing can be performed incrementally rather than loading the whole file into memory.

### 17.2 S3 ETags are not universal MD5 checksums

An important trap is treating an S3 object's ETag as the MD5 digest of its entire contents.

That is not generally correct.

Multipart uploads and certain encryption arrangements produce ETags that are not the full-object MD5 digest.

Use explicit supported checksum mechanisms when integrity verification requires a known checksum algorithm.

### 17.3 Integrity and authorization answer different questions

A checksum proves correspondence between bytes and a digest.

It doesn't prove that the uploader was authorized.

It doesn't prove that the file is harmless.

It doesn't prove that the contents represent truthful business information.

These are separate checks.

## 18. File Validation Is a Security Boundary

Suppose a guest uploads a document named `passport.pdf`.

The filename is user-controlled.

The `Content-Type` header is also supplied by the client.

Neither should be trusted as authoritative evidence that the file is a valid PDF.

### 18.1 Extension and type allowlists

An application should define which file types are permitted for the particular workflow.

A profile-image endpoint may accept selected image formats.

An identity-document endpoint may accept a narrower set of document formats.

Validation should check the actual bytes and structure where appropriate.

### 18.2 File signatures

Many formats have recognizable signatures or magic bytes.

These can help identify obviously mismatched content.

But a valid signature isn't sufficient proof that the entire file is safe or well-formed.

A malicious file may still have a plausible signature.

### 18.3 Security scanning

Depending on the risk, uploaded content may need malware scanning, sandboxed parsing, or other validation before being made available.

This can be asynchronous.

The upload enters quarantine.

A worker inspects the content.

Only an accepted result transitions the object to an available state.

### 18.4 Archive bombs

A compressed archive can be small relative to the enormous amount of data it expands into.

An archive-processing worker needs limits on expanded size, file count, nesting depth, CPU time, memory, and filesystem operations.

Limiting the uploaded archive to a small number of bytes doesn't automatically prevent decompression-related resource exhaustion.

### 18.5 Image processing

Even images can exercise complex parsers.

If the application generates thumbnails or rewrites images, use maintained libraries and suitable resource limits.

Decoding and re-encoding an image may reduce some risks but is not a universal malware-removal mechanism.

## 19. Original Filenames Are Display Data, Not Storage Paths

Suppose a supplier uploads a file whose name contains path separators or unusual characters.

If the backend uses the supplied filename directly in a filesystem path, it may create path traversal or overwrite risks.

A safer design generates its own storage key.

The original name can be retained separately as display metadata after appropriate validation and normalization.

### 19.1 Object keys and tenant isolation

An object key might include a tenant namespace.

But a prefix alone is not sufficient security.

The application must verify that the requesting user is authorized to access the referenced object.

A customer should not be able to download another customer's document simply by guessing its key.

### 19.2 Avoid exposing raw storage paths as authority

A download endpoint should accept an application-level object identifier and resolve the corresponding authorized storage key.

Do not let clients freely choose arbitrary bucket names and keys for privileged server-side downloads.

## 20. Downloads Have Their Own Architecture

We often focus on uploads, but large downloads create many of the same concerns.

A supplier may download a generated hotel archive.

A customer may retrieve an invoice.

An internal administrator may export thousands of records.

### 20.1 Backend-proxied downloads

The application can authenticate the requester and stream the file from storage.

This gives the backend control over the response.

But it also carries the full data-transfer workload.

### 20.2 Presigned download URLs

The backend can authorize the requester and generate a temporary download URL.

The client then retrieves the object directly from storage.

This reduces application-server transfer pressure.

But the signed URL is a sensitive capability and must have an appropriate scope and lifetime.

### 20.3 Streaming responses

If the backend proxies a download, it should generally stream large objects rather than load them completely into memory.

The same bounded-memory principle applies in both directions.

### 20.4 Range requests

HTTP supports byte-range requests.

Object storage systems such as S3 support retrieving specified byte ranges.

This can be useful for resuming interrupted downloads and for applications that need only part of an object.

A production download service should understand when it supports ranges and how those requests interact with authorization and caching.

### 20.5 Response headers matter

The server should provide suitable `Content-Type` and `Content-Disposition` behavior.

For sensitive or untrusted documents, forcing attachment download may be safer than allowing arbitrary browser rendering.

The correct policy depends on the content type and use case.

## 21. The Object Store and Database Do Not Share One Transaction

Imagine that a supplier successfully uploads an archive to S3.

The application then attempts to create its metadata record in PostgreSQL.

The database write fails.

The object exists, but the application doesn't know about it.

Now reverse the sequence.

The backend creates a metadata record first.

Then the upload fails.

The database contains a pending file record with no completed object.

These are common cross-system inconsistencies.

### 21.1 Choose an authoritative workflow record

A robust design often creates an upload session before allowing bytes to be transferred.

The session tracks the expected object and lifecycle.

The object may be present before the application marks it available.

That is acceptable if the system has a clear recovery process.

### 21.2 Verify rather than trust the client

A client may call a completion endpoint and claim success.

The backend should verify the relevant object through authoritative storage APIs.

For S3, a `HEAD` operation can retrieve object metadata without downloading the full object.

S3 provides strong read-after-write consistency for completed object PUTs and related object metadata operations.

This means the application doesn't need to assume that a successfully completed S3 object will remain invisible for an arbitrary eventual-consistency interval.

But strong object-store consistency doesn't make the S3 operation and PostgreSQL metadata update one atomic transaction.

### 21.3 Reconciliation

The application can periodically compare pending upload records with storage observations.

It can determine whether an upload completed, remains unfinished, expired, or requires manual investigation.

A reconciliation process must distinguish uncertainty from failure.

## 22. Storage Events Aren't Exactly-Once Business Events

Object storage can publish notifications when objects are created.

For example, S3 can notify a downstream service that an object was created.

This can trigger a validation worker.

But event delivery has its own semantics.

Amazon S3 event notifications are designed for at-least-once delivery and may arrive out of order.

### 22.1 Duplicate validation

A worker may receive the same object-created event more than once.

Validation should therefore be idempotent or otherwise safe under duplicate delivery.

### 22.2 Ordering

An object may be overwritten or replaced.

Notifications associated with different object versions may not arrive in the order the application expects.

A consumer should use appropriate object identity, version information, or another ordering mechanism rather than blindly allowing an old event to change the current state.

### 22.3 Don't publish a file before validation

A storage event can mean the bytes exist.

It doesn't mean they passed security and business checks.

The application should maintain a distinct acceptance state.

## 23. Orphaned Objects and Incomplete Multipart Sessions

A long-lived file subsystem inevitably accumulates abandoned work unless it actively manages cleanup.

There are two different categories.

**Incomplete multipart parts:** Data stored within an upload session that has not been finalized.

**Orphaned completed objects:** Ordinary stored objects that no longer correspond to a valid application record or retention requirement.

These require different cleanup mechanisms.

### 23.1 Incomplete multipart cleanup

S3 supports lifecycle rules that abort multipart uploads remaining incomplete beyond a configured age.

This is an important cost-control mechanism.

The application may also explicitly abort uploads that users cancel or that expire.

### 23.2 Completed-object cleanup

A completed object won't be removed merely because a multipart-abort lifecycle rule exists.

An orphaned object needs a separate retention and reconciliation policy.

### 23.3 Avoid deleting active work

Suppose a cleanup job runs at midnight.

It sees an upload session created yesterday.

But the supplier is still uploading a large archive over a slow connection.

Deleting the session immediately would interrupt legitimate work.

A safe cleanup process needs a defined expiration policy and suitable coordination with active transfers.

A heartbeat or last-activity timestamp may help, but the system must decide what activity counts and how to handle stalled sessions.

### 23.4 Cleanup is part of correctness

Storage cleanup isn't only about saving money.

Unnecessary retained identity documents may create privacy and compliance risks.

Expired temporary download artifacts may expose stale sensitive information.

The data lifecycle must reflect the application's actual retention requirements.

## 24. The Storage Cost Model

Cloud object storage can be inexpensive per gigabyte compared with operating dedicated file servers.

But total cost depends on more than stored bytes.

Important dimensions may include:

Stored capacity.

Upload and download requests.

Data transfer and egress.

Replication.

Lifecycle transitions.

Retention requirements.

Processing and scanning costs.

### 24.1 Retry waste

Suppose a supplier repeatedly uploads a four-gigabyte archive because the client cannot determine whether earlier attempts succeeded.

Each unnecessary retry consumes network capacity and may create additional storage operations.

The application may accumulate multiple completed or incomplete copies.

A resumable protocol and reliable status endpoint can reduce that waste.

### 24.2 The expensive orphan

Imagine ten thousand interrupted uploads, each leaving several gigabytes of unfinished parts.

Even if no completed objects appear in the ordinary file listing, the retained parts can create significant storage cost.

This is why incomplete multipart sessions require direct monitoring.

### 24.3 Tenant quotas

A multi-tenant platform should consider whether one supplier can upload unlimited data.

Per-tenant size limits, concurrency limits, retention policies, and storage quotas help prevent one customer's workload from exhausting shared resources.

The quotas must align with legitimate business use.

## 25. The Production Incident: Four Gigabytes, No Confirmation

Let's reconstruct the opening incident.

A supplier initiates a four-gigabyte archive upload.

The backend accepts the request.

The transfer begins.

The application buffers too much data and experiences memory pressure.

The client connection eventually times out.

The supplier retries.

A second upload session begins.

The original multipart parts remain stored.

The application database contains several pending records.

Support cannot determine which transfer completed.

The storage bill begins growing.

What failed?

Not just the HTTP request.

The system lacked a reliable large-object transfer architecture and lifecycle.

### 25.1 Immediate containment

Prevent additional uncontrolled retries and excessive concurrent uploads.

Inspect the active and incomplete upload sessions.

Identify whether completed objects exist.

Preserve legitimate supplier data while determining which sessions are recoverable.

### 25.2 Architecture correction

For suitable clients, use direct-to-object-storage multipart uploads with server-issued capabilities.

Maintain an application upload session with an explicit identity.

Support resuming interrupted transfers.

Verify object completion and integrity.

Keep uploaded content quarantined until accepted.

### 25.3 Cleanup

Abort abandoned incomplete multipart uploads after an appropriate retention period.

Use lifecycle rules as an additional safety mechanism.

Reconcile completed objects against application metadata.

### 25.4 Verification

Measure upload success, failed transfers, resume rates, incomplete-part storage, orphaned objects, memory usage, and validation outcomes.

A successful fix should improve both customer experience and resource behavior.

## 26. A Production-Ready File Lifecycle

A defensible design might look like this.

First, the authenticated supplier requests a new upload session.

The backend verifies permissions, file policy, size limits, and tenant quotas.

It creates a durable upload record and assigns an opaque object key.

For a large file, the backend initiates a multipart upload and supplies appropriate part-upload capabilities.

The supplier transfers the parts.

After completion, the backend verifies that the expected object exists and that size and integrity checks satisfy the upload contract.

The upload record moves to quarantine.

A validation worker inspects the object.

Accepted content becomes available to the intended users.

Rejected content is recorded and handled under the applicable retention policy.

Abandoned sessions are eventually aborted and cleaned up.

Completed objects with invalid or missing metadata are reconciled.

Downloads require a fresh authorization decision.

This system isn't conceptually complicated because it has many classes or services.

It's complicated because **the transfer, storage, validation, and business acceptance occur across separate failure boundaries**.

Once those boundaries are explicit, the design becomes much easier to reason about.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Four-Gigabyte Request

An API endpoint buffers a four-gigabyte upload into memory.

What are the immediate risks?

How does streaming change the resource model?

## Question 2 — Direct Upload

Why might a backend generate a presigned upload URL instead of receiving all file bytes itself?

What responsibilities remain with the backend?

## Question 3 — The Reused URL

A client receives a presigned PUT URL.

It uploads a file successfully, then repeats the PUT request using the same URL.

What can happen?

Why isn't the URL automatically a single-use business token?

## Question 4 — Multipart Failure

An S3 multipart upload has received several parts.

The client disconnects before completion.

Is a completed object necessarily available?

What happens to the stored parts?

## Question 5 — The Lost Response

The client times out during finalization.

How would you determine whether the upload completed?

Why is initiating a fresh upload immediately potentially wasteful?

## Question 6 — Content Validation

A user uploads a file named `passport.pdf` with `Content-Type: application/pdf`.

Is that sufficient evidence that the file is safe and valid?

## Question 7 — Object Authorization

A user knows another tenant's object key.

Should that be sufficient to download the file?

Where should the authorization decision occur?

## Question 8 — ETag

Can you always compare an S3 ETag with the MD5 checksum of the original file to prove integrity?

Why not?

## Question 9 — The Missing Database Record

An object exists in storage, but the application database update failed.

What kind of inconsistency is this?

How can the system repair it?

## Question 10 — The Cleanup Job

A cleanup task finds an incomplete upload created yesterday.

Should it always abort the upload?

What additional state or policy matters?

---

# Solutions and Discussion

## Solution 1 — Memory and Streaming

Buffering makes memory consumption proportional to upload size.

Concurrent uploads can exhaust available memory.

Streaming processes bounded chunks, using backpressure and suitable storage APIs to avoid accumulating the whole object in RAM.

## Solution 2 — Direct-to-Storage Architecture

Direct upload removes the application server from the bulk data path.

The backend still owns authentication, authorization, object-key assignment, size policy, upload-session state, completion verification, validation, and lifecycle management.

## Solution 3 — Presigned URL Reuse

A valid presigned PUT URL may be reused.

If the object key already exists, another PUT can overwrite the object unless protective conditions or other controls prevent it.

The application's logical upload session must not assume one-time usage merely because a URL was signed.

## Solution 4 — Multipart State

The uploaded parts can remain stored without a completed object.

They consume storage until the multipart upload is completed or aborted.

A lifecycle policy can help remove abandoned sessions.

## Solution 5 — Uncertain Completion

Check the authoritative upload session and object-store state.

Verify whether the completed object exists and matches the expected metadata and integrity information.

A timeout doesn't prove the storage operation failed.

## Solution 6 — File Validation

No.

The name and content-type header are client-controlled.

Use an allowlist, content inspection, appropriate parsing and size limits, and security scanning when the use case requires it.

A file signature alone isn't sufficient proof of safety.

## Solution 7 — Authorization

No.

The application must verify that the authenticated principal can access the relevant business object.

A temporary download capability should only be issued after authorization and should have an appropriately limited lifetime and scope.

## Solution 8 — ETag Semantics

No.

S3 multipart-upload ETags and certain encryption modes do not represent a full-object MD5 digest.

Use explicit supported integrity-check mechanisms and appropriate checksums.

## Solution 9 — Cross-System Inconsistency

The object store and application database do not participate in one ordinary atomic transaction.

A reconciliation workflow can discover the object, verify its identity and metadata, and repair or quarantine the corresponding application state.

## Solution 10 — Cleanup Safety

No.

The upload may still be active or legitimately resumable.

Cleanup must account for expiration policy, last activity, ownership, transfer state, and coordination with active work.

---

# The Mental Model Worth Keeping

File handling is not simply storing bytes.

It's a lifecycle involving authorization, transfer, storage, validation, publication, retrieval, and deletion.

Large files introduce extended resource lifetimes and partial failures.

Streaming controls memory.

Direct-to-storage transfers reduce application-server bandwidth.

Multipart uploads make large transfers resumable but create cleanup obligations.

Presigned URLs delegate limited capabilities, not business ownership.

Checksums establish byte integrity, not authorization or safety.

And a completed storage operation is not automatically an accepted business document.

The five questions worth remembering are:

**Who may upload or download it?**

**Where do the bytes actually travel?**

**How do we determine whether transfer completed?**

**When does the object become trusted and available?**

**What cleans up abandoned or expired data?**

---

# Next Lecture — SE325-L02: Bulk Imports, Exports, and Background Data Operations

We've learned how to move one large object safely.

The next lecture investigates what happens when the object contains a million records that must be processed.

A supplier uploads a large CSV of hotel rates.

The backend begins importing rows into the database.

Row 412,883 fails validation.

The worker crashes.

Some rows have already committed.

Another tenant starts an enormous export.

Interactive booking requests begin waiting for database connections.

We'll investigate resumable bulk jobs, checkpoints, validation, cancellation, resource limits, and protecting interactive workloads from background data processing.

*The spoken lecture ends here. The following practical experiments should be attempted independently before reading the diagnostic notes.*

---

# Optional Practical Lab — The Interrupted Multipart Upload

## Lab Contract

This is a local simulation of multipart-upload lifecycle behavior.

It uses only Python's standard library and the local filesystem.

No AWS account, object-storage charges, or cloud credentials are required.

The simulation demonstrates:

- Creating an upload session.
- Dividing a file into parts.
- Uploading parts independently.
- Retrying parts.
- Rejecting incomplete finalization.
- Verifying a completed object with SHA-256.
- Leaving unfinished parts behind.
- Aborting an abandoned session.
- Distinguishing transport completion from business acceptance.

It is **not a production upload server**.

In particular, it does not implement real HTTP uploads, authorization, cryptographic signing, concurrent state transitions, antivirus scanning, or S3's actual multipart protocol.

The simulation uses one-mebibyte parts to remain fast on an ordinary laptop. Real S3 multipart uploads generally require at least five mebibytes per part except for the last part.

The laboratory is structured as:

**Predict → Execute → Inspect → Break → Recover → Verify.**

## Lab 1 — Create the Simulator

Create a directory named `se325-upload-lab`.

Inside it, create `studio.py`.

The script creates a seven-mebibyte sample file and maintains an upload manifest.

All generated content lives beneath `se325_lab_store`.

The `init` command removes and recreates that dedicated directory only if a laboratory marker exists.

### The upload simulator

```python id="mtplab"
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import uuid

from pathlib import Path


ROOT = Path("se325_lab_store")
MARK = ROOT / ".lab-marker"

# Small demo parts. Real S3 multipart parts
# generally must be >=5 MiB except the last.
CHUNK = 1024 * 1024


def digest(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(
            lambda: f.read(64 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def get_state():
    if not MARK.exists():
        raise SystemExit(
            "Initialize first: python studio.py init"
        )

    return json.loads(
        (ROOT / "session.json").read_text()
    )


def save(s):
    path = ROOT / "session.json"
    temp = ROOT / "session.tmp"

    temp.write_text(
        json.dumps(
            s,
            indent=2,
            sort_keys=True,
        )
    )

    os.replace(temp, path)


def init():
    if ROOT.exists():
        if not MARK.exists():
            raise SystemExit(
                "Refusing to delete an unmarked directory"
            )

        shutil.rmtree(ROOT)

    ROOT.mkdir()
    MARK.write_text("disposable lab")

    source = ROOT / "sample.bin"
    source.write_bytes(os.urandom(7 * CHUNK))

    session = {
        "upload_id": uuid.uuid4().hex,
        "tenant": "mercury",
        "key": (
            "quarantine/mercury/"
            + uuid.uuid4().hex
        ),
        "expected_bytes": source.stat().st_size,
        "expected_sha256": digest(source),
        "part_bytes": CHUNK,
        "part_count": 7,
        "created_at": time.time(),
        "status": "UPLOADING",
    }

    (ROOT / "parts").mkdir()

    save(session)

    print(
        "Created demo upload:",
        session["upload_id"],
    )


def part(n):
    s = get_state()

    if s["status"] != "UPLOADING":
        raise SystemExit("Upload is not open")

    if not 1 <= n <= s["part_count"]:
        raise SystemExit("Invalid part number")

    source = ROOT / "sample.bin"

    dest = (
        ROOT / "parts" / f"{n:04d}.part"
    )

    temp = dest.with_suffix(".tmp")

    with source.open("rb") as src, temp.open("wb") as out:
        src.seek((n - 1) * s["part_bytes"])

        remaining = min(
            s["part_bytes"],
            s["expected_bytes"] - src.tell(),
        )

        while remaining:
            data = src.read(
                min(64 * 1024, remaining)
            )

            if not data:
                raise RuntimeError("Source truncated")

            out.write(data)
            remaining -= len(data)

    os.replace(temp, dest)

    print(
        "Stored part",
        n,
        "bytes",
        dest.stat().st_size,
        "sha256",
        digest(dest)[:16],
    )


def finish():
    s = get_state()

    if s["status"] not in (
        "UPLOADING",
        "QUARANTINED",
    ):
        raise SystemExit(
            "Upload is not completable"
        )

    final = (
        ROOT / "objects" / s["key"]
    )

    if not final.exists():
        for n in range(
            1,
            s["part_count"] + 1,
        ):
            p = (
                ROOT
                / "parts"
                / f"{n:04d}.part"
            )

            if not p.is_file():
                raise SystemExit(
                    f"Missing part {n}; completion denied"
                )

        final.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = final.with_suffix(
            ".assembling"
        )

        with temp.open("wb") as out:
            for n in range(
                1,
                s["part_count"] + 1,
            ):
                p = (
                    ROOT
                    / "parts"
                    / f"{n:04d}.part"
                )

                with p.open("rb") as f:
                    shutil.copyfileobj(
                        f,
                        out,
                        length=64 * 1024,
                    )

        if (
            temp.stat().st_size
            != s["expected_bytes"]
            or digest(temp)
            != s["expected_sha256"]
        ):
            temp.unlink(
                missing_ok=True
            )

            raise SystemExit(
                "Size or checksum mismatch;"
                " completion denied"
            )

        os.replace(temp, final)

    if (
        final.stat().st_size
        != s["expected_bytes"]
        or digest(final)
        != s["expected_sha256"]
    ):
        raise SystemExit(
            "Final object does not match manifest"
        )

    s["status"] = "QUARANTINED"
    save(s)

    shutil.rmtree(
        ROOT / "parts"
    )

    (ROOT / "parts").mkdir()

    print(
        "Stored completed object in quarantine:",
        final,
    )


def status():
    s = get_state()

    parts = list(
        (ROOT / "parts").glob("*.part")
    )

    print(
        json.dumps(
            {
                "status": s["status"],
                "uploaded_parts": len(parts),
                "uploaded_part_bytes": sum(
                    p.stat().st_size
                    for p in parts
                ),
                "expected_bytes": s["expected_bytes"],
                "object_key": s["key"],
            },
            indent=2,
        )
    )


def age():
    s = get_state()

    s["created_at"] -= (
        8 * 24 * 3600
    )

    save(s)

    print(
        "Session now appears eight days older"
    )


def sweep():
    s = get_state()

    is_stale = (
        time.time() - s["created_at"]
        > 7 * 24 * 3600
    )

    if (
        s["status"] == "UPLOADING"
        and is_stale
    ):
        shutil.rmtree(
            ROOT / "parts"
        )

        (ROOT / "parts").mkdir()

        s["status"] = "ABORTED"
        save(s)

        print(
            "Aborted stale session and"
            " removed unfinished parts"
        )

    else:
        print(
            "Nothing eligible for cleanup"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python studio.py "
            "init|part N|finish|status|age|sweep"
        )

    ops = {
        "init": init,
        "finish": finish,
        "status": status,
        "age": age,
        "sweep": sweep,
    }

    command = sys.argv[1]

    if command == "part" and len(sys.argv) == 3:
        part(int(sys.argv[2]))

    elif command in ops and len(sys.argv) == 2:
        ops[command]()

    else:
        raise SystemExit("Unknown command")
```

This simulator deliberately processes files in bounded chunks.

It uses local filesystem replacement to demonstrate one possible finalization step.

Real cloud object storage has different atomicity and lifecycle mechanisms.

The simulator also does not provide safe concurrent access to its JSON state file. Production upload sessions should be maintained using an appropriate transactional or coordinated state mechanism.

---

# Lab 2 — Start an Upload Session

Initialize the laboratory.

```bash id="u1t0cp"
python studio.py init
```

Inspect the generated directory.

You should find:

- `sample.bin`
- `session.json`
- `parts/`

The sample file is seven mebibytes.

The session manifest contains an upload ID, expected length, expected SHA-256 digest, part count, and lifecycle status.

### Questions

Why does the upload have its own ID?

Why should the object key be generated by the application?

Why is the expected checksum recorded before finalization?

Why does the initial status say `UPLOADING` rather than `AVAILABLE`?

---

# Lab 3 — An Interrupted Upload

Upload the first two parts.

```bash id="p2try1"
python studio.py part 1
python studio.py part 2
python studio.py status
```

The status should show two uploaded parts and approximately two mebibytes of stored unfinished data.

### Prediction

What happens if the client stops here?

Is a completed object available?

How much data remains on disk?

Now attempt to finalize.

```bash id="b4missing"
python studio.py finish
```

The operation should fail because the remaining parts are missing.

### Investigation

Observe that the existing parts remain stored.

This represents an incomplete upload session.

It is not a successful final object.

### Acceptance criteria

You can distinguish a failed finalization from a failed individual part upload.

You can explain why retained incomplete parts require cleanup.

---

# Lab 4 — Resume the Upload

Upload the missing parts.

```bash id="resume4"
python studio.py part 3
python studio.py part 4
python studio.py part 5
python studio.py part 6
python studio.py part 7
```

Check status.

```bash id="resumest"
python studio.py status
```

### Prediction

Should the client need to upload Parts 1 and 2 again?

Not if the existing parts are verified and still belong to the same logical upload session.

### Retry experiment

Re-upload Part 3.

```bash id="retry3"
python studio.py part 3
```

The simulator replaces the stored part at that number with the same expected bytes.

### Investigation

What would happen if a retry supplied different bytes?

How should an upload protocol detect that mismatch?

How does S3's upload ID and part number mechanism support retries?

---

# Lab 5 — Finalize with Integrity Verification

Complete the upload.

```bash id="finalize"
python studio.py finish
python studio.py status
```

The script should verify the assembled object's size and SHA-256 digest.

It then stores the completed object under a quarantine key.

The unfinished part files are removed after successful finalization.

### Critical question

Why does the resulting state say `QUARANTINED` rather than `AVAILABLE`?

Because transfer completion isn't the same as security and business acceptance.

### Repeat completion

Run:

```bash id="again5"
python studio.py finish
```

The operation should recognize the already completed object and verify its identity rather than create another distinct final object.

### Acceptance criteria

You understand why retries after uncertain completion need an authoritative status check.

You can explain why a checksum is useful but insufficient to establish file safety.

---

# Lab 6 — Corrupt a Part

Reset the laboratory.

```bash id="corrupt0"
python studio.py init
```

Upload all seven parts.

Now deliberately alter the contents of one part file using a local text or binary editor, or a short Python script.

For example, this command replaces the first byte of Part 3.

```bash id="corrupt3"
python -c "from pathlib import Path; p=Path('se325_lab_store/parts/0003.part'); b=bytearray(p.read_bytes()); b[0]^=1; p.write_bytes(b)"
```

Attempt finalization.

```bash id="corruptf"
python studio.py finish
```

### Investigation

The assembled file has the correct total size.

But its SHA-256 digest differs from the expected value.

The simulator should reject completion.

### Questions

Why isn't file size enough to prove integrity?

What is the difference between an integrity checksum and a malware scan?

Why shouldn't we interpret an S3 ETag as a universal full-object MD5 digest?

---

# Lab 7 — Abandoned Multipart Cleanup

Reset the laboratory.

```bash id="cleanup0"
python studio.py init
```

Upload two parts.

```bash id="cleanup2"
python studio.py part 1
python studio.py part 2
python studio.py status
```

Run the cleanup command.

```bash id="cleanfirst"
python studio.py sweep
```

The upload should not be removed because it is still within the simulated retention window.

Now make the session appear older.

```bash id="ageit"
python studio.py age
```

Run cleanup again.

```bash id="cleansecond"
python studio.py sweep
python studio.py status
```

The stale unfinished parts should be removed, and the session should enter `ABORTED`.

### Investigation

What if a real upload is still active but has an old creation timestamp?

What if a part upload is in flight when cleanup begins?

What state or coordination would be necessary to avoid deleting legitimate work?

### Production extension

Explain how an S3 lifecycle rule using `AbortIncompleteMultipartUpload` can act as a safety net.

Would that rule also delete completed objects that are no longer referenced by your database?

No. That's a separate lifecycle problem.

---

# Lab 8 — Design the Direct-to-S3 Upload API

## Starting requirement

Mercury wants to let authenticated hotel suppliers upload large photograph archives directly to S3.

The backend should not proxy the file bytes.

### Your assignment

Design the following operations.

**Create upload session:** Authenticate the supplier, validate the intended upload, generate an object key, create the durable session, and return upload instructions.

**Upload parts:** Allow the client to transfer parts through appropriate temporary storage capabilities.

**Inspect status:** Determine which parts or completed object exist and whether the logical session remains valid.

**Finalize:** Verify storage completion and integrity, then transition the object to quarantine.

**Validate:** Inspect the object and decide whether it can become available.

**Abort:** Stop an abandoned upload and remove its unfinished resources.

### Security requirements

The design must prevent:

- One tenant overwriting another tenant's object.
- Arbitrary use of privileged bucket keys.
- Uncontrolled object sizes.
- Public exposure of unvalidated documents.
- Treating a client-supplied filename as a trusted path.
- Reusing an upload URL as evidence of business completion.

### Acceptance criteria

The backend owns the upload lifecycle even when S3 handles the bytes.

---

# Lab 9 — The Completed Object Without a Database Record

## Incident

A client completes a multipart upload successfully.

The object exists in storage.

The application attempts to mark the corresponding upload session as complete.

The database write fails.

### Tasks

Explain why the object and database cannot be assumed to update atomically.

Determine how a recovery worker can establish whether the object exists.

Describe the checks required before accepting it.

Explain what happens if the original client retries finalization.

### Additional challenge

The storage service sends an object-created notification twice.

How should the validation worker behave?

### Acceptance criteria

You define an idempotent or otherwise safe state-recovery procedure.

You don't treat duplicate storage events as evidence that two different business uploads occurred.

---

# Lab 10 — The Download Authorization Failure

## Incident

A customer can request:

`GET /documents/{documentId}/download`

The backend retrieves the document metadata and generates a presigned S3 download URL.

The implementation verifies that the requester is logged in.

It does not verify that the document belongs to the requester or that they otherwise have permission to access it.

### Your tasks

Identify the authorization failure.

Explain why a hard-to-guess object key isn't sufficient protection.

Design a corrected authorization boundary.

Determine how long a presigned download URL should remain valid for the use case.

Describe how to prevent sensitive URL values from being unnecessarily exposed through logs and analytics.

### Acceptance criteria

Authentication and object-level authorization are treated as separate requirements.

---

# Final Incident — The Four-Gigabyte Supplier Archive

## Starting symptom

A supplier uploads a four-gigabyte archive.

The browser times out.

The supplier retries three times.

The application database contains several pending upload records.

The object-storage service contains incomplete multipart sessions.

Some parts remain billable.

Support cannot determine whether any upload completed successfully.

### Required incident report

Prepare a technical investigation containing:

**Business context:** What is the supplier trying to accomplish?

**Transfer architecture:** Which systems carry the bytes?

**Resource pressure:** What memory, bandwidth, temporary-storage, and timeout limits matter?

**Upload identity:** How can retries be associated with one logical transfer?

**Storage evidence:** How do you distinguish uploaded parts from completed objects?

**Completion verification:** What establishes that the intended bytes arrived?

**Business acceptance:** What validation is required before making the object available?

**Cleanup:** What happens to abandoned sessions and orphaned completed objects?

**Security:** How are upload and download permissions enforced?

**Recovery:** How would you restore a consistent state without losing legitimate supplier data?

**Verification:** Which metrics prove the correction worked?

### Interviewer challenge

Your interviewer says:

"Why not just increase the API timeout to ten minutes and give the container eight gigabytes of RAM?"

Explain when increasing resource limits might help and why it doesn't address the fundamental upload lifecycle, streaming, resumability, security, or cleanup problems.

---

# STOP — Independent Investigation Ends Here

Do not read the following notes until you've attempted the laboratory.

The objective is to reason about real failure boundaries rather than memorize the intended fix.

---

# Lab Diagnostic Notes

## Interrupted Upload

An interrupted multipart transfer can leave successfully uploaded parts stored without a completed object.

The client should preserve or recover the logical upload identity.

A new upload session isn't automatically necessary.

## Streaming

Bounded chunk processing reduces peak application memory requirements.

It doesn't eliminate network, disk, or storage costs.

Production implementations need suitable backpressure, timeouts, and cleanup.

## Integrity

The simulator compares SHA-256 digests.

A mismatch rejects finalization even when total size is correct.

This demonstrates byte-integrity verification, not malware detection or authorization.

## Quarantine

A completed object remains quarantined until the application accepts it.

Security scanning, metadata validation, business checks, and retention policy may be required before publication.

## Cleanup

Old unfinished parts are removed by the simulated sweeper.

Real production cleanup must consider in-flight work and concurrent state transitions.

S3 lifecycle rules provide an additional safety mechanism for abandoned multipart sessions.

## Cross-System Recovery

The object store and application database are independent systems.

A completed object may exist before the metadata transaction succeeds.

Reconciliation should verify the object and repair or reject the application's upload record safely.

## Authorization

Knowing an object identifier doesn't grant permission to access it.

The backend must authorize the requested business object before issuing a download capability.

## Production Architecture

A strong solution uses a durable upload session, bounded transfer mechanisms, constrained storage capabilities, explicit completion verification, quarantine, safe validation, and cleanup.

The design should survive interrupted transfers and uncertain responses without multiplying orphaned storage.

---

# Further Reading

1. **Amazon S3 — What Is S3?**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html

2. **Amazon S3 — Multipart Upload Overview**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html

3. **Amazon S3 — Multipart Upload Limits**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html

4. **Amazon S3 — Aborting Multipart Uploads**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/abort-mpu.html

5. **Amazon S3 — Lifecycle Cleanup of Incomplete Multipart Uploads**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html

6. **Amazon S3 — Presigned URLs**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html

7. **Amazon S3 — Uploading with Presigned URLs**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html

8. **Amazon S3 — Checking Object Integrity**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html

9. **Amazon S3 — Event Notifications**  
   https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html

10. **Amazon S3 — GetObject API**  
    https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html

11. **OWASP — File Upload Cheat Sheet**  
    https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

12. **Node.js — Stream API**  
    https://nodejs.org/api/stream.html

13. **MDN — HTTP Range Requests**  
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests

14. **tus — Resumable Upload Protocol**  
    https://tus.io/protocols/resumable-upload

Related programme chapters:

- SE320-L01 — The Anatomy of a Backend Service
- SE310-L01 — The Frontend–Backend Contract
- SE310-L02 — Authentication and Browser Security
- SE310-L03 — Application and Infrastructure Security
- SE340-L03 — Cloud Infrastructure and AWS Architecture
- SE325-L02 — Bulk Imports, Exports, and Background Data Operations
- SE325-L04 — Production Data Repair, Audit, and Lifecycle

---

# Dense Cheatsheet — Interview Glance Card

*The complete card is fenced so voice readers can skip it.*

```text id="se325card"
SE325-L01 — FILES, UPLOADS, OBJECT STORAGE
================================================

CENTRAL PRINCIPLE
-----------------
Receiving bytes != accepting a file.

A file has a lifecycle:
  authorization
  transfer
  storage
  verification
  validation
  publication
  download
  retention/deletion

LARGE REQUESTS
--------------
Small JSON != 4 GB file.

Large files create:
  memory pressure
  network pressure
  long connections
  timeout exposure
  temporary storage
  partial failures
  retry uncertainty

BUFFERING
---------
Entire payload in memory.

Memory proportional to file size.
Dangerous with concurrent uploads.

STREAMING
---------
Bounded chunks.
Backpressure.
Incremental processing.

Memory no longer proportional
to entire payload size.

Still uses resources.

UPLOAD ARCHITECTURES
--------------------
Backend-proxied:
  API receives and streams bytes.

Direct-to-storage:
  API authorizes.
  Client uploads to storage.

Multipart/resumable:
  independent parts
  retry failed parts
  complete when valid

OBJECT STORAGE
--------------
Bucket
Object key
Object data
Object metadata
Version, where enabled

S3 != POSIX filesystem.

PRESIGNED URL
-------------
Time-limited bearer capability.

Scoped by:
  operation
  bucket/key
  signer permissions
  signed request properties
  policy controls where applicable

Not automatically single-use.
PUT may overwrite existing key.
Do not log unnecessarily.

CORS != AUTHORIZATION.

UPLOAD SESSION
--------------
uploadId
tenant/owner
object key
expected size
expected checksum
status
created/expires
storage upload ID
validation result

States:
  REQUESTED
  UPLOADING
  QUARANTINED
  AVAILABLE
  REJECTED
  ABORTED
  EXPIRED

S3 MULTIPART
------------
CreateMultipartUpload
UploadPart
CompleteMultipartUpload
AbortMultipartUpload

Up to 10,000 parts.
Nonfinal parts usually >=5 MiB.

Incomplete parts consume storage.
They aren't a completed object.

CLEANUP
-------
Abort abandoned multipart sessions.
Lifecycle safety-net rules.
Reconcile orphaned completed objects.
Respect active uploads and retention.

INTEGRITY
---------
Content length is not enough.

Use appropriate checksums.

S3 ETag != universal full-object MD5,
especially for multipart uploads.

Integrity != security.

FILE VALIDATION
---------------
Allowlist types and sizes.
Do not trust filename.
Do not trust Content-Type alone.
Inspect actual content.
Limit decompression and processing.
Scan/sandbox when appropriate.
Use server-generated keys.

QUARANTINE
----------
Bytes arrived.
Not yet accepted.
Not yet publicly available.

Validation/scan can be asynchronous.

DOWNLOADS
---------
Object-level authorization.
Bounded streaming.
Presigned GET when appropriate.
Range support where needed.
Safe response headers.
Sensitive URL handling.

TENANT ISOLATION
----------------
Tenant prefixes help organization.
They aren't sufficient authorization.

Resolve permitted object through
authoritative application metadata.

CROSS-SYSTEM CONSISTENCY
------------------------
Object store and DB do not share
one ordinary atomic transaction.

Possible:
  object exists, metadata missing
  metadata pending, object missing
  scan event duplicated
  validation incomplete

Use lifecycle states and reconciliation.

EVENT NOTIFICATIONS
-------------------
S3 notifications can be
at-least-once and out of order.

Consumers need safe duplicate handling.

STORAGE COST
------------
Stored bytes
Incomplete parts
Requests
Egress
Replication
Scanning
Retention
Orphans

Monitor abandoned sessions.

DIAGNOSTIC PROCEDURE
--------------------
1. Identify logical upload.
2. Trace complete request path.
3. Check actual byte transfer.
4. Inspect multipart state.
5. Check object completion.
6. Verify size/integrity.
7. Inspect metadata transaction.
8. Check validation/quarantine.
9. Identify retries and orphans.
10. Correct and verify cleanup.

RED FLAGS
---------
"Just increase request timeout."
"Read file into one Buffer."
"Content-Type proves PDF."
"ETag always equals MD5."
"Presigned URL is single-use."
"Uploaded means safe to publish."
"Timeout means upload failed."
"Multipart parts are free."
"Known object key grants access."
"Delete all old sessions blindly."
"Strong S3 consistency means
 database and S3 are atomic."

MENTAL MODEL
------------
Who can access the file?
Where do the bytes move?
What proves completion?
When is it trusted?
Who cleans up abandoned data?

NEXT
----
SE325-L02
Bulk Imports, Exports,
and Background Data Operations
```
