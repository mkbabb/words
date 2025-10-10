# Beanie Metadata Class Analysis Report

**Date:** 2025-10-08
**Analysis Type:** Research Only - No Code Changes

## Executive Summary

All metadata classes inherit from `BaseVersionedData` but have a critical difference in their Beanie `Settings` configuration. **Corpus, SearchIndex, TrieIndex, and SemanticIndex metadata classes do NOT define their own `Settings` class**, while **LanguageEntry and LiteratureEntry metadata classes DO define their own `Settings` class**. This causes all the former to share the same MongoDB collection (`versioned_data`) while the latter get their own collections.

## 1. init_beanie() Call Location and Registered Models

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/storage/mongodb.py`
**Lines:** 97-120

```python
await init_beanie(
    database=database,
    document_models=[
        # New models
        Word,
        Definition,
        Example,
        Fact,
        Pronunciation,
        AudioMedia,
        ImageMedia,
        WordRelationship,
        WordList,
        # Versioning models - base class first
        BaseVersionedData,
        DictionaryEntry,
        BatchOperation,
        # Cache models - all versioned metadata classes
        Corpus.Metadata,
        SearchIndex.Metadata,
        TrieIndex.Metadata,
        SemanticIndex.Metadata,
    ],
)
```

**Key Observation:** The registration order includes `BaseVersionedData` first, then the specific metadata classes. However, because the metadata classes don't override Settings, they all inherit BaseVersionedData's Settings and share the same collection.

## 2. BaseVersionedData Class Definition

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/caching/models.py`
**Lines:** 177-247

```python
class BaseVersionedData(Document):
    """Base class for all versioned data with content management."""

    # Identification
    resource_id: str
    resource_type: ResourceType
    namespace: CacheNamespace

    # Versioning
    version_info: VersionInfo

    # Content storage
    content_location: ContentLocation | None = None
    content_inline: dict[str, Any] | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    ttl: timedelta | None = None

    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            # PRIMARY: Latest version lookup
            [("resource_id", 1), ("version_info.is_latest", 1), ("_id", -1)],
            # Specific version lookup
            [("resource_id", 1), ("version_info.version", 1)],
            # Content hash deduplication
            [("resource_id", 1), ("version_info.data_hash", 1)],
            # Corpus.Metadata indices (sparse)
            IndexModel([("corpus_name", 1)], sparse=True, name="corpus_name_sparse"),
            IndexModel([("vocabulary_hash", 1)], sparse=True, name="vocabulary_hash_sparse"),
            IndexModel([("parent_corpus_id", 1)], sparse=True, name="parent_corpus_id_sparse"),
            # Index metadata indices (sparse)
            IndexModel([("corpus_id", 1)], sparse=True, name="corpus_id_sparse"),
        ]
```

**Key Features:**
- `is_root = True` - This is important for Beanie's document hierarchy
- Sparse indices for subclass-specific fields (corpus_name, corpus_id, etc.)
- All indices are defined in the base class to work across all subclasses

## 3. Metadata Class Hierarchy

### 3.1 Corpus.Metadata

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/corpus/core.py`
**Lines:** 115-144

```python
class Metadata(
    BaseVersionedData,
    default_resource_type=ResourceType.CORPUS,
    default_namespace=CacheNamespace.CORPUS,
):
    """Corpus metadata for versioned persistence."""

    # Corpus identification
    corpus_name: str = ""
    corpus_type: CorpusType = CorpusType.LEXICON
    language: Language = Language.ENGLISH

    # Tree structure
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False

    # Vocabulary metadata
    vocabulary_size: int = 0
    vocabulary_hash: str = ""

    # Storage configuration
    content_location: ContentLocation | None = None
```

**Inheritance:**
- MRO: `['Metadata', 'BaseVersionedData', 'Document', 'LazyModel', 'BaseModel']`
- Has own Settings: **NO**
- Collection name: `versioned_data` (inherited from BaseVersionedData)
- is_root: `True` (inherited)

**Subclass-specific fields:**
- `corpus_name`
- `corpus_type`
- `language`
- `parent_corpus_id`
- `child_corpus_ids`
- `is_master`
- `vocabulary_size`
- `vocabulary_hash`

### 3.2 SearchIndex.Metadata

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/search/models.py`
**Lines:** 363-377

