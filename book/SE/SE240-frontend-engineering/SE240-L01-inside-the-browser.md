---
id: SE240-L01
course: SE240
title: "Inside the Browser"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S04]
prev: null
next: SE240-L02
---







# SE240 — Browser and Frontend Engineering

## Lecture 01: Inside the Browser

*How HTML, CSS, and JavaScript become pixels on a screen—and why changing one tiny property can bring an entire application to its knees.*

---

# 1. The Case of the Frozen Hotel Search

Your hotel-booking application has grown considerably. It now supports searching through thousands of hotels, comparing prices, filtering amenities, and displaying availability information.

The backend is performing beautifully. A request for 5,000 hotels takes approximately 80 milliseconds. The response is delivered quickly, and the browser has already downloaded the necessary JavaScript.

Yet there's a problem.

When a user changes the sorting option from "Recommended" to "Lowest price," the interface freezes for nearly half a second.

During that time:

- The dropdown appears unresponsive.
- The loading spinner stops animating.
- Buttons don't react immediately.
- Even typing into another input field feels broken.

Your first suspicion is Vue.

Perhaps its reactivity system is inefficient.

But then you try something interesting. You replace the Vue hotel-list component with ordinary JavaScript that manually generates thousands of DOM elements.

The interface still freezes.

You optimize the sorting algorithm. It becomes slightly faster, but the problem remains.

Then you modify the implementation so that only 30 hotels exist in the DOM at any given moment, even though the application still holds all 5,000 records in memory.

The freezing almost disappears.

What happened?

The application was not merely calculating a new list.

It was asking the browser to rebuild and visually process a substantial part of the interface. And those are very different kinds of work.

To understand why, we need to examine the browser as an execution environment—not simply as something that displays HTML.

---

# 2. The Browser Is a Small Operating Environment

When developers say "the browser executes JavaScript," they're describing only part of its responsibility.

A modern browser must simultaneously manage:

- Network requests and resource loading.
- HTML and CSS parsing.
- JavaScript execution.
- Document structure.
- Layout calculations.
- Painting and compositing.
- User input.
- Media playback.
- Storage and caching.
- Security boundaries between websites.

And it must somehow make all of this feel instantaneous.

Browsers such as Chrome and Firefox are internally complex, often using multiple processes and threads. For example, Chromium commonly separates browser-level responsibilities from rendering work performed in renderer processes. It also uses specialized infrastructure for graphics, networking, and other operations. The exact architecture varies between browsers and evolves over time.

But one distinction is particularly important for frontend developers.

**Much of the JavaScript execution and document-rendering coordination for a webpage happens on its main thread.**

That creates a potential bottleneck. If your JavaScript occupies the main thread for 500 milliseconds, the browser cannot freely execute every other main-thread task during that period. User events may have to wait, DOM updates may be delayed, and rendering opportunities may be missed.

Some operations, such as composited scrolling, can proceed on other threads under suitable circumstances, so the entire browser doesn't necessarily freeze uniformly. But the user can still experience a badly unresponsive application.

Let's trace how the browser arrives at the point where JavaScript can cause such trouble.

---

# 3. HTML: From a String to a Living Document

Suppose the browser receives this HTML:

```html
<!doctype html>
<html>
  <head>
    <title>Berlin Hotels</title>
    <link rel="stylesheet" href="/styles.css">
  </head>

  <body>
    <main>
      <h1>Hotels in Berlin</h1>
      <section id="results">
        <article class="hotel">
          <h2>Hotel Alexander</h2>
          <p>€140 per night</p>
        </article>
      </section>
    </main>
  </body>
</html>
```

The browser doesn't display this string directly. It parses the document according to HTML's rules and constructs a **Document Object Model**, or DOM.

Conceptually:

```text
Document
└── html
    ├── head
    │   ├── title
    │   └── link
    │
    └── body
        └── main
            ├── h1
            │   └── "Hotels in Berlin"
            │
            └── section#results
                └── article.hotel
                    ├── h2
                    └── p
```

The DOM consists of objects representing nodes and their relationships. JavaScript can inspect and modify these objects:

```javascript
const heading = document.querySelector("h1");

heading.textContent = "Hotels in Copenhagen";
```

This changes the document's internal structure or content. But here's an important distinction:

**Changing the DOM does not mean the corresponding pixels have already changed on screen.**

The browser must still determine how the updated document should look and produce an appropriate rendered frame.

## 3.1 HTML parsing can begin before downloading finishes

A browser doesn't normally need to receive the entire HTML document before beginning to process it. It can parse incoming content progressively.

When it discovers resources such as:

```html
<link rel="stylesheet" href="/styles.css">
<img src="/hotel.jpg" alt="Hotel">
<script src="/application.js"></script>
```

