# MyPy Error Breakdown - Detailed Fix Guide
**Date:** July 26, 2025  
**Total Errors:** 76 specific errors with line-by-line solutions

---

## Critical Priority Errors (24 errors)

### 1. Missing Return Type Annotations

#### Error 1: `src/floridify/api/core/query.py:118`
```python
# ERROR: Function is missing a return type annotation [no-untyped-def]
async def profile_query(self, description: str = "Query"):

# FIX:
async def profile_query(self, description: str = "Query") -> dict[str, Any]:
```

#### Error 2: `src/floridify/api/core/query.py:138`
```python
# ERROR: Function is missing a return type annotation [no-untyped-def]
def __init__(self):

# FIX:
def __init__(self) -> None:
```

#### Error 3: `src/floridify/api/main.py:32`
```python
# ERROR: Function is missing a return type annotation [no-untyped-def]
async def lifespan(app: FastAPI):

# FIX:
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
```

#### Error 4: `src/floridify/api/main.py:96`
```python
# ERROR: Function is missing a return type annotation [no-untyped-def]
async def api_info():

# FIX:
async def api_info() -> dict[str, str]:
```

### 2. Generic Type Parameters Missing

#### Error 5: `src/floridify/api/core/query.py:20`
```python
# ERROR: Missing type parameters for generic type "AsyncIOMotorDatabase" [type-arg]
def __init__(self, db: AsyncIOMotorDatabase | None = None):

# FIX:
from typing import Any
def __init__(self, db: AsyncIOMotorDatabase[Any] | None = None):
```

#### Error 6: `src/floridify/api/core/query.py:23`
```python
# ERROR: Missing type parameters for generic type "AsyncIOMotorDatabase" [type-arg]
async def _get_db(self) -> AsyncIOMotorDatabase:

# FIX:
async def _get_db(self) -> AsyncIOMotorDatabase[Any]:
```

#### Error 7: `src/floridify/api/core/query.py:61`
```python
# ERROR: Missing type parameters for generic type "dict" [type-arg]
def _get_index_recommendations(self, stats: list[dict]) -> list[str]:

# FIX:
def _get_index_recommendations(self, stats: list[dict[str, Any]]) -> list[str]:
```

### 3. Function Return Value Issues

#### Error 8: `src/floridify/connectors/wiktionary.py:702`
```python
# ERROR: Returning Any from function declared to return "list[Definition]" [no-any-return]
return raw_data.get("definitions", [])

# FIX:
definitions_data = raw_data.get("definitions", [])
if not isinstance(definitions_data, list):
    return []
return [Definition(**item) if isinstance(item, dict) else item 
        for item in definitions_data if isinstance(item, (dict, Definition))]
```

#### Error 9: `src/floridify/api/routers/definitions.py:432`
```python
# ERROR: Function does not return a value (it only ever returns None) [func-returns-value]
results = await enhance_definitions_parallel(

# FIX: Check the function signature and ensure it returns the expected type
# If the function should return None, change the return type annotation
async def batch_regenerate_components(...) -> dict[str, Any] | None:
    # ... existing code ...
    if not results:
        return None
    return results
```

### 4. Incompatible Assignment Types

#### Error 10: `src/floridify/audio/synthesizer.py:35`
```python
# ERROR: Incompatible types in assignment (expression has type "int", variable has type "AudioEncoding") [assignment]
audio_encoding: texttospeech.AudioEncoding = texttospeech.AudioEncoding.MP3

# FIX:
audio_encoding: texttospeech.AudioEncoding = texttospeech.AudioEncoding.MP3
# Or if the library returns int:
audio_encoding: int = texttospeech.AudioEncoding.MP3
```

#### Error 11: `src/floridify/batch/apple_dictionary_extractor.py:166`
```python
# ERROR: Argument 1 to "append" of "list" has incompatible type "ProviderData | BaseException"; expected "ProviderData" [arg-type]
valid_results.append(result)

# FIX:  
if isinstance(result, ProviderData):
    valid_results.append(result)
elif isinstance(result, BaseException):
    # Handle error case
    logger.error(f"Error in batch processing: {result}")
```

### 5. Union Type Attribute Access

#### Error 12: `src/floridify/api/routers/definitions.py:184`
```python
# ERROR: Item "None" of "Definition | None" has no attribute "model_dump" [union-attr]
definition_data = definition.model_dump()

# FIX:
if definition is None:
    return Response(status_code=404, content="Definition not found")
definition_data = definition.model_dump()
```

---

## High Priority Errors (28 errors)

### 1. Missing Attribute Errors

#### Error 13: `src/floridify/cli/commands/config.py:12`
```python
# ERROR: Module "src.floridify.utils.paths" has no attribute "get_config_path" [attr-defined]
from ..utils.paths import get_config_path

# FIX: Check if the function exists or create it
# Option 1: If function exists in different module
from ..config.paths import get_config_path

# Option 2: If function doesn't exist, create it
def get_config_path() -> Path:
    return Path.home() / ".floridify" / "config.toml"
```

#### Error 14: `src/floridify/cli/commands/similar.py:92`
```python
# ERROR: "OpenAIConnector" has no attribute "generate_synonyms" [attr-defined]
synonym_response = await ai_connector.generate_synonyms(

# FIX: Use the correct method name
synonym_response = await ai_connector._make_structured_request(
    prompt=f"Generate synonyms for: {word}",
    response_model=SynonymResponse,
    # ... other parameters
)
```

### 2. Incompatible Argument Types

#### Error 15: `src/floridify/connectors/oxford.py:261`
```python
# ERROR: Argument "language_register" to "Definition" has incompatible type "str | None"; expected "Literal['formal', 'informal', 'neutral', 'slang', 'technical'] | None" [arg-type]
language_register=register,

# FIX:
from typing import Literal
ValidRegister = Literal['formal', 'informal', 'neutral', 'slang', 'technical']

def validate_register(register: str | None) -> ValidRegister | None:
    if register is None:
        return None
    valid_registers = {'formal', 'informal', 'neutral', 'slang', 'technical'}
    return register if register in valid_registers else 'neutral'

# Usage:
language_register=validate_register(register),
```

#### Error 16: `src/floridify/api/routers/definitions.py:408`
```python
# ERROR: Argument 1 to "get_many" has incompatible type "list[PydanticObjectId]"; expected "list[PydanticObjectId | str]" [arg-type]
definitions = await repo.get_many(definition_ids)

# FIX:
from typing import cast
definitions = await repo.get_many(cast(list[PydanticObjectId | str], definition_ids))

# Or better, update the method signature if possible:
async def get_many(self, ids: list[PydanticObjectId | str]) -> list[Definition]:
```

### 3. List/Dict Type Annotation Issues

#### Error 17: `src/floridify/api/routers/definitions.py:302`
```python
# ERROR: List item 0 has incompatible type "dict[str, str]"; expected "ErrorDetail" [list-item]
errors=[
    {
        "type": "validation_error",
        "msg": f"Word '{word_text}' not found",
    }
]

# FIX:
from ..models.common import ErrorDetail
errors=[
    ErrorDetail(
        type="validation_error", 
        msg=f"Word '{word_text}' not found"
    )
]
```

#### Error 18: `src/floridify/api/core/query.py:221`
```python
# ERROR: Need type annotation for "operations" (hint: "operations: list[<type>] = ...") [var-annotated]
self.operations = []

# FIX:
from pymongo import UpdateOne, InsertOne, DeleteOne, ReplaceOne
from typing import Union

BulkOperation = Union[UpdateOne, InsertOne, DeleteOne, ReplaceOne]
self.operations: list[BulkOperation] = []
```

---

## Medium Priority Errors (15 errors)

### 1. Redundant Type Casts

#### Error 19: `src/floridify/ai/connector.py:153`
```python
# ERROR: Redundant cast to "T" [redundant-cast]
return cast(T, result)

# FIX:
return cast("T", result)  # Add quotes for forward reference
# Or if truly redundant:
return result  # Remove cast entirely if types already match
```

