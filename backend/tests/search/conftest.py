"""Search-specific test configuration and fixtures."""

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase

from floridify.corpus.core import Corpus
from floridify.search.core import Search
from floridify.search.fuzzy import FuzzySearch
from floridify.search.models import SearchIndex, SearchResult, TrieIndex
from floridify.search.semantic.core import SemanticSearch
from floridify.search.semantic.models import SemanticIndex
from floridify.search.trie import TrieSearch

SAMPLE_WORDS = [
    "apple",
    "application",
    "apply",
    "appreciate",
    "approach",
    "banana",
    "band",
    "bank",
    "banquet",
    "bar",
    "bark",
    "barrel",
    "base",
    "basic",
    "basket",
    "cat",
    "catalog",
    "catch",
    "category",
    "cathedral",
    "cattle",
    "cause",
    "caution",
    "cave",
    "ceiling",
    "celebrate",
    "cell",
    "center",
    "central",
    "century",
    "ceremony",
    "certain",
    "chair",
    "challenge",
    "chamber",
    "champion",
    "chance",
    "change",
    "channel",
    "chapter",
    "character",
    "charge",
    "charity",
    "charm",
    "chart",
    "chase",
    "check",
    "cheese",
    "chemical",
    "cherry",
    "chest",
    "chicken",
    "chief",
    "child",
    "choice",
    "choose",
    "church",
    "circle",
    "citizen",
    "city",
    "claim",
    "class",
    "classic",
    "clean",
    "clear",
    "clever",
    "climate",
    "climb",
    "clock",
    "close",
    "cloud",
    "club",
    "coach",
    "coast",
    "coat",
    "code",
    "coffee",
    "coin",
    "cold",
    "collapse",
    "collect",
    "college",
    "colony",
    "color",
    "column",
    "combine",
    "come",
    "comfort",
    "command",
    "comment",
    "commerce",
    "commission",
    "committee",
    "common",
    "communicate",
    "community",
    "company",
    "compare",
    "compete",
    "complain",
    "complete",
    "complex",
    "computer",
    "concentrate",
    "concept",
    "concern",
    "concert",
    "conclude",
    "condition",
    "conduct",
    "conference",
    "confidence",
    "confirm",
    "conflict",
    "confuse",
    "connect",
    "connection",
    "conscious",
    "consequence",
    "consider",
    "consist",
    "constant",
    "constitute",
    "construct",
    "consult",
    "consume",
    "contact",
    "contain",
    "contemporary",
    "content",
    "contest",
    "context",
    "continue",
    "contract",
    "contrast",
    "contribute",
    "control",
    "convention",
    "conversation",
    "convert",
    "convince",
    "cook",
    "cool",
    "cooperate",
    "copy",
    "core",
    "corn",
    "corner",
    "corporate",
    "correct",
    "correspond",
    "cost",
    "cotton",
    "council",
    "count",
    "country",
    "couple",
    "courage",
    "course",
    "court",
    "cousin",
    "cover",
    "craft",
    "crash",
    "crazy",
    "cream",
    "create",
    "creature",
    "credit",
    "crew",
    "crime",
    "criminal",
    "crisis",
    "criterion",
    "critic",
    "critical",
    "crop",
    "cross",
    "crowd",
    "crown",
    "crucial",
    "cruel",
    "cruise",
    "cry",
    "crystal",
    "culture",
    "cup",
    "curious",
    "current",
    "curriculum",
    "curve",
    "custom",
    "customer",
    "cut",
    "cycle",
    "dad",
    "daily",
    "damage",
    "dance",
    "danger",
    "dangerous",
    "dare",
    "dark",
    "data",
    "database",
    "date",
    "daughter",
    "day",
    "dead",
    "deal",
    "dealer",
    "dear",
    "death",
    "debate",
    "debt",
    "decade",
    "december",
    "decide",
    "decision",
    "deck",
    "declare",
    "decline",
    "decorate",
    "decrease",
    "deep",
    "defeat",
    "defend",
    "defense",
    "define",
    "definitely",
    "definition",
    "degree",
    "delay",
    "deliver",
    "delivery",
    "demand",
    "democracy",
    "democratic",
    "demonstrate",
    "demonstration",
    "deny",
    "department",
    "depend",
    "dependent",
    "deposit",
    "depression",
    "depth",
    "derive",
    "describe",
    "description",
    "desert",
    "deserve",
    "design",
    "designer",
    "desire",
    "desk",
    "desperate",
    "despite",
    "destroy",
    "destruction",
    "detail",
    "detect",
    "determine",
    "develop",
    "developer",
    "development",
    "device",
    "devote",
    "dialogue",
    "diamond",
    "dictionary",
    "die",
    "diet",
    "differ",
    "difference",
    "different",
    "difficult",
    "difficulty",
    "dig",
    "digital",
    "dinner",
    "direct",
    "direction",
    "directly",
    "director",
    "dirt",
    "disagree",
    "disappear",
    "disaster",
    "discipline",
    "discount",
    "discover",
    "discovery",
    "discuss",
    "discussion",
    "disease",
    "dismiss",
    "disorder",
    "display",
    "dispute",
    "distance",
    "distinct",
    "distinction",
    "distinguish",
    "distribute",
    "distribution",
    "district",
    "disturb",
    "divide",
    "division",
    "divorce",
    "doctor",
    "document",
    "dog",
    "dollar",
    "domain",
    "domestic",
    "dominant",
    "dominate",
    "door",
    "double",
    "doubt",
    "down",
    "dozen",
    "draft",
    "drag",
    "drama",
    "dramatic",
    "draw",
    "drawer",
    "drawing",
    "dream",
    "dress",
    "drink",
    "drive",
    "driver",
    "drop",
    "drug",
    "dry",
    "due",
    "during",
    "dust",
    "duty",
    "dynamic",
    "each",
    "eager",
    "ear",
    "early",
    "earn",
    "earth",
    "ease",
    "easily",
    "east",
    "eastern",
    "easy",
    "eat",
    "economic",
    "economics",
    "economy",
    "edge",
    "edition",
    "editor",
    "educate",
    "education",
    "educational",
    "effect",
    "effective",
    "effectively",
    "efficiency",
    "efficient",
    "effort",
    "egg",
    "eight",
    "either",
    "elaborate",
    "elderly",
    "elect",
    "election",
    "electric",
    "electrical",
    "electricity",
    "electronic",
    "element",
    "elementary",
    "elephant",
    "elevator",
    "eleven",
    "eliminate",
    "elite",
    "else",
    "elsewhere",
    "email",
    "embarrass",
    "embrace",
    "emerge",
    "emergency",
    "emotion",
    "emotional",
    "emphasis",
    "emphasize",
    "empire",
    "employ",
    "employee",
    "employer",
    "employment",
    "empty",
    "enable",
    "encounter",
    "encourage",
    "end",
    "enemy",
    "energy",
    "enforce",
    "engage",
    "engine",
    "engineer",
    "engineering",
    "enhance",
    "enjoy",
    "enormous",
    "enough",
    "ensure",
    "enter",
    "enterprise",
    "entertain",
    "entertainment",
    "enthusiasm",
    "entire",
    "entirely",
    "entrance",
    "entrepreneur",
    "entry",
    "environment",
    "environmental",
    "episode",
    "equal",
    "equally",
    "equipment",
    "era",
    "error",
    "escape",
    "especially",
    "essay",
    "essential",
    "establish",
    "establishment",
    "estate",
    "estimate",
]

