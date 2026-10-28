---
id: SE240-L04
course: SE240
title: "Delivering Modern Web Applications"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S09]
prev: SE240-L03
next: SE240-L05
---


<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L08
Existing section teaches rendering strategy and introductory SEO.
After SE215-L08 exists, add a concise cross-reference to its broader
technical SEO coverage. Preserve the current rendering explanation.
Do not duplicate or move the entire section.
-->










# SE240 — Browser and Frontend Engineering

## Lecture 04: Delivering Modern Web Applications

*How hundreds of Vue and TypeScript files become a production website—and why deploying a perfectly functional application can break the one that's already running.*

---

# 1. The Deployment That Broke Yesterday's Visitors

It's Wednesday afternoon at your hotel-booking company. The development team has finished a major frontend release. Everything looks excellent.

The new Vue application builds successfully. Automated tests pass. The deployment pipeline uploads the production files to S3, and CloudFront begins serving the new version. You open the website in a fresh browser tab. Perfect.

Search works. Hotel details work. Checkout works. Then customer support reports something peculiar. Users who opened the application before the deployment are experiencing crashes.

Their search pages work normally, but clicking the Reservations tab produces an error.

In Chrome DevTools, you discover a `GET` for `/assets/ReservationsView.a81c2f.js` that returns `404 Not Found`:

```text id="fdny4l"
GET /assets/ReservationsView.a81c2f.js

404 Not Found
```

Interesting. You inspect the current S3 deployment.

There's no file named `ReservationsView.a81c2f.js`:

```text id="hgbki8"
ReservationsView.a81c2f.js
```

There is, however, `ReservationsView.f73d91.js`:

```text id="nttxmc"
ReservationsView.f73d91.js
```

You check the build output. The new file is valid. The new frontend references it correctly.

The new application works. So why are customers requesting the old file? Because their browsers are still executing JavaScript from the **previous deployment**.

That old application contains a reference to the old Reservations chunk. When the user finally navigates to the reservations page, the browser attempts to download it. But your deployment process deleted the previous assets.

The running application has become a stranded survivor of an earlier release.

And here's the particularly uncomfortable part:

**You can deploy a new frontend without replacing the frontend that is already running inside your customers' browsers.**

This is one of the most important differences between traditional server application deployment and browser application deployment. Your backend process can be restarted. Your new server instances can replace old ones.

But the JavaScript already loaded into a customer's browser doesn't disappear merely because you've published a new build. To understand the consequences, we need to trace how a modern frontend moves from source code to production.

---

# 2. Your Source Code Isn't What the Browser Executes

Imagine a Vue application whose `src/` tree holds `main.ts`, `App.vue`, a `router/`, `components/`, feature folders for search, reservations, and payments, plus `services/`:

```text id="kldd4a"
src/
├── main.ts
├── App.vue
├── router/
├── components/
├── features/
│   ├── search/
│   ├── reservations/
│   └── payments/
└── services/
```

You write TypeScript. You write Vue single-file components. You import libraries from `node_modules`.

You use environment variables, CSS preprocessors, and perhaps several build-time plugins. But a production browser doesn't directly understand all these development abstractions.

Consider a tiny `<script setup lang="ts">` component that imports `ref` from Vue, holds `guests` as `ref<number>(2)`, and templates `Guests: {{ guests }}`:

```vue id="mo9v1w"
<script setup lang="ts">
import { ref } from "vue";

const guests = ref<number>(2);
</script>

<template>
  <p>Guests: {{ guests }}</p>
</template>
```

This is convenient source code. But the browser doesn't natively interpret `.vue` files.

And TypeScript type annotations such as `ref<number>(2)` are not part of ordinary JavaScript execution.

```typescript id="6ovrkc"
ref<number>(2)
```

Some transformation must happen. The Vue template must become executable rendering logic.

TypeScript-specific syntax must be removed. Imports must be resolved. Styles and assets must be incorporated into something the browser can load.

That's where our build tool enters.

---

# 3. Vite: Why Development and Production Behave Differently

Since our application uses Vue and Vite, let's examine Vite's responsibilities.

Vite has two major operating modes:

**Development:** Serve application modules efficiently and support rapid updates.

**Production build:** Produce optimized distributable assets.

These objectives are related, but not identical.

## 3.1 During development: Serve modules on demand

You run `npm run dev`.

```bash id="g1ncku"
npm run dev
```

Vite starts a development server. In its conventional development mode, Vite takes advantage of native browser ES modules.

Consider an entry that imports `createApp` from Vue and `App` from `./App.vue`, then mounts with `createApp(App).mount("#app")`:

```typescript id="6xla6w"
import { createApp } from "vue";
import App from "./App.vue";

createApp(App).mount("#app");
```

Rather than bundling the entire application into one giant file before serving anything, Vite can transform and deliver source modules as the browser requests them. It also optimizes dependencies, which change much less frequently than your application source.

This arrangement makes development pleasant. The server starts quickly. Editing a Vue component doesn't require rebuilding the entire application.

Hot Module Replacement, or **HMR**, can replace affected modules in the browser while preserving suitable application state. That last part is particularly convenient. You edit a component's CSS and immediately see the new styling without a full page reload.

But this development experience shouldn't be confused with how the application is delivered in production.

## 3.2 Why not simply deploy the development modules?

You might ask:

"If browsers support ES modules, why bother bundling anything?" It's a reasonable question.

Imagine your application imports a fan-out from `main.ts` into `App.vue`, `router.ts`, `searchStore.ts`, `HotelCard.vue`, `PriceDisplay.vue`, and hundreds of additional modules:

```text id="qq76wx"
main.ts
   ├── App.vue
   ├── router.ts
   ├── searchStore.ts
   ├── HotelCard.vue
   ├── PriceDisplay.vue
   └── hundreds of additional modules
```

Modern browsers can load module dependencies through HTTP. But a large unbundled module graph introduces overhead. The browser needs to discover dependencies, fetch modules, parse them, and execute them in the correct order.

Some requests can overlap. Others depend on discovering additional imports. Even under HTTP/2 or HTTP/3, an unnecessarily fragmented dependency graph can create expensive loading behavior.

