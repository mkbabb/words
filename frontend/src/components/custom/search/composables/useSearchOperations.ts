import { ref, Ref } from 'vue';
import { useAppStore } from '@/stores';
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
  const store = useAppStore();
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
      isDirectLookup: store.isDirectLookup,
      // isSwitchingModes: store.isSwitchingModes
    });
    
    clearSearchTimer();
    
    // Skip search if this is a direct lookup from sidebar/controls
    if (store.isDirectLookup) {
      console.log('🔍 SEARCH OPERATIONS - Skipping search due to direct lookup');
      store.searchResults = [];
      store.showSearchResults = false;
      return;
    }
    
    store.searchQuery = query.value;

    if (!query.value || query.value.length < 2) {
      store.searchResults = [];
      store.showSearchResults = false;
      isSearching.value = false;
      store.isAIQuery = false;
      store.showSparkle = false;
      return;
    }

    isSearching.value = true;
    // Don't set store.isSearching here - that's for actual word lookups, not searches

    searchTimer.value = setTimeout(async () => {
      try {
        const results = await store.search(query.value);
        store.searchResults = results.slice(0, 8);
        store.searchSelectedIndex = 0;

        if (store.sessionState) {
          store.sessionState.searchResults = results;
        }

        // Show results if we have them and not doing a direct lookup
        store.showSearchResults = results.length > 0 && !store.isDirectLookup;

        // Activate AI mode (but not during direct lookups)
        if (results.length === 0 && shouldTriggerAIMode(query.value) && !store.isDirectLookup) {
          store.isAIQuery = true;
          store.showSparkle = true;
          store.sessionState.isAIQuery = true;
          store.sessionState.aiQueryText = query.value;
        } else if (!store.isDirectLookup) {
          // Only reset AI mode if not doing a direct lookup (preserve existing state during lookup)
          store.isAIQuery = false;
          store.showSparkle = false;
          store.sessionState.isAIQuery = false;
          store.sessionState.aiQueryText = '';
        }

        // Call completion callback if provided
        onSearchComplete?.(results);
      } catch (error) {
        console.error('Search error:', error);
        store.searchResults = [];
      } finally {
        isSearching.value = false;
        // Don't set store.isSearching here either
      }
    }, 200);
  };

  /**
   * Clear search state
   */
  const clearSearch = () => {
    clearSearchTimer();
    store.searchQuery = '';
    store.searchResults = [];
    store.showSearchResults = false;
    store.isAIQuery = false;
    store.showSparkle = false;
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