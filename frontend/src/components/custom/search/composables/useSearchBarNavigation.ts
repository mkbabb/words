import { Ref, nextTick, computed } from 'vue';
import { useMagicKeys, whenever } from '@vueuse/core';
import { useRouter } from 'vue-router';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useContentStore } from '@/stores/content/content';
import { useHistoryStore } from '@/stores/content/history';
import { useSearchOrchestrator } from './useSearchOrchestrator';
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
  const searchBar = useSearchBarStore();
  const contentStore = useContentStore();
  const router = useRouter();
  const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery),
  });
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
    if (searchBar.searchMode === 'wordlist') {
      const wordlistResults = searchBar.getResults('wordlist');
      return wordlistResults ? wordlistResults.slice(0, 10) : [];
    } else {
      const lookupResults = searchBar.getResults('lookup');
      return lookupResults || [];
    }
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
        searchBar.clearResults();
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
        const lookupSubMode = searchBar.getSubMode('lookup');
        const routeName = lookupSubMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
        router.push({ name: routeName, params: { word: result.word } });
        searchBar.setDirectLookup(true);
        try {
          if (lookupSubMode === 'thesaurus') {
            // Fetch thesaurus data
            const thesaurusData = await orchestrator.getThesaurusData(result.word);
            contentStore.setCurrentThesaurus(thesaurusData);
          } else {
            // Fetch definition data
            const definition = await orchestrator.getDefinition(result.word);
            contentStore.setCurrentEntry(definition);
          }
        } finally {
          searchBar.setDirectLookup(false);
        }
      },
      
      handleEnter: async () => {
        const query = searchBar.searchQuery;
        
        // Handle AI query mode
        if (searchBar.isAIQuery && query) {
          try {
            const extractedCount = extractWordCount(query);
            // Use orchestrator to get AI suggestions
            const wordSuggestions = await orchestrator.getAISuggestions(query, extractedCount);

            if (wordSuggestions?.suggestions?.length > 0) {
              contentStore.setWordSuggestions(wordSuggestions);
              searchBar.setMode('lookup');
              searchBar.setSubMode('lookup', 'suggestions');
              // Add to AI query history
              const historyStore = useHistoryStore();
              historyStore.addToAIQueryHistory(query);
              // Navigate to home to display suggestions
              router.push({ name: 'Home' });
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
          await modeHandlers.lookup.selectResult(results[selectedIndex] as SearchResult);
          return;
        }

        // Direct word lookup
        if (query) {
          const lookupSubMode = searchBar.getSubMode('lookup');
          const routeName = lookupSubMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
          router.push({ name: routeName, params: { word: query } });
          searchBar.setDirectLookup(true);
          try {
            if (lookupSubMode === 'thesaurus') {
              // Fetch thesaurus data
              const thesaurusData = await orchestrator.getThesaurusData(query);
              contentStore.setCurrentThesaurus(thesaurusData);
            } else {
              // Fetch definition data
              const definition = await orchestrator.getDefinition(query);
              contentStore.setCurrentEntry(definition);
            }
          } finally {
            searchBar.setDirectLookup(false);
          }
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
    const handler = modeHandlers[searchBar.searchMode as keyof typeof modeHandlers];
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
    const handler = modeHandlers[searchBar.searchMode as keyof typeof modeHandlers];
    if (handler?.handleEnter) {
      return await handler.handleEnter();
    }
  };

  /**
   * Handle Escape key
   */
  const handleEscape = () => {
    if (searchBar.showSearchControls || searchBar.showDropdown) {
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
        if (searchBar.isFocused && searchInputRef.value) {
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