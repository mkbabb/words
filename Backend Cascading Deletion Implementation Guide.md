# Backend Cascading Deletion Implementation Guide

## Executive Summary

This document provides a comprehensive strategy for implementing robust cascading deletion across the Floridify backend. The current implementation has partial cascade support but lacks consistency and completeness, particularly in handling media references and cross-model dependencies.

## 1. Data Model Relationship Analysis

### Core Document Relationships

Based on analysis of `/backend/src/floridify/models/models.py` and related files, here's the complete relationship map:

```
Word (Root Entity)
├── Pronunciation (1:M) - word_id
│   └── AudioMedia (M:M) - audio_file_ids[]
├── Definition (1:M) - word_id
│   ├── Example (1:M) - definition_id
│   └── ImageMedia (M:M) - image_ids[]
├── Fact (1:M) - word_id
├── ProviderData (1:M) - word_id
│   ├── Definition (M:M) - definition_ids[]
│   └── Pronunciation (1:1) - pronunciation_id
└── SynthesizedDictionaryEntry (1:1) - word_id
    ├── Definition (M:M) - definition_ids[]
    ├── Fact (M:M) - fact_ids[]
    ├── Pronunciation (1:1) - pronunciation_id
    ├── ImageMedia (M:M) - image_ids[]
    └── ProviderData (M:M) - source_provider_data_ids[]

WordList (Independent Entity)
└── WordListItem (Embedded) - words[]
    ├── Word (M:1) - word_id
    └── Definition (M:M) - selected_definition_ids[]

Media Entities (Shared Resources)
├── ImageMedia - Referenced by Definition, SynthesizedDictionaryEntry
└── AudioMedia - Referenced by Pronunciation
```

### Current Cascade Implementation Status

| Repository | Has _cascade_delete | Cascade Behavior | Issues |
|------------|-------------------|------------------|---------|
| WordRepository | ✅ Complete | Deletes all word-related documents | Works correctly |
| DefinitionRepository | ✅ Partial | Deletes examples only | Missing image reference cleanup |
| ImageRepository | ❌ Stub | No-op implementation | **CRITICAL: No reference cleanup** |
| AudioRepository | ❌ Unknown | Not examined | Likely missing |
| SynthesisRepository | ❌ Stub | No-op implementation | Missing comprehensive cleanup |
| WordListRepository | ❌ Stub | No-op implementation | Self-contained, appropriate |
| ExampleRepository | ❌ Not found | Not implemented | Missing repository |
| FactRepository | ❌ Not found | Not implemented | Missing repository |

### **Critical Issue Identified**

The immediate problem is that `ImageMedia.delete()` does not clean up references in:
- `Definition.image_ids[]`
- `SynthesizedDictionaryEntry.image_ids[]`

This causes orphaned references and potential application errors when trying to load images.

## 2. Cascading Deletion Strategy Design

### Deletion Patterns

#### Hard Delete (Physical Removal)
- **Use for**: Core entities (Word, Definition, Example)
- **Behavior**: Permanently remove document and all dependent documents
- **Transaction**: Required for multi-document operations

#### Soft Delete (Logical Removal) 
- **Use for**: Audit-sensitive entities (if needed in future)
- **Behavior**: Mark as deleted, preserve data
- **Not currently implemented**: Consider for future enhancement

#### Reference Cleanup (Orphan Prevention)
- **Use for**: Shared resources (ImageMedia, AudioMedia)
- **Behavior**: Remove references from other documents before deletion
- **Critical**: Prevents orphaned references

### Cascade vs. Prevent Strategy

| Entity Type | Strategy | Reasoning |
|-------------|----------|-----------|
| Word → * | CASCADE | Word is root entity, all dependents become meaningless |
| Definition → Examples | CASCADE | Examples are meaningless without definition |
| Definition → Images | CLEANUP | Images might be shared, remove references only |
| Pronunciation → Audio | CLEANUP | Audio might be shared |
| SynthesizedEntry → * | CLEANUP | References other entities, don't own them |
| WordList → * | CLEANUP | References words, doesn't own them |

### Performance Considerations

- Use `asyncio.gather()` for parallel deletion operations
- Batch operations for large reference arrays
- Use MongoDB `$pull` operations for efficient reference removal
- Implement deletion in dependency order to avoid constraint violations

## 3. Implementation Architecture

