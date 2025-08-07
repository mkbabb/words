"""General utility functions."""

import coolname

from .logging import get_logger

logger = get_logger(__name__)


def generate_slug(word_count: int = 3) -> str:
    """Generate human-readable slug.

    Creates a memorable slug like 'myrtle-goldfish-swim' using coolname library.

    Args:
        word_count: Number of words in the slug (default 3)

    Returns:
        Generated slug string

    Examples:
        >>> slug = generate_slug()  # 'happy-penguin-dance'
        >>> slug = generate_slug(2)  # 'blue-tiger'
    """

    slug: str = coolname.generate_slug(word_count)
    logger.debug(f"Generated slug: {slug}")
    return slug
