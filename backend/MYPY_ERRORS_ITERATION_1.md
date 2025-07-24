# MyPy and Ruff Error Analysis - Iteration 1

## Summary Statistics
- **Total MyPy Errors**: 111
- **Files with Errors**: 21
- **Ruff Errors**: 0 (Clean!)

## Critical Issues by Category

### 1. Model Structure Transition Issues (35 errors)

#### Non-existent Models Referenced:
- **GeneratedExample**: `api/routers/definitions.py:130`
- **DictionaryEntry**: `anki/generator.py:15`, `cli/commands/database.py:12`
- **Examples**: `ai/synthesizer_old.py:10`

#### Incorrect Attribute Access:
- **definition.examples.generated**: 
  - `api/routers/definitions.py:128,131`
  - `anki/generator.py:243,244`
  - `connectors/apple_dictionary.py:384`
  - `cli/utils/formatting.py:366`

#### PydanticObjectId vs str Conversions:
- `ai/synthesizer.py:146,147,148,150,156,237,322,335,345,492,511,521,528,530`
- `ai/synthesis_functions.py:46,327`

### 2. Missing Required Arguments (17 errors)

#### frequency_band missing:
- `ai/synthesizer.py:321,491`
- `connectors/wiktionary.py:364`
- `connectors/oxford.py:251`
- `connectors/apple_dictionary.py:370`

#### Other missing arguments:
- `api/routers/definitions.py:102`: context for ExampleRegenerationRequest
- `connectors/apple_dictionary.py:277`: word_id, provider for ProviderData
- `connectors/wiktionary.py:509`: word_id for Pronunciation

### 3. Async/Await Issues (8 errors)

#### Missing await on get_storage():
- `api/routers/definitions.py:65,85,107,135`

#### Coroutine type mismatches:
- `utils/logging.py:191,194,251,253`

### 4. Type Annotation Issues (23 errors)

#### Missing return annotations:
- `text/processor.py:111`
- `search/semantic.py:51`

#### Incorrect type ignore syntax:
- `search/semantic.py:19,22,25,28`

#### Any type returns:
- `text/processor.py:142,149`
- `utils/logging.py:194,253`
- `ai/connector.py:158`

### 5. Field() Usage Errors (6 errors)
- `api/routers/batch.py:31,66,88`
- `api/routers/batch_v2.py:25,41,55`

### 6. Literal Type Mismatches (6 errors)
- `ai/synthesis_functions.py:105,252,276,329`
- `connectors/oxford.py:259`

### 7. Missing Methods/Attributes (14 errors)
- `utils/logging.py:88`: Logger._core
- `storage/mongodb.py:131`: ClientOptions.pool_options
- `api/middleware/field_selection.py:113`: ModelMetaclass.get
- `connectors/apple_dictionary.py:270,363`: _parse_apple_definition
- `storage/mongodb.py`: get_synthesized_entry, save_synthesized_entry, save_entry

### 8. Import/Type Stub Issues (11 errors)
- Missing stubs: spacy, nltk, faiss, numpy, sentence_transformers, sklearn, contractions, wikitextparser, CoreServices, genanki, coolname

## Files Requiring Most Attention (by error count)
1. `ai/synthesizer.py`: 15 errors
2. `ai/synthesis_functions.py`: 11 errors
3. `api/routers/batch.py`: 11 errors
4. `connectors/apple_dictionary.py`: 8 errors
5. `api/routers/definitions.py`: 8 errors

## Next Steps
Fix each category systematically, starting with model structure issues, then async/await, then type annotations.