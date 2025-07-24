"""Query optimization utilities for MongoDB operations."""

import time
from contextlib import asynccontextmanager
from typing import Any

from beanie import Document
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from floridify.storage.mongodb import get_database
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


class QueryOptimizer:
    """Utilities for optimizing MongoDB queries."""
    
    def __init__(self, db: AsyncIOMotorDatabase | None = None):
        self.db = db
    
    async def _get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if not self.db:
            self.db = await get_database()
        return self.db
    
    async def analyze_indexes(self, model: type[Document]) -> dict[str, Any]:
        """Analyze index usage for a model."""
        db = await self._get_db()
        collection = db[model.get_collection_name()]
        
        # Get existing indexes
        indexes = await collection.list_indexes().to_list(None)
        
        # Get index stats
        stats = []
        for index in indexes:
            index_stats = await collection.aggregate([
                {"$indexStats": {}},
                {"$match": {"name": index["name"]}},
            ]).to_list(None)
            
            stats.append({
                "name": index["name"],
                "keys": index["key"],
                "usage": index_stats[0] if index_stats else None,
            })
        
        return {
            "collection": model.get_collection_name(),
            "indexes": stats,
            "recommendations": self._get_index_recommendations(stats),
        }
    
    def _get_index_recommendations(self, stats: list[dict]) -> list[str]:
        """Generate index recommendations based on usage."""
        recommendations = []
        
        for stat in stats:
            if stat["usage"] and stat["usage"].get("accesses", {}).get("ops", 0) == 0:
                recommendations.append(f"Consider removing unused index: {stat['name']}")
        
        return recommendations
    
    async def create_optimal_indexes(self, model: type[Document]) -> list[str]:
        """Create optimal indexes for a model based on common queries."""
        db = await self._get_db()
        collection = db[model.get_collection_name()]
        created = []
        
        # Model-specific indexes
        if model.__name__ == "Word":
            indexes = [
                ([("text", ASCENDING), ("language", ASCENDING)], {"unique": True}),
                ([("normalized", ASCENDING)], {}),
                ([("created_at", DESCENDING)], {}),
            ]
        elif model.__name__ == "Definition":
            indexes = [
                ([("word_id", ASCENDING)], {}),
                ([("word_id", ASCENDING), ("part_of_speech", ASCENDING)], {}),
                ([("cefr_level", ASCENDING)], {"sparse": True}),
                ([("frequency_band", ASCENDING)], {"sparse": True}),
            ]
        elif model.__name__ == "Example":
            indexes = [
                ([("definition_id", ASCENDING)], {}),
                ([("word_id", ASCENDING)], {}),
                ([("quality_score", DESCENDING)], {"sparse": True}),
            ]
        elif model.__name__ == "SynthesizedDictionaryEntry":
            indexes = [
                ([("word_id", ASCENDING)], {"unique": True}),
                ([("accessed_at", DESCENDING)], {"sparse": True}),
                ([("access_count", DESCENDING)], {}),
            ]
        else:
            indexes = []
        
        # Create indexes
        for keys, options in indexes:
            try:
                index_name = await collection.create_index(keys, **options)
                created.append(index_name)
                logger.info(f"Created index {index_name} on {model.__name__}")
            except Exception as e:
                logger.warning(f"Failed to create index on {model.__name__}: {e}")
        
        return created
    
    @asynccontextmanager
    async def profile_query(self, description: str = "Query"):
        """Context manager for profiling queries."""
        start_time = time.time()
        
        # Enable profiling if needed
        await self._get_db()
        
        yield
        
        elapsed = time.time() - start_time
        
        if elapsed > 0.1:  # Log slow queries
            logger.warning(f"Slow query detected: {description} took {elapsed:.3f}s")
        else:
            logger.debug(f"{description} completed in {elapsed:.3f}s")


