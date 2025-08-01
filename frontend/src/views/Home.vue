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
                    <div :class="['flex-1 max-w-5xl mx-auto', store.mode === 'suggestions' ? 'px-4 sm:px-2' : '']">
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
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
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
const route = useRoute();

// Component refs
const stageTestRef = ref();


// Handle stage mode enter key
const handleStageEnter = (_query: string) => {
    if (stageTestRef.value && stageTestRef.value.startMockTest) {
        stageTestRef.value.startMockTest();
    }
};


// Watch for route changes
watch(() => route.name, async (routeName) => {
    if (routeName === 'Definition' && route.params.word) {
        const word = route.params.word as string;
        store.mode = 'dictionary';
        store.searchQuery = word;
        store.hasSearched = true;
        await store.getDefinition(word);
    } else if (routeName === 'Thesaurus' && route.params.word) {
        const word = route.params.word as string;
        store.mode = 'thesaurus';
        store.searchQuery = word;
        store.hasSearched = true;
        await store.getDefinition(word);
    }
}, { immediate: true });

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

<style scoped>
/* Progressive sidebar slide animation */
.sidebar-slide-enter-active {
    transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1); /* ease-apple-bounce */
}

.sidebar-slide-leave-active {
    transition: all 0.25s ease-out;
}

.sidebar-slide-enter-from {
    opacity: 0;
    transform: translateX(-20px);
}

.sidebar-slide-enter-to {
    opacity: 1;
    transform: translateX(0);
}

.sidebar-slide-leave-from {
    opacity: 1;
    transform: translateX(0);
}

.sidebar-slide-leave-to {
    opacity: 0;
    transform: translateX(-20px);
}
</style>
