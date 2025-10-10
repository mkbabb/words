"""Corpus management endpoints."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ...corpus.core import Corpus
from ...corpus.manager import get_tree_corpus_manager
from ...corpus.models import CorpusType
from ...models.base import Language
from ...models.parameters import CorpusCreateParams, CorpusListParams, PaginationParams
from ...models.responses import CorpusListResponse, CorpusResponse
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
        except ValueError:
            pass

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
        from ...corpus.core import Corpus

        query = Corpus.Metadata.find(filter_query)

        # Get total count
        total = await query.count()

        # Apply pagination
        corpus_docs = await query.skip(pagination.offset).limit(pagination.limit).to_list()

        # Load full corpus objects
        corpus_list = []
        for doc in corpus_docs:
            try:
                corpus = await Corpus.get(corpus_id=doc.id)
                if corpus:
                    corpus_data = {
                        "id": str(doc.id),
                        "name": corpus.corpus_name,
                        "language": corpus.language,
                        "corpus_type": corpus.corpus_type.value if corpus.corpus_type else "custom",
                        "vocabulary_size": len(corpus.vocabulary),
                        "unique_words": corpus.unique_word_count,
                        "has_semantic": corpus.semantic_index_id is not None,
                        "created_at": doc.created_at,
                        "updated_at": doc.last_updated,
                        "description": None,
                        "statistics": {
                            "vocabulary_hash": corpus.vocabulary_hash,
                            "is_master": corpus.is_master,
                            "child_count": len(corpus.child_corpus_ids),
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
        corpus = await Corpus.get(corpus_id=obj_id)
        if not corpus:
            raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}")

        # Get metadata
        metadata = await Corpus.Metadata.get(obj_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Corpus metadata not found: {corpus_id}")

        corpus_data = {
            "id": corpus_id,
            "name": corpus.corpus_name,
            "language": corpus.language,
            "corpus_type": corpus.corpus_type.value if corpus.corpus_type else "custom",
            "vocabulary_size": len(corpus.vocabulary),
            "unique_words": corpus.unique_word_count,
            "has_semantic": corpus.semantic_index_id is not None,
            "created_at": metadata.created_at,
            "updated_at": metadata.last_updated,
            "description": None,
            "statistics": {
                "vocabulary_hash": corpus.vocabulary_hash,
                "is_master": corpus.is_master,
                "child_count": len(corpus.child_corpus_ids),
                "parent_id": str(corpus.parent_corpus_id) if corpus.parent_corpus_id else None,
                "has_trie": corpus.trie_index_id is not None,
            }
            if include_stats
            else {},
        }

        return CorpusResponse(**corpus_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get corpus {corpus_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get corpus: {e!s}")


@router.post("/corpus", response_model=CorpusResponse)
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

        # Get metadata
        metadata = await Corpus.Metadata.get(corpus.corpus_id)
        if not metadata:
            raise HTTPException(status_code=500, detail="Failed to retrieve corpus metadata")

        corpus_data = {
            "id": str(corpus.corpus_id),
            "name": corpus.corpus_name,
            "language": corpus.language,
            "corpus_type": corpus.corpus_type.value if corpus.corpus_type else "custom",
            "vocabulary_size": len(corpus.vocabulary),
            "unique_words": corpus.unique_word_count,
            "has_semantic": corpus.semantic_index_id is not None,
            "created_at": metadata.created_at,
            "updated_at": metadata.last_updated,
            "description": params.description,
            "statistics": {
                "vocabulary_hash": corpus.vocabulary_hash,
                "is_master": corpus.is_master,
            },
        }

        return CorpusResponse(**corpus_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create corpus: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create corpus: {e!s}")


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
        corpus = await Corpus.get(corpus_id=obj_id)
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
