---
id: CS320-L03
course: CS320
title: "JavaScript and TypeScript Under the Microscope"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [CS101-S11]
prev: CS320-L02
next: CS320-L04
---




# CS320 — Operating Systems, Concurrency, and Runtimes
## Lecture 03: JavaScript and TypeScript Under the Microscope

*Coercion, equality, object identity, asynchronous mistakes, module systems, type inference, runtime guarantees, and the small language details behind surprisingly large production problems.*

**Estimated study time:** 80–100 minutes, including experiments and exercises.

---

### How to listen to this lecture

Written for continuous listening first, then for on-screen re-reading. The theme today is simple: **knowing the language ≠ knowing its syntax.** Runtime surprises — truthiness, `this`, async control flow, modules, and the boundary TypeScript cannot cross — are the point. Bold takeaways mark ideas worth pausing on. Near the end, answer the challenges **out loud** before reading the solutions. The predict-before-running experiments live after the spoken lecture ends — keep them for a screen session.

By the end, you should be able to explain why zero is not the same as missing, why object identity is not structural equality, why extracting a method can lose `this`, why `forEach` ignores async promises, how TypeScript narrowing and `satisfies` help without validating external JSON, and which guarantees sit outside the type checker.

---

# 1. The Deployment That Passed TypeScript and Broke Three Different Things

It's Thursday afternoon. Your SaaS platform has just received a modest update.

Nothing particularly dramatic.

The team has added a new payment integration, refactored a notification service, and simplified some asynchronous report-processing code.

The pull request looks respectable.

The types compile.

The tests pass.

The deployment succeeds.

Then the support tickets begin arriving.

**Problem one:** Some customers are receiving an unexpected service fee, even though their contracts explicitly specify a fee of zero.

**Problem two:** Confirmation notifications occasionally fail with an error saying that a method cannot read a property of `undefined`.

**Problem three:** The report generator sometimes announces that processing has finished even though several reports are still being generated.

Three separate bugs.

Three different parts of the application.

One shared characteristic:

**The code looks perfectly reasonable unless you understand the precise behavior of JavaScript.**

Let's examine the suspicious lines.

The fee calculation used `const fee = customer.serviceFee || defaultFee`.

The notification service extracted the method and called it unbound: `const notify = notificationService.send`, then `await notify(customer)`.

The report generator awaited inside `forEach` and then logged completion:

```typescript
reports.forEach(async report => {
  await generateReport(report);
});

console.log("All reports generated");
```

None of these snippets is particularly complicated.

An inexperienced developer might reasonably assume all three work.

An experienced developer who hasn't thought carefully about the relevant language semantics might also miss one of them during review.

And TypeScript won't necessarily rescue us.

The first line may be completely type-correct.

The second can be type-correct while failing because of `this` binding.

The third is also valid TypeScript, despite failing to wait for the asynchronous operations.

This is the kind of knowledge today's lecture is about.

We're not going to spend an hour learning how to declare variables.

You already know how to write JavaScript.

Instead, we're going to examine several of its deeper behavioral rules and the engineering consequences they produce.

The goal is not to memorize trivia.

It's to build a coherent mental model that makes these problems predictable rather than surprising.

---

# 2. Truthiness: When Zero Is Mistaken for Missing

Let's begin with the first bug: `const fee = customer.serviceFee || defaultFee`.

Suppose a customer object whose `serviceFee` is `0`, and a `defaultFee` of `15`.

What is `fee`?

It's 15. Not zero. The customer has explicitly negotiated a zero service fee, but the application charges the default.

Why?

Because the logical OR operator doesn't mean "use the value on the right if the value on the left is missing." It evaluates the left operand according to JavaScript's truthiness rules.

If the left operand is falsy, the expression returns the right operand. And zero is falsy.

## JavaScript's falsy values

Most JavaScript values are truthy. Only a relatively small collection is falsy:

- `false`
- `0`
- `-0`
- `0n`
- `""`
- `null`
- `undefined`
- `NaN`

There is also a peculiar legacy browser exception involving `document.all`, which you can safely ignore for ordinary application logic.

Everything else is truthy. `Boolean([])`, `Boolean({})`, `Boolean("false")`, and `Boolean("0")` are all `true`.

An empty array is truthy. An empty object is truthy. The string `"false"` is truthy.

JavaScript does not attempt to interpret the human meaning of the text. It follows its defined conversion rules.

## Logical OR versus nullish coalescing

Now consider `const fee = customer.serviceFee ?? defaultFee`.

This is different. The nullish coalescing operator, `??`, uses the right operand only when the left operand is `null` or `undefined`.

So `0 ?? 15` is `0`, `false ?? true` is `false`, `"" ?? "default"` is `""`, while `null ?? 15` and `undefined ?? 15` are both `15`.

For configuration values where zero, false, or an empty string are legitimate choices, `??` is often exactly what we want.

This is not merely a cleaner syntax preference. It expresses a different rule. Compare:

**`||` asks:** Is the left operand truthy?

**`??` asks:** Is the left operand neither null nor undefined?

That's the distinction.

## Optional chaining is related, but different

Consider `const city = customer.address?.city`.

The `?.` operator allows property access to stop when the value on its left is `null` or `undefined`.

It doesn't catch every possible error. For example, if `customer.address.city` is `null`, then `customer.address?.city.toUpperCase()` still throws — the city is null and the method call isn't protected. We could write `customer.address?.city?.toUpperCase()`.

Now the second optional chain protects the operation when `city` is nullish.

A common mistake is thinking that one `?.` somehow protects every later operation. It doesn't. And importantly, optional chaining doesn't validate the type of the underlying value. If `city` is the number 42, trying to call `toUpperCase()` will still fail at runtime.

## The engineering principle

Whenever you use a default value, ask:

**Does this field have a meaningful empty, zero, or false state?**

For payment fees, zero may be essential. For retry counts, zero may mean retries are disabled. For feature flags, false may be a deliberate choice. For strings, an empty string may be distinct from a missing string.