### Enhanced Base Repository Pattern

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Protocol
from enum import Enum
import asyncio
from beanie import Document, PydanticObjectId

T = TypeVar("T", bound=Document)

class CascadeAction(Enum):
    """Defines how cascade deletion should behave."""
    DELETE = "delete"  # Hard delete the related document
    CLEANUP = "cleanup"  # Remove references but keep document
    PREVENT = "prevent"  # Prevent deletion if references exist

class CascadeRule(Protocol):
    """Protocol for cascade deletion rules."""
    target_model: type[Document]
    action: CascadeAction
    reference_field: str  # Field containing the reference
    cleanup_fields: list[str] = []  # Fields to clean in target documents

class EnhancedBaseRepository[T: Document, CreateSchema, UpdateSchema](BaseRepository[T, CreateSchema, UpdateSchema]):
    """Enhanced base repository with comprehensive cascade support."""
    
    def __init__(self, model: type[T]):
        super().__init__(model)
        self._cascade_rules: list[CascadeRule] = []
        self._setup_cascade_rules()
    
    @abstractmethod
    def _setup_cascade_rules(self) -> None:
        """Define cascade rules for this repository."""
        pass
    
    async def delete(self, id: PydanticObjectId, cascade: bool = True, transaction: bool = True) -> bool:
        """Enhanced delete with comprehensive cascade support."""
        doc = await self.get(id, raise_on_missing=True)
        if doc is None:
            return False
        
        if transaction:
            # Use MongoDB transaction for consistency
            async with await get_transaction() as session:
                return await self._delete_with_cascade(doc, cascade, session)
        else:
            return await self._delete_with_cascade(doc, cascade, None)
    
    async def _delete_with_cascade(self, doc: T, cascade: bool, session=None) -> bool:
        """Execute deletion with cascade rules."""
        if cascade and self._cascade_rules:
            # Execute cascade rules in parallel where possible
            cascade_tasks = []
            for rule in self._cascade_rules:
                if rule.action == CascadeAction.DELETE:
                    cascade_tasks.append(self._cascade_delete_documents(doc, rule, session))
                elif rule.action == CascadeAction.CLEANUP:
                    cascade_tasks.append(self._cascade_cleanup_references(doc, rule, session))
                elif rule.action == CascadeAction.PREVENT:
                    await self._cascade_check_prevent(doc, rule)
            
            if cascade_tasks:
                await asyncio.gather(*cascade_tasks)
        
        # Delete the main document
        if session:
            await doc.delete(session=session)
        else:
            await doc.delete()
        
        return True
    
    async def _cascade_delete_documents(self, doc: T, rule: CascadeRule, session=None) -> None:
        """Delete related documents."""
        query = {rule.reference_field: str(doc.id)}
        if session:
            await rule.target_model.find(query).delete(session=session)
        else:
            await rule.target_model.find(query).delete()
    
    async def _cascade_cleanup_references(self, doc: T, rule: CascadeRule, session=None) -> None:
        """Clean up references in other documents."""
        # Find documents that reference this one
        reference_value = doc.id
        
        for cleanup_field in rule.cleanup_fields:
            # Remove reference from array fields
            update_query = {"$pull": {cleanup_field: reference_value}}
            find_query = {cleanup_field: reference_value}
            
            if session:
                await rule.target_model.find(find_query).update(update_query, session=session)
            else:
                await rule.target_model.find(find_query).update(update_query)
    
    async def _cascade_check_prevent(self, doc: T, rule: CascadeRule) -> None:
        """Check if deletion should be prevented due to references."""
        query = {rule.reference_field: str(doc.id)}
        count = await rule.target_model.find(query).count()
        if count > 0:
            raise ValueError(f"Cannot delete {self.model.__name__} {doc.id}: {count} {rule.target_model.__name__} documents reference it")

# Transaction helper
async def get_transaction():
    """Get MongoDB transaction session."""
    from floridify.storage.mongodb import get_database
    db = await get_database()
    return db.client.start_session()
```

### Cascade Rule Definitions

```python
from dataclasses import dataclass
from typing import Type

@dataclass
class CascadeRuleDefinition:
    target_model: Type[Document]
    action: CascadeAction
    reference_field: str = ""
    cleanup_fields: list[str] = None
    
    def __post_init__(self):
        if self.cleanup_fields is None:
            self.cleanup_fields = []