Production bundling attempts to improve this situation. It can combine suitable modules, remove unused code, optimize assets, and arrange chunks that better match application loading behavior.

In current Vite releases, the production build uses **Rolldown**, a Rust-based bundler. Older Vite versions used Rollup. The exact bundler implementation matters less to our architectural discussion than what the build process accomplishes.

## 3.3 The production build

You execute `npm run build`.

```bash id="xdgnbt"
npm run build
```

In a conventional Vite project, that invokes `vite build`, potentially along with other project-specific checks.

The resulting `dist/` directory might resemble an `index.html`, a favicon, and an `assets/` folder of hashed files such as `index.c481a2.js`, `index.72f391.css`, `vendor.18e992.js`, `HotelSearch.90ac13.js`, and `ReservationsView.a81c2f.js`:

```text id="lg8n8r"
dist/
├── index.html
├── favicon.svg
└── assets/
    ├── index.c481a2.js
    ├── index.72f391.css
    ├── vendor.18e992.js
    ├── HotelSearch.90ac13.js
    └── ReservationsView.a81c2f.js
```

These filenames are illustrative. The important observation is that the output no longer resembles the source tree. Vue components have been compiled.

TypeScript-specific syntax has been transformed. Modules have been bundled into an optimized arrangement. CSS may have been extracted.

Unused code may have been removed. And asset filenames may contain content-derived hashes. The `dist/` directory is now a deployable artifact.

One subtle qualification: **Vite's JavaScript transformation is not a substitute for TypeScript type checking.** A project commonly runs `vue-tsc` or another appropriate type checker separately as part of its build or CI process.

A successful transformation alone doesn't establish that all TypeScript expectations are correct.

---

# 4. Tree Shaking: Shipping Less Code Than You Wrote

Suppose your application imports only `calculateTotal` from `./pricing`:

```typescript id="rkl522"
import { calculateTotal } from "./pricing";
```

And `pricing.ts` exports both `calculateTotal` and an unused `generateHugeFinancialReport`:

```typescript id="uh1cqz"
export function calculateTotal() {
  // ...
}

export function generateHugeFinancialReport() {
  // ...
}
```

If the reporting function is never used by any reachable part of the application, a bundler may be able to exclude it from the production output. This optimization is called **tree shaking**. The underlying idea is to analyze module dependencies and remove code that isn't needed.

But tree shaking has limits.

Consider a side-effect import of `./analytics-setup` with no named binding:

```typescript id="57x8w3"
import "./analytics-setup";
```

This module might execute important code immediately when imported. The import has a side effect. A bundler cannot automatically assume that removing it is safe merely because it doesn't export a value consumed elsewhere.

Likewise, dynamic behavior can make static analysis more difficult. Tree shaking works particularly well when modules expose understandable, statically analyzable exports and have predictable side-effect behavior.

But the deeper engineering principle is simple:

**The best way to reduce JavaScript execution costs is often not to deliver unnecessary JavaScript in the first place.**

That connects directly to SE240-L01. Every unnecessary byte may need to be downloaded, decompressed, parsed, compiled, and potentially executed. A small bundle is not merely a networking optimization.

It can also be a CPU and responsiveness optimization.

---

# 5. Code Splitting: Why the Reservations Page Wasn't Already Loaded

Now we reach the mechanism behind our deployment mystery.

Imagine a large SaaS application with several substantial features—Hotel Search, Reservations, Payments, Analytics, and Administration:

```text id="7e5vss"
Application
├── Hotel Search
├── Reservations
├── Payments
├── Analytics
└── Administration
```

Should every customer download the entire Administration dashboard merely to search for a hotel? Probably not. Perhaps 95% of customers never visit that functionality.

Delivering it during initial page load would waste bandwidth and browser processing time.

**Code splitting** allows the build process to produce separately loadable JavaScript chunks.

Consider a Vue Router configuration where `/search` and `/reservations` each load their views through dynamic `import()` of `SearchView.vue` and `ReservationsView.vue`:

```typescript id="3r0zj6"
const routes = [
  {
    path: "/search",
    component: () => import(
      "@/features/search/SearchView.vue"
    )
  },
  {
    path: "/reservations",
    component: () => import(
      "@/features/reservations/ReservationsView.vue"
    )
  }
];
```

Notice the dynamic `import()`. Instead of importing both components eagerly, the router loads them when needed. The production build can create separate chunks.

When the customer first opens Search, the browser doesn't necessarily download the Reservations view. Later, when the customer navigates there, the browser fetches the required chunk. This is **lazy loading**.

## 5.1 Why lazy loading helps

Suppose your application contains roughly 180 KB for the core, 90 KB for Hotel Search, 120 KB for Reservations, and 350 KB for Administration.

```text id="dq6mae"
Core application:       180 KB
Hotel Search:            90 KB
Reservations:           120 KB
Administration:         350 KB
```

All figures are hypothetical compressed transfer sizes. An eager-loading strategy might require downloading most or all of that code before the user can interact with the application. A suitable code-splitting strategy could substantially reduce the initial transfer.

But lazy loading introduces a trade-off. The customer may now experience a delay when first navigating to another feature. And if the required asset is unavailable, that navigation can fail.

Exactly what happened in our opening incident.

## 5.2 The dependency waterfall

Imagine the browser loads in sequence: the application entry, then the Reservations chunk, then a shared date-picker chunk discovered only after parsing Reservations:

```text id="nhw7ma"
Application entry
        │
        ▼
Reservations chunk
        │
        ▼
Shared date-picker chunk
```

If the browser only discovers the date-picker dependency after downloading and parsing the Reservations chunk, the final dependency adds another sequential step. Modern build tools can optimize these situations by preloading known dependencies.

Vite, for example, supports module preload generation and optimized loading of asynchronous chunk dependencies.

But the general trade-off remains:

Too little code splitting can make initial loading expensive. Too much fragmentation can create excessive request and scheduling overhead. Good chunk boundaries reflect actual navigation and usage patterns.

## 5.3 Why the old application broke

Let's reconstruct the original incident.

At 13:00, version A is deployed with `index.html`, `index.c481a2.js`, and `ReservationsView.a81c2f.js`:

