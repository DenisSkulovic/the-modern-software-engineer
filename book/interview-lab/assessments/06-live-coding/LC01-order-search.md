# LC01 — Search and Select Orders

**Format:** 90-minute technical round including a **50-minute pair-programming / live-case window**  
**Role archetype:** senior React + TypeScript full-stack, commerce/search-facing product team  
**Evidence:** fictional practical exercise; some employers describe a "live case" but neither this task nor its coding rules are claimed to be theirs.  
**Tool rules (agree before starting):**
- **Independent mode:** IDE, language/framework docs, no coding agent.
- **AI-permitted mode:** agent is allowed; candidate must justify output and identify edge cases.
- Neither mode is universally superior. Follow the invitation; do not invent its AI policy.
**Runtime:** React 19 + TypeScript, browser, testing-library-style tests (tool versions illustrative); dependency installation/build already works.

## Part I — Candidate-facing packet

### 0–8 min — Technical conversation

"Tell me about a UI feature where data fetching, responsiveness and correctness were in tension. What was hard, and what did you personally decide?"

### 8–20 min — Clarify task and plan

You are editing a small internal order-search screen. The backend already exposes:

~~~ts
type Status = "all" | "open" | "fulfilled";
type Order = {
  id: string;
  customerName: string;
  status: Exclude<Status, "all">;
  totalCents: number;
};

declare function searchOrders(input: {
  query: string;
  status: Status;
  signal?: AbortSignal;
}): Promise<Order[]>;
// The API may reject on network errors; it honors AbortSignal.
// Data can return out of order. A "query" filters customer name server-side.
~~~

**User story:** An operator enters a customer search term and selects a status. Matching orders appear. Clicking a row selects it for a detail sidebar. Fast changes must not display old results as current. Empty and failure states must be visible. This is a *small screen*, not a reusable company design system.

**Acceptance criteria:**
1. Search term is controlled and visible; filter choices all/open/fulfilled are available.
2. Results match the **latest** query and filter, regardless of network completion order.
3. Loading, error, empty and populated states are distinguishable.
4. Each order row uses a stable ID key, is accessible as an interactive control, and calls `onSelect(order.id)`.
5. Currency output uses the provided `formatCents` helper; never do raw concatenation that loses cents.
6. A quick first pass is acceptable; explain trade-offs before adding abstractions.
7. Write at least one test or narrate a deterministic test of request race/error handling.

**Starter code** — deliberately incomplete:

~~~tsx
type Props = { onSelect(id: string): void };

function formatCents(n: number) {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "EUR",
  }).format(n / 100);
}

export function OrderSearch({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("all");
  const [rows, setRows] = useState<Order[]>([]);

  return (
    <section>
      <h2>Orders</h2>
      <label>
        Customer
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </label>
      {/* Add status filter, request lifecycle, result states and list. */}
    </section>
  );
}
~~~

**Candidate task:** Implement the smallest correct screen. You're not asked to create an API server, set up Vite, install TanStack Query or adopt Redux. You may use existing React hooks. Ask reasonable clarifying questions.

### 20–70 min — Pair programming

Interviewer watches and collaborates. They can ask:
- "What happens if the slower request finishes second?"
- "Would the older rows be shown under the new filter while loading?"
- "How will errors surface without a console-only failure?"
- "How would a user select the row with a keyboard?"
- "Why this component state arrangement rather than a global store?"
- "Could this request be expensive? Would debounce help?"
- "If you used AI, how do you know it didn't break cleanup?"

Do **not** introduce every follow-up if the candidate needs the whole time. Observe their incremental approach and whether they verify behavior.

### 70–82 min — Verify and extend

Ask the candidate to describe or implement one focused test: simulate two searches, resolve the second first and then the first; ensure the later state remains visible. If their solution relies on abort, simulate an API that resolves despite cancellation and discuss stale-response guards. Ask whether selecting a row should persist through filter changes; accept either choice if specified.

### 82–90 min — Review and candidate questions

"What would you improve with another hour, what would you consciously leave alone, and where might a real production version need more design?" Leave room for candidate questions.

---

# STOP — INTERVIEWER REFERENCE (DO NOT SHOW DURING REALISTIC ROUND)

## One small correct baseline

~~~tsx
export function OrderSearch({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("all");
  const [rows, setRows] = useState<Order[]>([]);
  const [phase, setPhase] =
    useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setPhase("loading");
    setRows([]);

    searchOrders({ query, status, signal: controller.signal })
      .then(result => {
        if (!active) return;
        setRows(result);
        setPhase("success");
      })
      .catch(error => {
        if (!active || controller.signal.aborted) return;
        setPhase("error");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [query, status]);

  return (
    <section>
      <h2>Orders</h2>
      <label>
        Customer
        <input value={query}
          onChange={e => setQuery(e.target.value)} />
      </label>
      <label>
        Status
        <select value={status}
          onChange={e => setStatus(e.target.value as Status)}>
          <option value="all">All</option>
          <option value="open">Open</option>
          <option value="fulfilled">Fulfilled</option>
        </select>
      </label>

      {phase === "loading" && <p role="status">Loading orders…</p>}
      {phase === "error" && <p role="alert">Orders unavailable</p>}
      {phase === "success" && rows.length === 0 && <p>No orders found</p>}
      {phase === "success" && rows.length > 0 && (
        <ul>
          {rows.map(o => (
            <li key={o.id}>
              <button type="button" onClick={() => onSelect(o.id)}>
                {o.customerName} — {formatCents(o.totalCents)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
~~~

This deliberately makes a network call on each input change, without debounce. That is acceptable for a small exercise if the trade-off is discussed; a production UI might debounce, cache or reuse server-query infrastructure. The cleanup guards superseded responses and aborts supported requests. React development Strict Mode may exercise setup/cleanup more than once; the logic remains safe. The candidate may use a query library if present, but is not required to install one.

**Test principle:** Use deferred Promises or mock service worker. Change input A to B; settle B; verify B row; settle A; verify B row remains and A does not appear. Trigger a rejected latest request and assert a readable error. Avoid asserting exact effect run counts or internal hook implementations.

**Watch for:** No loading/error; uncontrolled input accidentally mixed with state; firing requests during render; shared mutable response variable; stale A overwrites B; index list keys; order total rendered as euros rather than cents; rendering untrusted HTML; button with no type inside a form. A candidate who asks a thoughtful clarifying question may be stronger than one who implements every optional feature silently.

**Scoring:** technical correctness, incremental delivery, state/effect comprehension, testability, collaboration, ability to explain. Typing speed is secondary; a coding agent's correct code is not evidence of understanding if the candidate cannot defend it.

**Targeted refresh:** SE250-L01–L04, SE250-L06, CS220-L02.
