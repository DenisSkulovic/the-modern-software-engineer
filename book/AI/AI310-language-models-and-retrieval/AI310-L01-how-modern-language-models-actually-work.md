---
id: AI310-L01
course: AI310
title: "How Modern Language Models Actually Work"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [AI501-S01]
prev: null
next: AI310-L02
---



# AI310 — Language Models and Retrieval Engineering
## Lecture 01: How Modern Language Models Actually Work

### The Machine That Can Explain Its Own Mistakes—and Still Make Them

Imagine interviewing a software engineer with an extraordinary résumé.

They can explain PostgreSQL transaction isolation, write sophisticated TypeScript, discuss distributed consensus, translate between twenty languages, and analyze architectural decisions with surprising maturity. You ask them to investigate a race condition involving two concurrent hotel reservations, and they produce an excellent explanation, including the relevant SQL queries and a plausible fix.

Then you ask a simpler question: *Which Node.js API provides this particular capability?*

They confidently recommend a function that doesn't exist.

You challenge them. They apologize, explain why their earlier answer was incorrect, and confidently recommend another nonexistent function.

Something peculiar is happening.

The same computational system demonstrates considerable problem-solving ability and occasionally fails at tasks that should require little more than looking something up. It can generate a convincing mathematical proof containing a subtle logical error, then correctly explain that error when someone points it out.

This is not adequately explained by calling the system stupid, intelligent, or merely autocomplete. Those labels describe impressions, not mechanisms.

To understand what is happening, we need to follow a modern language model from its training objective to the moment it generates a single token.

Along the way, we'll encounter an architecture originally developed for machine translation, a surprisingly simple mathematical operation called attention, enormous collections of learned numerical parameters, and an important distinction between *producing an answer* and *establishing that the answer is true*.

By the end of this session, the apparent contradiction should look considerably less mysterious.

---

## 1. What Is a Language Model Actually Modeling?

Consider the following incomplete sentence:

> The database transaction was rolled back because the connection...

Several continuations are plausible:

- "...was lost."
- "...timed out."
- "...failed during commit."
- "...encountered an unexpected error."

The words preceding the continuation constrain what comes next. A language model attempts to represent those constraints mathematically.

More formally, an autoregressive language model estimates a conditional probability distribution:

**P(next token | preceding tokens)**

This distribution assigns a probability to every possible next token in the model's vocabulary.

Importantly, it does not return a single correct continuation. It represents many possibilities, with different probabilities depending on the preceding context.

A sequence containing tokens x₁, x₂, ..., xₙ can be assigned a probability through the chain rule:

**P(x₁, ..., xₙ) = P(x₁) × P(x₂ | x₁) × ... × P(xₙ | x₁, ..., xₙ₋₁)**

The remarkable implication is that predicting the next element of a sequence can become a general-purpose learning objective.

Why?

Because predicting language well requires modeling the structures that produce language.

To complete an ordinary sentence, the model needs some knowledge of grammar and vocabulary. To complete a legal argument, it needs representations of legal terminology and argumentative structure. To predict code, it benefits from learning programming syntax, data flow, API conventions, and patterns of correct implementation.

Suppose a training document contains:

> A transaction operating under snapshot isolation may still permit write skew when...

A model that has learned only English grammar won't predict the continuation particularly well. A model that has developed useful representations of database concurrency will perform better.

**The training objective rewards learning whatever statistical structure improves prediction—even when that structure resembles knowledge, abstraction, or reasoning.**

This is why "it's just predicting the next token" is simultaneously correct and misleading.

The phrase correctly describes a fundamental training and generation mechanism. It does not establish that the learned computation must be trivial.

A chess engine ultimately calculates numerical evaluations and selects moves. Describing it as "just arithmetic" is technically compatible with what it does, but a rather spectacular failure to explain its capabilities.

Language models deserve the same distinction between computational mechanism and emergent behavior.

### Statistical prediction is not a database lookup

A conventional information-retrieval system might locate an existing paragraph explaining snapshot isolation and return it.

A language model instead computes a new representation of the supplied context and generates a continuation using its learned parameters.

Sometimes that continuation closely resembles memorized training material. Sometimes it recombines familiar concepts. Sometimes it generalizes to combinations that were unlikely to have appeared verbatim in training.

Those behaviors are not mutually exclusive.

This immediately introduces a limitation: **the model has learned to produce plausible sequences, but plausibility is not identical to factual truth.**

We will return to that distinction once we understand the underlying machinery.

---

## 2. Tokenization: The Model Doesn't Read Words

Before a transformer processes text, the text must become numerical input.

A language model does not receive an English sentence as a semantic object. It receives a sequence of integer identifiers corresponding to units called *tokens*.

A token might represent:

- An entire common word.
- Part of a word.
- A punctuation symbol.
- Whitespace combined with text.
- A fragment of code.
- A sequence of bytes representing unusual characters.

For illustration, a tokenizer might divide:

`unbelievable`

into something resembling:

`un` + `believ` + `able`

That is not a claim about the exact segmentation used by any particular model. Different tokenizers have different vocabularies and produce different sequences.

### Why not simply tokenize by words?

A word-level vocabulary creates awkward problems.

English contains an enormous number of possible words, including technical identifiers, misspellings, compound words, names, and terms invented five minutes ago. Programming languages make the problem worse: developers can invent practically unlimited function and variable names.