```

## 4. Specific Repository Implementations

### 4.1 Enhanced ImageRepository

**Critical Priority**: This repository needs immediate attention to resolve orphaned references.

```python
class ImageRepository(EnhancedBaseRepository[ImageMedia, ImageCreate, ImageUpdate]):
    """Repository for image operations with comprehensive cascade cleanup."""
    
    def _setup_cascade_rules(self) -> None:
        """Define cascade rules for image deletion."""
        self._cascade_rules = [
            CascadeRuleDefinition(
                target_model=Definition,
                action=CascadeAction.CLEANUP,
                cleanup_fields=["image_ids"]
            ),
            CascadeRuleDefinition(
                target_model=SynthesizedDictionaryEntry,
                action=CascadeAction.CLEANUP,
                cleanup_fields=["image_ids"]
            )
        ]
    
    async def delete(self, item_id: PydanticObjectId, cascade: bool = True) -> bool:
        """Delete image with reference cleanup."""
        image = await self.get(item_id, raise_on_missing=True)
        if image is None:
            return False
        
        if cascade:
            # Clean up references in parallel
            await asyncio.gather(
                self._cleanup_definition_references(item_id),
                self._cleanup_synthesis_references(item_id)
            )
        
        await image.delete()
        return True
    
    async def _cleanup_definition_references(self, image_id: PydanticObjectId) -> None:
        """Remove image references from definitions."""
        await Definition.find(
            {"image_ids": image_id}
        ).update(
            {"$pull": {"image_ids": image_id}}
        )
    
    async def _cleanup_synthesis_references(self, image_id: PydanticObjectId) -> None:
        """Remove image references from synthesized entries."""
        await SynthesizedDictionaryEntry.find(
            {"image_ids": image_id}
        ).update(
            {"$pull": {"image_ids": image_id}}
        )
    
    async def get_orphaned_images(self) -> list[ImageMedia]:
        """Get images not referenced anywhere."""
        # This is complex with MongoDB - consider implementing as background job
        all_images = await ImageMedia.find().to_list()
        referenced_ids = set()
        
        # Collect all image references
        definitions = await Definition.find({"image_ids": {"$ne": []}}).to_list()
        for def_doc in definitions:
            referenced_ids.update(def_doc.image_ids)
        
        syntheses = await SynthesizedDictionaryEntry.find({"image_ids": {"$ne": []}}).to_list()
        for synth_doc in syntheses:
            referenced_ids.update(synth_doc.image_ids)
        
        # Return orphaned images
        return [img for img in all_images if img.id not in referenced_ids]
```

### 4.2 Enhanced AudioRepository

```python
class AudioRepository(EnhancedBaseRepository[AudioMedia, AudioCreate, AudioUpdate]):
    """Repository for audio operations with reference cleanup."""
    
    def _setup_cascade_rules(self) -> None:
        """Define cascade rules for audio deletion."""
        self._cascade_rules = [
            CascadeRuleDefinition(
                target_model=Pronunciation,
                action=CascadeAction.CLEANUP,
                cleanup_fields=["audio_file_ids"]
            )
        ]
    
    async def delete(self, item_id: PydanticObjectId, cascade: bool = True) -> bool:
        """Delete audio with reference cleanup."""
        audio = await self.get(item_id, raise_on_missing=True)
        if audio is None:
            return False
        
        if cascade:
            # Clean up pronunciation references
            await Pronunciation.find(
                {"audio_file_ids": item_id}
            ).update(
                {"$pull": {"audio_file_ids": item_id}}
            )
        
        await audio.delete()
        return True
```

### 4.3 Enhanced DefinitionRepository

```python
class DefinitionRepository(EnhancedBaseRepository[Definition, DefinitionCreate, DefinitionUpdate]):
    """Repository for Definition operations with comprehensive cascade."""
    
    def _setup_cascade_rules(self) -> None:
        """Define cascade rules for definition deletion."""
        self._cascade_rules = [
            CascadeRuleDefinition(
                target_model=Example,
                action=CascadeAction.DELETE,
                reference_field="definition_id"
            )
        ]
    
    async def delete(self, id: PydanticObjectId, cascade: bool = True) -> bool:
        """Delete definition with comprehensive cascade."""
        definition = await self.get(id, raise_on_missing=True)
        if definition is None:
            return False
        
        if cascade:
            # Parallel cleanup operations
            await asyncio.gather(
                # Delete examples (they belong to this definition)
                Example.find({"definition_id": str(id)}).delete(),
                # Clean up references in synthesis entries
                SynthesizedDictionaryEntry.find(
                    {"definition_ids": id}
                ).update(
                    {"$pull": {"definition_ids": id}}
                ),
                # Clean up references in provider data
                ProviderData.find(
                    {"definition_ids": id}
                ).update(
                    {"$pull": {"definition_ids": id}}
                )
            )
        
        await definition.delete()
        return True
```

### 4.4 Enhanced SynthesisRepository

```python
class SynthesisRepository(EnhancedBaseRepository[SynthesizedDictionaryEntry, SynthesisCreate, SynthesisUpdate]):
    """Repository for synthesized entries with reference-only cleanup."""
    
    def _setup_cascade_rules(self) -> None:
        """Synthesis entries reference but don't own other entities."""
        # No cascade rules - synthesis entries only reference other entities
        self._cascade_rules = []
    
    async def delete(self, id: PydanticObjectId, cascade: bool = True) -> bool:
        """Delete synthesis entry - no cascade needed as it only references."""
        entry = await self.get(id, raise_on_missing=True)
        if entry is None:
            return False
        
        # SynthesizedDictionaryEntry only contains references to other entities
        # It doesn't own them, so no cascade deletion needed
        await entry.delete()
        return True
```

### 4.5 Enhanced WordRepository (Already Good)

The current word repository implementation is already comprehensive:

```python
# Current implementation is good, but could be enhanced with the new pattern:
class WordRepository(EnhancedBaseRepository[Word, WordCreate, WordUpdate]):
    """Repository for Word operations - complete cascade deletion."""
    
    def _setup_cascade_rules(self) -> None:
        """Word owns most related entities."""
        self._cascade_rules = [
            CascadeRuleDefinition(
                target_model=Definition,
                action=CascadeAction.DELETE,
                reference_field="word_id"
            ),
            CascadeRuleDefinition(
                target_model=Pronunciation,
                action=CascadeAction.DELETE,
                reference_field="word_id"
            ),
            CascadeRuleDefinition(
                target_model=Fact,
                action=CascadeAction.DELETE,
                reference_field="word_id"
            ),
            CascadeRuleDefinition(
                target_model=ProviderData,
                action=CascadeAction.DELETE,
                reference_field="word_id"
            ),
            CascadeRuleDefinition(
                target_model=SynthesizedDictionaryEntry,
                action=CascadeAction.DELETE,
                reference_field="word_id"
            ),
            # Clean up references in word lists
            CascadeRuleDefinition(
                target_model=WordList,
                action=CascadeAction.CLEANUP,
                cleanup_fields=["words.word_id"]  # Embedded document field
            )
        ]
```

## 5. Current Issue Resolution: ImageMedia Deletion

### Immediate Implementation

Here's the specific code to fix the immediate image deletion problem:

```python
# File: /backend/src/floridify/api/repositories/image_repository.py

async def delete(self, item_id: PydanticObjectId, cascade: bool = True) -> bool:
    """Delete image with comprehensive reference cleanup."""
    image = await self.get(item_id, raise_on_missing=True)
    if image is None:
        return False
    
    if cascade:
        # Import here to avoid circular imports
        from ...models import Definition, SynthesizedDictionaryEntry
        
        # Clean up references in parallel
        await asyncio.gather(
            # Remove from Definition.image_ids arrays
            Definition.find(
                {"image_ids": item_id}
            ).update(
                {"$pull": {"image_ids": item_id}}
            ),
            # Remove from SynthesizedDictionaryEntry.image_ids arrays
            SynthesizedDictionaryEntry.find(
                {"image_ids": item_id}
            ).update(
                {"$pull": {"image_ids": item_id}}
            )
        )
    
    # Delete the image document
    await image.delete()
    return True
```

### Router Update

Update the image deletion endpoint to use cascade by default:

```python
# File: /backend/src/floridify/api/routers/media/images.py

@router.delete("/{image_id}", status_code=204, response_model=None)
async def delete_image(
    image_id: PydanticObjectId,
    cascade: bool = Query(True, description="Clean up references in other documents"),
    repo: ImageRepository = Depends(get_image_repo),
) -> None:
    """Delete an image with reference cleanup.
    
    Path Parameters:
        - image_id: ID of the image to delete
        
    Query Parameters:
        - cascade: Whether to clean up references (default: True)
    
    Errors:
        404: Image not found
    """
    await repo.delete(image_id, cascade=cascade)
