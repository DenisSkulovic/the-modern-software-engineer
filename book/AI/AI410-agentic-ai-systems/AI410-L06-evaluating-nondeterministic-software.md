---
id: AI410-L06
course: AI410
title: "Evaluating Nondeterministic Software"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [AI501-S10]
prev: AI410-L05
next: AI410-L07
---









# AI410 — Agentic AI Systems and Production Engineering
## Lecture 06: Evaluating Nondeterministic Software

### The Model Upgrade That Made Everything Better—Except the Product

Imagine you're leading development of an AI customer-service platform.

Your existing assistant handles hotel reservation questions, interprets cancellation policies, retrieves booking details, and occasionally prepares actions for human approval.

The system works reasonably well, although it has known weaknesses.

Then your model provider releases a new model.

The benchmarks are impressive. It reasons more effectively, follows complicated instructions more accurately, and produces noticeably more polished responses.

Your team tests it with twenty customer conversations.

Everyone is delighted.

The responses are clearer, more empathetic, and better organized. The new model even catches a subtle ambiguity that the old model missed.

You deploy it.

Two weeks later, customer-support managers report an uncomfortable pattern: the assistant has begun interpreting questions about cancellation as actual cancellation requests.

Customers asking *"What would happen if I canceled?"* are being classified as wanting to cancel.

The application hasn't executed unauthorized cancellations—the backend still enforces approval—but customers are receiving inappropriate cancellation quotes and confusing follow-up questions.

Meanwhile, operating costs have increased by 35%.

The model is better at standardized benchmarks. Its answers look better. Your developers prefer it.

Yet the actual product has become less reliable and more expensive.

How can both things be true?

Because **model capability and application quality are different things**, and neither can be established by looking at a handful of impressive examples.

Traditional software engineering gives us tests, assertions, integration environments, coverage reports, performance benchmarks, and production monitoring.

But language-model applications introduce a peculiar challenge.

The same input can produce multiple acceptable outputs. Incorrect answers may be beautifully written. A result can satisfy its JSON Schema while violating the user's intention. And an agent can reach the correct final answer through a wildly inefficient or unsafe sequence of actions.

We need a systematic way to evaluate these systems.

Not merely to demonstrate what they can do.

But to establish, with defensible evidence, how reliably they accomplish a particular task.

Welcome to **evaluation engineering**.

---

## 1. Why Conventional Testing Isn't Quite Enough

Consider a deterministic TypeScript function:

```ts
function calculateRefund(
  paid: number,
  penalty: number
): number {
  return Math.max(0, paid - penalty);
}
```

We can define exact expectations:

```ts
expect(calculateRefund(200, 50)).toBe(150);
expect(calculateRefund(100, 120)).toBe(0);
```

A test either passes or fails.

Now consider an LLM asked to explain why a customer received only €150 from a €200 payment.

Two valid responses might be:

> Your payment was €200, and a €50 cancellation penalty was deducted, leaving a refund of €150.

And:

> After the applicable €50 cancellation fee, the refundable amount is €150.

The wording differs, but both answers are correct.

A third response might say:

> Your refund is €150 because the hotel charges a 25% cancellation penalty.

Numerically, 25% of €200 is indeed €50.

But what if the hotel's policy specifies a fixed €50 charge rather than a percentage?

The answer contains the correct final amount while inventing the reasoning behind it.

A naïve test checking whether the response contains `"€150"` would pass.

This reveals three different properties:

**Structural correctness:** The response satisfies the expected format.

**Semantic correctness:** The response accurately represents the intended facts and requirements.

**Task success:** The system accomplishes the user's actual objective without violating important constraints.

These properties overlap, but none implies the others.

### What an evaluation actually is

An **evaluation**, usually shortened to *eval*, is a procedure for testing an AI system against specified criteria.

The simplest version has three components:

```text
Test input
    |
    v
System under evaluation
    |
    v
Observed output
    |
    v
Grader / evaluator
    |
    v
Measured result
```

The difficult part isn't running the model.

It's deciding what constitutes success and how to measure it reliably.

For deterministic tasks, exact assertions may work perfectly.

For ambiguous or subjective tasks, we need richer evaluation methods.

For multi-step agents, we may need to inspect both the final result and the actions taken to produce it.

The central objective remains familiar from ordinary testing:

**Make important failures observable before they reach production.**

---

## 2. Start With a Quality Contract, Not a Benchmark

Suppose your team wants to evaluate a hotel customer-service assistant.

The first instinct might be to measure how often the model provides a correct answer.

But "correct" is insufficiently precise.

Consider a customer asking:

> Can I cancel my booking without losing money?

A successful interaction may require the assistant to:

1. Identify the relevant reservation.
2. Retrieve the applicable cancellation policy.
3. Determine whether the customer is asking a question or requesting an action.
4. Explain eligibility accurately.
5. Avoid modifying the booking without authorization.

These are different requirements.

An assistant might satisfy four while failing the fifth.

A single quality score can hide that distinction.

### Decompose the business outcome

For a reservation-support system, we might define:

| Dimension | What we measure |
|---|---|
| Intent accuracy | Did the assistant understand the request? |
| Factual correctness | Were booking and policy facts accurate? |
| Tool correctness | Were appropriate operations selected? |
| Authorization | Were permissions respected? |
| Action correctness | Did permitted mutations produce the expected state? |
| Communication | Was the response clear and complete? |
| Efficiency | How much time and money did completion require? |

Not every dimension should have equal importance.

An awkwardly worded but correct refund explanation is usually preferable to a beautifully written answer that promises money the customer isn't entitled to.

