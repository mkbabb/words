"""Reusable quality validation functions for AI synthesis output.

All validators are pure functions — no AI calls, no I/O. They use heuristic
checks on structure, content, and consistency.
"""

from __future__ import annotations

from tests.quality.models import FixtureDefinition, GoldenFixture

# ---------------------------------------------------------------------------
# Structural validators
# ---------------------------------------------------------------------------


def validate_entry_completeness(fixture: GoldenFixture) -> list[str]:
    """Check that all required top-level fields are present."""
    errors = []
    if not fixture.word:
        errors.append("Missing or empty word")
    if not fixture.definitions:
        errors.append("Missing or empty definitions")
    return errors


def validate_definition_fields(definition: FixtureDefinition) -> list[str]:
    """Check that a single definition has required fields."""
    errors = []
    if not definition.part_of_speech:
        errors.append("Definition missing part_of_speech")
    if not definition.text:
        errors.append("Definition missing text")
    return errors


def validate_definition_count_range(
    definitions: list[FixtureDefinition],
    min_count: int,
    max_count: int,
) -> tuple[bool, str]:
    """Check definition count is within expected range."""
    count = len(definitions)
    ok = min_count <= count <= max_count
    msg = f"Expected {min_count}-{max_count} definitions, got {count}"
    return ok, msg


# ---------------------------------------------------------------------------
# Semantic validators
# ---------------------------------------------------------------------------


def validate_synonyms_not_duplicate_antonyms(definition: FixtureDefinition) -> list[str]:
    """Check that synonyms and antonyms don't overlap."""
    errors = []
    synonyms = {s.lower() for s in definition.synonyms}
    antonyms = {a.lower() for a in definition.antonyms}
    overlap = synonyms & antonyms
    if overlap:
        errors.append(f"Synonym/antonym overlap: {overlap}")
    return errors


def validate_synonyms_not_contain_word(word: str, synonyms: list[str]) -> list[str]:
    """Check that synonyms don't include the word itself."""
    errors = []
    word_lower = word.lower()
    for syn in synonyms:
        if syn.lower() == word_lower:
            errors.append(f"Synonym is self-referential: '{syn}'")
    return errors


def validate_language_consistency(fixture: GoldenFixture, expected_language: str) -> list[str]:
    """Check that language field matches expected value."""
    errors = []
    if fixture.language.lower() != expected_language.lower():
        errors.append(f"Expected language '{expected_language}', got '{fixture.language}'")
    return errors


def validate_cluster_diversity(definitions: list[FixtureDefinition]) -> tuple[bool, str]:
    """Check that definitions span multiple meaning clusters."""
    clusters = set()
    for d in definitions:
        if d.meaning_cluster:
            clusters.add(d.meaning_cluster.id)
    has_diversity = len(clusters) > 1
    msg = f"Found {len(clusters)} unique clusters"
    return has_diversity, msg


def validate_pos_coverage(
    definitions: list[FixtureDefinition], expected_pos: set[str]
) -> tuple[bool, str]:
    """Check that expected parts of speech are represented."""
    actual_pos = {d.part_of_speech.lower() for d in definitions if d.part_of_speech}
    missing = expected_pos - actual_pos
    ok = len(missing) == 0
    msg = (
        f"POS coverage: {actual_pos}. Missing: {missing}"
        if missing
        else f"POS coverage: {actual_pos}"
    )
    return ok, msg


def validate_definition_text_length(definitions: list[FixtureDefinition]) -> list[str]:
    """Check that definition texts are reasonable length."""
    errors = []
    for i, d in enumerate(definitions):
        if len(d.text) < 10:
            errors.append(f"Definition {i} too short ({len(d.text)} chars): '{d.text}'")
        elif len(d.text) > 500:
            errors.append(f"Definition {i} too long ({len(d.text)} chars)")
    return errors


def validate_no_duplicate_definitions(definitions: list[FixtureDefinition]) -> list[str]:
    """Check for exact duplicate definition texts."""
    errors = []
    seen: dict[str, int] = {}
    for i, d in enumerate(definitions):
        text = d.text.strip().lower()
        if text in seen:
            errors.append(f"Duplicate definition at index {i} and {seen[text]}: '{text[:60]}...'")
        else:
            seen[text] = i
    return errors


def validate_examples_contain_word(word: str, examples: list[str]) -> list[str]:
    """Check that example sentences contain the word (case-insensitive)."""
    errors = []
    word_lower = word.lower()
    for i, ex in enumerate(examples):
        if word_lower not in ex.lower():
            errors.append(f"Example {i} doesn't contain '{word}': '{ex[:80]}...'")
    return errors
