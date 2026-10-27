---
id: SE310-L03
course: SE310
title: "Application and Infrastructure Security"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S09]
prev: SE310-L02
next: null
---




# SE310 — Web APIs, Identity, and Security

## Lecture 03: Application and Infrastructure Security

*How an application can authenticate every user correctly, encrypt every connection, and still hand an attacker somebody else's private data.*

---

## 1. The Breach That Looked Like Normal Traffic

Your company operates a successful SaaS platform used by several hundred hotel businesses.

Each hotel has its own account, employees, reservations, customer records, invoices, and uploaded documents. The system uses a modern authentication provider, HTTPS everywhere, private S3 buckets, PostgreSQL, and AWS IAM roles.

The application has passed security reviews. Passwords aren't stored in plaintext, authorization tokens are validated, and the database isn't exposed to the internet.

One morning, a hotel manager reports something disturbing: while reviewing reservations, he discovered an invoice belonging to a completely different hotel.

Your security team investigates.

The application logs show an ordinary request:

```http id="vxb3sk"
GET /api/reservations/8b0a9f21
Authorization: Bearer eyJ...
```

The server validated the token. The user was authenticated, the reservation existed, PostgreSQL returned the record, and the API responded with HTTP 200.

There was no SQL injection. No stolen password. No suspicious AWS activity.

The attacker simply changed a reservation identifier in an otherwise legitimate request.

The backend executed:

```typescript id="0qvuyd"
const reservation = await repository.findOne({
  where: { id: req.params.id }
});

return res.json(reservation);
```

Can you see the problem?

The query established that the reservation existed. It never established that the authenticated user was entitled to access it.

A valid identity was mistakenly treated as sufficient authority.

The API was functioning precisely as implemented. Its network connections were encrypted, its database credentials were protected, and its token validation was correct.

Yet it had crossed the most important security boundary in the application.

**Security failures frequently occur not because one protective mechanism is broken, but because engineers mistake one successful protection for a guarantee it was never designed to provide.**

This session is about understanding those boundaries: between users and resources, applications and infrastructure, trusted code and untrusted data, and one customer and another.

---

## 2. Security Begins With a Threat Model

Software engineers often approach security as a checklist:

- Use HTTPS.
- Validate JWTs.
- Parameterize SQL.
- Encrypt data.
- Configure IAM.
- Scan dependencies.

These are worthwhile practices, but they don't constitute a complete security strategy.

A system can implement every item and still contain serious vulnerabilities.

Why?

Because security controls need to protect something against a particular class of threat.

A useful starting point is **threat modeling**: systematically examining what a system protects, who might attack it, which boundaries exist, and how those boundaries could be crossed.

### Assets, actors, and entry points

Consider our hotel-booking SaaS.

Its valuable assets include customer information, reservation history, payment records, employee credentials, supplier API keys, and the ability to modify bookings or initiate refunds.

Potential threat actors include external attackers, compromised customer accounts, malicious insiders, and attackers who gain access through vulnerable third-party dependencies.

Entry points include public APIs, administrative interfaces, upload endpoints, webhooks, background-job payloads, and infrastructure-management interfaces.

But a list of assets isn't enough.

We also need to understand how information and authority move through the system.

### Draw the trust boundaries

Consider this simplified architecture:

```text id="sp5noa"
        INTERNET / UNTRUSTED CLIENTS
                     │
                     ▼
              API Gateway
                     │
             ┌───────┴───────┐
             ▼               ▼
       Authentication    Request Validation
             │               │
             └───────┬───────┘
                     ▼
               Node.js API
                     │
            ┌────────┼────────┐
            ▼        ▼        ▼
        PostgreSQL   S3    External APIs
```

The important boundaries are not merely the boxes.

They include the transition from an unauthenticated network request to an authenticated identity, from authenticated identity to authorized business operation, and from application code to resources carrying broader infrastructure privileges.

For example, the Node.js application may possess an IAM role that allows it to read thousands of customer documents from S3.

An individual user should ordinarily have permission to access only a small subset.

The application therefore acts as a privileged intermediary.

A defect in its authorization logic can transform limited customer access into much broader data access.

### STRIDE as a thinking tool

One common threat-modeling framework is STRIDE.

| Category | Question |
|---|---|
| Spoofing | Can someone impersonate another identity? |
| Tampering | Can information or system state be modified improperly? |
| Repudiation | Can someone deny an action because trustworthy evidence is absent? |
| Information disclosure | Can sensitive data become accessible to unauthorized parties? |
| Denial of service | Can an attacker make the system unavailable? |
| Elevation of privilege | Can someone obtain authority beyond what they should possess? |

