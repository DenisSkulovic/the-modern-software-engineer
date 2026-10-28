---
id: CS220-L03
course: CS220
title: "Type Systems, Generics, Ownership, and Valid States"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS220-L02
next: CS220-L04
---




# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 03: Type Systems, Generics, Ownership, and Valid States

*Five languages receive the same booking-system requirements. Each can produce a working application. Each makes certain mistakes easier to catch and others easier to overlook. None can prove that the last available hotel room still exists.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a hotel-booking company preparing to modernize its backend.

The existing application is written in TypeScript. Some services use Python, and an architecture proposal recommends rewriting selected components in Java, Go, or Rust.

Everyone has an opinion.

The Java developer argues that stronger class and interface relationships would prevent careless mistakes.

The Go developer prefers small interfaces and a simpler model.

The Python developer points out that runtime validation and good tests are more important than elaborate type declarations.

The Rust developer believes the team needs to rethink ownership and mutation rather than endlessly debugging unexpected shared state.

And the TypeScript developer wants to know why rewriting a working booking system in another language is even being discussed.

During the meeting, three production incidents arrive.

First, a function receives a customer identifier where it expected a hotel identifier.

Both identifiers are strings, so the mistake passes through an otherwise well-typed TypeScript application.

Second, a booking calculation receives a reservation object whose dates unexpectedly change while the calculation is in progress.

Several parts of the application hold references to the same mutable object.

Third, a payment workflow accepts a response with all the expected fields, including `status: "confirmed"`.

The response is structurally valid.

Unfortunately, it isn't an authentic confirmation from the payment provider.

These incidents expose three different questions.

**Identity:** How can the language distinguish values that have the same representation but different meanings?

**Ownership:** How can the language control who may read, modify, or retain data?

**Authority:** How can the application establish that a fact is actually true?

Different type systems answer the first two questions differently.

None can solve the third merely by declaring a clever type.

## 1. A type is a restriction on what can happen

Imagine a hotel with several kinds of access cards.

One card opens guest rooms.

Another opens maintenance rooms.

A third opens the accounting office.

Physically, all three cards may be identical plastic rectangles containing similar-looking identifiers.

But their meanings differ.

If the system treats every identifier as an ordinary string, a programmer might accidentally pass a customer ID into a function expecting a reservation ID.

The computer sees two strings.

Why shouldn't it accept the call?

Because the application requires a distinction that the basic representation doesn't express.

A type system can help encode that distinction.

Instead of treating every string as interchangeable, we can define separate identities for different domain concepts.

The compiler can then reject certain accidental substitutions.

This is one of the most useful purposes of types: not describing how values look, but making relationships and restrictions explicit.

## 2. Shape is not identity

Suppose two objects each contain an `id` field and a `name` field.

One represents a hotel.

The other represents a customer.

Should they be interchangeable?

That depends on the language's type system.

A structurally oriented system examines the required members and their types.

If the shapes are compatible, the values may be considered compatible.

A nominally oriented system gives more importance to declared identities.

Two classes can have identical fields but remain distinct because they are different declared types.

Neither choice is universally superior.

Structural typing makes flexible composition and interoperability convenient.

Nominal typing makes certain domain distinctions explicit.

The central question is which relationships the application wants the checker to enforce.

## 3. The compiler can check a relationship without knowing the world

Now imagine a function that retrieves a hotel.

It accepts a HotelId and returns information about that hotel.

A type checker may confirm that the caller supplied a HotelId rather than a CustomerId.

Excellent.

But does that mean the hotel exists?

No.

Does it mean the hotel is currently accepting reservations?

No.

Does it mean the customer is authorized to view its information?

No.

Those are facts about the outside world.

A static type system operates on program declarations and information available during checking.

It doesn't automatically contact a production database to verify the current existence of every entity.

This is an important boundary.

Types can restrict which programs are considered valid.

They cannot make arbitrary external facts permanently true.

## 4. Generics preserve relationships

Imagine a function that retrieves an item from a collection.

If the input is a collection of Hotel objects, the result should be a Hotel.

If the input is a collection of Customer objects, the result should be a Customer.

We could write separate functions.

But they perform the same operation.

A generic function expresses the relationship between its input and output types without committing to one concrete type.

It is not simply a function that accepts anything.

The crucial feature is that the same type variable appears in multiple positions.

The compiler understands that those positions are related.

**Generics preserve information across an abstraction instead of throwing it away.**

That is why a generic function is often safer than a function that accepts and returns unconstrained values.

## 5. Some states should be impossible to describe

Consider a payment operation.

A naive representation might contain a status field and several optional properties.

Perhaps it has a confirmation ID.

Perhaps it has an error message.

Perhaps neither exists.

Perhaps both exist.

The application now has to defend against combinations that don't make sense.

But a payment isn't one vague object.

It's a process with different states.

A Pending payment doesn't yet have a confirmation.

A Confirmed payment has a confirmation identifier.

A Failed payment has a failure reason.

A type system with suitable sum types or discriminated unions can express those alternatives.

Now the compiler can reject code that attempts to read a confirmation ID from a Pending payment without establishing that the payment is Confirmed.

This is the practical meaning behind the phrase *make invalid states unrepresentable*.

It doesn't mean every business failure disappears.

It means the chosen representation excludes certain invalid combinations before execution.

## 6. Ownership is the other half of the problem

Now return to our booking dates.

Two services share a reference to one mutable reservation object.

The pricing service reads the check-in and check-out dates.

Meanwhile, another part of the application changes those dates.

The pricing service may now calculate a total using data that changed unexpectedly.

A language can offer different ways to manage this risk.

One approach uses immutable values and defensive copying.

Another uses conventions about ownership and mutation.

Another enforces certain ownership rules through the type system.

Rust makes these rules especially visible.

It asks which part of the program owns a value, who can borrow it, and whether mutation can occur while other references remain active.

This can eliminate important memory-safety failures and unsynchronized shared-memory access patterns.

But it doesn't prove that the new reservation dates are affordable, authorized, or consistent with the database.

Ownership protects one kind of correctness.

Business rules protect another.

## The three promises

Our booking application now has three useful layers of reasoning.

```text id="cs22003-intuition"
         DOMAIN VALUES
     HotelId is not CustomerId
                |
                v
        VALID PROGRAM STATES
   Pending / Confirmed / Failed
                |
                v
       OWNERSHIP AND ACCESS
   Who may read or mutate data?
                |
                v
       EXTERNAL AUTHORITATIVE
               FACTS
  Is the room available right now?
  Did the payment really succeed?
```

The first three layers can receive substantial assistance from language and type-system design.

