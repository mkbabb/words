# Import Fix Plan for Floridify Backend

## Summary of Findings

The codebase is configured to use **absolute imports** with the `floridify` package name. However, there are inconsistencies:

1. **Mixed import styles**: Some files use relative imports (`from ...`) while others use absolute (`from floridify...`)
2. **Incorrect imports**: Some files use `from src.floridify...` which is wrong
3. **Missing module**: `synthesis` module imported in `__init__.py` doesn't exist
4. **Function-level imports**: Some imports are inside functions instead of module level

## Import Convention

**Standard**: Use absolute imports starting with `floridify`
```python
# Correct:
from floridify.models.models import Definition
from floridify.api.core import handle_api_errors
from floridify.utils.logging import get_logger

# Incorrect:
from ..models.models import Definition  # Relative
from src.floridify.models import Definition  # Wrong prefix
```

## Files to Fix

### Priority 1: Fix Wrong Imports
1. `/src/floridify/core/lookup_pipeline.py` - Line 9
   - Change: `from src.floridify.storage.mongodb import get_synthesized_entry`
   - To: `from floridify.storage.mongodb import get_synthesized_entry`

2. `/src/floridify/api/routers/__init__.py` - Lines 15, 31
   - Remove: `synthesis` (module doesn't exist)

### Priority 2: Convert Relative to Absolute in Routers
Files using relative imports that need conversion:
- `batch.py`
- `corpus.py` 
- `health.py`
- `lookup.py`
- `search.py`
- `suggestions.py`
- `synonyms.py`

### Priority 3: Fix Core Module Imports
1. `/src/floridify/api/core/monitoring.py` - Line 13
   - Already uses absolute, but marked in mypy errors
   
2. `/src/floridify/api/core/query.py` - Lines 12-13
   - Already uses absolute, but marked in mypy errors

3. `/src/floridify/api/core/cache.py` - Line 12
   - Already uses absolute

### Priority 4: Move Function-Level Imports
1. `/src/floridify/connectors/wiktionary.py`
   - Line 142: Move `from floridify.storage.mongodb import get_storage` to top
   - Line 147: Move `from floridify.constants import Language` to top

2. `/src/floridify/connectors/oxford.py`
   - Line 76: Move `from floridify.storage.mongodb import get_storage` to top

## Implementation Order

1. Fix incorrect imports (src.floridify)
2. Remove non-existent module imports
3. Convert all relative imports to absolute
4. Move function-level imports to module level
5. Run mypy to verify no import errors
6. Update any remaining issues

## Validation

After fixes:
- All imports should start with `floridify.`
- No relative imports (`from ..`)
- All imports at module level (not in functions)
- MyPy should show no import errors