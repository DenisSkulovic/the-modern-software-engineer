---
id: CS360-L01
course: CS360
title: "The Art of Solving an Unfamiliar Problem"
type: elective
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: null
next: CS360-L02
---



# CS360 — Algorithms and Coding Interview Lab

## Lecture 01: The Art of Solving an Unfamiliar Problem

*You have seven years of experience building software. You've designed APIs, worked with databases, debugged production incidents, and deployed distributed services. Then an interviewer presents an unfamiliar array problem, and your mind goes blank. Twenty minutes later, somebody shows you a fifteen-line solution, and you understand every line. Why couldn't you discover it yourself?*

# Part I — Intuition

## The picture to carry in your head

Imagine you're an engineer investigating a city you've never visited.

You need to travel from the central railway station to a small museum somewhere in the suburbs.

Someone hands you a map.

What do you do?

You could immediately start driving in a random direction and hope the route becomes obvious.

You could stare at the map until the perfect route somehow materializes.

Or you could begin systematically.

First, establish where you are and where you need to go.

Then inspect the roads and constraints. Are there bridges? One-way streets? A river crossing? Are you walking, driving, or using public transport?

Next, identify a route that definitely works—even if it isn't the fastest.

Only after that do you search for a better route.

This is surprisingly close to the process of solving unfamiliar algorithmic problems.

The objective isn't to recognize a particular LeetCode problem from memory.

It's to transform an initially confusing request into a sequence of increasingly precise statements.

At first, you know what the problem asks.

Then you know what a correct solution would look like.

Then you know how to produce one.

Finally, you discover how to avoid unnecessary work.

**Algorithmic problem solving is the art of making useful progress before you know the optimal answer.**

## 1. The experienced engineer's uncomfortable interview

Imagine you're interviewing for a senior full-stack position.

The interviewer presents a problem:

"A hotel has a list of reservations for one physical room. Each reservation has a start and end time. Determine whether any two reservations overlap."

That sounds simple.

But several questions immediately arise.

Are the reservations sorted?

Can two reservations meet at exactly the same boundary?

What happens if an interval has the same start and end time?

Can the input contain hundreds of thousands of reservations?

May we modify the original array?

These questions aren't a sign that you don't understand the problem.

They're part of understanding it.

A good engineer doesn't solve an undefined problem and hope their assumptions happen to match the interviewer's.

They establish the contract first.

## 2. Start with something undeniably correct

Suppose we have five reservations.

One obvious approach is to compare every reservation with every later reservation.

If any pair overlaps, return true.

If no pair overlaps, return false.

That isn't sophisticated.

But it is correct under a clear definition of overlap.

It also establishes a baseline.

Now we can ask what makes it expensive.

With five reservations, the work is negligible.

With two hundred thousand, comparing every pair would require roughly twenty billion checks.

That's not attractive.

But notice what we've accomplished.

We haven't solved the performance problem yet.

We have established the logic of correctness and discovered the source of unnecessary work.

This is real progress.

A common interview mistake is trying to skip this stage because the candidate believes a senior engineer must immediately know the optimal algorithm.

Quite the opposite.

Explaining a correct baseline and its limitations demonstrates structured reasoning.

## 3. Search for structure that lets you skip work

Our reservations are unsorted.

That creates uncertainty.

A reservation beginning on Friday might appear before another beginning on Monday.

We cannot infer much from neighboring array positions.

But what if we sort the reservations by start time?

Now the sequence has meaningful structure.

Earlier starts come before later starts.

That lets us reason about which comparisons are necessary.

Perhaps we no longer need to compare every pair.

Perhaps neighboring reservations in sorted order tell us enough.

This is a recurring theme across algorithms.

Sorting, hashing, indexing, maintaining a running sum, or recording visited states can turn a problem from repeated searching into incremental work.

The useful question isn't:

"Which algorithm does the interviewer want?"

It's:

**"What information am I repeatedly rediscovering, and what structure would let me avoid rediscovering it?"**

## 4. An algorithm needs a reason it stays correct

Suppose you sort by start time and compare neighboring intervals.

Why should that work?

Maybe it seems plausible.

But plausible isn't proof.

We need to establish a property that remains true because of the sorting.

That property is an **invariant**.

An invariant is a condition maintained throughout an algorithm that allows us to reason about its correctness.

For this problem, the ordering gives us a powerful guarantee: if any two intervals overlap, there must also be an overlapping pair of neighboring intervals in start-time order.

We'll derive that carefully in the Deep Dive.

For now, the important lesson is that finding an algorithm is only half the work.

You also need to know why it doesn't miss a valid answer.

## 5. Constraints tell you which roads are worth exploring

Suppose the interviewer says the input contains at most twenty reservations.

The quadratic solution is perfectly reasonable.

It is simple, easy to verify, and fast enough.

Now suppose the input contains two hundred thousand reservations.

The same algorithm may become impractical.

The problem statement is otherwise identical.

But the acceptable solution changes.

This is why constraints matter.

They aren't decorative information appended to a coding exercise.

They tell you which algorithmic costs are affordable.

They also reveal hidden concerns.

Are numbers large enough to overflow the chosen representation?

Is memory limited?

Is the input already sorted?

Do we need one result or all matching pairs?

Can we mutate the input?

