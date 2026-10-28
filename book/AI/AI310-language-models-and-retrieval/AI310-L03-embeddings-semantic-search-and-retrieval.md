---
id: AI310-L03
course: AI310
title: "Embeddings, Semantic Search, and Retrieval"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [AI501-S03]
prev: AI310-L02
next: AI310-L04
---







# AI310 — Language Models and Retrieval Engineering
## Lecture 03: Embeddings, Semantic Search, and Retrieval

### Finding What Nobody Actually Wrote

A customer contacts a hotel support assistant with an unusual question:

> If the hotel shuts down because of an emergency, can I get my money back?

Your company's internal knowledge base contains the answer. Somewhere among 80,000 policy documents, contractual agreements, and support articles is a paragraph stating:

> In cases of force majeure resulting in supplier nonperformance, reimbursement obligations shall be determined according to the applicable accommodation agreement.

The customer never mentioned *force majeure*, *supplier nonperformance*, or *reimbursement obligations*.

The document never mentioned *hotel shutting down*, *emergency*, or *money back*.

A simple keyword search may struggle to connect them.

Yet a competent human support agent immediately recognizes that these passages concern the same underlying situation.

What if a search engine could recognize that relationship without requiring someone to manually maintain a dictionary of synonyms?

This is the promise of semantic search.

Instead of comparing documents exclusively through their words, we can represent them as numerical vectors and search for proximity in a learned mathematical space.

But there is a catch.

A system might discover that two passages are highly similar while completely misunderstanding which one actually answers the question.

For example, an article explaining why customers are **not entitled to refunds** may be extremely similar to one explaining when they **are entitled to refunds**.

Both discuss the same concepts. Both may live in nearly the same region of embedding space.

One might be precisely what you need. The other could lead to an expensive mistake.

Our mission is to understand how semantic retrieval works, why vector search is fast, where it fails, and why sophisticated search systems increasingly combine old-fashioned information retrieval with neural techniques.

---

## 1. Search Is a Ranking Problem, Not a String Problem

Let's start with something deceptively simple.

Suppose a database contains 100,000 hotel support articles. A customer asks:

> Can I change the dates of a non-refundable reservation?

We want to return the most relevant documents.

What does *relevant* mean?

A reasonable definition is:

**A document is relevant when it provides information useful for satisfying the user's actual information need.**

That's already more complicated than string matching.

An article about modifying flexible reservations might contain every important word from the query, yet fail to answer the question about non-refundable reservations.

Another article titled *Exceptions to Advance Purchase Terms* might contain the correct answer without sharing much vocabulary.

This distinction has shaped information retrieval for decades.

Traditional search engines use techniques such as inverted indexes, term weighting, document statistics, and ranking functions.

Semantic search adds learned representations that can connect related expressions even when their words differ.

Neither approach completely solves relevance.

The fundamental problem remains:

Given a query Q and documents D₁ through Dₙ, produce an ordering that places the most useful documents near the top.

In practice, search consists of several potentially distinct operations:

**Candidate retrieval:** Find a manageable set of documents that might be relevant.

**Ranking:** Order candidates according to estimated relevance.

**Filtering:** Enforce constraints such as tenant ownership, document type, permissions, or publication date.

**Reranking:** Apply a more expensive model to refine the ordering of a smaller candidate set.

These stages exist because searching millions of documents with the most sophisticated possible relevance model would often be prohibitively expensive.

We need efficient approximations first, followed by more careful judgment where it matters.

---

## 2. Embeddings: Teaching Software a Useful Geometry

We encountered embeddings in AI310-L01 when discussing token representations inside transformers.

Here, we are interested in a related but distinct application: **embedding models that convert entire passages, documents, or queries into numerical vectors suitable for comparison.**

Suppose we have three sentences:

A. "The hotel canceled my reservation."

B. "My accommodation booking was canceled by the property."

C. "The restaurant serves excellent Italian food."

An embedding model might map each sentence into a high-dimensional vector.

For illustration:

```text
A → [0.72, 0.11, -0.43, ...]
B → [0.69, 0.15, -0.40, ...]
C → [-0.21, 0.81, 0.17, ...]
```

These are invented vectors, not actual model outputs.

The intention is that A and B occupy relatively nearby positions in the embedding space because they describe related situations.

C should generally be farther away.

### How do embeddings acquire these relationships?

An embedding model is trained to produce representations useful for some objective.

For retrieval-oriented models, training may encourage query–document pairs judged relevant to have compatible representations while pushing irrelevant combinations farther apart.

For example, a training dataset might contain:

**Query:** "How do I reset my password?"

**Relevant passage:** "To recover access to your account, follow the credential reset procedure."

**Irrelevant passage:** "The hotel swimming pool closes at 22:00."

A contrastive training objective can encourage the model to score the relevant pair more highly than the irrelevant one.

Training often uses positive examples, negative examples, and increasingly difficult negative examples.

A *hard negative* might discuss password security extensively without actually explaining how to reset a password.

Distinguishing these examples teaches the embedding model more than merely separating unrelated topics.

### Embeddings are task-dependent

Not every embedding model is optimized for semantic search.

Some are trained primarily for sentence similarity, classification, clustering, multilingual alignment, or other objectives.

