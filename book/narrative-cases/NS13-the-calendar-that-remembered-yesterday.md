# NS13 — The Calendar That Remembered Yesterday

*Focus: React's mental model, state ownership, effects, asynchronous data, and production frontend judgment. A story for experienced developers, including those coming from Vue.*

All characters, companies, and events are fictional. Technical behavior is based on ordinary React application patterns; implementation details vary by framework and version.

## Monday — The appointment that belonged to someone else

The first complaint at CommonHours sounded like a customer misunderstanding. A receptionist at a chain of dental clinics said the appointment calendar occasionally displayed information from the clinic she had been viewing *before* switching offices. The header showed Bristol, the appointments briefly showed Bath, and the Add Appointment button sometimes opened a form with the wrong clinic preselected.

CommonHours was a scheduling product for businesses with multiple locations. Its React frontend had grown from a compact single-clinic app into a complex workspace with permissions, calendars, reminders, invoicing, and patient administration. Ellie had worked mostly with Vue before joining the team. She understood reactive interfaces well enough, but the first React code review made her feel as if familiar concepts had been translated into a dialect with different habits.

She opened the component. Selecting a clinic changed a selected-clinic identifier in application state. A data-fetching effect loaded appointments. The calendar displayed the response. There was a `useEffect` dependency array, some `useState` variables, a context provider, and a component keyed by its position in a list. Every piece looked plausible. The bug survived every unit test.

“Start with what the user believes,” said Morgan, the senior frontend engineer. “They believe choosing Bristol has changed which clinic the page represents. Now ask which pieces of state are supposed to change with that choice.”

Ellie made a list without opening another file. The URL identified the selected clinic and visible week. The appointments came from the server and belonged to that clinic and week. The open dialog, typed notes, and temporary validation errors were local interface state. Permissions were linked to the current clinic and user. Some settings, like dark mode, were global. The app had treated these as one big mass of “state,” and that was the first source of confusion.

Morgan described React rendering in plain language. A component function calculates a description of the interface based on its inputs and state for that render. React can render again, compare descriptions, and commit changes to the screen. A new render is not the same thing as mounting a completely new component. A component's local state can persist as long as React considers it the same component at the same relevant position and identity.

Ellie thought of Vue's live reactive references. Morgan cautioned that React event handlers see the state snapshot associated with the render that created them. A handler scheduled today doesn't automatically acquire the latest values merely because some state changed later. That difference would matter before the week was over.

## Tuesday — Two requests that were both correct

They reproduced the clinic-switching bug by slowing network responses. Ellie selected Bath, then immediately Bristol. The Bristol request returned quickly and displayed the correct appointments. Half a second later, the older Bath response finished and overwrote the same state variable. The screen now contained Bath appointments under the Bristol header.

The backend had done nothing wrong. Each request asked a valid question and received the right answer. The frontend failed because it let an answer to an *obsolete question* become authoritative.

“Could we just add a delay?” Ellie asked.

“We could,” Morgan said, “but that would be a charming way to make a correct application feel slow while keeping the race condition.”

They considered several fixes. With a manual effect, they could ensure cleanup prevented an outdated request from updating state. In many situations they could cancel unnecessary network requests using an abort signal, but cancellation alone did not mean the server had never started working or that every async pathway could be canceled perfectly. A robust design needed to ensure only results relevant to the current selection were accepted.

Then Morgan showed her a server-state query library. Instead of one undifferentiated `appointments` variable, each request was associated with a key containing the clinic identifier and requested week. The result for Bath belonged to Bath's cache entry. The result for Bristol belonged to Bristol's. Stale work might still complete, but it no longer had to overwrite the displayed answer for a different identity.

The library also handled request deduplication, loading states, caching, and refetch rules. It did not make the data correct forever. A cached result could be stale. It did not replace backend authorization. But it separated *server state*, which was a local copy of remote truth, from interface state, which the component could legitimately own.

Ellie began to see the architecture more clearly. The selected clinic and week belonged in the URL because users needed to share and revisit the view. The current appointments belonged in a server-state cache keyed by those inputs. The form's unsaved text belonged to the form. The user profile belonged to session context. Every piece had an owner and a lifetime. “State management” was no longer the choice of one giant library versus another; it was the art of putting each fact where it belonged.

## Wednesday — Why did the form keep the old patient?

The older appointment data no longer appeared under the wrong clinic. Yet switching from one patient record to another sometimes left the previous patient's unsaved note in the editor.

Ellie expected new props to reset the editor. Morgan explained why they did not. The editor component still occupied the same identity in the rendered tree. React preserved its local state, because from React's perspective it was the same component receiving different inputs. That is often exactly what you want: typing into a form should not disappear just because a parent rendered again. But when the identity of the *thing being edited* changes, persistence may be wrong.

