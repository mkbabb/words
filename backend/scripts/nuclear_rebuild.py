#!/usr/bin/env python3
"""Nuclear option: Wipe ALL versioned data and rebuild from scratch."""

import asyncio
from floridify.corpus.core import Corpus
from floridify.corpus.language.core import LanguageCorpus
from floridify.caching.models import BaseVersionedData
from floridify.models.base import Language
from floridify.storage.mongodb import get_storage
from floridify.search.semantic.models import SemanticIndex
from floridify.search.models import TrieIndex, SearchIndex

async def main():
    await get_storage()

    print("🧹 Deleting ALL versioned data from MongoDB...")

    # Delete all versioned data collections
    deleted_counts = {}
    for model_class in [Corpus.Metadata, SemanticIndex.Metadata, TrieIndex.Metadata, SearchIndex.Metadata, BaseVersionedData]:
        try:
            result = await model_class.find_all().delete()
            deleted_counts[model_class.__name__] = result.deleted_count if hasattr(result, 'deleted_count') else 0
            print(f"  - {model_class.__name__}: {deleted_counts[model_class.__name__]} deleted")
        except Exception as e:
            print(f"  - {model_class.__name__}: {e}")

    print(f"\n✅ Deleted {sum(deleted_counts.values())} total documents")

    print("\n🔨 Rebuilding language corpus from fresh sources...")
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="language_english",
        language=Language.ENGLISH,
        semantic=False,
    )

    print(f"\n✅ REBUILD COMPLETE")
    print(f"  Corpus: {corpus.corpus_name}")
    print(f"  Vocabulary: {len(corpus.vocabulary):,} words")
    print(f"  Lemmatized: {len(corpus.lemmatized_vocabulary):,} lemmas")
    print(f"  Children: {len(corpus.child_corpus_ids)} sub-corpora")

if __name__ == "__main__":
    asyncio.run(main())
