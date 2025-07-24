"""Tests for enhanced metadata fields in data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from floridify.models.models import (
    Definition,
    ProviderData,
    SynthesizedDictionaryEntry,
    Example,
    Pronunciation,
    Fact
)


class TestDefinitionMetadata:
    """Test enhanced metadata fields in Definition model."""

    def test_definition_with_default_metadata(self):
        """Test Definition creation with default metadata values."""
        definition = Definition(
            word_type="noun",
            definition="A test definition"
        )
        
        # Test default values
        assert definition.created_at is not None
        assert definition.updated_at is not None
        assert definition.accessed_at is None
        assert definition.created_by is None
        assert definition.updated_by is None
        assert definition.source_attribution is None
        assert definition.version == 1
        assert definition.quality_score is None
        assert definition.validation_status is None
        assert isinstance(definition.metadata, dict)
        assert len(definition.metadata) == 0

    def test_definition_with_custom_metadata(self):
        """Test Definition creation with custom metadata values."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        
        definition = Definition(
            word_type="verb",
            definition="A custom definition",
            created_at=custom_time,
            updated_at=custom_time,
            created_by="ai-synthesis",
            source_attribution="gpt-4",
            version=2,
            quality_score=0.95,
            validation_status="verified",
            metadata={"custom_field": "test_value"}
        )
        
        assert definition.created_at == custom_time
        assert definition.updated_at == custom_time
        assert definition.created_by == "ai-synthesis"
        assert definition.source_attribution == "gpt-4"
        assert definition.version == 2
        assert definition.quality_score == 0.95
        assert definition.validation_status == "verified"
        assert definition.metadata["custom_field"] == "test_value"

    def test_definition_version_validation(self):
        """Test version field validation (must be >= 1)."""
        with pytest.raises(ValidationError):
            Definition(
                word_type="noun",
                definition="Test",
                version=0
            )

    def test_definition_quality_score_validation(self):
        """Test quality_score field validation (0.0 to 1.0)."""
        # Valid range
        definition = Definition(
            word_type="noun",
            definition="Test",
            quality_score=0.5
        )
        assert definition.quality_score == 0.5
        
        # Invalid range
        with pytest.raises(ValidationError):
            Definition(
                word_type="noun",
                definition="Test",
                quality_score=1.5
            )
        
        with pytest.raises(ValidationError):
            Definition(
                word_type="noun",
                definition="Test",
                quality_score=-0.1
            )

    def test_definition_backwards_compatibility(self):
        """Test that new metadata fields don't break existing functionality."""
        # Old-style creation should still work
        definition = Definition(
            word_type="adjective",
            definition="Beautiful",
            synonyms=["pretty", "lovely"],
            meaning_cluster="beauty"
        )
        
        assert definition.word_type == "adjective"
        assert definition.definition == "Beautiful"
        assert "pretty" in definition.synonyms
        assert definition.meaning_cluster == "beauty"
        # New fields should have default values
        assert definition.version == 1
        assert definition.metadata == {}


class TestProviderDataMetadata:
    """Test enhanced metadata fields in ProviderData model."""

    def test_provider_data_with_metadata(self):
        """Test ProviderData creation with metadata."""
        provider_data = ProviderData(
            provider_name="oxford-api",
            sync_status="synced",
            version=3,
            metadata={"api_version": "v1.2", "rate_limit": 1000}
        )
        
        assert provider_data.provider_name == "oxford-api"
        assert provider_data.sync_status == "synced"
        assert provider_data.version == 3
        assert provider_data.metadata["api_version"] == "v1.2"
        assert provider_data.created_at is not None
        assert provider_data.accessed_at is None


class TestDictionaryEntryMetadata:
    """Test enhanced metadata fields in DictionaryEntry model."""

    def test_dictionary_entry_with_metadata(self):
        """Test DictionaryEntry creation with metadata."""
        pronunciation = Pronunciation(phonetic="test", ipa="/test/")
        
        # Use model_construct to bypass database initialization
        entry = DictionaryEntry.model_construct(
            word="test",
            pronunciation=pronunciation,
            lookup_count=5,
            quality_score=0.8,
            status="active",
            metadata={"source": "user_input"}
        )
        
        assert entry.word == "test"
        assert entry.lookup_count == 5
        assert entry.quality_score == 0.8
        assert entry.status == "active"
        assert entry.metadata["source"] == "user_input"
        assert entry.created_at is not None

    def test_dictionary_entry_lookup_count_validation(self):
        """Test lookup_count validation (must be >= 0)."""
        pronunciation = Pronunciation()
        
        with pytest.raises(ValidationError):
            DictionaryEntry.model_validate({
                "word": "test",
                "pronunciation": pronunciation.model_dump(),
                "lookup_count": -1
            })