A character-level vocabulary avoids that problem, but sequences become much longer.

Subword tokenization provides a useful compromise.

One widely used approach is **byte-pair encoding (BPE)**. Starting from relatively small units, the tokenizer-building process repeatedly merges frequently occurring adjacent sequences, creating larger vocabulary entries for common patterns.

The resulting vocabulary might contain a dedicated token for a frequent word and smaller pieces for an unusual identifier.

Byte-level approaches can also represent arbitrary text without requiring every possible word to appear in the vocabulary.

### Why engineers should care

Tokenization influences three things directly.

**First, context consumption.** Two strings with similar character lengths may use substantially different numbers of tokens. Natural-language text, source code, Unicode-heavy content, and unusual identifiers need not tokenize equally efficiently.

**Second, cost and computation.** Model services commonly measure usage in tokens, and the length of a token sequence affects computational requirements.

**Third, model behavior.** Some tasks become awkward because the token boundaries do not align with the structures humans naturally perceive.

Ask a person to count the letters in a word, and they can inspect its characters. A language model operates initially on token representations, which might not correspond to individual characters.

It can nevertheless learn to reason about spelling, reconstruct character-level information, or use suitable computational strategies. The important point is that those operations are not automatically provided by the tokenizer.

A token is simply the unit through which textual information enters and leaves the model.

It is not necessarily a word, concept, or grammatical entity.

---

## 3. Embeddings: Turning Symbols into Useful Geometry

After tokenization, we have integers.

Suppose our input becomes:

`[1847, 392, 10531, 271, ...]`

Those numbers identify vocabulary entries. Their numerical magnitudes carry no inherent semantic meaning.

Token 1847 isn't necessarily more sophisticated than token 392.

To perform useful computation, the model maps each token ID to a learned numerical vector called an **embedding**.

For example, a token might be represented by a vector with thousands of components:

`[0.12, -0.47, 0.83, 0.06, ...]`

These values are not hand-designed features. They are learned during training.

### How can numbers represent meaning?

Imagine representing software concepts in a fictional three-dimensional space.

One direction might approximately reflect whether something concerns storage, another whether it concerns concurrency, and another whether it concerns networking.

Under that representation, "PostgreSQL" and "MySQL" might occupy relatively nearby regions, while "PostgreSQL" and "giraffe" would likely be farther apart.

Real embeddings are vastly higher-dimensional, and their individual dimensions generally cannot be assigned such neat human-readable labels.

Meaning is distributed across many coordinates and interactions.

During training, useful geometric relationships arise because related tokens participate in related prediction problems.

This is one reason neural representations can support generalization. The model need not learn an entirely independent response for every possible string; it can reuse distributed patterns learned across many examples.

### The word "bank" problem

Consider:

> She deposited her salary at the bank.

And:

> The children sat on the river bank.

A single static representation for "bank" cannot fully express both meanings.

Transformers address this by constructing **contextual representations**.

The initial token embedding provides a starting representation. As information passes through successive transformer layers, the representation changes in response to the surrounding tokens.

Consequently, the final representation of "bank" in the financial sentence can differ substantially from its representation in the geographical sentence.

This distinction matters enormously.

An embedding table is not a dictionary containing the final meaning of every word. It provides initial vectors from which the network constructs context-sensitive representations.

We now need to understand how surrounding tokens influence one another.

That brings us to the transformer.

---

## 4. The Transformer: How Tokens Exchange Information

The transformer architecture was introduced in the 2017 paper *Attention Is All You Need*.

Earlier neural sequence models frequently relied on recurrent computations, processing tokens through successive time steps. Transformers introduced an architecture centered on attention mechanisms that allowed much more parallel processing during training.

The original transformer combined an encoder and decoder for sequence-to-sequence tasks such as translation. Many influential generative language models use a **decoder-only transformer** architecture, though modern models also incorporate numerous variations and optimizations.

For our purposes, consider a conventional decoder-style language model.

Its simplified structure is:

```text
Input text
    |
Tokenization
    |
Token embeddings + position information
    |
Transformer block 1
    |
Transformer block 2
    |
        ...
    |
Transformer block N
    |
Output projection
    |
Next-token logits
```

A transformer block typically contains attention computations, feed-forward transformations, normalization, and residual connections.

Let's examine those mechanisms.

### 4.1 Self-attention: Selecting relevant information

Consider:

> The trophy would not fit inside the suitcase because it was too big.

What does "it" refer to?

Probably the trophy.

Now modify the sentence:

> The trophy would not fit inside the suitcase because it was too small.

The likely referent changes to the suitcase.

The relevant words are not adjacent to the pronoun. Resolving the meaning requires connecting information across the sentence.

Self-attention gives the model a computational mechanism for mixing information from different token positions.

At each transformer layer, token representations are projected into three types of vectors:

- **Query (Q):** what information this position is seeking.
- **Key (K):** a representation used to determine how relevant another position is.
- **Value (V):** the information contributed by that position.

These descriptions are functional intuitions. Queries and keys are learned numerical projections, not literal questions and answers.

For a particular token position, the attention operation compares its query vector with the key vectors of positions it is permitted to attend to.

A common similarity computation is a dot product.

