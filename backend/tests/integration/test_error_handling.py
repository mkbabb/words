"""
Comprehensive error handling and edge case tests for the entire system.
Tests error scenarios, malformed inputs, edge cases, and system resilience.
"""

import asyncio
import io
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


class TestSystemErrorHandling:
    """Test comprehensive error handling across all system components."""

    @pytest.mark.asyncio
    async def test_database_connection_failure(
        self,
        async_client: AsyncClient,
        mocker
    ):
        """Test behavior when database is unavailable."""
        # Mock database connection failure
        mock_client = mocker.patch("motor.motor_asyncio.AsyncIOMotorClient")
        mock_client.return_value.admin.command = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        # Health check should detect database issues
        response = await async_client.get("/health")
        
        # Should return degraded status, not crash
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] in ["degraded", "unhealthy"]
            assert "database" in data
            assert data["database"] != "healthy"

    @pytest.mark.asyncio
    async def test_openai_api_failure_handling(
        self,
        async_client: AsyncClient,
        mocker
    ):
        """Test graceful handling of OpenAI API failures."""
        # Mock OpenAI to fail
        mock_openai = mocker.patch("src.floridify.ai.connector.OpenAIConnector")
        mock_openai.return_value.generate_response = AsyncMock(
            side_effect=Exception("OpenAI API unavailable")
        )
        
        # AI endpoint should handle failure gracefully
        response = await async_client.post(
            "/api/v1/ai/synthesize/pronunciation",
            json={"word": "test"}
        )
        
        # Should return error, not crash
        assert response.status_code in [500, 503]
        error_data = response.json()
        assert "error" in error_data

    @pytest.mark.asyncio
    async def test_malformed_json_requests(self, async_client: AsyncClient):
        """Test handling of malformed JSON requests."""
        # Send invalid JSON
        response = await async_client.request(
            "POST",
            "/api/v1/wordlists",
            content='{"name": invalid json}',
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self, async_client: AsyncClient):
        """Test protection against SQL injection (though using MongoDB)."""
        malicious_inputs = [
            "'; DROP TABLE words; --",
            "1' OR '1'='1",
            "admin'; DROP DATABASE floridify; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            # Test in various endpoints
            response = await async_client.get(f"/api/v1/lookup/{malicious_input}")
            assert response.status_code in [400, 404, 422]
            
            response = await async_client.get(f"/api/v1/search?q={malicious_input}")
            assert response.status_code in [200, 400, 422]  # Search might handle it
            
            response = await async_client.post("/api/v1/wordlists", json={
                "name": malicious_input,
                "description": "test"
            })
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_extremely_long_inputs(self, async_client: AsyncClient):
        """Test handling of extremely long inputs."""
        # Create very long strings
        long_word = "a" * 10000
        long_description = "x" * 100000
        
        # Test word lookup with long word
        response = await async_client.get(f"/api/v1/lookup/{long_word}")
        assert response.status_code in [400, 414, 422]  # Request too long or validation error
        
        # Test wordlist creation with long description
        response = await async_client.post("/api/v1/wordlists", json={
            "name": "Test",
            "description": long_description
        })
        assert response.status_code in [400, 422]
        
        # Test search with long query
        response = await async_client.get(f"/api/v1/search?q={long_word[:500]}")
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_unicode_edge_cases(self, async_client: AsyncClient):
        """Test handling of various Unicode edge cases."""
        unicode_test_cases = [
            "café",  # Normal accented character
            "🙂",    # Emoji
            "日本語", # Japanese characters
            "𝕌𝕟𝕚𝕔𝕠𝕕𝕖", # Mathematical symbols
            "\u0000", # Null character
            "\ufeff", # BOM character
            "test\r\nword", # Line breaks
            "word\ttest", # Tab character
            "word with\xa0spaces", # Non-breaking space
        ]
        
        for test_case in unicode_test_cases:
            try:
                response = await async_client.get(f"/api/v1/lookup/{test_case}")
                # Should either work or return proper error
                assert response.status_code in [200, 400, 404, 422]
                
                if response.status_code == 200:
                    data = response.json()
                    assert "word" in data
            except Exception as e:
                # Should not crash the server
                pytest.fail(f"Server crashed on Unicode input '{test_case}': {e}")

    @pytest.mark.asyncio
    async def test_concurrent_database_operations_conflicts(
        self,
        async_client: AsyncClient,
        wordlist_factory
    ):
        """Test handling of concurrent database operation conflicts."""
        # Create wordlist
        wordlist = await wordlist_factory(name="Concurrent Test")
        
        # Create tasks that might conflict
        tasks = []
        for i in range(10):
            # Concurrent updates to same wordlist
            task = async_client.put(f"/api/v1/wordlists/{wordlist.id}", json={
                "name": f"Updated Name {i}",
                "description": f"Updated description {i}"
            })
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some should succeed, others might conflict
        successful = 0
        conflicts = 0
        
        for response in responses:
            if isinstance(response, Exception):
                continue
            elif response.status_code == 200:
                successful += 1
            elif response.status_code == 409:  # Conflict
                conflicts += 1
        
        # At least one should succeed
        assert successful >= 1

    @pytest.mark.asyncio
    async def test_file_upload_edge_cases(self, async_client: AsyncClient):
        """Test file upload error handling."""
        # Empty file
        empty_file = io.BytesIO(b"")
        files = {"file": ("empty.txt", empty_file, "text/plain")}
        
        response = await async_client.post(
            "/api/v1/wordlists/upload",
            files=files,
            data={"name": "Empty File Test"}
        )
        assert response.status_code in [400, 422]
        
        # Binary file (not text)
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"  # PNG header
        binary_file = io.BytesIO(binary_data)
        files = {"file": ("image.png", binary_file, "image/png")}
        
        response = await async_client.post(
            "/api/v1/wordlists/upload",
            files=files,
            data={"name": "Binary File Test"}
        )
        assert response.status_code in [400, 422]
        
        # File with invalid encoding
        invalid_file = io.BytesIO(b"\xff\xfe\x00\x00invalid")
        files = {"file": ("invalid.txt", invalid_file, "text/plain")}
        
        response = await async_client.post(
            "/api/v1/wordlists/upload",
            files=files,
            data={"name": "Invalid Encoding Test"}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_rate_limiting_edge_cases(
        self,
        async_client: AsyncClient,
        mock_openai_client
    ):
        """Test rate limiting behavior under various scenarios."""
        # Rapid fire requests to AI endpoint
        tasks = []
        for i in range(50):
            task = async_client.post(
                "/api/v1/ai/synthesize/pronunciation",
                json={"word": f"test{i}"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count different response types
        success_count = 0
        rate_limited_count = 0
        error_count = 0
        
        for response in responses:
            if isinstance(response, Exception):
                error_count += 1
            elif response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_count += 1
            else:
                error_count += 1
        
        # System should handle the load gracefully
        total_handled = success_count + rate_limited_count
        assert total_handled >= 40  # Most requests should be handled properly

    @pytest.mark.asyncio
    async def test_memory_exhaustion_protection(
        self,
        async_client: AsyncClient
    ):
        """Test protection against memory exhaustion attacks."""
        # Try to create extremely large corpus
        huge_word_list = [f"word{i}" for i in range(10000)]  # Large but reasonable
        
        response = await async_client.post("/api/v1/corpus", json={
            "words": huge_word_list,
            "name": "Memory Test"
        })
        
        # Should either succeed or reject gracefully
        assert response.status_code in [200, 201, 400, 413, 422]
        
        if response.status_code in [400, 413, 422]:
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data

    @pytest.mark.asyncio
    async def test_circular_dependency_protection(
        self,
        async_client: AsyncClient,
        word_factory
    ):
        """Test protection against circular dependencies in data."""
        # Create words that might reference each other
        word1 = await word_factory(text="circular1")
        word2 = await word_factory(text="circular2")
        
        # Try to create circular relationship (if supported)
        # This is more about ensuring the system doesn't crash
        try:
            from src.floridify.models.models import WordRelationship
            
            rel1 = await WordRelationship(
                from_word_id=word1.id,
                to_word_id=word2.id,
                relationship_type="synonym"
            ).create()
            
            rel2 = await WordRelationship(
                from_word_id=word2.id,
                to_word_id=word1.id,
                relationship_type="synonym"
            ).create()
            
            # System should handle this gracefully
            assert rel1.id is not None
            assert rel2.id is not None
            
        except Exception as e:
            # If not supported, should fail gracefully
            assert "circular" in str(e).lower() or "recursive" in str(e).lower()

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        async_client: AsyncClient,
        mocker
    ):
        """Test handling of operation timeouts."""
        # Mock slow OpenAI response
        mock_openai = mocker.patch("src.floridify.ai.connector.OpenAIConnector")
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)  # Very slow response
            return {"content": "slow response"}
        
        mock_openai.return_value.generate_response = slow_response
        
        # Request should timeout or complete within reasonable time
        start_time = asyncio.get_event_loop().time()
        
        response = await async_client.post(
            "/api/v1/ai/synthesize/pronunciation",
            json={"word": "timeout_test"}
        )
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Should not hang indefinitely
        assert duration < 30  # 30 second maximum
        
        # Should return appropriate error code
        assert response.status_code in [200, 408, 500, 503]

    @pytest.mark.asyncio
    async def test_invalid_object_id_handling(self, async_client: AsyncClient):
        """Test handling of invalid MongoDB ObjectIds."""
        invalid_ids = [
            "not_an_object_id",
            "123",
            "000000000000000000000000",  # Valid format but might not exist
            "ffffffffffffffffffffffff",  # Valid format but unlikely to exist
            "null",
            "",
            "../admin"
        ]
        
        for invalid_id in invalid_ids:
            # Test wordlist retrieval
            response = await async_client.get(f"/api/v1/wordlists/{invalid_id}")
            assert response.status_code in [400, 404, 422]
            
            # Test wordlist update
            response = await async_client.put(f"/api/v1/wordlists/{invalid_id}", json={
                "name": "Test Update"
            })
            assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_content_type_handling(self, async_client: AsyncClient):
        """Test handling of various content types."""
        # Missing content type
        response = await async_client.request(
            "POST",
            "/api/v1/wordlists",
            content='{"name": "Test"}',
            headers={}  # No content-type header
        )
        # FastAPI might auto-detect or require explicit content-type
        assert response.status_code in [200, 201, 400, 415, 422]
        
        # Wrong content type
        response = await async_client.request(
            "POST",
            "/api/v1/wordlists",
            content='{"name": "Test"}',
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code in [400, 415, 422]
        
        # Multiple content types
        response = await async_client.request(
            "POST",
            "/api/v1/wordlists",
            content='{"name": "Test"}',
            headers={"Content-Type": "application/json, text/plain"}
        )
        assert response.status_code in [200, 201, 400, 415, 422]

    @pytest.mark.asyncio
    async def test_http_method_edge_cases(self, async_client: AsyncClient):
        """Test handling of unsupported HTTP methods."""
        # PATCH where not supported
        response = await async_client.request("PATCH", "/api/v1/health")
        assert response.status_code == 405  # Method Not Allowed
        
        # OPTIONS should be handled by CORS
        response = await async_client.request("OPTIONS", "/api/v1/wordlists")
        assert response.status_code in [200, 204, 405]
        
        # HEAD should work for GET endpoints
        response = await async_client.request("HEAD", "/api/v1/health")
        assert response.status_code in [200, 405]

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(
        self,
        async_client: AsyncClient,
        wordlist_factory
    ):
        """Test handling of concurrent user sessions."""
        # Create wordlist
        wordlist = await wordlist_factory(name="Session Test")
        
        # Simulate multiple concurrent sessions
        session_tasks = []
        for session_id in range(5):
            # Each "session" performs multiple operations
            async def session_operations(session_id):
                results = []
                # Get wordlist
                response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")
                results.append(response.status_code)
                
                # Add words
                response = await async_client.post(
                    f"/api/v1/wordlists/{wordlist.id}/words",
                    json={"words": [f"session{session_id}_word"]}
                )
                results.append(response.status_code)
                
                # Search words
                response = await async_client.get(
                    f"/api/v1/wordlists/{wordlist.id}/words/search?query=session{session_id}"
                )
                results.append(response.status_code)
                
                return results
            
            session_tasks.append(session_operations(session_id))
        
        results = await asyncio.gather(*session_tasks, return_exceptions=True)
        
        # All sessions should complete successfully
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Session failed with exception: {result}")
            else:
                # Most operations should succeed
                success_count = result.count(200) + result.count(201)
                assert success_count >= 2  # At least 2 of 3 operations succeed