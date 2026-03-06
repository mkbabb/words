import { defineStore } from 'pinia';
import { ref, readonly, computed, shallowRef } from 'vue';
import { searchApi } from '@/api';
import type { ModeHandler } from '@/stores/types/mode-types';
import type { SearchMode, SearchResult, CardVariant } from '@/types';
import type { SemanticStatusResponse } from '@/types/api';
import { CARD_VARIANTS } from '@/types';
import {
    PronunciationModes,
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
 * Unified lookup mode store.
 *
 * Owns search execution (abort controller lifecycle) and state.
 * AI query detection has been moved to useAIQueryDetection.
 * Semantic status polling has been moved to useSemanticStatusPoller.
 */
export const useLookupMode = defineStore(
    'lookupMode',
    () => {
        // ==========================================================================
        // CONFIGURATION STATE
        // ==========================================================================

        const selectedSources = ref<DictionarySource[]>(DEFAULT_SOURCES);
        const selectedLanguages = ref<Language[]>(DEFAULT_LANGUAGES);
        const noAI = ref(true);
        const searchMode = ref<SearchMethod[]>(['smart']);

        // ==========================================================================
        // SEARCH BAR STATE
        // ==========================================================================

        const isAIQuery = ref(false);
        const showSparkle = ref(false);
        const aiSuggestions = ref<string[]>([]);

        // ==========================================================================
        // SEMANTIC STATUS (state only — polling is in useSemanticStatusPoller)
        // ==========================================================================

        const semanticStatus = ref<SemanticStatusResponse | null>(null);

        // ==========================================================================
        // UI STATE
        // ==========================================================================

        const selectedCardVariant = ref<CardVariant>('default');
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
        let searchGeneration = 0;

        // ==========================================================================
        // COMPUTED
        // ==========================================================================

        const state = computed(() => ({
            hasResults: results.value.length > 0,
            resultCount: results.value.length,
            currentMethod: searchMethod.value,
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
                selectedLanguages.value = [
                    language,
                    ...languages.filter((l) => l !== language),
                ];
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

        const setSearchMode = (mode: SearchMethod | SearchMethod[]) => {
            searchMode.value = Array.isArray(mode) ? mode : [mode];
        };

        const toggleSearchMode = () => {
            const modes: Array<SearchMethod> = [
                'smart',
                'exact',
                'fuzzy',
                'semantic',
            ];
            const current = searchMode.value[0] || 'smart';
            const currentIndex = modes.indexOf(current);
            const nextIndex = (currentIndex + 1) % modes.length;
            searchMode.value = [modes[nextIndex]];
        };

        // ==========================================================================
        // SEARCH BAR ACTIONS (pure state setters)
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
        // SEMANTIC STATUS SETTER (for useSemanticStatusPoller composable)
        // ==========================================================================

        const setSemanticStatus = (status: SemanticStatusResponse | null) => {
            semanticStatus.value = status;
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
        // RESULTS OPERATIONS (pure state management — no API calls)
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
            searchMethod.value = 'smart';
            cursorPosition.value = 0;
        };

        const addResults = (newResults: SearchResult[]) => {
            results.value = [...results.value, ...newResults];
        };

        const detectSearchMethod = (
            searchResults: SearchResult[],
            query: string
        ): SearchMethod => {
            // Heuristic: if any result matches exactly, it was exact search
            const exactMatch = searchResults.some(
                (r) => r.word.toLowerCase() === query.toLowerCase()
            );
            if (exactMatch && searchResults.length > 0) return 'exact';
            if (searchResults.length > 0) return 'fuzzy';
            return 'smart';
        };

        const cycleCardVariant = () => {
            const variants: CardVariant[] = [...CARD_VARIANTS];
            const currentIndex = variants.indexOf(selectedCardVariant.value);
            const nextIndex = (currentIndex + 1) % variants.length;
            selectedCardVariant.value = variants[nextIndex];
        };

        const search = async (query: string): Promise<SearchResult[]> => {
            cancelSearch();
            const myGeneration = searchGeneration;
            abortController = new AbortController();

            try {
                const normalized = query.trim().toLowerCase();
                const searchResults = await searchApi.search(normalized, {
                    signal: abortController.signal,
                    mode: Array.isArray(searchMode.value)
                        ? searchMode.value.join(',')
                        : String(searchMode.value || 'smart'),
                });

                // Only update state if this is still the latest request
                if (myGeneration !== searchGeneration) {
                    return searchResults;
                }

                const method = detectSearchMethod(searchResults, normalized);
                setResults(searchResults, method);
                return searchResults;
            } catch (error: any) {
                if (
                    error.name === 'AbortError' ||
                    error.name === 'CanceledError' ||
                    error.code === 'ERR_CANCELED'
                ) {
                    return [];
                }
                if (myGeneration === searchGeneration) {
                    clearResults();
                }
                throw error;
            } finally {
                if (myGeneration === searchGeneration) {
                    abortController = null;
                }
            }
        };

        const cancelSearch = () => {
            // Invalidate any in-flight/soon-to-resolve requests.
            searchGeneration += 1;
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

        const reset = () => {
            // Reset config
            selectedSources.value = DEFAULT_SOURCES;
            selectedLanguages.value = DEFAULT_LANGUAGES;
            noAI.value = true;

            // Reset search bar
            isAIQuery.value = false;
            showSparkle.value = false;
            aiSuggestions.value = [];

            // Reset semantic status
            semanticStatus.value = null;

            // Reset UI
            selectedCardVariant.value = 'default';
            pronunciationMode.value = DEFAULT_PRONUNCIATION_MODE;

            // Reset results
            clearResults();
        };

        // ==========================================================================
        // MODE HANDLER
        // ==========================================================================

        const handler: ModeHandler = {
            onEnter: async (_previousMode: SearchMode) => {
                // Clear AI state when entering
                isAIQuery.value = false;
                showSparkle.value = false;
                clearAISuggestions();
                // NOTE: AI query detection and semantic polling are now
                // started/stopped by the SearchBar component via composables
            },

            onExit: async (_nextMode: SearchMode) => {
                // Clear AI suggestions when leaving
                clearAISuggestions();
                // Abort and invalidate any in-flight lookup request so stale
                // responses cannot repopulate UI after mode switch.
                cancelSearch();
                // NOTE: AI query detection and semantic polling are now
                // started/stopped by the SearchBar component via composables
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
            // Configuration State (persisted — no readonly for hydration)
            selectedSources,
            selectedLanguages,
            noAI,
            searchMode,

            // Search Bar State (not persisted — keep readonly)
            isAIQuery: readonly(isAIQuery),
            showSparkle: readonly(showSparkle),
            aiSuggestions: readonly(aiSuggestions),

            // Semantic Status (not persisted — keep readonly)
            semanticStatus: readonly(semanticStatus),

            // UI State (persisted — no readonly for hydration)
            selectedCardVariant,
            pronunciationMode,

            // Results State (cursorPosition persisted — no readonly; others keep readonly)
            results: readonly(results),
            cursorPosition,
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

            // Semantic Status Setter
            setSemanticStatus,

            // UI Actions
            setCardVariant,
            cycleCardVariant,
            togglePronunciation,
            setPronunciationMode,

            // Search Operations
            search,
            cancelSearch,

            // Results Operations
            setResults,
            clearResults,
            addResults,
            setCursorPosition,
            getResultAt,
            findResultByWord,

            // State Management
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