Choosing `||` instead of `??` can silently erase those distinctions. And that is a correctness problem, not a formatting issue.

---

# 3. Missing, Null, and Undefined Are Three Different Stories

Let's investigate something slightly subtler.

Imagine a REST API allowing customers to update their profiles. A customer can change their display name, phone number, and language preference.

Now compare these three requests.

**Request A:** an empty JSON object `{}`.

**Request B:** `{ "phoneNumber": null }`.

**Request C:** `{ "phoneNumber": "" }`.

Should the backend treat these requests identically?

Probably not.

A reasonable contract might define:

- Missing property: leave the existing value unchanged.
- `null`: explicitly clear the stored phone number.
- Empty string: reject it, or treat it according to an explicitly defined validation rule.

The distinction matters because we're representing different user intentions. Now consider two JavaScript objects: `a = {}` and `b = { phoneNumber: undefined }`.

Reading the property produces the same result — both `a.phoneNumber` and `b.phoneNumber` are `undefined`.

But are the objects identical in terms of property presence?

No. `Object.hasOwn(a, "phoneNumber")` is `false`; `Object.hasOwn(b, "phoneNumber")` is `true`.

The second object explicitly contains a property whose value is undefined. The first object doesn't contain the property at all.

And `"phoneNumber" in a` is `false`, while `"phoneNumber" in b` is `true`.

The `in` operator also detects property presence, but unlike `Object.hasOwn`, it includes inherited properties.

## Serialization changes the picture

Now serialize both objects: `JSON.stringify(a)` and `JSON.stringify(b)` both become `"{}"`.

Both become the same JSON. The distinction between absent and explicitly undefined has disappeared.

We encountered information loss in CS110-L02. Here it returns in a very practical form.

JavaScript supports `undefined`. JSON does not have an `undefined` value.

## The TypeScript connection

Consider an interface `ProfilePatch` with an optional `phoneNumber?: string`.

The question mark makes the property optional. With TypeScript's `exactOptionalPropertyTypes` enabled, the type more precisely expresses that `phoneNumber` can be absent or contain a string.

It doesn't automatically permit assigning explicit `undefined` unless the type includes it. That's useful because property absence and an explicitly present undefined value are not always semantically equivalent.

For our PATCH request, we might instead use `phoneNumber?: string | null` on that interface.

Now we have:

- Absent: unchanged.
- String: set a new number.
- Null: clear the number.

At runtime, we still need to validate incoming JSON. But the type better expresses the intended contract.

## Why `Partial<T>` can be dangerous

TypeScript provides a utility type, `Partial<User>`.

It makes all properties of `User` optional. But imagine using it as your entire update contract.

Your domain object contains:

- Customer ID.
- Email address.
- Subscription plan.
- Account status.
- Creation timestamp.
- Billing balance.

Should a generic profile-update endpoint allow arbitrary changes to all these fields?

Of course not.

A type that is convenient to generate isn't necessarily the correct representation of a business operation. For a serious application, a dedicated update type is usually more appropriate — for example `UpdateProfileRequest` with optional `displayName`, `phoneNumber` as `string | null`, and `language` constrained to `"en" | "lt" | "de"`.

This describes what the operation permits. Not merely what fields happen to exist on the database entity.

**Types should model business permissions and intentions, not just object shapes.**

---

# 4. Equality: Two Identical Objects That Aren't Equal

Let's move to another familiar JavaScript behavior. Consider two separately created objects `a` and `b`, each with `hotelId: "H-142"` and `roomId: "R-101"`. Comparing with `a === b` yields `false`.

The objects contain the same properties and values. But they are different objects. JavaScript compares ordinary objects by identity, not structural equality.

Now consider `const c = a`. Then `a === c` is `true` — both bindings refer to the same object. But it has consequences that are easy to overlook.

## The duplicate booking object

Suppose you use a Set to eliminate duplicate reservations, adding two separately created objects that both have `id: "R-101"`.

`reservations.size` is `2`.

Why?

Because the objects have different identities. The Set doesn't automatically compare their `id` fields. If your goal is deduplication by reservation ID, you need to encode that criterion.

For example, build a `Map` keyed by `reservation.id` from the incoming list.

Now records with the same ID map to the same key.

## Strict equality isn't the entire story

JavaScript has several related equality mechanisms. `===` performs strict equality without general type coercion.

So `0 === false` is `false`, and `"5" === 5` is `false`.

That's why strict equality is generally preferred for ordinary application comparisons. But there are edge cases. `NaN === NaN` is `false`, while `0 === -0` is `true`.

JavaScript also provides `Object.is`: `Object.is(NaN, NaN)` is `true`, and `Object.is(0, -0)` is `false`.

`Object.is()` uses a slightly different equality algorithm. Meanwhile, Map and Set use a comparison rule known as *SameValueZero* for key equality. This treats `NaN` as equal to itself and zero as equal to negative zero.

Do you need to memorize every formal equality algorithm for an ordinary senior full-stack interview?

Probably not. But you should understand that equality is defined by a particular operation, and different operations can have slightly different semantics.

Most importantly, **object equality doesn't automatically mean domain equality**.

Two separately loaded database records may represent the same customer. A Map containing those object references won't treat them as the same key merely because their fields match. Use stable domain identifiers when that's the identity rule your application requires.

---

# 5. The Clone That Wasn't Actually Independent

Here's a particularly common source of bugs in frontend applications. Suppose you have a reservation object with nested `guest` and `preferences` — id `R-101`, guest name Anna, breakfast preferred.

You want to create an editable copy. A developer writes a shallow spread: `const draft = { ...reservation }`.

Then: `draft.guest.name = "Maria"`.

What happens to the original reservation?

Its guest name also changes.

Why?

Because object spread performs a **shallow copy**. It copies the top-level properties into a new object. But nested objects remain references to the original nested objects.

Conceptually, both outer objects point at the same nested guest:

