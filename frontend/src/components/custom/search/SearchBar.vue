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
                    state.isAIQuery && !state.showErrorAnimation
                        ? 'border-2 border-amber-500 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-950/30 backdrop-blur-sm'
                        : state.showErrorAnimation
                        ? 'border-2 border-red-400/50 dark:border-red-600/50 bg-gradient-to-br from-red-50/20 to-red-50/10 dark:from-red-900/20 dark:to-red-900/10'
                        : 'border-2 border-border bg-background/20 backdrop-blur-3xl',
                    {
                        'cartoon-shadow-sm-hover': state.isContainerHovered,
                        'bg-background/30':
                            state.isContainerHovered && !state.isAIQuery,
                        'shake-error': state.showErrorAnimation,
                    },
                ]"
                :style="{
                    height: state.isAIQuery
                        ? 'auto'
                        : `${state.searchBarHeight}px`,
                    minHeight: state.isAIQuery
                        ? `${state.searchBarHeight}px`
                        : undefined,
                    maxHeight: state.isAIQuery
                        ? '420px'
                        : undefined,
                    overflowY: state.isAIQuery
                        ? 'visible'
                        : 'visible',
                    borderColor: state.isAIQuery && !state.showErrorAnimation
                        ? '#fbbf24'
                        : state.showErrorAnimation
                        ? '#f87171'
                        : undefined,
                }"
            >
                <!-- Sparkle Indicator -->
                <SparkleIndicator :show="state.showSparkle" />

                <!-- Mode Toggle -->
                <ModeToggle
                    v-model="state.mode"
                    :can-toggle="canToggleMode"
                    :opacity="iconOpacity"
                    :ai-mode="state.isAIQuery"
                />

                <!-- Search Input Container with Autocomplete -->
                <div class="relative max-w-none min-w-0 flex-1 flex-grow">
                    <!-- Autocomplete Overlay -->
                    <AutocompleteOverlay
                        :query="state.query"
                        :suggestion="state.autocompleteText"
                        :padding-left="iconOpacity > 0.1 ? '1rem' : '1.5rem'"
                        :padding-right="
                            state.query.length > 0
                                ? '5rem'
                                : state.expandButtonVisible
                                ? '3rem'
                                : iconOpacity > 0.1
                                  ? '1rem'
                                  : '1.5rem'
                        "
                        :text-align="
                            iconOpacity < 0.3 && !state.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                    />

                    <!-- Main Search Input -->
                    <SearchInput
                        ref="searchInputComponent"
                        v-model="state.query"
                        :placeholder="placeholder"
                        :ai-mode="state.isAIQuery"
                        :text-align="
                            iconOpacity < 0.3 && !state.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                        :style="{
                            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            paddingRight: state.query.length > 0 && state.isAIQuery
                                ? '4.5rem'  // Both clear and expand buttons visible
                                : state.query.length > 0 || state.isAIQuery
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

                    <!-- Button Container - positioned in bottom right -->
                    <div class="absolute right-2 bottom-2 z-20 flex items-center gap-1">
                        <!-- Expand Button -->
                        <Transition
                            enter-active-class="transition-all duration-200 ease-out"
                            leave-active-class="transition-all duration-200 ease-in"
                            enter-from-class="opacity-0 scale-90"
                            leave-to-class="opacity-0 scale-90"
                        >
                            <button
                                v-if="state.isAIQuery && state.scrollProgress < 0.3"
                                :class="[
                                    'rounded-md p-1 transition-all duration-200',
                                    'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                    state.isAIQuery
                                        ? 'bg-amber-100/80 hover:bg-amber-200/80 dark:bg-amber-900/40 dark:hover:bg-amber-800/40'
                                        : 'bg-muted/50 hover:bg-muted/80'
                                ]"
                                :style="{
                                    opacity: 1 - state.scrollProgress * 3,
                                    transform: `scale(${1 - state.scrollProgress * 0.5})`
                                }"
                                @click.stop="handleExpandClick"
                                title="Expand for longer input"
                            >
                                <Maximize2
                                    :class="[
                                        'h-4 w-4',
                                        state.isAIQuery
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
                                v-if="state.query.length > 0 && state.isFocused"
                                @click.stop="clearQuery"
                                :class="[
                                    'rounded-md p-1 transition-all duration-200',
                                    'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                    state.isAIQuery
                                        ? 'bg-transparent hover:bg-amber-100/80 dark:hover:bg-amber-900/40'
                                        : 'bg-transparent hover:bg-muted/80'
                                ]"
                                title="Clear search"
                            >
                                <X
                                    :class="[
                                        'h-4 w-4',
                                        state.isAIQuery
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
                        :is-open="state.showControls"
                        :ai-mode="state.isAIQuery"
                        @toggle="toggleControls"
                        @mousedown.prevent
                    />
                </div>
            </div>

            <!-- Thin Loading Progress Bar -->
            <ThinLoadingProgress
                :show="showProgressBar"
                :progress="loading.loadingProgress"
                :current-stage="loading.loadingStage"
                :mode="state.searchMode"
                :category="loading.loadingCategory"
                @click="handleProgressBarClick"
            />

            <!-- Dropdowns Container -->
            <div class="absolute top-full right-0 left-0 z-40 pt-2">
                <!-- Controls Dropdown -->
                <SearchControls
                    :show="state.showControls"
                    v-model:search-mode="state.searchMode"
                    v-model:selected-sources="state.selectedSources"
                    v-model:selected-languages="state.selectedLanguages"
                    v-model:no-a-i="state.noAI"
                    v-model:wordlist-filters="state.wordlistFilters"
                    v-model:wordlist-chunking="state.wordlistChunking"
                    v-model:wordlist-sort-criteria="state.wordlistSortCriteria"
                    :ai-suggestions="state.aiSuggestions"
                    :is-development="state.isDevelopment"
                    :show-refresh-button="!!searchResults.currentEntry && state.searchMode === 'lookup'"
                    :force-refresh-mode="state.forceRefreshMode"
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
                        :show="state.showResults"
                        :results="state.searchResults"
                        :loading="state.isSearching"
                        v-model:selected-index="state.selectedIndex"
                        :query="state.query"
                        :ai-mode="state.isAIQuery"
                        @select-result="selectResult"
                        @interaction="handleSearchAreaInteraction"
                    />
                </div>
            </div>
        </div>
    </div>

    <!-- Expanded Input Modal -->
    <ExpandModal
        :show="state.showExpandModal"
        :initial-query="state.query"
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
// Legacy store removed - all functionality migrated to modular stores
import { useStores } from '@/stores';
import { Maximize2, X } from 'lucide-vue-next';
import { HamburgerIcon } from '@/components/custom/icons';

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
    useSearchState,
    useSearchOperations,
    useSearchNavigation,
    useFocusManagement,
    useModalManagement,
    useSearchBarKeyboard,
    useScrollAnimationSimple,
    useAutocomplete
} from './composables';
import { shouldTriggerAIMode } from './utils/ai-query';

