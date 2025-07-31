<template>
    <!-- Sidebar -->
    <Sidebar />

    <div
        :class="
            cn('min-h-screen transition-all duration-300 ease-in-out', {
                'lg:ml-80': !store.sidebarCollapsed,
                'lg:ml-16': store.sidebarCollapsed,
            })
        "
    >
        <!-- Main View -->
        <div class="relative min-h-screen p-0 lg:p-4">
            <!-- Sticky Search Bar with scroll responsiveness -->
            <div :class="searchBarClasses">
                <div class="mx-auto w-full sm:max-w-4xl">
                    <SearchBar
                        :shrink-percentage="shrinkPercentage"
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
                    <div :class="['flex-1 max-w-5xl mx-auto', (store.mode === 'suggestions' || store.searchMode === 'wordlist') ? 'px-4 sm:px-2' : '']">
                        <!-- Animated Content Cards -->
                        <Transition
                    name="content-switch"
                    mode="out-in"
                >
                    <!-- Definition Content -->
                    <div v-if="store.searchMode === 'lookup' && store.mode !== 'suggestions'" key="lookup">
                        <!-- Loading State - only show skeleton if modal is visible and no partial data -->
                        <div v-if="isSearching && showLoadingModal && !store.partialEntry" class="space-y-8">
                            <DefinitionSkeleton />
                        </div>

                        <!-- Enhanced Definition Display - handles both streaming and complete data -->
                        <div v-else-if="store.isStreamingData || store.partialEntry || currentEntry || previousEntry || store.definitionError?.hasError" class="space-y-8">
                            <DefinitionDisplay 
                                v-if="store.isStreamingData || store.partialEntry || currentEntry || store.definitionError?.hasError" 
                            />
                        </div>

                        <!-- Empty State -->
                        <div v-else class="py-16 text-center">
                            <!-- Empty state - no text -->
                        </div>
                    </div>

                    <!-- Word Suggestions Content -->
                    <div v-else-if="store.mode === 'suggestions'" key="suggestions">
                        <div class="space-y-8">
                            <WordSuggestionDisplay />
                        </div>
                    </div>

                    <!-- Wordlist Content -->
                    <div
                        v-else-if="store.searchMode === 'wordlist'"
                        key="wordlist"
                    >
                        <WordListView />
                    </div>

                    <!-- Word of the Day Content -->
                    <div
                        v-else-if="store.searchMode === 'word-of-the-day'"
                        key="word-of-the-day"
                    >
                        <div class="space-y-8">
                            <!-- Word of the Day content will go here -->
                            <div
                                class="py-16 text-center text-muted-foreground"
                            >
                                Word of the Day mode coming soon...
                            </div>
                        </div>
                    </div>

                    <!-- Stage Content -->
                    <div v-else-if="store.searchMode === 'stage'" key="stage">
                        <div class="space-y-8">
                            <StageTest ref="stageTestRef" />
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
        :word="store.searchQuery || 'searching'"
        :progress="store.loadingProgress"
        :current-stage="store.loadingStage"
        :allow-dismiss="true"
        mode="lookup"
        :dynamic-checkpoints="store.loadingStageDefinitions"
        :category="store.loadingCategory"
    />
    
    <!-- Loading Modal for AI Suggestions -->
    <LoadingModal
        v-model="store.isSuggestingWords"
        :display-text="'efflorescing'"
        :progress="store.suggestionsProgress"
        :current-stage="store.suggestionsStage"
        mode="suggestions"
        :dynamic-checkpoints="store.suggestionsStageDefinitions"
        :category="store.suggestionsCategory"
    />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/stores';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay, WordSuggestionDisplay } from '@/components/custom/definition';
import { DefinitionSkeleton } from '@/components/custom/definition';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import WordListView from '@/components/custom/wordlist/WordListView.vue';
import { StageTest } from '@/components/custom/test';
import { ProgressiveSidebar } from '@/components/custom/navigation';

const store = useAppStore();
const route = useRoute();
const router = useRouter();

// Component refs
const stageTestRef = ref();

// Track loading modal visibility separately from search state
const showLoadingModal = ref(false);

// Handle stage mode enter key
const handleStageEnter = (_query: string) => {
    if (stageTestRef.value && stageTestRef.value.startMockTest) {
        stageTestRef.value.startMockTest();
    }
};


// Watch for route changes
watch(() => route.name, async (routeName) => {
    console.log('🔍 ROUTE WATCHER - Route changed to:', routeName, 'params:', route.params);
    
    if (routeName === 'Definition' && route.params.word) {
        const word = route.params.word as string;
        console.log('🔍 ROUTE WATCHER - Loading Definition for:', word);
        
        // Only call setSearchMode if we're not already in lookup mode
        if (store.searchMode !== 'lookup') {
            console.log('🔍 ROUTE WATCHER - Switching to lookup mode');
            store.setSearchMode('lookup', router);
        } else {
            console.log('🔍 ROUTE WATCHER - Already in lookup mode');
        }
        store.mode = 'dictionary';
        
        // Ensure the search query matches the word from the route
        console.log('🔍 ROUTE WATCHER - Setting search query to:', word);
        store.searchQuery = word;
        // Also update the lookup mode query in modeQueries
        store.modeQueries.lookup = word;
        
        // Hide search results immediately when loading definition via route
        console.log('🔍 ROUTE WATCHER - Hiding search results before searchWord');
        store.showSearchResults = false;
        store.searchResults = [];
        
        // Just do a normal lookup like any other search
        await store.searchWord(word);
    } else if (routeName === 'Thesaurus' && route.params.word) {
        const word = route.params.word as string;
        console.log('🔍 ROUTE WATCHER - Loading Thesaurus for:', word);
        
        // Only call setSearchMode if we're not already in lookup mode
        if (store.searchMode !== 'lookup') {
            console.log('🔍 ROUTE WATCHER - Switching to lookup mode');
            store.setSearchMode('lookup', router);
        } else {
            console.log('🔍 ROUTE WATCHER - Already in lookup mode');
        }
        store.mode = 'thesaurus';
        
        // Ensure the search query matches the word from the route
        console.log('🔍 ROUTE WATCHER - Setting search query to:', word);
        store.searchQuery = word;
        // Also update the lookup mode query in modeQueries
        store.modeQueries.lookup = word;
        
        // Hide search results immediately when loading thesaurus via route
        console.log('🔍 ROUTE WATCHER - Hiding search results before searchWord');
        store.showSearchResults = false;
        store.searchResults = [];
        
        // Just do a normal lookup like any other search
        await store.searchWord(word);
    } else if ((routeName === 'Wordlist' || routeName === 'WordlistSearch') && route.params.wordlistId) {
        const wordlistId = route.params.wordlistId as string;
        console.log('🔍 ROUTE WATCHER - Loading Wordlist:', wordlistId);
        
        console.log('🏠 Home.vue route watcher switching to wordlist mode');
        store.setSearchMode('wordlist', router);  // Pass router to indicate mode switching
        store.setWordlist(wordlistId);
        
        // Handle search query if present
        if (routeName === 'WordlistSearch' && route.params.query) {
            const query = decodeURIComponent(route.params.query as string);
            store.searchQuery = query;
        }
    }
}, { immediate: true });

// Watch for wordlist route parameter changes
watch(() => route.params.wordlistId, (newWordlistId) => {
    if (route.name === 'Wordlist' || route.name === 'WordlistSearch') {
        if (newWordlistId && typeof newWordlistId === 'string') {
            store.setWordlist(newWordlistId);
        } else {
            store.setWordlist(null);
        }
    }
}, { immediate: true });


onMounted(async () => {
    console.log('Home component mounted');
    console.log('Has searched:', store.hasSearched);
    console.log('Search results:', store.searchResults);

    // Note: Vocabulary suggestions are initialized automatically by the store
    // No need to refresh them here as the store already handles initialization
});

// Track loading modal visibility separately from search state
// (moved above route watcher to avoid reference error)
const isSearching = computed(() => store.isSearching);
const currentEntry = computed(() => store.currentEntry);
const previousEntry = ref<any>(null);

// Track previous entry for smooth transitions
watch(currentEntry, (newEntry, oldEntry) => {
    if (oldEntry && newEntry?.word !== oldEntry?.word) {
        previousEntry.value = oldEntry;
    }
    // Clear previous entry after transition
    if (newEntry) {
        setTimeout(() => {
            previousEntry.value = null;
        }, 1000);
    }
});

// Sync loading modal visibility with search state
watch(isSearching, (newVal) => {
    if (newVal) {
        showLoadingModal.value = true;
    } else {
        // Also hide modal when searching completes
        showLoadingModal.value = false;
    }
});


// Expose loading modal state to store
watch(showLoadingModal, (newVal) => {
    store.showLoadingModal = newVal;
});

// Sync store loading modal state back to local state
watch(() => store.showLoadingModal, (newVal) => {
    showLoadingModal.value = newVal;
});

// Scroll-based shrinking animation
const { y } = useScroll(window);
const scrollThreshold = 100;

const isScrolled = computed(() => y.value > scrollThreshold);
const shrinkPercentage = computed(() => {
    if (y.value <= scrollThreshold) return 0;
    return Math.min((y.value - scrollThreshold) / 60, 1);
});

const searchBarClasses = computed(() => {
    return cn(
        'sticky top-0 z-40 transition-all duration-300 ease-out',
        isScrolled.value ? 'py-2' : 'py-4'
    );
});

// Should show progressive sidebar
const shouldShowProgressiveSidebar = computed(() => {
    // Only show in lookup mode with dictionary content and a current entry
    if (store.searchMode !== 'lookup' || store.mode !== 'dictionary' || !currentEntry.value) return false;
    
    // Check if we have multiple clusters
    const definitions = currentEntry.value.definitions;
    if (!definitions || definitions.length === 0) return false;
    
    // Group by cluster to see if we have multiple
    const clusters = new Set(definitions.map(d => d.meaning_cluster?.id || 'default'));
    return clusters.size > 1;
});
</script>

<style scoped>
/* Content transitions - consistent with mode switching animation */
.content-switch-enter-active {
    transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* apple-spring */
}

.content-switch-leave-active {
    transition: all 0.25s cubic-bezier(0.6, -0.28, 0.735, 0.045); /* apple-bounce-in */
}

.content-switch-enter-from {
    opacity: 0;
    transform: scale(0.95) translateY(20px);
}

.content-switch-enter-to {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.content-switch-leave-from {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.content-switch-leave-to {
    opacity: 0;
    transform: scale(0.95) translateY(-20px);
}

/* Definition switching - smoother, opacity-focused */
.definition-switch-enter-active {
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* apple-spring */
}

.definition-switch-leave-active {
    transition: all 0.2s cubic-bezier(0.6, -0.28, 0.735, 0.045); /* apple-bounce-in */
}

.definition-switch-enter-from {
    opacity: 0;
    transform: scale(0.98) translateY(10px);
}

.definition-switch-enter-to {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.definition-switch-leave-from {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.definition-switch-leave-to {
    opacity: 0;
    transform: scale(0.98) translateY(-10px);
}

/* Progressive sidebar slide animation - Apple-style bounce */
.sidebar-slide-enter-active {
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* apple-spring */
}

.sidebar-slide-leave-active {
    transition: all 0.3s cubic-bezier(0.6, -0.28, 0.735, 0.045); /* apple-bounce-in */
}

.sidebar-slide-enter-from {
    opacity: 0;
    transform: translateX(-30px) scale(0.95);
}

.sidebar-slide-enter-to {
    opacity: 1;
    transform: translateX(0) scale(1);
}

.sidebar-slide-leave-from {
    opacity: 1;
    transform: translateX(0) scale(1);
}

.sidebar-slide-leave-to {
    opacity: 0;
    transform: translateX(-30px) scale(0.95);
}
</style>
