---
id: AI410-L02
course: AI410
title: "Agents: From Model Calls to Autonomous Workflows"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [AI501-S06]
prev: AI410-L01
next: AI410-L03
---










# AI410 — Agentic AI Systems and Production Engineering
## Lecture 02: Agents: From Model Calls to Autonomous Workflows

### The Agent That Completed Nine Steps and Failed on the Tenth

Imagine an AI assistant working for a hotel reservation platform.

A support manager gives it the following task:

> Investigate yesterday's failed reservations, identify affected customers, determine which failures were caused by our system, and prepare appropriate remedies for review.

The assistant begins working.

It queries the reservation database, examines application logs, retrieves payment statuses, compares failure timestamps, and identifies several likely infrastructure problems.

It discovers that a payment provider experienced intermittent timeouts. Some reservations were successfully charged but never confirmed. Others failed before payment authorization.

The assistant prepares a list of affected customers and proposes refunds or reservation corrections.

Nine operations completed successfully.

Then, during the tenth operation, something goes wrong.

The assistant loses its execution context after a model request fails. Its process restarts.

Now what?

Should it begin the investigation again? Should it repeat the database queries? Does it remember which customers were already examined? What if it had sent an email just before the failure?

Worse, suppose it resumes and decides that the best next step is to refund every customer with a failed reservation—even though some reservations were never charged.

We have reached a fascinating boundary in software engineering.

We have built something capable of interpreting a broad objective, selecting tools, gathering information, adapting its approach, and making decisions across multiple steps.

But its autonomy creates new questions about correctness, termination, state, and control.

This is the territory of **AI agents**.

The surprising part is that the central technology behind them is not particularly mysterious.

At its heart, an agent can be built from a language model, a collection of tools, some state, and an execution loop.

The difficult part is deciding how much authority that loop should possess—and engineering the system so that an imperfect decision doesn't become an uncontrolled business operation.

---

## 1. What Actually Makes Something an Agent?

The technology industry uses the word *agent* rather loosely.

A chatbot that calls a weather API is sometimes called an agent. So is a coding system that edits an entire repository, runs tests, fixes failures, and opens a pull request.

These systems have different degrees of autonomy.

A useful engineering distinction is between **workflows** and **agents**.

In a conventional workflow, application code determines the sequence of operations.

```text id="pw51nk"
Receive document
       |
       v
Extract information with LLM
       |
       v
Validate fields
       |
       v
Save record
```

The model performs one step, but it doesn't decide what happens next.

An agentic system delegates some control-flow decisions to the model.

```text id="50obtv"
Receive objective
       |
       v
Model examines current situation
       |
       v
Model selects next action
       |
       v
Application executes action
       |
       v
Model observes result
       |
       +------> Continue working?
       |
       v
Finish
```

The central difference is not whether an LLM exists.

It is **who decides the next step**.

In an agentic system, the model can influence the sequence of actions based on the observations it receives.

This distinction isn't a rigid industry standard. Real systems occupy a spectrum, and different frameworks define agents differently.

For our purposes, we'll use a practical definition:

**An AI agent is a software system that uses a model to select actions toward an objective, observes their results, and can adapt subsequent actions based on those observations.**

This definition does not require consciousness, independent desires, or any other anthropomorphic explanation.

An agent is an application architecture.

### Autonomy exists on a spectrum

Consider four systems.

| System | What the model controls |
|---|---|
| Intent classifier | Produces a classification |
| Tool-using assistant | Selects a tool and arguments |
| Workflow with agentic decisions | Chooses among permitted branches |
| Autonomous task agent | Selects and sequences actions toward a broad objective |

The boundaries are not absolute.

A tool-using assistant that repeatedly selects tools may already qualify as an agent under some definitions.

What matters architecturally is the degree of freedom granted to the model.

The more decisions it controls, the more situations the application must handle.

Autonomy expands capability, but also increases the space of possible execution paths.

---

## 2. The Agent Loop: A Surprisingly Small Machine

Let's strip away the frameworks.

An agent needs several basic components:

1. An objective.
2. A model capable of selecting an action.
3. Tools or operations available to the model.
4. State describing what has happened.
5. An execution loop with stopping conditions.

The fundamental cycle is:

**Observe → Decide → Act → Observe again.**

Suppose the objective is:

> Find out why reservation 123 failed.

The model receives the objective and available tools.

It decides to call:

```text id="n60w1m"
get_reservation(123)
```

The application executes the call and returns:

```json id="qrpwwl"
{
  "reservationId": "123",
  "status": "failed",
  "paymentStatus": "authorized",
  "providerReference": "abc-918"
}
```

Now the model has new information.

It might request:

```text id="qep474"
get_payment_events("abc-918")
```

The returned events indicate that payment authorization succeeded but reservation confirmation timed out.

The model can then request application logs or inspect a relevant operational incident.

Eventually it concludes:

> The reservation appears to have failed during confirmation after payment authorization. The payment state should be reconciled before any retry or refund.