Likewise, unauthorized data disclosure shouldn't be compensated for by excellent grammar.

### Hard constraints versus optimization objectives

A useful distinction is between **hard constraints** and **soft quality objectives**.

Hard constraints might include:

- No unauthorized reservation modifications.
- No cross-tenant data disclosure.
- No refund exceeding the authorized amount.
- No false claim that an unconfirmed operation succeeded.

Soft objectives might include clarity, conciseness, empathy, latency, and cost.

The evaluation system should reflect this asymmetry.

For example, imagine a weighted quality score:

```text
Intent accuracy:       90%
Factual correctness:   94%
Communication quality: 98%
```

An average score of 94% sounds impressive.

But if the system executed an unauthorized payment operation, that average is irrelevant to the release decision.

Some failures must be treated as independently disqualifying.

**Define success in terms of the business operation, not merely the quality of generated language.**

---

## 3. Building an Evaluation Dataset

An evaluation needs test cases.

A dataset of prompts alone is insufficient if we don't know what acceptable outcomes look like.

Let's design a dataset for reservation-intent extraction.

A test case might look like:

```json
{
  "id": "cancel-question-017",
  "input": "What happens if I cancel my booking?",
  "expectedIntent": "general_question",
  "forbiddenActions": ["cancel_reservation"],
  "category": "hypothetical_question",
  "risk": "high"
}
```

Notice that we haven't specified the exact response text.

We specified the behavior that matters.

Another example:

```json
{
  "id": "conditional-change-022",
  "input": "Move my arrival to Friday only if it costs no more than another €100.",
  "expectedIntent": "modify_booking",
  "expectedMaximumAdditionalCost": 100,
  "requiresQuote": true,
  "category": "conditional_request",
  "risk": "medium"
}
```

This case checks more than classification.

It tests whether the model preserves the conditional nature of the request.

### Where should evaluation cases come from?

A useful dataset combines several sources.

**Real production examples** reveal what actual users ask, including unusual wording, incomplete sentences, and unexpected combinations of requirements.

**Historical incidents** preserve cases where the system previously failed.

**Synthetic examples** help cover scenarios that are rare, expensive, or dangerous to encounter in production.

**Expert-designed edge cases** target subtle business rules that ordinary users may not exercise frequently.

The balance depends on the product.

A dataset containing only synthetic, perfectly grammatical customer questions may seriously overestimate performance on real support messages.

But production data alone can underrepresent rare, high-impact failures.

### Stratify the dataset

Suppose 70% of customer messages are simple booking-status questions.

If we sample randomly, our dataset will mostly contain easy status lookups.

The model might score 95% overall while failing half of the complicated refund disputes.

A more useful dataset deliberately includes categories such as:

- Routine reservation questions.
- Cancellation inquiries.
- Explicit modification requests.
- Conditional instructions.
- Ambiguous dates.
- Contradictory customer messages.
- Missing reservation identifiers.
- Cross-tenant access attempts.
- Refund disputes.
- Unavailable external systems.

This is **stratified evaluation**.

It allows us to inspect performance across important subpopulations instead of collapsing everything into an average.

Two views are valuable: performance weighted by actual production frequency, and performance by risk or scenario category.

The first estimates typical operational outcomes.

The second exposes weaknesses that aggregate statistics might conceal.

### Separate development and holdout datasets

Suppose an engineer notices that the model fails this input:

> What happens if I cancel?

They modify the prompt until the example passes.

Then they add that exact example to the evaluation report and declare the new prompt superior.

That test is useful as a regression check.

But it is no longer independent evidence that the system generalizes to unseen cancellation questions.

Repeatedly optimizing against the same dataset creates a form of overfitting.

A practical approach maintains:

**Development set:** Cases engineers inspect and use to improve the system.

**Regression set:** Known failure cases that must remain fixed.

**Holdout set:** Cases reserved for less frequent, independent comparisons.

The separation need not resemble an elaborate academic machine-learning benchmark.

But a test set stops being a strong independent test when everybody has spent six weeks optimizing specifically for it.

---

## 4. Ground Truth Is Harder Than It Sounds

In conventional testing, we often assume the expected result is known.

In LLM applications, establishing that expectation can itself require expert judgment.

Consider:

> I might arrive Saturday instead of Friday. What are my options?

What is the correct intent?

Is it `modify_booking`, `general_question`, or `unclear`?

Reasonable reviewers might disagree.

The appropriate answer depends on how the application's intent categories are defined.

### Write annotation rules

A good evaluation dataset includes a clear interpretation policy.

For example:

> Classify a request as `modify_booking` only when the customer expresses an intention to change the booking, rather than merely requesting information about possible changes.

Under this rubric:

> Please move my arrival to Saturday.

is a modification request.

But:

> Would it be possible to arrive Saturday instead?

may be an inquiry requiring a quote or clarification rather than permission to modify immediately.

The exact taxonomy is an application decision.

What matters is that the evaluation reflects explicit business semantics.

### Human disagreement is useful information

If three qualified reviewers disagree on a case, don't automatically force a majority answer and forget the disagreement.

Investigate why the case is ambiguous.

Perhaps the intent categories overlap.

Perhaps the correct behavior is to ask for clarification.

Perhaps the test case genuinely allows multiple acceptable responses.

Some datasets should therefore specify acceptable outcomes rather than one exact answer.

For example:

```json
{
  "input": "Maybe I should move my stay.",
  "acceptableIntents": [
    "general_question",
    "unclear"
  ],
  "requiredBehavior": "ask_clarifying_question"
}
```

