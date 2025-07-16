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
    <div class="min-h-screen">
      <Tabs v-model="activeTab" class="">
        <!-- Sticky Tabs and Search Bar -->
        <div :class="searchBarClasses">
          <div class="container grid gap-2" :style="{ 
            transform: `scale(${1 - shrinkPercentage * 0.05})`,
            opacity: 1 - shrinkPercentage * 0.1
          }">
            <TabsList class="flex justify-center bg-transparent">
              <TabsTrigger
                value="definition"
                style="font-family: 'Fraunces', serif"
                >Dictionary</TabsTrigger
              >
              <TabsTrigger
                value="visualizer"
                style="font-family: 'Fraunces', serif"
                >Visualizer</TabsTrigger
              >
            </TabsList>
          </div>

          <!-- Sticky Search Bar with scroll responsiveness -->
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
        </div>
      </Tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAppStore } from '@/stores';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import SearchBar from '@/components/SearchBar.vue';
import DefinitionDisplay from '@/components/DefinitionDisplay.vue';
import DefinitionSkeleton from '@/components/DefinitionSkeleton.vue';
import Sidebar from '@/components/Sidebar.vue';
import SeriesVisualizer from '@/components/SeriesVisualizer.vue';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const store = useAppStore();
const activeTab = ref<'definition' | 'visualizer'>('definition');

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
  return Math.min((y.value - scrollThreshold) / 100, 1);
});

const searchBarClasses = computed(() => {
  return cn(
    'sticky top-0 z-40 transition-all duration-300 ease-out',
    isScrolled.value ? 'py-2' : 'py-4'
  );
});
</script>