interface SearchBarProps {
    className?: string;
    shrinkPercentage?: number;
    hideDelay?: number;
    scrollThreshold?: number;
}

const props = withDefaults(defineProps<SearchBarProps>(), {
    shrinkPercentage: 0,
    hideDelay: 3000,
    scrollThreshold: 100,
});

const emit = defineEmits<{
    focus: [];
    blur: [];
    mouseenter: [];
    mouseleave: [];
    'stage-enter': [query: string];
}>();

// Store & State
const { searchBar, searchConfig, searchResults, ui, loading, orchestrator } = useStores();
const { iconOpacity } = useSearchBarUI();

// All functionality now uses modular stores - no legacy store needed

// Use centralized state management
const { state, canToggleMode, placeholder, resultsContainerStyle } = useSearchState();

// Progress bar state - track separately to persist after modal dismiss
const isLoadingInProgress = ref(false);

// Dialog state
const showClearStorageDialog = ref(false);

// Start showing progress when search starts
watch(() => loading.isSearching, (newVal) => {
    if (newVal) {
        isLoadingInProgress.value = true;
    }
});

// Hide progress when loading completes
watch(() => loading.isSearching, (searching) => {
    if (!searching) {
        setTimeout(() => isLoadingInProgress.value = false, 500);
    }
});

// Watch loading progress from modular stores
watch(() => [loading.loadingProgress, loading.isSearching], ([progress, searching]) => {
    // Only hide if we're at 100% AND not searching anymore
    if (typeof progress === 'number' && progress >= 100 && !searching) {
        // Delay hiding to show completion
        setTimeout(() => {
            isLoadingInProgress.value = false;
        }, 1000);
    }
    // Reset immediately if progress goes to 0 and we're not searching
    else if (progress === 0 && !searching) {
        isLoadingInProgress.value = false;
    }
});

const showProgressBar = computed(() => {
    // Show progress bar if loading is in progress and modal is not visible
    return isLoadingInProgress.value && !loading.showLoadingModal;
});

// Refs
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();
const searchInputComponent = ref<any>();
const searchResultsComponent = ref<any>();

// Computed ref for search input element
const searchInputRef = computed(() => searchInputComponent.value?.element);

// Scroll animation setup
const { containerStyle, updateScrollState } = useScrollAnimationSimple(
    computed(() => state.scrollProgress),
    computed(() => state.isContainerHovered),
    computed(() => state.isFocused),
    computed(() => state.showControls || state.showResults)
);

// Update scroll progress from prop
watch(
    () => props.shrinkPercentage,
    (newValue) => {
        state.scrollProgress = newValue;
    },
    { immediate: true }
);

// Autocomplete setup
const {
    autocompleteText,
    updateAutocomplete,
    acceptAutocomplete,
    handleSpaceKey: handleAutocompleteSpaceKey,
    handleArrowKey: handleAutocompleteArrowKey,
    handleInputClick: handleAutocompleteInputClick,
} = useAutocomplete({
    query: computed(() => state.query),
    searchResults: computed(() => state.searchResults),
    searchInput: searchInputRef,
    onQueryUpdate: (newQuery: string) => {
        state.query = newQuery;
    },
});

// Search operations
const { performSearch, clearSearch, cleanup: cleanupSearch } = useSearchOperations({
    query: computed(() => state.query),
});

