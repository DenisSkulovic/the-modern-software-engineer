---
id: CS220-L02
course: CS220
title: "JavaScript Semantics and TypeScript Reality"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [CS101-S11]
prev: CS220-L01
next: CS220-L03
---



# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 02: JavaScript Semantics and TypeScript Reality

*Three production bugs. One release. No exotic algorithms, no compiler defects, and no mysterious race in the operating system. Just ordinary JavaScript doing exactly what its specification says it should do.*

---

# Part I — Intuition

## The picture to carry in your head

It's Thursday afternoon at a hotel-booking company.

The engineering team has deployed a modest update to its TypeScript backend. A service-fee calculation was simplified. A notification method was refactored into a reusable callback. And a background report generator was changed to process a list of reports asynchronously.

The tests pass.

TypeScript reports no errors.

The deployment succeeds.

Then three problems appear.

One customer has a contractual service fee of zero euros. After the release, the application charges the default fee of fifteen euros.

Another customer completes a booking, but the confirmation email fails because the notification service unexpectedly loses access to its configured provider.

Meanwhile, the reporting dashboard announces that all reports were generated, although several are still running and others have failed.

Three unrelated features. Three perfectly legal JavaScript programs. Three incorrect business outcomes.

The interesting thing is that none of these failures requires advanced computer science to explain. They emerge from small misunderstandings about what JavaScript actually means.

## 1. The language is following rules you may not have intended

Consider the service fee.

The developer wrote an expression that chooses the configured fee or a default.

In their head, the expression meant:

"Use the customer's fee if one was provided."

But the JavaScript operator actually meant:

"Use the customer's fee if its value is truthy; otherwise use the default."

Zero is falsy.

So an explicitly configured fee of zero was replaced with fifteen.

The code didn't malfunction. The programmer chose an operation with different semantics from the intended business rule.

This is the recurring theme of the lecture.

A language doesn't execute what the developer meant. It executes what the program says.

## 2. A missing value is not the same as a false value

Imagine filling out a hotel reservation form.

You leave the breakfast field untouched.

That's one intention.

You explicitly choose "No breakfast."

That's another.

You choose breakfast but set the number of guests to zero because the reservation is not yet finalized.

That's a third.

A computer program needs to represent those distinctions.

JavaScript has values such as `false`, `0`, the empty string, `null`, and `undefined`.

Some behave similarly in conditional expressions because they are falsy.

But they aren't interchangeable.

An empty string may mean an intentionally cleared name.

Zero may mean a valid financial amount.

False may mean a deliberately disabled feature.

Undefined may indicate that no value was supplied or that a property lookup found nothing.

Null may be used by an application to represent an explicit absence.

The business meaning comes from the contract. JavaScript's truthiness rules don't know that contract.

## 3. Objects have identities, not just contents

Now imagine two hotel reservations.

They contain exactly the same data: the same customer, dates, and room number.

Are they necessarily the same JavaScript object?

No.

Two separately created objects have separate identities.

JavaScript can distinguish them even when their visible properties match.

Conversely, two variables may refer to the very same object.

Changing that object through one variable may affect what the other variable observes.

This becomes important in frontend forms.

A developer creates what appears to be a new reservation draft. The customer edits the draft and clicks Cancel.

But the original reservation has already changed.

Why?

Because the developer copied only the outer object while continuing to share a nested object.

The draft wasn't as independent as they believed.

The problem is not unique to JavaScript, but JavaScript's object-reference semantics make it particularly common.

## 4. A function remembers its surroundings—but `this` is different

Now consider the missing confirmation email.

The notification service has a method that uses `this.provider` to send mail.

The original code invokes the method through the service object.

The refactored code extracts the method and passes it to another function.

The method body hasn't changed.

But the way it is invoked has changed.

In JavaScript, ordinary methods don't permanently carry their original receiver around with them.

The value of `this` depends on how the function is called.

The extracted method may no longer have the object it expects.

This is different from a closure, which preserves access to variables in the lexical environment where the function was created.

That distinction sounds abstract, but it explains countless real callbacks, event handlers, and service-layer bugs.

## 5. An asynchronous callback isn't an asynchronous loop

Finally, consider the report generator.

The developer uses an array's `forEach` method and supplies an `async` callback.

Inside that callback, the code awaits report generation.

After the loop, the application announces that every report is complete.

But the announcement appears too early.

The reason is surprisingly simple.

`forEach` invokes callbacks.

It doesn't collect their returned Promises or wait for their settlement.

Marking a callback `async` doesn't change the contract of the function that calls it.

If you want to wait for several asynchronous operations, you need a mechanism that actually represents their combined completion.

That might be sequential `await` calls, `Promise.all`, `Promise.allSettled`, or bounded concurrency.

The correct choice depends on what the application is trying to guarantee.

## The picture connecting all three bugs

```text
INTENDED BUSINESS MEANING
          |
          v
    JavaScript source
          |
          v
   Actual language rules
          |
          +-- Truthiness: 0 becomes fallback
          |
          +-- Call-site this: receiver disappears
          |
          +-- forEach: returned Promises ignored
          |
          v
  Valid runtime execution
          |
          v
  Incorrect business outcome
```

This is why senior engineers need more than type annotations and framework familiarity.

They need to understand the semantics of the operations they use.

TypeScript can catch many mistakes, but it doesn't redefine JavaScript.

Its value comes from helping us describe and maintain knowledge about values and control flow—not from replacing the underlying runtime.

### Three questions before the Deep Dive

1. Why does `value || fallback` behave differently from `value ?? fallback` when `value` is zero?
2. How can an extracted method lose `this` while a closure retains access to its surrounding variables?
3. Why doesn't `await` inside an asynchronous `forEach` callback make the surrounding loop wait?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Deployment That Passed TypeScript and Broke Three Things

Let's reconstruct the release.

The service-fee calculation was changed during a cleanup of optional configuration handling.

The notification service was refactored so its send method could be passed directly to a booking workflow.

The reporting module switched from a conventional loop to an array method with an asynchronous callback.

None of these changes looked dangerous.

They were all syntactically valid.

Their types appeared compatible.

But each altered a specific language-level behavior.

The first changed how the application interpreted absence.

The second changed how a function was invoked.

The third changed how completion was observed.

These are three different semantic boundaries.

Our first task is to make them explicit.

## 2. Truthiness: When Zero Becomes Missing

Consider the original service-fee code.

```typescript
const fee = customer.serviceFee || defaultFee;
```

Suppose:

`customer.serviceFee` is zero.

`defaultFee` is fifteen.

The resulting fee is fifteen.

The `||` operator returns its left-hand operand when that operand is truthy, otherwise it evaluates and returns the right-hand operand.

It doesn't ask whether the left-hand operand exists.

It doesn't ask whether the value was supplied by the customer.

And it doesn't know whether zero is a valid business value.

### The falsy values

JavaScript has a small collection of falsy values, including `false`, zero, negative zero, `0n`, the empty string, `null`, `undefined`, and `NaN`.

The remaining ordinary values are truthy.

That includes empty arrays and empty objects.

An empty array is not falsy merely because it contains no elements.

An empty object is not falsy merely because it contains no properties.

The language's truthiness conversion is not a general-purpose emptiness test.

### Nullish coalescing

If the intended rule is "use the fallback only when the value is null or undefined," the appropriate operator is `??`.

```typescript
const fee = customer.serviceFee ?? defaultFee;
```

Now zero remains zero.

False remains false.

An empty string remains an empty string.

Only `null` and `undefined` trigger the fallback.

### Why this isn't merely syntax trivia

Consider a retry policy.

If zero retries means "never retry," then using `retries || 3` silently enables retries.

Consider a feature flag.

If false means "disabled," then `enabled || true` silently turns it on.

Consider a pagination offset.

An offset of zero is valid, but `offset || defaultOffset` can replace it.

The practical rule is to choose the operator according to the meaning of absence.

Use truthiness when you genuinely want to treat all falsy values as equivalent.

Use nullish coalescing when only null or undefined should trigger a default.

And use explicit validation when other values—such as negative numbers or empty strings—require distinct behavior.

### Optional chaining isn't validation

Optional chaining, such as `customer?.preferences?.language`, lets code safely stop property access when an intermediate value is nullish.

That is useful.

But it doesn't prove that the final value has the right type or meaning.

If the object came from untrusted JSON, optional chaining doesn't replace runtime validation.

Remember the boundary we established in L01.

JavaScript offers operations for dealing with values.

The application still owns the contract.

## 3. Missing, Undefined, and Null: Three Different Stories

Suppose the booking platform provides a profile-update endpoint.

A customer can change a phone number.

What should these inputs mean?

An absent `phoneNumber` property might mean "leave the current number unchanged."

A property explicitly containing `null` might mean "clear the number."

An empty string might be rejected or treated according to a separate documented rule.

Those intentions are different.

### Property presence versus property value

Consider two JavaScript objects.

The first has no `phoneNumber` property.

The second explicitly has `phoneNumber: undefined`.

Reading either property produces `undefined`.

But the property-presence checks differ.

`Object.hasOwn()` distinguishes whether an object owns the property.

The `in` operator also detects inherited properties, so it answers a broader question.

These differences matter when processing partial updates.

A developer who checks only whether `patch.phoneNumber !== undefined` may accidentally collapse two states that the API wanted to keep distinct.

### Serialization loses information

JSON has null, but not undefined.

When `JSON.stringify()` encounters an object property whose value is undefined, it ordinarily omits that property.

Within an array, an undefined element is represented as null during JSON serialization.

That means serialization can change the observable distinction between JavaScript values.

For example, an object with an absent property and an object containing that property with value undefined may both serialize to the same JSON object.

This is a form of information loss.

It matters whenever a JavaScript object becomes a network message or persistent record.

### The correct PATCH contract

For an application where absence means "unchanged" and null means "clear," a useful static representation might be:

```typescript
type UpdateProfileRequest = {
  displayName?: string;
  phoneNumber?: string | null;
  language?: "en" | "lt" | "de";
};
```

This is more precise than treating every field as an arbitrary optional value.

But it remains a static declaration.

Incoming requests still need appropriate validation.

### Why `Partial<User>` isn't an API design

TypeScript provides the `Partial<T>` utility type.

It's useful because it makes properties optional.

But imagine using `Partial<User>` directly as the profile-update request.

The full User entity might contain a database ID, billing status, permissions, subscription plan, and creation timestamp.

Should a profile-update endpoint permit changes to all of those fields?

No.

The update contract should describe authorized operations, not mechanically expose every field in the persistence model.

This is a distinction between **data shape and business permission**.

We'll study more expressive type modeling in L03.

## 4. Equality: Identical Contents, Different Objects

Now consider two objects.

Both contain the same room ID and booking date.

A developer compares them using `===`.

The result is false.

Why?

Because separately created ordinary objects have distinct identities.

Strict equality doesn't recursively compare their properties.

For object values, it compares whether the references identify the same object.

### Value equality versus identity equality

Primitive values such as strings and numbers generally compare according to their primitive-value semantics.

Objects compare according to identity.

Two references to the same object compare equal.

Two separately constructed objects don't become identical because their properties match.

This matters when using objects as Map keys or Set members.

If you use a newly constructed object as a key, it doesn't automatically match an earlier distinct object with the same fields.

For stable lookup by business identity, a string or another canonical identifier may be more appropriate.

### Loose equality

JavaScript also has `==`, which can apply type-conversion rules before comparison.

This makes some expressions behave unexpectedly.

For example, different primitive types can compare equal through coercion.

The problem isn't that loose equality is randomly implemented.

It follows defined language rules.

The problem is that those conversion rules may not match the domain relationship you intend to test.

For most ordinary application comparisons, strict equality is a clearer default.

But strict equality isn't a deep-equality function.

### `NaN` and negative zero

There are edge cases worth recognizing.

`NaN` is not strictly equal to itself.

Positive zero and negative zero compare equal under `===`.

`Object.is()` uses a different sameness relation that considers `NaN` equal to itself and distinguishes positive and negative zero.

These distinctions can matter in numerical code and certain equality-sensitive APIs.

But don't mistake the existence of several equality operations for a demand to memorize every obscure coercion example.

The engineering skill is to identify which notion of sameness the application actually requires.

