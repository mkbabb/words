# Floridify Import Convention

## Standard: Relative Imports

All imports within the `floridify` package must use **relative imports**.

## Rules

### 1. Within Same Package Level
```python
# In api/routers/lookup.py importing from api/routers/common.py
from .common import PipelineMetrics

# In api/core/base.py importing from api/core/query.py
from .query import QueryBuilder
```

### 2. From Parent Package
```python
# In api/routers/lookup.py importing from api/core/
from ..core import handle_api_errors

# In api/routers/lookup.py importing from api/middleware/
from ..middleware.rate_limiting import rate_limit
```

### 3. From Package Root
```python
# In api/routers/lookup.py importing from floridify root modules
from ...models.models import Definition, Word
from ...utils.logging import get_logger
from ...ai import get_openai_connector
```

### 4. Module-Level Imports Only
All imports must be at the module level (top of file). Function-level imports are not allowed.

```python
# CORRECT - At module level
from ...storage.mongodb import get_storage

async def fetch_data():
    storage = await get_storage()

# INCORRECT - Inside function
async def fetch_data():
    from ...storage.mongodb import get_storage  # Don't do this
    storage = await get_storage()
```

## Import Path Reference

From `/src/floridify/api/routers/`:
- `..core` → `/src/floridify/api/core/`
- `..repositories` → `/src/floridify/api/repositories/`
- `..middleware` → `/src/floridify/api/middleware/`
- `...models` → `/src/floridify/models/`
- `...utils` → `/src/floridify/utils/`
- `...ai` → `/src/floridify/ai/`

From `/src/floridify/api/core/`:
- `...utils` → `/src/floridify/utils/`
- `...storage` → `/src/floridify/storage/`
- `...caching` → `/src/floridify/caching/`

## Benefits

1. **Portability**: Package works regardless of installation method
2. **Clarity**: Clear relationship between modules
3. **Refactoring**: Easier to move modules without changing imports
4. **No Name Conflicts**: Avoids issues with package name changes

## Enforcement

- MyPy type checking enforces correct imports
- All PRs must pass import validation
- No absolute imports starting with `floridify.` allowed