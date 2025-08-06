"""
Lexicon source configurations for comprehensive language dictionaries.

Contains verified, high-quality sources for English and French lexicons focusing
on comprehensive coverage with minimal duplication. Sources prioritized for
word game quality (Scrabble, linguistic corpora) and academic rigor.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...models.definition import Language
from .constants import LexiconFormat
from .scrapers.default import ScraperFunc, default_scraper
from .scrapers.wikipedia_french_expressions import scrape_french_expressions


class LexiconSourceConfig(BaseModel):
    """Configuration for a lexicon source."""

    name: str = Field(..., description="Unique identifier for the source")
    url: str = Field(default="", description="URL to download the lexicon data")
    format: LexiconFormat = Field(..., description="Data format for parsing")
    language: Language = Field(..., description="Language of the lexicon")
    description: str = Field(default="", description="Human-readable description")
    scraper: ScraperFunc = Field(
        default=default_scraper,
        description="Scraper function (default: simple GET)",
        exclude=True,
    )

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


# High-quality lexicon sources with verified URLs (January 2025)
# Quality over quantity - comprehensive, non-overlapping sources
LEXICON_SOURCES = [
    # English - Scrabble Quality Word Lists
    LexiconSourceConfig(
        name="sowpods_scrabble_words",
        url="https://raw.githubusercontent.com/jesstess/Scrabble/master/scrabble/sowpods.txt",
        format=LexiconFormat.TEXT_LINES,
        language=Language.ENGLISH,
        description="SOWPODS official Scrabble dictionary (~267k words, highest quality)",
    ),
    LexiconSourceConfig(
        name="google_10k_frequency",
        url="https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
        format=LexiconFormat.TEXT_LINES,
        language=Language.ENGLISH,
        description="10k most frequent English words from Google Trillion Word Corpus",
    ),
    # English - High-Quality Phrasal Verbs and Idioms
    LexiconSourceConfig(
        name="english_phrasal_verbs_comprehensive",
        url="https://raw.githubusercontent.com/vacancy/SceneGraphParser/master/sng_parser/_data/phrasal-verbs.txt",
        format=LexiconFormat.TEXT_LINES,
        language=Language.ENGLISH,
        description="~1000 comprehensive English phrasal verbs (academic quality)",
    ),
    LexiconSourceConfig(
        name="english_phrasal_verbs_detailed",
        url="https://raw.githubusercontent.com/Semigradsky/phrasal-verbs/master/common.json",
        format=LexiconFormat.JSON_PHRASAL_VERBS,
        language=Language.ENGLISH,
        description="129 high-quality English phrasal verbs with definitions and examples",
    ),
    # English - French Expressions in English (Custom Scraper)
    LexiconSourceConfig(
        name="french_expressions_in_english",
        url="https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English",
        format=LexiconFormat.CUSTOM_SCRAPER,
        language=Language.ENGLISH,
        description="French words and expressions commonly used in English (Wikipedia)",
        scraper=scrape_french_expressions,
    ),
    # French - Official Scrabble Dictionary
    LexiconSourceConfig(
        name="french_scrabble_ods8",
        url="https://raw.githubusercontent.com/Thecoolsim/French-Scrabble-ODS8/main/French%20ODS%20dictionary.txt",
        format=LexiconFormat.TEXT_LINES,
        language=Language.FRENCH,
        description="Officiel du Scrabble 8 - complete French Scrabble dictionary (~411k words)",
    ),
    LexiconSourceConfig(
        name="french_frequency_50k",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/fr/fr_50k.txt",
        format=LexiconFormat.FREQUENCY_LIST,
        language=Language.FRENCH,
        description="50k most frequent French words from linguistic corpus",
    ),
]
