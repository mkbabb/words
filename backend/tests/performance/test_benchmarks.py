"""
Comprehensive performance benchmarking tests for all major system components.
Uses pytest-benchmark for accurate performance measurement and regression detection.
"""

import asyncio
import io

import pytest
from httpx import AsyncClient

from tests.conftest import assert_valid_object_id


class TestPerformanceBenchmarks:
    """Comprehensive performance benchmarks for all system components."""

    @pytest.mark.asyncio
    async def test_lookup_simple_performance(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        benchmark,
        performance_thresholds
    ):
        """Benchmark simple word lookup performance."""
        # Setup test data
        word = await word_factory(text="benchmark", language="en")
        await definition_factory(word_instance=word)
        
        async def lookup_operation():
            response = await async_client.get("/api/v1/lookup/benchmark")
            assert response.status_code == 200
            data = response.json()
            assert data["word"] == "benchmark"
            return data
        
        await benchmark.pedantic(lookup_operation, iterations=10, rounds=5)
        
        # Performance assertion
        mean_time = benchmark.stats.stats.mean
        assert mean_time < performance_thresholds["lookup_simple"]
        
        # Memory efficiency check
        assert benchmark.stats.stats.stddev < mean_time * 0.2  # Low variance

    @pytest.mark.asyncio
    async def test_lookup_complex_with_ai_performance(
        self,
        async_client: AsyncClient,
        mock_openai_client,
        benchmark,
        performance_thresholds
    ):
        """Benchmark complex lookup with AI synthesis."""
        async def complex_lookup_operation():
            response = await async_client.get("/api/v1/lookup/complexword")
            assert response.status_code == 200
            data = response.json()
            # Should have AI-synthesized content
            assert "definitions" in data
            return data
        
        await benchmark.pedantic(complex_lookup_operation, iterations=5, rounds=3)
        
        # Performance assertion for complex operations
        assert benchmark.stats.stats.mean < performance_thresholds["lookup_complex"]

    @pytest.mark.asyncio
    async def test_search_performance_scaling(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        benchmark,
        performance_thresholds
    ):
        """Benchmark search performance with increasing dataset size."""
        # Create datasets of different sizes
        dataset_sizes = [10, 50, 100, 500]
        results = {}
        
        for size in dataset_sizes:
            # Setup test data
            for i in range(size):
                word = await word_factory(text=f"searchword{i}", language="en")
                await definition_factory(word_instance=word)
            
            async def search_operation():
                response = await async_client.get("/api/v1/search?q=searchword&max_results=20")
                assert response.status_code == 200
                data = response.json()
                assert len(data["results"]) > 0
                return data
            
            await benchmark.pedantic(search_operation, iterations=5, rounds=3)
            results[size] = benchmark.stats.stats.mean
            
            # Each search should be within threshold
            assert benchmark.stats.stats.mean < performance_thresholds["search_basic"]
        
        # Search should scale reasonably (not exponentially)
        # Performance shouldn't degrade more than 3x from 10 to 500 items
        assert results[500] < results[10] * 3

    @pytest.mark.asyncio
    async def test_batch_lookup_performance(
        self,
        async_client: AsyncClient,
        mock_openai_client,
        benchmark,
        performance_thresholds
    ):
        """Benchmark batch lookup operations."""
        batch_data = {
            "words": ["batch1", "batch2", "batch3", "batch4", "batch5"],
            "providers": ["wiktionary"],
            "languages": ["en"]
        }
        
        async def batch_operation():
            response = await async_client.post("/api/v1/batch/lookup", json=batch_data)
            assert response.status_code == 200
            data = response.json()
            assert data["summary"]["requested"] == 5
            return data
        
        await benchmark.pedantic(batch_operation, iterations=3, rounds=3)
        
        # Batch operations should be efficient
        assert benchmark.stats.stats.mean < performance_thresholds["batch_lookup_5"]

    @pytest.mark.asyncio
    async def test_wordlist_creation_performance(
        self,
        async_client: AsyncClient,
        benchmark
    ):
        """Benchmark wordlist creation with varying sizes."""
        wordlist_sizes = [10, 100, 500, 1000]
        
        for size in wordlist_sizes:
            words = [f"perfword{i}" for i in range(size)]
            wordlist_data = {
                "name": f"Performance Test {size}",
                "description": f"Benchmark with {size} words",
                "words": words
            }
            
            async def create_operation():
                response = await async_client.post("/api/v1/wordlists", json=wordlist_data)
                assert response.status_code == 201
                data = response.json()
                assert data["total_words"] == size
                return data
            
            await benchmark.pedantic(create_operation, iterations=1, rounds=3)
            
            # Larger wordlists should still complete in reasonable time
            max_time = min(10.0, size * 0.01)  # Scale with size but cap at 10s
            assert benchmark.stats.stats.mean < max_time

    @pytest.mark.asyncio
    async def test_wordlist_upload_performance(
        self,
        async_client: AsyncClient,
        benchmark,
        performance_thresholds
    ):
        """Benchmark file upload performance."""
        # Create test file with substantial content
        words = [f"uploadword{i}" for i in range(1000)]
        file_content = "\n".join(words)
        file_data = io.BytesIO(file_content.encode())
        
        async def upload_operation():
            file_data.seek(0)  # Reset file pointer
            files = {"file": ("large_wordlist.txt", file_data, "text/plain")}
            data = {"name": "Performance Upload"}
            
            response = await async_client.post(
                "/api/v1/wordlists/upload",
                files=files,
                data=data
            )
            assert response.status_code == 201
            result = response.json()
            assert result["total_words"] == 1000
            return result
        
        await benchmark.pedantic(upload_operation, iterations=2, rounds=2)
        
        # File uploads should complete within threshold
        assert benchmark.stats.stats.mean < performance_thresholds["wordlist_upload"]

    @pytest.mark.asyncio
    async def test_ai_synthesis_performance(
        self,
        async_client: AsyncClient,
        mock_openai_client,
        benchmark,
        performance_thresholds
    ):
        """Benchmark AI synthesis operations."""
        request_data = {"word": "synthesis"}
        
        async def ai_operation():
            response = await async_client.post(
                "/api/v1/ai/synthesize/pronunciation",
                json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert "phonetic" in data
            return data
        
        await benchmark.pedantic(ai_operation, iterations=10, rounds=5)
        
        # AI operations should be fast with mocking
        assert benchmark.stats.stats.mean < performance_thresholds["ai_synthesis"]

    @pytest.mark.asyncio
    async def test_concurrent_request_performance(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        benchmark
    ):
        """Benchmark system performance under concurrent load."""
        # Setup test data
        word = await word_factory(text="concurrent", language="en")
        await definition_factory(word_instance=word)
        
        async def concurrent_operations():
            # Create multiple concurrent requests
            tasks = [
                async_client.get("/api/v1/lookup/concurrent"),
                async_client.get("/api/v1/search?q=concurrent"),
                async_client.get("/api/v1/wordlists"),
                async_client.get("/api/v1/health")
            ]
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
            
            return len(responses)
        
        await benchmark.pedantic(concurrent_operations, iterations=5, rounds=3)
        
        # Concurrent operations should complete quickly
        assert benchmark.stats.stats.mean < 2.0  # 2 seconds for 4 concurrent requests

    @pytest.mark.asyncio
    async def test_corpus_search_performance(
        self,
        async_client: AsyncClient,
        benchmark
    ):
        """Benchmark corpus search performance."""
        # Create corpus with substantial word list
        corpus_data = {
            "words": [f"corpusword{i}" for i in range(500)],
            "name": "performance_corpus"
        }
        
        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        assert create_response.status_code == 201
        corpus_id = create_response.json()["corpus_id"]
        
        async def corpus_search_operation():
            response = await async_client.post(
                f"/api/v1/corpus/{corpus_id}/search?query=corpusword&max_results=50"
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) > 0
            return data
        
        await benchmark.pedantic(corpus_search_operation, iterations=10, rounds=5)
        
        # Corpus search should be very fast (in-memory)
        assert benchmark.stats.stats.mean < 0.1  # 100ms

    @pytest.mark.asyncio
    async def test_database_operation_performance(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        benchmark
    ):
        """Benchmark database operation performance."""
        async def database_operations():
            # Create word
            word = await word_factory(text="dbperf", language="en")
            assert_valid_object_id(word.id)
            
            # Create definition
            definition = await definition_factory(word_instance=word)
            assert_valid_object_id(definition.id)
            
            # Query operations
            from src.floridify.models.models import Definition, Word
            found_word = await Word.find_one(Word.text == "dbperf")
            assert found_word is not None
            
            found_definitions = await Definition.find(Definition.word_id == word.id).to_list()
            assert len(found_definitions) > 0
            
            return len(found_definitions)
        
        await benchmark.pedantic(database_operations, iterations=10, rounds=5)
        
        # Database operations should be efficient
        assert benchmark.stats.stats.mean < 0.5  # 500ms for CRUD operations

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory
    ):
        """Test memory usage patterns under load."""
        import os

        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        for i in range(100):
            word = await word_factory(text=f"memtest{i}", language="en")
            await definition_factory(word_instance=word)
            
            # Make API calls
            await async_client.get(f"/api/v1/lookup/memtest{i}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage should not grow excessively
        assert memory_increase < 100  # Less than 100MB increase
        
        # Cleanup test data
        from src.floridify.models.models import Definition, Word
        await Word.delete_many({"text": {"$regex": "^memtest"}})
        await Definition.delete_many({})

    @pytest.mark.asyncio
    async def test_streaming_response_performance(
        self,
        async_client: AsyncClient,
        mock_openai_client,
        benchmark
    ):
        """Benchmark streaming response performance."""
        async def streaming_operation():
            response = await async_client.get(
                "/api/v1/lookup/streaming/stream",
                headers={"Accept": "text/event-stream"}
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            # Count events in stream
            event_count = response.text.count("data:")
            assert event_count > 0
            
            return event_count
        
        await benchmark.pedantic(streaming_operation, iterations=5, rounds=3)
        
        # Streaming should be efficient
        assert benchmark.stats.stats.mean < 3.0  # 3 seconds for streaming response

    @pytest.mark.asyncio
    async def test_cache_performance_impact(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        benchmark
    ):
        """Benchmark cache hit vs miss performance."""
        # Setup test data
        word = await word_factory(text="cached", language="en")
        await definition_factory(word_instance=word)
        
        # Warm up cache
        await async_client.get("/api/v1/lookup/cached")
        
        async def cache_hit_operation():
            response = await async_client.get("/api/v1/lookup/cached")
            assert response.status_code == 200
            return response.json()
        
        async def cache_miss_operation():
            response = await async_client.get("/api/v1/lookup/cached?force_refresh=true")
            assert response.status_code == 200
            return response.json()
        
        # Benchmark cache hits
        await benchmark.pedantic(cache_hit_operation, iterations=20, rounds=5)
        cache_hit_time = benchmark.stats.stats.mean
        
        # Benchmark cache misses
        await benchmark.pedantic(cache_miss_operation, iterations=5, rounds=3)
        cache_miss_time = benchmark.stats.stats.mean
        
        # Cache hits should be significantly faster
        assert cache_hit_time < cache_miss_time * 0.5  # At least 50% faster
        assert cache_hit_time < 0.1  # Cache hits should be very fast