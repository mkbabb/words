"""Literature corpus builder for processing and analyzing literary texts.

Migrated and enhanced from wotd/literature/corpus_builder.py.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from rich.console import Console

try:
    import spacy
except ImportError:
    spacy = None

from ...utils.logging import get_logger
from .api.gutenberg import GutenbergConnector
from .models import AuthorInfo, LiteraryWord, LiteraryWork

logger = get_logger(__name__)
console = Console()


class LiteratureCorpusBuilder:
    """Build and analyze literature corpora for WOTD training."""
    
    def __init__(self, connector: GutenbergConnector | None = None):
        """Initialize with optional connector."""
        self.connector = connector or GutenbergConnector()
        self.nlp = None  # Lazy load spaCy
        
        # Word frequency tracking
        self.word_frequencies: Counter[str] = Counter()
        self.word_works: defaultdict[str, set[str]] = defaultdict(set)
        self.word_contexts: defaultdict[str, list[str]] = defaultdict(list)
        
    def _load_nlp(self):
        """Lazy load spaCy model."""
        if self.nlp is None and spacy is not None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
                
    async def build_author_corpus(
        self,
        author: AuthorInfo,
        works: list[LiteraryWork],
        max_works: int | None = None,
        min_word_length: int = 3,
        max_context_per_word: int = 5,
    ) -> list[LiteraryWord]:
        """Build corpus from an author's works.
        
        Args:
            author: AuthorInfo object
            works: List of LiteraryWork objects
            max_works: Maximum number of works to process
            min_word_length: Minimum word length to include
            max_context_per_word: Maximum context examples per word
            
        Returns:
            List of LiteraryWord objects
        """
        self._load_nlp()
        
        # Download works
        texts = await self.connector.download_author_works(author, works, max_works)
        
        # Process each work
        for title, text in texts.items():
            self._process_text(text, title, author)
            
        # Build LiteraryWord objects
        literary_words = []
        for word, frequency in self.word_frequencies.most_common():
            if len(word) < min_word_length:
                continue
                
            literary_word = LiteraryWord(
                word=word,
                frequency=frequency,
                works=list(self.word_works[word]),
                author_name=author.name,
                period=author.period,
                context_examples=self.word_contexts[word][:max_context_per_word],
            )
            
            # Add POS tag if spaCy is available
            if self.nlp:
                doc = self.nlp(word)
                if doc:
                    literary_word.pos_tag = doc[0].pos_
                    literary_word.lemma = doc[0].lemma_
                    
            literary_words.append(literary_word)
            
        logger.info(f"✅ Built corpus with {len(literary_words)} unique words from {len(texts)} works")
        return literary_words
        
    def _process_text(self, text: str, title: str, author: AuthorInfo) -> None:
        """Process a text and extract words with context."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            # Clean and tokenize
            words = self._tokenize(sentence)
            
            for word in words:
                word_lower = word.lower()
                
                # Track frequency
                self.word_frequencies[word_lower] += 1
                
                # Track which work it appears in
                self.word_works[word_lower].add(title)
                
                # Save context (limit to 200 chars)
                context = sentence.strip()[:200]
                if context and len(self.word_contexts[word_lower]) < 10:
                    self.word_contexts[word_lower].append(context)
                    
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Filter out very short words and numbers
        return [w for w in words if len(w) > 2 and not w.isdigit()]
        
    async def build_multi_author_corpus(
        self,
        authors_works: dict[AuthorInfo, list[LiteraryWork]],
        max_works_per_author: int | None = None,
    ) -> dict[AuthorInfo, list[LiteraryWord]]:
        """Build corpus from multiple authors.
        
        Args:
            authors_works: Mapping of authors to their works
            max_works_per_author: Maximum works per author
            
        Returns:
            Mapping of authors to their literary words
        """
        corpora = {}
        
        for author, works in authors_works.items():
            console.print(f"[blue]Building corpus for {author.value}...[/blue]")
            
            # Create fresh builder for each author
            builder = LiteratureCorpusBuilder(self.connector)
            corpus = await builder.build_author_corpus(
                author, works, max_works_per_author
            )
            corpora[author] = corpus
            
        return corpora
        
    def analyze_vocabulary_richness(self) -> dict[str, Any]:
        """Analyze vocabulary richness metrics."""
        total_words = sum(self.word_frequencies.values())
        unique_words = len(self.word_frequencies)
        
        # Calculate type-token ratio
        ttr = unique_words / total_words if total_words > 0 else 0
        
        # Calculate hapax legomena (words appearing only once)
        hapax_count = sum(1 for freq in self.word_frequencies.values() if freq == 1)
        hapax_ratio = hapax_count / unique_words if unique_words > 0 else 0
        
        return {
            "total_words": total_words,
            "unique_words": unique_words,
            "type_token_ratio": ttr,
            "hapax_legomena": hapax_count,
            "hapax_ratio": hapax_ratio,
            "average_word_frequency": total_words / unique_words if unique_words > 0 else 0,
        }
        
    def get_characteristic_words(self, min_frequency: int = 5, top_n: int = 100) -> list[str]:
        """Get characteristic words for the corpus.
        
        Args:
            min_frequency: Minimum frequency threshold
            top_n: Number of top words to return
            
        Returns:
            List of characteristic words
        """
        # Filter by minimum frequency
        filtered = [
            word for word, freq in self.word_frequencies.items()
            if freq >= min_frequency
        ]
        
        # Sort by frequency and return top N
        return sorted(filtered, key=lambda w: self.word_frequencies[w], reverse=True)[:top_n]