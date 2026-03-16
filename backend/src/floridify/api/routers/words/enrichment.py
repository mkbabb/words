"""On-demand word enrichment endpoints.

Generate synonym chooser essays, phrases & idioms, and other enrichments
that are stored on the DictionaryEntry but generated lazily on request.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from ....ai.connector import get_ai_connector
from ....models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Phrase,
    SynonymChooser,
    Word,
)
from ....utils.logging import get_logger
from ...core import AdminDep

logger = get_logger(__name__)
router = APIRouter()


async def _get_synthesis_entry(word: str) -> tuple[DictionaryEntry, Word]:
    """Get the synthesized entry and word document for a word."""
    word_obj = await Word.find_one(Word.text == word)
    if not word_obj:
        raise HTTPException(status_code=404, detail=f"Word not found: {word}")

    entry = await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"No synthesized entry found for: {word}",
        )

    return entry, word_obj


@router.post("/{word}/synonym-chooser")
async def generate_synonym_chooser(
    word: str,
    _admin: AdminDep,
) -> dict[str, Any]:
    """Generate a comparative synonym essay for a word.

    Collects synonyms from all definitions, then generates a MW-style
    'Choose the Right Synonym' essay comparing them.
    """
    entry, word_obj = await _get_synthesis_entry(word)

    # Collect synonyms from all definitions
    all_synonyms: list[str] = []
    for def_id in entry.definition_ids:
        definition = await Definition.get(def_id)
        if definition and definition.synonyms:
            all_synonyms.extend(definition.synonyms)

    unique_synonyms = list(dict.fromkeys(all_synonyms))  # Deduplicate preserving order
    if len(unique_synonyms) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 synonyms for comparison, found {len(unique_synonyms)}",
        )

    ai = get_ai_connector()
    result = await ai.generate_synonym_chooser(word, unique_synonyms[:8])

    # Store on the entry
    entry.synonym_chooser = SynonymChooser(
        essay=result.essay,
        synonyms_compared=[
            {"word": s.word, "distinction": s.distinction}
            for s in result.synonyms_compared
        ],
        model_info=ai.last_model_info,
    )
    await entry.save()

    return {
        "word": word,
        "synonym_chooser": entry.synonym_chooser.model_dump(mode="json"),
    }


@router.post("/{word}/phrases")
async def generate_phrases(
    word: str,
    _admin: AdminDep,
) -> dict[str, Any]:
    """Generate phrases and idioms containing the word."""
    entry, word_obj = await _get_synthesis_entry(word)

    language = "English"
    if word_obj.languages:
        lang = word_obj.languages[0]
        lang_str = lang.value if hasattr(lang, "value") else str(lang)
        language_map = {"en": "English", "fr": "French", "es": "Spanish", "de": "German", "it": "Italian"}
        language = language_map.get(lang_str, "English")

    ai = get_ai_connector()
    result = await ai.generate_phrases(word, language)

    # Store on the entry
    entry.phrases = [
        Phrase(
            phrase=p.phrase,
            meaning=p.meaning,
            example=p.example,
            usage_register=p.register,
        )
        for p in result.phrases
    ]
    await entry.save()

    return {
        "word": word,
        "phrases": [p.model_dump(mode="json") for p in entry.phrases],
    }
