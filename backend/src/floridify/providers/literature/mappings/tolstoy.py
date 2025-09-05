"""Leo Tolstoy - Russian Novelist (1828-1910).

Comprehensive mapping of Tolstoy's works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, Period
from ..models import LiteratureEntry

AUTHOR = AuthorInfo(
    name="Leo Tolstoy",
    birth_year=1828,
    death_year=1910,
    nationality="Russian",
    period=Period.VICTORIAN,
    primary_genre=Genre.NOVEL,
    language=Language.ENGLISH,
    gutenberg_author_id="136",
)

WORKS = [
    LiteratureEntry(
        title="War and Peace",
        author=AUTHOR,
        gutenberg_id="2600",
        year=1869,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Anna Karenina",
        author=AUTHOR,
        gutenberg_id="1399",
        year=1877,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="What Is Art?",
        author=AUTHOR,
        gutenberg_id="64908",
        year=1897,
        genre=Genre.PHILOSOPHY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="What Men Live By, and Other Tales",
        author=AUTHOR,
        gutenberg_id="6157",
        year=1885,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Kingdom of God Is Within You",
        author=AUTHOR,
        gutenberg_id="43302",
        year=1894,
        genre=Genre.PHILOSOPHY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Master and Man",
        author=AUTHOR,
        gutenberg_id="986",
        year=1895,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Kreutzer Sonata and Other Stories",
        author=AUTHOR,
        gutenberg_id="689",
        year=1889,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Детство/Childhood (Russian)",
        author=AUTHOR,
        gutenberg_id="19681",
        year=1852,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,  # Russian text
    ),
    LiteratureEntry(
        title="Resurrection",
        author=AUTHOR,
        gutenberg_id="1938",
        year=1899,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Father Sergius",
        author=AUTHOR,
        gutenberg_id="985",
        year=1898,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Forged Coupon, and Other Stories",
        author=AUTHOR,
        gutenberg_id="243",
        year=1904,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Where Love is There God is Also",
        author=AUTHOR,
        gutenberg_id="38616",
        year=1885,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Childhood",
        author=AUTHOR,
        gutenberg_id="2142",
        year=1852,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Sevastopol",
        author=AUTHOR,
        gutenberg_id="47197",
        year=1856,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Youth",
        author=AUTHOR,
        gutenberg_id="2637",
        year=1857,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Tolstoy."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
