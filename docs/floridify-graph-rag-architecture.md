# Floridify Graph RAG Architecture
*Implementation Blueprint for Literature Store*

## System Overview

Extends Floridify's existing cascade search with graph-based RAG for sophisticated literature retrieval and word suggestion augmentation. The system employs state-of-the-art graph creation techniques with automated entity extraction, incremental construction, and quality validation.

## Graph Creation Pipeline

### 1. Entity Extraction System

```python
# backend/src/floridify/graph/extractor.py
from typing import Literal
import anthropic
import openai

class LiteraryEntityExtractor:
    """Multi-level entity extraction with confidence scoring."""
    
    # Schema-constrained extraction schema
    EXTRACTION_SCHEMA = {
        "characters": {
            "type": "array",
            "items": {
                "name": "string",
                "role": "string",
                "psychological_profile": "string",
                "relationships": [{"target": "string", "type": "string"}],
                "confidence": "number"
            }
        },
        "themes": {
            "type": "array",
            "items": {
                "theme": "string",
                "evidence": ["string"],
                "development": "string",
                "confidence": "number"
            }
        },
        "stylistic_elements": {
            "narrative_voice": "string",
            "literary_devices": ["string"],
            "temporal_structure": "string"
        },
        "intertextual_references": {
            "type": "array",
            "items": {
                "source_work": "string",
                "reference_type": Literal["citation", "allusion", "quotation"],
                "evidence": "string",
                "confidence": "number"
            }
        }
    }
    
    async def extract_from_document(
        self,
        document: LiteratureDocument,
        context_window: int = 200000  # Claude 3.5 Sonnet
    ) -> dict:
        """Extract entities with multi-model validation."""
        
        # Chunk if needed for context window
        chunks = self._smart_chunk(document.text, context_window)
        
        # Primary extraction with Claude 3.5
        primary_extractions = []
        for chunk in chunks:
            extraction = await self._claude_extract(chunk)
            primary_extractions.append(extraction)
        
        # Merge chunk extractions
        merged = self._merge_chunk_extractions(primary_extractions)
        
        # Validation with GPT-4o
        validated = await self._gpt4o_validate(document.text[:128000], merged)
        
        # Calculate confidence scores
        final = self._calculate_confidence(merged, validated)
        
        return final
    
    async def _claude_extract(self, text: str) -> dict:
        """Claude 3.5 Sonnet extraction with schema constraint."""
        
        prompt = f"""
        Extract literary entities from this text according to the schema.
        Preserve ambiguity and multiple interpretations where appropriate.
        
        TEXT: {text}
        
        SCHEMA: {json.dumps(self.EXTRACTION_SCHEMA)}
        
        Output valid JSON matching the schema.
        """
        
        response = await anthropic.AsyncAnthropic().messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192
        )
        
        return json.loads(response.content[0].text)
```

### 2. Graph Schema Design

```python
# backend/src/floridify/graph/schema.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class EntityType(str, Enum):
    """Literary entity types."""
    WORK = "work"
    CHARACTER = "character"
    THEME = "theme"
    MOTIF = "motif"
    AUTHOR = "author"
    WORD = "word"
    CONCEPT = "concept"

class RelationshipType(str, Enum):
    """Literary relationship types."""
    # Direct relationships
    CITES = "cites"
    QUOTES = "quotes"
    ALLUDES_TO = "alludes_to"
    
    # Thematic relationships
    EXPRESSES_THEME = "expresses_theme"
    SHARES_MOTIF = "shares_motif"
    PARALLEL_THEME = "parallel_theme"
    
    # Stylistic relationships
    INFLUENCED_BY = "influenced_by"
    STYLISTIC_ECHO = "stylistic_echo"
    PARODIES = "parodies"
    
    # Character relationships
    RELATED_TO = "related_to"
    APPEARS_IN = "appears_in"
    EVOLVES_TO = "evolves_to"

class LiteraryNode(BaseModel):
    """Node in the literary graph."""
    
    id: str = Field(description="Unique identifier")
    type: EntityType
    name: str
    
    # Metadata
    metadata: dict = {}
    embeddings: Optional[bytes] = None  # Compressed embeddings
    
    # Literary-specific attributes
    time_period: Optional[str] = None
    cultural_context: Optional[str] = None
    genre: Optional[str] = None
    
    # Quality metrics
    confidence_score: float = 1.0
    extraction_method: str = "llm"
    validation_status: str = "pending"

class LiteraryEdge(BaseModel):
    """Edge in the literary graph."""
    
    source_id: str
    target_id: str
    type: RelationshipType
    
    # Relationship strength and evidence
    weight: float = 1.0
    confidence: float = 1.0
    evidence: list[str] = []
    
    # Temporal information
    temporal_context: Optional[str] = None
    
    # Validation
    validated_by: Optional[str] = None
    validation_timestamp: Optional[datetime] = None
```

### 3. Incremental Construction Engine

```python
# backend/src/floridify/graph/incremental.py
import rustworkx as rx
from typing import AsyncIterator

class IncrementalGraphConstructor:
    """High-performance incremental graph construction."""
    
    def __init__(self):
        self.graph = rx.PyDiGraph()
        self.node_index = {}  # id -> node_index
        self.edge_index = {}  # (source, target, type) -> edge_index
        
        # Delta tracking
        self.delta_encoder = DeltaEncoder()
        self.version_control = GraphVersionControl()
        
        # Performance optimization
        self.batch_size = 1000
        self.pending_updates = []
    
    async def add_literature_stream(
        self,
        document_stream: AsyncIterator[LiteratureDocument]
    ) -> None:
        """Process document stream with incremental updates."""
        
        async for document in document_stream:
            # Extract entities and relationships
            extraction = await self.extractor.extract_from_document(document)
            
            # Batch updates for performance
            self.pending_updates.append(extraction)
            
            if len(self.pending_updates) >= self.batch_size:
                await self._flush_updates()
    
    async def _flush_updates(self) -> None:
        """Apply batched updates efficiently."""
        
        if not self.pending_updates:
            return
        
        # Process all pending extractions
        new_nodes = []
        new_edges = []
        
        for extraction in self.pending_updates:
            # Add nodes
            for entity_type, entities in extraction.items():
                if entity_type == "characters":
                    for char in entities:
                        node = LiteraryNode(
                            id=f"char:{char['name']}",
                            type=EntityType.CHARACTER,
                            name=char['name'],
                            metadata=char,
                            confidence_score=char.get('confidence', 1.0)
                        )
                        new_nodes.append(node)
            
            # Extract relationships
            for char in extraction.get('characters', []):
                for rel in char.get('relationships', []):
                    edge = LiteraryEdge(
                        source_id=f"char:{char['name']}",
                        target_id=f"char:{rel['target']}",
                        type=RelationshipType.RELATED_TO,
                        confidence=char.get('confidence', 1.0)
                    )
                    new_edges.append(edge)
        
        # Add to graph in batch
        await self._batch_add_nodes(new_nodes)
        await self._batch_add_edges(new_edges)
        
        # Track delta for version control
        delta = GraphDelta(
            added_nodes=new_nodes,
            added_edges=new_edges
        )
        await self.version_control.commit(delta)
        
        self.pending_updates.clear()
```

## Core Components

### 1. Graph Storage Layer

```python
# backend/src/floridify/graph/core.py
import rustworkx as rx
from motor.motor_asyncio import AsyncIOMotorClient

class LiteratureGraph:
    """High-performance graph for literature relationships."""
    
    def __init__(self):
        self.graph = rx.PyDiGraph()  # rustworkx for speed
        self.node_map: dict[str, int] = {}  # word/work -> node_id
        self.embeddings: dict[int, np.ndarray] = {}  # cached embeddings
    
    async def add_literature_work(self, work: LiteratureWork):
        """Add work to graph with relationships."""
        work_node = self.graph.add_node(work)
        
        # Connect to existing works via citations
        for citation in work.citations:
            if citation in self.node_map:
                self.graph.add_edge(
                    work_node, 
                    self.node_map[citation],
                    {"type": "cites", "weight": citation.strength}
                )
        
        # Connect via thematic similarity
        similar_works = await self._find_thematically_similar(work)
        for similar in similar_works:
            self.graph.add_edge(
                work_node,
                similar.node_id,
                {"type": "theme", "weight": similar.score}
            )
```

