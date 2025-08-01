import { ref, Ref } from 'vue';
import { useStores } from '@/stores';
import { shouldTriggerAIMode } from '../utils/ai-query';

interface UseSearchOperationsOptions {
  query: Ref<string>;
  onSearchComplete?: (results: any[]) => void;
}

/**
 * Handles search operations with debouncing and AI mode detection
 * Manages search timing and result processing
 */
export function useSearchOperations(options: UseSearchOperationsOptions) {
  const { searchBar, searchConfig, searchResults, loading, orchestrator } = useStores();
  const { query, onSearchComplete } = options;

  // Timer management
  const searchTimer = ref<ReturnType<typeof setTimeout> | undefined>();
  const isSearching = ref(false);

  /**
   * Clear any pending search timers
   */
  const clearSearchTimer = () => {
    if (searchTimer.value) {
      clearTimeout(searchTimer.value);
      searchTimer.value = undefined;
    }
  };

  /**
   * Perform debounced search operation
   */
  const performSearch = () => {
    console.log('🔍 SEARCH OPERATIONS - performSearch called', {
      query: query.value,
      queryLength: query.value?.length || 0,
      isDirectLookup: searchBar.isDirectLookup,
      isSwitchingModes: searchBar.isSwitchingModes
    });
    
    clearSearchTimer();
    
    // Skip search if this is a direct lookup from sidebar/controls
    if (searchBar.isDirectLookup) {
      console.log('🔍 SEARCH OPERATIONS - Skipping search due to direct lookup');
      searchResults.clearSearchResults();
      searchBar.hideDropdown();
      return;
    }
    
    // Skip search if we're switching modes
    if (searchBar.isSwitchingModes) {
      console.log('🔍 SEARCH OPERATIONS - Skipping search due to mode switching');
      searchResults.clearSearchResults();
      searchBar.hideDropdown();
      return;
    }
    
    searchBar.setQuery(query.value);

    if (!query.value || query.value.length < 2) {
      searchResults.clearSearchResults();
      searchBar.hideDropdown();
      isSearching.value = false;
      searchBar.disableAIMode();
      return;
    }

    isSearching.value = true;
    // Don't set loading.isSearching here - that's for actual word lookups, not searches

    searchTimer.value = setTimeout(async () => {
      try {
        const results = await orchestrator.search(query.value);
        // Results are automatically set in the searchResults store by the search method
        searchBar.setSelectedIndex(0);

        // Show results if we have them and not doing a direct lookup
        if (results.length > 0 && !searchBar.isDirectLookup) {
          searchBar.showDropdown();
        } else {
          searchBar.hideDropdown();
        }

        // Activate AI mode (but only in lookup mode and not during direct lookups)
        if (searchConfig.searchMode === 'lookup' && results.length === 0 && shouldTriggerAIMode(query.value) && !searchBar.isDirectLookup) {
          searchBar.enableAIMode();
          // AI mode is now non-persisted - already set above
          // aiQueryText removed - router handles query persistence
        } else if (!searchBar.isDirectLookup) {
          // Reset AI mode if not in lookup mode or not meeting AI criteria
          searchBar.disableAIMode();
          // AI mode is now non-persisted - already set above
          // aiQueryText removed - router handles query persistence
        }

        // Call completion callback if provided
        onSearchComplete?.(results);
      } catch (error) {
        console.error('Search error:', error);
        searchResults.clearSearchResults();
      } finally {
        isSearching.value = false;
        // Don't set loading.isSearching here either
      }
    }, 200);
  };

  /**
   * Clear search state
   */
  const clearSearch = () => {
    clearSearchTimer();
    searchBar.setQuery('');
    searchResults.clearSearchResults();
    searchBar.hideDropdown();
    searchBar.disableAIMode();
    isSearching.value = false;
  };

  // Cleanup on unmount
  const cleanup = () => {
    clearSearchTimer();
  };

  return {
    // State
    isSearching,
    
    // Methods
    performSearch,
    clearSearch,
    clearSearchTimer,
    cleanup,
  };
}