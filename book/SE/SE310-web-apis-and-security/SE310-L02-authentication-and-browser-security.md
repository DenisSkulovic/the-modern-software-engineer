---
id: SE310-L02
course: SE310
title: "Authentication and Browser Security"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [WEB201-S08]
prev: SE310-L01
next: SE310-L03
---




# SE310 — Web APIs, Identity, and Security

## Lecture 02: Authentication and Browser Security

*Why a valid login, an encrypted connection, and a perfectly functioning API still aren't enough to keep your application secure.*

---

# 1. The Customer Who Opened Someone Else's Reservation

Your hotel-booking platform has just completed an external security audit. The authentication system looks respectable.

Passwords are securely hashed. HTTPS is enforced. Sessions have expiration policies. The frontend handles login and logout properly.

The API requires authentication before exposing reservations. Then the security researcher demonstrates something uncomfortable. She logs into an ordinary customer account and opens her reservation:

```http
GET /api/reservations/9821
Cookie: session=...
```

The server responds successfully. Then she changes one number:

```http
GET /api/reservations/9822
Cookie: session=...
```

Another successful response. Except reservation 9822 belongs to somebody else. The researcher can now read another customer's name, hotel details, travel dates, and contact information.

The authentication system hasn't failed. The session is valid. The HTTPS connection is secure.

The API has correctly identified the user. And that's precisely the problem.

**The server knows who is making the request, but it hasn't checked whether that person is allowed to access the requested resource.**

This is a form of broken object-level authorization, historically often called IDOR—Insecure Direct Object Reference. It's particularly dangerous because the requests look completely ordinary.

There's no exotic exploit. No mysterious memory corruption. No need to defeat encryption.

The researcher simply requested a different resource, and the backend trusted her too much. This incident provides our starting point for understanding web security.

Securing a web application isn't one problem.

It's several distinct problems involving identity, permissions, credentials, browser isolation, untrusted content, and the boundaries between cooperating systems. Let's examine them one by one.

---

# 2. Authentication and Authorization: Two Questions That Must Never Be Confused

Imagine entering an office building. At reception, a security guard examines your passport. The guard establishes that you really are the person you claim to be.

That's **authentication**. Now imagine walking toward the company's financial records room. Should the security guard's verification of your identity automatically grant access?

Obviously not. The company must determine whether your identity has the necessary permissions. That's **authorization**.

In software, the distinction is the same. Authentication asks:

> Who is making this request, and what evidence supports that identity?

Authorization asks:

> Is this principal permitted to perform this specific action on this specific resource?

The word *principal* is useful here. It means the identity on whose behalf an operation is performed. That might be a user, an organization, a service account, or another authenticated actor.

## 2.1 Where the reservation API went wrong

Consider this simplified Express controller:

```typescript
app.get("/api/reservations/:id", requireAuth, async (req, res) => {
  const reservation = await reservationRepository.findOne({
    where: { id: req.params.id }
  });

  if (!reservation) {
    return res.sendStatus(404);
  }

  return res.json(reservation);
});
```

It uses `requireAuth`. Surely that's good? Yes, but incomplete.

The middleware might prove that the caller is customer 901. Nothing in the database query establishes that reservation 9822 belongs to customer 901. A stronger version constrains the lookup:

```typescript
app.get("/api/reservations/:id", requireAuth, async (req, res) => {
  const reservation = await reservationRepository.findOne({
    where: {
      id: req.params.id,
      customerId: req.user.id
    }
  });

  if (!reservation) {
    return res.sendStatus(404);
  }

  return res.json(reservation);
});
```

Now the server only returns a reservation belonging to the authenticated customer.

The authenticated user ID must come from trusted, server-validated authentication context—not from an arbitrary client-supplied parameter.

For a simple customer-owned reservation model, this approach works well. But real SaaS applications are often more complicated.

## 2.2 Multi-tenant authorization

Suppose your application supports hotel organizations. Each organization has employees, managers, and administrators. A reservation might belong to:

```text
Organization: Hotel Group A
Reservation: 9822
```

A manager from Hotel Group B must not access it. But merely checking the user's organization membership may also be insufficient.

Perhaps a hotel receptionist can view reservations but cannot issue refunds. Perhaps an accountant can view payments but cannot modify guest details. Authorization now depends on several dimensions:

```text
WHO is acting?
        +
WHICH organization?
        +
WHICH resource?
        +
WHAT operation?
        +
UNDER WHAT conditions?
```

Conceptually:

```typescript
authorize({
  principal: currentUser,
  action: "reservation:refund",
  resource: reservation,
  context: { organizationId }
});
```

This is closer to the actual authorization problem than simply checking:

```typescript
user.isAuthenticated
```

or even:

```typescript
user.role === "admin"
```

An administrator of one hotel isn't necessarily an administrator of every hotel.

A robust SaaS needs tenant boundaries enforced consistently across reads, writes, background jobs, exports, and administrative operations.

## 2.3 RBAC and ABAC

Two common authorization models are worth knowing.

**Role-Based Access Control (RBAC)** assigns permissions through roles.

For example:

```text
Receptionist → View bookings
Manager      → View and modify bookings
Finance      → View payments and process refunds
```

