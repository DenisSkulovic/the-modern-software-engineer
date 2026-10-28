---
id: SE215-L08
course: SE215
title: "Technical SEO and Web Discoverability"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L07
next: SE215-L09
---

# SE215 — The Software Engineering Ecosystem

## Lecture 08: Technical SEO and Web Discoverability

*Your team replaces an aging hotel catalogue with a beautifully engineered Vue application. The new pages load faster, the API performs better, the UI is responsive, and every end-to-end test passes. Three weeks later, organic search traffic has fallen dramatically. The marketing department wants to know what engineering broke. You open the website and everything works. Where do you even begin?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine Mercury, our hotel-booking company, owns a catalogue containing fifty thousand hotels.

Every hotel has a public page.

One page describes Hotel Alexander in Berlin. It contains photographs, room information, amenities, a description, and links to nearby hotels.

A person visiting the page directly has no difficulty using it.

But Mercury depends on something else.

People search for hotels in Berlin through Google and other search engines, and those engines need to discover Mercury's pages before potential customers can find them.

This introduces an entire process that ordinary application testing doesn't cover.

A browser test opens a known URL and verifies that the application works.

A search engine must first discover that the URL exists.

Then it must obtain the page, understand its content, decide whether that page belongs in its index, and determine whether it's relevant to a particular search.

**A page can be functional, accessible through a direct link, and still effectively invisible to search engines.**

That's today's central idea.

## 1. The search engine is another consumer of your application

As developers, we're accustomed to thinking about browsers as our primary clients.

The browser receives HTML, CSS, and JavaScript, executes the application, and presents the interface.

Search crawlers are different consumers.

They visit publicly accessible URLs, retrieve resources, discover links, and process content.

Some crawlers can execute JavaScript. Others have different capabilities.

Google, in particular, can render JavaScript-powered pages using a Chromium-based rendering system.

But this doesn't make the difference between initial HTML and client-rendered content irrelevant.

Suppose a hotel's description appears only after several JavaScript operations and a remote API request.

The content may be available to an ordinary browser user.

Whether a crawler processes that content successfully depends on what resources it can access, what it renders, and what it observes.

We need to understand both the application and the crawler's view of it.

## 2. Three distinct stages: crawling, indexing, and ranking

Imagine a librarian organizing a huge collection of books.

First, the librarian must discover which books exist.

Then examine and catalogue them.

Finally, when someone asks a question, decide which books are useful.

Search engines perform related activities.

**Crawling** is the process of discovering and retrieving URLs and resources.

**Indexing** involves understanding content, identifying representative pages, and deciding what information should be stored for retrieval.

**Serving and ranking** involve choosing which indexed results are relevant to a particular search and how to display them.

A failure at one stage can resemble a failure at another.

If the crawler never discovers a hotel page, it cannot index that page through ordinary discovery.

If the crawler retrieves a page containing an indexing prohibition, that page may be excluded from results.

If a page is successfully indexed but doesn't answer relevant searches well, it may receive little traffic anyway.

So when organic traffic falls, our first job is not to apply random SEO techniques.

It's to determine which stage is failing.

## 3. A small deployment mistake can affect thousands of pages

Let's return to Mercury's redesign.

The old catalogue used server-rendered HTML.

The new version uses a client-side application.

Developers test the pages and see no obvious problems.

But several changes happened during migration.

Some hotel URLs now return an almost-empty HTML shell.

The sitemap still contains outdated paths.

A layout template accidentally includes a `noindex` directive.

Several pages point their canonical URLs to the catalogue home page.

And a fallback route returns HTTP 200 even when the requested hotel does not exist.

Each mistake has a different consequence.

Some affect content processing.

Some affect discovery.

Some affect indexing decisions.

Some make distinct pages appear to be duplicates.

The website is functioning as a user interface, but its public information architecture has become inconsistent.

That's the kind of problem a developer needs to recognize.

## 4. Technical SEO isn't the same as marketing

Search engine optimization is often associated with keywords, marketing campaigns, and writing articles.

Those activities exist, but they aren't our primary concern.

Technical SEO addresses how a website makes its content accessible, interpretable, and appropriately represented to search engines.

Developers commonly influence URL design, HTML output, status codes, redirects, metadata, sitemaps, rendering, performance, and structured data.

An SEO specialist may define which pages the business wants search engines to discover.

A developer makes sure the platform can expose those pages correctly.

The two need to cooperate.

A page with technically perfect markup but useless content may receive little traffic.

And excellent content hidden behind broken routing or indexing directives may never get a fair chance to appear.

Neither discipline replaces the other.

## Three questions before the Deep Dive

1. Why doesn't a successful Playwright test prove that a hotel page can appear in Google Search?
2. What is the difference between a search crawler retrieving a page and a search engine choosing to index it?
3. If Mercury's traffic falls after a deployment, why should we investigate indexing evidence before rewriting page titles or descriptions?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The first investigation: what actually changed?

