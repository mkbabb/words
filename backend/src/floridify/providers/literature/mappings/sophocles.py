"""Sophocles - Ancient Greek Tragedian (c.496-406 BCE).

Comprehensive mapping of Sophocles' works available on Project Gutenberg.
"""

from ..models import AuthorInfo, Genre, LiteraryWork, Period

AUTHOR = AuthorInfo(
    name="Sophocles",
    birth_year=-496,
    death_year=-406,
    nationality="Greek",
    period=Period.ANCIENT,
    primary_genre=Genre.DRAMA,
    language=Language.ENGLISH,
    gutenberg_author_id="26",
)

WORKS = [
    LiteraryWork(
        title="Plays of Sophocles: Oedipus the King; Oedipus at Colonus; Antigone",
        author=AUTHOR,
        gutenberg_id="31",
        year=-429,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Oedipus King of Thebes",
        author=AUTHOR,
        gutenberg_id="27673",
        year=-429,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Seven Plays in English Verse",
        author=AUTHOR,
        gutenberg_id="14484",
        year=-450,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Antigone (Finnish Translation)",
        author=AUTHOR,
        gutenberg_id="54543",
        year=-441,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="fi",
    ),
    LiteraryWork(
        title="Philoktetes",
        author=AUTHOR,
        gutenberg_id="806",
        year=-409,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Specimens of Greek Tragedy",
        author=AUTHOR,
        gutenberg_id="7073",
        year=-430,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Book of illustrations: Ancient Tragedy",
        author=AUTHOR,
        gutenberg_id="19559",
        year=-430,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Edipo rey; Edipo en Colona; Antígona (Spanish Translation)",
        author=AUTHOR,
        gutenberg_id="63509",
        year=-429,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="es",
    ),
    LiteraryWork(
        title="Οιδίπους Τύραννος (Modern Greek)",
        author=AUTHOR,
        gutenberg_id="17839",
        year=-429,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="el",
    ),
    LiteraryWork(
        title="Αντιγόνη (Modern Greek)",
        author=AUTHOR,
        gutenberg_id="26731",
        year=-441,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="el",
    ),
    LiteraryWork(
        title="Οιδίπους επί Κολωνώ (Modern Greek)",
        author=AUTHOR,
        gutenberg_id="39382",
        year=-401,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="el",
    ),
    LiteraryWork(
        title="Antigone (Hungarian Translation)",
        author=AUTHOR,
        gutenberg_id="64403",
        year=-441,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="hu",
    ),
    LiteraryWork(
        title="Elektra (Hungarian Translation)",
        author=AUTHOR,
        gutenberg_id="56745",
        year=-410,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="hu",
    ),
    LiteraryWork(
        title="A trachisi nők (Women of Trachis - Hungarian)",
        author=AUTHOR,
        gutenberg_id="64367",
        year=-413,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="hu",
    ),
    LiteraryWork(
        title="Ajas: Szomorujáték (Ajax - Hungarian)",
        author=AUTHOR,
        gutenberg_id="56920",
        year=-450,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="hu",
    ),
    LiteraryWork(
        title="Koning Oedipus (Dutch Translation)",
        author=AUTHOR,
        gutenberg_id="45355",
        year=-429,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="nl",
    ),
    LiteraryWork(
        title="Oedipus király (Hungarian Translation)",
        author=AUTHOR,
        gutenberg_id="66100",
        year=-429,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="hu",
    ),
    LiteraryWork(
        title="Philoktetes (Hungarian Translation)",
        author=AUTHOR,
        gutenberg_id="61493",
        year=-409,
        genre=Genre.DRAMA,
        period=Period.ANCIENT,
        language="hu",
    ),
]

def get_works() -> list[LiteraryWork]:
    """Get all works by Sophocles."""
    return WORKS

def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR