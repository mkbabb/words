"""Reference cleanup service for maintaining data integrity."""

import asyncio
import logging
from typing import Any

from beanie import PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class CleanupService:
    """Simple, reusable reference cleanup service."""

    @staticmethod
    async def remove_object_id_from_arrays(
        collections: list[AsyncIOMotorCollection[Any]],
        array_field: str,
        object_id: PydanticObjectId,
    ) -> int:
        """Remove ObjectId from array fields across multiple collections.

        Args:
            collections: List of MongoDB collections to update
            array_field: Name of the array field containing ObjectIds
            object_id: The ObjectId to remove from arrays

        Returns:
            Total number of documents modified across all collections

        """
        tasks = [
            collection.update_many({array_field: object_id}, {"$pull": {array_field: object_id}})
            for collection in collections
        ]

        results = await asyncio.gather(*tasks)
        total_modified = sum(result.modified_count for result in results)

        logger.warning(
            f"Removed ObjectId {object_id} from {total_modified} documents across {len(collections)} collections",
        )
        return total_modified

    @staticmethod
    async def cleanup_image_references(image_id: PydanticObjectId) -> int:
        """Clean up image references from all collections that reference images.

        Args:
            image_id: The ID of the image being deleted

        Returns:
            Total number of documents that had their image_ids arrays updated

        """
        # Import models here to avoid circular imports
        from ...models import Definition, SynthesizedDictionaryEntry

        collections = [
            Definition.get_pymongo_collection(),
            SynthesizedDictionaryEntry.get_pymongo_collection(),
        ]

        logger.warning(f"Starting cleanup of image references for image {image_id}")
        total_cleaned = await CleanupService.remove_object_id_from_arrays(
            collections,  # type: ignore[arg-type]
            "image_ids",
            image_id,
        )

        logger.warning(
            f"Completed cleanup: removed image {image_id} from {total_cleaned} documents",
        )
        return total_cleaned
