"""Language corpus implementation with provider pattern support."""

from __future__ import annotations

from pydantic import Field

from ...caching.models import VersionConfig
from ...models.base import Language
from ...providers.language import (
    LanguageConnector,
    LanguageEntry,
    LanguageEntryMetadata,
    LanguageProvider,
)
from ..core import MultisourceCorpus
from ..models import CorpusType
from .models import LanguageCorpusMetadata


class LanguageCorpus(MultisourceCorpus):
    """Language-specific corpus with provider pattern integration."""
    
    # Language-specific fields
    corpus_type: CorpusType = CorpusType.LANGUAGE
    providers: list[LanguageProvider] = Field(default_factory=list)
    language_entries: dict[str, LanguageEntry] = Field(default_factory=dict)
    provider_vocabularies: dict[LanguageProvider, list[str]] = Field(default_factory=dict)
    
    async def add_provider(
        self,
        provider: LanguageProvider,
        connector: LanguageConnector,
        vocabulary: list[str] | None = None,
    ) -> None:
        """Add a language provider as a source.
        
        Args:
            provider: Provider enum value
            connector: Connector instance for fetching
            vocabulary: Pre-fetched vocabulary (optional)
        """
        if provider not in self.providers:
            self.providers.append(provider)
            
        # Fetch vocabulary if not provided
        if vocabulary is None:
            result = await connector.fetch(provider.value)
            vocabulary = result if result else []
            
        # Store provider vocabulary
        self.provider_vocabularies[provider] = vocabulary
        
        # Add as source to parent class
        await self.add_source(
            source_name=provider.value,
            vocabulary=vocabulary,
            metadata={
                "provider": provider.value,
                "source_url": connector.source_url,
                "parser": connector.parser_name,
                "scraper": connector.scraper_name,
            },
        )
        
        
            
    async def remove_provider(self, provider: LanguageProvider) -> None:
        """Remove a language provider.
        
        Args:
            provider: Provider to remove
        """
        if provider in self.providers:
            self.providers.remove(provider)
            
        # Remove from provider vocabularies
        if provider in self.provider_vocabularies:
            del self.provider_vocabularies[provider]
            
        # Remove language entries from this provider
        entries_to_remove = [
            entry_id
            for entry_id, entry in self.language_entries.items()
            if entry.provider == provider
        ]
        for entry_id in entries_to_remove:
            del self.language_entries[entry_id]
            
        # Remove source from parent class
        await self.remove_source(provider.value)
        
    async def get_provider_vocabulary(
        self,
        provider: LanguageProvider,
    ) -> list[str]:
        """Get vocabulary from a specific provider.
        
        Args:
            provider: Provider enum value
            
        Returns:
            List of words from the provider
        """
        return self.provider_vocabularies.get(provider, [])
        
    async def get_entries_by_provider(
        self,
        provider: LanguageProvider,
    ) -> list[LanguageEntry]:
        """Get all entries from a specific provider.
        
        Args:
            provider: Provider to filter by
            
        Returns:
            List of language entries from the provider
        """
        return [
            entry
            for entry in self.language_entries.values()
            if entry.provider == provider
        ]
        
    async def save(self, config: VersionConfig | None = None) -> None:
        """Save language corpus with metadata."""
        # Create metadata document
        metadata = LanguageCorpusMetadata(
            corpus_name=self.corpus_name,
            corpus_type=self.corpus_type,
            language=self.language,
            providers=self.providers,
            parent_id=self.parent_corpus_id,
            child_ids=self.child_corpus_ids,
            is_master=self.is_master,
            total_entries=len(self.language_entries),
            unique_entries=len(self.vocabulary),
            provider_counts={
                provider.value: len(self.provider_vocabularies.get(provider, []))
                for provider in self.providers
            },
        )
        
        # Set content
        content = self.model_dump()
        await metadata.set_content(content)
        
        # Save metadata
        await metadata.save_version(config)
        
        # Update corpus_id
        if metadata.id and not self.corpus_id:
            self.corpus_id = metadata.id
            
    @classmethod
    async def create_from_providers(
        cls,
        corpus_name: str,
        language: Language,
        providers: dict[LanguageProvider, LanguageConnector],
        semantic: bool = False,
        model_name: str | None = None,
    ) -> LanguageCorpus:
        """Create language corpus from multiple providers.
        
        Args:
            corpus_name: Name for the corpus
            language: Language of the corpus
            providers: Dict mapping providers to connectors
            semantic: Enable semantic search
            model_name: Embedding model name
            
        Returns:
            Configured LanguageCorpus instance
        """
        corpus = cls(
            corpus_name=corpus_name,
            corpus_type=CorpusType.LANGUAGE,
            language=language,
            is_master=True,
        )
        
        corpus.metadata = {
            "semantic_enabled": semantic,
            "model_name": model_name,
        }
        
        # Add all providers
        for provider, connector in providers.items():
            await corpus.add_provider(provider, connector)
            
        return corpus