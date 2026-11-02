# DB01 — Wrong Customer, Wrong Results

**Format:** 90-minute live debugging / code-forensics conversation, optional edits in an editor  
**Role archetype:** senior React + Node/TypeScript full-stack; B2B multi-tenancy, e-commerce/enterprise UI  
**Evidence:** simulated debugging round, modeled on job-relevant React/Node + production-quality responsibilities; **not a claimed employer assessment**.  
**Interviewer:** practical senior full-stack developer; helps with unfamiliar syntax, expects causal reasoning.  
**Allowed:** reading code, writing minimal pseudo-patches/tests, ordinary documentation by agreement; no hidden running repository.

## Part I — Candidate packet

### 0–8 min — Opening and context

"How do you usually investigate a production UI defect when you don't yet know whether it's frontend, backend, or infrastructure? Have you worked with an analogous issue?"

**Problem:** A B2B order dashboard sometimes shows results from another selected company after the user switches companies without logging out. On a separate occasion, a newly confirmed order remained in the list of open orders until refresh. Customers can belong to multiple companies. The server has access checks on all tenant routes. Both incidents are serious, but don't assume one cause.

### 8–22 min — Reproduce and form hypotheses

Ask for the first 3 observations the candidate would seek. Offer these when requested:

- Request A for tenant **north** and status **open** returns two order rows, including N-17.
- Without refreshing the page, the user switches to tenant **south**. The UI still displays N-17 for 3 seconds, then sometimes continues displaying N-17.
- In an isolated browser session for tenant south, the first request returns S-09 in some runs and N-17 in others.
- Hard refresh appears to fix the issue intermittently. No specific browser extension is involved.

**Interviewer:** "Can this be *only* a React stale-closure bug? What evidence would let you distinguish client cache, network request, and server response?"

### 22–43 min — Read the actual code

The React page:

~~~tsx
type Status = "open" | "confirmed";
type Order = { id: string; tenantId: string; status: Status };

function OrdersPage({ tenantId, status }: {
  tenantId: string; status: Status
}) {
  const queryClient = useQueryClient();
  const orders = useQuery({
    queryKey: ["orders", status],
    queryFn: () => api.getOrders(tenantId, status),
  });

  async function confirm(id: string) {
    await api.confirmOrder(tenantId, id);
    await queryClient.invalidateQueries({ queryKey: ["orders", status] });
  }

  if (orders.isPending) return <p>Loading…</p>;
  if (orders.isError) return <p>Could not load orders</p>;

  return (
    <ul>
      {orders.data.map(o => (
        <li key={o.id}>
          {o.id}
          {o.status === "open" &&
            <button onClick={() => confirm(o.id)}>Confirm</button>}
        </li>
      ))}
    </ul>
  );
}
~~~

Backend service (Express-shaped pseudocode; DB calls are async and return all rows in a tenant/status):

~~~ts
app.get("/tenants/:tenantId/orders", authenticated, async (req, res) => {
  const { tenantId } = req.params;
  const status = String(req.query.status);
  await requireTenantMembership(req.user.id, tenantId);

  const key = "orders:" + status;
  const cached = await redis.get(key);
  if (cached) return res.json(JSON.parse(cached));

  const rows = await db.orders.findMany({ tenantId, status });
  await redis.set(key, JSON.stringify(rows), { EX: 30 });
  return res.json(rows);
});

app.post("/tenants/:tenantId/orders/:id/confirm",
  authenticated,
  async (req, res) => {
    const { tenantId, id } = req.params;
    await requireTenantMembership(req.user.id, tenantId);
    const updated = await db.orders.confirmIfOpen({ tenantId, id });
    if (!updated) return res.sendStatus(409);
    await redis.del("orders:" + tenantId + ":open");
    return res.status(200).json(updated);
  }
);
~~~

Tasks:
1. List **independent** defects or risks and rank by severity.
2. State what is *proven* by the code and what remains unknown.
3. Sketch the minimum viable patch in both layers; do not simply remove Redis and declare victory.
4. Are membership checks sufficient? What distinguishes membership from permission to confirm orders?
5. When does a 30-second TTL help, and when does it fail as a correctness policy?

### 43–60 min — New evidence and discriminating tests

Reveal this only after code analysis or reasonable request:

~~~text
10:41:02.100 GET /tenants/north/orders?status=open user=U3 200 cache=MISS key=orders:open rows=2
10:41:02.450 GET /tenants/south/orders?status=open user=U3 200 cache=HIT  key=orders:open rows=2
10:42:08.130 POST /tenants/south/orders/S-09/confirm user=U3 200
10:42:08.400 GET /tenants/south/orders?status=open user=U3 200 cache=HIT key=orders:open rows=2
~~~

"Is there now enough evidence to identify a server data-isolation defect? What about the frontend? Which production protections and rollback would you choose?"

Provide one test concept for **each**:
- Same authenticated user switching authorized tenants.
- Separate users with disjoint memberships.
- Confirm order then refresh open list.
- Cache eviction or warm cache with same status across tenants.

### 60–77 min — A hard but realistic follow-up

"Our front-end engineer changes the query key to include tenantId, and the customer reports improvement. The product manager wants to ship that fix alone today. What do you say?"

Then: "The Redis key is fixed, but two authorization roles exist: tenant viewer and order operator. Both pass requireTenantMembership. Should both confirm orders? What else must change?"

Additional optional twist: if the user logs out and logs in as a different account in the same tab, how should the query-client cache be isolated/cleared? A change in query key is not a security boundary.

### 77–90 min — Communication and candidate questions

"Explain the incident to the product manager in 60 seconds without saying 'React bug' or 'Redis bug' as if either exhausted the investigation. What will ship today and how will we know it worked?" Reserve final 5–8 minutes for candidate questions.

---

# STOP — INTERVIEWER KEY / REFERENCE DIAGNOSIS

## Core facts and severity

1. **Critical server-side cross-tenant cache collision:** cache key is keyed only by status, not tenant; after membership check the server serves another tenant's stored data. A legitimate user in one tenant can see another's data if the cache is warm, including users with disjoint memberships. This is a confidentiality defect, not merely a UX bug.
2. **Client query identity collision:** query key omits tenantId, so client cache can reuse results between two authorized tenant contexts. Fix even when server is repaired; the UI shouldn't reuse one tenant's response for another.
3. **Cache invalidation mismatch:** GET caches orders:open; POST deletes orders:<tenant>:open, which is never the key that GET uses. TTL can make stale data disappear eventually but won't meet immediate consistency for confirmed orders.
4. **Authorization granularity:** membership check is not necessarily permission for mutation. Enforce tenant + capability/role at the server and audit mutation.
5. **Secondary errors:** absent mutation pending/error UX; the 409 semantics should be mapped to a user-visible conflict and refetch; returning all rows without paging may become costly. These are not equally urgent as leakage.

## Minimal correction

~~~tsx
const orders = useQuery({
  queryKey: ["orders", tenantId, status],
  queryFn: () => api.getOrders(tenantId, status),
});
async function confirm(id: string) {
  await api.confirmOrder(tenantId, id);
  await queryClient.invalidateQueries({ queryKey: ["orders", tenantId] });
}
~~~

~~~ts
// Shared, carefully scoped key function:
const ordersKey = (tenantId: string, status: string) =>
  "orders:" + tenantId + ":" + status;

// GET: validate tenant and status; read/write ordersKey(tenantId, status).
// POST: require specific order-confirm capability, update tenant-bound row,
// then invalidate relevant cached views (at least 'open'; maybe 'confirmed').
// If cache failures matter, choose an explicit invalidation/reconciliation policy.
~~~

Use an explicit allowlist for status values and enforce server-side tenant scoping of DB operations; never trust client tenantId alone. On rollout, **disable and purge unsafe cache namespace immediately**, then rebuild keys after tests. Corrected code still needs logs/metrics to determine any disclosure scope and an incident/privacy response per organization policy. A scoped key is necessary, not a substitute for authorization.

## Follow-up reasoning

The logs show a cache HIT for south on a north-populated status key: sufficient to diagnose the backend collision. A React-only fix is insufficient because an isolated browser session can receive the wrong JSON. Query invalidation on mutation must account for open/confirmed views and filters. Cache entries may be briefly stale because of race conditions; correctness-sensitive interactions should read from authoritative state or adopt versioning/invalidations. A 30s TTL limits lifetime, not visibility or security.

Good test plan exercises cross-tenant warm cache, authorized/unauthorized users, repeated switch, concurrent mutation, and role distinction at both API and UI. Validate via API/integration tests with a real test cache; a React component test alone cannot prove tenant isolation. Production containment precedes refactoring.

**Do not overpenalize:** Candidate may use plain state/effects instead of TanStack Query, or propose no response caching for sensitive data. Evaluate the ownership/security principles; if they propose removing Redis, ask about cost and whether that is a reasonable emergency containment rather than reject it outright.

**Debrief:** Distinguish knowledge of React query caches from backend privacy reasoning. Suggested refresher: SE250-L03, SE310-L02/L03, CS340-L06, SE440-L02.
