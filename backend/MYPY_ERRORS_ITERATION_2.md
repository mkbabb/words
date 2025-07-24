# MyPy Errors - ITERATION 2

## Summary
After ITERATION 1 fixes:
- **Total Errors**: 88 errors in 21 files
- **Ruff Errors**: 0 (clean!)

## Error Categories

### 1. Missing Module/Type Stubs (21 errors)
- nltk: 6 errors
- sentence_transformers/faiss: 8 errors
- wiktionaryparser: 1 error
- contractions: 1 error
- coolname: 1 error
- genanki: 1 error
- BeautifulSoup: 1 error
- contractions: 1 error
- pyobjc: 1 error

### 2. Name/Import Errors (10 errors)
- DictionaryEntry not defined: 6 errors
- GeneratedExample not defined: 1 error
- _parse_apple_definition not defined: 1 error
- definitions not defined: 2 errors

### 3. Type Annotation Issues (25 errors)
- Missing return type annotations: 6 errors
- Returning Any from typed functions: 8 errors
- Need type annotation for variables: 2 errors
- Invalid type ignore comments: 4 errors
- Incompatible return types: 5 errors

### 4. Field/Argument Errors (32 errors)
- Missing named arguments: 5 errors
- Incompatible default values: 2 errors
- Unexpected keyword arguments: 1 error
- Wrong argument types: 15 errors
- Field() usage errors: 2 errors
- Generator type issues: 7 errors

## Detailed Error List

### src/floridify/utils/logging.py
```
Line 88: error: "Logger" has no attribute "_core"  [attr-defined]
```

### src/floridify/text/processor.py
```
Line 15: error: Cannot find implementation or library stub for "spacy"  [import-not-found]
Line 16: error: Cannot find implementation or library stub for "spacy.tokens"  [import-not-found]
Line 23: error: Skipping analyzing "nltk": module is not installed  [import-not-found]
Line 111: error: Function is missing a return type annotation  [no-untyped-def]
Line 125: error: Skipping analyzing "nltk.stem": module is not installed  [import-not-found]
Line 126: error: Skipping analyzing "nltk.tokenize": module is not installed  [import-not-found]
Line 142: error: Returning Any from function declared to return "str"  [no-any-return]
Line 149: error: Returning Any from function declared to return "list[str]"  [no-any-return]
Line 206: error: Call to untyped function "_lazy_load_nltk" in typed context  [no-untyped-call]
```

### src/floridify/search/semantic.py
```
Line 19: error: Invalid "type: ignore" comment  [syntax]
Line 19: error: Cannot find implementation or library stub for "sentence_transformers"  [import-not-found]
Line 20: error: Cannot find implementation or library stub for "faiss"  [import-not-found]
Line 21: error: Cannot find implementation or library stub for "faiss.swigfaiss_avx2"  [import-not-found]
Line 22: error: Invalid "type: ignore" comment  [syntax]
Line 24: error: Cannot find implementation or library stub for "sentence_transformers"  [import-not-found]
Line 25: error: Invalid "type: ignore" comment  [syntax]
Line 27: error: Cannot find implementation or library stub for "faiss"  [import-not-found]
Line 28: error: Invalid "type: ignore" comment  [syntax]
Line 51: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
```

### src/floridify/text/normalizer.py
```
Line 9: error: Skipping analyzing "contractions": module is not installed  [import-not-found]
```

### src/floridify/batch/word_filter.py
```
Line 9: error: Skipping analyzing "nltk": module is not installed  [import-not-found]
Line 10: error: Skipping analyzing "nltk.corpus": module is not installed  [import-not-found]
```

### src/floridify/list/parser.py
```
Line 9: error: Skipping analyzing "coolname": module is not installed  [import-not-found]
```

### src/floridify/storage/mongodb.py
```
Line 131: error: "Callable[[], ClientOptions]" has no attribute "max_pool_size"  [attr-defined]
Line 269: error: Incompatible return value type (got "MongoDBStorage | None", expected "MongoDBStorage")  [return-value]
```

### src/floridify/api/routers/search.py
```
Line 102: error: Argument "results" to "SemanticSearchResponse" has incompatible type "list[dict[str, Any]]"; expected "list[SearchResult]"  [arg-type]
```

### src/floridify/api/middleware/field_selection.py
```
Line 90: error: Returning Any from function declared to return "set[str]"  [no-any-return]
Line 113: error: "ModelMetaclass" has no attribute "field_info"  [attr-defined]
Line 121: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
```

### src/floridify/connectors/wiktionary.py
```
Line 10: error: Skipping analyzing "wiktionaryparser": module is not installed  [import-not-found]
Line 364: error: Missing named argument "frequency_band" for "Definition"  [call-arg]
Line 509: error: Missing named argument "frequency_band" for "Definition"  [call-arg]
```

### src/floridify/connectors/oxford.py
```
Line 251: error: Missing named argument "frequency_band" for "Definition"  [call-arg]
Line 259: error: Argument "language_register" to "Definition" has incompatible type "str | None"; expected "Literal['formal', 'informal', 'neutral', 'slang', 'technical'] | None"  [arg-type]
```

### src/floridify/connectors/apple_dictionary.py
```
Line 65: error: Skipping analyzing "bs4": module is not installed  [import-not-found]
Line 96: error: "None" not callable  [misc]
Line 97: error: Returning Any from function declared to return "str"  [no-any-return]
Line 275: error: Name "_parse_apple_definition" is not defined  [name-defined]
Line 362: error: Need type annotation for "definitions" (hint: "definitions: list[<type>] = ...")  [var-annotated]
Line 399: error: Name "definitions" is not defined  [name-defined]
Line 401: error: Returning Any from function declared to return "ProviderData"  [no-any-return]
Line 401: error: Name "definitions" is not defined  [name-defined]
```

