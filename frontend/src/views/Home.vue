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
                <div class="mx-auto max-w-4xl">
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
                    <div v-if="shouldShowProgressiveSidebar" class="hidden w-48 flex-shrink-0 xl:block">
                        <div 
                            class="sticky"
                            :style="{ top: isScrolled ? '5rem' : '6rem', zIndex: 30 }"
                        >
                            <ProgressiveSidebar />
                        </div>
                    </div>
                    
                    <!-- Main Content -->
                    <div class="flex-1 max-w-5xl mx-auto">
                        <!-- Animated Content Cards -->
                        <Transition
                    mode="out-in"
                    enter-active-class="transition-all duration-300 ease-apple-bounce"
                    leave-active-class="transition-all duration-200 ease-out"
                    enter-from-class="opacity-0 scale-95 translate-x-8 rotate-1"
                    enter-to-class="opacity-100 scale-100 translate-x-0 rotate-0"
                    leave-from-class="opacity-100 scale-100 translate-x-0 rotate-0"
                    leave-to-class="opacity-0 scale-95 -translate-x-8 -rotate-1"
                >
                    <!-- Definition Content -->
                    <div v-if="store.searchMode === 'lookup' && store.mode !== 'suggestions'" key="lookup">
                        <!-- Loading State -->
                        <div v-if="isSearching" class="space-y-8">
                            <DefinitionSkeleton />
                        </div>

                        <!-- Definition Display -->
                        <div v-else-if="currentEntry" class="space-y-8">
                            <DefinitionDisplay />
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
                        <div class="space-y-8">
                            <!-- Wordlist content will go here -->
                            <div
                                class="py-16 text-center text-muted-foreground"
                            >
                                Wordlist mode coming soon...
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
        v-model="isSearching"
        :word="store.searchQuery || 'searching'"
        :progress="store.loadingProgress"
        :current-stage="store.loadingStage"
        mode="lookup"
    />
    
    <!-- Loading Modal for AI Suggestions -->
    <LoadingModal
        v-model="store.isSuggestingWords"
        :display-text="'Efflorescing'"
        :progress="store.suggestionsProgress"
        :current-stage="store.suggestionsStage"
        mode="suggestions"
    />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAppStore } from '@/stores';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay, WordSuggestionDisplay } from '@/components/custom/definition';
import { DefinitionSkeleton } from '@/components/custom/definition';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import { StageTest } from '@/components/custom/test';
import { ProgressiveSidebar } from '@/components/custom/navigation';

const store = useAppStore();

// Component refs
const stageTestRef = ref();


// Handle stage mode enter key
const handleStageEnter = (_query: string) => {
    if (stageTestRef.value && stageTestRef.value.startMockTest) {
        stageTestRef.value.startMockTest();
    }
};


onMounted(async () => {
    console.log('Home component mounted');
    console.log('Has searched:', store.hasSearched);
    console.log('Search results:', store.searchResults);

    // Ensure vocabulary suggestions are loaded
    if (store.vocabularySuggestions.length === 0) {
        await store.refreshVocabularySuggestions();
    }
});

const isSearching = computed(() => store.isSearching);
const currentEntry = computed(() => store.currentEntry);

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
    // Only show in dictionary mode with a current entry
    if (store.mode !== 'dictionary' || !currentEntry.value) return false;
    
    // Check if we have multiple clusters
    const definitions = currentEntry.value.definitions;
    if (!definitions || definitions.length === 0) return false;
    
    // Group by cluster to see if we have multiple
    const clusters = new Set(definitions.map(d => d.meaning_cluster?.id || 'default'));
    return clusters.size > 1;
});
</script>
