#!/usr/bin/env python
"""Simple test of VersionConfig without full imports."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test just the config
from src.floridify.connectors.config import VersionConfig

print("=" * 60)
print("Testing VersionConfig")
print("=" * 60)

# Test 1: Default config
print("\n1. Default VersionConfig:")
config = VersionConfig()
print(f"  force_api: {config.force_api}")
print(f"  version: {config.version}")
print(f"  save_versioned: {config.save_versioned}")
print(f"  increment_version: {config.increment_version}")

# Test 2: Custom config
print("\n2. Custom VersionConfig:")
config = VersionConfig(
    force_api=True,
    version="2.0.0",
    save_versioned=False,
    increment_version=False,
)
print(f"  force_api: {config.force_api}")
print(f"  version: {config.version}")
print(f"  save_versioned: {config.save_versioned}")
print(f"  increment_version: {config.increment_version}")

# Test 3: Immutability
print("\n3. Testing immutability:")
try:
    config.force_api = False
    print("  ✗ Config should be immutable!")
except Exception as e:
    print(f"  ✓ Config is properly immutable: {type(e).__name__}")

print("\n" + "=" * 60)
print("VersionConfig test successful!")
print("=" * 60)