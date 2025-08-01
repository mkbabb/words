import { useMagicKeys, whenever } from '@vueuse/core';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
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
  const { searchResults, orchestrator, searchBar, searchConfig, ui } = useStores();
  const router = useRouter();
  const { searchInputRef, onAutocompleteAccept, onAutocompleteSpace, onAutocompleteArrow } = options;

  // Navigate through search results with arrow keys
  const navigateResults = (direction: number) => {
    if (searchResults.searchResults.length === 0) return;

    const newIndex = Math.max(
      0,
      Math.min(
        searchResults.searchResults.length - 1,
        searchBar.searchSelectedIndex + direction
      )
    );
    
    searchBar.setSelectedIndex(newIndex);
  };

  // Select a search result
  const selectResult = async (result: SearchResult) => {
    // Navigate to appropriate route based on mode
    const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: result.word } });
    
    // Use orchestrator for direct lookup (sets isDirectLookup flag)
    await orchestrator.searchWord(result.word);
  };

  // Handle Enter key press
  const handleEnter = async () => {
    // Try autocomplete first
    if (searchBar.autocompleteText) {
      const accepted = await onAutocompleteAccept();
      if (accepted) return;
    }

    const query = searchBar.searchQuery;
    
    // If query is blank, just unfocus the search bar
    if (!query || query.trim() === '') {
      searchBar.setFocused(false);
      return;
    }
    
    // Handle stage mode
    if (searchConfig.searchMode === 'stage' && query) {
      // Emit stage-enter event (handled by parent component)
      return { type: 'stage-enter', query };
    }

    // Handle wordlist mode
    if (searchConfig.searchMode === 'wordlist' && query) {
      const words = query
        .split(/[,\s\n]+/)
        .map((word: string) => word.trim())
        .filter((word: string) => word.length > 0);

      if (words.length > 0) {
        const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
        router.push({ name: routeName, params: { word: words[0] } });
        
        // Use orchestrator for direct lookup
        await orchestrator.searchWord(words[0]);
      }
      return;
    }

    // Handle AI query mode
    if (searchBar.isAIQuery && query) {
      try {
        const extractedCount = extractWordCount(query);
        const wordSuggestions = await orchestrator.getAISuggestions(query, extractedCount);

        if (wordSuggestions && wordSuggestions.suggestions.length > 0) {
          searchResults.wordSuggestions = wordSuggestions;
          ui.setMode('suggestions');
          // hasSearched is handled by orchestrator
          // aiQueryText removed - router handles query persistence
        } else {
          searchBar.triggerErrorAnimation();
          showError('No word suggestions found for this query');
        }
      } catch (error: any) {
        console.error('AI suggestion error:', error);
        searchBar.triggerErrorAnimation();
        showError(error.message || 'Failed to get word suggestions');
      }
      return;
    }

    // Regular search
    if (searchResults.searchResults.length > 0 && searchBar.searchSelectedIndex >= 0) {
      await selectResult(searchResults.searchResults[searchBar.searchSelectedIndex]);
    } else if (query) {
      const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
      router.push({ name: routeName, params: { word: query } });
      
      // Use orchestrator for direct lookup
      await orchestrator.searchWord(query);
    }
  };

  // Handle Shift+Enter for force refresh
  const handleShiftEnter = async () => {
    // Force refresh is handled by the orchestrator based on config
    await handleEnter();
  };

  // Handle Escape key
  const handleEscape = () => {
    if (searchBar.showSearchControls || searchBar.showSearchResults) {
      searchBar.hideControls();
      searchBar.hideDropdown();
    } else {
      searchBar.setFocused(false);
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
    if (searchBar.isSearchBarFocused && searchInputRef.value) {
      handleShiftEnter();
    }
  });

  whenever(cmdEnter, () => {
    if (searchBar.isSearchBarFocused && searchInputRef.value) {
      handleShiftEnter();
    }
  });

  whenever(ctrlEnter, () => {
    if (searchBar.isSearchBarFocused && searchInputRef.value) {
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