This is straightforward and useful when permissions align with organizational responsibilities.

**Attribute-Based Access Control (ABAC)** evaluates properties of the actor, resource, action, and context.

For example:

> A manager may modify a reservation only when it belongs to their organization and its status permits modification.

The distinction isn't necessarily either/or. Real systems often combine role membership with resource ownership and contextual business rules.

The important lesson is that a role is rarely sufficient by itself to establish permission for every resource. And one final security principle:

**Hiding a button is not authorization.**

A Vue component may hide the Refund button from a receptionist. That's useful for user experience. But the backend must independently reject an unauthorized refund request.

The browser is controlled by the user, not by your application security team.

---

# 3. Sessions: How Does the Server Remember Who You Are?

HTTP requests are independent exchanges. Yet a customer can log in once and navigate through dozens of pages. How does the backend recognize the same user repeatedly?

One conventional solution is a server-side session. Imagine the login process:

```text
Browser                          Backend
   │                                │
   │──── Username + password ──────►│
   │                                │
   │                         Verify credentials
   │                         Create session
   │                                │
   │◄── Session cookie ─────────────│
   │                                │
   │──── Future HTTP request ──────►│
   │     with session cookie        │
   │                                │
   │                         Look up session
   │                         Identify user
```

The server generates a cryptographically unpredictable session identifier. For example, a fictional identifier:

```text
7ea4d9c1...
```

It associates that identifier with session state:

```text
Session ID → User 901
             Created at ...
             Expires at ...
             Authentication context ...
```

The session information might be stored in Redis, a database, or another suitable server-side store. The browser doesn't need to know the user's internal session data. It only needs the identifier.

## 3.1 Cookies carry the identifier

The server can respond with:

```http
Set-Cookie: __Host-session=7ea4d9c1...; Path=/; Secure; HttpOnly; SameSite=Lax
```

Let's inspect the attributes.

**Secure** instructs the browser to send the cookie only over secure connections, subject to browser-specific localhost exceptions.

**HttpOnly** prevents ordinary page JavaScript from reading the cookie through APIs such as `document.cookie`.

**SameSite=Lax** limits when the cookie accompanies cross-site requests.