it may initiate additional network requests. Browsers also use resource-discovery optimizations, commonly called preload scanners or speculative parsers, that can find resource references ahead of the main parser. That lets certain downloads overlap.

Rather than:

```text
Download HTML completely
        ↓
Discover CSS
        ↓
Download CSS
        ↓
Discover JavaScript
        ↓
Download JavaScript
```

the browser can often arrange overlapping work. This is one reason the structure of an HTML document and the discoverability of its critical resources affect loading performance.

## 3.2 JavaScript can interrupt the parser

Consider:

```html
<h1>Hotels</h1>

<script src="/application.js"></script>

<p>Find your perfect stay.</p>
```

A conventional synchronous external script can pause HTML parsing until the script is downloaded and executed.

Why? Because JavaScript can modify the document while the browser is constructing it. For example, historically, scripts could use `document.write()` to inject additional HTML into the parser's input stream. The browser cannot always safely continue constructing the document as though the script didn't exist.

Modern script-loading options help control this behavior.

| Script declaration | General behavior |
|---|---|
| `<script src="a.js">` | Can block HTML parsing while fetched and executed |
| `<script async src="a.js">` | Downloads asynchronously and executes when ready, without preserving relative execution order |
| `<script defer src="a.js">` | Downloads without blocking parsing; executes after parsing, before `DOMContentLoaded`, in document order |
| `<script type="module" src="a.js">` | Module scripts are deferred by default, with dependency-aware loading and execution |

These are simplified rules for ordinary document scripts. Features such as top-level `await` add further details.

For a modern Vite application, you might encounter:

```html
<script type="module" src="/src/main.ts"></script>
```

During development, the browser loads the module graph through Vite's development server. In production, the build typically supplies generated JavaScript assets. The browser eventually executes the code that initializes the Vue application.

But before the user sees the finished interface, another entire system needs to do its work.

CSS.

---

# 4. CSS: From Rules to Geometry

Let's imagine our hotel card uses:

```css
.hotel {
  display: flex;
  width: 600px;
  padding: 20px;
  background: white;
  border-radius: 12px;
}

.hotel h2 {
  font-size: 24px;
}
```

The browser parses CSS and builds an internal representation of stylesheet rules, often discussed as the **CSS Object Model**, or CSSOM. It then determines which styles apply to which elements. This involves the cascade, inheritance, specificity, and other CSS mechanisms.

But the final visual result isn't produced simply by attaching one CSS rule to one DOM node. The browser needs to resolve the combined effect of all applicable rules.

Consider:

```css
h2 {
  color: black;
}

.hotel h2 {
  color: blue;
}

.featured h2 {
  color: red;
}
```

Which color wins?

That depends on the cascade, including rule origins, importance, specificity, and source order. The browser needs to calculate the resulting style for the element. Then it needs to determine the element's actual dimensions and position. Those are separate tasks.

## 4.1 The DOM is not the layout tree

This distinction is extremely useful. The DOM represents document structure. The structures used for layout and rendering represent the boxes and visual relationships needed to display that document. They are not identical.

For example:

```html
<div style="display: none">
  You cannot see me.
</div>
```

The element exists in the DOM, and JavaScript can find it. But it does not generate an ordinary layout box.

Meanwhile:

```html
<div style="visibility: hidden">
  You cannot see me either.
</div>
```

still participates in layout, even though its content is not visibly painted. This explains why hiding elements can have different performance and layout consequences depending on how you hide them.

A DOM node is a document concept. A layout box is a rendering concept. They frequently correspond, but not one-to-one.

## 4.2 Layout: Solving the geometry problem

Suppose your page contains:

```html
<div class="container">
  <aside>Filters</aside>
  <main>Hotel results</main>
</div>
```

with:

```css
.container {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 24px;
}
```

The browser must determine:

- The available width of the container.
- The width of each column.
- The positions of its children.
- How text wraps.
- How tall each element becomes.
- How descendants influence their ancestors.

This process is called **layout**, historically also referred to as *reflow*. And the relationships can be surprisingly complicated.

Imagine changing the width of a sidebar.

The main content column becomes narrower. Hotel descriptions wrap onto additional lines. Cards become taller. Elements below those cards move.

A seemingly local change can affect a large region of the page.

That's why layout can be computationally expensive.

It isn't merely setting `element.x = 200`.

It's solving a set of interacting geometrical constraints.

---

# 5. The Rendering Pipeline: How Pixels Finally Appear

We can now assemble the major stages. A simplified browser rendering pipeline looks like this:

```text
HTML ─────► DOM
               │
CSS ──────► Styles
               │
               ▼
        Style Calculation
               │
               ▼
             Layout
               │
               ▼
             Paint
               │
               ▼
           Compositing
               │
               ▼
             Screen
```

