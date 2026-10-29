---
id: CS220-L01
course: CS220
title: "What a Programming Language Actually Promises"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [CS101-S06]
prev: null
next: CS220-L02
---





# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 01: What a Programming Language Actually Promises

*The compiler approves your program. The runtime executes it. The payment provider receives the request. The customer is charged the wrong amount. Everybody fulfilled their contract—except the application.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine that you're building a hotel-booking platform in TypeScript.

A customer selects a room costing 200 euros. The application retrieves a price quotation from an internal service, adds a booking fee, and displays the amount to be paid.

The code looks straightforward.

The price service returns a JSON object containing a field named `priceCents`. Your TypeScript interface declares that the field is a number.

Your calculation adds a 1,200-cent fee.

The application passes its TypeScript checks. The Docker image builds. The deployment succeeds.

Then the first customer sees an absurd total.

The expected amount is 21,200 cents.

The actual result behaves like the text `"200001200"`.

What happened?

The price service returned `"20000"` as a string, not `20000` as a number.

JavaScript's addition operator encountered a string and performed concatenation.

Your TypeScript declaration said the field was numeric, but that declaration hadn't converted or validated the data arriving from the network.

The program was legal JavaScript. Its runtime behavior followed JavaScript's rules.

The application was still wrong.

To understand why, we need to distinguish several different agreements that are easy to confuse.

## 1. The recipe, the inspector, and the kitchen

Imagine a professional kitchen.

A chef writes a recipe. The recipe contains instructions, quantities, and expected ingredients.

An inspector checks whether the recipe is well formed and follows certain rules.

The kitchen then executes the recipe with actual ingredients.

Finally, the customer eats the result.

Those are four different stages.

The inspector may confirm that a recipe consistently refers to flour, sugar, and butter.

But if a supplier delivers salt in a container labeled sugar, the recipe can produce a disastrous cake.

The inspection wasn't necessarily defective. It operated on the information available to it.

Something went wrong when the declared ingredients met the real ingredients.

Programming languages have similar boundaries.

**The language** defines which expressions exist and what they mean.

**Static analysis and type checking** can establish selected properties before execution.

**The runtime** executes the resulting program using actual values.

**The surrounding world** supplies data, timing, failures, and side effects that the language can't simply declare away.

Our booking bug occurred because information crossing from the outside world into the program was treated as though it had already satisfied an internal promise.

## 2. Source code is not what the processor ultimately sees

When you write TypeScript, the computer's processor doesn't directly execute TypeScript type annotations.

The source passes through a series of transformations and checks.

A TypeScript tool can parse the source, analyze its types, and produce JavaScript.

A JavaScript engine then executes that JavaScript using its own internal machinery.

Depending on the runtime and circumstances, that machinery may include interpretation, compilation, optimization, and machine code.

This is why the familiar argument about whether a language is "compiled" or "interpreted" is often less useful than it sounds.

Different stages can coexist.

A program may be checked ahead of time, transformed into another representation, interpreted initially, and optimized into native instructions later.

The important question is not which marketing category the language belongs to.

It is what happens at each stage, and which guarantees survive into execution.

## 3. Types are predictions about values

Suppose a function expects a number.

A static type checker can examine code paths and reject many operations that would obviously violate that expectation.

It might prevent passing a string into a function whose parameter is declared numeric.

That's valuable.

But imagine the function receives data from a network response.

The external server isn't controlled by your TypeScript compiler.

The server may return a string where you expected a number.

It may omit a required field.

It may return a structurally correct object containing a logically impossible value.

The type checker can only reason from its model of the program.

If that model includes an unjustified assumption about outside data, the checker may approve code built upon that assumption.

A type annotation isn't a spell that forces reality to comply.

### The trust boundary

```text
External price service
        |
        | JSON bytes: {"priceCents":"20000"}
        v
Network response
        |
        | Parse JSON
        v
Unknown runtime value
        |
        | Validate and normalize
        v
Trusted domain value
        |
        | Type-checked business logic
        v
Booking calculation
```

The critical transition isn't merely parsing the JSON.

It's establishing that the resulting value satisfies the contract your application needs.

## 4. The same source can run in different worlds

Now imagine moving the booking application between a browser and a Node.js server.

Both environments support JavaScript.

But they're not identical.

The browser provides interfaces for manipulating a document, handling user interactions, and accessing browser-managed capabilities.

Node.js provides server-oriented APIs for interacting with the operating system, processes, files, and networks.

Some APIs are available in both environments. Others are specific to one.

And even when two environments offer an API with the same name, supported options and implementation details can matter.

The JavaScript language defines core computational behavior.

The host environment supplies additional capabilities that allow the program to interact with the world.

This matters because a function can be perfectly valid JavaScript while depending on an API that doesn't exist in its current environment.

**Language compatibility and runtime-environment compatibility are separate concerns.**

## 5. Abstractions are useful because they hide things

Suppose your booking application uses a repository abstraction.

Instead of writing SQL directly, it calls `reservationRepository.save()`.

That's convenient.

The developer can focus on business operations without repeatedly writing database-specific code.

But what does `save()` actually guarantee?

Does it begin a transaction?

Does it commit before returning?

Does it retry after a connection failure?

Does it perform several SQL statements?

Does it update cached objects?

The method name doesn't answer those questions.

An abstraction hides implementation details so that users of the abstraction can work at a higher level.

That's valuable.

But the hidden details don't stop existing.

When correctness or performance depends on those details, the engineer must understand the boundary.

The right question isn't whether abstraction is good or bad.

It's **what the abstraction promises, and what it deliberately leaves outside that promise**.

## 6. A program has several kinds of correctness

Return to the hotel booking.

The source code is syntactically valid.

The type checker reports no errors.

The JavaScript runtime executes the operations according to the language's rules.

The network request completes.

The final amount is still wrong.

These observations are not contradictory.

They concern different kinds of correctness.

Syntactic correctness means the code follows the language's grammar.

Type correctness means it satisfies the properties enforced by the selected type system and configuration.

Runtime correctness concerns what actually happens when the program executes with real values and resources.

Business correctness concerns whether the resulting behavior satisfies the application's intended rules.

A successful compiler doesn't automatically verify a payment calculation.

A successful HTTP response doesn't automatically mean the reservation belongs to the correct customer.

And a function that returns without throwing isn't necessarily a function that produced the right result.

## The minute-long mental replay

A programming language defines what programs mean.

Tools can analyze those programs and reject selected mistakes before execution.

