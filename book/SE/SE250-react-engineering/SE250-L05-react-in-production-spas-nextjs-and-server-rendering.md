---
id: SE250-L05
course: SE250
title: "React in Production: SPAs, Next.js, and Server Rendering"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE250-L04
next: SE250-L06
---

# SE250 — React Engineering for Experienced Developers
## Lecture 05: React in Production — SPAs, Next.js, and Server Rendering

*Your React application works beautifully in the browser. Then someone asks why Google sees a loading screen, why the first visit feels slow, and why the server is suddenly rendering components that were supposed to be client-side.*

---

# Part I — Intuition

## 1. The Hotel Catalogue That Works Only After JavaScript Wakes Up

Imagine you're working on a hotel-booking platform with fifty thousand destination and hotel pages.

The frontend is a React application built with Vite. The backend exposes APIs for hotel descriptions, prices, availability, reviews, and reservations. The application is deployed as static assets behind a CDN.

Everything works.

A customer opens the website, searches for Amsterdam, clicks Hotel Aurora, and gets a perfectly functional page. They can explore photographs, select dates, and reserve a room.

Then the marketing department reports a problem.

Many hotel pages are performing poorly in organic search. External link previews are inconsistent. On slow mobile connections, users stare at a loading skeleton before meaningful hotel information appears.

An engineer opens the raw HTML returned by the website.

It contains the application shell, script references, and a root element.

But the actual hotel description isn't there.

The browser must download JavaScript, execute React, initialize the application, and fetch hotel data before the meaningful content appears.

Modern search engines can execute JavaScript, so this does not automatically make the content invisible to Google. But relying heavily on client-side rendering can complicate crawling, introduce rendering delays, and make content availability dependent on JavaScript execution.

More importantly, a real customer on a slow device may experience the same dependency chain.

The application is functional.

Its delivery model is poorly suited to some of its requirements.

Someone proposes migrating the catalogue to Next.js.

Another engineer replies that React already works, so changing frameworks is unnecessary.

Both have identified part of the problem.

Neither has yet defined the actual architectural trade-off.

## 2. Where Should the First Page Be Assembled?

Imagine our hotel page as a package being delivered to a customer.

With a conventional client-rendered SPA, we ship the materials and instructions. The customer's browser assembles the page after receiving them.

With server-side rendering, the server assembles the initial HTML before sending it.

With static generation, we assemble suitable pages ahead of time and store the results for delivery.

These approaches differ primarily in **where and when the initial interface is calculated**.

In a client-rendered SPA, the browser receives an HTML shell and application code. React calculates the interface after the code executes.

In server-side rendering, a server calculates HTML for the requested page and returns it to the browser.

In static generation, the page is calculated before the request, often during a build or revalidation process, and can be served from storage or a CDN.

### Visual anchor 1 — Three delivery models

```text
CLIENT-RENDERED SPA

Browser receives HTML shell
          |
          v
Downloads JavaScript
          |
          v
React executes in browser
          |
          v
Fetches hotel data
          |
          v
Meaningful page appears


REQUEST-TIME SSR

Customer requests Hotel Aurora
          |
          v
Server loads hotel data
          |
          v
Server generates HTML
          |
          v
Browser receives meaningful HTML
          |
          v
JavaScript hydrates interaction


STATIC GENERATION

Build process loads hotel data
          |
          v
Build generates HTML
          |
          v
CDN stores generated page
          |
          v
Customer receives existing HTML
```

This is a simplified picture. Real applications can overlap data fetching and rendering, stream partial responses, preload resources, and combine several techniques.

But the central question remains: **Must the browser construct the meaningful initial content, or can we provide it earlier?**

## 3. Server-Rendered HTML Is Not Yet an Interactive React Application

Suppose our server produces a beautiful hotel page.

The HTML already contains the hotel name, photographs, description, and price summary.

The browser can display it.

But the customer clicks a React-controlled date picker, and nothing happens until the corresponding JavaScript has loaded and initialized.

Why?

Because HTML can describe an interface without containing the React runtime and event handlers needed to operate it.

This is where *hydration* enters.

Hydration allows React to attach its client-side behavior to existing server-produced HTML.

The browser receives the page's initial appearance from the server, then React initializes the interactive parts using the corresponding client code.

Think of a hotel lobby already constructed and furnished before the receptionist arrives.

Customers can see the desk and signs. But some services don't operate until the staff and systems are ready.

Hydration is the process of making the preexisting interface operational.

### Visual anchor 2 — The first page visit

```text
Server
  |
  | HTML containing hotel content
  v
Browser displays initial page
  |
  | Download client JavaScript
  v
React hydrates interactive components
  |
  v
Date picker, buttons, forms operate
```

The analogy has a limitation: native browser behavior, such as ordinary links and certain HTML forms, can work before React hydrates. The page is not necessarily completely inert.

Still, hydration is a real cost.

The browser must receive, parse, and execute the relevant JavaScript, and React must initialize the interactive tree.

Server-rendered HTML improves the delivery of visible content, but it does not eliminate the need to consider JavaScript execution and main-thread responsiveness.

## 4. The Next.js Twist: Not Every Component Needs to Run in the Browser

Traditional server rendering usually meant React generated HTML on the server, and the corresponding client components then hydrated in the browser.

React Server Components introduce a different architectural idea.

Some components can execute entirely in a server environment and never send their component implementation to the browser.

Other components remain interactive and require client-side JavaScript.

Consider our hotel details page.

The hotel's name, description, location, and facilities can be obtained on the server.

These are mostly informational.

The date picker and guest-count selector require interactive browser state.

They belong in Client Components.

The page can compose both kinds.

### Visual anchor 3 — The component boundary

```text
HotelPage (Server Component)
│
├── HotelDescription (Server)
├── Facilities (Server)
├── ReviewsSummary (Server)
│
└── BookingWidget (Client)
      ├── DatePicker
      ├── GuestSelector
      └── ReserveButton
```

The Server Components can retrieve and prepare information without sending their implementation code to the browser.

The Client Components provide interactivity.

This does not mean the page is split into two separate applications.

React and Next.js compose the results into one interface.

But there are now two execution environments with different capabilities.

The server can access backend services and private credentials.

The browser can respond to clicks, maintain local interactive state, and access browser APIs.

Neither environment can freely perform every operation available to the other.

## 5. A Client Component Can Still Produce HTML on the Server

Here's a subtle point that confuses many developers.

In the Next.js App Router, adding the `"use client"` directive does not necessarily mean a component's initial HTML is generated only in the browser.

On an initial page visit, Next.js can prerender Client Components into HTML on the server too.

The directive principally establishes a client module boundary: the component and its imported client dependencies need to be available for client-side execution and interactivity.

It does not universally disable server-side HTML generation.

This explains an otherwise strange error.

A developer creates a Client Component and reads `window.localStorage` directly while the component renders.

They expect it to work because the file says `"use client"`.

But the initial rendering process may execute where `window` doesn't exist.

The component fails.

The developer has confused **being a Client Component** with **executing exclusively inside a browser**.

Those are not equivalent.

## 6. More Framework Does Not Automatically Mean More Performance

Our team is now excited about Next.js.

