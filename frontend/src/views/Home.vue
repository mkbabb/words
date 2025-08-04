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
                    <div :class="['flex-1 max-w-5xl mx-auto', (ui.mode === 'suggestions' || searchConfig.searchMode === 'wordlist') ? 'px-4 sm:px-2' : '']">
                        <!-- Animated Content Cards -->
                        <Transition
                    name="content-switch"
                    mode="out-in"
                    :duration="{ enter: 300, leave: 500 }"
                >
                    <!-- Definition Content -->
                    <div v-if="searchConfig.searchMode === 'lookup' && ui.mode !== 'suggestions'" key="lookup">
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
                    <div v-else-if="ui.mode === 'suggestions'" key="suggestions">
                        <div class="space-y-8">
                            <WordSuggestionDisplay />
                        </div>
                    </div>

                    <!-- Wordlist Content -->
                    <div v-else-if="searchConfig.searchMode === 'wordlist'" key="wordlist">
                        <WordListView />
                    </div>

                    <!-- Word of the Day Content -->
                    <div v-else-if="searchConfig.searchMode === 'word-of-the-day'" key="word-of-the-day">
                        <div class="space-y-8">
                            <div class="py-16 text-center text-muted-foreground">
                                Word of the Day mode coming soon...
                            </div>
                        </div>
                    </div>

                    <!-- Stage Content -->
                    <div v-else-if="searchConfig.searchMode === 'stage'" key="stage">
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

const { searchBar, searchConfig, searchResults, content, ui, loading, orchestrator } = useStores();
const route = useRoute();

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

// Handle stage mode enter key
const handleStageEnter = (_query: string) => {
    if (stageTestRef.value && stageTestRef.value.startMockTest) {
        stageTestRef.value.startMockTest();
    }
};


// Route orchestration using modern store API
watch(() => route.name, async (routeName) => {
    if (routeName === 'Definition' && route.params.word) {
        const word = route.params.word as string;
        // ✅ Use simple mode system - just change the modes
        searchConfig.setMode('lookup');
        searchConfig.setLookupMode('dictionary');
        searchBar.setQuery(word);
        
        // Only search if we don't have the current entry or it's a different word
        if (!content.currentEntry || content.currentEntry.word !== word) {
            await orchestrator.searchWord(word);
        }
    } else if (routeName === 'Thesaurus' && route.params.word) {
        const word = route.params.word as string;
        // ✅ Use simple mode system - just change the modes
        searchConfig.setMode('lookup');
        searchConfig.setLookupMode('thesaurus');
        searchBar.setQuery(word);
        
        // Only search if we don't have the current entry or it's a different word
        if (!content.currentEntry || content.currentEntry.word !== word) {
            await orchestrator.searchWord(word);
        } else if (!content.currentThesaurus) {
            // If switching to thesaurus mode and we don't have thesaurus data, fetch it
            console.log('🔍 Fetching thesaurus data for:', word);
            await orchestrator.getThesaurusData(word);
        }
    } else if ((routeName === 'Wordlist' || routeName === 'WordlistSearch') && route.params.wordlistId) {
        const wordlistId = route.params.wordlistId as string;
        // ✅ Use simple mode system - just change the mode
        searchConfig.setMode('wordlist');
        searchConfig.setWordlist(wordlistId);
        if (routeName === 'WordlistSearch' && route.params.query) {
            searchBar.setQuery(decodeURIComponent(route.params.query as string));
        }
    }
}, { immediate: true });

// Simplified wordlist parameter watching
watch(() => route.params.wordlistId, (newWordlistId) => {
    if ((route.name === 'Wordlist' || route.name === 'WordlistSearch') && newWordlistId) {
        searchConfig.setWordlist(newWordlistId as string);
    }
}, { immediate: true });


onMounted(async () => {
    // Stores auto-initialize - no manual setup needed
});

// Reactive state from modular stores
const isSearching = computed(() => loading.isSearching);
const currentEntry = computed(() => content.currentEntry);
const previousEntry = ref<any>(null);

// Content state for template
const partialEntry = computed(() => content.partialEntry);
const isStreamingData = computed(() => content.isStreamingData);
const definitionError = computed(() => content.definitionError);

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

// Simplified loading modal sync
watch(isSearching, (searching) => {
    showLoadingModal.value = searching;
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

// Progressive sidebar visibility logic
const shouldShowProgressiveSidebar = computed(() => {
    if (searchConfig.searchMode !== 'lookup' || ui.mode !== 'dictionary' || !currentEntry.value) return false;
    
    const definitions = currentEntry.value.definitions;
    if (!definitions?.length) return false;
    
    const clusters = new Set(definitions.map((d: any) => d.meaning_cluster?.id || 'default'));
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