A model that groups paraphrases effectively may not rank technical support documents particularly well.

The difference matters because a query and an answer are not necessarily paraphrases.

Consider:

> Why does my PostgreSQL transaction deadlock?

A relevant document might explain lock acquisition order, wait-for graphs, and deadlock detection without expressing the same question.

A retrieval-oriented model needs to learn a useful relationship between an information need and a document that satisfies it.

Some models also use distinct instructions or processing conventions for queries and documents. Ignoring those conventions can reduce retrieval quality even when the resulting vectors have compatible dimensions.

### Embeddings do not encode objective truth

Suppose we embed:

> Berlin is the capital of Germany.

And:

> Munich is the capital of Germany.

These sentences have nearly identical structure and closely related vocabulary. A semantic embedding model may place them near one another.

Yet one statement is true and the other is false.

The same problem arises with:

- "The customer is eligible for a refund."
- "The customer is not eligible for a refund."
- "The deadline is 14:00."
- "The deadline is 18:00."

Embeddings often capture broad semantic relationships better than precise logical distinctions.

A highly similar document may contradict another highly similar document.

**An embedding represents learned relationships useful for a task. It is not a compressed database of verified propositions.**

This is the first major limitation of semantic retrieval.

---

## 3. Vector Similarity: How Close Is Close?

Once documents and queries become vectors, we need a way to compare them.

Three common operations are Euclidean distance, dot product, and cosine similarity.

Their mathematical differences have practical consequences.

### Euclidean distance

For two vectors A and B, Euclidean distance measures their straight-line separation.

In two dimensions:

**d(A, B) = √((a₁ − b₁)² + (a₂ − b₂)²)**

Smaller distance means the vectors are closer.

This is the familiar geometry used to calculate the distance between two points on a flat map.

However, embedding vectors often have hundreds or thousands of dimensions.

The computation generalizes by summing squared coordinate differences across all dimensions.

### Dot product

The dot product multiplies corresponding coordinates and adds the results:

**A · B = Σ aᵢbᵢ**

It reflects both the alignment of the vectors and their magnitudes.

If vectors have different lengths, a longer vector may produce a larger dot product even without being better aligned in direction.

Whether that is desirable depends on how the embedding model was trained.

### Cosine similarity

Cosine similarity focuses on the angle between two vectors:

**cos(A, B) = (A · B) / (||A|| ||B||)**

For nonzero vectors, the result ranges from −1 to 1.

- **1:** Same direction.
- **0:** Orthogonal directions.
- **−1:** Opposite directions.

Consider:

```text
Query: A = [1, 1]

Document B = [2, 2]
Document C = [1, 0]
```

B points in exactly the same direction as A, so its cosine similarity is 1.

C points at a 45-degree angle from A, giving approximately 0.707.

But B has greater Euclidean distance from A than C does.

The two metrics therefore disagree about which document is closer.

Neither metric is universally superior.

The correct choice depends on the geometry learned by the embedding model.

### The normalization connection

A vector can be normalized to unit length:

**Â = A / ||A||**

For unit-length vectors, dot product equals cosine similarity.

Moreover:

**||A − B||² = 2 − 2(A · B)**

This means that for normalized vectors, maximizing dot product, maximizing cosine similarity, and minimizing Euclidean distance produce the same ranking, ignoring numerical precision and ties.

This is useful in practice because some embedding providers return normalized vectors.

It can also influence which similarity operator and index should be used.

But don't blindly normalize everything. Some models are trained to use vector magnitude meaningfully, and changing their representation may alter the intended similarity behavior.

### Similarity scores are not probabilities

Suppose a vector search returns a cosine similarity of 0.86.

Does that mean the document has an 86% probability of being relevant?

No.

Similarity scores are geometric quantities, not automatically calibrated relevance probabilities.

A score of 0.86 may be excellent for one embedding model and ordinary for another.

Even within one model, the appropriate threshold can vary between datasets and query types.

If an application treats 0.8 as a universal threshold for trustworthy information, it is inventing a guarantee that the embedding model does not provide.

---

## 4. Implement a Tiny Semantic Search Engine

Before introducing vector databases, let's implement the core operation.

Assume we have a few vectors already generated by an embedding model.

```ts
type Document = {
  id: string;
  text: string;
  embedding: number[];
};

const documents: Document[] = [
  {
    id: "refund",
    text: "Refunds are available for eligible cancellations.",
    embedding: [0.9, 0.1, 0.2],
  },
  {
    id: "restaurant",
    text: "The restaurant serves breakfast every morning.",
    embedding: [0.1, 0.9, 0.2],
  },
  {
    id: "payment",
    text: "Reimbursements are processed to the original card.",
    embedding: [0.8, 0.1, 0.3],
  },
];

function cosineSimilarity(
  a: number[],
  b: number[]
): number {
  if (a.length !== b.length || a.length === 0) {
    throw new Error("Incompatible vector dimensions");
  }

  const dot = a.reduce(
    (sum, value, i) => sum + value * b[i],
    0
  );

  const magnitude = (v: number[]) =>
    Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));

  const denominator = magnitude(a) * magnitude(b);

  if (denominator === 0) {
    throw new Error("Zero-length vector");
  }

  return dot / denominator;
}

function search(
  queryVector: number[],
  limit = 2
) {
  return documents
    .map(doc => ({
      ...doc,
      score: cosineSimilarity(
        queryVector,
        doc.embedding
      ),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

console.log(search([0.85, 0.1, 0.25]));
```

