"""AnkiConnect interface for direct Anki integration on macOS."""

from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


class AnkiConnectError(Exception):
    """Exception raised when AnkiConnect operations fail."""
    pass


class AnkiConnectInterface:
    """Interface for communicating with Anki via AnkiConnect add-on."""
    
    def __init__(self, url: str = "http://localhost:8765") -> None:
        """Initialize AnkiConnect interface.
        
        Args:
            url: AnkiConnect server URL (default: localhost:8765)
        """
        self.url = url
        self._is_available: bool | None = None
        
    def is_available(self) -> bool:
        """Check if AnkiConnect is available and Anki is running."""
        if self._is_available is not None:
            return self._is_available
            
        try:
            result = self.invoke("version")
            self._is_available = result is not None
            if self._is_available:
                logger.info(f"🔌 AnkiConnect available (version: {result})")
            return self._is_available
        except Exception as e:
            logger.debug(f"AnkiConnect not available: {e}")
            self._is_available = False
            return False
    
    def invoke(self, action: str, **params: Any) -> Any:
        """Send command to AnkiConnect.
        
        Args:
            action: AnkiConnect action to perform
            **params: Parameters for the action
            
        Returns:
            Result from AnkiConnect
            
        Raises:
            AnkiConnectError: If the request fails or returns an error
        """
        import time
        start_time = time.time()
        
        request_data = {
            "action": action,
            "params": params,
            "version": 6
        }
        
        try:
            request_json = json.dumps(request_data).encode("utf-8")
            request = urllib.request.Request(self.url, request_json)
            request.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.load(response)
            
            elapsed = time.time() - start_time
            logger.debug(f"🔌 AnkiConnect {action} completed in {elapsed:.3f}s")
            
            if response_data.get("error"):
                raise AnkiConnectError(f"AnkiConnect error: {response_data['error']}")
                
            return response_data.get("result")
            
        except urllib.error.URLError as e:
            raise AnkiConnectError(f"Failed to connect to AnkiConnect: {e}")
        except json.JSONDecodeError as e:
            raise AnkiConnectError(f"Invalid JSON response from AnkiConnect: {e}")
        except Exception as e:
            raise AnkiConnectError(f"AnkiConnect request failed: {e}")
    
    def get_deck_names(self) -> list[str]:
        """Get all deck names from Anki."""
        return self.invoke("deckNames")  # type: ignore[no-any-return]
    
    def create_deck(self, deck_name: str) -> bool:
        """Create a new deck in Anki.
        
        Args:
            deck_name: Name of the deck to create
            
        Returns:
            True if successful
        """
        try:
            self.invoke("createDeck", deck=deck_name)
            logger.debug(f"📁 Created deck: '{deck_name}'")
            return True
        except AnkiConnectError:
            # Deck might already exist
            return False
    
    def add_note(self, deck_name: str, model_name: str, fields: dict[str, str], 
                tags: list[str] | None = None) -> int | None:
        """Add a note to Anki.
        
        Args:
            deck_name: Target deck name
            model_name: Note type/model name
            fields: Field values for the note
            tags: Optional tags to add
            
        Returns:
            Note ID if successful, None otherwise
        """
        note_data = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags or []
        }
        
        try:
            note_id = self.invoke("addNote", note=note_data)
            logger.debug(f"📝 Added note {note_id} to deck '{deck_name}'")
            return note_id  # type: ignore[no-any-return]
        except AnkiConnectError as e:
            # If duplicate, try to find and update existing note
            if "duplicate" in str(e).lower():
                logger.debug(f"🔄 Attempting to update duplicate note in '{deck_name}'")
                return self._handle_duplicate_note(deck_name, model_name, fields, tags)
            else:
                logger.warning(f"Failed to add note to '{deck_name}': {e}")
                return None
    
    def _handle_duplicate_note(self, deck_name: str, model_name: str, 
                              fields: dict[str, str], tags: list[str] | None = None) -> int | None:
        """Handle duplicate notes by finding and updating existing ones."""
        try:
            # Try to find existing notes with similar content
            # Search for notes in the deck with matching first field (usually the front)
            first_field_value = next(iter(fields.values())) if fields else ""
            
            # Use AnkiConnect's findNotes to search for existing notes
            query = f'deck:"{deck_name}" {first_field_value}'
            note_ids = self.invoke("findNotes", query=query)
            
            if note_ids:
                # Update the first matching note
                note_id = note_ids[0]
                self.invoke("updateNoteFields", note={
                    "id": note_id,
                    "fields": fields
                })
                
                # Update tags if provided
                if tags:
                    self.invoke("updateNoteTags", note=note_id, tags=" ".join(tags))
                
                logger.debug(f"🔄 Updated existing note {note_id} in deck '{deck_name}'")
                return note_id  # type: ignore[no-any-return]
            else:
                logger.warning(f"Could not find duplicate note to update in '{deck_name}'")
                return None
                
        except AnkiConnectError as e:
            logger.warning(f"Failed to handle duplicate note in '{deck_name}': {e}")
            return None
    
    def import_package(self, apkg_path: str | Path) -> bool:
        """Import an .apkg file directly into Anki.
        
        Args:
            apkg_path: Path to the .apkg file
            
        Returns:
            True if import successful
        """
        apkg_path = Path(apkg_path)
        if not apkg_path.exists():
            logger.error(f"📦 .apkg file not found: {apkg_path}")
            return False
            
        try:
            with open(apkg_path, "rb") as f:
                deck_data = f.read()
            
            # Convert to base64 for transport
            deck_b64 = base64.b64encode(deck_data).decode("utf-8")
            
            self.invoke("importPackage", path=deck_b64)
            logger.info(f"📦 Imported package: {apkg_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import package {apkg_path}: {e}")
            return False
    
    def sync(self) -> bool:
        """Trigger Anki sync."""
        try:
            self.invoke("sync")
            logger.debug("🔄 Triggered Anki sync")
            return True
        except AnkiConnectError as e:
            logger.warning(f"Sync failed: {e}")
            return False
    
    def get_model_names(self) -> list[str]:
        """Get all note type/model names."""
        return self.invoke("modelNames")  # type: ignore[no-any-return]
    
    def create_model(self, model_name: str, fields: list[str], 
                    css: str, front_template: str, back_template: str) -> bool:
        """Create a custom note model in Anki.
        
        Args:
            model_name: Name for the new model
            fields: List of field names
            css: CSS styles for the model
            front_template: Front card template
            back_template: Back card template
            
        Returns:
            True if successful
        """
        model_data = {
            "modelName": model_name,
            "inOrderFields": fields,
            "css": css,
            "cardTemplates": [
                {
                    "Name": "Card 1",
                    "Front": front_template,
                    "Back": back_template
                }
            ]
        }
        
        try:
            self.invoke("createModel", model=model_data)
            logger.debug(f"🎨 Created model: '{model_name}'")
            return True
        except AnkiConnectError as e:
            logger.warning(f"Failed to create model '{model_name}': {e}")
            return False