This is a conceptual model. Real browser engines overlap, optimize, and sometimes skip work depending on what changed.

Let's examine the remaining stages.

## 5.1 Paint: What should be drawn?

After layout determines the geometry, the browser needs to produce visual content. This includes:

- Text glyphs.
- Backgrounds.
- Borders.
- Shadows.
- Images.
- Decorations.

Painting involves producing drawing instructions, and rasterization turns those instructions into pixel data. These operations can be split across threads and graphics infrastructure depending on the browser.

Imagine a hotel card with a photograph, a price, a shadow, and several text elements. Layout determines their sizes and positions. Painting determines what they visually contain. The two tasks are related but fundamentally different.

## 5.2 Compositing: Assembling the final picture

Modern browsers can organize visual content into composited layers. Some of these layers can be moved, transformed, or combined without repainting all their contents.

For example, imagine a panel sliding horizontally across the screen. If the browser can reuse the panel's already-rasterized content, changing its position may require comparatively little work. The compositor combines the relevant surfaces into the final visual result. This is particularly useful for animations and scrolling.

But layers aren't free. They require memory and management overhead, and creating hundreds of unnecessary composited layers can introduce problems of its own.

The practical takeaway is that different CSS changes can require dramatically different amounts of browser work.

---

# 6. Why Some CSS Changes Are Much More Expensive Than Others

Let's compare three animations.

### Animation A — Changing width

```javascript
element.style.width = "400px";
```

Changing width may affect geometry. The browser may need to recalculate layout, then paint and composite the affected content.

### Animation B — Changing background color

```javascript
element.style.backgroundColor = "red";
```

The element's geometry may remain unchanged, so layout may be unnecessary. But the element's appearance changes, so painting work is generally required.

### Animation C — Changing transform

```javascript
element.style.transform = "translateX(100px)";
```

Under suitable conditions, the browser can perform this as a compositor-only update, avoiding layout and repainting the element's contents. This is one reason `transform` and `opacity` are frequently recommended for smooth animations.

A useful simplified comparison:

| Change | Layout? | Paint? | Composite? |
|---|---|---|---|
| `width` | Usually | Usually | Usually |
| `background-color` | Usually not | Yes | Usually |
| `transform` | Usually not | Potentially avoidable | Yes |
| `opacity` | Usually not | Potentially avoidable | Yes |

These aren't absolute guarantees. Browser behavior depends on the element, rendering context, implementation, and whether compositing optimizations apply.

The underlying principle is more valuable than memorizing a particular table:

**The most efficient visual update is often the one that avoids recalculating geometry and repainting content.**

For example, animating a modal's movement using `transform` is generally preferable to repeatedly changing its `left` property when both achieve the same intended effect.

But don't start adding `will-change: transform` to every element in your application. Promotion and preallocation have costs. Optimizations should address a measured problem.

---

# 7. The 16.7-Millisecond Problem

Let's return to our hotel-search application. The user selects a sorting option, and the interface is supposed to respond smoothly.

Why does the number 16.7 milliseconds appear so often in frontend performance discussions?

Because a display refreshing at 60 Hz presents approximately 60 frames per second. The interval between refreshes is:

\[
\frac{1000\text{ ms}}{60} \approx 16.67\text{ ms}
\]

To produce a new frame for every refresh, the system needs to complete the necessary work in time. And JavaScript isn't the only thing competing for that interval. The browser may also need to perform style calculations, layout, painting, and compositor coordination. The application doesn't own the entire 16.7 milliseconds.

Now imagine a JavaScript callback that takes 180 milliseconds.

During that execution, the main thread cannot freely process the next input event or perform ordinary main-thread rendering work.

At 60 Hz, 180 milliseconds spans approximately eleven display intervals. The user may notice a conspicuous pause.

On a 120 Hz display, the interval between refreshes is about 8.3 milliseconds, making consistent high-refresh-rate animation even more demanding.

This is why frontend performance isn't merely about total computation time.

**It's also about when work happens and how long the main thread remains unavailable.**

And this brings us to the browser's event loop.

---

# 8. The Event Loop: The Browser's Scheduling Problem

You encountered event loops in the computer science foundations courses (CS110, CS220, CS320), so we won't revisit all the foundations. Instead, let's focus on what makes the browser's event loop especially interesting: it must coordinate JavaScript execution with user input and opportunities to update the rendered page.

Consider:

```javascript
button.addEventListener("click", () => {
  console.log("Clicked");
});
```

When the user clicks the button, the browser eventually dispatches the event. The listener executes as part of a task.

But what if the main thread is already executing this?

