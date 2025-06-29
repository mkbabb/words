"""Tests for AI comprehension system."""

from __future__ import annotations

import pytest

from src.floridify.ai import OpenAIConnector, DefinitionSynthesizer, WordProcessingPipeline
from src.floridify.config import Config, OpenAIConfig
from src.floridify.models import (
    Definition,
    Examples,
    GeneratedExample,
    ProviderData,
    Word,
    WordType,
)


class TestOpenAIConnector:
    """Test cases for OpenAI connector."""

    def test_openai_connector_initialization(self) -> None:
        """Test OpenAI connector can be initialized."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)
        
        assert connector.config.api_key == "test-key"
        assert connector.config.model == "gpt-4"  # default
        assert connector.client is not None
        assert connector.prompt_loader is not None

    def test_parse_ai_definitions(self) -> None:
        """Test parsing AI response into definitions."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)
        
        ai_response = """
        NOUN: A large body of water completely surrounded by land.
        VERB: To form a lake or collect in a lake-like manner.
        """
        
        definitions = connector._parse_ai_definitions(ai_response)
        
        assert len(definitions) == 2
        assert definitions[0].word_type == WordType.NOUN
        assert "large body of water" in definitions[0].definition
        assert definitions[1].word_type == WordType.VERB
        assert "form a lake" in definitions[1].definition

    def test_parse_example_sentences(self) -> None:
        """Test parsing AI response into example sentences."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)
        
        ai_response = """
        1. The serene lake reflected the mountain peaks perfectly.
        2. We decided to lake our afternoon by the peaceful shoreline.
        """
        
        sentences = connector._parse_example_sentences(ai_response)
        
        assert len(sentences) == 2
        assert "serene lake reflected" in sentences[0]
        assert "lake our afternoon" in sentences[1]

    def test_map_pos_to_word_type(self) -> None:
        """Test mapping part of speech strings to WordType enum."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)
        
        assert connector._map_pos_to_word_type("NOUN") == WordType.NOUN
        assert connector._map_pos_to_word_type("VERB") == WordType.VERB
        assert connector._map_pos_to_word_type("ADJECTIVE") == WordType.ADJECTIVE
        assert connector._map_pos_to_word_type("UNKNOWN") is None

    def test_prepare_synthesis_context(self) -> None:
        """Test preparing context from provider data."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)
        
        # Create sample provider data
        wiktionary_data = ProviderData(
            provider_name="wiktionary",
            definitions=[
                Definition(
                    word_type=WordType.NOUN,
                    definition="A body of water",
                    examples=Examples(
                        generated=[GeneratedExample(sentence="The lake was calm.")]
                    ),
                )
            ],
        )
        
        provider_data = {"wiktionary": wiktionary_data}
        context = connector._prepare_synthesis_context("lake", provider_data)
        
        assert "Word: lake" in context
        assert "WIKTIONARY DEFINITIONS:" in context
        assert "A body of water" in context
        assert "The lake was calm." in context


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
        provider_data = {
            "wiktionary": ProviderData(provider_name="wiktionary", definitions=[])
        }
        
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