The runtime implements the language behavior and provides or connects to the environment in which execution occurs.

External information crosses boundaries where the compiler's assumptions may not match reality.

Abstractions simplify programming by hiding details, but those details remain important when they affect correctness, performance, or failure handling.

The senior engineer's responsibility is to understand which guarantee comes from which layer—and not mistake one layer's success for another's.

### Three questions before the Deep Dive

1. Why can TypeScript accept a program whose real JSON input has the wrong type?
2. Why is "compiled versus interpreted" an inadequate description of modern runtime systems?
3. Why can an ORM or repository abstraction be convenient without guaranteeing correct database behavior?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Code That Passed Every Check and Charged the Wrong Price

Let's reconstruct the production incident precisely.

Our booking API calls a quotation service.

That service is supposed to return a price in integer cents.

The TypeScript application declares an interface describing the response and then calculates the total.

The developer assumes that the incoming data satisfies the declared interface.

The source contains an assertion similar to this:

```typescript
interface Quote {
  priceCents: number;
}

const response = await fetch(quoteUrl);
const quote = (await response.json()) as Quote;

const totalCents = quote.priceCents + 1200;
```

In the application's static model, `priceCents` is a number.

The type checker therefore accepts numeric arithmetic.

But suppose the response actually contains:

```json
{
  "priceCents": "20000"
}
```

JSON parsing produces an object whose `priceCents` property is a JavaScript string.

The `as Quote` assertion doesn't convert that string into a number.

The TypeScript compiler removes the assertion during compilation or transformation.

At runtime, JavaScript evaluates the actual values.

Adding a number to a string can produce string concatenation.

The resulting value is `"200001200"`, not `21200`.

The original source-level assumption has now become a business defect.

### Which component is wrong?

The external service violated the expected response contract.

The caller failed to validate the external value.

The type assertion made an unverified value appear trusted.

The JavaScript engine, meanwhile, correctly executed the operation according to JavaScript semantics.

This distinction matters because it tells us what to fix.

Replacing Node.js won't solve the problem.

Optimizing the compiler won't solve it.

Adding a more elaborate interface won't solve it.

The missing mechanism is validation at the trust boundary, followed by appropriate domain logic.

Before designing the fix, let's understand the layers involved.

## 2. A Programming Language Has Syntax and Semantics

A programming language is a formal system for expressing computations.

Its specification defines which programs are valid under its grammar and what language constructs mean.

Two ideas are especially important.

**Syntax** determines which forms of source code are permitted.

**Semantics** determines the behavior associated with those forms.

### Syntax

Consider an expression that omits a necessary closing parenthesis.

A parser may reject it before the program can execute.

The source doesn't satisfy the expected grammar.

This is a syntax problem.

A compiler or interpreter cannot simply assume which program the author intended.

### Semantics

Now consider the expression `"20000" + 1200`.

This is valid JavaScript syntax.

Its behavior follows JavaScript's semantics for the addition operator and the conversion behavior involved.

The fact that a developer intended numeric addition doesn't change the language's meaning.

The runtime executes the language's rules, not the programmer's private intentions.

This is why programming language semantics matter.

The difference between a string and a number isn't only a label in an editor.

It affects the operations that actually occur.

### Specifications and implementations

A language specification describes required behavior.

An implementation makes that behavior executable.

Different JavaScript engines can use different internal representations, optimization strategies, garbage collectors, and machine-code generation techniques while producing the required observable language behavior.

This distinction allows implementation innovation without requiring developers to rewrite every application whenever an engine changes.

But specifications can also leave certain choices to implementations or permit behavior that depends on the environment.

Not everything you observe belongs to the core language contract.

Understanding the difference between specified behavior and implementation details is a central engineering skill.

## 3. The Five Contracts Hidden Inside One Program

A useful mental model is to think of a program as passing through several contracts.

### Contract one: source validity

Can the source be parsed and interpreted according to the language grammar?

A syntax error may prevent the program from reaching later stages.

### Contract two: static analysis

Does the source satisfy properties that a compiler, type checker, linter, or other tool can establish before execution?

For example, a type checker may identify an invalid function call or an impossible property access under its model.

### Contract three: runtime behavior

Given actual values, what operations does the executing implementation perform?

Here, JavaScript's string concatenation behavior matters.

### Contract four: external interaction

What information do files, networks, databases, operating systems, and other services supply?

The quotation service can return malformed data or fail.

The database can reject a transaction.

The network can time out.

These behaviors aren't controlled solely by the programming language.

### Contract five: domain correctness

Does the application preserve the business rules it is responsible for?

For a booking system, the total amount must be correct.

A reservation must belong to the correct customer.

Inventory must not be oversold.

A payment must not be duplicated.

These requirements exist independently of which programming language the team chooses.

### Why layers matter

Suppose a request fails in production.

An engineer who treats every failure as a language problem may begin rewriting code unnecessarily.

Another might blame the database whenever a business invariant fails.

A better engineer identifies which contract was violated.

The wrong amount could originate from a malformed input, a numeric representation error, a business-logic defect, or a persistence problem.

Each possibility requires different evidence.

**Correctness is not one green checkmark. It is a collection of guarantees established at different boundaries.**

## 4. What Actually Happens to a TypeScript Program?

Now let's follow the source code through its execution pipeline.

A TypeScript application begins as text.

A compiler or related tool parses it into a structured representation.

A type checker can analyze relationships between expressions, declarations, and values.

A transformation stage produces executable JavaScript, removing or lowering TypeScript-specific constructs as appropriate.

A JavaScript runtime then executes that JavaScript.

The exact pipeline depends on the tooling.

### Parsing

Parsing turns the source into structured program elements.

The tool distinguishes declarations, expressions, function calls, operators, and other constructs.

A syntax error can be detected during this stage.

Parsing doesn't establish that your booking fee is legally or mathematically correct.

It establishes that the source has a structure the tool can understand.

### Type checking

TypeScript examines type relationships.

If a function accepts a number but receives a value statically known to be a string, the checker can report an error.

If a property doesn't exist on the declared type of an object, the checker can identify that.

With appropriate compiler options, it can provide useful guarantees concerning nullability, implicit `any`, and other risks.

But the analysis works from type information.

It doesn't automatically inspect live responses from the quotation service during compilation.

### Emitting JavaScript

TypeScript typically removes type-only constructs when producing JavaScript.

A type annotation doesn't remain as a runtime assertion.