```text
reservation ──→ original object
                    |
                    └── guest ──→ guest object
                                      ^
                                      |
draft ────────→ new object ──────────┘
```

The two outer objects are distinct. But they still share the nested guest object.

## Why this matters in Vue applications

Reactive frontend systems make state changes particularly visible. If a component creates what it believes is an independent draft but accidentally shares nested state with the original, editing a form can mutate authoritative UI state before the user presses Save.

Then Cancel doesn't actually cancel. The original state has already changed.

The bug is not necessarily in Vue's reactivity. It's in the application's object ownership and copying assumptions.

## `structuredClone()`

Modern JavaScript provides `structuredClone(reservation)`.

For supported values, this creates a deep clone using the structured clone algorithm. Now the nested guest object is separate.

But `structuredClone()` isn't a universal magic copier.

It cannot clone functions. It doesn't preserve every aspect of arbitrary class instances, prototypes, or property descriptors.

And large deep copies have performance and memory costs. You shouldn't deep-clone an enormous application state tree every time one field changes unless the design actually requires it.

## Immutable update patterns

Another approach is to create new objects only along the path being changed — spread the reservation, then spread `guest` with the new name.

Now the outer reservation object and nested guest object are new. The unchanged preferences object may remain shared. That's safe if we treat the shared object as immutable.

This style is often called a **structural-sharing immutable update**.

The key idea is that sharing references isn't inherently bad. It's dangerous when different parts of the application assume they own the same mutable object independently.

**Object identity, ownership, and mutation policy are architectural concerns, not merely JavaScript trivia.**

---

# 6. `this`: The Hidden Argument That Can Disappear

Now let's investigate our second production bug. The notification service is a class whose `send` method uses `this.provider.sendEmail(customer.email)`.

The service works when you call `await notificationService.send(customer)`.

But after a refactor, someone writes `const notify = notificationService.send` and then `await notify(customer)`.

And suddenly the application crashes.

Why?

Because JavaScript's `this` binding depends on how an ordinary function is invoked.

When you call `notificationService.send(customer)`, the method call supplies the service object as `this`. But when you extract the function into `notify` and invoke `notify(customer)`, you've lost the method-call receiver. Class methods execute in strict mode, so `this` will be undefined when invoked as an ordinary unbound function.

Then `this.provider` fails.

## `this` isn't the same as a closure

A closure retains variables from **where the function was defined**. An ordinary method's `this` depends on **how the function is called**. Extract `notificationService.send` and you keep the function body, but you lose the receiver — that is a `this` problem, not a missing lexical binding. Bind the method, wrap the call, or use an arrow that inherits `this` lexically when that is what you intend.

## Binding the method

One solution is `notificationService.send.bind(notificationService)`. The `bind()` method creates a function with a fixed `this` binding, so `await notify(customer)` works.

Another solution is a wrapper: `(customer) => notificationService.send(customer)`. The wrapper invokes the method through the original service object, preserving the expected receiver.

## Arrow functions behave differently

Arrow functions don't create their own `this` binding. They inherit `this` lexically from the surrounding context. For example, a class-field arrow `send = async (customer) => { await this.provider.sendEmail(customer.email); }` is created with the instance's `this` context. Extracting it doesn't lose that binding in the same way. But there's a trade-off.

Ordinary class methods are typically shared through the prototype. An arrow function defined as an instance field creates a function associated with each instance.

You don't need to use arrow fields for every class method. You need to understand when binding matters.

## The interview version

If an interviewer asks: "What's the difference between arrow functions and ordinary functions?"

A weak answer is: "Arrow functions are shorter."

A stronger answer discusses:

- Lexical versus call-site `this`.
- Constructors and `new`.
- The absence of an ordinary arrow function's own `arguments`.
- Callback behavior.
- Method binding.
- The practical consequences of these distinctions.

---

# 7. Classes Are Built on JavaScript's Prototype System

Here's something worth remembering when working with TypeScript classes. JavaScript's object model is fundamentally prototype-based. The `class` syntax provides a convenient way to define constructors and prototype-based methods, along with modern class features.

Consider a `Reservation` class with `id`, `hotelId`, and a `describe()` method that returns a short string.

Create two instances — `a` and `b` — with different ids. Both can call `describe()`. But an ordinary method isn't usually copied as an independent function onto every instance. It's found through the prototype chain.

We can observe that `Object.getPrototypeOf(a) === Reservation.prototype` is `true`.

And the ordinary `describe` method is on `Reservation.prototype`. This is useful because instances can share method implementations.

## How property lookup works

When you access `a.describe`, JavaScript first looks for an own property named `describe` on `a`. If it doesn't find one, it can continue searching through the prototype chain. Eventually, it finds the method on `Reservation.prototype`.

This is prototype delegation.

## Why knowing this matters

Most of the time, you can happily use classes without thinking about prototypes. But prototypes help explain:

- Inherited properties.
- Method sharing.
- How `instanceof` generally works.
- Why `Object.hasOwn()` differs from the `in` operator.
- Why extracted methods can lose their receiver.
- Why `Object.create(null)` produces an object without the ordinary Object prototype.

This is also relevant to security. If application logic blindly treats inherited properties as trusted own data, it can behave unexpectedly. And prototype pollution vulnerabilities exploit unsafe handling of object properties and prototype-related mechanisms.

You don't need to turn today's lecture into a JavaScript engine course. But understanding that JavaScript classes sit on a prototype-based object model gives you a much more coherent picture of how objects work.

---

# 8. Async Arrays: The Code That Finished Before It Started

Now for our third production bug.

The developer wrote an async callback inside `reports.forEach`, awaited `generateReport` inside it, then logged `"All reports generated"`.

The intention was obvious: process each report, wait for generation to finish, then announce completion.

But that's not what happens.

Why?

Because `forEach()` does not wait for asynchronous callbacks. It invokes the callback for each array element and ignores the promises returned by those callbacks. The method itself returns `undefined`.