An evaluation rubric can also include graded criteria for partially correct responses.

The important principle is that **ground truth is a specification created by people, and that specification can itself contain errors or ambiguity**.

---

## 5. Deterministic Graders: Use Them Wherever Possible

Not every LLM evaluation requires another language model.

In fact, deterministic checks should usually be the first tools we reach for.

Suppose a model returns:

```json
{
  "intent": "cancel_booking",
  "reservationId": "res_123",
  "requiresApproval": true
}
```

We can validate its schema with Zod.

We can check whether the intent belongs to an allowed enum.

We can verify that a reservation identifier is associated with the authenticated customer.

We can inspect whether the application actually modified the database.

All of these can be checked without probabilistic grading.

### A small TypeScript grader

```ts
type Intent =
  | "create_booking"
  | "modify_booking"
  | "cancel_booking"
  | "general_question"
  | "unclear";

type EvalCase = {
  id: string;
  input: string;
  acceptableIntents: Intent[];
  forbiddenTools: string[];
};

type ObservedResult = {
  intent: Intent;
  toolCalls: {
    name: string;
    arguments: Record<string, unknown>;
  }[];
  response: string;
};

function grade(
  test: EvalCase,
  actual: ObservedResult
) {
  const intentCorrect =
    test.acceptableIntents.includes(actual.intent);

  const forbiddenCall =
    actual.toolCalls.some(call =>
      test.forbiddenTools.includes(call.name)
    );

  return {
    caseId: test.id,
    intentCorrect,
    toolPolicyPassed: !forbiddenCall,
    passed: intentCorrect && !forbiddenCall,
  };
}
```

This grader is intentionally narrow.

It can detect incorrect intent labels and forbidden tool attempts.

It cannot determine whether a free-form explanation is accurate or whether a selected tool's arguments are semantically correct.

That's fine.

A narrow, trustworthy grader is better than an elaborate grader claiming to evaluate things it cannot observe.

### Test the state, not only the transcript

For a mutating agent, the most reliable assertion may concern the environment after execution.

Suppose the user requests cancellation of reservation 123.

Instead of merely checking that the final response says "canceled," inspect the test database:

```ts
expect(
  await repository.getStatus("res_123")
).toBe("canceled");
```

Also check that no unrelated reservation changed.

For payment workflows, use a simulated provider and inspect the actual operations recorded by the simulation.

This is particularly powerful because it separates generated narration from real effects.

**When the environment provides an authoritative outcome, grade that outcome rather than the model's description of it.**

---

## 6. LLM-as-a-Judge: Useful, but Not an Oracle

Some evaluation tasks cannot be reduced to exact assertions.

Suppose an assistant must explain a complicated cancellation policy in plain English.

We want to assess whether its explanation is:

- Factually supported.
- Complete.
- Clear.
- Free of invented conditions.

A model can help evaluate those properties.

This is commonly called **LLM-as-a-judge**.

The evaluator receives the original question, the generated answer, relevant reference information, and an explicit grading rubric.

It returns a score or structured judgment.

### Design a narrow judging task

A weak instruction would be:

> Rate this answer from 1 to 10.

What does a 7 mean?

Does the judge reward friendliness, correctness, or length?

A better rubric might say:

```text
Evaluate whether the assistant's answer is supported
by the supplied cancellation-policy evidence.

Check:
1. Does the answer correctly identify eligibility?
2. Does it preserve relevant exceptions?
3. Does it invent fees, deadlines, or guarantees?
4. Does it acknowledge missing information?

Return:
- supported: true/false
- missingCriticalInformation: true/false
- unsupportedClaims: string[]
- explanation: string
```

Now the judge has a more defined responsibility.

It is not simply giving an aesthetic opinion about the response.

### Reference-based versus reference-free judging

A **reference-based judge** compares output against known evidence or expected results.

For example, it receives the authoritative cancellation policy.

A **reference-free judge** evaluates an answer without direct access to ground truth.

The second approach can be useful for readability, tone, or formatting.

But it is much less trustworthy for factual correctness.

Asking one language model whether another language model's obscure historical claim is true does not magically establish the fact.

The judge may share the same misconception.

### Common judge biases

Research has identified several problems with model-based evaluators.

Judges may favor polished language, particular answer lengths, or familiar response styles.

In pairwise comparisons, they may prefer the answer shown first or second, depending on the model and setup.

They can also be influenced by apparent authority, elaborate reasoning, or superficial signals that aren't genuinely related to correctness.

A wrong but eloquent explanation may outperform a concise, correct answer under a poorly designed judge.

This is especially dangerous when evaluating a model upgrade whose main visible improvement is fluency.

### Calibrate against human reviewers

A practical solution is to assemble a human-reviewed calibration set.

Run the judge on these cases.

Then examine:

- Agreement with expert judgments.
- False approvals of incorrect answers.
- False rejections of acceptable answers.
- Performance across scenario categories.
- Sensitivity to answer order and style.

You can also test pairwise judges in both answer orders.

However, simply averaging multiple biased judge outputs does not guarantee an unbiased conclusion.

The purpose of calibration is to understand what the grader can reliably measure.

**An evaluator is another software component whose correctness must be established.**

---

## 7. Retrieval Evaluations: Diagnose the Pipeline

RAG provides an excellent example of why we should evaluate components separately.

Suppose a hotel-policy assistant answers a refund question incorrectly.

There are several possibilities:

1. The correct policy wasn't indexed.
2. Retrieval failed to find the correct passage.
3. Context assembly omitted the relevant exception.
4. The model received the evidence but misinterpreted it.
5. The final answer was correct, but the citation was wrong.

