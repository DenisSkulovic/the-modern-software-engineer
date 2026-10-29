---
id: CS360-L02
course: CS360
title: "Arrays, Strings, Hashing, and Sliding Windows"
type: elective
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS360-L01
next: CS360-L03
---

# CS360 — Algorithms and Coding Interview Lab

## Lecture 02: Arrays, Strings, Hashing, and Sliding Windows

*Your service processes a million events. A straightforward algorithm repeatedly scans the same records and takes minutes. Another implementation visits each record once, remembers a few facts, and finishes almost immediately. The difference isn't clever syntax. It's knowing what information can be preserved as the computation moves forward.*

# Part I — Intuition

## The picture to carry in your head

Imagine a security analyst investigating a stream of login attempts.

Each event records a user, timestamp, and whether the attempt succeeded.

The analyst needs to answer several questions.

Has this user appeared before?

Which users appear most frequently?

How many failures occurred in the last hundred attempts?

What's the longest consecutive stretch containing at most two failures?

And how many periods have a total risk score equal to a particular target?

These sound like different problems. And to some extent, they are.

But they share a useful characteristic: the data is arranged in a sequence, and the answer depends on information we can accumulate while moving through it.

The naïve approach is to repeatedly revisit old events.

For every new login, scan all previous logins to detect duplicates.

For every group of one hundred events, count failures from scratch.

For every possible interval, recalculate its total risk score.

This works for small inputs.

For a million records, it may perform enormous amounts of unnecessary work.

A better approach asks:

**What information did we already discover, and how can we preserve exactly what's needed for the next step?**

That question leads us to hashing, two pointers, sliding windows, and prefix sums.

## 1. Remembering what you've seen: hashing

Suppose we're scanning login identifiers.

The first identifier is Alice.

Then Bob.

Then Charlie.

Then Alice appears again.

How do we recognize that we've seen Alice?

We could inspect every previous event.

But a hash set provides a more direct approach.

After processing each event, we record the identifier in a set.

When a new event arrives, we ask whether its identifier is already present.

The set represents our memory of the past.

This turns repeated membership searches into expected constant-time operations.

But what if we need to know how many times each user appeared?

A set isn't enough.

Now we need a hash map associating identifiers with counts.

The distinction is simple:

A **set** answers whether something is present.

A **frequency map** answers how many times it appears.

These tools don't solve the problem on their own. They let us maintain the particular information the problem requires.

## 2. When order gives us permission to skip work

Now imagine a sorted list of numerical event scores.

We want to find two scores whose sum equals a target.

One approach is to test every pair.

But because the list is sorted, we know something about the values at its boundaries.

The leftmost score is the smallest.

The rightmost score is the largest.

Suppose their sum is too small.

Moving the right boundary left would make the sum no larger.

So that can't help us reach the target while keeping the left value fixed.

Instead, we advance the left boundary to a larger number.

If the sum is too large, we move the right boundary toward smaller values.

This is the **two-pointer technique**.

It works because the ordering lets us rule out possibilities without examining them individually.

The algorithm is not merely moving two indices around.

It is using a mathematical property to prove that discarded candidates cannot contain a solution.

## 3. A fixed window: stop recounting the same events

Our analyst wants the maximum number of failed logins in any consecutive block of one hundred attempts.

A straightforward approach counts failures in the first hundred events.

Then counts them again in events two through one hundred and one.

Then again in events three through one hundred and two.

But adjacent windows share almost all their elements.

Why recount ninety-nine events?

Instead, maintain the current count.

When the window advances by one position, remove the contribution of the event leaving the window and add the contribution of the new event entering it.

We update one maintained value rather than recomputing an entire hundred-element block.

That's a **fixed-size sliding window**.

The window moves.

The state changes incrementally.

And each event is handled only a small number of times.

## 4. A variable window: maintain a condition

Now the analyst asks a different question.

"What's the longest consecutive stretch of login attempts containing at most two failures?"

The window no longer has a fixed length.

We want it to grow as far as possible while preserving a condition.

Begin with an empty interval.

Extend its right boundary.

Count failures as they enter.

When the interval contains more than two failures, move the left boundary forward, removing the events that leave.

Continue until the window is valid again.

Keep the maximum valid length.

This is a **variable-size sliding window**.

The crucial idea is not the two indices themselves.

It's the invariant:

**After restoring the window, its contents satisfy the allowed-failure constraint.**

Because each event enters once and leaves at most once, the total movement can be linear.

But this style of window doesn't work for every problem.

Its correctness depends on how the relevant property changes when elements enter or leave.

That assumption is something we'll examine carefully.

## 5. Prefix sums: remember the total so far

Finally, the analyst assigns each event a numerical risk score.

Some scores are positive; others may be negative.

We want to count consecutive periods whose total risk equals a target.

One approach calculates the sum of every possible interval.

That's expensive.

Instead, imagine maintaining the sum of all scores we've seen so far.

At any position, the sum of an interval can be calculated from two prefix sums: the total up to the end, minus the total before the beginning.

So if we know the current prefix sum, the question becomes:

"Have we previously seen a prefix sum that differs from this one by exactly the target?"

A frequency map can answer that.

This combines two ideas.

Prefix sums transform interval totals into differences between accumulated values.

Hashing remembers how often those accumulated values occurred.

The result can count qualifying intervals in expected linear time—even when negative values make a conventional sliding-window technique inappropriate.

## 6. The common principle

We've encountered several techniques, but the underlying idea is the same.

Instead of repeatedly rediscovering information, maintain a compact representation of the part of the past that still matters.

A set remembers membership.

A map remembers counts or positions.

Two pointers exploit ordering.

A sliding window maintains properties of a moving interval.

Prefix sums preserve cumulative information.

The creative part of solving an interview problem is discovering **which information is sufficient**.

Remember too little, and you can't answer correctly.

Remember too much, and you waste time or memory.

Remember the right thing, and a problem that seemed quadratic may become linear.

## Three questions before the Deep Dive