```text id="zdj9wt"
index.html
index.c481a2.js
ReservationsView.a81c2f.js
```

A customer opens the application.

The browser downloads `index.c481a2.js`:

```text id="o4zyxz"
index.c481a2.js
```

But the customer hasn't opened Reservations yet. The Reservations chunk remains unloaded.

At 14:00, version B is deployed with a new `index.html`, `index.f9d172.js`, and `ReservationsView.f73d91.js`:

```text id="fqd2nl"
index.html
index.f9d172.js
ReservationsView.f73d91.js
```

The deployment process deletes the old files. At 14:05, the customer clicks Reservations.

The already-running JavaScript from version A still references `ReservationsView.a81c2f.js`:

```text id="vugci4"
ReservationsView.a81c2f.js
```

But the file no longer exists. The dynamic import fails. The browser doesn't spontaneously rewrite its running JavaScript to reference version B.

And so the application crashes. This is not a Vue bug. It's a failure to account for overlapping frontend releases.

---

# 6. Deployment Is a Consistency Problem

A deployment is often described as a three-step slogan—Build, Upload, Done:

```text id="3hmspv"
Build → Upload → Done
```

That description is dangerously incomplete. A running web application may involve multiple resources that must be mutually compatible.

For example, `index.html` can point at a main JS chunk that itself depends on shared JS and lazy route chunks, plus CSS and other assets:

```text id="e4yn65"
index.html
    │
    ├── Main JS chunk
    │       ├── Shared JS chunk
    │       └── Lazy route chunks
    │
    ├── CSS
    └── Other assets
```

A deployment changes some or all of these resources. But users may retrieve them at different times from different caches. That's where consistency problems emerge.

## 6.1 The wrong deployment order

Suppose your deployment process performs these operations:

1. Delete all old assets.
2. Upload the new `index.html`.
3. Upload new JavaScript and CSS.

What's wrong? During step 2, the new HTML may reference files that haven't been uploaded yet. A customer arriving at precisely the wrong moment can receive the new document and fail to download its dependencies.

Even worse, customers running the previous application lose access to old lazy-loaded chunks as soon as step 1 occurs. The deployment process has created a temporary inconsistent state.

## 6.2 A safer publishing strategy

For a conventional static SPA with content-hashed assets, a better approach is:

1. Build and test the complete release.
2. Upload all new versioned assets.
3. Verify the necessary assets are available.
4. Publish the new HTML entry document.
5. Retain previous assets for a suitable compatibility period.

Now the HTML should not reference assets that haven't been published. And older browser sessions can continue loading chunks from their original release. For more demanding environments, release-specific asset directories and atomic promotion of a release pointer can provide stronger coordination.

For example, release-specific directories such as `/releases/2026-10-25-a/assets/...` and `/releases/2026-10-25-b/assets/...`:

```text id="ggfplh"
/releases/2026-10-25-a/assets/...
/releases/2026-10-25-b/assets/...
```

The active HTML can be switched to reference the newer release while older assets remain available. The precise mechanism depends on your infrastructure.

But the principle is general:

**A release isn't one file. It's a compatible collection of resources that may remain in use after a newer release exists.**

## 6.3 What about recovering from chunk-loading errors?

Modern applications can detect certain dynamic-import failures. Vite provides a `vite:preloadError` event for relevant preload failures.

A simplified handler might listen for `vite:preloadError` and call `window.location.reload()`:

```typescript id="moxwi4"
window.addEventListener("vite:preloadError", () => {
  window.location.reload();
});
```

This illustrates the mechanism, not a complete production strategy. Blindly refreshing can create loops, discard unsaved user input, or repeatedly encounter stale HTML.

A production application should distinguish recoverable deployment mismatches from transient network failures, limit automatic recovery attempts, and avoid interrupting consequential workflows.

The first line of defense should be deploying compatible assets correctly. Error recovery is a fallback—not an excuse to delete dependencies that active sessions still need.

---

# 7. Caching: The HTML and JavaScript Have Different Jobs

We studied HTTP caching in CS230-L03. Now let's apply it to production deployment.

Suppose the browser requests `/index.html`:

```text id="wkzduz"
/index.html
```

That document references a content-hashed script at `/assets/index.f9d172.js`:

```text id="1a2x14"
/assets/index.f9d172.js
```

The JavaScript filename is content-hashed. If the JavaScript contents change, the filename changes. That gives us a powerful caching opportunity.

## 7.1 Immutable static assets

For a correctly versioned asset, a typical header is `Cache-Control: public, max-age=31536000, immutable`—about a year, marked immutable:

```http id="d96kam"
Cache-Control: public, max-age=31536000, immutable
```

This tells suitable caches that the response can remain fresh for a long period and is not expected to change at that URL. Why is this safe? Because a changed asset should receive a new URL.

The old file remains the old file. The new file gets a new name. The browser doesn't need to repeatedly ask whether `index.f9d172.js` has changed.

It shouldn't change.

## 7.2 HTML requires a different strategy

Now consider `/index.html` again:

```text id="97sgwp"
/index.html
```

The HTML entry document commonly retains the same URL across releases. Its contents change to reference the new assets. Caching it for a full year could leave customers loading an outdated application shell.

A common policy is `Cache-Control: no-cache`:

```http id="h54ebz"
Cache-Control: no-cache
```

As we learned earlier, this doesn't mean that HTTP caches cannot store the HTML. It means they must successfully validate it before reuse. A suitable validation response can still avoid retransmitting an unchanged document.

The important distinction is: versioned JS and CSS are long-lived and immutable; versioned images and fonts likewise; the HTML entry document should revalidate before reuse; and personalized API responses need an explicit policy based on sensitivity and freshness.

| Resource | Typical caching strategy |
|---|---|
| Versioned JS/CSS | Long-lived, immutable |
| Versioned images/fonts | Long-lived, immutable |
| HTML entry document | Revalidate before reuse |
| Personalized API responses | Explicit policy based on sensitivity and freshness |

This division is one of the most useful deployment patterns for modern SPAs.

## 7.3 Why CDN invalidation isn't enough