### 2. Enhanced Search Pipeline

```python
# backend/src/floridify/search/graph_rag.py
from floridify.search.core import SearchEngine

class GraphRAGSearchEngine(SearchEngine):
    """Extends existing SearchEngine with graph capabilities."""
    
    async def _graph_enhanced_search(
        self,
        query: str,
        literature_context: list[str]
    ) -> list[SearchResult]:
        """Graph-aware search with literature grounding."""
        
        # Phase 1: Standard cascade (existing)
        base_results = await self._smart_search_cascade(query)
        
        # Phase 2: Graph traversal via Personalized PageRank
        if literature_context:
            graph_results = await self._personalized_pagerank_search(
                query, 
                seed_nodes=literature_context
            )
            
            # Phase 3: Fusion
            return self._reciprocal_rank_fusion([base_results, graph_results])
        
        return base_results
    
    async def _personalized_pagerank_search(
        self, 
        query: str, 
        seed_nodes: list[str]
    ) -> list[GraphSearchResult]:
        """HippoRAG-style PPR for multi-hop reasoning."""
        
        # Get query embedding
        query_embedding = await self.embedder.embed(query)
        
        # Initialize PPR from seed nodes
        personalization = {
            self.graph.node_map[seed]: 1.0 / len(seed_nodes)
            for seed in seed_nodes
            if seed in self.graph.node_map
        }
        
        # Compute PPR scores
        ppr_scores = rx.pagerank(
            self.graph.graph,
            personalized=personalization,
            alpha=0.85
        )
        
        # Rank by PPR * semantic similarity
        results = []
        for node_id, ppr_score in ppr_scores.items():
            node_embedding = self.graph.embeddings.get(node_id)
            if node_embedding is not None:
                similarity = cosine_similarity(query_embedding, node_embedding)
                combined_score = ppr_score * similarity
                results.append((node_id, combined_score))
        
        return sorted(results, key=lambda x: x[1], reverse=True)[:self.top_k]
```

### 3. Literature-Aware Word Suggestion

```python
# backend/src/floridify/api/routers/suggestions.py
from floridify.graph.core import LiteratureGraph

class LiteratureSuggestionEngine:
    """Word suggestions with literature grounding."""
    
    def __init__(self):
        self.graph = LiteratureGraph()
        self.search = GraphRAGSearchEngine()
    
    async def suggest_words_from_literature(
        self,
        prompt: str,
        source_works: list[str],
        count: int = 10
    ) -> list[WordSuggestion]:
        """
        Generate word suggestions grounded in specific literature.
        
        Example: "10 good words from Hamlet" seeds with Hamlet's vocabulary.
        """
        
        # Extract thematic context from source works
        thematic_context = await self._extract_themes(source_works)
        
        # Perform graph-enhanced search
        candidates = await self.search._graph_enhanced_search(
            prompt,
            literature_context=source_works
        )
        
        # Filter and rank by literary relevance
        suggestions = []
        for candidate in candidates:
            # Check attestation in source works
            attestation = await self._check_attestation(
                candidate.word,
                source_works
            )
            
            if attestation.confidence > 0.7:
                suggestions.append(WordSuggestion(
                    word=candidate.word,
                    source_work=attestation.primary_source,
                    context=attestation.context,
                    literary_significance=attestation.significance
                ))
        
        return suggestions[:count]
```

### 4. Incremental Graph Updates

```python
# backend/src/floridify/graph/updater.py
class IncrementalGraphUpdater:
    """Efficient graph updates without full reconstruction."""
    
    async def add_user_literature(
        self,
        user_id: str,
        document: LiteratureDocument
    ):
        """Add document to user's personal literature graph."""
        
        # Extract entities and relationships
        entities = await self._extract_entities(document)
        relationships = await self._extract_relationships(entities)
        
        # Update graph incrementally
        async with self.graph.write_lock():
            new_nodes = []
            for entity in entities:
                if entity.id not in self.graph.node_map:
                    node_id = self.graph.graph.add_node(entity)
                    self.graph.node_map[entity.id] = node_id
                    new_nodes.append(node_id)
            
            # Add edges
            for rel in relationships:
                self.graph.graph.add_edge(
                    self.graph.node_map[rel.source],
                    self.graph.node_map[rel.target],
                    {"type": rel.type, "weight": rel.weight}
                )
            
            # Update embeddings for new nodes only
            await self._update_embeddings(new_nodes)
```

