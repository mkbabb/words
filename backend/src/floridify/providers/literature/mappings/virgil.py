"""Virgil - Roman Epic Poet (70-19 BCE).

Comprehensive mapping of Virgil's works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, LiteratureEntry, Period

AUTHOR = AuthorInfo(
    name="Virgil",
    birth_year=-70,
    death_year=-19,
    nationality="Roman",
    period=Period.ANCIENT,
    primary_genre=Genre.EPIC,
    language=Language.ENGLISH,
    gutenberg_author_id="4",
)

WORKS = [
    LiteratureEntry(
        title="The Aeneid (Dryden Translation)",
        author=AUTHOR,
        gutenberg_id="228",
        year=-19,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Aeneidos (Latin Original)",
        author=AUTHOR,
        gutenberg_id="227",
        year=-19,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Latin text
    ),
    LiteratureEntry(
        title="The Aeneid (Mackail Translation)",
        author=AUTHOR,
        gutenberg_id="22456",
        year=-19,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Georgics",
        author=AUTHOR,
        gutenberg_id="232",
        year=-30,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Georgicon (Latin Original)",
        author=AUTHOR,
        gutenberg_id="231",
        year=-30,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Latin text
    ),
    LiteratureEntry(
        title="The Aeneid of Virgil (Alternative)",
        author=AUTHOR,
        gutenberg_id="61596",
        year=-19,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Æneid of Virgil, Translated into English Verse",
        author=AUTHOR,
        gutenberg_id="18466",
        year=-19,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Bucolics and Eclogues",
        author=AUTHOR,
        gutenberg_id="230",
        year=-37,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Bucolics and Eclogues (Latin Original)",
        author=AUTHOR,
        gutenberg_id="229",
        year=-37,
        genre=Genre.POETRY,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Latin text
    ),
    LiteratureEntry(
        title="The Æneid of Virgil translated into English prose",
        author=AUTHOR,
        gutenberg_id="73488",
        year=-19,
        genre=Genre.EPIC,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Virgil."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