MISSPELLED_WORDS = {
    "aple": "apple",
    "aplication": "application",
    "apreciate": "appreciate",
    "aproach": "approach",
    "banna": "banana",
    "catlog": "catalog",
    "catagory": "category",
    "celing": "ceiling",
    "celebrat": "celebrate",
    "certin": "certain",
    "chalenj": "challenge",
    "chanje": "change",
    "charector": "character",
    "cheeze": "cheese",
    "chemicle": "chemical",
    "chery": "cherry",
    "cheif": "chief",
    "choise": "choice",
    "choos": "choose",
    "citicen": "citizen",
    "clasic": "classic",
    "clime": "climb",
    "colect": "collect",
    "colege": "college",
    "colum": "column",
    "coment": "comment",
    "comision": "commission",
    "commitee": "committee",
    "comunicate": "communicate",
    "comunity": "community",
    "compair": "compare",
    "compeat": "compete",
    "compleet": "complete",
    "consern": "concern",
    "conclood": "conclude",
    "conferance": "conference",
    "confidense": "confidence",
    "conekt": "connect",
    "consekuense": "consequence",
    "considder": "consider",
    "constent": "constant",
    "constuct": "construct",
    "contane": "contain",
    "contemporery": "contemporary",
    "continu": "continue",
    "contribut": "contribute",
    "conversasion": "conversation",
    "convins": "convince",
    "cooperat": "cooperate",
    "corespond": "correspond",
    "counsil": "council",
    "contry": "country",
    "cupple": "couple",
    "corage": "courage",
    "corse": "course",
    "cort": "court",
    "cozin": "cousin",
}


@pytest_asyncio.fixture
async def sample_corpus() -> Corpus:
    """Create a sample corpus for testing."""
    # Build the corpus with all required fields for search
    vocabulary = SAMPLE_WORDS
    corpus = Corpus(
        corpus_name="test-corpus",
        language="en",
        vocabulary=vocabulary,
        original_vocabulary=vocabulary,
        vocabulary_to_index={word: i for i, word in enumerate(vocabulary)},
        unique_word_count=len(vocabulary),
        total_word_count=len(vocabulary),
    )

    # Build signature and length buckets for fuzzy search
    from floridify.text.normalize import get_word_signature

    for idx, word in enumerate(vocabulary):
        # Length buckets
        length = len(word)
        if length not in corpus.length_buckets:
            corpus.length_buckets[length] = []
        corpus.length_buckets[length].append(idx)

        # Signature buckets
        sig = get_word_signature(word)
        if sig not in corpus.signature_buckets:
            corpus.signature_buckets[sig] = []
        corpus.signature_buckets[sig].append(idx)

    return corpus


