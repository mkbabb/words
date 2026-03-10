# storage/

MongoDB layer. Beanie ODM initialization, document model registration, connection pool.

```
storage/
├── __init__.py
├── dictionary.py       # Versioned save: save_entry_versioned(), save_definition_versioned()
└── mongodb.py          # MongoDBStorage, init_beanie(), get_storage() singleton
```

`MongoDBStorage` registers 19 document models with Beanie (Word, Definition, Example, Fact, Pronunciation, AudioMedia, ImageMedia, WordRelationship, WordList, BaseVersionedData, 6 Metadata subclasses, User, UserHistory, DictionaryEntry, BatchOperation).

`dictionary.py` handles dual-save: L3 version snapshot (SHA-256 content-addressable) + live document upsert with per-resource locking via `asyncio.Lock` defaultdicts.

Async throughout. Connection retry logic via `ensure_healthy_connection()`.
