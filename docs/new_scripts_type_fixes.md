# Type Fixes for New Scripts - Quick Reference

## 1. process_corpus.py

### Missing Dependencies
```bash
# Already in requirements - just needs proper imports
```

### Critical Fixes
```python
# Line 1-3: Add imports
from typing import Any, Optional
from collections import defaultdict, Counter

# Line 37: Fix class attribute types
def __init__(self):
    self.stats: dict[str, Any] = {
        "total_words": 0,
        "base_forms": 0,
        "inflections": 0,
        "reduction_percentage": 0.0,
        "inflection_types": defaultdict(int)
    }

# Line 57-63: Fix wordnet returns
def get_wordnet_pos(self, nltk_pos: str) -> str:
    """Convert NLTK POS to WordNet POS."""
    if nltk_pos.startswith('V'):
        return str(wordnet.VERB)
    # ... etc

# Line 101: Add return type
async def process_corpus(self) -> None:
    """Process the corpus and identify inflections."""

# Line 141: Add return type
def save_results(self) -> None:
    """Save results to JSON file."""

# Line 163: Add return type  
def display_statistics(self) -> None:
    """Display processing statistics."""

# Line 203: Add return type
async def main() -> None:
    """Main entry point."""
```

## 2. batch_synthesis_enhanced.py

### Missing Dependencies
```toml
# Add to pyproject.toml if not present:
# Already has required deps
```

### Critical Fixes
```python
# Line 27: Fix OpenAIConnector initialization
from floridify.utils.config import load_config
config = load_config()
ai_connector = AIConnector(api_key=config.openai_api_key)

# Line 34: Fix SearchEngine initialization
search_engine = SearchEngine()
# Remove: languages=["en"], enable_semantic=False

# Line 35: Remove non-existent method
# DELETE: await search_engine.initialize()

# Line 96, 141, 194, etc: Fix MongoDB close
# REPLACE ALL: await mongodb.close()
# WITH: await mongodb.client.close()

# Or better - use context manager:
async with get_mongodb() as mongodb:
    # ... use mongodb
    # auto-closes
```

## 3. frequency_analyzer.py

### Missing Dependencies
```bash
# Add to backend environment:
uv add aiohttp
```

### Critical Fixes
```python
# Line 18: After adding aiohttp to deps, this import will work

# Line 230: Type annotation for defaultdict
frequencies: defaultdict[str, int] = defaultdict(int)

# Line 267: Type annotation
combined: defaultdict[str, float] = defaultdict(float)

# Line 302: Add return type
async def analyze(
    self, 
    custom_weights: Optional[Dict[str, float]] = None
) -> tuple[dict[str, float], dict[str, int]]:
    """Analyze word frequencies."""

# Line 376: Add return type
def display_statistics(
    self, 
    frequencies: Dict[str, float], 
    word_list: List[str]
) -> None:
    """Display analysis statistics."""

# Line 395: Type annotation
all_words: set[str] = set()

# Line 418: Add return type
def integrate_with_corpus_processor(
    self, 
    corpus_processor_output: Path
) -> dict[str, Any]:
    """Integrate with corpus processor results."""

# Line 441: Add return type
async def main() -> None:
    """Main entry point."""
```

## Quick Fix Script

Run this to fix the most common issues:

```bash
#!/bin/bash
cd /Users/mkbabb/Programming/words/backend

# Fix any -> Any
find scripts -name "*.py" -exec sed -i '' 's/-> Dict\[str, any\]/-> Dict[str, Any]/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/-> dict\[str, any\]/-> dict[str, Any]/g' {} \;

# Fix missing return types for common patterns
find scripts -name "*.py" -exec sed -i '' 's/async def main():/async def main() -> None:/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/def __init__(self):/def __init__(self) -> None:/g' {} \;

# Update deprecated imports (Python 3.12+)
find scripts -name "*.py" -exec sed -i '' 's/from typing import Dict$/from typing import Any/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/: Dict\[/: dict[/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/: List\[/: list[/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/: Set\[/: set[/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/: Tuple\[/: tuple[/g' {} \;
```

## Validation Commands

After fixes, validate each script:

```bash
# Check individual files
mypy scripts/process_corpus.py --show-error-codes
mypy scripts/batch_synthesis_enhanced.py --show-error-codes  
mypy scripts/frequency_analyzer.py --show-error-codes

# Check with ruff
ruff check scripts/process_corpus.py --select ANN,TYP
ruff check scripts/batch_synthesis_enhanced.py --select ANN,TYP
ruff check scripts/frequency_analyzer.py --select ANN,TYP
```