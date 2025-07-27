#!/usr/bin/env python3
"""
Comprehensive Corpus Optimization Strategy for Floridify

This script provides a detailed analysis and implementation strategy for 
optimizing the English corpus to ~55k unique base forms while maintaining
search comprehensiveness.
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple, Optional

# Add the backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floridify.text.processor import TextProcessor, get_text_processor
from floridify.text.normalizer import normalize_text
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


class CorpusOptimizationStrategy:
    """Comprehensive corpus optimization analysis and recommendations."""
    
    def __init__(self):
        self.text_processor = get_text_processor()
        self.corpus_path = Path(__file__).parent.parent / "data/search/lexicons/sowpods_scrabble_words.txt"
        self.words: List[str] = []
        self.analysis_results: Dict = {}
        
    def load_corpus(self) -> None:
        """Load the SOWPODS corpus."""
        logger.info(f"Loading corpus from {self.corpus_path}")
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            self.words = [line.strip().lower() for line in f if line.strip()]
        logger.info(f"Loaded {len(self.words):,} words")
        
    def analyze_inflection_patterns(self) -> Dict[str, int]:
        """Analyze common inflection patterns in English."""
        patterns = {
            # Plurals
            'plural_s': 0,
            'plural_es': 0,
            'plural_ies': 0,
            'plural_ves': 0,
            'plural_irregular': 0,
            
            # Verb forms
            'verb_ed': 0,
            'verb_ing': 0,
            'verb_s': 0,
            'verb_ies': 0,
            
            # Comparatives/Superlatives
            'comp_er': 0,
            'super_est': 0,
            'comp_ier': 0,
            'super_iest': 0,
            
            # Derivations
            'adverb_ly': 0,
            'noun_ness': 0,
            'noun_ment': 0,
            'noun_tion': 0,
            'adj_able': 0,
            'adj_ful': 0,
            'adj_less': 0
        }
        
        for word in self.words:
            # Plural patterns
            if word.endswith('s') and not word.endswith('ss'):
                patterns['plural_s'] += 1
            elif word.endswith('es'):
                patterns['plural_es'] += 1
            elif word.endswith('ies') and len(word) > 3:
                patterns['plural_ies'] += 1
            elif word.endswith('ves'):
                patterns['plural_ves'] += 1
                
            # Verb patterns
            if word.endswith('ed') and len(word) > 3:
                patterns['verb_ed'] += 1
            elif word.endswith('ing') and len(word) > 4:
                patterns['verb_ing'] += 1
                
            # Comparative/Superlative
            if word.endswith('er') and not word.endswith('eer'):
                patterns['comp_er'] += 1
            elif word.endswith('est'):
                patterns['super_est'] += 1
                
            # Derivations
            if word.endswith('ly') and len(word) > 3:
                patterns['adverb_ly'] += 1
            elif word.endswith('ness'):
                patterns['noun_ness'] += 1
            elif word.endswith('ment'):
                patterns['noun_ment'] += 1
            elif word.endswith('tion'):
                patterns['noun_tion'] += 1
                
        return patterns
        
    def estimate_base_forms(self) -> Dict[str, any]:
        """Estimate the number of unique base forms using various methods."""
        estimates = {}
        
        # Method 1: Simple suffix stripping
        simple_bases = set()
        suffix_map = defaultdict(list)
        
        common_suffixes = ['s', 'es', 'ed', 'ing', 'er', 'est', 'ly', 'ness', 'ment', 'tion']
        
        for word in self.words:
            base = word
            for suffix in common_suffixes:
                if word.endswith(suffix) and len(word) > len(suffix) + 3:
                    potential_base = word[:-len(suffix)]
                    if potential_base in self.words:
                        base = potential_base
                        suffix_map[potential_base].append((word, suffix))
                        break
            simple_bases.add(base)
            
        estimates['simple_suffix_stripping'] = {
            'base_forms': len(simple_bases),
            'reduction': len(self.words) - len(simple_bases),
            'reduction_pct': ((len(self.words) - len(simple_bases)) / len(self.words)) * 100,
            'sample_mappings': dict(list(suffix_map.items())[:10])
        }
        
        # Method 2: Linguistic rules
        linguistic_bases = set()
        
        for word in self.words:
            base = self.apply_linguistic_rules(word)
            linguistic_bases.add(base)
            
        estimates['linguistic_rules'] = {
            'base_forms': len(linguistic_bases),
            'reduction': len(self.words) - len(linguistic_bases),
            'reduction_pct': ((len(self.words) - len(linguistic_bases)) / len(self.words)) * 100
        }
        
        # Method 3: Frequency-based clustering
        # Words that appear with common inflection patterns likely share a base
        cluster_bases = self.frequency_based_clustering()
        
        estimates['frequency_clustering'] = {
            'base_forms': len(cluster_bases),
            'reduction': len(self.words) - len(cluster_bases),
            'reduction_pct': ((len(self.words) - len(cluster_bases)) / len(self.words)) * 100
        }
        
        return estimates
        
    def apply_linguistic_rules(self, word: str) -> str:
        """Apply comprehensive linguistic rules for base form extraction."""
        original = word
        
        # Handle special cases first
        irregular_verbs = {
            'went': 'go', 'gone': 'go', 'saw': 'see', 'seen': 'see',
            'was': 'be', 'were': 'be', 'been': 'be', 'am': 'be', 'are': 'be', 'is': 'be',
            'had': 'have', 'has': 'have', 'did': 'do', 'does': 'do',
            'said': 'say', 'made': 'make', 'came': 'come', 'took': 'take', 'taken': 'take',
            'gave': 'give', 'given': 'give', 'found': 'find', 'thought': 'think',
            'brought': 'bring', 'bought': 'buy', 'caught': 'catch', 'taught': 'teach'
        }
        
        if word in irregular_verbs:
            return irregular_verbs[word]
            
        # Apply rules in order of specificity
        rules = [
            # Verb inflections
            ('ied', 'y'),      # studied -> study
            ('ying', 'y'),     # studying -> study  
            ('ies', 'y'),      # studies -> study
            ('ied', 'y'),      # cried -> cry
            
            # Double consonant + ed/ing
            ('tted', 't'),     # submitted -> submit
            ('tting', 't'),    # submitting -> submit
            ('pped', 'p'),     # stopped -> stop
            ('pping', 'p'),    # stopping -> stop
            ('nned', 'n'),     # planned -> plan
            ('nning', 'n'),    # planning -> plan
            
            # Standard verb forms
            ('ing', ''),       # walking -> walk
            ('ed', ''),        # walked -> walk
            
            # Plural forms
            ('ves', 'f'),      # leaves -> leaf, knives -> knife
            ('ves', 'fe'),     # lives -> life
            ('ies', 'y'),      # cities -> city
            ('oes', 'o'),      # tomatoes -> tomato
            ('xes', 'x'),      # boxes -> box
            ('zes', 'z'),      # buzzes -> buzz
            ('ses', 's'),      # glasses -> glass
            ('shes', 'sh'),    # brushes -> brush
            ('ches', 'ch'),    # churches -> church
            ('es', ''),        # dishes -> dish
            ('s', ''),         # cats -> cat
            
            # Comparatives/Superlatives
            ('iest', 'y'),     # happiest -> happy
            ('ier', 'y'),      # happier -> happy
            ('est', ''),       # fastest -> fast
            ('er', ''),        # faster -> fast
            
            # Adverbs and derivations
            ('ly', ''),        # quickly -> quick
            ('ness', ''),      # happiness -> happy
            ('ment', ''),      # management -> manage
            ('ful', ''),       # beautiful -> beauty
            ('less', ''),      # helpless -> help
        ]
        
        for suffix, replacement in rules:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                base = word[:-len(suffix)] + replacement
                # Check if it's a valid reduction
                if len(base) >= 3:
                    return base
                    
        return original
        
    def frequency_based_clustering(self) -> Set[str]:
        """Cluster words based on common patterns and frequency."""
        clusters = defaultdict(set)
        
        # Group words by their first 3-4 characters
        for word in self.words:
            if len(word) >= 4:
                prefix = word[:4]
                clusters[prefix].add(word)
            elif len(word) == 3:
                prefix = word
                clusters[prefix].add(word)
                
        # Identify base forms within clusters
        base_forms = set()
        
        for prefix, word_set in clusters.items():
            if len(word_set) > 1:
                # Find the shortest word as potential base
                shortest = min(word_set, key=len)
                base_forms.add(shortest)
                
                # Also check for common patterns
                for word in word_set:
                    base = self.apply_linguistic_rules(word)
                    if base in word_set:
                        base_forms.add(base)
            else:
                base_forms.update(word_set)
                
        return base_forms
        
    def generate_optimization_plan(self) -> None:
        """Generate a comprehensive optimization plan."""
        print("\n" + "="*80)
        print("CORPUS OPTIMIZATION STRATEGY FOR FLORIDIFY")
        print("="*80)
        
        print("\n1. CURRENT STATE ANALYSIS")
        print("-" * 40)
        print(f"Total words in SOWPODS: {len(self.words):,}")
        print(f"Target corpus size: ~55,000 base forms")
        print(f"Required reduction: ~{((len(self.words) - 55000) / len(self.words) * 100):.1f}%")
        
        # Analyze patterns
        patterns = self.analyze_inflection_patterns()
        print("\n2. INFLECTION PATTERN ANALYSIS")
        print("-" * 40)
        total_inflected = sum(patterns.values())
        print(f"Total potentially inflected forms: {total_inflected:,} ({total_inflected/len(self.words)*100:.1f}%)")
        print("\nTop inflection patterns:")
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {pattern}: {count:,} words ({count/len(self.words)*100:.1f}%)")
            
        # Estimate base forms
        estimates = self.estimate_base_forms()
        print("\n3. BASE FORM ESTIMATION")
        print("-" * 40)
        for method, results in estimates.items():
            print(f"\n{method.replace('_', ' ').title()}:")
            print(f"  Estimated base forms: {results['base_forms']:,}")
            print(f"  Reduction: {results['reduction_pct']:.1f}%")
            if 'sample_mappings' in results:
                print("  Sample mappings:")
                for base, inflections in list(results['sample_mappings'].items())[:5]:
                    forms = [f"{word} ({suffix})" for word, suffix in inflections[:3]]
                    print(f"    {base} -> {', '.join(forms)}")
                    
        print("\n4. RECOMMENDED IMPLEMENTATION STRATEGY")
        print("-" * 40)
        print("""
