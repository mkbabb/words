# wordlist/

Vocabulary lists with SM-2 spaced repetition.

```
wordlist/
├── models.py (217)         # Wordlist(Document), WordlistEntry(Document)
├── review.py (116)         # SM-2 algorithm
├── parser.py (485)         # Text, JSON, CSV, TSV file parsers
├── stats.py (85)           # Statistics calculation
├── utils.py, constants.py
└── word_of_the_day/
    └── models.py           # WordOfTheDay(Document)
```

**WordlistEntry**: word_id, frequency, status (Bronze → Silver → Gold), SM-2 fields (easiness_factor, interval, repetitions, next_review_date).

**SM-2**: quality rating 0-5 → calculates next_review_date, new easiness factor, interval, repetitions.
