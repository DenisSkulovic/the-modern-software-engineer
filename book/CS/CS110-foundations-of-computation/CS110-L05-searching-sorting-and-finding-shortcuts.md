---
id: CS110-L05
course: CS110
title: "Searching, Sorting, and Finding Shortcuts"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [CS101-S05]
prev: CS110-L04
next: null
---




# CS110 — Foundations of Computation and Algorithms
## Lecture 05: Searching, Sorting, and Finding Shortcuts

*Binary search, sorting, recursion, divide and conquer, greedy algorithms, graph search, and the surprisingly creative art of avoiding unnecessary computation.*

**Estimated study time:** 75–90 minutes, including experiments and exercises.

---

### How to read this session

Sixteen rooms. The theme today: **don't search where the answer cannot be.**

```text
  ROOM MAP
  ─────────────────────────────────────────────────────────────
  ① Railway greed      ② Binary search        ③ Invariants
  ④ Search the answer  ⑤ Why sort?            ⑥ Merge / D&C
  ⑦ Sorting lower bound ⑧ Greedy yes/no       ⑨ BFS·DFS·Dijkstra
  ⑩ Dynamic programming ⑪ Six patterns        ⑫ Elegant vs boring
  ⑬ Lab               ⑭ Challenges           ⑮ Solutions
  ⑯ Takeaways
  ─────────────────────────────────────────────────────────────
```

| Rooms | Theme | Feel |
|---|---|---|
| 1 | Cheap next ticket ≠ cheapest trip | mystery |
| 2–4 | Binary search + invariants + search-on-answer | the sharp knife |
| 5–10 | Sort, D&C, lower bounds, greedy, graphs, DP | toolkit |
| 11–16 | Patterns, judgment, lab, challenges | practice |

> **Reading tip:** Sticky notes name the *shortcut*. Diagrams show where work got skipped.

---

# 1. The Journey That Should Have Been Cheaper

> **Case file #005** — *Berlin → Vilnius. Budget traveler. Algorithm picks the worst route.*

Imagine you're building a European railway journey planner.

A customer wants to travel from Berlin to Vilnius. They're flexible about the route, willing to change trains, and interested in minimizing the total ticket price.

Your application has access to a simplified network of possible connections.

For illustration, let's invent these fares:

| Connection | Price |
|---|---:|
| Berlin → Warsaw | €10 |
| Warsaw → Vilnius | €90 |
| Berlin → Kaunas | €25 |
| Kaunas → Vilnius | €20 |
| Berlin → Vilnius | €80 |

These are hypothetical fares, not actual railway prices.

Your developer implements a seemingly reasonable algorithm:

1. Start in Berlin.
2. Look at the available outgoing connections.
3. Choose the cheapest connection.
4. Repeat until reaching Vilnius.

What could possibly go wrong?

```text
  GREEDY PATH                         BETTER PATHS
  ───────────                         ────────────
  Berlin ──€10──► Warsaw              Berlin ──€25──► Kaunas
                    │                                   │
                    €90                                 €20
                    ▼                                   ▼
                 Vilnius                             Vilnius
                 TOTAL €100                           TOTAL €45  ✓

  Direct: Berlin ──€80──► Vilnius   (also better than greedy)
```

The algorithm begins in Berlin and sees three options.

Warsaw costs €10.

Kaunas costs €25.

Vilnius directly costs €80.

Naturally, it chooses Warsaw.

Then it continues to Vilnius for another €90.

Total cost: **€100**.

Meanwhile, the customer could have traveled through Kaunas for just €45.

Or directly for €80.

Our algorithm has selected the most expensive of the three routes.

Wonderful. We've invented a travel agency that actively punishes budget-conscious customers.

But notice something important.

The program may be perfectly implemented.

No bugs.

No incorrect calculations.

No missing data.

It faithfully chooses the cheapest outgoing connection at every step.

The failure is conceptual.

> **Sticky note #1**
>
> Choosing the best immediate option doesn't necessarily produce the best overall solution.

This is the distinction between a *local optimum* and a *global optimum*.

The cheapest next step may be part of a terrible overall route.

And recognizing this distinction is central to algorithm design.

Today we're going to investigate several powerful ways of solving problems more intelligently:

| Shortcut | Idea |
|---|---|
| Sorting | expose useful structure |
| Eliminating search space | don't look where the answer can't be |
| Divide and conquer | smaller problems → combine |
| Exploit math properties | skip brute force |
| Reuse results | memoization / DP |
| Search networks carefully | BFS / DFS / Dijkstra |

But we'll begin with one of the simplest and most elegant algorithms ever invented.

```text
  ✓ Room 1 complete — local cheapest ≠ global cheapest
```

---

# 2. How to Find Something Among a Billion Possibilities

Imagine a database containing one billion customer records.

Every customer has a unique numerical ID.

The records are sorted by that ID.

You need to locate customer 847,293,104.

One possible strategy is to begin with the first record.

Check its ID.

Not a match.

Move to the second.

Not a match.

Continue.

In the worst case, you might inspect one billion records.

That's linear search.

O(n).

Now consider a different approach.

Open the collection near the middle.

The ID is approximately 500 million.

Your target is larger.

Therefore, you can discard the entire lower half of the search space.

Half a billion records eliminated after one comparison.

```text
  Binary search vs linear search
  ──────────────────────────────
  Linear:  check 1, check 2, check 3, …  (up to a billion)

  Binary:  middle → drop half
           middle → drop half
           middle → drop half
           … ~30 steps for a billion
```

Examine the middle of the remaining half.

Roughly 750 million.

Your target is still larger.

Discard another quarter-billion candidates.

Next comparison: approximately 875 million.

Too large.

Discard everything above it.

And continue.