The vectors are artificial, so the ranking demonstrates the algorithm rather than real language understanding.

But the retrieval mechanism is genuine.

For every document:

1. Calculate its similarity to the query.
2. Sort by similarity.
3. Return the highest-scoring results.

Notice something remarkable: once embeddings exist, the search engine doesn't need to understand English.

It only needs numerical vectors and a similarity function.

This separation is one reason embedding-based architectures are so flexible.

The embedding model performs the expensive learned representation step. The vector search system performs the numerical comparison step.

### The scaling problem

Our implementation compares the query against every stored document.

If we have N documents, each containing a D-dimensional vector, the similarity calculations require roughly **O(ND)** arithmetic work per query.

Sorting all N results adds further cost, although production systems can use top-k selection algorithms to avoid fully sorting everything.

For 500 documents, none of this matters.

For 50 million documents containing large vectors, it matters quite a lot.

This motivates vector indexes.

---

## 5. Exact Search Versus Approximate Nearest Neighbors

An exact nearest-neighbor query examines enough of the collection to guarantee the nearest results according to the chosen metric, assuming correct implementation.

A straightforward method is exhaustive comparison.

An approximate nearest-neighbor search, or **ANN**, uses an index to avoid comparing the query with every vector.

The result is usually faster, but it may miss some of the true nearest neighbors.

This is a deliberate trade-off.

### Why conventional indexes aren't sufficient

You already know how B-tree indexes accelerate database queries.

A B-tree exploits an ordered relationship among values. It works beautifully for conditions such as:

```sql
WHERE reservation_id = 123
```

Or:

```sql
WHERE created_at > '2026-10-01'
```

But how do we efficiently search a collection of points in a 1,536-dimensional space?

There is no single natural ordering that preserves all nearest-neighbor relationships.

A vector might be close to another vector in most dimensions while being far away in a few.

High-dimensional search also encounters phenomena associated with the *curse of dimensionality*, where many intuitive geometric indexing strategies become less effective as dimensionality increases.

Specialized approximate indexes address this problem through alternative data structures.

Two important approaches are graph-based HNSW and clustering-based inverted files.

---

## 6. HNSW: Navigating a Graph Instead of Scanning Everything

**Hierarchical Navigable Small World**, or HNSW, is one of the most widely used ANN indexing approaches.

Its idea is elegant: instead of comparing the query against every stored vector, construct a graph connecting vectors to useful neighbors.

Then search the graph by moving toward increasingly promising regions.

### A geographical analogy

Imagine trying to find the restaurant geographically closest to you in Europe.

An exhaustive solution would compare your location to every restaurant.

A hierarchical navigation strategy might work differently.

First, select the relevant country.

Then navigate toward the correct city.

Then move through neighborhoods.

Finally, examine nearby streets.

HNSW doesn't literally use countries or cities, but the analogy captures its coarse-to-fine organization.

### A hierarchy of proximity graphs

HNSW organizes data into multiple graph layers.

The upper layers contain relatively few nodes and support longer-range navigation.

Lower layers contain progressively more nodes and provide finer-grained connections.

The bottom layer contains the full indexed population.

Conceptually:

```text
Upper layer:
A ------------------------- Z

Middle layer:
A ------ F ------ M ------- Z
         \        |
          H ------R

Bottom layer:
A--B--C--F--G--H--J--M--N--R--S--Z
```

These are illustrative connections rather than an actual HNSW graph.

Search begins at a high layer and greedily moves toward nodes closer to the query.

It then descends to lower layers, progressively refining the search.

At the bottom, the algorithm explores a bounded candidate set rather than depending only on one greedy path.

This matters because a purely greedy walk could become trapped near a local candidate while missing better neighbors elsewhere.

HNSW's layered graph and candidate exploration help balance search speed and result quality.

### Construction and search parameters

Two important HNSW construction parameters are commonly called:

**M:** Controls the maximum number of graph connections per node at a layer, subject to implementation-specific details.

**ef_construction:** Controls the size of the candidate set considered during index construction.

Higher values can improve graph quality but increase construction time and memory consumption.

At query time, **ef_search** controls how broadly the graph is explored.

Increasing it usually improves recall at the cost of more work and greater latency.

The result is a classic engineering trade-off:

| Configuration | Likely consequence |
|---|---|
| Smaller search effort | Lower latency, potentially more missed neighbors |
| Larger search effort | Higher recall, more computation |
| More graph connections | Larger index, potentially better navigation |
| More exhaustive construction | Slower indexing, potentially higher-quality graph |

HNSW is not guaranteed to find the exact nearest neighbor.

That is the price of avoiding exhaustive comparison.

### An important operational detail

Graph indexes must also handle insertions, deletions, updates, memory management, and index maintenance.

A large HNSW index can consume substantial memory. Building and updating it can be significantly more expensive than performing simple relational inserts.

Indexing millions of embeddings isn't free merely because querying them can be fast.

### What about IVFFlat?

Another approach is **inverted file indexing**, commonly implemented as IVFFlat.

