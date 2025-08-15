"""WOTD ML API - Advanced preference learning and semantic word generation."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ....core.wotd_pipeline import (
    generate_words_from_prompt,
    get_ml_pipeline,
    get_pipeline_health,
    get_semantic_vocabulary,
    interpolate_corpus_preferences,
    reload_ml_pipeline,
)
from ....wotd.semantic_encoder import SemanticID, describe_semantic_id, similarity_score
from ...core import ListResponse, ResourceResponse

router = APIRouter(tags=["WOTD ML"])


class WOTDGenerationRequest(BaseModel):
    """Request model for WOTD word generation."""

    prompt: str = Field(
        description="Natural language or DSL prompt like 'Generate [0,0,*,*] words'",
    )
    num_words: int = Field(default=10, ge=1, le=50, description="Number of words to generate")
    temperature: float = Field(default=0.8, ge=0.1, le=2.0, description="Sampling temperature")


class WOTDGenerationResponse(BaseModel):
    """Response model for WOTD word generation."""

    words: list[str] = Field(description="Generated words")
    semantic_id: SemanticID | None = Field(description="Parsed semantic ID if DSL was used")
    clean_prompt: str = Field(description="Prompt with DSL syntax removed")
    description: str = Field(description="Human-readable description of semantic preferences")
    processing_time: float = Field(description="Time taken to generate words in seconds")
    metadata: dict[str, Any] = Field(description="Additional generation metadata")


class WOTDInterpolationRequest(BaseModel):
    """Request model for semantic ID interpolation."""

    corpus1: str = Field(description="First corpus name for interpolation")
    corpus2: str = Field(description="Second corpus name for interpolation")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Interpolation weight")
    context: str | None = Field(default=None, description="Optional context for generation")
    num_words: int = Field(default=10, ge=1, le=50, description="Number of words to generate")


@router.post("/generate", response_model=WOTDGenerationResponse)
async def generate_words(request: WOTDGenerationRequest) -> WOTDGenerationResponse:
    """Generate words using ML pipeline with preference learning.

    This endpoint supports both natural language prompts and DSL syntax:
    - Natural: "Generate beautiful classical words"
    - DSL: "Generate [0,0,*,*] words" (where [level0,level1,level2,level3])
    - Mixed: "Generate [0,*,*,*] words about nature"

    The DSL uses hierarchical semantic IDs:
    - Level 0: Style (0=classical, 1=modern, 2=romantic, 3=neutral)
    - Level 1: Complexity (0=beautiful, 1=simple, 2=complex, 3=plain)
    - Level 2: Era (0=shakespearean, 1=victorian, 2=modernist, 3=contemporary)
    - Level 3: Learned variations
    - Wildcards (*) allow flexibility in that dimension

    Returns:
        Generated words with semantic analysis and metadata.

    Errors:
        503: ML models not available
        500: Generation failed

    """
    try:
        result = generate_words_from_prompt(request.prompt, request.num_words, request.temperature)

        return WOTDGenerationResponse(
            words=result["words"],
            semantic_id=result["semantic_id"],
            clean_prompt=result["clean_prompt"],
            description=result["description"],
            processing_time=result["processing_time"],
            metadata=result["metadata"],
        )

    except RuntimeError as e:
        if "not found" in str(e).lower() or "run training" in str(e).lower():
            raise HTTPException(503, str(e))
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {e}")


@router.post("/interpolate", response_model=WOTDGenerationResponse)
async def interpolate_generate(request: WOTDInterpolationRequest) -> WOTDGenerationResponse:
    """Generate words by interpolating between two learned corpus preferences.

    This creates novel combinations by blending the semantic characteristics
    of two different word corpora in the vector space.

    For example:
    - corpus1="shakespeare", corpus2="modern", alpha=0.3
      → 70% shakespearean, 30% modern style
    - corpus1="beautiful", corpus2="simple", alpha=0.5
      → Balanced between beautiful and simple preferences

    Args:
        request: Interpolation parameters including corpus names and blend ratio

    Returns:
        Generated words from the interpolated preference space.

    Errors:
        400: Invalid corpus names
        503: ML models not available
        500: Interpolation failed

    """
    try:
        result = interpolate_corpus_preferences(
            request.corpus1,
            request.corpus2,
            request.alpha,
            request.context,
            request.num_words,
        )

        return WOTDGenerationResponse(
            words=result["words"],
            semantic_id=result["semantic_id"],
            clean_prompt=result["clean_prompt"],
            description=result["description"],
            processing_time=result["processing_time"],
            metadata=result["metadata"],
        )

    except RuntimeError as e:
        if "Invalid corpus" in str(e):
            raise HTTPException(400, str(e))
        if "not found" in str(e).lower() or "run training" in str(e).lower():
            raise HTTPException(503, str(e))
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {e}")


@router.get("/semantic-ids", response_model=ListResponse[dict[str, Any]])
async def list_semantic_ids() -> ListResponse[dict[str, Any]]:
    """List all learned semantic IDs and their meanings.

    Returns the vocabulary of learned preference vectors and their
    corresponding hierarchical discrete codes.

    Returns:
        List of semantic IDs with human-readable descriptions.

    Errors:
        503: ML models not available
        500: Failed to retrieve semantic IDs

    """
    try:
        semantic_ids = get_semantic_vocabulary()

        items = []
        for name, semantic_id in semantic_ids.items():
            description = describe_semantic_id(semantic_id)
            items.append(
                {
                    "name": name,
                    "semantic_id": semantic_id,
                    "description": description,
                    "dsl_syntax": f"[{','.join(map(str, semantic_id))}]",
                },
            )

        return ListResponse(items=items, total=len(items), offset=0, limit=len(items))

    except RuntimeError as e:
        if "not found" in str(e).lower() or "run training" in str(e).lower():
            raise HTTPException(503, str(e))
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to retrieve semantic IDs: {e}")


@router.get("/semantic-ids/{name}/similar")
async def find_similar_semantic_ids(name: str, threshold: float = 0.5) -> ResourceResponse:
    """Find semantic IDs similar to the given name.

    Uses hierarchical similarity scoring to find semantically related
    preference vectors based on their discrete code structure.

    Args:
        name: Name of the reference semantic ID
        threshold: Minimum similarity score (0.0 to 1.0)

    Returns:
        List of similar semantic IDs with similarity scores.

    Errors:
        404: Semantic ID not found
        503: ML models not available
        500: Similarity computation failed

    """
    try:
        semantic_ids = get_semantic_vocabulary()

        if name not in semantic_ids:
            raise HTTPException(404, f"Semantic ID '{name}' not found")

        reference_id = semantic_ids[name]
        similar_ids = []

        for other_name, other_id in semantic_ids.items():
            if other_name == name:
                continue

            similarity = similarity_score(reference_id, other_id)
            if similarity >= threshold:
                similar_ids.append(
                    {
                        "name": other_name,
                        "semantic_id": other_id,
                        "similarity": similarity,
                        "description": describe_semantic_id(other_id),
                        "dsl_syntax": f"[{','.join(map(str, other_id))}]",
                    },
                )

        # Sort by similarity descending
        similar_ids.sort(key=lambda x: x["similarity"], reverse=True)

        return ResourceResponse(
            data={
                "reference": {
                    "name": name,
                    "semantic_id": reference_id,
                    "description": describe_semantic_id(reference_id),
                },
                "similar_ids": similar_ids,
            },
            metadata={
                "threshold": threshold,
                "total_similar": len(similar_ids),
                "max_similarity": max([s["similarity"] for s in similar_ids]) if similar_ids else 0,
            },
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        if "not found" in str(e).lower() or "run training" in str(e).lower():
            raise HTTPException(503, str(e))
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Similarity search failed: {e}")


@router.get("/models/status")
async def get_models_status() -> ResourceResponse:
    """Get status of ML models and training pipeline.

    Returns information about available models, training status,
    and system capabilities.

    Returns:
        Model status and system information.

    """
    try:
        health_info = get_pipeline_health()

        return ResourceResponse(
            data=health_info,
            metadata={"checked_at": datetime.now(), "health_check_version": "1.0"},
        )

    except Exception as e:
        return ResourceResponse(
            data={
                "error": str(e),
                "pipeline_available": False,
                "pipeline_loaded": False,
                "ready_for_inference": False,
            },
            metadata={"checked_at": datetime.now(), "error_occurred": True},
        )


@router.post("/models/reload")
async def reload_models() -> ResourceResponse:
    """Reload ML models from disk.

    Forces reloading of the pipeline and models, useful after
    retraining or model updates.

    Returns:
        Reload status and new model information.

    Errors:
        503: Models not available
        500: Reload failed

    """
    try:
        # Force reload pipeline
        pipeline = reload_ml_pipeline()

        # Get fresh semantic IDs
        semantic_ids = pipeline.get_semantic_ids()

        return ResourceResponse(
            data={
                "reload_successful": True,
                "semantic_ids_count": len(semantic_ids),
                "available_corpora": list(semantic_ids.keys()),
                "pipeline_ready": True,
            },
            metadata={"reloaded_at": datetime.now(), "reload_version": "1.0"},
        )

    except RuntimeError as e:
        if "not found" in str(e).lower() or "run training" in str(e).lower():
            raise HTTPException(503, str(e))
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Model reload failed: {e}")


# Dependency function for pipeline access
async def get_wotd_pipeline():
    """FastAPI dependency to get WOTD pipeline with proper error handling."""
    try:
        return get_ml_pipeline()
    except RuntimeError as e:
        if "not found" in str(e).lower() or "run training" in str(e).lower():
            raise HTTPException(503, str(e))
        raise HTTPException(500, str(e))
