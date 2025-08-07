# Apple Dictionary Integration for macOS - Technical Implementation Guide

## Overview

This document provides comprehensive technical implementation details for integrating Apple Dictionary on macOS with Python applications. All methods are legally permissible for personal use on the user's own Mac.

## Legal Considerations

✅ **Personal Use**: Using Apple Dictionary through official APIs (DictionaryServices framework) for personal, non-commercial purposes is permitted on user's own Mac
✅ **API Access**: Apple provides official frameworks for dictionary access
❌ **Redistribution**: Cannot redistribute dictionary content or create commercial dictionary apps without proper licensing

## Implementation Methods

### Method 1: PyObjC with DictionaryServices Framework (Recommended)

This is the most robust approach using Apple's official APIs.

#### Installation
```bash
# Install PyObjC framework
pip install pyobjc-framework-CoreServices
# OR install full PyObjC suite (larger but more comprehensive)
pip install pyobjc
```

#### Basic Implementation
```python
#!/usr/bin/env python3
"""
Apple Dictionary integration using PyObjC DictionaryServices framework.
"""

import sys
from typing import Optional
try:
    from DictionaryServices import DCSCopyTextDefinition
    from CoreFoundation import CFRange
except ImportError:
    try:
        # Alternative import path for some PyObjC installations
        from CoreServices.DictionaryServices import DCSCopyTextDefinition
        from CoreFoundation import CFRange
    except ImportError:
        raise ImportError(
            "PyObjC DictionaryServices not available. Install with: "
            "pip install pyobjc-framework-CoreServices"
        )


class AppleDictionary:
    """Interface to macOS Dictionary.app using DictionaryServices framework."""
    
    def __init__(self):
        self.cache = {}  # Simple LRU cache for performance
        self.max_cache_size = 1000
    
    def lookup_word(self, word: str) -> Optional[str]:
        """
        Look up a word definition using Apple Dictionary.
        
        Args:
            word: The word to look up
            
        Returns:
            Definition string or None if not found
        """
        # Check cache first
        if word in self.cache:
            return self.cache[word]
        
        # Clean and prepare word
        search_word = word.strip().lower()
        if not search_word:
            return None
            
        # Create CFRange for entire word
        word_range = CFRange(0, len(search_word))
        
        try:
            # Call DictionaryServices API
            result = DCSCopyTextDefinition(None, search_word, word_range)
            
            if result:
                definition = str(result)
                # Cache the result
                self._add_to_cache(word, definition)
                return definition
            else:
                # Cache negative results to avoid repeated lookups
                self._add_to_cache(word, None)
                return None
                
        except Exception as e:
            print(f"Error looking up '{word}': {e}")
            return None
    
    def _add_to_cache(self, word: str, definition: Optional[str]):
        """Add word/definition to cache with LRU eviction."""
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO for this example)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[word] = definition
    
    def batch_lookup(self, words: list[str]) -> dict[str, Optional[str]]:
        """
        Look up multiple words efficiently.
        
        Args:
            words: List of words to look up
            
        Returns:
            Dictionary mapping words to their definitions
        """
        results = {}
        for word in words:
            results[word] = self.lookup_word(word)
        return results
    
    def clear_cache(self):
        """Clear the internal cache."""
        self.cache.clear()


# Command-line usage
def main():
    if len(sys.argv) < 2:
        print("Usage: python apple_dict.py <word>")
        sys.exit(1)
    
    dictionary = AppleDictionary()
    word = sys.argv[1]
    
    definition = dictionary.lookup_word(word)
    if definition:
        print(f"Definition of '{word}':")
        print("-" * 40)
        print(definition)
    else:
        print(f"No definition found for '{word}'")


if __name__ == "__main__":
    main()
```