Mercury's organic traffic has fallen.

Before modifying code, let's establish the symptoms.

Did the decline begin immediately after the new frontend deployment?

Did it affect every public page or only hotel-detail pages?

Did search impressions decrease, or did impressions remain stable while clicks fell?

Did particular languages or countries experience the decline?

Are the affected URLs still indexed?

Does the issue coincide with the deployment, a change in search demand, or something else?

These questions distinguish several possible failures.

If impressions collapse because thousands of URLs are no longer indexed, that's different from stable impressions accompanied by lower click-through rates.

The latter might involve result presentation or changing search behavior.

If only French-language hotel pages are affected, the problem may involve localization or URL mapping.

If errors spike on hotel-detail routes, infrastructure or rendering may be responsible.

A good investigation begins by narrowing the failure, not by applying an SEO checklist indiscriminately.

## 2. URL discovery: how does a crawler find your pages?

Imagine Mercury has fifty thousand hotel URLs.

The crawler knows the home page.

How does it discover the individual hotels?

One mechanism is ordinary links.

A city page links to hotel-detail pages.

Those pages link to related properties.

A crawler follows discoverable links and encounters new URLs.

This is why site architecture matters.

A public page buried behind a search form, an authenticated endpoint, or JavaScript-only interaction without suitable links may be difficult to discover.

### Use actual navigational links

For public navigation, standard HTML anchors with meaningful `href` values provide a clear, crawlable relationship.

A clickable element implemented exclusively through a JavaScript event handler may work for users but offer poorer discoverability to crawlers.

A frontend router can still handle client-side navigation while preserving real URLs and proper anchor elements.

The lesson is not that every interface action needs an anchor.

It's that navigation to a distinct public page should expose a meaningful destination.

### Sitemaps

Mercury can also publish an XML sitemap listing important public URLs.

A sitemap helps search engines discover URLs that the website wants crawled.

For a large catalogue, Mercury may use several sitemap files organized through a sitemap index.

An entry can include a last-modified timestamp when the site can accurately provide that information.

But there are two important qualifications.

A sitemap is not a substitute for coherent internal linking.

And including a URL in a sitemap does **not** guarantee that a search engine will index it.

The sitemap communicates discovery information and preferences.

It doesn't command the search engine to include every page.

### The outdated-sitemap failure

Suppose Mercury changes hotel URLs from `/hotel/9821` to `/hotels/berlin/alexander`.

But the sitemap still lists the old URLs.

The crawler now follows outdated destinations, perhaps through redirects or failed requests.

This doesn't necessarily destroy discoverability by itself, but it creates inconsistent signals and unnecessary work.

The updated sitemap should list the intended canonical URLs.

Old destinations should receive suitable redirects when the content has genuinely moved.

## 3. Crawl control isn't index control

Now imagine Mercury wants to prevent search engines from accessing internal administration routes.

A developer adds rules to `robots.txt`.

This file communicates crawling instructions to cooperative crawlers.

It can tell them not to request particular URL paths.

However, it's important not to misunderstand its purpose.

**`robots.txt` is not an access-control system, and blocking a URL from crawling does not guarantee that the URL cannot appear in search results.**

A search engine may discover a URL from another website and know the URL exists even if it cannot crawl its content.

And malicious clients aren't required to respect `robots.txt` at all.

Private information requires real authentication and authorization.

### The `noindex` distinction

Suppose Mercury has a publicly accessible promotion page that shouldn't appear in search results.

An appropriate indexing directive may be `noindex`, delivered through an HTML robots meta tag or a suitable HTTP header.

For example, an HTML page can declare that it shouldn't be indexed.

But here's the trap:

If the URL is blocked by `robots.txt`, Google may never retrieve the page and therefore never see its `noindex` instruction.

The team accidentally combines two controls that interfere with one another.

For pages intended to be removed from Google Search through `noindex`, the crawler must be allowed to access the relevant directive.

### Three separate requirements

Avoid treating these as interchangeable.

If the page contains private information, enforce access controls.

If the page may be publicly accessed but shouldn't appear in search, use the appropriate indexing controls.

If the goal is to manage cooperative crawler access, consider `robots.txt`.

Different requirements need different mechanisms.

## 4. HTTP status codes are part of SEO

Now consider an old hotel that is no longer listed.

The customer visits its previous URL.

Mercury's frontend displays a message saying the hotel cannot be found.

That sounds reasonable.

But what does the server return?

Suppose every route receives the application's `index.html` with HTTP 200.

The browser renders the not-found message after JavaScript executes.

From the HTTP layer, however, the server has claimed that the requested page was successfully returned.

This can contribute to a **soft 404** situation: a page behaves like missing content but doesn't communicate that condition through the expected response semantics.

### Meaningful responses

For a resource that no longer exists, HTTP 404 is generally appropriate.

HTTP 410 may be appropriate when a resource is permanently gone.

