"""Johann Wolfgang von Goethe - German Writer (1749-1832).

Comprehensive mapping of Goethe's works available on Project Gutenberg.
"""

from ....models.definition import Language
from ..models import AuthorInfo, Genre, LiteraryWork, Period

AUTHOR = AuthorInfo(
    name="Johann Wolfgang von Goethe",
    birth_year=1749,
    death_year=1832,
    nationality="German",
    period=Period.ROMANTIC,
    primary_genre=Genre.NOVEL,
    language=Language.ENGLISH,
    gutenberg_author_id="586",
)

WORKS = [
    LiteraryWork(
        title="The Sorrows of Young Werther",
        author=AUTHOR,
        gutenberg_id="2527",
        year=1774,
        genre=Genre.NOVEL,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Faust [Part 1]",
        author=AUTHOR,
        gutenberg_id="14591",
        year=1808,
        genre=Genre.DRAMA,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Faust: A Tragedy",
        author=AUTHOR,
        gutenberg_id="63203",
        year=1832,
        genre=Genre.DRAMA,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Faust: Der Tragödie erster Teil (German)",
        author=AUTHOR,
        gutenberg_id="2229",
        year=1808,
        genre=Genre.DRAMA,
        period=Period.ROMANTIC,
        language=Language.GERMAN,
    ),
    LiteraryWork(
        title="Faust: Eine Tragödie [erster Teil] (German)",
        author=AUTHOR,
        gutenberg_id="21000",
        year=1808,
        genre=Genre.DRAMA,
        period=Period.ROMANTIC,
        language=Language.GERMAN,
    ),
    LiteraryWork(
        title="Wilhelm Meister's Apprenticeship and Travels, Vol. I",
        author=AUTHOR,
        gutenberg_id="36483",
        year=1796,
        genre=Genre.NOVEL,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Die Wahlverwandtschaften (German)",
        author=AUTHOR,
        gutenberg_id="2403",
        year=1809,
        genre=Genre.NOVEL,
        period=Period.ROMANTIC,
        language=Language.GERMAN,
    ),
    LiteraryWork(
        title="The Autobiography of Goethe",
        author=AUTHOR,
        gutenberg_id="52654",
        year=1833,
        genre=Genre.BIOGRAPHY,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Goethe's Theory of Colours",
        author=AUTHOR,
        gutenberg_id="50572",
        year=1810,
        genre=Genre.ESSAY,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Letters from Switzerland and Travels in Italy",
        author=AUTHOR,
        gutenberg_id="53205",
        year=1816,
        genre=Genre.ESSAY,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Italienische Reise — Band 1 (German)",
        author=AUTHOR,
        gutenberg_id="2404",
        year=1817,
        genre=Genre.ESSAY,
        period=Period.ROMANTIC,
        language=Language.GERMAN,
    ),
    LiteraryWork(
        title="Maxims and Reflections",
        author=AUTHOR,
        gutenberg_id="33670",
        year=1833,
        genre=Genre.PHILOSOPHY,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Erotica Romana",
        author=AUTHOR,
        gutenberg_id="7889",
        year=1795,
        genre=Genre.POETRY,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="The Poems of Goethe",
        author=AUTHOR,
        gutenberg_id="5615",
        year=1832,
        genre=Genre.POETRY,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
    LiteraryWork(
        title="Hermann and Dorothea",
        author=AUTHOR,
        gutenberg_id="2054",
        year=1797,
        genre=Genre.EPIC,
        period=Period.ROMANTIC,
        language=Language.ENGLISH,
    ),
]

def get_works() -> list[LiteraryWork]:
    """Get all works by Goethe."""
    return WORKS

def get_author() -> AuthorInfo:
    """Get author information."""
    return AUTHOR