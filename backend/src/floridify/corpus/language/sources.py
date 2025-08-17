"""Language corpus source configurations.

Contains verified, high-quality sources for language corpora focusing
on comprehensive coverage with minimal duplication. Sources prioritized for
word game quality (Scrabble, linguistic corpora) and academic rigor.
"""

from __future__ import annotations

from ...models.dictionary import Language
from ..core import CorpusSource
from .scrapers.wikipedia_french_expressions import scrape_french_expressions

# High-quality language corpus sources with verified URLs
# Quality over quantity - comprehensive, non-overlapping sources
LANGUAGE_CORPUS_SOURCES = [
    # English - Scrabble Quality Word Lists
    CorpusSource(
        name="sowpods_scrabble_words",
        url="https://raw.githubusercontent.com/jesstess/Scrabble/master/scrabble/sowpods.txt",
        parser="parse_text_lines",
        language=Language.ENGLISH,
        description="SOWPODS official Scrabble dictionary (~267k words, highest quality)",
    ),
    CorpusSource(
        name="google_10k_frequency",
        url="https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
        parser="parse_text_lines",
        language=Language.ENGLISH,
        description="Google's 10,000 most common English words (filtered)",
    ),
    # English - Idioms and Phrases
    CorpusSource(
        name="wikipedia_idioms",
        url="https://raw.githubusercontent.com/saikatbsk/English-Idioms-Dataset/master/data/idioms.json",
        parser="parse_json_idioms",
        language=Language.ENGLISH,
        description="English idioms and their meanings from Wikipedia",
    ),
    CorpusSource(
        name="phrasal_verbs",
        url="https://gist.githubusercontent.com/Xeoncross/4379626/raw/phrasal_verbs.json",
        parser="parse_json_phrasal_verbs",
        language=Language.ENGLISH,
        description="Common English phrasal verbs",
    ),
    CorpusSource(
        name="common_phrases",
        url="https://raw.githubusercontent.com/alvations/pyphraselist/master/EN/common_phrases.txt",
        parser="parse_text_lines",
        language=Language.ENGLISH,
        description="Common English phrases and expressions",
    ),
    # French - Core Vocabulary
    CorpusSource(
        name="french_word_list",
        url="https://raw.githubusercontent.com/chrplr/openlexicon/master/datasets-info/Liste-de-mots-francais-Gutenberg/liste.de.mots.francais.frgut.txt",
        parser="parse_text_lines",
        language=Language.FRENCH,
        description="Comprehensive French word list from Gutenberg (~336k words)",
    ),
    CorpusSource(
        name="french_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/fr/fr_50k.txt",
        parser="parse_frequency_list",
        language=Language.FRENCH,
        description="50,000 most frequent French words with frequencies",
    ),
    # French - Expressions and Idioms
    CorpusSource(
        name="french_expressions",
        url="https://fr.wikipedia.org/wiki/Liste_de_proverbes_français",
        parser="parse_scraped_data",
        language=Language.FRENCH,
        description="French proverbs and expressions from Wikipedia",
        scraper=scrape_french_expressions,  # Custom scraper for Wikipedia
    ),
    # Spanish - Core Vocabulary
    CorpusSource(
        name="spanish_word_list",
        url="https://raw.githubusercontent.com/JorgeDuenasLerin/diccionario-espanol-txt/master/0_palabras_todas.txt",
        parser="parse_text_lines",
        language=Language.SPANISH,
        description="Comprehensive Spanish dictionary (~80k words)",
    ),
    CorpusSource(
        name="spanish_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/es/es_50k.txt",
        parser="parse_frequency_list",
        language=Language.SPANISH,
        description="50,000 most frequent Spanish words with frequencies",
    ),
    # German - Core Vocabulary
    CorpusSource(
        name="german_word_list",
        url="https://raw.githubusercontent.com/davidak/wortliste/master/wortliste.txt",
        parser="parse_text_lines",
        language=Language.GERMAN,
        description="German word list (~1.7M words)",
    ),
    CorpusSource(
        name="german_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/de/de_50k.txt",
        parser="parse_frequency_list",
        language=Language.GERMAN,
        description="50,000 most frequent German words with frequencies",
    ),
    # Italian - Core Vocabulary
    CorpusSource(
        name="italian_word_list",
        url="https://raw.githubusercontent.com/napolux/paroleitaliane/master/paroleitaliane/660000_parole_italiane.txt",
        parser="parse_text_lines",
        language=Language.ITALIAN,
        description="Comprehensive Italian word list (~660k words)",
    ),
    CorpusSource(
        name="italian_frequent_words",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/it/it_50k.txt",
        parser="parse_frequency_list",
        language=Language.ITALIAN,
        description="50,000 most frequent Italian words with frequencies",
    ),
]


__all__ = [
    "LANGUAGE_CORPUS_SOURCES",
]