This is **binary search**.

It's extraordinarily simple, but its consequences are remarkable.

Every comparison can eliminate approximately half the remaining candidates.

Let's see how many comparisons are needed.

| Number of records | Approximate halvings required |
|---|---:|
| 1,024 | 10 |
| 1 million | 20 |
| 1 billion | 30 |
| 1 trillion | 40 |

One trillion records.

About forty decisions to narrow the location to a single candidate.

That's astonishing.

Of course, these are counts of logical search steps, not promises about physical execution time. Reading data from a database or disk introduces additional costs.

But the algorithmic improvement is enormous.

## The essential trick

Binary search is not fast because the computer performs comparisons unusually quickly.

It's fast because each comparison tells us something about a huge number of elements.

If we know the collection is sorted, comparing the target against the middle element allows us to eliminate an entire half.

Without sorting, we lose that ability.

Imagine the customer IDs are arranged randomly.

If the middle ID is smaller than the target, does that prove the target belongs in the right half?

No.

It might be anywhere.

> **Sticky note #2**
>
> Binary search works because the organization of the data allows each comparison to eliminate possibilities.

This connects directly to CS110-L04.

A data structure and an algorithm cooperate.

The structure preserves useful information.

The algorithm exploits it.

```text
  ✓ Room 2 complete — one comparison, half a billion gone
```

---

# 3. Binary Search Is Really About Maintaining a Promise

Let's implement binary search.

You probably already understand the basic idea, so we won't spend pages explaining every line of a loop.

Instead, let's examine the part that separates a reliable implementation from a subtly broken one.

Consider this function:

```typescript
function lowerBound(
  values: number[],
  target: number
): number {
  let left = 0;
  let right = values.length;

  while (left < right) {
    const middle = Math.floor(
      (left + right) / 2
    );

    if (values[middle] < target) {
      left = middle + 1;
    } else {
      right = middle;
    }
  }

  return left;
}
```

What does this function return?

Not necessarily the position of an existing matching element.

It returns the first position at which the value is greater than or equal to the target.

If no such element exists, it returns the array's length.

For example:

```typescript
const values = [2, 4, 4, 4, 7, 9];

lowerBound(values, 4);  // 1
lowerBound(values, 5);  // 4
lowerBound(values, 10); // 6
```

This variant is particularly useful because it behaves sensibly when the target is absent or appears multiple times.

But why does it work?

## The invariant

At every step, the algorithm maintains a promise about the interval `[left, right)`.

The notation means that `left` is included and `right` is excluded.

```text
  Invariant: answer lives in [left, right)
  ────────────────────────────────────────
  [==== candidate range ====)
   left                    right

  middle too small?  →  left = middle + 1
  otherwise?         →  right = middle

  Shrink until left === right  →  that's the insertion point
```

The algorithm maintains the fact that the first element greater than or equal to the target must be located within this interval, possibly at its right endpoint when no qualifying element exists.

At the beginning, the entire array is a candidate.

Then we examine the middle element.

If the middle value is smaller than the target, we know something important.

Because the array is sorted, every element at or before the middle position must also be smaller than the target.

We can safely discard all of them.

Otherwise, the middle position might be the first qualifying element.

So we keep it and discard everything to its right.

With every iteration, the candidate interval shrinks.

Eventually, `left` equals `right`.

Only one insertion position remains.

That's our answer.

This maintained promise is called a **loop invariant**.

A loop invariant is a property that remains true throughout the execution of a loop.

It's a fundamental technique for reasoning about correctness.

And it reveals something important about algorithms:

> **Sticky note #3**
>
> A correct algorithm doesn't merely perform plausible steps. Each step must preserve the conditions that make the final result valid.

This is particularly useful in interviews.

If someone asks why your binary search works, explaining the invariant is much stronger than saying, "Well, it keeps cutting the array in half."

## Why binary search is notoriously bug-prone

For such a simple idea, binary search has an impressive history of incorrect implementations.

Common mistakes include:

| Trap | Symptom |
|---|---|
| Wrong interval boundaries | off-by-one / missed element |
| Infinite loops | `left` never meets `right` |
| Skipping the target | wrong branch update |
| Duplicate mishandling | finds *a* match, not the bound you wanted |
| Wrong insertion position | returns existence, not lower/upper bound |
| Midpoint overflow (fixed-width ints) | silent wrong index |

In languages with fixed-width integer indices, even calculating the midpoint carelessly can produce integer overflow.

A common safer expression is:

`left + floor((right - left) / 2)`

For JavaScript's ordinary practical array indexing ranges, the overflow issue isn't usually relevant in the same way, but the general lesson remains.

Small boundary details can invalidate an otherwise sound algorithm.

That's why choosing clear interval conventions and maintaining invariants is so valuable.

```text
  ✓ Room 3 complete — binary search = shrinking a promise
```

---

# 4. The Trick Works on More Than Numbers

Let's take binary search somewhere more interesting.

Suppose your company processes large batches of jobs.

The jobs must be handled in their existing order.

You can distribute them across at most five processing days.

Each day has a maximum allowed workload.

Your question is:

**What is the smallest daily workload capacity that allows all jobs to be completed within five days?**

Imagine the jobs have these workload sizes:

`[7, 2, 5, 10, 8]`

You could attempt various possible capacities.

Can the work be scheduled with a daily capacity of 10?

Can it be scheduled with 12?

15?

20?

Here's the interesting property.

If capacity 15 is sufficient, capacity 16 must also be sufficient.

And 17.

And 18.

Increasing the capacity cannot make a previously feasible schedule impossible, assuming the rules remain the same.

That means the answer to:

"Is capacity X sufficient?"

has a **monotonic** structure.

For small capacities, the answer is no.

After some threshold, the answer becomes yes.