An interface doesn't become a runtime validator.

A type assertion such as `as Quote` doesn't check a JSON response.

Some TypeScript constructs have runtime emit behavior—for example, certain enum patterns—so it is inaccurate to claim that every TypeScript construct disappears.

The important distinction is that ordinary type annotations and type assertions do not themselves enforce runtime data contracts.

### Execution

A JavaScript engine executes the resulting program.

It observes actual JavaScript values, not the TypeScript types the source author hoped those values would have.

If a network response contains a string, that value is a string until the application transforms it.

If a property is missing, it may be `undefined` when accessed.

If the code calls a non-function value, the runtime can throw a `TypeError`.

The execution follows JavaScript rules.

### The build-configuration trap

One subtle point deserves attention.

Running a TypeScript compiler and receiving type errors doesn't necessarily guarantee that no JavaScript files were emitted.

The behavior depends on options such as `noEmitOnError` and the selected build pipeline.

Some tools perform transformation without full type checking.

This means a project can successfully produce runnable JavaScript while separate type-checking errors remain.

A production pipeline should explicitly decide whether type errors block artifact publication.

Don't assume that the word *build* implies one universal collection of checks.

## 5. Compiled Versus Interpreted Is Not a Binary Choice

Developers often classify languages as compiled or interpreted.

The distinction captures something real, but the simple categories are often misleading.

Compilation is the transformation of one program representation into another.

Interpretation is a method of executing a program representation by processing its instructions through an interpreter.

A single language ecosystem can use both techniques.

### Ahead-of-time compilation

A compiler may translate source code or an intermediate representation into native machine code before the program begins executing.

C, C++, Rust, and Go commonly use ahead-of-time compilation in their ordinary toolchains.

That doesn't mean every program produced by those languages is automatically efficient.

The compiled program can still use poor algorithms, excessive memory, blocking I/O, or inappropriate synchronization.

Native code doesn't erase the cost of bad design.

### Bytecode and intermediate representations

Some language implementations compile source into an intermediate form.

The Java Virtual Machine commonly executes Java bytecode, using interpretation and runtime compilation techniques as appropriate.

CPython commonly compiles Python source into Python bytecode that its interpreter executes.

These representations are designed for their respective runtime systems.

The processor doesn't directly understand ordinary Python bytecode or Java bytecode as native machine instructions.

An implementation must execute or translate those instructions.

### Just-in-time compilation

A JIT compiler translates code into machine instructions during program execution.

This allows an implementation to use runtime information.

For example, a JavaScript engine may observe which operations and value shapes occur frequently and optimize certain execution paths.

The runtime must preserve the relevant language semantics, including handling cases where an optimization's assumptions stop holding.

The details can be sophisticated, but the architectural idea is simple.

The implementation can learn from execution.

### Why the distinction matters

An interpreter can spend more work per language operation.

A JIT may require warmup time and consume memory for generated code.

Ahead-of-time compilation may improve startup characteristics or produce optimized native code, depending on the workload.

But performance also depends on libraries, data representation, allocation behavior, the operating system, and the algorithm.

We'll compare those trade-offs later in CS220.

For now, the important concept is that **compilation strategy is an implementation choice, not a complete performance verdict**.

## 6. Language, Runtime, and Host Environment

Now imagine the same JavaScript calculation running in a browser and in Node.js.

The basic language expression `"20000" + 1200` behaves according to JavaScript semantics in both environments.

But the surrounding capabilities differ.

The browser provides a document model, user-interface events, and browser-managed networking and storage interfaces.

Node.js provides APIs for processes, filesystem interaction, networking, and other server-oriented operations.

A program may depend on capabilities that exist in one environment but not another.

### The JavaScript engine

A JavaScript engine implements the core language.

It parses and executes JavaScript, manages language values, and implements required semantics.

Its internal implementation may include garbage collection, optimization, and other mechanisms.

### The host

The host environment supplies additional APIs and integration with the outside world.

The `document` object in browsers is not part of the ECMAScript core language.

Filesystem APIs in Node.js are not intrinsic ECMAScript operations.

The Fetch API is a platform API implemented by browser environments and supported server runtimes, not a primitive defined by the core language itself.

This distinction matters when code is moved between environments.

A function can be syntactically valid, well typed according to its configured declarations, and still fail because the actual host lacks an API it expects.

### The declaration-file illusion

TypeScript projects often use declaration files to describe available APIs.

Those declarations help the checker reason about code.

But a declaration file doesn't install the corresponding implementation.

If your type environment claims an API exists and your runtime doesn't provide it, the program can fail when executed.

Again, the static model and the real environment must agree.

### A useful deployment question

Before moving an application to a new runtime, ask:

Does the runtime support the required language features?

Does it supply the necessary platform APIs?

Are the external libraries compatible?

Does the execution environment provide the expected permissions, files, networking, and resources?

These are separate questions.

Language compatibility alone isn't enough.

## 7. Static Typing and Dynamic Typing: Different Guarantees, Not Rankings

Let's clarify another common misunderstanding.

Dynamically typed languages are not languages without types.

Python values have types.

JavaScript values have types.

Those types influence what operations are valid and how expressions behave at runtime.

The distinction is about when and how selected properties are checked.

### Static typing

A static type system analyzes program expressions before execution.

It can reject programs that violate its rules.

This catches many mistakes early.

For example, if a function expects a number and the checker knows a string is being passed, it can report the mismatch.

Different static type systems can enforce different properties.

Some emphasize structural compatibility.

Others use nominal declarations.

Some encode ownership or lifetime relationships.

These differences matter, but they deserve their own lecture.

### Dynamic typing

A dynamically typed runtime uses actual values and their runtime behavior when executing operations.

Python doesn't need a static type checker to know that a value is a string during execution.

It can use that information when an operation is attempted.

Dynamic typing can support flexible code, but certain errors may be discovered only when a problematic path is executed.

### Python type hints

Python also supports type annotations and external static-checking tools.

These annotations can help developers reason about code and detect mistakes before execution.

But the existence of annotations doesn't mean that the ordinary Python runtime automatically enforces all declared type contracts.

The Python ecosystem demonstrates that static analysis and dynamic execution are not mutually exclusive concepts.

### The misleading hierarchy

It is tempting to say that static typing is always safer and dynamic typing is always more flexible.

Real engineering is more complicated.

A poorly designed statically typed application can contain severe business bugs.

A carefully validated dynamically typed application can maintain strong correctness guarantees.

