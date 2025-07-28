import { useMagicKeys, whenever } from '@vueuse/core';
import { useRouter } from 'vue-router';
import { useAppStore } from '@/stores';
import { showError } from '@/plugins/toast';
import { extractWordCount } from '../utils/ai-query';
import type { SearchResult } from '@/types';

interface UseSearchBarKeyboardOptions {
  searchInputRef: any;
  onAutocompleteAccept: () => Promise<boolean>;
  onAutocompleteSpace: (event: KeyboardEvent) => void;
  onAutocompleteArrow: (event: KeyboardEvent) => void;
}

/**
 * Focused composable for SearchBar keyboard interactions
 * Handles Enter, Escape, navigation, and keyboard shortcuts
 */
export function useSearchBarKeyboard(options: UseSearchBarKeyboardOptions) {
  const store = useAppStore();
  const router = useRouter();
  const { searchInputRef, onAutocompleteAccept, onAutocompleteSpace, onAutocompleteArrow } = options;

  // Navigate through search results with arrow keys
  const navigateResults = (direction: number) => {
    if (store.searchResults.length === 0) return;

    const newIndex = Math.max(
      0,
      Math.min(
        store.searchResults.length - 1,
        store.searchSelectedIndex + direction
      )
    );
    
    store.searchSelectedIndex = newIndex;
  };

  // Select a search result
  const selectResult = async (result: SearchResult) => {
    // Navigate to appropriate route based on mode
    const routeName = store.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: result.word } });
    
    // Use searchWord for direct lookup (sets isDirectLookup flag)
    await store.searchWord(result.word);
  };

  // Handle Enter key press
  const handleEnter = async () => {
    // Try autocomplete first
    if (store.autocompleteText) {
      const accepted = await onAutocompleteAccept();
      if (accepted) return;
    }

    const query = store.searchQuery;
    
    // Handle stage mode
    if (store.searchMode === 'stage' && query) {
      // Emit stage-enter event (handled by parent component)
      return { type: 'stage-enter', query };
    }

    // Handle wordlist mode
    if (store.searchMode === 'wordlist' && query) {
      const words = query
        .split(/[,\s\n]+/)
        .map((word) => word.trim())
        .filter((word) => word.length > 0);

      if (words.length > 0) {
        const routeName = store.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
        router.push({ name: routeName, params: { word: words[0] } });
        
        // Use searchWord for direct lookup
        await store.searchWord(words[0]);
      }
      return;
    }

    // Handle AI query mode
    if (store.isAIQuery && query) {
      try {
        const extractedCount = extractWordCount(query);
        const wordSuggestions = await store.getAISuggestions(query, extractedCount);

        if (wordSuggestions && wordSuggestions.suggestions.length > 0) {
          store.wordSuggestions = wordSuggestions;
          store.mode = 'suggestions';
          store.hasSearched = true;
          store.sessionState.aiQueryText = query;
        } else {
          store.showErrorAnimation = true;
          showError('No word suggestions found for this query');
          setTimeout(() => {
            store.showErrorAnimation = false;
          }, 600);
        }
      } catch (error: any) {
        console.error('AI suggestion error:', error);
        store.showErrorAnimation = true;
        showError(error.message || 'Failed to get word suggestions');
        setTimeout(() => {
          store.showErrorAnimation = false;
        }, 600);
      }
      return;
    }

    // Regular search
    if (store.searchResults.length > 0 && store.searchSelectedIndex >= 0) {
      await selectResult(store.searchResults[store.searchSelectedIndex]);
    } else if (query) {
      const routeName = store.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
      router.push({ name: routeName, params: { word: query } });
      
      // Use searchWord for direct lookup
      await store.searchWord(query);
    }
  };

  // Handle Shift+Enter for force refresh
  const handleShiftEnter = async () => {
    const previousForceRefresh = store.forceRefreshMode;
    store.forceRefreshMode = true;
    
    await handleEnter();
    
    store.forceRefreshMode = previousForceRefresh;
  };

  // Handle Escape key
  const handleEscape = () => {
    if (store.showSearchControls || store.showSearchResults) {
      store.showSearchControls = false;
      store.showSearchResults = false;
    } else {
      store.isSearchBarFocused = false;
    }
  };

  // Handle Space key (for autocomplete)
  const handleSpaceKey = (event: KeyboardEvent) => {
    onAutocompleteSpace(event);
  };

  // Handle Arrow keys (for autocomplete)
  const handleArrowKey = (event: KeyboardEvent) => {
    onAutocompleteArrow(event);
  };

  // Setup keyboard shortcuts
  const keys = useMagicKeys();
  const shiftEnter = keys['Shift+Enter'];
  const cmdEnter = keys['Cmd+Enter'];
  const ctrlEnter = keys['Ctrl+Enter'];

  // Watch for force refresh shortcuts
  whenever(shiftEnter, () => {
    if (store.isSearchBarFocused && searchInputRef.value) {
      handleShiftEnter();
    }
  });

  whenever(cmdEnter, () => {
    if (store.isSearchBarFocused && searchInputRef.value) {
      handleShiftEnter();
    }
  });

  whenever(ctrlEnter, () => {
    if (store.isSearchBarFocused && searchInputRef.value) {
      handleShiftEnter();
    }
  });

  return {
    // Methods
    navigateResults,
    selectResult,
    handleEnter,
    handleShiftEnter,
    handleEscape,
    handleSpaceKey,
    handleArrowKey,
  };
}