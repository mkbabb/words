# Data Model & API Refactor Plan - Floridify Dictionary

## Executive Summary

This document outlines a **performance-first, spartan refactor** of the dictionary data models and REST API. The goal is to eliminate redundancy, optimize query patterns, and enable granular updates while maintaining simplicity.

## Current State Analysis

### Data Model Issues
1. **Redundant Storage**: Provider data stored in both `DictionaryEntry` and `SynthesizedDictionaryEntry`
2. **No True Relationships**: Using document embedding instead of foreign keys
3. **Weak References**: WordList uses indices instead of IDs for definitions
4. **Missing Media Support**: No image or audio fields in models
5. **Opaque Metadata**: Unstructured dicts instead of atomic fields

### API Limitations
1. **No Update Endpoints**: Cannot PATCH definitions or components
2. **No Batch Operations**: Each word requires individual lookup
3. **Limited Field Selection**: No projection/GraphQL-style queries
4. **No Granular Updates**: Must regenerate entire entries

### Performance Bottlenecks
1. **Sequential Processing**: AI synthesis processes clusters one-by-one
2. **Large Documents**: Entire documents loaded for partial updates
3. **No Query Optimization**: Missing compound indexes for common patterns
4. **Limited Caching**: No database-level caching strategy

## Proposed Architecture

### Core Design Principles
- **Foreign Keys Over Embedding**: Use MongoDB references for relationships
- **Atomic Fields**: Every field individually addressable and updatable
- **Minimal Payload**: Send only requested data via field projection
- **Batch-First**: Design for bulk operations from the start
- **Cache Everything**: Multi-level caching with Redis + MongoDB

### New Data Model Structure

```python
# Phase 1: Normalized Core Models

class BaseMetadata(BaseModel):
    """Homogenous metadata pattern for all models"""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)
    
class Media(BaseModel):
    """Media storage for images/audio"""
    type: Literal["image", "audio"]
    url: str
    format: str  # png, jpg, mp3, wav
    size_bytes: int
    metadata: dict[str, Any]

class PronunciationV2(BaseMetadata):
    """Enhanced pronunciation with audio support"""
    word_id: str  # FK to Word
    phonetic: str
    ipa: str | None
    audio_files: list[Media] = []  # Multiple accents
    
class ExampleV2(BaseMetadata):
    """Standalone example model"""
    definition_id: str  # FK to Definition
    text: str
    type: Literal["generated", "literature"]
    source_id: str | None  # FK to Source if literature
    regenerable: bool = True
    quality_score: float = 0.8

class DefinitionV2(BaseMetadata):
    """Atomic definition with foreign keys"""
    word_id: str  # FK to Word
    provider_id: str | None  # FK to Provider
    word_type: str
    text: str
    meaning_cluster: str
    cluster_order: int  # For consistent ordering
    synonyms: list[str] = []  # Denormalized for performance
    antonyms: list[str] = []
    images: list[Media] = []  # Visual definitions
    
class FactV2(BaseMetadata):
    """Standalone fact model"""
    word_id: str  # FK to Word
    content: str
    category: str
    confidence: float
    source: str

class Word(Document):
    """Core word document - minimal"""
    text: str = Field(index=True, unique=True)
    normalized: str = Field(index=True)  # For search
    language: str = "en"
    metadata: BaseMetadata
    
    class Settings:
        name = "words"
        indexes = [
            [("text", 1), ("language", 1)],  # Compound index
            "normalized",
            "metadata.updated_at"
        ]

class Provider(Document):
    """Dictionary provider metadata"""
    name: str = Field(unique=True)
    api_endpoint: str | None
    last_sync: datetime
    metadata: BaseMetadata
    
    class Settings:
        name = "providers"

class SynthesizedEntryV2(Document):
    """Aggregated entry with foreign keys"""
    word_id: str = Field(index=True)  # FK to Word
    pronunciation_ids: list[str] = []  # FK to Pronunciation
    definition_ids: list[str] = []  # FK to Definition  
    fact_ids: list[str] = []  # FK to Fact
    synthesis_metadata: dict[str, Any]
    metadata: BaseMetadata
    
    class Settings:
        name = "synthesized_entries"
        indexes = [
            "word_id",
            [("word_id", 1), ("metadata.version", -1)]
        ]
```