Conceptually:

```text
Capacity:  8   9  10  11  12  13  14  15  16 ...
Feasible:  N   N   N   N   Y   Y   Y   Y   Y ...
                          ▲
                          └── first true = binary-search target
```

The numbers here are illustrative.

The important pattern is:

`false, false, false, ..., true, true, true`

We're looking for the first `true`.

Does that remind you of anything?

Exactly.

Binary search.

But this time, we're not searching an array.

We're searching a range of possible answers.

We implement a function:

`canFinishWithCapacity(capacity)`

It determines whether the work can be completed within the allowed number of days.

Then binary search finds the smallest capacity for which the function returns true.

This technique is commonly called **binary search on the answer**.

It's useful because many optimization problems are difficult to solve directly but easy to verify for a proposed threshold.

Examples include:

| Optimization shape | Binary-searchable? |
|---|---|
| Minimum required capacity | if monotonic |
| Maximum feasible load | if monotonic |
| Smallest acceptable resource allocation | if monotonic |
| Minimum speed to meet a deadline | if monotonic |
| Largest value under a monotonic constraint | if monotonic |

The essential skill isn't memorizing the phrase "binary search on the answer."

It's recognizing a monotonic property.

Once you discover that property, an apparently complicated optimization problem may collapse into a sequence of simple yes-or-no checks.

That's one of the pleasures of algorithm design.

Sometimes the clever part isn't the code.

It's identifying the mathematical structure hiding inside the problem.

> **Sticky note #4**
>
> Hard to solve, easy to check? Look for a monotonic threshold.

```text
  ✓ Room 4 complete — binary search on the answer
```

---

# 5. Sorting: The Expensive Operation That Makes Other Operations Cheap

Binary search requires ordered information.

So how do we obtain that order?

We sort.

Sorting is one of the most studied problems in computer science, partly because it appears everywhere and partly because it reveals fundamental ideas about algorithm design.

Consider a collection of reservations:

```typescript
const reservations = [
  { id: "R3", checkIn: "2026-11-09" },
  { id: "R1", checkIn: "2026-11-02" },
  { id: "R4", checkIn: "2026-11-15" },
  { id: "R2", checkIn: "2026-11-02" }
];
```

You need to display them chronologically.

In modern JavaScript, you might write:

```typescript
const sorted = reservations.toSorted(
  (a, b) =>
    a.checkIn.localeCompare(b.checkIn)
);
```

This works for consistently formatted ISO calendar dates such as `YYYY-MM-DD`, because their lexicographic order matches chronological date order.

It creates a new sorted array rather than modifying the original.

Nothing difficult about the code.

But what is the sorting implementation actually doing?

## The naive approach

One simple sorting strategy repeatedly compares neighboring elements and swaps them when they're out of order.

That's essentially bubble sort.

It has a charming simplicity.

Unfortunately, its worst-case time complexity is O(n²).

With large collections, that becomes problematic.

You can find better sorting algorithms by being more strategic.

And a particularly powerful strategy is **divide and conquer**.

```text
  ✓ Room 5 complete — sort pays upfront so search can skip work later
```

---

# 6. Divide and Conquer: Solve Something Smaller, Then Put It Back Together

Imagine you're given a shuffled deck of 1,000 numbered cards.

You need to arrange them in ascending order.

One approach is to repeatedly scan the entire deck, moving cards into position.

Another approach is to split the deck into two piles.

Sort each pile separately.

Then merge the two sorted piles.

If both piles are already sorted, merging them is straightforward.

Look at the first card in each pile.

Take the smaller one.

Repeat until both piles are exhausted.

Now imagine using the same strategy recursively to sort each half.

Split 1,000 cards into two groups of 500.

Split each group into groups of 250.

Continue until every group contains one card.

A single card is already sorted.

Then begin merging.

This is **merge sort**.

And it's a beautiful example of divide and conquer.

## Why does it work?

A merge-sort algorithm consists of three conceptual steps:

```text
  1. DIVIDE    split into smaller parts
  2. CONQUER   sort each part
  3. COMBINE   merge sorted parts → sorted whole
```

The key is that combining two sorted collections is much easier than sorting an arbitrary collection from scratch.

Let's look at a small example.

Original array:

`[8, 3, 6, 2, 7, 1]`

Divide:

`[8, 3, 6]` and `[2, 7, 1]`

Continue dividing until we have single-element collections.

Then merge:

```text
  [8, 3, 6, 2, 7, 1]
         │
    ┌────┴────┐
  [8,3,6]   [2,7,1]
    │         │
   …singles… …singles…
    │         │
  [3,6,8]   [1,2,7]
         │
    [1, 2, 3, 6, 7, 8]
```

`[3] + [8] → [3, 8]`

`[3, 8] + [6] → [3, 6, 8]`

On the other side:

`[2] + [7] → [2, 7]`

`[2, 7] + [1] → [1, 2, 7]`

Finally:

`[3, 6, 8] + [1, 2, 7]`

becomes:

`[1, 2, 3, 6, 7, 8]`

The exact intermediate grouping depends on how odd-sized arrays are split, but the principle remains the same.

## Why O(n log n)?

Let's reason about the work.

At each level of the recursive process, merging all the elements requires O(n) total work.

How many levels are there?

Every division approximately halves the collection.

So the number of levels grows as O(log n).

```text
  Levels ≈ log n
  Work per level ≈ O(n)
  ─────────────────────
  Total ≈ O(n log n)
```

Multiply the work per level by the number of levels:

`O(n) × O(log n) = O(n log n)`

That's the time complexity of merge sort.

It is dramatically better than quadratic sorting for large inputs.

A conventional array-based merge sort also requires O(n) auxiliary storage for merging.

