---
id: SE240-L05
course: SE240
title: "Performance: Why Fast Code Can Feel Slow"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S10]
prev: SE240-L04
next: SE240-L06
---






# SE240 — Browser and Frontend Engineering

## Lecture 05: Performance: Why Fast Code Can Feel Slow

*Why a website can have excellent servers, efficient algorithms, and modern infrastructure—yet still feel like it's running on a potato.*

---

# 1. The Website That Was Fast According to Everyone Except Its Customers

Your hotel-booking platform has a performance problem. Customers complain that the website is slow.

Naturally, the engineering team investigates. The backend team proudly produces its measurements:

```text
Average API response:      68 ms
Database query time:       12 ms
Server CPU utilization:    24%
```

Excellent. The infrastructure team reports that CloudFront is serving most static assets from cache.

The frontend team points out that the application uses Vue 3, Vite, lazy-loaded routes, and reasonably compact JavaScript bundles. Everything looks healthy.

Then someone runs a performance investigation using an ordinary midrange Android phone. The results are considerably less impressive:

```text
Largest Contentful Paint:      4.8 seconds
Interaction to Next Paint:     680 milliseconds
Cumulative Layout Shift:      0.24
```

A customer experiences something like this:

They open the website. The navigation bar appears.

Then a loading skeleton. Several seconds later, a large hotel photograph materializes.

They try opening the filters. The interface hesitates.

Then, just as they're about to click a hotel, an advertisement loads above the results and pushes everything downward. They click the wrong hotel.

The servers are fast. The website is miserable.

How can both be true? Because **software performance isn't one number**.

Different operations consume different resources, and different delays produce different experiences. A fast backend does not guarantee fast rendering.

A fast initial render does not guarantee responsive interactions. And a responsive page can still be maddening if its layout moves underneath the user's finger.

This session is about understanding performance as the customer actually experiences it. Not as an impressive-looking benchmark in an engineering dashboard.

---

# 2. Performance Is a Chain of Dependencies

In previous sessions, we've studied the major components of a web application. We can now put them together:

```text
User opens website
        │
        ▼
DNS, connection, TLS
        │
        ▼
HTTP request and response
        │
        ▼
HTML parsing
        │
        ▼
Download critical resources
        │
        ▼
Execute JavaScript
        │
        ▼
Render meaningful content
        │
        ▼
Respond to interactions
```

This diagram is simplified. Many operations can overlap. But the distinction between parallel and sequential work is essential.

Imagine our initial loading sequence:

```text
HTML                 200 ms
JavaScript           500 ms
Application startup  300 ms
Hotel API            250 ms
Rendering            150 ms
```

If every operation depends on the previous one, the customer waits approximately:

```text
200 + 500 + 300 + 250 + 150 = 1400 ms
```

Now suppose we reorganize the system so that JavaScript loading and some data fetching can overlap.

Or perhaps the initial HTML already contains useful hotel information.

We might substantially reduce elapsed loading time without making any individual operation faster. This is a crucial concept from performance engineering:

**The critical path determines how soon a particular result can be produced.**

The critical path is the longest chain of dependent work leading to the result we care about.

Optimizing something outside that path may have almost no effect on the result's completion time. Consider two resources:

**Resource A:** A 1 MB photograph displayed near the bottom of a page.

**Resource B:** A 100 KB JavaScript file required before the booking interface can initialize.

Making Resource A download twice as fast may improve total network activity.

But if the user doesn't see that photograph until much later, the initial experience might barely change.

Optimizing Resource B may produce a much greater improvement. The correct target depends on what the user needs and when.

This is why performance work should begin with measurement rather than a collection of fashionable optimization tricks.

---

# 3. Core Web Vitals: Three Different Ways to Make Users Miserable

Google's Core Web Vitals provide three standardized measurements of important aspects of page experience.

They don't describe every dimension of application performance. But they're excellent starting points because they correspond to distinct user-visible problems.

| Metric | Measures | Good threshold |
|---|---|---|
| **LCP** — Largest Contentful Paint | Loading of prominent content | ≤ 2.5 seconds |
| **INP** — Interaction to Next Paint | Responsiveness to interactions | ≤ 200 milliseconds |
| **CLS** — Cumulative Layout Shift | Unexpected visual movement | ≤ 0.1 |

These thresholds are evaluated using the 75th percentile of real page visits, with mobile and desktop assessed separately.

Let's understand what that actually means.

## 3.1 LCP: When does the important content appear?

Suppose our hotel page displays:

```text
┌─────────────────────────────────────┐
│ Hotel Alexander                     │
├─────────────────────────────────────┤
│                                     │
│          LARGE HOTEL PHOTO          │
│                                     │
├─────────────────────────────────────┤
│ €149 / night                        │
│ Reserve Now                         │
└─────────────────────────────────────┘
```

The photograph occupies a substantial part of the visible screen. It may become the page's Largest Contentful Paint candidate.

LCP measures when the largest qualifying image, text block, or video content visible within the viewport is rendered. Notice what it doesn't measure.

It doesn't necessarily tell us when every resource finishes downloading. It doesn't guarantee the application is interactive.

And it doesn't guarantee that the displayed information is up to date. It focuses on when prominent content appears.

A good LCP is 2.5 seconds or less. Above 4 seconds is considered poor.

## 3.2 INP: Does the page actually respond?

Suppose the customer clicks:

```text
Show Filters
```

Nothing happens for 600 milliseconds. Then the panel opens.

The network might be idle. The backend might not be involved.

But the customer has experienced an unresponsive interface.

**Interaction to Next Paint**, or INP, measures the delay from a qualifying user interaction until the browser can present the next frame reflecting its processing.

It considers interactions such as clicks, taps, and keyboard input.

Unlike the older First Input Delay metric, INP evaluates responsiveness throughout the page visit, not merely the first interaction.

For most page visits, the worst observed interaction contributes to the final INP value, with an outlier adjustment for pages containing large numbers of interactions.

A good INP is 200 milliseconds or less. Above 500 milliseconds is poor.

## 3.3 CLS: Does the interface stay where it belongs?

Imagine the user preparing to click:

```text
Reserve Room
```

At the last moment, a promotional banner appears above the button. Everything shifts downward.

The user accidentally clicks something else. That's an unexpected layout shift.

CLS measures visual instability caused by unexpected changes in the positions of visible elements. The score is unitless.

A good CLS is 0.1 or less. Above 0.25 is poor.

Modern CLS scoring uses the largest qualifying burst of layout shifts rather than simply adding every shift throughout an arbitrarily long page visit.

The distinction matters for long-lived applications. Now let's investigate each of these problems mechanistically.

---

# 4. LCP: Where Four Seconds Disappear

Our hotel-booking website has:

```text
LCP: 4.8 seconds
```

The backend API takes only 68 milliseconds. Where is the delay?

We need to break LCP into more useful components. For an image-based LCP, a common decomposition is:

1. Time to First Byte.
2. Resource load delay.
3. Resource load duration.
4. Element render delay.

Let's examine a hypothetical case.

| Phase | Duration |
|---|---:|
| TTFB | 500 ms |
| Resource load delay | 1,300 ms |
| Resource load duration | 1,100 ms |
| Element render delay | 1,900 ms |
| **Total LCP** | **4,800 ms** |

These durations describe consecutive portions of this hypothetical LCP timeline. The image takes 1.1 seconds to download.

But the browser spends 1.3 seconds before even beginning that download.

And after the resource arrives, another 1.9 seconds pass before it is rendered as the LCP element. That's where the really interesting problems are.

## 4.1 TTFB: Before the HTML arrives

We covered Time to First Byte in CS230-L01. It can include connection setup, redirects, network travel, intermediary processing, and server response generation.

Suppose our TTFB is 500 milliseconds. Can we improve it?

Perhaps. Maybe the HTML comes from a distant origin.

Maybe the application waits on slow server-side dependencies. Maybe an unnecessary redirect introduces another round trip.

But even reducing TTFB to 200 milliseconds would save only 300 milliseconds in this example. Useful, but nowhere near enough to solve the entire problem.

We need to examine the other phases.

## 4.2 Resource load delay: Why didn't the browser start sooner?

Imagine the hotel photograph is inserted by JavaScript:

```typescript
const hotel = await fetchHotelDetails();

heroImage.value = hotel.mainImageUrl;
```

The browser cannot discover the photograph's URL until the application retrieves and processes the hotel data. The dependency chain might be:

```text
Download HTML
       │
       ▼
Download JavaScript
       │
       ▼
Initialize Vue
       │
       ▼
Fetch hotel data
       │
       ▼
Discover image URL
       │
       ▼
Start image download
```

The photograph might be hosted on a blazing-fast CDN. But the browser cannot download a resource it doesn't know exists.

That is **resource discovery delay**. One possible architectural improvement is to make the important resource discoverable earlier.

For example, server-rendered HTML could contain:

```html
<img
  src="/images/hotel-alexander.avif"
  width="1200"
  height="800"
  alt="Hotel Alexander"
  fetchpriority="high"
>
```

Now the browser can discover the image while parsing the initial HTML. The `fetchpriority="high"` attribute provides a priority hint.

It doesn't guarantee a particular scheduling outcome, but it can help indicate that this resource deserves attention.

If the image can't appear directly in the initial HTML, a carefully configured preload may help:

```html
<link
  rel="preload"
  as="image"
  href="/images/hotel-alexander.avif"
  fetchpriority="high"
>
```

But don't blindly preload every image. Preloading unnecessary resources can compete with genuinely important ones.

The objective is to prioritize the actual critical resource.

## 4.3 Resource load duration: Transferring the image

Now suppose the image download itself takes 1.1 seconds. Several factors may matter:

- The number of transferred bytes.
- Available bandwidth.
- Network congestion.
- Compression format.
- CDN placement.
- Connection reuse.
- Competing downloads.

A 3 MB JPEG displayed at 600 pixels wide is a suspicious candidate for optimization. The browser may not need that much image data.

You could provide appropriately sized responsive images:

```html
<img
  src="/images/hotel-800.avif"
  srcset="
    /images/hotel-400.avif 400w,
    /images/hotel-800.avif 800w,
    /images/hotel-1200.avif 1200w
  "
  sizes="(max-width: 700px) 100vw, 600px"
  width="1200"
  height="800"
  alt="Hotel Alexander"
>
```

The browser can choose a suitable candidate based on layout and device characteristics.

Modern image formats such as AVIF and WebP may offer substantial savings compared with older alternatives, depending on image content and encoding settings.

But image compression isn't the entire story. If the browser waits two seconds before requesting a small image, compression alone won't solve the main problem.

## 4.4 Element render delay: The resource is here, but the pixels aren't

Now for the strangest part. The image has finished downloading.

Why would it take another 1.9 seconds to appear? Several explanations are possible.

Perhaps the application hasn't finished initializing. Perhaps the image is hidden until another asynchronous operation completes.

Perhaps the main thread is executing expensive JavaScript. Perhaps a component waits for several unrelated dependencies before rendering the image.

Or perhaps styles and layout work delay the final rendering opportunity. Consider:

```typescript
const [hotel, reviews, recommendations] =
  await Promise.all([
    fetchHotel(),
    fetchReviews(),
    fetchRecommendations()
  ]);

pageReady.value = true;
```

Suppose the hotel information arrives quickly. Reviews take much longer.

The UI waits for all three requests before showing the hotel page.

That's a poor dependency decision if reviews and recommendations aren't required for the initial display.

A better design may render hotel details as soon as they become available and fill in nonessential sections afterward. The central lesson:

**LCP can be delayed by resource loading, but it can also be delayed by the application refusing or failing to render content it already possesses.**

This distinction prevents a lot of wasted optimization effort.

---

# 5. The Network Waterfall: Read the Dependencies, Not Just the Colors

Open Chrome DevTools and visit the Network panel. You'll see a waterfall of requests.

It might resemble:

```text
Time →  0       500      1000      1500      2000 ms

HTML       █████
CSS            ███████
Main JS        █████████████
API                        ███████
Hero image                       ███████████
Font              ███████
Analytics            ████████████████
```

This is a conceptual diagram rather than a precise browser trace. The important information is not merely how long each bar is.

It's **when the request begins and what caused it to begin then**. Suppose the hero image begins downloading at 1,500 milliseconds.

Why? Was it discovered in the initial HTML?

Did JavaScript insert it later? Was it referenced by a stylesheet that loaded late?

Was its priority too low? Did another resource monopolize a constrained connection?

Was it accidentally marked for lazy loading even though it appears immediately in the viewport? These questions matter more than the total number of requests.

## 5.1 Not all bytes are equal

Suppose your page downloads:

```text
Main JavaScript:        250 KB
Analytics library:      180 KB
Below-fold photographs: 2 MB
Critical stylesheet:     30 KB
```

The 2 MB of photographs look like the obvious target. But perhaps they're correctly lazy-loaded and don't affect the initial experience.

Meanwhile, the analytics library runs expensive JavaScript during startup. Or the stylesheet is discovered late and delays rendering.

An optimization that removes 1 MB from irrelevant below-the-fold resources may be less valuable than removing 50 KB from the critical JavaScript path.

**Performance optimization is about the timing and consequences of work, not merely its quantity.**

---

# 6. INP: When JavaScript Steals the User's Time

Our page has:

```text
INP: 680 milliseconds
```

A customer clicks the filters button. The interface responds more than half a second later.

Let's break down one slow interaction. INP can be understood through three components:

```text
User interacts
      │
      ▼
Input Delay
      │
      ▼
Event Handler Processing
      │
      ▼
Presentation Delay
      │
      ▼
Next Frame
```