The last requires runtime validation, authentication, authorization, transactions, and coordination with external systems.

### Three questions before the Deep Dive

1. Why might two values have identical representations but need distinct types?
2. What relationship does a generic function preserve that a function using `any` may lose?
3. Why can't Rust's ownership system prevent two separate application processes from selling the same hotel room?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Five Languages, Three Bugs, One Booking System

Our architecture meeting has become an experiment.

The team agrees to investigate how five language ecosystems would approach the same booking system.

The languages are TypeScript, Python, Java, Go, and Rust.

We won't crown a winner.

Instead, we'll ask what guarantees each language can express naturally, what additional machinery it requires, and which failures remain possible regardless of implementation language.

Consider the three incidents.

In the first, a CustomerId is accidentally supplied where a HotelId is required.

In the second, multiple parts of the application share mutable reservation data without a clear ownership policy.

In the third, a structurally valid payment response is treated as authoritative proof that money was collected.

These are not three versions of the same bug.

They belong to different categories of correctness.

A strong type-system design begins by identifying the category.

## 2. What a Type System Actually Proves

A type system associates program expressions with types and establishes relationships among those types.

A type can describe permitted values, operations, or structures.

A function type can describe acceptable arguments and the result it promises to produce under the language's typing rules.

A type checker may reject a program that violates those rules.

But the meaning and strength of these guarantees depend on the language.

TypeScript, Java, Go, Python, and Rust make different choices about compatibility, inference, runtime representation, mutation, and safety.

They should not all be placed on a simplistic scale from weak to strong.

### Static versus dynamic checking

TypeScript performs static checks over JavaScript-oriented code.

Java uses a static type system with runtime type information and checks for certain operations.

Go uses static typing with explicit defined types and interface satisfaction rules.

Rust uses a static type system with ownership and borrowing constraints.

Python is dynamically typed, but its typing ecosystem supports optional static analysis through type hints and external checkers.

That last point matters.

Python is not a language without types.

Its runtime values have types that determine supported operations.

Static annotations are an additional development-time mechanism.

### Soundness and practical compromises

A type system is sound, in a formal sense, when it supports certain guarantees relating accepted programs to their runtime behavior under the system's model.

But practical language ecosystems may deliberately permit operations that weaken those guarantees.

TypeScript's documentation explicitly acknowledges unsoundness in its compatibility rules.

It prioritizes compatibility with common JavaScript programming patterns.

Java has casts and runtime exceptions.

Go uses explicit conversions and dynamic interface values.

Rust permits unsafe code through explicitly marked mechanisms and can still have ordinary logic errors.

Python's type hints generally aren't enforced automatically by the runtime.

A language's type system should therefore be evaluated through its actual guarantees and escape hatches.

The label *statically typed* is only the beginning of the analysis.

## 3. Types as Sets of Values—and Allowed Operations

A useful first approximation treats a type as a description of possible values.

A boolean permits true and false.

A string type permits strings.

A domain-specific identifier type may represent strings that have been assigned a particular semantic role.

But this model needs refinement.

Types also determine which operations are permitted and how values can be used.

A `HotelId` might be represented using a string internally while being deliberately incompatible with `CustomerId`.

That incompatibility is useful precisely because the two representations are similar.

### The swapped-identifier incident

Imagine a function that retrieves a hotel by identifier.

The caller accidentally passes the customer's identifier.

If both parameters are plain strings, an ordinary type checker may find nothing wrong.

The operation is structurally valid.

The database query may simply return no hotel.

Or, in a poorly designed system, it may accidentally return a record whose identifier happens to match.

The application's domain model knows that these are different kinds of identities.

The type declarations don't.

This is a modeling failure, not necessarily a type-checker failure.

### Distinct types can express domain meaning

One remedy is to represent HotelId and CustomerId as distinct types.

The compiler can then reject accidental substitutions.

But a type declaration alone isn't enough.

The application still needs a trustworthy way to construct a HotelId from external input.

The string `"H-123"` doesn't become a valid existing hotel simply because someone asserted that it has type HotelId.

And the same identifier may become invalid later if the hotel is deleted.

Distinguish the semantic category of a value from the current external fact it refers to.

## 4. Structural Typing: Compatibility by Shape

TypeScript's compatibility model is primarily structural.

If a value provides the members required by another type, it can often be assigned to that type.

Suppose a function accepts an object with a `name` property of type string.

A Customer object containing `name`, `email`, and `customerId` may satisfy that requirement.

The function doesn't need to know that the object came from a particular named class.

This flexibility is especially natural in JavaScript, where object literals and anonymous object structures are common.

### Where structural typing shines

Imagine a function that logs objects with an `id` property.

Many unrelated domain objects may expose such a property.

A structural interface can express the minimum capability required by the function.

The function doesn't need to force every caller to inherit from a shared base class.

This supports loose coupling.

It also makes library interoperability convenient.

### Where it becomes dangerous

Now imagine two identifiers:

HotelId is represented by a string.

CustomerId is also represented by a string.

If they are merely aliases of string, TypeScript treats them as interchangeable.

The names document developer intent, but don't necessarily create separate type identities.

Similarly, two object interfaces with identical structural members may be compatible even if the names represent distinct business concepts.

A structural checker cannot invent distinctions that the type model doesn't express.

### Branded types

TypeScript projects sometimes use branded or opaque-type patterns.

A unique symbolic property can distinguish an otherwise string-like HotelId from CustomerId at compile time.

The application can then expose constructors or parsers that produce the appropriate branded values.

This is useful because it gives the type checker additional information without necessarily changing the value's runtime representation.

But brands are still static conventions.

They do not automatically make incoming strings trustworthy.

And assertions can bypass the intended construction boundary.

The important protection comes from combining the type distinction with disciplined creation and validation.

## 5. Nominal Typing: Compatibility by Declared Identity

Now consider Java.

Suppose we declare two distinct record types.

One represents HotelId.

The other represents CustomerId.

Even if both contain a single string field, the declared types remain different.

A function accepting HotelId cannot ordinarily receive CustomerId merely because their internal fields happen to match.

This is a nominal distinction.

The declared identity matters.

### Why this is useful

Domain identifiers often have the same low-level representation but must never be confused.

Nominal types make that separation natural.

They can also provide dedicated constructors, methods, and validation logic.

The trade-off is additional declarations and sometimes conversion code.

That cost may be appropriate when the domain distinction is important.

### Java isn't purely nominal in every possible sense

Java's class and interface relationships are largely declared.

But a language's full compatibility system contains many additional rules involving primitives, arrays, generics, casts, inheritance, and runtime types.

