# Wordlist Pipeline

A spaced repetition vocabulary learning system built on SM-2 scheduling, with mastery tracking, pre-commit reconciliation for misspellings, and Anki flashcard export.

## Table of Contents

1. [Background](#1-background)
2. [SM-2 Algorithm](#2-sm-2-algorithm)
3. [Card State Machine](#3-card-state-machine)
4. [Mastery System](#4-mastery-system)
5. [Leech Detection](#5-leech-detection)
6. [Review Scheduling](#6-review-scheduling)
7. [Temperature System](#7-temperature-system)
8. [Statistics](#8-statistics)
9. [Wordlist CRUD](#9-wordlist-crud)
10. [File Parsing](#10-file-parsing)
11. [Reconciliation](#11-reconciliation)
12. [Search Integration](#12-search-integration)
13. [Anki Export](#13-anki-export)
14. [Key Files](#14-key-files)

---

## 1. Background

Human memory decays. In 1885, Hermann Ebbinghaus published *Über das Gedächtnis*, documenting what became the **forgetting curve**: newly acquired information follows an approximately exponential retention decay, with the steepest drop occurring in the first 24 hours [Ebbinghaus (1885)]. Without reinforcement, roughly 70% of learned material is lost within a day.

Ebbinghaus also observed the **spacing effect**—that distributing practice across time produces stronger retention than massing it into a single session. A word reviewed three times over three days is retained far longer than a word reviewed three times in one sitting. This finding has been replicated across more than a century of memory research and remains one of the most robust results in cognitive psychology.

In 1987, Piotr Wozniak formalized this insight into an algorithm. **SM-2** (SuperMemo algorithm #2) was the first computer-based spaced repetition system, designed to schedule reviews at the point where retention is about to fall below a target threshold [Wozniak & Gorzelanczyk (1994)]. The algorithm tracks two variables per card—an **ease factor** (difficulty multiplier) and a **repetition count**—and uses them to compute exponentially growing inter-review intervals. Cards answered correctly with confidence receive progressively longer intervals; cards answered incorrectly are reset and re-learned.

SM-2 has two tunable parameters (ease factor bounds and quality threshold) and produces intervals that are immediately interpretable: "this word will next appear in 12 days." Newer algorithms like FSRS [Ye (2022)] use machine-learned parameters and achieve marginally higher retention accuracy, but at the cost of opacity and implementation complexity. For a dictionary application where the user population is small and interpretability matters, SM-2's simplicity and three decades of empirical validation make it the appropriate choice.

Floridify extends SM-2 with an Anki-style card state machine, adding sub-day learning intervals (1-minute and 10-minute steps) that provide immediate reinforcement before the exponential schedule takes over. This hybrid approach addresses SM-2's original weakness—it had no mechanism for intra-day repetition of newly encountered words.

## 2. SM-2 Algorithm

### The Ease Factor Update

The core of SM-2 is an adaptive difficulty multiplier called the **ease factor** (EF). After each review, the ease factor is updated based on the user's self-reported quality score *q* (0--5):

```
EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
```

This quadratic adjustment produces the following deltas for each quality score:

| Quality | Label     | EF delta |
|---------|-----------|----------|
| 0       | Again     | -0.80    |
| 1       | Hard      | -0.54    |
| 2       | Difficult | -0.32    |
| 3       | Okay      | -0.14    |
| 4       | Good      | +0.00    |
| 5       | Easy      | +0.10    |

A quality score of 4 ("correct with minor hesitation") is the neutral point: the ease factor doesn't change. Scores below 4 reduce it; only a score of 5 increases it. The ease factor is clamped to `[1.3, 4.0]`:

```
EF = max(1.3, min(EF', 4.0))
```

The default ease factor is **2.5**. A card that always receives quality 4 ("Good") maintains this default. A card that consistently receives quality 3 ("Okay") drifts toward 1.3 over many reviews, shrinking its intervals and causing more frequent reviews—the appropriate response for a word the learner finds persistently difficult.

### Interval Calculation

The interval sequence depends on the quality score and the card's review history:

- **Quality < 3** (failure): The interval resets. The card enters relearning.
- **First successful review** (`repetitions == 0` after graduation): interval = **1 day**
- **Second successful review** (`repetitions == 1`): interval = **6 days**
- **Subsequent reviews** (`repetitions >= 2`): interval = `I(n-1) * EF`

The constants from [`wordlist/constants.py`](../backend/src/floridify/wordlist/constants.py):

| Constant                  | Value | Description                          |
|---------------------------|-------|--------------------------------------|
| `SM2_MIN_EASE_FACTOR`     | 1.3   | Minimum ease factor floor            |
| `SM2_DEFAULT_EASE_FACTOR` | 2.5   | Starting ease factor for new cards   |
| `SM2_MAX_EASE_FACTOR`     | 4.0   | Maximum ease factor ceiling          |
| `SM2_QUALITY_THRESHOLD`   | 3     | Scores below this count as failure   |
| `GRADUATING_INTERVAL_DAYS`| 1     | First review interval after learning |
| `EASY_INTERVAL_DAYS`      | 4     | Interval when graduating via "Easy"  |
| `MAX_INTERVAL_DAYS`       | 36500 | Hard cap (~100 years)                |

### Review-Phase Modifiers

During the review phase (YOUNG/MATURE cards), the interval calculation branches by quality:

- **Quality 2 (Hard):** `interval = round(interval * 1.2)` — a slight increase without adjusting EF. The `HARD_INTERVAL_MULTIPLIER` of 1.2 prevents interval stagnation while acknowledging difficulty.
- **Quality 3--4 (Good):** `interval = fuzz(round(interval * EF))` — standard SM-2 multiplication.
- **Quality 5 (Easy):** `interval = fuzz(round(interval * EF * 1.3))` — the `EASY_BONUS` of 1.3 accelerates cards the learner finds effortless, clearing them from the review queue faster.

## 3. Card State Machine

The system tracks five states modeled after Anki's card lifecycle. States govern which interval logic applies and how failures are handled.

```
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │
    ┌───────┐   first    ┌──────────┐   graduate   ┌───────┐   interval   ┌────────┐
    │  NEW  │ ────────── │ LEARNING │ ──────────── │ YOUNG │ ──≥ 21 d──── │ MATURE │
    │       │   review   │          │   (steps     │       │              │        │
    └───────┘            └──────────┘   complete)  └───┬───┘              └───┬────┘
                              ▲                        │                     │
                              │              lapse     │         lapse       │
                              │         (quality < 3)  │    (quality < 3)    │
                              │                        ▼                     │
                              │                  ┌─────────────┐             │
                              │                  │ RELEARNING  │◄────────────┘
                              │                  │             │
                              │                  └──────┬──────┘
                              │                         │
                              │         graduate        │
                              └─────────────────────────┘
                              (back to YOUNG with saved interval)
```

### Learning Steps

When a card enters LEARNING (first review of a NEW card) or RELEARNING (lapse from YOUNG/MATURE), it follows a sequence of sub-day steps:

| State        | Steps (minutes) | Constant                    |
|--------------|----------------|-----------------------------|
| LEARNING     | [1, 10]        | `LEARNING_STEPS_MINUTES`    |
| RELEARNING   | [10]           | `RELEARNING_STEPS_MINUTES`  |

Intervals are stored as fractional days: a 1-minute step becomes `1 / (24 * 60) ≈ 0.000694` days. The scheduler converts these to minute-precision `timedelta` values when computing `next_review_date`.

### State Transitions

**NEW → LEARNING:** On first review, regardless of quality. This is not counted as a lapse.

**LEARNING → LEARNING:** Quality < 3 (Again) resets to step 0. Quality 3--4 (Good) advances to the next step. If no more steps remain, the card graduates.

**LEARNING → YOUNG:** Graduation occurs when all learning steps are completed with quality ≥ 3, or immediately on quality 5 (Easy). The graduating interval is 1 day (normal) or 4 days (Easy).

**YOUNG → MATURE:** Automatic promotion when the computed interval reaches 21 days (`MATURE_INTERVAL_DAYS`).

**YOUNG/MATURE → RELEARNING:** A lapse (quality < 3). The current interval is saved in `graduated_interval` so it can be restored after relearning. The lapse counter increments, and the card enters RELEARNING at step 0 (10 minutes).

**RELEARNING → YOUNG:** Graduation from relearning restores the saved `graduated_interval` (or `GRADUATING_INTERVAL_DAYS`, whichever is larger), preserving the card's history rather than resetting to 1 day.

The Anki-style state machine exists because raw SM-2 has no sub-day intervals. A user encountering a word for the first time needs reinforcement within minutes, not a day later. The LEARNING/RELEARNING states provide this immediate loop before handing off to the exponential schedule.

## 4. Mastery System

Each word in a wordlist carries a mastery level derived from its card state and review performance. There are four tiers:

| Mastery Level | Ord | Conditions                                           |
|---------------|-----|------------------------------------------------------|
| DEFAULT       | 0   | Card is NEW or LEARNING                              |
| BRONZE        | 1   | Card is YOUNG, or RELEARNING (demoted on lapse)      |
| SILVER        | 2   | Card is YOUNG with `repetitions >= 5` and `EF >= 2.3`|
| GOLD          | 3   | Card is MATURE (interval ≥ 21 days)                  |

Mastery is recomputed after every review via `_update_mastery_level()` on [`WordListItem`](../backend/src/floridify/wordlist/models.py). The rules encode a progression: DEFAULT represents an unlearned word, BRONZE indicates active learning, SILVER requires sustained success (five consecutive correct reviews at moderate ease), and GOLD requires long-term retention.

**Promotion:** A YOUNG card is promoted to SILVER when it accumulates 5 successful repetitions with an ease factor at or above 2.3. When its interval reaches 21 days, it becomes MATURE and earns GOLD.

**Demotion:** A lapse (quality < 3) on a YOUNG or MATURE card immediately enters RELEARNING and demotes to BRONZE. From there, the card must re-graduate through YOUNG and re-earn SILVER or GOLD. This prevents a single lucky streak from permanently mastering a word.

The `MasteryLevel` enum supports comparison operators (`<`, `<=`, `>`, `>=`) via a numeric ordering, enabling queries like "show all words at or below SILVER."

## 5. Leech Detection

A **leech** is a card that has lapsed too many times—a word the learner repeatedly fails to retain despite repeated exposure. The threshold is **8 lapses** (`LEECH_THRESHOLD`).

When `lapse_count` reaches or exceeds 8, the `is_leech` flag is set on `ReviewData`. Leech detection is checked after every lapse in `_check_leech()`.

Leeches are not automatically suspended. The API provides explicit endpoints for suspension management:

- `GET /{wordlist_id}/review/leeches` — lists all leech words with their lapse counts and suspension status
- `POST /{wordlist_id}/review/leeches/{word}/suspend` — removes the word from future review sessions
- `POST /{wordlist_id}/review/leeches/{word}/unsuspend` — re-enables the word for reviews

The `suspended` flag on [`WordListItem`](../backend/src/floridify/wordlist/models.py) is checked during review session generation: suspended items are excluded from the `GET /{wordlist_id}/review/due` and `GET /{wordlist_id}/review/session` responses. This lets users consciously decide whether to keep struggling with a leech or set it aside.

## 6. Review Scheduling

### Due Date Computation

After each review, `next_review_date` is calculated from the current time plus the computed interval:

```python
if interval < 1:
    # Sub-day: use minutes (learning/relearning steps)
    minutes = interval * 24 * 60
    next_review_date = now + timedelta(minutes=max(minutes, 1))
else:
    next_review_date = now + timedelta(days=interval)
```

A word is due for review when `next_review_date <= now`. The `get_overdue_days()` method returns how many days past due a word is (negative if not yet due), used to prioritize the most overdue words in review sessions.

### Interval Fuzz

For intervals greater than 1 day, a random **fuzz** of ±5% (`INTERVAL_FUZZ_RANGE = 0.05`) is applied:

```python
fuzz = interval * 0.05
return max(1, interval + random.uniform(-fuzz, fuzz))
```

This prevents review clustering: without fuzz, two words learned on the same day with the same ease factor would always come due together, creating uneven daily review loads. The fuzz spreads reviews across adjacent days.

### Predicted Intervals

The frontend displays the next interval for each quality button ("Again: 10m", "Good: 4d", "Easy: 7d"). The `get_predicted_intervals()` method computes these by cloning the current `ReviewData` and simulating each quality score 0--5:

```python
def get_predicted_intervals(self) -> dict[int, float]:
    predictions = {}
    for q in range(6):
        clone = self.model_copy(deep=True)
        clone.process_review(q)
        predictions[q] = clone.interval
    return predictions
```

This clone-and-simulate approach keeps prediction logic in sync with actual review logic without duplication.

### Review History

Each review appends a `ReviewHistoryItem` (date, quality, interval, ease factor, card state) to the `review_history` list, capped at **50 entries** (`MAX_REVIEW_HISTORY`). When the cap is reached, the oldest entries are discarded. This provides an audit trail for analytics while bounding storage per word.

## 7. Temperature System

Each word carries a binary **temperature**: HOT or COLD.

- **HOT**: Set when the word is visited (`mark_visited()`) or reviewed (`review()`).
- **COLD**: Applied lazily when the word is read. If the word has been HOT for 24 hours or more (`COOLING_THRESHOLD_HOURS = 24`), `update_temperature()` transitions it to COLD.

Temperature evaluation is lazy: the cooling check runs in `update_temperature()`, called when listing words or fetching search results. There is no background timer. This design avoids write amplification—thousands of words cooling simultaneously would require thousands of database writes. Instead, temperature is evaluated on read and only persisted when the item is next saved for another reason.

Temperature enables UI features like "recently studied" filtering. The API supports `hot_only` query parameters on word listing and search endpoints.

## 8. Statistics

### Denormalized Stats

The [`WordList`](../backend/src/floridify/wordlist/models.py) document stores denormalized counts (`total_words`, `unique_words`) and a nested [`LearningStats`](../backend/src/floridify/wordlist/stats.py) object for fast reads:

| Field                | Description                              |
|----------------------|------------------------------------------|
| `total_reviews`      | Lifetime review session count            |
| `words_mastered`     | Words at GOLD mastery level              |
| `average_ease_factor`| Mean EF across all words                 |
| `retention_rate`     | `1 - (lapses / (repetitions + lapses))`  |
| `streak_days`        | Consecutive calendar days with study     |
| `last_study_date`    | Timestamp of most recent session         |
| `study_time_minutes` | Cumulative study time                    |

These stats are recomputed via MongoDB aggregation whenever words are added, removed, or reviewed. The [`recompute_stats()`](../backend/src/floridify/api/services/wordlist_stats.py) function runs a `$group` pipeline over `WordListItemDoc`:

```javascript
{
  $group: {
    _id: null,
    unique_words: { $sum: 1 },
    total_words: { $sum: "$frequency" },
    words_mastered: { $sum: { $cond: [{ $eq: ["$mastery_level", "gold"] }, 1, 0] } },
    avg_ease: { $avg: "$review_data.ease_factor" },
    total_reps: { $sum: "$review_data.repetitions" },
    total_lapses: { $sum: "$review_data.lapse_count" }
  }
}
```

### Detailed Stats

The `GET /{wordlist_id}/stats` endpoint returns richer analytics computed via a `$facet` aggregation:

- **Mastery distribution**: Count of words at each mastery level (DEFAULT, BRONZE, SILVER, GOLD)
- **Temperature distribution**: Count of HOT vs COLD words
- **Due-for-review count**: Words with `next_review_date <= now`
- **Most frequent words**: Top 5 by `frequency`
- **Hot words**: Top 5 most recently visited HOT words

The `$facet` stage executes the mastery/temperature/due aggregations in a single pipeline pass, avoiding multiple collection scans.

### Retention Rate

Retention rate is computed as:

```
retention_rate = 1 - (total_lapses / (total_repetitions + total_lapses))
```

A wordlist where 90 reviews succeeded and 10 lapsed has a retention rate of 0.9. This metric is denormalized on the `WordList` document for dashboard display and recomputed on every stats refresh.

### Study Streaks

The `LearningStats.record_study_session()` method maintains a streak counter. If the previous study date was exactly yesterday, the streak increments. If more than one day has passed, it resets to 1. The `is_streak_active()` check returns `true` if the user has studied today or yesterday. Review sessions expose streak context to the frontend for motivational cues.

## 9. Wordlist CRUD

### Data Model

Wordlists use a **normalized** storage model with two collections:

- **`word_lists`** ([`WordList`](../backend/src/floridify/wordlist/models.py)): Metadata document (name, description, tags, owner, denormalized stats).
- **`word_list_items`** ([`WordListItemDoc`](../backend/src/floridify/wordlist/models.py)): One document per word-in-wordlist, containing the word reference (`word_id`), review data, mastery, temperature, and user notes.

This separation means listing wordlists (for a sidebar or dashboard) never loads word-level data. Word data is fetched via `GET /{wordlist_id}/words` with pagination.

`WordListItemDoc` has a compound unique index on `(wordlist_id, word_id)`, preventing duplicate words within a single wordlist. Additional indexes support queries by next review date, mastery level, added date, and temperature.

### Content-Addressable Hashing

Each wordlist has a `hash_id` computed from its word content via SHA-256:

```python
def generate_wordlist_hash(words: Iterable[str]) -> str:
    normalized = sorted({word.strip().lower() for word in words if word.strip()})
    payload = "|".join(normalized)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

The words are lowercased, deduplicated, sorted, and pipe-joined before hashing. This produces a stable, order-independent fingerprint. On creation, the repository checks whether a wordlist with the same hash already exists—if so, it returns the existing wordlist with `created=False` rather than creating a duplicate. This prevents accidental duplicate uploads without requiring word-by-word comparison.

### Optimistic Locking

The `WordAddRequest` model accepts an optional `version` field. When provided, the repository compares it against the wordlist's current version before mutating:

```python
if version is not None and wordlist.version != version:
    raise VersionConflictException(expected=version, actual=wordlist.version)
```

This enables safe concurrent editing from multiple clients (mobile + desktop). A client reads the wordlist with its current version number, submits a modification with that version, and gets a 409 Conflict if another client modified the wordlist in the interim. The client can then re-read, merge, and retry. This avoids the latency and deadlock risks of pessimistic locking.

### Batch Word Creation

The `batch_get_or_create_words()` method on [`WordListRepository`](../backend/src/floridify/api/repositories/wordlist_repository.py) optimizes word creation:

1. Normalize all input words via `normalize()`
2. Bulk lookup existing `Word` documents with `$in` query
3. Bulk create missing words via `insert_many()`
4. Return word IDs in input order

This reduces a wordlist with 500 words from 500 individual database queries to 2 (one `find`, one `insert_many`).

### CRUD Endpoints

| Method | Path                          | Description                        |
|--------|-------------------------------|------------------------------------|
| GET    | `/wordlists`                  | List wordlists with filtering      |
| POST   | `/wordlists`                  | Create a new wordlist              |
| GET    | `/wordlists/{id}`             | Get wordlist metadata              |
| PUT    | `/wordlists/{id}`             | Update wordlist metadata           |
| DELETE | `/wordlists/{id}`             | Delete wordlist and all items      |
| POST   | `/wordlists/{id}/clone`       | Clone with reset learning stats    |
| GET    | `/wordlists/{id}/export`      | Export as txt, csv, or json        |
| POST   | `/wordlists/upload`           | Upload from file                   |
| POST   | `/wordlists/upload/stream`    | Upload with SSE progress           |

## 10. File Parsing

The [`parser`](../backend/src/floridify/wordlist/parser.py) module supports six text-based formats with automatic detection by file extension:

| Extension            | Parser              | Notes                              |
|----------------------|---------------------|------------------------------------|
| `.txt`               | `parse_text_file`   | Numbered, bulleted, or plain lists |
| `.csv`, `.tsv`       | `parse_csv_file`    | Auto-detects delimiter via sniffer |
| `.md`, `.markdown`   | `parse_markdown_file`| Lists + table extraction           |
| `.json`, `.jsonl`    | `parse_json_file`   | Array or `{words: [...]}` objects  |

### Text Normalization

All parsers run input through `preserve_text_format()`, which applies NFC Unicode normalization, strips zero-width characters, normalizes curly quotes/apostrophes to ASCII, converts em/en dashes to hyphens, and collapses whitespace.

### Phrase Detection

The `_looks_like_phrase()` heuristic distinguishes multi-word phrases from word lists separated by spaces. A multi-word input is treated as a single phrase (kept together) if it contains articles, prepositions, or conjunctions ("the art of war"), matches a set of common Latin/foreign phrases ("quid pro quo"), or consists entirely of capitalized words (proper noun phrase). Otherwise, words on the same line separated by spaces are split into individual entries.

### Entry Collapsing

After parsing, `collapse_entries()` merges duplicates by normalized lowercased key. Duplicate entries sum their frequencies and preserve the first non-null notes value. This means uploading a file containing "perspicacious" three times produces one entry with `frequency=3`.

### Validation

The `is_valid_word()` function rejects entries shorter than 1 character or longer than 100, entries containing no Latin/Cyrillic letters, and entries consisting solely of digits or punctuation.

### CSV Format

CSV files use the first column for word text. The optional second column is coerced to a frequency integer. The optional third column is treated as notes. A header row is detected if the first cell matches common header words (word, term, vocabulary, etc.) and automatically skipped.

## 11. Reconciliation

The [`reconcile`](../backend/src/floridify/wordlist/reconcile.py) module provides a pre-commit spell-check for wordlist uploads and word additions. Before persisting new words, the system categorizes each entry as **exact**, **ambiguous**, or **unresolved**.

### Reconciliation Flow

1. **Collapse entries**: Deduplicate and normalize the input entries.
2. **Batch exact lookup**: Query the `Word` collection with `$in` on the normalized texts. Words with an exact match in the database are immediately categorized as "exact."
3. **Smart cascade search**: For non-exact entries, run the multi-method search engine (without semantic search, for speed) with `SearchMode.SMART` and a minimum score of 0.55. This produces ranked candidates via exact, prefix, substring, fuzzy, and phonetic matching.
4. **Categorize results**:
   - **exact**: Normalized text matches a `Word` document exactly (score 1.0).
   - **ambiguous**: No exact match, but the search engine found candidates above the score threshold.
   - **unresolved**: No candidates found. The word may be a neologism, proper noun, or misspelling.
5. **Duplicate awareness**: If a `wordlist_id` is provided, each candidate is annotated with `already_in_wordlist: true/false` by checking membership in the target wordlist's `WordListItemDoc` set.

### Response Structure

The `ReconcilePreviewResponse` groups entries into three lists (`exact`, `ambiguous`, `unresolved`) with a summary:

```json
{
  "exact": [{ "source_text": "perspicacious", "resolved_text": "perspicacious", "status": "exact", ... }],
  "ambiguous": [{ "source_text": "persipacious", "candidates": [...], "status": "ambiguous", ... }],
  "unresolved": [{ "source_text": "xyzzy", "candidates": [], "status": "unresolved", ... }],
  "summary": {
    "total_entries": 3,
    "exact_entries": 1,
    "ambiguous_entries": 1,
    "unresolved_entries": 1
  }
}
```

The frontend uses this preview to let the user accept, correct, or dismiss each entry before committing the upload. The API endpoint is `POST /wordlists/reconcile-preview`.

## 12. Search Integration

Each wordlist gets a dedicated search **corpus** named `wordlist_{id}`. This corpus powers multi-method search (exact, prefix, substring, fuzzy, semantic) scoped to the words in that specific wordlist.

### Corpus Lifecycle

- **Creation**: When a wordlist is created with words, `_create_wordlist_corpus()` builds a [`Corpus`](../backend/src/floridify/corpus/core.py) from the word texts and registers it with the [`TreeCorpusManager`](../backend/src/floridify/corpus/manager.py).
- **Update**: When words are added or removed, `_finalize_word_change()` updates the corpus vocabulary and bumps its version. The search engine detects the vocabulary hash change and rebuilds its indices.
- **Invalidation**: On wordlist deletion, the corpus is invalidated and any cached `Search` instances for that corpus are evicted via `invalidate_by_corpus()`.

### Search Endpoints

| Method | Path                                   | Description                                |
|--------|----------------------------------------|--------------------------------------------|
| POST   | `/wordlists/{id}/search`               | Search within a specific wordlist          |
| POST   | `/wordlists/search-all`                | Search across all user wordlists           |
| GET    | `/wordlists/search/{query}`            | Search wordlist names (for navigation)     |

The per-wordlist search creates a `Search` instance with semantic search enabled, uses the smart cascade (exact → prefix → substring → fuzzy → semantic), then enriches results with wordlist-specific metadata (mastery, temperature, review data) via `enrich_search_results_with_wordlist_data()`. Post-search filtering by mastery level, temperature, and due status is applied server-side before pagination.

Cross-wordlist search (`search-all`) runs parallel searches across all user wordlists with a concurrency semaphore (capped at 10), merges results by score, and paginates the combined set.

## 13. Anki Export

The [`anki/`](../backend/src/floridify/anki/) module generates Anki-compatible flashcards from wordlist content.

### Card Types

Four card types are defined in the [`CardType`](../backend/src/floridify/anki/constants.py) enum. Two are fully implemented:

| Card Type         | Front                                         | Back                                |
|-------------------|-----------------------------------------------|-------------------------------------|
| `BEST_DESCRIBES`  | Word + pronunciation + 4 multiple-choice definitions | Correct answer + definition + examples + synonyms |
| `FILL_IN_BLANK`   | Pronunciation + cloze sentence + 4 word choices       | Word + correct answer + definition + examples     |

Two additional types (`DEFINITION_TO_WORD`, `WORD_TO_DEFINITION`) are registered but not yet implemented.

### AI-Generated Content

Card content is generated via the [`AIConnector`](../backend/src/floridify/ai/connector/base.py). For each word-definition pair:

- **BEST_DESCRIBES**: `generate_anki_best_describes()` produces four multiple-choice definitions (one correct, three distractors that are semantically related but incorrect).
- **FILL_IN_BLANK**: `generate_anki_fill_blank()` produces a context sentence with the target word removed and four word choices.

If a definition has fewer than 3 example sentences, additional examples are generated via `generate_examples()` to ensure the card back has sufficient context.

### Field Mapping

Both card types share a common field set. All user/AI content is HTML-escaped via `html.escape()` to prevent XSS in Anki's webview renderer.

| Field             | Source                          | Notes                            |
|-------------------|---------------------------------|----------------------------------|
| `Word`            | `DictionaryEntry.word`          | The vocabulary word              |
| `Pronunciation`   | `DictionaryEntry.pronunciation` | IPA phonetic transcription       |
| `PartOfSpeech`    | `Definition.part_of_speech`     | noun, verb, adjective, etc.      |
| `ChoiceA`--`D`    | AI-generated                    | Four answer options              |
| `CorrectChoice`   | AI-generated                    | Letter of correct answer         |
| `Definition`      | `Definition.definition`         | Full definition text             |
| `Examples`        | Generated + synthesized         | HTML-joined example sentences    |
| `Synonyms`        | `Definition.synonyms[:5]`       | Up to 5 synonyms                 |
| `Frequency`       | `WordListItem.frequency`        | Occurrence count in wordlist     |
| `FrequencyDisplay`| Computed                        | "×3" if frequency > 1, else ""   |

### .apkg Assembly

The [`AnkiCardGenerator.export_to_apkg()`](../backend/src/floridify/anki/generator.py) method uses the `genanki` library to build Anki package files:

1. **Deck creation**: A `genanki.Deck` with a deterministic ID derived from an MD5 hash of the deck name.
2. **Model creation**: One `genanki.Model` per card type, with template HTML, CSS, and field definitions. Model IDs are hardcoded constants (e.g., `1234567890` for BEST_DESCRIBES).
3. **Note creation**: Each `AnkiCard` is converted to a `genanki.Note` with field values ordered to match the model definition.
4. **Package write**: `genanki.Package.write_to_file()` produces the `.apkg` file.
5. **HTML preview**: An HTML file is generated alongside the `.apkg` for browser-based card preview.

### Card Styling

Templates use Apple HIG-influenced CSS: `-apple-system` font stack, 12px border radius, subtle box shadows, and a neutral gray palette (`#f5f5f7` backgrounds, `#1d1d1f` text). Correct answers are highlighted in green (`#30d158`), incorrect in red (`#ff3b30`), and selected choices in blue (`#007aff`).

### AnkiConnect Integration

The [`AnkiConnectInterface`](../backend/src/floridify/anki/ankiconnect.py) communicates with a running Anki desktop application via the AnkiConnect add-on's HTTP API (default: `localhost:8765`). It supports:

- **Availability check**: `version` action to detect whether Anki is running
- **Deck management**: `deckNames`, `createDeck`
- **Note management**: `addNote` with duplicate detection and `updateNoteFields` for existing notes
- **Model management**: `modelNames`, `createModel` for custom card templates
- **Package import**: `importPackage` for direct `.apkg` import
- **Sync trigger**: `sync` to push changes to AnkiWeb

The [`AnkiDirectIntegration`](../backend/src/floridify/anki/ankiconnect.py) wrapper provides a high-level `export_cards_directly()` method that attempts direct note creation first, falling back to `.apkg` file generation if AnkiConnect is unavailable. Partial success is handled gracefully—if some cards succeed and others fail, the successful count is returned and the operation is considered a partial success.

The API endpoint `GET /wordlists/{id}/export/anki` generates and streams the `.apkg` file directly.

### Export Pipeline

```
WordList → Fetch WordListItemDocs → Fetch Word texts + Definitions
  → AnkiCardGenerator.generate_cards() per word
    → AI generates choices + cloze sentence
    → AI augments examples if < 3
    → HTML-escape all fields
  → export_to_apkg() → genanki → .apkg file
```

## 14. Key Files

### Wordlist Core

| File | Purpose |
|------|---------|
| [`wordlist/constants.py`](../backend/src/floridify/wordlist/constants.py) | All enums (MasteryLevel, CardState, Temperature) and numeric constants |
| [`wordlist/review.py`](../backend/src/floridify/wordlist/review.py) | ReviewData model with SM-2 + card state machine logic |
| [`wordlist/models.py`](../backend/src/floridify/wordlist/models.py) | WordListItem, WordListItemDoc, WordList document models |
| [`wordlist/stats.py`](../backend/src/floridify/wordlist/stats.py) | LearningStats model with streak/session tracking |
| [`wordlist/parser.py`](../backend/src/floridify/wordlist/parser.py) | Multi-format file parsing (txt, csv, md, json) |
| [`wordlist/utils.py`](../backend/src/floridify/wordlist/utils.py) | SHA-256 hash generation, name generation |
| [`wordlist/reconcile.py`](../backend/src/floridify/wordlist/reconcile.py) | Pre-commit spell-check and candidate matching |

### API Layer

| File | Purpose |
|------|---------|
| [`api/routers/wordlist/main.py`](../backend/src/floridify/api/routers/wordlist/main.py) | CRUD endpoints, upload, clone, export |
| [`api/routers/wordlist/words.py`](../backend/src/floridify/api/routers/wordlist/words.py) | Word add/remove/update/visit endpoints |
| [`api/routers/wordlist/reviews.py`](../backend/src/floridify/api/routers/wordlist/reviews.py) | Review, session, leech management endpoints |
| [`api/routers/wordlist/search.py`](../backend/src/floridify/api/routers/wordlist/search.py) | Per-wordlist and cross-wordlist search |
| [`api/routers/wordlist/utils.py`](../backend/src/floridify/api/routers/wordlist/utils.py) | Search enrichment, post-filtering, corpus resolution |
| [`api/repositories/wordlist_repository.py`](../backend/src/floridify/api/repositories/wordlist_repository.py) | Repository pattern: CRUD, batch ops, corpus management |
| [`api/services/wordlist_stats.py`](../backend/src/floridify/api/services/wordlist_stats.py) | MongoDB aggregation pipelines for stats |

### Anki

| File | Purpose |
|------|---------|
| [`anki/constants.py`](../backend/src/floridify/anki/constants.py) | CardType enum (BEST_DESCRIBES, FILL_IN_BLANK, etc.) |
| [`anki/generator.py`](../backend/src/floridify/anki/generator.py) | AnkiCardGenerator: AI content + genanki .apkg assembly |
| [`anki/templates.py`](../backend/src/floridify/anki/templates.py) | Card HTML/CSS templates with Apple HIG styling |
| [`anki/ankiconnect.py`](../backend/src/floridify/anki/ankiconnect.py) | AnkiConnect HTTP client + direct integration wrapper |