STRIDE isn't intended to generate six mandatory sections in every design document.

Its value lies in prompting questions that developers might otherwise overlook.

For example, a document-upload feature may appear straightforward until someone asks whether the uploaded file can trigger expensive processing, overwrite another tenant's data, or cause the server to contact an internal address.

**Threat modeling is architecture review from the perspective of someone trying to misuse the system.**

---

## 3. Authentication and Authorization: Different Questions

We covered browser authentication mechanisms in the web engineering courses (CS230, SE240, SE310), so we won't reconstruct OAuth, sessions, and JWT validation here.

The distinction that matters for architecture is simple.

**Authentication asks:** Who is making the request?

**Authorization asks:** Is that identity permitted to perform this operation on this resource under these conditions?

Authentication can succeed while authorization fails.

For example, a hotel employee may be legitimately authenticated but should not be allowed to refund another hotel's reservation.

### Broken object-level authorization

The vulnerability in our opening incident is commonly called **Broken Object Level Authorization**, or BOLA.

It is a prominent category in OWASP's API security guidance.

A vulnerable endpoint:

```typescript id="0q0isb"
app.get("/reservations/:id", authenticate, async (req, res) => {
  const reservation = await reservationRepository.findOneBy({
    id: req.params.id
  });

  if (!reservation) {
    return res.sendStatus(404);
  }

  res.json(reservation);
});
```

The code checks authentication and resource existence, but not resource ownership or access rights.

A stronger approach uses a verified authorization context:

```typescript id="2vdy39"
app.get("/reservations/:id", authenticate, async (req, res) => {
  const tenantId = req.auth.activeTenantId;

  const reservation = await reservationRepository.findOneBy({
    id: req.params.id,
    tenantId
  });

  if (!reservation) {
    return res.sendStatus(404);
  }

  res.json(toReservationResponse(reservation));
});
```

Here `activeTenantId` must have been established from trusted server-side membership and authorization checks. It must not simply be copied from an arbitrary client-supplied header.

The query narrows access to the active tenant's resources.

However, this is still not a complete authorization solution. Some users within the same tenant may have different permissions, and sensitive fields may need separate access controls.

### Authorization has several dimensions

A mature application may need to consider:

- **Identity:** Which user or service is acting?
- **Tenant:** Which organization owns the resource?
- **Role:** What category of operations is permitted?
- **Resource:** Which specific object is being accessed?
- **Action:** Is the operation a read, modification, deletion, or financial transaction?
- **Context:** Does the current resource state permit the action?

Suppose a receptionist is allowed to view reservations but not issue refunds.

The system needs both tenant-level restrictions and operation-level permissions.

A manager may have refund authority, but a refund may still be forbidden if the transaction has already been fully refunded.

This final condition is a domain invariant rather than a conventional role check.

Security and business correctness meet at the operation boundary.

### Don't trust the UI to enforce permissions

Hiding the Refund button from unauthorized users improves usability.

It is not a security boundary.

A user can construct HTTP requests independently of the browser interface.

Every sensitive backend operation must enforce its own authorization requirements through trusted server-side mechanisms.

---

## 4. Multi-Tenant Isolation: One Database, Many Security Domains

Multi-tenancy makes authorization especially consequential.

Imagine a PostgreSQL table:

```sql id="7wfbml"
CREATE TABLE reservations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  guest_name TEXT NOT NULL,
  status TEXT NOT NULL,
  total_cents INTEGER NOT NULL
);
```

Every reservation belongs to a tenant.

A legitimate query might be:

```sql id="ij7s0s"
SELECT *
FROM reservations
WHERE tenant_id = $1
  AND id = $2;
```

But a developer implementing an administrative report accidentally writes:

```sql id="cxhzx7"
SELECT *
FROM reservations
WHERE status = 'CONFIRMED';
```

The report now returns confirmed reservations across every tenant.

Nothing is technically wrong with the SQL statement.

The security requirement was omitted.

### Where should tenant isolation live?

There are several possible approaches.

**Application-level filtering:** Repositories or domain services include tenant restrictions in relevant queries.

**Database-enforced policies:** PostgreSQL Row-Level Security, or RLS, can restrict which rows a database role may access.

**Separate schemas or databases:** Tenants receive stronger logical separation at the storage level.

**Separate infrastructure:** Particularly sensitive customers may receive dedicated application and data environments.

These strategies have different cost, isolation, and operational characteristics.

For many SaaS platforms, shared tables with carefully enforced tenant scoping are a practical starting point.

But consistency matters. One forgotten filter can compromise the boundary.

### PostgreSQL Row-Level Security