Suppose:

| Phase | Duration |
|---|---:|
| Input delay | 250 ms |
| Event processing | 180 ms |
| Presentation delay | 250 ms |
| **Total** | **680 ms** |

What does each part mean?

## 6.1 Input delay: The browser was busy

The customer clicked. But the main thread was occupied by something else.

Perhaps a third-party analytics library was initializing. Perhaps the application was rendering thousands of hotel cards.

Perhaps an unrelated callback was performing expensive synchronous computation. The click event had to wait before its handler could run.

This is input delay. The offending work doesn't necessarily belong to the clicked component.

That's an important diagnostic clue. A slow filters button may actually be caused by completely unrelated JavaScript executing on the same main thread.

## 6.2 Processing duration: The handler does too much

Now the browser starts executing the click handler. Consider:

```typescript
function openFilters() {
  filtersOpen.value = true;

  const result = expensiveHotelAnalysis(allHotels);

  analytics.value = result;
}
```

The first statement changes reactive state. But the expensive analysis runs synchronously.

The browser doesn't ordinarily paint the updated interface in the middle of the callback.

So even though `filtersOpen` becomes true immediately, the user may not see the panel open until the calculation finishes.

The solution could involve separating work into smaller tasks, deferring nonessential computation, or moving CPU-intensive processing into a Web Worker.

But merely wrapping the calculation in an `async` function isn't sufficient.

We established in SE240-L01 that asynchronous syntax doesn't magically move CPU work off the main thread.

## 6.3 Presentation delay: JavaScript finished, but rendering didn't

Even after the event handlers finish, the browser may need to perform style calculations, layout, painting, and compositing before showing the next frame.

Suppose clicking the filter button causes 5,000 hotel cards to change dimensions. The JavaScript handler might finish quickly.

But the browser now has a substantial rendering workload. The interaction remains slow.

This is why INP isn't simply a measurement of JavaScript event-handler duration. It captures the delay until the browser can present the next frame.

## 6.4 Yielding to the browser

Sometimes the expensive work cannot be eliminated entirely. But it may not need to happen in one uninterrupted task.

Consider:

```typescript
async function processHotels(hotels: Hotel[]) {
  for (let i = 0; i < hotels.length; i += 100) {
    processBatch(hotels.slice(i, i + 100));

    await new Promise<void>(resolve => {
      setTimeout(resolve, 0);
    });
  }
}
```

This is a simplified example of breaking computation into chunks and yielding through later tasks.

The browser gets opportunities to handle other work between batches. But chunk size, scheduling overhead, and task priorities matter.

Modern browsers also provide scheduling capabilities such as `scheduler.yield()` in supported environments.

A Web Worker may be preferable when the calculation is large and independent of the DOM.

And remember: yielding to the event loop doesn't make the total computation free. It may improve responsiveness by distributing the work across time.

That's often exactly what the user needs.

---

# 7. CLS: The Button That Escaped Under the Customer's Finger

Now for the third problem. Our hotel page has:

```text
CLS: 0.24
```

The customer is scrolling through search results. They spot a promising room.

As they're about to click it, an image loads above the button and pushes the entire page downward. This is not a network-latency problem.

It's a geometry problem.

## 7.1 How layout shifts happen

Consider:

```html
<img src="/hotel.jpg" alt="Hotel">
```

The browser doesn't necessarily know how much vertical space the image should occupy before its dimensions or layout constraints become known.

If the page initially reserves little or no space, surrounding elements may shift when the image loads. A better implementation can provide dimensions:

```html
<img
  src="/hotel.jpg"
  width="1200"
  height="800"
  alt="Hotel"
>
```

The browser can infer the image's aspect ratio before the resource finishes loading. CSS can then size the image responsively:

```css
.hotel-image {
  width: 100%;
  height: auto;
}
```

This helps preserve layout geometry.

## 7.2 Other common causes

Images aren't the only culprit. Unexpected shifts can come from:

- Advertisements inserted without reserved space.
- Banners appearing above existing content.
- Fonts swapping and changing text dimensions.
- Dynamically inserted recommendations.
- Late-loading widgets.
- Components changing height after asynchronous data arrives.

Imagine a reservation page initially displaying:

```text
Price: €149
```

Then, after another API request:

```text
Price: €149
Taxes and fees: €47
Total: €196
```

If the newly inserted content pushes the confirmation button downward, the user experiences a shift.

A better design might reserve enough space for the eventual pricing summary or structure the loading state so geometry remains stable.

## 7.3 Not every movement counts as an unexpected layout shift

Some movement is intentional. When a user opens an accordion, they expect the content below it to move.

CLS excludes certain shifts occurring shortly after qualifying user input, provided they meet the metric's conditions.

But delayed changes can still count as unexpected.

For example, a button click that triggers a network request and causes content to jump two seconds later may contribute to CLS.

The user may have initiated the operation, but the late shift is not necessarily treated as expected.

CSS transform-based animations also differ from layout-changing movement because transforms don't ordinarily alter the positions of surrounding layout boxes.

The important product principle is:

**The interface should not surprise users by moving interactive targets while they're trying to use them.**

A stable layout isn't merely aesthetic. It prevents mistakes.

---

# 8. Lab Performance Versus Real User Performance

Now imagine you've optimized the application on your powerful desktop computer. Chrome DevTools reports:

```text
LCP: 1.4 seconds
INP: 75 milliseconds
CLS: 0.02
```

Excellent. Then you check real-user measurements.

Many mobile users still experience poor performance. What's going on?

The laboratory and the real world are different environments.

## 8.1 Laboratory measurements

A **lab test** runs the application under controlled conditions. Tools such as Lighthouse and Chrome's Performance panel are useful here.

You can configure network and CPU throttling, reproduce workflows, record detailed timelines, and compare implementations.

This makes lab testing excellent for diagnosis and regression testing. But one lab run represents one particular environment and execution.

It cannot capture every real user experience.

## 8.2 Field measurements

**Real User Monitoring**, or RUM, collects measurements from actual browser visits.

This can reveal how an application performs across:

- Different devices.
- Network conditions.
- Geographical regions.
- Browser configurations.
- Page types.
- User workflows.

For example:

```text
High-end desktop users:
LCP p75 = 1.5 seconds

Midrange mobile users:
LCP p75 = 3.8 seconds
```

Now the problem becomes clearer. The application isn't universally slow.

It's slow under particular conditions. Perhaps weaker mobile CPUs struggle with JavaScript startup.

Perhaps the initial payload is too large for constrained mobile networks. Perhaps the viewport causes different imagery or layout behavior.

The distinction matters because optimizing only for the development team's machines can hide the actual customer experience.

## 8.3 Why percentiles matter

Suppose your production measurements show:

```text
LCP average:   2.1 seconds
LCP p50:       1.5 seconds
LCP p75:       2.8 seconds
LCP p95:       5.4 seconds
```

The average looks respectable. But 25% of measured visits take approximately 2.8 seconds or longer.

And the slowest 5% are experiencing much worse delays. This is why Core Web Vitals use the 75th percentile rather than simply evaluating average values.

A useful way to understand p75:

> Approximately 75% of observations are at or below this value, and approximately 25% are above it.

When evaluating Core Web Vitals, mobile and desktop performance should be considered separately.

Aggregating everything into one global average can hide major differences between user populations.

---

# 9. How to Measure Performance Without Fooling Yourself

Let's build a practical investigation strategy. You have three kinds of evidence.

## 9.1 Network timing

Chrome DevTools → Network. This tells you about:

- Request initiation.
- Resource discovery.
- Download durations.
- Connection-related timing.
- Resource sizes.
- Caching behavior.
- Request dependencies.

Use it when you suspect loading problems.

## 9.2 Main-thread and rendering activity

Chrome DevTools → Performance. Record the slow interaction.

Inspect:

- JavaScript execution.
- Long tasks.
- Event handling.
- Style recalculation.
- Layout.
- Painting.
- Interaction timing.
- Layout shifts.

Use it when the interface freezes, stutters, or responds slowly.

## 9.3 Field telemetry

You can collect Core Web Vitals using the maintained `web-vitals` library. For example:

```typescript
import {
  onLCP,
  onINP,
  onCLS
} from "web-vitals";

onLCP(metric => {
  console.log("LCP:", metric.value);
});

onINP(metric => {
  console.log("INP:", metric.value);
});

onCLS(metric => {
  console.log("CLS:", metric.value);
});
```

In a production application, you'd send measurements to your telemetry system rather than merely logging them.

You'd also want useful context, such as page category, device class, release version, and relevant performance attribution information.

Take care not to include sensitive customer data in performance telemetry.

Note that INP may be unavailable for page visits without qualifying interactions. The metric is not simply generated at page load.

You can also consult the Chrome User Experience Report, or CrUX, for eligible public sites with sufficient real-user data. A useful distinction:

**Lab testing helps explain why something is slow.**

**Field monitoring helps establish whether real users are experiencing that slowness and how widely.**

The strongest performance investigations combine both.

---

# 10. The Optimization Trap: Improving the Wrong Thing

