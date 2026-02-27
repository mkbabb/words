# Wordlist Module - Vocabulary Lists

Wordlist management with spaced repetition (SM-2 algorithm).

## Core Models

**Wordlist** (`models.py`):
- name, description, language, tags
- word_count, unique_word_count
- is_public, created_at, updated_at

**WordlistEntry** (`models.py`):
- word_id, wordlist_id
- frequency (how often encountered)
- status: Bronze → Silver → Gold
- SM-2 fields: easiness_factor, interval, repetitions
- next_review_date, last_reviewed_date

## Spaced Repetition

**SM-2 Algorithm** (`sm2.py`):
```python
def calculate_next_review(
    quality: int,  # 0-5 rating
    easiness_factor: float,
    interval: int,
    repetitions: int,
) -> tuple[datetime, float, int, int]:
    # Returns: (next_review_date, new_ef, new_interval, new_reps)
```

**Quality ratings**:
- 0: Complete blackout
- 1: Incorrect, but recognized
- 2: Incorrect, but easy to recall
- 3: Correct, but difficult
- 4: Correct, after hesitation
- 5: Perfect recall

**Progression**: Bronze (new) → Silver (learning) → Gold (mastered)
