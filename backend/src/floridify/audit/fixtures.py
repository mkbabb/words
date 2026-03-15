"""Deterministic fixtures for audit benchmarks."""

from __future__ import annotations

import hashlib
import types
from typing import Any

import numpy as np

from ..corpus.core import Corpus
from ..models.base import Language
from ..search.constants import DEFAULT_MIN_SCORE
from ..search.core import Search
from ..search.fuzzy import FuzzySearch
from ..search.search_index import SearchIndex
from ..search.semantic.core import SemanticSearch
from ..search.semantic.models import SemanticIndex
from ..search.trie import TrieSearch
from ..search.trie_index import TrieIndex

CORPUS_SIZES: dict[str, int] = {
    "tiny": 96,
    "small": 2_048,
    "medium": 32_768,
    "large": 200_000,
}

_SEED_WORDS = [
    "audittrail",
    "auditalpha",
    "auditalpine",
    "auditzulu",
    "auditsemantic",
    "apple",
    "banana",
    "dictionary",
    "example",
    "history",
    "provider",
    "semantic",
    "versioning",
    "rollback",
    "timeline",
]
_PREFIXES = ["pre", "post", "over", "under", "micro", "macro", "hyper", "ultra", "neo"]
_SUFFIXES = ["ing", "ed", "er", "ly", "able", "ness", "tion", "ment", "istic"]

AUDIT_WIKITEXT_SAMPLE = """
==English==
===Pronunciation===
* {{IPA|en|/ˈɔː.dɪt.treɪl/}}
===Etymology===
From {{m|en|audit}} + {{m|en|trail}}.
===Noun===
# {{lb|en|computing}} A recorded sequence of changes for inspection.
#* {{quote-book|en|year=2024|author=Audit Team|passage=The audit trail revealed every schema change in order.}}
# {{gloss|software}} A revision history used for rollback and debugging.
"""

AUDIT_WIKITEXT_FULL_ENTRY = """
==English==
===Pronunciation===
* {{IPA|en|/pɜːˌspɪˈkeɪʃəs/}}
* {{a|US}} {{IPA|en|/ˌpɝːspɪˈkeɪʃəs/}}
===Etymology===
From {{der|en|la|perspicax}}, from {{m|la|perspicere||to look through}}.
===Adjective===
# Having a ready insight into and understanding of things; shrewd.
#* {{quote-book|en|year=1920|author=F. Scott Fitzgerald|passage=He was perspicacious enough to see through the facade.}}
# {{lb|en|formal}} Mentally acute or discerning.
# Able to understand or judge things clearly.
===Noun===
# {{lb|en|rare}} A person with keen perception.
# {{gloss|archaic}} An act of perspicacity.
===Verb===
# {{lb|en|nonstandard}} To perceive with great clarity.
# To analyze with shrewd judgment.
====Synonyms====
* {{l|en|astute}}
* {{l|en|discerning}}
* {{l|en|perceptive}}
"""

WIKITEXT_CORRECTNESS_CASES: list[tuple[str, str]] = [
    ("{{lb|en|formal}} A test", "(formal) A test"),
    ("{{gloss|meaning}}", "(meaning)"),
    ("'''bold text'''", "bold text"),
    ("''italic text''", "italic text"),
    ("[[simple link]]", "simple link"),
    ("[[target|display text]]", "display text"),
    ("plain text only", "plain text only"),
    ("{{l|en|word}}", "word"),
    ("text with <ref>citation</ref> end", "text with citation end"),
    ("{{q|informal}} greeting", "(informal) greeting"),
]


def _generate_word(index: int) -> str:
    family = f"lex{index % 29}"
    core = f"{family}{index:05d}"
    prefix = _PREFIXES[index % len(_PREFIXES)]
    suffix = _SUFFIXES[index % len(_SUFFIXES)]
    return f"{prefix}{core}{suffix}"


def build_vocabulary(size: int) -> list[str]:
    """Generate a deterministic vocabulary of the requested size."""
    vocab: list[str] = list(dict.fromkeys(_SEED_WORDS))
    index = 0
    while len(vocab) < size:
        candidate = _generate_word(index)
        if candidate not in vocab:
            vocab.append(candidate)
        index += 1
    return vocab[:size]


