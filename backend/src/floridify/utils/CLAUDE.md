# utils/

Cross-cutting utilities.

```
utils/
├── logging.py (436)        # Loguru + Rich structured logging
├── config.py (283)         # Config singleton (auth/config.toml)
├── paths.py (99)           # Platform-specific cache/data/config dirs
├── sanitization.py (123)   # Input validation, XSS prevention
├── json_output.py (101)    # JSON formatting
├── introspection.py (142)  # Pydantic field detection (used by VersionedDataManager)
└── timeouts.py (22)        # Timeout utilities
```

- `get_logger()` — Loguru-based with Rich formatting
- `@log_timing` / `@log_stage` — decorators for execution timing and pipeline stages
- `Config` — singleton for auth/config.toml (OpenAI keys, DB URLs, rate limits)
- `get_cache_directory()` / `get_data_directory()` — platform-specific paths
