import { Ref } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useHistoryStore } from '@/stores/content/history';
import { useContentStore } from '@/stores/content/content';
import { useLoadingState } from '@/stores/ui/loading';
import { lookupApi, searchApi, aiApi } from '@/api';
import { logger } from '@/utils/logger';
import type {
    SearchResult,
    WordSuggestionResponse,
    SynthesizedDictionaryEntry,
} from '@/types';

export interface UseLookupSearchOptions {
    query: Ref<string>;
}

/**
 * Lookup mode search operations.
 *
 * Handles definition lookups, thesaurus data, autocomplete search,
 * and AI vocabulary suggestions.
 */
export function useLookupSearch(options: UseLookupSearchOptions) {
    const searchBar = useSearchBarStore();
    const lookupMode = useLookupMode();
    const history = useHistoryStore();
    const contentStore = useContentStore();
    const loading = useLoadingState();
    const { query } = options;

    // Track active stream for cancellation on new lookups
    let activeStreamController: AbortController | null = null;

    const executeLookupSearch = async (
        queryText: string
    ): Promise<SearchResult[]> => {
        if (queryText.length < 2) {
            searchBar.clearResults();
            searchBar.hideDropdown();
            return [];
        }

        // Prepare search state (cancel previous, get abort controller)
        const { controller, generation } = lookupMode.prepareSearch();

        try {
            const normalized = queryText.trim().toLowerCase();
            const searchResults = await searchApi.search(normalized, {
                signal: controller.signal,
                mode: Array.isArray(lookupMode.searchMode)
                    ? lookupMode.searchMode.join(',')
                    : String(lookupMode.searchMode || 'smart'),
            });

            // Stale generation -- a newer search was started
            if (!lookupMode.isCurrentGeneration(generation)) {
                return searchResults;
            }

            // Don't update UI if query changed while we were waiting
            const currentQuery = query.value?.trim() || '';
            if (currentQuery !== queryText) {
                return searchResults;
            }

            // Guard against mode switches while request was in flight.
            if (searchBar.searchMode !== 'lookup') {
                return searchResults;
            }

            const method = lookupMode.detectSearchMethod(
                searchResults,
                normalized
            );
            lookupMode.setResults(searchResults, method);

            if (searchBar.isDirectLookup || !searchBar.isFocused) {
                searchBar.clearResults();
                searchBar.hideDropdown();
                return searchResults;
            }

            if (searchResults.length > 0) {
                searchBar.openDropdown();
                searchBar.setSelectedIndex(0);
                history.addToHistory(queryText, searchResults);
            } else {
                searchBar.clearResults();
                searchBar.hideDropdown();
            }

            return searchResults;
        } catch (error: any) {
            if (
                error.name === 'AbortError' ||
                error.name === 'CanceledError' ||
                error.code === 'ERR_CANCELED'
            ) {
                return [];
            }
            if (lookupMode.isCurrentGeneration(generation)) {
                lookupMode.clearResults();
            }
            throw error;
        } finally {
            lookupMode.finalizeSearch(generation);
        }
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

        // Delay showing the modal — cached lookups return in <200ms and don't need it.
        // Only show if the lookup takes longer than 400ms (provider fetch / synthesis).
        const modalTimer = setTimeout(() => loading.setShowLoadingModal(true), 400);

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
            clearTimeout(modalTimer);
            activeStreamController = null;
            loading.setShowLoadingModal(false);
            loading.endOperation();
        }
    };

    const getThesaurusData = async (word: string): Promise<any> => {
        // In no_ai mode, extract synonyms from provider definitions
        if (lookupMode.noAI) {
            const entry = contentStore.currentEntry;
            if (entry?.definitions) {
                const synonyms = (entry.definitions as any[])
                    .flatMap((d: any) => d.synonyms || [])
                    .filter((s: string, i: number, arr: string[]) => arr.indexOf(s) === i)
                    .map((word: string) => ({ word, score: 0.8 }));
                return { word, synonyms, confidence: synonyms.length > 0 ? 0.7 : 0 };
            }
            return { word, synonyms: [], confidence: 0 };
        }

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

    /**
     * Abort the active lookup stream (if any).
     * Called by the orchestrator's cancelSearch.
     */
    const cancelLookupStream = () => {
        if (activeStreamController) {
            activeStreamController.abort();
            activeStreamController = null;
        }
    };

    return {
        executeLookupSearch,
        getDefinition,
        getThesaurusData,
        getAISuggestions,
        cancelLookupStream,
    };
}
