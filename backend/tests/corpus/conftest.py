"""Test configuration for corpus tests with real MongoDB."""
import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from floridify.caching.manager import TreeCorpusManager
from floridify.caching.models import CacheNamespace
from floridify.models.dictionary import CorpusType, Language
from floridify.models.versioned import (
    CorpusMetadata,
    DictionaryEntryMetadata,
    LiteratureEntryMetadata,
    ResourceType,
    SearchIndexMetadata,
    SemanticIndexMetadata,
    TrieIndexMetadata,
    VersionInfo,
)


@pytest_asyncio.fixture(scope="session")
async def motor_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create a MongoDB client for testing."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    yield client
    client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(motor_client: AsyncIOMotorClient):
    """Initialize test database and clean up after each test."""
    # Use a test database
    db = motor_client["test_floridify_corpus"]
    
    # Initialize Beanie with all document models
    await init_beanie(
        database=db,
        document_models=[
            CorpusMetadata,
            DictionaryEntryMetadata,
            LiteratureEntryMetadata,
            SearchIndexMetadata,
            SemanticIndexMetadata,
            TrieIndexMetadata,
        ],
    )
    
    yield db
    
    # Clean up - drop all collections after test
    for collection_name in await db.list_collection_names():
        await db.drop_collection(collection_name)


@pytest_asyncio.fixture
async def tree_manager(test_db) -> TreeCorpusManager:
    """Create a TreeCorpusManager instance."""
    return TreeCorpusManager()


@pytest_asyncio.fixture
async def sample_vocabularies() -> dict[str, list[str]]:
    """Various vocabulary samples for testing."""
    return {
        "empty": [],
        "small": ["apple", "banana", "cherry"],
        "unicode": ["café", "naïve", "résumé", "😀", "北京"],
        "duplicates": ["apple", "Apple", "APPLE", "apple"],
        "diacritics": ["cafe", "café", "naive", "naïve"],
        "large": [f"word_{i}" for i in range(15000)],
    }


@pytest_asyncio.fixture
async def corpus_tree(test_db, tree_manager: TreeCorpusManager, sample_vocabularies: dict[str, list[str]]):
    """Create a 3-level test tree using real CorpusMetadata."""
    # Create language corpus (master)
    language_corpus = CorpusMetadata(
        resource_id="English",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        version_info=VersionInfo(
            version="1.0.0",
            data_hash="test_hash",
            is_latest=True,
        ),
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        is_master=True,
        child_corpus_ids=[],
        content_inline={"vocabulary": sample_vocabularies["small"]},
        vocabulary_size=3,
        vocabulary_hash="test_hash",
    )
    await language_corpus.save()
    
    # Create work corpora (children)
    work1 = CorpusMetadata(
        resource_id="Shakespeare_Works",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        version_info=VersionInfo(
            version="1.0.0",
            data_hash="test_hash_1",
            is_latest=True,
        ),
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        parent_corpus_id=language_corpus.id,
        child_corpus_ids=[],
        content_inline={"vocabulary": ["thou", "thee", "thy"]},
        vocabulary_size=3,
        vocabulary_hash="test_hash_1",
    )
    await work1.save()
    
    work2 = CorpusMetadata(
        resource_id="Modern_Works",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        version_info=VersionInfo(
            version="1.0.0",
            data_hash="test_hash_2",
            is_latest=True,
        ),
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        parent_corpus_id=language_corpus.id,
        child_corpus_ids=[],
        content_inline={"vocabulary": ["internet", "smartphone", "app"]},
        vocabulary_size=3,
        vocabulary_hash="test_hash_2",
    )
    await work2.save()
    
    # Create chapter corpus (grandchild)
    chapter1 = CorpusMetadata(
        resource_id="Hamlet",
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        version_info=VersionInfo(
            version="1.0.0",
            data_hash="test_hash_3",
            is_latest=True,
        ),
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        parent_corpus_id=work1.id,
        content_inline={"vocabulary": ["to", "be", "or", "not"]},
        vocabulary_size=4,
        vocabulary_hash="test_hash_3",
    )
    await chapter1.save()
    
    # Update parent references
    language_corpus.child_corpus_ids = [work1.id, work2.id]
    await language_corpus.save()
    
    work1.child_corpus_ids = [chapter1.id]
    await work1.save()
    
    return {
        "master": language_corpus,
        "work1": work1,
        "work2": work2,
        "chapter1": chapter1,
    }


@pytest_asyncio.fixture
async def concurrent_executor():
    """Helper for concurrent operation testing."""
    async def execute_concurrent(tasks, delay=0.01):
        """Execute tasks concurrently with optional delay between starts."""
        async def delayed_task(task, d):
            await asyncio.sleep(d)
            return await task
        
        return await asyncio.gather(
            *[delayed_task(task, i * delay) for i, task in enumerate(tasks)],
            return_exceptions=True
        )
    return execute_concurrent


@pytest.fixture
def assert_helpers():
    """Common assertion helpers."""
    class Helpers:
        @staticmethod
        def assert_parent_child_linked(parent: CorpusMetadata, child: CorpusMetadata):
            """Verify parent-child relationship is properly linked."""
            assert child.id in parent.child_corpus_ids
            assert parent.id == child.parent_corpus_id
        
        @staticmethod
        def assert_vocabulary_contains(corpus: CorpusMetadata, expected_words: list[str]):
            """Verify corpus contains expected vocabulary."""
            vocab = corpus.content_inline.get("vocabulary", []) if corpus.content_inline else []
            assert all(word in vocab for word in expected_words)
        
        @staticmethod
        def assert_tree_consistency(root: CorpusMetadata, all_nodes: dict[str, CorpusMetadata]):
            """Verify entire tree structure is consistent."""
            visited = set()
            
            def check_node(node: CorpusMetadata):
                if node.id in visited:
                    raise ValueError(f"Circular reference detected at {node.resource_id}")
                visited.add(node.id)
                
                for child_id in node.child_corpus_ids:
                    child = next((n for n in all_nodes.values() if n.id == child_id), None)
                    if child:
                        assert child.parent_corpus_id == node.id
                        check_node(child)
            
            check_node(root)
            return True
    
    return Helpers()