Larger scores indicate stronger alignment between the query and key under the learned projection.

Those scores are scaled and passed through a softmax operation to produce normalized attention weights.

The central formula is:

**Attention(Q, K, V) = softmax(QKᵀ / √dₖ) V**

Where:

- Q contains query vectors.
- K contains key vectors.
- V contains value vectors.
- dₖ is the dimensionality of the keys.
- Softmax converts scores into weights summing to one across the eligible positions.

The output is a weighted combination of value vectors.

### 4.2 A small numerical example

Suppose the model is processing a token whose attention head considers three earlier positions.

Its calculated compatibility scores are:

| Position | Score |
|---|---:|
| "trophy" | 3.0 |
| "suitcase" | 1.0 |
| "because" | 0.0 |

For this simplified example, ignore the dimensional scaling because we are treating the numbers as already scaled scores.

Applying softmax produces approximately:

| Position | Attention weight |
|---|---:|
| "trophy" | 0.844 |
| "suitcase" | 0.114 |
| "because" | 0.042 |

The attention output is formed by multiplying each position's value vector by its weight and summing the results.

Notice what attention actually accomplishes: it constructs a new representation using information selected from other positions.

It does not literally retrieve a fact from a database, prove the correct interpretation, or independently understand grammatical references.

Nor should we assume that a single attention head reliably corresponds to one human-interpretable linguistic task. Actual heads and layers may encode distributed, overlapping, and difficult-to-interpret patterns.

Nevertheless, this operation gives the network a powerful way to combine distant contextual information.

### 4.3 Multi-head attention

A single attention calculation is relatively limited.

Different relationships may matter simultaneously: syntactic structure, entity references, nearby formatting, distant dependencies, and domain-specific patterns.

Transformers therefore commonly employ **multiple attention heads**.

Each head uses learned projections and computes its own attention patterns. Their outputs are combined and projected back into the model's representation space.

The important advantage isn't that one head becomes "the grammar expert" while another becomes "the mathematics expert."

It's that the layer can compute multiple different information-mixing patterns in parallel.

### 4.4 Causal masking: Preventing the model from seeing the future

There is an essential constraint for autoregressive language modeling.

When predicting token 17, the model must not use token 18.

Otherwise, training would become an absurdly easy examination in which the student can read tomorrow's answer sheet.

A decoder-style language model therefore uses **causal attention masking**.

At any position, attention is restricted to that position and eligible earlier positions.

Conceptually:

```text
            Can attend to
          1   2   3   4

Token 1   ✓   ·   ·   ·
Token 2   ✓   ✓   ·   ·
Token 3   ✓   ✓   ✓   ·
Token 4   ✓   ✓   ✓   ✓
```

During training, the model can process an entire sequence in parallel while respecting these dependencies. Each position learns to predict the next token using only the permitted prefix.

During generation, it produces new tokens sequentially because the next token depends on the previously generated ones.

That distinction explains an important part of inference performance, which we will examine shortly.

### 4.5 Attention isn't the entire transformer

It is tempting to think that transformers are simply enormous attention engines.

But attention primarily mixes information across positions. Transformer blocks also contain **feed-forward neural networks**, commonly applied independently to the representation at each position.

These transformations allow the network to perform additional nonlinear computation on the information assembled by attention.

We can think of the two mechanisms as complementary:

**Attention:** Which information from other positions should influence this representation?

**Feed-forward computation:** How should the resulting information be transformed?

Across many layers, the model alternates between combining contextual information and transforming its representations.

Residual connections preserve pathways through the network by adding a block's computed changes to an existing representation. Normalization mechanisms help maintain manageable activation behavior and improve training stability.

Position information is also necessary. Without positional information, attention alone would have difficulty representing the distinction between differently ordered sequences containing the same tokens.

Different transformer designs introduce position through learned embeddings, relative-position mechanisms, rotary position embeddings, or other techniques.

### 4.6 Why stack so many layers?

A single attention layer can combine information, but complicated problems may require several stages of computation.

Consider analyzing:

> The customer canceled the reservation after the hotel confirmed that the payment was refundable.

Useful interpretation may require identifying the customer, reservation, cancellation event, hotel confirmation, and conditions governing the refund.

Successive layers allow increasingly sophisticated transformations of the representation, although we should not imagine that every layer corresponds neatly to a particular human reasoning step.

At the end of the stack, the model has a contextual representation from which it can calculate scores for possible next tokens.

The same general computational machinery supports natural language, programming syntax, structured formats, and many forms of learned reasoning.

There is no separate SQL engine or English grammar parser hidden inside the transformer merely because it can produce SQL and grammatically correct English.

Its capabilities emerge from learned numerical computation.

---

## 5. Training: How a Model Acquires Its Parameters

We have described the architecture, but initially its numerical parameters are not useful.

The embedding vectors, attention projections, feed-forward weights, and other learned components must be adjusted through training.

A large language model can contain billions of parameters or more, depending on its architecture. These parameters collectively determine the network's behavior.

### 5.1 Pretraining through prediction errors

Imagine feeding the model the following sequence:

> The capital of Lithuania is Vilnius.

During causal language-model pretraining, the sequence provides many prediction tasks.

The model attempts to predict each next token from its preceding context.

Suppose that after reading "The capital of Lithuania is", the model assigns:

