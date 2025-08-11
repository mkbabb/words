import { defineStore } from 'pinia';
import { ref, readonly, computed, shallowRef, watch } from 'vue';
import { lookupApi, searchApi } from '@/api';
import { normalizeWord } from '@/utils';
import { CARD_VARIANTS } from '@/types';
import { shouldTriggerAIMode } from '@/components/custom/search/utils/ai-query';
import { useSearchBarStore } from '../search-bar';
import type { ModeHandler } from '@/stores/types/mode-types';
import type { SearchMode, SearchResult, CardVariant } from '@/types';
import {
    PronunciationModes,
    DEFAULT_CARD_VARIANT,
    DEFAULT_PRONUNCIATION_MODE,
    DEFAULT_SOURCES,
    DEFAULT_LANGUAGES,
    type PronunciationMode,
    type DictionarySource,
    type Language,
} from '@/stores/types/constants';

// Search mode type:
export type SearchMethod = 'smart' | 'exact' | 'fuzzy' | 'semantic';

/**
 * Unified lookup mode store
 * Combines configuration, search bar state, UI preferences, and search results
 */
export const useLookupMode = defineStore(
    'lookupMode',
    () => {
        // Get search bar store for query watching
        const getSearchBarStore = () => useSearchBarStore();
        // ==========================================================================
        // CONFIGURATION STATE
        // ==========================================================================

        const selectedSources = ref<DictionarySource[]>(DEFAULT_SOURCES);
        const selectedLanguages = ref<Language[]>(DEFAULT_LANGUAGES);
        const noAI = ref(true);
        const searchMode = ref<SearchMethod>('smart');

        // ==========================================================================
        // SEARCH BAR STATE
        // ==========================================================================

        const isAIQuery = ref(false);
        const showSparkle = ref(false);
        const aiSuggestions = ref<string[]>([]);

        // Watch for query changes to detect AI mode
        watch(
            () => {
                const store = getSearchBarStore();
                return store?.searchQuery || '';
            },
            (newQuery) => {
                if (newQuery && newQuery.length > 0) {
                    const shouldBeAI = shouldTriggerAIMode(newQuery);
                    if (shouldBeAI !== isAIQuery.value) {
                        setAIQuery(shouldBeAI);
                        if (shouldBeAI) {
                            setShowSparkle(true);
                        }
                    }
                } else {
                    // Reset AI mode for empty queries
                    if (isAIQuery.value) {
                        setAIQuery(false);
                        setShowSparkle(false);
                    }
                }
            }
        );

        // ==========================================================================
        // UI STATE
        // ==========================================================================

        const selectedCardVariant = ref<CardVariant>(DEFAULT_CARD_VARIANT);
        const pronunciationMode = ref<PronunciationMode>(
            DEFAULT_PRONUNCIATION_MODE
        );

        // ==========================================================================
        // RESULTS STATE
        // ==========================================================================

        const results = shallowRef<SearchResult[]>([]);
        const cursorPosition = ref(0);
        const searchMethod = ref<SearchMethod>('smart');
        let abortController: AbortController | null = null;

        // ==========================================================================
        // COMPUTED
        // ==========================================================================

        const state = computed(() => ({
            hasResults: results.value.length > 0,
            resultCount: results.value.length,
            currentMethod: searchMethod.value,
            isSearchActive: abortController !== null,
            isEmpty: results.value.length === 0,
        }));

        // ==========================================================================
        // CONFIGURATION ACTIONS
        // ==========================================================================

        const toggleSource = (source: DictionarySource) => {
            const sources = selectedSources.value;
            if (sources.includes(source)) {
                selectedSources.value = sources.filter((s) => s !== source);
            } else {
                selectedSources.value = [...sources, source];
            }
        };

        const setSources = (sources: DictionarySource[]) => {
            selectedSources.value = [...sources];
        };

        const toggleLanguage = (language: Language) => {
            const languages = selectedLanguages.value;
            if (languages.includes(language)) {
                selectedLanguages.value = languages.filter(
                    (l) => l !== language
                );
            } else {
                selectedLanguages.value = [...languages, language];
            }
        };

        const setLanguages = (languages: Language[]) => {
            selectedLanguages.value = [...languages];
        };

        const toggleAI = () => {
            noAI.value = !noAI.value;
        };

        const setAI = (enabled: boolean) => {
            noAI.value = !enabled;
        };

        const setSearchMode = (mode: SearchMethod) => {
            searchMode.value = mode;
        };

        const toggleSearchMode = () => {
            const modes: Array<SearchMethod> = [
                'smart',
                'exact',
                'fuzzy',
                'semantic',
            ];
            const currentIndex = modes.indexOf(searchMode.value);
            const nextIndex = (currentIndex + 1) % modes.length;
            searchMode.value = modes[nextIndex];
        };

        // ==========================================================================
        // SEARCH BAR ACTIONS
        // ==========================================================================

        const setAIQuery = (isAI: boolean) => {
            isAIQuery.value = isAI;

            if (isAI) {
                showSparkle.value = true;
                // Auto-hide sparkle after animation
                setTimeout(() => {
                    showSparkle.value = false;
                }, 2000);
            }
        };

        const setShowSparkle = (show: boolean) => {
            showSparkle.value = show;
        };

        const setAISuggestions = (suggestions: string[]) => {
            aiSuggestions.value = [...suggestions];
        };

        const addAISuggestion = (suggestion: string) => {
            if (!aiSuggestions.value.includes(suggestion)) {
                aiSuggestions.value = [...aiSuggestions.value, suggestion];
            }
        };

        const clearAISuggestions = () => {
            aiSuggestions.value = [];
        };

        // ==========================================================================
        // UI ACTIONS
        // ==========================================================================

        const setCardVariant = (variant: CardVariant) => {
            selectedCardVariant.value = variant;
        };

        const togglePronunciation = () => {
            pronunciationMode.value =
                pronunciationMode.value === PronunciationModes.PHONETIC
                    ? PronunciationModes.IPA
                    : PronunciationModes.PHONETIC;
        };

        const setPronunciationMode = (mode: PronunciationMode) => {
            pronunciationMode.value = mode;
        };

        // ==========================================================================
        // RESULTS OPERATIONS
        // ==========================================================================

        const setResults = (
            newResults: SearchResult[],
            method?: typeof searchMethod.value
        ) => {
            results.value = [...newResults];
            if (method) {
                searchMethod.value = method;
            }
        };

        const clearResults = () => {
            results.value = [];
            searchMethod.value = null;
            cursorPosition.value = 0;
        };

        const addResults = (newResults: SearchResult[]) => {
            results.value = [...results.value, ...newResults];
        };

        const search = async (query: string): Promise<SearchResult[]> => {
            // Cancel any existing search
            cancelSearch();

            // Create new abort controller
            abortController = new AbortController();

            try {
                console.log(`[LookupMode] Searching for: ${query}`);

                // Always perform dictionary search - AI mode is user-initiated only
                const searchResults = await searchApi.search(normalizedQuery, {
                    signal: abortController.signal,
                    mode: searchMode.value,
                });

                // Store results with method detection
                const method = detectSearchMethod(
                    searchResults,
                    normalizedQuery
                );
                setResults(searchResults, method);

                console.log(
                    `[LookupMode] Found ${searchResults.length} results using ${method} method`
                );
                return searchResults;
            } catch (error: any) {
                if (
                    error.name === 'AbortError' ||
                    error.code === 'ERR_CANCELED'
                ) {
                    console.log('[LookupMode] Search cancelled');
                    return [];
                }

                console.error('[LookupMode] Search error:', error);
                clearResults();
                throw error;
            } finally {
                abortController = null;
            }
        };

        const cancelSearch = () => {
            if (abortController) {
                abortController.abort();
                abortController = null;
            }
        };

        const setCursorPosition = (position: number) => {
            cursorPosition.value = position;
        };

        const getResultAt = (index: number): SearchResult | null => {
            return results.value[index] || null;
        };

        const findResultByWord = (word: string): SearchResult | null => {
            return (
                results.value.find(
                    (result) => result.word.toLowerCase() === word.toLowerCase()
                ) || null
            );
        };

        // ==========================================================================
        // STATE MANAGEMENT
        // ==========================================================================

        const getConfig = () => ({
            selectedSources: selectedSources.value,
            selectedLanguages: selectedLanguages.value,
            noAI: noAI.value,
            searchMode: searchMode.value,
        });

        const setConfig = (config: any) => {
            if (config.selectedSources) setSources(config.selectedSources);
            if (config.selectedLanguages)
                setLanguages(config.selectedLanguages);
            if (config.noAI !== undefined) noAI.value = config.noAI;
            if (config.searchMode !== undefined)
                searchMode.value = config.searchMode;
        };

        const getSearchBarState = () => ({
            isAIQuery: isAIQuery.value,
            showSparkle: showSparkle.value,
            aiSuggestions: [...aiSuggestions.value],
        });

        const setSearchBarState = (state: any) => {
            if (state.isAIQuery !== undefined) setAIQuery(state.isAIQuery);
            if (state.showSparkle !== undefined)
                setShowSparkle(state.showSparkle);
            if (state.aiSuggestions) setAISuggestions(state.aiSuggestions);
        };

        const getUIState = () => ({
            selectedCardVariant: selectedCardVariant.value,
            pronunciationMode: pronunciationMode.value,
        });

        const setUIState = (state: any) => {
            if (state.selectedCardVariant)
                setCardVariant(state.selectedCardVariant);
            if (state.pronunciationMode)
                setPronunciationMode(state.pronunciationMode);
        };

        const reset = () => {
            // Reset config
            selectedSources.value = DEFAULT_SOURCES;
            selectedLanguages.value = DEFAULT_LANGUAGES;
            noAI.value = true;

            // Reset search bar
            isAIQuery.value = false;
            showSparkle.value = false;
            aiSuggestions.value = [];

            // Reset UI
            selectedCardVariant.value = DEFAULT_CARD_VARIANT;
            pronunciationMode.value = DEFAULT_PRONUNCIATION_MODE;

            // Reset results
            clearResults();
        };

        // ==========================================================================
        // MODE HANDLER
        // ==========================================================================

        const handler: ModeHandler = {
            onEnter: async (previousMode: SearchMode) => {
                console.log('🔍 Entering lookup mode from:', previousMode);
                // Clear AI state when entering
                isAIQuery.value = false;
                showSparkle.value = false;
                clearAISuggestions();
            },

            onExit: async (nextMode: SearchMode) => {
                console.log('👋 Exiting lookup mode to:', nextMode);
                // Clear AI suggestions when leaving
                clearAISuggestions();
            },

            validateConfig: (config: any) => {
                return (
                    config.selectedSources?.length > 0 &&
                    config.selectedLanguages?.length > 0
                );
            },

            getDefaultConfig: () => ({
                selectedSources: DEFAULT_SOURCES,
                selectedLanguages: DEFAULT_LANGUAGES,
                noAI: true,
            }),
        };

        // ==========================================================================
        // RETURN API
        // ==========================================================================

        return {
            // Configuration State
            selectedSources: readonly(selectedSources),
            selectedLanguages: readonly(selectedLanguages),
            noAI: readonly(noAI),
            searchMode: readonly(searchMode),

            // Search Bar State
            isAIQuery: readonly(isAIQuery),
            showSparkle: readonly(showSparkle),
            aiSuggestions: readonly(aiSuggestions),

            // UI State
            selectedCardVariant: readonly(selectedCardVariant),
            pronunciationMode: readonly(pronunciationMode),

            // Results State
            results: readonly(results),
            cursorPosition: readonly(cursorPosition),
            searchMethod: readonly(searchMethod),

            // Computed
            state,

            // Configuration Actions
            toggleSource,
            setSources,
            toggleLanguage,
            setLanguages,
            toggleAI,
            setAI,
            setSearchMode,
            toggleSearchMode,

            // Search Bar Actions
            setAIQuery,
            setShowSparkle,
            setAISuggestions,
            addAISuggestion,
            clearAISuggestions,

            // UI Actions
            setCardVariant,
            cycleCardVariant,
            togglePronunciation,
            setPronunciationMode,

            // Results Operations
            setResults,
            clearResults,
            addResults,
            search,
            cancelSearch,
            setCursorPosition,
            getResultAt,
            findResultByWord,

            // State Management
            getConfig,
            setConfig,
            getSearchBarState,
            setSearchBarState,
            getUIState,
            setUIState,
            reset,

            // Utilities
            detectSearchMethod,

            // Mode Handler
            handler,
        };
    },
    {
        persist: {
            key: 'lookup-mode',
            pick: [
                'selectedSources',
                'selectedLanguages',
                'noAI',
                'searchMode',
                'selectedCardVariant',
                'pronunciationMode',
                'cursorPosition',
            ],
        },
    }
);
