"""Euripides - Ancient Greek Tragedian (c.480-406 BCE).

Comprehensive mapping of Euripides' works available on Project Gutenberg.
"""

from ....models.dictionary import Language
from ....models.literature import AuthorInfo, Genre, LiteratureEntry, Period

AUTHOR = AuthorInfo(
    name="Euripides",
    birth_year=-480,
    death_year=-406,
    nationality="Greek",
    period=Period.ANCIENT,
    primary_genre=Genre.DRAMA,
    language=Language.ENGLISH,
    gutenberg_author_id="1680",
)

WORKS = [
    LiteratureEntry(
        title="The Tragedies of Euripides, Volume I",
        author=AUTHOR,
        gutenberg_id="15081",
        year=-420,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Medea of Euripides",
        author=AUTHOR,
        gutenberg_id="35451",
        year=-431,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Electra of Euripides",
        author=AUTHOR,
        gutenberg_id="14322",
        year=-413,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Bacchae of Euripides",
        author=AUTHOR,
        gutenberg_id="35173",
        year=-405,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Trojan Women of Euripides",
        author=AUTHOR,
        gutenberg_id="35171",
        year=-415,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Trojan women of Euripides (Alternative)",
        author=AUTHOR,
        gutenberg_id="10096",
        year=-415,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Orestes",
        author=AUTHOR,
        gutenberg_id="56547",
        year=-408,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Ίων (Ion - Greek Text)",
        author=AUTHOR,
        gutenberg_id="27389",
        year=-413,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Greek text but in PG English collection
    ),
    LiteratureEntry(
        title="Euripides and His Age",
        author=AUTHOR,
        gutenberg_id="35472",
        year=1913,
        genre=Genre.BIOGRAPHY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Euripides."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
