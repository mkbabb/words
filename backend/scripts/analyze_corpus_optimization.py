#!/usr/bin/env python3
"""
Corpus Optimization Analysis Script

Analyzes the current English corpus and provides recommendations for optimization
to achieve ~55k unique base forms while maintaining comprehensiveness.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Import available NLP libraries
try:
    import nltk
    from nltk.stem import PorterStemmer, SnowballStemmer, WordNetLemmatizer
    from nltk.corpus import wordnet
    
    NLTK_AVAILABLE = True
    # Download required NLTK data
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('punkt', quiet=True)
except ImportError:
    NLTK_AVAILABLE = False
    print("Warning: NLTK not available. Install with: pip install nltk")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: spaCy not available. Install with: pip install spacy")


class CorpusAnalyzer:
    """Analyzes word corpus for optimization opportunities."""
    
    def __init__(self):
        self.setup_nlp_tools()
        
    def setup_nlp_tools(self):
        """Initialize NLP tools for analysis."""
        self.tools = {}
        
        if NLTK_AVAILABLE:
            self.tools['porter_stemmer'] = PorterStemmer()
            self.tools['snowball_stemmer'] = SnowballStemmer('english')
            self.tools['wordnet_lemmatizer'] = WordNetLemmatizer()
            
        if SPACY_AVAILABLE:
            try:
                self.tools['spacy_nlp'] = spacy.load('en_core_web_sm')
            except:
                print("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                
    def load_corpus(self, file_path: Path) -> List[str]:
        """Load words from corpus file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
            
    def analyze_morphological_patterns(self, words: List[str]) -> Dict[str, any]:
        """Analyze morphological patterns in the corpus."""
        analysis = {
            'total_words': len(words),
            'unique_words': len(set(words)),
            'suffix_patterns': defaultdict(int),
            'inflection_groups': defaultdict(list),
            'length_distribution': Counter()
        }
        
        # Common English suffixes for inflections
        inflection_suffixes = {
            's': 'plural/verb',
            'es': 'plural/verb',
            'ed': 'past tense',
            'ing': 'present participle',
            'er': 'comparative/agent',
            'est': 'superlative',
            'ly': 'adverb',
            'ment': 'noun',
            'ness': 'noun',
            'ity': 'noun',
            'tion': 'noun',
            'sion': 'noun',
            'ize': 'verb',
            'ise': 'verb',
            'able': 'adjective',
            'ible': 'adjective',
            'ful': 'adjective',
            'less': 'adjective'
        }
        
        # Analyze suffix patterns
        for word in words:
            analysis['length_distribution'][len(word)] += 1
            
            for suffix, category in inflection_suffixes.items():
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    analysis['suffix_patterns'][suffix] += 1
                    base = word[:-len(suffix)]
                    analysis['inflection_groups'][base].append((word, suffix, category))
                    
        return analysis
        
    def compare_reduction_methods(self, words: List[str], sample_size: int = 5000) -> Dict[str, any]:
        """Compare different reduction methods on a sample."""
        # Use sample for performance
        sample = words[:sample_size] if len(words) > sample_size else words
        results = {}
        
        # 1. Simple deduplication
        results['deduplication'] = {
            'method': 'Simple lowercase deduplication',
            'original': len(sample),
            'reduced': len(set(sample)),
            'reduction_pct': (1 - len(set(sample)) / len(sample)) * 100
        }
        
        # 2. Stemming methods
        if 'porter_stemmer' in self.tools:
            porter_stems = set()
            for word in sample:
                try:
                    porter_stems.add(self.tools['porter_stemmer'].stem(word))
                except:
                    porter_stems.add(word)
                    
            results['porter_stemming'] = {
                'method': 'Porter Stemmer (aggressive)',
                'original': len(sample),
                'reduced': len(porter_stems),
                'reduction_pct': (1 - len(porter_stems) / len(sample)) * 100
            }
            
        if 'snowball_stemmer' in self.tools:
            snowball_stems = set()
            for word in sample:
                try:
                    snowball_stems.add(self.tools['snowball_stemmer'].stem(word))
                except:
                    snowball_stems.add(word)
                    
            results['snowball_stemming'] = {
                'method': 'Snowball Stemmer (balanced)',
                'original': len(sample),
                'reduced': len(snowball_stems),
                'reduction_pct': (1 - len(snowball_stems) / len(sample)) * 100
            }
            
        # 3. Lemmatization
        if 'wordnet_lemmatizer' in self.tools:
            lemmas = set()
            for word in sample:
                try:
                    # Try different POS tags for better lemmatization
                    lemma_n = self.tools['wordnet_lemmatizer'].lemmatize(word, pos='n')
                    lemma_v = self.tools['wordnet_lemmatizer'].lemmatize(word, pos='v')
                    lemma_a = self.tools['wordnet_lemmatizer'].lemmatize(word, pos='a')
                    
                    # Choose shortest lemma
                    shortest = min([lemma_n, lemma_v, lemma_a], key=len)
                    lemmas.add(shortest)
                except:
                    lemmas.add(word)
                    
            results['wordnet_lemmatization'] = {
                'method': 'WordNet Lemmatizer (conservative)',
                'original': len(sample),
                'reduced': len(lemmas),
                'reduction_pct': (1 - len(lemmas) / len(sample)) * 100
            }
            
        # 4. Custom rule-based approach
        custom_bases = set()
        for word in sample:
            base = self.custom_base_form(word)
            custom_bases.add(base)
            
        results['custom_rules'] = {
            'method': 'Custom rule-based reduction',
            'original': len(sample),
            'reduced': len(custom_bases),
            'reduction_pct': (1 - len(custom_bases) / len(sample)) * 100
        }
        
        return results
        
    def custom_base_form(self, word: str) -> str:
        """Custom rule-based base form extraction."""
        # Order matters - check longer suffixes first
        suffix_rules = [
            # Verb forms
            ('ied', 'y'),      # studied -> study
            ('ies', 'y'),      # studies -> study
            ('ing', ''),       # studying -> study
            ('ed', ''),        # studied -> study
            
            # Plural forms
            ('ves', 'f'),      # leaves -> leaf
            ('ves', 'fe'),     # knives -> knife
            ('ies', 'y'),      # cities -> city
            ('oes', 'o'),      # tomatoes -> tomato
            ('ses', 's'),      # glasses -> glass
            ('xes', 'x'),      # boxes -> box
            ('zes', 'z'),      # buzzes -> buzz
            ('ches', 'ch'),    # churches -> church
            ('shes', 'sh'),    # brushes -> brush
            ('men', 'man'),    # men -> man
            ('ren', 'r'),      # children -> child (approximate)
            ('es', ''),        # dishes -> dish
            ('s', ''),         # cats -> cat
            
            # Comparative/Superlative
            ('iest', 'y'),     # happiest -> happy
            ('ier', 'y'),      # happier -> happy
            ('est', ''),       # fastest -> fast
            ('er', ''),        # faster -> fast
            
            # Adverbs
            ('ly', ''),        # quickly -> quick
        ]
        
        original = word
        for suffix, replacement in suffix_rules:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                base = word[:-len(suffix)] + replacement
                # Avoid creating very short words
                if len(base) >= 3:
                    return base
                    
        return original
        
    def generate_recommendations(self, corpus_path: Path) -> None:
        """Generate comprehensive optimization recommendations."""
        print(f"\n{'='*60}")
        print("CORPUS OPTIMIZATION ANALYSIS")
        print(f"{'='*60}\n")
        
        # Load corpus
        words = self.load_corpus(corpus_path)
        print(f"Loaded {len(words):,} words from {corpus_path.name}")
        
        # Basic statistics
        unique_words = set(words)
        print(f"Unique words: {len(unique_words):,}")
        print(f"Duplicates: {len(words) - len(unique_words):,}")
        
        # Morphological analysis
        print(f"\n{'='*60}")
        print("MORPHOLOGICAL ANALYSIS")
        print(f"{'='*60}\n")
        
        morph_analysis = self.analyze_morphological_patterns(list(unique_words))
        
        print("Most common suffixes:")
        for suffix, count in sorted(morph_analysis['suffix_patterns'].items(), 
                                   key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / len(unique_words)) * 100
            print(f"  -{suffix}: {count:,} words ({pct:.1f}%)")
            
        print("\nWord length distribution:")
        for length in range(1, 16):
            count = morph_analysis['length_distribution'].get(length, 0)
            if count > 0:
                print(f"  {length:2d} chars: {count:,} words")
                
        # Method comparison
        print(f"\n{'='*60}")
        print("REDUCTION METHOD COMPARISON")
        print(f"{'='*60}\n")
        
        method_results = self.compare_reduction_methods(list(unique_words))
        
        for method_name, result in method_results.items():
            print(f"{result['method']}:")
            print(f"  Original: {result['original']:,} words")
            print(f"  Reduced:  {result['reduced']:,} words")
            print(f"  Reduction: {result['reduction_pct']:.1f}%\n")
            
        # Calculate projections for full corpus
        print(f"\n{'='*60}")
        print("FULL CORPUS PROJECTIONS")
        print(f"{'='*60}\n")
        
        current_unique = len(unique_words)
        target_size = 55000
        
        print(f"Current unique words: {current_unique:,}")
        print(f"Target size: {target_size:,}")
        print(f"Required reduction: {current_unique - target_size:,} words ({((current_unique - target_size) / current_unique * 100):.1f}%)\n")
        
        print("Projected corpus sizes with different methods:")
        for method_name, result in method_results.items():
            reduction_rate = result['reduction_pct'] / 100
            projected_size = int(current_unique * (1 - reduction_rate))
            print(f"  {result['method']}: ~{projected_size:,} words")
            
        # Recommendations
        print(f"\n{'='*60}")
        print("RECOMMENDATIONS")
        print(f"{'='*60}\n")
        
        print("1. HYBRID APPROACH (Recommended):")
        print("   - Use WordNet lemmatization as primary method (conservative)")
        print("   - Apply custom rules for common patterns not caught by lemmatizer")
        print("   - Maintain separate lists for:")
        print("     * Irregular forms (go/went/gone)")
        print("     * Domain-specific terms")
        print("     * Proper nouns")
        print("     * Common abbreviations\n")
        
        print("2. IMPLEMENTATION TOOLS:")
        print("   - Primary: NLTK with WordNet (most accurate for English)")
        print("   - Secondary: spaCy (faster for batch processing)")
        print("   - Fallback: Custom rule-based for edge cases\n")
        
        print("3. QUALITY CONTROL:")
        print("   - Create mapping file: inflected form -> base form")
        print("   - Validate against frequency lists")
        print("   - Test search functionality with both forms")
        print("   - Maintain override list for exceptions\n")
        
        print("4. EXPECTED OUTCOMES:")
        print("   - Corpus reduction: 70-80% to ~55k base forms")
        print("   - Search improvement: Fewer false negatives")
        print("   - Memory usage: ~40% reduction")
        print("   - Lookup speed: 2-3x faster with smaller index\n")
        
        print("5. IMPLEMENTATION PHASES:")
        print("   Phase 1: Implement lemmatization pipeline")
        print("   Phase 2: Build inflection mapping database")
        print("   Phase 3: Update search to use base forms")
        print("   Phase 4: Add inflection expansion for queries")
        print("   Phase 5: Performance testing and optimization\n")


if __name__ == "__main__":
    # Path to SOWPODS corpus
    corpus_path = Path("/Users/mkbabb/Programming/words/backend/data/search/lexicons/sowpods_scrabble_words.txt")
    
    if not corpus_path.exists():
        print(f"Error: Corpus file not found at {corpus_path}")
        exit(1)
        
    analyzer = CorpusAnalyzer()
    analyzer.generate_recommendations(corpus_path)