"""Anki flashcard generator for dictionary entries."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import genanki  # type: ignore[import-untyped]

from ..ai.connector import OpenAIConnector
from ..ai.templates import PromptTemplateManager as PromptLoader
from ..models import Definition, DictionaryEntry
from ..utils.logging import get_logger
from .templates import AnkiCardTemplate, CardType

logger = get_logger(__name__)


def format_template_variables(**kwargs: Any) -> dict[str, Any]:
    """Format template variables for prompt rendering."""
    return kwargs


class AnkiCard:
    """Represents a single Anki flashcard."""

    def __init__(
        self,
        card_type: CardType,
        fields: dict[str, Any],
        template: AnkiCardTemplate,
    ) -> None:
        """Initialize Anki card.

        Args:
            card_type: Type of flashcard
            fields: Dictionary of field names to values
            template: Card template with styling
        """
        self.card_type = card_type
        self.fields = fields
        self.template = template

    def render_front(self) -> str:
        """Render the front of the card."""
        return self._render_template(self.template.front_template)

    def render_back(self) -> str:
        """Render the back of the card."""
        return self._render_template(self.template.back_template)

    def _render_template(self, template: str) -> str:
        """Render a template with field values."""
        result = template

        # Handle list rendering first: {{#ListField}}{{.}}{{/ListField}}
        for field_name, field_value in self.fields.items():
            if isinstance(field_value, list) and field_value:  # Only if list has items
                list_pattern = f"{{{{#{field_name}}}}}(.*?){{{{/{field_name}}}}}"

                def replace_list(match: re.Match[str]) -> str:
                    item_template = match.group(1)
                    rendered_items = []
                    for item in field_value:
                        rendered_item = item_template.replace("{{.}}", str(item))
                        rendered_items.append(rendered_item)
                    return "".join(rendered_items)

                result = re.sub(list_pattern, replace_list, result, flags=re.DOTALL)

        # Handle conditional sections: {{#FieldName}}...{{/FieldName}}
        for field_name, field_value in self.fields.items():
            section_pattern = f"{{{{#{field_name}}}}}(.*?){{{{/{field_name}}}}}"

            # Check if field has a meaningful value
            has_value = False
            if isinstance(field_value, list):
                has_value = len(field_value) > 0
            elif isinstance(field_value, str):
                has_value = field_value.strip() != ""
            elif field_value is not None:
                has_value = bool(field_value)

            if has_value:
                # Show section content (remove the conditional tags)
                result = re.sub(section_pattern, r"\1", result, flags=re.DOTALL)
            else:
                # Hide entire section
                result = re.sub(section_pattern, "", result, flags=re.DOTALL)

        # Handle simple substitution: {{FieldName}}
        for field_name, field_value in self.fields.items():
            if not isinstance(field_value, list):  # Skip lists (already handled)
                result = result.replace(
                    f"{{{{{field_name}}}}}", str(field_value) if field_value else ""
                )

        return result


class AnkiCardGenerator:
    """Generates Anki flashcards from dictionary entries."""

    def __init__(
        self,
        openai_connector: OpenAIConnector,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        """Initialize Anki card generator.

        Args:
            openai_connector: OpenAI connector for generating card content
            prompt_loader: Optional prompt loader (creates default if None)
        """
        self.openai_connector = openai_connector
        self.prompt_loader = prompt_loader or PromptLoader()

    async def generate_cards(
        self,
        entry: DictionaryEntry,
        card_types: list[CardType] | None = None,
        max_cards_per_type: int = 2,
    ) -> list[AnkiCard]:
        """Generate flashcards for a dictionary entry.

        Args:
            entry: Dictionary entry to create cards for
            card_types: Types of cards to generate (default: all types)
            max_cards_per_type: Maximum cards per type to generate

        Returns:
            List of generated Anki cards
        """
        logger.debug(f"Generating cards for word: {entry.word.text}")
        if card_types is None:
            card_types = [CardType.MULTIPLE_CHOICE, CardType.FILL_IN_BLANK]
        
        logger.debug(
            f"Card types: {[ct.value for ct in card_types]}, max per type: {max_cards_per_type}"
        )
        cards: list[Any] = []

        # Get AI synthesis provider data (preferred) or fall back to other providers
        ai_provider = entry.providers.get("ai_synthesis")
        if ai_provider and ai_provider.definitions:
            definitions = ai_provider.definitions
        else:
            # Collect definitions from all providers
            definitions = []
            for provider_data in entry.providers.values():
                definitions.extend(provider_data.definitions)

        if not definitions:
            return cards

        # Generate cards for each requested type
        for card_type in card_types:
            type_cards = []

            for definition in definitions[:max_cards_per_type]:
                try:
                    if card_type == CardType.MULTIPLE_CHOICE:
                        card = await self._generate_multiple_choice_card(entry, definition)
                    elif card_type == CardType.FILL_IN_BLANK:
                        card = await self._generate_fill_blank_card(entry, definition)
                    else:
                        continue  # Skip unsupported card types

                    if card:
                        type_cards.append(card)

                except Exception as e:
                    logger.error(
                        f"Error generating {card_type.value} card for {entry.word.text}: {e}"
                    )
                    continue

            cards.extend(type_cards)

        return cards

    async def _generate_multiple_choice_card(
        self, entry: DictionaryEntry, definition: Definition
    ) -> AnkiCard | None:
        """Generate a multiple choice flashcard."""
        try:
            # Load prompt template  
            template_content = self.prompt_loader.render_template("anki_multiple_choice")

            # Prepare examples for the prompt
            examples_text = ""
            if definition.examples.generated:
                examples_list = [ex.sentence for ex in definition.examples.generated[:3]]
                examples_text = " | ".join(examples_list)

            # Prepare template variables
            variables = format_template_variables(
                word=entry.word.text,
                definition=definition.definition,
                word_type=definition.word_type.value,
                examples=examples_text,
            )

            # Generate multiple choice content using template
            prompt = template_content.format(**variables)

            # Make API call
            response = await self.openai_connector.client.chat.completions.create(
                model=self.openai_connector.model_name,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=self.openai_connector.temperature or 0.6,
                max_tokens=self.openai_connector.max_tokens,
            )

            content = response.choices[0].message.content
            if not content:
                return None

            # Parse the response
            choices, correct_choice = self._parse_multiple_choice_response(content)
            if not choices or not correct_choice:
                return None

            # Prepare card fields
            fields = {
                "Word": entry.word.text,
                "Pronunciation": entry.pronunciation.phonetic or f"/{entry.word.text}/",
                "ChoiceA": choices.get("A", ""),
                "ChoiceB": choices.get("B", ""),
                "ChoiceC": choices.get("C", ""),
                "ChoiceD": choices.get("D", ""),
                "CorrectChoice": correct_choice,
                "Definition": definition.definition,
                "Examples": [ex.sentence for ex in definition.examples.generated[:3]],
                "Synonyms": [syn.word.text for syn in definition.synonyms[:5]]
                if definition.synonyms
                else [],
            }

            # Get card template
            card_template = AnkiCardTemplate.get_multiple_choice_template()

            return AnkiCard(CardType.MULTIPLE_CHOICE, fields, card_template)

        except Exception as e:
            logger.error(f"Error generating multiple choice card: {e}")
            return None

    async def _generate_fill_blank_card(
        self, entry: DictionaryEntry, definition: Definition
    ) -> AnkiCard | None:
        """Generate a fill-in-the-blank flashcard."""
        try:
            # Load prompt template
            template_content = self.prompt_loader.render_template("anki_fill_blank")

            # Prepare examples for the prompt
            examples_text = ""
            if definition.examples.generated:
                examples_list = [ex.sentence for ex in definition.examples.generated[:3]]
                examples_text = " | ".join(examples_list)

            # Prepare template variables
            variables = format_template_variables(
                word=entry.word.text,
                definition=definition.definition,
                word_type=definition.word_type.value,
                examples=examples_text,
            )

            # Generate fill-in-the-blank content using template
            prompt = template_content.format(**variables)

            # Make API call
            response = await self.openai_connector.client.chat.completions.create(
                model=self.openai_connector.model_name,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=self.openai_connector.temperature or 0.7,
                max_tokens=self.openai_connector.max_tokens,
            )

            content = response.choices[0].message.content
            if not content:
                return None

            # Parse the response
            sentence_with_blank, hint = self._parse_fill_blank_response(content)
            if not sentence_with_blank:
                return None

            # Create complete sentence by replacing blank with highlighted word
            complete_sentence = sentence_with_blank.replace(
                "_____", f'<span class="word-highlight">{entry.word.text}</span>'
            )

            # Get additional examples (not used in the blank)
            additional_examples = []
            if definition.examples.generated:
                additional_examples = [ex.sentence for ex in definition.examples.generated[1:4]]

            # Prepare card fields
            fields = {
                "Word": entry.word.text,
                "Pronunciation": entry.pronunciation.phonetic or f"/{entry.word.text}/",
                "SentenceWithBlank": sentence_with_blank,
                "WordType": definition.word_type.value,
                "Hint": hint or "",
                "CompleteSentence": complete_sentence,
                "Definition": definition.definition,
                "AdditionalExamples": additional_examples,
            }

            # Get card template
            card_template = AnkiCardTemplate.get_fill_in_blank_template()

            return AnkiCard(CardType.FILL_IN_BLANK, fields, card_template)

        except Exception as e:
            logger.error(f"Error generating fill-in-the-blank card: {e}")
            return None

    def _parse_multiple_choice_response(self, content: str) -> tuple[dict[str, str], str]:
        """Parse AI response for multiple choice content.

        Returns:
            Tuple of (choices dict, correct_choice_letter)
        """
        choices = {}
        correct_choice = ""

        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Parse choices: A) choice text
            if re.match(r"^[A-D]\)", line):
                letter = line[0]
                choice_text = line[3:].strip()
                choices[letter] = choice_text

            # Parse correct answer: CORRECT: A
            elif line.startswith("CORRECT:"):
                correct_choice = line.split(":", 1)[1].strip()

        return choices, correct_choice

    def _parse_fill_blank_response(self, content: str) -> tuple[str, str]:
        """Parse AI response for fill-in-the-blank content.

        Returns:
            Tuple of (sentence_with_blank, hint)
        """
        sentence = ""
        hint = ""

        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()

            if line.startswith("SENTENCE:"):
                sentence = line.split(":", 1)[1].strip()
            elif line.startswith("HINT:"):
                hint = line.split(":", 1)[1].strip()

        return sentence, hint

    def export_to_apkg(
        self, cards: list[AnkiCard], deck_name: str, output_path: str | Path
    ) -> bool:
        """Export cards to Anki .apkg file format.

        Args:
            cards: List of cards to export
            deck_name: Name of the Anki deck
            output_path: Path to save the .apkg file

        Returns:
            True if export successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create deck and models for different card types
            deck_id = self._generate_deck_id(deck_name)
            deck = genanki.Deck(deck_id, deck_name)

            # Create models for each card type
            models = {}
            for card in cards:
                card_type = card.card_type
                if card_type not in models:
                    models[card_type] = self._create_genanki_model(card_type, card.template)

            # Add notes to deck
            for card in cards:
                note = self._create_genanki_note(card, models[card.card_type])
                deck.add_note(note)

            # Create package and write to file
            package = genanki.Package(deck)
            package.write_to_file(str(output_path.with_suffix(".apkg")))

            # Also create HTML preview
            html_content = self._generate_html_preview(cards, deck_name)
            with open(output_path.with_suffix(".html"), "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.success(f"Exported {len(cards)} cards to {output_path.with_suffix('.apkg')}")
            logger.info(f"HTML preview available at {output_path.with_suffix('.html')}")
            return True

        except Exception as e:
            logger.error(f"Error exporting cards: {e}")
            return False

    def _generate_html_preview(self, cards: list[AnkiCard], deck_name: str) -> str:
        """Generate HTML preview of the cards."""
        html_parts = [
            "<!DOCTYPE html>",
            f"<html><head><title>{deck_name} - Flashcard Preview</title>",
            "<meta charset='utf-8'>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }",
            ".card-container { margin-bottom: 40px; }",
            ".card-side { margin-bottom: 20px; }",
            ".card-label { font-weight: bold; margin-bottom: 10px; }",
            "</style>",
            "</head><body>",
            f"<h1>{deck_name}</h1>",
            f"<p>Total cards: {len(cards)}</p>",
        ]

        for i, card in enumerate(cards, 1):
            html_parts.extend(
                [
                    "<div class='card-container'>",
                    f"<h2>Card {i} ({card.card_type.value})</h2>",
                    "<div class='card-side'>",
                    "<div class='card-label'>Front:</div>",
                    f"<style>{card.template.css_styles}</style>",
                    card.render_front(),
                    "</div>",
                    "<div class='card-side'>",
                    "<div class='card-label'>Back:</div>",
                    card.render_back(),
                    "</div>",
                    "</div>",
                ]
            )

        html_parts.extend(["</body></html>"])

        return "\n".join(html_parts)

    def _generate_deck_id(self, deck_name: str) -> int:
        """Generate a unique deck ID from deck name."""
        # Create a hash of the deck name and convert to int
        hash_obj = hashlib.md5(deck_name.encode("utf-8"))
        # Use first 8 bytes of hash as deck ID (must be positive)
        return int.from_bytes(hash_obj.digest()[:8], "big", signed=False) % (2**31 - 1)

    def _create_genanki_model(
        self, card_type: CardType, template: AnkiCardTemplate
    ) -> genanki.Model:
        """Create a genanki model for the given card type."""
        model_id = self._generate_model_id(card_type)

        # Create fields for the model
        fields = [{"name": field} for field in template.fields]

        # Create templates for front and back
        templates = [
            {
                "name": f"{card_type.value.title()} Card",
                "qfmt": template.front_template,
                "afmt": template.back_template,
            }
        ]

        # Add CSS and JavaScript
        css = template.css_styles
        if template.javascript:
            css += f"\\n<script>\\n{template.javascript}\\n</script>"

        return genanki.Model(
            model_id,
            f"Floridify {card_type.value.title()}",
            fields=fields,
            templates=templates,
            css=css,
        )

    def _generate_model_id(self, card_type: CardType) -> int:
        """Generate a unique model ID for the card type."""
        # Create consistent IDs for each card type
        type_ids = {
            CardType.MULTIPLE_CHOICE: 1234567890,
            CardType.FILL_IN_BLANK: 1234567891,
            CardType.DEFINITION_TO_WORD: 1234567892,
            CardType.WORD_TO_DEFINITION: 1234567893,
        }
        return type_ids.get(card_type, 1234567899)

    def _create_genanki_note(self, card: AnkiCard, model: genanki.Model) -> genanki.Note:
        """Create a genanki note from an AnkiCard."""
        # Convert card fields to list in the order expected by the model
        field_values = []
        for field_info in model.fields:
            field_name = field_info["name"]
            field_value = card.fields.get(field_name, "")

            # Handle list fields
            if isinstance(field_value, list):
                if field_value:  # Only join if list has items
                    field_value = " | ".join(str(item) for item in field_value)
                else:
                    field_value = ""

            field_values.append(str(field_value))

        return genanki.Note(
            model=model,
            fields=field_values,
        )