That is a simple agentic investigation.

The model doesn't merely answer from its original context. It gathers evidence through repeated interactions.

### A formal representation

We can describe an agent at step t using:

- **Sₜ:** Current application state.
- **Oₜ:** Latest observation.
- **Aₜ:** Selected action.
- **π:** The model-driven decision process.

Conceptually:

**Aₜ = π(Sₜ, Oₜ, Objective)**

After executing the action, the environment produces a new observation, and the application updates its state.

**Sₜ₊₁ = update(Sₜ, Aₜ, Oₜ₊₁)**

Then the loop repeats.

This resembles decision-making models studied in reinforcement learning and control theory.

We do not need to assume the agent is performing formal optimal planning.

The notation simply clarifies that an agent's next action depends on its objective and accumulated information.

### The loop has two different responsibilities

The model proposes the next step.

The application manages execution.

That second responsibility includes tool authorization, validation, resource limits, state persistence, and termination.

The model may decide that another database query would help, but it should not decide whether database access controls apply.

Those rules belong to trusted software.

This is the foundation of the entire architecture.

---

## 3. An Agent Is Not Necessarily a Planner

The word *agent* often evokes an elaborate planning process.

We imagine the model receiving an objective, constructing a ten-step plan, and executing it systematically.

But many useful agents operate without an explicit long-term plan.

Consider a coding assistant.

It receives:

> Fix the failing authentication tests.

It might inspect the test output, open the relevant source file, identify a likely bug, edit the implementation, and run the tests again.

Each decision depends on information acquired during the previous step.

The assistant might never create a complete plan in advance.

This is a form of iterative problem solving.

### Reactive agents

A reactive agent selects its next operation based primarily on current observations.

```text id="3iwx74"
Inspect error
     |
     v
Identify likely cause
     |
     v
Open relevant file
     |
     v
Modify implementation
     |
     v
Run test
     |
     +-- Failed --> Investigate again
     |
     v
Finish
```

This works well when feedback is informative and actions can be performed incrementally.

Software debugging is a natural example.

The environment tells the agent whether tests pass, which assertions fail, or which errors remain.

### Planning agents

Other tasks benefit from explicit planning.

Suppose the objective is:

> Analyze failed reservations across five hotel properties and prepare a remediation report.

The model might first identify subtasks:

- Retrieve reservation failures.
- Group failures by error category.
- Correlate payment events.
- Examine relevant deployment and infrastructure changes.
- Identify affected customers.
- Produce a report with supporting evidence.

A plan can reduce aimless exploration and help the system track progress.

However, the plan is not guaranteed to be correct.

The model might overlook an important dependency or misunderstand the business process.

### Plans should be revisable

Imagine the agent plans to investigate a payment outage.

After examining logs, it discovers that the actual problem was an internal database migration.

A rigid plan would continue gathering payment-provider information.

An adaptive agent should revise its approach.

This creates a useful distinction:

**Planning determines a provisional direction. Execution produces evidence that may justify changing that direction.**

A plan should guide the agent, not imprison it.

### Explicit plans aren't always worth the cost

Planning requires additional computation and introduces another output that may be incorrect.

For a two-step task, asking the model to create and evaluate a detailed plan is probably wasteful.

For a complicated investigation with many dependencies, explicit planning may improve coherence.

The appropriate question is whether planning measurably improves task completion, efficiency, or reliability.

Don't add a planning stage merely because an architecture diagram looks more impressive with one.

---

## 4. Building a Minimal Agent Runtime in TypeScript

Let's implement the essential mechanics without relying on a specific agent framework.

We'll use a provider-independent model interface so that the orchestration logic remains clear.

The example assumes tools already enforce the authorization principles discussed in AI410-L01.

### Define the decision contract

The model can choose one of three outcomes:

- Invoke a tool.
- Finish with an answer.
- Request clarification.

```ts id="udbfiq"
type AgentDecision =
  | {
      type: "tool_call";
      tool: string;
      arguments: unknown;
    }
  | {
      type: "finish";
      answer: string;
    }
  | {
      type: "clarify";
      question: string;
    };
```

This is more useful than allowing the model to return arbitrary text and hoping the application can infer what it intended.

Now define the information available to the agent.

```ts id="kcz7wp"
type Observation = {
  tool: string;
  result: unknown;
};

type AgentState = {
  objective: string;
  observations: Observation[];
  steps: number;
};

interface AgentModel {
  decide(state: AgentState): Promise<AgentDecision>;
}

interface ToolExecutor {
  execute(
    name: string,
    args: unknown
  ): Promise<unknown>;
}
```

The model adapter handles provider-specific messages, structured outputs, and model requests.

The tool executor handles application-specific operations.

### Implement the loop

```ts id="fbu8ec"
type AgentOutcome =
  | { status: "completed"; answer: string }
  | { status: "needs_input"; question: string }
  | { status: "limit_reached" };

async function runAgent(
  objective: string,
  model: AgentModel,
  tools: ToolExecutor
): Promise<AgentOutcome> {
  const state: AgentState = {
    objective,
    observations: [],
    steps: 0,
  };

  const MAX_STEPS = 8;

  while (state.steps < MAX_STEPS) {
    state.steps++;

    const decision = await model.decide(state);

    if (decision.type === "finish") {
      return {
        status: "completed",
        answer: decision.answer,
      };
    }

    if (decision.type === "clarify") {
      return {
        status: "needs_input",
        question: decision.question,
      };
    }

    const result = await tools.execute(
      decision.tool,
      decision.arguments
    );

    state.observations.push({
      tool: decision.tool,
      result,
    });
  }

  return { status: "limit_reached" };
}
```

This is a genuine elementary agent runtime.

The model decides what to do next, tools produce observations, and the application controls the loop.

However, the implementation is deliberately incomplete.

It doesn't persist state, handle timeouts, distinguish transient failures, enforce a total cost budget, or independently verify task completion.

The model also sees only accumulated observations, which may become excessively large.

These are not minor production details.

They determine whether the agent can operate reliably beyond a short demonstration.

### What happens when a tool fails?

In our implementation, a thrown exception terminates execution.

A more sophisticated runtime distinguishes failure categories.

If a search query returns no documents, the model might benefit from trying a different query.

If a reservation lookup fails because access is denied, the model should not be encouraged to circumvent authorization.

If the payment provider times out, the application may need reconciliation rather than another model decision.

Therefore, the tool execution layer should return structured outcomes and enforce retry policies.

Not every error belongs back in the agent loop.

---

## 5. The Hidden Complexity: State

Our minimal agent stores observations in an array.

That works until the process terminates.

Suppose the agent performs seven operations, then crashes.

The in-memory state disappears.

When the application restarts, the model doesn't automatically know what happened previously.

This brings us to a fundamental principle:

**An agent's operational state belongs to the application, not magically to the model.**

Some providers maintain conversation state or offer managed agent sessions. But even when conversation history is available, the application's authoritative workflow state is a separate concern.

### Conversation history is not execution state

Consider these facts:

> The assistant called the refund API.

> The refund API returned HTTP 200.

> The payment provider confirmed settlement.

> The customer received a notification.

These are different claims.

A conversation transcript may contain text describing them, but the application needs authoritative records establishing which events actually occurred.

For a durable workflow, useful state might include:

```ts id="dq1usg"
type AgentRunState = {
  runId: string;
  objective: string;
  status:
    | "running"
    | "waiting_for_input"
    | "completed"
    | "failed";

  currentStep: number;
  observations: Observation[];

  completedOperations: string[];
  pendingOperationId?: string;

  startedAt: string;
  updatedAt: string;
};
```

This still omits many practical fields, but it introduces the distinction between narrative context and persistent execution facts.

### Checkpointing

A checkpoint records enough state to resume execution after an interruption.

For example, after each successfully completed step, the application might persist:

```text id="1xkh7v"
Run: investigation-123
Step: 4
Completed:
- Retrieved failed reservations
- Grouped error categories
- Retrieved payment events
- Correlated provider timeouts

Next:
- Inspect application deployment history
```

When the worker restarts, it can recover the run and continue.

But checkpointing introduces an important complication.

Suppose an external email was sent, and the process crashed before the checkpoint recorded that fact.

On recovery, the system might attempt to send the email again.

The solution requires idempotency, durable operation records, or reconciliation.

A checkpoint alone does not create exactly-once execution across external systems.

We'll study agent memory and state in much greater detail in AI410-L03.

For now, remember that **conversation continuity, workflow recovery, and external side-effect correctness are three separate problems**.

---

## 6. Agents Versus Deterministic Workflows

This is probably the most important architectural decision in the session.

Imagine implementing a customer refund process.

The required business procedure is:

1. Authenticate the customer.
2. Retrieve the reservation.
3. Check whether a payment was collected.
4. Evaluate the applicable refund policy.
5. Calculate the refund.
6. Obtain approval if required.
7. Execute the refund.
8. Record the outcome.

Should an AI agent dynamically choose which of these steps to perform?

No compelling reason exists.

These operations are part of a known business process.

Allowing a model to skip, reorder, or reinterpret them introduces unnecessary uncertainty.

A conventional workflow is more appropriate.

### Where the model actually helps

Now imagine the customer writes:

> I booked that place in Berlin for the weekend after next, but my train got canceled, so I need to sort it out. I might still be able to arrive Saturday though.

The request is ambiguous.

Which reservation? Does the customer want cancellation, modification, or advice about options?

An LLM can interpret the language and identify missing information.

Once the intent becomes clear, deterministic orchestration can handle the business operation.

A sensible architecture is:

```text id="h8qztn"
Customer message
       |
       v
LLM interpretation
       |
       v
Structured intent
       |
       v
Deterministic business workflow
       |
       v
Authorized tools and validations
       |
       v
LLM explanation of result
```