Calling Java nominal is a useful high-level contrast with TypeScript's structural typing.

It isn't a complete description of the Java type system.

### Go: an interesting hybrid

Go demonstrates why simple labels can mislead.

Go has defined types with distinct identities.

For example, declaring HotelId and CustomerId as separate defined types based on string creates meaningful distinctions.

But Go interfaces are satisfied implicitly.

A type implements an interface when its method set satisfies the interface's requirements.

It doesn't have to declare an explicit `implements` relationship.

Thus, Go combines nominal distinctions for defined types with structural interface satisfaction.

The result is a design that encourages small capability-oriented interfaces.

### Python: static distinctions are optional

Python can use classes to create runtime-distinct domain objects.

It also supports `NewType` for static distinctions with very low runtime overhead.

A static checker can treat HotelId and CustomerId created through separate NewType declarations as distinct types.

But at runtime, NewType construction returns the underlying value essentially unchanged.

Python also supports structural typing through Protocol.

This allows static checkers to reason about objects based on supported operations without requiring explicit inheritance.

Again, one language can support multiple ways to express identity and capability.

### Rust: explicit types and traits

Rust's named types can distinguish domain values.

Its newtype pattern wraps an existing representation in a distinct struct.

Traits describe shared behavior or capabilities.

A type's trait implementations are explicit in normal Rust code, unlike Go's implicit interface satisfaction.

This allows a developer to distinguish two ideas:

The value's domain identity.

The capabilities that value supports.

The correct choice depends on whether the application needs distinct identities, interchangeable behavior, or both.

## 6. Inference: Less Writing, Not Less Checking

Type inference allows a compiler to determine types from context.

Consider a local variable assigned a number.

A statically typed language may infer its numeric type without requiring an explicit annotation.

This can reduce repetition.

But inference doesn't mean the language has stopped checking types.

The compiler still reasons about the resulting expression types and their relationships.

### Context determines how much inference is useful

Local values often have obvious types.

Public library APIs, domain boundaries, and complex generic relationships may benefit from explicit declarations.

For example, a function returning a payment state may expose a carefully defined union type.

Even if the compiler could infer a compatible shape, the explicit contract can communicate what the function promises to callers.

### Inference can preserve useful precision

Some languages and constructs preserve literal information.

Others widen an expression into a broader type.

TypeScript's `satisfies` operator can check that an expression matches a required structure while retaining useful inferred information.

We encountered that in L02.

The architectural lesson is that type annotations and inference should work together.

Use inference where it communicates the same guarantee with less noise.

Use explicit types where the boundary itself deserves a name.

### A type is not a proof of runtime truth

Remember the distinction from L01.

Inferring that a value is a string doesn't prove that it contains a valid hotel identifier.

Inferring a payment-response shape doesn't prove that the response came from the payment provider.

Type inference improves static reasoning.

It doesn't replace validation, authority, or business invariants.

## 7. Generics: Preserving a Relationship Across an Abstraction

Let's return to the booking system.

We have a repository function that retrieves records.

Suppose one version accepts a key and returns an arbitrary object.

That may be flexible, but it discards information.

The caller knows that a HotelId should retrieve a Hotel.

The function signature doesn't preserve that relationship.

A generic abstraction can.

### Generic identity

The simplest generic function returns the same kind of value it receives.

If the input is a Hotel, the output remains a Hotel.

If the input is a Customer, the output remains a Customer.

The type variable represents a relationship between argument and result.

It isn't merely a placeholder meaning "anything goes."

### Generic collections

A collection of Hotels should expose Hotels when retrieving elements.

A collection of Customers should expose Customers.

Without generics, the interface might require broad unions, casts, or runtime inspection.

Generics let the compiler preserve type information through reusable code.

### Generic constraints

Sometimes the abstraction requires a capability.

For example, a function may accept only values exposing an identifier.

A generic constraint can describe that requirement.

In TypeScript, the constraint might require a property named `id`.

In Go, an interface constraint may define permitted methods or, for generic type parameters, a type set.

In Rust, a trait bound describes required capabilities.

In Java, type parameters can have bounds.

The syntax differs.

The intellectual purpose is similar: reusable code with explicit requirements.

### Parametric polymorphism

The broader idea is called parametric polymorphism.

An operation is expressed in terms of type parameters rather than one concrete type.

This can make reusable functions safer because relationships between inputs and outputs remain visible.

But be careful.

A generic function can still contain logic errors.

The implementation may violate an intended business rule.

And a permissive or unsound type system may allow unsafe assumptions.

Generics give the checker a stronger vocabulary; they don't prove that every algorithm is correct.

## 8. Variance: The Hidden Question Behind Generic Compatibility

There is one more advanced idea worth understanding conceptually.

Suppose Dog is a subtype of Animal.

Should a collection of Dogs be usable wherever a collection of Animals is expected?

The answer depends on what operations are permitted.

If the collection is read-only, allowing code to read Dogs as Animals may be safe.

But suppose the receiving code is allowed to insert any Animal.

It might insert a Cat into what the caller still believes is a collection of Dogs.

Now the original collection's guarantee has been violated.

This is the problem variance addresses.

### Covariance and contravariance

Very roughly, covariance preserves a subtype relationship in the same direction.

Contravariance reverses the direction, especially relevant for certain function parameter relationships.

Invariance allows neither substitution without additional guarantees.

Different languages and type constructs apply different variance rules.

For application engineers, the most useful insight isn't memorizing terminology.

It's asking whether a type permits reading, writing, or both.

A producer and a consumer have different compatibility requirements.

### A useful design habit

When a collection or callback interface creates confusing type errors, examine what the code is allowed to do.

A read-only interface may support broader substitution than a mutable one.

A callback that accepts general Animals can safely handle Dogs.

A callback that accepts only Dogs cannot necessarily handle every Animal.

These rules aren't compiler pedantry.

They protect relationships between values and operations.

## 9. Product Types and Sum Types: Modeling Real States

Now return to the payment workflow.

A naive Payment interface contains optional fields for confirmation, failure reason, provider reference, and status.

The application allows combinations that shouldn't exist.

A better model distinguishes the alternatives.

### Product types

A product type combines required pieces of information.

For example, a confirmed payment might contain both a confirmation ID and a settled amount.

The value is valid only when it supplies all required components.

A record or struct is a familiar form of product type.

### Sum types

A sum type represents one of several alternatives.

Payment may be Pending, Confirmed, or Failed.

Each alternative carries different information.

In TypeScript, a discriminated union is a natural representation.

In Rust, an enum with associated data can express similar alternatives.

