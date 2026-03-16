"""Search router sub-package."""

from fastapi import APIRouter

from .main import router as main_router
from .rebuild import router as rebuild_router
from .semantic import router as semantic_router

router = APIRouter()
router.include_router(main_router)
router.include_router(semantic_router)
router.include_router(rebuild_router)

__all__ = ["router", "main_router", "rebuild_router", "semantic_router"]