## 5. The Shallow Copy That Mutated the Original

Let's move from equality to mutation.

A frontend form loads a reservation object containing a nested guest record.

The user wants to edit the guest name without modifying the saved reservation until they press Save.

A developer writes:

```typescript
const draft = { ...reservation };
draft.guest.name = "Maria";
```

The outer object is new.

But the nested `guest` object is still shared.

The spread operation performs a shallow copy.

It copies property values from the source object into the new object.

When a property value is a reference to another object, that reference is copied.

The nested object is not automatically duplicated.

### The underlying structure

```text
reservation ----> original reservation
                       |
                       +---- guest ------+
                                        |
draft ----------> new reservation       |
                       |                |
                       +---- guest ------+
                                        |
                                        v
                                shared guest object
```

Now the developer changes `draft.guest.name`.

The original reservation observes the same mutation because both outer objects refer to the same nested guest.

The UI's Cancel button can no longer restore the original state simply by discarding the draft reference.

The original object has already been modified.

### Structural sharing isn't inherently bad

Sharing references can be efficient.

The danger comes from uncoordinated mutation.

An immutable update can create new objects only along the path being changed.

That allows unchanged nested structures to remain shared while preserving the intended separation.

This is common in state-management libraries and functional-style frontend code.

### Deep cloning

JavaScript provides `structuredClone()` for cloning supported values through the structured clone algorithm.

It can duplicate nested ordinary data structures.

But it isn't a universal copier of every possible object.

Functions cannot be cloned through it.

It doesn't preserve arbitrary class-instance behavior or all property metadata.

And cloning a large graph has memory and performance costs.

Deep copying should be an intentional operation, not a reflexive response to every reference bug.

### Where this lesson ends

The question of which object owns which mutable state leads naturally into memory management, aliasing, and ownership models.

We'll examine those systematically later in CS220.

For today, remember the language-level fact:

**A variable can hold a reference to an object. Copying the reference doesn't copy the object.**

## 6. Closures: A Function Can Outlive Its Creator

Now consider a function that creates a retry policy.

It initializes a variable named `maxAttempts`.

Then it returns a function that decides whether another retry is allowed.

The outer function finishes executing.

Later, the returned function is invoked.

How can it still access `maxAttempts`?

Because JavaScript functions carry access to the lexical environment in which they were created.

This is a closure.

### Lexical scope

A function's lexical environment depends on where the function is defined in source code.

It doesn't simply gain access to whichever local variables happen to exist at its eventual call site.

This gives closures predictable relationships to surrounding bindings.

### Bindings, not necessarily snapshots

Imagine a factory returning two functions.

One reads the current retry limit.

The other updates it.

Both functions were created within the same invocation of the factory.

They can share access to the same captured binding.

If one function changes the binding, the other can observe the new value.

That means a closure doesn't necessarily freeze the value of every captured variable at creation time.

The distinction matters in callbacks and long-lived services.

### The stale-value surprise

Suppose code creates a callback using a particular local constant that represents the current configuration.

Later, the application replaces the configuration with a new object elsewhere.

The callback may continue referring to the old captured value.

Whether this occurs depends on which binding was captured and whether that binding was reassigned.

A callback capturing a mutable binding behaves differently from one capturing a constant that refers to a particular snapshot.

This is especially relevant in component frameworks, where different renders can create different lexical environments.

### The lifetime consequence

A closure may retain access to values after the surrounding function has returned.

If the closure remains reachable, objects referenced through its environment may remain reachable too.

That can be useful.

It can also contribute to memory retention when callbacks unintentionally hold large objects alive.

We'll examine garbage collection and memory leaks in a later lecture.

The language-level principle is enough for now:

**A closure preserves access to its lexical environment; it does not necessarily preserve a frozen copy of every value.**

## 7. `this`: A Different Kind of Context

Return to the missing confirmation email.

The notification service uses an ordinary class method.

The method calls `this.provider.sendEmail()`.

Originally, the application invokes the method through its service object.

After refactoring, another function receives the extracted method.

The original receiver is no longer part of the invocation.

### The call site matters

For an ordinary JavaScript function, `this` is generally determined by how the function is invoked.

Calling `notificationService.send()` supplies the service object as the receiver.

Extracting `notificationService.send` into an unrelated variable and calling that variable doesn't preserve the original receiver automatically.

Class methods execute in strict mode, so an unbound method invoked as an ordinary function receives undefined as `this`.

Accessing `this.provider` then fails.

### Why closures aren't the same thing

A closure retains lexical bindings from where it was defined.

An ordinary method's `this` depends on how it is called.

These mechanisms can interact, but they aren't interchangeable.

A function can have access to captured variables while receiving an unexpected `this`.

### Bind the receiver deliberately

One option is to use `bind()` to create a function with a fixed receiver.

Another is to pass a wrapper that invokes the method through the service object.

An arrow function uses lexical `this`, inheriting that value from the surrounding context instead of receiving an independent call-site binding.

This makes arrow callbacks convenient in many situations.

### The instance-field trade-off

A class may define an arrow function as an instance field.

That arrow function is associated with the instance's lexical `this`.

Extracting it doesn't lose its receiver in the same way as extracting a prototype method.

But each instance typically gets its own function value for that field, whereas ordinary prototype methods can be shared across instances.

The correct choice depends on the design.

Don't convert every method into an arrow field out of superstition.

Understand when the receiver matters.

## 8. Classes Are Built on JavaScript's Object Model

TypeScript classes often resemble classes in Java or C#.

But JavaScript's underlying object model is prototype-based.

A class declaration provides syntax and semantics for constructing objects, organizing methods, and expressing inheritance.

Ordinary instance methods are typically found on the class's prototype.

When property lookup doesn't find a method directly on an instance, it can follow the prototype chain.

This is why multiple instances can share access to the same method implementation.

### Own properties versus inherited properties

Suppose a method is defined on a class prototype.

The instance may not own that property directly.

But property access can still find it through the prototype chain.

This distinction also explains why `Object.hasOwn()` and the `in` operator answer different questions.

`Object.hasOwn()` checks whether the object itself owns the property.

The `in` operator can also find inherited properties.

### TypeScript `private` versus JavaScript `#private`

TypeScript supports accessibility modifiers such as `private`.

For ordinary TypeScript private members, the restriction is primarily enforced during static checking.

JavaScript runtime access isn't necessarily prevented by that modifier alone.

JavaScript also supports `#private` fields with runtime-enforced private-name semantics.

That is a stronger runtime distinction.

Don't confuse a TypeScript accessibility declaration with a universal runtime security boundary.

### Why this matters operationally

Prototype behavior can affect mocking, method extraction, serialization, and object construction.

Class instances don't automatically behave like plain JSON objects.

Spreading a class instance doesn't reconstruct its complete prototype behavior.

And parsing JSON doesn't instantiate the intended class merely because the resulting object has matching fields.

The difference between object shape and runtime identity remains important.

## 9. Async Array Methods: A Callback Promise Isn't a Waiting Contract

Now return to the report generator.

The developer writes an asynchronous callback inside `forEach`.

The callback awaits report generation.

After the `forEach` call, the application logs that every report is complete.

But the log appears before several operations finish.

### Why the language behaves this way

`forEach` is a synchronous array iteration method.

It invokes the supplied callback for each relevant element.

It doesn't await returned Promises.

An async callback returns a Promise.

But the surrounding `forEach` method has no contract to collect and wait for those Promises.

The result is that the asynchronous operations may be initiated while the enclosing code immediately continues.

### Three legitimate requirements

Suppose reports must run sequentially because each one depends on the previous report's result.

A `for...of` loop with `await` provides that ordering.

Now suppose reports are independent and there are only a few of them.

Mapping each report to a Promise and awaiting `Promise.all()` may be appropriate.

Or suppose the business requires observing every result even when some fail.

`Promise.allSettled()` can collect each operation's settlement outcome.

Those mechanisms have different semantics.

### `Promise.all()` doesn't cancel siblings

If one Promise rejects, `Promise.all()` rejects.

But that doesn't automatically stop the other asynchronous operations that were already started.

They may continue running and producing side effects.

A developer who assumes that one failure cancels the entire batch may create duplicate work or resource leaks.

### Concurrency is not automatically bounded

Calling `Promise.all()` on ten independent operations may be fine.

Calling it on ten thousand operations can create excessive concurrency.

The application may overwhelm external APIs, databases, network connection pools, or its own memory.

A bounded worker pool or concurrency limiter can provide better resource control.

We'll explore the scheduling and backpressure mechanics in the operating-systems and distributed-systems courses.

For today's language lesson, the essential distinction is:

**An async function returns a Promise. Its caller must decide whether and how that Promise's completion matters.**

## 10. Errors and Promises: The `return await` Distinction

JavaScript's asynchronous error handling has another subtle trap.

Suppose a function loads a customer from an external provider.

The function uses a `try` block and wants to catch provider failures.

Inside the `try`, it returns the Promise from `fetchCustomer()` directly.

Will its local `catch` handle a later rejection from that Promise?

Not necessarily.

The function has returned the Promise without awaiting its settlement inside that `try` context.

The surrounding async function adopts the returned Promise's eventual state, but the local catch block doesn't receive the later rejection in the same way.

### Await the rejection inside the intended boundary

Using `return await fetchCustomer()` inside the `try` changes the behavior.

If the awaited operation rejects, the rejection is raised within that `try` block.

The local catch can handle it.

This is one reason `return await` isn't always redundant.

It can be important for error handling and cleanup semantics, and modern JavaScript engines handle it efficiently.

### Don't turn every error into null

Now consider the error policy.

Suppose the provider returns 404 because the customer doesn't exist.

That's one outcome.

Suppose the provider times out.

That's another.

Suppose credentials have expired.

That's a third.

Returning null for every failure may cause the caller to treat a temporary outage as proof that the customer doesn't exist.

That can produce incorrect business decisions.

A better application contract distinguishes absence from unavailability and authorization failure.

We'll explore richer result types in L03.

### `finally` and cleanup

The `finally` block executes when control leaves its associated `try`, including through normal completion and exceptions.

But be careful with asynchronous work.

If the code returns a Promise without awaiting it, the function's `finally` may execute before that Promise settles.

If resource cleanup must occur after the asynchronous operation completes, the code needs an appropriate awaited lifecycle.

And ordinary language cleanup doesn't guarantee execution after abrupt process termination.

Again, a language mechanism has a specific contract.

It isn't a universal resource-management guarantee.

## 11. JavaScript Modules: Initialization Is Part of Program Behavior

Modern JavaScript projects contain large dependency graphs.

Services import repositories.

Repositories import shared utilities.

Configuration modules import constants.

Controllers import services.

The resulting module structure looks static in source code, but it has runtime evaluation behavior.

This becomes important during startup.

### ECMAScript modules

ESM uses `import` and `export` syntax.

The module system establishes dependencies and evaluates modules according to its rules.

Imported bindings are live.

If an exporting module updates a mutable exported binding, importing modules can observe that change.

This differs from imagining that every import receives a disconnected snapshot of the original value.

However, an importing module cannot simply reassign another module's imported binding.

The defining module owns that binding.

### Circular imports

Suppose module A imports module B.

Module B also imports module A.

This creates a dependency cycle.

Circular imports are not automatically forbidden in ECMAScript modules.

Some work correctly.

Others fail because code accesses an imported binding before the exporting module has initialized it.

This can result in a `ReferenceError`.

### Why the timing matters

Imagine that module A exports a configuration value using a top-level `const`.

Module B imports that value and reads it immediately during module evaluation.

If the dependency cycle causes B to evaluate before A has initialized the relevant binding, the read can fail.

If B instead accesses the value later, after initialization, the cycle may work.

The important distinction is not simply whether the dependency graph contains a cycle.

It's whether the evaluation order and initialization state support the access.

### Architectural implications

Even when a cycle is technically valid, it may reveal unnecessary coupling.

Suppose BookingService imports PaymentService, PaymentService imports NotificationService, and NotificationService imports BookingService.

That dependency structure deserves scrutiny.

Perhaps shared interfaces should live in a separate module.

Perhaps the services have unclear ownership boundaries.

Perhaps dependency injection should occur at a composition root.