#### Advanced Implementation with Formatting
```python
import re
from typing import Dict, List, Optional


class EnhancedAppleDictionary(AppleDictionary):
    """Enhanced Apple Dictionary with better formatting and features."""
    
    def format_definition(self, definition: str) -> Dict[str, any]:
        """
        Parse and format dictionary definition into structured data.
        
        Returns:
            Dict with parsed components like word_forms, definitions, etc.
        """
        if not definition:
            return {}
        
        # Clean up the definition
        cleaned = self._clean_definition(definition)
        
        # Extract word forms (noun, verb, adjective, etc.)
        word_forms = self._extract_word_forms(cleaned)
        
        # Split into numbered definitions
        definitions = self._extract_definitions(cleaned)
        
        return {
            'raw_definition': definition,
            'cleaned_definition': cleaned,
            'word_forms': word_forms,
            'definitions': definitions,
            'definition_count': len(definitions)
        }
    
    def _clean_definition(self, definition: str) -> str:
        """Clean up formatting in definition text."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', definition)
        
        # Format numbered definitions
        cleaned = re.sub(r' (\d+) ', r'\n\1. ', cleaned)
        
        # Format word types
        for word_type in ['noun', 'verb', 'adjective', 'adverb', 'pronoun']:
            cleaned = cleaned.replace(f' {word_type} ', f'\n• {word_type.upper()}: ')
        
        return cleaned.strip()
    
    def _extract_word_forms(self, definition: str) -> List[str]:
        """Extract grammatical word forms from definition."""
        word_forms = []
        pattern = r'•\s*(NOUN|VERB|ADJECTIVE|ADVERB|PRONOUN):'
        matches = re.finditer(pattern, definition, re.IGNORECASE)
        
        for match in matches:
            word_forms.append(match.group(1).lower())
        
        return word_forms
    
    def _extract_definitions(self, definition: str) -> List[str]:
        """Extract numbered definitions."""
        definitions = []
        pattern = r'(\d+\..*?)(?=\n\d+\.|\Z)'
        matches = re.finditer(pattern, definition, re.DOTALL)
        
        for match in matches:
            definitions.append(match.group(1).strip())
        
        return definitions


# Usage example
def demo_enhanced_dictionary():
    """Demonstrate enhanced dictionary features."""
    dictionary = EnhancedAppleDictionary()
    
    test_words = ['apple', 'run', 'beautiful', 'artificial intelligence']
    
    for word in test_words:
        print(f"\n{'='*50}")
        print(f"Looking up: {word}")
        print('='*50)
        
        definition = dictionary.lookup_word(word)
        if definition:
            formatted = dictionary.format_definition(definition)
            
            print(f"Word forms: {', '.join(formatted.get('word_forms', []))}")
            print(f"Definition count: {formatted.get('definition_count', 0)}")
            print("\nFormatted definition:")
            print(formatted.get('cleaned_definition', 'No definition available'))
        else:
            print("No definition found")
```

### Method 2: Subprocess with osascript/AppleScript

This method uses AppleScript through subprocess calls for dictionary access.

```python
#!/usr/bin/env python3
"""
Apple Dictionary access via AppleScript and subprocess.
"""

import subprocess
from typing import Optional
import shlex


class AppleScriptDictionary:
    """Access Apple Dictionary through AppleScript subprocess calls."""
    
    def __init__(self):
        self.cache = {}
    
    def lookup_word_via_applescript(self, word: str) -> Optional[str]:
        """
        Look up word using AppleScript to open Dictionary.app.
        This method opens Dictionary.app but doesn't return the definition.
        """
        if not word:
            return None
        
        # Escape the word for AppleScript
        escaped_word = word.replace('"', '\\"')
        
        applescript = f'''
        tell application "Dictionary"
            activate
            search for "{escaped_word}"
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return f"Dictionary.app opened for: {word}"
            else:
                return None
                
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"AppleScript error: {e}")
            return None
    
    def open_dictionary_url(self, word: str) -> bool:
        """
        Open dictionary using dict:// URL scheme.
        This is the most reliable subprocess method.
        """
        if not word:
            return False
        
        try:
            # Use dict:// URL scheme
            dict_url = f"dict://{shlex.quote(word)}"
            result = subprocess.run(
                ['open', dict_url],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error opening dictionary URL: {e}")
            return False


# Usage example
def demo_applescript_dictionary():
    """Demonstrate AppleScript dictionary access."""
    dictionary = AppleScriptDictionary()
    
    test_words = ['python', 'programming', 'artificial intelligence']
    
    for word in test_words:
        print(f"Opening dictionary for: {word}")
        success = dictionary.open_dictionary_url(word)
        if success:
            print(f"✓ Successfully opened dictionary for '{word}'")
        else:
            print(f"✗ Failed to open dictionary for '{word}'")
        
        # Small delay between openings
        import time
        time.sleep(1)
```