Instead of building a navigation graph, it partitions vectors into groups or lists based on their positions in the vector space.

A query identifies the most promising groups and searches those candidates.

Inspecting more groups usually improves recall but increases work.

In pgvector, IVFFlat generally has lower build-time and memory overhead than HNSW, while HNSW often offers a better speed–recall trade-off for querying.

IVFFlat also needs a representative dataset to construct useful clusters.

The correct choice depends on collection size, update patterns, query requirements, available memory, and measured performance.

For many PostgreSQL-backed applications, HNSW is a reasonable default to investigate first—but not a reason to create an ANN index before you need one.

---

## 7. Vector Search in PostgreSQL with pgvector

Let's connect the theory to a familiar database.

PostgreSQL can support vector similarity search through the **pgvector** extension.

This lets us store embeddings alongside relational data and query them with SQL.

For a small or medium-sized application already using PostgreSQL, this can be attractive because it avoids introducing an entirely separate vector-search service.

### Creating a vector-enabled table

Imagine a knowledge base for several hotel customers.

Our chosen embedding model produces 768-dimensional vectors.

We might use:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

The dimensionality must match the embedding output.

A 768-dimensional vector cannot be inserted into a `vector(768)` column if it contains only 512 components.

More subtly, two embedding models can produce vectors of identical dimensionality while learning incompatible representational spaces.

**Same dimensionality does not mean same meaning.**

You must know which embedding model and configuration produced your stored vectors.

### Exact similarity search

Given an embedded query, PostgreSQL can rank documents by cosine distance:

```sql
SELECT
    id,
    title,
    content,
    1 - (embedding <=> $1::vector) AS similarity
FROM knowledge_documents
WHERE tenant_id = $2
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

The `<=>` operator calculates cosine distance.

For pgvector, smaller distance corresponds to higher cosine similarity.

Therefore, the query sorts in ascending distance order.

The expression `1 - cosine_distance` converts that distance into a similarity score for display or analysis.

Notice the tenant filter.

It is not optional decoration. A multi-tenant search system must enforce document access through trusted database predicates or equivalent authorization mechanisms.

The embedding model does not understand your access-control policy, and similarity cannot substitute for authorization.

### Adding an HNSW index

For larger datasets, we might create:

```sql
CREATE INDEX knowledge_embedding_hnsw
ON knowledge_documents
USING hnsw (embedding vector_cosine_ops);
```

The operator class must match the distance operation used in indexed queries.

For example, an index configured for cosine distance is not automatically appropriate for an L2-distance query.

When the query and index are compatible, PostgreSQL may use the HNSW index to retrieve approximate nearest neighbors.

Use `EXPLAIN (ANALYZE, BUFFERS)` to inspect the actual execution plan rather than assuming the index is used.

With a tiny table, a sequential scan may still be cheaper.

### Filtering can surprise you

Here's an important complication.

Suppose the database contains one million document embeddings, but only 1% belong to a particular tenant.

An approximate index may identify nearby vectors globally before the query's tenant predicate eliminates nonmatching rows.

If most candidate vectors belong to other tenants, the remaining result set may contain fewer useful results than requested.

In pgvector, approximate-index filtering can therefore reduce effective recall.

Possible solutions include increasing search effort, using iterative index scans where supported, partitioning data, partial indexes, or performing exact search over a sufficiently small filtered subset.

For supported pgvector versions, an iterative HNSW scan can be enabled with:

```sql
SET hnsw.iterative_scan = strict_order;
```

This allows additional index exploration when necessary, subject to configured limits.

But remember the difference between **returning fewer candidates** and **exposing unauthorized candidates**.

The SQL authorization predicate must remain authoritative. Search tuning improves retrieval quality; it does not replace permission enforcement.

For small tenant-specific collections, a conventional index on `tenant_id`, followed by exact vector comparison, may be simpler and sufficiently fast.

This illustrates a broader principle:

**The best search strategy depends not only on vector similarity, but also on the relational constraints defining which documents are eligible.**

### Embedding lifecycle

A production system should preserve the embedding model identifier and version, either alongside each embedding or in associated index metadata.

Why?

Because replacing the embedding model changes the geometry of the space.

You cannot safely generate query embeddings with an unrelated new model and expect them to work correctly against vectors produced by the old model.

A migration may require re-embedding the document collection, constructing a new index, validating quality, and switching queries to the new representation.

Embedding upgrades are data migrations, not merely configuration changes.

---

## 8. Traditional Keyword Search Is Far from Obsolete

So far, neural semantic search sounds rather impressive.

Why not abandon keyword search entirely?

Because exact words frequently matter.

Suppose an engineer searches your internal documentation for:

`ERR_PAYMENT_PROVIDER_TIMEOUT`

A semantic model may find numerous articles about payment processing, retry strategies, and network failures.

But the engineer probably wants documents containing that exact error identifier.

Another query might reference:

- A reservation number.
- An obscure API method.
- A legal clause identifier.
- A product SKU.
- A specific hotel name.
- A newly introduced technical term.

For these cases, lexical matching can be extremely effective.

### Inverted indexes

A traditional search engine commonly relies on an **inverted index**.

Instead of scanning every document for each word, the index maps terms to documents containing those terms.

For example:

```text
"refund"      → documents [2, 5, 9, 18]
"reservation" → documents [1, 2, 7, 9]
"deadline"    → documents [2, 7, 14]
```

A query involving "refund deadline" can quickly identify documents containing the relevant terms.

Real systems use more sophisticated postings structures and may preserve term frequencies, positions, field information, and other statistics.

This approach remains extremely efficient.

The difficult part is ranking the matches.

### TF-IDF intuition

A basic principle in information retrieval is that frequent words within a document can indicate relevance, while words common across almost every document are less discriminative.

If every hotel article contains "hotel," that word tells us very little.

If only five documents contain a rare payment error code, that term may be highly informative.

This motivates **term frequency–inverse document frequency**, or TF-IDF.

Term frequency rewards words appearing in a document.

Inverse document frequency reduces the importance of terms occurring throughout the collection.

A term's usefulness therefore depends on both its frequency in a document and its rarity across the corpus.

### BM25

**BM25** is a widely used ranking function that refines these ideas.

Its score combines several influences:

- Whether query terms appear.
- How frequently they appear.
- How rare they are across documents.
- Document length.
- Controls preventing repeated terms from dominating indefinitely.

One important feature is *term-frequency saturation*.

If a document mentions "refund" three times, that may be stronger evidence than mentioning it once.

But mentioning it 300 times should not make it 100 times more relevant.

BM25 applies a nonlinear term-frequency function so the benefit of repetition diminishes.

It also uses document-length normalization, helping avoid systematically favoring long documents simply because they contain more words.

In common formulations, parameters named `k1` and `b` control term-frequency saturation and the strength of length normalization.

BM25 remains a strong retrieval baseline.

A system using expensive neural models should be compared against a well-configured lexical baseline rather than against an intentionally primitive string search.

### PostgreSQL full-text search

PostgreSQL includes its own full-text indexing and ranking mechanisms.

For example:

```sql
ALTER TABLE knowledge_documents
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', title || ' ' || content)
) STORED;