For content moved to another URL, a suitable permanent redirect communicates the new destination.

Temporary redirects have different semantics.

Successful public pages should normally return successful responses and the actual content intended for that URL.

The precise behavior depends on the product and migration requirements, but the principle is simple.

**The server's response should tell the truth about the resource.**

### The SPA complication

A client-rendered single-page application may serve the same HTML shell for many routes.

That is convenient for client-side routing.

But if every arbitrary URL returns the shell with status 200, genuine missing pages become difficult to distinguish at the HTTP layer.

Server-side routing, pre-rendering, explicit missing-page handling, or a suitable crawler-visible strategy can address this.

Google documents strategies for handling soft 404 behavior in JavaScript applications when returning the ideal HTTP status directly is impractical.

The right choice depends on the application's hosting architecture.

## 5. Rendering: can the crawler see the actual hotel?

Mercury's new website uses Vue.

When a customer opens a hotel page, the browser receives a small HTML document.

JavaScript initializes the application.

The application requests the hotel's data.

The frontend generates the visible hotel description.

Will Google see it?

Potentially, yes.

Google's rendering infrastructure can execute JavaScript and process the rendered page.

The simplistic claim that JavaScript-rendered pages cannot be indexed is incorrect.

But the rendering process introduces additional dependencies.

The JavaScript must be available.

The application must execute successfully.

The required content must become visible in the rendered result.

The application shouldn't require a real user to click a control before loading content essential to indexing.

And search engines other than Google may have different rendering capabilities.

### CSR, SSR, and static generation

Client-side rendering, or CSR, generates much of the visible page after the browser executes JavaScript.

Server-side rendering, or SSR, returns rendered HTML generated for the request.

Static site generation produces HTML ahead of time.

These approaches were covered in SE240-L04.

For SEO, the important distinction is how readily the significant public content and links are available to crawlers.

SSR or pre-rendering can make important page content available earlier and reduce dependence on successful client-side execution.

But SSR is not an automatic ranking advantage.

And CSR doesn't automatically make a website invisible.

Choose the rendering strategy according to product requirements, performance, content freshness, and discoverability.

### The blocked-assets trap

Suppose Mercury's `robots.txt` permits hotel pages but blocks the JavaScript files required to render their content.

Googlebot can retrieve the HTML shell.

But its rendering system cannot load the application's essential scripts.

The hotel description never appears in the rendered result.

The crawler can access the URL while still being unable to understand the page as intended.

That's why robots configuration must account for essential rendering resources, not only document URLs.

## 6. Canonicalization: fifty URLs for one hotel

Now imagine a hotel page can be reached through several URLs.

One has a currency parameter.

Another includes a campaign-tracking parameter.

Another contains sorting information inherited from a search page.

Another uses an old URL format.

The main content may be identical or substantially similar across these variants.

Which URL should search engines treat as the representative page?

This is the problem of **canonicalization**.

Search engines identify duplicate or very similar content and select a representative URL.

Mercury can express its preferred URL through signals such as redirects, canonical link annotations, and sitemap inclusion.

### The canonical tag

A page may include a canonical link indicating the preferred representative URL.

For example, a hotel page reached through a tracking-parameter URL might point to the clean hotel-detail URL.

But a canonical annotation is not an absolute command.

Google can select a different canonical based on the signals and content it observes.

So the relevant question isn't merely:

"Did we add a canonical tag?"

It's:

"Are our canonical signals coherent, and which URL did the search engine actually select?"

### The disaster scenario

Suppose a template bug causes every hotel page to declare the catalogue home page as its canonical.

Now thousands of distinct hotels are sending a signal that the home page is their preferred representative.

Search engines may interpret those signals in the context of the content and other evidence, but this is clearly an incorrect configuration.

A single shared-template mistake can create site-wide indexing problems.

### Canonical isn't a redirect

A redirect moves a requesting client toward another URL.

A canonical annotation communicates a preferred representative URL while generally leaving the current URL accessible.

Those aren't interchangeable behaviors.

If an old hotel path is permanently replaced, a redirect may be appropriate.

If several URL variants legitimately remain accessible but have substantially identical main content, canonicalization may be useful.

### Filter and search pages

Mercury also has URLs such as hotel search results filtered by amenities, location, dates, and price.

These can generate enormous numbers of combinations.

Some filtered pages may have distinctive value.

Others may be near duplicates or ephemeral views that shouldn't become independently indexed pages.

A practical URL strategy needs to determine which combinations deserve stable, discoverable destinations and which should remain navigational application state.

Blindly canonicalizing every filtered page to one general landing page can throw away useful distinctions.

Blindly exposing every possible filter combination creates the opposite problem.

The decision belongs at the intersection of product structure and technical SEO.

## 7. Titles, descriptions, and visible content

Now the crawler can access the hotel page, and the indexing signals are coherent.

What tells the search engine what the page is about?

