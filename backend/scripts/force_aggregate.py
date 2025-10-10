#!/usr/bin/env python3
"""Force aggregate vocabulary with index rebuilding."""

import asyncio
from floridify.corpus.core import Corpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import get_storage

async def main():
    await get_storage()
    manager = get_tree_corpus_manager()

    corpus = await Corpus.get(corpus_name='language_english')
    print(f"Before aggregation:")
    print(f"  Vocabulary: {len(corpus.vocabulary):,} words")
    print(f"  Lemmatized: {len(corpus.lemmatized_vocabulary):,} lemmas")
    print(f"  Children: {len(corpus.child_corpus_ids)} sub-corpora")

    print("\n🔄 Running aggregation with index rebuilding...")
    await manager.aggregate_vocabularies(corpus.corpus_id, update_parent=True)

    corpus = await Corpus.get(corpus_name='language_english')
    print(f"\n✅ After aggregation:")
    print(f"  Vocabulary: {len(corpus.vocabulary):,} words")
    print(f"  Lemmatized: {len(corpus.lemmatized_vocabulary):,} lemmas")
    print(f"  Children: {len(corpus.child_corpus_ids)} sub-corpora")
    print(f"  Has 'en coulisse': {'en coulisse' in corpus.vocabulary}")

if __name__ == "__main__":
    asyncio.run(main())