A single end-to-end pass rate won't distinguish these failures.

### Retrieval metrics

We already examined Precision@k, Recall@k, MRR, and NDCG in AI310-L03.

For RAG evaluation, a particularly valuable metric is **evidence recall**.

Suppose a question requires two passages:

- The ordinary cancellation rule.
- An exception for supplier nonperformance.

If retrieval returns only the ordinary rule, the answer may become incorrect even though the retrieved text is highly relevant.

Evidence recall measures whether the necessary supporting information was retrieved.

For multi-part questions, complete evidence coverage may matter more than finding one loosely relevant document.

### Context assembly evaluation

The retrieval stage may return both passages, but the context assembler might discard the exception due to token limits.

Therefore, evaluate the final evidence actually supplied to the model.

Useful checks include:

- Did every required source survive?
- Were obsolete documents excluded?
- Were unauthorized documents filtered?
- Were contradictory versions handled appropriately?
- Was source attribution preserved?

These are not language-generation questions.

They concern the information pipeline.

### Generation evaluation

Once the correct evidence reaches the model, evaluate:

**Faithfulness:** Does the answer's factual content follow from the evidence?

**Answer correctness:** Does it satisfy the user question according to authoritative expectations?

**Citation support:** Do cited passages justify the attached claims?

**Abstention:** Does the model acknowledge insufficient evidence rather than fabricate an answer?

An answer can be faithful to retrieved evidence and still wrong if the evidence itself is obsolete.

Likewise, an answer can be factually correct while citing a passage that doesn't support it.

These metrics detect different failure classes.

### Oracle-context testing

One particularly useful technique is to bypass retrieval and supply the known-correct passages directly.

If generation now succeeds, the failure likely occurred upstream.

If generation still fails, investigate interpretation and answer construction.

This is the same diagnostic principle used in ordinary software testing: isolate components to identify which boundary introduces the defect.

---

## 8. Evaluating Agents: The Journey Matters

Now the problem becomes more interesting.

A conventional model evaluation might consist of one prompt and one answer.

An agent can perform dozens of actions.

Consider a coding agent assigned:

> Fix the failing authentication tests.

The final code passes all tests.

Success?

Possibly.

But suppose the agent also deleted unrelated files, disabled a security check, and rewrote the test suite so it no longer verifies authentication.

The final test command returns green.

The task was not completed correctly.

### Evaluate the environment

For coding agents, useful checks include:

- Does the project build?
- Do the relevant tests pass?
- Were required behaviors preserved?
- Were unrelated files modified?
- Were security-sensitive checks weakened?
- Does the implementation satisfy the actual specification?

Passing tests is strong evidence only when those tests meaningfully represent the requirements.

An agent that can edit both implementation and tests may accidentally or deliberately modify the measuring instrument.

This is why independent evaluation artifacts matter.

### Evaluate tool trajectories

A trajectory is the sequence of actions and observations produced during an agent run.

For example:

```text
1. Read reservation
2. Read payment history
3. Read cancellation policy
4. Calculate refund quote
5. Request human approval
6. Execute approved operation
7. Verify payment-provider result
```

A good evaluation can inspect whether these steps occurred appropriately.

But avoid requiring one exact sequence when several valid strategies exist.

An agent might retrieve the policy before payment history without harming correctness.

The objective is to enforce meaningful constraints, not arbitrary choreography.

### Invariants are more robust than exact traces

For a refund agent, important invariants might be:

- Customer ownership verified before disclosing payment details.
- Approval obtained before refund execution.
- Amount did not exceed authorized limits.
- No duplicate refund created.
- Final success message followed authoritative confirmation.

These allow flexibility in harmless investigative steps while enforcing correctness where it matters.

### Simulate external systems

A reliable agent test environment should not execute real payments or alter production reservations.

Use isolated databases and simulated external APIs.

A payment simulator can return:

- Success.
- Decline.
- Timeout after successful execution.
- Duplicate-operation response.
- Stale transaction status.

The evaluator then checks the resulting state and recorded calls.

This is more meaningful than asking a model whether the agent "handled the refund safely."

---

## 9. Statistical Uncertainty: How Much Evidence Is Enough?

Suppose Version A succeeds on 88 of 100 tests.

Version B succeeds on 92.

Is B better?

Perhaps.

But a four-percentage-point difference over 100 examples may reflect sampling variation, differences in test difficulty, or stochastic output behavior.

We need to distinguish measured outcomes from conclusions about broader reliability.

### A proportion is an estimate

Suppose a system succeeds on 90 of 100 independent, representative cases.

The observed success rate is:

**p̂ = 90 / 100 = 90%**

But the true success probability across the intended task distribution is unknown.

A rough standard error for a sample proportion is:

**SE ≈ √(p̂(1 − p̂) / n)**

For p̂ = 0.9 and n = 100:

**SE ≈ 0.03**

A rough normal-approximation 95% interval is approximately 90% ± 5.9 percentage points.

For formal reporting, methods such as the Wilson interval are generally preferable, particularly near 0% or 100% success.

The exact interval also depends on assumptions about sampling and independence.

The point is simple:

**A measured success rate is not an exact property of the system.**

### Repeated trials

LLM applications can produce different outcomes from the same input.

Therefore, evaluating every case once may fail to capture variability.

Suppose a difficult reservation question produces:

- Correct answer in seven trials.
- Incorrect answer in three trials.

A single successful run would conceal the instability.

Repeated trials help estimate success probability conditional on the case and configuration.

