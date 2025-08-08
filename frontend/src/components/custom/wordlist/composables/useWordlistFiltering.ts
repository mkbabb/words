import { computed, ref, type Ref } from 'vue';
import type { WordListItem } from '@/types';
import type { WordlistFilters, SortCriterion, MasteryLevel, Temperature } from '@/types/wordlist';

/**
 * Composable for filtering and sorting wordlist items
 */
export function useWordlistFiltering(words: Ref<WordListItem[]>) {
  // Filter state
  const filters = ref<WordlistFilters>({
    mastery: ['bronze', 'silver', 'gold'],
    temperature: [],
    showHotOnly: false,
    showDueOnly: false,
    minScore: 0.4
  });
  
  // Sort state - using simple criteria for this composable
  const sortCriteria = ref<SortCriterion[]>([
    { key: 'word', order: 'asc' } as SortCriterion
  ]);
  
  // Apply filters to words
  const filteredWords = computed(() => {
    let result = [...words.value];
    
    // Apply mastery filter
    if (filters.value.mastery.length > 0 && filters.value.mastery.length < 3) {
      result = result.filter(word => {
        const level = (word.mastery_level || 'bronze') as MasteryLevel;
        return filters.value.mastery.includes(level);
      });
    }
    
    // Apply temperature filter
    if (filters.value.temperature.length > 0) {
      result = result.filter(word => {
        const temp = (word.temperature || 'cold') as Temperature;
        return filters.value.temperature.includes(temp);
      });
    }
    
    // Apply hot only filter
    if (filters.value.showHotOnly) {
      result = result.filter(word => word.temperature === 'hot');
    }
    
    // Apply due only filter
    if (filters.value.showDueOnly) {
      const now = new Date();
      result = result.filter(word => {
        if (!word.review_data?.next_review_date) return false;
        return new Date(word.review_data.next_review_date) <= now;
      });
    }
    
    return result;
  });
  
  // Apply sorting to filtered words
  const sortedWords = computed(() => {
    const sorted = [...filteredWords.value];
    
    // Apply each sort criterion in order
    sortCriteria.value.forEach(criterion => {
      sorted.sort((a, b) => {
        let aVal: any, bVal: any;
        
        // Handle both simple and advanced criteria
        const key = 'key' in criterion ? criterion.key : 
                   ('field' in criterion && criterion.field === 'mastery_level') ? 'mastery' :
                   ('field' in criterion && criterion.field === 'next_review') ? 'next_review' :
                   ('field' in criterion && criterion.field === 'added_at') ? 'created' :
                   'word';
        
        switch (key) {
          case 'word':
            aVal = a.word.toLowerCase();
            bVal = b.word.toLowerCase();
            break;
          case 'mastery':
            const masteryOrder = { bronze: 0, silver: 1, gold: 2 };
            aVal = masteryOrder[a.mastery_level as keyof typeof masteryOrder] || 0;
            bVal = masteryOrder[b.mastery_level as keyof typeof masteryOrder] || 0;
            break;
          case 'temperature':
            const tempOrder = { cold: 0, warm: 1, hot: 2 };
            aVal = tempOrder[a.temperature as keyof typeof tempOrder] || 0;
            bVal = tempOrder[b.temperature as keyof typeof tempOrder] || 0;
            break;
          case 'next_review':
            aVal = new Date(a.review_data?.next_review_date || 0).getTime();
            bVal = new Date(b.review_data?.next_review_date || 0).getTime();
            break;
          case 'created':
            aVal = new Date(a.added_date || 0).getTime();
            bVal = new Date(b.added_date || 0).getTime();
            break;
          default:
            return 0;
        }
        
        const result = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        const order = 'order' in criterion ? criterion.order : criterion.direction;
        return order === 'desc' ? -result : result;
      });
    });
    
    return sorted;
  });
  
  // Filter actions
  const toggleMasteryFilter = (level: MasteryLevel) => {
    const index = filters.value.mastery.indexOf(level);
    if (index >= 0) {
      filters.value.mastery.splice(index, 1);
    } else {
      filters.value.mastery.push(level);
    }
  };
  
  const toggleTemperatureFilter = (temp: Temperature) => {
    const index = filters.value.temperature.indexOf(temp);
    if (index >= 0) {
      filters.value.temperature.splice(index, 1);
    } else {
      filters.value.temperature.push(temp);
    }
  };
  
  const resetFilters = () => {
    filters.value = {
      mastery: ['bronze', 'silver', 'gold'],
      temperature: [],
      showHotOnly: false,
      showDueOnly: false,
      minScore: 0.4
    };
  };
  
  // Sort actions
  const setSortCriteria = (criteria: SortCriterion[]) => {
    sortCriteria.value = criteria;
  };
  
  const addSortCriterion = (criterion: SortCriterion) => {
    sortCriteria.value.push(criterion);
  };
  
  const removeSortCriterion = (index: number) => {
    sortCriteria.value.splice(index, 1);
  };
  
  const resetSort = () => {
    sortCriteria.value = [{ key: 'word', order: 'asc' }];
  };
  
  return {
    // State
    filters,
    sortCriteria,
    
    // Computed
    filteredWords,
    sortedWords,
    
    // Filter actions
    toggleMasteryFilter,
    toggleTemperatureFilter,
    resetFilters,
    
    // Sort actions
    setSortCriteria,
    addSortCriterion,
    removeSortCriterion,
    resetSort
  };
}