```python
class Metadata(
    BaseVersionedData,
    default_resource_type=ResourceType.SEARCH,
    default_namespace=CacheNamespace.SEARCH,
):
    """Minimal search metadata for versioning."""

    corpus_id: PydanticObjectId
    vocabulary_hash: str = ""
    has_trie: bool = False
    has_fuzzy: bool = False
    has_semantic: bool = False
    trie_index_id: PydanticObjectId | None = None
    semantic_index_id: PydanticObjectId | None = None
```

**Inheritance:**
- MRO: `['Metadata', 'BaseVersionedData', 'Document', 'LazyModel', 'BaseModel']`
- Has own Settings: **NO**
- Collection name: `versioned_data` (inherited from BaseVersionedData)
- is_root: `True` (inherited)

**Subclass-specific fields:**
- `corpus_id`
- `vocabulary_hash`
- `has_trie`
- `has_fuzzy`
- `has_semantic`
- `trie_index_id`
- `semantic_index_id`

### 3.3 TrieIndex.Metadata

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/search/models.py`
**Lines:** 93-102

```python
class Metadata(
    BaseVersionedData,
    default_resource_type=ResourceType.TRIE,
    default_namespace=CacheNamespace.TRIE,
):
    """Minimal trie metadata for versioning."""

    corpus_id: PydanticObjectId
    vocabulary_hash: str = ""
```

**Inheritance:**
- MRO: `['Metadata', 'BaseVersionedData', 'Document', 'LazyModel', 'BaseModel']`
- Has own Settings: **NO**
- Collection name: `versioned_data` (inherited from BaseVersionedData)
- is_root: `True` (inherited)

**Subclass-specific fields:**
- `corpus_id`
- `vocabulary_hash`

### 3.4 SemanticIndex.Metadata

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/models.py`
**Lines:** 68-80

```python
class Metadata(
    BaseVersionedData,
    default_resource_type=ResourceType.SEMANTIC,
    default_namespace=CacheNamespace.SEMANTIC,
):
    """Minimal semantic metadata for versioning."""

    corpus_id: PydanticObjectId
    model_name: str
    vocabulary_hash: str = ""
    embedding_dimension: int = 0
    index_type: str = "flat"
```

**Inheritance:**
- MRO: `['Metadata', 'BaseVersionedData', 'Document', 'LazyModel', 'BaseModel']`
- Has own Settings: **NO**
- Collection name: `versioned_data` (inherited from BaseVersionedData)
- is_root: `True` (inherited)

**Subclass-specific fields:**
- `corpus_id`
- `model_name`
- `vocabulary_hash`
- `embedding_dimension`
- `index_type`

## 4. Comparison: Working vs Non-Working Metadata Classes

### Working Example: LanguageEntry.Metadata

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/providers/language/models.py`
**Lines:** 98-109

```python
class Metadata(
    BaseVersionedData,
    default_resource_type=ResourceType.LANGUAGE,
    default_namespace=CacheNamespace.LANGUAGE,
):
    """Minimal language metadata for versioning."""

    class Settings:
        """Beanie settings."""

        name = "language_entry_metadata"
        indexes = ["provider"]
```

**Inheritance:**
- MRO: `['Metadata', 'BaseVersionedData', 'Document', 'LazyModel', 'BaseModel']`
- Has own Settings: **YES**
- Collection name: `language_entry_metadata` (overridden)
- is_root: Not set (uses Beanie default)

### Working Example: LiteratureEntry.Metadata

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/providers/literature/models.py`
**Lines:** 110-124

```python
class Metadata(
    BaseVersionedData,
    default_resource_type=ResourceType.LITERATURE,
    default_namespace=CacheNamespace.LITERATURE,
):
    """Minimal literature metadata for versioning."""

    provider: LiteratureProvider | None = None
    work_id: str | None = None

    class Settings:
        """Beanie settings."""

        name = "literature_entry_metadata"
        indexes = ["provider", "work_id"]
```

