# storage/

MongoDB layer. Beanie ODM initialization, 28 document models, 50-connection pool.

```
storage/
└── mongodb.py              # init_mongodb(), get_storage() singleton
```

Registers all document models with Beanie: Word, Definition, DictionaryEntry, Pronunciation, Example, Fact, Corpus, SearchIndex, TrieIndex, SemanticIndex, Wordlist, WordlistEntry, LiteratureSource, etc.

Async throughout. Automatic index creation. Transaction support when available. Connection retry logic.
