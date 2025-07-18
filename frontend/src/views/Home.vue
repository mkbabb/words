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
    <div class="relative min-h-screen p-2">
      <Tabs v-model="activeTab" class="">
        <!-- Sticky Tabs and Search Bar -->
        <TabsList
          class="m-auto grid w-fit grid-cols-3 justify-center gap-1 bg-transparent"
        >
          <TabsTrigger value="definition">Dictionary</TabsTrigger>
          <TabsTrigger value="visualizer">Visualizer</TabsTrigger>
          <TabsTrigger value="stage">Stage</TabsTrigger>
        </TabsList>

        <!-- Sticky Search Bar with scroll responsiveness -->
        <div :class="searchBarClasses">
          <SearchBar :shrink-percentage="shrinkPercentage" />
        </div>

        <!-- Border separator (not sticky) -->
        <div class="border-border/50 border-b"></div>

        <!-- Content Area -->
        <div class="container mx-auto max-w-5xl px-4 py-8">
          <!-- Definition Tab Content -->
          <TabsContent value="definition">
            <!-- Loading State -->
            <div v-if="isSearching" class="space-y-8">
              <DefinitionSkeleton />
            </div>

            <!-- Definition Display -->
            <div v-else-if="currentEntry" class="space-y-8">
              <DefinitionDisplay variant="default" />
            </div>

            <!-- Empty State -->
            <div v-else class="py-16 text-center">
              <!-- Empty state - no text -->
            </div>
          </TabsContent>

          <!-- Visualizer Tab Content -->
          <TabsContent value="visualizer">
            <div class="space-y-6">
              <div>
                <h2
                  class="text-3xl font-bold tracking-tight"
                  style="font-family: 'Fraunces', serif"
                >
                  Legendre Polynomial System
                </h2>
                <p
                  class="text-muted-foreground/70 dark:text-muted-foreground/50 mt-2 italic"
                  style="font-family: 'Fraunces', serif"
                >
                  Interactive visualization and series approximation using
                  Legendre polynomials
                </p>
              </div>

              <SeriesVisualizer />
            </div>
          </TabsContent>

          <!-- Stage Tab Content -->
          <TabsContent value="stage">
            <div class="space-y-8">
              <StageTest />
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  </div>

  <!-- Loading Modal -->
  <LoadingModal
    v-model="isSearching"
    :word="store.searchQuery || 'searching'"
    :progress="store.loadingProgress"
    :current-stage="store.loadingStage"
    :facts="currentFacts"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useAppStore } from '@/stores';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import SearchBar from '@/components/SearchBar.vue';
import DefinitionDisplay from '@/components/DefinitionDisplay.vue';
import DefinitionSkeleton from '@/components/DefinitionSkeleton.vue';
import Sidebar from '@/components/Sidebar.vue';
import SeriesVisualizer from '@/components/SeriesVisualizer.vue';
import LoadingModal from '@/components/LoadingModal.vue';
import StageTest from '@/components/StageTest.vue';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { dictionaryApi } from '@/utils/api';
import type { FactItem } from '@/types';

const store = useAppStore();
const activeTab = ref<'definition' | 'visualizer' | 'stage'>('definition');

// Facts for loading modal
const currentFacts = ref<FactItem[]>([]);

// Watch for search queries to fetch facts
watch(
  () => store.searchQuery,
  async newQuery => {
    if (newQuery && store.isSearching) {
      try {
        // Fetch facts asynchronously while search is happening
        const factsResponse = await dictionaryApi.getWordFacts(
          newQuery,
          5,
          store.lookupHistory.slice(-10).map(h => h.word)
        );
        currentFacts.value = factsResponse.facts;
      } catch (error) {
        console.warn('Failed to fetch facts:', error);
        currentFacts.value = [];
      }
    } else if (!newQuery) {
      currentFacts.value = [];
    }
  },
  { immediate: true }
);

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
</script>
