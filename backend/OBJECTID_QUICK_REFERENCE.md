# ObjectId Serialization - Quick Reference

## TL;DR

**No custom `@field_serializer` needed for ObjectId fields.** Beanie's `PydanticObjectId` has built-in serializers.

## Correct Usage

```python
from beanie import PydanticObjectId
from pydantic import BaseModel

class MyModel(BaseModel):
    corpus_id: PydanticObjectId
    parent_id: PydanticObjectId | None = None
    child_ids: list[PydanticObjectId] = []

    model_config = {
        "use_enum_values": True,  # For enum serialization
    }

# ✓ Correct: Use mode='json' for JSON serialization
model = MyModel(corpus_id=PydanticObjectId())
json_dict = model.model_dump(mode='json')  # ObjectIds → strings
json_str = json.dumps(json_dict)  # ✓ Works

# ✗ Wrong: Don't use model_dump() for JSON
python_dict = model.model_dump()  # ObjectIds → ObjectId instances
json_str = json.dumps(python_dict)  # ✗ Fails (needs custom encoder)
```

## How It Works

```python
# Python mode (default)
model.model_dump()
# → {"corpus_id": PydanticObjectId("68e574..."), ...}

# JSON mode
model.model_dump(mode='json')
# → {"corpus_id": "68e574...", ...}

# Built-in serializer in PydanticObjectId
# .venv/lib/python3.12/site-packages/beanie/odm/fields.py:155
serialization=core_schema.plain_serializer_function_ser_schema(
    lambda instance: str(instance), when_used="json"
)
```

## Fix for manager.py

**Current**:
```python
content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
```

**Recommended**:
```python
if hasattr(content, 'model_dump'):
    content_dict = content.model_dump(mode='json')
    content_str = json.dumps(content_dict, sort_keys=True)
else:
    content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
```

## What About Enums and DateTime?

```python
from enum import Enum
from datetime import datetime

class MyModel(BaseModel):
    my_enum: MyEnum
    created_at: datetime

    model_config = {
        "use_enum_values": True,  # Enums → values automatically
    }

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()  # Only if you want custom format
```

## Deserialization

Works automatically from strings:

```python
# From JSON
data = {"corpus_id": "68e574099fbdd484df264f43"}
model = MyModel(**data)  # ✓ Works

# From ObjectId
data = {"corpus_id": PydanticObjectId()}
model = MyModel(**data)  # ✓ Also works
```

## Benefits

1. **Built-in**: Uses Pydantic's optimized serializers
2. **Fast**: Single pass, no callback overhead
3. **Correct**: Handles ObjectIds, lists, optionals
4. **Maintainable**: Follows Pydantic best practices
5. **Type-safe**: Preserves type information

## See Also

- Full research: `/Users/mkbabb/Programming/words/backend/OBJECTID_SERIALIZATION_RESEARCH.md`
- Beanie source: `.venv/lib/python3.12/site-packages/beanie/odm/fields.py`
- Pydantic docs: https://docs.pydantic.dev/latest/concepts/serialization/
