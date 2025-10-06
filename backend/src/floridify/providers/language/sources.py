"""Language corpus source configurations.

Contains verified, high-quality sources for language corpora focusing
on comprehensive coverage with minimal duplication. Sources prioritized for
word game quality (Scrabble, linguistic corpora) and academic rigor.
"""

from __future__ import annotations

from collections import defaultdict

from ...models.base import Language
from .models import LanguageSource, ParserType, ScraperType

# High-quality language corpus sources with verified URLs
# Quality over quantity - comprehensive, non-overlapping sources
LANGUAGE_CORPUS_SOURCES = [
    # English - Scrabble Quality Word Lists
    LanguageSource(
        name="sowpods_scrabble_words",
        url="https://raw.githubusercontent.com/jesstess/Scrabble/master/scrabble/sowpods.txt",
        parser=ParserType.TEXT_LINES,
        language=Language.ENGLISH,
        description="SOWPODS official Scrabble dictionary (~267k words, highest quality)",
    ),
    LanguageSource(
        name="google_10k_frequency",
        url="https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
        parser=ParserType.TEXT_LINES,
        language=Language.ENGLISH,
        description="Google's 10,000 most common English words (filtered)",
    ),
    # English - Idioms and Phrases
    LanguageSource(
        name="american_idioms",
        url="https://raw.githubusercontent.com/yuxiaojian/most-common-american-idioms-with-synonyms/main/idioms.json",
        parser=ParserType.CUSTOM,
        language=Language.ENGLISH,
        description="Most common American idioms with synonyms and examples",
    ),
    LanguageSource(
        name="phrasal_verbs",
        url="https://raw.githubusercontent.com/Semigradsky/phrasal-verbs/master/common.json",
        parser=ParserType.CUSTOM,
        language=Language.ENGLISH,
        description="Common English phrasal verbs with definitions and examples",
    ),
    LanguageSource(
        name="common_phrases",
        url="https://gist.githubusercontent.com/maziyarpanahi/876f1d35b06a36992e38bb4b1a05f2f4/raw",
        parser=ParserType.TEXT_LINES,
        language=Language.ENGLISH,
        description="Top 500 common English phrases from Wikipedia corpus",
    ),
    LanguageSource(
        name="proverbs",
        url="https://raw.githubusercontent.com/dariusk/corpora/master/data/words/proverbs.json",
        parser=ParserType.CUSTOM,
        language=Language.ENGLISH,
        description="English proverbs and sayings by category",
    ),
    # French - Core Vocabulary
    LanguageSource(
        name="french_word_list",
        url="https://raw.githubusercontent.com/chrplr/openlexicon/master/datasets-info/Liste-de-mots-francais-Gutenberg/liste.de.mots.francais.frgut.txt",
        parser=ParserType.TEXT_LINES,
        language=Language.FRENCH,
        description="Comprehensive French word list from Gutenberg (~336k words)",
    ),
    LanguageSource(
        name="french_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/fr/fr_50k.txt",
        parser=ParserType.CUSTOM,
        language=Language.FRENCH,
        description="50,000 most frequent French words with frequencies",
    ),
    # French expressions used IN ENGLISH - should be part of English corpus
    LanguageSource(
        name="french_expressions",
        url="https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English",
        parser=ParserType.CUSTOM,
        language=Language.ENGLISH,  # These are French words used IN English
        description="French words and expressions used in English from Wikipedia glossary",
        scraper=ScraperType.FRENCH_EXPRESSIONS,  # Custom scraper for Wikipedia
    ),
    # Pure French sources below
    # French - Expressions and Idioms
    # Spanish - Core Vocabulary
    LanguageSource(
        name="spanish_word_list",
        url="https://raw.githubusercontent.com/JorgeDuenasLerin/diccionario-espanol-txt/master/0_palabras_todas.txt",
        parser=ParserType.TEXT_LINES,
        language=Language.SPANISH,
        description="Comprehensive Spanish dictionary (~80k words)",
    ),
    LanguageSource(
        name="spanish_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/es/es_50k.txt",
        parser=ParserType.CUSTOM,
        language=Language.SPANISH,
        description="50,000 most frequent Spanish words with frequencies",
    ),
    # German - Core Vocabulary
    LanguageSource(
        name="german_word_list",
        url="https://raw.githubusercontent.com/davidak/wortliste/master/wortliste.txt",
        parser=ParserType.TEXT_LINES,
        language=Language.GERMAN,
        description="German word list (~1.7M words)",
    ),
    LanguageSource(
        name="german_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/de/de_50k.txt",
        parser=ParserType.CUSTOM,
        language=Language.GERMAN,
        description="50,000 most frequent German words with frequencies",
    ),
    # Italian - Core Vocabulary
    LanguageSource(
        name="italian_word_list",
        url="https://raw.githubusercontent.com/napolux/paroleitaliane/master/paroleitaliane/660000_parole_italiane.txt",
        parser=ParserType.TEXT_LINES,
        language=Language.ITALIAN,
        description="Comprehensive Italian word list (~660k words)",
    ),
    LanguageSource(
        name="italian_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/it/it_50k.txt",
        parser=ParserType.CUSTOM,
        language=Language.ITALIAN,
        description="50,000 most frequent Italian words with frequencies",
    ),
]

# Create dictionary variant grouped by language
LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE: dict[Language, list[LanguageSource]] = defaultdict(list)
for source in LANGUAGE_CORPUS_SOURCES:
    LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE[source.language].append(source)

# Convert defaultdict to regular dict for cleaner representation
LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE = dict(LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE)

__all__ = [
    "LANGUAGE_CORPUS_SOURCES",
    "LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE",
]