- Vilnius: 0.08
- Kaunas: 0.12
- Riga: 0.10
- Other possibilities: remaining probability

The correct next token receives relatively low probability.

Training uses a loss function to quantify this mistake.

A standard language-model loss is **cross-entropy**, with the per-token contribution:

**Loss = −log P(correct token | context)**

A prediction assigning the correct token high probability receives a smaller loss.

The training algorithm computes how the model's parameters contributed to the loss and uses **backpropagation** to calculate gradients. An optimizer then updates the parameters in directions intended to improve predictions.

This occurs across enormous numbers of training examples.

Over time, the model learns representations that reduce prediction errors across the training distribution.

### 5.2 Why not memorize everything?

A sufficiently large model can memorize some training sequences, and memorization is a genuine concern.

But exact memorization alone is a poor general solution.

The number of possible sentences, code programs, and contextual combinations is astronomical. A model that learns reusable structure can improve predictions across many situations without needing to remember every sequence verbatim.

Learning that SQL transactions involve concurrency constraints is more generalizable than storing a million independent sentences containing the word "transaction."

In practice, learned behavior mixes pattern extraction, abstraction, generalization, and memorization.

We should not make the opposite mistake of assuming that because a model can generalize, it has a perfectly organized internal representation of the world.

Its knowledge is encoded implicitly in distributed parameter relationships, not as a clean collection of guaranteed factual records.

### 5.3 Training is computationally expensive

Each training step involves forward computation, calculation of prediction losses, backpropagation, and parameter updates.

Large models require substantial accelerator resources, distributed training techniques, and careful numerical engineering.

Specialized GPUs and other accelerators are useful because much of this workload involves dense numerical operations that can be parallelized.

The training process also has practical constraints: memory capacity, communication overhead, numerical precision, data quality, optimization stability, and available compute.

These are not incidental implementation details. They strongly influence which architectures and training strategies are feasible.

### 5.4 Pretraining is not enough to create a helpful assistant

A model trained primarily to predict internet documents may become excellent at continuing documents.

But continuing documents is different from obeying user instructions.

Ask such a model a question and it might complete the text as though it were writing an FAQ, a fictional dialogue, or an argumentative essay.

This motivates **post-training**.

A common approach is supervised fine-tuning on examples of desirable responses, followed in some systems by preference optimization or reinforcement learning based on human or automated feedback.

The purpose is to shape which behaviors the model produces: following instructions, using requested formats, refusing certain requests, expressing uncertainty appropriately, or solving tasks more effectively.

Pretraining develops broad representations and capabilities. Post-training can substantially alter how those capabilities are elicited and expressed, and can also improve performance on targeted tasks.

The exact procedures vary significantly across model families and providers.

### 5.5 Reasoning-oriented training

Some modern systems are additionally trained to improve performance on difficult problems involving multiple computational steps.

Training can reward successful mathematical solutions, correct code, effective verification, or other measurable outcomes, sometimes encouraging useful intermediate reasoning behavior.

Extra computation at inference time can also improve performance on difficult problems, although more generated reasoning does not guarantee correctness.

The important distinction is between the underlying model computation and the visible—or sometimes internal—process through which a system works on a problem.

A reasoning-capable model remains a learned computational system. Its reasoning behavior may be valuable, but we should evaluate whether it produces correct results rather than assuming that elaborate reasoning text is itself proof.

---

## 6. Inference: What Happens When You Send a Message?

Training modifies the model's parameters.

**Inference uses the trained parameters to compute outputs.**

For a conventional model, answering your question doesn't mean retraining on it. The model processes your supplied context through its existing network.

Let's follow the lifecycle.

### Stage 1: Construct and tokenize the input

The actual input may contain system instructions, user messages, conversation history, formatting markers, and other contextual material.

The tokenizer converts this content into token IDs.

Those IDs become vectors through the embedding mechanism, and the network processes them through its transformer layers.

### Stage 2: Prefill

The model processes the provided input context and computes the internal representations necessary to begin generation.

This initial phase is commonly called **prefill**.

Because the prompt tokens are already known, substantial computation can be parallelized across positions, subject to the causal mask.

For a large context, prefill may be computationally expensive.

### Stage 3: Produce next-token scores

The final representation at the current position is projected into scores associated with the model's output vocabulary.

These scores are called **logits**.

The logits can be converted into probabilities using softmax.

Suppose the prompt ends with:

> The SQL transaction was

Possible continuations might include tokens corresponding to "committed", "rolled", "aborted", and many others.

The model calculates a distribution over those possibilities.

### Stage 4: Select a token

A decoding strategy selects one token.

That token becomes part of the generated output and therefore part of the context for selecting subsequent tokens.

The process repeats:

```text
Prompt
  |
Predict token A
  |
Prompt + A
  |
Predict token B
  |
Prompt + A + B
  |
Predict token C
  |
...
```

Generation continues until a stopping condition is reached, such as an end-of-message token or an output-length limit.

This is called **autoregressive generation**.

### 6.1 Why KV caching matters

A naïve implementation would recompute the entire context through the network after generating every token.

That would waste an enormous amount of computation.

Instead, standard transformer inference commonly uses a **key-value cache**, or KV cache.