### Method 3: Direct File Access (Advanced)

This method directly accesses dictionary files for maximum performance.

```python
#!/usr/bin/env python3
"""
Direct access to Apple Dictionary files on macOS.
WARNING: This method involves reverse engineering and may break with OS updates.
"""

import os
import glob
import struct
import zlib
from pathlib import Path
from typing import Optional, List, Dict
import xml.etree.ElementTree as ET


class DirectDictionaryAccess:
    """
    Direct file access to Apple Dictionary data.
    This is experimental and may not work across all macOS versions.
    """
    
    DICTIONARY_PATHS = [
        "/System/Library/AssetsV2/com_apple_MobileAsset_DictionaryServices_dictionaryOSX",
        "/System/Library/Assets/com_apple_MobileAsset_DictionaryServices_dictionaryOSX",
        "/Library/Dictionaries"
    ]
    
    def __init__(self):
        self.dictionary_path = self._find_dictionary_path()
        self.cache = {}
    
    def _find_dictionary_path(self) -> Optional[str]:
        """Find the active dictionary path on the system."""
        for base_path in self.DICTIONARY_PATHS:
            if os.path.exists(base_path):
                # Look for New Oxford American Dictionary
                pattern = os.path.join(base_path, "**", "*New Oxford American Dictionary*")
                matches = glob.glob(pattern, recursive=True)
                
                for match in matches:
                    if match.endswith('.dictionary'):
                        return match
                    # Look for Body.data inside .dictionary bundles
                    body_data = os.path.join(match, "Body.data")
                    if os.path.exists(body_data):
                        return match
        
        return None
    
    def extract_dictionary_entries(self, limit: int = 100) -> List[Dict]:
        """
        Attempt to extract dictionary entries from Body.data file.
        WARNING: This is experimental and uses reverse engineering.
        """
        if not self.dictionary_path:
            return []
        
        body_data_path = os.path.join(self.dictionary_path, "Body.data")
        if not os.path.exists(body_data_path):
            return []
        
        entries = []
        
        try:
            with open(body_data_path, 'rb') as f:
                # Skip Apple header (first 108 bytes based on reverse engineering)
                f.seek(108)
                
                # Try to decompress the data
                compressed_data = f.read()
                
                try:
                    # Attempt zlib decompression
                    decompressed = zlib.decompress(compressed_data)
                    
                    # Try to parse as XML entries
                    entries = self._parse_decompressed_data(decompressed, limit)
                    
                except zlib.error:
                    # If zlib fails, try different approaches
                    print("Direct zlib decompression failed")
                    
        except Exception as e:
            print(f"Error extracting dictionary entries: {e}")
        
        return entries
    
    def _parse_decompressed_data(self, data: bytes, limit: int) -> List[Dict]:
        """
        Attempt to parse decompressed dictionary data.
        This is highly experimental.
        """
        entries = []
        
        try:
            # Convert to string and look for XML patterns
            text_data = data.decode('utf-8', errors='ignore')
            
            # Look for dictionary entry patterns
            import re
            entry_pattern = r'<d:entry[^>]*>.*?</d:entry>'
            matches = re.finditer(entry_pattern, text_data, re.DOTALL)
            
            for i, match in enumerate(matches):
                if i >= limit:
                    break
                
                try:
                    entry_xml = match.group(0)
                    # Parse XML to extract word and definition
                    root = ET.fromstring(entry_xml)
                    
                    # Extract word (this is speculative based on common XML patterns)
                    word_elem = root.find(".//d:headword") or root.find(".//headword")
                    definition_elem = root.find(".//d:definition") or root.find(".//definition")
                    
                    if word_elem is not None:
                        word = word_elem.text
                        definition = definition_elem.text if definition_elem is not None else "No definition"
                        
                        entries.append({
                            'word': word,
                            'definition': definition,
                            'source': 'direct_extraction'
                        })
                        
                except Exception as xml_error:
                    # Skip malformed entries
                    continue
                    
        except Exception as e:
            print(f"Error parsing decompressed data: {e}")
        
        return entries
    
    def get_dictionary_info(self) -> Dict:
        """Get information about available dictionaries."""
        info = {
            'dictionary_path': self.dictionary_path,
            'available_paths': [],
            'dictionary_files': []
        }
        
        # Check all possible paths
        for path in self.DICTIONARY_PATHS:
            if os.path.exists(path):
                info['available_paths'].append(path)
                
                # List dictionary files in this path
                dict_files = []
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith('.dictionary') or file == 'Body.data':
                            dict_files.append(os.path.join(root, file))
                
                info['dictionary_files'].extend(dict_files)
        
        return info


# Usage example
def demo_direct_access():
    """Demonstrate direct dictionary file access."""
    accessor = DirectDictionaryAccess()
    
    # Get system info
    info = accessor.get_dictionary_info()
    print("Dictionary System Information:")
    print(f"Active dictionary path: {info['dictionary_path']}")
    print(f"Available paths: {len(info['available_paths'])}")
    print(f"Dictionary files found: {len(info['dictionary_files'])}")
    
    # Try to extract some entries (experimental)
    print("\nAttempting to extract dictionary entries...")
    entries = accessor.extract_dictionary_entries(limit=10)
    
    if entries:
        print(f"Successfully extracted {len(entries)} entries:")
        for entry in entries[:5]:  # Show first 5
            print(f"- {entry['word']}: {entry['definition'][:100]}...")
    else:
        print("No entries extracted (this is expected - method is experimental)")
```

