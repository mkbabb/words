<template>
  <div class="min-h-screen">
    <!-- Landing Page View -->
    <div
      v-if="!hasSearched"
      class="flex items-center justify-center min-h-screen p-8"
    >
      <div class="w-full max-w-4xl">
        <SearchBar />
        
        <!-- Search History -->
        <div class="mt-16 max-w-2xl mx-auto">
          <SearchHistory />
        </div>
      </div>
    </div>

    <!-- Results View -->
    <div
      v-else
      class="min-h-screen"
    >
      <!-- Fixed Search Bar -->
      <div class="sticky top-0 z-40 bg-background/80 backdrop-blur-sm border-b">
        <div class="container mx-auto px-4 py-4">
          <SearchBar />
        </div>
      </div>

      <!-- Main Content -->
      <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
          <!-- Search Results -->
          <div v-if="isSearching" class="text-center py-8">
            <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mx-auto mb-4"></div>
            <p class="text-muted-foreground">Searching...</p>
          </div>

          <!-- No Results -->
          <div v-else-if="searchResults.length === 0" class="text-center py-8">
            <p class="text-muted-foreground">No results found for "{{ searchQuery }}"</p>
            <p class="text-sm text-muted-foreground mt-2">Try a different spelling or search term.</p>
          </div>

          <!-- Definition Display -->
          <div v-else-if="currentEntry" class="space-y-8">
            <DefinitionDisplay />
          </div>

          <!-- Search Results List -->
          <div v-else class="space-y-4">
            <h2 class="text-xl font-semibold">Search Results</h2>
            <div class="grid gap-4">
              <Card
                v-for="result in searchResults"
                :key="result.word"
                class="cursor-pointer hover:shadow-md transition-shadow"
                @click="selectResult(result)"
              >
                <CardHeader>
                  <CardTitle>{{ result.word }}</CardTitle>
                  <div class="flex items-center gap-2 text-sm text-muted-foreground">
                    <span class="capitalize">{{ result.type }}</span>
                    <span>•</span>
                    <span>{{ Math.round(result.score * 100) }}% match</span>
                  </div>
                </CardHeader>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import SearchBar from '@/components/SearchBar.vue';
import DefinitionDisplay from '@/components/DefinitionDisplay.vue';
import SearchHistory from '@/components/SearchHistory.vue';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';

const store = useAppStore();

onMounted(() => {
  console.log('Home component mounted');
  console.log('Has searched:', store.hasSearched);
  console.log('Search results:', store.searchResults);
});

const hasSearched = computed(() => store.hasSearched);
const isSearching = computed(() => store.isSearching);
const searchQuery = computed(() => store.searchQuery);
const searchResults = computed(() => store.searchResults);
const currentEntry = computed(() => store.currentEntry);

const selectResult = async (result: SearchResult) => {
  await store.getDefinition(result.word);
};
</script>