# Models Module - Type-Safe Data Layer

Pydantic v2 models for dictionary data, MongoDB ODM via Beanie, isomorphic CLI/API parameters.

## Structure

```
models/
├── __init__.py          # Public API (115 LOC) - exports 50+ models
├── parameters.py        # CLI/API shared parameters (458 LOC)
├── responses.py         # API response models (378 LOC)
├── dictionary.py        # Core dictionary entities (248 LOC)
├── base.py              # Base classes, enums, metadata (143 LOC)
├── literature.py        # Literature models (102 LOC)
├── relationships.py     # Word relationships (81 LOC)
└── registry.py          # Model class registry (46 LOC)
```

**Total**: 1,571 LOC, 50+ models

## Core Models

**Word** (`dictionary.py:248` - MongoDB Document)
```python
class Word(Document, BaseMetadata):
    text: str                    # Original form
    normalized: str              # Auto-computed via normalize_basic()
    lemma: str                   # Auto-computed via lemmatize_comprehensive()
    language: Language
    homograph_number: int | None

    # Indices: [(text, language)], normalized, lemma, [(text, homograph_number)]
```

**Definition** (`dictionary.py:248` - MongoDB Document)
```python
class Definition(Document, BaseMetadata):
    word_id: PydanticObjectId
    part_of_speech: str
    text: str
    meaning_cluster: MeaningCluster
    sense_number: str                    # "1a", "2b"

    # Relationships
    synonyms: list[str]
    antonyms: list[str]
    example_ids: list[PydanticObjectId]

    # Usage metadata
    language_register: Literal[formal|informal|neutral|slang|technical]
    domain: str | None                   # medical, legal, computing
    region: str | None                   # US, UK, AU
    cefr_level: Literal[A1-C2]
    frequency_band: int | None           # 1-5 (1=most common)

    # Grammar
    grammar_patterns: list[GrammarPattern]
    collocations: list[Collocation]
    transitivity: Literal[transitive|intransitive|both]

    # Word forms & usage
    word_forms: list[WordForm]           # plural, past_tense, etc.
    usage_notes: list[UsageNote]

    # Media & provenance
    image_ids: list[PydanticObjectId]
    providers: list[DictionaryProvider]
    model_info: ModelInfo | None         # AI provenance

    # Indices: word_id, part_of_speech, [(word_id, part_of_speech)]
```

**DictionaryEntry** (`dictionary.py:248` - MongoDB Document)
```python
class DictionaryEntry(Document, BaseMetadata):
    word_id: PydanticObjectId
    definition_ids: list[PydanticObjectId]
    pronunciation_id: PydanticObjectId | None
    fact_ids: list[PydanticObjectId]
    image_ids: list[PydanticObjectId]
    provider: DictionaryProvider
    language: Language
    etymology: Etymology                 # Nested model
    raw_data: dict | None                # Original API response
    model_info: ModelInfo | None

    # Indices: word_id, provider, language, [(word_id, provider)]
```

## Supporting Models

**Metadata & Provenance** (`base.py:143`)
- `BaseMetadata` - CRUD tracking (created_at, updated_at, version)
- `AccessTrackingMixin` - Access metrics (last_accessed, access_count)
- `ModelInfo` - AI provenance (model_name, confidence, tokens, response_time)

**Pronunciation** (`dictionary.py:248` - MongoDB Document)
- `phonetic`, `ipa`, `audio_file_ids`, `syllables`, `stress_pattern`

**Example** (`dictionary.py:248` - MongoDB Document)
- Discriminated union: type=Literal["generated", "literature"]
- Generated: text, model_info, context
- Literature: text, source (LiteratureSourceExample with literature_id, text_pos)

**Fact** (`dictionary.py:248` - MongoDB Document)
- content, category (etymology|usage|cultural|linguistic|historical), model_info

**Etymology** (`dictionary.py:248` - Nested BaseModel)
- text, origin_language, root_words, first_known_use

## Relationship Models

**Non-Document Models** (`relationships.py:81`):
- `WordForm` - Inflections (plural, past_tense, gerund)
- `GrammarPattern` - Grammar frames ("[Tn]", "sb/sth")
- `Collocation` - Word combinations with frequency
- `UsageNote` - Usage guidance (type, text)
- `MeaningCluster` - Semantic grouping (id, name, description, order, relevance)

**Document Model** (`relationships.py:81` - MongoDB):
- `WordRelationship` - Inter-word links (synonym, antonym, derived_from) with strength 0-1

## Parameter Models

**CLI/API Isomorphism** (`parameters.py:458`):

```python
# Lookup
class LookupParams(BaseModel):
    providers: list[DictionaryProvider] = [WIKTIONARY]
    languages: list[Language] = [ENGLISH]
    force_refresh: bool = False
    no_ai: bool = False

# Search
class SearchParams(BaseModel):
    languages: list[Language] = [ENGLISH]
    max_results: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.6, ge=0.0, le=1.0)
    mode: str = "smart"  # smart|exact|fuzzy|semantic
    force_rebuild: bool = False

# Corpus
class CorpusCreateParams(BaseModel):
    name: str
    language: Language
    vocabulary: list[str]  # Must be non-empty
    enable_semantic: bool = False
    ttl_hours: float = Field(ge=0.001, le=24.0)

# 10+ more parameter models
```

