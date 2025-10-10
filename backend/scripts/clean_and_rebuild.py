#!/usr/bin/env python3
"""Clean corrupted corpus and rebuild from scratch."""

import asyncio
from floridify.corpus.core import Corpus
from floridify.corpus.language.core import LanguageCorpus
from floridify.models.base import Language
from floridify.storage.mongodb import get_storage

async def main():
    await get_storage()

    # Delete corrupted corpus
    print("Deleting corrupted language_english corpus...")
    await Corpus.Metadata.find({"resource_id": "language_english"}).delete()

    # Rebuild
    print("Rebuilding language corpus with proper aggregation...")
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="language_english",
        language=Language.ENGLISH,
        semantic=False,
    )

    print(f"✅ Corpus rebuilt: {len(corpus.vocabulary)} words, {len(corpus.child_corpus_ids)} children")
    print(f"✅ Lemmatized vocabulary: {len(corpus.lemmatized_vocabulary)} lemmas")

if __name__ == "__main__":
    asyncio.run(main())
