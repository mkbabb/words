"""
Comprehensive tests for the wordlist pipeline REST API endpoints.
Tests CRUD operations, file upload, spaced repetition, learning analytics, and search.
"""

import asyncio
import io

import pytest
from ..conftest import assert_response_structure, assert_valid_object_id
from httpx import AsyncClient

from floridify.wordlist.models import WordList


class TestWordlistPipelineAPI:
    """Test wordlist pipeline with comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_create_wordlist_basic(self, async_client: AsyncClient):
        """Test basic wordlist creation."""
        wordlist_data = {
            "name": "Test Wordlist",
            "description": "A test wordlist for unit testing",
            "is_public": False,
            "tags": ["test", "example"],
            "words": ["hello", "world", "test"],
        }

        response = await async_client.post("/api/v1/wordlists", json=wordlist_data)

        assert response.status_code == 201
        data = response.json()

        # Validate response structure
        required_fields = ["id", "name", "description", "total_words", "unique_words"]
        assert_response_structure(data, required_fields)

        # Validate content
        assert data["name"] == "Test Wordlist"
        assert data["description"] == "A test wordlist for unit testing"
        assert data["total_words"] == 3
        assert data["unique_words"] == 3
        assert data["is_public"] is False
        assert set(data["tags"]) == {"test", "example"}
        assert_valid_object_id(data["id"])

    @pytest.mark.asyncio
    async def test_create_wordlist_validation(self, async_client: AsyncClient):
        """Test wordlist creation input validation."""
        # Empty name
        response = await async_client.post(
            "/api/v1/wordlists", json={"name": "", "description": "Test"}
        )
        assert response.status_code in [400, 422]

        # Name too long
        response = await async_client.post(
            "/api/v1/wordlists",
            json={
                "name": "x" * 201,  # Over limit
                "description": "Test",
            },
        )
        assert response.status_code in [400, 422]

        # Description too long
        response = await async_client.post(
            "/api/v1/wordlists",
            json={
                "name": "Test",
                "description": "x" * 1001,  # Over limit
            },
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_list_wordlists_with_filtering(self, async_client: AsyncClient, wordlist_factory):
        """Test listing wordlists with various filters."""
        # Create test wordlists
        await wordlist_factory(name="Public List", is_public=True, tags=["public"])
        await wordlist_factory(name="Private List", is_public=False, tags=["private"])
        await wordlist_factory(name="Tagged List", tags=["special", "tagged"])

        # Test basic listing
        response = await async_client.get("/api/v1/wordlists")
        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data
        assert len(data["items"]) >= 3

        # Test public filter
        response = await async_client.get("/api/v1/wordlists?is_public=true")
        assert response.status_code == 200
        data = response.json()

        public_lists = [item for item in data["items"] if item["is_public"]]
        assert len(public_lists) >= 1

        # Test tag filter
        response = await async_client.get("/api/v1/wordlists?has_tag=special")
        assert response.status_code == 200
        data = response.json()

        tagged_lists = [item for item in data["items"] if "special" in item["tags"]]
        assert len(tagged_lists) >= 1

    @pytest.mark.asyncio
    async def test_get_wordlist_details(self, async_client: AsyncClient, wordlist_factory):
        """Test retrieving detailed wordlist information."""
        # Create test wordlist
        wordlist = await wordlist_factory(
            name="Detailed List", description="Test description", words=["word1", "word2", "word3"]
        )

        response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")

        assert response.status_code == 200
        data = response.json()

        # Validate comprehensive response
        required_fields = ["id", "name", "description", "words", "total_words", "learning_stats"]
        assert_response_structure(data, required_fields)

        assert data["name"] == "Detailed List"
        assert data["total_words"] == 3
        assert len(data["words"]) == 3

        # Verify words have learning metadata
        for word in data["words"]:
            assert "word" in word
            assert "mastery_level" in word
            assert "added_at" in word

    @pytest.mark.asyncio
    async def test_update_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test updating wordlist metadata."""
        # Create test wordlist
        wordlist = await wordlist_factory(name="Original Name")

        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "tags": ["updated", "modified"],
        }

        response = await async_client.put(f"/api/v1/wordlists/{wordlist.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert set(data["tags"]) == {"updated", "modified"}

    @pytest.mark.asyncio
    async def test_delete_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test deleting a wordlist."""
        # Create test wordlist
        wordlist = await wordlist_factory(name="To Delete")

        response = await async_client.delete(f"/api/v1/wordlists/{wordlist.id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_wordlist_file(self, async_client: AsyncClient):
        """Test uploading wordlist from file."""
        # Create test file content
        file_content = "apple\nbanana\ncherry\ndate\n"
        file_data = io.BytesIO(file_content.encode())

        # Upload file
        files = {"file": ("wordlist.txt", file_data, "text/plain")}
        data = {"name": "Uploaded List", "description": "Uploaded from file", "is_public": "false"}

        response = await async_client.post("/api/v1/wordlists/upload", files=files, data=data)

        assert response.status_code == 201
        result = response.json()

        assert result["name"] == "Uploaded List"
        assert result["total_words"] == 4
        assert result["unique_words"] == 4

    @pytest.mark.asyncio
    async def test_upload_wordlist_streaming(self, async_client: AsyncClient):
        """Test streaming wordlist upload with progress."""
        # Create larger file for streaming test
        words = [f"word{i}" for i in range(100)]
        file_content = "\n".join(words)
        file_data = io.BytesIO(file_content.encode())

        files = {"file": ("large_wordlist.txt", file_data, "text/plain")}
        data = {"name": "Streaming Upload"}

        response = await async_client.post(
            "/api/v1/wordlists/upload/stream",
            files=files,
            data=data,
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 201
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Should contain progress events
        assert "data:" in response.text
        assert "progress" in response.text or "complete" in response.text

    @pytest.mark.asyncio
    async def test_add_words_to_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test adding words to existing wordlist."""
        # Create test wordlist
        wordlist = await wordlist_factory(words=["initial", "words"])

        add_data = {"words": ["new", "additional", "words"], "notes": "Added via API"}

        response = await async_client.post(f"/api/v1/wordlists/{wordlist.id}/words", json=add_data)

        assert response.status_code == 201
        data = response.json()

        # Total should be updated
        assert data["total_words"] == 5  # 2 initial + 3 new

        # Verify words were added
        get_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/words")
        words_data = get_response.json()

        word_texts = [w["word"] for w in words_data["items"]]
        assert "new" in word_texts
        assert "additional" in word_texts

    @pytest.mark.asyncio
    async def test_remove_word_from_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test removing word from wordlist."""
        # Create test wordlist
        wordlist = await wordlist_factory(words=["keep", "remove", "stay"])

        response = await async_client.delete(f"/api/v1/wordlists/{wordlist.id}/words/remove")

        assert response.status_code == 204

        # Verify word was removed
        get_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/words")
        words_data = get_response.json()

        word_texts = [w["word"] for w in words_data["items"]]
        assert "remove" not in word_texts
        assert "keep" in word_texts

    @pytest.mark.asyncio
    async def test_search_words_in_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test searching words within a wordlist."""
        # Create wordlist with searchable words
        words = ["testing", "tester", "testify", "example", "sample"]
        wordlist = await wordlist_factory(words=words)

        response = await async_client.get(
            f"/api/v1/wordlists/{wordlist.id}/words/search?query=test&limit=10"
        )

        assert response.status_code == 200
        data = response.json()

        # Should find words containing "test"
        assert len(data["items"]) >= 3
        result_words = [item["word"] for item in data["items"]]
        assert "testing" in result_words
        assert "tester" in result_words
        assert "testify" in result_words

    @pytest.mark.asyncio
    async def test_wordlist_review_system(self, async_client: AsyncClient, wordlist_factory):
        """Test spaced repetition review system."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["review", "study", "learn"])

        # Get words due for review
        response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/review/due")

        assert response.status_code == 200
        data = response.json()

        # All words should be due initially
        assert len(data["items"]) == 3

        # Submit review for one word
        review_data = {"word": "review", "mastery_level": "BRONZE", "quality_score": 0.8}

        review_response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/review", json=review_data
        )

        assert review_response.status_code == 200
        result = review_response.json()

        # Word should have updated mastery level
        assert result["mastery_level"] == "BRONZE"
        assert result["last_reviewed"] is not None

    @pytest.mark.asyncio
    async def test_bulk_word_review(self, async_client: AsyncClient, wordlist_factory):
        """Test bulk review submission."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["bulk1", "bulk2", "bulk3"])

        bulk_review_data = {
            "reviews": [
                {"word": "bulk1", "mastery_level": "BRONZE", "quality_score": 0.7},
                {"word": "bulk2", "mastery_level": "SILVER", "quality_score": 0.9},
                {"word": "bulk3", "mastery_level": "BRONZE", "quality_score": 0.6},
            ]
        }

        response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/review/bulk", json=bulk_review_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_reviewed"] == 3
        assert data["successful"] == 3
        assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_study_session_recording(self, async_client: AsyncClient, wordlist_factory):
        """Test recording study session statistics."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["session1", "session2"])

        session_data = {"duration_minutes": 30, "words_studied": 15, "words_mastered": 5}

        response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/review/study-session", json=session_data
        )

        assert response.status_code == 200
        data = response.json()

        # Should update learning statistics
        assert "learning_stats" in data
        assert data["learning_stats"]["total_study_time_minutes"] >= 30

    @pytest.mark.asyncio
    async def test_wordlist_statistics(self, async_client: AsyncClient, wordlist_factory):
        """Test detailed wordlist statistics."""
        # Create wordlist with various mastery levels
        wordlist = await wordlist_factory(words=["stat1", "stat2", "stat3"])

        response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/stats")

        assert response.status_code == 200
        data = response.json()

        # Should include comprehensive statistics
        required_fields = ["mastery_distribution", "review_stats", "learning_progress"]
        assert_response_structure(data, required_fields)

        # Mastery distribution should show counts by level
        assert "DEFAULT" in data["mastery_distribution"]
        assert isinstance(data["mastery_distribution"]["DEFAULT"], int)

    @pytest.mark.asyncio
    async def test_wordlist_search_by_name(self, async_client: AsyncClient):
        """Test searching wordlists by name."""
        # Create test wordlists with different names
        names = ["Mathematics Vocabulary", "Science Terms", "Math Problems"]
        for name in names:
            await WordList(
                name=name,
                description="Test list",
                hash_id=f"test_{name.lower().replace(' ', '_')}",
                words=[],
                total_words=0,
                unique_words=0,
            ).create()

        response = await async_client.get("/api/v1/wordlists/search/math")

        assert response.status_code == 200
        data = response.json()

        # Should find lists with "math" in name
        assert len(data["items"]) >= 2
        result_names = [item["name"] for item in data["items"]]
        assert "Mathematics Vocabulary" in result_names
        assert "Math Problems" in result_names

    @pytest.mark.asyncio
    async def test_wordlist_file_format_support(self, async_client: AsyncClient):
        """Test support for different file formats."""
        # Test CSV format
        csv_content = "word,definition\napple,red fruit\nbanana,yellow fruit"
        csv_data = io.BytesIO(csv_content.encode())

        files = {"file": ("wordlist.csv", csv_data, "text/csv")}
        data = {"name": "CSV Upload"}

        response = await async_client.post("/api/v1/wordlists/upload", files=files, data=data)

        assert response.status_code == 201
        result = response.json()
        assert result["total_words"] == 2

    @pytest.mark.asyncio
    async def test_wordlist_performance_large_list(
        self, async_client: AsyncClient, performance_thresholds, benchmark
    ):
        """Test performance with large wordlist operations."""
        # Create large wordlist
        large_words = [f"word{i}" for i in range(1000)]
        wordlist_data = {"name": "Large Performance Test", "words": large_words}

        async def create_large_wordlist():
            response = await async_client.post("/api/v1/wordlists", json=wordlist_data)
            assert response.status_code == 201
            return response.json()

        # Benchmark creation
        await benchmark.pedantic(create_large_wordlist, iterations=1, rounds=1)

        # Should complete within reasonable time
        assert benchmark.stats.stats.mean < performance_thresholds["wordlist_upload"]

    @pytest.mark.asyncio
    async def test_wordlist_concurrent_operations(
        self, async_client: AsyncClient, wordlist_factory
    ):
        """Test concurrent wordlist operations."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["concurrent", "test"])

        # Perform concurrent operations
        tasks = [
            async_client.get(f"/api/v1/wordlists/{wordlist.id}"),
            async_client.get(f"/api/v1/wordlists/{wordlist.id}/words"),
            async_client.get(f"/api/v1/wordlists/{wordlist.id}/stats"),
            async_client.post(f"/api/v1/wordlists/{wordlist.id}/words", json={"words": ["new"]}),
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Most operations should succeed (some may have conflicts)
        successful = [r for r in responses if not isinstance(r, Exception) and r.status_code < 400]
        assert len(successful) >= 3

    @pytest.mark.asyncio
    async def test_wordlist_spaced_repetition_algorithm(
        self, async_client: AsyncClient, wordlist_factory
    ):
        """Test spaced repetition algorithm (SM-2) implementation."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["algorithm", "test"])

        # Review word multiple times with different quality scores
        reviews = [
            {"word": "algorithm", "mastery_level": "BRONZE", "quality_score": 0.9},
            {"word": "algorithm", "mastery_level": "SILVER", "quality_score": 0.8},
            {"word": "algorithm", "mastery_level": "GOLD", "quality_score": 0.95},
        ]

        for review_data in reviews:
            response = await async_client.post(
                f"/api/v1/wordlists/{wordlist.id}/review", json=review_data
            )
            assert response.status_code == 200

        # Get updated word info
        words_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/words")
        words_data = words_response.json()

        algorithm_word = next(w for w in words_data["items"] if w["word"] == "algorithm")

        # Should have progressed through mastery levels
        assert algorithm_word["mastery_level"] == "GOLD"
        assert algorithm_word["review_count"] == 3