Java can model closed families using sealed hierarchies and records, subject to language version and design.

Go may use interfaces, explicit variants, or other patterns, although exhaustive sum-type modeling is less directly built into its ordinary language syntax.

Python can use unions and dataclasses with static analysis, while runtime validation remains important.

### The invalid-state problem

Suppose we represent Payment with one broad object.

It might contain:

`status = "pending"`

and

`confirmationId = "PAY-123"`

This state is contradictory under our domain model.

A discriminated union can make the confirmation ID available only on the Confirmed variant.

The compiler can then require the application to establish the current state before accessing confirmation-specific fields.

### Exhaustiveness

Suppose the application handles Pending, Confirmed, and Failed.

Later, the team introduces Refunded.

A well-designed closed state model can make incomplete case handling visible to the compiler.

TypeScript's `never` pattern is one approach.

Rust's exhaustive matching is another.

The benefit is particularly large when a workflow evolves over time.

A new state becomes a deliberate change to every relevant consumer.

### Don't mistake a state shape for a valid transition

Even if the type system prevents constructing a Confirmed payment without a confirmation ID, it doesn't prove that the confirmation was genuinely issued by the payment provider.

Nor does it automatically enforce which transitions are legal.

A Pending payment should not become Confirmed merely because a caller sets a field.

The transition needs appropriate authority and validation.

**Types can describe valid states. The application must still control who may create those states and under which conditions.**

## 10. Typestate: Move Some Workflow Rules Into Types

We can push the idea further.

Imagine a reservation process with distinct stages.

A draft reservation has not yet been validated.

A validated reservation has passed selected checks.

A confirmed reservation has passed the authoritative booking operation.

The application shouldn't allow a function that charges the customer to accept an arbitrary unvalidated draft.

A typestate-style design represents these stages as distinct types.

A function accepts one state and returns another.

For example, a validation operation accepts a DraftReservation and returns a ValidatedReservation.

A confirmation operation accepts a ValidatedReservation and attempts to produce a ConfirmedReservation.

This can make illegal call sequences harder to express.

### What typestate can guarantee

The compiler can reject code that attempts to call a confirmation-only function with an ordinary draft value.

It can also help prevent reading fields that aren't available before a stage completes.

This improves local workflow discipline.

### What typestate cannot guarantee

A reservation validated ten seconds ago may no longer be bookable.

The last room could have been sold by another request.

The payment provider could have rejected the charge.

The customer's account could have been suspended.

Static state transitions cannot generally freeze the outside world.

Therefore, a typestate design may improve code organization, but the authoritative transaction still needs runtime checks and coordination.

### The cost of stronger modeling

Typestate can introduce additional types, conversions, and generic parameters.

For a small CRUD application, an elaborate state-machine type architecture might create more maintenance work than it saves.

For a cryptographic protocol, transaction workflow, or safety-critical API, stronger stage restrictions may be highly valuable.

Use the technique when invalid sequencing is a real source of risk.

Don't turn every three-line operation into a miniature formal-methods research project.

## 11. Aliasing: Two Names, One Mutable Object

Now we reach our second production incident.

The booking calculation receives a Reservation object.

Another component also holds a reference to that object.

The pricing service reads the check-in date.

Another part of the application changes the check-out date.

The pricing service continues using the object, which now contains a different combination of values than it expected.

The problem is aliasing.

Two references provide access to the same underlying mutable data.

### Aliasing isn't inherently wrong

Shared references are useful.

They avoid unnecessary copying.

They allow different components to coordinate around shared state.

But sharing introduces responsibilities.

Who may modify the object?

When may modifications occur?

Can readers rely on stable values during an operation?

Does the system need a snapshot?

### The JavaScript approach

JavaScript permits objects to be referenced from multiple locations.

TypeScript's readonly declarations can restrict some mutation through checked code.

But ordinary readonly annotations don't create deep runtime immutability.

The application may choose immutable-update patterns, defensive copying, encapsulation, or other conventions.

These can be effective.

But the rules are largely enforced through design discipline and particular libraries or runtime mechanisms.

### The memory-management connection

If a long-lived callback or cache retains a reference, the object may remain reachable.

If many objects remain reachable unnecessarily, memory usage can grow.

We'll study reachability and garbage collection in L04.

For this lecture, our focus is ownership of mutable data.

The key question is not only whether an object exists.

It's who can change the object while someone else is using it.

## 12. Rust Ownership: One Accountable Owner

Rust approaches memory management and mutation with a distinctive model.

Each value has an owner.

Ownership may move between variables or functions.

When an owning value goes out of scope, its resources can be released through the relevant drop behavior.

This is checked at compile time for safe Rust code.

### Moving isn't copying

Imagine a Rust String value.

Assigning it to another variable normally moves ownership rather than automatically duplicating the underlying heap data.

The original variable can no longer be used as the owner after the move.

This avoids a situation where two independent owners both believe they should release the same resource.

If a separate copy is genuinely needed, the programmer can explicitly clone the value when the type supports that operation.

The explicit clone makes a potentially costly duplication visible.

### Copy types

Some simple values implement Rust's Copy trait.

For example, ordinary integer values can generally be copied when assigned.

In that case, both variables remain usable.

This is different from moving ownership of a heap-owning String.

The rules depend on the type.

### Why ownership matters

Without clear ownership rules, memory-management errors can include double frees, use-after-free, and dangling references.

Rust's ownership model prevents important classes of these errors in safe code.

It does so without requiring a general tracing garbage collector for ordinary ownership-based resource lifetimes.

But there is more to ownership than memory cleanup.

It also constrains how data can be borrowed and mutated.

## 13. Borrowing: You Can Use Data Without Owning It

Suppose a function needs to inspect a reservation.

It shouldn't necessarily take ownership of the reservation and prevent the caller from using it afterward.

Rust supports borrowing.

A reference allows code to access data without transferring ownership.

### Shared references

Rust allows multiple shared references to data under its ordinary borrowing rules.

These references permit observation without unrestricted direct mutation.

This is useful when several parts of a program need to read the same information.

### Mutable references

Rust also supports mutable references.

A mutable borrow provides controlled access for changing a value.

Under ordinary safe borrowing rules, the program cannot simultaneously use conflicting shared and mutable references to the same data.

The compiler enforces restrictions based on the relevant borrow lifetimes.

### The central exclusivity rule

A useful first approximation is:

You may have multiple shared borrows, or one exclusive mutable borrow, but not overlapping conflicting uses.

There are nuances involving interior mutability and specialized types, but this is the right starting model.

Why does the rule matter?

Imagine the pricing service reading reservation dates while another function mutates those same dates through a different alias.