The visible content matters.

So do meaningful titles, headings, descriptive links, and other page information.

### The title element

The HTML title should describe the actual page.

A hotel page with a title such as "Home" or "Mercury" gives little useful context.

A descriptive title naming the hotel and location is more helpful.

However, Google may generate a different displayed title link using page headings, visible content, and other signals.

The title element influences the result, but it doesn't guarantee the exact text displayed.

### Meta descriptions

A meta description can summarize the page for search results.

But Google may generate snippets from the page content instead, depending on the query.

Meta descriptions are therefore useful presentation hints, not a guaranteed search-result script.

### Headings and semantic content

Good headings organize the page for users and provide useful structure.

An `h1` should generally express the page's main subject.

Other headings should reflect the actual content hierarchy.

The goal isn't to insert keywords into every heading.

It's to make the document understandable.

A technically perfect heading hierarchy won't compensate for content that doesn't answer the user's query.

### Images

Hotel pages rely heavily on photographs.

Images need appropriate descriptive alternatives where relevant, sensible filenames, accessible surrounding content, and suitable loading behavior.

But SEO isn't an excuse to stuff keywords into `alt` text.

Alternative text should primarily serve the image's meaning and accessibility context.

That also helps maintain useful machine-readable information.

## 8. Structured data: giving content an explicit vocabulary

Imagine Mercury's hotel page describes a property named Hotel Alexander.

The page contains an address, amenities, and information about the business.

A search engine may infer some of these facts from ordinary text.

Structured data offers a way to express certain facts more explicitly using a standardized vocabulary.

One common implementation is JSON-LD.

For example, a page might describe an entity as a hotel and provide its name, URL, and address.

The vocabulary often comes from Schema.org.

### What structured data can do

Structured data may help search engines understand entities and relationships.

For supported search features, valid structured data can make a page eligible for special result presentations.

But eligibility isn't a guarantee.

A search engine may choose not to display a rich result even when the markup is technically valid.

And not every Schema.org type corresponds to a supported Google rich-result feature.

### Accuracy matters

Suppose Mercury claims a hotel has a five-star rating in structured data while the visible page contains no trustworthy corresponding information.

That isn't a clever optimization.

It can be misleading.

Structured data should describe actual page content accurately and follow the search engine's relevant policies.

Developers should validate the structure and consistency of the markup.

SEO specialists and product teams should ensure the represented facts are appropriate.

The important engineering principle is that **metadata must remain a truthful representation of the page, not a separate fictional advertisement for it**.

## 9. Internationalization: the same hotel for different audiences

Mercury serves customers in several countries.

It has English, French, Dutch, and German hotel pages.

Some pages contain translated descriptions.

Others contain regional differences such as currency, cancellation information, or local support details.

Search engines need help understanding which URLs are alternatives intended for different language or regional audiences.

This is where `hreflang` becomes useful.

### Language and region annotations

An `hreflang` annotation identifies an alternate version of a page for a particular language and optional region.

For example, `en-GB` indicates English content intended for the United Kingdom.

`fr` indicates French without specifying a particular country.

The country code alone isn't a valid substitute for a language code.

### The return-link requirement

If the English page identifies a French alternate, the French page should reciprocally identify the English version.

The alternate pages should also include consistent references to the relevant language variants, including themselves where appropriate.

Missing reciprocal annotations can cause the search engine to ignore or misinterpret the intended alternate relationship.

### Canonical and hreflang solve different problems

Canonicalization expresses the preferred representative within a set of duplicate or very similar URLs.

`hreflang` expresses relationships between language or regional alternatives.

If Mercury has genuinely separate English and French pages, it usually shouldn't blindly canonicalize the French page to the English one.

That could undermine the purpose of maintaining a distinct French-language destination.

The canonical and alternate-language strategy should be designed together.

### International SEO isn't just translation

A regional site may also need to consider localized URLs, payment methods, legal information, date formats, currencies, and content availability.

Those are product and engineering concerns as much as search concerns.

Our goal here is to recognize how localized public pages should remain discoverable and internally consistent.

## 10. Mobile usability and performance

Now consider the customer's device.

Many searches happen on mobile devices.

A hotel page might look excellent on a desktop but perform poorly on a slower phone.

Perhaps the initial JavaScript bundle is enormous.

Perhaps the largest hotel photograph arrives late.

Perhaps a cookie banner shifts the layout.

Perhaps filtering freezes the main thread.

These problems affect the user's experience and may also intersect with search performance considerations.

### Core Web Vitals

Google's Core Web Vitals include:

Largest Contentful Paint, which concerns the loading of prominent content.

Interaction to Next Paint, which concerns responsiveness.

Cumulative Layout Shift, which concerns unexpected visual movement.

SE240-L05 covers these in detail.

For the present lecture, understand their role in a broader investigation.

Core Web Vitals are useful measurements of page experience.

They're not magic scores that guarantee high search rankings.

