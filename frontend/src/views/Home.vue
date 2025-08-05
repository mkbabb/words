<template>
    <div>
        <!-- Sidebar -->
        <Sidebar />

        <div
            :class="
                cn('min-h-screen transition-all duration-300 ease-in-out', {
                    'lg:ml-80': !ui.sidebarCollapsed,
                    'lg:ml-16': ui.sidebarCollapsed,
                })
            "
        >
        <!-- Main View -->
        <div class="relative min-h-screen p-0 lg:p-4">
            <!-- Sticky Search Bar with scroll responsiveness -->
            <div :class="searchBarClasses">
                <div class="mx-auto w-full sm:max-w-4xl">
                    <SearchBar
                        :scroll-y="y"
                        :scroll-threshold="scrollThreshold"
                        :shrink-percentage="shrinkPercentage"
                        :scroll-progress="scrollProgress"
                        @stage-enter="handleStageEnter"
                    />
                </div>
            </div>

            <!-- Border separator (not sticky) -->
            <div class="border-b border-border/50 lg:my-6"></div>

            <!-- Content Area with Sidebar -->
            <div class="container mx-auto max-w-6xl">
                <div class="flex gap-6 relative">
                    <!-- Progressive Sidebar (Sticky) -->
                    <div 
                        class="hidden xl:block transition-all duration-300 ease-out"
                        :class="shouldShowProgressiveSidebar ? 'w-48 opacity-100' : 'w-0 opacity-0'"
                    >
                        <div 
                            v-if="shouldShowProgressiveSidebar"
                            class="sticky w-48"
                            :style="{ top: '5.5rem', zIndex: 30 }"
                        >
                            <ProgressiveSidebar />
                        </div>
                    </div>
                    
                    <!-- Main Content -->
                    <div :class="['flex-1 max-w-5xl mx-auto', (lookupSubMode === 'suggestions' || searchBar.searchMode === 'wordlist') ? 'px-4 sm:px-2' : '']">
                        <!-- Animated Content Cards -->
                        <Transition
                    name="content-switch"
                    mode="out-in"
                    :duration="{ enter: 300, leave: 500 }"
                >
                    <!-- Definition Content -->
                    <div v-if="searchBar.searchMode === 'lookup' && lookupSubMode !== 'suggestions'" key="lookup">
                        <!-- Loading State -->
                        <div v-if="isSearching && showLoadingModal && !partialEntry" class="space-y-8">
                            <DefinitionSkeleton />
                        </div>

                        <!-- Definition Display -->
                        <div v-else-if="isStreamingData || partialEntry || currentEntry || previousEntry || definitionError?.hasError" class="space-y-8">
                            <DefinitionDisplay />
                        </div>

                        <!-- Empty State -->
                        <div v-else class="py-16 text-center">
                            <!-- Empty state - no text -->
                        </div>
                    </div>

                    <!-- Word Suggestions Content -->
                    <div v-else-if="lookupSubMode === 'suggestions'" key="suggestions">
                        <div class="space-y-8">
                            <WordSuggestionDisplay />
                        </div>
                    </div>

                    <!-- Wordlist Content -->
                    <div v-else-if="searchBar.searchMode === 'wordlist'" key="wordlist">
                        <WordListView />
                    </div>

                    <!-- Word of the Day Content -->
                    <div v-else-if="searchBar.searchMode === 'word-of-the-day'" key="word-of-the-day">
                        <div class="space-y-8">
                            <div class="py-16 text-center text-muted-foreground">
                                Word of the Day mode coming soon...
                            </div>
                        </div>
                    </div>

                    <!-- Stage Content -->
                    <div v-else-if="searchBar.searchMode === 'stage'" key="stage">
                        <div class="space-y-8">
                            <!-- TODO: Import StageTest component -->
                            <div>Stage mode coming soon...</div>
                        </div>
                    </div>
                        </Transition>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Loading Modal for Lookup -->
    <LoadingModal
        v-model="showLoadingModal"
        :word="searchBar.searchQuery || 'searching'"
        :progress="loading.loadingProgress"
        :current-stage="loading.loadingStage"
        :allow-dismiss="true"
        mode="lookup"
        :dynamic-checkpoints="[...loading.loadingStageDefinitions]"
        :category="loading.loadingCategory"
    />
    
    <!-- Loading Modal for AI Suggestions -->
    <LoadingModal
        v-model="showSuggestionsModal"
        :display-text="'efflorescing'"
        :progress="loading.suggestionsProgress"
        :current-stage="loading.suggestionsStage"
        mode="suggestions"
        :dynamic-checkpoints="[...loading.suggestionsStageDefinitions]"
        :category="loading.suggestionsCategory"
    />
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useStores } from '@/stores';
// import { useLookupMode } from '@/stores/search/modes/lookup'; // Unused
// import { useWordlistMode } from '@/stores/search/modes/wordlist'; // Unused
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay, WordSuggestionDisplay } from '@/components/custom/definition';
import { DefinitionSkeleton } from '@/components/custom/definition';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import WordListView from '@/components/custom/wordlist/WordListView.vue';
// import { StageTest } from '@/components/custom/test';
import { ProgressiveSidebar } from '@/components/custom/navigation';

const { searchBar, content, ui, loading } = useStores();
// const wordlistMode = useWordlistMode(); // Unused
const route = useRoute();

// Use the orchestrator for search operations
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery)
});

// Component refs
const stageTestRef = ref();

// Track loading modal visibility separately from search state
const showLoadingModal = ref(false);