The system retains previously computed key and value representations from attention layers so that subsequent decoding steps do not need to recompute those representations for every preceding token.

Each new token generates additional cached state.

The cache reduces redundant work but consumes memory, which generally increases with the amount of retained context.

Some architectures modify this trade-off through grouped-query attention, sliding-window attention, compressed caches, or other mechanisms.

### 6.2 Why long contexts are expensive

In conventional full self-attention, computing attention across a sequence of length n involves a score matrix with approximately n² elements per head.

That gives standard full-attention prefill a quadratic attention-computation component.

Other parts of transformer computation have different scaling behavior, and optimized implementations can reduce memory overhead without necessarily eliminating the underlying pairwise attention work.

With KV caching, decoding a single new token need not rebuild the entire historical attention matrix. However, it still commonly attends over retained earlier keys, so the work and cache requirements depend on context length.

This distinction helps explain why LLM inference is often divided operationally into two different performance problems:

**Prefill:** Process the known input, often with substantial parallel computation.

**Decode:** Generate successive tokens, often constrained by sequential dependencies and memory movement.

The familiar experience of waiting for the first word and then watching text appear progressively is a visible consequence of this architecture.

---

## 7. Sampling: Where Probability Becomes an Answer

Let's consider the generation process more closely.

Suppose the model produces these illustrative next-token probabilities:

| Candidate | Probability |
|---|---:|
| "confirmed" | 0.60 |
| "completed" | 0.25 |
| "accepted" | 0.10 |
| "rejected" | 0.05 |

How should the application choose?

There are several strategies.

### Greedy decoding

Choose the highest-probability token at every step.

Here, that means "confirmed."

Greedy decoding removes deliberate random sampling, but it doesn't guarantee the best complete answer. The locally most probable token can lead into a less desirable sequence later.

It certainly doesn't guarantee factual correctness.

### Temperature

Temperature changes how sharply probabilities concentrate around high-scoring candidates.

The operation is commonly expressed as:

**P(i) = exp(zᵢ / T) / Σ exp(zⱼ / T)**

Where z represents logits and T is the temperature.

At temperature 1, the ordinary softmax distribution is preserved.

Lower positive temperatures concentrate probability on higher-scoring tokens. Higher temperatures flatten the distribution, making lower-scoring alternatives relatively more likely.

Temperature approaching zero behaves increasingly like greedy selection; implementations commonly treat temperature zero as a special greedy-decoding mode.

One subtlety deserves attention: increasing temperature doesn't necessarily make the model more creative in any meaningful human sense.

It increases variability in token selection.

That variability can produce interesting alternatives, but it can also produce incoherence, irrelevant wording, or mistakes.

### Top-p sampling

Another technique is **nucleus sampling**, commonly called top-p.

Rather than considering every vocabulary token, the decoder sorts candidates by probability and retains the smallest set whose cumulative probability reaches a threshold p.

With top-p equal to 0.9, the decoder keeps candidates accounting for at least approximately 90% of the probability mass, then renormalizes and samples from that set.

Unlike top-k sampling, which retains a fixed number of candidates, top-p adjusts the number based on how concentrated the distribution is.

These parameters can be combined, and different serving systems may apply additional constraints.

### Determinism is more complicated than setting temperature to zero

At a fixed point in the computation, given identical parameters and inputs, a deterministic numerical implementation will produce identical logits.

But a deployed model system may involve numerical nondeterminism, changing model versions, different hardware kernels, request routing, or other implementation effects.

Even when output generation is reproducible, a deterministic answer can be consistently wrong.

**Sampling controls how output candidates are selected. It is not a mechanism for validating whether those candidates are true.**

That distinction is fundamental.

---

## 8. Context Windows: Working Memory Without Permanent Learning

A modern language model can work with a substantial amount of supplied information.

But that information must be represented within its available context.

A **context window** is the amount of token context a model can process under its particular architecture and serving configuration.

It typically includes more than the latest user message.

Conversation history, instructions, retrieved documents, tool observations, and other content may all consume the same finite budget.

### Parameters versus context

Suppose you tell a model:

> Our hotel's cancellation deadline is now 18:00 instead of 16:00.

If the information is included in the current context, the model can use it when answering questions.

But the underlying model parameters have not automatically changed.

If the conversation is discarded and the information is not supplied again, the model does not inherently retain that update.

This creates two distinct mechanisms:

**Parametric knowledge** is information encoded through learned model parameters during training.

**Contextual information** is supplied to the model during its current inference.

A third mechanism can exist at the application level: storing information externally and retrieving it into future contexts.

That will become especially important in our sessions on retrieval and agent memory.

### Long context is not unlimited attention quality

A model advertising a large context window may accept an enormous document.

That does not mean every relevant detail inside it will be used equally reliably.

Performance depends on the task, model, context structure, distractors, document position, and whether the relevant information can be connected successfully during computation.

This is not merely a matter of total token capacity.

Imagine providing a hotel-support assistant with 500 pages of policies, contracts, correspondence, and historical booking records.

Somewhere in the middle sits the exact cancellation rule for a specific customer.

The model may fail to identify it despite the information being technically present.

A context window defines what the model can receive. It does not guarantee perfect retrieval or interpretation of everything inside.

This is one reason retrieval-augmented applications are more involved than stuffing as much text as possible into a prompt.

---

