# Corpus Module - Vocabulary Management

Hierarchical corpus trees with UUID-based relationships, vocabulary aggregation, semantic index integration.

## Structure

```
corpus/
├── core.py              # Corpus data model with indices (897 LOC)
├── manager.py           # TreeCorpusManager - hierarchy ops (1,353 LOC)
├── models.py            # CorpusType enum, CorpusSource (37 LOC)
├── parser.py            # 9 corpus parsers (268 LOC)
├── utils.py             # Vocabulary hashing (53 LOC)
├── language/
│   └── core.py         # LanguageCorpus - source management (377 LOC)
└── literature/
    └── core.py         # LiteratureCorpus - work management (358 LOC)
```

**Total**: 3,389 LOC across 8 files

## Core Data Model

**Corpus** (`core.py:897`):

```python
class Corpus:
    # Identity (UUID-based, stable across versions)
    corpus_uuid: str                     # Immutable UUID
    corpus_id: PydanticObjectId          # MongoDB _id (changes per version)
    corpus_name: str
    corpus_type: CorpusType             # LEXICON, LITERATURE, LANGUAGE, etc.
    language: Language

    # Hierarchy (UUID-based relationships)
    parent_uuid: str | None              # Parent's stable UUID
    child_uuids: list[str]               # Children's stable UUIDs
    is_master: bool                      # Master corpus flag

    # Vocabulary
    vocabulary: list[str]                # Sorted normalized words
    original_vocabulary: list[str]       # Original forms with diacritics
    vocabulary_size: int
    vocabulary_hash: str                 # SHA-256 for cache isolation

    # Indices (built from vocabulary)
    vocabulary_to_index: dict[str, int]           # word → index O(1)
    normalized_to_original_indices: dict          # norm_idx → [orig_idxs]
    lemmatized_vocabulary: list[str]              # Unique lemmas
    word_to_lemma_indices: dict[int, int]        # word_idx → lemma_idx
    lemma_to_word_indices: dict[int, list[int]]  # lemma_idx → [word_idxs]
    signature_buckets: dict[str, list[int]]      # signature → [word_idxs]
    length_buckets: dict[int, list[int]]         # length → [word_idxs]

    @classmethod
    async def create(
        cls,
        name: str,
        vocabulary: list[str],
        corpus_type: CorpusType,
        language: Language,
        semantic: bool = False,
        model_name: str | None = None,
    ) -> Corpus:
        # 1. Normalize vocabulary
        normalized = await batch_normalize(vocabulary)
        lemmatized = await batch_lemmatize(normalized)

        # 2. Build indices (lemmatization, signatures, length)
        corpus._create_unified_indices()
        corpus._build_signature_index()

        # 3. Optionally build semantic index
        if semantic:
            await SemanticIndex.get_or_create(corpus, model_name)

        return corpus
```

## Tree Operations

**TreeCorpusManager** (`manager.py:1,353`):

Manages UUID-based parent-child relationships:

```python
class TreeCorpusManager:
    _version_manager: VersionedDataManager
    _locks: defaultdict[tuple[ResourceType, str], asyncio.Lock]

    async def save_corpus(corpus: Corpus) -> Corpus:
        # 1. Convert enums to strings
        # 2. Remove self-references from child_uuids
        # 3. Save via VersionedDataManager
        # 4. Return versioned corpus

    async def update_parent(
        child_id: str | PydanticObjectId,
        parent_id: str | PydanticObjectId,
    ):
        # 1. Extract stable UUIDs
        # 2. Prevent self-reference
        # 3. Check for cycles via _would_create_cycle()
        # 4. Add child UUID to parent's child_uuids
        # 5. Set parent UUID on child
        # 6. Save both (creates new versions)

    async def aggregate_vocabularies(
        parent_id: str,
        update_parent: bool = True,
    ) -> list[str]:
        # 1. Get parent corpus by ID or UUID
        # 2. For each child_uuid in parent.child_uuids:
        #      - Recursively call aggregate_vocabularies(child_uuid)
        #      - Merge child vocabularies into set
        # 3. If not is_master, add parent's own vocabulary
        # 4. Sort and optionally update parent
        # 5. Rebuild all indices
        # 6. Save parent with aggregated vocabulary

    async def remove_child(
        parent_id: str,
        child_id: str,
        delete_child: bool = False,
    ):
        # 1. Remove child UUID from parent's child_uuids
        # 2. Clear parent reference from child
        # 3. Optionally cascade delete child

    async def delete_corpus(corpus_id: str):
        # 1. Get all child UUIDs recursively
        # 2. Delete all children
        # 3. Delete search indices (SearchIndex → TrieIndex, SemanticIndex)
        # 4. Delete corpus metadata via version manager

    def _would_create_cycle(
        child_id: PydanticObjectId,
        parent_id: PydanticObjectId,
    ) -> bool:
        # Walk up parent chain from parent_id
        # Return True if child_id found in chain
```

