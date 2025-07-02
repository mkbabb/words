"""Data models for word list management."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field


class WordFrequency(BaseModel):
    """Word with frequency tracking for interest measurement."""
    
    text: str = Field(..., description="The word text")
    frequency: int = Field(default=1, ge=1, description="Number of occurrences in list")
    created_at: datetime = Field(
        default_factory=datetime.now, description="First occurrence timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    
    def increment(self) -> None:
        """Increment frequency and update timestamp."""
        self.frequency += 1
        self.updated_at = datetime.now()


class WordList(Document):
    """Word list with metadata and frequency tracking."""
    
    name: str = Field(..., description="Human-readable list name")
    hash_id: str = Field(..., description="Content-based hash identifier")
    words: list[WordFrequency] = Field(default_factory=list, description="Words with frequency")
    total_words: int = Field(default=0, ge=0, description="Total word count")
    unique_words: int = Field(default=0, ge=0, description="Unique word count")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Settings:
        name = "word_lists"
        indexes = [
            "name",
            "hash_id",
            [("name", "text")],
            "created_at",
            "updated_at",
        ]
    
    @classmethod
    def generate_hash(cls, words: list[str]) -> str:
        """Generate content-based hash from word list."""
        # Sort words to ensure consistent hash regardless of order
        sorted_words = sorted(set(w.lower().strip() for w in words if w.strip()))
        content = "|".join(sorted_words)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def add_words(self, new_words: list[str]) -> None:
        """Add words to the list, updating frequencies for duplicates."""
        word_map = {wf.text.lower(): wf for wf in self.words}
        
        for word in new_words:
            word_clean = word.strip()
            if not word_clean:
                continue
                
            word_lower = word_clean.lower()
            if word_lower in word_map:
                word_map[word_lower].increment()
            else:
                new_word_freq = WordFrequency(text=word_clean)
                self.words.append(new_word_freq)
                word_map[word_lower] = new_word_freq
        
        self.update_stats()
    
    def update_stats(self) -> None:
        """Update word count statistics and timestamp."""
        self.unique_words = len(self.words)
        self.total_words = sum(wf.frequency for wf in self.words)
        self.updated_at = datetime.now()
        
        # Update hash based on current words
        word_texts = [wf.text for wf in self.words]
        self.hash_id = self.generate_hash(word_texts)
    
    def get_most_frequent(self, limit: int = 10) -> list[WordFrequency]:
        """Get most frequent words (highest interest)."""
        return sorted(self.words, key=lambda w: w.frequency, reverse=True)[:limit]
    
    def get_word_frequency(self, word: str) -> int:
        """Get frequency of a specific word."""
        word_lower = word.lower()
        for wf in self.words:
            if wf.text.lower() == word_lower:
                return wf.frequency
        return 0