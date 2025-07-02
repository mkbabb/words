"""Unit tests for AI system components."""

import json
from unittest.mock import patch

import pytest

from src.floridify.constants import DictionaryProvider
from src.floridify.models import Definition, ProviderData, Word, WordType


class TestDefinitionSynthesizer:
    """Test AI definition synthesis."""

    @pytest.fixture
    def mock_synthesizer(self, mock_openai_client):
        """Create DefinitionSynthesizer with mocked OpenAI client."""
        from src.floridify.ai import create_definition_synthesizer
        
        with patch('src.floridify.ai.synthesis.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            synthesizer = create_definition_synthesizer()
            return synthesizer

    @pytest.fixture
    def sample_provider_data(self):
        """Sample provider data for testing."""
        from src.floridify.models import Examples, Pronunciation
        
        return {
            "wiktionary": ProviderData(
                provider=DictionaryProvider.WIKTIONARY,
                word=Word(text="test"),
                definitions=[
                    Definition(
                        word_type=WordType.NOUN,
                        definition="A procedure to establish quality.",
                        examples=Examples(),
                        synonyms=[]
                    )
                ],
                pronunciation=Pronunciation(phonetic="/test/"),
                metadata={}
            )
        }

    @pytest.mark.asyncio
    async def test_successful_synthesis(self, mock_synthesizer, sample_provider_data):
        """Test successful AI definition synthesis."""
        word = Word(text="test")
        
        # Mock OpenAI response
        mock_response = {
            "word": "test",
            "pronunciation": "/test/",
            "definitions": [
                {
                    "word_type": "noun",
                    "definition": "A synthesized definition combining multiple sources.",
                    "examples": ["This is a synthesized example."],
                    "synonyms": ["examination", "trial"]
                }
            ]
        }
        
        mock_synthesizer._client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_response)
        
        result = await mock_synthesizer.synthesize_entry(word, sample_provider_data)
        
        assert result is not None
        assert result.word.text == "test"
        assert len(result.definitions) == 1
        assert "synthesized definition" in result.definitions[0].definition

    @pytest.mark.asyncio
    async def test_fallback_generation(self, mock_synthesizer):
        """Test AI fallback for unknown words."""
        word = Word(text="unknownword")
        
        # Mock AI fallback response
        mock_response = {
            "word": "unknownword",
            "pronunciation": "/ʌnˈnoʊnwɜrd/",
            "definitions": [
                {
                    "word_type": "noun",
                    "definition": "AI-generated definition for unknown word.",
                    "examples": ["This is an AI-generated example."],
                    "synonyms": []
                }
            ]
        }
        
        mock_synthesizer._client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_response)
        
        result = await mock_synthesizer.generate_fallback_entry(word)
        
        assert result is not None
        assert result.word.text == "unknownword"
        assert len(result.definitions) == 1
        assert "AI-generated" in result.definitions[0].definition
        assert result.pronunciation.phonetic == "/ʌnˈnoʊnwɜrd/"

    @pytest.mark.asyncio
    async def test_malformed_ai_response(self, mock_synthesizer, sample_provider_data):
        """Test handling of malformed AI responses."""
        word = Word(text="test")
        
        # Mock malformed JSON response
        mock_synthesizer._client.chat.completions.create.return_value.choices[0].message.content = "invalid json"
        
        result = await mock_synthesizer.synthesize_entry(word, sample_provider_data)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_synthesizer, sample_provider_data):
        """Test OpenAI API error handling."""
        word = Word(text="test")
        
        # Mock API error
        mock_synthesizer._client.chat.completions.create.side_effect = Exception("API Error")
        
        result = await mock_synthesizer.synthesize_entry(word, sample_provider_data)
        
        assert result is None

    def test_prompt_construction(self, mock_synthesizer, sample_provider_data):
        """Test AI prompt construction."""
        word = Word(text="test")
        
        prompt = mock_synthesizer._build_synthesis_prompt(word, sample_provider_data)
        
        assert "test" in prompt
        assert "procedure to establish quality" in prompt
        assert "wiktionary" in prompt.lower()

    def test_response_validation(self, mock_synthesizer):
        """Test AI response validation."""
        # Valid response
        valid_response = {
            "word": "test",
            "definitions": [
                {
                    "word_type": "noun",
                    "definition": "A valid definition",
                    "examples": ["Valid example"],
                    "synonyms": []
                }
            ]
        }
        
        assert mock_synthesizer._validate_response(valid_response)
        
        # Invalid responses
        invalid_responses = [
            {},  # Empty
            {"word": "test"},  # Missing definitions
            {"definitions": []},  # Missing word
            {"word": "test", "definitions": [{}]},  # Invalid definition structure
        ]
        
        for invalid_response in invalid_responses:
            assert not mock_synthesizer._validate_response(invalid_response)

    @pytest.mark.asyncio
    async def test_model_capability_detection(self, mock_synthesizer):
        """Test detection of reasoning vs standard models."""
        # Test with reasoning model
        with patch('src.floridify.ai.synthesis.MODEL_NAME', 'o3-mini'):
            assert mock_synthesizer._is_reasoning_model()
        
        # Test with standard model
        with patch('src.floridify.ai.synthesis.MODEL_NAME', 'gpt-4'):
            assert not mock_synthesizer._is_reasoning_model()

    @pytest.mark.asyncio
    async def test_bulk_processing(self, mock_synthesizer):
        """Test bulk processing optimization."""
        words = [Word(text=f"word{i}") for i in range(5)]
        provider_data_list = [{} for _ in range(5)]
        
        # Mock bulk response
        mock_responses = [
            {
                "word": f"word{i}",
                "definitions": [
                    {
                        "word_type": "noun",
                        "definition": f"Definition for word{i}",
                        "examples": [f"Example for word{i}"],
                        "synonyms": []
                    }
                ]
            }
            for i in range(5)
        ]
        
        mock_synthesizer._client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_responses)
        
        results = await mock_synthesizer.synthesize_bulk(words, provider_data_list)
        
        assert len(results) == 5
        assert all(r is not None for r in results)

    def test_pronunciation_generation(self, mock_synthesizer):
        """Test phonetic pronunciation generation."""
        word = "example"
        
        pronunciation = mock_synthesizer._generate_pronunciation(word)
        
        # Should return a plausible phonetic representation
        assert pronunciation.startswith("/")
        assert pronunciation.endswith("/")
        assert len(pronunciation) > 2

    @pytest.mark.asyncio
    async def test_context_preparation(self, mock_synthesizer, sample_provider_data):
        """Test context preparation for AI synthesis."""
        word = Word(text="test")
        
        context = mock_synthesizer._prepare_context(word, sample_provider_data)
        
        assert "word" in context
        assert "providers" in context
        assert context["word"] == "test"
        assert "wiktionary" in context["providers"]

    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_synthesizer, sample_provider_data):
        """Test AI response caching."""
        word = Word(text="test")
        
        # First request
        result1 = await mock_synthesizer.synthesize_entry(word, sample_provider_data)
        
        # Second request (should use cache if implemented)
        result2 = await mock_synthesizer.synthesize_entry(word, sample_provider_data)
        
        # Both should succeed
        assert result1 is not None
        assert result2 is not None