class TestSynthesizedDictionaryEntryMetadata:
    """Test enhanced metadata fields in SynthesizedDictionaryEntry model."""

    def test_synthesized_entry_with_metadata(self):
        """Test SynthesizedDictionaryEntry creation with metadata."""
        pronunciation = Pronunciation(phonetic="test", ipa="/test/")
        definition = Definition(word_type="noun", definition="Test definition")
        fact = Fact(
            content="Test fact", 
            category="etymology", 
            confidence=0.9
        )
        
        # Use model_construct to bypass database initialization
        entry = SynthesizedDictionaryEntry.model_construct(
            word="test",
            pronunciation=pronunciation,
            definitions=[definition],
            facts=[fact],
            synthesis_version="gpt-4-turbo",
            synthesis_quality=0.92,
            definition_count=1,
            fact_count=1,
            lookup_count=10,
            regeneration_count=2,
            status="active",
            metadata={"synthesis_duration": 2.5}
        )
        
        assert entry.word == "test"
        assert entry.synthesis_version == "gpt-4-turbo"
        assert entry.synthesis_quality == 0.92
        assert entry.definition_count == 1
        assert entry.fact_count == 1
        assert entry.lookup_count == 10
        assert entry.regeneration_count == 2
        assert entry.status == "active"
        assert entry.metadata["synthesis_duration"] == 2.5

    def test_synthesized_entry_count_validation(self):
        """Test count field validation (must be >= 0)."""
        pronunciation = Pronunciation()
        
        with pytest.raises(ValidationError):
            SynthesizedDictionaryEntry.model_validate({
                "word": "test",
                "pronunciation": pronunciation.model_dump(),
                "definition_count": -1
            })
        
        with pytest.raises(ValidationError):
            SynthesizedDictionaryEntry.model_validate({
                "word": "test",
                "pronunciation": pronunciation.model_dump(),
                "fact_count": -1
            })

    def test_synthesized_entry_quality_validation(self):
        """Test synthesis_quality validation (0.0 to 1.0)."""
        pronunciation = Pronunciation()
        
        # Valid quality score
        entry = SynthesizedDictionaryEntry.model_construct(
            word="test",
            pronunciation=pronunciation,
            synthesis_quality=0.85
        )
        assert entry.synthesis_quality == 0.85
        
        # Invalid quality score
        with pytest.raises(ValidationError):
            SynthesizedDictionaryEntry.model_validate({
                "word": "test",
                "pronunciation": pronunciation.model_dump(),
                "synthesis_quality": 1.1
            })


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing code."""

    def test_old_style_definition_creation(self):
        """Test that old-style Definition creation still works."""
        definition = Definition(
            word_type="noun",
            definition="Legacy definition",
            synonyms=["synonym1", "synonym2"],
            examples=Examples(),
            meaning_cluster="test_cluster",
            raw_metadata={"legacy": True}
        )
        
        # Old fields should work
        assert definition.word_type == "noun"
        assert definition.definition == "Legacy definition"
        assert len(definition.synonyms) == 2
        assert definition.meaning_cluster == "test_cluster"
        assert definition.raw_metadata["legacy"] is True
        
        # New fields should have defaults
        assert definition.version == 1
        assert definition.created_at is not None
        assert definition.updated_at is not None
        assert definition.metadata == {}

    def test_model_serialization(self):
        """Test that models can be serialized to dict (for API responses)."""
        definition = Definition(
            word_type="noun",
            definition="Test definition",
            created_by="ai-synthesis",
            quality_score=0.9
        )
        
        data = definition.model_dump()
        
        # Check that new fields are included
        assert "created_at" in data
        assert "updated_at" in data
        assert "created_by" in data
        assert "quality_score" in data
        assert "version" in data
        assert "metadata" in data
        
        # Check values
        assert data["created_by"] == "ai-synthesis"
        assert data["quality_score"] == 0.9
        assert data["version"] == 1

    def test_model_deserialization(self):
        """Test that models can be created from dict (for API requests)."""
        data = {
            "word_type": "verb",
            "definition": "To test something",
            "synonyms": ["examine", "verify"],
            "created_by": "user-edit",
            "version": 2,
            "quality_score": 0.95,
            "metadata": {"source": "manual_entry"}
        }
        
        definition = Definition(**data)
        
        assert definition.word_type == "verb"
        assert definition.definition == "To test something"
        assert definition.created_by == "user-edit"
        assert definition.version == 2
        assert definition.quality_score == 0.95
        assert definition.metadata["source"] == "manual_entry"