## 9. Why Models Can Reason—and Why They Still Hallucinate

We can now return to our opening mystery.

Why can an LLM explain sophisticated software architecture but invent an API?

The answer has several parts.

### 9.1 Learned structure supports genuine generalization

Programming languages are highly structured.

A model trained on substantial amounts of source code and technical explanations can develop useful representations of syntax, semantics, patterns, dependencies, and common software problems.

Those representations can support nontrivial computation.

For example, a model may reason that two concurrent transactions can both observe available inventory before either commits, and recognize that a particular isolation strategy might not prevent a business-level invariant from being violated.

That is useful technical reasoning, not merely reproducing an entire memorized paragraph.

However, successful reasoning about transaction behavior does not imply perfect knowledge of every API in every library version.

Those are different capabilities.

### 9.2 The training objective doesn't directly establish truth

Imagine a model has encountered hundreds of code examples involving fictional or obsolete library methods, many with syntactically plausible names.

It may learn that a certain kind of question is commonly answered with a function resembling:

`client.transactions.rollbackAsync()`

Given a related prompt, generating that identifier may be statistically attractive even when the exact API doesn't exist.

The model can construct an answer that fits familiar documentation patterns without having verified it against the library's actual interface.

Likewise, a fictional academic citation can have perfectly plausible formatting: authors, title, journal, year, and page numbers.

The result resembles a genuine citation because the model has learned how citations are structured.

But formatting competence is not bibliographic verification.

### 9.3 Token probability is not factual confidence

Suppose the model assigns a high probability to the next token in:

> The inventor of this technology was...

That score describes the model's relative preference for that token continuation under the current context and training.

It is not automatically a calibrated probability that the resulting historical statement is true.

A wrong answer can have very high model probability.

And a correct but unfamiliar answer may receive low probability.

Some models can produce useful estimates of their uncertainty, and confidence can sometimes be calibrated through appropriate training and evaluation. Nevertheless, neither fluent wording nor raw next-token probability should be mistaken for a reliable factual confidence guarantee.

### 9.4 Errors compound during generation

Autoregressive generation introduces another difficulty.

At every step, the model conditions on the tokens already generated.

If an early answer contains an incorrect assumption, later tokens may continue coherently from that assumption.

Consider:

> The customer is eligible for a full refund because the booking was canceled before the deadline...

If the booking actually missed the deadline, the subsequent explanation may develop a detailed but invalid argument.

The model's local continuation can be perfectly coherent relative to its own incorrect premise.

This is particularly dangerous because longer explanations can appear more convincing.

A detailed justification isn't necessarily independent evidence supporting the original conclusion.

### 9.5 Post-training affects presentation

Instruction tuning and preference optimization encourage models to produce responses users regard as helpful, clear, and appropriate.

That is generally valuable.

But the desirable properties of a response—coherence, helpfulness, directness, confidence, politeness—are not equivalent to factual correctness.

Training can improve truthfulness and appropriate uncertainty expression, yet no general guarantee follows that every confident statement has been verified.

This helps explain why models sometimes sound authoritative when mistaken.

The style of a competent explanation is easier to reproduce than a universal procedure for determining whether every statement is true.

### 9.6 Reasoning isn't always enough

One might propose a simple solution:

> Just tell the model to think harder.

Additional reasoning can improve results, especially when a problem can be decomposed into useful steps.

But it doesn't solve missing information or unreliable premises.

A model cannot derive the exact current signature of a newly released library method purely from logical reasoning when that detail is absent from its available knowledge.

It needs appropriate external information.

Similarly, generating more reasoning about a false assumption may merely produce a more elaborate false conclusion.

**Reasoning can transform available information. It cannot guarantee that the available information is complete, current, or correct.**

That is why tools, retrieval, verification, and evaluation become so important in production AI systems.

---

## 10. What Makes LLMs Different from Conventional Software?

Let's compare a conventional backend function with an LLM-driven component.

Suppose a deterministic function decides refund eligibility:

```ts
function isRefundEligible(
  canceledAt: Date,
  deadline: Date
): boolean {
  return canceledAt.getTime() <= deadline.getTime();
}
```

Given valid inputs and a fixed implementation, the function has an explicit behavioral rule.

We can test boundary conditions, inspect the implementation, and understand the contract.

Now imagine asking an LLM:

> Based on this conversation, is the customer eligible for a refund?

The model must interpret language, identify relevant facts, possibly resolve contradictions, and generate a result.

It may be extremely useful for extracting information from an ambiguous customer conversation.

But it does not automatically provide the correctness guarantees of the deterministic comparison.

A sensible architecture might use the model to extract the cancellation request and relevant facts, then let ordinary application logic evaluate the authoritative policy.

This highlights a useful division:

**Models are powerful at interpreting ambiguous inputs, transforming unstructured information, and generating flexible outputs. Conventional software is generally preferable for enforcing precise invariants and executable business rules.**

This is not an absolute division. Models can perform tasks that were previously difficult or impractical to encode deterministically, including sophisticated reasoning and code generation.

Conversely, ordinary code can also contain bugs and incomplete business logic.

The engineering difference lies in what guarantees each component can establish and how its behavior can be tested.

### A model is a component, not an oracle

When designing applications, it is useful to treat model outputs as potentially valuable but unverified results.