This is an AI-powered application, but not necessarily a highly autonomous agent.

And that's perfectly fine.

The objective is building useful software, not maximizing the number of decisions delegated to an LLM.

### When autonomy becomes justified

Consider a different objective:

> Investigate why failed booking confirmations increased yesterday.

The exact diagnostic path isn't known in advance.

The relevant information might reside in deployment logs, database metrics, payment-provider events, or application traces.

The agent must decide where to investigate based on what it discovers.

A fixed workflow could gather all available telemetry every time, but that may be expensive and inefficient.

An agent can adaptively narrow the investigation.

This is a stronger use case for autonomy because the problem involves genuine uncertainty about which information is needed next.

### A useful decision rule

Before introducing an agent, ask:

**Can the correct sequence of operations be determined reliably in advance?**

If yes, prefer deterministic orchestration.

If no, ask whether a model can make useful decisions from intermediate observations and whether those decisions can be bounded and evaluated.

If the answer is also yes, an agent may be justified.

Autonomy is most useful when the path to the objective is uncertain, but progress can still be evaluated.

---

## 7. The Architectural Middle Ground: Agentic Workflows

The choice isn't simply between rigid code and complete autonomy.

Many effective applications combine deterministic structure with model-driven decisions.

### Routing

A model classifies a request and chooses among established workflows.

```text id="s55nd9"
Customer request
      |
      v
LLM classification
      |
      +--> Reservation inquiry
      |
      +--> Billing support
      |
      +--> Technical problem
      |
      +--> Human escalation
```

The model controls one branch selection.

The resulting workflow can remain deterministic.

### Prompt chaining

A complex task is decomposed into a fixed series of model-powered operations.

For example:

```text id="7yc4p0"
Extract claims
      |
      v
Verify against evidence
      |
      v
Generate explanation
      |
      v
Validate output
```

This is useful when different subtasks benefit from different prompts or models.

The application decides the order.

### Parallelization

Some independent operations can run concurrently.

Suppose a support request requires reading payment history and retrieving a cancellation policy.

Both sources can be queried simultaneously, reducing latency.

But parallelism introduces resource limits, dependency concerns, and possible conflicting observations.

Only genuinely independent operations should run concurrently.

### Evaluator–optimizer loops

A model generates an artifact, another evaluation process assesses it, and the application requests revisions when necessary.

For example:

```text id="jwu8p4"
Generate report
      |
      v
Evaluate against requirements
      |
      +-- Insufficient --> Revise
      |
      v
Accept
```

The evaluator may use deterministic checks, another model, or a combination.

This is useful when feedback is meaningful and revisions demonstrably improve quality.

It is not a guarantee of correctness. A model-based evaluator can make mistakes, and an unbounded revision loop can consume substantial resources without improving the result.

These patterns are widely discussed in practical agent engineering, including Anthropic's *Building Effective Agents* guidance.

They demonstrate an important principle:

**You can introduce model-driven flexibility at precisely the points where it adds value, rather than making the entire workflow autonomous.**

---

## 8. Termination: How Does an Agent Know It Is Finished?

Our minimal runtime allows the model to return:

```json id="z36y9q"
{
  "type": "finish",
  "answer": "The investigation is complete."
}
```

But what proves that the investigation is actually complete?

Nothing.

The model may stop prematurely.

It might overlook a relevant reservation, misunderstand a failed tool call, or declare success because its generated narrative sounds complete.

This creates a fundamental distinction between:

**Model-declared completion** and **verified task completion**.

### Explicit success criteria

Suppose the objective is:

> Investigate 50 failed reservations.

The application may require:

- Every reservation has an investigation outcome.
- Every outcome references supporting evidence.
- Payments marked successful have been reconciled.
- Uncertain cases are explicitly identified.
- No unauthorized mutation occurred.
- The final report includes all relevant reservation IDs.

These criteria can be checked independently of the model's final statement.

A useful completion contract might be:

```ts id="dh011z"
type InvestigationResult = {
  investigatedReservationIds: string[];
  findings: {
    reservationId: string;
    category: string;
    evidenceIds: string[];
  }[];
  unresolvedReservationIds: string[];
};
```

The application can compare this result against the authoritative set of affected reservations.

If the agent investigated only 43 of 50, it should not silently declare complete success.

### Multiple termination conditions

An agent runtime should distinguish:

- Successful completion.
- Insufficient information.
- User clarification required.
- Human approval required.
- Execution-budget exhaustion.
- Unrecoverable failure.
- Cancellation.

These outcomes have different business meanings.

A run that reached its maximum number of steps is not necessarily successful.

A run that requests human input isn't necessarily failed.

And a run that finished generating text may still have incomplete external operations.

### Independent verification

For some tasks, the application can verify completion deterministically.

For example, a coding agent can run tests. A data-processing agent can validate output schemas and required records. A reservation agent can query authoritative booking status.

