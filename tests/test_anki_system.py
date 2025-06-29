"""Tests for Anki flashcard generation system."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.floridify.ai.openai_connector import OpenAIConnector
from src.floridify.anki import AnkiCardGenerator, AnkiCardTemplate, CardType
from src.floridify.config import OpenAIConfig
from src.floridify.models import (
    Definition,
    DictionaryEntry,
    Examples,
    GeneratedExample,
    Pronunciation,
    ProviderData,
    Word,
    WordType,
)


class TestAnkiCardTemplate:
    """Test cases for Anki card templates."""

    def test_multiple_choice_template_creation(self) -> None:
        """Test creating multiple choice template."""
        template = AnkiCardTemplate.get_multiple_choice_template()
        
        assert template.card_type == CardType.MULTIPLE_CHOICE
        assert "{{Word}}" in template.front_template
        assert "{{ChoiceA}}" in template.front_template
        assert "{{CorrectChoice}}" in template.back_template
        assert len(template.css_styles) > 0
        assert len(template.javascript) > 0
        assert "Word" in template.fields
        assert "ChoiceA" in template.fields

    def test_fill_blank_template_creation(self) -> None:
        """Test creating fill-in-blank template."""
        template = AnkiCardTemplate.get_fill_in_blank_template()
        
        assert template.card_type == CardType.FILL_IN_BLANK
        assert "{{SentenceWithBlank}}" in template.front_template
        assert "{{CompleteSentence}}" in template.back_template
        assert len(template.css_styles) > 0
        assert "Word" in template.fields
        assert "SentenceWithBlank" in template.fields


class TestAnkiCardGenerator:
    """Test cases for Anki card generator."""

    @pytest.fixture
    def mock_openai_connector(self) -> OpenAIConnector:
        """Create mock OpenAI connector."""
        config = OpenAIConfig(api_key="test-key")
        connector = OpenAIConnector(config)
        connector.client = MagicMock()
        return connector

    @pytest.fixture
    def sample_dictionary_entry(self) -> DictionaryEntry:
        """Create sample dictionary entry for testing."""
        # Create as mock to avoid Beanie issues
        entry = MagicMock()
        entry.word = Word(text="serendipity")
        entry.pronunciation = Pronunciation(phonetic="ser-uhn-dip-i-tee")
        
        # Create AI synthesis provider data
        ai_provider = ProviderData(
            provider_name="ai_synthesis",
            definitions=[
                Definition(
                    word_type=WordType.NOUN,
                    definition="The faculty of making fortunate discoveries by accident",
                    examples=Examples(
                        generated=[
                            GeneratedExample(sentence="Her serendipity led to a breakthrough discovery."),
                            GeneratedExample(sentence="The meeting was pure serendipity."),
                        ]
                    ),
                )
            ],
            is_synthetic=True,
        )
        
        entry.providers = {"ai_synthesis": ai_provider}
        return entry

    @pytest.mark.asyncio
    async def test_generate_multiple_choice_card(
        self, mock_openai_connector: OpenAIConnector, sample_dictionary_entry: DictionaryEntry
    ) -> None:
        """Test generating multiple choice flashcard."""
        
        # Mock AI response for multiple choice generation
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """A) The faculty of making fortunate discoveries by accident
B) A type of scientific instrument used in research
C) The study of ancient civilizations and their customs
D) A mathematical formula for calculating probability

CORRECT: A"""

        mock_openai_connector.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Initialize generator
        generator = AnkiCardGenerator(mock_openai_connector)
        
        # Generate cards
        cards = await generator.generate_cards(
            sample_dictionary_entry, 
            card_types=[CardType.MULTIPLE_CHOICE],
            max_cards_per_type=1
        )
        
        # Verify results
        assert len(cards) == 1
        card = cards[0]
        
        assert card.card_type == CardType.MULTIPLE_CHOICE
        assert card.fields["Word"] == "serendipity"
        assert card.fields["ChoiceA"] == "The faculty of making fortunate discoveries by accident"
        assert card.fields["CorrectChoice"] == "A"
        
        # Test rendering
        front_html = card.render_front()
        back_html = card.render_back()
        
        assert "serendipity" in front_html
        assert "The faculty of making fortunate discoveries by accident" in front_html
        assert "Correct Answer: A" in back_html

    @pytest.mark.asyncio
    async def test_generate_fill_blank_card(
        self, mock_openai_connector: OpenAIConnector, sample_dictionary_entry: DictionaryEntry
    ) -> None:
        """Test generating fill-in-the-blank flashcard."""
        
        # Mock AI response for fill-in-the-blank generation
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """SENTENCE: The scientist's _____ led to an unexpected breakthrough in cancer research.
HINT: A fortunate accident or discovery"""

        mock_openai_connector.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Initialize generator
        generator = AnkiCardGenerator(mock_openai_connector)
        
        # Generate cards
        cards = await generator.generate_cards(
            sample_dictionary_entry,
            card_types=[CardType.FILL_IN_BLANK],
            max_cards_per_type=1
        )
        
        # Verify results
        assert len(cards) == 1
        card = cards[0]
        
        assert card.card_type == CardType.FILL_IN_BLANK
        assert card.fields["Word"] == "serendipity"
        assert "_____" in card.fields["SentenceWithBlank"]
        assert card.fields["Hint"] == "A fortunate accident or discovery"
        assert "serendipity" in card.fields["CompleteSentence"]
        
        # Test rendering
        front_html = card.render_front()
        back_html = card.render_back()
        
        assert "_____" in front_html
        assert "A fortunate accident or discovery" in front_html
        assert "serendipity" in back_html

    @pytest.mark.asyncio
    async def test_generate_multiple_card_types(
        self, mock_openai_connector: OpenAIConnector, sample_dictionary_entry: DictionaryEntry
    ) -> None:
        """Test generating both card types."""
        
        # Mock responses for both card types
        responses = [
            # Multiple choice response
            MagicMock(),
            # Fill blank response  
            MagicMock(),
        ]
        
        responses[0].choices[0].message.content = """A) The faculty of making fortunate discoveries by accident
B) A type of scientific instrument
C) The study of ancient civilizations
D) A mathematical formula

CORRECT: A"""

        responses[1].choices[0].message.content = """SENTENCE: The researcher's _____ led to a major breakthrough.
HINT: A fortunate discovery"""

        mock_openai_connector.client.chat.completions.create = AsyncMock(side_effect=responses)
        
        # Initialize generator
        generator = AnkiCardGenerator(mock_openai_connector)
        
        # Generate both card types
        cards = await generator.generate_cards(
            sample_dictionary_entry,
            card_types=[CardType.MULTIPLE_CHOICE, CardType.FILL_IN_BLANK],
            max_cards_per_type=1
        )
        
        # Verify results
        assert len(cards) == 2
        
        # Check card types
        card_types = [card.card_type for card in cards]
        assert CardType.MULTIPLE_CHOICE in card_types
        assert CardType.FILL_IN_BLANK in card_types

    def test_parse_multiple_choice_response(self, mock_openai_connector: OpenAIConnector) -> None:
        """Test parsing multiple choice AI response."""
        generator = AnkiCardGenerator(mock_openai_connector)
        
        response_content = """A) The faculty of making fortunate discoveries by accident
B) A type of scientific instrument used in research  
C) The study of ancient civilizations and their customs
D) A mathematical formula for calculating probability

CORRECT: A"""
        
        choices, correct = generator._parse_multiple_choice_response(response_content)
        
        assert len(choices) == 4
        assert choices["A"] == "The faculty of making fortunate discoveries by accident"
        assert choices["B"] == "A type of scientific instrument used in research"
        assert correct == "A"

    def test_parse_fill_blank_response(self, mock_openai_connector: OpenAIConnector) -> None:
        """Test parsing fill-in-the-blank AI response."""
        generator = AnkiCardGenerator(mock_openai_connector)
        
        response_content = """SENTENCE: The scientist's _____ led to an unexpected breakthrough.
HINT: A fortunate accident or discovery"""
        
        sentence, hint = generator._parse_fill_blank_response(response_content)
        
        assert sentence == "The scientist's _____ led to an unexpected breakthrough."
        assert hint == "A fortunate accident or discovery"

    def test_card_rendering_with_lists(self, mock_openai_connector: OpenAIConnector) -> None:
        """Test card rendering with list fields."""
        generator = AnkiCardGenerator(mock_openai_connector)
        template = AnkiCardTemplate.get_multiple_choice_template()
        
        fields = {
            "Word": "test",
            "Examples": ["First example", "Second example"],
            "Synonyms": ["synonym1", "synonym2", "synonym3"],
            "EmptyList": [],
        }
        
        from src.floridify.anki.generator import AnkiCard
        card = AnkiCard(CardType.MULTIPLE_CHOICE, fields, template)
        
        back_html = card.render_back()
        
        # Lists with content should be rendered
        assert "First example" in back_html
        assert "Second example" in back_html
        assert "synonym1" in back_html
        
        # Empty lists should not break rendering
        assert "EmptyList" not in back_html

    @pytest.mark.asyncio
    async def test_export_to_apkg(
        self, mock_openai_connector: OpenAIConnector, sample_dictionary_entry: DictionaryEntry, tmp_path
    ) -> None:
        """Test exporting cards to .apkg format."""
        
        # Create a simple mock card
        template = AnkiCardTemplate.get_multiple_choice_template()
        fields = {
            "Word": "test",
            "Pronunciation": "test",
            "ChoiceA": "Choice A",
            "ChoiceB": "Choice B", 
            "ChoiceC": "Choice C",
            "ChoiceD": "Choice D",
            "CorrectChoice": "A",
            "Definition": "Test definition",
            "Examples": ["Example 1"],
            "Synonyms": ["synonym1"],
        }
        
        from src.floridify.anki.generator import AnkiCard
        cards = [AnkiCard(CardType.MULTIPLE_CHOICE, fields, template)]
        
        # Initialize generator and export
        generator = AnkiCardGenerator(mock_openai_connector)
        output_path = tmp_path / "test_deck.apkg"
        
        result = generator.export_to_apkg(cards, "Test Deck", str(output_path))
        
        # Should export both .apkg and .html files
        assert result is True
        apkg_file = output_path.with_suffix('.apkg')
        html_file = output_path.with_suffix('.html')
        
        assert apkg_file.exists()
        assert html_file.exists()
        
        # Check that .apkg file has content
        assert apkg_file.stat().st_size > 0
        
        # Check HTML content
        html_content = html_file.read_text()
        assert "Test Deck" in html_content
        assert "Total cards: 1" in html_content
        assert "test" in html_content

    @pytest.mark.asyncio
    async def test_generate_cards_with_no_definitions(
        self, mock_openai_connector: OpenAIConnector
    ) -> None:
        """Test generating cards when entry has no definitions."""
        
        # Create entry with no definitions
        entry = MagicMock()
        entry.word = Word(text="empty")
        entry.pronunciation = Pronunciation(phonetic="empty")
        entry.providers = {
            "test": ProviderData(provider_name="test", definitions=[])
        }
        
        generator = AnkiCardGenerator(mock_openai_connector)
        
        cards = await generator.generate_cards(entry)
        
        # Should return empty list
        assert len(cards) == 0

    @pytest.mark.asyncio
    async def test_generate_cards_with_ai_api_error(
        self, mock_openai_connector: OpenAIConnector, sample_dictionary_entry: DictionaryEntry
    ) -> None:
        """Test generating cards when AI API fails."""
        
        # Mock API to raise exception
        mock_openai_connector.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        generator = AnkiCardGenerator(mock_openai_connector)
        
        cards = await generator.generate_cards(
            sample_dictionary_entry,
            card_types=[CardType.MULTIPLE_CHOICE],
            max_cards_per_type=1
        )
        
        # Should handle error gracefully and return empty list
        assert len(cards) == 0