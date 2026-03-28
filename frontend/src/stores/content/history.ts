import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { generateId } from '@/utils'
import type {
  SearchHistory,
  LookupHistory,
  SearchResult,
  SynthesizedDictionaryEntry,
} from '@/types'

/**
 * HistoryStore - Search and lookup history management
 * Handles search history, lookup history, and AI query history.
 * Vocabulary suggestions cache lives in useVocabularySuggestions composable.
 */
export const useHistoryStore = defineStore('history', () => {
  // ==========================================================================
  // PERSISTED HISTORY STATE
  // ==========================================================================
  
  // Search history (for search bar functionality)
  const searchHistory = ref<SearchHistory[]>([])
  
  // Lookup history (main source for suggestions and tiles)
  const lookupHistory = ref<LookupHistory[]>([])
  
  // AI Query history (for Recent AI Suggestions)
  const aiQueryHistory = ref<Array<{ query: string; timestamp: string }>>([])

  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  // Recent searches (limited and sorted)
  const recentSearches = computed(() =>
    searchHistory.value.slice(0, 10).sort((a, b) => {
      const dateA = new Date(a.timestamp)
      const dateB = new Date(b.timestamp)
      if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
        return 0
      }
      return dateB.getTime() - dateA.getTime()
    })
  )

  // Recent lookups (unique words, most recent per word)
  const recentLookups = computed(() => {
    // Create a map to track the most recent lookup per word
    const wordMap = new Map<string, LookupHistory>()

    // Process all lookups and keep only the most recent per word
    lookupHistory.value.forEach((lookup) => {
      const normalizedWord = lookup.word.toLowerCase()
      const existing = wordMap.get(normalizedWord)

      if (!existing) {
        wordMap.set(normalizedWord, lookup)
      } else {
        // Compare timestamps and keep the more recent one
        const currentTime = new Date(lookup.timestamp).getTime()
        const existingTime = new Date(existing.timestamp).getTime()

        if (
          !isNaN(currentTime) &&
          !isNaN(existingTime) &&
          currentTime > existingTime
        ) {
          wordMap.set(normalizedWord, lookup)
        }
      }
    })

    // Convert map values to array and sort by timestamp (most recent first)
    return Array.from(wordMap.values())
      .sort((a, b) => {
        const dateA = new Date(a.timestamp)
        const dateB = new Date(b.timestamp)
        if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
          return 0
        }
        return dateB.getTime() - dateA.getTime()
      })
      .slice(0, 10) // Limit to 10 most recent unique words
  })

  // Recent lookup words (just the word strings)
  const recentLookupWords = computed(() =>
    recentLookups.value.map((lookup) => lookup.word)
  )

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Search history management
  const addToHistory = (query: string, results: SearchResult[]) => {
    const historyEntry: SearchHistory = {
      id: generateId(),
      query,
      timestamp: new Date(),
      results,
    }

    // Remove existing entry for same query
    const existingIndex = searchHistory.value.findIndex(
      (entry) => entry.query === query
    )
    if (existingIndex >= 0) {
      searchHistory.value.splice(existingIndex, 1)
    }

    // Add new entry at the beginning
    searchHistory.value.unshift(historyEntry)

    // Keep only last 50 searches
    if (searchHistory.value.length > 50) {
      searchHistory.value = searchHistory.value.slice(0, 50)
    }
  }

  const clearSearchHistory = () => {
    searchHistory.value = []
  }

  // Lookup history management
  const addToLookupHistory = (word: string, entry: SynthesizedDictionaryEntry) => {
    const historyEntry: LookupHistory = {
      id: generateId(),
      word: (word ?? '').toLowerCase().trim(), // Normalize for consistency
      timestamp: new Date(),
      entry,
    }

    // Remove existing entry for same word
    const existingIndex = lookupHistory.value.findIndex(
      (lookup) => lookup.word?.toLowerCase() === word?.toLowerCase()
    )
    if (existingIndex >= 0) {
      lookupHistory.value.splice(existingIndex, 1)
    }

    // Add new entry at the beginning
    lookupHistory.value.unshift(historyEntry)

    // Keep only last 25 lookups (entries are large SynthesizedDictionaryEntry objects)
    if (lookupHistory.value.length > 25) {
      lookupHistory.value = lookupHistory.value.slice(0, 25)
    }
  }

  const clearLookupHistory = () => {
    lookupHistory.value = []
  }

  // AI query history management
  const addToAIQueryHistory = (query: string) => {
    const existingIndex = aiQueryHistory.value.findIndex(
      (item) => item.query === query
    )
    if (existingIndex >= 0) {
      // Move existing query to front
      aiQueryHistory.value.splice(existingIndex, 1)
    }
    
    aiQueryHistory.value.unshift({
      query,
      timestamp: new Date().toISOString(),
    })
    
    // Keep only last 10 AI queries
    if (aiQueryHistory.value.length > 10) {
      aiQueryHistory.value = aiQueryHistory.value.slice(0, 10)
    }
  }

  const clearAIQueryHistory = () => {
    aiQueryHistory.value = []
  }

  // Utility functions
  const getSearchHistoryByQuery = (query: string) => {
    return searchHistory.value.filter(entry => 
      entry.query.toLowerCase().includes(query.toLowerCase())
    )
  }

  const getLookupHistoryByWord = (word: string) => {
    return lookupHistory.value.filter(entry => 
      entry.word.toLowerCase().includes(word.toLowerCase())
    )
  }

  // Stats and analytics
  const getHistoryStats = () => {
    return {
      totalSearches: searchHistory.value.length,
      totalLookups: lookupHistory.value.length,
      uniqueWordsLookedUp: new Set(lookupHistory.value.map(l => l.word.toLowerCase())).size,
      totalAIQueries: aiQueryHistory.value.length,
    }
  }

  // Merge remote history from backend (deduplicates by timestamp)
  const mergeRemoteHistory = (remote: { search_history?: any[]; lookup_history?: any[] }) => {
    if (remote.search_history?.length) {
      const existingTs = new Set(searchHistory.value.map(s => s.timestamp))
      for (const item of remote.search_history) {
        if (item.timestamp && !existingTs.has(item.timestamp)) {
          searchHistory.value.push({
            id: generateId(),
            query: item.query || '',
            timestamp: item.timestamp,
            mode: item.mode || 'dictionary',
            results: [],
          } as SearchHistory)
        }
      }
      // Re-sort by timestamp descending and cap
      searchHistory.value.sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      searchHistory.value = searchHistory.value.slice(0, 100)
    }

    if (remote.lookup_history?.length) {
      const existingTs = new Set(lookupHistory.value.map(l => l.timestamp))
      for (const item of remote.lookup_history) {
        if (item.timestamp && !existingTs.has(item.timestamp)) {
          lookupHistory.value.push({
            id: generateId(),
            word: item.word || '',
            timestamp: item.timestamp,
          } as LookupHistory)
        }
      }
      lookupHistory.value.sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      lookupHistory.value = lookupHistory.value.slice(0, 100)
    }
  }

  // Reset all history
  const resetAllHistory = () => {
    searchHistory.value = []
    lookupHistory.value = []
    aiQueryHistory.value = []
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State (persisted fields exposed as raw refs for hydration)
    searchHistory,
    lookupHistory,
    aiQueryHistory,

    // Computed
    recentSearches,
    recentLookups,
    recentLookupWords,

    // Actions
    addToHistory,
    clearSearchHistory,
    addToLookupHistory,
    clearLookupHistory,
    addToAIQueryHistory,
    clearAIQueryHistory,
    getSearchHistoryByQuery,
    getLookupHistoryByWord,
    getHistoryStats,
    mergeRemoteHistory,
    resetAllHistory
  }
}, {
  persist: {
    key: 'history',
    pick: [
      'searchHistory',
      'lookupHistory',
      'aiQueryHistory',
    ]
  }
})