Suppose you update CloudFront and invalidate `/index.html`:

```text id="a7rp4e"
/index.html
```

That helps edge locations obtain the new entry document. But CloudFront invalidation cannot force every customer to discard JavaScript already running in their browser. Nor does it necessarily clear arbitrary browser caches or other intermediaries.

Versioned filenames are valuable because they give changed content a new identity. They avoid relying on global cache invalidation to replace immutable assets.

The deployment strategy therefore combines two complementary ideas:

**Stable document URL with controlled freshness.**

**Versioned asset URLs with long-lived caching.**

---

# 8. Static Hosting: Does a Vue Application Need a Node.js Server?

Here's a surprisingly common architectural confusion. You develop a Vue application using Node.js tooling. You run a Vite development server.

You execute a Node-based build command. Does that mean your production frontend must run on Node.js? No.

For an ordinary client-side-rendered Vue SPA, the production output can consist entirely of static files.

For example, production may be just `index.html` plus `assets/*.js`, `assets/*.css`, and `assets/*.svg`:

```text id="nmb25p"
index.html
assets/*.js
assets/*.css
assets/*.svg
```

Those files can be served by:

- Nginx.
- Apache.
- S3 behind CloudFront.
- A static hosting service.
- Another suitable HTTP file-serving system.

The browser executes the frontend JavaScript. Your backend API may still use Node.js, Lambda, or another server runtime. But the frontend assets themselves don't require a persistent Node.js application server.

## 8.1 The client-side routing trap

Suppose the customer visits `https://stays.example.com/reservations`:

```text id="kj6kb5"
https://stays.example.com/reservations
```

Inside the running Vue application, Vue Router recognizes `/reservations`. But what happens when the customer refreshes the page?

The browser makes a new document request—`GET /reservations`:

```http id="o7gqo3"
GET /reservations
```

The static server looks for a resource at that path.

If it isn't configured to support SPA routing, it may return `404 Not Found`:

```http id="m6lfxk"
404 Not Found
```

The route worked through client-side navigation, but fails on refresh. A conventional SPA hosting setup needs an appropriate **history fallback**. For routes intended to be handled by the frontend, the server returns the application's HTML entry document.

Vue Router then interprets the path in the browser. However, blindly rewriting every missing request to `index.html` is also dangerous.

Imagine a missing or misconfigured API call such as `GET /api/reservations/9821`:

```http id="dmz00p"
GET /api/reservations/9821
```

If the API route is missing or misconfigured, returning HTML with status 200 can cause the frontend to attempt to parse HTML as JSON. Likewise, a missing JavaScript asset should not quietly return `index.html`. The browser may report a MIME-type error or another confusing failure.

A good hosting configuration distinguishes:

- Intended frontend document routes.
- API routes.
- Static asset requests.
- Genuine missing resources.

SPA fallback is a routing policy, not a universal answer to every 404.

---

# 9. CSR: When the Browser Builds the Application

So far we've primarily discussed **Client-Side Rendering**, or CSR. Consider a basic Vue application.

The browser receives a near-empty shell: a module script pointing at `/assets/index.f9d172.js` and a bare `<div id="app"></div>`:

```html id="ibkp9u"
<!doctype html>
<html>
  <head>
    <script
      type="module"
      src="/assets/index.f9d172.js"
    ></script>
  </head>

  <body>
    <div id="app"></div>
  </body>
</html>
```

The HTML contains very little actual page content. The JavaScript initializes Vue. Vue renders the interface.

The application fetches any required data.

Conceptually the CSR path is: receive the HTML shell, download JavaScript, execute the application, fetch necessary data, then render a useful interface:

```text id="awdlzc"
Receive HTML shell
        ↓
Download JavaScript
        ↓
Execute application
        ↓
Fetch necessary data
        ↓
Render useful interface
```

This is not necessarily the exact sequence for every CSR application. Some requests can overlap. But it illustrates the central dependency. The browser performs the initial application rendering.

## 9.1 Why CSR is attractive

For authenticated SaaS applications, CSR can be a very reasonable default. Once the application loads, users may spend hours inside it. They navigate between routes without requesting entirely new HTML documents.

They manipulate stateful interfaces. They interact with dashboards, forms, tables, and real-time information. A rich client-side runtime makes sense for these workloads.

CSR also allows the frontend to be deployed as static assets, separating application delivery from backend execution. But the initial loading experience can be expensive. The customer may wait for JavaScript before seeing useful content.

And on slower devices, parsing and executing the application can take substantially longer than downloading the HTML. This leads us to an alternative.

---

# 10. SSR: What If the Server Rendered the Page First?

Imagine opening a hotel details page.

With CSR, the initial HTML might contain only `<div id="app"></div>`:

```html id="4w3th2"
<div id="app"></div>
```

The browser must execute JavaScript before the hotel content appears. With **Server-Side Rendering**, or SSR, the server generates HTML containing the page's initial content.

For example, the same `#app` root might already hold a main heading "Hotel Alexander," "Berlin, Germany," and "From €149 per night":

```html id="hy11sm"
<div id="app">
  <main>
    <h1>Hotel Alexander</h1>
    <p>Berlin, Germany</p>
    <p>From €149 per night</p>
  </main>
</div>
```

The browser can begin displaying meaningful content before it finishes downloading and executing all the application JavaScript. This can significantly improve time-to-content, especially for slower devices or networks. But now the application has a new responsibility.

Something must render the Vue components on the server. For Vue, frameworks such as Nuxt provide higher-level infrastructure for SSR and related delivery strategies.

## 10.1 SSR changes where work happens

With CSR, the server returns an HTML shell, the browser executes Vue, and the browser builds the initial UI:

```text id="doyqfr"
Server returns HTML shell
           │
           ▼
Browser executes Vue
           │
           ▼
Browser builds initial UI
```

With SSR, the server executes rendering logic and returns populated HTML; the browser displays that content, loads JavaScript, and hydration enables interactivity:

```text id="iiie46"
Server executes rendering logic
           │
           ▼
Server returns populated HTML
           │
           ▼
Browser displays initial content
           │
           ▼
Browser loads JavaScript
           │
           ▼
Hydration enables interactivity
```