Phase 1: Infrastructure Setup (Week 1)
  - Create CorpusOptimizer class in search/lexicon/optimizer.py
  - Implement inflection mapping database (MongoDB collection)
  - Add configuration for optimization parameters
  
Phase 2: Lemmatization Pipeline (Week 2)
  - Integrate existing TextProcessor with lemmatization
  - Build comprehensive irregular forms database
  - Create validation test suite
  
Phase 3: Mapping Generation (Week 3)
  - Process full SOWPODS corpus
  - Generate inflection -> base form mappings
  - Create reverse lookup index
  - Validate against frequency lists
  
Phase 4: Search Integration (Week 4)
  - Update SearchEngine to use base forms
  - Implement query expansion (search -> searches, searching)
  - Add fallback to original corpus for edge cases
  
Phase 5: Performance Optimization (Week 5)
  - Benchmark search performance
  - Optimize data structures
  - Implement caching strategies
  - A/B test search quality

5. TECHNICAL IMPLEMENTATION DETAILS
""")
        print("-" * 40)
        print("""
a) Data Structure:
   ```python
   class OptimizedLexicon:
       base_forms: Set[str]              # ~55k entries
       inflection_map: Dict[str, str]    # inflected -> base
       reverse_map: Dict[str, List[str]] # base -> inflections
       frequency_scores: Dict[str, int]  # word frequency data
   ```

