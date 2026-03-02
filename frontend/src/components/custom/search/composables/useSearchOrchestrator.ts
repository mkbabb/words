import { Ref, computed, ref } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useLoadingState } from '@/stores/ui/loading';
import { lookupApi, aiApi, wordlistsApi } from '@/api';
import { logger } from '@/utils/logger';
import type {
    SearchResult,
    WordListItem,
    WordSuggestionResponse,
    SynthesizedDictionaryEntry,
} from '@/types';

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
 * - Loading state is wired to the global loading store
 * - Each mode has clearly separated operations
 */
export function useSearchOrchestrator(options: UseSearchOrchestratorOptions) {
    const searchBar = useSearchBarStore();
    const lookupMode = useLookupMode();
    const wordlistMode = useWordlistMode();
    const loading = useLoadingState();
    const { query, onSearchComplete } = options;

    // Reactive error state
    const _searchError = ref<Error | null>(null);

    // Track active stream for cancellation on new lookups
    let activeStreamController: AbortController | null = null;

    // Track active wordlist abort controller
    let wordlistAbortController: AbortController | null = null;

    // ============================================================================
    // SEARCH EXECUTION - MODE ROUTER
    // ============================================================================

    const performSearch = async () => {
        const queryText = query.value?.trim() || '';
        const mode = searchBar.searchMode;

        _searchError.value = null;
        loading.startOperation();

        try {
            let results: any[] = [];

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
        } finally {
            loading.endOperation();
        }
    };

    // ============================================================================
    // LOOKUP MODE OPERATIONS
    // ============================================================================

    const executeLookupSearch = async (
        queryText: string
    ): Promise<SearchResult[]> => {
        if (queryText.length < 2) {
            searchBar.clearResults();
            searchBar.hideDropdown();
            return [];
        }

        searchBar.clearResults();
        const results = await lookupMode.search(queryText);

        if (results.length > 0) {
            searchBar.openDropdown();
            searchBar.setSelectedIndex(-1);
        } else {
            searchBar.hideDropdown();
        }

        return results;
    };

    const getDefinition = async (
        word: string,
        options?: {
            forceRefresh?: boolean;
            onProgress?: (stage: string, progress: number) => void;
        }
    ): Promise<SynthesizedDictionaryEntry> => {
        // Abort any active stream before starting a new one
        if (activeStreamController) {
            activeStreamController.abort();
            activeStreamController = null;
        }

        const apiOptions = {
            forceRefresh: options?.forceRefresh || false,
            providers: Array.from(lookupMode.selectedSources) as any[],
            languages: Array.from(lookupMode.selectedLanguages) as any[],
            noAI: lookupMode.noAI,
        };

        loading.startOperation();
        loading.setShowLoadingModal(true);

        try {
            if (options?.onProgress) {
                activeStreamController = new AbortController();
                return await lookupApi.lookupStream(word, {
                    forceRefresh: apiOptions.forceRefresh,
                    providers: apiOptions.providers,
                    languages: apiOptions.languages,
                    noAI: apiOptions.noAI,
                    abortController: activeStreamController,
                    onProgress: (event) => {
                        const stage = event.stage || 'processing';
                        const progress = event.progress || 0;
                        loading.setLoadingStage(stage);
                        loading.setLoadingProgress(progress);
                        options.onProgress?.(stage, progress);
                    },
                });
            }

            return await lookupApi.lookup(word, apiOptions);
        } finally {
            activeStreamController = null;
            loading.setShowLoadingModal(false);
            loading.endOperation();
        }
    };

    const getThesaurusData = async (word: string): Promise<any> => {
        loading.startOperation();
        try {
            return await aiApi.synthesize.synonyms(word);
        } catch (error) {
            logger.error('Failed to fetch thesaurus data:', error);
            // Return a graceful fallback instead of crashing the UI
            return {
                word,
                synonyms: [],
                confidence: 0,
                error:
                    error instanceof Error
                        ? error.message
                        : 'Failed to load thesaurus data',
            };
        } finally {
            loading.endOperation();
        }
    };

    const getAISuggestions = async (
        query: string,
        count = 12,
        options?: {
            onProgress?: (
                stage: string,
                progress: number,
                message?: string,
                details?: any
            ) => void;
        }
    ): Promise<WordSuggestionResponse> => {
        loading.setSuggestingWords(true);

        try {
            if (options?.onProgress) {
                return await aiApi.suggestWordsStream(
                    query,
                    count,
                    (
                        stage: string,
                        progress: number,
                        message?: string,
                        details?: any
                    ) => {
                        loading.setSuggestionsStage(stage);
                        loading.setSuggestionsProgress(progress);
                        options.onProgress?.(stage, progress, message, details);
                    }
                );
            }

            return await aiApi.suggestWords(query, count);
        } finally {
            loading.stopSuggestions();
        }
    };

    // ============================================================================
    // WORDLIST MODE OPERATIONS
    // ============================================================================

    const cancelWordlistSearch = () => {
        if (wordlistAbortController) {
            wordlistAbortController.abort();
            wordlistAbortController = null;
        }
    };

    const executeWordlistFetch = async (
        wordlistId: string,
        offset = 0,
        limit = 100
    ): Promise<WordListItem[]> => {
        wordlistMode.setCurrentWordlistId(wordlistId);

        // Cancel any existing wordlist search
        cancelWordlistSearch();
        wordlistAbortController = new AbortController();

        try {
            const response = await wordlistsApi.getWordlistWords(wordlistId, {
                offset,
                limit,
            });

            const items = (response.items || []) as WordListItem[];
            const replace = offset === 0;

            // Update pagination in store
            wordlistMode.setPagination({
                offset: offset + items.length,
                limit,
                total: response.total || items.length,
                hasMore: (response.total || 0) > offset + items.length,
            });

            wordlistMode.setResults(items, replace);
            return items;
        } catch (error: any) {
            if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
                return [];
            }

            wordlistMode.clearResults();
            throw error;
        } finally {
            wordlistAbortController = null;
        }
    };

    const executeWordlistSearchApi = async (
        wordlistId: string,
        queryText: string,
        offset = 0,
        limit = 50
    ): Promise<WordListItem[]> => {
        wordlistMode.setCurrentWordlistId(wordlistId);
        wordlistMode.setCurrentQuery(queryText);

        // Cancel any existing wordlist search
        cancelWordlistSearch();
        wordlistAbortController = new AbortController();

        try {
            const response = await wordlistsApi.searchWordlist(wordlistId, {
                query: queryText,
                max_results: limit,
                min_score: wordlistMode.filters.minScore,
                offset,
                limit,
            });

            const items = (response.items || []) as WordListItem[];
            const replace = offset === 0;

            // Update pagination in store
            wordlistMode.setPagination({
                offset: offset + items.length,
                limit,
                total: response.total || items.length,
                hasMore: (response.total || 0) > offset + items.length,
            });

            wordlistMode.setResults(items, replace);
            return items;
        } catch (error: any) {
            if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
                return [];
            }

            wordlistMode.clearResults();
            throw error;
        } finally {
            wordlistAbortController = null;
        }
    };

    const executeWordlistSearch = async (
        queryText: string
    ): Promise<WordListItem[]> => {
        const wordlistId = wordlistMode.selectedWordlist;

        if (!wordlistId) {
            searchBar.clearResults();
            searchBar.hideDropdown();
            return [];
        }

        let results: WordListItem[] = [];

        if (!queryText) {
            results = await executeWordlistFetch(wordlistId);
            searchBar.hideDropdown();
        } else {
            results = await executeWordlistSearchApi(wordlistId, queryText);

            if (results.length > 0) {
                searchBar.openDropdown();
                searchBar.setSelectedIndex(0);
            } else {
                searchBar.hideDropdown();
            }
        }

        return results;
    };

    const loadMoreWordlist = async (): Promise<WordListItem[]> => {
        const { hasMore } = wordlistMode.pagination;
        const wordlistId = wordlistMode.currentWordlistId;
        if (!hasMore || !wordlistId) return [];

        const { offset, limit } = wordlistMode.pagination;
        const currentQuery = wordlistMode.currentQuery;

        if (currentQuery) {
            return await executeWordlistSearchApi(
                wordlistId,
                currentQuery,
                offset,
                limit
            );
        } else {
            return await executeWordlistFetch(wordlistId, offset, limit);
        }
    };

    const addToWordlist = async (_word: string): Promise<void> => {
        const wordlistId = wordlistMode.selectedWordlist;
        if (!wordlistId) {
            throw new Error('No wordlist selected');
        }
        // TODO: implement add word API call
    };

    const removeFromWordlist = async (_word: string): Promise<void> => {
        const wordlistId = wordlistMode.selectedWordlist;
        if (!wordlistId) {
            throw new Error('No wordlist selected');
        }
        // TODO: implement remove word API call
    };

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
        searchBar.clearResults();
        searchBar.hideDropdown();
        _searchError.value = null;
        loading.resetLoading();
    };

    const cancelSearch = () => {
        lookupMode.cancelSearch();
        cancelWordlistSearch();
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
        getDefinition,
        getThesaurusData,
        getAISuggestions,

        // Wordlist Mode Operations
        executeWordlistFetch,
        executeWordlistSearchApi,
        loadMoreWordlist,
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
