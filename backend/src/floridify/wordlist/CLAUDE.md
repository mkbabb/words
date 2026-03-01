# wordlist/

Vocabulary lists with SM-2 spaced repetition.

```
wordlist/
├── models.py (217)         # Wordlist(Document), WordlistEntry(Document)
├── review.py (128)         # SM-2 algorithm
├── parser.py (485)         # Text, JSON, CSV, TSV file parsers
├── stats.py (85)           # Statistics calculation
├── constants.py (30)       # Status thresholds, defaults
├── utils.py (31)           # Helper utilities
└── word_of_the_day/
    └── models.py (206)     # WordOfTheDay(Document)
```

**WordlistEntry**: word_id, frequency, status (Bronze -> Silver -> Gold), SM-2 fields (easiness_factor, interval, repetitions, next_review_date).

**SM-2**: quality rating 0-5 -> calculates next_review_date, new easiness factor, interval, repetitions.
