"""Search configuration constants.

Centralizes all tunable thresholds, budgets, and scoring parameters
across the search module. Import from here instead of hardcoding values.
"""

# ─── Score Thresholds ──────────────────────────────────────────────

# Semantic cascade — minimum scores before semantic results are included
SEMANTIC_FALLBACK_MIN_SCORE = 0.75  # When no exact/fuzzy/prefix results exist
SEMANTIC_SINGLE_WORD_MIN_SCORE = 0.78  # Single-word queries
SEMANTIC_PHRASE_MIN_SCORE = 0.72  # Multi-word queries

# Semantic strict mode for small corpora (sparse embedding space inflates scores)
SEMANTIC_SMALL_CORPUS_SIZE = 2000
SEMANTIC_SMALL_CORPUS_WORD_FLOOR = 0.82
SEMANTIC_SMALL_CORPUS_PHRASE_FLOOR = 0.78

# Lexical sanity gate — reject semantic matches that are textually unrelated
LEXICAL_SANITY_THRESHOLD = 0.35
LEXICAL_GATE_SCORE_MARGIN = 0.05

# Fuzzy quality gating — semantic only added when fuzzy quality is low
HIGH_QUALITY_FUZZY_SCORE = 0.7

# RapidFuzz primary scorer thresholds
STRONG_PRIMARY_SCORE = 0.85
STRONG_PRIMARY_COUNT = 3
FUZZY_PERFECT_SCORE = 0.99

# ─── Signal Boost Factors ─────────────────────────────────────────
# Applied AFTER length correction to avoid inflating scores past 1.0

PHONETIC_MATCH_BOOST = 1.08
CLOSE_EDIT_DISTANCE_BOOST = 1.02
MULTI_SIGNAL_BOOST = 1.03  # 3+ strategies found the candidate

# ─── Corpus Size Thresholds ───────────────────────────────────────

CORPUS_TINY = 500
CORPUS_SMALL = 5_000
CORPUS_MEDIUM = 50_000
CORPUS_LARGE = 100_000
CORPUS_XLARGE = 300_000

# ─── Candidate Budgets ────────────────────────────────────────────
# Scale-aware limits on candidates passed to RapidFuzz scoring

FUZZY_BUDGET_SMALL = 300
FUZZY_BUDGET_MEDIUM = 700
FUZZY_BUDGET_LARGE = 1100
FUZZY_BUDGET_XLARGE = 1700
PHONETIC_BUDGET_CAP = 200

# ─── BK-Tree Configuration ───────────────────────────────────────

BKTREE_MAX_CORPUS_SIZE = 500_000  # Skip BK-tree above this (time-budgeted)
BKTREE_TIME_BUDGET_SMALL = 20.0  # ms, corpora < 5K words
BKTREE_TIME_BUDGET_MEDIUM = 15.0  # ms, corpora 5K-50K
BKTREE_TIME_BUDGET_LARGE = 10.0  # ms, corpora > 50K
BKTREE_CASCADE_MIN_CANDIDATES = 10
BKTREE_MAX_RESULTS_CAP = 2000

# ─── Per-Word Phrase Decomposition ──────────────────────────────
#
# For multi-word phrase queries (e.g. "en coulisses"), only the suffix
# array is used per-word. BK-tree per-word cascading costs 40ms+ on
# 278K corpora (unbalanced tree), and trigram posting-list intersection
# hits 1000ms+ for common substrings. The suffix array covers the same
# candidates via O(m log n) binary search in <0.1ms.
#
# Stem trim lengths (0, 1, 2) are a language-agnostic morphological
# recall strategy, not English-specific stemming. By searching for
# progressively shorter prefixes of each query word, we increase the
# probability that the suffix array matches a morphological root:
#
#   Trim 0 (full word): exact substring — "coulisses" in a longer entry
#   Trim 1 (-1 char):   single-char inflection across Indo-European
#                        languages: -s (EN/FR/ES plural), -e (FR feminine,
#                        DE plural/case), -i (IT plural), -o (ES masculine)
#   Trim 2 (-2 chars):  two-char suffixes: -ed/-es/-er/-en (EN), -es/-er
#                        (FR), -as/-os/-ar (ES), -en/-er (DE)
#
# Precision is handled downstream by RapidFuzz, which scores the full
# query against full candidate strings — the trim only affects recall
# in the candidate generation phase.

PERWORD_MIN_WORD_LENGTH = 3  # Skip words shorter than this in phrase decomposition
PERWORD_SUFFIX_MIN_STEM_LENGTH = 4  # Min chars for a suffix array stem search
PERWORD_SUFFIX_TRIM_LENGTHS = (0, 1, 2)  # Char counts to trim from word end

# Adaptive edit distance: max_k = min(MAX, max(MIN, ceil(len * MULTIPLIER)))
EDIT_DISTANCE_LENGTH_MULTIPLIER = 0.35
EDIT_DISTANCE_MIN = 2
EDIT_DISTANCE_MAX = 5

# ─── Phonetic Search ─────────────────────────────────────────────

PHONETIC_FUZZY_COMPOSITE_LIMIT = 10_000  # Max composite codes for fuzzy scan
PHONETIC_CODE_DISTANCE_FRACTION = 4  # max_dist = len(code) // this
PHONETIC_WORD_THRESHOLD_FRACTION = 2  # majority = len(words) // this

# ─── RapidFuzz Scoring ────────────────────────────────────────────

PRIMARY_PHRASE_CUTOFF_MULTIPLIER = 45
PRIMARY_WORD_CUTOFF_MULTIPLIER = 50
SECONDARY_PHRASE_CUTOFF_MULTIPLIER = 35
SECONDARY_WORD_CUTOFF_MULTIPLIER = 45
SECONDARY_RESULT_BOOST = 1.2
RAPIDFUZZ_LIMIT_MULTIPLIER_LARGE = 5
RAPIDFUZZ_LIMIT_MULTIPLIER_SMALL = 3
VOCABULARY_SIZE_LIMIT_THRESHOLD = 200  # Switch between large/small multiplier

# ─── Trigram Index ────────────────────────────────────────────────

TRIGRAM_THRESHOLD_DENOMINATOR = 3  # min overlap = max(2, n_trigrams // this)
TRIGRAM_CAP_FRACTION = 0.8  # Reserve 20% of budget for length-bucket candidates
TRIGRAM_CAP_MINIMUM = 10

# ─── Bloom Filter ─────────────────────────────────────────────────

BLOOM_SMALL_CORPUS = 10_000
BLOOM_MEDIUM_CORPUS = 100_000
BLOOM_ERROR_RATE_SMALL = 0.001  # < 10K words
BLOOM_ERROR_RATE_MEDIUM = 0.01  # 10K-100K
BLOOM_ERROR_RATE_LARGE = 0.05  # > 100K

# ─── Caching ──────────────────────────────────────────────────────

INLINE_CONTENT_THRESHOLD_BYTES = 16 * 1024  # 16 KB — below this, store inline in MongoDB

# ─── Search Pipeline ─────────────────────────────────────────────

CORPUS_CHECK_INTERVAL_SECONDS = 30.0  # Hot-reload polling frequency
