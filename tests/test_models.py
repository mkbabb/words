"""Tests for data models."""

import pytest
from datetime import datetime

from src.floridify.models import (
    Word,
    DictionaryEntry,
    ProviderData,
    Definition,
    Examples,
    GeneratedExample,
    Pronunciation,
    WordType,
)


class TestWord:
    """Tests for Word model."""
    
    def test_word_creation(self) -> None:
        """Test basic word creation."""
        word = Word(text="example")
        assert word.text == "example"
        assert word.embedding == {}
    
    def test_word_with_embedding(self) -> None:
        """Test word with embedding data."""
        embedding = {"openai": [0.1, 0.2, 0.3]}
        word = Word(text="test", embedding=embedding)
        assert word.text == "test"
        assert word.embedding == embedding


class TestDefinition:
    """Tests for Definition model."""
    
    def test_definition_creation(self) -> None:
        """Test basic definition creation."""
        definition = Definition(
            word_type=WordType.NOUN,
            definition="A representative case or instance"
        )
        assert definition.word_type == WordType.NOUN
        assert definition.definition == "A representative case or instance"
        assert definition.synonyms == []
        assert isinstance(definition.examples, Examples)
    
    def test_definition_with_examples(self) -> None:
        """Test definition with examples."""
        examples = Examples(
            generated=[GeneratedExample(sentence="This is an **example** sentence.")]
        )
        definition = Definition(
            word_type=WordType.NOUN,
            definition="A test definition",
            examples=examples
        )
        assert len(definition.examples.generated) == 1
        assert definition.examples.generated[0].sentence == "This is an **example** sentence."


class TestProviderData:
    """Tests for ProviderData model."""
    
    def test_provider_data_creation(self) -> None:
        """Test basic provider data creation."""
        provider_data = ProviderData(provider_name="test_provider")
        assert provider_data.provider_name == "test_provider"
        assert provider_data.definitions == []
        assert provider_data.is_synthetic is False
        assert isinstance(provider_data.last_updated, datetime)
    
    def test_synthetic_provider_data(self) -> None:
        """Test synthetic provider data."""
        definition = Definition(
            word_type=WordType.VERB,
            definition="To demonstrate or illustrate"
        )
        provider_data = ProviderData(
            provider_name="ai",
            definitions=[definition],
            is_synthetic=True
        )
        assert provider_data.is_synthetic is True
        assert len(provider_data.definitions) == 1


# DictionaryEntry tests removed - requires Beanie initialization with MongoDB


class TestExamples:
    """Tests for Examples model."""
    
    def test_empty_examples(self) -> None:
        """Test empty examples container."""
        examples = Examples()
        assert examples.generated == []
        assert examples.literature == []
    
    def test_examples_with_generated(self) -> None:
        """Test examples with generated content."""
        generated = [
            GeneratedExample(sentence="First **example** sentence."),
            GeneratedExample(sentence="Second **example** sentence.", regenerable=False)
        ]
        examples = Examples(generated=generated)
        
        assert len(examples.generated) == 2
        assert examples.generated[0].regenerable is True
        assert examples.generated[1].regenerable is False