They are particularly valuable for tool selection, ambiguous interpretation, and agent trajectories.

But repeated trials over the same few examples don't substitute for a diverse dataset.

They estimate one dimension of variation, not the entire production task distribution.

### Paired comparisons

When comparing two model versions, evaluate them on the same cases.

Record where:

- Both succeed.
- Both fail.
- Only A succeeds.
- Only B succeeds.

The disagreements are especially informative.

If B fixes twenty of A's failures but introduces fifteen new failures, the net improvement is modest.

A paired analysis is generally more informative than comparing two unrelated samples.

Statistical techniques such as McNemar's test can analyze paired binary outcomes; paired bootstrap methods can help estimate uncertainty for more complex metrics.

The appropriate method depends on the data and experimental design.

### Rare failures require larger samples

Suppose a system produces zero unauthorized operations in 100 test runs.

Can we conclude that the unauthorized-operation probability is zero?

No.

Under independent Bernoulli-trial assumptions, a common approximation says that observing zero failures in n trials gives an upper 95% confidence bound of roughly **3/n**.

For 100 trials, that's approximately 3%.

For 10,000 trials, approximately 0.03%.

And even those bounds concern the tested distribution, not every possible adversarial input.

This illustrates why safety-critical invariants should be enforced by deterministic application controls rather than relying exclusively on empirical model reliability.

A model refusing 10,000 suspicious prompts is encouraging evidence.

It isn't a substitute for an authorization check.

---

## 10. Regression Testing: Making Quality Part of CI/CD

An evaluation suite becomes substantially more valuable when it's part of the development workflow.

Imagine changing a prompt to make customer responses shorter.

A developer sees improved readability.

But the change accidentally causes the model to omit refund exceptions.

Without regression testing, the defect may reach production unnoticed.

### A practical evaluation pipeline

```text
Code / prompt / model change
            |
            v
Deterministic unit tests
            |
            v
Structured-output checks
            |
            v
Small smoke evaluation
            |
            v
Full offline evaluation
            |
            v
Compare against baseline
            |
            v
Human review if required
            |
            v
Release decision
```

Not every commit needs to run thousands of expensive model calls.

A fast smoke suite can protect common workflows.

Larger evaluations may run before releases, during scheduled validation, or when model configurations change.

### Define release gates

Possible gates include:

**Hard invariant gate:** No observed unauthorized operations in the security suite, together with passing deterministic authorization tests.

**Task-quality gate:** Required accuracy thresholds across relevant categories.

**Regression gate:** No unacceptable deterioration from the baseline on important scenarios.

**Operational gate:** Latency and cost remain within budgets.

But beware of treating measured percentages as exact truths.

A 1% difference on a small dataset may not be meaningful.

Release thresholds should account for sample size, severity, and statistical uncertainty.

A high-risk regression may justify blocking release even if the overall accuracy improves.

### Avoid flaky evaluation bureaucracy

If the system is stochastic, a test may occasionally fail without any application change.

A CI pipeline that blocks randomly becomes frustrating and eventually gets ignored.

A better approach distinguishes:

- Deterministic contract violations.
- Stochastic quality measurements.
- Known unstable edge cases.
- Provider or infrastructure failures.

For probabilistic metrics, compare aggregate performance or use repeated trials where appropriate.

For hard constraints, build independent enforcement and tests wherever possible.

### Evaluation tooling in October 2026

The ecosystem evolves quickly, so avoid tying the methodology to one vendor's dashboard.

For example, OpenAI's legacy Evals platform is scheduled to become read-only on October 31, 2026, with shutdown planned for November 30, 2026.

A portable, code-first evaluation harness is therefore a sensible long-term foundation.

Tools such as **Promptfoo** and **LangSmith** provide workflows for maintaining datasets, comparing model or prompt variants, applying deterministic and model-based graders, and integrating evaluations into development or monitoring systems.

The important part isn't which dashboard you choose.

It's keeping your datasets, criteria, and experimental results reproducible and inspectable.

---

## 11. Online Evaluation: The Real World Is Different

Offline evaluations help us test expected scenarios.

Production introduces an entirely different distribution of inputs.

Customers use incomplete language, change their minds, mention unrelated details, and encounter business situations the test designers never anticipated.

A system can perform brilliantly on its evaluation dataset and fail on real traffic.

### Monitor business outcomes

For a customer-service agent, useful online metrics include:

- Verified resolution rate.
- Human escalation rate.
- Incorrect action rate.
- Reopened support cases.
- Repeat customer contacts.
- Customer corrections.
- Time to resolution.
- Cost per verified resolution.

Infrastructure metrics remain important, but they don't establish semantic quality.

A system can respond in 500 milliseconds with 99.99% uptime and still provide terrible advice.

### Beware misleading proxies

Suppose a new assistant asks fewer clarification questions.

That sounds like an improvement.

But perhaps it simply guesses instead of clarifying.

Likewise, a lower escalation rate can mean greater automation—or a system failing to escalate cases that require human review.

Metrics must be interpreted according to actual business outcomes.

For example, a refund dispute correctly escalated to a human may be a successful handling outcome, even though it wasn't autonomously resolved.

These categories should remain distinct.

### Online sampling and privacy

Reviewing production conversations can identify failures missing from offline tests.

But transcripts may contain personal information, payment references, or confidential business details.

Sampling and storage should respect appropriate privacy, access, and retention policies.

Avoid indiscriminately forwarding sensitive production data into external evaluation systems.

### A/B testing

For significant model or prompt changes, randomized experiments can provide stronger evidence than comparing one week against another.

Route eligible traffic between configurations A and B.

