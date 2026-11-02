# Assessment Authoring and Running Protocol

This adds reusable **interview scripts** to the existing [Interview Lab](../PROTOCOL.md); its evidence, candidate baseline, simulation modes, conduct rules, and 0–4 rubric remain authoritative.

## Four distinct layers

1. **Evidence:** employer JD / official hiring description (if known), otherwise broad industry inference. Put one line in every paper distinguishing these.
2. **Candidate brief:** everything a candidate is allowed to know at the start, including problem statement and tools.
3. **Interviewer script:** timetable and staged facts. Reveal follow-up evidence only when the candidate has reached that stage or asks an appropriate clarifying question. Do not force every branch.
4. **STOP / interviewer key:** explanations, potential fixes, discriminating evidence, red flags, evaluation and suggested drills. Never show before the candidate has finished in Realistic or Strict mode.

## Time budget and human behavior

A 90-minute session usually reserves 5–10 minutes for introductions and professional context, 50–65 minutes for one central technical topic, 10–15 minutes for extensions, and 5–10 minutes for candidate questions. A 60-minute peer conversation has a different allocation. Pacing is a script guide; neither ChatGPT nor a Markdown paper measures elapsed real time. Let conversations breathe; ask one question at a time.

**Interviewers are not answer dispensers.** If candidate requests missing information, provide a coherent fact from the packet; otherwise ask what they would measure or assume. If they choose a defensible alternative architecture, explore its consequences rather than punishing them for not matching the sample. Do not disclose hidden facts that would solve the exercise prematurely.

## What to evaluate

Use the existing 0–4 competency rubric, **with qualitative evidence** rather than a pass threshold. Weight per format:
- Conversation: actual ownership; concrete detail; learning; communication.
- Product case: framing the problem; scope control; contracts; cross-functional thinking; safe rollout.
- Debugging: reproduce; model hypotheses; discriminate with evidence; minimal correction; regressions.
- System design: requirements; data and identity; consistency; failure behavior; maintainability.
- AI-assisted: specification quality; detecting hallucinated assumptions; checking AI diffs; test plan and independent responsibility.
- Live coding: workable progression; correctness; tests; explanation; handling feedback.
- PR review: severity prioritization; data boundaries; compatibility; actionable comments and proportionate changes.

**Failure classification** after debrief: knowledge gap / mistaken model / execution gap / communication gap / relevant experience not demonstrated / correct but incomplete / alternative defensible choice. A weak React typing exercise is not evidence of weak Node architecture. No "probability of hire" or automatic fluency promotion.

## Format controls

- **Realistic:** one stage at a time, no answers/hints unless requested; debrief at end.
- **Guided:** prompt → answer → corrective feedback, then next.
- **Observe:** demonstrate both sides with believable questions and imperfect-but-effective answers.
- **Strict:** press on unsupported claims, never humiliate or invent gotcha requirements.
- **AI-permitted coding variant:** allow AI tools, but candidate must explain generated code, enumerate failure modes, and validate independently. Do not let the assistant itself claim to have executed tests unless tools did.

Use paper filenames and folders as stable IDs, not course lecture IDs; **do not add to curriculum.yaml** or log course-exam/lecture progress just because a paper was opened. Save actual mock reports only on request under ../sessions/.

## Candidate opening and logistics

Do not presume citizenship, relocation rights, English language level, compensation, production React mastery, specific personal incidents, or familiarity with an employer's internal stack. If asked about experience, candidate chooses a real example. Keep job descriptions public-safe and never place private application status or identifiable personal details into these papers.

## Quality control before adding a new paper

- The opening problem fits the target seniority and role.
- Code snippets are self-consistent, compile in principle or are explicitly pseudocode.
- Logs are timestamped and sufficient for at least two hypotheses, without fake proof.
- Candidate has genuine choices, not a hidden "right library".
- The answer key distinguishes cause from symptom and simulation facts from speculation.
- Total stages sum to stated time budget; there is room for questions at end.
- There is at least one concrete improvement and one realistic regression check.
- Avoid copy/paste tasks that depend on undisclosed repositories or external access.
- Company process claims are linked to dated/verified sources when possible; otherwise mark them unknown.