@pytest_asyncio.fixture
async def trie_search(sample_corpus: Corpus) -> TrieSearch:
    """Create TrieSearch instance with sample corpus."""
    # Create index directly without MongoDB persistence
    from beanie import PydanticObjectId

    index = TrieIndex(
        corpus_id=PydanticObjectId(),
        corpus_name=sample_corpus.corpus_name,
        vocabulary_hash="test_hash",
        trie_data=sorted(sample_corpus.vocabulary),
        word_frequencies={word: 10 for word in sample_corpus.vocabulary},
        original_vocabulary=sample_corpus.original_vocabulary,
        normalized_to_original={word: word for word in sample_corpus.vocabulary},
        word_count=len(sample_corpus.vocabulary),
        max_frequency=10,
    )

    return TrieSearch(index=index)


@pytest_asyncio.fixture
async def fuzzy_search(sample_corpus: Corpus) -> FuzzySearch:
    """Create FuzzySearch instance with sample corpus."""
    return FuzzySearch(min_score=0.6)


@pytest_asyncio.fixture
async def semantic_search(sample_corpus: Corpus) -> SemanticSearch:
    """Create SemanticSearch instance with sample corpus."""
    # Use a lightweight model for testing
    return await SemanticSearch.from_corpus(
        corpus=sample_corpus,
        model_name="all-MiniLM-L6-v2",
        device="cpu",
        batch_size=32,
    )


@pytest_asyncio.fixture
async def search_engine(sample_corpus: Corpus) -> Search:
    """Create unified Search instance with all methods."""
    # Create search index first
    from floridify.search.models import SearchIndex

    index = await SearchIndex.create(sample_corpus)

    # Create search engine
    engine = Search(index=index, corpus=sample_corpus)
    await engine.initialize()

    return engine


@pytest.fixture
def search_queries() -> dict[str, list[str]]:
    """Provide test queries for different search scenarios."""
    return {
        "exact": ["apple", "application", "category", "computer", "database"],
        "prefix": ["app", "cat", "com", "dat", "dev"],
        "misspelled": list(MISSPELLED_WORDS.keys()),
        "semantic": [
            "fruit",  # Should find apple, banana, cherry
            "technology",  # Should find computer, digital, electronic
            "building",  # Should find construct, establish
            "speak",  # Should find communicate, conversation, dialogue
            "education",  # Should find educate, educational, college
        ],
        "multi_word": [
            "apple pie",
            "computer science",
            "data analysis",
            "social media",
            "machine learning",
        ],
        "unicode": [
            "café",
            "naïve",
            "résumé",
            "Zürich",
            "北京",  # Beijing
        ],
        "special_chars": [
            "user@example.com",
            "hello-world",
            "file.txt",
            "$100",
            "C++",
        ],
        "edge_cases": [
            "",  # Empty query
            " ",  # Whitespace only
            "a" * 100,  # Very long query
            "xyz123qwe",  # Non-existent word
            "🚀",  # Emoji
        ],
    }


@pytest.fixture
def performance_thresholds() -> dict[str, float]:
    """Define performance thresholds for search operations."""
    return {
        "exact_search": 0.001,  # 1ms
        "fuzzy_search": 0.01,  # 10ms
        "semantic_search": 0.1,  # 100ms
        "cascade_search": 0.15,  # 150ms
        "index_build": 5.0,  # 5s
        "batch_search": 1.0,  # 1s for batch
    }


async def assert_search_result_valid(result: SearchResult) -> None:
    """Assert that a search result has valid structure."""
    assert result.word is not None
    assert 0.0 <= result.score <= 1.0
    assert result.method in ["exact", "fuzzy", "semantic", "prefix"]
    assert result.distance >= 0.0
    if result.metadata:
        assert "frequency" in result.metadata or "source" in result.metadata


async def create_test_indices(
    corpus: Corpus,
    test_db: AsyncIOMotorDatabase,
) -> tuple[TrieIndex, SemanticIndex, SearchIndex]:
    """Create and save test indices for a corpus."""
    # Create trie index
    trie_search = TrieSearch.from_corpus(corpus)
    trie_index = await TrieIndex.get_or_create(corpus, trie_search.to_trie_index())

    # Create semantic index
    semantic_search = await SemanticSearch.from_corpus(
        corpus=corpus,
        model_name="all-MiniLM-L6-v2",
    )
    semantic_index = await SemanticIndex.get_or_create(
        corpus, "all-MiniLM-L6-v2", semantic_search.to_semantic_index()
    )

    # Create search index
    search_index = await SearchIndex.from_corpus(corpus)

    return trie_index, semantic_index, search_index


@pytest.fixture
def mock_embeddings():
    """Mock embeddings for testing without loading models."""
    import numpy as np

    def generate_mock_embedding(text: str) -> np.ndarray:
        # Generate deterministic embedding based on text hash
        seed = hash(text) % (2**32)
        rng = np.random.RandomState(seed)
        return rng.randn(384).astype(np.float32)  # Standard embedding size

    return generate_mock_embedding
