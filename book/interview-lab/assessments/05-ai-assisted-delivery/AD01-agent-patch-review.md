# AD01 — The Agent Built It. Would You Ship It?

**Format:** 90-minute specification-first + AI-generated implementation review  
**Role archetype:** senior full-stack product engineer on an AI-first SaaS team; TypeScript/React/Node, compliance/evidence workflows  
**Evidence:** a *simulated* AI-aware technical interview inspired by job descriptions mentioning spec-driven and agent-assisted development. It is not an announced assessment format at any named employer.  
**Tool policy:** the "AI output" is provided in the packet. Optional live AI assistance can be enabled by the interviewer, but the candidate owns all judgments; no code execution is presumed.  
**Interviewer:** product-minded tech lead, interested in what you wouldn't ship.

## Part I — Candidate packet

### 0–10 min — Real experience and product framing

"How do you personally use coding agents? Which technical decisions do you keep in your own hands? Tell me about a generated change you had to question or repair."

Then a fictional task:

> A B2B compliance SaaS allows customer admins to collect evidence documents for annual audits. Users may request an AI summary of a document. The summary must never be treated as a compliance approval, and a customer may have several isolated workspaces. Build an initial "Summarize evidence" workflow. A coding agent generated a proposed implementation.

Clarifications (give on request):
- Documents live in private object storage, and each belongs to a workspace.
- Large PDFs may take minutes to parse; user should see progress and failures.
- The LLM is an external provider, and some documents contain sensitive business information.
- The permission model distinguishes viewer, editor and audit-admin.
- V1 must support 500 requests/day and a hard per-workspace monthly budget; bursts are possible.
- The provider's output is untrusted. There is already a job table and worker capability.

### 10–25 min — Evaluate the *specification*, not code yet

**Draft ticket:**

> "Add a button that sends a PDF to AI, gets a summary, stores it, and marks the evidence checked. Make it fast and robust. All users can use the button if they can see the document. Use the most powerful model and retries."

Interviewer: "Rewrite this into a reviewable minimal engineering specification. What acceptance criteria and open questions would you raise before letting an agent implement it?"

Explicitly discuss: who may request, visibility boundary, whether sensitive data may go to the provider, what "checked" means, async lifecycle, retry/idempotency, cost guardrails, observability, bad outputs, customer-facing fallback, and test acceptance.

### 25–50 min — Review an agent-generated patch

The agent produced this abbreviated patch (fictional; illustrative TypeScript, not a runnable repository):

~~~ts
// POST /api/summarize — authenticated route
app.post("/api/summarize", requireLogin, async (req, res) => {
  const { workspaceId, documentId } = req.body;

  const doc = await documents.findById(documentId);
  if (!doc) return res.sendStatus(404);

  const pdf = await objectStorage.download(doc.storageKey);
  const ai = await llm.complete({
    model: "best-available",
    prompt: "Summarize and decide if compliant:\n" + pdf.toString("utf8"),
  });

  const result = JSON.parse(ai.text);
  await documents.update(documentId, {
    summary: result.summary,
    complianceStatus: result.approved ? "approved" : "rejected",
  });
  return res.json({ ok: true, result });
});
~~~

~~~tsx
function SummaryButton({ workspaceId, documentId }: {
  workspaceId: string; documentId: string
}) {
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState("");

  async function run() {
    setBusy(true);
    const r = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspaceId, documentId }),
    });
    const payload = await r.json();
    setSummary(payload.result.summary);
    setBusy(false);
  }

  return <>
    <button disabled={busy} onClick={run}>Summarize</button>
    <div>{summary}</div>
  </>;
}
~~~

The agent also states in its PR description: "Fully secure because the route requires login. All retries are safe because React disables the button. LLM approvals are accurate enough to automate compliance checks."

**Tasks:**
1. Give a **ranked** review: security/correctness first, then operability, UX, maintainability.
2. Identify which claims in the PR description are unproven or false.
3. Give three exact, actionable review comments that you'd leave.
4. Draw the smallest viable backend and frontend contract for an asynchronous version.
5. List which tests the coding agent should produce and which you would inspect personally.

### 50–68 min — Revised plan and generated-code verification

"How would you use an agent to implement the safer version *without* handing it an unbounded instruction like 'do it correctly'?"

Request a concise work plan:
- Contract + schema changes and acceptance criteria.
- Slice 1: authenticated request and job creation.
- Slice 2: worker with document parsing/LLM integration.
- Slice 3: read/status endpoint and React UI.
- Slice 4: integration tests, adversarial tests, cost accounting, monitoring.
- Explicit review checkpoints and stop/go conditions.

Then inject a real-world issue:

> During rollout one workspace generates 300 summaries in 10 minutes. The provider bill climbs sharply. Logs show many repeated requests with new HTTP connections. No requests appear to have reached "approved" state, but the external provider was called hundreds of times.

Ask how to contain loss, recover jobs, identify idempotency failures and attribute cost.

### 68–82 min — AI disagreement and trade-off

"The agent proposes saving time by removing the job table: just use a longer HTTP timeout and automatically retry three times. It also says the model can decide audit approval with a disclaimer. Are either acceptable for V1? Under what different conditions might a synchronous design be fine?"

The candidate should distinguish requirements and risks, not condemn all sync requests as inherently wrong.

### 82–90 min — Candidate questions and final pitch

"Explain your smaller, safer proposal to Product in under 90 seconds. What will users get now, what is deferred, and how will we measure quality?" Reserve final questions.

---

# STOP — INTERVIEWER KEY / REFERENCE REVIEW

## P0 and P1 issues in the supplied patch

- **Cross-workspace access risk:** \`workspaceId\` is user-controlled, never checked against the fetched document's owner, and there is no explicit workspace-level authorization. Login is not authorization. The server must load document by workspace/resource and enforce action permission.
- **Unapproved disclosure:** raw sensitive document content is transmitted to an external LLM without a defined provider/data contract, redaction policy, approval, retention rule or customer governance. Access controls and storage/security reviews are required.
- **Incorrect business truth:** a model's \`approved\` field directly overwrites authoritative compliance status; untrusted output becomes a decision that may carry audit consequences. Summary is advisory; human or deterministic workflow owns actual approval.
- **Broken input handling:** \`pdf.toString("utf8")\` is not PDF extraction; PDF binary content isn't plain text. Parsing, size limits, document type checks and malicious-content boundaries are necessary.
- **Reliability and cost:** long HTTP request, no timeout bounds, quota, idempotency key, admission control, queue durability, retry budget, or per-request cost accounting. UI button disable cannot protect across retries/tabs/network failures. Errors leave \`busy\` stuck and \`payload.result\` can be absent. Blind \`JSON.parse\` trusts arbitrary model output.
- **Operational insight:** no trace/audit linkage, job status, progress/error state, or distinction between "failed", "timed out after provider accepted" and "already running".

## Better minimum contract

~~~text
POST /workspaces/{workspaceId}/documents/{documentId}/summaries
  Authorization: canRequestSummary(document, workspace, user)
  Header: Idempotency-Key: client-defined stable key per user action
  -> 202 { jobId, status: "queued" } OR existing job reference
GET /workspaces/{workspaceId}/summary-jobs/{jobId}
  -> { status: queued|running|succeeded|failed, summary?, safeError? }
~~~

Enforce request uniqueness and quota admission atomically where feasible, persist job before external work, never charge the same logical operation twice silently, extract text safely, validate model output against a schema and content policy, and keep audit/compliance approval outside the LLM response. Think carefully about "external provider may have processed the request even if our response timed out": provider idempotency/cost may be limited, so retry policy should be bounded and duplicates monitored.

V1 UI polls or subscribes to job status, permits cancel only when meaningful, displays advisory summary with provenance and a visible unverified state; user can refresh/reopen without losing status. Server returns redacted, authorized data, never uncontrolled model text directly into dangerous HTML.

## Useful test plan

Cross-workspace document ID attack, viewer vs permitted requester, malformed and scanned PDF, >max size, LLM invalid JSON, prompt-injection text inside document, timeout after provider accepted, duplicate POST/idempotency, quota race, job restart, redacted logging, logout/switch workspace and inaccessible job, polling permission, and cost ledger reconciliation. Check integration tests beyond the mocks the agent claims are passing.

## What good AI engineering judgment sounds like

"I'll give the coding agent a narrowly testable contract and ask it to implement one vertical slice. I will review authorization and business truth boundaries personally, run/inspect tests, compare the diff with acceptance criteria, and require evidence for any 'secure/complete' claim. I may ask another model to critique the patch, but agreement between models is not verification."

## Rubric

Strong: translates vague ticket into spec, finds the most consequential bugs, balances security with shipping, scopes AI safely, supervises implementation and testing. Weak: reviews naming/style before tenant data leak, treats authentication as authorization, accepts model approval as fact, assumes retries are harmless, cannot account for cost.

**Refresher if needed:** SE310-L02/L03, SE320-L03, AI410-L06/L07, CS430-L05, SE250-L03.