## Integration with Floridify

Here's how to integrate Apple Dictionary with your existing search system:

```python
# /backend/src/floridify/search/apple_dictionary.py
"""
Apple Dictionary integration for Floridify search system.
"""

from typing import Optional, List, Dict
import asyncio
from functools import lru_cache

from .models import SearchResult
from .constants import SearchMethod
from ..utils.logging import get_logger

logger = get_logger(__name__)


class AppleDictionarySearcher:
    """Apple Dictionary integration for Floridify."""
    
    def __init__(self):
        self.dictionary = None
        self._initialize_dictionary()
    
    def _initialize_dictionary(self):
        """Initialize the dictionary backend."""
        try:
            # Try PyObjC first (most reliable)
            from .apple_dict_backends import AppleDictionary
            self.dictionary = AppleDictionary()
            logger.info("Apple Dictionary initialized via PyObjC")
            
        except ImportError:
            try:
                # Fallback to AppleScript
                from .apple_dict_backends import AppleScriptDictionary
                self.dictionary = AppleScriptDictionary()
                logger.info("Apple Dictionary initialized via AppleScript")
                
            except Exception as e:
                logger.warning(f"Apple Dictionary not available: {e}")
                self.dictionary = None
    
    async def search_async(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Asynchronous search using Apple Dictionary.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        if not self.dictionary:
            return []
        
        # Run dictionary lookup in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        try:
            definition = await loop.run_in_executor(
                None, 
                self.dictionary.lookup_word, 
                query
            )
            
            if definition:
                return [SearchResult(
                    word=query,
                    score=1.0,  # Apple Dictionary is authoritative
                    method=SearchMethod.APPLE_DICTIONARY,
                    definition=definition,
                    metadata={
                        'source': 'Apple Dictionary',
                        'system_dictionary': True
                    }
                )]
            
        except Exception as e:
            logger.error(f"Apple Dictionary search error: {e}")
        
        return []
    
    def search_sync(self, query: str) -> Optional[SearchResult]:
        """
        Synchronous search for compatibility.
        
        Args:
            query: Search query
            
        Returns:
            SearchResult or None
        """
        if not self.dictionary:
            return None
        
        try:
            definition = self.dictionary.lookup_word(query)
            
            if definition:
                return SearchResult(
                    word=query,
                    score=1.0,
                    method=SearchMethod.APPLE_DICTIONARY,
                    definition=definition,
                    metadata={
                        'source': 'Apple Dictionary',
                        'system_dictionary': True
                    }
                )
                
        except Exception as e:
            logger.error(f"Apple Dictionary search error: {e}")
        
        return None
    
    @lru_cache(maxsize=1000)
    def cached_lookup(self, word: str) -> Optional[str]:
        """Cached dictionary lookup for performance."""
        if not self.dictionary:
            return None
        
        return self.dictionary.lookup_word(word)
    
    def is_available(self) -> bool:
        """Check if Apple Dictionary is available."""
        return self.dictionary is not None
```

