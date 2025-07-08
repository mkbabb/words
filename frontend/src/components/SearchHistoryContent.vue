<template>
  <div>
    <div v-if="recentSearches.length === 0" class="text-center py-8">
      <div v-if="!collapsed" class="text-muted-foreground">
        <p class="text-sm">No search history yet.</p>
        <p class="text-xs mt-1">Start searching to build your history!</p>
      </div>
      <div v-else class="text-muted-foreground">
        <Search :size="16" class="mx-auto opacity-50" />
      </div>
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="search in recentSearches"
        :key="search.id"
        :class="cn(
          'cursor-pointer transition-all hover:shadow-md rounded-lg border border-border/50 hover:border-border bg-card hover:bg-accent/50',
          {
            'p-1': collapsed,
            'p-3': !collapsed,
          }
        )"
        @click="repeatSearch(search.query)"
      >
        <div v-if="!collapsed" class="flex items-center justify-between">
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm truncate">{{ search.query }}</div>
            <div class="text-xs text-muted-foreground mt-1">
              {{ formatDate(search.timestamp) }}
              <Badge 
                v-if="search.results.length > 0" 
                variant="secondary"
                class="ml-2 text-xs"
              >
                {{ search.results.length }} result{{ search.results.length > 1 ? 's' : '' }}
              </Badge>
            </div>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            @click.stop="removeFromHistory(search.id)"
            class="opacity-0 group-hover:opacity-100 transition-opacity p-1"
          >
            <X :size="12" />
          </Button>
        </div>

        <div v-else class="flex items-center justify-center">
          <div class="relative w-10 h-10 rounded-lg bg-gradient-to-br from-amber-50 to-amber-100 border-2 border-amber-200 flex items-center justify-center shadow-sm transform hover:scale-105 transition-transform duration-200">
            <!-- Wood grain effect -->
            <div class="absolute inset-0 bg-gradient-to-br from-amber-100/30 to-amber-200/30 rounded-lg"></div>
            
            <!-- Main letter -->
            <span class="text-sm font-black text-amber-800 relative z-10">
              {{ search.query.charAt(0).toUpperCase() }}
            </span>
            
            <!-- Subscript with rest of word -->
            <span class="absolute -bottom-1 -right-1 text-[8px] font-semibold text-amber-600/70 bg-amber-50/90 px-1 rounded-sm max-w-6 truncate">
              {{ search.query.slice(1, 4) }}{{ search.query.length > 4 ? '...' : '' }}
            </span>
            
            <!-- Subtle inner shadow for depth -->
            <div class="absolute inset-0 rounded-lg shadow-inner opacity-30"></div>
          </div>
        </div>
      </div>

      <div v-if="!collapsed && recentSearches.length > 0" class="pt-2 border-t border-border/50">
        <Button
          variant="ghost"
          size="sm"
          @click="clearHistory"
          class="w-full text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear All History
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { useSearch } from '@/composables/useSearch';
import { formatDate, cn } from '@/utils';
import Button from '@/components/ui/Button.vue';
import Badge from '@/components/ui/Badge.vue';
import { Search, X } from 'lucide-vue-next';

interface Props {
  collapsed?: boolean;
}

const { collapsed = false } = defineProps<Props>();

const store = useAppStore();
const { searchWord } = useSearch();

const recentSearches = computed(() => store.recentSearches);

const repeatSearch = async (query: string) => {
  store.searchQuery = query;
  await searchWord(query);
};

const removeFromHistory = (id: string) => {
  const index = store.searchHistory.findIndex(search => search.id === id);
  if (index >= 0) {
    store.searchHistory.splice(index, 1);
  }
};

const clearHistory = () => {
  store.clearHistory();
};
</script>

<style scoped>
.group:hover .group-hover\:opacity-100 {
  opacity: 1;
}
</style>