Suppose your team discovers:

```text
LCP: 4.8 seconds
INP: 680 ms
CLS: 0.24
```

A developer proposes compressing every image. Another proposes migrating from Vue to React.

A third suggests increasing the Node.js server's CPU allocation. Someone else wants to add Redis.

Every suggestion could conceivably help a particular system. But none is justified by these three measurements alone.

Let's look at what a serious investigation might reveal.

### The LCP problem

The main hotel photograph is discovered 1.3 seconds late because the page waits for client-side initialization. The image is then downloaded.

Afterward, a large synchronous JavaScript task delays rendering.

The highest-value changes may be to expose important content earlier and reduce or defer blocking startup work.

### The INP problem

Opening filters causes Vue to update thousands of hotel cards and the browser to perform substantial layout work.

Virtualizing the results list or reducing the affected DOM work may help. Changing the backend database has nothing to do with the bottleneck.

### The CLS problem

A promotional banner loads asynchronously without reserved layout space.

Reserve a stable area for the banner or present it without displacing critical content unexpectedly. No complex algorithm required.

Three metrics. Three different mechanisms.

Three different solutions. This is why performance engineering is primarily a diagnostic discipline.

Not a contest to demonstrate how many optimization techniques you know.

---

# 11. Performance Budgets: Preventing Tomorrow's Regression

Imagine you fix the hotel-booking platform. The results improve:

```text
LCP: 2.1 seconds
INP: 145 ms
CLS: 0.05
```

Excellent. Then the marketing team introduces a large tracking library.

The design team adds an animated hero section. Another feature introduces a substantial charting dependency.

Six months later, the website is slow again. How do you prevent performance from gradually deteriorating?

One useful technique is a **performance budget**. A performance budget establishes limits or objectives for measurable aspects of an application.

For example:

```text
Initial JavaScript transfer:   ≤ 250 KB
Critical CSS transfer:        ≤ 50 KB
Mobile LCP p75:               ≤ 2.5 s
Mobile INP p75:               ≤ 200 ms
CLS p75:                      ≤ 0.1
```

These are illustrative budgets, not universal recommendations for every application.

A large, sophisticated dashboard may have different constraints from a public landing page.

The important thing is to make performance an explicit engineering requirement.

## 11.1 Asset budgets and experience budgets

Asset budgets are relatively straightforward to automate. A CI pipeline can detect when a production bundle grows substantially.

But asset size alone is an imperfect proxy for user experience. A small application can still perform expensive synchronous calculations.

A larger application can sometimes remain highly responsive if code is loaded and executed intelligently. So performance budgets should include both:

**Technical resource budgets**, such as initial JavaScript size.

**User-experience objectives**, such as LCP, INP, and CLS.

The first category helps prevent obvious regressions during development. The second ensures the optimization work actually improves the product.

## 11.2 Don't worship a perfect score

Lighthouse can generate a performance score. That's useful.

But the purpose of software engineering isn't to produce a beautiful green circle in a report.

A booking platform that scores well on initial loading but fails to respond correctly during checkout is not a great application.

Likewise, reducing an image's quality until hotel photographs look terrible may technically improve loading metrics while harming the actual product.

Performance is one quality attribute among several.

It must be balanced against correctness, usability, accessibility, maintainability, and business requirements.

The objective is not to minimize every millisecond at any cost. It's to deliver a reliably good experience with reasonable engineering effort.

---

# 12. Practical Lab — Investigating a Real Page

Here's a focused investigation you can perform using Chrome. You don't need to create a new application.

Choose a website you visit regularly or an existing project you control.

## Experiment A — Find the LCP element

Open Chrome DevTools. Navigate to the Performance panel.

Record a page load. Identify the LCP event and associated element.

Ask:

1. Which element became LCP?
2. When did its resource begin loading, if it needed one?
3. Was the resource discoverable from the initial HTML?
4. Did it finish downloading long before it rendered?

Now inspect the Network panel. Try to identify the critical dependency chain.

Don't simply count requests. Look for sequential delays.

## Experiment B — Simulate a weaker device

Use appropriate CPU and network throttling in DevTools. Reload the page.

Compare the timeline against your normal desktop experience. Which phases become more expensive?

If JavaScript execution grows dramatically while network timing changes little, CPU capability may be a major factor.

If downloads dominate, resource loading deserves more attention.

Remember that software throttling approximates constrained conditions; it isn't identical to testing on an actual midrange phone.

## Experiment C — Record a slow interaction

Open a page with a substantial interactive component. Start a Performance recording.

Change a filter, open a large menu, or sort a table. Stop the recording.

