"""Dante Alighieri - Italian Poet (1265-1321).

Comprehensive mapping of Dante's works available on Project Gutenberg.
"""

from ....models.definition import Language
from ..models import AuthorInfo, Genre, LiteraryWork, Period

AUTHOR = AuthorInfo(
    name="Dante Alighieri",
    birth_year=1265,
    death_year=1321,
    nationality="Italian",
    period=Period.MEDIEVAL,
    primary_genre=Genre.EPIC,
    language=Language.ENGLISH,
    gutenberg_author_id="50",
)

WORKS = [
    # Complete Divine Comedy
    LiteraryWork(
        title="The divine comedy",
        author=AUTHOR,
        gutenberg_id="8800",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Divine Comedy, Longfellow's Translation, Complete",
        author=AUTHOR,
        gutenberg_id="1004",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Divine Comedy, Cary's Translation, Complete",
        author=AUTHOR,
        gutenberg_id="1008",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    
    # Inferno
    LiteraryWork(
        title="Divine Comedy, Longfellow's Translation, Hell",
        author=AUTHOR,
        gutenberg_id="1001",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Divine Comedy, Cary's Translation, Hell",
        author=AUTHOR,
        gutenberg_id="1005",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Divine Comedy of Dante Alighieri: The Inferno",
        author=AUTHOR,
        gutenberg_id="41537",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Divine Comedy, Volume 1, Hell",
        author=AUTHOR,
        gutenberg_id="1995",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    
    # Purgatorio
    LiteraryWork(
        title="Divine Comedy, Longfellow's Translation, Purgatory",
        author=AUTHOR,
        gutenberg_id="1002",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Divine Comedy, Cary's Translation, Purgatory",
        author=AUTHOR,
        gutenberg_id="1006",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Divine Comedy by Dante, Illustrated, Purgatory, Complete",
        author=AUTHOR,
        gutenberg_id="8795",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    
    # Paradiso
    LiteraryWork(
        title="Divine Comedy, Longfellow's Translation, Paradise",
        author=AUTHOR,
        gutenberg_id="1003",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Divine Comedy, Volume 3, Paradise",
        author=AUTHOR,
        gutenberg_id="1997",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Divine Comedy by Dante, Illustrated, Paradise, Complete",
        author=AUTHOR,
        gutenberg_id="8799",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    
    # Italian editions
    LiteraryWork(
        title="La Divina Commedia di Dante (Italian)",
        author=AUTHOR,
        gutenberg_id="1012",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    LiteraryWork(
        title="Divina Commedia di Dante: Inferno (Italian)",
        author=AUTHOR,
        gutenberg_id="997",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    LiteraryWork(
        title="Divina Commedia di Dante: Purgatorio (Italian)",
        author=AUTHOR,
        gutenberg_id="998",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    LiteraryWork(
        title="Divina Commedia di Dante: Paradiso (Italian)",
        author=AUTHOR,
        gutenberg_id="999",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    LiteraryWork(
        title="La Divina Commedia di Dante: Complete (Italian)",
        author=AUTHOR,
        gutenberg_id="1000",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    
    # Other languages
    LiteraryWork(
        title="La Divina Comedia (Spanish)",
        author=AUTHOR,
        gutenberg_id="57303",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.SPANISH,
    ),
    LiteraryWork(
        title="Jumalainen näytelmä (Finnish)",
        author=AUTHOR,
        gutenberg_id="12546",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,  # Finnish text
    ),
    LiteraryWork(
        title="L'enfer (1 of 2) (French)",
        author=AUTHOR,
        gutenberg_id="22768",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.FRENCH,
    ),
    
    # Other works
    LiteraryWork(
        title="The New Life (La Vita Nuova)",
        author=AUTHOR,
        gutenberg_id="41085",
        year=1295,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="La vita nuova (Italian)",
        author=AUTHOR,
        gutenberg_id="71218",
        year=1295,
        genre=Genre.POETRY,
        period=Period.MEDIEVAL,
        language=Language.ITALIAN,
    ),
    LiteraryWork(
        title="The Banquet (Il Convito)",
        author=AUTHOR,
        gutenberg_id="12867",
        year=1307,
        genre=Genre.PHILOSOPHY,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The vision of hell",
        author=AUTHOR,
        gutenberg_id="8789",
        year=1320,
        genre=Genre.EPIC,
        period=Period.MEDIEVAL,
        language=Language.ENGLISH,
    ),
]

def get_works() -> list[LiteraryWork]:
    """Get all works by Dante."""
    return WORKS

def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR