"""Main test configuration with MongoDB setup and async fixture handling."""

from __future__ import annotations

# Set OpenMP threading limits BEFORE any library imports to prevent conflicts
# These settings work universally (local development and Docker)
import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import shutil
import subprocess
import time
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

# Model registry is now handled via simple switch statement
# No initialization needed

# Test configuration
TEST_DATABASE_NAME = "test_floridify"
DEFAULT_MONGODB_PORT = int(os.getenv("TEST_MONGODB_PORT", "27017"))


@pytest.fixture(scope="session")
def mongodb_server(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Launch a real mongod instance for the duration of the test session."""
    mongod_bin = shutil.which(os.getenv("MONGOD_BIN", "mongod"))
    if not mongod_bin:
        pytest.skip("mongod binary not available on PATH")

    data_dir = tmp_path_factory.mktemp("mongo-data")
    log_path = Path(data_dir) / "mongod.log"
    port = DEFAULT_MONGODB_PORT

    args = [
        mongod_bin,
        "--dbpath",
        str(data_dir),
        "--port",
        str(port),
        "--bind_ip",
        "127.0.0.1",
        "--nounixsocket",
        "--quiet",
    ]

    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT)

        try:
            client = MongoClient(f"mongodb://127.0.0.1:{port}", serverSelectionTimeoutMS=500)
            deadline = time.time() + 20
            while True:
                try:
                    client.admin.command("ping")
                    break
                except Exception as exc:  # pragma: no cover - startup delay only
                    if time.time() > deadline:
                        process.terminate()
                        process.wait(timeout=10)
                        pytest.skip(f"MongoDB server failed to start: {exc}")
                    time.sleep(0.2)
            client.close()
            yield f"mongodb://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
                process.kill()
                process.wait(timeout=10)


def get_document_models():
    """Import all Beanie document models."""
    from floridify.caching.models import BaseVersionedData
    from floridify.corpus.core import Corpus
    from floridify.models.base import AudioMedia, ImageMedia
    from floridify.models.dictionary import (
        Definition,
        DictionaryEntry,
        Example,
        Fact,
        Pronunciation,
        Word,
    )
    from floridify.models.relationships import WordRelationship
    from floridify.providers.batch import BatchOperation
    from floridify.providers.dictionary.models import DictionaryProviderEntry
    from floridify.providers.language.models import LanguageEntry
    from floridify.providers.literature.models import LiteratureEntry
    from floridify.search.models import SearchIndex, TrieIndex
    from floridify.search.semantic.models import SemanticIndex
    from floridify.wordlist.models import WordList

    return [
        # Core dictionary models
        Word,
        Definition,
        DictionaryEntry,
        Pronunciation,
        Example,
        Fact,
        # Media models
        AudioMedia,
        ImageMedia,
        # Relationship models
        WordRelationship,
        # WordList models
        WordList,
        # Versioning models
        BaseVersionedData,
        # Batch models
        BatchOperation,
        # Metadata models
        Corpus.Metadata,
        DictionaryProviderEntry.Metadata,
        LanguageEntry.Metadata,
        LiteratureEntry.Metadata,
        SearchIndex.Metadata,
        SemanticIndex.Metadata,
        TrieIndex.Metadata,
    ]


@pytest_asyncio.fixture(scope="function")
async def mongodb_client(mongodb_server: str) -> AsyncGenerator[AsyncIOMotorClient]:
    """Create MongoDB client for test."""
    client = AsyncIOMotorClient(mongodb_server, serverSelectionTimeoutMS=500)
    try:
        # Test connection
        await client.admin.command("ping")
        yield client
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        client.close()


@pytest_asyncio.fixture(scope="session")
async def mongodb_client_session(mongodb_server: str) -> AsyncGenerator[AsyncIOMotorClient]:
    """Create session-scoped MongoDB client for expensive setup (like semantic indices)."""
    client = AsyncIOMotorClient(mongodb_server, serverSelectionTimeoutMS=500)
    try:
        # Test connection
        await client.admin.command("ping")
        yield client
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(mongodb_client: AsyncIOMotorClient):
    """Create isolated test database with Beanie initialization."""
    # Use unique database name for each test
    db_name = f"{TEST_DATABASE_NAME}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    db = mongodb_client[db_name]

    # Initialize Beanie with document models
    await init_beanie(
        database=db,
        document_models=get_document_models(),
    )

    yield db

    # Clean up - drop database after test
    await mongodb_client.drop_database(db_name)


@pytest_asyncio.fixture(scope="session")
async def test_db_session(mongodb_client_session: AsyncIOMotorClient):
    """Create session-scoped test database for expensive setup (like semantic indices).

    This database persists for the entire test session to enable:
    - Pre-warming semantic indices once
    - Reusing expensive corpus builds
    - Sharing test data across tests
    """
    # Use unique database name for this session
    db_name = f"{TEST_DATABASE_NAME}_session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    db = mongodb_client_session[db_name]

    # Initialize Beanie with document models
    await init_beanie(
        database=db,
        document_models=get_document_models(),
    )

    yield db

    # Clean up - drop database after entire session
    await mongodb_client_session.drop_database(db_name)


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio markers."""
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio")


# Helper functions for API tests
def assert_response_structure(response: dict, required_fields: list[str]) -> None:
    """Assert that response contains all required fields."""
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"


def assert_valid_object_id(value: str) -> None:
    """Assert that value is a valid MongoDB ObjectId string."""
    assert isinstance(value, str), "ObjectId must be a string"
    assert len(value) == 24, "ObjectId must be 24 characters"
    assert all(c in "0123456789abcdef" for c in value.lower()), "ObjectId must be hexadecimal"


# Additional fixtures for API tests
@pytest_asyncio.fixture
async def async_client(test_db):
    """Create async FastAPI test client.

    Creates a test-specific app without BaseHTTPMiddleware-based middleware
    to avoid event loop conflicts with Motor/Beanie. Starlette's
    BaseHTTPMiddleware runs handlers in a TaskGroup that causes
    'Future attached to a different loop' errors with async MongoDB drivers.
    """
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from floridify.api.main import API_V1_PREFIX
    from floridify.api.routers import (
        ai,
        cache,
        config,
        corpus,
        database,
        health,
        lookup,
        providers,
        search,
        suggestions,
        word_versions,
        wordlist_reviews,
        wordlist_search,
        wordlist_words,
        wordlists,
    )

    # Create a minimal test app without BaseHTTPMiddleware
    test_app = FastAPI(title="Test App")

    # Register the same routers as the main app
    test_app.include_router(lookup, prefix=API_V1_PREFIX, tags=["lookup"])
    test_app.include_router(search, prefix=API_V1_PREFIX, tags=["search"])
    test_app.include_router(wordlists, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])
    test_app.include_router(wordlist_words, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])
    test_app.include_router(
        wordlist_reviews, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"]
    )
    test_app.include_router(
        wordlist_search, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"]
    )
    test_app.include_router(database, prefix=API_V1_PREFIX, tags=["database"])
    test_app.include_router(providers, prefix=API_V1_PREFIX, tags=["providers"])
    test_app.include_router(corpus, prefix=API_V1_PREFIX, tags=["corpus"])
    test_app.include_router(cache, prefix=API_V1_PREFIX, tags=["cache"])
    test_app.include_router(config, prefix=API_V1_PREFIX, tags=["config"])
    test_app.include_router(ai, prefix=API_V1_PREFIX, tags=["ai"])
    test_app.include_router(suggestions, prefix=API_V1_PREFIX, tags=["suggestions"])
    test_app.include_router(word_versions, prefix=f"{API_V1_PREFIX}/words", tags=["word-versions"])
    test_app.include_router(health, prefix="", tags=["health"])

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def performance_thresholds():
    """Define performance thresholds for various operations."""
    return {
        "lookup_single": 2.0,  # seconds
        "lookup_batch": 10.0,
        "search_fuzzy": 1.0,
        "search_semantic": 3.0,
        "ai_synthesis": 5.0,
        "corpus_build": 15.0,
        "provider_fetch": 3.0,
    }


# Test data factories for API tests
@pytest_asyncio.fixture
async def word_factory(test_db):
    """Factory for creating Word instances."""
    from floridify.models.dictionary import Language, Word

    created_words = []

    async def _create_word(text: str, language: str = "en", **kwargs):
        """Create and persist a Word instance."""
        lang_enum = Language.ENGLISH if language == "en" else Language(language)
        word = Word(
            text=text,
            language=lang_enum,
            **kwargs,
        )
        await word.save()
        created_words.append(word)
        return word

    yield _create_word

    # Cleanup
    for word in created_words:
        try:
            await word.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def definition_factory(test_db):
    """Factory for creating Definition instances."""
    from floridify.models.dictionary import Definition, DictionaryProvider

    created_definitions = []

    async def _create_definition(
        word_instance,
        text: str = "A test definition",
        part_of_speech: str = "noun",
        **kwargs,
    ):
        """Create and persist a Definition instance."""
        definition = Definition(
            word_id=word_instance.id,
            text=text,
            part_of_speech=part_of_speech,
            providers=[DictionaryProvider.FREE_DICTIONARY],
            **kwargs,
        )
        await definition.save()
        created_definitions.append(definition)
        return definition

    yield _create_definition

    # Cleanup
    for definition in created_definitions:
        try:
            await definition.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def wordlist_factory(test_db):
    """Factory for creating WordList instances."""
    from floridify.models.dictionary import Language, Word
    from floridify.wordlist.models import WordList, WordListItem

    created_wordlists = []
    created_words = []

    async def _create_wordlist(
        name: str = "Test Wordlist",
        description: str = "Test description",
        words: list[str] | None = None,
        is_public: bool = False,
        tags: list[str] | None = None,
        **kwargs,
    ):
        """Create and persist a WordList instance with words."""
        # Create Word documents for each word text if provided
        word_items = []
        if words:
            for word_text in words:
                # Create Word document
                word_doc = Word(
                    text=word_text,
                    language=Language.ENGLISH,
                )
                await word_doc.save()
                created_words.append(word_doc)

                # Create WordListItem
                word_item = WordListItem(word_id=word_doc.id)
                word_items.append(word_item)

        # Create WordList
        wordlist = WordList(
            name=name,
            description=description,
            hash_id=f"test_{name.lower().replace(' ', '_')}_{len(created_wordlists)}",
            words=word_items,
            total_words=len(word_items),
            unique_words=len(word_items),
            is_public=is_public,
            tags=tags or [],
            **kwargs,
        )
        await wordlist.save()
        created_wordlists.append(wordlist)
        return wordlist

    yield _create_wordlist

    # Cleanup
    for wordlist in created_wordlists:
        try:
            await wordlist.delete()
        except Exception:
            pass

    for word in created_words:
        try:
            await word.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def mock_dictionary_providers():
    """Mock dictionary provider setup for API tests."""
    from unittest.mock import AsyncMock, patch

    # Create mock providers
    mock_free_dict = AsyncMock()
    mock_wiktionary = AsyncMock()
    mock_oxford = AsyncMock()

    # Setup default return values
    mock_free_dict.fetch.return_value = {
        "word": "test",
        "phonetic": "/test/",
        "meanings": [
            {
                "partOfSpeech": "noun",
                "definitions": [
                    {
                        "definition": "A procedure for critical evaluation",
                        "example": "The test was difficult",
                    }
                ],
            }
        ],
    }

    mock_wiktionary.fetch.return_value = {
        "word": "test",
        "definitions": [
            {
                "partOfSpeech": "noun",
                "text": "An examination or quiz",
            }
        ],
    }

    mock_oxford.fetch.return_value = None  # Simulate not found

    # Patch the provider imports
    with (
        patch(
            "floridify.providers.dictionary.api.free_dictionary.FreeDictionaryConnector",
            return_value=mock_free_dict,
        ),
        patch(
            "floridify.providers.dictionary.scraper.wiktionary.WiktionaryConnector",
            return_value=mock_wiktionary,
        ),
        patch(
            "floridify.providers.dictionary.api.oxford.OxfordConnector", return_value=mock_oxford
        ),
    ):
        yield {
            "free_dictionary": mock_free_dict,
            "wiktionary": mock_wiktionary,
            "oxford": mock_oxford,
        }


