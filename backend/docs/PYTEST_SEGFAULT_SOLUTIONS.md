# Pytest Segmentation Fault Solutions - sentence-transformers + trust_remote_code on Apple Silicon

**Date**: January 2025
**Environment**: Python 3.12+, PyTorch 2.8.0, sentence-transformers 5.1.0, pytest-asyncio, Apple Silicon (M1/M2/M3/M4)
**Model**: GTE-Qwen2-1.5B-instruct (requires `trust_remote_code=True`)
**Issue**: Segmentation faults only during pytest execution with async tests, standalone scripts work fine

---

## Root Causes

### 1. **PyTorch Fork Safety on macOS**
- **Problem**: macOS uses `fork()` by default for multiprocessing in Python < 3.8, but macOS system libraries (especially Metal/MPS) start threads that become corrupted after fork
- **Impact**: PyTorch models with MPS backend crash when forked during pytest subprocess creation
- **Apple Silicon Specific**: M1/M2/M3/M4 chips use MPS (Metal Performance Shaders) backend which is NOT fork-safe

### 2. **pytest-asyncio + multiprocessing Interaction**
- **Problem**: pytest-asyncio may spawn subprocesses using fork mode, inheriting corrupted PyTorch/MPS state
- **Impact**: Model loading in fixtures or test setup causes segfaults when subprocess tries to use inherited MPS context

### 3. **trust_remote_code Models**
- **Problem**: Models requiring `trust_remote_code=True` (like GTE-Qwen2) load custom code that may initialize additional threads/resources
- **Impact**: More complex initialization means more state to corrupt during fork

### 4. **PyTorch 2.8.0 on Apple Silicon**
- **Recent Issue**: PyTorch 2.8.0 has known issues with MPS backend stability on Apple M4 chips (and potentially M1/M2/M3)
- **Crash Location**: `libomp.dylib` crashes during LayerNorm operations
- **Scope**: Affects both CPU and MPS execution modes

---

## Solution 1: Force CPU Mode (Recommended for Testing)

### Implementation

**Option A: Environment Variables (Global)**
```python
# tests/conftest.py
import os

# Set BEFORE any torch imports
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Enable fallback
os.environ["PYTORCH_MPS_FORCE_CPU"] = "1"  # Force CPU mode
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Disable tokenizer parallelism
os.environ["OMP_NUM_THREADS"] = "1"  # Single-threaded OpenMP
os.environ["MKL_NUM_THREADS"] = "1"  # Single-threaded MKL
```

**Option B: Device Override in conftest.py**
```python
# tests/conftest.py
import pytest
import torch

@pytest.fixture(scope="session", autouse=True)
def force_cpu_mode():
    """Force CPU mode for all tests to avoid MPS segfaults."""
    # Disable MPS
    if hasattr(torch.backends, "mps"):
        torch.backends.mps.is_available = lambda: False
        torch.backends.mps.is_built = lambda: False

    # Set default device to CPU
    torch.set_default_device("cpu")

    yield

    # Cleanup if needed
    torch.set_default_device("cpu")
```

**Option C: Model-Specific Device Override**
```python
# src/floridify/search/semantic/core.py
async def get_cached_model(
    model_name: str,
    device: str = "cpu",
    use_onnx: bool = False,
) -> Any:
    """Get or create cached sentence transformer model."""

    # ALWAYS use CPU in test environment to avoid MPS segfaults
    if "pytest" in sys.modules:
        device = "cpu"
        logger.warning("Test environment detected - forcing CPU mode")

    # ... rest of implementation
```

### Why This Works
- CPU mode avoids ALL MPS-related threading and fork safety issues
- Single-threaded execution prevents race conditions
- Trade-off: Tests run slower but are stable and reliable

---

## Solution 2: Multiprocessing Start Method (macOS Compatibility)

### Implementation

**Option A: Global Configuration (Recommended)**
```python
# tests/conftest.py
import multiprocessing as mp
import sys

def pytest_configure(config):
    """Configure pytest for macOS fork safety."""
    if sys.platform == "darwin":  # macOS only
        try:
            # Set to 'spawn' before any multiprocessing
            mp.set_start_method('spawn', force=True)
        except RuntimeError:
            # Already set, ignore
            pass
```