CREATE INDEX knowledge_text_gin
ON knowledge_documents
USING gin (search_vector);
```

Now we can query:

```sql
SELECT
    id,
    title,
    ts_rank_cd(
        search_vector,
        plainto_tsquery('english', $1)
    ) AS rank
FROM knowledge_documents
WHERE
    tenant_id = $2
    AND search_vector @@ plainto_tsquery('english', $1)
ORDER BY rank DESC
LIMIT 10;
```

This uses PostgreSQL's text-search functionality.

The ranking function `ts_rank_cd` is based on cover density; it is **not the same scoring algorithm as BM25**.

PostgreSQL full-text search can nevertheless provide a useful lexical retrieval mechanism.

Language configuration matters too. English stemming rules may be inappropriate for Lithuanian, German, or mixed-language documents.

For multilingual corpora, tokenization, stemming, language identification, and normalization require additional attention.

---

## 9. Hybrid Search: Combining Words and Meaning

Consider these two queries:

**Query A:** "How are customers reimbursed when accommodation becomes unavailable?"

**Query B:** "What does error `ERR_RES_4097` mean?"

Semantic retrieval is especially useful for Query A because it can connect different descriptions of the same problem.

Lexical retrieval is especially valuable for Query B because the exact identifier is highly informative.

But real queries often combine both kinds of information.

For example:

> Why does `ERR_RES_4097` happen when modifying a non-refundable reservation?

The ideal result must understand the reservation-modification concept while preserving the exact error code.

This motivates **hybrid search**.

A hybrid retrieval pipeline runs multiple candidate-generation methods and combines their results.

```text
                  User query
                      |
             +--------+--------+
             |                 |
             v                 v
        Lexical search    Vector search
          BM25/FTS          Embeddings
             |                 |
             v                 v
         Top 50             Top 50
             |                 |
             +--------+--------+
                      |
                      v
                 Merge + rank
                      |
                      v
                Final candidates
```

The challenge is combining rankings with incompatible scores.

A lexical relevance score of 12.7 cannot be meaningfully compared directly with a cosine similarity of 0.82.

They come from different mathematical systems.

### Reciprocal Rank Fusion

A practical solution is **Reciprocal Rank Fusion**, or RRF.

Instead of combining raw scores, RRF combines the positions of documents in different rankings.

A common formula is:

**RRF(d) = Σ 1 / (k + rankᵢ(d))**

Where:

- `rankᵢ(d)` is the position of document d in retrieval list i.
- `k` is a positive constant controlling how strongly top positions are favored.
- Missing documents contribute nothing for that list.

Consider two documents.

Document A ranks second in lexical search and fourth in semantic search.

Document B ranks first in lexical search but does not appear among semantic candidates.

With `k = 60`:

**A = 1/62 + 1/64 ≈ 0.0318**

**B = 1/61 ≈ 0.0164**

Document A wins because it appears near the top in both retrieval systems.

RRF is attractive because it doesn't require score calibration between different retrieval algorithms.

But it has limitations.

A highly relevant document appearing in only one ranking may lose to a mediocre document appearing in both.

The candidate cutoff, fusion constant, and relative contributions of each system still require evaluation.

Hybrid retrieval is powerful, not infallible.

---

## 10. Reranking: A More Expensive Second Opinion

Even after hybrid retrieval, the highest-ranked documents may not actually answer the question.

The first-stage retrieval systems are designed to search large collections efficiently.

They may be relatively weak at distinguishing fine-grained relevance.

This motivates reranking.

### Bi-encoders versus cross-encoders

A conventional embedding model used for retrieval is often a **bi-encoder**.

It independently computes an embedding for the query and an embedding for each document.

Those embeddings can be compared efficiently, and document embeddings can be precomputed.

```text
Query --------> Encoder ----> Query vector
                                  |
                               similarity
                                  |
