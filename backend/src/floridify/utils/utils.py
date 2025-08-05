"""General utility functions."""

import uuid

from .logging import get_logger

logger = get_logger(__name__)


def generate_slug(word_count: int = 3) -> str:
    """Generate human-readable slug.
    
    Creates a memorable slug like 'myrtle-goldfish-swim' using coolname library.
    Falls back to UUID if coolname fails.
    
    Args:
        word_count: Number of words in the slug (default 3)
        
    Returns:
        Generated slug string
        
    Examples:
        >>> slug = generate_slug()  # 'happy-penguin-dance'
        >>> slug = generate_slug(2)  # 'blue-tiger'
    """
    try:
        import coolname  # type: ignore[import-untyped]
        slug: str = coolname.generate_slug(word_count)
        logger.debug(f"Generated slug: {slug}")
        return slug
    except Exception as e:
        logger.warning(f"Failed to generate cool name: {e}, falling back to UUID")
        # Fallback to UUID (first 8 chars for brevity)
        return str(uuid.uuid4())[:8]


def generate_deterministic_id(*parts: str) -> str:
    """Generate deterministic ID from parts.
    
    Sorts parts alphabetically to ensure consistent ID generation
    regardless of input order.
    
    Args:
        *parts: Variable number of string parts to combine
        
    Returns:
        Deterministic ID string
        
    Examples:
        >>> generate_deterministic_id('en', 'fr', 'de')  # 'de-en-fr'
        >>> generate_deterministic_id('fr', 'en')  # 'en-fr'
    """
    sorted_parts = sorted(part.lower().strip() for part in parts if part.strip())
    return "-".join(sorted_parts)