Server rendering, static generation, streaming, Server Components, automatic routing—wonderful.

Should every React application use it?

No.

Imagine an internal cybersecurity dashboard.

Users authenticate before seeing anything. Search-engine indexing is irrelevant. The interface consists mainly of interactive tables, filters, charts, and operational controls.

The backend already exposes well-designed APIs.

A conventional React SPA may be entirely appropriate.

It can be deployed as static assets, served from a CDN, and developed independently of the backend.

Introducing a request-time rendering server might add deployment complexity, additional failure modes, and another operational responsibility without delivering much benefit.

Now compare that with our public hotel catalogue.

It has tens of thousands of addressable pages, important search visibility, public metadata, and substantial meaningful content.

Server rendering or prerendering may provide significant advantages.

The correct choice follows the product requirements.

### A tiny comprehension check

Three proposed applications:

A public hotel catalogue with fifty thousand indexable pages.

An internal authenticated operations dashboard.

A public documentation website whose content changes infrequently.

Which delivery models sound appropriate?

The catalogue is a strong candidate for hybrid server rendering and prerendering, with interactive booking widgets.

The dashboard may be well served by a conventional SPA.

The documentation site is a strong candidate for static generation.

None of those answers requires abandoning React.

The decision concerns delivery architecture, not whether React is a good UI library.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 7. React Is a Library; Next.js Is an Application Framework

Let's establish an important distinction.

React provides component composition, rendering, state, hooks, and related UI capabilities.

It does not, by itself, prescribe a complete production application's routing, server architecture, deployment model, caching strategy, or data-loading conventions.

A Vite project provides a development environment and build tooling for a React application.

You can combine it with React Router, TanStack Query, and other libraries to construct a substantial frontend architecture.

Next.js provides an integrated application framework around React.

It includes conventions for routing, server rendering, static generation, data fetching, streaming, server functions, and deployment.

This is not merely React with a more sophisticated build command.

It introduces decisions about where code executes, how data flows between environments, and when rendered output is cached.

### 7.1 Why Vite and Next.js are not direct equivalents

Vite primarily addresses development tooling and bundling. It is not inherently a complete application framework.

Next.js includes both build tooling and application-level conventions.

A Vite React SPA can be a complete production frontend when paired with the necessary libraries and infrastructure.

Likewise, Next.js can be used for applications that perform substantial rendering and interaction in the browser.

Neither choice determines the application's quality automatically.

The comparison should consider the complete architecture, not merely the package names.

## 8. Following a Request Through a Client-Rendered SPA

Consider the first visit to our existing hotel page.

The customer requests `/hotels/aurora`.

The CDN returns the application's HTML shell.

The browser downloads the relevant JavaScript modules.

React initializes, reads the route, and renders a loading interface.

An Effect or server-state library requests hotel data.

The response arrives.

React renders the hotel description.

The browser produces the corresponding pixels.

The customer can finally inspect the hotel.

### 8.1 The client-side waterfall

A naive implementation may serialize several operations.

First load JavaScript. Then initialize React. Then discover the hotel route. Then request hotel data. Then request availability. Then render the booking widget.

Some of these steps can be parallelized or started earlier.

But if important data fetching begins only after client JavaScript has executed, a dependency chain remains.

This matters particularly on slow mobile devices or networks.

A server-rendered route can move some data retrieval and HTML generation earlier.

The browser may receive meaningful content before it has executed the complete application.

### 8.2 A SPA can still be optimized

It would be wrong to conclude that SPAs are necessarily slow.

A well-engineered SPA can use route-based code splitting, resource preloading, effective caching, CDN delivery, optimized data fetching, and sensible rendering boundaries.

For repeat visits, a cached SPA can be very responsive.

And an authenticated application may derive little value from placing all initial rendering on the server.

The actual trade-off depends on first-visit requirements, repeat navigation, device capabilities, backend latency, and the application's content.

## 9. Server-Side Rendering: What Moves to the Server?

Now consider request-time SSR.

The customer's browser requests Hotel Aurora.

The server determines which page is requested, obtains the required data, and renders HTML.

The browser can display that HTML before React's client-side behavior has fully initialized.

This changes the location of important work.

Some data fetching happens in the server environment rather than being initiated later by the browser.

Some initial HTML construction happens on the server.

But the server now participates in the customer's request path.

### 9.1 SSR trades one kind of delay for another

If hotel data takes 800 milliseconds to retrieve, the server may have to wait before producing the complete response.

The browser might receive meaningful HTML later than expected.

Streaming can reduce this problem by delivering ready portions of the page while slower sections continue rendering.

But SSR is not automatically faster on every metric.

A poorly implemented SSR application can have high time-to-first-byte, expensive server rendering, and significant hydration cost.

A fast server response and a lightweight client bundle may produce excellent results.

A slow data layer and enormous interactive bundle may produce an expensive server-rendered application that still feels sluggish.

**Server rendering changes where work happens. It does not abolish the work.**

## 10. Static Generation: Building Pages Before Visitors Arrive

Our hotel catalogue contains fifty thousand pages.

Many descriptions, locations, facilities, and photographs change relatively infrequently.

Do we need to calculate every page from scratch for every visitor?

Not necessarily.

Static generation creates suitable output ahead of time.

The resulting files can be served efficiently from a CDN.

This can reduce request-time server computation and make public content available quickly.

### 10.1 Build-time rendering has constraints

Suppose every hotel page takes 100 milliseconds of work to generate.

Generating fifty thousand pages could require substantial total computation, even if the build system parallelizes the work.

The larger and more dynamic the catalogue becomes, the more important the build and regeneration strategy becomes.

Some pages may be generated ahead of time.

Others may be rendered when needed.

Content may be revalidated and cached according to an appropriate policy.

The correct design depends on the framework version and deployment model.

### 10.2 Static content and live inventory are different

Hotel descriptions might tolerate caching for hours or longer.

Room availability cannot be treated as a permanent build-time fact.

A static hotel page should not imply that a room is guaranteed available merely because inventory was positive when the page was generated.

The application can deliver stable hotel content from a CDN while retrieving current availability separately.

This is a natural example of hybrid rendering.

We do not need every piece of information on a page to share the same freshness policy.

## 11. Server Components Are Not Simply SSR Components

This distinction is fundamental.

Traditional SSR renders React components into HTML on the server, then the browser hydrates the interactive application.

React Server Components describe components whose implementation executes in the server environment and is not included in the client bundle.

Their rendered result is represented through the React Server Component protocol.

These are related technologies, but not identical.

Server Components can execute at build time or request time, depending on the framework's rendering strategy.

Their output may be used to generate initial HTML.

On subsequent navigations, the framework can transmit updated Server Component results without necessarily performing a full document navigation.

### 11.1 Server Components do not hydrate

A Server Component's implementation is not sent to the browser for client-side execution.

It therefore does not hydrate as a Client Component.

Instead, its rendered output is incorporated into the overall React tree.

Interactive Client Components within that tree require client-side code and hydration on the initial load.

A common misunderstanding is that Server Components are React components that run once on the server and then run again in the browser.

That is not the model.

### 11.2 Why the distinction matters

Imagine a Server Component imports an expensive library to transform hotel descriptions into HTML.

