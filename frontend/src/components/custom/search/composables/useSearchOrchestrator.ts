import { Ref, computed, ref } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useLoadingState } from '@/stores/ui/loading';
import { logger } from '@/utils/logger';
import type { SynthesizedDictionaryEntry } from '@/types';

import { useLookupSearch } from './useLookupSearch';
import { useWordlistSearch } from './useWordlistSearch';

export interface UseSearchOrchestratorOptions {
    query: Ref<string>;
    onSearchComplete?: (results: any[]) => void;
}

/**
 * Central orchestration composable for all search operations
 *
 * ARCHITECTURE:
 * - This composable routes to mode-specific composables
 * - Stores handle ONLY state management, never API calls
 * - Loading state is wired to the global loading store
 * - Each mode has clearly separated operations in its own composable
 */
export function useSearchOrchestrator(options: UseSearchOrchestratorOptions) {
    const searchBar = useSearchBarStore();
    const lookupMode = useLookupMode();
    const loading = useLoadingState();
    const { query, onSearchComplete } = options;

    // Reactive error state
    const _searchError = ref<Error | null>(null);

    // Mode-specific composables
    const lookup = useLookupSearch({ query });
    const wordlist = useWordlistSearch();

    // ============================================================================
    // SEARCH EXECUTION - MODE ROUTER
    // ============================================================================

    const performSearch = async () => {
        const queryText = query.value?.trim() || '';
        const mode = searchBar.searchMode;

        _searchError.value = null;

        try {
            let results: any[] = [];

            switch (mode) {
                case 'lookup':
                    results = await lookup.executeLookupSearch(queryText);
                    break;
                case 'wordlist':
                    // WordListView owns wordlist search (debounce, guards, error handling).
                    // No-op here to prevent double-watcher race conditions.
                    break;
                case 'word-of-the-day':
                    results = await executeWordOfTheDaySearch(queryText);
                    break;
                case 'stage':
                    results = await executeStageSearch(queryText);
                    break;
                default:
                    logger.warn(`Unhandled search mode: ${mode}`);
                    results = [];
            }

            if (onSearchComplete) {
                onSearchComplete(results);
            }

            return results;
        } catch (error) {
            logger.error('Search error:', error);
            _searchError.value = error as Error;
            searchBar.clearResults();
            searchBar.hideDropdown();
            return [];
        }
    };

    // ============================================================================
    // WORD-OF-THE-DAY MODE OPERATIONS
    // ============================================================================

    const executeWordOfTheDaySearch = async (
        _queryText: string
    ): Promise<any[]> => {
        searchBar.clearResults();
        searchBar.hideDropdown();
        return [];
    };

    const getTodaysWord =
        async (): Promise<SynthesizedDictionaryEntry | null> => {
            return null;
        };

    const getWordOfTheDayArchive = async (
        _limit = 30
    ): Promise<SynthesizedDictionaryEntry[]> => {
        return [];
    };

    // ============================================================================
    // STAGE MODE OPERATIONS
    // ============================================================================

    const executeStageSearch = async (_queryText: string): Promise<any[]> => {
        searchBar.clearResults();
        searchBar.hideDropdown();
        return [];
    };

    const executeStagedOperation = async (
        _operation: string,
        _params?: any
    ): Promise<any> => {
        // TODO: implement staged operation execution
        return null;
    };

    // ============================================================================
    // COMMON OPERATIONS
    // ============================================================================

    const clearSearch = () => {
        searchBar.setQuery('');
        // Don't nuke wordlist cards — WordListView re-fetches on empty query.
        if (searchBar.searchMode !== 'wordlist') {
            searchBar.clearResults();
        }
        searchBar.hideDropdown();
        _searchError.value = null;
        loading.resetLoading();
    };

    const cancelSearch = () => {
        lookupMode.cancelSearch();
        lookup.cancelLookupStream();
        wordlist.cancelWordlistSearch();
        loading.resetLoading();
    };

    const searchStatus = computed(() => ({
        isSearching: loading.isSearching.value,
        hasError: _searchError.value !== null,
        error: _searchError.value,
        mode: searchBar.searchMode,
        query: query.value,
        resultsCount: searchBar.currentResults.length,
    }));

    // ============================================================================
    // PUBLIC API
    // ============================================================================

    return {
        // State (from global loading store)
        isSearching: loading.isSearching,
        searchError: _searchError,
        searchStatus,

        // Main Operations
        performSearch,
        clearSearch,
        cancelSearch,

        // Lookup Mode Operations
        getDefinition: lookup.getDefinition,
        getThesaurusData: lookup.getThesaurusData,
        getAISuggestions: lookup.getAISuggestions,

        // Wordlist Mode Operations
        executeWordlistFetch: wordlist.executeWordlistFetch,
        executeWordlistSearchApi: wordlist.executeWordlistSearchApi,
        loadMoreWordlist: wordlist.loadMoreWordlist,
        addToWordlist: wordlist.addToWordlist,
        removeFromWordlist: wordlist.removeFromWordlist,
        processBatchWordlist: wordlist.processBatchWordlist,

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