A page with excellent metrics but irrelevant content can still perform poorly in search.

A page with useful content but severe technical failures may also struggle.

Technical SEO and user experience overlap, but they aren't the same discipline.

## 11. The production diagnostic workflow

Let's return to Mercury's traffic collapse.

We need a practical investigation.

### First: separate technical decline from search-demand change

Open Google Search Console.

Compare organic impressions and clicks before and after the release.

Segment by page, query, country, and device where appropriate.

If clicks fall while impressions remain relatively stable, investigate changes in click-through rate, result presentation, query mix, or competition.

If impressions collapse across thousands of pages, investigate whether discovery, indexing, canonicalization, or other search-visibility changes explain it.

These interpretations are hypotheses, not proof.

### Second: inspect representative URLs

Choose one previously successful hotel page and one newly affected page.

Use Search Console's URL Inspection tool.

Examine whether Google has indexed the URL.

Check the reported crawling and indexing information.

Compare the user-declared canonical with Google's selected canonical when available.

Investigate whether the page is accessible and what the rendered result contains.

### Third: inspect actual HTTP behavior

Request the URL directly.

Check its status code.

Follow any redirects.

Inspect response headers, including applicable robots directives.

Review the original HTML.

Then compare the initial document with the DOM after JavaScript rendering.

If the page requires JavaScript to display its important content, verify that the necessary resources are accessible and that rendering succeeds.

### Fourth: inspect discovery and indexing controls

Review the site's `robots.txt`.

Check the XML sitemaps.

Verify that the intended hotel URLs appear in the correct sitemap.

Inspect canonical annotations.

Check for accidental `noindex` directives.

Investigate links from city and catalogue pages.

### Fifth: investigate the release differences

Compare the old and new application behavior.

Did the routing system change?

Were URL structures modified?

Did a shared template begin emitting the wrong canonical URL?

Did the staging environment's `noindex` configuration leak into production?

Did the API introduce authentication requirements for otherwise public hotel content?

Did frontend assets become inaccessible to crawlers?

This is where ordinary software debugging and SEO meet.

### Sixth: fix the verified problem and monitor

Suppose we discover a mistaken site-wide `noindex` directive.

The immediate action is to remove the erroneous directive safely.

Then verify the corrected HTTP and HTML behavior.

Inspect representative pages again.

Monitor Search Console over time.

Don't expect search engines to update every result instantaneously.

Crawling and indexing are asynchronous processes influenced by multiple factors.

The fix should be validated technically, and the resulting search behavior should be observed rather than assumed.

## 12. What a senior developer should know

A senior frontend or full-stack engineer doesn't need to become a professional SEO strategist.

They should, however, understand enough to avoid common structural mistakes.

Public content should be discoverable through sensible URLs and links.

The server should return meaningful statuses.

Pages should express coherent indexing and canonical preferences.

The important content should be accessible to crawlers.

International variants should be properly related.

Structured data should accurately describe the page.

Performance should support a good user experience.

And the team should have a way to detect search-visibility regressions after major releases.

If an interviewer asks why a modern JavaScript website lost organic traffic, don't immediately answer:

"Because Google can't read JavaScript."

That's too simplistic and often wrong.

A better answer is to investigate the complete search pipeline and isolate the stage where the website stopped behaving as intended.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — A working page that search cannot find

A hotel page loads perfectly in Chrome when you enter the URL, but it receives no Google Search impressions. What different classes of causes would you investigate?

### Question 2 — Robots versus noindex

A developer blocks a page in `robots.txt` and also adds a `noindex` meta tag. Why might this fail to achieve the intended outcome?

### Question 3 — The sitemap misunderstanding

Mercury submits fifty thousand URLs through an XML sitemap. Does that guarantee Google will index all fifty thousand?

### Question 4 — The canonical bug

Every hotel detail page accidentally points its canonical link to the catalogue home page. Why is this problematic?

### Question 5 — Client-side rendering

Does using a Vue SPA automatically prevent Google from indexing its content? What should be investigated instead?

### Question 6 — The soft 404

A missing hotel page displays "Hotel not found" after JavaScript executes, but the server returns HTTP 200. What is wrong with that behavior?

### Question 7 — Structured data

A hotel page contains valid Schema.org markup. Does that guarantee a rich search result?

### Question 8 — Internationalization

The English hotel page links to a French alternative through `hreflang`, but the French page has no corresponding return link. What might happen?

### Question 9 — Traffic investigation

Organic clicks fall thirty percent immediately after a release. What evidence would you gather before concluding that the release caused the decline?

---

# Solutions and Discussion

## Solution 1 — Distinguish discovery, indexing, and serving

Investigate whether the URL is discoverable, whether crawlers can access it, whether its content is rendered and understood, whether indexing directives or canonicalization affect it, and whether the content is relevant to actual searches.

Search Console and representative URL inspections help narrow the problem.