1. Why does a hash set solve duplicate detection but not a problem requiring the number of occurrences?
2. What property of sorted numbers justifies moving only one pointer when a pair's sum is too high or too low?
3. What must remain true for a sliding window to shrink safely without missing a better answer?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. First identify what kind of sequence problem you have

Before selecting an algorithm, we need to clarify the structure of the requested answer.

Consider an array of event scores.

The interviewer asks for a contiguous group of events with a particular total.

That's a **subarray** problem.

A subarray consists of consecutive elements. If we choose indices three through seven, we include every element between them.

Now suppose the interviewer asks for a sequence of selected events that preserves their original order but permits skipping elements.

That's a **subsequence** problem.

A subsequence can omit elements between selected positions.

The distinction matters enormously.

A sliding window naturally represents a contiguous region.

It doesn't automatically solve a general subsequence problem.

Similarly, a substring is contiguous within a string's chosen unit of representation.

A subsequence of characters can skip characters.

Those are different search spaces.

### Why this is your first diagnostic question

Suppose we want a maximum-sum contiguous interval.

Prefix sums or sliding windows may be relevant.

Now suppose we want any collection of elements whose sum equals a target, regardless of position.

That can be a fundamentally different problem with very different complexity.

Recognizing the difference between contiguous and arbitrary selection should happen before writing code.

It is one of the easiest ways to avoid choosing a completely inappropriate pattern.

## 2. Hash sets: convert repeated searching into memory

Our event processor receives a stream of identifiers.

We want to detect whether the same identifier has appeared previously.

The brute-force solution compares each new identifier against all earlier identifiers.

For n distinct identifiers, that can require a quadratic number of comparisons.

Now introduce a hash set.

Before processing the next identifier, our set contains every identifier previously encountered.

When a new identifier arrives, we check membership.

If it already exists, we've found a repetition.

Otherwise, we add it.

### The invariant

Before each iteration:

**The set contains exactly the identifiers from the portion of the sequence already processed.**

This invariant makes the algorithm correct.

If the current identifier is in the set, it appeared earlier.

If it isn't, adding it preserves the invariant for the next iteration.

### Complexity

With typical hash-table behavior, membership checks and insertions take expected constant time.

Processing n events therefore takes O(n) expected time.

The set may contain up to n distinct identifiers, giving O(n) additional space.

That's a trade-off.

We've reduced repeated computation by storing information about the past.

### When a set isn't enough

Now change the question.

Instead of detecting whether an identifier has appeared, count how many times each identifier occurs.

A set cannot distinguish one occurrence from twelve.

We need a map from identifier to frequency.

As each identifier arrives, increment its count.

This is still expected linear time, but the maintained state now captures multiplicity.

The key question is not "Can I use a hash map?"

It's "What information must I preserve for the next operation?"

## 3. Frequency maps: counting without losing information

Consider the event sequence:

Alice, Bob, Alice, Charlie, Alice.

A set tells us that Alice, Bob, and Charlie occurred.

A frequency map tells us that Alice occurred three times, while Bob and Charlie each occurred once.

That distinction becomes essential when processing moving windows.

Suppose a window contains Alice twice.

When the left boundary advances past one Alice event, Alice is still present in the window.

If we simply remove Alice from a set, we incorrectly claim that the window no longer contains her.

A frequency map avoids this.

It records two occurrences before removal.

After removing one, the count becomes one.

Alice remains present.

Only when the count reaches zero can we remove the entry entirely.

### A recurring interview mistake

Candidates sometimes begin with a set because the problem mentions uniqueness.

But if elements can enter and leave a window, we must ask whether multiple copies may coexist.

If yes, a frequency map or last-position structure may be necessary.

The data structure must represent the state accurately throughout the algorithm.

## 4. Two pointers: exploiting an ordered search space

Let's examine a sorted numerical array.

Our task is to find two distinct elements whose sum equals a target.

The naïve solution tries every pair in O(n²) time.

But the array is sorted.

That gives us a useful ordering guarantee.

Place one pointer at the beginning and one at the end.

Calculate the sum of those two values.

If the sum equals the target, we're done.

If the sum is too small, move the left pointer right.

If the sum is too large, move the right pointer left.

Continue while the left pointer is before the right.

### Why moving left is safe when the sum is too small

Suppose the current smallest remaining value is a, and the largest is b.

Their sum is below the target.

Any other candidate paired with a must use a value no larger than b.

So every remaining pair containing a also has a sum below the target.

We can discard a from consideration.

Advancing the left pointer is safe.

### Why moving right is safe when the sum is too large

Now suppose a plus b exceeds the target.

Any other candidate paired with b uses a value no smaller than a.

So every remaining pair containing b also exceeds the target.

We can discard b.

Moving the right pointer left is safe.

### The invariant

At every step:

**Any pair that can still form the target must lie within the current pointer boundaries.**

Every pointer movement removes candidates we've proved impossible.

Neither pointer moves backward.

The algorithm takes O(n) time once the data is sorted.

If the input is unsorted, sorting first may require O(n log n) time and additional space depending on whether we're permitted to modify it.

### What if numbers are negative?

The method still works for a sorted numerical array.

Its proof depends on ordering, not positivity.

Negative numbers don't invalidate the logic.

That's different from certain sliding-window sum algorithms, where nonnegativity is essential.

This is why we should understand the proof rather than memorize the pointer movements.

## 5. Fixed-size windows: incremental arithmetic

Now return to our event processor.

Suppose each event has a numerical risk score.

We want the maximum total risk score among all consecutive groups of exactly one hundred events.

The straightforward algorithm calculates the sum of every hundred-element window independently.

For n events and window size k, that requires O(nk) time.

If k is large, much of that work is repeated.

Consider two neighboring windows.

The first covers events zero through ninety-nine.

The next covers events one through one hundred.

Ninety-nine events are shared.

The only changes are:

Event zero leaves.

Event one hundred enters.

Therefore, if we know the first window's sum, the next sum equals the previous sum minus the outgoing value plus the incoming value.

### The maintained invariant

At each step:

**The running sum equals the sum of exactly the elements in the current window.**

When we advance one position, subtracting the old leftmost element and adding the new rightmost element preserves that relationship.

