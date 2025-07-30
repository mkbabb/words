# API Refactoring Plan

## 1. Remove Synth Entries
- Delete `/backend/src/floridify/api/routers/synth_entries.py`
- Remove from router registration in main.py

## 2. Images API - Full CRUD
Current: Only GET endpoints
Target:
- `GET /images` - List images with pagination
- `POST /images` - Upload image
- `GET /images/{image_id}` - Get image metadata
- `GET /images/{image_id}/content` - Get image file
- `PUT /images/{image_id}` - Update image metadata
- `DELETE /images/{image_id}` - Delete image

## 3. Audio API - Full CRUD
Current: Only GET endpoints for cached audio
Target:
- `GET /audio` - List audio files with pagination
- `POST /audio` - Upload audio file
- `GET /audio/{audio_id}` - Get audio metadata
- `GET /audio/{audio_id}/content` - Get audio file
- `PUT /audio/{audio_id}` - Update audio metadata
- `DELETE /audio/{audio_id}` - Delete audio

## 4. AI Connector Updates
- Rename `word_suggestions` to `suggest_words` in:
  - `/backend/src/floridify/ai/connector.py`
  - `/backend/src/floridify/ai/base_connector.py`
  - All implementations

## 5. WordLists API Refactoring
Current structure is too complex. New structure:
```
/wordlists
  GET    /                     - List wordlists
  POST   /                     - Create wordlist
  GET    /{id}                 - Get wordlist
  PUT    /{id}                 - Update wordlist
  DELETE /{id}                 - Delete wordlist
  GET    /{id}/stats           - Get statistics
  
/wordlists/{id}/words
  GET    /                     - List words in wordlist
  POST   /                     - Add word to wordlist
  DELETE /{word}               - Remove word from wordlist
  
/wordlists/{id}/review
  GET    /                     - Get words due for review
  POST   /                     - Submit review results
  GET    /session              - Get review session
  POST   /session              - Start review session
```

Remove:
- `/wordlists/popular` - Not needed
- Complex review endpoints - Simplify with query params
- `/wordlists/{id}/visit/{word}` - Merge into review
- `/wordlists/{id}/mastery/{level}` - Use query params on words endpoint

## 6. Consistent Pagination
Ensure all list endpoints use:
- `offset` (default: 0)
- `limit` (default: 20, max: 100)
- `sort_by` (field name)
- `sort_order` (asc/desc)

## 7. Implementation Order
1. Remove synth_entries
2. Update AI connector (word_suggestions → suggest_words)
3. Implement full CRUD for images
4. Implement full CRUD for audio
5. Refactor wordlists API
6. Ensure consistent pagination
7. Run type checking
8. Run homogeneity audit