The exclusivity model prevents certain conflicting access patterns from being expressed through ordinary safe references.

That doesn't prove the dates are correct.

It does provide stronger guarantees about uncontrolled simultaneous mutation.

### Non-lexical lifetimes

A borrow doesn't necessarily remain active until the final closing brace of a block.

Rust's borrow analysis can recognize when a reference's last relevant use has occurred.

This allows later borrows that would otherwise appear to overlap syntactically.

The goal isn't to prohibit mutation forever.

It's to make the periods of access compatible.

## 14. Lifetimes: A Reference Must Not Outlive Its Data

Imagine a function creates a temporary String.

It then returns a reference to that String.

After the function returns, the local owning value is gone.

What should the reference point to?

Without protection, the program might hold a dangling reference.

Rust's lifetime system helps prevent this in safe code.

A reference must remain valid for the period in which it is used.

The compiler checks relationships between references and the data they refer to.

### Lifetimes aren't timers

A lifetime annotation doesn't instruct the runtime to keep an object alive for a particular number of seconds.

It describes relationships between the validity of references.

For example, a function returning a reference derived from one of its inputs may need to express which input's lifetime constrains the returned reference.

The annotation gives the compiler information about a relationship.

It doesn't dynamically extend the lifetime of a destroyed value.

### Why this matters for API design

Functions can expose ownership choices through their signatures.

Does a function consume a value?

Borrow it immutably?

Borrow it mutably?

Return an owned result?

Return a reference tied to an input?

These distinctions help callers reason about resource lifetime and mutation.

The cost is additional conceptual complexity, especially when designing APIs around shared data or long-lived references.

Rust makes certain responsibilities explicit that other languages often leave to conventions or runtime mechanisms.

## 15. Memory Safety Isn't Business Safety

Now comes the most important qualification.

Suppose we rewrite the booking system in Rust.

All code is safe Rust.

The compiler accepts the program.

There are no dangling references or unsynchronized data races in the ordinary safe code.

Can the application still sell the last hotel room twice?

Yes.

Imagine two independent backend processes.

Each opens a database transaction.

Each reads one room remaining.

Each attempts to create a reservation without appropriate database coordination.

Both may make locally valid decisions using correctly owned data.

Rust's borrow checker cannot automatically serialize transactions across two processes and one external database.

The problem belongs to distributed consistency and transactional isolation.

### Data race versus race condition

A data race is a particular kind of unsynchronized conflicting memory access.

Rust's safety model prevents data races in safe code under its guarantees.

A race condition is a broader category of correctness failure caused by the timing or ordering of events.

Two individually safe database requests can form a race condition.

Two messages can arrive in an unfortunate order.

An external payment can succeed just before a timeout.

A type system may prevent memory unsafety without preventing every race condition.

This distinction is essential.

### Locks don't solve business invariants automatically

Even within one process, using a mutex can protect a shared object from simultaneous mutation.

But if the authoritative state lives in a database accessed by several processes, a local mutex protects only the local process's coordination.

Other processes can still operate concurrently.

The correct solution requires coordination at the scope of the actual invariant.

For inventory, that might involve an atomic database update, appropriate transaction isolation, a uniqueness constraint, or another design that prevents overselling.

**Protecting memory access and protecting business truth are two different engineering jobs.**

## 16. Ownership Models Are Architectural Choices

We've compared several ways to manage mutation and state.

TypeScript and JavaScript often rely on garbage collection, references, and application-level immutability conventions.

Java also uses managed memory and can enforce selected access and type relationships through its language and library mechanisms.

Go provides garbage collection and explicit concurrency constructs, with application responsibility for synchronized shared-state access.

Rust uses ownership and borrowing to enforce significant memory-safety constraints statically in safe code.

These choices influence how applications are written.

But none is universally superior for every workload.

### The cost of flexibility

Flexible shared references can make application code concise.

They can also make it harder to determine who changed an object unexpectedly.

### The cost of stricter ownership

Ownership restrictions can make memory lifetime and mutation more predictable.

They can also require different API designs, explicit cloning, or more deliberate shared-state abstractions.

### The role of application architecture

Regardless of language, an application can often reduce mutation hazards by limiting shared mutable state.

Immutable snapshots, explicit state transitions, and message passing can make ownership easier to reason about.

In many backend services, the most important shared state is not even inside the process.

It's in databases, caches, brokers, and external APIs.

The language's local memory guarantees remain valuable, but the system's consistency design must address the actual distributed state.

## 17. Static Guarantees, Runtime Validation, and Authority

Let's return to the third incident.

The payment workflow receives an object containing:

`status: "confirmed"`

The field has the correct name and expected type.

The object passes structural validation.

Can we now mark the reservation paid?

Not necessarily.

Who produced the object?

Was it received through an authenticated channel?

Does it refer to the correct payment operation?

Is the confirmation authentic and still valid?

Could a malicious client simply invent the same JSON fields?

A type system can't establish those facts from shape alone.

### Three distinct checkpoints

The first checkpoint is **static compatibility**.

Does the source code use the value according to its declared type relationships?

The second is **runtime validity**.

Does the actual value satisfy the expected representation and domain constraints?

The third is **authority and consistency**.

Does the fact come from a trusted source, and does it remain true under the relevant business rules?

A payment response can pass the first two checks and fail the third.

### The secure transition

A robust payment workflow might accept a provider response through a verified integration, validate its structure, correlate it with the intended payment operation, and persist the state change transactionally.

It must also handle retries, duplicate callbacks, and ambiguous outcomes.

The type system can help model the possible states and reduce invalid local code paths.

It cannot replace the provider authentication or durable state-transition logic.

This is not a weakness peculiar to TypeScript.

It is a general limit of what static source analysis can establish about external reality.

## 18. How to Choose the Right Type-System Strength

We've now encountered several techniques.

Nominal distinctions can prevent swapped identifiers.

Structural typing supports flexible capability-based interoperability.

Generics preserve type relationships.

Sum types and exhaustive matching can prevent impossible local state combinations.

Ownership and borrowing can restrict conflicting memory access.

Typestate can make invalid operation sequences harder to express.

Why not use all of them everywhere?

Because each technique has a maintenance cost.

### Model important risks precisely

If a domain frequently confuses CustomerId and HotelId, introduce distinct identifier types.

If an application has a complicated state machine, use a representation that makes valid alternatives explicit.

If a system suffers from shared-mutation bugs, adopt a clear ownership or immutability policy.

If a library is designed for broad reuse, generics may preserve valuable relationships.

The common theme is that the extra type structure should eliminate an important ambiguity or failure mode.