### Complexity

Initialize the first window in O(k).

Then process each remaining element once.

The total is O(n), with O(1) additional state for the running sum and maximum.

This works even when scores are negative.

Why?

Because the window size is fixed.

We're not relying on monotonic growth or shrinkage to decide which windows can be skipped.

We simply evaluate every possible window of the required length efficiently.

### A subtle initialization bug

Suppose every possible window has a negative sum.

If we initialize the maximum result to zero, the algorithm may return zero even though no window has that sum.

For example, a three-element window containing negative two, negative four, and negative one has a sum of negative seven.

If it is the only valid window, negative seven is the correct answer.

Initializing the best value to zero silently changes the problem into one where selecting no window is permitted.

The contract required exactly k elements.

So the initial best result should come from an actual valid window.

This is a good example of why edge cases and initialization are part of correctness, not merely implementation trivia.

## 6. Variable-size windows: maintain a valid interval

Now our analyst asks:

"What's the longest consecutive sequence of login attempts containing at most two failures?"

The answer can have any length.

But the window must satisfy one constraint.

We can use two boundaries.

The right boundary expands the window.

The left boundary shrinks it.

We maintain the number of failures inside the current interval.

Whenever the failure count exceeds the permitted maximum, advance the left boundary until the condition becomes true again.

After restoring validity, consider the current window length as a candidate answer.

### The invariant

At the end of each right-boundary iteration:

**The current window contains at most k failures.**

This ensures that any window length recorded as a candidate is valid.

### Why shrinking doesn't lose the optimum

The critical reasoning is that extending the window can only preserve or increase the number of failures.

Removing events from the left can only preserve or decrease it.

If a window contains too many failures, extending it further cannot fix the problem.

We must remove failures by moving the left boundary.

Once the window becomes valid, we have the longest valid suffix ending at the current right boundary.

Any shorter suffix cannot improve the maximum length for that same endpoint.

Repeating this for every right boundary considers an optimal candidate for every possible endpoint.

Therefore, the maximum recorded length is correct.

### Why the nested loops are still linear

The implementation may contain a `while` loop inside a `for` loop.

That can look quadratic.

But examine total pointer movement.

The right boundary moves from the beginning to the end once.

The left boundary also moves forward at most n times.

Neither moves backward.

Therefore, the total number of boundary advances is O(n).

This is **amortized analysis**.

A nested loop isn't automatically O(n²).

You must count how often its operations can occur over the entire execution.

### The important assumption

This approach works because removing elements from the left cannot increase the number of failures.

The maintained condition behaves monotonically as the window changes.

Not every interval property has this behavior.

The next example shows why that's important.

## 7. Why negative numbers can break sliding-window logic

In CS360-L01, we studied the shortest nonempty interval whose sum reaches a target, assuming all values were nonnegative.

The algorithm expanded the right boundary until the sum was large enough, then shrank from the left while preserving the target.

That reasoning depends on nonnegative values.

If we add an element, the sum cannot decrease.

If we remove an element, the sum cannot increase.

Now allow negative numbers.

Those properties disappear.

Removing a negative value can increase the sum.

Adding a negative value can decrease it.

Consequently, a rule such as "stop shrinking once the sum falls below the target" is no longer justified.

A shorter qualifying interval might still exist after removing a negative value.

The issue isn't that sliding-window code dislikes negative numbers.

It's that its correctness proof no longer applies.

This is a general lesson:

**Before choosing a window algorithm, determine whether its property changes predictably as the boundaries move.**

If not, another representation may be necessary.

For some sum problems, prefix sums and hash maps provide that alternative.

## 8. Strings: the same patterns, a more complicated unit

Now consider a string problem.

"Find the length of the longest substring without repeating characters."

This appears similar to our login-window problem.

We want a contiguous sequence.

We maintain a moving window.

And the constraint is that every character in the window must be unique.

But strings introduce an important complication.

What exactly counts as a character?

### JavaScript strings and Unicode

JavaScript strings are sequences of UTF-16 code units.

Some Unicode code points require two UTF-16 code units.

And a user-perceived character, called a grapheme cluster, can consist of multiple Unicode code points.

For many coding interviews, the intended input domain is ASCII or ordinary code points.

But we should clarify.

If the interviewer says "Unicode code points," JavaScript iteration with `for...of` or converting the string using `Array.from` provides code-point-oriented iteration for ordinary well-formed Unicode text.

If the requirement concerns user-perceived grapheme clusters, additional segmentation rules are needed, potentially using `Intl.Segmenter`.

These aren't interchangeable units.

A correct algorithm over code units can produce the wrong answer for a problem defined over grapheme clusters.

### The interview habit

Ask one concise question.

"Should I treat characters as ASCII, Unicode code points, or user-perceived characters?"

If the interviewer specifies lowercase English letters, the problem becomes simpler.

If they specify code points, we can deliberately choose that representation.

The important thing is not memorizing Unicode internals in an algorithms interview.

It's respecting the specified unit of measurement.

## 9. Longest substring without repetition

Suppose our string is `abca`.

The longest substring without repeated characters has length three.

We could inspect every substring and test whether its characters are distinct.

But that repeats a lot of work.

Instead, maintain a sliding window with no duplicate code points.

A useful approach records the most recent index of each code point.

When we encounter a repeated code point whose previous occurrence lies inside our current window, move the left boundary just past that earlier occurrence.

Then update the code point's most recent position.

Track the maximum window length.

### The invariant

Before moving to the next element:

**The current window contains no repeated code point.**

The last-position map tells us whether the new code point violates that invariant.

If its last occurrence is outside the current window, no adjustment is necessary.

If its last occurrence is inside, we must exclude that earlier occurrence.

### The classic `abba` trap

Consider the string `abba`.

Process the first a.

Then b.

Now another b arrives.

The left boundary moves past the first b.

The valid window becomes the second b.

Then a arrives.

We have seen a before, at the beginning of the string.

But that earlier a is already outside our current window.

If we blindly move the left boundary to one position past the old a, we move backward and incorrectly expand the window to include both b characters.

The correct update is:

Move the left boundary to the greater of its current position and one position after the previous occurrence.

**The left boundary must never move backward.**

That's the small rule that distinguishes a correct last-position solution from a superficially similar broken one.

### Complexity

If we have an array of n code points, each code point is processed once.

Hash-map operations are expected constant time.

The scan therefore takes O(n) expected time, with O(k) map storage for k distinct code points.

Converting a JavaScript string to an array of code points also requires O(n) time and space.

The full implementation should account for that conversion rather than pretending string representation is free.

## 10. Prefix sums: turn intervals into differences

Now return to the event risk scores.

Suppose the sequence contains both positive and negative numbers.

We need to count how many contiguous intervals have total score equal to a target.

A sliding-window algorithm based on nonnegative sums is no longer reliable.

But there's another representation.

Let the prefix sum at position i be the sum of all values before i.

The prefix sum at position zero is zero.

If the prefix sum at position j is Pj and the prefix sum at position i is Pi, then the sum of the half-open interval from i to j is Pj minus Pi.

This identity is straightforward.

We accumulate from the beginning to j, then subtract everything before i.

What's left is exactly the interval from i to j.

### Transform the question

We want an interval whose sum equals target.

That means:

Current prefix sum minus earlier prefix sum equals target.

Rearranging:

Earlier prefix sum equals current prefix sum minus target.

So when we reach a new position, we need to know how many earlier prefixes have that required value.

A frequency map can answer.

### Why a frequency map, not a set?

We want to count **all** matching subarrays.

The same prefix-sum value may have occurred several times at different earlier positions.

Each occurrence can define a distinct valid interval ending at the current position.

A set would tell us whether at least one matching prefix existed.

A frequency map tells us how many.

That changes the answer.

## 11. The zero-prefix detail that breaks solutions

Before processing any input elements, the accumulated sum is zero.

That initial prefix is meaningful.

Suppose the first few elements sum exactly to the target.

Then the matching interval begins at index zero.

Its earlier prefix is the initial zero.

Therefore, the frequency map must initially record one occurrence of prefix sum zero.

Without that entry, intervals beginning at the start of the array can be missed.

### A small example

Consider scores one, negative one, one.

The target is one.

There are three matching subarrays:

The first one alone.

The last one alone.

And the entire sequence.

Let's see why the frequency map works.

Initially, prefix zero has frequency one.

After the first value, the current prefix is one. We seek an earlier prefix of zero and find one.

After the negative one, the current prefix returns to zero. We seek an earlier prefix of negative one and find none. Then we record another occurrence of prefix zero.

After the final one, the current prefix becomes one. We seek zero again.

This time zero has frequency two.

Those two earlier zero prefixes correspond to two distinct intervals ending at the final element.

The total count becomes three.

### Query before inserting

The processing order matters.

For each element, first update the running prefix.

Then count matching earlier prefix sums.

Finally record the current prefix as an earlier prefix for future iterations.

If we insert the current prefix before querying, we risk counting a zero-length interval when the target is zero.

But the problem asks for nonempty subarrays.

The correct order prevents that.

### Why this works with negative values

The prefix-sum identity doesn't require values to be nonnegative.

It is valid for positive, negative, and zero values.

We are not making assumptions about which direction a sum changes when the window expands.

We're comparing algebraic differences between prefix totals.

That's why this representation succeeds where a monotonic sliding-window argument can fail.

## 12. Three tools, three different questions

Let's compare the techniques conceptually.

Suppose a problem asks whether a particular value has ever appeared.

We need a set.

Suppose it asks for the longest contiguous interval meeting a maintainable condition.

We may need a sliding window.

Suppose it asks how many intervals sum to a particular value, with arbitrary signed numbers.

We can use prefix sums and a frequency map.

Now imagine the interviewer changes one word.

"Does a matching interval exist?"

Instead of "How many matching intervals exist?"

A set of prefix sums might be sufficient for an existence query.

Or perhaps they ask for the longest matching interval.

Now a map of earliest prefix positions may be more useful than a frequency map.

The underlying mathematical identity hasn't changed.

The information we must retain has changed.

This is precisely how algorithmic reasoning becomes transferable.

We identify the useful relationship, then choose a data structure representing the information needed by the requested output.

## 13. Common mistakes and why they happen

There are several mistakes worth learning before encountering them in interviews.

### Using a set when duplicates have multiplicity

If the window can contain two copies of one value, simply deleting the value from a set when one copy leaves loses information.

Use counts when multiplicity matters.

### Moving the left pointer backward

In longest-unique-substring problems, the last occurrence of a symbol may already lie outside the current window.

The left boundary must never retreat.

### Assuming every nested loop is quadratic

A shrinking-window `while` loop can execute at most n times across the whole scan if the left pointer only advances.

Analyze total movement rather than multiplying loop bounds mechanically.

### Using variable-window sum logic without verifying monotonicity

Negative numbers can invalidate the reasoning.

Check the assumptions before applying the pattern.

### Forgetting the initial prefix sum

A map that doesn't begin with one occurrence of zero can miss subarrays starting at index zero.

### Updating prefix frequencies too early

Counting after inserting the current prefix can introduce invalid zero-length intervals when target is zero.

Count matching earlier prefixes first.

### Confusing input length with the chosen string unit

JavaScript UTF-16 code units, Unicode code points, and grapheme clusters are different.

Clarify which unit the result should count.

### Ignoring the no-mutation requirement

Sorting an input array in place may violate the contract even when the returned answer is otherwise correct.

These mistakes often arise from the same underlying issue.

The candidate memorized how the code looked without fully understanding what state the algorithm was supposed to maintain.

## 14. How to recognize the pattern under interview pressure

Let's develop a practical recognition method.

When you see an unfamiliar sequence problem, first ask whether order matters.

If order doesn't matter and you're checking membership or frequency, hashing is a natural candidate.

If the input is sorted and you're searching for a relationship between boundary elements, consider two pointers.

If the task concerns every contiguous block of exactly k elements, consider a fixed-size sliding window.

If it concerns the longest or shortest contiguous interval satisfying a condition, ask whether a variable window has a useful monotonic property.

If it concerns sums of arbitrary intervals, especially when negative numbers or repeated totals matter, consider prefix sums.

Then ask what the algorithm must remember.

A Boolean?

A count?

The last position of a symbol?

The frequency of each symbol inside the current window?

The accumulated sum before each index?

The required information determines the data structure.

Only then should you write code.

### The last step: justify the shortcut

For hashing, explain why stored observations replace repeated searches.

For sorted two pointers, explain which candidates each movement safely eliminates.

For sliding windows, explain the invariant and why pointer movement is monotonic.

For prefix sums, explain why a difference of two prefix totals equals an interval total.

These are small proofs.

They're also the difference between pattern recognition and genuine problem solving.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — Set versus frequency map

A sliding window contains two occurrences of Alice. One Alice event leaves the window. Why is removing Alice from a set incorrect?

### Question 2 — Sorted two pointers

In a sorted array, the smallest remaining value plus the largest remaining value is below the target. Why can the smallest value be discarded?

### Question 3 — Fixed versus variable windows

Why can a fixed-size rolling-sum algorithm handle negative numbers, while a shortest-subarray sliding window may fail when negatives are introduced?

### Question 4 — Amortized complexity

A variable-window algorithm contains a `while` loop inside a `for` loop. Under what conditions can its total execution still be O(n)?

### Question 5 — The `abba` bug

A longest-unique-substring algorithm encounters a symbol whose previous occurrence lies before the current left boundary. Why must the left boundary remain unchanged?

### Question 6 — Prefix frequencies

Why does counting target-sum subarrays require a frequency map rather than merely a set of observed prefix sums?

### Question 7 — The zero prefix

Why must the prefix-frequency map initially contain one occurrence of sum zero?

### Question 8 — The update order

When counting nonempty subarrays with target sum zero, why must we count matching earlier prefixes before inserting the current prefix?

---

# Solutions and Discussion

## Solution 1 — Presence isn't multiplicity

A set records only whether Alice is present.

After one occurrence leaves, another remains.

A frequency map can decrement the count from two to one, preserving the correct state.

## Solution 2 — Ordering rules out every pair containing the smallest value

The largest remaining value is the biggest possible partner for the smallest.

If even that pair is below the target, every other pair containing the smallest value is also too small.

The left pointer can advance safely.

## Solution 3 — The assumptions differ

A fixed window evaluates every block of the required size through incremental addition and subtraction. Negative values don't invalidate that arithmetic.

A variable shortest-sum window often relies on extending the interval never decreasing the sum and shrinking it never increasing the sum.

Negative values invalidate those monotonic assumptions.

## Solution 4 — Count total pointer movement

If both pointers move only forward and each advances at most n times, their total movement is O(n).

The inner loop may run many times in one iteration but cannot collectively advance the left boundary more than n positions.

This is amortized linear behavior.

## Solution 5 — The old occurrence is already excluded

A previous occurrence before the current left boundary is not inside the current window.

Moving left backward would reintroduce elements that were already excluded, potentially violating uniqueness.

The new left boundary is the maximum of its current value and one position after the previous occurrence.

## Solution 6 — Different earlier positions define different intervals

The same prefix sum may occur several times.

Each occurrence can define a distinct subarray ending at the current position with the required sum.

A set loses that multiplicity; a frequency map preserves it.

## Solution 7 — Intervals can begin at index zero

The empty prefix before the first element has sum zero.

It allows a current prefix equal to the target to identify a subarray beginning at the start of the input.

Without the initial zero, those intervals may be missed.

## Solution 8 — Prevent counting an empty interval

For target zero, the current prefix equals itself.

If we insert it before querying, the algorithm may count the interval from the current position to itself, which has length zero.

The problem concerns nonempty subarrays, so the current prefix should become available only for later positions.

---

# The Mental Model Worth Keeping

When a sequence problem seems to require repeatedly scanning old elements, ask:

**What information about the past is still relevant?**

**Can I maintain that information as the sequence moves forward?**

**Does ordering allow me to discard candidates safely?**

**Does the window condition change monotonically when elements enter or leave?**

**Would accumulated prefix information turn repeated interval calculations into differences?**

The central principle is:

**Efficient sequence algorithms replace repeated searching with maintained knowledge—and correctness comes from proving that the maintained knowledge is sufficient.**

# Next Lecture — CS360-L03: Binary Search, Sorting, and Greedy Decisions

We've used sorting to make two-pointer decisions safe, and maintained state to avoid repeated scans.

Next we'll explore a different class of shortcuts.

Binary search repeatedly eliminates half the remaining possibilities, but only when the search space has the necessary ordering or monotonic structure.

Greedy algorithms commit to local decisions, but only when those choices can be justified without destroying the possibility of an optimal solution.

And sorting can transform problems in ways that make both techniques possible.

We'll learn not simply how to implement these algorithms, but how to recognize when their shortcuts are mathematically justified.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Coding Gym — Solve Before Reading the Hints

This is the practical half of CS360.

The audio lecture is intended to make these tools understandable. The exercises train you to discover and implement them independently.

For each problem, attempt the following sequence:

1. Clarify the exact input/output contract.
2. State a correct baseline.
3. Identify the repeated work.
4. Derive an improved strategy.
5. Write a correctness argument.
6. Implement and test.
7. Explain time and space complexity.

Do not inspect the hints or worked solutions until you've made a genuine attempt.

The examples use TypeScript, but you may solve them in another interview-appropriate language.

## Problem A — Two Risk Scores

**Focus:** Sorted two pointers  
**Suggested attempt:** 12–15 minutes

You receive a sorted array of integers and a target score.

Find two distinct elements whose sum equals the target.

Return their zero-based indices as a pair, or `null` if no pair exists.

The input array must remain unchanged.

### Examples

```text
scores = [-4, -1, 2, 5, 8]
target = 4
result = [1, 3]

scores = [1, 2, 3, 9]
target = 8
result = null

scores = [3, 3]
target = 6
result = [0, 1]
```

### Constraints

