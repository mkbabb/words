"""
Advanced phrase normalization and multi-word expression handling.

Uses modern NLP libraries for robust processing of phrases, idioms, and
multi-word expressions with state-of-the-art text normalization.
"""

from __future__ import annotations

import contractions  # type: ignore[import-untyped]
import ftfy
import regex
import spacy
import unicodedata2 as unicodedata  # type: ignore[import-not-found]
from pydantic import BaseModel, Field
from tokenizers import pre_tokenizers  # type: ignore[import-untyped]


class MultiWordExpression(BaseModel):
    """Represents a multi-word expression or phrase."""

    text: str = Field(..., description="Original text")
    normalized: str = Field(..., description="Normalized form")
    word_count: int = Field(..., gt=0, description="Number of words")
    is_idiom: bool = Field(default=False, description="Whether this is an idiomatic expression")
    language: str = Field(default="en", description="Language code")
    frequency: float = Field(default=0.0, ge=0.0, description="Usage frequency if available")

    model_config = {"frozen": True}


class PhraseNormalizer:
    """
    Advanced phrase normalization using modern NLP libraries.

    Leverages spaCy, HuggingFace tokenizers, and specialized libraries for
    state-of-the-art text normalization, contraction expansion, and phrase processing.
    """

    def __init__(self, language: str = "en") -> None:
        """Initialize the advanced phrase normalizer."""
        self.language = language

        # Load spaCy model for advanced text processing
        try:
            if language == "en":
                self.nlp = spacy.load("en_core_web_sm")
            elif language == "fr":
                self.nlp = spacy.load("fr_core_news_sm")
            else:
                self.nlp = spacy.load("en_core_web_sm")  # fallback
        except OSError:
            # Fallback to basic spacy model if language-specific model not available
            self.nlp = spacy.blank(language)

        # Configure spaCy pipeline for phrase processing
        self.nlp.add_pipe("sentencizer")

        # HuggingFace tokenizer for advanced preprocessing
        self.tokenizer = pre_tokenizers.Whitespace()

        # Compiled regex patterns for performance (using advanced regex library)
        self._whitespace_pattern = regex.compile(r"\s+")
        self._punctuation_pattern = regex.compile(
            r"[^\p{L}\p{N}\s\'-]"
        )  # Unicode-aware, preserve hyphens
        self._hyphen_pattern = regex.compile(
            r"[–—‒]"
        )  # Various dash types (excluding regular hyphen)
        self._apostrophe_pattern = regex.compile(r"[''`" "]")  # Various apostrophe types

    def normalize(self, text: str) -> str:
        """
        Advanced text normalization using modern NLP libraries.

        Process:
        1. Fix text encoding issues (ftfy)
        2. Unicode normalization (unicodedata2)
        3. Contraction expansion (contractions library)
        4. spaCy-based linguistic processing
        5. Advanced punctuation and whitespace handling

        Args:
            text: Raw input text

        Returns:
            Normalized text suitable for search operations
        """
        if not text:
            return ""

        # Step 1: Fix text encoding issues (mojibake, etc.)
        normalized = ftfy.fix_text(text)

        # Step 2: Unicode normalization (using faster unicodedata2)
        normalized = unicodedata.normalize("NFC", normalized)

        # Step 3: Case normalization
        normalized = normalized.lower()

        # Step 4: Standardize apostrophes and hyphens first
        normalized = self._apostrophe_pattern.sub("'", normalized)
        normalized = self._hyphen_pattern.sub("-", normalized)

        # Step 5: Expand contractions using modern library
        try:
            normalized = contractions.fix(normalized, slang=False)
        except Exception:
            # Fallback to original if contractions library fails
            pass

        # Step 6: Advanced punctuation handling with Unicode awareness
        normalized = self._punctuation_pattern.sub(" ", normalized)

        # Step 7: Normalize whitespace without splitting hyphenated words
        # Use simple whitespace normalization instead of spaCy tokenization
        # to preserve hyphenated compounds like "vis-à-vis"
        normalized = str(self._whitespace_pattern.sub(" ", normalized))

        return normalized.strip()

    def extract_phrases(self, text: str) -> list[MultiWordExpression]:
        """
        Extract multi-word expressions using advanced NLP techniques.

        Uses spaCy for:
        - Named entity recognition
        - Noun phrase detection
        - Dependency parsing for compound phrases
        - Linguistic pattern matching

        Args:
            text: Input text to analyze

        Returns:
            List of identified multi-word expressions
        """
        if not text.strip():
            return []

        phrases: list[MultiWordExpression] = []

        # Process with spaCy for advanced linguistic analysis
        doc = self.nlp(text)

        # Extract noun phrases (if model supports it)
        try:
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) > 1:  # Multi-word only
                    normalized = self.normalize(chunk.text)
                    if normalized:
                        phrases.append(
                            MultiWordExpression(
                                text=chunk.text,
                                normalized=normalized,
                                word_count=len(normalized.split()),
                                is_idiom=False,
                                language=self.language,
                            )
                        )
        except ValueError:
            # Model doesn't support noun chunks, skip this step
            pass

        # Extract named entities (often phrases)
        try:
            for ent in doc.ents:
                if len(ent.text.split()) > 1:  # Multi-word only
                    normalized = self.normalize(ent.text)
                    if normalized:
                        phrases.append(
                            MultiWordExpression(
                                text=ent.text,
                                normalized=normalized,
                                word_count=len(normalized.split()),
                                is_idiom=ent.label_ in ["WORK_OF_ART", "EVENT"],  # Likely idiomatic
                                language=self.language,
                            )
                        )
        except ValueError:
            # Model doesn't support named entities, skip this step
            pass

        # Look for hyphenated compounds using advanced regex
        hyphenated_phrases = self._find_hyphenated_phrases(text)
        phrases.extend(hyphenated_phrases)

        # Look for quoted phrases
        quoted_phrases = self._find_quoted_phrases(text)
        phrases.extend(quoted_phrases)

        # Deduplicate by normalized form
        unique_phrases = {}
        for phrase in phrases:
            if phrase.normalized not in unique_phrases:
                unique_phrases[phrase.normalized] = phrase

        return list(unique_phrases.values())

    def _find_hyphenated_phrases(self, text: str) -> list[MultiWordExpression]:
        """Find hyphenated compound expressions using advanced regex."""
        phrases = []

        # Advanced pattern for hyphenated compounds (Unicode-aware)
        hyphen_pattern = regex.compile(r"\b\p{L}+(?:[-–—]\p{L}+){1,4}\b")
        matches = hyphen_pattern.finditer(text)

        for match in matches:
            phrase_text = match.group()
            # Count hyphen variants
            hyphen_count = len(regex.findall(r"[-–—]", phrase_text))
            word_count = hyphen_count + 1

            if word_count >= 2:  # At least 2 words
                normalized = self.normalize(phrase_text)
                if normalized:
                    phrases.append(
                        MultiWordExpression(
                            text=phrase_text,
                            normalized=normalized,
                            word_count=word_count,
                            is_idiom=False,
                            language=self.language,
                        )
                    )

        return phrases

    def _find_quoted_phrases(self, text: str) -> list[MultiWordExpression]:
        """Find phrases enclosed in quotes using advanced Unicode-aware regex."""
        phrases = []

        # Unicode-aware pattern for quoted text (covers many quote types)
        quote_pattern = regex.compile(r'["\'\'""\«]([^"\'\'""\»]+)["\'\'""\»]')
        matches = quote_pattern.finditer(text)

        for match in matches:
            phrase_text = match.group(1).strip()
            if not phrase_text:
                continue

            normalized = self.normalize(phrase_text)
            word_count = len(normalized.split()) if normalized else 0

            if word_count >= 2:  # Multi-word phrases only
                phrases.append(
                    MultiWordExpression(
                        text=phrase_text,
                        normalized=normalized,
                        word_count=word_count,
                        is_idiom=True,  # Quoted phrases often idiomatic
                        language=self.language,
                    )
                )

        return phrases

    def is_phrase(self, text: str) -> bool:
        """
        Determine if text represents a multi-word expression using spaCy.

        Args:
            text: Text to analyze

        Returns:
            True if text is a multi-word expression
        """
        if not text.strip():
            return False

        # Use spaCy for intelligent tokenization
        doc = self.nlp(text.strip())
        tokens = [token for token in doc if not token.is_space and not token.is_punct]

        # Multiple meaningful tokens = phrase
        if len(tokens) > 1:
            return True

        # Single hyphenated compound = phrase (Unicode-aware)
        if len(tokens) == 1 and regex.search(r"[-–—]", tokens[0].text):
            return True

        return False

    def split_phrase(self, phrase: str) -> list[str]:
        """
        Split a phrase into component words using advanced tokenization.

        Args:
            phrase: Phrase to split

        Returns:
            List of component words
        """
        if not phrase.strip():
            return []

        # Use spaCy for intelligent tokenization
        doc = self.nlp(phrase)

        # Extract meaningful tokens (excluding spaces and some punctuation)
        words = []
        for token in doc:
            if not token.is_space:
                # Handle hyphenated compounds
                if "-" in token.text:
                    # Split on hyphens but preserve as separate words
                    parts = token.text.split("-")
                    words.extend([part for part in parts if part.strip()])
                else:
                    words.append(token.text)

        return [word for word in words if word.strip()]

    def join_words(self, words: list[str], prefer_hyphens: bool = False) -> str:
        """
        Join words into a phrase with intelligent separator selection.

        Args:
            words: List of words to join
            prefer_hyphens: Whether to use hyphens instead of spaces

        Returns:
            Joined phrase
        """
        if not words:
            return ""

        # Filter out empty words
        valid_words = [word.strip() for word in words if word.strip()]
        if not valid_words:
            return ""

        separator = "-" if prefer_hyphens else " "
        return separator.join(valid_words)
