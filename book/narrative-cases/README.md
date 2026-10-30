# Engineering Stories — an audio-first learning library

**Why this exists:** A software engineer can know many individual mechanisms and still struggle to picture how they fit into working products and teams. Stories create memorable situations in which those mechanisms matter. They can also **teach an unfamiliar concept from zero**, without assuming a listener first completed a formal lecture.

Listen while walking, resting, commuting, or playing a low-focus game. These are optional narratives, not a new course, not mandatory homework, and not graded.

The files retain the original `NSNN` series and live together in `book/narrative-cases/` for stability. **Shelves are reading views, not separate folders or curriculum levels.** A story may fit more than one shelf, but the default primary shelf below helps navigation. No physical moves, lecture renames, or changes to `curriculum.yaml` are necessary.

## Choose a shelf

### Discovery — learn an unfamiliar technology or practice

These assume little prior knowledge of the central topic. The narrator teaches terms at the moment they become necessary, from practical purpose to core mechanics and limits.

| Story | What becomes understandable | Spoken time at ~125 wpm |
| --- | --- | ---: |
| [NS12 — The Infrastructure That Wasn't in the Code](NS12-the-infrastructure-that-wasnt-in-the-code.md) | Terraform, state, plan, drift, cloud identities, Terraform vs Kubernetes, rollout and cost | ~29 min |

### Focused — follow one discipline through a living product

A story may stay mostly within one field and go deeper than a panoramic story. Adjacent systems enter only when causally necessary.

| Story | Main focus | Spoken time at ~125 wpm |
| --- | --- | ---: |
| [NS05 — The Experiment That Won Twice](NS05-the-experiment-that-won-twice.md) | Product analytics, experiments, event identity, causality | ~29 min |
| [NS06 — The Monolith That Refused to Die](NS06-the-monolith-that-refused-to-die.md) | Software architecture, modularity, team boundaries, microservice trade-offs | ~30 min |
| [NS08 — The Image That Ate the Worker](NS08-the-image-that-ate-the-worker.md) | Async media processing, memory, queues, backpressure, security | ~29 min |
| [NS09 — The Search Result That Lied](NS09-the-search-result-that-lied.md) | Search projection consistency, data ownership, indexing, privacy | ~30 min |
| [NS11 — The Document That Kept Growing](NS11-the-document-that-kept-growing.md) | MongoDB document boundaries, query plans, indexes, atomic writes, schema migration | ~30 min |
| [NS13 — The Calendar That Remembered Yesterday](NS13-the-calendar-that-remembered-yesterday.md) | React state, identity, effects, query caches, optimistic updates and testing | ~30 min |

### Panoramic — see the whole company and system interact

These move across many responsibilities and technologies because the events require them, not because the author is counting courses.

| Story | World and journey | Spoken time at ~125 wpm |
| --- | --- | ---: |
| [NS01 — The Friday Checkout](NS01-the-friday-checkout.md) | Hotel booking: UX, network, data, payments, releases, ops | ~33 min |
| [NS02 — The Scan That Would Not Finish](NS02-the-scan-that-would-not-finish.md) | Security platform: workers, MongoDB, K8s, UI, ownership | ~33 min |
| [NS03 — The Assistant That Almost Sent the Email](NS03-the-assistant-that-almost-sent-the-email.md) | AI SaaS: retrieval, tools, authz, product, deployment | ~34 min |
| [NS04 — The Tuesday Cutover](NS04-the-tuesday-cutover.md) | Field-service release: schema compatibility, policy, QA, teamwork | ~30 min |
| [NS07 — The City That Woke Up Offline](NS07-the-city-that-woke-up-offline.md) | Transit outage: regions, DNS, replicas, availability, incident response | ~29 min |
| [NS10 — The Team That Inherited Friday](NS10-the-team-that-inherited-friday.md) | Inheriting SaaS: ownership, release identity, tests, modernization | ~29 min |

**Time estimates** are based on approximate spoken-word counts, not guaranteed TTS runtime. Playback at 1.5× is faster. Stories are standalone: pick by curiosity, not ID order.

## How to use the library

- **Unfamiliar subject?** Start with Discovery or a Focused story. Listen for why the tool exists, what it owns, where it fails, and how it connects to the work. Use the relevant lecture later if you need detailed mechanisms.
- **Feeling fragmented?** Start with Panoramic. Let the storyline reconnect teams, user needs, software components, and architecture decisions.
- **Preparing for interviews?** Try explaining one decision in the story out loud, then switch to a separate course exam or Interview Lab when you want actual pressure. You do not have to solve anything during a relaxed listening pass.
- **Low-energy day?** Just listen. A story remains useful when you don't pause to take notes or answer questions.

## Editorial protocol — version 2

**The central change:** interdisciplinarity is optional. **Depth is optional; accuracy is not.** A story can teach one unfamiliar technology for thirty minutes, or naturally cross ten courses. Do not insert tangential technologies to satisfy a quota. Choose a strong narrative question, then cover enough material to resolve it.

### Story shapes

1. **Discovery:** The protagonist or listener begins with little familiarity with the main topic. Introduce purpose, vocabulary, working mental model, operational constraints and one or two useful contrasts. Avoid requiring prior lectures.
2. **Focused:** One dominant discipline or set of tightly linked concepts persists across several events. Include real engineering reasoning and teach beyond a superficial overview. Other topics appear only when needed.
3. **Panoramic:** The narrative shows how product, people and systems interact. Keep a coherent causal plot, not a technology-rollcall.

These shapes are labels, not levels, genres, difficulty rankings, or folder hierarchies. A story may have one primary shelf and secondary themes. Keep existing `NSNN` IDs and file paths stable; introduce topics through catalogue tags rather than moving files into course folders.

### Writing requirements

- **Audience:** experienced full-stack developer reactivating professional knowledge, primarily for practical product-company engineering. No assumption of specialist expertise. A Discovery story must be understandable before its matching lecture.
- **Length:** ideally **3,700–5,000 spoken words** (roughly 30–40 minutes at ~125 wpm); use shorter lengths when the plot truly benefits. Report actual estimates. Do not pad with generic moralizing.
- **Story before syllabus:** begin with a person, product, ambition, symptom, decision or disagreement. Let concepts become necessary. An explanation may take a few paragraphs, but it should advance understanding of the situation rather than halt the plot for a mini textbook.
- **Characters with motives:** give 2–5 people recognizable, defensible responsibilities. A QA engineer, product manager, platform engineer and developer need not agree. Show trade-offs, collaboration, and the cost of decisions.
- **Mechanistic correctness:** distinguish observation, hypotheses, tests and confirmed findings. Avoid claiming one universal fix or a capability a tool does not guarantee. Explain unfamiliar terms the first time they matter and revisit them naturally if useful.
- **Multiple story types:** launches, product iterations, technical discovery, performance work, migrations, unexpected failures, organizational handovers, cost reviews and experiments are all valid. Not every story needs an incident response bridge.
- **Audio first:** cohesive prose, short meaningful act headings, sparse dialogue, no heavy tables/code fences in the narrated part, no references requiring a screen. Avoid narrated numbered lecture objectives, quiz sections, and repeated summary endings.
- **Fiction clearly marked:** fictional companies and events; no identifying real employers as sources of incidents. Times and figures are illustrative unless otherwise stated.
- **Behind the story:** end the audio with exactly `*The spoken story ends here.*`; only afterwards add optional metadata: primary shelf, prior knowledge, course/lecture touchpoints, caveats, at most three reflection prompts.
- **Learning progress:** a story listen is *not* a course lecture listen or an exam attempt. Do not create fake lecture activity or automatically promote learning phases. A separate optional narrative log is reasonable only if desired.

### Before creating the next NS story

Review this README and existing stories for repeated plots, read relevant actual lectures or course scopes, decide the shelf and primary educational promise, write a causal outline, and create a standalone narrative. Use next unused sequential `NSNN` ID. Update only this catalogue and the new story files; do not edit `curriculum.yaml` or lecture frontmatter. The old story files need no retroactive frontmatter migration.

**North star:** The listener should end with either *“Now I understand what this unfamiliar thing does”* or *“Now I can see how those familiar things form an actual working system.”* Both are equally valuable.