### API Enhancement Plan

#### 1. Granular Update Endpoints

```python
# Atomic field updates
PATCH /api/definitions/{id}
Body: {"text": "Updated definition", "version": 2}

# Batch definition updates
PATCH /api/definitions/batch
Body: [{"id": "def1", "synonyms": ["new", "synonyms"]}]

# Component regeneration
POST /api/words/{id}/regenerate
Body: {"components": ["examples", "facts"], "definition_ids": ["def1"]}

# Bulk synonym management
PUT /api/definitions/{id}/synonyms
Body: {"synonyms": ["list", "of", "synonyms"], "mode": "replace"}
```

#### 2. Field Projection

```python
# Request specific fields only
GET /api/words/{id}?fields=text,definitions.text,definitions.synonyms

# Exclude heavy fields
GET /api/words/{id}?exclude=definitions.examples,facts

# Pagination for nested arrays
GET /api/definitions?word_id={id}&limit=10&offset=20
```

#### 3. Batch Operations

```python
# Batch word lookup
POST /api/words/lookup-batch
Body: {"words": ["efflorescence", "obstreperous"], "fields": ["definitions"]}

# Batch fact generation
POST /api/facts/generate-batch
Body: {"word_ids": ["id1", "id2"], "categories": ["etymology"]}

# Bulk updates with transactions
POST /api/updates/batch
Body: {
  "operations": [
    {"type": "update_definition", "id": "def1", "data": {...}},
    {"type": "add_example", "definition_id": "def1", "data": {...}}
  ]
}
```

#### 4. Performance Features

```python
# Conditional requests
GET /api/words/{id}
Headers: If-None-Match: "etag123"
Response: 304 Not Modified

# Cursor-based pagination
GET /api/words?cursor=eyJpZCI6MTIzfQ&limit=50

# Response streaming for large datasets
GET /api/words/export?format=jsonl
Response: Streaming JSON Lines

# Aggregation endpoints
GET /api/stats/definitions?group_by=word_type
```

### Database Optimization Strategy

#### 1. Indexes

```javascript
// Compound indexes for common queries
db.definitions.createIndex({ "word_id": 1, "meaning_cluster": 1 })
db.definitions.createIndex({ "provider_id": 1, "metadata.updated_at": -1 })
db.examples.createIndex({ "definition_id": 1, "type": 1 })

// Text search optimization
db.words.createIndex({ "normalized": "text", "text": "text" })

// Time-based queries
db.synthesized_entries.createIndex({ "metadata.updated_at": -1 })
```

#### 2. Query Optimization

```python
# Use projection
await DefinitionV2.find(
    {"word_id": word_id},
    projection={"text": 1, "synonyms": 1}
).to_list()

# Bulk operations
await DefinitionV2.insert_many(definitions, ordered=False)

# Atomic updates with version control
await DefinitionV2.find_one_and_update(
    {"_id": def_id, "metadata.version": version},
    {"$set": update_data, "$inc": {"metadata.version": 1}},
    return_document=ReturnDocument.AFTER
)
```

#### 3. Caching Strategy

```python
# Redis for hot data
CACHE_LAYERS = {
    "L1": "Redis (1-hour TTL)",  # Synthesized entries
    "L2": "MongoDB TTL collection (24-hour)",  # API responses  
    "L3": "Application memory (5-min)",  # Frequent lookups
}

# Cache-aside pattern
async def get_synthesized_entry(word_id: str):
    # L1: Redis
    if cached := await redis.get(f"synth:{word_id}"):
        return cached
    
    # L2: MongoDB
    if entry := await SynthesizedEntryV2.find_one({"word_id": word_id}):
        await redis.setex(f"synth:{word_id}", 3600, entry)
        return entry
    
    # L3: Generate
    return await generate_entry(word_id)
```

