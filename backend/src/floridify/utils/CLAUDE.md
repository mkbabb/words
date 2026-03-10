# utils/

Cross-cutting utilities.

```
utils/
├── __init__.py
├── config.py               # Config singleton (auth/config.toml)
├── introspection.py        # Pydantic field detection (used by VersionedDataManager)
├── json_output.py          # JSON formatting
├── language_precedence.py  # language_code(), merge_language_precedence()
├── logging.py              # Loguru + Rich structured logging
├── paths.py                # Platform-specific cache/data/config dirs
├── sanitization.py         # Input validation, XSS prevention
├── threading_config.py     # configure_threading()—macOS libomp triple-conflict fix
└── timeouts.py             # Timeout utilities
```

- `get_logger()`—Loguru-based with Rich formatting
- `@log_timing` / `@log_stage`—decorators for execution timing and pipeline stages
- `Config`—singleton for auth/config.toml (OpenAI keys, DB URLs, rate limits)
- `get_cache_directory()` / `get_data_directory()`—platform-specific paths
- `configure_threading()`—sets OMP_NUM_THREADS=1 on macOS to prevent SIGSEGV from competing OpenMP runtimes
