"""Tests for AI comprehension system."""

from __future__ import annotations

import pytest

from src.floridify.ai import DefinitionSynthesizer, OpenAIConnector, WordProcessingPipeline
from src.floridify.config import Config, OpenAIConfig
from src.floridify.models import (
    ProviderData,
    WordType,
)


class TestOpenAIConnector:
    """Test cases for OpenAI connector."""

    def test_openai_connector_initialization(self) -> None:
        """Test OpenAI connector can be initialized."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)

        assert connector.config.api_key == "test-key"
        assert connector.config.model == "gpt-4o"  # default
        assert connector.client is not None
        assert connector.capabilities is not None

    def test_convert_ai_definitions(self) -> None:
        """Test converting AI definitions to internal format."""
        from src.floridify.ai.schemas import AIDefinition, WordTypeEnum
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)

        ai_definitions = [
            AIDefinition(word_type=WordTypeEnum.NOUN, definition="A large body of water completely surrounded by land."),
            AIDefinition(word_type=WordTypeEnum.VERB, definition="To form a lake or collect in a lake-like manner."),
        ]

        definitions = connector._convert_ai_definitions(ai_definitions)

        assert len(definitions) == 2
        assert definitions[0].word_type == WordType.NOUN
        assert "large body of water" in definitions[0].definition
        assert definitions[1].word_type == WordType.VERB
        assert "form a lake" in definitions[1].definition

    def test_map_word_type(self) -> None:
        """Test mapping AI word types to internal WordType enum."""
        from src.floridify.ai.schemas import WordTypeEnum
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)

        # Test various word type mappings
        assert connector._map_word_type(WordTypeEnum.NOUN) == WordType.NOUN
        assert connector._map_word_type(WordTypeEnum.VERB) == WordType.VERB
        assert connector._map_word_type(WordTypeEnum.ADJECTIVE) == WordType.ADJECTIVE
        assert connector._map_word_type(WordTypeEnum.ADVERB) == WordType.ADVERB

    def test_build_request_params(self) -> None:
        """Test building OpenAI API request parameters."""
        from src.floridify.ai.schemas import DefinitionSynthesisResponse
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)

        system_message = "You are a helpful assistant."
        user_prompt = "Define the word 'test'."
        
        params = connector._build_request_params(
            system_message=system_message,
            user_prompt=user_prompt,
            response_schema=DefinitionSynthesisResponse
        )

        assert params["model"] == "gpt-4o"
        assert "messages" in params
        assert len(params["messages"]) == 2
        assert params["messages"][0]["role"] == "system"
        assert params["messages"][1]["role"] == "user"

    def test_model_capabilities(self) -> None:
        """Test model capability detection."""
        from src.floridify.ai.schemas import get_model_capabilities, is_reasoning_model
        
        # Test reasoning model
        o3_caps = get_model_capabilities("o3")
        assert o3_caps["supports_structured_outputs"] == True
        assert is_reasoning_model("o3") == True
        
        # Test standard model
        gpt4_caps = get_model_capabilities("gpt-4o")
        assert gpt4_caps["supports_structured_outputs"] == True
        assert is_reasoning_model("gpt-4o") == False


class TestDefinitionSynthesizer:
    """Test cases for definition synthesizer."""

    @pytest.fixture
    def mock_openai_connector(self) -> OpenAIConnector:
        """Create a mock OpenAI connector for testing."""
        config = OpenAIConfig(api_key="test-key")
        return OpenAIConnector(config)

    @pytest.fixture
    def mock_storage(self) -> None:
        """Create a mock storage for testing."""
        return None  # For basic tests, we can use None

    def test_synthesizer_initialization(
        self, mock_openai_connector: OpenAIConnector, mock_storage: None
    ) -> None:
        """Test synthesizer can be initialized."""
        synthesizer = DefinitionSynthesizer(mock_openai_connector, mock_storage)

        assert synthesizer.openai_connector == mock_openai_connector
        assert synthesizer.storage == mock_storage

    def test_extract_best_pronunciation(
        self, mock_openai_connector: OpenAIConnector, mock_storage: None
    ) -> None:
        """Test extracting best pronunciation from provider data."""
        synthesizer = DefinitionSynthesizer(mock_openai_connector, mock_storage)

        # Create sample provider data without pronunciation
        provider_data = {"wiktionary": ProviderData(provider_name="wiktionary", definitions=[])}

        pronunciation = synthesizer._extract_best_pronunciation(provider_data)

        # Should return default pronunciation
        assert pronunciation.phonetic == ""
        assert pronunciation.ipa is None


class TestWordProcessingPipeline:
    """Test cases for word processing pipeline."""

    @pytest.fixture
    def mock_config(self) -> Config:
        """Create a mock config for testing."""
        # This would normally load from TOML, but for tests we create manually
        from src.floridify.config import (
            DictionaryComConfig,
            OpenAIConfig,
            OxfordConfig,
            ProcessingConfig,
            RateLimits,
        )

        return Config(
            openai=OpenAIConfig(api_key="test-openai-key"),
            oxford=OxfordConfig(app_id="test-app-id", api_key="test-oxford-key"),
            dictionary_com=DictionaryComConfig(authorization="test-auth"),
            rate_limits=RateLimits(),
            processing=ProcessingConfig(),
        )

    def test_pipeline_initialization(self, mock_config: Config) -> None:
        """Test pipeline can be initialized."""
        from src.floridify.storage.mongodb import MongoDBStorage

        storage = MongoDBStorage()
        pipeline = WordProcessingPipeline(mock_config, storage)

        assert pipeline.config == mock_config
        assert pipeline.storage == storage
        assert len(pipeline.connectors) == 3  # wiktionary, oxford, dictionary_com
        assert "wiktionary" in pipeline.connectors
        assert "oxford" in pipeline.connectors
        assert "dictionary_com" in pipeline.connectors

    def test_get_processing_stats(self, mock_config: Config) -> None:
        """Test getting processing statistics."""
        from src.floridify.storage.mongodb import MongoDBStorage

        storage = MongoDBStorage()
        pipeline = WordProcessingPipeline(mock_config, storage)

        stats = pipeline.get_processing_stats()

        assert "providers_configured" in stats
        assert stats["providers_configured"] == 3
        assert "storage_connected" in stats
        assert "ai_model" in stats
        assert "embedding_model" in stats
