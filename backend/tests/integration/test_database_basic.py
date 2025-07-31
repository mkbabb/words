"""
Basic database integration tests to verify MongoDB setup and model creation.
"""

import pytest

from tests.conftest import assert_valid_object_id


class TestDatabaseBasicIntegration:
    """Test basic database functionality."""

    @pytest.mark.asyncio
    async def test_mongodb_connection(self, mongodb_client):
        """Test that MongoDB connection works."""
        # Ping the database
        result = await mongodb_client.admin.command("ping")
        assert result["ok"] == 1

    @pytest.mark.asyncio
    async def test_test_database_creation(self, test_db, test_db_name):
        """Test that test database is created with unique name."""
        assert test_db is not None
        assert test_db_name.startswith("test_floridify_")
        
        # Verify we can perform basic operations
        collection = test_db.test_collection
        await collection.insert_one({"test": "data"})
        
        doc = await collection.find_one({"test": "data"})
        assert doc is not None
        assert doc["test"] == "data"

    @pytest.mark.asyncio
    async def test_word_factory_creation(self, word_factory):
        """Test word factory creates valid word objects."""
        word = await word_factory(text="integration", language="en")
        
        assert word is not None
        assert word.text == "integration"
        assert word.language == "en"
        assert word.normalized == "integration"
        assert_valid_object_id(word.id)

    @pytest.mark.asyncio
    async def test_definition_factory_creation(self, definition_factory, word_factory):
        """Test definition factory creates valid definition objects."""
        # Create a word first
        word = await word_factory(text="define", language="en")
        
        # Create definition for the word
        definition = await definition_factory(
            word_instance=word,
            part_of_speech="verb",
            text="To state the meaning of something"
        )
        
        assert definition is not None
        assert definition.word_id == word.id
        assert definition.part_of_speech == "verb"
        assert definition.text == "To state the meaning of something"
        assert_valid_object_id(definition.id)

    @pytest.mark.asyncio
    async def test_wordlist_factory_creation(self, wordlist_factory):
        """Test wordlist factory creates valid wordlist objects."""
        wordlist = await wordlist_factory(
            name="Integration Test List",
            description="A test wordlist for integration testing",
            words=["integration", "test", "database"]
        )
        
        assert wordlist is not None
        assert wordlist.name == "Integration Test List"
        assert wordlist.total_words == 3
        assert wordlist.unique_words == 3
        assert len(wordlist.words) == 3
        assert_valid_object_id(wordlist.id)
        
        # Check word items (WordListItem objects have word_id, not word text)
        assert len(wordlist.words) == 3
        for word_item in wordlist.words:
            assert_valid_object_id(word_item.word_id)
            assert word_item.frequency == 1000

    @pytest.mark.asyncio
    async def test_database_isolation(self, test_db, word_factory):
        """Test that each test gets an isolated database."""
        # Create a word in this test
        word = await word_factory(text="isolated", language="en")
        assert word is not None
        
        # Verify it exists in our test database
        try:
            from src.floridify.models.models import Word
            found_word = await Word.find_one(Word.text == "isolated")
            assert found_word is not None
            assert found_word.id == word.id
        except ImportError:
            pytest.skip("Word model not available")

    @pytest.mark.asyncio
    async def test_multiple_model_creation(self, word_factory, definition_factory):
        """Test creating multiple related models."""
        # Create multiple words
        words = []
        for i in range(3):
            word = await word_factory(text=f"multi{i}", language="en")
            words.append(word)
        
        # Create definitions for each word
        definitions = []
        for i, word in enumerate(words):
            definition = await definition_factory(
                word_instance=word,
                part_of_speech="noun",
                text=f"Definition for multi{i}"
            )
            definitions.append(definition)
        
        # Verify all were created correctly
        assert len(words) == 3
        assert len(definitions) == 3
        
        for i, (word, definition) in enumerate(zip(words, definitions)):
            assert word.text == f"multi{i}"
            assert definition.word_id == word.id
            assert definition.text == f"Definition for multi{i}"