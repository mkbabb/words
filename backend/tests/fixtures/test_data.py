"""
Comprehensive test data fixtures for consistent testing across the entire test suite.
Provides realistic, edge case, and performance test data.
"""

from typing import Any

import pytest


@pytest.fixture
def comprehensive_test_words() -> list[str]:
    """Comprehensive list of test words covering various categories."""
    return [
        # Common words
        "test", "example", "sample", "word", "definition",
        "happy", "sad", "run", "walk", "beautiful",
        
        # Complex/academic words
        "ephemeral", "serendipity", "ubiquitous", "facetious", "perspicacious",
        "quintessential", "juxtaposition", "paradigm", "antithesis", "synthesis",
        
        # Technical words
        "algorithm", "database", "optimization", "implementation", "architecture",
        "polymorphism", "encapsulation", "abstraction", "inheritance", "composition",
        
        # Words with special characters
        "café", "naïve", "résumé", "piñata", "jalapeño",
        "façade", "fiancé", "décor", "cliché", "protégé",
        
        # Compound/hyphenated words
        "self-control", "mother-in-law", "well-being", "state-of-the-art", "follow-up",
        "break-in", "check-up", "make-up", "start-up", "grown-up",
        
        # Phrasal verbs
        "break down", "look up", "put off", "turn on", "give up",
        "figure out", "come across", "run into", "go through", "bring up"
    ]


@pytest.fixture
def fuzzy_matching_test_cases() -> list[dict[str, Any]]:
    """Test cases for fuzzy matching validation."""
    return [
        {"query": "hapiness", "expected": ["happiness"], "min_score": 0.8},
        {"query": "recieve", "expected": ["receive"], "min_score": 0.8},
        {"query": "definately", "expected": ["definitely"], "min_score": 0.8},
        {"query": "seperate", "expected": ["separate"], "min_score": 0.8},
        {"query": "occured", "expected": ["occurred"], "min_score": 0.8},
        {"query": "begining", "expected": ["beginning"], "min_score": 0.8},
        {"query": "enviroment", "expected": ["environment"], "min_score": 0.7},
        {"query": "accomodate", "expected": ["accommodate"], "min_score": 0.7},
        {"query": "embarass", "expected": ["embarrass"], "min_score": 0.7},
        {"query": "necessery", "expected": ["necessary"], "min_score": 0.7}
    ]


@pytest.fixture
def performance_test_words() -> list[str]:
    """Large set of words for performance testing."""
    base_words = [
        "analysis", "application", "approach", "area", "assessment", "assignment",
        "assumption", "attention", "attitude", "attribute", "authority", "availability",
        "benefit", "category", "challenge", "characteristic", "choice", "circumstance",
        "classification", "combination", "comment", "commitment", "communication", "community",
        "comparison", "competition", "complexity", "component", "composition", "computer",
        "concentration", "concept", "conclusion", "condition", "conference", "connection",
        "consideration", "construction", "consumption", "contact", "content", "context",
        "contribution", "control", "convention", "conversation", "cooperation", "coordination"
    ]
    
    # Generate variations for performance testing
    performance_words = []
    for word in base_words:
        performance_words.extend([
            word,
            f"{word}s",  # Plural
            f"{word}ed" if word.endswith('e') else f"{word}ed",  # Past tense
            f"{word}ing",  # Present participle
            f"pre{word}",  # Prefix variation
            f"{word}tion" if not word.endswith('tion') else word,  # Suffix variation
        ])
    
    return performance_words


@pytest.fixture
def unicode_edge_cases() -> list[str]:
    """Unicode edge cases for testing."""
    return [
        # Accented characters
        "café", "naïve", "résumé", "piñata", "jalapeño",
        
        # Different scripts
        "日本語",  # Japanese
        "العربية",  # Arabic
        "русский",  # Russian
        "ελληνικά",  # Greek
        "हिन्दी",   # Hindi
        
        # Emojis
        "🙂", "😊", "🎉", "🔥", "💡",
        
        # Mathematical symbols
        "∞", "∑", "∫", "∆", "π",
        
        # Special Unicode spaces and characters
        "\u00a0word",  # Non-breaking space
        "word\u2009test",  # Thin space
        "test\u200bword",  # Zero-width space
        
        # Combining characters
        "e\u0301",  # e with acute accent (é)
        "a\u0308",  # a with diaeresis (ä)
        
        # Right-to-left text
        "تجربة",  # Arabic test
        "עברית",  # Hebrew
    ]


@pytest.fixture
def malicious_input_test_cases() -> list[str]:
    """Potentially malicious inputs for security testing."""
    return [
        # SQL injection attempts (even though we use MongoDB)
        "'; DROP TABLE words; --",
        "1' OR '1'='1",
        "admin'; DROP DATABASE floridify; --",
        
        # XSS attempts
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        
        # Path traversal
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "/etc/shadow",
        
        # NoSQL injection
        "'; db.dropDatabase(); //",
        "$where: function() { return true; }",
        "{ $ne: null }",
        
        # Command injection
        "; ls -la; echo 'pwned'",
        "| cat /etc/passwd",
        "`rm -rf /`",
        
        # LDAP injection
        "*)(uid=*))(|(uid=*",
        "admin)(&(password=*))",
        
        # XML/XXE
        "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>",
        
        # Template injection
        "{{7*7}}",
        "${7*7}",
        "#{7*7}",
    ]