Inspect the interaction and main-thread work. Determine whether the delay came primarily from:

- Waiting to process input.
- JavaScript callbacks.
- Layout and rendering.

Now imagine how you'd optimize each different cause. The solutions should differ.

## Experiment D — Observe layout shifts

In the Performance panel, inspect the Layout Shifts track if the page produces any shifts. Identify the elements that moved and what caused the movement.

Was space reserved for images? Did an asynchronously loaded component change the page's geometry?

Did a font change text dimensions? Try to understand the causal chain instead of simply observing the final CLS score.

---

# 13. Engineering and Interview Challenges

### Challenge 1 — The Fast Backend

Your backend processes requests in 40 milliseconds. But the page's LCP is 4.5 seconds.

Name at least four mechanisms outside backend execution that could explain the result.

### Challenge 2 — The Giant Image

A page contains a 3 MB hero photograph. A developer compresses it to 300 KB.

The LCP improves only slightly. What might explain the disappointing result?

### Challenge 3 — The Frozen Button

A button's event handler runs for only 5 milliseconds. Yet INP is 600 milliseconds.

How is that possible? What would you investigate?

### Challenge 4 — The Jumping Page

A hotel-search page inserts recommendation cards above the results after an API response arrives. The user experiences significant layout shifts.

How could you reduce CLS without removing recommendations?

### Challenge 5 — The Impressive Laptop

Your development laptop produces an excellent performance score. Real mobile users consistently experience poor responsiveness.

Why might the results differ? How would you investigate the discrepancy?

---

# 14. Solutions and Discussion

**Challenge 1**

Possible causes include high network RTT, slow connection establishment, delayed discovery of critical resources, expensive JavaScript initialization, large asset transfers, late API requests, and delayed browser rendering.

TTFB and backend processing time are not equivalent to LCP. You need a browser-centered performance trace to determine which stages are responsible.

**Challenge 2**

Perhaps the photograph wasn't requested until late in the loading sequence.

Perhaps the browser finished downloading it but couldn't render it because JavaScript occupied the main thread.

Perhaps another dependency prevented the image from being displayed. Reducing download duration helps only the portion of LCP attributable to that transfer.

**Challenge 3**

The event handler may have waited behind another long main-thread task.

Or the browser may have required substantial style, layout, and painting work after the handler completed.

INP includes input delay, event processing, and presentation delay. A short handler doesn't guarantee a fast interaction.

**Challenge 4**

Reserve appropriate layout space before recommendations load.

You could display placeholders with predictable dimensions, place recommendations in a region that doesn't unexpectedly displace the active results, or otherwise maintain stable geometry.

The precise design depends on the interface, but the goal is to prevent late content from moving interactive elements unexpectedly.

**Challenge 5**

Mobile devices often have substantially less CPU capacity, different memory constraints, different viewport dimensions, and less reliable network conditions.

Field measurements reveal the actual distribution of customer experiences.

I would segment the data by device and page type, inspect slow interactions, and attempt to reproduce the relevant conditions in a lab.

Optimizing only against a high-end development computer is not sufficient.

---

# 15. The Mental Model Worth Keeping

Web performance is not one measurement.

It's the combined result of networking, resource discovery, browser execution, rendering, scheduling, and application architecture.

The most important principles are:

**The critical path determines when useful results become available.** Optimizing work outside that path may provide little visible benefit.

**LCP measures prominent content loading.** Delays can occur before a resource downloads, during its transfer, or after it arrives.

**INP measures responsiveness.** Slow interactions can result from a blocked main thread, expensive handlers, or rendering work.

**CLS measures visual stability.** Late content and unexpected changes in geometry can make an otherwise fast page frustrating to use.

**Field and laboratory measurements answer different questions.** Real users establish the actual experience; controlled tests help identify causes.

**Optimization should follow evidence.** Smaller bundles, faster databases, CDNs, Web Workers, and caching are tools—not universal solutions.

And the principle that should guide every serious performance investigation:

**Don't optimize the operation that looks slow in isolation. Identify the dependency that actually delays the customer's experience.**

A 50-millisecond improvement can be transformative if it removes an important sequential bottleneck.

A 500-millisecond improvement can be nearly invisible if it happens after the user already has everything they need.

Performance engineering is the art of understanding that difference.

---

# 16. Next Session — Testing and Reliability in the Frontend

Now imagine you've optimized the application. It loads quickly.

Interactions are responsive. The interface stays stable.

And your test suite contains 1,200 passing tests.

Then a customer opens the booking page, changes the date, clicks Reserve, and receives a confirmation for the wrong dates. How?

