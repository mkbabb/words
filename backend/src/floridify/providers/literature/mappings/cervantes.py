"""Miguel de Cervantes - Spanish Novelist (1547-1616).

Comprehensive mapping of Cervantes' works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, Period
from ..models import LiteratureEntry

AUTHOR = AuthorInfo(
    name="Miguel de Cervantes",
    birth_year=1547,
    death_year=1616,
    nationality="Spanish",
    period=Period.RENAISSANCE,
    primary_genre=Genre.NOVEL,
    language=Language.ENGLISH,
    gutenberg_author_id="505",
)

WORKS = [
    LiteratureEntry(
        title="Don Quijote (Spanish original)",
        author=AUTHOR,
        gutenberg_id="2000",
        year=1615,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="Don Quixote",
        author=AUTHOR,
        gutenberg_id="996",
        year=1615,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The History of Don Quixote, Volume 1",
        author=AUTHOR,
        gutenberg_id="5921",
        year=1605,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The History of Don Quixote, Volume 2",
        author=AUTHOR,
        gutenberg_id="5946",
        year=1615,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Don Quixote, Volume 1",
        author=AUTHOR,
        gutenberg_id="28842",
        year=1605,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Exemplary Novels of Cervantes",
        author=AUTHOR,
        gutenberg_id="14420",
        year=1613,
        genre=Genre.SHORT_STORY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Novelas ejemplares (Spanish)",
        author=AUTHOR,
        gutenberg_id="61202",
        year=1613,
        genre=Genre.SHORT_STORY,
        period=Period.RENAISSANCE,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="Galatea",
        author=AUTHOR,
        gutenberg_id="63404",
        year=1585,
        genre=Genre.ROMANCE,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Wanderings of Persiles and Sigismunda",
        author=AUTHOR,
        gutenberg_id="61561",
        year=1617,
        genre=Genre.ROMANCE,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Numantia",
        author=AUTHOR,
        gutenberg_id="53041",
        year=1585,
        genre=Genre.TRAGEDY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Viage al Parnaso (Spanish)",
        author=AUTHOR,
        gutenberg_id="16110",
        year=1614,
        genre=Genre.SATIRE,
        period=Period.RENAISSANCE,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="The Story of Don Quixote",
        author=AUTHOR,
        gutenberg_id="29468",
        year=1615,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="L'ingénieux chevalier Don Quichotte (French)",
        author=AUTHOR,
        gutenberg_id="42524",
        year=1615,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.FRENCH,
    ),
    LiteratureEntry(
        title="Don Quijote de la Mancha (Hungarian)",
        author=AUTHOR,
        gutenberg_id="66263",
        year=1615,
        genre=Genre.NOVEL,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,  # Hungarian text
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Cervantes."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
