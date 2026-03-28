"""Local assessment functions replacing AI calls where quality matches or exceeds.

Each module provides a local-first assessment with an optional AI fallback.
"""

from .cefr import assess_cefr_local
from .domain import classify_domain_local
from .frequency import assess_frequency_local
from .regional import detect_regional_local
from .register import classify_register_local

__all__ = [
    "assess_cefr_local",
    "assess_frequency_local",
    "classify_domain_local",
    "classify_register_local",
    "detect_regional_local",
]