```

## 6. Testing Strategy

### Unit Tests for Cascade Operations

```python
import pytest
from beanie import PydanticObjectId
from floridify.models import Word, Definition, ImageMedia, SynthesizedDictionaryEntry
from floridify.api.repositories import ImageRepository, DefinitionRepository

class TestCascadeDeletion:
    
    @pytest.fixture
    async def setup_image_references(self):
        """Setup test data with image references."""
        # Create test entities
        word = await Word(text="test", normalized="test").create()
        image = await ImageMedia(
            data=b"fake_image_data",
            format="png",
            size_bytes=100,
            width=100,
            height=100
        ).create()
        
        # Create definition with image reference
        definition = await Definition(
            word_id=word.id,
            part_of_speech="noun",
            text="test definition",
            image_ids=[image.id]
        ).create()
        
        # Create synthesis entry with image reference
        synthesis = await SynthesizedDictionaryEntry(
            word_id=word.id,
            image_ids=[image.id]
        ).create()
        
        return {
            "word": word,
            "image": image,
            "definition": definition,
            "synthesis": synthesis
        }
    
    async def test_image_cascade_deletion(self, setup_image_references):
        """Test that image deletion removes references."""
        data = await setup_image_references
        image_repo = ImageRepository()
        
        # Delete image with cascade
        await image_repo.delete(data["image"].id, cascade=True)
        
        # Verify image is deleted
        deleted_image = await ImageMedia.get(data["image"].id)
        assert deleted_image is None
        
        # Verify references are cleaned up
        updated_definition = await Definition.get(data["definition"].id)
        assert data["image"].id not in updated_definition.image_ids
        
        updated_synthesis = await SynthesizedDictionaryEntry.get(data["synthesis"].id)
        assert data["image"].id not in updated_synthesis.image_ids
    
    async def test_definition_cascade_deletion(self, setup_test_data):
        """Test that definition deletion cascades to examples."""
        # Setup definition with examples
        definition = await Definition(...).create()
        example = await Example(definition_id=definition.id, text="test").create()
        
        # Delete definition
        def_repo = DefinitionRepository()
        await def_repo.delete(definition.id, cascade=True)
        
        # Verify cascade
        assert await Definition.get(definition.id) is None
        assert await Example.get(example.id) is None
```

### Integration Tests

```python
class TestCascadeIntegration:
    
    async def test_word_complete_cascade(self):
        """Test complete word deletion cascade."""
        # Create word with all related entities
        word = await Word(text="comprehensive", normalized="comprehensive").create()
        
        # Create all related entities
        definition = await Definition(word_id=word.id, ...).create()
        example = await Example(definition_id=definition.id, ...).create()
        pronunciation = await Pronunciation(word_id=word.id, ...).create()
        fact = await Fact(word_id=word.id, ...).create()
        synthesis = await SynthesizedDictionaryEntry(word_id=word.id, ...).create()
        
        # Delete word
        word_repo = WordRepository()
        await word_repo.delete(word.id, cascade=True)
        
        # Verify complete cascade
        assert await Word.get(word.id) is None
        assert await Definition.get(definition.id) is None
        assert await Example.get(example.id) is None
        assert await Pronunciation.get(pronunciation.id) is None
        assert await Fact.get(fact.id) is None
        assert await SynthesizedDictionaryEntry.get(synthesis.id) is None
