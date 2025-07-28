<template>
    <div
        ref="searchContainer"
        :class="[
            'search-container relative z-50 mx-auto w-full origin-top px-3 sm:px-0',
            props.className,
        ]"
        :style="containerStyle"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
    >
        <!-- Main Layout -->
        <div class="pointer-events-auto relative overflow-visible pt-2 px-2 sm:px-2 pb-0">
            <!-- Search Bar -->
            <div
                ref="searchBarElement"
                :class="[
                    'search-bar relative flex items-center gap-2 overflow-visible px-1 py-0.5',
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
                            paddingRight: state.query.length > 0
                                ? '5rem'
                                : state.expandButtonVisible
                                ? '3rem'
                                : iconOpacity > 0.1
                                  ? '1rem'
                                  : '1.5rem',
                            paddingTop: '0.75rem',
                            paddingBottom: '0.75rem',
                        }"
                        @enter="handleEnter"
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

                    <!-- Clear Button -->
                    <Transition
                        enter-active-class="transition-all duration-200 ease-out"
                        leave-active-class="transition-all duration-200 ease-in"
                        enter-from-class="opacity-0 scale-90"
                        leave-to-class="opacity-0 scale-90"
                    >
                        <button
                            v-if="state.query.length > 0"
                            @click.stop="clearQuery"
                            :class="[
                                'absolute right-2 top-1/2 -translate-y-1/2 z-20 rounded-md p-1 transition-all duration-200',
                                'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                state.isAIQuery
                                    ? 'bg-amber-100/80 hover:bg-amber-200/80 dark:bg-amber-900/40 dark:hover:bg-amber-800/40'
                                    : 'bg-muted/50 hover:bg-muted/80'
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

                    <!-- Expand Button -->
                    <Transition
                        enter-active-class="transition-all duration-200 ease-out"
                        leave-active-class="transition-all duration-200 ease-in"
                        enter-from-class="opacity-0 scale-90"
                        leave-to-class="opacity-0 scale-90"
                    >
                        <button
                            v-if="state.expandButtonVisible && state.scrollProgress < 0.3 && state.query.length === 0"
                            :class="[
                                'absolute right-2 bottom-2 z-20 rounded-md p-1 transition-all duration-200',
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
                </div>

                <!-- Hamburger Button -->
                <HamburgerIcon
                    :is-open="state.showControls"
                    :ai-mode="state.isAIQuery"
                    :opacity="iconOpacity"
                    @toggle="state.showControls = !state.showControls"
                />

                <!-- Progress Bar -->
                <!-- <div
                    v-if="store.loadingProgress > 0"
                    class="absolute right-0 -bottom-2 left-0 h-2
                        overflow-hidden"
                >
                    <div
                        class="h-full rounded-full transition-[width]
                            duration-300"
                        :style="{
                            width: `${store.loadingProgress}%`,
                            background: generateRainbowGradient(8),
                        }"
                    />
                </div> -->
            </div>

            <!-- Dropdowns Container -->
            <div class="absolute top-full right-0 left-0 z-50 pt-2">
                <!-- Controls Dropdown -->
                <SearchControls
                    :show="state.showControls"
                    v-model:search-mode="state.searchMode"
                    v-model:selected-sources="state.selectedSources"
                    v-model:selected-languages="state.selectedLanguages"
                    :ai-suggestions="state.aiSuggestions"
                    :is-development="state.isDevelopment"
                    :show-refresh-button="!!store.currentEntry && state.searchMode === 'lookup'"
                    :force-refresh-mode="state.forceRefreshMode"
                    @word-select="selectWord"
                    @clear-storage="clearAllStorage"
                    @interaction="handleSearchAreaInteraction"
                    @toggle-sidebar="store.toggleSidebar()"
                    @toggle-refresh="handleForceRegenerate"
                />

                <!-- Search Results Container -->
                <div
                    :style="resultsContainerStyle"
                    :class="{ 'mt-2': state.showControls }"
                >
                    <SearchResults
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
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import { showError } from '@/plugins/toast';
import { Maximize2, RefreshCw, X } from 'lucide-vue-next';
import { HamburgerIcon } from '@/components/custom/icons';