And a static type checker can be bypassed or weakened through assertions, unchecked inputs, unsafe operations, or unsound assumptions.

The useful question is:

**Which errors does this type system catch, which guarantees does it enforce, and what remains the application's responsibility?**

## 8. The Boundary Where Types Stop Protecting You

Return to the quotation response.

Suppose the external service now returns a number as expected.

The value is:

`-20000`

It has the correct runtime type.

But should a hotel quotation contain a negative price?

Probably not under the ordinary pricing contract.

Now suppose the value is:

`999999999999`

Still a number.

But perhaps it exceeds the maximum legitimate booking amount.

Or suppose the price is correctly represented in cents but belongs to a different currency.

A plain numeric type cannot distinguish all those conditions.

### Structural validity

Structural validation asks whether the value has the expected shape.

Does the object contain `priceCents`?

Is the value a number?

Are required fields present?

Is the currency a recognized string or enumeration value?

This is already stronger than asserting that arbitrary JSON matches an interface.

### Semantic validity

Semantic validation asks whether the value makes sense in the domain.

Is the price nonnegative?

Is it finite?

Does it fit the chosen numeric representation?

Does it represent an integer number of cents?

Is the currency supported?

Does the quote correspond to the requested room and dates?

Is it still valid?

Some of these conditions can be represented with more expressive types.

Others require runtime checks against current application data or external systems.

### Validation isn't one universal function

Imagine a quotation object that passes every structural check.

It contains a valid price, currency, room identifier, and expiration timestamp.

But the room is no longer available.

The data is structurally valid and may even have been valid when issued.

The business operation still cannot proceed.

The application needs to consult authoritative state and enforce the booking invariant.

This is why we should distinguish:

**Shape:** Does the value have the expected structure?

**Meaning:** Does the value satisfy domain rules?

**Authority:** Is the relevant external state still true?

A type system can help express the first two, but the third often depends on runtime coordination and persistence.

## 9. Turning Unknown Data Into Trusted Data

How should our application handle the quotation response?

A sound design treats externally supplied JSON as unknown until it has been validated.

That is a useful distinction in TypeScript.

The type `unknown` requires code to establish properties before using the value in operations that assume a narrower type.

By contrast, `any` largely disables those checks.

### A deliberately small validator

Here's a focused example that validates the shape and basic numeric constraints of the quotation response:

```typescript
type Quote = {
  priceCents: number;
  currency: "EUR";
};

function parseQuote(input: unknown): Quote {
  if (
    typeof input !== "object" ||
    input === null ||
    !("priceCents" in input) ||
    !("currency" in input)
  ) {
    throw new Error("Invalid quote");
  }

  const candidate = input as Record<string, unknown>;

  if (
    !Number.isSafeInteger(candidate.priceCents) ||
    (candidate.priceCents as number) < 0 ||
    candidate.currency !== "EUR"
  ) {
    throw new Error("Invalid quote");
  }

  return {
    priceCents: candidate.priceCents as number,
    currency: "EUR",
  };
}
```

This code is intentionally limited to a small example.

It validates that `priceCents` is a safe nonnegative integer, and that the currency is the one supported by this particular operation.

A production implementation might use a schema-validation library and additional domain constraints.

But notice the critical difference from the original code.

The function doesn't simply declare that unknown input is a Quote.

It examines the actual runtime value before returning a trusted representation.

### Why constructing a new object helps

After validation, the function returns a new object containing only the fields it has accepted.

This creates a clearer boundary.

Code receiving the returned Quote can rely on the parser's documented guarantees, subject to the correctness of the validator itself and ordinary mutation considerations.

The parsing function becomes part of the application's trusted computing path.

If it contains a mistake, invalid data can still enter.

Therefore, validators deserve tests, especially around missing fields, wrong types, numeric boundaries, and malformed inputs.

### Validation is not automatic normalization

Suppose the service sends `"20000"` as a string.

Should we convert it to `20000`?

That depends on the contract.

If strings are an explicitly supported representation, normalization may be appropriate.

If the service contract requires a JSON number, silently accepting strings may conceal an upstream defect.

And permissive conversion can introduce surprising behavior for empty strings, whitespace, invalid numeric text, or extremely large values.

**Validate what the contract actually promises. Normalize only when the conversion has an intentional meaning.**

## 10. Type Safety Is Not Business Correctness

Suppose we repair the quotation parser.

The response is now valid.

The price is 20,000 cents.

The booking fee is 1,200 cents.

The calculated total is 21,200 cents.

Everything appears correct.

But the system still has a business problem.

Two customers are attempting to reserve the last available room.

Both requests read a state indicating one room remains.

Both independently decide that the booking is permitted.

Both commit reservations without appropriate coordination.

All the data types are valid.

Every arithmetic operation is correct.

Every function signature is satisfied.

The business invariant has been violated.

The hotel has sold the last room twice.

This demonstrates a deeper limit.

A type system can reject many malformed operations.

It doesn't automatically enforce consistency across concurrent database transactions.

That requires appropriate application and storage mechanisms.

We'll study those mechanisms in the database and distributed-systems courses.

For now, the important lesson is that a program can be perfectly type-correct while making an invalid state transition.

### Correct local operations can create an incorrect global state

Each booking request may be individually sensible.

The problem arises from the interaction between requests.

This is why language correctness must be separated from system correctness.

A compiler evaluates a program according to its static model.

It doesn't ordinarily observe all possible future combinations of concurrent external events and database state.

Application architecture must preserve the invariants that matter to the business.

## 11. Abstraction: Hiding Complexity Without Denying It

Now let's examine another common source of confusion.

Our booking application uses an ORM.

Developers can retrieve reservations through a convenient repository interface.

Instead of writing SQL, they ask for a customer and its reservations.

The API looks simple.

But the underlying ORM may perform several database operations.

### The N-plus-one example

Imagine displaying a list of one hundred customers.

The application retrieves the customer list using one query.

Then it accesses each customer's reservations.

Depending on the ORM and data-loading configuration, those accesses may trigger one additional database query per customer.

The code may look like one elegant operation over objects.

The database executes 101 queries.

This is the N-plus-one query problem.

The abstraction made the code easier to read.

It did not make database work disappear.

### The incorrect lesson

Some engineers see this and conclude that abstractions are bad.

That's not the right conclusion.

An ORM can be useful for domain modeling, query construction, persistence workflows, and developer productivity.

The problem isn't that it hides complexity.

That's its purpose.

