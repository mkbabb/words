"""ML-Powered Word of the Day API - Advanced preference learning system."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ....wotd import WOTDPipeline
from ....wotd.inference import create_pipeline
from ....wotd.semantic_encoder import SemanticID, describe_semantic_id, similarity_score
from ...core import ResourceResponse, ListResponse

router = APIRouter(prefix="/ml", tags=["ML Word of the Day"])


class MLWordGenerationRequest(BaseModel):
    """Request model for ML word generation."""
    
    prompt: str = Field(description="Natural language or DSL prompt like 'Generate [0,0,*,*] words'")
    num_words: int = Field(default=10, ge=1, le=50, description="Number of words to generate")
    context: str = Field(default="words", description="Context for generation")


class MLWordGenerationResponse(BaseModel):
    """Response model for ML word generation."""
    
    words: list[str] = Field(description="Generated words")
    semantic_id: SemanticID | None = Field(description="Parsed semantic ID if DSL was used")
    clean_prompt: str = Field(description="Prompt with DSL syntax removed")
    description: str = Field(description="Human-readable description of semantic preferences")
    processing_time: float = Field(description="Time taken to generate words in seconds")
    metadata: dict[str, Any] = Field(description="Additional generation metadata")


class MLInterpolationRequest(BaseModel):
    """Request model for semantic ID interpolation."""
    
    corpus1: str = Field(description="First corpus name for interpolation")
    corpus2: str = Field(description="Second corpus name for interpolation") 
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Interpolation weight")
    context: str = Field(default="words", description="Context for generation")
    num_words: int = Field(default=10, ge=1, le=50, description="Number of words to generate")


# Global pipeline instance (would be initialized at startup)
_pipeline_cache: WOTDPipeline | None = None


async def get_ml_pipeline() -> WOTDPipeline:
    """Get or initialize the ML pipeline."""
    global _pipeline_cache
    
    if _pipeline_cache is None:
        # Try to load from models directory
        models_dir = Path("models/wotd")
        encoder_path = models_dir / "semantic_encoder.pt"
        dsl_model_path = models_dir / "dsl_model"
        semantic_ids_path = models_dir / "semantic_ids.json"
        
        if encoder_path.exists() and dsl_model_path.exists() and semantic_ids_path.exists():
            # Load semantic IDs
            with open(semantic_ids_path) as f:
                semantic_ids = json.load(f)
            
            # Create pipeline
            _pipeline_cache = create_pipeline(
                str(encoder_path),
                str(dsl_model_path),
                semantic_ids
            )
        else:
            raise HTTPException(
                503, 
                "ML models not available. Run training pipeline first: python -m floridify.wotd.train"
            )
    
    return _pipeline_cache


@router.post("/generate", response_model=MLWordGenerationResponse)
async def generate_words_ml(
    request: MLWordGenerationRequest,
    pipeline: WOTDPipeline = Depends(get_ml_pipeline)
) -> MLWordGenerationResponse:
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
        result = pipeline.generate(request.prompt, request.num_words)
        
        # Get description of semantic ID if available
        description = "natural language"
        if result.semantic_id:
            description = describe_semantic_id(result.semantic_id)
        
        return MLWordGenerationResponse(
            words=result.words,
            semantic_id=result.semantic_id,
            clean_prompt=result.clean_prompt,
            description=description,
            processing_time=result.processing_time,
            metadata=result.metadata
        )
        
    except Exception as e:
        raise HTTPException(500, f"Word generation failed: {e}")


@router.post("/interpolate", response_model=MLWordGenerationResponse)
async def interpolate_generate(
    request: MLInterpolationRequest,
    pipeline: WOTDPipeline = Depends(get_ml_pipeline)
) -> MLWordGenerationResponse:
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
        result = pipeline.interpolate_generate(
            request.corpus1,
            request.corpus2,
            request.alpha,
            request.context,
            request.num_words
        )
        
        description = f"interpolation: {request.corpus1} + {request.corpus2} (α={request.alpha})"
        
        return MLWordGenerationResponse(
            words=result.words,
            semantic_id=result.semantic_id,
            clean_prompt=result.clean_prompt,
            description=description,
            processing_time=result.processing_time,
            metadata={
                **result.metadata,
                "interpolation": {
                    "corpus1": request.corpus1,
                    "corpus2": request.corpus2,
                    "alpha": request.alpha
                }
            }
        )
        
    except KeyError as e:
        raise HTTPException(400, f"Invalid corpus name: {e}")
    except Exception as e:
        raise HTTPException(500, f"Interpolation failed: {e}")


@router.get("/semantic-ids", response_model=ListResponse[dict[str, Any]])
async def list_semantic_ids(
    pipeline: WOTDPipeline = Depends(get_ml_pipeline)
) -> ListResponse[dict[str, Any]]:
    """List all learned semantic IDs and their meanings.
    
    Returns the vocabulary of learned preference vectors and their
    corresponding hierarchical discrete codes.
    
    Returns:
        List of semantic IDs with human-readable descriptions.
    """
    try:
        semantic_ids = pipeline.get_semantic_ids()
        
        items = []
        for name, semantic_id in semantic_ids.items():
            description = describe_semantic_id(semantic_id)
            items.append({
                "name": name,
                "semantic_id": semantic_id,
                "description": description,
                "dsl_syntax": f"[{','.join(map(str, semantic_id))}]"
            })
        
        return ListResponse(
            items=items,
            total=len(items),
            offset=0,
            limit=len(items)
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to retrieve semantic IDs: {e}")


@router.get("/semantic-ids/{name}/similar")
async def find_similar_semantic_ids(
    name: str,
    threshold: float = Query(0.5, ge=0.0, le=1.0, description="Similarity threshold"),
    pipeline: WOTDPipeline = Depends(get_ml_pipeline)
) -> ResourceResponse:
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
        500: Similarity computation failed
    """
    try:
        semantic_ids = pipeline.get_semantic_ids()
        
        if name not in semantic_ids:
            raise HTTPException(404, f"Semantic ID '{name}' not found")
        
        reference_id = semantic_ids[name]
        similar_ids = []
        
        for other_name, other_id in semantic_ids.items():
            if other_name == name:
                continue
                
            similarity = similarity_score(reference_id, other_id)
            if similarity >= threshold:
                similar_ids.append({
                    "name": other_name,
                    "semantic_id": other_id,
                    "similarity": similarity,
                    "description": describe_semantic_id(other_id),
                    "dsl_syntax": f"[{','.join(map(str, other_id))}]"
                })
        
        # Sort by similarity descending
        similar_ids.sort(key=lambda x: x["similarity"], reverse=True)
        
        return ResourceResponse(
            data={
                "reference": {
                    "name": name,
                    "semantic_id": reference_id,
                    "description": describe_semantic_id(reference_id)
                },
                "similar_ids": similar_ids
            },
            metadata={
                "threshold": threshold,
                "total_similar": len(similar_ids),
                "max_similarity": max([s["similarity"] for s in similar_ids]) if similar_ids else 0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Similarity search failed: {e}")


@router.get("/models/status")
async def get_model_status() -> ResourceResponse:
    """Get status of ML models and training pipeline.
    
    Returns information about available models, training status,
    and system capabilities.
    
    Returns:
        Model status and system information.
    """
    models_dir = Path("models/wotd")
    encoder_path = models_dir / "semantic_encoder.pt"
    dsl_model_path = models_dir / "dsl_model"
    semantic_ids_path = models_dir / "semantic_ids.json"
    metadata_path = models_dir / "training_metadata.json"
    
    # Check model files
    model_status = {
        "semantic_encoder": encoder_path.exists(),
        "dsl_model": dsl_model_path.exists() and dsl_model_path.is_dir(),
        "semantic_ids": semantic_ids_path.exists(),
        "metadata": metadata_path.exists()
    }
    
    pipeline_available = all([
        model_status["semantic_encoder"],
        model_status["dsl_model"],
        model_status["semantic_ids"]
    ])
    
    # Load metadata if available
    training_info = {}
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                training_info = json.load(f)
        except Exception:
            pass
    
    # Check if pipeline is loaded
    global _pipeline_cache
    pipeline_loaded = _pipeline_cache is not None
    
    return ResourceResponse(
        data={
            "pipeline_available": pipeline_available,
            "pipeline_loaded": pipeline_loaded,
            "model_files": model_status,
            "models_directory": str(models_dir),
            "training_info": training_info
        },
        metadata={
            "checked_at": datetime.now(),
            "ready_for_inference": pipeline_available and pipeline_loaded
        }
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
    global _pipeline_cache
    
    try:
        # Clear cache to force reload
        _pipeline_cache = None
        
        # Try to load new pipeline
        pipeline = await get_ml_pipeline()
        
        semantic_ids = pipeline.get_semantic_ids()
        
        return ResourceResponse(
            data={
                "reload_successful": True,
                "semantic_ids_count": len(semantic_ids),
                "available_corpora": list(semantic_ids.keys())
            },
            metadata={
                "reloaded_at": datetime.now(),
                "pipeline_ready": True
            }
        )
        
    except Exception as e:
        # Reset cache state
        _pipeline_cache = None
        raise HTTPException(500, f"Model reload failed: {e}")