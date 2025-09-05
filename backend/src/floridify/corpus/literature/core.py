"""Literature corpus implementation with provider integration.

Minimal implementation following KISS principles - inherits from Corpus,
delegates tree operations to TreeCorpusManager.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from beanie import PydanticObjectId

from ...models.base import Language
from ...models.literature import AuthorInfo, Genre, Period
from ...providers.literature.api.gutenberg import GutenbergConnector
from ...providers.literature.core import LiteratureConnector
from ...providers.literature.models import LiteratureSource
from ...utils.logging import get_logger
from ..core import Corpus
from ..manager import get_tree_corpus_manager
from ..models import CorpusType

logger = get_logger(__name__)


class LiteratureCorpus(Corpus):
    """Literature corpus with work management.
    
    Inherits all fields and functionality from Corpus.
    Adds literature-specific source management via TreeCorpusManager.
    """
    
    async def add_literature_source(
        self,
        source: LiteratureSource,
        connector: LiteratureConnector | None = None,
    ) -> PydanticObjectId | None:
        """Add a literature work as child corpus.
        
        Args:
            source: Literature source configuration
            connector: Optional connector to use (defaults to Gutenberg)
            
        Returns:
            Child corpus ID if created
        """
        logger.info(f"Adding literature source: {source.name}")
        
        # Use provided connector or default to Gutenberg
        if not connector:
            connector = GutenbergConnector()
        
        # Fetch work content
        entry = await connector.fetch(source.url or source.name)
        
        if not entry:
            logger.warning(f"Failed to fetch work: {source.name}")
            return None
        
        # Extract vocabulary from text
        vocabulary = []
        if hasattr(entry, "text") and entry.text:
            # Simple word extraction
            words = re.findall(r"\b[a-zA-Z]+\b", entry.text)
            vocabulary = list(set(word.lower() for word in words))
        elif hasattr(entry, "extracted_vocabulary"):
            vocabulary = entry.extracted_vocabulary
        
        if not vocabulary:
            logger.warning(f"No vocabulary extracted for work: {source.name}")
            return None
        
        # Create child corpus from work vocabulary
        child = await Corpus.create(
            corpus_name=f"{self.corpus_name}_{source.name}",
            vocabulary=vocabulary,
            language=source.language,
            semantic=self.metadata.get("semantic_enabled", False),
            model_name=self.metadata.get("model_name"),
        )
        
        # Set corpus type
        child.corpus_type = CorpusType.LITERATURE
        
        # Add metadata about the work
        child.metadata.update({
            "title": source.name,
            "author": source.author.name if source.author else "Unknown",
            "genre": source.genre.value if source.genre else None,
            "period": source.period.value if source.period else None,
        })
        
        # Save child corpus
        await child.save()
        
        if not child.corpus_id:
            logger.warning(f"Failed to save child corpus for work: {source.name}")
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
            f"Added work '{source.name}' with {len(vocabulary)} unique words"
        )
        
        return child.corpus_id
    
    async def add_author_works(
        self,
        author: AuthorInfo,
        work_ids: list[str],
        connector: LiteratureConnector | None = None,
    ) -> list[PydanticObjectId]:
        """Add multiple works from an author.
        
        Args:
            author: Author information
            work_ids: List of work IDs (e.g., Gutenberg IDs)
            connector: Optional connector to use
            
        Returns:
            List of created child corpus IDs
        """
        logger.info(f"Adding {len(work_ids)} works by {author.name}")
        
        if not connector:
            connector = GutenbergConnector()
        
        child_ids = []
        
        for work_id in work_ids:
            source = LiteratureSource(
                name=f"{author.name}_{work_id}",
                url=work_id,  # Gutenberg ID or URL
                author=author,
                genre=author.primary_genre,
                period=author.period,
                language=author.language or Language.ENGLISH,
            )
            
            try:
                child_id = await self.add_literature_source(source, connector)
                if child_id:
                    child_ids.append(child_id)
            except Exception as e:
                logger.error(f"Failed to add work {work_id}: {e}")
                continue
        
        logger.info(f"Successfully added {len(child_ids)} works")
        return child_ids
    
    async def add_file_work(
        self,
        file_path: Path | str,
        metadata: dict[str, Any] | None = None,
    ) -> PydanticObjectId | None:
        """Add a work from local file system.
        
        Args:
            file_path: Path to the literature file
            metadata: Optional metadata about the work
            
        Returns:
            Child corpus ID if created
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # Read file content
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
        
        # Extract vocabulary
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        vocabulary = list(set(word.lower() for word in words))
        
        # Create source from metadata
        meta = metadata or {}
        source = LiteratureSource(
            name=meta.get("title", file_path.stem),
            author=AuthorInfo(
                name=meta.get("author", "Unknown"),
                period=Period(meta.get("period", Period.CONTEMPORARY)),
                primary_genre=Genre(meta.get("genre", Genre.NOVEL)),
            )
            if "author" in meta
            else None,
            genre=Genre(meta.get("genre", Genre.NOVEL)) if "genre" in meta else None,
            period=Period(meta.get("period", Period.CONTEMPORARY))
            if "period" in meta
            else None,
            language=Language(meta.get("language", Language.ENGLISH))
            if "language" in meta
            else Language.ENGLISH,
        )
        
        # Create child corpus directly (no connector needed)
        child = await Corpus.create(
            corpus_name=f"{self.corpus_name}_{source.name}",
            vocabulary=vocabulary,
            language=source.language,
            semantic=self.metadata.get("semantic_enabled", False),
            model_name=self.metadata.get("model_name"),
        )
        
        child.corpus_type = CorpusType.LITERATURE
        child.metadata.update({
            "file_path": str(file_path),
            "title": source.name,
            "author": source.author.name if source.author else "Unknown",
        })
        
        await child.save()
        
        if child.corpus_id:
            # Update tree relationships
            manager = get_tree_corpus_manager()
            
            if not self.corpus_id:
                await self.save()
            
            if self.corpus_id:
                await manager.update_parent(self.corpus_id, child.corpus_id)
                self.child_corpus_ids.append(child.corpus_id)
                # Note: aggregate_vocabularies aggregates from the corpus and its children automatically
                await manager.aggregate_vocabularies(self.corpus_id)
            
            logger.info(f"Added file work '{source.name}' with {len(vocabulary)} words")
        
        return child.corpus_id
    
    async def remove_work(self, work_name: str) -> None:
        """Remove a literature work by name.
        
        Args:
            work_name: Name of work to remove
        """
        manager = get_tree_corpus_manager()
        
        # Find child corpus with matching name
        child_name = f"{self.corpus_name}_{work_name}"
        
        # Get child corpus using keyword argument
        child_meta = await manager.get_corpus(corpus_name=child_name)
        if not child_meta or not child_meta.id:
            logger.warning(f"Work '{work_name}' not found")
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
        
        logger.info(f"Removed work: {work_name}")
    
    async def update_work(
        self,
        work_name: str,
        source: LiteratureSource,
        connector: LiteratureConnector | None = None,
    ) -> None:
        """Update a literature work.
        
        Args:
            work_name: Current work name
            source: New source configuration
            connector: Optional connector to use
        """
        # Simple approach: remove old, add new
        await self.remove_work(work_name)
        await self.add_literature_source(source, connector)