Because the transformation happens on the server, the browser does not need to download that library merely to display the resulting content.

This can reduce client JavaScript.

It can also keep database drivers and certain backend integration code out of the client bundle.

But any data deliberately rendered into HTML or serialized into the client-visible payload must be treated as potentially visible to the customer.

Running a component on the server does not make all its output confidential.

## 12. The `"use client"` Boundary

In the Next.js App Router, pages and layouts are Server Components by default.

A file marked with `"use client"` establishes a boundary for a client-side module graph.

Consider the booking widget.

It needs `useState` to manage dates, event handlers to respond to clicks, and perhaps browser APIs for focus management.

It should be a Client Component.

The surrounding hotel description does not require those capabilities.

It can remain a Server Component.

### 12.1 Client boundaries propagate through imports

Suppose `BookingWidget` is marked `"use client"`.

It imports `DatePicker`, `GuestSelector`, and `ReservationButton`.

Those imported modules become part of the client module graph.

You do not need to mark every imported component separately.

However, marking an entire top-level application layout as a Client Component can pull much more code into the client graph than necessary.

A better approach is usually to establish client boundaries close to the genuinely interactive components.

This limits client JavaScript and makes server-only responsibilities clearer.

### 12.2 Composition is not the same as importing

There's a subtle but valuable exception.

A Server Component can pass server-rendered content as `children` to a Client Component.

Imagine a client-side modal that controls whether its contents are visible.

The modal can receive a Server Component's rendered result as a child.

This does not require importing the Server Component implementation into the client's module graph.

The distinction is between composing a server-rendered element and importing a server-only module from a client entry point.

Understanding that distinction allows sophisticated layouts without turning the entire application into client code.

## 13. A Concrete Next.js Hotel Page

Let's construct the important boundary.

The page retrieves hotel details on the server.

It then renders public information and passes a small, serializable summary to an interactive booking widget.

In a current App Router project, a dynamic page can receive route parameters asynchronously.

The following example illustrates that structure:

```tsx
// app/hotels/[id]/page.tsx

import { getPublicHotel } from "@/lib/hotels";
import BookingWidget from "./booking-widget";

export default async function HotelPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const hotel = await getPublicHotel(id);

  if (!hotel) {
    return <p>Hotel not found</p>;
  }

  return (
    <main>
      <h1>{hotel.name}</h1>
      <p>{hotel.description}</p>

      <BookingWidget
        hotelId={hotel.id}
        hotelName={hotel.name}
      />
    </main>
  );
}
```

The corresponding Client Component handles interaction:

```tsx
// app/hotels/[id]/booking-widget.tsx

"use client";

import { useState } from "react";

export default function BookingWidget({
  hotelId,
  hotelName,
}: {
  hotelId: string;
  hotelName: string;
}) {
  const [guests, setGuests] = useState(2);

  return (
    <section>
      <h2>Book {hotelName}</h2>
      <p>Guests: {guests}</p>

      <button onClick={() => setGuests(n => n + 1)}>
        Add guest
      </button>

      <p>Hotel ID: {hotelId}</p>
    </section>
  );
}
```

Notice what is absent.

The Server Component doesn't use `useState`.

The Client Component doesn't directly access the database.

The page doesn't serialize an entire internal hotel record, including private supplier contracts or backend credentials, into the booking widget.

The boundary passes only the information needed for interactivity.

This is an architectural choice, not merely a syntax requirement.

## 14. Props Crossing the Boundary

When a Server Component passes values into a Client Component, those values must be serializable according to React's supported server/client serialization rules.

Ordinary strings, numbers, arrays, and suitable plain data objects are common choices.

Arbitrary database connections, class instances, or closures are not appropriate props.

Special supported values and Server Function references have their own semantics.

### 14.1 Minimize exposed data

Suppose the hotel database record contains:

- Public hotel description.
- Public location.
- Internal supplier notes.
- Contractual commission rate.
- Private integration credentials.

The Client Component should receive only the public fields and values needed for its behavior.

Even if the Server Component itself can access all the fields, passing the complete object to a Client Component may expose information through serialized payloads.

Similarly, confidential values must not be embedded in HTML simply because they originated from server-side code.

**Server execution protects implementation code from the client bundle. It does not automatically protect serialized results.**

## 15. Hydration: The Server and Browser Must Agree Initially

Now we reach one of the most recognizable Next.js production bugs.

The server returns HTML containing one value.

When React hydrates on the client, its first render expects another value.

React detects a mismatch.

Suppose our hotel page renders the customer's local time using `new Date().toLocaleTimeString()`.

The server may use a different timezone, locale, or moment of execution than the browser.

The server renders one time string.

The browser renders another.

Hydration expects the initial client-rendered output to match the HTML produced on the server.

When they disagree, React may warn and attempt recovery, but the exact result depends on the mismatch.

Some differences may not be patched automatically.

### 15.1 Common mismatch causes

Hydration mismatches frequently involve nondeterministic values.

Examples include `Date.now()`, `Math.random()`, locale-dependent formatting, and rendering logic that branches according to whether `window` exists.

Invalid HTML nesting can also produce browser-parsed DOM structures that differ from React's expected tree.

Browser extensions or external scripts that modify the DOM before hydration can create further problems.

The key diagnostic question is:

> Given the same logical input, did the server and initial browser render describe the same interface?

### 15.2 A two-pass solution

If a value genuinely depends on browser-only information, one approach is to render a deterministic placeholder initially.

After hydration, an Effect reads the browser-specific value and updates React state.

That avoids asking the server to guess a browser value it cannot know.

But it also introduces an additional render and may cause visible content changes.

For large browser-only widgets, a framework-specific client-only strategy may be appropriate.

The choice depends on what the user needs to see initially.

### 15.3 Do not silence hydration warnings reflexively

React provides `suppressHydrationWarning` for narrowly unavoidable differences.

It is an escape hatch, not a general correction.

Overusing it hides genuine inconsistencies.

A developer should first determine why the server and browser disagree.

If the mismatch arises from different data, invalid markup, or nondeterministic rendering, fix the actual cause.

## 16. Browser APIs: Client Component Does Not Mean Browser-Only Rendering

Return to our hotel booking widget.

It wants to remember a display preference in `localStorage`.

A developer writes code that reads `window.localStorage` directly during rendering.

But the first page load may include server prerendering of that Client Component.

The server has no `window`.

The component can fail.

The correct approach depends on the requirement.

If the preference only matters after client initialization, read it inside an Effect and update state.

If the preference must influence the initial server-rendered appearance, consider storing an appropriate preference in a cookie accessible to server rendering.

If the component genuinely cannot render in a non-browser environment, use a supported client-only loading strategy.

Do not confuse `"use client"` with `"never executes while producing server HTML"`.

The directive defines component capabilities and module boundaries, not a universal browser-only execution guarantee.

## 17. Streaming: Don't Make the Entire Page Wait for Reviews

Our hotel page needs several pieces of data.

Hotel details take 80 milliseconds to load.

Facilities take 40 milliseconds.

Reviews take 1.5 seconds.

If the entire page waits for reviews before returning useful content, the customer experiences unnecessary delay.