PostgreSQL supports policies such as:

```sql id="45zeb7"
ALTER TABLE reservations
ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_reservations
ON reservations
USING (
  tenant_id = current_setting('app.tenant_id')::uuid
)
WITH CHECK (
  tenant_id = current_setting('app.tenant_id')::uuid
);
```

This illustrates how database access can depend on a session or transaction context established by the application.

A production implementation must control how that context is set, particularly when connections are pooled. Transaction-local settings are often preferable, and all relevant queries must execute under the correct context.

The application must never let an untrusted user arbitrarily select the tenant context.

Also, database owners and roles with special privileges may bypass RLS, unless appropriate configurations such as `FORCE ROW LEVEL SECURITY` are applied where relevant.

RLS is powerful defense in depth, but configuring it incorrectly can create a false sense of security.

### Isolation is more than SQL

Tenant boundaries also appear in:

- S3 object keys and authorization.
- Redis cache keys.
- Background-job payloads.
- Search indexes.
- Log retrieval.
- Exports and reports.
- Webhook destinations.
- Administrative support tooling.

Imagine caching a reservation under:

```text id="jha9ws"
reservation:123
```

If identifiers can overlap across tenants, one tenant may retrieve another tenant's cached data.

A safer key design might incorporate the relevant security scope:

```text id="o6looc"
tenant:456:reservation:123
```

Even then, the application must verify that the requesting identity is authorized for tenant 456.

Namespacing reduces accidental collisions; it doesn't replace authorization.

**Tenant isolation is an end-to-end system invariant, not a database convention.**

---

## 5. Least Privilege: Limiting the Damage of Compromise

Let's return to AWS.

Suppose the booking API needs to read and write customer documents in one S3 bucket.

A developer attaches:

```json id="1di8q5"
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}
```

The application now possesses extremely broad S3 permissions.

Everything works.

But if an attacker finds an application vulnerability that allows misuse of those credentials, the potential damage extends far beyond the application's intended operations.

The principle of **least privilege** says that a component should receive only the authority necessary to perform its responsibilities.

A narrower permission might look like:

```json id="njys14"
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::hotel-documents/customer-files/*"
}
```

This reduces the set of AWS operations available to the application.

It doesn't, by itself, isolate individual tenants within that prefix.

The application or a more granular access design must still enforce that boundary.

### Defense in depth

Consider a secure document-download operation.

Several defenses cooperate:

```text id="qdd482"
Authenticated User
        │
        ▼
Tenant Membership Check
        │
        ▼
Object-Level Authorization
        │
        ▼
Application IAM Role
        │
        ▼
S3 Bucket Policy
        │
        ▼
Private S3 Object
```

Each mechanism addresses a different concern.

If application authorization fails, IAM restrictions may still limit the damage to a particular bucket or prefix.

If IAM is overly broad, a properly restrictive bucket policy may prevent some operations.

But defense in depth isn't a guarantee that one defective layer will always be compensated for by another.

An applicable AWS explicit deny overrides an allow, while effective permissions also depend on identity, resource, organization, session, and permissions-boundary policies according to AWS's evaluation rules.

For cloud security, the senior-level question is:

**If this application process were compromised, what could its existing credentials actually do?**

That is more useful than asking whether the application has an IAM role.

---

## 6. Secrets: Credentials Have a Lifecycle

A secret is any value whose disclosure could grant unauthorized access or compromise a protected operation.

Examples include:

- Database passwords.
- External API keys.
- Private signing keys.
- Payment-provider credentials.
- Webhook verification secrets.
- OAuth client secrets.

The obvious rule is not to commit secrets into source code.

But real secret management is broader.

### Where secrets travel

A typical credential lifecycle looks like:

```text id="fy17ms"
Secret Creation
       │
       ▼
Secure Storage
       │
       ▼
Delivery to Workload
       │
       ▼
Application Use
       │
       ▼
Rotation / Revocation
```

At each stage, there is a potential exposure path.

For example, a secret might be stored safely in AWS Secrets Manager but accidentally included in an error log.

Or a deployment pipeline might retrieve it correctly but print its value during debugging.

Or a former employee's credentials might remain valid long after access should have been revoked.

### Prefer temporary credentials where possible

AWS IAM roles allow workloads to obtain temporary credentials through the supported credential-provider mechanisms.

That avoids distributing long-lived AWS access keys to every application instance.

But third-party integrations may still require long-lived API secrets.

Those should be stored and accessed with appropriate controls, then rotated according to the provider's capabilities and the organization's operational requirements.

### Rotation is not simply replacement

Imagine a payment provider allows two active API keys.