The problem is failing to understand where the abstraction's guarantees end.

### An abstraction has a cost model

A useful abstraction should allow developers to answer several questions.

What does this operation promise?

Which side effects can it perform?

What are its failure modes?

What is the approximate resource cost?

Does it preserve the relevant business semantics?

Where can the caller observe or control its behavior?

You don't need to inspect every implementation detail on every request.

But when correctness or performance depends on a hidden mechanism, you must be able to investigate it.

A good abstraction reduces ordinary cognitive load without making critical behavior impossible to understand.

## 12. Promises and Asynchrony: Completion of What?

Consider a function returning a Promise.

A developer writes:

`await reservationRepository.save(reservation)`

When the Promise resolves, what has completed?

That depends on the implementation's contract.

Perhaps the database operation committed successfully.

Perhaps a message was placed into an internal queue.

Perhaps an asynchronous operation was acknowledged by a service that will perform additional work later.

The JavaScript Promise mechanism represents eventual settlement of an asynchronous computation.

It doesn't independently define the durability semantics of an external database or broker.

Those semantics belong to the operation being represented.

### The dangerous inference

Imagine an API publishes a scan request to a queue.

The publishing operation resolves successfully.

The API returns HTTP 202 Accepted.

A developer says the scan succeeded.

But the scan hasn't executed yet.

The Promise's fulfillment established one stage of the workflow.

It did not establish completion of the business operation.

This is exactly the kind of confusion that appears when language constructs are treated as guarantees about the external world.

### Cancellation and timeouts

Likewise, an application can stop waiting for an operation without proving that the operation stopped remotely.

An HTTP request may time out after a database or payment service has already performed an action.

A rejected Promise doesn't necessarily mean the intended business effect never happened.

The application must distinguish observation from outcome.

The language offers tools for representing and coordinating asynchronous behavior.

The application defines what those tools mean within its business contract.

We'll develop the event loop, scheduling, cancellation, and concurrency mechanisms in later courses.

For now, remember the boundary: **a language-level completion signal is meaningful only through the contract of the operation it represents**.

## 13. Programming Paradigms Are Ways to Organize Responsibilities

Programming languages support different ways of organizing code.

You may hear terms such as procedural, object-oriented, functional, or declarative programming.

These terms are useful, but they shouldn't become rigid identities.

Modern languages often support several paradigms.

TypeScript supports functions, objects, classes, closures, and higher-order operations.

Python supports procedural, object-oriented, and functional styles.

Java, Go, and Rust make different design choices, but none can be summarized completely by one paradigm label.

### Procedural organization

A procedural approach describes a sequence of operations.

Read input, validate it, calculate a result, and persist it.

This can be appropriate when the operation's control flow is clear.

### Object-oriented organization

An object-oriented design groups state and behavior around objects or entities.

For example, a Reservation object might encapsulate operations relevant to reservation state.

That can protect local invariants when carefully designed.

But placing methods inside classes doesn't automatically solve distributed consistency or prevent invalid external data.

### Functional organization

A functional approach emphasizes composition of functions and often prefers explicit data transformations.

Pure functions are especially useful because their result depends on their inputs without hidden external side effects.

For example, a pricing function that accepts a validated quotation and returns a calculated total is easier to test than one that also fetches exchange rates, updates a database, and sends emails.

But real applications must eventually interact with the outside world.

A useful functional design often makes those interactions explicit rather than pretending they don't exist.

### Declarative organization

A declarative interface describes a desired result rather than every mechanical step.

SQL is a familiar example.

A query describes which data should be returned, while the database optimizer chooses an execution plan.

But the optimizer's choice affects performance.

Declarative code doesn't remove operational consequences.

### The practical lesson

Paradigms are design tools.

The goal is to choose structures that make important state, dependencies, side effects, and invariants understandable.

The best architecture isn't the one that can be described with the most fashionable paradigm name.

It's the one whose behavior remains correct and comprehensible as the system evolves.

## 14. The Boundary Between Pure Logic and External Effects

Let's return to our booking calculation.

We can divide the operation into three conceptual stages.

First, retrieve and validate the quotation.

Second, calculate the amount using trusted domain values.

Third, persist or transmit the resulting business operation.

These stages have different failure modes.

### External input

The quotation service can time out, return malformed JSON, or provide a value that violates the expected schema.

The application needs defensive validation and an explicit failure policy.

### Pure calculation

Given a validated quotation and booking fee, the calculation can be deterministic.

The function can be tested with ordinary inputs and boundary cases.

It doesn't need a real database or payment provider to establish the arithmetic.

### External effects

Creating a reservation and collecting payment involve external state.

Those operations may fail, partially complete, or encounter concurrency.

Their correctness requires more than arithmetic.

Separating these responsibilities makes the application easier to test and reason about.

It doesn't necessarily mean creating a complicated class hierarchy or dozens of abstraction layers.

The architecture should expose the important boundaries without introducing ceremony that obscures the actual operation.

### A useful engineering rule

Keep deterministic business calculations separate from uncertain I/O when doing so improves clarity.

Validate inputs before treating them as domain values.

Make side effects visible in interfaces and control flow.

And define what success means for operations interacting with external systems.

This is a stronger design habit than simply declaring everything with a TypeScript interface.

## 15. Tests Verify Different Claims

Our production incident passed type checking.

Would unit tests have caught it?

Possibly, if the test used a quotation response containing a string price.

But a unit test using only well-formed numeric input might pass.

Different tests establish different properties.

### Static checks

Type checking catches selected source-level inconsistencies.

It is especially useful for refactoring and maintaining relationships between functions and data structures.

But it doesn't automatically validate arbitrary runtime inputs.

### Unit tests

Unit tests exercise specific pieces of behavior with chosen inputs.

A pricing test can verify arithmetic, currency handling, and rejected values.

But test coverage doesn't guarantee that every possible input or external state has been considered.

### Integration tests

An integration test can verify that the application correctly interacts with a realistic quotation service, database, or message broker.

It may reveal mismatches between independently maintained contracts.

But the test environment must represent the relevant production behavior.

### Contract tests

Contract tests can help verify agreement between service producers and consumers.

For example, the quotation service and booking API should agree about the JSON representation of monetary values.

A useful contract test might reject `"20000"` when the schema requires a JSON number.

However, compatible schemas don't establish that the returned amount is the correct price.

### Property-based tests

Property-based tests can explore many generated inputs and check invariants.

For example, the total price should never be less than the nonnegative base price when adding a nonnegative fixed fee.