The unit tests passed. The components rendered correctly.

The mocked API returned valid data. The build succeeded.

But the actual interaction crossed several application boundaries—and the tests never exercised them together.

In **SE240-L06 — Testing and Reliability in the Frontend**, we'll investigate unit tests, component tests, integration tests, end-to-end tests, browser compatibility, accessibility, flaky tests, and the limitations of mocking.

The central mystery:

**How can a frontend have nearly perfect test coverage and still fail during ordinary user interaction?**

---


---

## Next Lecture — SE240-L06: Testing and Reliability in the Frontend

Continue in **SE240 — Browser and Frontend Engineering**.

## Further Reading — Optional References

1. [web.dev — Web Vitals](https://web.dev/articles/vitals) — Core Web Vitals and recommended thresholds.
2. [web.dev — Optimize Largest Contentful Paint](https://web.dev/articles/optimize-lcp) — LCP breakdown, resource discovery, and rendering delays.
3. [web.dev — Interaction to Next Paint](https://web.dev/articles/inp) — Responsiveness and interaction measurement.
4. [web.dev — Cumulative Layout Shift](https://web.dev/articles/cls) — Visual stability and layout shift scoring.
5. [Chrome DevTools — Performance](https://developer.chrome.com/docs/devtools/performance/) — Recording and analyzing performance traces.
6. [web.dev — Debug Performance in the Field](https://web.dev/articles/debug-performance-in-the-field) — Connecting real-user measurements to root causes.
7. [web-vitals Library](https://github.com/GoogleChrome/web-vitals) — Collecting Core Web Vitals in production.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE240-L05  PERFORMANCE: WHY FAST CODE CAN FEEL SLOW — INTERVIEW GLANCE CARD

CORE INSIGHT
  Fast APIs ≠ good UX  Backend 68 ms; users still see LCP 4.8s / INP 680ms / CLS 0.24
  Critical path        Longest dependent chain to the result that matters
  Optimize off-path    May barely change what the user experiences

CORE WEB VITALS (p75; mobile & desktop separate)
  Metric   Measures                         Good / Poor
  LCP      Prominent content paint          ≤2.5s / >4s
  INP      Interaction → next paint         ≤200ms / >500ms (whole visit, not FID)
  CLS      Unexpected layout movement       ≤0.1 / >0.25 (largest burst)

LCP BREAKDOWN (image example)
  TTFB | resource discovery delay | transfer | element render delay
  Discovery trap  Image URL only after HTML→JS→Vue→fetch hotel → late start
  Fix discovery   SSR/HTML <img> or careful preload + fetchpriority=high
  Transfer        Right-sized responsive images; AVIF/WebP; CDN — only helps transfer phase
  Render delay    Waiting on unrelated Promise.all; main-thread JS; hidden until ready
  Lesson          LCP delayed by load OR by app refusing to paint what it already has

NETWORK WATERFALL
  Read            When request starts and why — not only bar length
  Bytes ≠ equal   Below-fold 2MB lazy may matter less than 50KB on critical JS path

INP BREAKDOWN
  Input delay     Main thread busy (unrelated JS / render) before handler runs
  Processing      Handler does sync expensive work before paint can happen
  Presentation    Style/layout/paint after handlers (e.g. 5k cards resize)
  Yield           Chunk work + setTimeout(0) / scheduler.yield; Worker if DOM-independent
  async ≠ off-thread  (SE240-L01)

CLS
  Causes          Images without dimensions; ads/banners; font swap; late widgets/API inserts
  Fix             width/height or aspect-ratio space; stable placeholders; don't shove targets
  Not all motion  Accordion after user input may be excluded; late shift after click can still count
  Transforms      Often don't move surrounding layout boxes like geometry changes

LAB vs FIELD
  Lab             Lighthouse / Performance — diagnose & regress under control
  RUM / field     Real devices/networks; web-vitals onLCP/onINP/onCLS; CrUX if eligible
  Percentiles     Prefer p75 over averages; segment mobile vs desktop
  Tools           Network (discovery) · Performance (long tasks, layout, INP) · field telemetry

OPTIMIZATION TRAP
  Three metrics → three mechanisms (discovery+JS / DOM+layout / reserved space)
  Don't migrate frameworks or add Redis from CWV alone — diagnose first

PERFORMANCE BUDGETS
  Asset budgets   e.g. initial JS ≤250KB (illustrative)
  Experience      Mobile LCP/INP/CLS objectives
  Balance         Correctness, a11y, UX, maintainability — not worship Lighthouse score

SENIOR LINE: Don't optimize the slow-looking op—find the dependency that delays the customer.
```

