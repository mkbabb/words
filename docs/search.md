# Search

Floridify's search system is a five-method cascade over arbitrary lexicons, designed to answer one question well: given a user's query—correct, misspelled, phonetically approximated, or semantically adjacent—find the vocabulary entry they intended. Each method in the cascade covers a distinct failure mode of the ones before it: exact matching handles the common case in sub-millisecond time, prefix search powers autocomplete, substring search catches infix queries, fuzzy search tolerates typos and transpositions, and semantic search recovers meaning when all surface-level techniques fail.

The system processes corpora from hundreds of words to 300,000+, adapting its data structures, candidate budgets, and FAISS index topology to the scale at hand. All indices are versioned and persisted; a hot-reload mechanism detects vocabulary changes and atomically swaps the search engine without dropping queries.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Exact & Prefix Search: marisa-Trie](#exact--prefix-search-marisa-trie)
- [Bloom Filter](#bloom-filter)
- [Substring Search: Suffix Arrays](#substring-search-suffix-arrays)
- [Fuzzy Search](#fuzzy-search)
  - [BK-Tree](#bk-tree)
  - [Trigram Index with Probabilistic Masks](#trigram-index-with-probabilistic-masks)
  - [Length Buckets & Round-Robin Merging](#length-buckets--round-robin-merging)
  - [RapidFuzz Scoring Pipeline](#rapidfuzz-scoring-pipeline)
  - [Length Correction & Signal-Based Score Boosting](#length-correction--signal-based-score-boosting)
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
                  → Fuzzy (BK-tree + phonetic + trigram → RapidFuzz scoring)
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

**Component ownership.** The [`Search`](../backend/src/floridify/search/engine.py) orchestrator owns one instance each of [`TrieSearch`](../backend/src/floridify/search/trie/search.py), [`FuzzySearch`](../backend/src/floridify/search/fuzzy/search.py), [`SemanticSearch`](../backend/src/floridify/search/semantic/search.py), and [`SuffixArray`](../backend/src/floridify/search/fuzzy/suffix_array.py). It delegates to each in turn, aggregates their results, deduplicates, and returns a ranked list of [`SearchResult`](../backend/src/floridify/search/result.py) objects. Each result carries the matched word, a score in [0, 1], the search method that produced it, an optional lemmatized form, and language metadata.

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

## Fuzzy Search

Fuzzy search handles the case where the user has misspelled a word, transposed characters, or used a phonetically plausible but orthographically incorrect variant. The implementation is a multi-strategy candidate aggregation pipeline: multiple independent strategies each propose candidate vocabulary indices, the candidates are merged into a unified pool, and RapidFuzz scores the pool to produce final results.

The [`FuzzySearch`](../backend/src/floridify/search/fuzzy/search.py) orchestrates four candidate sources:

1. **BK-tree**: Edit distance within an adaptive radius
2. **Phonetic index**: Sound-alike matching via ICU normalization + Metaphone
3. **Trigram index**: Character n-gram overlap with probabilistic masks
4. **Length buckets**: Words of similar length as a fallback

Each strategy writes to a shared `dict[int, CandidateSignals]` mapping vocabulary indices to metadata about which strategies found them. The `CandidateSignals` model tracks four fields: `edit_distance` (int or None), `phonetic_match` (bool), `trigram_overlap` (bool), and `substring_match` (bool). This signals dictionary serves two purposes: it deduplicates candidates across strategies (each index appears at most once in the pool), and it enables score boosting later—candidates found by multiple independent strategies are almost certainly correct matches.

**Scale-aware candidate budgets.** The total candidate pool is capped to prevent RapidFuzz from being overwhelmed. The budget scales with corpus size:

| Corpus Size | Candidate Budget |
|-------------|-----------------|
| < 500 (TINY) | Full vocabulary |
| < 5,000 (SMALL) | 300 |
| < 50,000 (MEDIUM) | 700 |
| < 300,000 (XLARGE) | 1,100 |
| >= 300,000 | 1,700 |

When the candidate pool exceeds the budget, candidates are prioritized by signal strength: BK-tree matches with small edit distance rank highest, followed by phonetic matches, then trigram matches. This ensures the strongest candidates survive truncation.

### BK-Tree

A BK-tree [Burkhard & Keller (1973)](#references) is a metric tree that exploits the triangle inequality of edit distance to prune the search space. Each node stores a word and a dictionary mapping edit distances to child subtrees. To search for all words within distance k of a query q, the algorithm computes d(root, q), adds the root if d ≤ k, then recurses only into children whose edge labels are in the range [d - k, d + k]. By the triangle inequality, children outside this range can't possibly contain words within distance k of q.

The expected number of nodes visited is O(n^(k/log n))—far less than the full n for small k.

**Damerau-Levenshtein distance.** The [`BKTree`](../backend/src/floridify/search/fuzzy/bk_tree.py) uses Damerau-Levenshtein distance rather than standard Levenshtein. The critical difference: DL treats transposition of two adjacent characters as a single edit operation (cost 1), while standard Levenshtein decomposes it into a deletion plus an insertion (cost 2). Transpositions are the most common single-keystroke error—"teh" for "the," "recieve" for "receive"—and penalizing them as two edits inflates distances and degrades recall for the most frequent class of typos [Damerau (1964)](#references), [Levenshtein (1966)](#references). The implementation delegates to RapidFuzz's C++ `DamerauLevenshtein.distance()` for speed.

Why BK-tree over VP-tree? Both are metric trees, but they differ in branching strategy. A VP-tree (vantage-point tree) performs a binary split at each node: points closer than a median distance go left, farther go right. A BK-tree performs a multi-way split on exact distance values, creating one child per distinct distance. For integer metrics like edit distance (which produces discrete values 0, 1, 2, ...), the multi-way split is a natural fit—it partitions the space more finely than a binary split, leading to better pruning when the maximum search distance k is small relative to the tree depth.

**Adaptive k.** The maximum edit distance scales with query length:

```
max_k = min(5, max(2, ceil(query_length * 0.35)))
```

This yields k=2 for 1-4 character queries, k=2-3 for 5-8 characters, k=3-4 for 9-14 characters, and k=4-5 for 15+ characters. Shorter words tolerate fewer edits because a single edit represents a larger fraction of the word. The constants `EDIT_DISTANCE_MIN=2`, `EDIT_DISTANCE_MAX=5`, and `EDIT_DISTANCE_LENGTH_MULTIPLIER=0.35` are configurable.

**Cascading search with time budgets.** The [`cascading_search()`](../backend/src/floridify/search/fuzzy/bk_tree.py) function starts at k=1 and expands to k+1 if fewer than `BKTREE_CASCADE_MIN_CANDIDATES` (10) results are found, up to the adaptive max_k. At each level, the search checks a time budget:

| Corpus Size | Time Budget |
|-------------|-------------|
| < 5,000 | 20ms |
| 5,000 – 50,000 | 10ms |
| > 50,000 | 5ms |

If the budget is exceeded mid-expansion, the search returns the best results found so far. Above `BKTREE_MAX_CORPUS_SIZE` (100,000 words), the BK-tree is skipped entirely—at that scale, the tree is deep enough that even k=1 traversal becomes expensive, and trigram + phonetic strategies provide sufficient recall.

**Build.** `BKTree.build()` inserts words one at a time from a sorted vocabulary, computing a DL distance at each insertion to determine the child slot. Build time is O(n * h) where h is the tree height, typically O(log n) for random vocabularies.

### Trigram Index with Probabilistic Masks

The trigram index is an inverted index mapping character trigrams to the vocabulary words that contain them. Given a query, the system extracts its trigrams, intersects the posting lists, and returns words with sufficient overlap—a standard information retrieval technique. What makes this implementation unusual is the addition of two 8-bit masks per posting that provide sub-trigram positional precision, reducing false positives by 40-60%.

The design draws inspiration from [GitHub's Code Search architecture](https://github.blog/engineering/architecture-optimization/the-technology-behind-githubs-new-code-search/) (2023), which uses similar positional metadata to filter trigram matches.

**Standard trigram indexing.** Each word is padded with sentinel characters (`##word##`) and decomposed into overlapping 3-character sequences. "cat" becomes `["##c", "#ca", "cat", "at#", "t##"]`. The inverted index maps each trigram to the list of vocabulary indices containing it. To query, extract query trigrams, retrieve the posting lists, count how many trigrams each candidate shares with the query, and keep candidates above a threshold.

The problem: short queries produce few trigrams, and common trigrams (like `"the"`) appear in thousands of words. The overlap threshold must be low enough to catch genuine matches but this admits many false positives.

**The "3.5-gram" extension.** Each posting in the index is a structured numpy array with three fields:

```python
POSTING_DTYPE = np.dtype([("idx", np.int32), ("loc", np.uint8), ("nxt", np.uint8)])
```

- **`idx`**: The vocabulary word index (standard).
- **`loc`**: A positional mask. Bit `i % 8` is set for each position i where this trigram appears in the word. This records approximately *where* in the word the trigram occurs.
- **`nxt`**: A next-character mask. Bit `hash(next_char) % 8` is set, where `next_char` is the character immediately following the trigram. This gives "3.5-gram" precision—not quite a full 4-gram, but enough to eliminate candidates where the trigram is followed by a different character than in the query.

At query time, for each query trigram at position i, the system computes `query_loc_bit = 1 << (i & 7)` and `query_nxt_bit = 1 << hash(next_char) & 7`, then filters the posting list using vectorized numpy operations:

```python
loc_match = (posting["loc"] & query_loc_bit).astype(bool)
nxt_match = (posting["nxt"] & query_nxt_bit).astype(bool)
mask_pass = loc_match & nxt_match
```

Only postings that pass both mask checks are counted toward the overlap score. This eliminates candidates where the trigram occurs at a different position or is followed by a different character—a common source of false positives in standard trigram indexes.

**Overlap threshold.** A candidate must match at least `max(2, n_trigrams // 3)` of the query's trigrams (where `n_trigrams` is the total number of query trigrams). The `TRIGRAM_THRESHOLD_DENOMINATOR=3` constant controls this ratio. The trigram candidates are capped at `TRIGRAM_CAP_FRACTION` (0.8) of the total candidate budget, reserving 20% for length-bucket candidates.

**Memory layout.** The structured numpy arrays provide cache-friendly sequential access. For a vocabulary of 100,000 words with an average of 10 trigrams per word, the index contains roughly 1 million postings at 6 bytes each (int32 + uint8 + uint8) = ~6MB. Duplicate (trigram, word_idx) pairs are merged by OR-ing their masks.

### Length Buckets & Round-Robin Merging

Length buckets are the simplest candidate source: a dictionary mapping word lengths to numpy arrays of vocabulary indices. For a query of length L, the system collects words of length L-2 through L+2 (controlled by `length_tolerance`).

The key design decision is how to merge length-bucket candidates with higher-priority candidates from other strategies. Naively concatenating them would let a single large bucket (e.g., 5-letter words, which are extremely common in English) drown out candidates from adjacent buckets. The implementation uses **round-robin interleaving**: it creates iterators over each bucket and takes one unseen candidate from each bucket per round, cycling until the budget is filled.

```
Priority candidates (trigram + BK-tree + phonetic): [a, b, c, d, ...]
Length bucket L-1: [e, f, g, ...]
Length bucket L:   [h, i, j, ...]
Length bucket L+1: [k, l, m, ...]

Merged: [a, b, c, d, ..., e, h, k, f, i, l, g, j, m, ...]
```

This ensures that candidates from nearby lengths are evenly represented in the pool, giving the RapidFuzz scorer a balanced view of the neighborhood.

### RapidFuzz Scoring Pipeline

After candidate aggregation, the pool of candidate words is scored by [RapidFuzz](https://github.com/maxbachmann/RapidFuzz), a C++ implementation of fuzzy string matching.

**Primary scorer: WRatio.** The main scorer is `fuzz.WRatio` (Weighted Ratio), which computes the best score across several strategies (simple ratio, partial ratio, token sort, token set) and returns the maximum. The score cutoff is `min_score * 50` for single words and `min_score * 45` for phrases, preventing low-quality candidates from consuming processing time.

**Secondary scorer: token_set_ratio.** For phrases and long queries (>= 8 characters), a secondary pass uses `fuzz.token_set_ratio`, which decomposes strings into token sets and scores based on set overlap. This catches reorderings ("machine learning" vs "learning machine") that WRatio might miss. Secondary results receive a 1.2x boost (`SECONDARY_RESULT_BOOST`) to compensate for typically lower raw scores.

The secondary pass is skipped when:
- The primary pass already found 3+ results scoring above 0.85 (`STRONG_PRIMARY_SCORE`)
- The query is a short single word (< 6 characters) with existing results
- The query is a single word shorter than 8 characters

**Result limit.** RapidFuzz's `process.extract()` receives a limit of `max_results * multiplier`, where the multiplier is 5 for vocabulary pools > 200 words and 3 for smaller pools.

### Length Correction & Signal-Based Score Boosting

RapidFuzz's WRatio can be biased by length asymmetries. A 3-character candidate matching against a 15-character query can score deceptively high due to partial matching. The [`apply_length_correction()`](../backend/src/floridify/search/fuzzy/scoring.py) function applies multiplicative corrections:

- **Length ratio penalty**: `min(query_len, candidate_len) / max(query_len, candidate_len)`—penalizes large length mismatches.
- **Short fragment penalty**: Candidates <= 3 characters against queries > 6 characters receive a 0.5x penalty.
- **Phrase mismatch penalty**: Query is a phrase but candidate is a single word → 0.7x. Reverse → 0.95x (or 1.2x if the query matches the first word of the candidate phrase).
- **Prefix bonus**: 1.3x if the candidate starts with the query.

After length correction, **signal-based score boosting** rewards candidates that were found by multiple independent strategies:

| Signal | Boost | Rationale |
|--------|-------|-----------|
| Phonetic match | 1.08x | Candidate "sounds right"—strong signal for homophones and near-homophones |
| Edit distance ≤ 1 | 1.02x | Very close in edit space—modest tiebreaker |
| 3+ strategies found candidate | 1.03x | Multiple independent strategies converging = high confidence |

All boosts are capped at 1.0 to prevent score inflation. They are applied *after* length correction, ensuring they act as tiebreakers between candidates of similar corrected quality rather than overriding the base scoring.

## Phonetic Search

Phonetic search finds words that "sound like" the query, regardless of spelling. "Filosofy" should find "philosophy"; "nife" should find "knife." The implementation combines ICU transliteration for cross-linguistic sound normalization with jellyfish's Metaphone encoder [Philips (1990)](#references) for final phonetic coding.

### ICU Normalization Pipeline

The [`PhoneticEncoder`](../backend/src/floridify/search/phonetic/encoder.py) applies a two-stage normalization pipeline:

**Stage 1: Script normalization.** The CLDR-standard `Any-Latin; Latin-ASCII; Lower` transliteration converts any Unicode script to Latin, strips diacritics, and lowercases. This is a compiled ICU transliterator ([Unicode CLDR](#references)) that handles Cyrillic, Greek, CJK, and Arabic scripts transparently.

**Stage 2: Cross-linguistic phonetic rules.** A custom ICU rule set in [`phonetic/constants.py`](../backend/src/floridify/search/phonetic/constants.py) collapses sound equivalences that Metaphone—being English-phonology-only—doesn't handle:

- **French nasal vowels**: `en`, `an`, `on`, `in`, `un` before consonants → unified `an`. This makes "en coulisses" and "an coulisses" produce the same code.
- **French vowel digraphs**: `eau`/`aux` → `o`, `oi` → `wa`, `ou` → `oo`, `eu` → `oy`.
- **French consonant patterns**: `tion` → `sion`, `gn` → `ny`, `ille` → `eey`, `qu` → `k`.
- **German consonant clusters**: `tsch` → `ch`, `sch` → `sh`.
- **German vowel patterns**: `ei` → `ay`, `ie` → `ee`.
- **Cross-linguistic consonants**: `ph` → `f`, `ck` → `k`, `wh` → `w`, `ght` → `t`.
- **Double consonant simplification**: `ss` → `s`, `ll` → `l`, `cc` → `k`, etc.

ICU rule syntax uses context operators (`{` for lookbehind, `}` for lookahead) to express positional constraints. For example, the rule `e n } [bcdfghjklmnpqrstvwxyz] → a n` fires only when "en" is followed by a consonant—it won't trigger for "enable" (where "en" is followed by "a"). Rules are processed in order; the first match wins. The full rule set is approximately 50 rules covering the major phonetic patterns of French, German, and cross-linguistic consonant equivalences.

These rules are compiled into an ICU transliterator automaton at module load time. The compilation produces a finite-state transducer that processes the input string in a single left-to-right pass. Per-query cost is sub-microsecond—the ICU C++ engine handles the string transformation without any Python-level iteration.

Why Metaphone + ICU over Double Metaphone alone? Double Metaphone generates two codes per word (primary and alternate) to handle English ambiguities, but it has no knowledge of French nasals, German clusters, or other cross-linguistic patterns. By normalizing these patterns *before* Metaphone encoding, the system produces consistent phonetic codes regardless of source language orthography.

### Phonetic Index Architecture

The [`PhoneticIndex`](../backend/src/floridify/search/phonetic/index.py) builds two inverted indexes:

1. **Composite index**: Maps the composite Metaphone key (per-word codes joined with `|`) to vocabulary indices. For "en coulisses," the composite key is `AN|KLSS`.
2. **Per-word index**: Maps individual word Metaphone codes to vocabulary indices. "coulisses" → code `KLSS` → all vocabulary entries containing a word with that code.

### Search Strategy Cascade

Phonetic search uses a three-strategy cascade:

1. **Exact composite match**: Look up the query's composite key in the composite index. If found, these are very high-confidence matches—the entire phrase sounds identical.

2. **Fuzzy composite match**: If the composite index has fewer than `PHONETIC_FUZZY_COMPOSITE_LIMIT` (10,000) entries, compute Levenshtein distance between the query's composite key and all stored keys, accepting matches within `max(1, len(code) // 4)` distance. This catches slight phonetic variations.

3. **Per-word intersection**: Encode each query word independently, look up each code in the per-word index, and count how many query words each candidate matches. Candidates matching at least half the query words (`threshold = max(1, len(query_words) // 2)`) are returned, ordered by count.

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
├── FuzzyIndex (BK-tree, PhoneticIndex, SuffixArray as pickled bytes)
└── SemanticIndex (FAISS index + embeddings via GridFS)
```

Each index type extends `BaseVersionedData` with a `Metadata` inner class, providing:

- **Resource ID**: `{corpus_uuid}:{type}` (e.g., `abc123:trie`, `abc123:fuzzy`, `abc123:semantic`)
- **Vocabulary hash**: SHA-256 of the sorted vocabulary, used for cache invalidation. If the hash matches, the persisted index is valid; if not, it's rebuilt.
- **Version tracking**: Semantic versioning with `is_latest` flag for efficient "get latest" queries.

**TrieIndex persistence.** The trie data (sorted word list), word frequencies, normalized-to-original mapping, and Bloom filter bytes are stored as JSON via the versioned content manager. The Bloom filter's `bytearray` is persisted alongside its parameters (bit count, hash count, item count, error rate) so it can be restored without recomputation.

**FuzzyIndex persistence.** The BK-tree, PhoneticIndex, and SuffixArray are serialized via Python's `pickle`, then encoded with base85 for JSON-safe storage. Base85 encoding adds ~25% overhead compared to raw bytes but avoids binary-in-JSON issues. On load, `FuzzyIndex.deserialize()` unpickles all three structures and returns them as a tuple.

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
| BK-tree | O(n * h) | O(n^(k/log n)) | O(n) nodes |
| Trigram index | O(n * m) | O(t * p̄) where t=trigrams, p̄=avg posting length | O(n * m) postings |
| Phonetic index | O(n * w) where w=words per entry | O(c) where c=composite codes (strategy 2) | O(n * w) |
| Semantic (FAISS Flat) | O(n * d) | O(n * d) brute force | O(n * d) |
| Semantic (FAISS HNSW) | O(n * M * log n) | O(d * log n) | O(n * (d + M)) |
| Semantic (FAISS OPQ+IVF-PQ) | O(n * d) + training | O(d * nprobe) | O(n * m_pq * nbits/8) |

**Profiled numbers** (Apple M4 Max, Qwen3-0.6B, 300K word English corpus):

| Operation | Time | Notes |
|-----------|------|-------|
| Exact lookup (trie + Bloom) | ~0.001ms | Two O(m) passes: Bloom filter then trie |
| Prefix search (20 results) | ~0.001ms | marisa-trie C++ traversal |
| Substring search (suffix array) | ~1ms | Twin binary search over ~4.5MB text |
| Fuzzy search (full pipeline) | ~5-20ms | BK-tree + trigram + phonetic + RapidFuzz scoring |
| Semantic search (FAISS, result cache hit) | ~0.001ms | LRU dict lookup |
| Semantic search (FAISS, vocab embedding hit) | ~0.1ms | O(1) array access + FAISS query |
| Semantic search (FAISS, full encode) | ~10-50ms | Transformer inference + FAISS query |
| Model load (first query) | ~1.5s | Cached after first load |
| Corpus embedding (1,323 words, batch=128) | ~3.3s | 397 words/sec |
| Corpus embedding (5,000 words, batch=128) | ~11.6s | 430 words/sec |
| Full corpus embedding (300K words, batch=128) | ~13min | Multiprocessing, 2 workers (macOS) |
| FAISS index build (FlatL2, 10K vectors, 512D) | ~10ms | Brute-force, no training |
| FAISS index build (HNSW, 100K vectors, 512D) | ~5s | M=32, efConstruction=200 |
| Hot reload (index rebuild) | ~2-5s | Excludes semantic rebuild |
| Corpus change detection | ~1-2ms | Indexed MongoDB query |

**Batch size matters.** On Apple Silicon, `batch_size=128` is 42% faster than `batch_size=32` for the 0.6B model due to better SIMD utilization. Model-specific batch sizes are defined in `MODEL_BATCH_SIZES`. MPS (Apple GPU) is 0.72x the speed of CPU for this model size—the overhead of CPU-GPU data transfer dominates for the relatively small model.

**Memory footprint** for a 300K word corpus at 512D (after Matryoshka truncation):

| Component | Memory |
|-----------|--------|
| Embeddings (float32) | ~585MB |
| FAISS HNSW index | ~20MB overhead |
| Suffix array + reverse map | ~54MB |
| Trigram index | ~6MB |
| marisa-trie | ~20MB |
| Bloom filter | ~120KB |
| BK-tree (pickled) | ~15MB |
| PhoneticIndex | ~5MB |

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
| `STRONG_PRIMARY_SCORE` | 0.85 | RapidFuzz score to skip secondary scorer |
| `STRONG_PRIMARY_COUNT` | 3 | Number of strong results needed to skip secondary |
| `FUZZY_PERFECT_SCORE` | 0.99 | Score treated as perfect match |

### Signal Boost Factors

| Constant | Default | Purpose |
|----------|---------|---------|
| `PHONETIC_MATCH_BOOST` | 1.08 | Boost for candidates with phonetic match |
| `CLOSE_EDIT_DISTANCE_BOOST` | 1.02 | Boost for edit distance ≤ 1 |
| `MULTI_SIGNAL_BOOST` | 1.03 | Boost for candidates found by 3+ strategies |

### Corpus Size Thresholds

| Constant | Default | Purpose |
|----------|---------|---------|
| `CORPUS_TINY` | 500 | Below this, use full vocabulary as candidates |
| `CORPUS_SMALL` | 5,000 | Small corpus threshold |
| `CORPUS_MEDIUM` | 50,000 | Medium corpus threshold |
| `CORPUS_LARGE` | 100,000 | Large corpus threshold |
| `CORPUS_XLARGE` | 300,000 | Extra-large corpus threshold |

### Candidate Budgets

| Constant | Default | Purpose |
|----------|---------|---------|
| `FUZZY_BUDGET_SMALL` | 300 | Max candidates for corpora < 5K |
| `FUZZY_BUDGET_MEDIUM` | 700 | Max candidates for corpora < 50K |
| `FUZZY_BUDGET_LARGE` | 1,100 | Max candidates for corpora < 300K |
| `FUZZY_BUDGET_XLARGE` | 1,700 | Max candidates for corpora >= 300K |
| `PHONETIC_BUDGET_CAP` | 200 | Cap on phonetic candidates |

### BK-Tree Configuration

| Constant | Default | Purpose |
|----------|---------|---------|
| `BKTREE_MAX_CORPUS_SIZE` | 100,000 | Skip BK-tree above this size |
| `BKTREE_TIME_BUDGET_SMALL` | 20ms | Time budget for corpora < 10K |
| `BKTREE_TIME_BUDGET_MEDIUM` | 10ms | Time budget for corpora 10K-50K |
| `BKTREE_TIME_BUDGET_LARGE` | 5ms | Time budget for corpora > 50K |
| `BKTREE_CASCADE_MIN_CANDIDATES` | 10 | Min candidates before stopping k expansion |
| `BKTREE_MAX_RESULTS_CAP` | 2,000 | Safety cap per k level |
| `EDIT_DISTANCE_LENGTH_MULTIPLIER` | 0.35 | Multiplier for adaptive max_k |
| `EDIT_DISTANCE_MIN` | 2 | Minimum edit distance |
| `EDIT_DISTANCE_MAX` | 5 | Maximum edit distance |

### Trigram Index

| Constant | Default | Purpose |
|----------|---------|---------|
| `TRIGRAM_THRESHOLD_DENOMINATOR` | 3 | Overlap threshold = max(2, n_trigrams // this) |
| `TRIGRAM_CAP_FRACTION` | 0.8 | Reserve 20% of budget for length-bucket candidates |
| `TRIGRAM_CAP_MINIMUM` | 10 | Minimum trigram candidate cap |

### Bloom Filter

| Constant | Default | Purpose |
|----------|---------|---------|
| `BLOOM_SMALL_CORPUS` | 10,000 | Threshold for tight error rate |
| `BLOOM_MEDIUM_CORPUS` | 100,000 | Threshold for medium error rate |
| `BLOOM_ERROR_RATE_SMALL` | 0.001 | Error rate for corpora < 10K |
| `BLOOM_ERROR_RATE_MEDIUM` | 0.01 | Error rate for corpora 10K-100K |
| `BLOOM_ERROR_RATE_LARGE` | 0.05 | Error rate for corpora > 100K |

### RapidFuzz Scoring

| Constant | Default | Purpose |
|----------|---------|---------|
| `PRIMARY_PHRASE_CUTOFF_MULTIPLIER` | 45 | Score cutoff = min_score * this (phrases) |
| `PRIMARY_WORD_CUTOFF_MULTIPLIER` | 50 | Score cutoff = min_score * this (words) |
| `SECONDARY_PHRASE_CUTOFF_MULTIPLIER` | 35 | Secondary cutoff for phrases |
| `SECONDARY_WORD_CUTOFF_MULTIPLIER` | 45 | Secondary cutoff for words |
| `SECONDARY_RESULT_BOOST` | 1.2 | Boost for secondary scorer results |
| `RAPIDFUZZ_LIMIT_MULTIPLIER_LARGE` | 5 | Result limit multiplier for large pools |
| `RAPIDFUZZ_LIMIT_MULTIPLIER_SMALL` | 3 | Result limit multiplier for small pools |
| `VOCABULARY_SIZE_LIMIT_THRESHOLD` | 200 | Pool size to switch multiplier |

### Phonetic Search

| Constant | Default | Purpose |
|----------|---------|---------|
| `PHONETIC_FUZZY_COMPOSITE_LIMIT` | 10,000 | Max composite codes for fuzzy scan |
| `PHONETIC_CODE_DISTANCE_FRACTION` | 4 | max_dist = len(code) // this |
| `PHONETIC_WORD_THRESHOLD_FRACTION` | 2 | Majority = len(words) // this |

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
