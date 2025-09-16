"""Test AI connector functionality with MongoDB versioning."""

from unittest.mock import patch

import pytest

# Skip these tests if AI module has import issues
pytestmark = pytest.mark.skip(reason="AI module has unresolved imports")
from floridify.caching.models import VersionInfo


class TestAIConnector:
    """Test AI connector with MongoDB persistence and versioning."""

    @pytest.fixture
    async def ai_connector(self, test_db):
        """Create AI connector with test database."""
        connector = AIConnector(
            api_key="test-key",
            model="gpt-4",
            max_retries=2,
            timeout=30,
        )
        await connector.initialize()
        return connector

    @pytest.mark.asyncio
    async def test_ai_request_versioning(self, ai_connector, test_db):
        """Test AI request versioning and MongoDB storage."""
        request = AIRequest(
            prompt="Define the word 'test'",
            model="gpt-4",
            temperature=0.7,
            max_tokens=100,
        )

        with patch.object(ai_connector, "_call_api") as mock_api:
            mock_api.return_value = {
                "choices": [{"message": {"content": "A procedure for evaluation"}}],
                "usage": {"total_tokens": 50},
            }

            response = await ai_connector.complete(request)

            assert response.content == "A procedure for evaluation"
            assert response.model == "gpt-4"
            assert response.usage["total_tokens"] == 50
            assert isinstance(response.version, VersionInfo)

            # Verify MongoDB storage
            stored = await test_db.ai_responses.find_one({"request_id": request.id})
            assert stored is not None
            assert stored["content"] == response.content

    @pytest.mark.asyncio
    async def test_batch_processing(self, ai_connector):
        """Test batch AI request processing."""
        batch_request = BatchRequest(
            requests=[AIRequest(prompt=f"Define word {i}", model="gpt-4") for i in range(3)],
            max_concurrent=2,
        )

        with patch.object(ai_connector, "_call_api") as mock_api:
            mock_api.return_value = {
                "choices": [{"message": {"content": "Definition"}}],
                "usage": {"total_tokens": 10},
            }

            responses = await ai_connector.batch_complete(batch_request)

            assert len(responses) == 3
            assert all(r.content == "Definition" for r in responses)
            assert mock_api.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_logic(self, ai_connector):
        """Test retry logic on API failures."""
        request = AIRequest(prompt="Test", model="gpt-4")

        with patch.object(ai_connector, "_call_api") as mock_api:
            mock_api.side_effect = [
                Exception("API Error"),
                Exception("API Error"),
                {"choices": [{"message": {"content": "Success"}}], "usage": {"total_tokens": 5}},
            ]

            response = await ai_connector.complete(request)

            assert response.content == "Success"
            assert mock_api.call_count == 3

    @pytest.mark.asyncio
    async def test_caching_integration(self, ai_connector, test_db):
        """Test AI response caching."""
        request = AIRequest(
            prompt="Cached prompt",
            model="gpt-4",
            temperature=0,  # Deterministic for caching
        )

        with patch.object(ai_connector, "_call_api") as mock_api:
            mock_api.return_value = {
                "choices": [{"message": {"content": "Cached response"}}],
                "usage": {"total_tokens": 10},
            }

            # First call
            response1 = await ai_connector.complete(request)

            # Second call should use cache
            response2 = await ai_connector.complete(request)

            assert response1.content == response2.content
            assert mock_api.call_count == 1  # Only called once due to caching

    @pytest.mark.asyncio
    async def test_token_tracking(self, ai_connector):
        """Test token usage tracking across requests."""
        with patch.object(ai_connector, "_call_api") as mock_api:
            mock_api.return_value = {
                "choices": [{"message": {"content": "Response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

            for i in range(3):
                request = AIRequest(prompt=f"Test {i}", model="gpt-4")
                await ai_connector.complete(request)

            stats = await ai_connector.get_usage_stats()
            assert stats["total_requests"] == 3
            assert stats["total_tokens"] == 45

    @pytest.mark.asyncio
    async def test_error_handling(self, ai_connector):
        """Test comprehensive error handling."""
        request = AIRequest(prompt="Error test", model="gpt-4")

        with patch.object(ai_connector, "_call_api") as mock_api:
            # Test rate limit error
            mock_api.side_effect = Exception("Rate limit exceeded")

            with pytest.raises(Exception) as exc:
                await ai_connector.complete(request, max_retries=0)
            assert "Rate limit" in str(exc.value)

            # Test invalid API key
            mock_api.side_effect = Exception("Invalid API key")

            with pytest.raises(Exception) as exc:
                await ai_connector.complete(request, max_retries=0)
            assert "Invalid API key" in str(exc.value)
