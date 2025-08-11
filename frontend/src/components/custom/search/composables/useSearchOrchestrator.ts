import { ref, Ref, computed } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { lookupApi, aiApi } from '@/api';
import type { SearchResult, WordListItem, WordSuggestionResponse, SynthesizedDictionaryEntry } from '@/types';

interface UseSearchOrchestratorOptions {
  query: Ref<string>;
  onSearchComplete?: (results: any[]) => void;
}

/**
 * Central orchestration composable for all search operations
 * 
 * ARCHITECTURE:
 * - This composable handles ALL search logic and API calls
 * - Stores handle ONLY state management, never API calls
 * - Each mode has clearly separated operations
 * - No legacy patterns or fallback behaviors
 */
export function useSearchOrchestrator(options: UseSearchOrchestratorOptions) {
  const searchBar = useSearchBarStore();
  const lookupMode = useLookupMode();
  const wordlistMode = useWordlistMode();
  const { query, onSearchComplete } = options;

  const isSearching = ref(false);
  const searchError = ref<Error | null>(null);

  // ============================================================================
  // SEARCH EXECUTION - MODE ROUTER
  // ============================================================================
  
  /**
   * Main search dispatcher - routes to mode-specific handlers
   * NO FALLBACKS - each mode must handle its own search completely
   */
  const performSearch = async () => {
    const queryText = query.value?.trim() || '';
    const mode = searchBar.searchMode;
    
    console.log('🔍 ORCHESTRATOR: Executing search', {
      mode,
      query: queryText,
      length: queryText.length
    });

    // Clear previous errors
    searchError.value = null;
    isSearching.value = true;

    try {
      let results: any[] = [];
      
      // Route to mode-specific handler - NO FALLBACKS
      switch (mode) {
        case 'lookup':
          results = await executeLookupSearch(queryText);
          break;
          
        case 'wordlist':
          results = await executeWordlistSearch(queryText);
          break;
          
        case 'word-of-the-day':
          results = await executeWordOfTheDaySearch(queryText);
          break;
          
        case 'stage':
          results = await executeStageSearch(queryText);
          break;
          
        default:
          console.warn(`⚠️ Unhandled search mode: ${mode}`);
          results = [];
      }
      
      // Notify completion callback if provided
      if (onSearchComplete) {
        onSearchComplete(results);
      }
      
      return results;
    } catch (error) {
      console.error('❌ Search error:', error);
      searchError.value = error as Error;
      searchBar.clearResults();
      searchBar.hideDropdown();
      return [];
    } finally {
      isSearching.value = false;
    }
  };

  // ============================================================================
  // LOOKUP MODE OPERATIONS
  // ============================================================================
  
  /**
   * Execute search for lookup mode (dictionary/thesaurus)
   * Handles: autocomplete, definition lookups, synonym searches
   */
  const executeLookupSearch = async (queryText: string): Promise<SearchResult[]> => {
    // Minimum query length for lookup mode
    if (queryText.length < 2) {
      searchBar.clearResults();
      searchBar.hideDropdown();
      return [];
    }

    // Clear previous results
    searchBar.clearResults();
    
    // Execute search via mode store
    const results = await lookupMode.search(queryText);
    
    // Update UI based on results
    if (results.length > 0) {
      searchBar.openDropdown();
      searchBar.setSelectedIndex(0);
    } else {
      searchBar.hideDropdown();
    }
    
    return results;
  };

  /**
   * Get full definition for a word in lookup mode
   */
  const getDefinition = async (
    word: string, 
    options?: {
      forceRefresh?: boolean;
      onProgress?: (stage: string, progress: number) => void;
    }
  ): Promise<SynthesizedDictionaryEntry> => {
    const apiOptions = {
      forceRefresh: options?.forceRefresh || false,
      providers: Array.from(lookupMode.selectedSources) as any[], // Convert to providers
      languages: Array.from(lookupMode.selectedLanguages) as any[], // Cast to API Language type
      noAI: lookupMode.noAI
    };

    if (options?.onProgress) {
      // Use lookupStream for streaming
      return lookupApi.lookupStream(word, {
        forceRefresh: apiOptions.forceRefresh,
        providers: apiOptions.providers,
        languages: apiOptions.languages,
        noAI: apiOptions.noAI,
        onProgress: (event) => options.onProgress?.(event.stage || 'processing', event.progress || 0)
      });
    }
    
    return lookupApi.lookup(word, apiOptions);
  };

  /**
   * Get thesaurus data (synonyms/antonyms) for a word
   */
  const getThesaurusData = async (word: string): Promise<any> => {
    return aiApi.synthesize.synonyms(word);
  };

  /**
   * Get AI-powered word suggestions based on a query
   */
  const getAISuggestions = async (
    query: string, 
    count = 12,
    options?: {
      onProgress?: (stage: string, progress: number, message?: string, details?: any) => void;
    }
  ): Promise<WordSuggestionResponse> => {
    // Use aiApi.suggestWords for AI-powered word suggestions
    if (options?.onProgress) {
      // Use stream version with onProgress callback
      return aiApi.suggestWordsStream(
        query,
        count,
        options.onProgress // onProgress
      );
    }
    
    return aiApi.suggestWords(query, count);
  };

  // ============================================================================
  // WORDLIST MODE OPERATIONS
  // ============================================================================
  
  /**
   * Execute search for wordlist mode
   * Handles: wordlist filtering, word search within lists
   */
  const executeWordlistSearch = async (queryText: string): Promise<WordListItem[]> => {
    const wordlistId = wordlistMode.selectedWordlist;
    
    if (!wordlistId) {
      console.warn('⚠️ No wordlist selected');
      searchBar.clearResults();
      searchBar.hideDropdown();
      return [];
    }

    let results: WordListItem[] = [];

    // Empty query = show all words, with query = filter
    if (!queryText) {
      results = await wordlistMode.getWordlistWords(wordlistId);
      searchBar.hideDropdown(); // Don't show dropdown for full list
    } else {
      results = await wordlistMode.searchWordlist(wordlistId, queryText);
      
      // Show dropdown only for filtered results
      if (results.length > 0) {
        searchBar.openDropdown();
        searchBar.setSelectedIndex(0);
      } else {
        searchBar.hideDropdown();
      }
    }
    
    return results;
  };

  /**
   * Add a word to the current wordlist
   */
  const addToWordlist = async (word: string): Promise<void> => {
    const wordlistId = wordlistMode.selectedWordlist;
    if (!wordlistId) {
      throw new Error('No wordlist selected');
    }
    
    // TODO: Implement add word to list API
    console.log('Adding word to list:', wordlistId, word);
  };

  /**
   * Remove a word from the current wordlist
   */
  const removeFromWordlist = async (word: string): Promise<void> => {
    const wordlistId = wordlistMode.selectedWordlist;
    if (!wordlistId) {
      throw new Error('No wordlist selected');
    }
    
    // TODO: Implement remove word from list API
    console.log('Removing word from list:', wordlistId, word);
  };

  /**
   * Batch process words in the wordlist
   */
  const processBatchWordlist = async (
    words: string[],
    onProgress?: (completed: number, total: number) => void
  ): Promise<void> => {
    const wordlistId = wordlistMode.selectedWordlist;
    if (!wordlistId) {
      throw new Error('No wordlist selected');
    }

    for (let i = 0; i < words.length; i++) {
      await addToWordlist(words[i]);
      if (onProgress) {
        onProgress(i + 1, words.length);
      }
    }
  };

  // ============================================================================
  // WORD-OF-THE-DAY MODE OPERATIONS
  // ============================================================================
  
  /**
   * Execute search for word-of-the-day mode
   * Handles: fetching daily word, archives
   */
  const executeWordOfTheDaySearch = async (_queryText: string): Promise<any[]> => {
    // TODO: Implement word-of-the-day search
    console.log('📅 Word of the day search not yet implemented');
    searchBar.clearResults();
    searchBar.hideDropdown();
    return [];
  };

  /**
   * Get today's word of the day
   */
  const getTodaysWord = async (): Promise<SynthesizedDictionaryEntry | null> => {
    // TODO: Implement word-of-the-day API
    console.log('📅 Getting today\'s word');
    return null;
  };

  /**
   * Get word-of-the-day archive
   */
  const getWordOfTheDayArchive = async (
    _limit = 30
  ): Promise<SynthesizedDictionaryEntry[]> => {
    // TODO: Implement archive API
    console.log('📅 Getting word archive');
    return [];
  };

  // ============================================================================
  // STAGE MODE OPERATIONS
  // ============================================================================
  
  /**
   * Execute search for stage mode
   * Handles: test/staging functionality
   */
  const executeStageSearch = async (queryText: string): Promise<any[]> => {
    // Stage mode doesn't have traditional search
    console.log('🎭 Stage mode query:', queryText);
    searchBar.clearResults();
    searchBar.hideDropdown();
    return [];
  };

  /**
   * Execute staged operation
   */
  const executeStagedOperation = async (operation: string, params?: any): Promise<any> => {
    console.log('🎭 Executing staged operation:', operation, params);
    // TODO: Implement staging operations
    return null;
  };

  // ============================================================================
  // COMMON OPERATIONS
  // ============================================================================
  
  /**
   * Clear all search state
   */
  const clearSearch = () => {
    query.value = '';
    searchBar.clearResults();
    searchBar.hideDropdown();
    searchError.value = null;
    isSearching.value = false;
  };
  
  /**
   * Cancel any ongoing search operations
   */
  const cancelSearch = () => {
    // Cancel mode-specific searches
    lookupMode.cancelSearch();
    wordlistMode.cancelSearch();
    isSearching.value = false;
  };

  /**
   * Get current search status
   */
  const searchStatus = computed(() => ({
    isSearching: isSearching.value,
    hasError: searchError.value !== null,
    error: searchError.value,
    mode: searchBar.searchMode,
    query: query.value,
    resultsCount: searchBar.currentResults.length
  }));

  // ============================================================================
  // PUBLIC API
  // ============================================================================

  return {
    // State
    isSearching,
    searchError,
    searchStatus,
    
    // Main Operations
    performSearch,
    clearSearch,
    cancelSearch,
    
    // Lookup Mode Operations
    getDefinition,
    getThesaurusData,
    getAISuggestions,
    
    // Wordlist Mode Operations
    addToWordlist,
    removeFromWordlist,
    processBatchWordlist,
    
    // Word-of-the-Day Operations
    getTodaysWord,
    getWordOfTheDayArchive,
    
    // Stage Mode Operations
    executeStagedOperation,
    
    // Cleanup
    cleanup: () => {
      cancelSearch();
      clearSearch();
    },
  };
}