## Implementation Phases

### Phase 1: Data Model Migration (Week 1)
1. Create new normalized models with foreign keys
2. Write migration scripts to transform existing data
3. Add Media support for images/audio
4. Implement BaseMetadata pattern
5. Create compound indexes

### Phase 2: API Enhancement (Week 2)  
1. Add PATCH endpoints for atomic updates
2. Implement field projection/selection
3. Create batch operation endpoints
4. Add cursor pagination
5. Implement conditional requests

### Phase 3: Performance Optimization (Week 3)
1. Set up Redis caching layer
2. Implement connection pooling optimization
3. Add query monitoring and profiling
4. Optimize hot code paths
5. Implement response streaming

### Phase 4: Integration & Testing (Week 4)
1. Update AI components for new models
2. Modify frontend TypeScript interfaces
3. Create comprehensive test suite
4. Performance benchmarking
5. Documentation updates

## Success Metrics

### Performance Targets
- API response time: <50ms (p95)
- Database query time: <20ms (p95)
- Batch operations: >1000 items/second
- Cache hit rate: >80%
- Memory usage: <500MB baseline

### Quality Metrics
- Zero data redundancy
- 100% atomic update capability
- Full backward compatibility
- >95% test coverage
- <0.1% error rate

## Migration Strategy

### Zero-Downtime Migration
1. **Dual-Write Phase**: Write to both old and new models
2. **Backfill Phase**: Migrate historical data in batches
3. **Validation Phase**: Verify data integrity
4. **Cutover Phase**: Switch reads to new models
5. **Cleanup Phase**: Remove old models

### Rollback Plan
1. Feature flags for new endpoints
2. Versioned API with deprecation warnings
3. Database snapshots before migration
4. Incremental rollout by user percentage

## Code Examples

### Atomic Definition Update
```python
@router.patch("/definitions/{definition_id}")
async def update_definition(
    definition_id: str,
    update: DefinitionUpdate,
    version: int | None = None
) -> DefinitionV2:
    query = {"_id": definition_id}
    if version:
        query["metadata.version"] = version
    
    result = await DefinitionV2.find_one_and_update(
        query,
        {
            "$set": update.dict(exclude_unset=True),
            "$inc": {"metadata.version": 1},
            "$currentDate": {"metadata.updated_at": True}
        },
        return_document=ReturnDocument.AFTER
    )
    
    if not result:
        raise HTTPException(404, "Definition not found or version mismatch")
    
    # Invalidate caches
    await redis.delete(f"def:{definition_id}")
    
    return result
```

### Batch Lookup with Projection
```python
@router.post("/words/lookup-batch")
async def batch_lookup(
    request: BatchLookupRequest,
    fields: list[str] | None = None
) -> list[dict]:
    # Build projection
    projection = build_projection(fields) if fields else None
    
    # Parallel lookups with projection
    tasks = [
        get_word_with_relations(word, projection)
        for word in request.words
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [
        r if not isinstance(r, Exception) else None
        for r in results
    ]
```

### Optimized Search with Streaming
```python
@router.get("/words/export")
async def export_words(format: str = "jsonl") -> StreamingResponse:
    async def generate():
        async for word in Word.find_all().batch_size(100):
            entry = await build_full_entry(word)
            yield json.dumps(entry) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
```

## Conclusion

This refactor plan prioritizes **performance, simplicity, and maintainability**. By normalizing data models, implementing foreign key relationships, and enabling granular updates, we create a foundation for scalable dictionary operations while reducing complexity and redundancy.

The phased approach ensures smooth migration with minimal disruption, while the performance targets guarantee a responsive user experience even at scale.