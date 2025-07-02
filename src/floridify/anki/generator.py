"""Anki flashcard generator for dictionary entries."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import genanki  # type: ignore[import-untyped]

from ..ai.connector import OpenAIConnector
from ..ai.templates import PromptTemplateManager as PromptLoader
from ..models import Definition, DictionaryEntry, SynthesizedDictionaryEntry
from ..utils.logging import get_logger
from .ankiconnect import AnkiDirectIntegration
from .templates import AnkiCardTemplate, CardType

logger = get_logger(__name__)



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
        self.direct_integration = AnkiDirectIntegration()

    async def generate_cards(
        self,
        entry: DictionaryEntry | SynthesizedDictionaryEntry,
        card_types: list[CardType] | None = None,
        max_cards_per_type: int = 1,
    ) -> list[AnkiCard]:
        """Generate flashcards for a dictionary entry.

        Args:
            entry: Dictionary entry to create cards for
            card_types: Types of cards to generate (default: all types)
            max_cards_per_type: Maximum cards per type to generate

        Returns:
            List of generated Anki cards
        """
        import time
        start_time = time.time()
        
        logger.info(f"🎴 Starting card generation for word: '{entry.word.text}'")
        if card_types is None:
            card_types = [CardType.MULTIPLE_CHOICE, CardType.FILL_IN_BLANK]
        
        logger.debug(
            f"Card types: {[ct.value for ct in card_types]}, max per type: {max_cards_per_type}"
        )
        cards: list[Any] = []

        # Get definitions based on entry type
        if isinstance(entry, SynthesizedDictionaryEntry):
            # SynthesizedDictionaryEntry has definitions directly
            definitions = entry.definitions
        else:
            # DictionaryEntry has providers with definitions
            ai_provider = entry.providers.get("ai_synthesis")
            if ai_provider and ai_provider.definitions:
                definitions = ai_provider.definitions
            else:
                # Collect definitions from all providers
                definitions = []
                for provider_data in entry.providers.values():
                    definitions.extend(provider_data.definitions)

        if not definitions:
            logger.warning(f"📛 No definitions found for word: '{entry.word.text}'")
            return cards

        logger.debug(f"📖 Found {len(definitions)} definitions for '{entry.word.text}'")

        # Generate cards for each requested type
        for card_type in card_types:
            type_start_time = time.time()
            logger.info(f"⚡ Generating {card_type.value} cards for '{entry.word.text}'")
            type_cards = []

            for i, definition in enumerate(definitions[:max_cards_per_type]):
                try:
                    def_start_time = time.time()
                    logger.debug(f"🔨 Creating {card_type.value} card {i+1}/{min(max_cards_per_type, len(definitions))}")
                    
                    if card_type == CardType.MULTIPLE_CHOICE:
                        card = await self._generate_multiple_choice_card(entry, definition)
                    elif card_type == CardType.FILL_IN_BLANK:
                        card = await self._generate_fill_blank_card(entry, definition)
                    else:
                        logger.warning(f"⚠️ Unsupported card type: {card_type.value}")
                        continue  # Skip unsupported card types

                    if card:
                        type_cards.append(card)
                        def_elapsed = time.time() - def_start_time
                        logger.debug(f"✅ Created {card_type.value} card in {def_elapsed:.2f}s")
                    else:
                        logger.warning(f"❌ Failed to create {card_type.value} card")

                except Exception as e:
                    logger.error(
                        f"💥 Error generating {card_type.value} card for {entry.word.text}: {e}"
                    )
                    continue

            type_elapsed = time.time() - type_start_time
            logger.info(f"🎯 Generated {len(type_cards)} {card_type.value} cards in {type_elapsed:.2f}s")
            cards.extend(type_cards)

        total_elapsed = time.time() - start_time
        logger.info(f"🏁 Generated {len(cards)} total cards for '{entry.word.text}' in {total_elapsed:.2f}s")
        return cards

    async def _generate_multiple_choice_card(
        self, entry: DictionaryEntry | SynthesizedDictionaryEntry, definition: Definition
    ) -> AnkiCard | None:
        """Generate a multiple choice flashcard."""
        try:
            import time
            start_time = time.time()
            
            logger.debug(f"🧠 Generating multiple choice AI content for '{entry.word.text}'")
            
            # Prepare examples for the prompt
            examples_text = ""
            if definition.examples.generated:
                examples_list = [ex.sentence for ex in definition.examples.generated[:3]]
                examples_text = " | ".join(examples_list)
                logger.debug(f"📝 Using {len(examples_list)} examples for context")

            # Generate multiple choice content using structured output
            ai_start_time = time.time()
            ai_response = await self.openai_connector.generate_anki_multiple_choice(
                word=entry.word.text,
                definition=definition.definition,
                word_type=definition.word_type.value,
                examples=examples_text,
            )
            ai_elapsed = time.time() - ai_start_time
            logger.debug(f"🤖 OpenAI multiple choice generation took {ai_elapsed:.2f}s")

            # Format examples and synonyms as strings
            examples_text = ""
            if definition.examples.generated:
                examples_list = [ex.sentence for ex in definition.examples.generated[:3]]
                examples_text = " • ".join(examples_list)
            
            synonyms_text = ""
            if definition.synonyms:
                synonyms_list = [syn.word.text for syn in definition.synonyms[:5]]
                synonyms_text = ", ".join(synonyms_list)
            
            # Prepare card fields
            fields = {
                "Word": entry.word.text,
                "Pronunciation": entry.pronunciation.phonetic or f"/{entry.word.text}/",
                "ChoiceA": ai_response.choice_a,
                "ChoiceB": ai_response.choice_b,
                "ChoiceC": ai_response.choice_c,
                "ChoiceD": ai_response.choice_d,
                "CorrectChoice": ai_response.correct_choice,
                "Definition": definition.definition,
                "Examples": examples_text,
                "Synonyms": synonyms_text,
            }

            # Get card template
            template_start_time = time.time()
            card_template = AnkiCardTemplate.get_multiple_choice_template()
            template_elapsed = time.time() - template_start_time
            
            total_elapsed = time.time() - start_time
            logger.debug(f"📋 Multiple choice card creation completed in {total_elapsed:.2f}s (template: {template_elapsed:.3f}s)")

            return AnkiCard(CardType.MULTIPLE_CHOICE, fields, card_template)

        except Exception as e:
            logger.error(f"💥 Error generating multiple choice card for '{entry.word.text}': {e}")
            return None

    async def _generate_fill_blank_card(
        self, entry: DictionaryEntry | SynthesizedDictionaryEntry, definition: Definition
    ) -> AnkiCard | None:
        """Generate a fill-in-the-blank flashcard."""
        try:
            import time
            start_time = time.time()
            
            logger.debug(f"📝 Generating fill-in-blank AI content for '{entry.word.text}'")
            
            # Prepare examples for the prompt
            examples_text = ""
            if definition.examples.generated:
                examples_list = [ex.sentence for ex in definition.examples.generated[:3]]
                examples_text = " | ".join(examples_list)
                logger.debug(f"📚 Using {len(examples_list)} examples for context")

            # Generate fill-in-the-blank content using structured output
            ai_start_time = time.time()
            ai_response = await self.openai_connector.generate_anki_fill_blank(
                word=entry.word.text,
                definition=definition.definition,
                word_type=definition.word_type.value,
                examples=examples_text,
            )
            ai_elapsed = time.time() - ai_start_time
            logger.debug(f"🤖 OpenAI fill-in-blank generation took {ai_elapsed:.2f}s")

            # Create complete sentence by replacing blank with highlighted word
            complete_sentence = ai_response.sentence.replace(
                "_____", f'<span class="word-highlight">{entry.word.text}</span>'
            )

            # Prepare card fields
            fields = {
                "Word": entry.word.text,
                "Pronunciation": entry.pronunciation.phonetic or f"/{entry.word.text}/",
                "SentenceWithBlank": ai_response.sentence,
                "WordType": definition.word_type.value,
                "Hint": ai_response.hint or "",
                "CompleteSentence": complete_sentence,
                "Definition": definition.definition,
            }

            # Get card template
            template_start_time = time.time()
            card_template = AnkiCardTemplate.get_fill_in_blank_template()
            template_elapsed = time.time() - template_start_time
            
            total_elapsed = time.time() - start_time
            logger.debug(f"📋 Fill-in-blank card creation completed in {total_elapsed:.2f}s (template: {template_elapsed:.3f}s)")

            return AnkiCard(CardType.FILL_IN_BLANK, fields, card_template)

        except Exception as e:
            logger.error(f"💥 Error generating fill-in-blank card for '{entry.word.text}': {e}")
            return None


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
            import time
            start_time = time.time()
            
            logger.info(f"📦 Starting .apkg export: {len(cards)} cards to '{deck_name}'")
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"💾 Output path: {output_path.with_suffix('.apkg')}")

            # Create deck and models for different card types
            deck_creation_start = time.time()
            deck_id = self._generate_deck_id(deck_name)
            deck = genanki.Deck(deck_id, deck_name)
            deck_creation_elapsed = time.time() - deck_creation_start
            logger.debug(f"🏗️ Created deck in {deck_creation_elapsed:.3f}s")

            # Create models for each card type
            model_creation_start = time.time()
            models = {}
            card_type_counts = {}
            for card in cards:
                card_type = card.card_type
                card_type_counts[card_type.value] = card_type_counts.get(card_type.value, 0) + 1
                if card_type not in models:
                    models[card_type] = self._create_genanki_model(card_type, card.template)
            
            model_creation_elapsed = time.time() - model_creation_start
            logger.debug(f"🔧 Created {len(models)} models in {model_creation_elapsed:.3f}s")
            logger.debug(f"📊 Card distribution: {card_type_counts}")

            # Add notes to deck
            note_creation_start = time.time()
            for i, card in enumerate(cards):
                note = self._create_genanki_note(card, models[card.card_type])
                deck.add_note(note)
                if (i + 1) % 10 == 0:
                    logger.debug(f"📝 Added {i + 1}/{len(cards)} notes to deck")
            
            note_creation_elapsed = time.time() - note_creation_start
            logger.debug(f"📋 Added {len(cards)} notes in {note_creation_elapsed:.3f}s")

            # Create package and write to file
            package_start = time.time()
            package = genanki.Package(deck)
            package.write_to_file(str(output_path.with_suffix(".apkg")))
            package_elapsed = time.time() - package_start
            logger.debug(f"📦 Created .apkg package in {package_elapsed:.3f}s")

            # Also create HTML preview
            html_start = time.time()
            html_content = self._generate_html_preview(cards, deck_name)
            with open(output_path.with_suffix(".html"), "w", encoding="utf-8") as f:
                f.write(html_content)
            html_elapsed = time.time() - html_start
            logger.debug(f"🌐 Created HTML preview in {html_elapsed:.3f}s")

            total_elapsed = time.time() - start_time
            logger.success(f"✅ Exported {len(cards)} cards to {output_path.with_suffix('.apkg')} in {total_elapsed:.2f}s")
            logger.info(f"📄 HTML preview available at {output_path.with_suffix('.html')}")
            return output_path.with_suffix('.apkg')

        except Exception as e:
            logger.error(f"💥 Error exporting cards to .apkg: {e}")
            return None

    def export_directly_to_anki(
        self,
        cards: list[AnkiCard],
        deck_name: str,
        fallback_to_apkg: bool = True,
        output_path: Path | None = None,
    ) -> tuple[bool, Path | None]:
        """Export cards directly to Anki via AnkiConnect, with .apkg fallback.
        
        Args:
            cards: List of AnkiCard objects to export
            deck_name: Name of the target Anki deck
            fallback_to_apkg: Whether to create .apkg file if direct export fails
            output_path: Optional path for .apkg fallback (auto-generated if None)
            
        Returns:
            Tuple of (success, apkg_path). Success is True if cards were added to Anki
            directly, apkg_path is provided if .apkg was created as fallback.
        """
        import time
        start_time = time.time()
        
        logger.info(f"🚀 Attempting direct export of {len(cards)} cards to Anki deck '{deck_name}'")
        
        # Try direct export first
        if self.direct_integration.is_available():
            success = self.direct_integration.export_cards_directly(cards, deck_name)
            
            if success:
                total_time = time.time() - start_time
                logger.success(f"✅ Cards exported directly to Anki in {total_time:.2f}s")
                return True, None
            else:
                logger.warning("⚠️ Direct export failed, falling back to .apkg")
        else:
            logger.info("📦 AnkiConnect not available, using .apkg export")
        
        # Fallback to .apkg export
        if fallback_to_apkg:
            if output_path is None:
                output_path = Path.cwd() / f"{deck_name.replace(' ', '_')}"
            
            apkg_path = self.export_to_apkg(cards, output_path)
            
            if apkg_path is None:
                logger.error("💥 .apkg export also failed")
                return False, None
            
            # If AnkiConnect is available, try to import the .apkg directly
            if self.direct_integration.is_available():
                logger.info("🔄 Attempting to import .apkg directly into Anki")
                import_success = self.direct_integration.import_apkg_directly(apkg_path)
                
                if import_success:
                    total_time = time.time() - start_time
                    logger.success(f"✅ .apkg imported directly to Anki in {total_time:.2f}s")
                    return True, apkg_path
                else:
                    logger.warning("⚠️ Direct .apkg import failed")
            
            total_time = time.time() - start_time
            logger.info(f"📦 Created .apkg file in {total_time:.2f}s: {apkg_path}")
            return False, apkg_path
        
        logger.error("💥 All export methods failed")
        return False, None

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
