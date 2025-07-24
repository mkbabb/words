"""Field selection middleware for API responses."""

from typing import Any

from beanie import Document
from pydantic import BaseModel


def select_fields[T: BaseModel](
    obj: T,
    include: set[str] | None = None,
    exclude: set[str] | None = None
) -> dict[str, Any]:
    """Select specific fields from a Pydantic model.
    
    Args:
        obj: The model instance
        include: Fields to include (None = all fields)
        exclude: Fields to exclude
        
    Returns:
        Dictionary with selected fields
    """
    data = obj.model_dump()
    
    if include:
        # Only include specified fields
        data = {k: v for k, v in data.items() if k in include}
    
    if exclude:
        # Remove excluded fields
        data = {k: v for k, v in data.items() if k not in exclude}
    
    return data


def parse_field_param(field_str: str | None) -> set[str] | None:
    """Parse comma-separated field parameter.
    
    Args:
        field_str: Comma-separated field names
        
    Returns:
        Set of field names or None
    """
    if not field_str:
        return None
    
    return {f.strip() for f in field_str.split(",") if f.strip()}


class FieldSelector:
    """Field selection helper for API endpoints."""
    
    def __init__(
        self,
        include: str | None = None,
        exclude: str | None = None
    ):
        self.include = parse_field_param(include)
        self.exclude = parse_field_param(exclude)
    
    def select[T: BaseModel](self, obj: T) -> dict[str, Any]:
        """Apply field selection to an object."""
        return select_fields(obj, self.include, self.exclude)
    
    def select_many[T: BaseModel](self, objs: list[T]) -> list[dict[str, Any]]:
        """Apply field selection to multiple objects."""
        return [self.select(obj) for obj in objs]


async def load_related_fields(
    obj: Document,
    fields: set[str],
    depth: int = 1
) -> dict[str, Any]:
    """Load related fields from foreign keys.
    
    Args:
        obj: Document instance
        fields: Fields to load
        depth: Maximum depth for nested loading
        
    Returns:
        Dictionary with loaded fields
    """
    data: dict[str, Any] = obj.model_dump()
    
    if depth <= 0:
        return data
    
    # Check for foreign key fields
    for field_name in fields:
        if field_name.endswith("_id") and field_name[:-3] in fields:
            # Load related document
            related_field = field_name[:-3]
            fk_value = getattr(obj, field_name, None)
            
            if fk_value:
                # Dynamically import the related model
                # This is a simplified version - in production you'd have a registry
                from ...models import Definition, Example, Pronunciation, Word
                
                model_map = {
                    "word": Word,
                    "definition": Definition,
                    "example": Example,
                    "pronunciation": Pronunciation,
                }
                
                related_model = model_map.get(related_field)
                if related_model:
                    related_obj = await related_model.get(fk_value)  # type: ignore[attr-defined]
                    if related_obj:
                        data[related_field] = await load_related_fields(
                            related_obj,
                            fields,
                            depth - 1
                        )
    
    return data