Circular imports can be harmless, but they can also reveal a design that is becoming difficult to reason about.

## 12. CommonJS, ESM, and the Module Singleton Trap

Node.js supports both CommonJS and ECMAScript modules.

CommonJS traditionally uses `require()` and `module.exports`.

ESM uses standard `import` and `export`.

They differ in important loading and evaluation details, especially around interoperation, initialization, and certain asynchronous module capabilities.

For a modern application, developers should understand which system their project uses and how build tooling resolves module dependencies.

### The process-local singleton

Suppose a module exports a Map used as a cache.

Every ordinary import of that same module instance within one process can share the Map.

The developer calls it a singleton.

Then the application is scaled to four Node.js processes.

Do the four processes share the same Map?

No.

Each process has its own memory and module instances.

The same source code produces separate in-memory state in each process.

If cache coherence matters across processes, the system needs an appropriate shared or replicated state strategy.

### A module cache isn't a database

A module-level Map can be useful for ephemeral local caching.

It can reduce repeated computation.

But it doesn't automatically provide persistence, consistency, or coordination across processes.

This is especially important for authentication sessions, inventory counts, rate limits, and distributed locks.

A process-local singleton is not a distributed singleton.

We'll develop this boundary further in CS320 and the data-systems courses.

## 13. TypeScript Narrowing: Knowledge Derived From Control Flow

We've now examined several JavaScript runtime behaviors.

Let's return to TypeScript and ask what its static analysis can genuinely help with.

One of TypeScript's strongest capabilities is control-flow-based narrowing.

Suppose a value has type `string | number`.

Before examining the value, TypeScript must consider both possibilities.

If the code checks `typeof value === "string"`, the checker can refine its understanding within that branch.

The branch condition establishes information about the value.

Outside the branch, TypeScript uses the remaining possible types according to control-flow analysis.

### Types as knowledge

This is a useful way to think about static types.

The declared type represents what the compiler currently knows or assumes about a value.

A runtime check can provide additional evidence.

The compiler can then narrow the possible types within a relevant code path.

For example, after verifying that a value is a number, calling a number-specific method becomes meaningful.

### Discriminated unions

Now imagine a background report operation.

It can be Pending, Running, Completed, or Failed.

A broad interface containing many optional fields might permit meaningless combinations.

A discriminated union can represent separate state variants.

Each variant has a common status field and the fields appropriate to that state.

A Completed operation contains a result.

A Failed operation contains an error.

A Running operation contains its execution identifier.

TypeScript can narrow the variant based on a check of the status field.

This is powerful because the data model helps prevent accidental access to fields that shouldn't exist in the current state.

### Exhaustiveness checking

Suppose the application handles every known report state in a switch statement.

Later, a Cancelled state is added.

We want the compiler to identify code that hasn't been updated to handle cancellation.

A common technique uses the special type `never` in an exhaustive check.

When every variant is handled, the remaining value can be narrowed to `never`.

If a new variant remains unhandled, the check can become a type error.

This is a meaningful guarantee.

It allows a domain model to make certain omissions visible during development.

We'll explore sum types and invalid-state modeling more deeply in L03.

## 14. `satisfies`, Assertions, and Inference

TypeScript provides several superficially similar ways of expressing relationships between values and types.

But they serve different purposes.

### Type annotations

An annotation declares a variable's type and checks whether the expression is assignable to it.

This is useful for defining explicit interfaces and constraining the type exposed to consumers.

However, an annotation can sometimes widen information about a literal value that would otherwise be inferred more precisely.

### Type assertions

An assertion using `as` tells TypeScript to treat an expression as a specified type, within the language's assertion rules.

It doesn't perform a runtime conversion or validation.

We established that in L01.

Assertions can be appropriate when a guarantee has been established through other means.

But they can also silence real problems.

### The `satisfies` operator

The `satisfies` operator checks whether an expression is compatible with a specified type while preserving more of the expression's inferred type.

This is useful for configuration objects, route tables, event registries, and similar structures.

For example, a route map may require a fixed set of keys, each containing a path and authentication flag.

Using `satisfies` can check the required structure without unnecessarily discarding the precise information inferred about individual route definitions.

### No runtime validation

None of these constructs automatically validates arbitrary JSON arriving from a network.

A `satisfies` expression is a static compatibility check.

A type annotation isn't a parsing function.

A type assertion isn't a validator.

The right construct depends on whether you're declaring an interface, checking an expression, or expressing a known relationship.

## 15. Strict TypeScript: Make Hidden Assumptions Visible

Two TypeScript projects can use the same language while enforcing very different static guarantees.

Compiler settings matter.

A project with permissive options may accept code that a stricter project rejects.

That isn't evidence that one version of JavaScript behaves differently.

It's evidence that the static analysis policy differs.

### `strictNullChecks`

With strict null checking, nullable and potentially undefined values are treated more carefully.

Suppose `customers.find()` doesn't find a matching customer.

It returns undefined.

Accessing the missing customer's email without checking the result is unsafe.

A suitable strict configuration can report the problem.

Using a non-null assertion may silence the warning.

It doesn't create a customer at runtime.

### `noUncheckedIndexedAccess`

Consider an array of prices.

The code reads element 100.

The array contains only three values.

At runtime, the result is undefined.

Without stricter indexed-access behavior, TypeScript may treat array indexing as producing the declared element type.

Enabling `noUncheckedIndexedAccess` can include undefined in the result type where appropriate.

This exposes the possibility that the requested element isn't present.

### `exactOptionalPropertyTypes`

Optional properties have an important distinction between absence and explicitly present undefined values.

With `exactOptionalPropertyTypes`, TypeScript applies stricter assignment rules to optional properties.

A declaration such as `phoneNumber?: string` doesn't automatically permit assigning explicit undefined unless the type also allows it.

This aligns the static model more closely with JavaScript's property-presence semantics.

It's particularly useful for PATCH contracts and configuration objects.

### Strictness isn't correctness by itself

A strict compiler configuration can catch important categories of mistakes.

But it can also reveal limitations or ambiguities in type declarations.

Sometimes developers respond by adding assertions everywhere.

That can remove the benefit of strict checking.

A better approach is to investigate the warning.