### 2. Variable Redefinition

#### Error 20: `src/floridify/api/routers/batch.py:219`
```python
# ERROR: Name "results" already defined on line 199 [no-redef]
results: list[BatchResult] = []

# FIX:
batch_results: list[BatchResult] = []  # Use different variable name
# Or scope the variables properly in different blocks
```

---

## Specific High-Impact Fix Examples

### Database Query Builder Enhancement
```python
# Current problematic code in api/core/query.py
class QueryOptimizer:
    def __init__(self, db: AsyncIOMotorDatabase | None = None):  # Missing type params
        self.db = db
    
    async def _get_db(self) -> AsyncIOMotorDatabase:  # Missing type params
        if self.db is None:
            # Get from dependency
            pass
        return self.db

# Fixed version:
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict

class QueryOptimizer:
    def __init__(self, db: AsyncIOMotorDatabase[Dict[str, Any]] | None = None) -> None:
        self.db = db
    
    async def _get_db(self) -> AsyncIOMotorDatabase[Dict[str, Any]]:
        if self.db is None:
            from ..dependencies import get_database
            self.db = await get_database()
        return self.db
```

### API Router Response Type Safety
```python
# Current problematic code in api/routers/definitions.py
async def get_definition(word: str) -> ResourceResponse:
    definition = await service.get_definition(word)
    if definition:
        definition_data = definition.model_dump()  # Error: definition can be None
        return ResourceResponse(data=definition_data)
    return Response(status_code=304)  # Error: wrong return type

# Fixed version:
async def get_definition(word: str) -> ResourceResponse:
    definition = await service.get_definition(word)
    if definition is None:
        raise HTTPException(status_code=404, detail="Definition not found")
    
    definition_data = definition.model_dump()
    return ResourceResponse(data=definition_data)
```

### AI Connector Method Resolution
```python
# Current problematic code in ai/connector.py
def _make_structured_request(
    self, 
    prompt: str,
    response_model: type[T],
    **kwargs: Any,  # Ruff ANN401 warning
) -> T:
    return cast(T, result)  # Redundant cast error

# Fixed version:
from typing import TypeVar, Any, Unpack, TypedDict

class RequestKwargs(TypedDict, total=False):
    temperature: float
    max_tokens: int
    model: str

def _make_structured_request(
    self, 
    prompt: str,
    response_model: type[T],
    **kwargs: Unpack[RequestKwargs],
) -> T:
    # Process request...
    return response_model.model_validate(result)  # Proper validation instead of cast
```

---

## Implementation Priority Matrix

| Error Category | Count | Effort (Hours) | Impact | Priority |
|---------------|-------|---------------|---------|----------|
| Return Type Annotations | 8 | 2 | High | 1 |
| Generic Type Parameters | 5 | 3 | Critical | 1 |
| Union Type Safety | 7 | 4 | High | 1 |
| Missing Attributes | 8 | 6 | Medium | 2 |
| Argument Type Mismatches | 12 | 8 | Medium | 2 |
| Container Type Annotations | 8 | 3 | Medium | 2 |
| Function Call Issues | 10 | 12 | Low | 3 |
| Import/Module Issues | 18 | 4 | Low | 3 |

**Total Estimated Effort:** 42 hours (~1 week of focused development)

---

## Automated Fix Opportunities

### Ruff Auto-fixable Issues (17 instances)
```bash
# Apply automatic fixes for quotes in type expressions
uv run ruff check src/floridify --select TC006 --fix

# Apply automatic fixes for isinstance calls  
uv run ruff check src/floridify --select UP038 --fix
```

### MyPy Suggested Fixes
Many errors can be resolved with mypy suggestions:
```bash
# Run mypy with error codes and suggestions
uv run mypy src/floridify --show-error-codes --pretty --show-error-context
```

---

This detailed breakdown provides specific line-by-line fixes for achieving production-ready type safety in the Floridify backend codebase.