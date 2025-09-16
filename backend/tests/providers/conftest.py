"""Provider testing fixtures and configuration."""

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import AsyncClient, Response
from motor.motor_asyncio import AsyncIOMotorClient

from floridify.caching.core import GlobalCacheManager
from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
    VersionConfig,
)
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Example,
    Language,
    Pronunciation,
    Word,
)
from floridify.providers.batch import BatchOperation
from floridify.providers.core import ConnectorConfig, ProviderType


@pytest_asyncio.fixture(scope="function")
async def mongodb_client() -> AsyncIterator[AsyncIOMotorClient[Any]]:
    """Create test MongoDB client."""
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient("mongodb://localhost:27017")
    yield client
    client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(mongodb_client: AsyncIOMotorClient[Any]) -> AsyncIterator[Any]:
    """Initialize test database with Beanie models."""
    db = mongodb_client["test_floridify_providers"]

    # Import Metadata models
    from floridify.corpus.core import Corpus
    from floridify.providers.dictionary.models import DictionaryProviderEntry
    from floridify.providers.language.models import LanguageEntry
    from floridify.providers.literature.models import LiteratureEntry

    # Initialize Beanie with all document models
    await init_beanie(
        database=db,
        document_models=[
            # Dictionary models
            Word,
            Definition,
            DictionaryEntry,
            Pronunciation,
            Example,
            # Versioned models - include specific Metadata subclasses
            BaseVersionedData,
            DictionaryProviderEntry.Metadata,
            LanguageEntry.Metadata,
            LiteratureEntry.Metadata,
            Corpus.Metadata,
            # Batch operations
            BatchOperation,
        ],
    )

    yield db

    # Clean up after test
    for collection_name in await db.list_collection_names():
        await db.drop_collection(collection_name)


@pytest.fixture
def cache_manager(tmp_path) -> GlobalCacheManager:
    """Create test cache manager with in-memory backend."""
    from floridify.caching.filesystem import FilesystemBackend
    
    # Create a temporary filesystem backend for testing
    backend = FilesystemBackend(cache_dir=tmp_path / "test_cache")
    manager = GlobalCacheManager(backend)
    # Each test gets a fresh cache manager
    return manager


@pytest.fixture
def version_manager(cache_manager: GlobalCacheManager) -> VersionedDataManager:
    """Create test version manager."""
    vm = VersionedDataManager()
    vm.cache = cache_manager
    return vm


@pytest.fixture
def tree_corpus_manager(version_manager: VersionedDataManager) -> TreeCorpusManager:
    """Create test tree corpus manager."""
    return TreeCorpusManager(version_manager)


