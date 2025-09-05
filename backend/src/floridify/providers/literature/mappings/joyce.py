"""James Joyce - Irish Modernist Writer (1882-1941).

Comprehensive mapping of Joyce's works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, Period
from ..models import LiteratureEntry

AUTHOR = AuthorInfo(
    name="James Joyce",
    birth_year=1882,
    death_year=1941,
    nationality="Irish",
    period=Period.MODERNIST,
    primary_genre=Genre.NOVEL,
    language=Language.ENGLISH,
    gutenberg_author_id="1039",
)

WORKS = [
    LiteratureEntry(
        title="Ulysses",
        author=AUTHOR,
        gutenberg_id="4300",
        year=1922,
        genre=Genre.NOVEL,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Dubliners",
        author=AUTHOR,
        gutenberg_id="2814",
        year=1914,
        genre=Genre.SHORT_STORY,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="A Portrait of the Artist as a Young Man",
        author=AUTHOR,
        gutenberg_id="4217",
        year=1916,
        genre=Genre.NOVEL,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chamber Music",
        author=AUTHOR,
        gutenberg_id="2817",
        year=1907,
        genre=Genre.POETRY,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Exiles: A Play in Three Acts",
        author=AUTHOR,
        gutenberg_id="55945",
        year=1918,
        genre=Genre.DRAMA,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Dubliners (Alternative edition)",
        author=AUTHOR,
        gutenberg_id="7872",
        year=1914,
        genre=Genre.SHORT_STORY,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chamber Music (Alternative edition)",
        author=AUTHOR,
        gutenberg_id="20601",
        year=1907,
        genre=Genre.POETRY,
        period=Period.MODERNIST,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Joyce."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
