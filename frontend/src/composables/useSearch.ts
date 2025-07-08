import { ref, computed } from 'vue';
import { useDebounce } from '@vueuse/core';
import { useAppStore } from '@/stores';
import { dictionaryApi } from '@/utils/api';

export function useSearch() {
  const store = useAppStore();
  const suggestions = ref<string[]>([]);
  const isLoadingSuggestions = ref(false);

  // Debounced search input
  const debouncedQuery = useDebounce(computed(() => store.searchQuery), 300);

  // Get search suggestions
  async function getSuggestions(prefix: string) {
    if (!prefix.trim() || prefix.length < 2) {
      suggestions.value = [];
      return;
    }

    isLoadingSuggestions.value = true;
    
    try {
      const response = await dictionaryApi.getSuggestions(prefix);
      
      if (response.success) {
        suggestions.value = response.data;
      }
    } catch (error) {
      console.error('Suggestions error:', error);
      suggestions.value = [];
    } finally {
      isLoadingSuggestions.value = false;
    }
  }

  // Search with debouncing
  const performSearch = async (query: string) => {
    if (!query.trim()) return;
    await store.searchWord(query);
  };

  // Search on word click
  const searchWord = async (word: string) => {
    store.searchQuery = word;
    await performSearch(word);
  };

  return {
    suggestions,
    isLoadingSuggestions,
    debouncedQuery,
    getSuggestions,
    performSearch,
    searchWord,
  };
}