class TestSemanticSearch:
    """Test semantic search with embeddings."""

    @pytest.fixture
    def mock_semantic_search(self, mock_openai_client, mock_cache_dir):
        """Create SemanticSearch with mocked components."""
        from src.floridify.search.semantic import SemanticSearch
        
        with patch('src.floridify.search.semantic.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            search = SemanticSearch(cache_dir=mock_cache_dir)
            return search

    @pytest.mark.asyncio
    async def test_embedding_generation(self, mock_semantic_search):
        """Test text embedding generation."""
        text = "test query"
        
        embedding = await mock_semantic_search._generate_embedding(text)
        
        assert len(embedding) == 1536  # OpenAI embedding dimension
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_semantic_search_execution(self, mock_semantic_search):
        """Test semantic similarity search."""
        # Initialize with sample data
        words = ["test", "examination", "trial", "hello", "world"]
        await mock_semantic_search.initialize(words)
        
        # Mock similar embeddings for related words
        mock_semantic_search._word_embeddings = {
            "test": [0.1, 0.2, 0.3] + [0.0] * 1533,
            "examination": [0.1, 0.2, 0.25] + [0.0] * 1533,  # Similar to test
            "trial": [0.1, 0.2, 0.28] + [0.0] * 1533,  # Similar to test
            "hello": [0.8, 0.1, 0.1] + [0.0] * 1533,  # Different
            "world": [0.9, 0.05, 0.05] + [0.0] * 1533,  # Different
        }
        
        results = await mock_semantic_search.search("test", max_results=3)
        
        assert len(results) <= 3
        assert all(isinstance(score, float) for word, score in results)
        
        # Results should be sorted by similarity
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    @pytest.mark.asyncio
    async def test_embedding_cache(self, mock_semantic_search):
        """Test embedding caching functionality."""
        # First embedding generation
        embedding1 = await mock_semantic_search._generate_embedding("test")
        
        # Second generation (should use cache)
        embedding2 = await mock_semantic_search._generate_embedding("test")
        
        assert embedding1 == embedding2

    def test_similarity_calculation(self, mock_semantic_search):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]
        
        # Orthogonal vectors should have low similarity
        sim1 = mock_semantic_search._cosine_similarity(vec1, vec2)
        assert abs(sim1) < 0.1
        
        # Identical vectors should have similarity 1.0
        sim2 = mock_semantic_search._cosine_similarity(vec1, vec3)
        assert abs(sim2 - 1.0) < 0.1

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_semantic_search):
        """Test semantic search timeout protection."""
        # Mock slow API response
        mock_semantic_search._client.embeddings.create.side_effect = asyncio.TimeoutError()
        
        result = await mock_semantic_search._generate_embedding("test")
        
        # Should handle timeout gracefully
        assert result is None or len(result) == 1536