The browser still typically needs JavaScript for an interactive Vue application. SSR doesn't automatically eliminate client-side execution. It moves initial HTML generation to the server.

That can improve early presentation, but it also introduces server-side computation, infrastructure requirements, and additional complexity.

## 10.2 Hydration: Making server-rendered HTML interactive

Here's the fascinating part.

Suppose the server sends a bare `<button>Reserve Room</button>`:

```html id="c0f3ps"
<button>Reserve Room</button>
```

The browser can display it. But the HTML alone doesn't contain the Vue runtime and the application's event-handling logic. The button may look ready while its client-side interaction has not yet been established.

**Hydration** is the process through which the client-side Vue application connects to the existing server-rendered DOM.

Conceptually, Vue:

- Initializes the corresponding application logic.
- Matches its expected component output against the existing DOM.
- Establishes event handling and reactive behavior.
- Reuses suitable existing nodes instead of constructing the entire interface from scratch.

This is what turns server-rendered markup into an interactive application. And it creates a new problem. What if the server and browser disagree about what the page should contain?

---

# 11. The Hydration Mismatch: Two Computers, Two Different Realities

Imagine a Vue component whose script picks `greeting` with `Math.random()`—either `"Welcome!"` or `"Hello!"`—and templates that into an `h1`:

```vue id="ebk9kw"
<script setup lang="ts">
const greeting = Math.random() > 0.5
  ? "Welcome!"
  : "Hello!";
</script>

<template>
  <h1>{{ greeting }}</h1>
</template>
```

With CSR, this is mostly harmless. The browser calculates a value and renders it. With SSR, the code may execute once on the server and again on the client.

The server might produce `<h1>Welcome!</h1>`:

```html id="lnvukj"
<h1>Welcome!</h1>
```

But the browser calculates `Hello!`:

```text id="d4hvpm"
Hello!
```

The two outputs disagree. This is a **hydration mismatch**. Vue may attempt to recover by adjusting the DOM, but that creates additional work and can produce undesirable visual behavior.

A more realistic example involves dates. Suppose the server runs in UTC, while the customer is in Lithuania. The component formats a timestamp using the runtime's default timezone.

The server produces one date. The browser produces another. Again, the outputs may differ.

## 11.1 How to avoid mismatches

The principle is straightforward.

**Initial server and client rendering must agree on the data and assumptions used to produce the same markup.**

Possible strategies include:

- Serializing the server-used initial state and reusing it during hydration.
- Using deterministic formatting for the initial render.
- Deferring browser-specific values until after mounting.
- Avoiding random values in shared rendering paths unless their results are synchronized.
- Keeping invalid HTML nesting out of rendered templates.

The real difficulty emerges when developers assume their code only runs in a browser.

## 11.2 `window` doesn't exist everywhere

Consider reading `window.innerWidth` at module or setup time:

```typescript id="aqg1q0"
const width = window.innerWidth;
```

Perfectly ordinary browser code. But if executed during Node.js server rendering, it fails because `window` isn't available. Likewise, direct DOM operations using `document` don't belong in universal rendering code unless carefully isolated.

Vue's `onMounted()` hook is useful for browser-only work because it doesn't execute during SSR.

For example, keep `width` as `ref<number | null>(null)` and assign `window.innerWidth` only inside `onMounted`:

```typescript id="i9q72z"
const width = ref<number | null>(null);

onMounted(() => {
  width.value = window.innerWidth;
});
```

This avoids accessing `window` on the server. Of course, the UI must sensibly handle the initial `null` value.

## 11.3 The more dangerous SSR bug: Shared user state

Imagine a server-rendered application storing authenticated user information in module-level mutable state.

A request from Customer A sets module-level `currentUser = Customer A`:

```text id="j9y7wc"
currentUser = Customer A
```

Then Customer B's request arrives. If application state is improperly shared between requests, Customer B might observe information belonging to Customer A. This is a serious data-isolation problem.

SSR applications must manage request-specific state carefully. A common strategy is to create fresh application and store instances for each request. Pinia and SSR frameworks provide patterns for doing this correctly.

The important architectural difference:

**In CSR, one browser runtime normally belongs to one user's application session. In SSR, a long-running server process may render pages for many different users.**

Code written with browser-only assumptions can therefore become dangerous when moved into a shared server environment.

---

# 12. SSG: Generate the Page Before Anyone Requests It

There's another possibility. What if the page doesn't change for every request? Consider your company's public marketing website.

It contains:

- Product descriptions.
- Pricing-plan explanations.
- Documentation.
- Blog posts.
- Contact information.

Much of this content changes relatively infrequently. Why execute a server-side Vue rendering process for every visitor? You could generate the HTML ahead of time.

This is **Static Site Generation**, or SSG.

Conceptually SSG runs source content plus components through a build step into generated HTML, then static hosting, then the browser:

```text id="n2m5dx"
Source content + Components
             │
             ▼
          Build time
             │
             ▼
       Generated HTML
             │
             ▼
        Static hosting
             │
             ▼
           Browser
```

The output is ordinary HTML that can be distributed through a CDN. This can provide excellent performance and low operational complexity for suitable content. But the obvious limitation is freshness.

If hotel prices change every second, prebuilding every hotel's current availability into static HTML becomes problematic. You need a strategy for refreshing the generated content or retrieving dynamic data separately.

## 12.1 Comparing rendering approaches

In short: **CSR** produces initial HTML in the browser and suits interactive authenticated applications; **SSR** produces it on the server at request time and suits dynamic, content-rich pages that need early HTML; **SSG** produces it at build time and suits stable public content, documentation, and marketing.

| Strategy | Where initial HTML is produced | Particularly useful for |
|---|---|---|
| CSR | Browser | Interactive authenticated applications |
| SSR | Server at request time | Dynamic, content-rich pages needing early HTML |
| SSG | Build process | Stable public content, documentation, marketing |

These categories aren't mutually exclusive. A sophisticated product can combine them.

For example:

**Marketing website:** SSG.

**Public hotel details:** SSR or another suitable server-rendered strategy.

**Authenticated booking dashboard:** CSR.

