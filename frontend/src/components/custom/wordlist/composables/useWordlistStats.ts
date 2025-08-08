import { computed, type Ref } from 'vue';
import type { WordListItem } from '@/types';
import type { MasteryStats } from '@/types/wordlist';

/**
 * Composable for calculating wordlist statistics
 */
export function useWordlistStats(words: Ref<WordListItem[]>) {
  // Calculate mastery distribution
  const masteryStats = computed<MasteryStats>(() => {
    if (!words.value || words.value.length === 0) {
      return { bronze: 0, silver: 0, gold: 0, total: 0, dueForReview: 0 };
    }
    
    const stats = words.value.reduce((acc, word) => {
      const level = word.mastery_level || 'bronze';
      acc[level] = (acc[level] || 0) + 1;
      acc.total++;
      
      // Check if due for review
      if (word.review_data?.next_review_date) {
        const nextReview = new Date(word.review_data.next_review_date);
        if (nextReview <= new Date()) {
          acc.dueForReview++;
        }
      }
      
      return acc;
    }, { bronze: 0, silver: 0, gold: 0, total: 0, dueForReview: 0 } as MasteryStats);
    
    return stats;
  });
  
  // Calculate overall progress percentage
  const progressPercentage = computed(() => {
    const stats = masteryStats.value;
    if (stats.total === 0) return 0;
    
    // Weight: bronze=0.33, silver=0.66, gold=1.0
    const weighted = (stats.bronze * 0.33) + (stats.silver * 0.66) + (stats.gold * 1.0);
    return Math.round((weighted / stats.total) * 100);
  });
  
  // Get words due for review
  const dueWords = computed(() => {
    const now = new Date();
    return words.value.filter(word => {
      if (!word.review_data?.next_review_date) return false;
      return new Date(word.review_data.next_review_date) <= now;
    });
  });
  
  // Get hot words (frequently missed or due soon)
  const hotWords = computed(() => {
    return words.value.filter(word => word.temperature === 'hot');
  });
  
  return {
    masteryStats,
    progressPercentage,
    dueWords,
    hotWords
  };
}