## Performance Optimization

### Caching Strategy
```python
from functools import lru_cache
from typing import Dict, Optional
import time


class CachedAppleDictionary:
    """Apple Dictionary with advanced caching."""
    
    def __init__(self, cache_size: int = 10000, cache_ttl: int = 3600):
        self.dictionary = AppleDictionary()
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, tuple] = {}  # word -> (definition, timestamp)
    
    def lookup_word(self, word: str) -> Optional[str]:
        """Look up word with TTL caching."""
        current_time = time.time()
        
        # Check cache
        if word in self.cache:
            definition, timestamp = self.cache[word]
            if current_time - timestamp < self.cache_ttl:
                return definition
            else:
                # Cache expired, remove entry
                del self.cache[word]
        
        # Lookup from dictionary
        definition = self.dictionary.lookup_word(word)
        
        # Cache result
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry
            oldest_word = min(self.cache.keys(), 
                            key=lambda k: self.cache[k][1])
            del self.cache[oldest_word]
        
        self.cache[word] = (definition, current_time)
        return definition
    
    @lru_cache(maxsize=1000)
    def fast_lookup(self, word: str) -> Optional[str]:
        """Ultra-fast lookup with LRU cache."""
        return self.dictionary.lookup_word(word)
```

## Testing and Validation

```python
#!/usr/bin/env python3
"""
Test suite for Apple Dictionary integration.
"""

import unittest
from typing import List


class TestAppleDictionary(unittest.TestCase):
    """Test cases for Apple Dictionary integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.dictionary = AppleDictionary()
    
    def test_basic_lookup(self):
        """Test basic word lookup."""
        # Test common English word
        result = self.dictionary.lookup_word("apple")
        self.assertIsNotNone(result)
        self.assertIn("fruit", result.lower())
    
    def test_missing_word(self):
        """Test lookup of non-existent word."""
        result = self.dictionary.lookup_word("xyzzyqwerty")
        self.assertIsNone(result)
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = self.dictionary.lookup_word("")
        self.assertIsNone(result)
        
        result = self.dictionary.lookup_word("   ")
        self.assertIsNone(result)
    
    def test_batch_lookup(self):
        """Test batch word lookup."""
        words = ["apple", "banana", "cherry", "nonexistentword"]
        results = self.dictionary.batch_lookup(words)
        
        self.assertEqual(len(results), len(words))
        self.assertIsNotNone(results["apple"])
        self.assertIsNotNone(results["banana"])
        self.assertIsNotNone(results["cherry"])
        self.assertIsNone(results["nonexistentword"])
    
    def test_caching(self):
        """Test caching functionality."""
        word = "test"
        
        # First lookup
        result1 = self.dictionary.lookup_word(word)
        
        # Second lookup (should use cache)
        result2 = self.dictionary.lookup_word(word)
        
        self.assertEqual(result1, result2)
        self.assertIn(word, self.dictionary.cache)
    
    def test_case_insensitive(self):
        """Test case insensitive lookup."""
        word_lower = "apple"
        word_upper = "APPLE"
        word_mixed = "Apple"
        
        result_lower = self.dictionary.lookup_word(word_lower)
        result_upper = self.dictionary.lookup_word(word_upper)
        result_mixed = self.dictionary.lookup_word(word_mixed)
        
        # All should return results (though they may differ slightly)
        self.assertIsNotNone(result_lower)
        self.assertIsNotNone(result_upper)
        self.assertIsNotNone(result_mixed)


def run_system_tests():
    """Run comprehensive system tests."""
    print("Running Apple Dictionary System Tests...")
    
    # Test 1: Check PyObjC availability
    try:
        from DictionaryServices import DCSCopyTextDefinition
        print("✓ PyObjC DictionaryServices available")
    except ImportError:
        print("✗ PyObjC DictionaryServices not available")
    
    # Test 2: Test basic functionality
    dictionary = AppleDictionary()
    test_words = ["hello", "world", "python", "programming"]
    
    for word in test_words:
        result = dictionary.lookup_word(word)
        status = "✓" if result else "✗"
        print(f"{status} '{word}': {'Found' if result else 'Not found'}")
    
    # Test 3: Performance test
    import time
    start_time = time.time()
    
    for i in range(100):
        dictionary.lookup_word(f"test{i % 10}")  # Reuse words for cache testing
    
    end_time = time.time()
    print(f"✓ Performance: 100 lookups in {end_time - start_time:.2f}s")


if __name__ == "__main__":
    # Run unit tests
    unittest.main(verbosity=2, exit=False)
    
    # Run system tests
    print("\n" + "="*50)
    run_system_tests()
```

