# NS08 — The Image That Ate the Worker

*A design-sharing platform grows faster than its upload pipeline, and a performance problem turns out to involve browsers, queues, operating systems, security, and the meaning of success.*

All companies, people, and incidents are fictional. The mechanisms are realistic; figures are illustrative.

## Monday — The customer who couldn't show her work

InkNest was a collaboration platform for small architecture and interior-design studios. A user uploaded project images, marked regions for review, and shared private galleries with clients. The product looked simple: drag a file into the browser, watch a progress bar, and see a thumbnail appear.

At ten seventeen, Theo from customer support forwarded a complaint from a Lisbon studio. Their latest architectural render—an image several thousand pixels wide—had uploaded successfully, but the gallery remained stuck on “Processing.” Another user uploaded the same image twice and received two different thumbnails. A third reported that the whole project list slowed down whenever a colleague added a large batch of images.

Mika, backend engineer, checked the API dashboard. Upload requests were fast. Most returned success in less than two hundred milliseconds. The image worker dashboard was less encouraging: job retries had increased, processing time had doubled, and one Kubernetes deployment had restarted dozens of times overnight.

Lena, frontend engineer, opened the application. The browser displayed an enthusiastic green check as soon as object storage acknowledged the upload. That check meant the bytes had arrived. It did not mean a usable thumbnail existed, nor that the upload had been validated, nor that other people had access to it. The interface had collapsed three different states into one word: done.

They agreed to change the UI eventually, but Mika wanted to understand why processing had become unreliable first.

## The pipeline that had no reason to be synchronous

InkNest did not send multi-gigabyte image bodies through its ordinary JSON API. A backend endpoint authenticated the user and issued a short-lived, restricted upload authorization. The browser sent the file to object storage. The API recorded a pending asset with an owner, project, storage key, and expected size. A background job then validated the file, extracted metadata, generated thumbnails, and marked the asset ready.

This architecture kept the request path responsive. It also introduced an asynchronous workflow with failure modes the original upload dialog had never communicated. A user could close the tab after sending the bytes; the system still needed to process the file. A worker could fail; the upload should remain recoverable. A message could be delivered twice; it should not result in conflicting asset versions.

The job queue used at-least-once delivery. Mika explained to Lena that this didn't mean every job ran exactly once. If a worker completed work but died before acknowledging the message, the queue could deliver it again. They designed each processing attempt to use the asset identity and processing version to avoid duplicate publication of the same output.

There was another subtlety. A client-supplied file name was not a safe storage path, nor a reliable unique identity. Two users could upload files both named `final-final-2.png`; one user could include odd characters or misleading extensions. The storage object used a generated key scoped to the authorized project, while the display name remained untrusted metadata.

The backend verified permissions before issuing upload authorization and again before exposing the finished asset. A direct object-storage URL without appropriate expiration and scope could leak private designs. Access control could not rely on the gallery page merely hiding a button.

On Tuesday, Mika reproduced the processing failure with one of the affected files. The upload succeeded. The worker started. Memory usage rose sharply. The container disappeared.

## Tuesday — The confusing 30 percent CPU

Jonas, the platform engineer, joined the investigation. The Kubernetes event log reported that the worker had been killed for exceeding its memory limit. The worker's CPU utilization had been modest. Someone proposed increasing the number of replicas because “the cluster isn't busy.”

Jonas explained the distinction. A container runs inside resource constraints enforced through the operating system. A process can exceed its memory allowance even when the physical host has free RAM, and average CPU percentage doesn't describe peak memory allocation or garbage-collection behavior. Kubernetes can schedule a replacement Pod, but that doesn't make the failed attempt succeed. If a particular file always triggers the same memory peak, the new worker may die in the same place.

The worker was written in Python and called an image-processing library. For certain formats, reading a compressed image into memory produced an uncompressed pixel buffer far larger than the uploaded file. Generating several thumbnail variants at once allocated additional buffers. The code had been written for typical phone photos and tested with five-megabyte samples. It had not been designed around a maximum decoded pixel count.

Mika noted that increasing the container memory limit might reduce failures but wasn't a complete strategy. An attacker could upload a tiny compressed file that expanded into an enormous image. A resource-exhaustion bug was a security problem as well as a performance problem.

They added validated limits for file type, dimensions, decoded pixel count, and processing budget. The image decoder ran with controlled resource usage, and outputs were generated in a way that avoided keeping unnecessary full-sized copies resident simultaneously. Malformed files failed into a terminal user-visible state instead of cycling forever through retries.

