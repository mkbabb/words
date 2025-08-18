"""Literature corpus models."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import Field

from ...models.literature import AuthorInfo, Genre, Period
from ..models import CorpusMetadata, CorpusType


