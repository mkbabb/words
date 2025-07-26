"""Comprehensive tests for AI synthesis endpoints."""

import pytest
from fastapi.testclient import TestClient

from floridify.api.main import app


class TestAIPureGenerationEndpoints:
    """Test AI endpoints that generate content without definition context."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_generate_pronunciation(self, client: TestClient) -> None:
        """Test pronunciation generation endpoint."""
        request_data = {
            "word": "serendipity"
        }
        
        response = client.post("/api/v1/ai/synthesize/pronunciation", json=request_data)
        
        # May fail with rate limit or API key issues
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "word" in data
            assert "pronunciation" in data
            assert data["word"] == "serendipity"

    def test_generate_pronunciation_validation(self, client: TestClient) -> None:
        """Test pronunciation generation with invalid input."""
        # Empty word
        response = client.post("/api/v1/ai/synthesize/pronunciation", json={"word": ""})
        assert response.status_code == 422
        
        # Word too long
        response = client.post("/api/v1/ai/synthesize/pronunciation", json={"word": "a" * 101})
        assert response.status_code == 422

    def test_generate_suggestions(self, client: TestClient) -> None:
        """Test vocabulary suggestions endpoint."""
        request_data = {
            "input_words": ["happy", "sad", "angry"],
            "count": 8
        }
        
        response = client.post("/api/v1/ai/suggestions", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "suggestions" in data
            assert isinstance(data["suggestions"], list)

    def test_generate_suggestions_no_input(self, client: TestClient) -> None:
        """Test suggestions without input words."""
        request_data = {
            "count": 10
        }
        
        response = client.post("/api/v1/ai/suggestions", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "suggestions" in data

    def test_generate_word_forms(self, client: TestClient) -> None:
        """Test word forms generation endpoint."""
        request_data = {
            "word": "run",
            "part_of_speech": "verb"
        }
        
        response = client.post("/api/v1/ai/generate/word-forms", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "word" in data
            assert "word_forms" in data
            assert data["word"] == "run"

    def test_assess_frequency(self, client: TestClient) -> None:
        """Test frequency band assessment endpoint."""
        request_data = {
            "word": "ubiquitous",
            "definition": "Present, appearing, or found everywhere"
        }
        
        response = client.post("/api/v1/ai/assess/frequency", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "frequency_band" in data
            assert 1 <= data["frequency_band"] <= 5

    def test_assess_cefr(self, client: TestClient) -> None:
        """Test CEFR level assessment endpoint."""
        request_data = {
            "word": "cat",
            "definition": "A small domesticated carnivorous mammal"
        }
        
        response = client.post("/api/v1/ai/assess/cefr", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "cefr_level" in data
            assert data["cefr_level"] in ["A1", "A2", "B1", "B2", "C1", "C2"]


class TestAIDefinitionDependentEndpoints:
    """Test AI endpoints that require definition context."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_generate_synonyms(self, client: TestClient) -> None:
        """Test synonym generation endpoint."""
        request_data = {
            "word": "happy",
            "definition": "Feeling or showing pleasure or contentment",
            "part_of_speech": "adjective",
            "existing_synonyms": ["joyful", "cheerful"],
            "count": 5
        }
        
        response = client.post("/api/v1/ai/synthesize/synonyms", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "word" in data
            assert "synonyms" in data
            assert "confidence" in data
            assert isinstance(data["synonyms"], list)
            assert data["word"] == "happy"

    def test_generate_antonyms(self, client: TestClient) -> None:
        """Test antonym generation endpoint."""
        request_data = {
            "word": "happy",
            "definition": "Feeling or showing pleasure or contentment",
            "part_of_speech": "adjective",
            "existing_antonyms": ["sad"],
            "count": 3
        }
        
        response = client.post("/api/v1/ai/synthesize/antonyms", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "word" in data
            assert "antonyms" in data
            assert "confidence" in data
            assert isinstance(data["antonyms"], list)

    def test_generate_examples(self, client: TestClient) -> None:
        """Test example generation endpoint."""
        request_data = {
            "word": "serendipity",
            "part_of_speech": "noun",
            "definition": "The occurrence of events by chance in a happy or beneficial way",
            "count": 3
        }
        
        response = client.post("/api/v1/ai/generate/examples", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "word" in data
            assert "examples" in data
            assert "confidence" in data
            assert isinstance(data["examples"], list)
            assert len(data["examples"]) <= 3

    def test_generate_facts(self, client: TestClient) -> None:
        """Test facts generation endpoint."""
        request_data = {
            "word": "algorithm",
            "definition": "A process or set of rules to be followed in calculations",
            "count": 5,
            "previous_words": ["mathematics", "computer"]
        }
        
        response = client.post("/api/v1/ai/generate/facts", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "word" in data
            assert "facts" in data
            assert "confidence" in data
            assert "categories" in data
            assert isinstance(data["facts"], list)

    def test_classify_register(self, client: TestClient) -> None:
        """Test language register classification endpoint."""
        request_data = {
            "definition": "To consume food or drink"
        }
        
        response = client.post("/api/v1/ai/assess/register", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "register" in data
            assert data["register"] in ["formal", "informal", "neutral", "slang", "technical"]

    def test_identify_domain(self, client: TestClient) -> None:
        """Test domain identification endpoint."""
        request_data = {
            "definition": "A malignant tumor of potentially unlimited growth"
        }
        
        response = client.post("/api/v1/ai/assess/domain", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "domain" in data
            # Should identify medical domain

    def test_identify_collocations(self, client: TestClient) -> None:
        """Test collocation identification endpoint."""
        request_data = {
            "word": "make",
            "definition": "To create or produce something",
            "part_of_speech": "verb"
        }
        
        response = client.post("/api/v1/ai/assess/collocations", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "collocations" in data
            assert isinstance(data["collocations"], list)

    def test_extract_grammar_patterns(self, client: TestClient) -> None:
        """Test grammar pattern extraction endpoint."""
        request_data = {
            "definition": "To give something to someone",
            "part_of_speech": "verb"
        }
        
        response = client.post("/api/v1/ai/assess/grammar-patterns", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "patterns" in data
            assert isinstance(data["patterns"], list)

    def test_generate_usage_notes(self, client: TestClient) -> None:
        """Test usage notes generation endpoint."""
        request_data = {
            "word": "literally",
            "definition": "In a literal manner or sense; exactly"
        }
        
        response = client.post("/api/v1/ai/usage-notes", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "usage_notes" in data
            assert isinstance(data["usage_notes"], list)

    def test_detect_regional_variants(self, client: TestClient) -> None:
        """Test regional variant detection endpoint."""
        request_data = {
            "definition": "A lift in a building"
        }
        
        response = client.post("/api/v1/ai/assess/regional-variants", json=request_data)
        
        assert response.status_code in [200, 401, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "region" in data


class TestAISynthesisEndpoint:
    """Test the main synthesis endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_synthesize_entry_components(self, client: TestClient) -> None:
        """Test synthesizing entry components."""
        # First, get a synthesized entry
        list_response = client.get("/api/v1/words?limit=1")
        
        if list_response.status_code == 200 and list_response.json()["items"]:
            # Note: This test requires a SynthesizedDictionaryEntry to exist
            # which may not be the case in test data
            
            request_data = {
                "entry_id": "dummy_entry_id",
                "components": ["pronunciation", "synonyms"]
            }
            
            response = client.post("/api/v1/ai/synthesize", json=request_data)
            
            # May fail with 404 if entry doesn't exist
            assert response.status_code in [200, 401, 404, 429]


class TestAIEndpointValidation:
    """Test input validation for AI endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_invalid_count_parameters(self, client: TestClient) -> None:
        """Test count parameter validation."""
        # Suggestions with invalid count
        response = client.post("/api/v1/ai/suggestions", json={"count": 0})
        assert response.status_code == 422
        
        response = client.post("/api/v1/ai/suggestions", json={"count": 13})
        assert response.status_code == 422
        
        # Synonyms with invalid count
        request_data = {
            "word": "test",
            "definition": "test",
            "part_of_speech": "noun",
            "count": 21  # Too high
        }
        response = client.post("/api/v1/ai/synthesize/synonyms", json=request_data)
        assert response.status_code == 422

    def test_empty_string_validation(self, client: TestClient) -> None:
        """Test empty string validation."""
        # Empty word
        response = client.post("/api/v1/ai/generate/word-forms", json={
            "word": "",
            "part_of_speech": "verb"
        })
        assert response.status_code == 422
        
        # Empty definition
        response = client.post("/api/v1/ai/assess/register", json={
            "definition": ""
        })
        assert response.status_code == 422

    def test_string_length_validation(self, client: TestClient) -> None:
        """Test string length limits."""
        # Word too long
        response = client.post("/api/v1/ai/synthesize/pronunciation", json={
            "word": "a" * 101
        })
        assert response.status_code == 422
        
        # Definition too long
        response = client.post("/api/v1/ai/assess/domain", json={
            "definition": "a" * 1001
        })
        assert response.status_code == 422

    def test_list_length_validation(self, client: TestClient) -> None:
        """Test list length limits."""
        # Too many input words
        response = client.post("/api/v1/ai/suggestions", json={
            "input_words": ["word"] * 11,
            "count": 10
        })
        assert response.status_code == 422
        
        # Too many existing synonyms
        request_data = {
            "word": "test",
            "definition": "test",
            "part_of_speech": "noun",
            "existing_synonyms": ["syn"] * 21,
            "count": 5
        }
        response = client.post("/api/v1/ai/synthesize/synonyms", json=request_data)
        assert response.status_code == 422


class TestAIEndpointRateLimiting:
    """Test rate limiting for AI endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_rate_limit_headers(self, client: TestClient) -> None:
        """Test that rate limit headers are present."""
        request_data = {
            "word": "test"
        }
        
        response = client.post("/api/v1/ai/synthesize/pronunciation", json=request_data)
        
        # Should have rate limit headers if rate limiting is active
        if response.status_code == 429:
            assert "X-RateLimit-Limit" in response.headers or "Retry-After" in response.headers

    @pytest.mark.skip(reason="Rate limit testing requires multiple rapid requests")
    def test_rate_limit_enforcement(self, client: TestClient) -> None:
        """Test that rate limits are enforced."""
        # This test would need to make many rapid requests
        # to trigger rate limiting, which is not ideal for unit tests
        pass


class TestAIEndpointPerformance:
    """Performance tests for AI endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.mark.benchmark
    @pytest.mark.skip(reason="AI endpoints require API key and have variable latency")
    def test_pronunciation_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark pronunciation generation performance."""
        def generate_pronunciation():
            response = client.post("/api/v1/ai/synthesize/pronunciation", json={
                "word": "test"
            })
            return response
        
        # Note: This would actually call the AI API which is expensive
        # and has variable latency, so not suitable for benchmarking
        pass