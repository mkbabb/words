# Duplicated, Deprecated, and Dead Code Report

Generated: 2025-08-17

## Duplicate Class Definitions

### 1. BatchRequest
**Duplicated in:**
- `/backend/src/floridify/api/core/base.py:93` - `class BatchRequest(BaseModel)`
- `/backend/src/floridify/ai/batch_processor.py:30` - `class BatchRequest`

**Recommendation:** Consolidate into a single definition in `api/core/base.py` and import from there.

### 2. ModelInfo
**Duplicated in:**
- `/backend/src/floridify/models/base.py:79` - `class ModelInfo(BaseModel)`
- `/backend/src/floridify/ai/models.py:13` - `class ModelInfo(BaseModel)`

**Recommendation:** Use the version in `models/base.py` as the canonical definition.

### 3. BatchResponse
**Multiple specialized versions in:**
- `/backend/src/floridify/api/core/base.py:101` - `class BatchResponse(BaseModel)`
- Various AI modules with specialized batch response classes

**Recommendation:** Create a base BatchResponse class and use inheritance for specialized versions.

## Dead Imports from Deleted Files

### 1. AI Templates Module
**Deleted File:** `backend/src/floridify/ai/templates.py`
**Still imported in:**
- `/backend/src/floridify/anki/generator.py:18`
- `/backend/src/floridify/anki/__init__.py:5`

**Action Required:** Remove imports and update to use new template system.

### 2. Corpus Language Loader
**Deleted File:** `backend/src/floridify/corpus/loaders/language.py`
**Still imported in:**
- `/backend/src/floridify/search/language.py:12` - `from ..corpus.loaders.language import CorpusLanguageLoader`

**Action Required:** Update to use new loader system from `corpus/language/`.

### 3. WOTD Literature Module
**Deprecated Module:** `wotd/literature`
**Still imported in:**
- `/backend/src/floridify/wotd/trainer.py:52` - `from ..literature import LiteratureSourceManager`
- `/backend/src/floridify/wotd/trainer.py:74` - `from .literature import LiteratureCorpusBuilder`
- `/backend/src/floridify/wotd/trainer.py:797` - `from ..literature.models import Author as LitAuthor, Genre, Period`

**Action Required:** Update to use `providers/literature/` module instead.

## Deprecated Code Patterns

### TODO Comments Indicating Incomplete Implementation
1. `/backend/src/floridify/cli/utils/formatting.py:174` - `# TODO: Implement word display formatting`
2. `/backend/src/floridify/ai/synthesis_functions.py:1078` - `# TODO: Load provider data for pronunciation`
3. `/backend/src/floridify/ai/synthesis_functions.py:1084` - `# TODO: Load provider data for etymology`

**Recommendation:** Either implement these TODOs or remove if no longer relevant.

## Circular Import Risks

### High Risk Areas
1. **Caching ↔ Models**: Fixed with registry pattern in `models/versioned.py`
2. **Storage ↔ Models**: Potential circular dependencies between MongoDB storage and model definitions
3. **Corpus ↔ Search**: Complex interdependencies that could create circular imports

## Missing Infrastructure

### Loader Classes
**Missing but referenced:**
- `LanguageCorpusLoader` (referenced in `corpus/language/__init__.py`)
- `LiteratureCorpusLoader` (referenced in `corpus/literature/__init__.py`)

**Action Required:** Implement these loader classes or remove references.

## Consolidation Opportunities

### Repository Pattern
Multiple repository classes with similar patterns across:
- API routers
- Provider modules
- Storage layers

**Recommendation:** Create a base repository class and standardize the pattern.

### Caching Mechanisms
Similar caching logic implemented in:
- Caching module
- Individual provider modules
- API layer

**Recommendation:** Consolidate into the unified caching system.

## Priority Actions

### High Priority
1. Remove all dead imports from deleted files
2. Consolidate `BatchRequest` and `ModelInfo` duplicate definitions
3. Fix WOTD trainer imports to use new provider structure
4. Implement missing loader classes or remove references

### Medium Priority
1. Address TODO comments
2. Standardize repository patterns
3. Consolidate caching mechanisms

### Low Priority
1. Clean up warning log proliferation
2. Review and optimize import structures
3. Remove commented-out code blocks