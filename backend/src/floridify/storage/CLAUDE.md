# Storage Module - MongoDB Layer

Beanie ODM integration, async MongoDB operations, database initialization.

## Key Components

**MongoDB Connection** (`mongodb.py`):
- `init_mongodb()` - Initialize Beanie with document models
- `get_storage()` - Database accessor singleton
- Connection pooling (50 connections default)
- Async/await throughout

**Document Models**: All MongoDB documents registered with Beanie:
- Word, Definition, DictionaryEntry, Pronunciation, Example, Fact
- Corpus, SearchIndex, TrieIndex, SemanticIndex
- Wordlist, WordlistEntry
- LiteratureSource, etc.

**Features**:
- Automatic index creation
- Async query methods
- Transaction support (when available)
- Connection retry logic
