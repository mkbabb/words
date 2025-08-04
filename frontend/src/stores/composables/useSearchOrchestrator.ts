import { useStores } from '..';
import type { SearchResult } from '@/types';

/**
 * Unified search orchestrator that handles all search operations across modes
 * No debouncing - direct API calls for performance
 */
export function useSearchOrchestrator() {
  const { searchResults, searchBar, searchConfig, loading, ui } = useStores();

  // Mode-specific search handlers
  const searchHandlers = {
    /**
     * Lookup mode handler - dictionary/thesaurus search
     */
    lookup: {
      canSearch: (query: string) => query.trim().length >= 2,
      
      search: async (query: string): Promise<SearchResult[]> => {
        console.log('🔍 LOOKUP - searching for:', query);
        
        // Clear previous results immediately
        searchResults.clearSearchResults();
        
        // Perform search
        const results = await searchResults.search(query);
        
        // Show dropdown if we have results
        if (results.length > 0) {
          searchBar.openDropdown();
          searchBar.setSelectedIndex(0);
        } else {
          searchBar.hideDropdown();
        }
        
        return results;
      }
    },

    /**
     * Wordlist mode handler - list all or search within wordlist
     */
    wordlist: {
      canSearch: () => true, // Always allow search (empty query shows all)
      
      search: async (query: string): Promise<any[]> => {
        const wordlistId = searchConfig.selectedWordlist;
        if (!wordlistId) {
          console.warn('🔍 WORDLIST - no wordlist selected');
          return [];
        }

        console.log('🔍 WORDLIST - searching:', query || '(all words)');
        
        // Use the appropriate endpoint based on query
        const trimmedQuery = query.trim();
        let results: any[] = [];
        
        if (!trimmedQuery) {
          // Empty query - get all words
          results = await searchResults.getWordlistWords(wordlistId);
        } else {
          // Search within wordlist
          results = await searchResults.searchWordlist(wordlistId, trimmedQuery);
        }
        
        // Update wordlist-specific results (store ALL results, not just first 10)
        searchResults.setSearchResults('wordlist', results);
        
        // Show dropdown if we have results and a query
        if (results.length > 0 && trimmedQuery) {
          searchBar.openDropdown();
          searchBar.setSelectedIndex(0);
        } else if (!trimmedQuery) {
          searchBar.hideDropdown();
        }
        
        return results;
      }
    },

    /**
     * Stage mode handler - no search operations
     */
    stage: {
      canSearch: () => false,
      search: async () => []
    }
  };

  /**
   * Main search execution - handles all modes
   * No debouncing for immediate responsiveness
   */
  const executeSearch = async (query: string = ''): Promise<void> => {
    const mode = searchConfig.searchMode;
    const handler = searchHandlers[mode as keyof typeof searchHandlers];
    
    if (!handler) {
      console.warn(`🔍 Unknown search mode: ${mode}`);
      return;
    }

    // Store the query
    searchBar.setQuery(query);

    // Check if we can search in this mode
    if (!handler.canSearch(query)) {
      console.log(`🔍 ${mode.toUpperCase()} - cannot search with query:`, query);
      
      // Clear results for invalid queries in lookup mode
      if (mode === 'lookup') {
        searchResults.clearSearchResults();
        searchBar.hideDropdown();
      }
      return;
    }

    // Disable AI mode (will be re-enabled if needed)
    searchBar.disableAIMode();

    try {
      // Execute mode-specific search
      const results = await handler.search(query);
      
      // Handle AI mode for lookup searches with no results
      if (mode === 'lookup' && results.length === 0 && shouldTriggerAIMode(query)) {
        searchBar.enableAIMode();
      }
    } catch (error) {
      console.error(`🔍 ${mode.toUpperCase()} - search error:`, error);
      searchResults.clearSearchResults();
      searchBar.hideDropdown();
    }
  };

  /**
   * Search for a specific word - used for direct navigation
   */
  const searchWord = async (word: string): Promise<void> => {
    console.log('🔍 ORCHESTRATOR - searchWord:', word);
    
    // Set direct lookup flag to prevent dropdown
    searchBar.isDirectLookup = true;
    
    try {
      // Update query
      searchBar.setQuery(word);
      
      // Clear search results
      searchResults.clearSearchResults();
      
      // Get definition based on current UI mode
      if (ui.mode === 'thesaurus') {
        await getThesaurusData(word);
      } else {
        await getDefinition(word);
      }
    } finally {
      // Reset direct lookup flag
      searchBar.isDirectLookup = false;
    }
  };

  /**
   * Get definition with streaming progress
   */
  const getDefinition = async (word: string, forceRefresh: boolean = false): Promise<void> => {
    console.log('🔍 ORCHESTRATOR - getDefinition:', word, { forceRefresh });
    
    loading.startLoading(`Looking up "${word}"...`);
    
    try {
      await searchResults.getDefinition(word, {
        forceRefresh,
        onProgress: (progress: any) => {
          loading.updateProgress(progress.progress, progress.stage);
        },
        onStageConfig: (config: any) => {
          if (config?.stages) {
            loading.setStageDefinitions('definition', config.stages);
          }
        }
      });
      
      loading.stopLoading();
    } catch (error) {
      loading.stopLoading();
      throw error;
    }
  };

  /**
   * Get thesaurus data
   */
  const getThesaurusData = async (word: string): Promise<void> => {
    console.log('🔍 ORCHESTRATOR - getThesaurusData:', word);
    
    loading.startLoading(`Finding synonyms for "${word}"...`);
    
    try {
      await searchResults.getThesaurusData(word);
      loading.stopLoading();
    } catch (error) {
      loading.stopLoading();
      throw error;
    }
  };

  /**
   * Get AI suggestions with streaming
   */
  const getAISuggestions = async (query: string, count: number = 12) => {
    console.log('🔍 ORCHESTRATOR - getAISuggestions:', { query, count });
    
    loading.startSuggestions('Generating AI suggestions...');
    
    try {
      const result = await searchResults.getAISuggestions(query, count, {
        onProgress: (progress: any) => {
          loading.updateSuggestionsProgress(progress.progress, progress.stage);
        }
      });
      
      loading.stopSuggestions();
      return result;
    } catch (error) {
      loading.stopSuggestions();
      throw error;
    }
  };

  // Utility functions
  const shouldTriggerAIMode = (query: string): boolean => {
    if (!query || query.length < 5) return false;
    
    const isQuestion = /^(what|how|why|when|where|who|which|whose|whom)\s/i.test(query);
    const hasQuestionMark = query.includes('?');
    const isLongPhrase = query.split(' ').length > 3;
    const hasSpecialPattern = /(\s(is|are|was|were|means?|definition|define)\s)/i.test(query);
    
    return isQuestion || hasQuestionMark || (isLongPhrase && hasSpecialPattern);
  };

  return {
    // Main search method
    executeSearch,
    
    // Direct word operations
    searchWord,
    search: executeSearch, // Alias for backward compatibility
    getDefinition,
    getThesaurusData,
    getAISuggestions,
  };
}