An experienced problem solver treats constraints as design information.

## 6. The goal isn't to become a pattern-recognition machine

Over the coming lectures, we'll study hashing, two pointers, sliding windows, binary search, greedy methods, stacks, trees, graphs, and dynamic programming.

These are useful tools.

But knowing their names isn't enough.

An interviewer can change a problem slightly and invalidate the technique you memorized.

A sliding-window approach may rely on nonnegative values.

A binary search may rely on a monotonic predicate.

A greedy choice may require an exchange argument.

A graph traversal may need additional state beyond a visited-node flag.

The important skill is recognizing the conditions under which a technique is justified.

That is what we'll practice throughout CS360.

## Three questions before the Deep Dive

1. Why is describing a correct quadratic solution valuable even when you know it won't scale?
2. What does sorting the reservations by start time give us that the original unsorted array doesn't?
3. Why is an algorithmic invariant more useful than saying, "I tested it on a few examples and it seems to work"?

Hold those questions in mind. Now we'll walk through a realistic interview from the first sentence to the final test.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The interview begins before the algorithm

It's 10:00 on a Thursday morning.

You join a remote technical interview.

After brief introductions, the interviewer shares a problem.

"You're given an array of booking intervals for a single physical hotel room. Return whether any two bookings overlap."

A weak candidate immediately starts writing code.

Another candidate asks ten minutes of speculative questions and never begins.

A stronger candidate clarifies the few assumptions that materially affect correctness.

"Are intervals represented by numeric start and end times?"

Yes.

"Is the end exclusive? If one booking ends at 11 and another starts at 11, is that permitted?"

Yes.

"Are all intervals valid, with start strictly less than end?"

Yes.

"Is the input sorted?"

No.

"How large can it be, and may I reorder it?"

Up to two hundred thousand intervals. The original input must remain unchanged.

Now we have a precise contract.

Every interval represents the half-open range from its start, inclusive, to its end, exclusive.

Two adjacent bookings may touch at a boundary without overlapping.

The input can be large, unsorted, and must not be mutated.

Those facts determine much of our solution.

### Clarification isn't procrastination

Notice that we didn't ask irrelevant questions.

We didn't spend time discussing hotel cancellation policies or database isolation levels.

Those would matter in a production reservation system, but not in this algorithmic exercise unless the interviewer introduced them.

The purpose of clarification is to identify assumptions that change the algorithm.

A good interview question has a practical consequence.

## 2. Manufacture examples before designing an optimization

Let's create examples.

Two bookings from 9 to 11 and from 11 to 13 do not overlap.

Two bookings from 9 to 12 and from 11 to 13 do overlap.

An empty array contains no overlapping pair.

A single interval cannot overlap another interval because there is no other interval.

These cases establish the basic semantics.

Now consider a less convenient example.

The input contains intervals from 15 to 17, from 9 to 12, and from 11 to 14.

The first interval appears first in the array, but it begins last in time.

The second and third overlap.

This example reveals that original array adjacency doesn't represent temporal adjacency.

That matters because a naïve algorithm comparing only neighboring input elements can miss conflicts.

### Why examples are part of reasoning

Good examples don't merely illustrate the problem.

They expose assumptions.

A tiny example helps verify the definition.

An edge case checks a boundary.

A counterexample attacks a tempting but incorrect rule.

In this case, the boundary between intervals is particularly important.

Since the end is exclusive, equality between one interval's end and another's start is allowed.

The overlap test must use strict inequality at that boundary.

This is the difference between a correct algorithm and one that incorrectly rejects back-to-back reservations.

## 3. The baseline: compare every pair

The most straightforward solution examines every pair of distinct reservations.

For each pair, determine whether their intervals overlap.

For two intervals A and B, overlap exists when A begins before B ends, and B begins before A ends.

Equivalently, the maximum of their start times must be less than the minimum of their end times.

The strict inequality reflects our half-open interval contract.

We compare each interval with every later interval.

If we find an overlapping pair, return true.

Otherwise, return false after all comparisons.

### Why this is a good baseline

It is easy to understand.

It requires no sorting.

It uses constant auxiliary memory.

It is also easy to test against small inputs.

That's valuable, especially when building an optimized solution that we want to verify independently.

### The cost

For an input of size n, the number of pairs grows quadratically.

We call the time complexity O(n²).

With twenty intervals, that's negligible.

With two hundred thousand, the worst-case number of comparisons is roughly twenty billion.

Even if each comparison is individually cheap, the total work can become unacceptable.

The problem isn't the cost of comparing two intervals.

It's how frequently we repeat that comparison.

### A useful interview sentence

"I can solve this correctly in quadratic time by checking every pair. Given the upper bound of two hundred thousand intervals, I'd look for structure that avoids comparing unrelated pairs."

That's clear, confident, and intellectually honest.

You have established a working baseline and identified why optimization is necessary.

## 4. Before optimizing, locate the wasted work

What does the quadratic solution do unnecessarily?

It repeatedly checks whether intervals far apart in time overlap.

Suppose one booking ends on Monday and another begins on Friday.

They clearly cannot overlap.

But in an unsorted array, the algorithm doesn't know which intervals are far apart until it examines their values.

We need some way to organize the intervals by time.

Sorting by start time is a natural candidate.

After sorting, the intervals are encountered in chronological order of their starts.

Now we may be able to reason locally rather than compare every pair.

This is the critical creative step.

We haven't memorized a named algorithm.

We've identified what makes the brute-force approach expensive and changed the representation to make that work unnecessary.

## 5. Derive the optimized solution

Imagine the intervals sorted by start time.

We examine them from left to right.

Suppose the current interval begins before the previous interval ends.

Then the intervals overlap, because both are valid intervals and the later interval begins while the earlier one is still active.

We can return true.

But what if every pair of neighboring intervals is non-overlapping?

Does that prove no pair overlaps?

We need to be careful.

### The proof

Suppose, for contradiction, that two intervals somewhere in the sorted sequence overlap.

Call them interval i and interval j, with i occurring earlier than j.

Because the intervals are sorted by start time, interval i begins no later than interval j.

For them to overlap, interval j must begin before interval i ends.

Now consider the interval immediately following i.

Its start lies between the start of i and the start of j.

Therefore, it also begins before interval i ends.

Since both intervals have positive duration, interval i and its immediate successor overlap.

So if any overlapping pair exists, some neighboring pair must overlap.

That means comparing neighboring intervals after sorting is sufficient.

We don't need to examine every possible pair.

This is the correctness argument.

### The invariant

As we scan the sorted intervals, we maintain the following property:

**Before examining the next neighboring pair, no earlier neighboring pair has overlapped.**

If the current pair overlaps, we have found a valid answer.

If the scan reaches the end, no neighboring pair overlaps.

And our proof establishes that any overlapping pair anywhere would imply a neighboring overlap.

Therefore, the algorithm is correct.

Notice the difference between saying "this seems plausible" and establishing why a missed conflict is impossible.

That reasoning is what an interviewer wants to hear.

## 6. Analyze the new cost

We need to sort the intervals.

Comparison sorting generally takes O(n log n) time.

After sorting, we make one linear pass through the intervals.

That takes O(n).

The total is dominated by sorting, giving O(n log n) time.

We must also respect the requirement not to modify the input.

So we sort a copy rather than the original array.

That copy requires O(n) additional memory.

Sorting may also use implementation-dependent auxiliary space.

For a TypeScript solution using a copied array and a standard comparison sort, reporting O(n) additional storage for the copy is appropriate, with the sorting implementation's overhead acknowledged separately if needed.

### Is this optimal?

We have improved the worst-case time substantially over quadratic comparison.

But don't claim it is the mathematically optimal solution for every imaginable input domain.

If times were small bounded integers, a specialized representation might permit different strategies.

If the data were already sorted, the scan alone would take O(n).

If the input arrived as an online stream in arbitrary order, we would face a different set of constraints.

Our solution is a good general approach for the stated problem.

That is enough.

An interview isn't improved by making unsupported claims about global optimality.

## 7. Test the algorithm against its weakest assumptions

Now that we have a candidate solution, test it systematically.

### Empty and one-element arrays

There is no pair to overlap.

The answer is false.

### Exactly touching boundaries

The intervals from 9 to 11 and from 11 to 13 do not overlap.

Our condition must reflect that equality is allowed.

### Identical intervals

Two reservations both covering 9 to 11 clearly overlap.

### Unsorted input

Sorting makes the original order irrelevant to the result.

### Several intervals sharing a start

Any two positive-duration intervals beginning at the same instant overlap.

The scan should detect that.

### Very large or negative timestamp values

If the contract allows numeric timestamps, negative values can still represent valid points on a timeline.

Their sign isn't the issue.

Correct numeric comparison is.

In JavaScript, we'd also want the contract to guarantee finite, valid numeric values if the input may come from untrusted sources.

### Input preservation

The problem explicitly prohibits mutating the original array.

A solution calling an in-place sort directly on the input violates the contract even if it returns the correct Boolean answer.

This is easy to miss.

Correctness includes the API contract, not merely the returned value.

## 8. The interviewer changes one requirement

Just as you're finishing, the interviewer asks:

"What if I wanted the number of simultaneous bookings at the busiest moment?"

Now the previous algorithm isn't enough.

It can detect whether a conflict exists, but it doesn't directly calculate maximum concurrency.

We might consider start and end events, process them chronologically, and maintain the number of active intervals.

That is a different problem.

The same interval representation remains useful, but our maintained state changes.

Or the interviewer asks:

"What if bookings arrive continuously and you must detect conflicts without sorting the entire history each time?"

Now we need an online data structure or another incremental strategy.

Or:

"What if the input is guaranteed to be sorted?"

Then we can skip sorting and achieve a linear scan.

Or:

"What if I need the indices of the first overlapping pair in original input order?"

Now the meaning of *first* must be clarified. Our sorted chronology may not correspond to the required original-order result.

These changes illustrate something important.

A memorized solution can fail when the contract changes.

An understanding of the invariant lets us determine which part of the solution is still valid.

## 9. When you're stuck, make the problem smaller

Now consider a different interview.

You don't recognize the problem.

You have no idea which algorithm family it belongs to.

What should you do?

The worst response is often sitting silently, hoping that a familiar pattern suddenly appears.

Instead, reduce the uncertainty.

Try the problem with two elements.

Then three.

Try an example where all values are equal.

Try one where they are sorted.