A safe rotation process might:

1. Create a new key.
2. Deploy or activate the new credential.
3. Verify that all relevant workloads use it successfully.
4. Revoke the old key.
5. Confirm that no remaining process depends on it.

If the provider supports only one valid credential at a time, rotation becomes more operationally complicated.

The application may also cache secrets at startup, requiring a restart or an explicit refresh mechanism.

Secure secret storage is therefore only one part of credential management.

---

## 7. Encryption: Protecting Data in Different States

Engineers frequently describe a system as secure because its data is encrypted.

But encrypted against which threat?

Two common categories are **encryption in transit** and **encryption at rest**.

### Encryption in transit

TLS protects communication between endpoints against network interception and tampering when implemented and validated correctly.

For example:

```text id="3skbcx"
Browser ── TLS ──► API Gateway
```

But TLS termination creates another boundary.

If API Gateway terminates HTTPS and forwards traffic to another service, that downstream connection requires its own security assessment.

The entire path is not automatically encrypted merely because the browser displays a padlock.

Within a cloud environment, encryption requirements depend on the network architecture, service capabilities, risk model, and compliance obligations.

### Encryption at rest

S3, RDS, and other AWS services support encryption of stored data.

Encryption at rest helps protect against certain classes of unauthorized storage access and media exposure.

However, if the application has legitimate permission to decrypt and retrieve customer documents, an attacker who compromises that application may also be able to retrieve plaintext documents.

Encryption doesn't automatically prevent misuse by authorized principals.

### Key management

Encryption security depends heavily on the protection and use of cryptographic keys.

AWS Key Management Service, or KMS, supports managed key operations and access control for many AWS-integrated encryption workflows.

Depending on the service and configuration, teams may use AWS-owned, AWS-managed, or customer-managed keys, each with different operational and control implications.

For especially sensitive data, key access, key lifecycle, auditability, and separation of duties may be important architectural considerations.

### Passwords are different

Passwords should not ordinarily be stored using reversible encryption.

They should be processed through appropriate password-hashing algorithms, such as Argon2id, using a suitable configuration and unique salts.

This protects stored password verifiers against different threats than ordinary encryption addresses.

Cryptography is not one interchangeable security mechanism.

Choose the primitive that matches the required property: confidentiality, integrity, authentication, or password verification.

---

## 8. Injection: When Data Becomes Instructions

Let's examine one of software security's oldest recurring problems.

An application receives user input:

```typescript id="2zwp4v"
const email = req.query.email;
```

The developer constructs SQL:

```typescript id="lxous1"
const sql = `
  SELECT *
  FROM customers
  WHERE email = '${email}'
`;
```

The application has mixed untrusted data with executable SQL syntax.

A malicious input can alter how the database interprets the resulting query.

This is SQL injection.

### Parameterized queries

A stronger approach separates query structure from values:

```typescript id="0gedx1"
const result = await dataSource.query(
  "SELECT * FROM customers WHERE email = $1",
  [email]
);
```

The parameter is treated as data rather than incorporated as SQL source syntax.

This is also one reason properly used ORM query parameters are valuable.

However, parameterization is not a universal string-safety mechanism.

For example, SQL identifiers such as table names and column names generally cannot be supplied as ordinary value parameters.

If a user can choose a sort column, the application should map an allowed value to an approved SQL identifier rather than concatenate arbitrary text.

### Injection extends beyond SQL

Similar problems occur when untrusted input is interpreted as:

- Shell commands.
- Template expressions.
- File paths.
- Query languages.
- Regular expressions.
- Serialized executable objects.
- Configuration or workflow instructions.

The common failure is crossing a boundary between **data** and **authority-bearing instructions**.

A developer who has learned to parameterize SQL but freely constructs shell commands from user input hasn't solved the underlying problem.

### Insecure deserialization

Untrusted serialized data must also be treated carefully.

Ordinary `JSON.parse()` produces JavaScript values and does not itself execute arbitrary code, but parsing does not validate whether those values are safe for a business operation.

A payload may contain unexpected fields, deeply nested structures, or values designed to exploit subsequent processing.

More dangerous serialization formats or deserialization libraries may support object construction, type restoration, or executable behavior with security consequences.

The safe approach is to validate untrusted input against an explicit schema and avoid granting client-controlled fields direct authority over sensitive application state.

For example, this is dangerous:

```typescript id="0kvucp"
await userRepository.update(
  userId,
  req.body
);
```

If `req.body` contains `isAdmin: true`, a generic update may modify fields the user was never authorized to control.

This is often discussed as *mass assignment* or broken property-level authorization.

