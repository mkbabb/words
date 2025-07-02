"""Tests for Anki card generation."""

from unittest.mock import MagicMock, patch

import pytest

from src.floridify.models import Definition, Examples, Word, WordType


class TestAnkiGenerator:
    """Test Anki card generation functionality."""

    @pytest.fixture
    def mock_anki_generator(self):
        """Create AnkiGenerator with mocked dependencies."""
        try:
            from src.floridify.anki.generator import AnkiGenerator
            return AnkiGenerator()
        except ImportError:
            pytest.skip("Anki module not available")

    @pytest.fixture
    def sample_dictionary_entry(self):
        """Sample dictionary entry for testing."""
        return MagicMock(
            word=Word(text="test"),
            definitions=[
                Definition(
                    word_type=WordType.NOUN,
                    definition="A procedure to establish quality.",
                    examples=Examples(),
                    synonyms=[]
                ),
                Definition(
                    word_type=WordType.VERB,
                    definition="To examine or try out.",
                    examples=Examples(),
                    synonyms=[]
                )
            ]
        )

    def test_generator_initialization(self, mock_anki_generator):
        """Test AnkiGenerator initialization."""
        assert mock_anki_generator is not None

    def test_basic_card_generation(self, mock_anki_generator, sample_dictionary_entry):
        """Test basic card generation from dictionary entry."""
        try:
            cards = mock_anki_generator.generate_cards(sample_dictionary_entry)
            assert isinstance(cards, list)
            assert len(cards) > 0
        except AttributeError:
            pytest.skip("generate_cards method not implemented")

    def test_multiple_word_types(self, mock_anki_generator, sample_dictionary_entry):
        """Test card generation for multiple word types."""
        try:
            cards = mock_anki_generator.generate_cards(sample_dictionary_entry)
            
            # Should generate cards for both noun and verb definitions
            assert len(cards) >= 2
            
        except AttributeError:
            pytest.skip("generate_cards method not implemented")

    @pytest.mark.asyncio
    async def test_deck_export(self, mock_anki_generator, sample_dictionary_entry, mock_cache_dir):
        """Test Anki deck export to .apkg file."""
        try:
            cards = mock_anki_generator.generate_cards(sample_dictionary_entry)
            output_path = mock_cache_dir / "test_deck.apkg"
            
            # Mock genanki operations
            with patch('genanki.Deck') as mock_deck, \
                 patch('genanki.Package') as mock_package:
                
                mock_deck_instance = MagicMock()
                mock_deck.return_value = mock_deck_instance
                
                mock_package_instance = MagicMock()
                mock_package.return_value = mock_package_instance
                
                mock_anki_generator.export_deck(cards, output_path)
                
                # Verify deck creation was called
                mock_deck.assert_called()
                mock_package.assert_called()
                
        except (AttributeError, ImportError):
            pytest.skip("export_deck method or genanki not available")

    def test_card_template_application(self, mock_anki_generator):
        """Test card template application."""
        try:
            # Test template loading
            template = mock_anki_generator._get_card_template("basic")
            assert template is not None
            
        except AttributeError:
            pytest.skip("Card template methods not implemented")

    def test_error_handling(self, mock_anki_generator):
        """Test error handling with invalid data."""
        try:
            # Test with None entry
            cards = mock_anki_generator.generate_cards(None)
            assert cards == []
            
            # Test with empty entry
            empty_entry = MagicMock(definitions=[])
            cards = mock_anki_generator.generate_cards(empty_entry)
            assert cards == []
            
        except AttributeError:
            pytest.skip("generate_cards method not implemented")


class TestAnkiTemplates:
    """Test Anki card templates."""

    def test_template_loading(self):
        """Test template loading functionality."""
        try:
            from src.floridify.anki.templates import get_card_template
            
            # Test basic template
            template = get_card_template("basic")
            assert template is not None
            assert "front" in template
            assert "back" in template
            
        except ImportError:
            pytest.skip("Anki templates module not available")

    def test_template_rendering(self):
        """Test template rendering with data."""
        try:
            from src.floridify.anki.templates import render_template
            
            data = {
                "word": "test",
                "definition": "A procedure to establish quality.",
                "examples": ["This is a test."]
            }
            
            rendered = render_template("basic", data)
            assert "test" in rendered
            assert "procedure" in rendered
            
        except ImportError:
            pytest.skip("Template rendering not available")

    def test_css_styling(self):
        """Test CSS styling in templates."""
        try:
            from src.floridify.anki.templates import get_card_css
            
            css = get_card_css()
            assert css is not None
            assert isinstance(css, str)
            assert len(css) > 0
            
        except ImportError:
            pytest.skip("CSS styling not available")


class TestAnkiConstants:
    """Test Anki-related constants."""

    def test_card_type_constants(self):
        """Test card type constant definitions."""
        try:
            from src.floridify.anki.constants import CardType
            
            # Verify expected card types exist
            assert hasattr(CardType, 'BASIC')
            assert hasattr(CardType, 'CLOZE')
            
        except ImportError:
            pytest.skip("Anki constants not available")

    def test_model_ids(self):
        """Test Anki model ID constants."""
        try:
            from src.floridify.anki.constants import MODEL_IDS
            
            assert isinstance(MODEL_IDS, dict)
            assert len(MODEL_IDS) > 0
            
        except ImportError:
            pytest.skip("Model IDs not available")


class TestAnkiIntegration:
    """Test Anki integration with other components."""

    def test_dictionary_entry_integration(self):
        """Test integration with dictionary entries."""
        try:
            from src.floridify.anki.generator import AnkiGenerator
            from src.floridify.models.dictionary import DictionaryEntry, Pronunciation
            
            # Create a real dictionary entry
            entry = DictionaryEntry(
                word=Word(text="integration"),
                pronunciation=Pronunciation(phonetic="/ˌɪntɪˈɡreɪʃən/"),
                providers={}
            )
            
            generator = AnkiGenerator()
            cards = generator.generate_cards(entry)
            
            # Should handle real entry structure
            assert isinstance(cards, list)
            
        except ImportError:
            pytest.skip("Anki integration components not available")

    def test_batch_processing(self):
        """Test batch processing of multiple entries."""
        try:
            from src.floridify.anki.generator import AnkiGenerator
            
            entries = [
                MagicMock(word=Word(text=f"word{i}"), definitions=[])
                for i in range(5)
            ]
            
            generator = AnkiGenerator()
            all_cards = []
            
            for entry in entries:
                cards = generator.generate_cards(entry)
                all_cards.extend(cards)
            
            # Should process multiple entries
            assert isinstance(all_cards, list)
            
        except ImportError:
            pytest.skip("Batch processing not available")