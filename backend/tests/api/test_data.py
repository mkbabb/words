"""Test data for API testing including word banks and fuzzy test cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FuzzyTestCase:
    """Test case for fuzzy search validation."""
    
    input: str
    expected_matches: list[str]
    min_expected_score: float = 0.7


# Bank of 30 test words including simple words, phrases, and complex terms
TEST_WORDS = [
    # French phrases
    "en coulisses",
    "bon vivant", 
    "je ne sais quoi",
    "coup de grâce",
    "déjà vu",
    "faux pas",
    "vis-à-vis",
    
    # Latin phrases
    "carpe diem",
    "et cetera",
    "ad hoc",
    
    # Complex/rare words
    "serendipity",
    "ephemeral",
    "ubiquitous",
    "perspicacious",
    "pulchritudinous",
    "sesquipedalian",
    
    # Common words for baseline
    "happy",
    "beautiful",
    "intelligence",
    "computer",
    "philosophy",
    
    # Multi-word expressions
    "once in a blue moon",
    "break the ice",
    "piece of cake",
    
    # Technical terms
    "algorithm",
    "paradigm",
    "synchronous",
    "metamorphosis",
    
    # Commonly misspelled
    "accommodate",
    "definitely",
]

# Fuzzy search test cases
FUZZY_TEST_CASES = [
    # Typos and misspellings
    FuzzyTestCase(
        input="bob vivnt",
        expected_matches=["bon vivant"],
        min_expected_score=0.8
    ),
    FuzzyTestCase(
        input="serendip",
        expected_matches=["serendipity", "serendipitous"],
        min_expected_score=0.85
    ),
    FuzzyTestCase(
        input="algorythm",
        expected_matches=["algorithm"],
        min_expected_score=0.9
    ),
    FuzzyTestCase(
        input="definately",
        expected_matches=["definitely"],
        min_expected_score=0.85
    ),
    FuzzyTestCase(
        input="accomodate",
        expected_matches=["accommodate"],
        min_expected_score=0.9
    ),
    
    # Partial matches
    FuzzyTestCase(
        input="intell",
        expected_matches=["intelligence", "intelligent", "intellectual"],
        min_expected_score=0.7
    ),
    FuzzyTestCase(
        input="meta",
        expected_matches=["metamorphosis", "metaphor", "metadata"],
        min_expected_score=0.7
    ),
    
    # Phonetic similarities
    FuzzyTestCase(
        input="filosofy",
        expected_matches=["philosophy"],
        min_expected_score=0.8
    ),
    FuzzyTestCase(
        input="sincronus",
        expected_matches=["synchronous"],
        min_expected_score=0.75
    ),
    
    # Keyboard proximity errors
    FuzzyTestCase(
        input="haopy",
        expected_matches=["happy"],
        min_expected_score=0.8
    ),
    FuzzyTestCase(
        input="conputer",
        expected_matches=["computer"],
        min_expected_score=0.85
    ),
    
    # Missing letters
    FuzzyTestCase(
        input="beautful",
        expected_matches=["beautiful"],
        min_expected_score=0.9
    ),
    FuzzyTestCase(
        input="paradgm",
        expected_matches=["paradigm"],
        min_expected_score=0.85
    ),
    
    # Extra letters
    FuzzyTestCase(
        input="ephemerall",
        expected_matches=["ephemeral"],
        min_expected_score=0.9
    ),
    FuzzyTestCase(
        input="ubiquitious",
        expected_matches=["ubiquitous"],
        min_expected_score=0.85
    ),
    
    # Swapped letters
    FuzzyTestCase(
        input="peice of cake",
        expected_matches=["piece of cake"],
        min_expected_score=0.9
    ),
    FuzzyTestCase(
        input="carep diem",
        expected_matches=["carpe diem"],
        min_expected_score=0.85
    ),
]

# Performance test configurations
PERF_TEST_QUERIES = [
    # Short queries (trigger prefix search)
    "te", "ser", "alg", "met",
    
    # Medium queries (trigger fuzzy search)
    "seren", "intell", "beauti", "comput",
    
    # Long queries (trigger comprehensive search)
    "serendipity", "intelligence", "beautiful", "computer",
    
    # Phrases (trigger semantic search)
    "bon vivant", "en coulisses", "piece of cake",
    
    # Misspellings (test fuzzy matching)
    "serendipitious", "algoritm", "definately", "accomodate",
]

# Expected response time thresholds (milliseconds)
PERFORMANCE_THRESHOLDS = {
    "lookup": {
        "cached": 50,      # < 50ms for cached lookups
        "uncached": 500,   # < 500ms for uncached lookups
    },
    "search": {
        "short": 30,       # < 30ms for short queries
        "medium": 50,      # < 50ms for medium queries
        "long": 100,       # < 100ms for long queries
        "phrase": 150,     # < 150ms for phrase queries
    },
    "suggestions": {
        "default": 20,     # < 20ms for suggestions
    },
    "synonyms": {
        "cached": 100,     # < 100ms for cached synonyms
        "uncached": 300,   # < 300ms for uncached synonyms
    }
}

# Sample responses for mocking (if needed)
SAMPLE_LOOKUP_RESPONSE: dict[str, Any] = {
    "word": "serendipity",
    "pronunciation": {
        "phonetic": "ser-uh n-DIP-i-tee",
        "ipa": "/ˌsɛrənˈdɪpɪti/"
    },
    "definitions": [
        {
            "word_type": "noun",
            "definition": "The faculty of making fortunate discoveries by accident",
            "synonyms": ["chance", "fortune", "luck", "accident", "coincidence"],
            "examples": {
                "generated": [
                    {"sentence": "Finding the perfect apartment was pure serendipity."}
                ]
            },
            "meaning_cluster": "fortunate_discovery"
        }
    ],
    "last_updated": "2025-01-07T10:30:00Z"
}