// Computed property for suggestions modal visibility
const showSuggestionsModal = computed({
    get: () => loading.isSuggestingWords,
    set: (value: boolean) => {
        if (!value) {
            loading.stopSuggestions();
        }
    }
});

// Computed for current lookup submode
const lookupSubMode = computed(() => searchBar.getSubMode('lookup'));

// Handle stage mode enter key
const handleStageEnter = (_query: string) => {
    if (stageTestRef.value && stageTestRef.value.startMockTest) {
        stageTestRef.value.startMockTest();
    }
};


// Route orchestration using modern store API and orchestrator
watch(() => route.name, async (routeName) => {
    if (routeName === 'Definition' && route.params.word) {
        const word = route.params.word as string;
        // Use modern mode system - just change the modes
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'dictionary');
        searchBar.setQuery(word);
        
        // Only search if we don't have the current entry or it's a different word
        if (!content.currentEntry || content.currentEntry.word !== word) {
            searchBar.setDirectLookup(true);
            try {
                await orchestrator.getDefinition(word);
            } finally {
                searchBar.setDirectLookup(false);
            }
        }
    } else if (routeName === 'Thesaurus' && route.params.word) {
        const word = route.params.word as string;
        // Use modern mode system - just change the modes
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'thesaurus');
        searchBar.setQuery(word);
        
        // Only search if we don't have the current entry or it's a different word  
        if (!content.currentEntry || content.currentEntry.word !== word) {
            searchBar.setDirectLookup(true);
            try {
                await orchestrator.getThesaurusData(word);
            } finally {
                searchBar.setDirectLookup(false);
            }
        }
    } else if (routeName === 'Home') {
        // Clear when returning to home
        searchBar.clearQuery();
        content.clearCurrentEntry();
    }
}, { immediate: true });

// Watch search mode changes for clearing content
watch(() => searchBar.searchMode, (newMode, oldMode) => {
    if (newMode !== oldMode) {
        // Clear appropriate content when switching modes
        if (newMode !== 'lookup') {
            content.clearCurrentEntry();
        }
    }
});

// State from stores
const isSearching = computed(() => loading.isSearching);
const isStreamingData = computed(() => false); // TODO: Implement streaming
const currentEntry = computed(() => content.currentEntry);
const partialEntry = computed(() => null); // TODO: Implement partial results
const previousEntry = computed(() => null); // TODO: Implement previous entry
const definitionError = computed(() => ({
    hasError: false, // TODO: Implement error state
    message: ''
}));

// Scroll handling with responsive thresholds
const { y } = useScroll(typeof window !== 'undefined' ? window : null);

const scrollThreshold = computed(() => {
    const hasContent = currentEntry.value || content.wordSuggestions;
    // Dynamic thresholds based on content
    return hasContent ? 50 : 100;
});

// Enhanced scroll progress calculation
const scrollProgress = computed(() => {
    const threshold = scrollThreshold.value;
    const scrollPos = y.value;
    
    // Normalize scroll position to 0-1 range
    const maxScroll = threshold * 2; // Full effect at 2x threshold
    const progress = Math.min(scrollPos / maxScroll, 1);
    
    // Apply easing function for smoother transitions
    const easedProgress = 1 - Math.pow(1 - progress, 3);
    
    return easedProgress;
});

const shrinkPercentage = computed(() => {
    const progress = scrollProgress.value;
    const baseline = searchBar.isFocused ? 0 : 0.35;
    return Math.max(baseline, Math.min(progress * 0.85, 0.85));
});

// Search bar classes
const searchBarClasses = computed(() => [
    'relative top-0 z-40 bg-transparent',
    'transition-all duration-300 ease-out',
    'sticky',
    {
        'py-8': scrollProgress.value < 0.3,
        'py-4': scrollProgress.value >= 0.3 && scrollProgress.value < 0.7,
        'py-2': scrollProgress.value >= 0.7,
    },
]);

// Progressive sidebar visibility
const shouldShowProgressiveSidebar = computed(() => {
    const hasDefinition = !!currentEntry.value;
    const isLookupMode = searchBar.searchMode === 'lookup';
    const isSuggestionsSubMode = lookupSubMode.value === 'suggestions';
    const hasSuggestions = !!content.wordSuggestions;
    
    return isLookupMode && (hasDefinition || (isSuggestionsSubMode && hasSuggestions));
});

// Watch loading state for modal visibility
watch(() => loading.isSearching, (newValue) => {
    if (searchBar.searchMode === 'lookup' && !searchBar.isDirectLookup) {
        showLoadingModal.value = newValue;
    }
});

// Show loading modal when loading state is updated
watch(() => loading.showLoadingModal, (newValue) => {
    if (searchBar.searchMode === 'lookup') {
        showLoadingModal.value = newValue;
    }
});

// TODO: Handle streaming data updates when implemented

// Initialize wordlist if needed
onMounted(async () => {
    // Only fetch wordlists if we're in wordlist mode
    if (searchBar.searchMode === 'wordlist') {
        // TODO: Implement fetchWordlists
        console.log('TODO: Fetch wordlists');
    }
});
</script>

<style scoped>
/* Content switch animation */
.content-switch-enter-active,
.content-switch-leave-active {
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.content-switch-enter-from {
    opacity: 0;
    transform: translateY(10px);
}

.content-switch-enter-to {
    opacity: 1;
    transform: translateY(0);
}

.content-switch-leave-from {
    opacity: 1;
    transform: translateY(0);
}

.content-switch-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}

/* Card animations */
@keyframes cardFadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-card-fade-in {
    animation: cardFadeIn 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}
</style>