**Path=/** makes the cookie applicable across the host's URL paths.

The `__Host-` prefix imposes additional constraints in supporting browsers: the cookie must be Secure, must have `Path=/`, and must not specify a `Domain` attribute.

This limits certain cookie-scope and overwrite risks.

### Why use an opaque identifier?

Because the server retains control over the session. It can invalidate the session during logout. It can expire inactive sessions.

It can revoke a session after suspicious activity. It can update permissions without necessarily requiring the browser to obtain a new identity token. But server-side sessions have operational costs.

A distributed application needs shared or otherwise coordinated session storage. Multiple backend instances must be able to resolve the customer's session consistently.

Session lookup adds infrastructure dependencies. That's one reason another approach became popular: self-contained tokens.

---

# 4. JWTs: The Token That Carries Its Own Claims

A JSON Web Token, or JWT, is a compact format for representing claims. A common signed JWT contains three Base64URL-encoded sections:

```text
header.payload.signature
```

For example, its decoded payload might resemble:

```json
{
  "sub": "901",
  "iss": "https://auth.example.com",
  "aud": "hotel-api",
  "exp": 1795000000,
  "scope": "reservations:read"
}
```

These claims might indicate:

- `sub`: The subject identified by the token.
- `iss`: The issuer.
- `aud`: The intended audience.
- `exp`: The expiration time.
- `scope`: The permissions granted under the relevant authorization model.

The signature allows a verifier with the appropriate key material to check that the signed content hasn't been modified. Here's the crucial distinction:

**A signed JWT is not necessarily encrypted.**

Anyone possessing an ordinary signed JWT can decode its header and payload. The signature protects integrity and supports verification of authenticity. It doesn't make the contents confidential.

Therefore, don't put secrets or sensitive personal information into JWT payloads merely because they're encoded.

## 4.1 Why JWTs became popular

A backend can validate a properly signed JWT without necessarily performing a central session lookup on every request. That's attractive for distributed systems. Imagine:

```text
                  API Gateway
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
           Service A Service B Service C
```

Each service can potentially validate the token using trusted signing-key information. But there are trade-offs.

## 4.2 Revocation becomes more complicated

Suppose a JWT expires in one hour. A customer logs out after ten minutes. What happens to a copied token?

Unless the architecture implements additional controls, the token may remain acceptable until expiration. Server-side sessions are comparatively easy to revoke centrally.

Stateless tokens are convenient partly because they avoid centralized state—but immediate revocation may require reintroducing state or using other mechanisms.

Possible approaches include short-lived access tokens, token revocation lists, session-version checks, and appropriate refresh-token management. There isn't one universally superior solution.

## 4.3 Validation must be complete

A backend must not merely decode a token and trust the claims. It must verify the cryptographic signature using an explicitly permitted algorithm and trusted key, and validate relevant claims.

These commonly include the expected issuer, audience, expiration, and any application-required restrictions. An access token intended for Service A must not automatically become valid for Service B.

Otherwise, a token accepted in one context may be misused in another. The deeper principle:

> A token is evidence issued for a particular purpose, not a universal passport to every service that recognizes its format.

---

# 5. Cookies Versus Bearer Tokens: The Argument That Never Ends

A common interview question is:

"Would you use cookie-based sessions or JWT authentication?" The question is misleading. A JWT can itself be stored in a cookie.

And a session identifier can be supplied through a header. These concepts describe different dimensions:

- **Session versus self-contained token:** How identity state is represented and validated.
- **Cookie versus Authorization header:** How the browser sends credentials.
- **Browser storage choice:** Where credentials are retained.

Let's compare two common patterns.

## 5.1 Cookie-based authentication

The server sets a protected session cookie. The browser attaches it to matching requests according to cookie rules.

Advantages include relatively straightforward browser integration and the ability to use `HttpOnly` to prevent direct JavaScript access to the credential.

But automatic cookie attachment creates an important risk: cross-site requests may cause authenticated actions unless the application implements suitable CSRF defenses. We'll investigate that shortly.

## 5.2 Bearer token in an Authorization header

The frontend explicitly sends:

```http
Authorization: Bearer eyJ...
```

A bearer token is effectively a credential usable by whoever possesses it, unless additional sender-constraining mechanisms are employed. The application must choose how to retain it.

One tempting approach:

```typescript
localStorage.setItem("accessToken", token);
```

This survives page reloads and is easy to use. But JavaScript running in the same origin can read it.

If an attacker successfully executes JavaScript in your application's security context, they may be able to steal the token.

Using memory-only storage can reduce persistence and some extraction risks, but creates challenges around reloads and session continuity.

A protected cookie reduces direct JavaScript access to its contents, but doesn't eliminate the consequences of an XSS vulnerability. Which brings us to an architectural pattern.

## 5.3 The Backend-for-Frontend approach

For a substantial browser application, a **Backend for Frontend**, or BFF, can provide an attractive security boundary.

Instead of giving the browser long-lived OAuth credentials, the application backend handles token exchange and storage. The browser uses a protected session cookie to communicate with the BFF.

```text
Vue Browser Application
          │
          │ Session cookie
          ▼
         BFF
          │
          │ Server-managed access token
          ▼
     Backend APIs
```

This reduces the exposure of API tokens to browser JavaScript. It can also centralize authentication and simplify certain client concerns.

But a BFF adds operational complexity and another application boundary. And browser cookie sessions still require correct CSRF protection, session management, and authorization.

A BFF is a useful security architecture, not an invulnerability machine.

---

# 6. The Same-Origin Policy: Why Websites Cannot Read Everything

Now imagine you're logged into your bank. In another browser tab, you open a malicious website. The malicious website executes JavaScript.

Why can't it simply fetch your bank balance, read the response, and send the information to an attacker? One major reason is the browser's **same-origin policy**. An origin is defined by:

```text
scheme + hostname + port
```

Consider:

| URL | Same origin as `https://app.example.com`? |
|---|---|
| `https://app.example.com/settings` | Yes |
| `https://api.example.com` | No |
| `http://app.example.com` | No |
| `https://app.example.com:8443` | No |

The same-origin policy limits how documents and scripts from one origin can access resources belonging to another origin. It is one of the browser's most important isolation mechanisms.

Without it, simply visiting an untrusted website could expose information from other websites where you're authenticated. But there's an important subtlety.

**The same-origin policy doesn't categorically prevent browsers from sending cross-origin requests.**

Browsers have always been able to load images, submit forms, navigate to other websites, and perform many other cross-origin operations.

The policy primarily restricts certain kinds of cross-origin access, especially reading responses through JavaScript without permission.

That distinction is essential for understanding both CORS and CSRF.

---

# 7. CORS: Permission to Read Across Origins

Suppose your Vue frontend runs at:

```text
https://app.example.com
```

And your API runs at:

```text
https://api.example.com
```

They're different origins. Your frontend executes:

```typescript
const response = await fetch(
  "https://api.example.com/hotels"
);
```

The browser applies cross-origin access rules. If the API wants to allow the frontend origin to read the response, it can return:

```http
Access-Control-Allow-Origin: https://app.example.com
```

This is **Cross-Origin Resource Sharing**, or CORS. CORS is a controlled mechanism for relaxing the browser's default cross-origin reading restrictions.

## 7.1 The preflight request

Some cross-origin requests trigger an additional check before the actual request. For example, a request using a non-safelisted custom header may require a CORS preflight.

The browser sends an `OPTIONS` request resembling:

```http
OPTIONS /api/reservations
Origin: https://app.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type,authorization
```

The server might respond:

```http
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: POST
Access-Control-Allow-Headers: content-type,authorization
```

The browser evaluates the response and determines whether the actual cross-origin request is permitted under CORS. Preflight results can also be cached according to relevant rules.

Not every cross-origin request requires preflight. And a preflight is not the same thing as authenticating the user.

## 7.2 Credentialed requests

If your cross-origin API uses cookies, the frontend may need:

```typescript
fetch("https://api.example.com/me", {
  credentials: "include"
});
```

The API must permit credentialed CORS access appropriately. For example:

```http
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Credentials: true
Vary: Origin
```

Cookie attributes and browser policies must independently permit the cookie to be sent. You cannot use:

```http
Access-Control-Allow-Origin: *
```

to grant readable credentialed CORS responses. Browsers reject that combination.

## 7.3 The biggest CORS misconception

Suppose someone asks:

"How do we secure our API so only our frontend can call it?" And another developer answers:

"Configure CORS to allow only our frontend domain." That's not a complete security solution. CORS is enforced by browsers.

A command-line HTTP client, backend service, or attacker-controlled program can make direct requests without obeying browser CORS restrictions. For example:

```bash
curl https://api.example.com/reservations/9821
```

CORS doesn't prevent the request from being sent. The backend must enforce authentication and authorization regardless of the request's Origin header. This is worth memorizing:

**CORS controls whether browser JavaScript may access certain cross-origin responses. It is not an API authentication mechanism.**

---

# 8. CSRF: When the Browser Becomes an Unwitting Accomplice

Now consider the opposite problem. The browser may refuse to let a malicious website *read* a bank's response. But what if the attacker doesn't need to read anything?

What if they only need the browser to perform an action? Imagine a user is logged into your hotel-booking platform using a session cookie. The attacker persuades the user to visit a malicious website.

That site attempts to submit a request to the booking application. Under certain cookie and request conditions, the browser may attach the user's authentication cookie automatically.

If the backend accepts the resulting state-changing request without verifying its legitimate origin or intent, the operation may be performed under the user's identity.

This is **Cross-Site Request Forgery**, or CSRF. The browser isn't necessarily compromised. The user's credentials haven't necessarily been stolen.

The attacker abuses the fact that the browser may automatically include credentials when making requests to another site.

## 8.1 Why CORS doesn't automatically stop CSRF

This distinction is subtle but critical. CORS may prevent the attacking website's JavaScript from reading a cross-origin response.

But some requests, such as ordinary form submissions, can be sent cross-origin without requiring successful CORS permission.

If a state-changing endpoint accepts such a request and the necessary cookies accompany it, the damage may occur even though the attacker cannot read the response. That's why:

> "We configured CORS correctly" is not an adequate answer to "How do we prevent CSRF?"

The protections address related but different threats.

## 8.2 CSRF defenses

One classic defense is a CSRF token. The legitimate application obtains an unpredictable value associated with the user's session or another suitable protection scheme.

When submitting a sensitive request, the frontend includes that value. The server verifies it. An attacker controlling an unrelated website should not be able to obtain and supply a valid token.

Other important defenses include:

- Appropriate `SameSite` cookie policies.
- Server-side verification of `Origin` or, where appropriate, `Referer`.
- Requiring suitable request content types and custom headers for sensitive APIs.
- Avoiding state-changing operations through safe HTTP methods.
- Fetch Metadata-based protections where appropriate.

These defenses can be combined. No single mechanism is universally appropriate for every architecture.

## 8.3 SameSite isn't the same as same-origin

A particularly common source of confusion:

```text
https://app.example.com
https://api.example.com
```

These are different origins. But they're generally considered part of the same *site* under the schemeful site model because they share the same scheme and registrable domain.

The cookie `SameSite` attribute concerns site relationships, not strict origin equality.

This matters because `SameSite` restrictions alone don't necessarily protect against malicious or compromised sibling subdomains.

A robust CSRF design must account for the application's actual trust boundaries.

For many conventional browser applications, `SameSite=Lax` offers useful baseline protection against certain cross-site actions.

But it isn't a reason to discard all other CSRF defenses, particularly for sensitive operations or architectures involving multiple origins.

---

# 9. XSS: When Untrusted Data Becomes Executable Code

Now we reach one of the most consequential browser vulnerabilities.

**Cross-Site Scripting**, or XSS.

Despite its name, XSS often involves executing attacker-controlled JavaScript within the trusted origin of your own application. Consider the hotel platform's review system. A guest submits:

```text
Excellent location, friendly staff, comfortable beds.
```

Your application displays the review. Perfectly ordinary. But what if a malicious user submits content designed to be interpreted as HTML containing active script behavior?

If your frontend treats that content as executable markup instead of plain text, the attacker may cause code to run in the application's origin. That's an entirely different security situation.

The attacker-controlled code is no longer operating from an unrelated website. It's executing inside the trusted page.

## 9.1 Why this is so dangerous

Imagine code running within:

```text
https://app.example.com
```

It may be able to:

- Read application data available to JavaScript.
- Interact with the DOM.
- Make authenticated requests as the current user.
- Access sensitive values stored in browser-accessible storage.
- Change displayed information.
- Perform operations allowed by the victim's session.

Now reconsider the `HttpOnly` cookie. Can the injected JavaScript read the cookie through `document.cookie`? No, not if the cookie is properly marked `HttpOnly`.

That's a useful protection. But can the injected script make requests to the application's own backend, allowing the browser to attach that cookie automatically? Potentially yes.

This is why `HttpOnly` reduces credential theft opportunities but does not fully neutralize XSS.

An attacker may not need to steal the credential if malicious code can act using the current authenticated browser session.

## 9.2 Vue's default escaping helps

Consider:

```vue
<template>
  <p>{{ reviewText }}</p>
</template>
```

Vue normally treats interpolated content as text rather than executable HTML. That's an important built-in protection. Now consider:

```vue
<template>
  <div v-html="reviewText"></div>
</template>
```

This explicitly requests HTML interpretation. If `reviewText` comes from an untrusted source and hasn't been appropriately sanitized, the application may expose an injection vulnerability.

The appropriate solution isn't to abandon rich text altogether. It's to treat untrusted HTML as untrusted HTML.

If rich formatting is required, use a maintained HTML sanitizer configured for the intended content and keep its security updates current.

For example, libraries such as DOMPurify are commonly used for this purpose. But sanitization isn't a universal replacement for safe rendering. Prefer text rendering when HTML isn't necessary.

## 9.3 Dangerous DOM APIs

Consider:

```javascript
element.textContent = userInput;
```

This assigns text content. Now compare:

```javascript
element.innerHTML = userInput;
```

This parses the input as HTML. The second operation has a fundamentally different security meaning.

Similarly, dynamically constructing JavaScript code or placing untrusted data into executable contexts can create dangerous injection opportunities.

The appropriate defense depends on where the data is inserted. HTML text, HTML attributes, URLs, CSS, and JavaScript code all have different parsing rules.

A generic "escape special characters" function is not sufficient for every context. The broader rule:

**Untrusted information should remain data. It must not silently acquire the authority of executable code.**

## 9.4 Content Security Policy

Content Security Policy, or CSP, provides another layer of defense. A server can define restrictions on which scripts, styles, and other resources a page may load or execute.

For example, a carefully designed script policy can restrict executable scripts to approved sources, nonces, or hashes. CSP can substantially reduce the impact of certain injection vulnerabilities.

But it is not a substitute for proper output encoding and sanitization. And a careless policy that permits unrestricted inline scripts may provide little meaningful protection. CSP is defense in depth.

The first goal remains preventing untrusted data from becoming executable code.

---

# 10. OAuth 2.0: Delegating Access Without Sharing Passwords

Let's move to a different security problem. Suppose your hotel platform wants to integrate with a customer's Google Calendar.

The customer would like confirmed reservations to appear automatically in their calendar. How should your application obtain permission? An extremely bad approach would be:

"Please enter your Google password into our hotel-booking application." That would require users to share credentials with a separate service.

OAuth 2.0 provides a framework for delegated authorization. Instead of giving your application their password, the user authorizes specific access through an authorization server.

Your application receives credentials appropriate for the permitted operation.

## 10.1 The participants

A simplified OAuth system involves:

**Resource owner:** The person or entity controlling access to the resource.

**Client:** The application requesting delegated access.

**Authorization server:** The system responsible for authorizing the client and issuing tokens.

**Resource server:** The API holding the protected resources.

For example:

```text
Customer
   │
   │ Grants permission
   ▼
Google Authorization Server
   │
   │ Issues access token
   ▼
Hotel Application
   │
   │ Calls calendar API
   ▼
Google Calendar Resource Server
```

The hotel application might receive permission to create calendar events. That doesn't necessarily grant access to the user's email or cloud files. The authorization grant can be limited in scope.

## 10.2 Authorization Code with PKCE

A contemporary browser or mobile OAuth client commonly uses the Authorization Code flow with **PKCE**—Proof Key for Code Exchange. Here's the conceptual sequence:

```text
Client                        Authorization Server
  │                                    │
  │ Generate random verifier           │
  │ Derive challenge                    │
  │                                    │
  │── Authorization request ──────────►│
  │   with code challenge              │
  │                                    │
  │        User authenticates          │
  │        and grants consent          │
  │                                    │
  │◄── Authorization code ─────────────│
  │                                    │
  │── Code + original verifier ───────►│
  │                                    │
  │                       Verify challenge
  │                                    │
  │◄── Tokens ─────────────────────────│
```

Why introduce a verifier and challenge? Because an authorization code could otherwise be intercepted or injected under certain attack conditions.

PKCE binds the authorization code redemption to knowledge of the original verifier. A party possessing only the intercepted code should not be able to redeem it successfully.

Modern OAuth security guidance requires PKCE for public clients using authorization codes and recommends it for confidential clients.

OAuth implementations must also handle redirect URI validation, transaction binding, token protection, and other security concerns.

That's why implementing an OAuth flow completely from scratch is usually a poor use of engineering time. Use well-maintained libraries and provider integrations when possible.

---

# 11. OpenID Connect: OAuth Is Not Automatically Login

Here's a common misconception. "OAuth is how users log in with Google." Not exactly.

OAuth 2.0 is fundamentally an authorization framework. It allows clients to obtain delegated access to protected resources.

It doesn't, by itself, define a complete standardized protocol for authenticating users and conveying their identities to relying applications. That's where **OpenID Connect**, or OIDC, enters.

OIDC builds an identity layer on top of OAuth 2.0. It introduces the **ID token**. An ID token is a JWT carrying claims about an authentication event and the authenticated subject.

For example:

```json
{
  "iss": "https://accounts.example-idp.com",
  "sub": "user-901",
  "aud": "hotel-frontend",
  "exp": 1795000000,
  "iat": 1794996400
}
```

The application validates the token according to OIDC rules, including the issuer, intended audience, signature, expiration, and applicable transaction-specific values.

It can then establish an authenticated application session.

## 11.1 ID tokens and access tokens aren't interchangeable

An **ID token** is intended to communicate information about authentication to the relying client. An **access token** is intended to authorize access to protected resources.

They're different artifacts for different purposes. A backend API should not accept an ID token as a general substitute for a properly scoped access token simply because both happen to be JWTs.

Similarly, a client shouldn't assume an arbitrary OAuth access token is proof of the user's identity. Token format alone doesn't establish token purpose.

The issuer, audience, claims, verification rules, and surrounding protocol determine how a token may be used.

## 11.2 Authentication doesn't establish application permissions

Even after successful OIDC login, your application still needs its own authorization model. Suppose a user authenticates through Google. Great.

You now have evidence supporting their identity. Does that mean they can issue refunds in your hotel platform? Certainly not.

Your application must establish which internal user or account corresponds to the external identity and which roles, organizations, and resource permissions apply.

Federated authentication solves an identity problem. It doesn't eliminate your business authorization problem.

And we have now returned, rather elegantly, to the mistake from our opening reservation incident.

---

# 12. A Practical Security Architecture for Our Hotel SaaS

Let's put the major concepts together. Imagine we're designing a multi-tenant hotel-booking SaaS with:

- Vue frontend.
- Node.js backend.
- PostgreSQL database.
- Customer accounts.
- Hotel organization accounts.
- External identity-provider integration.
- Payment and reservation workflows.

One reasonable architecture might be:

```text
                Browser / Vue
                     │
                     │ HTTPS
                     │ Secure session cookie
                     ▼
                 BFF / API
                     │
          ┌──────────┼────────────┐
          │          │            │
          ▼          ▼            ▼
     Auth Session  Authorization  Business Logic
          │          │            │
          └──────────┼────────────┘
                     │
                     ▼
                 PostgreSQL
                     │
                     ▼
            Reservations / Users
```

Here are the security responsibilities.

## Authentication

The backend establishes an authenticated session or validates appropriate tokens. It identifies the caller using trusted credentials.

## Authorization

Every protected operation checks whether the caller has permission for the relevant action and resource.

For multi-tenant data, organization boundaries are enforced at the appropriate query and domain layers.

## Transport security

HTTPS protects communication across the public network. Internal connections also receive suitable protection according to the infrastructure's trust boundaries.

## Browser session protection

Cookies use appropriate `Secure`, `HttpOnly`, `SameSite`, scope, and expiration settings. Session identifiers are unpredictable and invalidated appropriately.

## CSRF protection

Sensitive cookie-authenticated operations use suitable protection against forged cross-site requests.

## XSS prevention

Untrusted content is rendered as text by default. Rich HTML is sanitized when necessary. CSP provides additional protection.

## API validation

The backend validates inputs, enforces permissions, and performs authoritative business checks.

## Operational controls

Sensitive operations are logged appropriately, without exposing secrets. Dependencies are maintained. Credentials and signing keys are protected and rotated under established policies.

This architecture is not the only reasonable design. You could use a different authentication provider, split some services, or adopt a token-based API model. But the security responsibilities remain.

Changing frameworks doesn't make trust boundaries disappear.

---

# 13. Practical Investigation: Find the Boundaries

You can explore several security concepts without attacking any real system.

Use your own application, a local development environment, or a deliberately designed training system.

## Experiment A — Inspect cookie attributes

Open Chrome DevTools on an application you're authorized to inspect.

Navigate to the Application panel and examine stored cookies.

Look for:

```text
Secure
HttpOnly
SameSite
Domain
Path
Expires / Max-Age
```

Ask:

Does JavaScript need direct access to this cookie?

Should the cookie be available to subdomains?

Does its lifetime make sense?

Would the current configuration permit or restrict the cross-site requests relevant to the application?

Notice that DevTools can display HttpOnly cookies even though ordinary page JavaScript cannot read them.

That's expected.

## Experiment B — Observe a CORS preflight

In a local development environment, make a cross-origin fetch request using a non-safelisted custom header:

```typescript
fetch("http://localhost:3000/api/example", {
  headers: {
    "X-Demo-Header": "hello"
  }
});
```

Run the frontend from a different origin, such as `http://localhost:5173`.

Inspect the browser's Network panel.

Depending on the request and applicable preflight caching, you should observe an `OPTIONS` request before the actual request.

Examine:

```text
Origin
Access-Control-Request-Headers
Access-Control-Allow-Origin
Access-Control-Allow-Headers
```

Now compare the behavior when the server doesn't grant the requested cross-origin access.

The crucial question:

Did the browser block the request itself, or did it send a request but prevent JavaScript from accessing the response?

Understand which behavior occurs and why.

## Experiment C — Check authorization at the resource boundary

Create two test users and two reservations in your own local application.

User A owns reservation 100.

User B owns reservation 200.

Authenticate as User A.

Verify that User A can retrieve reservation 100.

Then verify that User A cannot retrieve reservation 200.

Repeat for update and deletion or cancellation operations.

This is a much more meaningful authorization test than simply verifying that unauthenticated requests receive `401`.

The interesting failure is often not an anonymous user entering the system.

It's an authenticated user accessing the wrong resource.

## Experiment D — Compare safe text rendering with HTML rendering

Create a Vue component that receives an untrusted string.

Display the value using:

```vue
<p>{{ content }}</p>
```

Then compare that with:

```vue
<div v-html="content"></div>
```

Use harmless markup, such as a bold paragraph, to observe the difference.

The first treats the content as text.

The second interprets it as HTML.

Ask yourself whether any business requirement truly justifies accepting arbitrary HTML.

If it does, identify where sanitization belongs.

---

# 14. Engineering and Interview Challenges

### Challenge 1 — The Valid Token

A user supplies a valid access token.

The token identifies them as customer 901.

They request reservation 9822, which belongs to customer 902.

The backend verifies the token signature and expiration.

Is the request now authorized?

What additional check is necessary?

### Challenge 2 — The CORS Firewall

A developer configures:

```http
Access-Control-Allow-Origin: https://app.example.com
```

They claim attackers can no longer call the API from unauthorized applications.

Are they correct?

### Challenge 3 — The Protected Cookie

Your session cookie has:

```text
Secure
HttpOnly
SameSite=Lax
```

Does that make the application immune to XSS and CSRF?

Explain what the attributes protect against and what remains vulnerable.

### Challenge 4 — The JWT Logout Problem

Your application uses one-hour self-contained access tokens.

A customer logs out after five minutes.

You delete the token from the browser.

Does that guarantee that every copy of the token has become unusable?

What design changes might improve revocation behavior?

### Challenge 5 — OAuth Versus OIDC

A developer receives an OAuth access token and assumes this proves the user's identity.

Another developer receives an OIDC ID token and wants to send it to every backend API as a bearer access token.

What's wrong with both approaches?

---

# 15. Solutions and Discussion

**Challenge 1**

No.

Token validation establishes an authenticated principal and potentially other relevant claims.

The backend must additionally check whether that principal is permitted to access reservation 9822.

That may involve checking customer ownership, organization membership, role permissions, and resource-specific rules.

Authentication is necessary for many protected operations, but not sufficient for authorization.

**Challenge 2**

No.

CORS is a browser-enforced cross-origin access mechanism.

It doesn't prevent arbitrary HTTP clients from contacting the API.

The backend must enforce authentication and authorization regardless of which client makes the request.

**Challenge 3**

No.

`Secure` restricts cookie transmission to secure connections.

`HttpOnly` prevents direct cookie access through ordinary browser JavaScript.

`SameSite=Lax` reduces certain cross-site request risks.

But XSS may still allow malicious JavaScript to execute authenticated actions within the application's origin.

And some CSRF scenarios may still require additional defenses depending on the application and its origin/site relationships.

These attributes are useful layers of protection, not complete application security.

**Challenge 4**

No.

Deleting the browser's copy doesn't invalidate copies already obtained elsewhere.

A self-contained token may remain usable until it expires unless the server uses additional revocation or validation mechanisms.

Possible approaches include shorter token lifetimes, centrally checked revocation state, session-version policies, and carefully managed refresh tokens.

The appropriate design depends on security requirements and operational complexity.

**Challenge 5**

OAuth access tokens are designed for delegated resource access, not automatically for conveying standardized authentication assertions to a client.

OIDC introduces ID tokens for that purpose.

Conversely, an ID token intended for a particular relying client is not interchangeable with an access token intended for a resource server.

Each token must be validated and used according to its protocol-defined purpose, issuer, audience, and applicable claims.

---

# 16. The Mental Model Worth Keeping

Security is easier to understand when you stop treating it as one enormous checkbox labeled "secure."

Different mechanisms protect different boundaries.

**Authentication** establishes identity.

**Authorization** determines what that identity may do.

**Sessions and tokens** carry or represent authentication and authorization context between requests.

**TLS** protects communication across network connections.

**Same-origin policy** isolates browser security contexts.

**CORS** controls selected cross-origin access to responses.

**CSRF defenses** protect against unauthorized requests made using a victim's browser credentials.

**XSS defenses** prevent untrusted data from becoming executable code inside your application's origin.

**OAuth 2.0** supports delegated authorization.

**OpenID Connect** adds a standardized authentication layer.

None of these mechanisms automatically substitutes for another.

An application can use HTTPS and still have broken authorization.

It can use HttpOnly cookies and still suffer XSS.

It can configure CORS perfectly and still expose an API to unauthorized callers.

It can validate JWT signatures correctly and still give users access to the wrong organization's data.

And that brings us back to our opening incident.

The customer who accessed someone else's reservation didn't defeat the authentication system.

The API simply failed to ask the next question.

**Security is not merely proving who someone is. It's ensuring that every action crosses only the boundaries that person is entitled to cross.**

That's the mental model worth carrying into architecture reviews, API design, frontend development, and senior engineering interviews.

---

# 17. Next Session — Delivering Modern Web Applications

We've studied browsers, networking, HTTP, frontend architecture, state, APIs, and security.

But there's one enormous step we've mostly taken for granted.

How does your source code actually become a working application delivered to a customer?

Your Vue project contains hundreds of `.vue` and `.ts` files.

The browser doesn't understand Vue single-file components directly.

TypeScript types don't exist at runtime.

Development servers behave differently from production hosting.

And modern frontend deployments may involve build pipelines, content hashing, CDNs, server-side rendering, hydration, and multiple caching layers.

Now imagine a production deployment where the application works perfectly for new visitors but fails for customers with older cached HTML.

Or a server-rendered page that looks correct until JavaScript starts, at which point the interface mysteriously changes.

In **SE240-L04 — Delivering Modern Web Applications**, we'll follow a frontend application from source repository to production browser.

We'll investigate bundlers, modules, code splitting, client-side rendering, server-side rendering, hydration, CDNs, deployment strategies, and the engineering trade-offs behind modern web delivery.

---


---

## Next Lecture — SE310-L03: Application and Infrastructure Security

Continue in **SE310 — Web APIs, Identity, and Security**.

## Further Reading — Optional References

1. [OWASP — Broken Object-Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/) — One of the most important API authorization failure modes.
2. [MDN — Same-Origin Policy](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy) — Browser isolation boundaries.
3. [MDN — CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS) — Cross-origin access and preflight requests.
4. [MDN — Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie) — Cookie attributes and security behavior.
5. [OWASP — CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) — Defenses against cross-site request forgery.
6. [OWASP — XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) — Safe rendering, encoding, and sanitization.
7. [RFC 9700 — OAuth 2.0 Security Best Current Practice](https://www.rfc-editor.org/rfc/rfc9700.html) — Modern OAuth security recommendations, including PKCE.
8. [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html) — The identity layer built on OAuth 2.0.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE310-L02  AUTHENTICATION AND BROWSER SECURITY — INTERVIEW GLANCE CARD

OPENING (BOLA / IDOR)
  Valid session + HTTPS + auth middleware — GET /reservations/9822 still returns another's booking
  Authn ≠ Authz        Who is it? vs May they do THIS on THIS resource?

AUTHORIZATION
  Constrain lookup     id + customerId from trusted server auth context — never client-supplied id alone
  Multi-tenant         WHO + ORG + RESOURCE + ACTION + CONDITIONS
  RBAC                 Permissions via roles
  ABAC                 Actor/resource/action/context attributes
  UI hide              Not authorization — backend must reject

SESSIONS
  Opaque ID            Server store (Redis/DB); revoke/expire centrally
  Cookie attrs         Secure · HttpOnly · SameSite · Path; __Host- adds Secure+Path=/+no Domain
  Trade-off            Shared session store for multi-instance apps

JWT
  header.payload.sig   Signed ≠ encrypted; don't put secrets in payload
  Pros                 Validate without every-request central lookup
  Revocation           Logout ≠ instant kill until expiry unless extra state/short TTL/refresh design
  Validate fully       Signature + allowed alg + iss/aud/exp + purpose — not “decode and trust”

COOKIES vs BEARER
  Orthogonal dims      Session vs self-contained · Cookie vs Authorization · Storage choice
  Cookie auth          Browser auto-send → CSRF risk; HttpOnly helps vs JS read
  Bearer               Authorization: Bearer …; localStorage readable by XSS
  BFF                  Browser session cookie → BFF holds API tokens; still need CSRF/session care

SAME-ORIGIN POLICY
  Origin               scheme + host + port
  Limits               Cross-origin JS reading responses without permission
  Does NOT stop        Many cross-origin sends (forms, images, navigation)

CORS
  ACAO                 Permission for browser JS to read cross-origin response
  Preflight            OPTIONS for some non-simple requests — ≠ authentication
  Credentials          credentials:include + specific origin + Allow-Credentials; not *
  Myth bust            CORS ≠ API auth — curl/backends ignore it

CSRF
  Abuse                Auto-attached cookies perform state change; attacker may not need response body
  CORS ≠ CSRF fix      Form POST can succeed without readable CORS
  Defenses             CSRF token · SameSite · Origin/Referer checks · custom headers · no unsafe GET
  SameSite ≠ origin    app.example vs api.example = different origins, often same site

XSS
  Untrusted → code     In your origin; can act as user / read JS-visible data
  HttpOnly             Blocks document.cookie read; script can still call APIs with cookies attached
  Vue {{ }}            Text escape; v-html / innerHTML = HTML interpretation — sanitize if needed
  Contexts differ      HTML text vs attr vs URL vs JS — one “escape” fn isn't universal
  CSP                  Defense in depth — not substitute for safe rendering

OAUTH 2.0
  Delegated authz      Access without sharing passwords; scopes limit
  Roles                Resource owner · client · authorization server · resource server
  Auth Code + PKCE     Verifier/challenge binds code redemption; required for public clients (BCP)

OIDC
  Identity layer       ID token (JWT) for authn event to relying client
  ID ≠ access token    Different purposes/audiences — don't swap casually
  Still need           App-level authz after federated login

ARCHITECTURE REMINDER
  Authn · Authz · sessions/tokens · TLS · SOP · CORS · CSRF · XSS · OAuth · OIDC
  None substitutes for another.

SENIOR LINE: Security isn't proving who someone is—it's ensuring every action crosses only allowed boundaries.
```