// Import components
import SearchInput from './components/SearchInput.vue';
import SparkleIndicator from './components/SparkleIndicator.vue';
import ModeToggle from './components/ModeToggle.vue';
import AutocompleteOverlay from './components/AutocompleteOverlay.vue';
import SearchControls from './components/SearchControls.vue';
import SearchResults from './components/SearchResults.vue';
import ExpandModal from './components/ExpandModal.vue';

// Import composables and utilities
import { useSearchBarSharedState } from './composables/useSearchBarSharedState';
import { useScrollAnimationSimple } from './composables/useScrollAnimationSimple';
import { useAutocomplete } from './composables/useAutocomplete';
import { shouldTriggerAIMode, extractWordCount } from './utils/ai-query';
import { shouldShowExpandButton } from './utils/keyboard';

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

// Debug prop changes
if (import.meta.env.DEV) {
    watch(
        () => props.shrinkPercentage,
        (newVal, oldVal) => {
            if (newVal !== oldVal) {
                console.log('SearchBar prop changed:', { oldVal, newVal });
            }
        }
    );
}

const emit = defineEmits<{
    focus: [];
    blur: [];
    mouseenter: [];
    mouseleave: [];
    'stage-enter': [query: string];
}>();

// Store & State
const store = useAppStore();
const { state, iconOpacity, canToggleMode } = useSearchBarSharedState();

// Refs
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();
const searchInputComponent = ref<any>();
const regenerateRotation = ref(0);

// Computed
const placeholder = computed(() => {
    // First check searchMode for specific modes
    if (state.searchMode === 'wordlist') {
        return 'Enter words separated by spaces or commas...';
    } else if (state.searchMode === 'stage') {
        return 'Enter text for staging...';
    }

    // Default to mode-based placeholders for lookup mode
    return state.mode === 'dictionary'
        ? 'Definitions'
        : 'Synonyms';
});

const resultsContainerStyle = computed(() => ({
    paddingTop: '0px',
    transition: 'all 300ms cubic-bezier(0.25, 0.1, 0.25, 1)',
}));

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
        // Debug logging
        if (import.meta.env.DEV) {
            console.log('SearchBar scroll update:', {
                shrinkPercentage: newValue,
                scrollProgress: state.scrollProgress,
                containerStyle: containerStyle.value,
            });
        }
    },
    { immediate: true }
);

// Create a computed ref for the search input element
const searchInputRef = computed(() => searchInputComponent.value?.element);

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

// Timers
let searchTimer: ReturnType<typeof setTimeout> | undefined;
let isInteractingWithSearchArea = false;

// Watch query for autocomplete
watch(
    () => state.query,
    () => {
        updateAutocomplete();
        state.autocompleteText = autocompleteText.value;
        state.expandButtonVisible = shouldShowExpandButton(
            state.isAIQuery,
            state.query.length,
            state.query.includes('\n')
        );
    }
);

// Watch search results for autocomplete
watch(
    () => state.searchResults,
    () => {
        state.selectedIndex = 0;
        updateAutocomplete();
        state.autocompleteText = autocompleteText.value;
    }
);

// Event Handlers
const handleMouseEnter = () => {
    state.isContainerHovered = true;
    emit('mouseenter');
};

const handleMouseLeave = () => {
    state.isContainerHovered = false;
    emit('mouseleave');
};

const handleFocus = () => {
    state.isFocused = true;
    emit('focus');

    // Force textarea resize on focus
    nextTick(() => {
        if (searchInputComponent.value?.element?.value) {
            const textarea = searchInputComponent.value.element.value;
            textarea.style.height = 'auto';
            const scrollHeight = textarea.scrollHeight;
            textarea.style.height = `${scrollHeight}px`;
        }
    });

    // Restore search results if available
    if (
        store.sessionState?.searchResults?.length > 0 &&
        state.query.length >= 2
    ) {
        state.searchResults = store.sessionState.searchResults.slice(0, 8);
    }
};

const handleBlur = () => {
    setTimeout(() => {
        if (isInteractingWithSearchArea) return;

        state.isFocused = false;
        emit('blur');

        // Hide results on blur
        state.showResults = false;
        state.searchResults = [];
        state.isSearching = false;
    }, 150);
};

const handleInputClick = (event: MouseEvent) => {
    handleSearchAreaInteraction();
    handleAutocompleteInputClick(event);
};

const handleSearchAreaInteraction = () => {
    isInteractingWithSearchArea = true;
    setTimeout(() => {
        isInteractingWithSearchArea = false;
    }, 100);
};

// Search functionality
const performSearch = () => {
    clearTimeout(searchTimer);
    store.searchQuery = state.query;

    if (!state.query || state.query.length < 2) {
        state.searchResults = [];
        state.isSearching = false;
        state.isAIQuery = false;
        state.showSparkle = false;
        return;
    }

    state.isSearching = true;

    searchTimer = setTimeout(async () => {
        try {
            const results = await store.search(state.query);
            state.searchResults = results.slice(0, 8);
            state.selectedIndex = 0;

            if (store.sessionState) {
                store.sessionState.searchResults = results;
            }

            // Activate AI mode
            if (results.length === 0 && shouldTriggerAIMode(state.query)) {
                state.isAIQuery = true;
                state.showSparkle = true;
                store.sessionState.isAIQuery = true;
                store.sessionState.aiQueryText = state.query;
            } else {
                state.isAIQuery = false;
                state.showSparkle = false;
                store.sessionState.isAIQuery = false;
                store.sessionState.aiQueryText = '';
            }
        } catch (error) {
            console.error('Search error:', error);
            state.searchResults = [];
        } finally {
            state.isSearching = false;
        }
    }, 200);
};

// Keyboard handlers
const handleEnter = async () => {
    clearTimeout(searchTimer);

    if (state.autocompleteText) {
        const accepted = await acceptAutocomplete();
        if (accepted) {
            return;
        }
    }

    // Handle stage mode
    if (state.searchMode === 'stage' && state.query) {
        store.searchQuery = state.query;
        emit('stage-enter', state.query);
        return;
    }

    // Handle wordlist mode
    if (state.searchMode === 'wordlist' && state.query) {
        // Parse the query as a list of words (space, comma, or newline separated)
        const words = state.query
            .split(/[,\\s\\n]+/)
            .map((word) => word.trim())
            .filter((word) => word.length > 0);

        if (words.length > 0) {
            // Process wordlist - for now, just look up the first word
            // TODO: Implement full wordlist processing
            store.searchQuery = words[0];
            store.hasSearched = true;
            state.showResults = false;
            await store.getDefinition(words[0]);

            // You could emit a wordlist event here for future handling
            // emit('wordlist-enter', words);
        }
        return;
    }

    // Handle AI query mode
    if (state.isAIQuery && state.query) {
        try {
            const extractedCount = extractWordCount(state.query);
            const wordSuggestions = await store.getAISuggestions(
                state.query,
                extractedCount
            );

            if (wordSuggestions && wordSuggestions.suggestions.length > 0) {
                store.wordSuggestions = wordSuggestions;
                state.mode = 'suggestions';
                store.hasSearched = true;
                store.sessionState.aiQueryText = state.query;
            } else {
                state.showErrorAnimation = true;
                showError('No word suggestions found for this query');
                setTimeout(() => {
                    state.showErrorAnimation = false;
                }, 600);
            }
        } catch (error: any) {
            console.error('AI suggestion error:', error);
            state.showErrorAnimation = true;
            showError(error.message || 'Failed to get word suggestions');
            setTimeout(() => {
                state.showErrorAnimation = false;
            }, 600);
        }
        return;
    }

    // Regular search
    if (state.searchResults.length > 0 && state.selectedIndex >= 0) {
        await selectResult(state.searchResults[state.selectedIndex]);
    } else if (state.query) {
        state.isFocused = false;
        state.showResults = false;
        store.searchQuery = state.query;
        store.hasSearched = true;
        await store.getDefinition(state.query);
    }
};

const handleEscape = () => {
    if (state.showControls || state.showResults) {
        state.showControls = false;
        state.showResults = false;
    } else {
        // Blur input
        state.isFocused = false;
    }
};

const handleSpaceKey = (event: KeyboardEvent) => {
    handleAutocompleteSpaceKey(event);
};

const handleArrowKey = (event: KeyboardEvent) => {
    handleAutocompleteArrowKey(event);
};

const navigateResults = (direction: number) => {
    if (state.searchResults.length === 0) return;

    state.selectedIndex = Math.max(
        0,
        Math.min(
            state.searchResults.length - 1,
            state.selectedIndex + direction
        )
    );

    store.searchSelectedIndex = state.selectedIndex;
};

const selectResult = async (result: SearchResult) => {
    clearTimeout(searchTimer);
    state.query = result.word;
    store.searchQuery = result.word;
    state.searchResults = [];
    state.showResults = false;
    store.hasSearched = true;
    await store.getDefinition(result.word);
};

const selectWord = (word: string) => {
    state.query = word;
    handleEnter();
};

const handleForceRegenerate = () => {
    handleSearchAreaInteraction();
    state.forceRefreshMode = !state.forceRefreshMode;
};

const clearQuery = () => {
    state.query = '';
    state.searchResults = [];
    state.showResults = false;
    state.isAIQuery = false;
    state.showSparkle = false;
    searchInputComponent.value?.focus();
};

const clearAllStorage = () => {
    if (
        confirm(
            'This will clear all local storage including history and settings. Are you sure?'
        )
    ) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.reload();
    }
};

// Expand modal
const handleExpandClick = () => {
    state.showExpandModal = true;
};

const closeExpandModal = () => {
    state.showExpandModal = false;
};

const submitExpandedQuery = (query: string) => {
    state.query = query;
    state.showExpandModal = false;
    nextTick(() => {
        handleEnter();
    });
};

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
    if (!searchContainer.value || !state.showControls) return;
    
    const target = event.target as HTMLElement;
    // Check if click is outside the search container
    if (!searchContainer.value.contains(target)) {
        state.showControls = false;
    }
};

// Initialize
onMounted(async () => {
    // Add click outside listener
    document.addEventListener('click', handleClickOutside);
    
    // Watch query changes
    watch(
        () => state.query,
        () => {
            performSearch();
        }
    );
    
    // Watch store searchQuery changes to sync with local state
    watch(
        () => store.searchQuery,
        (newQuery) => {
            if (newQuery !== state.query) {
                state.query = newQuery;
            }
        }
    );

    // Watch for AI mode changes from store
    watch(
        () => store.sessionState?.isAIQuery,
        (isAI) => {
            if (isAI !== state.isAIQuery) {
                state.isAIQuery = isAI;
                state.showSparkle = isAI;
            }
        }
    );

    // Show results when focused with query
    watch(
        [() => state.isFocused, () => state.query, () => state.isAIQuery],
        ([focused, query, isAI]) => {
            if (focused && query && query.length > 0 && !isAI) {
                state.showResults = true;
            } else if (isAI) {
                state.showResults = false;
            }
        }
    );

    // Restore AI state if persisted
    if (store.sessionState.isAIQuery) {
        state.isAIQuery = true;
        state.showSparkle = true;
        if (store.sessionState.aiQueryText && !state.query) {
            state.query = store.sessionState.aiQueryText;
        }
    }

    // Get AI suggestions
    try {
        const history = await store.getHistoryBasedSuggestions();
        state.aiSuggestions = history.slice(0, 4);
    } catch {
        state.aiSuggestions = [];
    }
});

// Cleanup
onUnmounted(() => {
    clearTimeout(searchTimer);
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