class AnkiDirectIntegration:
    """High-level interface for direct Anki integration."""
    
    def __init__(self) -> None:
        """Initialize direct Anki integration."""
        self.ankiconnect = AnkiConnectInterface()
        self._availability_checked = False
        
    def is_available(self) -> bool:
        """Check if direct Anki integration is available."""
        if not self._availability_checked:
            available = self.ankiconnect.is_available()
            self._availability_checked = True
            
            if available:
                logger.info("🚀 Direct Anki integration available via AnkiConnect")
            else:
                logger.info("📦 Direct integration unavailable - will use .apkg export")
                
        return self.ankiconnect.is_available()
    
    def export_cards_directly(self, cards: list[Any], deck_name: str) -> bool:
        """Export cards directly to running Anki instance.
        
        Args:
            cards: List of AnkiCard objects to export
            deck_name: Target deck name in Anki
            
        Returns:
            True if all cards were added successfully
        """
        if not self.is_available():
            return False
            
        import time
        start_time = time.time()
        
        logger.info(f"🚀 Starting direct export of {len(cards)} cards to Anki deck '{deck_name}'")
        
        try:
            # Ensure deck exists
            existing_decks = self.ankiconnect.get_deck_names()
            if deck_name not in existing_decks:
                self.ankiconnect.create_deck(deck_name)
                logger.info(f"📁 Created new deck: '{deck_name}'")
            
            # Create models for each card type if needed
            created_models = set()
            for card in cards:
                model_name = f"Floridify {card.card_type.value.title()}"
                if model_name not in created_models:
                    if self._ensure_model_exists(card, model_name):
                        created_models.add(model_name)
            
            # Add cards to Anki
            successful_cards = 0
            failed_cards = 0
            
            for i, card in enumerate(cards):
                try:
                    model_name = f"Floridify {card.card_type.value.title()}"
                    
                    # Convert fields to string values
                    string_fields = {}
                    for field_name, field_value in card.fields.items():
                        if isinstance(field_value, list):
                            string_fields[field_name] = " • ".join(str(item) for item in field_value)
                        else:
                            string_fields[field_name] = str(field_value) if field_value else ""
                    
                    note_id = self.ankiconnect.add_note(
                        deck_name=deck_name,
                        model_name=model_name,
                        fields=string_fields,
                        tags=["floridify", "auto-generated"]
                    )
                    
                    if note_id:
                        successful_cards += 1
                        if (i + 1) % 10 == 0:
                            logger.debug(f"📝 Added {i + 1}/{len(cards)} cards to Anki")
                    else:
                        failed_cards += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to add card {i + 1}: {e}")
                    failed_cards += 1
            
            # Trigger sync
            if successful_cards > 0:
                self.ankiconnect.sync()
            
            total_time = time.time() - start_time
            
            if failed_cards == 0:
                logger.success(f"✅ Successfully added all {successful_cards} cards to Anki in {total_time:.2f}s")
                return True
            else:
                logger.warning(f"⚠️ Added {successful_cards} cards, {failed_cards} failed in {total_time:.2f}s")
                return successful_cards > 0
                
        except Exception as e:
            logger.error(f"💥 Direct export failed: {e}")
            return False
    
    def _ensure_model_exists(self, card: Any, model_name: str) -> bool:
        """Ensure a model exists for the given card type."""
        try:
            existing_models = self.ankiconnect.get_model_names()
            if model_name in existing_models:
                return True
                
            # Create model with card template
            success = self.ankiconnect.create_model(
                model_name=model_name,
                fields=card.template.fields,
                css=card.template.css_styles,
                front_template=card.template.front_template,
                back_template=card.template.back_template
            )
            
            if success:
                logger.info(f"🎨 Created Anki model: '{model_name}'")
            
            return success
            
        except Exception as e:
            logger.warning(f"Failed to ensure model '{model_name}' exists: {e}")
            return False
    
    def import_apkg_directly(self, apkg_path: str | Path) -> bool:
        """Import an .apkg file directly into Anki.
        
        Args:
            apkg_path: Path to the .apkg file
            
        Returns:
            True if import successful
        """
        if not self.is_available():
            return False
            
        return self.ankiconnect.import_package(apkg_path)