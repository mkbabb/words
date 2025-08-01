"""Core text processing with spacy fallbacks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Optional dependency handling
try:
    import spacy
    from spacy.language import Language as SpacyLanguage

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    SpacyLanguage = type("Language", (), {})  # type: ignore[assignment,misc]

try:
    import nltk  # type: ignore[import-untyped]

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@dataclass(frozen=True)
class ProcessingResult:
    """Result of text processing with metadata."""

    text: str
    tokens: list[str] = field(default_factory=list)
    method_used: str = "regex"
    processing_time_ms: float = 0.0
    features_available: list[str] = field(default_factory=list)


@runtime_checkable
class TextProcessorProtocol(Protocol):
    """Protocol for text processing implementations."""

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        ...

    def lemmatize(self, word: str) -> str:
        """Lemmatize a single word."""
        ...

    def is_available(self) -> bool:
        """Check if processor is available."""
        ...


class SpacyProcessor:
    """Spacy-based text processor."""

    def __init__(self, model: str = "en_core_web_sm"):
        if not SPACY_AVAILABLE:
            raise RuntimeError("Spacy not available")

        self.model_name = model
        self.nlp: SpacyLanguage | None = None
        self._load_model()

    def _load_model(self) -> None:
        """Load spacy model with optimizations."""
        try:
            # Disable unnecessary components for performance
            self.nlp = spacy.load(self.model_name, disable=["parser", "ner", "textcat"])
            logger.info(f"Loaded spacy model: {self.model_name}")
        except OSError:
            logger.warning(f"Spacy model {self.model_name} not found, using blank model")
            try:
                self.nlp = spacy.blank("en")
            except Exception as e:
                logger.error(f"Failed to create blank spacy model: {e}")
                raise

    def tokenize(self, text: str) -> list[str]:
        """Tokenize using spacy."""
        if not self.nlp:
            return []

        doc = self.nlp(text)
        return [token.text for token in doc if not token.is_space]

    def lemmatize(self, word: str) -> str:
        """Lemmatize using spacy."""
        if not self.nlp:
            return word

        doc = self.nlp(word)
        if not doc or doc[0].lemma_ == "-PRON-":
            return word

        return doc[0].lemma_

    def is_available(self) -> bool:
        """Check if spacy is available."""
        return self.nlp is not None


class NLTKProcessor:
    """NLTK-based text processor."""

    def __init__(self) -> None:
        if not NLTK_AVAILABLE:
            raise RuntimeError("NLTK not available")

        self._setup_nltk()

    def _setup_nltk(self) -> None:
        """Setup NLTK dependencies."""
        try:
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
            nltk.download("wordnet", quiet=True)
            nltk.download("averaged_perceptron_tagger", quiet=True)

            from nltk.stem import WordNetLemmatizer  # type: ignore[import-untyped]
            from nltk.tokenize import word_tokenize  # type: ignore[import-untyped]

            self.word_tokenize = word_tokenize
            self.lemmatizer = WordNetLemmatizer()
            self._available = True

            logger.info("NLTK processor initialized")
        except Exception as e:
            logger.error(f"Failed to setup NLTK: {e}")
            self._available = False

    def tokenize(self, text: str) -> list[str]:
        """Tokenize using NLTK."""
        if not self._available:
            return []

        return list(self.word_tokenize(text.lower()))

    def lemmatize(self, word: str) -> str:
        """Lemmatize using NLTK."""
        if not self._available:
            return word

        return str(self.lemmatizer.lemmatize(word.lower()))

    def is_available(self) -> bool:
        """Check if NLTK is available."""
        return self._available


class RegexProcessor:
    """Regex-based text processor - always available."""

    # Pre-compiled patterns for performance
    WORD_PATTERN = re.compile(r"\b\w+\b")
    SUFFIX_RULES = {
        "ing": "",
        "ed": "",
        "er": "",
        "est": "",
        "ly": "",
        "s": "",
    }

    def tokenize(self, text: str) -> list[str]:
        """Tokenize using regex."""
        return self.WORD_PATTERN.findall(text.lower())

    def lemmatize(self, word: str) -> str:
        """Basic lemmatization using suffix rules."""
        word = word.lower()

        for suffix, replacement in self.SUFFIX_RULES.items():
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[: -len(suffix)] + replacement

        return word

    def is_available(self) -> bool:
        """Regex processor is always available."""
        return True


class TextProcessor:
    """Main text processor with automatic fallbacks."""

    def __init__(self, prefer_method: str = "auto"):
        self.processors: list[TextProcessorProtocol] = []
        self._setup_processors(prefer_method)

    def _setup_processors(self, prefer_method: str) -> None:
        """Setup processors in order of preference."""
        if prefer_method == "spacy" and SPACY_AVAILABLE:
            try:
                self.processors.append(SpacyProcessor())
            except Exception as e:
                logger.warning(f"Failed to setup spacy: {e}")

        if prefer_method in ("nltk", "auto") and NLTK_AVAILABLE:
            try:
                self.processors.append(NLTKProcessor())
            except Exception as e:
                logger.warning(f"Failed to setup NLTK: {e}")

        if prefer_method == "auto" and SPACY_AVAILABLE:
            try:
                self.processors.append(SpacyProcessor())
            except Exception as e:
                logger.warning(f"Failed to setup spacy: {e}")

        # Always add regex as fallback
        self.processors.append(RegexProcessor())

        available_methods = [
            type(p).__name__.replace("Processor", "").lower()
            for p in self.processors
            if p.is_available()
        ]
        logger.info(f"Text processors available: {available_methods}")

    def get_processor(self) -> TextProcessorProtocol:
        """Get first available processor."""
        for processor in self.processors:
            if processor.is_available():
                return processor

        raise RuntimeError("No text processors available")

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text with best available method."""
        if not text.strip():
            return []

        processor = self.get_processor()
        return processor.tokenize(text)

    def lemmatize(self, word: str) -> str:
        """Lemmatize word with best available method."""
        if not word.strip():
            return word

        processor = self.get_processor()
        return processor.lemmatize(word)

    def process(self, text: str) -> ProcessingResult:
        """Process text and return detailed result."""
        import time

        start_time = time.time()

        if not text.strip():
            return ProcessingResult(text="", tokens=[])

        processor = self.get_processor()
        tokens = processor.tokenize(text)
        processing_time = (time.time() - start_time) * 1000

        return ProcessingResult(
            text=text,
            tokens=tokens,
            method_used=type(processor).__name__.replace("Processor", "").lower(),
            processing_time_ms=processing_time,
            features_available=[
                type(p).__name__.replace("Processor", "").lower()
                for p in self.processors
                if p.is_available()
            ],
        )


# Global instance for convenience
_default_processor: TextProcessor | None = None


def get_text_processor() -> TextProcessor:
    """Get global text processor instance."""
    global _default_processor

    if _default_processor is None:
        _default_processor = TextProcessor()

    return _default_processor
