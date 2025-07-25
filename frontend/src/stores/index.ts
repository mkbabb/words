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
} from '@/types';
import { dictionaryApi } from '@/utils/api';
import { generateId, normalizeWord } from '@/utils';

export const useAppStore = defineStore('app', () => {
  // Runtime state (not persisted)
  const isSearching = ref(false);
  const hasSearched = ref(false);
  const searchResults = ref<SearchResult[]>([]);
  const loadingProgress = ref(0);
  const loadingStage = ref('');
  const forceRefreshMode = ref(false);
  
  // Persisted UI State with validation
  const uiState = useStorage('ui-state', {
    mode: 'dictionary' as const,
    pronunciationMode: 'phonetic' as const,
    sidebarOpen: false,
    sidebarCollapsed: true,
    selectedCardVariant: 'default' as const,
    // Enhanced SearchBar state
    searchMode: 'lookup' as const,
    selectedSources: ['wiktionary', 'oxford', 'dictionary_com'] as string[],
    showControls: false,
    selectedWordlist: null as string | null,
  }, undefined, {
    serializer: {
      read: (v: any) => {
        try {
          const parsed = JSON.parse(v);
          // Validate card variant
          if (!['default', 'gold', 'silver', 'bronze'].includes(parsed.selectedCardVariant)) {
            parsed.selectedCardVariant = 'default';
          }
          // Validate search mode
          if (!['lookup', 'wordlist', 'stage'].includes(parsed.searchMode)) {
            parsed.searchMode = 'lookup';
          }
          // Validate selected sources
          if (!Array.isArray(parsed.selectedSources)) {
            parsed.selectedSources = ['wiktionary', 'oxford', 'dictionary_com'];
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
            selectedSources: ['wiktionary', 'oxford', 'dictionary_com'],
            showControls: false,
            selectedWordlist: null,
          };
        }
      },
      write: (v: any) => JSON.stringify(v),
    }
  });
  
  // Persisted Session State - Everything about search
  const sessionState = useStorage('session-state', {
    searchQuery: '',
    searchCursorPosition: 0,
    searchSelectedIndex: 0,
    searchResults: [] as SearchResult[],
    currentWord: null as string | null,
    currentEntry: null as SynthesizedDictionaryEntry | null,
    currentThesaurus: null as ThesaurusEntry | null,
  });
  
  // Create refs that sync with persisted state
  const searchQuery = computed({
    get: () => sessionState.value.searchQuery,
    set: (value) => { sessionState.value.searchQuery = value; }
  });
  
  const currentEntry = computed({
    get: () => sessionState.value.currentEntry,
    set: (value) => { sessionState.value.currentEntry = value || null; }
  });
  
  const currentThesaurus = computed({
    get: () => sessionState.value.currentThesaurus,
    set: (value) => { sessionState.value.currentThesaurus = value || null; }
  });
  
  const mode = computed({
    get: () => uiState.value.mode,
    set: (value) => { uiState.value.mode = value; }
  });
  
  const pronunciationMode = computed({
    get: () => uiState.value.pronunciationMode,
    set: (value) => { uiState.value.pronunciationMode = value; }
  });
  
  const sidebarOpen = computed({
    get: () => uiState.value.sidebarOpen,
    set: (value) => { uiState.value.sidebarOpen = value; }
  });
  
  const sidebarCollapsed = computed({
    get: () => uiState.value.sidebarCollapsed,
    set: (value) => { uiState.value.sidebarCollapsed = value; }
  });
  
  const selectedCardVariant = computed({
    get: () => uiState.value.selectedCardVariant,
    set: (value) => { uiState.value.selectedCardVariant = value; }
  });
  
  // Enhanced SearchBar computed properties
  const searchMode = computed({
    get: () => uiState.value.searchMode,
    set: (value) => { uiState.value.searchMode = value; }
  });
  
  const selectedSources = computed({
    get: () => uiState.value.selectedSources,
    set: (value) => { uiState.value.selectedSources = value; }
  });
  
  const showControls = computed({
    get: () => uiState.value.showControls,
    set: (value) => { uiState.value.showControls = value; }
  });
  
  const selectedWordlist = computed({
    get: () => uiState.value.selectedWordlist,
    set: (value) => { uiState.value.selectedWordlist = value; }
  });
  
  // Remove computed dropdown visibility - let component handle it
  
  const searchCursorPosition = computed({
    get: () => sessionState.value.searchCursorPosition,
    set: (value) => { sessionState.value.searchCursorPosition = value; }
  });
  
  const searchSelectedIndex = computed({
    get: () => sessionState.value.searchSelectedIndex,
    set: (value) => { sessionState.value.searchSelectedIndex = value; }
  });
  
  const theme = useStorage('theme', 'light');

  // Search history (persisted) - keeping for search bar functionality
  const searchHistory = useStorage<SearchHistory[]>('search-history', []);

  // Lookup history (persisted) - main source for suggestions and tiles
  const lookupHistory = useStorage<LookupHistory[]>('lookup-history', []);

  // Persisted suggestions cache
  const suggestionsCache = useStorage('suggestions-cache', {
    suggestions: [] as VocabularySuggestion[],
    lastWord: null as string | null,
    timestamp: null as number | null,
  });
  
  // Vocabulary suggestions state
  const vocabularySuggestions = computed({
    get: () => suggestionsCache.value.suggestions,
    set: (value) => { suggestionsCache.value.suggestions = value; }
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
    lookupHistory.value.forEach(lookup => {
      const normalizedWord = lookup.word.toLowerCase();
      const existing = wordMap.get(normalizedWord);
      
      if (!existing) {
        wordMap.set(normalizedWord, lookup);
      } else {
        // Compare timestamps and keep the more recent one
        const currentTime = new Date(lookup.timestamp).getTime();
        const existingTime = new Date(existing.timestamp).getTime();
        
        if (!isNaN(currentTime) && !isNaN(existingTime) && currentTime > existingTime) {
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
    recentLookups.value.map(lookup => lookup.word)
  );

  // Actions
  async function searchWord(query: string) {
    if (!query.trim()) return;

    const normalizedQuery = normalizeWord(query);
    searchQuery.value = normalizedQuery;
    hasSearched.value = true;

    // Direct lookup - no need for intermediate search
    await getDefinition(normalizedQuery);
  }

  // Search for word suggestions (used by SearchBar)
  async function search(query: string): Promise<SearchResult[]> {
    if (!query.trim()) return [];

    try {
      const results = await dictionaryApi.searchWord(query);
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

  async function getDefinition(word: string, overrideForceRefresh?: boolean) {
    // Use forceRefreshMode state or explicit override
    const shouldForceRefresh = overrideForceRefresh ?? forceRefreshMode.value;
    
    isSearching.value = true;
    loadingProgress.value = 0;
    loadingStage.value = shouldForceRefresh ? 'Regenerating word...' : 'Looking up word...';

    try {
      let entry;
      
      // Always use streaming endpoint to get pipeline progress
      entry = await dictionaryApi.getDefinitionStream(
        word,
        shouldForceRefresh,
        selectedSources.value, // Pass selected providers
        (stage, progress, message, details) => {
          // Map stage names to user-friendly messages
          const stageMessages: Record<string, string> = {
            'search': 'Searching word database...',
            'provider_fetch': `Fetching from ${selectedSources.value.length} provider${selectedSources.value.length > 1 ? 's' : ''}...`,
            'ai_clustering': 'AI clustering definitions...',
            'ai_synthesis': 'AI synthesizing definitions...',
            'ai_examples': 'Generating examples...',
            'ai_synonyms': 'Enhancing synonyms...',
            'storage_save': 'Saving to database...'
          };
          
          // Convert 0-1 to 0-100 progress
          const progressPercent = Math.round(progress * 100);
          
          // Enhanced debug logging with provider info
          console.log(`Stage: ${stage}, Progress: ${progress} → ${progressPercent}%, Message: ${message}`);
          if (details?.provider) {
            console.log(`Provider: ${details.provider}`);
          }
          
          // IMPORTANT: Ignore sub-stage progress updates that reset progress
          // Only update progress for main pipeline stages
          const subStages = ['provider_start', 'provider_connected', 'provider_downloading', 'provider_parsing', 'provider_complete'];
          
          if (subStages.includes(stage)) {
            console.log(`Ignoring sub-stage ${stage} progress update`);
            // Only update the message, not the progress
            if (details && details.provider) {
              loadingStage.value = `${details.provider}: ${stage.replace('provider_', '')}...`;
            }
            return; // Don't update progress for sub-stages
          }
          
          // Update progress only for main stages
          loadingProgress.value = progressPercent;
          
          // Show provider-specific messages when available
          let stageMessage = stageMessages[stage] || message;
          if (details && details.provider && stage === 'provider_fetch') {
            stageMessage = `Fetching from ${details.provider}...`;
          }
          loadingStage.value = stageMessage;
          
          // Log details for debugging
          if (details) {
            console.log(`Pipeline ${stage} details:`, details);
          }
        }
      );
      
      currentEntry.value = entry;
      
      // Update current word in session
      sessionState.value.currentWord = word;

      // Add to lookup history
      addToLookupHistory(word, entry);
      
      // Refresh suggestions if this is a new word
      if (word !== suggestionsCache.value.lastWord) {
        refreshVocabularySuggestions();
      }

      loadingProgress.value = 70;
      loadingStage.value = 'Finalizing...';

      // Also get thesaurus data
      if (mode.value === 'thesaurus') {
        loadingStage.value = 'Loading synonyms...';
        await getThesaurusData(word);
      }

      loadingProgress.value = 100;
      setTimeout(() => {
        loadingProgress.value = 0;
        loadingStage.value = '';
      }, 300);
      
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
    }
  }

  async function getThesaurusData(word: string) {
    try {
      const thesaurus = await dictionaryApi.getSynonyms(word);
      currentThesaurus.value = thesaurus;
    } catch (error) {
      console.error('Thesaurus error:', error);
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
      entry => entry.query === query
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

  function addToLookupHistory(word: string, entry: SynthesizedDictionaryEntry) {
    const historyEntry: LookupHistory = {
      id: generateId(),
      word: normalizeWord(word),
      timestamp: new Date(),
      entry,
    };

    // Remove existing entry for same word
    const existingIndex = lookupHistory.value.findIndex(
      lookup => lookup.word.toLowerCase() === word.toLowerCase()
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
      
      const newSuggestions = response.words.map(word => ({
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
    mode.value = mode.value === 'dictionary' ? 'thesaurus' : 'dictionary';

    // If we have a current word, fetch appropriate data
    if (currentEntry.value) {
      if (mode.value === 'thesaurus') {
        getThesaurusData(currentEntry.value.word);
      }
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

  // Enhanced SearchBar functions
  function toggleSearchMode() {
    // Cycle through modes: lookup -> wordlist -> stage -> lookup
    if (searchMode.value === 'lookup') {
      searchMode.value = 'wordlist';
    } else if (searchMode.value === 'wordlist') {
      searchMode.value = 'stage';
    } else {
      searchMode.value = 'lookup';
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

  function setWordlist(wordlist: string | null) {
    selectedWordlist.value = wordlist;
  }

  // Regenerate examples for a specific definition
  async function regenerateExamples(definitionIndex: number, definitionText?: string) {
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
        if (!def.examples) {
          def.examples = { generated: [], literature: [] };
        }
        def.examples.generated = response.examples.map(ex => ({
          sentence: ex.sentence,
          regenerable: ex.regenerable,
        }));
      }
      
      // Also update in lookup history
      const historyIndex = lookupHistory.value.findIndex(
        h => h.word === currentEntry.value?.word
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
        regenerateExamples(index, def.definition)
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
    vocabularySuggestions,
    isLoadingSuggestions,
    sidebarOpen,
    sidebarCollapsed,
    selectedCardVariant,
    loadingProgress,
    loadingStage,
    searchCursorPosition,
    forceRefreshMode,
    searchSelectedIndex,
    sessionState,
    // Enhanced SearchBar state
    searchMode,
    selectedSources,
    showControls,
    selectedWordlist,

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
    // Enhanced SearchBar functions
    toggleSearchMode,
    toggleControls,
    toggleSource,
    setWordlist,
    // Regeneration functions
    regenerateExamples,
    regenerateAllExamples,
  };
});