```javascript
function blockMainThread() {
  const start = performance.now();

  while (performance.now() - start < 1000) {
    // Deliberately occupy the main thread.
  }
}

blockMainThread();
```

For roughly one second, the JavaScript thread is busy.

The browser cannot simply interrupt arbitrary synchronous JavaScript execution to run your click handler.

The click may be received by the browser's input system, but dispatching and handling it on the busy main thread must wait.

This is why interfaces sometimes stop responding even though the network connection is perfectly healthy.

## 8.1 Tasks and microtasks

A useful simplified event-loop cycle is:

```text
Run a task
     │
     ▼
Run pending microtasks
     │
     ▼
Opportunity to update rendering
     │
     ▼
Continue with subsequent work
```

Real scheduling is more nuanced, and the browser doesn't necessarily render after every task. But the relationship between tasks, microtasks, and rendering is crucial.

Consider:

```javascript
console.log("A");

setTimeout(() => {
  console.log("B");
}, 0);

Promise.resolve().then(() => {
  console.log("C");
});

console.log("D");
```

The expected order is:

```text
A
D
C
B
```

Why? The synchronous statements execute first. The promise reaction runs as a microtask. The timer callback executes as a later task.

Now here's the interesting complication.

**The browser ordinarily processes the microtask queue before getting an opportunity to render.**

That means microtasks can delay painting.

## 8.2 How promises can starve rendering

Imagine this pathological code:

```javascript
function endlessMicrotasks() {
  queueMicrotask(endlessMicrotasks);
}

endlessMicrotasks();
```

Each microtask schedules another one, so the microtask queue never becomes empty.

The browser may never get an ordinary opportunity to perform its next rendering update.

This demonstrates something subtle.

Using promises or microtasks does not automatically make work non-blocking. Even if a computation is divided into many microtasks, they may still execute continuously before the browser can render.

For expensive work, yielding to a later task or using another scheduling strategy can be more appropriate.

## 8.3 `await` doesn't automatically free the browser

Consider:

```javascript
async function expensiveWork() {
  const result = calculateHugeDataset();
  return result;
}

await expensiveWork();
```

Despite the use of `async` and `await`, `calculateHugeDataset()` executes synchronously. If it blocks the main thread for 300 milliseconds, the browser still suffers that delay. The function returning a promise does not magically move its computation to another thread.

Now compare:

```javascript
const response = await fetch("/api/hotels");
```

The network operation can proceed without JavaScript continuously occupying the main thread. The function suspends while the promise is pending, and when the request completes, the continuation is scheduled. That's an entirely different situation.

**Asynchrony is not the same as parallel CPU execution.**

This distinction matters constantly in frontend engineering.

---

# 9. When Does the Browser Actually Paint?

Suppose you write:

```javascript
const status = document.querySelector("#status");

status.textContent = "Loading...";

performVeryExpensiveCalculation();

status.textContent = "Done!";
```

You might expect the user to briefly see:

```text
Loading...
```

before the calculation begins. But often they won't.

Why?

Because JavaScript runs synchronously through the entire callback.

The browser doesn't ordinarily paint between those statements. By the time it gets the opportunity to update the screen, the text has already changed to:

```text
Done!
```

The intermediate DOM state existed, but it never became a visible frame. This distinction explains a surprising number of frontend bugs. A DOM mutation isn't necessarily a rendered pixel update.

## 9.1 `requestAnimationFrame`

Browsers provide `requestAnimationFrame()` for coordinating callbacks with rendering opportunities. For example:

```javascript
function animate(timestamp) {
  element.style.transform =
    `translateX(${timestamp / 20}px)`;

  requestAnimationFrame(animate);
}

requestAnimationFrame(animate);
```

The browser invokes the callback before an upcoming repaint, subject to its scheduling rules. This is useful for visual animations because the callback cadence can align with display updates. It is generally preferable to attempting animation using an arbitrary `setInterval(..., 16)` loop.

But a `requestAnimationFrame` callback is not a license to run expensive computations. If the callback occupies the main thread for 100 milliseconds, it can still delay the frame. The goal is to prepare visual changes efficiently, not monopolize the rendering opportunity.

## 9.2 Vue's `nextTick()` is not a paint guarantee

Here's an especially relevant example.

```typescript
import { nextTick, ref } from "vue";

const loading = ref(false);

async function searchHotels() {
  loading.value = true;

  await nextTick();

  performExpensiveCalculation();

  loading.value = false;
}
```

A common misunderstanding is:

"After `nextTick()`, the browser has displayed my loading indicator."

Not necessarily. Vue's `nextTick()` waits for Vue's pending DOM update flush. That doesn't guarantee that the browser has completed a paint. The expensive calculation can still run before the screen displays the loading state.

