<template>
  <div v-if="collapsed" class="w-full h-full flex flex-col">
    <!-- Collapsed view - compact cards -->
    <div class="flex-1 relative min-h-0">
      <div class="absolute inset-0">
        <div class="space-y-1 max-h-full overflow-y-auto scrollbar-thin">
          <TransitionGroup
            name="toast-stack"
            tag="div"
            class="space-y-1"
          >
            <div
              v-for="(entry, index) in limitedSearches"
              :key="entry.id"
              :class="cn(
                'group relative w-full rounded-lg cursor-pointer transition-all duration-200 overflow-hidden',
                'bg-background border border-border shadow-sm',
                'hover:shadow-md hover:bg-accent'
              )"
              @click="searchWord(entry.query)"
              @mouseenter="hoveredIndex = index"
              @mouseleave="hoveredIndex = -1"
            >
              <div class="px-2 py-2 flex items-center justify-center">
                <span class="text-xs font-bold uppercase tracking-wider">
                  {{ entry.query.substring(0, 2) }}
                </span>
              </div>
              
              <!-- Tooltip on hover -->
              <div 
                v-if="hoveredIndex === index"
                class="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded-md pointer-events-none whitespace-nowrap z-50 shadow-md"
              >
                {{ entry.query }}
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>
    </div>
  </div>
  
  <div v-else class="space-y-1">
    <!-- Expanded view -->
    <TransitionGroup
      name="history-list"
      tag="div"
      class="space-y-1"
    >
      <div
        v-for="entry in recentSearches"
        :key="entry.id"
        :class="cn(
          'group flex items-center justify-between px-2 py-2 rounded-lg cursor-pointer transition-all duration-200',
          'hover:bg-accent hover:pl-3'
        )"
        @click="searchWord(entry.query)"
      >
        <div class="flex items-center gap-3 min-w-0">
          <History :size="14" class="text-muted-foreground shrink-0" />
          <span class="text-sm truncate">{{ entry.query }}</span>
        </div>
        <span class="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          {{ formatDate(entry.timestamp) }}
        </span>
      </div>
    </TransitionGroup>
    
    <div v-if="recentSearches.length === 0" class="text-center py-4">
      <p class="text-xs text-muted-foreground">No recent searches</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAppStore } from '@/stores';
import { formatDate, cn } from '@/utils';
import { History } from 'lucide-vue-next';

interface Props {
  collapsed: boolean;
}

defineProps<Props>();

const store = useAppStore();
const recentSearches = computed(() => store.recentSearches);

// Stack state
const hoveredIndex = ref(-1);

const limitedSearches = computed(() => {
  return recentSearches.value.slice(0, 20); // Limit to prevent performance issues
});

const searchWord = async (query: string) => {
  store.searchQuery = query;
  await store.searchWord(query);
};
</script>

<style scoped>
/* Hide scrollbar by default */
.scrollbar-none::-webkit-scrollbar {
  width: 0;
  display: none;
}

/* Show thin scrollbar on hover */
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: theme('colors.muted.DEFAULT');
  border-radius: 2px;
}

/* History list transitions */
.history-list-enter-active,
.history-list-leave-active {
  transition: all 0.3s ease;
}

.history-list-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.history-list-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

.history-list-move {
  transition: transform 0.3s ease;
}

/* Toast stack transitions */
.toast-stack-enter-active,
.toast-stack-leave-active {
  transition: all 0.3s ease;
}

.toast-stack-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.8);
}

.toast-stack-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.8);
}

.toast-stack-move {
  transition: all 0.3s ease;
}
</style>