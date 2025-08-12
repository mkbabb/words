"""Comprehensive mapping of authors to their literary works and Project Gutenberg IDs."""

from ..core import Author
from .models import AuthorMetadata, Genre, LiteraryWork, Period

# Author metadata with period and genre information
AUTHOR_METADATA = {
    # Ancient Authors
    Author.HOMER: AuthorMetadata(
        author=Author.HOMER,
        period=Period.ANCIENT, 
        primary_genre=Genre.EPIC,
        birth_year=-800,
        nationality="Greek"
    ),
    Author.SOPHOCLES: AuthorMetadata(
        author=Author.SOPHOCLES,
        period=Period.ANCIENT,
        primary_genre=Genre.DRAMA,
        birth_year=-496,
        death_year=-406, 
        nationality="Greek"
    ),
    Author.EURIPIDES: AuthorMetadata(
        author=Author.EURIPIDES,
        period=Period.ANCIENT,
        primary_genre=Genre.DRAMA,
        birth_year=-480,
        death_year=-406,
        nationality="Greek"
    ),
    Author.AESCHYLUS: AuthorMetadata(
        author=Author.AESCHYLUS,
        period=Period.ANCIENT,
        primary_genre=Genre.DRAMA,
        birth_year=-525,
        death_year=-456,
        nationality="Greek"
    ),
    Author.VIRGIL: AuthorMetadata(
        author=Author.VIRGIL,
        period=Period.ANCIENT,
        primary_genre=Genre.EPIC,
        birth_year=-70,
        death_year=-19,
        nationality="Roman"
    ),
    Author.OVID: AuthorMetadata(
        author=Author.OVID,
        period=Period.ANCIENT,
        primary_genre=Genre.POETRY,
        birth_year=-43,
        death_year=17,
        nationality="Roman"
    ),
    
    # Medieval Authors
    Author.DANTE: AuthorMetadata(
        author=Author.DANTE,
        period=Period.MEDIEVAL,
        primary_genre=Genre.EPIC,
        birth_year=1265,
        death_year=1321,
        nationality="Italian"
    ),
    Author.CHAUCER: AuthorMetadata(
        author=Author.CHAUCER,
        period=Period.MEDIEVAL,
        primary_genre=Genre.POETRY,
        birth_year=1343,
        death_year=1400,
        nationality="English"
    ),
    Author.BOCCACCIO: AuthorMetadata(
        author=Author.BOCCACCIO,
        period=Period.MEDIEVAL,
        primary_genre=Genre.SHORT_STORY,
        birth_year=1313,
        death_year=1375,
        nationality="Italian"
    ),
    Author.PETRARCH: AuthorMetadata(
        author=Author.PETRARCH,
        period=Period.MEDIEVAL,
        primary_genre=Genre.POETRY,
        birth_year=1304,
        death_year=1374,
        nationality="Italian"
    ),
    
    # Renaissance Authors
    Author.SHAKESPEARE: AuthorMetadata(
        author=Author.SHAKESPEARE,
        period=Period.RENAISSANCE,
        primary_genre=Genre.DRAMA,
        birth_year=1564,
        death_year=1616,
        nationality="English"
    ),
    Author.CERVANTES: AuthorMetadata(
        author=Author.CERVANTES,
        period=Period.RENAISSANCE,
        primary_genre=Genre.NOVEL,
        birth_year=1547,
        death_year=1616,
        nationality="Spanish"
    ),
    Author.MONTAIGNE: AuthorMetadata(
        author=Author.MONTAIGNE,
        period=Period.RENAISSANCE,
        primary_genre=Genre.ESSAY,
        birth_year=1533,
        death_year=1592,
        nationality="French"
    ),
    Author.RABELAIS: AuthorMetadata(
        author=Author.RABELAIS,
        period=Period.RENAISSANCE,
        primary_genre=Genre.NOVEL,
        birth_year=1494,
        death_year=1553,
        nationality="French"
    ),
    Author.SPENSER: AuthorMetadata(
        author=Author.SPENSER,
        period=Period.RENAISSANCE,
        primary_genre=Genre.POETRY,
        birth_year=1552,
        death_year=1599,
        nationality="English"
    ),
    Author.MILTON: AuthorMetadata(
        author=Author.MILTON,
        period=Period.RENAISSANCE,
        primary_genre=Genre.EPIC,
        birth_year=1608,
        death_year=1674,
        nationality="English"
    ),
    
    # Classical to Romantic
    Author.GOETHE: AuthorMetadata(
        author=Author.GOETHE,
        period=Period.ROMANTIC,
        primary_genre=Genre.NOVEL,
        birth_year=1749,
        death_year=1832,
        nationality="German"
    ),
    
    # 19th Century
    Author.DICKENS: AuthorMetadata(
        author=Author.DICKENS,
        period=Period.VICTORIAN,
        primary_genre=Genre.NOVEL,
        birth_year=1812,
        death_year=1870,
        nationality="English"
    ),
    Author.TOLSTOY: AuthorMetadata(
        author=Author.TOLSTOY,
        period=Period.VICTORIAN,
        primary_genre=Genre.NOVEL,
        birth_year=1828,
        death_year=1910,
        nationality="Russian"
    ),
    Author.DUMAS: AuthorMetadata(
        author=Author.DUMAS,
        period=Period.VICTORIAN,
        primary_genre=Genre.NOVEL,
        birth_year=1802,
        death_year=1870,
        nationality="French"
    ),
    
    # Modernist
    Author.JOYCE: AuthorMetadata(
        author=Author.JOYCE,
        period=Period.MODERNIST,
        primary_genre=Genre.NOVEL,
        birth_year=1882,
        death_year=1941,
        nationality="Irish"
    ),
    Author.WOOLF: AuthorMetadata(
        author=Author.WOOLF,
        period=Period.MODERNIST,
        primary_genre=Genre.NOVEL,
        birth_year=1882,
        death_year=1941,
        nationality="English"
    ),
    Author.PROUST: AuthorMetadata(
        author=Author.PROUST,
        period=Period.MODERNIST,
        primary_genre=Genre.NOVEL,
        birth_year=1871,
        death_year=1922,
        nationality="French"
    ),
}

