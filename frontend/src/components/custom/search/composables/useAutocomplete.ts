import { ref, watch, nextTick, type Ref } from 'vue'
import type { SearchResult } from '@/types'

interface UseAutocompleteOptions {
  query: Ref<string>
  searchResults: Ref<SearchResult[]>
  searchInput: Ref<HTMLTextAreaElement | undefined>
  onQueryUpdate: (newQuery: string) => void
}

/**
 * Composable for managing autocomplete text suggestions
 * Handles autocomplete preview, text completion, and related interactions
 */
export function useAutocomplete({
  query,
  searchResults,
  searchInput,
  onQueryUpdate,
}: UseAutocompleteOptions) {
  // State
  const autocompleteText = ref('')
  
  // Methods
  const updateAutocomplete = () => {
    if (!query.value || query.value.length < 2 || !searchResults.value || !searchResults.value.length) {
      autocompleteText.value = ''
      return
    }
    
    // Take the top match (highest score)
    const topMatch = searchResults.value[0]
    
    // Check if the top match starts with the current query (case insensitive)
    const queryLower = query.value.toLowerCase()
    const wordLower = topMatch.word.toLowerCase()
    
    if (
      wordLower.startsWith(queryLower) &&
      topMatch.word.length > query.value.length
    ) {
      // Use the top match for completion
      autocompleteText.value = topMatch.word
    } else {
      // No suitable completion available
      autocompleteText.value = ''
    }
  }
  
  const fillAutocomplete = () => {
    if (autocompleteText.value) {
      onQueryUpdate(autocompleteText.value)
      autocompleteText.value = ''
      
      // Move cursor to end
      nextTick(() => {
        if (searchInput.value) {
          const length = query.value.length
          searchInput.value.setSelectionRange(length, length)
        }
      })
    }
  }
  
  const acceptAutocomplete = async () => {
    if (autocompleteText.value) {
      fillAutocomplete()
      return true
    }
    return false
  }
  
  const handleSpaceKey = (event: KeyboardEvent) => {
    if (autocompleteText.value) {
      event.preventDefault()
      fillAutocomplete()
      // Add the space after filling
      nextTick(() => {
        onQueryUpdate(query.value + ' ')
      })
    }
  }
  
  const handleArrowKey = (event: KeyboardEvent) => {
    if (autocompleteText.value && searchInput.value) {
      const currentPosition = searchInput.value.selectionStart || 0
      
      // If it's a right arrow and we're at the end of the current text
      if (
        event.key === 'ArrowRight' &&
        currentPosition === query.value.length
      ) {
        event.preventDefault()
        fillAutocomplete()
        return
      }
      
      // Use nextTick to get the cursor position after the arrow key press
      nextTick(() => {
        if (searchInput.value) {
          const cursorPosition = searchInput.value.selectionStart || 0
          
          // If cursor moves beyond the current query length (into ghost text area)
          if (cursorPosition > query.value.length) {
            fillAutocomplete()
          }
        }
      })
    }
  }
  
  const handleInputClick = (_event: MouseEvent) => {
    if (autocompleteText.value && searchInput.value) {
      const input = searchInput.value
      const cursorPosition = input.selectionStart || 0
      
      // If cursor is positioned beyond the current query length (in ghost text area)
      if (cursorPosition > query.value.length) {
        fillAutocomplete()
      }
    }
  }
  
  const clearAutocomplete = () => {
    autocompleteText.value = ''
  }
  
  // Watchers
  watch(searchResults, () => {
    updateAutocomplete()
  })
  
  watch(query, () => {
    updateAutocomplete()
  })
  
  return {
    // State
    autocompleteText,
    
    // Methods
    updateAutocomplete,
    fillAutocomplete,
    acceptAutocomplete,
    handleSpaceKey,
    handleArrowKey,
    handleInputClick,
    clearAutocomplete,
  }
}