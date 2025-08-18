"""Geoffrey Chaucer - English Poet (c.1343-1400).

Comprehensive mapping of Chaucer's works available on Project Gutenberg.
"""

from ....models.dictionary import Language
from ....models.literature import AuthorInfo, Genre, LiteratureEntry, Period

AUTHOR = AuthorInfo(
    name="Geoffrey Chaucer",
    birth_year=1343,
    death_year=1400,
    nationality="English",
    period=Period.MEDIEVAL,
    primary_genre=Genre.POETRY,
    language=Language.ENGLISH,
    gutenberg_author_id="22",
)

WORKS = [
    LiteratureEntry(
        title="The Canterbury Tales, and Other Poems",
        author=AUTHOR,
        gutenberg_id="2383",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Works, Volume 4 — The Canterbury Tales (Middle English)",
        author=AUTHOR,
        gutenberg_id="22120",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="The Canterbury Tales",
        author=AUTHOR,
        gutenberg_id="23722",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Works, Volume 5 — Notes to the Canterbury Tales",
        author=AUTHOR,
        gutenberg_id="43016",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Dalle Novelle di Canterbury (Italian)",
        author=AUTHOR,
        gutenberg_id="47461",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    LiteratureEntry(
        title="Troilus and Criseyde",
        author=AUTHOR,
        gutenberg_id="257",
        year=1385,
        genre=Genre.ROMANCE,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Works, Volume 1 — Romaunt of the Rose; Minor Poems",
        author=AUTHOR,
        gutenberg_id="43089",
        year=1380,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Works, Volume 2 — Boethius and Troilus",
        author=AUTHOR,
        gutenberg_id="44833",
        year=1385,
        genre=Genre.PHILOSOPHY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Works, Volume 3 — The House of Fame; The Legend of Good Women",
        author=AUTHOR,
        gutenberg_id="45027",
        year=1386,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Works, Volume 6 — Introduction, Glossary, and Indexes",
        author=AUTHOR,
        gutenberg_id="43097",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer's Translation of Boethius's 'De Consolatione Philosophiae'",
        author=AUTHOR,
        gutenberg_id="42083",
        year=1385,
        genre=Genre.PHILOSOPHY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Dryden's Palamon and Arcite",
        author=AUTHOR,
        gutenberg_id="7490",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucer for Children: A Golden Key",
        author=AUTHOR,
        gutenberg_id="43984",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteratureEntry(
        title="Chaucerian and Other Pieces",
        author=AUTHOR,
        gutenberg_id="43195",
        year=1400,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteratureEntry]:
    """Get all works by Chaucer."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
