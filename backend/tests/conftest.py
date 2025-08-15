"""
Comprehensive test configuration with proper MongoDB setup and async fixture handling.
"""

import asyncio
import os
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from pytest_mock import MockerFixture

# Test configuration
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mongodb://localhost:27017")
TEST_DATABASE_NAME_PREFIX = "test_floridify"


# Minimal imports to avoid circular dependencies
def get_all_document_models():
    """Dynamically import all document models to avoid import issues."""
    try:
        from src.floridify.models.base import (
            AudioMedia,
            ImageMedia,
        )
        from src.floridify.models import (
            Definition,
            DictionaryEntry,
            Example,
            Fact,
            Pronunciation,
            Word,
        )
        from src.floridify.models.phrasal import PhrasalExpression
        from src.floridify.models.relationships import WordRelationship
        from src.floridify.models.word_of_the_day import (
            WordOfTheDayBatch,
            WordOfTheDayConfig,
        )
        from src.floridify.wordlist.models import WordList
        
        return [
            Word,
            Definition,
            Example,
            Pronunciation,
            Fact,
            DictionaryEntry,
            PhrasalExpression,
            WordRelationship,
            WordList,
            AudioMedia,
            ImageMedia,
            WordOfTheDayBatch,
            WordOfTheDayConfig,
        ]
    except ImportError as e:
        # Return empty list if imports fail - tests will skip MongoDB functionality
        print(f"Warning: Could not import models: {e}")
        return []


