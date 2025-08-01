import { reactive, computed } from 'vue';
import { useStores } from '@/stores';
import { useSearchBarUI } from './useSearchBarUI';

/**
 * Modern reactive state bridge for SearchBar
 * Provides clean interface to modular stores
 */
export function useSearchState() {
  const { searchBar, searchConfig, searchResults, ui, loading } = useStores();
  const { uiState } = useSearchBarUI();

  // Reactive state binding to modular stores
  const state = reactive({
    // Search bar store bindings
    get query() { return searchBar.searchQuery; },
    set query(value) { searchBar.setQuery(value); },
    get showResults() { return searchBar.showSearchResults; },
    set showResults(value) { value ? searchBar.showDropdown() : searchBar.hideDropdown(); },
    get isFocused() { return searchBar.isSearchBarFocused; },
    set isFocused(value) { searchBar.setFocused(value); },
    get isAIQuery() { return searchBar.isAIQuery; },
    get showSparkle() { return searchBar.showSparkle; },
    get showErrorAnimation() { return searchBar.showErrorAnimation; },
    set showErrorAnimation(_) { searchBar.triggerErrorAnimation(); },
    get selectedIndex() { return searchBar.searchSelectedIndex; },
    set selectedIndex(value) { searchBar.setSelectedIndex(value); },
    get showControls() { return searchBar.showSearchControls; },
    set showControls(value) { value ? searchBar.toggleControls() : searchBar.hideControls(); },
    get autocompleteText() { return searchBar.autocompleteText; },
    set autocompleteText(value) { searchBar.setAutocomplete(value); },
    get aiSuggestions() { return searchBar.aiSuggestions; },
    set aiSuggestions(value) { searchBar.setAISuggestions([...value]); },

    // Search results store bindings
    get searchResults() { return [...searchResults.searchResults]; },
    get isSearching() { return loading.isSearching; },
    get forceRefreshMode() { return loading.forceRefreshMode; },
    set forceRefreshMode(value) { value ? loading.enableForceRefresh() : loading.disableForceRefresh(); },

    // Search config store bindings  
    get mode() { return ui.mode; },
    set mode(value) { ui.setMode(value); },
    get searchMode() { return searchConfig.searchMode; },
    set searchMode(value) { searchConfig.setSearchModeLegacy(value); },
    get selectedSources() { return [...searchConfig.selectedSources]; },
    set selectedSources(value) { searchConfig.setSources([...value]); },
    get selectedLanguages() { return [...searchConfig.selectedLanguages]; },
    set selectedLanguages(value) { searchConfig.setLanguages([...value]); },
    get noAI() { return searchConfig.noAI; },
    set noAI(value) { searchConfig.setAI(!value); },

    // Search results bindings - AI suggestions removed as they don't exist in this store
    get wordlistFilters() { return ui.wordlistFilters; },
    set wordlistFilters(value) { ui.setWordlistFilters(value); },
    get wordlistChunking() { return ui.wordlistChunking; },
    set wordlistChunking(value) { ui.setWordlistChunking(value); },
    get wordlistSortCriteria() { return [...ui.wordlistSortCriteria]; },
    set wordlistSortCriteria(value) { ui.setWordlistSortCriteria([...value]); },
    
    // UI state (local)
    get isContainerHovered() { return uiState.isContainerHovered; },
    set isContainerHovered(value) { uiState.isContainerHovered = value; },
    get showExpandModal() { return uiState.showExpandModal; },
    set showExpandModal(value) { uiState.showExpandModal = value; },
    get scrollProgress() { return uiState.scrollProgress; },
    set scrollProgress(value) { uiState.scrollProgress = value; },
    get searchBarHeight() { return uiState.searchBarHeight; },
    set searchBarHeight(value) { uiState.searchBarHeight = value; },
    get expandButtonVisible() { return uiState.expandButtonVisible; },
    set expandButtonVisible(value) { uiState.expandButtonVisible = value; },
    get isDevelopment() { return uiState.isDevelopment; },
  });

  // Computed properties
  const canToggleMode = computed(() => {
    const hasWordQuery = !!searchResults.currentEntry;
    const hasSuggestionQuery = !!searchResults.wordSuggestions;
    
    if (!hasWordQuery && !hasSuggestionQuery) return false;
    if (hasSuggestionQuery && !hasWordQuery) return false;
    return true;
  });

  const placeholder = computed(() => {
    // Hide placeholder when scrolled
    if (state.scrollProgress > 0.3) {
      return '';
    }
    
    // First check searchMode for specific modes
    if (state.searchMode === 'wordlist') {
      return 'words';
    } else if (state.searchMode === 'stage') {
      return 'staging';
    }

    // Default to mode-based placeholders for lookup mode
    return state.mode === 'dictionary'
      ? 'definitions'
      : 'synonyms';
  });

  const resultsContainerStyle = computed(() => ({
    paddingTop: '0px',
    marginTop: state.showControls ? '0.5rem' : '0px',
    transition: 'all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  }));

  return {
    state,
    canToggleMode,
    placeholder,
    resultsContainerStyle,
  };
}