React Suspense and Next.js streaming allow parts of the interface to become available independently.

The server can deliver the hotel title and description while the reviews section is still pending.

The reviews area initially displays a fallback.

When the reviews are ready, the server streams the remaining content.

### 17.1 Boundary placement matters

If the entire page is wrapped in one large Suspense boundary, the fallback may hide useful content.

If reviews have their own boundary, the main hotel information can appear sooner.

The objective is not to create a Suspense boundary around every paragraph.

It is to group content according to meaningful loading dependencies.

### 17.2 Loading conventions in Next.js

The App Router supports `loading.tsx` for route-segment loading states.

It also supports explicit Suspense boundaries for more granular behavior.

For example, the hotel page can show a skeleton for the reviews section while other information is ready.

These mechanisms influence how navigation feels, especially when some server-rendered data is slow.

### 17.3 Streaming doesn't make the backend faster

If the reviews API takes 1.5 seconds, streaming does not change that fact.

It changes whether the customer must wait for reviews before seeing the rest of the page.

That can significantly improve perceived performance.

But excessive streaming fragmentation, poorly designed loading boundaries, or slow server work can still create a confusing user experience.

## 18. Data Fetching Without Accidental Waterfalls

Server Components can fetch data using ordinary asynchronous functions.

This is convenient because data retrieval can occur close to the component that needs the data.

But it introduces a familiar risk: sequential work.

Suppose our hotel page awaits hotel details, then awaits facilities, then awaits reviews.

If those requests are independent, their total waiting time can unnecessarily accumulate.

Where dependencies permit, operations can begin concurrently.

For example, the application can start hotel-details and reviews requests together and await both using `Promise.all`.

Or it can let a slower Server Component suspend independently behind a suitable boundary.

### 18.1 Parallelism is not always correct

Some requests genuinely depend on earlier results.

Perhaps the hotel-details response identifies a supplier whose API must then be queried.

That dependency cannot simply be removed.

But unrelated requests should not become sequential merely because the code was written as consecutive `await` expressions.

This is exactly the same reasoning used in backend request orchestration.

Server Components do not abolish ordinary latency dependencies.

They give us another location in which to manage them.

## 19. Routing and Navigation: Why Next.js Feels Like an SPA

A traditional server-rendered website might perform a full document navigation for every page.

Next.js can preserve the interactive application experience through client-side navigation.

Its App Router uses file-system conventions for pages, layouts, and route segments.

A `Link` can support prefetching and navigation without necessarily reloading the entire document.

Shared layouts can remain mounted while the page content changes.

That makes navigation between hotel search, hotel details, and booking steps feel more like a client application.

### 19.1 Shared layouts preserve state

Suppose a customer navigates between hotels while a global search bar lives in a shared layout.

The layout may remain mounted during client-side navigation.

Its local state can therefore survive those transitions.

This is useful when intentional.

But it can also surprise developers who expect a form to reset whenever the route changes.

React component identity still matters.

The App Router adds another architectural layer, but the component state rules from SE250-L01 remain applicable.

### 19.2 Prefetching is a trade-off

Prefetching a likely destination can make navigation faster.

But prefetching also consumes network and server resources.

For public static hotel pages, this may be relatively inexpensive.

For dynamically rendered personalized pages, unnecessary prefetching can create additional work.

Next.js has framework-specific rules for which routes and portions are prefetched.

You should understand the behavior of the version and routing configuration you're using rather than assuming every link always downloads its entire destination.

## 20. Caching: The Most Dangerous Place to Generalize

Caching behavior is one of the areas where Next.js explanations become outdated quickly.

Older articles describe automatic caching behavior that may not accurately represent a modern Next.js 16 application.

A sound mental model separates several kinds of caching.

There may be cached data-fetch results.

There may be cached rendered server output.

There may be client-side router caches.

There may be browser caches and CDN caches.

And if the application also uses TanStack Query, it may have a separate client-side server-state cache.

These layers do not share one universal freshness policy.

### 20.1 Cache Components in Next.js 16

Next.js 16 introduced the Cache Components model.

When enabled through `cacheComponents: true`, this model uses explicit caching mechanisms such as the `"use cache"` directive, `cacheLife`, and `cacheTag`.

Dynamic work is generally treated as request-time work unless explicitly cached under the applicable model.

Developers can identify cacheable components or functions and specify suitable lifetime and invalidation behavior.

This is different from historical descriptions of implicit caching.

The exact behavior also depends on whether Cache Components is enabled.

### 20.2 The distinction is architectural

Consider a hotel description.

It changes relatively infrequently.

Caching it can be useful.

Now consider a personalized booking quote.

It may depend on the current customer, dates, supplier, inventory, and pricing rules.

Accidentally sharing that quote across users would be a serious correctness or security defect.

The framework cannot infer the full business meaning of every cached value.

Developers must establish which values are safely shareable and what makes them stale.

### 20.3 Revalidation is not universal synchronization

Next.js provides mechanisms for invalidating or refreshing server-side cached results, including cache tags and route-oriented revalidation.

But invalidating a server cache does not automatically mean every open browser tab instantly updates its interface.

Similarly, invalidating a TanStack Query cache does not automatically invalidate every CDN or server-rendered cache.

You must identify the actual caching layers involved.

The same business event may require different synchronization mechanisms depending on the architecture.

**Caching is a consistency policy distributed across layers, not a single switch called `cache: true`.**

## 21. Server Functions and Mutations

React and Next.js support Server Functions.

In mutation contexts, these are commonly called Server Actions.

A Server Function executes on the server and can be invoked through supported client-facing mechanisms.

For example, a booking form might invoke a server-side function to submit reservation information.

This can reduce the need to manually construct some traditional API plumbing.

But it does not remove the need for authorization, validation, or transactional correctness.

### 21.1 Server Functions are externally callable

A Server Function that can be invoked from the client must be treated as a publicly reachable server endpoint.

It is not protected merely because its source code is not included in the browser bundle.

A malicious client may attempt to invoke it with arbitrary inputs.

Authentication and authorization checks must occur on the server.

The submitted hotel ID, price, dates, and customer information must be validated.

A reservation cannot trust a price supplied by the browser.

### 21.2 Mutations still need business guarantees

Imagine a customer clicks Reserve and the network connection fails before receiving confirmation.

Did the backend commit the booking?

Possibly.

Retrying without appropriate idempotency controls may create duplicate reservations or charges.

Server Functions do not eliminate this distributed-systems problem.

They provide a mechanism for invoking server work.

The business operation still requires correct transactional boundaries and failure recovery.

### 21.3 `"use server"` does not mean Server Component

This is a frequent source of confusion.

`"use client"` marks a client module boundary.

`"use server"` is associated with Server Functions.

It is not the directive used to declare ordinary Server Components.

In the App Router, components are Server Components by default unless placed behind an appropriate client boundary.

Those concepts must remain separate.

## 22. Secrets, Data Access, and Security Boundaries

Our hotel platform integrates with suppliers and payment providers.

The backend has credentials that must never reach the browser.

Server Components make it convenient to perform data access in a server environment.

But convenience does not replace security design.

A server-only data-access module can retrieve hotel information, perform authorization, and return a deliberately limited public representation.