This is an important distinction:

```text
Reactive state updated
          ≠
DOM updated
          ≠
Frame painted
```

Vue decides when to batch and apply reactive DOM updates. The browser decides when to render those updates. Understanding both schedulers is essential for diagnosing frontend responsiveness.

---

# 10. Forced Synchronous Layout: Accidentally Making the Browser Work Twice

Here's a particularly nasty performance bug. Imagine a function that resizes 1,000 elements.

```javascript
for (const element of elements) {
  element.style.width = "300px";

  const height = element.offsetHeight;

  console.log(height);
}
```

This code looks harmless. Set a width. Read a height. Repeat.

But consider what's happening. Changing an element's width may invalidate layout information. Reading `offsetHeight` asks the browser for its current geometry. To return an accurate answer, the browser may need to perform layout immediately.

Then the next iteration modifies another width, then reads another height, potentially forcing layout again.

This pattern is called **layout thrashing**.

The browser may repeatedly perform expensive geometry calculations that could otherwise have been combined.

Conceptually:

```text
Write style
    ↓
Force layout
    ↓
Write style
    ↓
Force layout
    ↓
Write style
    ↓
Force layout
```

The problem isn't that reading an element's dimensions is inherently wrong. The problem is alternating writes and layout-dependent reads in a way that prevents the browser from batching its work.

## 10.1 A better approach

When the operation permits it, group reads and writes separately.

```javascript
const heights = elements.map(
  element => element.offsetHeight
);

for (const element of elements) {
  element.style.width = "300px";
}
```

This example measures the old heights before changing widths. If you need the new heights, you may still require a layout calculation after applying the changes. But you can arrange the work so that the browser performs fewer unnecessary recalculations.

For example:

```javascript
for (const element of elements) {
  element.style.width = "300px";
}

// Read geometry after the writes have been grouped.
const newHeights = elements.map(
  element => element.offsetHeight
);
```

This can allow the browser to handle the accumulated changes more efficiently than forcing layout after every individual write.

The broader principle:

**Avoid repeatedly invalidating layout and immediately demanding fresh geometry inside a large loop.**

---

# 11. Returning to Vue: Why 5,000 Hotels Freeze the Interface

Now we can solve our original mystery. Suppose the application contains:

```vue
<template>
  <HotelCard
    v-for="hotel in sortedHotels"
    :key="hotel.id"
    :hotel="hotel"
  />
</template>
```

And each `HotelCard` contains:

- Several text elements.
- Images.
- Pricing details.
- Availability indicators.
- Buttons.
- Conditional badges.
- Nested components.

Five thousand cards might represent tens of thousands of DOM nodes.

When the sort order changes, several things may happen. First, Vue recalculates derived reactive values. Then its rendering system determines the necessary virtual-node changes. The framework updates or moves the relevant DOM elements. The browser may need to recalculate styles, layout affected content, and perform painting and compositing.

The exact cost depends on what changed and how the framework applies the update. Vue's keyed list rendering can preserve component identity and reuse existing elements when items move, so it doesn't necessarily destroy and recreate all 5,000 cards. But retaining thousands of nodes and rearranging them can still be expensive.

The bottleneck might be:

- JavaScript sorting.
- Vue's update and patching work.
- DOM operations.
- Browser layout.
- Painting.
- Or a combination of these.

This is why blaming "Vue reactivity" without profiling is premature.

## 11.1 Virtualization changes the problem

Instead of rendering all 5,000 hotels, suppose the interface renders only the visible portion plus a small buffer.

Conceptually:

```text
Application data:
5,000 hotels

Visible viewport:
20 hotel cards

Rendered DOM:
Approximately 30–40 cards
```

As the user scrolls, the application updates which items are represented in the DOM. This is known as **list virtualization** or *windowing*. The underlying dataset can remain large, but the browser doesn't need to maintain and render every card simultaneously.

Virtualization can produce dramatic improvements for very large lists.

Of course, it introduces complexities. Variable item heights require careful positioning logic.

Keyboard navigation and accessibility need attention.

Scrolling behavior and element focus must be handled correctly.

And virtualization won't automatically fix expensive computations performed over the entire dataset. But for a sufficiently large list, it can remove an enormous amount of unnecessary rendering work.

## 11.2 Not every optimization belongs in the framework

Suppose profiling shows:

```text
Sorting computation:     12 ms
Vue component updates:   45 ms
Browser layout:         180 ms
Painting:                90 ms
```

These are hypothetical measurements. Would replacing the sorting algorithm be the obvious priority?

No. The browser's visual processing is responsible for most of the delay.

Now imagine:

```text
Sorting computation:    350 ms
Vue component updates:   30 ms
Browser layout:          20 ms
Painting:                10 ms
```

