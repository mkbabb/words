# Corpus Redesign - KISS & DRY Architecture

## Core Principles

1. **Inherit from Corpus** - No intermediate classes
2. **Delegate to TreeCorpusManager** - All tree/aggregation operations
3. **Minimal additions** - Only domain-specific methods
4. **No field duplication** - Reuse Corpus fields
5. **Remove MultisourceCorpus** - Overengineered complexity

## Class Architecture

### LanguageCorpus (corpus/language/core.py)

```python
class LanguageCorpus(Corpus):
    """Language corpus with provider integration.
    
    Inherits all fields from Corpus - no duplication.
    Delegates tree operations to TreeCorpusManager.
    """
    
    async def add_language_source(
        self,
        source: LanguageSource,
    ) -> None:
        """Add a language source as child corpus.
        
        Creates child corpus from source vocabulary.
        Uses TreeCorpusManager for tree operations.
        """
        # Fetch vocabulary using URLLanguageConnector
        connector = URLLanguageConnector()
        entry = await connector.fetch_language_entry(source)
        
        # Create child corpus
        child = await Corpus.create(
            corpus_name=f"{self.corpus_name}_{source.name}",
            vocabulary=entry.vocabulary,
            language=source.language,
        )
        
        # Save child and update tree
        manager = get_tree_corpus_manager()
        await child.save()
        await manager.update_parent(self.corpus_id, child.corpus_id)
        
        # Aggregate vocabularies
        await manager.aggregate_vocabularies(
            self.corpus_id, 
            [child.corpus_id]
        )
    
    @classmethod
    async def create_from_language(
        cls,
        corpus_name: str,
        language: Language,
    ) -> LanguageCorpus:
        """Create corpus from all sources for a language.
        
        Uses LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE mapping.
        """
        # Create master corpus
        corpus = cls(
            corpus_name=corpus_name,
            corpus_type=CorpusType.LANGUAGE,
            language=language,
            is_master=True,
        )
        await corpus.save()
        
        # Add all language sources
        sources = LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE.get(language, [])
        for source in sources:
            await corpus.add_language_source(source)
        
        return corpus
    
    async def remove_source(self, source_name: str) -> None:
        """Remove a source - delegates to TreeCorpusManager."""
        # Find child corpus by name
        # Remove via TreeCorpusManager
        # Re-aggregate
        pass
    
    async def update_source(self, source_name: str, source: LanguageSource) -> None:
        """Update a source - delegates to TreeCorpusManager."""
        # Remove old source
        # Add new source
        pass
```

### LiteratureCorpus (corpus/literature/core.py)

```python
class LiteratureCorpus(Corpus):
    """Literature corpus with work management.
    
    Inherits all fields from Corpus - no duplication.
    Delegates tree operations to TreeCorpusManager.
    """
    
    async def add_literature_source(
        self,
        source: LiteratureSource,
    ) -> None:
        """Add a literature work as child corpus.
        
        Creates child corpus from work vocabulary.
        Uses TreeCorpusManager for tree operations.
        """
        # Fetch work using appropriate connector
        connector = get_literature_connector(source)
        entry = await connector.fetch_literature_entry(source)
        
        # Create child corpus
        child = await Corpus.create(
            corpus_name=f"{self.corpus_name}_{source.name}",
            vocabulary=entry.extracted_vocabulary,
            language=source.language,
        )
        
        # Save child and update tree
        manager = get_tree_corpus_manager()
        await child.save()
        await manager.update_parent(self.corpus_id, child.corpus_id)
        
        # Aggregate vocabularies
        await manager.aggregate_vocabularies(
            self.corpus_id,
            [child.corpus_id]
        )
    
    async def add_author_works(
        self,
        author: AuthorInfo,
        work_ids: list[str],
    ) -> None:
        """Add multiple works from an author.
        
        Creates child corpora for each work.
        """
        for work_id in work_ids:
            source = LiteratureSource(
                name=f"{author.name}_{work_id}",
                gutenberg_id=work_id,
                author=author,
            )
            await self.add_literature_source(source)
    
    async def remove_work(self, work_name: str) -> None:
        """Remove a work - delegates to TreeCorpusManager."""
        # Find child corpus by name
        # Remove via TreeCorpusManager  
        # Re-aggregate
        pass
    
    async def update_work(self, work_name: str, source: LiteratureSource) -> None:
        """Update a work - delegates to TreeCorpusManager."""
        # Remove old work
        # Add new work
        pass
```

## Key Changes from Current Implementation

### Remove:
- MultisourceCorpus class (311 lines)
- Duplicate field definitions in Metadata classes
- Complex source management logic
- Direct vocabulary aggregation

### Keep:
- Base Corpus functionality
- Inner Metadata pattern (but minimal)
- TreeCorpusManager integration

### Add (minimal):
- Domain-specific source addition methods
- Factory methods for language/literature
- Delegation to TreeCorpusManager

## TreeCorpusManager Usage

All tree operations delegated:
- `add_child_corpus()` - Add sources as children
- `remove_child_corpus()` - Remove sources
- `aggregate_vocabularies()` - Vocabulary union
- `update_parent()` - Maintain relationships
- `save_corpus_tree()` - Persist entire tree

## Benefits

1. **Simplicity**: ~100 lines instead of 500+
2. **DRY**: No field duplication
3. **KISS**: Single responsibility per class
4. **Maintainable**: Clear separation of concerns
5. **Extensible**: Easy to add new corpus types

## Migration Path

1. Remove MultisourceCorpus from core.py
2. Update LanguageCorpus to inherit from Corpus
3. Update LiteratureCorpus to inherit from Corpus
4. Remove complex Metadata classes
5. Update imports and exports
6. Run tests and fix type errors