**Option B: Per-Test Configuration**
```python
# tests/search/test_semantic_search.py
import pytest
import multiprocessing as mp
import sys

@pytest.fixture(scope="module", autouse=True)
def configure_multiprocessing():
    """Configure multiprocessing for macOS."""
    if sys.platform == "darwin":
        try:
            mp.set_start_method('spawn', force=True)
        except RuntimeError:
            pass
    yield
```

### Why This Works
- `spawn` creates fresh Python interpreter without inheriting corrupted state
- Slower but safer than `fork` on macOS
- Default on macOS Python 3.8+, but pytest may override

---

## Solution 3: Pytest Fixture Isolation

### Implementation

**Isolate Model Loading to Process Scope**
```python
# tests/conftest.py
import pytest
import multiprocessing as mp
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_model_in_subprocess(model_name: str):
    """Load model in isolated subprocess to avoid fork issues."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name, trust_remote_code=True, device="cpu")

@pytest.fixture(scope="session")
def semantic_model_session():
    """Session-scoped model fixture with subprocess isolation."""
    # Load in main process (safer with spawn mode)
    model = _load_model_in_subprocess("Alibaba-NLP/gte-Qwen2-1.5B-instruct")
    yield model
    # Cleanup
    del model
```

**Lazy Loading Pattern**
```python
# tests/search/conftest.py
@pytest_asyncio.fixture(scope="session")
async def semantic_model_lazy():
    """Lazy-load model only when first test needs it."""
    model = None

    def get_model():
        nonlocal model
        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",  # Smaller, faster model
                device="cpu",
                trust_remote_code=False,  # Avoid if possible
            )
        return model

    yield get_model

    # Cleanup
    if model is not None:
        del model
```

### Why This Works
- Defers model loading until after pytest subprocess creation
- Uses session scope to load once and reuse
- Smaller models reduce memory and initialization complexity

---

## Solution 4: Mock Model Loading for Unit Tests

### Implementation

**Mock SentenceTransformer**
```python
# tests/search/test_semantic_search.py
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

@pytest.fixture
def mock_sentence_model():
    """Mock sentence transformer to avoid loading real model."""
    mock_model = MagicMock()

    # Mock encode method
    def mock_encode(sentences, **kwargs):
        # Return realistic embeddings
        if isinstance(sentences, str):
            sentences = [sentences]
        return np.random.rand(len(sentences), 1536).astype(np.float32)

    mock_model.encode = mock_encode
    mock_model.device = "cpu"
    mock_model.max_seq_length = 512

    return mock_model

@pytest.fixture
def mock_get_cached_model(mock_sentence_model):
    """Mock model loading function."""
    with patch("floridify.search.semantic.core.get_cached_model") as mock:
        mock.return_value = mock_sentence_model
        yield mock

@pytest.mark.asyncio
async def test_semantic_search_with_mock(mock_get_cached_model):
    """Test semantic search with mocked model."""
    from floridify.search.semantic.core import SemanticSearch

    # Create engine - will use mocked model
    engine = await SemanticSearch.from_corpus(...)

    # Test logic without real model loading
    results = await engine.search("test query")
    assert results is not None
```

### Why This Works
- Completely avoids model loading and PyTorch initialization
- Tests business logic without ML dependencies
- Fast, reliable, no segfaults

---

## Solution 5: PyTorch Version Downgrade (Last Resort)

### Implementation

**Downgrade to Stable Version**
```toml
# pyproject.toml
[dependency-groups]
dev = [
    # ... other deps
    "torch==2.0.1",  # Known stable on Apple Silicon
    "sentence-transformers>=3.0.0,<4.0.0",  # Compatible version
]
```

**Or use version pinning:**
```bash
uv add --dev torch==2.0.1
uv add sentence-transformers==3.2.1
```

### Why This Works
- PyTorch 2.0.1 is known stable on M1/M2
- Avoids MPS backend issues in newer versions
- Trade-off: Miss out on performance improvements and new features

### Compatibility Matrix
| PyTorch | sentence-transformers | Apple Silicon Status |
|---------|----------------------|---------------------|
| 2.0.1   | 3.0.0-3.2.x         | ✅ Stable           |
| 2.1.1   | 3.0.0-3.2.x         | ⚠️ Mixed results    |
| 2.8.0   | 5.1.0               | ❌ Segfaults (M4)   |

