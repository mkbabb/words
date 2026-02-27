# Utils Module - Shared Utilities

Cross-cutting utilities for logging, config, paths, validation, formatting.

## Key Modules

**Logging** (`logging.py`):
- `get_logger()` - Loguru-based structured logging
- `log_timing` - Decorator for execution timing
- `log_stage` - Decorator for pipeline stages with emojis
- Log levels: DEBUG, INFO, SUCCESS, WARNING, ERROR

**Config** (`config.py`):
- `Config` - Singleton for auth/config.toml
- OpenAI API keys
- Model selection (gpt-5, gpt-5-mini, gpt-5-nano)
- Database URLs (production/development)
- Provider API keys

**Paths** (`paths.py`):
- `get_cache_directory()` - Platform-specific cache dir
- `get_data_directory()` - Application data dir
- `get_config_directory()` - Config file location

**Validation** (`validation.py`):
- `validate_word_input()` - Word format validation
- `validate_language()` - Language code validation
- `validate_url()` - URL format checking

**Formatting** (`formatting.py`):
- `format_definition_for_display()` - Terminal-friendly formatting
- `format_pronunciation()` - IPA → readable format
- `format_date()` - Human-readable dates

**Introspection** (`introspection.py`):
- `extract_metadata_params()` - Pydantic field detection
- Used by VersionedDataManager for dynamic field mapping