For other tasks, evaluation is inherently more subjective.

A research assistant's report may be thorough but not exhaustively complete.

In those cases, the system should communicate its limitations rather than manufacture certainty.

**An agent's declaration that it has finished is an observation to validate, not a proof of success.**

---

## 9. Reliability: Small Errors Compound Across Long Trajectories

A single model call may be highly reliable for a narrowly defined task.

But an agent may make dozens of decisions.

Each decision introduces another opportunity for failure.

Consider a simplified model where each step independently has a 98% probability of being correct.

For a workflow requiring 12 correct steps, the probability that every step succeeds is:

**0.98¹² ≈ 78.5%**

The individual step accuracy sounds excellent.

The complete workflow reliability is considerably less impressive.

This calculation assumes independent failures and no recovery. Real systems violate those assumptions in both directions.

Errors can be correlated, making outcomes worse. Verification and recovery can correct mistakes, making outcomes better.

The exact probability isn't the point.

The architectural lesson is that **multi-step autonomy creates an accumulating reliability problem**.

### Early errors can redirect the entire investigation

Suppose an agent misinterprets a payment-provider timeout as a payment decline.

It then investigates declined cards, customer balances, and failed authorizations.

Each subsequent step may be internally sensible.

But the entire trajectory is based on a faulty premise.

The agent can produce a detailed, coherent report about the wrong problem.

This is particularly dangerous because a long sequence of successful tool calls creates an impression of rigor.

The execution may be technically flawless while the investigation's central assumption is incorrect.

### Verification checkpoints

A useful agent architecture introduces checks at important decision boundaries.

For example:

```text id="6bl1h6"
Collect payment evidence
       |
       v
Classify failure
       |
       v
Verify classification
       |
       v
Choose investigation branch
```

The verification step might compare the classification against authoritative payment states.

It need not involve another language model.

Often, deterministic validation is more reliable.

### Recovery versus prevention

Some mistakes should be prevented by business rules.

A refund exceeding the authorized amount must be blocked before execution.

Other mistakes can be detected and corrected afterward.

A coding agent can edit a file, run tests, discover a regression, and revise the implementation.

The cost of errors matters.

Autonomy is attractive when actions are observable, reversible, and cheap to retry.

It becomes riskier when actions have irreversible external consequences.

This is why coding agents operating in isolated development environments are often more suitable for extensive autonomous experimentation than agents directly modifying financial records.

---

## 10. Budgeting an Agent's Autonomy

One ordinary model request has a relatively understandable cost.

An agent can make an unpredictable number of requests.

Suppose each model interaction costs an average of €0.01.

A task requiring five calls might cost €0.05.

But if the agent becomes stuck in an investigation loop and performs 200 model calls, inference alone costs approximately €2.

Now multiply that by thousands of concurrent tasks.

The larger concern is that model-call cost isn't the only expense.

Agents can invoke paid APIs, run compute-intensive tools, perform searches, transfer data, and hold infrastructure resources.

### Budget across multiple dimensions

A production runtime may enforce:

```ts id="v5tlkk"
type AgentBudget = {
  maxModelCalls: number;
  maxToolCalls: number;
  maxExecutionMs: number;
  maxInputTokens: number;
  maxOutputTokens: number;
  maxEstimatedCostEur: number;
};
```

Each dimension limits a different failure mode.

A model-call limit doesn't prevent one enormous request.

A token budget doesn't prevent a tool from initiating an expensive cloud operation.

A time limit doesn't guarantee that external side effects can be safely interrupted.

Budgets therefore need to exist at the relevant execution boundaries.

### Progress matters more than activity

An agent can be extremely busy without accomplishing anything.

Imagine this sequence:

```text id="82ayc2"
Search logs
Search logs again
Search logs with different wording
Search logs again
Summarize partial findings
Search logs again
```

Each operation may be valid.

But the system could be repeatedly exploring the same information.

A useful runtime should detect repeated actions or lack of progress where feasible.

For example, it might maintain a record of normalized tool requests and results, identifying repeated searches that return equivalent evidence.

However, automatically blocking repeated operations requires care.

Repeating a query may be appropriate if external state has changed.

The goal is not to prohibit repetition.

It is to distinguish productive investigation from aimless looping.

---

## 11. Durable Execution and Human Intervention

Long-running agents frequently need to pause.

Perhaps the customer must clarify their request.

Perhaps a support manager must approve a refund.

Perhaps the system must wait for a payment provider to reconcile an uncertain transaction.

A simple synchronous loop is poorly suited to waiting for hours or days.

### Pausing is a workflow state

Consider:

```text id="q4mddj"
INVESTIGATING
      |
      v
REMEDY_PREPARED
      |
      v
WAITING_FOR_APPROVAL
      |
      v
APPROVED
      |
      v
EXECUTING
      |
      v
COMPLETED
```

The process should not remain alive merely to wait for a manager to click a button.

