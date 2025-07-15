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
  // Reactive state
  const searchQuery = ref('');
  const isSearching = ref(false);
  const hasSearched = ref(false);
  const searchResults = ref<SearchResult[]>([]);
  const currentEntry = ref<SynthesizedDictionaryEntry>();
  const currentThesaurus = ref<ThesaurusEntry>();
  const mode = ref<'dictionary' | 'thesaurus'>('dictionary');
  const pronunciationMode = ref<'phonetic' | 'ipa'>('phonetic');
  const theme = useStorage('theme', 'light');
  const loadingProgress = ref(0);
  const loadingStage = ref('');

  // Sidebar state
  const sidebarOpen = ref(false); // For mobile modal
  const sidebarCollapsed = ref(true); // For desktop collapse

  // Search history (persisted) - keeping for search bar functionality
  const searchHistory = useStorage<SearchHistory[]>('search-history', []);

  // Lookup history (persisted) - main source for suggestions and tiles
  const lookupHistory = useStorage<LookupHistory[]>('lookup-history', []);

  // Vocabulary suggestions state
  const vocabularySuggestions = ref<VocabularySuggestion[]>([]);
  const isLoadingSuggestions = ref(false);

  // Computed properties
  const searchState = computed<SearchState>(() => ({
    query: searchQuery.value,
    isSearching: isSearching.value,
    hasSearched: hasSearched.value,
    results: searchResults.value,
    currentEntry: currentEntry.value,
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

  const recentLookups = computed(() =>
    lookupHistory.value.slice(0, 10).sort((a, b) => {
      const dateA = new Date(a.timestamp);
      const dateB = new Date(b.timestamp);
      if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
        return 0;
      }
      return dateB.getTime() - dateA.getTime();
    })
  );

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

  async function getDefinition(word: string) {
    isSearching.value = true;
    loadingProgress.value = 0;
    loadingStage.value = 'Looking up word...';

    try {
      // Simulate progress
      loadingProgress.value = 30;
      loadingStage.value = 'Fetching definition...';

      const entry = await dictionaryApi.getDefinition(word);
      currentEntry.value = entry;

      // Add to lookup history
      addToLookupHistory(word, entry);

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

  async function refreshVocabularySuggestions() {
    isLoadingSuggestions.value = true;
    try {
      const recentWords = recentLookupWords.value.slice(0, 10);
      const response =
        await dictionaryApi.getVocabularySuggestions(recentWords);
      vocabularySuggestions.value = response.words.map(word => ({
        word,
        reasoning: '',
        difficulty_level: 0,
        semantic_category: '',
      }));
    } catch (error) {
      console.error('Failed to get vocabulary suggestions:', error);
      vocabularySuggestions.value = [];
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
    currentEntry.value = undefined;
    currentThesaurus.value = undefined;
    mode.value = 'dictionary';
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
    loadingProgress,
    loadingStage,

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
  };
});
