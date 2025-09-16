"""Debug test to find where Metadata.corpus_id error occurs."""

import asyncio

import pytest

from floridify.caching.manager import get_version_manager
from floridify.caching.models import ResourceType
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
async def test_metadata_corpus_id(test_db):
    """Test to find where Metadata.corpus_id error occurs."""

    corpus_manager = TreeCorpusManager()
    version_manager = get_version_manager()

    # Create a simple corpus
    corpus = Corpus(
        corpus_name="metadata_test",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=["hello", "world"],
    )
    saved_corpus = await corpus_manager.save_corpus(corpus)
    print(f"1. Saved corpus with ID: {saved_corpus.corpus_id}")

    # Update the corpus
    saved_corpus.vocabulary.append("test")
    updated_corpus = await corpus_manager.update_corpus(
        saved_corpus.corpus_id,
        {"vocabulary": saved_corpus.vocabulary},
    )
    print(f"2. Updated corpus: {updated_corpus}")

    # Check version chain
    try:
        metadata = await version_manager.get_latest(
            resource_id=saved_corpus.corpus_name,
            resource_type=ResourceType.CORPUS,
        )
        print(f"3. Got metadata: {metadata}")

        # Try to access corpus_id on metadata (this might fail)
        if hasattr(metadata, "corpus_id"):
            print(f"4. Metadata has corpus_id: {metadata.corpus_id}")
        else:
            print("4. Metadata does NOT have corpus_id attribute")
            print(f"   Metadata attributes: {dir(metadata)}")
    except Exception as e:
        print(f"Error getting metadata: {e}")

    print("✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_metadata_corpus_id(None))