The team also isolated image processing from other background jobs. Previously, thumbnail generation and email notifications shared the same worker deployment. A problematic image could delay client invitations and password reset messages. Separating workloads didn't require building a new microservice architecture for every helper function; it required a clear resource and failure boundary where the workloads genuinely differed.

## The file that could not be trusted

Farah had one question about the upload pipeline: who decided whether an uploaded file was an image? The frontend checked the extension and the browser's reported MIME type. The backend also checked the provided MIME type. Both values could be misleading or supplied by an untrusted client. A file named `beautiful-room.png` was not necessarily a safe PNG, and a library capable of decoding many formats increased the worker's attack surface.

They separated accepting bytes from trusting them. Object storage could receive a file into a restricted temporary area. A processor would inspect its actual content with a controlled decoder, reject unsupported or malformed formats, apply resource limits, and generate a sanitized representation for ordinary viewing. Only after validation would the application mark the asset ready for distribution.

The team also considered what metadata to preserve. A photo might contain location information or details about the device that created it. For a private architecture project, exposing that metadata to every gallery viewer could reveal more than the user intended. The product kept only what its features required and stripped other metadata from derived public-facing previews according to its policy.

Theo asked if the team could skip validation for uploads from paid enterprise customers. Farah said authentication established which user was sending data, not whether every file from that user was benign. Trusted identities could still upload corrupted files, accidentally or otherwise. The validation boundary existed because the parser was exposed to untrusted bytes, regardless of whether the user had a subscription.

This wasn't merely a security lecture inserted into the project. A malformed upload had been exhausting processing memory, retries had harmed other workloads, and customers couldn't distinguish acceptable files from invalid ones. The same content boundary affected resource safety, queue behavior, UI state, and customer support.

## Wednesday — The queue got faster, then the site got slower

With the memory issue fixed, Mika increased worker concurrency to clear the backlog. Queue depth fell quickly. Ten minutes later, the project-list API became slow. The new workers were issuing many metadata writes, thumbnail status updates, and cache invalidations to the same PostgreSQL instance that served interactive user requests.

The database had spare CPU but many sessions waiting on connections and I/O. Some queries were small, but multiplied by high concurrency they exhausted connection-pool capacity. Adding another ten worker processes increased the number of database connections rather than the amount of useful completed work.

Jonas asked Mika to distinguish throughput from goodput: successful images processed per minute mattered, not merely attempts started per minute. The team set bounded worker concurrency, reduced redundant writes, and batched safe metadata updates where doing so preserved correctness. They monitored completed assets, retry frequency, queue waiting age, and database pool saturation together.

The application also performed an inefficient read on each gallery visit. It fetched every image's entire transformation history and then displayed only the latest thumbnail status. An apparently simple list endpoint was reading thousands of rows and doing work the UI didn't need. Mika introduced an authoritative current-state field, maintained during the processing transition, and kept the detailed history for audit and troubleshooting. An index matched the common filter by project and sort by creation time. The page became faster without pretending that fetching twenty records must be cheap regardless of how the database chose them.

A reviewer asked whether denormalizing current status duplicated data. It did. But duplication can be a deliberate read-model choice when the team defines the source of truth, update rules, and recovery path. The bad version is not duplication itself; it's duplicated facts that can silently disagree with no owner responsible for reconciliation.

## The test that accidentally protected a different system

Evie, the QA engineer, built an integration test for the problematic image. It uploaded a large sample, waited for a ready status, and verified that a thumbnail could be retrieved. The test passed repeatedly in staging. Yet a canary worker in production still restarted during a batch upload.

The difference was concurrency and environment. Staging processed one image at a time with generous container limits. Production processed multiple images per worker process and used tighter memory quotas. A worker that safely decoded one image might exceed its memory allowance when it decoded four simultaneously. The test protected individual-file correctness but hadn't modeled resource contention.

Jonas designed a load test that varied file dimensions, concurrency, and the number of worker replicas while measuring successful transformations per minute, peak resident memory, queue age, and database saturation. They learned that the optimal concurrency was lower than expected. Above that point, retries and garbage collection consumed more resources than the additional parallelism produced as useful output.

A developer proposed configuring the Kubernetes Horizontal Pod Autoscaler to add workers whenever queue depth rose. Jonas said autoscaling could help but wasn't an infinite-capacity promise. Workers still depended on the same database, storage service, and queue broker. More Pods could make downstream contention worse if each opened its own database connection pool and tried to process the backlog at full speed.

They limited aggregate concurrency and established resource-aware admission controls for unusually expensive transformations. Some large jobs entered a lower-priority lane with their own worker limits. Customer-visible processing time improved because ordinary uploads stopped waiting behind a handful of giant files and the service avoided repeated crashes.

