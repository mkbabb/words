"""John Milton - English Poet (1608-1674).

Comprehensive mapping of Milton's works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, LiteratureEntry, Period

AUTHOR = AuthorInfo(
    name="John Milton",
    birth_year=1608,
    death_year=1674,
    nationality="English",
    period=Period.RENAISSANCE,
    primary_genre=Genre.EPIC,
    language=Language.ENGLISH,
    gutenberg_author_id="58",
)

WORKS = [
    LiteratureEntry(
        title="Paradise Lost",
        author=AUTHOR,
        gutenberg_id="26",
        year=1667,
        genre=Genre.EPIC,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Paradise Lost (Alternative edition)",
        author=AUTHOR,
        gutenberg_id="20",
        year=1667,
        genre=Genre.EPIC,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Paradise Regained",
        author=AUTHOR,
        gutenberg_id="58",
        year=1671,
        genre=Genre.EPIC,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Poetical Works of John Milton",
        author=AUTHOR,
        gutenberg_id="1745",
        year=1674,
        genre=Genre.POETRY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Milton: Minor Poems",
        author=AUTHOR,
        gutenberg_id="31706",
        year=1645,
        genre=Genre.POETRY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="L'Allegro, Il Penseroso, Comus, and Lycidas",
        author=AUTHOR,
        gutenberg_id="397",
        year=1645,
        genre=Genre.POETRY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Milton's Comus",
        author=AUTHOR,
        gutenberg_id="19819",
        year=1634,
        genre=Genre.DRAMA,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Areopagitica",
        author=AUTHOR,
        gutenberg_id="608",
        year=1644,
        genre=Genre.ESSAY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Poemata: Latin, Greek and Italian Poems",
        author=AUTHOR,
        gutenberg_id="6929",
        year=1645,
        genre=Genre.POETRY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="El paraíso perdido (Spanish)",
        author=AUTHOR,
        gutenberg_id="67092",
        year=1667,
        genre=Genre.EPIC,
        period=Period.RENAISSANCE,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="Le Paradis Perdu (French)",
        author=AUTHOR,
        gutenberg_id="62922",
        year=1667,
        genre=Genre.EPIC,
        period=Period.RENAISSANCE,
        language=Language.FRENCH,
    ),
    LiteratureEntry(
        title="An Introduction to the Prose and Poetical Works",
        author=AUTHOR,
        gutenberg_id="44733",
        year=1900,
        genre=Genre.ESSAY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="A Day with John Milton",
        author=AUTHOR,
        gutenberg_id="40130",
        year=1910,
        genre=Genre.BIOGRAPHY,
        period=Period.RENAISSANCE,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Milton."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
