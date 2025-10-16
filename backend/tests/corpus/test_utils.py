"""Shared utilities for corpus testing."""

import random
import string

from floridify.corpus.core import Corpus


def create_test_vocabulary(
    size: int,
    unicode_ratio: float = 0.1,
    min_length: int = 3,
    max_length: int = 15,
    seed: int | None = None,
) -> list[str]:
    """Create a test vocabulary with specified characteristics.

    Args:
        size: Number of words to generate
        unicode_ratio: Ratio of Unicode words (0.0 to 1.0)
        min_length: Minimum word length
        max_length: Maximum word length
        seed: Random seed for reproducibility

    Returns:
        List of generated words

    """
    if seed is not None:
        random.seed(seed)

    vocabulary = []
    unicode_count = int(size * unicode_ratio)
    ascii_count = size - unicode_count

    # Generate ASCII words
    for i in range(ascii_count):
        length = random.randint(min_length, max_length)
        word = "".join(random.choices(string.ascii_lowercase, k=length))
        vocabulary.append(word)

    # Generate Unicode words
    unicode_chars = [
        "é",
        "è",
        "ê",
        "ë",
        "à",
        "â",
        "ù",
        "û",
        "ç",
        "ñ",
        "ö",
        "ü",
        "á",
        "í",
        "ó",
        "ú",
        "ý",
        "ä",
        "ï",
        "æ",
        "œ",
        "ø",
        "å",
        "ß",
    ]

    for i in range(unicode_count):
        length = random.randint(min_length, max_length)
        # Mix ASCII and Unicode characters
        chars = []
        for _ in range(length):
            if random.random() < 0.3:  # 30% chance of Unicode char
                chars.append(random.choice(unicode_chars))
            else:
                chars.append(random.choice(string.ascii_lowercase))
        vocabulary.append("".join(chars))

    random.shuffle(vocabulary)
    return vocabulary


def verify_tree_consistency(
    parent: Corpus.Metadata,
    children: list[Corpus.Metadata],
) -> bool:
    """Verify parent-child relationships are consistent.

    Args:
        parent: Parent corpus
        children: List of child corpora

    Returns:
        True if tree is consistent

    Raises:
        AssertionError: If inconsistency found

    """
    # Check all children reference parent
    for child in children:
        assert child.parent_uuid == parent.uuid, (
            f"Child {child.corpus_name} doesn't reference parent {parent.corpus_name}"
        )

    # Check parent references all children
    child_uuids = {child.uuid for child in children}
    parent_child_uuids = set(parent.child_uuids)

    assert child_uuids == parent_child_uuids, "Parent's child_uuids doesn't match actual children"

    # Check no circular references
    assert parent.uuid not in parent.child_uuids, (
        f"Parent {parent.corpus_name} references itself as child"
    )

    for child in children:
        assert child.uuid != parent.uuid, "Child has same UUID as parent"

    return True


def assert_vocabulary_aggregated(
    parent: Corpus.Metadata,
    children: list[Corpus.Metadata],
) -> None:
    """Assert parent vocabulary contains all child vocabularies.

    Args:
        parent: Parent corpus with aggregated vocabulary
        children: Child corpora

    Raises:
        AssertionError: If vocabulary not properly aggregated

    """
    parent_vocab = set(parent.content_inline.get("vocabulary", []))

    # Collect all child vocabularies
    all_child_words = set()
    for child in children:
        child_vocab = child.content_inline.get("vocabulary", [])
        all_child_words.update(child_vocab)

    # Parent should contain all child words
    missing_words = all_child_words - parent_vocab
    assert not missing_words, f"Parent missing words from children: {missing_words}"


