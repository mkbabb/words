"""Advanced word normalization for reducing corpus size and mapping variants to roots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import nltk
import spacy
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer, SnowballStemmer, WordNetLemmatizer
from rich.console import Console
from spacy.language import Language

console = Console()

@dataclass
class NormalizationStats:
    """Statistics from word normalization process."""
    total_words: int = 0
    normalized_words: int = 0
    unique_roots: int = 0
    compression_ratio: float = 0.0
    
    # Breakdown by type
    plurals_normalized: int = 0
    verb_forms_normalized: int = 0
    adjective_forms_normalized: int = 0
    other_forms_normalized: int = 0

class WordNormalizer:
    """Advanced word normalizer using stemming and lemmatization to reduce corpus size."""
    
    def __init__(
        self,
        method: str = "spacy",  # "spacy", "nltk", or "hybrid"
        language: str = "en",
        cache_file: Path | None = None,
        min_word_length: int = 3
    ):
        self.method = method
        self.language = language
        self.min_word_length = min_word_length
        self.cache_file = cache_file
        
        # Word mappings cache (normalized -> original_forms)
        self.word_mappings: dict[str, set[str]] = {}
        # Reverse mapping (original -> normalized)
        self.reverse_mappings: dict[str, str] = {}
        
        # Initialize processors
        self.spacy_nlp: Language | None = None
        self.porter_stemmer: PorterStemmer | None = None
        self.snowball_stemmer: SnowballStemmer | None = None
        self.wordnet_lemmatizer: WordNetLemmatizer | None = None
        
        # Load cache if exists
        self._load_cache()
        
        # Initialize processors based on method
        self._initialize_processors()
    
    def _initialize_processors(self) -> None:
        """Initialize normalization processors based on selected method."""
        if self.method in ["spacy", "hybrid"]:
            try:
                model_name = f"{self.language}_core_web_sm"
                self.spacy_nlp = spacy.load(model_name)
            except OSError:
                console.print(f"[yellow]spaCy model {self.language}_core_web_sm not found. Install with: python -m spacy download {self.language}_core_web_sm[/yellow]")
                if self.method == "spacy":
                    self.method = "nltk"
        
        if self.method in ["nltk", "hybrid"]:
            # Download required NLTK data
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('omw-1.4', quiet=True)
            
            self.porter_stemmer = PorterStemmer()
            self.snowball_stemmer = SnowballStemmer('english')
            self.wordnet_lemmatizer = WordNetLemmatizer()
    
    def _load_cache(self) -> None:
        """Load cached word mappings from file."""
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert sets back from lists
                    self.word_mappings = {
                        normalized: set(variants) 
                        for normalized, variants in data.get('mappings', {}).items()
                    }
                    self.reverse_mappings = data.get('reverse_mappings', {})
                console.print(f"[blue]Loaded {len(self.word_mappings)} cached word mappings[/blue]")
            except Exception as e:
                console.print(f"[yellow]Could not load cache: {e}[/yellow]")
    
    def _save_cache(self) -> None:
        """Save word mappings to cache file."""
        if not self.cache_file:
            return
        
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                # Convert sets to lists for JSON serialization
                data = {
                    'mappings': {
                        normalized: list(variants) 
                        for normalized, variants in self.word_mappings.items()
                    },
                    'reverse_mappings': self.reverse_mappings
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.print(f"[blue]Saved {len(self.word_mappings)} word mappings to cache[/blue]")
        except Exception as e:
            console.print(f"[yellow]Could not save cache: {e}[/yellow]")
    
    def _get_wordnet_pos(self, word: str) -> str:
        """Map POS tag to WordNet POS tag."""
        tag = nltk.pos_tag([word])[0][1][0].upper()
        tag_dict = {
            'J': wordnet.ADJ,      # Adjective
            'N': wordnet.NOUN,     # Noun
            'V': wordnet.VERB,     # Verb
            'R': wordnet.ADV       # Adverb
        }
        return tag_dict.get(tag, wordnet.NOUN)  # type: ignore[no-any-return]
    
    def _basic_normalize(self, word: str) -> str:
        """Basic rule-based normalization for common patterns."""
        word = word.lower().strip()
        
        # Skip if too short
        if len(word) < self.min_word_length:
            return word
        
        # Common plural patterns
        if word.endswith('ies') and len(word) > 4:
            return word[:-3] + 'y'  # stories -> story
        elif word.endswith('es') and len(word) > 3:
            if word.endswith(('ches', 'shes', 'xes', 'zes')):
                return word[:-2]  # boxes -> box
            elif word.endswith('ves'):
                return word[:-3] + 'f'  # knives -> knife
            else:
                return word[:-1]  # goes -> go
        elif word.endswith('s') and len(word) > 3:
            # Avoid removing 's' from words that end naturally with 's'
            if not word.endswith(('ss', 'us', 'is')):
                return word[:-1]  # cats -> cat
        
        # Common verb forms
        if word.endswith('ing') and len(word) > 5:
            if word[-4] == word[-5]:  # running -> run
                return word[:-4]
            else:
                return word[:-3]  # walking -> walk
        elif word.endswith('ed') and len(word) > 4:
            if word[-3] == word[-4]:  # stopped -> stop
                return word[:-3]
            else:
                return word[:-2]  # walked -> walk
        
        # Comparative/superlative adjectives
        if word.endswith('er') and len(word) > 4:
            return word[:-2]  # bigger -> big
        elif word.endswith('est') and len(word) > 5:
            return word[:-3]  # biggest -> big
        
        return word
    
    def _spacy_normalize(self, word: str) -> tuple[str, str]:
        """Normalize using spaCy lemmatization."""
        if not self.spacy_nlp:
            return word, "unchanged"
        
        doc = self.spacy_nlp(word)
        if doc and len(doc) > 0:
            lemma = doc[0].lemma_
            pos = doc[0].pos_
            
            # Skip pronouns and special tokens
            if lemma == "-PRON-" or lemma.startswith("-"):
                return word, "unchanged"
            
            # Determine normalization type
            if pos == "NOUN" and word != lemma:
                return lemma, "plural"
            elif pos in ["VERB", "AUX"] and word != lemma:
                return lemma, "verb_form"
            elif pos == "ADJ" and word != lemma:
                return lemma, "adjective_form"
            elif word != lemma:
                return lemma, "other_form"
            else:
                return word, "unchanged"
        
        return word, "unchanged"
    
    def _nltk_normalize(self, word: str) -> tuple[str, str]:
        """Normalize using NLTK lemmatization and stemming."""
        if not (self.wordnet_lemmatizer and self.porter_stemmer):
            return word, "unchanged"
        
        
        # Get POS tag for better lemmatization
        pos = self._get_wordnet_pos(word)
        
        # Try lemmatization first (more accurate)
        lemma = self.wordnet_lemmatizer.lemmatize(word, pos=pos)
        
        if lemma != word:
            # Determine type of normalization
            if pos == wordnet.NOUN:
                return lemma, "plural"
            elif pos == wordnet.VERB:
                return lemma, "verb_form"
            elif pos == wordnet.ADJ:
                return lemma, "adjective_form"
            else:
                return lemma, "other_form"
        
        # If lemmatization didn't change the word, try stemming
        stem = self.porter_stemmer.stem(word)
        if stem != word and len(stem) >= self.min_word_length:
            return stem, "stem"
        
        return word, "unchanged"
    
    def normalize_word(self, word: str) -> tuple[str, str]:
        """
        Normalize a single word to its root form.
        
        Returns:
            Tuple of (normalized_word, normalization_type)
        """
        # Check cache first
        if word in self.reverse_mappings:
            return self.reverse_mappings[word], "cached"
        
        # Clean the word
        cleaned_word = re.sub(r'[^a-zA-Z]', '', word.lower())
        if len(cleaned_word) < self.min_word_length:
            return word, "unchanged"
        
        # Apply normalization based on method
        if self.method == "spacy":
            normalized, norm_type = self._spacy_normalize(cleaned_word)
        elif self.method == "nltk":
            normalized, norm_type = self._nltk_normalize(cleaned_word)
        elif self.method == "hybrid":
            # Try spaCy first, fall back to NLTK
            normalized, norm_type = self._spacy_normalize(cleaned_word)
            if norm_type == "unchanged":
                normalized, norm_type = self._nltk_normalize(cleaned_word)
        else:
            # Basic rule-based
            normalized = self._basic_normalize(cleaned_word)
            norm_type = "basic" if normalized != cleaned_word else "unchanged"
        
        # Update mappings
        if normalized != word:
            if normalized not in self.word_mappings:
                self.word_mappings[normalized] = set()
            self.word_mappings[normalized].add(word)
            self.reverse_mappings[word] = normalized
        
        return normalized, norm_type
    
    def normalize_word_list(self, words: list[str]) -> tuple[list[str], dict[str, set[str]], NormalizationStats]:
        """
        Normalize a list of words and return unique roots with mappings.
        
        Returns:
            Tuple of (normalized_words, word_mappings, statistics)
        """
        console.print(f"[blue]Normalizing {len(words)} words using {self.method} method...[/blue]")
        
        stats = NormalizationStats()
        stats.total_words = len(words)
        
        normalized_words = []
        normalization_counts = {
            "plural": 0,
            "verb_form": 0, 
            "adjective_form": 0,
            "other_form": 0,
            "stem": 0,
            "basic": 0
        }
        
        for word in words:
            normalized, norm_type = self.normalize_word(word)
            normalized_words.append(normalized)
            
            if norm_type in normalization_counts:
                normalization_counts[norm_type] += 1
            
            if normalized != word:
                stats.normalized_words += 1
        
        # Calculate statistics
        stats.plurals_normalized = normalization_counts["plural"]
        stats.verb_forms_normalized = normalization_counts["verb_form"]
        stats.adjective_forms_normalized = normalization_counts["adjective_form"]
        stats.other_forms_normalized = (
            normalization_counts["other_form"] + 
            normalization_counts["stem"] + 
            normalization_counts["basic"]
        )
        
        # Get unique normalized words
        unique_normalized = list(set(normalized_words))
        stats.unique_roots = len(unique_normalized)
        stats.compression_ratio = (stats.total_words - stats.unique_roots) / stats.total_words * 100
        
        # Save cache
        self._save_cache()
        
        return unique_normalized, self.word_mappings, stats
    
    def get_variants(self, normalized_word: str) -> set[str]:
        """Get all original word variants for a normalized word."""
        return self.word_mappings.get(normalized_word, {normalized_word})
    
    def get_normalization_summary(self, stats: NormalizationStats) -> str:
        """Generate a summary of normalization results."""
        return f"""Word Normalization Summary ({self.method} method):