# Comprehensive mapping of authors to their major works with Gutenberg IDs
AUTHOR_WORKS_MAPPING = {
    # Ancient Authors
    Author.HOMER: [
        LiteraryWork("The Iliad", Author.HOMER, "2199", 800, Genre.EPIC, Period.ANCIENT),
        LiteraryWork("The Odyssey", Author.HOMER, "1727", 800, Genre.EPIC, Period.ANCIENT),
    ],
    
    Author.SOPHOCLES: [
        LiteraryWork("Oedipus Rex", Author.SOPHOCLES, "31", -429, Genre.DRAMA, Period.ANCIENT),
        LiteraryWork("Antigone", Author.SOPHOCLES, "31", -441, Genre.DRAMA, Period.ANCIENT),
        LiteraryWork("Electra", Author.SOPHOCLES, "31", -410, Genre.DRAMA, Period.ANCIENT),
    ],
    
    Author.EURIPIDES: [
        LiteraryWork("Medea", Author.EURIPIDES, "35", -431, Genre.DRAMA, Period.ANCIENT),
        LiteraryWork("The Bacchae", Author.EURIPIDES, "35", -405, Genre.DRAMA, Period.ANCIENT),
        LiteraryWork("Hippolytus", Author.EURIPIDES, "35", -428, Genre.DRAMA, Period.ANCIENT),
    ],
    
    Author.AESCHYLUS: [
        LiteraryWork("The Oresteia", Author.AESCHYLUS, "14417", -458, Genre.DRAMA, Period.ANCIENT),
        LiteraryWork("Prometheus Bound", Author.AESCHYLUS, "32861", -430, Genre.DRAMA, Period.ANCIENT),
    ],
    
    Author.VIRGIL: [
        LiteraryWork("The Aeneid", Author.VIRGIL, "227", -19, Genre.EPIC, Period.ANCIENT),
        LiteraryWork("Georgics", Author.VIRGIL, "227", -29, Genre.POETRY, Period.ANCIENT),
    ],
    
    Author.OVID: [
        LiteraryWork("Metamorphoses", Author.OVID, "21765", 8, Genre.POETRY, Period.ANCIENT),
        LiteraryWork("The Art of Love", Author.OVID, "56481", 1, Genre.POETRY, Period.ANCIENT),
    ],
    
    # Medieval Authors  
    Author.DANTE: [
        LiteraryWork("The Divine Comedy", Author.DANTE, "1004", 1320, Genre.EPIC, Period.MEDIEVAL),
        LiteraryWork("Inferno", Author.DANTE, "8800", 1314, Genre.EPIC, Period.MEDIEVAL),
        LiteraryWork("Purgatorio", Author.DANTE, "8801", 1318, Genre.EPIC, Period.MEDIEVAL),
        LiteraryWork("Paradiso", Author.DANTE, "8802", 1320, Genre.EPIC, Period.MEDIEVAL),
        LiteraryWork("Vita Nuova", Author.DANTE, "41085", 1295, Genre.POETRY, Period.MEDIEVAL),
    ],
    
    Author.CHAUCER: [
        LiteraryWork("The Canterbury Tales", Author.CHAUCER, "2383", 1400, Genre.POETRY, Period.MEDIEVAL),
        LiteraryWork("Troilus and Criseyde", Author.CHAUCER, "257", 1385, Genre.POETRY, Period.MEDIEVAL),
    ],
    
    Author.BOCCACCIO: [
        LiteraryWork("The Decameron", Author.BOCCACCIO, "23700", 1353, Genre.SHORT_STORY, Period.MEDIEVAL),
    ],
    
    # Renaissance Authors
    Author.SHAKESPEARE: [
        LiteraryWork("Complete Works", Author.SHAKESPEARE, "100", 1623, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("Hamlet", Author.SHAKESPEARE, "1524", 1603, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("Romeo and Juliet", Author.SHAKESPEARE, "1513", 1597, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("Macbeth", Author.SHAKESPEARE, "1533", 1606, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("Othello", Author.SHAKESPEARE, "1531", 1603, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("King Lear", Author.SHAKESPEARE, "1532", 1608, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("A Midsummer Night's Dream", Author.SHAKESPEARE, "1514", 1600, Genre.DRAMA, Period.RENAISSANCE),
        LiteraryWork("The Tempest", Author.SHAKESPEARE, "23042", 1611, Genre.DRAMA, Period.RENAISSANCE),
    ],
    
    Author.CERVANTES: [
        LiteraryWork("Don Quixote", Author.CERVANTES, "996", 1615, Genre.NOVEL, Period.RENAISSANCE),
    ],
    
    Author.MILTON: [
        LiteraryWork("Paradise Lost", Author.MILTON, "26", 1667, Genre.EPIC, Period.RENAISSANCE),
        LiteraryWork("Paradise Regained", Author.MILTON, "58", 1671, Genre.EPIC, Period.RENAISSANCE),
    ],
    
    # Classical to Romantic
    Author.GOETHE: [
        LiteraryWork("Faust", Author.GOETHE, "14591", 1832, Genre.DRAMA, Period.ROMANTIC),
        LiteraryWork("The Sorrows of Young Werther", Author.GOETHE, "2527", 1774, Genre.NOVEL, Period.ROMANTIC),
    ],
    
    # 19th Century
    Author.DICKENS: [
        LiteraryWork("A Tale of Two Cities", Author.DICKENS, "98", 1859, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("Great Expectations", Author.DICKENS, "1400", 1861, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("Oliver Twist", Author.DICKENS, "730", 1838, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("David Copperfield", Author.DICKENS, "766", 1850, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("A Christmas Carol", Author.DICKENS, "46", 1843, Genre.SHORT_STORY, Period.VICTORIAN),
    ],
    
    Author.TOLSTOY: [
        LiteraryWork("War and Peace", Author.TOLSTOY, "2600", 1869, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("Anna Karenina", Author.TOLSTOY, "1399", 1878, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("The Death of Ivan Ilyich", Author.TOLSTOY, "26", 1886, Genre.SHORT_STORY, Period.VICTORIAN),
    ],
    
    Author.DUMAS: [
        LiteraryWork("The Three Musketeers", Author.DUMAS, "1257", 1844, Genre.NOVEL, Period.VICTORIAN),
        LiteraryWork("The Count of Monte Cristo", Author.DUMAS, "1184", 1846, Genre.NOVEL, Period.VICTORIAN),
    ],
    
    # Modernist Authors
    Author.JOYCE: [
        LiteraryWork("Ulysses", Author.JOYCE, "4300", 1922, Genre.NOVEL, Period.MODERNIST),
        LiteraryWork("A Portrait of the Artist as a Young Man", Author.JOYCE, "4217", 1916, Genre.NOVEL, Period.MODERNIST),
        LiteraryWork("Dubliners", Author.JOYCE, "2814", 1914, Genre.SHORT_STORY, Period.MODERNIST),
        LiteraryWork("Chamber Music", Author.JOYCE, "5749", 1907, Genre.POETRY, Period.MODERNIST),
    ],
    
    Author.WOOLF: [
        # Note: Most Woolf works are still under copyright, limited Gutenberg availability
        LiteraryWork("Mrs. Dalloway", Author.WOOLF, "69702", 1925, Genre.NOVEL, Period.MODERNIST,
                   url="https://www.gutenberg.org/cache/epub/69702/pg69702.txt"),
        LiteraryWork("To the Lighthouse", Author.WOOLF, "70234", 1927, Genre.NOVEL, Period.MODERNIST,
                   url="https://www.gutenberg.org/cache/epub/70234/pg70234.txt"),
        LiteraryWork("Orlando", Author.WOOLF, "70998", 1928, Genre.NOVEL, Period.MODERNIST,
                   url="https://www.gutenberg.org/cache/epub/70998/pg70998.txt"),
        LiteraryWork("A Room of One's Own", Author.WOOLF, "37282", 1929, Genre.ESSAY, Period.MODERNIST,
                   url="https://www.gutenberg.org/cache/epub/37282/pg37282.txt"),
        LiteraryWork("Monday or Tuesday", Author.WOOLF, "29220", 1921, Genre.SHORT_STORY, Period.MODERNIST),
        LiteraryWork("The Voyage Out", Author.WOOLF, "34194", 1915, Genre.NOVEL, Period.MODERNIST),
        LiteraryWork("Night and Day", Author.WOOLF, "61527", 1919, Genre.NOVEL, Period.MODERNIST),
    ],
}


def get_author_works(author: Author) -> list[LiteraryWork]:
    """Get all literary works for a given author."""
    return AUTHOR_WORKS_MAPPING.get(author, [])


def get_author_metadata(author: Author) -> AuthorMetadata:
    """Get metadata for a given author."""
    return AUTHOR_METADATA[author]


def get_all_supported_authors() -> list[Author]:
    """Get all authors with available works."""
    return list(AUTHOR_WORKS_MAPPING.keys())


def get_works_by_period(period: Period) -> dict[Author, list[LiteraryWork]]:
    """Get all works grouped by authors for a specific period."""
    result = {}
    for author, works in AUTHOR_WORKS_MAPPING.items():
        author_period = AUTHOR_METADATA[author].period
        if author_period == period:
            result[author] = works
    return result


def get_works_by_genre(genre: Genre) -> dict[Author, list[LiteraryWork]]:
    """Get all works grouped by authors for a specific genre."""
    result = {}
    for author, works in AUTHOR_WORKS_MAPPING.items():
        genre_works = [work for work in works if work.genre == genre]
        if genre_works:
            result[author] = genre_works
    return result