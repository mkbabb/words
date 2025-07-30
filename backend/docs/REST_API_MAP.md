# Floridify REST API Structure

## API Prefix: `/api/v1`

### Health
- `GET /health` - Health check

### Search
- `GET /search?q=` - Search words (query param)
- `GET /search/{query}` - Search words (path param)
- `GET /search/{query}/suggestions` - Get suggestions
- `POST /search/rebuild-index` - Rebuild search index

### Words
- `GET /words` - List words
- `POST /words` - Create word
- `GET /words/{word_id}` - Get word
- `PUT /words/{word_id}` - Update word
- `DELETE /words/{word_id}` - Delete word
- `GET /words/search/{query}` - Search words

### Definitions
- `GET /definitions` - List definitions
- `POST /definitions` - Create definition
- `GET /definitions/{definition_id}` - Get definition
- `PUT /definitions/{definition_id}` - Update definition
- `DELETE /definitions/{definition_id}` - Delete definition
- `POST /definitions/{definition_id}/images` - Bind image
- `POST /definitions/{definition_id}/regenerate` - Regenerate
- `POST /definitions/batch/regenerate` - Batch regenerate

### Examples
- `GET /examples` - List examples
- `POST /examples` - Create example
- `GET /examples/{example_id}` - Get example
- `PUT /examples/{example_id}` - Update example
- `DELETE /examples/{example_id}` - Delete example
- `POST /examples/definition/{definition_id}/generate` - Generate
- `POST /examples/batch/update` - Batch update

### Facts
- `GET /facts` - List facts
- `POST /facts` - Create fact
- `GET /facts/{fact_id}` - Get fact
- `PUT /facts/{fact_id}` - Update fact
- `DELETE /facts/{fact_id}` - Delete fact

### WordLists
- `GET /wordlists` - List wordlists
- `POST /wordlists` - Create wordlist
- `GET /wordlists/{wordlist_id}` - Get wordlist
- `PUT /wordlists/{wordlist_id}` - Update wordlist
- `DELETE /wordlists/{wordlist_id}` - Delete wordlist
- `GET /wordlists/{wordlist_id}/words` - Get words
- `POST /wordlists/{wordlist_id}/words` - Add word
- `DELETE /wordlists/{wordlist_id}/words/{word}` - Remove word
- `POST /wordlists/{wordlist_id}/review` - Review word
- `POST /wordlists/{wordlist_id}/visit/{word}` - Visit word
- `POST /wordlists/{wordlist_id}/study` - Start study
- `GET /wordlists/{wordlist_id}/due` - Get due words
- `GET /wordlists/{wordlist_id}/mastery/{level}` - Get by mastery
- `GET /wordlists/{wordlist_id}/statistics` - Get stats
- `GET /wordlists/search/{query}` - Search wordlists
- `GET /wordlists/popular` - Get popular
- `POST /wordlists/{wordlist_id}/search` - Search in list
- `POST /wordlists/upload` - Upload file

### Lookup
- `GET /lookup/{word}` - Lookup word
- `GET /lookup/{word}/stream` - Stream lookup

### AI
- `POST /ai/synthesize` - Synthesize
- `POST /ai/synthesize/pronunciation` - Synthesize pronunciation
- `POST /ai/synthesize/synonyms` - Synthesize synonyms
- `POST /ai/synthesize/antonyms` - Synthesize antonyms
- `POST /ai/suggestions` - Get suggestions
- `POST /ai/generate/word-forms` - Generate forms
- `POST /ai/generate/examples` - Generate examples
- `POST /ai/generate/facts` - Generate facts
- `POST /ai/assess/frequency` - Assess frequency
- `POST /ai/assess/cefr` - Assess CEFR level
- `POST /ai/assess/register` - Assess register
- `POST /ai/assess/domain` - Assess domain
- `POST /ai/assess/collocations` - Get collocations
- `POST /ai/assess/grammar-patterns` - Get patterns
- `POST /ai/assess/regional-variants` - Get variants
- `POST /ai/usage-notes` - Get usage notes
- `POST /ai/validate-query` - Validate query
- `POST /ai/suggest-words` - Suggest words
- `GET /ai/suggest-words/stream` - Stream suggestions

### Batch
- `POST /batch/lookup` - Batch lookup
- `POST /batch/definitions/update` - Batch update defs
- `POST /batch/execute` - Execute batch

### Corpus
- `GET /corpus` - List corpora
- `POST /corpus` - Create corpus
- `GET /corpus/{corpus_id}` - Get corpus
- `POST /corpus/{corpus_id}/search` - Search corpus
- `GET /corpus-stats` - Get stats

### Audio
- `GET /audio/files/{audio_id}` - Get audio file
- `GET /audio/cache/{subdir}/{filename}` - Get cached

### Images
- `GET /images/{image_id}` - Get image info
- `GET /images/{image_id}/content` - Get image data

### Synonyms
- `GET /synonyms/{word}` - Get synonyms

### Synth Entries
- `POST /synth-entries/{entry_id}/images` - Add image
- `POST /synth-entries/{entry_id}/images/upload` - Upload image

### Word of the Day
- `GET /word-of-the-day/current` - Get current
- `POST /word-of-the-day/send` - Send WOTD
- `GET /word-of-the-day/history` - Get history
- `GET /word-of-the-day/config` - Get config
- `PUT /word-of-the-day/config` - Update config
- `GET /word-of-the-day/batches` - List batches
- `GET /word-of-the-day/batches/{batch_id}` - Get batch
- `PUT /word-of-the-day/batches/{batch_id}/config` - Update batch
- `POST /word-of-the-day/batches/{batch_id}/generate` - Generate

### Suggestions
- `GET /suggestions/{word}` - Get suggestions

## Issues Found:

1. **Inconsistent Query Params**: Some endpoints use raw query params, others use models
2. **Duplicate Search**: Both `/search` and `/words/search/{query}` exist
3. **Nested Imports**: Found in several routers
4. **Image Binding**: Should be generic definition update
5. **Batch Definition Update**: Appears unused/redundant
6. **REST Naming**: Some endpoints don't follow conventions
7. **Response Models**: Not all endpoints have proper response models