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
        <div
            class="pointer-events-auto relative overflow-visible px-0 pt-2 pb-0 sm:px-2"
        >
            <!-- Search Bar -->
            <div
                ref="searchBarElement"
                :class="[
                    'search-bar relative flex items-center gap-2 overflow-visible px-1 py-0.5 sm:px-1',
                    'shadow-cartoon-sm rounded-2xl transition-[border-color,background-color,box-shadow,backdrop-filter] duration-500 ease-apple-smooth',
                    searchBar.isAIQuery && !searchBar.hasErrorAnimation
                        ? 'border-2 border-amber-500 bg-amber-50 backdrop-blur-sm dark:border-amber-700/40 dark:bg-amber-950/30'
                        : searchBar.hasErrorAnimation
                          ? 'border-2 border-red-400/50 bg-gradient-to-br from-red-50/20 to-red-50/10 dark:border-red-600/50 dark:from-red-900/20 dark:to-red-900/10'
                          : 'border-2 border-border bg-background/90 backdrop-blur-xl',
                    {
                        'shadow-cartoon-sm-hover': uiState.isContainerHovered,
                        'bg-background/95':
                            uiState.isContainerHovered && !searchBar.isAIQuery,
                        'shake-error': searchBar.hasErrorAnimation,
                    },
                ]"
                :style="searchBarShellStyle"
            >
                <!-- Border shimmer overlay in AI mode -->
                <BorderShimmer
                    v-if="searchBar.isAIQuery && !searchBar.hasErrorAnimation"
                    :active="true"
                    color="var(--ai-accent)"
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
                    :show-subscript="canToggleMode"
                    :ai-mode="searchBar.isAIQuery"
                    @update:model-value="
                        (value: any) => searchBar.setSubMode('lookup', value)
                    "
                />

                <!-- Search Input Container with Autocomplete -->
                <div class="search-field-shell relative max-w-none min-w-0 flex-1 flex-grow">
                    <!-- Autocomplete Overlay -->
                    <AutocompleteOverlay
                        :query="searchQuery"
                        :suggestion="searchBar.autocompleteText"
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
                        :max-height="searchBar.isAIQuery ? 210 : 200"
                        :text-align="
                            iconOpacity < 0.3 && !searchBar.isAIQuery
                                ? 'center'
                                : 'left'
                        "
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

                    <!-- Clear/Expand Action Buttons -->
                    <SearchInputActions
                        :ai-mode="searchBar.isAIQuery"
                        :show-clear="
                            searchQuery.length > 0 && searchBar.isFocused
                        "
                        :scroll-progress="props.scrollProgress"
                        @expand="handleExpandClick"
                        @clear="clearQuery"
                    />
                </div>

                <!-- Hamburger Button -->
                <div
                    class="search-hamburger-slot flex flex-shrink-0 items-center justify-center overflow-hidden transition-[opacity,transform] duration-350 ease-apple-default"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
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
            <div class="absolute top-full right-0 left-0 z-40 pt-1">
                <!-- Controls Dropdown — grid-based height transition wrapper -->
                <div
                    :class="[
                        'controls-dropdown-wrapper',
                        searchBar.showSearchControls
                            ? 'controls-dropdown-open'
                            : 'controls-dropdown-closed',
                    ]"
                >
                    <SearchControls
                        class="min-h-0 overflow-hidden"
                        :show="true"
                        v-model:selected-sources="selectedSources"
                        v-model:selected-languages="selectedLanguages"
                        v-model:no-a-i="noAI"
                        v-model:wordlist-filters="wordlistFilters"
                        :wordlist-sort-criteria="wordlistSortCriteria"
                        @update:wordlist-sort-criteria="
                            (value: any) => (wordlistSortCriteria = value)
                        "
                        :ai-suggestions="searchBar.aiSuggestions as string[]"
                        :is-development="uiState.isDevelopment"
                        :show-refresh-button="
                            !!content.currentEntry &&
                            searchBar.searchMode === 'lookup'
                        "
                        :force-refresh-mode="loading.forceRefreshMode.value"
                        @word-select="selectWord"
                        @clear-storage="clearAllStorage"
                        @interaction="handleSearchAreaInteraction"
                        @toggle-sidebar="ui.toggleSidebar()"
                        @toggle-refresh="handleForceRegenerate"
                        @execute-search="handleEnterWrapped"
                    />
                </div>

                <!-- Search Results Container -->
                <div>
                    <SearchResults
                        ref="searchResultsComponent"
                        :show="searchBar.showDropdown"
                        :results="unifiedResults"
                        :loading="loading.isSearching.value"
                        v-model:selected-index="searchSelectedIndex"
                        :query="searchQuery"
                        :ai-mode="searchBar.isAIQuery"
                        :recent-searches="historyStore.recentSearches as any[]"
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
// Modular stores - direct imports
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useContentStore } from '@/stores/content/content';
import { useHistoryStore } from '@/stores/content/history';
import { useUIStore } from '@/stores/ui/ui-state';
import { useLoadingStore } from '@/stores/ui/loading';
// Maximize2 and X moved to SearchInputActions component
import { HamburgerIcon } from '@/components/custom/icons';
import { BorderShimmer } from '@/components/custom/animation';

// Import components
import SearchInput from './components/SearchInput.vue';
import SparkleIndicator from './components/SparkleIndicator.vue';
import ModeToggle from './components/ModeToggle.vue';
import AutocompleteOverlay from './components/AutocompleteOverlay.vue';
import SearchControls from './components/controls/SearchControls.vue';
import SearchResults from './components/results/SearchResults.vue';
import ExpandModal from './components/ExpandModal.vue';
import ThinLoadingProgress from './components/ThinLoadingProgress.vue';
import SearchInputActions from './components/SearchInputActions.vue';
import ConfirmDialog from '../ConfirmDialog.vue';

// Import composables
import {
    useSearchBarUI,
    useSearchBarBindings,
    useSearchBarNavigation,
    useFocusManagement,
    useModalManagement,
    useSearchBarScroll,
    useAutocomplete,
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
const content = useContentStore();
const historyStore = useHistoryStore();
const ui = useUIStore();
const loading = useLoadingStore();
const router = useRouter();
const { iconOpacity, uiState } = useSearchBarUI();

// Extracted v-model bindings, computeds, and mode-lifecycle watchers
const {
    searchQuery,
    searchSelectedIndex,
    unifiedResults,
    selectedSources,
    selectedLanguages,
    noAI,
    wordlistFilters,
    wordlistSortCriteria,
    canToggleMode,
    placeholder,
    showProgressBar,
    searchBarShellStyle,
    stopLifecycleEffects,
} = useSearchBarBindings({
    scrollProgress: () => props.scrollProgress,
    iconOpacity,
    uiState,
});

// Dialog state
const showClearStorageDialog = ref(false);

// Refs
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();
void searchBarElement; // bound via template ref="searchBarElement"
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
            return (
                (searchBar.getResults('wordlist')?.slice(0, 10) as any) || []
            );
        }
        return (searchBar.getResults('lookup') as any) || [];
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
    handleFocus,
    handleBlur,
    handleSearchAreaInteraction,
    focusInput,
    cleanup: cleanupFocus,
} = useFocusManagement({
    searchInputComponent,
    searchContainer,
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
    searchBar.toggleSearchControls();
};

const selectWord = (word: string) => {
    searchBar.hideDropdown();
    searchBar.hideControls();
    searchBar.clearResults();
    // Navigate — the route watcher in Home.vue handles the fetch
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word } });
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

// Close dropdown when loading modal appears (lookup initiated)
watch(
    () => loading.showLoadingModal.value,
    (showModal) => {
        if (showModal && searchBar.showDropdown) {
            searchBar.hideDropdown();
        }
    }
);

// Click outside handler is now in useFocusManagement composable

// Watch query changes — direct search (429s silenced in api/search.ts)
watch(
    () => searchBar.searchQuery,
    () => {
        performSearch();

        // Immediately recompute autocomplete for the new query.
        // This clears stale suggestions right away (e.g. if the new query
        // no longer matches the old suggestion prefix).
        updateAutocomplete();
        searchBar.setAutocompleteText(autocompleteText.value);
    }
);

// Watch search results for autocomplete updates.
// Use a single watcher on currentResults (covers both lookup and wordlist modes)
// instead of only watching lookup results.
watch(
    () => searchBar.currentResults,
    () => {
        updateAutocomplete();
        searchBar.setAutocompleteText(autocompleteText.value);
    }
);

// Initialize
onMounted(() => {
    searchBar.setAISuggestions([]);
});

// Cleanup
onUnmounted(() => {
    cleanupSearch();
    cleanupFocus();
    stopLifecycleEffects();
});
</script>

<style scoped>
.search-field-shell {
    min-height: var(--search-min-h, 48px);
    display: grid;
    align-items: stretch;
}

.search-hamburger-slot {
    width: var(--search-hamburger-width, 0rem);
    margin-left: var(--search-hamburger-gap, 0rem);
}

/*
 * Controls dropdown: grid-based height animation.
 * Uses grid-template-rows 0fr/1fr for smooth collapse without max-height.
 */
.controls-dropdown-wrapper {
    display: grid;
    will-change: grid-template-rows, opacity;
}

.controls-dropdown-open {
    grid-template-rows: 1fr;
    opacity: 1;
    margin-bottom: 0.25rem;
    /* ease-apple-smooth: cubic-bezier(0.4, 0, 0.2, 1) */
    transition:
        grid-template-rows 250ms cubic-bezier(0.4, 0, 0.2, 1),
        opacity 150ms cubic-bezier(0, 0, 0.2, 1),
        margin-bottom 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.controls-dropdown-closed {
    grid-template-rows: 0fr;
    opacity: 0;
    margin-bottom: 0;
    transition:
        grid-template-rows 180ms cubic-bezier(0.4, 0, 1, 1),
        opacity 120ms cubic-bezier(0.4, 0, 1, 1) 30ms,
        margin-bottom 180ms cubic-bezier(0.4, 0, 1, 1);
}

/* Disable animations for reduced motion */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