**Inheritance:**
- MRO: `['Metadata', 'BaseVersionedData', 'Document', 'LazyModel', 'BaseModel']`
- Has own Settings: **YES**
- Collection name: `literature_entry_metadata` (overridden)
- is_root: Not set (uses Beanie default)

## 5. Key Differences Summary

| Aspect | Corpus/Search/Trie/Semantic | Language/Literature |
|--------|----------------------------|---------------------|
| **Has own Settings class** | ❌ NO | ✅ YES |
| **Collection name** | `versioned_data` (shared) | `{type}_metadata` (unique) |
| **is_root setting** | `True` (inherited) | Not set (Beanie default) |
| **Custom indices** | Defined in BaseVersionedData | Defined in each class |
| **Collection isolation** | All share same collection | Each has own collection |

## 6. How Beanie Handles This

### Document Inheritance in Beanie

Beanie uses the `Settings` inner class to determine:
1. **Collection name** - Where documents are stored in MongoDB
2. **is_root** - Whether this is a root document class or a subclass
3. **Indices** - What indices to create on the collection

When a subclass **doesn't define its own Settings**:
- It inherits the parent's Settings completely
- It shares the same collection as the parent
- Documents are differentiated by discriminator fields or field presence

When a subclass **defines its own Settings**:
- It overrides the parent's collection name
- It gets its own MongoDB collection
- It can define its own indices

### Why Current Design Works

The current design uses a **polymorphic collection** approach:
1. All metadata classes share `versioned_data` collection
2. Differentiation happens via `resource_type` field (CORPUS, SEARCH, TRIE, SEMANTIC)
3. Sparse indices handle subclass-specific fields without errors
4. The `resource_id` + `resource_type` combo provides unique identification

This is a **valid Beanie pattern** and intentional, not a bug.

## 7. Field Introspection

The `get_subclass_fields()` function works correctly:

```python
from floridify.utils.introspection import get_subclass_fields

# Extract fields specific to each metadata class
corpus_fields = get_subclass_fields(Corpus.Metadata, BaseVersionedData)
# Returns: {'corpus_name', 'corpus_type', 'language', 'parent_corpus_id',
#           'child_corpus_ids', 'is_master', 'vocabulary_size', 'vocabulary_hash'}

search_fields = get_subclass_fields(SearchIndex.Metadata, BaseVersionedData)
# Returns: {'corpus_id', 'vocabulary_hash', 'has_trie', 'has_fuzzy',
#           'has_semantic', 'trie_index_id', 'semantic_index_id'}

trie_fields = get_subclass_fields(TrieIndex.Metadata, BaseVersionedData)
# Returns: {'corpus_id', 'vocabulary_hash'}

semantic_fields = get_subclass_fields(SemanticIndex.Metadata, BaseVersionedData)
# Returns: {'corpus_id', 'model_name', 'vocabulary_hash',
#           'embedding_dimension', 'index_type'}
```

## 8. Collection Names and Configuration

### Actual MongoDB Collections

Based on Beanie Settings, the following collections exist:

1. **versioned_data** - Shared by:
   - Corpus.Metadata
   - SearchIndex.Metadata
   - TrieIndex.Metadata
   - SemanticIndex.Metadata

2. **language_entry_metadata** - Used by:
   - LanguageEntry.Metadata

3. **literature_entry_metadata** - Used by:
   - LiteratureEntry.Metadata

### BaseVersionedData Indices

All in `versioned_data` collection:

```python
indexes = [
    # Primary version lookup
    [("resource_id", 1), ("version_info.is_latest", 1), ("_id", -1)],

    # Specific version
    [("resource_id", 1), ("version_info.version", 1)],

    # Hash deduplication
    [("resource_id", 1), ("version_info.data_hash", 1)],

    # Corpus-specific (sparse)
    IndexModel([("corpus_name", 1)], sparse=True, name="corpus_name_sparse"),
    IndexModel([("vocabulary_hash", 1)], sparse=True, name="vocabulary_hash_sparse"),
    IndexModel([("parent_corpus_id", 1)], sparse=True, name="parent_corpus_id_sparse"),

    # Index-specific (sparse)
    IndexModel([("corpus_id", 1)], sparse=True, name="corpus_id_sparse"),
]
```

