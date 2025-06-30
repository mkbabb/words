"""
Lexicon source configurations for comprehensive language dictionaries.

Contains active, verified sources for English and French lexicons including
words, phrases, idioms, and expressions with singular meanings.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Language(Enum):
    """Supported languages with ISO codes."""

    ENGLISH = "en"
    FRENCH = "fr"
    # Easily extensible for future languages
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"


class LexiconSourceConfig(BaseModel):
    """Configuration for a lexicon source."""
    
    name: str = Field(..., description="Unique identifier for the source")
    url: str = Field(..., description="URL to download the lexicon data")
    format: str = Field(
        ..., 
        description="Data format (text_lines, json_idioms, frequency_list, json_dict, json_array)"
    )
    language: Language = Field(..., description="Language of the lexicon")
    description: str = Field(default="", description="Human-readable description")
    
    model_config = {"frozen": True}


# Comprehensive lexicon sources with active URLs (verified 2024)
LEXICON_SOURCES = [
    # English - Primary Dictionaries
    LexiconSourceConfig(
        name="dwyl_english_words",
        url="https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
        format="text_lines",
        language=Language.ENGLISH,
        description="479k English words for dictionary/word-based projects"
    ),
    LexiconSourceConfig(
        name="jeremy_rifkin_wordlist",
        url="https://raw.githubusercontent.com/jeremy-rifkin/Wordlist/main/wordlist",
        format="text_lines",
        language=Language.ENGLISH,
        description="~300,000 English words"
    ),
    LexiconSourceConfig(
        name="google_10k_english",
        url="https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
        format="text_lines",
        language=Language.ENGLISH,
        description="10k most common English words by frequency"
    ),
    LexiconSourceConfig(
        name="coca_frequency",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
        format="frequency_list",
        language=Language.ENGLISH,
        description="Corpus of Contemporary American English frequency list"
    ),
    
    # English - Idioms and Phrases with Singular Meanings
    LexiconSourceConfig(
        name="english_idioms_mcgrawhill",
        url="https://raw.githubusercontent.com/zaghloul404/englishidioms/main/data/idioms.json",
        format="json_idioms",
        language=Language.ENGLISH,
        description="22,209 unique English idioms from McGraw-Hill Dictionary of American Idioms"
    ),
    LexiconSourceConfig(
        name="useful_english_phrases",
        url="https://raw.githubusercontent.com/khvorostin/useful-english-phrases/master/phrases.txt",
        format="text_lines",
        language=Language.ENGLISH,
        description="15,000 useful English phrases by Greenville Kleiser"
    ),
    LexiconSourceConfig(
        name="prepositional_phrase_idioms",
        url="https://raw.githubusercontent.com/kenclr/ppidioms/master/ppidioms.txt",
        format="text_lines",
        language=Language.ENGLISH,
        description="Prepositional phrase idioms with singular meanings"
    ),
    LexiconSourceConfig(
        name="generated_english_phrases",
        url="https://raw.githubusercontent.com/WithEnglishWeCan/generated-english-phrases/main/phrases.json",
        format="json_array",
        language=Language.ENGLISH,
        description="Generated English phrases and expressions"
    ),
    
    # French - Primary Dictionaries
    LexiconSourceConfig(
        name="french_dictionary",
        url="https://raw.githubusercontent.com/hbenbel/French-Dictionary/master/dictionary/francais.txt",
        format="text_lines",
        language=Language.FRENCH,
        description="Comprehensive French dictionary with gender/types/conjugations"
    ),
    LexiconSourceConfig(
        name="french_words_array",
        url="https://raw.githubusercontent.com/words/an-array-of-french-words/master/index.json",
        format="json_array",
        language=Language.FRENCH,
        description="~336,000 French words"
    ),
    LexiconSourceConfig(
        name="french_frequency",
        url="https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/fr/fr_50k.txt",
        format="frequency_list",
        language=Language.FRENCH,
        description="50k most frequent French words"
    ),
    LexiconSourceConfig(
        name="french_wordlist_taknok",
        url="https://raw.githubusercontent.com/Taknok/French-Wordlist/master/francais.txt",
        format="text_lines",
        language=Language.FRENCH,
        description="French wordlist without diacritics"
    ),
    
    # French - Idioms and Expressions with Singular Meanings
    LexiconSourceConfig(
        name="french_expressions_idioms",
        url="https://raw.githubusercontent.com/KarlSoftware/idioms-1/master/data/french_idioms.json",
        format="json_idioms",
        language=Language.FRENCH,
        description="French idioms, proverbs and expressions with equivalents"
    ),
    LexiconSourceConfig(
        name="french_mixed_expressions",
        url="https://api.github.com/repos/Gulantib/ExpGen/contents/french_expressions.json",
        format="json_github_api",
        language=Language.FRENCH,
        description="Generated French mixed expressions with singular meanings"
    ),
    
    # Common Phrase Collections (English/French idioms with singular meanings)
    LexiconSourceConfig(
        name="english_common_phrases",
        url="https://gist.githubusercontent.com/deekayen/4148741/raw/98d35708fa344717d8eee15d11987de6c8e26d7d/1-1000.txt",
        format="text_lines",
        language=Language.ENGLISH,
        description="1000 most common English phrases and expressions"
    ),
    LexiconSourceConfig(
        name="english_idiomatic_expressions",
        url="https://raw.githubusercontent.com/eubinecto/idiomatch/main/data/idioms_dataset.json",
        format="json_idioms",
        language=Language.ENGLISH,
        description="English idiomatic expressions for SpaCy pattern matching"
    ),
]

# Commonly known singular-meaning phrases and idioms for reference
COMMON_SINGULAR_MEANING_PHRASES = {
    "english": [
        "break a leg",  # good luck
        "piece of cake",  # very easy
        "hit the nail on the head",  # exactly right
        "spill the beans",  # reveal a secret
        "under the weather",  # feeling sick
        "bite the bullet",  # face a difficult situation
        "break the ice",  # start a conversation
        "call it a day",  # stop working
        "cost an arm and a leg",  # very expensive
        "don't judge a book by its cover",  # don't judge by appearance
    ],
    "french": [
        "en coulisses",  # behind the scenes
        "tomber dans les pommes",  # to faint
        "coûter les yeux de la tête",  # cost an arm and a leg
        "poser un lapin",  # to stand someone up
        "avoir le cafard",  # to feel blue/depressed
        "mettre les pieds dans le plat",  # put your foot in your mouth
        "avoir d'autres chats à fouetter",  # have other fish to fry
        "chercher une aiguille dans une botte de foin",  # needle in a haystack
        "il pleut des cordes",  # raining cats and dogs
        "casser les pieds",  # to annoy/bother someone
    ]
}