Instead, the application persists the state and resumes execution when the relevant event occurs.

This is familiar territory from durable background jobs and workflow orchestration.

### Agent frameworks and durable execution

Frameworks such as LangGraph provide graph-based workflow construction, persistence, interrupts, and resumption mechanisms.

OpenAI's Agents SDK manages model–tool loops, tool execution, handoffs, and related orchestration concerns. Managed agent runtimes can additionally provide hosted execution and persisted sessions.

These tools can reduce implementation effort, but their persistence semantics differ.

For example, checkpointing at node boundaries does not automatically guarantee that a side effect inside a partially executed node won't be repeated after recovery.

A payment operation still needs application-level idempotency.

An email-send operation still needs a strategy for uncertain outcomes.

A framework can remember where execution was supposed to continue.

It cannot repeal distributed-systems failure semantics.

### Human approval should preserve the original operation

Suppose an agent proposes refunding €180.

A manager approves the proposal.

During the waiting period, the underlying payment status changes.

The application must not simply tell the model:

> The manager said yes, continue.

It should resume a specific prepared operation, validate its current applicability, and enforce the approval's scope.

Otherwise, the model may reinterpret the approval as permission to perform a different action.

Human intervention is not just another conversational message.

It is an authorization event associated with a particular business operation.

---

## 12. Observability: Investigating the Investigator

An ordinary backend request might involve a few predictable service calls.

An agent run may involve an unfamiliar sequence of model decisions, tool requests, retries, and branches.

When something goes wrong, you need to reconstruct the trajectory.

A useful trace might look like:

```text id="4686fo"
Agent run: investigation-928
Objective: diagnose failed reservations

Step 1: Model decision
  → search_failed_reservations

Step 2: Tool execution
  → 47 reservations found

Step 3: Model decision
  → group_by_failure_reason

Step 4: Tool execution
  → 31 confirmation timeouts
  → 16 payment declines

Step 5: Model decision
  → inspect_payment_events

Step 6: Tool execution
  → 29 authorized payments
  → 2 unresolved states

Step 7: Model decision
  → inspect_deployment_history
...
```

Each step should contain appropriate identifiers, timestamps, statuses, and cost information.

### Logs, metrics, and traces

Conventional observability still applies.

**Logs** record meaningful events.

**Metrics** summarize behavior across many runs.

**Traces** show the sequence and dependency relationships within an individual execution.

Useful agent-specific metrics include:

- Model calls per completed task.
- Tool calls per task.
- Average and percentile execution latency.
- Cost per successful task.
- Percentage of runs requiring human intervention.
- Percentage terminated by limits.
- Duplicate or repeated tool-call rates.
- Verified task-completion rates.

A run that uses 30 model calls and completes successfully isn't necessarily better than one that uses five calls.

Efficiency matters.

### Evaluate trajectories, not just final answers

Suppose two agents produce identical investigation reports.

Agent A retrieved the necessary evidence, verified payment status, and stopped.

Agent B queried unrelated customer records, attempted three unauthorized operations, and eventually reached the same conclusion.

A final-answer comparison might treat them as equally successful.

Operationally, they are not remotely equivalent.

Agent evaluation must consider what actions were taken, whether they were appropriate, and whether the execution respected constraints.

We'll explore trajectory evaluation in AI410-L06.

For now, recognize that an agent's process is part of the product's behavior.

---

## 13. When an Agent Is Actually Worth Building

Let's consider several realistic applications.

### Coding assistants

Coding agents are among the strongest use cases for substantial autonomy.

They can inspect files, identify dependencies, modify code, run tests, and iterate based on feedback.

The environment provides relatively clear signals.

Tests pass or fail. Builds succeed or fail. Diffs can be reviewed.

When operating inside isolated workspaces with controlled permissions, many actions are reversible.

This creates favorable conditions for iterative model-driven work.

### Research assistants

Research tasks often require adaptive exploration.

A question may reveal several subquestions, which lead to new sources and further investigation.

An agent can choose search queries, inspect results, compare evidence, and refine its approach.

But verifying source quality and completeness remains difficult.

An impressive report may still omit important evidence.

### Customer-service workflows

Customer service contains both agent-friendly and deterministic tasks.

Interpreting complicated customer requests and locating relevant evidence can benefit from autonomy.

Issuing refunds, canceling bookings, or modifying payment details should remain tightly controlled by business workflows.

A hybrid architecture is usually preferable.

### Document-processing systems

If every document follows the same structure, a fixed extraction pipeline may be enough.

If documents vary dramatically and require different processing strategies—tables, scans, attachments, inconsistent formats—an agent may help select the appropriate tools and investigate extraction failures.

Again, the value comes from uncertainty in the process.

### The wrong reasons to use agents

Avoid introducing agents merely because:

- A model API supports tool calling.
- A framework makes orchestration easy.
- The company wants to advertise autonomous AI.
- A fixed workflow sounds insufficiently innovative.
- Someone saw an impressive demonstration.