// Navigation setup
const { navigateResults, resetSelection } = useSearchNavigation({
    searchResultsComponent,
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
    showExpandModal,
    handleExpandClick,
    closeExpandModal,
    submitExpandedQuery: submitExpandedQueryBase,
} = useModalManagement();

// Keyboard handling
const {
    handleEnter,
    handleEscape,
    selectResult,
} = useSearchBarKeyboard({
    searchInputRef,
    onAutocompleteAccept: acceptAutocomplete,
    onAutocompleteSpace: handleAutocompleteSpaceKey,
    onAutocompleteArrow: handleAutocompleteArrowKey,
});

// Event Handlers
const handleMouseEnter = () => {
    state.isContainerHovered = true;
    emit('mouseenter');
};

const handleMouseLeave = () => {
    state.isContainerHovered = false;
    emit('mouseleave');
};

const handleInputClick = (event: MouseEvent) => {
    handleSearchAreaInteraction();
    handleAutocompleteInputClick(event);
};

// Override handleEnter to handle stage mode
const handleEnterWrapped = async () => {
    if (state.searchMode === 'stage' && state.query) {
        searchBar.setQuery(state.query);
        emit('stage-enter', state.query);
        return;
    }
    await handleEnter();
};

const toggleControls = () => {
    state.showControls = !state.showControls;
};

const handleSpaceKey = (event: KeyboardEvent) => {
    handleAutocompleteSpaceKey(event);
};

const handleArrowKey = (event: KeyboardEvent) => {
    handleAutocompleteArrowKey(event);
};

const selectWord = async (word: string) => {
    await orchestrator.searchWord(word);
};

const handleForceRegenerate = () => {
    handleSearchAreaInteraction();
    state.forceRefreshMode = !state.forceRefreshMode;
};

const handleProgressBarClick = () => {
    // Reshow the loading progress modal when clicking the thin progress bar
    loading.showModal();
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
    state.query = query;
    submitExpandedQueryBase(query, handleEnterWrapped);
};

// Sync modal state
watch(() => showExpandModal.value, (newVal) => {
    state.showExpandModal = newVal;
});

watch(() => state.showExpandModal, (newVal) => {
    if (newVal !== showExpandModal.value) {
        showExpandModal.value = newVal;
    }
});

// Watch query for autocomplete
watch(
    () => state.query,
    () => {
        updateAutocomplete();
        state.autocompleteText = autocompleteText.value;
    }
);

// Watch search results for autocomplete
watch(
    () => state.searchResults,
    () => {
        resetSelection();
        updateAutocomplete();
        state.autocompleteText = autocompleteText.value;
    }
);

// Update scroll state
watch(
    () => props,
    () => {
        updateScrollState();
    },
    { deep: true }
);

// Click outside handler
const handleClickOutside = (event: MouseEvent) => {
    if (!searchContainer.value) return;
    
    const target = event.target as HTMLElement;
    
    // If click is outside the search container, handle blur behavior
    if (!searchContainer.value.contains(target)) {
        // Close controls
        state.showControls = false;
        
        // Trigger blur behavior if search bar is focused
        if (state.isFocused) {
            // Don't set interaction flag since this is an outside click
            isInteractingWithSearchArea.value = false;
            
            // Immediately trigger blur
            searchBar.setFocused(false);
            emit('blur');
            
            // Hide search results
            searchBar.hideDropdown();
            searchResults.clearSearchResults();
        }
    }
};

// Initialize
onMounted(async () => {
    document.addEventListener('click', handleClickOutside);
    
    // Watch query changes to trigger search
    watch(
        () => state.query,
        () => {
            performSearch();
        }
    );
    
    // Watch store searchQuery changes to sync with local state
    watch(
        () => searchBar.searchQuery,
        (newQuery) => {
            if (newQuery !== state.query) {
                state.query = newQuery;
            }
        }
    );
    
    // Watch local query changes to save to store as user types
    watch(
        () => state.query,
        (newQuery) => {
            if (newQuery !== searchBar.searchQuery) {
                searchBar.setQuery(newQuery);
            }
        }
    );

    // Watch for AI mode changes from store
    // AI mode is now non-persisted and dynamically determined by query
    
    // Note: isAIQuery and showSparkle are computed properties from useAIMode composable
    // They are automatically reactive and don't need manual assignment

    // Show results when focused with query (but not during direct lookups)
    watch(
        [() => state.isFocused, () => state.query, () => state.isAIQuery, () => state.searchResults, () => searchBar.isDirectLookup],
        ([focused, query, isAI, results, isDirectLookup]) => {
            console.log('🔍 SEARCHBAR WATCHER - focus/query/results changed', {
                focused,
                query,
                queryLength: query?.length || 0,
                isAI,
                resultsLength: results?.length || 0,
                isDirectLookup,
                // isSwitchingModes: store.isSwitchingModes
            });
            
            if (focused && query && query.length > 0 && !isAI && results && results.length > 0 && !isDirectLookup) {
                console.log('🔍 SEARCHBAR WATCHER - SHOWING SEARCH RESULTS');
                state.showResults = true;
            } else if (isAI || isDirectLookup) {
                console.log('🔍 SEARCHBAR WATCHER - HIDING SEARCH RESULTS (AI or direct lookup)');
                state.showResults = false;
            }
        }
    );

    // Hide results immediately when direct lookup starts
    watch(() => searchBar.isDirectLookup, (isDirectLookup) => {
        if (isDirectLookup) {
            state.showResults = false;
        }
    });

    // Check current query for AI mode on page load (in lookup mode only)
    if (searchConfig.searchMode === 'lookup' && state.query) {
        // AI mode is automatically computed by useAIMode composable based on query
        shouldTriggerAIMode(state.query); // Validate query pattern
    }

    // Initialize AI suggestions (method removed in modular architecture)
    state.aiSuggestions = [];
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