**Frequently updated availability:** API-driven dynamic data.

This is often more sensible than selecting one rendering strategy for every page merely because a framework supports it.

## 12.2 What about SEO?

Server-rendered or pre-rendered HTML can make content more readily available to crawlers. But the claim that client-rendered websites are categorically invisible to search engines is too simplistic. Some search engines, notably Google, can render JavaScript.

However, that processing has limitations and may introduce delays or additional complexity. SSR and SSG can provide more dependable initial content delivery for public pages where discoverability matters. For an authenticated internal SaaS dashboard, SEO is usually irrelevant.

Rendering strategy should follow actual product requirements.

---

# 13. Where Do CDNs Fit Into All This?

A CDN is often discussed as though it only caches photographs and JavaScript files. But the broader idea is distributing content and suitable processing closer to users. Consider a customer in Vilnius visiting a website whose origin infrastructure is in Frankfurt.

Without useful edge caching, requests for static resources may repeatedly travel to the origin region.

With CloudFront, the customer hits an edge that either returns a cache hit or, on a miss, fetches from the origin:

```text id="kx90jh"
Customer
    │
    ▼
CloudFront Edge
    │
    ├── Cache hit
    │       └── Return cached content
    │
    └── Cache miss
            │
            ▼
        Origin
```

For content-hashed JavaScript bundles, this is straightforward. The same bytes can be served to many customers. For personalized server-rendered pages, caching becomes more complicated.

Suppose the HTML contains a personalized greeting such as `Welcome back, Customer 901!`:

```text id="rcb8bb"
Welcome back, Customer 901!
```

You certainly don't want to serve that HTML to Customer 902. Caching personalized content requires correct isolation, cache-key design, and deliberate policies. Some architectures separate a publicly cacheable shell from private data fetched after authentication.

Others avoid shared caching for personalized HTML altogether. This is why the boundary between static delivery and dynamic application behavior matters. A CDN is not merely a performance switch you enable.

It's another participant in the system's caching and consistency model.

---

# 14. Build-Time Configuration: The Secret That Wasn't Secret

Let's examine one more practical deployment trap. Your Vue application needs to know where its API is hosted.

You configure Vite with `VITE_API_BASE_URL=https://api.example.com`:

```text id="493r0n"
VITE_API_BASE_URL=https://api.example.com
```

Then access it via `import.meta.env.VITE_API_BASE_URL`:

```typescript id="ug8ksa"
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL;
```

This is a normal pattern.

But what if someone configures `VITE_STRIPE_SECRET_KEY=...`:

```text id="02neio"
VITE_STRIPE_SECRET_KEY=...
```

and assumes it's safe because the value came from an environment variable? That is a serious misunderstanding. In Vite's conventional client build, variables exposed through the `VITE_` prefix are made available to client-side code at build time.

Their values can become part of publicly delivered JavaScript. Anyone who receives the bundle may be able to inspect them. The fact that something originated in an environment variable doesn't make it secret.

## 14.1 Build-time versus runtime configuration

A conventional static frontend build often embeds configuration values during compilation.

For example, a build environment with `API_BASE_URL = api.example.com` can bake that hostname into the production bundle:

```text id="40auqv"
Build environment:
API_BASE_URL = api.example.com
           │
           ▼
Production bundle contains configured URL
```

If the API hostname changes, you may need to rebuild the frontend. An alternative is runtime configuration.

For example, the application might fetch a public configuration document at `/config.json`:

```text id="najugq"
/config.json
```

This allows certain settings to change independently of the JavaScript build. But runtime configuration adds another dependency and raises questions about caching, availability, validation, and initialization order. Neither approach is universally superior.

Build-time configuration is simple and deterministic. Runtime configuration offers more deployment flexibility.

The essential security rule remains the same:

**Anything delivered to the browser is accessible to the browser's user. It cannot be treated as a server-side secret.**

---

# 15. A Sensible Deployment Architecture

Let's design a production delivery strategy for our Vue-based hotel SaaS.

Assume:

- Vue 3 and Vite.
- Client-side routing.
- Node.js or serverless backend APIs.
- S3 for static files.
- CloudFront for delivery.
- CI/CD for releases.

A plausible architecture runs from the Git repository through a CI pipeline of type checks and tests, into a Vite build of static assets, onto S3, out through CloudFront to the browser, which then calls the backend API:

```text id="nf4z9l"
             Git Repository
                   │
                   ▼
               CI Pipeline
                   │
          ┌────────┴────────┐
          │                 │
      Type Checks        Tests
          │                 │
          └────────┬────────┘
                   │
                   ▼
              Vite Build
                   │
                   ▼
             Static Assets
                   │
                   ▼
                 S3
                   │
                   ▼
              CloudFront
                   │
                   ▼
                Browser
                   │
                   ▼
             Backend API
```

The details could vary considerably, but this illustrates a clean separation. The frontend build produces static assets. CloudFront distributes them.

The browser executes the application. Backend services handle dynamic requests.

## 15.1 Release procedure

A reasonable release strategy would include:

**Build and validate.** Run appropriate checks, tests, and production build steps.

**Publish versioned assets.** Upload the new JavaScript, CSS, images, and fonts without deleting resources still needed by earlier releases.

**Publish the entry document.** Make the new HTML reference the new asset set.

**Control caching.** Use long-lived caching for immutable versioned assets and appropriate validation behavior for the HTML entry point.

**Verify the release.** Check that the page loads, critical chunks exist, routing works, and important API operations remain compatible.

**Preserve rollback capability.** Keep previous artifacts and ensure the current backend can support the frontend versions likely to remain in use.

This last point connects to SE310-L01. Frontend deployment compatibility is not only about JavaScript assets.

Suppose version A expects a flat `"price": 149.99`:

```json id="uc7zkq"
{
  "price": 149.99
}
```

Version B expects a nested `"price": { "amountMinor": 14999 }`:

```json id="uu4x7z"
{
  "price": {
    "amountMinor": 14999
  }
}
```

If the backend switches exclusively to the new representation, preserving version A's JavaScript chunks won't be enough. The old frontend can now load successfully but still fail when talking to the API. A robust deployment therefore needs **asset compatibility and API compatibility**.

