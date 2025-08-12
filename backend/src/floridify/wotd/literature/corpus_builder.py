"""Literature corpus builder using generalized Gutenberg connector and AI analysis."""

from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from pathlib import Path
from typing import Optional

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    
    # Download required NLTK data
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        try:
            nltk.download("punkt_tab")
        except:
            nltk.download("punkt")
    
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords")
        
    NLTK_AVAILABLE = True
    
except ImportError:
    NLTK_AVAILABLE = False

from ...ai import get_openai_connector
from ...utils.logging import get_logger
from ..core import Author, Complexity, Era, Style, WOTDCorpus, WOTDWord
from .connector import GutenbergConnector
from .mappings import AUTHOR_METADATA, get_author_metadata, get_author_works
from .models import LiteraryWord

logger = get_logger(__name__)


class LiteratureCorpusBuilder:
    """Build training corpora from literary texts using AI analysis."""
    
    def __init__(self, connector: Optional[GutenbergConnector] = None):
        """Initialize with optional custom Gutenberg connector."""
        self.connector = connector or GutenbergConnector()
        
        if NLTK_AVAILABLE:
            self.stop_words = set(stopwords.words('english'))
        else:
            # Fallback minimal stopwords list
            self.stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 
                'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 
                'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 
                'her', 'us', 'them'
            }
    
    async def build_author_corpus(
        self, 
        author: Author,
        max_works: Optional[int] = None,
        max_words: int = 200,
        use_ai_analysis: bool = True
    ) -> WOTDCorpus:
        """Build a corpus for a single author with AI semantic analysis.
        
        Args:
            author: Author to process
            max_works: Maximum number of works to process (None = all)  
            max_words: Maximum words to include in final corpus
            use_ai_analysis: Whether to use AI for semantic analysis
            
        Returns:
            WOTDCorpus with semantic metadata
        """
        logger.info(f"🏗️ Building corpus for {author.value}")
        
        # Get author's works
        works = get_author_works(author)
        if not works:
            raise ValueError(f"No works available for {author.value}")
            
        if max_works:
            works = works[:max_works]
            
        # Download texts
        texts = await self.connector.download_author_works(author, works, max_works)
        
        if not texts:
            raise ValueError(f"Failed to download any texts for {author.value}")
        
        # Extract meaningful words
        literary_words = await self._extract_meaningful_words(texts, author, max_words * 2)
        
        if use_ai_analysis:
            # Use AI analysis with literature template
            corpus = await self._analyze_with_ai(literary_words, author, max_words)
        else:
            # Fallback to heuristic analysis
            corpus = await self._analyze_with_heuristics(literary_words, author, max_words)
        
        logger.info(f"✅ Built {author.value} corpus: {len(corpus.words)} words")
        return corpus
    
    async def build_multiple_author_corpora(
        self, 
        authors: list[Author],
        max_works_per_author: Optional[int] = None,
        max_words_per_corpus: int = 200
    ) -> dict[Author, WOTDCorpus]:
        """Build corpora for multiple authors in parallel.
        
        Args:
            authors: List of authors to process
            max_works_per_author: Max works per author
            max_words_per_corpus: Max words per corpus
            
        Returns:
            Dict mapping authors to their corpora
        """
        logger.info(f"🏗️ Building corpora for {len(authors)} authors")
        
        # Build corpora concurrently
        tasks = [
            self.build_author_corpus(author, max_works_per_author, max_words_per_corpus)
            for author in authors
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        corpora = {}
        for author, result in zip(authors, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to build corpus for {author.value}: {result}")
            else:
                corpora[author] = result
        
        logger.info(f"✅ Successfully built {len(corpora)}/{len(authors)} corpora")
        return corpora
    
    async def _extract_meaningful_words(
        self, 
        texts: dict[str, str], 
        author: Author, 
        max_words: int
    ) -> list[LiteraryWord]:
        """Extract meaningful words from texts with frequency analysis."""
        
        # Combine all texts
        combined_text = ' '.join(texts.values())
        
        # Tokenize based on available tools
        if NLTK_AVAILABLE:
            try:
                words = word_tokenize(combined_text.lower())
            except:
                # Fallback if nltk fails
                words = re.findall(r'\\b[a-z]+\\b', combined_text.lower())
        else:
            words = re.findall(r'\\b[a-z]+\\b', combined_text.lower())
        
        # Filter words
        filtered_words = []
        for word in words:
            if (len(word) >= 4 and  # Minimum length
                word.isalpha() and  # Letters only
                word not in self.stop_words and  # Not a stop word
                not self._is_common_word(word)):  # Not too common
                filtered_words.append(word)
        
        # Count frequencies
        word_counts = Counter(filtered_words)
        
        # Get most interesting words (medium frequency)
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Filter out extremely common and extremely rare words
        min_freq = max(2, len(sorted_words) // 1000)  # At least 2, or 0.1% of total
        max_freq = len(sorted_words) // 20  # Top 5% might be too common
        
        interesting_words = [
            (word, count) for word, count in sorted_words
            if min_freq <= count <= max_freq
        ][:max_words]
        
        # Convert to LiteraryWord objects
        metadata = get_author_metadata(author)
        literary_words = []
        
        for word, frequency in interesting_words:
            # Find which works contain this word
            containing_works = [
                title for title, text in texts.items()
                if word in text.lower()
            ]
            
            literary_words.append(LiteraryWord(
                word=word,
                frequency=frequency,
                works=containing_works,
                author=author,
                period=metadata.period
            ))
        
        logger.info(f"📝 Extracted {len(literary_words)} meaningful words for {author.value}")
        return literary_words
    
    def _is_common_word(self, word: str) -> bool:
        """Check if word is too common/uninteresting."""
        common_patterns = [
            r'^[aeiou]{2,}',  # Vowel clusters like 'aai', 'ooo'
            r'ing$',  # Present participles (too many)
            r'ed$',   # Past tense (too many) 
            r'ly$',   # Adverbs (often less interesting)
            r'^un',   # Many un- words
            r'^re',   # Many re- words
        ]
        
        return any(re.search(pattern, word) for pattern in common_patterns)
    
    async def _analyze_with_ai(
        self, 
        words: list[LiteraryWord], 
        author: Author, 
        max_words: int
    ) -> WOTDCorpus:
        """Analyze words using AI with literature analysis template."""
        
        # Load literature analysis template
        template_path = Path(__file__).parent.parent.parent / "ai" / "prompts" / "wotd" / "literature_analysis.md"
        
        if not template_path.exists():
            logger.warning("Literature analysis template not found, using heuristics")
            return await self._analyze_with_heuristics(words, author, max_words)
        
        template_content = template_path.read_text()
        
        # Prepare input data
        word_list = [w.word for w in words[:100]]  # Process top 100 words
        word_frequencies = {w.word: w.frequency for w in words[:100]}
        metadata = get_author_metadata(author)
        
        input_data = f\"\"\"
## Input Data

**Author**: {author.value}
**Period**: {metadata.period.value}
**Genre**: {metadata.primary_genre.value}
**Word Count**: {len(words)}
**Birth Year**: {metadata.birth_year}
**Nationality**: {metadata.nationality}

**Vocabulary Sample**: {', '.join(word_list[:50])}

**Word Frequencies** (top 20):
{'; '.join([f"{w}: {f}" for w, f in list(word_frequencies.items())[:20]])}

**Sample Context**:
{self._get_sample_contexts(words[:10])}
\"\"\"
        
        # Combine template with data
        full_prompt = template_content + input_data
        
        try:
            # Get AI analysis using GPT-5 (o1)
            ai = await get_openai_connector()
            
            response = await ai.generate_text(
                prompt=full_prompt,
                model="o1",  # Use GPT-5 for enhanced analysis
                max_tokens=2500,
                temperature=0.2
            )
            
            # Parse AI response
            analysis = json.loads(response)
            
            # Extract semantic ID
            semantic_id = analysis["semantic_id"]
            
            # Get AI-suggested additions
            suggested_additions = analysis.get("augmentation", {}).get("suggested_additions", [])
            
            # Create enhanced word list
            enhanced_words = words[:max_words] + [
                LiteraryWord(
                    word=word,
                    frequency=1,
                    works=[f"{author.value}_ai_analysis"],
                    author=author,
                    period=metadata.period
                ) for word in suggested_additions[:max_words//4]  # Add up to 25% AI words
            ]
            
            # Convert to WOTD format
            wotd_words = [
                WOTDWord(word=w.word, frequency=w.frequency)
                for w in enhanced_words[:max_words]
            ]
            
            corpus = WOTDCorpus(
                id=f"{author.value}_literature",
                words=wotd_words,
                style=Style(semantic_id["style"]),
                complexity=Complexity(semantic_id["complexity"]),
                era=Era(semantic_id["era"]),
                metadata={
                    "author": author.value,
                    "source": "literature_ai_analysis",
                    "ai_analysis": analysis.get("analysis", {}),
                    "characteristics": analysis.get("characteristics", {}),
                    "quality_metrics": analysis.get("quality_metrics", {}),
                    "semantic_variation": semantic_id["variation"],
                    "word_count": len(wotd_words),
                    "period": metadata.period.value,
                    "genre": metadata.primary_genre.value,
                }
            )
            
            logger.info(
                f"✅ AI analysis for {author.value}: "
                f"style={semantic_id['style']}, complexity={semantic_id['complexity']}, "
                f"era={semantic_id['era']}, variation={semantic_id['variation']}"
            )
            
            return corpus
            
        except Exception as e:
            logger.error(f"❌ AI analysis failed for {author.value}: {e}")
            # Fallback to heuristics
            return await self._analyze_with_heuristics(words, author, max_words)
    
    async def _analyze_with_heuristics(
        self, 
        words: list[LiteraryWord], 
        author: Author, 
        max_words: int
    ) -> WOTDCorpus:
        """Fallback heuristic analysis when AI is unavailable."""
        
        metadata = get_author_metadata(author)
        
        # Use metadata to infer semantic attributes
        style_index = metadata.get_semantic_style_index()
        era_index = metadata.get_semantic_era_index()
        
        # Infer complexity from word characteristics
        avg_word_length = sum(len(w.word) for w in words) / len(words) if words else 5
        complexity_index = min(7, max(0, int((avg_word_length - 3) * 1.5)))
        
        # Convert to WOTD format
        wotd_words = [
            WOTDWord(word=w.word, frequency=w.frequency)
            for w in words[:max_words]
        ]
        
        corpus = WOTDCorpus(
            id=f"{author.value}_literature",
            words=wotd_words,
            style=Style(list(Style)[style_index % len(Style)]),
            complexity=Complexity(list(Complexity)[complexity_index % len(Complexity)]),
            era=Era(list(Era)[era_index % len(Era)]),
            metadata={
                "author": author.value,
                "source": "literature_heuristic",
                "period": metadata.period.value,
                "genre": metadata.primary_genre.value,
                "word_count": len(wotd_words),
                "avg_word_length": avg_word_length,
                "ai_augmentation": False,
            }
        )
        
        logger.info(f"✅ Heuristic analysis for {author.value}: {len(wotd_words)} words")
        return corpus
    
    def _get_sample_contexts(self, words: list[LiteraryWord]) -> str:
        """Get sample contexts for words (if available)."""
        contexts = []
        for word in words[:5]:  # Top 5 words
            if word.context_examples:
                context = word.context_examples[0][:100]  # First 100 chars
                contexts.append(f"{word.word}: \"{context}...\"")
            else:
                contexts.append(f"{word.word}: (appears in {', '.join(word.works[:2])})")
        
        return '\\n'.join(contexts)


# Convenience functions
async def build_shakespeare_corpus(max_words: int = 200) -> WOTDCorpus:
    """Build Shakespeare corpus (legacy compatibility)."""
    builder = LiteratureCorpusBuilder()
    return await builder.build_author_corpus(Author.SHAKESPEARE, max_words=max_words)


async def build_literature_training_set(
    authors: list[Author], 
    max_works_per_author: Optional[int] = None
) -> dict[str, WOTDCorpus]:
    """Build complete training set for multiple authors."""
    builder = LiteratureCorpusBuilder()
    corpora = await builder.build_multiple_author_corpora(authors, max_works_per_author)
    
    # Convert keys to strings for training compatibility
    return {author.value: corpus for author, corpus in corpora.items()}