## Thursday — The browser tells a better story

Lena rebuilt the upload UI around durable backend states. An asset could be uploading, uploaded, queued, processing, ready, or failed. The progress bar described bytes sent while uploading, but after that it switched to processing status instead of freezing at ninety-nine percent.

She used a simple status endpoint and occasional polling, with a faster refresh while the panel was visible. A colleague proposed WebSockets. Lena asked which interaction genuinely required two-way, low-latency messaging. A one-way event stream could work, but polling was reliable enough at their scale and simpler to operate. The client could recover after sleep or network loss by fetching current state, not by assuming it had received every intermediate notification.

They also fixed a React race. A user could navigate from project A to project B while project A's upload status request remained in flight. An old response sometimes updated the newly displayed project. State and request identity had to follow the project and asset, not merely whichever component happened to be on screen. They added stable query keys and prevented outdated responses from replacing current context.

A browser could optimistically show the uploaded image's local preview as soon as the file was selected. It still had to distinguish that preview from the processed server representation. A local preview proved the browser could decode the file; it did not prove the backend had safely stored, processed, and authorized it for a shared gallery.

Customer support liked the new error messages. A failed image no longer looked like a spinner with no end. The interface gave a useful explanation and a safe retry path, rather than telling the user to refresh and hope.

## The upload that succeeded and never belonged to anyone

During cleanup, Mika found thousands of objects in temporary storage with no corresponding asset record. Some represented uploads interrupted before the browser finalized metadata. Others came from an earlier API version that issued upload authorization and only tried to create the database record afterward. If the client disconnected between those actions, storage held the bytes but the application had no durable way to identify their owner or intended purpose.

They changed the protocol so the API created an upload intent before authorizing the object transfer. The intent included the tenant, target project, expected limits, and an expiry. The browser used the temporary storage key associated with that intent. A completion call or storage event triggered verification of the uploaded object and moved the intent into processing. Stale intents could be expired and their temporary objects removed according to a documented retention policy.

The new design still had failure windows. A storage event could be delayed. A completion call could be retried. A user could upload the same bytes twice under distinct intents. The system did not assume that a storage event arrived exactly once or that a client callback was authoritative. Durable intent identity and idempotent transitions made it possible to reconcile incomplete workflows.

Evie added tests for an upload that finished after its authorization expired, a completion call sent twice, and a user trying to reuse an upload intent from a different project. Farah reviewed whether temporary objects could be accessed through predictable keys. The team kept temporary storage private and restricted permissions, rather than treating a random-looking object key as sufficient authorization.

Lena liked the new state model because it gave her better UI language. “Uploading” meant bytes in transfer. “Processing” meant the service had the object and was working on it. “Ready” meant a validated derived representation existed and could be accessed by an authorized user. The distinction was less glamorous than animation, but it stopped the interface from making promises it couldn't keep.

## Friday — The cache was very efficient at being wrong

InkNest used a CDN for public marketing images and, in one deployment, cached transformed thumbnails behind a shared edge hostname. An optimization rule keyed cached responses mostly by the requested path. A private project thumbnail occasionally appeared under a stale signed URL after its access permissions changed.

The security engineer, Farah, investigated whether this was an actual exposure or merely an expired preview in a browser. She traced the cache key, response headers, origin authorization, URL lifetime, and whether the edge might serve an object after permission revocation. The team changed the private asset delivery design so a request had to pass an appropriate authorization boundary. For truly public marketing assets, long-lived CDN caching remained desirable. For private client work, the caching strategy was constrained by who could access the asset and how revocation should behave.

Somebody suggested setting every response to `no-store`. Farah said that might be a safe emergency containment step for sensitive responses, but it wasn't a substitute for a coherent access model and it could unnecessarily degrade safe public content. Security design should distinguish public immutable assets from private, changing, permissioned data.

At the same time, the platform team prepared a staged deployment. Worker images could be rolled forward without restarting the upload API. Database changes were compatible with old and new workers during the transition. The team verified that a partial rollback would not make newly created asset states unreadable by an older process.

The release succeeded, except for one surprise. A monitoring alert based on queue depth fired even as processing improved. The backlog had accumulated during the incident and was still large, but its oldest-message age and completed-work rate were improving. The team revised the alert so it reflected user impact and saturation, not just the existence of queued work.

## The economics of a thumbnail