Try one where they are reversed.

Ask what a brute-force solution would examine.

Identify repeated work.

Ask whether that repeated work can be stored, avoided, or bounded.

This frequently reveals the appropriate technique.

### Change the representation

Some problems become simpler when expressed differently.

An array problem may become a problem about prefix sums.

A scheduling problem may become a problem about sorted events.

A relationship problem may become a graph.

A repeated-membership question may become a set lookup.

A search over answers may become a monotonic decision problem.

The creative act is often choosing the right representation, not remembering a complicated formula.

### Separate correctness from speed

If you can produce a correct solution but cannot optimize it immediately, say so.

Explain the baseline.

Analyze its complexity.

Identify the limiting operation.

Then explore alternatives.

A candidate who reasons coherently toward a solution is often more convincing than one who jumps to an elegant algorithm without being able to explain why it works.

## 10. How to communicate while solving

An interviewer cannot reliably evaluate reasoning you never express.

But this doesn't mean narrating every keystroke or saying everything that passes through your mind.

A useful rhythm is:

First, summarize the contract.

Second, demonstrate a small example.

Third, describe a correct baseline.

Fourth, explain which part is too expensive.

Fifth, propose the optimization and its invariant.

Sixth, implement.

Seventh, test edge cases and analyze complexity.

The emphasis changes as you work.

During clarification, talk about assumptions.

During algorithm design, talk about the invariant.

During coding, explain the structure rather than every line.

During testing, talk about what could invalidate your solution.

### When you discover a mistake

Suppose halfway through implementation you realize your sorting algorithm mutates the input.

Don't hide it.

Explain the issue and correct it.

"I've realized the input must remain unchanged, so I'll sort a copy."

That's an ordinary engineering adjustment.

A problem-solving process that can detect and correct mistakes is more valuable than pretending no mistakes occurred.

### When the interviewer provides a hint

A hint isn't a verdict that you failed.

Treat it as new information.

Explain how it changes your understanding.

If the interviewer suggests sorting, don't immediately write a sorting call and stop thinking.

Ask why sorting helps.

What relationship does it create?

What comparison can now be eliminated?

The goal is to turn the hint into a justified step.

## 11. Complexity is a design tool, not a recital

Algorithmic complexity is useful because it lets us compare how work grows as input size increases.

But Big O is not a precise runtime prediction.

An O(n log n) algorithm may be slower than O(n²) on tiny inputs because of constants and setup overhead.

An O(n) solution may require so much memory that it becomes unsuitable for the environment.

A sorting solution may be simple and reliable when n is moderate.

A specialized data structure may be theoretically faster for repeated operations but significantly more difficult to maintain.

The point is to connect complexity to constraints.

For our reservations problem, a two-hundred-thousand-element input makes quadratic pair checking a poor general choice.

Sorting followed by one scan is a reasonable compromise.

It improves the growth rate without introducing an elaborate structure.

### Be precise about what you count

Time complexity measures the growth of work.

Space complexity measures additional memory, under the chosen convention.

If you sort a copied array, the copy consumes O(n) space.

If you sort in place, the sorting algorithm's own memory requirements still matter.

If you allocate a hash set of every observed identifier, that's O(n) additional storage in the worst case.

And if you must return all matching pairs, output size itself can dominate memory and runtime.

A good complexity explanation identifies the operations creating the cost.

It doesn't merely state two symbols and move on.

## 12. One more trap: solving a different problem correctly

Imagine the interviewer asks for the earliest repeated identifier in a sequence.

You write code that returns the smallest identifier appearing twice.

Those aren't the same requirement.

For the sequence 8, 3, 7, 7, 3, the earliest repeat encountered during a left-to-right scan is 7.

The smallest repeated identifier is 3.

Both answers could be justified under different specifications.

Only one matches the intended contract.

This is why clarification and examples matter.

The most efficient algorithm in the world is useless if it solves the wrong problem.

### Beware of implicit assumptions

Does "first" mean earliest by original index, earliest timestamp, or smallest value?

Does a duplicate mean two identical values or two records sharing a business key?

Are repeated values allowed?

Can negative numbers occur?

Do intervals include their endpoints?

May you mutate the input?

These aren't administrative details.

They can alter the correctness proof.

## 13. Build a repeatable personal method

Let's turn everything into a practical routine.

When facing an unfamiliar problem, use the following sequence.

**Clarify.** Identify the required result, input guarantees, edge semantics, and constraints.

**Model.** Construct small examples and at least one counterexample to a tempting assumption.

**Baseline.** Describe the simplest correct solution.

**Locate waste.** Identify repeated work or unnecessary exploration.

**Restructure.** Introduce sorting, hashing, maintained state, or another representation only when it solves the identified waste.

**Justify.** State an invariant or correctness argument.

**Implement.** Translate the plan into code without losing its essential properties.

**Verify.** Test ordinary cases, boundaries, and counterexamples.

**Communicate.** Explain complexity and trade-offs, and adapt when requirements change.

You won't execute this as a rigid ceremony during every interview.

On an easy problem, several steps may take seconds.

On a difficult problem, you may revisit earlier steps several times.

The value is that you always have a productive next action.

You never need to sit passively and wait for a flash of inspiration.

---

# The Oral Examination

Answer aloud before reading the solutions.

