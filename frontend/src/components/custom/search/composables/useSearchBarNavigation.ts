import { Ref, nextTick } from 'vue';
import { useMagicKeys, whenever } from '@vueuse/core';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { showError } from '@/plugins/toast';
import { extractWordCount } from '../utils/ai-query';
import type { SearchResult } from '@/types';

interface UseSearchBarNavigationOptions {
  searchInputRef: any;
  searchResultsComponent: Ref<any>;
  onAutocompleteAccept: () => Promise<boolean>;
  onAutocompleteSpace: (event: KeyboardEvent) => void;
  onAutocompleteArrow: (event: KeyboardEvent) => void;
}

/**
 * Unified navigation composable for SearchBar
 * Handles keyboard interactions, result navigation, and mode-specific behaviors
 */
export function useSearchBarNavigation(options: UseSearchBarNavigationOptions) {
  const { searchResults, orchestrator, searchBar, searchConfig, ui } = useStores();
  const router = useRouter();
  const { 
    searchInputRef, 
    searchResultsComponent,
    onAutocompleteAccept, 
    onAutocompleteSpace, 
    onAutocompleteArrow 
  } = options;

  /**
   * Get current results based on search mode
   */
  const getCurrentResults = () => {
    return searchConfig.searchMode === 'wordlist' 
      ? searchResults.getSearchResults('wordlist').slice(0, 10)
      : searchResults.getSearchResults('lookup');
  };

  /**
   * Navigate through results with keyboard
   */
  const navigateResults = (direction: number) => {
    const results = getCurrentResults();
    if (results.length === 0) return;

    const currentIndex = searchBar.searchSelectedIndex;
    const newIndex = Math.max(0, Math.min(results.length - 1, currentIndex + direction));
    
    searchBar.setSelectedIndex(newIndex);
    scrollToSelectedResult();
  };

  /**
   * Scroll selected result into view
   */
  const scrollToSelectedResult = () => {
    nextTick(() => {
      const container = searchResultsComponent.value?.container;
      const selectedElement = searchResultsComponent.value?.resultRefs?.[searchBar.searchSelectedIndex];
      
      if (!container || !selectedElement) return;
      
      const containerRect = container.getBoundingClientRect();
      const elementRect = selectedElement.getBoundingClientRect();
      
      const isAbove = elementRect.top < containerRect.top;
      const isBelow = elementRect.bottom > containerRect.bottom;
      
      if (isAbove || isBelow) {
        const elementTop = selectedElement.offsetTop;
        const elementHeight = selectedElement.offsetHeight;
        const containerHeight = container.offsetHeight;
        
        container.scrollTo({
          top: isAbove ? elementTop : elementTop + elementHeight - containerHeight,
          behavior: 'smooth'
        });
      }
    });
  };

  /**
   * Mode-specific handlers for different actions
   */
  const modeHandlers = {
    // Wordlist mode handlers
    wordlist: {
      selectResult: async (result: SearchResult) => {
        console.log('Selected wordlist item:', result.word);
        searchBar.setQuery('');
        searchBar.hideDropdown();
        searchResults.clearSearchResults('wordlist');
        // TODO: Emit event to scroll to word in list
      },
      
      handleEnter: async () => {
        console.log('Enter in wordlist mode - no action');
        // WordListView handles filtering
      }
    },

    // Lookup mode handlers
    lookup: {
      selectResult: async (result: SearchResult) => {
        const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
        router.push({ name: routeName, params: { word: result.word } });
        await orchestrator.searchWord(result.word);
      },
      
      handleEnter: async () => {
        const query = searchBar.searchQuery;
        
        // Handle AI query mode
        if (searchBar.isAIQuery && query) {
          try {
            const extractedCount = extractWordCount(query);
            const wordSuggestions = await orchestrator.getAISuggestions(query, extractedCount);

            if (wordSuggestions?.suggestions && wordSuggestions.suggestions.length > 0) {
              searchConfig.setMode('lookup');
              searchConfig.setLookupMode('suggestions');
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

        // Handle selected result
        const results = getCurrentResults();
        const selectedIndex = searchBar.searchSelectedIndex;
        
        if (selectedIndex >= 0 && selectedIndex < results.length) {
          await modeHandlers.lookup.selectResult(results[selectedIndex]);
          return;
        }

        // Direct word lookup
        if (query) {
          const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
          router.push({ name: routeName, params: { word: query } });
          await orchestrator.searchWord(query);
        }
      }
    },

    // Stage mode handlers
    stage: {
      selectResult: async () => {
        // Stage mode doesn't use search results
      },
      
      handleEnter: async () => {
        const query = searchBar.searchQuery;
        if (query) {
          return { type: 'stage-enter', query };
        }
      }
    }
  };

  /**
   * Select a search result based on current mode
   */
  const selectResult = async (result: SearchResult) => {
    const handler = modeHandlers[searchConfig.searchMode as keyof typeof modeHandlers];
    if (handler?.selectResult) {
      await handler.selectResult(result);
    }
  };

  /**
   * Handle Enter key press based on current mode
   */
  const handleEnter = async () => {
    // Try autocomplete first
    if (searchBar.autocompleteText) {
      const accepted = await onAutocompleteAccept();
      if (accepted) return;
    }

    const query = searchBar.searchQuery;
    
    // Unfocus on empty query
    if (!query?.trim()) {
      searchBar.setFocused(false);
      return;
    }

    // Execute mode-specific handler
    const handler = modeHandlers[searchConfig.searchMode as keyof typeof modeHandlers];
    if (handler?.handleEnter) {
      return await handler.handleEnter();
    }
  };

  /**
   * Handle Escape key
   */
  const handleEscape = () => {
    if (searchBar.showSearchControls || searchBar.showSearchResults) {
      searchBar.hideControls();
      searchBar.hideDropdown();
    } else {
      searchBar.setFocused(false);
    }
  };

  /**
   * Setup keyboard shortcuts
   */
  const setupKeyboardShortcuts = () => {
    const keys = useMagicKeys();
    const shortcuts = ['Shift+Enter', 'Cmd+Enter', 'Ctrl+Enter'];
    
    shortcuts.forEach(shortcut => {
      whenever(keys[shortcut], () => {
        if (searchBar.isSearchBarFocused && searchInputRef.value) {
          handleEnter(); // Force refresh handled by orchestrator config
        }
      });
    });
  };

  // Initialize shortcuts
  setupKeyboardShortcuts();

  return {
    // State
    getCurrentResults,
    
    // Navigation
    navigateResults,
    scrollToSelectedResult,
    
    // Actions
    selectResult,
    handleEnter,
    handleEscape,
    handleSpaceKey: onAutocompleteSpace,
    handleArrowKey: onAutocompleteArrow,
    
    // Utils
    resetSelection: () => searchBar.resetSelection(),
  };
}