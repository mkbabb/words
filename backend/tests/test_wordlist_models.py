"""Test WordList models with learning features."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from floridify.list.models import (
    LearningStats,
    MasteryLevel,
    ReviewData,
    Temperature,
    WordList,
    WordListItem,
)


def test_review_data_sm2_algorithm():
    """Test SM-2 spaced repetition algorithm."""
    review = ReviewData()
    
    # Initial state
    assert review.repetitions == 0
    assert review.ease_factor == 2.5
    assert review.interval == 1
    
    # First review - perfect (quality=5)
    review.update_sm2(5)
    assert review.repetitions == 1
    assert review.interval == 1
    assert review.ease_factor == 2.6  # Should increase
    
    # Second review - perfect
    review.update_sm2(5)
    assert review.repetitions == 2
    assert review.interval == 6
    assert review.ease_factor == 2.7
    
    # Third review - good (quality=4)
    review.update_sm2(4)
    assert review.repetitions == 3
    assert review.interval == round(6 * 2.7)  # 16
    # ease_factor = 2.7 + 0.1 - (5-4)*(0.08 + (5-4)*0.02) = 2.7 + 0.1 - 0.1 = 2.7
    assert review.ease_factor == 2.7
    
    # Fail (quality=2)
    review.update_sm2(2)
    assert review.repetitions == 0  # Reset
    assert review.interval == 1  # Reset
    assert review.lapse_count == 1
    

def test_wordlist_item():
    """Test WordListItem functionality."""
    word = WordListItem(text="ephemeral")
    
    # Initial state
    assert word.text == "ephemeral"
    assert word.frequency == 1
    assert word.mastery_level == MasteryLevel.BRONZE
    assert word.temperature == Temperature.COLD
    
    # Test increment
    word.increment()
    assert word.frequency == 2
    
    # Test mark visited
    word.mark_visited()
    assert word.temperature == Temperature.HOT
    assert word.last_visited is not None
    
    # Test review
    word.review(5)
    assert word.review_data.repetitions == 1
    assert word.temperature == Temperature.HOT
    
    # Test mastery level upgrade
    for _ in range(5):
        word.review(5)
    assert word.mastery_level == MasteryLevel.SILVER
    

def test_wordlist_without_db():
    """Test WordList functionality without database."""
    # Create WordList without Beanie initialization
    wordlist = WordList.model_construct(
        name="SAT Vocabulary",
        description="Essential SAT words",
        hash_id="test123",
        words=[],
        learning_stats=LearningStats()
    )
    
    # Add words
    words = ["ephemeral", "ubiquitous", "ephemeral", "paradigm"]
    wordlist.add_words(words)
    
    assert wordlist.unique_words == 3
    assert wordlist.total_words == 4
    
    # Check frequency tracking
    ephemeral = wordlist.get_word_item("ephemeral")
    assert ephemeral is not None
    assert ephemeral.frequency == 2
    
    # Test most frequent
    most_freq = wordlist.get_most_frequent(2)
    assert len(most_freq) == 2
    assert most_freq[0].text == "ephemeral"
    
    # Test review scheduling
    now = datetime.now()
    # Set only first 2 words as overdue
    for i, word in enumerate(wordlist.words):
        if i < 2:
            word.review_data.next_review_date = now - timedelta(days=1)
        else:
            word.review_data.next_review_date = now + timedelta(days=1)
    
    due = wordlist.get_due_for_review()
    assert len(due) == 2
    
    # Test mastery levels
    wordlist.words[0].mastery_level = MasteryLevel.GOLD
    gold_words = wordlist.get_by_mastery(MasteryLevel.GOLD)
    assert len(gold_words) == 1
    
    # Test learning stats
    wordlist.update_stats()
    assert wordlist.learning_stats.words_mastered == 1
    

def test_learning_stats():
    """Test learning statistics."""
    stats = LearningStats()
    
    # Initial state
    assert stats.total_reviews == 0
    assert stats.streak_days == 0
    
    # Test streak calculation with mock WordList
    wordlist = WordList.model_construct(
        name="Test",
        hash_id="test",
        words=[],
        learning_stats=LearningStats()
    )
    wordlist.record_study_session(30)
    
    assert wordlist.learning_stats.study_time_minutes == 30
    assert wordlist.learning_stats.streak_days == 1
    assert wordlist.learning_stats.last_study_date is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])