### src/floridify/api/routers/words.py
```
Line 92: error: Argument "word_forms" to "Word" has incompatible type "list[str]"; expected "list[WordForm] | None"  [arg-type]
Line 172: error: Incompatible types in assignment (expression has type "list[str]", variable has type "list[WordForm] | None")  [assignment]
```

### src/floridify/ai/connector.py
```
Line 158: error: Returning Any from function declared to return "DictionaryEntryFromProviderResponse"  [no-any-return]
```

### src/floridify/cli/commands/database.py
```
Line 75: error: Name "DictionaryEntry" is not defined  [name-defined]
Line 137: error: Name "DictionaryEntry" is not defined  [name-defined]
Line 150: error: Name "DictionaryEntry" is not defined  [name-defined]
Line 153: error: Name "DictionaryEntry" is not defined  [name-defined]
```

### src/floridify/batch/apple_dictionary_extractor.py
```
Line 176: error: Argument 2 to "Definition" has incompatible type "DictionaryProvider"; expected "str"  [arg-type]
Line 181: error: Incompatible types in assignment (expression has type "str", variable has type "DictionaryProvider")  [assignment]
Line 216: error: Missing named argument "frequency_band" for "Definition"  [call-arg]
Line 216: error: Missing named argument "provider_data_id" for "Definition"  [call-arg]
Line 228: error: "MongoDBStorage" has no attribute "save_definition"  [attr-defined]
```

### src/floridify/anki/generator.py
```
Line 11: error: Skipping analyzing "genanki": module is not installed  [import-not-found]
Line 95: error: Name "DictionaryEntry" is not defined  [name-defined]
Line 99: error: Returning Any from function declared to return "Deck"  [no-any-return]
Line 104: error: Returning Any from function declared to return "Deck"  [no-any-return]
Line 234: error: Name "DictionaryEntry" is not defined  [name-defined]
Line 252: error: Name "DictionaryEntry" is not defined  [name-defined]
Line 341: error: Name "DictionaryEntry" is not defined  [name-defined]
```

### src/floridify/ai/synthesis_functions.py
```
Line 40: error: Returning Any from function declared to return "Pronunciation | None"  [no-any-return]
Line 105: error: Argument "form_type" to "WordForm" has incompatible type "Any"; expected "str"  [arg-type]
Line 180: error: Returning Any from function declared to return "str | None"  [no-any-return]
Line 251: error: Argument "text" to "Collocation" has incompatible type "Any"; expected "str"  [arg-type]
Line 252: error: Argument "type" to "Collocation" has incompatible type "Any"; expected "str"  [arg-type]
Line 253: error: Argument "frequency" to "Collocation" has incompatible type "Any"; expected "float | None"  [arg-type]
Line 276: error: Argument "type" to "UsageNote" has incompatible type "Any"; expected "str"  [arg-type]
Line 329: error: Argument "category" to "Fact" has incompatible type "str"; expected "Literal['general', 'technical', 'cultural', 'scientific'] | None"  [arg-type]
Line 330: error: Argument "model_info" to "Fact" has incompatible type "dict[str, str | float | None]"; expected "ModelInfo | None"  [arg-type]
Line 405: error: Need type annotation for "provider_data" (hint: "provider_data: list[<type>] = ...")  [var-annotated]
Line 409: error: Argument 1 to "append" of "list[Any]" has incompatible type "Coroutine[Any, Any, Etymology | None]"; expected "Any"  [arg-type]
Line 421: error: Argument 1 to "append" of "list[Any]" has incompatible type "Coroutine[Any, Any, list[str]]"; expected "Any"  [arg-type]
Line 424: error: Argument 1 to "append" of "list[Any]" has incompatible type "Coroutine[Any, Any, str | None]"; expected "Any"  [arg-type]
Line 430: error: Argument 1 to "append" of "list[Any]" has incompatible type "Coroutine[Any, Any, list[Fact]]"; expected "Any"  [arg-type]
```

### src/floridify/ai/synthesizer.py
```
Line 190: error: Incompatible types in assignment (expression has type "str", variable has type "DictionaryProvider"  [assignment]
Line 209: error: Argument "order" to "MeaningCluster" has incompatible type "float"; expected "int"  [arg-type]
```

### src/floridify/api/routers/definitions.py
```
Line 60: error: Incompatible default for argument "updates" (default has type "ellipsis", argument has type "DefinitionUpdate")  [assignment]
Line 101: error: Incompatible default for argument "request" (default has type "ellipsis", argument has type "ExampleRegenerationRequest")  [assignment]
Line 149: error: Unexpected keyword argument "model_info" for "Example"  [call-arg]
```

### src/floridify/api/routers/batch.py
```
Line 65: error: No overload variant of "Field" matches argument types "ellipsis", "int", "int", "str"  [call-overload]
Line 87: error: No overload variant of "Field" matches argument types "ellipsis", "int", "int"  [call-overload]
Line 257: error: Generator has incompatible item type "BatchResult | BaseException"; expected "BatchResult"  [misc]
Line 257: error: Item "BaseException" of "BatchResult | BaseException" has no attribute "status"  [union-attr]
Line 258: error: Generator has incompatible item type "BatchResult | BaseException"; expected "BatchResult"  [misc]
Line 258: error: Item "BaseException" of "BatchResult | BaseException" has no attribute "status"  [union-attr]
Line 261: error: Argument "results" to "BatchResponse" has incompatible type "list[BaseException | BatchResult]"; expected "list[BatchResult]"  [arg-type]
```