They debated two approaches. They could explicitly update local form state when the patient identity changed, with careful rules about unsaved edits. Or they could key the editor by the patient's stable identifier so React treated a different patient as a different component instance and reset state appropriately. Neither approach was universally correct. If the user had unsaved changes, a sudden reset could be destructive. They chose to warn the user before discarding an unfinished note and reset the editor when the switch was confirmed.

On the same afternoon, a junior engineer used array indexes as keys for appointment cards. When a cancellation caused the list to reorder, the wrong card appeared to retain a little expanded-state indicator. The cards weren't confused about dates; React was reusing component identity based on positions that no longer referred to the same appointment. Stable identifiers mattered because keys describe identity, not just satisfy a warning in the console.

The distinction reminded Ellie of the database discussion she'd heard in a different team. A patient's display name wasn't a stable identity, and neither was their position in a list. The UI had its own version of the same problem: give the system a durable way to recognize which thing is which.

## Thursday — The effect that wasn't an effect

CommonHours had a small panel showing the selected week's revenue. Every time an appointment was added, the panel refreshed. But sometimes it refreshed twice, and sometimes it refreshed repeatedly until the browser became sluggish.

The developer had put a calculation inside an effect: whenever appointments changed, compute a total and store it in state. The effect also depended on an object assembled during rendering, so its dependency looked different by reference on each render. The extra state update caused another render. The dependency appeared changed again. A loop formed.

Ellie had originally thought of effects as a generic place to put logic “after React is ready.” Morgan challenged that idea. Rendering should remain a calculation of what the interface ought to look like. If a total can be computed from the appointments already in memory, it usually doesn't need its own independent state or an effect to synchronize it. Derived values can be calculated during rendering, perhaps memoized later if measurement shows an expensive computation. Duplicating one fact as separate state creates a consistency problem: now the source and its copy can disagree.

Effects had a more specific job: synchronize React with something outside the render calculation, such as a network subscription, timer, or imperative browser API. Each effect established a synchronization responsibility and cleaned it up when its inputs changed or the component stopped participating. A correct effect should remain sensible under development checks that set up and clean up an effect more than once. Trying to suppress that behavior with a flag was often hiding a missing cleanup.

The team removed the unnecessary effect. The revenue total became a derived calculation. The repeated refresh disappeared. For the actual network subscription that watched appointment changes, they added cleanup and made sure reconnecting did not duplicate listeners. They stopped debating effects as a style preference and began describing the external system each effect was meant to synchronize.

At lunch, Ellie said the distinction made React feel less mystical. Morgan replied that frameworks are often at their most confusing when they provide several ways to store the same truth and a developer accidentally uses all of them.

## Thursday night — The reminder written in yesterday's voice

Just after the team celebrated the effect fix, an automated reminder appeared for the clinic Ellie had previously selected. She had switched to Bristol, but the on-screen reminder still mentioned Bath. This time there was no slow network response. The app had scheduled a timer while Bath was selected, and the timer callback remembered the value of `selectedClinic` from the render that created it.

Ellie stared at the callback. “But `selectedClinic` changed.”

“Yes,” Morgan said, “and the component rendered with a new value. The old callback didn't travel forward in time.”

They walked through it as if describing photographs. At one moment, React rendered a component with Bath selected. A callback was created with access to that render's variables. Later the user selected Bristol, causing another render with a new snapshot. The previously scheduled callback still referred to the earlier snapshot unless the code deliberately replaced it or read current information through a suitable mechanism. JavaScript closures were doing ordinary JavaScript things. React simply made the timing visible.

One suggested fix was to omit the clinic value from the effect's dependency list, so the timer would run only once. That didn't make the old value fresh; it institutionalized the bug. Another engineer proposed putting every changing value into a mutable ref. Refs could be appropriate for data that needed to survive renders without triggering display updates, such as an imperative handle or a mutable pointer. But using them as a secret substitute for state made the application harder to reason about.

For this reminder, the team decided that the scheduled timer belonged to the current clinic selection. The effect would create it with the relevant identity and clean up the previous timer when that identity changed. Where behavior truly required the latest value without resubscribing, they would use an approach that made that intention explicit. The point was not to memorize one magic hook. It was to decide whether the callback should represent the historical snapshot or the current state.

Ellie could now explain why the React dependency checker had seemed so annoyingly strict. It was trying to make synchronization assumptions visible. Sometimes it pointed to an architectural smell. Sometimes it exposed a plain bug. Silencing it did not make either one disappear.


## Friday — The save that succeeded but looked like failure

A dentist edited an appointment's duration. The interface updated immediately before the server responded. Then the server rejected the change because another staff member had already moved the appointment to a different room. The frontend rolled back the optimistic update, but the calendar displayed an older cached version that didn't match either person's intended result.