- The array is sorted in nondecreasing order.
- It may contain negative values and duplicates.
- Length may be up to 200,000.
- Values and target are safe integers, and pair sums remain within the safe integer range.
- Any valid pair is acceptable.

### Your challenge

First describe the quadratic baseline.

Then derive a linear-time solution exploiting sorted order.

Explain why each pointer movement cannot discard every valid solution.

---

## Problem B — Maximum Risk in a Fixed Interval

**Focus:** Fixed-size sliding window  
**Suggested attempt:** 12–15 minutes

A monitoring service receives daily risk-score changes.

Some values may be negative because certain activities reduce risk.

Find the maximum sum of exactly k consecutive values.

### Examples

```text
scores = [2, -1, 4, -2, 5]
k = 3
result = 7

scores = [-5, -2, -7]
k = 2
result = -7

scores = [8]
k = 1
result = 8
```

### Constraints

- The input contains at least one value.
- One is less than or equal to k, and k is at most the input length.
- Values are finite safe integers.
- Intermediate sums fit within the safe integer range.
- Do not modify the input.
- The selected window must contain exactly k values.

### Your challenge

Avoid recomputing every k-element sum.

Explain why initializing the best sum to zero is incorrect for some valid inputs.

Derive the running-sum invariant.

---

## Problem C — Longest Unique Session Signature

**Focus:** Last-seen map and variable window  
**Suggested attempt:** 20 minutes

A service receives a session signature represented as a string.

Find the length of the longest contiguous substring containing no repeated Unicode code points.

### Examples

```text
signature = "abcabcbb"
result = 3

signature = "bbbbb"
result = 1

signature = "abba"
result = 2

signature = ""
result = 0

signature = "a🙂bc🙂d"
result = 4
```

### Constraints

- Count Unicode code points, not UTF-16 code units.
- You may convert the string into an array of code points.
- Grapheme-cluster segmentation is explicitly outside the exercise.
- The string may contain hundreds of thousands of code points.
- Do not modify the input.

### Your challenge

Derive an O(n) expected-time solution after choosing the code-point representation.

Explain the exact failure that occurs if the left boundary is allowed to move backward.

Then state the longest-unique-window invariant.

---

## Problem D — The Longest Acceptable Failure Streak

**Focus:** Variable-size sliding window  
**Suggested attempt:** 20 minutes

A backend logs a sequence of request outcomes.

Each element is one for success or zero for failure.

Find the maximum length of a contiguous interval containing at most k failures.

### Examples

```text
outcomes = [1, 0, 1, 0, 0, 1, 1]
k = 2
result = 5

outcomes = [0, 0, 0]
k = 0
result = 0

outcomes = [1, 1, 1]
k = 0
result = 3

outcomes = []
k = 2
result = 0
```

### Constraints

- Up to 200,000 outcomes.
- Every outcome is exactly zero or one.
- k is a nonnegative integer.
- Do not modify the input.

### Your challenge

Explain why you don't need to enumerate every possible interval.

Derive the invariant that the maintained window must satisfy.

Then prove that the algorithm is O(n) despite containing nested loops.

---

## Problem E — Count Exact-Risk Periods

**Focus:** Prefix sums and a frequency map  
**Suggested attempt:** 25 minutes

A security system receives a sequence of signed integer risk adjustments.

Count the number of nonempty contiguous intervals whose total adjustment equals a given target.

### Examples

```text
scores = [1, -1, 1]
target = 1
result = 3

scores = [0, 0, 0]
target = 0
result = 6

scores = [2, 3, -2, 1]
target = 3
result = 2

scores = []
target = 0
result = 0
```

### Constraints

- Up to 200,000 elements.
- Values may be negative, zero, or positive.
- Values, prefix sums, and the result count fit within JavaScript safe integers.
- The input must remain unchanged.

### Your challenge

Start with an O(n²) baseline.

Then express every subarray total as a difference between two prefix sums.

Derive a one-pass solution using a map.

Explain why the map begins with one occurrence of zero and why matching prefixes must be counted before the current prefix is inserted.

---

# Progressive Hints

Read one hint at a time, only after attempting the problem.

## Problem A hints

**Hint 1:** Which two elements provide the smallest and largest possible values among the current candidates?

**Hint 2:** If their sum is too small, can the smallest value pair with any smaller alternative?

**Hint 3:** Use one pointer at the beginning and one at the end. Move the boundary whose current value has been proved incapable of participating in a valid pair.

## Problem B hints

**Hint 1:** Consecutive windows of size k share k minus one elements.

**Hint 2:** Subtract the outgoing value and add the incoming value.

**Hint 3:** Initialize the best sum from the first actual window, not from zero.

## Problem C hints

**Hint 1:** Remember the latest index where each code point appeared.

**Hint 2:** A repeated code point matters only if its previous position is inside the current window.

**Hint 3:** Update the left boundary using the maximum of its current position and one position after the previous occurrence.

**Hint 4:** Use `Array.from(signature)` to work with code points instead of individual UTF-16 code units.

## Problem D hints

**Hint 1:** Maintain a window whose failure count is at most k.

**Hint 2:** Expand the right boundary. Shrink the left boundary while failures exceed k.

**Hint 3:** The longest valid suffix ending at each right boundary is sufficient to determine the global maximum.

## Problem E hints

**Hint 1:** The sum of `[i, j)` equals `prefix[j] - prefix[i]`.

**Hint 2:** For the current prefix P, seek previous prefixes equal to `P - target`.

**Hint 3:** Store frequencies, not merely membership.

**Hint 4:** Seed zero with frequency one.

**Hint 5:** Count matching previous prefixes before recording the current prefix.

---

# Worked Solutions

Do not use these as the starting point. Compare them against your own attempt.

## Solution A — Two pointers on sorted scores

### Reasoning

The original array is sorted.

Start with the smallest and largest elements.

If their sum is below target, the smallest element cannot pair with any remaining value to reach target.

Discard it by advancing the left pointer.

If the sum is above target, the largest element cannot pair with any remaining value to reach target.

Discard it by retreating the right pointer.

If the sum matches, return both indices.

### TypeScript

```typescript
function twoSumSorted(
  scores: number[],
  target: number
): [number, number] | null {
  let left = 0;
  let right = scores.length - 1;

  while (left < right) {
    const sum = scores[left] + scores[right];

    if (sum === target) {
      return [left, right];
    }

    if (sum < target) {
      left++;
    } else {
      right--;
    }
  }

  return null;
}
```

### Complexity

Time: O(n).

Additional space: O(1).

The input isn't modified.

### Invariant

Every pair that can still satisfy the target must lie within the remaining pointer boundaries.

The algorithm discards values only after proving they cannot participate in a valid pair with any remaining candidate.

---

## Solution B — Rolling fixed-window sum

### Reasoning

Calculate the first k-element sum.

Then move the window right one position at a time.

Subtract the element leaving and add the element entering.

Track the largest actual window sum.

### TypeScript

```typescript
function maxFixedWindowSum(
  scores: number[],
  k: number
): number {
  if (
    !Number.isInteger(k) ||
    k < 1 ||
    k > scores.length
  ) {
    throw new RangeError("Invalid window size");
  }

  let sum = 0;

  for (let i = 0; i < k; i++) {
    sum += scores[i];
  }

  let best = sum;

  for (let right = k; right < scores.length; right++) {
    sum += scores[right];
    sum -= scores[right - k];

    best = Math.max(best, sum);
  }

  return best;
}
```

### Complexity

Time: O(n).

Additional space: O(1).

### Invariant

After each update, `sum` equals the sum of exactly the k elements in the current window.

### Why not initialize `best` to zero?

If all valid window sums are negative, zero isn't a valid answer.

For `[-5, -2, -7]` with k equal to two, the correct maximum is negative seven.

Initializing to zero would silently allow an empty selection, which violates the problem contract.

---

## Solution C — Longest unique code-point substring

### Reasoning

Convert the input string into code points.

Maintain a window with no repeated code point.

Remember the most recent index of each code point.

When a repeated code point appears inside the window, move the left boundary beyond its earlier occurrence.

Never move the left boundary backward.

### TypeScript

```typescript
function longestUniqueSubstring(
  signature: string
): number {
  const chars = Array.from(signature);

  const lastSeen = new Map<string, number>();

  let left = 0;
  let best = 0;

  for (let right = 0; right < chars.length; right++) {
    const ch = chars[right];

    const previous = lastSeen.get(ch);

    if (previous !== undefined) {
      left = Math.max(left, previous + 1);
    }

    lastSeen.set(ch, right);

    best = Math.max(best, right - left + 1);
  }

  return best;
}
```

### Complexity

Let n be the number of code points.

Converting to code points takes O(n) time and memory.

The scan takes O(n) expected time.

The map stores at most O(k) entries for k distinct code points, bounded by n.

Overall additional memory is O(n) because of the converted array.

### Invariant

After processing each right-boundary element, the interval from `left` through `right` contains no repeated code point.

### The `abba` test

The second b moves left past the first b.

When the final a arrives, its earlier occurrence is outside the current window.

Using `Math.max` prevents the left boundary from moving backward.

That's the crucial correctness detail.

---

## Solution D — Longest interval with at most k failures

### Reasoning

Expand the right boundary.

If the incoming outcome is zero, increment the failure count.

While failures exceed k, move the left boundary right and subtract any failures that leave.

Once the window is valid, update the maximum length.

### TypeScript

```typescript
function longestAcceptableStreak(
  outcomes: number[],
  k: number
): number {
  if (!Number.isInteger(k) || k < 0) {
    throw new RangeError("k must be nonnegative");
  }

  let left = 0;
  let failures = 0;
  let best = 0;

  for (let right = 0; right < outcomes.length; right++) {
    if (outcomes[right] === 0) {
      failures++;
    }

    while (failures > k) {
      if (outcomes[left] === 0) {
        failures--;
      }

      left++;
    }

    best = Math.max(best, right - left + 1);
  }

  return best;
}
```

### Complexity

Time: O(n).

Additional space: O(1).

### Why the nested loops aren't quadratic

The right pointer advances n times.

The left pointer can advance at most n times across the entire execution.

No element leaves the window more than once.

Therefore, total pointer movement is linear.

### Invariant

After the shrinking loop, the current window contains no more than k failures.

For each right endpoint, the algorithm considers its longest valid suffix.

Taking the maximum over all right endpoints gives the longest valid interval overall.

---

## Solution E — Prefix sums and frequency counting

### Reasoning

Let the current prefix sum be P.

A prior prefix sum Q defines a subarray ending at the current position with target total exactly when P minus Q equals target.

Therefore, Q must equal P minus target.

Count how many times that earlier prefix occurred.

Then record the current prefix for future positions.

### TypeScript

```typescript
function countTargetSubarrays(
  scores: number[],
  target: number
): number {
  const frequencies = new Map<number, number>();

  frequencies.set(0, 1);

  let prefix = 0;
  let count = 0;

  for (const score of scores) {
    prefix += score;

    const needed = prefix - target;

    count += frequencies.get(needed) ?? 0;

    frequencies.set(
      prefix,
      (frequencies.get(prefix) ?? 0) + 1
    );
  }

  return count;
}
```

### Complexity

Time: O(n) expected, assuming typical hash-map operations.

Space: O(n) in the worst case.

### Why initialize zero with frequency one?

An interval beginning at index zero has an earlier prefix sum of zero.

Without it, intervals beginning at the start of the sequence could be missed.

### Why count before inserting?

The current prefix must not be paired with itself to produce a zero-length subarray.

Only earlier prefixes define nonempty intervals ending at the current position.

### The three-zero test

For scores `[0, 0, 0]` and target zero, there are six nonempty contiguous subarrays:

Three of length one.

Two of length two.

One of length three.

The frequency-map algorithm correctly counts all six because repeated zero prefixes represent distinct earlier starting positions.

This is also why a set would be insufficient.

---

# Retrieval Practice — Make the Patterns Transferable

You've now seen the solutions.

Don't interpret that familiarity as mastery.

Reattempt one of the exercises without looking at the implementation.