That's a very different diagnosis. Perhaps the sorting computation itself needs improvement or needs to happen away from the main thread.

This brings us to one final major tool.

---

# 12. Web Workers: Moving Computation Off the Main Thread

JavaScript execution in a webpage commonly happens on its main thread. But browsers also provide **Web Workers**.

A worker executes JavaScript in a separate execution environment, typically backed by another thread. That makes it useful for CPU-intensive work.

Imagine processing a large dataset. Instead of:

```javascript
const result = expensiveAnalysis(data);
```

on the main thread, you might send the data to a worker:

```javascript
const worker = new Worker(
  new URL("./analysis-worker.js", import.meta.url),
  { type: "module" }
);

worker.postMessage(data);

worker.onmessage = event => {
  renderResults(event.data);
};
```

And inside the worker:

```javascript
self.onmessage = event => {
  const result = expensiveAnalysis(event.data);

  self.postMessage(result);
};
```

The computation can now proceed without occupying the page's main JavaScript thread. The main thread remains more available for user interactions and rendering-related work.

But workers aren't magical either.

### They cannot directly manipulate the page's DOM

A dedicated worker doesn't have ordinary direct access to the document's DOM. It computes results and communicates with the page through messages.

### Transferring data has a cost

Data sent through `postMessage()` is typically structured-cloned unless transfer mechanisms or shared-memory arrangements are used. For very large datasets, copying and communication overhead can become significant. Transferable objects can reduce some copying costs. Shared memory introduces additional complexity and security requirements.

### Workers don't solve layout problems

If your bottleneck is 5,000 DOM elements requiring expensive layout, moving a sorting function into a worker may accomplish very little. The main thread still needs to update and render the interface.

Web Workers are particularly valuable when the bottleneck is substantial CPU computation that can be separated from DOM manipulation. They're not a universal replacement for frontend performance engineering.

---

# 13. Practical Investigation: Catch the Browser in the Act

Let's perform a compact investigation using Chrome DevTools.

## Experiment A — Observe a long task

Open an ordinary webpage and execute this in the console:

```javascript
const button = document.createElement("button");

button.textContent = "Freeze the main thread";

button.onclick = () => {
  const start = performance.now();

  while (performance.now() - start < 300) {
    // Simulate heavy synchronous work.
  }
};

document.body.appendChild(button);
```

Open the Performance panel.

Start recording.

Click the button.

Stop recording.

Look for the long JavaScript task. Now examine the main-thread timeline.

The browser should show a substantial period spent executing JavaScript.

Try interacting with the page while the computation runs.

This demonstrates how a single callback can delay unrelated interactions.

## Experiment B — Trigger layout thrashing

Create a collection of elements, then compare these two approaches.

First:

```javascript
console.time("interleaved");

for (const element of elements) {
  element.style.width = "300px";
  void element.offsetHeight;
}

console.timeEnd("interleaved");
```

Then try grouping writes and reads:

```javascript
console.time("grouped");

for (const element of elements) {
  element.style.width = "350px";
}

for (const element of elements) {
  void element.offsetHeight;
}

console.timeEnd("grouped");
```

You'll need to define `elements` as a collection of real DOM elements before running the snippets. Use the Performance panel rather than relying only on `console.time()`, and look for repeated layout calculations.

The exact difference depends on the page, browser optimizations, and whether the style changes actually invalidate geometry. But the experiment illustrates how JavaScript access patterns can influence browser rendering work.

## Experiment C — Compare two animations

Create a small element. Animate its position using `left`. Then animate it using `transform: translateX(...)`.

Inspect the Performance panel. Look for:

- Layout work.
- Paint work.
- Compositing behavior.
- Frame consistency.

Don't assume the transform version will always be dramatically faster. The purpose is to discover which rendering stages are involved.

## Experiment D — Profile a real Vue application

Use Chrome's Performance panel and, where appropriate, Vue DevTools. Perform an interaction that feels slow.

Identify whether the main cost comes from:

1. JavaScript execution.
2. Component updates.
3. Layout.
4. Paint.
5. Network waits.

Only then decide whether you need to optimize computation, reduce DOM complexity, virtualize lists, improve CSS behavior, or restructure data loading.

This diagnostic habit is more valuable than memorizing a hundred generic frontend performance tips.

---

# 14. Engineering and Interview Challenges

Try answering these independently before reading the solutions.

### Challenge 1 — The Invisible Loading Indicator

A developer writes:

```javascript
status.textContent = "Loading...";

calculateFor500Milliseconds();

status.textContent = "Done";
```

Users never see the loading message.

Why?

Would adding `await Promise.resolve()` between the first two statements guarantee that the message appears?