So again, we have a trade-off.

Better time complexity, but additional memory requirements.

## The power of recursion

Merge sort is naturally described recursively.

A recursive function solves a problem by invoking itself on smaller instances.

But recursion needs two things.

First, a **base case**.

Something that tells the process when to stop.

For merge sort, arrays with zero or one element are already sorted.

Second, **progress toward the base case**.

Each recursive call must work on a smaller collection.

Without progress, recursion can continue indefinitely or overflow the call stack.

Consider:

```typescript
function countdown(n: number): void {
  if (n <= 0) return;

  console.log(n);
  countdown(n - 1);
}
```

It's simple, but it contains the essential structure.

A base case.

A smaller recursive problem.

A predictable path toward termination.

Recursion isn't inherently faster than iteration.

Sometimes it's slower, particularly when function-call overhead or stack depth becomes significant.

But it can express naturally recursive problems much more clearly.

Trees, graphs, nested structures, parsers, and divide-and-conquer algorithms often benefit from recursive thinking.

## A caution about JavaScript

JavaScript engines have finite call stacks.

Deep recursion can produce a stack overflow.

For structures that may be extremely deep, iterative algorithms with explicit stacks can be safer.

For merge sort, the recursion depth is logarithmic, so stack depth is generally not the main practical concern.

The broader lesson is that elegant mathematical structure doesn't eliminate runtime constraints.

```text
  ✓ Room 6 complete — divide, conquer, merge (O(n log n))
```

---

# 7. Why Sorting Can't Always Be Faster Than O(n log n)

Here's a surprisingly deep question.

Could we invent a comparison-based sorting algorithm that always sorts arbitrary values in O(n) time?

Imagine a miraculous algorithm that can sort one million arbitrary objects using only a few million comparisons.

Would that be possible?

Under the standard comparison model, no.

There's a mathematical reason.

Suppose we have `n` distinct items.

How many different possible orderings are there?

For two items, there are two.

For three items, six.

For four items, twenty-four.

In general, there are:

`n!`

possible permutations.

That's `n` factorial.

A comparison between two items can distinguish at most two outcomes: one item comes before the other, or it doesn't. For distinct keys, equality doesn't arise.

Think of sorting as a decision process.

The algorithm must distinguish among all possible input orderings.

A sequence of binary decisions forms a decision tree.

A decision tree with height `h` can distinguish at most `2^h` outcomes.

Therefore, to distinguish `n!` possible orderings, we need:

`2^h ≥ n!`

Taking logarithms:

`h ≥ log₂(n!)`

And the growth of `log₂(n!)` is Θ(n log n).

```text
  Information argument (sketch)
  ─────────────────────────────
  n! possible orderings
  each comparison ≤ 1 bit of "which way?"
  need ≥ log₂(n!) ≈ Θ(n log n) comparisons
  in the worst case for comparison sorting
```

So any comparison-based sorting algorithm has a worst-case lower bound of Ω(n log n) comparisons.

This is one of the elegant results of algorithm analysis.

We've established a limit not by examining a particular implementation, but by considering how much information comparisons can reveal.

## So why do linear-time sorting algorithms exist?

Because the lower bound applies to **comparison-based sorting**.

If we know additional properties about the values, other strategies become possible.

Suppose we need to sort one million integers, but every integer lies between 0 and 100.

Instead of comparing pairs of values, we can count how many times each integer occurs.

Then reconstruct the sorted collection.

That's the basic idea behind counting sort.

Its time complexity is O(n + k), where `k` is the range of possible values.

If `k` is small, this can be effectively linear in the number of elements.

Radix sort also exploits the representation of keys rather than relying solely on arbitrary pairwise comparisons.

The crucial distinction is that these algorithms assume something about the data.

They aren't universal replacements for comparison sorting.

They trade generality for the ability to exploit structure.

And that gives us another important algorithmic principle:

> **Sticky note #5**
>
> Additional knowledge about the input can make a problem dramatically easier.

```text
  ✓ Room 7 complete — Ω(n log n) for comparisons; exploit structure to beat it
```

---

# 8. The Temptation of Greedy Algorithms

Let's return to our disastrous European railway planner.

The algorithm selected the cheapest outgoing ticket at every step.

That was a **greedy strategy**.

A greedy algorithm makes a locally attractive choice and commits to it without necessarily reconsidering earlier decisions.

Greedy algorithms are appealing because they can be simple and efficient.

But there's a danger.

A locally optimal choice doesn't automatically lead to a globally optimal result.

Our railway example demonstrated exactly that.

Berlin to Warsaw cost €10, but the onward connection was expensive.

Berlin to Kaunas cost €25, but the remaining journey was cheaper.

Choosing the cheapest first step failed.

Does this mean greedy algorithms are bad?

Not at all.

Some of the most elegant and efficient algorithms are greedy.

The important question is whether the problem has mathematical properties that make greedy choices safe.

## A problem where greed works beautifully

Imagine a conference room that can host one meeting at a time.

You have several meeting requests, each with a start and end time.

You want to schedule the maximum possible number of non-overlapping meetings.

A surprisingly effective strategy is:

**Always choose the available meeting that finishes earliest.**

Then repeat with meetings that start after the chosen one finishes.

Why might that work?

Because choosing the meeting that finishes earliest leaves as much room as possible for future meetings.

```text
  Unweighted interval scheduling (greed works)
  ────────────────────────────────────────────
  Always pick earliest-finishing available meeting

  |----A----|
        |----B----|
  |----------C----------|
               |--D--|

  Pick A (or whoever finishes first among available),
  then next compatible earliest-finisher, …
```

In fact, this strategy is optimal for the classic unweighted interval-scheduling problem.

It can be proven using an *exchange argument*.