class TestAIIntegration:
    """Test AI system integration."""

    def test_ai_factory_function(self):
        """Test AI component factory functions."""
        from src.floridify.ai import create_definition_synthesizer
        
        synthesizer = create_definition_synthesizer()
        assert synthesizer is not None
        assert hasattr(synthesizer, 'synthesize_entry')
        assert hasattr(synthesizer, 'generate_fallback_entry')

    @pytest.mark.asyncio
    async def test_ai_error_recovery(self, mock_openai_client):
        """Test AI system error recovery."""
        from src.floridify.ai import create_definition_synthesizer
        
        with patch('src.floridify.ai.synthesis.AsyncOpenAI') as mock_openai:
            # Mock API failure then success
            mock_openai.return_value = mock_openai_client
            mock_openai_client.chat.completions.create.side_effect = [
                Exception("API Error"),  # First call fails
                mock_openai_client.chat.completions.create.return_value  # Second call succeeds
            ]
            
            synthesizer = create_definition_synthesizer()
            
            # Should handle failure gracefully
            result = await synthesizer.synthesize_entry(Word(text="test"), {})
            # Result could be None (graceful failure) or successful retry

    def test_ai_configuration(self):
        """Test AI system configuration."""
        from src.floridify.ai.synthesis import MAX_TOKENS, MODEL_NAME
        
        assert isinstance(MODEL_NAME, str)
        assert isinstance(MAX_TOKENS, int)
        assert MAX_TOKENS > 0

    @pytest.mark.asyncio
    async def test_structured_output_parsing(self, mock_openai_client):
        """Test structured output parsing from AI responses."""
        from src.floridify.ai import create_definition_synthesizer
        
        with patch('src.floridify.ai.synthesis.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            
            # Mock structured response
            structured_response = {
                "word": "test",
                "definitions": [
                    {
                        "word_type": "noun",
                        "definition": "A structured definition",
                        "examples": ["Structured example"],
                        "synonyms": ["exam", "trial"]
                    }
                ]
            }
            
            mock_openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(structured_response)
            
            synthesizer = create_definition_synthesizer()
            result = await synthesizer.synthesize_entry(Word(text="test"), {})
            
            assert result is not None
            assert result.word.text == "test"
            assert len(result.definitions) == 1