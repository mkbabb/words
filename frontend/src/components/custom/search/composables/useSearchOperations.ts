import { ref, Ref } from 'vue';
import { useStores } from '@/stores';

interface UseSearchOperationsOptions {
  query: Ref<string>;
  onSearchComplete?: (results: any[]) => void;
}

/**
 * Search operations composable - NO DEBOUNCING for immediate responsiveness
 * All search logic is delegated to the orchestrator
 */
export function useSearchOperations(options: UseSearchOperationsOptions) {
  const { orchestrator } = useStores();
  const { query, onSearchComplete } = options;

  const isSearching = ref(false);

  /**
   * Execute search immediately - no debouncing
   */
  const performSearch = async () => {
    const queryText = query.value || '';
    
    console.log('🔍 SEARCH OPERATIONS - performSearch', {
      query: queryText,
      length: queryText.length
    });

    isSearching.value = true;

    try {
      // Delegate all search logic to orchestrator
      await orchestrator.executeSearch(queryText);
      
      // Notify completion if callback provided
      onSearchComplete?.([]);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      isSearching.value = false;
    }
  };

  /**
   * Clear search state
   */
  const clearSearch = () => {
    query.value = '';
    orchestrator.executeSearch(''); // Clear results
    isSearching.value = false;
  };

  return {
    // State
    isSearching,
    
    // Methods
    performSearch,
    clearSearch,
    
    // No cleanup needed without debouncing
    cleanup: () => {},
  };
}