So the surrounding code continues without waiting for the report-generation operations to complete. And failures inside those asynchronous callbacks may become unhandled promise rejections unless they're dealt with separately.

## Three different intentions

Let's distinguish three possible requirements.

### Requirement A: Process reports sequentially

Perhaps generating a report modifies shared state. Or perhaps the external provider only permits one operation at a time.

Use a `for...of` loop with `await generateReport(report)` inside.

Each operation completes before the next begins. Simple. Predictable. Potentially slow when operations are independent and mostly waiting on I/O.

### Requirement B: Process all reports concurrently

Suppose the operations are independent and the number of reports is small enough for the available capacity.

Use `await Promise.all(reports.map(report => generateReport(report)))`.

The `map()` operation creates an array of promises. `Promise.all()` waits until every promise fulfills, or rejects when one rejects.

Remember from CS320-L01: rejection doesn't automatically cancel the other operations. This approach is appropriate only when the concurrency is acceptable and the failure semantics make sense.

### Requirement C: Continue even when individual reports fail

Suppose one broken report shouldn't prevent the others from completing. You could use `await Promise.allSettled(reports.map(report => generateReport(report)))`.

Now you receive an outcome for every operation. You can inspect failures individually.

But `allSettled()` doesn't magically make the workload safe. It still initiates the operations without imposing a concurrency limit. For thousands of reports, a bounded worker pool may be more appropriate.

## The conceptual lesson

Array methods such as `map()`, `filter()`, and `forEach()` operate according to their defined synchronous iteration semantics.

Passing an asynchronous callback doesn't automatically turn the array method into an asynchronous control-flow construct. An `async` callback returns a promise. The caller must decide whether and how to await that promise.

An experienced JavaScript developer should recognize this immediately during code review, and it matters far more than obscure language trivia.

---

# 9. Errors and Promises: The Exception That Escaped the Catch

Let's explore another subtle asynchronous issue.

Consider an async `loadCustomer` that `return`s `fetchCustomerFromProvider()` inside a `try`, catching errors to log and return `null`.

At first glance, it looks reasonable. If something goes wrong, it catches the error and returns null.

But there's a subtle problem. Suppose `fetchCustomerFromProvider()` returns a promise that later rejects.

Does the `catch` block necessarily handle that rejection?

No.

The function returns the promise from inside the `try` block without awaiting its settlement there. The asynchronous rejection occurs after control has left the synchronous `try` statement. The surrounding async function adopts the returned promise's rejected state, but the local catch block isn't invoked for that later rejection.

Now consider the same function with `return await fetchCustomerFromProvider()` inside the `try`.

Here, the awaited rejection is raised within the async function's `try` context. The catch block can handle it.

This is one reason `return await` is not always redundant. Modern JavaScript runtimes handle `return await` efficiently, and its behavior can matter for local error handling and cleanup.

## But should every error become null?

Not necessarily.

Imagine `fetchCustomerFromProvider()` fails because authentication credentials expired. Returning `null` may make the caller believe the customer doesn't exist. Those are different outcomes.

A robust service might distinguish:

- Customer not found.
- Temporary provider failure.
- Authentication failure.
- Invalid provider response.
- Operation cancelled.
- Internal programming error.

Swallowing every exception and returning a neutral-looking value can hide serious system problems. This is where domain-specific error modeling becomes useful.

## An explicit result type

For example, a discriminated union `CustomerLookupResult` with statuses `found` (carrying a customer), `not_found`, and `temporarily_unavailable` (optional `retryAfterMs`).

Now the caller must confront the distinction. It cannot casually treat a network outage as proof that the customer doesn't exist without explicitly choosing to do so.

This is particularly valuable in systems involving external integrations and AI agents. An AI tool returning "customer not found" when the underlying database actually timed out can lead the agent to make incorrect decisions.

Correct error semantics matter.

## `finally` and cleanup

Consider acquiring a connection, then `try { return await performQuery(connection); } finally { connection.release(); }`.

The `finally` block executes when control leaves the `try`, including through normal completion or an error. This is useful for releasing resources.

However, `finally` doesn't magically guarantee cleanup under process termination, crashes, or other failures outside the program's normal execution. For database connections, locks, files, and streams, explicit lifecycle management remains important. This connects directly to the memory-management and operating-system sessions.

---

# 10. JavaScript Modules: What Happens When Files Depend on Each Other?

Let's move from individual language expressions to application structure. A modern Node.js or frontend project may contain hundreds or thousands of modules.

Services import repositories. Repositories import types. Components import utilities. Utilities import configuration. Configuration imports other modules.

What could go wrong?

Quite a lot, actually. To understand why, we need to distinguish **module loading, module evaluation, and module state**.

## ECMAScript modules

Consider a `config.mjs` that exports a live `currency` binding starting as `"EUR"` and a `changeCurrency` function that reassigns it. A `main.mjs` imports both, logs `currency` (EUR), calls `changeCurrency("USD")`, and logs again (USD).

The imported binding is **live**. It reflects updates made to the exported binding by its defining module. This differs from imagining that every import simply receives a disconnected snapshot of the exported variable's value.

However, the importing module cannot directly reassign the imported binding. The exporting module controls that binding.

## Module initialization

Modules aren't simply pasted into one enormous source file and executed randomly. The runtime establishes dependencies and evaluates modules according to module-system rules.

This becomes interesting when modules depend on one another cyclically.

## Circular dependencies

Imagine:

`reservations.mjs` imports `payments.mjs`. And `payments.mjs` imports `reservations.mjs`. Now each module depends on the other.

Cycles are permitted in ECMAScript modules. But accessing an imported binding before its initialization can produce a runtime error. For example, consider two files. `a.mjs` imports `./b.mjs` and then exports `const settings = { currency: "EUR" }`. `b.mjs` imports `{ settings }` from `./a.mjs` and immediately logs `settings.currency`.

If you execute `a.mjs` as the entry module, the evaluation of `b.mjs` attempts to access `settings` before `a.mjs` has initialized it. That produces a `ReferenceError`.

The problem is not that JavaScript fundamentally forbids circular imports.

Some circular dependencies work perfectly well when access to the imported value happens only after initialization. Others create subtle startup failures.

## Why circular dependencies matter architecturally

Imagine a codebase where:

- BookingService imports PaymentService.
- PaymentService imports NotificationService.
- NotificationService imports BookingService.

Even if the runtime handles the cycle, the architecture may be signaling excessive coupling.

Which service owns the relevant business operations?

Where should the shared interfaces live?

Can the dependencies be reorganized around clearer boundaries?

Circular imports are sometimes harmless, but architecturally they deserve investigation.

## CommonJS versus ESM

Node.js has historically supported CommonJS, using `const service = require("./service")`.

Modern JavaScript also has standard ECMAScript modules, using `import { service } from "./service.js"`.

Both systems remain relevant in Node.js ecosystems. They differ in loading and evaluation semantics, export behavior, interoperability, and certain tooling expectations. CommonJS uses `require()` and `module.exports`. ESM uses `import` and `export`, with static imports, live bindings, and standardized module semantics.

You don't need to memorize every interop corner case. But you should understand the module system your project uses and how your build tools resolve dependencies. Especially when debugging:

- Import errors.
- Circular dependencies.
- Test mocking.
- Duplicate module instances.
- Build configuration.
- Startup side effects.
- Server versus browser module compatibility.

## The module-level singleton trap

Consider `export const sessionCache = new Map()`.

Within one ordinary module instance, imports can share access to this Map. That's convenient. But suppose you run four Node.js processes.

Do they share the same Map?

No.

Each process has its own memory and module instances. Now you're back to the process-isolation concepts from CS320-L02.

A module-level singleton is not a distributed singleton. And a global variable is not a substitute for shared durable state.

---

# 11. TypeScript's Most Useful Trick: Narrowing What You Know

Let's return to TypeScript.

The goal of a type system isn't merely to annotate variables. Its deeper value is helping us express and maintain knowledge about program values.

Consider a `describe` function on `string | number` that checks `typeof value === "string"` before calling `toUpperCase()`, otherwise `toFixed(2)`:

```typescript
function describe(value: string | number) {
  if (typeof value === "string") {
    return value.toUpperCase();
  }

  return value.toFixed(2);
}
```

TypeScript understands that the `typeof` check divides the possible values into two cases. Inside the first branch, `value` is a string. In the remaining branch, it's a number.

This is called **type narrowing**. The compiler uses control flow and conditions to refine its knowledge about a value.

This becomes particularly powerful with discriminated unions.

## Modeling a workflow

Imagine an agent that can process customer requests. Its state might be a discriminated union on `status` — `idle`, `running` (with `taskId` and `startedAt`), `waiting_for_approval` (with `proposedAction`), `completed` (with `result`), and `failed` (with `error`):

```typescript
type AgentState =
  | {
      status: "idle";
    }
  | {
      status: "running";
      taskId: string;
      startedAt: number;
    }
  | {
      status: "waiting_for_approval";
      taskId: string;
      proposedAction: string;
    }
  | {
      status: "completed";
      taskId: string;
      result: string;
    }
  | {
      status: "failed";
      taskId: string;
      error: string;
    };
```

Notice what we've achieved.

A completed task must contain a result. A failed task must contain an error. A state waiting for approval must describe the proposed action. A running state must identify the task. These relationships are part of the type.

Now consider a `describeAgent` switch on `state.status` that returns a string for each case — idle, running, waiting for approval, completed, or failed:

```typescript
function describeAgent(state: AgentState): string {
  switch (state.status) {
    case "idle":
      return "No active task";

    case "running":
      return `Running ${state.taskId}`;

    case "waiting_for_approval":
      return `Approval required: ${state.proposedAction}`;

    case "completed":
      return `Completed: ${state.result}`;

    case "failed":
      return `Failed: ${state.error}`;
  }
}
```

TypeScript narrows each branch according to `status`. This is much safer than one enormous interface containing a dozen optional properties.

## Exhaustiveness checking

Now imagine adding a `CancelledState` with `status: "cancelled"`, a `taskId`, and a `reason`.

You update the union to include it. But the switch statement doesn't handle cancellation.

Can TypeScript help detect that omission?

Yes. One technique uses the special type `never`. Define `assertNever(value: never): never` to throw on an unexpected state, then put `return assertNever(state)` in the switch's `default` branch after handling idle, running, waiting for approval, completed, and failed.

As long as every possible union member is handled, TypeScript can determine that the default branch's `state` has type `never`. If you introduce a new state without handling it, the type checker can report an error.

That's a meaningful guarantee. It lets your domain model influence the compiler's ability to detect incomplete code.

---

# 12. `satisfies`: Checking a Contract Without Throwing Away Inference

Here's another TypeScript feature worth knowing. Suppose you define route names `home`, `reservations`, and `settings`, each requiring a `path` and `requiresAuth`.

You could annotate `const routes: Record<RouteName, RouteDefinition> = { ... }` with home at `/` (no auth) and the others requiring auth.

This validates the structure. But the explicit type annotation can widen some information about the individual values.

Sometimes we want to verify that an expression satisfies a contract while preserving more precise inferred information about the expression. That's what the `satisfies` operator is for — write the same routes object, then `satisfies Record<RouteName, RouteDefinition>`.

The compiler checks compatibility with the required structure. But the expression retains its own inferred type. This can be useful for:

- Configuration objects.
- Route maps.
- Feature definitions.
- Event maps.
- Command registries.
- API handler tables.

## The distinction between three TypeScript constructs

Consider three constructs. `const value: SomeType = expression` declares a variable with a particular type and checks assignability. `const value = expression as SomeType` is a type assertion — it tells the compiler to treat the expression as the asserted type, subject to the language's assertion rules. And `const value = expression satisfies SomeType` verifies compatibility while retaining the expression's inferred type.