Tests can generate boundary values and discover cases a developer didn't think to write individually.

Still, the quality of a property-based test depends on the property being meaningful.

### The testing lesson

Type checking, unit tests, contract tests, integration tests, and runtime monitoring provide different kinds of evidence.

They complement one another.

None should be described as a universal proof that a production business operation is correct.

## 16. Choosing What the Language Should Guarantee

Now imagine we're designing a larger booking system.

Should we encode every possible business condition into the type system?

Not necessarily.

Some constraints are cheap and useful to represent statically.

Others depend on live external state.

Still others would make the type system so elaborate that developers struggle to understand or maintain it.

### Stable structural relationships

It is often useful to distinguish a CustomerId from a ReservationId, even if both are represented using strings.

This can help prevent accidentally passing one identifier where the other is expected.

It can also be useful to represent mutually exclusive application states explicitly.

For example, a payment may be Pending, Confirmed, or Failed, with different fields valid for each state.

We'll explore these designs in CS220-L03.

### Runtime-dependent facts

Whether a room still exists, whether a customer's account is suspended, and whether a payment provider has accepted a transaction depend on current external facts.

A static type checker cannot establish those facts merely by inspecting the source.

Runtime validation and authoritative state transitions remain necessary.

### Ownership and mutation

Languages also differ in how they represent references, mutation, and ownership.

Some type systems can enforce powerful guarantees about resource access and memory safety.

These guarantees can eliminate important classes of bugs.

But they don't eliminate all application-level or distributed-systems failures.

We'll examine ownership and its trade-offs later, after establishing the underlying concepts.

### A useful allocation of responsibility

Use static types for relationships that can be expressed reliably before execution.

Use runtime validation for information entering from outside the trusted program state.

Use authoritative state and transaction mechanisms for business facts that can change concurrently.

Use tests and monitoring to evaluate behavior that remains uncertain.

The aim is not to make the compiler responsible for everything.

It's to give each guarantee to the mechanism capable of enforcing it.

## 17. A Senior Engineer's Decision Framework

When reading unfamiliar code, reviewing a framework, or choosing a language, ask five questions.

### What does the language specify?

Identify the semantics of the operations you're using.

Don't rely solely on intuition from another language.

A familiar operator or keyword may behave differently across languages.

### What does the static tooling establish?

Understand which errors are caught before execution.

Check compiler options and build enforcement.

A type checker configured permissively provides different guarantees from a strict one, and type assertions can bypass important protections.

### What does the runtime actually provide?

Identify the language implementation and host environment.

Does the required API exist?

Are resource behavior and execution constraints compatible with the application?

Does the runtime use a memory-management or concurrency model that matters for the workload?

### Where does untrusted reality enter?

Look for network responses, configuration, files, database results, message bodies, and user input.

Determine where these values become trusted application data.

If that transition is based on an assertion instead of validation, investigate the risk.

### What makes the business operation correct?

Write down the invariant.

For pricing, the amount and currency must be correct.

For reservations, inventory must not be oversold.

For payments, repeated attempts must not create duplicate charges.

Then identify which layer actually enforces the invariant.

This framework applies across languages.

A Rust service can violate a business rule.

A Python service can validate inputs correctly.

A Java application can mishandle a database transaction.

A TypeScript application can accept an incorrect JSON response.

The language changes which errors are easier to prevent, but it doesn't remove the need for engineering judgment.

## 18. The Oral Examination

Answer these aloud before reading the solutions. Don't merely define terms; explain the failure mechanism.

### Challenge 1 — The Typed Quotation

A TypeScript API declares that an external quotation contains `priceCents: number`.

The server returns `"20000"`.

The application uses a type assertion and adds a numeric booking fee.

Why can the code pass type checking and produce an incorrect total?

What would actually fix the boundary?

### Challenge 2 — The Compiled-Language Argument

An engineer claims:

"Go and Rust are compiled, so they're fast. Python and JavaScript are interpreted, so they're slow. Java is somewhere in the middle."

What is wrong with this reasoning?

### Challenge 3 — The Missing API

A JavaScript program works in the browser but fails in a server-side runtime because `document` is undefined.

Is this a JavaScript syntax error, a type-system problem, or a host-environment problem?

Explain the distinction.

### Challenge 4 — The Perfectly Typed Double Booking

Two customers simultaneously reserve the last room.

All function signatures are valid, all values have correct types, and neither request throws an exception.

Both reservations commit.

Why didn't type safety prevent the failure?

### Challenge 5 — The Invisible Database Work

A repository method appears to retrieve one customer with reservations.

The application suddenly executes hundreds of SQL queries.

Why doesn't the simple method interface guarantee inexpensive execution?

What evidence would you collect?

### Challenge 6 — The Misleading Promise

An API awaits a successful message publication and returns HTTP 202.

A developer claims the requested scan has completed successfully.

What exactly is wrong with that conclusion?

### Challenge 7 — The Stricter Type System

An engineer proposes representing every live business rule through elaborate static types.

Another proposes using ordinary primitive values everywhere and relying entirely on runtime checks.

How would you choose which guarantees belong in types and which belong elsewhere?

### Challenge 8 — The Broken Build Gate

A project runs a tool that produces JavaScript even when separate TypeScript type errors exist.

The release pipeline sees the output files and publishes them.

What important assumption has failed, and how would you correct the pipeline?

## 19. Solutions and Discussion

### Solution 1 — The type assertion didn't validate the response

TypeScript treated the asserted value as satisfying the Quote interface during static analysis.

The assertion didn't transform the runtime string into a number.

JavaScript then performed an operation using the actual string value.

The application should treat externally parsed JSON as unknown, validate it against a runtime schema, and enforce relevant domain constraints before performing trusted calculations.

### Solution 2 — Compilation isn't a complete performance model

Modern language implementations combine parsing, translation, interpretation, runtime compilation, optimization, and native execution in different ways.

JavaScript engines commonly use JIT compilation.

The JVM can interpret and compile bytecode at runtime.

CPython commonly executes its own bytecode, while performance-sensitive libraries may use native code.

Go and Rust commonly produce native executables, but they still have runtime, library, and resource costs.

Performance depends on workload, algorithms, memory representation, I/O, optimization, and implementation quality—not one language label.

### Solution 3 — The host environment is missing the capability

The JavaScript source may be syntactically valid.

The runtime may implement the JavaScript language correctly.

But the server-side host doesn't necessarily provide the browser's document APIs.