@pytest.fixture
def connector_config() -> ConnectorConfig:
    """Create test connector configuration."""
    return ConnectorConfig(
        provider_type=ProviderType.DICTIONARY,
        cache_namespace=CacheNamespace.DICTIONARY,
        max_retries=3,
        base_delay=0.1,  # Short delays for testing
        max_delay=1.0,
        rate_limit_calls=10,
        rate_limit_period=1.0,
        timeout=5.0,
    )


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create mock HTTP client for API testing."""
    client = AsyncMock(spec=AsyncClient)

    # Setup default response
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.json.return_value = {"test": "data"}
    response.text = '{"test": "data"}'
    response.raise_for_status = MagicMock()

    client.get.return_value = response
    client.post.return_value = response

    return client


@pytest.fixture
def sample_word() -> Word:
    """Create sample word for testing."""
    return Word(
        text="ubiquitous",
        normalized="ubiquitous",
        lemma="ubiquitous",
        language=Language.ENGLISH,
    )


@pytest.fixture
def sample_definition(sample_word: Word) -> Definition:
    """Create sample definition for testing."""
    return Definition(
        word_id=sample_word.id,
        part_of_speech="adjective",
        text="present, appearing, or found everywhere",
        synonyms=["omnipresent", "pervasive", "universal"],
        antonyms=["rare", "scarce"],
        language_register="neutral",
        cefr_level="C1",
        frequency_band=3,
        providers=[DictionaryProvider.OXFORD],
    )


@pytest.fixture
def sample_pronunciation(sample_word: Word) -> Pronunciation:
    """Create sample pronunciation for testing."""
    return Pronunciation(
        word_id=sample_word.id,
        phonetic="yoo-bik-wi-tus",
        ipa="/juːˈbɪkwɪtəs/",
        syllables=["u", "biq", "ui", "tous"],
        stress_pattern="0201",  # Secondary, primary, none, secondary
    )


@pytest.fixture
def sample_dictionary_entry(
    sample_word: Word, sample_definition: Definition, sample_pronunciation: Pronunciation
) -> DictionaryEntry:
    """Create sample dictionary entry for testing."""
    return DictionaryEntry(
        word_id=sample_word.id,
        definition_ids=[sample_definition.id] if sample_definition.id else [],
        pronunciation_id=sample_pronunciation.id,
        provider=DictionaryProvider.OXFORD,
        language=Language.ENGLISH,
        raw_data={"original": "response"},
    )


@pytest.fixture
def mock_dictionary_response() -> dict[str, Any]:
    """Create mock dictionary API response."""
    return {
        "word": "ubiquitous",
        "phonetic": "/juːˈbɪkwɪtəs/",
        "phonetics": [
            {
                "text": "/juːˈbɪkwɪtəs/",
                "audio": "https://api.example.com/audio/ubiquitous.mp3",
            }
        ],
        "meanings": [
            {
                "partOfSpeech": "adjective",
                "definitions": [
                    {
                        "definition": "present, appearing, or found everywhere",
                        "example": "his ubiquitous influence was felt by all the family",
                        "synonyms": ["omnipresent", "ever-present", "everywhere"],
                        "antonyms": ["rare", "scarce"],
                    }
                ],
            }
        ],
        "origin": "mid 19th century: from modern Latin ubiquitas + -ous",
    }


@pytest.fixture
def mock_literature_response() -> dict[str, Any]:
    """Create mock literature API response."""
    return {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "text": "It is a truth universally acknowledged...",
        "metadata": {
            "language": "en",
            "subject": ["Fiction", "Romance"],
            "rights": "Public Domain",
        },
    }


@pytest.fixture
def version_config() -> VersionConfig:
    """Create test version configuration."""
    return VersionConfig(
        version="1.0.0",
        increment_version=True,
        force_rebuild=False,
        use_cache=True,
        ttl=3600,
        metadata={"test": True},
    )


@pytest.fixture
async def sample_corpus_metadata(test_db: Any) -> Any:
    """Create sample corpus metadata."""
    from floridify.caching.models import VersionInfo
    from floridify.corpus.core import Corpus

    corpus = Corpus.Metadata(
        resource_id="test_corpus",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        version_info=VersionInfo(
            version="1.0.0",
            data_hash="test_hash",
        ),
        content_inline={"vocabulary": ["word1", "word2", "word3"]},
    )
    await corpus.save()
    return corpus


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter for testing."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock(return_value=True)
    limiter.release = MagicMock()
    limiter.reset = MagicMock()
    return limiter


@pytest.fixture
def mock_batch_operation() -> BatchOperation:
    """Create mock batch operation for testing."""
    return BatchOperation(
        operation_id="test_batch_001",
        operation_type="dictionary_lookup",
        provider=DictionaryProvider.OXFORD,
        total_items=100,
        processed_items=0,
        failed_items=0,
        corpus_name="test_corpus",
        corpus_language=Language.ENGLISH,
    )


@pytest.fixture
async def cleanup_cache():
    """Fixture to clean up cache after tests."""
    yield
    # Clean up any filesystem cache
    import shutil
    from pathlib import Path

    cache_dir = Path("/tmp/floridify_test_cache")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