The safer design maps approved fields explicitly.

---

## 9. SSRF: When the Server Becomes the Attacker's Browser

Imagine your hotel SaaS lets customers provide a URL containing their company logo.

The backend downloads the image and stores it in S3.

```typescript id="3mj522"
const response = await fetch(req.body.logoUrl);
```

This looks harmless.

But the backend is not an ordinary browser running on a customer's computer.

It may have network access to internal services, databases, cloud metadata endpoints, and administrative APIs that are unreachable from the public internet.

If an attacker controls the URL, they may be able to persuade the server to contact unintended destinations.

This is **Server-Side Request Forgery**, or SSRF.

### Why network position matters

Consider:

```text id="u3sov1"
Attacker
   │
   ▼
Public Upload API
   │
   ▼
Backend HTTP Client
   │
   ├── Public Internet
   ├── Internal Services
   └── Cloud Metadata / Infrastructure
```

The attacker does not necessarily need direct network access to internal infrastructure.

They only need a vulnerable application component willing to make requests on their behalf.

This creates a particularly dangerous interaction between application behavior and cloud-network privileges.

### Defending against SSRF

The strongest defense is often avoiding arbitrary outbound URLs altogether.

If the application only needs images from three known supplier domains, configure a narrowly defined allowlist and an appropriate outbound network policy.

For systems that genuinely require user-provided URLs, defenses may include:

- Restricting permitted protocols.
- Validating destinations against a clear allowlist or network policy.
- Preventing connections to prohibited internal and metadata addresses.
- Handling redirects safely.
- Defending against DNS rebinding and validation-to-connection races.
- Enforcing timeouts, response-size limits, and content validation.
- Restricting the application's network egress and cloud permissions.

Simply checking whether a URL starts with `https://` is insufficient.

Even a hostname validation can fail if DNS resolution, redirects, or connection establishment bypass the original check.

AWS EC2's Instance Metadata Service v2 provides an additional defense against some metadata-related attacks, but it does not make an application immune to SSRF.

The broader lesson is that **an application with network access is exercising a privilege whenever it makes an outbound request**.

That privilege needs boundaries.

---

## 10. Browser Security Still Matters Behind a Secure Backend

the web engineering courses (CS230, SE240, SE310) covered XSS, CSRF, browser-origin rules, and authentication mechanisms in greater detail.

Here, the architectural point is that browser security cannot be delegated entirely to the backend or API gateway.

### Cross-Site Scripting

Cross-site scripting occurs when untrusted content is incorporated into a page in a way that allows unintended script execution.

Modern frameworks such as Vue escape ordinary interpolated text by default, but unsafe HTML rendering, direct DOM manipulation, and dangerous third-party components can bypass those protections.

For example, rendering arbitrary user-controlled HTML through `v-html` requires careful consideration.

An XSS vulnerability can allow malicious script to act within the user's browser origin, potentially performing authenticated operations or accessing data available to that script.

### Cross-Site Request Forgery

CSRF concerns inducing a browser to send an unwanted authenticated request, particularly when the browser automatically attaches credentials such as cookies.

Defenses include suitable SameSite cookie configuration, CSRF tokens where needed, origin checks, and correct separation of safe and state-changing operations.

Using JWTs does not automatically eliminate CSRF. The actual risk depends on where credentials are stored and how requests are authenticated.

### Content Security Policy

A Content Security Policy can restrict which scripts and other resources the browser may load or execute.

It is valuable defense in depth, especially against some injection consequences.

But CSP is not an excuse to render untrusted HTML unsafely.

Likewise, CORS does not enforce backend authorization. It controls particular browser cross-origin access behavior, not whether an attacker can make HTTP requests with another client.

A secure application requires the browser, API, and underlying infrastructure to enforce their respective boundaries.

---

## 11. Supply-Chain Security: The Code You Didn't Write

Your Node.js application contains 20,000 lines of proprietary code.

Its dependency tree may contain vastly more code than that, including direct and transitive dependencies.

The application also depends on build tools, CI actions, Docker base images, package registries, and deployment infrastructure.

All of these participate in the software supply chain.

A supply-chain attack compromises or abuses one of those upstream components.

### The compromised dependency

Suppose a widely used npm package publishes a malicious update.

Your application's lockfile may prevent unexpectedly selecting the new version during a controlled installation, but the system remains vulnerable if the malicious version is deliberately or automatically introduced during a dependency update.

Package lifecycle scripts may also execute during installation.

This creates a trust boundary before your application even starts.

### The compromised pipeline

Consider a GitHub Actions workflow that builds and deploys production images.