For a coding assistant, execution and tests can validate generated code.

For a document assistant, source material can support factual statements.

For a hotel reservation assistant, an authoritative booking system can confirm availability and reservation status.

And for a payment workflow, trusted backend code must enforce customer ownership, amounts, permissions, and transactional correctness.

The model's impressive capabilities do not eliminate those responsibilities.

They create opportunities to automate portions of workflows that conventional software cannot handle nearly as flexibly.

---

## 11. Practical Investigation: Experiment With Token Probabilities

We don't need to train a neural network to investigate one of its most important behavioral mechanisms.

We can build a tiny decoding experiment in TypeScript.

Assume that a hypothetical model has generated the following logits for three candidate tokens:

```ts
const logits = {
  confirmed: 2.5,
  completed: 1.2,
  rejected: -0.3,
};
```

These are invented scores for demonstration, not values obtained from an actual LLM.

Our job is to convert them into probabilities under different temperatures.

```ts
const logits = [2.5, 1.2, -0.3];
const labels = ["confirmed", "completed", "rejected"];

function softmax(
  values: number[],
  temperature = 1
): number[] {
  if (temperature <= 0) {
    throw new Error("Temperature must be positive");
  }

  const scaled = values.map(v => v / temperature);
  const max = Math.max(...scaled);

  const weights = scaled.map(v => Math.exp(v - max));
  const total = weights.reduce((sum, v) => sum + v, 0);

  return weights.map(v => v / total);
}

for (const temperature of [0.5, 1, 2]) {
  const probabilities = softmax(logits, temperature);

  console.log(`Temperature: ${temperature}`);

  labels.forEach((label, i) => {
    console.log(label, probabilities[i].toFixed(4));
  });
}
```

Notice the subtraction of the maximum logit before exponentiation. This is a standard numerical-stability technique that reduces the risk of overflow without changing the resulting softmax distribution.

Run the experiment and observe how the probabilities change.

At low temperature, "confirmed" should dominate strongly. At high temperature, the alternatives become more competitive.

### Investigation A: Implement sampling

Extend the program to randomly select an output according to the calculated probabilities.

Run 10,000 trials and compare the observed token frequencies against the theoretical distribution.

You should see the frequencies approach the expected probabilities, subject to sampling variation.

Then investigate what happens if you select the highest-probability token every time.

The outcome becomes much more predictable, but you haven't established whether "confirmed" was the semantically correct answer.

### Investigation B: Implement top-p

Sort candidates by descending probability.

Select the smallest prefix whose cumulative probability reaches at least 0.9, then renormalize the selected probabilities.

Compare the candidate sets at temperatures 0.5 and 2.

You should find that the number of eligible tokens can change because the underlying distribution changes.

### Investigation C: Examine real tokenization

Use a tokenizer inspection tool such as OpenAI's `tiktoken` or a Hugging Face tokenizer.

Compare these strings:

- `The customer canceled the reservation.`
- `getReservationCancellationDeadline`
- `Neįtikėtinas sprendimas`
- `SELECT * FROM reservations WHERE id = $1;`

Inspect the actual token IDs and boundaries.

Repeat the experiment with more than one tokenizer, if possible.

The goal isn't to memorize particular token counts. It is to understand why character length, word count, and token count are different quantities.

### Investigation D: Test epistemic reliability

Ask an LLM several questions in three categories:

1. A problem whose answer can be logically derived from the provided information.
2. A question requiring an exact, obscure historical fact.
3. A question about an invented software library or function.

Compare the responses.

Does the model distinguish uncertainty appropriately? Does an elaborate explanation correlate with actual correctness? Does explicitly permitting the answer "I don't know" improve behavior?

Treat the outcomes as observations, not universal conclusions. Model behavior depends on the particular model, training, prompt, and task.

---

## 12. Engineering and Interview Challenges

These questions are intended to test causal understanding rather than vocabulary memorization.

### Challenge 1 — The temperature misconception

A colleague says:

> "Our AI sometimes invents database functions. Let's set temperature to zero. Then its answers will be deterministic, so they should be correct."

What is wrong with this reasoning?

### Challenge 2 — The giant context window

A vendor offers a model capable of accepting an enormous quantity of input text.

Your team proposes inserting the company's entire internal documentation collection into every request rather than building search or retrieval infrastructure.

What problems might remain, even if the documentation technically fits?

### Challenge 3 — The next-token paradox

An interviewer argues:

> "If the model predicts tokens one at a time, it cannot possibly reason about a problem requiring twenty logical steps."

How would you respond without claiming that LLM reasoning is infallible?

### Challenge 4 — Parameters versus memory

A customer tells an AI agent that their preferred contact method has changed from email to SMS.

The model correctly acknowledges the preference.

The next day, in a new conversation, the agent doesn't remember it.

Why? What mechanisms would make the preference available tomorrow?

### Challenge 5 — Model or deterministic code?

You're designing a hotel customer-service assistant.

A user writes:

> "My plans have changed. I'd rather arrive next Thursday, and if that costs more than another hundred euros, just keep the original booking."

Which parts of this operation are appropriate for LLM interpretation, and which require authoritative application logic?

---

## 13. Challenge Solutions and Discussion

### Solution 1 — Determinism is not correctness

Temperature zero typically selects the highest-scoring continuation instead of deliberately sampling alternatives.

That reduces sampling-driven variation, but the model may consistently prefer a nonexistent API.

In fact, deterministic decoding can make the same hallucination repeat reliably.

The appropriate corrective mechanism is grounding the answer in actual API documentation, validating generated code against available declarations, compiling it, executing tests, or otherwise verifying correctness.

Temperature is an output-selection control, not a truthfulness guarantee.

### Solution 2 — Capacity doesn't guarantee retrieval quality

Even if all documents fit, the application may face substantial inference cost, increased latency, irrelevant contextual information, contradictory or obsolete documents, and imperfect use of information buried in long contexts.

It may also introduce authorization problems if documents belonging to different departments or tenants are included without proper filtering.

A retrieval system can identify relevant, current, authorized documents and supply them in a manageable context.

However, retrieval creates its own engineering problems, including indexing, ranking, and missing relevant documents. That is why RAG is an architecture requiring evaluation rather than a magical fix.

### Solution 3 — Sequential output doesn't prohibit sophisticated computation

At each generation step, the model performs substantial numerical computation across many layers and representations.

Training can produce mechanisms capable of modeling dependencies, applying abstractions, and performing meaningful operations on intermediate information.

The model can also generate intermediate steps and condition subsequent computation on them, sometimes improving its ability to solve multi-stage problems.

Therefore, next-token generation does not impose a trivial upper bound on cognitive or computational sophistication.

But the architecture does not automatically guarantee valid reasoning. Intermediate steps can be mistaken, the model can rely on faulty premises, and long reasoning sequences can accumulate errors.

The right question is not whether token prediction could support reasoning. It demonstrably can support useful reasoning behavior.

The important question is how reliably that behavior solves the particular class of problems being evaluated.

### Solution 4 — The conversation isn't automatically persistent model memory

The customer preference was supplied in one inference context.

That did not automatically modify the model's trained parameters or ensure the information would appear in later requests.

To preserve it, the application might save a structured preference in a customer-profile database.

When the customer returns, trusted application code retrieves the preference and supplies it to the model or uses it directly in downstream workflows.

More sophisticated memory systems may summarize previous interactions, store selected facts, retrieve relevant history, and reconcile conflicting information.

But for an explicit business preference such as preferred contact method, an ordinary structured database field is probably the better solution.

Not everything needs a vector database and an AI memory framework. Sometimes a boolean or enum wins the architecture contest.

### Solution 5 — Interpret flexibly, execute deterministically

The LLM is useful for understanding the user's intent:

- Requested arrival: next Thursday.
- Maximum acceptable additional cost: €100.
- Fallback: preserve the existing booking.

The application must establish which calendar date "next Thursday" means in the relevant timezone and conversational context.

Then authoritative systems should identify the customer's reservation, check amendment eligibility, request actual availability and pricing, and calculate the price difference using validated amounts.

Application logic must enforce the €100 threshold and appropriate permissions.

The workflow should also handle price changes, concurrent reservation modifications, retries, and failed external operations.

The model can help interpret ambiguous language and explain the outcome to the customer.

It should not invent availability, determine authoritative prices from its own parameters, or modify the reservation merely because its generated text sounds plausible.

The distinction is not between intelligent and unintelligent components.

It is between **probabilistic interpretation and verifiable business operations**.

---

## Mental Model

A modern language model is a trained numerical system that transforms token sequences into contextual representations and computes distributions over possible continuations.

Its transformer layers combine attention-based information exchange with learned nonlinear transformations. Training develops broad capabilities through prediction and other optimization objectives; inference applies those learned parameters to new contexts.

The model can exhibit sophisticated reasoning because accurate prediction rewards learning useful structure. Yet its generated answer is not automatically a verified statement about reality.

**Remember: generating a convincing answer and establishing that the answer is correct are two different computational problems.**


---

## Next Lecture — AI310-L02: Engineering Applications Around LLMs

Continue in **AI310 — Language Models and Retrieval Engineering**.

## Further Reading

1. **Vaswani et al. — Attention Is All You Need (2017)**  
   The original transformer paper. Especially valuable for understanding scaled dot-product attention, multi-head attention, and architectural motivation.  
   https://arxiv.org/abs/1706.03762

2. **Hugging Face — How Do Transformers Work?**  
   An accessible technical explanation of transformer architecture, language modeling, and different model families.  
   https://huggingface.co/docs/course/chapter1/4

3. **OpenAI — tiktoken**  
   A practical implementation of byte-pair tokenization, including educational material explaining how token segmentation works.  
   https://github.com/openai/tiktoken

4. **Hugging Face — Generation Strategies**  
   Technical explanations of greedy decoding, sampling, temperature, top-p, and related generation mechanisms.  
   https://huggingface.co/docs/transformers/main_classes/text_generation

5. **Hugging Face — KV Cache Documentation**  
   Useful for connecting the conceptual transformer to practical inference performance and memory management.  
   https://huggingface.co/docs/transformers/main/kv_cache

6. **Ouyang et al. — Training Language Models to Follow Instructions with Human Feedback (2022)**  
   An influential explanation of why pretraining alone does not produce an instruction-following assistant and how post-training changes model behavior.  
   https://arxiv.org/abs/2203.02155