---

## Solution 6: Pytest Configuration Optimizations

### Implementation

**pyproject.toml**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

# Add these for stability on macOS
addopts = [
    "-v",                                    # Verbose
    "--tb=short",                           # Short traceback
    "--strict-markers",                     # Strict marker validation
    "--disable-warnings",                   # Reduce noise
    "-p", "no:faulthandler",               # Disable pytest faulthandler
    "--forked",                             # Use pytest-forked for isolation (if installed)
]

# Markers for selective testing
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "semantic: marks tests requiring semantic models",
    "integration: marks integration tests",
]
```

**Selective Test Execution**
```bash
# Skip semantic tests on CI or local
pytest -m "not semantic"

# Run only fast unit tests
pytest -m "not slow and not semantic"

# Run with fork isolation (requires pytest-forked)
pytest --forked tests/search/test_semantic_search.py
```

### Why This Works
- Isolates tests using `pytest-forked` plugin
- Allows selective execution to skip problematic tests
- Better debugging with faulthandler control

---

## Solution 7: Alternative Test Model (Recommended)

### Implementation

**Use Simpler Model for Tests**
```python
# tests/search/conftest.py
import os
import pytest

# Override default model for tests
TEST_MODEL = os.getenv(
    "TEST_SEMANTIC_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"  # No trust_remote_code needed
)

@pytest.fixture(scope="session")
def test_semantic_model():
    """Provide test-friendly semantic model."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(TEST_MODEL, device="cpu")

@pytest_asyncio.fixture
async def semantic_engine_test(small_corpus, test_semantic_model):
    """Create semantic engine with test model."""
    from floridify.search.semantic.core import SemanticSearch

    engine = await SemanticSearch.from_corpus(
        corpus=small_corpus,
        model_name=TEST_MODEL,  # Use test model
    )

    yield engine
```

**Environment-Based Configuration**
```python
# src/floridify/search/semantic/constants.py
import os

# Use lightweight model in test environment
DEFAULT_SENTENCE_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
    if os.getenv("PYTEST_CURRENT_TEST")
    else "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
)
```

### Why This Works
- Smaller models load faster and use less memory
- No `trust_remote_code` requirement = simpler initialization
- Tests still validate business logic with realistic embeddings

### Model Comparison for Testing
| Model | Dimensions | trust_remote_code | Load Time | Test Suitability |
|-------|-----------|-------------------|-----------|------------------|
| all-MiniLM-L6-v2 | 384 | ❌ No | ~1s | ✅ Excellent |
| BAAI/bge-m3 | 1024 | ❌ No | ~3s | ✅ Good |
| GTE-Qwen2-1.5B | 1536 | ✅ Yes | ~10s | ⚠️ Production only |

---

## Recommended Implementation Strategy

### Phase 1: Immediate Stabilization (Choose One)
1. **Quick Fix**: Force CPU mode in conftest.py (Solution 1A)
2. **Better Fix**: Use test-friendly model (Solution 7)

### Phase 2: Robust Testing (Combine)
1. Configure multiprocessing for macOS (Solution 2A)
2. Mock models for unit tests (Solution 4)
3. Use real models for integration tests with CPU mode

### Phase 3: Production Configuration
1. Keep GTE-Qwen2 for production/CLI usage
2. Auto-detect test environment and switch to lightweight model
3. Document testing requirements clearly

### Example Combined Implementation

```python
# tests/conftest.py
import os
import sys
import pytest
import multiprocessing as mp

# ============================================================================
# MACOS FORK SAFETY - Configure BEFORE any imports
# ============================================================================
if sys.platform == "darwin":
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # Already set

# ============================================================================
# PYTORCH STABILITY - Set environment variables BEFORE torch import
# ============================================================================
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# ============================================================================
# TEST MODEL CONFIGURATION
# ============================================================================
TEST_SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment for stability on Apple Silicon."""
    import torch

    # Force CPU mode for tests
    if hasattr(torch.backends, "mps"):
        original_is_available = torch.backends.mps.is_available
        torch.backends.mps.is_available = lambda: False

    torch.set_default_device("cpu")

    yield

    # Restore (if needed)
    torch.set_default_device("cpu")

