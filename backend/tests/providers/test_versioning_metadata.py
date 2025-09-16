"""Test versioning system with inner Metadata classes."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from floridify.caching.models import (
    BaseVersionedData,
    CacheNamespace,
    CompressionType,
    ContentLocation,
    ResourceType,
    StorageType,
    VersionConfig,
    VersionInfo,
)
from floridify.corpus.core import Corpus
from floridify.models.literature import LiteratureProvider
from floridify.models.registry import get_model_class
from floridify.providers.dictionary.models import DictionaryProviderEntry


class TestInnerMetadataClasses:
    """Test inner Metadata class registration and functionality."""

    def test_dictionary_metadata_registration(self):
        """Test that Dictionary Metadata is properly registered."""
        # Dictionary should be registered via get_model_class
        metadata_class = get_model_class(ResourceType.DICTIONARY)
        assert metadata_class is not None
        assert issubclass(metadata_class, BaseVersionedData)

    def test_language_metadata_registration(self):
        """Test that Language Metadata is properly registered."""
        # Corpus (Language) should be registered via get_model_class
        metadata_class = get_model_class(ResourceType.CORPUS)
        assert metadata_class is not None
        assert issubclass(metadata_class, BaseVersionedData)
        assert metadata_class.__name__ == "Metadata"

    def test_literature_metadata_registration(self):
        """Test that Literature Metadata is properly registered."""
        # Literature should be registered via get_model_class
        metadata_class = get_model_class(ResourceType.LITERATURE)
        assert metadata_class is not None
        assert issubclass(metadata_class, BaseVersionedData)
        # Check for literature-specific fields
        assert "provider" in metadata_class.model_fields
        assert "work_id" in metadata_class.model_fields

    def test_corpus_metadata_registration(self):
        """Test that Corpus Metadata is properly registered."""
        # Check if Corpus has a Metadata class
        assert hasattr(Corpus, "Metadata")
        metadata_class = Corpus.Metadata
        assert issubclass(metadata_class, BaseVersionedData)

    def test_get_model_class_error(self):
        """Test error when getting unregistered model class."""
        fake_resource = MagicMock()
        fake_resource.value = "fake_resource"

        with pytest.raises(ValueError) as exc_info:
            get_model_class(fake_resource)

        assert "No model registered for resource type" in str(exc_info.value)


@pytest.mark.asyncio
class TestVersionedDataOperations:
    """Test BaseVersionedData operations including get_content."""

    @pytest.fixture
    def sample_metadata(self):
        """Create sample versioned metadata."""
        metadata = BaseVersionedData(
            resource_id="test_resource",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="hash123",
                is_latest=True,
            ),
            content_inline={"test": "data", "key": "value"},
        )
        return metadata

    async def test_get_content_inline(self, sample_metadata):
        """Test get_content with inline storage."""
        content = await sample_metadata.get_content()
        assert content == {"test": "data", "key": "value"}

    async def test_get_content_external(self):
        """Test get_content with external storage."""
        metadata = BaseVersionedData(
            resource_id="test_resource",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="hash456",
                is_latest=True,
            ),
            content_location=ContentLocation(
                storage_type=StorageType.CACHE,
                cache_namespace=CacheNamespace.CORPUS,
                cache_key="corpus_key_123",
                size_bytes=1024,
                checksum="checksum789",
            ),
        )

        external_content = {"vocabulary": ["word1", "word2", "word3"]}

        with patch("floridify.caching.models.get_global_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get = AsyncMock(return_value=external_content)
            mock_get_cache.return_value = mock_cache

            content = await metadata.get_content()

            assert content == external_content
            mock_cache.get.assert_called_once_with(
                namespace=CacheNamespace.CORPUS, key="corpus_key_123"
            )

    async def test_get_content_no_data(self):
        """Test get_content when no content is available."""
        metadata = BaseVersionedData(
            resource_id="empty_resource",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="hash_empty",
                is_latest=True,
            ),
        )

        content = await metadata.get_content()
        assert content is None


class TestVersionConfig:
    """Test VersionConfig settings."""

    def test_version_config_defaults(self):
        """Test default values for VersionConfig."""
        config = VersionConfig()

        assert config.force_rebuild is False
        assert config.use_cache is True
        assert config.increment_version is True
        assert config.version is None
        assert config.ttl is None
        assert config.compression is None
        assert config.metadata == {}

    def test_version_config_with_ttl(self):
        """Test VersionConfig with TTL settings."""
        config = VersionConfig(
            force_rebuild=True,
            use_cache=False,
            ttl=timedelta(hours=24),
            compression=CompressionType.ZSTD,
        )

        assert config.force_rebuild is True
        assert config.use_cache is False
        assert config.ttl == timedelta(hours=24)
        assert config.compression == CompressionType.ZSTD

    def test_version_config_with_metadata(self):
        """Test VersionConfig with custom metadata."""
        custom_metadata = {
            "source": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "tags": ["test", "sample"],
        }

        config = VersionConfig(
            version="2.0.0",
            increment_version=False,
            metadata=custom_metadata,
        )

        assert config.version == "2.0.0"
        assert config.increment_version is False
        assert config.metadata == custom_metadata


class TestVersionChainManagement:
    """Test version chain and supersession management."""

    def test_version_info_creation(self):
        """Test VersionInfo creation and defaults."""
        version_info = VersionInfo(
            data_hash="hash123",
        )

        assert version_info.version == "1.0.0"
        assert version_info.is_latest is True
        assert version_info.superseded_by is None
        assert version_info.supersedes is None
        assert version_info.dependencies == []
        assert isinstance(version_info.created_at, datetime)

    def test_version_chain_linking(self):
        """Test version chain with supersession links."""
        old_id = PydanticObjectId()
        new_id = PydanticObjectId()

        old_version = VersionInfo(
            version="1.0.0",
            data_hash="old_hash",
            is_latest=False,
            superseded_by=new_id,
        )

        new_version = VersionInfo(
            version="2.0.0",
            data_hash="new_hash",
            is_latest=True,
            supersedes=old_id,
        )

        assert old_version.superseded_by == new_id
        assert new_version.supersedes == old_id
        assert old_version.is_latest is False
        assert new_version.is_latest is True

    def test_version_dependencies(self):
        """Test version with dependencies."""
        dep1 = PydanticObjectId()
        dep2 = PydanticObjectId()
        dep3 = PydanticObjectId()

        version_info = VersionInfo(
            version="3.0.0",
            data_hash="composite_hash",
            dependencies=[dep1, dep2, dep3],
        )

        assert len(version_info.dependencies) == 3
        assert dep1 in version_info.dependencies
        assert dep2 in version_info.dependencies
        assert dep3 in version_info.dependencies


@pytest.mark.asyncio
class TestProviderMetadataIntegration:
    """Test metadata integration with actual provider models."""

    async def test_dictionary_entry_with_metadata(self):
        """Test DictionaryProviderEntry with its Metadata class."""
        # Verify the Metadata class exists and is properly configured
        assert hasattr(DictionaryProviderEntry, "Metadata")
        metadata_class = DictionaryProviderEntry.Metadata

        # Create a metadata instance
        metadata = metadata_class(
            resource_id="dictionary_entry_123",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="dict_hash",
            ),
            content_inline={"word": "test", "definitions": []},
        )

        # Test get_content
        content = await metadata.get_content()
        assert content == {"word": "test", "definitions": []}

    async def test_language_entry_with_metadata(self):
        """Test LanguageEntry with its Metadata class."""
        # Get the registered metadata class
        metadata_class = get_model_class(ResourceType.CORPUS)

        # Create a metadata instance
        metadata = metadata_class(
            resource_id="language_corpus_456",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="lang_hash",
            ),
            content_inline={
                "vocabulary": ["mot", "parole", "langue"],
                "language": "French",
            },
        )

        # Test get_content
        content = await metadata.get_content()
        assert "vocabulary" in content
        assert len(content["vocabulary"]) == 3

    async def test_literature_entry_with_metadata(self):
        """Test LiteratureEntry with its Metadata class."""
        # Get the registered metadata class
        metadata_class = get_model_class(ResourceType.LITERATURE)

        # Create a metadata instance with literature-specific fields
        metadata = metadata_class(
            resource_id="shakespeare_hamlet",
            resource_type=ResourceType.LITERATURE,
            namespace=CacheNamespace.LITERATURE,
            provider=LiteratureProvider.GUTENBERG,
            work_id="hamlet_1603",
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="hamlet_hash",
            ),
            content_inline={
                "title": "Hamlet",
                "author": "Shakespeare",
                "text": "To be or not to be...",
            },
        )

        # Test literature-specific fields
        assert metadata.provider == LiteratureProvider.GUTENBERG
        assert metadata.work_id == "hamlet_1603"

        # Test get_content
        content = await metadata.get_content()
        assert content["title"] == "Hamlet"

    async def test_corpus_with_metadata(self):
        """Test Corpus with its Metadata class."""
        metadata_class = Corpus.Metadata

        # Create a corpus metadata instance
        metadata = metadata_class(
            resource_id="master_corpus",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="2.0.0",
                data_hash="corpus_hash",
            ),
            content_inline={
                "vocabulary": ["apple", "banana", "cherry"],
                "corpus_type": "LEXICON",
                "language": "English",
            },
        )

        # Test get_content
        content = await metadata.get_content()
        assert "vocabulary" in content
        assert len(content["vocabulary"]) == 3
        assert content["corpus_type"] == "LEXICON"


class TestContentLocationStrategies:
    """Test different content storage strategies."""

    def test_content_location_filesystem(self):
        """Test ContentLocation for filesystem storage."""
        location = ContentLocation(
            storage_type=StorageType.CACHE,
            cache_namespace=CacheNamespace.CORPUS,
            cache_key="corpus_12345",
            path="/cache/corpus/corpus_12345.json",
            compression=CompressionType.ZSTD,
            size_bytes=10240,
            size_compressed=2048,
            checksum="sha256:abcdef123456",
        )

        assert location.storage_type == StorageType.CACHE
        assert location.cache_namespace == CacheNamespace.CORPUS
        assert location.cache_key == "corpus_12345"
        assert location.path == "/cache/corpus/corpus_12345.json"
        assert location.compression == CompressionType.ZSTD
        assert location.size_compressed == 2048

    def test_content_location_memory(self):
        """Test ContentLocation for memory storage."""
        location = ContentLocation(
            storage_type=StorageType.MEMORY,
            cache_namespace=CacheNamespace.DICTIONARY,
            cache_key="dict_mem_789",
            size_bytes=512,
            checksum="md5:xyz789",
        )

        assert location.storage_type == StorageType.MEMORY
        assert location.path is None
        assert location.compression is None
        assert location.size_compressed is None

    def test_content_location_database(self):
        """Test ContentLocation for database storage."""
        location = ContentLocation(
            storage_type=StorageType.DATABASE,
            size_bytes=1024000,
            checksum="sha1:database123",
        )

        assert location.storage_type == StorageType.DATABASE
        assert location.cache_namespace is None
        assert location.cache_key is None
