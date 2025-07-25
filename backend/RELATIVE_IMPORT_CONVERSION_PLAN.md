# Relative Import Conversion Plan

## Summary
Convert all absolute imports (`from floridify.*`) to relative imports (`from ..*`) throughout the codebase.

## Files Requiring Conversion

### 1. API Routers (7 files, 33 imports)
- **atomic_updates.py** - 3 imports
- **batch_v2.py** - 3 imports  
- **definitions.py** - 7 imports (2 inside functions)
- **examples.py** - 5 imports
- **facts.py** - 7 imports
- **lookup.py** - 3 imports (all inside functions)
- **words.py** - 5 imports (2 inside functions)

### 2. API Core (3 files, 4 imports)
- **monitoring.py** - 1 import
- **query.py** - 2 imports
- **cache.py** - 1 import

### 3. Other Issues to Fix
- **routers/__init__.py** - Remove imports for deleted files (synthesis, definitions_old, facts_old, words_old)
- **connectors/wiktionary.py** - Move 2 function-level imports to module level
- **connectors/oxford.py** - Move 1 function-level import to module level

## Import Conversion Rules

From routers directory (`/src/floridify/api/routers/`):
- `from floridify.api.core` → `from ..core`
- `from floridify.api.repositories` → `from ..repositories`
- `from floridify.api.middleware` → `from ..middleware`
- `from floridify.models` → `from ...models`
- `from floridify.utils` → `from ...utils`
- `from floridify.ai` → `from ...ai`

From core directory (`/src/floridify/api/core/`):
- `from floridify.utils` → `from ...utils`
- `from floridify.storage` → `from ...storage`
- `from floridify.caching` → `from ...caching`

## Implementation Order

1. Fix router __init__.py (remove non-existent imports)
2. Convert routers (largest group)
3. Convert core modules
4. Move function-level imports to module level
5. Verify with `uv run mypy`

## Total Changes
- Files to modify: 13
- Import statements to convert: 37
- Function-level imports to move: 7
- Non-existent imports to remove: 4