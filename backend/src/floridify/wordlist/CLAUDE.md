# wordlist/

Vocabulary lists with SM-2 spaced repetition.

```
wordlist/
├── __init__.py
├── constants.py        # Status thresholds, defaults
├── models.py           # WordList(Document), WordlistEntry
├── parser.py           # Text, JSON, CSV, TSV file parsers
├── review.py           # ReviewHistoryItem, ReviewData (SM-2 fields)
├── stats.py            # Statistics calculation
├── utils.py            # Helper utilities
└── word_of_the_day/
    ├── __init__.py
    └── models.py       # WordOfTheDay(Document)
```

**WordlistEntry**: word_id, frequency, status (Bronze -> Silver -> Gold), SM-2 fields (easiness_factor, interval, repetitions, next_review_date).

**SM-2**: Quality rating 0–5 -> calculates next_review_date, new easiness factor, interval, repetitions.