Measure verified business outcomes, latency, cost, and important error rates.

Randomization helps reduce the influence of changing traffic composition.

But an A/B test doesn't automatically solve problems such as delayed outcomes, user-level interference, or rare safety failures.

For example, customer-support resolution may not be known until several days later.

The experiment must define the observation window appropriately.

### Shadow testing and canaries

A safer rollout may run a candidate model in shadow mode, comparing outputs without allowing it to mutate production state.

This is especially useful for evaluating intent classification and decision proposals.

But shadow execution must not accidentally invoke mutating tools, send customer messages, or trigger expensive downstream operations without appropriate controls.

Once offline evidence is sufficient, a limited canary rollout can expose a small fraction of real traffic to the new configuration.

Expand only when the observed results justify it.

---

## 12. Practical Implementation: A Small Evaluation Harness

Let's create a provider-independent TypeScript evaluation harness.

The objective is to test an existing reservation assistant through its application boundary, rather than bypassing the surrounding logic and evaluating the model alone.

### Define the scenario

```ts
type Intent =
  | "cancel_booking"
  | "modify_booking"
  | "general_question"
  | "unclear";

type EvalCase = {
  id: string;
  category: string;
  input: string;
  expectedIntent: Intent;
  forbiddenTools: string[];
};

type AgentResult = {
  intent: Intent;
  toolCalls: string[];
  answer: string;
  latencyMs: number;
  estimatedCost: number;
};

interface SystemUnderTest {
  execute(input: string): Promise<AgentResult>;
}
```

For a production-quality harness, this contract would also include isolated fixture state, authoritative business outcomes, and execution traces.

Let's implement the basic grader.

```ts
type GradeResult = {
  caseId: string;
  intentPassed: boolean;
  toolSafetyPassed: boolean;
  passed: boolean;
  latencyMs: number;
  estimatedCost: number;
};

function gradeCase(
  test: EvalCase,
  result: AgentResult
): GradeResult {
  const intentPassed =
    result.intent === test.expectedIntent;

  const toolSafetyPassed =
    !result.toolCalls.some(tool =>
      test.forbiddenTools.includes(tool)
    );

  return {
    caseId: test.id,
    intentPassed,
    toolSafetyPassed,
    passed: intentPassed && toolSafetyPassed,
    latencyMs: result.latencyMs,
    estimatedCost: result.estimatedCost,
  };
}
```

Now run an evaluation dataset.

```ts
async function evaluate(
  system: SystemUnderTest,
  cases: EvalCase[]
): Promise<GradeResult[]> {
  const results: GradeResult[] = [];

  for (const test of cases) {
    const output = await system.execute(test.input);

    results.push(gradeCase(test, output));
  }

  return results;
}
```

This is intentionally sequential.

For a small evaluation suite, that makes execution easier to understand and avoids unexpected concurrency effects.

A larger harness might use bounded parallelism, but it must respect provider limits and isolate test state.

### Aggregate the results

```ts
function summarize(results: GradeResult[]) {
  const count = results.length;

  if (count === 0) {
    throw new Error("Empty evaluation dataset");
  }

  const passed = results.filter(r => r.passed).length;

  const totalCost = results.reduce(
    (sum, r) => sum + r.estimatedCost,
    0
  );

  const totalLatency = results.reduce(
    (sum, r) => sum + r.latencyMs,
    0
  );

  return {
    cases: count,
    passRate: passed / count,
    averageLatencyMs: totalLatency / count,
    totalCost,
    costPerPassingCase:
      passed > 0 ? totalCost / passed : null,
  };
}
```

The metric `costPerPassingCase` is useful for an evaluation experiment, but it shouldn't be confused with true production cost per resolved customer issue.

Real business cost may include retries, infrastructure, human review, and delayed corrections.

### What happens when the system throws?

Our minimal runner currently aborts if one scenario throws an exception.

A better implementation would capture the error as a failed trial with an explicit failure category.

You generally don't want to exclude failed requests from the denominator.

A model that succeeds on 95% of completed responses but times out on 20% of attempts is not a 95%-reliable application.

### Preserve the experimental configuration

Every evaluation run should record:

```text
Evaluation dataset version
Application commit
Prompt version
Model identifier
Generation parameters
Tool versions
Retrieval configuration
Run timestamp
Evaluation harness version
```

Otherwise, comparing historical scores becomes guesswork.

If the prompt changed, the model changed, and the retrieval index was rebuilt simultaneously, an improved score does not reveal which change caused the improvement.

This is why disciplined experiments change one major variable at a time whenever practical.

---

## 13. Case Study: Choosing Between Two Models

Suppose we're evaluating two configurations on 250 representative reservation-support cases.

The following results are hypothetical.

| Metric | Configuration A | Configuration B |
|---|---:|---:|
| Correct task outcomes | 218/250 | 229/250 |
| Intent accuracy | 92% | 95% |
| Correct tool selection | 90% | 94% |
| Unauthorized mutations | 0 | 0 |
| p95 latency | 2.4 s | 4.1 s |
| Mean inference cost/request | €0.004 | €0.011 |

Configuration B appears better in quality.

But it's slower and substantially more expensive.

Would I deploy it?

Not from this table alone.

First, I would inspect the eleven-case difference in successful task outcomes.

Which cases improved?

Did B fix high-risk refund disputes, or merely improve routine booking questions?

Did it introduce new regressions in categories where A was previously reliable?

Next, I would examine the uncertainty of the measured difference using paired results.

If B consistently improves important cases without introducing unacceptable regressions, the increase in cost may be justified.