Two different problems. One production rollout.

---

# 16. Engineering and Interview Challenges

### Challenge 1 — The Broken Lazy Route

A frontend deployment deletes all previous JavaScript assets.

New visitors work normally.

Customers with older tabs experience `404` errors when opening certain routes.

Explain the failure and propose a deployment strategy that avoids it.

### Challenge 2 — The SPA Refresh Mystery

A Vue application works when navigating to `/reservations` through Vue Router.

Refreshing the page at the same URL returns `404`.

Why?

What should the hosting infrastructure do, and what should it avoid doing?

### Challenge 3 — The Build-Time Secret

A developer places an API secret in `VITE_PAYMENT_SECRET=...`:

```text id="hrks37"
VITE_PAYMENT_SECRET=...
```

They claim it's safe because the value comes from an environment variable.

Evaluate that claim.

### Challenge 4 — CSR or SSR?

You're building two products.

**Product A:** A public travel guide containing thousands of destination pages.

**Product B:** An authenticated logistics dashboard used for several hours per day.

Would you automatically choose the same rendering strategy for both?

Explain the trade-offs.

### Challenge 5 — Hydration Surprise

A Vue SSR application displays a different timestamp on the server and in the customer's browser.

Hydration produces a mismatch warning.

Why?

What design changes could prevent the mismatch?

---

# 17. Solutions and Discussion

**Challenge 1**

The old browser session still references JavaScript chunks from its original release.

Deleting those chunks breaks later dynamic imports.

A safer deployment publishes all new assets before switching the HTML entry document, retains previous versioned assets for a suitable period, and uses appropriate caching policies.

The backend should also remain compatible with frontend versions that may still be active.

**Challenge 2**

Client-side navigation doesn't necessarily request a new HTML document.

Refreshing the URL does.

The static server must support appropriate SPA route fallback so intended frontend document routes receive the application's HTML entry point.

But missing API routes and static assets should not be blindly rewritten to HTML, because that hides real failures and can produce misleading response types.

**Challenge 3**

The claim is false.

Client-exposed Vite environment variables can be embedded in the production JavaScript.

Anything delivered to the browser must be considered publicly inspectable.

Payment secrets and other server-side credentials belong in trusted backend infrastructure.

**Challenge 4**

No.

The public travel guide may benefit from SSR or SSG because early content availability and search-engine discoverability matter.

The authenticated logistics dashboard may be well suited to CSR because users spend long sessions interacting with a rich stateful interface.

The correct choice depends on performance requirements, content freshness, infrastructure complexity, and how users interact with each product.

**Challenge 5**

The server and browser generated different initial output.

Differences in timezone, locale, random values, or request-specific data can cause mismatches.

The application should ensure deterministic initial rendering, serialize appropriate server state for the client, and defer browser-specific rendering decisions when necessary.

---

# 18. The Mental Model Worth Keeping

A modern frontend doesn't travel directly from source code to the user's screen.

It passes through a chain of transformations and infrastructure: source code, build and transformation, JavaScript/CSS/HTML assets, hosting, CDN and browser caches, browser execution, and finally the rendered application:

```text id="3mhy4y"
Source Code
    │
    ▼
Build / Transformation
    │
    ▼
JavaScript, CSS, HTML Assets
    │
    ▼
Hosting Infrastructure
    │
    ▼
CDN and Browser Caches
    │
    ▼
Browser Execution
    │
    ▼
Rendered Application
```

Each stage introduces opportunities for optimization—and failure.

**Bundling** transforms development modules into production assets.

**Tree shaking** removes code that doesn't need to be shipped.

**Code splitting** postpones loading code until it's needed.

**Content hashing** gives changed assets new identities, enabling efficient caching.

**Deployment coordination** ensures compatible assets remain available while different application versions coexist.

**CSR** performs initial application rendering in the browser.

**SSR** generates initial HTML on the server and typically relies on hydration for client-side interactivity.

**SSG** generates HTML ahead of time for content that can be prebuilt.

**CDNs** distribute cacheable content closer to users, but require deliberate consistency and security policies.

And here's the most important lesson:

**A frontend deployment isn't an atomic replacement of the application everywhere. It's the introduction of a new version into an environment where older versions may continue running.**

That changes how we should think about asset retention, cache invalidation, API compatibility, rollback, and release safety.

---

# 19. Next Session — Performance: Why Fast Code Can Feel Slow

Our application is now built, deployed, cached, and delivered. The servers are fast. The CDN is working.

The JavaScript bundles are reasonably optimized. And yet customers still complain that the website feels sluggish. Why?

Perhaps the largest image appears two seconds late. Perhaps JavaScript occupies the main thread during initialization. Perhaps a seemingly harmless widget causes layout shifts.

Perhaps a button takes half a second to respond to user input. Or perhaps the application is technically responsive but spends too much time displaying loading screens.

In **SE240-L05 — Performance: Why Fast Code Can Feel Slow**, we'll examine real user experience as a measurable engineering problem.

We'll investigate Core Web Vitals, the critical rendering path, network waterfalls, JavaScript execution costs, responsiveness, layout stability, performance budgets, and practical profiling strategies.

The key question will no longer be:

"How fast is our code?"

It will be:

**"How quickly can the customer see, understand, and interact with the application?"**

---

## Next Lecture — SE240-L05: Performance: Why Fast Code Can Feel Slow

Continue in **SE240 — Browser and Frontend Engineering**.

---

*The spoken lecture ends here. The remaining material is a screen-first investigation worksheet and technical references — skip if you are listening; revisit when you can look at the screen.*

## Optional Practical Lab — Inspect Your Own Build

These experiments need a screen and a terminal. You can use an existing Vue/Vite project; each fence is copy-paste for the shell, and the surrounding steps say what to look for in `dist/` and DevTools.

## Experiment A — Examine the output

Run `npm run build`:

```bash id="50m365"
npm run build
```

Open the generated `dist/` directory.

Inspect the filenames.

Find the generated `index.html`.

Look at its script and stylesheet references.

Ask yourself:

Which code is loaded immediately?

Which files have content hashes?