### Challenge 2 — The Slow Animation

A modal animates its position by changing its `left` property sixty times per second. The animation stutters.

What browser work might this trigger?

What alternative would you consider?

### Challenge 3 — The Misleading Vue Diagnosis

A Vue application renders 10,000 table rows. Changing the sort order freezes the interface. The team proposes replacing Vue with React.

Is that a reasonable first step?

What evidence would you collect?

### Challenge 4 — The Worker Question

A frontend performs an expensive image-analysis algorithm that consumes 700 milliseconds of CPU time. The calculation does not need DOM access.

Would a Web Worker help?

What additional costs or limitations must be considered?

### Challenge 5 — The Promise Trap

A developer moves an expensive synchronous function into an `async` function and awaits it. The interface still freezes.

Explain why.

---

# 15. Solutions and Discussion

**Challenge 1**

The browser ordinarily doesn't paint the intermediate DOM state while the synchronous JavaScript callback continues executing. By the time the browser gets an opportunity to render, the text has already changed to "Done."

Adding `await Promise.resolve()` doesn't guarantee a paint because the continuation runs through the microtask mechanism, typically before the next rendering opportunity.

The application needs to structure its work so the browser can actually update the screen, potentially by yielding appropriately, separating expensive work into tasks, or moving computation into a worker.

**Challenge 2**

Changing `left` may invalidate layout geometry and require subsequent painting and compositing. If the same visual effect can be produced with `transform`, the browser may be able to animate it primarily through the compositor.

I would test the change and inspect the Performance panel rather than assuming the improvement is guaranteed.

**Challenge 3**

No. Switching frameworks before identifying the bottleneck is an expensive guess. Ten thousand table rows can create substantial DOM and rendering work regardless of framework.

I would profile JavaScript execution, component updates, DOM operations, layout, and painting. Virtualization, pagination, or reducing rendering complexity may be more effective than a framework migration.

**Challenge 4**

Yes, a Web Worker is a strong candidate because the computation is CPU-intensive and independent of the DOM.

But sending and returning data has overhead. Large inputs may require transferable buffers or other data-transfer strategies. The worker also cannot directly update DOM elements, so the main thread must receive the result and update the interface.

**Challenge 5**

Declaring a function `async` doesn't move its synchronous computation to another thread. The expensive function still runs on the main JavaScript thread until it completes.

`await` suspends execution when awaiting a pending promise, but it doesn't parallelize arbitrary CPU work. The developer needs to change how the computation is scheduled or where it executes.

---

# 16. The Mental Model Worth Keeping

A browser is not merely a JavaScript interpreter with a screen attached. It's a sophisticated rendering and execution environment.

The essential chain is:

```text
HTML + CSS
     ↓
DOM + Style Information
     ↓
Style Calculation
     ↓
Layout
     ↓
Paint
     ↓
Compositing
     ↓
Visible Pixels
```

JavaScript can modify the inputs to that pipeline. Those modifications may require very different amounts of work. Some changes affect geometry. Others affect only appearance. Some can be handled largely by compositing already-rendered content.

Meanwhile, the browser's main thread must coordinate JavaScript execution, events, and rendering opportunities. Long synchronous computations can therefore delay user interactions and prevent timely visual updates.

Microtasks, promises, and reactive frameworks do not automatically eliminate that problem. Vue can batch DOM updates intelligently, but it cannot make the browser's rendering costs disappear. Web Workers can move suitable computations away from the main thread, but they do not directly solve excessive DOM or layout work.

And perhaps the most important lesson from our hotel-search mystery:

**A slow frontend isn't necessarily caused by slow JavaScript calculations. Sometimes the real bottleneck is the work the browser must perform after JavaScript finishes.**

Understanding that distinction is the foundation of serious frontend performance engineering.

---

# 17. Next Session — Frontend Architecture Beyond Components

The browser can render beautifully and the architecture can still become hostile to change: six months in, a hotel-booking rule touches seven unrelated files, and a "reusable" component knows about auth, pricing, and currency.

In **SE240-L02 — Frontend Architecture Beyond Components**, we'll explore boundaries, state ownership, composables, feature modules, dependency direction, and the principles that distinguish maintainable frontend systems from collections of components that merely happen to work.

---


---

## Next Lecture — SE240-L02: Frontend Architecture Beyond Components

Continue in **SE240 — Browser and Frontend Engineering**.

## Further Reading — Optional References