These constructs solve different problems. And none performs runtime validation of arbitrary external JSON.

---

# 13. Strict TypeScript: The Settings That Reveal Hidden Assumptions

You may have encountered TypeScript projects with very different levels of strictness. One project compiles almost anything. Another complains about every possibly missing property and unsafe operation.

Some developers respond by adding assertions until the compiler becomes quiet. That's usually the wrong approach. A strict type checker can reveal assumptions that deserve examination.

## `strictNullChecks`

This setting distinguishes nullable values more carefully. If a function might return undefined, the compiler can require you to handle that possibility.

For example, `customers.find(c => c.id === requestedId)` may be undefined. Calling `customer.email` without establishing that a customer was found should produce a type error under appropriate strict checking. The compiler is asking a legitimate question.

What happens when the customer doesn't exist?

Don't silence it with `customer!.email` unless you have a real reason to guarantee that the value exists. The non-null assertion removes the compile-time warning. It doesn't change the runtime value.

## `noUncheckedIndexedAccess`

Consider `const prices: number[] = [10, 20, 30]` and then `const price = prices[100]`.

At runtime, the result is undefined. But without stricter indexed-access checks, TypeScript may treat array indexing as returning the element type.

With `noUncheckedIndexedAccess`, indexed access can include `undefined` in the resulting type. This more closely reflects the possibility that the requested element doesn't exist.

The setting can make code more verbose. But it catches a real category of assumptions.

## `exactOptionalPropertyTypes`

Covered earlier: it makes optional properties behave more precisely in static assignments. A property that may be absent isn't necessarily one that may explicitly contain `undefined`. This matters for PATCH contracts, configuration objects, and other structures where presence carries meaning.

## The practical philosophy

I wouldn't recommend enabling every obscure compiler option merely to prove intellectual seriousness. But `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes` are worth understanding and evaluating for serious TypeScript projects.

The deeper point is this:

**A type-checking warning often reveals an assumption about the program.**

Sometimes that assumption is safe. Sometimes the type definitions are inadequate. Sometimes the compiler cannot express a guarantee you've established elsewhere. And sometimes the warning exposes a real bug.

A good developer investigates which case applies instead of automatically silencing the compiler.

---

# 14. The Boundary That TypeScript Cannot Cross

Let's finish the theoretical portion with perhaps the most important distinction in modern TypeScript engineering. Imagine your backend receives a refund JSON body — action `refund`, amount `5000`, currency `EUR`, approved `true`:

```json
{
  "action": "refund",
  "amount": 5000,
  "currency": "EUR",
  "approved": true
}
```

You define a matching `RefundRequest` interface with those fields and types.

Excellent. Now the compiler knows how the object is supposed to look.

But what does `approved: true` actually mean?

Who approved it?

Was the approval issued by an authorized person?

Is it still valid?

Does it apply to this refund?

Could the client have invented the field?

A type system cannot answer those questions.

Runtime validation can establish that `approved` is a boolean. Authorization logic must establish whether the action is permitted. Business logic must enforce refund limits and transaction state.

The database may need to enforce consistency. The payment provider may require idempotency. Logging and auditing may be needed to reconstruct what happened.

These are different guarantees. Let's organize them as a spoken stack:

- **TypeScript** — static compatibility and relationships under its assumptions.
- **Runtime validation** — actual incoming values satisfy a defined schema.
- **Domain logic** — business rules and state transitions are valid.
- **Authorization** — the actor is permitted to perform the operation.
- **Database constraints** — selected persistent-data invariants are enforced.
- **Transactions** — coordinated state changes satisfy transactional guarantees.
- **External integrations** — only the guarantees actually provided by those services.
- **Tests and monitoring** — evidence about behavior, including failures and regressions.

A mature application combines these layers. No single one replaces the others.

This is why saying "the code is type-safe" is not the same as saying "the system is correct." And it's why a senior engineer needs to understand both language semantics and architecture.

The language helps you express a system. It doesn't eliminate the need to design one.

---

# 15. The Oral Examination

We now have enough of the language's precise behavior to talk about production bugs like an engineer rather than hoping TypeScript would have caught them.

Before reading the solutions, try answering these questions out loud. Imagine that a senior engineer is interviewing you and will challenge any hand-waving. Speak complete explanations, not fragments.

### Challenge A — The Broken Configuration System

*Suggested time: 10 minutes.*

Your application loads configuration values from several sources.

Some fields can legitimately contain zero or false.

Some can be absent.

Some can explicitly contain null.

A developer writes `const retries = config.retries || 3`, `const enabled = config.enabled || true`, and `const timeout = config.timeout ?? 5000`.

Identify the problematic assumptions.

How would you model the configuration contract?

What should happen if an environment variable contains the string `"false"`?

Would TypeScript's static types be enough to validate environment variables?

### Challenge B — The Unreliable Report Processor

*Suggested time: 10 minutes.*

A service processes 10,000 reports.

Each report requires an external API call.

The provider permits 25 concurrent requests.

The developer writes `await Promise.all(reports.map(generateReport))`.

What problems might this create?

How would you design bounded concurrency?

What would you do if individual reports fail?

How would you distinguish a retryable network failure from a permanent validation error?

What should the service record to support recovery after a process crash?

### Challenge C — The Dangerous State Model

*Suggested time: 10 minutes.*

You inherit a `Payment` interface with a free-form `status: string` and optional `transactionId`, `error`, and `refundedAt` fields:

```typescript
interface Payment {
  status: string;
  transactionId?: string;
  error?: string;
  refundedAt?: string;
}
```

The application handles:

- Pending payments.
- Authorized payments.
- Captured payments.
- Failed payments.
- Refunded payments.

What invalid or ambiguous states does this interface permit?

How would you improve the model?

Would you use a discriminated union?

Which guarantees could TypeScript enforce?

Which rules still require runtime or database validation?

### Challenge D — The Circular Dependency

*Suggested time: 8 minutes.*

