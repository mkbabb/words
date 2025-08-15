"""Ovid - Roman Poet (43 BCE - 17/18 CE).

Comprehensive mapping of Ovid's works available on Project Gutenberg.
"""

from ....models.dictionary import Language
from ..models import AuthorInfo, Genre, LiteraryWork, Period

AUTHOR = AuthorInfo(
    name="Ovid",
    birth_year=-43,
    death_year=17,
    nationality="Roman",
    period=Period.ANCIENT,
    primary_genre=Genre.POETRY,
    language=Language.ENGLISH,
    gutenberg_author_id="987",
)

WORKS = [
    LiteraryWork(
        title="The Lovers Assistant; Or, New Art of Love",
        author=AUTHOR,
        gutenberg_id="31036",
        year=2,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="El arte de amar (Spanish)",
        author=AUTHOR,
        gutenberg_id="67961",
        year=2,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteraryWork(
        title="The Metamorphoses of Ovid, Books I-VII",
        author=AUTHOR,
        gutenberg_id="21765",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Ars Amatoria; or, The Art Of Love",
        author=AUTHOR,
        gutenberg_id="47677",
        year=2,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Metamorphoses of Ovid, Books VIII-XV",
        author=AUTHOR,
        gutenberg_id="26073",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Amores; or, Amours",
        author=AUTHOR,
        gutenberg_id="47676",
        year=-16,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Last Poems of Ovid",
        author=AUTHOR,
        gutenberg_id="21920",
        year=14,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Fasti (Latin)",
        author=AUTHOR,
        gutenberg_id="8738",
        year=8,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Latin text
    ),
    LiteraryWork(
        title="Remedia Amoris; or, The Remedy of Love",
        author=AUTHOR,
        gutenberg_id="47678",
        year=2,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Metamorphoses of Publius Ovidus Naso in English blank verse",
        author=AUTHOR,
        gutenberg_id="28621",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Metamorfóseos o Transformaciones (1 de 4) (Spanish)",
        author=AUTHOR,
        gutenberg_id="66337",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteraryWork(
        title="Metamorfóseos o Transformaciones (2 de 4) (Spanish)",
        author=AUTHOR,
        gutenberg_id="66338",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteraryWork(
        title="Metamorfóseos o Transformaciones (3 de 4) (Spanish)",
        author=AUTHOR,
        gutenberg_id="66339",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteraryWork(
        title="Metamorfóseos o Transformaciones (4 de 4) (Spanish)",
        author=AUTHOR,
        gutenberg_id="66340",
        year=8,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteraryWork(
        title="Amores: elegías amatorias (Spanish)",
        author=AUTHOR,
        gutenberg_id="68015",
        year=-16,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
]


def get_works() -> list[LiteraryWork]:
    """Get all works by Ovid."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