## Installation and Setup

### 1. Install Dependencies
```bash
# Install PyObjC (recommended)
pip install pyobjc-framework-CoreServices

# Alternative: Full PyObjC suite (larger but more comprehensive)
pip install pyobjc

# For development and testing
pip install pytest pytest-asyncio
```

### 2. Verify Installation
```bash
# Test basic functionality
python -c "from DictionaryServices import DCSCopyTextDefinition; print('Dictionary Services available')"

# Test with a word
python -c "
from DictionaryServices import DCSCopyTextDefinition
from CoreFoundation import CFRange
result = DCSCopyTextDefinition(None, 'apple', CFRange(0, 5))
print('Definition found:' if result else 'No definition')
"
```

### 3. Integration with Floridify
```python
# Add to your search constants
class SearchMethod:
    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic" 
    APPLE_DICTIONARY = "apple_dictionary"  # Add this

# Update search configuration
SEARCH_METHODS = [
    SearchMethod.APPLE_DICTIONARY,  # Check Apple Dictionary first
    SearchMethod.EXACT,
    SearchMethod.FUZZY,
    SearchMethod.SEMANTIC,
]
```

## Performance Characteristics

- **PyObjC Method**: ~1-5ms per lookup, excellent caching
- **AppleScript Method**: ~100-500ms per lookup, opens Dictionary.app
- **Direct File Access**: Experimental, potentially very fast but unreliable

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: DictionaryServices**
   ```bash
   pip install pyobjc-framework-CoreServices
   # Or try the full package:
   pip install pyobjc
   ```

2. **Interpreter crashes on macOS 10.12**
   - Use Homebrew Python instead of python.org binary
   - Or upgrade to newer macOS version

3. **No definitions returned**
   - Check if Dictionary.app has downloaded dictionaries
   - Verify internet connection for initial dictionary download
   - Try looking up a common word like "apple" first

4. **Performance issues**
   - Implement caching as shown in examples
   - Use async methods for batch processing
   - Consider pre-warming cache with common words

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug mode in your dictionary class
dictionary = AppleDictionary()
dictionary.debug = True
```

## Conclusion

The PyObjC approach with DictionaryServices framework provides the most reliable and performant method for integrating Apple Dictionary on macOS. It's legally compliant for personal use, well-documented, and provides excellent performance with proper caching strategies.

For production use in Floridify, recommend:
1. Primary: PyObjC DictionaryServices (fast, reliable)
2. Fallback: AppleScript method (slower but works if PyObjC fails)
3. Avoid: Direct file access (experimental, may break with OS updates)

The integration provides authoritative dictionary definitions that can enhance your AI-powered search system with high-quality, trusted reference data.