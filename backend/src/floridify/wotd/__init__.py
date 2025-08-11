"""Word of the Day ML System - Clean, Independent, Performance-Focused."""

from .core import (
    Author,
    Complexity,
    Era,
    GenerateRequest,
    GenerateResponse,
    Style,
    TrainingConfig,
    TrainingResults,
    WOTDCorpus,
    WOTDWord,
)
from .generator import SyntheticGenerator, generate_training_data
from .sagemaker import SageMakerDeployer, deploy_complete_wotd_pipeline
from .storage import WOTDStorage, get_wotd_storage
from .trainer import WOTDTrainer, train_wotd_pipeline

__all__ = [
    # Core types
    "Author",
    "Style",
    "Complexity", 
    "Era",
    "WOTDWord",
    "WOTDCorpus",
    "TrainingConfig",
    "TrainingResults",
    "GenerateRequest",
    "GenerateResponse",
    
    # Main components
    "WOTDTrainer",
    "SyntheticGenerator", 
    "WOTDStorage",
    "SageMakerDeployer",
    
    # Convenience functions
    "train_wotd_pipeline",
    "generate_training_data",
    "get_wotd_storage",
    "deploy_complete_wotd_pipeline",
]