### Don't invent complexity without a corresponding problem

A tiny internal script may not need a sophisticated branded identifier framework.

A simple status flag may not need six layers of typestate generics.

A small helper may not need an elaborate abstract interface hierarchy.

Complex types are still software.

They need documentation, testing, and maintenance.

A type system should make programs easier to reason about.

If the model becomes harder to understand than the behavior it protects, reconsider the design.

### Think in guarantees

Ask what error the design will catch.

Would this distinction prevent a real category of accidental substitutions?

Would this union force callers to handle an important state?

Would this ownership boundary eliminate uncontrolled mutation?

Would this generic signature preserve a relationship otherwise lost?

If the answer is concrete, the complexity may be worthwhile.

If the answer is only "it looks more strongly typed," the design may be decorative.

## 19. The Senior Engineer's Type-System Review

Imagine reviewing a new payment module.

The team proposes a typed request object, a generic repository, and a state machine.

How would you evaluate it?

Start with domain identity.

Are different identifiers represented distinctly where confusion would be dangerous?

Next examine state representation.

Can the model express contradictory states, such as a payment marked Confirmed without a confirmation?

Then examine ownership.

Can multiple components mutate the same important value unexpectedly?

Are there clear rules about copying, sharing, and updates?

Now inspect external boundaries.

Where do values enter from HTTP requests, databases, messages, and third-party services?

Which validators establish runtime truth?

Finally, identify authoritative business operations.

Which state transitions require database transactions, authenticated provider responses, or concurrency control?

That last step is essential.

The strongest type model in the world can still sit on top of an unsafe business workflow.

A senior engineer should know when to improve the type system—and when the actual problem lies somewhere else.

## 20. The Oral Examination

Answer each scenario aloud before reading the solutions. Explain which language-level guarantee helps and which additional guarantees remain necessary.

### Challenge 1 — Two Strings, Two Meanings

A TypeScript function expects a HotelId.

A caller supplies a CustomerId.

Both are represented as strings, and the compiler accepts the call.

How would you make the distinction meaningful?

What limitation remains after introducing distinct types?

### Challenge 2 — Structural Versus Nominal

Two objects have identical fields but represent different domain concepts.

How might TypeScript treat them?

How might distinct Java record types treat them?

What does Go demonstrate about combining nominal and structural ideas?

### Challenge 3 — The Generic Repository

A repository function accepts and returns `any`.

The caller repeatedly casts results to the expected type.

What information is lost?

How would generics help preserve the relevant relationship?

### Challenge 4 — The Impossible Payment State

A payment object can contain `status: "pending"` together with a confirmation identifier and an error message.

Why is this model weak?

How would a discriminated union or equivalent sum type improve it?

### Challenge 5 — The Compiler-Approved Confirmation

A payment response has the correct structure and contains `status: "confirmed"`.

A developer treats it as proof of successful payment.

Which checks are still missing?

### Challenge 6 — The Shared Reservation

Two components hold references to the same mutable reservation object.

One changes the dates while another calculates the total.

What is the ownership problem?

How can different language designs address it?

### Challenge 7 — Rust and Double Booking

A team rewrites the booking service in safe Rust and concludes that race conditions are now impossible.

Why is that conclusion incorrect?

Distinguish a data race from a distributed business race.

### Challenge 8 — The Overengineered Type Model

A developer introduces seventeen generic parameters, several branded types, and an elaborate typestate hierarchy for a simple internal configuration object.

How would you judge whether this complexity is justified?

## 21. Solutions and Discussion

### Solution 1 — Make identifier types distinct

A branded or opaque-type pattern can distinguish HotelId from CustomerId in TypeScript.

A dedicated constructor or parser can establish the intended category.

But the compiler still cannot prove that the referenced hotel currently exists or is available.

That requires runtime interaction with authoritative state.

### Solution 2 — Compatibility depends on the language model

TypeScript primarily uses structural compatibility, so objects with matching required shapes may be compatible.

Distinct Java record types have nominal identities and aren't automatically interchangeable because their fields match.

Go uses distinct defined types while also supporting structural interface satisfaction through method sets.

The appropriate design depends on whether identity or capability is the important relationship.

### Solution 3 — Generics preserve input-output relationships

Using `any` discards useful static information.

The caller must reconstruct or assert the expected type.

A generic repository can preserve relationships between an entity type, identifier type, and result type.

That reduces casts and catches certain mismatches.

It does not prove that returned database records satisfy every business invariant.

### Solution 4 — Represent alternatives explicitly

A single broad object with optional fields permits contradictory combinations.

A discriminated union can distinguish Pending, Confirmed, and Failed variants.

Each variant carries the fields appropriate to that state.

Exhaustive checking can reveal missing handling when new states are added.

The application still needs to enforce authorized state transitions.

### Solution 5 — Structure isn't authority

The application must establish that the response came from the intended provider through appropriate authenticated communication.

It must correlate the response with the correct payment operation, validate business constraints, and handle duplicate or delayed messages.

A valid shape doesn't prove the represented fact is authentic.

### Solution 6 — Mutable aliases have no clear coordination policy

Two references expose the same mutable value.

One component can change data another component assumed would remain stable.

Possible responses include immutable snapshots, defensive copying, encapsulation, controlled mutation, or language-enforced borrowing and ownership rules.

The appropriate strategy depends on the data's lifetime and sharing requirements.

### Solution 7 — Memory safety doesn't imply distributed consistency

Rust's safe ownership and borrowing model prevents important memory-safety violations and data races.

But two independent database transactions can still race over the last available room.

The inventory invariant must be enforced through appropriate database or distributed coordination mechanisms.

A data race is a particular memory-access violation; a race condition is a broader timing-dependent correctness problem.

### Solution 8 — Evaluate the specific guarantee gained

Ask which real invalid states or incorrect operations the type model prevents.

If a distinction reliably catches important mistakes, the complexity may be justified.

If the model introduces substantial maintenance cost without protecting a meaningful invariant, simplify it.

The goal is stronger reasoning, not maximum type-level ceremony.

## 22. The Mental Model Worth Keeping

A type system is a language for describing and enforcing selected relationships between values and operations.

Structural typing emphasizes compatible shapes.

Nominal typing emphasizes declared identities.

Generics preserve relationships across reusable abstractions.

Sum types can express valid alternatives.

Ownership and borrowing can constrain data lifetime and mutation.

These are powerful mechanisms, but they solve different problems.

Whenever designing a type model, ask:

**What invalid program does this type reject? What valid program does it allow? What facts does the compiler still have to assume? What runtime or external authority must establish the remaining guarantees?**