The failure occurs because the program assumes a host capability that isn't available.

Static tooling may detect the mismatch if configured accurately, but declarations don't create missing runtime APIs.

### Solution 4 — Business invariants require appropriate coordination

Type correctness doesn't automatically prevent concurrent operations from violating shared business state.

Both requests may independently read one available room and attempt to reserve it.

The database and application must enforce the inventory invariant using appropriate transaction, locking, constraint, or atomic-update mechanisms.

The language type system is not a substitute for concurrency control over authoritative state.

### Solution 5 — The abstraction hides an execution plan

The repository method may trigger lazy loading or multiple separate queries.

The method name doesn't promise one database round trip or constant execution cost.

Inspect actual SQL logs, query counts, execution plans, and the ORM's loading configuration.

Then choose an appropriate query strategy without necessarily discarding the abstraction entirely.

### Solution 6 — Publication is not business completion

The Promise's fulfillment establishes the successful completion of the particular publishing operation according to its implementation contract.

It doesn't prove that a worker consumed the message, executed the scan, persisted findings, or marked the operation completed.

The API should represent asynchronous acceptance honestly and expose the durable scan lifecycle separately.

### Solution 7 — Match the guarantee to the enforcement mechanism

Use static types for reliable source-level relationships and states.

Use runtime validation for external values.

Use database and distributed-system mechanisms for live, concurrent business invariants.

Avoid both extremes: treating every string as interchangeable or building a type-level model so complex that it obscures the application.

The goal is meaningful correctness at a reasonable maintenance cost.

### Solution 8 — Artifact generation was mistaken for successful validation

A transformation tool can produce JavaScript without performing or enforcing the complete type-checking process.

The release pipeline should explicitly run the required type checks and fail on errors.

If using `tsc` for compilation, relevant options such as `noEmitOnError` can also prevent emitting JavaScript when type errors are reported.

The precise configuration should ensure that published artifacts satisfy the intended quality gate.

## 20. The Mental Model Worth Keeping

A programming language defines how expressions and operations behave.

Its static tooling can reject selected mistakes before execution.

Its runtime implements those semantics using actual values.

Its host environment supplies capabilities for interacting with the outside world.

And the application is responsible for validating external data and preserving business invariants.

Whenever an operation looks correct on paper but fails in production, ask:

**What did the compiler know? What did the runtime actually receive? What did the abstraction promise? What did the business require?**

Those four questions expose the boundary where the mistaken assumption entered the system.

## 21. Next Lecture — CS220-L02: JavaScript Semantics and TypeScript Reality

We've established that a language's guarantees are only as useful as our understanding of their boundaries.

Next, we'll put JavaScript and TypeScript under a microscope.

Why does JavaScript treat some values as truthy and others as falsy?

Why are two objects with identical contents not necessarily equal?

Why can a closure observe a value different from the one a developer expected?

What does `readonly` actually prevent, and what does it leave possible at runtime?

Why can asynchronous array operations complete in an unexpected order?

And how do TypeScript narrowing, strict compiler settings, and assertions interact with JavaScript's actual behavior?

The next lecture will examine these mechanisms directly.

We'll stop treating JavaScript's peculiarities as random trivia and start understanding them as consequences of a language with precise semantics.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — Make the Compiler Approve a Wrong Program

**Objective:** Observe the difference between TypeScript's static model and JavaScript's runtime values, then design a trustworthy boundary for external data.

Use Node.js and a locally installed TypeScript compiler. No external API or database is required.

### Lab A — Prepare a small project

Create a temporary project directory and install TypeScript:

```bash
mkdir cs220-l01-lab
cd cs220-l01-lab
npm init -y
npm install --save-dev typescript
npx tsc --init
```

Enable strict type checking in `tsconfig.json` if it isn't already enabled.

For this experiment, use a minimal configuration with a modern target and module settings appropriate for your installed Node.js version.

### Lab B — Make an unverified assertion

Create `quote.ts`:

```typescript
interface Quote {
  priceCents: number;
}

const externalJson = '{"priceCents":"20000"}';

const parsed = JSON.parse(externalJson) as Quote;

const totalCents = parsed.priceCents + 1200;

console.log({
  expected: 21200,
  actual: totalCents,
  runtimeType: typeof totalCents,
});
```

Compile and run the file:

```bash
npx tsc quote.ts --target es2022 --module commonjs
node quote.js
```

Observe the actual value and runtime type.

The code was accepted based on the asserted type.

The runtime value didn't satisfy that assertion.

**Question:** At which boundary did the application begin treating unverified information as trusted?

### Lab C — Inspect the emitted JavaScript

Open `quote.js`.

Find the equivalent of:

```javascript
const parsed = JSON.parse(externalJson);
```

Notice that the TypeScript interface and assertion aren't enforcing a runtime check.

The executable JavaScript contains the parsing and arithmetic operations.

**Question:** Why can't an interface declaration convert a JSON string into a numeric value?

### Lab D — Repair the boundary

Replace the assertion with a parser:

```typescript
type Quote = {
  priceCents: number;
};

function parseQuote(value: unknown): Quote {
  if (
    typeof value !== "object" ||
    value === null ||
    !("priceCents" in value)
  ) {
    throw new Error("Quote must be an object with priceCents");
  }

  const price = value.priceCents;

  if (
    typeof price !== "number" ||
    !Number.isSafeInteger(price) ||
    price < 0
  ) {
    throw new Error("priceCents must be a nonnegative safe integer");
  }

  return { priceCents: price };
}
```

Now use:

```typescript
const parsed: unknown = JSON.parse(externalJson);
const quote = parseQuote(parsed);
const totalCents = quote.priceCents + 1200;
```

With the original malformed response, validation should reject the input.

Change the JSON to contain the numeric value `20000`.

The calculation should then succeed.

**Question:** What changed in the actual execution, not merely the source-level declaration?

### Lab E — Explore structural versus semantic validity

Test these inputs against your parser:

```typescript
const examples: unknown[] = [
  { priceCents: 20000 },
  { priceCents: "20000" },
  { priceCents: -500 },
  { priceCents: 1.5 },
  { priceCents: Number.MAX_SAFE_INTEGER + 100 },
  {},
  null,
];
```

Determine which inputs should be accepted.

Then introduce a business requirement: a particular booking operation supports a maximum total amount of 100,000 cents.

Should that limit be enforced in the generic Quote parser, in a dedicated domain constructor, or at the booking-operation boundary?