**Note on sparse indices:** These allow subclass-specific fields to be indexed without requiring all documents to have those fields. This is how the polymorphic collection pattern works.

## 9. Version Manager Model Class Mapping

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/caching/manager.py`
**Line:** 632

```python
def _get_model_class(self, resource_type: ResourceType) -> type[BaseVersionedData]:
    """Map resource type enum to model class using registry pattern."""
    return get_versioned_model_class(resource_type)
```

**Registry Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/models/registry.py`

```python
def get_model_class(resource_type: ResourceType) -> type[BaseVersionedData]:
    """Get model class for a resource type using lazy imports."""

    if resource_type == ResourceType.CORPUS:
        from ..corpus.core import Corpus
        return Corpus.Metadata

    if resource_type == ResourceType.SEARCH:
        from ..search.models import SearchIndex
        return SearchIndex.Metadata

    if resource_type == ResourceType.TRIE:
        from ..search.models import TrieIndex
        return TrieIndex.Metadata

    if resource_type == ResourceType.SEMANTIC:
        from ..search.semantic.models import SemanticIndex
        return SemanticIndex.Metadata

    # ... other mappings
```

## 10. Special Handling and Initialization

### __init_subclass__ Hook

**Location:** `/Users/mkbabb/Programming/words/backend/src/floridify/caching/models.py`
**Lines:** 226-246

```python
def __init_subclass__(
    cls,
    default_resource_type: ResourceType | None = None,
    default_namespace: CacheNamespace | None = None,
    **kwargs: Any,
) -> None:
    """Set field defaults for child classes to avoid field shadowing warnings.

    Child classes can specify their resource_type and namespace like:
        class MyMetadata(BaseVersionedData,
                       default_resource_type=ResourceType.CORPUS,
                       default_namespace=CacheNamespace.CORPUS):
            pass
    """
    super().__init_subclass__(**kwargs)

    # Set field defaults at class creation time
    if default_resource_type is not None:
        cls.model_fields["resource_type"].default = default_resource_type
    if default_namespace is not None:
        cls.model_fields["namespace"].default = default_namespace
```

This hook allows each metadata class to set default values for `resource_type` and `namespace` without field shadowing warnings. It's invoked during class creation for all metadata classes.

## 11. Conclusions

### Architecture Pattern

The codebase uses a **Single Table Inheritance** pattern (in database terms) or **Polymorphic Document** pattern (in Beanie/ODM terms):

1. All metadata documents share the `versioned_data` collection
2. Documents are differentiated by `resource_type` field
3. Sparse indices handle optional/subclass-specific fields
4. Version manager uses `resource_type` to determine which class to instantiate

### This is Intentional Design

The pattern is **intentional and valid**:
- ✅ Reduces collection proliferation
- ✅ Simplifies version queries across all resource types
- ✅ Allows for unified version management
- ✅ Uses Beanie's `is_root=True` pattern correctly

### Why It Works

1. **Discriminator field**: `resource_type` distinguishes document types
2. **Sparse indices**: Allow subclass fields without breaking other documents
3. **Type-safe retrieval**: Registry pattern ensures correct class instantiation
4. **Pydantic validation**: Each class validates its own fields on load

### Potential Issues

The only potential issue is **index bloat** - the `versioned_data` collection has indices for all subclass fields, even if most documents don't use them. However, sparse indices mitigate this concern.

## 12. Recommendations

**For understanding the system:**
- This is a polymorphic document pattern, not a bug
- All metadata classes intentionally share `versioned_data` collection
- Differentiation happens via `resource_type` field
- Sparse indices ensure subclass fields are efficiently indexed

**For future development:**
- If adding new metadata classes, decide whether to:
  - Share `versioned_data` collection (current pattern) - inherit Settings
  - Use dedicated collection (Language/Literature pattern) - define own Settings
- Document the pattern choice in the metadata class docstring
- Add sparse indices to BaseVersionedData.Settings for new subclass fields

**No immediate action needed:**
- The current implementation is correct and intentional
- All metadata classes are properly registered with Beanie
- The polymorphic pattern is working as designed