A senior engineer should be able to explain precisely which decisions are delegated to the model and why deterministic code cannot handle them as effectively.

If that explanation is unclear, the agent architecture probably isn't justified yet.

---

## 14. Practical Lab: Build a Bounded Investigation Agent

We'll build a small agent that investigates simulated reservation failures.

The objective is not to maximize autonomy.

It is to observe how model-driven decisions interact with ordinary application constraints.

### Part A — Create a simulated environment

Prepare a dataset containing approximately 30 reservations.

Give them different failure conditions:

- Payment declined.
- Payment authorized, confirmation failed.
- Reservation created successfully.
- Provider timeout with unknown outcome.
- Duplicate reservation request.
- Invalid guest information.

Expose read-only tools:

```text id="8mrgon"
list_failed_reservations
get_reservation
get_payment_events
get_application_logs
get_deployment_history
```

The model should not have access to mutation tools.

### Part B — Implement the agent loop

Use the minimal runtime from Section 4 as a starting point.

Ask the agent:

> Investigate the failed reservations and identify likely causes.

Allow a maximum of twelve tool calls.

Record every decision and observation.

### Part C — Compare with a deterministic approach

Build a conventional workflow that retrieves all reservations, payment events, and relevant logs in a fixed sequence.

Compare:

- Total tool calls.
- Total model calls.
- Execution time.
- Estimated cost.
- Number of correctly classified failures.
- Missing or unsupported conclusions.

The agent may outperform the fixed workflow by selectively investigating relevant information.

Or it may waste resources exploring unnecessary branches.

Both outcomes are useful evidence.

### Part D — Introduce misleading evidence

Add a log message that appears to implicate the payment provider but actually corresponds to a different reservation.

Observe whether the agent follows the misleading clue.

Then introduce a verification tool that can cross-reference reservation IDs and payment-event identifiers.

Evaluate whether the additional capability improves results.

### Part E — Test termination

Make one reservation's payment outcome permanently unavailable.

Does the agent continue searching indefinitely?

Does it invent a conclusion?

Does it accurately identify the case as unresolved?

A robust agent should distinguish incomplete information from completed investigation.

### Part F — Simulate interruption

After the sixth tool call, terminate the execution process.

Persist the execution state before the interruption, then resume the investigation.

Ensure that completed observations remain available and unnecessary work isn't repeated.

For this read-only exercise, duplicate execution is mostly an efficiency concern.

In a later experiment, add a simulated notification operation with a stable idempotency key and test recovery after an uncertain outcome.

### Part G — Evaluate trajectories

Don't judge the agent only by its final report.

Inspect whether it:

- Selected relevant tools.
- Used correct reservation identifiers.
- Avoided unnecessary repetition.
- Recognized uncertain payment states.
- Respected execution limits.
- Produced conclusions supported by observed evidence.

The exercise should make one thing painfully clear: a successful-looking final answer reveals only part of an agent's actual behavior.

---

## 15. Engineering and Interview Challenges

### Challenge 1 — The unnecessary autonomy

An engineer proposes replacing a working refund workflow with an agent that can dynamically decide which business operations to perform.

Their argument is that the model is intelligent enough to understand refund policies.

Would you approve the design?

### Challenge 2 — The reliability paradox

An agent uses a model that achieves 98% accuracy on individual tool-selection decisions.

Nevertheless, the complete application fails a substantial fraction of multi-step tasks.

How can this happen?

### Challenge 3 — The confident completion

An investigation agent reports that all affected customers have been identified.

The application discovers that seven reservations were never examined.

What architectural change would prevent this failure from being considered a successful run?

### Challenge 4 — The interrupted workflow

An agent sends a customer email and then crashes before recording the operation's completion.

When restarted, it proposes sending the email again.

How should the runtime handle this?

### Challenge 5 — The planning trap

An agent creates a detailed ten-step plan to diagnose a production outage.

After the third step, evidence strongly contradicts the original hypothesis.

Should the system force completion of the plan?

---

## 16. Solutions and Discussion

### Solution 1 — Keep the deterministic refund workflow

The refund process contains known business invariants, permissions, and transactional requirements.

Understanding policy language is useful, but it does not justify delegating the execution sequence to a probabilistic model.

Use the LLM to interpret ambiguous requests or summarize applicable policy evidence.

Let deterministic application services evaluate eligibility, enforce limits, obtain approvals, and execute refunds.

Autonomy should be introduced only where uncertainty about the next step provides genuine value.

### Solution 2 — Errors accumulate across decisions

A multi-step task may require many correct decisions, and an early incorrect assumption can redirect later actions.

Under a simplified independence assumption, twelve steps at 98% accuracy produce approximately 78.5% all-correct execution probability.

Real failures can be correlated, and not every mistake is fatal.

The solution involves reducing unnecessary model decisions, introducing verification checkpoints, supporting recovery, and evaluating full task trajectories rather than individual outputs.

### Solution 3 — Independent completion verification