An application has three services:

- ReservationService.
- PaymentService.
- NotificationService.

Each imports another, eventually creating a cycle.

Sometimes the application starts successfully.

After a refactor, initialization fails because a dependency is accessed before it is ready.

What might be happening at the module level?

Would replacing ESM with CommonJS necessarily solve the architectural problem?

How would you reorganize the dependencies?

Could a shared domain interface, event boundary, or separate orchestration service simplify the design?

---

# 16. Solutions and Discussion

*Read this section after answering out loud. The coding lab appears after the spoken lecture ends.*

### Solution A — Configuration

Using `||` for retries makes an explicit zero fall back to three. Using `||` for enabled makes an explicit false become true.

The timeout expression using `??` preserves zero, although whether zero is valid depends on the domain.

Environment variables are strings. The string `"false"` is truthy. A configuration parser should explicitly interpret and validate environment values.

TypeScript types don't automatically validate runtime environment variables.

### Solution B — Report processing

An unbounded `Promise.all()` can initiate far more work than the provider permits. A bounded worker pool or semaphore can restrict concurrent operations to an appropriate level.

Failures should be classified according to whether they are retryable. The system should record durable job state, progress, and retry information where recovery is required. Process restarts must not silently lose completed work or cause unsafe duplicate side effects.

### Solution C — Payment states

The original interface permits many invalid combinations. For example:

- A pending payment with a transaction ID and an unrelated error.
- A failed payment containing a refund timestamp.
- A captured payment without a transaction ID.
- An arbitrary status string that the application doesn't recognize.

A discriminated union can represent valid shapes more precisely. But runtime validation, authorization, transaction rules, and database constraints are still needed to enforce business correctness.

### Solution D — Circular dependencies

Cyclic module imports can cause initialization-order problems when values are accessed before they're initialized. Changing module systems doesn't automatically remove the dependency cycle.

The architectural solution may involve separating shared domain concepts, reducing bidirectional dependencies, or introducing a coordinating service. Events can reduce direct coupling in some designs, but they also introduce their own complexity and consistency considerations.

The goal is to establish clear ownership and dependency direction.

---

# 17. The Mental Model Worth Keeping

Three production bugs: a zero fee treated as absence (`||` vs `??`); a notification method that lost `this`; a `forEach` that ignored async promises. No advanced algorithms — ordinary language misunderstandings.

Remember these durable distinctions:

**Truthiness is not absence** — zero, false, and empty string can be legitimate values; prefer `??` when nullish is the only missing case.

**Missing, `undefined`, and `null` can mean different things** — property presence, PATCH semantics, and JSON serialization each tell a different story.

**Identity is not structural equality** — Sets and Maps key by SameValueZero on references unless you encode domain IDs yourself.

**Copies need an ownership model** — shallow spread shares nested objects; mutation policy is architecture, not trivia.

**Method `this` depends on invocation** — extract a method and you may keep the body while losing the receiver.

**Classes sit on prototypes** — ordinary methods are shared; lookup walks the chain.

**Sync collection methods don't await callbacks** — an `async` callback returns a promise the caller must compose.

**Promise settlement and control flow decide error handling** — `return` versus `return await` inside `try` is not always redundant.

**Modules have initialization semantics** — live bindings and cycles can fail at startup without forbidding the import graph.

**TypeScript narrows and documents; it doesn't validate external data** — assertions aren't checks; correctness stacks types, runtime validation, domain rules, auth, database constraints, transactions, and tests.

> **The master sticky note**
>
> Knowing JavaScript's syntax is not the same as knowing what the language guarantees — and designing for real values, timing, and failure.

Syntax becomes automatic long before you own a mental model. Friendly JavaScript can hide shared mutable references, lost `this`, ignored promises, type assertions over invalid values, circular imports, and zero-as-default traps. None of that is random — all of it follows the rules.

AI writes fluent TypeScript. **Syntactic fluency isn't correct semantics.** The engineer's job is knowing what the language guarantees and designing for real values, timing, and failure.

You now have the vocabulary of concurrency, operating systems, and the runtime surprises that sit beneath everyday JavaScript and TypeScript. CS320 continues with focused operating-system and runtime deep dives.

---

# 18. Next Lecture — Scheduling, CPU Time, and Contention

In **CS320-L04**, we'll examine why a machine with spare average CPU can still leave one worker starved — scheduling queues, contention, quotas, and wall-clock time versus CPU time.

After the expanded CS320 sequence, the recommended study-order next course remains **SE240 — Frontend Engineering**. The browser is where many of today's lessons become visible in UI state, event timing, and the cost of careless copies. If your next focus is durable data rather than the UI surface, **CS330** is a natural data-path alternative. See the recommended study order in `README.md`.

---

## Optional Practical Lab — Predict Before Running

*The spoken lecture ends here. The remaining material is a screen-first investigation worksheet.*

These experiments are short, but they touch several important semantics.

Use Node.js, the browser console, or TypeScript Playground as appropriate.

**Suggested time: 15–20 minutes.**

> **Gym rules:** predict before you run. The oral challenges were in the spoken lecture; these labs are for your own eyes.

### Experiment A — Truthiness

Predict the results of these comparisons — `||` versus `??`, empty collections in conditionals, and `Boolean("false")`:

```javascript
console.log(0 || 99);
console.log(0 ?? 99);

console.log("" || "default");
console.log("" ?? "default");

console.log([] ? "yes" : "no");
console.log({} ? "yes" : "no");

console.log(Boolean("false"));
```

Which results correspond to business values that could be legitimate rather than missing?

### Experiment B — Equality

Predict identity versus structure, `NaN` equality, and how many entries a Set holds when you add `a`, a separately created twin `b`, and alias `c = a`:

```javascript
const a = { id: 1 };
const b = { id: 1 };
const c = a;

console.log(a === b);
console.log(a === c);

console.log(NaN === NaN);
console.log(Object.is(NaN, NaN));

const set = new Set([a, b, c]);

console.log(set.size);
```

Why does the Set contain the number of entries it does?

### Experiment C — Shallow copying

Predict what happens to the original after a shallow spread mutates nested state:

```javascript
const original = {
  guest: {
    name: "Anna"
  }
};

const draft = { ...original };

draft.guest.name = "Maria";

console.log(original.guest.name);
```

Now replace the shallow copy with `const draft = structuredClone(original)`.

What changes?

### Experiment D — Asynchronous iteration

Predict the order of these messages — especially whether `"Finished"` waits for the async callbacks:

```javascript
const sleep = ms =>
  new Promise(resolve => setTimeout(resolve, ms));

[1, 2, 3].forEach(async number => {
  await sleep(100);
  console.log("Processed", number);
});

console.log("Finished");
```

Now rewrite it once for sequential execution and once for concurrent execution with proper waiting.

### Experiment E — TypeScript and runtime reality

Consider this assertion from `unknown` to a `Customer` whose `id` is typed as a number, while the raw value carries `id: "42"`:

```typescript
interface Customer {
  id: number;
}

const raw: unknown = {
  id: "42"
};

const customer = raw as Customer;

console.log(customer.id.toFixed(0));
```

Does the compiler accept it?

Does the type assertion convert the string?

What happens at runtime?

How would you validate the input properly?

### Lab solutions

*Read after attempting the experiments.*

**Experiment A — Truthiness.** `0 || 99` is `99`; `0 ?? 99` is `0`. `"" || "default"` is `"default"`; `"" ?? "default"` is `""`. Empty arrays and objects are truthy, so both conditionals print `"yes"`. `Boolean("false")` is `true`. The practical danger is assuming falsy values mean missing values — for many domain fields, zero and false are perfectly valid.

**Experiment B — Equality.** The two separately created objects have different identities; `c` aliases `a`. So `a === b` is `false` and `a === c` is `true`. `NaN === NaN` is `false`, but `Object.is(NaN, NaN)` is `true`. The Set size is `2` because `a` and `c` are the same object while `b` is separate.

**Experiment C — Shallow copying.** The shallow copy shares the nested guest object, so mutating `draft.guest.name` changes what the original observes. `structuredClone()` creates a separate nested object for this supported data structure.

**Experiment D — Async iteration.** `"Finished"` appears before the asynchronous callbacks finish. `forEach()` doesn't await the promises returned by async callbacks. Sequential processing uses `for...of` with `await`. Concurrent processing uses an appropriate promise-composition mechanism such as `Promise.all()`, with explicit concurrency limits when necessary.

**Experiment E — Runtime type assertions.** The assertion doesn't convert `"42"` into a number. The runtime value remains a string. Calling `toFixed()` throws. A correct solution validates the external value and either rejects it or performs an explicitly permitted conversion.

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS320-L03  JS/TS UNDER THE MICROSCOPE — INTERVIEW GLANCE CARD

TRUTHINESS / DEFAULTS
  Falsy: false, 0, -0, 0n, "", null, undefined, NaN (else truthy)
  [] {} "false" "0" are truthy
  ||  uses truthiness → 0||15 → 15 (erases legitimate zero/false/"")
  ??  only null/undefined → 0??15 → 0
  ?. stops on nullish left; does NOT protect later ops or wrong types

MISSING vs NULL vs UNDEFINED
  Absent prop ≠ { phone: undefined } (hasOwn / in differ; in includes inherited)
  JSON.stringify drops undefined → both may become "{}" (info loss)
  PATCH contract: absent=unchanged; null=clear; ""=validate/reject per rules
  exactOptionalPropertyTypes: optional ≠ automatically | undefined
  Partial<Entity> ≠ safe update API — model permitted fields/intentions

EQUALITY / IDENTITY
  Objects: === is identity, not structural equality
  Set/Map keys: SameValueZero (NaN≈NaN; 0≈-0); domain dedupe → key by id Map
  === no coerce; NaN===NaN false; Object.is(NaN,NaN) true; Object.is(0,-0) false

COPY / OWNERSHIP
  { ...obj } shallow — nested refs shared → draft mutates original
  structuredClone: deep for supported data; no functions; cost for huge graphs
  Immutable path updates / structural sharing: share only if treated immutable
  Identity + ownership + mutation policy = architecture

this / CLASSES / PROTOTYPES
  Ordinary method this = call-site receiver; extract send → this undefined (strict)
  Closure = lexical env; this ≠ that — bind / wrapper / lexical arrow field
  Arrow: lexical this; no own arguments; not for constructors the same way
  class methods typically on .prototype; lookup walks chain
  hasOwn ≠ in; instanceof / pollution awareness

ASYNC ARRAYS / ERRORS
  forEach ignores returned promises → “Finished” too early; unhandled rejects risk
  Sequential: for…of + await
  Concurrent: Promise.all(map…) — rejection ≠ cancel siblings; bound capacity
  allSettled: per-outcome; still unbounded unless you limit
  return promise inside try ≠ catch later rejection; return await can matter
  Don’t map every failure → null (not_found ≠ outage); model result unions
  finally: cleanup on leave try; not crash/kill proof

MODULES
  ESM live bindings; importer can’t reassign export
  Cycles allowed; TDZ/access before init → ReferenceError
  CJS require vs ESM import — know your project’s system
  Module singleton ≠ distributed singleton (multi-process)

TYPESCRIPT TOOLING
  Narrowing (typeof, discriminants); exhaustiveness via never + default
  : Type vs as Type vs satisfies Type (check without widening inference)
  None validate external JSON
  strictNullChecks; noUncheckedIndexedAccess (index → T|undefined); !
  removes warning only

CORRECTNESS STACK (none replaces the rest)
  TS · runtime schema · domain rules · auth · DB constraints · transactions
  · external guarantees · tests/monitoring

SENIOR LINE: syntactic fluency ≠ knowing what the language guarantees —
             design for real values, timing, and failure.
```