**Question 1 — The baseline**

Why should you often describe a brute-force solution before proposing an optimized one?

**Question 2 — The interval invariant**

After sorting valid half-open intervals by start time, why is checking neighboring pairs sufficient to detect whether any overlap exists?

**Question 3 — Complexity**

For two hundred thousand intervals, compare the asymptotic cost of checking every pair with sorting followed by a linear scan.

**Question 4 — The contract change**

Suppose the interviewer says the input array must not be mutated. Which part of your implementation must change, and what space cost follows?

**Question 5 — The unfamiliar problem**

You cannot recognize a known algorithmic pattern. What concrete reasoning actions can you take without waiting for a hint?

**Question 6 — The misleading answer**

A problem asks for the earliest repeated value encountered during a scan. Why is returning the smallest duplicated value potentially incorrect?

---

# Solutions and Discussion

## Solution 1 — Establish correctness before optimization

A brute-force solution clarifies the required result and gives us a reference implementation.

Its complexity reveals why optimization is necessary.

It also identifies repeated work that a better representation may avoid.

## Solution 2 — Sorting creates a useful neighboring relationship

Suppose overlapping intervals i and j exist in start-time order.

The interval immediately after i begins no later than j, which begins before i ends.

Therefore, that neighboring interval also overlaps i.

If any overlap exists, a neighboring overlap must exist.

Checking every neighboring pair is sufficient.

## Solution 3 — Reduce quadratic growth

Pairwise comparison is O(n²).

Sorting followed by one scan is O(n log n), with the sort dominating.

At large input sizes, the second approach avoids enormous numbers of unnecessary comparisons.

## Solution 4 — Sort a copy

Use a copied collection rather than sorting the original array directly.

That introduces O(n) memory for the copy.

The sorting implementation may require additional auxiliary memory depending on the runtime.

## Solution 5 — Reduce uncertainty systematically

Clarify the contract, create small examples, derive a correct baseline, identify repeated work, try alternative representations, and look for a maintained invariant.

Explain the reasoning as it develops.

## Solution 6 — "First" has multiple meanings

The earliest repeated value is the value whose second occurrence appears first in the scan.

That need not be the numerically smallest duplicated value.

The algorithm must follow the exact meaning of the requested ordering.

---

# The Mental Model Worth Keeping

When you encounter an unfamiliar coding problem, don't ask:

"Which algorithm am I supposed to remember?"

Ask:

**What exactly counts as a correct answer?**

**What is the simplest way I can produce one?**

**Which work is being repeated unnecessarily?**

**What property would let me avoid that work safely?**

**How can I prove the optimized solution doesn't miss a valid answer?**

That is the difference between memorizing solutions and developing algorithmic judgment.

# Next Lecture — CS360-L02: Arrays, Strings, Hashing, and Sliding Windows

In the next lecture, we'll develop several of the most useful techniques for avoiding repeated work in sequences.

Hashing lets us remember what we've seen.

Two pointers let us coordinate movement through ordered data.

Sliding windows let us maintain information about a changing interval without recomputing everything inside it.

Prefix sums let us answer range questions using accumulated information.

But each technique has assumptions.

The goal will be to recognize those assumptions from a problem statement and derive the technique rather than simply associate it with a familiar keyword.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Coding Gym — Attempt Before Reading the Solutions

This is the essential half of CS360.

The spoken lecture introduced a method. Now we need to apply it without being shown the answer first.

Use TypeScript or another language you're comfortable using in interviews. TypeScript is used in the sample solutions.

For each problem, follow this process:

1. Clarify the contract and write examples.
2. Describe a brute-force baseline.
3. Identify the work you want to avoid.
4. Design and implement an improved algorithm.
5. Test edge cases and explain complexity.
6. Compare your reasoning against the solution only afterward.

Do not read the hints immediately.

An unfamiliar problem is supposed to create uncertainty. Working through that uncertainty is the skill we're training.

## Problem A — The First Repeated Reservation ID

**Difficulty:** Introductory  
**Suggested attempt:** 12–15 minutes

A backend service receives a sequence of reservation identifiers.

Your task is to return the first identifier that appears for a second time during a left-to-right scan.

If no identifier repeats, return `null`.

The array may be unsorted.

Identifiers are integers, including possibly negative values.

### Examples

Input: `[8, 3, 7, 7, 3]`  
Output: `7`

Input: `[4, 9, 4, 2, 9]`  
Output: `4`

Input: `[1, 2, 3, 4]`  
Output: `null`

Input: `[]`  
Output: `null`

### Constraints

- Up to 200,000 identifiers.
- The input must remain unchanged.
- Return the repeated value, not its index.
- Earliest means the earliest *second occurrence* encountered during the scan.

### Your task

Develop a correct baseline and improve it.

Explain what information must be remembered between elements.

Then answer:

How would the solution change if the input were too large to fit in memory and arrived as a stream?

## Problem B — The Busiest Moment at the Hotel

**Difficulty:** Intermediate  
**Suggested attempt:** 20 minutes

You're given reservations for a collection of rooms.

Each reservation is a half-open interval from `start`, inclusive, to `end`, exclusive.

Determine the maximum number of reservations active simultaneously.

All intervals are valid, with start strictly less than end.

### Examples

Input:

```text id="zqo10n"
[9, 11)
[10, 12)
[12, 14)
```

Output: `2`

The first and second reservations overlap. The third begins when the second ends, so they are not simultaneously active at that boundary.

Another input:

```text id="y692bi"
[1, 5)
[2, 6)
[3, 7)
[7, 9)
```

Output: `3`

The first three reservations overlap.

The final reservation begins when the third ends.

### Constraints

- Up to 200,000 intervals.
- Start and end times are finite numbers.
- The input is unsorted.
- Do not modify the input array.
- Return zero for an empty input.

### Your task

Begin with an obviously correct approach.

Then derive a solution that doesn't inspect every pair of reservations.

Think about what happens at the exact instant a reservation begins or ends.

**Important:** Equal timestamps require deliberate handling. The end of one half-open interval must not count as overlapping the start of another.

## Problem C — Find the Shortest Expensive Period

**Difficulty:** Intermediate  
**Suggested attempt:** 20–25 minutes

A backend processes tasks sequentially.

You receive a list of nonnegative integer task costs.

Find the length of the shortest nonempty contiguous sequence whose total cost is at least a given positive target.

If no such sequence exists, return zero.

### Examples

Input: `target = 7`, `costs = [2, 3, 1, 2, 4, 3]`  
Output: `2`

The final two costs, 4 and 3, sum to seven.

Input: `target = 5`, `costs = [1, 1, 1]`  
Output: `0`

Input: `target = 3`, `costs = [3]`  
Output: `1`

### Constraints

- Up to 200,000 costs.
- Every cost is between zero and one million.
- The target is a positive safe integer.
- Intermediate sums fit within JavaScript's safe integer range.
- The sequence must be contiguous.
- Do not modify the input.

### Your task

Explain a correct brute-force solution.

Then identify what work can be preserved as the interval grows or shrinks.

Finally, answer this follow-up:

**Would your optimized algorithm still be correct if task costs could be negative?**

Do not answer merely by intuition. Find an example that supports or refutes the claim.

---

# Progressive Hints

Read only the hints for the problem you're attempting. Use one hint at a time.

## Problem A hints

**Hint 1:** The answer depends on what has already appeared in the scan.

**Hint 2:** You need fast membership checks, not sorting.

**Hint 3:** Maintain a set of identifiers observed so far. When the current identifier already belongs to the set, you've found the earliest second occurrence.

## Problem B hints

**Hint 1:** The active count changes only when an interval begins or ends.

**Hint 2:** Represent every start as a positive event and every end as a negative event.

**Hint 3:** Sort events by time. For equal timestamps, process end events before start events to respect half-open intervals.

**Hint 4:** Maintain the current active count and the maximum value observed after processing start events.

## Problem C hints

**Hint 1:** A contiguous interval is determined by a left boundary and a right boundary.

**Hint 2:** Because costs are nonnegative, moving the right boundary forward cannot decrease the sum.

**Hint 3:** Once an interval's sum meets the target, try advancing the left boundary to make it shorter.

**Hint 4:** Keep a running sum rather than recalculating the sum of every interval.

---

# Worked Solutions and Interview Explanations

Read this section only after making a serious attempt.

## Solution A — A set of previously seen identifiers

### Baseline

For every identifier, compare it with all earlier identifiers.

If a match exists, return the current identifier.

This is correct because we scan in order and return at the first repeated occurrence.

But the worst-case time is O(n²).

### Optimization

The repeated work is checking whether the current identifier occurred earlier.

A hash set can remember that information.

For each identifier:

If it is already in the set, return it.

Otherwise, insert it.

We only need one pass.

### TypeScript

```typescript id="idw5l5"
function firstRepeated(ids: number[]): number | null {
  const seen = new Set<number>();

  for (const id of ids) {
    if (seen.has(id)) {
      return id;
    }

    seen.add(id);
  }

  return null;
}
```

### Complexity

Time: O(n) expected, assuming typical constant-time hash-set operations.

Space: O(n) in the worst case.

The array isn't modified.

### Why it's correct

Before processing each element, the set contains exactly the identifiers encountered earlier.

If the current identifier is present, it has occurred before.

Because we scan from left to right and return immediately, this is the earliest second occurrence.

### Streaming follow-up

If identifiers arrive as a stream, the same algorithm can process them incrementally.

But it still needs memory proportional to the number of distinct identifiers observed.

If memory is strictly bounded while the identifier domain is unbounded, exact duplicate detection may require external storage or a different contract.

A Bloom filter could reduce memory for approximate membership detection, but it permits false positives and therefore doesn't preserve the exact original guarantee.

The important lesson is to distinguish an exact problem from an approximate one.

## Solution B — Sweep through start and end events

### Baseline

One approach is to consider each interval's boundaries and count how many intervals are active at those moments.

Doing this independently for every boundary can require O(n²) work.

The repeated effort comes from scanning many intervals to recompute the active count.

### Optimization

The active count changes only at starts and ends.

So we create events.

A start increases the count by one.

An end decreases it by one.

Sort the events chronologically and process them in order.

For equal timestamps, process endings before beginnings.

That ensures a reservation ending at time 11 is not considered simultaneous with one beginning at 11.

### TypeScript

