"""Utility functions for wordlist searching with TTL corpus caching."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ....models import Word
from ....search.corpus import get_corpus_cache
from ...repositories import WordListRepository

# TTL corpus cache functions for wordlist search


def get_adaptive_min_score(query: str, base_score: float = 0.4) -> float:
    """
    Calculate adaptive minimum score based on query length.
    
    Short queries get lower thresholds to allow more partial matches.
    Longer queries maintain higher thresholds for precision.
    
    Args:
        query: Search query string
        base_score: Base minimum score for longer queries
        
    Returns:
        Adaptive minimum score between 0.2 and base_score
    """
    query_len = len(query.strip())
    
    if query_len <= 2:
        return 0.2  # Very permissive for 1-2 character queries
    elif query_len <= 4:
        return 0.25  # Permissive for 3-4 character queries
    elif query_len <= 6:
        return 0.3   # Moderate for 5-6 character queries
    else:
        return base_score  # Standard threshold for longer queries


async def search_wordlist_names(
    query: str,
    repo: WordListRepository,
    ttl_hours: float | None = None,
    max_results: int = 20,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """
    Search wordlist names using TTL corpus cache.
    
    Creates a temporary corpus of all wordlist names if one doesn't exist,
    then performs fuzzy search on that corpus.
    
    Args:
        query: Search query string
        repo: WordListRepository instance
        ttl_hours: TTL for the corpus cache (default: 1 hour)
        max_results: Maximum number of results to return
        min_score: Minimum fuzzy match score (0.0-1.0)
        
    Returns:
        List of matching wordlists with search scores
    """
    cache = await get_corpus_cache()
    corpus_id = "wordlist_names"
    
    # Check if we have a valid corpus
    corpus_info = cache.get_corpus_info(corpus_id)
    if not corpus_info:
        # Fetch all wordlist names to build corpus
        all_wordlists, _ = await repo.list(
            filter_dict={},
            pagination=None,  # Get all for corpus building
        )
        
        # Extract names for corpus
        wordlist_names = [wl.name for wl in all_wordlists if wl.name]
        
        if not wordlist_names:
            return []
            
        # Create new corpus - use phrases parameter for multi-word names
        # Extract single words and multi-word phrases
        single_words = []
        phrases = []
        
        for name in wordlist_names:
            if " " in name.strip():
                phrases.append(name)
            else:
                single_words.append(name)
        
        # Also add individual words from phrases for partial matching
        for phrase in phrases:
            words_in_phrase = phrase.lower().split()
            single_words.extend(words_in_phrase)
        
        # Remove duplicates
        single_words = list(set(single_words))
        
        corpus_id = cache.create_corpus(
            words=single_words,
            phrases=phrases,
            name="Wordlist Names",  # Consistent with WordList.get_names_corpus_name()
            ttl_hours=ttl_hours,
        )
    
    # Use adaptive scoring if not specified
    if min_score is None:
        min_score = get_adaptive_min_score(query, base_score=0.3)
    
    # Search the corpus
    search_result = await cache.search_corpus(
        corpus_id=corpus_id,
        query=query,
        max_results=max_results,
        min_score=min_score,
    )
    
    results = search_result["results"]
    if not results:
        return []
    
    # Process search results - prioritize phrases over individual words
    matched_wordlists = []
    processed_names = set()
    
    # First, process phrase matches (full wordlist names)
    for result in results:
        if result["is_phrase"]:
            name = result["word"]
            if name not in processed_names:
                wordlist = await repo.find_by_name(name)
                if wordlist:
                    populated_data = await repo.populate_words(wordlist)
                    matched_wordlists.append({
                        "wordlist": populated_data,
                        "score": result["score"],
                    })
                    processed_names.add(name)
    
    # Then, process word matches (find wordlists containing these words)
    for result in results:
        if not result["is_phrase"]:
            search_word = result["word"]
            # Find wordlists that contain this word in their name
            for name in wordlist_names:
                if name not in processed_names and search_word.lower() in name.lower():
                    wordlist = await repo.find_by_name(name)
                    if wordlist:
                        populated_data = await repo.populate_words(wordlist)
                        matched_wordlists.append({
                            "wordlist": populated_data,
                            "score": result["score"] * 0.8,  # Slightly lower score for partial matches
                        })
                        processed_names.add(name)
    
    # Sort by score descending
    matched_wordlists.sort(key=lambda x: x["score"], reverse=True)
    
    return matched_wordlists


async def search_words_in_wordlist(
    wordlist_id: PydanticObjectId,
    query: str,
    repo: WordListRepository,
    ttl_hours: float | None = None,
    max_results: int = 50,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """
    Search words within a specific wordlist using TTL corpus cache.
    
    Creates a temporary corpus of words in the wordlist if one doesn't exist,
    then performs fuzzy search on that corpus.
    
    Args:
        wordlist_id: ID of the wordlist to search within
        query: Search query string
        repo: WordListRepository instance
        ttl_hours: TTL for the corpus cache (default: 0.5 hours)
        max_results: Maximum number of results to return
        min_score: Minimum fuzzy match score (0.0-1.0)
        
    Returns:
        List of matching words with metadata and search scores
    """
    cache = await get_corpus_cache()
    corpus_id = f"wordlist_words_{wordlist_id}"
    
    # Get the wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None
    
    # Check if we have a valid corpus for this wordlist
    corpus_info = cache.get_corpus_info(corpus_id)
    if not corpus_info:
        # Fetch word documents to build corpus
        word_ids = [w.word_id for w in wordlist.words if w.word_id]
        
        if not word_ids:
            return []
            
        words = await Word.find({"_id": {"$in": word_ids}}).to_list()
        word_texts = [word.text for word in words if word.text]
        
        if not word_texts:
            return []
            
        # Create new corpus for this wordlist's words
        corpus_id = cache.create_corpus(
            words=word_texts,
            name=wordlist.get_words_corpus_name(),
            ttl_hours=ttl_hours,
        )
    
    # Use adaptive scoring if not specified
    if min_score is None:
        min_score = get_adaptive_min_score(query, base_score=0.4)
    
    # Search the corpus
    search_result = await cache.search_corpus(
        corpus_id=corpus_id,
        query=query,
        max_results=max_results,
        min_score=min_score,
    )
    
    results = search_result["results"]
    if not results:
        return []
    
    # Build word metadata map
    word_ids = [w.word_id for w in wordlist.words if w.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_item_map = {str(w.word_id): w for w in wordlist.words}
    
    # Convert search results to word data with metadata
    matched_words = []
    for result in results:
        # Find the word document and wordlist item
        word_doc = next((w for w in words if w.text == result["word"]), None)
        if not word_doc:
            continue
            
        word_item = word_item_map.get(str(word_doc.id))
        if not word_item:
            continue
        
        matched_words.append({
            "word": word_doc.text,
            "score": result["score"],
            "mastery_level": word_item.mastery_level,
            "review_count": word_item.review_data.repetitions if word_item.review_data else 0,
            "notes": word_item.notes,
            "tags": word_item.tags,
            "frequency": word_item.frequency,
        })
    
    return matched_words


async def invalidate_wordlist_corpus(wordlist_id: PydanticObjectId) -> None:
    """
    Invalidate TTL corpus cache for a specific wordlist.
    
    Call this when a wordlist's words have been modified to ensure
    fresh corpus creation on next search.
    
    Args:
        wordlist_id: ID of the wordlist whose corpus should be invalidated
    """
    cache = await get_corpus_cache()
    
    # Use consistent naming pattern without creating WordList object
    corpus_name = f"Words in wordlist {wordlist_id}"
    
    # Remove any corpora for this specific wordlist
    removed_count = cache.remove_corpus_by_name(corpus_name)
    if removed_count > 0:
        print(f"Invalidated {removed_count} corpus(es) for wordlist {wordlist_id}")


async def invalidate_wordlist_names_corpus() -> None:
    """
    Invalidate TTL corpus cache for wordlist names.
    
    Call this when wordlist names have been modified (create/update/delete)
    to ensure fresh corpus creation on next search.
    """
    cache = await get_corpus_cache()
    
    # Remove wordlist names corpus using consistent naming
    corpus_name = "Wordlist Names"  # Matches WordList.get_names_corpus_name()
    removed_count = cache.remove_corpus_by_name(corpus_name)
    if removed_count > 0:
        print(f"Invalidated {removed_count} wordlist names corpus(es)")


async def get_corpus_stats() -> dict[str, Any]:
    """Get statistics about the corpus cache usage."""
    cache = await get_corpus_cache()
    return cache.get_stats()