"""Language corpus implementation with provider integration.

Minimal implementation following KISS principles - inherits from Corpus,
delegates tree operations to TreeCorpusManager.
"""

from __future__ import annotations

from beanie import PydanticObjectId

from ...models.base import Language
from ...providers.language.models import LanguageSource
from ...providers.language.scraper.url import URLLanguageConnector
from ...providers.language.sources import LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE
from ...utils.logging import get_logger
from ..core import Corpus
from ..manager import get_tree_corpus_manager
from ..models import CorpusType

logger = get_logger(__name__)


class LanguageCorpus(Corpus):
    """Language corpus with provider integration.
    
    Inherits all fields and functionality from Corpus.
    Adds language-specific source management via TreeCorpusManager.
    """
    
    async def add_language_source(
        self,
        source: LanguageSource,
    ) -> PydanticObjectId | None:
        """Add a language source as child corpus.
        
        Args:
            source: Language source configuration
            
        Returns:
            Child corpus ID if created
        """
        logger.info(f"Adding language source: {source.name}")
        
        # Fetch vocabulary using connector
        connector = URLLanguageConnector()
        result = await connector.fetch(source.url)
        
        if not result or not isinstance(result, dict):
            logger.warning(f"No vocabulary fetched for source: {source.name}")
            return None
        
        # Extract vocabulary from result
        vocabulary = result.get("vocabulary", [])
        if not vocabulary:
            logger.warning(f"No vocabulary in result for source: {source.name}")
            return None
        
        # Create child corpus from source vocabulary
        child = await Corpus.create(
            corpus_name=f"{self.corpus_name}_{source.name}",
            vocabulary=vocabulary,
            language=source.language,
            semantic=self.metadata.get("semantic_enabled", False),
            model_name=self.metadata.get("model_name"),
        )
        
        # Set corpus type
        child.corpus_type = CorpusType.LANGUAGE
        
        # Save child corpus
        await child.save()
        
        if not child.corpus_id:
            logger.warning(f"Failed to save child corpus for source: {source.name}")
            return None
        
        # Update tree relationships via TreeCorpusManager
        manager = get_tree_corpus_manager()
        
        # Ensure parent has ID
        if not self.corpus_id:
            await self.save()
        
        # Update parent-child relationship
        if self.corpus_id:
            await manager.update_parent(self.corpus_id, child.corpus_id)
        
        # Aggregate vocabularies into parent
        if self.corpus_id and child.corpus_id:
            self.child_corpus_ids.append(child.corpus_id)
            # Note: aggregate_vocabularies aggregates from the corpus and its children automatically
            await manager.aggregate_vocabularies(self.corpus_id)
        
        logger.info(
            f"Added source '{source.name}' with {len(vocabulary)} words"
        )
        
        return child.corpus_id
    
    @classmethod
    async def create_from_language(
        cls,
        corpus_name: str,
        language: Language,
        semantic: bool = False,
        model_name: str | None = None,
    ) -> LanguageCorpus:
        """Create corpus from all available sources for a language.
        
        Args:
            corpus_name: Name for the corpus
            language: Target language
            semantic: Enable semantic search
            model_name: Embedding model name
            
        Returns:
            Configured LanguageCorpus with all language sources
        """
        logger.info(f"Creating language corpus for {language.value}")
        
        # Create master corpus
        corpus = cls(
            corpus_name=corpus_name,
            corpus_type=CorpusType.LANGUAGE,
            language=language,
            is_master=True,
            vocabulary=[],  # Empty vocabulary initially, will be aggregated from sources
        )
        
        corpus.metadata = {
            "semantic_enabled": semantic,
            "model_name": model_name,
        }
        
        # Save to get corpus ID
        await corpus.save()
        
        # Get all sources for language
        sources = LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE.get(language, [])
        
        if not sources:
            logger.warning(f"No sources found for language: {language.value}")
            return corpus
        
        logger.info(f"Adding {len(sources)} sources for {language.value}")
        
        # Add all sources
        for source in sources:
            try:
                await corpus.add_language_source(source)
            except Exception as e:
                logger.error(f"Failed to add source {source.name}: {e}")
                continue
        
        # Final save with aggregated vocabulary
        await corpus.save()
        
        logger.info(
            f"Created language corpus with {len(corpus.vocabulary)} unique words"
        )
        
        return corpus
    
    async def remove_source(self, source_name: str) -> None:
        """Remove a language source by name.
        
        Args:
            source_name: Name of source to remove
        """
        manager = get_tree_corpus_manager()
        
        # Find child corpus with matching name
        child_name = f"{self.corpus_name}_{source_name}"
        
        # Get child corpus using keyword argument
        child_meta = await manager.get_corpus(corpus_name=child_name)
        if not child_meta or not child_meta.id:
            logger.warning(f"Source '{source_name}' not found")
            return
        
        # Use manager to properly remove and delete child
        if self.corpus_id and child_meta.id:
            await manager.remove_child(
                parent_id=self.corpus_id,
                child_id=child_meta.id,
                delete_child=True  # Delete the child corpus
            )
            
            # Update local child_corpus_ids list
            if child_meta.id in self.child_corpus_ids:
                self.child_corpus_ids.remove(child_meta.id)
        
        logger.info(f"Removed source: {source_name}")
    
    async def update_source(
        self,
        source_name: str,
        source: LanguageSource,
    ) -> None:
        """Update a language source.
        
        Args:
            source_name: Current source name
            source: New source configuration
        """
        # Simple approach: remove old, add new
        await self.remove_source(source_name)
        await self.add_language_source(source)