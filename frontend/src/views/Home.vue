<template>
  <!-- Sidebar -->
  <Sidebar />

  <div 
    :class="cn(
      'min-h-screen transition-all duration-300 ease-in-out',
      {
        'lg:ml-80': !store.sidebarCollapsed,
        'lg:ml-16': store.sidebarCollapsed,
      }
    )"
  >
    <!-- Landing Page View -->
    <div
      v-if="!hasSearched"
      class="flex items-center justify-center min-h-screen p-8"
    >
      <div class="w-full max-w-4xl">
        <SearchBar />
      </div>
    </div>

    <!-- Results View -->
    <div
      v-else
      class="min-h-screen"
    >
      <!-- Fixed Search Bar -->
      <div 
        class="sticky top-0 z-40 bg-background/95 backdrop-blur-3xl border-b transition-all duration-300 ease-in-out"
      >
        <div class="container mx-auto px-4 py-4">
          <SearchBar />
        </div>
      </div>

      <!-- Main Content -->
      <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
          <!-- Loading State -->
          <div v-if="isSearching" class="space-y-8">
            <DefinitionSkeleton />
          </div>

          <!-- Definition Display -->
          <div v-else-if="currentEntry" class="space-y-8">
            <!-- Theme Selector for Testing -->
            <div class="flex gap-2 mb-4 justify-center">
              <button 
                v-for="variant in (['default', 'gold', 'silver', 'bronze'] as const)" 
                :key="variant"
                @click="selectedVariant = variant"
                :class="[
                  'px-3 py-1 rounded text-sm border',
                  selectedVariant === variant 
                    ? 'bg-primary text-primary-foreground border-primary' 
                    : 'bg-secondary text-secondary-foreground border-border hover:bg-accent'
                ]"
              >
                {{ variant.charAt(0).toUpperCase() + variant.slice(1) }}
              </button>
            </div>
            <DefinitionDisplay :variant="selectedVariant" />
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-16">
            <p class="text-muted-foreground text-lg">Start typing to search for a word</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAppStore } from '@/stores';
import { cn } from '@/utils';
import SearchBar from '@/components/SearchBar.vue';
import DefinitionDisplay from '@/components/DefinitionDisplay.vue';
import DefinitionSkeleton from '@/components/DefinitionSkeleton.vue';
import Sidebar from '@/components/Sidebar.vue';

const store = useAppStore();
const selectedVariant = ref<'default' | 'gold' | 'silver' | 'bronze'>('default');

onMounted(() => {
  console.log('Home component mounted');
  console.log('Has searched:', store.hasSearched);
  console.log('Search results:', store.searchResults);
});

const hasSearched = computed(() => store.hasSearched);
const isSearching = computed(() => store.isSearching);
const currentEntry = computed(() => store.currentEntry);

</script>