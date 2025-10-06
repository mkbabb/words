#!/usr/bin/env python3
"""Test GTE-Qwen2 model loading with trust_remote_code parameter."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sentence_transformers import SentenceTransformer

from floridify.search.semantic.constants import DEFAULT_SENTENCE_MODEL

print(f"Testing model: {DEFAULT_SENTENCE_MODEL}")
print("=" * 80)

try:
    print("\n1. Loading model WITH trust_remote_code=True...")
    model = SentenceTransformer(DEFAULT_SENTENCE_MODEL, trust_remote_code=True)
    print(f"   ✅ Model loaded successfully")
    print(f"   Model device: {model.device}")
    print(f"   Max sequence length: {model.max_seq_length}")

    print("\n2. Testing embedding generation...")
    test_sentence = "hello world"
    embedding = model.encode(test_sentence)
    print(f"   ✅ Embedding generated")
    print(f"   Embedding shape: {embedding.shape}")
    print(f"   Embedding dtype: {embedding.dtype}")

    print("\n✅ All tests passed!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