Does the value genuinely have the required property?

Can the code perform a runtime check?

Would a different data model express the invariant better?

Or is a carefully justified assertion appropriate?

The objective isn't to maximize compiler silence.

It's to make the program's assumptions explicit.

## 16. `readonly` Isn't Runtime Immutability

One final TypeScript distinction deserves attention.

TypeScript supports `readonly` properties.

This can prevent certain mutations through statically checked code.

But the modifier doesn't automatically freeze the underlying JavaScript object.

At runtime, the object may remain mutable.

The restriction exists in the static type system.

JavaScript's `Object.freeze()` provides a separate runtime mechanism for preventing certain modifications to an object.

But ordinary freezing is shallow.

Nested objects may remain mutable unless they are separately protected.

This connects back to our shallow-copy problem.

### Compile-time immutability versus runtime ownership

A type can discourage or reject mutation through a particular reference.

But another reference may still have a mutable view of the same object.

And the runtime value may remain mutable.

For strong correctness, an application needs a consistent policy about ownership and mutation.

That policy may involve immutable data structures, defensive copying, runtime enforcement, or type-system guarantees.

We'll examine the deeper ownership trade-offs in L03 and memory-lifetime consequences in L04.

For now, remember:

**A TypeScript declaration can constrain what checked code is allowed to write without making the JavaScript object physically immutable.**

## 17. Returning to the Three Production Bugs

Let's reconstruct the Thursday release.

### The incorrect fee

The developer used `||` when the business rule required nullish fallback.

Zero was a valid amount but falsy under JavaScript's truthiness rules.

The fix is to express the intended absence condition explicitly and test boundary values.

### The broken notification

The developer extracted a method whose behavior depended on `this`.

The new invocation no longer provided the expected receiver.

The fix is to preserve the receiver deliberately, through an appropriate wrapper or binding strategy.

### The premature report completion

The developer used an async callback with an array method that doesn't await returned Promises.

The surrounding function continued before the operations settled.

The fix is to choose explicit sequential, concurrent, or bounded-concurrency control flow according to the required semantics.

### What TypeScript contributed

TypeScript can help model values, detect missing possibilities, and enforce selected relationships.

But these bugs were rooted in valid JavaScript operations.

The type system doesn't replace the need to understand their runtime behavior.

This is the key point of the lecture:

**The most dangerous language bugs aren't always obscure. Often they're familiar constructs used with the wrong mental model.**

## 18. The Oral Examination

Answer the following aloud before reading the solutions. Focus on mechanisms, not memorized syntax.

### Challenge 1 — The Zero Fee

A customer explicitly configures a zero service fee.

The code uses `fee || 15`.

Why does it charge fifteen?

What operator better represents "default only when missing"?

### Challenge 2 — The Missing Property

Compare an object with no `phoneNumber` property and one containing `phoneNumber: undefined`.

How do property lookup, `Object.hasOwn()`, and JSON serialization treat them?

Why does this matter for PATCH APIs?

### Challenge 3 — The Cancel Button That Didn't Cancel

A frontend component creates a reservation draft with object spread.

It edits a nested guest object.

The original reservation changes before Save.

Explain the reference relationship and propose a safer update strategy.

### Challenge 4 — The Lost Receiver

An ordinary class method accesses `this.provider`.

The method is extracted and invoked through an unrelated variable.

Why might it fail?

How is this different from closure capture?

### Challenge 5 — The Async Loop

A developer uses `reports.forEach(async report => await generateReport(report))`.

The completion log appears immediately.

Why?

Describe three possible implementations for sequential processing, concurrent processing, and collecting all individual outcomes.

### Challenge 6 — The Rejection That Escaped

An async function returns an external Promise from inside a `try` block.

The local `catch` doesn't handle a later rejection.

Explain how `return await` changes the behavior.

### Challenge 7 — The Circular Module

Module A imports B.

Module B imports A.

B reads an imported constant from A before A initializes it.

Why can a runtime error occur even though circular imports are permitted?

### Challenge 8 — The Strict TypeScript Debate

A developer argues that `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes` are unnecessary bureaucracy.

Another responds by enabling them but silencing every complaint with assertions.

What is wrong with both approaches?

## 19. Solutions and Discussion

### Solution 1 — Truthiness is not absence

Zero is falsy, so the `||` operator chooses the right-hand fallback.

If the business rule defines absence as null or undefined, use nullish coalescing with `??`.

Also validate whether other inputs, such as negative values, are permitted.

### Solution 2 — Property presence and value differ

Both property lookups can produce undefined.

But `Object.hasOwn()` distinguishes an absent property from an explicitly present one.

When serializing object properties, JSON.stringify ordinarily omits properties whose values are undefined.

A PATCH API must define whether absence means unchanged, null means cleared, and other values mean updated.

That contract should not depend accidentally on truthiness.

### Solution 3 — Object spread is shallow

The outer draft object is new, but nested object references remain shared.

Mutating the nested guest therefore changes what the original object observes.

Use an immutable update that copies the relevant nested path, or an appropriate deep clone when justified.

The real requirement is a deliberate ownership and mutation policy.

### Solution 4 — Ordinary `this` depends on invocation

Extracting an ordinary class method loses the original method-call receiver.

The function body still exists, but `this` may be undefined when invoked unbound in strict mode.

Use a wrapper, `bind()`, or an appropriate lexical-arrow strategy.

Closures retain lexical bindings based on definition location; ordinary method receivers depend on invocation.

### Solution 5 — `forEach` ignores callback Promises

The array method invokes callbacks without awaiting their eventual settlement.

Use `for...of` with await for sequential operations.

Use `Promise.all()` for suitable concurrent operations whose combined success matters.

Use `Promise.allSettled()` when every individual outcome must be collected.

For large workloads, bound concurrency explicitly.

### Solution 6 — Await brings the rejection into the local `try`

Returning a Promise without awaiting it can allow a later rejection to bypass the local catch block.

`return await` waits for settlement within the `try` context, so a rejection is raised there and can be caught.

The function's error policy must still distinguish expected absence from infrastructure failure.

### Solution 7 — Initialization timing matters

ESM cycles are permitted, but accessing a lexical binding before initialization can produce a ReferenceError.

The module dependency graph and evaluation order determine when values become available.

A circular import may work if values are accessed only after initialization.

The existence of a cycle is a reason to inspect architecture, not automatic proof of a bug.

### Solution 8 — Strictness should expose assumptions, not create rituals

Ignoring useful strict checks loses opportunities to detect real problems.

Silencing every warning with an assertion can make the checker less meaningful.

Use compiler settings deliberately, investigate why a value may be absent or unsafe, and encode or validate the real guarantees.

Static analysis should improve reasoning rather than become a cosmetic score.

## 20. The Mental Model Worth Keeping

JavaScript defines precise runtime behavior.

TypeScript overlays static analysis on that behavior.

The two systems cooperate, but they don't replace one another.

When reviewing JavaScript or TypeScript code, ask:

**Is this operation testing truthiness or absence? Comparing values or identities? Copying data or copying references? Capturing a lexical binding or depending on a call-site receiver? Waiting for a Promise or merely creating one? Using a module binding before initialization?**

These distinctions are the foundation of predictable JavaScript engineering.

And when TypeScript reports a problem, ask what assumption it has exposed instead of immediately asserting the warning away.

## 21. Next Lecture — CS220-L03: Type Systems, Generics, Ownership, and Valid States

We now understand the JavaScript runtime behaviors that TypeScript must work with.

Next, we'll examine what different type systems can guarantee—and what they cannot.

We'll compare structural and nominal typing, generics, union types, discriminated states, and ownership models across TypeScript, Java, Go, Python, and Rust.

Why does Rust care who owns a value?

Why can two TypeScript strings with different business meanings be interchangeable?

Why do generics preserve relationships between values?

And how can a type system rule out entire categories of invalid program states without becoming a substitute for runtime authorization or transactional correctness?

The language mechanics are established.

Next comes language design.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

## Optional Practical Lab — Eight JavaScript Predictions

**Objective:** Predict behavior before running code, reproduce the original failures, and apply targeted fixes without changing the underlying language semantics.

Use a recent Node.js version and TypeScript. The examples are intentionally small so the mechanisms remain visible.

### Lab A — Truthiness and absence

Create `truthiness.mjs`:

```javascript
const values = [0, false, "", null, undefined, 12];

for (const value of values) {
  console.log({
    value,
    orDefault: value || "DEFAULT",
    nullishDefault: value ?? "DEFAULT",
  });
}
```

Run it:

```bash
node truthiness.mjs
```

Predict each result before inspecting the output.

**Question:** Which values triggered the fallback under `||` but not `??`?

### Lab B — Property presence and JSON

Create `presence.mjs`:

```javascript
const missing = {};
const explicitUndefined = { phoneNumber: undefined };
const explicitNull = { phoneNumber: null };

for (const item of [missing, explicitUndefined, explicitNull]) {
  console.log({
    value: item.phoneNumber,
    own: Object.hasOwn(item, "phoneNumber"),
    inObject: "phoneNumber" in item,
    json: JSON.stringify(item),
  });
}
```

Before running it, explain which distinctions JSON can and cannot preserve.

### Lab C — The shared nested object

Create `copy.mjs`:

```javascript
const reservation = {
  id: "R-101",
  guest: { name: "Anna" },
};

const draft = { ...reservation };
draft.guest.name = "Maria";

console.log("Original:", reservation.guest.name);
console.log("Draft:", draft.guest.name);
console.log("Same guest object:", reservation.guest === draft.guest);
```

Now repair the update with structural sharing.

```javascript
const repairedDraft = {
  ...reservation,
  guest: {
    ...reservation.guest,
    name: "Elena",
  },
};
```

Verify that changing `repairedDraft.guest.name` doesn't mutate `reservation.guest.name`.

### Lab D — The receiver disappears

Create `this-binding.mjs`:

```javascript
class NotificationService {
  constructor(provider) {
    this.provider = provider;
  }

  send(customer) {
    return this.provider.sendEmail(customer.email);
  }
}

const provider = {
  sendEmail(email) {
    return `Sent to ${email}`;
  },
};

const service = new NotificationService(provider);

console.log(service.send({ email: "guest@example.test" }));

const extracted = service.send;

try {
  console.log(extracted({ email: "guest@example.test" }));
} catch (error) {
  console.log("Extracted method failed:", error.message);
}

const bound = service.send.bind(service);

console.log(bound({ email: "guest@example.test" }));
```

**Question:** Why did `bind()` fix the issue without changing the method body?

### Lab E — Async `forEach` doesn't wait

Create `async-array.mjs`:

```javascript
const delay = (ms) =>
  new Promise((resolve) => setTimeout(resolve, ms));

const reports = ["A", "B", "C"];

reports.forEach(async (report) => {
  await delay(200);
  console.log("Completed", report);
});

console.log("All reports completed?");
```

Observe the ordering.

Now replace the loop with a `for...of` loop using await.

Then replace it with `await Promise.all(reports.map(...))`.

Because this is an ESM file, top-level await is available.

**Question:** Which version runs sequentially? Which starts operations concurrently? Which version waits for completion?

### Lab F — `return` versus `return await`

Create `error-boundary.mjs`:

```javascript
function failsLater() {
  return Promise.reject(new Error("Provider unavailable"));
}

async function withoutAwait() {
  try {
    return failsLater();
  } catch {
    return "Caught locally";
  }
}

async function withAwait() {
  try {
    return await failsLater();
  } catch {
    return "Caught locally";
  }
}

console.log(
  "Without await:",
  await withoutAwait().catch((error) => error.message)
);

console.log(
  "With await:",
  await withAwait().catch((error) => error.message)
);
```

Predict the output first.

**Question:** Why does the placement of `await` affect which catch block handles the rejection?

### Lab G — TypeScript narrowing and strictness

Create a small TypeScript project and enable strict checks.

Define a value of type `string | number`.

Write a function that uses `typeof` to narrow it before performing type-specific operations.

Then create an array containing three numbers and access index 100.

Enable `noUncheckedIndexedAccess` and observe how the inferred type changes.

Finally, model a profile patch with `phoneNumber?: string | null`, enable `exactOptionalPropertyTypes`, and test whether assigning explicit undefined is accepted.

**Question:** Which runtime facts did the compiler settings make more visible?

### Lab H — Circular modules

Create `a.mjs`:

```javascript
import "./b.mjs";

export const settings = {
  currency: "EUR",
};

console.log("A initialized");
```

Create `b.mjs`:

```javascript
import { settings } from "./a.mjs";

console.log("B sees", settings.currency);
```

Run:

```bash
node a.mjs
```

Observe the initialization error.

Now change `b.mjs` so it exports a function that reads `settings.currency` rather than reading it immediately during module evaluation.

Call that function after A has initialized its exported value.

**Question:** Why is a circular dependency not necessarily invalid, while early access to an uninitialized binding is?

---

## Further Reading

1. [MDN — JavaScript Data Types](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Data_structures) — Runtime values, primitives, and objects.
2. [MDN — Nullish Coalescing](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing) — Missing values versus falsy values.
3. [MDN — JSON.stringify](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify) — Serialization and information loss.
4. [MDN — Closures](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Closures) — Lexical environments and captured bindings.
5. [MDN — `this`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/this) — Call-site receivers and arrow functions.
6. [MDN — JavaScript Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules) — Live bindings, initialization, and cycles.
7. [TypeScript Handbook — Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) — Control-flow analysis and discriminated unions.
8. [TypeScript 4.9 — The `satisfies` Operator](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html) — Checking compatibility while preserving inference.
9. [TypeScript — Strict Compiler Options](https://www.typescriptlang.org/tsconfig/strict.html) — Compiler enforcement.
10. [MDN — async function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function) — Async return values, promises, and rejection handling.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is deliberately fenced for rapid screen-based revision.*

```text
CS220-L02 — JAVASCRIPT SEMANTICS AND TYPESCRIPT REALITY

CORE PRINCIPLE

  TypeScript checks selected static relationships.
  JavaScript executes actual runtime values.
  Valid JavaScript can still be wrong business logic.

TRUTHINESS

  Falsy:
    false
    0, -0, 0n
    ""
    null
    undefined
    NaN

  [] and {} are truthy.

  x || fallback:
    Fallback when x is falsy

  x ?? fallback:
    Fallback when x is null or undefined

  Zero and false are often valid business values.

PROPERTY PRESENCE

  Missing property:
    Lookup produces undefined

  Explicit property: undefined
    Lookup also produces undefined

  Object.hasOwn():
    Own property presence

  "key" in object:
    Includes inherited properties

JSON

  Object property with undefined:
    Ordinarily omitted

  Array element undefined:
    Serialized as null

  JSON has null, not undefined.

PATCH CONTRACTS

  Missing -> unchanged
  null    -> clear
  value   -> update

  Define semantics explicitly.
  Partial<Entity> may expose inappropriate fields.

EQUALITY

  ===:
    Primitive value equality / object identity

  ==:
    Coercive comparison rules

  Object.is:
    NaN equals itself
    Distinguishes +0 and -0

  Two distinct objects with same fields != same identity

REFERENCES

  Object spread:
    Shallow copy

  Nested objects:
    References remain shared

  structuredClone:
    Deep clone for supported values
    Not universal cloning of classes/functions

  Immutable update:
    Copy changed path, share unchanged immutable data

CLOSURES

  Function + lexical environment
  Retains access to surrounding bindings
  Captured bindings aren't necessarily frozen snapshots
  Retained references can extend object lifetimes

THIS

  Ordinary function:
    Receiver depends on invocation

  Extracted class method:
    May lose this

  Arrow:
    Lexical this

  Fix:
    bind()
    Wrapper method call
    Deliberate arrow strategy

CLASSES AND PROTOTYPES

  Ordinary methods shared through prototype
  Class-field functions often per instance
  Object.hasOwn differs from inherited property lookup

  TypeScript private:
    Primarily static restriction

  JavaScript #private:
    Runtime-enforced private-name semantics

ASYNC ARRAY METHODS

  forEach(async ...):
    Doesn't await returned promises

  for...of + await:
    Sequential processing

  Promise.all:
    Concurrent operations, aggregate fulfillment
    Rejects when one rejects
    Doesn't cancel other operations automatically

  Promise.allSettled:
    Collects individual settlement outcomes

  Large concurrency needs bounding.

RETURN AWAIT

  return promise inside try:
    Later rejection may bypass local catch

  return await promise inside try:
    Rejection raised within local try context

  finally and cleanup depend on awaited lifecycle

MODULES

  ESM:
    import/export
    Live bindings
    Dependency graph / evaluation order

  Circular imports permitted
  Reading uninitialized imported binding may throw

  CommonJS:
    require/module.exports
    Different loading and interop semantics

  Module singleton:
    Process-local, not distributed

TYPESCRIPT NARROWING

  typeof checks
  Property checks
  Discriminated unions
  Control-flow analysis
  Exhaustive never checks

  Types represent what compiler knows/assumes.

TYPESCRIPT CONSTRUCTS

  Annotation:
    Declares variable type

  Assertion:
    Treat expression as asserted type
    Doesn't validate at runtime

  satisfies:
    Checks compatibility
    Preserves more precise inference

STRICT SETTINGS

  strictNullChecks:
    Null/undefined possibilities visible

  noUncheckedIndexedAccess:
    Indexed values may be undefined

  exactOptionalPropertyTypes:
    Absent property != explicitly undefined

  readonly:
    Static restriction, not deep runtime freeze

SENIOR REVIEW QUESTIONS

  Truthiness or actual absence?
  Property missing or explicitly undefined?
  Value equality or reference identity?
  Shallow copy or independent nested state?
  Lexical binding or call-site this?
  Promise created or Promise awaited?
  Module evaluated or binding initialized?
  Static type promise or runtime guarantee?

FINAL MENTAL MODEL

  Know the language's exact semantics.
  Use TypeScript to expose useful assumptions.
  Validate external reality.
  Preserve business invariants separately.

SENIOR LINE

  "Most JavaScript production bugs aren't mystical.
   They arise when a developer assumes different semantics
   from those the language actually specifies. I identify
   the precise runtime behavior, then use TypeScript,
   validation and deliberate control flow to make the
   intended contract explicit."
```