The basic reasoning is that if an optimal schedule begins with a meeting that finishes later than the earliest-finishing available meeting, we can replace that first meeting with the earlier-finishing one without reducing the number of meetings that fit afterward.

So there exists an optimal schedule beginning with the greedy choice.

Then we can apply the same logic to the remaining problem.

That's what makes the greedy strategy safe.

Not intuition alone.

A mathematical property of the problem.

## When greed fails

Suppose meetings have different monetary values.

Now the goal is not to schedule the maximum number of meetings.

It's to maximize total revenue.

The earliest-finishing strategy may no longer be optimal.

Perhaps one long meeting earns €1,000, while three short meetings earn only €100 each.

Now we have a different optimization problem.

The same greedy rule can fail.

This is an important habit in algorithm design:

> **Sticky note #6**
>
> When someone proposes a greedy solution, ask what property guarantees that its local choices can be extended into a global optimum.

Without such a property, you may have a plausible heuristic rather than a correct optimal algorithm.

Heuristics can be useful.

But we should know when we're using one.

```text
  ✓ Room 8 complete — greed needs a correctness property
```

---

# 9. Exploring Networks: BFS, DFS, and Dijkstra

Our railway network is a graph.

Cities are vertices.

Connections are edges.

Ticket prices are edge weights.

We want to find a path with minimum total cost.

This is a shortest-path problem in a weighted graph.

But not every graph-search algorithm solves the same version of the problem.

Let's distinguish three important approaches.

## Breadth-first search

Breadth-first search, or BFS, explores nodes in layers.

First, nodes one edge away.

Then two edges away.

Then three.

We studied its basic implementation in CS110-L04.

For an unweighted graph, BFS finds a path with the fewest edges.

But that doesn't necessarily mean the lowest monetary cost.

Our Berlin–Vilnius example includes a direct connection.

BFS would identify it as a one-edge route.

But the direct ticket costs €80.

The route through Kaunas costs €45.

So BFS optimizes the number of connections, not arbitrary edge weights.

The algorithm is correct for the problem it's designed to solve.

It simply isn't solving our cheapest-ticket problem.

## Depth-first search

Depth-first search, or DFS, explores one branch deeply before returning to explore alternatives.

It often uses recursion or an explicit stack.

DFS is useful for:

- Reachability.
- Cycle detection.
- Dependency analysis.
- Exploring connected components.
- Topological ordering in appropriate directed graphs.
- Backtracking through possible solutions.

But ordinary DFS doesn't guarantee the shortest path.

A depth-first traversal may find a valid route quickly while missing a much cheaper alternative elsewhere.

Again, correctness depends on the question.

## Dijkstra's algorithm

Now we arrive at one of the most important algorithms in graph theory.

Dijkstra's algorithm finds shortest-path distances from a starting node in a graph with nonnegative edge weights.

It does something more intelligent than choosing the cheapest immediate outgoing edge.

It maintains the best currently known total cost of reaching each node from the starting point.

Then it repeatedly selects the unsettled node with the smallest tentative total cost.

Let's walk through our hypothetical railway example.

From Berlin, we know:

| Destination | Best known cost |
|---|---:|
| Berlin | €0 |
| Warsaw | €10 |
| Kaunas | €25 |
| Vilnius | €80 |

We first settle Berlin.

Then we choose Warsaw because its tentative total cost, €10, is the smallest.

From Warsaw, the onward connection to Vilnius costs €90.

The total route would cost €100.

But we already know a direct route costing €80.

So we keep €80.

Next, we choose Kaunas, with tentative cost €25.

From Kaunas, the connection to Vilnius costs €20.

Total cost through Kaunas:

`25 + 20 = €45`

That's better than €80.

We update Vilnius's tentative cost to €45.

Eventually, Vilnius is selected with that lowest tentative cost.

We've found the cheapest route in this simplified nonnegative weighted graph.

```text
  Naive greed: pick cheapest *edge* from here
  Dijkstra:    pick smallest *total cost from start*
               among unsettled frontier nodes
```

## What made Dijkstra different?

Our naive algorithm chose the cheapest edge leaving the current city and committed to a route.

Dijkstra considers the cheapest *total tentative cost from the starting city* among all frontier nodes.

That distinction is crucial.

Dijkstra's algorithm is also greedy, but its greedy choice is supported by a correctness property when edge weights are nonnegative.

Once the algorithm settles the currently cheapest reachable node, no path through unsettled nodes can later produce a cheaper route to it using nonnegative edges.

That's why the strategy works.

## Why negative weights matter

Suppose some edges could have negative costs.

A node that appears expensive now might become cheaper later through a negative-weight edge.

Then Dijkstra's key correctness argument no longer holds in general.

Algorithms such as Bellman–Ford address shortest paths with negative edge weights, provided a reachable negative cycle doesn't make the shortest-path cost undefined.

This isn't something you need to implement from memory today.

But it illustrates a broader lesson.

Algorithmic guarantees depend on assumptions.

Ignore the assumptions, and a perfectly implemented algorithm can return incorrect results.

## And real railway timetables are harder

Our fictional graph assumes connections have fixed additive costs.

But real railway journeys also have:

- Departure times.
- Arrival times.
- Minimum connection durations.
- Limited service schedules.
- Tickets whose prices depend on departure and availability.
- Routes that may not operate every day.

If we're minimizing arrival time instead of ticket cost, the model becomes time-dependent.

A connection is useful only if we can actually catch it.

The shortest geographical route may be slow.

The fewest changes may be expensive.

The cheapest route may arrive the next morning.

There's no universal "best route" without defining the objective and constraints.

This connects back to CS110-L01.

Before designing an algorithm, we must understand the actual problem.