If a malicious third-party action executes in a privileged release job, it may gain access to repository contents, workflow tokens, credentials, or deployment mechanisms according to the job's permissions.

The attacker's objective may be to modify the image or publish a malicious artifact.

Your application source code could remain perfectly innocent.

### Practical defenses

A production engineering team should establish controls such as:

- Dependency lockfiles and controlled updates.
- Dependency and container vulnerability scanning.
- Restricting CI job permissions.
- Reviewing third-party build actions.
- Pinning sensitive CI actions to reviewed commit SHAs.
- Using short-lived cloud credentials.
- Separating verification from privileged deployment.
- Protecting release branches and environments.
- Tracking artifact provenance and build identities.

A Software Bill of Materials, or SBOM, can help establish which components exist in an artifact and support vulnerability-response decisions.

Artifact signing and provenance verification can provide evidence about where an artifact came from and which build process produced it.

But cryptographic provenance doesn't prove the source code is benign.

A malicious artifact can be perfectly signed by a compromised but otherwise legitimate build pipeline.

Security requires protecting both the code and the authority used to produce and deploy it.

---

## 12. Container and Cloud Security: Shared Infrastructure, Shared Responsibility

Containers provide isolation, but they don't create invulnerable sandboxes.

An application may run as root inside a container, mount sensitive host directories, or receive broad Linux capabilities.

A compromised process can then exercise the authority available within that environment.

Security-sensitive container practices include running as an unprivileged user, minimizing capabilities, limiting writable filesystem access, and avoiding privileged execution.

Image scanning and timely base-image updates are also valuable.

However, no container configuration makes it safe to expose arbitrary internal administrative APIs.

### Network isolation

Consider a Node.js API that must connect to PostgreSQL.

The database should not ordinarily accept connections from arbitrary internet clients.

Security groups, subnet design, and appropriate network boundaries can limit which workloads can contact it.

But a database restricted to application servers is still vulnerable to misuse by a compromised application server.

Network isolation reduces exposure. It doesn't eliminate the need for database permissions, safe queries, and tenant authorization.

### Separate environments and duties

Development, staging, and production should have deliberate isolation.

For example, production credentials should not be available to ordinary pull-request workflows.

A compromised test dependency should not automatically obtain production deployment authority.

Separate AWS accounts may provide stronger administrative boundaries than merely creating differently named resources within one account.

The correct degree of isolation depends on organizational risk and operational requirements.

### Administrative access

Human access deserves the same discipline as application access.

Production access should be limited, authenticated appropriately, audited, and revoked promptly when no longer needed.

Multi-factor authentication and temporary privileged access can reduce the consequences of stolen or forgotten credentials.

A system with secure application code but uncontrolled administrator access remains vulnerable.

**Infrastructure security is ultimately about restricting authority and limiting blast radius.**

---

## 13. Security Logging and Incident Response

Security failures are not always immediately visible as application errors.

Remember our opening incident: the attacker received HTTP 200.

From an ordinary availability dashboard, the service looked healthy.

This means security observability requires different questions from performance monitoring.

### What should security events reveal?

Useful security signals may include:

- Repeated authorization failures.
- Unusual access to sensitive resources.
- Changes to IAM permissions.
- Unexpected administrative actions.
- New access keys or role assumptions.
- Suspicious bulk exports.
- Unusual outbound network activity.
- Changes to audit configuration.

But logs must be designed carefully.

Recording complete authentication tokens or payment details creates another security risk.

Security logs should preserve relevant identities, actions, resource references, timestamps, and outcomes without unnecessarily exposing sensitive values.

### What if customer data has leaked?

A credible security response has several phases.

**Containment:** Prevent ongoing unauthorized access.

**Evidence preservation:** Retain relevant logs and system state without unnecessarily exposing more data.

**Scope assessment:** Determine which accounts, resources, and time intervals may have been affected.

**Credential and access remediation:** Revoke compromised access and correct authorization defects.

**Recovery:** Restore safe service behavior and verify that controls work.

**Notification and legal assessment:** Follow applicable contractual, regulatory, and incident-reporting obligations.

For a business operating in the European Union, certain personal-data incidents may trigger GDPR reporting obligations, depending on their circumstances.

Those requirements should be handled through an established incident process rather than improvised by developers during an outage.

### Don't rush into destructive cleanup

If an attacker compromises an application server, immediately deleting every suspicious file may destroy evidence needed to determine what happened.

Similarly, restarting all infrastructure can remove volatile information.

Containment remains urgent, but serious incidents require coordinated evidence preservation and investigation.

This is one reason security response plans differ from ordinary reliability runbooks.

---

## 14. Practical Lab — Security Review of a Multi-Tenant SaaS

Imagine you join a small engineering team operating a hotel-management SaaS.

The architecture contains:

```text id="ox0g4f"
                      INTERNET
                         │
                         ▼
                    CloudFront
                         │
                         ▼
                   API Gateway
                         │
                         ▼
                    Node.js API
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
         PostgreSQL    Private S3   Supplier APIs
                         │
                         ▼
                   Documents

               Background Workers
                    │      │
                    ▼      ▼
                   SQS   Email API
```

The system has four known design characteristics.

**A.** Each API request has a validated JWT, but repositories frequently load records by ID without an explicit tenant filter.

**B.** Users can submit arbitrary image URLs, which the backend downloads using `fetch()`.

**C.** The API IAM role can read and write objects across several unrelated S3 buckets.

**D.** The production release pipeline uses a long-lived AWS access key stored in GitHub secrets.

Your task is to review the system as a senior engineer.

### Investigation A — Build the threat model

For each characteristic, identify:

1. The protected asset.
2. The trust boundary being crossed.
3. The authority granted to the component.
4. A plausible failure or misuse scenario.
5. A control that reduces the risk.

Avoid automatically categorizing every issue as SQL injection or authentication failure.

The problems are different.

### Investigation B — Repair object authorization

Start with this vulnerable repository method:

```typescript id="yfe3a7"
async function getReservation(id: string) {
  return repository.findOneBy({ id });
}
```

Redesign it so that tenant ownership is enforced.

A reasonable application-facing signature could be:

```typescript id="nsqiul"
type AuthorizedScope = {
  userId: string;
  tenantId: string;
  permissions: readonly string[];
};

async function getReservation(
  scope: AuthorizedScope,
  reservationId: string
) {
  if (!scope.permissions.includes("reservation:read")) {
    throw new Error("Forbidden");
  }

  return repository.findOneBy({
    id: reservationId,
    tenantId: scope.tenantId
  });
}
```

This assumes `AuthorizedScope` is constructed by trusted server-side authentication and authorization middleware, not copied from the request body.

Next, decide how you'd test access by a user belonging to Tenant A against a reservation belonging to Tenant B.

### Investigation C — Reduce IAM privileges

Suppose the API should only retrieve customer documents.

It should not create buckets, delete objects, or access unrelated storage.

Define a narrowly scoped IAM policy permitting only the required operations on the relevant object prefix.

Then ask whether the S3 bucket policy imposes additional restrictions.

Remember that the application may still require a separate authorization check to determine whether the requesting user may access a specific document.

### Investigation D — Review the image importer

An insecure implementation:

```typescript id="dxvtto"
app.post("/images/import", async (req, res) => {
  const response = await fetch(req.body.url);

  const data = Buffer.from(
    await response.arrayBuffer()
  );

  await storeImage(data);

  res.sendStatus(201);
});
```

Identify the problems beyond SSRF.

Consider uncontrolled response sizes, content-type assumptions, timeouts, malformed image processing, and resource exhaustion.

Propose an implementation strategy that constrains both the network destination and the downloaded content.

Do not assume a single URL-regex check is sufficient.

### Investigation E — Rank the findings

You have five working days to implement initial security improvements.

Rank the four issues according to likely exposure, business impact, ease of exploitation, and mitigation cost.

A defensible initial priority might place tenant isolation first because an authenticated user may already be able to access another customer's records.

However, the actual order could change if the image-import feature is publicly accessible and the backend has highly privileged access to sensitive internal infrastructure.

Security prioritization depends on concrete threat paths, not generic severity labels alone.

---

## 15. Engineering and Interview Challenges

### Challenge 1 — The authenticated data leak

A user has a valid JWT. The backend verifies its signature and expiration, then retrieves an invoice by ID.

The invoice belongs to a different customer.

Why did authentication succeed but security fail? Where should the missing control live?

### Challenge 2 — The private bucket

An S3 bucket blocks public access. Only the Node.js application's IAM role can read its objects.

A user discovers that changing a document identifier allows the application to retrieve another tenant's document.

Is the bucket correctly secured? Which layer is failing?

### Challenge 3 — The SSRF problem

A backend imports images from user-provided URLs.

The developer allows only HTTPS addresses and blocks strings containing `localhost` or `127.0.0.1`.

Is that sufficient? What additional controls matter?

### Challenge 4 — The compromised dependency

A malicious npm dependency executes during a privileged CI build.

The workflow has permission to publish Docker images and deploy to production.

What are the attacker's possible opportunities, and how would you reduce their impact?

### Challenge 5 — The encryption argument

A colleague argues that tenant-level authorization is less important because all customer documents are encrypted in S3.

Explain why this reasoning is flawed.

---

## 16. Solutions and Discussion

### Challenge 1 — Authentication doesn't establish ownership

The JWT establishes an identity according to the application's authentication model.

It does not automatically authorize access to arbitrary invoice IDs.

The backend needs to evaluate whether the user may read the particular invoice, including tenant membership, role permissions, and any additional business restrictions.

This should be enforced in a trusted application boundary and supported by scoped data-access mechanisms.

A central authorization policy can reduce duplication, but sensitive operations still need reliable enforcement.

### Challenge 2 — Infrastructure permissions and tenant permissions differ

The private bucket may be correctly protected against public anonymous access.

However, the application possesses legitimate authority to read its contents and is using that authority on behalf of the wrong customer.

The failing boundary is application-level object authorization.

Narrower IAM permissions, separate prefixes or roles, and other infrastructure controls can reduce blast radius, but they don't necessarily replace user-specific authorization.

This illustrates why a secure infrastructure configuration cannot compensate for arbitrary business authorization defects.

### Challenge 3 — Basic URL filtering is bypass-prone

HTTPS does not establish that a destination is permitted.

Blocking a few textual representations of loopback addresses also ignores DNS resolution, redirects, alternative address representations, IPv6, and other network paths.

I'd prefer a narrow allowlist of known domains whenever the business allows it.

For arbitrary public destinations, I'd enforce a carefully designed destination policy at connection time, disable or validate redirects, restrict outbound networking, and limit download size and duration.

Cloud metadata protections and least-privilege workload credentials provide additional defense.

### Challenge 4 — The build pipeline is part of the trusted computing base

A malicious dependency executing with the build job's privileges may be able to read accessible credentials, alter generated artifacts, or influence deployment outputs.

If the job has broad deployment permissions, a dependency compromise can become a production compromise.

I'd separate unprivileged verification from privileged publishing and deployment, use narrowly scoped short-lived credentials, protect release environments, and review dependency and action provenance.

Artifact integrity checks and controlled promotion further reduce the likelihood of unauthorized code entering production.

### Challenge 5 — Encryption doesn't prevent authorized decryption from being misused

Encryption at rest protects data against certain unauthorized storage-access scenarios.

But the backend must decrypt or retrieve readable documents for legitimate users.

If its authorization logic incorrectly permits a user to access another tenant's document, encryption may operate exactly as intended while the application returns the plaintext.

The problem is not broken cryptography.

It is broken authorization.

The same distinction applies to HTTPS: an encrypted connection can securely deliver confidential information to the wrong person.

---

## Mental Model

When reviewing application and infrastructure security, ask:

1. **Assets:** What information, operations, and privileges must be protected?
2. **Identity:** How is the requesting actor authenticated?
3. **Authorization:** What may that actor do, to which resource, under which conditions?
4. **Trust boundaries:** Where does untrusted information enter a more privileged environment?
5. **Authority:** What can the application, container, IAM role, or CI pipeline do if compromised?
6. **Defense in depth:** Which independent controls reduce exposure and limit damage?
7. **Detection and response:** Can misuse be discovered, contained, investigated, and corrected?

**The central principle: Security is the disciplined control of authority across system boundaries—not a collection of reassuring technologies.**


---

## End of SE310

**SE310 — Web APIs, Identity, and Security** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

1. **OWASP — [Top 10: 2025](https://top10.owasp.org/)**. The current major web application risk categories, including broken access control, misconfiguration, software supply-chain failures, injection, and insecure design.

2. **OWASP — [API Security Top 10: 2023](https://owasp.org/API-Security/)**. API-specific threats, especially broken object-level authorization, unrestricted resource consumption, and SSRF.

3. **OWASP — [Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)**. A practical framework for analyzing assets, data flows, trust boundaries, and threats.

4. **OWASP — [SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)**. Defensive approaches to unsafe outbound requests, address validation, DNS rebinding, and cloud metadata exposure.

5. **AWS — [IAM Policy Evaluation Logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)**. How applicable identity, resource, permissions-boundary, session, and organizational policies combine to authorize requests.

6. **AWS — [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)**. Bucket policies, Block Public Access, encryption, and access controls.

7. **PostgreSQL — [Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)**. Database-enforced row-level restrictions and their important operational limitations.

8. **OWASP — [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)**. A more comprehensive set of application-security verification requirements than the high-level Top 10 lists.

9. **Ross Anderson — *Security Engineering***. A substantial investigation of security mechanisms, threat models, protocols, failure modes, and the economics of securing real systems.

---


