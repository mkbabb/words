# Corpus System

Floridify's corpus system manages hierarchical collections of vocabulary that power the multi-method search engine. Every search query runs against a corpus: a normalized, indexed word list derived from language lexicons, literary texts, or user-defined wordlists. The corpus module handles creation, storage, tree composition, vocabulary aggregation, and lifecycle management for these collections.

Three corpus types serve distinct purposes. **Language corpora** assemble vocabulary from URL-based lexicon sources (Scrabble dictionaries, frequency lists, idiom collections) into a master tree per language. **Literature corpora** extract vocabulary from literary works fetched via Project Gutenberg or the Internet Archive, organized by author and genre. **Custom corpora** hold arbitrary word lists provided through the API or wordlist imports. All three share the same underlying `Corpus` model, tree operations, and search integration.

The corpus powers the search pipeline. When a user searches, the search engine loads the relevant corpus, walks its trie, BK-tree, suffix array, and FAISS indices, and returns scored results. When the corpus changes—sources added, vocabulary aggregated, children restructured—the search indices rebuild atomically from the new vocabulary.

## Table of Contents

1. [Tree Architecture](#1-tree-architecture)
2. [The Corpus Model](#2-the-corpus-model)
3. [Corpus Types](#3-corpus-types)
4. [TreeCorpusManager](#4-treecorpusmanager)
5. [Vocabulary Aggregation](#5-vocabulary-aggregation)
6. [Vocabulary Processing](#6-vocabulary-processing)
7. [Cascade Deletion](#7-cascade-deletion)
8. [Semantic Policy](#8-semantic-policy)
9. [Parsers](#9-parsers)
10. [Language Sources](#10-language-sources)
11. [Literature Sources](#11-literature-sources)
12. [API Layer](#12-api-layer)
13. [Key Files](#13-key-files)

---

## 1. Tree Architecture

Corpora form a tree. A master "English" corpus contains children like "sowpods_scrabble_words" and "google_10k_frequency." A master "Shakespeare" corpus contains children for *Hamlet*, *Macbeth*, *King Lear*. The master aggregates its children's vocabularies, producing a single combined word list that the search engine can index and query as one unit. This tree structure enables atomic subtree rebuilding: changing a child triggers re-aggregation of only its ancestor chain, not the entire corpus graph. It also permits bespoke compositions—a "Shakespeare's Comedies" corpus can exist as a subtree of the broader Shakespeare corpus, reusing the same child works without duplicating vocabulary data.

### The Dual-Identity Model

Each corpus carries two identifiers: a MongoDB `ObjectId` (`corpus_id`) and a UUID string (`corpus_uuid`). These serve fundamentally different roles.

The `corpus_id` is a standard Beanie `PydanticObjectId`—the `_id` field on the MongoDB document. It changes whenever a new version of the corpus is saved. The versioning system (see [docs/versioning.md](versioning.md)) creates a new `Metadata` document for each version, so the `_id` shifts with every save. This is fine for point-in-time lookups but breaks parent-child references: if a parent stores its child's `ObjectId`, that reference breaks the moment the child is re-saved.

The `corpus_uuid` is an immutable UUID4 string assigned once by the version manager's Pydantic validator and never changed. It survives version rotation because the versioning system copies it forward into each new metadata document. Parent-child relationships use UUIDs exclusively: `parent_uuid` is a string, `child_uuids` is a `list[str]`, both holding UUID values. When the version manager saves a new version of a child corpus, the parent's `child_uuids` list remains valid because the UUID hasn't changed—only the `ObjectId` has.

### Adjacency List Representation

The tree uses an adjacency list: each node stores its `parent_uuid` (nullable for roots) and its `child_uuids` list. This is stored both on the `Corpus` Pydantic model and on the `Corpus.Metadata` Beanie document, kept in sync during save operations in [`crud.py`](../backend/src/floridify/corpus/crud.py).

```
English (master, uuid=abc-123)
├── parent_uuid: None
├── child_uuids: [def-456, ghi-789, ...]
│
├── sowpods_scrabble_words (uuid=def-456)
│   ├── parent_uuid: abc-123
│   └── child_uuids: []
│
├── google_10k_frequency (uuid=ghi-789)
│   ├── parent_uuid: abc-123
│   └── child_uuids: []
│
└── american_idioms (uuid=jkl-012)
    ├── parent_uuid: abc-123
    └── child_uuids: []
```

Retrieval by UUID queries MongoDB for `{"uuid": corpus_uuid, "version_info.is_latest": True}`, locating the latest version of any node by its stable identifier.

### Cycle Detection and Self-Reference Prevention

The tree module in [`tree.py`](../backend/src/floridify/corpus/tree.py) prevents two structural invariant violations.

**Cycle detection** uses an upward walk. Before adding a child to a parent, `would_create_cycle()` starts at the proposed parent and walks up via `parent_uuid` links, checking whether it ever reaches the proposed child. If it does, the addition would create a cycle and is rejected. A visited set guards against existing cycles in the data.

```python
async def would_create_cycle(parent_id, child_id, ...):
    current = parent_id
    visited = set()
    while current:
        if current == child_id:
            return True
        if current in visited:
            break
        visited.add(current)
        corpus = await get_corpus_fn(corpus_id=current)
        current = parent_corpus.corpus_id if parent_corpus else None
    return False
```

**Self-reference prevention** operates at two levels. The `update_parent()` function in `tree.py` checks `parent_id == child_id` and returns `False` immediately. The `remove_self_references()` helper in `crud.py` filters a corpus's own UUID from its `child_uuids` list before every save and on every read, catching any self-references that slip through via race conditions or data migration.

### Reparenting

When a child is moved from one parent to another, `update_parent()` handles the full transition: it removes the child's UUID from the old parent's `child_uuids`, adds it to the new parent's `child_uuids`, updates the child's `parent_uuid`, and recomputes semantic policy for both the old and new parent chains. Each step saves through `save_corpus()` to maintain the version chain—a reparenting operation produces new versions for the old parent, the new parent, and the child.

### Why a Tree?

The tree structure solves three problems at once.

First, **atomic subtree rebuilding**. When a source updates—say SOWPODS releases a new edition—only the affected child corpus and its ancestor chain need rebuilding. Without the tree, updating one source in a flat merged corpus would require re-fetching and reprocessing every source.

Second, **bespoke composition without duplication**. A "Shakespeare's Comedies" corpus can include *A Midsummer Night's Dream* and *Twelfth Night* as children while a broader "Shakespeare" corpus includes those same works alongside the tragedies and histories. The child work corpora exist once in the database; the parent trees compose them differently.

Third, **vocabulary isolation for search quality**. Master corpora aggregate children's vocabularies for search but don't contribute vocabulary of their own. This prevents the aggregate container from polluting search results with stale or orphaned words that belong to no specific source.

---

## 2. The Corpus Model

The `Corpus` class in [`core.py`](../backend/src/floridify/corpus/core.py) is a Pydantic `BaseModel` that holds all vocabulary data and index structures in memory.

### Core Vocabulary Fields

| Field | Type | Description |
|-------|------|-------------|
| `vocabulary` | `list[str]` | Sorted, deduplicated, normalized word list |
| `original_vocabulary` | `list[str]` | Raw input words (preserving duplicates, casing, diacritics) |
| `lemmatized_vocabulary` | `list[str]` | Unique lemmas in first-seen order |

The `vocabulary` field is the canonical search target. Every word has been lowercased, Unicode-normalized, and deduplicated. The `original_vocabulary` preserves the raw input for display purposes—when a user searches and matches "cafe," the system can return "cafe" from the original vocabulary, which maps back to the accented form via `normalized_to_original_indices`.

### Index Structures

| Field | Type | Purpose |
|-------|------|---------|
| `vocabulary_to_index` | `dict[str, int]` | Normalized word to position in `vocabulary` |
| `normalized_to_original_indices` | `dict[int, list[int]]` | Normalized index to original indices (diacritics-preferred first) |
| `trigram_index` | `TrigramIndex` | Inverted index mapping character trigrams to vocabulary indices |
| `length_buckets` | `LengthBuckets` | Words bucketed by character length for fuzzy candidate selection |
| `lemma_text_to_index` | `dict[str, int]` | Lemma string to lemma index |
| `word_to_lemma_indices` | `dict[int, int]` | Word index to its lemma index |
| `lemma_to_word_indices` | `dict[int, list[int]]` | Lemma index to all word indices sharing that lemma |

The trigram index and length buckets are transient (`exclude=True` in Pydantic serialization)—they're rebuilt from vocabulary on every load via `_build_candidate_index()`. The lemmatization maps are persisted and rebuilt lazily when missing.

### Normalization Pipeline

`Corpus.create()` runs the full normalization pipeline:

1. **Batch normalize** the input vocabulary (lowercase, Unicode NFKD decomposition, diacritic stripping)
2. **Sort and deduplicate** to produce `unique_normalized`
3. **Build `vocabulary_to_index`** mapping from the sorted result
4. **Build `normalized_to_original_indices`**, sorting each index list to prefer words with diacritics over their ASCII equivalents
5. **Create lemmatization maps** via `create_lemmatization_maps()`
6. **Build candidate index** (trigram inverted index + length buckets)
7. **Optionally create semantic index** (FAISS) if `semantic=True`

Vocabulary size is capped at 1,000,000 words to prevent out-of-memory errors.

### Incremental Operations

The `Corpus` model supports incremental vocabulary modification without full reconstruction:

**`add_words(words)`** extends `original_vocabulary`, merges into the sorted normalized `vocabulary` via `merge_words()`, rebuilds all indices, updates word frequencies, and returns the count of new unique words added.

**`remove_words(words)`** filters both vocabularies via `filter_words()`, rebuilds indices, clears removed words from `word_frequencies`, and returns the count of removed unique words.

Both methods call `_rebuild_indices()` internally, which reconstructs `vocabulary_to_index`, `normalized_to_original_indices`, the trigram candidate index, and the lemmatization maps. The `vocabulary_hash` is recomputed to reflect the new content, enabling the search engine's hot-reload mechanism to detect changes and swap indices.

### Vocabulary Hashing

`get_vocabulary_hash()` in [`utils.py`](../backend/src/floridify/corpus/utils.py) produces a SHA-256 hash for content-addressable caching. Rather than hashing the entire vocabulary (which could be hundreds of thousands of words), it uses deterministic sampling: take the first 10 and last 10 words from the sorted vocabulary, concatenate them with the vocabulary length and an optional model name prefix, and hash the result. The model name inclusion prevents cache collisions between different embedding models operating on the same vocabulary. The hash is truncated to 16 hex characters by default.

### Name Generation

If no `corpus_name` is provided during creation, the `model_post_init()` hook generates one via `coolname.generate_slug(2)`, producing readable two-word slugs like "brave-falcon" or "silent-ocean." This ensures every corpus has a human-friendly identifier even when created programmatically.

### Metadata Inner Class

`Corpus.Metadata` extends `BaseVersionedData`—a Beanie `Document` subclass that handles versioned MongoDB persistence. It stores the tree structure fields (`parent_uuid`, `child_uuids`, `is_master`), semantic policy fields, vocabulary metadata (`vocabulary_size`, `vocabulary_hash`), and usage tracking (`ttl_hours`, `search_count`, `last_accessed`).

The `_class_id` ClassVar is critical. Beanie uses polymorphic document resolution to distinguish between `Corpus.Metadata`, `LanguageCorpus.Metadata`, and `LiteratureCorpus.Metadata` within the same MongoDB collection. Without unique `_class_id` discriminators, Beanie would confuse all three as `BaseVersionedData.Metadata`, breaking queries and type resolution. Each subclass overrides:

```python
_class_id: ClassVar[str] = "Corpus.Metadata"  # or "LanguageCorpus.Metadata", etc.

class Settings(BaseVersionedData.Settings):
    class_id = "_class_id"
```

---

## 3. Corpus Types

The `CorpusType` enum in [`models.py`](../backend/src/floridify/corpus/models.py) defines six variants:

| Value | Usage |
|-------|-------|
| `LEXICON` | Default type for generic vocabulary corpora |
| `LANGUAGE` | Language-specific corpora assembled from provider sources |
| `LITERATURE` | Literary work corpora with author/genre/period metadata |
| `WORDLIST` | Individual user wordlist corpora |
| `WORDLIST_NAMES` | Special corpus holding all wordlist name strings |
| `CUSTOM` | User-defined corpora created via the API |

### LanguageCorpus

`LanguageCorpus` in [`language/core.py`](../backend/src/floridify/corpus/language/core.py) inherits from `Corpus` and adds source management. Its `create_from_language()` class method follows a 3-step creation pattern:

1. **Save empty parent**: Create a master corpus with empty vocabulary, save it to get a stable UUID from the version manager
2. **Create children**: For each `LanguageSource`, fetch vocabulary via `URLLanguageConnector`, create a child `Corpus`, save it with `parent_uuid` set and `skip_parent_update=True` (to avoid N intermediate parent saves)
3. **Save parent again**: Aggregate all children's vocabularies in memory, set `child_uuids`, rebuild indices, and save the parent a second and final time

This produces exactly two parent versions (empty + complete) instead of N+2 versions that would fragment the version chain.

`LanguageCorpus` also links vocabulary to `Word` documents: after creating a child corpus, `_link_corpus_vocabulary_words()` batch-upserts `Word` documents with `corpus_ids` and `languages` fields, associating each word with its source corpus.

### LiteratureCorpus

`LiteratureCorpus` in [`literature/core.py`](../backend/src/floridify/corpus/literature/core.py) mirrors the language pattern but for literary works. Its `add_author_works()` method accepts an `AuthorInfo` and a list of work IDs, adds all works without per-source aggregation (`aggregate=False`), then aggregates once at the end. Vocabulary extraction from literature uses a simple regex: `re.findall(r"\b[a-zA-Z]+\b", text)`, followed by lowercase deduplication.

`LiteratureCorpus.Metadata` adds typed fields for literature-specific metadata (`title`, `author`, `genre`, `period`, `file_path`) that were previously stored in the generic metadata dict.

---

## 4. TreeCorpusManager

The `TreeCorpusManager` in [`manager.py`](../backend/src/floridify/corpus/manager.py) is a singleton that delegates all operations to standalone functions in three modules:

| Module | Responsibility |
|--------|---------------|
| [`crud.py`](../backend/src/floridify/corpus/crud.py) | `save_corpus`, `get_corpus`, `get_corpora_by_ids`, `get_corpora_by_uuids`, `get_stats` |
| [`aggregation.py`](../backend/src/floridify/corpus/aggregation.py) | `aggregate_vocabularies`, `aggregate_from_children` |
| [`tree.py`](../backend/src/floridify/corpus/tree.py) | `create_tree`, `update_parent`, `add_child`, `remove_child`, `delete_corpus`, `would_create_cycle`, `invalidate_corpus` |

### Singleton Access

```python
_tree_corpus_manager: TreeCorpusManager | None = None

def get_tree_corpus_manager() -> TreeCorpusManager:
    global _tree_corpus_manager
    if _tree_corpus_manager is None:
        _tree_corpus_manager = TreeCorpusManager()
    return _tree_corpus_manager
```

The constructor initializes with a `VersionedDataManager` (defaulting to the global instance from `get_version_manager()`).

### Pure Delegation

The manager's methods are thin wrappers. Each one passes `self.vm` (the version manager), `self.get_corpus` (for recursive lookups), and `self.save_corpus` (for recursive saves) into the standalone functions. This separation keeps the standalone functions testable without requiring a full manager instance, while the manager provides a convenient facade with consistent dependency wiring.

### CRUD Operations

`get_corpus()` accepts three lookup strategies—by `corpus_id` (ObjectId), by `corpus_uuid` (stable UUID), or by `corpus_name` (resource identifier)—and always returns the latest version. It rebuilds indices on load if needed: if `vocabulary_to_index` is empty, it's reconstructed from vocabulary; if `lemmatized_vocabulary` is empty, lemmatization maps are rebuilt.

`get_corpora_by_uuids()` batch-fetches multiple corpora in a single MongoDB query using `{"uuid": {"$in": corpus_uuids}}`, eliminating the N+1 query anti-pattern that would otherwise occur when loading a parent's children.

### Save Pipeline

`save_corpus()` in `crud.py` handles the persistence path. When a `Corpus` object is passed, the function extracts all fields into explicit parameters (with explicit parameters taking precedence over corpus object values), cleans self-references from `child_uuids`, and delegates to `VersionedDataManager.save()`. The version manager handles UUID assignment, version numbering, content hashing, and MongoDB persistence.

After saving, the function auto-updates the parent's `child_uuids` if the corpus has a `parent_uuid` and is being created (not updated). This auto-update is skipped when `skip_parent_update=True`, which `LanguageCorpus.create_from_language()` uses to batch child creation without N redundant parent saves. The semantic policy is also recomputed upward after auto-update.

### Update and Invalidation

`update_corpus()` on the manager loads the existing corpus, merges new content and metadata, preserves all existing tree structure fields, and saves with `increment_version=True`. The merge uses Python dict update semantics: new keys override existing ones, unmentioned keys are preserved.

`invalidate_corpus()` and `invalidate_all_corpora()` clear cache entries without deleting the underlying data. They remove keys from the `CORPUS` cache namespace and clear any versioned cache entries, forcing the next access to reload from MongoDB.

---

## 5. Vocabulary Aggregation

Vocabulary aggregation merges word lists from a corpus tree into a single sorted vocabulary on the parent. The `aggregate_vocabularies()` function in [`aggregation.py`](../backend/src/floridify/corpus/aggregation.py) performs a recursive merge using `asyncio.gather` for concurrent child fetches.

### Master vs Non-Master Logic

The aggregation distinguishes between master and non-master corpora:

- **Master corpora** (`is_master=True`) are pure containers. They contribute no vocabulary of their own—only their children's vocabularies are aggregated. This prevents the parent from competing with its children in search results.
- **Non-master corpora** include their own vocabulary in the aggregation alongside any children's.

```python
if corpus.is_master:
    # Master corpora never include their own vocabulary
    logger.info(f"Master corpus {corpus_id} - using only children's vocabulary")
elif corpus.vocabulary:
    vocabulary.update(corpus.vocabulary)
```

### Aggregation Flow

1. Load the target corpus
2. Collect `child_uuids` (with a fallback: if `child_uuids` is empty but `corpus_uuid` exists, query MongoDB for documents with matching `parent_uuid`)
3. Recursively aggregate each child's vocabulary via `asyncio.gather`, passing `update_parent=False` to prevent intermediate saves
4. Union all child vocabularies into a sorted set
5. If `update_parent=True` (the default for top-level calls), update the parent corpus with the aggregated vocabulary, rebuild all indices (vocabulary_to_index, lemmatization, trigram index), and save

### Index Rebuilding After Aggregation

When aggregation updates a parent, the following indices are rebuilt:

- `vocabulary_to_index` — reconstructed from the sorted vocabulary
- Unified indices (lemmatization maps) — via `_create_unified_indices()`
- Candidate index (trigram inverted index, length buckets) — via `_build_candidate_index()`
- Vocabulary stats — updated with new counts

The semantic policy is recomputed after aggregation if a `recompute_semantic_fn` is provided.

### Fallback Child Discovery

If a corpus's `child_uuids` list is empty but its `corpus_uuid` exists, aggregation performs a fallback query: `Corpus.Metadata.find({"parent_uuid": corpus.corpus_uuid, "version_info.is_latest": True})`. This handles cases where `child_uuids` wasn't persisted properly (e.g., during migration or after a partial save failure), recovering the tree structure from the children's `parent_uuid` pointers.

### Why Master vs Non-Master?

Masters exist as pure aggregation containers. If a master included its own vocabulary alongside its children's, the master's word list would compete with the children's in search results, returning duplicate matches. Worse, if a child is removed, the master would still contain the child's vocabulary until the next aggregation—stale data masquerading as authoritative. By excluding the master's own vocabulary, the aggregated result is always exactly the union of its children's current vocabularies.

---

## 6. Vocabulary Processing

The [`vocabulary.py`](../backend/src/floridify/corpus/vocabulary.py) module contains pure functions for vocabulary normalization, merging, filtering, and lemmatization.

### normalize_vocabulary

The primary entry point for raw word lists:

```python
def normalize_vocabulary(vocabulary: list[str]) -> tuple[
    list[str],              # unique_normalized: sorted deduplicated vocabulary
    dict[str, int],         # vocabulary_to_index: word -> index
    dict[int, list[int]],   # normalized_to_original_indices: norm_idx -> [orig_idxs]
]:
```

1. **Batch normalize**: calls `batch_normalize()` from the text module (lowercase, Unicode NFKD, diacritic stripping)
2. **Sort and deduplicate**: `sorted(set(normalized_vocabulary))`
3. **Build index**: `{word: i for i, word in enumerate(unique_normalized)}`
4. **Build reverse mapping**: For each original word, record which normalized index it maps to. Sort each index list so that words with diacritics come first.

### Diacritics Handling

The `has_diacritics()` function checks if any character has an ordinal above 127. When multiple original forms map to the same normalized form (e.g., "cafe" and "cafe" from "cafe" and "caf\u00e9"), the `normalized_to_original_indices` list is sorted to prefer the diacritical form:

```python
orig_indices.sort(key=lambda idx: (not has_diacritics(vocabulary[idx]), idx))
```

This means `get_original_word_by_index()` returns "caf\u00e9" rather than "cafe" when both exist.

### Lemmatization

`create_lemmatization_maps()` calls `batch_lemmatize()` from the text module and builds four structures:

- `lemmatized_vocabulary`: unique lemmas in first-seen order
- `lemma_text_to_index`: lemma string to its position in the lemma list
- `word_to_lemma_indices`: word index to lemma index (many-to-one)
- `lemma_to_word_indices`: lemma index to all word indices sharing that lemma (one-to-many)

These maps enable the fuzzy search to find morphological variants: searching "running" can match "run," "runs," and "ran" through shared lemma indices.

### Merge and Filter

`merge_words()` normalizes new words and unions them with the existing vocabulary, returning the sorted result. `filter_words()` removes specified words from both the normalized and original vocabularies, preserving index alignment.

---

## 7. Cascade Deletion

Corpus deletion in [`tree.py`](../backend/src/floridify/corpus/tree.py) handles the full dependency graph. The `delete_corpus()` function accepts a `cascade` flag that determines whether children are recursively deleted.

### Deletion Order

1. **Recursive child deletion** (if `cascade=True`): iterate over `child_uuids` and recursively call `delete_corpus()` on each, depth-first
2. **Remove from parent**: if the corpus has a `parent_uuid`, look up the parent corpus and call `remove_child()` to remove this corpus's UUID from the parent's `child_uuids` list
3. **Delete search index metadata**: use `asyncio.gather` to concurrently delete `TrieIndex.Metadata`, `SearchIndex.Metadata`, and `SemanticIndex.Metadata` documents matching this corpus's UUID
4. **Delete all version documents**: delete all `Corpus.Metadata` documents with `{"uuid": corpus_uuid}`, removing all versions (not just the latest)
5. **Clear cache entries**: delete the corpus's cache key from the `CORPUS` namespace via `get_global_cache()`

### Search Index Cleanup

The search index metadata documents (`TrieIndex.Metadata`, `SearchIndex.Metadata`, `SemanticIndex.Metadata`) are stored in the same MongoDB collection as other versioned data, discriminated by `_class_id`. Deletion queries filter by `{"corpus_uuid": corpus_uuid_to_delete}`, ensuring all index versions for this corpus are removed. This prevents orphaned index metadata from accumulating after corpus deletion.

---

## 8. Semantic Policy

The semantic policy system in [`semantic_policy.py`](../backend/src/floridify/corpus/semantic_policy.py) determines whether FAISS semantic search is enabled for each corpus node in the tree.

### Two Fields

| Field | Type | Description |
|-------|------|-------------|
| `semantic_enabled_explicit` | `bool \| None` | User-set value. `True` = explicitly enabled, `False` = explicitly disabled, `None` = inherit |
| `semantic_enabled_effective` | `bool` | Computed value used by the search engine |

### Child-to-Parent OR Logic

The effective state is computed via child-to-parent OR propagation:

```python
def compute_effective_semantic_state(explicit, child_states):
    return bool(explicit is True or any(child_states))
```

A corpus is semantically enabled if it's explicitly enabled OR if any of its children are effectively enabled. This means enabling semantic search on a single leaf corpus bubbles the effective state up through all ancestors to the root.

### Recomputation

Two recomputation functions handle different traversal directions:

**`recompute_semantic_effective_upward()`** starts at a node and walks up to the root via `parent_uuid` links. At each level, it fetches all children, collects their `semantic_enabled_effective` states, computes the new effective state, and persists it if changed. This is called after tree mutations (add child, remove child, reparenting).

**`recompute_semantic_effective_subtree()`** recurses depth-first from a root, computing effective states bottom-up. This is used for full tree recomputation.

Both functions use a `visited` set to guard against infinite loops from corrupted tree data.

### Why Two Fields?

The two-field design (`explicit` + `effective`) separates user intent from computed state. A user can explicitly enable semantic search on a leaf corpus without touching the parent. The effective state propagates upward automatically, enabling semantic search on the parent (because one of its children supports it). Later, if that child is removed, the parent's effective state updates to `False`—unless another child or the parent's own explicit setting keeps it enabled.

The `None` value for `semantic_enabled_explicit` means "inherit"—the corpus makes no claim about semantic search and defers entirely to its children's states. This three-valued logic (`True`/`False`/`None`) allows fine-grained control: a parent can force semantic search off (`False`) even if children have it enabled, or leave it unset (`None`) to let children drive the effective state.

---

## 9. Parsers

The [`parser.py`](../backend/src/floridify/corpus/parser.py) module provides 8 parser functions for lexicon data formats. Each function takes content and a `Language` and returns a `ParseResult`—a tuple of `(words: list[str], phrases: list[str])`. Phrases are identified by the `is_phrase()` utility (multi-word strings).

| Parser | Input Format | Output |
|--------|-------------|--------|
| `parse_text_lines` | One word per line, `#` comments | Words and phrases |
| `parse_frequency_list` | `word frequency` pairs per line | Words only (frequency ignored) |
| `parse_json_idioms` | JSON with `idioms`, `phrase`, or `text` keys | Phrases only |
| `parse_json_dict` | JSON object with words as keys | Words and phrases |
| `parse_json_array` | JSON array of strings | Words and phrases |
| `parse_github_api` | GitHub API response (base64 content) | Delegates to `parse_json_array` |
| `parse_csv_idioms` | CSV with `idiom`/`phrase`/`expression` columns | Phrases only |
| `parse_json_phrasal_verbs` | JSON array with `verb`/`phrasal_verb` keys | Phrases only |

A ninth function, `parse_scraped_data`, handles dict-structured data from custom scrapers, extracting `words` and `phrases` keys.

All parsers normalize each extracted string via `normalize()` before inclusion, filtering out empty strings. The `parse_text_lines` parser is the most commonly used, serving as the default for URL-based language sources that provide plain word lists.

---

## 10. Language Sources

Language corpus sources are defined in [`providers/language/sources.py`](../backend/src/floridify/providers/language/sources.py). Each source is a `LanguageSource` model with a name, URL, parser type, language, and description.

### English Sources

| Source | URL Host | Description | Parser |
|--------|----------|-------------|--------|
| `sowpods_scrabble_words` | github.com/jesstess | SOWPODS official Scrabble dictionary (~267k words) | `TEXT_LINES` |
| `google_10k_frequency` | github.com/first20hours | Google's 10,000 most common English words | `TEXT_LINES` |
| `american_idioms` | github.com/yuxiaojian | Common American idioms with synonyms | `CUSTOM` |
| `phrasal_verbs` | github.com/Semigradsky | Common English phrasal verbs | `CUSTOM` |
| `common_phrases` | gist.github.com | Top 500 common phrases from Wikipedia | `TEXT_LINES` |
| `proverbs` | github.com/dariusk/corpora | English proverbs and sayings | `CUSTOM` |
| `french_expressions` | en.wikipedia.org | French words used in English | `CUSTOM` (Wikipedia scraper) |

### Non-English Sources

| Language | Sources | Notable |
|----------|---------|---------|
| French | `french_word_list` (~336k), `french_frequent_words` (50k) | Gutenberg + FrequencyWords |
| Spanish | `spanish_word_list` (~80k), `spanish_frequent_words` (50k) | Community dict + FrequencyWords |
| German | `german_word_list` (~1.7M), `german_frequent_words` (50k) | Largest single source |
| Italian | `italian_word_list` (~660k), `italian_frequent_words` (50k) | paroleitaliane + FrequencyWords |

Sources are grouped by language via `LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE`, a dict mapping `Language` enum values to their source lists. `LanguageCorpus.create_from_language()` iterates over this dict to build the per-language master corpus.

### Word-to-Document Linking

After creating each child corpus, `LanguageCorpus._link_corpus_vocabulary_words()` batch-upserts `Word` documents. For each word in the child's vocabulary, it either creates a new `Word` document with `corpus_ids=[child_corpus_id]` and `languages=[child_language_codes]`, or updates an existing `Word` document by merging its language and corpus ID lists. This batched approach processes 1,000 words per iteration to avoid overwhelming MongoDB.

---

## 11. Literature Sources

Literature corpora draw from two external APIs and 15 pre-configured author mappings.

### Project Gutenberg

The `GutenbergConnector` in [`providers/literature/api/gutenberg.py`](../backend/src/floridify/providers/literature/api/gutenberg.py) downloads plain text from `mirror.gutenberg.org`. It tries multiple format paths for each work:

1. `files/{id}/{id}-0.txt` (UTF-8)
2. `files/{id}/{id}.txt` (plain text)
3. `files/{id}/{id}-8.txt` (ISO-8859-1)
4. `files/{id}/{id}.zip` (zipped text)

Downloaded texts are cleaned by stripping Gutenberg headers (`*** START OF ...`) and footers (`*** END OF ...`), removing transcriber notes, illustration markers, and page numbers, and normalizing whitespace.

The connector also supports catalog search via `search_works()`, parsing HTML from `gutenberg.org/ebooks/search/` to extract work IDs, titles, authors, and download counts.

### Internet Archive

The `InternetArchiveConnector` in [`providers/literature/api/internet_archive.py`](../backend/src/floridify/providers/literature/api/internet_archive.py) searches and downloads from `archive.org`. It uses the Archive's advanced search API (`advancedsearch.php`) with JSON output, filtering for `mediatype:texts`. Content download iterates the Archive's file listing page, preferring `.txt` over `.pdf` and `.epub`.

### Author Mappings

Fifteen author mapping modules in [`providers/literature/mappings/`](../backend/src/floridify/providers/literature/mappings/) provide pre-configured work lists with Gutenberg IDs, genre classifications, and period assignments:

| Author | Period | Primary Genre | Works Count |
|--------|--------|---------------|-------------|
| Shakespeare | Renaissance | Drama | 28 (tragedies, comedies, histories) |
| Homer | Ancient | Epic | 11 (Iliad, Odyssey + translations) |
| Dante | Medieval | Poetry | Mapped |
| Chaucer | Medieval | Poetry | Mapped |
| Milton | Renaissance | Poetry | Mapped |
| Cervantes | Renaissance | Novel | Mapped |
| Goethe | Enlightenment | Drama | Mapped |
| Joyce | Modern | Novel | Mapped |
| Dickens | Victorian | Novel | Mapped |
| Tolstoy | Realism | Novel | Mapped |
| Virgil | Ancient | Epic | Mapped |
| Ovid | Ancient | Poetry | Mapped |
| Aeschylus | Ancient | Tragedy | Mapped |
| Sophocles | Ancient | Tragedy | Mapped |
| Euripides | Ancient | Tragedy | Mapped |

Each mapping exports an `AUTHOR` (`AuthorInfo`) and a `WORKS` list of `LiteratureEntry` objects. The `LiteratureEntry` model composes a `LiteratureSource` with metadata: title, author, Gutenberg ID, year, genre, period, and language. Some authors include multi-language works—Homer's mappings include Spanish translations of the Iliad and Odyssey.

### Vocabulary Extraction

When `LiteratureCorpus.add_literature_source()` processes a fetched work, vocabulary extraction uses:

```python
words = re.findall(r"\b[a-zA-Z]+\b", entry.text)
vocabulary = list(set(word.lower() for word in words))
```

This captures alphabetic tokens only, deduplicates, and lowercases. The resulting vocabulary is passed to `Corpus.create()` for full normalization and index building. The regex intentionally excludes numbers, punctuation, and non-Latin characters—literature vocabulary extraction prioritizes clean English word forms over comprehensive tokenization.

### File-Based Works

`LiteratureCorpus.add_file_work()` bypasses the connector system entirely, reading a local file directly and extracting vocabulary with the same regex approach. It accepts optional metadata (title, author, genre, period) and creates a child corpus with `file_path` stored in its metadata for provenance tracking.

### Literature Text Parsers

The [`providers/literature/parsers.py`](../backend/src/floridify/providers/literature/parsers.py) module handles 5 text formats: plain text, Markdown, HTML, EPUB (via `ebooklib`), and PDF (via `pypdf`). The EPUB parser extracts text from all `ITEM_DOCUMENT` chapters; the PDF parser extracts from all pages. Both apply post-processing via `parse_text()` to remove pagination artifacts and normalize whitespace.

---

## 12. API Layer

The corpus REST API is defined in [`api/routers/corpus.py`](../backend/src/floridify/api/routers/corpus.py). All endpoints use the `TreeCorpusManager` singleton.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/corpus` | List all corpora with pagination and filtering (language, source type, stats) |
| `GET` | `/corpus/stats` | Corpus cache statistics (count, total searches) |
| `GET` | `/corpus/{corpus_id}` | Get a specific corpus by ObjectId (includes TTL expiration check) |
| `POST` | `/corpus` | Create a new corpus from vocabulary, with optional semantic indexing |
| `DELETE` | `/corpus/{corpus_id}` | Delete a corpus, optionally cascading to children |
| `POST` | `/corpus/{corpus_id}/search` | Search within a specific corpus (smart cascade mode) |
| `PATCH` | `/corpus/{corpus_id}/semantic` | Toggle explicit semantic policy and recompute effective state |
| `POST` | `/corpus/{corpus_id}/rebuild` | Admin-only: re-aggregate vocabulary and rebuild search indices |

### Corpus-Scoped Search

The `/corpus/{corpus_id}/search` endpoint creates a `SearchIndex` for the target corpus, initializes a `Search` engine from it, and runs `search_with_mode()` in `SearchMode.SMART` (the full cascade: exact, prefix, substring, fuzzy, semantic). Before searching, it atomically increments `search_count` and sets `last_accessed` on the corpus metadata via a MongoDB `$inc`/`$set` operation.

### TTL Expiration

Corpora have a configurable TTL stored on the metadata document. The `GET /corpus/{corpus_id}` endpoint computes `expires_at = created_at + timedelta(hours=ttl_hours)` and returns 404 if the current time exceeds it. The default TTL is 1 hour. Custom corpora created through the API can specify a different TTL via the `CorpusCreateParams.ttl_hours` field.

### Rebuild Endpoint

The `POST /corpus/{corpus_id}/rebuild` endpoint (admin-only) provides a recovery mechanism for stale or corrupted corpus state. It accepts a `CorpusRebuildRequest` with three options:

- `re_aggregate`: re-aggregate vocabulary from all children (default `True`)
- `rebuild_search`: rebuild search indices after aggregation (default `True`)
- `components`: which search components to rebuild: `"trie"`, `"semantic"`, or `"all"`

The endpoint loads the corpus with `use_cache=False`, runs aggregation if requested, then delegates to `_rebuild_corpus()` from the search rebuild module to reconstruct trie, fuzzy, and semantic indices from the fresh vocabulary.

### Repository Layer

The `CorpusRepository` in [`api/repositories/corpus_repository.py`](../backend/src/floridify/api/repositories/corpus_repository.py) provides a simpler interface used by other parts of the system (not the REST API directly). It wraps `TreeCorpusManager` with higher-level methods like `create_from_wordlist()` and `search()`, and the `CorpusSearchParams` model adds semantic weight configuration.

---

## 13. Key Files

### Core

| File | Purpose |
|------|---------|
| [`corpus/core.py`](../backend/src/floridify/corpus/core.py) | `Corpus` model: vocabulary, indices, tree fields, `Metadata` inner class, `create()`, `save()`, `delete()` |
| [`corpus/models.py`](../backend/src/floridify/corpus/models.py) | `CorpusType` enum, `CorpusSource` model |
| [`corpus/manager.py`](../backend/src/floridify/corpus/manager.py) | `TreeCorpusManager` singleton, delegates to crud/aggregation/tree |
| [`corpus/crud.py`](../backend/src/floridify/corpus/crud.py) | `save_corpus`, `get_corpus`, `get_corpora_by_uuids`, `remove_self_references` |
| [`corpus/tree.py`](../backend/src/floridify/corpus/tree.py) | `create_tree`, `update_parent`, `add_child`, `remove_child`, `delete_corpus`, `would_create_cycle` |
| [`corpus/aggregation.py`](../backend/src/floridify/corpus/aggregation.py) | `aggregate_vocabularies`, `aggregate_from_children` |

### Vocabulary & Policy

| File | Purpose |
|------|---------|
| [`corpus/vocabulary.py`](../backend/src/floridify/corpus/vocabulary.py) | `normalize_vocabulary`, `create_lemmatization_maps`, `merge_words`, `filter_words` |
| [`corpus/utils.py`](../backend/src/floridify/corpus/utils.py) | `get_vocabulary_hash` (SHA-256 content-addressable cache keys) |
| [`corpus/parser.py`](../backend/src/floridify/corpus/parser.py) | 8 parsers for lexicon data formats |
| [`corpus/semantic_policy.py`](../backend/src/floridify/corpus/semantic_policy.py) | `compute_effective_semantic_state`, `recompute_semantic_effective_upward`, `recompute_semantic_effective_subtree` |

### Corpus Types

| File | Purpose |
|------|---------|
| [`corpus/language/core.py`](../backend/src/floridify/corpus/language/core.py) | `LanguageCorpus`: `create_from_language`, `add_language_source`, `remove_source` |
| [`corpus/literature/core.py`](../backend/src/floridify/corpus/literature/core.py) | `LiteratureCorpus`: `add_literature_source`, `add_author_works`, `add_file_work` |

### Providers

| File | Purpose |
|------|---------|
| [`providers/language/sources.py`](../backend/src/floridify/providers/language/sources.py) | 14 language source definitions across 5 languages |
| [`providers/language/models.py`](../backend/src/floridify/providers/language/models.py) | `LanguageSource`, `LanguageEntry`, `ParserType`, `ScraperType` |
| [`providers/literature/api/gutenberg.py`](../backend/src/floridify/providers/literature/api/gutenberg.py) | `GutenbergConnector`: download, search, clean Gutenberg texts |
| [`providers/literature/api/internet_archive.py`](../backend/src/floridify/providers/literature/api/internet_archive.py) | `InternetArchiveConnector`: search and download from archive.org |
| [`providers/literature/mappings/`](../backend/src/floridify/providers/literature/mappings/) | 15 author modules with pre-configured Gutenberg work lists |
| [`providers/literature/parsers.py`](../backend/src/floridify/providers/literature/parsers.py) | Text, Markdown, HTML, EPUB, PDF parsers for literary content |

### API

| File | Purpose |
|------|---------|
| [`api/routers/corpus.py`](../backend/src/floridify/api/routers/corpus.py) | REST endpoints: CRUD, search, semantic toggle, rebuild |
| [`api/repositories/corpus_repository.py`](../backend/src/floridify/api/repositories/corpus_repository.py) | `CorpusRepository`: high-level create/get/search interface |