Next.js provides mechanisms such as the `server-only` import marker to prevent certain server-only modules from being imported into client code.

### 22.1 Public environment variables are public

Next.js supports exposing environment variables to browser bundles using the `NEXT_PUBLIC_` prefix.

Those values should never contain secrets.

In conventional Next.js builds, public environment values are typically inlined at build time.

This matters when promoting one application artifact between environments.

Changing the runtime environment variable afterward may not change the value already embedded in the browser bundle.

### 22.2 Server-only modules are not authorization

Marking a module as server-only prevents inappropriate client imports.

It does not prove that every call is authorized.

A server function can still return another tenant's records if the data-access layer is incorrectly scoped.

Likewise, rendering private data into HTML or serialized props exposes it to the recipient.

Authentication, authorization, tenant isolation, and output minimization remain essential.

### 22.3 Avoid leaking through caching

Server-side caching introduces additional risks.

If a cached response depends on user or tenant identity, the caching strategy must preserve that boundary.

A globally shared cache entry containing private customer information can become a cross-user data leak.

Cache keys, request context, and the chosen caching API must be designed accordingly.

The safe default is to avoid shared caching for sensitive personalized results unless the framework's semantics and isolation requirements are understood and explicitly satisfied.

## 23. Deployment: Static Assets Versus a Running Server

A conventional Vite React SPA can often be deployed as static HTML, JavaScript, CSS, and other assets.

A CDN or ordinary static web server can deliver those files.

The backend APIs run separately.

This creates a relatively simple operational boundary.

The frontend deployment does not ordinarily require an application server executing React for each incoming request.

### 23.1 Next.js may require runtime infrastructure

A Next.js application using request-time server rendering, Server Functions, or other dynamic server capabilities needs an appropriate runtime.

That may be a managed platform, a Node.js deployment, or another supported infrastructure arrangement.

Now you must consider server startup, request latency, memory consumption, deployment compatibility, observability, cache behavior, and scaling.

The deployment architecture has changed.

### 23.2 Next.js can also export static sites

Next.js supports static export for compatible applications.

In that mode, pages are generated during the build and deployed as static assets.

But features that require request-time server behavior are not available in a purely static export.

This includes important dynamic features such as request-dependent rendering, server actions, and certain routing capabilities.

A project using Next.js does not automatically require a running Next.js server, but its chosen features determine deployment requirements.

### 23.3 Operational simplicity is valuable

If our application is an authenticated internal dashboard and a SPA satisfies the product requirements, static deployment may be a genuine advantage.

It avoids adding another request-time compute layer.

If the application is a large public catalogue requiring server-side composition, dynamic metadata, and hybrid rendering, the extra runtime may be justified.

The engineering decision is not about choosing the most modern stack.

It is about paying for complexity only when the product benefits.

## 24. A Hybrid Architecture for the Hotel Platform

Let's design a plausible architecture for our fifty-thousand-page catalogue.

Public hotel descriptions can be rendered on the server or prerendered with suitable caching policies.

Search pages can expose useful metadata and meaningful initial content.

Interactive filtering, calendars, guest selectors, and booking forms remain Client Components.

Availability and personalized quotes use appropriately fresh, authoritative backend data.

Reservation submission occurs through a secured mutation boundary.

The backend enforces inventory, pricing, authorization, and transaction correctness.

Some components may use TanStack Query for client-side caching and refetching.

Server-side cache policies handle suitable public content.

Navigation uses framework routing and streaming where beneficial.

The important architectural feature is that different parts of the application have different delivery and freshness requirements.

We do not need every component to run in the same environment or use the same caching strategy.

### 24.1 Avoid duplicating the backend

One potential mistake is moving all business logic from an existing backend into Next.js merely because the framework supports server code.

If the platform already has mature reservation, payments, inventory, and supplier services, those systems may remain authoritative.

Next.js can act as a frontend-oriented server layer.

It can compose data, manage rendering, and provide appropriate boundary APIs without becoming a replacement for every backend service.

This resembles a backend-for-frontend architecture.

It is often a reasonable compromise for an existing production system.

## 25. Making the SPA Versus Next.js Decision

Imagine two projects.

The first is our public hotel catalogue.

Its pages need useful initial HTML, discoverable metadata, efficient first visits, and a mixture of stable public information and interactive booking behavior.

A framework supporting server rendering and static generation is a strong candidate.

The second project is an internal security operations dashboard.

It has authenticated users, dense interactions, numerous filters, and already-established backend APIs.

Search-engine indexing provides no meaningful value.

A client-rendered React SPA may be the simpler and more appropriate choice.

### 25.1 Questions worth asking before choosing

How important is initial HTML content?

Does search visibility matter?

What proportion of the interface is highly interactive?

Can meaningful content be prerendered?

How frequently does the data change?

Does the team already operate suitable server infrastructure?

Are there existing backend APIs?

What are the expected traffic patterns and geographic distribution?

What does the team understand well enough to debug in production?

These questions determine the appropriate complexity.

### 25.2 The wrong migration motivation

A weak reason to adopt Next.js is:

> Everyone uses it.

Another weak reason is:

> React SPAs are outdated.

Neither is a technical requirement.

A stronger reason is:

> We need public pages with reliable server-produced content and metadata, and we can justify the operational cost of hybrid rendering.

Or:

> We need request-time server composition and controlled client JavaScript boundaries.

These are defensible architectural claims.

## 26. The Production Debugging Playbook

Suppose our hotel catalogue has moved to Next.js.

Customers report three problems.

The initial page sometimes produces a hydration warning.

A private hotel quote appears stale after navigating back from checkout.

And the reviews section delays the entire page.

Do not treat them as one generic Next.js problem.

### Problem one — Hydration mismatch

Inspect the server-produced HTML and the initial browser render.

Look for nondeterministic values, browser-only APIs used during rendering, mismatched data, and invalid markup.

Determine whether a Client Component is being prerendered with assumptions that differ from the browser environment.

Fix the divergence rather than suppressing the warning.

### Problem two — Stale private quote

Identify which layer owns the quote.

Is it client-side query state, server-rendered output, router-cached data, or another cache?

Does the quote depend on customer identity and selected dates?

What mutation should invalidate or refresh it?

Are private results isolated correctly?

Avoid randomly disabling all caches before understanding which one is responsible.

### Problem three — Slow reviews

Measure the data dependency chain.

If reviews are independent of the main hotel content, consider placing them behind a separate Suspense boundary.

Allow useful content to arrive earlier.

Also investigate whether the reviews request itself can be optimized.

Streaming improves delivery sequencing, not backend response time.

### The important conclusion

React's fundamental rendering model still applies.

But production frameworks add new layers: server execution, serialization, HTML generation, caching, routing, and hydration.

When debugging, you must identify which layer owns the observed behavior.

Otherwise, you may fix a client component when the real problem is stale server output, or rewrite a data-fetching hook when the problem is a hydration mismatch.

---

# The Oral Examination

Answer each question aloud before reading the solutions.

## Question 1 — The Public Catalogue

A company has fifty thousand publicly addressable hotel pages. The current SPA performs well after loading, but initial visits are slow and search indexing is inconsistent.

Would you consider server rendering or static generation?

