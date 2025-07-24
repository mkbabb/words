# Legacy Code Cleanup Analysis

## Overview

This document comprehensively catalogs all backward compatibility aliases, legacy naming patterns, and workarounds found in the Floridify backend codebase. Each item includes the location, current implementation, and recommended action.

## 1. Backward Compatibility Aliases

### 1.1 AI Module Aliases

#### DefinitionSynthesizer Class Alias
- **Location**: `src/floridify/ai/synthesizer.py:552`
- **Current**: `DefinitionSynthesizer = EnhancedDefinitionSynthesizer`
- **Action**: Rename `EnhancedDefinitionSynthesizer` to `DefinitionSynthesizer` and remove alias

#### Factory Import Alias
- **Location**: `src/floridify/ai/factory.py:10`
- **Current**: `from .synthesizer import EnhancedDefinitionSynthesizer as DefinitionSynthesizer`
- **Action**: Update after renaming the class

#### Deprecated Factory Functions
- **Location**: `src/floridify/ai/factory.py:57-63, 92-100`
- **Functions**:
  - `create_openai_connector()` → Use `get_openai_connector()`
  - `create_definition_synthesizer()` → Use `get_definition_synthesizer()`
- **Action**: Remove deprecated functions

#### Method Alias
- **Location**: `src/floridify/ai/connector.py:484-486`
- **Current**: `_make_request()` aliases `_make_structured_request()`
- **Action**: Remove alias method

### 1.2 Logging Module Compatibility

#### Setup Function
- **Location**: `src/floridify/utils/logging.py:162-168`
- **Current**: `setup_logging()` preserved for backward compatibility
- **Action**: Check usage and remove if unused

#### Logger Method Alias
- **Location**: `src/floridify/utils/logging.py:125-127`
- **Current**: `warn()` method aliases `warning()`
- **Action**: Keep (standard Python logging compatibility)

### 1.3 Search Module Singletons

#### Global Singleton
- **Location**: `src/floridify/search/language.py:105-106`
- **Current**: `_language_search` global for backward compatibility
- **Action**: Review if singleton pattern is still needed

#### Ignored Parameters
- **Location**: `src/floridify/core/search_pipeline.py:30-31`
- **Current**: `enable_semantic` parameter ignored
- **Action**: Remove parameter from function signature

### 1.4 Lexicon Parser Compatibility

#### String to Enum Conversion
- **Location**: `src/floridify/search/lexicon/parser.py:331-334`
- **Current**: Converts string to `LexiconFormat` enum for compatibility
- **Action**: Ensure all callers use enum directly

## 2. Enhanced/Legacy Class Patterns

### 2.1 Enhanced Classes
- **EnhancedDefinitionSynthesizer** → Should be renamed to `DefinitionSynthesizer`
- **EnhancedDefinitionResponse** (ai/models.py:319) → Consider making this the standard

### 2.2 Test Files
- `tests/test_models_v2.py` → Rename to `test_models.py`

## 3. TODO/Workaround Patterns

### 3.1 Stub Implementations

#### Dictionary.com Connector
- **Location**: `src/floridify/connectors/dictionary_com.py`
- **Issue**: Entire connector is unimplemented stub
- **Action**: Implement or remove

#### Placeholder Data
- **Location**: `src/floridify/batch/apple_dictionary_extractor.py:362-367`
- **Issue**: Hardcoded word list as placeholder
- **Action**: Implement proper data source

### 3.2 Hardcoded Values

#### Confidence Scores
- **Location**: `src/floridify/ai/synthesizer.py:154`
- **Current**: `confidence=0.9` hardcoded
- **Action**: Calculate from component confidences

### 3.3 Async/Sync Limitations

#### CLI Formatting
- **Location**: `src/floridify/cli/utils/formatting.py:366-368`
- **Issue**: Examples skipped due to async loading in sync context
- **Action**: Implement async CLI formatting or preload data

## 4. Duplicate Implementations

### 4.1 Text Normalization
- `text/normalizer.py` - General text normalization
- `batch/word_normalizer.py` - Word-specific normalization
- **Action**: Consider consolidating common functionality

### 4.2 Factory Methods
- `create_*` methods duplicate `get_*` singleton methods
- **Action**: Remove `create_*` methods

## 5. Import Patterns to Clean

### 5.1 Remove These Imports
```python
# Current
from .synthesizer import EnhancedDefinitionSynthesizer as DefinitionSynthesizer

# Should be (after renaming)
from .synthesizer import DefinitionSynthesizer
```

### 5.2 Update Function Calls
- Replace `create_openai_connector()` with `get_openai_connector()`
- Replace `create_definition_synthesizer()` with `get_definition_synthesizer()`
- Replace `_make_request()` with `_make_structured_request()`

## Implementation Plan

### Phase 1: Rename Core Classes
1. Rename `EnhancedDefinitionSynthesizer` to `DefinitionSynthesizer`
2. Remove the alias line
3. Update all imports

### Phase 2: Remove Deprecated Functions
1. Remove `create_openai_connector()` and `create_definition_synthesizer()`
2. Update any callers to use `get_*` versions
3. Remove `_make_request()` alias method

### Phase 3: Clean Parameters
1. Remove `enable_semantic` parameter from search functions
2. Update function signatures and callers

### Phase 4: Address TODOs
1. Implement confidence calculation
2. Implement or remove Dictionary.com connector
3. Address async/sync issues in CLI

### Phase 5: Test and Verify
1. Run full test suite
2. Run mypy and ruff checks
3. Verify no functionality is broken

## Summary Statistics

- **Backward Compatibility Aliases**: 5
- **Deprecated Functions**: 3
- **Enhanced Classes to Rename**: 2
- **Stub Implementations**: 2
- **Ignored Parameters**: 2
- **TODO Comments**: 4
- **Test Files to Rename**: 1

Total items requiring action: **19**