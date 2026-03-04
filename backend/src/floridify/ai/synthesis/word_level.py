"""Word-level synthesis functions: pronunciation, etymology, word forms, facts."""

from __future__ import annotations

from typing import Any, cast

from ...audio import get_audio_synthesizer
from ...core.state_tracker import Stages, StateTracker
from ...models import AudioMedia, Etymology
from ...models.dictionary import (
    Definition,
    DictionaryEntry,
    Fact,
    Pronunciation,
    Word,
)
from ...models.relationships import WordForm
from ...utils.logging import get_logger
from ..connector import OpenAIConnector

logger = get_logger(__name__)


async def synthesize_pronunciation(
    word: str,
    providers_data: list[dict[str, Any]] | list[DictionaryEntry],
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
    language: str = "en",
) -> Pronunciation | None:
    """Synthesize pronunciation: enhance existing or create new."""
    # Find existing pronunciation
    existing_pronunciation = await _find_existing_pronunciation(providers_data)

    if existing_pronunciation:
        return await _enhance_pronunciation(existing_pronunciation, word, ai, state_tracker, language)
    return await _create_pronunciation(word, ai, state_tracker, language)


async def _find_existing_pronunciation(
    providers_data: list[dict[str, Any]] | list[DictionaryEntry],
) -> Pronunciation | None:
    """Find existing pronunciation from provider data."""
    for provider in providers_data:
        if isinstance(provider, DictionaryEntry):
            if provider.pronunciation_id:
                pronunciation = await Pronunciation.get(provider.pronunciation_id)
                if pronunciation:
                    return pronunciation
        elif provider.get("pronunciation"):
            return cast("Pronunciation", provider["pronunciation"])
    return None


async def _enhance_pronunciation(
    pronunciation: Pronunciation,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None,
    language: str = "en",
) -> Pronunciation:
    """Enhance existing pronunciation with missing data."""
    needs_enhancement = not pronunciation.phonetic or not pronunciation.ipa

    if needs_enhancement:
        try:
            if state_tracker:
                await state_tracker.update(
                    stage=Stages.AI_SYNTHESIS,
                    message=f"Enhancing pronunciation for {word}",
                )

            response = await ai.pronunciation(word, language=language)
            pronunciation.phonetic = response.phonetic
            pronunciation.ipa = response.ipa
            await pronunciation.save()

        except Exception as e:
            logger.error(f"Failed to enhance pronunciation for {word}: {e}")

    # Generate audio if missing
    if not pronunciation.audio_file_ids:
        await _generate_audio_files(pronunciation, word, language)

    return pronunciation


async def _create_pronunciation(
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None,
    language: str = "en",
) -> Pronunciation | None:
    """Create new pronunciation from scratch."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating pronunciation for {word}",
            )

        response = await ai.pronunciation(word, language=language)

        # Create Word object if we need word_id (assuming word parameter should be Word object)
        word_obj = await Word.find_one(Word.text == word)
        if not word_obj:
            word_obj = Word(text=word)
            await word_obj.save()

        assert word_obj.id is not None  # After save(), id is guaranteed to be not None
        pronunciation = Pronunciation(
            word_id=word_obj.id,
            phonetic=response.phonetic,
            ipa=response.ipa,
        )
        await pronunciation.save()

        # Generate audio files
        await _generate_audio_files(pronunciation, word, language)

        return pronunciation

    except Exception as e:
        logger.error(f"Failed to create pronunciation for {word}: {e}")
        return None


async def _generate_audio_files(pronunciation: Pronunciation, word: str, language: str = "en") -> None:
    """Generate audio files for pronunciation and store as AudioMedia documents."""
    try:
        audio_synthesizer = get_audio_synthesizer()
        audio_results = await audio_synthesizer.synthesize_pronunciation(pronunciation, word, language=language)

        if audio_results:
            audio_ids = []
            for result in audio_results:
                audio_doc = AudioMedia(
                    url=result.url,
                    format=result.format,
                    size_bytes=result.size_bytes,
                    duration_ms=result.duration_ms,
                    accent=result.accent,
                    quality=result.quality,
                )
                await audio_doc.save()
                audio_ids.append(audio_doc.id)

            pronunciation.audio_file_ids = audio_ids
            await pronunciation.save()
            logger.info(f"Generated {len(audio_results)} audio files for {word}")

    except Exception as audio_error:
        logger.warning(f"Failed to generate audio for {word}: {audio_error}")


async def synthesize_etymology(
    word: Word,
    providers_data: list[dict[str, Any]] | list[DictionaryEntry],
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> Etymology | None:
    """Extract and synthesize etymology from provider data."""
    # Collect etymology data from providers
    etymology_data = []

    for provider in providers_data:
        if isinstance(provider, DictionaryEntry):
            # DictionaryEntry format
            if provider.etymology:
                etymology_data.append(
                    {
                        "name": provider.provider,  # Already a string due to use_enum_values=True
                        "etymology_text": provider.etymology.text,
                    },
                )
        # Dict format
        elif provider.get("etymology"):
            etymology_data.append(
                {
                    "name": provider["name"],
                    "etymology_text": provider["etymology"],
                },
            )

    if not etymology_data:
        return None

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Extracting etymology for {word.text}",
            )
        response = await ai.extract_etymology(word.text, etymology_data)
        return Etymology(
            text=response.text,
            origin_language=response.origin_language,
            root_words=response.root_words,
            first_known_use=response.first_known_use,
            model_info=ai.last_model_info,  # Set model info
        )
    except Exception as e:
        logger.error(f"Failed to synthesize etymology for {word.text}: {e}")
        return None


async def synthesize_word_forms(
    word: Word,
    part_of_speech: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[WordForm]:
    """Generate word forms for a word."""
    # Determine primary part of speech from definitions
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating word forms for {word.text}",
            )
        response = await ai.identify_word_forms(word.text, part_of_speech)
        return [
            WordForm(
                form_type=form.type,  # type:ignore
                text=form.text,
            )
            for form in response.forms
        ]
    except Exception as e:
        logger.error(f"Failed to synthesize word forms for {word.text}: {e}")
        return []


async def generate_facts(
    word: Word,
    definitions: list[Definition],
    ai: OpenAIConnector,
    count: int = 3,
    state_tracker: StateTracker | None = None,
) -> list[Fact]:
    """Generate interesting facts about a word."""
    # Use primary definition for context
    primary_def = definitions[0].text if definitions else ""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating facts for {word.text}",
            )
        response = await ai.generate_facts(
            word=word.text,
            definition=primary_def,
            count=count,
        )

        facts = []
        for idx, fact_text in enumerate(response.facts):
            # Determine category from response
            category = response.categories[idx] if idx < len(response.categories) else "general"

            # Ensure category is valid - map to allowed Fact categories
            category_mapping = {
                "general": "usage",
                "technical": "linguistic",
                "scientific": "linguistic",
                "cultural": "cultural",
                "etymology": "etymology",
                "historical": "historical",
                "usage": "usage",
                "linguistic": "linguistic",
            }
            category = category_mapping.get(category.lower(), "usage")

            assert word.id is not None  # Word should have been saved before calling this function
            fact = Fact(
                word_id=word.id,
                content=fact_text,
                category=category,  # type: ignore[arg-type]
                model_info=ai.last_model_info,  # Use full model info from AI connector
            )
            await fact.save()
            facts.append(fact)

        return facts
    except Exception as e:
        logger.error(f"Failed to synthesize facts for {word.text}: {e}")
        return []
