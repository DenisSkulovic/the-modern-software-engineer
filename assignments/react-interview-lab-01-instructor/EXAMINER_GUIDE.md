# Confidential examiner guide

**DO NOT OPEN BEFORE/WHILE TAKING THE EXAM. Never share this directory with the candidate.**

RelayOps is a small React/TypeScript operations console with 270 deterministic tickets, three teams, six operators, an Express HTTP API and in-memory state. Candidate source and ZIP exclude these materials. The ZIP has one root directory and no dependencies, build output or Git internals. The local candidate directory has one baseline Git commit. When using an extracted ZIP, initialize Git and commit before starting.

The user explicitly authorized pushing this delivery to the existing study repository; that supersedes the handoff's older no-push instruction. Curriculum files are untouched. The original untracked `assignments/handoff.md` belongs to the user and is not part of this delivery commit.

## Session

Use a friendly practical full-stack interviewer, P1 European product-company context, Guided mode for learning unless the candidate requests a realistic simulation. They are an experienced engineer learning React; prioritize reasoning over API recall. This is fictional interview practice, not a claim about a real employer.

For 60 minutes: 0–8 explore and run tests; 8–20 reproduce and investigate; 20–43 focused fixes and regression checks; 43–53 discuss ownership and concurrency; 53–60 debrief and select a future task. For 90 minutes: 0–10 discovery; 10–50 debugging; 50–65 testing and discussion; 65–85 one small extension or its first slice; 85–90 debrief. Do not require all bugs and a whole feature within one session.

Baseline: installation, typecheck, build and ordinary startup succeed. The public suite has 27 tests: 26 pass and exactly one fails (`shows matching requests after narrowing a later queue page`). Do not fix that baseline before release. The four behavioral issues below are deliberate; syntax and setup failures are not. See `VALIDATION.md` for actual executed checks.

Before each reproduction run `npm run reset` while the API is running, then reload the page. Reload clears the module-level cache. Wait for `Queue ready`. Default team is Platform support with 90 records / nine pages. Default sort yields `ROP-1268` first. Fixture resets restore original values.

## A — filter/pagination state

Location: `client/src/App.tsx`, `filter`, which merges query changes without establishing a valid page for the new context. The backend deliberately returns an empty slice for a legal out-of-range page, not an error.

Reproduce: fresh page; Next twice (page 3); search `ROP-1001`. Result is `1 requests · Page 3 of 1` with an empty table. The ticket exists on page 1. Public React regression covers this actual App through MSW, asserting the matching request is visible without prescribing an implementation.

Accept resetting page on effective search/filter/team changes, or a carefully guarded correction based on returned page bounds. Discuss sort semantics. Fix all applicable contexts, not only the literal test. A naive effect may issue an extra invalid request or fight URL state later. Prefer atomic updates when appropriate. Verify the public test plus priority/status/team filters from later pages, no-match searches and normal next/previous navigation.

## B — query identity

Location: `client/src/hooks/useQueue.ts`, `load`, `key` serialization excludes `teamId`; requests themselves include it. The cache is populated only for completed reads. Request generations already guard older reads after a new query; that is separate from identity.

Reproduce: fresh load of Platform support page 1; select Billing operations without changing other controls. Team selector and summary change, rows still identify Platform support. Click Refresh, await completion; rows become Billing operations. If the key has not been cached, switching can work normally. Clear cache between diagnoses.

Accept a complete key derived from all material query parameters, or remove this small cache and justify the trade-off. A state-library migration is optional and usually excessive. Adding team only to effect dependencies is insufficient: the effect already executes. Verify both directions, two filter combinations and explicit refresh. Do not key by unstable object identity.

## C — draft synchronization

Location: `client/src/components/TicketDetail.tsx`, the effect copying `ticket.note` into local state for every replacement `ticket` object. `App.updated` sends confirmed status and assignment responses to the selected ticket too.

Reproduce: fresh queue, open first request; type a distinctive unsaved note; change Detail status to Triaged. The successful server response includes the unchanged canonical note and replaces the draft. Ordinary Save note does work.

Accept synchronization keyed to ticket identity with explicit save reconciliation, a dirty-state check or per-ticket draft ownership. Discuss switching tickets, closing the panel and server conflicts as product decisions. The detail is already keyed by ticket ID, so a new ticket remounts; preserving every draft forever is not required. Depending only on `ticket.note` helps unrelated updates but still loses drafts when a remote note changes. Removing every synchronization path without reconciling successful saves can leave false dirty indicators. Verify unsaved note across status/assignee/priority updates, explicit successful and failed saves, and switching tickets with documented semantics.

## D — read/mutation race

Locations: `server/app.ts` captures `store.list(q)` before the GET delay (1800 ms for explicit refresh); mutations confirm after 100 ms. `useQueue.replace` clears cached pages and maps a confirmed ticket into current data, but does not retire an in-flight read. `load` later overwrites the page. Backend state remains correct.

Reproduce: fresh default queue; note first row ID/status; click Refresh and immediately change that row to Triaged (choose New if already Triaged). Row first displays the confirmed update, then reverts when Refresh finishes. GET `/api/tickets/<id>` still reports the updated status. Another Refresh corrects the row. Displayed rows intentionally stay available during refresh.

Accept mutation-aware generations plus correct settling of loading and authoritative revalidation, version-aware merges or a coherent cache lifecycle. Simply aborting a request is insufficient if completion can still apply. Incrementing generation alone without managing `loading` can leave the workspace stuck. Disabling all actions during reads avoids the demonstration but degrades the intended product workflow; ask for the trade-off. Correct the filtered membership and counts after mutations too, where relevant. Verify both request completion orders, a failed mutation, switching filters during a pending read, multiple confirmations and eventual canonical membership/order. No need for a distributed synchronization framework.

## Evaluation

Look for observable evidence before edits, named invariants, focused diffs, recognition of independent local/server state, controlled timing tests and explicit product decisions. Recognize a partial but correct diagnosis. Weak signals include changing hooks at random, blanket memoization, deleting tests, making the server lie about pages, suppressing errors, or a large state-library rewrite without an ownership model.

Release only one future task once the candidate has understood the current issue. With limited time, choose F01's URL slice or F05. Never automatically write the candidate's patch. Support genuine setup problems promptly. Use the hint ladder one level at a time.