b) Search Algorithm:
   1. Normalize query
   2. Check if query is base form
   3. If not, lookup in inflection_map
   4. Expand to all inflections for fuzzy matching
   5. Apply existing search methods

c) Storage Optimization:
   - Use bloom filters for quick existence checks
   - Compress inflection mappings with prefix trees
   - Cache frequently searched terms
   - Lazy load full inflection data

6. EXPECTED BENEFITS
""")
        print("-" * 40)
        print("""
- Memory usage: 40-50% reduction
- Search speed: 2-3x improvement
- Index size: 60% smaller
- Better search recall (finding inflected forms)
- Simplified fuzzy matching
- Improved semantic search accuracy

7. QUALITY ASSURANCE
""")
        print("-" * 40)
        print("""
- Create test corpus with known inflections
- Validate all mappings preserve searchability  
- Check edge cases (compound words, hyphenations)
- Benchmark against current search quality
- User acceptance testing
- Maintain override list for exceptions

8. RECOMMENDED LIBRARIES
""")
        print("-" * 40)
        print("""
Primary: NLTK (already integrated)
  - WordNet lemmatizer for accuracy
  - POS tagging for context
  - Comprehensive English coverage
  
Secondary: spaCy (for batch processing)
  - Faster for large-scale processing
  - Good accuracy for common words
  - Pipeline optimization
  
Supplementary:
  - python-Levenshtein: Fast fuzzy matching
  - pybloom-live: Bloom filters
  - marisa-trie: Compressed prefix trees
""")


async def main():
    """Run the corpus optimization analysis."""
    strategy = CorpusOptimizationStrategy()
    strategy.load_corpus()
    strategy.generate_optimization_plan()
    

if __name__ == "__main__":
    asyncio.run(main())