What evidence would you collect before recommending a migration?

## Question 2 — The Internal Dashboard

An authenticated React dashboard uses complex client-side filters and charts. SEO is irrelevant, and mature backend APIs already exist.

Does moving to Next.js necessarily improve the system?

Defend your answer.

## Question 3 — Server Components Versus SSR

Explain the difference between traditional server-side rendering and React Server Components.

Does a Server Component hydrate in the browser?

Can Server Components execute at build time?

## Question 4 — The Client Component Trap

A developer adds `"use client"` to a component and reads `window.localStorage` during rendering.

The application throws an error during initial loading.

Why?

What are two legitimate ways to handle browser-dependent values?

## Question 5 — The Hydration Mismatch

A component displays `new Date().toLocaleTimeString()` during rendering.

The server and browser produce different strings.

What happens during hydration?

Why is `suppressHydrationWarning` not the preferred general solution?

## Question 6 — The Server Boundary

A Server Component retrieves a hotel record containing public descriptions and private supplier credentials.

It passes the entire record to a Client Component.

Is the private data protected because the original component ran on the server?

Explain.

## Question 7 — The Slow Reviews

Hotel details load in 100 milliseconds. Reviews take 1.5 seconds.

How could Suspense and streaming improve the initial experience?

What would remain slow?

## Question 8 — The Cache Mystery

A Next.js application uses Server Components, server-side caching, and TanStack Query in interactive widgets.

After a reservation, one screen shows updated availability while another remains stale.

How would you identify the responsible caching layer?

## Question 9 — Server Functions

A reservation mutation is implemented as a Server Function.

Can the developer assume it is secure because the function executes on the server?

What checks and guarantees are still required?

## Question 10 — Static Deployment

Can a Next.js application be deployed as static files?

What kinds of features prevent a purely static export from being sufficient?

## Question 11 — Architecture Interview

Design a public hotel details page with a description, reviews, live availability, date selection, and reservation submission.

Choose which responsibilities belong in Server Components, Client Components, and backend services.

Explain the rendering, caching, and security boundaries.

---

# Solutions and Discussion

## Solution 1 — The Public Catalogue

Yes, server rendering or prerendering is worth considering.

Investigate initial HTML content, real-user performance, crawler behavior, indexing coverage, metadata correctness, JavaScript payload size, and the existing client-loading waterfall.

A migration should target measurable problems rather than being justified solely by framework popularity.

## Solution 2 — The Internal Dashboard

Not necessarily.

A SPA may already provide an efficient and operationally simple architecture.

Next.js could still provide routing, server composition, or other benefits, but those must justify the additional framework and deployment complexity.

SEO alone provides no argument for this application.

## Solution 3 — Server Components Versus SSR

SSR produces initial HTML on the server for a React application that may subsequently hydrate interactive components.

Server Components execute in a server environment, and their implementation is not delivered to the browser.

They do not hydrate as Server Components.

They may execute at build time or request time according to the rendering architecture.

## Solution 4 — The Client Component Trap

Client Components can be prerendered into HTML on the server for initial requests.

The server environment does not provide browser APIs such as `window` or `localStorage`.

Possible solutions include reading browser-specific values after mount through an Effect or using a suitable client-only rendering strategy.

If the initial appearance must reflect a preference, consider a server-readable mechanism such as a cookie where appropriate.

## Solution 5 — Hydration Mismatch

React expects the initial client-rendered output to correspond to the server-produced HTML.

Different time strings violate that expectation and may produce warnings or recovery behavior.

Prefer deterministic initial output, consistent formatting inputs, or an intentional post-hydration update.

Suppressing warnings without investigating the cause can hide genuine defects.

## Solution 6 — The Server Boundary

No.

The Server Component's implementation is not shipped, but serialized props and rendered content can be visible to the client.

Passing the complete record may expose private fields.

The server should return an intentionally limited public data representation.

Authorization and output minimization remain necessary.

## Solution 7 — The Slow Reviews

The hotel title and description can render without waiting for reviews.

A separate Suspense boundary allows the reviews section to show fallback content until its data is ready.

The reviews request still takes 1.5 seconds unless its underlying data access is improved.

Streaming changes delivery order, not the response time of the dependency.

## Solution 8 — The Cache Mystery

Identify each representation and its ownership.

Inspect client-side query keys, server-side caching policy, router refresh behavior, and mutation invalidation.

Determine which cache contains the stale value and whether the mutation should affect it.

Do not assume invalidating one cache automatically refreshes every other layer.

## Solution 9 — Server Functions

No.

The function remains reachable through supported network invocation mechanisms.

It must authenticate and authorize the caller, validate input, enforce tenant boundaries, and apply correct business transaction logic.

Reservation and payment operations also need safe retry and idempotency behavior.

## Solution 10 — Static Deployment

Yes, Next.js supports static export for compatible applications.

But request-time server rendering, Server Functions, dynamic request-dependent behavior, and other runtime-specific capabilities cannot simply operate from static files.

The application must choose features consistent with its deployment model.

## Solution 11 — Architecture Interview

Public hotel descriptions and suitable stable information can be rendered or prerendered on the server.

Reviews may be streamed separately when they are slow.

Date selection and guest-count controls belong in Client Components.

Availability needs an appropriate freshness policy, with the backend remaining authoritative.

Reservation submission occurs through a secured mutation boundary with server-side validation and transaction controls.

Private data must not be serialized unnecessarily, and caching policies must distinguish public content from personalized quotes.

---

# The Mental Model Worth Keeping

A React application has two different architectural dimensions.

**The UI dimension:** components, state, rendering, Effects, identity, and interaction.

**The delivery dimension:** where components execute, when HTML is generated, which code reaches the browser, how data is cached, and how server and client representations remain consistent.

React provides the component model.

Frameworks such as Next.js add production delivery machinery around that model.

When evaluating a rendering architecture, ask:

**Where does this code execute? When is this content generated? What must reach the browser? Who owns data freshness? What must remain private?**

A good system deliberately places each responsibility in the environment where it belongs.

---

# Next Lecture — SE250-L06: The React Debugging Interview Studio

We have completed the conceptual foundation of React engineering.

We understand state snapshots, component identity, Effects, asynchronous closures, server-state architecture, rendering performance, testing, and server/client boundaries.

Now comes the uncomfortable part.

A real interviewer does not ask you to recite six lectures.

They open an unfamiliar codebase and show you a broken feature.

A reservation displays the wrong dates.

A list re-renders excessively.

A custom hook retains stale state.

A page crashes during hydration.

You're expected to investigate the problem, explain the mechanism, implement a correction, and defend your reasoning.

SE250-L06 is therefore not another lecture about React APIs.

It is an integrated debugging studio.

The goal is to demonstrate that you can reason about React independently.

*The spoken lecture ends here. The following practical investigations are designed for on-screen work.*

---

# Optional Practical Lab — Server and Client Boundary Investigations

## Working Protocol

For each investigation:

**Predict → Reproduce → Inspect → Diagnose → Correct → Verify → AI Review.**

Do not let AI diagnose the defect before your first attempt.

You may use Cursor to create the project scaffolding and insert the broken examples.

Keep observations and hypotheses in a short investigation log.

## Lab A — A Client Component That Crashes Before the Browser Loads

### Objective

Reproduce a server/client environment mistake.

Understand why `"use client"` does not guarantee browser-only execution during initial rendering.

### Setup

Create a new Next.js application using the App Router, TypeScript, and a `src` directory.

```bash
npx create-next-app@latest react-delivery-lab \
  --typescript --eslint --app --src-dir --use-npm

cd react-delivery-lab
npm run dev
```

The commands use the current create-next-app workflow. Confirm prompts and generated project configuration if the installed CLI version differs.

### Broken implementation

Create a Client Component that reads the browser's local storage during rendering.

```tsx
// src/app/preferences.tsx

"use client";

export default function Preferences() {
  const theme = window.localStorage.getItem("theme")
    ?? "light";

  return <p>Preferred theme: {theme}</p>;
}
```

Render it from the home page:

```tsx
// src/app/page.tsx

import Preferences from "./preferences";

export default function Page() {
  return (
    <main>
      <h1>Hotel Preferences</h1>
      <Preferences />
    </main>
  );
}
```

### Tasks

Predict whether the page can render successfully during the initial request.

Start the development server and observe the result.

Explain why the Client Component may execute during server prerendering.

Correct it by rendering a deterministic initial value and reading local storage after mount.

Then use the browser's developer tools to set a stored preference and reload the page.

Verify that the preference eventually appears.

### Acceptance criteria

The initial request no longer crashes.

Server-produced and initial client-rendered markup agree.

Browser-specific behavior occurs in a suitable lifecycle phase.

You can explain the additional post-hydration render and its UX implications.

---

## Lab B — The Hydration Mismatch

### Objective

Create a deterministic hydration mismatch, then correct it without suppressing warnings.

### Broken implementation

Create a Client Component whose output explicitly differs between server and browser environments.

```tsx
// src/app/environment-label.tsx

"use client";

export default function EnvironmentLabel() {
  const environment =
    typeof window === "undefined"
      ? "Server"
      : "Browser";

  return <p>Rendered for: {environment}</p>;
}
```

Render it from the home page.

### Tasks

Predict the value produced during server prerendering.

Predict the value produced during the initial browser render.

Observe the development hydration warning.

Explain why the mismatch occurs even though the component is marked `"use client"`.

Correct the implementation by using an initial value that is identical in both environments, then changing it after hydration.

Do not use `suppressHydrationWarning`.

### Acceptance criteria

The corrected component hydrates without mismatch warnings.

The final browser value is displayed after hydration.

You understand why React requires matching initial output.

---

## Lab C — Server Components and Interactive Islands

### Objective

Build a small hotel-details page using a Server Component and an interactive Client Component.

### Requirements

Create a route at `/hotels/aurora`.

The server-rendered page should display Hotel Aurora's public description and facilities.

A Client Component should allow the customer to increase or decrease the number of guests.

The guest-count component must use local state.

The Server Component should not use `useState`.

### Suggested structure

```text
src/
  app/
    hotels/
      [id]/
        page.tsx
        booking-widget.tsx
  lib/
    hotels.ts
```

### Tasks

Implement a server-only data-access function returning a public hotel record.

Have the route read the dynamic hotel ID.

Render the description on the server.

Pass only the data needed for the booking widget into the Client Component.

Run the application.

Inspect the initial HTML and the browser JavaScript bundle behavior using development tools.

Explain why the hotel-description code does not need to be shipped as client component implementation.

### Stretch task

Add another hotel route.

Make sure switching routes initializes the correct hotel data while respecting intentional preservation of shared layout state.

---

## Lab D — A Streaming Page with Slow Reviews

### Objective

Demonstrate that slow secondary data should not necessarily delay meaningful primary content.

### Setup

Create an asynchronous reviews component that waits two seconds before returning review content.

Use a controlled delay for the experiment.

The main hotel description should be immediately available.

### Tasks

First, implement the page so that the main page component awaits the reviews data before returning its complete UI.

Observe the loading behavior.

Then move the reviews work into a separate asynchronous Server Component and wrap it in Suspense.

Use a meaningful fallback such as "Loading guest reviews."

Verify that the main hotel description can appear while reviews are still pending.

### Acceptance criteria

The customer sees primary hotel information before reviews complete.

The reviews eventually appear.

You can explain which operation still takes two seconds and which part of the user experience improved.

---

## Lab E — The Architecture Decision Memo

### Scenario

Your team operates two React applications.

**Application A — Public hotel catalogue**

Approximately fifty thousand public pages, SEO-sensitive content, mostly stable descriptions, live availability, and interactive booking flows.

**Application B — Internal security dashboard**

Authenticated users, large interactive tables, complex filtering, existing backend APIs, no requirement for search-engine indexing, and deployment through a CDN.

### Assignment

Prepare a short architecture decision record for each application.

Include:

- Recommended rendering and delivery model.
- Data-fetching strategy.
- What should run in the browser.
- What should run on a server or during a build.
- Caching and freshness requirements.
- Deployment and operational implications.
- Main failure modes.
- Conditions under which you would reconsider the decision.

Do not assume both applications need the same framework.

### Evaluation criteria

The decision should connect technical choices to product constraints.

It should acknowledge meaningful trade-offs.

It should not treat React Server Components or Next.js as universal upgrades.

---

# Lab Solutions and Diagnostic Notes

**Read only after completing your own investigations.**

## Lab A — Browser API Access

The broken Client Component reads `window` during rendering.

Initial prerendering may happen on the server, where `window` does not exist.

A correction can initialize state to a deterministic placeholder and read local storage in an Effect.

```tsx
"use client";

import { useEffect, useState } from "react";

export default function Preferences() {
  const [theme, setTheme] = useState<string | null>(
    null
  );

  useEffect(() => {
    setTheme(
      window.localStorage.getItem("theme") ?? "light"
    );
  }, []);

  return (
    <p>
      Preferred theme: {theme ?? "Loading preference"}
    </p>
  );
}
```

The initial server output and initial browser render both display the placeholder.

After hydration, the Effect reads the browser value and triggers another render.

For theme preferences that must affect initial appearance, a server-readable cookie or other appropriate mechanism may provide a better experience.

## Lab B — Hydration Mismatch

The broken component produces "Server" during server prerendering and "Browser" during the browser's first render.

That violates the hydration requirement.

A corrected version can initialize to the same value in both environments and update after mount.

```tsx
"use client";

import { useEffect, useState } from "react";

export default function EnvironmentLabel() {
  const [environment, setEnvironment] =
    useState("Initializing");

  useEffect(() => {
    setEnvironment("Browser");
  }, []);

  return <p>Rendered for: {environment}</p>;
}
```

This avoids the mismatch at the cost of an additional client update.

## Lab C — Server and Client Boundaries

The server page retrieves a public hotel representation.

The booking widget uses `"use client"` and manages interactive guest count.

The boundary should pass serializable values such as hotel ID and display name.

Server-only data-access code should not be imported into the Client Component.

The client should not receive private supplier credentials or internal database records.

## Lab D — Streaming

Separating slow reviews into a Suspense-wrapped asynchronous Server Component allows primary hotel content to become available without waiting for the reviews.

The review operation remains slow.

Streaming improves the delivery sequence.

A suitable boundary makes the loading state local to the delayed content.

## Lab E — Architecture Decisions

Application A is a strong candidate for hybrid rendering using a framework such as Next.js.

Public hotel descriptions can be prerendered or server-rendered, while interactive booking controls remain client-side.

Live inventory must retain an appropriate freshness policy and authoritative backend validation.

Application B may be better served by a conventional React SPA, especially when existing APIs and static deployment already satisfy its requirements.

The key difference is not application complexity alone.

It is the nature of the initial content, rendering requirements, data boundaries, and operational constraints.

---

# Further Reading

1. **React — Server Components**  
   https://react.dev/reference/rsc/server-components

2. **React — `hydrateRoot`**  
   https://react.dev/reference/react-dom/client/hydrateRoot

3. **Next.js — Server and Client Components**  
   https://nextjs.org/docs/app/getting-started/server-and-client-components

4. **Next.js — Fetching Data**  
   https://nextjs.org/docs/app/getting-started/fetching-data

5. **Next.js — Linking and Navigating**  
   https://nextjs.org/docs/app/getting-started/linking-and-navigating

6. **Next.js — Static Exports**  
   https://nextjs.org/docs/app/guides/static-exports

7. **Next.js — Cache Components**  
   https://nextjs.org/docs/app/api-reference/config/next-config-js/cacheComponents

8. **Next.js — `use cache`**  
   https://nextjs.org/docs/app/api-reference/directives/use-cache

9. **Next.js — Revalidating Data**  
   https://nextjs.org/docs/app/getting-started/revalidating

10. **Next.js — Mutating Data**  
    https://nextjs.org/docs/app/getting-started/mutating-data

11. **Next.js — Data Security**  
    https://nextjs.org/docs/app/guides/data-security

12. **Next.js — Environment Variables**  
    https://nextjs.org/docs/app/guides/environment-variables

13. **Next.js — Production Checklist**  
    https://nextjs.org/docs/app/guides/production-checklist

Cross-reference SE240-L04 for broader web delivery architecture, SE215-L08 for technical SEO, SE250-L01 for React rendering and identity, SE250-L02 for Effect synchronization, SE250-L03 for server-state ownership, and SE250-L04 for performance and Suspense fundamentals.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE250-L05 — REACT PRODUCTION DELIVERY
================================================

REACT VS FRAMEWORK
------------------
React:
  Components, state, rendering, hooks

Vite:
  Development tooling and build pipeline

Next.js:
  React application framework
  Routing, server rendering, data loading,
  streaming, server/client boundaries

SPA
---
HTML shell -> JS -> React -> data -> content

Advantages:
- static deployment
- independent frontend/backend
- strong interactivity
- operational simplicity

Trade-offs:
- initial JS dependency
- possible client data waterfalls
- content indexing considerations

SSR
---
Request -> server data/render -> HTML
        -> browser hydration

Advantages:
- useful initial HTML
- server data composition
- metadata/content delivery

Costs:
- server runtime
- request-time work
- hydration
- operational complexity

STATIC GENERATION
-----------------
Build/revalidation -> HTML -> CDN

Good:
- stable public content
- documentation
- catalogue descriptions

Poor fit:
- always-current private inventory
- request-specific personalized data

SERVER COMPONENTS
-----------------
Execute in server environment.
Implementation not shipped to browser.
Can run at build or request time.
Can fetch data and use server-only modules.
Cannot use client state/event hooks.

Server Component != SSR Client Component.
Server Component does not hydrate.

CLIENT COMPONENTS
-----------------
"use client" declares client module boundary.

Can use:
- useState
- Effects
- event handlers
- browser APIs at appropriate time

Initial HTML can still be prerendered
on the server.

"use client" != browser-only rendering.

USE SERVER
----------
Marks Server Functions.
Not the marker for Server Components.

SERVER/CLIENT DATA
------------------
Pass supported serializable values.
Minimize data exposed to client.
Do not pass arbitrary server resources.
Never serialize secrets or private records.

HYDRATION
---------
Server HTML must match initial
client-rendered output.

Common failures:
- Date.now()
- Math.random()
- locale/timezone differences
- browser API branches during render
- different server/client data
- invalid HTML nesting

Fix root cause.
Do not reflexively suppress warnings.

SUSPENSE AND STREAMING
----------------------
Allow ready content to appear early.
Slow regions can display fallbacks.
Place boundaries around meaningful
loading dependencies.

Streaming != faster backend request.

DATA FETCHING
-------------
Avoid unnecessary sequential awaits.
Parallelize independent operations.
Keep true dependencies ordered.

NEXT APP ROUTER
---------------
app/.../page.tsx
app/.../layout.tsx
app/.../loading.tsx
app/.../error.tsx

Dynamic route:
app/hotels/[id]/page.tsx

Current route params can be Promise-based.

NAVIGATION
----------
Link supports client-side transitions.
Shared layouts may preserve state.
Prefetch behavior depends on route type.
Streaming improves slow navigation UX.

CACHING LAYERS
--------------
Server data/cache
Rendered server output
Client router cache
Browser cache
CDN cache
TanStack Query cache (when used)

They are not automatically synchronized.

NEXT.JS 16 CACHE COMPONENTS
---------------------------
Feature enabled by:
cacheComponents: true

Explicit caching:
"use cache"
cacheLife
cacheTag

Legacy caching models differ.
Check actual project configuration.

AUTHORITY
---------
Public hotel description:
  cacheable with suitable policy

Personalized quote:
  sensitive, request-dependent

Final reservation:
  backend authoritative

SERVER FUNCTIONS
----------------
Server-side invocation mechanism.
Network-reachable when exposed.

Must:
- authenticate
- authorize
- validate input
- enforce tenant isolation
- maintain transactional correctness

Server Functions are NOT
automatically trusted endpoints.

SECURITY
--------
server-only:
  prevents inappropriate client imports

NEXT_PUBLIC_*:
  exposed to browser bundle
  typically build-time inlined

Server-only execution does not make
rendered/serialized data confidential.

CACHE SECURITY
--------------
Do not share private cached data
across users or tenants.

Cache identity and policy must account
for authorization and personalization.

DEPLOYMENT
----------
SPA:
  static CDN hosting often sufficient

Next.js dynamic features:
  appropriate runtime required

Next.js static export:
  possible for compatible features
  excludes request-time server behavior

WHEN TO CHOOSE SPA
------------------
- authenticated internal application
- primarily interactive UI
- established backend APIs
- little SEO need
- static deployment valued

WHEN TO CONSIDER NEXT.JS
------------------------
- important initial HTML
- public indexable pages
- hybrid rendering needs
- server-side composition
- streaming or prerendering benefits

DO NOT CHOOSE BY HYPE.

DEBUGGING QUESTIONS
-------------------
1. Where did this code execute?
2. When was content generated?
3. What was serialized to the browser?
4. Was HTML hydrated consistently?
5. Which cache owns the stale value?
6. What invalidates that cache?
7. Does the server enforce authorization?
8. Is the added runtime complexity justified?

NEXT
----
SE250-L06
The React Debugging Interview Studio
```
