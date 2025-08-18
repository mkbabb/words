# Missing Classes and Functions Report

Generated: 2025-08-17

## Summary

This document lists all classes and functions that are referenced in imports but do not exist in the codebase. These need to be implemented or the references should be removed.

## Missing Classes

### 1. Corpus Module Classes

#### `LanguageCorpus` 📝 TO BE IMPLEMENTED
**Expected Location:** `/backend/src/floridify/corpus/language/core.py`
**Referenced In:**
- `/backend/src/floridify/corpus/language/__init__.py` (commented out)
- `/backend/src/floridify/corpus/__init__.py` (commented out)

**Purpose:** Language-specific corpus implementation
**Status:** To be implemented

#### `LanguageCorpusLoader` ❌ REMOVED
**Status:** Loaders have been removed from the architecture
**Action:** All references have been commented out

#### `LiteratureCorpus` 📝 TO BE IMPLEMENTED
**Expected Location:** `/backend/src/floridify/corpus/literature/core.py`
**Referenced In:**
- `/backend/src/floridify/corpus/literature/__init__.py` (commented out)
- `/backend/src/floridify/corpus/__init__.py` (commented out)

**Purpose:** Literature-specific corpus implementation
**Status:** To be implemented

#### `LiteratureCorpusLoader` ❌ REMOVED
**Status:** Loaders have been removed from the architecture
**Action:** All references have been commented out

### 2. API Repository Classes

#### `SynthesizedDictionaryEntry` ✅ RESOLVED
**Status:** Migrated to `DictionaryEntry`
**Action Taken:** All references updated to use `DictionaryEntry` instead

#### `DictionaryProviderData`
**Expected Location:** `/backend/src/floridify/models/` or `/backend/src/floridify/providers/dictionary/models.py`
**Referenced In:**
- `/backend/src/floridify/api/repositories/word_repository.py`

**Purpose:** Model for raw provider data

#### `LiteratureSource` ✅ RESOLVED
**Status:** Fixed - was confusion between `LiteratureSourceExample` and `LiteratureProvider`
**Action Taken:** 
- `example_repository.py` now uses `LiteratureSourceExample`
- `providers/literature/core.py` now uses `LiteratureProvider`

### 3. Caching Classes

#### `CacheTTL`
**Expected Location:** `/backend/src/floridify/caching/models.py`
**Referenced In:**
- `/backend/src/floridify/caching/__init__.py` (now removed)

**Purpose:** Cache time-to-live configuration

#### `ContentLocation` ✅ EXISTS
**Location:** `/backend/src/floridify/caching/models.py`
**Status:** Already exists and imports were fixed

#### `StorageType` ✅ EXISTS
**Location:** `/backend/src/floridify/caching/models.py`
**Status:** Already exists and imports were fixed

### 4. WOTD Module Classes (Deprecated)

#### `LiteratureSourceManager`
**Expected Location:** Previously in `/backend/src/floridify/wotd/literature/`
**Referenced In:**
- `/backend/src/floridify/wotd/trainer.py`

**Status:** Deprecated - should use `/backend/src/floridify/providers/literature/` instead

#### `LiteratureCorpusBuilder`
**Expected Location:** Previously in `/backend/src/floridify/wotd/literature/`
**Referenced In:**
- `/backend/src/floridify/wotd/trainer.py`

**Status:** Deprecated - needs refactoring

## Missing Functions

### `get_tree_corpus_manager`
**Expected Location:** `/backend/src/floridify/corpus/manager.py` (exists, but was incorrectly imported from caching/manager.py)
**Status:** Fixed - import paths corrected

## Action Items

### High Priority
1. Implement `SynthesizedDictionaryEntry` model or remove references
2. Implement `ContentLocation` and `StorageType` in caching/models.py
3. Clarify if `LiteratureSource` exists or should be created

### Medium Priority
1. Implement corpus loader classes or remove references:
   - `LanguageCorpus` and `LanguageCorpusLoader`
   - `LiteratureCorpus` and `LiteratureCorpusLoader`
2. Update WOTD module to use new provider structure

### Low Priority
1. Clean up deprecated WOTD literature references
2. Consider if `CacheTTL` is needed or can be removed permanently

## Notes

- Many of these missing classes appear to be part of an incomplete refactoring
- The corpus module structure suggests a planned but unimplemented abstraction layer
- WOTD module references are to a deprecated system that needs migration