@pytest.fixture
def ai_mock_responses() -> dict[str, Any]:
    """Mock responses for AI endpoints."""
    return {
        "pronunciation": {
            "phonetic": "/ˈtestɪŋ/",
            "ipa": "ˈtɛstɪŋ",
            "syllables": ["test", "ing"],
            "stress_pattern": "10"
        },
        "synonyms": {
            "synonyms": [
                {"word": "examination", "relevance": 0.95},
                {"word": "trial", "relevance": 0.90},
                {"word": "assessment", "relevance": 0.85},
                {"word": "evaluation", "relevance": 0.80},
                {"word": "check", "relevance": 0.75}
            ]
        },
        "antonyms": {
            "antonyms": [
                {"word": "ignore", "confidence": 0.80},
                {"word": "skip", "confidence": 0.75},
                {"word": "avoid", "confidence": 0.70}
            ]
        },
        "examples": {
            "examples": [
                {
                    "text": "We need to test this new feature thoroughly.",
                    "context": "software development"
                },
                {
                    "text": "The teacher will test the students next week.",
                    "context": "education"
                },
                {
                    "text": "This is a test of the emergency broadcast system.",
                    "context": "emergency services"
                }
            ]
        },
        "facts": {
            "facts": [
                {
                    "content": "The word 'test' comes from the Latin 'testum', meaning earthen pot.",
                    "category": "etymology"
                },
                {
                    "content": "Testing is a fundamental practice in software development.",
                    "category": "usage"
                },
                {
                    "content": "The verb 'test' first appeared in English in the 14th century.",
                    "category": "historical"
                }
            ]
        },
        "cefr": {
            "cefr_level": "B1",
            "reasoning": "Common word used in everyday and academic contexts."
        },
        "frequency": {
            "frequency_band": 2,
            "reasoning": "Very common word, used frequently in various contexts."
        },
        "register": {
            "register": "neutral",
            "confidence": 0.90
        },
        "suggestions": {
            "words": [
                {"word": "examine", "theme": "investigation"},
                {"word": "evaluate", "theme": "assessment"},
                {"word": "verify", "theme": "confirmation"},
                {"word": "validate", "theme": "approval"}
            ]
        }
    }


@pytest.fixture
def wordlist_test_data() -> dict[str, Any]:
    """Test data for wordlist operations."""
    return {
        "basic_wordlist": {
            "name": "Basic Test List",
            "description": "A simple wordlist for testing",
            "words": ["apple", "banana", "cherry", "date", "elderberry"],
            "is_public": False,
            "tags": ["fruit", "test"]
        },
        "large_wordlist": {
            "name": "Large Test List",
            "description": "A large wordlist for performance testing",
            "words": [f"word{i}" for i in range(1000)],
            "is_public": True,
            "tags": ["performance", "large"]
        },
        "academic_wordlist": {
            "name": "Academic Vocabulary",
            "description": "Advanced academic words",
            "words": [
                "paradigm", "synthesis", "hypothesis", "methodology", "empirical",
                "theoretical", "conceptual", "analytical", "systematic", "comprehensive"
            ],
            "is_public": True,
            "tags": ["academic", "advanced"]
        },
        "unicode_wordlist": {
            "name": "International Words",
            "description": "Words from different languages",
            "words": ["café", "naïve", "日本語", "العربية", "русский"],
            "is_public": False,
            "tags": ["international", "unicode"]
        }
    }


@pytest.fixture
def corpus_test_data() -> dict[str, Any]:
    """Test data for corpus operations."""
    return {
        "small_corpus": {
            "words": ["test", "example", "sample"],
            "name": "Small Test Corpus"
        },
        "medium_corpus": {
            "words": [f"corpus_word_{i}" for i in range(50)],
            "phrases": ["test phrase", "example expression"],
            "name": "Medium Test Corpus"
        },
        "large_corpus": {
            "words": [f"large_corpus_word_{i}" for i in range(500)],
            "name": "Large Performance Corpus"
        },
        "specialized_corpus": {
            "words": ["algorithm", "database", "optimization", "implementation"],
            "phrases": ["data structure", "machine learning", "artificial intelligence"],
            "name": "Technical Corpus"
        }
    }


@pytest.fixture
def http_error_test_cases() -> list[dict[str, Any]]:
    """HTTP error scenarios for testing."""
    return [
        {"status": 400, "scenario": "bad_request", "description": "Invalid request format"},
        {"status": 401, "scenario": "unauthorized", "description": "Missing authentication"},
        {"status": 403, "scenario": "forbidden", "description": "Insufficient permissions"},
        {"status": 404, "scenario": "not_found", "description": "Resource does not exist"},
        {"status": 409, "scenario": "conflict", "description": "Resource conflict"},
        {"status": 413, "scenario": "payload_too_large", "description": "Request entity too large"},
        {"status": 422, "scenario": "validation_error", "description": "Invalid input data"},
        {"status": 429, "scenario": "rate_limited", "description": "Too many requests"},
        {"status": 500, "scenario": "internal_error", "description": "Server error"},
        {"status": 503, "scenario": "service_unavailable", "description": "Service temporarily unavailable"}
    ]