@pytest.fixture(scope="session")
def semantic_test_model():
    """Provide lightweight model for semantic search tests."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        TEST_SEMANTIC_MODEL,
        device="cpu",
        trust_remote_code=False,
    )

    yield model

    # Cleanup
    del model

# ============================================================================
# SELECTIVE TEST EXECUTION
# ============================================================================
def pytest_collection_modifyitems(config, items):
    """Add skip markers for problematic tests on macOS."""
    if sys.platform == "darwin":
        skip_mps = pytest.mark.skip(reason="MPS backend unstable on macOS during tests")
        for item in items:
            if "mps" in item.keywords or "gpu" in item.keywords:
                item.add_marker(skip_mps)
```

```python
# tests/search/test_semantic_search.py
import pytest
from unittest.mock import patch

class TestSemanticSearch:
    """Semantic search tests with stability fixes."""

    @pytest.mark.asyncio
    async def test_initialize_index(self, semantic_engine: SemanticSearch):
        """Test initializing semantic index - uses test model via fixture."""
        await semantic_engine.initialize()

        assert semantic_engine.sentence_index is not None
        assert semantic_engine.sentence_embeddings is not None

    @pytest.mark.asyncio
    async def test_semantic_similarity_mocked(self, mocker):
        """Test semantic search with fully mocked model."""
        import numpy as np

        # Mock the model loading
        mock_model = mocker.MagicMock()
        mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)

        with patch("floridify.search.semantic.core.get_cached_model") as mock_get:
            mock_get.return_value = mock_model

            # Create engine with mocked model
            engine = await SemanticSearch.from_corpus(...)
            results = await engine.search("test query")

            assert isinstance(results, list)
```

---

## Debugging Techniques

### 1. Enable Python Faulthandler
```bash
# Get detailed segfault information
python -X faulthandler -m pytest tests/search/test_semantic_search.py -v
```

### 2. Run with GDB (macOS)
```bash
# Install gdb via homebrew
brew install gdb

# Run pytest under gdb
gdb --args python -m pytest tests/search/test_semantic_search.py

# In gdb:
(gdb) run
# When it crashes:
(gdb) backtrace
```

### 3. Isolate Problem Test
```bash
# Run single test in isolation
pytest tests/search/test_semantic_search.py::TestSemanticSearch::test_initialize_index -v

# Run with maximum verbosity
pytest tests/search/test_semantic_search.py -vvv --tb=long

# Run in subprocess (requires pytest-forked)
pytest tests/search/test_semantic_search.py --forked
```

### 4. Check for Thread/Process Issues
```python
# Add to test file
import threading
import multiprocessing as mp

def test_thread_safety():
    """Debug thread and process state."""
    print(f"Threads: {threading.active_count()}")
    print(f"Thread list: {threading.enumerate()}")
    print(f"MP start method: {mp.get_start_method()}")
```

---

## References

### Known Issues
- [sentence-transformers #2631](https://github.com/UKPLab/sentence-transformers/issues/2631) - Segfault with sklearn on macOS
- [sentence-transformers #1736](https://github.com/UKPLab/sentence-transformers/issues/1736) - M1 Silicon compatibility
- [HuggingFace Forum](https://discuss.huggingface.co/t/segfault-during-pytorch-transformers-inference-on-apple-silicon-m4-libomp-dylib-crash-on-layernorm/160930) - M4 segfault with libomp.dylib
- [Python Bug #43802](https://bugs.python.org/issue43802) - macOS multiprocessing segfault

### Documentation
- [PyTorch MPS Backend](https://docs.pytorch.org/docs/stable/notes/mps.html)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html)

---

## Summary

**Root Cause**: PyTorch MPS backend + fork() + trust_remote_code models = segfault on Apple Silicon

**Best Solutions**:
1. **For CI/Tests**: Use lightweight model (all-MiniLM-L6-v2) with CPU mode
2. **For Unit Tests**: Mock model loading entirely
3. **For Integration Tests**: Use session-scoped fixtures with spawn mode
4. **For Production**: Keep GTE-Qwen2, detect test environment and switch models

**Quick Fix** (Add to `tests/conftest.py`):
```python
import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
torch.set_default_device("cpu")
```

**Maintainable Fix** (Add to `tests/conftest.py`):
```python
import sys
import multiprocessing as mp

if sys.platform == "darwin":
    mp.set_start_method('spawn', force=True)

TEST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```
