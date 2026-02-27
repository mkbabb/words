"""Corpus management endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ...caching.models import VersionConfig
from ...corpus.core import Corpus
from ...corpus.manager import get_tree_corpus_manager
from ...corpus.models import CorpusType
from ...models.base import Language
from ...models.parameters import CorpusCreateParams, CorpusListParams, PaginationParams
from ...models.responses import CorpusListResponse, CorpusResponse
from ...search.constants import SearchMode
from ...search.core import Search
from ...search.models import SearchIndex
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()





def parse_corpus_list_params(
    language: str | None = None,
    source_type: str | None = None,
    include_stats: bool = True,
) -> CorpusListParams:
    """Parse corpus list parameters."""
    language_enum = None
    if language:
        try:
            language_enum = Language(language.lower())
        except ValueError as e:
            valid_languages = [lang.value for lang in Language]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid language '{language}'. Valid languages: {', '.join(valid_languages)}",
            ) from e

    return CorpusListParams(
        language=language_enum,
        source_type=source_type,
        include_stats=include_stats,
    )


def parse_pagination_params(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> PaginationParams:
    """Parse pagination parameters."""
    return PaginationParams(offset=offset, limit=limit)


@router.get("/corpus", response_model=CorpusListResponse)
async def list_corpora(
    params: CorpusListParams = Depends(parse_corpus_list_params),
    pagination: PaginationParams = Depends(parse_pagination_params),
) -> CorpusListResponse:
    """List all corpora with optional filtering.

    Supports filtering by:
    - Language
    - Source type (custom, language, literature, wordlist)
    - Statistics inclusion
    """
    try:
        # Build filter query
        filter_query: dict[str, Any] = {}
        if params.language:
            filter_query["language"] = params.language.value
        if params.source_type:
            filter_query["corpus_type"] = params.source_type

        # Get corpus metadata documents
        query = Corpus.Metadata.find(filter_query)

        # Get total count
        total = await query.count()

        # Apply pagination
        corpus_docs = await query.skip(pagination.offset).limit(pagination.limit).to_list()

        # Load full corpus objects
        corpus_list = []
        manager = get_tree_corpus_manager()
        for doc in corpus_docs:
            try:
                corpus = await manager.get_corpus(corpus_id=doc.id)
                if corpus:
                    # Query SearchIndex to get actual index status
                    search_index = None
                    if corpus.corpus_uuid:
                        search_index = await SearchIndex.get(corpus_uuid=corpus.corpus_uuid)

                    corpus_data = {
                        "id": str(doc.id),
                        "name": corpus.corpus_name,
                        "language": corpus.language,
                        "corpus_type": corpus.corpus_type.value if corpus.corpus_type else "custom",
                        "vocabulary_size": len(corpus.vocabulary),
                        "unique_words": corpus.unique_word_count,
                        "has_semantic": search_index.has_semantic if search_index else False,
                        "created_at": doc.version_info.created_at,
                        "updated_at": doc.version_info.created_at,  # Use created_at for both until we add updated_at
                        "description": None,
                        "statistics": {
                            "vocabulary_hash": corpus.vocabulary_hash,
                            "is_master": corpus.is_master,
                            "child_count": len(corpus.child_uuids),
                        }
                        if params.include_stats
                        else {},
                    }
                    corpus_list.append(CorpusResponse(**corpus_data))
            except Exception as e:
                logger.warning(f"Failed to load corpus {doc.id}: {e}")
                continue

        return CorpusListResponse(
            items=corpus_list,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
            has_more=(pagination.offset + len(corpus_list)) < total,
        )

    except Exception as e:
        logger.error(f"Failed to list corpora: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list corpora: {e!s}")


@router.get("/corpus/stats")
async def get_corpus_stats() -> dict[str, Any]:
    """Get corpus cache statistics.

    Returns information about corpus cache usage, including active corpora count,
    total search count, and memory usage statistics.
    """
    try:
        # Query all corpus metadata from MongoDB
        all_metadata = await Corpus.Metadata.find_all().to_list()
        total_corpora = len(all_metadata)
        total_searches = sum(meta.search_count for meta in all_metadata)

        return {
            "status": "success",
            "cache": {
                "size": total_corpora,
                "cache_size": total_corpora,  # Alias for compatibility
                "max_size": 1000,  # Default max size
                "total_searches": total_searches,
            },
            "message": f"Corpus cache contains {total_corpora} active corpora with {total_searches} total searches",
        }
    except Exception as e:
        logger.error(f"Failed to get corpus stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get corpus stats: {e!s}")


@router.get("/corpus/{corpus_id}", response_model=CorpusResponse)
async def get_corpus(
    corpus_id: str = Path(..., description="Corpus ID"),
    include_stats: bool = Query(default=True, description="Include statistics"),
) -> CorpusResponse:
    """Get a specific corpus by ID."""
    try:
        # Parse ObjectId
        try:
            obj_id = PydanticObjectId(corpus_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid corpus ID format")

        # Load corpus
        manager = get_tree_corpus_manager()
        corpus = await manager.get_corpus(corpus_id=obj_id)
        if not corpus:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}")

        # Get metadata
        metadata = await Corpus.Metadata.get(obj_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Corpus metadata not found: {corpus_id}")

        # Check TTL expiration - corpora expire after their TTL
        ttl_hours = metadata.ttl_hours

        creation_time = metadata.version_info.created_at
        # Ensure creation_time has timezone info
        if creation_time.tzinfo is None:
            creation_time = creation_time.replace(tzinfo=UTC)

        expires_at = creation_time + timedelta(hours=ttl_hours)
        now = datetime.now(UTC)

        # If corpus has expired, return 404
        if now > expires_at:
            raise HTTPException(status_code=404, detail=f"Corpus expired: {corpus_id}")

        # Query SearchIndex to get actual index status
        search_index = None
        if corpus.corpus_uuid:
            search_index = await SearchIndex.get(corpus_uuid=corpus.corpus_uuid)

        stats_dict = {
            "vocabulary_hash": corpus.vocabulary_hash,
            "is_master": corpus.is_master,
            "child_count": len(corpus.child_uuids),
            "parent_id": corpus.parent_uuid,
            "has_trie": search_index.has_trie if search_index else False,
            "ttl_hours": metadata.ttl_hours,
            "search_count": metadata.search_count,
        } if include_stats else {}

        corpus_data = {
            "id": corpus_id,
            "name": corpus.corpus_name,
            "language": corpus.language,
            "corpus_type": corpus.corpus_type.value if corpus.corpus_type else "custom",
            "vocabulary_size": len(corpus.vocabulary),
            "unique_words": corpus.unique_word_count,
            "has_semantic": search_index.has_semantic if search_index else False,
            "created_at": metadata.version_info.created_at,
            "updated_at": metadata.version_info.created_at,  # Use created_at for both until we add updated_at
            "description": None,
            "statistics": stats_dict,
        }

        return CorpusResponse(**corpus_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get corpus {corpus_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get corpus: {e!s}")


@router.post("/corpus", response_model=CorpusResponse, status_code=201)
async def create_corpus(
    params: CorpusCreateParams,
) -> CorpusResponse:
    """Create a new corpus.

    Supports:
    - Custom vocabulary
    - Language-specific corpus
    - Literature-based corpus
    - Optional semantic indexing
    """
    try:
        manager = get_tree_corpus_manager()

        # Parse corpus type
        corpus_type_map = {
            "custom": CorpusType.CUSTOM,
            "language": CorpusType.LANGUAGE,
            "literature": CorpusType.LITERATURE,
            "wordlist": CorpusType.WORDLIST,
        }
        corpus_type = corpus_type_map.get(params.source_type.lower(), CorpusType.CUSTOM)

        # Create corpus
        corpus = await Corpus.create(
            vocabulary=params.vocabulary,
            corpus_name=params.name,
            language=params.language,
            semantic=params.enable_semantic,
        )

        # Set corpus type after creation
        corpus.corpus_type = corpus_type

        # Save corpus
        corpus = await manager.save_corpus(corpus)

        if not corpus.corpus_id:
            raise HTTPException(status_code=500, detail="Failed to save corpus")

        # Get metadata and persist TTL
        metadata = await Corpus.Metadata.get(corpus.corpus_id)
        if not metadata:
            raise HTTPException(status_code=500, detail="Failed to retrieve corpus metadata")

        # Persist TTL to MongoDB
        metadata.ttl_hours = params.ttl_hours
        metadata.search_count = 0
        await metadata.save()

        # Query SearchIndex to get actual index status
        search_index = None
        if corpus.corpus_uuid:
            search_index = await SearchIndex.get(corpus_uuid=corpus.corpus_uuid)

        corpus_data = {
            "id": str(corpus.corpus_id),
            "name": corpus.corpus_name,
            "language": corpus.language,
            "corpus_type": corpus.corpus_type.value if corpus.corpus_type else "custom",
            "vocabulary_size": len(corpus.vocabulary),
            "unique_words": corpus.unique_word_count,
            "has_semantic": search_index.has_semantic if search_index else False,
            "created_at": metadata.version_info.created_at,
            "updated_at": metadata.version_info.created_at,  # Use created_at for both until we add updated_at
            "description": params.description,
            "statistics": {
                "vocabulary_hash": corpus.vocabulary_hash,
                "is_master": corpus.is_master,
                "ttl_hours": params.ttl_hours,
                "search_count": 0,
            },
        }

        return CorpusResponse(**corpus_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create corpus: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create corpus: {e!s}")


@router.post("/corpus/{corpus_id}/search")
async def search_within_corpus(
    corpus_id: str = Path(..., description="Corpus ID"),
    query: str = Query(..., description="Search query"),
    max_results: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0.6, ge=0.0, le=1.0),
) -> dict[str, Any]:
    """Search for words within a specific corpus."""
    try:
        # Parse ObjectId - return 400 for invalid format
        try:
            obj_id = PydanticObjectId(corpus_id)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid corpus ID format: {corpus_id}")

        # Load corpus
        manager = get_tree_corpus_manager()
        corpus = await manager.get_corpus(corpus_id=obj_id)
        if not corpus:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}")

        # Atomically increment search count in MongoDB
        await Corpus.Metadata.find_one(
            Corpus.Metadata.id == obj_id,
        ).update({"$inc": {"search_count": 1}, "$set": {"last_accessed": datetime.now(UTC)}})

        # Create search index for this corpus
        index = await SearchIndex.get_or_create(
            corpus=corpus,
            semantic=False,
            config=VersionConfig(use_cache=True),
        )

        # Create search engine from index
        search_engine = Search(index=index, corpus=corpus)
        await search_engine.initialize()

        # Perform smart search (cascade)
        results = await search_engine.search_with_mode(
            query=query,
            mode=SearchMode.SMART,
            max_results=max_results,
            min_score=min_score,
        )

        # Format results
        result_list = []
        for result in results:
            result_list.append(
                {
                    "word": result.word,
                    "score": result.score,
                    "method": result.method.value if result.method else "unknown",
                }
            )

        return {
            "results": result_list,
            "metadata": {
                "query": query,
                "corpus_id": corpus_id,
                "corpus_name": corpus.corpus_name,
                "total": len(result_list),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search corpus {corpus_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search corpus: {e!s}")


@router.delete("/corpus/{corpus_id}")
async def delete_corpus(
    corpus_id: str = Path(..., description="Corpus ID"),
    cascade: bool = Query(default=False, description="Delete child corpora"),
) -> dict[str, Any]:
    """Delete a corpus.

    Use cascade=true to also delete child corpora.
    """
    try:
        manager = get_tree_corpus_manager()

        # Parse ObjectId
        try:
            obj_id = PydanticObjectId(corpus_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid corpus ID format")

        # Check if corpus exists
        manager = get_tree_corpus_manager()
        corpus = await manager.get_corpus(corpus_id=obj_id)
        if not corpus:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}")

        # Delete corpus
        success = await manager.delete_corpus(
            corpus_id=obj_id,
            cascade=cascade,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete corpus")

        return {
            "status": "success",
            "message": f"Corpus {corpus_id} deleted successfully",
            "cascade": cascade,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete corpus {corpus_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete corpus: {e!s}")