The application should compare the agent's report against the authoritative set of reservations requiring investigation.

A structured result can explicitly identify investigated and unresolved items.

Completion should require satisfying defined acceptance criteria, not merely generating the phrase "investigation complete."

If seven reservations remain unexamined, the run should be marked incomplete or require further work.

### Solution 4 — Treat the outcome as uncertain

The runtime cannot assume that the email wasn't sent merely because the checkpoint is missing.

It should inspect persistent operation records or reconcile with the delivery provider where possible.

If the provider supports appropriate idempotency semantics, the same logical operation identity should be reused.

Otherwise, the application may need manual reconciliation or carefully designed duplicate-prevention logic.

Durable execution does not mean blindly replaying external side effects.

### Solution 5 — Replan based on evidence

An agent's plan is a provisional strategy, not an authoritative workflow contract.

If new evidence contradicts the hypothesis, the system should allow reassessment and revision.

However, changing the plan should still respect execution budgets, permissions, and business constraints.

The agent can adapt its investigative strategy.

It cannot redefine which operations it is authorized to perform.

**A useful agent is flexible about how it investigates, but disciplined about what it is allowed to do.**

---

## Mental Model

An agent is a model-driven decision loop operating within a software-controlled environment.

The model selects actions based on an objective and accumulated observations. The application owns state, tool execution, authorization, resource limits, recovery, and completion criteria.

Autonomy is valuable when the path to a solution is uncertain and intermediate feedback can guide the next step.

**Give the model freedom where judgment is useful, and enforce structure where correctness is mandatory.**


---

## Next Lecture — AI410-L03: Agent Memory, Context, and State

Continue in **AI410 — Agentic AI Systems and Production Engineering**.

## Further Reading

1. **Anthropic — Building Effective Agents**  
   An influential engineering discussion distinguishing workflows from agents, emphasizing simple composable patterns, orchestration, and appropriate autonomy.  
   https://www.anthropic.com/engineering/building-effective-agents

2. **OpenAI — A Practical Guide to Building Agents**  
   Guidance on agent architecture, model and tool selection, execution loops, guardrails, and deciding when autonomy is justified.  
   https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/

3. **OpenAI — Agents SDK Documentation**  
   Current reference for building agent runtimes with tools, handoffs, state, human review, and tracing.  
   https://developers.openai.com/api/docs/guides/agents/sdk

4. **OpenAI — Running Agents**  
   A closer examination of the agent loop, continuation strategies, termination, and interruption handling.  
   https://developers.openai.com/api/docs/guides/agents/running-agents

5. **LangGraph — Thinking in LangGraph**  
   Practical guidance for modeling agents and workflows as graphs containing data operations, LLM steps, actions, and human-intervention boundaries.  
   https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph

6. **Yao et al. — ReAct: Synergizing Reasoning and Acting in Language Models (2022)**  
   An influential research paper describing how language models can interleave reasoning with actions and observations from external environments.  
   https://arxiv.org/abs/2210.03629

7. **OpenAI — Evaluating Agent Workflows**  
   Documentation on evaluating agent behavior and execution trajectories rather than relying solely on final responses.  
   https://developers.openai.com/api/docs/guides/agents

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
AI410-L02  AGENTS / WORKFLOWS — INTERVIEW GLANCE CARD

DEFINITION
  Agent: model selects actions toward objective, observes results, adapts
  Workflow: app owns control flow; model may power a step
  Spectrum: classify → tool assistant → branchy workflow → autonomous task agent
  Autonomy expands capability AND path space

LOOP
  Observe → Decide → Act → Observe; Aₜ=π(Sₜ,Oₜ,Objective)
  Model proposes; app owns authz, limits, persistence, termination
  Finish/clarify/tool_call structured decisions; MAX_STEPS budget

PLANNING
  Reactive incremental OK (debug); plans provisional & revisable
  Don't plan every 2-step task for diagram beauty

STATE
  App owns operational state; transcript ≠ execution truth
  Conversation continuity ≠ workflow recovery ≠ external side-effect correctness
  Checkpoint + idempotency/reconcile (crash after email send)

AGENTS vs DETERMINISTIC
  Known refund sequence → deterministic + LLM interpret/explain
  Unknown investigation path → bounded agent justified
  Rule: can sequence be determined reliably in advance?

MIDDLE GROUND
  Routing; prompt chaining; agentic decisions at uncertain branches only
  Termination: model "done" is observation — verify acceptance criteria
  Errors compound across long trajectories; reduce unnecessary decisions

BUDGETS / DURABILITY / OBS
  Steps, tools, time, tokens, cost; human intervention points
  Durable runs; independent completion checks
  Trace full trajectory — final answer alone insufficient

WHEN WORTH IT
  Path uncertainty + evaluable progress + enforceable bounds
  Flexible how it investigates; disciplined what it's allowed to do

SENIOR LINE: freedom where judgment helps; structure where correctness is mandatory.
```
