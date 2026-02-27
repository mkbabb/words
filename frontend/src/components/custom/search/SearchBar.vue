<template>
    <div
        ref="searchContainer"
        :class="[
            'search-container relative z-30 mx-auto w-full origin-top px-1 sm:px-0',
            props.className,
        ]"
        :style="containerStyle"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
        @mousedown="handleSearchAreaInteraction"
        @click="handleSearchAreaInteraction"
    >
        <!-- Main Layout -->
        <div class="pointer-events-auto relative overflow-visible pt-2 px-0 sm:px-2 pb-0">
            <!-- Search Bar -->
            <div
                ref="searchBarElement"
                :class="[
                    'search-bar relative flex items-center gap-2 overflow-visible px-1 sm:px-1 py-0.5',
                    'cartoon-shadow-sm rounded-2xl transition-all duration-500 ease-out',
                    searchBar.isAIQuery && !searchBar.hasErrorAnimation
                        ? 'border-2 border-amber-500 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-950/30 backdrop-blur-sm'
                        : searchBar.hasErrorAnimation
                        ? 'border-2 border-red-400/50 dark:border-red-600/50 bg-gradient-to-br from-red-50/20 to-red-50/10 dark:from-red-900/20 dark:to-red-900/10'
                        : 'border-2 border-border bg-background/20 backdrop-blur-3xl',
                    {
                        'cartoon-shadow-sm-hover': uiState.isContainerHovered,
                        'bg-background/30':
                            uiState.isContainerHovered && !searchBar.isAIQuery,
                        'shake-error': searchBar.hasErrorAnimation,
                    },
                ]"
                :style="{
                    height: searchBar.isAIQuery
                        ? 'auto'
                        : `${uiState.searchBarHeight}px`,
                    minHeight: searchBar.isAIQuery
                        ? `${uiState.searchBarHeight}px`
                        : undefined,
                    maxHeight: searchBar.isAIQuery
                        ? '420px'
                        : undefined,
                    overflowY: searchBar.isAIQuery
                        ? 'visible'
                        : 'visible',
                    borderColor: searchBar.isAIQuery && !searchBar.hasErrorAnimation
                        ? '#fbbf24'
                        : searchBar.hasErrorAnimation
                        ? '#f87171'
                        : undefined,
                }"
            >
                <!-- Border shimmer overlay in AI mode -->
                <BorderShimmer
                  v-if="searchBar.isAIQuery && !searchBar.hasErrorAnimation"
                  :active="true"
                  color="rgb(251 191 36)"
                  :thickness="3"
                  :border-width="2"
                  :duration="2400"
                />
                <!-- Sparkle Indicator -->
                <SparkleIndicator :show="searchBar.showSparkle" />

                <!-- Mode Toggle -->
                <ModeToggle
                    :model-value="searchBar.getSubMode('lookup') as any"
                    :can-toggle="canToggleMode"
                    :opacity="iconOpacity"
                    :ai-mode="searchBar.isAIQuery"
                    @update:model-value="(value: any) => searchBar.setSubMode('lookup', value)"
                />

                <!-- Search Input Container with Autocomplete -->
                <div class="relative max-w-none min-w-0 flex-1 flex-grow">
                    <!-- Autocomplete Overlay -->
                    <AutocompleteOverlay
                        :query="searchQuery"
                        :suggestion="searchBar.autocompleteText"
                        :padding-left="iconOpacity > 0.1 ? '1rem' : '1.5rem'"
                        :padding-right="
                            searchQuery.length > 0
                                ? '5rem'
                                : uiState.expandButtonVisible
                                ? '3rem'
                                : iconOpacity > 0.1
                                  ? '1rem'
                                  : '1.5rem'
                        "
                        :text-align="
                            iconOpacity < 0.3 && !searchBar.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                    />

                    <!-- Main Search Input -->
                    <SearchInput
                        ref="searchInputComponent"
                        v-model="searchQuery"
                        :placeholder="placeholder"
                        :ai-mode="searchBar.isAIQuery"
                        :text-align="
                            iconOpacity < 0.3 && !searchBar.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                        :style="{
                            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            paddingRight: searchQuery.length > 0 && searchBar.isAIQuery
                                ? '4.5rem'  // Both clear and expand buttons visible
                                : searchQuery.length > 0 || searchBar.isAIQuery
                                ? '3rem'    // Either clear or expand button visible
                                : iconOpacity > 0.1
                                  ? '1rem'
                                  : '1.5rem',
                            paddingTop: '0.75rem',
                            paddingBottom: '0.75rem',
                        }"
                        @enter="handleEnterWrapped"
                        @tab="acceptAutocomplete"
                        @space="handleSpaceKey"
                        @arrow-down="navigateResults(1)"
                        @arrow-up="navigateResults(-1)"
                        @arrow-left="handleArrowKey"
                        @arrow-right="handleArrowKey"
                        @escape="handleEscape"
                        @focus="handleFocus"
                        @blur="handleBlur"
                        @input-click="handleInputClick"
                    />

                    <!-- Button Container - positioned based on AI mode -->
                    <div :class="[
                        'absolute z-20 flex items-center gap-1',
                        searchBar.isAIQuery ? 'right-2 bottom-2' : 'right-2 top-1/2 -translate-y-1/2'
                    ]">
                        <!-- Expand Button -->
                        <Transition
                            enter-active-class="transition-all duration-200 ease-out"
                            leave-active-class="transition-all duration-200 ease-in"
                            enter-from-class="opacity-0 scale-90"
                            leave-to-class="opacity-0 scale-90"
                        >
                            <button
                                v-if="searchBar.isAIQuery && props.scrollProgress < 0.3"
                                :class="[
                                    'rounded-md p-1 transition-all duration-200',
                                    'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                    searchBar.isAIQuery
                                        ? 'bg-amber-100/80 hover:bg-amber-200/80 dark:bg-amber-900/40 dark:hover:bg-amber-800/40'
                                        : 'bg-muted/50 hover:bg-muted/80'
                                ]"
                                :style="{
                                    opacity: 1 - props.scrollProgress * 3,
                                    transform: `scale(${1 - props.scrollProgress * 0.5})`
                                }"
                                @click.stop="handleExpandClick"
                                title="Expand for longer input"
                            >
                                <Maximize2
                                    :class="[
                                        'h-4 w-4',
                                        searchBar.isAIQuery
                                            ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200'
                                            : 'text-foreground/70 hover:text-foreground'
                                    ]"
                                />
                            </button>
                        </Transition>

                        <!-- Clear Button -->
                        <Transition
                            enter-active-class="transition-all duration-200 ease-out"
                            leave-active-class="transition-all duration-200 ease-in"
                            enter-from-class="opacity-0 scale-90"
                            leave-to-class="opacity-0 scale-90"
                        >
                            <button
                                v-if="searchQuery.length > 0 && searchBar.isFocused"
                                @click.stop="clearQuery"
                                :class="[
                                    'rounded-md p-1 transition-all duration-200',
                                    'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                    searchBar.isAIQuery
                                        ? 'bg-transparent hover:bg-amber-100/80 dark:hover:bg-amber-900/40'
                                        : 'bg-transparent hover:bg-muted/80'
                                ]"
                                title="Clear search"
                            >
                                <X
                                    :class="[
                                        'h-4 w-4',
                                        searchBar.isAIQuery
                                            ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200'
                                            : 'text-foreground/50 hover:text-foreground/70'
                                    ]"
                                />
                            </button>
                        </Transition>
                    </div>
                </div>

                <!-- Hamburger Button -->
                <div
                    class="flex flex-shrink-0 items-center justify-center overflow-hidden transition-all duration-300 ease-out"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
                        width: iconOpacity > 0.1 ? '40px' : '0px',
                        marginLeft: iconOpacity > 0.1 ? '8px' : '0px',
                    }"
                >
                    <HamburgerIcon
                        :is-open="searchBar.showSearchControls"
                        :ai-mode="searchBar.isAIQuery"
                        @toggle="toggleControls"
                        @mousedown.prevent
                    />
                </div>
            </div>

            <!-- Thin Loading Progress Bar -->
            <ThinLoadingProgress
                :show="showProgressBar"
                :progress="loading.loadingProgress.value"
                :current-stage="loading.loadingStage.value"
                :mode="searchBar.searchMode"
                :category="loading.loadingCategory.value"
                @click="handleProgressBarClick"
            />

            <!-- Dropdowns Container -->
            <div class="absolute top-full right-0 left-0 z-40 pt-2">
                <!-- Controls Dropdown -->
                <SearchControls
                    :show="searchBar.showSearchControls"
                    v-model:selected-sources="selectedSources"
                    v-model:selected-languages="selectedLanguages"
                    v-model:no-a-i="noAI"
                    v-model:wordlist-filters="wordlistFilters"
                    :wordlist-sort-criteria="wordlistSortCriteria"
                    @update:wordlist-sort-criteria="(value: any) => wordlistSortCriteria = value"
                    :ai-suggestions="searchBar.aiSuggestions as string[]"
                    :is-development="uiState.isDevelopment"
                    :show-refresh-button="!!content.currentEntry && searchBar.searchMode === 'lookup'"
                    :force-refresh-mode="loading.forceRefreshMode.value"
                    @word-select="selectWord"
                    @clear-storage="clearAllStorage"
                    @interaction="handleSearchAreaInteraction"
                    @toggle-sidebar="ui.toggleSidebar()"
                    @toggle-refresh="handleForceRegenerate"
                    @execute-search="handleEnterWrapped"
                />

                <!-- Search Results Container -->
                <div
                    :style="resultsContainerStyle"
                    class="transition-all duration-350 ease-apple-spring"
                >
                    <SearchResults
                        ref="searchResultsComponent"
                        :show="searchBar.showDropdown"
                        :results="(searchBar.currentResults || []) as any[]"
                        :loading="loading.isSearching.value"
                        v-model:selected-index="searchSelectedIndex"
                        :query="searchQuery"
                        :ai-mode="searchBar.isAIQuery"
                        :wordlist-mode="searchBar.searchMode === 'wordlist'"
                        :wordlist-results="searchBar.getResults('wordlist') as any[] || []"
                        @select-result="selectResult"
                        @interaction="handleSearchAreaInteraction"
                    />
                </div>
            </div>
        </div>
    </div>

    <!-- Expanded Input Modal -->
    <ExpandModal
        :show="uiState.showExpandModal"
        :initial-query="searchQuery"
        @close="closeExpandModal"
        @submit="submitExpandedQuery"
    />

    <ConfirmDialog
        v-model:open="showClearStorageDialog"
        title="Clear All Storage"
        description="This will clear all local storage including history and settings."
        message="This action cannot be undone. You will lose all your saved settings and search history."
        confirm-text="Clear All"
        cancel-text="Cancel"
        :destructive="true"
        @confirm="confirmClearStorage"
    />