That's the distinction between using types as documentation and using types as engineering tools.

## 23. Next Lecture — CS220-L04: References, Garbage Collection, and Memory Leaks

We've learned that values can be shared, moved, borrowed, copied, and protected through different language mechanisms.

Now a new question appears.

What happens to those values while the program runs?

A Node.js service can slowly consume more memory even when its garbage collector is working correctly.

A closure may retain an entire object graph long after its creator returned.

A cache may preserve thousands of entries the business no longer needs.

A frontend component may register event listeners that keep otherwise disposable state alive.

And the application's process memory may grow for reasons unrelated to ordinary JavaScript heap objects.

In the next lecture, we'll examine stack and heap concepts, references, reachability, garbage collection, memory retention, and the practical methods for diagnosing leaks.

Today was about who is allowed to use data.

Next we'll investigate why data remains alive—and what it costs.

*The spoken lecture ends here. The remaining material is for hands-on experiments and screen-based revision.*

---

## Optional Practical Lab — Five Type Systems, One Booking Domain

**Objective:** Compare what the type systems of TypeScript, Python, Java, Go, and Rust can express using the same small domain problem.

You don't need all five language toolchains installed. The exercises can be read and reasoned about first, then executed in whichever environments you have available.

### Lab A — TypeScript: Distinguish Domain Identifiers

Consider these ordinary aliases:

```typescript
type HotelId = string;
type CustomerId = string;

function loadHotel(id: HotelId) {
  return id;
}

const customerId: CustomerId = "C-123";

loadHotel(customerId);
```

TypeScript accepts the call because both aliases are strings.

Now introduce branded types:

```typescript
declare const hotelBrand: unique symbol;
declare const customerBrand: unique symbol;

type HotelId = string & {
  readonly [hotelBrand]: true;
};

type CustomerId = string & {
  readonly [customerBrand]: true;
};

function loadHotel(id: HotelId): void {
  console.log(id);
}

const customerId = "C-123" as CustomerId;

// Compile-time error:
// loadHotel(customerId);
```

The branded types are now incompatible in ordinary checked code.

**Investigate:** Why is the code using assertions to construct these example values still not suitable as a trusted runtime boundary?

Design a `parseHotelId(input: unknown): HotelId` function that validates a recognized identifier format before returning the branded value.

Explain why even this parser cannot prove that the hotel currently exists.

### Lab B — TypeScript: Make Invalid Payment States Harder to Express

Start with an overly permissive model:

```typescript
type Payment = {
  status: "pending" | "confirmed" | "failed";
  confirmationId?: string;
  error?: string;
};
```

This accepts contradictory combinations.

Replace it with:

```typescript
type Payment =
  | {
      status: "pending";
      requestId: string;
    }
  | {
      status: "confirmed";
      requestId: string;
      confirmationId: string;
    }
  | {
      status: "failed";
      requestId: string;
      error: string;
    };
```

Now implement an exhaustive handler:

```typescript
function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${String(value)}`);
}

function describePayment(payment: Payment): string {
  switch (payment.status) {
    case "pending":
      return `Pending ${payment.requestId}`;

    case "confirmed":
      return `Confirmed ${payment.confirmationId}`;

    case "failed":
      return `Failed: ${payment.error}`;

    default:
      return assertNever(payment);
  }
}
```

Add a fourth state named `refunded`.

Observe how the exhaustive check helps identify incomplete handling.

**Question:** Does the type model prove that a confirmed payment was actually settled by the provider?

### Lab C — Python: NewType Versus Runtime Identity

Python's NewType creates a static distinction without creating a separate runtime class.

```python
from typing import NewType

HotelId = NewType("HotelId", str)
CustomerId = NewType("CustomerId", str)

def load_hotel(hotel_id: HotelId) -> str:
    return hotel_id

hotel = HotelId("H-123")
customer = CustomerId("C-123")

print(load_hotel(hotel))

# A static type checker should reject this:
# load_hotel(customer)

print(type(hotel))
```

Use mypy or Pyright if available.

**Investigate:** Why does Python execute the underlying string representation even though static checkers can distinguish the new types?

Then compare this approach with defining actual classes that enforce identity at runtime.

### Lab D — Go: Defined Types and Implicit Interfaces

Consider distinct identifier types in Go:

```go
package main

import "fmt"

type HotelId string
type CustomerId string

func LoadHotel(id HotelId) {
    fmt.Println("Loading hotel:", id)
}

func main() {
    hotel := HotelId("H-123")
    customer := CustomerId("C-123")

    LoadHotel(hotel)

    _ = customer

    // This should fail to compile:
    // LoadHotel(customer)
}
```

Now define a small interface requiring a `String() string` method.

Create a HotelId method satisfying that interface.

Observe that the type need not explicitly declare `implements`.

**Question:** How does Go combine nominal defined types with structural interface satisfaction?

### Lab E — Java: Declared Identity

Create two records in a Java environment supporting records:

```java
record HotelId(String value) {}
record CustomerId(String value) {}

class Example {
    static void loadHotel(HotelId id) {
        System.out.println(id.value());
    }

    public static void main(String[] args) {
        HotelId hotel = new HotelId("H-123");
        CustomerId customer = new CustomerId("C-123");

        loadHotel(hotel);

        // This should not compile:
        // loadHotel(customer);
    }
}
```

**Question:** Why are the two records incompatible even though both wrap strings?

Would a record constructor automatically prove that the represented hotel exists?

### Lab F — Rust: Move, Borrow, and Clone

First, predict whether this program compiles:

```rust
fn main() {
    let first = String::from("reservation");
    let second = first;

    println!("{second}");

    // This should not compile:
    // println!("{first}");
}
```

Now use borrowing:

```rust
fn length_of(value: &String) -> usize {
    value.len()
}

fn main() {
    let reservation = String::from("R-123");

    let length = length_of(&reservation);

    println!("{reservation} has {length} bytes");
}
```

The function reads the String without taking ownership.

Next, test an exclusive mutable borrow:

```rust
fn add_suffix(value: &mut String) {
    value.push_str("-updated");
}

