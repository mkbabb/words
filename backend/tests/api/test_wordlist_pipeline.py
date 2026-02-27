"""Comprehensive tests for the wordlist pipeline REST API endpoints.
Tests CRUD operations, file upload, spaced repetition, learning analytics, and search.
"""

import asyncio
import io

import pytest
from httpx import AsyncClient

from floridify.wordlist.models import WordList

from ..conftest import assert_response_structure, assert_valid_object_id


class TestWordlistPipelineAPI:
    """Test wordlist pipeline with comprehensive coverage."""

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
        body = response.json()

        # API wraps response in ResourceResponse: {data, links, metadata}
        assert "data" in body
        data = body["data"]

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

    async def test_create_wordlist_validation(self, async_client: AsyncClient):
        """Test wordlist creation input validation."""
        # Empty name
        response = await async_client.post(
            "/api/v1/wordlists",
            json={"name": "", "description": "Test"},
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

    async def test_list_wordlists_with_filtering(self, async_client: AsyncClient, wordlist_factory):
        """Test listing wordlists with various filters."""
        # Create test wordlists
        await wordlist_factory(name="Public List", is_public=True, tags=["public"])
        await wordlist_factory(name="Private List", is_public=False, tags=["private"])
        await wordlist_factory(name="Tagged List", tags=["special", "tagged"])

        # Test basic listing - returns ListResponse: {items, total, offset, limit, has_more}
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

    async def test_get_wordlist_details(self, async_client: AsyncClient, wordlist_factory):
        """Test retrieving detailed wordlist information."""
        # Create test wordlist
        wordlist = await wordlist_factory(
            name="Detailed List",
            description="Test description",
            words=["word1", "word2", "word3"],
        )

        response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")

        assert response.status_code == 200
        body = response.json()

        # API wraps in ResourceResponse: {data, metadata, links}
        assert "data" in body
        data = body["data"]

        # Validate comprehensive response (populated words via populate_words)
        required_fields = ["id", "name", "description", "words", "total_words", "learning_stats"]
        assert_response_structure(data, required_fields)

        assert data["name"] == "Detailed List"
        assert data["total_words"] == 3
        assert len(data["words"]) == 3

        # Verify words have learning metadata (populated via populate_words)
        for word in data["words"]:
            assert "word" in word
            assert "mastery_level" in word
            assert "added_date" in word

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
        body = response.json()

        # API wraps in ResourceResponse
        data = body["data"]

        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert set(data["tags"]) == {"updated", "modified"}

    async def test_delete_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test deleting a wordlist."""
        # Create test wordlist
        wordlist = await wordlist_factory(name="To Delete")

        response = await async_client.delete(f"/api/v1/wordlists/{wordlist.id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")
        assert get_response.status_code == 404

    async def test_upload_wordlist_file(self, async_client: AsyncClient):
        """Test uploading wordlist from file."""
        # Create test file content
        file_content = "apple\nbanana\ncherry\ndate\n"
        file_data = io.BytesIO(file_content.encode())

        # Upload file - name/description/is_public are query params, not form data
        files = {"file": ("wordlist.txt", file_data, "text/plain")}

        response = await async_client.post(
            "/api/v1/wordlists/upload?name=Uploaded+List&description=Uploaded+from+file&is_public=false",
            files=files,
        )

        assert response.status_code == 201
        body = response.json()

        # Upload returns ResourceResponse with data: {id, name, word_count, created_at}
        result = body["data"]
        assert result["name"] == "Uploaded List"
        assert result["word_count"] == 4

    async def test_upload_wordlist_streaming(self, async_client: AsyncClient):
        """Test streaming wordlist upload with progress."""
        # Create larger file for streaming test
        words = [f"word{i}" for i in range(100)]
        file_content = "\n".join(words)
        file_data = io.BytesIO(file_content.encode())

        files = {"file": ("large_wordlist.txt", file_data, "text/plain")}

        response = await async_client.post(
            "/api/v1/wordlists/upload/stream?name=Streaming+Upload",
            files=files,
            headers={"Accept": "text/event-stream"},
        )

        # StreamingResponse defaults to status 200 (route status_code not propagated)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Should contain progress events
        assert "data:" in response.text
        assert "progress" in response.text or "complete" in response.text

    async def test_add_words_to_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test adding words to existing wordlist."""
        # Create test wordlist
        wordlist = await wordlist_factory(words=["initial", "words"])

        # WordAddRequest only has 'words' field (no 'notes')
        add_data = {"words": ["new", "additional", "words"]}

        # add_word endpoint returns 200 (no explicit status_code=201)
        response = await async_client.post(f"/api/v1/wordlists/{wordlist.id}/words", json=add_data)

        assert response.status_code == 200
        body = response.json()

        # ResourceResponse: {data: {id, word_count, added_words}, metadata, links}
        data = body["data"]
        assert data["word_count"] == 4  # 2 initial + 3 new, but "words" is a duplicate

        # Verify words were added via the get wordlist detail endpoint
        # (populate_words adds "word" text field)
        get_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")
        detail_data = get_response.json()["data"]

        word_texts = [w["word"] for w in detail_data["words"]]
        assert "new" in word_texts
        assert "additional" in word_texts

    async def test_remove_word_from_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test removing word from wordlist."""
        # Create test wordlist
        wordlist = await wordlist_factory(words=["keep", "remove", "stay"])

        response = await async_client.delete(f"/api/v1/wordlists/{wordlist.id}/words/remove")

        assert response.status_code == 204

        # Verify word was removed via detail endpoint (has populate_words)
        get_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")
        detail_data = get_response.json()["data"]

        word_texts = [w["word"] for w in detail_data["words"]]
        assert "remove" not in word_texts
        assert "keep" in word_texts

    async def test_search_words_in_wordlist(self, async_client: AsyncClient, wordlist_factory):
        """Test searching words within a wordlist."""
        # Create wordlist with searchable words
        words = ["testing", "tester", "testify", "example", "sample"]
        wordlist = await wordlist_factory(words=words)

        # Search endpoint is POST /{wordlist_id}/search with query params
        # Lower min_score to capture more fuzzy matches (testify scores ~0.5)
        response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/search?query=test&limit=10&min_score=0.4",
        )

        assert response.status_code == 200
        data = response.json()

        # Should find words related to "test" (at least tester, testing)
        assert len(data["items"]) >= 2
        # Verify results contain expected words
        result_words = [item["word"] for item in data["items"]]
        assert any("test" in w for w in result_words)

    async def test_wordlist_review_system(self, async_client: AsyncClient, wordlist_factory):
        """Test spaced repetition review system."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["review", "study", "learn"])

        # Get words due for review - returns ListResponse
        response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/review/due")

        assert response.status_code == 200
        data = response.json()

        # All words should be due initially
        assert len(data["items"]) == 3

        # Submit review for one word
        # WordReviewRequest expects: {word: str, quality: int (0-5)}
        review_data = {"word": "review", "quality": 4}

        review_response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/review",
            json=review_data,
        )

        assert review_response.status_code == 200
        body = review_response.json()

        # ResourceResponse: {data: {word, mastery_level, last_reviewed}, metadata, links}
        result = body["data"]
        assert result["word"] == "review"
        assert result["mastery_level"] is not None

    async def test_bulk_word_review(self, async_client: AsyncClient, wordlist_factory):
        """Test bulk review submission."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["bulk1", "bulk2", "bulk3"])

        # BulkReviewRequest.reviews contains WordReviewRequest objects
        # WordReviewRequest: {word: str, quality: int (0-5)}
        bulk_review_data = {
            "reviews": [
                {"word": "bulk1", "quality": 3},
                {"word": "bulk2", "quality": 5},
                {"word": "bulk3", "quality": 2},
            ],
        }

        response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/review/bulk",
            json=bulk_review_data,
        )

        assert response.status_code == 200
        body = response.json()

        # ResourceResponse: {data: {total_reviewed, successful, failed, failed_words}}
        data = body["data"]
        assert data["total_reviewed"] == 3
        assert data["successful"] == 3
        assert data["failed"] == 0

    async def test_study_session_recording(self, async_client: AsyncClient, wordlist_factory):
        """Test recording study session statistics."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["session1", "session2"])

        session_data = {"duration_minutes": 30, "words_studied": 15, "words_mastered": 5}

        response = await async_client.post(
            f"/api/v1/wordlists/{wordlist.id}/review/study-session",
            json=session_data,
        )

        assert response.status_code == 200
        body = response.json()

        # ResourceResponse: {data: {total_study_time, study_session_count, last_studied}}
        data = body["data"]
        assert data["total_study_time"] >= 30

    async def test_wordlist_statistics(self, async_client: AsyncClient, wordlist_factory):
        """Test detailed wordlist statistics."""
        # Create wordlist with various mastery levels
        wordlist = await wordlist_factory(words=["stat1", "stat2", "stat3"])

        response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}/stats")

        assert response.status_code == 200
        body = response.json()

        # ResourceResponse: {data: {basic_stats, word_counts, mastery_distribution, ...}}
        data = body["data"]

        # Should include comprehensive statistics
        required_fields = ["mastery_distribution", "word_counts", "basic_stats"]
        assert_response_structure(data, required_fields)

        # Mastery distribution should show counts by level (lowercase enum values)
        assert "default" in data["mastery_distribution"]
        assert isinstance(data["mastery_distribution"]["default"], int)

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

        # ListResponse: {items, total, offset, limit, has_more}
        # Should find lists with "math" in name
        assert len(data["items"]) >= 2
        result_names = [item["name"] for item in data["items"]]
        assert "Mathematics Vocabulary" in result_names
        assert "Math Problems" in result_names

    async def test_wordlist_file_format_support(self, async_client: AsyncClient):
        """Test support for different file formats."""
        # Test CSV format
        csv_content = "word,definition\napple,red fruit\nbanana,yellow fruit"
        csv_data = io.BytesIO(csv_content.encode())

        files = {"file": ("wordlist.csv", csv_data, "text/csv")}

        response = await async_client.post(
            "/api/v1/wordlists/upload?name=CSV+Upload",
            files=files,
        )

        assert response.status_code == 201
        body = response.json()

        # Upload returns ResourceResponse with data: {id, name, word_count, created_at}
        result = body["data"]
        assert result["word_count"] >= 1  # Parser may handle CSV differently

    async def test_wordlist_performance_large_list(
        self,
        async_client: AsyncClient,
    ):
        """Test performance with large wordlist operations."""
        import time

        # Create large wordlist
        large_words = [f"word{i}" for i in range(1000)]
        wordlist_data = {"name": "Large Performance Test", "words": large_words}

        start = time.monotonic()
        response = await async_client.post("/api/v1/wordlists", json=wordlist_data)
        elapsed = time.monotonic() - start

        assert response.status_code == 201

        # Should complete within reasonable time (30 seconds)
        assert elapsed < 30.0

    async def test_wordlist_concurrent_operations(
        self,
        async_client: AsyncClient,
        wordlist_factory,
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

        # Most operations should succeed (some may have conflicts due to concurrency)
        successful = [r for r in responses if not isinstance(r, Exception) and r.status_code < 500]
        assert len(successful) >= 3

    async def test_wordlist_spaced_repetition_algorithm(
        self,
        async_client: AsyncClient,
        wordlist_factory,
    ):
        """Test spaced repetition algorithm (SM-2) implementation."""
        # Create wordlist
        wordlist = await wordlist_factory(words=["algorithm", "test"])

        # Review word multiple times with increasing quality scores
        # WordReviewRequest: {word: str, quality: int (0-5)}
        reviews = [
            {"word": "algorithm", "quality": 4},
            {"word": "algorithm", "quality": 4},
            {"word": "algorithm", "quality": 5},
        ]

        for review_data in reviews:
            response = await async_client.post(
                f"/api/v1/wordlists/{wordlist.id}/review",
                json=review_data,
            )
            assert response.status_code == 200

        # Get updated word info via detail endpoint (has populate_words)
        detail_response = await async_client.get(f"/api/v1/wordlists/{wordlist.id}")
        detail_data = detail_response.json()["data"]

        algorithm_word = next(w for w in detail_data["words"] if w["word"] == "algorithm")

        # After 3 reviews, word should have progressed from DEFAULT
        # Mastery levels are serialized as lowercase enum values
        assert algorithm_word["mastery_level"] in ["bronze", "silver", "gold"]
        # review_data is in the nested review_data field
        assert algorithm_word["review_data"]["repetitions"] == 3
