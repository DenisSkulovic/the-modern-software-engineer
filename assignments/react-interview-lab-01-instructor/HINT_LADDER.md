# Confidential hint ladder

Give one hint at a time, tailored to the candidate's current evidence. First ask what they expected and observed. Do not name other issues while helping with one.

## A

1. What happens if you narrow the results after browsing further into the queue?
2. Compare the controls and the list request before and after the search.
3. The page number belongs to a particular result set; a new result set can have different bounds.
4. Inspect how `filter` combines changes with the current query. Which fields remain unchanged?
5. Reset or otherwise validate the page when the effective filtering context changes; update related query fields together. Cover every relevant context and retain normal pagination.

## B

1. Do the row labels agree with the selected team? Does refresh change the answer?
2. Compare whether a team switch issues a network request with what happens on refresh.
3. Cache entries must distinguish all inputs that can change their contents.
4. Compare the serialized key in `useQueue` with parameters sent by `api.list`.
5. Include `teamId` and all other material query fields in the key, or remove the cache with an explicit performance trade-off. Verify switching both directions with identical search/filter/page settings.

## C

1. What happens to a note you have not saved when you change another ticket field?
2. Trace the confirmed server object from the mutation back into the detail component.
3. A local draft and a server snapshot have different ownership and lifetimes.
4. Inspect the effect calling `setNote`. Does its dependency identify a ticket or every version of a ticket object?
5. Separate initialization on ticket change from reconciliation after successful saves. Preserve dirty drafts across unrelated updates; define what happens on real note conflicts and ticket switching. A keyed remount already handles identity changes.

## D

1. Try refreshing and immediately changing a visible status. What does the API say afterward?
2. Compare the completion order of list GET and PATCH requests in the Network panel.
3. A later response arrival does not imply a newer snapshot of canonical data.
4. Reads have generation guards. Does a confirmed mutation advance or invalidate that ordering? What data did GET capture?
5. Retire or reconcile pre-mutation reads and arrange authoritative refresh without dropping drafts or leaving loading stuck. Alternatively merge versioned entities. Test controlled response ordering and filter membership instead of relying on arbitrary delays.