This was not primarily a React rendering bug. It was a question of authority and concurrency. The server had the final say about bookings and room conflicts. The client was allowed to show a temporary prediction, but it needed to reconcile with the authoritative result and explain conflicts instead of silently losing user input.

They revised the mutation workflow. An optimistic change could make the interface feel immediate, but failure had to restore an appropriate previous cache state or refetch from the source. On success, related views might need invalidation. A patient's appointment list, the room schedule, and the weekly totals all depended on the same underlying change. Invalidating only the currently visible page could leave a different tab displaying stale information; invalidating the entire application after every write would be correct in a crude sense but wasteful.

They listed the affected queries and documented the business entity behind them. The front-end cache key was not simply a performance trick. It expressed the identity of a question. Mutations changed facts that many questions depended upon. Correct cache invalidation required understanding those relationships.

On the backend, the team used a version or conditional update rule to reject stale edits rather than blindly accepting the last write. The frontend then had a meaningful conflict state to display. Neither layer could fix the whole problem alone. The browser knew what the user intended; the server knew which state changes were allowed; the interface had to bridge the disagreement honestly.

## Next Tuesday — The smoothest slow calendar in the world

The correctness bugs were improving, but performance reports remained awkward. Staff complained that typing into the patient search field felt sticky in large clinics. A teammate proposed wrapping every component in memoization and stabilizing every function reference.

Morgan wanted measurements first. They opened the React profiler and recorded one slow interaction. A text input changed, and an expensive calendar grid recalculated even though its data had not meaningfully changed. Some renders were normal and inexpensive. Others performed costly work. The total render count wasn't a performance metric by itself; the interaction delay and actual work mattered.

They moved local search-input state closer to the input. They avoided making a broad context provider value change on every keystroke. They made the expensive calendar data calculation more selective. Some memoization became useful afterward, because the expensive component could genuinely skip work when its inputs were stable. But they did not decorate the entire codebase with memo hooks out of fear.

Ellie learned why `useMemo` and `useCallback` were tools rather than architectural foundations. Memoization could avoid some repeated work, but it could also add complexity and obscure stale-closure mistakes. A function that never changes identity but captures yesterday's business state isn't an improvement. React's compiler and newer tooling could sometimes reduce manual optimization work, but no optimizer could decide whether the calendar was showing the correct clinic.

They considered deferred updates for expensive search results so typing remained responsive while the list caught up. That might improve perceived responsiveness, but it did not make the computation free or fix a slow server. They still needed to understand which work was urgent, which could lag, and which belonged somewhere other than the browser.

The performance fix ended up smaller than the proposed memoization campaign. An expensive computation moved behind a properly keyed query, a broad provider stopped changing unnecessarily, and the input stopped owning the whole calendar's render cycle.

## The test that couldn't see the right bug

Morgan asked the team to add regression tests before declaring the clinic-switching problem solved. The first proposal was to test the fetch helper in isolation. It returned valid appointments. The second was to snapshot the calendar markup. The snapshots passed even in the branch that reintroduced the race.

Ellie remembered the original user experience: select Bath, then Bristol quickly; delay Bath's response so it arrives last; ensure Bristol remains authoritative. A test that never varied response order couldn't exercise the failure. They built a component-level test with controlled responses and asserted the actual visible clinic and appointment rows. They also tested that switching patients handled unsaved form state correctly.

Another test covered the optimistic edit. The UI showed a provisional change; the server returned a conflict; the interface restored an authoritative state and told the user what happened. These tests did not need to inspect the internal naming of every hook. They described behavior that mattered to the person using the product.

A QA engineer added a browser-level scenario: switch clinics while an appointment request is slow, open an editor, and navigate back. The test was slower than the component test, but it covered routing, request integration, and the visible screen. They did not turn every test into a full-browser exercise. The different levels gave them complementary evidence: focused tests were fast and diagnostic; end-to-end tests helped discover mistakes in the boundaries between components and services.

There was also a small lesson about React's development behavior. An effect setting up twice in a development check did not necessarily mean production always duplicated the same work. But if a subscription leaked or a handler had uncontrolled side effects, those checks were providing a useful warning. The team fixed the underlying lifetime problem rather than writing tests that assumed every effect must run exactly once.

A few days later the regression tests caught an attempted “performance optimization” that reused a query cache entry across clinics. The code looked tidy; the tests knew the business identity mattered. That was the difference between testing implementation and testing the contract.


## A different morning — Server rendering enters the room

The sales team then asked for public clinic pages that search engines could discover. The authenticated dashboard was already a client-rendered application. Should the whole product move to a server-rendering framework?