| Algorithm | Optimizes… | Needs… |
|---|---|---|
| BFS | fewest edges (hops) | unweighted (or equal weights) |
| DFS | exploration / structure | not shortest-path by itself |
| Dijkstra | total nonnegative cost | nonnegative edge weights |
| Real planner | whatever you defined | schedules, constraints, objective |

```text
  ✓ Room 9 complete — match the search to the objective
```

---

# 10. Reusing Answers: The First Taste of Dynamic Programming

Let's introduce one more important idea.

Imagine calculating the cheapest route through a large network.

A naive recursive algorithm might explore every possible route.

At each city, it considers every outgoing connection and recursively calculates the best possible continuation.

For a small acyclic network, that's straightforward.

But suppose different routes eventually reach the same city.

Then the recursive process might calculate the best remaining route from that city again and again.

That's wasted work.

Imagine arriving at Kaunas through several possible earlier routes.

Once we know the cheapest continuation from Kaunas to Vilnius, why recompute it every time?

We could remember the result.

This is called **memoization**.

A memoized function caches the result of a computation so that the same subproblem doesn't need to be solved repeatedly.

For suitable problems, memoization can transform an exponentially expensive recursive approach into a much more efficient one.

The larger family of techniques built around solving and reusing overlapping subproblems is called **dynamic programming**.

Despite its intimidating name, the central idea is often simple:

> **Sticky note #7**
>
> Solve smaller problems, store their answers, and reuse those answers when larger problems depend on them.

## An elementary example

Consider the Fibonacci sequence:

`0, 1, 1, 2, 3, 5, 8, 13...`

Each value is the sum of the previous two.

A naive recursive implementation might be:

```typescript
function fibonacci(n: number): number {
  if (n < 2) return n;

  return fibonacci(n - 1) +
         fibonacci(n - 2);
}
```

The code is beautiful.

But the execution is wasteful.

```text
  fib(5)
   ├─ fib(4)
   │   ├─ fib(3)
   │   │   ├─ fib(2) …
   │   │   └─ fib(1)
   │   └─ fib(2) …          ← same subtree, computed again
   └─ fib(3) …              ← and again
```

To calculate `fibonacci(40)`, it repeatedly recalculates many of the same smaller Fibonacci values.

A memoized version remembers them:

```typescript
const memo = new Map<number, number>();

function fibonacci(n: number): number {
  if (n < 2) return n;

  const cached = memo.get(n);

  if (cached !== undefined) {
    return cached;
  }

  const result =
    fibonacci(n - 1) +
    fibonacci(n - 2);

  memo.set(n, result);

  return result;
}
```

Now each distinct Fibonacci value up to `n` is calculated at most once.

Time complexity becomes O(n), rather than exponential for the naive recursive implementation.

We spend O(n) memory to save enormous amounts of repeated computation.

An iterative implementation can do even better in auxiliary memory, keeping only the most recent two values.

But the conceptual lesson is about recognizing repeated subproblems.

## When dynamic programming is useful

It appears in problems involving:

- Optimal scheduling.
- Resource allocation.
- Sequence comparison.
- Route optimization under certain constraints.
- Text processing.
- Planning and decision problems.
- Various combinatorial optimizations.

It isn't the answer to everything.

Some problems lack the necessary overlapping subproblem structure.

Others require more specialized algorithms.

But the ability to recognize repeated work is extremely valuable.

And you'll notice that this principle already appears in professional backend engineering.

| DP-ish engineering habit | Same intuition |
|---|---|
| Caching calculated results | don't recompute |
| Incremental aggregates | reuse previous state |
| Compiled templates | pay once |
| Avoiding repeated DB queries | overlapping work is expensive |

These aren't necessarily textbook dynamic programming, but they exploit a related engineering intuition:

Don't repeatedly perform expensive work when a valid reusable result already exists.

The challenge, of course, is knowing when the result remains valid.

And that's where state, caching, and consistency enter the picture.

```text
  ✓ Room 10 complete — remember answers to overlapping subproblems
```

---

# 11. The Six Algorithmic Patterns Worth Recognizing

We've covered quite a few ideas.

Let's organize them into a mental toolkit.

You don't need to memorize fifty algorithms.

For most full-stack engineering work and a substantial share of coding interviews, recognizing a few recurring patterns is much more valuable.

| Pattern | Core idea | Typical use |
|---|---|---|
| **Hash-based lookup** | Organize keys for fast expected membership checks | Deduplication, joins, caches, matching |
| **Sorting + binary search** | Establish order, then eliminate large ranges | Date ranges, thresholds, indexed lookups |
| **Two pointers / sliding window** | Maintain a moving region without rescanning everything | Sequences, substrings, bounded windows |
| **Divide and conquer** | Split a problem, solve smaller pieces, combine | Sorting, searching, recursive structures |
| **Greedy selection** | Make a locally optimal choice when correctness conditions permit | Scheduling, some graph algorithms |
| **Graph search / dynamic programming** | Explore relationships or reuse subproblem results | Routing, dependencies, planning, optimization |

Let's spend a moment on one pattern we haven't yet discussed.

## Sliding windows

Imagine an array of hourly API request counts.

You want the maximum total number of requests observed across any consecutive 24-hour window.

A naive implementation might calculate the sum of every 24-element window independently.

But neighboring windows overlap almost completely.

When the window moves forward by one hour:

- One old hour leaves the window.
- One new hour enters.

```text
  Hours:  [h0 h1 h2 … h23] h24 h25 …
           └──── window ────┘
                └──── window ────┘

  newSum = oldSum - outgoing + incoming
```

Why recalculate the entire sum?

We can update it incrementally:

`newSum = oldSum - outgoingValue + incomingValue`

That's a sliding window.

The technique turns many repeated calculations into constant-time updates.

