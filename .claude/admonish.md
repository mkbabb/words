# Quality Precepts

- **No fallback, workaround, or temp mocking behavior EVER**: Always simply and explicitly resolve errors.
    - **NEVER** attempt to preserve backwards compatibility.
    - **NEVER** alias deprecated functions or variables.
- **NEVER create variant implementations**: No "ClassEnhanced", "function_simple", or similar patterns unless explicitly requested. Perform all modifications in-line.
- **Tidy, trenchant code**: Clean up after yourself. Remove dead code, unused imports, and redundant logic.
- **No tautological implementations**
- **KISS**, **DRY**, **Explicit is ALWAYS better than implicit**

**Be fastidious and continue to iterate.**