## Solution 2 — The crawler may never see noindex

If `robots.txt` blocks crawling, Google may not retrieve the page and therefore may not encounter its `noindex` directive.

A disallowed URL can still become known through links.

Use the control appropriate to the actual requirement.

## Solution 3 — Sitemaps are discovery signals

A sitemap helps search engines learn about URLs and understand which pages the site considers important.

It does not guarantee crawling, indexing, ranking, or traffic.

## Solution 4 — Conflicting representation signals

The pages declare a common representative URL even though they contain distinct hotel content.

This may interfere with canonical selection and indexing.

Each meaningful hotel page should have a coherent canonical strategy reflecting its actual content and URL relationships.

## Solution 5 — Google can render JavaScript

Google can process JavaScript-powered pages.

But successful indexing depends on discoverability, resource accessibility, rendering, indexing controls, and content quality.

SSR or pre-rendering can reduce dependencies and improve reliability for publicly discoverable content.

## Solution 6 — The HTTP response misrepresents the resource

The application presents missing content while returning a successful HTTP response.

This can create a soft 404 problem.

Where possible, use an appropriate HTTP status or a suitable documented strategy for client-rendered missing pages.

## Solution 7 — Eligibility isn't a guarantee

Valid structured data may make a page eligible for supported rich-result features.

It doesn't guarantee that the search engine will display them.

Markup must also satisfy relevant policies and represent actual page content.

## Solution 8 — Alternate-language signals may not be accepted

Search engines may ignore or misinterpret incomplete `hreflang` relationships.

Relevant language alternatives should provide appropriate reciprocal annotations.

## Solution 9 — Establish correlation and isolate the failure

Compare pre- and post-release impressions, clicks, queries, affected pages, countries, and devices.

Inspect indexing and canonical information.

Check HTTP behavior and release changes.

The timing may suggest a deployment regression, but it doesn't prove one without further evidence.

---

# The Mental Model Worth Keeping

Search discoverability is a pipeline, not a single metadata setting.

**Discovery:** Can the search engine find the URL?

**Crawling:** Can it retrieve the required resources?

**Rendering:** Can it observe the meaningful page content?

**Indexing:** Do the content and indexing signals allow the page to be included?

**Serving:** Is the page relevant and useful for the searches people perform?

When traffic falls, identify the failing stage before choosing a fix.

Remember that sitemaps assist discovery, `robots.txt` controls cooperative crawling, `noindex` controls indexing when observed, and canonical annotations communicate preferred representatives.

**Technical SEO is the engineering discipline of making a public website understandable to search engines without compromising the experience of the people who use it.**

# Next Lecture — SE215-L09: Data Engineering for Application Developers

Our hotel catalogue is discoverable again.

Customers are booking rooms.

But management notices a new problem.

PostgreSQL contains the correct reservations.

The payment system records the correct charges.

Yet the analytics dashboard reports more bookings than the application actually created.

The data team says the event pipeline processed every message successfully.

The backend team says the database is correct.

How can both teams be right while the business report is wrong?

Next we'll follow operational data through ingestion, transformation, storage, and analytical reporting, and discover why building reliable data pipelines requires more than delivering messages from one system to another.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Audit a Public Hotel Catalogue

The following examples use fictional Mercury URLs. They're illustrative configurations, not a running application.

The objective is to investigate a public website methodically rather than memorize isolated SEO tricks.

## Lab A — Inspect the response before opening DevTools

Suppose a public hotel page should exist at:

`https://mercury.example/hotels/berlin/alexander`

Begin by inspecting its HTTP response.

```bash
curl -I https://mercury.example/hotels/berlin/alexander
```

Check the status code, redirects, content type, and relevant response headers.

Then retrieve the HTML and inspect it.

```bash
curl -L https://mercury.example/hotels/berlin/alexander
```

Ask:

Does the initial HTML contain meaningful hotel content?

Does it include the correct title?

Is there a canonical link?

Is there a robots directive?

Would a client that doesn't execute JavaScript understand what the page describes?

Then compare the initial HTML against the rendered document in Chrome DevTools.

If the rendered page contains important information absent from the response, investigate whether the rendering dependencies are accessible to relevant crawlers.

## Lab B — Inspect robots and indexing controls

A simple `robots.txt` might look like:

```text
User-agent: *
Disallow: /internal/
Disallow: /account/

Sitemap: https://mercury.example/sitemap.xml
```

This is illustrative and must be adapted to the actual site's public and private routes.

Remember that `robots.txt` is not a security mechanism.

Now consider an ordinary public page that should not appear in Google Search.

Its HTML might include:

```html
<meta name="robots" content="noindex">
```

Investigate whether Googlebot can actually retrieve the page and observe the directive.

**Challenge:** A page appears in search results even though it's disallowed by `robots.txt`. Explain why that doesn't necessarily contradict the crawling rule.

## Lab C — Build a minimal sitemap