</template>

<script setup lang="ts">
import { ref, computed, watch, watchEffect, onMounted, onUnmounted } from 'vue';
// Modular stores - direct imports
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useContentStore } from '@/stores/content/content';
import { useUIStore } from '@/stores/ui/ui-state';
import { useLoadingStore } from '@/stores/ui/loading';
import { Maximize2, X } from 'lucide-vue-next';
import { HamburgerIcon } from '@/components/custom/icons';
import { BorderShimmer } from '@/components/custom/animation';

// Import components
import SearchInput from './components/SearchInput.vue';
import SparkleIndicator from './components/SparkleIndicator.vue';
import ModeToggle from './components/ModeToggle.vue';
import AutocompleteOverlay from './components/AutocompleteOverlay.vue';
import SearchControls from './components/SearchControls.vue';
import SearchResults from './components/SearchResults.vue';
import ExpandModal from './components/ExpandModal.vue';
import ThinLoadingProgress from './components/ThinLoadingProgress.vue';
import ConfirmDialog from '../ConfirmDialog.vue';

// Import composables
import {
    useSearchBarUI,
    useSearchBarNavigation,
    useFocusManagement,
    useModalManagement,
    useSearchBarScroll,
    useAutocomplete
} from './composables';

interface SearchBarProps {
    className?: string;
    hideDelay?: number;
    scrollThreshold?: number;
    scrollY?: number;
    shrinkPercentage?: number;
    scrollProgress?: number;
}

const props = withDefaults(defineProps<SearchBarProps>(), {
    hideDelay: 3000,
    scrollThreshold: 100,
    scrollY: 0,
    shrinkPercentage: 0,
    scrollProgress: 0,
});

const emit = defineEmits<{
    focus: [];
    blur: [];
    mouseenter: [];
    mouseleave: [];
    'stage-enter': [query: string];
}>();

// Store & State - Direct store access for single source of truth
const searchBar = useSearchBarStore();
const lookupMode = useLookupMode();
const wordlistMode = useWordlistMode();
const content = useContentStore();
const ui = useUIStore();
const loading = useLoadingStore();
const { iconOpacity, uiState } = useSearchBarUI();

// All functionality now uses modular stores directly - no reactive wrapper needed

// Computed properties from stores
const canToggleMode = computed(() => {
    // Disable mode toggle in wordlist mode
    if (searchBar.searchMode === 'wordlist') return false;
    
    const hasWordQuery = !!content.currentEntry;
    const hasSuggestionQuery = !!content.wordSuggestions;
    
    if (!hasWordQuery && !hasSuggestionQuery) return false;
    if (hasSuggestionQuery && !hasWordQuery) return false;
    return true;
});

const placeholder = computed(() => {
    // Hide placeholder when scrolled
    if (props.scrollProgress > 0.3) {
        return '';
    }
    
    // First check searchMode for specific modes
    if (searchBar.searchMode === 'wordlist') {
        return 'words';
    } else if (searchBar.searchMode === 'stage') {
        return 'staging';
    }

    // Default to mode-based placeholders for lookup mode
    return searchBar.getSubMode('lookup') === 'dictionary'
        ? 'definitions'
        : 'synonyms';
});

const resultsContainerStyle = computed(() => ({
    paddingTop: '0px',
    marginTop: searchBar.showSearchControls ? '0.5rem' : '0px',
    transition: 'all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275)',
}));

// Computed properties for v-model bindings
const searchQuery = computed({
    get: () => searchBar.searchQuery,
    set: (value: string) => searchBar.setQuery(value)
});

const searchSelectedIndex = computed({
    get: () => searchBar.searchSelectedIndex,
    set: (value: number) => searchBar.setSelectedIndex(value)
});


// Computed properties for v-model bindings with mode stores directly
const selectedSources = computed({
    get: () => Array.from(lookupMode.selectedSources) as string[],
    set: (value: string[]) => lookupMode.setSources(value as any)
});

const selectedLanguages = computed({
    get: () => Array.from(lookupMode.selectedLanguages) as string[],
    set: (value: string[]) => lookupMode.setLanguages(value as any)
});

const noAI = computed({
    get: () => lookupMode.noAI,
    set: (value: boolean) => lookupMode.setAI(!value)
});

// Computed properties for v-model bindings with wordlist mode store
const wordlistFilters = computed({
    get: () => ({ ...wordlistMode.wordlistFilters }),
    set: (value: any) => wordlistMode.setWordlistFilters(value)
});

const wordlistSortCriteria = computed({
    get: () => [...wordlistMode.wordlistSortCriteria],
    set: (value: any) => wordlistMode.setWordlistSortCriteria(value)
});

// Progress bar state - computed based on loading state
const isLoadingInProgress = computed(() => {
    return loading.isSearching.value || (loading.loadingProgress.value > 0 && loading.loadingProgress.value < 100);
});

// Dialog state
const showClearStorageDialog = ref(false);

const showProgressBar = computed(() => {
    // Show progress bar if loading is in progress and modal is not visible
    return isLoadingInProgress.value && !loading.showLoadingModal.value;
});

// Refs
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>(); void searchBarElement; // bound via template ref="searchBarElement"
const searchInputComponent = ref<any>();
const searchResultsComponent = ref<any>();

// Computed ref for search input element
const searchInputRef = computed(() => searchInputComponent.value?.element);

// Scroll animation setup - use props for scroll data
const { containerStyle } = useSearchBarScroll({
    shrinkPercentage: () => props.shrinkPercentage,
});

// Autocomplete setup
const {
    autocompleteText,
    updateAutocomplete,
    acceptAutocomplete,
    handleSpaceKey: handleAutocompleteSpaceKey,
    handleArrowKey: handleAutocompleteArrowKey,
    handleInputClick: handleAutocompleteInputClick,
} = useAutocomplete({
    query: computed(() => searchBar.searchQuery),
    searchResults: computed(() => {
        // Use appropriate results based on search mode
        if (searchBar.searchMode === 'wordlist') {
            return searchBar.getResults('wordlist')?.slice(0, 10) as any || [];
        }
        return searchBar.getResults('lookup') as any || [];
    }),
    searchInput: searchInputRef,
    onQueryUpdate: (newQuery: string) => {
        searchBar.setQuery(newQuery);
    },
});

// Search operations - use orchestrator
import { useSearchOrchestrator } from './composables/useSearchOrchestrator';
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery),
});
const { performSearch, clearSearch, cleanup: cleanupSearch } = orchestrator;

// Unified navigation and keyboard handling
const {
    navigateResults,
    handleEnter,
    handleEscape,
    selectResult,
    handleSpaceKey,
    handleArrowKey,
} = useSearchBarNavigation({
    searchInputRef,
    searchResultsComponent,
    onAutocompleteAccept: acceptAutocomplete,
    onAutocompleteSpace: handleAutocompleteSpaceKey,
    onAutocompleteArrow: handleAutocompleteArrowKey,
});

// Focus management
const {
    isInteractingWithSearchArea,
    handleFocus,
    handleBlur,
    handleSearchAreaInteraction,
    focusInput,
    cleanup: cleanupFocus,
} = useFocusManagement({
    searchInputComponent,
    emit: emit as (event: string, ...args: any[]) => void,
});

// Modal management
const {
    handleExpandClick,
    closeExpandModal,
    submitExpandedQuery: submitExpandedQueryBase,
} = useModalManagement();


// Event Handlers
const handleMouseEnter = () => {
    uiState.isContainerHovered = true;
    emit('mouseenter');
};

const handleMouseLeave = () => {
    uiState.isContainerHovered = false;
    emit('mouseleave');
};

const handleInputClick = (event: MouseEvent) => {
    handleSearchAreaInteraction();
    handleAutocompleteInputClick(event);
};

// Override handleEnter to handle stage mode
const handleEnterWrapped = async () => {
    if (searchBar.searchMode === 'stage' && searchBar.searchQuery) {
        emit('stage-enter', searchBar.searchQuery);
        return;
    }
    await handleEnter();
};

const toggleControls = () => {
    console.log('🍔 Hamburger toggleControls called');
    console.log('🍔 Current showControls:', searchBar.showSearchControls);
    searchBar.toggleSearchControls();
    console.log('🍔 After toggle showControls:', searchBar.showSearchControls);
};


const selectWord = async (word: string) => {
    searchBar.setDirectLookup(true);
    try {
        const subMode = searchBar.getSubMode('lookup');
        if (subMode === 'thesaurus') {
            await orchestrator.getThesaurusData(word);
        } else {
            await orchestrator.getDefinition(word);
        }
    } finally {
        searchBar.setDirectLookup(false);
    }
};