If the benefit consists primarily of more polished explanations while core business correctness barely changes, I would be skeptical.

### Evaluate cost per successful task

Using only the illustrative inference costs:

Configuration A costs:

**250 × €0.004 = €1.00**

With 218 successful outcomes:

**€1.00 / 218 ≈ €0.0046 per success**

Configuration B costs:

**250 × €0.011 = €2.75**

With 229 successful outcomes:

**€2.75 / 229 ≈ €0.0120 per success**

B costs substantially more per successful task under this narrow model.

But perhaps B reduces human escalation or downstream support workload.

That could change the economics dramatically.

The correct decision depends on the full cost and business outcome, not merely inference pricing.

This case illustrates why evaluation is a product-engineering discipline rather than a model-ranking competition.

The goal is not to select the most impressive model.

It's to select the configuration that best satisfies the application's requirements.

---

## 14. Evaluation Anti-Patterns

Several mistakes appear repeatedly in AI development.

### Testing only impressive examples

Five successful demonstrations establish that the system can succeed.

They don't establish how often it succeeds or what causes failure.

### Exact string matching for open-ended answers

Two correct explanations may use different wording.

Evaluate semantic content where exact text is not the real requirement.

### Using a model judge without calibration

A judge that consistently rewards verbosity or confidence can make the wrong model appear superior.

Validate judges against trusted examples.

### Changing the test set until everything passes

Fixing known failures is useful, but continuously adapting the evaluation dataset to flatter the latest model destroys its independence.

Maintain holdout cases.

### Averaging away critical failures

A strong overall accuracy score doesn't excuse unauthorized operations, data leakage, or incorrect financial decisions.

Track hard constraints separately.

### Evaluating only the final answer

An agent may produce a correct summary after performing unauthorized actions or wasting enormous resources.

Inspect the execution trajectory and actual environment state.

### Ignoring failures and timeouts

Every attempted task belongs in the evaluation accounting.

Excluding incomplete runs creates survivorship bias.

### Optimizing a proxy instead of the outcome

Shorter responses, fewer tool calls, and lower escalation rates are not necessarily improvements.

They matter only insofar as they contribute to better business results.

---

## 15. Practical Lab: Build an Evaluation-Driven AI Service

This exercise ties together the previous nine sessions.

Use a reservation-support assistant built with TypeScript and a model API.

### Part A — Construct 60 evaluation scenarios

Create a dataset covering routine questions, cancellations, modifications, conditional requests, ambiguous language, missing data, and unauthorized access attempts.

Include historical failure cases and synthetic edge cases.

Keep at least ten cases as a holdout set.

### Part B — Define three grader layers

**Layer 1: Deterministic validation**

Check schemas, intent enums, required fields, tool permissions, and forbidden operations.

**Layer 2: Semantic evaluation**

Evaluate correctness against authoritative policy passages or expected interpretations.

Use human review and optionally a calibrated model judge.

**Layer 3: Business-state validation**

For mutating workflows, inspect the simulated database and external-provider records.

Check that intended state changes occurred and unintended changes did not.

### Part C — Compare two configurations

Choose two prompts or model configurations.

Run both against the same scenarios.

Repeat uncertain cases several times.

Record per-case results, not just aggregate percentages.

### Part D — Investigate disagreement

Identify cases where A passes and B fails, and vice versa.

Classify failures by root cause.

Was the problem context construction, interpretation, tool selection, authorization, or generation?

### Part E — Introduce an agent trajectory

Add a simulated cancellation workflow that retrieves a reservation, obtains a quote, and requires approval.

Create failure scenarios involving timeouts and uncertain external outcomes.

Evaluate the actual sequence of operations and final database state.

### Part F — Build a release gate

Make the evaluation executable from your CI pipeline.

Reject configurations that violate hard safety constraints.

For softer quality metrics, compare against a documented baseline using suitable uncertainty estimates.

Preserve the run's model, prompt, dataset, and application versions.

### Part G — Simulate production drift

Create twenty new customer messages representing a previously unseen class of questions.

Measure whether the old evaluation suite predicted the failures.

Add representative cases to the regression dataset, while preserving a separate holdout set.

The objective is to create a feedback loop:

**Production failures inform evaluations. Evaluations guide improvements. Improvements are validated before deployment.**

---

## 16. Engineering and Interview Challenges

### Challenge 1 — The benchmark victory

A new model scores substantially better on public reasoning benchmarks but performs worse on your reservation-support evaluation suite.

Which result should influence deployment?

### Challenge 2 — The perfect JSON

Your system returns schema-valid JSON on 100% of requests.

Does that establish reliable intent extraction?

### Challenge 3 — The judge who loves elegance

An LLM judge consistently prefers long, polished responses, even when they contain unsupported details.

How would you improve the evaluation?

### Challenge 4 — The 99% agent

An agent succeeds on 99 of 100 test cases.

The single failure involves issuing an unauthorized refund.

Would you release it?

### Challenge 5 — The apparent 3% improvement

Configuration A succeeds on 90% of 100 cases.

Configuration B succeeds on 93%.

The team announces that B is definitively superior.

What's wrong with that conclusion?

---

## 17. Solutions and Discussion

### Solution 1 — Application-specific evidence matters most

Public benchmarks measure useful aspects of model capability, but they don't necessarily represent your task distribution, business rules, tool environment, or operational requirements.

The reservation-support evaluation is more directly relevant to deployment.

However, verify that the evaluation dataset is representative and that the scoring process is trustworthy.

A model can be broadly more capable yet less suitable for a particular application.

### Solution 2 — Structure is not meaning

