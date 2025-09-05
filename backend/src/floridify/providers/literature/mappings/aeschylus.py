"""Aeschylus - Ancient Greek Tragedian (c.525-456 BCE).

Comprehensive mapping of Aeschylus' works available on Project Gutenberg.
"""

from ....models.base import Language
from ....models.literature import AuthorInfo, Genre, Period
from ..models import LiteratureEntry

AUTHOR = AuthorInfo(
    name="Aeschylus",
    birth_year=-525,
    death_year=-456,
    nationality="Greek",
    period=Period.ANCIENT,
    primary_genre=Genre.DRAMA,
    language=Language.ENGLISH,
    gutenberg_author_id="2825",
)

WORKS = [
    LiteratureEntry(
        title="Prometheus Bound and the Seven Against Thebes",
        author=AUTHOR,
        gutenberg_id="27458",
        year=-465,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Agamemnon of Aeschylus",
        author=AUTHOR,
        gutenberg_id="14417",
        year=-458,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Four Plays of Aeschylus",
        author=AUTHOR,
        gutenberg_id="8714",
        year=-460,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The House of Atreus",
        author=AUTHOR,
        gutenberg_id="8604",
        year=-458,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Lyrical Dramas of Aeschylus",
        author=AUTHOR,
        gutenberg_id="59225",
        year=-460,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Æschylos Tragedies and Fragments",
        author=AUTHOR,
        gutenberg_id="53174",
        year=-460,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Tragedias (Spanish)",
        author=AUTHOR,
        gutenberg_id="66023",
        year=-460,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.SPANISH,
    ),
    LiteratureEntry(
        title="Προμηθεύς Δεσμώτης (Prometheus Bound - Greek)",
        author=AUTHOR,
        gutenberg_id="39251",
        year=-430,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Greek text in PG English collection
    ),
    LiteratureEntry(
        title="Αγαμέμνων (Agamemnon - Greek)",
        author=AUTHOR,
        gutenberg_id="39536",
        year=-458,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Ευμενίδες (Eumenides - Greek)",
        author=AUTHOR,
        gutenberg_id="39208",
        year=-458,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Επτά επί Θήβας (Seven Against Thebes - Greek)",
        author=AUTHOR,
        gutenberg_id="17996",
        year=-467,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Χοηφόροι (Libation Bearers - Greek)",
        author=AUTHOR,
        gutenberg_id="39073",
        year=-458,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Πέρσαι (The Persians - Greek)",
        author=AUTHOR,
        gutenberg_id="39409",
        year=-472,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Prometheus Geboeid (Dutch)",
        author=AUTHOR,
        gutenberg_id="57697",
        year=-430,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Dutch text
    ),
    LiteratureEntry(
        title="Agamemnon (Finnish)",
        author=AUTHOR,
        gutenberg_id="53137",
        year=-458,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,  # Finnish text
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Aeschylus."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
