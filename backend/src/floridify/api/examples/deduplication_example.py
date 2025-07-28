"""Example FastAPI endpoint with request deduplication.

This example shows how to use request deduplication in FastAPI endpoints
to prevent duplicate concurrent requests from overwhelming backend services.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from ...caching import cached_api_call, deduplicated
from ...utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Simulate database/API calls
async def fetch_from_database(item_id: str) -> dict[str, Any]:
    """Simulate an expensive database query."""
    logger.info(f"📊 Executing database query for item: {item_id}")
    await asyncio.sleep(1.5)  # Simulate query time
    return {
        "id": item_id,
        "name": f"Item {item_id}",
        "price": 99.99,
        "stock": 42,
        "fetched_at": time.time(),
    }


async def call_external_api(query: str) -> dict[str, Any]:
    """Simulate calling an external API."""
    logger.info(f"🌐 Calling external API with query: {query}")
    await asyncio.sleep(2.0)  # Simulate API latency
    return {
        "query": query,
        "results": [f"Result {i} for {query}" for i in range(5)],
        "api_timestamp": time.time(),
    }


# Example 1: Basic deduplication for database queries
@router.get("/items/{item_id}")
# @deduplicated(key_func=lambda item_id: f"get_item:{item_id}")
async def get_item(item_id: str) -> dict[str, Any]:
    """Get item details with request deduplication.
    
    Multiple concurrent requests for the same item will only result
    in one database query.
    """
    try:
        # This will be deduplicated - concurrent requests will wait
        # for the first one to complete
        result = await fetch_from_database(item_id)
        return {
            "status": "success",
            "data": result,
            "deduplicated": True,
        }
    except Exception as e:
        logger.error(f"Failed to fetch item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example 2: Deduplication with caching
@router.get("/search")
@cached_api_call(
    ttl_hours=0.5,  # Cache for 30 minutes
    key_func=lambda q: ("search", q),
)
async def search_items(q: str) -> dict[str, Any]:
    """Search items with caching and deduplication.
    
    Benefits:
    1. Concurrent identical searches share the same result (deduplication)
    2. Subsequent searches within 30 minutes return cached results
    3. Reduces load on external search API
    """
    if not q or len(q) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    
    # This expensive operation will be both cached and deduplicated
    api_result = await call_external_api(q)
    
    return {
        "status": "success",
        "query": q,
        "data": api_result,
        "cached": False,  # First request won't be cached
    }


# Example 3: Manual deduplication for complex operations
class BatchProcessor:
    """Example of manual deduplication for batch operations."""
    
    def __init__(self) -> None:
        self._in_flight: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()
    
    async def process_batch(self, batch_id: str, items: list[str]) -> dict[str, Any]:
        """Process a batch with deduplication."""
        # Check if this batch is already being processed
        async with self._lock:
            if batch_id in self._in_flight:
                logger.info(f"🔄 Batch {batch_id} already in flight, waiting...")
                future = self._in_flight[batch_id]
            else:
                # Create new future for this batch
                future = asyncio.Future()
                self._in_flight[batch_id] = future
                
                # Schedule the actual processing
                asyncio.create_task(self._do_process_batch(batch_id, items, future))
        
        # Wait for result
        result: dict[str, Any] = await future
        return result
    
    async def _do_process_batch(
        self,
        batch_id: str,
        items: list[str],
        future: asyncio.Future[Any],
    ) -> None:
        """Actually process the batch."""
        try:
            logger.info(f"🏭 Processing batch {batch_id} with {len(items)} items")
            await asyncio.sleep(3)  # Simulate processing
            
            result = {
                "batch_id": batch_id,
                "processed_count": len(items),
                "items": items,
                "processed_at": time.time(),
            }
            
            future.set_result(result)
            logger.info(f"✅ Batch {batch_id} processing complete")
            
        except Exception as e:
            future.set_exception(e)
            logger.error(f"❌ Batch {batch_id} processing failed: {e}")
        
        finally:
            # Clean up
            async with self._lock:
                self._in_flight.pop(batch_id, None)


# Global batch processor instance
batch_processor = BatchProcessor()


@router.post("/process-batch/{batch_id}")
async def process_batch(batch_id: str, items: list[str]) -> dict[str, Any]:
    """Process a batch of items with deduplication.
    
    If multiple requests come in for the same batch_id while processing
    is in progress, they will all wait for and receive the same result.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Items list cannot be empty")
    
    result = await batch_processor.process_batch(batch_id, items)
    
    return {
        "status": "success",
        "data": result,
        "message": "Batch processed (may have been deduplicated)",
    }


# Example 4: Deduplication with timeout
@router.get("/external-data/{resource_id}")
@deduplicated(
    key_func=lambda resource_id: f"external:{resource_id}",
    max_wait_time=5.0,  # Don't wait more than 5 seconds
)
async def get_external_data(resource_id: str) -> dict[str, Any]:
    """Fetch external data with deduplication and timeout.
    
    If a request is already in flight, new requests will wait up to
    5 seconds for it to complete. After that, they'll make their own request.
    """
    try:
        # Simulate unreliable external service
        logger.info(f"🌍 Fetching external resource: {resource_id}")
        
        # Random delay to simulate network issues
        import random
        delay = random.uniform(1, 7)  # Sometimes exceeds timeout
        await asyncio.sleep(delay)
        
        return {
            "status": "success",
            "resource_id": resource_id,
            "data": f"External data for {resource_id}",
            "fetch_time": delay,
            "timestamp": time.time(),
        }
        
    except asyncio.CancelledError:
        logger.warning(f"Request cancelled for resource: {resource_id}")
        raise HTTPException(status_code=503, detail="Request cancelled")
    except Exception as e:
        logger.error(f"Failed to fetch resource {resource_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Test endpoint to demonstrate deduplication
@router.get("/test-deduplication")
async def test_deduplication() -> dict[str, Any]:
    """Test endpoint that triggers multiple concurrent requests.
    
    This demonstrates how deduplication works by making several
    concurrent requests to the same endpoints.
    """
    # Test 1: Multiple requests for the same item
    item_tasks = [
        get_item("test-item-123") for _ in range(5)
    ]
    
    # Test 2: Multiple searches
    search_tasks = [
        search_items("python") for _ in range(3)
    ]
    
    start_time = time.time()
    
    # Execute all tasks concurrently
    item_results = await asyncio.gather(*item_tasks)
    search_results = await asyncio.gather(*search_tasks)
    
    elapsed = time.time() - start_time
    
    # Check if deduplication worked
    item_timestamps = [r["data"]["fetched_at"] for r in item_results]
    search_timestamps = [r["data"]["api_timestamp"] for r in search_results]
    
    return {
        "status": "success",
        "elapsed_time": elapsed,
        "item_requests": {
            "count": len(item_tasks),
            "unique_executions": len(set(item_timestamps)),
            "all_timestamps": item_timestamps,
        },
        "search_requests": {
            "count": len(search_tasks),
            "unique_executions": len(set(search_timestamps)),
            "all_timestamps": search_timestamps,
        },
        "deduplication_worked": len(set(item_timestamps)) == 1 and len(set(search_timestamps)) == 1,
    }