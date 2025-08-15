"""Charles Dickens - Victorian Novelist (1812-1870).

Comprehensive mapping of Dickens' works available on Project Gutenberg.
"""

from ....models.dictionary import Language
from ..models import AuthorInfo, Genre, LiteraryWork, Period

AUTHOR = AuthorInfo(
    name="Charles Dickens",
    birth_year=1812,
    death_year=1870,
    nationality="English",
    period=Period.VICTORIAN,
    primary_genre=Genre.NOVEL,
    language=Language.ENGLISH,
    gutenberg_author_id="37",
)

WORKS = [
    LiteraryWork(
        title="The Pickwick Papers",
        author=AUTHOR,
        gutenberg_id="580",
        year=1836,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="David Copperfield",
        author=AUTHOR,
        gutenberg_id="766",
        year=1850,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="A Christmas Carol",
        author=AUTHOR,
        gutenberg_id="24022",
        year=1843,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="A Tale of Two Cities",
        author=AUTHOR,
        gutenberg_id="98",
        year=1859,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Hard Times",
        author=AUTHOR,
        gutenberg_id="786",
        year=1854,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Great Expectations",
        author=AUTHOR,
        gutenberg_id="1400",
        year=1861,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Bleak House",
        author=AUTHOR,
        gutenberg_id="1023",
        year=1853,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Nicholas Nickleby",
        author=AUTHOR,
        gutenberg_id="967",
        year=1839,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="A Christmas Carol in Prose",
        author=AUTHOR,
        gutenberg_id="46",
        year=1843,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Oliver Twist",
        author=AUTHOR,
        gutenberg_id="730",
        year=1838,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Our Mutual Friend",
        author=AUTHOR,
        gutenberg_id="883",
        year=1865,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Old Curiosity Shop",
        author=AUTHOR,
        gutenberg_id="700",
        year=1841,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Sketches by Boz",
        author=AUTHOR,
        gutenberg_id="882",
        year=1836,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="American Notes",
        author=AUTHOR,
        gutenberg_id="675",
        year=1842,
        genre=Genre.ESSAY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Little Dorrit",
        author=AUTHOR,
        gutenberg_id="963",
        year=1857,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Mystery of Edwin Drood",
        author=AUTHOR,
        gutenberg_id="564",
        year=1870,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Martin Chuzzlewit",
        author=AUTHOR,
        gutenberg_id="968",
        year=1844,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Dombey and Son",
        author=AUTHOR,
        gutenberg_id="821",
        year=1848,
        genre=Genre.NOVEL,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Three Ghost Stories",
        author=AUTHOR,
        gutenberg_id="1289",
        year=1865,
        genre=Genre.SHORT_STORY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Pictures from Italy",
        author=AUTHOR,
        gutenberg_id="650",
        year=1846,
        genre=Genre.ESSAY,
        period=Period.VICTORIAN,
        language=Language.ENGLISH,
    ),
]


def get_works() -> list[LiteraryWork]:
    """Get all works by Dickens."""
    return WORKS


def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR
