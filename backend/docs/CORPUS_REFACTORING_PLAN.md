# Comprehensive Corpus Architecture Refactoring Plan

## Overview
Complete migration from filesystem-based lexicon system to MongoDB-based corpus architecture, eliminating redundancy and introducing no legacy behavior.

## Core Principles
- **KISS**: Single unified corpus system, no dual paths
- **DRY**: One corpus management system for all use cases
- **No Legacy**: Complete removal of filesystem caching
- **Deterministic**: Reproducible corpus IDs across systems

## Phase 1: Directory & Module Restructuring

### 1.1 Rename lexicon → corpus
```
src/floridify/search/lexicon/ → src/floridify/search/corpus/
├── __init__.py
├── core.py (formerly lexicon/core.py)
├── language_loader.py → corpus_loader.py
├── sources.py (unchanged)
├── parser.py (unchanged)
└── scrapers/ (unchanged)
```

### 1.2 Move corpus.py → corpus/core.py
```
src/floridify/search/corpus.py → src/floridify/search/corpus/core.py
```

### 1.3 Create corpus utilities
```
src/floridify/search/utils.py (NEW)
└── Corpus ID generation and naming utilities

src/floridify/utils/utils.py
└── Add generate_slug() from wordlist/utils.py
```

## Phase 2: Core Refactoring Tasks

### 2.1 Corpus ID Helper Functions
Create deterministic corpus ID generation in `search/utils.py`:

```python
def generate_corpus_id(corpus_type: CorpusType, languages: list[Language] | None = None, custom_id: str | None = None) -> str:
    """Generate deterministic corpus ID.
    
    Rules:
    - language_search: sorted languages joined with dash (en-fr-de)
    - wordlist: provided custom_id or generated slug
    - wordlist_names: static "wordlist-names"
    - custom: provided custom_id or generated slug
    """
    if corpus_type == CorpusType.LANGUAGE_SEARCH and languages:
        # Sort languages for deterministic ID
        sorted_langs = sorted([lang.value for lang in languages])
        return "-".join(sorted_langs)
    elif custom_id:
        return custom_id
    else:
        # Generate slug for wordlists and custom corpora
        return generate_slug()

def get_corpus_name(corpus_type: CorpusType, corpus_id: str) -> str:
    """Generate consistent corpus name for MongoDB storage."""
    return f"{corpus_type.value}_{corpus_id}"
```

### 2.2 Move Slug Generation
Extract from `wordlist/utils.py` to `utils/utils.py`:

```python
# utils/utils.py
import coolname

def generate_slug(word_count: int = 3) -> str:
    """Generate human-readable slug (e.g., 'myrtle-goldfish-swim')."""
    try:
        return coolname.generate_slug(word_count)
    except Exception:
        # Fallback to UUID
        import uuid
        return str(uuid.uuid4())[:8]
```

### 2.3 Rename LexiconLanguageLoader → CorpusLanguageLoader
Transform to use MongoDB caching exclusively:

```python
class CorpusLanguageLoader:
    """Load language data and create corpus in MongoDB."""
    
    def __init__(self, force_rebuild: bool = False):
        # No cache_dir - all caching in MongoDB
        self.force_rebuild = force_rebuild
        self._corpus_manager: CorpusManager | None = None
    
    async def load_languages(self, languages: list[Language]) -> CorpusData:
        """Load languages and create/retrieve corpus from MongoDB."""
        # Generate deterministic corpus ID
        corpus_id = generate_corpus_id(CorpusType.LANGUAGE_SEARCH, languages)
        corpus_name = get_corpus_name(CorpusType.LANGUAGE_SEARCH, corpus_id)
        
        # Check MongoDB cache first
        if not self.force_rebuild:
            cached_data = await CorpusData.find_one({"corpus_name": corpus_name})
            if cached_data and not cached_data.is_expired():
                return cached_data
        
        # Load from sources if not cached
        words, phrases = await self._load_from_sources(languages)
        
        # Create corpus via CorpusManager
        corpus_manager = await get_corpus_manager()
        await corpus_manager.create_corpus(
            corpus_type=CorpusType.LANGUAGE_SEARCH,
            corpus_id=corpus_id,
            words=words,
            phrases=phrases,
            semantic=len(words) < 10000,  # Auto-enable for small corpora
        )
        
        return CorpusData(
            corpus_name=corpus_name,
            words=words,
            phrases=phrases,
            languages=languages,
        )
```

### 2.4 Update LanguageSearch
Remove cache_dir and integrate with CorpusLanguageLoader:

```python
class LanguageSearch:
    def __init__(self, languages: list[Language], semantic: bool = False):
        # No cache_dir parameter
        self.languages = sorted(languages)  # Sort for deterministic ID
        self.semantic = semantic
        self._corpus_loader: CorpusLanguageLoader | None = None
        
    async def initialize(self):
        # Use CorpusLanguageLoader
        self._corpus_loader = CorpusLanguageLoader()
        corpus_data = await self._corpus_loader.load_languages(self.languages)
        
        # Create search engine with corpus_name (not semantic_corpus_name)
        corpus_id = generate_corpus_id(CorpusType.LANGUAGE_SEARCH, self.languages)
        corpus_name = get_corpus_name(CorpusType.LANGUAGE_SEARCH, corpus_id)
        
        self.search_engine = SearchEngine(
            lexicon=SimpleLexicon(corpus_data.words, corpus_data.phrases),
            corpus_name=corpus_name,  # Renamed from semantic_corpus_name
            semantic=self.semantic,
        )
```