def create_corpus_tree(
    depth: int = 3,
    branching_factor: int = 2,
    vocab_size: int = 100,
) -> dict[str, Corpus.Metadata]:
    """Create a test corpus tree with specified structure.

    Args:
        depth: Tree depth
        branching_factor: Number of children per node
        vocab_size: Vocabulary size for each corpus

    Returns:
        Dictionary mapping corpus names to Corpus.Metadata objects

    """
    tree = {}
    counter = 0

    def create_node(level: int, parent_uuid: str | None = None) -> Corpus.Metadata:
        nonlocal counter
        counter += 1

        is_root = parent_uuid is None
        corpus = Corpus.Metadata(
            corpus_name=f"Corpus_L{level}_N{counter}",
            corpus_type="LANGUAGE" if is_root else "LITERATURE",
            is_master=is_root,
            parent_uuid=parent_uuid,
            child_uuids=[],
            content_inline={
                "vocabulary": create_test_vocabulary(vocab_size, unicode_ratio=0.1, seed=counter),
            },
        )

        tree[corpus.corpus_name] = corpus

        # Create children recursively
        if level < depth - 1:
            for _ in range(branching_factor):
                child = create_node(level + 1, corpus.uuid)
                corpus.child_uuids.append(child.uuid)

        return corpus

    # Create root and build tree
    root = create_node(0)
    tree["root"] = root

    return tree


def calculate_tree_stats(root: Corpus.Metadata, all_nodes: dict[str, Corpus.Metadata]) -> dict:
    """Calculate statistics for a corpus tree.

    Args:
        root: Root corpus
        all_nodes: Dictionary of all corpus nodes

    Returns:
        Dictionary with tree statistics

    """
    stats = {
        "total_nodes": len(all_nodes),
        "max_depth": 0,
        "leaf_count": 0,
        "total_vocabulary": set(),
        "avg_children_per_node": 0,
        "max_children": 0,
    }

    def traverse(node: Corpus.Metadata, depth: int = 0):
        stats["max_depth"] = max(stats["max_depth"], depth)

        # Add vocabulary
        vocab = node.content_inline.get("vocabulary", [])
        stats["total_vocabulary"].update(vocab)

        # Count children
        child_count = len(node.child_uuids)
        stats["max_children"] = max(stats["max_children"], child_count)

        if child_count == 0:
            stats["leaf_count"] += 1

        # Traverse children
        for child_uuid in node.child_uuids:
            child = next((n for n in all_nodes.values() if n.uuid == child_uuid), None)
            if child:
                traverse(child, depth + 1)

    traverse(root)

    # Calculate average children
    non_leaf_count = stats["total_nodes"] - stats["leaf_count"]
    if non_leaf_count > 0:
        total_children = sum(len(n.child_uuids) for n in all_nodes.values())
        stats["avg_children_per_node"] = total_children / non_leaf_count

    stats["unique_vocabulary_count"] = len(stats["total_vocabulary"])
    del stats["total_vocabulary"]  # Remove set from stats

    return stats


def simulate_vocabulary_update(
    corpus: Corpus.Metadata,
    add_words: list[str] | None = None,
    remove_words: list[str] | None = None,
) -> list[str]:
    """Simulate vocabulary update operations.

    Args:
        corpus: Corpus to update
        add_words: Words to add
        remove_words: Words to remove

    Returns:
        Updated vocabulary

    """
    vocab = corpus.content_inline.get("vocabulary", []).copy()

    if remove_words:
        vocab = [w for w in vocab if w not in remove_words]

    if add_words:
        # Add only new words (no duplicates)
        existing = set(vocab)
        new_words = [w for w in add_words if w not in existing]
        vocab.extend(new_words)

    corpus.content_inline["vocabulary"] = vocab
    return vocab


def generate_test_statistics(corpus: Corpus.Metadata) -> dict:
    """Generate comprehensive statistics for a corpus.

    Args:
        corpus: Corpus to analyze

    Returns:
        Dictionary of statistics

    """
    vocab = corpus.content_inline.get("vocabulary", [])

    if not vocab:
        return {
            "vocabulary_count": 0,
            "unique_count": 0,
            "avg_word_length": 0,
            "min_word_length": 0,
            "max_word_length": 0,
            "unicode_count": 0,
            "ascii_count": 0,
        }

    unique_vocab = set(vocab)

    # Calculate lengths
    lengths = [len(word) for word in vocab]

    # Count Unicode vs ASCII
    unicode_count = sum(1 for word in vocab if any(ord(c) > 127 for c in word))
    ascii_count = len(vocab) - unicode_count

    return {
        "vocabulary_count": len(vocab),
        "unique_count": len(unique_vocab),
        "avg_word_length": sum(lengths) / len(lengths),
        "min_word_length": min(lengths),
        "max_word_length": max(lengths),
        "unicode_count": unicode_count,
        "ascii_count": ascii_count,
        "duplicate_ratio": 1 - (len(unique_vocab) / len(vocab)) if vocab else 0,
    }
