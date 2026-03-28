"""Local CEFR level assessment using frequency + sense prominence.

Word-level frequency gives the base CEFR. Sense-level prominence (from
WordNet SemCor) adjusts it: rare senses of common words get harder CEFR
levels. E.g., "bank" is A2 for the financial sense but B2-C1 for the
"ridge/pile" or "aircraft tilt" senses.
"""

from __future__ import annotations

from typing import Literal

from .frequency import (
    adjust_band_for_sense,
    assess_frequency_local,
    assess_sense_frequency,
)

CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]

_BAND_TO_CEFR: dict[int, CefrLevel] = {
    5: "A1",
    4: "A2",
    3: "B1",
    2: "B2",
    1: "C1",
}


async def assess_cefr_local(
    word: str,
    lang: str = "en",
    definition_text: str = "",
    part_of_speech: str = "",
) -> CefrLevel | None:
    """Assess CEFR level using word frequency + sense prominence.

    When definition_text is provided, adjusts for sense-level frequency:
    rare senses of common words get higher CEFR levels.

    Args:
        word: The word to assess.
        lang: ISO language code.
        definition_text: The specific definition text (for sense-level adjustment).
        part_of_speech: POS of the definition.

    Returns:
        CEFR level string, or None if assessment unavailable.
    """
    word_band = assess_frequency_local(word, lang)
    if word_band is None:
        return None

    # Adjust for sense prominence when definition context is available
    if definition_text and part_of_speech:
        sense_freq = await assess_sense_frequency(word, part_of_speech, definition_text)
        adjusted_band = adjust_band_for_sense(word_band, sense_freq)
    else:
        adjusted_band = word_band

    return _BAND_TO_CEFR.get(adjusted_band, "C2")
