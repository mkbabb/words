# Frontend to Backend API Endpoint Mapping

## Overview
This document maps all frontend API calls from `frontend/src/utils/api.ts` to their corresponding backend routes. 

**Critical Finding**: The backend routers have incorrect import syntax in `main.py` that will cause runtime errors.

## Critical Issues Found

### 1. Router Import Errors in main.py
The backend is trying to access `.router` on imported modules, but the modules are already router instances:

```python
# INCORRECT (current code):
app.include_router(lookup.router, prefix=API_V1_PREFIX, tags=["lookup"])

# CORRECT (should be):
app.include_router(lookup, prefix=API_V1_PREFIX, tags=["lookup"])
```

This affects ALL router imports in main.py lines 105-124.

### 2. Type Safety Issues
- 286 type errors found across the backend
- Repository return type mismatches
- Missing py.typed markers
- Extensive use of `Any` types

## API Endpoint Mapping

### ✅ Successfully Mapped Endpoints

| Frontend Call | Backend Route | Status |
|--------------|---------------|--------|
| `GET /api/v1/search` | `/search` router | ✅ Mapped |
| `GET /api/v1/lookup/{word}` | `/lookup` router | ✅ Mapped |
| `GET /api/v1/lookup/{word}/stream` | `/lookup` router (SSE) | ✅ Mapped |
| `POST /api/v1/lookup/{word}/regenerate-examples` | `/lookup` router | ✅ Mapped |
| `GET /api/v1/health` | `/health` router | ✅ Mapped |
| `GET /api/v1/suggestions` | `/suggestions` router | ✅ Mapped |
| `POST /api/v1/suggestions` | `/suggestions` router | ✅ Mapped |
| `POST /api/v1/ai/synthesize/synonyms` | `/ai` router | ✅ Mapped |
| `POST /api/v1/ai/suggest-words` | `/ai` router | ✅ Mapped |
| `GET /api/v1/ai/suggest-words/stream` | `/ai` router (SSE) | ✅ Mapped |
| `PUT /api/v1/definitions/{id}` | `/definitions` router | ✅ Mapped |
| `GET /api/v1/definitions/{id}` | `/definitions` router | ✅ Mapped |
| `POST /api/v1/definitions/{id}/regenerate` | `/definitions` router | ✅ Mapped |
| `PUT /api/v1/examples/{id}` | `/examples` router | ✅ Mapped |

### Wordlist Endpoints

| Frontend Call | Backend Route | Status |
|--------------|---------------|--------|
| `GET /api/v1/wordlists` | `/wordlists` router | ✅ Mapped |
| `GET /api/v1/wordlists/{id}` | `/wordlists` router | ✅ Mapped |
| `POST /api/v1/wordlists` | `/wordlists` router | ✅ Mapped |
| `POST /api/v1/wordlists/upload` | `/wordlists` router | ✅ Mapped |
| `PUT /api/v1/wordlists/{id}` | `/wordlists` router | ✅ Mapped |
| `DELETE /api/v1/wordlists/{id}` | `/wordlists` router | ✅ Mapped |
| `POST /api/v1/wordlists/{id}/words` | `/wordlists/{wordlist_id}/words` router | ✅ Mapped |
| `DELETE /api/v1/wordlists/{id}/words/{word}` | `/wordlists/{wordlist_id}/words` router | ✅ Mapped |
| `POST /api/v1/wordlists/{id}/search` | `/wordlists` router | ✅ Mapped |
| `GET /api/v1/wordlists/{id}/words` | `/wordlists/{wordlist_id}/words` router | ✅ Mapped |
| `GET /api/v1/wordlists/{id}/statistics` | `/wordlists` router | ✅ Mapped |

### ❌ Removed/Deprecated Endpoints

| Frontend Call | Status | Notes |
|--------------|--------|-------|
| `getSearchSuggestions()` | ❌ Removed | Returns empty array, suggests using vocabulary suggestions |

## Router Module Structure

### Refactored Architecture
```
routers/
├── __init__.py          # Imports all routers
├── ai/                  # AI-related endpoints
│   ├── __init__.py      # Exports main_router and suggestions_router
│   ├── main.py          # /ai endpoints
│   └── suggestions.py   # /suggestions endpoints
├── media/              # Media endpoints
│   ├── __init__.py     # Exports audio_router and images_router
│   ├── audio.py        # /audio endpoints
│   └── images.py       # /images endpoints
├── words/              # Word-related endpoints
│   ├── __init__.py     # Exports all word routers
│   ├── main.py         # /words endpoints
│   ├── definitions.py  # /definitions endpoints
│   ├── examples.py     # /examples endpoints
│   ├── facts.py        # /facts endpoints
│   └── word_of_the_day.py # /word-of-day endpoints
├── wordlists/          # Wordlist endpoints
│   ├── __init__.py     # Exports all wordlist routers
│   ├── main.py         # /wordlists endpoints
│   ├── words.py        # /wordlists/{id}/words endpoints
│   └── reviews.py      # /wordlists/{id}/review endpoints
├── batch.py            # Batch processing
├── corpus.py           # Corpus operations
├── health.py           # Health check
├── lookup.py           # Word lookup
└── search.py           # Search functionality
```

## Required Fixes

### 1. Fix Router Imports in main.py
All router imports need to remove the `.router` suffix since the imported objects are already router instances.

### 2. Fix Type Errors
- Update repository method signatures to match BaseRepository
- Add py.typed markers to all packages
- Replace `Any` types with proper type annotations
- Add runtime validation for external API responses

### 3. Verify Response Types
- Ensure all backend responses match frontend type definitions
- Add proper error response types
- Implement consistent response wrapping

## Conclusion

All frontend API endpoints have corresponding backend routes, but the backend has critical import errors that will prevent the application from starting. The refactoring has improved code organization but introduced type safety regressions that need immediate attention.