```typescript id="4aqf51"
type Interval = {
  start: number;
  end: number;
};

type Event = {
  time: number;
  delta: 1 | -1;
};

function maxConcurrent(intervals: Interval[]): number {
  const events: Event[] = [];

  for (const interval of intervals) {
    events.push({ time: interval.start, delta: 1 });
    events.push({ time: interval.end, delta: -1 });
  }

  events.sort((a, b) =>
    a.time - b.time || a.delta - b.delta
  );

  let active = 0;
  let maximum = 0;

  for (const event of events) {
    active += event.delta;

    if (active > maximum) {
      maximum = active;
    }
  }

  return maximum;
}
```

### Why the tie-breaking rule works

For half-open intervals, an interval ending at time t is no longer active at t.

An interval beginning at t is active at t.

Processing the ending first removes reservations that have finished before adding the new ones.

Since all intervals have positive duration, the event sequence remains coherent under that ordering.

### Complexity

There are two events per interval.

Sorting takes O(n log n).

Processing the events takes O(n).

The event array consumes O(n) additional space.

### Why it's correct

Between event timestamps, the set of active intervals cannot change.

All changes in active count occur at starts and ends.

Our sweep processes every such change in chronological order.

The maintained active count therefore represents the number of active reservations after the relevant events, and the maximum records the peak concurrency.

### Interview follow-up

What if the interviewer asks for the earliest time when maximum concurrency occurs?

We can track the timestamp when a new maximum is first reached.

But we must carefully define whether the answer refers to the event instant or an open interval between events.

This is where specifying temporal semantics matters.

## Solution C — Maintain a shrinking window

### Baseline

For each starting position, expand the right boundary until the sum reaches the target or the array ends.

If we recompute or repeatedly process large intervals from each starting point, we can require quadratic work.

### Observation

All task costs are nonnegative.

Therefore, extending the right boundary cannot decrease the window sum.

And removing values from the left cannot increase it.

This monotonic behavior is the key property.

### Optimized algorithm

Maintain a window with left and right boundaries and a running sum.

Move the right boundary forward, adding each new cost.

Whenever the sum reaches or exceeds the target, record the current window length.

Then advance the left boundary, subtracting the value that leaves the window.

Continue shrinking while the sum still meets the target.

Once it no longer does, resume expanding to the right.

Each boundary moves forward at most n times.

### TypeScript

```typescript id="yeolv9"
function shortestPeriod(
  target: number,
  costs: number[]
): number {
  let left = 0;
  let sum = 0;
  let best = Infinity;

  for (let right = 0; right < costs.length; right++) {
    sum += costs[right];

    while (sum >= target) {
      best = Math.min(best, right - left + 1);

      sum -= costs[left];
      left++;
    }
  }

  return best === Infinity ? 0 : best;
}
```

### Complexity

Time: O(n), because each element enters the window once and leaves at most once.

Additional space: O(1).

### The invariant

At every step, `sum` represents the total cost of the current window.

When the window meets the target, shrinking it from the left tests whether a shorter qualifying window exists for the current right boundary.

Because all costs are nonnegative, once shrinking makes the sum too small, removing even more values cannot restore the target.

We can safely stop shrinking and expand the right boundary again.

### What if negative costs are allowed?

The algorithm is no longer generally correct.

Its reasoning depends on monotonic behavior.

With negative values, removing a left-hand value can increase the sum.

That invalidates the assumption that once the window falls below the target, further shrinking cannot help.

For example:

```text id="zrg9d3"
target = 3
costs = [2, -1, 2, 2]
```

The shortest qualifying interval is the final `[2, 2]`, of length two.

The standard nonnegative sliding-window algorithm can miss it because the negative value disrupts the relationship between window movement and sum.

A more general solution for negative values uses a different strategy, commonly involving prefix sums and a monotonic deque.

We will revisit the underlying patterns later.

The lesson isn't to memorize that advanced algorithm today.

It's to understand why the original one stopped being justified.

**A change in assumptions can invalidate an invariant, even if the code still runs.**

---

# Retrieval Practice — Turn Understanding Into Skill

You have now seen the worked solutions.

That creates a dangerous feeling of familiarity.

Everything makes sense.

The code is short.

Perhaps you feel you could have written it.

Maybe you could.

But recognition isn't the same as recall.

We need to test that.

## First retrieval: next study session

Without opening the solutions, attempt one of the three problems again.

Begin with the explanation, not the code.

State the contract.

Describe the baseline.

Explain the optimization.

Name the invariant.

Then implement.

If you cannot reconstruct the invariant, don't immediately reread the entire chapter. Try reconstructing the reasoning from a small example first.

## Second retrieval: after several days

Choose a variation.

For Problem A, return the index of the first second occurrence rather than the identifier.

For Problem B, return the earliest time when maximum concurrency begins.

For Problem C, change the contract to allow negative values and explain precisely why the original technique fails before looking for another algorithm.

This tests whether you learned a transferable principle or merely memorized a particular solution.

## Your self-assessment rubric

For each problem, score yourself on five dimensions from zero to two.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Contract | Missed key assumptions | Clarified after difficulty | Clarified proactively |
| Baseline | No correct approach | Correct after hint | Derived independently |
| Optimization | Couldn't find | Needed hint | Derived and justified |
| Implementation | Incorrect/incomplete | Minor errors | Correct and tested |
| Communication | Couldn't explain | Partial explanation | Clear invariant and trade-offs |