For a fixed window size, the whole array can be processed in O(n) time.

And the general concept applies beyond arrays.

Moving averages.

Rate limiting.

Recent-event statistics.

Rolling metrics.

Streaming analytics.

The broader principle is that neighboring solutions often share most of their information.

Recognizing that overlap allows us to reuse previous work.

```text
  ✓ Room 11 complete — six patterns on the pocket card
```

---

# 12. When the Elegant Algorithm Loses to the Boring One

There's one last trap worth investigating before the exercises.

Suppose you're asked to find whether a target exists in a collection.

You have two approaches.

**Approach A:** Sort the collection, then use binary search.

**Approach B:** Scan the collection linearly.

Binary search is O(log n).

Linear search is O(n).

So A must be faster, right?

Not necessarily.

Because Approach A has an upfront sorting cost.

For a collection of `n` elements:

- Sorting generally costs O(n log n).
- Binary search costs O(log n).

If you're performing only one lookup, sorting first is usually unnecessary.

The entire approach costs O(n log n), compared with O(n) for a simple scan.

But what if you'll perform one hundred thousand lookups against the same collection?

Now the sorting cost can be amortized across many searches.

We pay once to organize the data.

Then every lookup benefits.

```text
  One lookup:     scan O(n)  beats  sort+search O(n log n)
  Many lookups:   pay once to organize → each search is cheap
```

This is a recurring architectural question:

> **Sticky note #8**
>
> Is it worth spending resources upfront to make future operations cheaper?

That's what database indexes do.

That's what caches do.

That's what precomputed search structures do.

And it's why workload patterns matter so much.

An algorithm cannot be judged without knowing how it will be used.

## A note about JavaScript sorting

One small but useful runtime detail.

JavaScript's default `sort()` behavior converts elements to strings and compares them according to string ordering.

For example:

```typescript
[1, 10, 2].sort();
// [1, 10, 2]
```

That's usually not what you want for numerical sorting.

Use a comparator:

```typescript
[1, 10, 2].sort((a, b) => a - b);
// [1, 2, 10]
```

Also remember that `sort()` mutates the original array.

The newer `toSorted()` method produces a new array.

Modern ECMAScript specifies stable sorting, meaning elements that compare equal retain their original relative order.

But stability, mutation, and comparison semantics are separate concerns.

A senior TypeScript developer should understand these behaviors even if they don't know which sorting algorithm a particular JavaScript engine uses internally.

```text
  ✓ Room 12 complete — elegant ≠ always faster for your workload
```

---

# 13. Practical Lab: Let's Make the Computer Do Less Work

Now for a little experimentation.

These exercises are deliberately small.

The goal is to observe algorithmic behavior, not build another application.

**Suggested time: 15–20 minutes.**

> **Gym rules:** predict before you run. Spoilers live in Room 15 for the challenges; these labs are for your own eyes.

## Experiment A — Binary search with duplicates

Start with:

```typescript
const values = [
  1, 3, 3, 3, 5, 8, 8, 12
];
```

Implement the `lowerBound` function from earlier.

Predict the result for these targets:

```typescript
lowerBound(values, 3);
lowerBound(values, 4);
lowerBound(values, 8);
lowerBound(values, 13);
```

Now think about this:

How would you find the first index containing a value strictly greater than the target?

How would you count the number of occurrences of a target without scanning the entire matching range?

Hint: two boundary searches are enough.

## Experiment B — Sorting isn't free

Create an array of 100,000 random integers.

Measure the time required to:

1. Search the unsorted array for a value.
2. Sort the array.
3. Search the sorted array using binary search.

Repeat the lookup many times.

At approximately what number of lookups does the initial sorting cost begin to pay for itself?

Don't expect a universal answer.

The result depends on the JavaScript engine, hardware, data distribution, and exact implementation.

That's part of the lesson.

## Experiment C — The cheapest next ticket

Represent our hypothetical railway network as a graph.

Try implementing the naive greedy algorithm that selects the cheapest outgoing edge at each step.

Use the example from the opening.

Observe its failure.

Now implement a small exhaustive search that enumerates all simple paths in this tiny graph.

Compare the cheapest complete route with the greedy route.

You don't need to implement Dijkstra yet.

The purpose is to see the difference between local decisions and globally evaluated solutions.

## Experiment D — Repeated work

Run the naive recursive Fibonacci function for increasing values of `n`.

Try values such as 20, 30, and 35.

Measure the execution time.

Then run the memoized version.

Observe how the growth changes.

Avoid pushing naive recursion to unnecessarily large values.

Its execution time grows rapidly.

```text
  ✓ Room 13 complete — lab done (or at least attempted)
```

---

# 14. Four Interview-Style Challenges

These exercises are intended to make you think before writing code.

## Challenge A — The Reservation Search

**Suggested time: 8 minutes**

Your application stores 500,000 reservations in memory.

They're sorted by check-in date.

You need to retrieve all reservations whose check-in date falls between November 10 and November 15.

You can assume dates use a consistent sortable representation.

Questions:

1. Would you scan the entire array?
2. How could binary search improve the operation?
3. What happens if there are 10,000 matching reservations?
4. Does O(log n) search mean the entire query can return 10,000 results in O(log n)?
5. What happens to performance if reservations are frequently inserted into this sorted array?

## Challenge B — The Interviewer's Trap

**Suggested time: 8 minutes**

You're given an unsorted array of one million integers.

You need to answer whether a particular value exists.

An interviewer says:

"Binary search is faster than linear search, so why don't you sort the array first?"

How would you respond?

Now suppose the same array will receive 200,000 membership queries.

Does your answer change?

Would you prefer sorting or building a hash-based Set?

What factors would influence your choice?

## Challenge C — The Scheduling Problem

