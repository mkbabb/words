# Backend Type Checking Report - August 13, 2025

## Executive Summary

Comprehensive type checking revealed **131 type errors** across **53 files** in the backend codebase. The errors fall into several critical categories that need immediate attention, particularly around the versioning system, manager classes, and enum/TTL type mismatches.

**Type Safety Score**: ~65% (files with errors / total files checked)

## Critical Issues Requiring Immediate Attention

### 1. TTL/Timedelta Type Mismatches (High Priority)
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/manager.py:222`
```python
# Error: Incompatible return value type (got "timedelta", expected "CacheTTL | None")
def default_cache_ttl(self) -> CacheTTL | None:
    return CacheTTL.SEMANTIC  # CacheTTL.SEMANTIC is timedelta(days=7)
```
**Root Cause**: `CacheTTL.SEMANTIC` is defined as `timedelta(days=7)` but the method expects `CacheTTL | None`.
**Resolution**: Change return type to `timedelta | None` or create proper enum values.

### 2. Missing Base Manager Infrastructure (Critical)
**Files**: Multiple manager classes importing missing modules:
- `floridify.core.base_manager.BaseResourceManager` - Missing
- `floridify.core.manager_registry.register_manager` - Missing

**Affected Files**:
- `/Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/manager.py:14`
- `/Users/mkbabb/Programming/words/backend/src/floridify/api/repositories/provider_repository.py:20`

**Impact**: Prevents proper inheritance and manager registration across the system.

### 3. Versioned Data Manager Issues (High Priority)
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/providers/base.py:102`
```python
# Error: Missing positional argument "data_class" in call to "VersionedDataManager"
manager = VersionedDataManager[DictionaryVersionedData]()
```
**Root Cause**: Constructor signature mismatch for VersionedDataManager.

### 4. Exception Handling Type Error (High Priority)
**File**: `/Users/mkbabb/Programming/words/backend/src/floridify/providers/dictionary/manager.py:88`
```python
# Error: Incompatible types (expression has type "DictionaryProviderData | BaseException", target has type "DictionaryProviderData")
results[provider] = result  # from asyncio.gather(..., return_exceptions=True)
```
**Resolution**: Add proper type narrowing with isinstance check.

### 5. Module Duplicate Conflict (Blocking)
**Error**: `Source file found twice under different module names: "floridify.api.routers.search" and "src.floridify.api.routers.search"`
**Impact**: Prevents full API type checking.

## Module-by-Module Breakdown

### Providers Module (19 files checked, 80 errors)

#### Dictionary Providers
**Critical Errors**:
- **Constructor Mismatches**: API providers missing required `provider` argument
- **Property Overrides**: `provider_name` and `provider_version` property signature conflicts
- **Method Signature Mismatches**: `_fetch_from_provider` incompatible signatures across inheritance hierarchy

**Examples**:
```python
# /Users/mkbabb/Programming/words/backend/src/floridify/providers/dictionary/api/free_dictionary.py:41
super().__init__()  # Missing 'provider' argument

# /Users/mkbabb/Programming/words/backend/src/floridify/providers/dictionary/api/merriam_webster.py:63
@property
def provider_name(self) -> DictionaryProvider:  # Should return str, not DictionaryProvider
```

#### Literature Providers
- **Language Type Mismatches**: `str` provided where `Language` enum expected
- **Content Location Type Conflicts**: Mismatched content location types between versioned and provider models

#### Utils and Base Classes
- **Missing Return Annotations**: Multiple async context manager methods
- **TTL Type Issues**: `int | None` provided where `timedelta | None` expected

### Search Module (12 files checked, 19 errors)

#### Semantic Search Manager
- **Base Class Issues**: Cannot inherit from `BaseResourceManager` (type `Any`)
- **TTL Return Type**: Returns `timedelta` where `CacheTTL | None` expected
- **Return Type Issues**: Methods returning `Any` instead of declared types

#### Core Search
- **Method Availability**: `CorpusManager` missing `get_corpus_metadata` method
- **Argument Mismatches**: Unexpected `vocab_hash` argument in `get_corpus` calls

#### Language Search
- **Union Attribute Access**: Accessing attributes on `LexiconData | None` without proper null checks
- **Constructor Arguments**: Missing required `corpus_name` argument

### API Repositories (11 files checked, 25 errors)

#### Provider Repository
- **Base Class Inheritance**: Cannot subclass from `Any` type
- **Type Assignment Issues**: Enum values assigned to incompatible types
- **Method Chain Issues**: `FindOne` object missing `sort` attribute
- **Null Pointer Access**: Accessing attributes on potentially `None` DeleteResult

#### Corpus Repository
- **Manager Method Calls**: Unexpected `corpus_name` argument and missing methods
- **Return Type Issues**: Methods returning `Any` instead of declared types

#### Wordlist Repository
- **Manager Method Availability**: `CorpusManager` missing `invalidate_corpus` method
- **Argument Mismatches**: Unexpected `corpus_name` in `create_corpus` calls

### Corpus Module (15 files checked, 17 errors)

#### Models
- **Pydantic Field Issues**: Invalid `Field(unique=True)` usage
- **Missing Type Annotations**: Constructor and method signatures

#### Loaders
- **Cache Assignment**: `None` variable assigned `UnifiedCache` instance
- **Attribute Access**: Missing attributes on data models
- **Method Name Issues**: Calling non-existent methods
- **Async/Await Issues**: Non-awaitable objects in await expressions

### Core Module (7 files checked, 7 errors)

#### Lookup Pipeline
- **Import Issues**: Missing `ProviderData` in definition models
- **Connector Assignment**: Incompatible connector types in assignments

#### WOTD Pipeline  
- **Missing Attributes**: Module missing expected classes and functions
- **Return Type Issues**: Methods returning `Any` instead of declared types

## Recommended Resolution Order

### Phase 1: Infrastructure (Blocking Issues)
1. **Create Missing Base Classes**
   - Implement `floridify.core.base_manager.BaseResourceManager`
   - Implement `floridify.core.manager_registry.register_manager`
   - Create missing `floridify.api.repositories.base.BaseRepository`

2. **Fix Module Duplication**
   - Resolve search.py file conflicts
   - Ensure proper module path resolution

### Phase 2: Type System Alignment (High Priority)
3. **Fix TTL/Enum Type Issues**
   - Standardize CacheTTL usage patterns
   - Fix return type annotations to match actual returned types
   - Create proper enum wrapper if needed

4. **Fix Versioned Data Manager**
   - Correct constructor signatures
   - Add missing required arguments
   - Ensure proper generic type usage

### Phase 3: API and Provider Fixes (Medium Priority)
5. **Provider Constructor Issues**
   - Add missing required arguments to API provider constructors
   - Fix property override signatures
   - Align method signatures across inheritance hierarchy

6. **Repository Type Issues**  
   - Fix base class inheritance issues
   - Add proper type narrowing for union types
   - Implement missing repository methods

### Phase 4: Search and Corpus Refinements (Low Priority)
7. **Manager Method Availability**
   - Implement missing manager methods or remove calls
   - Fix argument signatures for existing methods
   - Add proper null checking for union types

8. **Missing Annotations**
   - Add type annotations to remaining untyped methods
   - Fix generic type parameters
   - Add return type annotations

## Code Snippets for Critical Fixes

### Fix 1: TTL Type Issue
```python
# Current (broken)
def default_cache_ttl(self) -> CacheTTL | None:
    return CacheTTL.SEMANTIC

# Fix Option A: Change return type
def default_cache_ttl(self) -> timedelta | None:
    return CacheTTL.SEMANTIC

# Fix Option B: Create enum wrapper
class CacheTTLEnum(Enum):
    SEMANTIC = CacheTTL.SEMANTIC
    CORPUS = CacheTTL.CORPUS
    # etc.
```

### Fix 2: Exception Handling in Manager
```python
# Current (broken)
results[provider] = result

# Fixed
if not isinstance(result, Exception) and result:
    results[provider] = result
```

### Fix 3: Versioned Data Manager Constructor
```python
# Current (broken)
manager = VersionedDataManager[DictionaryVersionedData]()

# Fixed (need to check actual constructor signature)
manager = VersionedDataManager(data_class=DictionaryVersionedData)
```

## Summary

The codebase has a solid foundation but requires systematic attention to type consistency, particularly around:
- Infrastructure classes (base managers, registries)
- Enum/TTL type standardization  
- Exception handling type safety
- Manager method signatures and availability

Addressing these issues in the recommended order will significantly improve type safety and catch potential runtime errors early in development.