### 5. MongoDB Integration

```python
# backend/src/floridify/models/graph_models.py
from beanie import Document
from pydantic import Field

class LiteratureWork(Document):
    """Literature work in graph."""
    
    title: str
    author: str
    period: str
    genre: str
    
    # Graph relationships
    citations: list[Citation] = []
    themes: list[Theme] = []
    vocabulary: list[str] = []
    
    # Embeddings
    semantic_embedding: bytes  # Compressed FAISS-compatible
    style_embedding: bytes
    
    class Settings:
        name = "literature_works"
        indexes = [
            "title",
            "author",
            "period",
            ("author", "title")  # Compound index
        ]

class UserLiteratureGraph(Document):
    """Per-user literature graph snapshot."""
    
    user_id: PydanticObjectId
    graph_data: bytes  # Serialized rustworkx graph
    node_map: dict[str, int]
    last_updated: datetime
    
    class Settings:
        name = "user_literature_graphs"
```

## Integration Points

### 1. Existing Search Enhancement

```python
# Modify backend/src/floridify/search/core.py
class SearchEngine:
    async def search(
        self,
        query: str,
        *,
        literature_context: Optional[list[str]] = None  # NEW
    ) -> list[SearchResult]:
        if literature_context:
            return await self._graph_enhanced_search(query, literature_context)
        return await self._smart_search_cascade(query)
```

### 2. API Endpoint Addition

```python
# backend/src/floridify/api/routers/literature.py
@router.post("/suggest-from-literature")
async def suggest_from_literature(
    request: LiteratureSuggestionRequest
) -> list[WordSuggestion]:
    """Generate word suggestions from specific literary works."""
    engine = LiteratureSuggestionEngine()
    return await engine.suggest_words_from_literature(
        request.prompt,
        request.source_works,
        request.count
    )
```

### 3. Caching Integration

```python
# Extend backend/src/floridify/caching/unified.py
class UnifiedCache:
    async def cache_graph_result(
        self,
        key: str,
        result: GraphSearchResult,
        ttl: int = 3600
    ):
        """Cache graph traversal results."""
        # Existing cache infrastructure handles this
        await self.set(key, result, ttl=ttl)
```

## Performance Guarantees

| Operation | Target Latency | Method |
|-----------|---------------|---------|
| Graph traversal | <50ms | rustworkx + cached PPR |
| Literature suggestion | <100ms | Pre-computed embeddings |
| Incremental update | <10ms | Partial graph updates |
| Full graph load | <500ms | Compressed serialization |

## Memory Footprint

- Base graph: ~1KB per node (work/concept)
- Embeddings: 768 floats → 97 bytes (compressed)
- 10K works: ~10MB graph + 1MB embeddings
- Per-user overhead: <100MB for extensive libraries

## Deployment Phases

### Phase 1: Core Infrastructure (Week 1)
```bash
# Add dependencies
uv add rustworkx faiss-cpu
```
- Implement `LiteratureGraph` class
- Add graph storage models
- Create basic PPR traversal

### Phase 2: Search Integration (Week 2)
- Extend `SearchEngine` with graph methods
- Implement fusion algorithms
- Add literature context parameters

### Phase 3: API & Testing (Week 3)
- Create `/suggest-from-literature` endpoint
- Add comprehensive tests
- Performance benchmarking

## Monitoring

```python
# backend/src/floridify/graph/metrics.py
class GraphMetrics:
    """Track graph RAG performance."""
    
    graph_size: int
    avg_traversal_time: float
    cache_hit_rate: float
    ppr_convergence_iterations: int
    suggestion_accuracy: float
```

## Conclusion

This architecture provides Floridify with state-of-the-art graph RAG capabilities while:
- Maintaining sub-100ms response times
- Reusing existing infrastructure
- Minimizing new dependencies
- Supporting per-user literature stores
- Enabling sophisticated literary analysis