### 2.5 Update SemanticSearch for MongoDB-only Caching
Remove filesystem caching completely:

```python
class SemanticSearch:
    def __init__(self, corpus_name: str, force_rebuild: bool = False):
        # No cache_dir - MongoDB only
        self.corpus_name = corpus_name
        self.force_rebuild = force_rebuild
        
    async def _save_to_mongodb(self):
        """Save embeddings to MongoDB with compression."""
        cache_entry = SemanticIndexCache(
            corpus_name=self.corpus_name,
            vocabulary=self.vocabulary,
            embeddings=self._compress_embeddings(),
            metadata={...},
            ttl_hours=168.0,
        )
        await cache_entry.save()
    
    async def _load_from_mongodb(self):
        """Load embeddings from MongoDB."""
        cache_entry = await SemanticIndexCache.find_one({
            "corpus_name": self.corpus_name
        })
        if cache_entry and not cache_entry.is_expired():
            self._decompress_embeddings(cache_entry.embeddings)
            return True
        return False
```

### 2.6 Update SearchEngine
Change semantic_corpus_name → corpus_name:

```python
class SearchEngine:
    def __init__(self, lexicon, corpus_name: str, semantic: bool = False):
        self.lexicon = lexicon
        self.corpus_name = corpus_name  # Renamed
        self.semantic = semantic
        
        if semantic:
            self.semantic_search = SemanticSearch(
                corpus_name=corpus_name,  # Use unified naming
            )
```

## Phase 3: Remove Filesystem Dependencies

### 3.1 Remove cache_dir from all components
- ✅ CorpusLanguageLoader: No cache_dir
- ✅ LanguageSearch: No cache_dir
- ✅ SemanticSearch: No cache_dir
- ✅ CacheManager: Deprecate file-based caching methods
- ✅ HTTPClient: Use MongoDB for HTTP cache

### 3.2 Eliminate SimpleLexicon as separate entity
Functionality absorbed into CorpusData model:

```python
class CorpusData(Document):
    """MongoDB document for corpus storage."""
    corpus_name: str
    corpus_type: CorpusType
    words: list[str]
    phrases: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    expires_at: datetime
    
    class Settings:
        name = "corpus_data"
        indexes = [
            IndexModel([("corpus_name", 1)], unique=True),
            IndexModel([("expires_at", 1)], expireAfterSeconds=0),
        ]
    
    def to_lexicon(self) -> SimpleLexicon:
        """Convert to lexicon for search engine."""
        return SimpleLexicon(self.words, self.phrases)
```

## Phase 4: Implementation Order

1. **Utils Refactoring** (30 min)
   - Move generate_slug to utils/utils.py
   - Create search/utils.py with corpus helpers

2. **Directory Restructuring** (45 min)
   - Rename lexicon → corpus
   - Move corpus.py → corpus/core.py
   - Update all imports

3. **CorpusLanguageLoader** (2 hours)
   - Rename from LexiconLanguageLoader
   - Remove cache_dir, implement MongoDB caching
   - Integrate with CorpusManager

4. **LanguageSearch Updates** (1 hour)
   - Remove cache_dir parameter
   - Use CorpusLanguageLoader
   - Switch to corpus_name

5. **SemanticSearch MongoDB** (1.5 hours)
   - Remove filesystem caching
   - Implement MongoDB-only storage
   - Update compression/decompression

6. **SearchEngine Updates** (30 min)
   - Rename semantic_corpus_name → corpus_name
   - Update all references

7. **Testing & Validation** (1 hour)
   - Run mypy and ruff
   - Test API endpoints
   - Verify MongoDB caching

## Phase 5: Cleanup

### 5.1 Remove deprecated code
- Delete old filesystem cache directories
- Remove unused imports
- Clean up legacy configuration

### 5.2 Update documentation
- Update CLAUDE.md files
- Add migration guide
- Document new corpus architecture

## Benefits of Refactoring

1. **Unified Storage**: All caching in MongoDB
2. **Deterministic IDs**: Reproducible corpus identification
3. **No Redundancy**: Single corpus management system
4. **Simplified API**: corpus_name instead of semantic_corpus_name
5. **Auto-optimization**: Automatic semantic for small corpora
6. **Better Performance**: MongoDB TTL, compression, indexing
7. **Cleaner Architecture**: Clear separation of concerns

## Success Metrics

- ✅ No filesystem caching remains
- ✅ All corpus types use CorpusManager
- ✅ Deterministic corpus IDs
- ✅ MongoDB-only storage
- ✅ No lexicon objects (replaced by corpus)
- ✅ Unified corpus_name parameter
- ✅ All tests pass with mypy and ruff