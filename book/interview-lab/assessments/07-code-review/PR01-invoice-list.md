# PR01 — The Invoice List That Almost Works

**Format:** 90-minute pull-request review / senior engineering discussion  
**Role archetype:** TypeScript/Node/SQL + React data-heavy product, backend-leaning or full-stack  
**Evidence:** fictional code-review assessment drawn from real-world requirements such as financial workflows, data exploration, production reliability. **Not a named employer's PR.**  
**Interviewer:** experienced teammate; asks for review comments ranked by risk, not a style critique.

## Part I — Candidate and interviewer packet

### 0–10 min — Opening

"Tell me how you review a change in a codebase you don't fully know. What do you read first? How do you distinguish a must-fix from a preference?"

### 10–22 min — Product requirement

Product asks for a "Paid amount" column on invoices, with filters, stable pagination and an expandable React row. A customer can pay a single invoice in multiple payments; adjustments may also be recorded independently. Invoice totals are in integer cents; payment rows are nonnegative captured amounts. The endpoint returns 25 invoices per page within one authorized workspace. The legacy endpoint already checks whether the current user can read invoices for that workspace.

The PR author claims: "Fast query, handles partial payments, straightforward pagination. Snapshot tests green."

**Expected review style:** State high-priority issues, reproduce mentally with a small dataset, and suggest proportionate fixes. You are not required to rewrite the whole module.

### 22–48 min — PR excerpts