Explain the invariant before writing code.

Then change a condition.

For Problem A, remove the sorted-input guarantee. Can you still find a pair efficiently using a hash map? How does the memory trade-off change?

For Problem B, require the minimum rather than maximum fixed-window sum. Which parts of the algorithm remain unchanged?

For Problem C, return the longest unique substring itself rather than its length. What additional state must be retained?

For Problem D, replace "at most k failures" with "exactly k failures." Can you adapt the method without enumerating every subarray?

For Problem E, ask only whether a matching interval exists. Do you still need frequency counts? Then ask for the longest matching interval. What information about earlier prefixes becomes useful?

These variations are more valuable than repeatedly copying the original solutions.

## Coding self-assessment

Score each category from zero to two.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Recognition | Wrong approach | Recognized after a hint | Derived independently |
| Invariant | Couldn't explain | Partial reasoning | Clear correctness argument |
| Implementation | Incorrect or incomplete | Minor errors | Correct |
| Edge cases | Missed key cases | Found after prompting | Tested proactively |
| Complexity | Unclear | Mostly correct | Precise and justified |

Record one mistake after each attempt.

The ideal entry isn't "forgot sliding window."

It's something more specific:

"I didn't check whether the sum property was monotonic."

"I used a set even though duplicates needed counts."

"I let the left boundary move backward."

"I forgot the initial zero prefix."

Those observations identify exactly what needs practice.

---

# Further Reading

Recommended resources:

- **MIT OpenCourseWare — Introduction to Algorithms:** https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/
- **CP-Algorithms — Prefix Sums:** https://cp-algorithms.com/
- **MDN — JavaScript `Map`:** https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map
- **MDN — JavaScript `Set`:** https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set
- **MDN — `Intl.Segmenter`:** https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Segmenter

Related programme chapters:

- CS110-L04 — Data Structures: Choosing How to Remember Things
- CS110-L05 — Searching, Sorting, and Finding Shortcuts
- CS360-L01 — The Art of Solving an Unfamiliar Problem
- CS360-L03 — Binary Search, Sorting, and Greedy Decisions

---

## Dense Cheatsheet — Interview Glance Card

```text
CS360-L02 — ARRAYS, STRINGS, HASHING, SLIDING WINDOWS

CENTRAL MODEL
  Efficient sequence algorithms maintain useful information
  instead of repeatedly rediscovering it.

FIRST QUESTIONS
  Contiguous subarray/substring or arbitrary subsequence?
  Does order matter?
  Sorted input?
  Duplicates?
  Negative values?
  Exact count, existence, shortest, or longest?
  Can input be modified?

HASH SET
  Remembers which values were seen
  Expected O(1) lookup/insert
  O(n) expected scan, O(n) space worst case
  Good for membership / first repeat
  Set loses frequency information

HASH MAP
  Value -> count, position, or other state
  Frequency map needed when multiplicity matters
  Last-position map useful for unique-substring windows
  Memory grows with number of distinct keys

SORTED TWO POINTERS
  left at smallest, right at largest
  sum < target -> move left rightward
  sum > target -> move right leftward
  sum = target -> solution
  Justification: sorted order rules out discarded pairs
  O(n) scan after sorting
  Negative numbers do not invalidate proof

FIXED SLIDING WINDOW
  First window sum
  Advance: remove outgoing, add incoming
  Maintain exact k-element state
  O(n) time, O(1) auxiliary space
  Negative numbers allowed for rolling sums
  Initialize best using real window, not zero

VARIABLE SLIDING WINDOW
  Expand right boundary
  Restore invariant by shrinking left
  Record valid window result
  Each boundary moves forward at most n times
  Nested while inside for can still be O(n) amortized
  Requires suitable monotonic property

AT MOST K FAILURES
  failure count maintained in current window
  shrink while failures > k
  longest valid suffix for each right endpoint
  O(n) time, O(1) space

STRING WINDOW
  Define character unit:
    UTF-16 code unit
    Unicode code point
    Grapheme cluster
  For code points: Array.from(str)
  Track last seen position
  left = max(left, previousIndex + 1)
  Never move left backward
  "abba" is the classic counterexample

PREFIX SUM
  P[0] = 0
  P[j] - P[i] = sum of [i, j)
  Target interval:
    prior prefix = current prefix - target
  Works with negative values

COUNT TARGET-SUM SUBARRAYS
  Map<prefixSum, frequency>
  Initialize 0 -> 1
  For each value:
    update prefix
    count += freq(prefix - target)
    then record current prefix
  Count BEFORE insert, avoid zero-length intervals
  O(n) expected time, O(n) space worst case
  Repeated prefix sums represent distinct start positions
  [0,0,0], target 0 -> 6 qualifying subarrays

WHY VARIABLE SUM WINDOWS CAN FAIL
  Nonnegative values provide monotonic sum behavior
  Negative values break that property
  Removing a negative can increase window sum
  Re-check invariant before reusing familiar pattern

INTERVIEW MISTAKES
  Subarray confused with subsequence
  Set used where frequency needed
  Left boundary moved backward
  Fixed window initialized with invalid zero candidate
  Sliding window used without monotonicity
  Initial prefix sum zero omitted
  Prefix inserted before count
  String unit not specified
  O(n) amortized loop mistaken for O(n²)

RECOGNITION GUIDE
  Membership / first repeat      -> Set
  Counting duplicates            -> Frequency Map
  Sorted relationship            -> Two Pointers
  Exactly k consecutive values   -> Fixed Window
  Longest/shortest valid interval -> Variable Window
  Arbitrary signed interval sums -> Prefix Sums
  Number of target-sum intervals  -> Prefix Frequency Map

SENIOR INTERVIEW ANSWER
  "I'd identify the sequence constraints, establish a baseline,
   then ask which information is repeatedly recomputed.
   Hashing preserves observations, windows preserve interval
   state, and prefix sums turn intervals into differences.
   I'd justify the relevant invariant before implementing."

MENTAL MODEL
  What must I remember?
  What can I safely forget?
  What allows the boundary to advance?
  Which assumptions make the shortcut correct?
```
