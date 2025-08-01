import { defineStore } from 'pinia'
import { ref, readonly, computed } from 'vue'
import { dictionaryApi } from '@/api'
import { normalizeWord } from '@/utils'
// Router sync is handled by the orchestrator
import type {
  SearchResult,
  ThesaurusEntry,
  WordSuggestionResponse
} from '@/types'
import type { DictionaryProvider, Language, SynthesizedDictionaryEntry } from '@/types/api'

/**
 * SearchResultsStore - Search results, current content, and streaming data
 * Handles search operations, definition lookups, streaming data, and content management
 * Session-persists critical data like current entry and search results
 */
export const useSearchResultsStore = defineStore('searchResults', () => {
  // ==========================================================================
  // RUNTIME STATE (Non-persisted)
  // ==========================================================================
  
  // Search results for dropdown
  const searchResults = ref<SearchResult[]>([])
  
  // Streaming state for progressive loading
  const partialEntry = ref<Partial<SynthesizedDictionaryEntry> | null>(null)
  const isStreamingData = ref(false)
  
  // Error state for definition display
  const definitionError = ref<{
    hasError: boolean
    errorType: 'network' | 'not-found' | 'server' | 'ai-failed' | 'empty' | 'unknown'
    errorMessage: string
    canRetry: boolean
    originalWord?: string
  } | null>(null)

  // ==========================================================================
  // SESSION-PERSISTED STATE
  // ==========================================================================
  
  // Current content
  const currentEntry = ref<SynthesizedDictionaryEntry | null>(null)
  const currentThesaurus = ref<ThesaurusEntry | null>(null)
  const wordSuggestions = ref<WordSuggestionResponse | null>(null)
  const currentWord = ref<string | null>(null)
  
  // Cursor position for search results navigation
  const searchCursorPosition = ref(0)

  // Router integration is handled by the orchestrator

  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  // Combined search state for easy access
  const searchState = computed(() => ({
    results: searchResults.value,
    currentEntry: currentEntry.value || undefined,
    currentThesaurus: currentThesaurus.value || undefined,
    wordSuggestions: wordSuggestions.value || undefined,
    isStreaming: isStreamingData.value,
    partialEntry: partialEntry.value,
    hasError: !!definitionError.value?.hasError,
    error: definitionError.value
  }))

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Search operations
  const search = async (query: string): Promise<SearchResult[]> => {
    if (!query.trim()) return []

    try {
      const results = await dictionaryApi.searchWord(query)
      searchResults.value = results
      return results
    } catch (error) {
      console.error('Search error:', error)
      return []
    }
  }

  const clearSearchResults = () => {
    searchResults.value = []
  }

  // Definition operations
  const getDefinition = async (
    word: string,
    forceRefresh = false,
    selectedSources: string[] = ['wiktionary'],
    selectedLanguages: string[] = ['en'],
    noAI = true,
    onProgress?: (stage: string, progress: number, message?: string, details?: any) => void,
    onStageConfig?: (category: string, stages: any[]) => void,
    onPartialData?: (partialData: any) => void
  ) => {
    const normalizedWord = normalizeWord(word)
    
    // Clear any existing error state when starting new search (only if not retrying an error)
    if (!definitionError.value?.hasError || definitionError.value.originalWord !== normalizedWord) {
      definitionError.value = null
    }

    try {
      // Reset partial state and start streaming
      partialEntry.value = null
      isStreamingData.value = true

      // Always use streaming endpoint to get pipeline progress
      const entry = await dictionaryApi.getDefinitionStream(
        word,
        forceRefresh,
        selectedSources as DictionaryProvider[],
        selectedLanguages as Language[],
        (stage, progress, message, details) => {
          console.log(`Stage: ${stage}, Progress: ${progress}%, Message: ${message}`)
          onProgress?.(stage, progress, message, details)
        },
        (category, stages) => {
          console.log(`Received stage config for category: ${category}`, stages)
          onStageConfig?.(category, stages)
        },
        (partialData) => {
          console.log('Received partial data:', partialData)
          partialEntry.value = partialData
          onPartialData?.(partialData)
        },
        noAI
      )

      console.log('Setting currentEntry:', entry)
      currentEntry.value = entry
      currentWord.value = normalizedWord

      // Check for empty results and set error state if needed
      if (!entry || !entry.definitions || entry.definitions.length === 0) {
        definitionError.value = {
          hasError: true,
          errorType: 'empty',
          errorMessage: `No definitions found for "${word}"`,
          canRetry: true,
          originalWord: word
        }
      } else {
        // Clear error state on successful lookup with results
        definitionError.value = null
      }

      return entry
    } catch (error) {
      console.error('Definition error:', error)
      
      // Reset streaming state on error
      partialEntry.value = null
      
      // Set error state based on error type
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
      let errorType: 'network' | 'not-found' | 'server' | 'ai-failed' | 'empty' | 'unknown' = 'unknown'
      let canRetry = true
      
      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        errorType = 'not-found'
        canRetry = false
      } else if (errorMessage.includes('network') || errorMessage.includes('fetch') || 
                 errorMessage.includes('Stream ended without completion') ||
                 errorMessage.includes('connection')) {
        errorType = 'network'
      } else if (errorMessage.includes('500') || errorMessage.includes('server')) {
        errorType = 'server'
      } else if (errorMessage.includes('AI') || errorMessage.includes('synthesis')) {
        errorType = 'ai-failed'
      }
      
      definitionError.value = {
        hasError: true,
        errorType,
        errorMessage: errorType === 'not-found' 
          ? `No definitions found for "${word}"`
          : errorMessage,
        canRetry,
        originalWord: word
      }
      
      // Force clear current entry to ensure error state shows
      currentEntry.value = null
      throw error
    } finally {
      isStreamingData.value = false
    }
  }

  const getThesaurusData = async (word: string) => {
    try {
      // If we already have the current entry, use its synonyms directly
      if (currentEntry.value && currentEntry.value.word === word) {
        const synonymsList: Array<{ word: string; score: number }> = []

        // Collect synonyms from all definitions
        currentEntry.value.definitions?.forEach((def, index) => {
          if (def.synonyms && Array.isArray(def.synonyms)) {
            def.synonyms.forEach((syn: string, synIndex) => {
              // Avoid duplicates
              if (!synonymsList.some((s) => s.word === syn)) {
                // Generate varying scores based on definition order and synonym position
                const baseScore = 0.9 - index * 0.1
                const positionPenalty = synIndex * 0.02
                const score = Math.max(0.5, Math.min(0.95, baseScore - positionPenalty))
                synonymsList.push({ word: syn, score })
              }
            })
          }
        })

        currentThesaurus.value = {
          word: word,
          synonyms: synonymsList,
          confidence: 0.9,
        }
      } else {
        // Fallback to API call if we don't have the entry
        const thesaurus = await dictionaryApi.getSynonyms(word)
        currentThesaurus.value = thesaurus
      }
    } catch (error) {
      console.error('Thesaurus error:', error)
      currentThesaurus.value = {
        word: word,
        synonyms: [],
        confidence: 0,
      }
    }
  }

  // AI suggestions
  const getAISuggestions = async (
    query: string,
    count: number = 12,
    onProgress?: (stage: string, progress: number, message?: string, details?: any) => void,
    onStageConfig?: (category: string, stages: any[]) => void
  ): Promise<WordSuggestionResponse | null> => {
    try {
      // Use streaming API for real-time progress updates
      const response = await dictionaryApi.getAISuggestionsStream(
        query,
        count,
        (stage, progress, message, details) => {
          console.log(`AI Suggestions - Stage: ${stage}, Progress: ${progress}%, Message: ${message || ''}`)
          onProgress?.(stage, progress, message, details)
        },
        (category, stages) => {
          console.log(`Received suggestions stage config for category: ${category}`, stages)
          onStageConfig?.(category, stages)
        }
      )

      wordSuggestions.value = response
      return response
    } catch (error) {
      console.error('AI suggestions error:', error)
      wordSuggestions.value = null
      throw error
    }
  }

  // Content update operations
  const updateDefinition = async (definitionId: string, updates: any) => {
    console.log('[SearchResults] Updating definition:', definitionId, 'with:', updates)
    try {
      const response = await dictionaryApi.updateDefinition(definitionId, updates)
      console.log('[SearchResults] Update response:', response)

      // Update current entry if this definition is part of it
      if (currentEntry.value) {
        const defIndex = currentEntry.value.definitions.findIndex((d) => d.id === definitionId)
        if (defIndex >= 0) {
          console.log('[SearchResults] Updating local definition at index:', defIndex)
          Object.assign(currentEntry.value.definitions[defIndex], updates)
        } else {
          console.warn('[SearchResults] Definition not found in current entry')
        }
      }

      return response
    } catch (error) {
      console.error('Failed to update definition:', error)
      throw error
    }
  }

  const updateExample = async (exampleId: string, updates: { text: string }) => {
    console.log('[SearchResults] Updating example:', exampleId, 'with:', updates)
    try {
      const response = await dictionaryApi.updateExample(exampleId, updates)
      console.log('[SearchResults] Example update response:', response)
      return response
    } catch (error) {
      console.error('[SearchResults] Failed to update example:', error)
      throw error
    }
  }

  const regenerateDefinitionComponent = async (definitionId: string, component: string) => {
    try {
      const response = await dictionaryApi.regenerateDefinitionComponent(definitionId, component)

      // Update current entry with regenerated data
      if (currentEntry.value) {
        const defIndex = currentEntry.value.definitions.findIndex((d) => d.id === definitionId)
        if (defIndex >= 0) {
          const def = currentEntry.value.definitions[defIndex]
          // Update the specific component
          if (component === 'language_register') {
            def.language_register = response[component]
          } else if (component in def) {
            (def as any)[component] = response[component]
          }
        }
      }

      return response
    } catch (error) {
      console.error(`Failed to regenerate ${component}:`, error)
      throw error
    }
  }

  const regenerateExamples = async (definitionIndex: number, definitionText?: string) => {
    if (!currentEntry.value) return

    try {
      const response = await dictionaryApi.regenerateExamples(
        currentEntry.value.word,
        definitionIndex,
        definitionText,
        2
      )

      // Update the current entry with new examples
      if (currentEntry.value.definitions[definitionIndex]) {
        const def = currentEntry.value.definitions[definitionIndex]
        // Replace only generated examples, keep literature ones
        const literatureExamples = def.examples?.filter((ex) => ex.type === 'literature') || []
        def.examples = [...(response.examples as any[]), ...literatureExamples]
      }

      return response
    } catch (error) {
      console.error('Failed to regenerate examples:', error)
      throw error
    }
  }

  const refreshSynthEntryImages = async () => {
    console.log('[SearchResults] Refreshing synthesized entry images')
    if (!currentEntry.value?.id) {
      console.warn('[SearchResults] No current entry ID available for image refresh')
      return
    }

    try {
      const refreshedEntry = await dictionaryApi.refreshSynthEntry(currentEntry.value.id)
      console.log('[SearchResults] Refreshed entry with updated images:', refreshedEntry)
      
      // Replace the current entry with refreshed data
      currentEntry.value = refreshedEntry

      return refreshedEntry
    } catch (error) {
      console.error('[SearchResults] Failed to refresh entry images:', error)
      throw error
    }
  }

  // State management
  const clearCurrentEntry = () => {
    currentEntry.value = null
    currentThesaurus.value = null
    currentWord.value = null
    definitionError.value = null
  }

  const clearWordSuggestions = () => {
    wordSuggestions.value = null
  }

  const clearError = () => {
    definitionError.value = null
  }

  const setCursorPosition = (position: number) => {
    searchCursorPosition.value = position
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    searchResults: readonly(searchResults),
    currentEntry: readonly(currentEntry),
    currentThesaurus: readonly(currentThesaurus),
    wordSuggestions: readonly(wordSuggestions),
    currentWord: readonly(currentWord),
    searchCursorPosition: readonly(searchCursorPosition),
    partialEntry: readonly(partialEntry),
    isStreamingData: readonly(isStreamingData),
    definitionError: readonly(definitionError),
    
    // Computed
    searchState,
    
    // Actions
    search,
    clearSearchResults,
    getDefinition,
    getThesaurusData,
    getAISuggestions,
    updateDefinition,
    updateExample,
    regenerateDefinitionComponent,
    regenerateExamples,
    refreshSynthEntryImages,
    clearCurrentEntry,
    clearWordSuggestions,
    clearError,
    setCursorPosition
  }
}, {
  persist: {
    key: 'search-results',
    pick: [
      'currentEntry',
      'currentThesaurus', 
      'wordSuggestions',
      'currentWord',
      'searchCursorPosition'
    ]
  }
})