The finance team asked why storage and network costs kept rising despite the new processor's efficiency. InkNest stored original files, several thumbnail resolutions, and sometimes multiple intermediate outputs. The CDN served many repeated views, but private projects with rapidly changing access rules avoided aggressive shared caching. Customers wanted high-resolution images while sales wanted low subscription prices.

Mika modeled the cost per uploaded asset: object storage for originals and derivatives, compute for decoding and transformation, database metadata, repeated egress, and operational overhead for retries and debugging. The picture varied dramatically by file size and user behavior. Ten thousand thumbnails never viewed had a different cost profile from a small thumbnail opened daily by a project team.

They changed the pipeline to generate a modest baseline set of representations and create certain expensive variants on demand, with caching where authorization semantics allowed. They added lifecycle rules for temporary processing files and explicit retention for abandoned uploads. These changes reduced waste without hiding access-control decisions inside a cost optimization.

The pricing discussion exposed one more architectural lesson. A technically elegant pipeline that transformed everything into every possible resolution could be financially silly. Engineers needed to understand not only whether work was possible and correct, but whether the product's economics justified it at the customer's scale.

## One final failure in the viewer

During rollout, Lena noticed a different symptom: images now processed reliably but some galleries felt sluggish when users scrolled. The backend had reduced processing time, and CDN hit rates were high. Yet the browser stuttered on large projects because the frontend eagerly mounted hundreds of image elements and performed layout work for all of them.

She recorded a performance trace and found time spent decoding images, constructing elements, and recalculating layout. The bottleneck was no longer the worker. Virtualizing long galleries, reserving image dimensions to reduce layout shifts, loading appropriate thumbnail resolutions, and avoiding unnecessary re-renders improved the experience far more than adding another backend instance.

The team distinguished two types of optimization. Worker efficiency affected how quickly a new asset became ready. Viewer efficiency affected how smoothly a customer could browse assets that were already ready. A single “image performance” dashboard blurred those experiences together. They added measurements around both journeys so future changes could be evaluated at the layer where users felt them.

Mika found the distinction reassuring. The architecture wasn't one pipeline with one speed. It was several linked experiences, each with a different workload and a different definition of success. Fixing one moved the bottleneck elsewhere. That didn't mean the first fix failed; it meant the team could now see farther down the path.


## Two weeks later — The expensive part was uncertainty

InkNest's support team reviewed the incident cost. The cloud bill for extra processing capacity was noticeable but manageable. The greater cost had been customer uncertainty: people didn't know if their files were uploaded, whether they should try again, or whether their private designs were accessible to the correct clients.

Mika and Lena walked through the entire lifecycle on a whiteboard. The browser obtained permission to upload. Object storage accepted the bytes. The backend persisted a pending record. A queue delivered work. A constrained processor validated and transformed the file. The database recorded authoritative state. The API exposed it to authorized clients. A cache accelerated delivery where its permission and freshness semantics allowed. Observability followed the transitions, not only the first HTTP response.

Jonas said that nearly every component had behaved reasonably according to its narrow contract at some point during the incident. Object storage had stored bytes. The queue had redelivered abandoned jobs. Kubernetes had restarted workers that exceeded their limits. The API had returned quickly. Yet the product was failing because nobody had owned the meaning of “ready” across all those boundaries.

Theo from support sent the Lisbon studio an update. Their large render was now available, and the gallery reported processing failures clearly for invalid files. The customer thanked him, then asked whether the team could add a button to rotate an image ninety degrees.

There was a short silence in the engineering channel. Mika wrote, “New feature. New state transition. Let's design it before the button.”

The team had learned that performance and reliability weren't properties of the image processor alone. They emerged from the entire path: browser, authorization, object storage, queue, worker memory, database, caching, deployment, and the human expectations attached to a tiny green checkmark.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Connections:** SE240-L02/L03/L05 (client state, UI performance); SE250-L03 (server state/query identity); SE310-L02/L03 (auth and application security); SE320-L01/L02/L03 (service boundaries, caches, queues); CS320-L04/L06 (memory constraints and runtimes); CS330-L01/L02 (schema, indexes, query shape); CS340-L01 (derived state); CS430-L01/L03 (idempotency, overload); SE340-L02 (containers); SE440-L01/L02 (observability, incidents); SE215-L11 (release coordination).

**Technical caveats:** Compressed file size does not bound decoded memory use. A restarted Pod does not imply work completed. Exact cloud storage and CDN authorization models differ. Polling, SSE, and WebSockets can all work when paired with durable state and appropriate resource controls.

**Optional reflections:** What does “upload complete” mean to the customer? Why did adding worker concurrency slow interactive requests? Where should permission enforcement happen for private thumbnails?