```

## 7. Migration and Deployment Strategy

### Phase 1: Critical Fix (Immediate)
1. **Update ImageRepository** with reference cleanup
2. **Deploy to fix immediate orphaned reference issues**
3. **Run cleanup script for existing orphaned references**

### Phase 2: Comprehensive Enhancement (Next Sprint)
1. **Implement EnhancedBaseRepository pattern**
2. **Update all repositories to use new pattern**
3. **Add comprehensive test coverage**
4. **Update API documentation**

### Phase 3: Advanced Features (Future)
1. **Add soft delete support**
2. **Implement cascade prevention rules**
3. **Add cascade audit logging**
4. **Performance optimization with bulk operations**

### Cleanup Script for Existing Data

```python
async def cleanup_orphaned_image_references():
    """Clean up existing orphaned image references."""
    
    # Find all image IDs that exist
    existing_images = await ImageMedia.find().to_list()
    existing_image_ids = {img.id for img in existing_images}
    
    # Clean up definitions
    definitions = await Definition.find({"image_ids": {"$ne": []}}).to_list()
    for definition in definitions:
        original_count = len(definition.image_ids)
        definition.image_ids = [img_id for img_id in definition.image_ids if img_id in existing_image_ids]
        if len(definition.image_ids) != original_count:
            await definition.save()
            print(f"Cleaned {original_count - len(definition.image_ids)} orphaned references from definition {definition.id}")
    
    # Clean up synthesis entries
    syntheses = await SynthesizedDictionaryEntry.find({"image_ids": {"$ne": []}}).to_list()
    for synthesis in syntheses:
        original_count = len(synthesis.image_ids)
        synthesis.image_ids = [img_id for img_id in synthesis.image_ids if img_id in existing_image_ids]
        if len(synthesis.image_ids) != original_count:
            await synthesis.save()
            print(f"Cleaned {original_count - len(synthesis.image_ids)} orphaned references from synthesis {synthesis.id}")
```

## 8. Implementation Checklist

### Immediate Priority (Critical Issue)
- [ ] Update `ImageRepository.delete()` method with reference cleanup
- [ ] Add cascade parameter to image deletion API endpoint
- [ ] Test image deletion with reference cleanup
- [ ] Deploy fix to production
- [ ] Run cleanup script for existing orphaned references

### High Priority (Next Sprint)
- [ ] Implement `EnhancedBaseRepository` base class
- [ ] Create `CascadeRule` and related infrastructure
- [ ] Update `AudioRepository` with reference cleanup
- [ ] Enhance `DefinitionRepository` with comprehensive cascade
- [ ] Add comprehensive unit tests for cascade operations
- [ ] Update API documentation

### Medium Priority (Future Sprints)
- [ ] Implement cascade prevention rules where appropriate
- [ ] Add cascade audit logging
- [ ] Create orphan detection and cleanup utilities
- [ ] Implement soft delete support if needed
- [ ] Performance optimization with batch operations
- [ ] Add integration tests for complex cascade scenarios

### Low Priority (Nice to Have)
- [ ] Background job for orphan cleanup
- [ ] Cascade operation metrics and monitoring
- [ ] Admin interface for managing orphaned resources
- [ ] Cascade operation undo functionality

## 9. Monitoring and Observability

### Metrics to Track
- Number of cascade operations per day
- Orphaned reference detection frequency
- Cascade operation performance
- Failed cascade operations

### Logging Strategy
```python
import structlog

logger = structlog.get_logger(__name__)

async def delete_with_logging(self, id: PydanticObjectId, cascade: bool = True) -> bool:
    """Delete with comprehensive logging."""
    logger.info(
        "Starting deletion",
        entity_type=self.model.__name__,
        entity_id=str(id),
        cascade_enabled=cascade
    )
    
    start_time = time.time()
    try:
        result = await self._delete_with_cascade(doc, cascade)
        
        logger.info(
            "Deletion completed",
            entity_type=self.model.__name__,
            entity_id=str(id),
            duration=time.time() - start_time,
            success=True
        )
        return result
    except Exception as e:
        logger.error(
            "Deletion failed",
            entity_type=self.model.__name__,
            entity_id=str(id),
            error=str(e),
            duration=time.time() - start_time
        )
        raise
```

## Conclusion

This implementation guide provides a comprehensive strategy for implementing robust cascading deletion across the Floridify backend. The immediate priority is fixing the `ImageMedia` deletion issue, followed by systematic enhancement of all repositories with the new cascade pattern.

The proposed architecture ensures data integrity, prevents orphaned references, and provides a consistent approach to handling entity relationships across the entire system. The phased implementation approach allows for immediate critical fixes while building toward a comprehensive solution.

Key benefits of this approach:
1. **Data Integrity**: Prevents orphaned references and maintains referential consistency
2. **Performance**: Uses parallel operations and MongoDB bulk updates for efficiency
3. **Maintainability**: Consistent pattern across all repositories
4. **Flexibility**: Support for different cascade strategies per relationship
5. **Observability**: Comprehensive logging and monitoring capabilities

The implementation should begin with the critical `ImageRepository` fix and progress through the phases outlined above.