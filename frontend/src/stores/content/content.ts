import { defineStore } from 'pinia'
import { ref, readonly, shallowRef } from 'vue'
import { dictionaryApi } from '@/api'
import type {
  SynthesizedDictionaryEntry,
  ThesaurusEntry,
  WordSuggestionResponse
} from '@/types'

/**
 * Error state for definition lookups
 */
interface DefinitionErrorState {
  hasError: boolean
  errorType: 'network' | 'not-found' | 'server' | 'ai-failed' | 'empty' | 'unknown'
  errorMessage: string
  canRetry: boolean
  originalWord?: string
}

/**
 * ContentStore - Manages current content display
 * Handles definitions, thesaurus data, word suggestions, and content updates
 * This store focuses on the "what is currently being displayed" aspect
 */
export const useContentStore = defineStore('content', () => {
  // ==========================================================================
  // CONTENT STATE
  // ==========================================================================
  
  // Current displayed content
  const currentEntry = shallowRef<SynthesizedDictionaryEntry | null>(null)
  const currentThesaurus = shallowRef<ThesaurusEntry | null>(null)
  const wordSuggestions = shallowRef<WordSuggestionResponse | null>(null)
  const currentWord = ref<string | null>(null)
  
  // Streaming state for progressive loading
  const partialEntry = shallowRef<Partial<SynthesizedDictionaryEntry> | null>(null)
  const isStreamingData = ref(false)
  
  // Error state
  const definitionError = ref<DefinitionErrorState | null>(null)
  
  // Sidebar navigation state
  const sidebarActiveCluster = ref<string | null>('')
  const sidebarActivePartOfSpeech = ref<string | null>('')
  
  // Sidebar accordion states for different views
  const sidebarAccordionState = shallowRef({
    lookup: [] as string[],
    wordlist: [] as string[],
    'word-of-the-day': [] as string[],
    stage: [] as string[],
  })
  
  // ==========================================================================
  // CONTENT MANAGEMENT
  // ==========================================================================
  
  const setCurrentEntry = (entry: SynthesizedDictionaryEntry | null) => {
    currentEntry.value = entry
    if (entry) {
      currentWord.value = entry.word
      definitionError.value = null
    }
  }
  
  const setPartialEntry = (entry: Partial<SynthesizedDictionaryEntry> | null) => {
    partialEntry.value = entry
  }
  
  const setCurrentThesaurus = (thesaurus: ThesaurusEntry | null) => {
    currentThesaurus.value = thesaurus
  }
  
  const setWordSuggestions = (suggestions: WordSuggestionResponse | null) => {
    wordSuggestions.value = suggestions
  }
  
  const setStreamingState = (streaming: boolean) => {
    isStreamingData.value = streaming
  }
  
  const setError = (error: DefinitionErrorState | null) => {
    definitionError.value = error
    if (error) {
      currentEntry.value = null
    }
  }
  
  // ==========================================================================
  // CONTENT UPDATES
  // ==========================================================================
  
  const updateDefinition = async (definitionId: string, updates: any) => {
    if (!currentEntry.value) return
    
    try {
      const response = await dictionaryApi.updateDefinition(
        definitionId,
        updates
      )
      
      // Update the current entry with the new data
      const updatedEntry = { ...currentEntry.value }
      const defIndex = updatedEntry.definitions?.findIndex(d => d.id === definitionId)
      
      if (defIndex !== undefined && defIndex >= 0 && updatedEntry.definitions) {
        updatedEntry.definitions[defIndex] = {
          ...updatedEntry.definitions[defIndex],
          ...response
        }
        currentEntry.value = updatedEntry
      }
      
      return response
    } catch (error) {
      console.error('[Content] Failed to update definition:', error)
      throw error
    }
  }
  
  const updateExample = async (definitionId: string, exampleId: string, newText: string) => {
    if (!currentEntry.value) return
    
    try {
      const response = await dictionaryApi.updateExample(
        exampleId,
        { text: newText }
      )
      
      // Update the current entry with the new example
      const updatedEntry = { ...currentEntry.value }
      const defIndex = updatedEntry.definitions?.findIndex(d => d.id === definitionId)
      
      if (defIndex !== undefined && defIndex >= 0 && updatedEntry.definitions) {
        const exampleIndex = updatedEntry.definitions[defIndex].examples?.findIndex(
          e => e.id === exampleId
        )
        
        if (exampleIndex !== undefined && exampleIndex >= 0 && 
            updatedEntry.definitions[defIndex].examples) {
          updatedEntry.definitions[defIndex].examples[exampleIndex] = response
          currentEntry.value = updatedEntry
        }
      }
      
      return response
    } catch (error) {
      console.error('[Content] Failed to update example:', error)
      throw error
    }
  }
  
  const regenerateDefinitionComponent = async (
    definitionId: string,
    component: 'definition' | 'examples' | 'usage_notes'
  ) => {
    if (!currentEntry.value) return
    
    try {
      const response = await dictionaryApi.regenerateDefinitionComponent(
        definitionId,
        component
      )
      
      // Update the current entry with regenerated content
      const updatedEntry = { ...currentEntry.value }
      const defIndex = updatedEntry.definitions?.findIndex(d => d.id === definitionId)
      
      if (defIndex !== undefined && defIndex >= 0 && updatedEntry.definitions) {
        updatedEntry.definitions[defIndex] = {
          ...updatedEntry.definitions[defIndex],
          ...response
        }
        currentEntry.value = updatedEntry
      }
      
      return response
    } catch (error) {
      console.error('[Content] Failed to regenerate component:', error)
      throw error
    }
  }
  
  const regenerateExamples = async (definitionIndex: number) => {
    if (!currentEntry.value || !currentEntry.value.definitions) return
    
    const definition = currentEntry.value.definitions[definitionIndex]
    if (!definition) return
    
    try {
      const response = await dictionaryApi.regenerateExamples(
        currentEntry.value.word,
        definitionIndex
      )
      
      // Update the current entry with new examples
      const updatedEntry = { ...currentEntry.value }
      if (updatedEntry.definitions) {
        updatedEntry.definitions[definitionIndex] = {
          ...definition,
          examples: response.examples as any // API returns different format
        }
        currentEntry.value = updatedEntry
      }
      
      return response
    } catch (error) {
      console.error('[Content] Failed to regenerate examples:', error)
      throw error
    }
  }
  
  const refreshEntryImages = async () => {
    if (!currentEntry.value) return
    
    try {
      const response = await dictionaryApi.refreshSynthEntry(currentEntry.value.word)
      
      // Update the current entry with new images
      currentEntry.value = {
        ...currentEntry.value,
        ...response
      }
      
      return response
    } catch (error) {
      console.error('[Content] Failed to refresh entry images:', error)
      throw error
    }
  }
  
  // ==========================================================================
  // STATE MANAGEMENT
  // ==========================================================================
  
  const clearCurrentEntry = () => {
    currentEntry.value = null
    currentThesaurus.value = null
    currentWord.value = null
    definitionError.value = null
    partialEntry.value = null
  }
  
  const clearWordSuggestions = () => {
    wordSuggestions.value = null
  }
  
  const clearError = () => {
    definitionError.value = null
  }
  
  // ==========================================================================
  // SIDEBAR NAVIGATION
  // ==========================================================================
  
  const setSidebarActiveCluster = (cluster: string | null) => {
    sidebarActiveCluster.value = cluster
  }
  
  const setSidebarActivePartOfSpeech = (partOfSpeech: string | null) => {
    sidebarActivePartOfSpeech.value = partOfSpeech
  }
  
  // Accordion state management
  const setSidebarAccordionState = (
    view: 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage',
    state: string[]
  ) => {
    sidebarAccordionState.value = {
      ...sidebarAccordionState.value,
      [view]: [...state]
    }
  }
  
  const toggleAccordionItem = (
    view: 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage',
    item: string
  ) => {
    const currentState = sidebarAccordionState.value[view]
    const newState = currentState.includes(item)
      ? currentState.filter(i => i !== item)
      : [...currentState, item]
    
    sidebarAccordionState.value = {
      ...sidebarAccordionState.value,
      [view]: newState
    }
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    currentEntry: readonly(currentEntry),
    currentThesaurus: readonly(currentThesaurus),
    wordSuggestions: readonly(wordSuggestions),
    currentWord: readonly(currentWord),
    partialEntry: readonly(partialEntry),
    isStreamingData: readonly(isStreamingData),
    definitionError: readonly(definitionError),
    
    // Sidebar navigation state
    sidebarActiveCluster: readonly(sidebarActiveCluster),
    sidebarActivePartOfSpeech: readonly(sidebarActivePartOfSpeech),
    sidebarAccordionState: readonly(sidebarAccordionState),
    
    // Actions
    setCurrentEntry,
    setPartialEntry,
    setCurrentThesaurus,
    setWordSuggestions,
    setStreamingState,
    setError,
    
    // Updates
    updateDefinition,
    updateExample,
    regenerateDefinitionComponent,
    regenerateExamples,
    refreshEntryImages,
    
    // State management
    clearCurrentEntry,
    clearWordSuggestions,
    clearError,
    
    // Sidebar navigation
    setSidebarActiveCluster,
    setSidebarActivePartOfSpeech,
    setSidebarAccordionState,
    toggleAccordionItem,
  }
}, {
  persist: {
    key: 'content',
    pick: [
      'currentEntry',
      'currentThesaurus',
      'wordSuggestions',
      'currentWord',
      'sidebarActiveCluster',
      'sidebarActivePartOfSpeech',
      'sidebarAccordionState'
    ]
  }
})