1. [MDN — How Browsers Work](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/How_browsers_work) — Parsing, rendering, and browser internals.
2. [MDN — Critical Rendering Path](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Critical_rendering_path) — DOM, CSSOM, layout, and painting.
3. [web.dev — Rendering Performance](https://web.dev/articles/rendering-performance) — Layout, paint, compositing, and optimization.
4. [MDN — Microtask Guide](https://developer.mozilla.org/en-US/docs/Web/API/HTML_DOM_API/Microtask_guide) — Microtasks and the browser event loop.
5. [web.dev — Optimize Long Tasks](https://web.dev/articles/optimize-long-tasks) — Improving responsiveness through scheduling.
6. [Vue — Global API: nextTick](https://vuejs.org/api/general.html#nexttick) — Vue's DOM update scheduling.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE240-L01  INSIDE THE BROWSER — INTERVIEW GLANCE CARD

CORE MODEL
  Browser             Small OS: network, parse, JS, DOM, layout, paint, input, media, storage, security
  Main thread         Much JS + document-rendering coordination share it → long JS delays events / DOM / frames
  Hotel mystery       Sort of 5,000 hotels froze UI; algorithm fine — browser rebuild/layout of huge DOM was cost
  Fix that worked     Keep full data in memory; render only ~30 visible cards (virtualization / windowing)

HTML → DOM
  Parse               HTML string → Document Object Model (nodes + relationships)
  DOM ≠ pixels        Changing DOM does not mean screen already updated
  Progressive parse   Can start before full download; preload scanners discover resources early
  Sync <script>       Can block HTML parsing (JS may mutate document / document.write)
  async               Download async; execute when ready; order not preserved
  defer               Download without blocking; run after parse, before DOMContentLoaded, in order
  type="module"       Deferred by default; dependency-aware

CSS → GEOMETRY
  CSSOM + cascade     Rules → which styles apply (origins, importance, specificity, source order)
  DOM ≠ layout tree   display:none → in DOM, no ordinary layout box
                      visibility:hidden → still participates in layout
  Layout / reflow     Solve interacting geometry; local change can cascade widely

RENDERING PIPELINE (conceptual)
  HTML→DOM / CSS→styles → Style calc → Layout → Paint → Compositing → Screen
  Paint               Drawing instructions / raster of glyphs, backgrounds, borders, shadows, images
  Compositing         Layers move/combine; can avoid full repaint; layers cost memory

CSS CHANGE COST (simplified — not absolute)
  Change              Layout?   Paint?              Composite?
  width               Usually   Usually             Usually
  background-color    Usually N Yes                 Usually
  transform / opacity Usually N Potentially avoid   Yes (compositor-friendly)
  Principle           Cheapest update often avoids geometry + content repaint
  Caution             will-change everywhere has cost — measure first

FRAME BUDGET
  60 Hz ≈ 16.7 ms/frame; 120 Hz ≈ 8.3 ms — JS shares interval with style/layout/paint
  Long task (e.g. 180 ms) spans many frames → conspicuous freeze
  Perf = when work runs + how long main thread stays unavailable — not only total CPU

EVENT LOOP
  Cycle (simplified)  Task → pending microtasks → opportunity to update rendering → …
  Order demo          sync A,D → microtask C → timer task B
  Microtasks          Ordinarily drain before render opportunity → can delay paint
  Endless microtasks  Can starve rendering
  async/await         Does NOT move sync CPU work off main thread
  await fetch         Network can proceed without occupying main thread
  Asynchrony ≠ parallel CPU execution

PAINT TIMING
  Sync callback       Intermediate DOM states often never painted (Loading… → Done)
  requestAnimationFrame  Before upcoming repaint; still not license for expensive work
  Vue nextTick()      Waits for Vue DOM flush — NOT a paint guarantee
  Chain               Reactive update ≠ DOM updated ≠ frame painted

FORCED SYNC LAYOUT / THRASHING
  Pattern             Write style → read offsetHeight → write → read… forces repeated layout
  Fix                 Group reads, then writes (or writes then one read pass)
  Principle           Don't invalidate layout then demand geometry in a tight loop

VUE + LARGE LISTS
  Cost sources        Sort JS, Vue patch, DOM ops, layout, paint — profile before blaming reactivity
  Virtualization      Large dataset; DOM holds viewport + buffer; scroll updates window
  Caveats             Variable heights, a11y, focus; doesn't fix O(n) CPU over whole dataset

WEB WORKERS
  Use                 CPU-heavy work off main thread via postMessage
  Cannot              Directly manipulate page DOM
  Cost                Structured clone / transfer; shared memory = complexity
  Don't fix           Layout of 5,000 DOM nodes — main thread still renders

DIAGNOSE FIRST
  Long task → Performance panel; thrashing → interleaved vs grouped; animate left vs transform
  Vue slow?           JS vs components vs layout vs paint vs network — then choose fix

SENIOR LINE: Slow frontend ≠ slow JS math. Often the browser work after JS finishes.
```

