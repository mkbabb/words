"""Data loading services to reduce duplication across routers."""

from typing import Any, TypeVar

from beanie import Document

from ...models.base import AudioMedia, ImageMedia
from ...models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Example,
    Pronunciation,
    Word,
)
from ...models.richness import compute_entry_richness
from ...utils.language_precedence import to_language_codes

T = TypeVar("T", bound=Document)


class DataLoader:
    """Base class for data loading operations."""

    @staticmethod
    async def load_by_ids(model_class: type[T], ids: list[Any]) -> list[T]:
        """Load multiple documents by IDs efficiently using batch query."""
        if not ids:
            return []

        docs = await model_class.find({"_id": {"$in": ids}}).to_list()
        # Preserve original ordering
        doc_map = {doc.id: doc for doc in docs}
        return [doc_map[did] for did in ids if did in doc_map]


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
        pron_dict = pronunciation.model_dump(mode="json", exclude={"id", "word_id"})

        # Load and transform audio files (batch query)
        audio_files = []
        if pron_dict.get("audio_file_ids"):
            audios = await DataLoader.load_by_ids(AudioMedia, pron_dict["audio_file_ids"])
            for audio in audios:
                audio_dict = audio.model_dump(mode="json", exclude={"id"})
                if audio_dict.get("url", "").startswith("/"):
                    audio_dict["url"] = f"/api/v1/audio/{audio.id!s}/content"
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
        _provider_data_cache: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Load definition with all related data resolved.

        Args:
            definition: The definition document
            include_examples: Whether to load example data
            include_images: Whether to load image data
            include_provider_data: Whether to include provider data
            provider_data_ids: Provider data IDs to load (for shared provider data)
            _provider_data_cache: Pre-loaded provider data dicts (avoids N+1 re-fetch)

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
                definition.meaning_cluster.model_dump(mode="json")
                if definition.meaning_cluster
                else None
            ),
            "sense_number": definition.sense_number,
            "word_forms": [wf.model_dump(mode="json") for wf in definition.word_forms],
            "synonyms": definition.synonyms,
            "antonyms": definition.antonyms,
            "language_register": definition.language_register,
            "domain": definition.domain,
            "region": definition.region,
            "usage_notes": [un.model_dump(mode="json") for un in definition.usage_notes],
            "grammar_patterns": [gp.model_dump(mode="json") for gp in definition.grammar_patterns],
            "collocations": [c.model_dump(mode="json") for c in definition.collocations],
            "transitivity": definition.transitivity,
            "cefr_level": definition.cefr_level,
            "frequency_band": definition.frequency_band,
        }

        # Load examples (batch query)
        if include_examples and definition.example_ids:
            examples = await DataLoader.load_by_ids(Example, definition.example_ids)
            def_dict["examples"] = [e.model_dump(mode="json") for e in examples]
        else:
            def_dict["examples"] = []

        # Load images (batch query)
        if include_images and definition.image_ids:
            images = await DataLoader.load_by_ids(ImageMedia, definition.image_ids)
            def_dict["images"] = [
                img.model_dump(mode="json", exclude={"data"}) for img in images
            ]
        else:
            def_dict["images"] = []

        # Use pre-loaded provider data if available, otherwise load
        if include_provider_data and provider_data_ids:
            if _provider_data_cache is not None:
                def_dict["providers_data"] = _provider_data_cache
            else:
                providers = await DataLoader.load_by_ids(DictionaryEntry, provider_data_ids)
                def_dict["providers_data"] = [
                    p.model_dump(mode="json", exclude={"id"}) for p in providers
                ]
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
                provider_data = await DictionaryEntry.get(provider_id)
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


class DictionaryEntryLoader(DataLoader):
    """Service for loading DictionaryEntry synthesis and converting to API response."""

    @staticmethod
    async def load_as_lookup_response(
        entry: DictionaryEntry,
    ) -> dict[str, Any]:
        """Load a DictionaryEntry and convert to LookupResponse format.

        Args:
            entry: The synthesized dictionary entry to load
            include_provider_data: Whether to include provider data in definitions

        Returns:
            Dictionary ready to be used as LookupResponse

        """
        # Load word
        word_obj = await Word.get(entry.word_id)
        if not word_obj:
            raise ValueError(f"Word not found for ID: {entry.word_id}")

        # Load provider (non-synthesis) DictionaryEntry documents for this word
        provider_entries = await DictionaryEntry.find(
            DictionaryEntry.word_id == entry.word_id,
            DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
        ).to_list()
        provider_entry_ids = [str(pe.id) for pe in provider_entries] if provider_entries else None

        # Pre-serialize provider data once (avoids N+1 re-fetch per definition)
        provider_data_cache: list[dict[str, Any]] | None = None
        if provider_entry_ids:
            provider_data_cache = [
                pe.model_dump(mode="json", exclude={"id"}) for pe in provider_entries
            ]

        # Batch-load all definitions in one query, then resolve relations
        definitions = []
        all_defs: list[Definition] = []
        if entry.definition_ids:
            all_defs = await DataLoader.load_by_ids(Definition, entry.definition_ids)
            for definition in all_defs:
                def_dict = await DefinitionLoader.load_with_relations(
                    definition=definition,
                    include_examples=True,
                    include_images=True,
                    include_provider_data=True,
                    provider_data_ids=provider_entry_ids,
                    _provider_data_cache=provider_data_cache,
                )
                definitions.append(def_dict)

        # Load pronunciation with audio files
        pronunciation = None
        if entry.pronunciation_id:
            pronunciation = await PronunciationLoader.load_with_audio(str(entry.pronunciation_id))

        # Load images for the synth entry itself (batch query)
        images = []
        if entry.image_ids:
            image_docs = await DataLoader.load_by_ids(ImageMedia, entry.image_ids)
            images = [img.model_dump(mode="json", exclude={"data"}) for img in image_docs]

        # Build the response dictionary from canonical Word language precedence.
        response_languages = to_language_codes(list(word_obj.languages))
        if not response_languages:
            raise ValueError(
                f"Word '{word_obj.id}' is missing languages. "
                "Migration is required to provide a non-empty languages list.",
            )

        # Compute richness score (reuses already-loaded definitions)
        richness_score = compute_entry_richness(entry, all_defs)

        return {
            "word": word_obj.text,
            "languages": response_languages,
            "pronunciation": pronunciation,
            "definitions": definitions,
            "etymology": (entry.etymology.model_dump(mode="json") if entry.etymology else None),
            "last_updated": entry.updated_at,
            "model_info": (entry.model_info.model_dump(mode="json") if entry.model_info else None),
            "id": str(entry.id),
            "images": images,
            "richness_score": richness_score,
        }
