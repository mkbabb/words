import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useStorage } from '@vueuse/core';
import type {
  SearchState,
  SearchHistory,
  SynthesizedDictionaryEntry,
  SearchResult,
  ThesaurusEntry,
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

  // Search history (persisted)
  const searchHistory = useStorage<SearchHistory[]>('search-history', []);

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
    searchHistory.value
      .slice(0, 10)
      .sort((a, b) => {
        const dateA = new Date(a.timestamp);
        const dateB = new Date(b.timestamp);
        if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
          return 0;
        }
        return dateB.getTime() - dateA.getTime();
      })
  );

  // Actions
  async function searchWord(query: string) {
    if (!query.trim()) return;

    const normalizedQuery = normalizeWord(query);
    searchQuery.value = normalizedQuery;
    isSearching.value = true;
    hasSearched.value = true;
    loadingProgress.value = 0;

    try {
      // Stage 1: Searching
      loadingStage.value = 'Searching...';
      loadingProgress.value = 25;
      
      const response = await dictionaryApi.searchWord(normalizedQuery);
      
      if (response.success) {
        searchResults.value = response.data;
        loadingProgress.value = 50;
        
        // If we have results, get the first one's definition
        if (response.data.length > 0) {
          // Stage 2: Getting definition
          loadingStage.value = 'Getting definition...';
          loadingProgress.value = 75;
          await getDefinition(response.data[0].word);
        }
        
        // Stage 3: Complete
        loadingStage.value = 'Complete';
        loadingProgress.value = 100;
        
        // Add to search history
        addToHistory(normalizedQuery, response.data);
      }
    } catch (error) {
      console.error('Search error:', error);
      searchResults.value = [];
    } finally {
      // Small delay to show completion
      setTimeout(() => {
        isSearching.value = false;
        loadingProgress.value = 0;
        loadingStage.value = '';
      }, 300);
    }
  }

  async function getDefinition(word: string) {
    try {
      const response = await dictionaryApi.getDefinition(word);
      
      if (response.success) {
        currentEntry.value = response.data;
        
        // Also get thesaurus data
        if (mode.value === 'thesaurus') {
          await getThesaurusData(word);
        }
      }
    } catch (error) {
      console.error('Definition error:', error);
    }
  }

  async function getThesaurusData(word: string) {
    try {
      const response = await dictionaryApi.getSynonyms(word);
      
      if (response.success) {
        currentThesaurus.value = response.data;
      }
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

  function togglePronunciation() {
    pronunciationMode.value = pronunciationMode.value === 'phonetic' ? 'ipa' : 'phonetic';
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
    sidebarOpen,
    sidebarCollapsed,
    loadingProgress,
    loadingStage,
    
    // Computed
    searchState,
    recentSearches,
    
    // Actions
    searchWord,
    getDefinition,
    getThesaurusData,
    addToHistory,
    clearHistory,
    togglePronunciation,
    toggleMode,
    toggleTheme,
    toggleSidebar,
    setSidebarCollapsed,
    reset,
  };
});