~~~ts
// Server query (workspace authorization happens in middleware).
const sql = \`
  SELECT i.id, i.created_at, i.total_cents,
         SUM(p.amount_cents) AS paid_cents
  FROM invoices i
  LEFT JOIN payments p ON p.invoice_id = i.id
  LEFT JOIN invoice_adjustments a ON a.invoice_id = i.id
  WHERE i.workspace_id = $1
  GROUP BY i.id
  ORDER BY i.created_at DESC
  LIMIT 25 OFFSET $2
\`;
const rows = await pool.query(sql, [workspaceId, page * 25]);
return rows;
~~~

~~~tsx
function InvoiceList({ rows }: { rows: InvoiceRow[] }) {
  return (
    <ul>
      {rows.map((row, index) => (
        <InvoiceItem key={index} invoice={row} />
      ))}
    </ul>
  );
}

function InvoiceItem({ invoice }: { invoice: InvoiceRow }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li>
      <button onClick={() => setExpanded(v => !v)}>
        {invoice.id}: {invoice.paidCents / 100} EUR paid
      </button>
      {expanded && <InvoiceDetails invoiceId={invoice.id} />}
    </li>
  );
}
~~~

**Tasks:**
1. Review for *financial correctness*, pagination stability, frontend state identity, and user-visible meaning.
2. Which single SQL data example demonstrates a potentially serious arithmetic bug? Sketch two invoices, payments and adjustments and predict the bad result.
3. If paid_cents is NULL for an invoice with no payment, is it semantically the same as 0? How do you choose representation?
4. What data contract should the API expose about amounts and paging?
5. Write three review comments categorized blocking / important / follow-up.

### 48–65 min — Evidence from production-like testing

Reveal only when candidate reaches investigation:

~~~text
Invoices:
  I-101 created_at=10:00 total=10000 (cents)
  I-102 created_at=10:00 total= 5000 (cents)
Payments:
  I-101: P-1 amount=3000, P-2 amount=2000
  I-102: no rows
Adjustments:
  I-101: A-1 type=discount, A-2 type=manual_credit
  I-102: no rows
Observed API:
  I-101 paid_cents=10000; I-102 paid_cents=NULL
~~~

"Explain the numbers. Which fix addresses the correctness issue with the least blast radius? What's your plan for testing and for checking whether historic responses were incorrect?"

### 65–79 min — New constraint

"The product owner wants an export of all invoices and asks whether we can just allow a page=100000 query. A teammate suggests caching the endpoint for five minutes to fix performance. Another wants to switch to GraphQL."

Explore why OFFSET grows with page depth; deterministic tiebreaker when created_at ties; keyset/cursor pagination trade-offs; bounded export background job; caching privacy and freshness; framework/tool choice does not repair joins.

### 79–90 min — Communication and candidate questions

"Would you approve the PR as-is, request changes, or split it? Draft a concise review summary a teammate would actually want to receive." Reserve candidate questions.

---

# STOP — INTERVIEWER KEY / CODE REVIEW REFERENCE

## Main bug: join multiplication

For I-101, **two payments × two adjustments = four joined rows**. The SUM of payments becomes (3000+2000) × 2 = **10000 cents**, falsely indicating full payment when only 5000 cents were captured. The adjustments join contributes no selected columns, so it is suspicious and unnecessary for the shown feature. I-102 gets NULL because SQL SUM over no non-null payment values produces NULL. A single invoice's duplicates are not separate invoices; grouping by invoice ID does not undo join multiplication.

**Blocking correction:** For this feature, remove the adjustment join entirely if unused. Prefer preaggregated payments with one row per invoice when multiple one-to-many joins become necessary:

~~~sql
SELECT i.id, i.created_at, i.total_cents,
       COALESCE(p.paid_cents, 0) AS paid_cents
FROM invoices i
LEFT JOIN (
  SELECT invoice_id, SUM(amount_cents) AS paid_cents
  FROM payments
  GROUP BY invoice_id
) p ON p.invoice_id = i.id
WHERE i.workspace_id = $1
ORDER BY i.created_at DESC, i.id DESC
LIMIT 25 OFFSET $2;
~~~

This sketch is for query correctness, **not** a claim that it is optimal for large global payments tables. A production query may filter invoice IDs first or use a lateral/indexed aggregate; inspect EXPLAIN, data volume and indexes. Model pending/voided/refunded payments as the product contract requires; don't blindly sum every ledger row if real status semantics exist. The sample states nonnegative captured amounts.

## Other issues

- **Nondeterministic pagination:** created_at ties, and ORDER BY lacks a unique tiebreaker. Add ID. Offset pagination is functional for small shallow pages with stable dataset but degrades with deep offsets and can skip/duplicate records across concurrent inserts. Keyset cursor based on (created_at, id) is a reasonable alternative, not a universal requirement.
- **React identity:** index keys can attach expanded local state to the wrong invoice after reorder/insert/page change. Use stable \`row.id\`.
- **Money representation:** raw division and string concatenation lose localization and may yield awkward decimal rendering. Use a deliberate currency formatter and contract, with integer cents as source where applicable.
- **NULL semantics:** API must choose and document whether no payment means paid=0. COALESCE to zero is usually appropriate for total captured payments; do not treat unknown/missing *data availability* the same as confirmed zero when business semantics differ.
- **Contract and security:** workspace authorization is stated to exist in middleware, so do **not** invent an absent auth check. Verify all related detail endpoints enforce same boundary; invoices/exports can contain sensitive information. Return page/cursor metadata and stable sort behavior.

## Review priority and test evidence

Blocking: incorrect paid sum due join multiplication. Important: stable keys and pagination tie-breaker, correct handling of zero/NULL, readable currency. Follow-up: deep pagination/export design, load testing, index choices. Write review comments with a tiny reproduction and precise proposal, not "SQL is bad" or "Rewrite in GraphQL."

Tests: one invoice with 2 payments and 2 adjustments, invoice with zero payments, two tied timestamps, insert between page requests, filter by workspace, reordered React rows with one expanded, snapshot plus behavior/asserted money amounts, query plan on realistic cardinality.

The 100000th page OFFSET means walking/discarding a large number of records; avoid making it a synchronous export. Use a bounded background export and permission checks, with a durable status/result link. Five-minute caching may reduce repeated reads but can expose stale financial state and needs tenant isolation. GraphQL might change API flexibility, not fix SQL correctness.

**Rubric:** prioritize user-impacting arithmetic errors; reason from multiplicity, explain minimal correction, write collegial review comments and avoid unrequested abstractions. If candidate flags "SQL injection" here without evidence, ask them to point to the interpolated untrusted value: the shown SQL uses parameters, not raw input interpolation.

**Targeted refresh:** CS350-L01/L02, CS330-L02, SE250-L01, SE310-L01.
