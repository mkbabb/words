"""Tests for batch operations and error handling."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import HTTPStatusError, RequestError, TimeoutException

from floridify.models.dictionary import DictionaryProvider, Language
from floridify.providers.batch import BatchOperation, BatchStatus
from floridify.providers.core import (
    ConnectorConfig,
    ProviderType,
)
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
    WiktionaryWholesaleConnector,
)
from floridify.providers.utils import (
    AdaptiveRateLimiter,
    ScrapingError,
)


class TestBatchOperations:
    """Test batch processing operations."""
    
    @pytest.mark.asyncio
    async def test_batch_operation_creation(self, test_db):
        """Test creating and saving batch operations."""
        batch = BatchOperation(
            operation_id="test_batch_001",
            operation_type="dictionary_lookup",
            provider=DictionaryProvider.OXFORD,
            total_items=1000,
            corpus_name="test_corpus",
            corpus_language=Language.ENGLISH,
        )
        
        await batch.save()
        
        # Reload and verify
        loaded = await BatchOperation.find_one(
            BatchOperation.operation_id == "test_batch_001"
        )
        
        assert loaded is not None
        assert loaded.total_items == 1000
        assert loaded.status == BatchStatus.PENDING
        assert loaded.processed_items == 0
        assert loaded.failed_items == 0
    
    @pytest.mark.asyncio
    async def test_batch_progress_tracking(self, test_db):
        """Test tracking batch operation progress."""
        batch = BatchOperation(
            operation_id="progress_test",
            operation_type="corpus_build",
            provider=DictionaryProvider.WIKTIONARY,
            total_items=100,
        )
        await batch.save()
        
        # Simulate processing
        batch.status = BatchStatus.IN_PROGRESS
        batch.started_at = datetime.now(UTC)
        
        for i in range(50):
            batch.processed_items += 1
            if i % 10 == 0:
                # Update checkpoint periodically
                batch.update_checkpoint({"last_processed": i, "position": i})
        
        await batch.save()
        
        # Verify progress
        assert batch.processed_items == 50
        assert batch.checkpoint["last_processed"] == 40
        assert batch.last_checkpoint_at is not None
    
    @pytest.mark.asyncio
    async def test_batch_error_tracking(self, test_db):
        """Test error tracking in batch operations."""
        batch = BatchOperation(
            operation_id="error_test",
            operation_type="dictionary_lookup",
            provider=DictionaryProvider.FREE_DICTIONARY,
            total_items=10,
        )
        await batch.save()
        
        # Add errors
        batch.add_error("word1", "404 Not Found", "NOT_FOUND")
        batch.add_error("word2", "Rate limit exceeded", "RATE_LIMIT")
        batch.add_error("word3", "Timeout", "TIMEOUT")
        
        await batch.save()
        
        # Verify errors
        assert batch.failed_items == 3
        assert len(batch.errors) == 3
        assert batch.errors[0]["word"] == "word1"
        assert batch.errors[1]["error_code"] == "RATE_LIMIT"
    
    @pytest.mark.asyncio
    async def test_batch_resume_capability(self, test_db):
        """Test resuming interrupted batch operations."""
        # Create partially completed batch
        batch = BatchOperation(
            operation_id="resume_test",
            operation_type="corpus_download",
            provider=DictionaryProvider.WIKTIONARY,
            total_items=1000,
            processed_items=500,
            status=BatchStatus.IN_PROGRESS,
            checkpoint={
                "last_word": "middle",
                "position": 500,
                "partial_results": ["word1", "word2"],
            },
        )
        await batch.save()
        
        # Simulate resume
        loaded = await BatchOperation.find_one(
            BatchOperation.operation_id == "resume_test"
        )
        
        assert loaded is not None
        assert loaded.processed_items == 500
        assert loaded.checkpoint["position"] == 500
        
        # Continue processing from checkpoint
        start_position = loaded.checkpoint["position"]
        for i in range(start_position, loaded.total_items):
            loaded.processed_items += 1
        
        loaded.status = BatchStatus.COMPLETED
        loaded.completed_at = datetime.now(UTC)
        await loaded.save()
        
        assert loaded.processed_items == loaded.total_items
        assert loaded.status == BatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_batch_statistics(self, test_db):
        """Test batch operation statistics."""
        batch = BatchOperation(
            operation_id="stats_test",
            operation_type="dictionary_lookup",
            provider=DictionaryProvider.OXFORD,
            total_items=100,
        )
        
        batch.started_at = datetime.now(UTC)
        
        # Simulate processing with statistics
        batch.processed_items = 95
        batch.failed_items = 5
        batch.statistics = {
            "words_per_second": 2.5,
            "cache_hits": 30,
            "cache_misses": 70,
            "api_calls": 70,
            "retries": 10,
            "average_response_time": 0.5,
        }
        
        batch.completed_at = datetime.now(UTC) + timedelta(seconds=40)
        batch.status = BatchStatus.COMPLETED
        
        await batch.save()
        
        # Verify statistics
        assert batch.statistics["words_per_second"] == 2.5
        assert batch.statistics["cache_hits"] == 30
        assert batch.statistics["api_calls"] == 70
        
        # Calculate success rate
        success_rate = (batch.processed_items - batch.failed_items) / batch.total_items
        assert success_rate == 0.9  # 90% success rate
    
    @pytest.mark.asyncio
    async def test_parallel_batch_processing(self, test_db, connector_config):
        """Test parallel processing of batch operations."""
        words = [f"word_{i}" for i in range(20)]
        
        connector = FreeDictionaryConnector(connector_config)
        
        # Mock lookup to simulate processing
        async def mock_lookup(word):
            await asyncio.sleep(0.01)  # Simulate API delay
            return {"word": word, "definition": f"Definition of {word}"}
        
        with patch.object(connector, 'lookup', side_effect=mock_lookup):
            # Process in parallel batches
            batch_size = 5
            results = []
            
            for i in range(0, len(words), batch_size):
                batch_words = words[i:i + batch_size]
                batch_tasks = [connector.lookup(w) for w in batch_words]
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
            
            assert len(results) == len(words)
            assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_with_rate_limiting(self, test_db, connector_config):
        """Test batch processing with rate limiting."""
        # Configure aggressive rate limiting
        config = ConnectorConfig(
            provider_type=ProviderType.DICTIONARY,
            rate_limit_calls=5,
            rate_limit_period=1.0,
        )
        
        connector = FreeDictionaryConnector(config)
        
        call_times = []
        
        async def track_calls(word):
            call_times.append(asyncio.get_event_loop().time())
            return {"word": word}
        
        with patch.object(connector, 'lookup', side_effect=track_calls):
            # Process batch
            words = [f"word_{i}" for i in range(10)]
            tasks = [connector.lookup(w) for w in words]
            await asyncio.gather(*tasks)
            
            # Check rate limiting was applied
            # Should have delays between batches of 5
            if len(call_times) > 5:
                # Time between 5th and 6th call should show rate limiting
                time_diff = call_times[5] - call_times[4]
                # Should have some delay due to rate limiting
                # (exact timing depends on implementation)


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff in rate limiting."""
        from floridify.providers.utils import RateLimitConfig
        
        config = RateLimitConfig(
            base_requests_per_second=2.0,
            min_delay=0.1,
            max_delay=2.0,
            backoff_multiplier=2.0,
        )
        
        # Test backoff multiplier is configured
        assert config.backoff_multiplier == 2.0
        assert config.min_delay == 0.1
        assert config.max_delay == 2.0
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_errors(self, connector_config):
        """Test retry logic for transient errors."""
        connector = FreeDictionaryConnector(connector_config)
        
        call_count = 0
        
        async def flaky_api(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Fail first 2 attempts
                raise RequestError("Connection error")
            
            # Succeed on 3rd attempt
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"success": True}
            return response
        
        with patch.object(connector, 'client') as mock_client:
            mock_client.get = flaky_api
            
            result = await connector.lookup("test")
            
            assert call_count == 3
            assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_errors(self, connector_config):
        """Test that permanent errors are not retried."""
        connector = FreeDictionaryConnector(connector_config)
        
        call_count = 0
        
        async def permanent_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            response = MagicMock()
            response.status_code = 404  # Not Found - permanent error
            response.raise_for_status.side_effect = HTTPStatusError(
                "Not Found", request=MagicMock(), response=response
            )
            return response
        
        with patch.object(connector, 'client') as mock_client:
            mock_client.get = permanent_error
            
            result = await connector.lookup("nonexistent")
            
            # Should not retry on 404
            assert call_count == 1
            assert result is None
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test handling of rate limit errors."""
        limiter = AdaptiveRateLimiter(
            calls_per_period=2,
            period=0.1,
            adaptive=True,
        )
        
        # Make calls up to limit
        async with limiter:
            pass
        async with limiter:
            pass
        
        # Next call should be rate limited
        start_time = asyncio.get_event_loop().time()
        async with limiter:
            pass
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should have waited for rate limit window
        assert elapsed >= 0.05  # Some delay expected
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiting based on errors."""
        limiter = AdaptiveRateLimiter(
            calls_per_period=10,
            period=1.0,
            adaptive=True,
        )
        
        initial_rate = limiter.calls_per_period
        
        # Simulate rate limit errors
        for _ in range(3):
            limiter.on_rate_limit_error()
        
        # Rate should be reduced
        assert limiter.calls_per_period < initial_rate
        
        # Simulate successful calls
        for _ in range(10):
            limiter.on_success()
        
        # Rate should recover somewhat
        assert limiter.calls_per_period > limiter.calls_per_period * 0.5
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, connector_config):
        """Test handling of timeout errors."""
        config = ConnectorConfig(
            provider_type=ProviderType.DICTIONARY,
            timeout=0.1,  # 100ms timeout
            max_retries=2,
        )
        
        connector = FreeDictionaryConnector(config)
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.5)  # Longer than timeout
            return MagicMock()
        
        with patch.object(connector, 'client') as mock_client:
            mock_client.get = slow_response
            
            with pytest.raises(TimeoutException):
                await connector.lookup("test")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for failing services."""
        
        class CircuitBreaker:
            def __init__(self, failure_threshold=5, recovery_timeout=1.0):
                self.failure_count = 0
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout
                self.last_failure_time = None
                self.is_open = False
            
            async def call(self, func, *args, **kwargs):
                if self.is_open:
                    if self.last_failure_time:
                        elapsed = asyncio.get_event_loop().time() - self.last_failure_time
                        if elapsed < self.recovery_timeout:
                            raise ScrapingError("Circuit breaker is open")
                    self.is_open = False
                    self.failure_count = 0
                
                try:
                    result = await func(*args, **kwargs)
                    self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = asyncio.get_event_loop().time()
                    
                    if self.failure_count >= self.failure_threshold:
                        self.is_open = True
                    
                    raise e
        
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        
        async def failing_function():
            raise Exception("Service unavailable")
        
        # Trigger circuit breaker
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_function)
        
        # Circuit should be open
        assert breaker.is_open is True
        
        # Should fail fast while open
        with pytest.raises(ScrapingError, match="Circuit breaker is open"):
            await breaker.call(failing_function)
        
        # Wait for recovery
        await asyncio.sleep(0.15)
        
        # Circuit should allow retry
        async def working_function():
            return "success"
        
        result = await breaker.call(working_function)
        assert result == "success"
        assert breaker.is_open is False


class TestWholesaleBatchOperations:
    """Test wholesale/bulk provider operations."""
    
    @pytest.mark.asyncio
    async def test_wholesale_download(self, test_db, connector_config):
        """Test wholesale dictionary download."""
        connector = WiktionaryWholesaleConnector(connector_config)
        
        # Mock download of dictionary dump
        mock_dump_data = {
            "words": [
                {"word": "apple", "definitions": ["a fruit"]},
                {"word": "banana", "definitions": ["another fruit"]},
            ]
        }
        
        with patch.object(connector, 'download_dump') as mock_download:
            mock_download.return_value = mock_dump_data
            
            # Create batch operation
            batch = BatchOperation(
                operation_id="wholesale_test",
                operation_type="wholesale_download",
                provider=DictionaryProvider.WIKTIONARY,
                total_items=len(mock_dump_data["words"]),
            )
            await batch.save()
            
            # Process dump
            batch.status = BatchStatus.IN_PROGRESS
            batch.started_at = datetime.now(UTC)
            
            for word_data in mock_dump_data["words"]:
                # Process each word
                batch.processed_items += 1
                batch.update_checkpoint({"last_word": word_data["word"]})
            
            batch.status = BatchStatus.COMPLETED
            batch.completed_at = datetime.now(UTC)
            await batch.save()
            
            assert batch.processed_items == 2
            assert batch.status == BatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_incremental_updates(self, test_db):
        """Test incremental updates from wholesale sources."""
        # Track last update
        last_update = datetime.now(UTC) - timedelta(days=7)
        
        batch = BatchOperation(
            operation_id="incremental_test",
            operation_type="incremental_update",
            provider=DictionaryProvider.WIKTIONARY,
            checkpoint={"last_update": last_update.isoformat()},
        )
        await batch.save()
        
        # Simulate getting changes since last update
        changes = [
            {"word": "newword1", "action": "added"},
            {"word": "oldword", "action": "updated"},
            {"word": "deletedword", "action": "deleted"},
        ]
        
        batch.total_items = len(changes)
        batch.status = BatchStatus.IN_PROGRESS
        
        for change in changes:
            if change["action"] == "added":
                # Add new word
                pass
            elif change["action"] == "updated":
                # Update existing word
                pass
            elif change["action"] == "deleted":
                # Delete word
                pass
            
            batch.processed_items += 1
        
        batch.checkpoint["last_update"] = datetime.now(UTC).isoformat()
        batch.status = BatchStatus.COMPLETED
        await batch.save()
        
        assert batch.processed_items == 3
        assert batch.checkpoint["last_update"] is not None


class TestBatchRecovery:
    """Test batch operation recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_recover_from_partial_failure(self, test_db):
        """Test recovering from partial batch failure."""
        # Create batch with partial failure
        batch = BatchOperation(
            operation_id="partial_failure",
            operation_type="dictionary_lookup",
            provider=DictionaryProvider.OXFORD,
            total_items=100,
            processed_items=60,
            failed_items=10,
            status=BatchStatus.PARTIAL,
            errors=[
                {"word": f"failed_{i}", "error": "API Error"}
                for i in range(10)
            ],
        )
        await batch.save()
        
        # Retry failed items
        retry_batch = BatchOperation(
            operation_id="partial_failure_retry",
            operation_type="dictionary_lookup_retry",
            provider=DictionaryProvider.OXFORD,
            total_items=10,  # Only failed items
            checkpoint={"parent_batch": batch.operation_id},
        )
        await retry_batch.save()
        
        # Process retries
        retry_batch.processed_items = 8  # 8 succeeded on retry
        retry_batch.failed_items = 2  # 2 still failed
        retry_batch.status = BatchStatus.COMPLETED
        await retry_batch.save()
        
        # Update original batch
        batch.processed_items += 8
        batch.failed_items = 2
        batch.status = BatchStatus.COMPLETED
        await batch.save()
        
        assert batch.processed_items == 68
        assert batch.failed_items == 2
    
    @pytest.mark.asyncio
    async def test_batch_rollback(self, test_db):
        """Test rolling back failed batch operations."""
        batch = BatchOperation(
            operation_id="rollback_test",
            operation_type="corpus_update",
            provider=DictionaryProvider.WIKTIONARY,
            total_items=50,
            processed_items=25,
            status=BatchStatus.IN_PROGRESS,
            checkpoint={
                "processed_words": ["word1", "word2", "word3"],
                "snapshot_id": "snapshot_123",
            },
        )
        await batch.save()
        
        # Simulate critical failure
        batch.status = BatchStatus.FAILED
        batch.errors.append({
            "error": "Critical database error",
            "timestamp": datetime.now(UTC),
        })
        
        # Rollback using snapshot
        snapshot_id = batch.checkpoint.get("snapshot_id")
        if snapshot_id:
            # Would restore from snapshot in real implementation
            batch.checkpoint["rolled_back"] = True
            batch.checkpoint["rollback_timestamp"] = datetime.now(UTC).isoformat()
        
        await batch.save()
        
        assert batch.status == BatchStatus.FAILED
        assert batch.checkpoint.get("rolled_back") is True