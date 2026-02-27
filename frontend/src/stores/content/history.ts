import { defineStore } from 'pinia'
import { ref, readonly, computed } from 'vue'
import { generateId } from '@/utils'
import { suggestionsApi } from '@/api'
import { logger } from '@/utils/logger'
import type {
  SearchHistory,
  LookupHistory,
  SearchResult,
  SynthesizedDictionaryEntry,
  VocabularySuggestion
} from '@/types'

/**
 * HistoryStore - Search and lookup history management
 * Handles search history, lookup history, AI query history, and vocabulary suggestions
 * Uses modern Pinia persistence with intelligent caching and throttling
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
  
  // Vocabulary suggestions cache with metadata
  const suggestionsCache = ref({
    suggestions: [] as VocabularySuggestion[],
    lastWord: null as string | null,
    timestamp: null as number | null,
  })

  // ==========================================================================
  // NON-PERSISTED STATE
  // ==========================================================================
  
  const isLoadingSuggestions = ref(false)

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

  // Vocabulary suggestions (cached with timestamp validation)
  const vocabularySuggestions = computed(() => {
    const ONE_HOUR = 60 * 60 * 1000
    const cache = suggestionsCache.value
    
    // Return cached suggestions if they're valid and recent
    if (
      cache.suggestions.length > 0 &&
      cache.timestamp &&
      Date.now() - cache.timestamp < ONE_HOUR
    ) {
      return cache.suggestions
    }
    
    return []
  })

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
      word: word.toLowerCase().trim(), // Normalize for consistency
      timestamp: new Date(),
      entry,
    }

    // Remove existing entry for same word
    const existingIndex = lookupHistory.value.findIndex(
      (lookup) => lookup.word.toLowerCase() === word.toLowerCase()
    )
    if (existingIndex >= 0) {
      lookupHistory.value.splice(existingIndex, 1)
    }

    // Add new entry at the beginning
    lookupHistory.value.unshift(historyEntry)

    // Keep only last 50 lookups
    if (lookupHistory.value.length > 50) {
      lookupHistory.value = lookupHistory.value.slice(0, 50)
    }

    // Refresh vocabulary suggestions with new history, but throttle it
    const FIVE_MINUTES = 5 * 60 * 1000
    const cache = suggestionsCache.value
    const shouldRefresh = !cache.timestamp || Date.now() - cache.timestamp > FIVE_MINUTES
    
    if (shouldRefresh) {
      refreshVocabularySuggestions()
    }
  }

  const clearLookupHistory = () => {
    lookupHistory.value = []
    suggestionsCache.value.suggestions = []
    suggestionsCache.value.lastWord = null
    suggestionsCache.value.timestamp = null
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

  // Vocabulary suggestions management
  const refreshVocabularySuggestions = async (forceRefresh = false) => {
    const ONE_HOUR = 60 * 60 * 1000
    const currentWord = lookupHistory.value[0]?.word // Most recent lookup
    const cache = suggestionsCache.value

    // Prevent concurrent calls
    if (isLoadingSuggestions.value && !forceRefresh) {
      return // Already loading, skip this call
    }

    // Use cache if conditions are met
    if (
      !forceRefresh &&
      cache.suggestions.length > 0 &&
      cache.timestamp &&
      Date.now() - cache.timestamp < ONE_HOUR &&
      currentWord === cache.lastWord
    ) {
      return // Use cached suggestions
    }

    isLoadingSuggestions.value = true
    try {
      const recentWords = recentLookupWords.value.slice(0, 10)

      const response = await suggestionsApi.getVocabulary(recentWords)

      const newSuggestions = response.words.map((word) => ({
        word,
        reasoning: '',
        difficulty_level: 0,
        semantic_category: '',
      }))

      // Update cache
      suggestionsCache.value = {
        suggestions: newSuggestions,
        lastWord: currentWord,
        timestamp: Date.now(),
      }
    } catch (error) {
      logger.error('Failed to get vocabulary suggestions:', error)
      // Don't clear cache on error - keep using old suggestions
    } finally {
      isLoadingSuggestions.value = false
    }
  }

  const getHistoryBasedSuggestions = async (): Promise<string[]> => {
    try {
      const recentWords = recentLookupWords.value.slice(0, 10)
      const response = await suggestionsApi.getVocabulary(recentWords)
      return response.words
    } catch (error) {
      logger.error('Failed to get history-based suggestions:', error)
      // Fallback to simple word list from history
      return recentLookupWords.value.slice(0, 4)
    }
  }

  // Cache management
  const clearSuggestionsCache = () => {
    suggestionsCache.value = {
      suggestions: [],
      lastWord: null,
      timestamp: null,
    }
  }

  const invalidateSuggestionsCache = () => {
    suggestionsCache.value.timestamp = null
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
      suggestionsCount: vocabularySuggestions.value.length,
      cacheLastUpdated: suggestionsCache.value.timestamp
    }
  }

  // Reset all history
  const resetAllHistory = () => {
    searchHistory.value = []
    lookupHistory.value = []
    aiQueryHistory.value = []
    clearSuggestionsCache()
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    searchHistory: readonly(searchHistory),
    lookupHistory: readonly(lookupHistory),
    aiQueryHistory: readonly(aiQueryHistory),
    vocabularySuggestions,
    isLoadingSuggestions: readonly(isLoadingSuggestions),
    
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
    refreshVocabularySuggestions,
    getHistoryBasedSuggestions,
    clearSuggestionsCache,
    invalidateSuggestionsCache,
    getSearchHistoryByQuery,
    getLookupHistoryByWord,
    getHistoryStats,
    resetAllHistory
  }
}, {
  persist: {
    key: 'history',
    pick: [
      'searchHistory',
      'lookupHistory',
      'aiQueryHistory',
      'suggestionsCache'
    ]
  }
})