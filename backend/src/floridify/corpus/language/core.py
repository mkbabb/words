"""Language corpus implementation with provider integration.

Minimal implementation following KISS principles - inherits from Corpus,
delegates tree operations to TreeCorpusManager.
"""

from __future__ import annotations

from typing import ClassVar

from beanie import PydanticObjectId

from ...caching.models import VersionConfig
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

    class Metadata(Corpus.Metadata):
        """LanguageCorpus-specific metadata with discriminator.

        CRITICAL: Unique _class_id discriminator prevents Beanie from confusing
        LanguageCorpus.Metadata with Corpus.Metadata or LiteratureCorpus.Metadata.
        This allows polymorphic queries and proper document type resolution.
        """

        _class_id: ClassVar[str] = "LanguageCorpus.Metadata"

        class Settings(Corpus.Metadata.Settings):
            class_id = "_class_id"

    async def add_language_source(
        self,
        source: LanguageSource,
        connector: URLLanguageConnector | None = None,
        aggregate: bool = True,
    ) -> PydanticObjectId | None:
        """Add a language source as child corpus.

        Args:
            source: Language source configuration

        Returns:
            Child corpus ID if created

        """
        logger.info(f"Adding language source: {source.name}")

        # Fetch vocabulary using connector
        connector = connector or URLLanguageConnector()
        # Always force rebuild for corpus building to avoid stale cache
        result = await connector.fetch_source(source, config=VersionConfig(force_rebuild=True))

        if not result:
            logger.warning(f"No vocabulary fetched for source: {source.name}")
            return None

        # Extract vocabulary from result
        vocabulary = result.vocabulary
        if not vocabulary:
            logger.warning(f"No vocabulary in result for source: {source.name}")
            return None

        # Create child corpus from source vocabulary
        # Use just the source name - parent-child relationship is via IDs
        child = await Corpus.create(
            corpus_name=source.name,
            vocabulary=vocabulary,
            language=source.language,
            semantic=self.metadata.get("semantic_enabled", False),
            model_name=self.metadata.get("model_name"),
        )

        # Set corpus type
        child.corpus_type = CorpusType.LANGUAGE

        # Save child corpus
        await child.save()

        logger.info(f"Saved child corpus '{source.name}' with corpus_id={child.corpus_id}")

        if not child.corpus_id:
            logger.warning(f"Failed to save child corpus for source: {source.name}")
            return None

        # Update tree relationships via TreeCorpusManager
        manager = get_tree_corpus_manager()

        # Ensure parent has ID
        if not self.corpus_id:
            await self.save()

        logger.info(f"Parent corpus '{self.corpus_name}' using corpus_id={self.corpus_id}")

        # Update parent-child relationship
        if self.corpus_id:
            await manager.update_parent(
                self,
                child,
                config=None,  # Use default caching to avoid discriminator timing issues
            )

            # Refresh parent to get updated children list
            # Use corpus_name because update_parent may create a new version with new ID
            fresh_parent = await manager.get_corpus(
                corpus_name=self.corpus_name,
                config=None,  # Use default caching
            )
            if fresh_parent:
                self.child_uuids = fresh_parent.child_uuids
                self.corpus_id = fresh_parent.corpus_id  # Update to new ID

        # Aggregate vocabularies into parent (only if requested)
        # This allows batching aggregations when adding multiple sources
        if aggregate and self.corpus_id and child.corpus_id:
            # Note: update_parent already adds the child to parent's child_uuids
            # aggregate_vocabularies aggregates from the corpus and its children automatically
            await manager.aggregate_vocabularies(self.corpus_id)

            # Update local vocabulary to reflect aggregated result
            # Use corpus_name because aggregate_vocabularies creates a new version with new ID
            updated_corpus = await manager.get_corpus(corpus_name=self.corpus_name)
            if updated_corpus and updated_corpus.vocabulary:
                self.vocabulary = updated_corpus.vocabulary
                self.corpus_id = updated_corpus.corpus_id  # Update to new ID

        logger.info(f"Added source '{source.name}' with {len(vocabulary)} words")

        return child.corpus_id

    @classmethod
    async def from_language(
        cls,
        language: Language,
        name: str,
        vocabulary: list[str] | None = None,
    ) -> LanguageCorpus:
        """Create a LanguageCorpus from language and vocabulary.

        Args:
            language: Language for the corpus
            name: Corpus name
            vocabulary: Initial vocabulary (optional)

        Returns:
            LanguageCorpus instance

        """
        corpus = cls(
            corpus_name=name,
            corpus_type=CorpusType.LANGUAGE,
            language=language,
            vocabulary=vocabulary or [],
        )
        return corpus

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

        # Get all sources for the language (full corpus)
        sources = LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE.get(language, [])

        if not sources:
            logger.warning(f"No sources found for language: {language.value}")
            return corpus

        logger.info(f"Adding {len(sources)} sources for {language.value}")

        # Add all sources in parallel WITHOUT aggregation
        # This prevents redundant aggregations - we'll do one final aggregation at the end
        async def add_source_safe(source: LanguageSource) -> bool:
            """Add source with error handling."""
            try:
                # FIX: aggregate=False to prevent redundant aggregations
                await corpus.add_language_source(source, aggregate=False)
                return True
            except Exception as e:
                logger.error(f"Failed to add source {source.name}: {e}")
                return False

        # Process sources sequentially to avoid race conditions in tree updates
        results: list[bool] = []
        for source in sources:
            results.append(await add_source_safe(source))

        successful = sum(1 for r in results if r is True)
        logger.info(f"Successfully added {successful}/{len(sources)} sources")

        # FIX: Aggregate ONCE after all sources are added
        from ...caching.models import VersionConfig

        manager = get_tree_corpus_manager()

        if successful > 0:
            # Reload corpus to get latest ID with all children
            logger.info("Reloading corpus to get latest state before aggregation...")
            fresh_corpus = await manager.get_corpus(
                corpus_name=corpus.corpus_name, config=VersionConfig(use_cache=False)
            )

            if fresh_corpus and fresh_corpus.corpus_uuid:
                logger.info(f"Aggregating vocabularies from {successful} sources...")
                logger.info(
                    f"About to call aggregate_vocabularies with corpus_uuid={fresh_corpus.corpus_uuid}"
                )
                try:
                    # Use corpus_uuid (stable) instead of corpus_id (changes with each version)
                    await manager.aggregate_vocabularies(corpus_uuid=fresh_corpus.corpus_uuid)
                    logger.info("aggregate_vocabularies call completed")
                except Exception as e:
                    logger.error(f"Exception in aggregate_vocabularies: {e}", exc_info=True)

        # Reload corpus to get aggregated vocabulary
        # Use corpus_name instead of corpus_id because save_corpus creates a new version with new ID
        # CRITICAL FIX: Don't use use_cache=False here! The aggregation just saved vocabulary to cache,
        # so we WANT to read from cache. Using use_cache=False causes get_versioned_content() to skip
        # the cache entirely and return None, resulting in empty vocabulary.
        reloaded = await manager.get_corpus(
            corpus_name=corpus.corpus_name  # Use default config (use_cache=True)
        )

        if reloaded:
            corpus = reloaded
            logger.info(f"✅ Created language corpus with {len(corpus.vocabulary):,} unique words")
        else:
            logger.warning("Failed to reload corpus after aggregation")

        return corpus

    async def remove_source(self, source_name: str) -> None:
        """Remove a language source by name.

        Args:
            source_name: Name of source to remove

        """
        manager = get_tree_corpus_manager()

        # Find child corpus with matching name from parent's children
        # Child corpora use just the source name
        child_name = source_name
        logger.info(f"Looking for child corpus named: {child_name}")

        # Ensure we have the latest parent state with children
        # Use corpus_name for consistency (corpus_id may be stale)
        if self.corpus_name:
            fresh_parent = await manager.get_corpus(
                corpus_name=self.corpus_name,
                config=VersionConfig(use_cache=False),
            )
            if fresh_parent:
                self.child_uuids = fresh_parent.child_uuids
                self.corpus_id = fresh_parent.corpus_id  # Update to current ID
                logger.info(f"Parent has {len(self.child_uuids)} children: {self.child_uuids}")

        # Look through parent's actual children rather than global search
        child_id_to_remove = None
        # Safely iterate over children, handling potential None values
        if self.child_uuids:
            for child_uuid in self.child_uuids:
                potential_child = await manager.get_corpus(corpus_uuid=child_uuid)
                logger.info(
                    f"Checking child {child_uuid}: name={potential_child.corpus_name if potential_child else 'None'}, looking for={child_name}"
                )
                if potential_child and potential_child.corpus_name == child_name:
                    # CRITICAL: Use the UUID from parent's list
                    child_id_to_remove = potential_child.corpus_id
                    logger.info(
                        f"Found matching child: using corpus_id={child_id_to_remove} (uuid={child_uuid})"
                    )
                    break

        if not child_id_to_remove:
            logger.warning(
                f"Source '{source_name}' not found in children (child_name: {child_name})"
            )
            return

        logger.info(f"Found child corpus {child_id_to_remove} to remove")

        # Use manager to properly remove and delete child
        if self.corpus_id and child_id_to_remove:
            logger.info(
                f"Calling remove_child with parent_id={self.corpus_id}, child_id={child_id_to_remove}"
            )
            success = await manager.remove_child(
                parent_id=self.corpus_id,
                child_id=child_id_to_remove,
                delete_child=True,  # Delete the child corpus
            )

            logger.info(f"remove_child returned: {success}")

            if success:
                # Re-aggregate vocabularies after removing child
                await manager.aggregate_vocabularies(self.corpus_id)

                # Sync local state with database state - force fresh read
                # Use corpus_name because aggregate_vocabularies creates a new version
                updated_corpus = await manager.get_corpus(
                    corpus_name=self.corpus_name,
                    config=VersionConfig(use_cache=False, force_rebuild=True),
                )
                if updated_corpus:
                    logger.info(f"After removal, parent children: {updated_corpus.child_uuids}")
                    logger.info(f"After removal, parent vocabulary: {updated_corpus.vocabulary}")
                    self.child_uuids = updated_corpus.child_uuids
                    self.corpus_id = updated_corpus.corpus_id  # Update to new ID
                    self.vocabulary = updated_corpus.vocabulary

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
