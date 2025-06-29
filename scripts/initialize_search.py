#!/usr/bin/env python3
"""Initialize the Floridify search engine with comprehensive English and French words.

This script demonstrates the search engine initialization process and can be run 
after installing the required dependencies.

Usage:
    python scripts/initialize_search.py [--force]
    
Options:
    --force    Force rebuild of search indices
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from floridify.search.search_manager import SearchManager
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Dependencies not available: {e}")
    print("To install dependencies, run: uv pip install -r requirements.txt")
    DEPENDENCIES_AVAILABLE = False


async def initialize_search_engine(force_rebuild: bool = False) -> None:
    """Initialize the comprehensive search engine."""
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Cannot initialize search engine - missing dependencies")
        print("\nRequired packages:")
        print("  - numpy")
        print("  - scikit-learn") 
        print("  - faiss-cpu")
        print("  - rapidfuzz")
        print("  - pygtrie")
        print("  - httpx")
        print("  - aiofiles")
        print("\nInstall with: uv pip install numpy scikit-learn faiss-cpu rapidfuzz pygtrie httpx aiofiles")
        return
    
    print("🔍 Initializing Floridify Search Engine...")
    print("="*60)
    
    try:
        # Initialize search manager
        search_manager = SearchManager()
        
        if force_rebuild:
            print("🔄 Force rebuild enabled - this will take several minutes")
        
        # Initialize with comprehensive lexicons
        await search_manager.initialize(force_rebuild=force_rebuild)
        
        # Show final statistics
        stats = search_manager.get_search_stats()
        
        print("\n" + "="*60)
        print("✅ Search Engine Successfully Initialized!")
        print("="*60)
        
        # Index statistics
        index_stats = stats['index']
        print(f"📊 Word Index:")
        print(f"  • Total words: {index_stats['total_words']:,}")
        print(f"  • Unique words: {index_stats['unique_words']:,}")
        print(f"  • Languages: {', '.join(index_stats['languages'])}")
        print(f"  • Index status: {'✅ Loaded' if index_stats['is_loaded'] else '❌ Not loaded'}")
        
        # Vector statistics
        vector_stats = stats['vectorized']
        print(f"\n🧠 Vector Search:")
        print(f"  • Vector status: {'✅ Built' if vector_stats['is_built'] else '❌ Not built'}")
        print(f"  • Embedding dimension: {vector_stats.get('embedding_dim', 'N/A')}")
        print(f"  • Character vocab: {vector_stats.get('char_vocab_size', 'N/A'):,}")
        print(f"  • Subword vocab: {vector_stats.get('subword_vocab_size', 'N/A'):,}")
        
        # Lexicon statistics
        lexicon_stats = stats['lexicons']
        print(f"\n📚 Lexicon Sources:")
        print(f"  • Online sources: {lexicon_stats['online_sources']}")
        print(f"  • Local collections: {lexicon_stats['local_collections']}")
        print(f"  • Cache directory: {lexicon_stats['cache_dir']}")
        
        print(f"\n💾 Cache location: {stats['cache_dir']}")
        
        print("\n🎉 Ready for search operations!")
        print("\nExample CLI commands:")
        print("  floridify search fuzzy 'hello' --max-results 10")
        print("  floridify search similar 'happy' --count 5")
        print("  floridify search advanced 'bio' --min-length 6")
        print("  floridify search stats")
        
    except Exception as e:
        print(f"❌ Search engine initialization failed: {e}")
        print("\nThis may be due to:")
        print("  • Missing dependencies")
        print("  • Network connectivity issues")
        print("  • Insufficient disk space")
        print("  • Permission issues")
        raise


def main() -> None:
    """Main entry point for search initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize Floridify search engine with comprehensive word indices"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force rebuild of search indices"
    )
    
    args = parser.parse_args()
    
    # Run initialization
    asyncio.run(initialize_search_engine(force_rebuild=args.force))


if __name__ == "__main__":
    main()