**Suggested time: 10 minutes**

You have a collection of meeting requests.

Each meeting has a start time, end time, and revenue.

You want to maximize revenue without scheduling overlapping meetings.

A colleague proposes:

"Always select the meeting that finishes earliest."

Is this guaranteed to produce the maximum revenue?

If not, construct a counterexample.

How might remembering the best solution to smaller scheduling subproblems help?

You don't need to implement the full algorithm.

Focus on understanding why a greedy strategy may fail and how dynamic programming could become relevant.

## Challenge D — Graph Search in Production

**Suggested time: 10 minutes**

You're implementing dependency resolution for a build system.

Project A depends on B and C.

B depends on D.

C also depends on D.

Questions:

1. How would you represent these relationships?
2. How would you ensure D is built only once?
3. What happens if A depends on B and B depends on A?
4. Would BFS or DFS help detect a dependency cycle?
5. Why is a simple visited Set insufficient by itself for detecting every directed cycle correctly?

The final question is particularly important.

It introduces the distinction between nodes that have been completely processed and nodes that are still active in the current traversal.

```text
  ✓ Room 14 complete — challenges attempted
```

---

# 15. Solutions and Discussion

*Read this section after attempting the exercises.*

## Challenge A — Reservation ranges

Because the array is sorted, binary search can find the beginning of the requested date range.

A second boundary search can locate the end.

The two searches require O(log n) comparisons each.

But retrieving the matching records still requires O(k) work, where `k` is the number of matching reservations.

So the total is:

**O(log n + k)**

This is an important complexity pattern for range queries.

You can't return 10,000 records without performing work proportional to the output size.

Frequent insertion into a sorted array may be expensive because maintaining order can require shifting elements.

For a heavily updated production dataset, an ordered index or database-backed structure may be preferable.

## Challenge B — Sorting versus searching

For one lookup, sorting first is generally wasteful.

A linear scan costs O(n).

Sorting and then binary searching costs O(n log n) overall.

For many repeated lookups, preprocessing can be worthwhile.

A hash-based Set provides expected O(n) construction and expected O(1) membership checks, making it attractive for repeated exact membership queries.

Sorting may be preferable when ordered traversal or range searches are also needed, or when memory constraints and data characteristics favor that approach.

The correct choice depends on the workload.

## Challenge C — Weighted scheduling

Selecting the earliest-finishing meeting maximizes the number of compatible meetings in the classic unweighted problem.

But it doesn't necessarily maximize revenue.

Imagine these requests:

- Meeting A: 09:00–10:00, revenue €10.
- Meeting B: 10:00–11:00, revenue €10.
- Meeting C: 09:00–11:00, revenue €100.

The earliest-finishing strategy could select A and B, earning €20.

But selecting C earns €100.

A dynamic-programming solution can consider whether to include each meeting and reuse optimal results for compatible earlier or later subproblems.

This is the classic weighted interval-scheduling problem.

## Challenge D — Dependency graphs

Represent the projects as a directed graph.

An edge from A to B means A depends on B.

A build system can use graph traversal to identify dependencies and avoid rebuilding the same project unnecessarily.

But cycles require special attention.

Suppose A depends on B and B depends on A.

Neither can be built first under those dependency rules.

A common DFS-based cycle-detection method tracks three conceptual states:

- Unvisited.
- Currently being explored.
- Completely processed.

If traversal encounters a node that is already active in the current recursion path, it has discovered a directed cycle.

A simple visited Set isn't sufficient by itself because revisiting a completely processed node can be perfectly legitimate.

For example, both B and C may depend on D.

Encountering D through two different branches doesn't necessarily indicate a cycle.

This is why graph algorithms often need more precise state than merely "seen" versus "unseen."

```text
  ✓ Room 15 complete — answers checked
```

---

# 16. The Bigger Picture

Exploit structure — sorted data, graphs, monotonic predicates — so you search less blindly.

Separate local choices from global objectives. The cheapest next railway ticket need not yield the cheapest journey; greedy needs a correctness argument.

Divide problems with merge sort and recursion, with correct base cases and progress. Don't repeat work: memoization, DP, sliding windows, indexes, caches.

Match the algorithm to the objective: BFS for unweighted hop count, Dijkstra for nonnegative costs, a real planner for schedules and prices. Workload matters. Correctness is not optional.

Berlin to Vilnius began with a reasonable greedy algorithm — fast, simple, terrible. The fix wasn't faster code. It was better problem structure: local versus global, a graph of cities and connections, a defined cost, and an algorithm whose correctness matched those assumptions.

```text
  POCKET CARD — CS110-L05
  ═══════════════════════════════════════════════════════════
  1. Local optimum ≠ global optimum
  2. Binary search eliminates half — needs order / monotonicity
  3. Maintain an invariant; boundaries are the bugs
  4. Sort pays so later ops can skip work
  5. D&C / merge: O(n log n); comparisons can't beat Ω(n log n)
  6. Greedy needs a proof; Dijkstra ≠ "cheapest next edge"
  7. Memoize overlapping subproblems; sliding windows reuse sums
  8. Workload decides: one lookup ≠ a hundred thousand
  ═══════════════════════════════════════════════════════════
```

> **The master sticky note**
>
> A good algorithm doesn't simply search faster. It uses knowledge about the problem to avoid searching where the answer cannot be.

That is why binary search, sorting, and graph algorithms remain valuable even when an assistant can generate the code. Someone still has to recognize which problem to solve, which assumptions hold, and which result is correct.

```text
  ✓ All rooms visited. Tickets cheaper. See you in CS220-L01.
```

---


---

## End of CS110

**CS110 — Foundations of Computation and Algorithms** is complete. See the recommended study order in `README.md` for natural next courses.

