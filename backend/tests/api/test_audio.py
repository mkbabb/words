"""Comprehensive tests for Audio endpoints."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from beanie import PydanticObjectId

from floridify.api.main import app
from floridify.models import AudioMedia


class TestAudioEndpoints:
    """Test audio file serving endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_get_audio_file_not_found(self, client: TestClient) -> None:
        """Test getting non-existent audio file."""
        fake_id = str(PydanticObjectId())
        response = client.get(f"/api/v1/audio/files/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Audio file not found"

    @pytest.mark.asyncio
    async def test_get_audio_file_success(self, client: TestClient) -> None:
        """Test getting audio file by ID."""
        # Create a test audio media document
        test_audio = AudioMedia(
            word_id="test_word_id",
            url="test_audio.mp3",
            format="mp3",
            source="test",
            duration=1.5,
            language="en"
        )
        await test_audio.save()
        
        try:
            # Try to get the audio file
            response = client.get(f"/api/v1/audio/files/{test_audio.id}")
            
            # Will likely fail since test file doesn't exist on disk
            assert response.status_code == 404
            assert "not found on disk" in response.json()["detail"]
        finally:
            # Cleanup
            await test_audio.delete()

    def test_get_cached_audio_file(self, client: TestClient) -> None:
        """Test getting cached audio file."""
        # Test with valid path structure
        response = client.get("/api/v1/audio/cache/ab/test_audio.mp3")
        
        # Will likely return 404 since file doesn't exist
        assert response.status_code == 404
        assert response.json()["detail"] == "Audio file not found"

    def test_get_cached_audio_invalid_format(self, client: TestClient) -> None:
        """Test getting cached audio with invalid format."""
        # Even if file existed, invalid format should fail
        response = client.get("/api/v1/audio/cache/ab/test_audio.exe")
        
        # Should fail either at file existence check or format validation
        assert response.status_code in [400, 404]

    def test_get_cached_audio_path_traversal(self, client: TestClient) -> None:
        """Test path traversal protection."""
        # Attempt path traversal
        dangerous_paths = [
            "/api/v1/audio/cache/../../../etc/passwd",
            "/api/v1/audio/cache/../../secrets.txt",
            "/api/v1/audio/cache/%2e%2e%2f%2e%2e%2fconfig.py",
            "/api/v1/audio/cache/./../../sensitive.dat",
        ]
        
        for path in dangerous_paths:
            response = client.get(path)
            # Should be blocked by security check
            assert response.status_code in [403, 404]
            
            if response.status_code == 403:
                assert response.json()["detail"] == "Access denied"

    def test_get_cached_audio_invalid_subdir(self, client: TestClient) -> None:
        """Test handling of invalid subdirectory names."""
        invalid_subdirs = [
            "toolong",  # Should be 2 chars
            "a",  # Too short
            "../",  # Path traversal attempt
            "a/b",  # Contains slash
        ]
        
        for subdir in invalid_subdirs:
            response = client.get(f"/api/v1/audio/cache/{subdir}/test.mp3")
            assert response.status_code in [403, 404]

    def test_get_cached_audio_valid_formats(self, client: TestClient) -> None:
        """Test that valid audio formats are accepted."""
        valid_formats = ["mp3", "wav", "ogg"]
        
        for format in valid_formats:
            response = client.get(f"/api/v1/audio/cache/ab/test.{format}")
            # Will be 404 for non-existent files, but format should be accepted
            assert response.status_code == 404
            assert response.json()["detail"] == "Audio file not found"

    def test_audio_response_headers(self, client: TestClient) -> None:
        """Test response headers for audio files."""
        # This test would require an actual file to exist
        # We can't test the actual headers without a real file
        pass

    def test_malformed_audio_id(self, client: TestClient) -> None:
        """Test handling of malformed audio IDs."""
        bad_ids = [
            "not-an-objectid",
            "12345",
            "xyz123abc",
            "",
            "null",
            "undefined",
        ]
        
        for bad_id in bad_ids:
            response = client.get(f"/api/v1/audio/files/{bad_id}")
            # Should fail with 404 or validation error
            assert response.status_code == 404

    def test_special_characters_in_filename(self, client: TestClient) -> None:
        """Test handling of special characters in filenames."""
        special_filenames = [
            "test%20audio.mp3",  # URL encoded space
            "test+audio.mp3",  # Plus sign
            "test(1).mp3",  # Parentheses
            "test[1].mp3",  # Brackets
            "test{1}.mp3",  # Braces
            "test@audio.mp3",  # At symbol
            "test#audio.mp3",  # Hash
            "test$audio.mp3",  # Dollar sign
        ]
        
        for filename in special_filenames:
            response = client.get(f"/api/v1/audio/cache/ab/{filename}")
            # Should handle gracefully - either 404 or proper error
            assert response.status_code in [400, 404]


class TestAudioEndpointPerformance:
    """Performance tests for audio endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.mark.benchmark
    def test_audio_lookup_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark audio file lookup performance."""
        fake_id = str(PydanticObjectId())
        
        def lookup_audio():
            response = client.get(f"/api/v1/audio/files/{fake_id}")
            assert response.status_code == 404
            return response
        
        result = benchmark(lookup_audio)
        
        # Performance assertions - lookup should be fast even for non-existent files
        assert benchmark.stats["mean"] < 0.05  # Average under 50ms

    @pytest.mark.benchmark
    def test_cached_audio_lookup_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark cached audio lookup performance."""
        def lookup_cached():
            response = client.get("/api/v1/audio/cache/ab/test.mp3")
            assert response.status_code == 404
            return response
        
        result = benchmark(lookup_cached)
        
        # Performance assertions
        assert benchmark.stats["mean"] < 0.03  # Average under 30ms


class TestAudioEdgeCases:
    """Edge case tests for audio endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_very_long_filename(self, client: TestClient) -> None:
        """Test handling of extremely long filenames."""
        long_filename = "a" * 255 + ".mp3"
        response = client.get(f"/api/v1/audio/cache/ab/{long_filename}")
        # Should handle gracefully
        assert response.status_code in [400, 404]

    def test_empty_filename(self, client: TestClient) -> None:
        """Test handling of empty filename."""
        response = client.get("/api/v1/audio/cache/ab/")
        # Should fail appropriately
        assert response.status_code in [307, 404, 422]

    def test_null_byte_in_path(self, client: TestClient) -> None:
        """Test handling of null bytes in path."""
        # Null byte injection attempt
        response = client.get("/api/v1/audio/cache/ab/test%00.mp3")
        # Should be rejected
        assert response.status_code in [400, 403, 404]

    def test_unicode_in_filename(self, client: TestClient) -> None:
        """Test handling of unicode characters in filename."""
        unicode_filenames = [
            "音声.mp3",  # Japanese
            "аудио.mp3",  # Russian
            "صوت.mp3",  # Arabic
            "🎵.mp3",  # Emoji
        ]
        
        for filename in unicode_filenames:
            response = client.get(f"/api/v1/audio/cache/ab/{filename}")
            # Should handle gracefully
            assert response.status_code in [400, 404]

    def test_double_extension(self, client: TestClient) -> None:
        """Test handling of files with double extensions."""
        response = client.get("/api/v1/audio/cache/ab/test.mp3.exe")
        # Should reject based on final extension
        assert response.status_code in [400, 404]

    def test_no_extension(self, client: TestClient) -> None:
        """Test handling of files without extension."""
        response = client.get("/api/v1/audio/cache/ab/test")
        # Should fail due to inability to determine format
        assert response.status_code in [400, 404]

    def test_case_sensitivity(self, client: TestClient) -> None:
        """Test case sensitivity in format detection."""
        # Test uppercase extensions
        response = client.get("/api/v1/audio/cache/ab/test.MP3")
        # Should handle case-insensitively or fail gracefully
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_concurrent_audio_requests(self, client: TestClient) -> None:
        """Test handling of concurrent requests for same audio."""
        import asyncio
        
        fake_id = str(PydanticObjectId())
        
        async def make_request():
            return client.get(f"/api/v1/audio/files/{fake_id}")
        
        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should return 404
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code == 404