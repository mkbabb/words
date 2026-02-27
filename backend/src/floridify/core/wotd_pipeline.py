"""WOTD ML Pipeline - Core business logic for Word of the Day machine learning system."""

import json
import logging
from pathlib import Path
from typing import Any

from ..utils.paths import get_cache_directory
from ..wotd import WOTDPipeline
from ..wotd.inference import create_pipeline

logger = logging.getLogger(__name__)

# Global pipeline instance cache
_pipeline_cache: WOTDPipeline | None = None


def get_wotd_models_directory() -> Path:
    """Get directory for WOTD models using path utilities."""
    return get_cache_directory("wotd_models")


def get_ml_pipeline() -> WOTDPipeline:
    """Get or initialize the ML pipeline.

    This function manages the global pipeline instance and handles
    model loading from the standardized cache directory.

    Returns:
        Initialized WOTDPipeline ready for inference.

    Raises:
        RuntimeError: If models are not available or failed to load.

    """
    global _pipeline_cache

    if _pipeline_cache is None:
        # Get models directory using path utilities
        models_dir = get_wotd_models_directory()
        encoder_path = models_dir / "semantic_encoder.pt"
        dsl_model_path = models_dir / "dsl_model"
        semantic_ids_path = models_dir / "semantic_ids.json"

        if not encoder_path.exists():
            raise RuntimeError(
                f"Semantic encoder model not found at {encoder_path}. "
                "Run training pipeline first: python -m floridify.wotd.train",
            )

        if not dsl_model_path.exists() or not dsl_model_path.is_dir():
            raise RuntimeError(
                f"DSL model not found at {dsl_model_path}. "
                "Run training pipeline first: python -m floridify.wotd.train",
            )

        if not semantic_ids_path.exists():
            raise RuntimeError(
                f"Semantic IDs vocabulary not found at {semantic_ids_path}. "
                "Run training pipeline first: python -m floridify.wotd.train",
            )

        try:
            # Load semantic IDs
            with open(semantic_ids_path) as f:
                semantic_ids = json.load(f)

            # Create pipeline
            _pipeline_cache = create_pipeline(str(encoder_path), str(dsl_model_path), semantic_ids)

        except Exception as e:
            raise RuntimeError(f"Failed to load ML models: {e}")

    return _pipeline_cache


def reload_ml_pipeline() -> WOTDPipeline:
    """Force reload of the ML pipeline from disk.

    Useful after retraining models or updating the model files.
    Clears the global cache and reloads fresh models.

    Returns:
        Newly loaded WOTDPipeline instance.

    Raises:
        RuntimeError: If models are not available or failed to load.

    """
    global _pipeline_cache
    _pipeline_cache = None
    return get_ml_pipeline()


def get_wotd_training_config() -> dict[str, Any]:
    """Get WOTD training configuration with proper paths.

    Returns configuration for training pipeline using
    standardized path utilities.

    Returns:
        Dictionary with training configuration paths and settings.

    """
    models_dir = get_wotd_models_directory()

    return {
        "models_directory": str(models_dir),
        "encoder_path": str(models_dir / "semantic_encoder.pt"),
        "dsl_model_path": str(models_dir / "dsl_model"),
        "semantic_ids_path": str(models_dir / "semantic_ids.json"),
        "metadata_path": str(models_dir / "training_metadata.json"),
        "training_data_path": str(models_dir / "training_data"),
        "encoder_epochs": 100,
        "dsl_epochs": 10,
        "batch_size": 4,
    }


def check_wotd_models_status() -> dict[str, Any]:
    """Check the status of WOTD models and training infrastructure.

    Returns detailed information about model availability,
    training status, and system readiness.

    Returns:
        Dictionary with comprehensive model status information.

    """
    models_dir = get_wotd_models_directory()
    encoder_path = models_dir / "semantic_encoder.pt"
    dsl_model_path = models_dir / "dsl_model"
    semantic_ids_path = models_dir / "semantic_ids.json"
    metadata_path = models_dir / "training_metadata.json"

    # Check model files
    model_status = {
        "semantic_encoder": encoder_path.exists(),
        "dsl_model": dsl_model_path.exists() and dsl_model_path.is_dir(),
        "semantic_ids": semantic_ids_path.exists(),
        "metadata": metadata_path.exists(),
    }

    # Overall pipeline availability
    pipeline_available = all(
        [model_status["semantic_encoder"], model_status["dsl_model"], model_status["semantic_ids"]],
    )

    # Load metadata if available
    training_info = {}
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                training_info = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse training metadata: {e}")
            raise ValueError(f"Invalid training metadata JSON: {e}")
        except OSError as e:
            logger.error(f"Failed to read training metadata file: {e}")
            raise ValueError(f"Cannot read training metadata: {e}")

    # Check if pipeline is loaded in memory
    global _pipeline_cache
    pipeline_loaded = _pipeline_cache is not None

    return {
        "pipeline_available": pipeline_available,
        "pipeline_loaded": pipeline_loaded,
        "model_files": model_status,
        "models_directory": str(models_dir),
        "training_info": training_info,
        "ready_for_inference": pipeline_available and pipeline_loaded,
        "file_paths": {
            "encoder": str(encoder_path),
            "dsl_model": str(dsl_model_path),
            "semantic_ids": str(semantic_ids_path),
            "metadata": str(metadata_path),
        },
    }