Are there separate chunks for lazily loaded routes?

Is the output organized the way you expected?

## Experiment B — Watch lazy loading

Open your built application using an appropriate local preview server—`npm run preview`:

```bash id="spkdoc"
npm run preview
```

In a conventional Vite project, this invokes `vite preview`.

It's useful for local inspection, but not intended as a full production hosting solution.

Open DevTools → Network.

Load the application's starting page.

Then navigate to a lazily loaded route.

Look for JavaScript chunks requested only after navigation.

Now you can see the connection between `import()` in your source code and actual runtime network behavior.

## Experiment C — Inspect cache headers

Against a deployed application, use `curl -I` on the document URL, for example `https://example.com/`:

```bash id="dbt69a"
curl -I https://example.com/
```

Then inspect a versioned asset such as `/assets/index.abc123.js` the same way:

```bash id="41hasd"
curl -I https://example.com/assets/index.abc123.js
```

Compare their `Cache-Control` headers.

Does the HTML require validation before reuse?

Is the asset eligible for long-lived caching?

Remember that cache behavior may be affected by intermediary configuration, not merely headers set by the origin.

## Experiment D — Simulate the broken deployment

In a local test environment, perform two builds that produce different lazy-loaded chunk filenames.

Load version A in the browser.

Keep the page open.

Replace the served assets with version B, removing the old chunks.

Then navigate to a lazy route that wasn't previously loaded.

Observe the failed chunk request.

Repeat the experiment while retaining the older assets.

You should now understand exactly why deployment retention policies matter.

Do this only in your development environment, not against a live customer application.

---

## Further Reading — Optional References

1. [Vite — Building for Production](https://vite.dev/guide/build) — Production builds, output configuration, chunking, and dynamic-import failures.
2. [Vite — Why Vite](https://vite.dev/guide/why) — Development module loading and production bundling.
3. [Vite — Features](https://vite.dev/guide/features) — Dynamic imports, CSS splitting, and preload optimizations.
4. [Vue — Server-Side Rendering](https://vuejs.org/guide/scaling-up/ssr) — SSR, hydration, mismatches, and server-side state isolation.
5. [MDN — HTTP Caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching) — Freshness, validation, and immutable asset caching.
6. [AWS — CloudFront File Versioning](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/UpdatingExistingObjects.html) — Asset versioning and edge-cache management.
7. [AWS — CloudFront Invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html) — Invalidation versus versioned filenames.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE240-L04  DELIVERING MODERN WEB APPLICATIONS — INTERVIEW GLANCE CARD

DEPLOYMENT MYSTERY
  Old tab             Still runs previous JS; lazy import → ReservationsView.OLD.js → 404
  New build           Has ReservationsView.NEW.js; deleted old chunks
  Key insight         Publishing a new frontend does not replace JS already in browsers

BUILD PIPELINE
  Source ≠ browser    .vue / TS annotations need transform; imports/assets resolved
  Vite dev            Native ESM on demand; HMR; fast start — ≠ production delivery
  Vite build          Bundled/optimized dist/: hashed JS/CSS chunks, compiled Vue
  Typecheck           vite transform ≠ vue-tsc / CI type checking
  Tree shaking        Drop unreachable exports; side-effect imports & dynamic code limit it
  Principle           Best JS cost cut = don't ship unnecessary JS

CODE SPLITTING / LAZY ROUTES
  dynamic import()    Separate chunks; load on navigation
  Trade-off           Smaller initial load vs first-navigation delay + chunk 404 risk
  Waterfall           Discover deps late → sequential fetches; preload helps
  Chunk boundaries    Match real navigation/usage

SAFE PUBLISH (static SPA + hashed assets)
  Wrong               Delete old → upload new HTML → upload assets (gaps + break old tabs)
  Better              Upload new versioned assets → verify → publish HTML → retain old assets awhile
  Optional            /releases/<id>/… + switch HTML pointer
  Principle           A release = compatible resource set that may outlive the next release
  vite:preloadError   Reload fallback only; not excuse to delete live chunks; avoid refresh loops

CACHING
  Hashed JS/CSS       Cache-Control: public, max-age=31536000, immutable (URL changes on content)
  HTML entry          Same URL across releases → no-cache / revalidate before reuse
  CDN invalidate HTML Helps edge get new shell; cannot flush running browser JS
  Pair                Stable HTML URL + controlled freshness · versioned assets + long cache

STATIC HOSTING
  SPA output          Static files (Nginx/S3/CloudFront) — Node for build ≠ required for serving
  History fallback    Refresh /reservations → serve index.html for frontend routes
  Don't rewrite       Missing /api or missing .js → HTML 200 (MIME/parse disasters)

RENDERING STRATEGIES
  CSR                 Shell HTML → download JS → execute → fetch → render (good rich SaaS)
  SSR                 Server HTML with content → display early → hydrate for interactivity
  Hydration           Client Vue binds to existing DOM; mismatch if server/client disagree
  Mismatch causes     Math.random, timezone/locale Date formatting, diverging state
  Avoid               Serialize initial state; deterministic first paint; defer browser-only
  onMounted           Browser-only (window/document); handle null SSR first paint
  SSR state hazard    Module-level mutable user state → cross-request leaks; fresh app/store per request
  SSG                 Prebuild HTML at build time; great for stable marketing/docs; freshness limits
  Mix                 Marketing SSG · public details SSR · auth dashboard CSR · live data via API
  SEO                 SSR/SSG help public discoverability; irrelevant for auth-only SaaS

CDN
  Edge cache          Hashed static easy; personalized HTML needs isolation / no shared cache

CONFIG SECRETS
  VITE_*              Embedded in client bundle at build — publicly inspectable
  Never               Put payment/API secrets in VITE_ env for the browser
  Runtime config      /config.json flexibility vs caching/init complexity
  Rule                Anything delivered to the browser is accessible to the user

RELEASE CHECKLIST
  Build/test → publish versioned assets → publish HTML → cache policy → verify → keep rollback
  Also                API compatibility with still-running old frontends (SE310-L01)

SENIOR LINE: Frontend deploy isn't atomic replacement everywhere—old versions keep running.
```