@pytest_asyncio.fixture
async def mock_openai_client():
    """Mock OpenAI client for API tests."""
    from unittest.mock import AsyncMock, MagicMock, patch

    # Import all response models we need to mock
    from floridify.ai.models import (
        AntonymCandidate,
        AntonymResponse,
        CEFRLevelResponse,
        Collocation,
        CollocationResponse,
        ExampleGenerationResponse,
        FactGenerationResponse,
        FrequencyBandResponse,
        GrammarPatternResponse,
        PronunciationResponse,
        QueryValidationResponse,
        RegionalVariantResponse,
        RegisterClassificationResponse,
        Suggestion,
        SuggestionsResponse,
        SynonymCandidate,
        SynonymGenerationResponse,
        UsageNote,
        UsageNoteResponse,
        WordForm,
        WordFormResponse,
        WordSuggestion,
        WordSuggestionResponse,
    )

    # Create mock connector instance with properly typed methods
    mock_connector = MagicMock()

    # Mock the last_model_used property to return a string
    type(mock_connector).last_model_used = property(lambda self: "gpt-4")

    # Mock the last_model_info property to return a proper ModelInfo
    from floridify.models.base import ModelInfo

    _mock_model_info = ModelInfo(name="gpt-4", confidence=0.95, temperature=0.7)
    type(mock_connector).last_model_info = property(lambda self: _mock_model_info)

    # Mock pronunciation method
    mock_connector.pronunciation = AsyncMock(
        return_value=PronunciationResponse(phonetic="BYOO-tuh-fuhl", ipa="/ˈbjuːtəfəl/")
    )

    # Mock synonym generation
    mock_connector.synthesize_synonyms = AsyncMock(
        return_value=SynonymGenerationResponse(
            synonyms=[
                SynonymCandidate(
                    word="joyful",
                    language="English",
                    relevance=0.9,
                    efflorescence=0.85,
                    explanation="Expresses happiness with energy",
                ),
                SynonymCandidate(
                    word="content",
                    language="English",
                    relevance=0.85,
                    efflorescence=0.8,
                    explanation="Gentle satisfaction",
                ),
                SynonymCandidate(
                    word="pleased",
                    language="English",
                    relevance=0.8,
                    efflorescence=0.75,
                    explanation="Simple satisfaction",
                ),
            ],
            confidence=0.9,
        )
    )

    # Mock antonym generation
    mock_connector.synthesize_antonyms = AsyncMock(
        return_value=AntonymResponse(
            antonyms=[
                AntonymCandidate(
                    word="sad",
                    language="English",
                    relevance=0.9,
                    efflorescence=0.8,
                    explanation="Direct opposite of happiness",
                ),
                AntonymCandidate(
                    word="unhappy",
                    language="English",
                    relevance=0.85,
                    efflorescence=0.75,
                    explanation="Lacking happiness",
                ),
                AntonymCandidate(
                    word="miserable",
                    language="English",
                    relevance=0.8,
                    efflorescence=0.85,
                    explanation="Deeply unhappy state",
                ),
            ],
            confidence=0.9,
        )
    )

    # Mock example generation
    mock_connector.generate_examples = AsyncMock(
        return_value=ExampleGenerationResponse(
            example_sentences=[
                "She gave an elaborate explanation of the process.",
                "The artist created an elaborate mural.",
                "They planned an elaborate celebration.",
            ],
            confidence=0.9,
        )
    )

    # Mock fact generation
    mock_connector.generate_facts = AsyncMock(
        return_value=FactGenerationResponse(
            facts=[
                "The word originates from Latin",
                "It entered English in the 15th century",
                "It has multiple related forms",
            ],
            confidence=0.85,
            categories=["etymology", "history"],
        )
    )

    # Mock suggestions
    mock_connector.suggestions = AsyncMock(
        return_value=SuggestionsResponse(
            suggestions=[
                Suggestion(
                    word="refined",
                    reasoning="Cultured elegance",
                    difficulty_level=3,
                    semantic_category="elegance",
                ),
                Suggestion(
                    word="cultured",
                    reasoning="Sophisticated taste",
                    difficulty_level=3,
                    semantic_category="elegance",
                ),
                Suggestion(
                    word="polished",
                    reasoning="Smooth sophistication",
                    difficulty_level=2,
                    semantic_category="elegance",
                ),
                Suggestion(
                    word="graceful",
                    reasoning="Elegant movement",
                    difficulty_level=2,
                    semantic_category="elegance",
                ),
            ],
            input_analysis="Words suggesting elegance and sophistication",
            confidence=0.88,
        )
    )

    # Mock CEFR assessment
    mock_connector.assess_cefr_level = AsyncMock(
        return_value=CEFRLevelResponse(level="C1", reasoning="Advanced vocabulary", confidence=0.85)
    )

    # Mock frequency assessment
    mock_connector.assess_frequency_band = AsyncMock(
        return_value=FrequencyBandResponse(band=3, reasoning="Moderately common", confidence=0.8)
    )

    # Mock register classification
    mock_connector.classify_register = AsyncMock(
        return_value=RegisterClassificationResponse(
            register="formal", reasoning="Academic language style", confidence=0.85
        )
    )

    # Mock word forms
    mock_connector.identify_word_forms = AsyncMock(
        return_value=WordFormResponse(
            forms=[
                WordForm(type="plural", text="beauties"),
                WordForm(type="adverb", text="beautifully"),
            ]
        )
    )

    # Mock collocations
    mock_connector.assess_collocations = AsyncMock(
        return_value=CollocationResponse(
            collocations=[
                Collocation(type="verb+noun", phrase="make a decision", frequency=0.9),
                Collocation(type="verb+noun", phrase="take action", frequency=0.85),
                Collocation(type="verb+noun", phrase="have an effect", frequency=0.8),
            ]
        )
    )

    # Mock grammar patterns
    mock_connector.assess_grammar_patterns = AsyncMock(
        return_value=GrammarPatternResponse(
            patterns=["[Tn]", "[Tn.pr]"],
            descriptions=["Takes direct object", "Takes object with preposition"],
        )
    )

    # Mock usage notes
    mock_connector.usage_note_generation = AsyncMock(
        return_value=UsageNoteResponse(
            notes=[
                UsageNote(type="confusion", text="Often confused with 'effect'"),
                UsageNote(type="register", text="Used in formal contexts"),
            ]
        )
    )

    # Mock regional variants
    mock_connector.assess_regional_variants = AsyncMock(
        return_value=RegionalVariantResponse(regions=["UK", "US"])
    )

    # Mock query validation
    mock_connector.validate_query = AsyncMock(
        return_value=QueryValidationResponse(
            is_valid=True, reason="Query seeks word suggestions", is_word_suggestion_request=True
        )
    )

    # Mock word suggestions
    mock_connector.suggest_words = AsyncMock(
        return_value=WordSuggestionResponse(
            suggestions=[
                WordSuggestion(
                    word="intelligent",
                    confidence=0.9,
                    efflorescence=0.85,
                    reasoning="Having mental capacity",
                    example_usage="She is an intelligent person.",
                ),
                WordSuggestion(
                    word="clever",
                    confidence=0.85,
                    efflorescence=0.8,
                    reasoning="Quick to understand",
                    example_usage="He solved the puzzle with a clever approach.",
                ),
            ],
            query_type="descriptive",
            original_query="words that describe someone who is very intelligent",
        )
    )

    # Patch both the class and get_openai_connector function
    with (
        patch("floridify.ai.connector.OpenAIConnector", return_value=mock_connector),
        patch("floridify.ai.connector.get_openai_connector", return_value=mock_connector),
    ):
        yield mock_connector


@pytest.fixture
def test_words():
    """Common test words for search and lookup tests."""
    return [
        "apple",
        "banana",
        "cherry",
        "date",
        "elderberry",
        "fig",
        "grape",
        "honeydew",
        "kiwi",
        "lemon",
    ]
