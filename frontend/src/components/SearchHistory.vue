<template>
  <Card>
    <CardHeader>
      <div class="flex items-center justify-between">
        <CardTitle>Search History</CardTitle>
        <Button
          v-if="recentSearches.length > 0"
          variant="outline"
          size="sm"
          @click="clearHistory"
        >
          Clear All
        </Button>
      </div>
    </CardHeader>

    <CardContent>
      <div v-if="recentSearches.length === 0" class="text-center py-8 text-muted-foreground">
        <p>No search history yet.</p>
        <p class="text-sm">Start searching to build your history!</p>
      </div>

      <div v-else class="space-y-2 max-h-96 overflow-y-auto">
        <Card
          v-for="search in recentSearches"
          :key="search.id"
          class="cursor-pointer transition-all hover:shadow-md hover:bg-accent/50"
          @click="repeatSearch(search.query)"
        >
          <CardContent class="p-3">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="font-medium">{{ search.query }}</div>
                <div class="text-sm text-muted-foreground">
                  {{ formatDate(search.timestamp) }}
                  <Badge 
                    v-if="search.results.length > 0" 
                    variant="secondary"
                    class="ml-2"
                  >
                    {{ search.results.length }} result{{ search.results.length > 1 ? 's' : '' }}
                  </Badge>
                </div>
              </div>
              
              <Button
                variant="ghost"
                size="sm"
                @click.stop="removeFromHistory(search.id)"
              >
                ×
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { useSearch } from '@/composables/useSearch';
import { formatDate } from '@/utils';
import Button from '@/components/ui/Button.vue';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import Badge from '@/components/ui/Badge.vue';

const store = useAppStore();
const { performSearch } = useSearch();

const recentSearches = computed(() => store.recentSearches);

const clearHistory = () => {
  store.clearHistory();
};

const repeatSearch = async (query: string) => {
  store.searchQuery = query;
  await performSearch(query);
};

const removeFromHistory = (id: string) => {
  const index = store.searchHistory.findIndex(search => search.id === id);
  if (index >= 0) {
    store.searchHistory.splice(index, 1);
  }
};
</script>