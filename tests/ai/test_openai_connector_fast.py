"""Fast unit tests for OpenAI connector with proper mocking."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.floridify.ai.openai_connector import OpenAIConnector
from src.floridify.ai.schemas import DefinitionSynthesisResponse, WordTypeEnum
from src.floridify.config import OpenAIConfig


class TestOpenAIConnectorFast:
    """Fast unit tests with proper mocking - no network calls."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return OpenAIConfig(api_key="test-key", model="o3", reasoning_effort="high")

    @pytest.fixture
    def connector(self, config):
        """Create connector with mocked client."""
        connector = OpenAIConnector(config)
        connector.client = AsyncMock()
        return connector

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, connector):
        """Test successful embedding generation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        connector.client.embeddings.create.return_value = mock_response

        result = await connector.generate_embedding("test")

        assert result == [0.1, 0.2, 0.3]
        connector.client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_error(self, connector):
        """Test embedding generation with error."""
        connector.client.embeddings.create.side_effect = Exception("API Error")

        result = await connector.generate_embedding("test")

        assert result == []

    @pytest.mark.asyncio
    async def test_structured_definitions_success(self, connector):
        """Test successful structured definition generation."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {
            "definitions": [
                {"word_type": "noun", "definition": "A test definition"},
                {"word_type": "verb", "definition": "To test something"}
            ]
        }
        """
        connector.client.chat.completions.create.return_value = mock_response

        # Test
        result = await connector._generate_definitions_structured("test", {})

        # Assertions
        assert len(result) == 2
        assert result[0].definition == "A test definition"
        assert result[1].definition == "To test something"

    def test_model_capabilities(self, connector):
        """Test model capabilities detection."""
        assert connector.capabilities.uses_reasoning_effort is True
        assert connector.capabilities.supports_temperature is False

    def test_build_request_params_o3_model(self, connector):
        """Test request parameters for o3 model."""

        params = connector._build_request_params("system", "user", DefinitionSynthesisResponse)

        # o3 should not have temperature but should have reasoning_effort
        assert "temperature" not in params
        assert "reasoning_effort" in params
        assert params["reasoning_effort"] == "high"
        assert "response_format" in params

    def test_word_type_mapping(self, connector):
        """Test word type mapping."""
        from src.floridify.models import WordType

        result = connector._map_word_type(WordTypeEnum.NOUN)
        assert result == WordType.NOUN

        result = connector._map_word_type(WordTypeEnum.VERB)
        assert result == WordType.VERB
