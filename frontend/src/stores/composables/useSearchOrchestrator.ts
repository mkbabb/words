import { nextTick } from 'vue'
import { useSearchBarStore } from '../search/search-bar'
import { useSearchConfigStore } from '../search/search-config'
import { useSearchResultsStore } from '../search/search-results'
import { useLoadingStore } from '../ui/loading'
import { useHistoryStore } from '../content/history'
import { useNotificationStore } from '../utils/notifications'
import { useUIStore } from '../ui/ui-state'
import { normalizeWord } from '@/utils'

/**
 * Search Orchestrator Composable
 * Coordinates complex search operations across multiple stores
 * Provides high-level actions that replace the monolithic store functions
 */
export function useSearchOrchestrator() {
  // Get all the stores
  const searchBar = useSearchBarStore()
  const searchConfig = useSearchConfigStore()
  const searchResults = useSearchResultsStore()
  const loading = useLoadingStore()
  const history = useHistoryStore()
  const notifications = useNotificationStore()
  const ui = useUIStore()

  // ==========================================================================
  // COMPLEX SEARCH OPERATIONS
  // ==========================================================================

  const searchWord = async (query: string) => {
    console.log('🔍 SEARCHWORD - Called with query:', query, {
      isSwitchingModes: searchBar.isSwitchingModes,
      isDirectLookup: searchBar.isDirectLookup,
      currentShowSearchResults: searchBar.showSearchResults,
      searchResultsLength: searchResults.searchResults.length
    })
    
    if (!query.trim()) return

    const normalizedQuery = normalizeWord(query)
    
    // Set up search bar state for direct lookup
    searchBar.resetForDirectLookup()
    searchBar.setQuery(normalizedQuery)
    loading.setHasSearched(true)

    // Clear search results dropdown
    searchResults.clearSearchResults()
    
    // Only hide controls if we're not switching modes via the controls
    if (!searchBar.isSwitchingModes) {
      searchBar.hideControls()
    }

    // Perform the definition lookup
    await getDefinition(normalizedQuery)

    // Reset direct lookup flag after a delay
    setTimeout(() => {
      console.log('🔍 SEARCHWORD - Resetting isDirectLookup flag')
      searchBar.setDirectLookup(false)
    }, 2000)
  }

  const search = async (query: string) => {
    if (!query.trim()) return []

    try {
      const results = await searchResults.search(query)
      
      // Add to history if we have results
      if (results.length > 0) {
        history.addToHistory(query, results)
      }

      return results
    } catch (error) {
      console.error('Search error:', error)
      return []
    }
  }

  const getDefinition = async (word: string, forceRefresh?: boolean) => {
    const shouldForceRefresh = forceRefresh ?? loading.forceRefreshMode

    // Set up loading state
    loading.startLoading(
      shouldForceRefresh ? 'Regenerating word...' : 'Looking up word...',
      false
    )

    try {
      const entry = await searchResults.getDefinition(
        word,
        shouldForceRefresh,
        [...searchConfig.selectedSources], // Convert readonly to mutable
        [...searchConfig.selectedLanguages], // Convert readonly to mutable
        searchConfig.noAI,
        // Progress callback
        (stage, progress, message, _details) => {
          loading.updateProgress(progress, stage, message)
        },
        // Stage config callback
        (category, stages) => {
          loading.setStageDefinitions(category, stages)
        }
      )

      console.log('Definition lookup completed:', entry)
      
      // Auto-adjust AI mode based on model_info presence
      if (entry?.model_info) {
        searchConfig.setAI(true)
        console.log('Auto-enabled AI mode: definition has model_info')
      } else if (entry && !entry.model_info) {
        searchConfig.setAI(false)
        console.log('Auto-disabled AI mode: definition has no model_info')
      }

      // Add to lookup history
      if (entry) {
        history.addToLookupHistory(word, entry)
      }

      // Emit events for engagement tracking
      window.dispatchEvent(new CustomEvent('word-searched'))
      window.dispatchEvent(new CustomEvent('definition-viewed'))

      // Auto-switch from suggestions mode to dictionary mode after successful lookup
      if (ui.mode === 'suggestions') {
        ui.setMode('dictionary')
      }

      // Also get thesaurus data if we're in thesaurus mode
      if (ui.mode === 'thesaurus') {
        await getThesaurusData(word)
      }

      // Reset force refresh mode after successful lookup
      if (shouldForceRefresh && loading.forceRefreshMode) {
        loading.disableForceRefresh()
      }

      return entry
    } catch (error) {
      console.error('Definition error:', error)
      
      notifications.showError(
        error instanceof Error ? error.message : 'Failed to get definition'
      )
      
      throw error
    } finally {
      loading.stopLoading()
    }
  }

  const getThesaurusData = async (word: string) => {
    try {
      await searchResults.getThesaurusData(word)
    } catch (error) {
      console.error('Thesaurus error:', error)
      notifications.showError('Failed to get thesaurus data')
    }
  }

  const getAISuggestions = async (query: string, count: number = 12) => {
    try {
      // Set up loading state for AI suggestions
      loading.startSuggestions('Generating word suggestions...')
      
      // Set up search bar state
      searchBar.setDirectLookup(true)
      searchBar.hideDropdown()
      searchBar.hideControls()

      const response = await searchResults.getAISuggestions(
        query,
        count,
        // Progress callback
        (stage, progress, message, _details) => {
          loading.updateSuggestionsProgress(progress, stage, message)
        },
        // Stage config callback
        (category, stages) => {
          loading.setSuggestionsStageDefinitions(category, stages)
        }
      )

      // Add to AI query history
      history.addToAIQueryHistory(query)

      // Reset direct lookup flag
      setTimeout(() => {
        searchBar.setDirectLookup(false)
      }, 100)

      return response
    } catch (error) {
      console.error('AI suggestions error:', error)
      notifications.showError('Failed to generate word suggestions')
      throw error
    } finally {
      loading.stopSuggestions()
    }
  }

  // ==========================================================================
  // MODE SWITCHING OPERATIONS
  // ==========================================================================

  const toggleSearchMode = async (router?: any) => {
    // Don't allow mode switching during active search
    if (loading.isSearching || loading.isSuggestingWords) {
      return
    }

    console.log('🔄 toggleSearchMode called:', searchConfig.searchMode)
    
    // Store current state before switching
    const currentQuery = searchBar.searchQuery
    
    console.log('💾 Saving query for mode:', searchConfig.searchMode, 'query:', currentQuery)
    
    // Save current query to mode-specific storage BEFORE changing mode
    searchBar.saveModeQuery(searchConfig.searchMode, currentQuery)
    
    // Use search config store to handle the mode cycling and router navigation
    await searchConfig.toggleSearchMode(router, searchResults.currentEntry, ui.mode)
    
    // Restore query for the NEW mode
    const restoredQuery = searchBar.restoreModeQuery(searchConfig.searchMode)
    searchBar.setQuery(restoredQuery)
    
    console.log('🔄 Restored query for mode:', searchConfig.searchMode, 'query:', restoredQuery)
    
    // Clear search results when changing modes to prevent stale dropdown
    searchBar.clearResults()
    
    // Force reactivity trigger
    await nextTick()
    
    // Handle AI mode based on the new mode and restored query
    if (searchConfig.searchMode === 'lookup') {
      // AI mode detection is handled by the searchBar store automatically
      console.log('✨ AI mode state will be updated based on query')
    } else {
      // Disable AI mode when switching away from lookup mode
      searchBar.disableAIMode()
      console.log('❌ AI mode disabled - not in lookup mode')
    }

    // Reset suggestion mode when changing search modes
    if (ui.mode === 'suggestions' && searchConfig.searchMode !== 'lookup') {
      // Only reset if we don't have a current entry to fall back to
      if (!searchResults.currentEntry) {
        reset()
      } else {
        ui.setMode('dictionary')
      }
    }
  }

  const setSearchMode = async (
    newMode: 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage',
    router?: any
  ) => {
    const currentQuery = searchBar.searchQuery
    
    // Save current query before switching
    searchBar.saveModeQuery(searchConfig.searchMode, currentQuery)
    
    // Set switching modes flag
    searchBar.setSwitchingModes(true)
    
    // Use search config store to handle the mode setting and router navigation
    await searchConfig.setSearchMode(newMode, router, searchResults.currentEntry, ui.mode)
    
    // Restore query for the new mode
    const restoredQuery = searchBar.restoreModeQuery(newMode)
    searchBar.setQuery(restoredQuery)
    
    // Clear search results when changing modes
    searchBar.clearResults()
    
    // Force reactivity trigger
    await nextTick()
    
    // Reset the mode switching flag after a short delay
    setTimeout(() => {
      searchBar.setSwitchingModes(false)
    }, 500)
  }

  // ==========================================================================
  // UTILITY FUNCTIONS
  // ==========================================================================

  const reset = () => {
    searchBar.clearQuery()
    loading.resetAllLoading()
    searchResults.clearSearchResults()
    searchResults.clearCurrentEntry()
    searchResults.clearWordSuggestions()
    ui.setMode('dictionary')
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================

  return {
    // Search operations
    searchWord,
    search,
    getDefinition,
    getThesaurusData,
    getAISuggestions,
    
    // Mode operations
    toggleSearchMode,
    setSearchMode,
    
    // Utility
    reset
  }
}