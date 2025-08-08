import { defineStore } from 'pinia'
import { ref, readonly, computed, shallowRef } from 'vue'
import { useLookupContentState } from './modes/lookup'
import { useSearchBarStore } from '../search/search-bar'
import { useHistoryStore } from './history'
import type {
  SynthesizedDictionaryEntry,
  ThesaurusEntry,
  WordSuggestionResponse,
  Definition
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
  const searchBarStore = useSearchBarStore()
  const lookupContent = useLookupContentState()
  
  // ==========================================================================
  // SHARED CONTENT STATE (non-mode-specific)
  // ==========================================================================
  
  const currentWord = ref<string | null>(null)
  const definitionError = ref<DefinitionErrorState | null>(null)
  
  // General accordion state for sidebar views (shared across modes)
  const sidebarAccordionState = shallowRef({
    lookup: [] as string[],
    wordlist: [] as string[],
    'word-of-the-day': [] as string[],
    stage: [] as string[]
  })
  
  // ==========================================================================
  // MODE-AWARE COMPUTED PROPERTIES
  // ==========================================================================
  
  // Delegate to current mode's content
  const currentEntry = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.currentEntry.value
    }
    return null
  })
  
  const currentThesaurus = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.currentThesaurus.value
    }
    return null
  })
  
  const wordSuggestions = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.wordSuggestions.value
    }
    return null
  })
  
  const partialEntry = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.partialEntry.value
    }
    return null
  })
  
  const isStreamingData = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.isStreamingData.value
    }
    return false
  })
  
  const regeneratingDefinitionIndex = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.regeneratingDefinitionIndex.value
    }
    return null
  })
  
  // Progressive sidebar state (mode-specific, currently only lookup mode)
  const sidebarActiveCluster = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.sidebarActiveCluster.value
    }
    return null
  })
  
  const sidebarActivePartOfSpeech = computed(() => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.sidebarActivePartOfSpeech.value
    }
    return null
  })
  
  // ==========================================================================
  // DELEGATED ACTIONS
  // ==========================================================================
  
  const setCurrentEntry = (entry: SynthesizedDictionaryEntry | null) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setCurrentEntry(entry)
    }
    if (entry) {
      currentWord.value = entry.word
      definitionError.value = null
      // Add to lookup history when a new entry is set
      const historyStore = useHistoryStore()
      historyStore.addToLookupHistory(entry.word, entry)
    }
  }
  
  const setPartialEntry = (entry: Partial<SynthesizedDictionaryEntry> | null) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setPartialEntry(entry)
    }
  }
  
  const setCurrentThesaurus = (thesaurus: ThesaurusEntry | null) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setCurrentThesaurus(thesaurus)
    }
  }
  
  const setWordSuggestions = (suggestions: WordSuggestionResponse | null) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setWordSuggestions(suggestions)
    }
  }
  
  const setStreamingState = (streaming: boolean) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setStreamingState(streaming)
    }
  }
  
  const setError = (error: DefinitionErrorState | null) => {
    definitionError.value = error
    if (error && searchBarStore.searchMode === 'lookup') {
      lookupContent.setCurrentEntry(null)
    }
  }
  
  // ==========================================================================
  // DELEGATED CONTENT OPERATIONS
  // ==========================================================================
  
  const updateDefinition = async (definitionId: string, updates: Partial<Definition>) => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.updateDefinition(definitionId, updates)
    }
    throw new Error('Update definition not supported in current mode')
  }
  
  const updateExample = async (definitionId: string, exampleId: string, newText: string) => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.updateExample(definitionId, exampleId, newText)
    }
    throw new Error('Update example not supported in current mode')
  }
  
  const regenerateDefinitionComponent = async (
    definitionId: string,
    component: 'definition' | 'examples' | 'usage_notes'
  ) => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.regenerateDefinitionComponent(definitionId, component)
    }
    throw new Error('Regenerate definition component not supported in current mode')
  }
  
  const regenerateExamples = async (definitionIndex: number) => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.regenerateExamples(definitionIndex)
    }
    throw new Error('Regenerate examples not supported in current mode')
  }
  
  const refreshEntryImages = async () => {
    if (searchBarStore.searchMode === 'lookup') {
      return lookupContent.refreshEntryImages()
    }
    throw new Error('Refresh entry images not supported in current mode')
  }
  
  // ==========================================================================
  // STATE MANAGEMENT
  // ==========================================================================
  
  const clearCurrentEntry = () => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.clearCurrentEntry()
    }
    currentWord.value = null
    definitionError.value = null
  }
  
  const clearWordSuggestions = () => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.clearWordSuggestions()
    }
  }
  
  const clearError = () => {
    definitionError.value = null
  }
  
  // ==========================================================================
  // SIDEBAR ACCORDION MANAGEMENT
  // ==========================================================================
  
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
      ? currentState.filter((i: string) => i !== item)
      : [...currentState, item]
    
    sidebarAccordionState.value = {
      ...sidebarAccordionState.value,
      [view]: newState
    }
  }
  
  // ==========================================================================
  // PROGRESSIVE SIDEBAR MANAGEMENT (Mode-specific)
  // ==========================================================================
  
  const setSidebarActiveCluster = (cluster: string | null) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setSidebarActiveCluster(cluster)
    }
  }
  
  const setSidebarActivePartOfSpeech = (partOfSpeech: string | null) => {
    if (searchBarStore.searchMode === 'lookup') {
      lookupContent.setSidebarActivePartOfSpeech(partOfSpeech)
    }
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Mode-aware state (computed)
    currentEntry,
    currentThesaurus,
    wordSuggestions,
    partialEntry,
    isStreamingData,
    regeneratingDefinitionIndex,
    sidebarActiveCluster,
    sidebarActivePartOfSpeech,
    
    // Shared state
    currentWord: readonly(currentWord),
    definitionError: readonly(definitionError),
    sidebarAccordionState: readonly(sidebarAccordionState),
    
    
    // Delegated actions
    setCurrentEntry,
    setPartialEntry,
    setCurrentThesaurus,
    setWordSuggestions,
    setStreamingState,
    setError,
    
    // Delegated operations
    updateDefinition,
    updateExample,
    regenerateDefinitionComponent,
    regenerateExamples,
    refreshEntryImages,
    
    // State management
    clearCurrentEntry,
    clearWordSuggestions,
    clearError,
    
    // Sidebar accordion
    setSidebarAccordionState,
    toggleAccordionItem,
    
    // Progressive sidebar
    setSidebarActiveCluster,
    setSidebarActivePartOfSpeech
    
  }
}, {
  persist: {
    key: 'content',
    pick: [
      'currentEntry',
      'currentThesaurus',
      'wordSuggestions',
      'currentWord',
      'sidebarAccordionState'
    ]
  }
})