class AggregationBuilder:
    """Builder for complex MongoDB aggregation pipelines."""
    
    def __init__(self):
        self.pipeline = []
    
    def match(self, query: dict[str, Any]) -> "AggregationBuilder":
        """Add match stage."""
        self.pipeline.append({"$match": query})
        return self
    
    def lookup(
        self,
        from_collection: str,
        local_field: str,
        foreign_field: str,
        as_field: str
    ) -> "AggregationBuilder":
        """Add lookup stage."""
        self.pipeline.append({
            "$lookup": {
                "from": from_collection,
                "localField": local_field,
                "foreignField": foreign_field,
                "as": as_field,
            }
        })
        return self
    
    def unwind(self, path: str, preserve_empty: bool = False) -> "AggregationBuilder":
        """Add unwind stage."""
        self.pipeline.append({
            "$unwind": {
                "path": f"${path}",
                "preserveNullAndEmptyArrays": preserve_empty,
            }
        })
        return self
    
    def group(self, _id: Any, fields: dict[str, Any]) -> "AggregationBuilder":
        """Add group stage."""
        group_stage = {"_id": _id}
        group_stage.update(fields)
        self.pipeline.append({"$group": group_stage})
        return self
    
    def sort(self, fields: dict[str, int]) -> "AggregationBuilder":
        """Add sort stage."""
        self.pipeline.append({"$sort": fields})
        return self
    
    def limit(self, n: int) -> "AggregationBuilder":
        """Add limit stage."""
        self.pipeline.append({"$limit": n})
        return self
    
    def skip(self, n: int) -> "AggregationBuilder":
        """Add skip stage."""
        self.pipeline.append({"$skip": n})
        return self
    
    def project(self, fields: dict[str, Any]) -> "AggregationBuilder":
        """Add project stage."""
        self.pipeline.append({"$project": fields})
        return self
    
    def add_fields(self, fields: dict[str, Any]) -> "AggregationBuilder":
        """Add fields stage."""
        self.pipeline.append({"$addFields": fields})
        return self
    
    def facet(self, facets: dict[str, list]) -> "AggregationBuilder":
        """Add facet stage for multiple aggregations."""
        self.pipeline.append({"$facet": facets})
        return self
    
    def build(self) -> list[dict[str, Any]]:
        """Build the pipeline."""
        return self.pipeline


class BulkOperationBuilder:
    """Builder for bulk operations."""
    
    def __init__(self, model: type[Document]):
        self.model = model
        self.operations = []
    
    def insert_one(self, document: dict[str, Any]) -> "BulkOperationBuilder":
        """Add insert operation."""
        self.operations.append({"insertOne": {"document": document}})
        return self
    
    def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False
    ) -> "BulkOperationBuilder":
        """Add update one operation."""
        self.operations.append({
            "updateOne": {
                "filter": filter,
                "update": update,
                "upsert": upsert,
            }
        })
        return self
    
    def update_many(
        self,
        filter: dict[str, Any],
        update: dict[str, Any]
    ) -> "BulkOperationBuilder":
        """Add update many operation."""
        self.operations.append({
            "updateMany": {
                "filter": filter,
                "update": update,
            }
        })
        return self
    
    def delete_one(self, filter: dict[str, Any]) -> "BulkOperationBuilder":
        """Add delete one operation."""
        self.operations.append({"deleteOne": {"filter": filter}})
        return self
    
    def delete_many(self, filter: dict[str, Any]) -> "BulkOperationBuilder":
        """Add delete many operation."""
        self.operations.append({"deleteMany": {"filter": filter}})
        return self
    
    async def execute(self) -> dict[str, Any]:
        """Execute bulk operations."""
        if not self.operations:
            return {"acknowledged": True, "modifiedCount": 0}
        
        db = await get_database()
        collection = db[self.model.get_collection_name()]
        
        result = await collection.bulk_write(self.operations)
        
        return {
            "acknowledged": result.acknowledged,
            "insertedCount": result.inserted_count,
            "matchedCount": result.matched_count,
            "modifiedCount": result.modified_count,
            "deletedCount": result.deleted_count,
            "upsertedCount": result.upserted_count,
        }