def prepare_wotd_training_environment() -> dict[str, str]:
    """Prepare the training environment with proper directory structure.

    Creates necessary directories and returns paths for training pipeline.

    Returns:
        Dictionary with prepared training paths.

    """
    models_dir = get_wotd_models_directory()
    training_data_dir = models_dir / "training_data"

    # Ensure directories exist
    models_dir.mkdir(parents=True, exist_ok=True)
    training_data_dir.mkdir(parents=True, exist_ok=True)

    return {
        "models_directory": str(models_dir),
        "training_data_directory": str(training_data_dir),
        "encoder_output": str(models_dir / "semantic_encoder.pt"),
        "dsl_model_output": str(models_dir / "dsl_model"),
        "semantic_ids_output": str(models_dir / "semantic_ids.json"),
        "metadata_output": str(models_dir / "training_metadata.json"),
    }


# Convenience functions for common operations


def get_semantic_vocabulary() -> dict[str, list[int]]:
    """Get the learned semantic vocabulary.

    Returns:
        Dictionary mapping corpus names to semantic IDs.

    Raises:
        RuntimeError: If pipeline is not available.

    """
    pipeline = get_ml_pipeline()
    return pipeline.get_semantic_ids()


def generate_words_from_prompt(
    prompt: str,
    num_words: int = 10,
    temperature: float = 0.8,
) -> dict[str, Any]:
    """Generate words using the ML pipeline.

    Convenience function for word generation with error handling.

    Args:
        prompt: Natural language or DSL prompt
        num_words: Number of words to generate
        temperature: Sampling temperature

    Returns:
        Generation result with words and metadata.

    Raises:
        RuntimeError: If generation fails or pipeline unavailable.

    """
    try:
        pipeline = get_ml_pipeline()
        result = pipeline.generate(prompt, num_words, temperature)

        return {
            "words": result.words,
            "semantic_id": result.semantic_id,
            "clean_prompt": result.clean_prompt,
            "description": result.description,
            "processing_time": result.processing_time,
            "metadata": result.metadata,
        }

    except Exception as e:
        raise RuntimeError(f"Word generation failed: {e}")


def interpolate_corpus_preferences(
    corpus1: str,
    corpus2: str,
    alpha: float = 0.5,
    context: str | None = None,
    num_words: int = 10,
) -> dict[str, Any]:
    """Interpolate between two corpus preferences.

    Convenience function for semantic interpolation with error handling.

    Args:
        corpus1: First corpus name
        corpus2: Second corpus name
        alpha: Interpolation weight (0.0 to 1.0)
        context: Optional context for generation
        num_words: Number of words to generate

    Returns:
        Generation result with interpolated preferences.

    Raises:
        RuntimeError: If interpolation fails or corpus names invalid.

    """
    try:
        pipeline = get_ml_pipeline()
        result = pipeline.interpolate_generate(corpus1, corpus2, alpha, context, num_words)

        return {
            "words": result.words,
            "semantic_id": result.semantic_id,
            "clean_prompt": result.clean_prompt,
            "description": f"interpolation: {corpus1} + {corpus2} (α={alpha})",
            "processing_time": result.processing_time,
            "metadata": {
                **result.metadata,
                "interpolation": {"corpus1": corpus1, "corpus2": corpus2, "alpha": alpha},
            },
        }

    except KeyError as e:
        raise RuntimeError(f"Invalid corpus name: {e}")
    except Exception as e:
        raise RuntimeError(f"Interpolation failed: {e}")


def get_pipeline_health() -> dict[str, Any]:
    """Get comprehensive health status of the WOTD ML system.

    Returns:
        Complete health check including models, memory usage, and capabilities.

    """
    try:
        status = check_wotd_models_status()

        # If pipeline is loaded, get additional info
        if status["pipeline_loaded"]:
            try:
                vocabulary = get_semantic_vocabulary()
                status["vocabulary_size"] = len(vocabulary)
                status["available_corpora"] = list(vocabulary.keys())
            except Exception as e:
                logger.error(f"Failed to retrieve vocabulary from pipeline: {e}", exc_info=True)
                status["vocabulary_error"] = str(e)

        return status

    except Exception as e:
        return {
            "error": str(e),
            "pipeline_available": False,
            "pipeline_loaded": False,
            "ready_for_inference": False,
        }