Document -----> Encoder ----> Document vector
```

A **cross-encoder** works differently.

It receives the query and candidate document together, allowing the model to analyze their relationship directly.

```text
Query + Candidate document
              |
              v
         Cross-encoder
              |
              v
        Relevance score
```

Because the model jointly processes the query and candidate, it can capture finer relationships than independent embeddings.

For example, a cross-encoder may better distinguish between:

> Customers can receive refunds if the hotel cancels.

And:

> Customers cannot receive refunds if they cancel voluntarily.

Both passages share much of their vocabulary and subject matter.

A stronger reranker can consider the precise information need and the conditional distinctions between passages.

However, cross-encoders must evaluate query–document pairs.

Scoring one million documents individually would be expensive.

So we use a two-stage design:

1. Retrieve perhaps 50–200 candidates efficiently.
2. Rerank them with a more capable relevance model.
3. Return the best few.

The exact candidate count depends on latency, costs, quality requirements, and the chosen models.

Some systems use learned sparse retrieval or late-interaction models as additional alternatives between simple dense retrieval and full cross-encoder reranking.

The shared principle is to allocate expensive relevance computation selectively.

### Reranking cannot recover missing candidates

Suppose the correct policy never appears in the initial candidate set.

No reranker can promote it into the results, because it never sees it.

This produces an important architectural dependency:

**Candidate generation must achieve sufficient recall before sophisticated ranking can improve final precision.**

Optimizing reranking while ignoring retrieval misses is like hiring the world's best interviewer and then giving them a shortlist containing none of the qualified candidates.

An expensive and remarkably professional failure.

---

## 11. Measuring Retrieval Quality

Search feels subjective until we define measurable objectives.

Suppose a query has five genuinely relevant documents in the corpus.

Your system returns ten results, three of which are relevant.

Two basic metrics are useful.

### Precision@k

Precision measures what fraction of retrieved results are relevant.

**Precision@10 = 3/10 = 30%**

This tells us how much irrelevant material appears among the returned results.

For user-facing search, high precision near the top is often important.

### Recall@k

Recall measures what fraction of all relevant documents were retrieved.

**Recall@10 = 3/5 = 60%**

For a retrieval stage feeding a reranker, recall may be especially important.

The reranker can remove irrelevant candidates, but it cannot invent relevant documents that were never retrieved.

### Mean Reciprocal Rank

Sometimes only one correct result matters.

**Reciprocal Rank = 1 / position of first relevant result**

If the first relevant document appears in third position:

**RR = 1/3**

Mean Reciprocal Rank, or MRR, averages this quantity over many queries.

It rewards systems that place a relevant result early.

### NDCG

Not all relevance is binary.

A document might be:

- Perfectly relevant.
- Partially relevant.
- Related but insufficient.
- Completely irrelevant.

Normalized Discounted Cumulative Gain, or **NDCG**, evaluates ranking quality using graded relevance judgments and discounts useful results appearing farther down the ranking.

It is valuable when the first result matters more than the tenth and when relevance has multiple levels.

### Two different meanings of recall

Be careful: ANN index recall and retrieval relevance recall are not identical.

**ANN recall** measures how many of the exact nearest neighbors the approximate index successfully returns.

**Retrieval recall** measures how many genuinely relevant documents appear among the results.

An ANN index can achieve nearly perfect recall of the nearest vectors while the embedding model ranks the wrong documents.

Conversely, a slightly approximate index may still retrieve every document needed for a particular task.

This distinction prevents us from confusing index performance with search quality.

### Constructing an evaluation dataset

A useful retrieval evaluation dataset contains:

```text
Query
Relevant document IDs
Optional graded relevance scores
Metadata constraints
Expected query category
```

For example:

```json
{
  "query": "Can I recover the cost if the hotel closes?",
  "relevantDocumentIds": [17, 42],
  "category": "supplier_cancellation"
}
```

A serious dataset includes difficult cases:

- Synonyms and paraphrases.
- Exact identifiers.
- Negation.
- Rare technical terminology.
- Multilingual questions.
- Outdated versus current documents.
- Similar documents with different conditions.
- Questions for which no relevant document exists.

Human relevance judgments are not perfectly objective, but they provide substantially better evidence than admiring a few impressive search results.

Evaluate different retrieval configurations on the same representative query set.

Measure quality alongside latency, memory consumption, and indexing cost.

The fastest vector search is not necessarily the best search system.

---

## 12. The Engineering Traps That Matter

Several failure modes deserve special attention because they arise naturally from everything we've learned.

### Negation and numerical precision

Embeddings may consider "refunds permitted" and "refunds prohibited" similar.

They may also fail to distinguish policy thresholds such as €100 and €1,000.

Use reranking, structured filters, authoritative checks, or other task-specific mechanisms where these distinctions matter.

### Metadata filtering

A document may be semantically relevant but belong to the wrong tenant, jurisdiction, product version, or time period.

Metadata constraints should be part of candidate eligibility, not merely optional ranking hints.

A search result that violates access controls is not an imperfect ranking—it is a security failure.

### Duplicate and near-duplicate documents

A knowledge base may contain dozens of copies of nearly identical policies.

These can dominate top-k results, reducing the diversity of useful information.

Deduplication, document grouping, and source-aware selection can help.

### Multilingual representation

Some embedding models support multiple languages well; others do not.

A German query searching English policies may work with an appropriately trained multilingual model, but multilingual capability must be evaluated rather than assumed.

### Stale embeddings

If a document changes but its embedding remains unchanged, vector search operates on a stale representation.

Even if the displayed document content is fresh, its search position may reflect the old content.

Embedding generation and index updates therefore belong to the broader data-maintenance lifecycle.

### No relevant document exists

Nearest-neighbor search will generally return the nearest available vectors even when every document is irrelevant.

The closest point in a vector space is not necessarily a good match.

Applications need strategies for abstaining, requesting clarification, or reporting that no suitable evidence was found.

Fixed similarity thresholds may help in particular datasets, but they require calibration.

---

## 13. Practical Lab: A Small Hybrid Search System

Build a search service over 100–500 realistic technical or hotel-support documents.

Use PostgreSQL with pgvector.

### Part A — Create the baseline

Store each document's ID, title, content, tenant, and relevant metadata.

Implement PostgreSQL full-text search first.

Test queries containing exact identifiers, policy terms, and ordinary natural language.

Record the top ten results for each query.

### Part B — Add embeddings

Choose a retrieval-oriented embedding model.

Generate one embedding per document, preserving the model identifier and dimensionality.

Embed user queries using the same compatible model configuration, accounting for any query-specific instructions required by that model.

Store the vectors in PostgreSQL and implement cosine-distance search.

For a modest dataset, begin with exact vector search.

There is no need to introduce ANN approximation before the dataset justifies it.

### Part C — Compare retrieval approaches

Create 20–30 representative queries with manually identified relevant documents.

Compare:

1. Lexical retrieval.
2. Dense vector retrieval.
3. Hybrid retrieval using RRF.

Measure Precision@5, Recall@10, and MRR where appropriate.

Identify which query types favor each method.

### Part D — Introduce approximate indexing

Expand the dataset if necessary, potentially using a larger public document collection.

Add an HNSW index.

Compare query plans, latency, index size, and differences between approximate and exact nearest-neighbor results.

Experiment with `hnsw.ef_search`.

Test highly selective metadata filters and observe whether ANN candidate exploration affects the number of matching results.

### Part E — Add a reranker

Take the top 30–50 hybrid candidates and rerank them using a suitable cross-encoder.

Measure whether final ranking improves.

Then deliberately remove the correct document from the candidate pool.

Observe that reranking cannot recover it.

The purpose of this lab is not to build an enormous search platform. It is to understand how representation quality, index behavior, ranking, and filtering independently influence retrieval quality.

---

## 14. Engineering and Interview Challenges

### Challenge 1 — The perfect similarity score

Your vector search returns a policy with cosine similarity 0.94.

A developer claims this proves the policy answers the customer's question.

What is wrong with that conclusion?

### Challenge 2 — The missing tenant results

Your HNSW-backed database contains millions of documents from thousands of tenants.

A query for a small tenant returns only three results despite requesting ten.

The tenant has hundreds of documents.

What could explain this behavior?

### Challenge 3 — The embedding migration

Your team upgrades to a newer embedding model that produces vectors with exactly the same dimensionality as the previous model.

Can you simply switch the query-embedding function without rebuilding the document embeddings?

### Challenge 4 — The expensive reranker

A colleague proposes using a powerful cross-encoder to score every document in a collection of ten million records.

Why is this generally a poor architecture? How would you redesign it?

### Challenge 5 — The search-quality paradox

Your ANN index achieves 99.9% recall relative to exact nearest-neighbor search.

But customers still complain that the returned documents are irrelevant.

How can both observations be true?

---

## 15. Solutions and Discussion

### Solution 1 — Similarity measures geometry, not correctness

The score measures compatibility between the query and document under the embedding model.

It does not establish that the document answers the question, contains correct information, or satisfies the user's constraints.

A passage contradicting the correct policy may have high similarity because it discusses the same concepts.

Relevance must be evaluated separately, potentially using a reranker, authoritative metadata, and task-specific validation.

### Solution 2 — Approximate search and selective filtering can interact badly

The shared ANN index may prioritize globally nearby vectors belonging to other tenants.

The tenant predicate removes those rows, leaving fewer results than requested.

Investigate the execution plan, filtering behavior, search effort, and candidate limits.

Possible remedies include iterative HNSW scans, tuning `ef_search`, partitioning, partial indexes for suitable tenant distributions, or exact search after efficient tenant filtering.

Do not remove the authorization filter to improve result counts.

### Solution 3 — Equal dimensions do not imply compatible vector spaces

Different embedding models learn different geometries.

Two 768-dimensional representations may have entirely different meanings.

Switching only query embeddings can destroy retrieval quality.

Treat the change as a representation migration: build new document embeddings, construct compatible indexes, evaluate the new configuration, and switch queries consistently.

### Solution 4 — Use efficient retrieval before expensive ranking

A cross-encoder generally processes each query–document pair jointly.

Ten million comparisons per user query are unlikely to be economical for an interactive application.

Instead, use lexical or embedding-based retrieval to identify a relatively small candidate set.

Then apply the cross-encoder to those candidates.

The initial stage prioritizes scalability and sufficient recall; the second stage prioritizes precise ranking.

### Solution 5 — The index can reproduce the wrong geometry perfectly

ANN recall compares approximate search with exact search under the same vector metric.

If the embedding model places irrelevant documents closest to the query, an index achieving 99.9% nearest-neighbor recall faithfully reproduces that poor ordering.

The problem lies in representation quality or relevance modeling, not necessarily indexing.

Compare against human-labeled relevance judgments, inspect query categories, and consider hybrid retrieval or reranking.

**Retrieving the mathematically nearest document is only useful when the mathematics reflects the user's actual information need.**

---

## Mental Model

Semantic retrieval converts queries and documents into vectors, then searches for proximity in a learned representation space.

Vector indexes such as HNSW make large-scale similarity search practical by trading exactness for efficiency. Lexical retrieval preserves the importance of exact terms, while hybrid search and reranking combine complementary signals.

The crucial distinction is between geometric similarity and actual relevance.

**Retrieval is a ranking problem. Embeddings provide one powerful signal—not a guarantee that the nearest document contains the right answer.**


---

## Next Lecture — AI310-L04: Retrieval-Augmented Generation

Continue in **AI310 — Language Models and Retrieval Engineering**.

## Further Reading

1. **pgvector — Official Documentation**  
   Practical reference for PostgreSQL vector operators, HNSW, IVFFlat, indexing strategies, filtering, and hybrid search.  
   https://github.com/pgvector/pgvector

2. **Malkov & Yashunin — Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs**  
   The foundational HNSW research, explaining graph construction and hierarchical nearest-neighbor navigation.  
   https://arxiv.org/abs/1603.09320

3. **PostgreSQL — Full Text Search**  
   Official documentation covering `tsvector`, `tsquery`, indexing, matching, ranking, and configuration.  
   https://www.postgresql.org/docs/current/textsearch.html

4. **Elasticsearch — Similarity Settings**  
   Useful technical reference for BM25 ranking, term-frequency saturation, and document-length normalization.  
   https://www.elastic.co/docs/reference/elasticsearch/index-settings/similarity

5. **Sentence Transformers — Retrieve & Re-Rank**  
   Practical explanations and examples of bi-encoders, cross-encoders, semantic retrieval, and two-stage ranking.  
   https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html

6. **BEIR — A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models**  
   Research on evaluating retrieval approaches across diverse tasks rather than relying on one narrow benchmark.  
   https://arxiv.org/abs/2104.08663

7. **Cormack, Clarke & Büttcher — Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**  
   An influential paper on combining rankings from different retrieval systems.  
   https://doi.org/10.1145/1571941.1572114

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
AI310-L03  EMBEDDINGS & RETRIEVAL — INTERVIEW GLANCE CARD

SEARCH = RANKING
  Relevant = useful for information need (≠ string match)
  Stages: candidate retrieve → rank → filter (tenant/date) → optional rerank

EMBEDDINGS
  Passage/query → vector; contrastive train (hard negatives)
  Retrieval-oriented ≠ paraphrase/similarity model; follow query/doc conventions
  Similar geometry can link true & false / allowed & prohibited claims
  Embedding ≠ compressed verified facts

SIMILARITY
  L2 / dot / cosine; for unit vectors: same ranking (up to ties/precision)
  Score ≠ probability of relevance; thresholds need calibration per model/data

SCALE
  Exact: O(ND) scan; ANN (HNSW, IVFFlat): speed vs missed neighbors
  HNSW: hierarchical graphs; M / ef_construction / ef_search trade-offs
  IVFFlat: cluster lists; lower build/memory; needs representative data
  B-trees don't preserve NN in high-D

PGVECTOR
  vector(d) must match model; same dim ≠ same space
  <=> cosine distance; ORDER ASC; 1−dist = similarity display
  Tenant filter AUTHORITATIVE; ANN + selective filter can starve results
  Iterative HNSW / higher ef_search / partition / exact after filter
  Model upgrade = re-embed + reindex migration

LEXICAL STILL WINS
  Exact IDs/error codes/SKU; inverted index; TF-IDF intuition; BM25 saturation
  Postgres FTS (tsvector/GIN) ≠ BM25 algorithm but useful baseline

HYBRID + RERANK
  Lexical + dense → merge (RRF: Σ 1/(k+rank)); no raw-score mixing
  Bi-encoder retrieve; cross-encoder rerank small candidate set
  Reranker cannot invent missing candidates — need recall first

METRICS
  Precision@k / Recall@k / MRR / NDCG (graded)
  ANN recall ≠ relevance recall (faithful wrong geometry possible)

TRAPS
  Negation/numbers; metadata eligibility; near-dupes; multilingual; stale embeds;
  NN always returns something — may need abstain

SENIOR LINE: nearest vector useful only if geometry matches the information need.
```
