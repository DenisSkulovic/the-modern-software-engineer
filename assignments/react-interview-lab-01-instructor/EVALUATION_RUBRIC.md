# Confidential learning rubric

Use 0–4 as descriptive anchors: 0 no evidence yet, 1 recognizes with substantial help, 2 partly independent, 3 independent and correct, 4 anticipates consequences and verifies alternatives. Do not average into a hiring verdict. Note hints used, exact observations, confidence and a useful next practice step.

| Dimension | Evidence to look for |
| --- | --- |
| Observation and reproduction | Stable steps, expected versus actual behavior, browser and API evidence |
| Hypotheses | Competing explanations, a small discriminating experiment, willingness to revise |
| React state/lifecycle | Ownership, render snapshots, identity and effects explained in context |
| Asynchronous correctness | Request start/completion order, canonical state, mutation boundaries |
| API and data ownership | Distinguishes HTTP correctness, query identity and local representation |
| Minimality and maintainability | Focused patch, readable names, product trade-offs, no needless framework |
| Testing | Behavioral regression with meaningful assertions and controlled timing |
| Communication | Clear reasoning, uncertainty stated, misconceptions corrected through evidence |
| Prioritization | Chooses high-impact correctness work; leaves a clear list of remaining risks |

A sound alternative solution gets full credit. Imperfect syntax is a smaller issue than incorrect ownership. Distinguish unfamiliar React syntax from a faulty mental model. Record partial understanding rather than reducing the whole session to how many defects were completed. Do not infer performance competence without measurement or interview success probabilities from this exercise.

Debrief with: one observed strength, one material misconception, one evidence-backed improvement, and one next task. Ask the candidate to explain their final invariant and how the test protects it. Do not mark curriculum lectures fluent automatically.