**Key fixes**:
- **N+1 Query Fix**: Batch retrieves by UUID (lines 510-513) - single MongoDB query
- **Self-Reference Prevention**: `_remove_self_references()` helper (lines 39-64)
- **UUID Stability**: Uses immutable UUIDs for relationships, not ObjectIds

## Vocabulary Aggregation

**Recursive aggregation** (`manager.py:620-713`):

```python
# Example: Language corpus with 3 source children
async def aggregate_vocabularies("english_master"):
    # 1. Get master corpus
    master = await get_corpus("english_master")

    # 2. Parallel child aggregation
    child_vocabs = await asyncio.gather(*[
        aggregate_vocabularies(child_uuid)
        for child_uuid in master.child_uuids
    ])

    # 3. Merge vocabularies
    aggregated = set()
    for child_vocab in child_vocabs:
        aggregated.update(child_vocab)

    # 4. Master corpus: ONLY aggregated children (ignore own vocabulary)
    if master.is_master:
        vocabulary = sorted(aggregated)
    else:
        vocabulary = sorted(aggregated.union(set(master.vocabulary)))

    # 5. Rebuild indices
    master.vocabulary = vocabulary
    await master._rebuild_indices()

    # 6. Save master corpus
    await save_corpus(master)

    return vocabulary
```

**Master corpus behavior**:
- `is_master=True`: Contains ONLY aggregated children
- `is_master=False`: Contains own vocabulary + children

## LanguageCorpus

**Language-specific corpus** (`language/core.py:377`):

```python
class LanguageCorpus(Corpus):
    async def add_language_source(
        source_name: str,
        source: LanguageSource,
    ) -> Corpus:
        # 1. Fetch source data via LanguageConnector
        # 2. Create child corpus from vocabulary
        # 3. Save child via TreeCorpusManager
        # 4. Update parent-child relationship
        # 5. Aggregate vocabularies from parent+children
        # 6. Reload parent to get aggregated vocabulary

    @classmethod
    async def create_from_language(
        cls,
        language: Language,
        semantic: bool = False,
    ) -> LanguageCorpus:
        # 1. Create master corpus
        # 2. For each source in LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE[language]:
        #      - await add_language_source(source_name, source)
        # 3. Single aggregation at end (not per source)
        # 4. Reload corpus with aggregated vocabulary

    async def remove_source(source_name: str):
        # Remove source corpus + re-aggregate

    async def update_source(source_name: str, new_source: LanguageSource):
        # Remove old + add new
```

## LiteratureCorpus

**Literature-specific corpus** (`literature/core.py:358`):

```python
class LiteratureCorpus(Corpus):
    async def add_literature_source(
        work_id: int | str,
        provider: LiteratureProvider = GUTENBERG,
        author: str | None = None,
    ) -> Corpus:
        # 1. Fetch work via LiteratureConnector
        # 2. Extract vocabulary from text (regex: r"\b[a-zA-Z]+\b")
        # 3. Create child corpus with work metadata
        # 4. Save child + update parent-child relationship
        # 5. Aggregate vocabularies

    async def add_author_works(
        author: str,
        work_ids: list[int | str],
        provider: LiteratureProvider = GUTENBERG,
    ):
        # Parallel work additions via asyncio.gather()

    async def add_file_work(
        file_path: str,
        title: str,
        author: str | None = None,
    ):
        # Read local file → extract vocabulary → create child corpus

    async def remove_work(work_id: str):
        # Remove work corpus

    async def update_work(work_id: str, new_work: LiteratureSource):
        # Remove old + add new
```

## Semantic Index Integration

**FAISS index building** (`core.py:262-278`):

```python
# In Corpus.create()
if semantic:
    from ..search.semantic.constants import DEFAULT_SENTENCE_MODEL
    from ..search.semantic.models import SemanticIndex

    model_name = model_name or DEFAULT_SENTENCE_MODEL
    await SemanticIndex.get_or_create(
        corpus=corpus,
        model_name=model_name,
        batch_size=None,  # Use default
    )
```

**Deletion cascade** (`core.py:859-876`):
```python
# When deleting corpus:
# 1. Get SearchIndex for corpus
# 2. Delete SearchIndex (cascades to TrieIndex and SemanticIndex)
# 3. Delete Corpus metadata
```

## Parsers

**9 parsers** (`parser.py:268`):

| Parser | Input | Output |
|--------|-------|--------|
| `parse_text_lines` | One word per line | (words, phrases) |
| `parse_frequency_list` | "word 123" format | (words, phrases) |
| `parse_json_idioms` | JSON with idioms | (words, phrases) |
| `parse_json_dict` | JSON dictionary | (words, phrases) |
| `parse_json_array` | JSON array | (words, phrases) |
| `parse_github_api` | GitHub API response | (words, phrases) |
| `parse_csv_idioms` | CSV with columns | (words, phrases) |
| `parse_json_phrasal_verbs` | JSON phrasal verbs | (words, phrases) |
| `parse_scraped_data` | Custom scraper | (words, phrases) |

**Common pattern**:
```python
def parse_text_lines(content: str) -> tuple[list[str], list[str]]:
    words, phrases = [], []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue  # Skip comments/empty
        normalized = normalize(line)
        if is_phrase(normalized):
            phrases.append(normalized)
        else:
            words.append(normalized)
    return list(set(words)), list(set(phrases))
```

## Vocabulary Hashing

**Deterministic hashing** (`utils.py:53`):

```python
def get_vocabulary_hash(
    vocabulary: list[str],
    model_name: str | None = None,
    max_length: int = 16,
    is_sorted: bool = False,
) -> str:
    # 1. Sort vocabulary if not already sorted
    # 2. Sample first + last 20 words for speed
    # 3. Include model_name to prevent cache collisions
    # 4. Compute SHA-256 hash
    # 5. Return 16-char hex string

    # Used for:
    # - Semantic index cache keys (per-model isolation)
    # - Corpus change detection
    # - Version comparison
```

## Indices & Data Structures

**Vocabulary indices** (built in `_create_unified_indices`):

```python
# 1. Lemmatization maps
word_to_lemma_indices: dict[int, int]        # word_idx → lemma_idx
lemma_to_word_indices: dict[int, list[int]]  # lemma_idx → [word_idxs]

# 2. Signature buckets (consonants only: "perspicacious" → "prsp")
signature_buckets: dict[str, list[int]]      # signature → [word_idxs]

# 3. Length buckets
length_buckets: dict[int, list[int]]         # length → [word_idxs]

# 4. Normalized-to-original mapping
normalized_to_original_indices: dict[int, list[int]]  # norm_idx → [orig_idxs]
```

**Used by search**:
- `get_candidates()` - Smart candidate selection for fuzzy search
- `get_word_by_index()` - O(1) normalized word lookup
- `get_original_word_by_index()` - Map to original form with diacritics

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Corpus.create() | <500ms | For 10k words (normalize + index) |
| aggregate_vocabularies() | 100-500ms | Recursive with parallel children |
| get_candidates() | 1-10ms | Uses signature/length buckets |
| save_corpus() | 50-200ms | MongoDB write + version manager |
| get_corpus() | 10-50ms | Includes index rebuilding if needed |
| Batch get_corpora_by_uuids() | 50-100ms | Single MongoDB query (N+1 fix) |

## MongoDB Storage

**Metadata model** (`core.py:118-153`):

```python
class Corpus.Metadata(BaseVersionedData):
    _class_id: ClassVar[str] = "Corpus.Metadata"  # Discriminator

    corpus_name: str
    corpus_type: CorpusType
    language: Language
    parent_uuid: str | None
    child_uuids: list[str]
    is_master: bool
    vocabulary_size: int
    vocabulary_hash: str
    content_location: ContentLocation | None  # For >16KB vocabulary
```

**Polymorphic hierarchy**:
- `Corpus.Metadata._class_id = "Corpus.Metadata"`
- `LanguageCorpus.Metadata._class_id = "LanguageCorpus.Metadata"`
- `LiteratureCorpus.Metadata._class_id = "LiteratureCorpus.Metadata"`

**Collection**: Single `corpus_metadata` collection with discriminator field

## Design Patterns

- **Singleton** - `get_tree_corpus_manager()` accessor
- **Factory** - `Corpus.create()` with index building
- **Hierarchy** - Parent-child tree with cycle detection
- **N+1 Query Fix** - Batch UUID retrieval
- **Versioning** - VersionedDataManager for immutable history
- **Polymorphic Inheritance** - LanguageCorpus, LiteratureCorpus extend Corpus
- **Lazy Index Building** - Indices rebuilt on load if missing
- **Deterministic Hashing** - Vocabulary hash for cache isolation

## Corpus Types

```python
class CorpusType(Enum):
    LEXICON = "lexicon"                    # Dictionary/vocabulary
    LITERATURE = "literature"              # Literary texts
    LANGUAGE = "language"                  # Language-specific
    WORDLIST = "wordlist"                  # Individual wordlist
    WORDLIST_NAMES = "wordlist_names"
    CUSTOM = "custom"
```