Defend your choice based on the intended contract.

### Lab F — Test compiler behavior

Create a deliberate static type error:

```typescript
const amount: number = "not a number";
```

Run the compiler with and without `--noEmitOnError`, observing the generated output behavior.

Use an isolated output directory or remove old generated files first so you don't mistake stale output for newly emitted JavaScript.

**Question:** Why is a build artifact's existence not proof that type checking passed?

### Lab G — Classify failures

Consider the following problems:

1. A TypeScript file has an invalid token.
2. A function receives a string where a number is expected, and the checker catches it.
3. A server-side JavaScript program tries to access `document`.
4. A quotation service returns malformed JSON.
5. Two valid reservations are created for the same last available room.
6. An ORM performs 101 SQL queries for one page.
7. A Promise resolves after publishing a message, but the background job never completes.

For each case, identify the relevant boundary:

- Syntax and parsing.
- Static checking.
- Runtime and host environment.
- External data validation.
- Domain and transactional correctness.
- Abstraction performance.
- Asynchronous operation semantics.

Then explain which test or observation would most directly reveal the problem.

### Lab H — Write the production correction

Prepare a short engineering explanation of the original pricing incident.

Include the incorrect assumption, the actual runtime behavior, the missing validation, and the proposed prevention measures.

A complete answer should mention more than adding another TypeScript interface.

It should identify the runtime trust boundary and the tests needed to establish the real data contract.

---

## Further Reading

1. [TypeScript Handbook — The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html) — Static checking, erasure, and emitted JavaScript.
2. [TypeScript Handbook — Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html) — Types, assertions, and their limits.
3. [TypeScript Handbook — Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) — Establishing more precise types from runtime checks.
4. [MDN — JavaScript Language Overview](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Language_overview) — Core language semantics.
5. [MDN — JavaScript Execution Model](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model) — Engines, hosts, and execution.
6. [ECMAScript Language Specification](https://tc39.es/ecma262/) — Normative JavaScript language semantics.
7. [Python — Typing](https://docs.python.org/3/library/typing.html) — Static type hints in a dynamically typed language.
8. [The Twelve-Factor App — Dependencies](https://12factor.net/dependencies) — Explicit runtime dependencies and application environment assumptions.

---

## Dense Cheatsheet — Interview Glance Card

*This reference is fenced for rapid screen-based revision rather than continuous voice playback.*

```text
CS220-L01 — WHAT A PROGRAMMING LANGUAGE ACTUALLY PROMISES

FOUR CORE QUESTIONS

  What does the language specify?
  What can static tooling prove?
  What does the runtime actually execute?
  What must the application enforce?

LANGUAGE

  Syntax:
    Valid program structure

  Semantics:
    Meaning of valid operations

  Implementation:
    Machinery realizing those semantics

  Specification != particular engine implementation

TYPE CHECKING

  Static analysis before execution
  Rejects selected invalid relationships
  Works from its model of values and operations

  Type correctness != business correctness

TYPESCRIPT

  Type annotations normally erased
  Interfaces aren't runtime validators
  Type assertions don't transform input data
  `as Quote` != parse/validate Quote
  `any` weakens static checking
  `unknown` requires narrowing

  Emitting JS != type checks passed
  Configure CI and compiler quality gates explicitly

SOURCE TO EXECUTION

  Source code
      -> Parse / analyze
      -> Type check
      -> Transform / compile
      -> Execute
      -> Observe effects

  Exact pipeline varies by tooling/runtime

COMPILED VS INTERPRETED

  Compilation:
    Transform program representation

  Interpretation:
    Execute representation through interpreter

  JIT:
    Compile during execution

  AOT:
    Compile before execution

  Modern runtimes may combine strategies
  Compilation strategy != guaranteed speed

ENGINE VS HOST

  Engine:
    Implements core language semantics

  Host:
    Supplies platform APIs and environment

  Browser DOM != ECMAScript core
  Node filesystem/process APIs != ECMAScript core
  Declaration files don't install runtime APIs

EXTERNAL TRUST BOUNDARY

  JSON bytes
      -> Parse
      -> unknown
      -> Validate
      -> Normalize when appropriate
      -> Trusted domain value

  Assertion != validation
  Shape != business meaning
  Current external fact != static declaration

PRICE EXAMPLE

  Expected:
    20000 + 1200 = 21200

  Actual malformed input:
    "20000" + 1200 = "200001200"

  TypeScript assertion doesn't prevent concatenation

VALIDATION

  Structural:
    Expected properties and primitive types

  Semantic:
    Domain constraints, valid ranges, currency

  Authoritative:
    External state still satisfies invariant

BUSINESS INVARIANTS

  Correct types don't prevent:
    Double bookings
    Duplicate payments
    Invalid authorization
    Stale inventory
    Incorrect workflow transitions

  Database/distributed coordination may be required

ABSTRACTIONS

  Hide implementation details
  Should expose meaningful contracts
  May conceal:
    Extra database queries
    Network requests
    Allocation
    Retries
    Persistence semantics

  Convenience != zero cost or universal correctness

PROMISES

  Promise fulfillment means the represented
  asynchronous operation fulfilled its contract

  Queue publication != job completion
  Timeout != proof of remote rollback
  Cancellation != reversal of side effects

PARADIGMS

  Procedural:
    Sequence of actions

  Object-oriented:
    Group state and behavior

  Functional:
    Compose transformations, make effects explicit

  Declarative:
    Describe desired result, delegate execution strategy

  Paradigm labels are tools, not quality guarantees

TESTING LAYERS

  Static checks:
    Source-level relationships

  Unit tests:
    Selected local behaviors

  Contract tests:
    Producer-consumer agreement

  Integration tests:
    Real component interactions

  Property-based tests:
    Generated inputs and invariants

  Production monitoring:
    Actual behavior under real conditions

SENIOR DECISION FRAMEWORK

  1. Identify language semantics
  2. Identify static guarantees
  3. Identify runtime and host assumptions
  4. Validate external boundaries
  5. Enforce domain invariants in the right layer

FINAL MENTAL MODEL

  Source validity
      !=
  Static type correctness
      !=
  Runtime execution success
      !=
  External operation success
      !=
  Business correctness

SENIOR LINE

  "A language specifies behavior and its tooling can check
   selected properties, but the runtime executes actual values
   in a real environment. I validate data at trust boundaries,
   keep side effects explicit, and enforce business invariants
   with mechanisms capable of guaranteeing them."
```