# MongoDB Client Fixtures  
@pytest_asyncio.fixture(scope="function")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create MongoDB client for test session."""
    client = None
    try:
        client = AsyncIOMotorClient(TEST_DATABASE_URL)
        # Test the connection
        await client.admin.command("ping")
        yield client
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        if client:
            client.close()


@pytest_asyncio.fixture
async def test_db_name() -> str:
    """Generate unique test database name."""
    return f"{TEST_DATABASE_NAME_PREFIX}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def test_db(mongodb_client: AsyncIOMotorClient, test_db_name: str):
    """Create isolated test database with Beanie initialization."""
    db = mongodb_client[test_db_name]
    
    # Get all document models
    document_models = get_all_document_models()
    
    if document_models:
        try:
            # Initialize Beanie with the test database
            await init_beanie(database=db, document_models=document_models)
        except Exception as e:
            pytest.skip(f"Could not initialize Beanie: {e}")
    
    yield db
    
    # Cleanup: Drop test database
    try:
        await mongodb_client.drop_database(test_db_name)
    except Exception:
        pass  # Ignore cleanup errors


# Storage Mock Fixture
@pytest_asyncio.fixture
async def mock_storage(test_db, mongodb_client, test_db_name, mocker):
    """Mock MongoDB storage to use test database."""
    try:
        from src.floridify.storage.mongodb import MongoDBStorage
        
        # Create a test storage instance
        test_storage = MongoDBStorage(
            connection_string=TEST_DATABASE_URL,
            database_name=test_db_name,
        )
        test_storage.client = mongodb_client
        test_storage._initialized = True
        
        # Mock the global storage functions to return our test storage
        mocker.patch("src.floridify.storage.mongodb._storage", test_storage)
        mocker.patch("src.floridify.storage.mongodb.get_storage", return_value=test_storage)
        mocker.patch("src.floridify.storage.mongodb.get_database", return_value=test_db)
        
        return test_storage
    except ImportError as e:
        pytest.skip(f"Could not import MongoDB storage: {e}")


# Application Fixtures
@pytest_asyncio.fixture
async def test_app(test_db, mock_storage):
    """Create FastAPI test app with test database."""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        from src.floridify.api.middleware import CacheHeadersMiddleware, LoggingMiddleware
        from src.floridify.api.routers import (
            ai,
            corpus,
            definitions,
            health,
            lookup,
            search,
            suggestions,
            wordlists,
        )
        
        # Create test app without lifespan (to avoid production DB initialization)
        app = FastAPI(
            title="Floridify Dictionary API (Test)",
            description="AI-enhanced dictionary with semantic search (Test Mode)",
            version="0.1.0-test",
        )
        
        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
        app.add_middleware(CacheHeadersMiddleware)
        app.add_middleware(LoggingMiddleware)
        
        # Add routers
        api_v1_prefix = "/api/v1"
        app.include_router(health, prefix="", tags=["health"])
        app.include_router(lookup, prefix=api_v1_prefix, tags=["lookup"])
        app.include_router(search, prefix=api_v1_prefix, tags=["search"])
        app.include_router(corpus, prefix=api_v1_prefix, tags=["corpus"])
        app.include_router(suggestions, prefix=api_v1_prefix, tags=["suggestions"])
        app.include_router(ai, prefix=api_v1_prefix, tags=["ai"])
        app.include_router(definitions, prefix=f"{api_v1_prefix}/definitions", tags=["definitions"])
        app.include_router(wordlists, prefix=f"{api_v1_prefix}/wordlists", tags=["wordlists"])
        
        return app
    except ImportError as e:
        pytest.skip(f"Could not import FastAPI app: {e}")


@pytest_asyncio.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    if test_app is None:
        pytest.skip("FastAPI app not available")
    
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Model Factory Fixtures
@pytest_asyncio.fixture
async def word_factory(test_db):
    """Factory for creating test words."""
    if test_db is None:
        pytest.skip("Test database not available")
    
    created_words = []
    
    async def _create_word(
        text: str = "test",
        language: str = "en",
        normalized: str | None = None,
        **kwargs
    ):
        try:
            from src.floridify.models.models import Word
            
            word_data = {
                "text": text,
                "language": language,
                "normalized": normalized or text.lower(),
                "offensive_flag": False,
                **kwargs
            }
            word = await Word(**word_data).create()
            created_words.append(word)
            return word
        except ImportError:
            pytest.skip("Word model not available")
    
    yield _create_word
    
    # Cleanup created words
    for word in created_words:
        try:
            await word.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def definition_factory(test_db):
    """Factory for creating test definitions."""
    if test_db is None:
        pytest.skip("Test database not available")
    
    created_definitions = []
    
    async def _create_definition(
        word_instance=None,
        part_of_speech: str = "noun",
        text: str = "A test definition",
        **kwargs
    ):
        try:
            from src.floridify.models.models import Definition, Word
            
            if word_instance is None:
                # Create a default word
                word_instance = await Word(
                    text="testword",
                    language="en", 
                    normalized="testword"
                ).create()
            
            definition_data = {
                "word_id": word_instance.id,
                "part_of_speech": part_of_speech,
                "text": text,
                **kwargs
            }
            definition = await Definition(**definition_data).create()
            created_definitions.append(definition)
            return definition
        except ImportError:
            pytest.skip("Definition model not available")
    
    yield _create_definition
    
    # Cleanup created definitions
    for definition in created_definitions:
        try:
            await definition.delete()
        except Exception:
            pass


@pytest_asyncio.fixture
async def wordlist_factory(test_db):
    """Factory for creating test wordlists."""
    if test_db is None:
        pytest.skip("Test database not available")
    
    created_wordlists = []
    
    async def _create_wordlist(
        name: str = "Test Wordlist",
        description: str = "A test wordlist",
        words: list[str] | None = None,
        **kwargs
    ):
        try:
            from src.floridify.models.models import Word
            from src.floridify.wordlist.models import WordList, WordListItem
            
            # Create Word documents for each word text and get WordListItems
            word_items = []
            for word_text in (words or ["test", "example", "sample"]):
                # Create a Word document first
                word_doc = await Word(
                    text=word_text,
                    language="en",
                    normalized=word_text.lower()
                ).create()
                
                # Create WordListItem with the word_id
                word_item = WordListItem(
                    word_id=word_doc.id,
                    frequency=1000,
                )
                word_items.append(word_item)
            
            wordlist_data = {
                "name": name,
                "description": description,
                "hash_id": f"test_{uuid.uuid4().hex[:8]}",
                "words": word_items,
                "total_words": len(word_items),
                "unique_words": len(word_items),
                "is_public": False,
                **kwargs
            }
            wordlist = await WordList(**wordlist_data).create()
            created_wordlists.append(wordlist)
            return wordlist
        except ImportError:
            pytest.skip("WordList model not available")
    
    yield _create_wordlist
    
    # Cleanup created wordlists
    for wordlist in created_wordlists:
        try:
            await wordlist.delete()
        except Exception:
            pass


# Mock Fixtures
@pytest.fixture
def mock_openai_client(mocker: MockerFixture):
    """Mock OpenAI client for AI synthesis testing.""" 
    from src.floridify.ai.models import (
        AntonymResponse,
        CEFRLevelResponse,
        CollocationResponse,
        ExampleGenerationResponse,
        FactGenerationResponse,
        FrequencyBandResponse,
        GrammarPatternResponse,
        PronunciationResponse,
        QueryValidationResponse,
        RegionalVariantResponse,
        RegisterClassificationResponse,
        SuggestionsResponse,
        SynonymGenerationResponse,
        UsageNoteResponse,
        WordFormResponse,
        WordSuggestionResponse,
    )
    
    # Mock the OpenAI connector instance and its methods
    mock_connector = mocker.patch("src.floridify.ai.connector.OpenAIConnector")
    
    # Create mock instance
    mock_instance = mock_connector.return_value
    
    # Mock each async method with proper return types
    async def mock_pronunciation(word: str) -> PronunciationResponse:
        return PronunciationResponse(
            phonetic=f"{word.upper()}",
            ipa=f"/ˈ{word.lower()}/",
            confidence=0.95
        )
    
    async def mock_synthesize_synonyms(
        self, word: str, definition: str, part_of_speech: str, existing_synonyms: list[str], count: int = 10
    ) -> SynonymGenerationResponse:
        return SynonymGenerationResponse(
            synonyms=[
                {
                    "word": "joyful", 
                    "language": "English",
                    "relevance": 0.88,
                    "efflorescence": 0.85,
                    "explanation": "Conveys a sense of buoyant happiness and delight"
                },
                {
                    "word": "cheerful", 
                    "language": "English", 
                    "relevance": 0.82,
                    "efflorescence": 0.78,
                    "explanation": "Expresses bright and optimistic mood"
                }
            ],
            confidence=0.90
        )
    
    async def mock_generate_examples(
        self, word: str, part_of_speech: str, definition: str, count: int = 1, **kwargs
    ) -> ExampleGenerationResponse:
        return ExampleGenerationResponse(
            example_sentences=[
                "In her presentation, she elaborated on the project's scope, highlighting key technologies and expected outcomes over the next five years."
            ],
            confidence=0.88
        )
    
    async def mock_generate_facts(
        self, word: str, definition: str, count: int = 5, previous_words: list[str] | None = None, **kwargs
    ) -> FactGenerationResponse:
        return FactGenerationResponse(
            facts=[
                f"The word '{word}' was coined by Horace Walpole in 1754 after reading a Persian fairy tale, 'The Three Princes of Serendip,' where the heroes were always making accidental discoveries."
            ],
            confidence=0.85,
            categories=["etymology", "historical"]
        )
    
    async def mock_suggestions(self, input_words: list[str], count: int = 5, **kwargs) -> SuggestionsResponse:
        return SuggestionsResponse(
            suggestions=[
                {
                    "word": "graceful",
                    "reasoning": "This word embodies both sophistication and elegance in movement or manner",
                    "difficulty_level": 3,
                    "semantic_category": "elegance"
                }
            ],
            input_analysis="The input words suggest a focus on refined, cultured qualities emphasizing grace and style.",
            confidence=0.93
        )
    
    async def mock_assess_cefr_level(word: str, **kwargs) -> CEFRLevelResponse:
        return CEFRLevelResponse(
            word=word,
            assessment={
                "level": "C2",
                "confidence": 0.95,
                "reasoning": f"The word '{word}' is not commonly used in everyday language and requires advanced vocabulary knowledge. It demonstrates sophisticated linguistic complexity, as it refers to a deep understanding or insight, which aligns with the characteristics of C2 vocabulary."
            }
        )
    
    async def mock_assess_frequency_band(word: str, **kwargs) -> FrequencyBandResponse:
        return FrequencyBandResponse(
            word=word,
            frequency_band=7500,
            confidence=0.88
        )
    
    async def mock_classify_register(word: str, **kwargs) -> RegisterClassificationResponse:
        return RegisterClassificationResponse(
            word=word,
            register="formal",
            confidence=0.92
        )
    
    async def mock_identify_word_forms(word: str, **kwargs) -> WordFormResponse:
        return WordFormResponse(
            word=word,
            forms={"verb": f"{word}ed", "noun": f"{word}ness"}
        )
    
    async def mock_assess_collocations(word: str, **kwargs) -> CollocationResponse:
        return CollocationResponse(
            word=word,
            collocations=[f"{word} example", f"very {word}"]
        )
    
    async def mock_assess_grammar_patterns(word: str, **kwargs) -> GrammarPatternResponse:
        return GrammarPatternResponse(
            word=word,
            patterns=[f"{word} + noun", f"adverb + {word}"]
        )
    
    async def mock_usage_note_generation(word: str, **kwargs) -> UsageNoteResponse:
        return UsageNoteResponse(
            word=word,
            usage_notes=f"The word '{word}' is commonly used in formal contexts."
        )
    
    async def mock_assess_regional_variants(self, definition: str, **kwargs) -> RegionalVariantResponse:
        return RegionalVariantResponse(
            regions=["US", "UK", "global"],
            confidence=0.75
        )
    
    async def mock_validate_query(query: str, **kwargs) -> QueryValidationResponse:
        return QueryValidationResponse(
            query=query,
            is_valid=True,
            confidence=0.95
        )
    
    async def mock_suggest_words(query: str, **kwargs) -> WordSuggestionResponse:
        return WordSuggestionResponse(
            query=query,
            suggestions=[f"{query}_suggestion1", f"{query}_suggestion2"]
        )
    
    async def mock_synthesize_antonyms(
        self, word: str, definition: str, part_of_speech: str, existing_antonyms: list[str], **kwargs
    ) -> AntonymResponse:
        return AntonymResponse(
            antonyms=[f"un{word}", f"non-{word}"],
            confidence=0.85
        )
    
    # Assign mocked methods to the instance
    mock_instance.pronunciation = mock_pronunciation
    mock_instance.synthesize_synonyms = mock_synthesize_synonyms
    mock_instance.generate_examples = mock_generate_examples
    mock_instance.generate_facts = mock_generate_facts
    mock_instance.suggestions = mock_suggestions
    mock_instance.assess_cefr_level = mock_assess_cefr_level
    mock_instance.assess_frequency_band = mock_assess_frequency_band
    mock_instance.classify_register = mock_classify_register
    mock_instance.identify_word_forms = mock_identify_word_forms
    mock_instance.assess_collocations = mock_assess_collocations
    mock_instance.assess_grammar_patterns = mock_assess_grammar_patterns
    mock_instance.usage_note_generation = mock_usage_note_generation
    mock_instance.assess_regional_variants = mock_assess_regional_variants
    mock_instance.validate_query = mock_validate_query
    mock_instance.suggest_words = mock_suggest_words
    mock_instance.synthesize_antonyms = mock_synthesize_antonyms
    
    # Also mock the factory function and global singleton
    mocker.patch("src.floridify.ai.factory.get_openai_connector", return_value=mock_instance)
    mocker.patch("src.floridify.ai.get_openai_connector", return_value=mock_instance)
    mocker.patch("src.floridify.ai.factory._openai_connector", mock_instance)
    
    # Mock the imports where OpenAI connector is used
    mocker.patch("src.floridify.ai.connector.OpenAIConnector", return_value=mock_instance)
    
    return mock_connector


@pytest.fixture
def mock_dictionary_providers(mocker: MockerFixture):
    """Mock dictionary provider responses."""
    mock_wiktionary = mocker.patch("src.floridify.connectors.wiktionary.WiktionaryConnector")
    
    mock_definition_data = {
        "word": "test",
        "language": "en",
        "definitions": [
            {
                "part_of_speech": "noun",
                "text": "A procedure for critical evaluation",
                "examples": ["This is a test."]
            }
        ],
        "pronunciation": {
            "ipa": "tɛst",
            "phonetic": "/test/"
        },
        "etymology": "From Latin testum"
    }
    
    def mock_lookup_word(word: str, **kwargs):
        return mock_definition_data
    
    mock_wiktionary.return_value.lookup_word = mock_lookup_word
    return mock_wiktionary


@pytest.fixture
def mock_search_engine(mocker: MockerFixture):
    """Mock search engine operations."""
    mock_search = mocker.patch("src.floridify.core.search_pipeline.get_search_engine")
    
    class MockSearchEngine:
        def search(self, query: str, **kwargs):
            return [
                {"word": "test", "score": 1.0, "method": "exact"},
                {"word": "testing", "score": 0.8, "method": "fuzzy"},
                {"word": "examination", "score": 0.6, "method": "semantic"}
            ]
        
        def find_best_match(self, query: str, **kwargs):
            results = self.search(query)
            return results[0] if results else None
    
    mock_search.return_value = MockSearchEngine()
    return mock_search


# Performance Testing Fixtures
@pytest.fixture
def performance_thresholds():
    """Performance benchmarks for testing."""
    return {
        "lookup_simple": 1.0,      # seconds
        "lookup_complex": 2.0,     # seconds  
        "search_basic": 0.2,       # seconds
        "batch_lookup_5": 5.0,     # seconds
        "wordlist_upload": 10.0,   # seconds
        "ai_synthesis": 3.0,       # seconds
    }


# Test Data Fixtures
@pytest.fixture
def test_words():
    """Common test words for consistent testing."""
    return [
        "test", "example", "sample", "word", "definition",
        "happy", "sad", "run", "walk", "beautiful",
        "ephemeral", "serendipity", "ubiquitous", "facetious", "perspicacious"
    ]


@pytest.fixture
def test_definitions():
    """Sample definitions for testing."""
    return [
        {
            "word": "test",
            "part_of_speech": "noun",
            "text": "A procedure for critical evaluation",
            "examples": ["This is a test of the system."]
        },
        {
            "word": "test", 
            "part_of_speech": "verb",
            "text": "To try something in order to see if it works",
            "examples": ["Let's test this new feature."]
        }
    ]


# Utility Functions for Tests
def assert_valid_object_id(obj_id: Any) -> None:
    """Assert that object ID is valid."""
    from bson import ObjectId
    assert isinstance(obj_id, ObjectId) or (isinstance(obj_id, str) and ObjectId.is_valid(obj_id))


def assert_response_structure(response_data: dict[str, Any], required_fields: list[str]) -> None:
    """Assert response has required structure."""
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"


async def wait_for_async_operation(operation, timeout: float = 5.0):
    """Wait for async operation with timeout."""
    return await asyncio.wait_for(operation, timeout=timeout)