import { defineStore } from 'pinia'
import { ref, readonly, computed, shallowRef } from 'vue'
import { dictionaryApi, wordlistsApi } from '@/api'
import { normalizeWord } from '@/utils'
import type { SearchResult, SearchMode } from '@/types'

/**
 * SearchResultsStore - Manages search results only
 * Handles search operations and results storage for all search modes
 * Content display is handled by the ContentStore
 */
export const useSearchResultsStore = defineStore('searchResults', () => {
  // ==========================================================================
  // SEARCH STATE
  // ==========================================================================
  
  // Generalized search results keyed by mode
  const searchResults = shallowRef<Record<SearchMode, any[]>>({
    lookup: [],
    wordlist: [],
    'word-of-the-day': [],
    stage: []
  })
  
  // Search cursor position for restoring search state
  const searchCursorPosition = ref(0)
  
  // Abort controllers for cancellable requests
  let searchAbortController: AbortController | null = null
  
  // ==========================================================================
  // COMPUTED
  // ==========================================================================
  
  const searchState = computed(() => ({
    hasLookupResults: searchResults.value.lookup.length > 0,
    hasWordlistResults: searchResults.value.wordlist.length > 0,
    lookupResultCount: searchResults.value.lookup.length,
    wordlistResultCount: searchResults.value.wordlist.length,
  }))
  
  // ==========================================================================
  // SEARCH OPERATIONS
  // ==========================================================================
  
  /**
   * Get search results for a specific mode
   */
  const getSearchResults = (mode: SearchMode) => {
    return searchResults.value[mode] || []
  }
  
  /**
   * Set search results for a specific mode
   */
  const setSearchResults = (mode: SearchMode, results: any[]) => {
    searchResults.value = {
      ...searchResults.value,
      [mode]: [...results]
    }
  }
  
  /**
   * Clear search results for a specific mode or all modes
   */
  const clearSearchResults = (mode?: SearchMode) => {
    if (mode) {
      searchResults.value = {
        ...searchResults.value,
        [mode]: []
      }
    } else {
      // Clear all modes
      searchResults.value = {
        lookup: [],
        wordlist: [],
        'word-of-the-day': [],
        stage: []
      }
    }
  }
  
  /**
   * Search for words (lookup mode)
   */
  const search = async (query: string): Promise<SearchResult[]> => {
    const normalizedQuery = normalizeWord(query)
    
    // Cancel any existing search
    cancelSearch()
    
    // Create new abort controller
    searchAbortController = new AbortController()
    
    try {
      console.log(`[SearchResults] Searching for: ${query}`)
      
      const results = await dictionaryApi.searchWord(normalizedQuery, {
        signal: searchAbortController.signal
      })
      
      // Store results
      setSearchResults('lookup', results)
      
      console.log(`[SearchResults] Found ${results.length} results`)
      return results
      
    } catch (error: any) {
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        console.log('[SearchResults] Search cancelled')
        return []
      }
      
      console.error('[SearchResults] Search error:', error)
      clearSearchResults('lookup')
      throw error
    } finally {
      searchAbortController = null
    }
  }
  
  /**
   * Cancel ongoing search
   */
  const cancelSearch = () => {
    if (searchAbortController) {
      searchAbortController.abort()
      searchAbortController = null
    }
  }
  
  /**
   * Get wordlist words (for empty query in wordlist mode)
   */
  const getWordlistWords = async (wordlistId: string) => {
    try {
      const response = await wordlistsApi.getWordlistWords(wordlistId, {
        offset: 0,
        limit: 100
      })
      
      const results = response.items || []
      setSearchResults('wordlist', results)
      return results
      
    } catch (error) {
      console.error('[SearchResults] Failed to get wordlist words:', error)
      clearSearchResults('wordlist')
      return []
    }
  }
  
  /**
   * Search within wordlist
   */
  const searchWordlist = async (wordlistId: string, query: string) => {
    try {
      const response = await wordlistsApi.searchWordlist(wordlistId, {
        query,
        max_results: 50,
        min_score: 0.4,
        offset: 0,
        limit: 50
      })
      
      const results = response.items || []
      setSearchResults('wordlist', results)
      return results
      
    } catch (error) {
      console.error('[SearchResults] Failed to search wordlist:', error)
      clearSearchResults('wordlist')
      return []
    }
  }
  
  /**
   * Set cursor position for search restoration
   */
  const setCursorPosition = (position: number) => {
    searchCursorPosition.value = position
  }
  
  // ==========================================================================
  // CONTENT OPERATIONS (Moved to ContentStore)
  // ==========================================================================
  
  /**
   * Get definition for a word
   * Note: This updates the ContentStore, not search results
   */
  const getDefinition = async (word: string, options?: any) => {
    // Import content store to avoid circular dependency
    const { useContentStore } = await import('../content/content')
    const contentStore = useContentStore()
    
    const normalizedWord = normalizeWord(word)
    
    try {
      console.log(`[SearchResults] Getting definition for: ${word}`)
      
      contentStore.setStreamingState(true)
      contentStore.setPartialEntry(null)
      
      const entry = await dictionaryApi.getDefinitionStream(
        normalizedWord,
        options?.forceRefresh || false,
        undefined, // providers
        undefined, // languages
        options?.onProgress, // onProgress
        options?.onStageConfig, // onConfig
        (data: any) => { // onPartialResult
          contentStore.setPartialEntry(data)
        }
      )
      
      if (!entry || Object.keys(entry).length === 0) {
        contentStore.setError({
          hasError: true,
          errorType: 'empty',
          errorMessage: `No definitions found for "${word}"`,
          canRetry: true,
          originalWord: word
        })
      } else {
        contentStore.setCurrentEntry(entry)
      }
      
      return entry
      
    } catch (error: any) {
      console.error('[SearchResults] Definition error:', error)
      
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
      let errorType: 'network' | 'not-found' | 'server' | 'ai-failed' | 'empty' | 'unknown' = 'unknown'
      
      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        errorType = 'not-found'
      } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
        errorType = 'network'
      }
      
      contentStore.setError({
        hasError: true,
        errorType,
        errorMessage,
        canRetry: errorType !== 'not-found',
        originalWord: word
      })
      
      throw error
    } finally {
      contentStore.setStreamingState(false)
    }
  }
  
  /**
   * Get thesaurus data
   */
  const getThesaurusData = async (word: string) => {
    const { useContentStore } = await import('../content/content')
    const contentStore = useContentStore()
    
    try {
      // First check if we have synonyms in current entry
      if (contentStore.currentEntry && contentStore.currentEntry.word === word) {
        const synonymsList: Array<{ word: string; score: number }> = []
        
        contentStore.currentEntry.definitions?.forEach((def: any, index: number) => {
          if (def.synonyms && Array.isArray(def.synonyms)) {
            def.synonyms.forEach((syn: string, synIndex: number) => {
              if (!synonymsList.some((s) => s.word === syn)) {
                const baseScore = 0.9 - index * 0.1
                const positionPenalty = synIndex * 0.02
                const score = Math.max(0.5, Math.min(0.95, baseScore - positionPenalty))
                synonymsList.push({ word: syn, score })
              }
            })
          }
        })
        
        contentStore.setCurrentThesaurus({
          word: word,
          synonyms: synonymsList,
          confidence: 0.9,
        })
      } else {
        // Fallback to API
        const thesaurus = await dictionaryApi.getSynonyms(word)
        contentStore.setCurrentThesaurus(thesaurus)
      }
    } catch (error) {
      console.error('[SearchResults] Failed to get thesaurus data:', error)
      throw error
    }
  }
  
  /**
   * Get AI suggestions
   */
  const getAISuggestions = async (query: string, count: number = 12, options?: any) => {
    const { useContentStore } = await import('../content/content')
    const contentStore = useContentStore()
    
    try {
      console.log(`[SearchResults] Getting AI suggestions for: ${query}`)
      
      const suggestions = await dictionaryApi.getAISuggestionsStream(
        query,
        count,
        options?.onProgress
      )
      
      contentStore.setWordSuggestions(suggestions)
      return suggestions
      
    } catch (error) {
      console.error('[SearchResults] Failed to get AI suggestions:', error)
      throw error
    }
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    searchResults: readonly(searchResults),
    searchCursorPosition: readonly(searchCursorPosition),
    
    // Computed
    searchState,
    
    // Search operations
    getSearchResults,
    setSearchResults,
    clearSearchResults,
    search,
    cancelSearch,
    getWordlistWords,
    searchWordlist,
    setCursorPosition,
    
    // Content operations (delegate to ContentStore)
    getDefinition,
    getThesaurusData,
    getAISuggestions,
    
    // Legacy compatibility (deprecated)
    setWordlistSearchResults: (results: any[]) => setSearchResults('wordlist', results),
    clearWordlistSearchResults: () => clearSearchResults('wordlist'),
    get wordlistSearchResults() { return searchResults.value.wordlist },
  }
}, {
  persist: {
    key: 'search-results',
    pick: ['searchCursorPosition']
  }
})