## Response Models

**Base Response** (`responses.py:378`):
```python
class BaseResponse(BaseModel):
    timestamp: datetime  # Auto-generated
    version: str = "v1"
```

**Domain Responses**:
- `LookupResponse` - word, definitions, pronunciation, etymology, providers_used, cache_hit
- `SearchResponse` - query, results, total_found, mode, has_results
- `WordlistResponse` - name, word_count, unique_word_count, top_words
- `CorpusResponse` - name, vocabulary_size, has_semantic, search_count (computed field)
- `CacheStatsResponse` - namespace, total_entries, hit_rate, size_bytes
- `DatabaseStatsResponse` - overview, provider_coverage, quality_metrics
- `HealthResponse` - status, components, uptime_seconds

**Generic Response** (`responses.py:378`):
```python
class ListResponse[T](BaseResponse):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool

    @property
    def count(self) -> int:
        return len(self.items)

# Type aliases
WordListResponse = ListResponse[dict[str, Any]]
CorpusListResponse = ListResponse[CorpusResponse]
```

## Literature Models

**Author Info** (`literature.py:102`):
```python
class AuthorInfo(BaseModel):
    name: str
    birth_year: int | None
    death_year: int | None
    nationality: str | None
    period: Period  # ANCIENT, MEDIEVAL, RENAISSANCE, etc.
    primary_genre: Genre  # EPIC, DRAMA, POETRY, etc.
    language: Language = ENGLISH

    def get_semantic_era_index(self) -> int:
        """Maps Period to 0-7 for WOTD training"""

    def get_semantic_style_index(self) -> int:
        """Maps Genre to 0-4 for WOTD training"""
```

**Enums**:
- `LiteratureProvider` - GUTENBERG, INTERNET_ARCHIVE, WIKISOURCE, etc.
- `Genre` - 13 genres (EPIC, DRAMA, POETRY, NOVEL, etc.)
- `Period` - 9 periods (ANCIENT, MEDIEVAL, RENAISSANCE, etc.)

## Validation

**Field Validators** (`parameters.py:458`):
```python
@field_validator("providers", mode="before")
def parse_providers(v: Any) -> list[DictionaryProvider]:
    """Convert string → enum with error handling"""

@field_validator("vocabulary", mode="after")
def validate_vocabulary_not_empty(v: list[str]) -> list[str]:
    """Ensure corpus vocabulary non-empty"""
```

**Field Constraints**:
```python
frequency_band: int | None = Field(ge=1, le=5)
confidence: float = Field(ge=0.0, le=1.0)
max_results: int = Field(ge=1, le=100)
sort_order: str = Field(pattern="^(asc|desc)$")
```

**Computed Fields** (`responses.py:378`):
```python
@computed_field
@property
def search_count(self) -> int:
    return self.statistics.get("search_count", 0) if self.statistics else 0
```

## Model Hierarchy

```
BaseModel (Pydantic)
├── Non-Document Models
│   ├── Enums (Language, DictionaryProvider, Period, Genre)
│   ├── BaseMetadata + AccessTrackingMixin
│   ├── ModelInfo (AI provenance)
│   ├── Etymology, WordForm, Collocation, etc. (nested)
│   ├── Parameters (LookupParams, SearchParams, etc.)
│   └── Responses (BaseResponse → LookupResponse, etc.)
│
└── Document Models (MongoDB + Beanie)
    ├── Word(Document, BaseMetadata)
    ├── Definition(Document, BaseMetadata)
    ├── DictionaryEntry(Document, BaseMetadata)
    ├── Pronunciation(Document, BaseMetadata)
    ├── Example(Document, BaseMetadata)
    ├── Fact(Document, BaseMetadata)
    └── WordRelationship(Document, BaseMetadata)
```

## Design Patterns

- **Enumerations** - Controlled vocabularies (Language, Provider, Period, Genre)
- **Mixin** - AccessTrackingMixin for reusable tracking
- **Parameter Object** - Shared CLI/API parameters
- **Discriminated Union** - Example type: "generated" | "literature"
- **Registry** - ResourceType → Model class mapping
- **Composite** - Nested models (Definition contains WordForm, Collocation, etc.)
- **Type Parameterization** - ListResponse[T]
- **Lazy Computation** - Word.__init__() auto-computes normalized, lemma
- **Semantic Mapping** - AuthorInfo methods for ML feature extraction

## MongoDB Indices

**Optimized Query Patterns**:
- Word: `[(text, language)]`, `normalized`, `lemma`
- Definition: `word_id`, `part_of_speech`, `[(word_id, part_of_speech)]`
- DictionaryEntry: `word_id`, `provider`, `[(word_id, provider)]`
- WordRelationship: `[(from_word_id, relationship_type)]`, `[(to_word_id, relationship_type)]`

## Statistics

- **8 files**, **1,571 LOC**
- **50+ models**: 9 MongoDB documents, 40+ Pydantic models
- **7 @field_validators** with custom validation logic
- **179+ total models** across entire backend (includes nested/embedded)
- **100% type coverage** - strict TypeScript-like typing