Schema validity establishes that the output satisfies supported structural constraints.

The model can still misunderstand the customer, extract the wrong amount, confuse a question with an instruction, or invent missing information.

Evaluate semantic interpretation and downstream business outcomes separately.

### Solution 3 — Calibrate and constrain the judge

Give the judge authoritative reference evidence and a rubric prioritizing factual support over style.

Create human-reviewed calibration examples containing polished but incorrect answers.

Inspect false approvals, test ordering effects for pairwise judgments, and separate communication quality from factual correctness.

Where deterministic checks are possible, use them rather than asking the judge to infer everything.

### Solution 4 — No, not without fixing the security boundary

A single unauthorized refund is a serious failure regardless of the aggregate success rate.

The appropriate response is to establish why backend authorization permitted the action and correct that enforcement failure.

The model should not possess authority to execute unauthorized financial operations even if it behaves correctly on most prompts.

After fixing the boundary, rerun relevant deterministic security tests and adversarial evaluations.

### Solution 5 — The difference may not be statistically meaningful

A three-percentage-point difference over 100 examples is insufficient to establish a confident improvement without further analysis.

Examine paired outcomes, uncertainty intervals, and the distribution of regressions.

Repeat stochastic trials where appropriate and expand representative coverage if the decision warrants it.

Also consider latency, cost, and failure severity.

**An improvement is a hypothesis until the evaluation provides enough evidence to support it.**

---

## Mental Model

An AI evaluation system turns vague expectations into measurable behavioral contracts.

Deterministic checks verify structure and invariants. Human and model-based grading assess semantic qualities. Retrieval evaluations isolate information failures, while agent evaluations examine both outcomes and execution trajectories.

Statistical methods establish how much confidence we should place in observed improvements, and production monitoring reveals failures our offline tests didn't anticipate.

**The goal of evaluation isn't to produce a high score. It's to produce credible evidence that the system accomplishes the right task, within the right constraints, consistently enough for its intended use.**


---

## Next Lecture — AI410-L07: Security, Reliability, and Economics of AI Systems

Continue in **AI410 — Agentic AI Systems and Production Engineering**.

## Further Reading

1. **Anthropic — Demystifying Evals for AI Agents (2026)**  
   An excellent practical treatment of agent evaluation, environments, graders, task design, human review, and production monitoring.  
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

2. **OpenAI — Evaluating Agent Workflows**  
   Official guidance on evaluating multi-step agent behavior using traces, graders, datasets, and systematic comparisons.  
   https://developers.openai.com/api/docs/guides/agent-evals

3. **OpenAI Cookbook — Optimizing Customer Support Agents for Cost and Quality (2026)**  
   A particularly relevant end-to-end example of evaluating support agents while optimizing prompts, tools, latency, and operating costs.  
   https://developers.openai.com/cookbook/examples/agent_optimization/optimizing_agents_for_cost_and_quality

4. **OpenAI Cookbook — Moving from OpenAI Evals to Promptfoo (2026)**  
   A practical migration guide emphasizing portable, code-first evaluations that can run locally or in CI.  
   https://developers.openai.com/cookbook/examples/evaluation/moving-from-openai-evals-to-promptfoo

5. **LangSmith — Evaluation Concepts and Types**  
   Documentation covering offline evaluation, online monitoring, deterministic graders, model judges, and pairwise comparisons.  
   https://docs.langchain.com/langsmith/evaluation-types

6. **Shi et al. — Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge (2024)**  
   Research illustrating why automated model judges require calibration and why evaluator behavior should not be assumed unbiased.  
   https://arxiv.org/abs/2406.07791

7. **OWASP — LLM Top 10**  
   A useful security reference for constructing adversarial evaluation scenarios involving injection, information disclosure, excessive agency, and unsafe integrations.  
   https://genai.owasp.org/llm-top-10/

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
AI410-L06  EVALUATING NONDETERMINISTIC SOFTWARE — INTERVIEW GLANCE CARD

WHY TESTS DIFFER
  Structure OK ≠ semantics OK ≠ task success under constraints
  Eval: make important failures observable before production

QUALITY CONTRACT FIRST
  Decompose business outcome; hard constraints vs soft optimization
  Success = business operation, not fluent language
  Public benchmark win ≠ product fit

DATASETS
  Real traffic / incidents / synthetic / expert edges; stratify categories
  Dev / regression / holdout separation; don't overfit the test set
  Ground truth is a human spec — can be ambiguous; disagreement informative

GRADERS
  Deterministic first (schema, authz, uniqueness, state)
  Grade environment state, not only transcript claims
  LLM-as-judge: narrow task; reference-based vs free; calibrate humans
  Biases (position, verbosity); judge is another component to validate

RAG / AGENTS
  Retrieval metrics + context coverage + faithfulness/correctness/citations
  Oracle-context isolates generation
  Agent: trajectories + invariants (must/must-not tools) + simulated externals

STATISTICS / CI
  Rate is estimate; SE≈√(p̂(1−p̂)/n); paired comparisons; rare fails need n
  Gates: hard invariants / task quality / regression / latency-cost
  Avoid flaky bureaucracy; tools (Promptfoo, LangSmith) hold harness, not truth

ONLINE
  Business outcomes; distrust vanity proxies; privacy in sampling
  A/B, shadow, canary; production failures feed eval suite

ANTI-PATTERNS
  Only impressive demos; exact string match; uncalibrated judge;
  edit tests until green; average away critical fails; ignore timeouts

SENIOR LINE: high score ≠ goal; credible evidence of right task under constraints.
```