Total words: {stats.total_words:,}
Normalized words: {stats.normalized_words:,} ({stats.normalized_words/stats.total_words*100:.1f}%)
Unique roots: {stats.unique_roots:,}
Compression ratio: {stats.compression_ratio:.1f}%

Normalization breakdown:
  Plurals: {stats.plurals_normalized:,}
  Verb forms: {stats.verb_forms_normalized:,}
  Adjective forms: {stats.adjective_forms_normalized:,}
  Other forms: {stats.other_forms_normalized:,}

Space reduction: {stats.total_words - stats.unique_roots:,} words removed
"""

# Predefined normalizer configurations
class NormalizerPresets:
    """Predefined normalizer configurations for different use cases."""
    
    @staticmethod
    def conservative() -> WordNormalizer:
        """Conservative normalization - prefer accuracy over compression."""
        return WordNormalizer(
            method="spacy",
            cache_file=Path("./cache/word_normalizer_conservative.json"),
            min_word_length=2
        )
    
    @staticmethod
    def aggressive() -> WordNormalizer:
        """Aggressive normalization - maximize compression."""
        return WordNormalizer(
            method="hybrid",
            cache_file=Path("./cache/word_normalizer_aggressive.json"),
            min_word_length=3
        )
    
    @staticmethod
    def fast() -> WordNormalizer:
        """Fast normalization - basic rules for speed."""
        return WordNormalizer(
            method="basic",
            cache_file=Path("./cache/word_normalizer_fast.json"),
            min_word_length=3
        )
    
    @staticmethod
    def balanced() -> WordNormalizer:
        """Balanced normalization - good accuracy and compression."""
        return WordNormalizer(
            method="nltk",
            cache_file=Path("./cache/word_normalizer_balanced.json"),
            min_word_length=3
        )