Suppose Mercury has three stable, canonical hotel-detail URLs.

A simplified sitemap could look like this:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://mercury.example/hotels/berlin/alexander</loc>
  </url>
  <url>
    <loc>https://mercury.example/hotels/paris/central</loc>
  </url>
  <url>
    <loc>https://mercury.example/hotels/amsterdam/canal</loc>
  </url>
</urlset>
```

For a real catalogue, generate the sitemap from the appropriate authoritative records.

Don't include removed or non-indexable URLs indiscriminately.

If using `<lastmod>`, ensure it reflects meaningful changes rather than simply the time the sitemap was generated.

For large catalogues, consider splitting sitemaps and providing a sitemap index.

**Challenge:** Why is including every possible date-filtered search URL a poor default sitemap strategy?

## Lab D — Canonicalization

Imagine the same hotel can be reached at these URLs:

```text
https://mercury.example/hotels/berlin/alexander
https://mercury.example/hotels/berlin/alexander?currency=EUR
https://mercury.example/hotels/berlin/alexander?utm_source=newsletter
```

Assume their primary public content is substantially the same.

A canonical annotation on the parameterized versions might point to the clean URL:

```html
<link
  rel="canonical"
  href="https://mercury.example/hotels/berlin/alexander"
>
```

Now answer:

Does this annotation redirect the browser?

Does it guarantee which URL Google selects?

Would the same canonical strategy be appropriate for a genuinely different French-language hotel page?

How would you verify the search engine's selected canonical?

## Lab E — Structured data

A hotel page may include structured data describing its real contents.

For example:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Hotel",
  "name": "Hotel Alexander",
  "url": "https://mercury.example/hotels/berlin/alexander",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Berlin",
    "addressCountry": "DE"
  }
}
</script>
```

This illustrates JSON-LD syntax and Schema.org vocabulary.

It does not establish eligibility for a particular Google rich-result feature.

Verify that the markup describes actual visible information accurately.

Use appropriate validators, including Google's Rich Results Test for supported search features.

**Challenge:** Why is adding fabricated review ratings to structured data a dangerous approach to improving search appearance?

## Lab F — International hotel pages

Mercury publishes English and French versions of the same hotel description.

The English page declares its own language version and the French alternative.

The French page declares its own language version and the English alternative.

Consider whether the following relationship is correctly represented:

```html
<link
  rel="alternate"
  hreflang="en"
  href="https://mercury.example/en/hotels/berlin/alexander"
>

<link
  rel="alternate"
  hreflang="fr"
  href="https://mercury.example/fr/hotels/berlin/alexander"
>
```

These links would need to be included appropriately on the relevant alternate pages, with consistent canonicalization.

Now investigate a deliberately incorrect implementation in which the French page canonicalizes to the English URL despite containing a genuine translated version.

Explain why the canonical and localization strategies need to be designed together.

## Lab G — Diagnose the traffic collapse

Mercury's observed search performance is:

| Metric | Before redesign | After redesign |
|---|---:|---:|
| Weekly organic impressions | 500,000 | 110,000 |
| Weekly organic clicks | 24,000 | 5,200 |
| Hotel URLs reported indexed | 44,000 | 9,000 |
| Frontend browser tests | Passing | Passing |
| API error rate | Low | Low |

These are fictional numbers for the exercise.

The team discovers three changes:

1. The new frontend uses CSR for hotel-detail pages.
2. The sitemap contains many obsolete URLs.
3. A shared template adds a canonical link pointing every hotel page to the catalogue home page.

Prepare a diagnosis.

Which finding deserves immediate attention?

What would you verify before modifying code?

How would you distinguish correlation from causation?

What technical checks should run before the next catalogue release?

How would you monitor recovery afterward?

The goal is to explain a defensible investigation, not to promise that a particular fix will immediately restore search traffic.

---

# Further Reading

Primary technical references:

- **Google Search Central — How Google Search Works:** https://developers.google.com/search/docs/fundamentals/how-search-works
- **Google Search Central — JavaScript SEO Basics:** https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- **Google Search Central — SEO Guide for Developers:** https://developers.google.com/search/docs/fundamentals/get-started-developers
- **Google Search Central — Introduction to robots.txt:** https://developers.google.com/search/docs/crawling-indexing/robots/intro
- **Google Search Central — Block Search Indexing with noindex:** https://developers.google.com/search/docs/crawling-indexing/block-indexing
- **Google Search Central — Canonicalization:** https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- **Google Search Central — Build and Submit a Sitemap:** https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- **Google Search Central — Structured Data Guidelines:** https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- **Google Search Central — Localized Versions:** https://developers.google.com/search/docs/specialty/international/localized-versions
- **Google Search Console:** https://search.google.com/search-console/about
- **Schema.org:** https://schema.org/

Related programme chapters:

- SE215-L07 — Owning End-to-End Testing
- SE215-L09 — Data Engineering for Application Developers
- SE240-L01 — Inside the Browser
- SE240-L04 — Delivering Modern Web Applications
- SE240-L05 — Performance: Why Fast Code Can Feel Slow
- SE240-L07 — Anatomy of a Production Web Page

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for TTS skipping and rapid screen revision.*

```text
SE215-L08 — TECHNICAL SEO AND WEB DISCOVERABILITY

CORE PIPELINE
  Discovery -> Crawling -> Rendering -> Indexing -> Serving
  A working webpage isn't automatically a searchable webpage.

DISCOVERY
  Use real crawlable <a href="..."> navigation
  Important public pages need stable URLs
  Sitemaps help discovery but don't guarantee indexing
  Large catalogues may need sitemap indexes
  Use accurate lastmod when available

CRAWL CONTROL
  robots.txt manages cooperative crawler access
  robots.txt is NOT security
  Disallowed URLs can still be known/indexed by URL
  Blocking essential JS/CSS can prevent successful rendering

INDEX CONTROL
  <meta name="robots" content="noindex">
  or appropriate X-Robots-Tag header
  Crawler must access page to observe noindex
  robots.txt disallow + noindex can conflict
  Authentication protects private data; noindex doesn't

HTTP STATUS
  200 = successful resource
  301/308 = permanent redirect as appropriate
  404 = resource not found
  410 = gone
  SPA fallback 200 for nonexistent page -> soft 404 risk
  Server responses should reflect resource reality

RENDERING
  Google can execute JavaScript
  CSR != automatically invisible
  SSR/SSG can expose content and links earlier
  Essential JS/CSS/API resources must be accessible
  Rendered content matters
  Other crawlers may have different capabilities

CANONICALIZATION
  Duplicate/very similar URLs -> preferred representative
  rel=canonical is a strong signal, not an absolute command
  Redirects also signal consolidation
  Sitemap inclusion is weaker signal
  Canonical != redirect
  Incorrect site-wide canonical can affect thousands of URLs
  Inspect Google-selected canonical in Search Console

FACETED NAVIGATION
  Filters can produce enormous URL combinations
  Decide which pages deserve indexed destinations
  Avoid indexing arbitrary ephemeral states
  Don't blindly canonicalize genuinely distinct useful pages
  Coordinate URL design with product/SEO requirements

CONTENT METADATA
  <title> should describe the actual page
  Google may generate different displayed title
  meta description may influence snippet, not guarantee it
  Semantic headings clarify document structure
  Internal link text provides useful context
  Accurate alt text serves accessibility and content meaning

STRUCTURED DATA
  Schema.org vocabulary, commonly JSON-LD
  Describe actual page facts faithfully
  Google rich-result eligibility != guaranteed display
  Only supported features have relevant rich-result treatment
  Validate markup; don't invent reviews or ratings

INTERNATIONAL SEO
  hreflang identifies language/region alternatives
  Language required; region optional
  Alternate pages need reciprocal annotations
  Include appropriate self-references
  Canonical and hreflang need coherent design
  Distinct translated pages shouldn't be indiscriminately
  canonicalized to one language

MOBILE AND PERFORMANCE
  Responsive/mobile usability matters
  LCP: loading of prominent content
  INP: responsiveness
  CLS: visual stability
  Core Web Vitals matter for experience, not magic ranking
  Avoid JS failures, oversized images, blocking resources

SEARCH CONSOLE
  Compare impressions, clicks, queries, pages, countries, devices
  Inspect representative URLs
  Check crawl/indexing reports
  Compare declared vs Google-selected canonical
  Inspect rendered HTML/resources
  Monitor before/after changes over time

PRODUCTION DIAGNOSTIC
  1. Identify affected URL groups and timeline
  2. Compare search impressions and clicks
  3. Inspect representative URLs in Search Console
  4. Verify HTTP codes and redirects
  5. Inspect robots/noindex controls
  6. Check sitemap and internal links
  7. Inspect canonical and hreflang
  8. Compare initial HTML with rendered content
  9. Find actual release regression
 10. Fix and observe subsequent crawling/indexing

COMMON FAILURES
  Staging noindex copied into production
  robots.txt blocks required resources
  Client-side routes return 200 on missing content
  Wrong canonical injected by shared template
  Sitemap uses outdated/noncanonical destinations
  Language alternates lack return links
  Content exists only after unsupported interaction
  Public catalogue API accidentally requires authentication
  Search traffic blamed on code without evidence

SENIOR INTERVIEW ANSWER
  "I'd distinguish crawling, indexing and serving.
   I'd compare Search Console performance before/after,
   inspect a representative URL, validate status and
   robots controls, compare HTML and rendered content,
   check canonical and sitemap signals, then isolate
   the actual deployment regression before changing code."

MENTAL MODEL
  Discoverable URL.
  Accessible response.
  Renderable content.
  Coherent indexing signals.
  Relevant answer to the user's search.
```