async def build_corpus_fixture(
    name: str,
    size: int,
    *,
    language: Language = Language.ENGLISH,
) -> Corpus:
    """Create an in-memory corpus fixture with a stable UUID."""
    corpus = await Corpus.create(
        corpus_name=name,
        vocabulary=build_vocabulary(size),
        semantic=False,
        language=language,
    )
    corpus.corpus_uuid = f"audit-{name}-uuid"
    return corpus


async def build_search_fixture(
    name: str,
    size: int,
    *,
    min_score: float = DEFAULT_MIN_SCORE,
) -> Search:
    """Create an in-memory Search instance without touching persistence."""
    corpus = await build_corpus_fixture(name, size)
    trie_index = await TrieIndex.create(corpus)
    search_index = await SearchIndex.create(corpus, min_score=min_score, semantic=False)
    search_index.trie_index_id = trie_index.index_id

    search = Search(index=search_index, corpus=corpus)
    search.trie_search = TrieSearch(index=trie_index)
    search.fuzzy_search = FuzzySearch(min_score=min_score)
    search._initialized = True
    search._semantic_ready = False
    return search


def fake_encode_texts(texts: list[str], *, dimension: int = 32) -> np.ndarray:
    """Create deterministic normalized embeddings without model downloads."""
    rows: list[np.ndarray] = []
    for text in texts:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        repeated = (digest * ((dimension // len(digest)) + 1))[:dimension]
        vector = np.frombuffer(repeated, dtype=np.uint8).astype(np.float32)
        vector = (vector / 127.5) - 1.0
        norm = np.linalg.norm(vector)
        rows.append(vector if norm == 0 else vector / norm)
    return np.vstack(rows).astype("float32")


def install_fake_semantic_encoder(search: SemanticSearch, *, dimension: int = 32) -> None:
    """Patch a SemanticSearch instance to use deterministic fake embeddings."""

    def _encode(self: SemanticSearch, texts: list[str], use_multiprocessing: bool = True) -> np.ndarray:  # noqa: ARG001
        return fake_encode_texts(texts, dimension=dimension)

    class _FakeSentenceModel:
        def encode(self, sentences: list[str], **_: Any) -> np.ndarray:
            return fake_encode_texts(list(sentences), dimension=dimension)

    search.sentence_model = _FakeSentenceModel()  # type: ignore[assignment]
    search.device = "cpu"
    search._encode = types.MethodType(_encode, search)


async def build_semantic_fixture(
    name: str,
    size: int,
    *,
    dimension: int = 32,
) -> tuple[Corpus, SemanticIndex, SemanticSearch]:
    """Create an in-memory SemanticSearch fixture backed by fake embeddings."""
    corpus = await build_corpus_fixture(name, size)
    index = await SemanticIndex.create(corpus, model_name="audit-fake", batch_size=32)
    search = SemanticSearch(index=index, corpus=corpus)
    install_fake_semantic_encoder(search, dimension=dimension)
    return corpus, index, search


def build_multi_version_payloads(num_versions: int = 10) -> list[dict[str, object]]:
    """Generate a chain of dictionary-entry payloads with incremental mutations."""
    payloads: list[dict[str, object]] = []
    for v in range(num_versions):
        payloads.append({
            "word": "audittrail",
            "definitions": [
                {
                    "part_of_speech": "noun",
                    "text": f"Definition text revision {v}.",
                    "examples": [f"Example {i}" for i in range(v % 4 + 1)],
                },
                {
                    "part_of_speech": "verb",
                    "text": f"To audit-trail something ({v}).",
                    "examples": [f"Verb example {v}"],
                },
                *(
                    [{"part_of_speech": "adjective", "text": f"Audit-trailed ({v})."}]
                    if v >= 5
                    else []
                ),
            ],
            "etymology": {"text": f"From audit + trail, revision {v}."},
            "pronunciation": {"ipa": "/ˈɔː.dɪt.treɪl/"},
            "metadata": {"revision": v, "tags": ["audit", "history"]},
        })
    return payloads