A score of ten is excellent.

A score of six or seven with a clear understanding of your weak points is useful progress.

Don't use the score to judge your intelligence.

Use it to identify what to practice next.

A candidate who knows exactly why they failed a problem has a much stronger route to improvement than one who merely collects another accepted solution.

## The mistake journal

After each exercise, record one short note.

Not a transcription of the solution.

Record the obstacle.

Examples:

"I did not consider using a set to preserve earlier observations."

"I understood sorting but could not prove that neighboring intervals were sufficient."

"I forgot the half-open boundary rule."

"I chose sliding window without checking whether values were nonnegative."

"I started coding before specifying the meaning of first."

These notes become your most valuable revision material.

They identify the reasoning habits that need strengthening.

---

# Further Reading

Useful references for deliberate practice:

- **MIT OpenCourseWare — Introduction to Algorithms:** https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/
- **CP-Algorithms — Algorithms for Competitive Programming:** https://cp-algorithms.com/
- **The Algorithm Design Manual**, Steven S. Skiena
- **Elements of Programming Interviews**, Adnan Aziz, Tsung-Hsien Lee, and Amit Prakash

Related programme chapters:

- CS110-L03 — Algorithms and the Cost of Computation
- CS110-L04 — Data Structures: Choosing How to Remember Things
- CS110-L05 — Searching, Sorting, and Finding Shortcuts
- CS120-L01 — Logic, Proofs, and Invariants
- CS360-L02 — Arrays, Strings, Hashing, and Sliding Windows

---

## Dense Cheatsheet — Interview Glance Card

```text id="jv94oa"
CS360-L01 — SOLVING UNFAMILIAR CODING PROBLEMS

CORE IDEA
  Don't wait to recognize an algorithm.
  Make progress by reducing uncertainty.

THE REPEATABLE PROCESS
  1. CLARIFY   Define inputs, outputs, edge semantics, constraints
  2. MODEL     Build small examples and counterexamples
  3. BASELINE  State a simple correct solution
  4. LOCATE    Find repeated/unnecessary work
  5. IMPROVE   Change representation or maintained state
  6. JUSTIFY   State invariant / correctness argument
  7. CODE      Implement while preserving the contract
  8. TEST      Boundaries, duplicates, empty inputs, extremes
  9. EXPLAIN   Complexity, assumptions, alternatives, trade-offs

CLARIFICATION QUESTIONS
  Sorted or unsorted?
  Duplicates allowed?
  Negative values allowed?
  Inclusive or exclusive boundaries?
  Return one answer or every answer?
  Original order significant?
  May input be mutated?
  n maximum?
  Memory constraints?
  Exact or approximate result?

BASELINE
  Brute force establishes correctness
  Complexity shows why improvement matters
  Baseline can serve as differential-test oracle
  Don't skip it out of embarrassment

OPTIMIZATION
  Identify what is repeatedly searched/recomputed
  Sorting creates ordered relationships
  Hashing preserves membership information
  Maintained state avoids recomputation
  Prefix sums preserve accumulated information
  Invariants explain why skipped work is safe

PROOF / INVARIANTS
  Initialization: invariant holds before processing
  Maintenance: every step preserves it
  Termination: invariant implies correct final answer
  Tests provide evidence, not a universal correctness proof

INTERVAL PROBLEM
  Half-open intervals: [start, end)
  Touching end/start does not overlap
  Pair overlap iff max(starts) < min(ends)
  Brute force O(n²)
  Sort by start, check adjacent pairs: O(n log n)
  Proof: any overlapping pair implies adjacent overlap
  Copy input first when mutation prohibited

COMPLEXITY
  O(n²) pairwise comparison
  O(n log n) comparison sorting + O(n) scan
  O(n) expected hash-set lookup pass
  O(n) sliding window when its assumptions hold
  Account for extra storage, copies and output size
  Big O isn't exact wall-clock time

PATTERN PRECONDITIONS
  Sliding window may require nonnegative contributions
  Binary search needs monotonic predicate/order
  Greedy needs a justified local-choice property
  Hashing may require O(n) memory
  Sorting may destroy original-order information
  Constraint change => reconsider correctness proof

INTERVIEW COMMUNICATION
  Clarify briefly
  State baseline
  Name limiting cost
  Explain improvement
  Give invariant
  Implement
  Test adversarial examples
  Summarize complexity and trade-offs

WHEN STUCK
  Reduce to n=2 or n=3
  Try all equal / strictly ordered / reversed inputs
  Find a counterexample to first idea
  Ask what repeated work can be remembered
  Change representation
  Use interviewer hint as information, not defeat

PRACTICE
  Solve unaided before hints
  Use one hint at a time
  Explain before coding
  Reattempt later without solution
  Record the obstacle, not copied code

SENIOR INTERVIEW LINE
  "I'll clarify the contract and constraints, establish a
   correct baseline, identify the repeated work, then derive
   an optimization and explain the invariant that makes it
   correct. Finally I'll test edge cases and analyze the
   time and memory trade-offs."

MENTAL MODEL
  Correctness first.
  Find the wasted work.
  Preserve a useful invariant.
  Prove the shortcut is safe.
```