const handleForceRegenerate = () => {
    handleSearchAreaInteraction();
    loading.setForceRefreshMode(!loading.forceRefreshMode.value);
};

const handleProgressBarClick = () => {
    // Reshow the loading progress modal when clicking the thin progress bar
    loading.setShowLoadingModal(true);
};

const clearQuery = () => {
    clearSearch();
    focusInput();
};

const clearAllStorage = () => {
    showClearStorageDialog.value = true;
};

const confirmClearStorage = () => {
    localStorage.clear();
    sessionStorage.clear();
    showClearStorageDialog.value = false;
    window.location.reload();
};

// Expand modal wrapper
const submitExpandedQuery = (query: string) => {
    searchBar.setQuery(query);
    submitExpandedQueryBase(query, handleEnterWrapped);
};

// Modal state is now handled directly by useModalManagement composable
// No watchers needed - single source of truth

// Autocomplete updates are now handled by the useAutocomplete composable
// which already watches query and results internally

// Scroll state updates are handled by useSearchBarScroll composable
// which already computes based on props

// Reset selected index when results change
watchEffect(() => {
    const results = searchBar.currentResults || [];
    
    // Reset selected index if out of bounds
    const maxResults = searchBar.searchMode === 'wordlist' ? Math.min(10, results.length) : results.length;
    if (searchBar.searchSelectedIndex >= maxResults) {
        searchBar.setSelectedIndex(0);
    }
});

// Click outside handler
const handleClickOutside = (event: MouseEvent) => {
    if (!searchContainer.value) return;
    
    const target = event.target as HTMLElement;
    
    // If click is outside the search container, handle blur behavior
    if (!searchContainer.value.contains(target)) {
        // Close controls
        searchBar.hideControls();
        
        // Trigger blur behavior if search bar is focused
        if (searchBar.isFocused) {
            // Don't set interaction flag since this is an outside click
            isInteractingWithSearchArea.value = false;
            
            // Immediately trigger blur
            searchBar.setFocused(false);
            emit('blur');
            
            // Hide search results
            searchBar.hideDropdown();
            searchBar.clearResults();
        }
    }
};

// Initialize
onMounted(async () => {
    document.addEventListener('click', handleClickOutside);
    
    // Watch query changes for immediate search - NO DEBOUNCING
    watch(
        () => searchBar.searchQuery,
        () => {
            // Trigger search immediately for all modes
            performSearch();
            
            // Update autocomplete
            updateAutocomplete();
            searchBar.setAutocompleteText(autocompleteText.value);
        }
    );

    // Watch search results for autocomplete updates
    watch(
        () => searchBar.getResults('lookup'),
        () => {
            updateAutocomplete();
            searchBar.setAutocompleteText(autocompleteText.value);
        }
    );


    // Watch for AI mode changes from store
    // AI mode is now non-persisted and dynamically determined by query
    
    // Note: isAIQuery and showSparkle are computed properties from search bar store
    // They are automatically reactive and don't need manual assignment

    // Let search operations handle dropdown visibility directly
    // Only hide dropdown when focus is lost or query is empty
    watchEffect(() => {
        const focused = searchBar.isFocused;
        const query = searchBar.searchQuery;
        
        // Only hide dropdown for specific conditions, let search operations show it
        // Don't hide for AI mode - let it show AI suggestions
        if (!focused || !query || query.length === 0) {
            if (searchBar.showDropdown) {
                console.log('🔍 Hiding dropdown - no focus/query');
                searchBar.hideDropdown();
            }
        }
    });

    // AI mode detection is now handled in the lookup store itself

    // Initialize AI suggestions using the store action
    searchBar.setAISuggestions([]);
});

// Cleanup
onUnmounted(() => {
    cleanupSearch();
    cleanupFocus();
    document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* Disable animations for reduced motion */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
