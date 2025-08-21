"""Homer - Ancient Greek Epic Poet (8th century BCE).

Comprehensive mapping of Homer's works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, LiteratureEntry, Period

AUTHOR = AuthorInfo(
    name="Homer",
    birth_year=-800,
    death_year=None,
    nationality="Greek",
    period=Period.ANCIENT,
    primary_genre=Genre.EPIC,
    language=Language.ENGLISH,
    gutenberg_author_id="705",
)

WORKS = [
    LiteratureEntry(
        title="The Iliad",
        author=AUTHOR,
        gutenberg_id="6130",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Iliad (Alternative Translation)",
        author=AUTHOR,
        gutenberg_id="2199",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Odyssey",
        author=AUTHOR,
        gutenberg_id="1727",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Odyssey (Alternative Translation)",
        author=AUTHOR,
        gutenberg_id="3160",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Odyssey (Third Translation)",
        author=AUTHOR,
        gutenberg_id="28797",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Odyssey of Homer",
        author=AUTHOR,
        gutenberg_id="1728",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Iliad of Homer",
        author=AUTHOR,
        gutenberg_id="16452",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Odysseys of Homer, together with the shorter poems",
        author=AUTHOR,
        gutenberg_id="48895",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="La Odisea (Spanish Translation)",
        author=AUTHOR,
        gutenberg_id="58221",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="La Ilíada (Spanish Translation)",
        author=AUTHOR,
        gutenberg_id="57654",
        year=-750,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="Homer: The Iliad; The Odyssey (W. Lucas Collins' Guide)",
        author=AUTHOR,
        gutenberg_id="59306",
        year=1876,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Homer."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
