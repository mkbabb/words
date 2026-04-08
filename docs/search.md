# Search

Floridify's search system is a five-method cascade over arbitrary lexicons, designed to answer one question well: given a user's query—correct, misspelled, phonetically approximated, or semantically adjacent—find the vocabulary entry they intended. Each method in the cascade covers a distinct failure mode of the ones before it: exact matching handles the common case in sub-millisecond time, prefix search powers autocomplete, substring search catches infix queries, fuzzy search tolerates typos and transpositions, and semantic search recovers meaning when all surface-level techniques fail.

The system processes corpora from hundreds of words to 300,000+, adapting its data structures, candidate budgets, and FAISS index topology to the scale at hand. All indices are versioned and persisted; a hot-reload mechanism detects vocabulary changes and atomically swaps the search engine without dropping queries.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Exact & Prefix Search: marisa-Trie](#exact--prefix-search-marisa-trie)
- [Bloom Filter](#bloom-filter)
- [Substring Search: Suffix Arrays](#substring-search-suffix-arrays)
- [Fuzzy Search: the `ffuzzy` crate](#fuzzy-search-the-ffuzzy-crate)
  - [Adaptive k](#adaptive-k)
  - [Damerau-Levenshtein, not plain Levenshtein](#damerau-levenshtein-not-plain-levenshtein)
  - [BK-tree, bounded](#bk-tree-bounded)
  - [The "3.5-gram" trigram index](#the-35-gram-trigram-index)
  - [Signal-based score boosting](#signal-based-score-boosting)
- [Phonetic Search](#phonetic-search)
- [Semantic Search](#semantic-search)
- [Cascade Orchestration & Scoring](#cascade-orchestration--scoring)
- [Index Persistence & Versioning](#index-persistence--versioning)
- [Hot-Reload & Search Pipeline](#hot-reload--search-pipeline)
- [Performance Characteristics](#performance-characteristics)
- [Configuration Reference](#configuration-reference)
- [References](#references)
- [Glossary](#glossary)

## Architecture Overview

The cascade topology is sequential with early termination:

```
Query → Normalize → Exact (marisa-trie)
                  → Prefix (marisa-trie)
                  → Substring (suffix array, if |query| >= 3)
                  → Fuzzy (ffuzzy: SymSpell + BK-tree + 3.5-gram + phonetic)
                  → Semantic (FAISS, quality-gated)
                  → Deduplicate (METHOD_PRIORITY)
                  → Sort (score + METHOD_SORT_BONUS)
                  → Top N
```

A cascade, not a parallel fan-out. Exact match is the common case—roughly 60-70% of lookup queries hit an exact match on the first try, returning in under 1ms. Running all five methods in parallel would waste CPU on the remaining four for no benefit. The cascade only engages expensive methods when cheaper ones come up short.

Four search modes control routing:

| Mode | Behavior |
|------|----------|
| `SMART` | Full cascade with early termination and quality gating |
| `EXACT` | Only exact match |
| `FUZZY` | Only fuzzy pipeline |
| `SEMANTIC` | Only semantic search (awaits initialization if still building) |

**Component ownership.** The [`Search`](../backend/src/floridify/search/engine.py) orchestrator owns one instance each of [`TrieSearch`](../backend/src/floridify/search/trie/search.py), [`FuzzySearch`](../backend/src/floridify/search/fuzzy/search.py) (a thin Python wrapper around an `ffuzzy.Index`), [`SemanticSearch`](../backend/src/floridify/search/semantic/search.py), and [`SuffixArray`](../backend/src/floridify/search/fuzzy/suffix_array.py). It delegates to each in turn, aggregates their results, deduplicates, and returns a ranked list of [`SearchResult`](../backend/src/floridify/search/result.py) objects. Each result carries the matched word, a score in [0, 1], the search method that produced it, an optional lemmatized form, and language metadata.

**Normalization boundary.** Query normalization happens exactly once, at the `Search` entry point. The `normalize()` function (from `floridify.text`) performs lowercase conversion, diacritic stripping, contraction expansion, and Unicode normalization. Results are mapped back to original forms with diacritics via a pre-built `normalized_to_original` dictionary on the corpus. This ensures that searches for "cafe," "café," "CAFE," and "Café" all match the same entry, while the user sees "café" in the results.

**Index lifecycle.** On startup, `SearchEngineManager` builds a `LanguageSearch` wrapper around `Search`. The `Search.initialize()` method loads or constructs a `TrieIndex`, `FuzzyIndex`, and (asynchronously) a `SemanticIndex`. All indices are keyed by `vocabulary_hash`—a content-addressable hash of the corpus vocabulary. If the hash matches a persisted index, the cached version is loaded; otherwise, the index is rebuilt from scratch. Semantic initialization runs in a background `asyncio.Task` so that exact, prefix, substring, and fuzzy search are available immediately while embeddings are being computed—a process that can take minutes for large corpora.

**Caching layers.** Search instances are cached at two levels. A module-level `_search_instance_cache` in [`cache.py`](../backend/src/floridify/search/cache.py) maps `(corpus_name, semantic_model)` tuples to initialized `Search` instances, avoiding repeated initialization for the same corpus. A higher-level `_language_search_cache` in [`language.py`](../backend/src/floridify/search/language.py) maps language tuples to `LanguageSearch` wrappers. Both caches are invalidated on hot reload.

## Exact & Prefix Search: marisa-Trie

Exact and prefix search use [marisa-trie](https://github.com/pytries/marisa-trie), a C++ implementation of the LOUDS-based succinct trie described by [Yata et al. (2007)](#references). LOUDS (Level-Ordered Unary Degree Sequence) encodes the trie structure as a bit vector, storing only ~2 bits per node plus the labels themselves. For a vocabulary of 500,000 words, the marisa-trie consumes roughly 20MB—approximately 5x less than an equivalent Python `dict` or `set`, which pays the overhead of per-object pointers, hash tables, and reference counts.

**Exact lookup** is O(m) where m is the query length. The implementation in [`TrieSearch.search_exact()`](../backend/src/floridify/search/trie/search.py) normalizes the query, checks the Bloom filter (see next section), and then calls `marisa_trie.Trie.__contains__()`. If the trie confirms membership, the normalized key is returned; the caller maps it back to the original form with diacritics via a pre-built `normalized_to_original` dictionary.

**Prefix enumeration** calls `marisa_trie.Trie.keys(prefix)`, which traverses the subtree rooted at the prefix node. Results are ranked by word frequency. For small result sets (fewer than `max_results`), a simple Python sort suffices; for large sets, `numpy.argsort` over the frequency array avoids the overhead of Python comparison functions.

marisa-trie was chosen over a Python `dict` for two reasons: memory and prefix enumeration. A `dict` can answer membership queries in O(1) amortized time, but it can't enumerate prefixes without scanning all keys. marisa-trie provides native prefix enumeration through its tree structure—the same operation that would require a separate data structure (e.g., a sorted list with binary search) is built into the trie's topology.

**Build time** is O(n * m) where n is the vocabulary size and m is the average word length. The [`TrieIndex.create()`](../backend/src/floridify/search/trie/index.py) method sorts the vocabulary (a requirement for marisa-trie's construction algorithm), builds a frequency map using heuristic scoring for words without corpus frequency data, and constructs the `normalized_to_original` mapping from the corpus's index-based mapping.

## Bloom Filter

Before touching the trie, exact search checks a Bloom filter—a probabilistic data structure that answers "is this element in the set?" with no false negatives and a controlled false positive rate. If the filter says "no," the word is definitely not in the vocabulary, and the more expensive trie lookup is skipped. This pre-test saves ~30-50% of search time for non-existent words, which represent the majority of queries in a fuzzy search context (most candidate words aren't exact matches).

### Information-Theoretic Foundations

A Bloom filter [Bloom (1970)](#references) is a bit array of m bits with k independent hash functions. To insert an element, compute k hash positions and set those bits. To query, check whether all k positions are set—if any is clear, the element is definitely absent.

**Optimal bit count.** For n expected elements and target false positive rate p:

```
m = -n * ln(p) / (ln 2)²
```

This minimizes the bit array size for the desired error rate. For n = 100,000 and p = 0.01, m ≈ 958,506 bits (≈117 KB).

**Optimal hash count.** Given m bits and n elements:

```
k = (m / n) * ln 2
```

For the parameters above, k ≈ 7 hash functions.

**False positive rate.** After inserting n elements into an m-bit array with k hash functions, the probability of a false positive is:

```
p_fp = (1 - e^(-kn/m))^k
```

The [`BloomFilter`](../backend/src/floridify/search/trie/bloom.py) implementation uses [xxHash](https://github.com/Cyan4973/xxHash) (xxh64) with different seeds for each of the k hash functions. xxHash is a non-cryptographic hash optimized for speed—its C implementation produces 64-bit digests in single-digit nanoseconds per call, making the k-hash computation negligible relative to even a cache-friendly trie lookup.

### Tiered Error Rates

The system selects error rates by corpus size to balance memory against false positive cost:

| Corpus Size | Error Rate | Memory per Element |
|-------------|------------|--------------------|
| < 10,000 | 0.001 (0.1%) | ~1.8 bytes |
| 10,000 – 100,000 | 0.01 (1%) | ~1.2 bytes |
| > 100,000 | 0.05 (5%) | ~0.8 bytes |

Smaller corpora can afford tighter error rates because the total memory is small regardless. Larger corpora use looser rates to keep the filter compact—a false positive merely triggers an unnecessary (but fast) trie lookup, so the cost of occasional false positives is low.

**Persistence.** The Bloom filter's bit array, hash count, and parameters are serialized alongside the `TrieIndex`. On reload, the filter is restored from the persisted bytes rather than rebuilt from the vocabulary.

## Substring Search: Suffix Arrays

When a user searches for "graph," they may want "paragraph," "grapheme," or "bibliography." Substring search finds all vocabulary words containing the query as an infix.

The implementation uses suffix arrays—a space-efficient alternative to suffix trees that provides the same O(m log n) query time with better cache locality and O(n) space overhead [Karkkainen & Sanders (2003)](#references).

### Construction

The [`SuffixArray`](../backend/src/floridify/search/fuzzy/suffix_array.py) class concatenates all vocabulary words into a single byte string with null-byte sentinels: `"word1\0word2\0word3\0..."`. It then constructs a suffix array over this text using [pydivsufsort](https://github.com/louisabraham/pydivsufsort), a Python binding for [libdivsufsort](https://github.com/y-256/libdivsufsort), which implements the SA-IS algorithm for O(n) suffix array construction.

Two auxiliary structures support O(1) lookups during queries:

- **`_word_starts`**: An array of byte offsets where each word begins in the concatenated text. Built in O(n) with a single scan.
- **`_suffix_to_word`**: A reverse mapping from every text position to its vocabulary word index, using `bisect.bisect_right` over `_word_starts` during construction.

The total space is dominated by the suffix array itself (one int64 per byte of text) plus the reverse mapping (one int32 per byte). For a 500,000-word vocabulary with average word length 8, this is approximately: text ≈ 4.5MB, suffix array ≈ 36MB, reverse map ≈ 18MB.

Why suffix arrays over suffix trees? Suffix trees store explicit edge labels and child pointers, consuming 10-20 bytes per character. Suffix arrays store only a permutation of indices—8 bytes per character for int64—with no pointer overhead. The sorted order also means linear scans through matching suffixes exhibit excellent cache locality, as explored by [Abouelhoda et al. (2004)](#references).

### Query

A substring query performs two binary searches over the suffix array—a technique sometimes called "twin binary search"—to find the leftmost and rightmost suffixes that begin with the query bytes. The first binary search finds the leftmost suffix >= query; the second finds the first suffix > query. Every suffix in the range `[left, right)` has the query as a prefix, and by extension the corresponding vocabulary word contains the query as a substring.

The time complexity is O(m * log(n * m̄)) where m is the query length and n * m̄ is the total text length (n words of average length m̄). Each binary search iteration compares m bytes, and there are O(log(n * m̄)) iterations.

Matches that span word boundaries (contain a null sentinel) are rejected. Exact matches (where the word equals the query) are excluded to avoid duplicating results from exact search. The `_suffix_to_word` reverse mapping converts text positions to vocabulary indices in O(1).

Each match is scored by **coverage ratio**: `len(query) / len(word)`. Searching for "graph" in "grapheme" gives coverage 5/8 = 0.625, while "graph" in "bibliography" gives 5/12 ≈ 0.417. Higher coverage means the query explains more of the word, so it ranks first.

When invoked from the cascade orchestrator (`search_substring()`), results receive a composite score blending coverage (70%) with position bonus (30%)—matches occurring earlier in the word score higher, reflecting the intuition that "graph" appearing at position 0 in "grapheme" is more relevant than at position 6 in "bibliography."

A fallback path handles queries shorter than 3 characters (which can't form trigrams) by direct substring scan over the vocabulary.

## Fuzzy Search: the `ffuzzy` crate

Fuzzy search handles the case where the user has misspelled a word, transposed characters, or used a phonetically plausible but orthographically incorrect variant. The entire fuzzy stage is the [`ffuzzy`](https://github.com/mkbabb/ffuzzy) Rust crate, loaded from Python via PyO3 and driven from a thin wrapper at [`FuzzySearch`](../backend/src/floridify/search/fuzzy/search.py) that maps its `SearchHit` objects into Floridify's `SearchResult`.

`ffuzzy` is a hybrid. No single fuzzy algorithm wins across all query shapes, so it fuses five engines behind an adaptive router:

1. **SymSpell** — precomputed delete variants for O(1) `k ≤ 2` lookup. The hot path for short typos.
2. **Levenshtein automaton + FST** — scaffolded but currently a no-op stub, pending a maintained upstream Rust DFA crate. SymSpell covers the band in the meantime.
3. **BK-tree (Damerau-Levenshtein)** — arena-allocated metric tree with bounded search (node-visit cap + wall-clock time budget + cascading k). Fallback for `k ≥ 3` and long queries.
4. **3.5-gram trigram index** — padded trigrams with 8-bit positional mask plus a 3-bit next-char hash. High-recall candidate pre-filter.
5. **Phonetic (pragmatic Double Metaphone)** — silent-consonant-aware encoder (`kn-`/`ps-`/`wr-`/`gn-`/`pn-`) that catches the sound-alike cases lexical distance misses.

The router orders the engines by `(query_length, adaptive_k)`, aggregates their candidates into a signal map, splits the pool into lexical-only and phonetic-marked halves (phonetic candidates get a relaxed verification bound so equivalents aren't dropped by the strict lexical filter), and runs a SIMD-accelerated Damerau-Levenshtein verification pass. Length correction and multiplicative signal boosts produce the final score.

Full algorithmic details live in the `ffuzzy` repo's docs:

- [`ffuzzy` README](https://github.com/mkbabb/ffuzzy/blob/master/README.md) — public API, installation, and measured results on Floridify's 278K corpus.
- [`ffuzzy` router](https://github.com/mkbabb/ffuzzy/blob/master/docs/router.md) — adaptive engine selection, aggregation, and the relaxed phonetic bound.
- [`ffuzzy` scoring](https://github.com/mkbabb/ffuzzy/blob/master/docs/scoring.md) — length correction, signal boosts, SIMD verification.
- [`ffuzzy` engines/](https://github.com/mkbabb/ffuzzy/blob/master/docs/engines/) — one file per engine with data structures, algorithms, and code excerpts.
- [`ffuzzy` integration](https://github.com/mkbabb/ffuzzy/blob/master/docs/integration.md) — how Floridify itself wires the crate in via `docker-compose` `additional_contexts`, a uv path source, and versioned MongoDB blob storage.

### Adaptive k

The maximum edit distance scales with query length (`ffuzzy-core::lib::adaptive_max_distance`):

```
max_k = min(5, max(2, ceil(query_length * 0.35)))
```

This yields k=2 for 1-4 character queries, k=2-3 for 5-8 characters, k=3-4 for 9-14 characters, and k=4-5 for 15+ characters. Shorter words tolerate fewer edits because a single edit represents a larger fraction of the word. Callers can override it via `SearchConfig.max_distance` (`max_distance=` keyword on the Python API).

### Damerau-Levenshtein, not plain Levenshtein

`ffuzzy` uses Damerau-Levenshtein distance rather than standard Levenshtein. The critical difference: DL treats a transposition of two adjacent characters as a single edit (cost 1), while plain Levenshtein decomposes it into a deletion plus an insertion (cost 2). Transpositions are the most common single-keystroke error — `teh` for the, `recieve` for receive — and penalizing them as two edits inflates distances and degrades recall for the most frequent class of typos [Damerau (1964)](#references), [Levenshtein (1966)](#references).

The BK-tree uses scalar DL via the `strsim` crate for correctness during tree traversal. Candidate verification on the hot path uses SIMD restricted DL via `triple_accel::levenshtein_exp`, with a scalar cross-check on very short strings where restricted DL can diverge from full DL.

### BK-tree, bounded

Classical BK-trees [Burkhard & Keller (1973)](#references) prune the search space via the triangle inequality: compute `d = DL(root, q)`, recurse only into children whose edge labels fall in `[d - k, d + k]`. Unbounded, the worst case scans most of the tree on high-k long queries. `ffuzzy`'s BK-tree bounds the recursion in three dimensions:

- **Node visit cap** (default 50,000) — stops the traversal after a fixed number of visited nodes and returns partial results.
- **Wall-clock time budget** (default 10ms) — checked every 256 visits, stops mid-traversal if exceeded.
- **Cascading k** — starts at k=1 and expands only when fewer than `min_candidates` (default 10) results have been found, up to the adaptive max.

The nodes live in a contiguous `Vec<Node>` arena with sorted `Vec<(u8, u32)>` children, eliminating pointer-chasing on every visit. There is no 20-character query-length cap; long misspellings run against the bounded search and return whatever fits within the budget.

### The "3.5-gram" trigram index

Padded trigrams (`"##cat##"` → `["##c", "#ca", "cat", "at#", "t##"]`) map to posting lists keyed on a compact record:

```rust
#[repr(C)]
pub struct Posting {
    pub idx: u32,       // vocabulary word index
    pub loc: u8,        // positional mask: bit (i & 7) for each position
    pub nxt: u8,        // 3-bit hash of the next character, packed in 8 bits
    pub _reserved: u16, // padding to 8 bytes
}
```

At query time, each trigram's posting list is filtered by bitwise intersection against the query's positional and next-char masks: `(p.loc & query_loc_bit) != 0 && (p.nxt & query_nxt_bit) != 0`. The overlap threshold is `max(2, n_trigrams / 3)` — a 6-trigram query needs 2 mask-passing trigrams, a 12-trigram query needs 4. The design borrows from GitHub's code search trigram architecture, adapted for natural-language fuzzy matching rather than source tokens.

When the trigram pass produces fewer candidates than the budget, the remainder is filled via round-robin over **length buckets** (`AHashMap<u32, Vec<u32>>`, sorted word indices by byte length), within a `±length_tolerance` window (default 2). Round-robin matters because a single bucket (L=5 English words, for example) would otherwise swamp the pool and drown out adjacent lengths.

### Signal-based score boosting

Each engine tags its candidates in a shared signal map (`CandidateSignals { edit_distance, phonetic_match, trigram_overlap, symspell_match, automaton_match }`). After SIMD DL verification and length correction, the scoring pipeline applies multiplicative boosts:

| Signal | Boost | Rationale |
|--------|-------|-----------|
| Phonetic match | ×1.12 | Candidate sounds right — strong signal for homophones and near-homophones |
| Edit distance ≤ 1 | ×1.02 | Very close in edit space — modest tiebreaker |
| SymSpell hit | ×1.01 | Authoritative k≤2 lookup — tiny bump |
| 3+ engines found candidate | ×1.03 | Multiple independent engines converging = high confidence |

All boosts clamp to 1.0 at each step. They act as tiebreakers between candidates of similar corrected quality rather than overriding the base scoring. The phonetic boost is ×1.12 (up from the Python baseline's ×1.08) because the prior value was insufficient to move `filosofy`→philosophy ahead of `filosofy`→falsify in the final ranking. Length correction is a linear ramp: factor `1.0` when `len_ratio ≥ 0.75`, falling linearly to `0.85` at ratio 0.

## Phonetic Search

The phonetic engine lives inside `ffuzzy` alongside the rest and runs in parallel as an orthogonal recall signal. Its job is to catch sound-alike misspellings that lexical distance cannot see: `filosofy` finding philosophy, `knite` finding knight, `sycology` finding psychology, `noledge` finding knowledge.

The implementation is a pragmatic Double Metaphone port with explicit silent-consonant collapse at word start — the fix for the specific regression the Python baseline had:

```rust
let start = if n >= 2 {
    match (chars[0], chars[1]) {
        ('k', 'n') => 1, // knite → nite
        ('p', 'n') => 1, // pneumonia → neumonia
        ('p', 's') => 1, // psychology → sychology
        ('w', 'r') => 1, // wrong → rong
        ('g', 'n') => 1, // gnome → nome
        _ => 0,
    }
} else {
    0
};
```

The main Metaphone loop then walks from `start`, so `knight` and `knite` both encode to `NT`, `psychology` and `sycology` collapse to the same code, and so on. The inverted index (`AHashMap<String, SmallVec<[u32; 4]>>`) maps each code to the vocabulary entries that encode to it. Lookup is a single Metaphone call + a hash lookup.

Candidates surfaced only by the phonetic engine can have large lexical distances (`knite` → knight is DL=2, `sycology` → psychology is DL=3, and bigger cases go further). The router handles this by verifying phonetic-marked candidates against a relaxed bound `max(max_k, query_len / 2 + 1)` so phonetic equivalents aren't killed by the strict lexical filter.

The Python baseline's ICU-based cross-linguistic normalization pipeline (French nasal vowels, German consonant clusters, `ph → f`, `ght → t`, and friends) is *not* carried over into `ffuzzy`. The current phonetic engine is English-first, and the silent-consonant fix is the primary contribution over the Python baseline. If cross-linguistic phonetic matching becomes load-bearing again, the `PhoneticIndex` interface is agnostic to the encoder — the ICU pipeline can be ported in behind the same inverted-index layer without touching the router or the scoring stages.

Details: [`ffuzzy` engines/phonetic.md](https://github.com/mkbabb/ffuzzy/blob/master/docs/engines/phonetic.md).

## Semantic Search

When all surface-level methods fail—when the user types "happy" looking for "felicitous," or "quick" looking for "expeditious"—semantic search uses dense vector similarity to find words with related meanings.

### Embedding Model

The system supports a catalog of embedding models, defined in [`semantic/constants.py`](../backend/src/floridify/search/semantic/constants.py):

| Model | Parameters | Native Dim | MTEB Score | MRL Range |
|-------|-----------|-----------|------------|-----------|
| Qwen3-Embedding-0.6B | 600M | 1024 | 64.33 | 32–1024 |
| Qwen3-Embedding-4B | 4B | 2560 | 69.45 | 32–2560 |
| Qwen3-Embedding-8B | 8B | 4096 | 70.58 | 32–4096 |
| BAAI/bge-m3 | ~560M | 1024 |—|—|
| all-MiniLM-L6-v2 | 22M | 384 |—|—|
| gte-Qwen2-1.5B | 1.5B | 1536 | 67.16 |—|

The default is **Qwen3-Embedding-0.6B**, chosen for its balance of quality, speed, and cross-lingual capability.

Qwen3-Embedding supports Matryoshka Representation Learning (MRL) [Kusupati et al. (2022)](#references), which trains embeddings such that the first d dimensions of a d'-dimensional vector (d < d') form a valid embedding in their own right. The system truncates from 1024D to 512D (`MATRYOSHKA_DIM=512`), halving memory and storage with less than 1% quality degradation on semantic similarity tasks. After truncation, vectors are re-normalized to unit length.

The [`SemanticEncoder`](../backend/src/floridify/search/semantic/encoder.py) handles model initialization, device detection (CUDA if available, CPU otherwise; MPS on Apple Silicon is currently slower than CPU for this model size), and text-to-embedding conversion. Encoding uses `sentence-transformers`' `.encode()` with float32 precision and L2 normalization. INT8 quantization is disabled—sentence-transformers computes calibration ranges from the encoding batch, and single-word vocabularies produce too narrow a value distribution, causing catastrophic score compression.

**Multiprocessing.** For corpora exceeding 5,000 words on CPU, the encoder splits the vocabulary into chunks and distributes them across a `multiprocessing.Pool`. On Linux (Docker), fork-based workers share the model via copy-on-write. On macOS, spawn-based workers each load their own copy of the model—capped at 2 workers to avoid OOM.

### FAISS Index Selection

The [`build_optimized_index()`](../backend/src/floridify/search/semantic/index_builder.py) function selects a FAISS index topology based on corpus size, following a five-tier strategy [Johnson, Douze & Jegou (2019)](#references):

| Corpus Size | Index Type | Parameters | Memory | Quality Loss |
|-------------|-----------|------------|--------|-------------|
| < 10,000 | `IndexFlatL2` |—| 100% baseline | 0% (exact) |
| 10,000 – 50,000 | `IndexIVFFlat` | nlist=max(64, sqrt(n)), nprobe=nlist/4 | ~105% baseline | < 0.1% |
| 50,000 – 100,000 | `IndexScalarQuantizer` INT8 | QT_8bit | 25% baseline | ~1-2% |
| 100,000 – 200,000 | `IndexHNSWFlat` (default) or `IndexIVFPQ` | M=32, efConstruction=200, efSearch=64 | ~110% baseline (HNSW) | ~2-3% |
| > 200,000 | OPQ + `IndexIVFPQ` | OPQ rotation, nlist=n/25, m=64, nbits=8 | ~3% baseline | ~10-15% |

**Memory estimates** for a 512D embedding space (at MATRYOSHKA_DIM=512):

| Corpus | Flat (MB) | IVF-Flat (MB) | SQ-INT8 (MB) | HNSW (MB) | OPQ+IVF-PQ (MB) |
|--------|-----------|---------------|--------------|-----------|------------------|
| 10K | 20 | 21 | 5 |—|—|
| 50K | 100 | 105 | 25 |—|—|
| 100K | 200 |—| 50 | 220 |—|
| 300K |—|—|—|—| 9 |

Why HNSW at 100K-200K but OPQ+IVF-PQ above 200K? HNSW [Malkov & Yashunin (2018)](#references) builds a hierarchical graph where each vector connects to M neighbors per layer. Queries navigate the graph from coarse to fine layers, achieving logarithmic search time. At 100K-200K, the graph fits comfortably in memory and provides 3-5x speedup with only 2-3% recall degradation. Above 200K, the graph's memory overhead (approximately `4 + 2*M` bytes per vector per layer) becomes significant, and product quantization offers better compression: 64 subquantizers with 8-bit codebooks compress each vector from 2048 bytes to 64 bytes (97% reduction). OPQ (Optimized Product Quantization) pre-rotates the vector space to align with subquantizer boundaries, recovering some of the quality lost to quantization.

HNSW parameters are configurable via environment variables: `FLORIDIFY_USE_HNSW`, `FLORIDIFY_HNSW_M` (default 32), `FLORIDIFY_HNSW_EF_CONSTRUCTION` (200), `FLORIDIFY_HNSW_EF_SEARCH` (64).

### L2 Distance to Similarity Conversion

FAISS searches in L2 (Euclidean) distance space. For unit-normalized vectors, L2 distance ranges from 0 (identical) to 2 (maximally dissimilar), and relates to cosine similarity as: `cos_sim = 1 - d_L2² / 2`. The system converts L2 distances to similarity scores via:

```
similarity = 1 - (distance / 2)
```

where the divisor `L2_DISTANCE_NORMALIZATION = 2` normalizes the range to [0, 1].

### In-Vocabulary O(1) Lookup

For queries that exist in the vocabulary, semantic search skips the transformer entirely. The [`_lookup_vocab_embedding()`](../backend/src/floridify/search/semantic/search.py) method performs three O(1) lookups:

1. `corpus.vocabulary_to_index[normalize(query)]` → word index
2. `corpus.word_to_lemma_indices[word_idx]` → lemma index
3. `sentence_embeddings[lemma_idx]` → pre-computed embedding

This reduces semantic search latency for known words from ~10-50ms (transformer inference) to ~0.001ms (array access).

### Incremental Updates

For corpora under 50,000 words, the system maintains a per-word embedding cache (`dict[str, np.ndarray]`). When the corpus changes, it computes the diff (added/removed words), encodes only the new words, removes deleted entries from the cache, rebuilds the embedding matrix in corpus order, and constructs a fresh FAISS index. The FAISS rebuild is cheap—sub-millisecond for < 50K vectors with `IndexFlatL2`. Above 50K, a full rebuild is triggered.

### Query & Result Caching

The [`SemanticQueryCache`](../backend/src/floridify/search/semantic/query_cache.py) maintains two LRU caches:

- **Query embedding cache** (100 entries): Maps query strings to their computed embeddings. Avoids re-encoding the same query.
- **Result cache** (500 entries): Maps query strings to their final `SearchResult` lists. The fastest path—a cache hit returns results without touching FAISS at all.

Both caches flush to L2 (disk) storage via a debounced 5-second timer, providing persistence across restarts. Empty results are never cached, preventing poisoning from races during semantic initialization.

## Cascade Orchestration & Scoring

The [`_smart_search_cascade()`](../backend/src/floridify/search/engine.py) method in `Search` implements the full cascade logic. The key decisions:

### Always Run Prefix

Unlike a pure cascade that terminates as soon as any method finds results, the smart cascade *always* runs prefix search alongside exact search. For autocomplete UX, users expect to see words that start with their query ("de" → "deer," "dear," "deep"), not just an exact match. Prefix search is cheap (marisa-trie) and essential for the frontend search dropdown.

### Early Termination

If exact + prefix results fill `max_results`, the cascade terminates without running substring, fuzzy, or semantic search. This is the common case for queries that are valid prefixes—fast termination avoids unnecessary computation.

### Quality Gating for Semantic

Semantic search is expensive (transformer inference on cache miss) and can produce false positives for short queries ("exampl" → "table" at 73% similarity). The cascade applies quality gating:

1. Count high-quality fuzzy results (score >= `HIGH_QUALITY_FUZZY_SCORE` = 0.7).
2. Compute `semantic_limit = max_results - |high_quality| - |prefix| - |exact|`.
3. If `semantic_limit <= 0`, skip semantic search entirely.
4. If no text-based results exist at all, require a higher minimum semantic score (`SEMANTIC_FALLBACK_MIN_SCORE` = 0.75) to prevent garbage results.

**Strict score floors.** Semantic results must exceed `SEMANTIC_SINGLE_WORD_MIN_SCORE` (0.78) for single-word queries or `SEMANTIC_PHRASE_MIN_SCORE` (0.72) for multi-word queries. For small corpora (< 2,000 words), the sparse embedding space inflates similarity scores—unrelated words can score 0.80+ simply because there aren't enough neighbors to push them down. The floors are raised to 0.82 (word) and 0.78 (phrase) for these corpora.

**Lexical sanity gate.** Even with score floors, semantic search can return textually unrelated results. A `SequenceMatcher` check rejects candidates where the lexical similarity to the query is below `LEXICAL_SANITY_THRESHOLD` (0.35) unless their semantic score exceeds the floor by at least `LEXICAL_GATE_SCORE_MARGIN` (0.05). This prevents "knife" from appearing in results for "table" at borderline similarity scores.

### Deduplication

When the same word is found by multiple methods (exact and prefix, fuzzy and semantic), the cascade deduplicates using `METHOD_PRIORITY`:

| Method | Priority |
|--------|----------|
| EXACT | 5 |
| PREFIX | 4 |
| SUBSTRING | 3 |
| SEMANTIC | 2 |
| FUZZY | 1 |

For duplicate words (case-insensitive), the result with the highest priority method wins. If priorities are equal, the higher score wins. In `collect_all_matches` mode, all (method, score) pairs are preserved as `MatchDetail` objects on the result, but the primary method is still the highest-priority one.

### Sort Tiebreaker

Final sorting uses `score + METHOD_SORT_BONUS`:

| Method | Bonus |
|--------|-------|
| EXACT | +0.03 |
| PREFIX | +0.02 |
| SUBSTRING | +0.015 |
| SEMANTIC | +0.01 |
| FUZZY | +0.00 |

These bonuses are small enough to never override a genuinely better score—a fuzzy match at 0.95 still beats a semantic match at 0.80—but they break ties in favor of more trustworthy methods. A prefix match at 0.90 sorts ahead of a fuzzy match at 0.90.

## Index Persistence & Versioning

All search indices participate in the project's three-level versioned storage system (see [docs/versioning.md](versioning.md)). The hierarchy is:

```
SearchIndex (top-level, links component indices by ID)
├── TrieIndex (marisa-trie data, frequencies, Bloom filter bytes)
├── FuzzyIndex (ffuzzy blob + pickled SuffixArray, binary via GridFS)
└── SemanticIndex (FAISS index + embeddings via GridFS)
```

Each index type extends `BaseVersionedData` with a `Metadata` inner class, providing:

- **Resource ID**: `{corpus_uuid}:{type}` (e.g., `abc123:trie`, `abc123:fuzzy`, `abc123:semantic`)
- **Vocabulary hash**: SHA-256 of the sorted vocabulary, used for cache invalidation. If the hash matches, the persisted index is valid; if not, it's rebuilt.
- **Version tracking**: Semantic versioning with `is_latest` flag for efficient "get latest" queries.

**TrieIndex persistence.** The trie data (sorted word list), word frequencies, normalized-to-original mapping, and Bloom filter bytes are stored as JSON via the versioned content manager. The Bloom filter's `bytearray` is persisted alongside its parameters (bit count, hash count, item count, error rate) so it can be restored without recomputation.

**FuzzyIndex persistence.** The `ffuzzy.Index` is serialized by Rust into a single opaque byte blob via `to_bytes()` (bincode format with a schema version byte; see [`ffuzzy` docs/format.md](https://github.com/mkbabb/ffuzzy/blob/master/docs/format.md)). That blob plus a pickled `SuffixArray` are handed to the version manager's `binary_payload` hook, which routes them to GridFS in a single atomic write. The small metadata document (corpus ID, vocabulary hash, size stats, build time) stays inline. On load, the manager rehydrates the binary dict from GridFS and `FuzzyIndex.deserialize()` calls `ffuzzy.Index.from_bytes()` to reconstruct the Rust index. A schema mismatch surfaces as a `ValueError` and triggers a rebuild from the live vocabulary.

**SemanticIndex persistence.** Embeddings and FAISS index data are stored as binary blobs via the GridFS-backed external storage system. The `SemanticIndex.binary_data` field (excluded from `model_dump()`) holds references to the externally stored bytes. The resource ID includes the model name and a vocabulary hash prefix to support coexistence of indices built with different models or Matryoshka dimensions.

**Inline vs. external storage.** Content smaller than `INLINE_CONTENT_THRESHOLD_BYTES` (16 KB) is stored inline in the MongoDB document. Larger content—which includes all semantic data—is stored externally via GridFS, referenced by a `ContentLocation` object in the metadata.

## Hot-Reload & Search Pipeline

The [`SearchEngineManager`](../backend/src/floridify/core/search_pipeline.py) is a singleton that manages the search engine's lifecycle with periodic corpus change detection and atomic engine replacement.

### Fingerprinting

The manager maintains a `_CorpusFingerprint` containing the corpus name, vocabulary hash, and version string. On each check, it queries the `BaseVersionedData` collection for the latest version of the corpus and compares the hash and version against the stored fingerprint.

### Polling Cycle

The check runs at most once per `CORPUS_CHECK_INTERVAL_SECONDS` (30 seconds). The hot path cost is a single `time.monotonic()` call (~10ns). If within the interval, the cached engine is returned immediately.

When the interval elapses:

1. Query MongoDB for the current corpus metadata (~1-2ms, indexed query on `resource_id` + `is_latest`).
2. Compare vocabulary hash and version against fingerprint.
3. If unchanged, update `_last_check` and return the cached engine.
4. If changed, initiate hot reload.

### Hot Reload

Hot reload runs under an `asyncio.Lock` with double-check-after-lock to handle concurrent coroutines:

1. Acquire lock.
2. Re-check if corpus changed (another coroutine may have already reloaded).
3. Clear the language search cache and search instance cache.
4. Build a new `LanguageSearch` with `force_rebuild=True`.
5. Atomic swap: update `self._engine`, `self._fingerprint`, `self._last_check`.
6. Release lock.

The old engine continues serving requests until step 5 completes. There is no downtime window.

### Background Initialization

On application startup (during the FastAPI lifespan), `SearchEngineManager.start_background_init()` creates an `asyncio.Task` that builds the initial search engine. The task calls `get_language_search()`, which creates the language corpus (aggregating vocabulary sources), builds the trie and fuzzy indices, and kicks off background semantic initialization.

Requests arriving before initialization completes will `await self._init_task`—they block without spinning. If background init fails, the error message is stored in `_init_error` and retried inline on the next `get_engine()` call, providing resilient startup behavior.

### Semantic Initialization Lock

Semantic index construction is the most expensive operation in the search system (minutes for large corpora). It runs in a background `asyncio.Task` managed by `Search._semantic_init_task`. A dedicated `asyncio.Lock` (`_semantic_init_lock`) prevents race conditions: concurrent callers that check `_semantic_ready` and decide to start initialization are serialized through the lock. The lock also protects the atomic state transition from "building" to "ready," ensuring no reader observes a partially-initialized semantic engine.

If semantic initialization fails, the error is recorded in `_semantic_init_error` and the engine continues to serve exact, prefix, substring, and fuzzy search. Semantic-specific requests (`SearchMode.SEMANTIC`) will await the init task and raise if it failed.

## Performance Characteristics

| Method | Build Complexity | Query Complexity | Space Complexity |
|--------|-----------------|------------------|------------------|
| Exact (marisa-trie) | O(n * m) | O(m) | O(n * m) succinct |
| Prefix (marisa-trie) |—(shared with exact) | O(m + k) where k = results |—(shared) |
| Bloom filter | O(n * k_hash) | O(k_hash) | O(n) bits |
| Substring (suffix array) | O(n * m) via SA-IS | O(m * log(n * m)) | O(n * m) |
| ffuzzy SymSpell (k≤2) | O(n * m^2) parallel | O(1) amortized hashmap | O(n * m^2) variants |
| ffuzzy BK-tree (bounded) | O(n * h) serial | O(min(max_visits, n^(k/log n))) | O(n) arena nodes |
| ffuzzy 3.5-gram trigram | O(n * m) | O(t * p̄) where t=trigrams, p̄=avg posting length | O(n * m) postings |
| ffuzzy phonetic index | O(n) | O(1) hashmap | O(n) |
| Semantic (FAISS Flat) | O(n * d) | O(n * d) brute force | O(n * d) |
| Semantic (FAISS HNSW) | O(n * M * log n) | O(d * log n) | O(n * (d + M)) |
| Semantic (FAISS OPQ+IVF-PQ) | O(n * d) + training | O(d * nprobe) | O(n * m_pq * nbits/8) |

**Profiled numbers** (Apple M4 Max, Qwen3-0.6B, 278K word English corpus):

| Operation | Time | Notes |
|-----------|------|-------|
| Exact lookup (trie + Bloom) | ~0.001ms | Two O(m) passes: Bloom filter then trie |
| Prefix search (20 results) | ~0.001ms | marisa-trie C++ traversal |
| Substring search (suffix array) | ~1ms | Twin binary search over ~4.5MB text |
| Fuzzy search, short typo (`algorythm`) | ~12ms server-side | ffuzzy: SymSpell authoritative, no BK-tree fire |
| Fuzzy search, phonetic (`sycology`/`noledge`) | ~12-13ms server-side | ffuzzy: phonetic + relaxed DL verify |
| Fuzzy search, long misspelling (`antidisestablishmentarianizm`) | ~15-25ms server-side | ffuzzy: BK-tree bounded traversal, no 20-char cap |
| Fuzzy search, multi-word phrase (`en couliss`) | ~13ms server-side, p95 flat | ffuzzy: was ~31ms / p95 403ms in Python baseline |
| Semantic search (FAISS, result cache hit) | ~0.001ms | LRU dict lookup |
| Semantic search (FAISS, vocab embedding hit) | ~0.1ms | O(1) array access + FAISS query |
| Semantic search (FAISS, full encode) | ~10-50ms | Transformer inference + FAISS query |
| Model load (first query) | ~1.5s | Cached after first load |
| Corpus embedding (1,323 words, batch=128) | ~3.3s | 397 words/sec |
| Corpus embedding (5,000 words, batch=128) | ~11.6s | 430 words/sec |
| Full corpus embedding (278K words, batch=128) | ~13min | Multiprocessing, 2 workers (macOS) |
| FAISS index build (FlatL2, 10K vectors, 512D) | ~10ms | Brute-force, no training |
| FAISS index build (HNSW, 100K vectors, 512D) | ~5s | M=32, efConstruction=200 |
| ffuzzy build (278K words) | ~10s | Parallel SymSpell via rayon; BK-tree insertion serial |
| ffuzzy blob deserialize | ~200ms | bincode, single-shot |
| Hot reload (index rebuild) | ~2-5s | Excludes semantic rebuild |
| Corpus change detection | ~1-2ms | Indexed MongoDB query |

Fuzzy numbers above are server-side `X-Process-Time` (whole request, including HTTP middleware, normalization, corpus lookup, serialization). The ffuzzy search itself is sub-millisecond for SymSpell-authoritative k≤2 cases. See [`ffuzzy` docs/motivation.md](https://github.com/mkbabb/ffuzzy/blob/master/docs/motivation.md) for the full benchmark table and the pre-ffuzzy baseline.

**Batch size matters.** On Apple Silicon, `batch_size=128` is 42% faster than `batch_size=32` for the 0.6B model due to better SIMD utilization. Model-specific batch sizes are defined in `MODEL_BATCH_SIZES`. MPS (Apple GPU) is 0.72x the speed of CPU for this model size—the overhead of CPU-GPU data transfer dominates for the relatively small model.

**Memory footprint** for a 278K word corpus at 512D (after Matryoshka truncation):

| Component | Memory |
|-----------|--------|
| Embeddings (float32) | ~545MB |
| FAISS HNSW index | ~20MB overhead |
| Suffix array + reverse map | ~50MB |
| marisa-trie | ~20MB |
| Bloom filter | ~120KB |
| ffuzzy full blob (SymSpell k=2 + BK-tree + 3.5-gram + FST + phonetic) | ~128MB |
| ffuzzy slim (no SymSpell) | ~48MB |

## Configuration Reference

All tunable constants are centralized in [`search/config.py`](../backend/src/floridify/search/config.py):

### Score Thresholds

| Constant | Default | Purpose |
|----------|---------|---------|
| `SEMANTIC_FALLBACK_MIN_SCORE` | 0.75 | Minimum semantic score when no text-based results exist |
| `SEMANTIC_SINGLE_WORD_MIN_SCORE` | 0.78 | Floor for single-word semantic queries |
| `SEMANTIC_PHRASE_MIN_SCORE` | 0.72 | Floor for multi-word semantic queries |
| `SEMANTIC_SMALL_CORPUS_SIZE` | 2,000 | Corpus size below which strict semantic floors apply |
| `SEMANTIC_SMALL_CORPUS_WORD_FLOOR` | 0.82 | Strict word floor for small corpora |
| `SEMANTIC_SMALL_CORPUS_PHRASE_FLOOR` | 0.78 | Strict phrase floor for small corpora |
| `LEXICAL_SANITY_THRESHOLD` | 0.35 | Minimum SequenceMatcher ratio for semantic results |
| `LEXICAL_GATE_SCORE_MARGIN` | 0.05 | Score margin above floor to bypass lexical gate |
| `HIGH_QUALITY_FUZZY_SCORE` | 0.7 | Fuzzy score threshold for quality gating |
| `FUZZY_PERFECT_SCORE` | 0.99 | Score treated as perfect match |

Signal-boost factors (phonetic match, close-edit, multi-engine) live inside the `ffuzzy` crate now. See the [ffuzzy tuning knobs](#ffuzzy-tuning-knobs) table below.

### Corpus Size Thresholds

| Constant | Default | Purpose |
|----------|---------|---------|
| `CORPUS_TINY` | 500 | Below this, use full vocabulary as candidates |
| `CORPUS_SMALL` | 5,000 | Small corpus threshold |
| `CORPUS_MEDIUM` | 50,000 | Medium corpus threshold |
| `CORPUS_LARGE` | 100,000 | Large corpus threshold |
| `CORPUS_XLARGE` | 300,000 | Extra-large corpus threshold |

### ffuzzy tuning knobs

The fuzzy stage is driven by `ffuzzy`, so the previous Python-level constants (`BKTREE_*`, `FUZZY_BUDGET_*`, `TRIGRAM_*`, `PHONETIC_*`, `RAPIDFUZZ_*`) are no longer load-bearing. Tuning now happens inside the Rust crate via `SearchConfig`, `BoundedSearchConfig`, and `CandidateConfig`. The Python PyO3 wrapper (`ffuzzy.Index.search`) exposes the most important knobs as keyword arguments — `max_results`, `min_score`, `max_distance` — and uses `ffuzzy`'s defaults for everything else.

Representative defaults (all configurable via `ffuzzy-core`'s Rust API):

| Knob | Default | Source |
|------|---------|--------|
| `SearchConfig.max_results` | 20 | `ffuzzy-core/src/router/mod.rs` |
| `SearchConfig.min_score` | 0.6 | same |
| `BoundedSearchConfig.max_visits` | 50,000 | `ffuzzy-core/src/bktree/search.rs` |
| `BoundedSearchConfig.time_budget_ms` | 10.0 | same |
| `BoundedSearchConfig.min_candidates` | 10 | same |
| `CandidateConfig.trigram_cap_fraction` | 0.8 | `ffuzzy-core/src/trigram/query.rs` |
| `CandidateConfig.length_tolerance` | 2 | same |
| `BuildConfig.symspell_max_k` | 2 | `ffuzzy-core/src/router/mod.rs` |
| `BuildConfig.symspell_max_word_len` | 30 | same |
| adaptive k formula | `min(5, max(2, ceil(len * 0.35)))` | `ffuzzy-core/src/lib.rs::adaptive_max_distance` |
| Phonetic boost | ×1.12 | `ffuzzy-core/src/score/signals.rs` |
| Close-edit boost (d ≤ 1) | ×1.02 | same |
| Multi-engine boost (≥ 3 engines) | ×1.03 | same |
| SymSpell boost | ×1.01 | same |
| Length correction ramp | `0.85 + 0.15 * (ratio / 0.75)` below 0.75 | `ffuzzy-core/src/score/length_correct.rs` |

Details: [`ffuzzy` docs/scoring.md](https://github.com/mkbabb/ffuzzy/blob/master/docs/scoring.md), [`ffuzzy` docs/engines/](https://github.com/mkbabb/ffuzzy/blob/master/docs/engines/).

### Bloom Filter

| Constant | Default | Purpose |
|----------|---------|---------|
| `BLOOM_SMALL_CORPUS` | 10,000 | Threshold for tight error rate |
| `BLOOM_MEDIUM_CORPUS` | 100,000 | Threshold for medium error rate |
| `BLOOM_ERROR_RATE_SMALL` | 0.001 | Error rate for corpora < 10K |
| `BLOOM_ERROR_RATE_MEDIUM` | 0.01 | Error rate for corpora 10K-100K |
| `BLOOM_ERROR_RATE_LARGE` | 0.05 | Error rate for corpora > 100K |

### Search Pipeline

| Constant | Default | Purpose |
|----------|---------|---------|
| `CORPUS_CHECK_INTERVAL_SECONDS` | 30.0 | Hot-reload polling frequency |
| `INLINE_CONTENT_THRESHOLD_BYTES` | 16,384 | Below this, store content inline in MongoDB |

### Semantic Search (Environment Variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEMANTIC_SEARCH_ENABLED` | `true` | Enable/disable semantic search globally |
| `FLORIDIFY_MATRYOSHKA_DIM` | `512` | Embedding truncation dimension (0 = disable) |
| `FLORIDIFY_USE_HNSW` | `true` | Use HNSW index for 100K-200K corpora |
| `FLORIDIFY_HNSW_M` | `32` | HNSW connections per node |
| `FLORIDIFY_HNSW_EF_CONSTRUCTION` | `200` | HNSW build-time search depth |
| `FLORIDIFY_HNSW_EF_SEARCH` | `64` | HNSW query-time search depth |

## References

- Abouelhoda, M. I., Kurtz, S., & Ohlebusch, E. (2004). Replacing suffix trees with enhanced suffix arrays. *Journal of Discrete Algorithms*, 2(1), 53-86.
- Bloom, B. H. (1970). Space/time trade-offs in hash coding with allowable errors. *Communications of the ACM*, 13(7), 422-426.
- Burkhard, W. A., & Keller, R. M. (1973). Some approaches to best-match file searching. *Communications of the ACM*, 16(4), 230-236.
- Damerau, F. J. (1964). A technique for computer detection and correction of spelling errors. *Communications of the ACM*, 7(3), 171-176.
- GitHub Engineering. (2023). The technology behind GitHub's new code search. https://github.blog/engineering/architecture-optimization/the-technology-behind-githubs-new-code-search/
- Gallant, A. (2023). ripgrep: A line-oriented search tool. https://burntsushi.net/ripgrep/
- Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data*, 7(3), 535-547.
- Kärkkäinen, J., & Sanders, P. (2003). Simple linear work suffix array construction. *International Colloquium on Automata, Languages, and Programming*, 943-955.
- Kusupati, A., Bhatt, G., Rege, A., et al. (2022). Matryoshka representation learning. *Advances in Neural Information Processing Systems*, 35.
- Levenshtein, V. I. (1966). Binary codes capable of correcting deletions, insertions, and reversals. *Soviet Physics Doklady*, 10(8), 707-710.
- Malkov, Y. A., & Yashunin, D. A. (2018). Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 42(4), 824-836.
- Philips, L. (1990). Hanging on the metaphone. *Computer Language Magazine*, 7(12), 38-43.
- Unicode Consortium. CLDR Transliteration Charts. https://cldr.unicode.org/
- Yata, S., Oono, M., Morita, K., Fuketa, M., Sumitomo, T., & Aoe, J. (2007). A compact static double-array keeping character codes. *Information Processing & Management*, 43(1), 237-247.

## Glossary

**BK-tree**: A metric tree that organizes elements by their pairwise distances, exploiting the triangle inequality to prune search space during nearest-neighbor queries.

**Bloom filter**: A probabilistic data structure that tests set membership with no false negatives and a controlled false positive rate, using a bit array and multiple hash functions.

**Cascade**: A sequential execution strategy where methods are tried in order of increasing cost, with early termination when sufficient results are found.

**Damerau-Levenshtein distance**: An edit distance metric that counts insertions, deletions, substitutions, and transpositions of adjacent characters, each as a single operation.

**FAISS**: Facebook AI Similarity Search—a library for efficient similarity search and clustering of dense vectors, supporting exact and approximate nearest neighbor search.

**HNSW**: Hierarchical Navigable Small World—a graph-based approximate nearest neighbor algorithm that builds a multi-layer proximity graph for logarithmic query time.

**IVF (Inverted File)**: A FAISS index structure that partitions vectors into clusters (Voronoi cells) and searches only nearby clusters at query time.

**Matryoshka Representation Learning (MRL)**: A training technique that produces embeddings where any prefix of dimensions forms a valid, lower-dimensional embedding.

**Metaphone**: A phonetic algorithm that encodes words by their English pronunciation, mapping homophones and near-homophones to the same code.

**OPQ (Optimized Product Quantization)**: A rotation applied before product quantization that aligns the vector space with subquantizer boundaries for better reconstruction accuracy.

**Product Quantization (PQ)**: A compression technique that splits vectors into subspaces, quantizes each independently with a codebook, and stores only the codebook indices.

**RapidFuzz**: A C++ library for fast fuzzy string matching, implementing algorithms like WRatio, token_set_ratio, and various edit distance metrics.

**Suffix array**: A sorted array of all suffixes of a text, enabling O(m log n) substring queries via binary search.

**Trigram**: A contiguous sequence of three characters extracted from a string, used for approximate string matching via inverted indexes.

**Vocabulary hash**: A SHA-256 hash of the sorted vocabulary list, used as a content-addressable key for cache invalidation.
