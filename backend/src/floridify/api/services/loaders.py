"""Data loading services to reduce duplication across routers."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ...models import AudioMedia, Definition, Example, ImageMedia, Pronunciation, ProviderData


class DataLoader:
    """Base class for data loading operations."""
    
    @staticmethod
    async def load_by_ids(model_class: type, ids: list[str]) -> list[Any]:
        """Load multiple documents by IDs efficiently."""
        if not ids:
            return []
        
        documents = []
        for doc_id in ids:
            doc = await model_class.get(doc_id)
            if doc:
                documents.append(doc)
        return documents


class PronunciationLoader(DataLoader):
    """Service for loading pronunciation data with related audio files."""
    
    @staticmethod
    async def load_with_audio(pronunciation_id: str | None) -> dict[str, Any] | None:
        """Load pronunciation with fully resolved audio file information."""
        if not pronunciation_id:
            return None
        
        pronunciation = await Pronunciation.get(pronunciation_id)
        if not pronunciation:
            return None
        
        # Convert to dict
        pron_dict = pronunciation.model_dump(exclude={"id"})
        
        # Load and transform audio files
        audio_files = []
        if pronunciation.audio_file_ids:
            for audio_id in pronunciation.audio_file_ids:
                audio = await AudioMedia.get(audio_id)
                if audio:
                    audio_dict = audio.model_dump(exclude={"id"})
                    # Convert file path to API URL
                    if audio_dict.get("url", "").startswith("/"):
                        audio_dict["url"] = f"/api/v1/audio/files/{audio_id}"
                    audio_files.append(audio_dict)
        
        pron_dict["audio_files"] = audio_files
        return pron_dict


class DefinitionLoader(DataLoader):
    """Service for loading definition data with related entities."""
    
    @staticmethod
    async def load_with_relations(
        definition: Definition,
        include_examples: bool = True,
        include_images: bool = True,
        include_provider_data: bool = True,
        provider_data_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load definition with all related data resolved.
        
        Args:
            definition: The definition document
            include_examples: Whether to load example data
            include_images: Whether to load image data
            include_provider_data: Whether to include provider data
            provider_data_ids: Provider data IDs to load (for shared provider data)
            
        Returns:
            Dictionary with fully resolved definition data
        """
        # Start with base definition data
        def_dict = {
            "id": str(definition.id),
            "created_at": definition.created_at,
            "updated_at": definition.updated_at,
            "version": definition.version,
            "part_of_speech": definition.part_of_speech,
            "text": definition.text,
            "meaning_cluster": (
                definition.meaning_cluster.model_dump() 
                if definition.meaning_cluster else None
            ),
            "sense_number": definition.sense_number,
            "word_forms": [wf.model_dump() for wf in definition.word_forms],
            "synonyms": definition.synonyms,
            "antonyms": definition.antonyms,
            "language_register": definition.language_register,
            "domain": definition.domain,
            "region": definition.region,
            "usage_notes": [un.model_dump() for un in definition.usage_notes],
            "grammar_patterns": [gp.model_dump() for gp in definition.grammar_patterns],
            "collocations": [c.model_dump() for c in definition.collocations],
            "transitivity": definition.transitivity,
            "cefr_level": definition.cefr_level,
            "frequency_band": definition.frequency_band,
        }
        
        # Load examples if requested
        if include_examples and definition.example_ids:
            examples = []
            for example_id in definition.example_ids:
                example = await Example.get(example_id)
                if example:
                    examples.append(example.model_dump(mode='json'))
            def_dict["examples"] = examples
        else:
            def_dict["examples"] = []
        
        # Load images if requested
        if include_images and definition.image_ids:
            images = []
            for image_id in definition.image_ids:
                image = await ImageMedia.get(image_id)
                if image:
                    images.append(image.model_dump(mode='json', exclude={'data'}))
            def_dict["images"] = images
        else:
            def_dict["images"] = []
        
        # Load provider data if requested
        if include_provider_data and provider_data_ids:
            providers_data = []
            for provider_id in provider_data_ids:
                provider_data = await ProviderData.get(provider_id)
                if provider_data:
                    providers_data.append(provider_data.model_dump(exclude={"id"}))
            def_dict["providers_data"] = providers_data
        else:
            def_dict["providers_data"] = []
        
        return def_dict
    
    @staticmethod
    async def load_multiple_with_relations(
        definitions: list[Definition],
        provider_data_ids: list[str] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Load multiple definitions with relations.
        
        This method efficiently loads shared provider data once and passes it
        to each definition loader.
        """
        # Load provider data once if provided
        if provider_data_ids:
            # Pre-load all provider data
            provider_data_cache = {}
            for provider_id in provider_data_ids:
                provider_data = await ProviderData.get(provider_id)
                if provider_data:
                    provider_data_cache[provider_id] = provider_data
        
        # Load each definition
        loaded_definitions = []
        for definition in definitions:
            def_dict = await DefinitionLoader.load_with_relations(
                definition=definition,
                provider_data_ids=provider_data_ids,
                **kwargs,
            )
            loaded_definitions.append(def_dict)
        
        return loaded_definitions