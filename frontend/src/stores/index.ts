import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useStorage } from '@vueuse/core';
import type {
    SearchState,
    SearchHistory,
    LookupHistory,
    SynthesizedDictionaryEntry,
    SearchResult,
    ThesaurusEntry,
    VocabularySuggestion,
    WordSuggestionResponse,
} from '@/types';
import { dictionaryApi, wordlistApi } from '@/utils/api';
import { generateId, normalizeWord } from '@/utils';

// Define sort criteria type
interface SortCriterion {
    field: string;
    direction: 'asc' | 'desc';
}

export const useAppStore = defineStore('app', () => {
    // Runtime state (not persisted)
    const isSearching = ref(false);
    const hasSearched = ref(false);
    const searchResults = ref<SearchResult[]>([]);
    const loadingProgress = ref(0);
    const loadingStage = ref('');
    const forceRefreshMode = ref(false);
    const showLoadingModal = ref(false);
    const loadingStageDefinitions = ref<Array<{progress: number, label: string, description: string}>>([]);
    const loadingCategory = ref('');

    // SearchBar UI state (not persisted)
    const showSearchResults = ref(false);
    const searchSelectedIndex = ref(0);
    const isSearchBarFocused = ref(false);
    const showSearchControls = ref(false);
    const isAIQuery = ref(false);
    const showSparkle = ref(false);
    const showErrorAnimation = ref(false);
    const autocompleteText = ref('');
    const aiSuggestions = ref<string[]>([]);
    const isDirectLookup = ref(false);
    const wordSuggestions = computed({
        get: () => sessionState.value.wordSuggestions,
        set: (value) => {
            sessionState.value.wordSuggestions = value || null;
        },
    });
    const isSuggestingWords = ref(false);
    const suggestionsProgress = ref(0);
    const suggestionsStage = ref('');
    const suggestionsStageDefinitions = ref<Array<{progress: number, label: string, description: string}>>([]);
    const suggestionsCategory = ref('');

    // Persisted UI State with validation
    const uiState = useStorage(
        'ui-state',
        {
            mode: 'dictionary' as 'dictionary' | 'thesaurus' | 'suggestions',
            pronunciationMode: 'phonetic' as const,
            sidebarOpen: false,
            sidebarCollapsed: true,
            selectedCardVariant: 'default' as const,
            // Enhanced SearchBar state
            searchMode: 'lookup' as const,
            selectedSources: ['wiktionary'] as string[],
            selectedLanguages: ['en'] as string[],
            showControls: false,
            noAI: true,
            selectedWordlist: null as string | null,
            // Progressive sidebar state
            sidebarActiveCluster: '',
            sidebarActivePartOfSpeech: '',
            // Accordion states for different views
            sidebarAccordionState: {
                lookup: [] as string[],
                wordlist: [] as string[],
                'word-of-the-day': [] as string[],
                stage: [] as string[],
            },
            // Wordlist filters
            wordlistFilters: {
                showBronze: true,
                showSilver: true,
                showGold: true,
                showHotOnly: false,
                showDueOnly: false,
            },
            // Wordlist chunking
            wordlistChunking: {
                byMastery: false,
                byDate: false,
                byLastVisited: false,
                byFrequency: false,
            },
            // Wordlist sorting
            wordlistSortCriteria: [] as SortCriterion[],
        },
        undefined,
        {
            serializer: {
                read: (v: any) => {
                    try {
                        const parsed = JSON.parse(v);
                        // Validate card variant
                        if (
                            !['default', 'gold', 'silver', 'bronze'].includes(
                                parsed.selectedCardVariant
                            )
                        ) {
                            parsed.selectedCardVariant = 'default';
                        }
                        // Validate search mode
                        if (
                            ![
                                'lookup',
                                'wordlist',
                                'word-of-the-day',
                                'stage',
                            ].includes(parsed.searchMode)
                        ) {
                            parsed.searchMode = 'lookup';
                        }
                        // Validate selected sources
                        if (!Array.isArray(parsed.selectedSources)) {
                            parsed.selectedSources = ['wiktionary'];
                        }
                        // Validate selected languages
                        if (!Array.isArray(parsed.selectedLanguages)) {
                            parsed.selectedLanguages = ['en'];
                        }
                        // Validate noAI flag
                        if (typeof parsed.noAI !== 'boolean') {
                            parsed.noAI = true;
                        }
                        // Validate accordion state
                        if (
                            !parsed.sidebarAccordionState ||
                            typeof parsed.sidebarAccordionState !== 'object'
                        ) {
                            parsed.sidebarAccordionState = {
                                lookup: [],
                                wordlist: [],
                                stage: [],
                            };
                        }
                        // Validate wordlist filters
                        if (
                            !parsed.wordlistFilters ||
                            typeof parsed.wordlistFilters !== 'object'
                        ) {
                            parsed.wordlistFilters = {
                                showBronze: true,
                                showSilver: true,
                                showGold: true,
                                showHotOnly: false,
                                showDueOnly: false,
                            };
                        }
                        // Validate wordlist chunking
                        if (
                            !parsed.wordlistChunking ||
                            typeof parsed.wordlistChunking !== 'object'
                        ) {
                            parsed.wordlistChunking = {
                                byMastery: false,
                                byDate: false,
                                byLastVisited: false,
                                byFrequency: false,
                            };
                        }
                        // Validate wordlist sort criteria
                        if (!Array.isArray(parsed.wordlistSortCriteria)) {
                            parsed.wordlistSortCriteria = [];
                        }
                        return parsed;
                    } catch {
                        return {
                            mode: 'dictionary',
                            pronunciationMode: 'phonetic',
                            sidebarOpen: false,
                            sidebarCollapsed: true,
                            selectedCardVariant: 'default',
                            searchMode: 'lookup',
                            selectedSources: ['wiktionary'],
                            selectedLanguages: ['en'],
                            showControls: false,
                            noAI: true,
                            selectedWordlist: null,
                            sidebarActiveCluster: '',
                            sidebarActivePartOfSpeech: '',
                            sidebarAccordionState: {
                                lookup: [],
                                wordlist: [],
                                stage: [],
                            },
                            wordlistFilters: {
                                showBronze: true,
                                showSilver: true,
                                showGold: true,
                                showHotOnly: false,
                                showDueOnly: false,
                            },
                            wordlistChunking: {
                                byMastery: false,
                                byDate: false,
                                byLastVisited: false,
                                byFrequency: false,
                            },
                            wordlistSortCriteria: [] as SortCriterion[],
                        };
                    }
                },
                write: (v: any) => JSON.stringify(v),
            },
        }
    );

    // Persisted Session State - Everything about search
    const sessionState = useStorage('session-state', {
        // Mode-specific search queries
        searchQueries: {
            lookup: '',
            wordlist: '',
            wordOfTheDay: '',
            stage: '',
        },
        searchCursorPosition: 0,
        searchSelectedIndex: 0,
        searchResults: [] as SearchResult[],
        currentWord: null as string | null,
        currentEntry: null as SynthesizedDictionaryEntry | null,
        currentThesaurus: null as ThesaurusEntry | null,
        isAIQuery: false,
        aiQueryText: '',
        wordSuggestions: null as WordSuggestionResponse | null,
    });

    // Create refs that sync with persisted state - mode-specific search queries
    const searchQuery = computed({
        get: () => {
            const mode =
                searchMode.value === 'word-of-the-day'
                    ? 'wordOfTheDay'
                    : searchMode.value;
            return sessionState.value.searchQueries?.[mode] || '';
        },
        set: (value) => {
            const mode =
                searchMode.value === 'word-of-the-day'
                    ? 'wordOfTheDay'
                    : searchMode.value;
            if (sessionState.value.searchQueries) {
                sessionState.value.searchQueries[mode] = value;
            }
        },
    });

    const currentEntry = computed({
        get: () => sessionState.value.currentEntry,
        set: (value) => {
            sessionState.value.currentEntry = value || null;
        },
    });

    const currentThesaurus = computed({
        get: () => sessionState.value.currentThesaurus,
        set: (value) => {
            sessionState.value.currentThesaurus = value || null;
        },
    });

    const mode = computed({
        get: () => uiState.value.mode,
        set: (value) => {
            uiState.value.mode = value;
        },
    });

    const pronunciationMode = computed({
        get: () => uiState.value.pronunciationMode,
        set: (value) => {
            uiState.value.pronunciationMode = value;
        },
    });

    const sidebarOpen = computed({
        get: () => uiState.value.sidebarOpen,
        set: (value) => {
            uiState.value.sidebarOpen = value;
        },
    });

    const sidebarCollapsed = computed({
        get: () => uiState.value.sidebarCollapsed,
        set: (value) => {
            uiState.value.sidebarCollapsed = value;
        },
    });

    const selectedCardVariant = computed({
        get: () => uiState.value.selectedCardVariant,
        set: (value) => {
            uiState.value.selectedCardVariant = value;
        },
    });

    // Enhanced SearchBar computed properties
    const searchMode = computed({
        get: () => uiState.value.searchMode,
        set: (value) => {
            uiState.value.searchMode = value;
        },
    });

    const selectedSources = computed({
        get: () => uiState.value.selectedSources,
        set: (value) => {
            uiState.value.selectedSources = value;
        },
    });

    const selectedLanguages = computed({
        get: () => uiState.value.selectedLanguages,
        set: (value) => {
            uiState.value.selectedLanguages = value;
        },
    });

    const showControls = computed({
        get: () => uiState.value.showControls,
        set: (value) => {
            uiState.value.showControls = value;
        },
    });

    const selectedWordlist = computed({
        get: () => uiState.value.selectedWordlist,
        set: (value) => {
            uiState.value.selectedWordlist = value;
        },
    });

    const noAI = computed({
        get: () => uiState.value.noAI,
        set: (value) => {
            uiState.value.noAI = value;
        },
    });

    const sidebarAccordionState = computed({
        get: () => uiState.value.sidebarAccordionState,
        set: (value) => {
            uiState.value.sidebarAccordionState = value;
        },
    });

    const sidebarActiveCluster = computed({
        get: () => uiState.value.sidebarActiveCluster,
        set: (value) => {
            uiState.value.sidebarActiveCluster = value;
        },
    });

    const sidebarActivePartOfSpeech = computed({
        get: () => uiState.value.sidebarActivePartOfSpeech,
        set: (value) => {
            uiState.value.sidebarActivePartOfSpeech = value;
        },
    });

    const wordlistFilters = computed({
        get: () => uiState.value.wordlistFilters,
        set: (value) => {
            uiState.value.wordlistFilters = value;
        },
    });

    const wordlistChunking = computed({
        get: () => uiState.value.wordlistChunking,
        set: (value) => {
            uiState.value.wordlistChunking = value;
        },
    });

    const wordlistSortCriteria = computed({
        get: () => uiState.value.wordlistSortCriteria,
        set: (value) => {
            uiState.value.wordlistSortCriteria = value;
        },
    });

    // Remove computed dropdown visibility - let component handle it

    const searchCursorPosition = computed({
        get: () => sessionState.value.searchCursorPosition,
        set: (value) => {
            sessionState.value.searchCursorPosition = value;
        },
    });

    const theme = useStorage('theme', 'light');

    // Search history (persisted) - keeping for search bar functionality
    const searchHistory = useStorage<SearchHistory[]>('search-history', []);

    // Lookup history (persisted) - main source for suggestions and tiles
    const lookupHistory = useStorage<LookupHistory[]>('lookup-history', []);

    // AI Query history (persisted) - for Recent AI Suggestions
    const aiQueryHistory = useStorage<
        Array<{ query: string; timestamp: string }>
    >('ai-query-history', []);

    // Persisted suggestions cache
    const suggestionsCache = useStorage('suggestions-cache', {
        suggestions: [] as VocabularySuggestion[],
        lastWord: null as string | null,
        timestamp: null as number | null,
    });

    // Vocabulary suggestions state
    const vocabularySuggestions = computed({
        get: () => suggestionsCache.value.suggestions,
        set: (value) => {
            suggestionsCache.value.suggestions = value;
        },
    });
    const isLoadingSuggestions = ref(false);

    // Computed properties
    const searchState = computed<SearchState>(() => ({
        query: searchQuery.value,
        isSearching: isSearching.value,
        hasSearched: hasSearched.value,
        results: searchResults.value,
        currentEntry: currentEntry.value || undefined,
        mode: mode.value,
    }));

    const recentSearches = computed(() =>
        searchHistory.value.slice(0, 10).sort((a, b) => {
            const dateA = new Date(a.timestamp);
            const dateB = new Date(b.timestamp);
            if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
                return 0;
            }
            return dateB.getTime() - dateA.getTime();
        })
    );

    const recentLookups = computed(() => {
        // Create a map to track the most recent lookup per word
        const wordMap = new Map<string, LookupHistory>();

        // Process all lookups and keep only the most recent per word
        lookupHistory.value.forEach((lookup) => {
            const normalizedWord = lookup.word.toLowerCase();
            const existing = wordMap.get(normalizedWord);

            if (!existing) {
                wordMap.set(normalizedWord, lookup);
            } else {
                // Compare timestamps and keep the more recent one
                const currentTime = new Date(lookup.timestamp).getTime();
                const existingTime = new Date(existing.timestamp).getTime();

                if (
                    !isNaN(currentTime) &&
                    !isNaN(existingTime) &&
                    currentTime > existingTime
                ) {
                    wordMap.set(normalizedWord, lookup);
                }
            }
        });

        // Convert map values to array and sort by timestamp (most recent first)
        return Array.from(wordMap.values())
            .sort((a, b) => {
                const dateA = new Date(a.timestamp);
                const dateB = new Date(b.timestamp);
                if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
                    return 0;
                }
                return dateB.getTime() - dateA.getTime();
            })
            .slice(0, 10); // Limit to 10 most recent unique words
    });

    const recentLookupWords = computed(() =>
        recentLookups.value.map((lookup) => lookup.word)
    );

    // Actions
    async function searchWord(query: string) {
        if (!query.trim()) return;

        const normalizedQuery = normalizeWord(query);

        // Set direct lookup flag to prevent search triggering
        isDirectLookup.value = true;
        searchQuery.value = normalizedQuery;
        hasSearched.value = true;

        // Reset AI mode when doing a direct word lookup
        isAIQuery.value = false;
        showSparkle.value = false;
        sessionState.value.isAIQuery = false;
        sessionState.value.aiQueryText = '';

        // Hide search dropdown when performing word lookup
        searchResults.value = [];
        sessionState.value.searchResults = [];
        showSearchResults.value = false;

        // Direct lookup - no need for intermediate search
        await getDefinition(normalizedQuery);

        // Reset direct lookup flag after a short delay
        setTimeout(() => {
            isDirectLookup.value = false;
        }, 100);
    }

    // Search for word suggestions (used by SearchBar)
    async function search(query: string): Promise<SearchResult[]> {
        if (!query.trim()) return [];

        try {
            let results: SearchResult[] = [];

            // Handle different search modes
            if (searchMode.value === 'wordlist' && selectedWordlist.value) {
                // Search within the selected wordlist using corpus API
                const corpusResults = await wordlistApi.searchWordlist(
                    selectedWordlist.value,
                    query,
                    { max_results: 20, min_score: 0.6 }
                );

                // Transform corpus results to SearchResult format
                results =
                    corpusResults.data.results?.map((result: any) => ({
                        word: result.word,
                        score: result.score,
                        source_method: 'corpus' as const,
                        highlight_snippet: result.context || '',
                    })) || [];
            } else {
                // Default dictionary search
                results = await dictionaryApi.searchWord(query);
            }

            searchResults.value = results;

            // Update persisted search results
            sessionState.value.searchResults = results;

            // Add to history if we have results
            if (results.length > 0) {
                addToHistory(query, results);
            }

            return results;
        } catch (error) {
            console.error('Search error:', error);
            return [];
        }
    }

    async function getDefinition(word: string, forceRefresh?: boolean) {
        // Use forceRefreshMode state or explicit override
        const shouldForceRefresh = forceRefresh ?? forceRefreshMode.value;

        isSearching.value = true;
        loadingProgress.value = 0;
        loadingStage.value = shouldForceRefresh
            ? 'Regenerating word...'
            : 'Looking up word...';

        try {
            let entry;

            // Always use streaming endpoint to get pipeline progress
            entry = await dictionaryApi.getDefinitionStream(
                word,
                shouldForceRefresh,
                selectedSources.value, // Pass selected providers
                selectedLanguages.value, // Pass selected languages
                (stage, progress, message, details) => {
                    // Enhanced debug logging with provider info
                    console.log(
                        `Stage: ${stage}, Progress: ${progress}%, Message: ${message}`
                    );

                    // Simple linear progress update
                    loadingProgress.value = progress;

                    loadingStage.value = stage;

                    // Log details for debugging
                    if (details) {
                        console.log(`Pipeline ${stage} details:`, details);
                    }
                },
                (category, stages) => {
                    // Handle dynamic stage configuration
                    console.log(`Received stage config for category: ${category}`, stages);
                    loadingCategory.value = category;
                    loadingStageDefinitions.value = stages;
                },
                noAI.value // Pass noAI flag
            );

            console.log('Setting currentEntry:', entry);
            console.log('Entry images:', entry.images);
            console.log('First definition:', entry.definitions?.[0]);
            console.log(
                'First definition part_of_speech:',
                entry.definitions?.[0]?.part_of_speech
            );
            console.log('First definition ID:', entry.definitions?.[0]?.id);
            console.log(
                'First definition examples:',
                entry.definitions?.[0]?.examples
            );

            // Log synth entry ID if available
            if (entry.synth_entry_id) {
                console.log('Synthesized Entry ID:', entry.synth_entry_id);
            }

            currentEntry.value = entry;

            // Update current word in session
            sessionState.value.currentWord = word;

            // Add to lookup history
            addToLookupHistory(word, entry);

            // Emit events for engagement tracking
            window.dispatchEvent(new CustomEvent('word-searched'));
            window.dispatchEvent(new CustomEvent('definition-viewed'));

            // Refresh suggestions if this is a new word
            if (word !== suggestionsCache.value.lastWord) {
                refreshVocabularySuggestions();
            }

            // Auto-switch from suggestions mode to dictionary mode after successful lookup
            if (mode.value === 'suggestions') {
                mode.value = 'dictionary';
            }

            // Also get thesaurus data
            if (mode.value === 'thesaurus') {
                await getThesaurusData(word);
            }

            // Reset force refresh mode after successful lookup
            if (shouldForceRefresh && forceRefreshMode.value) {
                forceRefreshMode.value = false;
            }
        } catch (error) {
            console.error('Definition error:', error);
            loadingProgress.value = 0;
            loadingStage.value = '';
        } finally {
            isSearching.value = false;
            // Reset progress after a delay to show completion
            setTimeout(() => {
                loadingProgress.value = 0;
                loadingStage.value = '';
            }, 1000);
        }
    }

    async function getThesaurusData(word: string) {
        try {
            // If we already have the current entry, use its synonyms directly
            if (currentEntry.value && currentEntry.value.word === word) {
                const synonymsList: Array<{ word: string; score: number }> = [];

                // Collect synonyms from all definitions
                currentEntry.value.definitions?.forEach((def, index) => {
                    if (def.synonyms && Array.isArray(def.synonyms)) {
                        def.synonyms.forEach((syn: string, synIndex) => {
                            // Avoid duplicates
                            if (!synonymsList.some((s) => s.word === syn)) {
                                // Generate varying scores based on definition order and synonym position
                                // Primary definitions get higher base scores
                                const baseScore = 0.9 - index * 0.1;
                                // Earlier synonyms in the list are typically more relevant
                                const positionPenalty = synIndex * 0.02;
                                const score = Math.max(
                                    0.5,
                                    Math.min(0.95, baseScore - positionPenalty)
                                );
                                synonymsList.push({ word: syn, score });
                            }
                        });
                    }
                });

                currentThesaurus.value = {
                    word: word,
                    synonyms: synonymsList,
                    confidence: 0.9,
                };
            } else {
                // Fallback to API call if we don't have the entry
                const thesaurus = await dictionaryApi.getSynonyms(word);
                currentThesaurus.value = thesaurus;
            }
        } catch (error) {
            console.error('Thesaurus error:', error);
            currentThesaurus.value = {
                word: word,
                synonyms: [],
                confidence: 0,
            };
        }
    }

    function addToHistory(query: string, results: SearchResult[]) {
        const historyEntry: SearchHistory = {
            id: generateId(),
            query,
            timestamp: new Date(),
            results,
        };

        // Remove existing entry for same query
        const existingIndex = searchHistory.value.findIndex(
            (entry) => entry.query === query
        );
        if (existingIndex >= 0) {
            searchHistory.value.splice(existingIndex, 1);
        }

        // Add new entry at the beginning
        searchHistory.value.unshift(historyEntry);

        // Keep only last 50 searches
        if (searchHistory.value.length > 50) {
            searchHistory.value = searchHistory.value.slice(0, 50);
        }
    }

    function clearHistory() {
        searchHistory.value = [];
    }

    function addToLookupHistory(
        word: string,
        entry: SynthesizedDictionaryEntry
    ) {
        const historyEntry: LookupHistory = {
            id: generateId(),
            word: normalizeWord(word),
            timestamp: new Date(),
            entry,
        };

        // Remove existing entry for same word
        const existingIndex = lookupHistory.value.findIndex(
            (lookup) => lookup.word.toLowerCase() === word.toLowerCase()
        );
        if (existingIndex >= 0) {
            lookupHistory.value.splice(existingIndex, 1);
        }

        // Add new entry at the beginning
        lookupHistory.value.unshift(historyEntry);

        // Keep only last 50 lookups
        if (lookupHistory.value.length > 50) {
            lookupHistory.value = lookupHistory.value.slice(0, 50);
        }

        // Refresh vocabulary suggestions with new history
        refreshVocabularySuggestions();
    }

    function clearLookupHistory() {
        lookupHistory.value = [];
        vocabularySuggestions.value = [];
    }

    async function refreshVocabularySuggestions(forceRefresh = false) {
        const ONE_HOUR = 60 * 60 * 1000;
        const currentWord = sessionState.value.currentWord;
        const cache = suggestionsCache.value;

        // Use cache if:
        // 1. Not forcing refresh
        // 2. Cache exists and has suggestions
        // 3. Cache is less than 1 hour old
        // 4. Current word hasn't changed
        if (
            !forceRefresh &&
            cache.suggestions.length > 0 &&
            cache.timestamp &&
            Date.now() - cache.timestamp < ONE_HOUR &&
            currentWord === cache.lastWord
        ) {
            return; // Use cached suggestions
        }

        isLoadingSuggestions.value = true;
        try {
            const recentWords = recentLookupWords.value.slice(0, 10);
            const response =
                await dictionaryApi.getVocabularySuggestions(recentWords);

            const newSuggestions = response.words.map((word) => ({
                word,
                reasoning: '',
                difficulty_level: 0,
                semantic_category: '',
            }));

            // Update cache
            suggestionsCache.value = {
                suggestions: newSuggestions,
                lastWord: currentWord,
                timestamp: Date.now(),
            };
        } catch (error) {
            console.error('Failed to get vocabulary suggestions:', error);
            // Don't clear cache on error - keep using old suggestions
        } finally {
            isLoadingSuggestions.value = false;
        }
    }

    async function getHistoryBasedSuggestions(): Promise<string[]> {
        try {
            const recentWords = recentLookupWords.value.slice(0, 10);
            const response =
                await dictionaryApi.getVocabularySuggestions(recentWords);
            return response.words;
        } catch (error) {
            console.error('Failed to get history-based suggestions:', error);
            // Fallback to simple word list from history
            return recentLookupWords.value.slice(0, 4);
        }
    }

    function togglePronunciation() {
        pronunciationMode.value =
            pronunciationMode.value === 'phonetic' ? 'ipa' : 'phonetic';
    }

    function toggleMode() {
        // Store the current suggestions state if we're leaving suggestions mode
        const hasSuggestionsData = !!wordSuggestions.value;

        // If in suggestions mode
        if (mode.value === 'suggestions') {
            // Only allow switching if we have a current entry (last looked up word)
            if (currentEntry.value) {
                mode.value = 'dictionary';
                // The current entry already contains the last looked up word
            }
            // If no current entry, do nothing - can't switch modes
            return;
        }

        // If in dictionary/thesaurus and we have suggestions data, allow cycling through all modes
        if (mode.value === 'dictionary') {
            mode.value = 'thesaurus';
        } else if (mode.value === 'thesaurus') {
            // If we have suggestions data, go back to suggestions mode
            if (hasSuggestionsData) {
                mode.value = 'suggestions';
            } else {
                // Otherwise cycle back to dictionary
                mode.value = 'dictionary';
            }
        }

        // If we have a current word and switching to thesaurus, fetch data
        if (currentEntry.value && mode.value === 'thesaurus') {
            getThesaurusData(currentEntry.value.word);
        }
    }

    function toggleTheme() {
        theme.value = theme.value === 'light' ? 'dark' : 'light';
    }

    function toggleSidebar() {
        sidebarOpen.value = !sidebarOpen.value;
    }

    function setSidebarCollapsed(collapsed: boolean) {
        sidebarCollapsed.value = collapsed;
    }

    function reset() {
        searchQuery.value = '';
        isSearching.value = false;
        hasSearched.value = false;
        searchResults.value = [];
        currentEntry.value = null;
        currentThesaurus.value = null;
        mode.value = 'dictionary';
    }

    // Notification system
    const notifications = ref<
        Array<{
            id: string;
            type: 'success' | 'error' | 'info' | 'warning';
            message: string;
            duration?: number;
        }>
    >([]);

    function showNotification(notification: {
        type: 'success' | 'error' | 'info' | 'warning';
        message: string;
        duration?: number;
    }) {
        const id = generateId();
        notifications.value.push({ id, ...notification });

        // Auto-remove after duration (default 5 seconds)
        setTimeout(() => {
            notifications.value = notifications.value.filter(
                (n) => n.id !== id
            );
        }, notification.duration || 5000);
    }

    function removeNotification(id: string) {
        notifications.value = notifications.value.filter((n) => n.id !== id);
    }

    // Track session start time for engagement metrics
    const sessionStartTime = ref(Date.now());

    // Enhanced SearchBar functions
    function toggleSearchMode() {
        // Don't allow mode switching during active search
        if (isSearching.value || isSuggestingWords.value) {
            return;
        }

        // Cycle through modes: lookup -> wordlist -> word-of-the-day -> stage -> lookup
        if (searchMode.value === 'lookup') {
            searchMode.value = 'wordlist';
        } else if (searchMode.value === 'wordlist') {
            searchMode.value = 'word-of-the-day';
        } else if (searchMode.value === 'word-of-the-day') {
            searchMode.value = 'stage';
        } else {
            searchMode.value = 'lookup';
        }

        // Reset suggestion mode when changing search modes
        if (mode.value === 'suggestions' && searchMode.value !== 'lookup') {
            // Only reset if we don't have a current entry to fall back to
            if (!currentEntry.value) {
                reset();
            } else {
                mode.value = 'dictionary';
            }
        }
    }

    function toggleControls() {
        showControls.value = !showControls.value;
    }

    function toggleSource(source: string) {
        const sources = selectedSources.value;
        if (sources.includes(source)) {
            selectedSources.value = sources.filter((s: string) => s !== source);
        } else {
            selectedSources.value = [...sources, source];
        }
    }

    function toggleLanguage(language: string) {
        const languages = selectedLanguages.value;
        if (languages.includes(language)) {
            selectedLanguages.value = languages.filter(
                (l: string) => l !== language
            );
        } else {
            selectedLanguages.value = [...languages, language];
        }
    }

    function setWordlist(wordlist: string | null) {
        selectedWordlist.value = wordlist;
    }

    // Regenerate examples for a specific definition
    async function regenerateExamples(
        definitionIndex: number,
        definitionText?: string
    ) {
        if (!currentEntry.value) return;

        try {
            const response = await dictionaryApi.regenerateExamples(
                currentEntry.value.word,
                definitionIndex,
                definitionText,
                2
            );

            // Update the current entry with new examples
            if (currentEntry.value.definitions[definitionIndex]) {
                const def = currentEntry.value.definitions[definitionIndex];
                // Replace only generated examples, keep literature ones
                const literatureExamples =
                    def.examples?.filter((ex) => ex.type === 'literature') ||
                    [];
                def.examples = [
                    ...(response.examples as any[]),
                    ...literatureExamples,
                ];
            }

            // Also update in lookup history
            const historyIndex = lookupHistory.value.findIndex(
                (h) => h.word === currentEntry.value?.word
            );
            if (historyIndex >= 0) {
                lookupHistory.value[historyIndex].entry = currentEntry.value;
            }

            return response;
        } catch (error) {
            console.error('Failed to regenerate examples:', error);
            throw error;
        }
    }

    // Regenerate all examples for the current word
    async function regenerateAllExamples() {
        if (!currentEntry.value) return;

        try {
            // Regenerate examples for each definition
            const promises = currentEntry.value.definitions.map((def, index) =>
                regenerateExamples(index, def.text)
            );

            await Promise.all(promises);
        } catch (error) {
            console.error('Failed to regenerate all examples:', error);
            throw error;
        }
    }

    // Initialize vocabulary suggestions on store creation
    async function initializeVocabularySuggestions() {
        // Always try to get suggestions, even with empty history
        await refreshVocabularySuggestions();
    }

    // Call initialization when store is created
    initializeVocabularySuggestions();

    // Get AI word suggestions for descriptive queries
    async function getAISuggestions(
        query: string,
        count: number = 12
    ): Promise<WordSuggestionResponse | null> {
        try {
            // Set direct lookup flag for AI suggestions
            isDirectLookup.value = true;

            // Hide search dropdown when getting AI suggestions
            searchResults.value = [];
            sessionState.value.searchResults = [];
            showSearchResults.value = false;

            isSuggestingWords.value = true;
            suggestionsProgress.value = 0;
            suggestionsStage.value = 'START';

            // Use streaming API for real-time progress updates
            const response = await dictionaryApi.getAISuggestionsStream(
                query,
                count,
                (stage, progress, message, details) => {
                    // Update progress and stage in real-time
                    suggestionsStage.value = stage;
                    suggestionsProgress.value = progress;

                    // Log progress for debugging
                    console.log(
                        `AI Suggestions - Stage: ${stage}, Progress: ${progress}%, Message: ${message || ''}`
                    );
                },
                (category, stages) => {
                    // Handle dynamic stage configuration
                    console.log(`Received suggestions stage config for category: ${category}`, stages);
                    suggestionsCategory.value = category;
                    suggestionsStageDefinitions.value = stages;
                }
            );

            wordSuggestions.value = response;

            // Add to AI query history
            const existingIndex = aiQueryHistory.value.findIndex(
                (item) => item.query === query
            );
            if (existingIndex >= 0) {
                // Move existing query to front
                aiQueryHistory.value.splice(existingIndex, 1);
            }
            aiQueryHistory.value.unshift({
                query,
                timestamp: new Date().toISOString(),
            });
            // Keep only last 10 AI queries
            if (aiQueryHistory.value.length > 10) {
                aiQueryHistory.value = aiQueryHistory.value.slice(0, 10);
            }

            // Don't manually set progress - let the streaming handle it

            // Reset direct lookup flag
            setTimeout(() => {
                isDirectLookup.value = false;
            }, 100);

            return response;
        } catch (error) {
            console.error('AI suggestions error:', error);
            wordSuggestions.value = null;
            suggestionsProgress.value = 0;
            suggestionsStage.value = '';
            throw error;
        } finally {
            isSuggestingWords.value = false;
            // Reset progress after a delay to show completion
            setTimeout(() => {
                suggestionsProgress.value = 0;
                suggestionsStage.value = '';
                isDirectLookup.value = false;
            }, 1000);
        }
    }

    // Test function to manually update progress
    function testProgressUpdate() {
        console.log('Testing progress updates...');
        isSearching.value = true;
        let progress = 0;
        const interval = setInterval(() => {
            progress += 10;
            console.log(`Setting loadingProgress to ${progress}`);
            loadingProgress.value = progress;
            loadingStage.value = `Test progress: ${progress}%`;

            if (progress >= 100) {
                clearInterval(interval);
                setTimeout(() => {
                    isSearching.value = false;
                    loadingProgress.value = 0;
                }, 1000);
            }
        }, 500);
    }

    // Expose test function globally for debugging
    if (typeof window !== 'undefined') {
        (window as any).testProgress = testProgressUpdate;
    }

    return {
        // State
        searchQuery,
        isSearching,
        hasSearched,
        searchResults,
        currentEntry,
        currentThesaurus,
        mode,
        pronunciationMode,
        theme,
        searchHistory,
        lookupHistory,
        aiQueryHistory,
        vocabularySuggestions,
        isLoadingSuggestions,
        sidebarOpen,
        sidebarCollapsed,
        selectedCardVariant,
        loadingProgress,
        loadingStage,
        loadingStageDefinitions,
        loadingCategory,
        showLoadingModal,
        searchCursorPosition,
        forceRefreshMode,
        sessionState,
        wordSuggestions,
        isSuggestingWords,
        suggestionsProgress,
        suggestionsStage,
        suggestionsStageDefinitions,
        suggestionsCategory,
        // SearchBar UI state
        showSearchResults,
        isSearchBarFocused,
        showSearchControls,
        isAIQuery,
        showSparkle,
        showErrorAnimation,
        autocompleteText,
        aiSuggestions,
        searchSelectedIndex,
        isDirectLookup,
        // Enhanced SearchBar state
        searchMode,
        selectedSources,
        selectedLanguages,
        showControls,
        selectedWordlist,
        noAI,
        sidebarActiveCluster,
        sidebarActivePartOfSpeech,
        sidebarAccordionState,
        wordlistFilters,
        wordlistChunking,
        wordlistSortCriteria,
        // Notifications
        notifications,
        sessionStartTime,

        // Computed
        searchState,
        recentSearches,
        recentLookups,
        recentLookupWords,

        // Actions
        searchWord,
        search,
        getDefinition,
        getThesaurusData,
        addToHistory,
        clearHistory,
        addToLookupHistory,
        clearLookupHistory,
        refreshVocabularySuggestions,
        initializeVocabularySuggestions,
        getHistoryBasedSuggestions,
        togglePronunciation,
        toggleMode,
        toggleTheme,
        toggleSidebar,
        setSidebarCollapsed,
        reset,
        showNotification,
        removeNotification,
        // Enhanced SearchBar functions
        toggleSearchMode,
        toggleControls,
        toggleSource,
        toggleLanguage,
        setWordlist,
        // Regeneration functions
        regenerateExamples,
        regenerateAllExamples,
        // AI functions
        getAISuggestions,

        // Definition update functions
        async updateDefinition(definitionId: string, updates: any) {
            console.log(
                '[Store] Updating definition:',
                definitionId,
                'with:',
                updates
            );
            try {
                const response = await dictionaryApi.updateDefinition(
                    definitionId,
                    updates
                );
                console.log('[Store] Update response:', response);

                // Update current entry if this definition is part of it
                if (currentEntry.value) {
                    const defIndex = currentEntry.value.definitions.findIndex(
                        (d) => d.id === definitionId
                    );
                    if (defIndex >= 0) {
                        console.log(
                            '[Store] Updating local definition at index:',
                            defIndex
                        );
                        Object.assign(
                            currentEntry.value.definitions[defIndex],
                            updates
                        );
                    } else {
                        console.warn(
                            '[Store] Definition not found in current entry'
                        );
                    }
                }

                showNotification({
                    type: 'success',
                    message: 'Definition updated successfully',
                    duration: 3000,
                });

                return response;
            } catch (error) {
                console.error('Failed to update definition:', error);
                showNotification({
                    type: 'error',
                    message: 'Failed to update definition',
                    duration: 5000,
                });
                throw error;
            }
        },

        async updateExample(exampleId: string, updates: { text: string }) {
            console.log(
                '[Store] Updating example:',
                exampleId,
                'with:',
                updates
            );
            try {
                const response = await dictionaryApi.updateExample(
                    exampleId,
                    updates
                );
                console.log('[Store] Example update response:', response);

                showNotification({
                    type: 'success',
                    message: 'Example updated successfully',
                    duration: 3000,
                });

                return response;
            } catch (error) {
                console.error('[Store] Failed to update example:', error);
                showNotification({
                    type: 'error',
                    message: 'Failed to update example',
                    duration: 3000,
                });
                throw error;
            }
        },

        async regenerateDefinitionComponent(
            definitionId: string,
            component: string
        ) {
            try {
                const response =
                    await dictionaryApi.regenerateDefinitionComponent(
                        definitionId,
                        component
                    );

                // Update current entry with regenerated data
                if (currentEntry.value) {
                    const defIndex = currentEntry.value.definitions.findIndex(
                        (d) => d.id === definitionId
                    );
                    if (defIndex >= 0) {
                        const def = currentEntry.value.definitions[defIndex];
                        // Update the specific component
                        if (component === 'language_register') {
                            def.language_register = response[component];
                        } else if (component in def) {
                            (def as any)[component] = response[component];
                        }
                    }
                }

                showNotification({
                    type: 'success',
                    message: `${component} regenerated successfully`,
                    duration: 3000,
                });

                return response;
            } catch (error) {
                console.error(`Failed to regenerate ${component}:`, error);
                showNotification({
                    type: 'error',
                    message: `Failed to regenerate ${component}`,
                    duration: 5000,
                });
                throw error;
            }
        },

        async fetchDefinition(definitionId: string) {
            try {
                const response =
                    await dictionaryApi.getDefinitionById(definitionId);
                return response;
            } catch (error) {
                console.error('Failed to fetch definition:', error);
                throw error;
            }
        },
    };
});