fn main() {
    let mut reservation = String::from("R-123");

    add_suffix(&mut reservation);

    println!("{reservation}");
}
```

**Explain:** Which problems does the borrow checker prevent? Which business conditions remain completely outside its knowledge?

### Lab G — The Ownership Review

Imagine a reservation object shared by:

- A pricing calculator.
- A date-editing form.
- A background availability checker.
- A persistence service.

Design an ownership and mutation strategy.

You might choose immutable snapshots, a single state owner, controlled mutation APIs, or another defensible model.

Explain how your design prevents one component from changing values another component assumes are stable.

Then explain how you would preserve consistency when the same reservation is accessed by several independent backend processes.

### Lab H — The Architecture Decision

Choose a type-design approach for these four problems.

**Problem A:** Prevent mixing CustomerId and HotelId.

**Problem B:** Represent a payment that must be Pending, Confirmed, or Failed.

**Problem C:** Prevent uncontrolled mutation of a shared in-memory configuration object.

**Problem D:** Prevent two separate application instances from selling the last room.

For each problem, identify whether the primary solution belongs in:

- Static types.
- Runtime validation.
- Ownership and mutation discipline.
- Database or distributed coordination.

A strong answer may use several mechanisms for one problem, but it should identify which mechanism actually enforces the critical invariant.

---

## Further Reading

1. [TypeScript — Type Compatibility](https://www.typescriptlang.org/docs/handbook/type-compatibility.html) — Structural typing and compatibility.
2. [TypeScript — Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html) — Preserving relationships between types.
3. [TypeScript — Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) — Discriminated unions and exhaustive checking.
4. [Java Language Specification — Types, Values, and Variables](https://docs.oracle.com/javase/specs/jls/se25/html/jls-4.html) — Java's type model.
5. [Go Language Specification](https://go.dev/ref/spec) — Defined types, interfaces, method sets, and generics.
6. [Go FAQ — Interfaces](https://go.dev/doc/faq) — Implicit interface satisfaction.
7. [Python — typing](https://docs.python.org/3/library/typing.html) — NewType, Protocol, generics, and type annotations.
8. [Rust Book — Understanding Ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) — Moves, Copy, Clone, and ownership.
9. [Rust Book — References and Borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html) — Shared and mutable borrowing.
10. [Rust Book — Generic Types, Traits, and Lifetimes](https://doc.rust-lang.org/book/ch10-00-generics.html) — Type parameters, traits, and reference lifetimes.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is deliberately fenced for screen-based revision.*

```text
CS220-L03 — TYPE SYSTEMS, GENERICS, OWNERSHIP, VALID STATES

CENTRAL PRINCIPLE

A type system enforces selected relationships
between program values and operations.

It doesn't automatically establish current
external facts or business correctness.

THREE INCIDENTS

1. CustomerId passed as HotelId
   -> Domain identity problem

2. Shared reservation mutated unexpectedly
   -> Aliasing / ownership problem

3. Structurally valid fake payment confirmation
   -> Authority / runtime validation problem

STATIC VS DYNAMIC

Static typing:
  Properties checked before execution

Dynamic typing:
  Runtime values determine operations

Python:
  Dynamic runtime typing + optional static hints

TypeScript:
  Static checking over JavaScript semantics

TYPES AS CONTRACTS

Shape:
  Which members/operations exist?

Identity:
  Which domain concept is represented?

State:
  Which alternatives are valid?

Ownership:
  Who may use or modify data?

STRUCTURAL TYPING

Compatibility largely by required members.

TypeScript:
  Primarily structural
  Flexible object composition
  Same shape can imply compatibility

NOMINAL TYPING

Compatibility depends on declared identities.

Java:
  Named classes/records/interfaces

Rust:
  Distinct named types/newtypes

Go:
  Distinct defined types
  Implicit structural interface satisfaction

Python:
  NewType -> static distinctness
  Protocol -> structural static typing
  NewType does not create a distinct runtime class

BRANDED TYPES

TypeScript pattern:
  string & { readonly [brand]: ... }

Useful for:
  HotelId vs CustomerId
  ReservationId vs PaymentId

Limits:
  Assertions can bypass
  No automatic runtime validation
  No proof of external existence

INFERENCE

Compiler derives types from context.
Inference != dynamic typing.
Explicit types useful at domain/public boundaries.

GENERICS

Preserve relationships between inputs and outputs.

Example:
  identity<T>(value: T): T

Generic constraints:
  Express required capabilities

Generics don't prove business invariants.

VARIANCE

Covariance:
  Subtyping preserved in same direction

Contravariance:
  Subtyping relation reversed

Invariance:
  Neither unrestricted substitution

Important when:
  Mutable collections
  Function parameters
  Producer/consumer APIs

PRODUCT TYPES

Combine required values.

Example:
  ConfirmedPayment has:
    requestId + confirmationId

SUM TYPES

Choose one alternative.

Payment =
  Pending
  | Confirmed
  | Failed

Discriminated unions:
  Narrow by status
  Enable exhaustive handling

MAKE INVALID STATES UNREPRESENTABLE

Use types to exclude contradictory local states.

But:
  Valid representation != authentic payment
  Valid state != authorized transition

TYPESTATE

Encode workflow stage in type:
  Draft -> Validated -> Confirmed

Can prevent invalid local call sequences.
Cannot freeze changing external state.

ALIASING

Two references, one mutable object.

Risk:
  One component changes state another assumes stable.

Mitigations:
  Immutable snapshots
  Defensive copies
  Controlled mutation
  Ownership/borrowing rules

RUST OWNERSHIP

Each value has an owner.
Ownership can move.
Owned resources dropped when appropriate.

Move != clone.

Copy:
  Simple Copy types remain usable after assignment.

Clone:
  Explicit duplication where supported.

BORROWING

&T:
  Shared reference

&mut T:
  Mutable borrow

Ordinary safe borrowing:
  Multiple shared uses OR
  Exclusive mutable access

No conflicting overlapping borrows.

LIFETIMES

Describe reference-validity relationships.
References cannot outlive their referents in safe Rust.
Annotations don't extend runtime object lifetime.

DATA RACE VS RACE CONDITION

Data race:
  Unsynchronized conflicting memory access

Race condition:
  Broader timing-dependent correctness failure

Rust prevents data races in safe code.
Rust cannot automatically prevent double booking
across independent database transactions.

THREE CHECKPOINTS

1. Static compatibility
   Does program use types correctly?

2. Runtime validity
   Does actual input satisfy the contract?

3. Authority and consistency
   Is external fact authentic/current/authorized?

TYPE DESIGN RULE

Introduce complexity when it prevents
a meaningful category of errors.

Don't create elaborate type systems
merely for intellectual decoration.

SENIOR REVIEW

What wrong program does the type reject?
What important program does it allow?
What runtime assumptions remain?
Who owns mutable state?
Which external invariant needs authority?

SENIOR LINE

  "I use types to distinguish domain identities,
   preserve generic relationships, represent valid
   states, and constrain ownership. But I don't
   mistake static guarantees for proof of runtime
   authority, transactional correctness, or
   distributed business invariants."
```