Ellie expected a debate about which React architecture was fashionable. Instead, they divided the product by user needs. Public pages benefited from server-rendered or statically generated HTML and predictable discovery. The authenticated calendar was an interactive tool with complex local state; a client-heavy approach remained reasonable. They could mix delivery strategies rather than treat the entire company as one giant rendering decision.

The new public pages introduced another concept: hydration. Server-produced HTML could appear before the browser had finished attaching interactive behavior. The initial client render needed to agree with the server's output or the framework could warn about mismatches. Time-zone-specific text and browser-only state were easy ways to accidentally render different initial content on the server and client.

The team encountered exactly that when a clinic page displayed “appointments available today” according to the server's time zone. Some visitors across the world saw a different calendar day after hydration. The fix was not to silence the warning. It was to define what “today” meant for that clinic, serialize the appropriate date context, and avoid treating whichever machine happened to run the code as the authority on business time.

A useful frontend architecture, Ellie realized, was not one framework setting applied everywhere. It was a collection of ownership choices: where data came from, which location's time mattered, when the interface could be interactive, and what happened when the network or server disagreed.

## The component nobody was brave enough to split

After the incident fixes, the team reviewed a component called `CalendarWorkspace`. It fetched appointments, displayed a date picker, managed dialog state, interpreted access permissions, performed mutations, showed toast notifications, and calculated monthly revenue. It had not started as a monster. Each feature had been added by someone trying to help a customer by Friday.

A new hire proposed breaking it into twenty custom hooks immediately. Ellie asked what the boundaries would actually represent. A custom hook could reuse behavior, but it did not magically create one shared instance of state. Calling the same hook in two components generally created two separate sets of hook state unless the hook deliberately relied on an external shared store or context. Extraction could improve readability while preserving accidental coupling.

They chose a smaller redesign. The calendar view received a clear identity from URL state. A query layer owned appointment retrieval and caching. The editor owned unsaved form state and validation. Permission decisions remained in an appropriate authorization model rather than a collection of ad hoc button checks. Presentation components received enough information to display events without knowing how the server fetched them.

Ellie compared it to modular backend services. The point of separation wasn't the number of files. It was the cost of changing one concern without accidentally changing another. They kept the current component where it was small enough and split only areas where ownership had become ambiguous. They did not introduce a global state library just to make every prop disappear from sight.

By the end of the review, the codebase still had compromises. But future clinic-switching bugs would have fewer places to hide, because the team had made the identity of the view, the source of remote data, and the lifetime of local edits explicit. That was more valuable than obtaining a perfect architectural diagram from an AI assistant in thirty seconds.


## Three months later — The page that finally knew where it was

CommonHours still had bugs. Some were ordinary CSS mistakes. Some were backend problems. Some involved browser permissions, slow mobile devices, or customers keeping a tab open for a week. No architecture made those disappear. But the team now had a way to ask more precise questions.

When a clinic switch displayed stale appointments, they checked the query identity and request lifecycle. When a form remembered the wrong patient, they checked component identity and local-state lifetime. When derived totals went stale, they asked whether the app had copied a fact unnecessarily. When an effect looped, they asked which external system it was synchronizing. When a mutation raced another user, they distinguished the temporary client prediction from server authority. When rendering felt slow, they measured the actual interaction before memoizing anything.

Ellie remembered her first React code review and the strange sense that Vue intuition had deserted her. It hadn't. She had brought a good understanding of reactive applications, but React asked her to be particularly explicit about render snapshots, identity, and synchronization.

Morgan asked whether she finally liked React.

“I like knowing which parts are allowed to remember things,” she said.

It wasn't the answer he expected, but it was probably the best one.

The calendar had stopped remembering yesterday's clinic. More importantly, the team had learned to distinguish memory that served the user from memory that accidentally overruled the present.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Shelf:** Focused · **Primary discipline:** React/frontend state · **Starting knowledge:** Familiarity with component-based frontend development; React internals optional.

**Relevant lectures:** SE250-L01 (React rendering and identity), SE250-L02 (effects, closures, cleanup), SE250-L03 (state ownership and data fetching), SE250-L04 (performance), SE250-L05 (SPA/SSR/hydration), SE240-L02 (frontend architecture), SE240-L03 (reactive application state), SE310-L01 (frontend/backend contract).

**Technical caveats:** Cleanup strategies must match the async mechanism; aborting a request is not equivalent to rollback of work already processed by a server. React keys affect identity within a rendering context. Query libraries vary in invalidation and cancellation behavior. Optimistic updates must account for concurrent mutations and cache reconciliation. SSR approaches depend on the product and framework.

**Optional reflection:** Which information should be in the URL, local component state, or server-state cache? Why can two individually correct responses produce an incorrect screen? Why does reducing render count not automatically improve UX?
